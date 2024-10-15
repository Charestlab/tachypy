import os
import numpy as np
from tachypy import (
    Screen,
    Texture,
    draw_rectangle,
    draw_fixation_cross,
    center_rect_on_point,
    ResponseHandler,
    fabriquer_gabor,
    noisy_bit_dithering
)

# which screen should we draw to?
screen_number = 1
screen = Screen(screen_number=screen_number, fullscreen=True, desired_refresh_rate=60)

# set the screen's background colour to gray
screen.fill([128, 128, 128])

# flip the screen to make the background color visible
screen.flip()

# check for the screen's actual refresh rate
frame_rate_actual = screen.test_flip_intervals(num_frames=100)*1000
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

center_x = screen.width//2 
center_y = screen.height//2 
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

        # draw a rectangle
        draw_rectangle([100, 100, 1000, 800], fill=False, thickness=1.0, color=(0.0, 255.0, 0.0))

        # draw the texture
        texture.draw(dest_rect)

        # draw the fixation cross
        draw_fixation_cross([center_x, center_y], 50, 50, thickness=2.0, color=(255.0, 0.0, 0.0))

        time_stamp = screen.flip()

        frame_intervals.append(screen.get_flip_interval()) 

        # Handle events
        response_handler.get_events()
        if response_handler.should_quit():
            running = False
            break

        # Example: Check if the spacebar was pressed
        if response_handler.is_key_down('a'):
            print("a key pressed!")
            # Do something in response to the spacebar press
       
# Analyze frame intervals after the loop ends
frame_intervals = np.array(frame_intervals)
average_interval = np.mean(frame_intervals) * 1000  # Convert to milliseconds
std_deviation = np.std(frame_intervals) * 1000      # Convert to milliseconds

print(f"Average frame interval: {average_interval:.4f} ms")
print(f"Standard deviation: {std_deviation:.4f} ms")

# one last flip
screen.flip()

# close the screen
screen.close()
