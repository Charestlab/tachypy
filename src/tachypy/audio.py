import numpy as np
import threading
import time

try:
    import sounddevice as sd
except Exception:
    sd = None

class Audio:
    """Simple scheduled audio playback wrapper around sounddevice."""

    def __init__(self, sample_rate=44100, channels=1):
        """Initialize audio playback parameters and backend availability."""
        if sd is None:
            raise RuntimeError(
                "Audio backend `sounddevice` is unavailable. "
                "On macOS, try installing PortAudio and reinstalling sounddevice "
                "(e.g., `brew install portaudio` then `pip install sounddevice`)."
            )
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_playing = False

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
        sd.play(data, samplerate=self.sample_rate)
        sd.wait()  # Wait until playback is finished
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
        sd.stop()
        self.is_playing = False

    def close(self):
        """Close audio resources by stopping playback."""
        self.stop()
