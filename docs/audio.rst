Audio
=====

Audio class
-----------

``tachypy.Audio`` is now a convenience scheduler over ``tachyaudio``. TachyPy no
longer owns sounddevice or dummy audio backends; low-level device handling,
streaming, buffering, and latency statistics live in ``tachyaudio``.

Basic playback:

.. code-block:: python

   import numpy as np
   from tachypy import Audio

   audio = Audio(sample_rate=48000, channels=1)
   tone = np.zeros(4800, dtype=np.float32)
   audio.play(tone)

Scheduling
----------

``Audio.play(data, when=...)`` keeps the old TachyPy convenience API. ``when`` is
an absolute monotonic time in seconds. Internally, TachyPy waits until that time
and then writes the contiguous float32 frame buffer to ``tachyaudio.OutputStream``.

.. code-block:: python

   import time

   audio = Audio(sample_rate=48000, channels=2, latency=0.01)
   audio.play(stereo_buffer, when=time.monotonic() + 0.250)

Configuration
-------------

The following parameters are passed through to ``tachyaudio.OutputStream``:

- ``sample_rate``
- ``channels``
- ``block_size``
- ``device_id``
- ``latency``
- ``timeout`` for write/drain operations

The retained ``backend`` argument accepts only ``None``, ``"auto"``, or
``"tachyaudio"``. Legacy ``"sounddevice"`` and ``"dummy"`` values now raise a
``ValueError``.

Installation
------------

The base TachyPy install depends on ``tachyaudio>=0.2.0b1``. In most cases, pip
can resolve this dependency without enabling global pre-release selection:

.. code-block:: bash

   pip install tachypy

If your resolver does not accept the tachyaudio pre-release automatically, retry
with:

.. code-block:: bash

   pip install --pre tachypy

For direct development installs:

.. code-block:: bash

   pip install --pre -e .

Testing
-------

Unit tests mock ``tachyaudio.OutputStream``. Hardware/audio-device validation
should remain a dedicated local or lab-machine test, separate from CI.
