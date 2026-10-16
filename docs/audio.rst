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

Experimental native scheduling (macOS, Linux ALSA)
----------------------------------------------------

Requires the companion tachyaudio native-scheduling development build; the
released minimum dependency 0.2.0b2 does not provide this API. Install that build
before testing this branch. Unsupported platforms or old builds fail explicitly.
The default software mode remains compatible with the existing dependency.

On Linux, native scheduling goes through direct ALSA, not PulseAudio/PipeWire.
Pass an explicit hardware device, e.g. ``device_id="hw:CARD=PCH,DEV=0"``
(list candidates with ``aplay -L``); ``default``/``pulse``/``plughw`` device
ids are rejected. tachyaudio negotiates float32, then signed-32, then
signed-16 interleaved output depending on what the codec supports — check
``tachyaudio.ScheduledOutputStream(...).status()['device_format']`` if you
need to know which was selected. The worker thread makes a best-effort
request for real-time (``SCHED_FIFO``) scheduling; on an unprivileged account
without an ``RLIMIT_RTPRIO`` grant this silently falls back to normal
priority (see tachyaudio's ``docs/ubuntu-scheduling.md`` for how to grant it
on a lab machine for better protection against underruns under load).

.. code-block:: python

   import time
   import numpy as np
   from tachypy.audio import Audio

   audio = Audio(sample_rate=48000, channels=1, timing_mode="native",
                 minimum_lead_time=0.050, timeout=2)
   try:
       audio.prepare()
       stimulus = np.zeros(4800, dtype=np.float32)
       timing = audio.play(stimulus, when=time.monotonic() + 0.250).result()
       print(timing.predicted_error_seconds)
   finally:
       audio.close()

``play`` copies and submits the entire stimulus synchronously, before returning.
The native callback then places samples against the device output clock without
requiring Python to run at onset. Choose the device's actual sample rate; no
resampling or device rate changes are performed. Mono duplicates to all device
output channels; otherwise use the complete device output channel count.
``block_size`` and ``latency`` must be omitted in this mode.

Only one outstanding stimulus is supported per Audio instance. Even requests for
nonoverlapping future times are rejected until the current Future completes.
``when=0``, past deadlines, insufficient lead, and native failures are errors,
not requests to play late. Lead is checked after copying as well as before it;
allow margin for preparation. Prepare well before choosing the deadline.

The Future returns ``tachyaudio.ScheduledTiming`` after rendering and estimated
device completion, not after externally confirmed acoustic completion. Its
``predicted_error_seconds`` is a device-clock estimate. Late rendering may drop
the stimulus or truncate a stimulus already in progress; mark that trial invalid.
Calling ``future.result(timeout=...)`` only limits the caller's wait; it does not
cancel playback. ``Audio(timeout=...)`` limits native completion from the worker
start, including the scheduled lead. ``stop()`` cancels and closes; samples already
handed to hardware cannot be recalled. ``Future.cancel()`` cannot cancel native
requests because submission has already occurred. Stream reuse happens after
estimated completion, and native worker failures remain visible via the Future,
``last_error``, and a warning.

Run the silent end-to-end probe on a macOS device configured for 48 kHz:

.. code-block:: bash

   python examples/measure_native_audio.py --trials 100 --output native-results.json

It tests idle playback and holding Python's GIL across onset, preserving failures
and raw internal estimates. It does not measure voltage at the output or sound
at the ear. See tachyaudio's ``docs/electrical-loopback.md`` for external validation
and ``docs/native-scheduling.md`` for the architecture and acceptance protocol.
