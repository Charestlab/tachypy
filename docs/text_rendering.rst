Text Rendering
==============

TachyPy has one text class: ``Text``.

Text class
----------

``Text`` renders system TrueType/OpenType fonts with FreeType + HarfBuzz as
OpenGL quads. ``font_name`` accepts a family name, a comma-separated fallback
list (e.g. ``"Avenir Next, Helvetica, Arial"``), or a direct font-file path.

FreeType and HarfBuzz are required dependencies. If ``font_name`` doesn't
resolve, TachyPy tries built-in defaults (Helvetica, Arial, DejaVu Sans,
Liberation Sans, Noto Sans, Times New Roman) and warns; construction raises
only if none resolve.

HiDPI and Retina displays
--------------------------

On Retina displays the framebuffer has more physical pixels than logical pixels.
Pass ``screen.content_scale`` so FreeType rasterizes at the correct physical
resolution — otherwise text appears blurry.

.. code-block:: python

    label = Text("Hello", content_scale=screen.content_scale)

.. image:: _static/content_scale.png
   :alt: content_scale=1 (blurry) vs content_scale=2 (sharp)
   :align: center

Why the default is ``2.0``
~~~~~~~~~~~~~~~~~~~~~~~~~~

``Text`` and ``Scrollbar`` default ``content_scale`` to
``2.0`` (matching every Retina/HiDPI display) instead of ``1.0``, as a
safety net: neither class is linked to a ``Screen``, so a caller who
forgets this parameter can't be warned. At ``1.0`` that mistake renders
silently blurry on the most common display class in a research lab (every
Mac laptop); at ``2.0`` it just renders correctly. Always prefer passing
the real ``screen.content_scale`` — the default is a fallback, not a
recommendation to skip it.

Performance: build once, update with ``set_text()``
-----------------------------------------------------

Constructing a ``Text`` loads the font file and builds a
fresh FreeType face + HarfBuzz font every time — roughly **2-3 ms before a
single glyph is rasterized**, regardless of ``content_scale``. That alone
can exceed a whole frame budget at high refresh rates (240 Hz = 4.17 ms),
so recreating a ``Text`` inside a per-frame or per-trial loop is a common
way to silently blow it.

Build the object **once** and update content with
:meth:`~tachypy.text.Text.set_text` instead — it reuses the
glyph cache, so only newly-seen glyphs are rasterized:

.. code-block:: python

    # Bad: reloads the font face from disk every trial.
    for trial in trials:
        label = Text(f"Score: {score}", dest_rect=..., content_scale=screen.content_scale)
        label.draw()

    # Good: build once, mutate in place.
    label = Text("Score: 0", dest_rect=..., content_scale=screen.content_scale)
    for trial in trials:
        label.set_text(f"Score: {score}")
        label.draw()

Rasterizing a higher ``content_scale`` does cost more per *new* glyph
(roughly ``content_scale**2``, since texture area grows with the square of
the resolution), but that's paid once per glyph and dwarfed by the
font-loading cost above. It's also cheap in absolute terms — measured RGBA
texture memory for a 41-glyph set (a full sentence with accents):

========= ====== ====== ======
font size 1.0    2.0    2.8
========= ====== ====== ======
24 pt     30 KB  118 KB 223 KB
28 pt     40 KB  155 KB 301 KB
40 pt     80 KB  318 KB 607 KB
========= ====== ====== ======

Even the worst case (607 KB) is smaller than a single stimulus image
(~750 KB for 500x500 RGB) — not worth optimizing. Recreating the ``Text``
object itself is the real cost to avoid. See ``slider_lab.py``'s
``target_text`` in the :doc:`wooting` demos for a working example.
