from tachypy.scrollbar_interaction import (
    SliderControls,
    _effective_pressure,
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


def test_pressure_mapping_is_precise_at_low_pressure():
    assert _effective_pressure(0.05, 0.05, 2.5) == 0.0
    assert _effective_pressure(0.2, 0.05, 2.5) < _effective_pressure(0.8, 0.05, 2.5)


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


def test_mouse_keyboard_keeps_analog_key_movement():
    slider = FakeSlider()
    clock_value = iter([0.0, 0.0, 0.01, 0.02, 0.10])
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
    clock_value = iter([0.0, 0.0, 0.01, 0.02, 0.10])
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
