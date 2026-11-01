DROP SCHEMA IF EXISTS unit_testing_demo CASCADE;
CREATE SCHEMA unit_testing_demo;
SET search_path TO unit_testing_demo;

CREATE TYPE order_status AS ENUM ('new', 'paid', 'cancelled');
CREATE TYPE test_status AS ENUM ('passed', 'failed', 'skipped');

CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    price NUMERIC(12, 2) NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL CHECK (stock >= 0)
);

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    customer_name TEXT NOT NULL CHECK (length(trim(customer_name)) > 0)
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(customer_id),
    status order_status NOT NULL DEFAULT 'new',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    product_id TEXT NOT NULL REFERENCES products(product_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE test_suites (
    suite_id BIGSERIAL PRIMARY KEY,
    suite_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE test_cases (
    test_case_id BIGSERIAL PRIMARY KEY,
    suite_id BIGINT NOT NULL REFERENCES test_suites(suite_id) ON DELETE CASCADE,
    test_name TEXT NOT NULL,
    category TEXT NOT NULL,
    expected_result TEXT NOT NULL,
    UNIQUE (suite_id, test_name)
);

CREATE TABLE test_runs (
    run_id BIGSERIAL PRIMARY KEY,
    suite_id BIGINT NOT NULL REFERENCES test_suites(suite_id),
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    environment TEXT NOT NULL,
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE test_results (
    result_id BIGSERIAL PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES test_runs(run_id) ON DELETE CASCADE,
    test_case_id BIGINT NOT NULL REFERENCES test_cases(test_case_id),
    status test_status NOT NULL,
    duration_ms INTEGER NOT NULL CHECK (duration_ms >= 0),
    actual_result TEXT,
    failure_message TEXT,
    UNIQUE (run_id, test_case_id),
    CHECK (
        (status = 'failed' AND failure_message IS NOT NULL)
        OR status <> 'failed'
    )
);

CREATE TABLE fixtures (
    fixture_id BIGSERIAL PRIMARY KEY,
    fixture_name TEXT NOT NULL UNIQUE,
    fixture_type TEXT NOT NULL,
    fixture_payload JSONB NOT NULL
);

CREATE INDEX idx_test_cases_suite
    ON test_cases(suite_id);

CREATE INDEX idx_test_runs_suite_started
    ON test_runs(suite_id, started_at DESC);

CREATE INDEX idx_test_results_run_status
    ON test_results(run_id, status);

CREATE INDEX idx_fixtures_type
    ON fixtures(fixture_type);

INSERT INTO products(product_id, product_name, price, stock)
VALUES
    ('KB-01', 'Mechanical Keyboard', 80.00, 10),
    ('MS-01', 'Wireless Mouse', 25.00, 20),
    ('HD-01', 'USB Headset', 45.00, 5);

INSERT INTO customers(customer_name)
VALUES
    ('Test Customer'),
    ('Rollback Customer');

INSERT INTO orders(customer_id, status)
VALUES
    (1, 'new'),
    (2, 'new');

INSERT INTO order_items(order_id, product_id, quantity, unit_price)
VALUES
    (1, 'KB-01', 2, 80.00),
    (1, 'MS-01', 1, 25.00),
    (2, 'KB-01', 2, 80.00),
    (2, 'HD-01', 6, 45.00);

INSERT INTO test_suites(suite_name, description)
VALUES
    (
        'order-service',
        'Unit tests for validation, totals, inventory, state transitions, and rollback'
    ),
    (
        'repository-governance',
        'Unit tests for merge eligibility policy decisions'
    );

INSERT INTO test_cases(
    suite_id,
    test_name,
    category,
    expected_result
)
VALUES
    (1, 'valid product', 'validation', 'product is accepted'),
    (1, 'negative price', 'validation', 'validation error'),
    (1, 'subtotal calculation', 'calculation', '185.00'),
    (1, 'taxed total', 'calculation', '218.30'),
    (1, 'successful payment', 'state transition', 'order becomes paid'),
    (1, 'insufficient stock rollback', 'failure handling', 'previous reservations are released'),
    (1, 'cancellation', 'state transition', 'reserved stock is released'),
    (2, 'required approvals', 'policy', 'two approvals required'),
    (2, 'status check enforcement', 'policy', 'failed check blocks merge'),
    (2, 'conversation enforcement', 'policy', 'unresolved conversation blocks merge');

INSERT INTO fixtures(fixture_name, fixture_type, fixture_payload)
VALUES
(
    'standard-catalog',
    'inventory',
    '[
        {"product_id":"KB-01","price":80.00,"stock":10},
        {"product_id":"MS-01","price":25.00,"stock":20},
        {"product_id":"HD-01","price":45.00,"stock":5}
    ]'::jsonb
),
(
    'valid-order',
    'order',
    '{"items":[{"product_id":"KB-01","quantity":2},{"product_id":"MS-01","quantity":1}]}'::jsonb
),
(
    'insufficient-stock-order',
    'order',
    '{"items":[{"product_id":"KB-01","quantity":2},{"product_id":"HD-01","quantity":6}]}'::jsonb
);

CREATE OR REPLACE FUNCTION calculate_order_subtotal(p_order_id BIGINT)
RETURNS NUMERIC(12,2)
LANGUAGE plpgsql
AS $$
DECLARE
    subtotal NUMERIC(12,2);
BEGIN
    SELECT COALESCE(SUM(quantity * unit_price), 0)
    INTO subtotal
    FROM order_items
    WHERE order_id = p_order_id;

    IF subtotal = 0 THEN
        RAISE EXCEPTION 'Order % has no billable items', p_order_id;
    END IF;

    RETURN subtotal;
END;
$$;

CREATE OR REPLACE FUNCTION calculate_order_total(p_order_id BIGINT)
RETURNS NUMERIC(12,2)
LANGUAGE sql
AS $$
    SELECT ROUND(
        calculate_order_subtotal(p_order_id) * 1.18,
        2
    );
$$;

CREATE OR REPLACE FUNCTION validate_test_result()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'failed'
       AND (NEW.failure_message IS NULL OR length(trim(NEW.failure_message)) = 0)
    THEN
        RAISE EXCEPTION 'Failed test results require a failure message';
    END IF;

    IF NEW.status <> 'failed' THEN
        NEW.failure_message := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_test_result
BEFORE INSERT OR UPDATE ON test_results
FOR EACH ROW
EXECUTE FUNCTION validate_test_result();

CREATE OR REPLACE FUNCTION finish_test_run(p_run_id BIGINT)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE test_runs
    SET finished_at = now()
    WHERE run_id = p_run_id
      AND finished_at IS NULL;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Open test run % was not found', p_run_id;
    END IF;
END;
$$;

INSERT INTO test_runs(suite_id, environment)
VALUES
    (1, 'postgresql-fixture'),
    (2, 'postgresql-policy');

INSERT INTO test_results(
    run_id,
    test_case_id,
    status,
    duration_ms,
    actual_result
)
VALUES
    (1, 1, 'passed', 3, 'product accepted'),
    (1, 2, 'passed', 2, 'validation error raised'),
    (1, 3, 'passed', 4, '185.00'),
    (1, 4, 'passed', 4, '218.30'),
    (1, 5, 'passed', 6, 'order transitioned to paid'),
    (1, 6, 'passed', 7, 'inventory rollback verified'),
    (1, 7, 'passed', 5, 'inventory restored'),
    (2, 8, 'passed', 2, 'approval threshold enforced'),
    (2, 9, 'passed', 2, 'failed status check blocks merge'),
    (2, 10, 'failed', 2, 'unexpected policy result',
        'Conversation state was not propagated to the policy evaluator');

SELECT finish_test_run(1);
SELECT finish_test_run(2);

CREATE VIEW test_run_report AS
SELECT
    tr.run_id,
    ts.suite_name,
    tr.environment,
    tr.started_at,
    tr.finished_at,
    COUNT(res.result_id) AS total_tests,
    COUNT(*) FILTER (WHERE res.status = 'passed') AS passed_tests,
    COUNT(*) FILTER (WHERE res.status = 'failed') AS failed_tests,
    COUNT(*) FILTER (WHERE res.status = 'skipped') AS skipped_tests,
    ROUND(AVG(res.duration_ms), 2) AS average_duration_ms
FROM test_runs tr
JOIN test_suites ts ON ts.suite_id = tr.suite_id
LEFT JOIN test_results res ON res.run_id = tr.run_id
GROUP BY
    tr.run_id,
    ts.suite_name,
    tr.environment,
    tr.started_at,
    tr.finished_at;

CREATE VIEW failing_tests AS
SELECT
    tr.run_id,
    ts.suite_name,
    tc.test_name,
    res.failure_message,
    res.duration_ms
FROM test_results res
JOIN test_runs tr ON tr.run_id = res.run_id
JOIN test_suites ts ON ts.suite_id = tr.suite_id
JOIN test_cases tc ON tc.test_case_id = res.test_case_id
WHERE res.status = 'failed';

CREATE VIEW order_validation_report AS
SELECT
    o.order_id,
    c.customer_name,
    o.status,
    calculate_order_subtotal(o.order_id) AS subtotal,
    calculate_order_total(o.order_id) AS total
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
WHERE EXISTS (
    SELECT 1
    FROM order_items oi
    WHERE oi.order_id = o.order_id
);

SELECT *
FROM test_run_report
ORDER BY run_id;

SELECT *
FROM failing_tests
ORDER BY run_id;

SELECT
    suite_name,
    SUM(total_tests) AS tests,
    SUM(passed_tests) AS passed,
    SUM(failed_tests) AS failed
FROM test_run_report
GROUP BY suite_name
ORDER BY suite_name;

SELECT *
FROM order_validation_report
ORDER BY order_id;

WITH expected AS (
    SELECT
        'valid-order'::TEXT AS fixture_name,
        185.00::NUMERIC AS expected_subtotal,
        218.30::NUMERIC AS expected_total
)
SELECT
    e.fixture_name,
    e.expected_subtotal,
    calculate_order_subtotal(1) AS actual_subtotal,
    e.expected_total,
    calculate_order_total(1) AS actual_total,
    calculate_order_subtotal(1) = e.expected_subtotal
        AND calculate_order_total(1) = e.expected_total AS assertion_passed
FROM expected e;

DO $$
DECLARE
    actual NUMERIC(12,2);
BEGIN
    actual := calculate_order_total(1);

    IF actual <> 218.30 THEN
        RAISE EXCEPTION
            'Assertion failed: expected 218.30, got %',
            actual;
    END IF;
END;
$$;

BEGIN;

UPDATE products
SET stock = stock - 2
WHERE product_id = 'KB-01'
  AND stock >= 2;

IF (SELECT stock FROM products WHERE product_id = 'KB-01') < 0 THEN
    ROLLBACK;
    RAISE EXCEPTION 'Inventory invariant violated';
END IF;

ROLLBACK;

SELECT
    product_id,
    product_name,
    stock,
    price
FROM products
ORDER BY product_id;
