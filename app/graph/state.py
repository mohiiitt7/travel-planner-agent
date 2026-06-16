from typing import TypedDict, Optional, List


class TravelState(TypedDict):
    user_query: str
    destination: Optional[str]
    budget: Optional[int]
    days: Optional[int]
    trip_type: Optional[str]
    weather: Optional[str]
    itinerary: str
    estimated_cost: int
    cost_breakdown: dict
    recommendations: List[str]
    missing_information: List[str]
    previous_destination: Optional[str]
    final_response: dict
    modify: bool
    modification_request: str
