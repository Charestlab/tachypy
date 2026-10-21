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
   try:
       audio.prepare()
       playback = audio.play(tone)
       playback.result(timeout=2)
   finally:
       audio.close()

Scheduling
----------

The following describes the default ``timing_mode="software"``. Native mode is
explicitly opt-in; it never silently falls back to software scheduling.

``Audio.play(data, when=...)`` keeps the old TachyPy convenience API. ``when`` is
an absolute monotonic time in seconds. Internally, TachyPy waits until that time
and then writes the contiguous float32 frame buffer to ``tachyaudio.OutputStream``.

Call ``prepare()`` before the first timing-sensitive trial to open and warm the
device. Sequential sounds reuse one stream. Overlapping sounds retain their
previous behavior by using separate streams; only one idle stream is retained
after completion. Close each ``Audio`` instance when the experiment finishes.
The scheduled time is the software submission time, not a measured acoustic
onset. Device buffering still adds latency.

On Linux this mode goes through tachyaudio's ``miniaudio`` backend and the
desktop sound server (PulseAudio/PipeWire), so ``device_id`` values are
sound-server nodes from ``tachyaudio.list_devices()``. Measured by acoustic
loopback, onsets varied by 3.4 ms (standard deviation) around ``when``. For
timing-critical stimuli use native mode (below), which bypasses the server.

``play()`` returns a ``concurrent.futures.Future``. Device-open errors are raised
directly from ``play()`` or ``prepare()``; worker errors are raised by
``playback.result()`` or ``audio.wait()`` (which waits for the latest request).
Worker failures also emit a warning and are stored in ``audio.last_error``.
Failed streams are closed, and the next request opens a fresh stream. Playback
is not automatically retried because replaying an experimental stimulus after
its deadline could invalidate the trial.

``stop()`` cancels both scheduled and active sounds, waits for their workers to
release the streams, and closes the idle stream. Cancelled playback results raise
``concurrent.futures.CancelledError``. ``Audio`` can be used again after stopping.
Audio data is copied when submitted so later edits cannot alter a scheduled sound.

The unreleased tachyaudio drain changes are needed to keep macOS streams warm
after playback. With tachyaudio 0.2.0b2, stream reuse still works but macOS pays
the device-start cost again after draining.

.. code-block:: python

   import time

   audio = Audio(sample_rate=48000, channels=2, latency=0.01)
   audio.play(stereo_buffer, when=time.monotonic() + 0.250)

Configuration
-------------

In the default software mode, the following parameters are passed through to
``tachyaudio.OutputStream`` (native mode: see below; ``latency`` there is the
Linux ALSA buffer and ``block_size`` is rejected):

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

The base TachyPy install depends on ``tachyaudio>=0.2.0b2``. In most cases, pip
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

Native scheduling (macOS, Linux)
--------------------------------

``timing_mode="native"`` hands each sound to tachyaudio's
``ScheduledOutputStream``: native code places its first sample on the device
clock at ``when``, without Python running at onset. Measured on Linux by
acoustic loopback, onset jitter was about 70 µs, against 3.4 ms for the
software mode; use it for timing-critical stimuli, with a wired interface. It
needs a tachyaudio build newer than 0.2.0b2 (install from source until the next
release) and fails explicitly otherwise.

On Linux it plays through ALSA directly, bypassing PulseAudio/PipeWire, so it
needs a hardware ``device_id``. Leave it out once: the error lists every output
(monitor speakers over HDMI/DisplayPort included) with its id and whether it is
free. On macOS the default output is used unless ``device_id`` is given.

.. code-block:: python

   import time
   import numpy as np
   from tachypy.audio import Audio

   tone = (0.1 * np.sin(2 * np.pi * 1000 * np.arange(4800) / 48000)).astype(np.float32)

   audio = Audio(sample_rate=48000, device_id="hw:CARD=PCH,DEV=0", timing_mode="native")
   try:
       audio.prepare()
       start = time.monotonic() + 0.100
       first = audio.play(tone, when=start)
       second = audio.play(tone, when=start + len(tone) / 48000)  # back to back
       print(first.result().predicted_onset_ns, second.result().predicted_onset_ns)
   finally:
       audio.close()

Only ``device_id`` (Linux), ``sample_rate`` and ``timing_mode`` are needed:
``latency`` (the ALSA buffer) and ``minimum_lead_time`` are chosen
automatically, and mono stimuli are copied to every device channel. tachyaudio's
``docs/linux-scheduling.md`` lists every parameter and common errors.

- ``play`` copies the stimulus and submits it before returning. ``when`` must be
  at least the stream's lead time ahead (measured on Linux, 8–12 ms on the
  devices tested; 50 ms on macOS). A late or too-close deadline raises; nothing
  is played late.
- Several sounds can be queued ahead (Linux: up to 32; macOS: one at a time),
  back to back if wanted. Sounds overlapping in time are rejected.
- Each Future returns ``tachyaudio.ScheduledTiming``, device-clock estimates
  rather than acoustic measurements, after estimated completion. A dropped
  sound raises: mark the trial invalid. Failures also go to ``last_error`` and
  a warning.
- ``future.result(timeout=...)`` only limits the wait; ``Audio(timeout=...)``
  limits completion. Cancel with ``stop()``, not ``Future.cancel()``; samples
  already in the device cannot be recalled.
- The sample rate must be one the device supports (nothing is resampled);
  ``block_size`` is rejected.

On macOS, a silent end-to-end probe tests idle playback and Python holding the
GIL across onset:

.. code-block:: bash

   python examples/measure_native_audio.py --trials 100 --output native-results.json

It reports internal estimates, not sound at the ear; see tachyaudio's
``docs/electrical-loopback.md`` for external validation.
