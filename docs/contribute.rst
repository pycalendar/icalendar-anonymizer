.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

************
Contributing
************

This guide covers the development workflow, testing, code style, and other requirements to contribute to icalendar-anonymizer.

icalendar-anonymizer follows the Python Calendaring Ecosystem's `Code of Conduct <https://pycal.org/code-of-conduct/>`_.

.. _development-prerequisites:

.. include:: ./_include/prerequisites.inc

.. _development-configure-git:

.. include:: ./_include/configure-git.inc
.. include:: ./_include/configure-git-card-dev.inc
.. include:: ./_include/configure-git-steps.inc


Install icalendar-anonymizer for development
============================================

Change your directory to your local clone.

.. code-block:: shell

    cd icalendar-anonymizer

Install icalendar-anonymizer for development—including all of its dependencies for tests, documentation, and formatting code, as well as a Python virtual environment—with the following command.

.. code-block:: shell

    make dev


Development workflow
====================

This section covers the general development workflow.
Subsequent sections go into more detail.

Follow these steps from the root of your clone.

1.  Check out the ``main`` branch, update it locally, and create a branch from it.

    ..  code-block:: shell

        git checkout main
        git pull origin main
        git checkout -b feature-name

#.  Write your code changes, corresponding tests, docstrings, and narrative documentation.
    All new features must include tests and documentation.

#.  Run tests.
    You can pass any options that pytest supports as an environment variable or argument ``TESTOPTS``.

    ..  code-block:: shell

        make test

#.  Build documentation and view a live preview in a web browser.

    ..  code-block:: shell

        make livehtml

#.  Check links in documentation.

    ..  code-block:: shell

        make linkcheckbroken

#.  Check spelling, style, and grammar in narrative documentation.

    ..  code-block:: shell

        make vale

#.  Lint and format code.

    ..  code-block:: shell

        make lint-check  # Check for linting errors
        make lint-fix    # Auto-fix linting errors
        make format      # Format code

#.  Commit your changes, using the `Conventional Commits <https://www.conventionalcommits.org/en/v1.0.0/>`_ message format that follows :doc:`contribute/commit-format`.

    ..  code-block:: shell

        git add .
        git commit -m "feat: add new feature description"

#.  Push your changes to GitHub.

    ..  code-block:: shell

        git push origin feature-name

#.  Open a pull request on GitHub.


Run tests
=========

This section describes how to run tests.

Run all tests
-------------

..  code-block:: shell

    make test

Run tests with coverage
-----------------------

..  code-block:: shell

    make coverage

The test coverage report will be in ``htmlcov/index.html``.

Test requirements
-----------------

All tests must satisfy the following requirements.

-   A minimum of 90% coverage is required and enforced by continuous integration (CI).
-   All tests must pass.
-   All new features and bug fixes must have tests.
-   Use parametrized tests to reduce duplication, as described in :ref:`test-organization`.

CI test matrix
--------------

Continuous integration runs tests on the matrix cross-product of the following parameters.

-   Python versions 3.11, 3.12, and 3.13
-   Ubuntu, Windows, and macOS operating systems

This creates nine test jobs.
Tests must pass across the entire matrix.


Code quality
============

Use `Ruff <https://docs.astral.sh/ruff/>`_ for linting and formatting code.
Ruff is configured to limit line length to one-hundred characters.

Check for lint errors
---------------------

..  code-block:: shell

    make lint-check

Fix lint errors
---------------

..  code-block:: shell

    make lint-fix

This project sets ``unsafe-fixes = true`` in :file:`pyproject.toml`, so ``make lint-fix`` applies Ruff's unsafe fixes too, not only the safe ones.
Review the diff before committing.

Format code
-----------

..  code-block:: shell

    make format

Configuration
-------------

Ruff settings are in :file:`pyproject.toml` under the ``[tool.ruff]`` table.

CI enforces the same Ruff version as that used in development.

pre-commit hooks
================

pre-commit hooks catch issues before committing, providing feedback faster than waiting for CI.
These are installed automatically when creating a development environment.
The hooks are defined in :file:`.pre-commit-config.yaml`.

What runs on every commit
-------------------------

