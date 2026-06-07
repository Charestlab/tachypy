Examples
========

Demo script
-----------

Run the bundled demo:

.. code-block:: bash

   python example_tachypy.py

Run the fullscreen GLFW clock and stop-timer demo:

.. code-block:: bash

   tachypy-clock-demo

From a source checkout:

.. code-block:: bash

   python clock_timer_demo.py

Use ``Esc`` to quit, click ``START``/``STOP``/``RESET``, or use ``Space`` and
``R``. For windowed development, run:

.. code-block:: bash

   tachypy-clock-demo --windowed

Select backend explicitly:

.. code-block:: bash

   TACHYPY_BACKEND=glfw python example_tachypy.py
   TACHYPY_BACKEND=pygame python example_tachypy.py  # legacy compatibility

Notes
-----

- The demo defaults to GLFW and OpenGL/system-font text renderers.
- Legacy pygame mode requires installing ``tachypy[pygame]``.
- On constrained CI systems, set ``TACHYPY_AUDIO_BACKEND=dummy``.
