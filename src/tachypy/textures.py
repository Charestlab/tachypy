# textures.py
import numpy as np
from OpenGL.GL import *


class Texture:
    def __init__(self, image):
        self.texture_id = glGenTextures(1)
        self.load_texture(image)
    
    def load_texture(self, image):
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, image.shape[1], image.shape[0], 0, GL_RGB, GL_UNSIGNED_BYTE, image)
        
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
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

    def draw(self, a_rect):
        """
        Draw a texture on the screen.
        Parameters:
            texture_id: The ID of the texture to draw.
            a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, xy], [x2, y2]].
        """

        a_rect = np.asarray(a_rect)
        if a_rect.shape[0]==4:
            x1, y1, x2, y2 = np.asarray(a_rect)
        elif a_rect.shape[0]==2 & a_rect.shape[1]==2:
            x1, y1 = a_rect[0]
            x2, y2 = a_rect[1]
        else:
            raise ValueError("A rectangle is defined either as [x1, y1, x2, y2] or [[x1, xy], [x2, y2]].")

        if x2<=x1 or y2<=y1:
            raise ValueError("x2 must be equal or smaller than x1 an y2 must be equal or smaller than y1.")

        # Open all colour channels.
        glColor3f(1.0, 1.0, 1.0)

        # bind the texture to be drawn       
        self.bind()
        
        # map the texture to the rectangle
        glBegin(GL_QUADS)
        # Compute centered vertex positions
        glTexCoord2f(0, 0); glVertex2f(x1, y1) # left - top
        glTexCoord2f(1, 0); glVertex2f(x2, y1) # right - top
        glTexCoord2f(1, 1); glVertex2f(x2, y2) # right - bottom
        glTexCoord2f(0, 1); glVertex2f(x1, y2) # left - bottom
        glEnd()
        
        # unbind the texture
        self.unbind()


