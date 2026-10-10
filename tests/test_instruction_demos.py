"""Layout, timeline and packaging checks for the instruction demos (no OpenGL context needed)."""
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tachypy.instruction_demos import keypad
from tachypy.instruction_demos import (
    GifUwuFixationCross,
    GifUwuHoldTrial,
    GifUwuScrollbar,
    HoldDemoPhase,
    InteractiveTrial,
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


def test_is_finished_only_when_not_looping(clock):
    once, looping = GifUwuScrollbar(make_screen()), GifUwuScrollbar(make_screen(), loop=True)
    for demo in (once, looping):
        demo.start()
    assert not once.is_finished
    clock.now += once.duration + 0.1
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


class Pad:
    """Scriptable stand-in for an analog keyboard: set ``z`` / ``c`` between frames."""

    min_pressure_start, max_pressure_start, threshold, hold_seconds = 0.01, 0.35, 0.8, 0.3

    def __init__(self):
        self.z = self.c = 0.0
        self.requested, self.validated = [], []

    def read_pressures(self, keys):
        self.requested.append(tuple(keys))
        return {"z": self.z, "c": self.c}

    def validate_analog_keys(self, keys):
        self.validated.append(tuple(keys))


def test_modes_are_validated():
    screen = make_screen()
    for demo in (GifUwuScrollbar, GifUwuFixationCross):
        with pytest.raises(ValueError, match="mode"):
            demo(screen, mode="live")
        with pytest.raises(ValueError, match="pressure source"):
            demo(screen, mode="interactive")
        with pytest.raises(ValueError, match="not both"):
            demo(screen, mode="interactive", source=Pad(), pressure_reader=lambda: (0, 0))
        with pytest.raises(ValueError, match="differ"):
            demo(screen, left_key="z", right_key="Z")


def test_fixation_takes_its_band_from_the_source_and_rescales_the_script():
    default, real = GifUwuFixationCross(make_screen()), GifUwuFixationCross(make_screen(), source=Pad())
    assert (real.config.min_pressure_start, real.config.max_pressure_start, real.config.hold_seconds) == (0.01, 0.35, 0.3)
    assert (default.config.min_pressure_start, default.config.threshold) == (0.33, 0.8)
    assert default._left_pressures.max() > default.config.threshold
    assert real._left_pressures.max() > real.config.threshold  # the overshoot still reads "too strong"
    ideal = real._left_pressures[np.argmin(abs(real._times - (real.pressure_start + 1.55 * 1.75)))]
    assert real.config.min_pressure_start <= ideal <= real.config.max_pressure_start  # and the ideal stays ideal
    explicit = GifUwuFixationCross(make_screen(), source=Pad(), threshold=0.9)
    assert explicit.config.threshold == 0.9


def test_interactive_fixation_follows_the_real_pressures_from_the_first_frame(clock):
    pad, seen = Pad(), []
    demo = GifUwuFixationCross(make_screen(), mode="interactive", source=pad)
    demo.start()
    assert pad.validated == [("z", "c")] and demo.is_live and demo.caption_ready
    for z, c in ((0.0, 0.0), (0.2, 0.1), (0.6, 0.05)):
        pad.z, pad.c = z, c
        clock.now += 0.05
        demo.draw()
        seen.append((demo.state.left_pressure, demo.state.right_pressure))
    assert seen == [(0.0, 0.0), (0.2, 0.1), (0.6, 0.05)]
    assert demo._keyboard_opacities(demo._live_from) == (0.0, 1.0)  # straight to the side view
    clock.now += 1000.0
    assert not demo.is_finished
    assert pad.requested[-1] == ("z", "c")


def test_video_then_interactive_waits_for_a_press_then_hands_over(clock):
    pad = Pad()
    demo = GifUwuFixationCross(make_screen(), mode="video_then_interactive", pressure_reader=lambda: (pad.z, pad.c), loop=True)
    demo.draw()
    clock.now += 0.3
    demo.draw()
    assert not demo.is_live and not demo.caption_ready  # still the animation
    scripted = (demo.state.left_pressure, demo.state.right_pressure)
    pad.z = 0.5
    clock.now += 0.2
    demo.draw()
    assert demo.is_live and demo.caption_ready
    assert demo.state.left_pressure == 0.5 and scripted == (0.0, 0.0)
    pad.z = 0.0
    clock.now += 5.0
    demo.draw()
    assert demo.is_live and demo.state.left_pressure == 0.0  # stays live after the release
    demo.start()
    assert not demo.is_live  # restarting plays the video again


def test_takeover_during_the_outro_snaps_to_the_side_view(clock):
    pad = Pad()
    demo = GifUwuFixationCross(make_screen(), mode="video_then_interactive", pressure_reader=lambda: (pad.z, pad.c))
    demo.start()
    demo.draw()  # a first frame with the keys up arms the takeover
    clock.now += demo.pressure_end + 0.1
    pad.c = 0.4
    demo.draw()
    assert demo._live_from == demo._side_start


def test_interactive_scrollbar_moves_with_hold_to_speed_and_clamps(clock):
    pad = Pad()
    demo = GifUwuScrollbar(make_screen(), mode="interactive", source=pad)
    demo.start()
    values = {}
    for name, (z, c) in {"rest": (0, 0), "right": (0, 0.6), "left": (0.6, 0)}.items():
        pad.z, pad.c = z, c
        for _ in range(30):
            clock.now += 0.05
            demo.draw()
        values[name] = demo._live_value
    assert values["rest"] == 50.0 and values["right"] > 50.0 and values["left"] < values["right"]
    pad.z, pad.c = 0.0, 0.6
    for _ in range(400):
        clock.now += 0.05
        demo.draw()
    assert demo._live_value == 100.0
    pad.z = pad.c = 0.6  # a tie moves nothing
    held = demo._live_value
    demo.draw()
    assert demo._live_value == held
    assert pad.requested[-1] == ("z", "c")


def test_video_then_interactive_scrollbar_continues_from_the_scripted_cursor(clock):
    pad = Pad()
    demo = GifUwuScrollbar(make_screen(), mode="video_then_interactive", source=pad, loop=True)
    demo.start()
    clock.now += 1.0
    demo.draw()
    assert not demo.is_live
    scripted = demo._sample()[0]
    assert scripted != 50.0  # the animation has moved the cursor
    pad.z = 0.5
    clock.now += 0.001
    demo.draw()
    assert demo.is_live and demo._live_value == pytest.approx(scripted, abs=1.0)


class Handler:
    def __init__(self, presses=(), quit_after=None):
        self.presses, self.frames, self.quit_after = dict(presses), 0, quit_after
        self.keys_to_listen = ["z"]

    def get_events(self):
        self.frames += 1

    def should_quit(self):
        return self.quit_after is not None and self.frames > self.quit_after

    def was_key_pressed(self, key):
        return self.presses.get(key, -1) == self.frames


def test_play_runs_until_the_exit_key_and_shows_the_caption_after_one_pass(clock):
    drawn = []
    marker = SimpleNamespace(draw=lambda: drawn.append("text"))
    caption = SimpleNamespace(draw=lambda: drawn.append("caption"))
    screen = make_screen()
    screen.fill = lambda color: None
    screen.flip = lambda: setattr(clock, "now", clock.now + 0.5)
    demo = GifUwuScrollbar(screen, loop=True)
    handler = Handler(presses={"x": 40})
    assert demo.play(handler, drawables=[marker], caption=caption) == "x"
    assert "x" in handler.keys_to_listen and drawn[0] == "text"
    assert "caption" not in drawn[: int(demo.duration / 0.5)]
    assert "caption" in drawn[int(demo.duration / 0.5) + 1:]


def test_play_returns_none_when_the_window_is_closed(clock):
    screen = make_screen()
    screen.fill = screen.flip = lambda *args: None
    assert GifUwuFixationCross(screen).play(Handler(quit_after=3)) is None


def test_hold_trial_rescales_its_built_in_pressures_onto_the_real_band():
    pad = Pad()
    pad.min_pressure_start, pad.max_pressure_start = 0.1, 0.4
    default = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0))
    real = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0), source=pad)
    assert default._default_pressures(HoldDemoPhase("g", 1.0, "s", "green"), 0.0) == (0.55, 0.45)
    assert (real.config.min_pressure_start, real.config.max_pressure_start, real.config.hold_seconds) == (0.1, 0.4, 0.3)
    green = real._default_pressures(HoldDemoPhase("g", 1.0, "s", "green"), 0.0)
    assert all(0.1 <= p <= 0.4 for p in green)  # still "ideal" on the real band
    weak = real._default_pressures(HoldDemoPhase("w", 1.0, "s", "left_weak"), 0.0)[0]
    assert 0.0 < weak < 0.1  # still "too light"
    explicit = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(1.0),
                               source=pad, max_pressure_start=0.5)
    assert explicit.config.max_pressure_start == 0.5


