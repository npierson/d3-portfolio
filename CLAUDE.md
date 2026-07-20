# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
source venv/bin/activate
uvicorn main:app --reload
```

Server runs at http://localhost:8000. Swagger UI at `/docs`. SQLite DB is created and seeded on first startup at `data/portfolio.db` — delete that file to reseed.

To use Postgres instead: `export DATABASE_URL="postgresql+psycopg2://..."` before launching. No code change needed.

**Snowflake** is supported via key-pair (JWT) auth and is selected automatically when `SNOWFLAKE_ACCOUNT` is set. `database.py` reads the connection params (`SNOWFLAKE_ACCOUNT`, `_USER`, `_WAREHOUSE`, `_DATABASE`, `_SCHEMA`, `_ROLE`) from env vars / `.env`, loads the RSA private key from `snowflake_key.p8`, converts it to DER, and passes it to the connector via `connect_args` (the key can't live in the URL string). Backend precedence in `database.py`: **Snowflake** (if `SNOWFLAKE_ACCOUNT` set) → **`DATABASE_URL`** → **SQLite** default — so commenting out `SNOWFLAKE_ACCOUNT` in `.env` falls back to local SQLite with zero code change. Requires `snowflake-sqlalchemy` + `python-dotenv` (both in `requirements.txt`, unlike the ETL-script deps). Register the public key on the Snowflake side once with `ALTER USER <user> SET RSA_PUBLIC_KEY='<body of snowflake_key.pub, no header/newlines>'` (needs SECURITYADMIN/ACCOUNTADMIN); verify with `DESC USER <user>` — the `RSA_PUBLIC_KEY_FP` must match `SHA256:` + `openssl rsa -pubin -in snowflake_key.pub -outform DER | openssl dgst -sha256 -binary | openssl enc -base64`. **Secrets are gitignored:** `snowflake_key.p8`, `snowflake_key.pub`, and `.env` — never commit them.

Two Snowflake-specific gotchas the code already handles, worth knowing if you touch `database.py`: (1) Snowflake has **no traditional indexes**, so `init_db()` clears `table.indexes` before `create_all` when on Snowflake (primary keys are unaffected). (2) Snowflake **doesn't return autoincrement PKs** to SQLAlchemy's ORM identity map, which raises `FlushError: NULL identity key` on `add_all` — so `_seed()`/`_seed_inflation()` seed via **Core bulk inserts** (`db.execute(insert(Model), [dicts])`), letting Snowflake generate the id. Use that pattern for any new seeding that must run on Snowflake.

**Dependency versions matter.** If you `pip install` packages ad hoc instead of `pip install -r requirements.txt`, you can end up with a `fastapi`/`starlette` newer than the pinned `jinja2==3.1.4` expects, which throws `TypeError: unhashable type: 'dict'` inside `Jinja2Templates.TemplateResponse` on every page route (not just new ones — it breaks `/` too). If page routes 500 with that error, reinstall from `requirements.txt` exactly.

## Architecture

FastAPI app with two distinct response surfaces backed by one SQLAlchemy store (SQLite by default; Postgres via `DATABASE_URL` or Snowflake via `SNOWFLAKE_ACCOUNT` — see "Running the app"):

- **Page routes** live directly on the app in `main.py` (`/`, `/stacked`, `/telephone`, `/inflation`) and render Jinja2 templates from `templates/`.
- **JSON API routes** live in `routers/data.py` under the `/api` prefix and return ORM rows via Pydantic schemas in `schemas.py`.

Each template under `templates/` is a self-contained page: HTML + inline `<script type="module">` that imports D3 v7 from the jsdelivr CDN and fetches data from the corresponding `/api/...` endpoint. There is no frontend build step and `static/js/` is currently empty — D3 logic lives inside the templates, not in separate JS files.

Page routes aren't cross-linked in a shared nav — `index.html` only links to itself plus a card for `/inflation`. `/stacked` and `/telephone` are reachable only by typing the URL. Keep that in mind if you add a page and expect it to be discoverable from `/`.

### Data model

Three ORM models in `models.py`, each backing one chart family:

- `ChartDataPoint` (`chart`, `label`, `value`) — discriminated by the `chart` column. Values in use: `"bar"`, `"line"` (synthetic demo data), and `"unemployment"` (real BLS unemployment rate, seeded from `inflation_data.json`). Served by `/api/charts` and `/api/charts/{name}`.
- `StackedDataPoint` (`group`, `series`, `value`) — one row per (group, series) cell. Served by `/api/stacked`.
- `InflationDataPoint` (`category`, `month`, `yoy_pct`) — one row per (CPI category, month), year-over-year % change. Served by `/api/inflation`.

When adding a new chart type, the convention is: add a new ORM model, seed it inside `database._seed()` (guarded by an empty-table check; use Core bulk inserts — `db.execute(insert(Model), [dicts])` — not ORM `add_all`, so seeding works on Snowflake too), expose a new endpoint in `routers/data.py`, and add a page route in `main.py` + a template that fetches from it. `InflationDataPoint` deviates slightly: its seeding is a separate `database._seed_inflation()` call (also empty-table guarded, invoked right after `_seed()` in `init_db()`) because it reads from a checked-in JSON file rather than inline Python literals — follow that split if a new chart type is also backed by an offline data-fetch script rather than hardcoded samples.

### telephone_etl.py

Standalone offline script — not imported by the FastAPI app. Calls the Anthropic API (`claude-haiku-4-5-20251001`) to iteratively "improve" an s'mores recipe and writes `telephone_results.json`, which `templates/telephone.html` loads at render time. Requires `ANTHROPIC_API_KEY` and `pip install anthropic` (not in `requirements.txt`). Re-run it manually to regenerate the JSON the page consumes.

### inflation_etl.py

Standalone offline script — not imported by the FastAPI app. Fetches real BLS Consumer Price Index category data (All Items, Shelter, Food, Energy, Medical Care, Transportation) plus the unemployment rate from FRED's public CSV export (`fred.stlouisfed.org/graph/fredgraph.csv`, no API key needed), computes year-over-year % change per category, and writes `inflation_data.json`. Requires `pip install requests` (not in `requirements.txt`). `database._seed_inflation()` loads that JSON into the `InflationDataPoint` table (and an `unemployment` `ChartDataPoint` series) once per fresh DB — delete `data/portfolio.db` and re-run `inflation_etl.py` to refresh with current data. Served at `/api/inflation` and rendered at `/inflation` (`templates/inflation.html`).

Known data quirk: FRED occasionally reports a month as `.` (not yet published at fetch time — this happened for 2025-10 across several series in the current `inflation_data.json`). Both the seed data and `inflation_etl.py` linearly interpolate those gaps from the neighboring months rather than dropping them, so every month in the YoY window has a value.
