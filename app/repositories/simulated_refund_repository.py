
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_review import TicketReview
from app.models.simulated_refund import SimulatedRefund


def simulate_refund(
    db: Session,
    *,
    ticket_id: str,
    authenticated_reviewer_id: str,
) -> SimulatedRefund:

    try:
        with db.begin():
            # 1. 锁定工单，防止同一工单并发处理
            ticket = db.scalar(
                select(Ticket)
                .where(Ticket.ticket_id == ticket_id)
                .with_for_update()
            )

            if ticket is None:
                raise ValueError("ticket_not_found")

            if ticket.ticket_type != "refund_request":
                raise ValueError("not_refund_request")

            # 2. 同一工单重复请求，返回已有结果
            existing = db.scalar(
                select(SimulatedRefund).where(
                    SimulatedRefund.ticket_id == ticket_id
                )
            )

            if existing is not None:
                return existing

            # 3. 必须已经通过人工审核
            if ticket.status != "approved":
                raise ValueError("ticket_not_approved")

            approved_review = db.scalar(
                select(TicketReview).where(
                    TicketReview.ticket_id == ticket_id,
                    TicketReview.decision == "approved",
                )
            )

            if approved_review is None:
                raise ValueError("approved_review_not_found")

            # 4. 防止同一订单通过不同工单重复退款
            existing_order_refund = db.scalar(
                select(SimulatedRefund).where(
                    SimulatedRefund.order_id == ticket.order_id
                )
            )

            if existing_order_refund is not None:
                raise ValueError(
                    "order_already_simulated_refunded"
                )

            # 5. 创建模拟退款记录
            refund = SimulatedRefund(
                refund_id=str(uuid4()),
                ticket_id=ticket.ticket_id,
                order_id=ticket.order_id,
                status="simulated_refund_completed",
                processed_by=authenticated_reviewer_id,
            )

            db.add(refund)
            db.flush()

        # 退出 with 后事务成功提交
        db.refresh(refund)
        return refund

    except IntegrityError as exc:
        # 数据库唯一约束冲突后，事务已回滚
        # 重新查询，区分幂等重试和重复订单
        existing = db.scalar(
            select(SimulatedRefund).where(
                SimulatedRefund.ticket_id == ticket_id
            )
        )

        if existing is not None:
            return existing

        # 并发情况下，另一张工单可能已处理该订单
        if "ticket" in locals():
            order_refund = db.scalar(
                select(SimulatedRefund).where(
                    SimulatedRefund.order_id == ticket.order_id
                )
            )

            if order_refund is not None:
                raise ValueError(
                    "order_already_simulated_refunded"
                ) from exc

        raise