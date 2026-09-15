<!--- SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors -->
<!--- SPDX-License-Identifier: AGPL-3.0-or-later -->

# icalendar-anonymizer

Part of the [Python Calendaring Ecosystem](https://pycal.org).

Strip personal data from iCalendar files while preserving technical properties for bug reproduction.

Calendar bugs are hard to reproduce without actual calendar data, but people can't share their calendars publicly due to privacy concerns. This tool uses hash-based anonymization to remove sensitive information (names, emails, locations, descriptions) while keeping all date/time, recurrence, and timezone data intact.

[![Documentation](https://readthedocs.org/projects/icalendar-anonymizer/badge/?version=stable)](https://docs.icalendar-anonymizer.com/stable/)
[![Tests](https://github.com/pycalendar/icalendar-anonymizer/actions/workflows/tests.yml/badge.svg)](https://github.com/pycalendar/icalendar-anonymizer/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/pycalendar/icalendar-anonymizer/branch/main/graph/badge.svg?token=BeroSsugTc)](https://codecov.io/gh/pycalendar/icalendar-anonymizer)
[![PyPI version](https://img.shields.io/pypi/v/icalendar-anonymizer.svg)](https://pypi.org/project/icalendar-anonymizer/)
[![Python versions](https://img.shields.io/pypi/pyversions/icalendar-anonymizer.svg)](https://pypi.org/project/icalendar-anonymizer/)
[![Container image](https://img.shields.io/badge/ghcr.io-pycalendar%2Ficalendar--anonymizer-blue)](https://github.com/pycalendar/icalendar-anonymizer/pkgs/container/icalendar-anonymizer)
[![License: AGPL-3.0-or-later](https://img.shields.io/badge/License-AGPL%203.0--or--later-blue.svg)](https://github.com/pycalendar/icalendar-anonymizer?tab=AGPL-3.0-1-ov-file#readme)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Usage

**Web Service:** https://icalendar-anonymizer.com

For installation and other usage options, see the [documentation](https://docs.icalendar-anonymizer.com/stable/).

## Contributing

See the [contributing guide](https://docs.icalendar-anonymizer.com/stable/contributing.html).


## Funding

This project is funded through [NGI0 Commons Fund](https://nlnet.nl/commonsfund), a fund established by [NLnet](https://nlnet.nl) with financial support from the European Commission's [Next Generation Internet](https://ngi.eu) program. Learn more at the [NLnet project page](https://nlnet.nl/project/Python-Webcalendaring).

[<img src="https://nlnet.nl/logo/banner.png" alt="NLnet foundation logo" width="20%" />](https://nlnet.nl)
[<img src="https://nlnet.nl/image/logos/NGI0_tag.svg" alt="NGI Zero Logo" width="20%" />](https://nlnet.nl/commonsfund)

## License

AGPL-3.0-or-later. See [LICENSE](LICENSE).
