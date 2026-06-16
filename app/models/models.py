from pydantic import BaseModel
from typing import List


class TravelPlan(BaseModel):
    destination: str
    days: int
    estimated_cost: int
    weather: str
    itinerary: str
    recommendations: List[str]
    cost_breakdown: dict = {}
