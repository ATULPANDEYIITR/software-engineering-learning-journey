-- Design Patterns I: Factory, Builder, Singleton
--
-- PostgreSQL-compatible relational model for a deployment platform.
--
-- Factory:
--   The database stores target types and executor registrations so an
--   application-level factory can select the correct execution strategy.
--
-- Builder:
--   A deployment request is represented as a progressively configurable
--   aggregate whose final state is constrained by relational rules.
--
-- Singleton:
--   The database does not attempt to make a connection pool or application
--   object a Singleton. Instead, it models the process-wide audit concept as
--   one logical audit stream for the application. PostgreSQL sequences and
--   constraints provide database-level identity and integrity.

DROP SCHEMA IF EXISTS design_patterns_i CASCADE;

CREATE SCHEMA design_patterns_i;

SET search_path TO design_patterns_i;

-- ---------------------------------------------------------------------------
-- Domain tables
-- ---------------------------------------------------------------------------

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name VARCHAR(120) NOT NULL UNIQUE,
    owner_team VARCHAR(120) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE deployment_targets (
    target_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_code VARCHAR(40) NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE executor_registrations (
    executor_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_id BIGINT NOT NULL REFERENCES deployment_targets(target_id),
    executor_name VARCHAR(120) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (target_id)
);

CREATE TABLE deployment_requests (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    target_id BIGINT NOT NULL REFERENCES deployment_targets(target_id),
    application_name VARCHAR(150) NOT NULL,
    version VARCHAR(30) NOT NULL,
    owner_name VARCHAR(120) NOT NULL,
    risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
    replica_count INTEGER NOT NULL DEFAULT 1,
    rollback_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    deployment_state VARCHAR(20) NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    validated_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT deployment_version_format
        CHECK (version ~ '^v?[0-9]+\.[0-9]+\.[0-9]+$'),

    CONSTRAINT deployment_risk_valid
        CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),

    CONSTRAINT deployment_replica_range
        CHECK (replica_count BETWEEN 1 AND 100),

    CONSTRAINT deployment_state_valid
        CHECK (
            deployment_state IN (
                'created',
                'validated',
                'executing',
                'completed',
                'failed'
            )
        ),

    CONSTRAINT critical_requires_rollback
        CHECK (
            risk_level <> 'critical'
            OR rollback_enabled = TRUE
        )
);

CREATE TABLE deployment_environment (
    deployment_id BIGINT NOT NULL
        REFERENCES deployment_requests(deployment_id)
        ON DELETE CASCADE,
    variable_name VARCHAR(100) NOT NULL,
    variable_value TEXT NOT NULL,
    PRIMARY KEY (deployment_id, variable_name)
);

CREATE TABLE deployment_metadata (
    deployment_id BIGINT NOT NULL
        REFERENCES deployment_requests(deployment_id)
        ON DELETE CASCADE,
    metadata_key VARCHAR(100) NOT NULL,
    metadata_value TEXT NOT NULL,
    PRIMARY KEY (deployment_id, metadata_key)
);

