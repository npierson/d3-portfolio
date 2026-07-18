"""
inflation_etl.py  –  Post-COVID Inflation Dashboard: data refresh
==================================================================
Standalone offline script — not imported by the FastAPI app. Fetches CPI
category indices and the unemployment rate from FRED's public CSV export
(no API key required), computes year-over-year % change for each CPI
category, and writes inflation_data.json, which database._seed() loads on
next startup (only when the inflation_data table is empty — delete
data/portfolio.db to reseed).

Series pulled (U.S. city average, not seasonally adjusted, source: BLS via FRED):
  CPIAUCNS       All Items
  CUUR0000SAH1   Shelter
  CPIUFDNS       Food
  CPIENGNS       Energy
  CPIMEDNS       Medical Care
  CPITRNNS       Transportation
  UNRATE         Unemployment rate (seasonally adjusted, for context)

Usage:
  pip install requests
  python inflation_etl.py

Output:
  inflation_data.json  (consumed by database._seed_inflation())
"""

import csv
import io
import json
import os
from datetime import date

import requests

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

SERIES = {
    "All Items":      "CPIAUCNS",
    "Shelter":        "CUUR0000SAH1",
    "Food":           "CPIUFDNS",
    "Energy":         "CPIENGNS",
    "Medical Care":   "CPIMEDNS",
    "Transportation": "CPITRNNS",
}

UNEMPLOYMENT_SERIES_ID = "UNRATE"

# How far back to compute year-over-year change from.
YOY_START_YEAR = 2020
YOY_START_MONTH = 1

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; d3-portfolio-etl/1.0)"}


def fetch_series(series_id: str) -> dict:
    """Download a FRED series as {"YYYY-MM": float value}, skipping missing ('.') points."""
    url = FRED_CSV_URL.format(series_id=series_id)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    reader = csv.reader(io.StringIO(resp.text))
    header = next(reader)  # ["DATE", series_id] or ["observation_date", series_id]

    out = {}
    for row in reader:
        if len(row) < 2:
            continue
        raw_date, raw_val = row[0], row[1]
        if raw_val in (".", "", None):
            continue
        month_key = raw_date[:7]  # "YYYY-MM-DD" -> "YYYY-MM"
        out[month_key] = float(raw_val)

    return out


def month_key(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def next_month(year: int, month: int) -> tuple:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def months_from(start_year: int, start_month: int, end_year: int, end_month: int) -> list:
    out = []
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        out.append(month_key(y, m))
        y, m = next_month(y, m)
    return out


def interpolate_missing(series: dict, all_months: list) -> dict:
    """Linearly interpolate any month missing from `series` using neighboring months."""
    filled = dict(series)
    for i, m in enumerate(all_months):
        if m in filled:
            continue
        prev_val = next(
            (filled[all_months[j]] for j in range(i - 1, -1, -1) if all_months[j] in filled),
            None,
        )
        next_val = next(
            (filled[all_months[j]] for j in range(i + 1, len(all_months)) if all_months[j] in filled),
            None,
        )
        if prev_val is not None and next_val is not None:
            filled[m] = round((prev_val + next_val) / 2, 3)
    return filled


def run_pipeline() -> dict:
    today = date.today()
    all_months = months_from(YOY_START_YEAR - 1, YOY_START_MONTH, today.year, today.month)
    yoy_months = months_from(YOY_START_YEAR, YOY_START_MONTH, today.year, today.month)

    print("Fetching CPI category series from FRED…")
    category_series = {}
    for category, series_id in SERIES.items():
        print(f"  {category} ({series_id})…")
        raw = fetch_series(series_id)
        category_series[category] = interpolate_missing(raw, all_months)

    print(f"Fetching unemployment rate ({UNEMPLOYMENT_SERIES_ID})…")
    unemployment_raw = fetch_series(UNEMPLOYMENT_SERIES_ID)
    unemployment_filled = interpolate_missing(unemployment_raw, all_months)

    print("Computing year-over-year % change…")
    records = []
    for category, series in category_series.items():
        for m in yoy_months:
            year, month = int(m[:4]), int(m[5:7])
            prev_key = month_key(year - 1, month)
            if m not in series or prev_key not in series:
                continue
            yoy = round((series[m] / series[prev_key] - 1.0) * 100, 2)
            records.append({"month": m, "category": category, "yoy_pct": yoy})

    unemployment = [
        {"month": m, "rate": unemployment_filled[m]}
        for m in yoy_months
        if m in unemployment_filled
    ]

    out = {
        "source": "U.S. Bureau of Labor Statistics via FRED (fred.stlouisfed.org)",
        "generated": today.isoformat(),
        "note": "Any month FRED reported as '.' (not yet available at fetch time) was linearly interpolated.",
        "categories": list(SERIES.keys()),
        "inflation": records,
        "unemployment": unemployment,
    }

    out_path = os.path.join(os.path.dirname(__file__), "inflation_data.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"✓  Wrote {len(records)} inflation records and {len(unemployment)} unemployment "
          f"records to {out_path}")
    print("  Delete data/portfolio.db and restart the app to reseed with the refreshed data.")
    return out


if __name__ == "__main__":
    run_pipeline()
