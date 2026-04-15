"""Sphinx configuration for TachyPy docs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "TachyPy"
author = "TachyPy contributors"
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
]
autosummary_generate = True
autodoc_mock_imports = [
    "pygame",
    "OpenGL",
    "glfw",
    "sounddevice",
    "screeninfo",
    "PIL",
    "freetype",
    "uharfbuzz",
]
templates_path = ["_templates"]
exclude_patterns = ["_build"]
html_theme = "alabaster"
