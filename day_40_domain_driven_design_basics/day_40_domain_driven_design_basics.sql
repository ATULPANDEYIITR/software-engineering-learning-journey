DROP SCHEMA IF EXISTS ddd_basics CASCADE;
CREATE SCHEMA ddd_basics;
SET search_path TO ddd_basics;

-- PostgreSQL implementation of a small ordering domain.
-- The schema separates aggregate identity from value-object data.
-- Customer and Order are entities because their identities persist.
-- Money, ProductCode, and Address are modeled as value data.
-- Order is the aggregate root; order_line belongs to that aggregate.
--
-- Database constraints protect invariants that must survive regardless
-- of which application service writes the data.

CREATE TYPE order_status AS ENUM (
    'DRAFT',
    'CONFIRMED',
    'CANCELLED'
);

CREATE TABLE customer (
    customer_id UUID PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    street TEXT NOT NULL,
    city TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    country TEXT NOT NULL DEFAULT 'India',

    CONSTRAINT customer_name_not_blank
        CHECK (length(trim(customer_name)) > 0),

    CONSTRAINT customer_email_valid
        CHECK (position('@' IN email) > 1),

    CONSTRAINT customer_postal_code_not_blank
        CHECK (length(trim(postal_code)) > 0)
);

CREATE TABLE product (
    product_id UUID PRIMARY KEY,
    product_code TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    currency CHAR(3) NOT NULL DEFAULT 'INR',
    unit_price NUMERIC(14, 2) NOT NULL,

    CONSTRAINT product_code_valid
        CHECK (product_code ~ '^[A-Z0-9-]{2,40}$'),

    CONSTRAINT product_name_not_blank
        CHECK (length(trim(product_name)) > 0),

    CONSTRAINT product_currency_valid
        CHECK (currency ~ '^[A-Z]{3}$'),

    CONSTRAINT product_price_non_negative
        CHECK (unit_price >= 0)
);

CREATE TABLE customer_order (
    order_id UUID PRIMARY KEY,
    customer_id UUID NOT NULL
        REFERENCES customer(customer_id),
    status order_status NOT NULL DEFAULT 'DRAFT',
    shipping_street TEXT NOT NULL,
    shipping_city TEXT NOT NULL,
    shipping_postal_code TEXT NOT NULL,
    shipping_country TEXT NOT NULL DEFAULT 'India',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    confirmed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    cancellation_reason TEXT,

    CONSTRAINT shipping_street_not_blank
        CHECK (length(trim(shipping_street)) > 0),

    CONSTRAINT shipping_city_not_blank
        CHECK (length(trim(shipping_city)) > 0),

    CONSTRAINT shipping_postal_code_not_blank
        CHECK (length(trim(shipping_postal_code)) > 0),

    CONSTRAINT cancellation_data_consistent
        CHECK (
            (status = 'CANCELLED'
             AND cancelled_at IS NOT NULL
             AND length(trim(cancellation_reason)) > 0)
            OR
            (status <> 'CANCELLED'
             AND cancelled_at IS NULL
             AND cancellation_reason IS NULL)
        ),

    CONSTRAINT confirmation_data_consistent
        CHECK (
            (status = 'CONFIRMED' AND confirmed_at IS NOT NULL)
            OR
            (status <> 'CONFIRMED' AND confirmed_at IS NULL)
        )
);

CREATE TABLE order_line (
    order_line_id UUID PRIMARY KEY,
    order_id UUID NOT NULL
        REFERENCES customer_order(order_id)
        ON DELETE CASCADE,
    product_id UUID NOT NULL
        REFERENCES product(product_id),
    quantity INTEGER NOT NULL,
    unit_price NUMERIC(14, 2) NOT NULL,
    currency CHAR(3) NOT NULL,

    -- The aggregate does not permit the same product to appear in
    -- multiple independent lines.
    CONSTRAINT one_product_per_order
        UNIQUE (order_id, product_id),

    CONSTRAINT quantity_positive
        CHECK (quantity > 0),

    CONSTRAINT line_price_non_negative
        CHECK (unit_price >= 0),

    CONSTRAINT line_currency_valid
        CHECK (currency ~ '^[A-Z]{3}$')
);

CREATE INDEX idx_order_customer
    ON customer_order(customer_id);

CREATE INDEX idx_order_status
    ON customer_order(status);

CREATE INDEX idx_order_line_product
    ON order_line(product_id);

INSERT INTO customer (
    customer_id,
    customer_name,
    email,
    street,
    city,
    postal_code,
    country
)
VALUES
(
    '00000000-0000-0000-0000-000000000001',
    'Atul Pandey',
    'atul@example.com',
    '14 Gomti Nagar',
    'Lucknow',
    '226010',
    'India'
),
(
    '00000000-0000-0000-0000-000000000002',
    'Meera Sharma',
    'meera@example.com',
    '21 Indira Nagar',
    'Lucknow',
    '226016',
    'India'
);

INSERT INTO product (
    product_id,
    product_code,
    product_name,
    currency,
    unit_price
)
VALUES
(
    '10000000-0000-0000-0000-000000000001',
    'LAPTOP-14',
    'Business Laptop',
    'INR',
    79999.00
),
(
    '10000000-0000-0000-0000-000000000002',
    'USB-C-HUB',
    'USB-C Docking Hub',
    'INR',
    2499.50
),
(
    '10000000-0000-0000-0000-000000000003',
    'MOUSE',
    'Wireless Mouse',
    'INR',
    1200.00
);

