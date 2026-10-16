# Native audio integration validation — 2026-10-15

Development branch: `dev_0.2.3`, based on main `7d8b53f`.
Requires the companion tachyaudio `dev_0.2.0b3` branch.
No release or minimum dependency bump is included: native timing is opt-in and
old tachyaudio installations fail explicitly when native mode is selected.
Merge/release the tachyaudio API before advertising a pip-installable native mode.

## Automated checks

31 focused audio tests passed (existing lifecycle tests and new native tests).
New coverage: synchronous early submission, data copying, reuse, overlap rejection,
missing API, invalid deadlines/settings, cancellation, timeout and error propagation.
Ruff and `git diff --check` passed. These are audio-focused tests, not a claim that
the complete visual/experiment test suite or all Python versions were exercised.

## Silent hardware integration

macOS 26.5.1 arm64, Python 3.14.5, default output at 48 kHz, mono duplicated by
the native backend. One millisecond of zero samples per trial, scheduled
100–130 ms ahead; 100 idle and 100 main-thread GIL-held trials.

| Condition | Trials | Failures | Max predicted residual | Minimum render lead |
| --- | ---: | ---: | ---: | ---: |
| Idle | 100 | 0 | 19.992 us | 12.173 ms |
| Python held across onset | 100 | 0 | 20.724 us | 12.176 ms |

The raw JSON is retained locally in the tachyaudio workspace at
`build/tachypy-native-integration-2026-10-15.json`. Reproduce from this checkout
with both development packages installed:

```sh
python -m pytest tests/test_audio.py tests/test_audio_extended.py tests/test_audio_native.py
python examples/measure_native_audio.py --trials 100 --output native-results.json
```

The probe saves all failures and per-trial estimates, and holds Python across
onset to test that the native callback does not depend on the Python worker.
All submitted samples are zero: this tests scheduling and lifecycle, not audible
waveform fidelity. Future completion is estimated device completion.

These residuals are sample-grid calculations, not independently measured timing
accuracy. No electrical loopback, acoustic measurements, or paired PsychPortAudio
measurements have been performed. No Windows/Linux scheduled path was tested or
implemented. See the companion tachyaudio `docs/electrical-loopback.md` protocol.
