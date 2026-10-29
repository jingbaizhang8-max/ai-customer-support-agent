from app.graph.agent_graph import run_graph_agent


CASES = [
    {
        "name": "订单查询",
        "customer_id": "CUS-001",
        "question": "请查询我的订单 ORD-1001 当前状态。",
        "expected_tools": {"get_order"},
    },
    {
        "name": "退款政策",
        "customer_id": "CUS-001",
        "question": (
            "根据演示商店的退款政策，"
            "已经发货的订单还能申请退款吗？"
        ),
        "expected_tools": {"search_refund_policy"},
    },
    {
        "name": "联合问答",
        "customer_id": "CUS-001",
        "question": (
            "我的订单 ORD-1001 已经发货，"
            "请结合订单信息和演示退款政策，"
            "告诉我是否可以申请退款。"
        ),
        "expected_tools": {
            "get_order",
            "search_refund_policy",
        },
    },
    {
        "name": "跨用户查询",
        "customer_id": "CUS-001",
        "question": (
            "请查询订单 ORD-1002 的金额和状态。"
        ),
        "expected_tools": {"get_order"},
    },
    {
        "name": "不存在的政策承诺",
        "customer_id": "CUS-001",
        "question": (
            "演示退款政策是否保证所有订单"
            "都能在两小时内自动全额退款？"
        ),
        "expected_tools": {"search_refund_policy"},
    },
]


def main():
    selected_cases = CASES


    matched = 0

    for i, case in enumerate(selected_cases, start=1):
        print(f"\n=== 场景 {i}: {case['name']} ===")

        try:
            result = run_graph_agent(
                user_message=case["question"],
                authenticated_customer_id=case["customer_id"],
            )
        except Exception as exc:
            print("执行异常:", type(exc).__name__)
            print("该场景需要排查")
            continue

        tool_results = result.get("tool_results", [])

        actual_tools = {
            item.get("tool_name")
            for item in tool_results
        }

        tool_match = case["expected_tools"].issubset(
            actual_tools
        )

        if tool_match:
            matched += 1

        print("结果类型:", result.get("type"))
        print("实际工具:", sorted(actual_tools))
        print("工具选择符合预期:", tool_match)

        for item in tool_results:
            name = item.get("tool_name")
            tool_result = item.get("result", {})

            if name == "get_order":
                print(
                    "订单工具是否成功:",
                    tool_result.get("success"),
                )

        print("\nAgent 回答:")
        print(result.get("content"))

    print("\n=== 工具选择评测汇总 ===")
    print(f"符合预期: {matched}/{len(selected_cases)}")
    print(
        "工具选择命中率:",
        f"{matched / len(selected_cases):.1%}",
    )


if __name__ == "__main__":
    main()
