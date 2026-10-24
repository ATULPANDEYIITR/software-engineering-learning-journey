DROP SCHEMA IF EXISTS transaction_lab CASCADE;
CREATE SCHEMA transaction_lab;

SET search_path TO transaction_lab;

-- Accounts are the durable resources modified by transactions.
CREATE TABLE accounts (
    account_id      BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_name      TEXT NOT NULL,
    balance         NUMERIC(14, 2) NOT NULL DEFAULT 0,
    version         BIGINT NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT accounts_owner_not_blank
        CHECK (length(btrim(owner_name)) > 0),

    CONSTRAINT accounts_balance_nonnegative
        CHECK (balance >= 0),

    CONSTRAINT accounts_version_nonnegative
        CHECK (version >= 0)
);

CREATE TABLE customers (
    customer_id     BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name   TEXT NOT NULL UNIQUE
);

CREATE TABLE ledger_transactions (
    transaction_id  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_ref UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    transaction_type TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'ACTIVE',
    isolation_level TEXT NOT NULL DEFAULT 'READ COMMITTED',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    committed_at    TIMESTAMPTZ,

    CONSTRAINT transaction_type_valid
        CHECK (transaction_type IN ('TRANSFER', 'DEPOSIT', 'WITHDRAWAL')),

    CONSTRAINT transaction_status_valid
        CHECK (status IN ('ACTIVE', 'COMMITTED', 'ROLLED_BACK')),

    CONSTRAINT transaction_isolation_valid
        CHECK (
            isolation_level IN (
                'READ UNCOMMITTED',
                'READ COMMITTED',
                'REPEATABLE READ',
                'SERIALIZABLE'
            )
        ),

    CONSTRAINT transaction_commit_timestamp_valid
        CHECK (
            (status = 'COMMITTED' AND committed_at IS NOT NULL)
            OR
            (status <> 'COMMITTED')
        )
);

CREATE TABLE transaction_entries (
    entry_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES ledger_transactions(transaction_id)
        ON DELETE RESTRICT,
    account_id     BIGINT NOT NULL
        REFERENCES accounts(account_id)
        ON DELETE RESTRICT,
    entry_type     TEXT NOT NULL,
    amount         NUMERIC(14, 2) NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT transaction_entry_type_valid
        CHECK (entry_type IN ('DEBIT', 'CREDIT')),

    CONSTRAINT transaction_entry_amount_positive
        CHECK (amount > 0)
);

CREATE INDEX transaction_entries_account_idx
    ON transaction_entries(account_id);

CREATE INDEX transaction_entries_transaction_idx
    ON transaction_entries(transaction_id);

