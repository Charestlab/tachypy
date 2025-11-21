# draggable.py

import pygame


class Draggable:
    """
    Enveloppe un target qui a :
        - draw()
        - hit_test(x, y) -> bool
        - move_by(dx, dy)
    """
    def __init__(self, target):
        self.target = target
        self.dragging = False
        self._last_mouse_pos = None

    def draw(self):
        self.target.draw()

class DraggableManager:
    def __init__(self, button_index=0):
        """
        Classe gérant plusieurs Draggables.
        Input:
            button_index : 0 = gauche, 1 = milieu, 2 = droite
            (cohérent avec ResponseHandler). default = 0 (gauche)
        """
        self.button_index = button_index
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
                            d._last_mouse_pos = (mx, my)

                            # Le monter au-dessus : le mettre en dernier
                            self.draggables.remove(d)
                            self.draggables.append(d)
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

            if self.active._last_mouse_pos is None:
                self.active._last_mouse_pos = current_pos
                return

            lx, ly = self.active._last_mouse_pos
            cx, cy = current_pos
            dx, dy = cx - lx, cy - ly

            if dx != 0 or dy != 0:
                self.active.target.move_by(dx, dy)
                self.active._last_mouse_pos = current_pos