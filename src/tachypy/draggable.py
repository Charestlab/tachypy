# draggable.py

import pygame


class Draggable:
    """
    Enveloppe un target qui a :
        - draw()
        - hit_test(x, y) -> bool
        - move_by(dx, dy)
        - get_bounds() -> (x1, y1, x2, y2)
    """
    def __init__(self, target):
        self.target = target
        self.dragging = False
        self._last_mouse_pos = None

    def draw(self):
        self.target.draw()

class DraggableManager:
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

    def add(self, draggable):
        """
        Ajoute un Draggable.
        """
        self.draggables.append(draggable)

    def draw(self):
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
