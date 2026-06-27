# D3 Analytics Portfolio

A small portfolio of interactive [D3.js v7](https://d3js.org/) visualisations served by a [FastAPI](https://fastapi.tiangolo.com/) backend. Each page is a self-contained chart that fetches its data from a JSON API backed by a SQLAlchemy/SQLite store.

## Quick start

```bash
source venv/bin/activate          # or: python -m venv venv && pip install -r requirements.txt
uvicorn main:app --reload
```

The server runs at [http://localhost:8000](http://localhost:8000). Interactive API docs (Swagger UI) are at [`/docs`](http://localhost:8000/docs).

On first startup the SQLite database is created and seeded at `data/portfolio.db`. **Delete that file to reseed.**

## Pages

| Route | Description |
|---|---|
| [`/`](http://localhost:8000/) | Home — animated D3 bar chart (monthly values) and line/area chart (quarterly trend) |
| [`/stacked`](http://localhost:8000/stacked) | Stacked ↔ grouped bar chart of regional sales by product category |
| [`/telephone`](http://localhost:8000/telephone) | "AI Echo Chamber" — visualisation of an LLM iteratively rewriting a recipe (see [telephone_etl.py](telephone_etl.py)) |

Each page lives in `templates/` as HTML with an inline `<script type="module">` that imports D3 from the jsdelivr CDN and fetches from the matching `/api/...` endpoint. There is no frontend build step.

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/charts` | List all chart names (`bar`, `line`) |
| `GET` | `/api/charts/{name}` | Data points for a named chart |
| `POST` | `/api/charts` | Add a new data point |
| `GET` | `/api/stacked` | All rows for the stacked/grouped bar chart |

## Architecture

```
main.py            FastAPI app; page routes (/, /stacked, /telephone) + Jinja2 templates
routers/data.py    JSON API routes under the /api prefix
models.py          SQLAlchemy ORM models
schemas.py         Pydantic request/response schemas
database.py        Engine setup + table creation + sample-data seeding
templates/         One self-contained HTML page per chart (D3 lives inline here)
static/            CSS / JS (static/js is currently empty)
telephone_etl.py   Offline script that generates telephone_results.json
data/portfolio.db  SQLite file, auto-created and seeded on first run
```

### Data model

Two ORM models in [models.py](models.py), each backing one chart family:

- **`ChartDataPoint`** (`chart`, `label`, `value`) — discriminated by the `chart` column (`"bar"`, `"line"`). Served by `/api/charts` and `/api/charts/{name}`.
- **`StackedDataPoint`** (`group`, `series`, `value`) — one row per (group, series) cell. Served by `/api/stacked`.

### Adding a new chart type

1. Add a new ORM model in [models.py](models.py).
2. Seed it inside `database._seed()`, guarded by an empty-table check.
3. Expose an endpoint in [routers/data.py](routers/data.py).
4. Add a page route in [main.py](main.py) and a template that fetches from it.

## Using Postgres instead of SQLite

No code change needed — set `DATABASE_URL` before launching:

```bash
export DATABASE_URL="postgresql+psycopg2://user:pass@host/dbname"
uvicorn main:app --reload
```

## telephone_etl.py

A standalone offline script (not imported by the app). It calls the Anthropic API to iteratively "improve" an s'mores recipe and writes `telephone_results.json`, which `templates/telephone.html` loads at render time. Run it manually to regenerate that JSON:

```bash
pip install anthropic            # not in requirements.txt
export ANTHROPIC_API_KEY="sk-..."
python telephone_etl.py
```

## Requirements

Python dependencies are pinned in [requirements.txt](requirements.txt): FastAPI, Uvicorn, SQLAlchemy, Jinja2, and python-multipart. D3 is loaded client-side from a CDN.
