API Reference
=============

Public package
--------------

.. automodule:: tachypy
   :members:
   :undoc-members:

Core modules
------------

.. automodule:: tachypy.screen
   :members:

.. automodule:: tachypy.responses
   :members:

.. automodule:: tachypy.audio
   :members:

.. automodule:: tachypy.text
   :members:

.. automodule:: tachypy.scrollbar
   :members:

Scrollbar interaction
---------------------

.. automodule:: tachypy.scrollbar_interaction
   :members:

.. automodule:: tachypy.psychophysics
   :members:

Wooting pressure feedback
-------------------------

Keyboard-agnostic visual feedback toolkit (see :doc:`wooting`). These modules
never import a keyboard package; they render feedback for any object satisfying
:class:`tachypy.feedback.PressureSource`.

.. automodule:: tachypy.feedback
   :members:

Instruction demos
-----------------

Keypad animations to play while presenting instructions, scripted or driven by
the participant's real pressures (see :doc:`wooting`). They never import a
keyboard package.

.. autoclass:: tachypy.instruction_demos.GifUwuFixationCross
   :members: start, draw, play, is_finished, is_complete, is_live, caption_ready

.. autoclass:: tachypy.instruction_demos.GifUwuScrollbar
   :members: start, draw, play, is_finished, is_complete, is_live, caption_ready

.. autoclass:: tachypy.instruction_demos.GifUwuHoldTrial
   :members: start, draw, play, is_finished, is_complete, is_live, caption_ready

.. autoclass:: tachypy.instruction_demos.HoldDemoPhase

.. autoclass:: tachypy.instruction_demos.InteractiveTrial

.. autoclass:: tachypy.instruction_demos.TrialDemoFrame
