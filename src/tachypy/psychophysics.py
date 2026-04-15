import warnings

import numpy as np


__all__ = [
    "make_sine_grating",
    "make_gaussian_envelope",
    "make_gabor",
    "normalize_to_unit_interval",
    "noisy_bit_dithering",
    "make_wiggles_sine",
    "make_concentric_sine_circles",
    "make_sine_sectors",
    "make_checkerboard",
    "make_checkerboard_tile",
    "location_bubbles",
    # Legacy French names kept for backward compatibility.
    "fabriquer_grille_sin",
    "fabriquer_enveloppe_gaussienne",
    "fabriquer_gabor",
    "stretch",
    "fabriquer_wiggles_sin",
    "fabriquer_cercles_sin",
    "fabriquer_secteurs_sin",
    "fabriquer_grand_damier",
    "fabriquer_petit_damier",
]


def _warn_legacy_name(legacy_name, replacement_name):
    warnings.warn(
        f"`{legacy_name}` is deprecated and will be removed in a future release. "
        f"Use `{replacement_name}` instead.",
        DeprecationWarning,
        stacklevel=2,
    )


def make_sine_grating(nx, frequency, phase, angle):
    """Create a square sine grating image with values in [0, 1]."""
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    ramp = np.cos(angle) * xv + np.sin(angle) * yv
    return np.sin(frequency * 2 * np.pi * ramp + phase) / 2 + 0.5


def make_gaussian_envelope(nx, std_dev):
    """Create a centered square Gaussian envelope image with values in [0, 1]."""
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    return np.exp(-((xv - 0.5) ** 2 / std_dev ** 2) - ((yv - 0.5) ** 2 / std_dev ** 2))


def make_gabor(nx, frequency, phase, angle, std_dev):
    """Create a Gabor patch image with values in [0, 1]."""
    gaussian = make_gaussian_envelope(nx, std_dev)
    sine = make_sine_grating(nx, frequency, phase, angle)
    return gaussian * (sine - 0.5) + 0.5


def normalize_to_unit_interval(im):
    """Normalize an array to [0, 1], returning zeros for constant arrays."""
    im = np.asarray(im, dtype=np.float64)
    im_min = np.amin(im)
    im_max = np.amax(im)
    span = im_max - im_min
    if span == 0:
        return np.zeros_like(im)
    return (im - im_min) / span


def noisy_bit_dithering(im, depth=256):
    """
    Implement noisy-bit dithering from Allard & Faubert (2008).

    Parameters
    ----------
    im : ndarray
        Input image matrix with values expected in [0, 1].
    depth : int
        Number of display levels (default 256).
    """
    tim = im * (depth - 1.0)
    tim = np.uint8(
        np.fmax(
            np.fmin(np.around(tim + np.random.random(np.shape(im)) - 0.5), depth - 1.0),
            0.0,
        )
    )
    return tim


def make_wiggles_sine(nx, frequency_min, frequency_max, radial_frequency, radial_phase, phase):
    """Create a square "wiggles" image with values in [0, 1]."""
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    angles = np.arctan2((yv - 0.5), (xv - 0.5))
    modulation_freq = (frequency_max - frequency_min) * (
        np.sin(radial_frequency * angles + radial_phase) / 2 + 0.5
    ) + frequency_min
    radii = np.sqrt((xv - 0.5) ** 2 + (yv - 0.5) ** 2)
    return np.sin(modulation_freq * 2 * np.pi * radii + phase) / 2 + 0.5


def make_concentric_sine_circles(nx, frequency, phase):
    """Create concentric sine circles with values in [0, 1]."""
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    radii = np.sqrt((xv - 0.5) ** 2 + (yv - 0.5) ** 2)
    return np.sin(frequency * 2 * np.pi * radii + phase) / 2 + 0.5


def make_sine_sectors(nx, frequency, phase):
    """Create angular sine sectors with values in [0, 1]."""
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    angles = np.arctan2((yv - 0.5), (xv - 0.5))
    return np.sin(frequency * angles + phase) / 2 + 0.5


def make_checkerboard(num_pixels_per_cell, n_rows, n_cols):
    """Create a checkerboard image made of repeated 2x2 checkerboard tiles."""
    tile = make_checkerboard_tile(num_pixels_per_cell)
    board = np.zeros((2 * n_rows * num_pixels_per_cell, 2 * n_cols * num_pixels_per_cell))
    for xx in np.arange(n_rows):
        for yy in np.arange(n_cols):
            board[
                xx * 2 * num_pixels_per_cell:(xx + 1) * 2 * num_pixels_per_cell:1,
                yy * 2 * num_pixels_per_cell:(yy + 1) * 2 * num_pixels_per_cell:1,
            ] = tile
    return board


