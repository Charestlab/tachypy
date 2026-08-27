"""Manual diagnostic: measure the actual achieved flip() rate under VSync.

Not part of the automated pytest suite -- it needs a real display and takes
several seconds, so it's meant to be run by hand, not in CI. Useful for
sanity-checking VSync/pacing behavior on a new machine, after a GLFW/platform
update, or when investigating a suspiciously low frame rate in an experiment:
run this first to see what the bare display/loop combo can achieve before
suspecting your own drawables or hardware polling.

Two independent things are compared:

* Tight loop: poll_events()+fill()+flip() back to back, no pacing. Mainly a
  sanity check that VSync is actually engaging at all -- if this comes back
  wildly higher than the reported monitor rate, events likely aren't being
  polled (see Screen.poll_events(); on macOS, VSync silently stops blocking
  flip() if the window's event queue isn't serviced).
* Paced: uses the same tachypy.screen.LoopPacer that interact_slider and
  wait_light_press_visual use internally, so this reflects what those loops
  can actually achieve independent of your own drawables/hardware polling.

Run windowed during development:

    python tests/manual_fps_probe.py --windowed

Run fullscreen (bypasses window compositing, generally closer to the
monitor's real rate):

    python tests/manual_fps_probe.py
"""
from __future__ import annotations

import argparse
import time

from tachypy import Screen
from tachypy.screen import LoopPacer, get_render_interval


def measure_tight_loop(screen: Screen, num_frames: int) -> float:
    """Mean flip() interval with no pacing at all. Returns 0.0 if unmeasurable."""
    intervals = []
    first_flip = True
    for _ in range(num_frames):
        screen.poll_events()
        screen.fill((128, 128, 128))
        screen.flip()
        interval = screen.get_flip_interval()
        if not first_flip and interval:
            intervals.append(interval)
        first_flip = False
    return sum(intervals) / len(intervals) if intervals else 0.0


def measure_paced_loop(screen: Screen, duration_s: float) -> float:
    """Mean flip() interval using LoopPacer, matching the real interaction loops."""
    start = time.perf_counter()

    def wait_until(target: float) -> None:
        remaining = target - time.perf_counter()
        if remaining > 0:
            time.sleep(remaining)

    pacer = LoopPacer(screen, wait_until, start)
    intervals = []
    first_flip = True
    end = start + duration_s
    while True:
        now = time.perf_counter()
        if now >= end:
            break
        screen.poll_events()
        if pacer.render_due(now):
            screen.fill((128, 128, 128))
            screen.flip()
            interval = screen.get_flip_interval()
            if not first_flip and interval:
                intervals.append(interval)
            first_flip = False
            now = time.perf_counter()
            pacer.after_render(now)
        pacer.wait(now)
    return sum(intervals) / len(intervals) if intervals else 0.0


def run_probe(args: argparse.Namespace) -> None:
    screen = Screen(
        vsync=True,
        fullscreen=args.fullscreen,
        width=None if args.fullscreen else args.width,
        height=None if args.fullscreen else args.height,
        screen_number=args.screen,
    )
    try:
        print(f"Monitor mode reports: {1 / get_render_interval(screen):.2f} Hz")

        print(f"Tight loop, {args.frames} frames, no pacing...")
        mean_tight = measure_tight_loop(screen, args.frames)
        print(f"  -> {1 / mean_tight:.2f} Hz" if mean_tight else "  -> no frames measured")

        print(f"Paced loop (LoopPacer), {args.duration:.1f}s...")
        mean_paced = measure_paced_loop(screen, args.duration)
        print(f"  -> {1 / mean_paced:.2f} Hz" if mean_paced else "  -> no frames measured")
    finally:
        screen.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure TachyPy's achieved flip() rate under VSync.")
    parser.add_argument("--windowed", dest="fullscreen", action="store_false", help="run in a window instead of fullscreen")
    parser.add_argument("--width", type=int, default=800, help="window width when using --windowed")
    parser.add_argument("--height", type=int, default=600, help="window height when using --windowed")
    parser.add_argument("--screen", type=int, default=0, help="monitor index")
    parser.add_argument("--frames", type=int, default=300, help="frame count for the tight-loop measurement")
    parser.add_argument("--duration", type=float, default=3.0, help="duration in seconds for the paced measurement")
    parser.set_defaults(fullscreen=True)
    return parser.parse_args()


def main() -> None:
    run_probe(parse_args())


if __name__ == "__main__":
    main()
