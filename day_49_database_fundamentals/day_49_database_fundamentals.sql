-- Database Fundamentals: Relational vs Non-Relational Databases
--
-- PostgreSQL-compatible relational implementation.
--
-- The model uses an online commerce domain to show why a relational
-- database separates customers, products, orders, and order items.
-- It also includes a JSONB product_attributes column to demonstrate a
-- practical boundary: relational systems can support semi-structured
-- attributes without turning the core relational model into a document
-- database.
--
-- The database enforces:
-- * primary-key uniqueness
-- * foreign-key relationships
-- * domain constraints
-- * positive quantities and non-negative prices
-- * valid order states
-- * useful query indexes
-- * transactional order creation
-- * aggregate queries
-- * JSONB querying for variable product attributes

DROP SCHEMA IF EXISTS database_fundamentals CASCADE;

CREATE SCHEMA database_fundamentals;

SET search_path TO database_fundamentals;

CREATE TABLE customers (
    customer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    country_code CHAR(2) NOT NULL
        CHECK (country_code ~ '^[A-Z]{2}$'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    product_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents BIGINT NOT NULL CHECK (price_cents >= 0),

    -- JSONB is appropriate for product-specific attributes such as
    -- keyboard switch type or camera resolution. Core business fields
    -- remain relational columns with explicit constraints.
    product_attributes JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(product_attributes) = 'object')
);

CREATE TABLE orders (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES customers(customer_id),
    order_status TEXT NOT NULL
        CHECK (
            order_status IN (
                'pending',
                'paid',
                'shipped',
                'cancelled'
            )
        ),
    ordered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL
        REFERENCES orders(order_id)
        ON DELETE CASCADE,

    product_id BIGINT NOT NULL
        REFERENCES products(product_id),

    quantity INTEGER NOT NULL CHECK (quantity > 0),

    -- Keeping the historical selling price here prevents later product
    -- price changes from changing the value of an old order.
    unit_price_cents BIGINT NOT NULL CHECK (unit_price_cents >= 0),

    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX idx_orders_customer_id
    ON orders(customer_id);

CREATE INDEX idx_orders_status
    ON orders(order_status);

CREATE INDEX idx_order_items_product_id
    ON order_items(product_id);

CREATE INDEX idx_products_category
    ON products(category);

-- GIN supports containment and key/value queries over JSONB attributes.
CREATE INDEX idx_products_attributes_gin
    ON products
    USING GIN (product_attributes);

INSERT INTO customers (email, full_name, country_code)
VALUES
    ('aisha@example.com', 'Aisha Khan', 'IN'),
    ('daniel@example.com', 'Daniel Reed', 'GB'),
    ('mei@example.com', 'Mei Chen', 'SG');

INSERT INTO products (
    sku,
    product_name,
    category,
    price_cents,
    product_attributes
)
VALUES
(
    'KB-100',
    'Mechanical Keyboard',
    'electronics',
    8900,
    '{
        "switch": "tactile",
        "layout": "US",
        "backlight": true
    }'::jsonb
),
(
    'MS-200',
    'Wireless Mouse',
    'electronics',
    4200,
    '{
        "dpi": 1600,
        "connection": "Bluetooth",
        "battery_months": 12
    }'::jsonb
),
(
    'NB-300',
    'Notebook',
    'stationery',
    900,
    '{
        "pages": 200,
        "paper": "recycled"
    }'::jsonb
),
(
    'CAM-400',
    'Web Camera',
    'electronics',
    12500,
    '{
        "resolution": "4K",
        "microphone_noise_reduction": true,
        "modes": ["conference", "streaming"]
    }'::jsonb
);

-- The transaction creates a complete order and its line items as one
-- atomic unit. If any statement fails, PostgreSQL can roll the complete
-- transaction back rather than leaving an incomplete order aggregate.

BEGIN;

INSERT INTO orders (customer_id, order_status)
SELECT customer_id, 'paid'
FROM customers
WHERE email = 'aisha@example.com'
RETURNING order_id \gset created_order_

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price_cents
)
SELECT
    :'created_order_order_id',
    product_id,
    1,
    price_cents
FROM products
WHERE sku = 'KB-100';

