"""Display and timing utilities for TachyPy with pluggable backends."""

import os
import warnings
from time import monotonic_ns, sleep
from typing import Dict, Optional, Sequence, Tuple

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

_GLFW_KEY_MAP: Dict[str, str] = {
    "space":         "KEY_SPACE",
    "apostrophe":    "KEY_APOSTROPHE",
    "comma":         "KEY_COMMA",
    "minus":         "KEY_MINUS",
    "period":        "KEY_PERIOD",
    "slash":         "KEY_SLASH",
    "0":             "KEY_0",
    "1":             "KEY_1",
    "2":             "KEY_2",
    "3":             "KEY_3",
    "4":             "KEY_4",
    "5":             "KEY_5",
    "6":             "KEY_6",
    "7":             "KEY_7",
    "8":             "KEY_8",
    "9":             "KEY_9",
    "semicolon":     "KEY_SEMICOLON",
    "equal":         "KEY_EQUAL",
    "a":             "KEY_A",
    "b":             "KEY_B",
    "c":             "KEY_C",
    "d":             "KEY_D",
    "e":             "KEY_E",
    "f":             "KEY_F",
    "g":             "KEY_G",
    "h":             "KEY_H",
    "i":             "KEY_I",
    "j":             "KEY_J",
    "k":             "KEY_K",
    "l":             "KEY_L",
    "m":             "KEY_M",
    "n":             "KEY_N",
    "o":             "KEY_O",
    "p":             "KEY_P",
    "q":             "KEY_Q",
    "r":             "KEY_R",
    "s":             "KEY_S",
    "t":             "KEY_T",
    "u":             "KEY_U",
    "v":             "KEY_V",
    "w":             "KEY_W",
    "x":             "KEY_X",
    "y":             "KEY_Y",
    "z":             "KEY_Z",
    "left_bracket":  "KEY_LEFT_BRACKET",
    "backslash":     "KEY_BACKSLASH",
    "right_bracket": "KEY_RIGHT_BRACKET",
    "grave_accent":  "KEY_GRAVE_ACCENT",
    "world_1":       "KEY_WORLD_1",
    "world_2":       "KEY_WORLD_2",
    "escape":        "KEY_ESCAPE",
    "esc":           "KEY_ESCAPE",
    "enter":         "KEY_ENTER",
    "return":        "KEY_ENTER",
    "tab":           "KEY_TAB",
    "backspace":     "KEY_BACKSPACE",
    "insert":        "KEY_INSERT",
    "delete":        "KEY_DELETE",
    "right":         "KEY_RIGHT",
    "left":          "KEY_LEFT",
    "down":          "KEY_DOWN",
    "up":            "KEY_UP",
    "page_up":       "KEY_PAGE_UP",
    "page_down":     "KEY_PAGE_DOWN",
    "home":          "KEY_HOME",
    "end":           "KEY_END",
    "caps_lock":     "KEY_CAPS_LOCK",
    "scroll_lock":   "KEY_SCROLL_LOCK",
    "num_lock":      "KEY_NUM_LOCK",
    "print_screen":  "KEY_PRINT_SCREEN",
    "pause":         "KEY_PAUSE",
    "f1":            "KEY_F1",
    "f2":            "KEY_F2",
    "f3":            "KEY_F3",
    "f4":            "KEY_F4",
    "f5":            "KEY_F5",
    "f6":            "KEY_F6",
    "f7":            "KEY_F7",
    "f8":            "KEY_F8",
    "f9":            "KEY_F9",
    "f10":           "KEY_F10",
    "f11":           "KEY_F11",
    "f12":           "KEY_F12",
    "f13":           "KEY_F13",
    "f14":           "KEY_F14",
    "f15":           "KEY_F15",
    "f16":           "KEY_F16",
    "f17":           "KEY_F17",
    "f18":           "KEY_F18",
    "f19":           "KEY_F19",
    "f20":           "KEY_F20",
    "f21":           "KEY_F21",
    "f22":           "KEY_F22",
    "f23":           "KEY_F23",
    "f24":           "KEY_F24",
    "f25":           "KEY_F25",
    "kp_0":          "KEY_KP_0",
    "kp_1":          "KEY_KP_1",
    "kp_2":          "KEY_KP_2",
    "kp_3":          "KEY_KP_3",
    "kp_4":          "KEY_KP_4",
    "kp_5":          "KEY_KP_5",
    "kp_6":          "KEY_KP_6",
    "kp_7":          "KEY_KP_7",
    "kp_8":          "KEY_KP_8",
    "kp_9":          "KEY_KP_9",
    "kp_decimal":    "KEY_KP_DECIMAL",
    "kp_divide":     "KEY_KP_DIVIDE",
    "kp_multiply":   "KEY_KP_MULTIPLY",
    "kp_subtract":   "KEY_KP_SUBTRACT",
    "kp_add":        "KEY_KP_ADD",
    "kp_enter":      "KEY_KP_ENTER",
    "kp_equal":      "KEY_KP_EQUAL",
    "left_shift":    "KEY_LEFT_SHIFT",
    "left_ctrl":     "KEY_LEFT_CONTROL",
    "left_alt":      "KEY_LEFT_ALT",
    "left_super":    "KEY_LEFT_SUPER",
    "right_shift":   "KEY_RIGHT_SHIFT",
    "right_ctrl":    "KEY_RIGHT_CONTROL",
    "right_alt":     "KEY_RIGHT_ALT",
    "right_super":   "KEY_RIGHT_SUPER",
    "menu":          "KEY_MENU",
}


