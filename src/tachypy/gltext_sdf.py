"""Signed-distance-field text rendering with OpenGL shaders."""

from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from OpenGL.GL import (
    GL_BLEND,
    GL_CLAMP_TO_EDGE,
    GL_FRAGMENT_SHADER,
    GL_LINEAR,
    GL_LINK_STATUS,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_RED,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_TRUE,
    GL_UNSIGNED_BYTE,
    GL_VERTEX_SHADER,
    glAttachShader,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glCompileShader,
    glCreateProgram,
    glCreateShader,
    glDeleteProgram,
    glDeleteShader,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glGetProgramInfoLog,
    glGetProgramiv,
    glGetShaderInfoLog,
    glGetUniformLocation,
    glLinkProgram,
    glShaderSource,
    glTexCoord2f,
    glTexImage2D,
    glTexParameteri,
    glUniform1f,
    glUniform1i,
    glUniform3f,
    glUseProgram,
    glVertex2f,
)

from tachypy.gltext import GLText, GLYPH_BITMAPS


_VERTEX_SHADER = """
#version 120
void main() {
    gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
    gl_TexCoord[0] = gl_MultiTexCoord0;
}
"""

_FRAGMENT_SHADER = """
#version 120
uniform sampler2D u_atlas;
uniform float u_edge;
uniform float u_smoothing;
uniform vec3 u_color;

void main() {
    float dist = texture2D(u_atlas, gl_TexCoord[0].st).r;
    float alpha = smoothstep(u_edge - u_smoothing, u_edge + u_smoothing, dist);
    gl_FragColor = vec4(u_color, alpha);
}
"""


