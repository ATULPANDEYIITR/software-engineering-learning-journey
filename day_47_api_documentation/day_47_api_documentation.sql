-- PostgreSQL 15+
-- API documentation, OpenAPI contracts, request/response schemas,
-- version evolution, compatibility findings, and release governance.
--
-- This script creates an isolated schema and can be rerun by dropping that
-- schema. Do not use DROP SCHEMA CASCADE against a shared production schema.

BEGIN;

DROP SCHEMA IF EXISTS api_contract_lab CASCADE;
CREATE SCHEMA api_contract_lab;
SET search_path TO api_contract_lab, public;

CREATE TYPE http_method AS ENUM (
    'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'
);

CREATE TYPE contract_artifact_format AS ENUM (
    'openapi-json', 'openapi-yaml'
);

CREATE TYPE release_state AS ENUM (
    'draft', 'validating', 'approved', 'rejected', 'released'
);

CREATE TYPE finding_severity AS ENUM (
    'error', 'warning', 'information'
);

CREATE TYPE schema_location AS ENUM (
    'path', 'query', 'header', 'cookie', 'request-body', 'response-body'
);

CREATE TABLE api_services (
    service_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service_name TEXT NOT NULL UNIQUE,
    base_path TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT api_service_name_nonblank CHECK (btrim(service_name) <> ''),
    CONSTRAINT api_base_path_absolute CHECK (
        base_path = '/' OR left(base_path, 1) = '/'
    )
);

CREATE TABLE api_versions (
    api_version_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service_id BIGINT NOT NULL REFERENCES api_services(service_id)
        ON DELETE CASCADE,
    version_major INTEGER NOT NULL CHECK (version_major >= 0),
    version_minor INTEGER NOT NULL CHECK (version_minor >= 0),
    version_patch INTEGER NOT NULL CHECK (version_patch >= 0),
    lifecycle_state TEXT NOT NULL DEFAULT 'draft'
        CHECK (lifecycle_state IN ('draft', 'active', 'deprecated', 'retired')),
    previous_version_id BIGINT REFERENCES api_versions(api_version_id),
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (service_id, version_major, version_minor, version_patch),
    UNIQUE (api_version_id, service_id),
    CHECK (previous_version_id IS NULL OR previous_version_id <> api_version_id)
);

CREATE TABLE contract_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    artifact_format contract_artifact_format NOT NULL,
    document JSONB NOT NULL,
    document_sha256 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    validated_at TIMESTAMPTZ,
    validation_passed BOOLEAN,
    CONSTRAINT artifact_hash_format CHECK (
        document_sha256 ~ '^[0-9a-f]{64}$'
    ),
    CONSTRAINT artifact_is_object CHECK (
        jsonb_typeof(document) = 'object'
    ),
    CONSTRAINT artifact_openapi_version CHECK (
        document ? 'openapi'
        AND document ->> 'openapi' LIKE '3.%'
    ),
    UNIQUE (api_version_id, document_sha256)
);

CREATE TABLE api_operations (
    operation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    operation_key TEXT NOT NULL,
    method http_method NOT NULL,
    path_template TEXT NOT NULL,
    summary TEXT NOT NULL,
    authentication_required BOOLEAN NOT NULL DEFAULT TRUE,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (api_version_id, operation_key),
    UNIQUE (api_version_id, method, path_template),
    UNIQUE (operation_id, api_version_id),
    CHECK (btrim(operation_key) <> ''),
    CHECK (left(path_template, 1) = '/'),
    CHECK (btrim(summary) <> '')
);

CREATE TABLE schema_definitions (
    schema_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    schema_name TEXT NOT NULL,
    json_schema JSONB NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    UNIQUE (api_version_id, schema_name),
    UNIQUE (schema_id, api_version_id),
    CHECK (jsonb_typeof(json_schema) = 'object'),
    CHECK (json_schema ? 'type')
);

