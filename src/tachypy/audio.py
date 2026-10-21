"""TachyPy audio convenience wrapper backed by tachyaudio."""

from __future__ import annotations

import math
import os
import threading
import time
import warnings
from concurrent.futures import CancelledError, Future

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
        timing_mode="software",
        minimum_lead_time=None,
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
            Passed through to ``tachyaudio.OutputStream``. In native
            mode ``latency`` is the device buffer in seconds, passed to
            ``tachyaudio.ScheduledOutputStream``; leave it ``None`` to let
            tachyaudio choose it on Linux or preserve the shared HAL buffer
            on macOS. An explicit macOS latency changes the shared device
            buffer until close; avoid conflicting settings in concurrent streams.
        timeout : float | None
            Software write/drain timeout; native mode total completion timeout,
            including the wait until the scheduled onset.
        timing_mode : str
            ``"software"`` (default) or experimental device-clock ``"native"``
            (macOS Core Audio, or Linux via direct ALSA with an explicit
            ``device_id="hw:CARD,DEVICE"``; Windows native scheduling is not
            yet available).
        minimum_lead_time : float | None
            Minimum advance notice in seconds for native scheduling. ``None``
            (default) lets tachyaudio derive it from the device's measured
            output delay on Linux and macOS.
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
        if timing_mode not in ("software", "native"):
            raise ValueError("timing_mode must be 'software' or 'native'")
        if minimum_lead_time is not None and (
            not math.isfinite(minimum_lead_time) or minimum_lead_time < 0
        ):
            raise ValueError("minimum_lead_time must be finite and nonnegative")
        if timing_mode == "native" and block_size is not None:
            raise ValueError("native timing chooses its own period; omit block_size")
        self.timing_mode = timing_mode
        self.minimum_lead_time = minimum_lead_time
        if timeout is not None and (not math.isfinite(timeout) or timeout < 0):
            raise ValueError("timeout must be finite and nonnegative")
        self.is_playing = False
        self._stream = None
        self._lock = threading.Lock()
        self._thread = None
        self._active = {}
        self._last_playback = None
        self.last_error = None
        self._stopping = False

    def _open_stream(self):
        if self.timing_mode == "native":
            factory = getattr(tachyaudio, "ScheduledOutputStream", None)
            if factory is None:
                raise RuntimeError("native timing requires a tachyaudio build with ScheduledOutputStream")
            options = {}
            if self.latency is not None:
                options["latency"] = self.latency
            if self.minimum_lead_time is not None:
                options["minimum_lead_time"] = self.minimum_lead_time
            return factory(
                sample_rate=self.sample_rate,
                channels=self.channels,
                device_id=self.device_id,
                **options,
            )
        return tachyaudio.OutputStream(
            sample_rate=self.sample_rate,
            channels=self.channels,
            block_size=self.block_size,
            device_id=self.device_id,
            latency=self.latency,
            dtype="float32",
        )

    def prepare(self):
        """Open and warm an idle stream before a timing-sensitive trial.

        Device errors are raised to the caller. Call ``close()`` when finished
        to release the retained stream.
        """
        with self._lock:
            if self._stopping:
                raise RuntimeError("audio is stopping")
            if self._stream is None:
                stream = self._open_stream()
                try:
                    stream.start()
                    if self.timing_mode == "software":
                        stream.drain(timeout=0)
                except BaseException:
                    stream.close()
                    raise
                self._stream = stream

    def play(self, data, when=0):
        """Play a NumPy buffer, optionally scheduled at an absolute monotonic time.

        ``when`` is expressed in seconds from ``time.monotonic_ns() / 1e9``.
        Returns a ``Future``; call ``result()`` to wait and surface playback
        failures. Device opening happens synchronously unless ``prepare()``
        already supplied an idle stream. Concurrent sounds use separate streams.

        Native mode instead submits immediately to the device-clock scheduler
        and requires an explicit future deadline. Several sounds can be queued
        ahead on one stream (up to 32 on Linux and macOS), back to
        back if desired; sounds overlapping in time are rejected. Its Future
        returns ScheduledTiming estimates, not physical measurements. Use
        stop(), not Future.cancel(), to cancel submitted requests.
        """
        buffer = self._prepare_buffer(data)
        when = float(when)
        if not math.isfinite(when):
            raise ValueError("when must be finite")
        if self.timing_mode == "native":
            if when <= 0:
                raise ValueError("native timing requires an explicit future monotonic 'when'")
            return self._play_native(buffer, when)
        current_time = time.monotonic_ns()
        delay = int((float(when) * 1e9) - current_time)
        if delay < 0 and when != 0 and self.timing_mode == "software":
            warnings.warn("'when' time is in the past; playing immediately.", RuntimeWarning, stacklevel=2)
        target_ns = round(when * 1e9) if self.timing_mode == "native" else current_time + max(delay, 0)
        future = Future()
        cancelled = threading.Event()
        with self._lock:
            if self._stopping:
                raise RuntimeError("audio is stopping")
            try:
                stream = self._stream if self._stream is not None else self._open_stream()
            except Exception as error:
                self.last_error = error
                raise
            self._stream = None
            thread = threading.Thread(
                target=self._run_playback,
                args=(buffer, target_ns, stream, cancelled, future),
                daemon=True,
            )
            self._active[future] = (cancelled, thread)
            self._last_playback = future
            self._thread = thread
            self.is_playing = True
            try:
                thread.start()
            except BaseException:
                del self._active[future]
                self.is_playing = bool(self._active)
                stream.close()
                raise
        return future

    def _play_native(self, buffer, when):
        """Queue one stimulus on the shared native stream and track it."""
        future = Future()
        cancelled = threading.Event()
        with self._lock:
            if self._stopping:
                raise RuntimeError("audio is stopping")
            stream = self._stream
            try:
                if stream is None:
                    stream = self._open_stream()
                    try:
                        stream.start()
                    except BaseException:
                        stream.close()
                        raise
                    self._stream = stream
                stimulus = stream.schedule(buffer, when=when)
            except BaseException as error:
                self.last_error = error
                if stream is not None and not self._active:
                    stream.close()
                    self._stream = None
                raise
            future.set_running_or_notify_cancel()
            thread = threading.Thread(
                target=self._run_native, args=(stream, stimulus, cancelled, future), daemon=True
            )
            self._active[future] = (cancelled, thread)
            self._last_playback = future
            self._thread = thread
            self.is_playing = True
            try:
                thread.start()
            except BaseException:
                del self._active[future]
                self.is_playing = bool(self._active)
                stream.cancel(stimulus)
                raise
        return future

    def _run_native(self, stream, stimulus, cancelled, future):
        error = None
        result = None
        try:
            result = self._wait_native(stream, stimulus, cancelled)
        except BaseException as failure:
            error = failure
        # A missed onset only drops this sound; a stream fault ends the stream.
        broken = error is not None and stream.failed
        with self._lock:
            self._active.pop(future, None)
            self.is_playing = bool(self._active)
            if broken and self._stream is stream:
                self._stream = None
            if error is not None and not isinstance(error, CancelledError):
                self.last_error = error
        if broken:
            stream.close()
        if not future.cancelled():
            if error is None:
                future.set_result(result)
            else:
                future.set_exception(error)
        if error is not None and not isinstance(error, CancelledError):
            warnings.warn(f"Audio playback failed: {error}", RuntimeWarning, stacklevel=2)

    def wait(self, timeout=None):
        """Wait for the most recently requested sound and raise its failure."""
        with self._lock:
            future = self._last_playback
        if future is not None:
            return future.result(timeout=timeout)

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
        if data.shape[0] == 0:
            raise ValueError("Data must contain at least one frame.")
        return np.array(data, dtype=np.float32, order="C", copy=True)

    def _run_playback(self, data, target_ns, stream, cancelled, future):
        error = None
        result = None
        try:
            if not future.set_running_or_notify_cancel():
                raise CancelledError()
            while True:
                remaining = (target_ns - time.monotonic_ns()) / 1e9
                if remaining <= 0:
                    break
                if cancelled.wait(min(remaining, 0.005)):
                    raise CancelledError()
            if cancelled.is_set():
                raise CancelledError()
            deadline = None if self.timeout is None else time.monotonic() + self.timeout
            written = stream.write(data)
            if not 0 <= written <= len(data):
                raise RuntimeError("backend returned an invalid frame count")
            if written == len(data):
                stream.drain(timeout=0)
            stream.start()
            while written < len(data):
                if cancelled.is_set():
                    raise CancelledError()
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("audio write did not complete before timeout")
                accepted = stream.write(data[written:])
                if not 0 <= accepted <= len(data) - written:
                    raise RuntimeError("backend returned an invalid frame count")
                written += accepted
                if written < len(data):
                    cancelled.wait(0.001)
            deadline = None if self.timeout is None else time.monotonic() + self.timeout
            while not stream.drain(timeout=0):
                if cancelled.wait(0.001):
                    raise CancelledError()
                if deadline is not None and time.monotonic() >= deadline:
                    raise TimeoutError("audio playback did not drain before timeout")
            if cancelled.is_set():
                raise CancelledError()
        except BaseException as failure:
            error = failure
        finally:
            with self._lock:
                retain = error is None and not self._stopping and self._stream is None
                if retain:
                    self._stream = stream
            try:
                if not retain:
                    stream.close()
            except BaseException as failure:
                if error is None:
                    error = failure
            finally:
                with self._lock:
                    self._active.pop(future, None)
                    self.is_playing = bool(self._active)
                    if error is not None and not isinstance(error, CancelledError):
                        self.last_error = error
            if not future.cancelled():
                if error is None:
                    future.set_result(result)
                else:
                    future.set_exception(error)
            if error is not None and not isinstance(error, CancelledError):
                warnings.warn(f"Audio playback failed: {error}", RuntimeWarning, stacklevel=2)

    def _wait_native(self, stream, stimulus, cancelled):
        deadline = None if self.timeout is None else time.monotonic() + self.timeout
        while True:
            if cancelled.is_set():
                stream.cancel(stimulus)
                raise CancelledError()
            if deadline is not None and time.monotonic() >= deadline:
                stream.cancel(stimulus)
                raise TimeoutError("native playback exceeded timeout")
            try:
                result = stream.wait(timeout=0.010, stimulus=stimulus)
            except TimeoutError:
                continue
            if cancelled.is_set():
                raise CancelledError()
            return result

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
        """Cancel pending/active sounds and release all retained streams."""
        with self._lock:
            if self._stopping:
                return
            self._stopping = True
            stream = self._stream
            self._stream = None
            active = list(self._active.values())
            for cancelled, thread in active:
                cancelled.set()
        try:
            for cancelled, thread in active:
                if thread is not threading.current_thread():
                    thread.join()
            if stream is not None:
                stream.close()
        finally:
            with self._lock:
                self.is_playing = False
                self._stopping = False

    def close(self):
        """Close audio resources by stopping playback."""
        self.stop()
