import pytest

import tachypy.glsystemtext as glsys_module
import tachypy.text as text_module
from tachypy.glsystemtext import GLSystemText
from pathlib import Path
from types import SimpleNamespace


class FakeFallback:
    def __init__(self, *args, **kwargs):
        self.text = kwargs.get("text") if "text" in kwargs else (args[0] if args else "")
        self.dest_rect = kwargs.get("dest_rect")
        self.draw_called = False

    def set_text(self, new_text):
        self.text = new_text

    def set_dest_rect(self, dest_rect):
        self.dest_rect = dest_rect

    def draw(self):
        self.draw_called = True

    def delete(self):
        return None


def test_glsystemtext_falls_back_when_deps_unavailable(monkeypatch):
    monkeypatch.setattr(glsys_module, "HAS_FREETYPE", False)
    monkeypatch.setattr(glsys_module, "HAS_HARFBUZZ", False)
    monkeypatch.setattr(glsys_module, "GLText", FakeFallback)

    text = GLSystemText("hello", dest_rect=[0, 0, 100, 50])

    assert text._fallback is not None
    text.draw()
    assert text._fallback.draw_called is True


def test_text_alias_points_to_glsystemtext():
    assert text_module.Text is GLSystemText


def test_glsystemtext_fallback_mutators(monkeypatch):
    monkeypatch.setattr(glsys_module, "HAS_FREETYPE", False)
    monkeypatch.setattr(glsys_module, "HAS_HARFBUZZ", False)
    monkeypatch.setattr(glsys_module, "GLText", FakeFallback)

    text = GLSystemText("start", dest_rect=[0, 0, 100, 50])
    text.set_text("next")
    text.set_dest_rect([10, 10, 120, 70])

    assert text._fallback.text == "next"
    assert text._fallback.dest_rect == [10, 10, 120, 70]


def test_resolve_font_path_accepts_direct_path(tmp_path):
    font_file = tmp_path / "MyFont-Regular.ttf"
    font_file.write_bytes(b"fake-font")

    resolved = GLSystemText.resolve_font_path(str(font_file))
    assert resolved == font_file


def test_resolve_font_path_uses_best_token_match(monkeypatch):
    fake_fonts = [
        Path("/tmp/Arial.ttf"),
        Path("/tmp/HelveticaNeue-Bold.ttf"),
        Path("/tmp/TimesNewRoman.ttf"),
    ]
    monkeypatch.setattr(GLSystemText, "_iter_system_font_files", staticmethod(lambda: fake_fonts))

    resolved = GLSystemText.resolve_font_path("Helvetica Neue, Arial")
    assert resolved == Path("/tmp/HelveticaNeue-Bold.ttf")


def test_resolve_font_path_prefers_regular_over_unrequested_style_variants(monkeypatch):
    # A plain family query resolves to the regular variant, not bold/italic.
    fake_fonts = [
        Path("/tmp/Arial Narrow Italic.ttf"),
        Path("/tmp/Arial Bold Italic.ttf"),
        Path("/tmp/Arial Bold.ttf"),
        Path("/tmp/Arial Italic.ttf"),
        Path("/tmp/Arial.ttf"),
    ]
    monkeypatch.setattr(GLSystemText, "_iter_system_font_files", staticmethod(lambda: fake_fonts))

    assert GLSystemText.resolve_font_path("Arial") == Path("/tmp/Arial.ttf")
    assert GLSystemText.resolve_font_path("Arial Italic") == Path("/tmp/Arial Italic.ttf")
    assert GLSystemText.resolve_font_path("Arial Bold") == Path("/tmp/Arial Bold.ttf")


def test_draw_skips_blank_lines_without_crashing(monkeypatch):
    # draw() handles a blank line (from "\n\n" or word-wrap) without crashing.
    pytest.importorskip("freetype")
    pytest.importorskip("uharfbuzz")

    text = GLSystemText(
        "Line one.\n\nLine two.",
        dest_rect=[0, 0, 500, 300],
        font_name="Arial",
        font_size=32.0,
    )
    assert text._enabled, "expected the real freetype+harfbuzz path to be active"
    assert "" in text._split_lines()

    fake_glyph = glsys_module._GlyphTexture(texture_id=0, width=1, height=1, bearing_x=0.0, bearing_y=0.0)
    monkeypatch.setattr(text, "_glyph_texture", lambda codepoint: fake_glyph)
    noop = lambda *args, **kwargs: None
    for gl_func in ("glEnable", "glDisable", "glBlendFunc", "glColor3f", "glBindTexture", "glBegin", "glEnd", "glTexCoord2f", "glVertex2f"):
        monkeypatch.setattr(glsys_module, gl_func, noop)

    text.draw()


