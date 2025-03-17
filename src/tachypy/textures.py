# textures.py
import numpy as np
from OpenGL.GL import *


class Texture:
    def __init__(self, image):
        """
        Initialize a texture from a numpy array.
        The image array should be in format (height, width, channels) or (channels, height, width)
        """
        self.texture_id = glGenTextures(1)
        self.load_texture(image)
    
    def load_texture(self, image):
        """
        Load a texture from a numpy array.
        Handles both (height, width, channels) and (channels, height, width) formats.
        """
        # Ensure image is a numpy array
        image = np.asarray(image, dtype=np.uint8)
        
        # Check array dimensions
        if len(image.shape) != 3:
            raise ValueError(f"Image array must have 3 dimensions, got {len(image.shape)}")
        
        # Get dimensions
        if image.shape[2] == 3:  # (height, width, channels) format
            height, width, channels = image.shape
            # Convert to (channels, height, width) format
            image = np.transpose(image, (2, 0, 1))
        elif image.shape[0] == 3:  # (channels, height, width) format
            channels, height, width = image.shape
        else:
            raise ValueError(f"Invalid image format. Expected 3 channels, got shape {image.shape}")
        
        # Ensure the array is contiguous in memory
        if not image.flags['C_CONTIGUOUS']:
            image = np.ascontiguousarray(image)
        
        # Bind texture
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        
        # Set pixel storage mode
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        
        # Load texture data
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, image)
        
        # Set texture parameters
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        
        # Unbind texture
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
            a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, xy], [x2, y2]].
        """
        a_rect = np.asarray(a_rect)
        if a_rect.shape[0] == 4:
            x1, y1, x2, y2 = np.asarray(a_rect)
        elif a_rect.shape[0] == 2 and a_rect.shape[1] == 2:
            x1, y1 = a_rect[0]
            x2, y2 = a_rect[1]
        else:
            raise ValueError("A rectangle is defined either as [x1, y1, x2, y2] or [[x1, xy], [x2, y2]].")

        if x2 <= x1 or y2 <= y1:
            raise ValueError("x2 must be equal or smaller than x1 and y2 must be equal or smaller than y1.")

        # Enable texturing modulations        
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)

        # Open all colour channels.
        glColor3f(1.0, 1.0, 1.0)

        # bind the texture to be drawn       
        self.bind()
        
        # map the texture to the rectangle
        glBegin(GL_QUADS)
        # Compute centered vertex positions
        glTexCoord2f(0, 0); glVertex2f(x1, y1)  # left - top
        glTexCoord2f(1, 0); glVertex2f(x2, y1)  # right - top
        glTexCoord2f(1, 1); glVertex2f(x2, y2)  # right - bottom
        glTexCoord2f(0, 1); glVertex2f(x1, y2)  # left - bottom
        glEnd()
        
        # unbind the texture
        self.unbind()


