
from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Shipment(Base):
    __tablename__ = "shipments"

    order_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("orders.order_id"),
        primary_key=True,
    )

    shipping_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    carrier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
