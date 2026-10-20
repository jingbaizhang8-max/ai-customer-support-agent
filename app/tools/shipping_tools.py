from app.core.database import SessionLocal
from app.repositories.order_repository import get_order_by_id
from app.repositories.shipment_repository import get_shipment_by_order_id
from app.repositories.order_repository import get_order_for_customer

def get_shipping_status(order_id: str) -> dict | None:
    with SessionLocal() as db:
        order = get_order_by_id(db,order_id)

        if order is None:
            return None

        shipment = get_shipment_by_order_id(db, order_id)

        if shipment is None:
            return {
                "order_id": order_id,
                "shipping_status": None,
                "carrier": None,
                "tracking_number": None,
            }

        return {
            "order_id": order_id,
            "shipping_status": shipment.shipping_status,
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
        }

def get_shipping_status_for_authenticated_customer(
        order_id: str,
        authenticated_customer_id: str,
) -> dict | None:

    with SessionLocal() as db:
        order = get_order_for_customer(
            db,
            order_id,
            authenticated_customer_id,
        )

        #先查归属，再查物流
        if order is None:
            return None

        shipment = get_shipment_by_order_id(
            db,
            order_id,
        )

        if shipment is None:
            return {
                "order_id": order_id,
                "shipping_status": None,
                "carrier": None,
                "tracking_number": None,
            }

        return {
            "order_id": order_id,
            "shipping_status": shipment.shipping_status,
            "carrier": shipment.carrier,
            "tracking_number": shipment.tracking_number,
        }