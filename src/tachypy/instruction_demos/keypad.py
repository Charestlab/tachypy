"""Animated UwU-keypad demos for instruction screens: fixation-cross hold, slider, full trial.

The demos are scripted by default (no keyboard or TachyWooting needed), so they can be
shown while presenting the instructions, before a participant touches the hardware. The
fixation-cross and slider demos can also follow the participant's real pressures:
``mode`` is ``"video"``, ``"interactive"`` or ``"video_then_interactive"`` (see
:class:`LiveDemoMixin`).

- :class:`GifUwuScrollbar` -- keyboard image under a :class:`~tachypy.scrollbar.Scrollbar`
  whose red cursor and key square use the real hold-to-speed math
  (:mod:`tachypy.scrollbar_interaction`).
- :class:`GifUwuFixationCross` -- top-view keyboard fading into a side view whose keycaps
  travel and recolor with the pressures; they also drive a
  :class:`~tachypy.feedback.PressureFeedbackState`, so the cross behaves as in a live trial.
- :class:`GifUwuHoldTrial` -- a fixation-cross lesson around your own trial drawer.

:class:`~tachypy.Texture` is RGB-only, so the transparent keyboard PNGs are composited
onto ``background_color`` at load time; set it to the screen fill.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np
from OpenGL.GL import (
    GL_LINE_LOOP,
    GL_MODULATE,
    GL_QUADS,
    GL_TEXTURE_ENV,
    GL_TEXTURE_ENV_MODE,
    GL_TRIANGLE_FAN,
    glBegin,
    glColor3f,
    glColor4f,
    glEnd,
    glLineWidth,
    glTexCoord2f,
    glTexEnvf,
    glVertex2f,
)

from tachypy.feedback import PressureFeedbackConfig, PressureFeedbackState
from tachypy.scrollbar import Scrollbar
from tachypy.scrollbar_interaction import SliderControls, _accelerated_step, _edge_scale, _movement_direction
from tachypy.shapes import Line, Rectangle
from tachypy.text import Text
from tachypy.textures import Texture

_ASSETS = Path(__file__).parent / "assets"
_KEYBOARD_PNG = str(_ASSETS / "wooting_keyboard.png")
_SIDE_PNG = str(_ASSETS / "wooting_keyboard_side.png")
_SIDE_BASE_PNG = str(_ASSETS / "wooting_keyboard_side_base.png")

# Key-face centers as fractions of the top-view image (from the SVG 808×606 viewBox).
_KEY_FRACS = {"z": (0.2426, 0.4637), "c": (0.7574, 0.4637)}
_KB_ASPECT = 1212 / 1616  # top-view image height / width (= 0.75)

# Widget-bottom → keyboard-top gap (fraction of keyboard width), shared so both demos align.
_KEYBOARD_GAP_FRAC = 0.22
# Scrollbar half-height below position_y (its end markers, tachypy half_end_height = 20, are the lowest point).
_SCROLLBAR_HALF_HEIGHT = 20.0


def _load_keyboard_rgb(path: str, background_color) -> np.ndarray:
    """Load a transparent keyboard PNG and flatten it onto ``background_color``."""
    try:
        from PIL import Image
    except ImportError as exc:  # Pillow is an optional dependency of the demos
        raise ImportError(
            "The instruction demos load PNG images with Pillow: pip install 'tachypy[wooting]' "
            "(or pip install Pillow)."
        ) from exc
    img = Image.open(path).convert("RGBA")
    canvas = Image.new("RGBA", img.size, (*background_color, 255))
    canvas.alpha_composite(img)
    return np.asarray(canvas.convert("RGB"), dtype=np.uint8)


def _ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, float(t)))
    return 0.5 - 0.5 * math.cos(math.pi * t)


def _lerp_color(start, end, progress: float):
    progress = max(0.0, min(1.0, float(progress)))
    return tuple(int(round(s + (e - s) * progress)) for s, e in zip(start, end))


MODES = ("video", "interactive", "video_then_interactive")
#: Pressure above which a key press hands a ``video_then_interactive`` demo to the participant.
DEFAULT_TAKEOVER_PRESSURE = 15 / 255


class LiveDemoMixin:
    """Mode handling, live pressure polling and the blocking :meth:`play` loop.

    Subclasses call :meth:`_init_live` in ``__init__``, route ``draw`` through
    :meth:`_poll_live`, and implement :meth:`_on_takeover` (what "live" starts from).
    """

    def _init_live(self, mode, source, pressure_reader, left_key, right_key, takeover_pressure):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {', '.join(MODES)}; got {mode!r}")
        if mode != "video" and source is None and pressure_reader is None:
            raise ValueError(f"mode={mode!r} needs a pressure source: pass source= or pressure_reader=")
        if source is not None and pressure_reader is not None:
            raise ValueError("pass either source= or pressure_reader=, not both")
        self.mode = mode
        self.source = source
        self.left_key = str(left_key).lower()
        self.right_key = str(right_key).lower()
        if self.left_key == self.right_key:
            raise ValueError("left_key and right_key must differ")
        self.takeover_pressure = float(takeover_pressure)
        self._pressure_reader = pressure_reader
        self._live = False
        self._ever_live = False
        self._armed = True  # False while keys are still held from before the demo started

    @property
    def is_live(self) -> bool:
        """True while the participant's real pressures drive the demo."""
        return self._live

    @property
    def is_complete(self) -> bool:
        """True once the demo's own goal is met (e.g. the cross completed ``max_completions`` times)."""
        return False

    @property
    def caption_ready(self) -> bool:
        """True once the participant has seen one full video pass, or has taken control."""
        if self.mode == "interactive" or self._ever_live:
            return True
        return self._t0 is not None and time.perf_counter() - self._t0 >= self.duration

    def start(self):
        """(Re)start the demo from the beginning (an interactive demo is live at once)."""
        self._t0 = time.perf_counter()
        self._live = self._ever_live = False
        self._armed = self.mode != "video_then_interactive"  # keys already down must be released first
        if self.mode != "video":
            validate = getattr(self.source, "validate_analog_keys", None)
            if callable(validate):
                validate((self.left_key, self.right_key))
        if self.mode == "interactive":
            self._begin_live(self._t0, from_start=True)

    def _read_live(self) -> tuple[float, float]:
        if self._pressure_reader is not None:
            left, right = self._pressure_reader()
        else:
            pressures = self.source.read_pressures((self.left_key, self.right_key))
            left, right = pressures[self.left_key], pressures[self.right_key]
        return float(left), float(right)

    def _begin_live(self, now: float, *, from_start: bool = False) -> None:
        self._live = self._ever_live = True
        self._on_takeover(now, from_start)

    def _poll_live(self, now: float):
        """Return the live ``(left, right)`` pressures, or None while the video plays."""
        if self.mode == "video":
            return None
        pair = self._read_live()
        if not self._live:
            if not self._armed:
                self._armed = max(pair) <= self.takeover_pressure
                return None
            if max(pair) <= self.takeover_pressure:
                return None
            self._begin_live(now)
        return pair

    def _on_takeover(self, now: float, from_start: bool) -> None:
        raise NotImplementedError

    def play(
        self,
        response_handler,
        *,
        exit_keys: Sequence[str] = ("x",),
        drawables: Sequence[object] = (),
        caption=None,
        background_color=None,
        pause_after_completion: float = 0.6,
    ) -> str | None:
        """Run the demo until an exit key is pressed or it completes (blocking, one frame per flip).

        Parameters
        ----------
        response_handler : ResponseHandler-like
            Polled each frame for exit keys and window-close / Escape.
        exit_keys : sequence of str
            Keys that end the demo (default ``("x",)``).
        drawables : sequence
            Objects with ``draw()`` drawn under the demo every frame (e.g. the
            instruction text).
        caption : object, optional
            Drawn only once :attr:`caption_ready` (e.g. a "press [X] to continue" hint).
        background_color : sequence of int, optional
            Screen fill; defaults to the demo's ``background_color``.
        pause_after_completion : float
            Seconds the finished demo stays on screen once :attr:`is_complete`.

        Returns
        -------
        str or None
            The exit key that was pressed, ``"completed"`` when the demo completed, or
            None if the window was closed / Escape.
        """
        keys = [str(key).lower() for key in exit_keys]
        listened = getattr(response_handler, "keys_to_listen", None)
        if listened is not None:
            response_handler.keys_to_listen = sorted({str(k).lower() for k in listened} | set(keys))
            if hasattr(response_handler, "_probed_keys"):
                response_handler._probed_keys.update(keys)
        fill = self.background_color if background_color is None else background_color
        self.start()
        completed_at = None
        while True:
            response_handler.get_events()
            if response_handler.should_quit():
                return None
            for key in keys:
                if response_handler.was_key_pressed(key):
                    return key
            if self.is_complete:
                completed_at = time.perf_counter() if completed_at is None else completed_at
                if time.perf_counter() - completed_at >= pause_after_completion:
                    return "completed"
            self.screen.fill(fill)
            for drawable in drawables:
                drawable.draw()
            self.draw(self.screen)
            if caption is not None and self.caption_ready:
                caption.draw()
            self.screen.flip()


