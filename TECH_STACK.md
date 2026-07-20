# Technology Stack

A rundown of every technology in this project and what it does here.

**One-line summary:** a FastAPI + SQLAlchemy backend (SQLite/Postgres) serving
Jinja2 pages and a JSON API, with D3 v7 rendering charts client-side from a CDN,
fed by offline Python ETL scripts that pull from FRED and the Claude API.

## Backend (Python)

| Technology | Version | What it does here |
|---|---|---|
| **FastAPI** | 0.115.0 | The web framework. Defines page routes in `main.py` (`/`, `/stacked`, `/telephone`, `/inflation`) and JSON API routes in `routers/data.py` (under `/api`). Auto-generates Swagger docs at `/docs`. |
| **Uvicorn** (`[standard]`) | 0.30.6 | The ASGI server that actually runs the app (`uvicorn main:app --reload`). |
| **SQLAlchemy** | 2.0.35 | ORM + DB layer. Models in `models.py` (`ChartDataPoint`, `StackedDataPoint`, `InflationDataPoint`); engine/session/seeding in `database.py`. |
| **Jinja2** | 3.1.4 | Server-side HTML templating. Renders the pages in `templates/`. Pinned deliberately — a newer FastAPI/Starlette breaks it (see `CLAUDE.md`). |
| **Pydantic** | bundled w/ FastAPI | Request/response schemas in `schemas.py` — validates and serializes ORM rows to JSON (`DataPointOut`, `StackedPointOut`, `InflationPointOut`). |
| **python-multipart** | 0.0.10 | Form-data parsing support for FastAPI (dependency; not heavily exercised yet). |
| **Python** | 3.14 (in `venv/`) | Runtime. |

## Database

- **SQLite** — the default store, auto-created and seeded at `data/portfolio.db` on first startup. Delete the file to reseed.
- **PostgreSQL** — supported with zero code changes via `psycopg2`; set the `DATABASE_URL` env var before launch (`database.py:11`). Not active by default.

## Frontend (no build step)

- **D3.js v7** — the visualization library, imported directly as an ES module from the jsdelivr CDN (`https://cdn.jsdelivr.net/npm/d3@7/+esm`). All chart logic lives inline in the templates (`inflation.html`, `stacked.html`, etc.) — there's no bundler, npm frontend, or `static/js/`. Each page fetches from its `/api/...` endpoint and renders SVG.

## Offline ETL scripts (standalone — not imported by the app)

- **`inflation_etl.py`** — uses the **`requests`** library to pull real CPI category series + unemployment (`UNRATE`) from the **FRED public CSV export** (`fred.stlouisfed.org`, no API key), computes year-over-year %, and writes `inflation_data.json`.
- **`telephone_etl.py`** — uses the **`anthropic`** SDK to call **Claude (`claude-haiku-4-5-20251001`)** in a "telephone" loop, writing `telephone_results.json`.

> ⚠️ Note: `requests` and `anthropic` are **not** in `requirements.txt` — install them manually only when running these scripts.

## Tooling / infra

- **Git / GitHub** — version control (`origin/main`).
- **Swagger UI / OpenAPI** — auto-provided by FastAPI at `/docs`.
