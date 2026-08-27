"""Interactive laboratory for tuning duration-based scrollbar movement."""
from __future__ import annotations

import argparse
import random
import time
from dataclasses import dataclass

import numpy as np

from tachypy import Circle, Line, ResponseHandler, Screen, Scrollbar, Text, WOOTING_ACQUISITION
from tachypy.scrollbar_interaction import _quadratic_speed, run_slider_interaction

TARGETS = (5, 15, 30, 45, 55, 70, 85, 95)
DEFAULTS = run_slider_interaction.__kwdefaults__

# name, low, high, default key, default scale, y-fraction, decimals.
# Order matches the unpacking in main()'s settings().
CONTROL_SPECS = (
    ("Deadzone (uint8)", 0, 100, "pressure_deadzone", 255, 0.13, 0),
    ("Acceleration", 10, 1000, "acceleration", 1, 0.201, 0),
    ("Maximum speed", 5, 200, "movement_speed", 1, 0.272, 0),
    ("Curve X (horizontal)", -1, 0, "curve_x", 1, 0.343, 2),
    ("Curve Y (vertical)", -1, 1, "curve_y", 1, 0.414, 2),
    ("Outward edge margin (0 = OFF)", 0, 50, "edge_margin", 1, 0.485, 0),
    ("Edge reduction (0 = OFF)", 0, 3, "edge_reduction", 1, 0.556, 2),
)


@dataclass
class ParameterControl:
    """Mouse-adjustable parameter backed by a TachyPy scrollbar."""

    name: str
    low: float
    high: float
    slider: Scrollbar
    label: Text
    decimals: int = 1

    @classmethod
    def create(cls, screen, name, low, high, initial, y, decimals=1):
        panel_width = screen.width / 2
        slider = Scrollbar(
            screen_width=panel_width, screen_height=screen.height, position_y=y,
            half_bar_length=min(350, panel_width / 2 - 80), num_marks=9,
            text_left="", text_right="", limit_mouse=True,
            content_scale=screen.content_scale,
        )
        label = Text(
            "", dest_rect=(40, y - 42, panel_width - 40, y - 15),
            font_size=18, color=(0, 0, 0), content_scale=screen.content_scale,
        )
        control = cls(name, float(low), float(high), slider, label, decimals)
        control.set_value(initial)
        return control

    @property
    def value(self):
        return self.low + (self.high - self.low) * self.slider.get_value() / 100

    def set_value(self, value):
        self.slider.set_value(100 * (float(value) - self.low) / (self.high - self.low))
        self.label.set_text(
            f"{self.name}: {self.value:.{self.decimals}f}   [{self.low:g}-{self.high:g}]"
        )

    def hit(self, x, y):
        return self.slider.min_x <= x <= self.slider.max_x and abs(y - self.slider.position_y) <= 30

    def move_to(self, x, y):
        changed = self.slider.handle_mouse(x, y)
        if changed:
            self.set_value(self.value)
        return changed

    def draw(self):
        self.label.draw()
        self.slider.draw()


