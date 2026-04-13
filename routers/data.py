"""
API routes – serve chart data as JSON for D3 to consume.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import ChartDataPoint
from schemas import DataPointOut, DataPointIn

router = APIRouter()


@router.get("/charts", response_model=List[str])
def list_charts(db: Session = Depends(get_db)):
    """Return the names of all available charts."""
    results = db.query(ChartDataPoint.chart).distinct().all()
    return [r[0] for r in results]


@router.get("/charts/{chart_name}", response_model=List[DataPointOut])
def get_chart_data(chart_name: str, db: Session = Depends(get_db)):
    """Return all data points for a given chart name."""
    points = db.query(ChartDataPoint).filter(ChartDataPoint.chart == chart_name).all()
    if not points:
        raise HTTPException(status_code=404, detail=f"No data found for chart '{chart_name}'")
    return points


@router.post("/charts", response_model=DataPointOut, status_code=201)
def add_data_point(point: DataPointIn, db: Session = Depends(get_db)):
    """Add a new data point (useful for dynamic demos)."""
    db_point = ChartDataPoint(**point.model_dump())
    db.add(db_point)
    db.commit()
    db.refresh(db_point)
    return db_point
