"""Audit Screen constructor arguments at the GLFW boundary, without a display."""

import sys
import types
from unittest.mock import Mock

import pytest

import tachypy.screen as screen_module
from tachypy.screen import Screen


@pytest.fixture
def glfw_backend(monkeypatch):
    mode = types.SimpleNamespace(
        size=types.SimpleNamespace(width=1920, height=1080), refresh_rate=144
    )
    glfw = Mock(
        TRUE=1, DOUBLEBUFFER=0x21010, REFRESH_RATE=0x2100F, CURSOR=0x33001,
        CURSOR_DISABLED=0x34003, CURSOR_NORMAL=0x34001,
    )
    glfw.get_monitors.return_value = ["primary", "secondary"]
    glfw.get_video_mode.return_value = mode
    glfw.get_video_modes.return_value = [mode]
    glfw.get_monitor_pos.return_value = (1920, 0)
    glfw.create_window.return_value = "window"
    glfw.get_window_size.return_value = (800, 600)
    glfw.get_framebuffer_size.return_value = (1600, 1200)
    monkeypatch.setitem(sys.modules, "glfw", glfw)
    for name in ("glViewport", "glMatrixMode", "glLoadIdentity", "gluOrtho2D"):
        monkeypatch.setattr(screen_module, name, Mock())
    monkeypatch.setattr(Screen, "_init_opengl_state", lambda self: None)
    return glfw


@pytest.mark.parametrize("fullscreen", [False, True])
@pytest.mark.parametrize("vsync", [False, True])
@pytest.mark.parametrize("grab_input", [False, True])
def test_constructor_forwards_window_and_context_settings(
    glfw_backend, fullscreen, vsync, grab_input
):
    glfw = glfw_backend
    Screen(screen_number=1, width=800, height=600, fullscreen=fullscreen,
           vsync=vsync, grab_input=grab_input, warmup_frames=0)

    glfw.create_window.assert_called_once_with(
        800, 600, "TachyPy", "secondary" if fullscreen else None, None
    )
    glfw.make_context_current.assert_called_once_with("window")
    glfw.swap_interval.assert_called_once_with(1 if vsync else 0)
    calls = [call[0] for call in glfw.mock_calls]
    assert calls.index("make_context_current") < calls.index("swap_interval")
    glfw.set_input_mode.assert_called_once_with(
        "window", glfw.CURSOR, glfw.CURSOR_DISABLED if grab_input else glfw.CURSOR_NORMAL
    )
    if fullscreen:
        glfw.set_window_pos.assert_not_called()
    else:
        glfw.set_window_pos.assert_called_once_with("window", 1980, 60)


@pytest.mark.parametrize("width,height,expected", [
    (None, None, (1920, 1080)), (800, None, (800, 1080)), (None, 600, (1920, 600)),
])
def test_omitted_dimensions_default_independently(glfw_backend, width, height, expected):
    screen = Screen(width=width, height=height, warmup_frames=0)
    assert glfw_backend.create_window.call_args.args[:2] == expected
    # The public dimensions reflect GLFW's actual logical size after creation.
    assert (screen.width, screen.height) == (800, 600)
    assert screen.content_scale == 2


@pytest.mark.parametrize("fullscreen", [False, True])
@pytest.mark.parametrize("vsync", [False, True])
def test_desired_refresh_rate_is_a_glfw_mode_request(glfw_backend, vsync, fullscreen):
    screen = Screen(desired_refresh_rate=120, vsync=vsync, fullscreen=fullscreen, warmup_frames=0)
    assert screen.desired_refresh_rate == 120
    glfw_backend.window_hint.assert_any_call(glfw_backend.REFRESH_RATE, 120)
    calls = glfw_backend.mock_calls
    from unittest.mock import call
    assert calls.index(call.window_hint(glfw_backend.REFRESH_RATE, 120)) < calls.index(
        call.create_window(1920, 1080, "TachyPy", "primary" if fullscreen else None, None)
    )
    glfw_backend.set_window_monitor.assert_not_called()


def test_refresh_rate_keyword_is_not_supported():
    with pytest.raises(TypeError, match="refresh_rate"):
        Screen(refresh_rate=120)


@pytest.mark.parametrize("rate", [None, 0, -1])
def test_unset_or_unthrottled_rate_does_not_request_display_mode(glfw_backend, rate):
    Screen(desired_refresh_rate=rate, warmup_frames=0)
    glfw_backend.window_hint.assert_called_once_with(glfw_backend.DOUBLEBUFFER, 1)


@pytest.mark.parametrize("actual", [120, 100])
def test_fullscreen_refreshes_mode_and_schedules_at_selected_rate(glfw_backend, actual, monkeypatch, capsys):
    import tachypy._warnings as warnings_module
    monkeypatch.setattr(warnings_module, "_warned", set())
    before = glfw_backend.get_video_mode.return_value
    after = types.SimpleNamespace(
        size=types.SimpleNamespace(width=800, height=600), refresh_rate=actual
    )
    glfw_backend.get_video_mode.side_effect = [before, after]
    glfw_backend.get_video_modes.return_value = [before, after]
    screen = Screen(width=800, height=600, desired_refresh_rate=120, warmup_frames=0)
    assert screen._mode_refresh_rate == actual
    assert screen._max_mode_refresh_rate == actual
    assert screen_module.get_render_interval(screen) == pytest.approx(1 / actual)
    message = capsys.readouterr().err
    assert ("closest supported display mode" in message) == (actual != 120)


def test_windowed_refresh_request_explains_glfw_limitation(glfw_backend, monkeypatch, capsys):
    import tachypy._warnings as warnings_module
    monkeypatch.setattr(warnings_module, "_warned", set())
    Screen(fullscreen=False, desired_refresh_rate=120, warmup_frames=0)
    assert "GLFW ignores desired_refresh_rate in windowed mode" in capsys.readouterr().err
