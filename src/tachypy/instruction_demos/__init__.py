"""Keypad demos to show with the instructions: the fixation-cross hold, the slider, a full trial.

Each is a scripted video (no keyboard needed), a live demo driven by the participant's real
pressures, or the video until the participant takes over: ``mode="video"`` (default),
``"interactive"`` or ``"video_then_interactive"``. See :doc:`wooting` for gifs and details.

.. code-block:: python

   from tachypy.instruction_demos import GifUwuFixationCross

   demo = GifUwuFixationCross(screen, mode="video_then_interactive", source=wooting_acquisition,
                              loop=True, max_completions=2)   # omit mode/source for a plain video
   demo.play(response_handler, exit_keys=("x",))               # until [X], or two successful holds

Classes: :class:`GifUwuFixationCross`, :class:`GifUwuScrollbar`, :class:`GifUwuHoldTrial`
(with :class:`HoldDemoPhase`, :class:`InteractiveTrial`, :class:`TrialDemoFrame`).
Requires Pillow to load the keypad images (``pip install "tachypy[wooting]"``).
"""
from .keypad import (
    GifUwuFixationCross,
    GifUwuHoldTrial,
    GifUwuScrollbar,
    HoldDemoPhase,
    InteractiveTrial,
    PressureProvider,
    TrialDemoFrame,
    TrialDrawer,
)

__all__ = [
    "GifUwuFixationCross",
    "GifUwuHoldTrial",
    "GifUwuScrollbar",
    "HoldDemoPhase",
    "InteractiveTrial",
    "PressureProvider",
    "TrialDemoFrame",
    "TrialDrawer",
]