CREATE TABLE operation_parameters (
    parameter_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES api_operations(operation_id)
        ON DELETE CASCADE,
    parameter_name TEXT NOT NULL,
    parameter_location schema_location NOT NULL,
    required BOOLEAN NOT NULL DEFAULT FALSE,
    parameter_schema JSONB NOT NULL,
    description TEXT NOT NULL,
    UNIQUE (operation_id, parameter_name, parameter_location),
    CHECK (
        parameter_location NOT IN ('request-body', 'response-body')
    ),
    CHECK (
        parameter_location <> 'path' OR required = TRUE
    ),
    CHECK (jsonb_typeof(parameter_schema) = 'object'),
    CHECK (btrim(parameter_name) <> '')
);

CREATE TABLE operation_request_schemas (
    operation_id BIGINT NOT NULL REFERENCES api_operations(operation_id)
        ON DELETE CASCADE,
    schema_id BIGINT NOT NULL REFERENCES schema_definitions(schema_id)
        ON DELETE RESTRICT,
    required BOOLEAN NOT NULL DEFAULT TRUE,
    media_type TEXT NOT NULL DEFAULT 'application/json',
    PRIMARY KEY (operation_id, media_type),
    CHECK (media_type LIKE '%/%')
);

CREATE TABLE operation_responses (
    response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES api_operations(operation_id)
        ON DELETE CASCADE,
    status_code INTEGER NOT NULL CHECK (status_code BETWEEN 100 AND 599),
    description TEXT NOT NULL,
    schema_id BIGINT REFERENCES schema_definitions(schema_id)
        ON DELETE RESTRICT,
    media_type TEXT,
    UNIQUE (operation_id, status_code),
    CHECK (
        (status_code = 204 AND schema_id IS NULL AND media_type IS NULL)
        OR
        (status_code <> 204 AND (
            schema_id IS NULL
            OR media_type IS NOT NULL
        ))
    )
);

CREATE TABLE consumer_applications (
    consumer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    consumer_name TEXT NOT NULL UNIQUE,
    team_name TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    CHECK (btrim(consumer_name) <> ''),
    CHECK (contact_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$')
);

CREATE TABLE consumer_contract_expectations (
    expectation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    consumer_id BIGINT NOT NULL REFERENCES consumer_applications(consumer_id)
        ON DELETE CASCADE,
    operation_id BIGINT NOT NULL REFERENCES api_operations(operation_id)
        ON DELETE CASCADE,
    expected_status INTEGER NOT NULL CHECK (expected_status BETWEEN 100 AND 599),
    expected_response JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (consumer_id, operation_id, expected_status),
    CHECK (jsonb_typeof(expected_response) = 'object')
);

CREATE TABLE contract_test_runs (
    test_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    test_suite TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    tests_total INTEGER NOT NULL CHECK (tests_total >= 0),
    tests_failed INTEGER NOT NULL CHECK (
        tests_failed >= 0 AND tests_failed <= tests_total
    ),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    report JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (btrim(test_suite) <> ''),
    CHECK (passed = (tests_failed = 0)),
    CHECK (jsonb_typeof(report) = 'object')
);

CREATE TABLE implementation_observations (
    observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    operation_id BIGINT NOT NULL REFERENCES api_operations(operation_id)
        ON DELETE CASCADE,
    observed_status INTEGER NOT NULL CHECK (observed_status BETWEEN 100 AND 599),
    accepted_request_fields TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    authentication_enforced BOOLEAN NOT NULL,
    sample_count BIGINT NOT NULL DEFAULT 1 CHECK (sample_count > 0),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (jsonb_typeof(evidence) = 'object')
);

CREATE TABLE compatibility_findings (
    finding_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    old_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    new_version_id BIGINT NOT NULL REFERENCES api_versions(api_version_id)
        ON DELETE CASCADE,
    operation_key TEXT NOT NULL,
    severity finding_severity NOT NULL,
    change_code TEXT NOT NULL,
    description TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ,
    CHECK (old_version_id <> new_version_id),
    CHECK (btrim(change_code) <> ''),
    CHECK (btrim(description) <> '')
);

CREATE TABLE release_candidates (
    release_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    api_version_id BIGINT NOT NULL UNIQUE
        REFERENCES api_versions(api_version_id) ON DELETE CASCADE,
    state release_state NOT NULL DEFAULT 'draft',
    breaking_change BOOLEAN NOT NULL DEFAULT FALSE,
    schema_validation_passed BOOLEAN NOT NULL DEFAULT FALSE,
    security_review_passed BOOLEAN NOT NULL DEFAULT FALSE,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        state NOT IN ('approved', 'released')
        OR (
            schema_validation_passed
            AND security_review_passed
            AND approved_by IS NOT NULL
            AND approved_at IS NOT NULL
        )
    )
);

