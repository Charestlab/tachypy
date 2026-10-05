"""Preview the demos in their own window: ``python -m tachypy.instruction_demos [scrollbar|fixation]``."""
from __future__ import annotations

import sys

from . import GifUwuFixationCross, GifUwuScrollbar

_DEMOS = {"scrollbar": GifUwuScrollbar, "fixation": GifUwuFixationCross}


def preview(which: str = "scrollbar", *, background=(128, 128, 128)) -> None:
    """Loop one demo in a window until Esc (needs a display)."""
    from tachypy import ResponseHandler, Screen  # imported lazily: preview-only

    screen = Screen(fullscreen=False, width=1280, height=800)
    rh = ResponseHandler(screen=screen)
    demo = _DEMOS[which](screen, background_color=background, loop=True)
    demo.start()
    try:
        while True:
            rh.get_events()
            if rh.should_quit() or rh.was_key_pressed("escape"):
                break
            screen.fill(background)
            demo.draw(screen)
            screen.flip()
    finally:
        screen.close()


def main(argv: list[str] | None = None) -> None:
    """Preview the named demos in sequence (both if none is named)."""
    for name in (sys.argv[1:] if argv is None else argv) or list(_DEMOS):
        if name not in _DEMOS:
            raise SystemExit(f"unknown demo {name!r}; choose from {', '.join(_DEMOS)}")
        preview(name)


if __name__ == "__main__":
    main()
