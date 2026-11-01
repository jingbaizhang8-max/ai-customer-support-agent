from sqlalchemy import select

from app.core.database import get_db
from app.models.simulated_refund import SimulatedRefund
from app.tools.order_tools import (
    get_order_for_authenticated_customer,
)


def prepare_refund_request(
    order_id: str,
    reason: str,
    authenticated_customer_id: str,
) -> dict | None:
    """
    Prepare a refund request draft.
    Read-only: never creates a ticket or executes a refund.
    """

    order = get_order_for_authenticated_customer(
        order_id=order_id,
        authenticated_customer_id=authenticated_customer_id,
    )

    if order is None:
        return None


    # 只有通过订单归属校验后，才能查询退款状态
    db_generator = get_db()
    db = next(db_generator)

    try:
        existing_refund = db.scalar(
            select(SimulatedRefund.refund_id).where(
                SimulatedRefund.order_id == order["order_id"]
            )
        )
    finally:
        db_generator.close()

    if existing_refund is not None:
        return {
            "action": "refund_request_unavailable",
            "order_id": order["order_id"],
            "reason": "order_already_simulated_refunded",
            "requires_customer_confirmation": False,
        }


    return {
        "action": "refund_request_draft",
        "order_id": order["order_id"],
        "ticket_type": "refund_request",
        "description": reason.strip(),
        "requires_customer_confirmation": True,
    }
