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


class FakeScreen:
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
