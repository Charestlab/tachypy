# responses.py
import time
import warnings
from types import SimpleNamespace

try:
    import pygame
except ImportError:  # pragma: no cover - exercised in pygame-free installs.
    pygame = None

class ResponseHandler:
    """
    Process keyboard and mouse input events from Pygame or GLFW screen backend.
    """

    def __init__(self, keys_to_listen=None, screen=None):
        """Create an input handler for pygame events or a GLFW-backed Screen."""
        self.should_exit = False
        self.start_time = time.monotonic_ns()
        self.screen = screen
        self.backend = getattr(screen, "backend", "glfw") if screen is not None else "glfw"

        self.key_presses = []
        self.mouse_clicks = []

        # Per-frame key transitions.
        self.key_down_events = set()
        self.key_up_events = set()
        # Persistent set of currently held keys.
        self.held_keys = set()
        # Keycode mirrors for robust querying across layouts/platforms.
        self.key_down_keycodes = set()
        self.key_up_keycodes = set()
        self.held_keycodes = set()

        self.mouse_position = None
        self.mouse_buttons = [False, False, False]

        self.keys_to_listen = keys_to_listen
        self.events = []
        _default_keys = ["space", "enter", "kp_enter", "escape", "a", "left", "right", "up", "down"]
        initial = keys_to_listen if keys_to_listen is not None else _default_keys
        self._glfw_probed_keys: set = {
            self._normalize_key_name(k) if isinstance(k, str) else k for k in initial
        }
        if self.backend == "glfw" and self.screen is not None and hasattr(self.screen, "track_keys"):
            self.screen.track_keys(self._glfw_probed_keys)

    @staticmethod
    def _normalize_key_name(key_name):
        """Normalize key name aliases into stable canonical names."""
        if not isinstance(key_name, str):
            return key_name
        if key_name == " ":
            return "space"
        normalized = key_name.strip().lower()
        if normalized in {"spacebar"}:
            return "space"
        if normalized in {"esc"}:
            return "escape"
        return normalized

    def _is_listened_key(self, key_name, key_code):
        """Return True when the key should be tracked by this handler."""
        if self.keys_to_listen is None:
            return True

        normalized_name = self._normalize_key_name(key_name)
        normalized_list = {
            self._normalize_key_name(k) if isinstance(k, str) else k for k in self.keys_to_listen
        }
        return (normalized_name in normalized_list) or (key_code in normalized_list)

    def reset_timer(self):
        """Reset the event timestamp origin."""
        self.start_time = time.monotonic_ns()

    def get_events(self):
        """
        Retrieve and process events, updating internal state.
        """
        self.key_down_events.clear()
        self.key_up_events.clear()
        self.key_down_keycodes.clear()
        self.key_up_keycodes.clear()

        if self.backend == "glfw":
            self._get_events_glfw()
            return

        if pygame is None:
            raise RuntimeError("pygame backend requested but pygame is not installed. Install `tachypy[pygame]`.")

        self.events = pygame.event.get()

        for event in self.events:
            timestamp = (time.monotonic_ns() - self.start_time) / 1e9

            if event.type == pygame.QUIT:
                self.should_exit = True

            elif event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                normalized_name = self._normalize_key_name(key_name)
                if self._is_listened_key(key_name, event.key):
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keydown',
                        'key': normalized_name,
                    })
                    self.key_down_events.add(normalized_name)
                    self.held_keys.add(normalized_name)
                    self.key_down_keycodes.add(event.key)
                    self.held_keycodes.add(event.key)

                if event.key == pygame.K_ESCAPE:
                    self.should_exit = True

            elif event.type == pygame.KEYUP:
                key_name = pygame.key.name(event.key)
                normalized_name = self._normalize_key_name(key_name)
                if self._is_listened_key(key_name, event.key):
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keyup',
                        'key': normalized_name,
                    })
                    self.key_up_events.add(normalized_name)
                    self.held_keys.discard(normalized_name)
                    self.key_up_keycodes.add(event.key)
                    self.held_keycodes.discard(event.key)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                button_index = event.button - 1
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mousedown',
                    'button': button_index,
                    'pos': event.pos,
                })

            elif event.type == pygame.MOUSEBUTTONUP:
                button_index = event.button - 1
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mouseup',
                    'button': button_index,
                    'pos': event.pos,
                })

        self.mouse_position = pygame.mouse.get_pos()
        pressed = pygame.mouse.get_pressed()
        self.mouse_buttons = list(pressed[:3])

    def _get_events_glfw(self):
        """Collect key and mouse transition state from a GLFW-backed Screen."""
        self.events = []
        timestamp = (time.monotonic_ns() - self.start_time) / 1e9

        if self.screen is None:
            raise RuntimeError("GLFW ResponseHandler requires `screen` to be provided.")

        if self.screen.should_close() or self.screen.was_key_pressed("escape"):
            self.should_exit = True

        for key_name in self._glfw_probed_keys:
            if self.screen.was_key_pressed(key_name):
                self.key_presses.append({
                    'time': timestamp,
                    'type': 'keydown',
                    'key': key_name,
                })
                self.key_down_events.add(key_name)
                self.held_keys.add(key_name)

            is_down = self.screen.is_key_down(key_name)
            if is_down:
                self.held_keys.add(key_name)
            elif key_name in self.held_keys:
                self.key_presses.append({
                    'time': timestamp,
                    'type': 'keyup',
                    'key': key_name,
                })
                self.key_up_events.add(key_name)
                self.held_keys.discard(key_name)

        get_mouse_position = getattr(self.screen, "get_mouse_position", lambda: None)
        is_mouse_button_pressed = getattr(self.screen, "is_mouse_button_pressed", lambda _b: False)
        was_mouse_button_pressed = getattr(self.screen, "was_mouse_button_pressed", lambda _b: False)
        was_mouse_button_released = getattr(self.screen, "was_mouse_button_released", lambda _b: False)

        self.mouse_position = get_mouse_position()
        self.mouse_buttons = [
            is_mouse_button_pressed(0),
            is_mouse_button_pressed(1),
            is_mouse_button_pressed(2),
        ]
        for button_index in (0, 1, 2):
            button_num = button_index + 1
            if was_mouse_button_pressed(button_index):
                mouse_down = self._make_mouse_event("down", button_num, self.mouse_position)
                self.events.append(mouse_down)
                self.mouse_clicks.append(
                    {
                        "time": timestamp,
                        "type": "mousedown",
                        "button": button_index,
                        "pos": self.mouse_position,
                    }
                )
            if was_mouse_button_released(button_index):
                mouse_up = self._make_mouse_event("up", button_num, self.mouse_position)
                self.events.append(mouse_up)
                self.mouse_clicks.append(
                    {
                        "time": timestamp,
                        "type": "mouseup",
                        "button": button_index,
                        "pos": self.mouse_position,
                    }
                )

    @staticmethod
    def _make_mouse_event(direction, button, position):
        """Return a mouse transition event without requiring pygame in GLFW mode."""
        if pygame is not None:
            event_type = pygame.MOUSEBUTTONDOWN if direction == "down" else pygame.MOUSEBUTTONUP
            return pygame.event.Event(event_type, {"button": button, "pos": position})

        event_type = "MOUSEBUTTONDOWN" if direction == "down" else "MOUSEBUTTONUP"
        return SimpleNamespace(type=event_type, button=button, pos=position)

    def should_quit(self):
        """Return whether a quit signal has been received."""
        return self.should_exit

    def get_key_presses(self):
        """Return recorded key transition events."""
        return self.key_presses

    def _promote_glfw_key(self, normalized_key) -> None:
        """Add a key to the probed set so it receives full tracking from the next frame."""
        self._glfw_probed_keys.add(normalized_key)
        if self.screen is not None and hasattr(self.screen, "track_keys"):
            self.screen.track_keys([normalized_key])

    def is_key_down(self, key_name):
        """Return True when the given key is currently held."""
        if isinstance(key_name, int):
            return key_name in self.held_keycodes
        normalized = self._normalize_key_name(key_name)
        if normalized in self.held_keys:
            return True
        if self.backend == "glfw" and self.screen is not None and normalized not in self._glfw_probed_keys:
            self._promote_glfw_key(normalized)
            result = bool(getattr(self.screen, "is_key_down", lambda k: False)(normalized))
            if result:
                self.held_keys.add(normalized)
            return result
        return False

    def was_key_pressed(self, key_name):
        """Return True when the given key transitioned to down this frame."""
        if isinstance(key_name, int):
            return key_name in self.key_down_keycodes
        normalized = self._normalize_key_name(key_name)
        if normalized in self.key_down_events:
            return True
        if self.backend == "glfw" and self.screen is not None and normalized not in self._glfw_probed_keys:
            self._promote_glfw_key(normalized)
            result = bool(getattr(self.screen, "was_key_pressed", lambda k: False)(normalized))
            if result:
                self.key_down_events.add(normalized)
                self.held_keys.add(normalized)
            return result
        return False

    def get_mouse_position(self):
        """Return the latest mouse position or None if unavailable."""
        return self.mouse_position

    def is_mouse_button_pressed(self, button):
        """Return True when the given mouse button index is pressed."""
        if button < 0 or button >= len(self.mouse_buttons):
            return False
        return self.mouse_buttons[button]

    def get_mouse_clicks(self):
        """Return recorded mouse button transition events."""
        return self.mouse_clicks

    def set_position(self, x, y):
        """Set mouse position (pygame) or tracked logical position (glfw)."""
        if self.backend == "glfw":
            if self.screen is not None and hasattr(self.screen, "set_mouse_position"):
                self.screen.set_mouse_position(x, y)
            self.mouse_position = (x, y)
            return
        if pygame is None:
            raise RuntimeError("pygame backend requested but pygame is not installed. Install `tachypy[pygame]`.")
        pygame.mouse.set_pos((x, y))
        self.mouse_position = (x, y)

    def wait_for_keypress(self, keys=None, timeout=None, screen=None, time_reference_ns=None):
        """Block until one of the listed keys is pressed, keeping the display alive.

        Draws nothing — the caller is responsible for having already presented the
        stimulus before calling this.  The screen is flipped each iteration to
        satisfy the OS event loop and keep timing tight.

        Parameters
        ----------
        keys : list of str | None
            Key names to accept.  None means any key.
        timeout : float | None
            Maximum wait in seconds.  None means wait forever.
        screen : Screen | None
            Screen to flip each frame.  Defaults to ``self.screen``.
        time_reference_ns : int | None
            Nanosecond timestamp used as the RT origin (e.g. ``screen.last_flip_time``
            to measure from stimulus onset).  Defaults to the time of the first flip
            inside this call.

        Returns
        -------
        (key_name, rt_seconds) : (str | None, float)
            ``key_name`` is None on timeout or quit; ``rt_seconds`` is elapsed time
            from ``time_reference_ns`` (or first flip) to the detected keypress.
        """
        if self.backend == "pygame" and keys is not None and self.keys_to_listen is not None:
            listened = {
                self._normalize_key_name(k) if isinstance(k, str) else k
                for k in self.keys_to_listen
            }
            untracked = [k for k in keys if self._normalize_key_name(k) not in listened]
            if untracked:
                warnings.warn(
                    f"wait_for_keypress: pygame backend tracks only keys passed to "
                    f"ResponseHandler at construction. "
                    f"These keys will never be detected: {untracked}. "
                    f"Add them to keys_to_listen=[ ... ] when creating ResponseHandler.",
                    UserWarning,
                    stacklevel=2,
                )

        active_screen = screen if screen is not None else self.screen
        self.clear_events()

        ref_ns = None

        while True:
            if active_screen is not None:
                active_screen.flip()

            if ref_ns is None:
                ref_ns = time_reference_ns if time_reference_ns is not None else time.monotonic_ns()

            self.get_events()

            elapsed = (time.monotonic_ns() - ref_ns) / 1e9

            if self.should_quit():
                return None, elapsed

            if timeout is not None and elapsed >= timeout:
                return None, elapsed

            if keys is None:
                if self.key_down_events:
                    return next(iter(self.key_down_events)), elapsed
            else:
                for key in keys:
                    if self.was_key_pressed(key):
                        return self._normalize_key_name(key), elapsed

    def clear_events(self):
        """Clear tracked key/mouse states and pending framework events."""
        self.key_presses.clear()
        self.mouse_clicks.clear()
        self.key_down_events.clear()
        self.key_up_events.clear()
        self.held_keys.clear()
        self.key_down_keycodes.clear()
        self.key_up_keycodes.clear()
        self.held_keycodes.clear()
        self.should_exit = False
        self.events = []
        if self.backend == "pygame" and pygame is not None:
            pygame.event.clear()
