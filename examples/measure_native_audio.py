"""Silent macOS integration probe; device-clock estimates, not physical onset."""

import argparse
import json
import platform
import random
import sys
import time
from pathlib import Path

import numpy as np

from tachypy.audio import Audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 1 or args.output.exists():
        parser.error("positive trial count and a new output path required")
    records = []
    audio = Audio(sample_rate=48000, channels=1, timing_mode="native", timeout=2)
    previous_interval = sys.getswitchinterval()
    try:
        audio.prepare()
        for condition in ("idle", "python-held"):
            for trial in range(args.trials):
                target = time.monotonic() + random.uniform(0.100, 0.130)
                record = {"condition": condition, "trial": trial, "target": target}
                try:
                    future = audio.play(np.zeros(48, dtype=np.float32), when=target)
                    if condition == "python-held":
                        sys.setswitchinterval(0.5)
                        while time.monotonic() < target + 0.020:
                            pass
                        sys.setswitchinterval(previous_interval)
                    timing = future.result(timeout=2)
                    record.update(predicted_error_us=timing.predicted_error_seconds * 1e6,
                                  render_lead_ms=(timing.predicted_onset_ns -
                                                  timing.render_complete_ns) / 1e6)
                except Exception as error:
                    record["error"] = repr(error)
                finally:
                    sys.setswitchinterval(previous_interval)
                records.append(record)
    finally:
        sys.setswitchinterval(previous_interval)
        audio.close()
        args.output.write_text(json.dumps({"platform": platform.platform(),
                                          "python": sys.version, "records": records}, indent=2))
    failures = sum("error" in record for record in records)
    print(f"{len(records)} trials; {failures} failures; raw results: {args.output}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
