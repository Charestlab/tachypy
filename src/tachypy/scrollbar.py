"""Scrollbar widget for continuous responses (0..100 by default)."""

from typing import Sequence, Tuple

import numpy as np

from tachypy.shapes import Line, center_rect_on_point
from tachypy.text import Text


class Scrollbar:
    def __init__(
        self,
        screen_width: float,
        screen_height: float,
        position_y: float = 200,
        half_bar_length: float = 400,
        bar_thickness: float = 4,
        bar_color: Sequence[float] = (0, 0, 0),
        half_mark_height: float = 5,
        mark_thickness: float = 3,
        mark_color: Sequence[float] = (0, 0, 0),
        num_marks: int = 10,
        half_end_height: float = 20,
        end_thickness: float = 4,
        end_color: Sequence[float] = (0, 0, 0),
        text_left: str = "0",
        text_right: str = "100",
        font_size: int = 24,
        font_name: str = "Helvetica",
        text_color: Sequence[float] = (0, 0, 0),
        text_offset: float = 12,
    ):
        self.screen_width = float(screen_width)
        self.screen_height = float(screen_height)
        self.position_y = float(position_y)
        self.half_bar_length = float(half_bar_length)
        self.bar_thickness = float(bar_thickness)
        self.bar_color = bar_color
        self.half_mark_height = float(half_mark_height)
        self.mark_thickness = float(mark_thickness)
        self.mark_color = mark_color
        self.num_marks = int(num_marks)
        self.half_end_height = float(half_end_height)
        self.end_thickness = float(end_thickness)
        self.end_color = end_color
        self.text_left = text_left
        self.text_right = text_right
        self.text_size = int(font_size)
        self.font_name = font_name
        self.text_color = text_color
        self.text_offset = float(text_offset)

        self.center_x = self.screen_width / 2

        self.bar = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y),
            end_point=(self.center_x + self.half_bar_length, self.position_y),
            thickness=self.bar_thickness,
            color=self.bar_color,
        )

        self.marks = []
        for x in np.linspace(
            self.center_x - self.half_bar_length,
            self.center_x + self.half_bar_length,
            self.num_marks,
        ):
            self.marks.append(
                Line(
                    start_point=(x, self.position_y - self.half_mark_height),
                    end_point=(x, self.position_y + self.half_mark_height),
                    thickness=self.mark_thickness,
                    color=self.mark_color,
                )
            )

        self.left_end = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x - self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color,
        )
        self.right_end = Line(
            start_point=(self.center_x + self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x + self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color,
        )

        left_text_pos = center_rect_on_point(
            [0, 0, 500, 500],
            [self.center_x - self.half_bar_length, self.position_y + self.half_end_height + self.text_offset],
        )
        right_text_pos = center_rect_on_point(
            [0, 0, 500, 500],
            [self.center_x + self.half_bar_length, self.position_y + self.half_end_height + self.text_offset],
        )

        self.text_left_label = Text(
            text=self.text_left,
            font_name=self.font_name,
            font_size=self.text_size,
            color=self.text_color,
            dest_rect=left_text_pos,
        )
        self.text_right_label = Text(
            text=self.text_right,
            font_name=self.font_name,
            font_size=self.text_size,
            color=self.text_color,
            dest_rect=right_text_pos,
        )

        self.half_mobile_line_height = 12
        self.mobile_line_thickness = 6
        self.mobile_line_color = (255, 0, 0)
        self.mobile_line_x = self.center_x
        self.mobile_line = Line(
            start_point=(self.mobile_line_x, self.position_y - self.half_mobile_line_height),
            end_point=(self.mobile_line_x, self.position_y + self.half_mobile_line_height),
            thickness=self.mobile_line_thickness,
            color=self.mobile_line_color,
        )

    @property
    def min_x(self) -> float:
        return self.center_x - self.half_bar_length

    @property
    def max_x(self) -> float:
        return self.center_x + self.half_bar_length

    def _update_mobile_line_geometry(self) -> None:
        self.mobile_line.set_start_point((self.mobile_line_x, self.position_y - self.half_mobile_line_height))
        self.mobile_line.set_end_point((self.mobile_line_x, self.position_y + self.half_mobile_line_height))

    def draw(self) -> None:
        self.bar.draw()
        for mark in self.marks:
            mark.draw()
        self.left_end.draw()
        self.right_end.draw()
        self.text_left_label.draw()
        self.text_right_label.draw()
        self.mobile_line.draw()

    def handle_mouse(self, mouse_x: float, mouse_y: float) -> bool:
        """Update mobile line from mouse position. Returns True if moved."""
        if abs(mouse_y - self.position_y) > self.half_end_height * 2:
            return False

        new_x = float(np.clip(mouse_x, self.min_x, self.max_x))
        if new_x == self.mobile_line_x:
            return False

        self.mobile_line_x = new_x
        self._update_mobile_line_geometry()
        return True

    def get_normalized_value(self) -> float:
        """Return current position in [0, 1]."""
        return (self.mobile_line_x - self.min_x) / (self.max_x - self.min_x)

    def get_value(self) -> float:
        """Return current position in [0, 100]."""
        return self.get_normalized_value() * 100.0

    def set_normalized_value(self, value: float) -> None:
        """Set position from normalized value in [0, 1] (clamped)."""
        clamped = float(np.clip(value, 0.0, 1.0))
        self.mobile_line_x = self.min_x + clamped * (self.max_x - self.min_x)
        self._update_mobile_line_geometry()

    def set_value(self, value: float) -> None:
        """Set position from value in [0, 100] (clamped)."""
        self.set_normalized_value(value / 100.0)

    def get_range(self) -> Tuple[float, float]:
        """Return value range represented by this widget."""
        return 0.0, 100.0