INSERT INTO customer_order (
    order_id,
    customer_id,
    status,
    shipping_street,
    shipping_city,
    shipping_postal_code,
    shipping_country
)
VALUES
(
    '20000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    'DRAFT',
    '14 Gomti Nagar',
    'Lucknow',
    '226010',
    'India'
),
(
    '20000000-0000-0000-0000-000000000002',
    '00000000-0000-0000-0000-000000000002',
    'DRAFT',
    '21 Indira Nagar',
    'Lucknow',
    '226016',
    'India'
);

INSERT INTO order_line (
    order_line_id,
    order_id,
    product_id,
    quantity,
    unit_price,
    currency
)
VALUES
(
    '30000000-0000-0000-0000-000000000001',
    '20000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000001',
    1,
    79999.00,
    'INR'
),
(
    '30000000-0000-0000-0000-000000000002',
    '20000000-0000-0000-0000-000000000001',
    '10000000-0000-0000-0000-000000000002',
    2,
    2499.50,
    'INR'
),
(
    '30000000-0000-0000-0000-000000000003',
    '20000000-0000-0000-0000-000000000002',
    '10000000-0000-0000-0000-000000000003',
    3,
    1200.00,
    'INR'
);

-- Aggregate query: order totals are derived from the lines owned by each order.
SELECT
    o.order_id,
    c.customer_name,
    o.status,
    COUNT(ol.order_line_id) AS line_count,
    SUM(ol.quantity) AS total_units,
    SUM(ol.quantity * ol.unit_price) AS order_total
FROM customer_order AS o
JOIN customer AS c
    ON c.customer_id = o.customer_id
LEFT JOIN order_line AS ol
    ON ol.order_id = o.order_id
GROUP BY
    o.order_id,
    c.customer_name,
    o.status
ORDER BY o.created_at;

-- This query identifies draft aggregates that are structurally ready
-- for confirmation because they contain at least one positive-priced line.
WITH order_totals AS (
    SELECT
        o.order_id,
        COUNT(ol.order_line_id) AS line_count,
        COALESCE(SUM(ol.quantity * ol.unit_price), 0) AS total
    FROM customer_order AS o
    LEFT JOIN order_line AS ol
        ON ol.order_id = o.order_id
    WHERE o.status = 'DRAFT'
    GROUP BY o.order_id
)
SELECT
    order_id,
    line_count,
    total
FROM order_totals
WHERE line_count > 0
  AND total > 0
ORDER BY order_id;

-- The transaction demonstrates an aggregate state transition.
-- Both the status and confirmation timestamp change atomically.
BEGIN;

UPDATE customer_order
SET
    status = 'CONFIRMED',
    confirmed_at = CURRENT_TIMESTAMP
WHERE order_id = '20000000-0000-0000-0000-000000000001'
  AND status = 'DRAFT'
  AND EXISTS (
      SELECT 1
      FROM order_line
      WHERE order_line.order_id =
            customer_order.order_id
  );

COMMIT;

SELECT
    order_id,
    status,
    confirmed_at
FROM customer_order
WHERE order_id = '20000000-0000-0000-0000-000000000001';

-- Cancellation demonstrates a different valid state transition.
BEGIN;

UPDATE customer_order
SET
    status = 'CANCELLED',
    cancelled_at = CURRENT_TIMESTAMP,
    cancellation_reason = 'Customer requested cancellation'
WHERE order_id = '20000000-0000-0000-0000-000000000002'
  AND status = 'DRAFT';

COMMIT;

SELECT
    order_id,
    status,
    cancellation_reason,
    cancelled_at
FROM customer_order
WHERE order_id = '20000000-0000-0000-0000-000000000002';

-- Database-enforced invariant demonstration.
-- The following statement is intentionally commented out because executing
-- it would fail: the unique constraint prevents duplicate products inside
-- the same Order aggregate.
--
-- INSERT INTO order_line (
--     order_line_id,
--     order_id,
--     product_id,
--     quantity,
--     unit_price,
--     currency
-- )
-- VALUES (
--     '30000000-0000-0000-0000-000000000004',
--     '20000000-0000-0000-0000-000000000001',
--     '10000000-0000-0000-0000-000000000001',
--     1,
--     79999.00,
--     'INR'
-- );

-- Domain-oriented reporting: expose the aggregate as a read model without
-- allowing consumers to mutate the underlying tables through the view.
CREATE VIEW order_summary AS
SELECT
    o.order_id,
    c.customer_name,
    o.status,
    COALESCE(SUM(ol.quantity), 0) AS total_units,
    COALESCE(
        SUM(ol.quantity * ol.unit_price),
        0
    ) AS total_value,
    COUNT(ol.order_line_id) AS line_count
FROM customer_order AS o
JOIN customer AS c
    ON c.customer_id = o.customer_id
LEFT JOIN order_line AS ol
    ON ol.order_id = o.order_id
GROUP BY
    o.order_id,
    c.customer_name,
    o.status;

SELECT *
FROM order_summary
ORDER BY order_id;
