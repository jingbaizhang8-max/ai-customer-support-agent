import os
import json
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url=os.getenv(
        "DEEPSEEK_BASE_URL",
        "https://api.deepseek.com"
    ),
)

GET_ORDER_TOOL = {
    "type": "function",
    "function": {
        "name": "get_order",
        "description": "Look up an order by its order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "Order ID such as ORD-1001",
                }
            },
            "required": ["order_id"],
        },
    },
}

def request_tool_call(user_message: str):
    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an e-commerce support assistant. "
                    "Use get_order when a customer asks about an order. "
                    "Never invent order or shipping details."
                ),
            },
            {
                "role": "user",
                "content": user_message,
            },
        ],
        tools=[GET_ORDER_TOOL],
        tool_choice="auto",
    )

    return response.choices[0].message

def generate_final_answer(
        user_message: str,
        assistant_message,
        tool_results: list[dict],
) -> str:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an e-commerce support assistant. "
                "Answer using only the provided tool results. "
                "Never invent order or shipping information. "
                "If a tool returns an error, explain it clearly."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
        assistant_message.model_dump(exclude_none=True),
    ]

    for item in tool_results:
        messages.append(
            {
                "role": "tool",
                "tool_call_id": item["tool_call_id"],
                "content": json.dumps(item["result"]),
            }
        )

    response = client.chat.completions.create(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-flash"),
        messages=messages,
    )

    return response.choices[0].message.content or ""

if __name__ == "__main__":
    message = request_tool_call(
        "Please check the shipping status of order ORD-1001."
    )

    if message.tool_calls:
        for call in message.tool_calls:
            print("Tool name:", call.function.name)
            print("Arguments:", call.function.arguments)
    else:
        print("Model response:", message.content)