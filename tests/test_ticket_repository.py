
import pytest

from sqlalchemy import create_engine, select, func, text
from sqlalchemy.orm import Session

from app.models.ticket import Ticket
import app.repositories.ticket_repository as repo


@pytest.fixture
def db_engine(monkeypatch):
    # Isolated SQLite database, not PostgreSQL.
    engine = create_engine("sqlite+pysqlite:///:memory:")

    # Minimal orders table for the Ticket foreign key.
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE orders "
                "(order_id VARCHAR(36) PRIMARY KEY)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO orders (order_id) "
                "VALUES ('ORD-1001')"
            )
        )

    Ticket.__table__.create(bind=engine)

    # Isolate repository tests from the real order repository.
    def fake_get_order_for_customer(db, order_id, customer_id):
        if order_id == "ORD-1001" and customer_id == "CUS-001":
            return object()
        return None

    monkeypatch.setattr(
        repo,
        "get_order_for_customer",
        fake_get_order_for_customer,
    )

    yield engine
    engine.dispose()


def submit_ticket(
    db,
    key="request-001",
    description="Item arrived damaged.",
    customer_id="CUS-001",
):
    return repo.create_ticket_for_customer(
        db,
        order_id="ORD-1001",
        authenticated_customer_id=customer_id,
        ticket_type="refund_request",
        description=description,
        idempotency_key=key,
    )


def test_create_ticket_and_persist(db_engine):
    with Session(db_engine) as db:
        ticket = submit_ticket(db)
        assert ticket is not None
        assert ticket.status == "pending_review"
        ticket_id = ticket.ticket_id

    # Read using a new Session.
    with Session(db_engine) as db:
        saved = repo.get_ticket_for_customer(
            db,
            ticket_id=ticket_id,
            authenticated_customer_id="CUS-001",
        )

        assert saved is not None
        assert saved.ticket_id == ticket_id


def test_same_key_returns_same_ticket(db_engine):
    with Session(db_engine) as db:
        first = submit_ticket(db)
        second = submit_ticket(db)

        assert first.ticket_id == second.ticket_id

        count = db.scalar(
            select(func.count()).select_from(Ticket)
        )

        assert count == 1


def test_same_key_different_content_rejected(db_engine):
    with Session(db_engine) as db:
        submit_ticket(db)

        with pytest.raises(
            ValueError,
            match="idempotency_key_conflict",
        ):
            submit_ticket(
                db,
                description="Package is missing.",
            )

        count = db.scalar(
            select(func.count()).select_from(Ticket)
        )

        assert count == 1


def test_unauthorized_creation_blocked(db_engine):
    with Session(db_engine) as db:
        result = submit_ticket(
            db,
            customer_id="CUS-002",
        )

        assert result is None

        count = db.scalar(
            select(func.count()).select_from(Ticket)
        )

        assert count == 0


def test_other_customer_cannot_read_ticket(db_engine):
    with Session(db_engine) as db:
        ticket = submit_ticket(db)
        ticket_id = ticket.ticket_id

        denied = repo.get_ticket_for_customer(
            db,
            ticket_id=ticket_id,
            authenticated_customer_id="CUS-002",
        )

        assert denied is None
