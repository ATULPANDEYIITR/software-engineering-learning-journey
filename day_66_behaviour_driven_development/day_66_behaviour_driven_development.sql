-- ============================================================
-- BEHAVIOR-DRIVEN DEVELOPMENT
-- PostgreSQL acceptance testing and scenario management
--
-- Domain: E-commerce order placement
-- Concepts: Features, scenarios, Given-When-Then steps,
--           acceptance criteria, execution results,
--           scenario outlines, and reporting.
--
-- PostgreSQL 14+
-- ============================================================

BEGIN;

DROP SCHEMA IF EXISTS bdd CASCADE;

CREATE SCHEMA bdd;

SET search_path TO bdd, public;

-- ============================================================
-- 1. ENUM TYPES
-- ============================================================

CREATE TYPE scenario_status AS ENUM (
    'DRAFT',
    'READY',
    'ACTIVE',
    'RETIRED'
);

CREATE TYPE step_keyword AS ENUM (
    'GIVEN',
    'WHEN',
    'THEN',
    'AND'
);

CREATE TYPE execution_status AS ENUM (
    'RUNNING',
    'PASSED',
    'FAILED',
    'SKIPPED',
    'BLOCKED'
);

CREATE TYPE environment_type AS ENUM (
    'DEVELOPMENT',
    'TEST',
    'STAGING',
    'PRODUCTION'
);

-- ============================================================
-- 2. USERS AND ROLES
-- ============================================================

CREATE TABLE users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    role VARCHAR(30) NOT NULL
        CHECK (
            role IN (
                'BUSINESS_ANALYST',
                'DEVELOPER',
                'QA_ENGINEER',
                'PRODUCT_OWNER',
                'TEST_ADMIN'
            )
        ),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 3. FEATURES
-- ============================================================

CREATE TABLE features (
    feature_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    feature_key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    owner_id BIGINT NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(description)) > 0)
);

-- ============================================================
-- 4. SCENARIOS
-- ============================================================

CREATE TABLE scenarios (
    scenario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    feature_id BIGINT NOT NULL
        REFERENCES features(feature_id) ON DELETE CASCADE,

    scenario_key VARCHAR(80) NOT NULL UNIQUE,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,

    status scenario_status NOT NULL DEFAULT 'DRAFT',

    priority SMALLINT NOT NULL DEFAULT 3
        CHECK (priority BETWEEN 1 AND 5),

    created_by BIGINT NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (feature_id, name),

    CHECK (length(trim(name)) > 0)
);

-- ============================================================
-- 5. SCENARIO STEPS
-- ============================================================

CREATE TABLE scenario_steps (
    step_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    scenario_id BIGINT NOT NULL
        REFERENCES scenarios(scenario_id) ON DELETE CASCADE,

    sequence_number INTEGER NOT NULL
        CHECK (sequence_number > 0),

    keyword step_keyword NOT NULL,

    step_text TEXT NOT NULL,

    UNIQUE (scenario_id, sequence_number),

    CHECK (length(trim(step_text)) > 0)
);

CREATE INDEX idx_scenario_steps_order
    ON scenario_steps(scenario_id, sequence_number);

-- ============================================================
-- 6. SCENARIO OUTLINE EXAMPLES
-- ============================================================

CREATE TABLE scenario_examples (
    example_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    scenario_id BIGINT NOT NULL
        REFERENCES scenarios(scenario_id) ON DELETE CASCADE,

    example_name VARCHAR(150) NOT NULL,

    parameters JSONB NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (scenario_id, example_name),

    CHECK (jsonb_typeof(parameters) = 'object')
);

CREATE INDEX idx_scenario_examples_enabled
    ON scenario_examples(scenario_id)
    WHERE enabled = TRUE;

-- ============================================================
-- 7. TEST ENVIRONMENTS
-- ============================================================

CREATE TABLE test_environments (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    environment_name VARCHAR(100) NOT NULL UNIQUE,

    environment environment_type NOT NULL,

    base_url TEXT NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    CHECK (base_url ~ '^https?://')
);