CREATE TABLE governance_findings (
    governance_finding_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id BIGINT NOT NULL REFERENCES release_candidates(release_id)
        ON DELETE CASCADE,
    severity finding_severity NOT NULL,
    finding_code TEXT NOT NULL,
    detail TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(finding_code) <> ''),
    CHECK (btrim(detail) <> '')
);

CREATE INDEX api_operations_version_method_idx
    ON api_operations(api_version_id, method, path_template);

CREATE INDEX contract_test_runs_latest_idx
    ON contract_test_runs(api_version_id, executed_at DESC);

CREATE INDEX implementation_observations_operation_status_idx
    ON implementation_observations(operation_id, observed_status);

CREATE INDEX compatibility_findings_unresolved_idx
    ON compatibility_findings(new_version_id, severity)
    WHERE resolved_at IS NULL;

CREATE INDEX governance_findings_release_errors_idx
    ON governance_findings(release_id, finding_code)
    WHERE severity = 'error';

CREATE INDEX contract_artifacts_document_gin_idx
    ON contract_artifacts USING GIN (document jsonb_path_ops);

-- Example service and API versions.
INSERT INTO api_services (service_name, base_path, description)
VALUES (
    'Incident Management API',
    '/api/v3',
    'Contract for incident creation, retrieval, and incident listing.'
);

INSERT INTO api_versions (
    service_id, version_major, version_minor, version_patch, lifecycle_state
)
SELECT service_id, 3, 0, 0, 'active'
FROM api_services
WHERE service_name = 'Incident Management API';

INSERT INTO api_versions (
    service_id, version_major, version_minor, version_patch,
    lifecycle_state, previous_version_id
)
SELECT service_id, 3, 1, 0, 'draft', api_version_id
FROM api_versions
WHERE version_major = 3
  AND version_minor = 0
  AND version_patch = 0;

INSERT INTO api_operations (
    api_version_id, operation_key, method, path_template, summary,
    authentication_required
)
SELECT api_version_id, 'listIncidents', 'GET', '/incidents',
       'List incidents', TRUE
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO api_operations (
    api_version_id, operation_key, method, path_template, summary,
    authentication_required
)
SELECT api_version_id, 'createIncident', 'POST', '/incidents',
       'Create an incident', TRUE
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO api_operations (
    api_version_id, operation_key, method, path_template, summary,
    authentication_required
)
SELECT api_version_id, 'getIncident', 'GET', '/incidents/{incidentId}',
       'Retrieve an incident', TRUE
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO schema_definitions (
    api_version_id, schema_name, json_schema, description
)
SELECT api_version_id, 'CreateIncident',
    '{
      "type": "object",
      "required": ["title", "severity"],
      "properties": {
        "title": {"type": "string", "minLength": 5, "maxLength": 120},
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "description": {"type": "string", "maxLength": 4000}
      },
      "additionalProperties": false
    }'::jsonb,
    'Accepted request body for incident creation.'
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO schema_definitions (
    api_version_id, schema_name, json_schema, description
)
SELECT api_version_id, 'Incident',
    '{
      "type": "object",
      "required": ["id", "title", "severity", "status"],
      "properties": {
        "id": {"type": "integer", "minimum": 1},
        "title": {"type": "string"},
        "severity": {
          "type": "string",
          "enum": ["low", "medium", "high", "critical"]
        },
        "status": {
          "type": "string",
          "enum": ["open", "investigating", "resolved"]
        }
      },
      "additionalProperties": false
    }'::jsonb,
    'Successful incident representation.'
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO operation_request_schemas (operation_id, schema_id, required)
SELECT o.operation_id, s.schema_id, TRUE
FROM api_operations o
JOIN api_versions v ON v.api_version_id = o.api_version_id
JOIN schema_definitions s ON s.api_version_id = v.api_version_id
WHERE o.operation_key = 'createIncident'
  AND s.schema_name = 'CreateIncident';

