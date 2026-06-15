"""Structural contract for objects that provide analog key pressure.

The feedback engine is keyboard-agnostic: it only needs a way to read pressures
and the light-press thresholds. Any object satisfying :class:`PressureSource`
(for example ``tachywooting.WOOTING_ACQUISITION``) can drive the visual feedback,
without TachyPy ever importing the keyboard package.
"""
from __future__ import annotations

from typing import Dict, Protocol, Sequence, Union, runtime_checkable


@runtime_checkable
class PressureSource(Protocol):
    """Minimal interface a keyboard must expose to drive visual feedback.

    Attributes
    ----------
    min_pressure_start, max_pressure_start : float
        Bounds of the accepted light-press interval.
    threshold : float
        Response threshold of the acquisition task.
    hold_seconds : float
        Default continuous-hold duration for readiness checks.

    Methods
    -------
    read_pressures(keys)
        Return current analog pressures (``[0, 1]``) for the given keys,
        as a mapping keyed by ``str(key)`` preserving input order.
    """

    min_pressure_start: float
    max_pressure_start: float
    threshold: float
    hold_seconds: float

    def read_pressures(self, keys: Sequence[Union[str, int]]) -> Dict[str, float]: ...
