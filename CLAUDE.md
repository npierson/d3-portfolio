# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate
uvicorn main:app --reload
```

Server runs at http://localhost:8000. Swagger UI at `/docs`. SQLite DB is created and seeded on first startup at `data/portfolio.db` — delete that file to reseed.

To use Postgres instead: `export DATABASE_URL="postgresql+psycopg2://..."` before launching. No code change needed (`database.py:11`).

## Architecture

FastAPI app with two distinct response surfaces backed by one SQLAlchemy/SQLite store:

- **Page routes** live directly on the app in `main.py` (`/`, `/stacked`, `/telephone`) and render Jinja2 templates from `templates/`.
- **JSON API routes** live in `routers/data.py` under the `/api` prefix and return ORM rows via Pydantic schemas in `schemas.py`.

Each template under `templates/` is a self-contained page: HTML + inline `<script type="module">` that imports D3 v7 from the jsdelivr CDN and fetches data from the corresponding `/api/...` endpoint. There is no frontend build step and `static/js/` is currently empty — D3 logic lives inside the templates, not in separate JS files.

### Data model

Two ORM models in `models.py`, each backing one chart family:

- `ChartDataPoint` (`chart`, `label`, `value`) — discriminated by the `chart` column (`"bar"`, `"line"`). Served by `/api/charts` and `/api/charts/{name}`.
- `StackedDataPoint` (`group`, `series`, `value`) — one row per (group, series) cell. Served by `/api/stacked`.

When adding a new chart type, the convention is: add a new ORM model, seed it inside `database._seed()` (guarded by an empty-table check), expose a new endpoint in `routers/data.py`, and add a page route in `main.py` + a template that fetches from it.

### telephone_etl.py

Standalone offline script — not imported by the FastAPI app. Calls the Anthropic API (`claude-haiku-4-5-20251001`) to iteratively "improve" an s'mores recipe and writes `telephone_results.json`, which `templates/telephone.html` loads at render time. Requires `ANTHROPIC_API_KEY` and `pip install anthropic` (not in `requirements.txt`). Re-run it manually to regenerate the JSON the page consumes.
