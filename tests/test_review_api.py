
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.core.auth import (
    JWT_ISSUER,
    JWT_AUDIENCE,
    JWT_ALGORITHM,
)
from app.core.reviewer_auth import (
    REVIEWER_JWT_AUDIENCE,
    REVIEWER_JWT_ALGORITHM,
)


CUSTOMER_SECRET = "customer-test-secret-at-least-32-bytes-long"
REVIEWER_SECRET = "reviewer-test-secret-at-least-32-bytes-long"

TICKET_ID = "00000000-0000-4000-8000-000000000001"
REVIEW_URL = f"/reviews/{TICKET_ID}"

VALID_BODY = {
    "decision": "approved",
    "reason": "Approved by the test reviewer.",
}


def make_reviewer_token(role="reviewer", expired=False):
    now = datetime.now(timezone.utc)

    payload = {
        "sub": "TEST-REVIEWER-001",
        "role": role,
        "iss": JWT_ISSUER,
        "aud": REVIEWER_JWT_AUDIENCE,
        "iat": now - timedelta(hours=1) if expired else now,
        "exp": (
            now - timedelta(minutes=1)
            if expired
            else now + timedelta(minutes=15)
        ),
    }

    return jwt.encode(
        payload,
        REVIEWER_SECRET,
        algorithm=REVIEWER_JWT_ALGORITHM,
    )


def make_customer_token():
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
        CUSTOMER_SECRET,
        algorithm=JWT_ALGORITHM,
    )


@pytest.fixture
def review_client(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        CUSTOMER_SECRET,
    )
    monkeypatch.setenv(
        "REVIEWER_JWT_SECRET_KEY",
        REVIEWER_SECRET,
    )

    calls = []
    reviewed_tickets = set()

    def fake_review_ticket(
        db,
        *,
        ticket_id,
        authenticated_reviewer_id,
        decision,
        reason,
    ):
        calls.append(authenticated_reviewer_id)

        if ticket_id in reviewed_tickets:
            raise ValueError("ticket_not_pending")

        reviewed_tickets.add(ticket_id)

        return SimpleNamespace(
            review_id=str(uuid4()),
            ticket_id=ticket_id,
            reviewer_id=authenticated_reviewer_id,
            decision=decision,
            reason=reason,
        )

    monkeypatch.setattr(
        "app.api.reviews.review_ticket",
        fake_review_ticket,
    )

    original_overrides = app.dependency_overrides.copy()

    # No real PostgreSQL connection in these API tests.
    app.dependency_overrides[get_db] = lambda: None

    try:
        with TestClient(app) as client:
            yield client, calls
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def submit_review(client, token=None):
    headers = {}

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    return client.post(
        REVIEW_URL,
        json=VALID_BODY,
        headers=headers,
    )


def test_missing_token_returns_401(review_client):
    client, calls = review_client

    response = submit_review(client)

    assert response.status_code == 401
    assert calls == []


def test_customer_token_cannot_approve(review_client):
    client, calls = review_client

    response = submit_review(
        client,
        make_customer_token(),
    )

    assert response.status_code == 401
    assert calls == []


def test_valid_reviewer_can_approve(review_client):
    client, calls = review_client

    response = submit_review(
        client,
        make_reviewer_token(),
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "approved"
    assert (
        response.json()["reviewer_id"]
        == "TEST-REVIEWER-001"
    )
    assert calls == ["TEST-REVIEWER-001"]


def test_wrong_role_returns_401(review_client):
    client, calls = review_client

    response = submit_review(
        client,
        make_reviewer_token(role="customer"),
    )

    assert response.status_code == 401
    assert calls == []


def test_expired_reviewer_token_returns_401(review_client):
    client, calls = review_client

    response = submit_review(
        client,
        make_reviewer_token(expired=True),
    )

    assert response.status_code == 401
    assert calls == []


def test_duplicate_review_returns_409(review_client):
    client, calls = review_client
    token = make_reviewer_token()

    first = submit_review(client, token)
    second = submit_review(client, token)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == "ticket_not_pending"
    assert len(calls) == 2