-- ============================================================
-- 8. ACCEPTANCE CRITERIA
-- ============================================================

CREATE TABLE acceptance_criteria (
    criterion_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    scenario_id BIGINT NOT NULL
        REFERENCES scenarios(scenario_id) ON DELETE CASCADE,

    criterion_key VARCHAR(80) NOT NULL UNIQUE,

    criterion_description TEXT NOT NULL,

    mandatory BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (scenario_id, criterion_description),

    CHECK (length(trim(criterion_description)) > 0)
);

-- ============================================================
-- 9. SCENARIO EXECUTIONS
-- ============================================================

CREATE TABLE scenario_executions (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    scenario_id BIGINT NOT NULL
        REFERENCES scenarios(scenario_id),

    environment_id BIGINT NOT NULL
        REFERENCES test_environments(environment_id),

    executed_by BIGINT NOT NULL
        REFERENCES users(user_id),

    status execution_status NOT NULL DEFAULT 'RUNNING',

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    duration_ms NUMERIC(14, 3),

    error_message TEXT,

    build_reference VARCHAR(120),

    CHECK (
        completed_at IS NULL
        OR completed_at >= started_at
    ),

    CHECK (
        duration_ms IS NULL
        OR duration_ms >= 0
    ),

    CHECK (
        status NOT IN ('PASSED', 'FAILED', 'SKIPPED', 'BLOCKED')
        OR completed_at IS NOT NULL
    )
);

CREATE INDEX idx_executions_scenario_time
    ON scenario_executions(scenario_id, started_at DESC);

CREATE INDEX idx_executions_status
    ON scenario_executions(status, started_at DESC);

-- ============================================================
-- 10. INDIVIDUAL STEP EXECUTION RESULTS
-- ============================================================

CREATE TABLE step_execution_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    execution_id BIGINT NOT NULL
        REFERENCES scenario_executions(execution_id) ON DELETE CASCADE,

    step_id BIGINT NOT NULL
        REFERENCES scenario_steps(step_id),

    status execution_status NOT NULL,

    actual_result TEXT,

    duration_ms NUMERIC(14, 3)
        CHECK (duration_ms IS NULL OR duration_ms >= 0),

    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (execution_id, step_id)
);

CREATE INDEX idx_step_results_execution
    ON step_execution_results(execution_id, status);

-- ============================================================
-- 11. DATABASE INTEGRITY TRIGGERS
-- ============================================================

-- Scenario activation requires at least one Given, When, and Then.
CREATE OR REPLACE FUNCTION validate_scenario_activation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    given_count INTEGER;
    when_count INTEGER;
    then_count INTEGER;
BEGIN
    IF NEW.status = 'ACTIVE'
       AND OLD.status <> 'ACTIVE' THEN

        SELECT
            COUNT(*) FILTER (WHERE keyword = 'GIVEN'),
            COUNT(*) FILTER (WHERE keyword = 'WHEN'),
            COUNT(*) FILTER (WHERE keyword = 'THEN')
        INTO given_count, when_count, then_count
        FROM scenario_steps
        WHERE scenario_id = NEW.scenario_id;

        IF given_count = 0
           OR when_count = 0
           OR then_count = 0 THEN

            RAISE EXCEPTION
                'Scenario % requires Given, When and Then steps',
                NEW.scenario_key;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_scenario_activation
BEFORE UPDATE OF status ON scenarios
FOR EACH ROW
EXECUTE FUNCTION validate_scenario_activation();

-- Prevent a scenario from being activated with incomplete
-- mandatory acceptance criteria.
CREATE OR REPLACE FUNCTION validate_mandatory_criteria()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    mandatory_count INTEGER;
BEGIN
    IF NEW.status = 'ACTIVE'
       AND OLD.status <> 'ACTIVE' THEN

        SELECT COUNT(*)
        INTO mandatory_count
        FROM acceptance_criteria
        WHERE scenario_id = NEW.scenario_id
          AND mandatory = TRUE;

        IF mandatory_count = 0 THEN
            RAISE EXCEPTION
                'Active scenarios require mandatory acceptance criteria';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_mandatory_criteria