INSERT INTO operation_responses (
    operation_id, status_code, description, schema_id, media_type
)
SELECT o.operation_id, x.status_code, x.description, s.schema_id,
       CASE WHEN x.status_code = 204 THEN NULL ELSE 'application/json' END
FROM api_operations o
JOIN api_versions v ON v.api_version_id = o.api_version_id
CROSS JOIN (
    VALUES
        ('listIncidents', 200, 'Incident list'),
        ('listIncidents', 401, 'Authentication required'),
        ('createIncident', 201, 'Incident created'),
        ('createIncident', 400, 'Invalid request'),
        ('createIncident', 401, 'Authentication required'),
        ('createIncident', 409, 'Duplicate incident reference'),
        ('getIncident', 200, 'Incident retrieved'),
        ('getIncident', 401, 'Authentication required'),
        ('getIncident', 404, 'Incident not found')
) AS x(operation_key, status_code, description)
LEFT JOIN schema_definitions s
    ON s.api_version_id = v.api_version_id
   AND s.schema_name = CASE
       WHEN x.status_code IN (200, 201) THEN 'Incident'
       ELSE NULL
   END
WHERE o.operation_key = x.operation_key
  AND v.version_major = 3
  AND v.version_minor = 1
  AND v.version_patch = 0;

INSERT INTO operation_parameters (
    operation_id, parameter_name, parameter_location, required,
    parameter_schema, description
)
SELECT operation_id, 'incidentId', 'path', TRUE,
       '{"type":"integer","minimum":1}'::jsonb,
       'Positive identifier of the incident.'
FROM api_operations
WHERE operation_key = 'getIncident';

INSERT INTO consumer_applications (
    consumer_name, team_name, contact_email
)
VALUES
    ('Operations Dashboard', 'Operations Engineering', 'ops@example.test'),
    ('Compliance Reporting', 'Risk and Compliance', 'compliance@example.test');

INSERT INTO consumer_contract_expectations (
    consumer_id, operation_id, expected_status, expected_response
)
SELECT c.consumer_id, o.operation_id, 200,
       '{"requiredFields":["items","total"]}'::jsonb
FROM consumer_applications c
JOIN api_operations o ON o.operation_key = 'listIncidents'
WHERE c.consumer_name = 'Operations Dashboard';

INSERT INTO consumer_contract_expectations (
    consumer_id, operation_id, expected_status, expected_response
)
SELECT c.consumer_id, o.operation_id, 201,
       '{"requiredFields":["id","title","severity","status"]}'::jsonb
FROM consumer_applications c
JOIN api_operations o ON o.operation_key = 'createIncident'
WHERE c.consumer_name = 'Compliance Reporting';

INSERT INTO contract_test_runs (
    api_version_id, test_suite, passed, tests_total, tests_failed, report
)
SELECT api_version_id, 'openapi-schema-validation', TRUE, 42, 0,
       '{"validator":"pipeline","checks":["paths","operations","schemas","responses"]}'::jsonb
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

INSERT INTO contract_test_runs (
    api_version_id, test_suite, passed, tests_total, tests_failed, report
)
SELECT api_version_id, 'runtime-contract-tests', TRUE, 86, 0,
       '{"checks":["request-validation","status-codes","authentication","response-shapes"]}'::jsonb
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

-- These observations provide concrete evidence of runtime behavior. They do not
-- prove complete conformance: sampled observations must be complemented by tests.
INSERT INTO implementation_observations (
    operation_id, observed_status, accepted_request_fields,
    authentication_enforced, sample_count, evidence
)
SELECT operation_id, 201,
       ARRAY['title', 'severity', 'description'],
       TRUE, 12,
       '{"source":"contract-test-suite","result":"passed"}'::jsonb
FROM api_operations
WHERE operation_key = 'createIncident';

