import pytest

import tachypy.audio as audio_module
from tachypy.audio import Audio


def test_audio_requires_tachyaudio_when_missing(monkeypatch):
    monkeypatch.setattr(audio_module, "tachyaudio", None)
    monkeypatch.setattr(audio_module, "_TACHYAUDIO_IMPORT_ERROR", ImportError("missing"))

    with pytest.raises(RuntimeError, match="tachyaudio is required"):
        Audio()


def test_legacy_dummy_backend_is_rejected():
    with pytest.raises(ValueError, match="tachyaudio"):
        Audio(backend="dummy")
