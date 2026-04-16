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

Installing sounddevice prerequisites
------------------------------------

``sounddevice`` may require PortAudio system libraries.

Linux (Debian/Ubuntu):

.. code-block:: bash

   sudo apt update
   sudo apt install libportaudio2 libportaudiocpp0 portaudio19-dev

macOS:

Install Homebrew (if needed):

.. code-block:: bash

   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

Then install PortAudio:

.. code-block:: bash

   brew install portaudio

Windows:

Pip wheels for ``sounddevice`` often work directly. If not, one workaround is:

.. code-block:: bash

   choco install portaudio
