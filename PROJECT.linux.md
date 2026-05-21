# D3 Analytics Portfolio (Linux)

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

## Prerequisites (Linux)

Python 3.11+ and the `venv` module are required.

Debian / Ubuntu:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

Fedora / RHEL:

```bash
sudo dnf install python3 python3-pip
```

Arch:

```bash
sudo pacman -S python python-pip
```

## First-Time Setup

Run these in order. Each step exists for a reason — skipping any of them will produce one of the failures listed under Troubleshooting.

```bash
cd ~/Projects/d3-portfolio
python3 -m venv .venv              # create the local virtualenv
source .venv/bin/activate          # activate it — prompt should now show (.venv)
pip install -r requirements.txt    # install fastapi, uvicorn, sqlalchemy, jinja2, python-multipart
mkdir -p data                      # SQLite won't auto-create the data/ directory, and Git can't track empty dirs so it isn't in the repo
```

## Migrating From Another Machine (e.g. fresh clone after working on macOS)

If you previously developed on a different machine or OS and just pulled the repo here, **do not reuse any `.venv` that may have come along** — venvs are not portable. Wipe it and start fresh:

```bash
cd ~/Projects/d3-portfolio
deactivate 2>/dev/null   # in case an old venv is somehow active
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p data
```

## Running the App

```bash
cd ~/Projects/d3-portfolio
source .venv/bin/activate
uvicorn main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000). The SQLite DB and sample data are created automatically on first request.

## Troubleshooting

- **`The virtual environment was not created successfully because ensurepip is not available`** — install the `python3-venv` package for your distro (see Prerequisites).
- **`uvicorn: command not found`** — make sure the virtualenv is activated; you should see `(.venv)` in your prompt. Confirm with `which uvicorn` — it should point inside `.venv/bin/`.
- **`ModuleNotFoundError: No module named 'fastapi'` (or similar) even though pip says it's installed** — your `.venv` was likely created on another machine. pip bakes absolute paths into the shebangs of `.venv/bin/*` scripts, so a venv built elsewhere fails to exec and the shell silently falls back to a system-wide `uvicorn` that doesn't see your venv's packages. Fix: follow the "Migrating From Another Machine" steps above.
- **`sqlite3.OperationalError: unable to open database file`** — the `data/` directory doesn't exist. Run `mkdir -p data` from the project root. SQLite won't create the parent directory, and `.gitignore` plus Git's lack of empty-dir tracking means the folder isn't in the repo.
- **Port 8000 already in use** — run `uvicorn main:app --reload --port 8001` or kill the existing process with `lsof -ti:8000 | xargs kill`.
