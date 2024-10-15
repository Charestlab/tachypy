# visuals.py

import numpy as np
from OpenGL.GL import *


def draw_rectangle(a_rect, fill=True, thickness=1.0, color=(255.0, 255.0, 255.0)):
    """
    Draw a rectangle on the screen.

    Parameters:
        a_rect: A rectangle defined as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].
        fill: If True, the rectangle will be filled. If False, only the outline will be drawn.
        thickness: Thickness of the outline if fill is False.
        color: RGB tuple (r, g, b) for the rectangle's color, with values between 0 and 255.

    """
    a_rect = np.asarray(a_rect)
    if a_rect.shape[0] == 4:
        x1, y1, x2, y2 = a_rect
    elif a_rect.shape == (2, 2):
        (x1, y1), (x2, y2) = a_rect
    else:
        raise ValueError("Rectangle must be [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].")

    if x2 < x1 or y2 < y1:
        raise ValueError("x2 must be >= x1 and y2 must be >= y1.")
    
    color = np.asarray(color) / 255.0
    glColor3f(*color)

    if fill:
        glBegin(GL_QUADS)
        glVertex2f(x1, y1)  # Top-left
        glVertex2f(x2, y1)  # Top-right
        glVertex2f(x2, y2)  # Bottom-right
        glVertex2f(x1, y2)  # Bottom-left
        glEnd()
    else:
        glLineWidth(thickness)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x1, y1)  # Top-left
        glVertex2f(x2, y1)  # Top-right
        glVertex2f(x2, y2)  # Bottom-right
        glVertex2f(x1, y2)  # Bottom-left
        glEnd()


def draw_line(pts1, pts2, thickness=1.0, color=(255.0, 0.0, 0.0)):
    """
    Draw a line from pts1 to pts2 with the specified thickness and color.
    
    Parameters:
        pts1: Starting point of the line.
        pts2: Ending point of the line.
        thickness: Thickness of the line.
        color: RGB tuple (r, g, b) for the line color, with values between 0 and 255.
        
    """
    color = np.asarray(color) / 255.0
    glColor3f(*color)
    glLineWidth(thickness)
    glBegin(GL_LINES)
    glVertex2f(*pts1)
    glVertex2f(*pts2)
    glEnd()


def draw_fixation_cross(center_pts, half_width, half_height, thickness=1.0, color=(255.0, 0.0, 0.0)):
    """
    Draw a fixation cross on the screen.

    Parameters:
        center_pts: Center point of the fixation cross.
        half_width: Half-width of the fixation cross.
        half_height: Half-height of the fixation cross.
        thickness: Thickness of the cross.
        color: RGB tuple (r, g, b) for the cross color, with values between 0 and 255.
    """
    x, y = center_pts
    draw_line([x - half_width, y], [x + half_width, y], thickness, color)
    draw_line([x, y - half_height], [x, y + half_height], thickness, color)


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