-   Code lint
-   Code format
-   REUSE compliance validates SPDX license headers
-   File integrity checks:

    -   Trailing whitespace removal
    -   End-of-file fixer
    -   YAML, JSON, and TOML syntax validation
    -   Python AST check
    -   Case conflict check
    -   Merge conflict detection
    -   Large file prevention, configured to detect files larger than 1MB
    -   Line ending normalization to ``LF``
    -   Debug statement detection

-   Commit message validation, enforcing Conventional Commits format

Performance
-----------

All checks complete in under five seconds.

Run pre-commit manually
-----------------------

You can run pre-commit manually.

Run all hooks on all files.

..  code-block:: shell

    make pc

    pre-commit run ruff --all-files  # Run specific hook

Skip hooks
----------

For work-in-progress commits, you can skip pre-commit hooks with the following command.
Use it sparingly.

..  code-block:: shell

    git commit --no-verify

..  note::

    pre-commit is optional for contributors.
    CI enforces the same checks regardless.
    Core maintainers should use it.

Code style guidelines
=====================

This section describes guidelines for writing code in icalendar-anonymizer.

Docstrings
----------

Use Google-style docstrings with multi-line format:

..  code-block:: python

    def foo(arg1: str, arg2: int) -> str:
        """Brief description on first line.

        More detailed explanation if needed. Can span multiple paragraphs.

        Args:
            arg1: Description of first argument
            arg2: Description of second argument

        Returns:
            Description of return value

        Raises:
            ValueError: When invalid input provided
        """

Include an Examples section only with real, testable doctests.


..  _test-organization:

Test organization
-----------------

Use ``pytest.mark.parametrize`` for duplicate test patterns:

..  code-block:: python

    @pytest.mark.parametrize(
        ("property_name", "expected_value"),
        [
            ("status", "CONFIRMED"),
            ("priority", 1),
        ],
    )
    def test_preserves_metadata(property_name, expected_value):
        """Test implementation."""

Organize tests into logical groups with clear section comments.

Imports
-------

-   Standard library imports first
-   Third-party imports second
-   Local imports third
-   Sort alphabetically within each group

..  code-block:: python

    # Standard library
    import hashlib
    from datetime import datetime

    # Third-party
    from icalendar import Calendar

    # Local
    from icalendar_anonymizer import anonymize

Line length
-----------

The maximum line length for code is 100 characters maximum.
It is enforced by Ruff.

Documentation style guidelines
==============================

This section describes the guidelines for writing documentation for icalendar-anonymizer. 

API documentation
-----------------

Use :program:`autodoc` for API function signatures in Sphinx documentation:

..  code-block:: rst

    .. autofunction:: icalendar_anonymizer.anonymize

This ensures documentation stays in sync with code.
Don't manually copy function signatures.

Code examples
-------------

Use doctest format for Python examples in documentation:

..  code-block:: rst

    ..  doctest::

        >>> from icalendar import Calendar
        >>> from icalendar_anonymizer import anonymize
        >>> # Example code here

This allows examples to be automatically tested for correctness.

Pull request process
====================

This section describes the guidelines for working with pull requests for icalendar-anonymizer. 

Requirements
------------

The following list of requirements must be satisfied to merge a pull request.

-   At least one approval is required before merge
-   All tests must pass
-   Coverage must be greater than or equal to 90%
-   Pull request title must follow :doc:`contribute/commit-format`
-   A change log entry (see :ref:`change-log`), unless the change doesn't affect users

Title format
------------

Pull request titles must follow conventional commits because maintainers use squash merge:

..  code-block:: text

    feat: add preserve parameter to anonymize function
    fix: correct UID uniqueness handling
    docs: update installation instructions

The pull request title becomes the commit message on the ``main`` branch.

Change log
----------

See :ref:`change-log` below.

.. _artificial-intelligence-policy:

Artificial intelligence policy
==============================

icalendar-anonymizer follows the Python Calendaring Ecosystem's `AI policy <https://pycal.org/ai-policy/>`_. Read it before using AI to help draft a pull request.

.. _change-log:

Change log
==========

If your PR changes behavior, add a news fragment. CI-only and internal-refactor PRs don't need one.

..  code-block:: shell

    touch news/<issue-number>.<type>.rst

Where ``<type>`` is one of: ``breaking``, ``removal``, ``feature``, ``bugfix``, ``documentation``, ``deps``, ``internal``, ``chore``, ``security``.

