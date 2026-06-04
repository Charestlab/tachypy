Getting Started
===============

Install TachyPy
---------------

.. code-block:: bash

   pip install tachypy

The base install includes GLFW for display/input, PyOpenGL, Pillow text
support, and pyserial for serial trigger workflows. Pygame is no longer a base
dependency.

For development:

.. code-block:: bash

   git clone https://github.com/Charestlab/tachypy.git
   cd tachypy
   pip install -e .

Optional extras
---------------

.. code-block:: bash

   pip install -e ".[test]"        # pytest, coverage, lint tooling
   pip install -e ".[pygame]"      # legacy pygame compatibility backend
   pip install -e ".[text]"        # Pillow text fallback
   pip install -e ".[system_text]" # FreeType + HarfBuzz text renderer
   pip install -e ".[audio_sd]"    # sounddevice backend

Minimal loop
------------

.. code-block:: python

   from tachypy import Screen, ResponseHandler

   screen = Screen(fullscreen=False, width=1280, height=720, backend="glfw")
   responses = ResponseHandler(screen=screen)

   running = True
   while running:
       screen.fill((128, 128, 128))
       screen.flip()
       responses.get_events()
       if responses.should_quit() or responses.was_key_pressed("esc"):
           running = False

   screen.close()
