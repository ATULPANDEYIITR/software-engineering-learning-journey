DROP SCHEMA IF EXISTS indexing_lab CASCADE;
CREATE SCHEMA indexing_lab;

SET search_path = indexing_lab, public;

-- ============================================================
-- Core relational model
-- ============================================================

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    owner_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL,
    region TEXT NOT NULL CHECK (
        region IN ('north', 'south', 'east', 'west')
    )
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'paid', 'shipped', 'cancelled')
    ),
    region TEXT NOT NULL CHECK (
        region IN ('north', 'south', 'east', 'west')
    ),
    total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
    created_at TIMESTAMPTZ NOT NULL
);

-- The base workload has an explicit transactional identifier.
CREATE TABLE order_events (
    event_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'created',
            'paid',
            'shipped',
            'cancelled'
        )
    ),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Sample data
-- ============================================================

INSERT INTO repositories (repository_name, owner_name)
VALUES
    ('platform-api', 'engineering'),
    ('analytics-service', 'data');

INSERT INTO customers (customer_name, region)
SELECT
    'Customer ' || n,
    CASE n % 4
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END
FROM generate_series(1, 100) AS n;

INSERT INTO orders (
    repository_id,
    customer_id,
    status,
    region,
    total_amount,
    created_at
)
SELECT
    CASE WHEN n % 2 = 0 THEN 1 ELSE 2 END,
    ((n * 17) % 100) + 1,
    CASE n % 4
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'paid'
        WHEN 2 THEN 'shipped'
        ELSE 'cancelled'
    END,
    CASE n % 4
        WHEN 0 THEN 'north'
        WHEN 1 THEN 'south'
        WHEN 2 THEN 'east'
        ELSE 'west'
    END,
    100 + ((n * 37) % 4900),
    TIMESTAMPTZ '2026-01-01 00:00:00+00'
        + (n || ' days')::INTERVAL
FROM generate_series(1, 5000) AS n;

INSERT INTO order_events (order_id, event_type)
SELECT
    order_id,
    CASE status
        WHEN 'pending' THEN 'created'
        WHEN 'paid' THEN 'paid'
        WHEN 'shipped' THEN 'shipped'
        WHEN 'cancelled' THEN 'cancelled'
    END
FROM orders;

-- ============================================================
-- Index design
-- ============================================================

-- Equality lookup by customer.
CREATE INDEX idx_orders_customer
ON orders (customer_id);

-- Composite index.
-- The leading column matters: customer_id can be searched
-- efficiently before created_at is considered.
CREATE INDEX idx_orders_customer_created
ON orders (customer_id, created_at DESC);

-- Composite filtering and ordering workload.
CREATE INDEX idx_orders_status_region_created
ON orders (status, region, created_at DESC);

-- Partial index: only paid orders are stored in this index.
-- This reduces index size for workloads concentrated on paid rows.
CREATE INDEX idx_orders_paid_customer
ON orders (customer_id)
INCLUDE (total_amount, region, created_at)
WHERE status = 'paid';

-- Covering index for a common reporting query.
CREATE INDEX idx_orders_region_covering
ON orders (region, created_at DESC)
INCLUDE (customer_id, total_amount);

-- ============================================================
-- Statistics
-- ============================================================

ANALYZE repositories;
ANALYZE customers;
ANALYZE orders;
ANALYZE order_events;

-- ============================================================
-- Basic retrieval
-- ============================================================

SELECT
    order_id,
    customer_id,
    status,
    total_amount
FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC;

-- ============================================================
-- Composite index workload
-- ============================================================

SELECT
    order_id,
    status,
    region,
    total_amount,
    created_at
FROM orders
WHERE status = 'paid'
  AND region = 'north'
ORDER BY created_at DESC
LIMIT 20;

-- ============================================================
-- Demonstrating the importance of the leading index column
-- ============================================================

-- This can use idx_orders_customer_created efficiently because
-- customer_id is the leading key.
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    created_at,
    total_amount
FROM orders
WHERE customer_id = 42
ORDER BY created_at DESC
LIMIT 20;

-- A predicate only on created_at does not provide the same
-- leading-key lookup advantage for the customer-first index.
EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    customer_id,
    total_amount
FROM orders
WHERE created_at >= TIMESTAMPTZ '2026-10-01'
ORDER BY created_at DESC;

-- ============================================================
-- Partial-index workload
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    customer_id,
    total_amount,
    region
FROM orders
WHERE status = 'paid'
  AND customer_id = 42;

-- ============================================================
-- Covering-index workload
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    customer_id,
    total_amount,
    created_at
FROM orders
WHERE region = 'north'
ORDER BY created_at DESC
LIMIT 50;

-- ============================================================
-- Aggregation workload
-- ============================================================

SELECT
    region,
    status,
    COUNT(*) AS order_count,
    SUM(total_amount) AS total_value,
    AVG(total_amount) AS average_value
FROM orders
GROUP BY region, status
ORDER BY region, status;

-- ============================================================
-- CTE for a two-stage reporting workload
-- ============================================================

