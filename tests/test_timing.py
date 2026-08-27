import pytest

from tachypy.screen import LoopPacer, get_render_interval


class Screen:
    _max_mode_refresh_rate = 180
    vsync = True


def test_render_interval_uses_display_mode_rate():
    assert get_render_interval(Screen()) == pytest.approx(1 / 180)


def test_render_interval_uses_desired_rate_without_vsync():
    screen = Screen()
    screen.vsync = False
    screen.desired_refresh_rate = 120
    assert get_render_interval(screen) == pytest.approx(1 / 120)


def test_render_interval_uses_mode_rate_without_vsync_when_desired_rate_is_unset():
    screen = Screen()
    screen.vsync = False
    screen.desired_refresh_rate = None
    assert get_render_interval(screen) == pytest.approx(1 / 180)


def test_render_interval_uses_conservative_fallback_without_screen_rate():
    assert get_render_interval(object()) == pytest.approx(1 / 60)


def test_render_interval_rejects_nonpositive_rate():
    screen = Screen()
    screen.vsync = False
    screen.desired_refresh_rate = -1
    with pytest.raises(ValueError, match="positive"):
        get_render_interval(screen)


def test_loop_pacer_render_due_advances_schedule():
    pacer = LoopPacer(Screen(), wait_until=lambda t: None, start=0.0)
    assert pacer.render_due(0.0) is True
    assert pacer.render_due(0.001) is False
    assert pacer.render_due(1 / 180) is True


def test_loop_pacer_rejects_nonpositive_poll_interval():
    with pytest.raises(ValueError, match="poll_interval"):
        LoopPacer(Screen(), wait_until=lambda t: None, start=0.0, poll_interval=0)


def test_loop_pacer_defers_first_render_when_requested():
    pacer = LoopPacer(Screen(), wait_until=lambda t: None, start=0.0, defer_first_render=True)
    assert pacer.render_due(0.0) is False
    assert pacer.render_due(1 / 180 - 0.001) is True


def test_loop_pacer_reanchors_before_vsync_after_render():
    pacer = LoopPacer(Screen(), wait_until=lambda t: None, start=0.0)
    pacer.render_due(0.0)
    pacer.after_render(1.0)
    assert pacer.render_due(1.0 + 1 / 180 - 0.0011) is False
    assert pacer.render_due(1.0 + 1 / 180 - 0.001) is True


def test_loop_pacer_render_lateness_does_not_accumulate():
    pacer = LoopPacer(_100HzScreen(), wait_until=lambda t: None, start=0.0)
    assert pacer.render_due(0.0) is True
    assert pacer.render_due(0.0108) is True
    assert pacer.render_due(0.0199) is False
    assert pacer.render_due(0.0201) is True


def test_loop_pacer_wait_advances_poll_schedule():
    waits = []
    pacer = LoopPacer(Screen(), wait_until=waits.append, start=0.0, poll_interval=0.001)
    pacer.render_due(0.0)
    pacer.wait(0.0)
    pacer.wait(0.001)
    assert waits == [pytest.approx(0.001), pytest.approx(0.002)]


def test_loop_pacer_wait_resyncs_after_falling_far_behind():
    waits = []
    pacer = LoopPacer(Screen(), wait_until=waits.append, start=0.0, poll_interval=0.001)
    pacer.render_due(5.0)
    pacer.wait(5.0)
    assert waits == [pytest.approx(5.001)]


def test_loop_pacer_wakes_for_render_before_next_poll():
    waits = []
    pacer = LoopPacer(
        _100HzScreen(), wait_until=waits.append, start=0.0,
        poll_interval=0.02, defer_first_render=True,
    )
    pacer.wait(0.0)
    assert waits == [pytest.approx(0.0075)]


def test_loop_pacer_sustains_120_hz_without_poll_catchup_bursts():
    class Screen120:
        _max_mode_refresh_rate = 120
        vsync = True

    now = [0.0]
    samples = []
    flips = []
    frame_interval = 1 / 120

    def wait_until(target):
        now[0] = max(now[0], target)

    pacer = LoopPacer(Screen120(), wait_until, now[0])
    while now[0] < 3.0:
        samples.append(now[0])
        if pacer.render_due(now[0]):
            next_vsync = (int(now[0] / frame_interval) + 1) * frame_interval
            now[0] = next_vsync
            flips.append(next_vsync)
            pacer.after_render(now[0])
        pacer.wait(now[0])

    achieved_hz = (len(flips) - 1) / (flips[-1] - flips[0])
    polling_hz = (len(samples) - 1) / (samples[-1] - samples[0])
    assert achieved_hz == pytest.approx(120)
    assert polling_hz > 900
    assert all(later > earlier for earlier, later in zip(samples, samples[1:]))


class _100HzScreen:
    _max_mode_refresh_rate = 100
    vsync = True


def test_loop_pacer_tracks_consecutive_late_renders():
    pacer = LoopPacer(_100HzScreen(), wait_until=lambda t: None, start=0.0)
    assert pacer.frame_interval == pytest.approx(0.01)

    assert pacer.render_due(0.00) is True  # on time
    assert pacer.late_renders == 0

    assert pacer.render_due(0.01) is True  # on time
    assert pacer.late_renders == 0

    assert pacer.render_due(0.05) is True  # 0.03 late (>= frame_interval)
    assert pacer.late_renders == 1

    assert pacer.render_due(0.10) is True  # late again
    assert pacer.late_renders == 2

    assert pacer.render_due(0.11) is True  # back on time -> resets
    assert pacer.late_renders == 0
