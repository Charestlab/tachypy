"""Shared TachyPy diagnostic warning helper.

Deduplicates identical warnings (same context + message) so constructing many
``Text``/``GLSystemText`` objects with the same misconfiguration -- a common
pattern, since an experiment scene typically builds one label per UI element
-- doesn't flood stderr with repeats of the same root cause.
"""
import sys

_warned: set = set()


def warn_once(context: str, message: str) -> None:
    """Print a TachyPy-branded warning to stderr, once per unique (context, message)."""
    key = (context, message)
    if key in _warned:
        return
    _warned.add(key)
    label = f"\n\t[TachyPy WARNING]: {context}"
    if sys.stderr.isatty():
        label = f"\033[1;31m{label}\033[0m"
    print(f"{label}\n\t\t{message}", file=sys.stderr, end="\n\n")
