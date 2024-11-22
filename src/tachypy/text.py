import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *


class Text:
    def __init__(self, text, font_name='Helvetica', font_size=24, color=(255, 255, 255), dest_rect=None, line_spacing=4):
        """
        Initialize the Text object.

        Parameters:
            text: 
                The text string to render.
            dest_rect : list or tuple
                A rectangle [x1, y1, x2, y2] defining the text bounding box. Optional.
            font_name: 
                the name of the font.
            font_size:
                The font size in points.
            color: 
                Color of the text as an RGB tuple.
            
        """
        pygame.font.init()
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.dest_rect = dest_rect
        self.texture_id = None
        self.surface = None
        self.line_spacing = line_spacing

        self.lines = []
        self._split_text_into_lines()
        self._generate_surface()

    def _split_text_into_lines(self):
        """Split the text into multiple lines that fit within the dest_rect width."""
        if not self.dest_rect:
            raise ValueError("dest_rect must be set to split text into lines.")

        font = pygame.font.SysFont(self.font_name, self.font_size)
        max_width = self.dest_rect[2] - self.dest_rect[0]  # Width of the rectangle

        words = self.text.split()
        line = ""
        self.lines = []
        for word in words:
            test_line = f"{line} {word}".strip()
            if font.size(test_line)[0] <= max_width:
                line = test_line
            else:
                self.lines.append(line)
                line = word
        if line:
            self.lines.append(line)

    def _generate_surface(self):
        """Generate a Pygame surface with the text rendered."""
        font = pygame.font.SysFont(self.font_name, self.font_size)

        line_surfaces = [font.render(line, True, self.color) for line in self.lines]
        max_width = max(surface.get_width() for surface in line_surfaces)
        total_height = sum(surface.get_height() for surface in line_surfaces) + (len(line_surfaces) - 1) * self.line_spacing

        # Create the surface with an appropriate size
        self.surface = pygame.Surface((max_width, total_height), pygame.SRCALPHA)
        self.surface.fill((0, 0, 0, 0))  # Transparent background

        # Draw each line on the surface
        y_offset = 0
        for surface in line_surfaces:
            self.surface.blit(surface, (0, y_offset))
            y_offset += surface.get_height() + self.line_spacing

        self._generate_texture()

    def _generate_texture(self):
        """Upload the Pygame surface as an OpenGL texture."""
        if self.texture_id:
            glDeleteTextures([self.texture_id])

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        surface_data = pygame.image.tostring(self.surface, "RGBA", True)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.surface.get_width(),
                     self.surface.get_height(), 0, GL_RGBA, GL_UNSIGNED_BYTE, surface_data)

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBindTexture(GL_TEXTURE_2D, 0)

    def draw(self):
        """
        Draw the text on the screen, centered within the dest_rect.
        """
        if not self.dest_rect:
            raise ValueError("dest_rect must be set to draw text.")

        x1, y1, x2, y2 = self.dest_rect
        rect_width = x2 - x1
        rect_height = y2 - y1

        # Center the text within the rectangle
        texture_width = self.surface.get_width()
        texture_height = self.surface.get_height()
        center_x = x1 + rect_width // 2
        center_y = y1 + rect_height // 2
        x_start = center_x - texture_width // 2
        y_start = center_y - texture_height // 2

        # Enable blending and set blend function for transparency
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Bind the texture and draw the quad
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)

        glBegin(GL_QUADS)
        glTexCoord2f(0, 1); glVertex2f(x_start, y_start)  # Top-left
        glTexCoord2f(1, 1); glVertex2f(x_start + texture_width, y_start)  # Top-right
        glTexCoord2f(1, 0); glVertex2f(x_start + texture_width, y_start + texture_height)  # Bottom-right
        glTexCoord2f(0, 0); glVertex2f(x_start, y_start + texture_height)  # Bottom-left
        glEnd()

        # Unbind texture and disable states
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)

    def set_text(self, new_text):
        """
        Update the text and regenerate the surface and texture.
        """
        self.text = new_text
        self._split_text_into_lines()
        self._generate_surface()

    def set_dest_rect(self, dest_rect):
        """
        Update the destination rectangle and regenerate the surface if needed.
        """
        self.dest_rect = dest_rect
        self._split_text_into_lines()
        self._generate_surface()
        