class GifUwuScrollbar(LiveDemoMixin):
    """Scripted UwU-keyboard → scrollbar animation, drawable in a TachyPy loop.

    The keyboard is a fixed image; only the red key square and the scrollbar
    cursor move. The cursor follows the same hold-to-speed math as the real
    analog interaction (:mod:`tachypy.scrollbar_interaction`), driven toward
    scripted targets so the loop closes exactly on ``initial_value``.

    Parameters
    ----------
    screen : tachypy.Screen
        Display the widget is drawn on; used for size and ``content_scale``.
    background_color : sequence of int
        RGB fill the transparent keyboard PNG is composited onto (set it to the
        experiment's screen fill), since ``tachypy.Texture`` has no alpha.
    keyboard_png : str
        Path to the keyboard image.
    keyboard_width, scrollbar_width : float, optional
        On-screen widths in pixels; ``None`` falls back to
        ``DEFAULT_KEYBOARD_WIDTH`` / ``DEFAULT_SCROLLBAR_WIDTH``. Independent.
    top_y, gap : float, optional
        Block top and scrollbar→keyboard gap; ``None`` centers the block and
        uses ``KEYBOARD_GAP_FRAC × keyboard_width``.
    key_square_frac : float
        Red key-square side as a fraction of ``keyboard_width``.
    key_color, key_text_color : sequence of int
        RGB of the key square / scrollbar cursor, and of the key letter.
    movement_speed, acceleration, curve_x, curve_y, edge_margin, edge_reduction : float
        Hold-to-speed math (same defaults as ``run_slider_interaction``).
    initial_value, right_target, left_target : float
        Loop start/close value, the C extremity, and the Z target.
    rest_start, rest_mid, rest_end : float
        Seconds held still before, between, and after the key sweeps.
    sim_hz : float
        Trajectory sampling rate.
    loop : bool
        Replay forever instead of stopping after one pass.
    mode : {"video", "interactive", "video_then_interactive"}
        Who drives the cursor: the scripted animation, the participant's real Z / C
        pressures (same hold-to-speed math), or the animation until the first press.
    source, pressure_reader :
        Live pressures for the interactive modes: an object with
        ``read_pressures(keys)`` (e.g. a ``WOOTING_ACQUISITION``), or a callable
        returning ``(left, right)`` in 0-1. Pass at most one.
    left_key, right_key : str
        Keys read from ``source``; left moves the cursor left, right moves it right.
    takeover_pressure, pressure_deadzone : float
        Pressure that hands a ``video_then_interactive`` demo to the participant, and
        the deadzone below which a live key does not move the cursor.

    Example
    -------
    >>> demo = GifUwuScrollbar(screen, mode="video_then_interactive", source=wooting, loop=True)
    >>> demo.play(response_handler, exit_keys=("x",))  # video until Z / C is pressed, then live
    """

    #: Keyboard width (px) when ``keyboard_width`` is None.
    DEFAULT_KEYBOARD_WIDTH = 300
    #: Bar-bottom→keyboard-top gap (fraction of keyboard width), shared with GifUwuFixationCross.
    KEYBOARD_GAP_FRAC = _KEYBOARD_GAP_FRAC
    #: Full scrollbar width (px) when ``scrollbar_width`` is None (independent of the keyboard).
    DEFAULT_SCROLLBAR_WIDTH = 420

    def __init__(
        self,
        screen,
        *,
        background_color=(128, 128, 128),
        keyboard_png: str = _KEYBOARD_PNG,
        keyboard_width: float | None = None,
        top_y: float | None = None,
        gap: float | None = None,
        key_square_frac: float = 0.20,
        key_color=(255, 45, 45),
        key_text_color=(255, 255, 255),
        movement_speed: float = 100.0,
        acceleration: float = 100.0,
        curve_x: float = -0.25,
        curve_y: float = -0.03,
        edge_margin: float = 10.0,
        edge_reduction: float = 0.6,
        initial_value: float = 50.0,
        right_target: float = 99.0,
        left_target: float = 25.0,
        rest_start: float = 0.20,
        rest_mid: float = 0.10,
        rest_end: float = 0.25,
        scrollbar_width: float | None = None,
        sim_hz: float = 250.0,
        loop: bool = False,
        mode: str = "video",
        source=None,
        pressure_reader=None,
        left_key: str = "z",
        right_key: str = "c",
        takeover_pressure: float = DEFAULT_TAKEOVER_PRESSURE,
        pressure_deadzone: float = 15 / 255,
    ):
        self._init_live(mode, source, pressure_reader, left_key, right_key, takeover_pressure)
        self.screen = screen
        self.background_color = tuple(int(c) for c in background_color)
        self.loop = bool(loop)
        self.key_color = tuple(int(c) for c in key_color)
        self.key_text_color = tuple(int(c) for c in key_text_color)
        self.sim_hz = float(sim_hz)

        # Scrollbar on top, keyboard below; the centered layout matches GifUwuFixationCross so the demos align.
        W = float(keyboard_width if keyboard_width is not None else self.DEFAULT_KEYBOARD_WIDTH)
        H = W * _KB_ASPECT
        gap = W * self.KEYBOARD_GAP_FRAC if gap is None else float(gap)
        sb_width = float(scrollbar_width if scrollbar_width is not None else self.DEFAULT_SCROLLBAR_WIDTH)
        cx = screen.width / 2.0
        if top_y is None:
            # Same rule as GifUwuFixationCross: keyboard `gap` below the widget's lowest point, rect centered.
            kb_top = (screen.height - H + gap) / 2.0
            sb_y = kb_top - gap - _SCROLLBAR_HALF_HEIGHT  # bar bottom (end markers) = kb_top - gap
        else:
            sb_band = 50.0  # vertical extent of the label-free scrollbar
            block_top = float(top_y)
            sb_y = block_top + sb_band / 2.0
            kb_top = block_top + sb_band + gap
        self._kb_rect = [cx - W / 2.0, kb_top, cx + W / 2.0, kb_top + H]

        # Red key-square size + on-screen centers for Z and C.
        self._sq = W * float(key_square_frac)
        self._key_xy = {
            k: (cx - W / 2.0 + fx * W, kb_top + fy * H) for k, (fx, fy) in _KEY_FRACS.items()
        }

        self._texture = Texture(_load_keyboard_rgb(keyboard_png, self.background_color))

        # Clean scrollbar: no intermediate ticks, no 0/100 endpoint labels.
        self.scrollbar = Scrollbar(
            screen_width=screen.width,
            screen_height=screen.height,
            position_y=sb_y,
            half_bar_length=sb_width / 2.0,
            num_marks=2,
            text_left="",
            text_right="",
            content_scale=getattr(screen, "content_scale", 2.0),
        )
        self.scrollbar.mobile_line_color = self.key_color
        self.scrollbar.mobile_line.set_color(self.key_color)

        self._times, self._values, self._keys = self._build_trajectory(
            movement_speed=movement_speed, acceleration=acceleration,
            curve_x=curve_x, curve_y=curve_y,
            edge_margin=edge_margin, edge_reduction=edge_reduction,
            initial_value=initial_value, right_target=right_target,
            left_target=left_target, rest_start=rest_start,
            rest_mid=rest_mid, rest_end=rest_end,
        )
        self.duration = float(self._times[-1]) if len(self._times) else 0.0
        self._t0: float | None = None
        self._initial_value = float(initial_value)
        self._motion = (acceleration, movement_speed, curve_x, curve_y, edge_margin, edge_reduction)
        self._pressure_deadzone = float(pressure_deadzone)
        self._live_value = self._initial_value
        self._live_hold = 0.0
        self._live_direction = 0
        self._live_last = 0.0

    def _build_trajectory(self, *, movement_speed, acceleration, curve_x, curve_y,
                          edge_margin, edge_reduction, initial_value,
                          right_target, left_target, rest_start, rest_mid, rest_end):
        """Drive the real hold-to-speed math toward targets, then rest.

        Sequence: middle → (hold C) right extremity → (hold Z) ``left_target``
        → (hold C) middle. Each phase is *target-driven* and clamps exactly onto
        its target on the crossing step, so the animation ends precisely at the
        start value and loops seamlessly — even though the edge slow-down near an
        end breaks the symmetry of equal-duration holds.
        """
        dt = 1.0 / self.sim_hz
        value = float(initial_value)
        t = 0.0
        times, values, keys = [], [], []

        def record(key: str) -> None:
            nonlocal t
            t += dt
            times.append(t)
            values.append(value)
            keys.append(key)

        def rest(seconds: float) -> None:
            for _ in range(max(0, int(round(seconds / dt)))):
                record("")

        def hold_to(key: str, target: float) -> None:
            nonlocal value
            direction = -1 if key == "z" else 1
            hold = 0.0
            for _ in range(int(10.0 / dt)):  # safety bound
                if (value >= target) if direction > 0 else (value <= target):
                    break
                dist, hold = _accelerated_step(hold, dt, acceleration, movement_speed, curve_x, curve_y)
                dist *= _edge_scale(value, direction, edge_margin, edge_reduction)
                nxt = value + direction * dist
                if (direction > 0 and nxt >= target) or (direction < 0 and nxt <= target):
                    nxt = target  # land exactly on the target
                value = float(np.clip(nxt, 0.0, 100.0))
                record(key)

        rest(rest_start)
        hold_to("c", float(right_target))     # middle → right extremity
        rest(rest_mid)
        hold_to("z", float(left_target))      # right → left_target (25 before the left edge)
        rest(rest_mid)
        hold_to("c", float(initial_value))    # left_target → middle (closes the loop)
        rest(rest_end)
        return np.asarray(times), np.asarray(values), keys

    @property
    def is_finished(self) -> bool:
        if self.loop or self._live or self._t0 is None or self.duration <= 0:
            return False
        return (time.perf_counter() - self._t0) >= self.duration

    def _on_takeover(self, now: float, from_start: bool) -> None:
        """Continue from the scripted cursor position (or ``initial_value`` when interactive-only)."""
        self._live_value = self._initial_value if from_start else self._sample()[0]
        self._live_hold, self._live_direction, self._live_last = 0.0, 0, now

    def _step_live(self, now: float, left: float, right: float):
        """Advance the cursor with the real hold-to-speed math; return (value, key)."""
        acceleration, speed, curve_x, curve_y, edge_margin, edge_reduction = self._motion
        dt = min(max(0.0, now - self._live_last), 0.1)
        self._live_last = now
        direction = _movement_direction(SliderControls(decrease=left, increase=right), self._pressure_deadzone)
        if direction == 0:
            self._live_hold = 0.0
        else:
            if direction != self._live_direction:
                self._live_hold = 0.0
            distance, self._live_hold = _accelerated_step(
                self._live_hold, dt, acceleration, speed, curve_x, curve_y)
            distance *= _edge_scale(self._live_value, direction, edge_margin, edge_reduction)
            self._live_value = float(np.clip(self._live_value + direction * distance, 0.0, 100.0))
        self._live_direction = direction
        return self._live_value, {-1: "z", 0: "", 1: "c"}[direction]

    def _sample(self):
        """Return (value, key) for the current elapsed time."""
        if self._t0 is None:
            return float(self._values[0]), self._keys[0]
        t = time.perf_counter() - self._t0
        if self.loop and self.duration > 0:
            t = t % self.duration
        idx = int(min(max(t * self.sim_hz, 0.0), len(self._values) - 1))
        return float(self._values[idx]), self._keys[idx]

    def draw(self, screen=None) -> None:
        """Draw the keyboard, the animated scrollbar, and the red key square."""
        if self._t0 is None:
            self.start()
        now = time.perf_counter()
        live = self._poll_live(now)
        value, key = self._sample() if live is None else self._step_live(now, *live)

        self._texture.draw(self._kb_rect)

        self.scrollbar.set_value(value)
        self.scrollbar.draw()

        if key in self._key_xy:
            kx, ky = self._key_xy[key]
            s = self._sq
            Rectangle([kx - s / 2, ky - s / 2, kx + s / 2, ky + s / 2],
                      fill=True, color=self.key_color).draw()
            Text(
                key.upper(),
                dest_rect=(kx - s / 2, ky - s / 2, kx + s / 2, ky + s / 2),
                font_size=s * 0.55,
                color=self.key_text_color,
                content_scale=getattr(self.screen, "content_scale", 2.0),
            ).draw()


