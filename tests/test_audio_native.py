import time
from concurrent.futures import CancelledError
from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio


class ScheduledStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        self.ready = set()
        self.error = None
        self.scheduled = {}
        self.cancelled = []

    @property
    def failed(self):
        return self.closed or self.error is not None

    @property
    def lead_time(self):
        return 0.050

    def start(self):
        pass

    def schedule(self, data, *, when):
        if when < time.monotonic() + 0.050:
            raise ValueError("insufficient lead")
        if any(abs(when - other) < 0.001 for other, _ in self.scheduled.values()):
            raise ValueError("overlaps a stimulus already scheduled on this stream")
        stimulus = len(self.scheduled) + 1
        self.scheduled[stimulus] = (when, data.copy())
        return stimulus

    def wait(self, timeout, stimulus=None):
        if self.error:
            raise self.error
        if stimulus not in self.ready:
            time.sleep(0.001)
            raise TimeoutError()
        return ("timing", stimulus)

    def cancel(self, stimulus=None):
        self.cancelled.append(stimulus)

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


def test_native_queues_sounds_on_one_stream(native):
    audio = Audio(timing_mode="native")
    try:
        audio.prepare()
        data = np.ones(8, dtype=np.float32)
        target = time.monotonic() + 1
        first = audio.play(data, when=target)
        data[:] = 0
        second = audio.play(data, when=target + 0.5)
        assert native[0].scheduled[1][0] == target
        assert np.all(native[0].scheduled[1][1] == 1)
        assert not first.cancel()
        with pytest.raises(ValueError, match="overlaps"):
            audio.play(data, when=target)
        assert not native[0].closed
        assert audio.is_playing
        native[0].ready.update({1, 2})
        assert first.result(1) == ("timing", 1)
        assert second.result(1) == ("timing", 2)
        assert len(native) == 1
    finally:
        audio.close()


def test_native_cancel_and_reopen(native):
    audio = Audio(timing_mode="native")
    future = audio.play(np.zeros(8), when=time.monotonic() + 1)
    audio.stop()
    with pytest.raises(CancelledError):
        future.result(1)
    assert native[0].cancelled == [1]
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


@pytest.mark.parametrize("when", [float("nan"), float("inf")])
def test_native_rejects_non_finite_when(native, when):
    with pytest.raises(ValueError):
        Audio(timing_mode="native").play(np.zeros(8), when=when)
    assert not native


def test_native_play_now_schedules_at_soonest_onset(native):
    # play(data) with no when schedules ASAP (now + lead_time), not an error.
    audio = Audio(timing_mode="native")
    try:
        audio.prepare()
        before = time.monotonic()
        future = audio.play(np.zeros(8, dtype=np.float32))
        when, _ = native[0].scheduled[1]
        assert when >= before + native[0].lead_time
        native[0].ready.add(1)
        assert future.result(1) == ("timing", 1)
    finally:
        audio.close()


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


@pytest.mark.parametrize("kwargs", [{"block_size": 128},
                                       {"minimum_lead_time": -1}, {"timing_mode": "other"}])
def test_native_invalid_configuration(native, kwargs):
    options = {"timing_mode": "native", **kwargs}
    with pytest.raises(ValueError):
        Audio(**options)


def test_native_latency_sets_device_buffer(native, monkeypatch):
    monkeypatch.setattr(audio_module.sys, "platform", "darwin")
    Audio(timing_mode="native").prepare()
    Audio(timing_mode="native", latency=0.005, minimum_lead_time=0.015).prepare()
    assert native[0].kwargs["latency"] == 0.001
    assert "minimum_lead_time" not in native[0].kwargs
    assert native[1].kwargs["latency"] == 0.005
    assert native[1].kwargs["minimum_lead_time"] == 0.015
    with pytest.raises(ValueError, match="block_size"):
        Audio(timing_mode="native", block_size=64)


def test_native_play_now_uses_callback_without_python_deadline(native, monkeypatch):
    monkeypatch.setattr(audio_module.sys, "platform", "darwin")
    audio = Audio(timing_mode="native")
    try:
        audio.prepare()
        stream = native[0]
        submitted = []
        def asap(data):
            submitted.append(data.copy())
            return 42
        stream.schedule_asap = asap
        future = audio.play(np.zeros(8, dtype=np.float32))
        assert len(submitted) == 1
        assert not stream.scheduled
        stream.ready.add(42)
        assert future.result(1) == ("timing", 42)
    finally:
        audio.close()


