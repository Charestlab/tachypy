"""Preview the demos in their own window.

``python -m tachypy.instruction_demos [scrollbar|fixation ...] [--mode MODE] [--min-pressure X --max-pressure Y]
[--hold-seconds S] [--completions N]``; the interactive modes read a connected Wooting keyboard,
whose correct-pressure band is the one given. ``--hold-seconds`` and ``--completions`` apply to the fixation cross.
"""
from __future__ import annotations

import argparse

from . import GifUwuFixationCross, GifUwuScrollbar
from .keypad import MODES

_DEMOS = {"scrollbar": GifUwuScrollbar, "fixation": GifUwuFixationCross}


def preview(which: str = "scrollbar", *, background=(128, 128, 128), mode: str = "video",
            band: dict | None = None, **fixation) -> None:
    """Loop one demo in a window until Esc; ``band`` (``min_pressure_start``, ``max_pressure_start``) goes to the
    keyboard, ``fixation`` (``hold_seconds``, ``max_completions``) to the fixation-cross demo."""
    from tachypy import ResponseHandler, Screen  # imported lazily: preview-only

    source = None
    if mode != "video":
        from tachypy.wooting import WOOTING_ACQUISITION

        source = WOOTING_ACQUISITION(**(band or {}))
        source.initialize_keyboard()
    screen = Screen(fullscreen=False, width=1280, height=800)
    rh = ResponseHandler(screen=screen)
    try:
        demo = _DEMOS[which](screen, background_color=background, loop=True, mode=mode, source=source,
                             **(fixation if which == "fixation" else {}))
        demo.play(rh, exit_keys=("escape",))
    finally:
        screen.close()
        if source is not None:
            source.uninitialize_keyboard()


def main(argv: list[str] | None = None) -> None:
    """Preview the named demos in sequence (both if none is named)."""
    parser = argparse.ArgumentParser(prog="python -m tachypy.instruction_demos", description=__doc__)
    parser.add_argument("demos", nargs="*", metavar="demo", help=f"{' / '.join(_DEMOS)} (default: both)")
    parser.add_argument("--mode", choices=MODES, default="video")
    parser.add_argument("--min-pressure", type=float, help="lower bound of the correct pressure (0-1)")
    parser.add_argument("--max-pressure", type=float, help="upper bound of the correct pressure (0-1)")
    parser.add_argument("--hold-seconds", type=float, help="fixation cross: hold needed in band (default 0.3 interactive)")
    parser.add_argument("--completions", type=int, default=0,
                        help="fixation cross: end after N completed holds (0 = never)")
    args = parser.parse_args(argv)
    if unknown := [name for name in args.demos if name not in _DEMOS]:
        parser.error(f"unknown demo {unknown[0]!r}; choose from {', '.join(_DEMOS)}")
    band = {name: value for name, value in (("min_pressure_start", args.min_pressure),
                                            ("max_pressure_start", args.max_pressure)) if value is not None}
    fixation = {"max_completions": args.completions}
    if args.hold_seconds is not None:
        fixation["hold_seconds"] = args.hold_seconds
    for name in args.demos or _DEMOS:
        preview(name, mode=args.mode, band=band, **fixation)


if __name__ == "__main__":
    main()
