class FakeGlfw:
    PRESS = 1
    RELEASE = 0
    KEY_SPACE = 32
    KEY_ENTER = 257
    KEY_KP_ENTER = 335
    KEY_ESCAPE = 256
    KEY_A = 65
    KEY_B = 66
    KEY_F1 = 290
    KEY_F2 = 291
    KEY_LEFT = 263
    KEY_RIGHT = 262
    KEY_UP = 265
    KEY_DOWN = 264
    KEY_R = 82
    MOUSE_BUTTON_LEFT = 0
    MOUSE_BUTTON_MIDDLE = 1
    MOUSE_BUTTON_RIGHT = 2
    CURSOR = 0
    CURSOR_HIDDEN = 1
    CURSOR_NORMAL = 2

    def __init__(self):
        self.down_keys = set()
        self.mouse_down = set()
        self.cursor_pos = (0, 0)
        self.closed = False
        self.poll_count = 0
        self.cursor_modes = []
        self.swap_count = 0

    def get_key(self, window, key):
        return self.PRESS if key in self.down_keys else self.RELEASE

    def get_mouse_button(self, window, button):
        return self.PRESS if button in self.mouse_down else self.RELEASE

    def get_cursor_pos(self, window):
        return self.cursor_pos

    def set_cursor_pos(self, window, x, y):
        self.cursor_pos = (float(x), float(y))

    def poll_events(self):
        self.poll_count += 1

    def window_should_close(self, window):
        return self.closed

    def set_input_mode(self, window, mode, value):
        self.cursor_modes.append((mode, value))

    def swap_buffers(self, window):
        self.swap_count += 1

    def get_window_size(self, window):
        return (800, 600)

    def get_framebuffer_size(self, window):
        return (800, 600)

    def terminate(self):
        pass

    def destroy_window(self, window):
        pass


class FakeScreen:
    backend = "glfw"

    def __init__(self):
        self._glfw = FakeGlfw()
        self._glfw_window = "window"
        self.screen = self._glfw_window
        self.flip_count = 0

    def poll_events(self):
        self._glfw.poll_events()

    def should_close(self):
        return self._glfw.window_should_close(self._glfw_window)

    def flip(self):
        self.flip_count += 1
