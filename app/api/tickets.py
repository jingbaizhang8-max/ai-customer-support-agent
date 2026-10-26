from typing import Literal
from uuid import UUID

from fastapi import (
APIRouter,
Depends,
Header,
HTTPException,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.agent import get_authenticated_customer_id
from app.core.database import get_db
from app.repositories.ticket_repository import (
create_ticket_for_customer,
get_ticket_for_customer,
)

router = APIRouter()

class CreateTicketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str = Field(
        pattern=r"^(?:ORD-\d{4}|[0-9a-f]{32})$"
    )

    ticket_type: Literal[
        "refund_request",
        "shipping_issue",
        "general_inquiry",
    ]

    description: str = Field(
        min_length=1,
        max_length=2000,
    )

    confirmed: Literal[True]

def serialize_ticket(ticket):
    return {
        "ticket_id": ticket.ticket_id,
        "order_id": ticket.order_id,
        "ticket_type": ticket.ticket_type,
        "description": ticket.description,
        "status": ticket.status,
        "created_at": (
            ticket.created_at.isoformat()
            if ticket.created_at else None
        ),
    }

@router.post("")
def create_ticket(
        request: CreateTicketRequest,
        idempotency_key: str = Header(
            min_length=1,
            max_length=64,
            alias="Idempotency-Key",
        ),
        customer_id: str = Depends(
            get_authenticated_customer_id
        ),
        db: Session = Depends(get_db),
):
    try:
        ticket = create_ticket_for_customer(
            db,
            order_id=request.order_id,
            authenticated_customer_id=customer_id,
            ticket_type=request.ticket_type,
            description=request.description,
            idempotency_key=idempotency_key,
        )

    except ValueError as exc:
        error = str(exc)

        if error == "idempotency_key_conflict":
            raise HTTPException(
                status_code=409,
                detail=error,
            ) from exc

        raise HTTPException(
            status_code=400,
            detail=error,
        ) from exc

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="order_not_found",
        )

    return serialize_ticket(ticket)

@router.get("/{ticket_id}")
def read_ticket(
        ticket_id: UUID,
        customer_id: str = Depends(
            get_authenticated_customer_id
        ),
        db: Session = Depends(get_db),
):
    ticket = get_ticket_for_customer(
        db,
        ticket_id=str(ticket_id),
        authenticated_customer_id=customer_id,
    )

    if ticket is None:
        raise HTTPException(
            status_code=404,
            detail="ticket_not_found",
        )

    return serialize_ticket(ticket)