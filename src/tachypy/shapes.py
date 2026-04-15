"""Basic 2D OpenGL shape primitives used by TachyPy."""

from typing import Sequence, Tuple, Union

import numpy as np
from OpenGL.GL import (
    GL_LINE_LOOP,
    GL_LINES,
    GL_MODULATE,
    GL_QUADS,
    GL_TEXTURE_ENV,
    GL_TEXTURE_ENV_MODE,
    GL_TRIANGLE_FAN,
    glBegin,
    glColor3f,
    glEnd,
    glLineWidth,
    glTexEnvf,
    glVertex2f,
)


PointLike = Sequence[float]
RectLike = Union[Sequence[float], Sequence[Sequence[float]]]


class Circle:
    def __init__(
        self,
        center: PointLike,
        radius: float,
        fill: bool = True,
        thickness: float = 1.0,
        color: Sequence[float] = (255.0, 255.0, 255.0),
        num_segments: int = 100,
    ):
        self.center = np.asarray(center, dtype=np.float32)
        self.radius = float(radius)
        self.fill = bool(fill)
        self.thickness = float(thickness)
        self.num_segments = int(num_segments)
        self.set_color(color)

    def set_center(self, center: PointLike) -> None:
        self.center = np.asarray(center, dtype=np.float32)

    def set_radius(self, radius: float) -> None:
        self.radius = float(radius)

    def set_color(self, color: Sequence[float]) -> None:
        self.color = np.asarray(color, dtype=np.float32) / 255.0

    def hit_test(self, x: float, y: float) -> bool:
        dx = x - self.center[0]
        dy = y - self.center[1]
        return dx * dx + dy * dy <= self.radius * self.radius

    def move_by(self, dx: float, dy: float) -> None:
        self.center[0] += dx
        self.center[1] += dy

    def get_bounds(self) -> Tuple[float, float, float, float]:
        x1 = self.center[0] - self.radius
        y1 = self.center[1] - self.radius
        x2 = self.center[0] + self.radius
        y2 = self.center[1] + self.radius
        return float(x1), float(y1), float(x2), float(y2)

    def draw(self) -> None:
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor3f(*self.color)

        if self.fill:
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(*self.center)
        else:
            glLineWidth(self.thickness)
            glBegin(GL_LINE_LOOP)

        for i in range(self.num_segments + 1):
            angle = 2.0 * np.pi * i / self.num_segments
            x = self.center[0] + self.radius * np.cos(angle)
            y = self.center[1] + self.radius * np.sin(angle)
            glVertex2f(x, y)

        glEnd()


class Rectangle:
    def __init__(
        self,
        a_rect: RectLike,
        fill: bool = True,
        thickness: float = 1.0,
        color: Sequence[float] = (255.0, 255.0, 255.0),
    ):
        self.set_rect(a_rect)
        self.fill = bool(fill)
        self.thickness = float(thickness)
        self.set_color(color)

    def move_by(self, dx: float, dy: float) -> None:
        self.x1 += dx
        self.x2 += dx
        self.y1 += dy
        self.y2 += dy

    def hit_test(self, x: float, y: float) -> bool:
        return (self.x1 <= x <= self.x2) and (self.y1 <= y <= self.y2)

    def set_rect(self, a_rect: RectLike) -> None:
        a_rect = np.asarray(a_rect, dtype=np.float32)
        if a_rect.shape[0] == 4:
            self.x1, self.y1, self.x2, self.y2 = a_rect
        elif a_rect.shape == (2, 2):
            (self.x1, self.y1), (self.x2, self.y2) = a_rect
        else:
            raise ValueError("Rectangle must be [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].")

        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("x2 must be >= x1 and y2 must be >= y1.")

    def set_color(self, color: Sequence[float]) -> None:
        self.color = np.asarray(color, dtype=np.float32) / 255.0

    def get_bounds(self) -> Tuple[float, float, float, float]:
        return float(self.x1), float(self.y1), float(self.x2), float(self.y2)

    def draw(self) -> None:
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor3f(*self.color)

        if self.fill:
            glBegin(GL_QUADS)
        else:
            glLineWidth(self.thickness)
            glBegin(GL_LINE_LOOP)

        glVertex2f(self.x1, self.y1)
        glVertex2f(self.x2, self.y1)
        glVertex2f(self.x2, self.y2)
        glVertex2f(self.x1, self.y2)
        glEnd()


