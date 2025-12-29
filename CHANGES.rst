.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

==========
Change log
==========

.. icalendar-anonymizer uses `Semantic Versioning <https://semver.org>`_.
..
.. Given a version number MAJOR.MINOR.PATCH, increment the:
..
.. - MAJOR version when you make incompatible API changes.
.. - MINOR version when you add functionality in a backward compatible manner.
.. - PATCH version when you make backward compatible bug fixes.
..
.. When adding entries:
..
.. - Add entries as bullet points under the appropriate category.
.. - Use double backticks for `inline literals <https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html#rst-roles>`_.
..
..   .. code-block:: rst
..
..       ``PROPERTY``
..
.. - Use the `Python domain <https://www.sphinx-doc.org/en/master/usage/domains/python.html>`_ to mark up Python modules, classes, methods, and other Python objects.
..
..   .. code-block:: rst
..
..       :py:func:`function_name`
..
.. - Use the ``:file:`` directive for `files <https://www.sphinx-doc.org/en/master/usage/restructuredtext/roles.html#role-file>`_.
..
..   .. code-block:: rst
..
..       :file:`file.py`
..
.. - Reference issues and pull requests with a link when relevant.
..
..   .. code-block:: rst
..
..       See `Issue 123 <url>`_.
..
.. - Start with a past tense verb, such as "Added", "Fixed", "Removed", "Updated", and other verbs.

0.1.2 (unreleased)
------------------

.. _v0.1.2-new-features:

New features
''''''''''''

- Added FastAPI web service with three endpoints: ``POST /anonymize`` (JSON), ``POST /upload`` (file), ``GET /fetch`` (URL). SSRF protection blocks private IPs, localhost, and invalid schemes. 10s timeout, 10MB limit. Install: ``pip install icalendar-anonymizer[web]``. See `Issue 4 <https://github.com/mergecal/icalendar-anonymizer/issues/4>`_.

.. _v0.1.2-minor-changes:

Minor changes
'''''''''''''

.. _v0.1.2-bug-fixes:

Bug fixes
'''''''''

0.1.1 (2025-12-25)
------------------

.. _v0.1.1-new-features:

New features
''''''''''''

- Added Sphinx documentation with PyData theme on Read the Docs. Includes installation guide, Python API reference with property table and autodoc, CLI usage guide, web service API documentation, and contributing guide with commit format reference. Changed bash to shell code-block lexer, converted lists to definition lists, added documentation standards section. Configured :file:`docs/conf.py` with ``sphinx_design``, ``sphinx_copybutton``, ``sphinx.ext.intersphinx``. Updated :file:`pyproject.toml` with doc dependencies. Added badge to :file:`README.md`. Documentation at https://icalendar-anonymizer.readthedocs.io/stable/. See `Issue 9 <https://github.com/mergecal/icalendar-anonymizer/issues/9>`_ and `PR 60 <https://github.com/mergecal/icalendar-anonymizer/pull/60>`_.
- Added :file:`.readthedocs.yaml` configuration file with Ubuntu 24.04 build environment and Python 3.13 to enable automatic documentation builds on Read the Docs. See `PR 56 <https://github.com/mergecal/icalendar-anonymizer/pull/56>`_.
- Added command-line interface with :program:`icalendar-anonymize` and :program:`ican` commands. Supports stdin/stdout piping, file I/O, and verbose mode. Uses :program:`Click` for argument parsing with built-in ``-`` convention for Unix-style streams. Binary mode handling for ICS files. Comprehensive error handling with clear messages. Install with ``pip install icalendar-anonymizer[cli]``. See `Issue 3 <https://github.com/mergecal/icalendar-anonymizer/issues/3>`_.

.. _v0.1.1-minor-changes:

Minor changes
'''''''''''''

- Commented out CHANGES.rst formatting guidelines to hide from rendered documentation. Added note in :file:`CONTRIBUTING.md` directing contributors to read the source file for formatting guidelines. Guidelines remain visible in source. See `Issue 61 <https://github.com/mergecal/icalendar-anonymizer/issues/61>`_.

.. _v0.1.1-bug-fixes:

Bug fixes
'''''''''

- Fixed GitHub release notes to strip "v" prefix from PyPI version in install command. Added version extraction step in :file:`.github/workflows/release.yml` to convert tag ``v0.1.0`` to ``0.1.0`` for pip install command, ensuring correct PyPI package installation.

0.1.0 (2025-12-05)
------------------

.. _v0.1.0-new-features:

New features
''''''''''''

