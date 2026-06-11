import pytest

from fake_glfw import FakeGlfw, FakeScreen
from tachypy.responses import ResponseHandler


def test_response_handler_requires_screen():
    with pytest.raises(ValueError, match="requires a Screen"):
        ResponseHandler()


def test_tracks_held_keys_across_frames():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen, keys_to_listen=["a"])

    screen._glfw.down_keys = {FakeGlfw.KEY_A}
    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is True
    assert screen._glfw.poll_count == 1

    handler.get_events()
    assert handler.is_key_down("a") is True
    assert handler.was_key_pressed("a") is False

    screen._glfw.down_keys = set()
    handler.get_events()
    assert handler.is_key_down("a") is False
    assert "a" in handler.key_up_events


def test_keys_to_listen_filters_untracked_keys_until_queried():
    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["a"], screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_B}

    handler.get_events()
    assert handler.get_key_presses() == []
    assert handler.was_key_pressed("b") is True
    assert handler.is_key_down("b") is True


def test_space_aliases_and_integer_keycodes():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_SPACE}

    handler.get_events()

    assert handler.was_key_pressed("space") is True
    assert handler.is_key_down("spacebar") is True
    assert handler.was_key_pressed(FakeGlfw.KEY_SPACE) is True
    assert handler.is_key_down(FakeGlfw.KEY_SPACE) is True


def test_mouse_transitions_and_position():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.cursor_pos = (10, 20)
    screen._glfw.mouse_down = {FakeGlfw.MOUSE_BUTTON_LEFT}

    handler.get_events()
    assert handler.get_mouse_position() == (10.0, 20.0)
    assert handler.is_mouse_button_pressed(0) is True
    assert handler.was_mouse_button_pressed(0) is True
    assert handler.events[0].type == "MOUSEBUTTONDOWN"

    screen._glfw.mouse_down = set()
    handler.get_events()
    assert handler.was_mouse_button_released(0) is True
    assert handler.get_mouse_clicks()[-1]["type"] == "mouseup"


def test_set_position_updates_glfw_cursor():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    handler.set_position(7, 8)
    assert screen._glfw.cursor_pos == (7.0, 8.0)
    assert handler.get_mouse_position() == (7.0, 8.0)
