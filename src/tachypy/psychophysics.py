import numpy as np
import random
  
def fabriquer_grille_sin(nx, frequence, phase, angle):
    # fabriquer_grille_sin permet de fabriquer l'image carrée d'une grille sinusoïdale variant entre 0 et 1.
    # La fontion admet 4 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     frequence: spécifie la fréquence de la grille sinusoïdale en cycles par largeur d'image
    #     phase: spécifie la phase de la grille sinusoïdale en radians
    #     angle: spécifie l'orientation de la grille sinusoïdale en radians
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    rampe = (np.cos(angle) * xv + np.sin(angle) * yv)
    grille_sin = np.sin(frequence * 2 * np.pi * rampe + phase) / 2 + 0.5
    return grille_sin


def fabriquer_enveloppe_gaussienne(nx, ecart_type):
    # fabriquer_enveloppe_gaussienne permet de fabriquer l'image carrée d'une enveloppe gaussienne centrale variant entre 0 et 1.
    # La fontion admet 2 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     ecart_type: spécifie l'écart-type de la gaussienne 2D en largeur d'image
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    gaussienne = np.exp(-((xv - 0.5) ** 2 / ecart_type ** 2) - ((yv - 0.5) ** 2 / ecart_type ** 2))
    return gaussienne


def fabriquer_gabor(nx, frequence, phase, angle, ecart_type):
    # fabriquer_gabor permet de fabriquer une tache de gabor variant entre 0 et 1
    # La fontion admet 5 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     frequence: spécifie la fréquence de la grille sinusoïdale en cycles par largeur d'image
    #     phase: spécifie la phase de la grille sinusoïdale en radians
    #     angle: spécifie l'orientation de la grille sinusoïdale en radians
    #     ecart_type: spécifie l'écart-type de la gaussienne 2D en largeur d'image
    gaussienne = fabriquer_enveloppe_gaussienne(nx, ecart_type)
    grille_sin = fabriquer_grille_sin(nx, frequence, phase, angle)
    gabor = gaussienne * (grille_sin - 0.5) + 0.5
    return gabor


def stretch(im):

  tim = (im - np.amin(im)) / (np.amax(im) - np.amin(im))
  return tim


def noisy_bit_dithering(im, depth = 256):
    # Implements the dithering algorithm presented in:
    # Allard, R., Faubert, J. (2008) The noisy-bit method for digital displays:
    # converting a 256 luminance resolution into a continuous resolution. Behavior 
    # Research Method, 40(3), 735-743.
    # It takes 2 arguments:
    #   im: is an image matrix in float64 that varies between 0 and 1, 
    #   depth: is the number of evenly separated luminance values at your disposal. 
    #     Default is 256 (1 byte).
    # It returns:
    #   tim: a matrix containg integer values between 1 and depth, indicating which 
    #     luminance value should be used for every pixel. 
    #
    # E.g.:
    #   tim = noisy_bit_dithering(im, depth = 256)
    #
    # This example assumes that all rgb values are linearly related to luminance 
    # values (e.g. on a Mac, put your LCD monitor gamma parameter to 1 in the Displays 
    # section of the System Preferences). If this is not the case, use a lookup table 
    # to transform the tim integer values into rgb values corresponding to evenly 
    # spaced luminance values.
    #
    # Frederic Gosselin, 27/09/2022
    # frederic.gosselin@umontreal.ca
        tim = im * (depth - 1.0)
        tim = np.uint8(np.fmax(np.fmin(np.around(tim + np.random.random(np.shape(im)) - 0.5), depth - 1.0), 0.0))
        return tim


def fabriquer_wiggles_sin(nx, frequence_min, frequence_max, frequence_radiale, phase_radiale, phase):
    # fabriquer_wiggles_sin permet de fabriquer l'image carrée de "wiggles", les stimuli inventés par Frances Wilkinson, variant entre 0 et 1.
    # La fontion admet 6 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     frequence_radiale: spécifie le nombre de bosses et de creux par 2*pi radians
    #     phase_radiale: spécifie la phase angulaire des creux et des bossses en radians
    #     frequence_min: spécifie la fréquence des bosses concentriques par largeur d'image
    #     frequence_max: spécifie la fréquence des creux concentriques par largeur d'image
    #     phase: spécifie la phase des bosses et des creux concentriques en radians
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    angles = np.arctan2((yv - 0.5), (xv - 0.5))
    modulation_freq = (frequence_max - frequence_min) * (np.sin(frequence_radiale * angles + phase_radiale) / 2 + 0.5) + frequence_min
    rayons = np.sqrt((xv - 0.5) ** 2 + (yv - 0.5) ** 2)
    wiggles_sin = np.sin(modulation_freq * 2 * np.pi * rayons + phase) / 2 + 0.5
    return wiggles_sin