def test_interactive_modes_default_to_a_0_3_s_hold():
    reader = lambda: (0.0, 0.0)  # noqa: E731
    assert GifUwuFixationCross(make_screen()).config.hold_seconds == 0.5  # the video keeps its own pacing
    assert GifUwuFixationCross(make_screen(), mode="interactive", pressure_reader=reader).config.hold_seconds == 0.3
    assert GifUwuFixationCross(make_screen(), mode="video_then_interactive", pressure_reader=reader,
                               hold_seconds=0.8).config.hold_seconds == 0.8


def hold_cross(clock, pressures, **kwargs):
    """An interactive cross reading ``pressures[0]`` (a mutable pair); the ideal band is 0.33-0.66."""
    return GifUwuFixationCross(make_screen(), mode="interactive", pressure_reader=lambda: tuple(pressures), **kwargs)


def hold_for(demo, clock, seconds, step=0.05):
    for _ in range(round(seconds / step)):
        clock.now += step
        demo.draw()


def test_completions_count_each_full_hold_and_need_a_release_between(clock):
    pressures = [0.5, 0.5]
    demo = hold_cross(clock, pressures)
    demo.start()
    hold_for(demo, clock, 0.2)
    assert demo.completions == 0  # held for less than hold_seconds
    hold_for(demo, clock, 0.3)
    assert demo.completions == 1
    hold_for(demo, clock, 2.0)
    assert demo.completions == 1  # one long hold counts once
    pressures[:] = [0.5, 0.9]  # out of band: the hold breaks
    hold_for(demo, clock, 0.2)
    pressures[:] = [0.5, 0.5]
    hold_for(demo, clock, 0.6)
    assert demo.completions == 2
    demo.start()
    assert demo.completions == 0


