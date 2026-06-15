"""Pure pressure-feedback model: source contract, settings, and state machine.

This module contains no OpenGL or drawing code, so it stays importable in
headless environments and is unit-testable on its own.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Protocol, Sequence, Union, runtime_checkable

# Internal classification of a single key's pressure relative to the interval.
PressureStatus = Literal["too_weak", "ideal", "too_strong"]


@runtime_checkable
class PressureSource(Protocol):
    """Minimal interface a keyboard must expose to drive visual feedback.

    The feedback engine is keyboard-agnostic: it only needs a way to read
    pressures and the light-press thresholds. Any object satisfying this
    protocol (for example ``tachywooting.WOOTING_ACQUISITION``) can drive the
    visual feedback, without TachyPy ever importing the keyboard package.

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


@dataclass(frozen=True)
class PressureFeedbackConfig:
    """Settings for pressure-readiness feedback: thresholds, hold, and scaling.

    Parameters
    ----------
    min_pressure_start : float, default=0.01
        Lower bound for the accepted light-press interval.
    max_pressure_start : float, default=0.35
        Upper bound for the accepted light-press interval.
    threshold : float, default=0.8
        Response threshold used by the acquisition task. Must be greater than
        ``max_pressure_start``.
    hold_seconds : float, default=0.30
        Duration both pressures must remain inside the accepted interval before
        readiness is reached.
    min_scale, normal_scale, max_scale : float
        Visual scale factors for the weakest non-zero pressure, the in-range
        pressure, and strong over-pressure (used by :meth:`scale_for`).
    """

    min_pressure_start: float = 0.01
    max_pressure_start: float = 0.35
    threshold: float = 0.8
    hold_seconds: float = 0.30
    min_scale: float = 0.25
    normal_scale: float = 1.0
    max_scale: float = 2.0

    def __post_init__(self) -> None:
        if not (0 <= self.min_pressure_start < self.max_pressure_start < self.threshold <= 1):
            raise ValueError("Require 0 <= min_pressure_start < max_pressure_start < threshold <= 1")
        if self.hold_seconds <= 0:
            raise ValueError("hold_seconds must be positive")
        if not (0 < self.min_scale <= self.normal_scale <= self.max_scale):
            raise ValueError("Require 0 < min_scale <= normal_scale <= max_scale")

    @classmethod
    def from_source(cls, source, *, hold_seconds: float | None = None, **overrides):
        """Build a config from a :class:`PressureSource`.

        Parameters
        ----------
        source : PressureSource
            Object exposing ``min_pressure_start``, ``max_pressure_start``,
            ``threshold`` and ``hold_seconds`` (e.g. a keyboard acquisition).
        hold_seconds : float, optional
            Override the source's ``hold_seconds``.
        **overrides
            Any other field to override (scale factors, thresholds, ...).

        Returns
        -------
        PressureFeedbackConfig
        """
        values = dict(
            min_pressure_start=source.min_pressure_start,
            max_pressure_start=source.max_pressure_start,
            threshold=source.threshold,
            hold_seconds=source.hold_seconds if hold_seconds is None else hold_seconds,
        )
        values.update(overrides)
        return cls(**values)

    def scale_for(self, pressure: float) -> float:
        """Return the visual scale factor for one pressure value.

        Returns ``0.0`` when ``pressure`` is exactly zero, ``normal_scale``
        inside the accepted interval, and a clamped continuous scale outside it.
        """
        pressure = max(0.0, min(1.0, float(pressure)))
        if pressure == 0.0:
            return 0.0

        low, high = self.min_pressure_start, self.max_pressure_start
        if pressure < low:
            if low <= 0:
                return self.normal_scale
            ratio = pressure / low
            return self._clamp_scale(self.min_scale + ratio * (self.normal_scale - self.min_scale))

        if pressure <= high:
            return self.normal_scale

        if high >= 1.0:
            return self.max_scale
        ratio = (pressure - high) / (1.0 - high)
        return self._clamp_scale(self.normal_scale + ratio * (self.max_scale - self.normal_scale))

    def _clamp_scale(self, value: float) -> float:
        return max(self.min_scale, min(self.max_scale, float(value)))


@dataclass
class PressureFeedbackState:
    """State machine for real-time pressure feedback.

    Parameters
    ----------
    config : PressureFeedbackConfig
        Feedback thresholds, hold duration, and scale factors.

    Attributes
    ----------
    left_pressure, right_pressure : float
        Most recent pressure values.
    left_scale, right_scale : float
        Current visual scale values for the left and right horizontal segments.
    left_status, right_status : {"too_weak", "ideal", "too_strong"}
        Pressure classification for each side.
    hold_progress : float
        Fraction of the hold duration completed, clamped to ``[0, 1]``.
    elapsed_hold_time : float
        Seconds spent continuously inside the accepted interval.
    is_ready : bool
        ``True`` once both pressures have remained ideal for ``hold_seconds``.
    """

    config: PressureFeedbackConfig
    left_pressure: float = 0.0
    right_pressure: float = 0.0
    left_scale: float = 1.0
    right_scale: float = 1.0
    left_status: PressureStatus = "too_weak"
    right_status: PressureStatus = "too_weak"
    hold_progress: float = 0.0
    elapsed_hold_time: float = 0.0
    is_ready: bool = False
    _hold_started_at: float | None = None

    def update(self, left_pressure: float, right_pressure: float, now: float) -> None:
        """Update pressure status, scale, hold timer, and readiness.

        Parameters
        ----------
        left_pressure : float
            Current pressure for the left monitored key.
        right_pressure : float
            Current pressure for the right monitored key.
        now : float
            Current monotonic timestamp, usually from ``time.perf_counter()``.

        Returns
        -------
        None
            The object is updated in place.
        """
        self.left_pressure = float(left_pressure)
        self.right_pressure = float(right_pressure)
        self.left_status = self._status(self.left_pressure)
        self.right_status = self._status(self.right_pressure)
        self.left_scale = self.config.scale_for(self.left_pressure)
        self.right_scale = self.config.scale_for(self.right_pressure)

        if self.left_status == "ideal" and self.right_status == "ideal":
            if self._hold_started_at is None:
                self._hold_started_at = float(now)
            self.elapsed_hold_time = max(0.0, float(now) - self._hold_started_at)
            self.hold_progress = min(1.0, self.elapsed_hold_time / self.config.hold_seconds)
            self.is_ready = self.hold_progress >= 1.0
            return

        self._hold_started_at = None
        self.elapsed_hold_time = 0.0
        self.hold_progress = 0.0
        self.is_ready = False

    def _status(self, pressure: float) -> PressureStatus:
        if pressure < self.config.min_pressure_start:
            return "too_weak"
        if pressure > self.config.max_pressure_start:
            return "too_strong"
        return "ideal"
