Contributing
============

Local development workflow
--------------------------

.. code-block:: bash

   pip install -e ".[test]"
   ruff check src tests
   pytest

Pull request expectations
-------------------------

- Add regression tests for bug fixes.
- Keep APIs documented with docstrings.
- Update docs/README when behavior or setup changes.
- Ensure CI passes before merge.

Suggested branch protections
----------------------------

- Require passing CI checks on pull requests.
- Require at least one approving review.
- Disallow direct pushes to ``main``.
