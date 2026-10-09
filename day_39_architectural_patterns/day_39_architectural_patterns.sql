-- ============================================================
-- Architectural Patterns: Layered, MVC, and Hexagonal
-- PostgreSQL demonstration
-- ============================================================
--
-- This schema models a common order-processing domain.
-- The database represents the persistence concerns that would
-- normally sit behind application architecture boundaries.
--
-- The SQL deliberately focuses on relational responsibilities:
-- entities, relationships, constraints, indexes, views,
-- transactions, and integrity enforcement.
-- ============================================================


DROP SCHEMA IF EXISTS architecture_patterns CASCADE;

CREATE SCHEMA architecture_patterns;

SET search_path TO architecture_patterns;


-- ============================================================
-- Domain data
-- ============================================================

CREATE TYPE order_status AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED'
);


CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_code VARCHAR(30) NOT NULL UNIQUE,
    customer_name VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT customers_name_not_blank
        CHECK (length(trim(customer_name)) > 0)
);


CREATE TABLE products (
    product_id BIGSERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    product_name VARCHAR(150) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT products_price_non_negative
        CHECK (unit_price >= 0),
    CONSTRAINT products_name_not_blank
        CHECK (length(trim(product_name)) > 0)
);


CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(40) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),
    status order_status NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMPTZ,
    CONSTRAINT confirmed_order_requires_timestamp
        CHECK (
            status <> 'CONFIRMED'
            OR confirmed_at IS NOT NULL
        )
);


CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES orders(order_id)
        ON DELETE CASCADE,
    product_id BIGINT NOT NULL
        REFERENCES products(product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL,
    CONSTRAINT order_items_quantity_positive
        CHECK (quantity > 0),
    CONSTRAINT order_items_price_non_negative
        CHECK (unit_price >= 0),
    CONSTRAINT unique_product_per_order
        UNIQUE (order_id, product_id)
);


-- ============================================================
-- Indexes
-- ============================================================
--
-- These indexes support the access patterns that application
-- services commonly require when retrieving a customer's orders
-- or locating items belonging to an order.
-- ============================================================

CREATE INDEX idx_orders_customer_created
    ON orders(customer_id, created_at DESC);

CREATE INDEX idx_order_items_order
    ON order_items(order_id);

CREATE INDEX idx_order_items_product
    ON order_items(product_id);


-- ============================================================
-- Seed data
-- ============================================================

INSERT INTO customers (customer_code, customer_name)
VALUES
    ('CUST-LAYER', 'Layered Architecture Customer'),
    ('CUST-MVC', 'MVC Architecture Customer'),
    ('CUST-HEX', 'Hexagonal Architecture Customer'),
    ('CUST-TEST', 'Architecture Test Customer');


INSERT INTO products (sku, product_name, unit_price)
VALUES
    ('KEYBOARD', 'Mechanical Keyboard', 75.00),
    ('MOUSE', 'Precision Mouse', 40.00),
    ('MONITOR', '27 Inch Monitor', 300.00),
    ('CABLE', 'USB-C Cable', 12.50),
    ('API-GATEWAY', 'API Gateway Appliance', 500.00),
    ('CACHE', 'Application Cache Node', 125.00),
    ('SERVER', 'Application Server', 1500.00),
    ('SSD', 'Enterprise SSD', 180.00);


-- ============================================================
-- Relational view
-- ============================================================
--
-- The view is intentionally a read-oriented database boundary.
-- It gives presentation/reporting consumers a stable projection
-- without requiring them to reconstruct order totals themselves.
-- ============================================================

CREATE VIEW order_summary AS
SELECT
    o.order_id,
    o.order_number,
    c.customer_code,
    c.customer_name,
    o.status,
    o.created_at,
    o.confirmed_at,
    COALESCE(
        SUM(oi.quantity * oi.unit_price),
        0
    )::NUMERIC(12, 2) AS order_total,
    COALESCE(
        SUM(oi.quantity),
        0
    )::INTEGER AS total_units
FROM orders o
JOIN customers c
    ON c.customer_id = o.customer_id
LEFT JOIN order_items oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    o.order_number,
    c.customer_code,
    c.customer_name,
    o.status,
    o.created_at,
    o.confirmed_at;


-- ============================================================
-- Database-level state validation
-- ============================================================
--
-- The application should enforce state transitions, but the
-- database should still protect critical invariants. This trigger
-- prevents a confirmed order from silently becoming pending again.
-- ============================================================

CREATE OR REPLACE FUNCTION prevent_invalid_order_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status = 'CONFIRMED'
       AND NEW.status <> 'CONFIRMED' THEN
        RAISE EXCEPTION
            'A confirmed order cannot transition back to %',
            NEW.status;
    END IF;

    IF OLD.status = 'CANCELLED'
       AND NEW.status <> 'CANCELLED' THEN
        RAISE EXCEPTION
            'A cancelled order cannot be reopened through a normal update';
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_prevent_invalid_order_transition
BEFORE UPDATE OF status
ON orders
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_order_transition();


-- ============================================================
-- Transactional order creation
-- ============================================================
--
-- The transaction guarantees that the order header and all of its
-- lines are committed together. A failure in any statement causes
-- the caller to roll back the complete operation.
-- ============================================================

