import json

from app.agent.llm_service import request_tool_call, generate_final_answer
from app.harness.tool_registry import execute_tool

def run_agent(user_message: str):
    message = request_tool_call(user_message)

    if not message.tool_calls:
        return {
            "type": "text",
            "content": message.content,
        }

    results = []

    for call in message.tool_calls:
        tool_name = call.function.name

        try:
            arguments = json.loads(call.function.arguments)

            if not isinstance(arguments,dict):
                raise ValueError("Arguments must be an object")

        except (json.JSONDecodeError, TypeError, ValueError):
            tool_result = {
                "success": False,
                "error": "invalid_json_arguments",
            }

        else:
            tool_result = execute_tool(
                tool_name,
                arguments,
            )
        results.append(
            {
                "tool_call_id": call.id,
                "tool_name": tool_name,
                "result": tool_result,
            }
        )

    final_answer = generate_final_answer(
        user_message=user_message,
        assistant_message=message,
        tool_results=results,
    )

    return {
        "type": "answer",
        "content": final_answer,
        "tool_results": results,
    }

if __name__ == "__main__":
    result = run_agent(
        "Please check order ORD-1001."
    )

    print(result)
