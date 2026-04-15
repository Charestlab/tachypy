Getting Started
===============

Install TachyPy
---------------

.. code-block:: bash

   pip install tachypy

For development:

.. code-block:: bash

   git clone https://github.com/Charestlab/tachypy.git
   cd tachypy
   pip install -e .

Optional extras
---------------

.. code-block:: bash

   pip install -e ".[test]"        # pytest, coverage, lint tooling
   pip install -e ".[glfw]"        # GLFW backend
   pip install -e ".[text]"        # Pillow text fallback
   pip install -e ".[system_text]" # FreeType + HarfBuzz text renderer
   pip install -e ".[audio_sd]"    # sounddevice backend

Minimal loop
------------

.. code-block:: python

   from tachypy import Screen, ResponseHandler

   screen = Screen(fullscreen=False, width=1280, height=720, backend="pygame")
   responses = ResponseHandler(screen=screen)

   running = True
   while running:
       screen.fill((128, 128, 128))
       screen.flip()
       responses.get_events()
       if responses.should_quit() or responses.was_key_pressed("esc"):
           running = False

   screen.close()
