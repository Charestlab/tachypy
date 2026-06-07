"""Development launcher for TachyPy's packaged clock/stopwatch demo."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from tachypy.examples.clock_timer_demo import main


if __name__ == "__main__":
    main()
