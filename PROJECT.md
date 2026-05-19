# D3 Analytics Portfolio

Interactive data visualisations built with **D3.js v7** and **FastAPI**.

## Project at a Glance

| File / Folder | Purpose |
|---|---|
| `main.py` | FastAPI app entry point; mounts static files, Jinja2 templates, and API router |
| `database.py` | SQLite via SQLAlchemy; creates tables and seeds sample data on first run |
| `models.py` | `ChartDataPoint` ORM model (`chart`, `label`, `value`) |
| `schemas.py` | Pydantic schemas for API input (`DataPointIn`) and output (`DataPointOut`) |
| `routers/data.py` | REST endpoints — `GET /api/charts`, `GET /api/charts/{name}`, `POST /api/charts` |
| `templates/index.html` | Single-page UI with animated D3 bar chart and line chart |
| `static/css/style.css` | Dark-theme styles and D3 element rules |
| `data/portfolio.db` | SQLite database file (auto-created on first run) |

## Stack

- **Backend:** FastAPI + SQLAlchemy (SQLite by default; swap `DATABASE_URL` env var for Postgres)
- **Frontend:** D3.js v7 (CDN ES module), Jinja2 templates
- **Charts:** Animated bar chart (monthly values) and area/line chart (quarterly trend)

## API

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/charts` | List all chart names |
| `GET` | `/api/charts/{name}` | Get data points for a chart |
| `POST` | `/api/charts` | Add a new data point |

Interactive API docs available at [`/docs`](http://localhost:8000/docs).

## Running the App

```bash
cd /Users/nat/Projects/d3-portfolio
source venv/bin/activate
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000).
