import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.api import agent as agent_api


def fake_answer():
    return {
        "type": "answer",
        "content": "测试回答",
        "tool_results": [],
    }


@pytest.fixture
def authed_client():
    # 只在测试中模拟已通过 JWT 验证的客户
    app.dependency_overrides[
        agent_api.get_authenticated_customer_id
    ] = lambda: "CUS-001"

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(
            agent_api.get_authenticated_customer_id,
            None,
        )


# 1. 多轮模式：正确传递会话 ID 和可信客户身份
def test_memory_conversation_id(
    authed_client, monkeypatch
):
    monkeypatch.setenv("USE_LANGGRAPH_AGENT", "true")

    calls = []

    def fake_graph(**kwargs):
        calls.append(kwargs)
        return fake_answer()

    monkeypatch.setattr(
        agent_api, "run_graph_agent", fake_graph
    )

    conversation_id = str(uuid4())

    response = authed_client.post(
        "/agent/chat",
        json={
            "message": "查询我的订单",
            "conversation_id": conversation_id,
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert calls[0]["conversation_id"] == conversation_id
    assert (
        calls[0]["authenticated_customer_id"]
        == "CUS-001"
    )


# 2. 非法 UUID：拒绝请求
def test_invalid_conversation_id(authed_client):
    response = authed_client.post(
        "/agent/chat",
        json={
            "message": "查询订单",
            "conversation_id": "not-a-uuid",
        },
    )

    assert response.status_code == 422


# 3. 关闭 LangGraph：拒绝多轮会话请求
def test_memory_requires_langgraph(
    authed_client, monkeypatch
):
    monkeypatch.setenv("USE_LANGGRAPH_AGENT", "false")

    response = authed_client.post(
        "/agent/chat",
        json={
            "message": "查询订单",
            "conversation_id": str(uuid4()),
        },
    )

    assert response.status_code == 400


# 4. 没有 JWT：必须拒绝访问
def test_memory_requires_auth():
    client = TestClient(app)

    response = client.post(
        "/agent/chat",
        json={
            "message": "查询订单",
            "conversation_id": str(uuid4()),
        },
    )

    assert response.status_code == 401


# 5. 不传 conversation_id：旧版 Agent 仍可运行
def test_legacy_agent_still_works(
    authed_client, monkeypatch
):
    monkeypatch.setenv("USE_LANGGRAPH_AGENT", "false")

    def fake_legacy(**kwargs):
        assert (
            kwargs["authenticated_customer_id"]
            == "CUS-001"
        )
        return fake_answer()

    monkeypatch.setattr(
        agent_api, "run_agent_loop", fake_legacy
    )

    response = authed_client.post(
        "/agent/chat",
        json={"message": "你好"},
    )

    assert response.status_code == 200
    assert response.json()["type"] == "answer"