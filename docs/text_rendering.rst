Text Rendering
==============

TachyPy offers multiple text paths depending on precision and dependency needs.

Text class
----------

``Text`` is the convenience layer for instruction screens and simple overlays.
It tries ``pygame.font`` first, then a Pillow fallback when configured.

OpenGL text renderers
---------------------

- ``GLText``: bitmap glyph renderer in pure OpenGL.
- ``GLTextSDF``: signed-distance-field renderer for smoother scaling.
- ``GLSystemText``: system-font rendering using FreeType + HarfBuzz.

The OpenGL renderers are backend-independent and do not require
``pygame.font``.

Recommended usage
-----------------

- Use ``Text`` for quick experiments and prototypes.
- Use ``GLSystemText`` for highest quality multilingual/system-font rendering.
- Use ``GLTextSDF`` when scalable text quality matters and shaping is simple.
