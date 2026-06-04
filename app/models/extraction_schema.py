from pydantic import BaseModel
from typing import Optional


class TripDetails(BaseModel):
    destination: Optional[str] = None
    budget: Optional[int] = None
    days: Optional[int] = None
