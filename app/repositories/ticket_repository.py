from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.ticket import Ticket
from app.repositories.order_repository import get_order_for_customer

ALLOWED_TICKET_TYPES = {
    "refund_request",
    "shipping_issue",
    "general_inquiry",
}


def create_ticket_for_customer(
    db: Session,
    *,
    order_id: str,
    authenticated_customer_id: str,
    ticket_type: str,
    description: str,
    idempotency_key: str,
) -> Ticket | None:

    # 1. Validate inputs.
    if not authenticated_customer_id:
        raise ValueError("authentication_required")

    if ticket_type not in ALLOWED_TICKET_TYPES:
        raise ValueError("invalid_ticket_type")

    if not isinstance(description, str):
        raise ValueError("invalid_description")

    description = description.strip()

    if not description or len(description) > 2000:
        raise ValueError("invalid_description")

    if (
        not isinstance(idempotency_key, str)
        or not 1 <= len(idempotency_key) <= 64
        or idempotency_key != idempotency_key.strip()
    ):
        raise ValueError("invalid_idempotency_key")

    # 2. Verify order ownership BEFORE accessing tickets.
    order = get_order_for_customer(
        db,
        order_id,
        authenticated_customer_id,
    )

    if order is None:
        return None

    # 3. Find an existing ticket with the same key.
    def find_existing_ticket():
        stmt = select(Ticket).where(
            Ticket.customer_id == authenticated_customer_id,
            Ticket.idempotency_key == idempotency_key,
        )
        return db.scalar(stmt)

    def check_same_request(existing: Ticket):
        if (
            existing.order_id != order_id
            or existing.ticket_type != ticket_type
            or existing.description != description
        ):
            raise ValueError("idempotency_key_conflict")

        return existing

    existing = find_existing_ticket()

    if existing is not None:
        return check_same_request(existing)

    # 4. Create a new ticket.
    ticket = Ticket(
        customer_id=authenticated_customer_id,
        order_id=order_id,
        ticket_type=ticket_type,
        description=description,
        idempotency_key=idempotency_key,
        status="pending_review",
    )

    try:
        db.add(ticket)
        db.commit()
        db.refresh(ticket)
        return ticket

    except IntegrityError:
        # A concurrent request may have inserted the same key.
        db.rollback()

        existing = find_existing_ticket()

        if existing is None:
            raise

        return check_same_request(existing)

    except Exception:
        db.rollback()
        raise


def get_ticket_for_customer(
        db: Session,
        *,
        ticket_id: str,
        authenticated_customer_id: str,
) -> Ticket | None:
    stmt = select(Ticket).where(
        Ticket.ticket_id == ticket_id,
        Ticket.customer_id == authenticated_customer_id,
    )

    return db.scalar(stmt)