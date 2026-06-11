import tachypy.text as text_module
from tachypy.text import LegacyText


class FakeImage:
    FLIP_TOP_BOTTOM = "flip"

    def __init__(self, size=(1, 1)):
        self.size = size

    @classmethod
    def new(cls, mode, size, color):
        return cls(size)

    def transpose(self, mode):
        return self

    def tobytes(self, *args):
        return b"fake"


class FakeDrawer:
    def __init__(self, image):
        pass

    def textbbox(self, pos, value, font=None):
        return (0, 0, max(1, len(value)) * 8, 16)

    def text(self, pos, value, fill=None, font=None):
        pass


class FakeImageDraw:
    Draw = FakeDrawer


class FakeFont:
    pass


class FakeImageFont:
    @staticmethod
    def truetype(name, size):
        return FakeFont()

    @staticmethod
    def load_default():
        return FakeFont()


def patch_gl_and_pillow(monkeypatch):
    monkeypatch.setattr(text_module, "glDeleteTextures", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glBindTexture", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glTexImage2D", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glTexParameterf", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glGenTextures", lambda *args, **kwargs: 1)
    monkeypatch.setattr(text_module.LegacyText, "_init_text_backend", fake_init_text_backend)


def fake_init_text_backend(self):
    self._pil_image = FakeImage
    self._pil_draw = FakeImageDraw
    self._pil_imagefont = FakeImageFont
    self._font_obj = FakeFont()


def test_legacy_text_can_initialize_without_dest_rect(monkeypatch):
    patch_gl_and_pillow(monkeypatch)

    text = LegacyText(text="Hello TachyPy", dest_rect=None, backend="pillow")

    assert text.lines == ["Hello TachyPy"]


def test_legacy_text_handles_empty_content(monkeypatch):
    patch_gl_and_pillow(monkeypatch)

    text = LegacyText(text="", dest_rect=[0, 0, 120, 80], backend="pillow")
    text.set_text("")

    assert len(text.lines) >= 1


def test_legacy_text_rejects_pygame_backend():
    try:
        LegacyText(text="x", backend="pygame")
    except ValueError as exc:
        assert "pillow" in str(exc)
    else:
        raise AssertionError("pygame backend should be rejected")
