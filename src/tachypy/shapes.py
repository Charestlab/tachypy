# visuals.py

import numpy as np
from OpenGL.GL import *


class Circle:
    def __init__(self, center, radius, fill=True, thickness=1.0, color=(255.0, 255.0, 255.0), num_segments=100):
        """
        Initialize a Circle object.

        Parameters:
            center: Center coordinates of the circle as a tuple (x, y).
            radius: Radius of the circle.
            fill: If True, the circle will be filled. If False, only the outline will be drawn.
            thickness: Thickness of the outline if fill is False.
            color: RGB tuple (r, g, b) for the circle's color, with values between 0 and 255.
            num_segments: The number of line segments to approximate the circle.
        """
        self.center = np.asarray(center, dtype=np.float32)
        self.radius = float(radius)
        self.fill = fill
        self.thickness = thickness
        self.set_color(color)
        self.num_segments = int(num_segments)

    def set_center(self, center):
        self.center = np.asarray(center, dtype=np.float32)

    def set_radius(self, radius):
        self.radius = float(radius)

    def set_color(self, color):
        self.color = np.asarray(color) / 255.0  # Normalize color to [0, 1]

    def draw(self):
        # Set the color for the circle
        glColor3f(*self.color)

        # Choose the OpenGL primitive type based on whether the circle is filled or not
        if self.fill:
            glBegin(GL_TRIANGLE_FAN)
            # Start with the center point for a filled circle
            glVertex2f(*self.center)
        else:
            glLineWidth(self.thickness)
            glBegin(GL_LINE_LOOP)

        # Draw the circle by specifying vertices
        for i in range(self.num_segments + 1):
            angle = 2.0 * np.pi * i / self.num_segments  # Angle for each segment
            x = self.center[0] + self.radius * np.cos(angle)
            y = self.center[1] + self.radius * np.sin(angle)
            glVertex2f(x, y)

        glEnd()


class Rectangle:
    def __init__(self, a_rect, fill=True, thickness=1.0, color=(255.0, 255.0, 255.0)):
        """
        Initialize a Rectangle object.

        Parameters:
            a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].
            fill: If True, the rectangle will be filled. If False, only the outline will be drawn.
            thickness: Thickness of the outline if fill is False.
            color: RGB tuple (r, g, b) for the rectangle's color, with values between 0 and 255.
        """
        self.set_rect(a_rect)
        self.fill = fill
        self.thickness = thickness
        self.set_color(color)

    def set_rect(self, a_rect):
        a_rect = np.asarray(a_rect)
        if a_rect.shape[0] == 4:
            self.x1, self.y1, self.x2, self.y2 = a_rect
        elif a_rect.shape == (2, 2):
            (self.x1, self.y1), (self.x2, self.y2) = a_rect
        else:
            raise ValueError("Rectangle must be [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].")

        if self.x2 < self.x1 or self.y2 < self.y1:
            raise ValueError("x2 must be >= x1 and y2 must be >= y1.")

    def set_color(self, color):
        self.color = np.asarray(color) / 255.0

    def draw(self):

        glColor3f(*self.color)

        if self.fill:
            glBegin(GL_QUADS)
            glVertex2f(self.x1, self.y1)  # Top-left
            glVertex2f(self.x2, self.y1)  # Top-right
            glVertex2f(self.x2, self.y2)  # Bottom-right
            glVertex2f(self.x1, self.y2)  # Bottom-left
            glEnd()
        else:
            glLineWidth(self.thickness)
            glBegin(GL_LINE_LOOP)
            glVertex2f(self.x1, self.y1)  # Top-left
            glVertex2f(self.x2, self.y1)  # Top-right
            glVertex2f(self.x2, self.y2)  # Bottom-right
            glVertex2f(self.x1, self.y2)  # Bottom-left
            glEnd()
        


