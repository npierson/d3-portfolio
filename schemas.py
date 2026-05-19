"""
Pydantic schemas – what the API sends and receives.
"""
from pydantic import BaseModel


class DataPointOut(BaseModel):
    id:    int
    chart: str
    label: str
    value: float

    model_config = {"from_attributes": True}


class DataPointIn(BaseModel):
    chart: str
    label: str
    value: float


class StackedPointOut(BaseModel):
    id:     int
    group:  str
    series: str
    value:  float

    model_config = {"from_attributes": True}
