"""Minimal three-trial Wooting analog scrollbar demo.

Run with ``python -m tachypy.wooting.demos.slider_demo`` or the installed
``tachypy-wooting-slider-demo`` command.

The demo uses the TachyPy ``Scrollbar`` widget unchanged and adds interaction
through ``WOOTING_ACQUISITION.interact_slider`` in ``mouse_keyboard`` mode:
the mouse or analog ``Z``/``C`` keys move the scrollbar, while a mouse click
or ``X`` confirms it. Press ``Escape`` to quit.
"""
from __future__ import annotations

try:
    from tachypy import Screen, Scrollbar, Text, WOOTING_ACQUISITION
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Install the Wooting extra first: pip install 'tachypy[wooting]'") from exc


N_TRIALS = 3


def main() -> int:
    acquisition = WOOTING_ACQUISITION()
    screen = None
    try:
        acquisition.initialize_keyboard()
        screen = Screen(width=1100, height=650, fullscreen=False, grab_input=False)
        instruction = "MOUSE or Z/C : MOVE    CLICK or X : CONFIRM"

        slider = Scrollbar(
            screen_width=screen.width,
            screen_height=screen.height,
            position_y=screen.height / 2,
            half_bar_length=350,
            num_marks=11,
            content_scale=screen.content_scale,
        )
        message = Text(
            "",
            dest_rect=(60, 40, screen.width - 60, 180),
            color=(0, 0, 0),
            content_scale=screen.content_scale,
        )

        print(f"Controls: {instruction}. Press Escape to quit.")
        for trial in range(1, N_TRIALS + 1):
            message.set_text(f"TRIAL {trial}/{N_TRIALS}\n{instruction}\nESCAPE : QUIT")
            value, reaction_time = acquisition.interact_slider(
                slider=slider,
                screen=screen,
                drawables=(message,),
                input_mode="mouse_keyboard",
                mouse_quiet_period=0.04,
            )
            if value is None:
                print("Demo cancelled.")
                return 0
            print(f"Trial {trial}: value={value:.2f}, reaction_time={reaction_time:.3f}s")

        print("Demo complete.")
        return 0
    finally:
        acquisition.uninitialize_keyboard()
        if screen is not None and hasattr(screen, "close"):
            screen.close()


if __name__ == "__main__":
    raise SystemExit(main())
