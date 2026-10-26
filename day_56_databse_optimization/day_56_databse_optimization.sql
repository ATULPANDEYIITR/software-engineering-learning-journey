DROP SCHEMA IF EXISTS optimization_lab CASCADE;
CREATE SCHEMA optimization_lab;

SET search_path = optimization_lab, public;

-- ============================================================
-- DATABASE OPTIMIZATION MODEL
-- ============================================================

CREATE TYPE query_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed'
);

CREATE TYPE check_status AS ENUM (
    'pending',
    'passed',
    'failed',
    'cancelled'
);

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE app_users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    commit_hash CHAR(40) NOT NULL,
    parent_commit_id BIGINT REFERENCES commits(commit_id),
    committed_by BIGINT NOT NULL
        REFERENCES app_users(user_id),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    changed_rows INTEGER NOT NULL DEFAULT 0
        CHECK (changed_rows >= 0),
    UNIQUE (repository_id, commit_hash)
);

CREATE TABLE query_workloads (
    workload_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT
        REFERENCES repositories(repository_id)
        ON DELETE SET NULL,
    workload_name TEXT NOT NULL,
    query_text TEXT NOT NULL,
    status query_status NOT NULL DEFAULT 'queued',
    estimated_rows BIGINT
        CHECK (estimated_rows IS NULL OR estimated_rows >= 0),
    actual_rows BIGINT
        CHECK (actual_rows IS NULL OR actual_rows >= 0),
    estimated_cost NUMERIC(18,4)
        CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
    actual_duration_ms NUMERIC(18,4)
        CHECK (actual_duration_ms IS NULL OR actual_duration_ms >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE query_executions (
    execution_id BIGSERIAL PRIMARY KEY,
    workload_id BIGINT NOT NULL
        REFERENCES query_workloads(workload_id)
        ON DELETE CASCADE,
    plan_hash TEXT NOT NULL,
    access_path TEXT NOT NULL,
    join_strategy TEXT,
    sort_method TEXT,
    rows_removed_by_filter BIGINT NOT NULL DEFAULT 0
        CHECK (rows_removed_by_filter >= 0),
    buffers_shared_hit BIGINT NOT NULL DEFAULT 0
        CHECK (buffers_shared_hit >= 0),
    buffers_shared_read BIGINT NOT NULL DEFAULT 0
        CHECK (buffers_shared_read >= 0),
    execution_time_ms NUMERIC(18,4) NOT NULL
        CHECK (execution_time_ms >= 0),
    captured_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE indexes (
    index_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    table_name TEXT NOT NULL,
    index_name TEXT NOT NULL,
    indexed_columns TEXT[] NOT NULL,
    included_columns TEXT[] NOT NULL DEFAULT '{}',
    is_unique BOOLEAN NOT NULL DEFAULT FALSE,
    estimated_storage_mb NUMERIC(18,2) NOT NULL DEFAULT 0
        CHECK (estimated_storage_mb >= 0),
    UNIQUE (repository_id, index_name)
);

CREATE TABLE optimization_findings (
    finding_id BIGSERIAL PRIMARY KEY,
    workload_id BIGINT NOT NULL
        REFERENCES query_workloads(workload_id)
        ON DELETE CASCADE,
    severity TEXT NOT NULL
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    category TEXT NOT NULL
        CHECK (
            category IN (
                'scan',
                'join',
                'sort',
                'aggregation',
                'statistics',
                'index',
                'cardinality'
            )
        ),
    finding TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX idx_workloads_status
    ON query_workloads(status);

CREATE INDEX idx_workloads_repository_created
    ON query_workloads(repository_id, created_at DESC);

CREATE INDEX idx_executions_workload_captured
    ON query_executions(workload_id, captured_at DESC);

CREATE INDEX idx_findings_unresolved
    ON optimization_findings(workload_id, severity)
    WHERE resolved = FALSE;

CREATE INDEX idx_indexes_table
    ON indexes(table_name);

-- ============================================================
-- SAMPLE DATA
-- ============================================================

INSERT INTO repositories (repository_name)
VALUES
    ('commerce-platform'),
    ('analytics-platform');

INSERT INTO app_users (username)
VALUES
    ('db-admin'),
    ('performance-engineer'),
    ('application-owner');

INSERT INTO branches (repository_id, branch_name, is_default)
SELECT repository_id, 'main', TRUE
FROM repositories
WHERE repository_name IN ('commerce-platform', 'analytics-platform');

INSERT INTO commits (
    repository_id,
    commit_hash,
    committed_by,
    changed_rows
)
SELECT
    r.repository_id,
    repeat(
        CASE
            WHEN r.repository_name = 'commerce-platform' THEN 'a'
            ELSE 'b'
        END,
        40
    ),
    u.user_id,
    125
FROM repositories r
CROSS JOIN LATERAL (
    SELECT user_id
    FROM app_users
    WHERE username = 'application-owner'
) u;

INSERT INTO query_workloads (
    repository_id,
    workload_name,
    query_text,
    status,
    estimated_rows,
    actual_rows,
    estimated_cost,
    actual_duration_ms
)
SELECT
    r.repository_id,
    'monthly-completed-orders',
    $q$
SELECT c.region, SUM(o.total_amount)
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
  AND o.created_at >= DATE '2026-01-01'
GROUP BY c.region
ORDER BY SUM(o.total_amount) DESC
$q$,
    'completed',
    250000,
    243871,
    155000.00,
    1842.31
FROM repositories r
WHERE r.repository_name = 'commerce-platform';

INSERT INTO query_workloads (
    repository_id,
    workload_name,
    query_text,
    status,
    estimated_rows,
    actual_rows,
    estimated_cost,
    actual_duration_ms
)
SELECT
    r.repository_id,
    'customer-region-search',
    $q$
SELECT id, email
FROM customers
WHERE region = $1
ORDER BY id
$q$,
    'completed',
    22500,
    21981,
    8200.00,
    91.22
FROM repositories r
WHERE r.repository_name = 'commerce-platform';

INSERT INTO query_workloads (
    repository_id,
    workload_name,
    query_text,
    status
)
SELECT
    r.repository_id,
    'failed-cardinality-analysis',
    'SELECT * FROM orders JOIN customers ON orders.customer_id = customers.id',
    'failed'
FROM repositories r
WHERE r.repository_name = 'analytics-platform';

INSERT INTO indexes (
    repository_id,
    table_name,
    index_name,
    indexed_columns,
    included_columns,
    is_unique,
    estimated_storage_mb
)
SELECT
    r.repository_id,
    'orders',
    'idx_orders_customer',
    ARRAY['customer_id'],
    '{}',
    FALSE,
    420.50
FROM repositories r
WHERE r.repository_name = 'commerce-platform';

INSERT INTO indexes (
    repository_id,
    table_name,
    index_name,
    indexed_columns,
    included_columns,
    estimated_storage_mb
)
SELECT
    r.repository_id,
    'orders',
    'idx_orders_status_created_covering',
    ARRAY['status', 'created_at'],
    ARRAY['customer_id', 'total_amount'],
    850.75
FROM repositories r
WHERE r.repository_name = 'commerce-platform';

INSERT INTO indexes (
    repository_id,
    table_name,
    index_name,
    indexed_columns,
    included_columns,
    is_unique,
    estimated_storage_mb
)
SELECT
    r.repository_id,
    'customers',
    'idx_customers_region',
    ARRAY['region'],
    '{}',
    FALSE,
    110.25
FROM repositories r
WHERE repository_name = 'commerce-platform';

INSERT INTO query_executions (
    workload_id,
    plan_hash,
    access_path,
    join_strategy,
    sort_method,
    rows_removed_by_filter,
    buffers_shared_hit,
    buffers_shared_read,
    execution_time_ms
)
SELECT
    workload_id,
    'baseline-plan-001',
    'Seq Scan on orders',
    'Hash Join',
    'quicksort',
    2189000,
    18450,
    76000,
    1842.31
FROM query_workloads
WHERE workload_name = 'monthly-completed-orders';

INSERT INTO query_executions (
    workload_id,
    plan_hash,
    access_path,
    join_strategy,
    sort_method,
    rows_removed_by_filter,
    buffers_shared_hit,
    buffers_shared_read,
    execution_time_ms
)
SELECT
    workload_id,
    'optimized-plan-002',
    'Index Only Scan on idx_orders_status_created_covering',
    'Nested Loop',
    'quicksort',
    0,
    29400,
    4100,
    312.87
FROM query_workloads
WHERE workload_name = 'monthly-completed-orders';

INSERT INTO optimization_findings (
    workload_id,
    severity,
    category,
    finding,
    recommendation
)
SELECT
    workload_id,
    'high',
    'scan',
    'Baseline execution scans most rows in orders.',
    'Use a selective composite index aligned with status and created_at predicates.'
FROM query_workloads
WHERE workload_name = 'monthly-completed-orders';

INSERT INTO optimization_findings (
    workload_id,
    severity,
    category,
    finding,
    recommendation
)
SELECT
    workload_id,
    'high',
    'cardinality',
    'Estimated and actual row counts differ materially.',
    'Refresh statistics and investigate data-distribution changes.'
FROM query_workloads
WHERE workload_name = 'monthly-completed-orders';

INSERT INTO optimization_findings (
    workload_id,
    severity,
    category,
    finding,
    recommendation
)
SELECT
    workload_id,
    'medium',
    'index',
    'Covering index increases storage and write maintenance cost.',
    'Retain only when workload frequency justifies the additional index footprint.'
FROM query_workloads
WHERE workload_name = 'monthly-completed-orders';

-- ============================================================
-- REPORTING VIEW
-- ============================================================

CREATE VIEW workload_performance_report AS
SELECT
    w.workload_id,
    r.repository_name,
    w.workload_name,
    w.status,
    w.estimated_rows,
    w.actual_rows,
    CASE
        WHEN w.estimated_rows IS NULL
          OR w.estimated_rows = 0
        THEN NULL
        ELSE ROUND(
            w.actual_rows::numeric / w.estimated_rows,
            4
        )
    END AS actual_to_estimated_ratio,
    w.estimated_cost,
    w.actual_duration_ms,
    COUNT(e.execution_id) AS execution_count,
    MAX(e.execution_time_ms) AS latest_execution_ms
FROM query_workloads w
LEFT JOIN repositories r
    ON r.repository_id = w.repository_id
LEFT JOIN query_executions e
    ON e.workload_id = w.workload_id
GROUP BY
    w.workload_id,
    r.repository_name,
    w.workload_name,
    w.status,
    w.estimated_rows,
    w.actual_rows,
    w.estimated_cost,
    w.actual_duration_ms;

-- ============================================================
-- PLAN-REGRESSION VIEW
-- ============================================================

CREATE VIEW plan_regression_report AS
WITH execution_ranked AS (
    SELECT
        e.*,
        ROW_NUMBER() OVER (
            PARTITION BY workload_id
            ORDER BY captured_at DESC
        ) AS rn
    FROM query_executions e
)
SELECT
    w.workload_name,
    old_plan.execution_time_ms AS previous_execution_ms,
    latest_plan.execution_time_ms AS latest_execution_ms,
    ROUND(
        (
            latest_plan.execution_time_ms
            - old_plan.execution_time_ms
        ) / NULLIF(old_plan.execution_time_ms, 0) * 100,
        2
    ) AS execution_change_percent
FROM query_workloads w
JOIN execution_ranked latest_plan
    ON latest_plan.workload_id = w.workload_id
   AND latest_plan.rn = 1
JOIN execution_ranked old_plan
    ON old_plan.workload_id = w.workload_id
   AND old_plan.rn = 2;

-- ============================================================
-- VALIDATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_workload(
    p_workload_id BIGINT
)
RETURNS TABLE (
    workload_id BIGINT,
    issue TEXT,
    severity TEXT
)
LANGUAGE SQL
AS $$
    SELECT
        w.workload_id,
        'Actual row count is substantially higher than estimated'::TEXT,
        'high'::TEXT
    FROM query_workloads w
    WHERE w.workload_id = p_workload_id
      AND w.estimated_rows IS NOT NULL
      AND w.estimated_rows > 0
      AND w.actual_rows > w.estimated_rows * 2

    UNION ALL

    SELECT
        w.workload_id,
        'Actual row count is substantially lower than estimated',
        'medium'
    FROM query_workloads w
    WHERE w.workload_id = p_workload_id
      AND w.estimated_rows IS NOT NULL
      AND w.estimated_rows > 0
      AND w.actual_rows < w.estimated_rows / 2

    UNION ALL

    SELECT
        w.workload_id,
        'Query failed and requires investigation',
        'critical'
    FROM query_workloads w
    WHERE w.workload_id = p_workload_id
      AND w.status = 'failed';
$$;

-- ============================================================
-- TRANSACTIONAL OPTIMIZATION WORKFLOW
-- ============================================================

BEGIN;

INSERT INTO optimization_findings (
    workload_id,
    severity,
    category,
    finding,
    recommendation
)
SELECT
    w.workload_id,
    v.severity,
    CASE
        WHEN v.severity = 'critical' THEN 'cardinality'
        ELSE 'statistics'
    END,
    v.issue,
    CASE
        WHEN v.severity = 'critical'
            THEN 'Inspect the failed execution and validate query assumptions.'
        ELSE 'Compare planner statistics with actual data distribution.'
    END
FROM query_workloads w
CROSS JOIN LATERAL validate_workload(w.workload_id) v
WHERE w.workload_name IN (
    'monthly-completed-orders',
    'failed-cardinality-analysis'
);

COMMIT;

-- ============================================================
-- RETRIEVAL: SLOWEST WORKLOADS
-- ============================================================

SELECT
    workload_name,
    actual_duration_ms,
    estimated_rows,
    actual_rows
FROM workload_performance_report
WHERE actual_duration_ms IS NOT NULL
ORDER BY actual_duration_ms DESC;

-- ============================================================
-- VALIDATION: CARDINALITY ESTIMATION
-- ============================================================

SELECT
    workload_name,
    estimated_rows,
    actual_rows,
    actual_to_estimated_ratio
FROM workload_performance_report
WHERE estimated_rows IS NOT NULL
  AND actual_rows IS NOT NULL
  AND (
      actual_rows > estimated_rows * 2
      OR actual_rows < estimated_rows / 2
  )
ORDER BY ABS(
    LN(
        GREATEST(
            actual_to_estimated_ratio,
            0.000001
        )
    )
) DESC;

-- ============================================================
-- INDEX COST / BENEFIT REPORT
-- ============================================================

SELECT
    i.table_name,
    i.index_name,
    i.indexed_columns,
    i.included_columns,
    i.estimated_storage_mb,
    COUNT(e.execution_id) AS observed_executions
FROM indexes i
LEFT JOIN query_workloads w
    ON w.repository_id = i.repository_id
LEFT JOIN query_executions e
    ON e.workload_id = w.workload_id
GROUP BY
    i.table_name,
    i.index_name,
    i.indexed_columns,
    i.included_columns,
    i.estimated_storage_mb
ORDER BY i.estimated_storage_mb DESC;

-- ============================================================
-- UNRESOLVED OPTIMIZATION FINDINGS
-- ============================================================

SELECT
    w.workload_name,
    f.severity,
    f.category,
    f.finding,
    f.recommendation
FROM optimization_findings f
JOIN query_workloads w
    ON w.workload_id = f.workload_id
WHERE NOT f.resolved
ORDER BY
    CASE f.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        ELSE 4
    END,
    w.workload_name;

-- ============================================================
-- CTE: BUFFER EFFICIENCY
-- ============================================================

WITH buffer_metrics AS (
    SELECT
        w.workload_name,
        e.execution_id,
        e.buffers_shared_hit,
        e.buffers_shared_read,
        e.execution_time_ms,
        e.buffers_shared_hit
            + e.buffers_shared_read AS total_buffers
    FROM query_executions e
    JOIN query_workloads w
        ON w.workload_id = e.workload_id
)
SELECT
    workload_name,
    execution_id,
    total_buffers,
    ROUND(
        buffers_shared_hit::numeric
        / NULLIF(total_buffers, 0),
        4
    ) AS cache_hit_ratio,
    execution_time_ms
FROM buffer_metrics
ORDER BY execution_time_ms DESC;

-- ============================================================
-- REAL PostgreSQL PLAN INSPECTION
-- ============================================================
-- The following query is intentionally read-only and uses
-- PostgreSQL's planner without executing the target query.

EXPLAIN
SELECT c.region, SUM(o.total_amount)
FROM (
    SELECT customer_id, total_amount
    FROM optimization_lab.query_workloads
    WHERE status = 'completed'
) AS o
JOIN (
    SELECT repository_id, repository_name AS region
    FROM optimization_lab.repositories
) AS c
    ON c.repository_id = o.customer_id
GROUP BY c.region;

-- ============================================================
-- ANALYZE COMMAND
-- ============================================================
-- PostgreSQL normally performs ANALYZE on real application tables.
-- This demonstration records the operational intent rather than
-- referencing nonexistent orders/customers tables.

ANALYZE optimization_lab.query_workloads;
ANALYZE optimization_lab.query_executions;
ANALYZE optimization_lab.optimization_findings;
