from uuid import uuid4

from sqlalchemy import (
CheckConstraint,
DateTime,
ForeignKey,
String,
Text,
func,
)
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import Index

from app.core.database import Base
from app.models.order import Order

class Ticket(Base):
    __tablename__ = "tickets"

    __table_args__ = (
        CheckConstraint(
            "ticket_type IN ('refund_request','shipping_issue','general_inquiry')",
            name="ck_tickets_type",
        ),
        CheckConstraint(
          "status IN ('pending_review','approved','rejected','closed')",
            name="ck_tickets_status",
        ),
        Index(
            "ux_tickets_customer_id_idempotency_key",
            "customer_id",
            "idempotency_key",
            unique=True,
        ),
    )

    ticket_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    customer_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(f"{Order.__tablename__}.order_id"),
        nullable=False,
        index=True,
    )

    ticket_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    idempotency_key: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending_review",
    )

    created_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )