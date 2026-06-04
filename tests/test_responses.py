from types import SimpleNamespace

import pytest

pygame = pytest.importorskip("pygame")

from tachypy.responses import ResponseHandler


def test_is_key_down_tracks_held_keys_across_frames(monkeypatch):
    event_batches = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a)],
        [],
        [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_a)],
    ]

    def fake_get():
        if event_batches:
            return event_batches.pop(0)
        return []

    monkeypatch.setattr("tachypy.responses.pygame.event.get", fake_get)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (100, 200))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (False, False, False))

    handler = ResponseHandler(screen=SimpleNamespace(backend="pygame"))

    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is True

    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is False

    handler.get_events()
    assert handler.is_key_down("a") is False


def test_keys_to_listen_filters_untracked_keys(monkeypatch):
    events = [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_b)]

    monkeypatch.setattr("tachypy.responses.pygame.event.get", lambda: events)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (0, 0))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (True, False, False))

    handler = ResponseHandler(keys_to_listen=["a"], screen=SimpleNamespace(backend="pygame"))
    handler.get_events()

    assert handler.get_key_presses() == []
    assert handler.is_key_down("b") is False
    assert handler.is_mouse_button_pressed(0) is True
    assert handler.is_mouse_button_pressed(3) is False


def test_space_detection_works_with_keycode_and_name_aliases(monkeypatch):
    events = [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_SPACE)]

    monkeypatch.setattr("tachypy.responses.pygame.event.get", lambda: events)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (0, 0))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (False, False, False))
    # Simulate a platform/layout returning a literal space for key name.
    monkeypatch.setattr(
        "tachypy.responses.pygame.key.name",
        lambda key: " " if key == pygame.K_SPACE else "unknown",
    )

    handler = ResponseHandler(screen=SimpleNamespace(backend="pygame"))
    handler.get_events()

    assert handler.was_key_pressed("space") is True
    assert handler.is_key_down("space") is True
    assert handler.was_key_pressed(pygame.K_SPACE) is True
    assert handler.is_key_down(pygame.K_SPACE) is True


def test_glfw_mode_tracks_keys_without_pygame_event_queue():
    class FakeScreen:
        backend = "glfw"

        def __init__(self):
            self.down = {"space"}
            self.pressed = {"space"}
            self.mouse_down = {0}
            self.mouse_pressed = {0}
            self.mouse_released = set()
            self.mouse_pos = (10, 20)

        def should_close(self):
            return False

        def was_key_pressed(self, key):
            return key in self.pressed

        def is_key_down(self, key):
            return key in self.down

        def get_mouse_position(self):
            return self.mouse_pos

        def is_mouse_button_pressed(self, button):
            return button in self.mouse_down

        def was_mouse_button_pressed(self, button):
            return button in self.mouse_pressed

        def was_mouse_button_released(self, button):
            return button in self.mouse_released

        def set_mouse_position(self, x, y):
            self.mouse_pos = (x, y)

    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    handler.get_events()

    assert handler.was_key_pressed("space") is True
    assert handler.is_key_down("space") is True
    assert handler.get_mouse_position() == (10, 20)
    assert handler.is_mouse_button_pressed(0) is True
    assert any(ev.type == pygame.MOUSEBUTTONDOWN for ev in handler.events)
