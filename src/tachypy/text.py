"""TachyPy's text rendering: system fonts via FreeType + HarfBuzz, drawn as OpenGL quads."""

from dataclasses import dataclass
from functools import lru_cache
import math
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

from tachypy._warnings import warn_once

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


class Text:
    """
    Render text with system TrueType/OpenType fonts and OpenGL quads.

    TachyPy's only text class. An unresolved ``font_name`` is retried
    against a small built-in default list (see :meth:`resolve_font_path`),
    with a warning; construction only raises if none of those resolve either.
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
        content_scale: float = 2.0,
    ):
        """Create a system-font text renderer with OpenGL quad drawing.

        Parameters
        ----------
        text : str
            Text to render. Newlines (``\\n``) produce multi-line output.
        dest_rect : tuple (x1, y1, x2, y2), optional
            Bounding box in logical pixels (top-left origin). Text is laid
            out and word-wrapped within this rectangle. If omitted, text
            starts at the origin with no wrapping.
        font_name : str
            Family name (``"Helvetica"``), comma-separated fallback list
            (``"Avenir, Helvetica, Arial"``), or an absolute font file path.
        font_size : float
            Size in logical points.
        color : sequence of 3 ints
            RGB color in the 0–255 range.
        line_spacing : float
            Line-height multiplier relative to the font's natural height.
        align : str
            Horizontal alignment within ``dest_rect``: ``"left"``,
            ``"center"``, or ``"right"``.
        vertical_align : str
            Vertical alignment within ``dest_rect``: ``"top"``,
            ``"center"``, or ``"bottom"``.
        content_scale : float
            Pass ``screen.content_scale`` for sharp text on HiDPI screens.
            Defaults to ``2.0``; see :doc:`text_rendering` for why.

        Raises
        ------
        RuntimeError
            FreeType/HarfBuzz are missing or the resolved font file couldn't
            be parsed (this shouldn't happen with a normal ``pip install
            tachypy`` -- both are mandatory dependencies).
        FileNotFoundError
            ``font_name`` didn't resolve to a font file, and neither did any
            of TachyPy's built-in default fonts.

        Notes
        -----
        Construction is not cheap: it loads the font file and builds a
        FreeType face + HarfBuzz font from scratch (a few milliseconds,
        independent of ``content_scale``), which alone can exceed a single
        frame budget at high refresh rates. Build one instance up front and
        reuse it across frames/trials, updating content with
        :meth:`set_text` (cheap: only newly-seen glyphs are rasterized,
        already-seen ones are served from this instance's glyph cache).
        Never recreate a ``Text`` inside a per-frame or per-trial loop. See
        :doc:`text_rendering` for measurements.
        """
        self.text = text
        self.dest_rect = dest_rect
        self.font_name = font_name
        self.font_size = float(font_size)
        self.color = color
        self.line_spacing = float(line_spacing)
        self.align = align
        self.vertical_align = vertical_align

        self._face = None
        self._hb_font = None
        self._font_bytes = None
        self._glyph_cache: Dict[int, _GlyphTexture] = {}
        self._line_height = self.font_size
        self._content_scale = float(content_scale)
        if not math.isfinite(self._content_scale) or self._content_scale <= 0:
            raise ValueError("content_scale must be a finite value greater than 0.")

        if not (HAS_FREETYPE and HAS_HARFBUZZ):
            missing = ", ".join(
                name
                for name, available in (
                    ("freetype-py", HAS_FREETYPE),
                    ("uharfbuzz", HAS_HARFBUZZ),
                )
                if not available
            )
            raise RuntimeError(
                f"{missing} not installed, but TachyPy requires both for text "
                "rendering (they're in tachypy's base install_requires, so this "
                "shouldn't happen with a normal `pip install tachypy`)."
                "\n\tReinstall with: pip install --force-reinstall freetype-py uharfbuzz"
            )

        font_path = self.resolve_font_path(self.font_name)
        if font_path is None:
            raise FileNotFoundError(
                f"No font file found matching '{self.font_name}', and none of "
                "TachyPy's built-in default fonts (Helvetica, Arial, DejaVu Sans, "
                "Liberation Sans, Noto Sans, Times New Roman) were found on this "
                "system either."
                "\n\tPass an absolute font file path, or install one of those fonts."
            )
        if not self._font_path_matches_query(font_path, self.font_name):
            warn_once(
                "Text font resolution",
                f"'{self.font_name}' isn't available on this system; using "
                f"'{font_path.name}' instead, which may look different."
                "\n\t\tPass an absolute path or an installed font name if "
                "the exact typeface matters.",
            )
        try:
            self._init_system_font(font_path)
        except Exception as err:
            raise RuntimeError(
                f"Found a font file for '{self.font_name}' ({font_path}) but "
                f"couldn't load it: {err}."
                "\n\tCheck that the font file isn't corrupt, or try a different "
                "font_name."
            ) from err

    @staticmethod
    def _text_preview(text: str, limit: int = 40) -> str:
        """Return a one-line, length-capped preview of ``text`` for warning messages."""
        single_line = text.replace("\n", "\\n")
        if len(single_line) > limit:
            single_line = single_line[:limit].rstrip() + "..."
        return single_line

    @staticmethod
    @lru_cache(maxsize=1)
    def _iter_system_font_files() -> Tuple[Path, ...]:
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
        return tuple(files)

    @classmethod
    def clear_font_cache(cls) -> None:
        """Clear the cached system-font discovery results.

        This is useful when an experiment installs or removes a font while
        the Python process is running. Normal applications should not need to
        call it.
        """
        cache_clear = getattr(cls._iter_system_font_files, "cache_clear", None)
        if cache_clear is not None:
            cache_clear()

    @staticmethod
    def _tokenize_font_query(font_name: str) -> List[str]:
        """Normalize a font query into searchable tokens."""
        normalized = re.sub(r"[^a-z0-9]+", " ", str(font_name).lower()).strip()
        return [part for part in normalized.split() if part]

    @classmethod
    def _font_path_matches_query(cls, font_path: Path, font_name: str) -> bool:
        """Return whether a resolved path matches one requested font query."""
        direct = Path(str(font_name).split(",", 1)[0].strip()).expanduser()
        if direct == font_path:
            return True

        stem_tokens = cls._tokenize_font_query(font_path.stem)
        stem_styles = set(stem_tokens) & cls._STYLE_WORDS
        stem_family = [token for token in stem_tokens if token not in cls._STYLE_WORDS]
        stem_joined = "".join(stem_family)
        queries = [query.strip() for query in str(font_name).split(",") if query.strip()]
        for query in queries:
            tokens = cls._tokenize_font_query(query)
            if not tokens:
                continue
            query_styles = set(tokens) & cls._STYLE_WORDS
            query_family = [token for token in tokens if token not in cls._STYLE_WORDS]
            family_matches = "".join(query_family) == stem_joined
            unexpected_styles = stem_styles - query_styles - {"regular"}
            if family_matches and not unexpected_styles and query_styles <= stem_styles:
                return True
        return False

    # Style qualifiers penalized in resolve_font_path() unless requested.
    _STYLE_WORDS = {
        "italic", "oblique", "bold", "narrow", "condensed", "black", "light",
        "medium", "semibold", "semilight", "thin", "heavy", "extrabold",
        "ultra", "expanded", "book", "regular",
    }

    @classmethod
    def resolve_font_path(cls, font_name: str) -> Optional[Path]:
        """Resolve a system font from a family/path query.

        Supports:
        - absolute/relative font file paths
        - comma-separated fallback font families (e.g. "Avenir, Helvetica, Arial")
        - partial family/style matching against system font file names

        Style words (e.g. "Bold", "Italic") in the query are matched against
        the font file, but unrequested style words present in a candidate's
        file name are penalized so a plain query like "Arial" prefers the
        regular weight over "Arial Narrow Italic". An exact family match
        (e.g. "Arial" -> "Arial.ttf") is also preferred over a candidate with
        extra qualifiers (e.g. "Arial Unicode").
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
            requested_styles = set(tokens) & cls._STYLE_WORDS
            query_family = [token for token in tokens if token not in cls._STYLE_WORDS]
            query_family_joined = "".join(query_family)

            # Rank by relevance, then by style/exactness (see docstring).
            scored = []
            for path in candidates:
                stem_tokens = cls._tokenize_font_query(path.stem)
                stem_family = [token for token in stem_tokens if token not in cls._STYLE_WORDS]
                stem_joined = " ".join(stem_tokens)
                stem_family_joined = "".join(stem_family)

                # Every token must match, or a common one like "sans" could silently match any Sans-family font.
                if not all(token in stem_tokens or token in stem_joined for token in tokens):
                    continue
                relevance = sum(3 if token in stem_tokens else 1 for token in tokens)

                unrequested_styles = (set(stem_tokens) & cls._STYLE_WORDS) - requested_styles
                exact_family = stem_family_joined == query_family_joined
                exact_match = set(stem_tokens) == set(tokens)
                scored.append((exact_family, relevance, -len(unrequested_styles), exact_match, path))

            if scored:
                scored.sort(key=lambda item: (item[0], item[1], item[2], item[3]), reverse=True)
                return scored[0][4]

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
        physical_size = max(1, round(self.font_size * self._content_scale * 64))

        self._font_bytes = font_path.read_bytes()
        self._face = freetype.Face(str(font_path))
        self._face.set_char_size(physical_size)

        self._hb_font = hb.Font(hb.Face(self._font_bytes))
        self._hb_font.scale = (physical_size, physical_size)

        metrics = self._face.size
        self._line_height = (
            max(1.0, float(metrics.height) / 64.0 / self._content_scale)
            * self.line_spacing
        )

    def _scaled_26_6(self, value: float) -> float:
        """Convert HarfBuzz/FreeType 26.6 units to TachyPy logical pixels.

        "26.6" is fixed-point notation: the last 6 bits are fractional, so
        HarfBuzz/FreeType store 64 units for each physical framebuffer pixel.
        Rounding before dividing by ``content_scale`` keeps glyph advances on
        the real display pixel grid, while TachyPy still draws in logical
        coordinates.
        """
        return round(float(value) / 64.0) / self._content_scale

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
        _, positions = self._shape(line)
        pen_x = 0.0
        for pos in positions:
            pen_x += self._scaled_26_6(pos.x_advance)
        return pen_x

    def _line_bounds(self, line: str) -> Tuple[float, float, float]:
        """Return the rendered line bounds as (width, top, bottom)."""
        if line == "":
            return 0.0, 0.0, 0.0

        # Use actual glyph extents so descenders do not get vertically clipped.
        infos, positions = self._shape(line)
        scale = self._content_scale
        pen_x = 0.0
        max_x = 0.0
        top = 0.0
        bottom = 0.0

        for info, pos in zip(infos, positions):
            glyph = self._glyph_texture(info.codepoint)
            x_offset = self._scaled_26_6(pos.x_offset)
            y_offset = self._scaled_26_6(pos.y_offset)

            glyph_x = pen_x + x_offset + glyph.bearing_x / scale
            glyph_top = -glyph.bearing_y / scale - y_offset
            glyph_bottom = glyph_top + glyph.height / scale

            max_x = max(max_x, glyph_x + glyph.width / scale)
            top = min(top, glyph_top)
            bottom = max(bottom, glyph_bottom)
            pen_x += self._scaled_26_6(pos.x_advance)

        return max(max_x, pen_x), top, bottom

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
                if not current:
                    current = word
                elif self._measure_line(f"{current} {word}") <= max_width:
                    current = f"{current} {word}"
                else:
                    lines.append(current)
                    current = word
            if current:
                lines.append(current)

        overflow_width = 0.0
        for line in lines:
            if not line:
                continue
            width = self._measure_line(line)
            if width > max_width:
                overflow_width = max(overflow_width, width)
        if overflow_width > max_width:
            warn_once(
                "Text layout",
                f"Text '{self._text_preview(self.text)}' contains a word "
                f"{overflow_width:.1f}px wide, wider than dest_rect ({max_width:.1f}px); "
                f"it can't be broken, so it will overflow past the edge."
                "\n\t\tUse a wider rectangle, a smaller font, or shorter words.",
            )

        return lines

    def set_text(self, new_text: str):
        """Update content text in place (cheap -- reuses this instance's
        glyph cache; only glyphs not already seen are rasterized). Prefer
        this over constructing a new ``Text`` on a per-frame/per-trial path.
        """
        self.text = new_text

    def set_dest_rect(self, dest_rect):
        """Update destination layout rectangle."""
        self.dest_rect = dest_rect

    def draw(self):
        """Draw text."""
        lines = self._split_lines()
        line_bounds = [self._line_bounds(line) for line in lines]
        line_widths = [bounds[0] for bounds in line_bounds]
        block_top = min(
            (i * self._line_height + top for i, (_, top, _) in enumerate(line_bounds)),
            default=0.0,
        )
        block_bottom = max(
            (i * self._line_height + bottom for i, (_, _, bottom) in enumerate(line_bounds)),
            default=0.0,
        )
        total_height = max(1.0, block_bottom - block_top)

        if self.dest_rect and total_height > float(self.dest_rect[3] - self.dest_rect[1]):
            rect_height = float(self.dest_rect[3] - self.dest_rect[1])
            warn_once(
                "Text layout",
                f"Text '{self._text_preview(self.text)}' is {total_height:.1f}px tall, "
                f"taller than dest_rect ({rect_height:.1f}px); it is not clipped, so it "
                f"will draw past the rectangle's edge."
                "\n\t\tUse a taller rectangle, smaller text, or fewer lines.",
            )

        if self.dest_rect:
            x1, y1, x2, y2 = self.dest_rect
            rect_w = float(x2 - x1)
            rect_h = float(y2 - y1)
            if self.vertical_align == "top":
                baseline0 = y1 - block_top
            elif self.vertical_align == "bottom":
                baseline0 = y1 + rect_h - total_height - block_top
            else:
                baseline0 = y1 + (rect_h - total_height) / 2.0 - block_top
        else:
            x1 = 0.0
            rect_w = max(line_widths) if line_widths else 0.0
            baseline0 = -block_top

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glColor3f(self.color[0] / 255.0, self.color[1] / 255.0, self.color[2] / 255.0)

        baseline = baseline0
        for line, line_w in zip(lines, line_widths):
            if line == "":
                # Handle empty lines (e.g., "\n\n")
                baseline += self._line_height
                continue

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
            scale = self._content_scale
            # Start on a physical pixel; _scaled_26_6 keeps each advance there too.
            pen_x = round(pen_x * scale) / scale
            baseline = round(baseline * scale) / scale
            for info, pos in zip(infos, positions):
                glyph = self._glyph_texture(info.codepoint)

                x_offset = self._scaled_26_6(pos.x_offset)
                y_offset = self._scaled_26_6(pos.y_offset)

                x = pen_x + x_offset + glyph.bearing_x / scale
                y = baseline - glyph.bearing_y / scale - y_offset
                x2 = x + glyph.width / scale
                y2 = y + glyph.height / scale

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

                pen_x += self._scaled_26_6(pos.x_advance)

            baseline += self._line_height

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)

    def delete(self):
        """Release allocated glyph textures."""
        for glyph in self._glyph_cache.values():
            glDeleteTextures([glyph.texture_id])
        self._glyph_cache.clear()
