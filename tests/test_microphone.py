from unittest.mock import Mock

import numpy as np
import pytest

import tachypy.microphone as capture


@pytest.fixture
def device(monkeypatch):
    factory = Mock()
    monkeypatch.setattr(capture.tachyaudio, "InputStream", factory)
    return factory


def test_record_discards_old_frames_and_returns_writable_stereo_copy(device):
    mic = capture.Microphone(sample_rate=1000, channels=2)
    device.assert_not_called()
    stream = device.return_value
    stream.read_exactly.return_value = np.arange(6, dtype=np.float32).tobytes()
    with mic:
        clip = mic.record(0.003)
        stream.start.assert_called_once()
        assert [c[0] for c in stream.method_calls] == ["start", "flush", "read_exactly"]
        stream.read_exactly.assert_called_once_with(3, timeout=2.003)
        assert clip.shape == (3, 2)
        assert clip.dtype == np.float32
        clip[0, 0] = -1
    stream.close.assert_called_once()


def test_failed_start_closes_device_and_can_retry(device):
    mic = capture.Microphone()
    broken, healthy = Mock(), Mock()
    broken.start.side_effect = RuntimeError("device disconnected")
    device.side_effect = [broken, healthy]
    with pytest.raises(RuntimeError, match="disconnected"):
        mic.start()
    broken.close.assert_called_once()
    with mic:
        healthy.start.assert_called_once()
    healthy.close.assert_called_once()


def test_invalid_requests_do_not_open_device(device):
    mic = capture.Microphone()
    with pytest.raises(ValueError, match="positive"):
        mic.read(0)
    with pytest.raises(ValueError, match="positive"):
        mic.read_exactly(-1)
    for seconds in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="positive"):
            mic.record(seconds)
    device.assert_not_called()


def test_partial_mono_read_stop_and_restart(device):
    mic = capture.Microphone()
    stream = device.return_value
    stream.read.return_value = np.array([0.25], dtype=np.float32).tobytes()
    np.testing.assert_array_equal(mic.read(2), [0.25])
    stream.read.assert_called_once_with(2)
    mic.stop()
    mic.stop()
    stream.stop.assert_called_once()
    mic.start()
    assert stream.start.call_count == 2
    mic.close()
    mic.close()
    stream.close.assert_called_once()


@pytest.mark.parametrize("options", [{"sample_rate": 0}, {"channels": -1}])
def test_invalid_capture_config_is_rejected_at_construction(options, device):
    with pytest.raises(ValueError, match="positive"):
        capture.Microphone(**options)
    device.assert_not_called()
