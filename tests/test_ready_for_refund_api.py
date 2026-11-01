
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.core.reviewer_auth import (
    get_authenticated_reviewer_id,
)


@pytest.fixture
def reviewer_client():
    previous = app.dependency_overrides.copy()

    mock_db = MagicMock()

    app.dependency_overrides[
        get_authenticated_reviewer_id
    ] = lambda: "reviewer001"

    app.dependency_overrides[
        get_db
    ] = lambda: mock_db

    try:
        with TestClient(app) as client:
            yield client, mock_db
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_ready_queue_returns_approved_ticket(reviewer_client):
    client, mock_db = reviewer_client

    ticket = SimpleNamespace(
        ticket_id="test-ticket-001",
        order_id="ORD-1002",
        customer_id="CUS-002",
        ticket_type="refund_request",
        status="approved",
        description="Day 35 test refund",
        created_at=datetime.now(timezone.utc),
    )

    mock_db.scalars.return_value.all.return_value = [ticket]

    response = client.get("/reviews/ready-for-refund")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["order_id"] == "ORD-1002"
    assert data[0]["status"] == "approved"
    assert data[0]["customer_id"] == "CUS-002"


def test_ready_queue_returns_empty_list(reviewer_client):
    client, mock_db = reviewer_client

    mock_db.scalars.return_value.all.return_value = []

    response = client.get("/reviews/ready-for-refund")

    assert response.status_code == 200
    assert response.json() == []


def test_ready_queue_rejects_invalid_limit(reviewer_client):
    client, _ = reviewer_client

    response = client.get(
        "/reviews/ready-for-refund?limit=101"
    )

    assert response.status_code == 422