def make_checkerboard_tile(num_pixels_per_cell):
    """Create a 2x2 checkerboard tile."""
    tile = np.zeros((2 * num_pixels_per_cell, 2 * num_pixels_per_cell))
    tile[0:num_pixels_per_cell:1, 0:num_pixels_per_cell:1] = np.ones((num_pixels_per_cell, num_pixels_per_cell))
    tile[
        num_pixels_per_cell:2 * num_pixels_per_cell:1,
        num_pixels_per_cell:2 * num_pixels_per_cell:1,
    ] = np.ones((num_pixels_per_cell, num_pixels_per_cell))
    return tile


def location_bubbles(nb_bubbles=50, std_bubble=25, an_image=None, x_size=None, y_size=None, random_state=None):
    """
    Generate a bubbles mask and optionally apply it to an image.

    Parameters
    ----------
    nb_bubbles : int
        Expected number of bubbles.
    std_bubble : float
        Standard deviation of each bubble in pixels.
    an_image : ndarray, optional
        Optional image with values in [0, 1].
    x_size, y_size : int, optional
        Image dimensions when `an_image` is not provided.
    random_state : tuple, optional
        Numpy random state as returned by `np.random.get_state()`.
    """
    if random_state is not None:
        np.random.set_state(random_state)
    else:
        raise ValueError("Must provide a pseudo-random generator state.")

    if x_size is None and y_size is None and an_image is not None:
        y_size, x_size = an_image.shape[:2]

    if x_size is None or y_size is None:
        raise ValueError("Either x_size and y_size must be specified, or an_image must be provided.")

    n_zero = 5
    max_half_size = round(std_bubble * n_zero)
    temp_rand = np.random.rand(y_size + 2 * max_half_size, x_size + 2 * max_half_size)
    the_noise = temp_rand <= (
        nb_bubbles / ((x_size + 2 * max_half_size) * (y_size + 2 * max_half_size))
    )

    if an_image is None:
        return the_noise

    y, x = np.meshgrid(
        np.arange(-max_half_size, max_half_size + 1),
        np.arange(-max_half_size, max_half_size + 1),
    )
    gauss = np.exp(-(x ** 2 / std_bubble ** 2 + y ** 2 / std_bubble ** 2))
    gauss /= np.max(gauss)

    f_the_noise = np.fft.fft2(the_noise.astype(float), s=(y_size + 4 * max_half_size, x_size + 4 * max_half_size))
    f_padded_gauss = np.fft.fft2(gauss, s=(y_size + 4 * max_half_size, x_size + 4 * max_half_size))
    temp_plane = np.fft.ifft2(f_the_noise * f_padded_gauss).real

    win_plane = np.minimum(
        temp_plane[max_half_size:y_size + max_half_size, max_half_size:x_size + max_half_size],
        1,
    )

    if len(an_image.shape) == 3:
        win_plane = np.stack((win_plane,) * 3, axis=-1)

    stimulus = win_plane / 2 * (an_image - 0.5) + 0.5
    return the_noise, stimulus


# Backward-compatible French wrappers.
def fabriquer_grille_sin(nx, frequence, phase, angle):
    _warn_legacy_name("fabriquer_grille_sin", "make_sine_grating")
    return make_sine_grating(nx, frequence, phase, angle)


def fabriquer_enveloppe_gaussienne(nx, ecart_type):
    _warn_legacy_name("fabriquer_enveloppe_gaussienne", "make_gaussian_envelope")
    return make_gaussian_envelope(nx, ecart_type)


def fabriquer_gabor(nx, frequence, phase, angle, ecart_type):
    _warn_legacy_name("fabriquer_gabor", "make_gabor")
    return make_gabor(nx, frequence, phase, angle, ecart_type)


def stretch(im):
    _warn_legacy_name("stretch", "normalize_to_unit_interval")
    return normalize_to_unit_interval(im)


def fabriquer_wiggles_sin(nx, frequence_min, frequence_max, frequence_radiale, phase_radiale, phase):
    _warn_legacy_name("fabriquer_wiggles_sin", "make_wiggles_sine")
    return make_wiggles_sine(nx, frequence_min, frequence_max, frequence_radiale, phase_radiale, phase)


def fabriquer_cercles_sin(nx, frequence, phase):
    _warn_legacy_name("fabriquer_cercles_sin", "make_concentric_sine_circles")
    return make_concentric_sine_circles(nx, frequence, phase)


def fabriquer_secteurs_sin(nx, frequence, phase):
    _warn_legacy_name("fabriquer_secteurs_sin", "make_sine_sectors")
    return make_sine_sectors(nx, frequence, phase)


def fabriquer_grand_damier(une_case, M, N):
    _warn_legacy_name("fabriquer_grand_damier", "make_checkerboard")
    return make_checkerboard(une_case, M, N)


def fabriquer_petit_damier(une_case):
    _warn_legacy_name("fabriquer_petit_damier", "make_checkerboard_tile")
    return make_checkerboard_tile(une_case)
