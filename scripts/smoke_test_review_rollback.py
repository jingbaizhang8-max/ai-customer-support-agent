from uuid import uuid4

from sqlalchemy import delete, event, func, select

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
                description="Day 25 rollback test.",
                idempotency_key=str(uuid4()),
            )

            assert ticket is not None
            ticket_id = ticket.ticket_id

            print("1. Pending ticket created: PASSED")

        # 2. Simulate an error before inserting
        # the review audit record.
        def fail_audit_insert(mapper, connection, target):
            if target.ticket_id == ticket_id:
                raise RuntimeError(
                    "simulated_audit_insert_failure"
                )

        event.listen(
            TicketReview,
            "before_insert",
            fail_audit_insert,
        )

        try:
            with SessionLocal() as db:
                try:
                    review_ticket(
                        db,
                        ticket_id=ticket_id,
                        authenticated_reviewer_id="TEST-REVIEWER-001",
                        decision="approved",
                        reason="Rollback test.",
                    )
                except RuntimeError as exc:
                    assert (
                        str(exc)
                        == "simulated_audit_insert_failure"
                    )
                    print("2. Simulated failure caught: PASSED")
                else:
                    raise AssertionError(
                        "Expected review failure"
                    )
        finally:
            event.remove(
                TicketReview,
                "before_insert",
                fail_audit_insert,
            )

        # 3. Verify state in a new session.
        with SessionLocal() as db:
            saved_ticket = db.get(Ticket, ticket_id)

            review_count = db.scalar(
                select(func.count())
                .select_from(TicketReview)
                .where(TicketReview.ticket_id == ticket_id)
            )

            assert saved_ticket is not None
            assert saved_ticket.status == "pending_review"
            assert review_count == 0

            print("3. Ticket status rolled back: PASSED")
            print("4. No audit record created: PASSED")

    finally:
        # Clean up only this test's temporary data.
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