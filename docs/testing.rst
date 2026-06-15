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