# Side-view geometry (from the 808×380 side-view image / its SVG).
_SIDE_ASPECT = 380 / 808
_SIDE_WIDTH_COMPENSATION = 1596 / 1488
_SIDE_KEY_X = {"left": 208.0, "right": 600.0}
_SIDE_VISIBLE_TOP = 102.0
_SIDE_CASE_TOP = 190.0
_SIDE_KEY_TRAVEL = 36.0
_PRESSURE_SEQUENCE_SECONDS = 3.30
# Band the scripted pressures are written for; they are rescaled onto any other band.
_FLASH_SECONDS = 0.6  # how long the check mark shows after a completion
_BAND_DEFAULTS = {"min_pressure_start": 0.33, "max_pressure_start": 0.66, "threshold": 0.8, "hold_seconds": 0.5}


class GifUwuFixationCross(LiveDemoMixin):
    """Scripted UwU-keyboard → fixation-cross pressure animation.

    A top-view keyboard image fades into a side view whose two keycaps travel
    and recolor with scripted pressures; the same pressures drive a TachyPy
    :class:`~tachypy.feedback.PressureFeedbackState`, so the fixation cross
    below grows, recolors, and prints pressure exactly as in a live trial.

    Parameters
    ----------
    screen : tachypy.Screen
        Display the widget is drawn on; used for size and ``content_scale``.
    background_color : sequence of int
        RGB fill the transparent keyboard PNGs are composited onto (no alpha in
        ``tachypy.Texture``); set it to the experiment's screen fill.
    keyboard_png, side_keyboard_png, side_keyboard_base_png : str
        Top view, full side view, and side view without keycaps.
    keyboard_width, top_y, gap : float, optional
        Top-view width (px) and block placement; ``None`` uses
        ``DEFAULT_KEYBOARD_WIDTH``, centers the block, and sets
        ``KEYBOARD_GAP_FRAC × keyboard_width``.
    key_pressure_deadzone : float
        Pressures at or below this read as a released (white) key.
    key_color_min, key_color_max, key_color_ideal : sequence of int
        Keycap RGB for too-weak, too-strong, and in-band pressure.
    min_pressure_start, max_pressure_start, threshold, hold_seconds : float, optional
        ``PressureFeedbackConfig`` band edges, target threshold, and hold time. ``None``
        takes them from ``source`` (judging pressure exactly like the real task), else
        0.33 / 0.66 / 0.8 and 0.5 s (0.3 s interactive). The scripted pressures are
        rescaled onto the band, so "too weak / ideal / too strong" always shows correctly.
    cross_half_size, cross_thickness : float
        Fixation-cross arm half-length and line thickness.
    show_pressure_text, left_pressure_label, right_pressure_label :
        Whether to print each non-ideal pressure beside the cross, and its label.
    pressure_text_color, pressure_text_font_size, pressure_text_width, pressure_text_height, pressure_text_gap, pressure_text_decimals :
        Readout styling (``None`` sizes derive from the screen).
    sim_hz, playback_slowdown : float
        Timeline sampling rate and how much to stretch the 3.3 s pressure script.
    intro_seconds, transition_seconds, settle_seconds, outro_seconds : float
        Durations of the intro hold, top↔side cross-fade, pre-press settle, and outro.
    loop : bool
        Replay forever instead of stopping after one pass.
    mode : {"video", "interactive", "video_then_interactive"}
        Who drives the keycaps and the cross: the scripted animation, the participant's
        real pressures (side view straight away), or the animation until the first
        Z / C press, after which the real pressures take over.
    source, pressure_reader :
        Live pressures for the interactive modes: an object with
        ``read_pressures(keys)`` (e.g. a ``WOOTING_ACQUISITION``), or a callable
        returning ``(left, right)`` in 0-1. Pass at most one.
    left_key, right_key : str
        Keys read from ``source`` (left drives the left arm of the cross).
    takeover_pressure : float
        Pressure above which a key press hands a ``video_then_interactive`` demo over.
    max_completions : int
        Live completions (both keys held in band for ``hold_seconds``, the cross turning
        black) after which the demo is complete: ``is_complete`` / ``is_finished`` become
        True and ``play`` returns ``"completed"``. ``0`` (default) never ends, for free
        practice. ``completions`` holds the running count.
    completion_feedback : bool
        Feedback on real completions: a counter (``completions``, or
        ``completions / max_completions``) below the keypad, and a green check mark beside it
        for 0.6 s after each one.
    completion_label : str
        Optional word before the counter (``"Hits"`` gives ``Hits: 2 / 3``).

    Example
    -------
    >>> demo = GifUwuFixationCross(screen, mode="video_then_interactive", source=wooting,
    ...                            loop=True, max_completions=2)
    >>> demo.play(response_handler, exit_keys=("x",))  # "completed" after two successful holds
    """

    #: Top-view keyboard width (px) when ``keyboard_width`` is None.
    DEFAULT_KEYBOARD_WIDTH = 300
    #: Cross-bottom→keyboard-top gap (fraction of keyboard width), shared with GifUwuScrollbar.
    KEYBOARD_GAP_FRAC = _KEYBOARD_GAP_FRAC

    def __init__(
        self,
        screen,
        *,
        background_color=(128, 128, 128),
        keyboard_png: str = _KEYBOARD_PNG,
        side_keyboard_png: str = _SIDE_PNG,
        side_keyboard_base_png: str = _SIDE_BASE_PNG,
        keyboard_width: float | None = None,
        top_y: float | None = None,
        gap: float | None = None,
        key_pressure_deadzone: float = 0.01,
        key_color_min=(255, 150, 150),
        key_color_max=(255, 45, 45),
        key_color_ideal=(72, 190, 110),
        min_pressure_start: float | None = None,
        max_pressure_start: float | None = None,
        threshold: float | None = None,
        hold_seconds: float | None = None,
        cross_half_size: float = 36.0,
        cross_thickness: float = 10.0,
        show_pressure_text: bool = True,
        left_pressure_label: str = "Z",
        right_pressure_label: str = "C",
        pressure_text_color=(0, 0, 0),
        pressure_text_font_size: int | None = None,
        pressure_text_width: float | None = None,
        pressure_text_height: float | None = None,
        pressure_text_gap: float = 10.0,
        pressure_text_decimals: int = 2,
        sim_hz: float = 120.0,
        playback_slowdown: float = 1.75,
        intro_seconds: float = 0.8,
        transition_seconds: float = 0.5,
        settle_seconds: float = 0.25,
        outro_seconds: float = 0.6,
        loop: bool = False,
        mode: str = "video",
        source=None,
        pressure_reader=None,
        left_key: str = "z",
        right_key: str = "c",
        takeover_pressure: float = DEFAULT_TAKEOVER_PRESSURE,
        max_completions: int = 0,
        completion_feedback: bool = True,
        completion_label: str = "",
    ):
        self._init_live(mode, source, pressure_reader, left_key, right_key, takeover_pressure)
        if int(max_completions) < 0:
            raise ValueError("max_completions must be >= 0 (0 = never ends)")
        self.max_completions = int(max_completions)
        self.completions = 0
        self._was_ready = False
        self.completion_feedback = bool(completion_feedback)
        self.completion_label = str(completion_label)
        self._completed_at = None
        self._counter = None  # (text, Text) of the completion counter
        self.screen = screen
        self.background_color = tuple(int(c) for c in background_color)
        self.loop = bool(loop)
        self.key_color_min = tuple(int(c) for c in key_color_min)
        self.key_color_max = tuple(int(c) for c in key_color_max)
        self.key_color_ideal = tuple(int(c) for c in key_color_ideal)
        self.key_pressure_deadzone = float(key_pressure_deadzone)
        self.cross_half_size = float(cross_half_size)
        self.cross_max_scale = 2.0
        self.cross_half_height = self.cross_half_size
        self.cross_thickness = float(cross_thickness)
        screen_min = min(float(screen.width), float(screen.height))
        self.show_pressure_text = bool(show_pressure_text)
        self.left_pressure_label = str(left_pressure_label)
        self.right_pressure_label = str(right_pressure_label)
        self.pressure_text_color = tuple(int(c) for c in pressure_text_color)
        self.pressure_text_font_size = int(pressure_text_font_size or max(12, round(screen_min * 0.012)))
        self.pressure_text_width = float(pressure_text_width or max(48.0, screen_min * 0.055))
        self.pressure_text_height = float(
            pressure_text_height or max(20.0, self.pressure_text_font_size * 1.5)
        )
        self.pressure_text_gap = float(pressure_text_gap)
        self.pressure_text_decimals = int(pressure_text_decimals)
        self._left_pressure_text = None
        self._right_pressure_text = None
        self.sim_hz = float(sim_hz)
        self.playback_slowdown = max(0.01, float(playback_slowdown))
        self.intro_seconds = max(0.0, float(intro_seconds))
        self.transition_seconds = max(0.01, float(transition_seconds))
        self.settle_seconds = max(0.0, float(settle_seconds))
        self.outro_seconds = max(0.01, float(outro_seconds))
        self.pressure_start = self.intro_seconds + self.transition_seconds + self.settle_seconds
        self.pressure_end = self.pressure_start + _PRESSURE_SEQUENCE_SECONDS * self.playback_slowdown
        fallback = {**_BAND_DEFAULTS, "hold_seconds": 0.5 if mode == "video" else 0.3}
        explicit = dict(min_pressure_start=min_pressure_start, max_pressure_start=max_pressure_start,
                        threshold=threshold, hold_seconds=hold_seconds)
        self.config = PressureFeedbackConfig(
            **{name: float(value if value is not None else getattr(source, name, fallback[name]))
               for name, value in explicit.items()},
            max_scale=self.cross_max_scale,
        )
        self.state = PressureFeedbackState(self.config)

        width = float(keyboard_width if keyboard_width is not None else self.DEFAULT_KEYBOARD_WIDTH)
        height = width * _KB_ASPECT
        gap = width * self.KEYBOARD_GAP_FRAC if gap is None else float(gap)
        center_x = screen.width / 2.0
        if top_y is None:
            # Same rule as GifUwuScrollbar; the lowest point is the cross bottom (centre + cross_half_size).
            kb_top = (screen.height - height + gap) / 2.0
            cross_center_y = kb_top - gap - self.cross_half_size  # cross bottom = kb_top - gap
        else:
            # Block-top layout kept for subclasses that re-place the scene (GifUwuHoldTrial passes top_y=0).
            cross_band = self.cross_half_height * 2.0
            block_top = float(top_y)
            cross_center_y = block_top + self.cross_half_height
            kb_top = block_top + cross_band + gap

        self._cross_center = (center_x, cross_center_y)
        self._kb_rect = [center_x - width / 2.0, kb_top, center_x + width / 2.0, kb_top + height]
        # Compensate for the side image's wider transparent margins.
        side_width = width * _SIDE_WIDTH_COMPENSATION
        side_height = side_width * _SIDE_ASPECT
        # Align the visible key tops with the top-view image's upper limit.
        side_top = kb_top - side_height * (_SIDE_VISIBLE_TOP / 380.0)
        self._side_rect = [
            center_x - side_width / 2.0,
            side_top,
            center_x + side_width / 2.0,
            side_top + side_height,
        ]
        self._side_scale = side_width / 808.0
        self._texture = Texture(_load_keyboard_rgb(keyboard_png, self.background_color))
        self._side_texture = Texture(_load_keyboard_rgb(side_keyboard_png, self.background_color))
        self._side_base_texture = Texture(_load_keyboard_rgb(side_keyboard_base_png, self.background_color))
        self._times, self._left_pressures, self._right_pressures = self._build_pressure_timeline()
        self.duration = float(self._times[-1]) if len(self._times) else 0.0
        self._t0: float | None = None

    def _build_pressure_timeline(self):
        """Show Z alone, then both keys reaching, missing, and recovering the target."""
        dt = 1.0 / self.sim_hz
        duration = self.pressure_end + self.outro_seconds
        times, left, right = [], [], []
        for idx in range(int(round(duration / dt))):
            t = idx * dt
            sequence_t = (t - self.pressure_start) / self.playback_slowdown
            times.append(t)
            left.append(self._left_pressure(sequence_t))
            right.append(self._right_pressure(sequence_t))
        return np.asarray(times), self._onto_band(np.asarray(left)), self._onto_band(np.asarray(right))

    def _onto_band(self, pressures: np.ndarray) -> np.ndarray:
        """Rescale scripted pressures from the reference band onto ``self.config``'s band."""
        ref = tuple(_BAND_DEFAULTS[name] for name in ("min_pressure_start", "max_pressure_start", "threshold"))
        cfg = self.config
        target = (cfg.min_pressure_start, cfg.max_pressure_start, cfg.threshold)
        if target == ref:
            return pressures
        return np.interp(pressures, (0.0, *ref, 1.0), (0.0, *target, 1.0))

    @staticmethod
    def _left_pressure(t: float) -> float:
        """Z pulses solo, then joins C to reach / miss / recover the target."""
        if t < 0.20:
            return 0.0
        if t < 1.20:  # two solo pulses while C is still released
            progress = (t - 0.20) / 1.00
            return 0.92 * (0.5 - 0.5 * math.cos(4.0 * math.pi * progress))
        return GifUwuFixationCross._reaching_tail(t, center=0.55, hold=0.57)

    @staticmethod
    def _right_pressure(t: float) -> float:
        """C stays released until Z stops pulsing, then follows the same arc."""
        if t < 1.20:
            return 0.0
        return GifUwuFixationCross._reaching_tail(t, center=0.45, hold=0.49)

    @staticmethod
    def _reaching_tail(t: float, center: float, hold: float) -> float:
        """Shared arc from 1.20 s: rise to ``center``, wobble in the ideal band,
        settle on ``hold``, overshoot past threshold, recover, then fade out."""
        if t < 1.40:  # rise into the ideal band
            return center * _ease_in_out((t - 1.20) / 0.20)
        if t < 1.90:  # small sinusoidal variation around the ideal
            return center + 0.08 * math.sin(2.0 * math.pi * (t - 1.40) / 0.50)
        if t < 2.05:  # ease onto the hold level
            return center + (hold - center) * _ease_in_out((t - 1.90) / 0.15)
        if t < 2.20:
            return hold
        if t < 2.45:  # overshoot past the threshold ("too strong")
            return hold + 0.35 * _ease_in_out((t - 2.20) / 0.25)
        if t < 2.70:  # recover back to the hold level
            return hold + 0.35 * (1.0 - _ease_in_out((t - 2.45) / 0.25))
        if t < 3.00:
            return hold
        if t < 3.30:  # release
            return hold * (1.0 - _ease_in_out((t - 3.00) / 0.30))
        return 0.0

    @property
    def is_complete(self) -> bool:
        return self.max_completions > 0 and self.completions >= self.max_completions

    @property
    def is_finished(self) -> bool:
        if self.is_complete:
            return True
        if self.loop or self._live or self._t0 is None or self.duration <= 0:
            return False
        return (time.perf_counter() - self._t0) >= self.duration

    def start(self):
        """(Re)start the demo and reset the completion count."""
        super().start()
        self.completions, self._was_ready, self._completed_at = 0, False, None

    @property
    def _side_start(self) -> float:
        return self.intro_seconds + self.transition_seconds

    def _on_takeover(self, now: float, from_start: bool) -> None:
        """Finish the top-to-side fade if it is under way, then stay on the side view."""
        elapsed = 0.0 if from_start else self._sample()[0]
        self._live_from = self._side_start if from_start else min(elapsed, self._side_start)
        self._live_t0 = now

    def _sample(self):
        if self._t0 is None:
            return 0.0, 0.0, 0.0
        t = time.perf_counter() - self._t0
        if self.loop and self.duration > 0:
            t = t % self.duration
        idx = int(min(max(t * self.sim_hz, 0.0), len(self._times) - 1))
        return t, float(self._left_pressures[idx]), float(self._right_pressures[idx])

    def draw(self, screen=None) -> None:
        """Draw the keyboard transition, synchronized pressure, and cross."""
        if self._t0 is None:
            self.start()
        now = time.perf_counter()
        live = self._poll_live(now)
        if live is None:
            elapsed, left_pressure, right_pressure = self._sample()
        else:
            left_pressure, right_pressure = live
            elapsed = min(self._live_from + (now - self._live_t0), self._side_start)
        self.state.update(left_pressure=left_pressure, right_pressure=right_pressure, now=now)
        ready = live is not None and self.state.is_ready  # only real pressures count, not the video
        if ready and not self._was_ready:
            self.completions += 1
            self._completed_at = now
        self._was_ready = ready

        self._draw_keyboard(elapsed, left_pressure, right_pressure)
        self._draw_cross()
        if self.completion_feedback and self._live:
            self._draw_counter()

    def _draw_keyboard(self, elapsed: float, left_pressure: float, right_pressure: float) -> None:
        top_alpha, side_alpha = self._keyboard_opacities(elapsed)
        if top_alpha >= 1.0:
            self._texture.draw(self._kb_rect)
        elif top_alpha > 0.0:
            self._draw_texture_with_alpha(self._texture, self._kb_rect, top_alpha)

        side_is_active = self.intro_seconds + self.transition_seconds <= elapsed < self.pressure_end
        if side_is_active:
            self._side_base_texture.draw(self._side_rect)
            self._draw_side_key("left", left_pressure)
            self._draw_side_key("right", right_pressure)
            self._draw_side_case_edge()
        elif side_alpha > 0.0:
            self._draw_texture_with_alpha(self._side_texture, self._side_rect, side_alpha)

    def _keyboard_opacities(self, elapsed: float) -> tuple[float, float]:
        """Fade one keyboard view fully out before fading the other in."""
        if elapsed < self.intro_seconds:
            return 1.0, 0.0
        if elapsed < self.intro_seconds + self.transition_seconds:
            progress = (elapsed - self.intro_seconds) / self.transition_seconds
            if progress < 0.5:
                return 1.0 - _ease_in_out(progress * 2.0), 0.0
            return 0.0, _ease_in_out((progress - 0.5) * 2.0)
        if elapsed < self.pressure_end:
            return 0.0, 1.0

        progress = (elapsed - self.pressure_end) / self.outro_seconds
        if progress < 0.5:
            return 0.0, 1.0 - _ease_in_out(progress * 2.0)
        return _ease_in_out((progress - 0.5) * 2.0), 0.0

    @staticmethod
    def _draw_texture_with_alpha(texture: Texture, rect, alpha: float) -> None:
        """Overlay a texture for the smooth top-to-side transition."""
        texture.set_rect(rect)
        x1, y1, x2, y2 = texture.rect
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor4f(1.0, 1.0, 1.0, max(0.0, min(1.0, alpha)))
        texture.bind()
        glBegin(GL_QUADS)
        for uv, xy in zip(((0, 0), (1, 0), (1, 1), (0, 1)), ((x1, y1), (x2, y1), (x2, y2), (x1, y2))):
            glTexCoord2f(*uv)
            glVertex2f(*xy)
        glEnd()
        texture.unbind()
        glColor4f(1.0, 1.0, 1.0, 1.0)

    def _draw_side_key(self, side: str, pressure: float) -> None:
        visual_pressure = min(1.0, max(0.0, pressure))
        travel = _SIDE_KEY_TRAVEL * visual_pressure
        points = self._clip_key_to_case(self._side_key_points(_SIDE_KEY_X[side], travel))
        points = [self._side_point(x, y) for x, y in points]
        color = self._key_pressure_color(pressure)

        glColor3f(*(channel / 255.0 for channel in color))
        glBegin(GL_TRIANGLE_FAN)
        for point in points:
            glVertex2f(*point)
        glEnd()

        glColor3f(*(channel / 255.0 for channel in (37, 42, 52)))
        glLineWidth(max(1.0, 6.0 * self._side_scale * getattr(self.screen, "content_scale", 1.0)))
        glBegin(GL_LINE_LOOP)
        for point in points:
            glVertex2f(*point)
        glEnd()

    def _key_pressure_color(self, pressure: float):
        if pressure <= self.key_pressure_deadzone:
            return 255, 255, 255
        if self.config.min_pressure_start <= pressure <= self.config.max_pressure_start:
            return self.key_color_ideal
        if pressure < self.config.min_pressure_start:
            return self.key_color_min
        excess = (pressure - self.config.max_pressure_start) / (
            self.config.threshold - self.config.max_pressure_start
        )
        return _lerp_color(self.key_color_min, self.key_color_max, excess)

    @staticmethod
    def _side_key_points(center_x: float, travel: float):
        def quadratic(start, control, end, steps=6):
            return [
                (
                    (1 - t) ** 2 * start[0] + 2 * (1 - t) * t * control[0] + t**2 * end[0],
                    (1 - t) ** 2 * start[1] + 2 * (1 - t) * t * control[1] + t**2 * end[1],
                )
                for t in (step / steps for step in range(1, steps + 1))
            ]

        points = [(center_x - 92, 218), (center_x - 78, 116)]
        points += quadratic((center_x - 78, 116), (center_x - 76, 102), (center_x - 57, 102))
        points.append((center_x + 57, 102))
        points += quadratic((center_x + 57, 102), (center_x + 76, 102), (center_x + 78, 116))
        points.append((center_x + 92, 218))
        return [(x, y + travel) for x, y in points]

    @staticmethod
    def _clip_key_to_case(points):
        """Hide the translated key below the top edge of the keyboard case."""
        clipped = []
        previous = points[-1]
        previous_inside = previous[1] <= _SIDE_CASE_TOP
        for current in points:
            current_inside = current[1] <= _SIDE_CASE_TOP
            if current_inside != previous_inside:
                ratio = (_SIDE_CASE_TOP - previous[1]) / (current[1] - previous[1])
                clipped.append((previous[0] + ratio * (current[0] - previous[0]), _SIDE_CASE_TOP))
            if current_inside:
                clipped.append(current)
            previous, previous_inside = current, current_inside
        return clipped

    def _side_point(self, x: float, y: float):
        x1, y1, x2, y2 = self._side_rect
        return x1 + x * (x2 - x1) / 808.0, y1 + y * (y2 - y1) / 380.0

    def _draw_side_case_edge(self) -> None:
        start = self._side_point(90.0, _SIDE_CASE_TOP)
        end = self._side_point(718.0, _SIDE_CASE_TOP)
        thickness = 8.0 * self._side_scale * getattr(self.screen, "content_scale", 1.0)
        Line(start, end, thickness=thickness, color=(37, 42, 52)).draw()

    def _draw_cross(self) -> None:
        cx, cy = self._cross_center
        half = self.cross_half_size
        color = _lerp_color((100, 100, 100), (0, 0, 0), self.state.hold_progress)

        self._draw_goal_markers(cx, cy)
        if self.state.left_scale > 0.0:
            self._draw_side("left", cx, cy, half * self.state.left_scale, color)
        if self.state.right_scale > 0.0:
            self._draw_side("right", cx, cy, half * self.state.right_scale, color)

        # Drawn last so the black vertical fixation bar stays visually on top.
        Line(
            (cx, cy - self.cross_half_height),
            (cx, cy + self.cross_half_height),
            thickness=self.cross_thickness,
            color=(0, 0, 0),
        ).draw()
        if self.show_pressure_text and (
            self.state.left_status != "ideal" or self.state.right_status != "ideal"
        ):
            self._draw_pressure_text(cx, cy + self.cross_half_height)

    def _counter_rect(self, width: float, height: float):
        """Where the counter goes: centered just below the keypad, clear of the instruction text above."""
        cx, top = self.screen.width / 2.0, self._kb_rect[3] + self.pressure_text_gap
        return (cx - width / 2, top, cx + width / 2, top + height)

    def _draw_counter(self) -> None:
        """Show the completion count in the success green (and a check mark just after a completion)."""
        goal = f" / {self.max_completions}" if self.max_completions else ""
        value = f"{self.completion_label + ': ' if self.completion_label else ''}{self.completions}{goal}"
        if self._counter is None or self._counter[0] != value:
            font_size = round(self.pressure_text_font_size * 1.4)
            rect = self._counter_rect(font_size * (0.45 * len(value) + 1), font_size * 2.4)
            self._counter = (value, Text(
                value, dest_rect=rect, font_size=font_size, color=self.key_color_ideal,
                content_scale=getattr(self.screen, "content_scale", 2.0)), rect, font_size)
        self._counter[1].draw()
        if self._completed_at is not None and time.perf_counter() - self._completed_at < _FLASH_SECONDS:
            self._draw_check(self._counter[2], font_size=self._counter[3])

    def _draw_check(self, rect, font_size: float) -> None:
        """A green check mark just left of the counter, confirming a completion."""
        size, thickness = font_size * 1.3, font_size * 0.28
        x, y = rect[0] - size * 1.4, (rect[1] + rect[3]) / 2.0 - size / 2.0
        elbow, tip = (x + size * 0.38, y + size * 0.95), (x + size, y + size * 0.1)
        for start, end in (((x, y + size * 0.55), elbow), (elbow, tip)):
            Line(start, end, thickness=thickness, color=self.key_color_ideal).draw()

    def _draw_side(self, side: str, cx: float, cy: float, length: float, color) -> None:
        if length <= 0:
            return
        end_x = cx - length if side == "left" else cx + length
        Line((end_x, cy), (cx, cy), thickness=self.cross_thickness, color=color).draw()

    def _draw_goal_markers(self, cx: float, cy: float) -> None:
        marker_width = max(1.0, self.cross_thickness * 0.33)
        half = self.cross_half_size
        Line(
            (cx - half - marker_width, cy),
            (cx - half, cy),
            thickness=self.cross_thickness,
            color=(0, 0, 0),
        ).draw()
        Line(
            (cx + half, cy),
            (cx + half + marker_width, cy),
            thickness=self.cross_thickness,
            color=(0, 0, 0),
        ).draw()

    def _draw_pressure_text(self, cx: float, cross_bottom: float) -> None:
        """Show each non-ideal key pressure beside the cross, as TachyPy does."""
        y1 = cross_bottom + self.pressure_text_gap
        y2 = y1 + self.pressure_text_height
        half = self.cross_half_size
        if self.state.left_status != "ideal":
            rect = (cx - half - self.pressure_text_width, y1, cx - half, y2)
            self._left_pressure_text = self._draw_pressure_value(
                self._left_pressure_text,
                self.left_pressure_label,
                self.state.left_pressure,
                rect,
            )
        if self.state.right_status != "ideal":
            rect = (cx + half, y1, cx + half + self.pressure_text_width, y2)
            self._right_pressure_text = self._draw_pressure_value(
                self._right_pressure_text,
                self.right_pressure_label,
                self.state.right_pressure,
                rect,
            )

    def _draw_pressure_value(self, text_obj, label: str, pressure: float, rect):
        prefix = f"{label}: " if label else ""
        value = f"{prefix}{pressure:.{self.pressure_text_decimals}f}"
        if text_obj is None:
            text_obj = Text(
                value,
                dest_rect=rect,
                font_size=self.pressure_text_font_size,
                color=self.pressure_text_color,
                content_scale=getattr(self.screen, "content_scale", 2.0),
            )
        else:
            text_obj.set_dest_rect(rect)
            if text_obj.text != value:
                text_obj.set_text(value)
        text_obj.draw()
        return text_obj


