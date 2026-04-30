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
..       :issue:`123`
..       :pr:`456`
..
.. - Start with a past tense verb, such as "Added", "Fixed", "Removed", "Updated", and other verbs.

0.1.5 (unreleased)
------------------

.. _v0.1.5-new-features:

New features
''''''''''''

- Added Dependabot config. :issue:`78`
- Added ``CODEOWNERS``. :issue:`28`
- Added ``SECURITY.md``. :issue:`44`
- Added ``field_modes`` support to Fernet live-proxy tokens so per-field UI choices are applied on fetch. :issue:`139`
- Added Open Web Calendar tutorial at :file:`docs/tutorials/open-web-calendar.rst`. :issue:`93`
- Added :file:`docs/examples.rst` with real-world workflows. :issue:`59`

.. _v0.1.5-minor-changes:

Minor changes
'''''''''''''

.. _v0.1.5-bug-fixes:

Bug fixes
'''''''''

0.1.4 (2026-04-20)
------------------

.. _v0.1.4-new-features:

New features
''''''''''''

- Persisted per-field anonymization options across page loads via ``localStorage``. :issue:`116`

.. _v0.1.4-minor-changes:

Minor changes
'''''''''''''

- Removed "(30-day expiry)" from shareable-link checkbox labels. :issue:`113`
- Synced per-field anonymization options across Upload, Paste, and Fetch URL tabs. :issue:`115`
- Changed web UI default field modes: SUMMARY keeps original, other text/address fields are removed, UID remains randomized. :issue:`117`

.. _v0.1.4-bug-fixes:

Bug fixes
'''''''''

- Fixed :file:`Dockerfile` ``CMD`` to use JSON array form with ``sh -c`` wrapper, resolving the ``JSONArgsRecommended`` lint warning while preserving shell variable expansion for ``HOST``, ``PORT``, and ``WORKERS``.
- Preserved ``X-WR-TIMEZONE``. :issue:`112`

0.1.3 (2026-04-02)
------------------

.. _v0.1.3-new-features:

New features
''''''''''''

- Added automatic Docker build trigger on release via ``gh workflow run`` in :file:`.github/workflows/release.yml`. :issue:`77`

.. _v0.1.3-minor-changes:

Minor changes
'''''''''''''

- Migrated repository from ``mergecal`` to ``pycalendar`` GitHub organization.
- Docker image moved from Docker Hub (``sashankbhamidi/icalendar-anonymizer``) to GitHub Container Registry (``ghcr.io/pycalendar/icalendar-anonymizer``). All historical tags are available at the new location. :issue:`71` :pr:`106`

0.1.2 (2026-02-11)
------------------

.. _v0.1.2-new-features:

New features
''''''''''''

- Added configurable per-field anonymization modes with four options: keep (preserve original), remove (strip property), randomize (hash - default), and replace (fixed placeholder). Supports 10 configurable fields: ``SUMMARY``, ``DESCRIPTION``, ``LOCATION``, ``COMMENT``, ``CONTACT``, ``RESOURCES``, ``CATEGORIES``, ``ATTENDEE``, ``ORGANIZER``, and ``UID``. New ``field_modes`` parameter in :py:func:`anonymize` function. CLI flags: ``--summary``, ``--description``, ``--location``, etc. Web API: ``config`` field in request bodies and query parameters. Frontend: collapsible "Advanced Options" section in all three tabs. Backward compatible with existing ``preserve`` parameter. Constraint: ``UID`` cannot use remove mode (would break recurring events). :issue:`92`
- Added Fernet-based encrypted links for live calendar proxying. Endpoints: ``POST /fernet-generate`` (creates token) and ``GET /fernet/{token}`` (fetches and anonymizes on-the-fly). Token encrypts source URL and salt via ``FERNET_KEY`` environment variable. Frontend radio buttons toggle between Fernet (live) and R2 (snapshot) modes. Vendors pure-Python Fernet implementation for Cloudflare Workers compatibility. :issue:`95`
- Added ``/anonymized`` endpoint for curl-friendly anonymization. Supports GET with ``ics`` query parameter and POST with raw ICS body. Returns ``text/calendar`` without ``Content-Disposition`` header for easy piping. :issue:`25`
- Added shareable links with Cloudflare R2 storage. Users can generate time-limited public URLs for anonymized calendars with 30-day auto-expiry. New endpoints: ``POST /share`` (generate link) and ``GET /s/{id}`` (retrieve file). Frontend checkboxes in all three tabs (upload, paste, fetch URL). R2 client wrapper with MockR2Client for local dev and WorkersR2Client for production. Health endpoint reports R2 availability. R2 bucket binding configured in :file:`wrangler.jsonc`. :issue:`7`
- Added Cloudflare Workers deployment support with Python FastAPI via Pyodide. Configured :file:`wrangler.jsonc` for Workers Assets serving static files. Created :file:`worker.py` entry point using ``asgi.fetch()`` integration. Added :file:`build.sh` to bundle local package into ``python_modules/``. GitHub Actions workflow deploys on main branch. Custom domain configured at https://icalendar-anonymizer.com. :issue:`19` :pr:`83`
- Added Docker setup for self-hosting. Multi-stage :file:`Dockerfile` with Python 3.13-slim, non-root user (UID 1000), and gunicorn with uvicorn workers. Health check endpoint ``GET /health`` returns service status, version, and feature flags. :file:`docker-compose.yml` with environment variables for host, port, workers, and file size limit. Documentation at :file:`docs/usage/self-hosting.rst`. :issue:`8`
- Added frontend interface with file upload, paste, and URL fetch capabilities. Implemented drag and drop file upload with visual feedback. Added progressive enhancement for no-JavaScript environments. Provided WCAG AA compliant accessibility features (keyboard navigation, screen readers). Included mobile-responsive design for all device sizes. Zero external dependencies (vanilla HTML/CSS/JS). :issue:`5`
- Added FastAPI web service with three endpoints: ``POST /anonymize`` (JSON), ``POST /upload`` (file), ``GET /fetch`` (URL). SSRF protection blocks private IPs, localhost, and invalid schemes. 10s timeout, 10MB limit. Install: ``pip install icalendar-anonymizer[web]``. :issue:`4`

