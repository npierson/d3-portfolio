"""
SQLAlchemy ORM models.
"""
from sqlalchemy import Column, Integer, String, Float
from database import Base


class ChartDataPoint(Base):
    """A single data point belonging to a named chart."""
    __tablename__ = "chart_data"

    id      = Column(Integer, primary_key=True, index=True)
    chart   = Column(String, index=True, nullable=False)  # e.g. "bar", "line"
    label   = Column(String, nullable=False)              # x-axis label
    value   = Column(Float,  nullable=False)              # y-axis value