Write a short, user-facing description of the change inside the file, starting with a past tense verb such as "Added," "Fixed," "Removed," or "Updated." Use double backticks for inline literals (``` ``PROPERTY`` ```), the ``:py:func:``/``:py:class:`` roles for Python objects, and the ``:file:`` role for file paths. Towncrier appends the issue link automatically from the filename, so don't add one yourself. For a change with no issue number, name the file ``+<short-description>.<type>.rst`` instead.

Fragments are collected into :file:`CHANGES.rst` at release time. Don't edit that file directly.

If you used AI to help write the change, briefly disclose it in the fragment, per the :ref:`artificial-intelligence-policy`.

To preview what the change log will look like:

..  code-block:: shell

    towncrier build --draft --version 0.0.0

If you're unsure whether your PR needs a fragment, ask a maintainer rather than skipping silently.

License and REUSE compliance
============================

This project follows the `REUSE specification <https://reuse.software/>`_ for clear licensing.

License
-------

The project is licensed under AGPL-3.0-or-later.

SPDX headers and :file:`REUSE.toml`
-----------------------------------

All new source files must include SPDX headers.
Autogenerated files that cannot have persistent headers may instead rely on entries in :file:`REUSE.toml` as a fallback.

SPDX headers are required in all source files:

Python files
^^^^^^^^^^^^

..  code-block:: python

    # SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
    # SPDX-License-Identifier: AGPL-3.0-or-later

reStructuredText files
^^^^^^^^^^^^^^^^^^^^^^

..  code-block:: rst

    .. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
    .. SPDX-License-Identifier: AGPL-3.0-or-later

Markdown files
^^^^^^^^^^^^^^

..  code-block:: markdown

    <!--- SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors -->
    <!--- SPDX-License-Identifier: AGPL-3.0-or-later -->

:file:`REUSE.toml`
^^^^^^^^^^^^^^^^^^

Use :file:`REUSE.toml` only as a fallback for autogenerated files that cannot reasonably include headers.
It must not be treated as a substitute for adding headers to regular source files.

Check compliance
================

pre-commit hooks automatically check REUSE compliance.
You can also run the check manually:

..  code-block:: shell

    reuse lint

All files must pass REUSE compliance before merge.

Cloudflare Workers deployment
=============================

The hosted service at https://icalendar-anonymizer.com runs on Cloudflare Workers, using `Pyodide <https://pyodide.org/>`_ to run the same FastAPI app as the pip package.
This section is for contributors working on that deployment path.
It's not required knowledge for the library, CLI, or self-hosted web service.

:file:`worker.py` at the repository root is the Workers entry point (:file:`wrangler.jsonc`'s ``main``).
Before importing the FastAPI app, it sets ``CLOUDFLARE_WORKERS=true`` in the environment.
:file:`src/icalendar_anonymizer/webapp/main.py` reads that variable at import time and at request time to:

-   Mount ``icalendar_anonymizer.webapp.r2.WorkersR2Client`` instead of the in-memory ``MockR2Client`` used everywhere else
-   Skip mounting ``/static`` via FastAPI's ``StaticFiles`` (Cloudflare Workers serves static assets itself)
-   Report ``r2_enabled: true`` from ``GET /health``

:file:`wrangler.jsonc` configures the rest of the deployment: an R2 bucket binding (``CALENDAR_SHARE_BUCKET``) for shareable links, the custom domain route, and an ``assets.run_worker_first`` list of paths that must reach the Python worker instead of being served as static files.

:file:`build.sh` prepares a deployable tree before ``wrangler deploy`` runs: it copies the package into ``python_modules/`` (Workers' Pyodide runtime imports it from there) and copies the static frontend into ``src/icalendar_anonymizer/webapp/assets/`` (the directory :file:`wrangler.jsonc`'s ``assets.directory`` points at).
The ``cloudflare-deploy.yml`` GitHub Actions workflow runs this on every ``v*`` tag push, or manually via ``workflow_dispatch``.

Get help
========

-   Check the `Issue Tracker <https://github.com/pycalendar/icalendar-anonymizer/issues>`_
-   Open a new issue for bugs or feature requests
-   For major changes, open an issue for discussion before starting work

Reference
=========

..  toctree::
    :maxdepth: 1

    contribute/commit-format
