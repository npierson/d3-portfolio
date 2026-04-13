"""
D3 Portfolio – FastAPI entry point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from contextlib import asynccontextmanager

from database import init_db
from routers import data


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database on startup."""
    init_db()
    yield


app = FastAPI(
    title="D3 Analytics Portfolio",
    description="A portfolio of interactive D3.js visualisations powered by FastAPI.",
    version="0.1.0",
    lifespan=lifespan,
)

# Static files (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates
templates = Jinja2Templates(directory="templates")

# API routes
app.include_router(data.router, prefix="/api", tags=["data"])


@app.get("/", include_in_schema=False)
async def index(request: Request):
    """Serve the portfolio home page."""
    return templates.TemplateResponse("index.html", {"request": request})
