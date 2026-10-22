Audio
=====

``tachypy.Audio`` plays sound buffers through the ``tachyaudio`` backend. It is
built so a non-audio experiment gets a dead-simple "play this now" call, while
timing-critical stimuli can opt into microsecond-precise, device-clock onsets —
with the same ``play()`` call. TachyPy no longer owns any audio backend itself;
device handling, buffering and latency live in ``tachyaudio``.

Quick start
-----------

.. code-block:: python

   import numpy as np
   from tachypy import Audio

   audio = Audio(sample_rate=48000, channels=1)
   tone = (0.1 * np.sin(2 * np.pi * 440 * np.arange(24000) / 48000)).astype(np.float32)

   audio.play(tone)        # play now
   audio.wait()            # optional: block until it finishes
   audio.close()           # when the experiment ends

- ``play(data)`` plays as soon as the device can; ``play(data, when=t)`` places
  the onset at absolute monotonic time ``t`` (``time.monotonic()`` clock).
- ``play()`` returns a ``concurrent.futures.Future``: ``future.result(timeout)``
  waits and raises any failure, or call ``audio.wait()`` for the latest sound.
- Mono ``data`` is duplicated to every channel; the array is copied on submit, so
  you may reuse or edit it immediately.
- By default ``Audio`` already uses the precise native scheduler when the platform
  supports it (see `Timing modes`_), so you get good onset precision for free.
- Call ``close()`` (or ``stop()``) when finished to release the device.

Timing modes
------------

``Audio`` picks the best timing automatically:

- ``timing_mode="auto"`` (default): the precise ``native`` scheduler when it can be
  set up, otherwise ``software`` with a one-time warning — so an experiment that is
  not about audio still gets device-clock precision where possible, without having
  to ask for it.
- ``timing_mode="native"``: forces the device-clock scheduler and **raises** if it
  is unavailable (macOS Core Audio; Linux via direct ALSA with
  ``device_id="hw:..."``; not on Windows) — a hard error instead of a silent
  downgrade, for when precise timing is required.
- ``timing_mode="software"``: forces the OS-mixer path (works everywhere).

Scheduled onset precision and immediate response time are different measurements.
Use ``when=`` to align a stimulus to a predetermined instant. On macOS, native
``play(data)`` instead takes the first available callback after copying the sound;
its delay varies with callback phase and device latency.

Precise timing (native mode)
----------------------------

.. code-block:: python

   import time, numpy as np
   from tachypy import Audio

   tone = (0.1 * np.sin(2 * np.pi * 1000 * np.arange(4800) / 48000)).astype(np.float32)

   audio = Audio(sample_rate=48000, channels=1, timing_mode="native", latency=0.005)
   try:
       audio.prepare()                              # open + warm the device once, at setup
       audio.play(tone)                             # now, on the device clock
       start = time.monotonic() + 0.200
       a = audio.play(tone, when=start)             # precise future onset
       b = audio.play(tone, when=start + len(tone) / 48000)  # back to back
       print(a.result().predicted_onset_ns, b.result().predicted_onset_ns)
   finally:
       audio.close()

- **For a precisely controlled onset, schedule with** ``when=`` computed ahead of
  the onset (relative to your trial clock), giving the scheduler its full
  ``lead_time``. ``play(data)`` without ``when`` is the convenient "play now" form:
  on macOS it uses the next available native callback, without a lead or 5 ms
  margin. It requires an idle stream; wait for the previous sound first.
  Linux and older backends retain ``now + lead_time + 5 ms``.
- Up to 32 sounds queue ahead on one stream, back to back or overlapping.
  Sounds whose onsets overlap in time are mixed (summed and clamped to [-1, 1]).
- ``play(data)`` with no ``when`` schedules at the soonest valid onset for you; an
  explicit ``when`` must be at least ``lead_time`` ahead or the call raises.
- Call ``prepare()`` once during setup so the device-open cost is off the
  timing-critical path (``play()`` opens it lazily otherwise).
- Each Future returns a ``ScheduledTiming`` (device-clock estimates, not acoustic
  measurements). Cancel with ``stop()``, not ``Future.cancel()``; samples already
  handed to the device cannot be recalled.

For the fastest onset your machine can sustain without glitches, measure it once at
setup with tachyaudio's **silent** probe and pass the result:

.. code-block:: python

   import tachyaudio as ta
   s = ta.fastest_safe_settings(device_id="BuiltInSpeakerDevice")  # ~1 s, silent, under CPU load
   audio = Audio(timing_mode="native", latency=s.latency, minimum_lead_time=s.minimum_lead_time)

It sweeps buffers from the hardware minimum up and returns the fastest that ran a
dense burst of zero-filled sounds with no dropped/late onset (nothing audible, no
microphone). Re-run it per machine — smaller buffers have thinner timing margin on
slower or busier hardware. The ``tachyaudio-audio-report`` command does the full
diagnostic (latencies, jitter, lead search).

Platform notes (native):