WITH paid_orders AS (
    SELECT
        customer_id,
        region,
        total_amount
    FROM orders
    WHERE status = 'paid'
),
customer_totals AS (
    SELECT
        customer_id,
        region,
        COUNT(*) AS paid_order_count,
        SUM(total_amount) AS paid_value
    FROM paid_orders
    GROUP BY customer_id, region
)
SELECT
    customer_id,
    region,
    paid_order_count,
    paid_value
FROM customer_totals
WHERE paid_order_count >= 5
ORDER BY paid_value DESC;

-- ============================================================
-- Index catalog inspection
-- ============================================================

SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'indexing_lab'
ORDER BY tablename, indexname;

-- PostgreSQL's statistics view can reveal whether indexes are
-- being used in a real workload.
SELECT
    relname,
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'indexing_lab'
ORDER BY idx_scan DESC, indexrelname;

-- ============================================================
-- Database-level validation function
-- ============================================================

CREATE OR REPLACE FUNCTION validate_order_amount()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.total_amount < 0 THEN
        RAISE EXCEPTION
            'Order % has an invalid negative amount',
            NEW.order_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_order_amount
BEFORE INSERT OR UPDATE ON orders
FOR EACH ROW
EXECUTE FUNCTION validate_order_amount();

-- ============================================================
-- Status transition validation
-- ============================================================

CREATE OR REPLACE FUNCTION validate_status_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE'
       AND OLD.status = 'cancelled'
       AND NEW.status <> 'cancelled' THEN
        RAISE EXCEPTION
            'Cancelled orders cannot return to an active state';
    END IF;

    IF TG_OP = 'UPDATE'
       AND OLD.status = 'shipped'
       AND NEW.status NOT IN ('shipped', 'cancelled') THEN
        RAISE EXCEPTION
            'Shipped orders cannot return to pending or paid';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_status_transition
BEFORE UPDATE OF status ON orders
FOR EACH ROW
EXECUTE FUNCTION validate_status_transition();

-- ============================================================
-- Transactional write and index-maintenance example
-- ============================================================

BEGIN;

INSERT INTO orders (
    repository_id,
    customer_id,
    status,
    region,
    total_amount,
    created_at
)
VALUES (
    1,
    42,
    'paid',
    'north',
    725.50,
    TIMESTAMPTZ '2026-10-25 10:00:00+00'
);

INSERT INTO order_events (
    order_id,
    event_type
)
SELECT
    order_id,
    'paid'
FROM orders
WHERE repository_id = 1
  AND customer_id = 42
  AND status = 'paid'
ORDER BY order_id DESC
LIMIT 1;

COMMIT;

-- ============================================================
-- Failure case: rejected negative amount
-- This statement is intentionally wrapped in a transaction so
-- the failure does not affect the rest of the database session.
-- ============================================================

DO $$
BEGIN
    BEGIN
        INSERT INTO orders (
            repository_id,
            customer_id,
            status,
            region,
            total_amount,
            created_at
        )
        VALUES (
            1,
            42,
            'paid',
            'north',
            -100.00,
            CURRENT_TIMESTAMP
        );
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Rejected invalid order: %',
                SQLERRM;
    END;
END;
$$;

-- ============================================================
-- Failure case: invalid status transition
-- ============================================================

DO $$
DECLARE
    shipped_order BIGINT;
BEGIN
    SELECT order_id
    INTO shipped_order
    FROM orders
    WHERE status = 'shipped'
    ORDER BY order_id
    LIMIT 1;

    BEGIN
        UPDATE orders
        SET status = 'pending'
        WHERE order_id = shipped_order;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Rejected invalid status transition: %',
                SQLERRM;
    END;
END;
$$;

-- ============================================================
-- Query-performance comparison
-- ============================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    customer_id,
    total_amount
FROM orders
WHERE customer_id = 42;

EXPLAIN (ANALYZE, BUFFERS)
SELECT
    order_id,
    customer_id,
    total_amount
FROM orders
WHERE customer_id > 0;

-- The first query is selective enough to benefit from an index
-- in many distributions. The second may return most rows, making
-- a sequential scan a reasonable PostgreSQL choice.

-- ============================================================
-- View for operational reporting
-- ============================================================

CREATE OR REPLACE VIEW order_indexing_report AS
SELECT
    region,
    status,
    COUNT(*) AS order_count,
    ROUND(SUM(total_amount), 2) AS total_amount,
    ROUND(AVG(total_amount), 2) AS average_amount,
    MIN(created_at) AS first_order,
    MAX(created_at) AS latest_order
FROM orders
GROUP BY region, status;

SELECT *
FROM order_indexing_report
ORDER BY region, status;

-- ============================================================
-- Transactional consistency check
-- ============================================================

SELECT
    COUNT(*) AS orders,
    COUNT(*) FILTER (
        WHERE total_amount < 0
    ) AS invalid_amounts,
    COUNT(*) FILTER (
        WHERE status NOT IN (
            'pending',
            'paid',
            'shipped',
            'cancelled'
        )
    ) AS invalid_statuses
FROM orders;
