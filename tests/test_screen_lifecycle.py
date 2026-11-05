"""Display state, HiDPI projection, timing and resource ownership without a GPU."""

from unittest.mock import Mock, call

import pytest

import tachypy.screen as screen_module
from tachypy.screen import Screen


@pytest.fixture
def screen(monkeypatch):
    result = Screen.__new__(Screen)
    result.width, result.height = 800, 600
    result._glfw_window = "window"
    result._glfw = Mock(CURSOR=1, CURSOR_NORMAL=2, CURSOR_HIDDEN=3)
    result._glfw.get_window_size.return_value = (800, 600)
    result._glfw.get_framebuffer_size.return_value = (1600, 1200)
    result._glfw.window_should_close.return_value = False
    result._reset_flip_timing()
    for name in ("glViewport", "glMatrixMode", "glLoadIdentity", "gluOrtho2D", "glClearColor",
                 "glClear", "glDisable", "glEnable", "glBlendFunc", "glBindTexture"):
        monkeypatch.setattr(screen_module, name, Mock())
    return result


def test_opengl_initialization_and_clear(screen):
    screen._init_opengl_state()
    screen_module.glViewport.assert_called_once_with(0, 0, 1600, 1200)
    screen_module.gluOrtho2D.assert_called_once_with(0, 800, 600, 0)
    screen_module.glEnable.assert_called_once_with(screen_module.GL_BLEND)
    screen.fill((255, 128, 0))
    assert screen_module.glClearColor.call_args.args == pytest.approx((1, 128 / 255, 0, 1))
    assert screen_module.glClear.call_args.args == (screen_module.GL_COLOR_BUFFER_BIT | screen_module.GL_DEPTH_BUFFER_BIT,)


def test_opengl_initialization_uses_logical_size_for_zero_framebuffer(screen):
    screen._glfw.get_framebuffer_size.return_value = (0, 0)
    screen._init_opengl_state()
    screen_module.glViewport.assert_called_once_with(0, 0, 800, 600)


def test_resize_keeps_logical_projection_separate_from_hidpi_viewport(screen):
    screen._glfw.get_window_size.return_value = (1000, 700)
    screen._glfw.get_framebuffer_size.return_value = (2000, 1400)
    screen._sync_glfw_viewport_and_projection()
    assert (screen.width, screen.height, screen.content_scale) == (1000, 700, 2)
    screen_module.glViewport.assert_called_once_with(0, 0, 2000, 1400)
    screen_module.gluOrtho2D.assert_called_once_with(0, 1000, 700, 0)
    screen_module.gluOrtho2D.reset_mock()
    screen._sync_glfw_viewport_and_projection()
    screen_module.gluOrtho2D.assert_not_called()
    screen._glfw.get_window_size.return_value = (0, 0)
    screen._sync_glfw_viewport_and_projection(force=True)
    assert (screen.width, screen.height) == (1000, 700)


def test_context_manager_restores_cursor_and_closes_on_exception(screen):
    with pytest.raises(ValueError, match="trial failed"):
        with screen as opened:
            assert opened is screen
            screen.set_mouse_visible(False)
            assert not screen.mouse_visible
            raise ValueError("trial failed")
    assert screen.mouse_visible
    assert screen._glfw.set_input_mode.call_args_list == [call("window", 1, 3), call("window", 1, 2)]
    screen._glfw.destroy_window.assert_called_once_with("window")
    screen._glfw.terminate.assert_called_once()
    assert screen._glfw_window is None


def test_cursor_visibility_close_request_and_flip_interval(screen):
    screen.set_mouse_visible(True)
    assert screen.mouse_visible
    assert not screen.should_close()
    screen._glfw.window_should_close.return_value = True
    assert screen.should_close()
    assert screen.get_flip_interval() is None
    screen.last_flip_time, screen.prev_flip_time = 25_000_000, 5_000_000
    assert screen.get_flip_interval() == 0.02
    assert screen.test_flip_intervals(num_frames=0) == 0


def test_wait_sleeps_then_spins_to_deadline(screen, monkeypatch):
    clock = iter([0, 0, 7_000_000, 10_000_000])
    monkeypatch.setattr(screen_module, "monotonic_ns", lambda: next(clock))
    wait = Mock()
    monkeypatch.setattr(screen_module, "sleep", wait)
    screen.wait(0)
    screen.wait(-1)
    screen.wait(0.010)
    wait.assert_called_once_with(0.001)


def test_manual_tick_sleeps_and_stops_at_deadline(screen, monkeypatch):
    screen.vsync = False
    screen.desired_refresh_rate = 100
    screen._last_tick_time_ns = 0
    clock = iter([0, 0, 7_000_000, 10_000_000, 10_000_001])
    monkeypatch.setattr(screen_module, "monotonic_ns", lambda: next(clock))
    wait = Mock()
    monkeypatch.setattr(screen_module, "sleep", wait)
    screen.tick()
    wait.assert_called_once_with(0.001)
    assert screen._last_tick_time_ns == 10_000_001
