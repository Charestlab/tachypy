"""Layout, timeline and packaging checks for the instruction demos (no OpenGL context needed)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tachypy.instruction_demos import hold_trial, keypad
from tachypy.instruction_demos import (
    GifUwuFixationCross,
    GifUwuHoldTrial,
    GifUwuScrollbar,
    HoldDemoPhase,
)


class Dummy:
    """Stand-in for GL-backed drawables (Texture, Scrollbar, Text...): accepts anything."""

    def __init__(self, *args, **kwargs):
        self.rect = (0.0, 0.0, 1.0, 1.0)
        self.text = ""
        self.mobile_line = SimpleNamespace(set_color=lambda color: None)

    def __getattr__(self, name):
        return lambda *args, **kwargs: None


@pytest.fixture(autouse=True)
def no_gl(monkeypatch):
    for name in ("Texture", "Scrollbar", "Text", "Rectangle", "Line"):
        monkeypatch.setattr(keypad, name, Dummy)
    for name in ("glTexEnvf", "glColor4f", "glColor3f", "glBegin", "glEnd", "glTexCoord2f", "glVertex2f", "glLineWidth"):
        monkeypatch.setattr(keypad, name, lambda *args, **kwargs: None)
    monkeypatch.setattr(hold_trial, "Rectangle", Dummy)
    monkeypatch.setattr(keypad, "_load_keyboard_rgb", lambda path, background: np.zeros((2, 2, 3), np.uint8))


def make_screen(width=1280, height=800):
    return SimpleNamespace(width=width, height=height, content_scale=2.0)


def test_packaged_images_exist():
    for path in (keypad._KEYBOARD_PNG, keypad._SIDE_PNG, keypad._SIDE_BASE_PNG):
        assert Path(path).is_file(), path


def test_load_keyboard_rgb_flattens_onto_background(monkeypatch):
    pytest.importorskip("PIL")
    monkeypatch.undo()
    rgb = keypad._load_keyboard_rgb(keypad._KEYBOARD_PNG, (10, 20, 30))
    assert rgb.dtype == np.uint8 and rgb.ndim == 3 and rgb.shape[2] == 3
    assert tuple(rgb[0, 0]) == (10, 20, 30)  # transparent corner takes the background color


def test_both_demos_place_the_keyboard_on_the_same_rect():
    screen = make_screen()
    scroll = GifUwuScrollbar(screen)
    cross = GifUwuFixationCross(screen)
    assert scroll._kb_rect == cross._kb_rect
    assert scroll._kb_rect[2] - scroll._kb_rect[0] == GifUwuScrollbar.DEFAULT_KEYBOARD_WIDTH


def test_scrollbar_animation_closes_its_loop():
    demo = GifUwuScrollbar(make_screen(), initial_value=50.0)
    assert demo.duration > 0
    assert demo._values[-1] == pytest.approx(50.0)
    assert 99.0 in demo._values and demo._values.min() <= 25.0 + 1e-9
    assert set(demo._keys) == {"", "c", "z"}


def test_is_finished_only_when_not_looping(monkeypatch):
    clock = SimpleNamespace(now=0.0, perf_counter=lambda: clock.now)
    monkeypatch.setattr(keypad, "time", clock)
    once, looping = GifUwuScrollbar(make_screen()), GifUwuScrollbar(make_screen(), loop=True)
    for demo in (once, looping):
        demo.start()
    assert not once.is_finished
    clock.now = once.duration + 0.1
    assert once.is_finished and not looping.is_finished


def test_pressure_colors_follow_the_feedback_band():
    cross = GifUwuFixationCross(make_screen())
    cfg = cross.config
    assert cross._key_pressure_color(0.0) == (255, 255, 255)
    assert cross._key_pressure_color((cfg.min_pressure_start + cfg.max_pressure_start) / 2) == cross.key_color_ideal
    assert cross._key_pressure_color(cfg.min_pressure_start / 2) == cross.key_color_min
    assert cross._key_pressure_color(cfg.threshold) == cross.key_color_max


def test_fixation_timeline_ends_released():
    cross = GifUwuFixationCross(make_screen())
    assert cross._left_pressures[-1] == 0.0 and cross._right_pressures[-1] == 0.0
    assert cross._left_pressures.max() > cross.config.threshold  # the "too strong" overshoot is shown


def phases(*durations):
    return [HoldDemoPhase(f"p{i}", d, "scene") for i, d in enumerate(durations)]


@pytest.mark.parametrize("size", [(1024, 640), (1280, 800), (1920, 1080), (2560, 1440)])
def test_hold_trial_fits_the_requested_window_without_resizing_the_keyboard(size):
    screen = make_screen(*size)
    top, bottom = screen.height * 0.30 + 20, screen.height - max(24, screen.height * 0.05) - 100 - 20
    demo = GifUwuHoldTrial(screen, trial_drawer=lambda frame: None, phases=phases(1.0),
                           content_top=top, content_bottom=bottom)
    assert demo._monitor_rect[1] >= top - 0.5
    assert demo._side_rect[3] <= bottom + 0.5
    assert demo._kb_rect[2] - demo._kb_rect[0] == 300.0  # same keyboard size as the other demos


def test_hold_trial_without_window_is_top_anchored():
    demo = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0))
    assert demo._monitor_rect[1] == max(38.0, 800 * 0.055)


def test_hold_trial_validates_phases_and_modes():
    screen = make_screen()
    with pytest.raises(ValueError):
        GifUwuHoldTrial(screen, trial_drawer=lambda frame: None, phases=[])
    with pytest.raises(ValueError):
        GifUwuHoldTrial(screen, trial_drawer=lambda frame: None, phases=phases(1.0, 0.0))
    demo = GifUwuHoldTrial(screen, trial_drawer=lambda frame: None, phases=phases(1.0, 2.0))
    assert demo.duration == 3.0
    phase, progress = demo._phase_at(2.0)
    assert phase.name == "p1" and progress == pytest.approx(0.5)
    with pytest.raises(ValueError):
        demo._default_pressures(HoldDemoPhase("x", 1.0, "s", pressure_mode="nope"), 0.5)


@pytest.fixture
def clock(monkeypatch):
    fake = SimpleNamespace(now=100.0, perf_counter=lambda: fake.now)
    monkeypatch.setattr(keypad, "time", fake)
    monkeypatch.setattr(hold_trial, "time", fake)
    return fake


def sweep(demo, clock, steps=80):
    demo.draw()  # drawing before start() starts the clock
    for i in range(steps):
        clock.now = 100.0 + demo.duration * i / steps
        demo.draw()


def test_scrollbar_draws_over_the_whole_loop(clock):
    sweep(GifUwuScrollbar(make_screen(), loop=True), clock)
    sweep(GifUwuScrollbar(make_screen(), top_y=120.0), clock)


def test_fixation_cross_draws_every_keyboard_view_and_cross_state(clock):
    sweep(GifUwuFixationCross(make_screen(), loop=True, show_pressure_text=True), clock, steps=200)


def test_hold_trial_draws_every_pressure_mode(clock):
    modes = ("released", "ramp_to_green", "green", "lose_left", "left_weak", "remove_left",
             "left_released", "recover_left", "respond_left", "respond_right", "release")
    frames = []
    demo = GifUwuHoldTrial(
        make_screen(),
        trial_drawer=frames.append,
        phases=[HoldDemoPhase(m, 1.0, "scene", m, show_cross=True) for m in modes],
        loop=True,
    )
    sweep(demo, clock, steps=110)
    assert {f.phase_name for f in frames} == set(modes)
    assert all(0.0 <= f.progress <= 1.0 for f in frames)


def test_hold_trial_uses_a_custom_pressure_provider(clock):
    seen = []
    demo = GifUwuHoldTrial(
        make_screen(), trial_drawer=lambda frame: seen.append((frame.left_pressure, frame.right_pressure)),
        phases=phases(1.0), pressure_provider=lambda phase, progress: (0.3, 0.6),
    )
    demo.draw()
    assert seen == [(0.3, 0.6)]


def test_hold_trial_stops_at_the_end_unless_looping(clock):
    demo = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0, 1.0), playback_speed=2.0)
    demo.start()
    assert demo.duration == 1.0
    clock.now += 5.0
    assert demo._elapsed() == demo.timeline_duration and demo.is_finished
    with pytest.raises(ValueError):
        GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0), playback_speed=0)


def test_fixation_is_finished_only_when_not_looping(clock):
    once, looping = GifUwuFixationCross(make_screen()), GifUwuFixationCross(make_screen(), loop=True)
    assert not once.is_finished
    for demo in (once, looping):
        demo.start()
    clock.now += once.duration + 0.1
    assert once.is_finished and not looping.is_finished


def test_missing_pillow_gives_an_actionable_error(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setitem(sys.modules, "PIL", None)
    with pytest.raises(ImportError, match="tachypy\\[wooting\\]"):
        keypad._load_keyboard_rgb(keypad._KEYBOARD_PNG, (0, 0, 0))
