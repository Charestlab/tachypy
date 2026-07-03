"""TachyPy ↔ Wooting integration (requires ``pip install tachypy[wooting]``).

This module is the single import surface for using a Wooting analog keyboard
*inside* TachyPy experiments. It re-exports TachyWooting's public API and adds an
enriched :class:`WOOTING_ACQUISITION` that gains TachyPy visual feedback
(``wait_light_press_visual``) on top of the hardware acquisition class.

TachyPy core never imports this module, so ``pip install tachypy`` stays usable
without a keyboard. Importing this module without TachyWooting installed raises a
clear, actionable error.
"""
from __future__ import annotations

try:
    import tachywooting as _tachywooting
except ImportError as exc:  # pragma: no cover - exercised via packaging
    raise ImportError(
        "The Wooting integration requires the 'tachywooting' package.\n"
        "Install it with:\n\n    pip install 'tachypy[wooting]'\n"
    ) from exc

from tachypy.feedback import VisualPressureFeedbackMixin

# Re-export the keyboard's public API so experiments need only one import.
from tachywooting import (  # noqa: F401
    convert_char_to_keycode,
    convert_keycode_to_char,
    ffi,
    lib,
    load_session,
    load_trial,
    trial_to_dataframe,
)
from tachywooting.visualize import visualize, visualize_all_keys  # noqa: F401

# TachyPy-enriched acquisition class that combines Wooting's hardware acquisition and TachyPy's visual feedback.
class WOOTING_ACQUISITION(_tachywooting.WOOTING_ACQUISITION, VisualPressureFeedbackMixin):
    """Wooting acquisition enriched with TachyPy visual feedback.

    Identical to :class:`tachywooting.WOOTING_ACQUISITION` (acquisition, logging,
    readiness checks) plus :meth:`~tachypy.feedback.VisualPressureFeedbackMixin.wait_light_press_visual`
    for on-screen pressure feedback.
    """


__all__ = [
    "WOOTING_ACQUISITION",
    "convert_char_to_keycode",
    "convert_keycode_to_char",
    "ffi",
    "lib",
    "load_session",
    "load_trial",
    "trial_to_dataframe",
    "visualize",
    "visualize_all_keys",
]