INSERT INTO order_items (
    order_id,
    product_id,
    quantity,
    unit_price_cents
)
SELECT
    :'created_order_order_id',
    product_id,
    2,
    price_cents
FROM products
WHERE sku = 'MS-200';

COMMIT;

-- Relational reconstruction of an order aggregate.
SELECT
    o.order_id,
    c.full_name AS customer,
    o.order_status,
    SUM(
        oi.quantity * oi.unit_price_cents
    ) AS total_cents
FROM orders AS o
JOIN customers AS c
    ON c.customer_id = o.customer_id
JOIN order_items AS oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    c.full_name,
    o.order_status
ORDER BY o.order_id;

-- Product/category analysis benefits from relational grouping.
SELECT
    p.category,
    COUNT(DISTINCT p.product_id) AS product_count,
    COALESCE(
        SUM(oi.quantity * oi.unit_price_cents),
        0
    ) AS revenue_cents
FROM products AS p
LEFT JOIN order_items AS oi
    ON oi.product_id = p.product_id
GROUP BY p.category
ORDER BY revenue_cents DESC;

-- JSONB provides flexible attribute querying while the product itself
-- remains a relational row with a primary key and constrained price.
SELECT
    sku,
    product_name,
    product_attributes ->> 'switch' AS switch_type
FROM products
WHERE product_attributes @> '{"switch": "tactile"}'::jsonb;

-- Extract nested array information from a document-shaped attribute.
SELECT
    sku,
    product_name,
    mode
FROM products
CROSS JOIN LATERAL jsonb_array_elements_text(
    product_attributes -> 'modes'
) AS mode
WHERE product_attributes ? 'modes';

-- Database-level invalid-state demonstration.
-- The following statements are intentionally commented out because the
-- complete script must execute successfully. They illustrate constraints
-- that would reject invalid data if uncommented.
--
-- INSERT INTO order_items (
--     order_id,
--     product_id,
--     quantity,
--     unit_price_cents
-- )
-- VALUES (999999, 1, 1, 8900);
-- The foreign key rejects an unknown order.
--
-- INSERT INTO products (
--     sku,
--     product_name,
--     category,
--     price_cents
-- )
-- VALUES ('KB-100', 'Duplicate SKU', 'electronics', 5000);
-- The unique constraint rejects the duplicate SKU.
--
-- INSERT INTO order_items (
--     order_id,
--     product_id,
--     quantity,
--     unit_price_cents
-- )
-- VALUES (1, 1, 0, 8900);
-- The CHECK constraint rejects a zero quantity.

-- A relational schema can also enforce state-dependent business rules
-- with a trigger when the rule cannot be represented cleanly as a CHECK.
-- This trigger prevents a cancelled order from receiving new items.

CREATE OR REPLACE FUNCTION prevent_items_on_cancelled_order()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    current_status TEXT;
BEGIN
    SELECT order_status
    INTO current_status
    FROM orders
    WHERE order_id = NEW.order_id;

    IF current_status = 'cancelled' THEN
        RAISE EXCEPTION
            'Cannot add items to cancelled order %',
            NEW.order_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_prevent_items_on_cancelled_order
BEFORE INSERT OR UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION prevent_items_on_cancelled_order();

-- A view gives reporting consumers a stable relational projection of
-- normalized tables without duplicating the underlying data.
CREATE OR REPLACE VIEW order_totals AS
SELECT
    o.order_id,
    c.customer_id,
    c.full_name,
    o.order_status,
    o.ordered_at,
    COALESCE(
        SUM(oi.quantity * oi.unit_price_cents),
        0
    ) AS total_cents
FROM orders AS o
JOIN customers AS c
    ON c.customer_id = o.customer_id
LEFT JOIN order_items AS oi
    ON oi.order_id = o.order_id
GROUP BY
    o.order_id,
    c.customer_id,
    c.full_name,
    o.order_status,
    o.ordered_at;

SELECT *
FROM order_totals
ORDER BY order_id;

-- The relational design makes relationships explicit:
-- customers -> orders -> order_items -> products.
-- JSONB adds controlled flexibility for attributes that vary by product,
-- but primary keys, foreign keys, transactions, and relational queries
-- remain responsible for the core integrity model.
