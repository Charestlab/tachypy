"""Texture-backed text helpers implemented with Pillow and OpenGL."""

from __future__ import annotations

import warnings

from OpenGL.GL import (
    GL_BLEND,
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_REPLACE,
    GL_RGBA,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    GL_TEXTURE_ENV,
    GL_TEXTURE_ENV_MODE,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glBlendFunc,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glTexCoord2f,
    glTexEnvf,
    glTexImage2D,
    glTexParameterf,
    glVertex2f,
)


class LegacyText:
    """OpenGL text object that renders text to a Pillow-backed texture."""

    def __init__(
        self,
        text,
        font_name="Helvetica",
        font_size=24,
        color=(255, 255, 255),
        dest_rect=None,
        line_spacing=4,
        backend="auto",
    ):
        """Create a text texture, optionally wrapping it inside ``dest_rect``."""
        self._font_available = True
        self._warned_font_unavailable = False
        self.backend = str(backend).lower()
        if self.backend not in {"auto", "pillow"}:
            raise ValueError("Text backend must be 'auto' or 'pillow'.")
        self._pil_image = None
        self._pil_draw = None
        self._pil_imagefont = None
        self._font_obj = None
        self._surface_data = None
        self.texture_width = 0
        self.texture_height = 0
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.dest_rect = dest_rect
        self.texture_id = None
        self.surface = None
        self.line_spacing = line_spacing

        self._init_text_backend()
        self.lines = []
        self._split_text_into_lines()
        self._generate_surface()

    def _init_text_backend(self):
        """Initialize Pillow font rendering."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            self._pil_image = Image
            self._pil_draw = ImageDraw
            self._pil_imagefont = ImageFont
            self._font_obj = self._load_pillow_font()
        except Exception as err:
            if self.backend == "pillow":
                raise RuntimeError(f"pillow text backend unavailable: {err}") from err
            self._font_available = False
            warnings.warn(
                "No text backend available. Install Pillow to use texture-backed text.",
                RuntimeWarning,
                stacklevel=2,
            )

    def _load_pillow_font(self):
        """Load the requested Pillow font or fall back to the default font."""
        try:
            return self._pil_imagefont.truetype(self.font_name, self.font_size)
        except Exception:
            return self._pil_imagefont.load_default()

    def _measure_text(self, text_value):
        """Measure text dimensions in pixels."""
        scratch = self._pil_image.new("RGBA", (1, 1), (0, 0, 0, 0))
        drawer = self._pil_draw.Draw(scratch)
        bbox = drawer.textbbox((0, 0), text_value if text_value else " ", font=self._font_obj)
        width = max(1, int(bbox[2] - bbox[0]))
        height = max(1, int(bbox[3] - bbox[1]))
        return width, height

    def _split_text_into_lines(self):
        """Split text into lines that fit within ``dest_rect`` width."""
        if not self._font_available or not self.dest_rect:
            self.lines = self.text.splitlines() or [self.text]
            if not self.lines:
                self.lines = [""]
            return

        max_width = self.dest_rect[2] - self.dest_rect[0]
        self.lines = []
        raw_lines = self.text.splitlines() or [""]
        for raw_line in raw_lines:
            if raw_line == "":
                self.lines.append("")
                continue
            words = raw_line.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                if self._measure_text(test_line)[0] <= max_width or line == "":
                    line = test_line
                else:
                    self.lines.append(line)
                    line = word
            if line:
                self.lines.append(line)

    def _generate_surface(self):
        """Render the current lines to RGBA bytes and upload an OpenGL texture."""
        if not self._font_available:
            self.surface = None
            self.texture_id = None
            self._surface_data = None
            self.texture_width = 0
            self.texture_height = 0
            return

        lines = self.lines if self.lines else [""]
        line_sizes = [self._measure_text(line if line else " ") for line in lines]
        max_width = max(width for width, _ in line_sizes)
        total_height = sum(height for _, height in line_sizes) + (len(line_sizes) - 1) * self.line_spacing

        image = self._pil_image.new("RGBA", (max_width, total_height), (0, 0, 0, 0))
        drawer = self._pil_draw.Draw(image)
        y_offset = 0
        for line, (_, height) in zip(lines, line_sizes):
            drawer.text((0, y_offset), line if line else " ", fill=tuple(self.color) + (255,), font=self._font_obj)
            y_offset += height + self.line_spacing

        image = image.transpose(self._pil_image.FLIP_TOP_BOTTOM)
        self.texture_width, self.texture_height = image.size
        self._surface_data = image.tobytes("raw", "RGBA")
        self._generate_texture()

    def _generate_texture(self):
        """Upload text bytes as an OpenGL texture."""
        if self._surface_data is None or self.texture_width <= 0 or self.texture_height <= 0:
            return
        if self.texture_id:
            glDeleteTextures([self.texture_id])

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            self.texture_width,
            self.texture_height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            self._surface_data,
        )
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

    def draw(self):
        """Draw the text texture centered in ``dest_rect``."""
        if not self._font_available or self.texture_width <= 0 or self.texture_height <= 0 or self.texture_id is None:
            if not self._warned_font_unavailable:
                warnings.warn("Text.draw() skipped because font backend is unavailable.", RuntimeWarning, stacklevel=2)
                self._warned_font_unavailable = True
            return
        if not self.dest_rect:
            raise ValueError("dest_rect must be set to draw text.")

        x1, y1, x2, y2 = self.dest_rect
        center_x = x1 + (x2 - x1) // 2
        center_y = y1 + (y2 - y1) // 2
        x_start = center_x - self.texture_width // 2
        y_start = center_y - self.texture_height // 2

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 1)
        glVertex2f(x_start, y_start)
        glTexCoord2f(1, 1)
        glVertex2f(x_start + self.texture_width, y_start)
        glTexCoord2f(1, 0)
        glVertex2f(x_start + self.texture_width, y_start + self.texture_height)
        glTexCoord2f(0, 0)
        glVertex2f(x_start, y_start + self.texture_height)
        glEnd()

        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)

    def set_text(self, new_text):
        """Update text content and regenerate the texture."""
        self.text = new_text
        self._split_text_into_lines()
        self._generate_surface()

    def set_dest_rect(self, dest_rect):
        """Update destination rectangle and regenerate wrapped lines."""
        self.dest_rect = dest_rect
        self._split_text_into_lines()
        self._generate_surface()

    def delete(self):
        """Delete the OpenGL texture associated with this text object."""
        if self.texture_id:
            glDeleteTextures([self.texture_id])
            self.texture_id = None


from tachypy.glsystemtext import GLSystemText

Text = GLSystemText
