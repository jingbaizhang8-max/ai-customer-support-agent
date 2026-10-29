
from app.graph.agent_graph import run_graph_agent


result = run_graph_agent(
    user_message=(
        "Please use get_order to check my order ORD-1001, "
        "and use search_refund_policy to determine whether "
        "a shipped order can request a refund. "
        "Explain the human approval requirement. "
        "Clearly state that this is a fictional demo policy, "
        "not an official Olist policy, and no real refund occurs."
    ),
    authenticated_customer_id="CUS-001",
)

print("\n=== Agent 回答 ===")
print(result.get("content"))

print("\n=== 工具调用记录 ===")

tool_names = []

for item in result.get("tool_results", []):
    name = item.get("tool_name")
    tool_names.append(name)

    print("工具：", name)
    print("结果：", item.get("result"))

print("\n本次调用的工具：", tool_names)