- Added ``preserve`` parameter to :py:func:`anonymize` function. Accepts optional set of property names to preserve beyond defaults. Case-insensitive. Allows preserving properties like ``CATEGORIES`` or ``COMMENT`` for bug reproduction when user confirms no sensitive data. Added 7 tests for preserve functionality. See `Issue 53 <https://github.com/mergecal/icalendar-anonymizer/issues/53>`_.
- Added core anonymization engine with :py:func:`anonymize` function using SHA-256 deterministic hashing. Removes personal data (names, emails, locations, descriptions) while preserving technical properties (dates, recurrence, timezones). Configurable salt parameter enables reproducible output. Property classification system with default-deny for unknown properties. Structure-preserving hash functions maintain word count and email format. UID uniqueness preserved across calendar. Special handling for ``ATTENDEE``/``ORGANIZER`` with ``CN`` parameter anonymization. Test suite with 35 tests achieves 95% coverage. See `Issue 1 <https://github.com/mergecal/icalendar-anonymizer/issues/1>`_ and `Issue 2 <https://github.com/mergecal/icalendar-anonymizer/issues/2>`_.
- Added comprehensive CI/CD workflows with GitHub Actions: test matrix across Ubuntu/Windows/macOS with Python 3.11-3.13, Ruff to lint and check the format of code, Codecov integration with multi-platform coverage tracking, PyPI trusted publishing (OIDC, no tokens required), Docker multi-arch builds (AMD64/ARM64), and automatic GitHub releases with generated notes. Added :file:`.github/workflows/tests.yml`, :file:`.github/workflows/publish.yml`, :file:`.github/workflows/docker.yml`, and :file:`.github/workflows/release.yml`. Configured hatch test matrix for local multi-version testing and coverage exclusions in :file:`pyproject.toml`. Added CI/CD badges to :file:`README.md` (tests, coverage, PyPI version, Python versions, Docker pulls). Added test structure with placeholder files referencing related issues. Docker images published to Docker Hub at ``sashankbhamidi/icalendar-anonymizer``. See `Issue 10 <https://github.com/mergecal/icalendar-anonymizer/issues/10>`_.
- Added :file:`.gitattributes` to normalize line endings across platforms (LF in repository, native line endings on checkout).
- Added comprehensive pre-commit hooks configuration with Ruff linting/formatting, file integrity checks, and commit message validation. Updated :file:`CONTRIBUTING.md` with setup instructions and usage documentation. Added Ruff badge to :file:`README.md`. See `Issue 20 <https://github.com/mergecal/icalendar-anonymizer/issues/20>`_.
- Added conventional commits configuration (``.cz.toml``), pre-commit hooks, CI workflows, and documentation. See `Issue 27 <https://github.com/mergecal/icalendar-anonymizer/issues/27>`_.
- Applied Sphinx best practices to ``CHANGES.rst`` including proper RST roles, subheadings, and past tense verbs. See `Issue 31 <https://github.com/mergecal/icalendar-anonymizer/issues/31>`_.
- Added project configuration files (``.gitignore``, ``.editorconfig``, ``.python-version``, ``requirements-dev.txt``). See `Issue 16 <https://github.com/mergecal/icalendar-anonymizer/issues/16>`_.
- Added :file:`LICENSE` with AGPL-3.0-or-later license. See `Issue 14 <https://github.com/mergecal/icalendar-anonymizer/issues/14>`_.
- Added :file:`CONTRIBUTING.md` with development workflow, commit message format, testing requirements, and project structure. See `Issue 15 <https://github.com/mergecal/icalendar-anonymizer/issues/15>`_.
- Added :file:`README.md` with installation instructions and usage examples for Python API, CLI, and web service. See `Issue 13 <https://github.com/mergecal/icalendar-anonymizer/issues/13>`_.
- Added :file:`pyproject.toml` with hatchling build system, hatch-vcs version management, package structure, and dependencies. Tests included in package at ``src/icalendar_anonymizer/tests/``. See `Issue 12 <https://github.com/mergecal/icalendar-anonymizer/issues/12>`_.
- Added REUSE specification compliance with SPDX headers to all source files, configuration files, documentation, and workflows. Added :file:`.github/workflows/reuse.yml` for automated CI compliance checking and ``reuse`` hook to :file:`.pre-commit-config.yaml` for local validation. Downloaded :file:`LICENSES/AGPL-3.0-or-later.txt`. Project is fully compliant with REUSE 3.3 specification for clear licensing. See `Issue 22 <https://github.com/mergecal/icalendar-anonymizer/issues/22>`_.

.. _v0.1.0-minor-changes:

Minor changes
'''''''''''''

- Standardized docstring format to multi-line Google-style across all modules. Removed placeholder Examples sections. See `Issue 52 <https://github.com/mergecal/icalendar-anonymizer/issues/52>`_.
- Parametrized duplicate test patterns using :py:func:`pytest.mark.parametrize` for datetime, recurrence, metadata, text anonymization, and word count tests. Reduced test duplication while maintaining coverage. See `Issue 52 <https://github.com/mergecal/icalendar-anonymizer/issues/52>`_.
- Added doctest validation for core modules with :file:`test_with_doctest.py`. See `Issue 52 <https://github.com/mergecal/icalendar-anonymizer/issues/52>`_.
- Updated :file:`CONTRIBUTING.md` with code style guidelines including docstring format, test organization patterns, and import conventions. See `Issue 52 <https://github.com/mergecal/icalendar-anonymizer/issues/52>`_.
