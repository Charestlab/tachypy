import itertools

import pytest

from tachypy.scrollbar_interaction import (
    SliderControls,
    _accelerated_step,
    _edge_scale,
    _movement_direction,
    _quadratic_speed,
    run_slider_interaction,
)


class FakeSlider:
    def __init__(self):
        self.value = 50.0

    def set_value(self, value):
        self.value = max(0.0, min(100.0, value))

    def get_value(self):
        return self.value

    def draw(self):
        pass

    def handle_mouse(self, x, _y):
        changed = self.value != x
        self.set_value(x)
        return changed

    def move_by(self, delta_x, _mouse_y=None):
        changed = delta_x != 0
        self.set_value(self.value + delta_x)
        return changed


class FakeInput:
    def __init__(self, values):
        self.values = iter(values)

    def __call__(self):
        return next(self.values)


class FakeResponse:
    def get_events(self):
        pass

    def should_quit(self):
        return False

    def set_position(self, _x, _y):
        pass


class FakeMouseResponse(FakeResponse):
    def __init__(self, positions, clicks=True, click_after=0):
        self.positions = iter(positions)
        self.clicks = clicks
        self.frame = 0
        self.click_after = click_after

    def get_mouse_position(self):
        return next(self.positions)

    def get_mouse_clicks(self):
        self.frame += 1
        return ([{"type": "mouseup", "pos": (80.0, 0.0)}]
                if self.clicks and self.frame > self.click_after else [])


class CumulativeMouseResponse(FakeResponse):
    """Mimics the real ResponseHandler: mouse_clicks only grows and is never
    reset between calls, unlike FakeMouseResponse's frame-local recompute.

    ``click_appears_on_call`` controls which get_mouse_clicks() call first
    sees the click, so a test can put it on a frame where keyboard_active
    is True before the loop later checks it with keyboard_active False.
    """

    def __init__(self, position, click_appears_on_call):
        self.position = position
        self.click_appears_on_call = click_appears_on_call
        self.calls = 0
        self._clicks = []

    def get_mouse_position(self):
        return self.position

    def get_mouse_clicks(self):
        self.calls += 1
        if self.calls == self.click_appears_on_call and not self._clicks:
            self._clicks.append({"type": "mouseup", "button": 0, "pos": self.position})
        return self._clicks


class EdgeMouseResponse(FakeResponse):
    def __init__(self):
        self.positions = iter([(500.0, 300.0), (999.0, 300.0), (500.0, 300.0)])
        self.recenters = []

    def get_mouse_position(self):
        return next(self.positions)

    def get_mouse_clicks(self):
        return []

    def set_position(self, x, y):
        self.recenters.append((x, y))


class FakeScreen:
    width = 1000

    def fill(self, color):
        pass

    def flip(self):
        pass


class FakeMouseScreen(FakeScreen):
    vsync = False
    desired_refresh_rate = -1

    def __init__(self):
        self.mouse_visible = True
        self.show_calls = 0

    def hide_mouse(self):
        self.mouse_visible = False

    def show_mouse(self):
        self.mouse_visible = True
        self.show_calls += 1


class IncompleteMouseScreen(FakeScreen):
    """Has mouse_visible but no hide_mouse/show_mouse -- an incomplete duck-typed screen."""

    mouse_visible = True


class QuittingResponse(FakeResponse):
    def get_mouse_position(self):
        return (50.0, 0.0)

    def get_mouse_clicks(self):
        return []

    def should_quit(self):
        return True


def padded_clock(values):
    """A finite clock schedule that repeats its last value instead of raising StopIteration.

    A render can trigger an extra clock() read to resync after a blocking flip(),
    which a plain iter([...]) can't absorb without knowing the exact call count.
    """
    return iter(itertools.chain(values, itertools.repeat(values[-1])))


def test_movement_direction_uses_deadzone_and_stronger_key():
    deadzone = 15 / 255
    assert _movement_direction(SliderControls(increase=deadzone), deadzone) == 0
    assert _movement_direction(SliderControls(increase=0.8), deadzone) == 1
    assert _movement_direction(SliderControls(decrease=0.8), deadzone) == -1
    assert _movement_direction(SliderControls(decrease=0.4, increase=0.8), deadzone) == 1
    assert _movement_direction(SliderControls(decrease=0.8, increase=0.8), deadzone) == 0


@pytest.mark.parametrize(
    "parameters",
    [
        {"movement_speed": 0},
        {"acceleration": 0},
        {"pressure_deadzone": -0.01},
        {"pressure_deadzone": 1},
        {"curve_x": -1.01},
        {"curve_x": 0.01},
        {"curve_y": -1.01},
        {"curve_y": 1.01},
    ],
)
def test_invalid_movement_parameters_are_rejected(parameters):
    with pytest.raises(ValueError, match="movement"):
        run_slider_interaction(
            slider=FakeSlider(),
            screen=FakeScreen(),
            response_handler=FakeResponse(),
            control_reader=FakeInput([SliderControls()]),
            wait_until=lambda _: None,
            **parameters,
        )