class TextBox:
    """
    A class to create an interactive text input box for user input.

    Attributes:
        position (tuple): The (x, y) position of the top-left corner of the text box.
        size (tuple): The (width, height) dimensions of the text box.
        font (pygame.font.Font): The font used for rendering text.
        text_color (tuple): RGB color of the input text.
        box_color (tuple): RGB color of the text box background.
        border_color (tuple): RGB color of the text box border.
        border_thickness (int): Thickness of the border in pixels.
        text (str): The current text input by the user.
        submitted (bool): Flag indicating whether the user has submitted the text.
        cursor_position (int): The position of the cursor within the text.
    """

    def __init__(self, position, size, font, text_color=(0, 0, 0),
                 box_color=(255, 255, 255), border_color=(0, 0, 0), border_thickness=2):
        """
        Initialize the TextBox object.

        Parameters:
            position (tuple): The (x, y) position of the top-left corner of the text box.
            size (tuple): The (width, height) dimensions of the text box.
            font (pygame.font.Font): The font used for rendering text.
            text_color (tuple): RGB color of the input text.
            box_color (tuple): RGB color of the text box background.
            border_color (tuple): RGB color of the text box border.
            border_thickness (int): Thickness of the border in pixels.
        """
        self.position = position
        self.size = size
        self.font = font
        self.text_color = text_color
        self.box_color = box_color
        self.border_color = border_color
        self.border_thickness = border_thickness

        self.text = ""  # Current text input by the user
        self.text_surface = None  # Surface for rendered text
        self.texture_id = None  # OpenGL texture ID
        self.width = self.size[0]  # Width of the texture (same as text box width)
        self.height = self.size[1]  # Height of the texture (same as text box height)
        self.cursor_visible = True  # Cursor visibility flag
        self.cursor_timer = 0  # Timer for cursor blinking
        self.cursor_switch_ms = 500  # Cursor blink interval in milliseconds
        self.submitted = False  # Flag to indicate submission

        self.padding = 5  # Padding inside the text box
        self.offset = 0  # Offset for scrolling text

        self.cursor_position = 0  # Cursor position within the text

        self.update_texture()  # Initial texture update

    def handle_event(self, event):
        """
        Handle Pygame events related to text input.

        Parameters:
            event (pygame.event.Event): A Pygame event object.
        """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                if self.cursor_position > 0:
                    # Remove character before the cursor
                    self.text = self.text[:self.cursor_position - 1] + self.text[self.cursor_position:]
                    self.cursor_position -= 1
                    self.update_texture()
            elif event.key == pygame.K_DELETE:
                if self.cursor_position < len(self.text):
                    # Remove character after the cursor
                    self.text = self.text[:self.cursor_position] + self.text[self.cursor_position + 1:]
                    self.update_texture()
            elif event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                # Enter key pressed; set submitted flag to True
                self.submitted = True
            elif event.key == pygame.K_LEFT:
                if self.cursor_position > 0:
                    self.cursor_position -= 1
                    self.update_texture()
            elif event.key == pygame.K_RIGHT:
                if self.cursor_position < len(self.text):
                    self.cursor_position += 1
                    self.update_texture()
            else:
                # Add the unicode character to the text if it's printable
                char = event.unicode
                if char.isprintable():
                    self.text = self.text[:self.cursor_position] + char + self.text[self.cursor_position:]
                    self.cursor_position += len(char)
                    self.update_texture()

    def update_texture(self):
        """
        Update the OpenGL texture with the current text.
        """
        # Render the text onto a surface
        self.text_surface = self.font.render(self.text, True, self.text_color)
        text_width, text_height = self.text_surface.get_size()

        # Create a surface with the size of the text box
        box_surface = pygame.Surface(self.size, pygame.SRCALPHA)

        # Calculate maximum width available for text
        max_text_width = self.size[0] - 2 * self.padding

        # Calculate the width of text up to the cursor position
        cursor_text = self.text[:self.cursor_position]
        cursor_width = self.font.size(cursor_text)[0]

        # Determine if text needs to be scrolled
        if cursor_width - self.offset > max_text_width:
            # Move offset to the right to keep cursor visible
            self.offset = cursor_width - max_text_width + 10  # Additional padding
        elif cursor_width - self.offset < 0:
            # Move offset to the left to keep cursor visible
            self.offset = cursor_width - 10  # Additional padding

        # Ensure offset is not negative
        if self.offset < 0:
            self.offset = 0

        # Blit the text onto the box surface with the calculated offset
        box_surface.blit(self.text_surface, (-self.offset + self.padding, (self.size[1] - text_height) / 2))

        # Update the texture
        self.width, self.height = box_surface.get_size()
        # Convert the surface to a string buffer for OpenGL
        text_data = pygame.image.tostring(box_surface, "RGBA", True)
        # Generate a texture ID if not already created
        if self.texture_id is None:
            self.texture_id = glGenTextures(1)
        # Bind the texture and upload the data
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.width, self.height,
                     0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
        # Set texture parameters for scaling
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        # Unbind the texture
        glBindTexture(GL_TEXTURE_2D, 0)

    def update(self, delta_time):
        """
        Update the text box, handling cursor blinking.

        Parameters:
            delta_time (float): Time elapsed since the last update in milliseconds.
        """
        # Update the cursor timer
        self.cursor_timer += delta_time
        if self.cursor_timer >= self.cursor_switch_ms:
            # Reset the timer and toggle cursor visibility
            self.cursor_timer %= self.cursor_switch_ms
            self.cursor_visible = not self.cursor_visible

    def draw(self):
        """
        Draw the text box, including the background, border, text, and cursor.
        """
        x, y = self.position
        width, height = self.size

        # Draw the text box background
        glColor3ub(*self.box_color)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()

        # Draw the border around the text box if border thickness is greater than zero
        if self.border_thickness > 0:
            glColor3ub(*self.border_color)
            glLineWidth(self.border_thickness)
            glBegin(GL_LINE_LOOP)
            glVertex2f(x, y)
            glVertex2f(x + width, y)
            glVertex2f(x + width, y + height)
            glVertex2f(x, y + height)
            glEnd()

        # Draw the text inside the text box
        if self.texture_id is not None:
            glPushAttrib(GL_ENABLE_BIT | GL_COLOR_BUFFER_BIT | GL_TEXTURE_BIT)
            glPushMatrix()
            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            # Bind the texture
            glBindTexture(GL_TEXTURE_2D, self.texture_id)
            glEnable(GL_TEXTURE_2D)
            glColor3f(1.0, 1.0, 1.0)

            # Draw the textured quad with the text
            x1 = x
            y1 = y
            x2 = x + self.width
            y2 = y + self.height

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
            glPopMatrix()
            glPopAttrib()

        # Draw the cursor
        if self.cursor_visible:
            self.draw_cursor()

    def draw_cursor(self):
        """
        Draw the cursor at the appropriate position.
        """
        # Calculate cursor position
        x, y = self.position
        padding = self.padding
        text_height = self.text_surface.get_height()
        cursor_height = text_height
        cursor_width = 2  # Width of the cursor line

        # Calculate the width of text up to the cursor position
        cursor_text = self.text[:self.cursor_position]
        cursor_x_in_text = self.font.size(cursor_text)[0]

        # Calculate cursor x position on the screen
        cursor_x_position = x + padding + cursor_x_in_text - self.offset

        # Ensure cursor is within the text box
        cursor_x_min = x + padding
        cursor_x_max = x + self.size[0] - padding
        if cursor_x_position < cursor_x_min:
            cursor_x_position = cursor_x_min
        elif cursor_x_position > cursor_x_max:
            cursor_x_position = cursor_x_max

        # Set cursor color (same as text color)
        glColor3ub(*self.text_color)

        # Draw the cursor as a rectangle
        glBegin(GL_QUADS)
        glVertex2f(cursor_x_position, y + (self.size[1] - cursor_height) / 2)
        glVertex2f(cursor_x_position + cursor_width, y + (self.size[1] - cursor_height) / 2)
        glVertex2f(cursor_x_position + cursor_width, y + (self.size[1] + cursor_height) / 2)
        glVertex2f(cursor_x_position, y + (self.size[1] + cursor_height) / 2)
        glEnd()

    def clear(self):
        """
        Clear the text box content and reset the submitted flag.
        """
        self.text = ""
        self.cursor_position = 0
        self.submitted = False
        self.update_texture