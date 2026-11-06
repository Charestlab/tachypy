Audio
=====

``tachypy.Audio`` plays sound buffers through the ``tachyaudio`` backend. It is
built so a non-audio experiment gets a dead-simple "play this now" call, while
timing-critical stimuli use scheduled device-clock onsets by default —
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

``Audio`` uses native timing by default on every supported OS:

- ``timing_mode="native"`` (default): device-clock scheduling through Core Audio
  on macOS, direct ALSA on Linux, and WASAPI on Windows. Device errors raise;
  Linux requires an explicit ``device_id="hw:..."``.
- ``timing_mode="auto"``: selects native when structurally available, otherwise
  falls back to software with a one-time warning (an older build without the
  scheduler, or Linux without a hardware device). Device-open failures raise.
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
  Linux, Windows, and older backends retain ``now + lead_time + 5 ms``.
- **Simplest precise form:** ``play_after(data, seconds)`` schedules playback after the requested delay. In native mode, the delay starts once
  the device is ready; allow more than the device lead time. To align several sounds to one instant, read it once with
  ``now()``::

     t0 = audio.now()
     audio.play(reference, when=t0 + 0.25)
     audio.play(target, when=t0 + 0.25 + len(reference) / sample_rate)

  ``now()`` returns the exact clock ``when=`` expects; ``prepare()`` only syncs the
  device to it, so calling ``now()`` before or after ``prepare()`` is equivalent.
- Up to 32 sounds queue ahead on one stream, back to back or overlapping.
  Sounds whose onsets overlap in time are mixed (summed and clamped to [-1, 1]).
- ``play(data)`` with no ``when`` schedules at the soonest valid onset for you; an
  explicit ``when`` must be at least ``lead_time`` ahead or the call raises.
- Call ``prepare()`` once during setup so the device-open cost is off the
  timing-critical path (``play()`` opens it lazily otherwise).
- Each Future returns a ``ScheduledTiming`` (device-clock estimates, not acoustic
  measurements). Cancel with ``stop()``, not ``Future.cancel()``; samples already
  handed to the device cannot be recalled.

The device clock and ``prepare()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To place an onset at a ``time.monotonic()`` instant, native mode must know how the
Python clock maps to the **audio hardware clock** — the two drift apart.
``prepare()`` (and the first ``play()`` if you skip it) opens the device, starts it,
and waits briefly for the hardware to deliver its first timing callbacks, which
establishes that mapping. **This short wait is the synchronization; it is required,
not a delay to avoid.** Do it once at setup so it is off the timing-critical path.

Native mode adapts this wait to the output: **wireless routes (Bluetooth, AirPods,
AirPlay) are given up to ~10 s** to spin up, wired/built-in outputs only ~2 s (a
healthy device returns the moment its first callbacks arrive, so this costs nothing
in practice). ``prepare()`` only raises ``Core Audio clock did not become ready;
close and reopen`` if the device still produced no clock in that window — i.e. it is
genuinely stuck or mid-handoff. If you hit it:

- Retry ``prepare()`` once — a transitioning Bluetooth device usually settles.
- Or pass ``device_id="BuiltInSpeakerDevice"`` (the most reliable clock source).
- Make sure nothing else is reconfiguring the default device at that moment.

Keep interactive plotting on the main thread. Audio futures normally complete on
playback workers, so do not call ``plt.show()`` or update GUI widgets from a future
callback. For plots shown after a trial, wait for playback and leave the
``with Audio(...) as audio:`` block before showing the figure.

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
- **Windows** — shared-mode, event-driven WASAPI. ``device_id=None`` uses the
  default output; explicit ids come from ``tachyaudio.list_devices()``.
  Use the endpoint's float32 mix sample rate (commonly 48 kHz); no resampling
  is performed. Omit ``latency``: Windows uses its default shared-engine period.
  When Python uses ``GetTickCount64()`` for ``time.monotonic()``, caller deadlines
  are tick-quantized even though rendering uses QPC timestamps.

TachyPy requires ``tachyaudio>=0.2.0b4,<2``, including Windows native scheduling.
Compatible platform wheels install automatically from PyPI.
Older builds without a native scheduler fail explicitly in the default mode.

