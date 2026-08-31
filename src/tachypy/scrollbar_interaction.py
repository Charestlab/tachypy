"""Keyboard and mouse interaction for TachyPy scrollbar-like widgets.

The interaction loop is deliberately separate from :class:`tachypy.scrollbar.Scrollbar`:
``Scrollbar`` owns drawing and value/geometry handling, while this module owns
input, timing, movement, confirmation, and quit handling. This keeps
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
``X`` to confirm. Movement starts slowly and accelerates while a key remains
above the deadzone. Confirmation is only accepted while neither movement key
is active.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Literal

from tachypy.responses import ResponseHandler
from tachypy.screen import LoopPacer


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
    """Add analog-key scrollbar interaction to an acquisition.

    The host object must implement ``read_pressures(keys)`` and return a mapping
    from each requested key to a normalized pressure. If it implements
    ``validate_analog_keys(keys)``, that method is called before the loop starts.
    The Wooting implementation raises for an unmapped key, before any response
    is collected.

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
    keyword arguments, for example ``acceleration`` or ``drawables``.

    Notes
    -----
    Analog polling targets ~1 kHz between display submissions. Rendering is
    paced separately; a blocking ``flip()`` can briefly pause same-thread
    polling.
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
            expose ``move_by(delta_x, mouse_y)``.
        screen : TachyPy Screen-like object
            Display surface exposing ``flip()`` and optionally ``fill(color)``.
        response_handler : ResponseHandler, optional
            Input/event handler. If omitted, a default handler is created so
            window close and ``Escape`` can abort the interaction.
        decrease_key, increase_key, confirm_key : str or int, optional
            The three analog keys. Defaults to ``Z``, ``C``, and ``X``. They
            must be distinct, non-empty, and valid analog keys. A Wooting host
            raises before the loop if a key is not mapped as analog.
        **kwargs
            Options forwarded to :func:`run_slider_interaction`, including
            ``input_mode``, ``drawables``, ``control_callback``, ``initial_value``,
            ``movement_speed``, ``acceleration``, ``pressure_deadzone``,
            ``curve_x``, ``curve_y``, ``edge_margin``, and ``edge_reduction``.

        Returns
        -------
        (float, float) or (None, None)
            Selected scrollbar value and reaction time in seconds. ``(None,
            None)`` means the participant quit or the window was closed.

        Notes
        -----
        In ``keyboard`` mode, movement pressure is sampled continuously. In
        ``mouse_keyboard`` mode, the mouse or the analog movement keys control
        the value, and the confirm key or a mouse click selects it.
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


def _movement_direction(controls: SliderControls, deadzone: float) -> int:
    """Return -1, 0, or 1 from thresholded movement keys."""
    decrease = controls.decrease if controls.decrease > deadzone else 0.0
    increase = controls.increase if controls.increase > deadzone else 0.0
    return (increase > decrease) - (decrease > increase)


def _quadratic_speed(hold_time, acceleration, maximum, curve_x, curve_y):
    """Return speed on the bounded quadratic hold curve."""
    phase = min(max(hold_time * acceleration / maximum - curve_x, 0.0), 1.0)
    return maximum * max(0.0, curve_y + (1 - curve_y) * phase**2)


def _accelerated_step(hold_time, dt, acceleration, maximum, curve_x=0.0, curve_y=0.0):
    """Integrate one step of the quadratic hold-to-speed curve."""
    ramp_time = maximum / acceleration
    offset = -curve_x * ramp_time
    effective_hold = min(ramp_time, hold_time + offset)
    new_hold = min(max(0.0, ramp_time - offset), hold_time + dt)
    new_effective = min(ramp_time, new_hold + offset)
    accelerating = new_effective - effective_hold
    zero_crossing = ramp_time * (-curve_y / (1 - curve_y)) ** 0.5 if curve_y < 0 else 0.0
    positive_start = max(effective_hold, zero_crossing)
    positive_duration = max(0.0, new_effective - positive_start)
    distance = maximum * curve_y * positive_duration
    distance += maximum * (1 - curve_y) * max(
        0.0, new_effective**3 - positive_start**3,
    ) / (3 * ramp_time**2)
    distance += maximum * (dt - accelerating)
    return distance, new_hold


def _edge_scale(value, direction, margin, reduction):
    """Scale outward movement near an endpoint; inward movement stays unchanged."""
    if margin <= 0 or reduction <= 0:
        return 1.0
    distance = value if direction < 0 else 100 - value
    return min(max(distance / margin, 0.0), 1.0) ** reduction


