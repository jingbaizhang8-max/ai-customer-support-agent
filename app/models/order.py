from sqlalchemy import String, Numeric
from sqlalchemy.orm import Mapped,mapped_column

from app.core.database import Base

class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    customer_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    total_amount: Mapped[float] = mapped_column(
        Numeric(10, 2, asdecimal=False),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )