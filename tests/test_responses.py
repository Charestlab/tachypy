from types import SimpleNamespace

import pygame

from tachypy.responses import ResponseHandler


def test_is_key_down_tracks_held_keys_across_frames(monkeypatch):
    event_batches = [
        [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_a)],
        [],
        [SimpleNamespace(type=pygame.KEYUP, key=pygame.K_a)],
    ]

    def fake_get():
        if event_batches:
            return event_batches.pop(0)
        return []

    monkeypatch.setattr("tachypy.responses.pygame.event.get", fake_get)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (100, 200))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (False, False, False))

    handler = ResponseHandler()

    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is True

    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is False

    handler.get_events()
    assert handler.is_key_down("a") is False


def test_keys_to_listen_filters_untracked_keys(monkeypatch):
    events = [SimpleNamespace(type=pygame.KEYDOWN, key=pygame.K_b)]

    monkeypatch.setattr("tachypy.responses.pygame.event.get", lambda: events)
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pos", lambda: (0, 0))
    monkeypatch.setattr("tachypy.responses.pygame.mouse.get_pressed", lambda: (True, False, False))

    handler = ResponseHandler(keys_to_listen=["a"])
    handler.get_events()

    assert handler.get_key_presses() == []
    assert handler.is_key_down("b") is False
    assert handler.is_mouse_button_pressed(0) is True
    assert handler.is_mouse_button_pressed(3) is False