def test_edge_reduction_only_affects_outward_movement():
    assert _edge_scale(10, -1, 20, 1) == pytest.approx(0.5)
    assert _edge_scale(10, -1, 20, 2) == pytest.approx(0.25)
    assert _edge_scale(10, 1, 20, 2) == 1.0
    assert _edge_scale(0, -1, 20, 1) == 0.0
    assert _edge_scale(0, -1, 0, 1) == 1.0


@pytest.mark.parametrize("parameters", [{"edge_margin": -1}, {"edge_reduction": -0.1}])
def test_invalid_edge_parameters_are_rejected(parameters):
    with pytest.raises(ValueError, match="edge"):
        run_slider_interaction(
            slider=FakeSlider(),
            screen=FakeScreen(),
            response_handler=FakeResponse(),
            control_reader=FakeInput([SliderControls()]),
            wait_until=lambda _: None,
            **parameters,
        )


def test_negative_mouse_quiet_period_is_rejected():
    with pytest.raises(ValueError, match="edge"):
        run_slider_interaction(
            slider=FakeSlider(),
            screen=FakeScreen(),
            response_handler=FakeResponse(),
            control_reader=FakeInput([SliderControls()]),
            wait_until=lambda _: None,
            mouse_quiet_period=-0.01,
        )


def test_held_key_accelerates_until_maximum_speed():
    clock_value = padded_clock([0.0, 0.0, 0.1, 0.2, 0.3])
    value, _ = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(increase=0.8),
            SliderControls(increase=0.8),
            SliderControls(increase=0.8),
            SliderControls(confirm=0.8),
        ]),
        movement_speed=10,
        acceleration=100,
        curve_x=0,
        curve_y=0,
        edge_margin=0,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert value == pytest.approx(51 + 1 / 3)


def test_quadratic_integration_is_independent_of_step_size():
    whole, _ = _accelerated_step(0, 0.6, 100, 100, -0.25, -0.03)
    total = hold = 0.0
    for _ in range(600):
        distance, hold = _accelerated_step(hold, 0.001, 100, 100, -0.25, -0.03)
        total += distance
    assert total == pytest.approx(whole)


@pytest.mark.parametrize("hold_time", [0.0, 0.2, 0.6, 0.8])
def test_integrated_curve_matches_reported_speed(hold_time):
    step = 1e-6
    distance, _ = _accelerated_step(hold_time, step, 100, 100, -0.25, -0.03)
    expected = _quadratic_speed(hold_time, 100, 100, -0.25, -0.03)
    assert distance / step == pytest.approx(expected, abs=1e-4)


def test_curve_position_controls_initial_speed():
    def move(curve_x=0, curve_y=0):
        clock_value = padded_clock([0.0, 0.0, 0.1, 0.2])
        return run_slider_interaction(
            slider=FakeSlider(),
            screen=FakeScreen(),
            response_handler=FakeResponse(),
            control_reader=FakeInput([
                SliderControls(increase=0.8),
                SliderControls(increase=0.8),
                SliderControls(confirm=0.8),
            ]),
            curve_x=curve_x,
            curve_y=curve_y,
            movement_speed=40,
            acceleration=200,
            edge_margin=0,
            clock=lambda: next(clock_value),
            wait_until=lambda _: None,
        )[0]

    assert move(curve_x=-0.25) > move()
    assert move(curve_y=0.25) > move()
    assert move(curve_y=-0.25) < move()
    assert move(curve_x=-1) == pytest.approx(54.0)
    assert move(curve_y=1) == pytest.approx(54.0)


def test_pressure_magnitude_does_not_change_speed_above_deadzone():
    def move(pressure):
        clock_value = padded_clock([0.0, 0.0, 0.1, 0.2])
        return run_slider_interaction(
            slider=FakeSlider(),
            screen=FakeScreen(),
            response_handler=FakeResponse(),
            control_reader=FakeInput([
                SliderControls(increase=pressure),
                SliderControls(increase=pressure),
                SliderControls(confirm=0.8),
            ]),
            clock=lambda: next(clock_value),
            wait_until=lambda _: None,
        )[0]

    assert move(0.1) == pytest.approx(move(1.0))


