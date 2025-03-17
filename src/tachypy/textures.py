# textures.py
import numpy as np
from OpenGL.GL import *
from OpenGL.error import GLError
import ctypes
import sys

def check_gl_context():
    """Check if OpenGL context is initialized"""
    try:
        if sys.platform == 'darwin':  # macOS
            # On macOS, we can check if OpenGL is initialized by trying to get the current context
            from OpenGL.platform import ctypesloader
            CGL = ctypesloader.loadLibrary(ctypes.CDLL, 'OpenGL.framework/OpenGL')
            context = CGL.CGLGetCurrentContext()
            if context is None:
                print("\nERROR: No OpenGL context found!")
                print("This usually means you haven't initialized a screen yet.")
                print("Make sure to create a Screen object before creating textures:")
                print("\nExample:")
                print("from tachypy import Screen")
                print("screen = Screen()  # Initialize screen first")
                print("texture = Texture(image)  # Then create textures")
                print("\n")
            return context is not None
        elif sys.platform == 'win32':  # Windows
            context = ctypes.windll.opengl32.wglGetCurrentContext()
            if context is None:
                print("\nERROR: No OpenGL context found!")
                print("This usually means you haven't initialized a screen yet.")
                print("Make sure to create a Screen object before creating textures:")
                print("\nExample:")
                print("from tachypy import Screen")
                print("screen = Screen()  # Initialize screen first")
                print("texture = Texture(image)  # Then create textures")
                print("\n")
            return context is not None
        else:  # Linux
            context = ctypes.CDLL('libGL.so').glXGetCurrentContext()
            if context is None:
                print("\nERROR: No OpenGL context found!")
                print("This usually means you haven't initialized a screen yet.")
                print("Make sure to create a Screen object before creating textures:")
                print("\nExample:")
                print("from tachypy import Screen")
                print("screen = Screen()  # Initialize screen first")
                print("texture = Texture(image)  # Then create textures")
                print("\n")
            return context is not None
    except Exception as e:
        print(f"\nERROR: Failed to check OpenGL context: {str(e)}")
        print("This usually means you haven't initialized a screen yet.")
        print("Make sure to create a Screen object before creating textures:")
        print("\nExample:")
        print("from tachypy import Screen")
        print("screen = Screen()  # Initialize screen first")
        print("texture = Texture(image)  # Then create textures")
        print("\n")
        return False

def check_gl_error():
    """Check for OpenGL errors and print them"""
    try:
        error = glGetError()
        if error != GL_NO_ERROR:
            print(f"OpenGL Error: {error}")
            return True
        return False
    except Exception as e:
        print(f"Failed to check OpenGL error: {str(e)}")
        return True

