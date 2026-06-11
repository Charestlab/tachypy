from fake_glfw import FakeGlfw, FakeScreen
from tachypy.responses import ResponseHandler


def test_escape_or_window_close_sets_quit():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    screen._glfw.down_keys = {FakeGlfw.KEY_ESCAPE}
    handler.get_events()
    assert handler.should_quit() is True

    handler.clear_events()
    screen._glfw.down_keys = set()
    screen._glfw.closed = True
    handler.get_events()
    assert handler.should_quit() is True


def test_wait_for_keypress_returns_key_and_rt():
    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["left", "right"], screen=screen)

    def flip():
        screen.flip_count += 1
        if screen.flip_count >= 3:
            screen._glfw.down_keys = {FakeGlfw.KEY_LEFT}

    screen.flip = flip
    key, rt = handler.wait_for_keypress(keys=["left", "right"])

    assert key == "left"
    assert rt >= 0
    assert screen.flip_count == 3


def test_wait_for_keypress_timeout():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    key, rt = handler.wait_for_keypress(keys=["space"], timeout=0.0)

    assert key is None
    assert rt >= 0


def test_clear_events_preserves_held_state_snapshots():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_SPACE}
    handler.get_events()

    handler.clear_events()

    assert handler.get_key_presses() == []
    assert handler.was_key_pressed("space") is False
    assert handler.is_key_down("space") is True
