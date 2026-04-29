from types import SimpleNamespace

import pygame

from tachypy.draggable import Draggable, DraggableManager
from tachypy.responses import ResponseHandler


class DummyTarget:
    def __init__(self, bounds):
        self.x1, self.y1, self.x2, self.y2 = bounds

    def draw(self):
        return None

    def hit_test(self, x, y):
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def move_by(self, dx, dy):
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def get_bounds(self):
        return self.x1, self.y1, self.x2, self.y2


class DummyResponse:
    def __init__(self, events, mouse_pos):
        self.events = events
        self._mouse_pos = mouse_pos

    def set_position(self, x, y):
        self._mouse_pos = (x, y)

    def get_mouse_position(self):
        return self._mouse_pos


def test_drag_is_clamped_to_manager_bounds():
    target = DummyTarget((10, 10, 30, 30))
    manager = DraggableManager(button_index=0, screen_width=100, screen_height=100)
    manager.add(Draggable(target))

    down = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(15, 15))
    response = DummyResponse([down], mouse_pos=(15, 15))
    manager.update_from_response(response)

    # Simulate mouse far outside bounds.
    response.events = []
    response._mouse_pos = (200, 200)
    manager.update_from_response(response)

    x1, y1, x2, y2 = target.get_bounds()
    assert x2 <= 100
    assert y2 <= 100


def test_drag_works_without_explicit_bounds():
    target = DummyTarget((0, 0, 10, 10))
    manager = DraggableManager(button_index=0)
    manager.add(Draggable(target))

    down = SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5))
    response = DummyResponse([down], mouse_pos=(5, 5))
    manager.update_from_response(response)

    response.events = []
    response._mouse_pos = (20, 15)
    manager.update_from_response(response)

    x1, y1, x2, y2 = target.get_bounds()
    assert (x1, y1, x2, y2) == (15, 10, 25, 20)


def test_drag_works_with_glfw_response_handler():
    class FakeScreen:
        backend = "glfw"

        def __init__(self):
            self.mouse_pos = (5, 5)
            self.mouse_down = {0}
            self.mouse_pressed = {0}
            self.mouse_released = set()

        def should_close(self):
            return False

        def was_key_pressed(self, key):
            return False

        def is_key_down(self, key):
            return False

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

    target = DummyTarget((0, 0, 10, 10))
    manager = DraggableManager(button_index=0)
    manager.add(Draggable(target))

    screen = FakeScreen()
    response = ResponseHandler(screen=screen)
    response.get_events()
    manager.update_from_response(response)

    screen.mouse_pressed = set()
    screen.mouse_pos = (20, 15)
    response.get_events()
    manager.update_from_response(response)

    x1, y1, x2, y2 = target.get_bounds()
    assert (x1, y1, x2, y2) == (15, 10, 25, 20)
