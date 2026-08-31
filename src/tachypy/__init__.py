"""TachyPy public API with lazy imports to avoid unnecessary backend loading."""

from importlib import import_module

__all__ = [
    "Screen",
    "Texture",
    "Draggable",
    "DraggableManager",
    "Circle",
    "Rectangle",
    "Line",
    "FixationCross",
    "center_rect_on_point",
    "ResponseHandler",
    "Scrollbar",
    "Text",
    "make_sine_grating",
    "make_gaussian_envelope",
    "make_gabor",
    "normalize_to_unit_interval",
    "make_wiggles_sine",
    "make_concentric_sine_circles",
    "make_sine_sectors",
    "make_checkerboard",
    "make_checkerboard_tile",
    "fabriquer_grille_sin",
    "fabriquer_gabor",
    "noisy_bit_dithering",
    "fabriquer_enveloppe_gaussienne",
    "stretch",
    "fabriquer_wiggles_sin",
    "fabriquer_cercles_sin",
    "fabriquer_secteurs_sin",
    "fabriquer_grand_damier",
    "fabriquer_petit_damier",
    "location_bubbles",
    "Audio",
    "QuestObject",
    "PressureFeedbackWidget",
    "InteractiveFixationCross",
    "PressureFeedbackState",
    "PressureFeedbackConfig",
    "PressureSource",
    "VisualPressureFeedbackMixin",
    "AnalogSliderMixin",
    "run_slider_interaction",
]


_EXPORT_MAP = {
    "Screen": ("tachypy.screen", "Screen"),
    "Texture": ("tachypy.textures", "Texture"),
    "Draggable": ("tachypy.draggable", "Draggable"),
    "DraggableManager": ("tachypy.draggable", "DraggableManager"),
    "Circle": ("tachypy.shapes", "Circle"),
    "Rectangle": ("tachypy.shapes", "Rectangle"),
    "Line": ("tachypy.shapes", "Line"),
    "FixationCross": ("tachypy.shapes", "FixationCross"),
    "center_rect_on_point": ("tachypy.shapes", "center_rect_on_point"),
    "ResponseHandler": ("tachypy.responses", "ResponseHandler"),
    "Scrollbar": ("tachypy.scrollbar", "Scrollbar"),
    "Text": ("tachypy.text", "Text"),
    "make_sine_grating": ("tachypy.psychophysics", "make_sine_grating"),
    "make_gaussian_envelope": ("tachypy.psychophysics", "make_gaussian_envelope"),
    "make_gabor": ("tachypy.psychophysics", "make_gabor"),
    "normalize_to_unit_interval": ("tachypy.psychophysics", "normalize_to_unit_interval"),
    "make_wiggles_sine": ("tachypy.psychophysics", "make_wiggles_sine"),
    "make_concentric_sine_circles": ("tachypy.psychophysics", "make_concentric_sine_circles"),
    "make_sine_sectors": ("tachypy.psychophysics", "make_sine_sectors"),
    "make_checkerboard": ("tachypy.psychophysics", "make_checkerboard"),
    "make_checkerboard_tile": ("tachypy.psychophysics", "make_checkerboard_tile"),
    "fabriquer_grille_sin": ("tachypy.psychophysics", "fabriquer_grille_sin"),
    "fabriquer_gabor": ("tachypy.psychophysics", "fabriquer_gabor"),
    "noisy_bit_dithering": ("tachypy.psychophysics", "noisy_bit_dithering"),
    "fabriquer_enveloppe_gaussienne": ("tachypy.psychophysics", "fabriquer_enveloppe_gaussienne"),
    "stretch": ("tachypy.psychophysics", "stretch"),
    "fabriquer_wiggles_sin": ("tachypy.psychophysics", "fabriquer_wiggles_sin"),
    "fabriquer_cercles_sin": ("tachypy.psychophysics", "fabriquer_cercles_sin"),
    "fabriquer_secteurs_sin": ("tachypy.psychophysics", "fabriquer_secteurs_sin"),
    "fabriquer_grand_damier": ("tachypy.psychophysics", "fabriquer_grand_damier"),
    "fabriquer_petit_damier": ("tachypy.psychophysics", "fabriquer_petit_damier"),
    "location_bubbles": ("tachypy.psychophysics", "location_bubbles"),
    "Audio": ("tachypy.audio", "Audio"),
    "QuestObject": ("tachypy.quest", "QuestObject"),
    "PressureFeedbackWidget": ("tachypy.feedback", "PressureFeedbackWidget"),
    "InteractiveFixationCross": ("tachypy.feedback", "InteractiveFixationCross"),
    "PressureFeedbackState": ("tachypy.feedback", "PressureFeedbackState"),
    "PressureFeedbackConfig": ("tachypy.feedback", "PressureFeedbackConfig"),
    "PressureSource": ("tachypy.feedback", "PressureSource"),
    "VisualPressureFeedbackMixin": ("tachypy.feedback", "VisualPressureFeedbackMixin"),
    "AnalogSliderMixin": ("tachypy.scrollbar_interaction", "AnalogSliderMixin"),
    "run_slider_interaction": ("tachypy.scrollbar_interaction", "run_slider_interaction"),
    # Wooting keyboard integration — convenience shortcut for the one distinctive,
    # high-frequency entry point: `from tachypy import WOOTING_ACQUISITION`.
    # Resolved lazily from the `tachypy.wooting` facade, which requires the
    # `tachypy[wooting]` extra (a clear ImportError is raised otherwise). Kept out
    # of `__all__` so tachypy core stays keyboard-agnostic and doc builds / `import *`
    # never pull in TachyWooting. Generic helpers (visualize, load_trial, lib, ffi, …)
    # are intentionally NOT aliased here — they live under `tachypy.wooting` to keep
    # the top-level namespace unambiguous and collision-free for future devices.
    "WOOTING_ACQUISITION": ("tachypy.wooting", "WOOTING_ACQUISITION"),
}


def __getattr__(name):
    """Lazily import and return public API attributes on first access."""
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module 'tachypy' has no attribute '{name}'")
    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
