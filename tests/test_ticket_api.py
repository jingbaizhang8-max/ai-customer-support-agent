
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.agent import get_authenticated_customer_id
from app.core.database import get_db

from unittest.mock import MagicMock

VALID_BODY = {
    "order_id": "ORD-1001",
    "ticket_type": "refund_request",
    "description": "Item arrived damaged.",
    "confirmed": True,
}


@pytest.fixture
def api_client(monkeypatch):
    saved_tickets = {}

    def fake_create_ticket(
        db,
        *,
        order_id,
        authenticated_customer_id,
        ticket_type,
        description,
        idempotency_key,
    ):
        # Simulate order ownership.
        if (
            authenticated_customer_id != "CUS-001"
            or order_id != "ORD-1001"
        ):
            return None

        key = (
            authenticated_customer_id,
            idempotency_key,
        )

        existing = saved_tickets.get(key)

        if existing is not None:
            if (
                existing.order_id != order_id
                or existing.ticket_type != ticket_type
                or existing.description != description.strip()
            ):
                raise ValueError(
                    "idempotency_key_conflict"
                )

            return existing

        ticket = SimpleNamespace(
            ticket_id=str(uuid4()),
            customer_id=authenticated_customer_id,
            order_id=order_id,
            ticket_type=ticket_type,
            description=description.strip(),
            status="pending_review",
            created_at=None,
        )

        saved_tickets[key] = ticket

        return ticket

    def fake_get_ticket(
        db,
        *,
        ticket_id,
        authenticated_customer_id,
    ):
        for ticket in saved_tickets.values():
            if (
                ticket.ticket_id == ticket_id
                and ticket.customer_id
                == authenticated_customer_id
            ):
                return ticket

        return None

    monkeypatch.setattr(
        "app.api.tickets.create_ticket_for_customer",
        fake_create_ticket,
    )

    monkeypatch.setattr(
        "app.api.tickets.get_ticket_for_customer",
        fake_get_ticket,
    )

    original_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[
        get_authenticated_customer_id
    ] = lambda: "CUS-001"

    app.dependency_overrides[get_db] = lambda: None

    try:
        with TestClient(app) as client:
            yield client, saved_tickets
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(original_overrides)


def submit_ticket(client, key, body=None):
    return client.post(
        "/tickets",
        json=VALID_BODY if body is None else body,
        headers={"Idempotency-Key": key},
    )


def test_create_ticket_success(api_client):
    client, saved = api_client

    response = submit_ticket(
        client,
        "request-001",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "pending_review"
    assert response.json()["order_id"] == "ORD-1001"
    assert len(saved) == 1


def test_duplicate_request_returns_same_ticket(api_client):
    client, saved = api_client

    first = submit_ticket(client, "request-002")
    second = submit_ticket(client, "request-002")

    assert first.status_code == 200
    assert second.status_code == 200

    assert (
        first.json()["ticket_id"]
        == second.json()["ticket_id"]
    )

    assert len(saved) == 1


def test_idempotency_conflict_returns_409(api_client):
    client, saved = api_client

    first = submit_ticket(client, "request-003")

    changed_body = {
        **VALID_BODY,
        "description": "My package is missing.",
    }

    second = submit_ticket(
        client,
        "request-003",
        changed_body,
    )

    assert first.status_code == 200
    assert second.status_code == 409

    assert (
        second.json()["detail"]
        == "idempotency_key_conflict"
    )

    assert len(saved) == 1


def test_unauthorized_order_returns_404(api_client):
    client, saved = api_client

    # Simulate a different authenticated customer.
    app.dependency_overrides[
        get_authenticated_customer_id
    ] = lambda: "CUS-002"

    response = submit_ticket(
        client,
        "request-004",
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "order_not_found"
    assert len(saved) == 0


def test_ticket_read_authorization(api_client):
    client, saved = api_client

    created = submit_ticket(
        client,
        "request-005",
    )

    assert created.status_code == 200

    ticket_id = created.json()["ticket_id"]

    mock_db = MagicMock()
    mock_db.scalar.return_value = None

    app.dependency_overrides[get_db] = lambda: mock_db

    # Owner can access the ticket.
    owner_response = client.get(
        f"/tickets/{ticket_id}"
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["ticket_id"] == ticket_id

    # Another customer cannot access the ticket.
    app.dependency_overrides[
        get_authenticated_customer_id
    ] = lambda: "CUS-002"

    other_response = client.get(
        f"/tickets/{ticket_id}"
    )

    assert other_response.status_code == 404
    assert (
        other_response.json()["detail"]
        == "ticket_not_found"
    )
