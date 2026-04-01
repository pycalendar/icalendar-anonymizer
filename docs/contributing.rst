.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

============
Contributing
============

This guide covers the development workflow, testing, code style, and contribution requirements.

.. note::
   A shorter quick-reference version is available in the repository's :file:`CONTRIBUTING.md` file for GitHub.

Getting Started
===============

Fork and Clone
--------------

Fork the repository on GitHub, then clone your fork:

.. code-block:: shell

    git clone https://github.com/YOUR-USERNAME/icalendar-anonymizer.git
    cd icalendar-anonymizer

Install Development Dependencies
--------------------------------

Install in editable mode with dev extras:

.. code-block:: shell

    pip install -e ".[dev]"

This installs:

- **pytest** - Testing framework
- **ruff** - Linting and code formatting
- **pre-commit** - Git hook management
- **commitizen** - Conventional commit enforcement
- **reuse** - License compliance checking
- **build** and **twine** - Package building and publishing

For documentation building, also install:

.. code-block:: shell

    pip install -e ".[doc]"

Development Workflow
====================

1. **Create a Feature Branch**

   Create a branch from ``main``:

   .. code-block:: shell

       git checkout main
       git pull origin main
       git checkout -b feature-name

2. **Make Changes with Tests**

   Write your code changes and corresponding tests. All new features must include tests.

3. **Run Tests and Linting**

   .. code-block:: shell

       pytest                     # Run tests
       ruff check .               # Check for linting errors
       ruff check . --fix         # Auto-fix linting errors
       ruff format .              # Format code

4. **Commit with Conventional Format**

   Follow :doc:`contribute/commit-format` for commit messages:

   .. code-block:: shell

       git add .
       git commit -m "feat: add new feature description"

5. **Push and Open Pull Request**

   .. code-block:: shell

       git push origin feature-name

   Then open a pull request on GitHub.

Running Tests
=============

Run All Tests
-------------

.. code-block:: shell

    pytest

Run with Coverage
-----------------

.. code-block:: shell

    pytest --cov=src/icalendar_anonymizer --cov-report=html

Coverage report will be in ``htmlcov/index.html``.

Test Requirements
-----------------

- **90% minimum coverage** required - PRs fail if coverage drops below this threshold
- All tests must pass before merge
- Add tests for all new features and bug fixes
- Use parametrized tests to reduce duplication (see :ref:`contributing:Test Organization`)

CI Test Matrix
--------------

Continuous integration runs tests on:

- **Python versions**: 3.11, 3.12, 3.13
- **Operating systems**: Ubuntu, Windows, macOS

This creates 9 test jobs total. All must pass before merge.

Code Quality
============

Linting with Ruff
-----------------

We use `Ruff <https://docs.astral.sh/ruff/>`_ for linting and code formatting with a **100-character line length**.

Check for Errors
^^^^^^^^^^^^^^^^

.. code-block:: shell

    ruff check .

Auto-Fix Errors
^^^^^^^^^^^^^^^

.. code-block:: shell

    ruff check . --fix

Format Code
^^^^^^^^^^^

.. code-block:: shell

    ruff format .

Configuration
^^^^^^^^^^^^^

Ruff settings are in ``pyproject.toml`` under ``[tool.ruff]``. The CI enforces the same Ruff version (>=0.14.0) for consistency.

Pre-commit Hooks (Recommended)
==============================

Pre-commit hooks catch issues before committing, providing faster feedback than waiting for CI.

Setup (One-Time)
----------------

.. code-block:: shell

    pre-commit install                          # Install pre-commit hooks
    pre-commit install --hook-type commit-msg   # Install commit message validation

What Runs on Every Commit
-------------------------

- **Ruff linting** (``ruff check --fix``) - Auto-fixes linting errors
- **Ruff formatting** (``ruff format``) - Auto-formats Python code
- **REUSE compliance** (``reuse lint``) - Validates SPDX license headers
- **File integrity checks**:
  - Trailing whitespace removal
  - End-of-file fixer
  - YAML/JSON/TOML validation
  - Python AST check
  - Case conflict check
  - Merge conflict detection
  - Large file prevention (>1MB)
  - Line ending normalization (LF)
  - Debug statement detection
- **Commit message validation** - Enforces conventional commits format

Performance
-----------

All checks complete in under 5 seconds.

Run Manually
------------

.. code-block:: shell

    pre-commit run --all-files       # Run all hooks on all files
    pre-commit run ruff --all-files  # Run specific hook

Skip Hooks (Sparingly)
----------------------

For work-in-progress commits:

.. code-block:: shell

    git commit --no-verify

Note on Pre-commit
------------------

Pre-commit is **optional** for contributors. CI enforces the same checks regardless. Core maintainers should use it.

Code Style Guidelines
=====================

Docstrings
----------

Use **Google-style docstrings** with multi-line format:

.. code-block:: python

    def function(arg1: str, arg2: int) -> str:
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

Don't include Examples sections unless they contain real, testable doctests.

Test Organization
-----------------

Use ``pytest.mark.parametrize`` for duplicate test patterns:

