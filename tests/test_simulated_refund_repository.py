
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.repositories.simulated_refund_repository import (
    simulate_refund,
)


TICKET_ID = "12641446-8778-4a0e-9859-c3075fec0747"


def make_ticket(status="approved"):
    return SimpleNamespace(
        ticket_id=TICKET_ID,
        order_id="ORD-1001",
        ticket_type="refund_request",
        status=status,
    )


def test_pending_ticket_cannot_refund():
    db = MagicMock()

    # 第一次查询：找到工单
    # 第二次查询：没有已有退款记录
    db.scalar.side_effect = [
        make_ticket("pending_review"),
        None,
    ]

    with pytest.raises(
        ValueError,
        match="ticket_not_approved",
    ):
        simulate_refund(
            db,
            ticket_id=TICKET_ID,
            authenticated_reviewer_id="reviewer001",
        )

    db.add.assert_not_called()


def test_same_ticket_is_idempotent():
    db = MagicMock()

    existing_refund = SimpleNamespace(
        refund_id="existing-refund-001",
        ticket_id=TICKET_ID,
        order_id="ORD-1001",
        status="simulated_refund_completed",
    )

    db.scalar.side_effect = [
        make_ticket(),
        existing_refund,
    ]

    result = simulate_refund(
        db,
        ticket_id=TICKET_ID,
        authenticated_reviewer_id="reviewer001",
    )

    assert result is existing_refund
    assert result.refund_id == "existing-refund-001"

    # 不应该再次插入数据库
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_same_order_cannot_refund_twice():
    db = MagicMock()

    approved_review = SimpleNamespace(
        decision="approved",
    )

    existing_order_refund = SimpleNamespace(
        refund_id="other-refund-001",
        order_id="ORD-1001",
    )

    db.scalar.side_effect = [
        make_ticket(),
        None,
        approved_review,
        existing_order_refund,
    ]

    with pytest.raises(
        ValueError,
        match="order_already_simulated_refunded",
    ):
        simulate_refund(
            db,
            ticket_id=TICKET_ID,
            authenticated_reviewer_id="reviewer001",
        )

    db.add.assert_not_called()


def test_approved_ticket_creates_refund():
    db = MagicMock()

    approved_review = SimpleNamespace(
        decision="approved",
    )

    db.scalar.side_effect = [
        make_ticket(),
        None,
        approved_review,
        None,
    ]

    result = simulate_refund(
        db,
        ticket_id=TICKET_ID,
        authenticated_reviewer_id="reviewer001",
    )

    assert result.ticket_id == TICKET_ID
    assert result.order_id == "ORD-1001"
    assert result.status == "simulated_refund_completed"
    assert result.processed_by == "reviewer001"

    db.add.assert_called_once_with(result)
    db.flush.assert_called_once()
    db.refresh.assert_called_once_with(result)
