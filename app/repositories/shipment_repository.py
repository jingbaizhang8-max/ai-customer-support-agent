
from sqlalchemy.orm import Session

from app.models.shipment import Shipment


def get_shipment_by_order_id(
    db: Session,
    order_id: str,
) -> Shipment | None:

    return db.get(Shipment, order_id)