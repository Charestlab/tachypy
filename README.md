# TachyPy

TachyPy is a psychophysics engine for Python focused on precise visual timing with
OpenGL rendering, dual display/input backends, and experiment-friendly stimulus
helpers.

## Highlights

- OpenGL stimulus rendering (`Texture`, `Shapes`, fixation, etc.).
- Two window/input backends via `Screen`: `pygame` (default) and `glfw`.
- Backend-aware input handling through `ResponseHandler`.
- Multiple text paths:
  - `Text` (pygame-font first, Pillow fallback),
  - `GLText` (OpenGL bitmap glyphs),
  - `GLTextSDF` (distance-field text),
  - `GLSystemText` (system fonts via FreeType + HarfBuzz).
- Psychophysics helpers (`make_gabor`, gratings, normalization, dithering).
- Audio playback utility (`Audio`) with backend abstraction (`sounddevice` or `dummy`).
- Test suite for core logic and regressions.

## Installation

Install base package:

```bash
pip install tachypy
```

Editable install for development:

```bash
git clone https://github.com/Charestlab/tachypy.git
cd tachypy
pip install -e .
```

Optional extras:

```bash
pip install -e ".[test]"        # pytest
pip install -e ".[glfw]"        # GLFW backend
pip install -e ".[text]"        # Pillow text fallback
pip install -e ".[system_text]" # FreeType + HarfBuzz system-font text
pip install -e ".[audio_sd]"    # sounddevice backend
```

## Quick Start

```python
import os
from tachypy import Screen, ResponseHandler

backend = os.getenv("TACHYPY_BACKEND", "pygame")
screen = Screen(
    screen_number=0,
    fullscreen=False,
    width=1280,
    height=720,
    backend=backend,
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

Or explicitly choose backend:

```bash
TACHYPY_BACKEND=glfw python example_tachypy.py
```

## Backend Notes

- `Screen(backend="pygame")`: SDL/Pygame-managed window and events.
- `Screen(backend="glfw")`: GLFW-managed window/events, with top-left logical
  coordinate handling aligned to TachyPy conventions.
- For robust key/mouse behavior across backends, initialize
  `ResponseHandler(screen=screen)` so it can route event polling correctly.

## Text Rendering Notes

- `Text` is convenience-first and works for most instruction screens.
- `GLText`/`GLTextSDF`/`GLSystemText` render text directly in OpenGL and are
  backend-independent.
- If `pygame.font` is unavailable in your Python build, use `.[text]` or
  `.[system_text]` and switch to OpenGL text classes.

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
