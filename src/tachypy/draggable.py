# draggable.py
from __future__ import annotations

from typing import Optional, Tuple


class Draggable:
    """Wrap a drawable target that supports hit-testing and movement."""

    def __init__(self, target):
        """Wrap a drawable/hit-testable target as a draggable object."""
        self.target = target
        self.dragging = False
        self._last_mouse_pos = None

    def draw(self):
        """Draw the wrapped target."""
        self.target.draw()


class DraggableManager:
    """Manage drag interactions for a collection of Draggable instances."""

    def __init__(self, button_index=0, screen_width=None, screen_height=None):
        """Create a manager for left/middle/right mouse-button dragging."""
        self.button_index = button_index
        if screen_width is None or screen_height is None:
            self.bounds = None
        else:
            self.bounds = (0, 0, screen_width, screen_height)
        self.draggables = []
        self.active = None

    def _pick_active(self, mx: float, my: float) -> None:
        """Pick top-most draggable under cursor and bring it to front."""
        for d in reversed(self.draggables):
            if d.target.hit_test(mx, my):
                self.active = d
                d.dragging = True
                self.draggables.remove(d)
                self.draggables.append(d)
                x1, y1, x2, y2 = d.target.get_bounds()
                d._last_mouse_pos = ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
                return

    def _release_active(self) -> None:
        """Release the currently active draggable, if any."""
        if self.active is not None:
            self.active.dragging = False
            self.active._last_mouse_pos = None
            self.active = None

    def _drag_active_with_position(self, current_pos: Optional[Tuple[float, float]]) -> None:
        """Move the active draggable so its center follows the cursor."""
        if self.active is None or not self.active.dragging or current_pos is None:
            return
        lx, ly = self.active._last_mouse_pos or current_pos
        cx, cy = current_pos
        x1, y1, x2, y2 = self.active.target.get_bounds()
        w = x2 - x1
        h = y2 - y1
        if self.bounds is None:
            cx_clamped = cx
            cy_clamped = cy
        else:
            min_x, min_y, max_x, max_y = self.bounds
            cx_clamped = max(min_x + w / 2.0, min(cx, max_x - w / 2.0))
            cy_clamped = max(min_y + h / 2.0, min(cy, max_y - h / 2.0))
        dx = cx_clamped - lx
        dy = cy_clamped - ly
        if dx != 0 or dy != 0:
            self.active.target.move_by(dx, dy)
        self.active._last_mouse_pos = (cx_clamped, cy_clamped)

    def add(self, draggable):
        """Add a draggable target to the manager."""
        self.draggables.append(draggable)

    def draw(self):
        """Draw all managed draggables in current z-order."""
        for d in self.draggables:
            d.draw()

    def update_from_response(self, response_handler):
        """Update draggable state from a ``ResponseHandler`` snapshot."""
        required = (
            "get_mouse_position",
            "was_mouse_button_pressed",
            "is_mouse_button_pressed",
            "was_mouse_button_released",
            "set_position",
        )
        if not all(callable(getattr(response_handler, name, None)) for name in required):
            raise RuntimeError("update_from_response requires a ResponseHandler-like object.")

        current_pos = response_handler.get_mouse_position()
        if response_handler.was_mouse_button_pressed(self.button_index) and current_pos is not None:
            mx, my = current_pos
            self._pick_active(mx, my)
            if self.active is not None and self.active._last_mouse_pos is not None:
                cx, cy = self.active._last_mouse_pos
                response_handler.set_position(int(cx), int(cy))
                current_pos = response_handler.get_mouse_position()

        if self.active is not None:
            if (
                response_handler.was_mouse_button_released(self.button_index)
                or not response_handler.is_mouse_button_pressed(self.button_index)
            ):
                self._release_active()
            else:
                self._drag_active_with_position(current_pos)

    def update_from_screen(self, screen) -> None:
        """Reject direct screen input polling; use ``update_from_response`` instead."""
        raise RuntimeError("DraggableManager now reads input only from ResponseHandler, not Screen.")