@dataclass(frozen=True)
class HoldDemoPhase:
    """One timed scene and its keyboard-pressure behavior.

    ``pressure_mode`` scripts the pressures of the video. In an :class:`InteractiveTrial`
    the pressures are real and the phase may also set ``wait_for`` (stay at least
    ``duration`` seconds, then until the cross completes: ``"ready"``, or a key reaches the
    response threshold: ``"response"``) and ``guard`` (the trial fails if a finger lifts).
    """

    name: str
    duration: float
    scene: str
    pressure_mode: str = "green"
    show_cross: bool = False
    attempt: str | None = None
    response: str | None = None
    wait_for: str | None = None
    guard: bool = False

    def __post_init__(self):
        if self.wait_for not in (None, "ready", "response"):
            raise ValueError(f"wait_for must be None, 'ready' or 'response'; got {self.wait_for!r}")


@dataclass(frozen=True)
class InteractiveTrial:
    """One real trial for :class:`GifUwuHoldTrial`: ``phases`` run in order on the participant's
    pressures; if a ``guard`` phase loses a finger, ``fail`` is shown and the trial restarts."""

    phases: tuple[HoldDemoPhase, ...]
    fail: HoldDemoPhase

    def __post_init__(self):
        if not self.phases or any(p.duration <= 0 for p in (*self.phases, self.fail)):
            raise ValueError("an interactive trial needs phases (and a fail phase) with positive durations")


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
    response_side: str | None = None  # "left" / "right" once the participant answered (interactive)


