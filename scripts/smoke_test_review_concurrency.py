from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import delete, func, select

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

    # Synchronize two reviewer requests.
    barrier = Barrier(2)

    def reviewer_worker(reviewer_id, decision):
        barrier.wait(timeout=10)

        with SessionLocal() as db:
            try:
                review = review_ticket(
                    db,
                    ticket_id=ticket_id,
                    authenticated_reviewer_id=reviewer_id,
                    decision=decision,
                    reason="Day 25 concurrency test.",
                )

                return ("success", review.decision)

            except ValueError as exc:
                if str(exc) != "ticket_not_pending":
                    raise

                return ("blocked", str(exc))

    try:
        # 1. Create one pending ticket.
        with SessionLocal() as db:
            ticket = create_ticket_for_customer(
                db,
                order_id="ORD-1001",
                authenticated_customer_id="CUS-001",
                ticket_type="refund_request",
                description="Concurrent review test.",
                idempotency_key=str(uuid4()),
            )

            assert ticket is not None
            ticket_id = ticket.ticket_id

            print("1. Pending ticket created: PASSED")

        # 2. Submit two reviewer requests concurrently.
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_a = pool.submit(
                reviewer_worker,
                "TEST-REVIEWER-A",
                "approved",
            )

            future_b = pool.submit(
                reviewer_worker,
                "TEST-REVIEWER-B",
                "rejected",
            )

            results = [
                future_a.result(),
                future_b.result(),
            ]

        print("Reviewer results:", results)

        # 3. Exactly one decision must succeed.
        assert sum(
            result[0] == "success"
            for result in results
        ) == 1

        assert sum(
            result[0] == "blocked"
            for result in results
        ) == 1

        print("2. Only one reviewer succeeded: PASSED")

        # 4. Database state must be consistent.
        with SessionLocal() as db:
            saved_ticket = db.get(Ticket, ticket_id)

            saved_review = db.scalar(
                select(TicketReview).where(
                    TicketReview.ticket_id == ticket_id
                )
            )

            review_count = db.scalar(
                select(func.count())
                .select_from(TicketReview)
                .where(TicketReview.ticket_id == ticket_id)
            )

            assert saved_ticket is not None
            assert saved_review is not None
            assert review_count == 1
            assert saved_ticket.status == saved_review.decision

            print("3. Database consistency: PASSED")
            print("Final decision:", saved_ticket.status)

    finally:
        # Clean only this test's temporary ticket.
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