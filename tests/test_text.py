from types import SimpleNamespace

import tachypy.text as text_module
from tachypy.text import LegacyText


class FakeSurface:
    def __init__(self, size):
        self._size = size

    def get_width(self):
        return self._size[0]

    def get_height(self):
        return self._size[1]

    def get_size(self):
        return self._size

    def fill(self, color):
        return None

    def blit(self, surface, position):
        return None


class FakeFont:
    def size(self, value):
        # Deterministic width heuristic for wrapping tests.
        return (max(1, len(value)) * 8, 16)

    def render(self, value, antialias, color):
        width = max(1, len(value)) * 8
        return FakeSurface((width, 16))


class FakeFontModule:
    def init(self):
        return None

    def SysFont(self, name, size):
        return FakeFont()


def patch_gl_and_pygame(monkeypatch):
    monkeypatch.setattr(text_module, "glDeleteTextures", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glBindTexture", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glTexImage2D", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glTexParameterf", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glTexParameteri", lambda *args, **kwargs: None)
    monkeypatch.setattr(text_module, "glGenTextures", lambda *args, **kwargs: 1)

    fake_pygame = SimpleNamespace(
        font=FakeFontModule(),
        SRCALPHA=1,
        Surface=lambda size, flags=None: FakeSurface(size),
        image=SimpleNamespace(tostring=lambda *args, **kwargs: b"fake"),
    )
    monkeypatch.setattr(text_module, "pygame", fake_pygame)


def test_legacy_text_can_initialize_without_dest_rect(monkeypatch):
    patch_gl_and_pygame(monkeypatch)

    text = LegacyText(text="Hello TachyPy", dest_rect=None, backend="pygame")

    assert text.lines == ["Hello TachyPy"]


def test_legacy_text_handles_empty_content(monkeypatch):
    patch_gl_and_pygame(monkeypatch)

    text = LegacyText(text="", dest_rect=[0, 0, 120, 80], backend="pygame")
    text.set_text("")

    assert len(text.lines) >= 1


def test_textbox_clear_refreshes_texture(monkeypatch):
    patch_gl_and_pygame(monkeypatch)

    box = text_module.TextBox(position=(0, 0), size=(200, 40), font=FakeFont())
    box.text = "abc"
    box.cursor_position = 2
    box.submitted = True
    box.clear()

    assert box.text == ""
    assert box.cursor_position == 0
    assert box.submitted is False
