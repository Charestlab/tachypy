from types import SimpleNamespace

import pytest

from tachypy.draggable import Draggable, DraggableManager
from tachypy.responses import ResponseHandler


class Target:
    def __init__(self, bounds=(0, 0, 10, 10)):
        self.x1, self.y1, self.x2, self.y2 = bounds
        self.draw_count = 0
        self.moves = []

    def draw(self):
        self.draw_count += 1

    def hit_test(self, x, y):
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def move_by(self, dx, dy):
        self.moves.append((dx, dy))
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def get_bounds(self):
        return self.x1, self.y1, self.x2, self.y2


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


def test_draggable_draw_and_glfw_drag_without_pygame(monkeypatch):
    import tachypy.draggable as draggable_module

    monkeypatch.setattr(draggable_module, "pygame", None)

    class FakeScreen:
        backend = "glfw"

        def __init__(self):
            self.mouse_pos = (5, 5)
            self.mouse_down = {0}
            self.mouse_pressed = {0}
            self.mouse_released = set()
            self.set_positions = []

        def get_mouse_position(self):
            return self.mouse_pos

        def is_mouse_button_pressed(self, button):
            return button in self.mouse_down

        def was_mouse_button_pressed(self, button):
            return button in self.mouse_pressed

        def was_mouse_button_released(self, button):
            return button in self.mouse_released

        def set_mouse_position(self, x, y):
            self.set_positions.append((x, y))
            self.mouse_pos = (x, y)

    target = Target((0, 0, 10, 10))
    draggable = Draggable(target)
    manager = DraggableManager(button_index=0)
    manager.add(draggable)
    manager.draw()
    assert target.draw_count == 1

    screen = FakeScreen()
    response = SimpleNamespace(backend="glfw", screen=screen)
    manager.update_from_response(response)

    assert manager.active is draggable
    assert draggable.dragging is True
    assert screen.set_positions == [(5, 5)]

    screen.mouse_pressed = set()
    screen.mouse_pos = (20, 15)
    manager.update_from_response(response)

    assert target.get_bounds() == (15, 10, 25, 20)

    screen.mouse_down = set()
    screen.mouse_released = {0}
    manager.update_from_response(response)

    assert manager.active is None
    assert draggable.dragging is False


def test_draggable_glfw_clamps_to_bounds_without_pygame(monkeypatch):
    import tachypy.draggable as draggable_module

    monkeypatch.setattr(draggable_module, "pygame", None)

    screen = SimpleNamespace(
        backend="glfw",
        pos=(15, 15),
        get_mouse_position=lambda: screen.pos,
        is_mouse_button_pressed=lambda button: button == 0,
        was_mouse_button_pressed=lambda button: button == 0,
        was_mouse_button_released=lambda button: False,
        set_mouse_position=lambda x, y: setattr(screen, "pos", (x, y)),
    )
    target = Target((10, 10, 30, 30))
    manager = DraggableManager(button_index=0, screen_width=100, screen_height=100)
    manager.add(Draggable(target))
    response = SimpleNamespace(backend="glfw", screen=screen)

    manager.update_from_response(response)
    screen.was_mouse_button_pressed = lambda button: False
    screen.pos = (200, 200)
    manager.update_from_response(response)

    assert target.x2 <= 100
    assert target.y2 <= 100


def test_draggable_requires_screen_methods_for_glfw():
    manager = DraggableManager()
    with pytest.raises(RuntimeError, match="update_from_screen requires"):
        manager.update_from_screen(SimpleNamespace())
