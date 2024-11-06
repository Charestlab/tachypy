# responses.py
import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from tachypy.shapes import Line  # Assuming Line class is in your visuals module
from tachypy.text import Text     # Assuming you have a Text class
import time
# responses.py


class ResponseHandler:
    """
    A class to handle user input events in a Pygame application.

    This class processes keyboard and mouse events, maintains the current state
    of keys and mouse buttons, and provides methods to access this information.
    It also handles quitting the application when needed.

    Attributes:
        should_exit (bool): Flag indicating whether the application should quit.
        start_time (int): Start time in nanoseconds for reaction time measurement.
        key_presses (list): List of key press and release events.
        mouse_clicks (list): List of mouse click events.
        key_down_events (set): Set of keys currently pressed down.
        key_up_events (set): Set of keys released in the current frame.
        mouse_position (tuple): Current position of the mouse cursor.
        mouse_buttons (tuple): Current state of mouse buttons (pressed or not).
        keys_to_listen (list): List of key names to listen for. If None, listens to all keys.
        events (list): List of Pygame events processed in the current frame.
    """

    def __init__(self, keys_to_listen=None):
        """
        Initialize the ResponseHandler.

        Parameters:
            keys_to_listen (list): List of key names to listen for (e.g., ['a', 's', 'escape']).
                                   If None, listens to all keys.
        """
        # Flag indicating whether the application should quit
        self.should_exit = False
        # Start time for reaction time measurement
        self.start_time = time.monotonic_ns()

        # Lists to store input events
        self.key_presses = []    # List of key press and release events
        self.mouse_clicks = []   # List of mouse click events

        # Sets to track current key states
        self.key_down_events = set()  # Set of keys currently pressed down
        self.key_up_events = set()    # Set of keys released in the current frame

        # Mouse state
        self.mouse_position = None                   # Current mouse position (x, y)
        self.mouse_buttons = [False, False, False]   # Mouse buttons states: [Left, Middle, Right]

        # List of key names to listen for
        self.keys_to_listen = keys_to_listen

        # List to store Pygame events processed in the current frame
        self.events = []

    def reset_timer(self):
        """
        Reset the start time for reaction time measurements.
        """
        self.start_time = time.monotonic_ns()

    def get_events(self):
        """
        Retrieve and process Pygame events, updating internal state.

        Stores the events in self.events for access by other components.
        """
        # Clear key event sets
        self.key_down_events.clear()
        self.key_up_events.clear()

        # Get events from Pygame event queue
        self.events = pygame.event.get()

        for event in self.events:
            # Calculate timestamp relative to start_time, in seconds
            timestamp = (time.monotonic_ns() - self.start_time) / 1e9

            if event.type == pygame.QUIT:
                # Set flag to exit the application
                self.should_exit = True

            elif event.type == pygame.KEYDOWN:
                # Key pressed down
                key_name = pygame.key.name(event.key)
                if self.keys_to_listen is None or key_name in self.keys_to_listen:
                    # Store key press event
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keydown',
                        'key': key_name
                    })
                    # Add to set of currently pressed keys
                    self.key_down_events.add(key_name)
                    # Check for escape key to quit application
                    if key_name == 'escape':
                        self.should_exit = True

            elif event.type == pygame.KEYUP:
                # Key released
                key_name = pygame.key.name(event.key)
                if self.keys_to_listen is None or key_name in self.keys_to_listen:
                    # Store key release event
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keyup',
                        'key': key_name
                    })
                    # Add to set of keys released this frame
                    self.key_up_events.add(key_name)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Mouse button pressed
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mousedown',
                    'button': event.button - 1,  # Adjust to 0-based index
                    'pos': event.pos
                })

            elif event.type == pygame.MOUSEBUTTONUP:
                # Mouse button released
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mouseup',
                    'button': event.button - 1,  # Adjust to 0-based index
                    'pos': event.pos
                })

        # Update mouse position and button states
        self.mouse_position = pygame.mouse.get_pos()
        self.mouse_buttons = pygame.mouse.get_pressed()

    def should_quit(self):
        """
        Check if the application should quit.

        Returns:
            bool: True if the application should quit, False otherwise.
        """
        return self.should_exit

    def get_key_presses(self):
        """
        Get the list of key press and release events.

        Returns:
            list: A list of dictionaries with keys:
                - 'time': Timestamp of the event relative to start_time (float).
                - 'type': 'keydown' or 'keyup'.
                - 'key': Name of the key.
        """
        return self.key_presses

    def is_key_down(self, key_name):
        """
        Check if a specific key is currently pressed down.

        Parameters:
            key_name (str): Name of the key to check.

        Returns:
            bool: True if the key is currently pressed, False otherwise.
        """
        return key_name in self.key_down_events

    def get_mouse_position(self):
        """
        Get the current mouse position.

        Returns:
            tuple: (x, y) coordinates of the mouse cursor.
        """
        return self.mouse_position

    def is_mouse_button_pressed(self, button):
        """
        Check if a specific mouse button is currently pressed.

        Parameters:
            button (int): 0 for left button, 1 for middle button, 2 for right button.

        Returns:
            bool: True if the button is currently pressed, False otherwise.
        """
        return self.mouse_buttons[button]

    def get_mouse_clicks(self):
        """
        Get the list of mouse click events.

        Returns:
            list: A list of dictionaries with keys:
                - 'time': Timestamp of the event relative to start_time (float).
                - 'type': 'mousedown' or 'mouseup'.
                - 'button': 0 for left button, 1 for middle button, 2 for right button.
                - 'pos': (x, y) position of the mouse at the time of the event.
        """
        return self.mouse_clicks

    def set_position(self, x, y):
        """
        Set the mouse cursor position.

        Parameters:
            x (int): x-coordinate to move the cursor to.
            y (int): y-coordinate to move the cursor to.
        """
        pygame.mouse.set_pos((x, y))
        # Update internal mouse position
        self.mouse_position = (x, y)

    def clear_events(self):
        """
        Clear the lists of key presses and mouse clicks.

        This can be used to reset the stored events after they've been processed.
        """
        self.key_presses.clear()
        self.mouse_clicks.clear()
        self.key_down_events.clear()
        self.key_up_events.clear()


