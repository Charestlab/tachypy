"""Geometry and drawing contracts, with only the OpenGL boundary replaced."""

from unittest.mock import Mock

import numpy as np
import pytest

import tachypy.shapes as shapes
from tachypy.shapes import Circle, FixationCross, Line, Rectangle, center_rect_on_point


@pytest.fixture
def gl(monkeypatch):
    calls = Mock()
    for name in ("glTexEnvf", "glColor3f", "glBegin", "glEnd", "glLineWidth", "glVertex2f"):
        monkeypatch.setattr(shapes, name, getattr(calls, name))
    return calls


@pytest.mark.parametrize("filled", [True, False])
def test_circle_geometry_and_rendered_perimeter(gl, filled):
    circle = Circle((0, 0), 1, fill=filled, thickness=3, num_segments=4)
    circle.set_center((10, 20))
    circle.set_radius(2)
    circle.move_by(1, -1)
    circle.set_color((255, 128, 0))
    assert circle.get_bounds() == (9, 17, 13, 21)
    assert circle.hit_test(13, 19)
    assert not circle.hit_test(13.01, 19)
    circle.draw()
    vertices = np.array([c.args for c in gl.glVertex2f.call_args_list])
    if filled:
        np.testing.assert_allclose(vertices[0], [11, 19])
        vertices = vertices[1:]
        gl.glBegin.assert_called_once_with(shapes.GL_TRIANGLE_FAN)
    else:
        gl.glBegin.assert_called_once_with(shapes.GL_LINE_LOOP)
        gl.glLineWidth.assert_called_once_with(3)
    np.testing.assert_allclose(vertices, [[13, 19], [11, 21], [9, 19], [11, 17], [13, 19]])
    assert gl.glColor3f.call_args.args == pytest.approx((1, 128 / 255, 0))
    gl.glEnd.assert_called_once()


@pytest.mark.parametrize("rect", [[1, 2, 5, 8], [[1, 2], [5, 8]]])
@pytest.mark.parametrize("filled", [True, False])
def test_rectangle_bounds_hit_testing_and_draw(gl, rect, filled):
    rectangle = Rectangle(rect, fill=filled, thickness=2)
    rectangle.move_by(3, -1)
    assert rectangle.get_bounds() == (4, 1, 8, 7)
    assert rectangle.hit_test(4, 7)
    assert not rectangle.hit_test(9, 7)
    assert not rectangle.hit_test(5, 8)
    rectangle.draw()
    assert [c.args for c in gl.glVertex2f.call_args_list] == [(4, 1), (8, 1), (8, 7), (4, 7)]
    gl.glBegin.assert_called_once_with(shapes.GL_QUADS if filled else shapes.GL_LINE_LOOP)
    if not filled:
        gl.glLineWidth.assert_called_once_with(2)


@pytest.mark.parametrize("rect", [[0, 1, 2], [2, 0, 1, 3], [0, 3, 1, 2]])
def test_rectangle_rejects_invalid_bounds(rect):
    with pytest.raises(ValueError):
        Rectangle(rect)


def test_line_hit_testing_uses_segment_and_handles_zero_length(gl):
    line = Line((0, 0), (10, 0))
    assert line.hit_test(5, 2, tolerance=2)
    assert not line.hit_test(5, 2.1, tolerance=2)
    assert not line.hit_test(-3, 0, tolerance=2)
    assert not line.hit_test(13, 0, tolerance=2)
    line.set_start_point((1, 2))
    line.set_end_point((1, 2))
    assert line.hit_test(1, 3, tolerance=1)
    assert not line.hit_test(1, 3.1, tolerance=1)
    line.move_by(3, 4)
    line.set_thickness(5)
    line.draw()
    assert [c.args for c in gl.glVertex2f.call_args_list] == [(4, 6), (4, 6)]
    gl.glLineWidth.assert_called_once_with(5)
    gl.glBegin.assert_called_once_with(shapes.GL_LINES)


def test_fixation_updates_both_lines_and_draws_them(gl):
    cross = FixationCross((10, 20), 3, 4)
    cross.set_center((30, 40))
    cross.set_size(5, 6)
    cross.set_color((0, 255, 0))
    cross.set_thickness(2)
    cross.draw()
    assert [c.args for c in gl.glVertex2f.call_args_list] == [(25, 40), (35, 40), (30, 34), (30, 46)]
    assert [c.args for c in gl.glColor3f.call_args_list] == [(0, 1, 0), (0, 1, 0)]
    assert [c.args for c in gl.glLineWidth.call_args_list] == [(2,), (2,)]


@pytest.mark.parametrize("rect", [[0, 0, 10, 20], [[0, 0], [10, 20]]])
def test_center_rect_preserves_dimensions(rect):
    assert center_rect_on_point(rect, (25, 35)) == [20, 25, 30, 45]
