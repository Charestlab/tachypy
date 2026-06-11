from fake_glfw import FakeGlfw, FakeScreen
from tachypy.draggable import Draggable, DraggableManager
from tachypy.responses import ResponseHandler


class DummyTarget:
    def __init__(self, bounds):
        self.x1, self.y1, self.x2, self.y2 = bounds
        self.drawn = 0

    def draw(self):
        self.drawn += 1

    def hit_test(self, x, y):
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2

    def move_by(self, dx, dy):
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def get_bounds(self):
        return self.x1, self.y1, self.x2, self.y2


def test_drag_is_clamped_to_manager_bounds():
    target = DummyTarget((10, 10, 30, 30))
    manager = DraggableManager(button_index=0, screen_width=100, screen_height=100)
    manager.add(Draggable(target))
    screen = FakeScreen()
    response = ResponseHandler(screen=screen)

    screen._glfw.cursor_pos = (15, 15)
    screen._glfw.mouse_down = {FakeGlfw.MOUSE_BUTTON_LEFT}
    response.get_events()
    manager.update_from_response(response)

    screen._glfw.cursor_pos = (200, 200)
    response.get_events()
    manager.update_from_response(response)

    x1, y1, x2, y2 = target.get_bounds()
    assert x2 <= 100
    assert y2 <= 100


def test_drag_works_without_explicit_bounds():
    target = DummyTarget((0, 0, 10, 10))
    manager = DraggableManager(button_index=0)
    manager.add(Draggable(target))
    screen = FakeScreen()
    response = ResponseHandler(screen=screen)

    screen._glfw.cursor_pos = (5, 5)
    screen._glfw.mouse_down = {FakeGlfw.MOUSE_BUTTON_LEFT}
    response.get_events()
    manager.update_from_response(response)

    screen._glfw.cursor_pos = (20, 15)
    response.get_events()
    manager.update_from_response(response)

    assert target.get_bounds() == (15.0, 10.0, 25.0, 20.0)


def test_draw_and_release_and_none_mouse_position():
    target = DummyTarget((0, 0, 10, 10))
    draggable = Draggable(target)
    manager = DraggableManager(button_index=0, screen_width=100, screen_height=100)
    manager.add(draggable)
    manager.draw()
    assert target.drawn == 1

    screen = FakeScreen()
    response = ResponseHandler(screen=screen)
    screen._glfw.cursor_pos = (5, 5)
    screen._glfw.mouse_down = {FakeGlfw.MOUSE_BUTTON_LEFT}
    response.get_events()
    manager.update_from_response(response)
    assert manager.active is draggable and draggable.dragging

    screen._glfw.mouse_down = set()
    response.get_events()
    manager.update_from_response(response)
    assert manager.active is None and draggable.dragging is False


def test_update_from_screen_is_rejected():
    manager = DraggableManager()
    try:
        manager.update_from_screen(FakeScreen())
    except RuntimeError as exc:
        assert "ResponseHandler" in str(exc)
    else:
        raise AssertionError("update_from_screen should fail")
