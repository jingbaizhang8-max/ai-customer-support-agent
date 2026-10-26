from sqlalchemy import text
from app.core.database import engine

def main():
    if engine.url.database != "ai_customer_support_db":
        raise RuntimeError("Unexpected database")

    with engine.begin() as conn:
        conn.execute(
            text(
                "ALTER TABLE tickets "
                "ADD COLUMN IF NOT EXISTS "
                "idempotency_key VARCHAR(64)"
            )
        )

        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ux_tickets_customer_id_idempotency_key "
                "ON tickets (customer_id, idempotency_key)"
            )
        )

        print("Ticket idempotency migration completed")

if __name__ == "__main__":
    main()