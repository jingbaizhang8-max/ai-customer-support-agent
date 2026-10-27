from openai import OpenAIError
import json
from importlib import import_module
from types import SimpleNamespace
old_loop_module = import_module("app.agent.agent_loop")
graph_module = import_module("app.graph.agent_graph")


def make_message(content="", tool_specs=None, prefix="call"):
    tool_calls = []

    for index, (name, arguments) in enumerate(tool_specs or []):
        raw_arguments = (
            arguments
            if isinstance(arguments, str)
            else json.dumps(arguments)
        )

        tool_calls.append(
            SimpleNamespace(
                id=f"{prefix}-{index}",
                function=SimpleNamespace(
                    name=name,
                    arguments=raw_arguments,
                ),
            )
        )

    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
    )

    def model_dump(exclude_none=True):
        data = {
            "role": "assistant",
            "content": content,
        }

        if tool_calls:
            data["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": call.function.arguments,
                    },
                }
                for call in tool_calls
            ]

        return data

    message.model_dump = model_dump
    return message


def initial_state(customer_id="CUS-001"):
    return {
        "messages": [
            {
                "role": "system",
                "content": "Test customer support assistant.",
            },
            {
                "role": "user",
                "content": "Check order ORD-1001.",
            },
        ],
        "authenticated_customer_id": customer_id,
        "tool_history": [],
        "seen_tool_calls": [],
        "steps": 0,
        "result": None,
        "pending_calls": [],
    }


def mock_llm(monkeypatch, responses):
    response_iterator = iter(responses)

    def fake_request_agent_step(messages):
        return next(response_iterator)

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_request_agent_step,
    )


def test_direct_answer_without_tools(monkeypatch):
    mock_llm(
        monkeypatch,
        [make_message(content="Hello!")],
    )

    result = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert result["result"]["type"] == "answer"
    assert result["result"]["content"] == "Hello!"
    assert result["tool_history"] == []
    assert result["steps"] == 1


def test_tool_execution_receives_customer_identity(monkeypatch):
    mock_llm(
        monkeypatch,
        [
            make_message(
                tool_specs=[
                    ("get_order", {"order_id": "ORD-1001"})
                ],
            ),
            make_message(content="Your order is shipped."),
        ],
    )

    calls = []

    def fake_execute_tool(
        name,
        arguments,
        *,
        authenticated_customer_id=None,
    ):
        calls.append(
            (name, arguments, authenticated_customer_id)
        )

        return {
            "success": True,
            "data": {"status": "shipped"},
        }

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = graph_module.agent_graph.invoke(
        initial_state("CUS-001")
    )

    assert result["result"]["type"] == "answer"
    assert len(calls) == 1

    assert calls[0] == (
        "get_order",
        {"order_id": "ORD-1001"},
        "CUS-001",
    )

    assert result["tool_history"][0]["tool_name"] == "get_order"


def test_invalid_json_does_not_execute_tool(monkeypatch):
    mock_llm(
        monkeypatch,
        [
            make_message(
                tool_specs=[
                    ("get_order", "{invalid-json")
                ],
            ),
            make_message(content="Invalid tool arguments."),
        ],
    )

    def forbidden_execute(*args, **kwargs):
        raise AssertionError("Tool must not execute")

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        forbidden_execute,
    )

    result = graph_module.agent_graph.invoke(
        initial_state()
    )

    tool_result = result["tool_history"][0]["result"]

    assert tool_result["success"] is False
    assert tool_result["error"] == "invalid_json_arguments"


def test_duplicate_tool_call_is_blocked(monkeypatch):
    request = ("get_order", {"order_id": "ORD-1001"})

    mock_llm(
        monkeypatch,
        [
            make_message(
                tool_specs=[request],
                prefix="first",
            ),
            make_message(
                tool_specs=[request],
                prefix="second",
            ),
            make_message(content="Done."),
        ],
    )

    calls = []

    def fake_execute_tool(name, arguments, **kwargs):
        calls.append(name)
        return {"success": True}

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        fake_execute_tool,
    )

    result = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert calls == ["get_order"]
    assert len(result["tool_history"]) == 2
    assert (
        result["tool_history"][1]["result"]["error"]
        == "duplicate_tool_call"
    )


def test_step_limit_returns_result(monkeypatch):
    responses = [
        make_message(
            tool_specs=[
                ("get_order", {"order_id": "ORD-1001"})
            ],
            prefix=f"round-{i}",
        )
        for i in range(4)
    ]

    mock_llm(monkeypatch, responses)

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        lambda *args, **kwargs: {"success": True},
    )

    result = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert result["steps"] == 4
    assert result["result"]["type"] == "step_limit_reached"
    assert len(result["tool_history"]) == 4


def test_tool_limit_blocks_execution(monkeypatch):
    seven_calls = [
        ("get_order", {"order_id": "ORD-1001"})
        for _ in range(7)
    ]

    mock_llm(
        monkeypatch,
        [make_message(tool_specs=seven_calls)],
    )

    def forbidden_execute(*args, **kwargs):
        raise AssertionError("Tool limit was bypassed")

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        forbidden_execute,
    )

    result = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert result["result"]["type"] == "tool_limit_reached"
    assert result["tool_history"] == []


def test_graph_blocks_unauthenticated_order_access(monkeypatch):
    mock_llm(
        monkeypatch,
        [
            make_message(
                tool_specs=[
                    ("get_order", {"order_id": "ORD-1001"})
                ]
            ),
            make_message(content="Authentication required."),
        ],
    )

    # Do NOT mock execute_tool in this test.
    result = graph_module.agent_graph.invoke(
        initial_state(customer_id=None)
    )

    tool_result = result["tool_history"][0]["result"]

    assert tool_result["success"] is False
    assert tool_result["error"] == "authentication_required"
    assert result["result"]["type"] == "answer"