@pytest.mark.parametrize("platform", ["darwin", "linux", "win32"])
@pytest.mark.parametrize("mode", [None, "auto", "native"])
def test_native_selection_on_all_platforms(native, monkeypatch, platform, mode):
    monkeypatch.setattr(audio_module.sys, "platform", platform)
    options = {} if mode is None else {"timing_mode": mode}
    device = "hw:0,0" if platform == "linux" else None
    audio = Audio(sample_rate=48000, device_id=device, **options)
    try:
        assert audio.timing_mode == "native"
        audio.prepare()
        assert native[0].kwargs["device_id"] == device
        if platform == "win32":
            assert "latency" not in native[0].kwargs
        future = audio.play(np.zeros(8), when=time.monotonic() + 1)
        native[0].ready.add(1)
        assert future.result(1) == ("timing", 1)
    finally:
        audio.close()


@pytest.mark.parametrize("platform", ["linux", "win32"])
def test_native_immediate_uses_guarded_deadline(native, monkeypatch, platform):
    monkeypatch.setattr(audio_module.sys, "platform", platform)
    audio = Audio(device_id="hw:0,0" if platform == "linux" else None)
    try:
        audio.prepare()
        def unsupported_asap(data):
            pytest.fail("schedule_asap is macOS-only")
        native[0].schedule_asap = unsupported_asap
        before = time.monotonic()
        future = audio.play(np.zeros(8))
        assert native[0].scheduled[1][0] >= before + native[0].lead_time
        native[0].ready.add(1)
        assert future.result(1) == ("timing", 1)
    finally:
        audio.close()


def test_auto_linux_without_hardware_retains_software_fallback(native, monkeypatch):
    monkeypatch.setattr(audio_module.sys, "platform", "linux")
    monkeypatch.setattr(audio_module, "_AUTO_FALLBACK_WARNED", set())
    with pytest.warns(RuntimeWarning, match="hardware device"):
        assert Audio(timing_mode="auto").timing_mode == "software"
    assert Audio().timing_mode == "native"


def test_auto_legacy_build_retains_software_fallback(monkeypatch):
    monkeypatch.setattr(audio_module, "tachyaudio", SimpleNamespace())
    monkeypatch.setattr(audio_module, "_AUTO_FALLBACK_WARNED", set())
    with pytest.warns(RuntimeWarning, match="no native scheduler"):
        assert Audio(timing_mode="auto").timing_mode == "software"
    with pytest.raises(RuntimeError, match="ScheduledOutputStream"):
        Audio().prepare()


@pytest.mark.parametrize("prepared", [False, True])
def test_play_after_anchors_delay_after_device_start(native, monkeypatch, prepared):
    clock = [100.0]

    def start(self):
        clock[0] += 2.0

    def schedule(self, data, *, when):
        assert when - clock[0] >= self.lead_time
        self.scheduled[1] = (when, data)
        return 1

    monkeypatch.setattr(ScheduledStream, "start", start)
    monkeypatch.setattr(Audio, "now", lambda self: clock[0])
    monkeypatch.setattr(ScheduledStream, "schedule", schedule)
    with Audio(timing_mode="native") if prepared else _unprepared_audio() as audio:
        future = audio.play_after(np.zeros(8), 0.25)
        assert native[0].scheduled[1][0] == 102.25
        native[0].ready.add(1)
        assert future.result(1) == ("timing", 1)


@contextmanager
def _unprepared_audio():
    audio = Audio(timing_mode="native")
    try:
        yield audio
    finally:
        audio.close()


def test_play_after_rejects_short_delay_on_first_play(native):
    with pytest.raises(ValueError, match="advance notice"):
        Audio(timing_mode="native").play_after(np.zeros(8), 0.01)
    assert native[0].closed


@pytest.mark.parametrize("read_before_prepare", [False, True])
def test_absolute_onset_is_unchanged_by_prepare(native, read_before_prepare):
    audio = Audio(timing_mode="native")
    try:
        if read_before_prepare:
            target = audio.now() + 1
        audio.prepare()
        if not read_before_prepare:
            target = audio.now() + 1
        future = audio.play(np.zeros(8), when=target)
        assert native[0].scheduled[1][0] == target
        native[0].ready.add(1)
        assert future.result(1) == ("timing", 1)
    finally:
        audio.close()


def test_failed_context_entry_releases_stream(native, monkeypatch):
    def start(self):
        raise RuntimeError("clock never became ready")

    monkeypatch.setattr(ScheduledStream, "start", start)
    with pytest.raises(RuntimeError, match="clock never became ready"), Audio(timing_mode="native"):
        pytest.fail("the context body cannot run after failed startup")
    assert native[0].closed
