from typing import TypedDict, NotRequired

from langgraph.graph import StateGraph, START, END


# 1. Define shared state.
class SupportState(TypedDict):
    user_message: str
    intent: NotRequired[str]
    reply: NotRequired[str]

# 2. Classify user intent.
def classify_intent(state: SupportState) -> dict:
    message = state["user_message"].lower()

    if "shipping" in message or "tracking" in message:
        intent = "shipping"

    elif "order" in message:
        intent = "order"

    else:
        intent = "general"

    return {"intent": intent}

# 3. Define response nodes.
def handle_order(state: SupportState) -> dict:
    return {
        "reply": "Order request detected."
                 "Order lookup is not connected yet."
    }

def handle_shipping(state: SupportState) -> dict:
    return {
        "reply": "Shipping request detected."
                 "Shipping lookup is not connected yet."
    }

def handle_general(state: SupportState) -> dict:
    return {
        "reply": "General customer support request detected."
    }

# 4. Route to the appropriate node.
def route_intent(state: SupportState) -> str:
    return state["intent"]

# 5. Build the graph.
builder = StateGraph(SupportState)

builder.add_node("classify", classify_intent)
builder.add_node("order", handle_order)
builder.add_node("shipping", handle_shipping)
builder.add_node("general", handle_general)

builder.add_edge(START, "classify")

builder.add_conditional_edges(
    "classify",
    route_intent,
    {
        "order": "order",
        "shipping": "shipping",
        "general": "general",
    },
)

builder.add_edge("order", END)
builder.add_edge("shipping", END)
builder.add_edge("general", END)

# 6. Compile into an executable graph.
graph = builder.compile()