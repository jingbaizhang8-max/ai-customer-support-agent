from typing import Literal
from uuid import UUID

from datetime import datetime
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
)
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.reviewer_auth import (
    get_authenticated_reviewer_id,
)
from app.repositories.ticket_review_repository import (
    review_ticket,
    list_pending_refund_tickets,
)

router = APIRouter()

class ReviewRequest(BaseModel):
    model_config =  ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]

    reason: str = Field(
        max_length=2000,
        min_length=1,
    )

class PendingRefundTicket(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: str
    customer_id: str
    order_id: str
    description: str
    status: str
    created_at: datetime

@router.get("/pending", response_model = list[PendingRefundTicket],)
def get_pending_refund_tickets(
        limit: int = Query(default=50, ge=1, le=100),
        reviewer_id: str = Depends(
            get_authenticated_reviewer_id
        ),
        db: Session = Depends(get_db),
):
    return list_pending_refund_tickets(
        db,
        limit=limit,
    )

@router.post("/{ticket_id}")
def submit_review(
        ticket_id: UUID,
        request: ReviewRequest,
        reviewer_id: str = Depends(get_authenticated_reviewer_id),
        db: Session = Depends(get_db),
):
    try:
        review = review_ticket(
            db,
            ticket_id=str(ticket_id),
            authenticated_reviewer_id=reviewer_id,
            decision=request.decision,
            reason=request.reason,
        )

    except ValueError as exc:
        error = str(exc)

        if error == "ticket_not_found":
            raise HTTPException(
                status_code=404,
                detail="ticket_not_found",
            ) from exc

        if error == "ticket_not_pending":
            raise HTTPException(
                status_code=409,
                detail="ticket_not_pending",
            ) from exc

        raise HTTPException(
            status_code=400,
            detail="invalid_review_request",
        ) from exc

    return {
            "review_id": review.review_id,
            "ticket_id": review.ticket_id,
            "reviewer_id": review.reviewer_id,
            "decision": review.decision,
            "reason": review.reason,
    }