def test_the_video_part_never_counts_as_a_completion(clock):
    pressures = [0.0, 0.0]
    demo = GifUwuFixationCross(make_screen(), mode="video_then_interactive", loop=True,
                               pressure_reader=lambda: tuple(pressures))
    demo.start()
    hold_for(demo, clock, demo.duration * 2)  # the scripted pressures hold the cross several times
    assert demo.completions == 0 and not demo.is_live


def test_max_completions_ends_the_demo_but_zero_never_does(clock):
    pressures = [0.5, 0.5]
    limited, free = hold_cross(clock, pressures, max_completions=2), hold_cross(clock, pressures)
    for demo in (limited, free):
        demo.start()
    hold_for(limited, clock, 0.6)
    assert not limited.is_complete
    pressures[:] = [0.0, 0.0]
    hold_for(limited, clock, 0.1)
    pressures[:] = [0.5, 0.5]
    hold_for(limited, clock, 0.6)
    assert limited.completions == 2 and limited.is_complete and limited.is_finished
    hold_for(free, clock, 5.0)
    assert free.completions == 1 and not free.is_complete and not free.is_finished
    with pytest.raises(ValueError, match="max_completions"):
        GifUwuFixationCross(make_screen(), max_completions=-1)


def test_play_returns_completed_after_a_short_pause(clock):
    pressures = [0.5, 0.5]
    demo = hold_cross(clock, pressures, max_completions=1)
    screen = demo.screen
    screen.fill = lambda color: None
    screen.flip = lambda: setattr(clock, "now", clock.now + 0.05)
    assert demo.play(Handler(), pause_after_completion=0.3) == "completed"
    assert demo.completions == 1 and clock.now - 100.0 < 3.0


TRIAL = InteractiveTrial(
    phases=(
        HoldDemoPhase("acquire", 0.1, "acquire", show_cross=True, wait_for="ready"),
        HoldDemoPhase("cue", 0.2, "cue", guard=True),
        HoldDemoPhase("imagery", 0.3, "imagery", guard=True, show_cross=True),
        HoldDemoPhase("question", 0.1, "question", guard=True, wait_for="response"),
        HoldDemoPhase("response", 0.2, "response"),
        HoldDemoPhase("result", 0.2, "correct"),
    ),
    fail=HoldDemoPhase("fail", 0.4, "incorrect"),
)


def live_trial(clock, pressures, **kwargs):
    frames, events = [], []
    demo = GifUwuHoldTrial(
        make_screen(), trial_drawer=frames.append, mode="interactive", interactive=TRIAL,
        pressure_reader=lambda: tuple(pressures), on_event=events.append, **kwargs)
    demo.start()
    return demo, frames, events


def run_for(demo, clock, seconds, step=0.02):
    for _ in range(round(seconds / step)):
        clock.now += step
        demo.draw()


