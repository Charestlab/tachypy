import tachypy.gltext as gltext_module
import tachypy._warnings as warnings_module
from tachypy.gltext import GLText


def patch_gl(monkeypatch):
    monkeypatch.setattr(gltext_module, "glEnable", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glBlendFunc", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glDisable", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glColor3f", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glBegin", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glVertex2f", lambda *args, **kwargs: None)
    monkeypatch.setattr(gltext_module, "glEnd", lambda *args, **kwargs: None)


def test_gltext_wraps_into_multiple_lines_when_rect_is_narrow(monkeypatch):
    patch_gl(monkeypatch)
    text = GLText("this is a long message", dest_rect=[0, 0, 80, 40], pixel_size=3)

    assert len(text.lines) > 1


def test_gltext_draw_runs_without_texture_backend(monkeypatch):
    patch_gl(monkeypatch)
    text = GLText("hello", dest_rect=[0, 0, 200, 80])
    text.draw()

    assert text.lines == ["hello"]


def test_gltext_variable_width_metrics(monkeypatch):
    patch_gl(monkeypatch)
    text = GLText("WWW ...", dest_rect=[0, 0, 400, 80])

    wide_w, _ = text._measure_line("WWW")
    narrow_w, _ = text._measure_line("...")

    assert wide_w > narrow_w


def test_gltext_warns_when_character_is_replaced_by_question_mark(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())

    GLText("café", dest_rect=[0, 0, 200, 80])

    message = capsys.readouterr().err
    assert "GLText glyph resolution" in message
    assert "'é'" in message
    assert "rendered as '?'" in message


def test_gltext_warns_when_entire_text_exceeds_rectangle(monkeypatch, capsys):
    monkeypatch.setattr(warnings_module, "_warned", set())

    GLText("one two three four", dest_rect=[0, 0, 20, 80], pixel_size=3)

    message = capsys.readouterr().err
    assert "GLText layout" in message
    assert "Text width" in message
    assert "Minimum dest_rect width to display this text without wrapping" in message
    assert "wrap automatically at whitespace" in message
    assert "insert '\\n'" in message