- **macOS** — Core Audio. ``device_id=None`` uses the default output, or pass
  ``"BuiltInSpeakerDevice"``. ``latency=None`` requests a 1 ms buffer in native mode;
  ``latency=0.005`` requests a 5 ms buffer (a shared device setting, restored on
  close on a best-effort basis). Smaller explicit buffers are accepted when supported by the hardware. Onset jitter is
  ~5 µs and the advance notice (``lead_time``) is ~21 ms at a 1 ms buffer; the
  fixed hardware presentation latency (~16 ms on the tested Mac) is physical and
  cannot be reduced. See tachyaudio ``docs/native-scheduling.md``.
- **Linux** — direct ALSA, bypassing PulseAudio/PipeWire, so it needs a hardware
  ``device_id="hw:CARD=...,DEV=..."``. Omit it once and the raised error lists
  every output (HDMI/DisplayPort monitor speakers included) with its id and
  whether it is free. ``latency=None`` auto-selects the buffer (real-time
  priority: ~2 ms onboard/PCI, 5 ms USB). Onsets land on the sample grid and are
  never early, so placement error is 0–1 sample: 20.8 µs at 48 kHz, 5.2 µs at
  192 kHz — use the highest ``sample_rate`` your device supports when precision
  matters. See tachyaudio ``docs/linux-scheduling.md``.
- **Windows** — native scheduling is unavailable; software mode works.

Native scheduling needs a ``tachyaudio`` build newer than 0.2.0b2 (install from
source until the next release); it fails explicitly on an older build.

Reference
---------

================================  ============================================================
Call                              Behavior
================================  ============================================================
``play(data)``                    Play now; returns a ``Future``.
``play(data, when=t)``            Play with the onset at monotonic time ``t``.
``wait(timeout=None)``            Wait for the most recent sound; re-raises its failure.
``prepare()``                     Open and warm the device ahead of the first sound.
``stop()``                        Cancel all pending/active sounds; the instance stays usable.
``close()``                       Stop and release the device.
``is_playing``                    True while any sound is pending or playing.
``last_error``                    The most recent worker failure, or ``None``.
================================  ============================================================

``Audio(...)`` parameters:

- ``sample_rate``, ``channels`` — of your buffers; no resampling is done.
- ``device_id`` — output device (see each mode's note); ``None`` is the default.
- ``latency`` — software: the ``OutputStream`` buffer in seconds; native: the
  device buffer in seconds (``None`` requests 1 ms on macOS; Linux chooses its buffer).
- ``timing_mode`` — ``"auto"`` (default), ``"native"``, or ``"software"``.
- ``minimum_lead_time`` — native only; override the advance notice (``None``
  derives it from the device's measured output delay).
- ``timeout`` — software: write/drain timeout; native: total completion timeout,
  including the wait until the scheduled onset.
- ``block_size`` — software only; rejected in native mode.

Errors and lifecycle
--------------------

Device-open errors raise from ``play()`` or ``prepare()``. Playback-worker errors
are raised by ``future.result()`` or ``audio.wait()``, also emit a warning, and
are stored in ``audio.last_error``; the failed stream is closed and the next
``play()`` opens a fresh one. Playback is never auto-retried — replaying a
stimulus after its deadline could invalidate a trial. ``stop()`` cancels
everything (those Futures raise ``concurrent.futures.CancelledError``) and the
``Audio`` instance can be reused afterwards.

Install
-------

.. code-block:: bash

   pip install tachypy          # add --pre if the tachyaudio pre-release is rejected

Caveats and validation
----------------------

Reported times are a software submission time (software mode) or device-clock
estimates (native mode), **not** an externally measured acoustic onset — device
buffering and the fixed hardware presentation latency still apply. Validate with
``examples/measure_native_audio.py`` (silent scheduling under Python load) and
tachyaudio's ``examples/measure_coreaudio_loopback.py`` (acoustic intervals
through the integrated speakers/microphone, constant delay and clock drift
removed). For absolute onset accuracy use an external reference; see tachyaudio's
``docs/electrical-loopback.md``.

To tune advance notice on your machine, run ``tachyaudio-audio-report --tune-only``.
It compares buffers and leads at idle and under CPU load, then validates the
shortest passing tested setting with fresh trials. Apply the reported ``latency``
and ``minimum_lead_time`` to ``Audio(timing_mode="native", ...)``. This is a
workload-specific result, not a safety guarantee; repeat with your actual stimuli.
``prepare()`` warms the stream; the lead controls earliest onset, not sound spacing.

For the shortest immediate response, run
``tachyaudio-audio-report --immediate-only --json immediate.json`` and apply its
validated ``latency``. Use ``--stimulus-ms 100`` to test longer sounds. The report
includes the hardware minimum, idle/loaded p99 delay and independent validation.
Call ``prepare()`` before the trial; first-play device startup is additional.
Immediate timing results expose ``submission_to_onset_seconds``;
``predicted_error_seconds`` applies only to explicit deadlines.
