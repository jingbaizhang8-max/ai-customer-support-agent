import pytest

from sqlalchemy import (
    create_engine,
    event,
    select,
    func,
    text,
)
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_review import TicketReview
from app.repositories.ticket_review_repository import (
    review_ticket,
)


@pytest.fixture
def review_db():
    # Isolated SQLite database.
    engine = create_engine("sqlite+pysqlite:///:memory:")

    # Minimal parent table for the foreign key.
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE orders "
                "(order_id VARCHAR(36) PRIMARY KEY)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO orders (order_id) "
                "VALUES ('ORD-1001')"
            )
        )

    Ticket.__table__.create(bind=engine)
    TicketReview.__table__.create(bind=engine)

    with Session(engine) as db:
        ticket = Ticket(
            customer_id="CUS-001",
            order_id="ORD-1001",
            ticket_type="refund_request",
            description="Day 25 review test.",
            idempotency_key="review-test-001",
            status="pending_review",
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.ticket_id

    yield engine, ticket_id

    engine.dispose()


def test_review_updates_status_and_audit(review_db):
    engine, ticket_id = review_db

    with Session(engine) as db:
        review = review_ticket(
            db,
            ticket_id=ticket_id,
            authenticated_reviewer_id="REVIEWER-001",
            decision="approved",
            reason="Test approval.",
        )
        assert review.decision == "approved"

    with Session(engine) as db:
        ticket = db.get(Ticket, ticket_id)
        saved_review = db.scalar(
            select(TicketReview).where(
                TicketReview.ticket_id == ticket_id
            )
        )

        assert ticket.status == "approved"
        assert saved_review is not None
        assert saved_review.reviewer_id == "REVIEWER-001"


def test_duplicate_review_is_rejected(review_db):
    engine, ticket_id = review_db

    with Session(engine) as db:
        review_ticket(
            db,
            ticket_id=ticket_id,
            authenticated_reviewer_id="REVIEWER-001",
            decision="approved",
            reason="First decision.",
        )

    with Session(engine) as db:
        with pytest.raises(
            ValueError,
            match="ticket_not_pending",
        ):
            review_ticket(
                db,
                ticket_id=ticket_id,
                authenticated_reviewer_id="REVIEWER-002",
                decision="rejected",
                reason="Second decision.",
            )

    with Session(engine) as db:
        count = db.scalar(
            select(func.count())
            .select_from(TicketReview)
            .where(TicketReview.ticket_id == ticket_id)
        )
        assert count == 1


def test_review_failure_rolls_back(review_db):
    engine, ticket_id = review_db

    def fail_insert(mapper, connection, target):
        if target.ticket_id == ticket_id:
            raise RuntimeError("simulated_insert_failure")

    event.listen(
        TicketReview,
        "before_insert",
        fail_insert,
    )

    try:
        with Session(engine) as db:
            with pytest.raises(
                RuntimeError,
                match="simulated_insert_failure",
            ):
                review_ticket(
                    db,
                    ticket_id=ticket_id,
                    authenticated_reviewer_id="REVIEWER-001",
                    decision="approved",
                    reason="Rollback test.",
                )
    finally:
        event.remove(
            TicketReview,
            "before_insert",
            fail_insert,
        )

    with Session(engine) as db:
        ticket = db.get(Ticket, ticket_id)

        count = db.scalar(
            select(func.count())
            .select_from(TicketReview)
            .where(TicketReview.ticket_id == ticket_id)
        )

        assert ticket.status == "pending_review"
        assert count == 0