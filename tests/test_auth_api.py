from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import (
    JWT_ALGORITHM,
    JWT_ISSUER,
    JWT_AUDIENCE,
)


client = TestClient(app)

TEST_SECRET = "test-only-secret-for-jwt-automated-tests-123456"


@pytest.fixture(autouse=True)
def configure_test_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", TEST_SECRET)


@pytest.fixture
def mock_agent(monkeypatch):
    calls = []

    def fake_run_agent_loop(
        user_message,
        *,
        authenticated_customer_id=None,
    ):
        calls.append(authenticated_customer_id)

        return {
            "customer_id": authenticated_customer_id,
            "message": user_message,
        }

    monkeypatch.setattr(
        "app.api.agent.run_agent_loop",
        fake_run_agent_loop,
    )

    return calls



def make_token(
    customer_id="CUS-001",
    secret=TEST_SECRET,
    expired=False,
    issuer=JWT_ISSUER,
    audience=JWT_AUDIENCE,
):
    now = datetime.now(timezone.utc)

    issued_at = now - timedelta(hours=1) if expired else now
    expires_at = (
        now - timedelta(minutes=1)
        if expired
        else now + timedelta(minutes=15)
    )

    payload = {
        "iss": issuer,
        "aud": audience,
        "iat": issued_at,
        "exp": expires_at,
    }

    if customer_id is not None:
        payload["sub"] = customer_id

    return jwt.encode(
        payload,
        secret,
        algorithm=JWT_ALGORITHM,
    )



def send_chat(token=None):
    headers = {}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    return client.post(
        "/agent/chat",
        json={"message": "Check order ORD-1001"},
        headers=headers,
    )


def test_missing_token_returns_401(mock_agent):
    response = send_chat()

    assert response.status_code == 401
    assert mock_agent == []


def test_valid_token_passes_customer_identity(mock_agent):
    token = make_token(customer_id="CUS-001")

    response = send_chat(token)

    assert response.status_code == 200
    assert response.json()["customer_id"] == "CUS-001"
    assert mock_agent == ["CUS-001"]


def test_other_customer_identity_is_preserved(mock_agent):
    token = make_token(customer_id="CUS-002")

    response = send_chat(token)

    assert response.status_code == 200
    assert response.json()["customer_id"] == "CUS-002"
    assert mock_agent == ["CUS-002"]


def test_forged_signature_returns_401(mock_agent):
    token = make_token(
        secret="wrong-test-signing-key-at-least-32-bytes"
    )

    response = send_chat(token)

    assert response.status_code == 401
    assert mock_agent == []


def test_expired_token_returns_401(mock_agent):
    token = make_token(expired=True)

    response = send_chat(token)

    assert response.status_code == 401
    assert mock_agent == []



def test_wrong_issuer_returns_401(mock_agent):
    token = make_token(
        issuer="unknown-issuer"
    )

    response = send_chat(token)

    assert response.status_code == 401
    assert mock_agent == []


def test_wrong_audience_returns_401(mock_agent):
    token = make_token(
        audience="another-api"
    )

    response = send_chat(token)

    assert response.status_code == 401
    assert mock_agent == []


def test_missing_subject_returns_401(mock_agent):
    token = make_token(
        customer_id=None
    )

    response = send_chat(token)

    assert response.status_code == 401
    assert mock_agent == []
