"""Text layout and glyph upload contracts without depending on installed fonts."""

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

import tachypy._warnings as warnings_module
import tachypy.text as text_module
from tachypy.text import Text, _GlyphTexture


@pytest.fixture
def renderer(monkeypatch):
    text = Text.__new__(Text)
    text.text = "A"
    text.dest_rect = [10, 20, 110, 70]
    text.align = "left"
    text.vertical_align = "top"
    text.color = (255, 128, 0)
    text._content_scale = 1
    text._line_height = 12
    text._glyph_cache = {}
    text._face = Mock()
    text._face.glyph = SimpleNamespace(
        bitmap=SimpleNamespace(width=2, rows=2, pitch=3, buffer=[1, 2, 99, 3, 4, 99]),
        bitmap_left=1, bitmap_top=2,
    )
    calls = Mock()
    for name in ("glGenTextures", "glBindTexture", "glTexImage2D", "glTexParameterf", "glEnable",
                 "glDisable", "glBlendFunc", "glColor3f", "glBegin", "glEnd", "glVertex2f",
                 "glTexCoord2f", "glDeleteTextures"):
        monkeypatch.setattr(text_module, name, getattr(calls, name))
    calls.glGenTextures.return_value = 17
    return text, calls


def test_glyph_upload_strips_row_padding_and_caches_texture(renderer):
    text, calls = renderer
    glyph = text._glyph_texture(42)
    assert (glyph.texture_id, glyph.width, glyph.height, glyph.bearing_x, glyph.bearing_y) == (17, 2, 2, 1, 2)
    pixels = calls.glTexImage2D.call_args.args[-1]
    np.testing.assert_array_equal(pixels[:, :, :3], np.full((2, 2, 3), 255))
    np.testing.assert_array_equal(pixels[:, :, 3], [[1, 2], [3, 4]])
    assert text._glyph_texture(42) is glyph
    text._face.load_glyph.assert_called_once_with(42, text_module.freetype.FT_LOAD_RENDER)
    calls.glGenTextures.assert_called_once()
    text.delete()
    text.delete()
    calls.glDeleteTextures.assert_called_once_with([17])
    assert text._glyph_cache == {}


def test_empty_glyph_uploads_one_transparent_pixel(renderer):
    text, calls = renderer
    text._face.glyph.bitmap = SimpleNamespace(width=0, rows=0, pitch=0, buffer=[])
    glyph = text._glyph_texture(1)
    assert (glyph.width, glyph.height) == (1, 1)
    np.testing.assert_array_equal(calls.glTexImage2D.call_args.args[-1], [[[255, 255, 255, 0]]])


@pytest.mark.parametrize("horizontal,x", [("left", 10), ("center", 57), ("right", 104)])
@pytest.mark.parametrize("vertical,y", [("top", 20), ("center", 40), ("bottom", 60)])
def test_glyph_quads_align_with_destination_bounds(renderer, monkeypatch, horizontal, x, vertical, y):
    text, calls = renderer
    text.align, text.vertical_align = horizontal, vertical
    monkeypatch.setattr(text, "_shape", lambda line: (
        [SimpleNamespace(codepoint=1)], [SimpleNamespace(x_advance=6 * 64, x_offset=0, y_offset=0)]))
    monkeypatch.setattr(text, "_glyph_texture", lambda index: _GlyphTexture(17, 6, 10, 0, 8))
    text.draw()
    assert [c.args for c in calls.glVertex2f.call_args_list] == [(x, y), (x + 6, y), (x + 6, y + 10), (x, y + 10)]
    assert [c.args for c in calls.glTexCoord2f.call_args_list] == [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert calls.glColor3f.call_args.args == pytest.approx((1, 128 / 255, 0))
    assert calls.glBindTexture.call_args.args == (text_module.GL_TEXTURE_2D, 0)


def test_text_update_reuses_glyph_cache_and_wraps_at_word_boundaries(renderer, monkeypatch):
    text, _ = renderer
    text._glyph_cache[1] = _GlyphTexture(17, 6, 10, 0, 8)
    monkeypatch.setattr(text, "_measure_line", lambda value: len(value) * 5)
    text.set_text("aa bb cc\n\naa")
    text.set_dest_rect([0, 0, 25, 50])
    assert text._split_lines() == ["aa bb", "cc", "", "aa"]
    assert 1 in text._glyph_cache
    text.set_dest_rect(None)
    assert text._split_lines() == ["aa bb cc", "", "aa"]
    text.set_text("")
    assert text._split_lines() == [""]


def test_empty_lines_and_measurements(renderer):
    text, _ = renderer
    assert text._measure_line("") == 0
    assert text._line_bounds("") == (0, 0, 0)


def test_text_without_rectangle_draws_from_origin(renderer, monkeypatch):
    text, calls = renderer
    text.dest_rect = None
    monkeypatch.setattr(text, "_shape", lambda line: (
        [SimpleNamespace(codepoint=1)], [SimpleNamespace(x_advance=6 * 64, x_offset=0, y_offset=0)]))
    monkeypatch.setattr(text, "_glyph_texture", lambda index: _GlyphTexture(17, 6, 10, 0, 8))
    text.draw()
    assert calls.glVertex2f.call_args_list[0].args == (0, 0)


def test_vertical_overflow_warns_without_changing_glyph_geometry(renderer, monkeypatch, capsys):
    text, calls = renderer
    text.dest_rect = [0, 0, 10, 5]
    monkeypatch.setattr(warnings_module, "_warned", set())
    monkeypatch.setattr(text, "_shape", lambda line: (
        [SimpleNamespace(codepoint=1)], [SimpleNamespace(x_advance=6 * 64, x_offset=0, y_offset=0)]))
    monkeypatch.setattr(text, "_glyph_texture", lambda index: _GlyphTexture(17, 6, 10, 0, 8))
    text.draw()
    assert "taller than dest_rect" in capsys.readouterr().err
    assert calls.glVertex2f.call_args_list[-1].args == (0, 10)


def test_font_cache_can_be_invalidated(monkeypatch):
    calls = []
    @lru_cache(maxsize=1)
    def discover():
        calls.append(True)
        return (Path("Example.ttf"),)
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(discover))
    assert Text.resolve_font_path("Example") == Path("Example.ttf")
    Text.resolve_font_path("Example")
    assert len(calls) == 1
    Text.clear_font_cache()
    Text.resolve_font_path("Example")
    assert len(calls) == 2


def test_font_resolution_handles_empty_and_tokenless_queries(monkeypatch):
    assert Text.resolve_font_path("") is None
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(lambda: ()))
    assert Text.resolve_font_path("Missing") is None
    monkeypatch.setattr(Text, "_iter_system_font_files", staticmethod(lambda: (Path("Unrelated.ttf"),)))
    assert Text.resolve_font_path(", ,") is None
    assert not Text._font_path_matches_query(Path("Unrelated.ttf"), "!!!")
