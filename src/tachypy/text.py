import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *


class Text:
    def __init__(self, text, position, font, font_size, color=(0, 0, 0)):
        """
        Initialize the Text object.

        Parameters:
            text: The text string to render.
            position: Tuple (x, y) specifying the position.
            font: Pygame font object.
            color: Color of the text as an RGB tuple.
        """
        pygame.font.init()
        self.font = pygame.font.SysFont(font, font_size)
        self.text = text
        self.position = position
        self.color = color
        self.texture_id = None
        self.width = 0
        self.height = 0
        self.update_texture()

    def update_texture(self):
        # Render the text onto a Pygame surface
        text_surface = self.font.render(self.text, True, self.color)
        self.width, self.height = text_surface.get_size()
        # Convert the surface to a string buffer
        text_data = pygame.image.tostring(text_surface, "RGBA", True)
        # Generate a texture ID if not already done
        if self.texture_id is None:
            self.texture_id = glGenTextures(1)
        # Bind the texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        # Upload the texture data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        # Set texture parameters
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # Unbind the texture
        glBindTexture(GL_TEXTURE_2D, 0)

    def draw(self):
        # Enable blending for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Bind the texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glEnable(GL_TEXTURE_2D)
        glColor3f(1.0, 1.0, 1.0)
        x, y = self.position
        # Adjust for texture size to center the text
        x1 = x - self.width / 2
        y1 = y - self.height / 2
        x2 = x + self.width / 2
        y2 = y + self.height / 2
        # Draw textured quad
        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x1, y1)
        glTexCoord2f(1, 1); glVertex2f(x2, y1)
        glTexCoord2f(1, 0); glVertex2f(x2, y2)
        glTexCoord2f(0, 0); glVertex2f(x1, y2)
        glEnd()
        # Disable textures and blending
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_BLEND)