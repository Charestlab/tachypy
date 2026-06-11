"""Display and timing utilities for TachyPy with pluggable backends."""

import warnings
from time import monotonic_ns, sleep
from typing import Optional, Sequence, Tuple

import numpy as np
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
from screeninfo import get_monitors

class Screen:
    """Create and manage a GLFW/OpenGL display."""

    def __init__(
        self,
        screen_number: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fullscreen: bool = True,
        vsync: bool = True,
        desired_refresh_rate: int = 60,
        grab_input: bool = True,
        backend: str = "glfw",
        warmup_frames: int = 60,
        warmup_color: Sequence[float] = (128, 128, 128),
    ):
        """Initialize display window, OpenGL context, and timing state."""
        self.backend = backend.strip().lower()
        if self.backend != "glfw":
            raise ValueError("Pygame support has been removed; backend must be 'glfw'.")
        if int(warmup_frames) < 0:
            raise ValueError("warmup_frames must be >= 0")

        self.width = int(width) if width is not None else None
        self.height = int(height) if height is not None else None
        self.fullscreen = bool(fullscreen)
        self.vsync = bool(vsync)
        self.desired_refresh_rate = int(desired_refresh_rate)
        self.grab_input = bool(grab_input)
        self.warmup_frames = int(warmup_frames)
        self.warmup_color = tuple(warmup_color)
        self.mouse_visible = True

        self.last_flip_time: Optional[int] = None
        self.prev_flip_time: Optional[int] = None
        self.last_flip_submit_time: Optional[int] = None
        self.prev_flip_submit_time: Optional[int] = None
        self._last_tick_time_ns: Optional[int] = None

        self.monitor = None
        self.screen = None
        self._glfw = None
        self._glfw_window = None

        self._init_glfw_backend(screen_number)
        self._init_opengl_state()
        self._warm_up_display()

    @staticmethod
    def _clamp_screen_number(screen_number: int, n_monitors: int) -> int:
        """Return a valid monitor index, warning if the requested one is out of range."""
        safe = max(0, int(screen_number))
        if safe >= n_monitors:
            warnings.warn(
                f"screen_number={screen_number} exceeds available monitors ({n_monitors}); using 0.",
                UserWarning,
                stacklevel=4,  # _clamp_screen_number → _init_*_backend → __init__ → caller
            )
            return 0
        return safe

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

    def _init_glfw_backend(self, screen_number: int) -> None:
        """Create a GLFW window/context on the requested monitor."""
        try:
            import glfw
        except ImportError as err:
            raise RuntimeError(
                "GLFW backend requested but `glfw` is not installed. "
                "Install with `pip install tachypy` or `pip install glfw`."
            ) from err

        if not glfw.init():
            raise RuntimeError("Failed to initialize GLFW.")

        self._glfw = glfw
        monitors = glfw.get_monitors() or []
        if not monitors:
            glfw.terminate()
            raise RuntimeError("No monitors detected by GLFW.")

        safe_screen_number = Screen._clamp_screen_number(screen_number, len(monitors))
        monitor = monitors[safe_screen_number]
        self.monitor = monitor

        mode = glfw.get_video_mode(monitor)
        if mode is None:
            glfw.terminate()
            raise RuntimeError("Unable to read monitor video mode.")

        if self.width is None:
            self.width = int(mode.size.width)
        if self.height is None:
            self.height = int(mode.size.height)

        glfw.default_window_hints()
        glfw.window_hint(glfw.DOUBLEBUFFER, glfw.TRUE)

        fullscreen_monitor = monitor if self.fullscreen else None
        window = glfw.create_window(self.width, self.height, "TachyPy", fullscreen_monitor, None)
        if window is None:
            glfw.terminate()
            raise RuntimeError("Failed to create GLFW window.")

        self._glfw_window = window
        self.screen = window
        glfw.make_context_current(window)
        glfw.swap_interval(1 if self.vsync else 0)

        if not self.fullscreen:
            mx, my = glfw.get_monitor_pos(monitor)
            glfw.set_window_pos(window, mx + 60, my + 60)

        cursor_mode = glfw.CURSOR_DISABLED if self.grab_input else glfw.CURSOR_NORMAL
        glfw.set_input_mode(window, glfw.CURSOR, cursor_mode)

        # Keep logical size (points) and framebuffer size (pixels) distinct on HiDPI displays.
        self._sync_glfw_viewport_and_projection(force=True)

    def _init_opengl_state(self) -> None:
        """Configure 2D projection and default OpenGL state."""
        fb_w, fb_h = self._glfw.get_framebuffer_size(self._glfw_window)
        viewport_w = int(fb_w) if fb_w > 0 else int(self.width)
        viewport_h = int(fb_h) if fb_h > 0 else int(self.height)

        glViewport(0, 0, viewport_w, viewport_h)
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

    def _reset_flip_timing(self) -> None:
        """Clear flip/tick timestamps after non-experiment setup frames."""
        self.last_flip_time = None
        self.prev_flip_time = None
        self.last_flip_submit_time = None
        self.prev_flip_submit_time = None
        self._last_tick_time_ns = None

    def _warm_up_display(self) -> None:
        """Present neutral frames before the caller starts experiment timing."""
        for _ in range(self.warmup_frames):
            self.fill(self.warmup_color)
            self.flip()
        self._reset_flip_timing()

    def flip(self) -> int:
        """Swap buffers and return the immediate post-swap timestamp in nanoseconds.

        The returned value is captured immediately after the backend swap call
        returns, before event polling, viewport synchronization, input updates,
        or frame-rate housekeeping. It approximates the display swap completion
        time, not photon onset at a specific screen location.
        """
        self.prev_flip_time = self.last_flip_time
        self.prev_flip_submit_time = self.last_flip_submit_time
        submit_time = monotonic_ns()

        self._glfw.swap_buffers(self._glfw_window)
        this_time = monotonic_ns()
        self._sync_glfw_viewport_and_projection()

        self.last_flip_submit_time = submit_time
        self.last_flip_time = this_time
        self.tick()
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
        if self.desired_refresh_rate <= 0 or self.vsync:
            return

        now = monotonic_ns()
        if self._last_tick_time_ns is None:
            self._last_tick_time_ns = now
            return

        target_frame_ns = int(1e9 / self.desired_refresh_rate)
        deadline = self._last_tick_time_ns + target_frame_ns
        while True:
            remaining_ns = deadline - monotonic_ns()
            sleep_duration = self._sleep_duration_for_remaining_ns(remaining_ns)
            if sleep_duration is None:
                if remaining_ns <= 0:
                    break
                continue
            sleep(sleep_duration)

        self._last_tick_time_ns = monotonic_ns()

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
        """Hide cursor in the active backend window."""
        self._glfw.set_input_mode(self._glfw_window, self._glfw.CURSOR, self._glfw.CURSOR_HIDDEN)
        self.mouse_visible = False

    def show_mouse(self) -> None:
        """Show cursor in the active backend window."""
        self._glfw.set_input_mode(self._glfw_window, self._glfw.CURSOR, self._glfw.CURSOR_NORMAL)
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
        """Close the display backend."""
        self.show_mouse()
        if self._glfw_window is not None:
            self._glfw.destroy_window(self._glfw_window)
            self._glfw_window = None
        self._glfw.terminate()

    def _sync_glfw_viewport_and_projection(self, force: bool = False) -> None:
        """Sync logical projection and framebuffer viewport for GLFW HiDPI."""
        win_w, win_h = self._glfw.get_window_size(self._glfw_window)
        fb_w, fb_h = self._glfw.get_framebuffer_size(self._glfw_window)
        if win_w <= 0 or win_h <= 0 or fb_w <= 0 or fb_h <= 0:
            return

        logical_changed = force or (int(win_w) != int(self.width) or int(win_h) != int(self.height))
        if logical_changed:
            self.width = int(win_w)
            self.height = int(win_h)

        # Always keep viewport in framebuffer pixels (HiDPI-safe).
        glViewport(0, 0, int(fb_w), int(fb_h))

        if logical_changed:
            # Use TachyPy's top-left logical origin convention.
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluOrtho2D(0, self.width, self.height, 0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

    def poll_events(self) -> None:
        """Pump pending GLFW window events without interpreting participant input."""
        self._glfw.poll_events()

    def should_close(self) -> bool:
        """Return whether the GLFW window has received a close request."""
        return bool(self._glfw.window_should_close(self._glfw_window))

    def __enter__(self):
        """Enter context manager and return this Screen instance."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit context manager by closing window/resources."""
        self.close()
        return False