CREATE TABLE transaction_events (
    event_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    transaction_id BIGINT NOT NULL
        REFERENCES ledger_transactions(transaction_id)
        ON DELETE CASCADE,
    event_type     TEXT NOT NULL,
    event_details  JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX transaction_events_transaction_time_idx
    ON transaction_events(transaction_id, occurred_at DESC);

CREATE OR REPLACE FUNCTION prevent_invalid_transaction_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status = 'COMMITTED'
       AND NEW.status <> 'COMMITTED' THEN
        RAISE EXCEPTION
            'Committed transaction % cannot change state',
            OLD.transaction_id;
    END IF;

    IF OLD.status = 'ROLLED_BACK'
       AND NEW.status <> 'ROLLED_BACK' THEN
        RAISE EXCEPTION
            'Rolled-back transaction % cannot change state',
            OLD.transaction_id;
    END IF;

    IF NEW.status = 'COMMITTED'
       AND NEW.committed_at IS NULL THEN
        NEW.committed_at := clock_timestamp();
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER transaction_status_guard
BEFORE UPDATE ON ledger_transactions
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_transaction_status();

INSERT INTO customers (customer_name)
VALUES
    ('Alice'),
    ('Bob'),
    ('Carol');

INSERT INTO accounts (owner_name, balance)
VALUES
    ('Alice', 1000.00),
    ('Bob', 1000.00),
    ('Carol', 1000.00);

-- A transaction is represented by ledger rows plus an explicit status.
INSERT INTO ledger_transactions (
    transaction_type,
    status,
    isolation_level
)
VALUES (
    'TRANSFER',
    'COMMITTED',
    'READ COMMITTED'
);

INSERT INTO transaction_entries (
    transaction_id,
    account_id,
    entry_type,
    amount
)
VALUES
    (1, 1, 'DEBIT', 250.00),
    (1, 2, 'CREDIT', 250.00);

INSERT INTO transaction_events (
    transaction_id,
    event_type,
    event_details
)
VALUES (
    1,
    'COMMIT',
    '{"reason":"validated transfer"}'
);

-- Account balances are changed only after the complete transfer has
-- passed validation. This statement is intentionally transactional.
BEGIN;

UPDATE accounts
SET balance = balance - 250.00,
    version = version + 1
WHERE account_id = 1
  AND balance >= 250.00;

IF (SELECT balance FROM accounts WHERE account_id = 1) < 0 THEN
    ROLLBACK;
END IF;

UPDATE accounts
SET balance = balance + 250.00,
    version = version + 1
WHERE account_id = 2;

COMMIT;

-- Read committed validation of current balances.
SELECT
    account_id,
    owner_name,
    balance,
    version
FROM accounts
ORDER BY account_id;

-- Atomicity invariant: money has not appeared or disappeared.
SELECT
    SUM(balance) AS total_balance
FROM accounts;

-- Consistency validation: no account may have a negative balance.
SELECT
    COUNT(*) AS invalid_accounts
FROM accounts
WHERE balance < 0;

-- Ledger validation: every committed transfer must have balanced entries.
SELECT
    transaction_id,
    SUM(
        CASE
            WHEN entry_type = 'DEBIT' THEN -amount
            ELSE amount
        END
    ) AS net_change
FROM transaction_entries
GROUP BY transaction_id
HAVING SUM(
    CASE
        WHEN entry_type = 'DEBIT' THEN -amount
        ELSE amount
    END
) <> 0;

-- Demonstrate rollback. No account state survives the transaction.
BEGIN;

INSERT INTO ledger_transactions (
    transaction_type,
    status,
    isolation_level
)
VALUES (
    'WITHDRAWAL',
    'ACTIVE',
    'READ COMMITTED'
);

UPDATE accounts
SET balance = balance - 5000.00,
    version = version + 1
WHERE account_id = 2
  AND balance >= 5000.00;

-- The UPDATE affects zero rows because the balance is insufficient.
-- The entire unit of work is explicitly cancelled.
ROLLBACK;

-- Demonstrate a savepoint for partial failure handling.
BEGIN;

UPDATE accounts
SET balance = balance + 100.00,
    version = version + 1
WHERE account_id = 3;

SAVEPOINT before_invalid_operation;

UPDATE accounts
SET balance = balance - 10000.00,
    version = version + 1
WHERE account_id = 3
  AND balance >= 10000.00;

ROLLBACK TO SAVEPOINT before_invalid_operation;

-- The valid operation before the savepoint remains in the transaction.
COMMIT;

-- PostgreSQL MVCC makes the following isolation-level behaviors possible.
-- READ COMMITTED sees a fresh committed snapshot for each statement.
-- REPEATABLE READ maintains a stable transaction snapshot.
-- SERIALIZABLE adds conflict detection so concurrent executions behave
-- as though they were serialized when the transaction can commit.

-- Explicit SERIALIZABLE example:
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;

SELECT
    account_id,
    balance,
    version
FROM accounts
WHERE account_id IN (1, 2)
ORDER BY account_id;

-- Business-rule validation can be performed before committing.
DO $$
DECLARE
    current_total NUMERIC(14, 2);
BEGIN
    SELECT SUM(balance)
    INTO current_total
    FROM accounts;

    IF current_total < 0 THEN
        RAISE EXCEPTION
            'Consistency violation: total balance cannot be negative';
    END IF;
END;
$$;

COMMIT;

-- Transaction history report.
SELECT
    lt.transaction_id,
    lt.transaction_type,
    lt.status,
    lt.isolation_level,
    lt.started_at,
    lt.committed_at,
    COUNT(te.entry_id) AS entry_count
FROM ledger_transactions AS lt
LEFT JOIN transaction_entries AS te
    ON te.transaction_id = lt.transaction_id
GROUP BY
    lt.transaction_id,
    lt.transaction_type,
    lt.status,
    lt.isolation_level,
    lt.started_at,
    lt.committed_at
ORDER BY lt.transaction_id;

-- Account-level activity aggregation.
SELECT
    a.account_id,
    a.owner_name,
    a.balance,
    COALESCE(
        SUM(
            CASE
                WHEN te.entry_type = 'CREDIT' THEN te.amount
                ELSE 0
            END
        ),
        0
    ) AS total_credits,
    COALESCE(
        SUM(
            CASE
                WHEN te.entry_type = 'DEBIT' THEN te.amount
                ELSE 0
            END
        ),
        0
    ) AS total_debits
FROM accounts AS a
LEFT JOIN transaction_entries AS te
    ON te.account_id = a.account_id
GROUP BY
    a.account_id,
    a.owner_name,
    a.balance
ORDER BY a.account_id;

-- A CTE can calculate whether the current account state satisfies
-- the primary consistency conditions.
WITH account_checks AS (
    SELECT
        account_id,
        balance >= 0 AS nonnegative_balance,
        version >= 0 AS valid_version
    FROM accounts
)
SELECT
    COUNT(*) FILTER (
        WHERE nonnegative_balance AND valid_version
    ) AS valid_accounts,
    COUNT(*) FILTER (
        WHERE NOT (nonnegative_balance AND valid_version)
    ) AS invalid_accounts
FROM account_checks;

-- Current transaction totals can be inspected without modifying state.
SELECT
    status,
    COUNT(*) AS transaction_count
FROM ledger_transactions
GROUP BY status
ORDER BY status;
