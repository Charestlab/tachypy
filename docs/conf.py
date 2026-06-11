"""Sphinx configuration for TachyPy docs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

project = "TachyPy"
author = "TachyPy contributors"
extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
]
autosummary_generate = True
autodoc_mock_imports = [
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
html_theme = "furo"
html_title = "TachyPy"
html_static_path = ["_static"]
html_theme_options = {
    "sidebar_hide_name": False,
    "source_repository": "https://github.com/Charestlab/tachypy/",
    "source_branch": "main",
    "source_directory": "docs/",
}
