# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

"""icalendar-anonymizer - Strip personal data from iCalendar files.

This package provides tools to anonymize iCalendar data while preserving
technical properties for bug reproduction.
"""

from ._config import CONFIGURABLE_FIELDS, AnonymizeMode
from .anonymizer import anonymize
from .formats.jcal import anonymize_jcal
from .formats.jscal import JSCAL_CONFIGURABLE_FIELDS, anonymize_jscal
from .version import __version__, __version_tuple__, version, version_tuple

__all__ = [
    "CONFIGURABLE_FIELDS",
    "JSCAL_CONFIGURABLE_FIELDS",
    "AnonymizeMode",
    "__version__",
    "__version_tuple__",
    "anonymize",
    "anonymize_jcal",
    "anonymize_jscal",
    "version",
    "version_tuple",
]