TrialDrawer = Callable[[TrialDemoFrame], None]
PressureProvider = Callable[[HoldDemoPhase, float], tuple[float, float]]


class GifUwuHoldTrial(GifUwuFixationCross):
    """Animate a pressure lesson around experiment-provided trial content.

    ``trial_drawer`` draws only task-specific content in ``display_rect``.
    ``phases`` controls the scenes and timing. ``pressure_provider`` may replace
    the built-in pressure behaviors for a completely custom interaction (its
    values are used as given). The pressure band (``min_pressure_start``,
    ``max_pressure_start``, ``threshold``) comes from the arguments, else from
    ``source`` (e.g. a ``WOOTING_ACQUISITION``, so the lesson matches the real task;
    else 0.33 / 0.66 / 0.8; the built-in behaviors are rescaled onto it.

    ``mode`` works as for :class:`GifUwuFixationCross`. The interactive modes also need
    ``interactive``, an :class:`InteractiveTrial`: the participant then performs the trial
    (cross, cue, imagery, answer) with real pressures; lifting a finger during a ``guard``
    phase shows its ``fail`` phase and restarts, and finishing the last phase counts a
    completion (``max_completions`` as for the cross). ``video_then_interactive`` plays
    ``phases`` until the first Z / C press, then starts the first trial. ``completions``,
    ``failures`` and ``events`` (dicts with ``event`` = ``"fingers_lifted"`` / ``"response"`` /
    ``"completed"``, ``time``, ``attempt``, ``phase``) record what happened; ``on_event`` is
    called with each. With ``completion_feedback`` a counter of completed trials (prefixed by
    ``completion_label``) shows in the monitor's top-right corner. A finger counts as lifted
    below ``finger_present_threshold`` (``None``: the source's, else 0.01); the answer is a
    key reaching the response ``threshold``.

    Example
    -------
    >>> trial = InteractiveTrial(
    ...     phases=(HoldDemoPhase("acquire", 0.3, "acquire", show_cross=True, wait_for="ready"),
    ...             HoldDemoPhase("imagery", 1.7, "imagery", guard=True),
    ...             HoldDemoPhase("question", 0.5, "question", guard=True, wait_for="response"),
    ...             HoldDemoPhase("result", 1.2, "correct")),
    ...     fail=HoldDemoPhase("fail", 2.0, "incorrect"))
    >>> demo = GifUwuHoldTrial(screen, trial_drawer=draw_trial, phases=video_phases, source=wooting,
    ...                        mode="video_then_interactive", interactive=trial, max_completions=2)
    >>> demo.play(response_handler)

    Built-in pressure modes are ``released``, ``ramp_to_green``, ``green``,
    ``lose_left``, ``left_weak``, ``remove_left``, ``left_released``,
    ``recover_left``, ``respond_left``, ``respond_right``, and ``release``.
    """

    def __init__(
        self,
        screen,
        *,
        trial_drawer: TrialDrawer,
        phases: Sequence[HoldDemoPhase] = (),
        pressure_provider: PressureProvider | None = None,
        language: str = "Fr",
        background_color=(128, 128, 128),
        keyboard_width: float = 300.0,
        monitor_width: float | None = None,
        content_top: float | None = None,
        content_bottom: float | None = None,
        min_pressure_start: float | None = None,
        max_pressure_start: float | None = None,
        threshold: float | None = None,
        source=None,
        playback_speed: float = 1.0,
        loop: bool = False,
        mode: str = "video",
        interactive: InteractiveTrial | None = None,
        pressure_reader=None,
        left_key: str = "z",
        right_key: str = "c",
        takeover_pressure: float = DEFAULT_TAKEOVER_PRESSURE,
        max_completions: int = 0,
        finger_present_threshold: float | None = None,
        on_event: Callable[[dict], None] | None = None,
        completion_feedback: bool = True,
        completion_label: str = "",
    ):
        super().__init__(
            screen,
            background_color=background_color,
            keyboard_width=keyboard_width,
            top_y=0,
            min_pressure_start=min_pressure_start,
            max_pressure_start=max_pressure_start,
            threshold=threshold,
            source=source,
            cross_half_size=28.0,
            cross_thickness=8.0,
            show_pressure_text=False,
            loop=False,
            mode=mode,
            pressure_reader=pressure_reader,
            left_key=left_key,
            right_key=right_key,
            takeover_pressure=takeover_pressure,
            max_completions=max_completions,
            completion_feedback=completion_feedback,
            completion_label=completion_label,
        )
        if mode != "video" and interactive is None:
            raise ValueError(f"mode={mode!r} needs interactive=InteractiveTrial(...)")
        self.interactive = interactive
        self.on_event = on_event
        self.finger_present_threshold = float(
            finger_present_threshold if finger_present_threshold is not None
            else getattr(source, "finger_present_threshold", 0.01))
        self.failures, self.events = 0, []
        self.language = str(language)
        self.loop = bool(loop)
        self.playback_speed = float(playback_speed)
        if self.playback_speed <= 0:
            raise ValueError("playback_speed must be greater than zero")
        self.trial_drawer = trial_drawer
        self.pressure_provider = pressure_provider or self._default_pressures
        self.phases = tuple(phases)
        if (self.phases or mode != "interactive") and (
                not self.phases or any(phase.duration <= 0 for phase in self.phases)):
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
        """Return the built-in pressures, rescaled onto the band in use."""
        left, right = self._scripted_pressures(phase, progress)
        return float(self._onto_band(left)), float(self._onto_band(right))

    def _scripted_pressures(self, phase: HoldDemoPhase, progress: float) -> tuple[float, float]:
        """Pressures of the behavior named by the phase, written for the 0.33 / 0.66 / 0.8 band."""
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

    def start(self):
        """(Re)start the demo and clear the completion / failure counts and the event log."""
        super().start()
        self.failures, self.events = 0, []

    def _on_takeover(self, now: float, from_start: bool) -> None:
        self.state = PressureFeedbackState(self.config)  # the video ran on its own clock
        self._begin_trial(now)

    def _begin_trial(self, now: float) -> None:
        self._index, self._phase_t0, self._failed, self._side = 0, now, False, None

    def _log(self, event: str, now: float, phase: str, **info) -> None:
        record = {"event": event, "time": now, "attempt": self.completions + self.failures + 1,
                  "phase": phase, **info}
        self.events.append(record)
        if self.on_event is not None:
            self.on_event(record)

    def _gate_open(self, phase: HoldDemoPhase, left: float, right: float, now: float) -> bool:
        if phase.wait_for == "ready":
            return self.state.is_ready
        if phase.wait_for == "response":
            if max(left, right) < self.config.threshold:
                return False
            self._side = "left" if left >= right else "right"
            self._log("response", now, phase.name, side=self._side)
            return True
        return True

    def _step_trial(self, now: float, left: float, right: float) -> tuple[HoldDemoPhase, float]:
        """Advance the interactive trial by one frame; return the phase to draw and its progress."""
        trial = self.interactive
        if self.is_complete:
            return trial.phases[-1], 1.0
        phase = trial.fail if self._failed else trial.phases[self._index]
        lifted = [key for key, pressure in ((self.left_key, left), (self.right_key, right))
                  if pressure < self.finger_present_threshold]
        if phase.guard and not self._failed and lifted:
            self._log("fingers_lifted", now, phase.name, keys=lifted)
            self.failures += 1
            self._failed, self._phase_t0, phase = True, now, trial.fail
        elif now - self._phase_t0 >= phase.duration and self._gate_open(phase, left, right, now):
            self._phase_t0 = now
            if self._failed:
                self._begin_trial(now)
            elif self._index + 1 < len(trial.phases):
                self._index += 1
            else:
                self._log("completed", now, phase.name)
                self.completions += 1
                if not self.is_complete:
                    self._begin_trial(now)
            phase = trial.fail if self._failed else trial.phases[self._index]
        return phase, min(1.0, (now - self._phase_t0) / phase.duration)

    def draw(self, screen=None) -> None:
        """Draw the generic shell, then call the experiment's renderer."""
        if self._t0 is None:
            self.start()
        now = time.perf_counter()
        live = self._poll_live(now)
        if live is None:
            elapsed = self._elapsed()
            phase, progress = self._phase_at(elapsed)
            left, right = self.pressure_provider(phase, progress)
            self.state.update(left_pressure=left, right_pressure=right, now=elapsed)
            side = None
        else:
            left, right = live
            self.state.update(left_pressure=left, right_pressure=right, now=now)
            phase, progress = self._step_trial(now, left, right)
            side = self._side

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
            response_side=side,
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
        if self.completion_feedback and self._live:
            self._draw_counter()

    def _counter_rect(self, width: float, height: float):
        """In the monitor: top-right corner of the display."""
        x1, y1, x2, _ = self._display_rect
        pad = (x2 - x1) * 0.02
        return (x2 - pad - width, y1 + pad, x2 - pad, y1 + pad + height)

    def _draw_monitor(self) -> None:
        x1, y1, x2, y2 = self._monitor_rect
        cx = (x1 + x2) / 2.0
        Rectangle((cx - 18, y2, cx + 18, y2 + 14), fill=True, color=(37, 42, 52)).draw()
        Rectangle((cx - 70, y2 + 12, cx + 70, y2 + 20), fill=True, color=(37, 42, 52)).draw()
        Rectangle(self._monitor_rect, fill=True, color=(37, 42, 52)).draw()
        Rectangle(self._display_rect, fill=True, color=self.background_color).draw()