class HoldSpeedPlot:
    """Plot speed against hold duration and show live Z/C positions."""

    duration_max = 1.0
    speed_max = 200.0

    def __init__(self, screen, top, bottom):
        self.left, self.right = screen.width / 2 + 70, screen.width - 70
        self.top, self.bottom = top, bottom
        self.deadzone = DEFAULTS["pressure_deadzone"]
        self.acceleration = DEFAULTS["acceleration"]
        self.max_speed = DEFAULTS["movement_speed"]
        self.curve_x, self.curve_y = DEFAULTS["curve_x"], DEFAULTS["curve_y"]
        self.pressures, self.started, self.durations = [0.0, 0.0], [None, None], [0.0, 0.0]
        self.axes = (
            Line((self.left, top), (self.left, bottom), 2, (0, 0, 0)),
            Line((self.left, bottom), (self.right, bottom), 2, (0, 0, 0)),
        )
        self.grid, self.labels = [], []
        for duration in np.linspace(0, self.duration_max, 6):
            x = self._x(duration)
            self.grid.append(Line((x, top), (x, bottom), 1, (105, 105, 105)))
            self.labels.append(Text(
                f"{duration:.1f}", dest_rect=(x - 25, bottom + 3, x + 25, bottom + 26),
                font_size=13, color=(0, 0, 0), content_scale=screen.content_scale,
            ))
        for speed in (0, 40, 80, 120, 160, 200):
            y = self._y(speed)
            self.grid.append(Line((self.left, y), (self.right, y), 1, (105, 105, 105)))
            self.labels.append(Text(
                str(speed), dest_rect=(self.left - 58, y - 11, self.left - 8, y + 11),
                font_size=13, color=(0, 0, 0), content_scale=screen.content_scale,
            ))
        self.title = Text(
            "HOLD DURATION (s) -> SPEED (units/s)",
            dest_rect=(self.left - 30, top - 65, self.right + 30, top - 25),
            font_size=20, color=(0, 0, 0), content_scale=screen.content_scale,
        )
        self.info = Text(
            "", dest_rect=(self.left - 20, bottom + 30, self.right + 20, bottom + 62),
            font_size=14, color=(0, 0, 0), content_scale=screen.content_scale,
        )
        self.curve = [Line((0, 0), (0, 0), 3, (0, 70, 190)) for _ in range(64)]
        self.markers = (
            Circle((0, 0), 6, color=(210, 40, 40), num_segments=24),
            Circle((0, 0), 6, color=(0, 145, 65), num_segments=24),
        )
        self.update(
            self.deadzone, self.acceleration, self.max_speed, self.curve_x, self.curve_y,
        )

    def _x(self, duration):
        return self.left + min(duration / self.duration_max, 1) * (self.right - self.left)

    def _y(self, speed):
        return self.bottom - min(speed / self.speed_max, 1) * (self.bottom - self.top)

    def _speed_at(self, t):
        """Speed reached after holding for duration ``t``, per the current curve settings."""
        return _quadratic_speed(
            t, self.acceleration, self.max_speed, self.curve_x, self.curve_y,
        )

    def update(self, deadzone, acceleration, max_speed, curve_x, curve_y):
        self.deadzone, self.acceleration = deadzone, acceleration
        self.max_speed, self.curve_x, self.curve_y = max_speed, curve_x, curve_y
        durations = np.linspace(0, self.duration_max, len(self.curve) + 1)
        points = [(self._x(t), self._y(self._speed_at(t))) for t in durations]
        for line, start, end in zip(self.curve, points, points[1:]):
            line.set_start_point(start)
            line.set_end_point(end)
        self.info.set_text(
            f"DEADZONE {deadzone * 255:.0f} | ACCELERATION {acceleration:.0f} | "
            f"MAX {max_speed:.0f} | X {curve_x:.2f} | Y {curve_y:.2f} | Z RED / C GREEN"
        )

    def track(self, decrease, increase):
        now = time.perf_counter()
        self.pressures[:] = decrease, increase
        active = (
            None if decrease == increase else 0 if decrease > increase else 1
        ) if max(decrease, increase) > self.deadzone else None
        for index, pressure in enumerate(self.pressures):
            if index == active and pressure > self.deadzone:
                self.started[index] = now if self.started[index] is None else self.started[index]
                self.durations[index] = now - self.started[index]
            else:
                self.started[index], self.durations[index] = None, 0.0

    def draw(self):
        for drawable in (*self.grid, *self.axes, *self.curve, *self.labels, self.title, self.info):
            drawable.draw()
        for started, duration, marker in zip(self.started, self.durations, self.markers):
            if started is not None:
                marker.set_center((self._x(duration), self._y(self._speed_at(duration))))
                marker.draw()


def _next_target(pool, previous):
    if not pool:
        pool.extend(TARGETS)
        random.shuffle(pool)
    if pool[-1] == previous and len(pool) > 1:
        pool[-1], pool[-2] = pool[-2], pool[-1]
    return pool.pop()


def parse_args():
    parser = argparse.ArgumentParser(description="Interactively tune the Wooting scrollbar.")
    parser.add_argument("--fullscreen", action="store_true")
    return parser.parse_args()


