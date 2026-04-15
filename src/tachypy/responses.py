# responses.py
import time

import pygame

from tachypy.scrollbar import Scrollbar


class ResponseHandler:
    """
    Process keyboard and mouse input events from Pygame.
    """

    def __init__(self, keys_to_listen=None):
        self.should_exit = False
        self.start_time = time.monotonic_ns()

        self.key_presses = []
        self.mouse_clicks = []

        # Per-frame key transitions.
        self.key_down_events = set()
        self.key_up_events = set()
        # Persistent set of currently held keys.
        self.held_keys = set()

        self.mouse_position = None
        self.mouse_buttons = [False, False, False]

        self.keys_to_listen = keys_to_listen
        self.events = []

    def reset_timer(self):
        self.start_time = time.monotonic_ns()

    def get_events(self):
        """
        Retrieve and process Pygame events, updating internal state.
        """
        self.key_down_events.clear()
        self.key_up_events.clear()

        self.events = pygame.event.get()

        for event in self.events:
            timestamp = (time.monotonic_ns() - self.start_time) / 1e9

            if event.type == pygame.QUIT:
                self.should_exit = True

            elif event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                if self.keys_to_listen is None or key_name in self.keys_to_listen:
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keydown',
                        'key': key_name,
                    })
                    self.key_down_events.add(key_name)
                    self.held_keys.add(key_name)
                    if key_name == 'escape':
                        self.should_exit = True

            elif event.type == pygame.KEYUP:
                key_name = pygame.key.name(event.key)
                if self.keys_to_listen is None or key_name in self.keys_to_listen:
                    self.key_presses.append({
                        'time': timestamp,
                        'type': 'keyup',
                        'key': key_name,
                    })
                    self.key_up_events.add(key_name)
                    self.held_keys.discard(key_name)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                button_index = event.button - 1
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mousedown',
                    'button': button_index,
                    'pos': event.pos,
                })

            elif event.type == pygame.MOUSEBUTTONUP:
                button_index = event.button - 1
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mouseup',
                    'button': button_index,
                    'pos': event.pos,
                })

        self.mouse_position = pygame.mouse.get_pos()
        pressed = pygame.mouse.get_pressed()
        self.mouse_buttons = list(pressed[:3])

    def should_quit(self):
        return self.should_exit

    def get_key_presses(self):
        return self.key_presses

    def is_key_down(self, key_name):
        return key_name in self.held_keys

    def was_key_pressed(self, key_name):
        return key_name in self.key_down_events

    def get_mouse_position(self):
        return self.mouse_position

    def is_mouse_button_pressed(self, button):
        if button < 0 or button >= len(self.mouse_buttons):
            return False
        return self.mouse_buttons[button]

    def get_mouse_clicks(self):
        return self.mouse_clicks

    def set_position(self, x, y):
        pygame.mouse.set_pos((x, y))
        self.mouse_position = (x, y)

    def clear_events(self):
        self.key_presses.clear()
        self.mouse_clicks.clear()
        self.key_down_events.clear()
        self.key_up_events.clear()
        self.held_keys.clear()
        self.should_exit = False
        self.events = []
        pygame.event.clear()
