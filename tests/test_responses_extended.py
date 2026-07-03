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

    poll_count = {"n": 0}
    original_poll_events = screen.poll_events

    def poll_events():
        poll_count["n"] += 1
        if poll_count["n"] >= 3:
            screen._glfw.down_keys = {FakeGlfw.KEY_LEFT}
        original_poll_events()

    screen.poll_events = poll_events
    key, rt = handler.wait_for_keypress(keys=["left", "right"])

    assert key == "left"
    assert rt >= 0
    assert poll_count["n"] == 3
    assert screen.flip_count == 0


def test_wait_for_keypress_timeout():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    key, rt = handler.wait_for_keypress(keys=["space"], timeout=0.0)

    assert key is None
    assert rt >= 0


def test_wait_for_keypress_detected_key_wins_over_same_iteration_timeout():
    # Regression test: elapsed can already reach `timeout` in the very iteration
    # a key is detected (e.g. get_events()/poll_events() itself took longer than
    # a very short timeout -- common with short polling intervals like 10ms).
    # The keypress must still be honored, not silently dropped because the
    # timeout check used to run before the key check.
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_SPACE}  # already pressed on the very first poll

    key, rt = handler.wait_for_keypress(keys=["space"], timeout=0.0)

    assert key == "space"


def test_wait_for_keypress_default_still_exits_on_escape():
    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["space"], screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_ESCAPE}

    key, rt = handler.wait_for_keypress(keys=["space"])

    assert key is None
    assert rt >= 0


def test_wait_for_keypress_callback_fires_once_on_timeout():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    calls = []
    key, rt = handler.wait_for_keypress(
        keys=["space"], timeout=0.05, callback=lambda: calls.append(1), callback_delay=0.02,
    )

    assert key is None
    assert calls == [1]
    assert rt >= 0.02


def test_wait_for_keypress_callback_canceled_by_early_keypress():
    screen = FakeScreen()
    handler = ResponseHandler(keys_to_listen=["space"], screen=screen)

    poll_count = {"n": 0}
    original_poll_events = screen.poll_events

    def poll_events():
        poll_count["n"] += 1
        if poll_count["n"] >= 3:  # fires within a few ms, well before callback_delay
            screen._glfw.down_keys = {FakeGlfw.KEY_SPACE}
        original_poll_events()

    screen.poll_events = poll_events

    calls = []
    key, rt = handler.wait_for_keypress(
        keys=["space"], callback=lambda: calls.append(1), callback_delay=1.0,
    )

    assert key == "space"
    assert calls == [], "callback must not fire when the key arrives first"


def test_wait_for_keypress_requires_positive_callback_delay():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    for bad_delay in (None, 0, -1):
        try:
            handler.wait_for_keypress(keys=["space"], callback=lambda: None, callback_delay=bad_delay)
            assert False, f"expected ValueError for callback_delay={bad_delay!r}"
        except ValueError:
            pass


def test_wait_for_keypress_callback_exception_becomes_runtime_error():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)

    def bad_callback():
        raise KeyError("boom")

    try:
        handler.wait_for_keypress(keys=["space"], timeout=1.0, callback=bad_callback, callback_delay=0.01)
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert isinstance(e.__cause__, KeyError)


def test_clear_events_preserves_held_state_snapshots():
    screen = FakeScreen()
    handler = ResponseHandler(screen=screen)
    screen._glfw.down_keys = {FakeGlfw.KEY_SPACE}
    handler.get_events()

    handler.clear_events()

    assert handler.get_key_presses() == []
    assert handler.was_key_pressed("space") is False
    assert handler.is_key_down("space") is True
