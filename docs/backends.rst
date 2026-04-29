Backends
========

Display backends
----------------

``Screen`` supports:

- ``backend="pygame"`` (default)
- ``backend="glfw"``

Use GLFW for lower-overhead event/display handling in many setups:

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

``DraggableManager`` works with both backends when fed events from
``ResponseHandler``. In GLFW mode, TachyPy now synthesizes mouse
down/up transition events so drag interactions match pygame behavior.

Coordinate convention
---------------------

TachyPy uses a top-left origin convention for 2D logical coordinates. The GLFW
path is synchronized to preserve this behavior consistently across windowed and
HiDPI displays.