INSERT INTO implementation_observations (
    operation_id, observed_status, accepted_request_fields,
    authentication_enforced, sample_count, evidence
)
SELECT operation_id, 401, ARRAY[]::TEXT[],
       TRUE, 3,
       '{"source":"negative-authentication-test","result":"passed"}'::jsonb
FROM api_operations
WHERE operation_key = 'listIncidents';

INSERT INTO compatibility_findings (
    old_version_id, new_version_id, operation_key,
    severity, change_code, description
)
SELECT old.api_version_id, new.api_version_id, 'createIncident',
       'warning', 'OPTIONAL_RESPONSE_FIELD',
       'An optional response property was introduced; confirm consumer tolerance.'
FROM api_versions old
JOIN api_versions new ON new.previous_version_id = old.api_version_id
WHERE old.version_major = 3 AND old.version_minor = 0
  AND new.version_major = 3 AND new.version_minor = 1;

INSERT INTO release_candidates (
    api_version_id, state, breaking_change,
    schema_validation_passed, security_review_passed
)
SELECT api_version_id, 'validating', FALSE, TRUE, TRUE
FROM api_versions
WHERE version_major = 3 AND version_minor = 1 AND version_patch = 0;

-- Verify that every registered operation has at least one response definition.
CREATE VIEW operations_without_responses AS
SELECT o.operation_id, o.operation_key, o.method, o.path_template
FROM api_operations o
LEFT JOIN operation_responses r ON r.operation_id = o.operation_id
GROUP BY o.operation_id, o.operation_key, o.method, o.path_template
HAVING COUNT(r.response_id) = 0;

-- Compare observed status codes with the operation's documented response codes.
CREATE VIEW undocumented_runtime_statuses AS
SELECT DISTINCT
    o.api_version_id,
    o.operation_key,
    obs.observed_status,
    obs.observed_at
FROM implementation_observations obs
JOIN api_operations o ON o.operation_id = obs.operation_id
LEFT JOIN operation_responses r
    ON r.operation_id = o.operation_id
   AND r.status_code = obs.observed_status
WHERE r.response_id IS NULL;

-- An API contract can declare authentication, but evidence must show enforcement.
CREATE VIEW authentication_contract_mismatches AS
SELECT DISTINCT
    o.api_version_id,
    o.operation_key,
    obs.observed_status
FROM api_operations o
JOIN implementation_observations obs
    ON obs.operation_id = o.operation_id
WHERE o.authentication_required = TRUE
  AND obs.authentication_enforced = FALSE;

-- Check whether a release has a passing contract-test run. The latest run for
-- each suite is selected before evaluating the release.
CREATE VIEW latest_contract_test_results AS
SELECT DISTINCT ON (api_version_id, test_suite)
    api_version_id,
    test_suite,
    passed,
    tests_total,
    tests_failed,
    executed_at
FROM contract_test_runs
ORDER BY api_version_id, test_suite, executed_at DESC, test_run_id DESC;

