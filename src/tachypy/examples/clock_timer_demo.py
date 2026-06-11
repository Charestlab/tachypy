"""Minimal GLFW/System Text clock and stopwatch demo for TachyPy.

Run fullscreen:

    python clock_timer_demo.py

Run windowed during development:

    python clock_timer_demo.py --windowed
"""

from __future__ import annotations

import argparse
import math
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence

from tachypy import Text, Circle, Line, Rectangle, ResponseHandler, Screen


BACKGROUND = (218, 218, 216)
INK = (18, 20, 22)
MUTED = (105, 108, 112)
PANEL = (232, 232, 229)
PANEL_STROKE = (188, 188, 184)
ACCENT = (42, 89, 255)
ACCENT_DARK = (26, 63, 197)
RESET = (58, 60, 64)
RESET_DARK = (36, 38, 42)


def clock_endpoint(center_x: float, center_y: float, radius: float, angle_radians: float) -> tuple[float, float]:
    """Convert a clock angle, where 0 is 12 o'clock, to screen coordinates."""
    return (
        center_x + math.sin(angle_radians) * radius,
        center_y - math.cos(angle_radians) * radius,
    )


def format_elapsed(seconds: float) -> str:
    centiseconds = int(seconds * 100)
    minutes, centiseconds = divmod(centiseconds, 6000)
    whole_seconds, centiseconds = divmod(centiseconds, 100)
    return f"{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def city_from_timezone_name(timezone_name: str) -> str:
    """Convert an IANA timezone name like America/Toronto into a display city."""
    city = timezone_name.strip().split("/")[-1]
    return city.replace("_", " ").strip()


def infer_city_label() -> str:
    """Best-effort local city inference from system timezone configuration."""
    timezone_name = os.environ.get("TZ", "").strip()
    if timezone_name and "/" in timezone_name:
        return city_from_timezone_name(timezone_name)

    localtime_path = Path("/etc/localtime")
    try:
        resolved = localtime_path.resolve()
    except OSError:
        resolved = localtime_path

    parts = resolved.parts
    if "zoneinfo" in parts:
        zone_parts = parts[parts.index("zoneinfo") + 1 :]
        if zone_parts:
            return city_from_timezone_name("/".join(zone_parts))

    return "Local"


@dataclass
class Stopwatch:
    elapsed_before_start: float = 0.0
    started_at: float = 0.0
    running: bool = False

    def elapsed(self) -> float:
        if not self.running:
            return self.elapsed_before_start
        return self.elapsed_before_start + (time.monotonic() - self.started_at)

    def toggle(self) -> None:
        now = time.monotonic()
        if self.running:
            self.elapsed_before_start += now - self.started_at
            self.running = False
        else:
            self.started_at = now
            self.running = True

    def reset(self) -> None:
        self.elapsed_before_start = 0.0
        self.started_at = 0.0
        self.running = False


class Label:
    def __init__(
        self,
        text: str,
        rect: Sequence[float],
        *,
        font_name: str,
        font_size: float,
        color: Sequence[float] = INK,
        align: str = "center",
    ) -> None:
        self.text = Text(
            text,
            dest_rect=rect,
            font_name=font_name,
            font_size=font_size,
            color=color,
            align=align,
        )

    def set_text(self, value: str) -> None:
        self.text.set_text(value)

    def draw(self) -> None:
        self.text.draw()


class Button:
    def __init__(
        self,
        rect: Sequence[float],
        text: str,
        *,
        font_name: str,
        fill: Sequence[float],
        hover_fill: Sequence[float],
    ) -> None:
        self.rect = list(rect)
        self.fill = fill
        self.hover_fill = hover_fill
        self.box = Rectangle(rect, fill=True, color=fill)
        self.border = Rectangle(rect, fill=False, thickness=1.5, color=INK)
        self.label = Label(text, rect, font_name=font_name, font_size=24, color=(255, 255, 255))

    def contains(self, point: tuple[float, float] | None) -> bool:
        if point is None:
            return False
        x, y = point
        return self.box.hit_test(x, y)

    def set_text(self, text: str) -> None:
        self.label.set_text(text)

    def draw(self, mouse_position: tuple[float, float] | None) -> None:
        self.box.set_color(self.hover_fill if self.contains(mouse_position) else self.fill)
        self.box.draw()
        self.border.draw()
        self.label.draw()


