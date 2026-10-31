
-- Day 34: simulated refund records
-- No real payment or money transfer.

CREATE TABLE IF NOT EXISTS simulated_refunds (
    refund_id VARCHAR(36) PRIMARY KEY,

    ticket_id VARCHAR(36) NOT NULL UNIQUE
        REFERENCES tickets(ticket_id),

    order_id VARCHAR(36) NOT NULL UNIQUE
        REFERENCES orders(order_id),

    status VARCHAR(32) NOT NULL
        DEFAULT 'simulated_refund_completed',

    processed_by VARCHAR(64) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_simulated_refund_status
        CHECK (status = 'simulated_refund_completed')
);

COMMENT ON TABLE simulated_refunds IS
'Demo-only simulated refunds. No real funds are transferred.';
