# draggable.py
from __future__ import annotations

from typing import Any, Optional, Tuple

try:
    import pygame
except Exception:  # pragma: no cover - optional at runtime in GLFW-only stacks
    pygame = None


class Draggable:
    """
    Enveloppe un target qui a :
        - draw()
        - hit_test(x, y) -> bool
        - move_by(dx, dy)
        - get_bounds() -> (x1, y1, x2, y2)
    """
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
        """
        Classe gérant plusieurs Draggables.
        Input:
            button_index : 0 = gauche, 1 = milieu, 2 = droite
            (cohérent avec ResponseHandler). default = 0 (gauche)
        """
        self.button_index = button_index
        if screen_width is None or screen_height is None:
            self.bounds = None
        else:
            self.bounds = (0, 0, screen_width, screen_height)
        self.draggables = []
        self.active = None  # Draggable actuellement en drag

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
        if self.active is not None:
            self.active.dragging = False
            self.active._last_mouse_pos = None
            self.active = None

    def _drag_active_with_position(self, current_pos: Optional[Tuple[float, float]]) -> None:
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
        """
        Ajoute un Draggable.
        """
        self.draggables.append(draggable)

    def draw(self):
        """Draw all managed draggables in current z-order."""
        # L'ordre de la liste = z-index
        for d in self.draggables:
            d.draw()

    def update_from_response(self, response_handler):
        """
        Met à jour l'état des draggables en fonction des events
        reçus par le ResponseHandler.
        Input:
            response_handler : ResponseHandler
        """
        # GLFW native path: avoid pygame event dependency.
        screen = getattr(response_handler, "screen", None)
        backend = getattr(response_handler, "backend", None) or getattr(screen, "backend", None)
        if backend == "glfw" and screen is not None:
            self.update_from_screen(screen)
            return

        if pygame is None:
            raise RuntimeError("pygame is required for update_from_response when backend is not GLFW.")

        # --- 1) gérer les events press/release ---
        for event in response_handler.events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                btn_index = event.button - 1  # pygame 1,2,3 → 0,1,2
                if btn_index == self.button_index:
                    mx, my = event.pos

                    # Parcourir les draggables du haut vers le bas
                    # (fin de liste = top)
                    for d in reversed(self.draggables):
                        if d.target.hit_test(mx, my):
                            # C'est celui-là qu'on prend
                            self.active = d
                            d.dragging = True

                            # Monter en haut (z-index)
                            self.draggables.remove(d)
                            self.draggables.append(d)

                            # Calculer le centre de l'objet
                            x1, y1, x2, y2 = d.target.get_bounds()
                            cx = (x1 + x2) / 2.0
                            cy = (y1 + y2) / 2.0

                            # Recentrer la souris sur l'objet
                            # (on suppose que tu passes le response_handler à update_from_response)
                            response_handler.set_position(int(cx), int(cy))

                            # On peut considérer que la "dernière position" de la souris est ce centre
                            d._last_mouse_pos = (cx, cy)

                            break

            elif event.type == pygame.MOUSEBUTTONUP:
                btn_index = event.button - 1
                if btn_index == self.button_index and self.active is not None:
                    self.active.dragging = False
                    self.active._last_mouse_pos = None
                    self.active = None

        # --- 2) si on a un actif en drag, le déplacer ---
        if self.active is not None and self.active.dragging:
            current_pos = response_handler.get_mouse_position()
            if current_pos is None:
                return

            lx, ly = self.active._last_mouse_pos or current_pos
            cx, cy = current_pos

            # Récupère bounding box actuel
            x1, y1, x2, y2 = self.active.target.get_bounds()

            # Dimensions de l'objet
            w = x2 - x1
            h = y2 - y1

            if self.bounds is None:
                cx_clamped = cx
                cy_clamped = cy
            else:
                min_x, min_y, max_x, max_y = self.bounds
                # Clamp la souris pour garder l'objet dans les limites.
                cx_clamped = max(min_x + w/2, min(cx, max_x - w/2))
                cy_clamped = max(min_y + h/2, min(cy, max_y - h/2))

            # dx, dy à partir de la souris clampée
            dx = cx_clamped - lx
            dy = cy_clamped - ly

            if dx != 0 or dy != 0:
                self.active.target.move_by(dx, dy)

            # Mise à jour logique
            self.active._last_mouse_pos = (cx_clamped, cy_clamped)

    def update_from_screen(self, screen: Any) -> None:
        """Update draggable states directly from a GLFW-aware Screen object."""
        get_mouse = getattr(screen, "get_mouse_position", None)
        was_pressed = getattr(screen, "was_mouse_button_pressed", None)
        is_pressed = getattr(screen, "is_mouse_button_pressed", None)
        was_released = getattr(screen, "was_mouse_button_released", None)
        if not all(callable(fn) for fn in (get_mouse, was_pressed, is_pressed, was_released)):
            raise RuntimeError(
                "update_from_screen requires get_mouse_position/was_mouse_button_pressed/"
                "is_mouse_button_pressed/was_mouse_button_released methods."
            )

        current_pos = get_mouse()
        if was_pressed(self.button_index) and current_pos is not None:
            mx, my = current_pos
            self._pick_active(mx, my)
            if self.active is not None and self.active._last_mouse_pos is not None:
                cx, cy = self.active._last_mouse_pos
                set_mouse = getattr(screen, "set_mouse_position", None)
                if callable(set_mouse):
                    set_mouse(int(cx), int(cy))
                    current_pos = get_mouse()
                else:
                    current_pos = (cx, cy)

        if self.active is not None:
            if was_released(self.button_index) or not is_pressed(self.button_index):
                self._release_active()
            else:
                self._drag_active_with_position(current_pos)
