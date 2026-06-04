from app.graph.nodes import budget_validation_node

state = {
    "destination": "Goa",
    "budget": 20000,
    "days": 3,
    "itinerary": ""
}

result = budget_validation_node(state)
print("Estimated Cost:")
print(result["estimated_cost"])

print("\nRecommendations:")
print(result["recommendations"])
