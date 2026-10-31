
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.reviewer_auth import get_authenticated_reviewer_id
from app.repositories.simulated_refund_repository import simulate_refund


router = APIRouter(
    prefix="/refunds",
    tags=["Simulated Refunds"],
)


class SimulatedRefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    refund_id: str
    ticket_id: str
    order_id: str
    status: str
    processed_by: str
    created_at: datetime


@router.post(
    "/simulate/{ticket_id}",
    response_model=SimulatedRefundResponse,
)
def execute_simulated_refund(
    ticket_id: UUID,
    reviewer_id: str = Depends(
        get_authenticated_reviewer_id
    ),
    db: Session = Depends(get_db),
):
    try:
        refund = simulate_refund(
            db,
            ticket_id=str(ticket_id),
            authenticated_reviewer_id=reviewer_id,
        )

        return refund

    except ValueError as exc:
        error = str(exc)

        if error == "ticket_not_found":
            raise HTTPException(
                status_code=404,
                detail=error,
            ) from exc

        if error in {
            "not_refund_request",
            "ticket_not_approved",
            "approved_review_not_found",
            "order_already_simulated_refunded",
        }:
            raise HTTPException(
                status_code=409,
                detail=error,
            ) from exc

        raise HTTPException(
            status_code=400,
            detail="invalid_refund_request",
        ) from exc

    except IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="refund_conflict",
        ) from exc
