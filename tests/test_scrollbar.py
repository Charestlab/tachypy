import pytest

import tachypy.scrollbar as scrollbar_module
from tachypy.scrollbar import Scrollbar


class FakeText:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def draw(self):
        return None


def test_scrollbar_mouse_clamp_and_value(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100, position_y=200)

    moved = sb.handle_mouse(mouse_x=10_000, mouse_y=200)
    assert moved is True
    assert sb.mobile_line_x == pytest.approx(sb.max_x)
    assert sb.get_value() == pytest.approx(100.0)


def test_scrollbar_ignore_mouse_when_far_in_y(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600)
    before = sb.mobile_line_x

    moved = sb.handle_mouse(mouse_x=500, mouse_y=999)
    assert moved is False
    assert sb.mobile_line_x == before


def test_scrollbar_set_value_and_normalized_value(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100)
    sb.set_value(25)
    assert sb.get_value() == pytest.approx(25.0)

    sb.set_normalized_value(2.0)
    assert sb.get_normalized_value() == pytest.approx(1.0)
