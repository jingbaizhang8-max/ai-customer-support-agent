
from types import SimpleNamespace

from app.agent import agent_loop


def make_tool_message(tool_name, call_id):
    arguments = '{"order_id": "ORD-1001"}'

    call = SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(
            name=tool_name,
            arguments=arguments,
        ),
    )

    return SimpleNamespace(
        tool_calls=[call],
        content=None,
        model_dump=lambda exclude_none=True: {
            "role": "assistant",
            "tool_calls": [{
                "id": call_id,
                "type": "function",
                "function": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            }],
        },
    )


def test_agent_executes_multiple_steps(monkeypatch):
    responses = [
        make_tool_message("get_order", "call_001"),
        make_tool_message("get_shipping_status", "call_002"),
        SimpleNamespace(
            tool_calls=None,
            content="Your order is in transit.",
            model_dump=lambda exclude_none=True: {
                "role": "assistant",
                "content": "Your order is in transit.",
            },
        ),
    ]

    captured_messages = []

    def fake_request_agent_step(messages):
        captured_messages.append(list(messages))
        return responses.pop(0)

    monkeypatch.setattr(
        agent_loop,
        "request_agent_step",
        fake_request_agent_step,
    )

    result = agent_loop.run_agent_loop(
        "Check ORD-1001. If shipped, find tracking.",
        authenticated_customer_id="CUS-001",
    )

    assert result["type"] == "answer"
    assert result["content"] == "Your order is in transit."

    assert len(captured_messages) == 3

    assert [
        item["step"] for item in result["tool_results"]
    ] == [1, 2]

    assert [
        item["tool_name"] for item in result["tool_results"]
    ] == [
        "get_order",
        "get_shipping_status",
    ]

    assert result["tool_results"][0]["result"]["success"]
    assert result["tool_results"][1]["result"]["success"]

    # 第二轮调用 LLM 时，已包含第一轮工具结果
    assert captured_messages[1][-1]["role"] == "tool"
    assert captured_messages[1][-1]["tool_call_id"] == "call_001"



def test_agent_stops_at_step_limit(monkeypatch):
    call_count = 0

    def always_request_tool(messages):
        nonlocal call_count

        call_count += 1

        return make_tool_message(
            "get_order",
            f"call_{call_count}",
        )

    monkeypatch.setattr(
        agent_loop,
        "request_agent_step",
        always_request_tool,
    )

    result = agent_loop.run_agent_loop(
        "Keep checking order ORD-1001.",
        authenticated_customer_id="CUS-001",
    )

    assert result["type"] == "step_limit_reached"

    assert call_count == agent_loop.MAX_STEPS

    assert len(result["tool_results"]) == agent_loop.MAX_STEPS

    assert [
        item["step"] for item in result["tool_results"]
    ] == [1, 2, 3, 4]


def test_agent_rejects_tool_calls_over_budget(monkeypatch):
    monkeypatch.setattr(agent_loop, "MAX_TOOL_CALLS", 1)

    fake_message = make_tool_message(
        "get_order", "call_001"
    )

    second_message = make_tool_message(
        "get_shipping_status", "call_002"
    )

    fake_message.tool_calls.extend(
        second_message.tool_calls
    )

    monkeypatch.setattr(
        agent_loop,
        "request_agent_step",
        lambda messages: fake_message,
    )

    def forbidden_execution(*args, **kwargs):
        raise AssertionError("Tools must not execute")

    monkeypatch.setattr(
        agent_loop,
        "execute_tool",
        forbidden_execution,
    )

    result = agent_loop.run_agent_loop(
        "Check my order and its shipping status.",
        authenticated_customer_id="CUS-001",
    )

    assert result["type"] == "tool_limit_reached"
    assert result["tool_results"] == []


def test_agent_detects_duplicate_tool_calls(monkeypatch):
    responses = iter([
        make_tool_message("get_order", "call_001"),
        make_tool_message("get_order", "call_002"),
        SimpleNamespace(
            tool_calls=None,
            content="Order checked.",
            model_dump=lambda exclude_none=True: {
                "role": "assistant",
                "content": "Order checked.",
            },
        ),
    ])

    monkeypatch.setattr(
        agent_loop,
        "request_agent_step",
        lambda messages: next(responses),
    )

    original_execute_tool = agent_loop.execute_tool
    execution_count = 0

    def counted_execute_tool(
            tool_name,
            arguments,
            *,
            authenticated_customer_id=None,
    ):
        nonlocal execution_count
        execution_count += 1

        return original_execute_tool(
            tool_name,
            arguments,
            authenticated_customer_id=authenticated_customer_id,
        )

    monkeypatch.setattr(
        agent_loop,
        "execute_tool",
        counted_execute_tool,
    )

    result = agent_loop.run_agent_loop(
        "Check order ORD-1001.",
        authenticated_customer_id="CUS-001"
    )

    assert result["type"] == "answer"
    assert len(result["tool_results"]) == 2

    assert result["tool_results"][0]["result"]["success"] is True

    assert result["tool_results"][1]["result"] == {
        "success": False,
        "error": "duplicate_tool_call",
    }

    assert execution_count == 1
