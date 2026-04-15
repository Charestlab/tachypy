import pytest

import tachypy.audio as audio_module


def test_sounddevice_backend_request_errors_when_unavailable(monkeypatch):
    monkeypatch.setattr(audio_module, "sd", None)
    with pytest.raises(RuntimeError, match="sounddevice"):
        audio_module._build_backend("sounddevice")


def test_auto_backend_falls_back_to_dummy_with_warning(monkeypatch):
    monkeypatch.setattr(audio_module, "sd", None)
    with pytest.warns(RuntimeWarning, match="falling back to dummy"):
        backend = audio_module._build_backend("auto")
    assert backend.name == "dummy"