def fabriquer_cercles_sin(nx, frequence, phase):
    # fabriquer_cercles_sin permet de fabriquer l'image carrée de cercles concentriques sinusoïdaux variant entre 0 et 1.
    # La fontion admet 3 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     frequence: spécifie la fréquence des cercles sinusoïdaux en cycles par largeur d'image
    #     phase: spécifie la phase des cercles sinusoïdaux en radians
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    rayons = np.sqrt((xv - 0.5) ** 2 + (yv - 0.5) ** 2)
    cercles_sin = np.sin(frequence * 2 * np.pi * rayons + phase) / 2 + 0.5;
    return cercles_sin


def fabriquer_secteurs_sin(nx, frequence, phase):
    # fabriquer_secteurs_sin permet de fabriquer l'image carrée de secteurs sinusoïdaux variant entre 0 et 1.
    # La fontion admet 3 variables:
    #     nx: spécifie la largeur et la hauter de l'image
    #     frequence: spécifie la fréquence des secteurs sinusoïdaux en cycles par 2*pi
    #     phase: spécifie la phase des secteurs sinusoïdaux en radians
    x = np.linspace(0, 1, nx)
    xv, yv = np.meshgrid(x, x)
    angles = np.arctan2((yv - 0.5), (xv - 0.5))
    secteurs_sin = np.sin(frequence * angles + phase) / 2 + 0.5
    return secteurs_sin


def fabriquer_grand_damier(une_case, M, N):
    petit_damier = fabriquer_petit_damier(une_case)
    grand_damier = np.zeros((2*M*une_case, 2*N*une_case))
    for xx in np.arange(M):
        for yy in np.arange(N):
            grand_damier[xx*2*une_case:(xx+1)*2*une_case:1, yy*2*une_case:(yy+1)*2*une_case:1] = petit_damier
    return grand_damier



def fabriquer_petit_damier(une_case):
    petit_damier = np.zeros((2*une_case, 2*une_case))
    petit_damier[0:une_case:1,0:une_case:1] = np.ones((une_case, une_case))
    petit_damier[une_case:2*une_case:1,une_case:2*une_case:1] = np.ones((une_case, une_case))
    return petit_damier


