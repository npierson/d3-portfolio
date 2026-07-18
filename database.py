"""
Database setup – SQLite via SQLAlchemy.
Swap DATABASE_URL for a Postgres URL in production with zero code changes.
"""
import os
import json
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
    _seed_inflation()


def get_db():
    """FastAPI dependency – yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed():
    """Insert sample data only when the table is empty."""
    from models import ChartDataPoint, StackedDataPoint
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

        if db.query(StackedDataPoint).count() == 0:
            # Regional sales ($k) by product category — 5 regions × 4 categories
            stacked_samples = [
                # Electronics
                StackedDataPoint(group="North",   series="Electronics", value=120),
                StackedDataPoint(group="South",   series="Electronics", value=95),
                StackedDataPoint(group="East",    series="Electronics", value=140),
                StackedDataPoint(group="West",    series="Electronics", value=108),
                StackedDataPoint(group="Central", series="Electronics", value=87),
                # Clothing
                StackedDataPoint(group="North",   series="Clothing", value=75),
                StackedDataPoint(group="South",   series="Clothing", value=88),
                StackedDataPoint(group="East",    series="Clothing", value=62),
                StackedDataPoint(group="West",    series="Clothing", value=95),
                StackedDataPoint(group="Central", series="Clothing", value=70),
                # Food
                StackedDataPoint(group="North",   series="Food", value=55),
                StackedDataPoint(group="South",   series="Food", value=72),
                StackedDataPoint(group="East",    series="Food", value=49),
                StackedDataPoint(group="West",    series="Food", value=61),
                StackedDataPoint(group="Central", series="Food", value=80),
                # Furniture
                StackedDataPoint(group="North",   series="Furniture", value=40),
                StackedDataPoint(group="South",   series="Furniture", value=33),
                StackedDataPoint(group="East",    series="Furniture", value=58),
                StackedDataPoint(group="West",    series="Furniture", value=45),
                StackedDataPoint(group="Central", series="Furniture", value=29),
            ]
            db.add_all(stacked_samples)
            db.commit()
    finally:
        db.close()


def _seed_inflation():
    """Load inflation_data.json (BLS CPI via FRED, see inflation_etl.py) and seed
    the InflationDataPoint table plus an 'unemployment' ChartDataPoint series.
    Only runs when the tables are empty.
    """
    from models import InflationDataPoint, ChartDataPoint

    json_path = os.path.join(os.path.dirname(__file__), "inflation_data.json")
    if not os.path.exists(json_path):
        return

    db = SessionLocal()
    try:
        if db.query(InflationDataPoint).count() == 0:
            with open(json_path) as f:
                payload = json.load(f)

            inflation_rows = [
                InflationDataPoint(
                    category=row["category"],
                    month=row["month"],
                    yoy_pct=row["yoy_pct"],
                )
                for row in payload.get("inflation", [])
            ]
            db.add_all(inflation_rows)

            unemployment_rows = [
                ChartDataPoint(chart="unemployment", label=row["month"], value=row["rate"])
                for row in payload.get("unemployment", [])
            ]
            db.add_all(unemployment_rows)

            db.commit()
    finally:
        db.close()
