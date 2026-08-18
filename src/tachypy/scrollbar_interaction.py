"""Keyboard and mouse interaction for TachyPy scrollbar-like widgets.

The interaction loop is deliberately separate from :class:`tachypy.scrollbar.Scrollbar`:
``Scrollbar`` owns drawing and value/geometry handling, while this module owns
input, timing, pressure mapping, confirmation, and quit handling. This keeps
all of TachyPy's scrollbar customization available regardless of how the value
is selected.

There are two intended entry points:

``AnalogSliderMixin.interact_slider``
    Convenience method for an acquisition object that provides
    ``read_pressures(keys)`` and, optionally, ``validate_analog_keys(keys)``.
    ``WOOTING_ACQUISITION`` gains this method through the TachyPy Wooting
    integration.

``run_slider_interaction``
    Keyboard-agnostic loop for other analog keyboards or custom input sources.
    Supply a ``control_reader`` returning :class:`SliderControls` each frame.

The default keyboard mapping is ``Z`` to decrease, ``C`` to increase, and
``X`` to confirm. The movement keys are analog: pressure is converted to a
nonlinear speed, so light presses provide fine control. Confirmation is only
accepted when neither movement key is active.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal

from tachypy.responses import ResponseHandler


@dataclass(frozen=True)
class SliderControls:
    """One frame of normalized controls for a scrollbar interaction.

    Each value should normally be in the inclusive range ``0.0``–``1.0``.
    ``decrease`` and ``increase`` control movement; ``confirm`` selects the
    current scrollbar value when it crosses the confirmation threshold.

    Attributes
    ----------
    decrease : float
        Analog pressure for the key that moves the scrollbar toward its lower
        values (``Z`` by default).
    increase : float
        Analog pressure for the key that moves the scrollbar toward its higher
        values (``C`` by default).
    confirm : float
        Analog pressure for the selection key (``X`` by default).
    """

    decrease: float = 0.0
    increase: float = 0.0
    confirm: float = 0.0


class AnalogSliderMixin:
    """Add pressure-driven scrollbar interaction to an analog acquisition.

    The host object must implement ``read_pressures(keys)`` and return a mapping
    from each requested key to a normalized pressure. If it implements
    ``validate_analog_keys(keys)``, that method is called before the loop starts;
    ``WOOTING_ACQUISITION`` uses it to verify that all three keys are available
    as analog keys on the connected Wooting keyboard.

    The mixin does not draw or replace the scrollbar. Pass any configured
    :class:`tachypy.scrollbar.Scrollbar` instance to :meth:`interact_slider`.

    Example
    -------
    .. code-block:: python

       acq = WOOTING_ACQUISITION()
       acq.initialize_keyboard()
       try:
           value, reaction_time = acq.interact_slider(
               slider=scrollbar,
               screen=screen,
               input_mode="keyboard",       # or "mouse_keyboard"
               decrease_key="z",            # lower value
               increase_key="c",             # higher value
               confirm_key="x",              # select value
           )
       finally:
           acq.uninitialize_keyboard()

    ``Escape`` is handled automatically when no ``response_handler`` is
    supplied. Additional ``run_slider_interaction`` options can be forwarded as
    keyword arguments, for example ``pressure_gamma`` or ``drawables``.
    """

    def interact_slider(
        self, *, slider, screen, response_handler=None,
        decrease_key="z", increase_key="c", confirm_key="x", **kwargs,
    ):
        """Run a scrollbar response using this acquisition's analog pressures.

        Parameters
        ----------
        slider : object
            TachyPy ``Scrollbar``-like object. It must expose ``set_value``,
            ``get_value``, and ``draw``. In ``mouse_keyboard`` mode it must also
            expose ``handle_mouse``.
        screen : TachyPy Screen-like object
            Display surface exposing ``flip()`` and optionally ``fill(color)``.
        response_handler : ResponseHandler, optional
            Input/event handler. If omitted, a default handler is created so
            window close and ``Escape`` can abort the interaction.
        decrease_key, increase_key, confirm_key : str or int, optional
            The three analog keys. Defaults to ``Z``, ``C``, and ``X``. They
            must be distinct, non-empty, and valid analog keys when the host
            provides ``validate_analog_keys``.
        **kwargs
            Options forwarded to :func:`run_slider_interaction`, including
            ``input_mode``, ``drawables``, ``initial_value``,
            ``movement_speed``, ``pressure_deadzone``, and ``pressure_gamma``.

        Returns
        -------
        (float, float) or (None, None)
            Selected scrollbar value and reaction time in seconds. ``(None,
            None)`` means the participant quit or the window was closed.

        Notes
        -----
        In ``keyboard`` mode, movement pressure is sampled continuously. In
        ``mouse_keyboard`` mode, the mouse controls the value and the confirm
        key selects it; the keyboard movement keys are not used for movement.
        """
        keys = tuple(str(key).strip().lower() for key in (decrease_key, increase_key, confirm_key))
        if not all(keys) or len(set(keys)) != 3:
            raise ValueError("Slider keys must be three distinct non-empty names")
        validate = getattr(self, "validate_analog_keys", None)
        if callable(validate):
            validate(keys)

        def read():
            values = self.read_pressures(keys)
            return SliderControls(*(values[key] for key in keys))

        return run_slider_interaction(
            slider=slider, screen=screen,
            response_handler=response_handler or ResponseHandler(screen=screen),
            control_reader=read, **kwargs,
        )


def _effective_pressure(pressure: float, deadzone: float, gamma: float) -> float:
    """Map raw pressure to movement strength after a deadzone.

    For ``pressure > deadzone``, the exact mapping is::

        effective = ((pressure - deadzone) / (1 - deadzone)) ** gamma

    The result is clipped to the ``0.0``–``1.0`` range before exponentiation.
    ``gamma=1`` is therefore linear *after* the deadzone. ``gamma > 1`` makes
    low pressures disproportionately gentle while keeping full pressure at
    full speed. ``gamma=0`` would be a step function (zero below the deadzone,
    one above it), not a linear mapping, and is rejected by the public loop.
    """
    if pressure <= deadzone:
        return 0.0
    return ((min(1.0, float(pressure)) - deadzone) / (1.0 - deadzone)) ** gamma


def run_slider_interaction(
    *,
    slider,
    screen,
    response_handler=None,
    input_mode: Literal["keyboard", "mouse_keyboard"] = "keyboard",
    control_reader: Callable[[], SliderControls] | None = None,
    validate_input: Callable[[], None] | None = None,
    drawables=(),
    initial_value: float = 50.0,
    movement_speed: float = 100.0,
    pressure_deadzone: float = 0.05,
    pressure_gamma: float = 2.5,
    confirm_threshold: float = 0.6,
    release_threshold: float = 0.03,
    mouse_quiet_period: float = 0.08,
    background_color=(128, 128, 128),
    clock: Callable[[], float] = time.perf_counter,
    wait_until: Callable[[float], None] | None = None,
):
    """Run a customizable scrollbar with analog controls.

    This is the backend-agnostic interaction loop. It never imports Wooting or
    another keyboard package: ``control_reader`` supplies the current controls,
    one :class:`SliderControls` object per frame. Use
    :meth:`AnalogSliderMixin.interact_slider` when the input source already has
    a ``read_pressures`` method.

    Parameters
    ----------
    slider : object
        Scrollbar-like widget exposing ``set_value(value)``, ``get_value()``,
        and ``draw()``. For ``mouse_keyboard`` it must also expose
        ``handle_mouse(x, y)``. A normal TachyPy ``Scrollbar`` keeps all of its
        visual and mouse customization.
    screen : TachyPy Screen-like object
        Must expose ``flip()``; if it exposes ``fill(color)``, the screen is
        cleared before each frame.
    response_handler : ResponseHandler-like object, optional
        Used for event polling, window-close/Escape detection, and mouse
        position in ``mouse_keyboard`` mode. It is optional in keyboard-only
        mode, although supplying one enables quit handling.
    input_mode : {"keyboard", "mouse_keyboard"}, default="keyboard"
        ``"keyboard"`` uses analog decrease/increase pressures for movement and
        the confirm pressure for selection. ``"mouse_keyboard"`` uses the mouse
        for movement and the confirm pressure for selection; the mouse must be
        quiet for ``mouse_quiet_period`` before confirmation.
    control_reader : callable
        Zero-argument callable returning ``SliderControls`` for the current
        frame. Values are expected in ``0.0``–``1.0``.
    validate_input : callable, optional
        Called once before the loop. Use this in a keyboard-specific adapter to
        validate key availability without putting keyboard imports here.
    drawables : sequence, optional
        Objects with ``draw()`` called after the scrollbar on every frame.
    initial_value : float, default=50.0
        Value assigned to the scrollbar at the start of the interaction.
    movement_speed : float, default=100.0
        Maximum scrollbar units per second at full effective pressure.
    pressure_deadzone : float, default=0.05
        Pressures at or below this value do not move the scrollbar.
    pressure_gamma : float, default=2.5
        Exponent used after deadzone normalization in
        ``effective = normalized_pressure ** pressure_gamma``. ``1`` gives a
        linear mapping after the deadzone; values above ``1`` make light
        presses slower and improve fine adjustment. ``0`` is invalid because it
        would create an abrupt on/off step rather than a useful speed curve.
    confirm_threshold : float, default=0.6
        Pressure that the confirm key must cross to select the value.
    release_threshold : float, default=0.03
        All three controls must fall below this level before a trial is armed.
        This prevents a key held from the previous trial from immediately
        moving or confirming the next one.
    mouse_quiet_period : float, default=0.08
        In ``mouse_keyboard`` mode, required seconds without mouse movement
        before confirmation is accepted.
    background_color : tuple, default=(128, 128, 128)
        RGB color used to clear the screen when ``fill`` is available.
    clock : callable, default=time.perf_counter
        Monotonic clock used for movement integration and reaction time.
    wait_until : callable, optional
        ``wait_until(deadline)`` used to pace the loop. Defaults to a portable
        sleep-based implementation; inject a deterministic function in tests.

    Returns
    -------
    (float, float) or (None, None)
        The selected scrollbar value and elapsed reaction time in seconds, or
        ``(None, None)`` if the response handler requests a quit.

    Raises
    ------
    ValueError
        If the input mode, control reader, or pressure thresholds are invalid.

    Examples
    --------
    A Wooting experiment normally uses the mixin adapter:

    .. code-block:: python

       value, rt = acquisition.interact_slider(
           slider=scrollbar, screen=screen,
           drawables=(instruction_text,),
           pressure_gamma=2.5,
       )

    A different analog keyboard can use the generic loop directly:

    .. code-block:: python

       def read_controls():
           return SliderControls(
               decrease=keyboard.pressure("z"),
               increase=keyboard.pressure("c"),
               confirm=keyboard.pressure("x"),
           )

       value, rt = run_slider_interaction(
           slider=scrollbar, screen=screen, control_reader=read_controls,
       )
    """
    if input_mode not in ("keyboard", "mouse_keyboard"):
        raise ValueError("input_mode must be 'keyboard' or 'mouse_keyboard'")
    if control_reader is None:
        raise ValueError("control_reader is required")
    if input_mode == "mouse_keyboard" and response_handler is None:
        raise ValueError("response_handler is required for mouse_keyboard mode")
    if not 0 <= pressure_deadzone < 1 or pressure_gamma <= 0:
        raise ValueError("Invalid pressure mapping parameters")
    if not 0 <= release_threshold < confirm_threshold <= 1:
        raise ValueError("Require 0 <= release_threshold < confirm_threshold <= 1")
    if validate_input is not None:
        validate_input()
    if wait_until is None:
        wait_until = lambda deadline: time.sleep(max(0.0, deadline - clock()))
    if response_handler is not None:
        if hasattr(response_handler, "clear_events"):
            response_handler.clear_events()
        if hasattr(response_handler, "reset_timer"):
            response_handler.reset_timer()

    slider.set_value(initial_value)
    start = last = clock()
    previous_confirm = 0.0
    armed = False
    last_mouse_move = float("-inf")
    next_tick = start

    def draw():
        if hasattr(screen, "fill"):
            screen.fill(background_color)
        slider.draw()
        for drawable in drawables:
            drawable.draw()
        screen.flip()

    while True:
        if response_handler is not None:
            response_handler.get_events()
            if response_handler.should_quit():
                return None, None

        now = clock()
        dt = min(max(0.0, now - last), 0.1)
        last = now
        controls = control_reader()
        movement_active = input_mode == "keyboard" and max(controls.decrease, controls.increase) > pressure_deadzone

        if not armed:
            armed = max(controls.decrease, controls.increase, controls.confirm) < release_threshold
            previous_confirm = controls.confirm
            if not armed:
                draw()
                next_tick += 0.001
                wait_until(next_tick)
                continue

        if input_mode == "mouse_keyboard":
            position = response_handler.get_mouse_position() if response_handler is not None else None
            moved = position is not None and slider.handle_mouse(*position)
            if moved:
                last_mouse_move = now
        elif movement_active:
            direction = _effective_pressure(controls.increase, pressure_deadzone, pressure_gamma)
            direction -= _effective_pressure(controls.decrease, pressure_deadzone, pressure_gamma)
            slider.set_value(slider.get_value() + movement_speed * direction * dt)

        if (
            previous_confirm < confirm_threshold <= controls.confirm
            and not movement_active
            and (input_mode == "keyboard" or now - last_mouse_move >= mouse_quiet_period)
        ):
            return slider.get_value(), now - start
        previous_confirm = controls.confirm
        draw()

        next_tick += 0.001
        wait_until(next_tick)
