Scrollbar widget
================

TachyPy's :class:`~tachypy.scrollbar.Scrollbar` is a customizable visual
widget for selecting a continuous value, ``0``–``100`` by default. It is
independent of the input device: the same widget can be controlled with the
mouse, an analog keyboard, or another custom interaction loop.

Normal mouse use
----------------

Create the scrollbar with the display dimensions, draw it every frame, and
pass the current mouse position to ``handle_mouse``. The value is selected when
a mouse button is released:

.. code-block:: python

   from tachypy import ResponseHandler, Screen, Scrollbar

   screen = Screen(fullscreen=False)
   responses = ResponseHandler(screen=screen)
   scrollbar = Scrollbar(
       screen_width=screen.width,
       screen_height=screen.height,
       position_y=screen.height / 2,
       half_bar_length=350,
       num_marks=11,
       text_left="0",
       text_right="100",
       content_scale=screen.content_scale,
   )

   value = None
   while value is None:
       responses.get_events()
       if responses.should_quit():
           break

       scrollbar.handle_mouse(*responses.get_mouse_position())
       screen.fill((128, 128, 128))
       scrollbar.draw()
       screen.flip()

       for click in responses.get_mouse_clicks():
           if click["type"] == "mouseup":
               value = scrollbar.get_value()

   screen.close()

The widget's value can also be controlled directly:

.. code-block:: python

   scrollbar.set_value(50)       # choose an initial/current value
   current = scrollbar.get_value()

Customization
-------------

The constructor keeps the appearance and geometry of the scrollbar explicit.
Common options include:

* ``half_bar_length``, ``bar_thickness`` and ``bar_color`` for the main bar;
* ``num_marks``, ``mark_thickness`` and ``mark_color`` for tick marks;
* ``text_left``, ``text_right``, ``font_name``, ``font_size`` and
  ``text_color`` for endpoint labels;
* ``notch_label_every`` to label interior tick marks with their value
  (0-100 scale), and ``notch_label_font_scale`` to size them relative to
  ``font_size``;
* ``show_value_label`` to show the current integer value live under the
  moving marker;
* ``half_end_height``, ``end_thickness`` and ``end_color`` for the endpoints;
* ``limit_mouse`` to require the cursor to stay near the bar's horizontal line;
* ``content_scale=screen.content_scale`` for sharp labels on Retina/HiDPI
  displays.

For the complete constructor reference, see the
:class:`~tachypy.scrollbar.Scrollbar` API documentation.

Analog keyboard interaction
----------------------------

Analog keyboard controls are documented with the Wooting integration because
they include key roles, pressure-to-speed mapping, confirmation safety, Wooting
key validation, and keyboard/mouse modes. The interaction layer keeps this
widget unchanged and simply drives its existing ``set_value``/``draw`` API:

.. seealso::

   :doc:`wooting`

The generic, keyboard-agnostic API is documented in
:mod:`tachypy.scrollbar_interaction`.
