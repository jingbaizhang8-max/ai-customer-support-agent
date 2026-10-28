from uuid import uuid4

from app.graph.agent_graph import (
    run_graph_agent,
    memory_agent_graph,
)

customer_id = "CUS-001"
conversation_id = str(uuid4())

print("=== 第一轮 ===")

result1 = run_graph_agent(
    "请使用 get_order 查询我的订单 ORD-1001",
    authenticated_customer_id=customer_id,
    conversation_id=conversation_id,
)

print(result1)

print("\n=== 第二轮 ===")

result2 = run_graph_agent(
    "那它现在发货了吗？请查询物流状态",
    authenticated_customer_id=customer_id,
    conversation_id=conversation_id,
)

print(result2)

# 检查保存的用户消息
config = {
    "configurable": {
        "thread_id": (
            f"customer:{customer_id}"
            f":conversation:{conversation_id}"
        )
    }
}
# print("\n=== 对比内部和外部读取 ===")
# print("外部 Graph ID:", id(memory_agent_graph))
# print("外部 thread_id:", config["configurable"]["thread_id"])
snapshot = memory_agent_graph.get_state(config)
# print("外部消息数量:", len(snapshot.values.get("messages", [])))
# print(
#     "外部 Checkpoint 数量:",
#     len(list(memory_agent_graph.get_state_history(config)))
# )
# print("\n=== Checkpointer 诊断 ===")
# print("保存的字段：", list(snapshot.values.keys()))
# print("实际线程：", snapshot.config.get("configurable", {}).get("thread_id"))

messages = snapshot.values.get("messages", [])

print("消息数量：", len(messages))

user_messages = [
    msg["content"]
    for msg in messages
    if isinstance(msg, dict) and msg.get("role") == "user"
]

print("\n=== 已保存的用户消息 ===")
for msg in user_messages:
    print(msg)

assert len(user_messages) == 2
print("\n多轮消息保存测试通过")


# ========== 多客户与多会话隔离测试 ==========

print("\n=== 多客户隔离测试 ===")


def make_config(customer_id: str, conversation_id: str):
    return {
        "configurable": {
            "thread_id": (
                f"customer:{customer_id}"
                f":conversation:{conversation_id}"
            )
        }
    }


# 1. 原客户 + 原会话：应能读取历史
state_a = memory_agent_graph.get_state(
    make_config("CUS-001", conversation_id)
)

assert len(state_a.values.get("messages", [])) > 0

print("客户 A 原会话：可以读取历史")


# 2. 不同客户 + 相同会话 UUID
state_b = memory_agent_graph.get_state(
    make_config("CUS-002", conversation_id)
)

assert state_b.values.get("messages", []) == []

print("客户 B 相同会话 UUID：无历史")


# 3. 相同客户 + 不同会话 UUID
other_conversation_id = str(uuid4())

state_c = memory_agent_graph.get_state(
    make_config("CUS-001", other_conversation_id)
)

assert state_c.values.get("messages", []) == []

print("客户 A 新会话：无历史")


print("\n多客户与多会话隔离测试通过")