def location_bubbles(nb_bubbles=50, std_bubble=25, an_image=None, x_size=None, y_size=None, random_state=None):
    """
    Generates a noisy spatial mask (referred to as a 'bubbles mask') and applies it to an image, 
    as first done in Gosselin and Schyns (2001, Vision Research, Experiment 1). This function 
    is used both to generate stimuli for an experiment and the bubbles masks for a classification 
    image analysis afterward.

    Parameters:
    nb_bubbles : int, optional
        The expected number of bubbles (sampled areas). The exact number of bubbles varies from 
        trial to trial to ensure spatial independence of the bubbles. Default is 50.
    std_bubble : float, optional
        The standard deviation of each Gaussian filter (bubble) in pixels. Each bubble modulates 
        the contrast from 0 at the edges to 1 at the center. Default is 25.
    an_image : ndarray, optional
        The image to which the bubbles will be applied. This image can be grayscale (x_size x y_size) 
        or color (x_size x y_size x 3), and its values must range between 0 and 1. Must be provided if 
        x_size or y_size are not.
    x_size : int, optional
        The width of the image. Either x_size and y_size or an_image must be provided.
    y_size : int, optional
        The height of the image. Either x_size and y_size or an_image must be provided.
    random_state : random.RandomState object, optional
        A random state object to control reproducibility. Must be provided.

    Returns:
    tuple:
        If an_image is not provided:
            - the_noise: ndarray
                A (x_size + 2*std_bubble*5 by y_size + 2*std_bubble*5) binary array representing 
                the centers of the bubbles. It is larger than the image to ensure homogeneous sampling, 
                including at the image's borders.
        If an_image is provided:
            - the_noise: ndarray
                A (x_size + 2*std_bubble*n_zero by y_size + 2*std_bubble*n_zeros, with n_zero equal to 5) 
                binary array representing the centers of the bubbles. It is larger than the image to ensure 
                homogeneous sampling, including at the image's borders. 
            - stimulus: ndarray
                The resulting stimulus after applying the bubbles mask to the original image. Where the 
                bubbles do not sample the image, the stimulus appears mid-gray (value of 0.5).

    Raises:
    ValueError:
        If neither an image nor x_size and y_size are provided, or if random_state is not provided.

    Example:
        a_seed = 0
        np.random.seed(a_seed)
        x_size = 256
        y_size = 200
        an_image = np.random.random((y_size, x_size)) # grayscale image with values between 0 and 1        
        nb_bubbles = 100
        std_bubble = 15
        random_state = np.random.get_state()
        the_noise, stimulus = location_noise(nb_bubbles=nb_bubbles, std_bubble=std_bubble, an_image=an_image, x_size=None, y_size=None, random_state=random_state) # with an image
        #the_noise = location_noise(nb_bubbles=nb_bubbles, std_bubble=std_bubble, an_image=None, x_size=an_image.shape[0], y_size=an_image.shape[1], random_state=random_state) # with coordinates

    History:
        Written by Frederic Gosselin, October 17 2024
    """

    # Set the random state for reproducibility
    if random_state is not None:
        #random.setstate(random_state)
        np.random.set_state(random_state)
    else:
        raise ValueError("Must provide a pseudo-random generator state.")

    # Determine the size of the image (x_size, y_size) from the provided image if not explicitly provided
    if x_size is None and y_size is None and an_image is not None:
        y_size, x_size = an_image.shape[:2]  # Use the shape of the image

    # Raise an error if no valid size information is available
    if x_size is None or y_size is None:
        raise ValueError("Either x_size and y_size must be specified, or an_image must be provided.")
    
    # Generate probabilistic placement of bubbles over an extended area (to handle image borders)
    n_zero = 5  # Number of standard deviations to use for the bubble size
    max_half_size = round(std_bubble * n_zero)  # Maximum size (half-width) for the Gaussian bubble
    #temp_rand = np.asarray([[random.uniform(0, 1) for _ in range(x_size + 2*max_half_size)] for _ in range(y_size + 2*max_half_size)]) # Noise over extended area
    temp_rand = np.random.rand(y_size + 2*max_half_size, x_size + 2*max_half_size)
    the_noise = (temp_rand <= (nb_bubbles / ((x_size+2*max_half_size) * (y_size+2*max_half_size))))  # Binary mask

    # If no image is provided, return just the noise mask and the current random state
    if an_image is None:
        #return the_noise, random.getstate()
        return the_noise
    
    else:
        # Create a 2D Gaussian kernel to simulate bubble spread (blur effect)
        y, x = np.meshgrid(np.arange(-max_half_size, max_half_size + 1), np.arange(-max_half_size, max_half_size + 1))
        gauss = np.exp(-(x**2 / std_bubble**2 + y**2 / std_bubble**2))  # Gaussian equation
        gauss /= np.max(gauss)  # Normalize Gaussian kernel

        # Apply convolution using FFT (efficient for large arrays)
        f_the_noise = np.fft.fft2(the_noise.astype(float), s=(y_size + 4*max_half_size, x_size + 4*max_half_size))  # FFT of noise
        f_padded_gauss = np.fft.fft2(gauss, s=(y_size + 4*max_half_size, x_size + 4*max_half_size))  # FFT of Gaussian
        temp_plane = np.fft.ifft2(f_the_noise * f_padded_gauss).real  # Inverse FFT to apply Gaussian blur

        # Extract the valid region of the resulting plane after convolution
        win_plane = np.minimum(temp_plane[max_half_size:y_size + max_half_size, max_half_size:x_size + max_half_size], 1)

        # Handle color images by applying the noise plane to each channel
        if len(an_image.shape) == 3:
            win_plane = np.stack((win_plane,) * 3, axis=-1)  # Stack the plane for RGB channels

        # Combine the noise mask with the original image to generate the final stimulus
        stimulus = win_plane / 2 * (an_image - 0.5) + 0.5  # Blend noise mask with image

        # Return the noise mask, the final stimulus, and the current random state
        return the_noise, stimulus
