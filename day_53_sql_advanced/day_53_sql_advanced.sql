DROP SCHEMA IF EXISTS advanced_sql CASCADE;
CREATE SCHEMA advanced_sql;
SET search_path TO advanced_sql;

-- The model separates transactional facts from descriptive dimensions.
CREATE TABLE customers (
    customer_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_name text NOT NULL,
    region text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT customers_name_chk CHECK (length(trim(customer_name)) >= 2),
    CONSTRAINT customers_region_chk CHECK (length(trim(region)) >= 2)
);

CREATE TABLE products (
    product_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name text NOT NULL UNIQUE,
    category text NOT NULL,
    unit_price numeric(12,2) NOT NULL,
    CONSTRAINT products_price_chk CHECK (unit_price >= 0),
    CONSTRAINT products_category_chk CHECK (category IN ('Electronics', 'Furniture'))
);

CREATE TABLE sales (
    sale_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id bigint NOT NULL REFERENCES customers(customer_id),
    product_id bigint NOT NULL REFERENCES products(product_id),
    sale_date date NOT NULL,
    quantity integer NOT NULL,
    unit_price numeric(12,2) NOT NULL,
    CONSTRAINT sales_quantity_chk CHECK (quantity > 0),
    CONSTRAINT sales_price_chk CHECK (unit_price >= 0)
);

CREATE TABLE customer_targets (
    customer_id bigint PRIMARY KEY REFERENCES customers(customer_id),
    monthly_target numeric(14,2) NOT NULL,
    CONSTRAINT customer_targets_positive_chk CHECK (monthly_target > 0)
);

CREATE INDEX sales_customer_date_idx
    ON sales (customer_id, sale_date);

CREATE INDEX sales_product_idx
    ON sales (product_id);

CREATE INDEX sales_date_idx
    ON sales (sale_date);

INSERT INTO customers (customer_name, region)
VALUES
    ('Asha', 'North'),
    ('Ravi', 'South'),
    ('Meera', 'North'),
    ('Kabir', 'West'),
    ('Nisha', 'West'),
    ('Dev', 'East');

INSERT INTO products (product_name, category, unit_price)
VALUES
    ('Laptop', 'Electronics', 1200.00),
    ('Phone', 'Electronics', 850.00),
    ('Desk', 'Furniture', 450.00),
    ('Monitor', 'Electronics', 400.00),
    ('Chair', 'Furniture', 300.00);

INSERT INTO customer_targets (customer_id, monthly_target)
SELECT customer_id,
       CASE region
           WHEN 'North' THEN 1800
           WHEN 'South' THEN 2000
           WHEN 'West' THEN 1500
           ELSE 1000
       END
FROM customers;

INSERT INTO sales (customer_id, product_id, sale_date, quantity, unit_price)
VALUES
    (1, 1, '2026-01-05', 1, 1200.00),
    (2, 2, '2026-01-08', 1, 850.00),
    (3, 3, '2026-01-10', 1, 450.00),
    (1, 4, '2026-02-04', 1, 400.00),
    (4, 5, '2026-02-12', 1, 300.00),
    (2, 1, '2026-02-18', 1, 1300.00),
    (5, 2, '2026-03-03', 1, 900.00),
    (3, 5, '2026-03-11', 1, 280.00),
    (1, 2, '2026-03-17', 1, 820.00),
    (4, 1, '2026-04-07', 1, 1250.00);

-- A generated value keeps revenue calculation consistent with stored facts.
ALTER TABLE sales
ADD COLUMN revenue numeric(14,2)
GENERATED ALWAYS AS (quantity * unit_price) STORED;

-- INNER JOIN combines matching rows from both relations.
SELECT
    s.sale_id,
    c.customer_name,
    c.region,
    p.product_name,
    s.quantity,
    s.revenue
FROM sales AS s
JOIN customers AS c
    ON c.customer_id = s.customer_id
JOIN products AS p
    ON p.product_id = s.product_id
ORDER BY s.sale_date, s.sale_id;

-- LEFT JOIN deliberately retains customers that have no sales.
SELECT
    c.customer_id,
    c.customer_name,
    COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS lifetime_revenue
FROM customers AS c
LEFT JOIN sales AS s
    ON s.customer_id = c.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY lifetime_revenue DESC, c.customer_id;

-- A subquery produces the average customer revenue used by the outer query.
SELECT
    customer_id,
    customer_name,
    lifetime_revenue
FROM (
    SELECT
        c.customer_id,
        c.customer_name,
        COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS lifetime_revenue
    FROM customers AS c
    LEFT JOIN sales AS s
        ON s.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
) AS customer_totals
WHERE lifetime_revenue >= (
    SELECT AVG(lifetime_revenue)
    FROM (
        SELECT
            c.customer_id,
            COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS lifetime_revenue
        FROM customers AS c
        LEFT JOIN sales AS s
            ON s.customer_id = c.customer_id
        GROUP BY c.customer_id
    ) AS averages
)
ORDER BY lifetime_revenue DESC;

-- A CTE makes the monthly aggregation reusable by the following query.
WITH monthly_sales AS (
    SELECT
        date_trunc('month', sale_date)::date AS sales_month,
        SUM(revenue)::numeric(14,2) AS monthly_revenue
    FROM sales
    GROUP BY date_trunc('month', sale_date)::date
),
monthly_baseline AS (
    SELECT
        AVG(monthly_revenue) AS average_monthly_revenue
    FROM monthly_sales
)
SELECT
    m.sales_month,
    m.monthly_revenue,
    ROUND(b.average_monthly_revenue, 2) AS average_monthly_revenue,
    CASE
        WHEN m.monthly_revenue > b.average_monthly_revenue
            THEN 'Above average'
        ELSE 'At or below average'
    END AS performance
