"""Mixin that grafts visual pressure feedback onto any pressure source.

Any acquisition class that satisfies :class:`~tachypy.feedback.source.PressureSource`
(reads pressures, exposes the light-press thresholds) becomes able to show
visual feedback simply by mixing this in::

    class WOOTING_ACQUISITION(BaseWooting, VisualPressureFeedbackMixin):
        ...

The visual logic lives once, in :mod:`tachypy.feedback.engine`. This mixin only
wires the keyboard's pressure reading and config into that engine and builds the
default widget.
"""
from __future__ import annotations

from typing import Any, Sequence

from .engine import DEFAULT_EXIT_KEYS, run_light_press_visual
from .fixation import InteractiveFixationCross
from .state import PressureFeedbackConfig, PressureFeedbackState


class VisualPressureFeedbackMixin:
    """Adds :meth:`wait_light_press_visual` to a :class:`PressureSource`."""

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
