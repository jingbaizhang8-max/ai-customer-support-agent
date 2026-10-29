import json
import math

def build_sliding_window(
        messages: list[dict],
        max_turns: int = 4,
) -> list[dict]:
    """
    保留 System Prompt 和最近 max_turns 轮用户对话。

    一轮对话：
    user -> assistant -> tool -> assistant
    或：
    user -> assistant

    不修改原始 messages。
    """

    if max_turns < 1:
        raise ValueError("max_turns must be >= 1")

    system_messages = []
    turns = []

    for message in messages:
        role = message.get("role")

        if role == "system":
            if turns:
                raise ValueError(
                    "system message must apper before user turns"
                )
            system_messages.append(message)

        elif role == "user":
            turns.append([message])

        elif role in ("assistant", "tool"):
            if not turns:
                raise ValueError("message without user turn")
            turns[-1].append(message)

        else:
            raise ValueError(f"unsupported role: {role}")

    if not turns:
        raise ValueError("no user messages")

    recent_turns = turns[-max_turns:]

    result = system_messages + [
        message
        for turn in recent_turns
        for message in turn
    ]

    pending = set()
    for message in result:
        role = message["role"]

        if role == "assistant":
            if pending:
                raise ValueError("unfinished tool calls")
            for call in message.get("tool_calls") or []:
                call_id = call["id"]
                if call_id in pending:
                    raise  ValueError("duplicate tool call id")

                pending.add(call_id)
        elif role == "tool":
            call_id = message.get("tool_call_id")

            if call_id not in pending:
                raise ValueError("orphan tool result")

            pending.remove(call_id)

        elif role=="user" and pending:
            raise ValueError("unfinished tool calls")

    if pending:
        raise ValueError("unfinished tool calls")

    return result


def estimate_tokens(messages: list[dict]) -> int:
    total =0

    for message in messages:
        content = json.dumps(
            message,
            ensure_ascii=False,
        )

        byte_count = len(content.encode("utf-8"))

        total += math.ceil(byte_count / 3) + 8

    return total

def build_budgeted_context(
        messages: list[dict],
        max_turns: int= 4,
        max_context_tokens: int = 4000,
        reserved_output_tokens: int = 800,
        reserved_tool_tokens: int = 500,
) -> list[dict]:

    available_tokens = (
        max_context_tokens - reserved_tool_tokens -reserved_output_tokens
    )

    if available_tokens <= 0:
        raise ValueError("invalid_token_budget")

    turn_count = sum(
        message.get("role") == "user"
        for message in messages
    )

    keep_turns = min(max_turns, turn_count)

    for count in range(keep_turns, 0, -1):
        candidate = build_sliding_window(
            messages, max_turns=count,
        )

        estimated = estimate_tokens(candidate)

        if estimated <= available_tokens:
            return candidate

    raise ValueError("current_turn_exceeds_budget")