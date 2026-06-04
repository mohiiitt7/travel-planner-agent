from graph import graph
from services.pdf_export import export_pdf #ignore

query = input(
    "Enter your travel request: "
).strip()

if not query:
    print(
        "Please enter a valid travel request."
    )
    exit()

state = {
    "user_query": query,

    "destination": None,
    "budget": None,
    "days": None,

    "trip_type": None,

    "weather": None,

    "itinerary": "",

    "estimated_cost": 0,

    "recommendations": [],

    "missing_information": [],

    "previous_destination": None,

    "final_response": {}
}

config = {
    "configurable": {
        "thread_id": "user-1"
    }
}

result = graph.invoke(
    state,
    config={
        "configurable": {
            "thread_id": "travel-api"
        }
    }
)

response = result["final_response"]

if "clarification_needed" in response:

    print("\nMore information needed:\n")

    for question in response["clarification_needed"]:
        print(f"• {question}")

else:

    export_pdf(response)

    print(
        "\nPDF generated successfully: "
        "travel_plan.pdf"
    )

    print("\n" + "=" * 60)
    print("AI TRAVEL PLANNER")
    print("=" * 60)

    print(f"\n📍 Destination : {response['destination']}")
    print(f"📅 Days        : {response['days']}")
    print(f"💰 Cost        : ₹{response['estimated_cost']}")

    print("\n🌍 Itinerary")
    print("-" * 60)

    print(response["itinerary"])

    print("\n💡 Recommendations")
    print("-" * 60)

    for rec in response["recommendations"]:
        print(f"• {rec}")