-- ============================================================
-- TEST COVERAGE MANAGEMENT DATABASE
-- PostgreSQL
--
-- Features:
-- 1. Test suites and test cases
-- 2. Source components and coverage obligations
-- 3. Test executions and execution history
-- 4. Statement, branch and function coverage
-- 5. Coverage aggregation and reporting
-- 6. Threshold-based quality gates
-- 7. Test failure classification
-- 8. Transaction-safe test result processing
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS test_coverage;

SET search_path TO test_coverage, public;

-- ------------------------------------------------------------
-- 1. ENUM TYPES
-- ------------------------------------------------------------

CREATE TYPE coverage_metric AS ENUM (
    'STATEMENT',
    'BRANCH',
    'FUNCTION'
);

CREATE TYPE test_status AS ENUM (
    'PENDING',
    'RUNNING',
    'PASSED',
    'FAILED',
    'SKIPPED'
);

CREATE TYPE failure_category AS ENUM (
    'ASSERTION',
    'VALIDATION',
    'UNEXPECTED',
    'TIMEOUT',
    'ENVIRONMENT'
);

CREATE TYPE gate_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED'
);

-- ------------------------------------------------------------
-- 2. PROJECTS
-- ------------------------------------------------------------

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(project_name)) > 0)
);

-- ------------------------------------------------------------
-- 3. SOURCE COMPONENTS
-- ------------------------------------------------------------

CREATE TABLE source_components (
    component_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    component_name VARCHAR(150) NOT NULL,
    language VARCHAR(50) NOT NULL,
    source_path VARCHAR(500) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (project_id, component_name),
    UNIQUE (project_id, source_path),

    CHECK (length(trim(component_name)) > 0),
    CHECK (length(trim(source_path)) > 0)
);

-- ------------------------------------------------------------
-- 4. TEST SUITES
-- ------------------------------------------------------------

CREATE TABLE test_suites (
    suite_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    suite_name VARCHAR(150) NOT NULL,
    suite_type VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (project_id, suite_name),

    CHECK (
        suite_type IN (
            'UNIT',
            'INTEGRATION',
            'SYSTEM',
            'REGRESSION',
            'SECURITY'
        )
    )
);

-- ------------------------------------------------------------
-- 5. TEST CASES
-- ------------------------------------------------------------

CREATE TABLE test_cases (
    test_case_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    suite_id BIGINT NOT NULL REFERENCES test_suites(suite_id),
    test_code VARCHAR(80) NOT NULL UNIQUE,
    test_name VARCHAR(200) NOT NULL,
    description TEXT,
    priority SMALLINT NOT NULL DEFAULT 2,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    CHECK (priority BETWEEN 1 AND 5),
    CHECK (length(trim(test_name)) > 0)
);

-- ------------------------------------------------------------
-- 6. COVERAGE OBLIGATIONS
--
-- Each row represents one measurable statement, branch,
-- or function that must be exercised.
-- ------------------------------------------------------------

CREATE TABLE coverage_items (
    coverage_item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    component_id BIGINT NOT NULL
        REFERENCES source_components(component_id),
    metric coverage_metric NOT NULL,
    item_key VARCHAR(200) NOT NULL,
    description TEXT,
    critical BOOLEAN NOT NULL DEFAULT FALSE,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (component_id, metric, item_key),

    CHECK (length(trim(item_key)) > 0)
);

-- ------------------------------------------------------------
-- 7. TEST EXECUTION RUNS
-- ------------------------------------------------------------

CREATE TABLE test_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    environment VARCHAR(100) NOT NULL,
    source_revision VARCHAR(100) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CHECK (length(trim(environment)) > 0),
    CHECK (length(trim(source_revision)) > 0),
    CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

-- ------------------------------------------------------------
-- 8. TEST EXECUTION RESULTS
-- ------------------------------------------------------------

CREATE TABLE test_results (
    test_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES test_runs(run_id),
    test_case_id BIGINT NOT NULL REFERENCES test_cases(test_case_id),
    status test_status NOT NULL DEFAULT 'PENDING',
    failure_type failure_category,
    error_message TEXT,
    duration_ms NUMERIC(12, 3),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (run_id, test_case_id),

    CHECK (duration_ms IS NULL OR duration_ms >= 0),

    CHECK (
        (status = 'FAILED' AND failure_type IS NOT NULL)
        OR
        (status <> 'FAILED' AND failure_type IS NULL)
    )
);

