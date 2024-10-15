import numpy as np
  
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