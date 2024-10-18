# screen.py

import os
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from screeninfo import get_monitors
from time import monotonic_ns, sleep


class Screen:
    def __init__(self, screen_number=0, width=None, height=None, fullscreen=True, vsync=True, desired_refresh_rate=60):
        """
        Initialize a screen using Pygame and OpenGL.
        
        Parameters
        ----------
        
        screen_number : int
            The number of the screen to use. Default is 0.
            
        width : int
            The width of the screen. Default is the width of the monitor.
        
        height : int
            The height of the screen. Default is the height of the monitor.

        fullscreen : bool
            Whether to use fullscreen mode. Default is True.
        
        vsync : bool
            Whether to use vertical synchronization. Default is True.
        
        desired_refresh_rate : int
            The desired refresh rate of the screen in Hz. Default is 60.
        
        """
        # Get monitors
        monitors = get_monitors()
        
        # Set monitor
        if len(monitors) > screen_number:
            monitor = monitors[screen_number]
        else:
            monitor = monitors[0]
        
        self.monitor = monitor
        self.width = width or monitor.width
        self.height = height or monitor.height
        self.fullscreen = fullscreen
        self.vsync = vsync
        self.desired_refresh_rate = desired_refresh_rate
        self.mouse_visible = True

        # Internal timing variables for frame measurement
        self.last_flip_time = None
        self.prev_flip_time = None

        # Set the window position to the monitor's position
        os.environ['SDL_VIDEO_WINDOW_POS'] = f"{monitor.x},{monitor.y}"

        # Initialize Pygame and create a window
        pygame.init()
        flags = DOUBLEBUF | OPENGL
        if fullscreen:
            flags |= FULLSCREEN
        self.screen = pygame.display.set_mode((self.width, self.height), flags, vsync=vsync)
        self.clock = pygame.time.Clock()

        # grab the mouse attention
        pygame.event.set_grab(True)

        # Initialize OpenGL
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.width, self.height, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glClearColor(0.5, 0.5, 0.5, 1)  # Gray background

        # Disable depth testing once during setup
        glDisable(GL_DEPTH_TEST)

    def flip(self):
        """
        Flip the screen and keep a timestamp.

        Returns
        -------
        float
            The timestamp of the flip.
        """
        pygame.display.flip()
        self.tick()
        self.prev_flip_time = self.last_flip_time
        this_time = monotonic_ns()
        self.last_flip_time = this_time
        return this_time

    def get_flip_interval(self):
        """
        Get the interval between the last two flips.

        Returns
        -------
        float
            The interval between the last two flips in seconds.
        
        """
        if self.last_flip_time is None or self.prev_flip_time is None:
            return None
        return (self.last_flip_time - self.prev_flip_time)/1e9 # go back to seconds
    
    def fill(self, color=(128,128,128)):
        """
        Fill the screen with a color.

        Parameters
        ----------
        color : tuple
            The color to fill the screen with. Should be a tuple of 3 integers between 0 and 255.

        """
        # Use OpenGL to clear the screen with the specified color
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND)
        glBlendFunc(GL_ONE, GL_ZERO)
        glDisable(GL_DEPTH_TEST)
        glClearColor(color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def tick(self):
        """
        Limit the frame rate to the desired refresh rate
        """
        self.clock.tick(self.desired_refresh_rate)

    def test_flip_intervals(self, num_frames=50):
        """
        Test the flip intervals of the screen.

        Parameters
        ----------
        num_frames : int
            The number of frames to test. Default is 50.
        """
        frame_rates = []
        for _ in range(num_frames):
            self.fill((128, 128, 128))
            self.flip()
            frame_rates.append(self.get_flip_interval())
        frame_rates_array = np.array(frame_rates)
        frame_rate_actual = np.mean(frame_rates_array[frame_rates_array>0])
        return frame_rate_actual

    def hide_mouse(self):
        # Hide the mouse cursor
        pygame.mouse.set_visible(False)

    def show_mouse(self):
        # Show the mouse cursor
        pygame.mouse.set_visible(True)

    def wait(self, duration_secs):
        """
        Wait for a specified duration in seconds using high-precision timing.
        
        Parameters:
            duration_secs: The duration to wait in seconds (float).
        """
        start_time = monotonic_ns()
        end_time = start_time + int(duration_secs * 1e9)  # Convert seconds to nanoseconds

        # Sleep in small increments to reduce CPU usage
        while True:
            current_time = monotonic_ns()
            remaining_time = (end_time - current_time) / 1e9  # Convert to seconds

            if remaining_time <= 0:
                break

            if remaining_time > 0.005:
                # If more than 5 milliseconds remaining, sleep for a short duration
                sleep(0.001)  # Sleep for 1 millisecond
            else:
                # Busy-wait for the remaining time for higher precision
                pass

    def close(self):
        """
        Close the screen.
        """
        self.show_mouse()
        pygame.quit()