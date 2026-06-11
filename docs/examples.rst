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

Run the default demo:

.. code-block:: bash

   python example_tachypy.py

Notes
-----

- ``Screen`` defaults to GLFW, and ``Text`` defaults to the system-font renderer.
- On constrained CI systems, set ``TACHYPY_AUDIO_BACKEND=dummy``.
