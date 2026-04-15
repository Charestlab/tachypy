import numpy as np
import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio, _AudioBackend, _DummyBackend, _SoundDeviceBackend


def test_audio_backend_base_methods_raise_and_close_calls_stop():
    backend = _AudioBackend()
    with pytest.raises(NotImplementedError):
        backend.play(np.zeros(1, dtype=np.float32), 44100)
    with pytest.raises(NotImplementedError):
        backend.wait()
    with pytest.raises(NotImplementedError):
        backend.stop()


def test_sounddevice_backend_calls_sd(monkeypatch):
    calls = []

    class FakeSD:
        @staticmethod
        def play(data, samplerate):
            calls.append(("play", samplerate, data.shape))

        @staticmethod
        def wait():
            calls.append(("wait",))

        @staticmethod
        def stop():
            calls.append(("stop",))

    monkeypatch.setattr(audio_module, "sd", FakeSD)
    backend = _SoundDeviceBackend()
    backend.play(np.zeros((4, 1), dtype=np.float32), sample_rate=22050)
    backend.wait()
    backend.stop()
    assert calls == [("play", 22050, (4, 1)), ("wait",), ("stop",)]


def test_dummy_backend_wait_noop_and_sleep_branch(monkeypatch):
    backend = _DummyBackend()
    backend.wait()  # no scheduled playback branch

    t = {"now": 1_000_000_000}
    slept = []

    monkeypatch.setattr(audio_module.time, "monotonic_ns", lambda: t["now"])
    monkeypatch.setattr(audio_module.time, "sleep", lambda s: slept.append(s))
    backend.play(np.zeros(100, dtype=np.float32), sample_rate=100)
    backend.wait()
    assert slept and slept[0] > 0


def test_build_backend_auto_prefers_sounddevice_when_available(monkeypatch):
    class FakeSD:
        pass

    monkeypatch.setattr(audio_module, "sd", FakeSD)
    backend = audio_module._build_backend("auto")
    assert backend.name == "sounddevice"


def test_audio_play_validation_errors():
    audio = Audio(backend="dummy")
    with pytest.raises(ValueError, match="NumPy"):
        audio.play([1, 2, 3], when=0)
    with pytest.raises(ValueError, match="1D or 2D"):
        audio.play(np.zeros((2, 2, 2), dtype=np.float32), when=0)


def test_audio_playback_thread_and_close(monkeypatch):
    events = []

    class FakeBackend:
        name = "fake"

        def play(self, data, sample_rate):
            events.append(("play", sample_rate, data.shape))

        def wait(self):
            events.append(("wait",))

        def stop(self):
            events.append(("stop",))

        def close(self):
            events.append(("close",))

    monkeypatch.setattr(audio_module, "_build_backend", lambda _: FakeBackend())
    audio = Audio(backend="dummy")
    audio._playback_thread(np.zeros(8, dtype=np.float32), delay=0)
    assert audio.is_playing is False
    assert events[:2] == [("play", 44100, (8,)), ("wait",)]

    monkeypatch.setattr(audio, "_precise_delay", lambda d: events.append(("delay", d)))
    audio._playback_thread(np.zeros(4, dtype=np.float32), delay=10)
    assert ("delay", 10) in events

    audio.stop()
    audio.close()
    assert ("stop",) in events and ("close",) in events
