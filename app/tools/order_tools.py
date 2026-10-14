from app.core.database import SessionLocal
from app.repositories.order_repository import get_order_by_id
from app.repositories.shipment_repository import get_shipment_by_order_id


def get_order(order_id: str) -> dict | None:
    with SessionLocal() as db:
        order = get_order_by_id(db, order_id)

        if order is None:
            return None

        shipment = get_shipment_by_order_id(db, order_id)

        return {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "status": order.status,
            "total_amount": float(order.total_amount),
            "currency": order.currency,
            "shipping_status": (
                shipment.shipping_status
                if shipment is not None
                else None
            ),
        }