BEFORE UPDATE OF status ON scenarios
FOR EACH ROW
EXECUTE FUNCTION validate_mandatory_criteria();

-- ============================================================
-- 12. EXECUTION COMPLETION PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE complete_execution(
    p_execution_id BIGINT,
    p_status execution_status,
    p_error_message TEXT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_started_at TIMESTAMPTZ;
BEGIN
    IF p_status NOT IN (
        'PASSED',
        'FAILED',
        'SKIPPED',
        'BLOCKED'
    ) THEN
        RAISE EXCEPTION 'Invalid terminal execution status';
    END IF;

    SELECT started_at
    INTO v_started_at
    FROM scenario_executions
    WHERE execution_id = p_execution_id
      AND status = 'RUNNING'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Execution does not exist or is not running';
    END IF;

    UPDATE scenario_executions
    SET
        status = p_status,
        completed_at = NOW(),
        duration_ms = (
            EXTRACT(EPOCH FROM (NOW() - v_started_at)) * 1000
        ),
        error_message = p_error_message
    WHERE execution_id = p_execution_id;

END;
$$;

-- ============================================================
-- 13. EXECUTION VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_execution_results()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    expected_steps INTEGER;
    completed_steps INTEGER;
    failed_steps INTEGER;
    v_scenario_id BIGINT;
BEGIN
    IF NEW.status IN ('PASSED', 'FAILED') THEN

        SELECT scenario_id
        INTO v_scenario_id
        FROM scenario_executions
        WHERE execution_id = NEW.execution_id;

        SELECT COUNT(*)
        INTO expected_steps
        FROM scenario_steps
        WHERE scenario_id = v_scenario_id;

        SELECT
            COUNT(*),
            COUNT(*) FILTER (WHERE status IN ('FAILED', 'BLOCKED'))
        INTO completed_steps, failed_steps
        FROM step_execution_results
        WHERE execution_id = NEW.execution_id;

        IF completed_steps <> expected_steps THEN
            RAISE EXCEPTION
                'Expected % step results, found %',
                expected_steps,
                completed_steps;
        END IF;

        IF NEW.status = 'PASSED' AND failed_steps > 0 THEN
            RAISE EXCEPTION
                'A passing scenario cannot contain failed or blocked steps';
        END IF;

        IF NEW.status = 'FAILED' AND failed_steps = 0 THEN
            RAISE EXCEPTION
                'A failed scenario requires at least one failed or blocked step';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_execution_results
BEFORE UPDATE OF status ON scenario_executions
FOR EACH ROW
WHEN (
    NEW.status IN ('PASSED', 'FAILED')
)
EXECUTE FUNCTION validate_execution_results();

-- ============================================================
-- 14. SAMPLE USERS
-- ============================================================

INSERT INTO users (username, role) VALUES
('business.analyst', 'BUSINESS_ANALYST'),
('developer.one', 'DEVELOPER'),
('qa.engineer', 'QA_ENGINEER'),
('product.owner', 'PRODUCT_OWNER'),
('test.admin', 'TEST_ADMIN');

-- ============================================================
-- 15. SAMPLE FEATURES
-- ============================================================

INSERT INTO features (
    feature_key,
    name,
    description,
    owner_id
)
VALUES (
    'ORDERS-001',
    'Online order placement',
    'Validate customer order processing and fulfillment.',
    1
);

-- ============================================================
-- 16. SAMPLE SCENARIOS
-- ============================================================

INSERT INTO scenarios (
    feature_id,
    scenario_key,
    name,
    description,
    status,
    priority,
    created_by
)
VALUES
(
    1,
    'ORD-SC-001',
    'Successful order placement',
    'Authenticated customers can purchase available products.',
    'READY',
    1,
    1
),
(
    1,
    'ORD-SC-002',
    'Insufficient inventory',
    'Orders exceeding inventory must be rejected.',
    'READY',
    1,
    1
),
(
    1,
    'ORD-SC-003',
    'Unauthenticated customer',
    'Unauthenticated customers cannot place orders.',
    'READY',
    2,
    1
),
(
    1,
    'ORD-SC-004',
    'Payment authorization failure',
    'Failed payment must not reserve inventory.',
    'READY',
    1,
    1
);

-- ============================================================
-- 17. GIVEN-WHEN-THEN STEPS
-- ============================================================

INSERT INTO scenario_steps (
    scenario_id,
    sequence_number,
    keyword,
    step_text
)
VALUES
-- Scenario 1
(1, 1, 'GIVEN', 'The customer is authenticated'),
(1, 2, 'AND', 'The product has a price of 1000.00'),
(1, 3, 'AND', 'The product has 10 units in stock'),
(1, 4, 'WHEN', 'The customer orders 2 units'),
(1, 5, 'THEN', 'The order is confirmed'),
(1, 6, 'AND', 'The total including 10 percent tax is 2200.00'),
(1, 7, 'AND', 'The remaining inventory is 8 units'),

-- Scenario 2
(2, 1, 'GIVEN', 'The product has 2 units in stock'),
(2, 2, 'WHEN', 'The customer orders 5 units'),
(2, 3, 'THEN', 'The order is rejected'),
(2, 4, 'AND', 'Inventory remains unchanged'),

-- Scenario 3
(3, 1, 'GIVEN', 'The customer is not authenticated'),
(3, 2, 'AND', 'The product is available'),
(3, 3, 'WHEN', 'The customer attempts to place an order'),
(3, 4, 'THEN', 'The system rejects the request'),

-- Scenario 4
(4, 1, 'GIVEN', 'The customer is authenticated'),
(4, 2, 'AND', 'The product is available'),
(4, 3, 'AND', 'Payment authorization is rejected'),
(4, 4, 'WHEN', 'The customer submits an order'),
(4, 5, 'THEN', 'The order is rejected'),
(4, 6, 'AND', 'Inventory remains unchanged');

-- ============================================================
-- 18. ACCEPTANCE CRITERIA
-- ============================================================

INSERT INTO acceptance_criteria (
    scenario_id,
    criterion_key,
    criterion_description,
    mandatory
)
VALUES
(1, 'AC-001', 'Customer authentication succeeds', TRUE),
(1, 'AC-002', 'Inventory reservation is correct', TRUE),
(1, 'AC-003', 'Order total includes applicable tax', TRUE),
(1, 'AC-004', 'Order confirmation is recorded', TRUE),

(2, 'AC-005', 'Excess quantity is rejected', TRUE),
(2, 'AC-006', 'Inventory remains unchanged', TRUE),

(3, 'AC-007', 'Authentication is mandatory', TRUE),

(4, 'AC-008', 'Payment rejection prevents confirmation', TRUE),
(4, 'AC-009', 'Failed payment does not reserve inventory', TRUE);

-- ============================================================
-- 19. DATA-DRIVEN SCENARIO OUTLINE
-- ============================================================

INSERT INTO scenario_examples (
    scenario_id,
    example_name,
    parameters
)
VALUES
(
    1,
    'One unit',
    '{"quantity": 1, "price": 1000.00, "tax_rate": 0.10, "expected_total": 1100.00}'
),
(
    1,
    'Two units',
    '{"quantity": 2, "price": 1000.00, "tax_rate": 0.10, "expected_total": 2200.00}'
),
(
    1,
    'Three units',
    '{"quantity": 3, "price": 1000.00, "tax_rate": 0.10, "expected_total": 3300.00}'
);

-- ============================================================
-- 20. ENVIRONMENTS
-- ============================================================

INSERT INTO test_environments (
    environment_name,
    environment,
    base_url
)
VALUES
('Development', 'DEVELOPMENT', 'http://localhost:8000'),
('QA', 'TEST', 'https://qa.example.com'),
('Staging', 'STAGING', 'https://staging.example.com');

-- ============================================================
-- 21. ACTIVATE VALID SCENARIOS
-- ============================================================

UPDATE scenarios
SET status = 'ACTIVE'
WHERE scenario_id IN (1, 2, 3, 4);

-- ============================================================
-- 22. CREATE TEST EXECUTIONS
-- ============================================================

INSERT INTO scenario_executions (
    scenario_id,
    environment_id,
    executed_by,
    status,
    build_reference
)
VALUES
(1, 2, 3, 'RUNNING', 'build-2026.11.001'),
(2, 2, 3, 'RUNNING', 'build-2026.11.001'),
(3, 2, 3, 'RUNNING', 'build-2026.11.001'),
(4, 2, 3, 'RUNNING', 'build-2026.11.001');

-- ============================================================
-- 23. STEP EXECUTION RESULTS
-- ============================================================

INSERT INTO step_execution_results (
    execution_id,
    step_id,
    status,
    actual_result,
    duration_ms
)
SELECT
    1,
    step_id,
    'PASSED',
    'Acceptance condition satisfied',
    12.500
FROM scenario_steps
WHERE scenario_id = 1;

INSERT INTO step_execution_results (
    execution_id,
    step_id,
    status,
    actual_result,
    duration_ms
)
SELECT
    2,
    step_id,
    'PASSED',
    'Inventory restriction correctly enforced',
    10.250
FROM scenario_steps
WHERE scenario_id = 2;

INSERT INTO step_execution_results (
    execution_id,
    step_id,
    status,
    actual_result,
    duration_ms
)
SELECT
    3,
    step_id,
    'PASSED',
    'Authentication restriction correctly enforced',
    8.750
FROM scenario_steps
WHERE scenario_id = 3;

-- Scenario 4 contains a failed payment expectation.
INSERT INTO step_execution_results (
    execution_id,
    step_id,
    status,
    actual_result,
    duration_ms
)
SELECT
    4,
    step_id,
    CASE
        WHEN sequence_number = 5 THEN 'FAILED'::execution_status
        ELSE 'PASSED'::execution_status
    END,
    CASE
        WHEN sequence_number = 5
            THEN 'Unexpected order confirmation'
        ELSE 'Step executed'
    END,
    15.000
FROM scenario_steps
WHERE scenario_id = 4;

-- ============================================================
-- 24. COMPLETE EXECUTIONS
-- ============================================================

CALL complete_execution(1, 'PASSED', NULL);

CALL complete_execution(2, 'PASSED', NULL);

CALL complete_execution(3, 'PASSED', NULL);

CALL complete_execution(
    4,
    'FAILED',
    'Payment failure behavior did not satisfy acceptance criteria'
);

-- ============================================================
-- 25. RETRIEVAL VIEW
-- ============================================================

CREATE VIEW feature_scenario_details AS
SELECT
    f.feature_key,
    f.name AS feature_name,
    s.scenario_key,
    s.name AS scenario_name,
    s.status AS scenario_status,
    s.priority,
    COUNT(st.step_id) AS total_steps,
    COUNT(ac.criterion_id) AS acceptance_criteria_count
FROM features f
JOIN scenarios s
    ON s.feature_id = f.feature_id
LEFT JOIN scenario_steps st
    ON st.scenario_id = s.scenario_id
LEFT JOIN acceptance_criteria ac
    ON ac.scenario_id = s.scenario_id
GROUP BY
    f.feature_key,
    f.name,
    s.scenario_key,
    s.name,
    s.status,
    s.priority;

-- ============================================================
-- 26. EXECUTION REPORT VIEW
-- ============================================================

CREATE VIEW scenario_execution_report AS
SELECT
    s.scenario_key,
    s.name AS scenario_name,
    e.execution_id,
    env.environment_name,
    u.username AS executed_by,
    e.status,
    e.duration_ms,
    e.started_at,
    e.completed_at,
    e.error_message
FROM scenario_executions e
JOIN scenarios s
    ON s.scenario_id = e.scenario_id
JOIN test_environments env
    ON env.environment_id = e.environment_id
JOIN users u
    ON u.user_id = e.executed_by;

-- ============================================================
-- 27. CTE: FEATURE EXECUTION AGGREGATION
-- ============================================================

WITH execution_totals AS (
    SELECT
        s.feature_id,
        COUNT(e.execution_id) AS total_executions,
        COUNT(*) FILTER (
            WHERE e.status = 'PASSED'
        ) AS passed,
        COUNT(*) FILTER (
            WHERE e.status = 'FAILED'
        ) AS failed,
        COUNT(*) FILTER (
            WHERE e.status = 'BLOCKED'
        ) AS blocked
    FROM scenarios s
    LEFT JOIN scenario_executions e
        ON e.scenario_id = s.scenario_id
    GROUP BY s.feature_id
)
SELECT
    f.feature_key,
    f.name,
    et.total_executions,
    et.passed,
    et.failed,
    et.blocked,
    ROUND(
        100.0 * et.passed /
        NULLIF(et.total_executions, 0),
        2
    ) AS pass_percentage
FROM features f
JOIN execution_totals et
    ON et.feature_id = f.feature_id;

-- ============================================================
-- 28. VALIDATION: INCOMPLETE SCENARIOS
-- ============================================================

SELECT
    s.scenario_key,
    s.name
FROM scenarios s
WHERE NOT EXISTS (
    SELECT 1
    FROM scenario_steps st
    WHERE st.scenario_id = s.scenario_id
      AND st.keyword = 'GIVEN'
)
OR NOT EXISTS (
    SELECT 1
    FROM scenario_steps st
    WHERE st.scenario_id = s.scenario_id
      AND st.keyword = 'WHEN'
)
OR NOT EXISTS (
    SELECT 1
    FROM scenario_steps st
    WHERE st.scenario_id = s.scenario_id
      AND st.keyword = 'THEN'
);

-- ============================================================
-- 29. VALIDATION: MISSING ACCEPTANCE CRITERIA
-- ============================================================

SELECT
    s.scenario_key,
    s.name
FROM scenarios s
WHERE s.status = 'ACTIVE'
AND NOT EXISTS (
    SELECT 1
    FROM acceptance_criteria ac
    WHERE ac.scenario_id = s.scenario_id
      AND ac.mandatory = TRUE
);

-- ============================================================
-- 30. SCENARIO OUTLINE EVALUATION
-- ============================================================

SELECT
    s.scenario_key,
    se.example_name,
    (se.parameters ->> 'quantity')::INTEGER AS quantity,
    (se.parameters ->> 'price')::NUMERIC AS price,
    (se.parameters ->> 'tax_rate')::NUMERIC AS tax_rate,
    (se.parameters ->> 'expected_total')::NUMERIC AS expected_total,

    ROUND(
        (
            (se.parameters ->> 'quantity')::NUMERIC
            *
            (se.parameters ->> 'price')::NUMERIC
            *
            (
                1 + (se.parameters ->> 'tax_rate')::NUMERIC
            )
        ),
        2
    ) AS calculated_total,

    ROUND(
        (
            (se.parameters ->> 'quantity')::NUMERIC
            *
            (se.parameters ->> 'price')::NUMERIC
            *
            (
                1 + (se.parameters ->> 'tax_rate')::NUMERIC
            )
        ),
        2
    ) = (se.parameters ->> 'expected_total')::NUMERIC
        AS example_passed

FROM scenario_examples se
JOIN scenarios s
    ON s.scenario_id = se.scenario_id
WHERE se.enabled = TRUE;

-- ============================================================
-- 31. WORKFLOW PROCESSING: EXECUTIONS WITHOUT RESULTS
-- ============================================================

SELECT
    e.execution_id,
    s.scenario_key,
    s.name,
    e.status
FROM scenario_executions e
JOIN scenarios s
    ON s.scenario_id = e.scenario_id
WHERE NOT EXISTS (
    SELECT 1
    FROM step_execution_results sr
    WHERE sr.execution_id = e.execution_id
);

-- ============================================================
-- 32. ELIGIBILITY DETERMINATION
-- ============================================================

SELECT
    s.scenario_key,
    s.name,

    CASE
        WHEN s.status <> 'ACTIVE'
            THEN 'NOT_ELIGIBLE_SCENARIO_INACTIVE'

        WHEN NOT EXISTS (
            SELECT 1
            FROM acceptance_criteria ac
            WHERE ac.scenario_id = s.scenario_id
              AND ac.mandatory = TRUE
        )
            THEN 'NOT_ELIGIBLE_CRITERIA_MISSING'

        WHEN NOT EXISTS (
            SELECT 1
            FROM scenario_executions e
            WHERE e.scenario_id = s.scenario_id
              AND e.status = 'PASSED'
        )
            THEN 'NOT_ELIGIBLE_NO_PASSED_EXECUTION'

        ELSE 'ELIGIBLE'
    END AS acceptance_eligibility

FROM scenarios s;

-- ============================================================
-- 33. STEP-LEVEL FAILURE REPORT
-- ============================================================

SELECT
    s.scenario_key,
    s.name AS scenario_name,
    st.sequence_number,
    st.keyword,
    st.step_text,
    sr.status,
    sr.actual_result,
    sr.duration_ms
FROM step_execution_results sr
JOIN scenario_executions e
    ON e.execution_id = sr.execution_id
JOIN scenarios s
    ON s.scenario_id = e.scenario_id
JOIN scenario_steps st
    ON st.step_id = sr.step_id
WHERE sr.status IN ('FAILED', 'BLOCKED')
ORDER BY
    e.execution_id,
    st.sequence_number;

-- ============================================================
-- 34. PERFORMANCE: RECENT FAILURE ANALYSIS
-- ============================================================

SELECT
    s.scenario_key,
    s.name,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (
        WHERE e.status = 'FAILED'
    ) AS failed_runs,
    ROUND(
        AVG(e.duration_ms),
        2
    ) AS average_duration_ms
FROM scenarios s
JOIN scenario_executions e
    ON e.scenario_id = s.scenario_id
GROUP BY
    s.scenario_key,
    s.name
ORDER BY failed_runs DESC, average_duration_ms DESC;

-- ============================================================
-- 35. TRANSACTION SAFETY DEMONSTRATION
-- ============================================================

-- A failed operation rolls back all changes in its transaction.
-- The exception is caught in a PL/pgSQL subtransaction.

DO $$
DECLARE
    v_before INTEGER;
    v_after INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO v_before
    FROM scenarios;

    BEGIN
        INSERT INTO scenarios (
            feature_id,
            scenario_key,
            name,
            description,
            status,
            priority,
            created_by
        )
        VALUES (
            1,
            'ORD-SC-ROLLBACK',
            'Temporary invalid scenario',
            'Transaction rollback demonstration.',
            'READY',
            3,
            1
        );

        RAISE EXCEPTION 'Simulated transaction failure';

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Expected rollback: %', SQLERRM;
    END;

    SELECT COUNT(*)
    INTO v_after
    FROM scenarios;

    IF v_before <> v_after THEN
        RAISE EXCEPTION 'Transaction rollback failed';
    END IF;

    RAISE NOTICE 'Transaction rollback verified';
END;
$$;

-- ============================================================
-- 36. FINAL FEATURE REPORT
-- ============================================================

SELECT *
FROM feature_scenario_details
ORDER BY priority, scenario_key;

SELECT *
FROM scenario_execution_report
ORDER BY execution_id;

COMMIT;
