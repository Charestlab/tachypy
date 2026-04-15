import tachypy.scrollbar as scrollbar_module
from tachypy.scrollbar import Scrollbar


class DummyDrawable:
    def __init__(self, *args, **kwargs):
        self.draw_calls = 0

    def draw(self):
        self.draw_calls += 1


def test_scrollbar_draw_get_range_and_no_move_branch(monkeypatch):
    monkeypatch.setattr(scrollbar_module, "Text", DummyDrawable)
    monkeypatch.setattr(scrollbar_module, "Line", DummyDrawable)
    sb = Scrollbar(screen_width=800, screen_height=600, half_bar_length=100, num_marks=3)

    assert sb.get_range() == (0.0, 100.0)

    # Same x position: should return False.
    moved = sb.handle_mouse(mouse_x=sb.mobile_line_x, mouse_y=sb.position_y)
    assert moved is False

    sb.draw()
