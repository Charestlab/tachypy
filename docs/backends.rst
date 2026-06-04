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
