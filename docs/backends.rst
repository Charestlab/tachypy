Backends
========

Display backends
----------------

``Screen`` supports:

- ``backend="glfw"`` (default)
- ``backend="pygame"`` legacy compatibility backend, installed via ``tachypy[pygame]``

Use GLFW for the primary timing-focused event/display path:

.. code-block:: python

   screen = Screen(backend="glfw", fullscreen=True, vsync=True)

Display warmup
--------------

``Screen`` presents neutral gray warmup frames during initialization before the
caller starts experiment timing. This is enabled by default because photodiode
testing showed more stable behavior after the first frames following window and
OpenGL context creation.

.. code-block:: python

   screen = Screen(warmup_frames=60)  # default, about 1 s at 60 Hz
   screen = Screen(warmup_frames=0)   # disable if you need manual control

Warmup flip timestamps are cleared after the warmup sequence, so the first
experiment flip starts with a clean ``Screen`` timing state.

Input/event handling
--------------------

Always pass the screen object to ``ResponseHandler`` so event polling matches
the active backend:

.. code-block:: python

   responses = ResponseHandler(screen=screen)

This avoids mixing Pygame polling with GLFW windows.

Draggable compatibility
-----------------------

``DraggableManager`` works with the GLFW path when fed events from
``ResponseHandler``. The legacy pygame path remains available for existing
experiments that explicitly install ``tachypy[pygame]``.

Coordinate convention
---------------------

TachyPy uses a top-left origin convention for 2D logical coordinates. The GLFW
path is synchronized to preserve this behavior consistently across windowed and
HiDPI displays.
