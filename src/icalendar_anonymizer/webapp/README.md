<!--- SPDX-FileCopyrightText: 2025 icalendar-anonymizer contributors -->
<!--- SPDX-License-Identifier: AGPL-3.0-or-later -->

# Web Application Structure

This directory contains the FastAPI web service for icalendar-anonymizer.

## Directory Layout

```
webapp/
├── main.py          # FastAPI app with all API endpoints
├── r2.py            # R2 storage client (MockR2Client + WorkersR2Client)
├── static/          # Frontend source files (HTML/CSS/JS)
└── assets/          # [gitignored] Generated during Cloudflare deployment
```

## Deployment Modes

The same Python code runs in two environments:

### Self-Hosted (Local/Docker)

```bash
uvicorn icalendar_anonymizer.webapp.main:app
```

- Static files served by FastAPI from `static/`
- Uses `MockR2Client` (in-memory, non-persistent)
- Shareable links only last during the session

### Cloudflare Workers (icalendar-anonymizer.com)

- Entry point: `worker.py` (in repo root)
- Static files served via Cloudflare Assets from `assets/`
- Uses `WorkersR2Client` with R2 bucket binding
- Shareable links persist for 30 days

## Why Two Static Directories?

- `static/` - Source files, tracked in git
- `assets/` - Cloudflare Assets directory, gitignored

During Cloudflare deployment, `static/` is copied to `assets/`. This separation keeps the repo clean while allowing Cloudflare's asset pipeline to work correctly.

## R2 Client

The `r2.py` module provides two implementations of the same interface:

| Client | Environment | Storage |
|--------|-------------|---------|
| `MockR2Client` | Local/Docker | In-memory dict |
| `WorkersR2Client` | Cloudflare Workers | R2 bucket (Pyodide FFI) |

The correct client is injected via middleware in `main.py` based on the `CLOUDFLARE_WORKERS` environment variable.
