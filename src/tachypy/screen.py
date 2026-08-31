"""Display and timing utilities for TachyPy with pluggable backends."""

from time import monotonic_ns, sleep
from typing import Callable, Optional, Sequence, Tuple

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

from tachypy._warnings import warn_once

_WARMUP_COLOR = (128, 128, 128)


def get_render_interval(screen) -> float:
    """Return the frame interval used by TachyPy's visual loops.

    The rate is selected as follows:

    * VSync on: use the monitor's highest reported rate at the current
      resolution, not just whatever the *current* mode happens to report
      (adaptive-refresh displays, e.g. ProMotion, can otherwise get stuck
      pacing to a transient idle rate).
    * VSync off:

      * with ``desired_refresh_rate``: use the desired rate;
      * without it: use the same max-at-resolution rate, then 60 Hz.
      * ``desired_refresh_rate <= 0`` requests unthrottled ``flip()``
        timing (see :class:`Screen`), which a scheduled loop like
        :class:`LoopPacer` can't represent (it needs a positive interval to
        pace against); it falls back to the same max-at-resolution rate,
        then 60 Hz, with a warning.

    The interval only schedules loop updates. VSync controls presentation
    synchronization; manual pacing does not.
    """
    rate = getattr(screen, "_max_mode_refresh_rate", None)
    if not getattr(screen, "vsync", True):
        desired = getattr(screen, "desired_refresh_rate", None)
        if desired is not None and desired <= 0:
            warn_once(
                "LoopPacer render interval",
                f"desired_refresh_rate={desired} requests unthrottled flip() timing, "
                f"but this scheduled render loop needs a positive rate to pace "
                f"against; using {rate or 60.0:g} Hz instead."
                "\n\t\tPass a positive desired_refresh_rate to pace this loop "
                "to a specific rate.",
            )
        else:
            rate = desired or rate
    rate = 60.0 if rate is None else float(rate)
    if rate <= 0:
        raise ValueError("the render rate must be positive")
    return 1.0 / rate


class LoopPacer:
    """Pace rendering and input polling on independent schedules.

    Render deadlines stay phase-locked instead of accumulating loop overhead.
    ``render_due`` and ``wait`` are independent so a caller can draw one last
    frame and return without going through the poll wait.
    """

    def __init__(
        self, screen, wait_until: Callable[[float], None], start: float,
        *, poll_interval: float = 1.0 / 1000.0, defer_first_render: bool = False,
    ):
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self._wait_until = wait_until
        self.frame_interval = get_render_interval(screen)
        self.poll_interval = poll_interval
        # Request the render slightly early so flip()'s VSync block lands on time.
        self._render_lead = (
            min(poll_interval, self.frame_interval / 4)
            if getattr(screen, "vsync", True)
            else 0.0
        )
        render_delay = max(0.0, self.frame_interval - self._render_lead)
        self._next_render = start + render_delay if defer_first_render else start
        self._next_poll = start + poll_interval
        self.late_renders = 0

    def render_due(self, now: float) -> bool:
        """Return whether a frame is due, advancing the render schedule if so.

        Also tracks ``late_renders``: the number of consecutive renders that
        missed their scheduled slot by a full frame_interval or more (e.g. a
        slow ``draw()`` call), reset to 0 the moment a render is on time.
        """
        if now < self._next_render:
            return False
        if now - self._next_render >= self.frame_interval:
            self.late_renders += 1
        else:
            self.late_renders = 0
        elapsed_slots = int((now - self._next_render) / self.frame_interval) + 1
        self._next_render += elapsed_slots * self.frame_interval
        return True

    def after_render(self, now: float) -> None:
        """Anchor the next render deadline to a completed buffer swap."""
        delay = max(0.0, self.frame_interval - self._render_lead)
        self._next_render = now + delay

    def wait(self, now: float) -> None:
        """Wait for the next polling slot or render deadline, whichever is first.

        A missed polling slot is skipped rather than caught up on, since a
        back-to-back catch-up read can't recover a sample that was never
        acquired at the time it was due.
        """
        if self._next_poll <= now:
            elapsed_slots = int((now - self._next_poll) / self.poll_interval) + 1
            self._next_poll += elapsed_slots * self.poll_interval
        self._wait_until(min(self._next_poll, self._next_render))


