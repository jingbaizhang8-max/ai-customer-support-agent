
from app.tools.order_tools import get_order
from app.tools import shipping_tools


def test_get_order_not_found():
    result = get_order("ORD-9999")

    assert result is None


def test_shipping_order_not_found():
    result = shipping_tools.get_shipping_status("ORD-9999")

    assert result is None


def test_shipping_record_not_found(monkeypatch):
    monkeypatch.setattr(
        shipping_tools,
        "get_shipment_by_order_id",
        lambda db, order_id: None,
    )

    result = shipping_tools.get_shipping_status("ORD-1001")

    assert result == {
        "order_id": "ORD-1001",
        "shipping_status": None,
        "carrier": None,
        "tracking_number": None,
    }
