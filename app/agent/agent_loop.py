
import json

from app.agent.llm_service import request_agent_step
from app.harness.tool_registry import execute_tool


MAX_STEPS = 4
MAX_TOOL_CALLS = 6

def run_agent_loop(user_message: str) -> dict:
    messages = [
        {
            "role": "system",
            "content": (
                "You are an e-commerce support assistant. "
                "Use tools to obtain order and shipping information. "
                "For conditional requests, check the necessary "
                "order information before deciding the next action. "
                "Never invent order or shipping details."
            ),
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

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


if __name__ == "__main__":
    result = run_agent_loop(
        "请帮我查询订单 e481f51cbdc54678b7cc49136f2d6af7。"
        "告诉我订单状态和金额。"
        "如果没有物流记录，请明确说明没有物流详情，"
        "不要编造承运商和运单号。"
    )

    print("Final result:", result["content"])
    print("Tool history:", result["tool_results"])