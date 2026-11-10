"""Microphone capture for TachyPy, backed by ``tachyaudio.InputStream``.

Returns NumPy ``float32`` arrays, mirroring :class:`tachypy.Audio`'s ergonomics:
open, ``record(seconds)`` for a blocking clip, or ``start()``/``read()``/``stop()``
to stream. On macOS the first capture triggers the microphone permission prompt;
grant it in System Settings → Privacy & Security → Microphone.
"""

from __future__ import annotations

import math
import operator

import numpy as np

try:
    import tachyaudio
except Exception as err:  # pragma: no cover - exercised only in broken installs.
    tachyaudio = None
    _TACHYAUDIO_IMPORT_ERROR = err
else:
    _TACHYAUDIO_IMPORT_ERROR = None


class Microphone:
    """Capture audio from an input device as NumPy ``float32`` arrays."""

    def __init__(
        self,
        sample_rate=48000,
        channels=1,
        *,
        device_id=None,
        latency=None,
        block_size=None,
    ):
        """Configure capture. The device opens lazily on the first capture.

        Parameters
        ----------
        sample_rate, channels : int
            Of the captured data; no resampling is done.
        device_id : str | None
            Input device id; ``None`` uses the system default input.
        latency : float | None
            Requested input buffer in seconds (``None`` lets the backend choose).
        block_size : int | None
            Backend block size; ``None`` lets the backend choose.
        """
        if tachyaudio is None:
            raise RuntimeError(
                f"tachyaudio is required for microphone capture: {_TACHYAUDIO_IMPORT_ERROR}"
            )
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_id = device_id
        self.latency = latency
        self.block_size = block_size
        self._stream = None
        self._started = False

    def _open(self):
        if self._stream is None:
            self._stream = tachyaudio.InputStream(
                sample_rate=self.sample_rate,
                channels=self.channels,
                device_id=self.device_id,
                latency=self.latency,
                block_size=self.block_size,
                dtype="float32",
            )

    def start(self):
        """Open the device and begin capturing into the buffer."""
        self._open()
        if not self._started:
            try:
                self._stream.start()
            except BaseException:
                self.close()
                raise
            self._started = True

    def _to_array(self, buffer):
        frames = np.frombuffer(buffer, dtype=np.float32)
        if self.channels > 1:
            frames = frames.reshape(-1, self.channels)
        return np.array(frames, copy=True)

    def read(self, frames):
        """Return up to ``frames`` frames already captured (may be fewer).

        Shape ``(n,)`` for mono, ``(n, channels)`` otherwise.
        """
        frames = operator.index(frames)
        if frames < 1:
            raise ValueError("frames must be positive")
        self.start()
        return self._to_array(self._stream.read(frames))

    def read_exactly(self, frames, timeout=None):
        """Wait for and return exactly ``frames`` frames.

        Raises ``TimeoutError`` if they are not captured before ``timeout``.
        """
        frames = operator.index(frames)
        if frames < 1:
            raise ValueError("frames must be positive")
        self.start()
        return self._to_array(self._stream.read_exactly(frames, timeout=timeout))

    def record(self, seconds, timeout=None):
        """Block and capture ``seconds`` of audio, starting now.

        Returns a ``float32`` array of ``round(seconds * sample_rate)`` frames,
        shape ``(N,)`` for mono or ``(N, channels)`` otherwise. Buffered input from
        before the call is discarded, so the clip starts at the call.
        """
        if not math.isfinite(seconds) or seconds <= 0:
            raise ValueError("seconds must be finite and positive")
        frames = round(seconds * self.sample_rate)
        if frames < 1:
            raise ValueError("seconds must capture at least one frame")
        self.start()
        self._stream.flush()
        if timeout is None:
            timeout = seconds + 2.0
        return self.read_exactly(frames, timeout=timeout)

    def flush(self):
        """Discard buffered captured frames without closing the device."""
        if self._stream is not None:
            self._stream.flush()

    def stop(self):
        """Stop capture without releasing the device."""
        if self._stream is not None and self._started:
            self._stream.stop()
            self._started = False

    def close(self):
        """Stop and release the device."""
        if self._stream is not None:
            try:
                self._stream.close()
            finally:
                self._stream = None
                self._started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