def draw_clock(center_x: float, center_y: float, radius: float, now: datetime) -> None:
    Circle((center_x, center_y), radius, fill=True, color=PANEL, num_segments=1000).draw()
    Circle((center_x, center_y), radius, fill=False, thickness=3.0, color=INK, num_segments=1000).draw()

    for tick in range(60):
        is_hour = tick % 5 == 0
        outer = radius * 0.91
        inner = radius * (0.80 if is_hour else 0.86)
        angle = 2.0 * math.pi * tick / 60.0
        Line(
            clock_endpoint(center_x, center_y, inner, angle),
            clock_endpoint(center_x, center_y, outer, angle),
            thickness=3.0 if is_hour else 1.2,
            color=INK if is_hour else MUTED,
        ).draw()

    second = now.second + now.microsecond / 1_000_000.0
    minute = now.minute + second / 60.0
    hour = (now.hour % 12) + minute / 60.0

    hour_angle = 2.0 * math.pi * hour / 12.0
    minute_angle = 2.0 * math.pi * minute / 60.0
    second_angle = 2.0 * math.pi * second / 60.0

    Line((center_x, center_y), clock_endpoint(center_x, center_y, radius * 0.48, hour_angle), thickness=8.0, color=INK).draw()
    Line((center_x, center_y), clock_endpoint(center_x, center_y, radius * 0.68, minute_angle), thickness=5.0, color=INK).draw()
    Line((center_x, center_y), clock_endpoint(center_x, center_y, radius * 0.76, second_angle), thickness=2.0, color=ACCENT).draw()
    Circle((center_x, center_y), radius * 0.035, fill=True, color=INK, num_segments=48).draw()
    Circle((center_x, center_y), radius * 0.017, fill=True, color=ACCENT, num_segments=48).draw()


