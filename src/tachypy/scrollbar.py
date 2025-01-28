import numpy as np
from tachypy.shapes import Line, center_rect_on_point  # Assuming Line class is in your visuals module
from tachypy.text import Text     # Assuming you have a Text class

class Scrollbar:
    def __init__(self,
                 screen_width,
                 screen_height,
                 position_y=200,  # Since origin is at top-left, positive y is downward
                 half_bar_length=400,
                 bar_thickness=4,
                 bar_color=(0, 0, 0),
                 half_mark_height=5,
                 mark_thickness=3,
                 mark_color=(0, 0, 0),
                 num_marks=10,
                 half_end_height=20,
                 end_thickness=4,
                 end_color=(0, 0, 0),
                 text_left='0',
                 text_right='100',
                 font_size=24,
                 font_name='Helvetica',
                 text_color=(0, 0, 0),
                 text_offset=12):
        """
        Initialize the Scrollbar.

        Parameters:
            screen_width: Width of the screen.
            screen_height: Height of the screen.
        """
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.position_y = position_y
        self.half_bar_length = half_bar_length
        self.bar_thickness = bar_thickness
        self.bar_color = bar_color
        self.half_mark_height = half_mark_height
        self.mark_thickness = mark_thickness
        self.mark_color = mark_color
        self.num_marks = num_marks
        self.half_end_height = half_end_height
        self.end_thickness = end_thickness
        self.end_color = end_color
        self.text_left = text_left
        self.text_right = text_right
        self.text_size = font_size
        self.font_name = font_name
        self.text_color = text_color
        self.text_offset = text_offset

        # Center x-coordinate
        self.center_x = self.screen_width / 2

        # Create the main bar
        self.bar = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y),
            end_point=(self.center_x + self.half_bar_length, self.position_y),
            thickness=self.bar_thickness,
            color=self.bar_color
        )

        # Create the marks
        self.marks = []
        for x in np.linspace(self.center_x - self.half_bar_length,
                             self.center_x + self.half_bar_length,
                             self.num_marks):
            mark = Line(
                start_point=(x, self.position_y - self.half_mark_height),
                end_point=(x, self.position_y + self.half_mark_height),
                thickness=self.mark_thickness,
                color=self.mark_color
            )
            self.marks.append(mark)

        # Create the ends
        self.left_end = Line(
            start_point=(self.center_x - self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x - self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color
        )
        self.right_end = Line(
            start_point=(self.center_x + self.half_bar_length, self.position_y - self.half_end_height),
            end_point=(self.center_x + self.half_bar_length, self.position_y + self.half_end_height),
            thickness=self.end_thickness,
            color=self.end_color
        )

        left_text_pos = center_rect_on_point(
            [0, 0, 500, 500], 
            [self.center_x - self.half_bar_length, self.position_y + self.half_end_height + self.text_offset]
        )

        right_text_pos = center_rect_on_point(
            [0, 0, 500, 500], 
            [self.center_x + self.half_bar_length, self.position_y + self.half_end_height + self.text_offset]
        )

        # Create the text labels
        self.text_left_label = Text(
            text=self.text_left,
            font_name=self.font_name,
            font_size=self.text_size,
            color=self.text_color,
            dest_rect = left_text_pos
        )
        self.text_right_label = Text(
            text=self.text_right,
            font_name=self.font_name,
            font_size=self.text_size,
            color=self.text_color,
            dest_rect = right_text_pos
        )

        # Mobile part (draggable line)
        self.half_mobile_line_height = 12    # Half the height of the mobile line
        self.mobile_line_thickness = 6       # Thickness of the mobile line
        self.mobile_line_color = (255, 0, 0) # Color of the mobile line (red)
        self.mobile_line_x = self.center_x   # Start at the center
        self.mobile_line = Line(
            start_point=(self.mobile_line_x, self.position_y - self.half_mobile_line_height),
            end_point=(self.mobile_line_x, self.position_y + self.half_mobile_line_height),
            thickness=self.mobile_line_thickness,
            color=self.mobile_line_color
        )

    def draw(self):
        # Draw the main bar
        self.bar.draw()
        # Draw the marks
        for mark in self.marks:
            mark.draw()
        # Draw the ends
        self.left_end.draw()
        self.right_end.draw()
        # Draw the text labels
        self.text_left_label.draw()
        self.text_right_label.draw()
        # Draw the mobile line
        self.mobile_line.draw()

    def handle_mouse(self, mouse_x, mouse_y):
        """
        Update the position of the mobile line based on mouse input.

        Parameters:
            mouse_x: x-coordinate of the mouse.
            mouse_y: y-coordinate of the mouse.
        """
        # Check if mouse_y is near the bar's position_y (within some tolerance)
        if abs(mouse_y - self.position_y) <= self.half_end_height * 2:
            # Clamp mouse_x within the bar's range
            min_x = self.center_x - self.half_bar_length
            max_x = self.center_x + self.half_bar_length
            new_x = np.clip(mouse_x, min_x, max_x)
            self.mobile_line_x = new_x
            # Update the mobile line's position
            self.mobile_line.set_start_point((self.mobile_line_x, self.position_y - self.half_mobile_line_height))
            self.mobile_line.set_end_point((self.mobile_line_x, self.position_y + self.half_mobile_line_height))
 

    def get_value(self):
        """
        Get the value corresponding to the position of the mobile line.

        Returns:
            A float value between 0 and 100.
        """
        min_x = self.center_x - self.half_bar_length
        max_x = self.center_x + self.half_bar_length
        value = ((self.mobile_line_x - min_x) / (max_x - min_x)) * 100
        return value
