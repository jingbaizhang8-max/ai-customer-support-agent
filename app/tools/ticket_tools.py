from app.core.database import SessionLocal
from app.repositories.ticket_repository import get_ticket_for_customer

def get_ticket_for_authenticated_customer(
    ticket_id: str,
    authenticated_customer_id: str,
) -> dict | None:

    with SessionLocal() as db:
        ticket = get_ticket_for_customer(
            db,
            ticket_id=ticket_id,
            authenticated_customer_id=authenticated_customer_id
        )

        if ticket is None:
            return None

        return {
            "ticket_id": ticket.ticket_id,
            "customer_id": ticket.customer_id,
            "order_id": ticket.order_id,
            "ticket_type": ticket.ticket_type,
            "description": ticket.description,
            "status": ticket.status,
            "created_at": (
                ticket.created_at.isoformat()
                if ticket.created_at else None
            ),
            "updated_at": (
                ticket.updated_at.isoformat()
                if ticket.updated_at else None
            ),
        }