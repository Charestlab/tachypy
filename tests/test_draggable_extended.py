from types import SimpleNamespace

import pytest

pygame = pytest.importorskip("pygame")

from tachypy.draggable import Draggable, DraggableManager


class Target:
    def __init__(self):
        self.drawn = 0
        self.x1, self.y1, self.x2, self.y2 = (0, 0, 10, 10)
        self.moves = []

    def draw(self):
        self.drawn += 1

    def hit_test(self, x, y):
        return True

    def move_by(self, dx, dy):
        self.moves.append((dx, dy))

    def get_bounds(self):
        return self.x1, self.y1, self.x2, self.y2


class Resp:
    def __init__(self):
        self.events = []
        self.pos = (5, 5)

    def set_position(self, x, y):
        self.pos = (x, y)

    def get_mouse_position(self):
        return self.pos


def test_draw_and_release_and_none_mouse_position():
    t = Target()
    d = Draggable(t)
    m = DraggableManager(button_index=0, screen_width=100, screen_height=100)
    m.add(d)
    m.draw()
    assert t.drawn == 1

    r = Resp()
    r.events = [SimpleNamespace(type=pygame.MOUSEBUTTONDOWN, button=1, pos=(5, 5))]
    m.update_from_response(r)
    assert m.active is d and d.dragging

    r.events = [SimpleNamespace(type=pygame.MOUSEBUTTONUP, button=1, pos=(5, 5))]
    m.update_from_response(r)
    assert m.active is None and d.dragging is False

    m.active = d
    d.dragging = True
    r.events = []
    r.pos = None
    m.update_from_response(r)
    assert t.moves == []