class Texture:
    def __init__(self, image):
        """
        Initialize a texture from a numpy array.
        The image array should be in format (height, width, channels) or (channels, height, width)
        """
        print("Texture.__init__: Starting texture initialization")
        
        # Check if OpenGL context is initialized
        if not check_gl_context():
            raise RuntimeError("No OpenGL context found. Please initialize a Screen before creating textures.")
        
        # Check OpenGL state
        print("Texture.__init__: Checking OpenGL state")
        if check_gl_error():
            print("Texture.__init__: OpenGL error detected before texture creation")
        
        try:
            # Generate texture ID
            print("Texture.__init__: Generating texture ID")
            self.texture_id = glGenTextures(1)
            if check_gl_error():
                print("Texture.__init__: Error generating texture ID")
                raise GLError("Failed to generate texture ID")
            print(f"Texture.__init__: Generated texture ID: {self.texture_id}")
            
            # Load texture
            print("Texture.__init__: Loading texture")
            self.load_texture(image)
            print("Texture.__init__: Texture initialization complete")
            
        except Exception as e:
            print(f"Texture.__init__: Error during initialization: {str(e)}")
            if hasattr(self, 'texture_id'):
                try:
                    glDeleteTextures([self.texture_id])
                except:
                    pass
            raise
    
    def load_texture(self, image):
        """
        Load a texture from a numpy array.
        Handles both (height, width, channels) and (channels, height, width) formats.
        """
        print("Texture.load_texture: Starting texture loading")
        
        # Ensure image is a numpy array
        print("Texture.load_texture: Converting to numpy array")
        image = np.asarray(image, dtype=np.uint8)
        print(f"Texture.load_texture: Array shape: {image.shape}, dtype: {image.dtype}")
        
        # Check array dimensions
        if len(image.shape) != 3:
            raise ValueError(f"Image array must have 3 dimensions, got {len(image.shape)}")
        
        # Get dimensions
        print("Texture.load_texture: Processing array dimensions")
        if image.shape[2] == 3:  # (height, width, channels) format
            height, width, channels = image.shape
            print(f"Texture.load_texture: Converting from (height, width, channels) format: {image.shape}")
            # Convert to (channels, height, width) format
            image = np.transpose(image, (2, 0, 1))
            print(f"Texture.load_texture: Converted shape: {image.shape}")
        elif image.shape[0] == 3:  # (channels, height, width) format
            channels, height, width = image.shape
            print(f"Texture.load_texture: Using (channels, height, width) format: {image.shape}")
        else:
            raise ValueError(f"Invalid image format. Expected 3 channels, got shape {image.shape}")
        
        # Ensure the array is contiguous in memory
        print("Texture.load_texture: Checking memory contiguity")
        if not image.flags['C_CONTIGUOUS']:
            print("Texture.load_texture: Converting to contiguous array")
            image = np.ascontiguousarray(image)
        
        # Bind texture
        print("Texture.load_texture: Binding texture")
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        if check_gl_error():
            print("Texture.load_texture: Error binding texture")
            raise GLError("Failed to bind texture")
        
        # Set pixel storage mode
        print("Texture.load_texture: Setting pixel storage mode")
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        if check_gl_error():
            print("Texture.load_texture: Error setting pixel storage mode")
            raise GLError("Failed to set pixel storage mode")
        
        # Load texture data
        print(f"Texture.load_texture: Loading texture data with dimensions {width}x{height}")
        try:
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_UNSIGNED_BYTE, image)
            if check_gl_error():
                print("Texture.load_texture: Error loading texture data")
                raise GLError("Failed to load texture data")
            print("Texture.load_texture: Successfully loaded texture data")
        except Exception as e:
            print(f"Texture.load_texture: Error loading texture data: {str(e)}")
            raise
        
        # Set texture parameters
        print("Texture.load_texture: Setting texture parameters")
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        if check_gl_error():
            print("Texture.load_texture: Error setting texture parameters")
            raise GLError("Failed to set texture parameters")
        
        # Unbind texture
        print("Texture.load_texture: Unbinding texture")
        glBindTexture(GL_TEXTURE_2D, 0)
        if check_gl_error():
            print("Texture.load_texture: Error unbinding texture")
            raise GLError("Failed to unbind texture")
        print("Texture.load_texture: Texture loading complete")

    def bind(self):
        print("Texture.bind: Binding texture")
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glEnable(GL_TEXTURE_2D)
        if check_gl_error():
            print("Texture.bind: Error binding texture")
            raise GLError("Failed to bind texture")
        print("Texture.bind: Texture bound and enabled")

    def unbind(self):
        print("Texture.unbind: Unbinding texture")
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        # Reset the modelview matrix to avoid any transformations being carried over
        glLoadIdentity()
        if check_gl_error():
            print("Texture.unbind: Error unbinding texture")
            raise GLError("Failed to unbind texture")
        print("Texture.unbind: Texture unbound and matrix reset")

    def delete(self):
        print("Texture.delete: Deleting texture")
        glDeleteTextures([self.texture_id])
        if check_gl_error():
            print("Texture.delete: Error deleting texture")
            raise GLError("Failed to delete texture")
        print("Texture.delete: Texture deleted")

    def draw(self, a_rect):
        """
        Draw a texture on the screen.
        Parameters:
            a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, xy], [x2, y2]].
        """
        print("Texture.draw: Starting texture drawing")
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

        print(f"Texture.draw: Drawing texture to rectangle ({x1}, {y1}) -> ({x2}, {y2})")
        
        # Enable texturing modulations        
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        if check_gl_error():
            print("Texture.draw: Error setting texture environment")
            raise GLError("Failed to set texture environment")

        # Open all colour channels.
        glColor3f(1.0, 1.0, 1.0)
        if check_gl_error():
            print("Texture.draw: Error setting color")
            raise GLError("Failed to set color")

        # bind the texture to be drawn       
        self.bind()
        
        # map the texture to the rectangle
        print("Texture.draw: Drawing quad")
        glBegin(GL_QUADS)
        # Compute centered vertex positions
        glTexCoord2f(0, 0); glVertex2f(x1, y1)  # left - top
        glTexCoord2f(1, 0); glVertex2f(x2, y1)  # right - top
        glTexCoord2f(1, 1); glVertex2f(x2, y2)  # right - bottom
        glTexCoord2f(0, 1); glVertex2f(x1, y2)  # left - bottom
        glEnd()
        if check_gl_error():
            print("Texture.draw: Error drawing quad")
            raise GLError("Failed to draw quad")
        
        # unbind the texture
        self.unbind()
        print("Texture.draw: Drawing complete")


