Backends
========

Display backends
----------------

``Screen`` supports GLFW only. Pygame support has been removed from the
timing-focused display/input path.

Use GLFW for display creation and OpenGL context management:

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

Always pass the screen object to ``ResponseHandler`` so input state is read from
the active display backend:

.. code-block:: python

   responses = ResponseHandler(screen=screen)

This is required because ``ResponseHandler`` calls ``screen.poll_events()`` and
owns all key/mouse state snapshots. ``Screen`` does not track participant
responses directly.

Draggable compatibility
-----------------------

``DraggableManager`` reads mouse transitions from ``ResponseHandler``. Call
``responses.get_events()`` once per frame, then pass the handler to
``manager.update_from_response(responses)``.

Coordinate convention
---------------------

TachyPy uses a top-left origin convention for 2D logical coordinates. The GLFW
path is synchronized to preserve this behavior consistently across windowed and
HiDPI displays.
