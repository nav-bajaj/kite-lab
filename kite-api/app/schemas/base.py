"""
Base schemas used across the API.
"""
from pydantic import BaseModel
from typing import Literal


UniverseId = Literal["nse500", "nifty250", "nifty100"]


class UniverseInfo(BaseModel):
    """Universe information."""
    id: UniverseId
    name: str
    description: str
    stocks: int
    risk_profile: str

    class Config:
        from_attributes = True
