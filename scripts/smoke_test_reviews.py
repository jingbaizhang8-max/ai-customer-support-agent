
from uuid import uuid4

from sqlalchemy import select, func, delete

from app.core.database import SessionLocal, engine
from app.models.ticket import Ticket
from app.models.ticket_review import TicketReview
from app.repositories.ticket_repository import (
    create_ticket_for_customer,
)
from app.repositories.ticket_review_repository import (
    review_ticket,
)


def main():
    if engine.url.database != "ai_customer_support_db":
        raise RuntimeError("Unexpected database")

    ticket_id = None

    try:
        # 1. Create a temporary pending ticket.
        with SessionLocal() as db:
            ticket = create_ticket_for_customer(
                db,
                order_id="ORD-1001",
                authenticated_customer_id="CUS-001",
                ticket_type="refund_request",
                description="Day 25 manual review test.",
                idempotency_key=str(uuid4()),
            )

            assert ticket is not None
            assert ticket.status == "pending_review"
            ticket_id = ticket.ticket_id

            print("1. Pending ticket created: PASSED")

        # 2. Simulate a trusted reviewer decision.
        with SessionLocal() as db:
            review = review_ticket(
                db,
                ticket_id=ticket_id,
                authenticated_reviewer_id="TEST-REVIEWER-001",
                decision="approved",
                reason="Development test approval only.",
            )

            assert review.decision == "approved"
            assert review.ticket_id == ticket_id

            print("2. Review approved: PASSED")

        # 3. Verify persistence in another session.
        with SessionLocal() as db:
            saved_ticket = db.get(Ticket, ticket_id)

            saved_review = db.scalar(
                select(TicketReview).where(
                    TicketReview.ticket_id == ticket_id
                )
            )

            assert saved_ticket is not None
            assert saved_ticket.status == "approved"

            assert saved_review is not None
            assert saved_review.reviewer_id == "TEST-REVIEWER-001"

            print("3. Status and audit record persisted: PASSED")

        # 4. Reject a second review of the same ticket.
        with SessionLocal() as db:
            try:
                review_ticket(
                    db,
                    ticket_id=ticket_id,
                    authenticated_reviewer_id="TEST-REVIEWER-002",
                    decision="rejected",
                    reason="Second review attempt.",
                )
            except ValueError as exc:
                assert str(exc) == "ticket_not_pending"
            else:
                raise AssertionError(
                    "Duplicate review was accepted"
                )

            print("4. Duplicate review blocked: PASSED")

        # 5. Confirm only one review record exists.
        with SessionLocal() as db:
            count = db.scalar(
                select(func.count())
                .select_from(TicketReview)
                .where(TicketReview.ticket_id == ticket_id)
            )

            assert count == 1

            print("5. Only one review record: PASSED")

    finally:
        # Delete only data created by this smoke test.
        if ticket_id is not None:
            with SessionLocal() as db:
                db.execute(
                    delete(TicketReview).where(
                        TicketReview.ticket_id == ticket_id
                    )
                )

                db.execute(
                    delete(Ticket).where(
                        Ticket.ticket_id == ticket_id
                    )
                )

                db.commit()

            print("Temporary test data cleaned up")


if __name__ == "__main__":
    main()
