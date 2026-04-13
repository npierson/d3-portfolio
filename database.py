"""
Database setup – SQLite via SQLAlchemy.
Swap DATABASE_URL for a Postgres URL in production with zero code changes.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Local SQLite by default; override via environment variable for Postgres:
#   export DATABASE_URL="postgresql+psycopg2://user:pass@host/dbname"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/portfolio.db")

# SQLite needs check_same_thread=False; ignored by other dialects
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables if they don't exist, and seed sample data."""
    from models import ChartDataPoint  # avoid circular import at module level
    Base.metadata.create_all(bind=engine)
    _seed()


def get_db():
    """FastAPI dependency – yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed():
    """Insert sample data only when the table is empty."""
    from models import ChartDataPoint
    db = SessionLocal()
    try:
        if db.query(ChartDataPoint).count() == 0:
            samples = [
                ChartDataPoint(chart="bar", label="January",  value=42),
                ChartDataPoint(chart="bar", label="February", value=67),
                ChartDataPoint(chart="bar", label="March",    value=53),
                ChartDataPoint(chart="bar", label="April",    value=89),
                ChartDataPoint(chart="bar", label="May",      value=74),
                ChartDataPoint(chart="bar", label="June",     value=95),
                ChartDataPoint(chart="line", label="Q1", value=120),
                ChartDataPoint(chart="line", label="Q2", value=145),
                ChartDataPoint(chart="line", label="Q3", value=132),
                ChartDataPoint(chart="line", label="Q4", value=178),
            ]
            db.add_all(samples)
            db.commit()
    finally:
        db.close()