class Line:
    def __init__(
        self,
        start_point: PointLike,
        end_point: PointLike,
        thickness: float = 1.0,
        color: Sequence[float] = (255.0, 0.0, 0.0),
    ):
        self.start_point = np.asarray(start_point, dtype=np.float32)
        self.end_point = np.asarray(end_point, dtype=np.float32)
        self.thickness = float(thickness)
        self.set_color(color)

    def move_by(self, dx: float, dy: float) -> None:
        self.start_point[0] += dx
        self.start_point[1] += dy
        self.end_point[0] += dx
        self.end_point[1] += dy

    def hit_test(self, x: float, y: float, tolerance: float = 5.0) -> bool:
        p = np.array([x, y], dtype=np.float32)
        a = self.start_point
        b = self.end_point
        ab = b - a
        ab_len2 = np.dot(ab, ab)

        if ab_len2 == 0:
            dist2 = np.dot(p - a, p - a)
            return dist2 <= tolerance * tolerance

        t = np.dot(p - a, ab) / ab_len2
        t = max(0.0, min(1.0, t))
        closest = a + t * ab
        dist2 = np.dot(p - closest, p - closest)
        return dist2 <= tolerance * tolerance

    def set_start_point(self, point: PointLike) -> None:
        self.start_point = np.asarray(point, dtype=np.float32)

    def set_end_point(self, point: PointLike) -> None:
        self.end_point = np.asarray(point, dtype=np.float32)

    def set_color(self, color: Sequence[float]) -> None:
        self.color = np.asarray(color, dtype=np.float32) / 255.0

    def set_thickness(self, thickness: float) -> None:
        self.thickness = float(thickness)

    def draw(self) -> None:
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor3f(*self.color)
        glLineWidth(self.thickness)
        glBegin(GL_LINES)
        glVertex2f(*self.start_point)
        glVertex2f(*self.end_point)
        glEnd()


class FixationCross:
    def __init__(
        self,
        center: PointLike,
        half_width: float,
        half_height: float,
        thickness: float = 1.0,
        color: Sequence[float] = (255.0, 0.0, 0.0),
    ):
        self.center = np.asarray(center, dtype=np.float32)
        self.half_width = float(half_width)
        self.half_height = float(half_height)
        self.thickness = float(thickness)
        self.color = color

        self.horizontal_line = Line(
            start_point=(self.center[0] - self.half_width, self.center[1]),
            end_point=(self.center[0] + self.half_width, self.center[1]),
            thickness=self.thickness,
            color=self.color,
        )
        self.vertical_line = Line(
            start_point=(self.center[0], self.center[1] - self.half_height),
            end_point=(self.center[0], self.center[1] + self.half_height),
            thickness=self.thickness,
            color=self.color,
        )

    def set_center(self, center: PointLike) -> None:
        self.center = np.asarray(center, dtype=np.float32)
        self.update_lines()

    def set_size(self, half_width: float, half_height: float) -> None:
        self.half_width = float(half_width)
        self.half_height = float(half_height)
        self.update_lines()

    def set_color(self, color: Sequence[float]) -> None:
        self.color = color
        self.horizontal_line.set_color(color)
        self.vertical_line.set_color(color)

    def set_thickness(self, thickness: float) -> None:
        self.thickness = float(thickness)
        self.horizontal_line.set_thickness(thickness)
        self.vertical_line.set_thickness(thickness)

    def update_lines(self) -> None:
        self.horizontal_line.set_start_point((self.center[0] - self.half_width, self.center[1]))
        self.horizontal_line.set_end_point((self.center[0] + self.half_width, self.center[1]))
        self.vertical_line.set_start_point((self.center[0], self.center[1] - self.half_height))
        self.vertical_line.set_end_point((self.center[0], self.center[1] + self.half_height))

    def draw(self) -> None:
        self.horizontal_line.draw()
        self.vertical_line.draw()


def center_rect_on_point(a_rect: RectLike, a_point: PointLike):
    """Center a rectangle on a point and return [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = (
        a_rect if len(a_rect) == 4 else [a_rect[0][0], a_rect[0][1], a_rect[1][0], a_rect[1][1]]
    )
    width = x2 - x1
    height = y2 - y1
    cx, cy = a_point

    new_x1 = cx - width // 2
    new_y1 = cy - height // 2
    new_x2 = new_x1 + width
    new_y2 = new_y1 + height

    return [new_x1, new_y1, new_x2, new_y2]
