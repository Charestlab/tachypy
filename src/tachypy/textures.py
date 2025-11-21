# textures.py
import numpy as np
from OpenGL.GL import *


class Texture:
    def __init__(self, image, a_rect=None):
        """
        image : np.ndarray (H, W, 3), uint8
        a_rect : [x1, y1, x2, y2] ou [[x1, y1], [x2, y2]] (optionnel)
                 Si None, on met un rect par défaut basé sur la taille de l'image.
        """
        self.texture_id = glGenTextures(1)
        self.load_texture(image)

        if a_rect is None:
            # Par défaut: un rectangle de la taille de l'image, à l'origine
            h, w = image.shape[0], image.shape[1]
            self.rect = np.array([0.0, 0.0, float(w), float(h)], dtype=np.float32)
        else:
            self.set_rect(a_rect)

    # ---------- Gestion de la texture GPU ----------

    def load_texture(self, image):
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            image.shape[1],
            image.shape[0],
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            image
        )
        
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

    def bind(self):
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glEnable(GL_TEXTURE_2D)

    def unbind(self):
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        # Reset the modelview matrix to avoid any transformations being carried over
        glLoadIdentity()

    def delete(self):
        glDeleteTextures([self.texture_id])

    # ---------- Gestion du rect / position ----------

    def set_rect(self, a_rect):
        """
        a_rect: [x1, y1, x2, y2] ou [[x1, y1], [x2, y2]]
        """
        a_rect = np.asarray(a_rect, dtype=np.float32)

        if a_rect.shape == (4,):
            x1, y1, x2, y2 = a_rect
        elif a_rect.shape == (2, 2):
            (x1, y1), (x2, y2) = a_rect
        else:
            raise ValueError("A rectangle is defined either as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].")

        if x2 <= x1 or y2 <= y1:
            raise ValueError("x2 must be > x1 and y2 must be > y1.")

        self.rect = np.array([x1, y1, x2, y2], dtype=np.float32)

    def move_by(self, dx, dy):
        """
        Translate the rectangle by (dx, dy).
        """
        self.rect[0] += dx
        self.rect[1] += dy
        self.rect[2] += dx
        self.rect[3] += dy

    def hit_test(self, x, y):
        """
        Return True if (x, y) is inside the current rect.
        """
        x1, y1, x2, y2 = self.rect
        return (x1 <= x <= x2) and (y1 <= y <= y2)
    
    def get_bounds(self):
        x1, y1, x2, y2 = self.rect
        return float(x1), float(y1), float(x2), float(y2)

    # ---------- Dessin ----------

    def draw(self, a_rect=None):
        """
        Draw the texture on the screen.

        Parameters:
            a_rect: optionnel. Si fourni, met à jour temporairement la position.
                    Si None, utilise self.rect.
        """
        if a_rect is not None:
            # Met à jour la position stockée
            self.set_rect(a_rect)

        x1, y1, x2, y2 = self.rect

        # Enable texturing modulations        
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)

        # Open all colour channels.
        glColor3f(1.0, 1.0, 1.0)

        # bind the texture to be drawn       
        self.bind()
        
        # map the texture to the rectangle
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x1, y1)  # left - top
        glTexCoord2f(1, 0); glVertex2f(x2, y1)  # right - top
        glTexCoord2f(1, 1); glVertex2f(x2, y2)  # right - bottom
        glTexCoord2f(0, 1); glVertex2f(x1, y2)  # left - bottom
        glEnd()
        
        # unbind the texture
        self.unbind()