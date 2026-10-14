from app.core.database import SessionLocal
from app.models.order import Order
from app.models.shipment import Shipment

def seed_data():
    with SessionLocal.begin() as db:
        orders = [
            Order(
                order_id="ORD-1001",
                customer_id="CUS-001",
                status="shipped",
                total_amount=89.99,
                currency="USD",

            ),
            Order(
                order_id="ORD-1002",
                customer_id="CUS-002",
                status="paid",
                total_amount=149.50,
                currency="USD",
            ),
        ]

        for order in orders:
            if db.get(Order, order.order_id) is None:
                db.add(order)

        db.flush()

        shipments = [
            Shipment(
                order_id="ORD-1001",
                shipping_status="in_transit",
                carrier="Demo Express",
                tracking_number="DEMO-TRACK-1001",
            ),
            Shipment(
                order_id="ORD-1002",
                shipping_status="not_shipped",
                carrier=None,
                tracking_number=None,
            ),
        ]

        for shipment in shipments:
            if db.get(Shipment, shipment.order_id) is None:
                db.add(shipment)

    print("Demo orders and shipments are ready.")

if __name__ == "__main__":
    seed_data()