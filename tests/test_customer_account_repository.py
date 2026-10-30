
import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.passwords import (
    hash_password,
    verify_password,
)
from app.models.customer_account import CustomerAccount
from app.repositories.customer_account_repository import (
    create_customer_account,
    get_customer_by_email,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")

    CustomerAccount.__table__.create(engine)

    with Session(engine) as session:
        yield session

    engine.dispose()


def test_create_customer_account(db):
    hashed = hash_password("StrongPassword2026!")

    account = create_customer_account(
        db,
        email="Test@Example.com",
        password_hash=hashed,
    )

    assert account.customer_id.startswith("CUS-")
    assert account.email == "test@example.com"
    assert account.password_hash != "StrongPassword2026!"

    assert verify_password(
        "StrongPassword2026!",
        account.password_hash,
    )


def test_find_customer_by_email(db):
    create_customer_account(
        db,
        email="test@example.com",
        password_hash=hash_password("StrongPassword2026!"),
    )

    account = get_customer_by_email(
        db,
        "TEST@EXAMPLE.COM",
    )

    assert account is not None
    assert account.email == "test@example.com"


def test_duplicate_email_is_rejected(db):
    create_customer_account(
        db,
        email="test@example.com",
        password_hash=hash_password("StrongPassword2026!"),
    )

    with pytest.raises(
        ValueError,
        match="email_already_registered",
    ):
        create_customer_account(
            db,
            email="TEST@example.com",
            password_hash=hash_password("AnotherStrongPassword2026!"),
        )
