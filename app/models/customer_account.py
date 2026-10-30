from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

# 这里导入 app/models/ticket.py 使用的同一个 Base
# 请复制 Ticket 模型中的 Base 导入语句
from app.models.ticket import Base

class CustomerAccount(Base):
    __tablename__ = "customer_accounts"

    customer_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=true(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


Index(
    "ux_customer_accounts_email",
    func.lower(CustomerAccount.__table__.c.email),
    unique=True,
)
