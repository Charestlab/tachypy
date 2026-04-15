import numpy as np

from tachypy.gltext_sdf import GLTextSDF


def test_glyph_binary_contains_foreground_pixels():
    mask = GLTextSDF._glyph_binary("A", scale=4, padding=2)

    assert mask.dtype == bool
    assert mask.any()


def test_signed_distance_sign_convention():
    mask = np.zeros((7, 7), dtype=bool)
    mask[2:5, 2:5] = True
    signed = GLTextSDF._signed_distance(mask)

    assert signed[3, 3] > 0
    assert signed[0, 0] < 0


def test_sdf_texture_conversion_range():
    signed = np.array([[-10.0, 0.0, 10.0]], dtype=np.float32)
    tex = GLTextSDF._to_sdf_texture(signed, spread=10.0)

    assert tex.dtype == np.uint8
    assert int(tex[0, 0]) < int(tex[0, 1]) < int(tex[0, 2])
