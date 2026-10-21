import threading
import time
from concurrent.futures import CancelledError

import numpy as np
import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio


class FakeOutputStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.started = False
        self.events = []
        self.frames = []
        self.capacity = 3
        self.allow_drain = threading.Event()
        self.allow_drain.set()
        self.write_error = None

    def start(self):
        self.events.append("start")
        self.started = True

    def write(self, data):
        if self.write_error is not None:
            raise self.write_error
        assert not self.closed
        self.events.append("write")
        accepted = min(len(data), self.capacity)
        self.frames.extend(data[:accepted].tolist())
        return accepted

    def drain(self, timeout=None):
        assert timeout == 0
        self.events.append("drain")
        return self.allow_drain.is_set()

    def close(self):
        assert not self.closed
        self.events.append("close")
        self.closed = True


@pytest.fixture
def streams(monkeypatch):
    opened = []

    def factory(**kwargs):
        stream = FakeOutputStream(**kwargs)
        opened.append(stream)
        return stream

    monkeypatch.setattr(audio_module, "tachyaudio", type("Backend", (), {"OutputStream": factory}))
    return opened


def test_open_failure_reaches_caller(monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("device unavailable")

    monkeypatch.setattr(audio_module, "tachyaudio", type("Backend", (), {"OutputStream": fail}))
    audio = Audio()
    with pytest.raises(RuntimeError, match="device unavailable"):
        audio.play(np.zeros(4))
    assert isinstance(audio.last_error, RuntimeError)
    assert not audio.is_playing
    assert not audio._active


def test_prefills_then_streams_large_clip_and_reuses(streams):
    audio = Audio(sample_rate=48000, timeout=1)
    data = np.arange(20, dtype=np.float32)
    try:
        audio.play(data).result(timeout=1)
        audio.play(data).result(timeout=1)
        assert len(streams) == 1
        assert streams[0].events[:2] == ["write", "start"]
        assert streams[0].frames == list(data) * 2
        assert not streams[0].closed
        assert not audio.is_playing
    finally:
        audio.close()
    assert streams[0].closed


def test_prepare_warms_and_reuses_stream(streams):
    audio = Audio()
    try:
        audio.prepare()
        audio.prepare()
        assert len(streams) == 1
        assert streams[0].started
        audio.play(np.zeros(4)).result(timeout=1)
        assert len(streams) == 1
    finally:
        audio.close()


def test_overlapping_sounds_get_independent_streams(streams):
    audio = Audio()
    try:
        audio.prepare()
        streams[0].allow_drain.clear()
        first = audio.play(np.ones(4))
        second = audio.play(np.full(4, 2))
        second.result(timeout=1)
        assert not first.done()
        assert audio.is_playing
        streams[0].allow_drain.set()
        first.result(timeout=1)
        assert len(streams) == 2
        assert streams[0].closed
        assert not streams[1].closed
        assert streams[0].frames == [1] * 4
        assert streams[1].frames == [2] * 4
    finally:
        audio.close()


def test_worker_error_is_observable_and_next_play_recovers(streams):
    audio = Audio()
    try:
        audio.prepare()
        streams[0].write_error = RuntimeError("write failed")
        with pytest.warns(RuntimeWarning, match="Audio playback failed"):
            future = audio.play(np.zeros(4))
            with pytest.raises(RuntimeError, match="write failed"):
                future.result(timeout=1)
            audio._thread.join(timeout=1)
        with pytest.raises(RuntimeError, match="write failed"):
            audio.wait()
        assert streams[0].closed
        assert isinstance(audio.last_error, RuntimeError)
        audio.play(np.zeros(4)).result(timeout=1)
        assert len(streams) == 2
    finally:
        audio.close()


def test_stop_cancels_scheduled_sound_without_playing(streams):
    audio = Audio()
    future = audio.play(np.zeros(4), when=time.monotonic() + 60)
    audio.stop()
    with pytest.raises(CancelledError):
        future.result(timeout=1)
    assert streams[0].closed
    assert "write" not in streams[0].events
    assert not audio.is_playing
    audio.stop()


def test_stop_interrupts_drain_and_can_reopen(streams):
    audio = Audio()
    audio.prepare()
    streams[0].allow_drain.clear()
    future = audio.play(np.zeros(4))
    audio.stop()
    with pytest.raises(CancelledError):
        future.result(timeout=1)
    assert streams[0].closed
    audio.play(np.zeros(4)).result(timeout=1)
    audio.close()


def test_drain_timeout_surfaces_and_closes_stream(streams):
    audio = Audio(timeout=0.01)
    audio.prepare()
    streams[0].allow_drain.clear()
    with pytest.warns(RuntimeWarning, match="Audio playback failed"):
        future = audio.play(np.zeros(4))
        with pytest.raises(TimeoutError, match="did not drain"):
            future.result(timeout=1)
        audio._thread.join(timeout=1)
    assert streams[0].closed
    audio.close()


def test_warns_and_plays_immediately_for_past_when_in_software_mode(streams):
    audio = Audio()
    try:
        when = time.monotonic() - 0.1
        with pytest.warns(RuntimeWarning, match="'when' time is in the past; playing immediately"):
            future = audio.play(np.zeros(4), when=when)
            future.result(timeout=1)
        assert streams[0].frames == [0.0] * 4
        assert not audio.is_playing
    finally:
        audio.close()


def test_play_owns_buffer_during_scheduled_playback(streams):
    audio = Audio()
    data = np.ones(4, dtype=np.float32)
    try:
        future = audio.play(data, when=time.monotonic() + 0.02)
        data[:] = 0
        future.result(timeout=1)
        assert streams[0].frames == [1] * 4
    finally:
        audio.close()


@pytest.mark.parametrize("data", [[], np.zeros((2, 2, 2)), np.zeros(0)])
def test_invalid_buffers_rejected(streams, data):
    with pytest.raises(ValueError):
        Audio().play(data)
    assert not streams


def test_audio_constructor_validates_sample_rate_and_channels():
    with pytest.raises(ValueError, match="sample_rate"):
        Audio(sample_rate=0)
    with pytest.raises(ValueError, match="channels"):
        Audio(channels=0)