.. _v0.1.2-minor-changes:

Minor changes
'''''''''''''

- Added :file:`REUSE.toml` for fallback licensing of files without SPDX headers (auto-generated :file:`_version.py`). In-file headers remain preferred. :issue:`58`
- Improved test coverage for Cloudflare Workers integration. :pr:`90`
- Moved ``fastapi``, ``httpx``, and ``python-multipart`` from core dependencies to ``[web]`` extras. Base installation now only requires ``icalendar``. :issue:`23`
- Updated documentation to use ``python -m pip`` per best practices.

.. _v0.1.2-bug-fixes:

Bug fixes
'''''''''

- Fixed Fernet encryption for Cloudflare Workers by vendoring pyaes and fernet (MIT-licensed from ``ricmoo/pyaes`` and ``oz123/python-fernet``). Pyodide requires pure-Python or wasm32 wheels; ``cryptography`` has neither on PyPI. Added ``FERNET_KEY`` env copy from Workers to ``os.environ``. :pr:`100` :pr:`101`
- Fixed property iteration causing subcomponent corruption. Changed calendar property iteration from ``property_items()`` to ``items()`` to avoid copying subcomponent properties to calendar level, and added filtering of ``BEGIN``/``END`` structural markers in component property processing. This resolves malformed ICS output where event properties appeared at calendar level and were wrapped in spurious subcomponents during serialization/deserialization. :issue:`92`
- Fixed Cloudflare Workers deployment issues including module bundling, build order, static asset serving, and wrangler configuration. :pr:`84` :pr:`85` :pr:`86` :pr:`87` :pr:`88`

0.1.1 (2025-12-25)
------------------

.. _v0.1.1-new-features:

New features
''''''''''''

- Added Sphinx documentation with PyData theme on Read the Docs. Includes installation guide, Python API reference with property table and autodoc, CLI usage guide, web service API documentation, and contributing guide with commit format reference. Changed bash to shell code-block lexer, converted lists to definition lists, added documentation standards section. Configured :file:`docs/conf.py` with ``sphinx_design``, ``sphinx_copybutton``, ``sphinx.ext.intersphinx``. Updated :file:`pyproject.toml` with doc dependencies. Added badge to :file:`README.md`. Documentation at https://icalendar-anonymizer.readthedocs.io/stable/. :issue:`9` :pr:`60`
- Added :file:`.readthedocs.yaml` configuration file with Ubuntu 24.04 build environment and Python 3.13 to enable automatic documentation builds on Read the Docs. :pr:`56`
- Added command-line interface with :program:`icalendar-anonymize` and :program:`ican` commands. Supports stdin/stdout piping, file I/O, and verbose mode. Uses :program:`Click` for argument parsing with built-in ``-`` convention for Unix-style streams. Binary mode handling for ICS files. Comprehensive error handling with clear messages. Install with ``pip install icalendar-anonymizer[cli]``. :issue:`3`

.. _v0.1.1-minor-changes:

Minor changes
'''''''''''''

- Commented out CHANGES.rst formatting guidelines to hide from rendered documentation. Added note in :file:`CONTRIBUTING.md` directing contributors to read the source file for formatting guidelines. Guidelines remain visible in source. :issue:`61`

.. _v0.1.1-bug-fixes:

Bug fixes
'''''''''

