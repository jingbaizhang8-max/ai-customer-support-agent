import json

from app.agent.llm_service import request_agent_step
from app.harness.tool_registry import execute_tool


MAX_STEPS = 4
MAX_TOOL_CALLS = 6

def build_initial_messages(user_message: str) -> list[dict]:
    return  [
        {
            "role": "system",
            "content": (
                "You are an e-commerce customer support assistant. "
                "Use tools to obtain order and shipping information. "
                "For conditional requests, check the necessary "
                "order information before deciding the next action. "
                "Never invent order or shipping details. "

                "Use search_refund_policy for return and refund policy questions. "
                "The policy knowledge base contains a fictional demonstration "
                "policy, not official Olist or real merchant rules. "

                "Never use this fictional policy to determine refund "
                "eligibility for real Olist orders. "
                "Never approve, promise, or execute a real refund. "

                "When search_refund_policy returns a result, inspect "
                "data.status, not just the success flag. "
                "Only treat status='retrieved' as a policy answer. "

                "If evidence is insufficient or the RAG service fails, "
                "explain that the policy cannot be confirmed. "
                "Never invent refund conditions, amounts, or deadlines. "

                "When explaining retrieved policy, cite the document source "
                "and clearly state that the policy is fictional. "
            ),

        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

def run_agent_loop(
    user_message: str,
    *,
    authenticated_customer_id: str | None = None,
) -> dict:
    messages = build_initial_messages(user_message)

    tool_history = []
    seen_tool_calls = set()

    for step in range(MAX_STEPS):
        message = request_agent_step(messages)

        messages.append(
            message.model_dump(exclude_none=True)
        )

        if not message.tool_calls:
            return {
                "type": "answer",
                "content": message.content or "",
                "tool_results": tool_history,
            }

        if len(tool_history) + len(message.tool_calls) > MAX_TOOL_CALLS:
            return {
                "type": "tool_limit_reached",
                "content": "Agent stopped: tool call limit reached.",
                "tool_results": tool_history,
            }

        for call in message.tool_calls:
            tool_name = call.function.name

            try:
                arguments = json.loads(
                    call.function.arguments
                )

                if not isinstance(arguments, dict):
                    raise ValueError("Arguments must be an object")

            except (json.JSONDecodeError, TypeError, ValueError):
                result = {
                    "success": False,
                    "error": "invalid_json_arguments",
                }
            else:
                call_signature = (
                    tool_name,
                    json.dumps(arguments, sort_keys=True),
                )

                if call_signature in seen_tool_calls:
                    result = {
                        "success": False,
                        "error": "duplicate_tool_call",
                    }
                else:
                    seen_tool_calls.add(call_signature)

                    result = execute_tool(
                        tool_name,
                        arguments,
                        authenticated_customer_id=authenticated_customer_id,
                    )

            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result),
            })

            tool_history.append({
                "step": step + 1,
                "tool_name": tool_name,
                "result": result,
            })

    return {
        "type": "step_limit_reached",
        "content": "Agent stopped after reaching the step limit.",
        "tool_results": tool_history,
    }



# if __name__ == "__main__":
#     result = run_agent_loop(
#         "According to the fictional demo store's return policy, "
#         "how many calendar days after delivery can a customer "
#         "request a return? Is a refund guaranteed? "
#         "Please cite the source document. "
#         "Clearly state that this fictional policy does not "
#         "apply to real Olist orders."
#     )
#
#     print("Final result:", result["content"])
#     print("Tool history:", result["tool_results"])
if __name__ == "__main__":
    result = run_agent_loop(
        "Please check the status and total amount "
        "of order ORD-1001.",
        authenticated_customer_id=None,
    )

    print("Final result:", result["content"])
    print("Tool history:", result["tool_results"])