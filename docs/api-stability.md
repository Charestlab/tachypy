# API stability from 1.0

TachyPy 1.x follows semantic versioning for its documented runtime classes,
functions, call signatures, return values, and behavior. Compatible additions
belong in minor releases; fixes preserve public behavior. Incompatible changes
require a major version, with documented deprecations before removal.

Private names beginning with an underscore and demonstration programs are
outside this compatibility promise. Device/driver behavior and hardware timing
limits depend on the experiment machine and remain subject to validation.

## Audio compatibility

TachyPy supports TachyAudio 1.x and retains compatibility with the released
0.2.0b4 API (`tachyaudio>=0.2.0b4,<2`). This lets each project prepare and release
independently; a future incompatible TachyAudio major version is not selected
automatically. Native audio timing remains the default on macOS, Linux, and
Windows, with the documented device/rate restrictions and explicit software
fallback option.

Removing the old general beta label does not turn software/device-clock
timestamps into calibrated physical onset measurements. Hardware validation
remains necessary when an experiment depends on physical onset accuracy.

## Release validation

All runtime Python modules, including QUEST, screen, text, textures, and shapes,
are included in combined statement/branch coverage. CI enforces a 90% minimum
on Linux, macOS, and Windows. Example/demo entry points remain outside the
coverage total. See [Testing](testing.rst) for the command and scope.

Graphics tests verify layout, geometry, pixel uploads, lifecycle, and commands at
the GLFW/OpenGL boundary. They supplement on-machine visual/input/audio tests;
they do not measure actual GPU output, VSync, or photons reaching a photodiode.
