import numpy as np
import pytest

from tachypy.audio import Audio


def test_sleep_duration_for_remaining_ns_thresholds():
    assert Audio._sleep_duration_for_remaining_ns(-1) is None
    assert Audio._sleep_duration_for_remaining_ns(0) is None
    assert Audio._sleep_duration_for_remaining_ns(5_000_000) is None
    assert Audio._sleep_duration_for_remaining_ns(10_000_001) == 0.005


def test_play_expands_mono_data_to_requested_channels(monkeypatch):
    captured = {}

    def fake_playback(self, data, delay):
        captured["shape"] = data.shape
        captured["dtype"] = data.dtype
        captured["delay"] = delay

    class FakeThread:
        def __init__(self, target, args, daemon):
            self.target = target
            self.args = args

        def start(self):
            self.target(*self.args)

    monkeypatch.setattr(Audio, "_playback_thread", fake_playback)
    monkeypatch.setattr("tachypy.audio.threading.Thread", FakeThread)
    monkeypatch.setattr("tachypy.audio.time.monotonic_ns", lambda: 2_000_000_000)

    audio = Audio(sample_rate=44_100, channels=2)
    mono = np.array([0.1, -0.1, 0.2], dtype=np.float64)

    audio.play(mono, when=1.0)

    assert captured["shape"] == (3, 2)
    assert captured["dtype"] == np.float32
    assert captured["delay"] == 0


def test_play_raises_for_wrong_channel_count():
    audio = Audio(channels=2)
    stereo = np.array([[0.1], [0.2]], dtype=np.float32)

    with pytest.raises(ValueError, match="channels"):
        audio.play(stereo, when=0)


def test_invalid_backend_raises():
    with pytest.raises(ValueError, match="tachyaudio"):
        Audio(backend="sounddevice")


def test_backend_env_accepts_auto(monkeypatch):
    monkeypatch.setenv("TACHYPY_AUDIO_BACKEND", "auto")
    audio = Audio()
    assert audio.backend_name == "tachyaudio"
