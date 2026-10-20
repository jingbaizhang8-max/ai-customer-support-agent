from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from app.tools import order_tools, shipping_tools


@pytest.fixture(autouse=True)
def mock_order_database(monkeypatch):
    orders = {
        "ORD-1001": SimpleNamespace(
            order_id="ORD-1001",
            customer_id="CUS-001",
            status="shipped",
            total_amount=89.99,
            currency="USD",
        ),
        "ORD-1002": SimpleNamespace(
            order_id="ORD-1002",
            customer_id="CUS-002",
            status="paid",
            total_amount=149.50,
            currency="USD",
        ),
    }

    shipments = {
        "ORD-1001": SimpleNamespace(
            shipping_status="in_transit",
            carrier="Demo Express",
            tracking_number="DEMO-TRACK-1001",
        ),
        "ORD-1002": SimpleNamespace(
            shipping_status="not_shipped",
            carrier=None,
            tracking_number=None,
        ),
    }

    def fake_get_order(db, order_id):
        return orders.get(order_id)

    def fake_get_order_for_customer(db, order_id, customer_id):
        order = orders.get(order_id)

        if order is None:
            return None

        if order.customer_id != customer_id:
            return None

        return order
    def fake_get_shipment(db, order_id):
        return shipments.get(order_id)

    monkeypatch.setattr(
        order_tools, "SessionLocal", lambda: nullcontext()
    )
    monkeypatch.setattr(
        shipping_tools, "SessionLocal", lambda: nullcontext()
    )

    monkeypatch.setattr(
        order_tools, "get_order_by_id", fake_get_order
    )
    monkeypatch.setattr(
        shipping_tools, "get_order_by_id", fake_get_order
    )

    monkeypatch.setattr(
        order_tools, "get_shipment_by_order_id", fake_get_shipment
    )
    monkeypatch.setattr(
        shipping_tools, "get_shipment_by_order_id", fake_get_shipment
    )
    monkeypatch.setattr(
        order_tools,
        "get_order_for_customer",
        fake_get_order_for_customer,
    )

    monkeypatch.setattr(
        shipping_tools,
        "get_order_for_customer",
        fake_get_order_for_customer,
    )