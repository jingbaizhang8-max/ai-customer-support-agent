
CREATE TABLE IF NOT EXISTS customer_accounts (
    customer_id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS
    ux_customer_accounts_email
ON customer_accounts (LOWER(email));
