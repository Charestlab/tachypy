"""Scrollbar widget for continuous response (0..100 range by default)."""

from typing import Sequence, Tuple

import numpy as np

from tachypy._warnings import warn_once
from tachypy.shapes import Line, center_rect_on_point
from tachypy.text import Text


class Scrollbar:
    """Draw a scrollbar with a movable marker and configurable mouse behavior.

    Parameters
    ----------
    screen_width, screen_height : float
        Size of the display area used to place the scrollbar.
    position_y : float
        Vertical position of the bar and marker in screen coordinates.
    half_bar_length : float
        Half the horizontal length of the bar.
    bar_thickness, mark_thickness, end_thickness : float
        Thickness of the main bar, tick marks, and end markers.
    bar_color, mark_color, end_color : sequence of float
        Colors used for the bar, marks, and ends.
    half_mark_height : float
        Half the height of each tick mark.
    num_marks : int
        Number of tick marks drawn along the bar.
    half_end_height : float
        Half the height of the left and right end markers.
    text_left, text_right : str
        Labels displayed at each end of the scrollbar.
    font_size : int
        Font size used for the end labels.
    font_name : str
        Font name used for the labels.
    text_color : sequence of float
        Color of the labels.
    text_offset : float
        Vertical offset for the labels above the bar.
    notch_label_every : int
        Label every Nth tick mark with its value (0-100 scale), skipping the
        two extremities since ``text_left``/``text_right`` already label
        those. ``0`` (default) disables notch labels entirely. Mutually
        exclusive with ``show_value_label`` -- both share the same label row.
    notch_label_font_scale : float
        Font size for notch labels, as a fraction of ``font_size``.
    show_value_label : bool
        Show the current integer value directly under the moving marker,
        updated live as it moves. Uses the same font size/color as
        ``text_left``/``text_right`` and sits on the same row as those
        labels. Mutually exclusive with ``notch_label_every``.
    limit_mouse : bool
        When True, the marker only updates when the mouse stays near the bar's
        horizontal line. Set to False to allow interaction even when the cursor
        is farther away vertically.
    content_scale : float
        Pass ``screen.content_scale`` for sharp end labels on HiDPI screens.
        Defaults to ``2.0``; see :doc:`text_rendering` for why.

    Example
    -------
    >>> scrollbar = Scrollbar(screen_width=screen.width, screen_height=screen.height, content_scale=screen.content_scale)
    >>> value = None
    >>> response_handler.clear_events()
    >>> while value is None:
    ...     response_handler.get_events()
    ...     mouse_x, mouse_y = response_handler.get_mouse_position()
    ...     scrollbar.handle_mouse(mouse_x, mouse_y)
    ...     screen.fill((127, 127, 127))
    ...     scrollbar.draw()
    ...     screen.flip()
    ...     for click in response_handler.get_mouse_clicks():
    ...         if click["type"] == "mouseup":
    ...             value = scrollbar.get_value()
    True
    False
    """

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
        text_offset: float = 24,
        notch_label_every: int = 0,
        notch_label_font_scale: float = 0.7,
        show_value_label: bool = False,
        limit_mouse: bool = False,
        content_scale: float = 2.0,
    ):
        """Create the bar, ticks, labels, and movable marker for the scrollbar."""
        if notch_label_every < 0:
            raise ValueError("notch_label_every must be >= 0")
        if notch_label_every > 0 and show_value_label:
            raise ValueError(
                "notch_label_every and show_value_label share the same label row and "
                "can overlap; enable only one."
            )
        self.screen_width = float(screen_width)
        self.screen_height = float(screen_height)
        self.position_y = float(position_y)
        self.half_bar_length = float(half_bar_length)
        if self.half_bar_length <= 0:
            raise ValueError("half_bar_length must be greater than 0")
        self.bar_thickness = float(bar_thickness)
        self.bar_color = bar_color
        self.half_mark_height = float(half_mark_height)
        self.mark_thickness = float(mark_thickness)
        self.mark_color = mark_color
        self.num_marks = int(num_marks)
        if self.num_marks < 2:
            raise ValueError("num_marks must be at least 2")
        self.half_end_height = float(half_end_height)
        self.end_thickness = float(end_thickness)
        self.end_color = end_color
        self.text_left = text_left
        self.text_right = text_right
        self.text_size = int(font_size)
        self.font_name = font_name
        self.text_color = text_color
        self.text_offset = float(text_offset)
        self.notch_label_every = int(notch_label_every)
        self.notch_label_font_scale = float(notch_label_font_scale)
        self.show_value_label = bool(show_value_label)
        self.limit_mouse = bool(limit_mouse)
        self.content_scale = float(content_scale)
        if not np.isfinite(self.content_scale) or self.content_scale <= 0:
            raise ValueError("content_scale must be a finite value greater than 0")

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
            content_scale=self.content_scale,
        )
        self.text_right_label = Text(
            text=self.text_right,
            font_name=self.font_name,
            font_size=self.text_size,
            color=self.text_color,
            dest_rect=right_text_pos,
            content_scale=self.content_scale,
        )

        self.notch_labels = []
        if self.notch_label_every > 0:
            notch_font_size = max(1, round(self.text_size * self.notch_label_font_scale))
            mark_xs = np.linspace(
                self.center_x - self.half_bar_length, self.center_x + self.half_bar_length, self.num_marks,
            )
            mark_values = np.linspace(0.0, 100.0, self.num_marks)
            for i in range(1, self.num_marks - 1):  # skip both extremities
                if i % self.notch_label_every != 0:
                    continue
                pos = center_rect_on_point(
                    [0, 0, 500, 500],
                    [mark_xs[i], self.position_y + self.half_end_height + self.text_offset],
                )
                self.notch_labels.append(Text(
                    text=str(int(round(mark_values[i]))),
                    font_name=self.font_name,
                    font_size=notch_font_size,
                    color=self.text_color,
                    dest_rect=pos,
                    content_scale=self.content_scale,
                ))

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

        self.value_label = None
        if self.show_value_label:
            self.value_label = Text(
                text=str(int(round(self.get_value()))),
                font_name=self.font_name,
                font_size=self.text_size,
                color=self.text_color,
                dest_rect=self._value_label_rect(),
                content_scale=self.content_scale,
            )

    @property
    def min_x(self) -> float:
        """Return minimum marker x-position."""
        return self.center_x - self.half_bar_length

    @property
    def max_x(self) -> float:
        """Return maximum marker x-position."""
        return self.center_x + self.half_bar_length

    def _value_label_rect(self):
        """Return the centered dest_rect for the live value label, above the marker."""
        return center_rect_on_point(
            [0, 0, 500, 500],
            [self.mobile_line_x, self.position_y + self.half_end_height + self.text_offset],
        )

    def _update_mobile_line_geometry(self) -> None:
        """Update marker line endpoints from current x-position."""
        self.mobile_line.set_start_point((self.mobile_line_x, self.position_y - self.half_mobile_line_height))
        self.mobile_line.set_end_point((self.mobile_line_x, self.position_y + self.half_mobile_line_height))
        if self.value_label is not None:
            self.value_label.set_text(str(int(round(self.get_value()))))
            self.value_label.set_dest_rect(self._value_label_rect())

    def draw(self) -> None:
        """Draw the scrollbar, ticks, labels, and marker."""
        self.bar.draw()
        for mark in self.marks:
            mark.draw()
        self.left_end.draw()
        self.right_end.draw()
        self.text_left_label.draw()
        self.text_right_label.draw()
        for notch_label in self.notch_labels:
            notch_label.draw()
        if self.value_label is not None:
            self.value_label.draw()
        self.mobile_line.draw()

    def handle_mouse(self, mouse_x: float, mouse_y: float) -> bool:
        """Move the marker to the given mouse x-position and return True when it changes."""
        if self.limit_mouse and abs(mouse_y - self.position_y) > self.half_end_height * 2:
            return False

        new_x = float(np.clip(mouse_x, self.min_x, self.max_x))
        if new_x == self.mobile_line_x:
            return False

        self.mobile_line_x = new_x
        self._update_mobile_line_geometry()
        return True

    def move_by(self, delta_x: float, mouse_y: float | None = None) -> bool:
        """Move the marker by a relative x-distance in screen pixels."""
        return self.handle_mouse(
            self.mobile_line_x + delta_x,
            self.position_y if mouse_y is None else mouse_y,
        )

    def get_normalized_value(self) -> float:
        """Return current position in [0, 1]."""
        return (self.mobile_line_x - self.min_x) / (self.max_x - self.min_x)

    def get_value(self) -> float:
        """Return current position in [0, 100]."""
        return self.get_normalized_value() * 100.0

    def set_normalized_value(self, value: float) -> None:
        """Set position from normalized value in [0, 1] (clamped)."""
        value = float(value)
        if not np.isfinite(value):
            raise ValueError("scrollbar value must be finite")
        clamped = float(np.clip(value, 0.0, 1.0))
        if clamped != value:
            warn_once(
                "Scrollbar set_value",
                "A value outside the expected range was silently clamped "
                "(set_value expects 0-100, set_normalized_value expects 0-1). "
                "Check whatever computed it upstream.",
            )
        self.mobile_line_x = self.min_x + clamped * (self.max_x - self.min_x)
        self._update_mobile_line_geometry()

    def set_value(self, value: float) -> None:
        """Set position from value in [0, 100] (clamped)."""
        self.set_normalized_value(value / 100.0)

    def get_range(self) -> Tuple[float, float]:
        """Return value range represented by this widget."""
        return 0.0, 100.0
