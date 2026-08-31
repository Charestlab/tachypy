Getting Started
===============

Install TachyPy
---------------

.. code-block:: bash

   pip install tachypy

The base install includes GLFW, PyOpenGL, FreeType, HarfBuzz, pyserial, and
TachyAudio. Pygame is no longer supported. TachyAudio is currently beta;
TachyPy requires ``tachyaudio>=0.2.0b2``. If pip refuses pre-releases, pass
``--pre`` explicitly.

For development:

.. code-block:: bash

   git clone https://github.com/Charestlab/tachypy.git
   cd tachypy
   pip install -e .

Optional extras
---------------

.. code-block:: bash

   pip install -e ".[test]"        # pytest, coverage, lint tooling
   pip install -e ".[wooting]"     # Wooting analog-keyboard integration

See :doc:`wooting` for the Wooting analog-keyboard integration.

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
