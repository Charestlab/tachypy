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
- Audio playback utility (`Audio`) with backend abstraction (`sounddevice` or `dummy`).
- Test suite for core logic and regressions.

## Installation

Install base package:

```bash
pip install tachypy
```

The base install includes GLFW for display/input, PyOpenGL, Pillow text
support, and pyserial for serial/trigger workflows. Pygame is no longer a base
dependency.

Editable install for development:

```bash
git clone https://github.com/Charestlab/tachypy.git
cd tachypy
pip install -e .
```

Optional extras:

```bash
pip install -e ".[test]"        # pytest
pip install -e ".[pygame]"      # legacy pygame compatibility backend
pip install -e ".[text]"        # Pillow text fallback
pip install -e ".[system_text]" # FreeType + HarfBuzz system-font text
pip install -e ".[audio_sd]"    # sounddevice backend
```

### sounddevice / PortAudio prerequisites

`sounddevice` requires PortAudio on some systems.

Linux (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev
```

macOS:

Install Homebrew (if needed):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Then install PortAudio:

```bash
brew install portaudio
```

Windows:

`sounddevice` wheels often already include what is needed. If installation still fails, one workaround is:

```bash
choco install portaudio
```

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
- `Screen(backend="pygame")`: legacy SDL/Pygame-managed compatibility backend. Install with `tachypy[pygame]`.
- For robust key/mouse behavior across backends, initialize
  `ResponseHandler(screen=screen)` so it can route event polling correctly.
- `DraggableManager` now works on both backends when events are read through
  `ResponseHandler(screen=screen)`.

## Text Rendering Notes

- `Text` is the polished system-font renderer and is equivalent to `GLSystemText`.
- `GLText`/`GLTextSDF`/`GLSystemText` render text directly in OpenGL and are
  backend-independent.
- `GLSystemText` supports system font selection by family name, fallback list
  (e.g. `"Avenir Next, Helvetica, Arial"`), or direct font file path.
- For production instruction text, prefer `Text` with `.[system_text]`.
- The old texture-backed constructor is backbenched as `tachypy.text.LegacyText`.
- The legacy pygame text path requires `tachypy[pygame]`.

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

For CI/headless testing, use:

```bash
TACHYPY_AUDIO_BACKEND=dummy pytest
```

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