def test_release_resets_acceleration():
    clock_value = padded_clock([0.0, 0.0, 0.1, 0.2, 0.3, 0.4])
    value, _ = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(increase=0.8),
            SliderControls(increase=0.8),
            SliderControls(),
            SliderControls(increase=0.8),
            SliderControls(confirm=0.8),
        ]),
        movement_speed=100,
        acceleration=100,
        curve_x=0,
        curve_y=0,
        edge_margin=0,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert value == pytest.approx(50 + 1 / 15)


def test_direction_change_resets_acceleration():
    clock_value = padded_clock([0.0, 0.0, 0.1, 0.2, 0.3])
    value, _ = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(increase=0.8),
            SliderControls(increase=0.8),
            SliderControls(decrease=0.8),
            SliderControls(confirm=0.8),
        ]),
        movement_speed=100,
        acceleration=100,
        curve_x=0,
        curve_y=0,
        edge_margin=0,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert value == pytest.approx(50.0)


def test_keyboard_slider_moves_and_confirms():
    slider = FakeSlider()
    clock_value = iter([0.0, 0.001, 0.002, 0.003, 0.004])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(decrease=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result[0] < 50.0
    assert result[1] > 0.0


def test_control_callback_receives_each_sample():
    samples = [SliderControls(), SliderControls(increase=0.8), SliderControls(confirm=0.8)]
    observed = []
    clock_value = iter([0.0, 0.001, 0.002, 0.003])
    run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput(samples),
        control_callback=observed.append,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert observed == samples


def test_control_callback_can_stop_interaction():
    result = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([SliderControls()]),
        control_callback=lambda _controls: True,
        clock=lambda: 0.0,
        wait_until=lambda _: None,
    )
    assert result == (None, None)


def test_none_initial_value_preserves_previous_selection():
    slider = FakeSlider()
    slider.set_value(73.5)
    clock_value = iter([0.0, 0.001, 0.002])
    value, _ = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        initial_value=None,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert value == 73.5


def test_movement_key_held_at_start_moves_immediately():
    slider = FakeSlider()
    clock_value = padded_clock([0.0, 0.0, 0.01, 0.02, 0.03, 0.04])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(increase=0.8),
            SliderControls(increase=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result[0] > 50.0


def test_stronger_opposing_key_determines_direction():
    slider = FakeSlider()
    clock_value = iter([0.0, 0.0, 0.01, 0.02])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(decrease=0.4, increase=0.8),
            SliderControls(decrease=0.4, increase=0.8),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result[0] > 50.0


def test_equal_opposing_keys_cancel():
    clock_value = iter([0.0, 0.0, 0.01, 0.02])
    result = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(decrease=0.8, increase=0.8),
            SliderControls(decrease=0.8, increase=0.8),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result[0] == 50.0


def test_confirm_held_at_start_requires_release_and_repress():
    clock_value = iter([0.0, 0.0, 0.001, 0.002, 0.003])
    result = run_slider_interaction(
        slider=FakeSlider(),
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(confirm=0.8),
            SliderControls(confirm=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result == (50.0, pytest.approx(0.003))


def test_confirmation_is_blocked_during_movement_until_x_is_repressed():
    slider = FakeSlider()
    clock_value = iter(i / 1000 for i in range(8))
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(increase=0.8),
            SliderControls(increase=0.8, confirm=0.8),
            SliderControls(confirm=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result[0] > 50.0


def test_confirm_blocked_when_decrease_and_increase_pressures_tie():
    # A tie between Z and C resolves to no net movement (direction=0), but
    # both keys are still held -- X must stay blocked, not just when there's
    # net motion, matching "X cannot confirm while Z or C is active".
    slider = FakeSlider()
    clock_value = padded_clock([0.0, 0.0, 0.001, 0.002, 0.003])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([
            SliderControls(),                                        # frame 0: arm confirm
            SliderControls(decrease=0.8, increase=0.8, confirm=0.8),  # frame 1: tied Z/C + confirm cross -- must not confirm
            SliderControls(),                                        # frame 2: release everything
            SliderControls(confirm=0.8),                             # frame 3: legitimate confirm
        ]),
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result == (50.0, pytest.approx(0.003))


def test_mouse_click_confirms_after_quiet_period():
    slider = FakeSlider()
    clock_value = iter([0.0, 0.0, 0.01, 0.06])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeMouseResponse(
            [(10.0, 0.0), (50.0, 0.0), (50.0, 0.0)], click_after=2
        ),
        control_reader=FakeInput([SliderControls(), SliderControls(), SliderControls()]),
        input_mode="mouse_keyboard",
        mouse_quiet_period=0.04,
        clock=lambda: next(clock_value),
        wait_until=lambda _: None,
    )
    assert result == (90.0, 0.06)


def test_stale_click_during_keyboard_input_is_drained_not_confirmed_later():
    # A click that lands while keyboard_active is True must not resurface and
    # spuriously confirm on a later, unrelated frame once keyboard goes quiet.
    # increase=0.9 (not confirm) makes keyboard_active True without itself
    # crossing confirm_threshold, so it can't confirm through a different path.
    slider = FakeSlider()
    response = CumulativeMouseResponse(position=(50.0, 0.0), click_appears_on_call=2)
    clock_value = padded_clock([0.0, 0.0, 0.001, 0.002, 0.003])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=response,
        control_reader=FakeInput([
            SliderControls(),              # frame 0: arm (no click yet)
            SliderControls(increase=0.9),  # frame 1: keyboard_active; click appears, must be drained not acted on
            SliderControls(),              # frame 2: keyboard_active False; stale click must NOT confirm here
            SliderControls(confirm=0.8),   # frame 3: legitimate keyboard confirm
        ]),
        input_mode="mouse_keyboard",
        wait_until=lambda _: None,
        clock=lambda: next(clock_value),
    )
    # Confirmed via the legitimate keyboard path on frame 3, not the stale click on frame 2.
    assert result[1] == pytest.approx(0.003)


def test_mouse_keyboard_keeps_analog_key_movement():
    slider = FakeSlider()
    clock_value = padded_clock([0.0, 0.0, 0.01, 0.02, 0.10])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeMouseResponse([(50.0, 0.0)] * 4, clicks=False),
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(increase=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        input_mode="mouse_keyboard",
        wait_until=lambda _: None,
        clock=lambda: next(clock_value),
    )
    assert result[0] > 50.0


def test_mouse_is_locked_while_any_keyboard_key_has_pressure():
    slider = FakeSlider()
    clock_value = padded_clock([0.0, 0.0, 0.01, 0.02, 0.10])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeMouseResponse(
            [(500.0, 0.0), (900.0, 0.0), (900.0, 0.0), (900.0, 0.0)],
            clicks=False,
        ),
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(increase=0.8),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        input_mode="mouse_keyboard",
        wait_until=lambda _: None,
        clock=lambda: next(clock_value),
    )
    assert 50.0 < result[0] < 60.0


def test_mouse_keyboard_recenters_at_screen_edge():
    slider = FakeSlider()
    response = EdgeMouseResponse()
    clock_value = iter([0.0, 0.0, 0.01, 0.10])
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=response,
        control_reader=FakeInput([
            SliderControls(),
            SliderControls(),
            SliderControls(confirm=0.8),
        ]),
        input_mode="mouse_keyboard",
        wait_until=lambda _: None,
        clock=lambda: next(clock_value),
    )
    assert result[0] == 100.0
    assert response.recenters == [(500.0, 300.0)]


