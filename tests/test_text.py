import pytest

import tachypy._warnings as warnings_module
import tachypy.text as text_module
from tachypy import Text as TopLevelText
from tachypy.text import Text
from pathlib import Path
from types import SimpleNamespace


def test_top_level_text_is_the_same_class():
    assert TopLevelText is Text


def test_public_text_warns_when_a_word_cannot_be_broken(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(
        Text,
        "resolve_font_path",
        staticmethod(lambda font_name: Path("/tmp/A.ttf")),
    )
    monkeypatch.setattr(Text, "_init_system_font", lambda self, font_path: None)

    # Every single word alone (>2 chars * 10px each) already exceeds the
    # 20px-wide rect, so wrapping can't fix it -- a genuine overflow.
    text = Text("one two three four", dest_rect=[0, 0, 20, 80], font_name="A")
    monkeypatch.setattr(text, "_measure_line", lambda line: float(len(line) * 10))

    text._split_lines()

    message = capsys.readouterr().err
    assert "Text layout" in message
    assert "one two three four" in message
    assert "can't be broken" in message


def test_public_text_does_not_warn_when_wrapping_resolves_it(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(
        Text,
        "resolve_font_path",
        staticmethod(lambda font_name: Path("/tmp/A.ttf")),
    )
    monkeypatch.setattr(Text, "_init_system_font", lambda self, font_path: None)

    # The full sentence is wider than the rect, but each individual word
    # (<= 40px) fits within it (100px) -- wrapping resolves this cleanly,
    # no information is lost, so this should not warn.
    text = Text("one two three four", dest_rect=[0, 0, 100, 80], font_name="A")
    monkeypatch.setattr(text, "_measure_line", lambda line: float(len(line) * 10))

    lines = text._split_lines()

    assert len(lines) > 1  # actually wrapped
    message = capsys.readouterr().err
    assert message == ""


def test_text_layout_warning_truncates_long_text_preview(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(
        Text,
        "resolve_font_path",
        staticmethod(lambda font_name: Path("/tmp/A.ttf")),
    )
    monkeypatch.setattr(Text, "_init_system_font", lambda self, font_path: None)

    long_text = "word " * 30
    text = Text(long_text, dest_rect=[0, 0, 20, 80], font_name="A")
    monkeypatch.setattr(text, "_measure_line", lambda line: float(len(line) * 10))

    text._split_lines()

    message = capsys.readouterr().err
    assert "..." in message
    assert long_text not in message  # full text should not be dumped verbatim


def test_text_raises_when_deps_unavailable(monkeypatch):
    monkeypatch.setattr(text_module, "HAS_FREETYPE", False)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", False)

    with pytest.raises(RuntimeError, match="freetype-py.*uharfbuzz"):
        Text("hello", dest_rect=[0, 0, 100, 50], font_name="Avenir")


def test_text_raises_when_font_not_found_anywhere(monkeypatch):
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(Text, "resolve_font_path", staticmethod(lambda font_name: None))

    with pytest.raises(FileNotFoundError, match="Nonexistent Font"):
        Text("hello", dest_rect=[0, 0, 100, 50], font_name="Nonexistent Font")


def test_text_raises_when_font_init_fails(monkeypatch):
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(Text, "resolve_font_path", staticmethod(lambda font_name: Path("/tmp/fake.ttf")))

    def raising_init(self, font_path):
        raise OSError("corrupt font")

    monkeypatch.setattr(Text, "_init_system_font", raising_init)

    with pytest.raises(RuntimeError, match="couldn't load it"):
        Text("hello", dest_rect=[0, 0, 100, 50], font_name="Corrupt Font")


def test_text_warns_when_last_resort_font_is_used(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(Text, "resolve_font_path", staticmethod(lambda font_name: Path("/tmp/Arial.ttf")))
    monkeypatch.setattr(Text, "_init_system_font", lambda self, font_path: None)

    Text("hello", dest_rect=[0, 0, 100, 50], font_name="Missing Typeface")

    message = capsys.readouterr().err
    assert "'Missing Typeface' isn't available on this system" in message
    assert "Arial.ttf" in message


@pytest.mark.parametrize("content_scale", [0, -1, float("nan")])
def test_text_rejects_invalid_content_scale(content_scale):
    with pytest.raises(ValueError, match="content_scale"):
        Text("hello", content_scale=content_scale)


def test_text_last_resort_warning_fires_only_once(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text_module, "HAS_FREETYPE", True)
    monkeypatch.setattr(text_module, "HAS_HARFBUZZ", True)
    monkeypatch.setattr(Text, "resolve_font_path", staticmethod(lambda font_name: Path("/tmp/Arial.ttf")))
    monkeypatch.setattr(Text, "_init_system_font", lambda self, font_path: None)

    Text("first", dest_rect=[0, 0, 100, 50], font_name="Missing Typeface")
    Text("second", dest_rect=[0, 0, 100, 50], font_name="Missing Typeface")

    message = capsys.readouterr().err
    assert message.count("[TachyPy WARNING]: Text font resolution") == 1


def test_resolve_font_path_accepts_direct_path(tmp_path):
    font_file = tmp_path / "MyFont-Regular.ttf"
    font_file.write_bytes(b"fake-font")

    resolved = Text.resolve_font_path(str(font_file))
    assert resolved == font_file


def test_resolve_font_path_uses_best_token_match(monkeypatch):
    fake_fonts = [
        Path("/tmp/Arial.ttf"),
        Path("/tmp/HelveticaNeue-Bold.ttf"),
        Path("/tmp/TimesNewRoman.ttf"),
    ]
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(lambda: fake_fonts))

    resolved = Text.resolve_font_path("Helvetica Neue, Arial")
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
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(lambda: fake_fonts))

    assert Text.resolve_font_path("Arial") == Path("/tmp/Arial.ttf")
    assert Text.resolve_font_path("Arial Italic") == Path("/tmp/Arial Italic.ttf")
    assert Text.resolve_font_path("Arial Bold") == Path("/tmp/Arial Bold.ttf")


def test_resolve_font_path_requires_all_requested_tokens(monkeypatch):
    # A common token such as "sans" must not make an unrelated family look
    # like a successful match. Otherwise the fallback warning is suppressed.
    fake_fonts = [
        Path("/tmp/Hiragino Sans GB.ttc"),
        Path("/tmp/Arial.ttf"),
    ]
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(lambda: fake_fonts))

    resolved = Text.resolve_font_path("Foo Sans")

    assert resolved == Path("/tmp/Arial.ttf")
    assert not Text._font_path_matches_query(resolved, "Foo Sans")


def test_font_path_match_rejects_family_suffixes_and_unrequested_styles():
    assert not Text._font_path_matches_query(Path("/tmp/NotoSansOriya.ttc"), "Noto Sans")
    assert not Text._font_path_matches_query(Path("/tmp/Arial Bold.ttf"), "Arial")
    assert Text._font_path_matches_query(Path("/tmp/Arial-Regular.ttf"), "Arial")


def test_draw_skips_blank_lines_without_crashing(monkeypatch):
    # draw() handles a blank line (from "\n\n" or word-wrap) without crashing.
    pytest.importorskip("freetype")
    pytest.importorskip("uharfbuzz")

    text = Text(
        "Line one.\n\nLine two.",
        dest_rect=[0, 0, 500, 300],
        font_name="Arial",
        font_size=32.0,
    )
    assert "" in text._split_lines()

    fake_glyph = text_module._GlyphTexture(texture_id=0, width=1, height=1, bearing_x=0.0, bearing_y=0.0)
    monkeypatch.setattr(text, "_glyph_texture", lambda codepoint: fake_glyph)
    noop = lambda *args, **kwargs: None
    for gl_func in ("glEnable", "glDisable", "glBlendFunc", "glColor3f", "glBindTexture", "glBegin", "glEnd", "glTexCoord2f", "glVertex2f"):
        monkeypatch.setattr(text_module, gl_func, noop)

    text.draw()


def test_draw_centers_actual_glyph_bounds_in_dest_rect(monkeypatch):
    # Vertical centering uses the glyph's rendered bounds, not just ascender/line-height metrics.
    text = Text(
        "g",
        dest_rect=[0, 0, 100, 10],
        font_size=10.0,
    )
    text._content_scale = 1.0
    text._line_height = 10.0

    fake_info = SimpleNamespace(codepoint=1)
    fake_pos = SimpleNamespace(x_advance=9 * 64, x_offset=0, y_offset=0)
    fake_glyph = text_module._GlyphTexture(
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
        monkeypatch.setattr(text_module, gl_func, noop)
    monkeypatch.setattr(text_module, "glVertex2f", capture_vertex)

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
    text = Text("i", dest_rect=[0, 0, 100, 10], font_size=10.0)
    text._content_scale = 1.0
    text._line_height = 10.0

    fake_glyph = text_module._GlyphTexture(
        texture_id=0, width=3, height=10, bearing_x=0.0, bearing_y=5.0,
    )
    monkeypatch.setattr(text, "_glyph_texture", lambda codepoint: fake_glyph)

    noop = lambda *args, **kwargs: None
    for gl_func in ("glEnable", "glDisable", "glBlendFunc", "glColor3f", "glBindTexture", "glBegin", "glEnd", "glTexCoord2f"):
        monkeypatch.setattr(text_module, gl_func, noop)

    # Sweep pen position across a full pixel to cover every subpixel offset.
    for offset in [i / 10.0 for i in range(11)]:
        fake_info = SimpleNamespace(codepoint=1)
        fake_pos = SimpleNamespace(x_advance=3 * 64, x_offset=int(offset * 64), y_offset=0)
        monkeypatch.setattr(text, "_shape", lambda line, fp=fake_pos, fi=fake_info: ([fi], [fp]))

        vertices = []
        monkeypatch.setattr(text_module, "glVertex2f", lambda x, y: vertices.append((x, y)))

        text.draw()

        x_values = [x for x, _ in vertices]
        width = max(x_values) - min(x_values)
        assert width == pytest.approx(fake_glyph.width), f"offset={offset} width={width}"