def test_draw_centers_actual_glyph_bounds_in_dest_rect(monkeypatch):
    # Vertical centering uses the glyph's rendered bounds, not just ascender/line-height metrics.
    text = GLSystemText(
        "g",
        dest_rect=[0, 0, 100, 10],
        font_size=10.0,
    )
    text._enabled = True
    text._fallback = None
    text._content_scale = 1.0
    text._line_height = 10.0
    text._ascender = 8.0

    fake_info = SimpleNamespace(codepoint=1)
    fake_pos = SimpleNamespace(x_advance=9 * 64, x_offset=0, y_offset=0)
    fake_glyph = glsys_module._GlyphTexture(
        texture_id=0,
        width=9,
        height=10,
        bearing_x=0.0,
        bearing_y=5.0,
    )
    monkeypatch.setattr(text, "_shape", lambda line: ([fake_info], [fake_pos]))
    monkeypatch.setattr(text, "_glyph_texture", lambda codepoint: fake_glyph)

    vertices = []

    def capture_vertex(x, y):
        vertices.append((x, y))

    noop = lambda *args, **kwargs: None
    for gl_func in ("glEnable", "glDisable", "glBlendFunc", "glColor3f", "glBindTexture", "glBegin", "glEnd", "glTexCoord2f"):
        monkeypatch.setattr(glsys_module, gl_func, noop)
    monkeypatch.setattr(glsys_module, "glVertex2f", capture_vertex)

    text.draw()

    x_values = [x for x, _ in vertices]
    y_values = [y for _, y in vertices]
    # Quad width matches the glyph's own bitmap size, not independently rounded edges.
    assert min(x_values) == pytest.approx(46.0)
    assert max(x_values) == pytest.approx(55.0)
    assert max(x_values) - min(x_values) == pytest.approx(fake_glyph.width)
    assert min(y_values) == pytest.approx(0.0)
    assert max(y_values) == pytest.approx(10.0)


def test_draw_preserves_glyph_width_across_half_pixel_boundary(monkeypatch):
    # Glyph width stays constant regardless of subpixel pen position.
    text = GLSystemText("i", dest_rect=[0, 0, 100, 10], font_size=10.0)
    text._enabled = True
    text._fallback = None
    text._content_scale = 1.0
    text._line_height = 10.0
    text._ascender = 8.0

    fake_glyph = glsys_module._GlyphTexture(
        texture_id=0, width=3, height=10, bearing_x=0.0, bearing_y=5.0,
    )
    monkeypatch.setattr(text, "_glyph_texture", lambda codepoint: fake_glyph)

    noop = lambda *args, **kwargs: None
    for gl_func in ("glEnable", "glDisable", "glBlendFunc", "glColor3f", "glBindTexture", "glBegin", "glEnd", "glTexCoord2f"):
        monkeypatch.setattr(glsys_module, gl_func, noop)

    # Sweep pen position across a full pixel to cover every subpixel offset.
    for offset in [i / 10.0 for i in range(11)]:
        fake_info = SimpleNamespace(codepoint=1)
        fake_pos = SimpleNamespace(x_advance=3 * 64, x_offset=int(offset * 64), y_offset=0)
        monkeypatch.setattr(text, "_shape", lambda line, fp=fake_pos, fi=fake_info: ([fi], [fp]))

        vertices = []
        monkeypatch.setattr(glsys_module, "glVertex2f", lambda x, y: vertices.append((x, y)))

        text.draw()

        x_values = [x for x, _ in vertices]
        width = max(x_values) - min(x_values)
        assert width == pytest.approx(fake_glyph.width), f"offset={offset} width={width}"
