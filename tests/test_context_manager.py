
import pytest

from app.agent.context_manager import build_sliding_window
from app.agent.context_manager import (
    estimate_tokens,
    build_budgeted_context,
)

def example_messages():
    return [
        {"role": "system", "content": "你是客服 Agent"},

        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！"},

        {"role": "user", "content": "查询 ORD-1001"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "get_order",
                        "arguments": '{"order_id":"ORD-1001"}',
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": '{"status":"shipped"}',
        },
        {"role": "assistant", "content": "订单已发货"},

        {"role": "user", "content": "它现在在哪里？"},
    ]


def test_keep_recent_two_turns():
    messages = example_messages()

    result = build_sliding_window(
        messages,
        max_turns=2,
    )

    assert len(result) == 6
    assert result[0]["role"] == "system"
    assert result[1]["content"] == "查询 ORD-1001"
    assert result[-1]["content"] == "它现在在哪里？"

    # 原始历史没有被删除
    assert len(messages) == 8


def test_keep_tool_call_pair():
    result = build_sliding_window(
        example_messages(),
        max_turns=2,
    )

    tool_call = result[2]["tool_calls"][0]["id"]
    tool_result = result[3]["tool_call_id"]

    assert tool_call == tool_result == "call_001"


def test_one_turn_drops_old_tool_calls():
    result = build_sliding_window(
        example_messages(),
        max_turns=1,
    )

    assert [msg["role"] for msg in result] == [
        "system",
        "user",
    ]


def test_reject_orphan_tool_result():
    messages = [
        {"role": "system", "content": "客服"},
        {"role": "user", "content": "查询"},
        {
            "role": "tool",
            "tool_call_id": "missing_call",
            "content": "{}",
        },
    ]

    with pytest.raises(
        ValueError,
        match="orphan tool result",
    ):
        build_sliding_window(messages)


def test_budget_removes_old_turns():
    messages = [
        {"role": "system", "content": "客服助手"},
        {"role": "user", "content": "旧问题" * 200},
        {"role": "assistant", "content": "旧回答" * 200},
        {"role": "user", "content": "查询 ORD-1001"},
    ]

    latest = build_sliding_window(messages, max_turns=1)
    budget = estimate_tokens(latest) + 50

    result = build_budgeted_context(
        messages,
        max_turns=3,
        max_context_tokens=budget,
        reserved_output_tokens=30,
        reserved_tool_tokens=20,
    )

    assert result == latest
    assert len(messages) == 4


def test_budget_preserves_tool_pair():
    messages = [
        {"role": "system", "content": "客服"},
        {"role": "user", "content": "旧问题" * 200},
        {"role": "assistant", "content": "旧回答" * 200},

        {"role": "user", "content": "查询订单"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_001",
                    "type": "function",
                    "function": {
                        "name": "get_order",
                        "arguments": "{}",
                    },
                }
            ],
        },
        {
            "role": "tool",
            "tool_call_id": "call_001",
            "content": '{"status":"shipped"}',
        },
        {"role": "assistant", "content": "订单已发货"},

        {"role": "user", "content": "那物流呢？"},
    ]

    latest_two = build_sliding_window(
        messages,
        max_turns=2,
    )

    result = build_budgeted_context(
        messages,
        max_turns=3,
        max_context_tokens=estimate_tokens(latest_two) + 50,
        reserved_output_tokens=30,
        reserved_tool_tokens=20,
    )

    assert result == latest_two
    assert result[2]["tool_calls"][0]["id"] == "call_001"
    assert result[3]["tool_call_id"] == "call_001"


def test_budget_rejects_oversized_current_turn():
    messages = [
        {"role": "system", "content": "客服"},
        {"role": "user", "content": "很长的问题" * 1000},
    ]

    with pytest.raises(
        ValueError,
        match="current_turn_exceeds_budget",
    ):
        build_budgeted_context(
            messages,
            max_context_tokens=100,
            reserved_output_tokens=20,
            reserved_tool_tokens=20,
        )
