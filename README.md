# TachyPy

**TachyPy** is a Python package designed for creating high-performance visual stimuli using OpenGL and Pygame. It provides a set of tools for screen management, texture handling, drawing visual elements, handling user responses, and generating psychophysical stimuli. TachyPy is ideal for researchers and developers working on psychophysics experiments, visualizations, or any application requiring precise control over visual presentations and user inputs.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Dependencies](#dependencies)
- [Usage](#usage)
  - [Example](#example)
- [Modules](#modules)
  - [Screen](#screen)
  - [Texture](#texture)
  - [Visuals](#visuals)
  - [Responses](#responses)
  - [Psychophysics](#psychophysics)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)
- [Acknowledgments](#acknowledgments)

---

## Features

- **Screen Management**: Initialize and manage screens with OpenGL contexts, handle multiple monitors, and control refresh rates.
- **Texture Handling**: Load and manage textures efficiently using OpenGL.
- **Drawing Utilities**: Functions to draw rectangles, lines, fixation crosses, and stimuli on the screen.
- **User Input Handling**: Capture keyboard and mouse events, including reaction times, without directly interacting with Pygame.
- **Psychophysical Stimuli Generation**: Create stimuli such as Gabor patches with customizable parameters.


## Installation

You can install TachyPy directly from GitHub:

```bash
pip install git+https://github.com/Charestlab/tachypy.git
```

Alternatively, clone the repository and install in editable mode:

```bash
git clone https://github.com/yourusername/tachypy.git
cd tachypy
pip install -e .
```

## Dependencies

- **Python 3.6** or higher
- **NumPy** (>=1.18.0)
- **Pygame** (>=2.0.0)
- **PyOpenGL** (>=3.1.0)
- **screeninfo** (>=0.6.0)

You can install the dependencies using:

```bash
pip install -r requirements.txt
```

## Usage

Here’s a quick example demonstrating how to use TachyPy to display a moving Gabor patch with a fixation cross and handle user input.

## Example

```python
import os
import time
import numpy as np
from tachypy import (
    Audio,
    Screen,
    Texture,
    Circle,
    FixationCross,
    center_rect_on_point,
    ResponseHandler,
    fabriquer_gabor,
    noisy_bit_dithering
)

def main():
    # which screen should we draw to?
    screen_number = 1
    screen = Screen(screen_number=screen_number, fullscreen=True, desired_refresh_rate=60)

    # get some relevant screen properties
    center_x = screen.width//2 
    center_y = screen.height//2 

    # let's initialise our FixationCross
    fixation_cross = FixationCross(center=[center_x, center_y], half_width=50, half_height=50, thickness=2.0, color=(255, 0, 0))  # Red cross

    # let's add a white circle
    circle = Circle(center=(320, 240), radius=50, fill=True, color=(0, 255, 0))  # Green circle

    # let's start our audio player
    audio_player = Audio(sample_rate=44100, channels=1)

    # make a sinewave for the sound
    duration = 1.0  # seconds
    frequency = 440.0  # Hz (A4 note)
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    amplitude = 0.5
    waveform = amplitude * np.sin(2 * np.pi * frequency * t).astype(np.float32)


    # set the screen's background colour to gray
    screen.fill([128, 128, 128])

    # flip the screen to make the background color visible
    screen.flip()

    # check for the screen's actual refresh rate
    frame_rate_actual = 1/screen.test_flip_intervals(num_frames=100)
    print(frame_rate_actual)

    # Initialize ResponseHandler
    response_handler = ResponseHandler()

    # create a moving Gabor patch animation
    nx = 750
    frequency_per_im = 10
    speed_in_cycles_per_s = 3
    nb_frames_per_cycle = int(frame_rate_actual / speed_in_cycles_per_s)

    rms_target = 0.08
    film = []
    for ii in range(nb_frames_per_cycle):
        phase = 2 * np.pi * ii / nb_frames_per_cycle
        gabor = fabriquer_gabor(nx, frequence=frequency_per_im, phase=phase, angle=np.pi/4, ecart_type=0.2)

        gabor = rms_target / np.std(gabor) * (gabor - 0.5) + 0.5
        gabor_dithered = noisy_bit_dithering(gabor)
        
        gabor_rgb = np.stack((gabor_dithered,)*3, axis=-1) # could be done in the OpenGL functions, like the colors
        # gabor_rgb[:,:,2] = 255 - gabor_rgb[:,:,2]
        film.append(gabor_rgb)


    # Load stimuli (example: red, green, blue squares)
    textures = [Texture(stimulus) for stimulus in film]

    # define the position in which the Texture will be mapped.
    dest_rect = center_rect_on_point([0, 0, nx-100, nx-100], [center_x, center_y])

    # Main loop
    running = True

    # Track frame timestamps to measure interval consistency
    frame_intervals = []

    # flip an initial screen and set initial time
    start_time = screen.flip()

    while running:
        for current_trial, texture in enumerate(textures):

            screen.fill([128, 128, 128])

            # draw a circle
            circle.draw()

            # draw the texture
            texture.draw(dest_rect)

            # draw the fixation cross
            fixation_cross.draw()

            time_stamp = screen.flip()

            frame_intervals.append(screen.get_flip_interval()) 

            # Handle events
            response_handler.get_events()
            if response_handler.should_quit():
                running = False
                break

            # Example: Check if the a key was pressed
            if response_handler.is_key_down('a'):
                print("a key pressed!")
                audio_player.play(waveform)
                # Do something in response to the spacebar press
            
    #time.sleep(0.01)
        
    # Analyze frame intervals after the loop ends
    frame_intervals = np.array(frame_intervals)
    average_interval = np.mean(frame_intervals) * 1000  # Convert to milliseconds
    std_deviation = np.std(frame_intervals) * 1000      # Convert to milliseconds

    print(f"Average frame interval: {average_interval:.4f} ms")
    print(f"Standard deviation: {std_deviation:.4f} ms")

    # one last flip
    screen.flip()

    # close the audio player
    audio_player.close()

    # close the screen
    screen.close()

if __name__ == "__main__":
    main()
```

## Modules

## Screen

Class: Screen

Manages screen initialization, handling multiple monitors, setting up OpenGL contexts, and controlling refresh rates.

Features:

- Initialize fullscreen or windowed mode.
- Control vsync and desired refresh rates.
- Provide methods to flip the display and tick the clock.
- Test flip intervals to measure actual frame rates.

Example:

```python
from tachypy import Screen

screen = Screen(screen_number=0, fullscreen=True, desired_refresh_rate=60)
screen.fill((128, 128, 128))  # Fill the screen with gray color
screen.flip()
```


## Texture

**Class**: Texture

Handles loading and managing OpenGL textures from images or NumPy arrays.

Features:

- Load textures into OpenGL.
- Bind and unbind textures for rendering.
- Delete textures when no longer needed.

Example:

```python
from tachypy import Texture
import numpy as np

# Create an example image
image = np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8)
texture = Texture(image)
texture.bind()
# Render with the texture
texture.unbind()
```

## Visuals

Provides utility functions for drawing basic shapes and stimuli.

**Functions**:

- draw_rectangle(a_rect, fill=True, thickness=1.0, color=(255, 255, 255)): Draws a rectangle.
- draw_line(pts1, pts2, thickness=1.0, color=(255, 0, 0)): Draws a line between two points.
- draw_fixation_cross(center_pts, half_width, half_height, thickness=1.0, color=(255, 0, 0)): Draws a fixation cross.
- center_rect_on_point(a_rect, a_point): Centers a rectangle on a given point.
- draw_stimulus(texture, a_rect): Draws a texture on the screen within the specified rectangle.

## Responses

**Class**: ResponseHandler

Handles user input events, including keyboard and mouse interactions, without exposing Pygame directly.

Features:

- Capture key presses and releases with timestamps.
- Detect mouse clicks and positions.
- Check if specific keys are pressed or released.
- Determine if the application should quit.

## Contributing

Contributions are welcome! If you'd like to contribute to TachyPy, please follow these steps:

1. **Fork** the repository on GitHub.
2. **Clone** your forked repository.
3. **Create a new branch** for your feature or bugfix.
4. **Make your changes** and commit them with descriptive messages.
5. **Push** your changes to your fork.
6. **Submit a pull request** to the main repository.

Please ensure that your code follows the project’s coding standards and includes appropriate tests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments

- Pygame for the multimedia library.
- PyOpenGL for the OpenGL bindings.
- NumPy for numerical computations.
- screeninfo for monitor information.
