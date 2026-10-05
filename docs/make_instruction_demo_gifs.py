"""Render the instruction-demo gifs used by docs/wooting.rst (needs a display).

Run from the repository root::

    python docs/make_instruction_demo_gifs.py

Each demo is played on a simulated clock, one frame per 1/fps second, so the
result is identical on every machine; the frames are read back from the
framebuffer, cropped to the demo, and written as a seamlessly looping gif.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from OpenGL.GL import GL_RGB, GL_UNSIGNED_BYTE, GL_VIEWPORT, glGetIntegerv, glReadPixels
from PIL import Image, ImageChops

from tachypy import Screen
from tachypy.instruction_demos import GifUwuFixationCross, GifUwuScrollbar, keypad

OUT_DIR = Path(__file__).parent / "gifs"
BACKGROUND = (128, 128, 128)
OUTPUT_WIDTH = 560  # px
PALETTE_COLORS = 64

DEMOS = {
    "wooting-uwu-fixation-cross.gif": (GifUwuFixationCross, 15),
    "wooting-uwu-scrollbar.gif": (GifUwuScrollbar, 20),
}


def read_frame() -> Image.Image:
    viewport = glGetIntegerv(GL_VIEWPORT)
    pixels = glReadPixels(0, 0, viewport[2], viewport[3], GL_RGB, GL_UNSIGNED_BYTE)
    return Image.frombytes("RGB", (viewport[2], viewport[3]), pixels).transpose(Image.FLIP_TOP_BOTTOM)


def render_frames(screen: Screen, demo_cls, fps: int) -> list[Image.Image]:
    clock = SimpleNamespace(now=0.0, perf_counter=lambda: clock.now)
    keypad.time = clock  # the demos read time.perf_counter(); drive it by hand
    demo = demo_cls(screen, background_color=BACKGROUND, loop=True)
    demo.start()
    frames = []
    for index in range(round(demo.duration * fps)):
        clock.now = index / fps
        screen.fill(BACKGROUND)
        demo.draw(screen)
        frames.append(read_frame())
        screen.flip()
    return frames


def crop_to_content(frames: list[Image.Image], pad: int = 40) -> list[Image.Image]:
    background = Image.new("RGB", frames[0].size, BACKGROUND)
    boxes = [box for f in frames if (box := ImageChops.difference(f, background).getbbox())]
    left = max(0, min(b[0] for b in boxes) - pad)
    top = max(0, min(b[1] for b in boxes) - pad)
    right = min(frames[0].width, max(b[2] for b in boxes) + pad)
    bottom = min(frames[0].height, max(b[3] for b in boxes) + pad)
    return [f.crop((left, top, right, bottom)) for f in frames]


def save_gif(frames: list[Image.Image], path: Path, fps: int) -> None:
    height = round(frames[0].height * OUTPUT_WIDTH / frames[0].width)
    frames = [f.resize((OUTPUT_WIDTH, height), Image.LANCZOS) for f in frames]
    # One shared palette (built from sampled frames) avoids color flicker between frames.
    sample = frames[:: max(1, len(frames) // 12)]
    sheet = Image.new("RGB", (OUTPUT_WIDTH, height * len(sample)))
    for i, f in enumerate(sample):
        sheet.paste(f, (0, i * height))
    palette = sheet.quantize(colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    paletted = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    paletted[0].save(path, save_all=True, append_images=paletted[1:], duration=round(1000 / fps),
                     loop=0, optimize=True, disposal=2)


def main() -> None:
    screen = Screen(fullscreen=False, width=960, height=600, vsync=False, grab_input=False)
    try:
        for name, (demo_cls, fps) in DEMOS.items():
            frames = crop_to_content(render_frames(screen, demo_cls, fps))
            save_gif(frames, OUT_DIR / name, fps)
            print(f"{name}: {len(frames)} frames, {(OUT_DIR / name).stat().st_size / 1024:.0f} KiB")
    finally:
        screen.close()


if __name__ == "__main__":
    main()
