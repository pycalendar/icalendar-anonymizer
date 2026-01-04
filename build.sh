#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

set -euxo pipefail

# Remove previous build artifacts
rm -rf python_modules/icalendar_anonymizer
rm -rf src/icalendar_anonymizer/webapp/assets

# Ensure python_modules directory exists
mkdir -p python_modules

# Copy the package source to python_modules
# This makes icalendar_anonymizer importable in the Workers environment
cp -r src/icalendar_anonymizer python_modules/

# Remove test files, static files, and pycache from deployment
find python_modules/icalendar_anonymizer -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find python_modules/icalendar_anonymizer -type d -name "static" -exec rm -rf {} + 2>/dev/null || true
find python_modules/icalendar_anonymizer -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python_modules/icalendar_anonymizer -name "*.pyc" -delete 2>/dev/null || true

# Build assets directory structure for Cloudflare Workers
# Assets are served at root level, but we need /static prefix to match local dev
mkdir -p src/icalendar_anonymizer/webapp/assets/static
cp src/icalendar_anonymizer/webapp/static/index.html src/icalendar_anonymizer/webapp/assets/
cp src/icalendar_anonymizer/webapp/static/style.css src/icalendar_anonymizer/webapp/assets/static/
cp src/icalendar_anonymizer/webapp/static/app.js src/icalendar_anonymizer/webapp/assets/static/

echo "Build completed: icalendar_anonymizer package and assets prepared for Workers"
