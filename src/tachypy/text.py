import warnings

import pygame
from OpenGL.GL import *
from OpenGL.GLU import *


class Text:
    """OpenGL text object with pluggable font backends and texture upload."""

    def __init__(
        self,
        text,
        font_name='Helvetica',
        font_size=24,
        color=(255, 255, 255),
        dest_rect=None,
        line_spacing=4,
        backend="auto",
    ):
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
        self._font_available = True
        self._warned_font_unavailable = False
        self.backend = str(backend).lower()
        self._font_backend = None
        self._font_obj = None
        self._pil_image = None
        self._pil_draw = None
        self._pil_imagefont = None
        self._surface_data = None
        self.texture_width = 0
        self.texture_height = 0
        self.text = text
        self.font_name = font_name
        self.font_size = font_size
        self.color = color
        self.dest_rect = dest_rect
        self.texture_id = None
        self.surface = None
        self.line_spacing = line_spacing

        self._init_text_backend()
        self.lines = []
        self._split_text_into_lines()
        self._generate_surface()

    def _init_text_backend(self):
        """Initialize selected text backend and font object."""
        if self.backend not in {"auto", "pygame", "pillow"}:
            raise ValueError("Text backend must be 'auto', 'pygame', or 'pillow'.")

        if self.backend in {"auto", "pygame"}:
            try:
                pygame.font.init()
                self._font_obj = pygame.font.SysFont(self.font_name, self.font_size)
                # Smoke test for environments where pygame.font appears available but fails at render.
                _ = self._font_obj.size("Ag")
                self._font_backend = "pygame"
                return
            except Exception as err:
                if self.backend == "pygame":
                    raise RuntimeError(f"pygame text backend unavailable: {err}") from err

        if self.backend in {"auto", "pillow"}:
            try:
                from PIL import Image, ImageDraw, ImageFont

                self._pil_image = Image
                self._pil_draw = ImageDraw
                self._pil_imagefont = ImageFont
                self._font_obj = self._load_pillow_font()
                self._font_backend = "pillow"
                return
            except Exception as err:
                if self.backend == "pillow":
                    raise RuntimeError(f"pillow text backend unavailable: {err}") from err

        self._font_available = False
        warnings.warn(
            "No text backend available. Install a working pygame font stack or Pillow.",
            RuntimeWarning,
            stacklevel=2,
        )

    def _load_pillow_font(self):
        """Load requested Pillow font or fall back to default font."""
        try:
            return self._pil_imagefont.truetype(self.font_name, self.font_size)
        except Exception:
            return self._pil_imagefont.load_default()

    def _measure_text(self, text_value):
        """Measure text dimensions in pixels for the active backend."""
        if self._font_backend == "pygame":
            return self._font_obj.size(text_value)

        # Pillow backend.
        scratch = self._pil_image.new("RGBA", (1, 1), (0, 0, 0, 0))
        drawer = self._pil_draw.Draw(scratch)
        bbox = drawer.textbbox((0, 0), text_value if text_value else " ", font=self._font_obj)
        width = max(1, int(bbox[2] - bbox[0]))
        height = max(1, int(bbox[3] - bbox[1]))
        return width, height

    def _split_text_into_lines(self):
        """Split the text into multiple lines that fit within the dest_rect width."""
        if not self._font_available:
            self.lines = self.text.splitlines() or [self.text]
            if not self.lines:
                self.lines = [""]
            return

        if not self.dest_rect:
            self.lines = self.text.splitlines() or [self.text]
            if not self.lines:
                self.lines = [""]
            return

        max_width = self.dest_rect[2] - self.dest_rect[0]  # Width of the rectangle

        self.lines = []
        raw_lines = self.text.splitlines() or [""]
        for raw_line in raw_lines:
            if raw_line == "":
                self.lines.append("")
                continue

            words = raw_line.split()
            line = ""
            for word in words:
                test_line = f"{line} {word}".strip()
                if self._measure_text(test_line)[0] <= max_width or line == "":
                    line = test_line
                else:
                    self.lines.append(line)
                    line = word
            if line:
                self.lines.append(line)

    def _generate_surface(self):
        """Generate a Pygame surface with the text rendered."""
        if not self._font_available:
            self.surface = None
            self.texture_id = None
            self._surface_data = None
            self.texture_width = 0
            self.texture_height = 0
            return

        lines = self.lines if self.lines else [""]
        if self._font_backend == "pygame":
            # Render empty lines as spaces so we still get a stable line height.
            line_surfaces = [self._font_obj.render(line if line else " ", True, self.color) for line in lines]
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

            self.texture_width = int(self.surface.get_width())
            self.texture_height = int(self.surface.get_height())
            self._surface_data = pygame.image.tostring(self.surface, "RGBA", True)
        else:
            line_sizes = [self._measure_text(line if line else " ") for line in lines]
            max_width = max(width for width, _ in line_sizes)
            total_height = sum(height for _, height in line_sizes) + (len(line_sizes) - 1) * self.line_spacing

            image = self._pil_image.new("RGBA", (max_width, total_height), (0, 0, 0, 0))
            drawer = self._pil_draw.Draw(image)
            y_offset = 0
            for line, (_, h) in zip(lines, line_sizes):
                drawer.text((0, y_offset), line if line else " ", fill=tuple(self.color) + (255,), font=self._font_obj)
                y_offset += h + self.line_spacing

            # OpenGL expects bottom-left origin by default; match pygame path with vertical flip.
            image = image.transpose(self._pil_image.FLIP_TOP_BOTTOM)
            self.surface = None
            self.texture_width, self.texture_height = image.size
            self._surface_data = image.tobytes("raw", "RGBA")

        self._generate_texture()

    def _generate_texture(self):
        """Upload the Pygame surface as an OpenGL texture."""
        if self._surface_data is None or self.texture_width <= 0 or self.texture_height <= 0:
            return

        if self.texture_id:
            glDeleteTextures([self.texture_id])

        self.texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGBA,
            self.texture_width,
            self.texture_height,
            0,
            GL_RGBA,
            GL_UNSIGNED_BYTE,
            self._surface_data,
        )

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        glBindTexture(GL_TEXTURE_2D, 0)

    def draw(self):
        """
        Draw the text on the screen, centered within the dest_rect.
        """
        if not self._font_available or self.texture_width <= 0 or self.texture_height <= 0 or self.texture_id is None:
            if not self._warned_font_unavailable:
                warnings.warn(
                    "Text.draw() skipped because font backend is unavailable.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._warned_font_unavailable = True
            return

        if not self.dest_rect:
            raise ValueError("dest_rect must be set to draw text.")

        x1, y1, x2, y2 = self.dest_rect
        rect_width = x2 - x1
        rect_height = y2 - y1

        # Center the text within the rectangle
        texture_width = self.texture_width
        texture_height = self.texture_height
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

    def delete(self):
        """
        Delete the OpenGL texture associated with this text object.
        """
        if self.texture_id:
            glDeleteTextures([self.texture_id])
            self.texture_id = None
        



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
        self.update_texture()
