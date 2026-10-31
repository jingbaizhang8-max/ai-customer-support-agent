
import importlib
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.core.reviewer_auth import get_authenticated_reviewer_id

refunds_api = importlib.import_module("app.api.refunds")

TICKET_ID = "12641446-8778-4a0e-9859-c3075fec0747"


@pytest.fixture
def reviewer_client():
    old_overrides = app.dependency_overrides.copy()

    app.dependency_overrides[
        get_authenticated_reviewer_id
    ] = lambda: "reviewer001"

    app.dependency_overrides[get_db] = lambda: MagicMock()

    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(old_overrides)


def test_refund_requires_reviewer_jwt():
    with TestClient(app) as client:
        response = client.post(
            f"/refunds/simulate/{TICKET_ID}"
        )

    assert response.status_code == 401


def test_refund_rejects_pending_ticket(
    reviewer_client, monkeypatch
):
    def fake_simulate_refund(
            db, *, ticket_id, authenticated_reviewer_id
    ):
        raise ValueError("ticket_not_approved")

    monkeypatch.setattr(
        refunds_api,
        "simulate_refund",
        fake_simulate_refund,
    )

    response = reviewer_client.post(
        f"/refunds/simulate/{TICKET_ID}"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "ticket_not_approved"


def test_refund_success_response(
    reviewer_client, monkeypatch
):
    def fake_simulate_refund(
        db, *, ticket_id, authenticated_reviewer_id
    ):
        assert ticket_id == TICKET_ID
        assert authenticated_reviewer_id == "reviewer001"

        return SimpleNamespace(
            refund_id="test-refund-001",
            ticket_id=ticket_id,
            order_id="ORD-1001",
            status="simulated_refund_completed",
            processed_by=authenticated_reviewer_id,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        refunds_api,
        "simulate_refund",
        fake_simulate_refund,
    )

    response = reviewer_client.post(
        f"/refunds/simulate/{TICKET_ID}"
    )

    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "simulated_refund_completed"
    assert data["order_id"] == "ORD-1001"
    assert data["processed_by"] == "reviewer001"