def test_graph_blocks_unregistered_tool(monkeypatch):
    mock_llm(
        monkeypatch,
        [
            make_message(
                tool_specs=[
                    ("delete_all_orders", {})
                ]
            ),
            make_message(content="Tool not allowed."),
        ],
    )

    # Use the real Tool Registry.
    result = graph_module.agent_graph.invoke(
        initial_state(customer_id="CUS-001")
    )

    tool_result = result["tool_history"][0]["result"]

    assert tool_result["success"] is False
    assert tool_result["error"] == "tool_not_allowed"




def test_run_graph_agent_entrypoint(monkeypatch):
    captured_messages = []

    def fake_llm(messages):
        captured_messages.extend(messages)
        return make_message(
            content="Hello from LangGraph!"
        )

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_llm,
    )

    result = graph_module.run_graph_agent(
        "Hello",
        authenticated_customer_id="CUS-001",
    )

    assert result["type"] == "answer"
    assert result["content"] == "Hello from LangGraph!"
    assert result["tool_results"] == []

    assert captured_messages[0]["role"] == "system"
    assert captured_messages[1]["role"] == "user"
    assert captured_messages[1]["content"] == "Hello"

def test_tool_limit_preserves_message_pairs(monkeypatch):
    seven_calls = [
        ("get_order", {"order_id": "ORD-1001"})
        for _ in range(7)
    ]

    mock_llm(
        monkeypatch,
        [make_message(tool_specs=seven_calls)],
    )

    def forbidden_execute(*args, **kwargs):
        raise AssertionError("Tool must not execute")

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        forbidden_execute,
    )

    state = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert state["result"]["type"] == "tool_limit_reached"

    assistant = next(
        message
        for message in state["messages"]
        if message["role"] == "assistant"
    )

    tool_messages = [
        message
        for message in state["messages"]
        if message["role"] == "tool"
    ]

    assert len(assistant["tool_calls"]) == 7
    assert len(tool_messages) == 7

    call_ids = {
        call["id"]
        for call in assistant["tool_calls"]
    }

    result_ids = {
        message["tool_call_id"]
        for message in tool_messages
    }

    assert call_ids == result_ids

    assert all(
        json.loads(message["content"])["error"]
        == "tool_limit_reached"
        for message in tool_messages
    )

    assert state["tool_history"] == []


def test_llm_failure_returns_safe_result(monkeypatch):
    def fake_llm(messages):
        raise OpenAIError("simulated API failure")

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_llm,
    )

    state = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert state["result"]["type"] == "llm_service_error"
    assert state["tool_history"] == []
    assert state["result"]["tool_results"] == []


def test_llm_failure_preserves_tool_history(monkeypatch):
    call_count = 0

    def fake_llm(messages):
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return make_message(
                tool_specs=[
                    ("get_order", {"order_id": "ORD-1001"})
                ]
            )

        raise OpenAIError("simulated API timeout")

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_llm,
    )

    def fake_tool(name, arguments, **kwargs):
        return {
            "success": True,
            "data": {"status": "shipped"},
        }

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        fake_tool,
    )

    state = graph_module.agent_graph.invoke(
        initial_state()
    )

    assert state["result"]["type"] == "llm_service_error"
    assert len(state["tool_history"]) == 1
    assert state["tool_history"][0]["tool_name"] == "get_order"
    assert len(state["result"]["tool_results"]) == 1

def test_old_and_new_agents_same_direct_answer(monkeypatch):
    def fake_llm(messages):
        return make_message(
            content="Hello, how can I help?"
        )

    monkeypatch.setattr(
        old_loop_module,
        "request_agent_step",
        fake_llm,
    )

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_llm,
    )

    old_result = old_loop_module.run_agent_loop(
        "Hello",
        authenticated_customer_id="CUS-001",
    )

    new_result = graph_module.run_graph_agent(
        "Hello",
        authenticated_customer_id="CUS-001",
    )

    assert old_result == new_result
    assert new_result["type"] == "answer"


def test_old_and_new_agents_same_tool_result(monkeypatch):
    def make_fake_llm():
        responses = iter([
            make_message(
                tool_specs=[
                    ("get_order", {"order_id": "ORD-1001"})
                ]
            ),
            make_message(
                content="Your order is shipped."
            ),
        ])

        def fake_llm(messages):
            return next(responses)

        return fake_llm

    monkeypatch.setattr(
        old_loop_module,
        "request_agent_step",
        make_fake_llm(),
    )

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        make_fake_llm(),
    )

    calls = []

    def fake_execute_tool(
        name,
        arguments,
        *,
        authenticated_customer_id=None,
    ):
        calls.append(
            (name, arguments, authenticated_customer_id)
        )

        return {
            "success": True,
            "data": {
                "order_id": "ORD-1001",
                "status": "shipped",
            },
        }

    monkeypatch.setattr(
        old_loop_module,
        "execute_tool",
        fake_execute_tool,
    )

    monkeypatch.setattr(
        graph_module,
        "execute_tool",
        fake_execute_tool,
    )

    old_result = old_loop_module.run_agent_loop(
        "Check order ORD-1001",
        authenticated_customer_id="CUS-001",
    )

    new_result = graph_module.run_graph_agent(
        "Check order ORD-1001",
        authenticated_customer_id="CUS-001",
    )

    assert old_result == new_result

    assert calls == [
        ("get_order", {"order_id": "ORD-1001"}, "CUS-001"),
        ("get_order", {"order_id": "ORD-1001"}, "CUS-001"),
    ]

    assert new_result["type"] == "answer"
    assert len(new_result["tool_results"]) == 1
