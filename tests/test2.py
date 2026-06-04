from app.graph.nodes import extract_information, clarification_node

state = {
    "user_query": "I want to travel",
    "destination": None,
    "budget": None,
    "days": None,
    "missing_information": [],
    "weather": None,
    "itinerary": "",
    "estimated_cost": 0,
    "recommendations": [],
    "previous_destination": None,
    "final_response": {}
}

result = extract_information(state)
print("After Extraction:")
print(result)

if result["missing_information"]:
    clarification = clarification_node(result)
    print("\nClarification Needed:")
    print(clarification["final_response"])