def test_interactive_trial_waits_for_the_cross_then_runs_its_phases(clock):
    pressures = [0.0, 0.0]
    demo, frames, _ = live_trial(clock, pressures)
    run_for(demo, clock, 1.0)
    assert {f.phase_name for f in frames} == {"acquire"}  # nothing happens until the keys are held
    pressures[:] = [0.5, 0.5]
    run_for(demo, clock, 0.2)
    assert frames[-1].phase_name == "acquire"  # held for less than hold_seconds (0.3 s)
    run_for(demo, clock, 0.4)
    assert [f.phase_name for f in frames][-1] in {"cue", "imagery"}
    assert all(f.response_side is None for f in frames)


def test_lifting_a_finger_in_a_guard_phase_fails_the_trial_and_restarts_it(clock):
    pressures = [0.5, 0.5]
    demo, frames, events = live_trial(clock, pressures)
    run_for(demo, clock, 0.6)  # past acquire, into the guarded phases
    pressures[:] = [0.0, 0.5]
    run_for(demo, clock, 0.1)
    assert demo.failures == 1 and frames[-1].phase_name == "fail" and frames[-1].scene == "incorrect"
    assert events[0]["event"] == "fingers_lifted" and events[0]["keys"] == ["z"]
    assert events[0]["phase"] in {"cue", "imagery"} and events[0]["attempt"] == 1
    run_for(demo, clock, 0.6)  # the fail screen ends and the trial restarts from the cross
    assert frames[-1].phase_name == "acquire" and demo.completions == 0
    pressures[:] = [0.5, 0.5]
    run_for(demo, clock, 0.4)
    assert events[-1]["event"] == "fingers_lifted" and len(events) == 1


def test_a_correct_trial_records_the_answer_and_completes(clock):
    pressures = [0.5, 0.5]
    demo, frames, events = live_trial(clock, pressures, max_completions=1)
    run_for(demo, clock, 0.9)
    assert frames[-1].phase_name == "question"  # waits for an answer, however long
    run_for(demo, clock, 1.0)
    assert frames[-1].phase_name == "question" and not demo.is_complete
    pressures[:] = [0.5, 0.9]
    run_for(demo, clock, 0.1)
    assert frames[-1].response_side == "right"
    pressures[:] = [0.0, 0.0]  # fingers may lift once the answer is given
    run_for(demo, clock, 0.6)
    assert demo.failures == 0 and demo.completions == 1 and demo.is_complete and demo.is_finished
    assert frames[-1].phase_name == "result" and frames[-1].response_side == "right"
    assert [e["event"] for e in events] == ["response", "completed"] and events[0]["side"] == "right"
    assert {e["attempt"] for e in events} == {1}


def test_unlimited_trials_restart_after_each_completion(clock):
    pressures = [0.5, 0.5]
    demo, frames, events = live_trial(clock, pressures)
    run_for(demo, clock, 0.9)
    pressures[:] = [0.9, 0.5]
    run_for(demo, clock, 0.9)
    pressures[:] = [0.5, 0.5]
    run_for(demo, clock, 0.4)
    assert demo.completions == 1 and not demo.is_complete
    assert frames[-1].response_side is None and frames[-1].phase_name in {"acquire", "cue"}  # a fresh trial


def test_video_then_interactive_trial_starts_with_the_first_press(clock):
    pressures = [0.0, 0.0]
    demo = GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(5.0), loop=True,
                           mode="video_then_interactive", interactive=TRIAL, pressure_reader=lambda: tuple(pressures))
    demo.start()
    run_for(demo, clock, 1.0)
    assert not demo.is_live
    pressures[:] = [0.5, 0.5]
    run_for(demo, clock, 0.1)
    assert demo.is_live and demo._index == 0 and demo.state.hold_progress < 1.0
    demo.start()
    assert not demo.is_live and demo.failures == 0 and demo.events == []


def test_interactive_hold_trial_validation():
    reader = lambda: (0.0, 0.0)  # noqa: E731
    with pytest.raises(ValueError, match="interactive="):
        GifUwuHoldTrial(make_screen(), trial_drawer=print, mode="interactive", pressure_reader=reader)
    with pytest.raises(ValueError, match="wait_for"):
        HoldDemoPhase("x", 1.0, "s", wait_for="later")
    with pytest.raises(ValueError, match="positive"):
        InteractiveTrial(phases=(), fail=HoldDemoPhase("f", 1.0, "s"))
    GifUwuHoldTrial(make_screen(), trial_drawer=print, mode="interactive", interactive=TRIAL, pressure_reader=reader)
    with pytest.raises(ValueError):
        GifUwuHoldTrial(make_screen(), trial_drawer=print, phases=[])


