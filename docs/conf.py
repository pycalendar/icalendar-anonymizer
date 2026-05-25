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
]

# Theme configuration
html_theme = "pydata_sphinx_theme"
html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/pycalendar/icalendar-anonymizer",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
            "attributes": {
                "target": "_blank",
                "rel": "noopener me",
                "class": "nav-link custom-fancy-css",
            },
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/icalendar",
            "icon": "fa-custom fa-pypi",
            "type": "fontawesome",
            "attributes": {
                "target": "_blank",
                "rel": "noopener me",
                "class": "nav-link custom-fancy-css",
            },
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

html_static_path = [
    "_static",
]
# Customize the navbar icons
html_js_files = [
   ("js/custom-icons.js", {"defer": "defer"}),
]
# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "icalendar": ("https://icalendar.readthedocs.io/en/latest/", None),
}

# -- linkcheck builder configuration ----------------------------------
# Ignore localhost
linkcheck_ignore = [
    # Ignore local development server
    r"http://127.0.0.1",
    r"http://localhost",
    # Ignore pages that require authentication
    r"https://calendar.google.com/",
    r"https://github.com/pycalendar/icalendar-anonymizer/fork",
    # Ignore specific anchors
]
linkcheck_anchors = True
linkcheck_timeout = 5
linkcheck_retries = 1

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
