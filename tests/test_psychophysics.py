import numpy as np
import pytest

from tachypy.psychophysics import (
    fabriquer_gabor,
    location_bubbles,
    make_gabor,
    make_sine_grating,
    normalize_to_unit_interval,
    noisy_bit_dithering,
    stretch,
)


def test_fabriquer_gabor_has_expected_shape_and_range():
    with pytest.warns(DeprecationWarning):
        gabor = fabriquer_gabor(nx=64, frequence=6, phase=0.5, angle=0.2, ecart_type=0.1)

    assert gabor.shape == (64, 64)
    assert np.min(gabor) >= 0.0
    assert np.max(gabor) <= 1.0


def test_stretch_handles_constant_image_without_nan():
    im = np.full((4, 4), 3.14)
    with pytest.warns(DeprecationWarning):
        result = stretch(im)

    assert np.all(result == 0)
    assert np.isfinite(result).all()


def test_noisy_bit_dithering_respects_depth():
    im = np.linspace(0, 1, 25, dtype=np.float64).reshape(5, 5)
    dithered = noisy_bit_dithering(im, depth=16)

    assert dithered.dtype == np.uint8
    assert dithered.min() >= 0
    assert dithered.max() <= 15


def test_location_bubbles_requires_random_state():
    try:
        location_bubbles(nb_bubbles=5, std_bubble=2, x_size=16, y_size=16, random_state=None)
    except ValueError as err:
        assert "pseudo-random" in str(err)
    else:
        raise AssertionError("Expected ValueError when random_state is None")


def test_english_alias_matches_legacy_output():
    with pytest.warns(DeprecationWarning):
        legacy = fabriquer_gabor(nx=32, frequence=4, phase=0.0, angle=0.0, ecart_type=0.2)
    modern = make_gabor(nx=32, frequency=4, phase=0.0, angle=0.0, std_dev=0.2)

    assert np.allclose(legacy, modern)


def test_modern_normalization_and_sine_grating_shapes():
    arr = np.array([[1.0, 2.0], [3.0, 5.0]])
    norm = normalize_to_unit_interval(arr)
    grating = make_sine_grating(nx=16, frequency=3, phase=0.1, angle=0.3)

    assert norm.min() == 0.0
    assert norm.max() == 1.0
    assert grating.shape == (16, 16)