Reference
---------

================================  ============================================================
Call                              Behavior
================================  ============================================================
``play(data)``                    Play now; returns a ``Future``.
``play(data, when=t)``            Play with the onset at monotonic time ``t``.
``play_after(data, seconds)``     Play ``seconds`` from now (clock handled for you); returns a ``Future``.
``now()``                         "Now" on the clock ``when=`` uses; anchor several onsets to one instant.
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
  device buffer in seconds (``None`` requests 1 ms on macOS; Linux chooses its buffer; omit on Windows).
- ``timing_mode`` — ``"native"`` (default), ``"auto"``, or ``"software"``.
- ``minimum_lead_time`` — native only; override the advance notice (``None``
  derives it from the device's measured output delay).
- ``latency_bias`` — native, macOS only; seconds added to the onset compensation to
  calibrate a device whose true latency the HAL misreports (see `Bluetooth / wireless
  outputs`_). ``None`` applies no bias.
- ``timeout`` — software: write/drain timeout; native: total completion timeout,
  including the wait until the scheduled onset.
- ``block_size`` — software only; rejected in native mode.

Bluetooth / wireless outputs
----------------------------

Bluetooth (AirPods, wireless headphones) and AirPlay **cannot give precise acoustic
onset timing**, because the sink's jitter buffer adds a large, variable latency that
the operating system does not fully report. For anything timing-critical (interaural
delays, audio–visual sync, reaction-time onsets), use a **wired or built-in** output.

If you must use Bluetooth, you can get the **mean** onset accurate — the residual
jitter stays — by calibrating the systematic offset:

1. Keep the stream **output-only** (do not open the microphone; that drops AirPods
   into low-quality hands-free mode). ``Audio`` already opens output only.
2. Measure your device's true delay once (an acoustic loopback, e.g. tachyaudio's
   ``examples/measure_coreaudio_loopback.py``, or a known reference), then pass the
   extra latency the OS under-reported as ``latency_bias``:

   .. code-block:: python

      # measured true latency − reported presentation_latency_us ≈ 80 ms, say
      audio = Audio(timing_mode="native", device_id="<airpods id>", latency_bias=0.080)

Native mode already tracks the device's clock drift per callback, so within one
connection a calibrated bias holds reasonably well; reconnecting the device can
change the offset, so re-check after a reconnect.

Errors and lifecycle
--------------------

Device-open errors raise from ``play()`` or ``prepare()``. Playback-worker errors
are raised by ``future.result()`` or ``audio.wait()``, also emit a warning, and
are stored in ``audio.last_error``; the failed stream is closed and the next
``play()`` opens a fresh one. Playback is never auto-retried — replaying a
stimulus after its deadline could invalidate a trial. ``stop()`` cancels
everything (those Futures raise ``concurrent.futures.CancelledError``) and the
``Audio`` instance can be reused afterwards.

Recording from the microphone
-----------------------------

``tachypy.Microphone`` captures audio as NumPy ``float32`` arrays (backed by
``tachyaudio``'s input stream). Open, record, close — same style as ``Audio``:

.. code-block:: python

   from tachypy import Microphone

   with Microphone(sample_rate=48000, channels=1) as mic:
       clip = mic.record(2.0)          # blocks 2 s; float32 array, shape (96000,)
   # device released on exit

- ``record(seconds)`` discards anything buffered, then captures exactly
  ``round(seconds * sample_rate)`` frames and returns them — shape ``(N,)`` for mono,
  ``(N, channels)`` otherwise.
- To stream instead, ``start()`` then ``read(frames)`` (up to ``frames`` already
  captured) or ``read_exactly(frames, timeout=...)`` (waits), then ``stop()`` /
  ``close()``. ``flush()`` drops buffered input.
- ``Microphone(...)`` takes ``sample_rate``, ``channels``, and keyword-only
  ``device_id`` (``None`` = default input), ``latency`` and ``block_size``.
- **macOS:** the first capture triggers the microphone permission prompt. Grant it in
  System Settings → Privacy & Security → Microphone (if denied, you get silence or an
  error). The ``tachyaudio-audio-report`` command also checks capture permissions.

Install
-------

.. code-block:: bash

   pip install tachypy

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
