from types import SimpleNamespace

import pytest

pygame = pytest.importorskip("pygame")

from tachypy.responses import ResponseHandler


def test_quit_escape_mouse_and_clear_paths(monkeypatch):
    events = [
        SimpleNamespace(type=pygame.QUIT),
        SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_ESCAPE),
        SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(1, 2)),
        SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(3, 4)),
    ]
    monkeypatch.setattr("tachypy.responses.pygame.event.get", lambda: events)
    monkeypatch.setattr("tachypy.responses.pygame.event.clear", lambda: None)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (11, 22))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (True, False, True))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.set_pos", lambda pos: None)

    h = ResponseHandler(keys_to_listen=[pygame.K_ESCAPE, "spacebar"], screen=SimpleNamespace(backend="pygame"))
    h.get_events()
    assert h.should_quit() is True
    assert len(h.get_mouse_clicks()) == 2
    h.set_position(7, 8)
    assert h.get_mouse_position() == (7, 8)
    h.clear_events()
    assert h.get_key_presses() == []
    assert h.get_mouse_clicks() == []
    assert h.should_quit() is False


def test_glfw_release_and_missing_screen_error():
    h = ResponseHandler(screen=SimpleNamespace(backend="glfw"))
    with pytest.raises(RuntimeError, match="requires `screen`"):
        h.screen = None
        h.get_events()

    class FakeScreen:
        backend = "glfw"

        def __init__(self):
            self.pressed = {"space"}
            self.down = {"space"}

        def should_close(self):
            return False

        def was_key_pressed(self, key):
            return key in self.pressed

        def is_key_down(self, key):
            return key in self.down

    s = FakeScreen()
    h = ResponseHandler(screen=s, keys_to_listen=["space"])
    h.get_events()
    assert h.was_key_pressed("space")
    s.pressed = set()
    s.down = set()
    h.get_events()
    assert "space" in h.key_up_events