-- ------------------------------------------------------------
-- 9. COVERAGE OBSERVATIONS
--
-- Records which measurable source items were executed
-- during a particular test run.
-- ------------------------------------------------------------

CREATE TABLE coverage_observations (
    observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES test_runs(run_id),
    coverage_item_id BIGINT NOT NULL
        REFERENCES coverage_items(coverage_item_id),
    execution_count BIGINT NOT NULL DEFAULT 1,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (run_id, coverage_item_id),

    CHECK (execution_count > 0)
);

-- ------------------------------------------------------------
-- 10. COVERAGE POLICIES
-- ------------------------------------------------------------

CREATE TABLE coverage_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    policy_name VARCHAR(150) NOT NULL,
    minimum_statement NUMERIC(5, 2) NOT NULL DEFAULT 80,
    minimum_branch NUMERIC(5, 2) NOT NULL DEFAULT 80,
    minimum_function NUMERIC(5, 2) NOT NULL DEFAULT 80,
    minimum_passing_tests INTEGER NOT NULL DEFAULT 1,
    block_on_failed_tests BOOLEAN NOT NULL DEFAULT TRUE,
    block_on_uncovered_critical BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (project_id, policy_name),

    CHECK (minimum_statement BETWEEN 0 AND 100),
    CHECK (minimum_branch BETWEEN 0 AND 100),
    CHECK (minimum_function BETWEEN 0 AND 100),
    CHECK (minimum_passing_tests >= 0)
);

-- ------------------------------------------------------------
-- 11. QUALITY GATE RESULTS
-- ------------------------------------------------------------

CREATE TABLE quality_gate_results (
    gate_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES test_runs(run_id),
    policy_id BIGINT NOT NULL REFERENCES coverage_policies(policy_id),
    status gate_status NOT NULL DEFAULT 'PENDING',
    statement_percentage NUMERIC(6, 2),
    branch_percentage NUMERIC(6, 2),
    function_percentage NUMERIC(6, 2),
    evaluated_at TIMESTAMPTZ,
    failure_reason TEXT,

    UNIQUE (run_id, policy_id)
);

-- ------------------------------------------------------------
-- 12. PERFORMANCE INDEXES
-- ------------------------------------------------------------

CREATE INDEX idx_components_project
    ON source_components(project_id);

CREATE INDEX idx_test_cases_suite
    ON test_cases(suite_id);

CREATE INDEX idx_test_results_run_status
    ON test_results(run_id, status);

CREATE INDEX idx_test_results_case
    ON test_results(test_case_id);

CREATE INDEX idx_coverage_items_component_metric
    ON coverage_items(component_id, metric)
    WHERE active = TRUE;

CREATE INDEX idx_coverage_observations_run
    ON coverage_observations(run_id, coverage_item_id);

CREATE INDEX idx_test_runs_project_started
    ON test_runs(project_id, started_at DESC);

CREATE INDEX idx_active_policies
    ON coverage_policies(project_id)
    WHERE active = TRUE;

-- ------------------------------------------------------------
-- 13. SAMPLE PROJECT
-- ------------------------------------------------------------

INSERT INTO projects (project_name, description)
VALUES (
    'Financial Calculation Service',
    'Coverage monitoring for a numerical calculation service'
);

INSERT INTO source_components (
    project_id,
    component_name,
    language,
    source_path
)
VALUES
(
    1,
    'DivisionService',
    'Python',
    'src/division_service.py'
),
(
    1,
    'ClassificationService',
    'Python',
    'src/classification_service.py'
);

INSERT INTO test_suites (
    project_id,
    suite_name,
    suite_type
)
VALUES
(1, 'Division Unit Tests', 'UNIT'),
(1, 'Classification Unit Tests', 'UNIT');

