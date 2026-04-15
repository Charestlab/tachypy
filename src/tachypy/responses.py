# responses.py
import time

import pygame

class ResponseHandler:
    """
    Process keyboard and mouse input events from Pygame or GLFW screen backend.
    """

    def __init__(self, keys_to_listen=None, screen=None):
        """Create an input handler for pygame events or a GLFW-backed Screen."""
        self.should_exit = False
        self.start_time = time.monotonic_ns()
        self.screen = screen
        self.backend = getattr(screen, "backend", "pygame") if screen is not None else "pygame"

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
        self._default_glfw_keys = ["space", "enter", "kp_enter", "escape", "a"]

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
        """Collect key transition state from a GLFW-backed Screen."""
        self.events = []
        timestamp = (time.monotonic_ns() - self.start_time) / 1e9

        if self.screen is None:
            raise RuntimeError("GLFW ResponseHandler requires `screen` to be provided.")

        if self.screen.should_close() or self.screen.was_key_pressed("escape"):
            self.should_exit = True

        keys_to_probe = self.keys_to_listen if self.keys_to_listen is not None else self._default_glfw_keys
        for key in keys_to_probe:
            key_name = self._normalize_key_name(key)

            if self.screen.was_key_pressed(key):
                self.key_presses.append({
                    'time': timestamp,
                    'type': 'keydown',
                    'key': key_name,
                })
                self.key_down_events.add(key_name)
                self.held_keys.add(key_name)

            is_down = self.screen.is_key_down(key)
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

        self.mouse_position = None
        self.mouse_buttons = [False, False, False]

    def should_quit(self):
        """Return whether a quit signal has been received."""
        return self.should_exit

    def get_key_presses(self):
        """Return recorded key transition events."""
        return self.key_presses

    def is_key_down(self, key_name):
        """Return True when the given key is currently held."""
        if isinstance(key_name, int):
            return key_name in self.held_keycodes
        return self._normalize_key_name(key_name) in self.held_keys

    def was_key_pressed(self, key_name):
        """Return True when the given key transitioned to down this frame."""
        if isinstance(key_name, int):
            return key_name in self.key_down_keycodes
        return self._normalize_key_name(key_name) in self.key_down_events

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
            self.mouse_position = (x, y)
            return
        pygame.mouse.set_pos((x, y))
        self.mouse_position = (x, y)

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
        if self.backend == "pygame":
            pygame.event.clear()