def recorders(monkeypatch):
    lines, texts = [], []
    monkeypatch.setattr(keypad, "Line", lambda *args, **kwargs: lines.append(kwargs.get("color")) or Dummy())
    monkeypatch.setattr(keypad, "Text", lambda value, **kwargs: texts.append(value) or Dummy())
    return lines, texts


def test_a_completion_shows_a_check_mark_and_updates_the_counter(clock, monkeypatch):
    lines, texts = recorders(monkeypatch)
    pressures = [0.5, 0.5]
    demo = hold_cross(clock, pressures, max_completions=3, completion_label="Hits")
    demo.start()
    green = demo.key_color_ideal
    run_for_frames = lambda seconds: hold_for(demo, clock, seconds)  # noqa: E731
    run_for_frames(0.2)
    assert texts[-1] == "Hits: 0 / 3" and green not in lines
    run_for_frames(0.2)  # the hold completes
    assert demo.completions == 1 and texts[-1] == "Hits: 1 / 3" and lines[-2:] == [green, green]  # the check mark
    run_for_frames(1.0)
    assert green not in lines[-3:] and lines[-1] == (0, 0, 0)  # gone; the cross itself never turns green


def test_feedback_can_be_switched_off_and_never_shows_on_the_video(clock, monkeypatch):
    lines, texts = recorders(monkeypatch)
    pressures = [0.5, 0.5]
    quiet = hold_cross(clock, pressures, completion_feedback=False)
    quiet.start()
    hold_for(quiet, clock, 1.0)
    assert quiet.completions == 1 and quiet.key_color_ideal not in lines and texts == []
    video = GifUwuFixationCross(make_screen(), loop=True)
    video.start()
    hold_for(video, clock, video.duration)
    assert not [t for t in texts if not t.startswith(("Z", "C"))] and video.key_color_ideal not in lines
    free = hold_cross(clock, pressures)
    free.start()
    hold_for(free, clock, 0.1)
    assert texts[-1] == "0"  # no goal: just the count


def test_hold_trial_shows_a_counter_of_completed_trials_in_the_monitor(clock, monkeypatch):
    rects, texts = [], []
    monkeypatch.setattr(keypad, "Text", lambda value, **kwargs: texts.append(value) or rects.append(kwargs["dest_rect"]) or Dummy())
    pressures = [0.5, 0.5]
    demo, frames, _ = live_trial(clock, pressures, max_completions=2, completion_label="Trials")
    run_for(demo, clock, 0.1)
    assert texts[-1] == "Trials: 0 / 2"
    x1, y1, x2, y2 = demo._display_rect
    assert x1 < rects[-1][0] and rects[-1][2] < x2 and y1 < rects[-1][1] and rects[-1][3] < y2  # inside the display
    run_for(demo, clock, 0.9)
    pressures[:] = [0.5, 0.9]
    run_for(demo, clock, 1.0)
    assert demo.completions == 1 and texts[-1] == "Trials: 1 / 2"
    quiet, _, _ = live_trial(clock, pressures, completion_feedback=False)
    texts.clear()
    run_for(quiet, clock, 0.2)
    assert texts == []


def test_keys_already_down_do_not_cancel_the_video_until_released(clock):
    pressures = [0.5, 0.5]  # fingers still on the keys from the previous screen
    for demo in (GifUwuFixationCross(make_screen(), mode="video_then_interactive", loop=True,
                                     pressure_reader=lambda: tuple(pressures)),
                 GifUwuScrollbar(make_screen(), mode="video_then_interactive", loop=True,
                                 pressure_reader=lambda: tuple(pressures)),
                 GifUwuHoldTrial(make_screen(), trial_drawer=lambda frame: None, phases=phases(5.0), loop=True,
                                 mode="video_then_interactive", interactive=TRIAL,
                                 pressure_reader=lambda: tuple(pressures))):
        pressures[:] = [0.5, 0.5]
        demo.start()
        run_for(demo, clock, 0.5)
        assert not demo.is_live  # the video keeps playing
        pressures[:] = [0.0, 0.0]
        run_for(demo, clock, 0.1)
        assert not demo.is_live  # released: armed, still the video
        pressures[:] = [0.5, 0.0]
        run_for(demo, clock, 0.1)
        assert demo.is_live  # a new press takes over
        demo.start()
        assert not demo._armed  # restarting re-arms on the next release
