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

Protected main workflow
-----------------------

``main`` is protected. Do not push feature work directly to ``main``. Use a
short-lived branch and open a pull request:

.. code-block:: bash

   git switch -c feature/my-change
   # edit files, add tests/docs
   ruff check src tests
   pytest
   git push -u origin feature/my-change

Then open a pull request against ``main``. Before merge:

- Required CI checks must pass, including lint, tests, coverage, and docs.
- At least one approving review is required.
- Requested code-owner review should be resolved before merging.
- Stale approvals should be refreshed after meaningful new commits.
- All review conversations should be resolved.

Code owners
-----------

The repository uses ``.github/CODEOWNERS`` to request owner review
automatically. If a change touches any file, GitHub asks the listed owner to
review the pull request. This supports the branch ruleset option
``Require review from Code Owners``.

Branch protection settings
--------------------------

- Require passing CI checks on pull requests.
- Require at least one approving review.
- Require review from Code Owners.
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Disallow direct pushes to ``main``.
- Block force pushes and branch deletion for ``main``.
