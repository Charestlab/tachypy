Getting Started
===============

Install TachyPy
---------------

.. code-block:: bash

   pip install --pre tachypy

The base install includes GLFW for display/input, PyOpenGL, Pillow text
support, pyserial for serial trigger workflows, and TachyAudio for audio
playback. Pygame support has been removed; GLFW is the supported display/input
backend. TachyAudio is currently published as a beta release, so use
``--pre`` when installing TachyPy from PyPI.

For development:

.. code-block:: bash

   git clone https://github.com/Charestlab/tachypy.git
   cd tachypy
   pip install -e .

Optional extras
---------------

.. code-block:: bash

   pip install -e ".[test]"        # pytest, coverage, lint tooling
   pip install -e ".[text]"        # Pillow text fallback
   # Audio support (tachyaudio) is included in the base install

Minimal loop
------------

.. code-block:: python

   from tachypy import Screen, ResponseHandler

   screen = Screen(fullscreen=False, width=1280, height=720)
   responses = ResponseHandler(screen=screen)

   running = True
   while running:
       screen.fill((128, 128, 128))
       screen.flip()
       responses.get_events()
       if responses.should_quit() or responses.was_key_pressed("esc"):
           running = False

   screen.close()
