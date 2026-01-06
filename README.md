<!--- SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors -->
<!--- SPDX-License-Identifier: AGPL-3.0-or-later -->

# icalendar-anonymizer

Strip personal data from iCalendar files while preserving technical properties for bug reproduction.

Calendar bugs are hard to reproduce without actual calendar data, but people can't share their calendars publicly due to privacy concerns. This tool uses hash-based anonymization to remove sensitive information (names, emails, locations, descriptions) while keeping all date/time, recurrence, and timezone data intact.

[![Documentation](https://readthedocs.org/projects/icalendar-anonymizer/badge/?version=stable)](https://icalendar-anonymizer.readthedocs.io/stable/)
[![Tests](https://github.com/mergecal/icalendar-anonymizer/actions/workflows/tests.yml/badge.svg)](https://github.com/mergecal/icalendar-anonymizer/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mergecal/icalendar-anonymizer/graph/badge.svg?token=6tcJpy0th3)](https://codecov.io/gh/mergecal/icalendar-anonymizer)
[![PyPI version](https://img.shields.io/pypi/v/icalendar-anonymizer.svg)](https://pypi.org/project/icalendar-anonymizer/)
[![Python versions](https://img.shields.io/pypi/pyversions/icalendar-anonymizer.svg)](https://pypi.org/project/icalendar-anonymizer/)
[![Docker pulls](https://img.shields.io/docker/pulls/sashankbhamidi/icalendar-anonymizer.svg)](https://hub.docker.com/r/sashankbhamidi/icalendar-anonymizer)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL%203.0--or--later-blue.svg)](https://github.com/mergecal/icalendar-anonymizer?tab=AGPL-3.0-1-ov-file#readme)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Usage

**Web Service:** https://icalendar-anonymizer.com

For installation and other usage options, see the [documentation](https://docs.icalendar-anonymizer.com/stable/).

## Contributing

See the contributing guide at https://docs.icalendar-anonymizer.com/stable/contributing.html.

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
