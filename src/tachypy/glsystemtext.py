"""System-font OpenGL text rendering (FreeType + HarfBuzz) with graceful fallback."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from OpenGL.GL import (
    GL_BLEND,
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glColor3f,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glTexCoord2f,
    glTexImage2D,
    glTexParameterf,
    glVertex2f,
)

from tachypy.gltext import GLText

try:
    import freetype  # type: ignore

    HAS_FREETYPE = True
except Exception:
    HAS_FREETYPE = False
    freetype = None

try:
    import uharfbuzz as hb  # type: ignore

    HAS_HARFBUZZ = True
except Exception:
    HAS_HARFBUZZ = False
    hb = None


@dataclass
class _GlyphTexture:
    """Cached OpenGL texture and metrics for a single shaped glyph."""
    texture_id: int
    width: int
    height: int
    bearing_x: float
    bearing_y: float


class GLSystemText:
    """
    Render text with system TrueType/OpenType fonts and OpenGL quads.

    Falls back to GLText when shaping/rasterization dependencies are missing.
    """

    def __init__(
        self,
        text: str,
        dest_rect=None,
        font_name: str = "Helvetica",
        font_size: float = 32.0,
        color: Sequence[float] = (255, 255, 255),
        line_spacing: float = 1.15,
        align: str = "center",
        vertical_align: str = "center",
        fallback_renderer: str = "bitmap",
    ):
        """Create a system-font text renderer with OpenGL quad drawing."""
        self.text = text
        self.dest_rect = dest_rect
        self.font_name = font_name
        self.font_size = float(font_size)
        self.color = color
        self.line_spacing = float(line_spacing)
        self.align = align
        self.vertical_align = vertical_align

        self._fallback = None
        self._enabled = False

        self._face = None
        self._hb_font = None
        self._font_bytes = None
        self._glyph_cache: Dict[int, _GlyphTexture] = {}
        self._line_height = float(font_size)
        self._ascender = float(font_size * 0.8)

        if HAS_FREETYPE and HAS_HARFBUZZ:
            font_path = self.resolve_font_path(self.font_name)
            if font_path is not None:
                try:
                    self._init_system_font(font_path)
                    self._enabled = True
                except Exception:
                    self._enabled = False

        if not self._enabled:
            if fallback_renderer == "sdf":
                from tachypy.gltext_sdf import GLTextSDF

                self._fallback = GLTextSDF(
                    text=text,
                    dest_rect=dest_rect,
                    color=color,
                    pixel_size=max(2.0, font_size / 8.0),
                    line_spacing=2.0,
                    align=align,
                    vertical_align=vertical_align,
                )
            else:
                self._fallback = GLText(
                    text=text,
                    dest_rect=dest_rect,
                    color=color,
                    pixel_size=max(2.0, font_size / 8.0),
                    line_spacing=2.0,
                    align=align,
                    vertical_align=vertical_align,
                )

    @staticmethod
    def _iter_system_font_files() -> List[Path]:
        """Return discovered TrueType/OpenType font files from common locations."""
        files: List[Path] = []
        font_dirs = [
            Path("/System/Library/Fonts"),
            Path("/Library/Fonts"),
            Path.home() / "Library/Fonts",
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
            Path.home() / ".fonts",
            Path.home() / ".local" / "share" / "fonts",
            Path("C:/Windows/Fonts"),
        ]
        for directory in font_dirs:
            if not directory.exists():
                continue
            for path in directory.glob("**/*"):
                if path.is_file() and path.suffix.lower() in {".ttf", ".otf", ".ttc"}:
                    files.append(path)
        return files

    @staticmethod
    def _tokenize_font_query(font_name: str) -> List[str]:
        """Normalize a font query into searchable tokens."""
        normalized = re.sub(r"[^a-z0-9]+", " ", str(font_name).lower()).strip()
        return [part for part in normalized.split() if part]

    @classmethod
    def resolve_font_path(cls, font_name: str) -> Optional[Path]:
        """Resolve a system font from a family/path query.

        Supports:
        - absolute/relative font file paths
        - comma-separated fallback font families (e.g. "Avenir, Helvetica, Arial")
        - partial family/style matching against system font file names
        """
        if not font_name:
            return None

        direct = Path(font_name).expanduser()
        if direct.is_file():
            return direct

        candidates = cls._iter_system_font_files()
        if not candidates:
            return None

        queries = [q.strip() for q in str(font_name).split(",") if q.strip()]
        if not queries:
            queries = [str(font_name)]

        for query in queries:
            tokens = cls._tokenize_font_query(query)
            if not tokens:
                continue
            best_score = -1
            best_path = None
            for path in candidates:
                stem_tokens = cls._tokenize_font_query(path.stem)
                stem_joined = " ".join(stem_tokens)

                score = 0
                for token in tokens:
                    if token in stem_tokens:
                        score += 3
                    elif token in stem_joined:
                        score += 1

                if score > best_score:
                    best_score = score
                    best_path = path

            if best_score > 0 and best_path is not None:
                return best_path

        # Last-resort defaults.
        for fallback in (
            "Helvetica",
            "Arial",
            "DejaVu Sans",
            "Liberation Sans",
            "Noto Sans",
            "Times New Roman",
        ):
            tokens = cls._tokenize_font_query(fallback)
            for path in candidates:
                stem_tokens = cls._tokenize_font_query(path.stem)
                if all(token in " ".join(stem_tokens) for token in tokens):
                    return path
        return None

    def _init_system_font(self, font_path: Path) -> None:
        """Initialize FreeType face and HarfBuzz font from a font file."""
        self._font_bytes = font_path.read_bytes()
        self._face = freetype.Face(str(font_path))
        self._face.set_char_size(int(self.font_size * 64))

        self._hb_font = hb.Font(hb.Face(self._font_bytes))
        self._hb_font.scale = (int(self.font_size * 64), int(self.font_size * 64))

        metrics = self._face.size
        self._line_height = max(1.0, float(metrics.height) / 64.0) * self.line_spacing
        self._ascender = float(metrics.ascender) / 64.0

    def _shape(self, text: str):
        """Shape a string into glyph indices and positions via HarfBuzz."""
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self._hb_font, buf)
        return buf.glyph_infos, buf.glyph_positions

    def _glyph_texture(self, glyph_index: int) -> _GlyphTexture:
        """Return (and cache) an OpenGL texture for a glyph index."""
        cached = self._glyph_cache.get(glyph_index)
        if cached is not None:
            return cached

        self._face.load_glyph(glyph_index, freetype.FT_LOAD_RENDER)
        slot = self._face.glyph
        bitmap = slot.bitmap

        width = int(bitmap.width)
        rows = int(bitmap.rows)
        if width <= 0 or rows <= 0:
            width, rows = 1, 1
            alpha = np.zeros((rows, width), dtype=np.uint8)
        else:
            alpha = np.array(bitmap.buffer, dtype=np.uint8).reshape(rows, bitmap.pitch)[:, :width]

        rgba = np.zeros((rows, width, 4), dtype=np.uint8)
        rgba[:, :, 0:3] = 255
        rgba[:, :, 3] = alpha

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, rows, 0, GL_RGBA, GL_UNSIGNED_BYTE, rgba)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)

        glyph = _GlyphTexture(
            texture_id=tex,
            width=width,
            height=rows,
            bearing_x=float(slot.bitmap_left),
            bearing_y=float(slot.bitmap_top),
        )
        self._glyph_cache[glyph_index] = glyph
        return glyph

    def _measure_line(self, line: str) -> float:
        """Measure shaped line width in logical pixels."""
        if line == "":
            return 0.0
        infos, positions = self._shape(line)
        pen_x = 0.0
        for info, pos in zip(infos, positions):
            _ = info
            pen_x += float(pos.x_advance) / 64.0
        return pen_x

    def _split_lines(self) -> List[str]:
        """Wrap text lines to the destination rectangle width when provided."""
        if not self.dest_rect:
            return self.text.splitlines() or [self.text]

        max_width = float(self.dest_rect[2] - self.dest_rect[0])
        lines: List[str] = []
        raw_lines = self.text.splitlines() or [""]

        for raw in raw_lines:
            if raw == "":
                lines.append("")
                continue
            words = raw.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                if current == "" or self._measure_line(candidate) <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

        return lines

    def set_text(self, new_text: str):
        """Update content text."""
        self.text = new_text
        if self._fallback is not None:
            self._fallback.set_text(new_text)

    def set_dest_rect(self, dest_rect):
        """Update destination layout rectangle."""
        self.dest_rect = dest_rect
        if self._fallback is not None:
            self._fallback.set_dest_rect(dest_rect)

    def draw(self):
        """Draw text, delegating to fallback renderer when system path is disabled."""
        if self._fallback is not None:
            self._fallback.draw()
            return

        lines = self._split_lines()
        line_widths = [self._measure_line(line) for line in lines]
        total_height = max(1.0, len(lines) * self._line_height)

        if self.dest_rect:
            x1, y1, x2, y2 = self.dest_rect
            rect_w = float(x2 - x1)
            rect_h = float(y2 - y1)
            if self.vertical_align == "top":
                baseline0 = y1 + self._ascender
            elif self.vertical_align == "bottom":
                baseline0 = y1 + rect_h - total_height + self._ascender
            else:
                baseline0 = y1 + (rect_h - total_height) / 2.0 + self._ascender
        else:
            x1 = 0.0
            rect_w = max(line_widths) if line_widths else 0.0
            baseline0 = self._ascender

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor3f(self.color[0] / 255.0, self.color[1] / 255.0, self.color[2] / 255.0)

        baseline = baseline0
        for line, line_w in zip(lines, line_widths):
            if self.dest_rect:
                if self.align == "left":
                    pen_x = x1
                elif self.align == "right":
                    pen_x = x1 + rect_w - line_w
                else:
                    pen_x = x1 + (rect_w - line_w) / 2.0
            else:
                pen_x = x1

            infos, positions = self._shape(line)
            for info, pos in zip(infos, positions):
                glyph = self._glyph_texture(info.codepoint)

                x_offset = float(pos.x_offset) / 64.0
                y_offset = float(pos.y_offset) / 64.0

                x = pen_x + x_offset + glyph.bearing_x
                y = baseline - glyph.bearing_y - y_offset
                x2 = x + glyph.width
                y2 = y + glyph.height

                glBindTexture(GL_TEXTURE_2D, glyph.texture_id)
                glBegin(GL_QUADS)
                # FreeType bitmap rows are uploaded top-to-bottom; map v=0 to top vertex.
                glTexCoord2f(0.0, 0.0)
                glVertex2f(x, y)
                glTexCoord2f(1.0, 0.0)
                glVertex2f(x2, y)
                glTexCoord2f(1.0, 1.0)
                glVertex2f(x2, y2)
                glTexCoord2f(0.0, 1.0)
                glVertex2f(x, y2)
                glEnd()

                pen_x += float(pos.x_advance) / 64.0

            baseline += self._line_height

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def delete(self):
        """Release allocated glyph textures and fallback resources."""
        if self._fallback is not None and hasattr(self._fallback, "delete"):
            self._fallback.delete()
            return

        for glyph in self._glyph_cache.values():
            glDeleteTextures([glyph.texture_id])
        self._glyph_cache.clear()