.. code-block:: python

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

- Standard library imports first
- Third-party imports second
- Local imports third
- Sort alphabetically within each group

.. code-block:: python

    # Standard library
    import hashlib
    from datetime import datetime

    # Third-party
    from icalendar import Calendar

    # Local
    from icalendar_anonymizer import anonymize

Line Length
-----------

**100 characters maximum** - enforced by Ruff.

Documentation
-------------

API Documentation
^^^^^^^^^^^^^^^^^

Use **autodoc** for API function signatures in Sphinx documentation:

.. code-block:: rst

    .. autofunction:: icalendar_anonymizer.anonymize

This ensures documentation stays in sync with code. Don't manually copy function signatures.

Code Examples
^^^^^^^^^^^^^

Use **doctest format** for Python examples in documentation:

.. code-block:: rst

    .. doctest::

        >>> from icalendar import Calendar
        >>> from icalendar_anonymizer import anonymize
        >>> # Example code here

This allows examples to be automatically tested for correctness.

Pull Request Process
====================

Requirements
------------

- **One approval** required before merge
- All tests must pass (9 test jobs)
- Coverage must be ≥90%
- PR title must follow :doc:`contribute/commit-format`
- Update ``CHANGES.rst`` with your changes

PR Title Format
---------------

PR titles must follow conventional commits because we use squash merge:

.. code-block:: text

    feat: add preserve parameter to anonymize function
    fix: correct UID uniqueness handling
    docs: update installation instructions

The PR title becomes the commit message on ``main``.

Update CHANGES.rst
------------------

Add your changes to ``CHANGES.rst`` following the formatting rules documented in the file header.

See :ref:`contributing:CHANGES.rst Formatting` below.

CHANGES.rst Formatting
======================

Add entries under the appropriate category in ``CHANGES.rst``:

Categories
----------

- **Breaking changes** - Incompatible API changes
- **New features** - New functionality
- **Minor changes** - Small improvements
- **Bug fixes** - Bug fixes

Formatting Rules
----------------

Use these RST formatting conventions:

Inline Literals
^^^^^^^^^^^^^^^

Use double backticks for property names and inline code:

.. code-block:: rst

    ``PROPERTY``
    ``preserve`` parameter

Python Objects
^^^^^^^^^^^^^^

Use Python domain roles:

.. code-block:: rst

    :py:func:`function_name`
    :py:class:`ClassName`
    :py:meth:`method_name`

Files
^^^^^

Use the ``:file:`` directive:

.. code-block:: rst

    :file:`docs/conf.py`
    :file:`pyproject.toml`

Issue Links
^^^^^^^^^^^

Reference issues with full URLs:

.. code-block:: rst

    See `Issue 9 <https://github.com/pycalendar/icalendar-anonymizer/issues/9>`_.

Verbs
^^^^^

Start entries with past tense verbs:

- Added
- Fixed
- Updated
- Removed
- Deprecated

Example Entry
-------------

.. code-block:: rst

    - Added ``preserve`` parameter to :py:func:`anonymize` function. Accepts optional
      set of property names to preserve beyond defaults. Case-insensitive. Allows
      preserving properties like ``CATEGORIES`` or ``COMMENT`` for bug reproduction
      when user confirms no sensitive data. Added 7 tests for preserve functionality.
      See `Issue 53 <https://github.com/pycalendar/icalendar-anonymizer/issues/53>`_.

See the ``CHANGES.rst`` file header for complete formatting guidelines.

Licensing and REUSE Compliance
==============================

This project follows the `REUSE specification <https://reuse.software/>`_ for clear licensing.

License
-------

The project is licensed under **AGPL-3.0-or-later**.

SPDX Headers and REUSE.toml
----------------------------

**All new source files must include SPDX headers.** Auto-generated files that cannot have persistent headers may instead rely on entries in ``REUSE.toml`` as a fallback.

**In-file headers** (required for all source files):

Python Files
^^^^^^^^^^^^

.. code-block:: python

    # SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
    # SPDX-License-Identifier: AGPL-3.0-or-later

RST Files
^^^^^^^^^

.. code-block:: rst

    .. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
    .. SPDX-License-Identifier: AGPL-3.0-or-later

Markdown Files
^^^^^^^^^^^^^^

.. code-block:: markdown

    <!--- SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors -->
    <!--- SPDX-License-Identifier: AGPL-3.0-or-later -->

**REUSE.toml** (fallback only):

Use ``REUSE.toml`` only as a fallback for auto-generated files that cannot reasonably include headers; it must not be treated as a substitute for adding headers to regular source files.

Checking Compliance
-------------------

Pre-commit hooks automatically check REUSE compliance. You can also run manually:

.. code-block:: shell

    reuse lint

All files must pass REUSE compliance before merge.

Getting Help
============

- Check the `Issue Tracker <https://github.com/pycalendar/icalendar-anonymizer/issues>`_
- Open a new issue for bugs or feature requests
- For major changes, open an issue for discussion before starting work

Reference
=========

.. toctree::
   :maxdepth: 1

   contribute/commit-format
