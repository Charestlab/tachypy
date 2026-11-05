"""Abort, timeout and source wiring for visual feedback, using a virtual clock."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import tachypy.feedback.runner as runner
from tachypy.feedback import PressureFeedbackConfig, PressureFeedbackState, VisualPressureFeedbackMixin


@pytest.mark.parametrize("handler,expected", [
    (None, False), (SimpleNamespace(), False),
    (SimpleNamespace(should_quit=lambda: True), True),
    (SimpleNamespace(key_down_events=["ESCAPE"]), True),
    (SimpleNamespace(key_down_events=["a"]), False),
    (SimpleNamespace(get_key_presses=lambda: [{"type": "keyup", "key": "escape"}]), False),
    (SimpleNamespace(get_key_presses=lambda: [{"type": "keydown", "key": "Escape"}]), True),
])
def test_exit_handler_protocols(handler, expected):
    assert runner._exit_requested(handler, {"escape"}) is expected


@pytest.fixture
def loop(monkeypatch):
    clock = SimpleNamespace(now=0.0)
    monkeypatch.setattr(runner.time, "perf_counter", lambda: clock.now)
    def wait_until(deadline):
        clock.now = max(clock.now, deadline)
    screen = SimpleNamespace(flip=Mock(), fill=Mock(), vsync=False, desired_refresh_rate=100)
    widget = Mock()
    state = PressureFeedbackState(PressureFeedbackConfig(hold_seconds=0.003))
    return dict(read_pair=lambda: (0.1, 0.1), state=state, widget=widget,
                screen=screen, wait_until=wait_until), clock


def test_feedback_reaches_hold_and_draws_overlays_and_dynamic_background(loop):
    options, clock = loop
    overlay = Mock()
    handler = SimpleNamespace(keys_to_listen=["A"], _probed_keys=set(), get_events=Mock())
    assert runner.run_light_press_visual(**options, response_handler=handler,
                                        overlay_drawables=[overlay], background_color=lambda: (1, 2, 3))
    assert clock.now == pytest.approx(0.003)
    assert options["state"].is_ready
    assert options["screen"].flip.call_count == 2
    assert overlay.draw.call_count == 2
    options["screen"].fill.assert_called_with((1, 2, 3))
    assert "a" in handler.keys_to_listen and "escape" in handler._probed_keys
    handler.get_events.assert_called()


def test_feedback_aborts_before_reading_pressure(loop):
    options, _ = loop
    options["read_pair"] = Mock(side_effect=AssertionError("must not read after abort"))
    assert not runner.run_light_press_visual(**options, response_handler=SimpleNamespace(key_down_events=["q"]))
    options["widget"].draw.assert_not_called()


def test_feedback_timeout_and_missing_screen(loop):
    options, _ = loop
    options["read_pair"] = lambda: (0, 0)
    with pytest.raises(TimeoutError, match="timeout"):
        runner.run_light_press_visual(**options, timeout_seconds=0.002)
    options["screen"] = object()
    with pytest.raises(AttributeError, match="flip"):
        runner.run_light_press_visual(**options)


def test_default_wait_only_sleeps_for_future_deadlines(monkeypatch):
    monkeypatch.setattr(runner.time, "perf_counter", lambda: 1)
    sleep = Mock()
    monkeypatch.setattr(runner.time, "sleep", sleep)
    runner._default_wait_until(0.5)
    runner._default_wait_until(1.25)
    sleep.assert_called_once_with(0.25)


class Source(VisualPressureFeedbackMixin):
    initialized = True
    min_pressure_start = 0.1
    max_pressure_start = 0.3
    threshold = 0.8
    hold_seconds = 0.01

    def read_pressures(self, keys):
        return {str(key): 0.2 for key in keys}


@pytest.mark.parametrize("changes,options,message", [
    ({"initialized": False}, {}, "initialized"),
    ({}, {"timeout_seconds": 0}, "timeout_seconds"),
    ({}, {"target_keys": ["a"]}, "exactly two"),
    ({"hold_seconds": 0}, {}, "hold_seconds"),
])
def test_source_configuration_rejected_early(changes, options, message):
    source = Source()
    for key, value in changes.items():
        setattr(source, key, value)
    with pytest.raises(ValueError, match=message):
        source.wait_light_press_visual(screen=object(), **{"target_keys": ["a", "b"], **options})


def test_custom_widget_and_integer_key_source_wiring(monkeypatch):
    source = Source()
    source.validate_analog_keys = Mock()
    source._wait_until_next_tick = Mock()
    widget = Mock()
    def loop(**options):
        assert options["read_pair"]() == (0.2, 0.2)
        assert options["widget"] is widget
        assert options["state"].config.hold_seconds == 0.02
        assert options["wait_until"] is source._wait_until_next_tick
        return True
    monkeypatch.setattr(runner, "run_light_press_visual", loop)
    assert source.wait_light_press_visual([1, 2], screen=object(), widget=widget, hold_seconds=0.02)
    source.validate_analog_keys.assert_called_once_with([1, 2])
