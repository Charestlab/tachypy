import tachypy.gltext as gltext_module
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
