DROP SCHEMA IF EXISTS design_patterns_demo CASCADE;

CREATE SCHEMA design_patterns_demo;

SET search_path TO design_patterns_demo;

-- ============================================================
-- Repository pattern data model
-- ============================================================

CREATE TABLE products (
    product_id      BIGINT PRIMARY KEY,
    product_name    VARCHAR(150) NOT NULL,
    category        VARCHAR(80) NOT NULL,
    price           NUMERIC(12, 2) NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT products_price_positive CHECK (price > 0),
    CONSTRAINT products_name_nonempty CHECK (length(trim(product_name)) > 0)
);

CREATE INDEX idx_products_category_active
    ON products (category, active);

CREATE TABLE customers (
    customer_id     BIGINT PRIMARY KEY,
    customer_name   VARCHAR(150) NOT NULL,
    email           VARCHAR(255) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    order_id        BIGINT PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    status          VARCHAR(30) NOT NULL,
    total_amount    NUMERIC(12, 2) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT orders_customer_fk
        FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id),

    CONSTRAINT orders_status_valid
        CHECK (
            status IN (
                'PENDING',
                'PAID',
                'SHIPPED',
                'CANCELLED'
            )
        ),

    CONSTRAINT orders_total_positive
        CHECK (total_amount > 0)
);

CREATE INDEX idx_orders_customer_status
    ON orders (customer_id, status);

CREATE TABLE order_items (
    order_id        BIGINT NOT NULL,
    product_id      BIGINT NOT NULL,
    quantity        INTEGER NOT NULL,
    unit_price      NUMERIC(12, 2) NOT NULL,

    PRIMARY KEY (order_id, product_id),

    CONSTRAINT order_items_order_fk
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    CONSTRAINT order_items_product_fk
        FOREIGN KEY (product_id)
        REFERENCES products(product_id),

    CONSTRAINT order_items_quantity_positive
        CHECK (quantity > 0),

    CONSTRAINT order_items_price_positive
        CHECK (unit_price > 0)
);

-- ============================================================
-- Facade workflow support tables
-- ============================================================

CREATE TABLE payments (
    payment_id      BIGINT PRIMARY KEY,
    order_id        BIGINT NOT NULL UNIQUE,
    amount          NUMERIC(12, 2) NOT NULL,
    status          VARCHAR(30) NOT NULL,

    CONSTRAINT payments_order_fk
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT payments_status_valid
        CHECK (
            status IN (
                'AUTHORIZED',
                'CAPTURED',
                'FAILED',
                'REFUNDED'
            )
        ),

    CONSTRAINT payments_amount_positive
        CHECK (amount > 0)
);

CREATE TABLE shipments (
    shipment_id     BIGINT PRIMARY KEY,
    order_id        BIGINT NOT NULL UNIQUE,
    address         VARCHAR(500) NOT NULL,
    status          VARCHAR(30) NOT NULL,

    CONSTRAINT shipments_order_fk
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id),

    CONSTRAINT shipments_status_valid
        CHECK (
            status IN (
                'READY',
                'DISPATCHED',
                'DELIVERED',
                'CANCELLED'
            )
        )
);

CREATE TABLE audit_events (
    event_id        BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id        BIGINT,
    event_type      VARCHAR(50) NOT NULL,
    event_details   JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT audit_order_fk
        FOREIGN KEY (order_id)
        REFERENCES orders(order_id)
        ON DELETE SET NULL
);

CREATE INDEX idx_audit_events_order_created
    ON audit_events (order_id, created_at DESC);

-- ============================================================
-- Decorator-oriented reporting views
-- ============================================================

CREATE VIEW active_product_catalog AS
SELECT
    product_id,
    product_name,
    category,
    price
FROM products
WHERE active = TRUE;

CREATE VIEW paid_order_summary AS
SELECT
    o.order_id,
    c.customer_name,
    o.total_amount,
    p.status AS payment_status,
    s.status AS shipment_status
FROM orders o
JOIN customers c
    ON c.customer_id = o.customer_id
LEFT JOIN payments p
    ON p.order_id = o.order_id
LEFT JOIN shipments s
    ON s.order_id = o.order_id
WHERE o.status = 'PAID';

-- ============================================================
-- Sample repository data
-- ============================================================

INSERT INTO products (
    product_id,
    product_name,
    category,
    price,
    active
)
VALUES
    (101, 'Enterprise VPN Gateway', 'security', 899.00, TRUE),
    (102, 'Hardware Security Key', 'security', 79.50, TRUE),
    (103, 'USB-C Docking Station', 'hardware', 189.99, TRUE),
    (104, 'Legacy Network Adapter', 'hardware', 49.99, FALSE),
    (105, 'Encrypted Backup Appliance', 'security', 1299.00, TRUE);

