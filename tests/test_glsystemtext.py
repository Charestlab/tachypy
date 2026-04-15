import tachypy.glsystemtext as glsys_module
from tachypy.glsystemtext import GLSystemText


class FakeFallback:
    def __init__(self, *args, **kwargs):
        self.text = kwargs.get("text") if "text" in kwargs else (args[0] if args else "")
        self.dest_rect = kwargs.get("dest_rect")
        self.draw_called = False

    def set_text(self, new_text):
        self.text = new_text

    def set_dest_rect(self, dest_rect):
        self.dest_rect = dest_rect

    def draw(self):
        self.draw_called = True

    def delete(self):
        return None


def test_glsystemtext_falls_back_when_deps_unavailable(monkeypatch):
    monkeypatch.setattr(glsys_module, "HAS_FREETYPE", False)
    monkeypatch.setattr(glsys_module, "HAS_HARFBUZZ", False)
    monkeypatch.setattr(glsys_module, "GLText", FakeFallback)

    text = GLSystemText("hello", dest_rect=[0, 0, 100, 50])

    assert text._fallback is not None
    text.draw()
    assert text._fallback.draw_called is True


def test_glsystemtext_fallback_mutators(monkeypatch):
    monkeypatch.setattr(glsys_module, "HAS_FREETYPE", False)
    monkeypatch.setattr(glsys_module, "HAS_HARFBUZZ", False)
    monkeypatch.setattr(glsys_module, "GLText", FakeFallback)

    text = GLSystemText("start", dest_rect=[0, 0, 100, 50])
    text.set_text("next")
    text.set_dest_rect([10, 10, 120, 70])

    assert text._fallback.text == "next"
    assert text._fallback.dest_rect == [10, 10, 120, 70]
