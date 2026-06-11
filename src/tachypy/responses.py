# responses.py
from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Optional


_GLFW_KEY_MAP = {
    "space": "KEY_SPACE",
    "apostrophe": "KEY_APOSTROPHE",
    "comma": "KEY_COMMA",
    "minus": "KEY_MINUS",
    "period": "KEY_PERIOD",
    "slash": "KEY_SLASH",
    "0": "KEY_0",
    "1": "KEY_1",
    "2": "KEY_2",
    "3": "KEY_3",
    "4": "KEY_4",
    "5": "KEY_5",
    "6": "KEY_6",
    "7": "KEY_7",
    "8": "KEY_8",
    "9": "KEY_9",
    "semicolon": "KEY_SEMICOLON",
    "equal": "KEY_EQUAL",
    "a": "KEY_A",
    "b": "KEY_B",
    "c": "KEY_C",
    "d": "KEY_D",
    "e": "KEY_E",
    "f": "KEY_F",
    "g": "KEY_G",
    "h": "KEY_H",
    "i": "KEY_I",
    "j": "KEY_J",
    "k": "KEY_K",
    "l": "KEY_L",
    "m": "KEY_M",
    "n": "KEY_N",
    "o": "KEY_O",
    "p": "KEY_P",
    "q": "KEY_Q",
    "r": "KEY_R",
    "s": "KEY_S",
    "t": "KEY_T",
    "u": "KEY_U",
    "v": "KEY_V",
    "w": "KEY_W",
    "x": "KEY_X",
    "y": "KEY_Y",
    "z": "KEY_Z",
    "left_bracket": "KEY_LEFT_BRACKET",
    "backslash": "KEY_BACKSLASH",
    "right_bracket": "KEY_RIGHT_BRACKET",
    "grave_accent": "KEY_GRAVE_ACCENT",
    "world_1": "KEY_WORLD_1",
    "world_2": "KEY_WORLD_2",
    "escape": "KEY_ESCAPE",
    "esc": "KEY_ESCAPE",
    "enter": "KEY_ENTER",
    "return": "KEY_ENTER",
    "tab": "KEY_TAB",
    "backspace": "KEY_BACKSPACE",
    "insert": "KEY_INSERT",
    "delete": "KEY_DELETE",
    "right": "KEY_RIGHT",
    "left": "KEY_LEFT",
    "down": "KEY_DOWN",
    "up": "KEY_UP",
    "page_up": "KEY_PAGE_UP",
    "page_down": "KEY_PAGE_DOWN",
    "home": "KEY_HOME",
    "end": "KEY_END",
    "caps_lock": "KEY_CAPS_LOCK",
    "scroll_lock": "KEY_SCROLL_LOCK",
    "num_lock": "KEY_NUM_LOCK",
    "print_screen": "KEY_PRINT_SCREEN",
    "pause": "KEY_PAUSE",
    "f1": "KEY_F1",
    "f2": "KEY_F2",
    "f3": "KEY_F3",
    "f4": "KEY_F4",
    "f5": "KEY_F5",
    "f6": "KEY_F6",
    "f7": "KEY_F7",
    "f8": "KEY_F8",
    "f9": "KEY_F9",
    "f10": "KEY_F10",
    "f11": "KEY_F11",
    "f12": "KEY_F12",
    "f13": "KEY_F13",
    "f14": "KEY_F14",
    "f15": "KEY_F15",
    "f16": "KEY_F16",
    "f17": "KEY_F17",
    "f18": "KEY_F18",
    "f19": "KEY_F19",
    "f20": "KEY_F20",
    "f21": "KEY_F21",
    "f22": "KEY_F22",
    "f23": "KEY_F23",
    "f24": "KEY_F24",
    "f25": "KEY_F25",
    "kp_0": "KEY_KP_0",
    "kp_1": "KEY_KP_1",
    "kp_2": "KEY_KP_2",
    "kp_3": "KEY_KP_3",
    "kp_4": "KEY_KP_4",
    "kp_5": "KEY_KP_5",
    "kp_6": "KEY_KP_6",
    "kp_7": "KEY_KP_7",
    "kp_8": "KEY_KP_8",
    "kp_9": "KEY_KP_9",
    "kp_decimal": "KEY_KP_DECIMAL",
    "kp_divide": "KEY_KP_DIVIDE",
    "kp_multiply": "KEY_KP_MULTIPLY",
    "kp_subtract": "KEY_KP_SUBTRACT",
    "kp_add": "KEY_KP_ADD",
    "kp_enter": "KEY_KP_ENTER",
    "kp_equal": "KEY_KP_EQUAL",
    "left_shift": "KEY_LEFT_SHIFT",
    "left_ctrl": "KEY_LEFT_CONTROL",
    "left_alt": "KEY_LEFT_ALT",
    "left_super": "KEY_LEFT_SUPER",
    "right_shift": "KEY_RIGHT_SHIFT",
    "right_ctrl": "KEY_RIGHT_CONTROL",
    "right_alt": "KEY_RIGHT_ALT",
    "right_super": "KEY_RIGHT_SUPER",
    "menu": "KEY_MENU",
}


