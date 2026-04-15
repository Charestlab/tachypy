import numpy as np
import pytest

import tachypy.textures as textures_module
from tachypy.textures import Texture


def patch_gl(monkeypatch):
    monkeypatch.setattr(textures_module, "glGenTextures", lambda *args, **kwargs: 1)
    monkeypatch.setattr(textures_module, "glBindTexture", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glPixelStorei", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glTexImage2D", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glTexParameterf", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glEnable", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glDisable", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glLoadIdentity", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glTexSubImage2D", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glDeleteTextures", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glTexEnvf", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glColor3f", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glBegin", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glTexCoord2f", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glVertex2f", lambda *args, **kwargs: None)
    monkeypatch.setattr(textures_module, "glEnd", lambda *args, **kwargs: None)


def test_texture_rect_and_hit_test(monkeypatch):
    patch_gl(monkeypatch)
    image = np.zeros((20, 10, 3), dtype=np.uint8)

    texture = Texture(image)

    assert texture.get_bounds() == (0.0, 0.0, 10.0, 20.0)
    assert texture.hit_test(5, 5) is True
    assert texture.hit_test(15, 25) is False


def test_texture_update_rejects_shape_changes(monkeypatch):
    patch_gl(monkeypatch)
    image = np.zeros((20, 10, 3), dtype=np.uint8)
    texture = Texture(image)

    with pytest.raises(ValueError, match="does not match"):
        texture.update(np.zeros((19, 10, 3), dtype=np.uint8))


def test_texture_rejects_invalid_image_shape(monkeypatch):
    patch_gl(monkeypatch)
    with pytest.raises(ValueError, match="shape"):
        Texture(np.zeros((10, 10), dtype=np.uint8))


def test_texture_rejects_dual_rect_args(monkeypatch):
    patch_gl(monkeypatch)
    image = np.zeros((20, 10, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="either"):
        Texture(image, a_rect=[0, 0, 1, 1], rect=[0, 0, 2, 2])
