"""Visual pressure-feedback toolkit for analog keyboards.

Keyboard-agnostic: it renders feedback for any object satisfying
:class:`PressureSource` and never imports a keyboard package. Most users do not
import from here directly — they call ``wait_light_press_visual`` on an
acquisition class enriched with :class:`VisualPressureFeedbackMixin`
(see :mod:`tachypy.wooting`). The building blocks below are exposed for power
users who want custom widgets or to drive the loop manually.

Layout
------
- ``model``   — pure logic: ``PressureSource``, ``PressureFeedbackConfig``
  (thresholds, hold, and scaling), and ``PressureFeedbackState`` (no OpenGL).
- ``widgets`` — rendering: ``PressureFeedbackWidget`` (ABC) and the default
  ``InteractiveFixationCross``.
- ``runner``  — the agnostic loop (``run_light_press_visual``) and the
  user-facing ``VisualPressureFeedbackMixin``.
"""
from .model import PressureFeedbackConfig, PressureFeedbackState, PressureSource
from .runner import DEFAULT_EXIT_KEYS, VisualPressureFeedbackMixin, run_light_press_visual
from .widgets import InteractiveFixationCross, PressureFeedbackWidget

__all__ = [
    "DEFAULT_EXIT_KEYS",
    "InteractiveFixationCross",
    "PressureFeedbackConfig",
    "PressureFeedbackState",
    "PressureFeedbackWidget",
    "PressureSource",
    "VisualPressureFeedbackMixin",
    "run_light_press_visual",
]
