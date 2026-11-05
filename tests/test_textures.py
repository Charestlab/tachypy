import warnings

import numpy as np
import pytest

import tachypy._warnings as warnings_module
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


def test_texture_warns_when_normalized_image_is_converted_to_uint8(monkeypatch, capsys):
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.full((2, 2, 3), 0.5, dtype=np.float32))

    message = capsys.readouterr().err
    assert "Texture image conversion" in message
    assert "normalized to [0, 1]" in message


def test_texture_conversion_warning_reports_caller_location(monkeypatch, capsys):
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.full((2, 2, 3), 0.5, dtype=np.float32))  # this line's number should show up below

    message = capsys.readouterr().err
    assert "test_textures.py:" in message


def test_texture_conversion_warning_reports_fractional_precision_loss(monkeypatch, capsys):
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.full((2, 2, 3), 200.5, dtype=np.float32))

    message = capsys.readouterr().err
    assert "truncated (not rounded)" in message
    assert "min=200.5, max=200.5" in message


def test_texture_does_not_warn_for_lossless_integer_valued_float(monkeypatch, capsys):
    # Exact integer values within [0, 255] cast losslessly regardless of
    # dtype -- nothing is silently changed, so this should not warn.
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.full((2, 2, 3), 200.0, dtype=np.float32))

    assert capsys.readouterr().err == ""


def test_texture_does_not_warn_for_non_uint8_integer_dtype(monkeypatch, capsys):
    # int64 (numpy's common default) with values already in [0, 255] is a
    # lossless dtype narrowing, not a real problem.
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.full((2, 2, 3), 200, dtype=np.int64))

    assert capsys.readouterr().err == ""


def test_texture_does_not_warn_for_all_zero_image(monkeypatch, capsys):
    # An all-zero image isn't ambiguous between a [0, 1] and [0, 255] scale.
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    Texture(np.zeros((2, 2, 3), dtype=np.float32))

    assert capsys.readouterr().err == ""


def test_texture_conversion_warning_reports_range_when_out_of_bounds(monkeypatch, capsys):
    patch_gl(monkeypatch)
    monkeypatch.setattr(warnings_module, "_warned", set())

    image = np.full((2, 2, 3), 10.0, dtype=np.float32)
    image[0, 0, 0] = 300.0
    Texture(image)

    message = capsys.readouterr().err
    assert "outside [0, 255]" in message
    assert "max=300" in message


def test_texture_nonfinite_conversion_is_deterministic_without_numpy_warnings(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    image = np.array([[[np.nan, np.inf, -np.inf]]], dtype=np.float32)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        converted = Texture._validate_image(image)

    assert caught == []
    assert converted.tolist() == [[[0, 255, 0]]]
    assert "contains NaN or infinite values" in capsys.readouterr().err


def test_texture_upload_update_and_delete_lifecycle(monkeypatch):
    from unittest.mock import Mock

    patch_gl(monkeypatch)
    upload, update, delete = Mock(), Mock(), Mock()
    monkeypatch.setattr(textures_module, "glTexImage2D", upload)
    monkeypatch.setattr(textures_module, "glTexSubImage2D", update)
    monkeypatch.setattr(textures_module, "glDeleteTextures", delete)
    pixels = np.arange(18, dtype=np.uint8).reshape(2, 3, 3)
    texture = Texture(pixels, rect=[[10, 20], [40, 50]])
    assert upload.call_args.args[3:5] == (3, 2)
    np.testing.assert_array_equal(upload.call_args.args[-1], pixels)
    replacement = np.full_like(pixels, 123)
    texture.update(replacement)
    assert update.call_args.args[4:6] == (3, 2)
    np.testing.assert_array_equal(update.call_args.args[-1], replacement)
    texture.delete()
    texture.delete()
    delete.assert_called_once_with([1])
    assert texture.texture_id == 0


@pytest.mark.parametrize("rect", [[0, 1, 2], [0, 0, 0, 2], [0, 2, 3, 1]])
def test_texture_rejects_invalid_drawing_rectangles(rect):
    with pytest.raises(ValueError):
        Texture._normalize_rect(rect)


def test_texture_draw_preserves_orientation_and_resets_state(monkeypatch):
    from unittest.mock import Mock

    patch_gl(monkeypatch)
    calls = Mock()
    for name in ("glVertex2f", "glTexCoord2f", "glBindTexture", "glEnable", "glDisable", "glLoadIdentity"):
        monkeypatch.setattr(textures_module, name, getattr(calls, name))
    texture = Texture(np.zeros((2, 3, 3), dtype=np.uint8))
    texture.move_by(10, 20)
    assert texture.get_bounds() == (10, 20, 13, 22)
    calls.reset_mock()
    texture.draw(a_rect=[1, 2, 7, 10])
    assert [c.args for c in calls.glVertex2f.call_args_list] == [(1, 2), (7, 2), (7, 10), (1, 10)]
    assert [c.args for c in calls.glTexCoord2f.call_args_list] == [(0, 0), (1, 0), (1, 1), (0, 1)]
    assert calls.glBindTexture.call_args.args == (textures_module.GL_TEXTURE_2D, 0)
    calls.glDisable.assert_called_once_with(textures_module.GL_TEXTURE_2D)
    calls.glLoadIdentity.assert_called_once()
    texture.draw(rect=[2, 3, 8, 11])
    assert texture.get_bounds() == (2, 3, 8, 11)
    with pytest.raises(ValueError, match="either"):
        texture.draw(rect=[0, 0, 1, 1], a_rect=[0, 0, 1, 1])


def test_texture_nonnumeric_conversion_and_all_nonfinite_pixels(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())
    result = Texture._validate_image(np.array([[["12", "34", "56"]]]))
    assert result.tolist() == [[[12, 34, 56]]]
    assert "may not convert as intended" in capsys.readouterr().err
    monkeypatch.setattr(warnings_module, "_warned", set())
    result = Texture._validate_image(np.full((1, 1, 3), np.nan))
    assert result.tolist() == [[[0, 0, 0]]]
