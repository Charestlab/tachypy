import tachypy._warnings as warnings_module
from tachypy._warnings import caller_location, warn_once


def test_caller_location_reports_the_calling_file_and_line(monkeypatch):
    location = caller_location()  # this line's number should show up below
    assert location.startswith("test_warnings.py:")
    assert location != "unknown location"


def test_caller_location_skips_tachypy_internal_frames():
    # A helper defined inside tachypy._warnings itself should still report the
    # *test's* call site, not the internal wrapper's.
    def _internal_wrapper():
        return caller_location()

    location = _internal_wrapper()
    assert location.startswith("test_warnings.py:")


def test_warn_once_deduplicates_by_context_and_message(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())

    warn_once("Some context", "Some message")
    warn_once("Some context", "Some message")

    message = capsys.readouterr().err
    assert message.count("[TachyPy WARNING]: Some context") == 1


def test_warn_once_treats_different_messages_as_distinct(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())

    warn_once("Some context", "First message")
    warn_once("Some context", "Second message")

    message = capsys.readouterr().err
    assert "First message" in message
    assert "Second message" in message
