"""Configurable pressure-hold lesson around experiment-provided trial content.

:class:`GifUwuHoldTrial` extends :class:`~tachypy.instruction_demos.GifUwuFixationCross`
with a simulated monitor in which *your* experiment draws its own trial (cue,
stimulus, response...) while a side-view keypad shows the finger pressure that
goes with it. Typical use: contrast a trial where pressure is released (bad) with
one where it is held (good).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Callable, Sequence

from tachypy.shapes import Rectangle

from .keypad import GifUwuFixationCross, _ease_in_out

@dataclass(frozen=True)
class HoldDemoPhase:
    """One timed scene and its keyboard-pressure behavior."""

    name: str
    duration: float
    scene: str
    pressure_mode: str = "green"
    show_cross: bool = False
    attempt: str | None = None
    response: str | None = None


@dataclass(frozen=True)
class TrialDemoFrame:
    """State passed to the experiment's ``trial_drawer`` each frame."""

    phase_name: str
    scene: str
    attempt: str | None
    progress: float
    language: str
    display_rect: tuple[float, float, float, float]
    cross_center: tuple[float, float]
    content_scale: float
    left_pressure: float
    right_pressure: float
    response: str | None = None


TrialDrawer = Callable[[TrialDemoFrame], None]
PressureProvider = Callable[[HoldDemoPhase, float], tuple[float, float]]


