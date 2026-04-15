"""Texture helpers for uploading and drawing image stimuli with OpenGL."""

from typing import Optional, Sequence, Tuple, Union

import numpy as np
from OpenGL.GL import (
    GL_CLAMP_TO_EDGE,
    GL_LINEAR,
    GL_MODULATE,
    GL_QUADS,
    GL_RGB,
    GL_TEXTURE_2D,
    GL_TEXTURE_ENV,
    GL_TEXTURE_ENV_MODE,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNPACK_ALIGNMENT,
    GL_UNSIGNED_BYTE,
    glBegin,
    glBindTexture,
    glColor3f,
    glDeleteTextures,
    glDisable,
    glEnable,
    glEnd,
    glGenTextures,
    glLoadIdentity,
    glPixelStorei,
    glTexCoord2f,
    glTexEnvf,
    glTexImage2D,
    glTexParameterf,
    glTexSubImage2D,
    glVertex2f,
)


RectLike = Union[Sequence[float], Sequence[Sequence[float]]]


class Texture:
    """OpenGL texture wrapper with rectangle-based drawing utilities."""

    def __init__(self, image: np.ndarray, a_rect: Optional[RectLike] = None, rect: Optional[RectLike] = None):
        """
        Parameters
        ----------
        image : np.ndarray
            RGB image with shape (H, W, 3) and dtype convertible to uint8.
        a_rect, rect : sequence, optional
            Rectangle as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].
            `rect` is the preferred name; `a_rect` is kept for compatibility.
        """
        if rect is not None and a_rect is not None:
            raise ValueError("Pass either `rect` or `a_rect`, not both.")

        image = self._validate_image(image)
        self.texture_id = glGenTextures(1)
        self.image_shape: Tuple[int, int, int] = image.shape
        self.load_texture(image)

        rect_value = rect if rect is not None else a_rect
        if rect_value is None:
            h, w = image.shape[0], image.shape[1]
            self.rect = np.array([0.0, 0.0, float(w), float(h)], dtype=np.float32)
        else:
            self.set_rect(rect_value)

    @staticmethod
    def _validate_image(image: np.ndarray) -> np.ndarray:
        """Validate and normalize image array to uint8 RGB format."""
        image = np.asarray(image)
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must have shape (H, W, 3)")
        if image.dtype != np.uint8:
            image = image.astype(np.uint8)
        return image

    @staticmethod
    def _normalize_rect(a_rect: RectLike) -> np.ndarray:
        """Normalize rectangle input into float32 [x1, y1, x2, y2]."""
        a_rect = np.asarray(a_rect, dtype=np.float32)
        if a_rect.shape == (4,):
            x1, y1, x2, y2 = a_rect
        elif a_rect.shape == (2, 2):
            (x1, y1), (x2, y2) = a_rect
        else:
            raise ValueError("A rectangle is defined as [x1, y1, x2, y2] or [[x1, y1], [x2, y2]].")

        if x2 <= x1 or y2 <= y1:
            raise ValueError("x2 must be > x1 and y2 must be > y1.")

        return np.array([x1, y1, x2, y2], dtype=np.float32)

    def load_texture(self, image: np.ndarray) -> None:
        """Upload texture pixels to the GPU."""
        image = self._validate_image(image)
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            image.shape[1],
            image.shape[0],
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            image,
        )

        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glBindTexture(GL_TEXTURE_2D, 0)

    def bind(self) -> None:
        """Bind this texture and enable texturing."""
        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glEnable(GL_TEXTURE_2D)

    def unbind(self) -> None:
        """Unbind texture and reset texturing state."""
        glDisable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)
        glLoadIdentity()

    def update(self, image: np.ndarray) -> None:
        """Update texture pixels in-place; shape must match the original texture."""
        image = self._validate_image(image)
        if image.shape != self.image_shape:
            raise ValueError(f"image shape {image.shape} does not match existing texture shape {self.image_shape}")

        glBindTexture(GL_TEXTURE_2D, self.texture_id)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        w, h = image.shape[1], image.shape[0]
        glTexSubImage2D(
            GL_TEXTURE_2D,
            0,
            0,
            0,
            w,
            h,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            image,
        )
        glBindTexture(GL_TEXTURE_2D, 0)

    def delete(self) -> None:
        """Delete this texture object from GPU memory."""
        if getattr(self, "texture_id", 0):
            glDeleteTextures([self.texture_id])
            self.texture_id = 0

    def set_rect(self, a_rect: RectLike) -> None:
        """Set drawing rectangle for subsequent draw calls."""
        self.rect = self._normalize_rect(a_rect)

    def move_by(self, dx: float, dy: float) -> None:
        """Translate drawing rectangle by (dx, dy)."""
        self.rect[0] += dx
        self.rect[1] += dy
        self.rect[2] += dx
        self.rect[3] += dy

    def hit_test(self, x: float, y: float) -> bool:
        """Return True if point lies inside current rectangle."""
        x1, y1, x2, y2 = self.rect
        return bool((x1 <= x <= x2) and (y1 <= y <= y2))

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Return current rectangle bounds as floats."""
        x1, y1, x2, y2 = self.rect
        return float(x1), float(y1), float(x2), float(y2)

    def draw(self, a_rect: Optional[RectLike] = None, rect: Optional[RectLike] = None) -> None:
        """Draw the texture to `rect`/`a_rect` or to the current stored rectangle."""
        if rect is not None and a_rect is not None:
            raise ValueError("Pass either `rect` or `a_rect`, not both.")

        rect_value = rect if rect is not None else a_rect
        if rect_value is not None:
            self.set_rect(rect_value)

        x1, y1, x2, y2 = self.rect

        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glColor3f(1.0, 1.0, 1.0)

        self.bind()
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0)
        glVertex2f(x1, y1)
        glTexCoord2f(1, 0)
        glVertex2f(x2, y1)
        glTexCoord2f(1, 1)
        glVertex2f(x2, y2)
        glTexCoord2f(0, 1)
        glVertex2f(x1, y2)
        glEnd()
        self.unbind()
