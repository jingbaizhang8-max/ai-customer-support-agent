from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
CheckConstraint,
DateTime,
ForeignKey,
String,
Text,
UniqueConstraint,
func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.ticket import Ticket

class TicketReview(Base):
    __tablename__ = "ticket_reviews"

    __table_args__ = (
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_ticket_reviews_decision",
        ),
        UniqueConstraint(
            "ticket_id",
            name="uq_ticket_reviews_ticket_id",
        ),
    )

    review_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda : str(uuid4()),
    )

    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(f"{Ticket.__tablename__}.ticket_id"),
        nullable=False,
        index=True,
    )

    reviewer_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