-- A database-level release function provides a single transition point. It
-- rejects a release when structural validation, security review, contract tests,
-- documented response codes, or compatibility checks fail.
CREATE FUNCTION approve_api_release(
    p_release_id BIGINT,
    p_approver TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    candidate release_candidates%ROWTYPE;
    version_record api_versions%ROWTYPE;
    previous_major INTEGER;
    latest_failed_suite BOOLEAN;
BEGIN
    SELECT *
    INTO candidate
    FROM release_candidates
    WHERE release_id = p_release_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Release % does not exist', p_release_id;
    END IF;

    IF candidate.state <> 'validating' THEN
        RAISE EXCEPTION
            'Release % must be validating before approval; current state is %',
            p_release_id, candidate.state;
    END IF;

    IF p_approver IS NULL OR btrim(p_approver) = '' THEN
        RAISE EXCEPTION 'Approver identity must not be blank';
    END IF;

    IF NOT candidate.schema_validation_passed THEN
        RAISE EXCEPTION 'OpenAPI schema validation has not passed';
    END IF;

    IF NOT candidate.security_review_passed THEN
        RAISE EXCEPTION 'Security review has not passed';
    END IF;

    SELECT *
    INTO version_record
    FROM api_versions
    WHERE api_version_id = candidate.api_version_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'API version record is missing';
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM latest_contract_test_results t
        WHERE t.api_version_id = candidate.api_version_id
          AND t.passed = FALSE
    )
    INTO latest_failed_suite;

    IF latest_failed_suite THEN
        RAISE EXCEPTION 'At least one latest contract test suite failed';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM latest_contract_test_results t
        WHERE t.api_version_id = candidate.api_version_id
          AND t.test_suite = 'runtime-contract-tests'
          AND t.passed = TRUE
    ) THEN
        RAISE EXCEPTION 'Passing runtime contract tests are required';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM undocumented_runtime_statuses u
        WHERE u.api_version_id = candidate.api_version_id
    ) THEN
        RAISE EXCEPTION 'Runtime emits an undocumented HTTP status';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM authentication_contract_mismatches a
        WHERE a.api_version_id = candidate.api_version_id
    ) THEN
        RAISE EXCEPTION 'Authentication contract mismatch detected';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM compatibility_findings f
        WHERE f.new_version_id = candidate.api_version_id
          AND f.resolved_at IS NULL
          AND f.severity = 'error'
    ) THEN
        RAISE EXCEPTION 'Unresolved breaking compatibility findings exist';
    END IF;

    IF candidate.breaking_change THEN
        SELECT previous.version_major
        INTO previous_major
        FROM api_versions current_version
        JOIN api_versions previous
          ON previous.api_version_id = current_version.previous_version_id
        WHERE current_version.api_version_id = candidate.api_version_id;

        IF previous_major IS NULL THEN
            RAISE EXCEPTION
                'Breaking release must identify a previous version';
        END IF;

        IF version_record.version_major <= previous_major THEN
            RAISE EXCEPTION
                'Breaking API changes require a major version increment';
        END IF;
    END IF;

    UPDATE release_candidates
    SET state = 'approved',
        approved_by = p_approver,
        approved_at = now()
    WHERE release_id = p_release_id;

    RETURN TRUE;
END;
$$;

-- Inspect operation and response coverage.
SELECT
    o.operation_key,
    o.method,
    o.path_template,
    COUNT(r.response_id) AS documented_response_count,
    ARRAY_AGG(r.status_code ORDER BY r.status_code)
        FILTER (WHERE r.status_code IS NOT NULL) AS documented_statuses
FROM api_operations o
LEFT JOIN operation_responses r ON r.operation_id = o.operation_id
GROUP BY o.operation_id, o.operation_key, o.method, o.path_template
ORDER BY o.operation_key;

-- Inspect request-schema constraints represented in JSONB.
SELECT
    s.schema_name,
    s.json_schema ->> 'type' AS root_type,
    s.json_schema -> 'required' AS required_properties,
    s.json_schema -> 'properties' AS property_definitions
FROM schema_definitions s
JOIN api_versions v ON v.api_version_id = s.api_version_id
WHERE v.version_major = 3 AND v.version_minor = 1
ORDER BY s.schema_name;

-- Detect implementation statuses that have not been documented.
SELECT *
FROM undocumented_runtime_statuses
ORDER BY operation_key, observed_status;

-- Detect release operations that lack response definitions.
SELECT *
FROM operations_without_responses;

-- Assess consumer dependencies before changing a response contract.
SELECT
    c.consumer_name,
    c.team_name,
    o.operation_key,
    e.expected_status,
    e.expected_response
FROM consumer_contract_expectations e
JOIN consumer_applications c ON c.consumer_id = e.consumer_id
JOIN api_operations o ON o.operation_id = e.operation_id
ORDER BY c.consumer_name, o.operation_key;

-- Show the most recent contract test result for every suite.
SELECT
    v.version_major || '.' || v.version_minor || '.' || v.version_patch
        AS api_version,
    t.test_suite,
    t.passed,
    t.tests_total,
    t.tests_failed,
    t.executed_at
FROM latest_contract_test_results t
JOIN api_versions v ON v.api_version_id = t.api_version_id
ORDER BY t.test_suite;

-- The seeded candidate is intentionally still in validating state. Approval is
-- invoked explicitly by an authorized release pipeline, not automatically when
-- this educational schema is loaded.

COMMIT;
