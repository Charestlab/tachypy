"""Animated keypad demos for explaining analog keys while presenting instructions.

Scripted animations of the Wooting UwU keypad that need no keyboard or
TachyWooting: show them with the instructions so participants understand the
pressure-sensitive keys *before* they use them. See :doc:`wooting` for gifs and a
complete example.

.. code-block:: python

   from tachypy.instruction_demos import GifUwuFixationCross

   demo = GifUwuFixationCross(screen, background_color=(128, 128, 128), loop=True)
   demo.start()
   while not response_handler.was_key_pressed("x"):
       response_handler.get_events()
       screen.fill((128, 128, 128))
       demo.draw(screen)
       screen.flip()

Requires Pillow to load the keypad images (``pip install "tachypy[wooting]"``).
"""
from .hold_trial import GifUwuHoldTrial, HoldDemoPhase, PressureProvider, TrialDemoFrame, TrialDrawer
from .keypad import GifUwuFixationCross, GifUwuScrollbar

__all__ = [
    "GifUwuFixationCross",
    "GifUwuHoldTrial",
    "GifUwuScrollbar",
    "HoldDemoPhase",
    "PressureProvider",
    "TrialDemoFrame",
    "TrialDrawer",
]
