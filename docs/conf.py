# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""Sphinx configuration for icalendar-anonymizer documentation."""

project = "icalendar-anonymizer"
copyright = "2025, icalendar-anonymizer contributors"  # noqa: A001
author = "icalendar-anonymizer contributors"

# Extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_issues",
]

# sphinx_issues configuration
issues_github_path = "pycalendar/icalendar-anonymizer"

# Theme configuration
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/pycalendar/icalendar-anonymizer",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/icalendar-anonymizer",
            "icon": "fa-brands fa-python",
            "type": "fontawesome",
        },
    ],
    "logo": {"text": "icalendar-anonymizer"},
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "navbar_align": "content",
    "show_nav_level": 1,
    "navigation_with_keys": True,
    "collapse_navigation": False,
    "search_bar_text": "Search documentation",
}

html_context = {
    "github_user": "pycalendar",
    "github_repo": "icalendar-anonymizer",
    "github_version": "main",
    "doc_path": "docs",
}

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "icalendar": ("https://icalendar.readthedocs.io/en/latest/", None),
}

# Napoleon settings (Google-style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
}

# Autosectionlabel settings
autosectionlabel_prefix_document = True
