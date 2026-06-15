Wooting Analog Keyboards
========================

TachyPy integrates with **tachywooting**, a hardware toolbox for Wooting analog
keyboards (analog pressure acquisition,
hierarchical HDF5 logging, light-press / release readiness checks). The hardware
toolbox is usable on its own; this page documents only what becomes available
**inside TachyPy** once the integration is installed — chiefly on-screen visual
pressure feedback. For the full keyboard/logging reference, see tachywooting's own
documentation.

Installation
------------

The integration ships as an optional extra. It pulls ``tachywooting`` and exposes
the keyboard through the top-level ``tachypy`` namespace:

.. code-block:: bash

   pip install "tachypy[wooting]"

(See `First-time setup`_ below for the one-time native/permissions step.)

One import surface
------------------

The enriched ``WOOTING_ACQUISITION`` — the hardware acquisition class plus TachyPy
visual feedback — is available straight from the top-level package:

.. code-block:: python

   from tachypy import WOOTING_ACQUISITION  # keyboard + visual feedback

You never import ``tachywooting`` directly. ``WOOTING_ACQUISITION`` is the only
keyboard symbol exposed at the top level (it is the common entry point and its
name is unambiguous). The rest of the keyboard surface — the helpers
(``convert_char_to_keycode``, ``load_trial``, ``load_session``,
``trial_to_dataframe``, ``visualize``, ``visualize_all_keys``) and the low-level
CFFI handles ``lib`` and ``ffi`` — lives under :mod:`tachypy.wooting`:

.. code-block:: python

   from tachypy.wooting import visualize, load_trial, convert_char_to_keycode

First-time setup
----------------

The first time you create a ``WOOTING_ACQUISITION``, TachyPy builds the native
interface automatically if it is missing (this needs only a C compiler, no admin
rights). The Wooting **SDK plugins and input permissions**, however, require a
one-time privileged step:

.. code-block:: bash

   wooting-build-interface   # installs SDK plugins + permissions (needs admin)

If the keyboard is not detected, the error message tells you exactly to run this
command — you do not have to remember it.

Basic keyboard use
------------------

The enriched class behaves exactly like the hardware acquisition class for
acquisition and logging:

.. code-block:: python

   from tachypy import WOOTING_ACQUISITION

   acq = WOOTING_ACQUISITION(threshold=0.8)
   acq.initialize_keyboard(verbose=True)
   try:
       # Instantaneous analog pressure (0.0–1.0) of one or more keys
       print(acq.read_pressure("C"))
       print(acq.read_pressures(["C", "Z"]))

       # Block until keys are held in the light-press range (no display needed)
       acq.wait_keys_light_press(target_keys=["C", "Z"], quit_key="Q")

       # Record an analog trial and write it to an HDF5 shard
       acq.setup_logging(name="tracking", path="logs", int_analog=2)
       trial = acq.acquire_analog_values(target_keys=["C", "Z"])
   finally:
       acq.uninitialize_keyboard()

Visual pressure feedback
------------------------

``wait_light_press_visual`` shows an interactive fixation cross while waiting for
two keys to stay within the light-press interval for ``hold_seconds``. It needs a
TachyPy :class:`~tachypy.Screen`; pass a :class:`~tachypy.ResponseHandler` to allow
the participant to abort:

.. code-block:: python

   from tachypy import Screen, ResponseHandler, FixationCross
   from tachypy import WOOTING_ACQUISITION

   acq = WOOTING_ACQUISITION(threshold=0.8, min_pressure_start=0.33, max_pressure_start=0.66)
   acq.initialize_keyboard()

   screen = Screen(fullscreen=False)
   rh = ResponseHandler(screen=screen)
   fixation = FixationCross(center=(screen.width // 2, screen.height // 2),
                            half_width=18, half_height=18, thickness=8, color=(0, 0, 0))

   ready = acq.wait_light_press_visual(
       target_keys=["c", "z"],
       screen=screen,
       response_handler=rh,
       fixation_cross=fixation,   # geometry + color copied automatically
       show_pressure_text=True,
       show_goal_markers=True,
   )

The horizontal bar grows and shrinks with pressure, turns toward the target color
as the hold completes, and (optionally) shows live pressure values for keys that
fall outside the acceptable interval.

.. image:: gifs/wooting-visual-fixation-demo.gif
   :alt: Interactive fixation cross with real-time pressure feedback
   :width: 100%

Custom widgets (advanced)
-------------------------

``wait_light_press_visual`` builds an
:class:`~tachypy.feedback.InteractiveFixationCross` by default. To render feedback
differently, subclass :class:`~tachypy.feedback.PressureFeedbackWidget` and pass it
via ``widget=``. The pressure state machine
(:class:`~tachypy.feedback.PressureFeedbackState`) and the pressure-to-scale mapper
(:class:`~tachypy.feedback.PressureScaleMapper`) are reusable building blocks. See
:doc:`api` for the full ``tachypy.feedback`` reference.

These tools are keyboard-agnostic: any object exposing the
:class:`~tachypy.feedback.PressureSource` contract (``read_pressures`` plus the
light-press thresholds) can drive the same feedback loop.

Console demos
-------------

The integration installs two on-screen demos (they require a display):

.. code-block:: bash

   tachypy-wooting-fixation-demo   # gamified interactive fixation cross
   tachypy-wooting-mini-bw         # minimal black/white response experiment

.. image:: gifs/wooting-mini-bw-experiment.gif
   :alt: Minimal black/white response experiment
   :width: 100%
