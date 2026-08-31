"""Shared TachyPy diagnostic warning helper.

Deduplicates identical warnings (same context + message) so constructing many
objects with the same misconfiguration doesn't flood stderr with repeats.
"""
import os
import sys
import traceback
from pathlib import Path

_warned: set = set()
_PACKAGE_DIR = Path(__file__).resolve().parent

# On by default; off if TACHYPY_DISABLE_WARNINGS is truthy, or via set_warnings_enabled().
_enabled = os.environ.get("TACHYPY_DISABLE_WARNINGS", "").strip().lower() not in (
    "1", "true", "yes", "on",
)


def set_warnings_enabled(enabled: bool) -> None:
    """Turn TachyPy's ``[TachyPy WARNING]`` diagnostics on or off."""
    global _enabled
    _enabled = bool(enabled)


def warnings_enabled() -> bool:
    """Return whether TachyPy's diagnostic warnings are currently enabled."""
    return _enabled


def caller_location() -> str:
    """Return 'file.py:line' for the nearest stack frame outside tachypy itself."""
    for frame in reversed(traceback.extract_stack()[:-1]):  # skip this frame itself
        frame_path = Path(frame.filename).resolve()
        if _PACKAGE_DIR not in frame_path.parents:
            return f"{frame_path.name}:{frame.lineno}"
    return "unknown location"


def warn_once(context: str, message: str) -> None:
    """Print a TachyPy-branded warning to stderr, once per unique (context, message).

    Tagged with the caller's file:line (not part of the dedup key, so repeats collapse to one warning).
    """
    if not _enabled:
        return
    key = (context, message)
    if key in _warned:
        return
    _warned.add(key)
    label = f"\n\t[TachyPy WARNING]: {context} (from {caller_location()})"
    if sys.stderr.isatty():
        label = f"\033[1;31m{label}\033[0m"
    print(f"{label}\n\t\t{message}", file=sys.stderr, end="\n\n")