CREATE TABLE audit_events (
    audit_event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deployment_id BIGINT REFERENCES deployment_requests(deployment_id),
    event_type VARCHAR(100) NOT NULL,
    event_message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- Indexes
-- ---------------------------------------------------------------------------

CREATE INDEX idx_deployments_repository
    ON deployment_requests(repository_id);

CREATE INDEX idx_deployments_state
    ON deployment_requests(deployment_state);

CREATE INDEX idx_deployments_target
    ON deployment_requests(target_id);

CREATE INDEX idx_audit_deployment_time
    ON audit_events(deployment_id, created_at);

-- ---------------------------------------------------------------------------
-- Seed the factory registry
-- ---------------------------------------------------------------------------

INSERT INTO repositories (
    repository_name,
    owner_team
)
VALUES
    ('payment-api', 'platform-team'),
    ('legacy-reporting', 'operations-team'),
    ('billing-worker', 'platform-team');

INSERT INTO deployment_targets (
    target_code,
    description
)
VALUES
    ('kubernetes', 'Containerized workloads managed through Kubernetes'),
    ('virtual-machine', 'Workloads deployed to virtual machine instances'),
    ('serverless', 'Function-oriented serverless deployments');

INSERT INTO executor_registrations (
    target_id,
    executor_name
)
SELECT target_id, 'KubernetesDeploymentExecutor'
FROM deployment_targets
WHERE target_code = 'kubernetes';

INSERT INTO executor_registrations (
    target_id,
    executor_name
)
SELECT target_id, 'VirtualMachineDeploymentExecutor'
FROM deployment_targets
WHERE target_code = 'virtual-machine';

INSERT INTO executor_registrations (
    target_id,
    executor_name
)
SELECT target_id, 'ServerlessDeploymentExecutor'
FROM deployment_targets
WHERE target_code = 'serverless';

-- ---------------------------------------------------------------------------
-- Builder-like aggregate construction
-- ---------------------------------------------------------------------------
--
-- A relational database does not implement the object-oriented Builder
-- pattern directly. Instead, its tables allow the final aggregate to be
-- assembled across normalized relations while constraints enforce the
-- properties that must hold for a valid final object.

BEGIN;

INSERT INTO deployment_requests (
    repository_id,
    target_id,
    application_name,
    version,
    owner_name,
    risk_level,
    replica_count,
    rollback_enabled
)
SELECT
    r.repository_id,
    t.target_id,
    'payment-api',
    '4.2.0',
    'platform-team',
    'high',
    6,
    TRUE
FROM repositories r
JOIN deployment_targets t
    ON t.target_code = 'kubernetes'
WHERE r.repository_name = 'payment-api';

INSERT INTO deployment_environment (
    deployment_id,
    variable_name,
    variable_value
)
SELECT
    currval(
        pg_get_serial_sequence(
            'deployment_requests',
            'deployment_id'
        )
    ),
    'ENVIRONMENT',
    'production';

INSERT INTO deployment_environment (
    deployment_id,
    variable_name,
    variable_value
)
SELECT
    currval(
        pg_get_serial_sequence(
            'deployment_requests',
            'deployment_id'
        )
    ),
    'REGION',
    'ap-south-1';

INSERT INTO deployment_metadata (
    deployment_id,
    metadata_key,
    metadata_value
)
SELECT
    currval(
        pg_get_serial_sequence(
            'deployment_requests',
            'deployment_id'
        )
    ),
    'change_ticket',
    'CHG-2026-1042';

INSERT INTO deployment_metadata (
    deployment_id,
    metadata_key,
    metadata_value
)
SELECT
    currval(
        pg_get_serial_sequence(
            'deployment_requests',
            'deployment_id'
        )
    ),
    'owner_team',
    'platform';

COMMIT;

-- ---------------------------------------------------------------------------
-- Factory-oriented query
-- ---------------------------------------------------------------------------
--
-- The application can use this result as the registry from which a Factory
-- selects the concrete executor for each deployment target.

SELECT
    t.target_code,
    e.executor_name,
    e.active
FROM deployment_targets t
JOIN executor_registrations e
    ON e.target_id = t.target_id
ORDER BY t.target_code;

-- ---------------------------------------------------------------------------
-- Deployment validation view
-- ---------------------------------------------------------------------------

CREATE VIEW deployment_validation AS
SELECT
    d.deployment_id,
    d.application_name,
    d.version,
    t.target_code,
    e.executor_name,
    d.risk_level,
    d.replica_count,
    d.rollback_enabled,
    CASE
        WHEN d.risk_level = 'critical'
             AND NOT d.rollback_enabled
            THEN FALSE
        WHEN t.target_code = 'serverless'
             AND d.replica_count <> 1
            THEN FALSE
        WHEN d.deployment_state = 'failed'
            THEN FALSE
        ELSE TRUE
    END AS eligible_for_execution
FROM deployment_requests d
JOIN deployment_targets t
    ON t.target_id = d.target_id
JOIN executor_registrations e
    ON e.target_id = d.target_id
WHERE e.active = TRUE;

SELECT *
FROM deployment_validation
ORDER BY deployment_id;

-- ---------------------------------------------------------------------------
-- Metadata aggregation
-- ---------------------------------------------------------------------------

SELECT
    d.deployment_id,
    d.application_name,
    d.version,
    jsonb_object_agg(
        m.metadata_key,
        m.metadata_value
    ) AS metadata
FROM deployment_requests d
LEFT JOIN deployment_metadata m
    ON m.deployment_id = d.deployment_id
GROUP BY
    d.deployment_id,
    d.application_name,
    d.version
ORDER BY d.deployment_id;

-- ---------------------------------------------------------------------------
-- Transactional state transition
-- ---------------------------------------------------------------------------
--
-- The SELECT ... FOR UPDATE locks the selected deployment during the state
-- transition, preventing two workers from concurrently validating and
-- executing the same deployment record.

BEGIN;

SELECT deployment_id
FROM deployment_requests
WHERE deployment_id = 1
FOR UPDATE;

UPDATE deployment_requests
SET
    deployment_state = 'validated',
    validated_at = CURRENT_TIMESTAMP
WHERE deployment_id = 1
  AND deployment_state = 'created';

INSERT INTO audit_events (
    deployment_id,
    event_type,
    event_message
)
VALUES (
    1,
    'deployment.validated',
    'Deployment passed database-level validation.'
);

COMMIT;

-- ---------------------------------------------------------------------------
-- Execution transition
-- ---------------------------------------------------------------------------

BEGIN;

UPDATE deployment_requests
SET deployment_state = 'executing'
WHERE deployment_id = 1
  AND deployment_state = 'validated';

INSERT INTO audit_events (
    deployment_id,
    event_type,
    event_message
)
VALUES (
    1,
    'deployment.executing',
    'Deployment executor selected and execution started.'
);

COMMIT;

-- ---------------------------------------------------------------------------
-- Completion transition
-- ---------------------------------------------------------------------------

BEGIN;

UPDATE deployment_requests
SET
    deployment_state = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE deployment_id = 1
  AND deployment_state = 'executing';

INSERT INTO audit_events (
    deployment_id,
    event_type,
    event_message
)
VALUES (
    1,
    'deployment.completed',
    'Deployment completed successfully.'
);

COMMIT;

-- ---------------------------------------------------------------------------
-- Audit history
-- ---------------------------------------------------------------------------

SELECT
    d.application_name,
    d.version,
    a.event_type,
    a.event_message,
    a.created_at
FROM audit_events a
JOIN deployment_requests d
    ON d.deployment_id = a.deployment_id
ORDER BY a.created_at, a.audit_event_id;

-- ---------------------------------------------------------------------------
-- Invalid state demonstration
-- ---------------------------------------------------------------------------
--
-- The following statement is intentionally not executed because PostgreSQL
-- should reject a critical deployment without rollback through the CHECK
-- constraint. The SELECT below exposes the rule without intentionally
-- aborting the script.

SELECT
    'critical deployment without rollback' AS attempted_configuration,
    FALSE AS expected_to_be_accepted;

-- ---------------------------------------------------------------------------
-- Operational report
-- ---------------------------------------------------------------------------

SELECT
    t.target_code,
    COUNT(*) AS deployments,
    COUNT(*) FILTER (
        WHERE d.deployment_state = 'completed'
    ) AS completed,
    COUNT(*) FILTER (
        WHERE d.deployment_state = 'failed'
    ) AS failed,
    AVG(d.replica_count)::NUMERIC(10,2) AS average_replicas
FROM deployment_requests d
JOIN deployment_targets t
    ON t.target_id = d.target_id
GROUP BY t.target_code
ORDER BY t.target_code;
