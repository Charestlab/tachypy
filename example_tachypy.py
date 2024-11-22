import os
import time
import numpy as np
from tachypy import (
    Audio,
    Screen,
    Texture,
    Circle,
    Rectangle,
    FixationCross,
    Text,
    center_rect_on_point,
    ResponseHandler,
    fabriquer_gabor,
    noisy_bit_dithering
)

# which screen should we draw to?
screen_number = 1
screen = Screen(screen_number=screen_number, fullscreen=True, desired_refresh_rate=60)

# get some relevant screen properties
center_x = screen.width//2 
center_y = screen.height//2 

# let's initialise our FixationCross
fixation_cross = FixationCross(center=[center_x, center_y], half_width=50, half_height=50, thickness=2.0, color=(255, 0, 0))  # Red cross

# let's add a white circle
circle = Circle(center=(320, 240), radius=50, fill=True, color=(255, 255, 255))  # Green circle

# let's add a nice blue rectangle
# first we can define the rectangle it will strecth to:
a_rect = [center_x+500, 190, center_x+1000, 290]
rectangle = Rectangle(a_rect, fill=True, thickness=1.0, color=(20.0, 50.0, 255.0))

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
dest_rect = center_rect_on_point([0, 0, nx-1, nx-1], [center_x, center_y])

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

        # draw a rectangle
        rectangle.draw()


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

# Create a Text object
dest_rect = center_rect_on_point([0, 0, .85*screen.width, .2*screen.height], [center_x, center_y])
text = Text("Thanks for using tachypy. Here is a long sentence that should be rendered on multiple lines. Only if that is necessary, of course. Press spacebar to continue with this demonstration.",
            dest_rect=dest_rect,
            font_name='Arial', 
            font_size=36, 
            color=(25, 50, 255))

# Clear events before the text is drawn
response_handler.clear_events()


# Draw the text
running = True
while running:
    screen.fill((128, 128, 128))  # Gray background
    text.draw()  # Draw the text
    screen.flip()

    # Handle events
    response_handler.get_events()
    if response_handler.should_quit():
        running = False
        break

    # Example: Check if the spacebar was pressed
    elif response_handler.is_key_down('space'):
        print("Spacebar pressed!")
        running = False
        break


# Create a Text object
dest_rect = center_rect_on_point([0, 0, .85*screen.width, .2*screen.height], [center_x, center_y])
text = Text("Here is a shorter instruction. Press spacebar to quit.",
            dest_rect=dest_rect,
            font_name='Arial', 
            font_size=36, 
            color=(25, 50, 255))

# Clear events before the text is drawn
response_handler.clear_events()

# Draw the text
running = True
while running:
    screen.fill((128, 128, 128))  # Gray background
    text.draw()  # Draw the text
    screen.flip()

    # Handle events
    response_handler.get_events()
    if response_handler.should_quit():
        running = False
        break

    # Example: Check if the spacebar was pressed
    elif response_handler.is_key_down('space'):
        print("Spacebar pressed!")
        running = False
        break

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
