"""TachyPy audio convenience wrapper backed by tachyaudio."""

from __future__ import annotations

import os
import threading
import time

import numpy as np

try:
    import tachyaudio
except Exception as err:  # pragma: no cover - exercised only in broken installs.
    tachyaudio = None
    _TACHYAUDIO_IMPORT_ERROR = err
else:
    _TACHYAUDIO_IMPORT_ERROR = None


class Audio:
    """Schedule playback through :mod:`tachyaudio` while preserving TachyPy's API."""

    def __init__(
        self,
        sample_rate=44100,
        channels=1,
        backend=None,
        *,
        block_size=None,
        device_id=None,
        latency=None,
        timeout=None,
    ):
        """Initialize audio playback state.

        Parameters
        ----------
        sample_rate : int
            Sample rate in Hz.
        channels : int
            Number of output channels.
        backend : str | None
            Must be ``None``, ``"auto"``, or ``"tachyaudio"``. The argument is
            retained for source compatibility; TachyPy no longer owns alternate
            audio backends.
        block_size, device_id, latency : optional
            Passed through to ``tachyaudio.OutputStream``.
        timeout : float | None
            Timeout used for ``write_all`` and ``drain``.
        """
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        if self.sample_rate < 1:
            raise ValueError("sample_rate must be positive")
        if self.channels < 1:
            raise ValueError("channels must be positive")

        requested_backend = backend or os.getenv("TACHYPY_AUDIO_BACKEND", "tachyaudio")
        if requested_backend == "auto":
            requested_backend = "tachyaudio"
        if requested_backend != "tachyaudio":
            raise ValueError("TachyPy audio now supports only backend='tachyaudio'.")

        if tachyaudio is None:
            raise RuntimeError(
                "tachyaudio is required for TachyPy audio. Install with `pip install tachyaudio`."
            ) from _TACHYAUDIO_IMPORT_ERROR

        self.backend_name = "tachyaudio"
        self.block_size = block_size
        self.device_id = device_id
        self.latency = latency
        self.timeout = timeout
        self.is_playing = False
        self._stream = None
        self._lock = threading.Lock()
        self._thread = None

    def play(self, data, when=0):
        """Play a NumPy buffer, optionally scheduled at an absolute monotonic time.

        ``when`` is expressed in seconds from ``time.monotonic_ns() / 1e9``.
        The call starts a daemon thread and returns immediately.
        """
        buffer = self._prepare_buffer(data)
        current_time = time.monotonic_ns()
        delay = int((float(when) * 1e9) - current_time)
        if delay < 0:
            print("Warning: 'when' time is in the past. Playing immediately.")
            delay = 0

        thread = threading.Thread(target=self._playback_thread, args=(buffer, delay), daemon=True)
        self._thread = thread
        thread.start()

    def _prepare_buffer(self, data):
        """Validate, channel-adapt, and return contiguous float32 audio frames."""
        if not isinstance(data, np.ndarray):
            raise ValueError("Data must be a NumPy array.")

        if data.ndim == 1:
            if self.channels > 1:
                data = np.tile(data[:, np.newaxis], (1, self.channels))
        elif data.ndim == 2:
            if data.shape[1] != self.channels:
                raise ValueError(f"Data must have {self.channels} channels.")
        else:
            raise ValueError("Data must be a 1D or 2D NumPy array.")

        if data.dtype != np.float32:
            data = data.astype(np.float32)
        return np.ascontiguousarray(data)

    def _playback_thread(self, data, delay):
        """Worker thread that waits for the target time then plays audio."""
        if delay > 0:
            self._precise_delay(delay)

        stream = tachyaudio.OutputStream(
            sample_rate=self.sample_rate,
            channels=self.channels,
            block_size=self.block_size,
            device_id=self.device_id,
            latency=self.latency,
            dtype="float32",
        )
        with self._lock:
            self._stream = stream
            self.is_playing = True

        try:
            stream.start()
            stream.write_all(data, timeout=self.timeout)
            if not stream.drain(timeout=self.timeout):
                raise TimeoutError("audio playback did not drain before timeout")
        finally:
            try:
                stream.close()
            finally:
                with self._lock:
                    if self._stream is stream:
                        self._stream = None
                        self.is_playing = False

    def _precise_delay(self, delay):
        """Wait for the specified nanosecond delay with high precision."""
        end_time = time.monotonic_ns() + int(delay)
        while True:
            remaining = end_time - time.monotonic_ns()
            sleep_duration = self._sleep_duration_for_remaining_ns(remaining)
            if sleep_duration is None:
                if remaining <= 0:
                    break
                continue
            time.sleep(sleep_duration)

    @staticmethod
    def _sleep_duration_for_remaining_ns(remaining_ns):
        """Return a sleep duration in seconds for a remaining nanosecond delay."""
        if remaining_ns <= 0:
            return None
        if remaining_ns > 10_000_000:
            return 0.005
        return None

    def stop(self):
        """Stop current playback immediately."""
        with self._lock:
            stream = self._stream
        if stream is not None:
            stream.stop()
            stream.close()
        with self._lock:
            if self._stream is stream:
                self._stream = None
                self.is_playing = False

    def close(self):
        """Close audio resources by stopping playback."""
        self.stop()
