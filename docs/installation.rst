.. SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
.. SPDX-License-Identifier: AGPL-3.0-or-later

============
Installation
============

This guide covers installation for end users. For development setup, see :doc:`contributing`.

Requirements
============

- Python 3.11, 3.12, or 3.13

Basic Installation
==================

Install the core package:

.. code-block:: shell

    python -m pip install icalendar-anonymizer

This installs only the Python library with its core dependency, ``icalendar``.

.. tip::

    Using ``python -m pip`` ensures you install to the correct Python interpreter.
    See `Why you should use python -m pip <https://snarky.ca/why-you-should-use-python-m-pip/>`_ for details.

Optional Features
=================

This section describes how to install optional features of ``icalendar-anonymizer``, including a command-line interface (CLI) and web service support.

Command-Line Interface
----------------------

Install the CLI with the following command.

.. code-block:: shell

    python -m pip install icalendar-anonymizer[cli]

This installs the :program:`icalendar-anonymize` and :program:`ican` commands. See :doc:`usage/cli` for usage details.

Web Service
-----------

Install the web service with the following command.

.. code-block:: shell

    python -m pip install icalendar-anonymizer[web]

This installs FastAPI, uvicorn, and dependencies for the REST API server. See :doc:`usage/web-service` for usage details.

All Features
------------

Install all the foregoing optional features with the following command.

.. code-block:: shell

    python -m pip install icalendar-anonymizer[all]

Docker
======

Pull and run the Docker image:

.. code-block:: shell

    docker pull sashankbhamidi/icalendar-anonymizer
    docker run -p 8000:8000 sashankbhamidi/icalendar-anonymizer

The web service will be available at http://localhost:8000. See :doc:`usage/self-hosting` for configuration options.

Verifying Installation
======================

Check the installation:

.. code-block:: python

    import icalendar_anonymizer
    print(icalendar_anonymizer.__version__)

Or check the installed version:

.. code-block:: shell

    python -m pip show icalendar-anonymizer

Upgrading
=========

Upgrade to the latest version:

.. code-block:: shell

    python -m pip install --upgrade icalendar-anonymizer

Uninstalling
============

Remove the package:

.. code-block:: shell

    python -m pip uninstall icalendar-anonymizer

Troubleshooting
===============

This section describes how to troubleshoot issues with installation.

Import Error
------------

If you get an ``ImportError`` when importing ``icalendar_anonymizer``, then try the following steps.

#. Verify that the package is installed.

   .. code-block:: shell

       pip list | grep icalendar

#. Check that you're using a supported version of Python.

   .. code-block:: shell

       python --version

#. Ensure that you're in the correct virtual environment.

Dependency Conflicts
--------------------

``icalendar-anonymizer`` requires a compatible version of ``icalendar``.
If you encounter dependency conflicts with ``icalendar``, then perform the following steps.

#. Check that your installed version of ``icalendar`` is supported by ``icalendar-anonymizer``.

   .. code-block:: shell

       pip show icalendar

#. Upgrade ``icalendar``, if needed.

   .. code-block:: shell

       python -m pip install --upgrade icalendar

Getting Help
============

If you encounter installation issues:

- Check the `Issue Tracker <https://github.com/mergecal/icalendar-anonymizer/issues>`_ for existing issues.
- If there isn't an existing issue, then open a new one.
