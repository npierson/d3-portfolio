"""
Database setup – SQLite by default; Snowflake (key-pair auth) when configured.

Backends, in priority order:
  1. Snowflake  – active when SNOWFLAKE_ACCOUNT is set. Authenticates with an
     RSA key pair (no password); connection params come from env vars / .env.
  2. DATABASE_URL – any SQLAlchemy URL (e.g. Postgres). Zero code changes.
  3. SQLite     – the local default (data/portfolio.db).
"""
import os
import json
from sqlalchemy import create_engine, insert
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Load .env (Snowflake config + private-key path) if python-dotenv is installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

USE_SNOWFLAKE = bool(os.getenv("SNOWFLAKE_ACCOUNT"))


def _snowflake_engine():
    """Build a Snowflake engine using key-pair (JWT) auth.

    The private key can't travel in the URL, so it's loaded from disk, converted
    to DER, and handed to the connector via connect_args. Set the passphrase env
    var only if the .p8 file was created with one (ours is unencrypted).
    """
    from snowflake.sqlalchemy import URL
    from cryptography.hazmat.primitives import serialization

    key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "snowflake_key.p8")
    passphrase = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE")
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=passphrase.encode() if passphrase else None,
        )
    pkb = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    url = URL(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    return create_engine(url, connect_args={"private_key": pkb})


if USE_SNOWFLAKE:
    engine = _snowflake_engine()
else:
    # Local SQLite by default; override via DATABASE_URL for Postgres etc:
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
    if USE_SNOWFLAKE:
        # Snowflake has no traditional indexes; drop the index=True objects so
        # create_all won't emit CREATE INDEX (primary keys are unaffected).
        for table in Base.metadata.tables.values():
            table.indexes.clear()
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
    """Insert sample data only when the table is empty.

    Uses Core bulk inserts (not ORM add_all) so the DB generates the autoincrement
    id without SQLAlchemy trying to read it back — Snowflake doesn't return
    generated keys, which breaks the ORM identity map. Works the same on SQLite.
    """
    from models import ChartDataPoint, StackedDataPoint
    db = SessionLocal()
    try:
        if db.query(ChartDataPoint).count() == 0:
            samples = [
                {"chart": "bar",  "label": "January",  "value": 42},
                {"chart": "bar",  "label": "February", "value": 67},
                {"chart": "bar",  "label": "March",    "value": 53},
                {"chart": "bar",  "label": "April",    "value": 89},
                {"chart": "bar",  "label": "May",      "value": 74},
                {"chart": "bar",  "label": "June",     "value": 95},
                {"chart": "line", "label": "Q1", "value": 120},
                {"chart": "line", "label": "Q2", "value": 145},
                {"chart": "line", "label": "Q3", "value": 132},
                {"chart": "line", "label": "Q4", "value": 178},
            ]
            db.execute(insert(ChartDataPoint), samples)
            db.commit()

        if db.query(StackedDataPoint).count() == 0:
            # Regional sales ($k) by product category — 5 regions × 4 categories
            stacked_samples = [
                # Electronics
                {"group": "North",   "series": "Electronics", "value": 120},
                {"group": "South",   "series": "Electronics", "value": 95},
                {"group": "East",    "series": "Electronics", "value": 140},
                {"group": "West",    "series": "Electronics", "value": 108},
                {"group": "Central", "series": "Electronics", "value": 87},
                # Clothing
                {"group": "North",   "series": "Clothing", "value": 75},
                {"group": "South",   "series": "Clothing", "value": 88},
                {"group": "East",    "series": "Clothing", "value": 62},
                {"group": "West",    "series": "Clothing", "value": 95},
                {"group": "Central", "series": "Clothing", "value": 70},
                # Food
                {"group": "North",   "series": "Food", "value": 55},
                {"group": "South",   "series": "Food", "value": 72},
                {"group": "East",    "series": "Food", "value": 49},
                {"group": "West",    "series": "Food", "value": 61},
                {"group": "Central", "series": "Food", "value": 80},
                # Furniture
                {"group": "North",   "series": "Furniture", "value": 40},
                {"group": "South",   "series": "Furniture", "value": 33},
                {"group": "East",    "series": "Furniture", "value": 58},
                {"group": "West",    "series": "Furniture", "value": 45},
                {"group": "Central", "series": "Furniture", "value": 29},
            ]
            db.execute(insert(StackedDataPoint), stacked_samples)
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
                {
                    "category": row["category"],
                    "month": row["month"],
                    "yoy_pct": row["yoy_pct"],
                }
                for row in payload.get("inflation", [])
            ]
            if inflation_rows:
                db.execute(insert(InflationDataPoint), inflation_rows)

            unemployment_rows = [
                {"chart": "unemployment", "label": row["month"], "value": row["rate"]}
                for row in payload.get("unemployment", [])
            ]
            if unemployment_rows:
                db.execute(insert(ChartDataPoint), unemployment_rows)

            db.commit()
    finally:
        db.close()