class Screen:
    """Create and manage a GLFW/OpenGL display for TachyPy experiments.

    Usage and timing:

    * Draw objects, call :meth:`flip` to present the frame, and use :meth:`fill`
      to clear the display.
    * VSync is enabled by default and recommended for experiments.
    * With VSync on, TachyPy paces to the monitor's highest reported rate at
      the current resolution; this is not a measurement of photon onset.
    * A ``desired_refresh_rate`` above that rate produces a warning.
    * With VSync off, ``desired_refresh_rate`` manually paces frames but does
      not synchronize them to the display and may cause tearing.

    Examples
    --------
    The usual setup is simply::

        screen = Screen()
        screen.fill((127, 127, 127))
        stimulus.draw()
        timestamp = screen.flip()

    For explicit manual pacing::

        screen = Screen(vsync=False, desired_refresh_rate=60)

    Parameters
    ----------
    screen_number : int, default=0
        Index of the monitor to use, following GLFW's monitor order.
    width, height : int, optional
        Window dimensions. When omitted, the selected monitor's dimensions are
        used.
    fullscreen : bool, default=True
        Whether to create a fullscreen window.
    vsync : bool, default=True
        Synchronize buffer swaps with the monitor's refresh cycle. This is the
        recommended setting for experiments.
    desired_refresh_rate : int, optional
        Manual pacing rate used only when ``vsync=False``. ``0`` or a negative
        value explicitly disables manual pacing (``flip()`` is left
        unthrottled), which ``None`` does not — an unset rate falls back to
        the monitor's highest reported rate at the current resolution, then
        60 Hz. When VSync is enabled, TachyPy warns if this value exceeds
        that rate but does not use it to change presentation timing.
        A scheduled loop (:class:`LoopPacer`, used by
        :func:`~tachypy.scrollbar_interaction.run_slider_interaction`) can't
        run unthrottled -- ``0``/negative falls back to the same rate as an
        unset one there instead, with a warning.
    grab_input : bool, default=True
        Whether GLFW captures the mouse inside the window.
    backend : str, default="glfw"
        Display backend. Only ``"glfw"`` is supported.
    warmup_frames : int, default=60
        Number of neutral frames presented before the experiment begins.

    Attributes
    ----------
    mouse_visible : bool
        Whether TachyPy currently considers the mouse cursor visible.
    content_scale : float
        Framebuffer-to-window scale factor. Pass it to text and widget objects
        that support HiDPI rendering.
    """

    def __init__(
        self,
        screen_number: int = 0,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fullscreen: bool = True,
        vsync: bool = True,
        desired_refresh_rate: Optional[int] = None,
        grab_input: bool = True,
        backend: str = "glfw",
        warmup_frames: int = 60,
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
        self.desired_refresh_rate = None if desired_refresh_rate is None else int(desired_refresh_rate)
        self.grab_input = bool(grab_input)
        self.warmup_frames = int(warmup_frames)
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
        self.content_scale: float = 1.0
        # Refresh rate reported by the active GLFW monitor mode.
        self._mode_refresh_rate: Optional[float] = None
        # Highest refresh rate reported across the selected monitor's video modes.
        self._max_mode_refresh_rate: Optional[float] = None

        self._init_glfw_backend(screen_number)
        self._warn_if_requested_rate_exceeds_display()
        self._warn_if_mode_refresh_rate_unknown()
        self._init_opengl_state()
        self._warm_up_display()

    @staticmethod
    def _monitor_name(glfw_module, monitor) -> str:
        """Return a decoded, human-readable monitor name."""
        name = glfw_module.get_monitor_name(monitor) or b"unknown"
        return name.decode("utf-8", errors="replace") if isinstance(name, bytes) else name

    @staticmethod
    def _video_mode_rate(video_mode) -> Optional[float]:
        """Return a GLFW video mode's refresh rate, across binding attribute-name variants."""
        rate = getattr(video_mode, "refresh_rate", None) or getattr(video_mode, "refreshRate", None)
        return float(rate) if rate else None

    @staticmethod
    def _max_refresh_rate(glfw_module, monitor, width=None, height=None) -> Optional[float]:
        """Return the highest refresh rate across a monitor's video modes, preferring ``width``/``height`` if given."""
        matching, all_rates = [], []
        for video_mode in glfw_module.get_video_modes(monitor) or []:
            rate = Screen._video_mode_rate(video_mode)
            if rate is None:
                continue
            all_rates.append(rate)
            size = getattr(video_mode, "size", None)
            if width is not None and size is not None and (int(size.width), int(size.height)) == (int(width), int(height)):
                matching.append(rate)
        return max(matching) if matching else (max(all_rates) if all_rates else None)

    @staticmethod
    def _describe_monitors(glfw_module, monitors) -> str:
        """Return an indented 'index: name (up to N Hz)' listing of monitors."""
        lines = []
        for i, monitor in enumerate(monitors):
            name = Screen._monitor_name(glfw_module, monitor)
            max_rate = Screen._max_refresh_rate(glfw_module, monitor)
            rate_text = f"up to {max_rate:g} Hz" if max_rate else "refresh rate unknown"
            lines.append(f"\t\t  {i}: {name} ({rate_text})")
        return "\n".join(lines)

    @staticmethod
    def _clamp_screen_number(screen_number: int, glfw_module, monitors) -> int:
        """Return a valid monitor index, warning if the requested one is out of range."""
        safe = max(0, int(screen_number))
        if int(screen_number) < 0 or safe >= len(monitors):
            listing = Screen._describe_monitors(glfw_module, monitors)
            warn_once(
                "Screen initialization",
                f"screen_number={screen_number} is outside the available monitor range "
                f"(0-{len(monitors) - 1}); "
                f"using monitor 0.\n\t\tDetected monitors:\n{listing}",
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

    def _warn_if_requested_rate_exceeds_display(self) -> None:
        """Warn when the display cannot meet an explicitly requested rate."""
        requested = self.desired_refresh_rate
        actual = self._max_mode_refresh_rate
        if requested and actual and actual < requested:
            mode = "VSync is enabled" if self.vsync else "VSync is disabled"
            advice = (
                "\n\t\tThis is the highest rate this monitor reports at its current "
                "resolution, across all its modes."
                "\n\t\tLower desired_refresh_rate, or change resolution/refresh rate in "
                "your OS display settings if you expected higher."
            )
            warn_once(
                "Screen initialization",
                f"{mode}, but this monitor supports at most {actual:g} Hz; "
                f"the requested {requested:g} Hz cannot be fully presented.{advice}",
            )

    def _warn_if_mode_refresh_rate_unknown(self) -> None:
        """Warn when GLFW couldn't report any refresh rate, forcing a 60 Hz guess.

        Skipped when ``vsync=False`` with ``desired_refresh_rate`` set, since
        that value is used instead of the guess.
        """
        if self._max_mode_refresh_rate is not None:
            return
        if not self.vsync and self.desired_refresh_rate:
            return
        advice = (
            "\n\t\tTachyPy cannot verify the true rate and will pace to a conservative"
            " 60 Hz guess (guessing too high risks stalling input polling while a frame"
            " blocks on the real, slower VSync)."
            "\n\t\tPass desired_refresh_rate explicitly (with vsync=False) if you know "
            "the real rate."
        )
        warn_once(
            "Screen initialization",
            f"GLFW could not report a refresh rate for this display, in the current "
            f"mode or any other.{advice}",
        )

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

        safe_screen_number = Screen._clamp_screen_number(screen_number, glfw, monitors)
        monitor = monitors[safe_screen_number]
        self.monitor = monitor

        mode = glfw.get_video_mode(monitor)
        if mode is None:
            glfw.terminate()
            raise RuntimeError("Unable to read monitor video mode.")

        self._mode_refresh_rate = Screen._video_mode_rate(mode)
        self._max_mode_refresh_rate = Screen._max_refresh_rate(glfw, monitor, mode.size.width, mode.size.height)

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
            self.fill(_WARMUP_COLOR)
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
        """Limit frame updates when VSync is disabled."""
        if self.vsync:
            return
        if self.desired_refresh_rate is not None and self.desired_refresh_rate <= 0:
            return  # explicit 0 (or negative) disables manual pacing
        rate = self.desired_refresh_rate or self._max_mode_refresh_rate or 60.0

        now = monotonic_ns()
        if self._last_tick_time_ns is None:
            self._last_tick_time_ns = now
            return

        target_frame_ns = int(1e9 / rate)
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
            # Without this, some platforms (e.g. macOS) stop blocking flip() for VSync.
            self.poll_events()
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
        self.content_scale = float(fb_h) / float(win_h) if win_h > 0 else 1.0

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
