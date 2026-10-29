from openai import OpenAIError

import json
from typing import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from uuid import UUID

from sqlalchemy.orm import raiseload

from app.agent.llm_service import request_agent_step
from app.agent.agent_loop import (
    MAX_STEPS,
    MAX_TOOL_CALLS,
    build_initial_messages,
)
from app.harness.tool_registry import execute_tool
from app.agent.context_manager import (
    build_budgeted_context,
    estimate_tokens,
)


class AgentState(TypedDict):
    messages: list[dict]
    authenticated_customer_id: str | None
    tool_history: list[dict]
    seen_tool_calls: list[str]
    steps: int
    result: dict | None
    pending_calls: list[dict]

def finish(state, result_type, content):
    return {
        "result": {
            "type": result_type,
            "content": content,
            "tool_results": state["tool_history"],
        }
    }

def llm_node(state: AgentState) -> dict:
    try:
        model_messages = build_budgeted_context(
            state["messages"],
            max_turns = 4,
            max_context_tokens=8000,
            reserved_output_tokens=1500,
            reserved_tool_tokens=1500,
        )

    except ValueError as exc:
        if str(exc) == "current_turn_exceeds_budget":
            return finish(
                state,
                "context_limit_error",
                "当前上下文过长，请缩短问题后重试",
            )
        raise

    print("完整历史消息数：", len(state["messages"]))
    print("发送给模型的消息数：", len(model_messages))
    print("估算 Token 数：", estimate_tokens(model_messages))

    try:
        message = request_agent_step(model_messages)
    except OpenAIError:

        return {
            "pending_calls": [],
            **finish(
                state,
                "llm_service_error",
                "LLM service is temporarily unavailable.",
            ),
        }
    messages = state["messages"] + [
        message.model_dump(exclude_none=True)
    ]

    steps = state["steps"] + 1

    if not message.tool_calls:
        return {
            "messages": messages,
            "steps": steps,
            "pending_calls": [],
            **finish(state, "answer", message.content or ""),
        }

    if (
            len(state["tool_history"]) + len(message.tool_calls)
            > MAX_TOOL_CALLS
    ):
        # Reject the entire batch without executing any tools.
        error_result = {
            "success": False,
            "error": "tool_limit_reached",
        }

        # Keep every assistant tool call paired with a tool response.
        for call in message.tool_calls:
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(error_result),
            })

        return {
            "messages": messages,
            "steps": steps,
            "pending_calls": [],
            **finish(
                state,
                "tool_limit_reached",
                "Agent stopped: tool call limit reached.",
            ),
        }

    pending_calls = [
        {
            "id": call.id,
            "name": call.function.name,
            "arguments": call.function.arguments,
        }
        for call in message.tool_calls
    ]

    return {
        "messages": messages,
        "steps": steps,
        "pending_calls": pending_calls
    }

def tool_node(state: AgentState) -> dict:
    messages = list(state["messages"])
    history = list(state["tool_history"])
    seen = list(state["seen_tool_calls"])

    for call in state["pending_calls"]:
        name = call["name"]

        try:
            arguments = json.loads(call["arguments"])

            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be an object")

        except (json.JSONDecodeError, TypeError, ValueError):
            result = {
                "success": False,
                "error": "invalid_json_arguments",
            }

        else:
            signature = json.dumps(
                [name, arguments],
                sort_keys=True,
            )

            if signature in seen:
                result= {
                    "success": False,
                    "error": "duplicate_tool_call",
                }
            else:
                seen.append(signature)

                result = execute_tool(
                    name,
                    arguments,
                    authenticated_customer_id=state["authenticated_customer_id"],
                )

        messages.append({
            "role": "tool",
            "tool_call_id": call["id"],
            "content": json.dumps(result),
        })

        history.append({
            "step": state["steps"],
            "tool_name": name,
            "result": result,
        })

    return {
        "messages": messages,
        "tool_history": history,
        "seen_tool_calls": seen,
        "pending_calls": [],
    }

def route_after_llm(state: AgentState) -> str:
    if state["result"] is not None:
        return "end"
    if state["pending_calls"]:
        return "tools"

    return "end"


def limit_node(state: AgentState) -> dict:
    return finish(
        state,
        "step_limit_reached",
        "Agent stopped after reaching the step limit.",
    )


def route_after_tools(state: AgentState) -> str:
    if state["steps"] >= MAX_STEPS:
        return "limit"

    return "llm"

builder = StateGraph(AgentState)

builder.add_node("llm", llm_node)
builder.add_node("tools", tool_node)
builder.add_node("limit", limit_node)

builder.add_edge(START, "llm")

builder.add_conditional_edges(
    "llm",
    route_after_llm,
    {
        "tools": "tools",
        "end": END,
    },
)

builder.add_conditional_edges(
    "tools",
    route_after_tools,
    {
        "llm": "llm",
        "limit": "limit",
    },
)

builder.add_edge("limit", END)

agent_graph = builder.compile()

memory_agent_graph = builder.compile(
    checkpointer=InMemorySaver()
)

def run_graph_agent(
    user_message: str,
    *,
    authenticated_customer_id: str | None = None,
    conversation_id: str | None = None,
) -> dict:

    if (
        not isinstance(user_message, str)
        or not user_message.strip()
    ):
        raise ValueError("invalid_user_message")

    use_memory = conversation_id is not None

    config = None

    if use_memory:
        if not authenticated_customer_id:
            raise ValueError("authentication_required")

        try:
            conversation_id = str(UUID(conversation_id))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("invalid_conversation_id")

        thread_id = (
            f"customer:{authenticated_customer_id}"
            f":conversation:{conversation_id}"
        )

        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        snapshot = memory_agent_graph.get_state(config)

        previous_messages = (
            snapshot.values.get("messages", [])
            if snapshot is not None
            else []
        )

        if previous_messages:
            messages = list(previous_messages) + [
                {
                    "role": "user",
                    "content": user_message,
                }
            ]
        else:
            messages = build_initial_messages(user_message)

    else:
        messages = build_initial_messages(user_message)



    initial_state: AgentState = {
        "messages": messages,
        "authenticated_customer_id": authenticated_customer_id,
        "tool_history": [],
        "seen_tool_calls": [],
        "steps": 0,
        "result": None,
        "pending_calls": [],
    }

    if use_memory:
        final_state = memory_agent_graph.invoke(
            initial_state,
            config=config,
        )

        saved = memory_agent_graph.get_state(config)
    else:
        final_state = agent_graph.invoke(initial_state)

    result = final_state.get("result")

    if result is None:
        raise RuntimeError(
            "Graph ended without a final result"
        )

    return result