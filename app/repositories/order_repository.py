from sqlalchemy.orm import Session

from app.models.order import Order


def get_order_by_id(
    db: Session,
    order_id: str,
) -> Order | None:

    return db.get(Order, order_id)