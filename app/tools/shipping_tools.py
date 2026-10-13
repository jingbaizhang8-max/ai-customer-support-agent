from app.tools.order_tools import get_order

MOCK_SHIPMENTS = {
    "ORD-1001": {
        "carrier": "Demo Express",
        "tracking_number": "DEMO-TRACK-1001",
    }
}


def get_shipping_status(order_id: str) -> dict | None:
    order = get_order(order_id)

    if order is None:
        return None

    shipment = MOCK_SHIPMENTS.get(order_id,{})

    return {
        "order_id": order_id,
        "shipping_status": order["shipping_status"],
        "carrier": shipment.get("carrier"),
        "tracking_number": shipment.get("tracking_number"),
    }