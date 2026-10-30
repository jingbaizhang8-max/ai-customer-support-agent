import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.customer_account import CustomerAccount


def get_customer_by_email(
    db: Session,
    email: str,
) -> CustomerAccount | None:
    normalized_email = email.strip().lower()

    statement = select(CustomerAccount).where(
        func.lower(CustomerAccount.email) == normalized_email
    )

    return db.scalar(statement)


def create_customer_account(
    db: Session,
    *,
    email: str,
    password_hash: str,
) -> CustomerAccount:
    normalized_email = email.strip().lower()

    account = CustomerAccount(
        customer_id=f"CUS-{uuid.uuid4().hex}",
        email=normalized_email,
        password_hash=password_hash,
        is_active=True,
    )

    db.add(account)

    try:
        db.commit()
        db.refresh(account)
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("email_already_registered") from exc

    return account