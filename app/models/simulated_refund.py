
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SimulatedRefund(Base):
    __tablename__ = "simulated_refunds"

    __table_args__ = (
        CheckConstraint(
            "status = 'simulated_refund_completed'",
            name="ck_simulated_refund_status",
        ),
    )

    refund_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    ticket_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tickets.ticket_id"),
        unique=True,
        nullable=False,
    )

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.order_id"),
        unique=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="simulated_refund_completed",
        server_default="simulated_refund_completed",
    )

    processed_by: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