INSERT INTO test_cases (
    suite_id,
    test_code,
    test_name,
    priority
)
VALUES
(1, 'TC-001', 'Normal division', 1),
(1, 'TC-002', 'Negative division', 2),
(1, 'TC-003', 'Division by zero', 1),
(1, 'TC-004', 'Invalid numerator', 2),
(2, 'TC-005', 'Negative classification', 1),
(2, 'TC-006', 'Zero classification', 1),
(2, 'TC-007', 'Positive classification', 2),
(2, 'TC-008', 'Large number classification', 1),
(2, 'TC-009', 'Invalid classification', 2);

-- ------------------------------------------------------------
-- 14. REGISTER COVERAGE ITEMS
-- ------------------------------------------------------------

INSERT INTO coverage_items (
    component_id,
    metric,
    item_key,
    description,
    critical
)
VALUES
-- Division statements
(1, 'STATEMENT', 'divide.validation', 'Validate numeric inputs', TRUE),
(1, 'STATEMENT', 'divide.calculation', 'Perform division', TRUE),

-- Division branches
(1, 'BRANCH', 'divide.zero', 'Zero denominator branch', TRUE),

-- Division functions
(1, 'FUNCTION', 'safe_divide', 'Division function', TRUE),

-- Classification statements
(2, 'STATEMENT', 'classify.validation', 'Validate input', TRUE),
(2, 'STATEMENT', 'classify.negative', 'Negative return statement', FALSE),
(2, 'STATEMENT', 'classify.zero', 'Zero return statement', FALSE),
(2, 'STATEMENT', 'classify.positive', 'Positive return statement', FALSE),
(2, 'STATEMENT', 'classify.large', 'Large number return statement', TRUE),

-- Classification branches
(2, 'BRANCH', 'classify.negative', 'Negative condition', FALSE),
(2, 'BRANCH', 'classify.zero', 'Zero condition', FALSE),
(2, 'BRANCH', 'classify.positive', 'Positive condition', FALSE),
(2, 'BRANCH', 'classify.large', 'Large number condition', TRUE),

-- Classification function
(2, 'FUNCTION', 'classify_number', 'Number classification function', TRUE);

-- ------------------------------------------------------------
-- 15. COVERAGE POLICY
-- ------------------------------------------------------------

INSERT INTO coverage_policies (
    project_id,
    policy_name,
    minimum_statement,
    minimum_branch,
    minimum_function,
    minimum_passing_tests,
    block_on_failed_tests,
    block_on_uncovered_critical
)
VALUES (
    1,
    'Production Release Policy',
    80,
    80,
    80,
    9,
    TRUE,
    TRUE
);

-- ------------------------------------------------------------
-- 16. SAMPLE TEST RUN
-- ------------------------------------------------------------

INSERT INTO test_runs (
    project_id,
    environment,
    source_revision
)
VALUES (
    1,
    'CI',
    'release-2026-11-06'
);

INSERT INTO test_results (
    run_id,
    test_case_id,
    status,
    duration_ms
)
VALUES
(1, 1, 'PASSED', 2.1),
(1, 2, 'PASSED', 1.8),
(1, 3, 'PASSED', 1.2),
(1, 4, 'PASSED', 1.4),
(1, 5, 'PASSED', 1.3),
(1, 6, 'PASSED', 1.1),
(1, 7, 'PASSED', 1.2),
(1, 8, 'PASSED', 1.5),
(1, 9, 'PASSED', 1.7);

-- ------------------------------------------------------------
-- 17. SAMPLE COVERAGE OBSERVATIONS
-- ------------------------------------------------------------

INSERT INTO coverage_observations (
    run_id,
    coverage_item_id,
    execution_count
)
SELECT
    1,
    coverage_item_id,
    CASE
        WHEN item_key = 'divide.validation' THEN 4
        WHEN item_key = 'divide.calculation' THEN 2
        WHEN item_key = 'classify.validation' THEN 5
        ELSE 1
    END
FROM coverage_items
WHERE item_key IN (
    'divide.validation',
    'divide.calculation',
    'divide.zero',
    'safe_divide',
    'classify.validation',
    'classify.negative',
    'classify.zero',
    'classify.positive',
    'classify.large',
    'classify_number'
);

-- ------------------------------------------------------------
-- 18. COVERAGE SUMMARY VIEW
-- ------------------------------------------------------------