- Fixed GitHub release notes to strip "v" prefix from PyPI version in install command. Added version extraction step in :file:`.github/workflows/release.yml` to convert tag ``v0.1.0`` to ``0.1.0`` for pip install command, ensuring correct PyPI package installation.

0.1.0 (2025-12-05)
------------------

.. _v0.1.0-new-features:

New features
''''''''''''

- Added ``preserve`` parameter to :py:func:`anonymize` function. Accepts optional set of property names to preserve beyond defaults. Case-insensitive. Allows preserving properties like ``CATEGORIES`` or ``COMMENT`` for bug reproduction when user confirms no sensitive data. Added 7 tests for preserve functionality. :issue:`53`
- Added core anonymization engine with :py:func:`anonymize` function using SHA-256 deterministic hashing. Removes personal data (names, emails, locations, descriptions) while preserving technical properties (dates, recurrence, timezones). Configurable salt parameter enables reproducible output. Property classification system with default-deny for unknown properties. Structure-preserving hash functions maintain word count and email format. UID uniqueness preserved across calendar. Special handling for ``ATTENDEE``/``ORGANIZER`` with ``CN`` parameter anonymization. Test suite with 35 tests achieves 95% coverage. :issue:`1` :issue:`2`
- Added comprehensive CI/CD workflows with GitHub Actions: test matrix across Ubuntu/Windows/macOS with Python 3.11-3.13, Ruff to lint and check the format of code, Codecov integration with multi-platform coverage tracking, PyPI trusted publishing (OIDC, no tokens required), Docker multi-arch builds (AMD64/ARM64), and automatic GitHub releases with generated notes. Added :file:`.github/workflows/tests.yml`, :file:`.github/workflows/publish.yml`, :file:`.github/workflows/docker.yml`, and :file:`.github/workflows/release.yml`. Configured hatch test matrix for local multi-version testing and coverage exclusions in :file:`pyproject.toml`. Added CI/CD badges to :file:`README.md` (tests, coverage, PyPI version, Python versions, Docker pulls). Added test structure with placeholder files referencing related issues. Docker images originally published to Docker Hub at ``sashankbhamidi/icalendar-anonymizer``; migrated to GitHub Container Registry at ``ghcr.io/pycalendar/icalendar-anonymizer`` in v0.1.3. :issue:`10`
- Added :file:`.gitattributes` to normalize line endings across platforms (LF in repository, native line endings on checkout).
- Added comprehensive pre-commit hooks configuration with Ruff linting/formatting, file integrity checks, and commit message validation. Updated :file:`CONTRIBUTING.md` with setup instructions and usage documentation. Added Ruff badge to :file:`README.md`. :issue:`20`
- Added conventional commits configuration (``.cz.toml``), pre-commit hooks, CI workflows, and documentation. :issue:`27`
- Applied Sphinx best practices to ``CHANGES.rst`` including proper RST roles, subheadings, and past tense verbs. :issue:`31`
- Added project configuration files (``.gitignore``, ``.editorconfig``, ``.python-version``, ``requirements-dev.txt``). :issue:`16`
- Added :file:`LICENSE` with AGPL-3.0-or-later license. :issue:`14`
- Added :file:`CONTRIBUTING.md` with development workflow, commit message format, testing requirements, and project structure. :issue:`15`
- Added :file:`README.md` with installation instructions and usage examples for Python API, CLI, and web service. :issue:`13`
- Added :file:`pyproject.toml` with hatchling build system, hatch-vcs version management, package structure, and dependencies. Tests included in package at ``src/icalendar_anonymizer/tests/``. :issue:`12`
- Added REUSE specification compliance with SPDX headers to all source files, configuration files, documentation, and workflows. Added :file:`.github/workflows/reuse.yml` for automated CI compliance checking and ``reuse`` hook to :file:`.pre-commit-config.yaml` for local validation. Downloaded :file:`LICENSES/AGPL-3.0-or-later.txt`. Project is fully compliant with REUSE 3.3 specification for clear licensing. :issue:`22`

.. _v0.1.0-minor-changes:

Minor changes
'''''''''''''

- Standardized docstring format to multi-line Google-style across all modules. Removed placeholder Examples sections. :issue:`52`
- Parametrized duplicate test patterns using :py:func:`pytest.mark.parametrize` for datetime, recurrence, metadata, text anonymization, and word count tests. Reduced test duplication while maintaining coverage. :issue:`52`
- Added doctest validation for core modules with :file:`test_with_doctest.py`. :issue:`52`
- Updated :file:`CONTRIBUTING.md` with code style guidelines including docstring format, test organization patterns, and import conventions. :issue:`52`
