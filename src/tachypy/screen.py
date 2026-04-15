"""Display and timing utilities for TachyPy."""

import os
from time import monotonic_ns, sleep
from typing import Optional, Sequence, Tuple

import numpy as np
import pygame
from OpenGL.GL import (
    GL_BLEND,
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_MODELVIEW,
    GL_ONE_MINUS_SRC_ALPHA,
    GL_PROJECTION,
    GL_SRC_ALPHA,
    GL_TEXTURE_2D,
    glBindTexture,
    glBlendFunc,
    glClear,
    glClearColor,
    glDisable,
    glEnable,
    glLoadIdentity,
    glMatrixMode,
    glViewport,
)
from OpenGL.GLU import gluOrtho2D
from pygame.locals import DOUBLEBUF, FULLSCREEN, OPENGL
from screeninfo import get_monitors


class Screen:
    """Create and manage a Pygame window backed by an OpenGL context."""

    def __init__(
        self,
        screen_number: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fullscreen: bool = True,
        vsync: bool = True,
        desired_refresh_rate: int = 60,
    ):
        monitors = get_monitors()
        if not monitors:
            raise RuntimeError("No monitors detected.")

        safe_screen_number = max(0, int(screen_number))
        if safe_screen_number >= len(monitors):
            safe_screen_number = 0

        monitor = monitors[safe_screen_number]

        self.monitor = monitor
        self.width = int(width or monitor.width)
        self.height = int(height or monitor.height)
        self.fullscreen = bool(fullscreen)
        self.vsync = bool(vsync)
        self.desired_refresh_rate = int(desired_refresh_rate)
        self.mouse_visible = True

        self.last_flip_time: Optional[int] = None
        self.prev_flip_time: Optional[int] = None

        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{monitor.x},{monitor.y}"

        pygame.init()
        flags = DOUBLEBUF | OPENGL
        if self.fullscreen:
            flags |= FULLSCREEN
        self.screen = pygame.display.set_mode((self.width, self.height), flags, vsync=self.vsync)
        self.clock = pygame.time.Clock()

        pygame.event.set_grab(True)

        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluOrtho2D(0, self.width, self.height, 0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glClearColor(0.5, 0.5, 0.5, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glDisable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.flip()
        pygame.event.get()

    @staticmethod
    def _normalize_rgb_color(color: Sequence[float]) -> Tuple[float, float, float]:
        """Normalize an RGB color from [0, 255] into [0, 1]."""
        if len(color) != 3:
            raise ValueError("color must be a 3-item RGB sequence")
        r, g, b = color
        return (float(r) / 255.0, float(g) / 255.0, float(b) / 255.0)

    @staticmethod
    def _sleep_duration_for_remaining_ns(remaining_ns: int) -> Optional[float]:
        """Return sleep duration in seconds, or None for busy-wait/exit path."""
        if remaining_ns <= 0:
            return None
        if remaining_ns > 5_000_000:
            return 0.001
        return None

    def flip(self) -> int:
        """Swap buffers and return the flip timestamp in nanoseconds."""
        pygame.display.flip()
        self.tick()
        self.prev_flip_time = self.last_flip_time
        this_time = monotonic_ns()
        self.last_flip_time = this_time
        return this_time

    def get_flip_interval(self) -> Optional[float]:
        """Return the interval between the last two flips in seconds."""
        if self.last_flip_time is None or self.prev_flip_time is None:
            return None
        return (self.last_flip_time - self.prev_flip_time) / 1e9

    def fill(self, color: Sequence[float] = (128, 128, 128)) -> None:
        """Clear the screen with the provided RGB color in [0, 255]."""
        r, g, b = self._normalize_rgb_color(color)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_DEPTH_TEST)
        glClearColor(r, g, b, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def tick(self) -> None:
        """Limit frame updates to the desired refresh rate."""
        self.clock.tick(self.desired_refresh_rate)

    def test_flip_intervals(self, num_frames: int = 50) -> float:
        """Measure and return the mean frame interval in seconds."""
        frame_intervals = []
        for _ in range(num_frames):
            self.fill((128, 128, 128))
            self.flip()
            interval = self.get_flip_interval()
            if interval is not None and interval > 0:
                frame_intervals.append(interval)

        if not frame_intervals:
            return 0.0
        return float(np.mean(np.array(frame_intervals)))

    def hide_mouse(self) -> None:
        pygame.mouse.set_visible(False)
        self.mouse_visible = False

    def show_mouse(self) -> None:
        pygame.mouse.set_visible(True)
        self.mouse_visible = True

    def set_mouse_visible(self, visible: bool) -> None:
        """Set mouse visibility explicitly."""
        if visible:
            self.show_mouse()
        else:
            self.hide_mouse()

    def wait(self, duration_secs: float) -> None:
        """Wait for a duration in seconds using high precision timing."""
        if duration_secs <= 0:
            return

        end_time = monotonic_ns() + int(duration_secs * 1e9)
        while True:
            remaining_ns = end_time - monotonic_ns()
            sleep_duration = self._sleep_duration_for_remaining_ns(remaining_ns)
            if sleep_duration is None:
                if remaining_ns <= 0:
                    break
                continue
            sleep(sleep_duration)

    def close(self) -> None:
        """Close the display and quit Pygame."""
        self.show_mouse()
        pygame.quit()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False
