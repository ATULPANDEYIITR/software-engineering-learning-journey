/*
============================================================
SOFTWARE RELEASE ENGINEERING
PostgreSQL Release Management and Governance Database
============================================================

Implements:
- Repositories and environments
- Immutable release artifacts
- Change requests and approvals
- Release strategies
- Deployment execution
- Traffic progression
- Automated health checks
- Rollback records
- Audit history
- Release eligibility
- Operational reporting

Target: PostgreSQL 14+
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS release_mgmt;

SET search_path TO release_mgmt, public;

-- ---------------------------------------------------------
-- ENUM TYPES
-- ---------------------------------------------------------

CREATE TYPE environment_type AS ENUM (
    'development',
    'staging',
    'production'
);

CREATE TYPE release_strategy AS ENUM (
    'rolling',
    'canary',
    'blue_green',
    'recreate'
);

CREATE TYPE change_risk AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

CREATE TYPE change_status AS ENUM (
    'submitted',
    'approved',
    'rejected',
    'implemented'
);

CREATE TYPE release_status AS ENUM (
    'created',
    'validating',
    'deploying',
    'succeeded',
    'failed',
    'rolled_back'
);

CREATE TYPE check_status AS ENUM (
    'pending',
    'passed',
    'failed'
);

CREATE TYPE deployment_status AS ENUM (
    'running',
    'succeeded',
    'failed',
    'rolled_back'
);

-- ---------------------------------------------------------
-- REPOSITORIES
-- ---------------------------------------------------------

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name VARCHAR(150) NOT NULL UNIQUE,
    owner_name VARCHAR(150) NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(repository_name)) > 0),
    CHECK (length(trim(owner_name)) > 0)
);

-- ---------------------------------------------------------
-- USERS AND RELEASE ROLES
-- ---------------------------------------------------------

CREATE TABLE release_users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(username)) > 0)
);

CREATE TABLE release_roles (
    role_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_name VARCHAR(80) NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE user_repository_roles (
    user_id BIGINT NOT NULL REFERENCES release_users(user_id),
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    role_id BIGINT NOT NULL REFERENCES release_roles(role_id),

    PRIMARY KEY (user_id, repository_id, role_id)
);

-- ---------------------------------------------------------
-- RELEASE ENVIRONMENTS
-- ---------------------------------------------------------

CREATE TABLE environments (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    environment_name environment_type NOT NULL,
    active_version VARCHAR(60),
    deployment_locked BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (repository_id, environment_name)
);

-- ---------------------------------------------------------
-- RELEASE ARTIFACTS
-- ---------------------------------------------------------

CREATE TABLE release_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    version VARCHAR(60) NOT NULL,
    commit_hash VARCHAR(64) NOT NULL,
    image_digest VARCHAR(71) NOT NULL,
    build_number INTEGER NOT NULL,
    created_by BIGINT NOT NULL REFERENCES release_users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (repository_id, version),
    UNIQUE (repository_id, build_number),

    CHECK (length(trim(version)) > 0),
    CHECK (length(commit_hash) >= 7),
    CHECK (image_digest ~ '^sha256:[a-fA-F0-9]{64}$'),
    CHECK (build_number > 0)
);

-- ---------------------------------------------------------
-- CHANGE MANAGEMENT
-- ---------------------------------------------------------

CREATE TABLE change_requests (
    change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    risk change_risk NOT NULL,
    status change_status NOT NULL DEFAULT 'submitted',
    requested_by BIGINT NOT NULL REFERENCES release_users(user_id),
    scheduled_start TIMESTAMPTZ,
    scheduled_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(title)) > 0),
    CHECK (length(trim(description)) > 0),
    CHECK (
        scheduled_end IS NULL
        OR scheduled_start IS NULL
        OR scheduled_end > scheduled_start
    )
);

CREATE TABLE change_approvals (
    approval_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    change_id BIGINT NOT NULL REFERENCES change_requests(change_id),
    reviewer_id BIGINT NOT NULL REFERENCES release_users(user_id),
    decision VARCHAR(20) NOT NULL,
    comments TEXT,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (change_id, reviewer_id),

    CHECK (decision IN ('approved', 'rejected'))
);

CREATE INDEX idx_change_status
ON change_requests(status, risk);

CREATE INDEX idx_change_repository
ON change_requests(repository_id, created_at DESC);

-- ---------------------------------------------------------
-- RELEASE RECORDS
-- ---------------------------------------------------------

CREATE TABLE releases (
    release_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    artifact_id BIGINT NOT NULL REFERENCES release_artifacts(artifact_id),
    change_id BIGINT NOT NULL REFERENCES change_requests(change_id),
    environment_id BIGINT NOT NULL REFERENCES environments(environment_id),
    strategy release_strategy NOT NULL,
    status release_status NOT NULL DEFAULT 'created',

    previous_version VARCHAR(60),
    traffic_percentage INTEGER NOT NULL DEFAULT 0,

    created_by BIGINT NOT NULL REFERENCES release_users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CHECK (traffic_percentage BETWEEN 0 AND 100)
);

CREATE INDEX idx_releases_environment_status
ON releases(environment_id, status);

CREATE INDEX idx_releases_created
ON releases(created_at DESC);

-- Only one active deployment can exist in an environment.
CREATE UNIQUE INDEX uq_active_environment_release
ON releases(environment_id)
WHERE status IN ('validating', 'deploying');

-- ---------------------------------------------------------
-- STATUS CHECKS
-- ---------------------------------------------------------

CREATE TABLE deployment_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id BIGINT NOT NULL REFERENCES releases(release_id),
    check_name VARCHAR(100) NOT NULL,
    status check_status NOT NULL DEFAULT 'pending',
    details TEXT,
    executed_at TIMESTAMPTZ,

    UNIQUE (release_id, check_name)
);

-- ---------------------------------------------------------
-- DEPLOYMENT EXECUTION
-- ---------------------------------------------------------

CREATE TABLE deployments (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id BIGINT NOT NULL REFERENCES releases(release_id),
    execution_number INTEGER NOT NULL,
    status deployment_status NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    failure_reason TEXT,

    UNIQUE (release_id, execution_number),
    CHECK (execution_number > 0)
);

CREATE INDEX idx_deployments_release
ON deployments(release_id, started_at DESC);

-- ---------------------------------------------------------
-- DEPLOYMENT METRICS
-- ---------------------------------------------------------

CREATE TABLE deployment_metrics (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    deployment_id BIGINT NOT NULL REFERENCES deployments(deployment_id),
    traffic_percentage INTEGER NOT NULL,
    error_rate NUMERIC(8,6) NOT NULL,
    latency_ms NUMERIC(12,3) NOT NULL,
    availability NUMERIC(8,6) NOT NULL,
    successful_requests BIGINT NOT NULL DEFAULT 0,
    failed_requests BIGINT NOT NULL DEFAULT 0,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (traffic_percentage BETWEEN 0 AND 100),
    CHECK (error_rate BETWEEN 0 AND 1),
    CHECK (latency_ms >= 0),
    CHECK (availability BETWEEN 0 AND 1),
    CHECK (successful_requests >= 0),
    CHECK (failed_requests >= 0)
);

CREATE INDEX idx_metrics_deployment_time
ON deployment_metrics(deployment_id, observed_at DESC);

-- ---------------------------------------------------------
-- ROLLBACK HISTORY
-- ---------------------------------------------------------

CREATE TABLE rollback_events (
    rollback_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id BIGINT NOT NULL REFERENCES releases(release_id),
    restored_version VARCHAR(60),
    reason TEXT NOT NULL,
    initiated_by BIGINT REFERENCES release_users(user_id),
    rolled_back_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------
-- AUDIT HISTORY
-- ---------------------------------------------------------

CREATE TABLE release_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    release_id BIGINT REFERENCES releases(release_id),
    change_id BIGINT REFERENCES change_requests(change_id),
    actor_id BIGINT REFERENCES release_users(user_id),
    event_type VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_release_audit_release
ON release_audit(release_id, created_at DESC);

CREATE INDEX idx_release_audit_details
ON release_audit USING GIN(details);

-- ---------------------------------------------------------
-- BRANCH-LEVEL RELEASE POLICIES
-- ---------------------------------------------------------

CREATE TABLE release_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    environment_name environment_type NOT NULL,
    required_successful_checks INTEGER NOT NULL DEFAULT 3,
    minimum_health_samples INTEGER NOT NULL DEFAULT 1,
    maximum_error_rate NUMERIC(8,6) NOT NULL DEFAULT 0.020000,
    maximum_latency_ms NUMERIC(12,3) NOT NULL DEFAULT 500,
    minimum_availability NUMERIC(8,6) NOT NULL DEFAULT 0.995000,
    require_approved_change BOOLEAN NOT NULL DEFAULT TRUE,
    require_artifact_digest BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (repository_id, environment_name),

    CHECK (required_successful_checks >= 0),
    CHECK (minimum_health_samples > 0),
    CHECK (maximum_error_rate BETWEEN 0 AND 1),
    CHECK (maximum_latency_ms > 0),
    CHECK (minimum_availability BETWEEN 0 AND 1)
);

-- ---------------------------------------------------------
-- APPROVAL REQUIREMENT FUNCTION
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION required_change_approvals(
    p_risk change_risk
)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT CASE p_risk
        WHEN 'low' THEN 1
        WHEN 'medium' THEN 1
        WHEN 'high' THEN 2
        WHEN 'critical' THEN 3
    END;
$$;

-- ---------------------------------------------------------
-- CHANGE APPROVAL VALIDATION TRIGGER
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_change_approval()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_requester BIGINT;
BEGIN
    SELECT requested_by
    INTO v_requester
    FROM change_requests
    WHERE change_id = NEW.change_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Change request does not exist';
    END IF;

    IF NEW.reviewer_id = v_requester THEN
        RAISE EXCEPTION 'Self-approval is prohibited';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM release_users
        WHERE user_id = NEW.reviewer_id
          AND active = TRUE
    ) THEN
        RAISE EXCEPTION 'Reviewer is not active';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_change_approval
BEFORE INSERT ON change_approvals
FOR EACH ROW
EXECUTE FUNCTION validate_change_approval();

-- ---------------------------------------------------------
-- AUTOMATIC CHANGE STATUS UPDATE
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION update_change_approval_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_change_id BIGINT;
    v_required INTEGER;
    v_approved INTEGER;
    v_rejected INTEGER;
    v_risk change_risk;
BEGIN
    v_change_id := NEW.change_id;

    SELECT risk
    INTO v_risk
    FROM change_requests
    WHERE change_id = v_change_id
    FOR UPDATE;

    SELECT
        COUNT(*) FILTER (WHERE decision = 'approved'),
        COUNT(*) FILTER (WHERE decision = 'rejected')
    INTO v_approved, v_rejected
    FROM change_approvals
    WHERE change_id = v_change_id;

    v_required := required_change_approvals(v_risk);

    UPDATE change_requests
    SET status = CASE
        WHEN v_rejected > 0 THEN 'rejected'::change_status
        WHEN v_approved >= v_required THEN 'approved'::change_status
        ELSE 'submitted'::change_status
    END
    WHERE change_id = v_change_id
      AND status IN ('submitted', 'approved');

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_update_change_approval_status
AFTER INSERT ON change_approvals
FOR EACH ROW
EXECUTE FUNCTION update_change_approval_status();

-- ---------------------------------------------------------
-- RELEASE CREATION VALIDATION
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_release_creation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_change_status change_status;
    v_artifact_repository BIGINT;
    v_environment_repository BIGINT;
    v_environment environment_type;
    v_current_version VARCHAR(60);
    v_new_version VARCHAR(60);
BEGIN
    SELECT status
    INTO v_change_status
    FROM change_requests
    WHERE change_id = NEW.change_id
    FOR UPDATE;

    IF v_change_status IS DISTINCT FROM 'approved' THEN
        RAISE EXCEPTION 'Release requires an approved change';
    END IF;

    SELECT repository_id, version
    INTO v_artifact_repository, v_new_version
    FROM release_artifacts
    WHERE artifact_id = NEW.artifact_id;

    SELECT repository_id, environment_name, active_version
    INTO v_environment_repository, v_environment, v_current_version
    FROM environments
    WHERE environment_id = NEW.environment_id
    FOR UPDATE;

    IF v_artifact_repository <> v_environment_repository THEN
        RAISE EXCEPTION 'Artifact and environment repositories differ';
    END IF;

    IF v_current_version IS NOT DISTINCT FROM v_new_version THEN
        RAISE EXCEPTION 'Version is already active';
    END IF;

    NEW.previous_version := v_current_version;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_release_creation
BEFORE INSERT ON releases
FOR EACH ROW
EXECUTE FUNCTION validate_release_creation();

-- ---------------------------------------------------------
-- DEPLOYMENT ELIGIBILITY FUNCTION
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION check_release_eligibility(
    p_release_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_release RECORD;
    v_policy RECORD;
    v_check_count INTEGER;
    v_failed_checks INTEGER;
    v_approved INTEGER;
    v_required INTEGER;
    v_metric_count INTEGER;
    v_unhealthy_count INTEGER;
BEGIN
    SELECT
        r.release_id,
        r.status,
        r.strategy,
        r.artifact_id,
        r.change_id,
        r.environment_id,
        a.repository_id,
        a.image_digest,
        c.status AS change_status,
        c.risk,
        e.environment_name
    INTO v_release
    FROM releases r
    JOIN release_artifacts a
        ON a.artifact_id = r.artifact_id
    JOIN change_requests c
        ON c.change_id = r.change_id
    JOIN environments e
        ON e.environment_id = r.environment_id
    WHERE r.release_id = p_release_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Release not found'::TEXT;
        RETURN;
    END IF;

    IF v_release.status NOT IN ('created', 'failed') THEN
        RETURN QUERY SELECT FALSE, 'Invalid release state'::TEXT;
        RETURN;
    END IF;

    IF v_release.change_status <> 'approved' THEN
        RETURN QUERY SELECT FALSE, 'Change is not approved'::TEXT;
        RETURN;
    END IF;

    SELECT *
    INTO v_policy
    FROM release_policies
    WHERE repository_id = v_release.repository_id
      AND environment_name = v_release.environment_name;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Release policy is missing'::TEXT;
        RETURN;
    END IF;

    IF v_policy.require_artifact_digest
       AND v_release.image_digest !~ '^sha256:[a-fA-F0-9]{64}$'
    THEN
        RETURN QUERY SELECT FALSE, 'Invalid artifact digest'::TEXT;
        RETURN;
    END IF;

    SELECT
        COUNT(*) FILTER (WHERE status = 'passed'),
        COUNT(*) FILTER (WHERE status <> 'passed')
    INTO v_check_count, v_failed_checks
    FROM deployment_checks
    WHERE release_id = p_release_id;

    IF v_check_count < v_policy.required_successful_checks
       OR v_failed_checks > 0
    THEN
        RETURN QUERY SELECT FALSE, 'Deployment checks incomplete or failed'::TEXT;
        RETURN;
    END IF;

    IF v_release.status = 'created' THEN
        RETURN QUERY SELECT TRUE, 'Eligible for deployment'::TEXT;
    END IF;

    RETURN QUERY SELECT TRUE, 'Eligible for retry after validation'::TEXT;
END;
$$;

-- ---------------------------------------------------------
-- RELEASE STATE TRANSITION TRIGGER
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_release_state_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.status = 'created' AND
            NEW.status IN ('validating', 'failed'))
        OR
        (OLD.status = 'validating' AND
            NEW.status IN ('deploying', 'failed'))
        OR
        (OLD.status = 'deploying' AND
            NEW.status IN ('succeeded', 'failed'))
        OR
        (OLD.status IN ('failed', 'succeeded') AND
            NEW.status = 'rolled_back')
    ) THEN
        RAISE EXCEPTION
            'Invalid release transition: % -> %',
            OLD.status,
            NEW.status;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_release_state_transition
BEFORE UPDATE OF status ON releases
FOR EACH ROW
EXECUTE FUNCTION validate_release_state_transition();

-- ---------------------------------------------------------
-- RELEASE AUDIT TRIGGER
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION audit_release_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO release_audit (
        release_id,
        change_id,
        event_type,
        details
    )
    VALUES (
        NEW.release_id,
        NEW.change_id,
        'RELEASE_STATE_CHANGED',
        jsonb_build_object(
            'old_status', OLD.status,
            'new_status', NEW.status,
            'version', (
                SELECT version
                FROM release_artifacts
                WHERE artifact_id = NEW.artifact_id
            )
        )
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_release_changes
AFTER UPDATE OF status ON releases
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION audit_release_changes();

-- ---------------------------------------------------------
-- ROLLBACK PROCEDURE
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE rollback_release(
    p_release_id BIGINT,
    p_reason TEXT,
    p_actor BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_release RECORD;
BEGIN
    IF length(trim(COALESCE(p_reason, ''))) = 0 THEN
        RAISE EXCEPTION 'Rollback reason is required';
    END IF;

    SELECT *
    INTO v_release
    FROM releases
    WHERE release_id = p_release_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Release not found';
    END IF;

    IF v_release.status NOT IN ('failed', 'succeeded') THEN
        RAISE EXCEPTION 'Release cannot be rolled back from current state';
    END IF;

    UPDATE environments
    SET active_version = v_release.previous_version,
        deployment_locked = FALSE,
        updated_at = CURRENT_TIMESTAMP
    WHERE environment_id = v_release.environment_id;

    UPDATE releases
    SET status = 'rolled_back',
        traffic_percentage = 0,
        completed_at = CURRENT_TIMESTAMP
    WHERE release_id = p_release_id;

    INSERT INTO rollback_events (
        release_id,
        restored_version,
        reason,
        initiated_by
    )
    VALUES (
        p_release_id,
        v_release.previous_version,
        p_reason,
        p_actor
    );

    INSERT INTO release_audit (
        release_id,
        change_id,
        actor_id,
        event_type,
        details
    )
    VALUES (
        p_release_id,
        v_release.change_id,
        p_actor,
        'ROLLBACK_COMPLETED',
        jsonb_build_object(
            'restored_version', v_release.previous_version,
            'reason', p_reason
        )
    );
END;
$$;

-- ---------------------------------------------------------
-- RELEASE REPORTING VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW release_overview AS
SELECT
    r.release_id,
    repo.repository_name,
    a.version,
    a.commit_hash,
    e.environment_name,
    r.strategy,
    r.status,
    r.previous_version,
    r.traffic_percentage,
    c.title AS change_title,
    c.risk,
    c.status AS change_status,
    u.username AS release_owner,
    r.created_at,
    r.completed_at
FROM releases r
JOIN release_artifacts a
    ON a.artifact_id = r.artifact_id
JOIN change_requests c
    ON c.change_id = r.change_id
JOIN environments e
    ON e.environment_id = r.environment_id
JOIN repositories repo
    ON repo.repository_id = a.repository_id
JOIN release_users u
    ON u.user_id = r.created_by;

-- ---------------------------------------------------------
-- HEALTH REPORTING VIEW
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW deployment_health_report AS
SELECT
    d.deployment_id,
    d.release_id,
    COUNT(m.metric_id) AS observation_count,
    ROUND(AVG(m.error_rate), 6) AS average_error_rate,
    ROUND(AVG(m.latency_ms), 3) AS average_latency_ms,
    ROUND(AVG(m.availability), 6) AS average_availability,
    MAX(m.traffic_percentage) AS maximum_traffic
FROM deployments d
LEFT JOIN deployment_metrics m
    ON m.deployment_id = d.deployment_id
GROUP BY d.deployment_id, d.release_id;

-- ---------------------------------------------------------
-- SAMPLE DATA
-- ---------------------------------------------------------

INSERT INTO repositories (
    repository_name,
    owner_name,
    default_branch
)
VALUES (
    'payment-platform',
    'engineering',
    'main'
);

INSERT INTO release_users (username, email)
VALUES
    ('release-manager', 'release@example.com'),
    ('engineering-lead', 'engineering@example.com'),
    ('technical-lead', 'technical@example.com'),
    ('security-lead', 'security@example.com'),
    ('operations-lead', 'operations@example.com'),
    ('developer', 'developer@example.com');

INSERT INTO release_roles (role_name, description)
VALUES
    ('developer', 'Application development'),
    ('release_manager', 'Release orchestration'),
    ('technical_reviewer', 'Technical change approval'),
    ('security_reviewer', 'Security approval'),
    ('operations', 'Production operations');

INSERT INTO environments (
    repository_id,
    environment_name,
    active_version
)
SELECT
    repository_id,
    'staging',
    '0.9.0'
FROM repositories
WHERE repository_name = 'payment-platform';

INSERT INTO environments (
    repository_id,
    environment_name,
    active_version
)
SELECT
    repository_id,
    'production',
    '1.0.0'
FROM repositories
WHERE repository_name = 'payment-platform';

INSERT INTO release_policies (
    repository_id,
    environment_name,
    required_successful_checks,
    minimum_health_samples,
    maximum_error_rate,
    maximum_latency_ms,
    minimum_availability
)
SELECT
    repository_id,
    'staging',
    2,
    2,
    0.030,
    700,
    0.990
FROM repositories
WHERE repository_name = 'payment-platform';

INSERT INTO release_policies (
    repository_id,
    environment_name,
    required_successful_checks,
    minimum_health_samples,
    maximum_error_rate,
    maximum_latency_ms,
    minimum_availability
)
SELECT
    repository_id,
    'production',
    3,
    2,
    0.020,
    500,
    0.995
FROM repositories
WHERE repository_name = 'payment-platform';

-- ---------------------------------------------------------
-- SAMPLE CHANGE REQUEST
-- ---------------------------------------------------------

INSERT INTO change_requests (
    repository_id,
    title,
    description,
    risk,
    requested_by
)
SELECT
    r.repository_id,
    'Database query optimization',
    'Optimize payment database query execution.',
    'high',
    u.user_id
FROM repositories r
CROSS JOIN release_users u
WHERE r.repository_name = 'payment-platform'
  AND u.username = 'developer';

-- Independent approvals: high-risk changes need two.
INSERT INTO change_approvals (
    change_id,
    reviewer_id,
    decision,
    comments
)
SELECT
    c.change_id,
    u.user_id,
    'approved',
    'Technical review completed.'
FROM change_requests c
CROSS JOIN release_users u
WHERE c.title = 'Database query optimization'
  AND u.username = 'technical-lead';

INSERT INTO change_approvals (
    change_id,
    reviewer_id,
    decision,
    comments
)
SELECT
    c.change_id,
    u.user_id,
    'approved',
    'Security review completed.'
FROM change_requests c
CROSS JOIN release_users u
WHERE c.title = 'Database query optimization'
  AND u.username = 'security-lead';

-- ---------------------------------------------------------
-- SAMPLE ARTIFACT
-- ---------------------------------------------------------

INSERT INTO release_artifacts (
    repository_id,
    version,
    commit_hash,
    image_digest,
    build_number,
    created_by
)
SELECT
    r.repository_id,
    '2.0.0',
    'b234567890abcdef',
    'sha256:' || repeat('b', 64),
    101,
    u.user_id
FROM repositories r
CROSS JOIN release_users u
WHERE r.repository_name = 'payment-platform'
  AND u.username = 'developer';

-- ---------------------------------------------------------
-- SAMPLE RELEASE
-- ---------------------------------------------------------

INSERT INTO releases (
    artifact_id,
    change_id,
    environment_id,
    strategy,
    status,
    created_by
)
SELECT
    a.artifact_id,
    c.change_id,
    e.environment_id,
    'canary',
    'created',
    u.user_id
FROM release_artifacts a
JOIN repositories repo
    ON repo.repository_id = a.repository_id
JOIN change_requests c
    ON c.repository_id = repo.repository_id
JOIN environments e
    ON e.repository_id = repo.repository_id
JOIN release_users u
    ON u.username = 'release-manager'
WHERE a.version = '2.0.0'
  AND c.title = 'Database query optimization'
  AND e.environment_name = 'production';

-- ---------------------------------------------------------
-- SAMPLE AUTOMATED CHECKS
-- ---------------------------------------------------------

INSERT INTO deployment_checks (
    release_id,
    check_name,
    status,
    details,
    executed_at
)
SELECT
    release_id,
    'unit-tests',
    'passed',
    'All unit tests passed.',
    CURRENT_TIMESTAMP
FROM releases
WHERE status = 'created';

INSERT INTO deployment_checks (
    release_id,
    check_name,
    status,
    details,
    executed_at
)
SELECT
    release_id,
    'security-scan',
    'passed',
    'No critical vulnerabilities.',
    CURRENT_TIMESTAMP
FROM releases
WHERE status = 'created';

INSERT INTO deployment_checks (
    release_id,
    check_name,
    status,
    details,
    executed_at
)
SELECT
    release_id,
    'integration-tests',
    'passed',
    'Integration tests passed.',
    CURRENT_TIMESTAMP
FROM releases
WHERE status = 'created';

-- ---------------------------------------------------------
-- SAMPLE DEPLOYMENT AND METRICS
-- ---------------------------------------------------------

INSERT INTO deployments (
    release_id,
    execution_number,
    status
)
SELECT
    release_id,
    1,
    'running'
FROM releases
WHERE status = 'created';

INSERT INTO deployment_metrics (
    deployment_id,
    traffic_percentage,
    error_rate,
    latency_ms,
    availability,
    successful_requests,
    failed_requests
)
SELECT
    d.deployment_id,
    sample.traffic,
    sample.error_rate,
    sample.latency,
    sample.availability,
    sample.successful_requests,
    sample.failed_requests
FROM deployments d
CROSS JOIN (
    VALUES
        (5, 0.004::NUMERIC, 150::NUMERIC, 0.999::NUMERIC, 5000, 20),
        (10, 0.006::NUMERIC, 180::NUMERIC, 0.998::NUMERIC, 6000, 40),
        (25, 0.075::NUMERIC, 900::NUMERIC, 0.980::NUMERIC, 4000, 300)
) AS sample(
    traffic,
    error_rate,
    latency,
    availability,
    successful_requests,
    failed_requests
)
WHERE d.status = 'running';

-- ---------------------------------------------------------
-- ELIGIBILITY QUERIES
-- ---------------------------------------------------------

SELECT *
FROM check_release_eligibility(
    (SELECT release_id FROM releases LIMIT 1)
);

-- Check completion and validation.
SELECT
    r.release_id,
    COUNT(*) FILTER (
        WHERE dc.status = 'passed'
    ) AS passed_checks,
    COUNT(*) FILTER (
        WHERE dc.status <> 'passed'
    ) AS incomplete_or_failed_checks
FROM releases r
LEFT JOIN deployment_checks dc
    ON dc.release_id = r.release_id
GROUP BY r.release_id;

-- ---------------------------------------------------------
-- HEALTH AGGREGATION
-- ---------------------------------------------------------

SELECT
    release_id,
    MAX(traffic_percentage) AS highest_traffic,
    ROUND(AVG(error_rate), 5) AS average_error_rate,
    ROUND(MAX(latency_ms), 2) AS maximum_latency,
    ROUND(MIN(availability), 5) AS minimum_availability
FROM deployments d
JOIN deployment_metrics m
    ON m.deployment_id = d.deployment_id
GROUP BY release_id;

-- ---------------------------------------------------------
-- RELEASE STRATEGY REPORT
-- ---------------------------------------------------------

SELECT
    strategy,
    environment_name,
    status,
    COUNT(*) AS release_count
FROM release_overview
GROUP BY strategy, environment_name, status
ORDER BY environment_name, strategy, status;

-- ---------------------------------------------------------
-- CHANGE APPROVAL REPORT
-- ---------------------------------------------------------

SELECT
    c.change_id,
    c.title,
    c.risk,
    c.status,
    required_change_approvals(c.risk) AS required_approvals,
    COUNT(a.approval_id) FILTER (
        WHERE a.decision = 'approved'
    ) AS approved_count
FROM change_requests c
LEFT JOIN change_approvals a
    ON a.change_id = c.change_id
GROUP BY
    c.change_id,
    c.title,
    c.risk,
    c.status;

-- ---------------------------------------------------------
-- DEPLOYMENT HEALTH EVALUATION
-- ---------------------------------------------------------

SELECT
    d.deployment_id,
    d.release_id,
    COUNT(m.metric_id) AS sample_count,
    BOOL_AND(
        m.error_rate <= p.maximum_error_rate
        AND m.latency_ms <= p.maximum_latency_ms
        AND m.availability >= p.minimum_availability
    ) AS all_samples_healthy
FROM deployments d
JOIN releases r
    ON r.release_id = d.release_id
JOIN environments e
    ON e.environment_id = r.environment_id
JOIN release_artifacts a
    ON a.artifact_id = r.artifact_id
JOIN release_policies p
    ON p.repository_id = a.repository_id
   AND p.environment_name = e.environment_name
LEFT JOIN deployment_metrics m
    ON m.deployment_id = d.deployment_id
GROUP BY
    d.deployment_id,
    d.release_id,
    p.maximum_error_rate,
    p.maximum_latency_ms,
    p.minimum_availability;

-- ---------------------------------------------------------
-- WORKFLOW PROCESSING EXAMPLE
-- ---------------------------------------------------------
-- This transaction demonstrates how a failed deployment
-- is recorded and the previous version is restored.
--
-- It does not activate the candidate version.

DO $$
DECLARE
    v_release_id BIGINT;
    v_deployment_id BIGINT;
BEGIN
    SELECT release_id
    INTO v_release_id
    FROM releases
    WHERE status = 'created'
    ORDER BY release_id
    LIMIT 1
    FOR UPDATE;

    IF v_release_id IS NOT NULL THEN

        UPDATE releases
        SET status = 'validating'
        WHERE release_id = v_release_id;

        UPDATE releases
        SET status = 'deploying'
        WHERE release_id = v_release_id;

        UPDATE deployments
        SET status = 'failed',
            completed_at = CURRENT_TIMESTAMP,
            failure_reason = 'Canary health threshold exceeded'
        WHERE release_id = v_release_id
          AND status = 'running'
        RETURNING deployment_id INTO v_deployment_id;

        UPDATE releases
        SET status = 'failed'
        WHERE release_id = v_release_id;

        IF v_deployment_id IS NOT NULL THEN
            UPDATE releases
            SET status = 'rolled_back',
                traffic_percentage = 0,
                completed_at = CURRENT_TIMESTAMP
            WHERE release_id = v_release_id;

            INSERT INTO rollback_events (
                release_id,
                restored_version,
                reason
            )
            SELECT
                release_id,
                previous_version,
                'Canary health threshold exceeded'
            FROM releases
            WHERE release_id = v_release_id;
        END IF;
    END IF;
END;
$$;

-- ---------------------------------------------------------
-- ROLLBACK AND ACTIVE VERSION REPORT
-- ---------------------------------------------------------

SELECT
    repository_name,
    environment_name,
    active_version,
    deployment_locked,
    updated_at
FROM environments e
JOIN repositories r
    ON r.repository_id = e.repository_id
ORDER BY repository_name, environment_name;

SELECT
    release_id,
    restored_version,
    reason,
    rolled_back_at
FROM rollback_events
ORDER BY rolled_back_at DESC;

-- ---------------------------------------------------------
-- AUDIT REPORT
-- ---------------------------------------------------------

SELECT
    audit_id,
    release_id,
    change_id,
    event_type,
    details,
    created_at
FROM release_audit
ORDER BY created_at DESC;

COMMIT;
