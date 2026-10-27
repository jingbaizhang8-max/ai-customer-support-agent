
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api import agent as agent_api
from app.core.auth import (
    JWT_ALGORITHM,
    JWT_ISSUER,
    JWT_AUDIENCE,
)


TEST_SECRET = "test-customer-jwt-secret-at-least-32-bytes"


def make_token(secret=TEST_SECRET):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": "CUS-001",
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }

    return jwt.encode(
        payload,
        secret,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
def api_client(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        TEST_SECRET,
    )

    calls = []

    def fake_old_agent(
        user_message,
        *,
        authenticated_customer_id=None,
    ):
        calls.append(
            ("old", user_message, authenticated_customer_id)
        )

        return {
            "type": "answer",
            "content": "Response from old Agent Loop",
            "tool_results": [],
        }

    def fake_graph_agent(
        user_message,
        *,
        authenticated_customer_id=None,
    ):
        calls.append(
            ("graph", user_message, authenticated_customer_id)
        )

        return {
            "type": "answer",
            "content": "Response from LangGraph",
            "tool_results": [],
        }

    monkeypatch.setattr(
        agent_api,
        "run_agent_loop",
        fake_old_agent,
    )

    monkeypatch.setattr(
        agent_api,
        "run_graph_agent",
        fake_graph_agent,
    )

    with TestClient(app) as client:
        yield client, calls


def send_chat(client, token=None):
    headers = {}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    return client.post(
        "/agent/chat",
        json={"message": "Check order ORD-1001"},
        headers=headers,
    )


def test_default_uses_old_agent(api_client, monkeypatch):
    monkeypatch.delenv(
        "USE_LANGGRAPH_AGENT",
        raising=False,
    )

    client, calls = api_client

    response = send_chat(client, make_token())

    assert response.status_code == 200
    assert response.json()["content"] == (
        "Response from old Agent Loop"
    )

    assert calls == [
        ("old", "Check order ORD-1001", "CUS-001")
    ]


def test_false_uses_old_agent(api_client, monkeypatch):
    monkeypatch.setenv(
        "USE_LANGGRAPH_AGENT",
        "false",
    )

    client, calls = api_client

    response = send_chat(client, make_token())

    assert response.status_code == 200

    assert calls == [
        ("old", "Check order ORD-1001", "CUS-001")
    ]


def test_true_uses_langgraph(api_client, monkeypatch):
    monkeypatch.setenv(
        "USE_LANGGRAPH_AGENT",
        "true",
    )

    client, calls = api_client

    response = send_chat(client, make_token())

    assert response.status_code == 200
    assert response.json()["content"] == (
        "Response from LangGraph"
    )

    assert calls == [
        ("graph", "Check order ORD-1001", "CUS-001")
    ]


def test_invalid_jwt_blocks_langgraph(
    api_client,
    monkeypatch,
):
    monkeypatch.setenv(
        "USE_LANGGRAPH_AGENT",
        "true",
    )

    client, calls = api_client

    invalid_token = make_token(
        secret="incorrect-signing-key-at-least-32-bytes"
    )

    response = send_chat(
        client,
        invalid_token,
    )

    assert response.status_code == 401
    assert calls == []
