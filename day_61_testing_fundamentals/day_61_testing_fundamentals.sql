DROP SCHEMA IF EXISTS testing_fundamentals CASCADE;
CREATE SCHEMA testing_fundamentals;
SET search_path = testing_fundamentals, public;

CREATE TYPE test_level AS ENUM ('unit', 'integration', 'system');
CREATE TYPE test_run_status AS ENUM ('passed', 'failed', 'skipped');
CREATE TYPE test_case_status AS ENUM ('active', 'disabled');

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_key TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT projects_key_format
        CHECK (project_key ~ '^[A-Z][A-Z0-9_-]{2,30}$')
);

CREATE TABLE test_suites (
    suite_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id)
        ON DELETE CASCADE,
    suite_name TEXT NOT NULL,
    test_level test_level NOT NULL,
    UNIQUE (project_id, suite_name)
);

CREATE TABLE test_cases (
    test_case_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    suite_id BIGINT NOT NULL REFERENCES test_suites(suite_id)
        ON DELETE CASCADE,
    case_key TEXT NOT NULL,
    case_name TEXT NOT NULL,
    status test_case_status NOT NULL DEFAULT 'active',
    expected_duration_ms INTEGER NOT NULL DEFAULT 0,
    UNIQUE (suite_id, case_key),
    CHECK (expected_duration_ms >= 0)
);

CREATE TABLE test_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id)
        ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    environment TEXT NOT NULL,
    status test_run_status NOT NULL,
    commit_sha TEXT NOT NULL,
    CHECK (length(commit_sha) >= 7),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

CREATE TABLE test_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES test_runs(run_id)
        ON DELETE CASCADE,
    test_case_id BIGINT NOT NULL REFERENCES test_cases(test_case_id)
        ON DELETE RESTRICT,
    status test_run_status NOT NULL,
    duration_ms INTEGER NOT NULL,
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (run_id, test_case_id),
    CHECK (duration_ms >= 0),
    CHECK (
        (status = 'failed' AND error_message IS NOT NULL)
        OR status <> 'failed'
    )
);

CREATE INDEX idx_test_cases_suite_level
    ON test_suites(project_id, test_level);

CREATE INDEX idx_test_runs_project_started
    ON test_runs(project_id, started_at DESC);

CREATE INDEX idx_test_results_run_status
    ON test_results(run_id, status);

CREATE INDEX idx_test_results_case
    ON test_results(test_case_id);

CREATE OR REPLACE FUNCTION validate_test_result_case()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    case_project BIGINT;
    run_project BIGINT;
BEGIN
    SELECT s.project_id
    INTO case_project
    FROM test_cases tc
    JOIN test_suites s ON s.suite_id = tc.suite_id
    WHERE tc.test_case_id = NEW.test_case_id;

    SELECT project_id
    INTO run_project
    FROM test_runs
    WHERE run_id = NEW.run_id;

    IF case_project IS NULL OR run_project IS NULL THEN
        RAISE EXCEPTION 'Test case or run does not exist';
    END IF;

    IF case_project <> run_project THEN
        RAISE EXCEPTION
            'Test result cannot connect cases and runs from different projects';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_test_result_case
BEFORE INSERT OR UPDATE ON test_results
FOR EACH ROW
EXECUTE FUNCTION validate_test_result_case();

CREATE OR REPLACE FUNCTION finish_run(
    p_run_id BIGINT,
    p_status test_run_status
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM test_runs
        WHERE run_id = p_run_id
    ) THEN
        RAISE EXCEPTION 'Unknown test run %', p_run_id;
    END IF;

    UPDATE test_runs
    SET finished_at = now(),
        status = p_status
    WHERE run_id = p_run_id;
END;
$$;

CREATE OR REPLACE VIEW test_run_report AS
SELECT
    r.run_id,
    p.project_key,
    r.environment,
    r.commit_sha,
    r.status AS run_status,
    COUNT(tr.result_id) AS executed_tests,
    COUNT(*) FILTER (WHERE tr.status = 'passed') AS passed_tests,
    COUNT(*) FILTER (WHERE tr.status = 'failed') AS failed_tests,
    COUNT(*) FILTER (WHERE tr.status = 'skipped') AS skipped_tests,
    COALESCE(SUM(tr.duration_ms), 0) AS total_duration_ms,
    CASE
        WHEN COUNT(tr.result_id) = 0 THEN 0
        ELSE ROUND(
            100.0 * COUNT(*) FILTER (WHERE tr.status = 'passed')
            / COUNT(tr.result_id),
            2
        )
    END AS pass_rate
FROM test_runs r
JOIN projects p ON p.project_id = r.project_id
LEFT JOIN test_results tr ON tr.run_id = r.run_id
GROUP BY
    r.run_id,
    p.project_key,
    r.environment,
    r.commit_sha,
    r.status;

INSERT INTO projects (project_key, name)
VALUES ('PAYMENTS', 'Payment Processing Service');

INSERT INTO test_suites (project_id, suite_name, test_level)
SELECT project_id, 'Money Rules', 'unit'
FROM projects
WHERE project_key = 'PAYMENTS';

INSERT INTO test_suites (project_id, suite_name, test_level)
SELECT project_id, 'Repository Service', 'integration'
FROM projects
WHERE project_key = 'PAYMENTS';

