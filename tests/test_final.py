from app.graph.nodes import final_response_node

state = {
    "destination": "Goa",
    "days": 3,
    "estimated_cost": 15500,
    "weather": "Sunny, 30°C",
    "itinerary": "Day 1 Beach\nDay 2 Water Sports\nDay 3 Shopping",
    "recommendations": ["Budget is sufficient"]
}

result = final_response_node(state)
print(result["final_response"])
