import doctest

import pytest

import tachypy.scrollbar as scrollbar_module
from tachypy.scrollbar import Scrollbar


class FakeText:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def draw(self):
        return None


class FakeScreen:
    width = 800
    height = 600
    content_scale = 1.0

    def fill(self, color):
        return None

    def flip(self):
        return None


class FakeResponseHandler:
    def __init__(self):
        self.calls = 0

    def clear_events(self):
        return None

    def get_events(self):
        self.calls += 1

    def get_mouse_position(self):
        return (300, 200)

    def get_mouse_clicks(self):
        if self.calls < 2:
            return []
        return [{"type": "mouseup"}]


def test_scrollbar_docstring_example_runs(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)
    monkeypatch.setattr(scrollbar_module.Line, "draw", lambda self: None)

    globs = {
        "Scrollbar": Scrollbar,
        "screen": FakeScreen(),
        "response_handler": FakeResponseHandler(),
    }
    tests = doctest.DocTestFinder().find(Scrollbar, globs=globs)
    runner = doctest.DocTestRunner()
    for test in tests:
        runner.run(test)

    assert runner.failures == 0


def test_scrollbar_mouse_clamp_and_value(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100, position_y=200)

    moved = sb.handle_mouse(mouse_x=10_000, mouse_y=200)
    assert moved is True
    assert sb.mobile_line_x == pytest.approx(sb.max_x)
    assert sb.get_value() == pytest.approx(100.0)


def test_scrollbar_ignore_mouse_when_far_in_y(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, limit_mouse=True)
    before = sb.mobile_line_x

    moved = sb.handle_mouse(mouse_x=500, mouse_y=999)
    assert moved is False
    assert sb.mobile_line_x == before


def test_scrollbar_allows_mouse_far_in_y_when_limit_disabled(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, limit_mouse=False)

    moved = sb.handle_mouse(mouse_x=500, mouse_y=999)
    assert moved is True
    assert sb.mobile_line_x == pytest.approx(500.0)


def test_scrollbar_set_value_and_normalized_value(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100)
    sb.set_value(25)
    assert sb.get_value() == pytest.approx(25.0)

    sb.set_normalized_value(2.0)
    assert sb.get_normalized_value() == pytest.approx(1.0)