INSERT INTO test_suites (project_id, suite_name, test_level)
SELECT project_id, 'Customer Checkout', 'system'
FROM projects
WHERE project_key = 'PAYMENTS';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'UNIT-001', 'Calculate valid discount', 3
FROM test_suites
WHERE suite_name = 'Money Rules';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'UNIT-002', 'Reject negative total', 2
FROM test_suites
WHERE suite_name = 'Money Rules';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'INT-001', 'Persist and retrieve payment', 30
FROM test_suites
WHERE suite_name = 'Repository Service';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'INT-002', 'Reject duplicate payment', 25
FROM test_suites
WHERE suite_name = 'Repository Service';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'SYS-001', 'Complete checkout', 180
FROM test_suites
WHERE suite_name = 'Customer Checkout';

INSERT INTO test_cases (
    suite_id,
    case_key,
    case_name,
    expected_duration_ms
)
SELECT suite_id, 'SYS-002', 'Reject invalid checkout', 140
FROM test_suites
WHERE suite_name = 'Customer Checkout';

INSERT INTO test_runs (
    project_id,
    environment,
    status,
    commit_sha
)
SELECT project_id, 'ci', 'passed',
       '9f2a7c1d8e1234567890abcdef1234567890abcd'
FROM projects
WHERE project_key = 'PAYMENTS';

INSERT INTO test_runs (
    project_id,
    environment,
    status,
    commit_sha
)
SELECT project_id, 'ci', 'failed',
       'a8d41e2c9f1234567890abcdef1234567890abcd'
FROM projects
WHERE project_key = 'PAYMENTS';

INSERT INTO test_results (
    run_id,
    test_case_id,
    status,
    duration_ms,
    error_message
)
SELECT
    r.run_id,
    tc.test_case_id,
    CASE
        WHEN tc.case_key = 'SYS-002' AND r.status = 'failed'
            THEN 'Checkout validation rejected malformed payment data'
        ELSE 'passed'::test_run_status
    END,
    CASE tc.case_key
        WHEN 'UNIT-001' THEN 3
        WHEN 'UNIT-002' THEN 2
        WHEN 'INT-001' THEN 28
        WHEN 'INT-002' THEN 31
        WHEN 'SYS-001' THEN 175
        ELSE 151
    END,
    CASE
        WHEN tc.case_key = 'SYS-002' AND r.status = 'failed'
            THEN 'Checkout validation rejected malformed payment data'
        ELSE NULL
    END
FROM test_runs r
JOIN projects p ON p.project_id = r.project_id
JOIN test_cases tc ON tc.case_key IN (
    'UNIT-001',
    'UNIT-002',
    'INT-001',
    'INT-002',
    'SYS-001',
    'SYS-002'
)
WHERE p.project_key = 'PAYMENTS';

-- Retrieval: active test cases grouped by testing level.
SELECT
    s.test_level,
    tc.case_key,
    tc.case_name,
    tc.expected_duration_ms
FROM test_cases tc
JOIN test_suites s ON s.suite_id = tc.suite_id
WHERE tc.status = 'active'
ORDER BY s.test_level, tc.case_key;

-- Validation: failed cases require a diagnostic message.
SELECT result_id, run_id, test_case_id, error_message
FROM test_results
WHERE status = 'failed'
  AND (error_message IS NULL OR btrim(error_message) = '');

-- Aggregation and reporting.
SELECT *
FROM test_run_report
ORDER BY run_id;

-- Failure analysis by test level.
SELECT
    s.test_level,
    COUNT(*) AS total_results,
    COUNT(*) FILTER (WHERE tr.status = 'passed') AS passed,
    COUNT(*) FILTER (WHERE tr.status = 'failed') AS failed,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE tr.status = 'passed')
        / NULLIF(COUNT(*), 0),
        2
    ) AS pass_rate
FROM test_results tr
JOIN test_cases tc ON tc.test_case_id = tr.test_case_id
JOIN test_suites s ON s.suite_id = tc.suite_id
GROUP BY s.test_level
ORDER BY s.test_level;

-- Identify tests exceeding their expected duration.
SELECT
    tc.case_key,
    tc.case_name,
    tc.expected_duration_ms,
    tr.duration_ms,
    tr.duration_ms - tc.expected_duration_ms AS excess_ms
FROM test_results tr
JOIN test_cases tc ON tc.test_case_id = tr.test_case_id
WHERE tr.duration_ms > tc.expected_duration_ms
ORDER BY excess_ms DESC;

-- Transactional workflow: record a new run and its results atomically.
BEGIN;

WITH new_run AS (
    INSERT INTO test_runs (
        project_id,
        environment,
        status,
        commit_sha
    )
    SELECT
        project_id,
        'staging',
        'passed',
        'b71d91a1234567890abcdef1234567890abcdef12'
    FROM projects
    WHERE project_key = 'PAYMENTS'
    RETURNING run_id, project_id
)
INSERT INTO test_results (
    run_id,
    test_case_id,
    status,
    duration_ms
)
SELECT
    nr.run_id,
    tc.test_case_id,
    'passed',
    tc.expected_duration_ms
FROM new_run nr
JOIN test_cases tc ON tc.case_key IN ('UNIT-001', 'UNIT-002');

COMMIT;

-- The function updates completion time and preserves a single run identity.
SELECT finish_run(
    (
        SELECT run_id
        FROM test_runs
        WHERE commit_sha = 'b71d91a1234567890abcdef1234567890abcdef12'
    ),
    'passed'
);

SELECT *
FROM test_run_report
WHERE commit_sha = 'b71d91a1234567890abcdef1234567890abcdef12';
