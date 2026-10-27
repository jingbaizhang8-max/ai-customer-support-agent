from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
from app.models.ticket_review import TicketReview

ALLOWED_DECISIONS = {
    "approved",
    "rejected",
}

def review_ticket(
        db: Session,
        *,
        ticket_id: str,
        authenticated_reviewer_id: str,
        decision: str,
        reason: str,
) -> TicketReview:
    # 1. Validate input
    if(
        not isinstance(authenticated_reviewer_id, str)
        or not authenticated_reviewer_id.strip()
        or len(authenticated_reviewer_id) > 64
    ):
        raise ValueError("reviewer_required")

    if decision not in ALLOWED_DECISIONS:
        raise ValueError("invalid_reason")

    reason = reason.strip()

    if not reason or len(reason) > 2000:
        raise ValueError("invalid_reason")

    try:
        # 2. Lock the ticket row
        stmt = (
            select(Ticket).where(Ticket.ticket_id==ticket_id).with_for_update()
        )

        ticket = db.scalar(stmt)

        if ticket is None:
            raise ValueError("ticket_not_found")

        # 3. Allow only pending tickets to be reviewed
        if ticket.status != "pending_review":
            raise ValueError("ticket_not_pending")

        # 4. Update the ticket status
        ticket.status = decision

        # 5. Create the audit record
        review = TicketReview(
            ticket_id = ticket.ticket_id,
            reviewer_id=authenticated_reviewer_id,
            decision=decision,
            reason=reason,
        )

        db.add(review)

        # 6. Flush both changes, then commit atomically
        db.flush()
        db.commit()

        return review

    except Exception:
        db.rollback()
        raise
