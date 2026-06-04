from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from app.graph.state import TravelState
from app.graph.nodes import (
    extract_information,
    clarification_node,
    planner_node,
    budget_validation_node,
    final_response_node,
    route_after_extraction,
    memory_node,
    hotel_preference_node,
    modify_itinerary_node
)

builder = StateGraph(TravelState)

builder.add_node("extract", extract_information)
builder.add_node("clarification", clarification_node)
builder.add_node("memory", memory_node)
builder.add_node("hotel_preference", hotel_preference_node)
builder.add_node("planner", planner_node)
builder.add_node("budget_validation", budget_validation_node)
builder.add_node("modify_itinerary", modify_itinerary_node)
builder.add_node("final", final_response_node)

builder.set_entry_point("extract")

builder.add_conditional_edges(
    "extract",
    route_after_extraction,
    {
        "clarification": "clarification",
        "planner": "memory"
    }
)

builder.add_edge("memory", "hotel_preference")
builder.add_edge("hotel_preference", "planner")
builder.add_edge("planner", "budget_validation")
builder.add_edge("budget_validation", "modify_itinerary")
builder.add_edge("modify_itinerary", "final")

builder.add_edge("clarification", END)
builder.add_edge("final", END)

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)
