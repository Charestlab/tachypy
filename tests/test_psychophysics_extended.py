import numpy as np
import pytest

from tachypy import psychophysics as psycho


def test_frequency_pattern_helpers_and_checkerboards():
    wiggles = psycho.make_wiggles_sine(
        nx=16, frequency_min=1, frequency_max=4, radial_frequency=3, radial_phase=0.2, phase=0.1
    )
    circles = psycho.make_concentric_sine_circles(nx=16, frequency=5, phase=0.3)
    sectors = psycho.make_sine_sectors(nx=16, frequency=7, phase=0.2)
    tile = psycho.make_checkerboard_tile(2)
    board = psycho.make_checkerboard(2, 2, 3)

    assert wiggles.shape == (16, 16)
    assert circles.shape == (16, 16)
    assert sectors.shape == (16, 16)
    assert tile.shape == (4, 4)
    assert board.shape == (8, 12)


def test_location_bubbles_noise_only_and_image_paths():
    np.random.seed(0)
    state = np.random.get_state()

    noise = psycho.location_bubbles(nb_bubbles=5, std_bubble=2, x_size=16, y_size=12, random_state=state)
    assert noise.shape == (12 + 2 * round(2 * 5), 16 + 2 * round(2 * 5))
    assert noise.dtype == np.bool_

    image = np.ones((10, 14, 3), dtype=np.float64) * 0.75
    state = np.random.get_state()
    noise2, stimulus = psycho.location_bubbles(
        nb_bubbles=4,
        std_bubble=1.5,
        an_image=image,
        random_state=state,
    )
    assert noise2.ndim == 2
    assert stimulus.shape == image.shape
    assert np.min(stimulus) >= 0.0
    assert np.max(stimulus) <= 1.0


def test_location_bubbles_requires_size_or_image():
    np.random.seed(1)
    state = np.random.get_state()
    with pytest.raises(ValueError, match="x_size and y_size"):
        psycho.location_bubbles(nb_bubbles=1, std_bubble=1, random_state=state)


@pytest.mark.parametrize(
    "fn,args",
    [
        ("fabriquer_grille_sin", (8, 2, 0.1, 0.0)),
        ("fabriquer_enveloppe_gaussienne", (8, 0.2)),
        ("fabriquer_wiggles_sin", (8, 1, 2, 3, 0.1, 0.0)),
        ("fabriquer_cercles_sin", (8, 2, 0.1)),
        ("fabriquer_secteurs_sin", (8, 2, 0.1)),
        ("fabriquer_grand_damier", (2, 1, 2)),
        ("fabriquer_petit_damier", (2,)),
    ],
)
def test_all_legacy_aliases_emit_deprecation(fn, args):
    with pytest.warns(DeprecationWarning):
        out = getattr(psycho, fn)(*args)
    assert out is not None
