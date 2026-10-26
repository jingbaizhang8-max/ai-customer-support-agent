
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.agent import get_authenticated_customer_id
from app.core.database import get_db


VALID_BODY = {
    "order_id": "ORD-1001",
    "ticket_type": "refund_request",
    "description": "I would like to request a refund.",
    "confirmed": True,
}


@pytest.fixture
def client(monkeypatch):
    # Prevent any real ticket from being created.
    def block_database_write(**kwargs):
        raise AssertionError(
            "Ticket creation must not be called"
        )

    monkeypatch.setattr(
        "app.api.tickets.create_ticket_for_customer",
        block_database_write,
    )

    # Avoid opening a real database session.
    original_overrides = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = lambda: None

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def test_missing_jwt_returns_401(client):
    response = client.post(
        "/tickets",
        json=VALID_BODY,
        headers={"Idempotency-Key": "test-request-001"},
    )

    assert response.status_code == 401


def test_unconfirmed_request_returns_422(client):
    # Simulate a customer who has already authenticated.
    app.dependency_overrides[
        get_authenticated_customer_id
    ] = lambda: "CUS-001"

    body = {
        **VALID_BODY,
        "confirmed": False,
    }

    response = client.post(
        "/tickets",
        json=body,
        headers={"Idempotency-Key": "test-request-002"},
    )

    assert response.status_code == 422


def test_missing_idempotency_key_returns_422(client):
    app.dependency_overrides[
        get_authenticated_customer_id
    ] = lambda: "CUS-001"

    response = client.post(
        "/tickets",
        json=VALID_BODY,
    )

    assert response.status_code == 422