INSERT INTO customers (
    customer_id,
    customer_name,
    email
)
VALUES
    (1001, 'Asha Technologies', 'asha@example.com'),
    (1002, 'Northstar Systems', 'northstar@example.com');

-- ============================================================
-- Facade-style order transaction
--
-- A facade in application code would coordinate these database
-- operations. PostgreSQL provides transaction boundaries so that
-- the complete workflow succeeds or rolls back as one unit.
-- ============================================================

BEGIN;

INSERT INTO orders (
    order_id,
    customer_id,
    status,
    total_amount
)
VALUES (
    5001,
    1001,
    'PENDING',
    978.50
);

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price
)
VALUES
    (5001, 102, 1, 79.50),
    (5001, 103, 1, 189.99);

INSERT INTO payments (
    payment_id,
    order_id,
    amount,
    status
)
VALUES (
    7001,
    5001,
    978.50,
    'AUTHORIZED'
);

INSERT INTO shipments (
    shipment_id,
    order_id,
    address,
    status
)
VALUES (
    8001,
    5001,
    '42 Enterprise Avenue, Bengaluru',
    'READY'
);

UPDATE orders
SET status = 'PAID'
WHERE order_id = 5001;

INSERT INTO audit_events (
    order_id,
    event_type,
    event_details
)
VALUES (
    5001,
    'ORDER_CONFIRMED',
    jsonb_build_object(
        'payment_id', 7001,
        'shipment_id', 8001,
        'workflow', 'facade'
    )
);

COMMIT;

-- ============================================================
-- Repository-style queries
-- ============================================================

SELECT
    product_id,
    product_name,
    category,
    price
FROM products
WHERE product_id = 101;

SELECT
    product_id,
    product_name,
    price
FROM products
WHERE category = 'security'
  AND active = TRUE
ORDER BY price;

SELECT
    c.customer_name,
    COUNT(o.order_id) AS order_count,
    COALESCE(SUM(o.total_amount), 0) AS total_value
FROM customers c
LEFT JOIN orders o
    ON o.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_value DESC;

-- ============================================================
-- Decorator-style query composition
--
-- The base relation provides all products. SQL clauses can then
-- progressively add filtering, ordering, aggregation, or
-- projection in the same way a decorated query object can add
-- behavior around a base query.
-- ============================================================

WITH catalog AS (
    SELECT
        product_id,
        product_name,
        category,
        price
    FROM products
    WHERE active = TRUE
),
security_products AS (
    SELECT *
    FROM catalog
    WHERE category = 'security'
),
premium_security_products AS (
    SELECT *
    FROM security_products
    WHERE price >= 500
)
SELECT
    product_id,
    product_name,
    price
FROM premium_security_products
ORDER BY price DESC;

-- ============================================================
-- Facade workflow reporting
-- ============================================================

SELECT
    order_id,
    customer_name,
    total_amount,
    payment_status,
    shipment_status
FROM paid_order_summary
ORDER BY order_id;

SELECT
    event_id,
    order_id,
    event_type,
    event_details,
    created_at
FROM audit_events
ORDER BY created_at DESC;

-- ============================================================
-- Integrity demonstrations
-- ============================================================

DO $$
BEGIN
    BEGIN
        INSERT INTO products (
            product_id,
            product_name,
            category,
            price
        )
        VALUES (
            999,
            'Invalid Product',
            'security',
            -10
        );
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE
                'Expected repository integrity failure: negative price rejected.';
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        INSERT INTO orders (
            order_id,
            customer_id,
            status,
            total_amount
        )
        VALUES (
            5002,
            999999,
            'PENDING',
            100.00
        );
    EXCEPTION
        WHEN foreign_key_violation THEN
            RAISE NOTICE
                'Expected facade workflow failure: unknown customer rejected.';
    END;
END;
$$;

-- ============================================================
-- Transaction rollback demonstration
-- ============================================================

BEGIN;

INSERT INTO orders (
    order_id,
    customer_id,
    status,
    total_amount
)
VALUES (
    5999,
    1002,
    'PENDING',
    250.00
);

INSERT INTO audit_events (
    order_id,
    event_type,
    event_details
)
VALUES (
    5999,
    'TEMPORARY_ORDER',
    jsonb_build_object('state', 'will_rollback')
);

ROLLBACK;

SELECT
    order_id,
    status
FROM orders
WHERE order_id = 5999;

-- The query returns no rows because both inserts were rolled back.
