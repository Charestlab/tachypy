import pytest

import tachypy.screen as screen_module
from fake_glfw import FakeGlfw
from tachypy.screen import Screen


def test_normalize_rgb_color_converts_to_unit_range():
    result = Screen._normalize_rgb_color((255, 128, 0))
    assert result == pytest.approx((1.0, 128 / 255.0, 0.0))


def test_normalize_rgb_color_rejects_bad_shapes():
    with pytest.raises(ValueError):
        Screen._normalize_rgb_color((1, 2))


def test_sleep_duration_for_remaining_ns_behavior():
    assert Screen._sleep_duration_for_remaining_ns(-1) is None
    assert Screen._sleep_duration_for_remaining_ns(0) is None
    assert Screen._sleep_duration_for_remaining_ns(1_000_000) is None
    assert Screen._sleep_duration_for_remaining_ns(6_000_000) == 0.001


def test_screen_rejects_unknown_backend():
    with pytest.raises(ValueError, match="backend"):
        Screen(backend="unknown-backend")


def test_screen_rejects_pygame_backend():
    with pytest.raises(ValueError, match="Pygame support has been removed"):
        Screen(backend="pygame")


def test_screen_rejects_negative_warmup_frames():
    with pytest.raises(ValueError, match="warmup_frames"):
        Screen(backend="glfw", warmup_frames=-1)


def test_warm_up_display_flips_neutral_frames_and_resets_timing():
    calls = []
    screen = Screen.__new__(Screen)
    screen.warmup_frames = 3
    screen.warmup_color = (128, 128, 128)
    screen.last_flip_time = 10
    screen.prev_flip_time = 5
    screen.last_flip_submit_time = 9
    screen.prev_flip_submit_time = 4
    screen._last_tick_time_ns = 1
    screen.fill = lambda color: calls.append(("fill", color))
    screen.flip = lambda: calls.append(("flip", None))

    screen._warm_up_display()

    assert calls == [
        ("fill", (128, 128, 128)),
        ("flip", None),
        ("fill", (128, 128, 128)),
        ("flip", None),
        ("fill", (128, 128, 128)),
        ("flip", None),
    ]
    assert screen.last_flip_time is None
    assert screen.prev_flip_time is None
    assert screen.last_flip_submit_time is None
    assert screen.prev_flip_submit_time is None
    assert screen._last_tick_time_ns is None


def test_glfw_flip_timestamps_before_housekeeping(monkeypatch):
    calls = []
    times = iter([100, 200])
    fake_glfw = FakeGlfw()

    screen = Screen.__new__(Screen)
    screen.backend = "glfw"
    screen._glfw = fake_glfw
    screen._glfw_window = "window"
    screen.last_flip_time = 50
    screen.prev_flip_time = None
    screen.last_flip_submit_time = 40
    screen.prev_flip_submit_time = None
    screen._sync_glfw_viewport_and_projection = lambda: calls.append("sync")
    screen.tick = lambda: calls.append("tick")

    def fake_monotonic_ns():
        value = next(times)
        calls.append(f"time:{value}")
        return value

    monkeypatch.setattr(screen_module, "monotonic_ns", fake_monotonic_ns)

    assert screen.flip() == 200
    assert screen.prev_flip_submit_time == 40
    assert screen.last_flip_submit_time == 100
    assert screen.prev_flip_time == 50
    assert screen.last_flip_time == 200
    assert calls == ["time:100", "time:200", "sync", "tick"]
    assert fake_glfw.swap_count == 1
    assert fake_glfw.poll_count == 0


def test_poll_events_delegates_to_glfw_only():
    fake_glfw = FakeGlfw()
    screen = Screen.__new__(Screen)
    screen._glfw = fake_glfw
    screen._glfw_window = "window"

    screen.poll_events()

    assert fake_glfw.poll_count == 1


def test_clamp_screen_number_warns_when_out_of_range():
    with pytest.warns(UserWarning, match="screen_number=5"):
        result = Screen._clamp_screen_number(5, 2)
    assert result == 0


def test_clamp_screen_number_no_warning_when_valid(recwarn):
    result = Screen._clamp_screen_number(1, 3)
    assert result == 1
    assert len(recwarn) == 0


def test_clamp_screen_number_negative_clamps_silently_to_zero(recwarn):
    result = Screen._clamp_screen_number(-1, 2)
    assert result == 0
    assert len(recwarn) == 0
