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

.. automodule:: tachypy.gltext
   :members:

.. automodule:: tachypy.gltext_sdf
   :members:

.. automodule:: tachypy.glsystemtext
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
