import os
import threading
import time
import warnings

import numpy as np

try:
    import sounddevice as sd
except Exception:
    sd = None


class _AudioBackend:
    """Abstract audio backend interface used by :class:`Audio`."""

    name = "abstract"

    def play(self, data, sample_rate):
        """Start playing a numpy buffer."""
        raise NotImplementedError

    def wait(self):
        """Block until playback completes."""
        raise NotImplementedError

    def stop(self):
        """Stop active playback."""
        raise NotImplementedError

    def close(self):
        """Release backend resources."""
        self.stop()


class _SoundDeviceBackend(_AudioBackend):
    """Sounddevice backend wrapping PortAudio."""

    name = "sounddevice"

    def play(self, data, sample_rate):
        sd.play(data, samplerate=sample_rate)

    def wait(self):
        sd.wait()

    def stop(self):
        sd.stop()


class _DummyBackend(_AudioBackend):
    """No-op backend for CI/headless environments."""

    name = "dummy"

    def __init__(self):
        self._play_until_ns = None

    def play(self, data, sample_rate):
        duration_ns = int((len(data) / float(sample_rate)) * 1e9)
        self._play_until_ns = time.monotonic_ns() + max(duration_ns, 0)

    def wait(self):
        if self._play_until_ns is None:
            return
        remaining_ns = self._play_until_ns - time.monotonic_ns()
        if remaining_ns > 0:
            time.sleep(remaining_ns / 1e9)
        self._play_until_ns = None

    def stop(self):
        self._play_until_ns = None


def _build_backend(backend_name):
    """Instantiate a backend from a backend selection string."""
    if backend_name == "sounddevice":
        if sd is None:
            raise RuntimeError(
                "Audio backend 'sounddevice' requested but sounddevice is unavailable. "
                "Install with `pip install 'tachypy[audio_sd]'`."
            )
        return _SoundDeviceBackend()
    if backend_name == "dummy":
        return _DummyBackend()
    if backend_name == "auto":
        if sd is not None:
            return _SoundDeviceBackend()
        warnings.warn(
            "sounddevice not available; falling back to dummy audio backend.",
            RuntimeWarning,
            stacklevel=2,
        )
        return _DummyBackend()
    raise ValueError(f"Unsupported audio backend '{backend_name}'.")


class Audio:
    """Scheduled audio playback wrapper with pluggable backend support."""

    def __init__(self, sample_rate=44100, channels=1, backend=None):
        """Initialize audio playback state.

        Parameters
        ----------
        sample_rate : int
            Sample rate in Hz.
        channels : int
            Number of audio output channels.
        backend : str | None
            One of ``"auto"``, ``"sounddevice"``, ``"dummy"``.
            ``None`` resolves from ``TACHYPY_AUDIO_BACKEND`` env var, then ``"auto"``.
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_playing = False
        requested_backend = backend or os.getenv("TACHYPY_AUDIO_BACKEND", "auto")
        self.backend = _build_backend(requested_backend)
        self.backend_name = self.backend.name

    def play(self, data, when=0):
        """
        Plays a NumPy array as audio at a specified time.
        :param data: NumPy array of audio data.
        :param when: Absolute time in seconds (monotonic) when playback should start.
        """
        if not isinstance(data, np.ndarray):
            raise ValueError("Data must be a NumPy array.")

        # Ensure data has the correct shape
        if data.ndim == 1:
            if self.channels > 1:
                # Duplicate mono data for multiple channels
                data = np.tile(data[:, np.newaxis], (1, self.channels))
        elif data.ndim == 2:
            if data.shape[1] != self.channels:
                raise ValueError(f"Data must have {self.channels} channels.")
        else:
            raise ValueError("Data must be a 1D or 2D NumPy array.")

        # Ensure data is in float32 format
        if data.dtype != np.float32:
            data = data.astype(np.float32)

        # Calculate delay until 'when' time
        current_time = time.monotonic_ns()
        delay = (when * 1e9) - current_time # convert delay from secs to nanosecs

        if delay < 0:
            print("Warning: 'when' time is in the past. Playing immediately.")
            delay = 0

        # Start playback in a separate thread to avoid blocking
        threading.Thread(target=self._playback_thread, args=(data, delay), daemon=True).start()

    def _playback_thread(self, data, delay):
        """Worker thread that waits for the target time then plays audio."""
        if delay > 0:
            # High-precision wait until the scheduled time
            self._precise_delay(delay)

        self.is_playing = True
        self.backend.play(data, sample_rate=self.sample_rate)
        self.backend.wait()
        self.is_playing = False

    def _precise_delay(self, delay):
        """Wait for the specified delay with high precision."""
        end_time = time.monotonic_ns() + delay
        while True:
            remaining = end_time - time.monotonic_ns()
            sleep_duration = self._sleep_duration_for_remaining_ns(remaining)
            if sleep_duration is None:
                if remaining <= 0:
                    break
                # Busy-wait for the final few milliseconds for precision.
                continue
            time.sleep(sleep_duration)

    @staticmethod
    def _sleep_duration_for_remaining_ns(remaining_ns):
        """
        Return a sleep duration in seconds for a remaining nanosecond delay.
        """
        if remaining_ns <= 0:
            return None
        # Sleep while there is still more than ~10 ms left.
        if remaining_ns > 10_000_000:
            return 0.005
        return None

    def stop(self):
        """Stop current playback immediately."""
        self.backend.stop()
        self.is_playing = False

    def close(self):
        """Close audio resources by stopping playback."""
        self.stop()
        self.backend.close()