class Screen:
    """Create and manage a display backed by Pygame or GLFW."""

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
        if self.backend not in {"pygame", "glfw"}:
            raise ValueError("backend must be 'pygame' or 'glfw'")
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
        self.clock = None
        self._pygame = None
        self._glfw = None
        self._glfw_window = None
        self._glfw_prev_key_state: Dict[int, bool] = {}
        self._glfw_curr_key_state: Dict[int, bool] = {}
        self._glfw_keys_to_track = set()
        self._glfw_prev_mouse_state: Dict[int, bool] = {}
        self._glfw_curr_mouse_state: Dict[int, bool] = {}
        self._glfw_mouse_position: Optional[Tuple[float, float]] = None

        if self.backend == "pygame":
            self._init_pygame_backend(screen_number)
        else:
            self._init_glfw_backend(screen_number)

        self._init_opengl_state()
        self._warm_up_display()

        if self.backend == "pygame":
            self._pygame.event.get()

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

    def _init_pygame_backend(self, screen_number: int) -> None:
        """Create a pygame window/context on the requested monitor."""
        monitors = get_monitors()
        if not monitors:
            raise RuntimeError("No monitors detected.")

        safe_screen_number = Screen._clamp_screen_number(screen_number, len(monitors))
        monitor = monitors[safe_screen_number]
        self.monitor = monitor

        if self.width is None:
            self.width = int(monitor.width)
        if self.height is None:
            self.height = int(monitor.height)

        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{monitor.x},{monitor.y}"

        import pygame
        from pygame.locals import DOUBLEBUF, FULLSCREEN, OPENGL

        self._pygame = pygame
        pygame.init()
        flags = DOUBLEBUF | OPENGL
        if self.fullscreen:
            flags |= FULLSCREEN
        self.screen = pygame.display.set_mode((self.width, self.height), flags, vsync=self.vsync)
        self.clock = pygame.time.Clock()
        pygame.event.set_grab(self.grab_input)

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
        self._glfw_keys_to_track = {
            glfw.KEY_SPACE,
            glfw.KEY_ENTER,
            glfw.KEY_KP_ENTER,
            glfw.KEY_ESCAPE,
        }
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
        if self.backend == "glfw":
            fb_w, fb_h = self._glfw.get_framebuffer_size(self._glfw_window)
            viewport_w = int(fb_w) if fb_w > 0 else int(self.width)
            viewport_h = int(fb_h) if fb_h > 0 else int(self.height)
        else:
            viewport_w = int(self.width)
            viewport_h = int(self.height)

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

        if self.backend == "pygame":
            self._pygame.display.flip()
            this_time = monotonic_ns()
        else:
            self._glfw.swap_buffers(self._glfw_window)
            this_time = monotonic_ns()
            self._glfw.poll_events()
            self._sync_glfw_viewport_and_projection()
            self._update_glfw_key_state()
            self._update_glfw_mouse_state()

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
        if self.backend == "pygame":
            self.clock.tick(self.desired_refresh_rate)
            return

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
        if self.backend == "pygame":
            self._pygame.mouse.set_visible(False)
        else:
            self._glfw.set_input_mode(self._glfw_window, self._glfw.CURSOR, self._glfw.CURSOR_HIDDEN)
        self.mouse_visible = False

    def show_mouse(self) -> None:
        """Show cursor in the active backend window."""
        if self.backend == "pygame":
            self._pygame.mouse.set_visible(True)
        else:
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
        if self.backend == "pygame":
            self._pygame.quit()
        else:
            if self._glfw_window is not None:
                self._glfw.destroy_window(self._glfw_window)
                self._glfw_window = None
            self._glfw.terminate()

    def _sync_glfw_viewport_and_projection(self, force: bool = False) -> None:
        """Sync logical projection and framebuffer viewport for GLFW HiDPI."""
        if self.backend != "glfw":
            return

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
            # Keep the same top-left origin convention as pygame backend.
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluOrtho2D(0, self.width, self.height, 0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

    def _update_glfw_key_state(self) -> None:
        """Update tracked GLFW key down/up state snapshot."""
        self._glfw_prev_key_state, self._glfw_curr_key_state = self._glfw_curr_key_state, {}
        for key in self._glfw_keys_to_track:
            state = self._glfw.get_key(self._glfw_window, key) == self._glfw.PRESS
            self._glfw_curr_key_state[key] = bool(state)

    def track_keys(self, keys) -> None:
        """Register additional GLFW keys for per-frame transition tracking."""
        if self.backend != "glfw":
            return
        for key in keys:
            code = self._glfw_keycode(key)
            if code is not None:
                self._glfw_keys_to_track.add(code)

    def _update_glfw_mouse_state(self) -> None:
        """Update tracked GLFW mouse button transitions and cursor position."""
        buttons_to_track = [
            self._glfw.MOUSE_BUTTON_LEFT,
            self._glfw.MOUSE_BUTTON_MIDDLE,
            self._glfw.MOUSE_BUTTON_RIGHT,
        ]
        self._glfw_prev_mouse_state = dict(self._glfw_curr_mouse_state)
        self._glfw_curr_mouse_state = {}
        for button in buttons_to_track:
            state = self._glfw.get_mouse_button(self._glfw_window, button) == self._glfw.PRESS
            self._glfw_curr_mouse_state[button] = bool(state)

        cursor_x, cursor_y = self._glfw.get_cursor_pos(self._glfw_window)
        self._glfw_mouse_position = (float(cursor_x), float(cursor_y))

    def _glfw_keycode(self, key) -> Optional[int]:
        """Map a key name or keycode to GLFW keycode."""
        if isinstance(key, int):
            return key
        key_name = str(key).strip().lower()
        attr = _GLFW_KEY_MAP.get(key_name)
        if attr is None:
            return None
        return getattr(self._glfw, attr, None)

    def is_key_down(self, key) -> bool:
        """Return True when key is currently held (GLFW backend only)."""
        if self.backend == "glfw":
            code = self._glfw_keycode(key)
            if code is None:
                return False
            self._glfw_keys_to_track.add(code)
            return bool(self._glfw_curr_key_state.get(code, False))
        return False

    def was_key_pressed(self, key) -> bool:
        """Return True when key transitioned to down this frame (GLFW only)."""
        if self.backend == "glfw":
            code = self._glfw_keycode(key)
            if code is None:
                return False
            self._glfw_keys_to_track.add(code)
            was_down = self._glfw_prev_key_state.get(code, False)
            is_down = self._glfw_curr_key_state.get(code, False)
            return bool(is_down and not was_down)
        return False

    def should_close(self) -> bool:
        """Return close status for GLFW windows; always False for pygame."""
        if self.backend == "pygame":
            return False
        return bool(self._glfw.window_should_close(self._glfw_window))

    def get_mouse_position(self) -> Optional[Tuple[float, float]]:
        """Return current mouse position for GLFW backend, otherwise None."""
        if self.backend != "glfw":
            return None
        return self._glfw_mouse_position

    def is_mouse_button_pressed(self, button_index: int) -> bool:
        """Return True when the mouse button is currently pressed (GLFW only)."""
        if self.backend != "glfw":
            return False
        mapping = {
            0: self._glfw.MOUSE_BUTTON_LEFT,
            1: self._glfw.MOUSE_BUTTON_MIDDLE,
            2: self._glfw.MOUSE_BUTTON_RIGHT,
        }
        button = mapping.get(int(button_index))
        if button is None:
            return False
        return bool(self._glfw_curr_mouse_state.get(button, False))

    def was_mouse_button_pressed(self, button_index: int) -> bool:
        """Return True when the mouse button transitioned to down this frame."""
        if self.backend != "glfw":
            return False
        mapping = {
            0: self._glfw.MOUSE_BUTTON_LEFT,
            1: self._glfw.MOUSE_BUTTON_MIDDLE,
            2: self._glfw.MOUSE_BUTTON_RIGHT,
        }
        button = mapping.get(int(button_index))
        if button is None:
            return False
        was_down = self._glfw_prev_mouse_state.get(button, False)
        is_down = self._glfw_curr_mouse_state.get(button, False)
        return bool(is_down and not was_down)

    def was_mouse_button_released(self, button_index: int) -> bool:
        """Return True when the mouse button transitioned to up this frame."""
        if self.backend != "glfw":
            return False
        mapping = {
            0: self._glfw.MOUSE_BUTTON_LEFT,
            1: self._glfw.MOUSE_BUTTON_MIDDLE,
            2: self._glfw.MOUSE_BUTTON_RIGHT,
        }
        button = mapping.get(int(button_index))
        if button is None:
            return False
        was_down = self._glfw_prev_mouse_state.get(button, False)
        is_down = self._glfw_curr_mouse_state.get(button, False)
        return bool(was_down and not is_down)

    def set_mouse_position(self, x: float, y: float) -> None:
        """Set cursor position for active backend window."""
        if self.backend == "pygame":
            self._pygame.mouse.set_pos((x, y))
            return
        self._glfw.set_cursor_pos(self._glfw_window, float(x), float(y))
        self._glfw_mouse_position = (float(x), float(y))

    def __enter__(self):
        """Enter context manager and return this Screen instance."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Exit context manager by closing window/resources."""
        self.close()
        return False
