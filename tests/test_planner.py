from app.graph.nodes import planner_node

state = {
    "user_query": "I want a 3 day trip to Goa with budget 20000",
    "destination": "Goa",
    "budget": 20000,
    "days": 3,
    "weather": None,
    "itinerary": "",
    "estimated_cost": 0,
    "recommendations": [],
    "missing_information": [],
    "previous_destination": None,
    "final_response": {}
}

result = planner_node(state)
print(result["itinerary"])