class GifUwuHoldTrial(GifUwuFixationCross):
    """Animate a pressure lesson around experiment-provided trial content.

    ``trial_drawer`` draws only task-specific content in ``display_rect``.
    ``phases`` controls the scenes and timing. ``pressure_provider`` may replace
    the built-in pressure behaviors for a completely custom interaction.

    Built-in pressure modes are ``released``, ``ramp_to_green``, ``green``,
    ``lose_left``, ``left_weak``, ``remove_left``, ``left_released``,
    ``recover_left``, ``respond_left``, ``respond_right``, and ``release``.
    """

    def __init__(
        self,
        screen,
        *,
        trial_drawer: TrialDrawer,
        phases: Sequence[HoldDemoPhase],
        pressure_provider: PressureProvider | None = None,
        language: str = "Fr",
        background_color=(128, 128, 128),
        keyboard_width: float = 300.0,
        monitor_width: float | None = None,
        content_top: float | None = None,
        content_bottom: float | None = None,
        min_pressure_start: float = 0.33,
        max_pressure_start: float = 0.66,
        threshold: float = 0.8,
        playback_speed: float = 1.0,
        loop: bool = False,
    ):
        super().__init__(
            screen,
            background_color=background_color,
            keyboard_width=keyboard_width,
            top_y=0,
            min_pressure_start=min_pressure_start,
            max_pressure_start=max_pressure_start,
            threshold=threshold,
            cross_half_size=28.0,
            cross_thickness=8.0,
            show_pressure_text=False,
            loop=False,
        )
        self.language = str(language)
        self.loop = bool(loop)
        self.playback_speed = float(playback_speed)
        if self.playback_speed <= 0:
            raise ValueError("playback_speed must be greater than zero")
        self.trial_drawer = trial_drawer
        self.pressure_provider = pressure_provider or self._default_pressures
        self.phases = tuple(phases)
        if not self.phases or any(phase.duration <= 0 for phase in self.phases):
            raise ValueError("phases must contain only positive durations")
        self.timeline_duration = sum(phase.duration for phase in self.phases)
        self.duration = self.timeline_duration / self.playback_speed

        self._layout_monitor(monitor_width, content_top=content_top, content_bottom=content_bottom)
        self._layout_side_keyboard()

    def _layout_monitor(
        self,
        monitor_width: float | None,
        content_top: float | None = None,
        content_bottom: float | None = None,
    ) -> None:
        """Place the monitor (and, via `_layout_side_keyboard`, the keyboard below it).

        With no `content_top`/`content_bottom`, anchors near the top of the screen
        (the standalone preview's own look). With both given -- e.g. the space left
        between a caller's top instruction text and bottom caption -- the monitor
        shrinks (its 16:9 ratio kept, the keyboard's own size untouched) only as
        much as needed for the whole monitor+keyboard block to fit inside that
        window, then centers it there, so it never collides with either.
        """
        width_cap = float(monitor_width or min(720.0, self.screen.width * 0.60))
        cx = self.screen.width / 2.0
        default_top = max(38.0, self.screen.height * 0.055)

        if content_bottom is None:
            height = min(width_cap * 9.0 / 16.0, self.screen.height * 0.45)
            width = width_cap
            top = default_top if content_top is None else float(content_top)
        else:
            top_bound = default_top if content_top is None else float(content_top)
            gap_to_keyboard = max(28.0, self.screen.height * 0.04)
            side_height = self._side_rect[3] - self._side_rect[1]
            available_height = max(1.0, float(content_bottom) - top_bound - gap_to_keyboard - side_height)
            height = min(width_cap * 9.0 / 16.0, self.screen.height * 0.45, available_height)
            width = height * 16.0 / 9.0
            block_height = height + gap_to_keyboard + side_height
            top = top_bound + max(0.0, (float(content_bottom) - top_bound - block_height) / 2.0)

        self._monitor_rect = (cx - width / 2.0, top, cx + width / 2.0, top + height)
        bezel = max(6.0, width * 0.012)
        self._display_rect = (
            self._monitor_rect[0] + bezel,
            self._monitor_rect[1] + bezel,
            self._monitor_rect[2] - bezel,
            self._monitor_rect[3] - bezel,
        )
        inner_height = self._display_rect[3] - self._display_rect[1]
        self._cross_center = (cx, self._display_rect[1] + inner_height * 0.42)

    def _layout_side_keyboard(self) -> None:
        side_width = self._side_rect[2] - self._side_rect[0]
        side_height = self._side_rect[3] - self._side_rect[1]
        cx = self.screen.width / 2.0
        visible_top = self._monitor_rect[3] + max(28.0, self.screen.height * 0.04)
        side_top = visible_top - side_height * (102.0 / 380.0)
        self._side_rect = (
            cx - side_width / 2.0,
            side_top,
            cx + side_width / 2.0,
            side_top + side_height,
        )

    def _elapsed(self) -> float:
        if self._t0 is None:
            return 0.0
        elapsed = (time.perf_counter() - self._t0) * self.playback_speed
        if self.loop:
            return elapsed % self.timeline_duration
        return min(elapsed, self.timeline_duration)

    def _phase_at(self, elapsed: float) -> tuple[HoldDemoPhase, float]:
        cursor = 0.0
        for phase in self.phases:
            end = cursor + phase.duration
            if elapsed < end:
                return phase, (elapsed - cursor) / phase.duration
            cursor = end
        return self.phases[-1], 1.0

    @staticmethod
    def _green_pressures(progress: float) -> tuple[float, float]:
        variation = 0.035 * math.sin(2.0 * math.pi * progress)
        return 0.55 + variation, 0.45 + variation

    def _default_pressures(self, phase: HoldDemoPhase, progress: float) -> tuple[float, float]:
        """Return pressures for the reusable behavior named by the phase."""
        mode = phase.pressure_mode
        if mode == "released":
            return 0.0, 0.0
        if mode == "ramp_to_green":
            ramp = _ease_in_out(progress)
            return 0.55 * ramp, 0.45 * ramp
        if mode == "green":
            return self._green_pressures(progress)
        if mode == "lose_left":
            left, right = self._green_pressures(progress)
            loss = _ease_in_out((progress - 0.45) / 0.18)
            return left + (0.12 - left) * loss, right
        if mode == "left_weak":
            return 0.12, 0.45
        if mode == "remove_left":
            left, right = self._green_pressures(progress)
            removal = _ease_in_out((progress - 0.40) / 0.60)
            return left * (1.0 - removal), right
        if mode == "left_released":
            return 0.0, 0.45
        if mode == "recover_left":
            return 0.12 + 0.43 * _ease_in_out(progress), 0.45
        if mode == "respond_left":
            return 0.55 + 0.37 * _ease_in_out(progress), 0.45
        if mode == "respond_right":
            return 0.55, 0.45 + 0.37 * _ease_in_out(progress)
        if mode == "release":
            release = 1.0 - _ease_in_out(progress)
            return 0.55 * release, 0.45 * release
        raise ValueError(f"Unknown pressure mode: {mode!r}")

    def draw(self, screen=None) -> None:
        """Draw the generic shell, then call the experiment's renderer."""
        if self._t0 is None:
            self.start()
        elapsed = self._elapsed()
        phase, progress = self._phase_at(elapsed)
        left, right = self.pressure_provider(phase, progress)
        self.state.update(left_pressure=left, right_pressure=right, now=elapsed)

        frame = TrialDemoFrame(
            phase_name=phase.name,
            scene=phase.scene,
            attempt=phase.attempt,
            progress=progress,
            language=self.language,
            display_rect=self._display_rect,
            cross_center=self._cross_center,
            content_scale=getattr(self.screen, "content_scale", 2.0),
            left_pressure=left,
            right_pressure=right,
            response=phase.response,
        )

        # Draw first: flattened transparent padding must not erase the monitor.
        self._side_base_texture.draw(self._side_rect)
        self._draw_side_key("left", left)
        self._draw_side_key("right", right)
        self._draw_side_case_edge()

        self._draw_monitor()
        if phase.show_cross:
            self._draw_cross()
        self.trial_drawer(frame)

    def _draw_monitor(self) -> None:
        x1, y1, x2, y2 = self._monitor_rect
        cx = (x1 + x2) / 2.0
        Rectangle((cx - 18, y2, cx + 18, y2 + 14), fill=True, color=(37, 42, 52)).draw()
        Rectangle((cx - 70, y2 + 12, cx + 70, y2 + 20), fill=True, color=(37, 42, 52)).draw()
        Rectangle(self._monitor_rect, fill=True, color=(37, 42, 52)).draw()
        Rectangle(self._display_rect, fill=True, color=self.background_color).draw()
