# responses.py

import pygame
import time

class ResponseHandler:
    def __init__(self):
        # Initialize Pygame's event system
        pygame.event.set_allowed([
            pygame.KEYDOWN,
            pygame.KEYUP,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
            pygame.QUIT
        ])
        self.key_presses = []
        self.mouse_clicks = []
        self.start_time = time.monotonic_ns()
        self.should_exit = False
        self.key_down_events = set()
        self.key_up_events = set()

    def get_events(self):
        self.key_down_events.clear()
        self.key_up_events.clear()

        events = pygame.event.get()
        for event in events:
            timestamp = (time.monotonic_ns() - self.start_time) /1e9 # convert to secs 
            if event.type == pygame.KEYDOWN:
                key_name = pygame.key.name(event.key)
                self.key_presses.append({
                    'time': timestamp,
                    'type': 'keydown',
                    'key': key_name
                })
                self.key_down_events.add(key_name)
                if key_name == 'escape':
                    self.should_exit = True
            elif event.type == pygame.KEYUP:
                key_name = pygame.key.name(event.key)
                self.key_presses.append({
                    'time': timestamp,
                    'type': 'keyup',
                    'key': key_name
                })
                self.key_up_events.add(key_name)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mousedown',
                    'button': event.button,
                    'pos': event.pos
                })
            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_clicks.append({
                    'time': timestamp,
                    'type': 'mouseup',
                    'button': event.button,
                    'pos': event.pos
                })
            elif event.type == pygame.QUIT:
                self.should_exit = True
        return events

    def is_key_down(self, key_name):
        return key_name in self.key_down_events

    def is_key_up(self, key_name):
        return key_name in self.key_up_events

    def should_quit(self):
        return self.should_exit

    def reset(self):
        self.key_presses = []
        self.mouse_clicks = []
        self.start_time = time.monotonic_ns()
        self.should_exit = False
        self.key_down_events.clear()
        self.key_up_events.clear()