"""Visual pressure-feedback toolkit for analog keyboards.

This subpackage is keyboard-agnostic: it renders feedback for any object that
satisfies :class:`PressureSource` (it never imports a keyboard package). Most
users do not import from here directly — they call ``wait_light_press_visual``
on an acquisition class enriched with :class:`VisualPressureFeedbackMixin`
(see :mod:`tachypy.wooting`). The building blocks below are exposed for power
users who want custom widgets or to drive the loop manually.
"""
from .engine import DEFAULT_EXIT_KEYS, run_light_press_visual
from .fixation import InteractiveFixationCross
from .mapping import PressureScaleMapper
from .mixin import VisualPressureFeedbackMixin
from .source import PressureSource
from .state import PressureFeedbackConfig, PressureFeedbackState, PressureStatus
from .widgets import PressureFeedbackWidget

__all__ = [
    "DEFAULT_EXIT_KEYS",
    "InteractiveFixationCross",
    "PressureFeedbackConfig",
    "PressureFeedbackState",
    "PressureFeedbackWidget",
    "PressureScaleMapper",
    "PressureSource",
    "PressureStatus",
    "VisualPressureFeedbackMixin",
    "run_light_press_visual",
]
