import numpy as np
import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio


class FakeOutputStream:
    calls = []
    drain_result = True

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.closed = False
        FakeOutputStream.calls.append(("init", kwargs))

    def start(self):
        FakeOutputStream.calls.append(("start",))

    def write_all(self, data, timeout=None):
        FakeOutputStream.calls.append(("write_all", data.shape, data.dtype, timeout))
        return data.shape[0]

    def drain(self, timeout=None):
        FakeOutputStream.calls.append(("drain", timeout))
        return self.drain_result

    def stop(self):
        FakeOutputStream.calls.append(("stop",))

    def close(self):
        self.closed = True
        FakeOutputStream.calls.append(("close",))


def install_fake_tachyaudio(monkeypatch):
    FakeOutputStream.calls = []
    fake = type("FakeTachyAudio", (), {"OutputStream": FakeOutputStream})
    monkeypatch.setattr(audio_module, "tachyaudio", fake)
    return fake


def test_audio_play_validation_errors():
    audio = Audio()
    with pytest.raises(ValueError, match="NumPy"):
        audio.play([1, 2, 3], when=0)
    with pytest.raises(ValueError, match="1D or 2D"):
        audio.play(np.zeros((2, 2, 2), dtype=np.float32), when=0)


def test_audio_playback_thread_uses_tachyaudio_stream(monkeypatch):
    install_fake_tachyaudio(monkeypatch)
    audio = Audio(sample_rate=22_050, channels=1, block_size=64, device_id="dev", latency=0.01, timeout=0.5)
    data = np.zeros(8, dtype=np.float32)

    audio._playback_thread(data, delay=0)

    assert audio.is_playing is False
    assert FakeOutputStream.calls[0] == (
        "init",
        {
            "sample_rate": 22_050,
            "channels": 1,
            "block_size": 64,
            "device_id": "dev",
            "latency": 0.01,
            "dtype": "float32",
        },
    )
    assert ("start",) in FakeOutputStream.calls
    assert ("write_all", (8,), np.dtype("float32"), 0.5) in FakeOutputStream.calls
    assert ("drain", 0.5) in FakeOutputStream.calls
    assert FakeOutputStream.calls[-1] == ("close",)


def test_audio_playback_thread_delay_and_drain_timeout(monkeypatch):
    install_fake_tachyaudio(monkeypatch)
    audio = Audio(timeout=0.1)
    events = []
    monkeypatch.setattr(audio, "_precise_delay", lambda d: events.append(("delay", d)))
    FakeOutputStream.drain_result = False

    with pytest.raises(TimeoutError, match="did not drain"):
        audio._playback_thread(np.zeros(4, dtype=np.float32), delay=10)

    FakeOutputStream.drain_result = True
    assert events == [("delay", 10)]
    assert FakeOutputStream.calls[-1] == ("close",)


def test_stop_closes_active_stream(monkeypatch):
    install_fake_tachyaudio(monkeypatch)
    audio = Audio()
    stream = FakeOutputStream(sample_rate=1, channels=1, block_size=None, device_id=None, latency=None, dtype="float32")
    audio._stream = stream
    audio.is_playing = True

    audio.stop()

    assert ("stop",) in FakeOutputStream.calls
    assert ("close",) in FakeOutputStream.calls
    assert audio._stream is None
    assert audio.is_playing is False


def test_stop_does_not_clear_replaced_stream(monkeypatch):
    install_fake_tachyaudio(monkeypatch)
    audio = Audio()
    stream = FakeOutputStream(sample_rate=1, channels=1, block_size=None, device_id=None, latency=None, dtype="float32")
    replacement = FakeOutputStream(
        sample_rate=1,
        channels=1,
        block_size=None,
        device_id=None,
        latency=None,
        dtype="float32",
    )
    audio._stream = stream
    audio.is_playing = True

    original_close = stream.close

    def close_and_replace():
        audio._stream = replacement
        audio.is_playing = True
        original_close()

    stream.close = close_and_replace

    audio.stop()

    assert audio._stream is replacement
    assert audio.is_playing is True


def test_audio_constructor_validates_sample_rate_and_channels():
    with pytest.raises(ValueError, match="sample_rate"):
        Audio(sample_rate=0)
    with pytest.raises(ValueError, match="channels"):
        Audio(channels=0)
