Testing and Development
=======================

TachyPy includes an automated ``pytest`` suite focused on deterministic,
headless-safe checks for core logic and backend regressions.

What is covered
---------------

- Audio scheduling and channel-shape validation.
- TachyAudio-backed scheduling and channel-shape validation.
- Response handling state transitions (key press/release behavior).
- Draggable object movement and boundary clamping.
- GLFW drag/input behavior.
- Psychophysics helper invariants (shape/range and edge cases).
- Text object line processing edge cases.

Run tests
---------

From the repository root:

.. code-block:: bash

   pip install -e ".[test]"
   pytest

Coverage
--------

Coverage runs by default through pytest configuration:

.. code-block:: bash

   pytest

The suite currently enforces a minimum line coverage threshold in CI.

Add new tests
-------------

- Prefer pure logic tests over rendering integration tests where possible.
- Mock GLFW/OpenGL interactions when asserting non-rendering behavior.
- Add regression tests for every bug fix before release.
- Mock ``tachyaudio.OutputStream`` in CI and keep hardware audio tests separate.

Manual diagnostics
-------------------

Some checks need a real display and human judgment, so they live in
``tests/`` as plain scripts rather than ``pytest`` cases — not collected by
the automated suite, and not installed as a console command, since they're
for TachyPy developers, not experiment authors.

``tests/manual_fps_probe.py``
   Measures the actual achieved ``flip()`` rate under VSync, with no
   drawable content. Useful for sanity-checking VSync/pacing behavior on a
   new machine, after a GLFW/platform update, or when investigating a
   suspiciously low frame rate before suspecting your own drawables or
   hardware polling. Reports a tight, unpaced loop and a paced measurement
   using the same ``LoopPacer`` as ``interact_slider`` and
   ``wait_light_press_visual``.

   .. code-block:: bash

      python tests/manual_fps_probe.py            # fullscreen
      python tests/manual_fps_probe.py --windowed  # windowed, for development
