# SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors
# SPDX-License-Identifier: AGPL-3.0-or-later

# syntax=docker/dockerfile:1

# Build stage
FROM python:3.13-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml README.md ./
COPY .git/ ./.git/
COPY src/ ./src/

# Build wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Runtime stage
FROM python:3.13-slim

LABEL org.opencontainers.image.title="icalendar-anonymizer"
LABEL org.opencontainers.image.description="Strip personal data from iCalendar files while preserving technical properties for bug reproduction"
LABEL org.opencontainers.image.url="https://github.com/pycalendar/icalendar-anonymizer"
LABEL org.opencontainers.image.source="https://github.com/pycalendar/icalendar-anonymizer"
LABEL org.opencontainers.image.licenses="AGPL-3.0-or-later"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package with web dependencies, gunicorn, uvicorn and performance extras
RUN pip install --no-cache-dir "$(ls /tmp/*.whl)[web]" \
    gunicorn httptools uvloop && \
    rm -rf /tmp/*.whl

# Switch to non-root user
USER appuser

# Environment variables with defaults
ENV HOST=0.0.0.0 \
    PORT=8000 \
    WORKERS=4 \
    PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Run with gunicorn
CMD ["sh", "-c", "gunicorn icalendar_anonymizer.webapp.main:app --bind ${HOST}:${PORT} --workers ${WORKERS} --worker-class uvicorn.workers.UvicornWorker --access-logfile - --error-logfile -"]
