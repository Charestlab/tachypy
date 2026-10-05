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
autodoc_preserve_defaults = True
autodoc_mock_imports = [
    "OpenGL",
    "glfw",
    "tachyaudio",
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

# Badge substitutions shared by every page
rst_epilog = """
.. |ci| image:: https://github.com/Charestlab/tachypy/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/Charestlab/tachypy/actions/workflows/ci.yml
   :alt: CI
.. |pypi| image:: https://img.shields.io/pypi/v/tachypy.svg
   :target: https://pypi.org/project/tachypy/
   :alt: PyPI version
.. |pyversions| image:: https://img.shields.io/pypi/pyversions/tachypy.svg
   :target: https://pypi.org/project/tachypy/
   :alt: Python versions
.. |docs| image:: https://readthedocs.org/projects/tachypy/badge/?version=latest
   :target: https://tachypy.readthedocs.io/en/latest/?badge=latest
   :alt: Docs status
.. |license| image:: https://img.shields.io/github/license/Charestlab/tachypy.svg
   :target: https://github.com/Charestlab/tachypy/blob/main/LICENSE
   :alt: License
"""
