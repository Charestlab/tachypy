"""Regression tests for the GLFW response path."""

from fake_glfw import FakeGlfw, FakeScreen
from tachypy.responses import ResponseHandler


def test_untracked_function_key_is_promoted_on_first_query():
    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["space"], screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_F1}

    handler.get_events()

    assert handler.was_key_pressed("f1") is True
    assert handler.is_key_down("f1") is True
    assert "f1" in handler._probed_keys


def test_untracked_key_promoted_when_no_keys_to_listen():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_F2}

    handler.get_events()

    assert handler.was_key_pressed("f2") is True
    assert handler.is_key_down("f2") is True
    assert "f2" in handler._probed_keys


def test_unknown_key_name_is_false():
    handler = ResponseHandler(screen=FakeScreen())
    handler.get_events()

    assert handler.was_key_pressed("not-a-key") is False
    assert handler.is_key_down("not-a-key") is False
