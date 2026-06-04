Examples
========

Demo script
-----------

Run the bundled demo:

.. code-block:: bash

   python example_tachypy.py

Select backend explicitly:

.. code-block:: bash

   TACHYPY_BACKEND=glfw python example_tachypy.py
   TACHYPY_BACKEND=pygame python example_tachypy.py  # legacy compatibility

Notes
-----

- The demo defaults to GLFW and OpenGL/system-font text renderers.
- Legacy pygame mode requires installing ``tachypy[pygame]``.
- On constrained CI systems, set ``TACHYPY_AUDIO_BACKEND=dummy``.
