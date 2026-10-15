import time
from concurrent.futures import CancelledError
from types import SimpleNamespace

import numpy as np
import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio


class ScheduledStream:
    def __init__(self, **kwargs):
        self.closed = False
        self.ready = False
        self.error = None
        self.result = object()

    def start(self):
        pass

    def schedule(self, data, *, when):
        if when < time.monotonic() + 0.050:
            raise ValueError("insufficient lead")
        self.data = data.copy()
        self.when = when

    def wait(self, timeout):
        if self.error:
            raise self.error
        if not self.ready:
            time.sleep(0.001)
            raise TimeoutError()
        return self.result

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True


@pytest.fixture
def native(monkeypatch):
    opened = []

    def factory(**kwargs):
        stream = ScheduledStream(**kwargs)
        opened.append(stream)
        return stream

    monkeypatch.setattr(audio_module, "tachyaudio", SimpleNamespace(ScheduledOutputStream=factory))
    return opened


def test_native_submits_synchronously_and_reuses(native):
    audio = Audio(timing_mode="native")
    try:
        audio.prepare()
        data = np.ones(8, dtype=np.float32)
        target = time.monotonic() + 1
        future = audio.play(data, when=target)
        data[:] = 0
        assert native[0].when == target
        assert np.all(native[0].data == 1)
        assert not future.cancel()
        with pytest.raises(RuntimeError, match="outstanding"):
            audio.play(data, when=target)
        native[0].ready = True
        assert future.result(1) is native[0].result
        assert audio.play(data, when=target).result(1) is native[0].result
        assert len(native) == 1
    finally:
        audio.close()


def test_native_cancel_and_reopen(native):
    audio = Audio(timing_mode="native")
    future = audio.play(np.zeros(8), when=time.monotonic() + 1)
    audio.stop()
    with pytest.raises(CancelledError):
        future.result(1)
    assert native[0].closed
    audio.prepare()
    assert len(native) == 2
    audio.close()


def test_native_rejects_late_submission(native):
    audio = Audio(timing_mode="native")
    with pytest.raises(ValueError, match="lead"):
        audio.play(np.zeros(8), when=time.monotonic() - 1)
    assert native[0].closed
    assert audio.last_error is not None
    assert not audio.is_playing


@pytest.mark.parametrize("when", [0, float("nan"), float("inf")])
def test_native_requires_deadline(native, when):
    with pytest.raises(ValueError):
        Audio(timing_mode="native").play(np.zeros(8), when=when)
    assert not native


def test_native_error_surfaces(native):
    audio = Audio(timing_mode="native")
    audio.prepare()
    native[0].error = RuntimeError("clock discontinuity")
    with pytest.warns(RuntimeWarning, match="clock discontinuity"):
        future = audio.play(np.zeros(8), when=time.monotonic() + 1)
        with pytest.raises(RuntimeError, match="clock discontinuity"):
            future.result(1)
        audio.stop()
    assert native[0].closed
    assert audio.last_error is native[0].error


def test_native_timeout(native):
    audio = Audio(timing_mode="native", timeout=0.010)
    with pytest.warns(RuntimeWarning, match="timeout"):
        future = audio.play(np.zeros(8), when=time.monotonic() + 1)
        with pytest.raises(TimeoutError):
            future.result(1)
        audio.stop()
    assert native[0].closed


def test_native_unavailable_has_no_fallback(monkeypatch):
    monkeypatch.setattr(audio_module, "tachyaudio", SimpleNamespace())
    with pytest.raises(RuntimeError, match="ScheduledOutputStream"):
        Audio(timing_mode="native").prepare()


@pytest.mark.parametrize("kwargs", [{"latency": 0.01}, {"block_size": 128},
                                       {"minimum_lead_time": -1}, {"timing_mode": "other"}])
def test_native_invalid_configuration(native, kwargs):
    options = {"timing_mode": "native", **kwargs}
    with pytest.raises(ValueError):
        Audio(**options)