class GLTextSDF(GLText):
    """Draw higher-quality scalable text using an SDF texture atlas."""

    def __init__(
        self,
        text: str,
        dest_rect=None,
        color: Sequence[float] = (255, 255, 255),
        pixel_size: float = 4.0,
        line_spacing: float = 2.0,
        glyph_spacing: float = 1.0,
        align: str = "center",
        vertical_align: str = "center",
        sdf_scale: int = 8,
        sdf_padding: int = 6,
        sdf_spread: float = 10.0,
        smoothing: float = 0.10,
    ):
        """Create an SDF text renderer with atlas and shader parameters."""
        super().__init__(
            text=text,
            dest_rect=dest_rect,
            color=color,
            pixel_size=pixel_size,
            line_spacing=line_spacing,
            glyph_spacing=glyph_spacing,
            align=align,
            vertical_align=vertical_align,
        )
        self.sdf_scale = int(sdf_scale)
        self.sdf_padding = int(sdf_padding)
        self.sdf_spread = float(sdf_spread)
        self.smoothing = float(smoothing)

        self._program: Optional[int] = None
        self._atlas_tex: Optional[int] = None
        self._atlas_uv: Dict[str, Tuple[float, float, float, float]] = {}
        self._atlas_glyph_size: Dict[str, Tuple[float, float]] = {}

        self._build_atlas()
        self._build_program()

    @staticmethod
    def _glyph_binary(ch: str, scale: int, padding: int) -> np.ndarray:
        """Rasterize a bitmap glyph into a padded high-resolution binary mask."""
        glyph = GLYPH_BITMAPS.get(ch, GLYPH_BITMAPS.get(ch.upper(), GLYPH_BITMAPS["?"]))
        gh = len(glyph)
        gw = len(glyph[0])
        h = gh * scale + 2 * padding
        w = gw * scale + 2 * padding
        mask = np.zeros((h, w), dtype=bool)
        for r, row in enumerate(glyph):
            for c, bit in enumerate(row):
                if bit != "1":
                    continue
                y0 = padding + r * scale
                x0 = padding + c * scale
                mask[y0:y0 + scale, x0:x0 + scale] = True
        return mask

    @staticmethod
    def _signed_distance(mask: np.ndarray) -> np.ndarray:
        """Compute signed distance (positive inside, negative outside) for a mask."""
        h, w = mask.shape
        yy, xx = np.mgrid[0:h, 0:w]
        points = np.stack([yy.ravel(), xx.ravel()], axis=1)

        fg = np.argwhere(mask)
        bg = np.argwhere(~mask)

        if len(fg) == 0:
            return -np.ones((h, w), dtype=np.float32)
        if len(bg) == 0:
            return np.ones((h, w), dtype=np.float32)

        d2_fg = ((points[:, None, :] - fg[None, :, :]) ** 2).sum(axis=2)
        d2_bg = ((points[:, None, :] - bg[None, :, :]) ** 2).sum(axis=2)

        dist_fg = np.sqrt(d2_fg.min(axis=1)).reshape(h, w)
        dist_bg = np.sqrt(d2_bg.min(axis=1)).reshape(h, w)

        # Positive inside, negative outside.
        return (dist_bg - dist_fg).astype(np.float32)

    @staticmethod
    def _to_sdf_texture(signed_distance: np.ndarray, spread: float) -> np.ndarray:
        """Map signed distances to [0, 255] SDF texel intensities."""
        sdf = np.clip(0.5 + signed_distance / (2.0 * spread), 0.0, 1.0)
        return np.uint8(np.round(sdf * 255.0))

    def _build_atlas(self):
        """Build and upload a packed SDF atlas for supported glyphs."""
        chars = sorted(GLYPH_BITMAPS.keys())
        sdf_tiles: List[Tuple[str, np.ndarray]] = []

        for ch in chars:
            mask = self._glyph_binary(ch, self.sdf_scale, self.sdf_padding)
            signed = self._signed_distance(mask)
            tex = self._to_sdf_texture(signed, self.sdf_spread)
            sdf_tiles.append((ch, tex))

        tile_h = max(tile.shape[0] for _, tile in sdf_tiles)
        tile_w = max(tile.shape[1] for _, tile in sdf_tiles)

        cols = 16
        rows = (len(sdf_tiles) + cols - 1) // cols

        atlas_h = rows * tile_h
        atlas_w = cols * tile_w
        atlas = np.zeros((atlas_h, atlas_w), dtype=np.uint8)

        for idx, (ch, tile) in enumerate(sdf_tiles):
            r = idx // cols
            c = idx % cols
            y0 = r * tile_h
            x0 = c * tile_w
            atlas[y0:y0 + tile.shape[0], x0:x0 + tile.shape[1]] = tile

            u0 = x0 / atlas_w
            v0 = y0 / atlas_h
            u1 = (x0 + tile.shape[1]) / atlas_w
            v1 = (y0 + tile.shape[0]) / atlas_h
            self._atlas_uv[ch] = (u0, v0, u1, v1)
            self._atlas_glyph_size[ch] = (tile.shape[1] / self.sdf_scale, tile.shape[0] / self.sdf_scale)

        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RED, atlas_w, atlas_h, 0, GL_RED, GL_UNSIGNED_BYTE, atlas)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)
        self._atlas_tex = tex

    def _build_program(self):
        """Compile and link the SDF shader program."""
        vs = glCreateShader(GL_VERTEX_SHADER)
        glShaderSource(vs, _VERTEX_SHADER)
        glCompileShader(vs)
        log = glGetShaderInfoLog(vs)
        if log:
            log_text = log.decode("utf-8", errors="ignore").strip()
            if log_text:
                raise RuntimeError(f"GLTextSDF vertex shader compile error: {log_text}")

        fs = glCreateShader(GL_FRAGMENT_SHADER)
        glShaderSource(fs, _FRAGMENT_SHADER)
        glCompileShader(fs)
        log = glGetShaderInfoLog(fs)
        if log:
            log_text = log.decode("utf-8", errors="ignore").strip()
            if log_text:
                raise RuntimeError(f"GLTextSDF fragment shader compile error: {log_text}")

        prog = glCreateProgram()
        glAttachShader(prog, vs)
        glAttachShader(prog, fs)
        glLinkProgram(prog)
        status = glGetProgramiv(prog, GL_LINK_STATUS)
        if status != GL_TRUE:
            msg = glGetProgramInfoLog(prog).decode("utf-8", errors="ignore")
            raise RuntimeError(f"GLTextSDF program link error: {msg}")

        glDeleteShader(vs)
        glDeleteShader(fs)
        self._program = prog

    def _glyph_uv(self, ch: str) -> Tuple[float, float, float, float]:
        """Return atlas UV coordinates for a glyph, with fallback."""
        if ch in self._atlas_uv:
            return self._atlas_uv[ch]
        upper = ch.upper()
        if upper in self._atlas_uv:
            return self._atlas_uv[upper]
        return self._atlas_uv["?"]

    def draw(self):
        """Draw text using the SDF atlas and shader smoothing."""
        if self._program is None or self._atlas_tex is None:
            return

        lines = self.lines if self.lines else [""]

        line_heights = []
        line_widths = []
        for line in lines:
            w, h = self._measure_line(line)
            line_widths.append(w)
            line_heights.append(h)

        total_height = sum(line_heights) + (len(lines) - 1) * self.line_spacing * self.pixel_size

        if self.dest_rect:
            x1, y1, x2, y2 = self.dest_rect
            rect_w = x2 - x1
            rect_h = y2 - y1
            if self.vertical_align == "top":
                base_y = y1
            elif self.vertical_align == "bottom":
                base_y = y1 + rect_h - total_height
            else:
                base_y = y1 + (rect_h - total_height) / 2.0
        else:
            x1 = 0
            base_y = 0
            rect_w = max(line_widths) if line_widths else 0

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self._atlas_tex)

        glUseProgram(self._program)
        glUniform1i(glGetUniformLocation(self._program, "u_atlas"), 0)
        glUniform1f(glGetUniformLocation(self._program, "u_edge"), 0.5)
        glUniform1f(glGetUniformLocation(self._program, "u_smoothing"), self.smoothing)
        color_loc = glGetUniformLocation(self._program, "u_color")
        glUniform3f(
            color_loc,
            self.color[0] / 255.0,
            self.color[1] / 255.0,
            self.color[2] / 255.0,
        )

        y = base_y
        glBegin(GL_QUADS)
        for line, line_w, line_h in zip(lines, line_widths, line_heights):
            if self.dest_rect:
                if self.align == "left":
                    x = x1
                elif self.align == "right":
                    x = x1 + rect_w - line_w
                else:
                    x = x1 + (rect_w - line_w) / 2.0
            else:
                x = x1

            for idx, ch in enumerate(line):
                u0, v0, u1, v1 = self._glyph_uv(ch)
                left, right, advance = self._glyph_metrics(ch)
                draw_w = max(1.0, (right - left + 1) * self.pixel_size)
                draw_h = self.glyph_h * self.pixel_size

                x2 = x + draw_w
                y2 = y + draw_h

                glTexCoord2f(u0, v1)
                glVertex2f(x, y)
                glTexCoord2f(u1, v1)
                glVertex2f(x2, y)
                glTexCoord2f(u1, v0)
                glVertex2f(x2, y2)
                glTexCoord2f(u0, v0)
                glVertex2f(x, y2)

                x += advance * self.pixel_size
                if idx < len(line) - 1:
                    x += self.glyph_spacing * self.pixel_size

            y += line_h + self.line_spacing * self.pixel_size
        glEnd()

        glUseProgram(0)
        glBindTexture(GL_TEXTURE_2D, 0)

    def delete(self):
        """Release OpenGL resources owned by this SDF text object."""
        if self._atlas_tex:
            glDeleteTextures([self._atlas_tex])
            self._atlas_tex = None
        if self._program:
            glDeleteProgram(self._program)
            self._program = None
