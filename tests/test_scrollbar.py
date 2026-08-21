import doctest

import pytest

import tachypy.scrollbar as scrollbar_module
from tachypy.scrollbar import Scrollbar


class FakeText:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.text = kwargs.get("text")
        self.dest_rect = kwargs.get("dest_rect")

    def draw(self):
        return None

    def set_text(self, new_text):
        self.text = new_text

    def set_dest_rect(self, dest_rect):
        self.dest_rect = dest_rect


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
        if self.calls > 50:
            raise AssertionError("loop did not terminate after a mouseup was available")

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


def test_scrollbar_rejects_negative_notch_label_every(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    with pytest.raises(ValueError, match="notch_label_every"):
        Scrollbar(screen_width=800, screen_height=600, notch_label_every=-1)


def test_scrollbar_rejects_notch_labels_combined_with_value_label(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    with pytest.raises(ValueError, match="overlap"):
        Scrollbar(
            screen_width=800, screen_height=600,
            notch_label_every=2, show_value_label=True,
        )


def test_scrollbar_no_notch_labels_by_default(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, num_marks=11)
    assert sb.notch_labels == []


def test_scrollbar_notch_labels_skip_extremities_and_use_value_scale(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, num_marks=11, notch_label_every=2)
    # Marks 0 and 10 (the extremities) are excluded even though 0 % 2 == 0 and 10 % 2 == 0.
    assert [label.text for label in sb.notch_labels] == ["20", "40", "60", "80"]


def test_scrollbar_notch_label_font_is_scaled_down(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(
        screen_width=800, screen_height=600, num_marks=11,
        notch_label_every=2, font_size=20, notch_label_font_scale=0.5,
    )
    assert all(label.kwargs["font_size"] == 10 for label in sb.notch_labels)
    assert all(label.kwargs["color"] == sb.text_color for label in sb.notch_labels)
    assert all(label.kwargs["font_name"] == sb.font_name for label in sb.notch_labels)


def test_scrollbar_value_label_disabled_by_default(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600)
    assert sb.value_label is None


def test_scrollbar_value_label_tracks_marker_and_shows_integer_value(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", FakeText)

    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100, show_value_label=True)
    assert sb.value_label.text == "50"

    sb.set_value(33.7)
    assert sb.value_label.text == "34"
    assert sb.value_label.dest_rect == sb._value_label_rect()