CREATE VIEW v_coverage_summary AS
SELECT
    p.project_id,
    p.project_name,
    ci.metric,
    COUNT(ci.coverage_item_id) AS total_items,
    COUNT(co.observation_id) AS covered_items,
    COUNT(ci.coverage_item_id)
        - COUNT(co.observation_id) AS uncovered_items,

    ROUND(
        CASE
            WHEN COUNT(ci.coverage_item_id) = 0 THEN 100
            ELSE
                100.0 * COUNT(co.observation_id)
                / COUNT(ci.coverage_item_id)
        END,
        2
    ) AS coverage_percentage

FROM projects p
JOIN source_components sc
    ON sc.project_id = p.project_id
JOIN coverage_items ci
    ON ci.component_id = sc.component_id
    AND ci.active = TRUE

LEFT JOIN coverage_observations co
    ON co.coverage_item_id = ci.coverage_item_id
    AND co.run_id = 1

GROUP BY
    p.project_id,
    p.project_name,
    ci.metric;

-- ------------------------------------------------------------
-- 19. FUNCTION: GET COVERAGE FOR A RUN
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_run_coverage(
    p_run_id BIGINT,
    p_metric coverage_metric
)
RETURNS TABLE (
    total_items BIGINT,
    covered_items BIGINT,
    uncovered_items BIGINT,
    coverage_percentage NUMERIC
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        COUNT(ci.coverage_item_id),

        COUNT(co.observation_id),

        COUNT(ci.coverage_item_id)
            - COUNT(co.observation_id),

        ROUND(
            CASE
                WHEN COUNT(ci.coverage_item_id) = 0 THEN 100
                ELSE
                    100.0 * COUNT(co.observation_id)
                    / COUNT(ci.coverage_item_id)
            END,
            2
        )

    FROM test_runs tr
    JOIN projects p
        ON p.project_id = tr.project_id
    JOIN source_components sc
        ON sc.project_id = p.project_id
    JOIN coverage_items ci
        ON ci.component_id = sc.component_id
        AND ci.metric = p_metric
        AND ci.active = TRUE

    LEFT JOIN coverage_observations co
        ON co.coverage_item_id = ci.coverage_item_id
        AND co.run_id = tr.run_id

    WHERE tr.run_id = p_run_id;
$$;

-- ------------------------------------------------------------
-- 20. FUNCTION: FIND UNCOVERED ITEMS
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION get_uncovered_items(
    p_run_id BIGINT
)
RETURNS TABLE (
    component_name VARCHAR,
    metric coverage_metric,
    item_key VARCHAR,
    critical BOOLEAN
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        sc.component_name::VARCHAR,
        ci.metric,
        ci.item_key::VARCHAR,
        ci.critical

    FROM test_runs tr
    JOIN source_components sc
        ON sc.project_id = tr.project_id
    JOIN coverage_items ci
        ON ci.component_id = sc.component_id
        AND ci.active = TRUE

    LEFT JOIN coverage_observations co
        ON co.coverage_item_id = ci.coverage_item_id
        AND co.run_id = tr.run_id

    WHERE tr.run_id = p_run_id
      AND co.observation_id IS NULL

    ORDER BY ci.critical DESC, sc.component_name, ci.item_key;
$$;

-- ------------------------------------------------------------
-- 21. PROCEDURE: EVALUATE QUALITY GATE
--
-- Coverage percentages and test results are evaluated
-- against an active policy.
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE evaluate_quality_gate(
    p_run_id BIGINT,
    p_policy_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_policy coverage_policies%ROWTYPE;
    v_project_id BIGINT;

    v_statement NUMERIC;
    v_branch NUMERIC;
    v_function NUMERIC;

    v_passed INTEGER;
    v_failed INTEGER;

    v_uncovered_critical INTEGER;
    v_status gate_status;
    v_reason TEXT := '';
BEGIN
    SELECT *
    INTO v_policy
    FROM coverage_policies
    WHERE policy_id = p_policy_id
      AND active = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active coverage policy not found';
    END IF;

    SELECT project_id
    INTO v_project_id
    FROM test_runs
    WHERE run_id = p_run_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Test run not found';
    END IF;

    IF v_project_id <> v_policy.project_id THEN
        RAISE EXCEPTION 'Policy and run belong to different projects';
    END IF;

    SELECT coverage_percentage
    INTO v_statement
    FROM get_run_coverage(p_run_id, 'STATEMENT');

    SELECT coverage_percentage
    INTO v_branch
    FROM get_run_coverage(p_run_id, 'BRANCH');

    SELECT coverage_percentage
    INTO v_function
    FROM get_run_coverage(p_run_id, 'FUNCTION');

    SELECT
        COUNT(*) FILTER (WHERE status = 'PASSED'),
        COUNT(*) FILTER (
            WHERE status = 'FAILED'
               OR status IN ('PENDING', 'RUNNING')
        )
    INTO v_passed, v_failed
    FROM test_results
    WHERE run_id = p_run_id;

    SELECT COUNT(*)
    INTO v_uncovered_critical
    FROM get_uncovered_items(p_run_id)
    WHERE critical = TRUE;

    IF v_statement < v_policy.minimum_statement THEN
        v_reason := v_reason || 'Statement coverage below threshold; ';
    END IF;

    IF v_branch < v_policy.minimum_branch THEN
        v_reason := v_reason || 'Branch coverage below threshold; ';
    END IF;

    IF v_function < v_policy.minimum_function THEN
        v_reason := v_reason || 'Function coverage below threshold; ';
    END IF;

    IF v_passed < v_policy.minimum_passing_tests THEN
        v_reason := v_reason || 'Insufficient passing tests; ';
    END IF;

    IF v_policy.block_on_failed_tests AND v_failed > 0 THEN
        v_reason := v_reason || 'Failed or incomplete tests exist; ';
    END IF;

    IF v_policy.block_on_uncovered_critical
       AND v_uncovered_critical > 0 THEN
        v_reason := v_reason || 'Critical coverage items uncovered; ';
    END IF;

    v_status := CASE
        WHEN v_reason = '' THEN 'PASSED'::gate_status
        ELSE 'FAILED'::gate_status
    END;

    INSERT INTO quality_gate_results (
        run_id,
        policy_id,
        status,
        statement_percentage,
        branch_percentage,
        function_percentage,
        evaluated_at,
        failure_reason
    )
    VALUES (
        p_run_id,
        p_policy_id,
        v_status,
        v_statement,
        v_branch,
        v_function,
        CURRENT_TIMESTAMP,
        NULLIF(v_reason, '')
    )
    ON CONFLICT (run_id, policy_id)
    DO UPDATE SET
        status = EXCLUDED.status,
        statement_percentage = EXCLUDED.statement_percentage,
        branch_percentage = EXCLUDED.branch_percentage,
        function_percentage = EXCLUDED.function_percentage,
        evaluated_at = EXCLUDED.evaluated_at,
        failure_reason = EXCLUDED.failure_reason;

END;
$$;

-- ------------------------------------------------------------
-- 22. VALIDATION TRIGGER
--
-- Coverage observations must belong to the same project
-- as the associated test run.
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_coverage_observation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_run_project BIGINT;
    v_component_project BIGINT;
BEGIN
    SELECT project_id
    INTO v_run_project
    FROM test_runs
    WHERE run_id = NEW.run_id;

    SELECT sc.project_id
    INTO v_component_project
    FROM coverage_items ci
    JOIN source_components sc
        ON sc.component_id = ci.component_id
    WHERE ci.coverage_item_id = NEW.coverage_item_id;

    IF v_run_project IS DISTINCT FROM v_component_project THEN
        RAISE EXCEPTION
            'Coverage observation crosses project boundaries';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_coverage_observation
BEFORE INSERT OR UPDATE
ON coverage_observations
FOR EACH ROW
EXECUTE FUNCTION validate_coverage_observation();

-- ------------------------------------------------------------
-- 23. VALIDATION: PREVENT FALSE COMPLETION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_run_completion()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL THEN

        IF EXISTS (
            SELECT 1
            FROM test_results
            WHERE run_id = NEW.run_id
              AND status IN ('PENDING', 'RUNNING')
        ) THEN
            RAISE EXCEPTION
                'Cannot complete a run with pending or running tests';
        END IF;

    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_run_completion
BEFORE UPDATE OF completed_at
ON test_runs
FOR EACH ROW
EXECUTE FUNCTION validate_run_completion();

-- ------------------------------------------------------------
-- 24. TRANSACTIONAL QUALITY GATE EVALUATION
-- ------------------------------------------------------------

CALL evaluate_quality_gate(1, 1);

UPDATE test_runs
SET completed_at = CURRENT_TIMESTAMP
WHERE run_id = 1;

-- ------------------------------------------------------------
-- 25. RETRIEVAL QUERIES
-- ------------------------------------------------------------

-- All project components and their source files.
SELECT
    p.project_name,
    sc.component_name,
    sc.language,
    sc.source_path
FROM projects p
JOIN source_components sc
    ON sc.project_id = p.project_id
ORDER BY sc.component_name;

-- All test cases and their suite classifications.
SELECT
    ts.suite_name,
    ts.suite_type,
    tc.test_code,
    tc.test_name,
    tc.priority
FROM test_suites ts
JOIN test_cases tc
    ON tc.suite_id = ts.suite_id
ORDER BY ts.suite_name, tc.priority;

-- ------------------------------------------------------------
-- 26. COVERAGE AGGREGATION
-- ------------------------------------------------------------

SELECT *
FROM v_coverage_summary
ORDER BY metric;

-- Individual metric evaluation.
SELECT *
FROM get_run_coverage(1, 'STATEMENT');

SELECT *
FROM get_run_coverage(1, 'BRANCH');

SELECT *
FROM get_run_coverage(1, 'FUNCTION');

-- ------------------------------------------------------------
-- 27. UNCOVERED ITEM ANALYSIS
-- ------------------------------------------------------------

SELECT *
FROM get_uncovered_items(1);

-- Critical coverage gaps.
SELECT *
FROM get_uncovered_items(1)
WHERE critical = TRUE;

-- ------------------------------------------------------------
-- 28. TEST FAILURE REPORT
-- ------------------------------------------------------------

SELECT
    tc.test_code,
    tc.test_name,
    tr.status,
    tr.failure_type,
    tr.error_message,
    tr.duration_ms
FROM test_results tr
JOIN test_cases tc
    ON tc.test_case_id = tr.test_case_id
WHERE tr.run_id = 1
ORDER BY tr.status, tc.priority;

-- ------------------------------------------------------------
-- 29. EXECUTION PERFORMANCE REPORT
-- ------------------------------------------------------------

SELECT
    tc.test_name,
    tr.duration_ms,
    tr.status,
    ROUND(
        AVG(tr.duration_ms) OVER (),
        3
    ) AS average_execution_ms
FROM test_results tr
JOIN test_cases tc
    ON tc.test_case_id = tr.test_case_id
WHERE tr.run_id = 1
ORDER BY tr.duration_ms DESC;

-- ------------------------------------------------------------
-- 30. QUALITY GATE REPORT
-- ------------------------------------------------------------

SELECT
    p.project_name,
    cp.policy_name,
    qg.status,
    qg.statement_percentage,
    qg.branch_percentage,
    qg.function_percentage,
    qg.failure_reason,
    qg.evaluated_at
FROM quality_gate_results qg
JOIN coverage_policies cp
    ON cp.policy_id = qg.policy_id
JOIN projects p
    ON p.project_id = cp.project_id
WHERE qg.run_id = 1;

-- ------------------------------------------------------------
-- 31. HISTORICAL COVERAGE OBSERVATION REPORT
-- ------------------------------------------------------------

SELECT
    ci.metric,
    ci.item_key,
    SUM(co.execution_count) AS total_executions,
    COUNT(DISTINCT co.run_id) AS number_of_runs
FROM coverage_items ci
LEFT JOIN coverage_observations co
    ON co.coverage_item_id = ci.coverage_item_id
GROUP BY ci.metric, ci.item_key
ORDER BY ci.metric, ci.item_key;

COMMIT;

-- ============================================================
-- DATABASE WORKFLOW
--
-- Project registration
--       |
-- Source component registration
--       |
-- Coverage obligation registration
--       |
-- Test suite and test case registration
--       |
-- Test execution
--       |
-- Coverage observations
--       |
-- Metric aggregation
--       |
-- Policy evaluation
--       |
-- Quality gate decision
-- ============================================================
