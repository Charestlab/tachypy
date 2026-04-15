"""Backend-independent OpenGL bitmap text rendering."""

from typing import Dict, List, Sequence, Tuple

from OpenGL.GL import (
    GL_BLEND,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_QUADS,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    glBegin,
    glBlendFunc,
    glColor3f,
    glDisable,
    glEnable,
    glEnd,
    glVertex2f,
)


# 5x7 bitmap font for common ASCII characters.
GLYPH_BITMAPS: Dict[str, Tuple[str, ...]] = {
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11100", "10010", "10001", "10001", "10001", "10010", "11100"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00110", "00110"),
    ",": ("00000", "00000", "00000", "00000", "00000", "00110", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "?": ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ":": ("00000", "00110", "00110", "00000", "00110", "00110", "00000"),
    ";": ("00000", "00110", "00110", "00000", "00110", "00100", "01000"),
    "'": ("00100", "00100", "00000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "/": ("00001", "00010", "00100", "01000", "10000", "00000", "00000"),
    "\\": ("10000", "01000", "00100", "00010", "00001", "00000", "00000"),
    "+": ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    "=": ("00000", "11111", "00000", "11111", "00000", "00000", "00000"),
    "_": ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    "|": ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    "[": ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    "]": ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    "{": ("00010", "00100", "00100", "01000", "00100", "00100", "00010"),
    "}": ("01000", "00100", "00100", "00010", "00100", "00100", "01000"),
    "<": ("00001", "00010", "00100", "01000", "00100", "00010", "00001"),
    ">": ("10000", "01000", "00100", "00010", "00100", "01000", "10000"),
    "@": ("01110", "10001", "10111", "10101", "10111", "10000", "01110"),
    "#": ("01010", "11111", "01010", "01010", "11111", "01010", "01010"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    "%": ("11001", "11010", "00100", "01000", "10110", "00110", "00000"),
    "^": ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "*": ("00000", "10101", "01110", "11111", "01110", "10101", "00000"),
    "`": ("01000", "00100", "00010", "00000", "00000", "00000", "00000"),
    "~": ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
}

# Backward-compatible alias for internal references.
_GLYPHS = GLYPH_BITMAPS


class GLText:
    """Draw simple bitmap text directly with OpenGL quads."""

    def __init__(
        self,
        text: str,
        dest_rect=None,
        color: Sequence[float] = (255, 255, 255),
        pixel_size: float = 3.0,
        line_spacing: float = 2.0,
        glyph_spacing: float = 1.0,
        align: str = "center",
        vertical_align: str = "center",
    ):
        """Create a bitmap OpenGL text object with rectangle-based layout."""
        self.text = text
        self.dest_rect = dest_rect
        self.color = color
        self.pixel_size = float(pixel_size)
        self.line_spacing = float(line_spacing)
        self.glyph_spacing = float(glyph_spacing)
        self.align = align
        self.vertical_align = vertical_align

        self.glyph_w = 5
        self.glyph_h = 7
        self._glyph_metrics_cache: Dict[str, Tuple[int, int, int]] = {}
        self.lines: List[str] = []
        self._split_text_into_lines()

    def _glyph_metrics(self, ch: str) -> Tuple[int, int, int]:
        """
        Return (left_col, right_col, advance_cols) for a glyph.
        """
        glyph = self._glyph_for_char(ch)
        key = "".join(glyph)
        if key in self._glyph_metrics_cache:
            return self._glyph_metrics_cache[key]

        left = self.glyph_w
        right = -1
        for row in glyph:
            for idx, bit in enumerate(row):
                if bit == "1":
                    left = min(left, idx)
                    right = max(right, idx)

        if right < left:
            # Empty glyph (space).
            result = (0, 0, 3)
        else:
            width = right - left + 1
            result = (left, right, width + 1)
        self._glyph_metrics_cache[key] = result
        return result

    def _measure_line(self, line: str) -> Tuple[float, float]:
        """Return rendered (width, height) for a single line."""
        if not line:
            return self.pixel_size, self.glyph_h * self.pixel_size

        total_cols = 0.0
        for ii, ch in enumerate(line):
            _, _, adv = self._glyph_metrics(ch)
            total_cols += adv
            if ii < len(line) - 1:
                total_cols += self.glyph_spacing

        width = max(self.pixel_size, total_cols * self.pixel_size)
        height = self.glyph_h * self.pixel_size
        return width, height

    def _split_text_into_lines(self):
        """Wrap text into lines that fit destination width when provided."""
        if not self.dest_rect:
            self.lines = self.text.splitlines() or [self.text]
            if not self.lines:
                self.lines = [""]
            return

        max_width = self.dest_rect[2] - self.dest_rect[0]

        self.lines = []
        raw_lines = self.text.splitlines() or [""]
        for raw in raw_lines:
            if raw == "":
                self.lines.append("")
                continue

            words = raw.split()
            current = ""
            for word in words:
                candidate = f"{current} {word}".strip()
                candidate_width, _ = self._measure_line(candidate)
                if candidate_width <= max_width or current == "":
                    current = candidate
                else:
                    self.lines.append(current)
                    current = word
            if current:
                self.lines.append(current)

    def _glyph_for_char(self, ch: str) -> Tuple[str, ...]:
        """Return bitmap glyph rows for a character with fallback."""
        if ch in _GLYPHS:
            return _GLYPHS[ch]
        upper = ch.upper()
        if upper in _GLYPHS:
            return _GLYPHS[upper]
        return _GLYPHS["?"]

    def set_text(self, new_text: str):
        """Update displayed text and recompute line wrapping."""
        self.text = new_text
        self._split_text_into_lines()

    def set_dest_rect(self, dest_rect):
        """Update destination rectangle and recompute line wrapping."""
        self.dest_rect = dest_rect
        self._split_text_into_lines()

    def draw(self):
        """Draw the bitmap text block using immediate-mode OpenGL quads."""
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
        glDisable(GL_TEXTURE_2D)
        glColor3f(self.color[0] / 255.0, self.color[1] / 255.0, self.color[2] / 255.0)

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
                glyph = self._glyph_for_char(ch)
                left, right, advance = self._glyph_metrics(ch)
                for row, bit_row in enumerate(glyph):
                    for col in range(left, right + 1):
                        bit = bit_row[col]
                        if bit != "1":
                            continue
                        px = x + (col - left) * self.pixel_size
                        py = y + row * self.pixel_size
                        p2x = px + self.pixel_size
                        p2y = py + self.pixel_size
                        glVertex2f(px, py)
                        glVertex2f(p2x, py)
                        glVertex2f(p2x, p2y)
                        glVertex2f(px, p2y)
                x += advance * self.pixel_size
                if idx < len(line) - 1:
                    x += self.glyph_spacing * self.pixel_size

            y += line_h + self.line_spacing * self.pixel_size
        glEnd()
