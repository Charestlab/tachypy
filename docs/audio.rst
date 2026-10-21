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
ALSA/HAL device buffer and ``block_size`` is rejected):

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
clock at ``when``, without Python running at onset. Measured by acoustic
loopback, onset jitter was about 70 µs on Linux (wired interface) and about
5 µs on macOS (integrated speakers/microphone), against 3.4 ms for the software
mode; the macOS figure held under Python CPU load. Use native mode for
timing-critical stimuli. It
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

``play()`` copies and queues up to 32 non-overlapping sounds. Submit each
``when`` at least the stream's lead time ahead; late requests raise. Call
``prepare()`` before computing the first deadline. Mono is duplicated across
device channels; no resampling is performed and ``block_size`` is rejected.

Each Future returns ``ScheduledTiming`` estimates after estimated completion.
``future.result(timeout=...)`` limits waiting; ``Audio(timeout=...)`` limits
completion. Cancel with ``stop()``, not ``Future.cancel()``. Samples already
sent to the device cannot be recalled. Playback failures also set ``last_error``.

``minimum_lead_time=None`` derives the advance notice from native output timing.
On Linux, ``latency=None`` selects the ALSA buffer automatically: with real-time
priority 2 ms on an onboard/PCI card (about 4.5 ms lead time) and 5 ms on USB.
Onsets land on the sample grid and are never early, so the placement error is
0 to 1 sample: up to 20.8 µs at 48 kHz and 5.2 µs at 192 kHz. Use the highest
``sample_rate`` your device supports when onset precision matters, and schedule
with some margin beyond the lead time. See tachyaudio's
``docs/linux-scheduling.md`` for device setup and parameters.

On macOS, omit ``device_id`` for the default output or use
``"BuiltInSpeakerDevice"`` for integrated speakers. Match the current device
sample rate, typically 48000 Hz. ``latency=None`` preserves the HAL buffer;
``latency=0.005`` requests 5 ms. This changes a shared device setting, restored
at close on a best-effort basis if unchanged by another client. Avoid conflicting
settings across concurrent streams. See tachyaudio's ``docs/native-scheduling.md``.

Validation probes:

- ``examples/measure_native_audio.py`` tests silent scheduling under Python load.
- tachyaudio's ``examples/measure_coreaudio_loopback.py`` measures acoustic
  intervals using the integrated speakers and microphone, removing constant
  delay and capture-clock drift.

Neither establishes absolute physical-onset accuracy; see tachyaudio's
``docs/electrical-loopback.md`` for external validation.