FROM monthly_sales AS m
CROSS JOIN monthly_baseline AS b
ORDER BY m.sales_month;

-- Window functions retain individual rows while calculating partition-level
-- and ordered analytical values.
SELECT
    s.sale_id,
    c.customer_name,
    s.sale_date,
    s.revenue,
    SUM(s.revenue) OVER (
        PARTITION BY s.customer_id
        ORDER BY s.sale_date, s.sale_id
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )::numeric(14,2) AS running_customer_revenue,
    AVG(s.revenue) OVER (
        PARTITION BY s.customer_id
    )::numeric(14,2) AS customer_average_sale
FROM sales AS s
JOIN customers AS c
    ON c.customer_id = s.customer_id
ORDER BY s.customer_id, s.sale_date, s.sale_id;

-- RANK and DENSE_RANK show different treatment of ties.
WITH customer_revenue AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.region,
        COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS revenue
    FROM customers AS c
    LEFT JOIN sales AS s
        ON s.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name, c.region
)
SELECT
    customer_id,
    customer_name,
    region,
    revenue,
    RANK() OVER (
        PARTITION BY region
        ORDER BY revenue DESC
    ) AS regional_rank,
    DENSE_RANK() OVER (
        PARTITION BY region
        ORDER BY revenue DESC
    ) AS regional_dense_rank,
    ROW_NUMBER() OVER (
        PARTITION BY region
        ORDER BY revenue DESC, customer_id
    ) AS regional_row_number
FROM customer_revenue
ORDER BY region, regional_rank, customer_id;

-- LAG compares each customer's monthly revenue with its previous month.
WITH monthly_customer_sales AS (
    SELECT
        customer_id,
        date_trunc('month', sale_date)::date AS sales_month,
        SUM(revenue)::numeric(14,2) AS monthly_revenue
    FROM sales
    GROUP BY customer_id, date_trunc('month', sale_date)::date
)
SELECT
    customer_id,
    sales_month,
    monthly_revenue,
    LAG(monthly_revenue) OVER (
        PARTITION BY customer_id
        ORDER BY sales_month
    ) AS previous_month_revenue,
    (
        monthly_revenue
        - COALESCE(
            LAG(monthly_revenue) OVER (
                PARTITION BY customer_id
                ORDER BY sales_month
            ),
            0
        )
    )::numeric(14,2) AS change_from_previous
FROM monthly_customer_sales
ORDER BY customer_id, sales_month;

-- NTILE distributes customers into four revenue segments.
WITH customer_revenue AS (
    SELECT
        c.customer_id,
        c.customer_name,
        COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS revenue
    FROM customers AS c
    LEFT JOIN sales AS s
        ON s.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name
)
SELECT
    customer_id,
    customer_name,
    revenue,
    NTILE(4) OVER (ORDER BY revenue DESC) AS revenue_quartile
FROM customer_revenue
ORDER BY revenue DESC;

-- This view exposes a reusable analytical relation without materializing
-- potentially stale results.
CREATE OR REPLACE VIEW customer_performance AS
WITH customer_sales AS (
    SELECT
        c.customer_id,
        c.customer_name,
        c.region,
        COALESCE(SUM(s.revenue), 0)::numeric(14,2) AS revenue
    FROM customers AS c
    LEFT JOIN sales AS s
        ON s.customer_id = c.customer_id
    GROUP BY c.customer_id, c.customer_name, c.region
)
SELECT
    cs.*,
    ct.monthly_target,
    (cs.revenue >= ct.monthly_target) AS target_reached,
    RANK() OVER (
        PARTITION BY cs.region
        ORDER BY cs.revenue DESC
    ) AS regional_rank
FROM customer_sales AS cs
JOIN customer_targets AS ct
    ON ct.customer_id = cs.customer_id;

SELECT *
FROM customer_performance
ORDER BY region, regional_rank;

-- A trigger rejects negative quantities before the generated revenue is
-- evaluated. Database enforcement prevents invalid writes from bypassing
-- application validation.
CREATE OR REPLACE FUNCTION validate_sale()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.quantity <= 0 THEN
        RAISE EXCEPTION 'Quantity must be positive';
    END IF;

    IF NEW.unit_price < 0 THEN
        RAISE EXCEPTION 'Unit price cannot be negative';
    END IF;

    IF NEW.sale_date > CURRENT_DATE THEN
        RAISE EXCEPTION 'Sale date cannot be in the future';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER sales_validation_trigger
BEFORE INSERT OR UPDATE ON sales
FOR EACH ROW
EXECUTE FUNCTION validate_sale();

-- Transactional insertion demonstrates atomic validation. The invalid row
-- causes the transaction to fail rather than partially committing.
BEGIN;

INSERT INTO sales (
    customer_id,
    product_id,
    sale_date,
    quantity,
    unit_price
)
VALUES (
    5,
    2,
    CURRENT_DATE,
    1,
    900.00
);

COMMIT;

-- EXPLAIN ANALYZE can be used operationally to verify whether the indexes
-- support the actual execution plan.
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF)
SELECT
    customer_id,
    SUM(revenue)
FROM sales
WHERE sale_date >= DATE '2026-01-01'
  AND sale_date < DATE '2027-01-01'
GROUP BY customer_id
ORDER BY SUM(revenue) DESC;
