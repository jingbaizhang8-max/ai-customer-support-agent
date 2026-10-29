
from importlib import import_module

from openai import OpenAIError


def test_llm_node_keeps_latest_four_turns(monkeypatch):
    graph_module = import_module(
        "app.graph.agent_graph"
    )

    # 构造 6 轮历史对话
    messages = [
        {
            "role": "system",
            "content": "你是电商客服助手",
        }
    ]

    for i in range(1, 7):
        messages.append({
            "role": "user",
            "content": f"问题{i}",
        })

        if i == 4:
            # 第四轮包含一次完整的工具调用
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_004",
                    "type": "function",
                    "function": {
                        "name": "get_order",
                        "arguments": '{"order_id":"ORD-1001"}',
                    },
                }],
            })

            messages.append({
                "role": "tool",
                "tool_call_id": "call_004",
                "content": '{"status":"shipped"}',
            })

        messages.append({
            "role": "assistant",
            "content": f"回答{i}",
        })

    original_count = len(messages)

    state = {
        "messages": messages,
        "authenticated_customer_id": "CUS-001",
        "tool_history": [],
        "seen_tool_calls": [],
        "steps": 0,
        "result": None,
        "pending_calls": [],
    }

    captured = {}

    # 模拟 LLM 请求，不真正调用 DeepSeek
    def fake_request_agent_step(model_messages):
        captured["messages"] = model_messages
        raise OpenAIError("mock_llm_error")

    monkeypatch.setattr(
        graph_module,
        "request_agent_step",
        fake_request_agent_step,
    )

    # 运行真正的 llm_node
    graph_module.llm_node(state)

    sent = captured["messages"]

    # 只保留最近四轮：3、4、5、6
    user_messages = [
        message["content"]
        for message in sent
        if message["role"] == "user"
    ]

    assert user_messages == [
        "问题3",
        "问题4",
        "问题5",
        "问题6",
    ]

    # System Prompt 必须保留
    assert sent[0]["role"] == "system"

    # Tool Call 和 Tool Result 必须配对
    tool_call_ids = [
        call["id"]
        for message in sent
        if message["role"] == "assistant"
        for call in message.get("tool_calls", [])
    ]

    tool_result_ids = [
        message["tool_call_id"]
        for message in sent
        if message["role"] == "tool"
    ]

    assert tool_call_ids == ["call_004"]
    assert tool_result_ids == ["call_004"]

    # 原始状态不应被裁剪
    assert len(state["messages"]) == original_count

    original_user_messages = [
        message["content"]
        for message in state["messages"]
        if message["role"] == "user"
    ]

    assert len(original_user_messages) == 6