class ResponseHandler:
    """Poll a GLFW-backed Screen and track participant keyboard/mouse responses."""

    def __init__(self, keys_to_listen=None, screen=None):
        """Create an input handler bound to a GLFW-backed ``Screen``."""
        if screen is None:
            raise ValueError("ResponseHandler requires a Screen instance: ResponseHandler(screen=screen).")
        self.screen = screen
        self.backend = getattr(screen, "backend", "glfw")
        if self.backend != "glfw":
            raise ValueError("ResponseHandler supports only the GLFW backend.")

        self._glfw = getattr(screen, "_glfw", None)
        self._window = getattr(screen, "_glfw_window", getattr(screen, "screen", None))
        if self._glfw is None or self._window is None:
            raise RuntimeError("ResponseHandler requires a GLFW Screen with an initialized window.")

        self.should_exit = False
        self.start_time = time.monotonic_ns()
        self.keys_to_listen = keys_to_listen
        self.events = []
        self.key_presses = []
        self.mouse_clicks = []
        self.key_down_events = set()
        self.key_up_events = set()
        self.held_keys = set()
        self.key_down_keycodes = set()
        self.key_up_keycodes = set()
        self.held_keycodes = set()
        self.mouse_position = None
        self.mouse_buttons = [False, False, False]
        self.mouse_down_events = set()
        self.mouse_up_events = set()
        self._prev_key_state = {}
        self._curr_key_state = {}
        self._prev_mouse_state = {}
        self._curr_mouse_state = {}

        default_keys = ["space", "enter", "kp_enter", "escape", "a", "left", "right", "up", "down"]
        initial = keys_to_listen if keys_to_listen is not None else default_keys
        self._probed_keys = {self._normalize_key_name(k) if isinstance(k, str) else k for k in initial}

    @staticmethod
    def _normalize_key_name(key_name):
        """Normalize key aliases into stable canonical names."""
        if not isinstance(key_name, str):
            return key_name
        if key_name == " ":
            return "space"
        normalized = key_name.strip().lower()
        if normalized == "spacebar":
            return "space"
        if normalized == "esc":
            return "escape"
        return normalized

    def _glfw_keycode(self, key) -> Optional[int]:
        """Map a key name or keycode to a GLFW keycode."""
        if isinstance(key, int):
            return key
        key_name = self._normalize_key_name(key)
        attr = _GLFW_KEY_MAP.get(key_name)
        if attr is None:
            return None
        return getattr(self._glfw, attr, None)

    def _mouse_button_code(self, button_index: int) -> Optional[int]:
        mapping = {
            0: getattr(self._glfw, "MOUSE_BUTTON_LEFT", None),
            1: getattr(self._glfw, "MOUSE_BUTTON_MIDDLE", None),
            2: getattr(self._glfw, "MOUSE_BUTTON_RIGHT", None),
        }
        return mapping.get(int(button_index))

    def reset_timer(self):
        """Reset the event timestamp origin."""
        self.start_time = time.monotonic_ns()

    def get_events(self):
        """Poll the screen event pump and update response state snapshots."""
        self.key_down_events.clear()
        self.key_up_events.clear()
        self.key_down_keycodes.clear()
        self.key_up_keycodes.clear()
        self.mouse_down_events.clear()
        self.mouse_up_events.clear()
        self.events = []

        poll_events = getattr(self.screen, "poll_events", None)
        if not callable(poll_events):
            raise RuntimeError("ResponseHandler requires screen.poll_events().")
        poll_events()

        timestamp = (time.monotonic_ns() - self.start_time) / 1e9
        if self._screen_should_close() or self._query_key_down("escape"):
            if self._query_key_pressed("escape"):
                self._record_key_down("escape", self._glfw_keycode("escape"), timestamp)
            self.should_exit = True

        self._update_key_state(timestamp)
        self._update_mouse_state(timestamp)

    def _screen_should_close(self) -> bool:
        should_close = getattr(self.screen, "should_close", None)
        if callable(should_close):
            return bool(should_close())
        return bool(self._glfw.window_should_close(self._window))

    def _query_key_down(self, key) -> bool:
        code = self._glfw_keycode(key)
        if code is None:
            return False
        return bool(self._glfw.get_key(self._window, code) == self._glfw.PRESS)

    def _query_key_pressed(self, key) -> bool:
        code = self._glfw_keycode(key)
        if code is None:
            return False
        return bool(self._curr_key_state.get(code, False) and not self._prev_key_state.get(code, False))

    def _record_key_down(self, key_name, key_code, timestamp) -> None:
        normalized = self._normalize_key_name(key_name)
        self.key_presses.append({"time": timestamp, "type": "keydown", "key": normalized})
        self.key_down_events.add(normalized)
        self.held_keys.add(normalized)
        if key_code is not None:
            self.key_down_keycodes.add(key_code)
            self.held_keycodes.add(key_code)

    def _record_key_up(self, key_name, key_code, timestamp) -> None:
        normalized = self._normalize_key_name(key_name)
        self.key_presses.append({"time": timestamp, "type": "keyup", "key": normalized})
        self.key_up_events.add(normalized)
        self.held_keys.discard(normalized)
        if key_code is not None:
            self.key_up_keycodes.add(key_code)
            self.held_keycodes.discard(key_code)

    def _update_key_state(self, timestamp) -> None:
        self._prev_key_state, self._curr_key_state = self._curr_key_state, {}
        for key_name in sorted(self._probed_keys, key=str):
            code = self._glfw_keycode(key_name)
            if code is None:
                continue
            is_down = self._glfw.get_key(self._window, code) == self._glfw.PRESS
            was_down = self._prev_key_state.get(code, False)
            self._curr_key_state[code] = bool(is_down)
            if is_down and not was_down:
                self._record_key_down(key_name, code, timestamp)
            elif was_down and not is_down:
                self._record_key_up(key_name, code, timestamp)
            elif is_down:
                self.held_keys.add(self._normalize_key_name(key_name))
                self.held_keycodes.add(code)

    def _update_mouse_state(self, timestamp) -> None:
        self._prev_mouse_state, self._curr_mouse_state = self._curr_mouse_state, {}
        cursor_x, cursor_y = self._glfw.get_cursor_pos(self._window)
        self.mouse_position = (float(cursor_x), float(cursor_y))

        self.mouse_buttons = []
        for button_index in (0, 1, 2):
            code = self._mouse_button_code(button_index)
            is_down = False if code is None else self._glfw.get_mouse_button(self._window, code) == self._glfw.PRESS
            was_down = self._prev_mouse_state.get(code, False)
            self._curr_mouse_state[code] = bool(is_down)
            self.mouse_buttons.append(bool(is_down))
            if is_down and not was_down:
                self.mouse_down_events.add(button_index)
                self._append_mouse_event("down", button_index, timestamp)
            elif was_down and not is_down:
                self.mouse_up_events.add(button_index)
                self._append_mouse_event("up", button_index, timestamp)

    def _append_mouse_event(self, direction, button_index, timestamp) -> None:
        event_type = "MOUSEBUTTONDOWN" if direction == "down" else "MOUSEBUTTONUP"
        event = SimpleNamespace(type=event_type, button=button_index + 1, pos=self.mouse_position)
        self.events.append(event)
        self.mouse_clicks.append(
            {
                "time": timestamp,
                "type": "mousedown" if direction == "down" else "mouseup",
                "button": button_index,
                "pos": self.mouse_position,
            }
        )

    def should_quit(self):
        """Return whether a quit signal has been received."""
        return self.should_exit

    def get_key_presses(self):
        """Return recorded key transition events."""
        return self.key_presses

    def _promote_key(self, normalized_key) -> Optional[int]:
        self._probed_keys.add(normalized_key)
        code = self._glfw_keycode(normalized_key)
        if code is not None and code not in self._curr_key_state:
            self._curr_key_state[code] = self._query_key_down(normalized_key)
        return code

    def is_key_down(self, key_name):
        """Return True when the given key is currently held."""
        normalized = self._normalize_key_name(key_name)
        code = self._glfw_keycode(normalized)
        if code is None:
            return False
        if normalized not in self._probed_keys:
            code = self._promote_key(normalized)
        result = bool(self._curr_key_state.get(code, False) or self._query_key_down(normalized))
        if result:
            self.held_keys.add(normalized)
            self.held_keycodes.add(code)
        return result

    def was_key_pressed(self, key_name):
        """Return True when the given key transitioned to down this frame."""
        normalized = self._normalize_key_name(key_name)
        code = self._glfw_keycode(normalized)
        if code is None:
            return False
        if normalized not in self._probed_keys:
            code = self._promote_key(normalized)
            if self._curr_key_state.get(code, False) and not self._prev_key_state.get(code, False):
                self.key_down_events.add(normalized)
                self.held_keys.add(normalized)
        return normalized in self.key_down_events or code in self.key_down_keycodes

    def get_mouse_position(self):
        """Return the latest mouse position or None if unavailable."""
        return self.mouse_position

    def is_mouse_button_pressed(self, button):
        """Return True when the given mouse button index is pressed."""
        if button < 0 or button >= len(self.mouse_buttons):
            return False
        return bool(self.mouse_buttons[button])

    def was_mouse_button_pressed(self, button):
        """Return True when the mouse button transitioned to down this frame."""
        return int(button) in self.mouse_down_events

    def was_mouse_button_released(self, button):
        """Return True when the mouse button transitioned to up this frame."""
        return int(button) in self.mouse_up_events

    def get_mouse_clicks(self):
        """Return recorded mouse button transition events."""
        return self.mouse_clicks

    def set_position(self, x, y):
        """Set the cursor position in the GLFW window and local state."""
        self._glfw.set_cursor_pos(self._window, float(x), float(y))
        self.mouse_position = (float(x), float(y))

    def wait_for_keypress(self, keys=None, timeout=None, screen=None, time_reference_ns=None):
        """Block until one of the listed keys is pressed, keeping the display alive."""
        active_screen = screen if screen is not None else self.screen
        self.clear_events()
        if keys is not None:
            for key in keys:
                self._probed_keys.add(self._normalize_key_name(key))

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
        """Clear tracked transition events while preserving held-state snapshots."""
        self.key_presses.clear()
        self.mouse_clicks.clear()
        self.key_down_events.clear()
        self.key_up_events.clear()
        self.key_down_keycodes.clear()
        self.key_up_keycodes.clear()
        self.mouse_down_events.clear()
        self.mouse_up_events.clear()
        self.should_exit = False
        self.events = []
