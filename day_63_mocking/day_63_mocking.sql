DROP SCHEMA IF EXISTS mocking_demo CASCADE;
CREATE SCHEMA mocking_demo;
SET search_path = mocking_demo;

CREATE TYPE dependency_kind AS ENUM ('real', 'stub', 'fake', 'mock');
CREATE TYPE test_result AS ENUM ('passed', 'failed');
CREATE TYPE payment_status AS ENUM ('approved', 'declined');

CREATE TABLE services (
    service_id BIGSERIAL PRIMARY KEY,
    service_name TEXT NOT NULL UNIQUE,
    purpose TEXT NOT NULL
);

CREATE TABLE test_cases (
    test_case_id BIGSERIAL PRIMARY KEY,
    test_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE dependencies (
    dependency_id BIGSERIAL PRIMARY KEY,
    service_id BIGINT NOT NULL REFERENCES services(service_id),
    dependency_name TEXT NOT NULL,
    kind dependency_kind NOT NULL,
    configured_result JSONB,
    UNIQUE (service_id, dependency_name)
);

CREATE TABLE dependency_calls (
    call_id BIGSERIAL PRIMARY KEY,
    dependency_id BIGINT NOT NULL REFERENCES dependencies(dependency_id),
    test_case_id BIGINT NOT NULL REFERENCES test_cases(test_case_id),
    invocation_number INTEGER NOT NULL CHECK (invocation_number > 0),
    operation_name TEXT NOT NULL,
    request_payload JSONB NOT NULL,
    response_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (dependency_id, test_case_id, invocation_number)
);

CREATE TABLE test_executions (
    execution_id BIGSERIAL PRIMARY KEY,
    test_case_id BIGINT NOT NULL REFERENCES test_cases(test_case_id),
    result test_result NOT NULL,
    actual_output JSONB,
    failure_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE payments (
    payment_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    status payment_status,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX idx_dependency_calls_test
    ON dependency_calls(test_case_id, dependency_id);

CREATE INDEX idx_test_executions_case_time
    ON test_executions(test_case_id, executed_at DESC);

INSERT INTO services (service_name, purpose)
VALUES
    ('PaymentService', 'Coordinates payment validation, fraud evaluation, authorization, and persistence');

INSERT INTO test_cases (test_name, description)
VALUES
    ('stub_controls_gateway_result', 'Uses a predetermined gateway response'),
    ('fake_blocks_customer', 'Uses a working in-memory fraud rule'),
    ('mock_verifies_interaction', 'Verifies an exact dependency interaction'),
    ('invalid_payment', 'Confirms validation prevents dependency calls'),
    ('multiple_mock_calls', 'Detects an unexpected repeated interaction');

INSERT INTO dependencies (service_id, dependency_name, kind, configured_result)
SELECT s.service_id, x.dependency_name, x.kind::dependency_kind, x.result::jsonb
FROM services s
CROSS JOIN (
    VALUES
        ('PaymentGateway', 'stub', '{"status":"approved"}'),
        ('FraudService', 'fake', '{"blocked_customers":["C-BLOCKED"]}'),
        ('PaymentGatewayMock', 'mock', '{"expected_calls":1}'),
        ('PaymentRepositoryFake', 'fake', '{"storage":"in_memory"}')
) AS x(dependency_name, kind, result)
WHERE s.service_name = 'PaymentService';

INSERT INTO payments (payment_id, customer_id, amount, currency, status)
VALUES
    ('P-100', 'C-10', 100.00, 'USD', 'approved'),
    ('P-101', 'C-BLOCKED', 100.00, 'USD', 'declined'),
    ('P-102', 'C-20', 300.00, 'USD', 'approved'),
    ('P-103', 'C-20', 25.00, 'USD', NULL);

CREATE OR REPLACE FUNCTION validate_payment_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'approved' AND NEW.amount <= 0 THEN
        RAISE EXCEPTION 'Approved payments must have a positive amount';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_payment_status
BEFORE INSERT OR UPDATE ON payments
FOR EACH ROW
EXECUTE FUNCTION validate_payment_status();

CREATE OR REPLACE FUNCTION record_dependency_call(
    p_dependency_name TEXT,
    p_test_name TEXT,
    p_operation TEXT,
    p_request JSONB,
    p_response JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_dependency_id BIGINT;
    v_test_case_id BIGINT;
    v_next_call INTEGER;
    v_call_id BIGINT;
BEGIN
    SELECT dependency_id
    INTO v_dependency_id
    FROM dependencies
    WHERE dependency_name = p_dependency_name;

    IF v_dependency_id IS NULL THEN
        RAISE EXCEPTION 'Unknown dependency: %', p_dependency_name;
    END IF;

    SELECT test_case_id
    INTO v_test_case_id
    FROM test_cases
    WHERE test_name = p_test_name;

    IF v_test_case_id IS NULL THEN
        RAISE EXCEPTION 'Unknown test case: %', p_test_name;
    END IF;

    SELECT COALESCE(MAX(invocation_number), 0) + 1
    INTO v_next_call
    FROM dependency_calls
    WHERE dependency_id = v_dependency_id
      AND test_case_id = v_test_case_id;

    INSERT INTO dependency_calls (
        dependency_id,
        test_case_id,
        invocation_number,
        operation_name,
        request_payload,
        response_payload
    )
    VALUES (
        v_dependency_id,
        v_test_case_id,
        v_next_call,
        p_operation,
        p_request,
        p_response
    )
    RETURNING call_id INTO v_call_id;

    RETURN v_call_id;
END;
$$;

BEGIN;

SELECT record_dependency_call(
    'PaymentGateway',
    'stub_controls_gateway_result',
    'authorize',
    '{"payment_id":"P-100","amount":100,"currency":"USD"}',
    '{"status":"approved"}'
);

INSERT INTO test_executions (
    test_case_id,
    result,
    actual_output
)
SELECT test_case_id, 'passed', '{"status":"approved"}'
FROM test_cases
WHERE test_name = 'stub_controls_gateway_result';

COMMIT;

BEGIN;

SELECT record_dependency_call(
    'FraudService',
    'fake_blocks_customer',
    'is_suspicious',
    '{"customer_id":"C-BLOCKED"}',
    '{"suspicious":true}'
);

INSERT INTO test_executions (
    test_case_id,
    result,
    actual_output
)
SELECT test_case_id, 'passed', '{"status":"declined"}'
FROM test_cases
WHERE test_name = 'fake_blocks_customer';

COMMIT;

BEGIN;

SELECT record_dependency_call(
    'PaymentGatewayMock',
    'mock_verifies_interaction',
    'authorize',
    '{"payment_id":"P-102","amount":300,"currency":"USD"}',
    '{"status":"approved"}'
);

INSERT INTO test_executions (
    test_case_id,
    result,
    actual_output
)
SELECT test_case_id, 'passed', '{"gateway_calls":1}'
FROM test_cases
WHERE test_name = 'mock_verifies_interaction';

COMMIT;

BEGIN;

INSERT INTO test_executions (
    test_case_id,
    result,
    actual_output,
    failure_message
)
SELECT
    test_case_id,
    'passed',
    '{"gateway_calls":0,"fraud_calls":0}',
    NULL
FROM test_cases
WHERE test_name = 'invalid_payment';

COMMIT;

BEGIN;

SELECT record_dependency_call(
    'PaymentGatewayMock',
    'multiple_mock_calls',
    'authorize',
    '{"payment_id":"P-104","amount":400,"currency":"USD"}',
    '{"status":"approved"}'
);

SELECT record_dependency_call(
    'PaymentGatewayMock',
    'multiple_mock_calls',
    'authorize',
    '{"payment_id":"P-104","amount":400,"currency":"USD"}',
    '{"status":"approved"}'
);

INSERT INTO test_executions (
    test_case_id,
    result,
    actual_output,
    failure_message
)
SELECT
    test_case_id,
    'failed',
    '{"gateway_calls":2}',
    'Expected exactly one gateway interaction'
FROM test_cases
WHERE test_name = 'multiple_mock_calls';

COMMIT;

CREATE VIEW dependency_usage_report AS
SELECT
    d.dependency_name,
    d.kind,
    COUNT(dc.call_id) AS call_count,
    COUNT(DISTINCT dc.test_case_id) AS test_count
FROM dependencies d
LEFT JOIN dependency_calls dc
    ON dc.dependency_id = d.dependency_id
GROUP BY d.dependency_id, d.dependency_name, d.kind;

CREATE VIEW test_quality_report AS
SELECT
    tc.test_name,
    COUNT(te.execution_id) AS executions,
    COUNT(*) FILTER (WHERE te.result = 'passed') AS passed,
    COUNT(*) FILTER (WHERE te.result = 'failed') AS failed,
    MAX(te.executed_at) AS last_execution
FROM test_cases tc
LEFT JOIN test_executions te
    ON te.test_case_id = tc.test_case_id
GROUP BY tc.test_case_id, tc.test_name;

-- Retrieval: dependency inventory and implementation strategy.
SELECT
    service_name,
    dependency_name,
    kind,
    configured_result
FROM services s
JOIN dependencies d ON d.service_id = s.service_id
ORDER BY service_name, dependency_name;

-- Validation: mock interactions that violate a single-call expectation.
SELECT
    tc.test_name,
    d.dependency_name,
    COUNT(dc.call_id) AS actual_calls
FROM test_cases tc
JOIN dependency_calls dc ON dc.test_case_id = tc.test_case_id
JOIN dependencies d ON d.dependency_id = dc.dependency_id
WHERE d.kind = 'mock'
GROUP BY tc.test_name, d.dependency_name
HAVING COUNT(dc.call_id) <> 1;

-- Aggregation: dependency usage by isolation technique.
SELECT
    kind,
    COUNT(*) AS dependency_count,
    SUM(call_count) AS total_calls
FROM dependency_usage_report
GROUP BY kind
ORDER BY kind;

-- Evaluation: test success rate.
WITH counts AS (
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (WHERE result = 'passed') AS passed
    FROM test_executions
)
SELECT
    total,
    passed,
    ROUND(100.0 * passed / NULLIF(total, 0), 2) AS pass_rate
FROM counts;

-- Reporting: operational view of each test.
SELECT *
FROM test_quality_report
ORDER BY test_name;

-- Workflow state: payments that were evaluated but have no final state.
SELECT
    payment_id,
    customer_id,
    amount,
    currency
FROM payments
WHERE status IS NULL;

-- Eligibility-style decision: whether a mock interaction is acceptable.
SELECT
    tc.test_name,
    d.dependency_name,
    COUNT(dc.call_id) AS actual_calls,
    CASE
        WHEN d.kind <> 'mock' THEN 'not_applicable'
        WHEN COUNT(dc.call_id) = 1 THEN 'eligible'
        ELSE 'rejected'
    END AS interaction_decision
FROM test_cases tc
JOIN dependency_calls dc ON dc.test_case_id = tc.test_case_id
JOIN dependencies d ON d.dependency_id = dc.dependency_id
GROUP BY tc.test_name, d.dependency_name, d.kind;
