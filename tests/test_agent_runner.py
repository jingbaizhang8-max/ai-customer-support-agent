from types import SimpleNamespace

from app.agent import agent_runner


def test_agent_executes_order_tool(monkeypatch):
    fake_call = SimpleNamespace(
        id="call_001",
        function=SimpleNamespace(
            name="get_order",
            arguments='{"order_id": "ORD-1001"}',
        ),
    )

    fake_message = SimpleNamespace(
        tool_calls=[fake_call],
        content=None,
    )

    monkeypatch.setattr(
        agent_runner,
        "request_tool_call",
        lambda user_message: fake_message,
    )

    monkeypatch.setattr(
        agent_runner,
        "generate_final_answer",
        lambda **kwargs: "Your order is in transit.",
    )

    result = agent_runner.run_agent(
        "Where is order ORD-1001?",
        authenticated_customer_id="CUS-001"
    )

    assert result["type"] == "answer"
    assert result["content"] == "Your order is in transit."

    tool_result = result["tool_results"][0]

    assert tool_result["tool_call_id"] == "call_001"
    assert tool_result["tool_name"] == "get_order"
    assert tool_result["result"]["success"] is True
    assert tool_result["result"]["data"]["status"] == "shipped"


def test_agent_returns_text_without_tool_call(monkeypatch):
    fake_message = SimpleNamespace(
        tool_calls=None,
        content="Hello! How can I help?",
    )

    monkeypatch.setattr(
        agent_runner,
        "request_tool_call",
        lambda user_message: fake_message,
    )

    result = agent_runner.run_agent("Hello")

    assert result["type"] == "text"
    assert result["content"] == "Hello! How can I help?"


def test_agent_rejects_invalid_json_arguments(monkeypatch):
    fake_call = SimpleNamespace(
        id="call_002",
        function=SimpleNamespace(
            name="get_order",
            arguments="{invalid json}",
        ),
    )

    fake_message = SimpleNamespace(
        tool_calls=[fake_call],
        content=None,
    )

    monkeypatch.setattr(
        agent_runner,
        "request_tool_call",
        lambda user_message: fake_message,
    )

    monkeypatch.setattr(
        agent_runner,
        "generate_final_answer",
        lambda **kwargs: "Invalid tool arguments.",
    )

    result = agent_runner.run_agent(
        "Check my order.",
        authenticated_customer_id="CUS-001"
    )

    assert result["tool_results"][0]["result"] == {
        "success": False,
        "error": "invalid_json_arguments",
    }
