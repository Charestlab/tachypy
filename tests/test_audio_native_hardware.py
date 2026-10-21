"""Opt-in silent integration with the real Core Audio scheduled queue."""
import os
import sys
import time
from concurrent.futures import CancelledError

import numpy as np
import pytest

from tachypy.audio import Audio

pytestmark = pytest.mark.skipif(
    sys.platform != 'darwin' or os.environ.get('TACHYPY_TEST_AUDIO_HARDWARE') != '1',
    reason='requires explicit Core Audio hardware testing',
)


def test_coreaudio_queues_32_futures_on_one_prepared_stream():
    audio = Audio(sample_rate=48000, channels=1, timing_mode='native',
                  device_id='BuiltInSpeakerDevice', latency=.005)
    try:
        audio.prepare()
        stream = audio._stream
        target = time.monotonic() + .3
        futures = [audio.play(np.zeros(480, dtype=np.float32), when=target + index*.01)
                   for index in range(32)]
        results = [future.result(timeout=3) for future in futures]
        assert audio._stream is stream
        assert all(result.rendered_frames == 480 for result in results)
        assert all(abs(right.predicted_onset_ns - left.predicted_end_ns) <= 20834
                   for left, right in zip(results, results[1:]))
        assert not audio.is_playing
        pending = audio.play(np.zeros(480, dtype=np.float32), when=time.monotonic()+1)
        audio.stop()
        with pytest.raises(CancelledError):
            pending.result(timeout=1)
        audio.prepare()
        assert audio._stream is not stream
    finally:
        audio.close()