def test_poll_wait_resyncs_to_post_render_clock_after_a_render():
    # A render on the first iteration "blocks" for a long time (0.02 -> 5.0), simulating
    # a slow flip(). The poll wait must be scheduled off the fresh post-render clock
    # reading, not the stale pre-render `now`, or it drifts/busy-spins relative to real time.
    slider = FakeSlider()
    clock_value = padded_clock([0.0, 0.02, 5.0, 5.001])
    waits = []
    result = run_slider_interaction(
        slider=slider,
        screen=FakeScreen(),
        response_handler=FakeResponse(),
        control_reader=FakeInput([SliderControls(), SliderControls(confirm=0.8)]),
        clock=lambda: next(clock_value),
        wait_until=waits.append,
    )
    assert waits == [pytest.approx(5.001)]
    assert result == (50.0, pytest.approx(5.001))


def test_mouse_visibility_restored_when_pacer_construction_fails():
    screen = FakeMouseScreen()
    with pytest.raises(ValueError):
        run_slider_interaction(
            slider=FakeSlider(),
            screen=screen,
            response_handler=FakeMouseResponse([(500.0, 300.0)]),
            control_reader=FakeInput([SliderControls()]),
            input_mode="mouse_keyboard",
            wait_until=lambda _: None,
            clock=lambda: 0.0,
        )
    assert screen.mouse_visible is True
    assert screen.show_calls == 1


def test_finish_does_not_crash_when_screen_lacks_mouse_visibility_methods():
    # The initial hide is skipped via hasattr(screen, "hide_mouse"); finish()
    # must use the same guard, not just "was mouse_visible known", or a
    # screen with the attribute but not the methods crashes on exit.
    result = run_slider_interaction(
        slider=FakeSlider(),
        screen=IncompleteMouseScreen(),
        response_handler=QuittingResponse(),
        control_reader=FakeInput([SliderControls()]),
        input_mode="mouse_keyboard",
        wait_until=lambda _: None,
        clock=lambda: 0.0,
    )
    assert result == (None, None)
