Examples
========

Demo script
-----------

Run the bundled demo:

.. code-block:: bash

   python example_tachypy.py

Select backend explicitly:

.. code-block:: bash

   TACHYPY_BACKEND=pygame python example_tachypy.py
   TACHYPY_BACKEND=glfw python example_tachypy.py

Notes
-----

- If your Python build lacks ``pygame.font``, use OpenGL text renderers
  (``GLText``, ``GLTextSDF``, or ``GLSystemText``).
- On constrained CI systems, set ``TACHYPY_AUDIO_BACKEND=dummy``.
