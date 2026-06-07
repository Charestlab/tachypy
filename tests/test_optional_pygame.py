from types import SimpleNamespace

import pytest

from tachypy.responses import ResponseHandler


def test_pygame_backend_requires_pygame_when_missing(monkeypatch):
    import tachypy.responses as responses_module

    monkeypatch.setattr(responses_module, "pygame", None)
    handler = ResponseHandler(screen=SimpleNamespace(backend="pygame"))

    with pytest.raises(RuntimeError, match="tachypy\\[pygame\\]"):
        handler.get_events()


def test_glfw_mouse_events_do_not_require_pygame(monkeypatch):
    import tachypy.responses as responses_module

    monkeypatch.setattr(responses_module, "pygame", None)

    class FakeScreen:
        backend = "glfw"

        def should_close(self):
            return False

        def was_key_pressed(self, key):
            return False

        def is_key_down(self, key):
            return False

        def get_mouse_position(self):
            return (3, 4)

        def is_mouse_button_pressed(self, button):
            return button == 0

        def was_mouse_button_pressed(self, button):
            return button == 0

        def was_mouse_button_released(self, button):
            return False

    handler = ResponseHandler(screen=FakeScreen())
    handler.get_events()

    assert handler.events[0].type == "MOUSEBUTTONDOWN"
    assert handler.events[0].button == 1


def test_glfw_response_handler_registers_listened_keys(monkeypatch):
    import tachypy.responses as responses_module

    monkeypatch.setattr(responses_module, "pygame", None)

    class FakeScreen:
        backend = "glfw"

        def __init__(self):
            self.tracked_keys = []

        def track_keys(self, keys):
            self.tracked_keys.extend(keys)

        def should_close(self):
            return False

        def was_key_pressed(self, key):
            return key == "r"

        def is_key_down(self, key):
            return key == "r"

    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["r"], screen=screen)
    handler.get_events()

    assert screen.tracked_keys == ["r"]
    assert handler.was_key_pressed("r") is True
