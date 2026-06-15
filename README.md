# TachyPy
[![Docs Status](https://readthedocs.org/projects/tachypy/badge/?version=latest)](https://tachypy.readthedocs.io/en/latest/?badge=latest)

TachyPy is a psychophysics engine for Python focused on precise visual timing with
OpenGL rendering, a GLFW-first display/input backend, and experiment-friendly
stimulus helpers.

## Why "TachyPy"?

The name TachyPy comes from the tachistoscope: a classic laboratory instrument
used to present visual stimuli for precisely controlled, brief durations.
TachyPy aims to bring that timing discipline into Python experiments while
keeping stimulus code readable and inspectable.

![Historical tachistoscope device](https://raw.githubusercontent.com/Charestlab/tachypy/main/docs/_static/tachistoscope-device.png)

## Timing Validation

TachyPy's GLFW backend was tested with a photodiode setup using a centrally
presented white square on a uniform gray background. The white square was shown
for one frame on a 60 Hz monitor. The photodiode was placed at the screen center,
over the white square, and the recording captured both serial trigger events and
the photodiode signal.

![Photodiode timing validation: after-flip trigger aligned to photodiode response](https://raw.githubusercontent.com/Charestlab/tachypy/main/docs/_static/photodiode_after_flip_waveform.png)

In the after-flip trigger condition shown here, the dashed line marks the serial
flash trigger. The blue trace is the median photodiode waveform, with the shaded
region showing the 5th to 95th percentile range across flashes.

Summary for this run:

- Median rise after flash trigger: `6.35 ms`
- SD of rise after flash trigger: `0.20 ms`
- Median photodiode pulse width: `16.60 ms`
- SD of photodiode pulse width: `0.18 ms`

These measurements are hardware/display dependent, but they provide a concrete
validation pattern for TachyPy timing tests: combine serial trigger logging,
photodiode measurements, and TachyPy flip timestamps rather than relying on
software timestamps alone.

## Highlights

- OpenGL stimulus rendering (`Texture`, `Shapes`, fixation, etc.).
- GLFW-first window/input handling via `Screen` for tighter display control.
- Backend-aware input handling through `ResponseHandler`.
- Multiple text paths:
  - `Text` (system fonts via FreeType + HarfBuzz; polished default),
  - `GLText` (OpenGL bitmap glyphs),
  - `GLTextSDF` (distance-field text),
  - `GLSystemText` (backward-compatible explicit name for `Text`).
- Psychophysics helpers (`make_gabor`, gratings, normalization, dithering).
- Audio playback utility (`Audio`) backed by `tachyaudio`.
- Test suite for core logic and regressions.

## Installation

Install base package:

```bash
pip install tachypy
```

The base install includes GLFW for display/input, PyOpenGL, Pillow text
support, pyserial for serial/trigger workflows, and TachyAudio for audio playback.
Pygame support has been removed; GLFW is the supported display/input backend.
TachyAudio is currently published as a beta release; if your pip resolver refuses pre-releases, pass `--pre` (or install `tachyaudio==0.2.0b1`) explicitly.

Editable install for development:

```bash
git clone https://github.com/Charestlab/tachypy.git
cd tachypy
pip install --pre -e .
```

Optional extras:

```bash
pip install -e ".[test]"        # pytest
pip install -e ".[text]"        # Pillow text fallback
# Audio support (tachyaudio) is included in the base install
```

### Audio dependency

TachyPy audio now uses `tachyaudio>=0.2.0b1`. TachyPy no longer depends on
`sounddevice` or requires users to install PortAudio separately. Hardware/audio
device validation should still be done on the lab machine that will run the
experiment.

## Quick Start

```python
from tachypy import Screen, ResponseHandler

screen = Screen(
    screen_number=0,
    fullscreen=False,
    width=1280,
    height=720,
)
responses = ResponseHandler(screen=screen)

running = True
while running:
    screen.fill((128, 128, 128))
    screen.flip()

    responses.get_events()
    if responses.should_quit() or responses.was_key_pressed("esc"):
        running = False
    if responses.was_key_pressed("space"):
        print("Space pressed")

screen.close()
```

To run the full demo:

```bash
python example_tachypy.py
```

To run the fullscreen GLFW clock/stop-timer demo:

```bash
tachypy-clock-demo
```

From a source checkout:

```bash
python clock_timer_demo.py
```

Use `Esc` to quit, click `START`/`STOP`/`RESET`, or use `Space` and `R`.
For development, use `tachypy-clock-demo --windowed` or `python clock_timer_demo.py --windowed`.

Choose a font for demo text rendering with GLFW `Text`/`GLSystemText`:

```bash
TACHYPY_FONT="Avenir Next, Helvetica, Arial" python example_tachypy.py
```

## Backend Notes

- `Screen(backend="glfw")`: GLFW-managed window/events, with top-left logical
  coordinate handling aligned to TachyPy conventions.
- `Screen(...)` defaults to GLFW, so most code does not need a backend argument.
- `Screen(...)` also presents 60 neutral warmup frames by default before
  experiment timing begins; set `warmup_frames=0` to disable or choose another
  count for a specific display.
- Initialize `ResponseHandler(screen=screen)` for input. It calls
  `screen.poll_events()` and owns keyboard/mouse state; `Screen` does not track
  participant responses directly.
- `DraggableManager` reads mouse transitions through `ResponseHandler(screen=screen)`.

## Text Rendering Notes

- `Text` is the polished system-font renderer and is equivalent to `GLSystemText`.
- `GLText`/`GLTextSDF`/`GLSystemText` render text directly in OpenGL and are
  backend-independent.
- `GLSystemText` supports system font selection by family name, fallback list
  (e.g. `"Avenir Next, Helvetica, Arial"`), or direct font file path.
- For production instruction text, prefer `Text` with `.[system_text]`.
- The old texture-backed constructor is backbenched as `tachypy.text.LegacyText`.

## API Naming

The psychophysics module exposes modern English APIs (for example
`make_gabor`, `make_sine_grating`, `normalize_to_unit_interval`).
Legacy French names remain as compatibility wrappers and emit
`DeprecationWarning`.

## Testing

Run tests:

```bash
pip install -e ".[test]"
pytest
```

Current suite covers audio timing helpers, response/key state handling,
backend behavior, psychophysics invariants, text layout/renderer basics, and
other regression-prone utility paths.

CI uses mocked TachyAudio streams for deterministic unit tests. Keep hardware
audio-device validation as a dedicated local or lab-machine test.

## Documentation

Expanded docs live in `/docs` and include:

- getting started
- backend behavior and input routing
- text rendering options
- audio backend guidance
- examples and contribution workflow

Hosted docs (Read the Docs): https://tachypy.readthedocs.io/

If Read the Docs is not auto-updating after pushes, reconnect GitHub in RTD and
re-sync project webhooks from the RTD project settings.

## Main Modules

- `screen.py`: display/context lifecycle and backend abstraction.
- `responses.py`: keyboard/mouse event handling and key-state queries.
- `text.py`, `gltext.py`, `gltext_sdf.py`, `glsystemtext.py`: text rendering.
- `textures.py`, `shapes.py`, `draggable.py`, `scrollbar.py`: visual primitives.
- `psychophysics.py`: stimulus generation and normalization utilities.
- `audio.py`: sound playback and timing helpers.

## Contributing

1. Fork and clone the repository.
2. Create a branch for your change.
3. Add tests for behavioral changes.
4. Run `pytest`.
5. Open a pull request.

## License

MIT. See `LICENSE`.
