from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.order import Order


def get_order_by_id(
    db: Session,
    order_id: str,
) -> Order | None:

    return db.get(Order, order_id)

def get_order_for_customer(
        db: Session,
        order_id: str,
        customer_id: str,
) -> Order | None:

    stmt = select(Order).where(
        Order.order_id == order_id,
        Order.customer_id == customer_id,
    )

    return db.scalar(stmt)