class Scrollbar:
    def __init__(self,
                 screen_width,
                 screen_height,
                 position_y=200,  # Since origin is at top-left, positive y is downward
                 half_bar_length=400,
                 bar_thickness=4,
                 bar_color=(0, 0, 0),
                 half_mark_height=5,
                 mark_thickness=3,
                 mark_color=(0, 0, 0),
                 num_marks=10,
                 half_end_height=20,
                 end_thickness=4,
                 end_color=(0, 0, 0),
                 text_left='0',
                 text_right='100',
                 font_size=24,
                 font_name='Helvetica',
                 text_color=(0, 0, 0),
                 text_offset=12):
        """
        Initialize the Scrollbar.

        Parameters:
            screen_width: Width of the screen.
            screen_height: Height of the screen.
            ... (other parameters remain the same) ...
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.position_y = position_y
        self.half_bar_length = half_bar_length
        self.bar_thickness = bar_thickness
        self.bar_color = bar_color
        self.half_mark_height = half_mark_height
        self.mark_thickness = mark_thickness
        self.mark_color = mark_color
        self.num_marks = num_marks
        self.half_end_height = half_end_height
        self.end_thickness = end_thickness
        self.end_color = end_color
        self.text_left = text_left
        self.text_right = text_right
        self.text_size = font_size
        self.font_name = font_name
        self.text_color = text_color
        self.text_offset = text_offset

        # Center x-coordinate
        self.center_x = self.screen_width / 2

        # Create the main bar
        self.bar = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y),
            end_point=(self.center_x + self.half_bar_length, self.position_y),
            thickness=self.bar_thickness,
            color=self.bar_color
        )

        # Create the marks
        self.marks = []
        for x in np.linspace(self.center_x - self.half_bar_length,
                             self.center_x + self.half_bar_length,
                             self.num_marks):
            mark = Line(
                start_point=(x, self.position_y - self.half_mark_height),
                end_point=(x, self.position_y + self.half_mark_height),
                thickness=self.mark_thickness,
                color=self.mark_color
            )
            self.marks.append(mark)

        # Create the ends
        self.left_end = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x - self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color
        )
        self.right_end = Line(
            start_point=(self.center_x + self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x + self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color
        )

        # Create the text labels
        self.text_left_label = Text(
            text=self.text_left,
            position=(self.center_x - self.half_bar_length, self.position_y + self.half_end_height + self.text_offset),
            font=self.font_name,
            font_size=self.text_size,
            color=self.text_color
        )
        self.text_right_label = Text(
            text=self.text_right,
            position=(self.center_x + self.half_bar_length, self.position_y + self.half_end_height + self.text_offset),
            font=self.font_name,
            font_size=self.text_size,
            color=self.text_color
        )

        # Mobile part (draggable line)
        self.half_mobile_line_height = 12    # Half the height of the mobile line
        self.mobile_line_thickness = 6       # Thickness of the mobile line
        self.mobile_line_color = (255, 0, 0) # Color of the mobile line (red)
        self.mobile_line_x = self.center_x   # Start at the center
        self.mobile_line = Line(
            start_point=(self.mobile_line_x, self.position_y - self.half_mobile_line_height),
            end_point=(self.mobile_line_x, self.position_y + self.half_mobile_line_height),
            thickness=self.mobile_line_thickness,
            color=self.mobile_line_color
        )

    def draw(self):
        # Draw the main bar
        self.bar.draw()
        # Draw the marks
        for mark in self.marks:
            mark.draw()
        # Draw the ends
        self.left_end.draw()
        self.right_end.draw()
        # Draw the text labels
        self.text_left_label.draw()
        self.text_right_label.draw()
        # Draw the mobile line
        self.mobile_line.draw()

    def handle_mouse(self, mouse_x, mouse_y):
        """
        Update the position of the mobile line based on mouse input.

        Parameters:
            mouse_x: x-coordinate of the mouse.
            mouse_y: y-coordinate of the mouse.
        """
        # Check if mouse_y is near the bar's position_y (within some tolerance)
        if abs(mouse_y - self.position_y) <= self.half_end_height * 2:
            # Clamp mouse_x within the bar's range
            min_x = self.center_x - self.half_bar_length
            max_x = self.center_x + self.half_bar_length
            new_x = np.clip(mouse_x, min_x, max_x)
            self.mobile_line_x = new_x
            # Update the mobile line's position
            self.mobile_line.set_start_point((self.mobile_line_x, self.position_y - self.half_mobile_line_height))
            self.mobile_line.set_end_point((self.mobile_line_x, self.position_y + self.half_mobile_line_height))
 

    def get_value(self):
        """
        Get the value corresponding to the position of the mobile line.

        Returns:
            A float value between 0 and 100.
        """
        min_x = self.center_x - self.half_bar_length
        max_x = self.center_x + self.half_bar_length
        value = ((self.mobile_line_x - min_x) / (max_x - min_x)) * 100
        return value