def main():
    """Run the interactive parameter lab."""
    args = parse_args()
    target_pool = []
    acquisition = WOOTING_ACQUISITION()
    screen = None
    try:
        acquisition.initialize_keyboard()
        screen = Screen(
            width=None if args.fullscreen else 1200, height=None if args.fullscreen else 900,
            fullscreen=args.fullscreen, grab_input=False, screen_number=1,
        )
        responses = ResponseHandler(screen=screen, keys_to_listen=["escape"])
        controls = [
            ParameterControl.create(
                screen, name, low, high, DEFAULTS[key] * scale, screen.height * y_fraction, decimals,
            )
            for name, low, high, key, scale, y_fraction, decimals in CONTROL_SPECS
        ]
        speed_plot = HoldSpeedPlot(screen, screen.height * 0.11, screen.height * 0.51)
        test_slider = Scrollbar(
            screen_width=screen.width, screen_height=screen.height,
            position_y=screen.height * 0.83, half_bar_length=430, num_marks=11,
            content_scale=screen.content_scale, notch_label_every=2,
        )
        header = Text(
            "ADJUST SETTINGS, THEN PRESS X TO START",
            dest_rect=(40, 15, screen.width / 2 - 40, 65),
            font_size=25, color=(0, 0, 0), content_scale=screen.content_scale,
        )
        target_text = Text(
            "", dest_rect=(40, screen.height * 0.61, screen.width - 40, screen.height * 0.81),
            font_size=28, color=(0, 0, 0), content_scale=screen.content_scale,
        )
        target_lines = tuple(Line((0, 0), (0, 0), 4, (0, 90, 255)) for _ in range(2))
        scene = (header, *controls, speed_plot, target_text, *target_lines)
        target = _next_target(target_pool, None)

        def read_keys():
            pressures = acquisition.read_pressures(("z", "c", "x"))
            speed_plot.track(pressures["z"], pressures["c"])
            return pressures

        def control_at(mouse_x, mouse_y):
            return next((item for item in controls if item.hit(mouse_x, mouse_y)), None)

        def settings():
            deadzone, acceleration, max_speed, curve_x, curve_y, edge_margin, edge_reduction = (
                control.value for control in controls
            )
            speed_plot.update(deadzone / 255, acceleration, max_speed, curve_x, curve_y)
            return {
                "pressure_deadzone": deadzone / 255,
                "acceleration": acceleration,
                "movement_speed": max_speed,
                "curve_x": curve_x,
                "curve_y": curve_y,
                "edge_margin": edge_margin,
                "edge_reduction": edge_reduction,
            }

        def show_target(message):
            target_text.set_text(f"TARGET: {target:g}\n{message}\nESCAPE: FINISH")
            target_x = test_slider.min_x + target / 100 * (test_slider.max_x - test_slider.min_x)
            for line, start_y, end_y in zip(
                target_lines,
                (test_slider.position_y - 32, test_slider.position_y + 14),
                (test_slider.position_y - 14, test_slider.position_y + 32),
            ):
                line.set_start_point((target_x, start_y))
                line.set_end_point((target_x, end_y))

        def draw_scene():
            screen.fill((128, 128, 128))
            test_slider.draw()
            for drawable in scene:
                drawable.draw()
            screen.flip()

        def wait_for_start(dragged=None):
            armed = started = False
            responses.clear_events()
            while not responses.should_quit():
                responses.get_events()
                pressures = read_keys()
                if pressures["x"] < 0.03:
                    if started:
                        return True
                    armed = True
                elif armed and pressures["x"] >= 0.6:
                    started = True
                    show_target("RELEASE X TO START")
                mouse_x, mouse_y = responses.get_mouse_position()
                if responses.was_mouse_button_pressed(0):
                    dragged = control_at(mouse_x, mouse_y)
                if dragged and responses.is_mouse_button_pressed(0) and dragged.move_to(mouse_x, mouse_y):
                    settings()
                if responses.was_mouse_button_released(0):
                    dragged = None
                draw_scene()
            return False

        def wait_for_release(message):
            show_target(f"{message}   RELEASE X")
            while not responses.should_quit():
                responses.get_events()
                if read_keys()["x"] < 0.03:
                    return True
                draw_scene()
            return False

        tuning_control = None

        def update_live(analog_controls):
            nonlocal tuning_control
            speed_plot.track(analog_controls.decrease, analog_controls.increase)
            if responses.was_mouse_button_pressed(0):
                tuning_control = control_at(*responses.get_mouse_position())
            return tuning_control is not None

        settings()
        show_target("X: START")
        if wait_for_start():
            header.set_text("CURRENT SETTINGS")
            while True:
                tuning_control = None
                show_target("Z/C: MOVE    X: CONFIRM")
                selected, reaction_time = acquisition.interact_slider(
                    slider=test_slider, screen=screen, response_handler=responses,
                    drawables=scene, control_callback=update_live, initial_value=None,
                    **settings(),
                )
                if selected is None:
                    if tuning_control is not None:
                        header.set_text("ADJUST SETTINGS, THEN PRESS X TO RESUME")
                        show_target("X: RESUME")
                        if not wait_for_start(tuning_control):
                            break
                        header.set_text("CURRENT SETTINGS")
                        continue
                    break
                error = abs(selected - target)
                if not wait_for_release(f"ERROR: {error:.2f}   RT: {reaction_time:.3f}s"):
                    break
                target = _next_target(target_pool, target)
        return 0
    finally:
        acquisition.uninitialize_keyboard()
        if screen is not None:
            screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
