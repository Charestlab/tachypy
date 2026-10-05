"""Animated UwU-keypad demos for instruction screens: fixation-cross hold and analog slider.

Scripted, keyboard-free animations of the Wooting UwU keypad. No keyboard or
TachyWooting is needed to play them, so they can be shown while presenting the
instructions (to explain how the pressure-sensitive keys work) before a
participant ever touches the hardware.

- :class:`GifUwuScrollbar` -- a fixed keyboard image under a live
  :class:`~tachypy.scrollbar.Scrollbar` whose red cursor (and a red key square)
  follow the *same* duration-based math as the real analog interaction
  (:mod:`tachypy.scrollbar_interaction`), scripted so the loop closes seamlessly.
- :class:`GifUwuFixationCross` -- a top-view keyboard that fades into a side view
  whose two keycaps travel and recolor with scripted pressures. The same
  pressures drive a :class:`~tachypy.feedback.PressureFeedbackState`, so the
  fixation cross below grows, recolors, and prints pressure exactly as in a live
  trial.

Both expose ``start()``, ``draw(screen)``, ``is_finished`` and a ``loop`` flag.
:class:`~tachypy.Texture` is RGB-only, so the transparent keyboard PNGs are
composited onto ``background_color`` at load time; set it to the screen fill so
the keyboard blends in.
"""
from __future__ import annotations

import math
import time
from pathlib import Path

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
from tachypy.scrollbar_interaction import _accelerated_step, _edge_scale
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


class GifUwuScrollbar:
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
    ):
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

    def start(self):
        """(Re)start the animation clock from now."""
        self._t0 = time.perf_counter()

    @property
    def is_finished(self) -> bool:
        if self.loop or self._t0 is None or self.duration <= 0:
            return False
        return (time.perf_counter() - self._t0) >= self.duration

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
        value, key = self._sample()

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


class GifUwuFixationCross:
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
    min_pressure_start, max_pressure_start, threshold, hold_seconds : float
        ``PressureFeedbackConfig`` band edges, target threshold, and hold time.
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
        min_pressure_start: float = 0.33,
        max_pressure_start: float = 0.66,
        threshold: float = 0.8,
        hold_seconds: float = 0.50,
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
    ):
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
        self.config = PressureFeedbackConfig(
            min_pressure_start=float(min_pressure_start),
            max_pressure_start=float(max_pressure_start),
            threshold=float(threshold),
            hold_seconds=float(hold_seconds),
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
        return np.asarray(times), np.asarray(left), np.asarray(right)

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

    def start(self):
        """(Re)start the animation clock from now."""
        self._t0 = time.perf_counter()

    @property
    def is_finished(self) -> bool:
        if self.loop or self._t0 is None or self.duration <= 0:
            return False
        return (time.perf_counter() - self._t0) >= self.duration

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
        elapsed, left_pressure, right_pressure = self._sample()
        now = time.perf_counter()
        self.state.update(left_pressure=left_pressure, right_pressure=right_pressure, now=now)

        self._draw_keyboard(elapsed, left_pressure, right_pressure)
        self._draw_cross()

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