class Line:
    def __init__(self, start_point, end_point, thickness=1.0, color=(255.0, 0.0, 0.0)):
        """
        Initialize a Line object.

        Parameters:
            start_point: Starting point of the line as a tuple (x, y).
            end_point: Ending point of the line as a tuple (x, y).
            thickness: Thickness of the line.
            color: RGB tuple (r, g, b) for the line color, with values between 0 and 255.
        """
        self.start_point = np.asarray(start_point, dtype=np.float32)
        self.end_point = np.asarray(end_point, dtype=np.float32)
        self.thickness = thickness
        self.set_color(color)

    def set_start_point(self, point):
        self.start_point = np.asarray(point, dtype=np.float32)

    def set_end_point(self, point):
        self.end_point = np.asarray(point, dtype=np.float32)

    def set_color(self, color):
        self.color = np.asarray(color) / 255.0  # Normalize color to [0, 1]

    def set_thickness(self, thickness):
        self.thickness = thickness

    def draw(self):

        glColor3f(*self.color)
        glLineWidth(self.thickness)
        glBegin(GL_LINES)
        glVertex2f(*self.start_point)
        glVertex2f(*self.end_point)
        glEnd()



class FixationCross:
    def __init__(self, center, half_width, half_height, thickness=1.0, color=(255.0, 0.0, 0.0)):
        """
        Initialize a FixationCross object.

        Parameters:
            center: Center point of the fixation cross as a tuple (x, y).
            half_width: Half-width of the fixation cross.
            half_height: Half-height of the fixation cross.
            thickness: Thickness of the cross lines.
            color: RGB tuple (r, g, b) for the cross color, with values between 0 and 255.
        """
        self.center = np.asarray(center, dtype=np.float32)
        self.half_width = half_width
        self.half_height = half_height
        self.thickness = thickness
        self.color = color

        # Create the horizontal and vertical lines
        self.horizontal_line = Line(
            start_point=(self.center[0] - self.half_width, self.center[1]),
            end_point=(self.center[0] + self.half_width, self.center[1]),
            thickness=self.thickness,
            color=self.color
        )

        self.vertical_line = Line(
            start_point=(self.center[0], self.center[1] - self.half_height),
            end_point=(self.center[0], self.center[1] + self.half_height),
            thickness=self.thickness,
            color=self.color
        )

    def set_center(self, center):
        self.center = np.asarray(center, dtype=np.float32)
        self.update_lines()

    def set_size(self, half_width, half_height):
        self.half_width = half_width
        self.half_height = half_height
        self.update_lines()

    def set_color(self, color):
        self.color = color
        self.horizontal_line.set_color(color)
        self.vertical_line.set_color(color)

    def set_thickness(self, thickness):
        self.thickness = thickness
        self.horizontal_line.set_thickness(thickness)
        self.vertical_line.set_thickness(thickness)

    def update_lines(self):
        # Update the positions of the lines based on the center and size
        self.horizontal_line.set_start_point((self.center[0] - self.half_width, self.center[1]))
        self.horizontal_line.set_end_point((self.center[0] + self.half_width, self.center[1]))
        self.vertical_line.set_start_point((self.center[0], self.center[1] - self.half_height))
        self.vertical_line.set_end_point((self.center[0], self.center[1] + self.half_height))

    def draw(self):
        # Draw both lines
        self.horizontal_line.draw()
        self.vertical_line.draw()

def center_rect_on_point(a_rect, a_point):
    """
    Center a rectangle on a point.

    Parameters:
        a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].
        a_point: A point defined as [x, y].
    """
    x1, y1, x2, y2 = a_rect if len(a_rect) == 4 else [a_rect[0][0], a_rect[0][1], a_rect[1][0], a_rect[1][1]]
    width = x2 - x1
    height = y2 - y1
    cx, cy = a_point

    new_x1 = cx - width // 2
    new_y1 = cy - height // 2
    new_x2 = new_x1 + width
    new_y2 = new_y1 + height

    return [new_x1, new_y1, new_x2, new_y2]