def run_demo(args: argparse.Namespace) -> None:
    font_name = args.font or os.environ.get("TACHYPY_FONT", "Avenir Next, Helvetica, Arial")
    city_name = args.city or infer_city_label()
    screen = Screen(
        screen_number=args.screen,
        width=None if args.fullscreen else args.width,
        height=None if args.fullscreen else args.height,
        fullscreen=args.fullscreen,
        backend="glfw",
        vsync=True,
        grab_input=False,
    )

    try:
        responses = ResponseHandler(keys_to_listen=["space", "r", "escape"], screen=screen)
        stopwatch = Stopwatch()
        city_label = Label(city_name.upper(), [0, 0, 1, 1], font_name=font_name, font_size=42, color=INK)
        date_label = Label("", [0, 0, 1, 1], font_name=font_name, font_size=28, color=MUTED)
        timer_title = Label("STOP TIMER", [0, 0, 1, 1], font_name=font_name, font_size=22, color=MUTED)
        timer_value = Label("00:00.00", [0, 0, 1, 1], font_name=font_name, font_size=78, color=INK)
        hint = Label("Esc exits  ·  Space starts/stops  ·  R resets", [0, 0, 1, 1], font_name=font_name, font_size=20, color=MUTED)

        start_stop_button: Button | None = None
        reset_button: Button | None = None
        consumed_mouse_clicks = 0
        reset_key_was_down = False

        while True:
            width, height = screen.width, screen.height
            now = datetime.now()
            responses.get_events()
            mouse_position = responses.get_mouse_position()

            clock_center_x = width * 0.31
            clock_center_y = height * 0.52
            clock_radius = min(width * 0.235, height * 0.37)

            panel_left = width * 0.63
            panel_top = height * 0.25
            panel_right = width * 0.91
            panel_bottom = height * 0.70
            button_top = panel_top + (panel_bottom - panel_top) * 0.66
            button_height = 58
            gap = 18
            button_width = (panel_right - panel_left - gap * 3) / 2

            start_rect = [panel_left + gap, button_top, panel_left + gap + button_width, button_top + button_height]
            reset_rect = [panel_left + gap * 2 + button_width, button_top, panel_right - gap, button_top + button_height]

            if start_stop_button is None or reset_button is None:
                start_stop_button = Button(
                    start_rect,
                    "START",
                    font_name=font_name,
                    fill=ACCENT,
                    hover_fill=ACCENT_DARK,
                )
                reset_button = Button(
                    reset_rect,
                    "RESET",
                    font_name=font_name,
                    fill=RESET,
                    hover_fill=RESET_DARK,
                )
            else:
                start_stop_button.box.set_rect(start_rect)
                start_stop_button.border.set_rect(start_rect)
                start_stop_button.label.text.set_dest_rect(start_rect)
                reset_button.box.set_rect(reset_rect)
                reset_button.border.set_rect(reset_rect)
                reset_button.label.text.set_dest_rect(reset_rect)

            if responses.should_quit() or responses.was_key_pressed("escape"):
                break
            if responses.was_key_pressed("space"):
                stopwatch.toggle()
            reset_key_is_down = responses.is_key_down("r")
            if responses.was_key_pressed("r") or (reset_key_is_down and not reset_key_was_down):
                stopwatch.reset()
            reset_key_was_down = reset_key_is_down
            new_mouse_clicks = responses.mouse_clicks[consumed_mouse_clicks:]
            consumed_mouse_clicks = len(responses.mouse_clicks)
            for click in new_mouse_clicks:
                if click["type"] != "mousedown":
                    continue
                click_position = click["pos"]
                if start_stop_button.contains(click_position):
                    stopwatch.toggle()
                elif reset_button.contains(click_position):
                    stopwatch.reset()

            start_stop_button.set_text("STOP" if stopwatch.running else "START")
            timer_value.set_text(format_elapsed(stopwatch.elapsed()))
            date_label.set_text(now.strftime("%A, %B %-d") if os.name != "nt" else now.strftime("%A, %B %#d"))

            city_label.text.set_dest_rect([clock_center_x - 260, clock_center_y - clock_radius - 76, clock_center_x + 260, clock_center_y - clock_radius - 42])
            date_label.text.set_dest_rect([clock_center_x - 260, clock_center_y + clock_radius + 30, clock_center_x + 260, clock_center_y + clock_radius + 70])
            timer_title.text.set_dest_rect([panel_left, panel_top + 38, panel_right, panel_top + 72])
            timer_value.text.set_dest_rect([panel_left, panel_top + 132, panel_right, panel_top + 222])
            hint.text.set_dest_rect([0, height - 58, width, height - 24])

            screen.fill(BACKGROUND)
            Rectangle([panel_left, panel_top, panel_right, panel_bottom], fill=True, color=PANEL).draw()
            Rectangle([panel_left, panel_top, panel_right, panel_bottom], fill=False, thickness=2.0, color=PANEL_STROKE).draw()
            draw_clock(clock_center_x, clock_center_y, clock_radius, now)
            city_label.draw()
            date_label.draw()
            timer_title.draw()
            timer_value.draw()
            start_stop_button.draw(mouse_position)
            reset_button.draw(mouse_position)
            hint.draw()
            screen.flip()
    finally:
        screen.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TachyPy GLFW analog clock and stopwatch demo.")
    parser.add_argument("--windowed", dest="fullscreen", action="store_false", help="run in a window instead of fullscreen")
    parser.add_argument("--width", type=int, default=1280, help="window width when using --windowed")
    parser.add_argument("--height", type=int, default=720, help="window height when using --windowed")
    parser.add_argument("--screen", type=int, default=0, help="monitor index for fullscreen mode")
    parser.add_argument("--font", default="", help="system font family/path, or comma-separated fallback list")
    parser.add_argument("--city", default="", help="override the inferred city label shown under LOCAL TIME")
    parser.set_defaults(fullscreen=True)
    return parser.parse_args()


def main() -> None:
    run_demo(parse_args())


if __name__ == "__main__":
    main()
