from uuid import uuid4
from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models.ticket import Ticket
from app.repositories.ticket_repository import (
    create_ticket_for_customer,
    get_ticket_for_customer,
)


def main():
    ticket_id = None
    test_key = str(uuid4())

    try:
        # 1. CUS-001 creates a ticket for their own order.
        with SessionLocal() as db:
            ticket = create_ticket_for_customer(
                db,
                order_id="ORD-1001",
                authenticated_customer_id="CUS-001",
                ticket_type="refund_request",
                description="Day 24 test: request manual refund review.",
                idempotency_key=test_key,
            )

            assert ticket is not None
            assert ticket.status == "pending_review"

            ticket_id = ticket.ticket_id

            print("1. Authorized creation: PASSED")
            print("Ticket ID:", ticket_id)

            # Retry the exact same request using the same key.
            retried_ticket = create_ticket_for_customer(
                db,
                order_id="ORD-1001",
                authenticated_customer_id="CUS-001",
                ticket_type="refund_request",
                description="Day 24 test: request manual refund review.",
                idempotency_key=test_key,
            )

            assert retried_ticket is not None
            assert retried_ticket.ticket_id == ticket_id

            print("5. Idempotent retry: PASSED")

            # 6. Same idempotency key but different request content.
            try:
                create_ticket_for_customer(
                    db,
                    order_id="ORD-1001",
                    authenticated_customer_id="CUS-001",
                    ticket_type="shipping_issue",
                    description="My package has not arrived.",
                    idempotency_key=test_key,
                )
            except ValueError as exc:
                assert str(exc) == "idempotency_key_conflict"
            else:
                raise AssertionError(
                    "Different request with the same key was accepted"
                )

            print("6. Idempotency key conflict rejected: PASSED")

            # 7. Verify that only one ticket exists for this key.
            ticket_count = db.scalar(
                select(func.count())
                .select_from(Ticket)
                .where(
                    Ticket.customer_id == "CUS-001",
                    Ticket.idempotency_key == test_key,
                )
            )

            assert ticket_count == 1

            print("7. No duplicate ticket created: PASSED")

            # 2. CUS-002 tries to create a ticket
            # for CUS-001's order.
            denied = create_ticket_for_customer(
                db,
                order_id="ORD-1001",
                authenticated_customer_id="CUS-002",
                ticket_type="refund_request",
                description="Unauthorized test request.",
                idempotency_key=str(uuid4())
            )

            assert denied is None
            print("2. Unauthorized creation blocked: PASSED")

        # Use a NEW database session to verify persistence.
        with SessionLocal() as db:
            # 3. Owner can read the saved ticket.
            saved_ticket = get_ticket_for_customer(
                db,
                ticket_id=ticket_id,
                authenticated_customer_id="CUS-001",
            )

            assert saved_ticket is not None
            assert saved_ticket.status == "pending_review"
            print("3. Owner can read saved ticket: PASSED")

            # 4. Another customer cannot read the ticket.
            forbidden = get_ticket_for_customer(
                db,
                ticket_id=ticket_id,
                authenticated_customer_id="CUS-002",
            )

            assert forbidden is None
            print("4. Unauthorized read blocked: PASSED")

    finally:
        # Remove only the ticket created by this test.
        if ticket_id is not None:
            with SessionLocal() as db:
                test_ticket = db.get(Ticket, ticket_id)

                if test_ticket is not None:
                    db.delete(test_ticket)
                    db.commit()
                    print("Test ticket cleaned up")


if __name__ == "__main__":
    main()