Audio
=====

Audio class
-----------

``Audio`` now uses a backend abstraction:

- ``sounddevice``: low-latency backend (recommended for timing-critical runs).
- ``dummy``: no-op backend for CI/headless testing.
- ``auto``: selects ``sounddevice`` when available, otherwise ``dummy``.

Backend selection
-----------------

Select backend in code:

.. code-block:: python

   from tachypy import Audio
   audio = Audio(sample_rate=44100, channels=1, backend="sounddevice")

Or through environment:

.. code-block:: bash

   TACHYPY_AUDIO_BACKEND=dummy pytest

CI guidance
-----------

Use the ``dummy`` backend in CI to avoid native audio-driver requirements.
Keep hardware/audio integration tests in dedicated jobs or local validation
passes.
