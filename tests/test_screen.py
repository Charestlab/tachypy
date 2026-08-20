import types

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


def test_reports_when_requested_rate_exceeds_display_mode(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = True
    screen.desired_refresh_rate = 240
    screen._max_mode_refresh_rate = 180

    screen._warn_if_requested_rate_exceeds_display()
    message = capsys.readouterr().err
    assert "[TachyPy WARNING]: Screen initialization" in message
    assert "180 Hz" in message
    assert "240 Hz" in message


def test_warning_uses_max_rate_not_a_stale_current_mode(capsys):
    # The current-mode snapshot (60 Hz) can be stale on adaptive-refresh
    # displays; the warning must judge against the true ceiling (144 Hz),
    # not the transient current reading, or it would fire a false positive.
    screen = Screen.__new__(Screen)
    screen.vsync = True
    screen.desired_refresh_rate = 120
    screen._mode_refresh_rate = 60
    screen._max_mode_refresh_rate = 144

    screen._warn_if_requested_rate_exceeds_display()
    assert not capsys.readouterr().err


def test_does_not_report_when_display_mode_is_sufficient(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = True
    screen.desired_refresh_rate = 60
    screen._max_mode_refresh_rate = 180

    screen._warn_if_requested_rate_exceeds_display()
    assert not capsys.readouterr().err


def test_manual_pacing_reports_when_requested_rate_exceeds_display_rate(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = False
    screen.desired_refresh_rate = 240
    screen._max_mode_refresh_rate = 180

    screen._warn_if_requested_rate_exceeds_display()
    message = capsys.readouterr().err
    assert "VSync is disabled" in message
    assert "180 Hz" in message
    assert "240 Hz" in message


def test_reports_when_mode_refresh_rate_is_unknown(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = True
    screen.desired_refresh_rate = None
    screen._max_mode_refresh_rate = None

    screen._warn_if_mode_refresh_rate_unknown()
    message = capsys.readouterr().err
    assert "[TachyPy WARNING]: Screen initialization" in message
    assert "60 Hz guess" in message


def test_does_not_report_unknown_rate_when_mode_rate_is_known(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = True
    screen.desired_refresh_rate = None
    screen._max_mode_refresh_rate = 180

    screen._warn_if_mode_refresh_rate_unknown()
    assert not capsys.readouterr().err


def test_does_not_report_unknown_rate_when_desired_rate_overrides_it(capsys):
    screen = Screen.__new__(Screen)
    screen.vsync = False
    screen.desired_refresh_rate = 60
    screen._max_mode_refresh_rate = None

    screen._warn_if_mode_refresh_rate_unknown()
    assert not capsys.readouterr().err


def test_tick_uses_max_mode_rate_when_manual_rate_is_not_set(monkeypatch):
    screen = Screen.__new__(Screen)
    screen.vsync = False
    screen.desired_refresh_rate = None
    screen._max_mode_refresh_rate = 100
    screen._last_tick_time_ns = None
    times = iter([100, 100, 10_000_100, 10_000_100])
    monkeypatch.setattr(screen_module, "monotonic_ns", lambda: next(times))

    screen.tick()
    screen.tick()

    assert screen._last_tick_time_ns == 10_000_100


def test_tick_is_disabled_by_explicit_zero_desired_rate():
    screen = Screen.__new__(Screen)
    screen.vsync = False
    screen.desired_refresh_rate = 0
    screen._max_mode_refresh_rate = 100
    screen._last_tick_time_ns = None

    screen.tick()

    assert screen._last_tick_time_ns is None


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


def test_flip_intervals_polls_events_every_frame(monkeypatch):
    # Without polling events, some platforms (macOS) stop servicing the
    # window's compositor scheduling and flip() no longer blocks for VSync,
    # silently invalidating this measurement.
    fake_glfw = FakeGlfw()
    screen = Screen.__new__(Screen)
    screen.backend = "glfw"
    screen._glfw = fake_glfw
    screen._glfw_window = "window"
    screen.last_flip_time = None
    screen.prev_flip_time = None
    screen.last_flip_submit_time = None
    screen.prev_flip_submit_time = None
    screen.fill = lambda color: None
    screen._sync_glfw_viewport_and_projection = lambda: None
    screen.tick = lambda: None

    times = iter(range(0, 2_000_000_000, 1_000_000))
    monkeypatch.setattr(screen_module, "monotonic_ns", lambda: next(times))

    screen.test_flip_intervals(num_frames=5)

    assert fake_glfw.poll_count == 5
    assert fake_glfw.swap_count == 5


def test_poll_events_delegates_to_glfw_only():
    fake_glfw = FakeGlfw()
    screen = Screen.__new__(Screen)
    screen._glfw = fake_glfw
    screen._glfw_window = "window"

    screen.poll_events()

    assert fake_glfw.poll_count == 1


class _FakeMonitor:
    def __init__(self, name, refresh_rates):
        self.name = name
        self.refresh_rates = refresh_rates


class _FakeMonitorGlfw:
    @staticmethod
    def get_monitor_name(monitor):
        return monitor.name.encode("utf-8")

    @staticmethod
    def get_video_modes(monitor):
        return [types.SimpleNamespace(refresh_rate=r) for r in monitor.refresh_rates]


def test_max_refresh_rate_returns_highest_reported_mode():
    monitor = _FakeMonitor("Built-in Retina Display", [60, 120, 90])
    assert Screen._max_refresh_rate(_FakeMonitorGlfw(), monitor) == 120


def test_max_refresh_rate_returns_none_without_modes():
    monitor = _FakeMonitor("Unknown Monitor", [])
    assert Screen._max_refresh_rate(_FakeMonitorGlfw(), monitor) is None


def test_max_refresh_rate_at_resolution_prefers_modes_matching_current_resolution():
    class Glfw:
        @staticmethod
        def get_video_modes(monitor):
            return [
                types.SimpleNamespace(refresh_rate=240, size=types.SimpleNamespace(width=1280, height=720)),
                types.SimpleNamespace(refresh_rate=120, size=types.SimpleNamespace(width=1920, height=1080)),
                types.SimpleNamespace(refresh_rate=60, size=types.SimpleNamespace(width=1920, height=1080)),
            ]

    result = Screen._max_refresh_rate(Glfw(), monitor=object(), width=1920, height=1080)
    assert result == 120  # not 240, which is only available at a different resolution


def test_max_refresh_rate_at_resolution_falls_back_to_global_max_without_a_match():
    class Glfw:
        @staticmethod
        def get_video_modes(monitor):
            return [types.SimpleNamespace(refresh_rate=144, size=types.SimpleNamespace(width=2560, height=1440))]

    result = Screen._max_refresh_rate(Glfw(), monitor=object(), width=1920, height=1080)
    assert result == 144


def test_clamp_screen_number_warns_when_out_of_range(capsys):
    monitors = [_FakeMonitor("Built-in Retina Display", [60, 120]), _FakeMonitor("LG Ultrawide", [60, 144])]
    result = Screen._clamp_screen_number(5, _FakeMonitorGlfw(), monitors)
    message = capsys.readouterr().err
    assert "[TachyPy WARNING]: Screen initialization" in message
    assert "screen_number=5" in message
    assert "0: Built-in Retina Display (up to 120 Hz)" in message
    assert "1: LG Ultrawide (up to 144 Hz)" in message
    assert result == 0


def test_clamp_screen_number_no_warning_when_valid(capsys):
    monitors = [_FakeMonitor("A", [60]), _FakeMonitor("B", [60]), _FakeMonitor("C", [60])]
    result = Screen._clamp_screen_number(1, _FakeMonitorGlfw(), monitors)
    assert result == 1
    assert not capsys.readouterr().err


def test_clamp_screen_number_negative_clamps_silently_to_zero(capsys):
    monitors = [_FakeMonitor("A", [60]), _FakeMonitor("B", [60])]
    result = Screen._clamp_screen_number(-1, _FakeMonitorGlfw(), monitors)
    assert result == 0
    assert not capsys.readouterr().err
