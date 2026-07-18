# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate
uvicorn main:app --reload
```

Server runs at http://localhost:8000. Swagger UI at `/docs`. SQLite DB is created and seeded on first startup at `data/portfolio.db` — delete that file to reseed.

To use Postgres instead: `export DATABASE_URL="postgresql+psycopg2://..."` before launching. No code change needed (`database.py:11`).

**Dependency versions matter.** If you `pip install` packages ad hoc instead of `pip install -r requirements.txt`, you can end up with a `fastapi`/`starlette` newer than the pinned `jinja2==3.1.4` expects, which throws `TypeError: unhashable type: 'dict'` inside `Jinja2Templates.TemplateResponse` on every page route (not just new ones — it breaks `/` too). If page routes 500 with that error, reinstall from `requirements.txt` exactly.

## Architecture

FastAPI app with two distinct response surfaces backed by one SQLAlchemy/SQLite store:

- **Page routes** live directly on the app in `main.py` (`/`, `/stacked`, `/telephone`, `/inflation`) and render Jinja2 templates from `templates/`.
- **JSON API routes** live in `routers/data.py` under the `/api` prefix and return ORM rows via Pydantic schemas in `schemas.py`.

Each template under `templates/` is a self-contained page: HTML + inline `<script type="module">` that imports D3 v7 from the jsdelivr CDN and fetches data from the corresponding `/api/...` endpoint. There is no frontend build step and `static/js/` is currently empty — D3 logic lives inside the templates, not in separate JS files.

Page routes aren't cross-linked in a shared nav — `index.html` only links to itself plus a card for `/inflation`. `/stacked` and `/telephone` are reachable only by typing the URL. Keep that in mind if you add a page and expect it to be discoverable from `/`.

### Data model

Three ORM models in `models.py`, each backing one chart family:

- `ChartDataPoint` (`chart`, `label`, `value`) — discriminated by the `chart` column. Values in use: `"bar"`, `"line"` (synthetic demo data), and `"unemployment"` (real BLS unemployment rate, seeded from `inflation_data.json`). Served by `/api/charts` and `/api/charts/{name}`.
- `StackedDataPoint` (`group`, `series`, `value`) — one row per (group, series) cell. Served by `/api/stacked`.
- `InflationDataPoint` (`category`, `month`, `yoy_pct`) — one row per (CPI category, month), year-over-year % change. Served by `/api/inflation`.

When adding a new chart type, the convention is: add a new ORM model, seed it inside `database._seed()` (guarded by an empty-table check), expose a new endpoint in `routers/data.py`, and add a page route in `main.py` + a template that fetches from it. `InflationDataPoint` deviates slightly: its seeding is a separate `database._seed_inflation()` call (also empty-table guarded, invoked right after `_seed()` in `init_db()`) because it reads from a checked-in JSON file rather than inline Python literals — follow that split if a new chart type is also backed by an offline data-fetch script rather than hardcoded samples.

### telephone_etl.py

Standalone offline script — not imported by the FastAPI app. Calls the Anthropic API (`claude-haiku-4-5-20251001`) to iteratively "improve" an s'mores recipe and writes `telephone_results.json`, which `templates/telephone.html` loads at render time. Requires `ANTHROPIC_API_KEY` and `pip install anthropic` (not in `requirements.txt`). Re-run it manually to regenerate the JSON the page consumes.

### inflation_etl.py

Standalone offline script — not imported by the FastAPI app. Fetches real BLS Consumer Price Index category data (All Items, Shelter, Food, Energy, Medical Care, Transportation) plus the unemployment rate from FRED's public CSV export (`fred.stlouisfed.org/graph/fredgraph.csv`, no API key needed), computes year-over-year % change per category, and writes `inflation_data.json`. Requires `pip install requests` (not in `requirements.txt`). `database._seed_inflation()` loads that JSON into the `InflationDataPoint` table (and an `unemployment` `ChartDataPoint` series) once per fresh DB — delete `data/portfolio.db` and re-run `inflation_etl.py` to refresh with current data. Served at `/api/inflation` and rendered at `/inflation` (`templates/inflation.html`).

Known data quirk: FRED occasionally reports a month as `.` (not yet published at fetch time — this happened for 2025-10 across several series in the current `inflation_data.json`). Both the seed data and `inflation_etl.py` linearly interpolate those gaps from the neighboring months rather than dropping them, so every month in the YoY window has a value.
