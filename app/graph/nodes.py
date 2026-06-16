from app.models.extraction_schema import TripDetails
from app.services.llm import llm
from app.models.models import TravelPlan
from app.tools.tools import weather_tool, hotel_cost_tool, food_cost_tool
from app.services.memory_store import save_destination, load_destination
import re


structured_llm = llm.with_structured_output(TripDetails)


def extract_information(state):
    query = state["user_query"].lower()
    destination = None
    budget = None
    days = None

    day_match = re.search(r"(\d+)\s*day", query)
    if day_match:
        days = int(day_match.group(1))

    numbers = re.findall(r"\d+", query)
    if numbers:
        budget = max([int(x) for x in numbers])

    ignore_words = {
        "i", "want", "to", "travel", "trip",
        "for", "with", "budget", "day", "days"
    }
    words = re.findall(r"[a-zA-Z]+", query)
    for word in words:
        if word not in ignore_words:
            destination = word.title()
            break

    if not destination:
        memory_keywords = ["another", "again", "same", "previous"]
        if any(keyword in query.lower() for keyword in memory_keywords):
            previous = load_destination()
            if previous:
                print(f"\nUsing previous destination: {previous}")
                destination = previous

    missing = []
    if not destination:
        missing.append("destination")
    if not budget:
        missing.append("budget")
    if not days:
        missing.append("days")

    print("\nExtraction Result:")
    print(f"destination={destination} budget={budget} days={days}")

    return {
        **state,
        "destination": destination,
        "budget": budget,
        "days": days,
        "missing_information": missing
    }


def clarification_node(state):
    questions = []
    if "destination" in state["missing_information"]:
        questions.append("Which destination would you like to visit?")
    if "budget" in state["missing_information"]:
        questions.append("What is your budget?")
    if "days" in state["missing_information"]:
        questions.append("How many days will you travel?")

    return {
        **state,
        "final_response": {
            "clarification_needed": questions
        }
    }


def planner_node(state):
    destination = state["destination"]
    days = state["days"]
    trip_type = state.get("trip_type", "budget")
    weather = weather_tool(destination)

    prompt = f"""
    Create a {days}-day travel itinerary for {destination}.

    Trip Type:
    {trip_type}

    Weather:
    {weather}

    IMPORTANT:
    If trip type is budget:
    - Use affordable activities
    - Use public transport
    - Focus on free attractions

    If trip type is luxury:
    - Include premium experiences
    - Include luxury dining
    - Include high-end attractions

    Return plain text only.
    Do NOT use markdown/bullets/symbols.
    Format exactly like:

    Day 1:
    Activity 1
    Activity 2
    """

    response = llm.invoke(prompt)
    return {
        **state,
        "weather": weather,
        "itinerary": response.content
    }


def budget_validation_node(state):
    destination = state["destination"]
    days = state["days"]
    budget = state["budget"]

    hotel_cost = hotel_cost_tool(destination) * days
    food_cost = food_cost_tool(destination) * days
    transport_cost = 3000
    activity_cost = 2000

    if state.get("trip_type") == "luxury":
        hotel_cost *= 2
        food_cost *= 2
        activity_cost *= 2

    total_cost = hotel_cost + food_cost + transport_cost + activity_cost
    
    cost_breakdown = {
        "Hotel": hotel_cost,
        "Food": food_cost,
        "Transport": transport_cost,
        "Activities": activity_cost
    }

    recommendations = []

    if total_cost > budget:
        difference = total_cost - budget
        recommendations.append(f"Your trip exceeds budget by ₹{difference}")
        recommendations.append("Choose budget hotels")
        recommendations.append("Reduce activities")
        recommendations.append("Reduce trip duration")
    else:
        savings = budget - total_cost
        recommendations.append(
            f"Budget is sufficient. You still have ₹{savings} remaining."
        )

    return {
        **state,
        "estimated_cost": total_cost,
        "cost_breakdown": cost_breakdown,
        "recommendations": recommendations
    }


def final_response_node(state):
    response = TravelPlan(
        destination=state["destination"],
        days=state["days"],
        estimated_cost=state["estimated_cost"],
        weather=state["weather"],
        itinerary=state["itinerary"],
        recommendations=state["recommendations"],
        cost_breakdown=state.get("cost_breakdown", {})
    )
    return {
        **state,
        "final_response": response.model_dump()
    }


def route_after_extraction(state):
    if state["missing_information"]:
        return "clarification"
    return "planner"


def hotel_preference_node(state):
    return {
        **state,
        "trip_type": state.get("trip_type", "budget")
    }


def modify_itinerary_node(state):

    modify = state.get(
        "modify",
        False
    )

    modification_request = state.get(
        "modification_request",
        ""
    )

    print("\n===== MODIFY NODE =====")
    print("Modify:", modify)
    print(
        "Modification Request:",
        modification_request
    )

    if modify and modification_request:

        prompt = f"""
        You MUST modify the itinerary.

        Current itinerary:

        {state['itinerary']}

        User request:

        {modification_request}

        Rules:
        1. Apply the requested change.
        2. Keep all days.
        3. Insert the new activity.
        4. Return the COMPLETE updated itinerary.
        5. Do not return the original itinerary unchanged.
        """

        updated = llm.invoke(prompt)

        print("ITINERARY MODIFIED")

        return {
            **state,
            "itinerary": updated.content
        }

    print("NO MODIFICATION APPLIED")

    return state


def memory_node(state):
    current_destination = state.get("destination")
    if current_destination:
        save_destination(current_destination)
    return state
