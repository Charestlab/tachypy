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

.. _refresh-rates-vsync:

Refresh rates and VSync
------------------------

Two independent things happen whenever a frame is drawn:

- **Presentation timing** — whether a buffer swap is synced to the display.
  Handled entirely by VSync: when on, the OS/GPU blocks ``flip()`` until the
  real vertical blank, regardless of what TachyPy knows.
- **Loop scheduling** — how often the interaction loops (``interact_slider``,
  ``wait_light_press_visual``) bother calling ``flip()`` at all, via
  ``get_render_interval()``.

VSync only blocks ``flip()`` while events are being pumped on some platforms
(see ``poll_events()``) — every TachyPy interaction loop already does this.

``get_render_interval()`` only reads the ``vsync`` flag to pick which rate to
use — the monitor's highest rate at the current resolution when on,
``desired_refresh_rate`` when off — never to observe VSync itself: the
vertical-blank signal is only observable by calling ``flip()``, which
blocks, so using it here would mean blocking on every scheduling check
instead of just when a frame is actually due. A wrong estimate only affects
how often frames are submitted, never presentation correctness.

``desired_refresh_rate`` feeds both, but not consistently:

.. list-table::
   :header-rows: 1

   * - Value
     - ``tick()`` (manual pacing, ``vsync=False``)
     - Interaction loops
   * - ``None`` (default)
     - Monitor's max rate at current resolution, or 60 Hz if unknown
     - Same
   * - ``0``
     - No rate limit — ``flip()`` runs flat out
     - Same as ``None`` (still rate-limited)
   * - positive, e.g. ``120``
     - Paces to that rate
     - Same
   * - negative, e.g. ``-1``
     - No rate limit, same as ``0``
     - Raises ``ValueError``

Known rough edge, not deliberate design — don't rely on ``0``/negative
behavior being stable across the two paths.

This normally costs nothing: the monitor's rate is detected correctly, so
both paths use it directly. TachyPy paces to the *highest* rate at the
current resolution rather than whatever the current mode reports, since
adaptive-refresh displays (e.g. ProMotion) can otherwise get stuck at a
transient idle rate. The 60 Hz fallback only applies when GLFW can't report
any rate at all — and guesses low rather than high, since an over-eager
schedule can stall input polling (same thread) more than a slow one.

Screen initialization warnings
-------------------------------

``Screen`` can print up to three ``[TachyPy WARNING]`` diagnostics to
stderr at construction, each firing at most once:

``screen_number`` out of range
   Falls back to monitor 0, listing every detected monitor's name and max
   refresh rate.

Requested rate exceeds the display
   ``desired_refresh_rate`` exceeds the monitor's highest rate at the
   current resolution.

Display rate unknown
   GLFW couldn't report any rate, so TachyPy guesses 60 Hz. Suppressed when
   ``vsync=False`` with ``desired_refresh_rate`` set, since that's used
   instead.

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