BEGIN;

INSERT INTO orders (
    order_number,
    customer_id
)
SELECT
    'ORD-LAYER-001',
    customer_id
FROM customers
WHERE customer_code = 'CUST-LAYER';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    2,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'KEYBOARD'
WHERE o.order_number = 'ORD-LAYER-001';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    1,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'MOUSE'
WHERE o.order_number = 'ORD-LAYER-001';

UPDATE orders
SET
    status = 'CONFIRMED',
    confirmed_at = CURRENT_TIMESTAMP
WHERE order_number = 'ORD-LAYER-001';

COMMIT;


-- ============================================================
-- MVC-oriented persistence example
-- ============================================================
--
-- The controller/model layer may decide that a new order should
-- exist before its presentation representation is rendered.
-- SQL remains responsible only for durable relational state.
-- ============================================================

BEGIN;

INSERT INTO orders (
    order_number,
    customer_id
)
SELECT
    'ORD-MVC-001',
    customer_id
FROM customers
WHERE customer_code = 'CUST-MVC';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    1,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'MONITOR'
WHERE o.order_number = 'ORD-MVC-001';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    3,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'CABLE'
WHERE o.order_number = 'ORD-MVC-001';

UPDATE orders
SET
    status = 'CONFIRMED',
    confirmed_at = CURRENT_TIMESTAMP
WHERE order_number = 'ORD-MVC-001';

COMMIT;


-- ============================================================
-- Hexagonal-oriented persistence example
-- ============================================================
--
-- A hexagonal application can use this schema as one driven
-- adapter while keeping the core independent of PostgreSQL.
-- The application knows the repository port, while this SQL
-- represents one concrete persistence adapter.
-- ============================================================

BEGIN;

INSERT INTO orders (
    order_number,
    customer_id
)
SELECT
    'ORD-HEX-001',
    customer_id
FROM customers
WHERE customer_code = 'CUST-HEX';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    1,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'API-GATEWAY'
WHERE o.order_number = 'ORD-HEX-001';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    p.product_id,
    2,
    p.unit_price
FROM orders o
JOIN products p
    ON p.sku = 'CACHE'
WHERE o.order_number = 'ORD-HEX-001';

UPDATE orders
SET
    status = 'CONFIRMED',
    confirmed_at = CURRENT_TIMESTAMP
WHERE order_number = 'ORD-HEX-001';

COMMIT;


-- ============================================================
-- Query used by an application read boundary
-- ============================================================

SELECT
    order_number,
    customer_code,
    status,
    order_total,
    total_units
FROM order_summary
ORDER BY created_at;


-- ============================================================
-- Domain-specific validation query
-- ============================================================
--
-- This detects orders whose stored line totals exceed a policy
-- threshold. Such a query can support application-level policy
-- evaluation without moving relational aggregation into memory.
-- ============================================================

SELECT
    order_number,
    customer_code,
    order_total
FROM order_summary
WHERE order_total > 1000
ORDER BY order_total DESC;


-- ============================================================
-- Customer-level aggregation
-- ============================================================

SELECT
    customer_code,
    customer_name,
    COUNT(order_id) AS order_count,
    COALESCE(SUM(order_total), 0)::NUMERIC(12, 2)
        AS lifetime_order_value
FROM order_summary
GROUP BY
    customer_code,
    customer_name
ORDER BY lifetime_order_value DESC;


-- ============================================================
-- Invalid state demonstration
-- ============================================================
--
-- The statement below is intentionally wrapped in a transaction
-- and rolled back. It demonstrates that database constraints and
-- triggers reject invalid state transitions rather than allowing
-- the application to create impossible persisted state.
-- ============================================================

BEGIN;

DO $$
DECLARE
    target_order BIGINT;
BEGIN
    SELECT order_id
    INTO target_order
    FROM orders
    WHERE order_number = 'ORD-LAYER-001';

    BEGIN
        UPDATE orders
        SET status = 'PENDING'
        WHERE order_id = target_order;
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE
                'Invalid transition rejected: %',
                SQLERRM;
    END;
END;
$$;

ROLLBACK;


-- ============================================================
-- Referential integrity edge case
-- ============================================================
--
-- An order item references a real product through a foreign key.
-- The database therefore prevents an item from referencing an
-- unknown product, independently of application architecture.
-- ============================================================

DO $$
BEGIN
    BEGIN
        INSERT INTO order_items (
            order_id,
            product_id,
            quantity,
            unit_price
        )
        VALUES (
            (SELECT order_id
             FROM orders
             WHERE order_number = 'ORD-HEX-001'),
            999999,
            1,
            10.00
        );
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE
                'Invalid product reference rejected by database.';
    END;
END;
$$;


-- ============================================================
-- Architecture-oriented read model
-- ============================================================
--
-- The final query demonstrates how the database can provide a
-- stable read projection to an adapter or presentation layer.
-- ============================================================

SELECT
    order_number,
    customer_name,
    status,
    total_units,
    order_total,
    confirmed_at
FROM order_summary
WHERE status = 'CONFIRMED'
ORDER BY confirmed_at DESC;
