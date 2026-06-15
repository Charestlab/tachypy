"""Visual pressure-feedback loop and the user-facing mixin.

``run_light_press_visual`` is the keyboard-agnostic render loop: it never imports
any keyboard package — pressures are supplied through a ``read_pair`` callable and
timing can be delegated to an injected ``wait_until``.

``VisualPressureFeedbackMixin`` grafts ``wait_light_press_visual`` onto any object
satisfying :class:`~tachypy.feedback.model.PressureSource`; it wires the keyboard's
pressure reading and thresholds into the loop and builds the default widget.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Sequence

from .model import PressureFeedbackConfig, PressureFeedbackState
from .widgets import InteractiveFixationCross, PressureFeedbackWidget

DEFAULT_EXIT_KEYS: tuple[str, ...] = ("escape", "esc", "enter", "return", "space", "q")

_TICK_INTERVAL = 1.0 / 1000.0  # 1000 Hz polling


def _exit_requested(response_handler, exit_keys: set[str]) -> bool:
    """Return True when the user requested an exit through a response handler.

    Works with any TachyPy ``ResponseHandler``-like object (duck-typed): it may
    expose ``get_events``, ``should_quit`` and ``get_key_presses``.
    """
    if response_handler is None:
        return False
    if hasattr(response_handler, "get_events"):
        response_handler.get_events()
    if hasattr(response_handler, "should_quit") and response_handler.should_quit():
        return True
    if hasattr(response_handler, "key_down_events"):
        return any(str(key).lower() in exit_keys for key in response_handler.key_down_events)
    if not hasattr(response_handler, "get_key_presses"):
        return False
    for event in response_handler.get_key_presses():
        if event.get("type") == "keydown" and str(event.get("key", "")).lower() in exit_keys:
            return True
    return False


def _default_wait_until(next_t: float) -> None:
    remaining = next_t - time.perf_counter()
    if remaining > 0:
        time.sleep(remaining)


def run_light_press_visual(
    *,
    read_pair: Callable[[], tuple[float, float]],
    state: PressureFeedbackState,
    widget: PressureFeedbackWidget,
    screen,
    response_handler=None,
    exit_keys: Sequence[str] = DEFAULT_EXIT_KEYS,
    overlay_drawables: Sequence[object] | None = None,
    background_color=(128, 128, 128),
    timeout_seconds: float | None = None,
    wait_until: Callable[[float], None] | None = None,
    verbose: bool = False,
) -> bool:
    """Run the visual light-press feedback loop until ready or aborted.

    Parameters
    ----------
    read_pair : callable
        Zero-argument callable returning ``(left_pressure, right_pressure)``.
    state : PressureFeedbackState
        Feedback state machine to drive each frame.
    widget : PressureFeedbackWidget
        Widget updated and drawn each frame.
    screen : object
        TachyPy ``Screen``-like object. Must expose ``flip()``; if it exposes
        ``fill(color)``, the screen is cleared with ``background_color``.
    response_handler : object, optional
        ``ResponseHandler``-like object. Exit and quit requests return ``False``.
    exit_keys : sequence of str
        Keys that abort the wait when ``response_handler`` is active.
    overlay_drawables : sequence, optional
        Objects with ``.draw()`` called each frame after the widget.
    background_color : tuple or callable
        RGB color (or callable returning one) used to clear the screen.
    timeout_seconds : float, optional
        Maximum wait time. Raises ``TimeoutError`` if exceeded.
    wait_until : callable, optional
        ``wait_until(next_t)`` used to pace the loop. Defaults to a portable
        sleep; pass a keyboard's precise tick for tighter timing.
    verbose : bool, default=False
        Reserved for future logging hooks.

    Returns
    -------
    bool
        ``True`` when both keys were held in range for the hold duration.
        ``False`` when the user exits via ``response_handler``.
    """
    if not hasattr(screen, "flip"):
        raise AttributeError("screen must expose flip()")
    wait_until = _default_wait_until if wait_until is None else wait_until

    exit_key_set = {str(key).lower() for key in exit_keys}
    if response_handler is not None and hasattr(response_handler, "keys_to_listen"):
        existing = getattr(response_handler, "keys_to_listen", None) or []
        merged = {str(key).lower() for key in existing} | exit_key_set
        response_handler.keys_to_listen = sorted(merged)
        if hasattr(response_handler, "_probed_keys"):
            response_handler._probed_keys.update(merged)

    next_t = time.perf_counter()
    deadline = None if timeout_seconds is None else next_t + timeout_seconds

    while True:
        now = time.perf_counter()
        if deadline is not None and now >= deadline:
            raise TimeoutError("run_light_press_visual: timeout exceeded")
        if _exit_requested(response_handler, exit_key_set):
            return False

        frame_background_color = background_color() if callable(background_color) else background_color
        if hasattr(screen, "fill"):
            screen.fill(frame_background_color)

        left, right = read_pair()
        state.update(left_pressure=float(left), right_pressure=float(right), now=now)

        widget.update(state)
        widget.draw()
        if overlay_drawables:
            for drawable in overlay_drawables:
                drawable.draw()

        screen.flip()

        if state.is_ready:
            return True

        next_t += _TICK_INTERVAL
        now2 = time.perf_counter()
        if next_t < (now2 - 0.10):
            next_t = now2 + _TICK_INTERVAL
        wait_until(next_t)


class VisualPressureFeedbackMixin:
    """Adds :meth:`wait_light_press_visual` to a :class:`PressureSource`.

    Any acquisition class that satisfies the ``PressureSource`` contract becomes
    able to show visual feedback simply by mixing this in::

        class WOOTING_ACQUISITION(BaseWooting, VisualPressureFeedbackMixin):
            ...
    """

    def wait_light_press_visual(
        self,
        target_keys: Sequence[str | int],
        screen,
        response_handler=None,
        fixation_cross=None,
        overlay_drawables: Sequence[object] | None = None,
        # ── timing ──────────────────────────────────────────────────────────
        hold_seconds: float | None = None,
        timeout_seconds: float | None = None,
        # ── appearance ──────────────────────────────────────────────────────
        background_color: tuple[int, int, int] = (128, 128, 128),
        initial_color: tuple[int, int, int] | None = None,
        show_pressure_text: bool | None = None,
        show_goal_markers: bool | None = None,
        # ── behaviour ───────────────────────────────────────────────────────
        exit_keys: Sequence[str] = DEFAULT_EXIT_KEYS,
        # ── others ──────────────────────────────────────────────────────────
        widget: Any | None = None,
        verbose: bool = False,
    ) -> bool:
        """
        Wait for two keys to stay in the light-press range while showing visual feedback.

        Parameters
        ----------
        target_keys : sequence of str or int
            Exactly two keys. The first controls the left side of the widget,
            the second the right side.
        screen : TachyPy Screen object
            Must expose ``flip()``. If it exposes ``fill(color)``, the screen is
            cleared with ``background_color`` each frame.
        response_handler : TachyPy ResponseHandler, optional
            When provided, quit requests and ``exit_keys`` presses return ``False``.
        fixation_cross : TachyPy FixationCross, optional
            Existing fixation cross whose geometry and color are copied by the
            auto-created widget. Invalid with ``widget``.
        overlay_drawables : sequence, optional
            Objects with a ``.draw()`` method called each frame after the widget.
        hold_seconds : float, optional
            Required continuous hold duration. Defaults to ``self.hold_seconds``.
        timeout_seconds : float, optional
            Maximum wait time. Raises ``TimeoutError`` if exceeded.
        background_color : tuple[int, int, int], default=(128, 128, 128)
            RGB color used to clear the screen each frame.
        initial_color : tuple[int, int, int], optional
            Starting color of the horizontal bar. Defaults to ``(100, 100, 100)``.
            Invalid with ``widget``.
        show_pressure_text : bool, optional
            Show real-time pressure values above the cross for out-of-range keys.
            Defaults to ``False``. Invalid with ``widget``.
        show_goal_markers : bool, optional
            Show thin ticks at the target positions. Defaults to ``False``.
            Invalid with ``widget``.
        exit_keys : sequence of str
            Keys that abort the wait when ``response_handler`` is active.
        widget : PressureFeedbackWidget, optional
            Full custom widget override. When provided, ``fixation_cross``,
            ``initial_color``, ``show_pressure_text`` and ``show_goal_markers``
            are invalid.
        verbose : bool, default=False
            Reserved for future logging hooks.

        Returns
        -------
        bool
            ``True`` when both keys were held in range for ``hold_seconds``.
            ``False`` when the user exits via ``response_handler``.

        Raises
        ------
        ValueError
            Invalid arguments or incompatible parameter combinations.
        TimeoutError
            ``timeout_seconds`` exceeded before readiness.

        Examples
        --------
        >>> acq.wait_light_press_visual(target_keys=["c", "z"], screen=screen)

        >>> acq.wait_light_press_visual(
        ...     target_keys=["c", "z"], screen=screen,
        ...     response_handler=rh, fixation_cross=fixation,
        ... )
        """
        if not getattr(self, "initialized", False):
            raise ValueError('Keyboard must be initialized through "initialize_keyboard()".')
        if timeout_seconds is not None and timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0 if provided")

        target_keys = list(target_keys)
        if len(target_keys) != 2:
            raise ValueError("wait_light_press_visual requires exactly two target keys")

        if widget is not None:
            conflicting = [
                name for name, value in (
                    ("fixation_cross", fixation_cross),
                    ("initial_color", initial_color),
                    ("show_pressure_text", show_pressure_text),
                    ("show_goal_markers", show_goal_markers),
                )
                if value is not None
            ]
            if conflicting:
                raise ValueError(
                    "Do not pass auto-widget configuration arguments when `widget` is provided: "
                    f"{', '.join(conflicting)}. Configure the widget directly instead."
                )

        config = PressureFeedbackConfig.from_source(self, hold_seconds=hold_seconds)
        if config.hold_seconds <= 0:
            raise ValueError("hold_seconds must be > 0")

        if widget is None:
            widget = InteractiveFixationCross(
                screen=screen,
                fixation_cross=fixation_cross,
                background_color=background_color,
                initial_color=(100, 100, 100) if initial_color is None else initial_color,
                acquisition=self,
                show_pressure_text=False if show_pressure_text is None else show_pressure_text,
                show_goal_markers=False if show_goal_markers is None else show_goal_markers,
            )

        state = PressureFeedbackState(config)

        left_key, right_key = str(target_keys[0]), str(target_keys[1])

        def _read_pair() -> tuple[float, float]:
            pressures = self.read_pressures(target_keys)
            return pressures[left_key], pressures[right_key]

        return run_light_press_visual(
            read_pair=_read_pair,
            state=state,
            widget=widget,
            screen=screen,
            response_handler=response_handler,
            exit_keys=exit_keys,
            overlay_drawables=overlay_drawables,
            background_color=background_color,
            timeout_seconds=timeout_seconds,
            wait_until=getattr(self, "_wait_until_next_tick", None),
            verbose=verbose,
        )