def run_slider_interaction(
    *,
    slider,
    screen,
    response_handler=None,
    input_mode: Literal["keyboard", "mouse_keyboard"] = "keyboard",
    control_reader: Callable[[], SliderControls] | None = None,
    control_callback: Callable[[SliderControls], bool | None] | None = None,
    validate_input: Callable[[], None] | None = None,
    drawables=(),
    initial_value: float | None = 50.0,
    movement_speed: float = 100.0,
    acceleration: float = 100.0,
    pressure_deadzone: float = 15 / 255,
    curve_x: float = -0.25,
    curve_y: float = -0.03,
    edge_margin: float = 10.0,
    edge_reduction: float = 0.6,
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
        ``move_by(delta_x, mouse_y)``. A normal TachyPy ``Scrollbar`` keeps all
        of its visual and mouse customization.
    screen : TachyPy Screen-like object
        Must expose ``flip()``; if it exposes ``fill(color)``, the screen is
        cleared before each frame.
    response_handler : ResponseHandler-like object, optional
        Used for event polling, window-close/Escape detection, and mouse
        position in ``mouse_keyboard`` mode. It is optional in keyboard-only
        mode, although supplying one enables quit handling. Mouse mode also
        requires ``set_position`` for automatic edge recentering.
    input_mode : {"keyboard", "mouse_keyboard"}, default="keyboard"
        ``"keyboard"`` uses analog decrease/increase pressures for movement and
        the confirm pressure for selection. ``"mouse_keyboard"`` accepts both
        mouse or analog-key movement and either a left mouse click or the confirm
        pressure for selection; the mouse must be quiet for
        ``mouse_quiet_period`` before confirmation.
        Any analog-key pressure above the deadzone temporarily gives the
        keyboard exclusive control.
        The hidden cursor is recentered horizontally when it reaches a screen
        edge, so relative movement remains available in both directions.
    control_reader : callable
        Zero-argument callable returning ``SliderControls`` for the current
        frame. Values are expected in ``0.0``–``1.0``.
    control_callback : callable, optional
        Receives each ``SliderControls`` sample after it is read. This can
        update lightweight live feedback without polling the keyboard twice.
        Return ``True`` to stop the interaction with ``(None, None)``.
    validate_input : callable, optional
        Called once before the loop. Use this in a keyboard-specific adapter to
        validate key availability without putting keyboard imports here.
    drawables : sequence, optional
        Objects with ``draw()`` called after the scrollbar on every frame.
    initial_value : float or None, default=50.0
        Value assigned at the start. Use ``None`` to preserve the scrollbar's
        current value, such as the selection from the preceding trial.
    movement_speed : float, default=100.0
        Maximum scrollbar units per second reached while a movement key is held.
    acceleration : float, default=100.0
        Controls the quadratic speed ramp. With ``curve_x=0``, maximum speed is
        reached after ``movement_speed / acceleration`` seconds; a negative
        ``curve_x`` shortens that duration. Releasing or changing direction
        resets the ramp immediately.
    pressure_deadzone : float, default=15/255
        Pressures at or below 15 on the keyboard's 0–255 scale do not move the
        scrollbar.
    curve_x : float, default=-0.25
        Horizontal position of the quadratic vertex, from ``-1`` to ``0``, as
        a proportion of ramp duration. Negative values start farther along the
        curve; ``-1`` starts at maximum speed.
    curve_y : float, default=-0.03
        Vertical position of the quadratic vertex, from ``-1`` to ``1``, as a
        proportion of ``movement_speed``. Positive values increase initial
        speed; negative portions of the curve are clamped to zero speed.
    edge_margin : float, default=10.0
        Distance from each endpoint over which outward keyboard movement is
        progressively reduced. ``0`` disables edge reduction.
    edge_reduction : float, default=0.6
        Strength of edge reduction. ``0`` disables it, ``1`` gives a linear
        reduction, and values above ``1`` slow movement more strongly. Movement
        back toward the center is never reduced.
    confirm_threshold : float, default=0.6
        Pressure that the confirm key must cross to select the value.
    release_threshold : float, default=0.03
        The confirm key must fall below this level once before it can select a
        value. Movement keys remain responsive from the first input sample.
    mouse_quiet_period : float, default=0.08
        Required seconds without mouse movement before mouse confirmation is
        accepted. It is also used by ``mouse_keyboard`` mode before keyboard
        confirmation.
    background_color : tuple, default=(128, 128, 128)
        RGB color used to clear the screen when ``fill`` is available.
    clock : callable, default=time.perf_counter
        Monotonic clock used for movement integration and reaction time.
    wait_until : callable, optional
        ``wait_until(deadline)`` used to pace the loop. Defaults to a portable
        sleep-based implementation; inject a deterministic function in tests.

    Notes
    -----
    Control polling targets ~1 kHz between display submissions. Rendering is
    paced separately; a blocking ``flip()`` can briefly pause same-thread
    polling.

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
           acceleration=200,
           movement_speed=80,
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
        raise ValueError("response_handler is required for mouse input")
    if input_mode == "mouse_keyboard" and not hasattr(response_handler, "set_position"):
        raise ValueError("mouse_keyboard mode requires response_handler.set_position")
    if input_mode == "mouse_keyboard" and not hasattr(slider, "move_by"):
        raise ValueError("mouse_keyboard mode requires slider.move_by(delta_x, mouse_y)")
    mouse_was_visible = getattr(screen, "mouse_visible", None)
    if (movement_speed <= 0 or acceleration <= 0 or not 0 <= pressure_deadzone < 1
            or not -1 <= curve_x <= 0 or not -1 <= curve_y <= 1
            or edge_margin < 0 or edge_reduction < 0 or mouse_quiet_period < 0):
        raise ValueError("Invalid movement, deadzone, or edge parameters")
    if not 0 <= release_threshold < confirm_threshold <= 1:
        raise ValueError("Require 0 <= release_threshold < confirm_threshold <= 1")
    if validate_input is not None:
        validate_input()
    if input_mode == "mouse_keyboard" and hasattr(screen, "hide_mouse"):
        screen.hide_mouse()
    if wait_until is None:
        wait_until = lambda deadline: time.sleep(max(0.0, deadline - clock()))
    if response_handler is not None:
        if hasattr(response_handler, "clear_events"):
            response_handler.clear_events()
        if hasattr(response_handler, "reset_timer"):
            response_handler.reset_timer()

    if initial_value is not None:
        slider.set_value(initial_value)
    previous_confirm = 0.0
    confirm_armed = False
    last_mouse_move = float("-inf")
    last_mouse_position = None
    consumed_mouse_clicks = 0
    movement_hold_time = 0.0
    previous_direction = 0

    def draw():
        if hasattr(screen, "fill"):
            screen.fill(background_color)
        slider.draw()
        for drawable in drawables:
            drawable.draw()
        screen.flip()

    def finish(result):
        if (input_mode == "mouse_keyboard" and mouse_was_visible is not None
                and hasattr(screen, "show_mouse") and hasattr(screen, "hide_mouse")):
            (screen.show_mouse if mouse_was_visible else screen.hide_mouse)()
        return result

    draw()
    start = last = clock()
    try:
        pacer = LoopPacer(screen, wait_until, start, defer_first_render=True)
    except Exception:
        finish(None)
        raise

    while True:
        if response_handler is not None:
            response_handler.get_events()
            if response_handler.should_quit():
                return finish((None, None))

        now = clock()
        dt = min(max(0.0, now - last), 0.1)
        last = now
        controls = control_reader()
        if control_callback is not None and control_callback(controls):
            return finish((None, None))
        if not confirm_armed and controls.confirm < release_threshold:
            confirm_armed = True
        keyboard_active = max(controls.decrease, controls.increase, controls.confirm) > pressure_deadzone
        direction = _movement_direction(controls, pressure_deadzone)
        movement_keys_held = (
            input_mode in ("keyboard", "mouse_keyboard")
            and (controls.decrease > pressure_deadzone or controls.increase > pressure_deadzone)
        )
        movement_active = movement_keys_held and direction != 0

        mouse_position = None
        mouse_moved = False
        previous_mouse_position = None
        if input_mode == "mouse_keyboard":
            mouse_position = response_handler.get_mouse_position()
            previous_mouse_position = last_mouse_position
            mouse_moved = previous_mouse_position is not None and mouse_position != previous_mouse_position
            if mouse_moved:
                last_mouse_move = now
            last_mouse_position = mouse_position

        if input_mode == "mouse_keyboard" and mouse_moved:
            if not keyboard_active:
                delta_x = mouse_position[0] - previous_mouse_position[0]
                slider.move_by(delta_x, mouse_position[1])
            if hasattr(screen, "width") and (
                    mouse_position[0] <= 1 or mouse_position[0] >= screen.width - 1):
                center = (screen.width / 2, mouse_position[1])
                response_handler.set_position(*center)
                last_mouse_position = center
                last_mouse_move = now

        if movement_active:
            if direction != previous_direction:
                movement_hold_time = 0.0
            distance, movement_hold_time = _accelerated_step(
                movement_hold_time, dt, acceleration, movement_speed, curve_x, curve_y,
            )
            distance *= _edge_scale(
                slider.get_value(), direction, edge_margin, edge_reduction,
            )
            # Clamp here, not in set_value(): hitting an edge via a held key isn't a mistake.
            target = max(0.0, min(100.0, slider.get_value() + direction * distance))
            slider.set_value(target)
        else:
            movement_hold_time = 0.0
        previous_direction = direction

        if input_mode == "mouse_keyboard":
            all_clicks = response_handler.get_mouse_clicks()
            new_clicks = all_clicks[consumed_mouse_clicks:]
            consumed_mouse_clicks = len(all_clicks)
            if not keyboard_active:
                for click in new_clicks:
                    if (click["type"] == "mouseup" and click.get("button", 0) == 0
                            and now - last_mouse_move >= mouse_quiet_period):
                        return finish((slider.get_value(), now - start))

        if (
            # movement_keys_held, not movement_active: a tied Z/C press still blocks confirm.
            confirm_armed
            and previous_confirm < confirm_threshold <= controls.confirm
            and not movement_keys_held
            and (input_mode == "keyboard" or now - last_mouse_move >= mouse_quiet_period)
        ):
            return finish((slider.get_value(), now - start))
        previous_confirm = controls.confirm
        if pacer.render_due(now):
            draw()
            now = clock()
            pacer.after_render(now)
        pacer.wait(now)
