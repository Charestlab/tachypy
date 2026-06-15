"""Keyboard-agnostic visual pressure-feedback loop.

This module owns the render loop only. It never imports any keyboard package:
pressures are supplied through a ``read_pair`` callable, and timing can be
delegated to an injected ``wait_until`` (the keyboard's precise sleep) or falls
back to a portable default.
"""
from __future__ import annotations

import time
from typing import Callable, Sequence

from .state import PressureFeedbackState
from .widgets import PressureFeedbackWidget

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
        response_handler.keys_to_listen = sorted(exit_key_set)
        if hasattr(response_handler, "_probed_keys"):
            response_handler._probed_keys.update(exit_key_set)

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
