from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage, AIMessage


# 1. 定义一个简单的回复节点
def reply_node(state: MessagesState):
    last_message = state["messages"][-1].content

    return {
        "messages": [
            AIMessage(content=f"已收到：{last_message}")
        ]
    }


# 2. 构建 LangGraph
builder = StateGraph(MessagesState)

builder.add_node("reply", reply_node)
builder.add_edge(START, "reply")
builder.add_edge("reply", END)


# 3. 添加 Checkpointer
memory = InMemorySaver()
graph = builder.compile(checkpointer=memory)


# 4. 客户 A：第一次对话
config_a = {
    "configurable": {
        "thread_id": "demo-customer-A"
    }
}

graph.invoke(
    {
        "messages": [
            HumanMessage(content="我的订单是 ORD-1001")
        ]
    },
    config=config_a
)


# 5. 客户 A：第二次对话
graph.invoke(
    {
        "messages": [
            HumanMessage(content="我刚才说的是哪个订单？")
        ]
    },
    config=config_a
)


# 6. 查看客户 A 保存的对话
state_a = graph.get_state(config_a)

print("客户 A 的历史消息：")

for message in state_a.values["messages"]:
    print(message.type, ":", message.content)

print("客户 A 消息数量：", len(state_a.values["messages"]))


# 7. 客户 B：独立对话
config_b = {
    "configurable": {
        "thread_id": "demo-customer-B"
    }
}

graph.invoke(
    {
        "messages": [
            HumanMessage(content="我的订单是 ORD-1002")
        ]
    },
    config=config_b
)

state_b = graph.get_state(config_b)

print("\n客户 B 消息数量：", len(state_b.values["messages"]))
