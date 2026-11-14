/*
===============================================================================
ENVIRONMENT MANAGEMENT
Development | Testing | Staging | Production

PostgreSQL 15+

Implements:
- Environment and repository-independent release management
- Environment-specific configuration
- Immutable release artifacts
- Deployment history
- Deployment approvals
- Automated checks
- Environment secrets metadata
- Health verification
- Promotion enforcement
- Rollback
- Deployment reporting

Security:
Secret values are not stored in this database.
Only secret identifiers and availability metadata are recorded.
Production credentials belong in an external secret manager.

Execute as a database owner with permission to create schemas.
===============================================================================
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS environment_mgmt;

SET search_path TO environment_mgmt, public;

-- ---------------------------------------------------------------------------
-- 1. DOMAIN TYPES
-- ---------------------------------------------------------------------------

CREATE TYPE environment_name AS ENUM (
    'development',
    'testing',
    'staging',
    'production'
);

CREATE TYPE deployment_status AS ENUM (
    'pending',
    'validating',
    'deployed',
    'failed',
    'rolled_back'
);

CREATE TYPE approval_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'revoked'
);

CREATE TYPE check_status AS ENUM (
    'pending',
    'passed',
    'failed',
    'skipped'
);

-- ---------------------------------------------------------------------------
-- 2. ORGANIZATIONAL IDENTITIES
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    role_name VARCHAR(60) NOT NULL,
    PRIMARY KEY (user_id, role_name)
);

-- ---------------------------------------------------------------------------
-- 3. APPLICATIONS AND ENVIRONMENTS
-- ---------------------------------------------------------------------------

CREATE TABLE applications (
    application_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    application_name VARCHAR(120) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE environments (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    environment_code environment_name NOT NULL UNIQUE,

    application_url TEXT NOT NULL,

    database_name VARCHAR(120) NOT NULL,

    debug_enabled BOOLEAN NOT NULL DEFAULT FALSE,

    replica_count INTEGER NOT NULL,

    minimum_healthy_replicas INTEGER NOT NULL,

    deployment_timeout_seconds INTEGER NOT NULL DEFAULT 120,

    approval_required BOOLEAN NOT NULL DEFAULT FALSE,

    secrets_required BOOLEAN NOT NULL DEFAULT TRUE,

    is_available BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_replica_count
        CHECK (replica_count >= 1),

    CONSTRAINT valid_healthy_replicas
        CHECK (
            minimum_healthy_replicas >= 1
            AND minimum_healthy_replicas <= replica_count
        ),

    CONSTRAINT valid_timeout
        CHECK (deployment_timeout_seconds > 0),

    CONSTRAINT nondevelopment_https
        CHECK (
            environment_code = 'development'
            OR application_url LIKE 'https://%'
        ),

    CONSTRAINT debug_environment_restriction
        CHECK (
            environment_code = 'development'
            OR debug_enabled = FALSE
        ),

    CONSTRAINT approval_environment_restriction
        CHECK (
            environment_code NOT IN ('staging', 'production')
            OR approval_required = TRUE
        )
);

CREATE TABLE application_environments (
    application_id BIGINT NOT NULL
        REFERENCES applications(application_id),

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    PRIMARY KEY (application_id, environment_id)
);

-- ---------------------------------------------------------------------------
-- 4. RELEASE ARTIFACTS
-- ---------------------------------------------------------------------------

CREATE TABLE release_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    artifact_name VARCHAR(150) NOT NULL,

    version VARCHAR(40) NOT NULL,

    source_commit VARCHAR(64) NOT NULL,

    sha256_digest CHAR(64) NOT NULL UNIQUE,

    build_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    build_status VARCHAR(20) NOT NULL DEFAULT 'successful',

    created_by BIGINT REFERENCES users(user_id),

    CONSTRAINT valid_semantic_version
        CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),

    CONSTRAINT valid_commit
        CHECK (source_commit ~ '^[a-f0-9]{7,64}$'),

    CONSTRAINT valid_digest
        CHECK (sha256_digest ~ '^[a-f0-9]{64}$'),

    CONSTRAINT valid_build_status
        CHECK (build_status IN ('successful', 'failed')),

    UNIQUE (artifact_name, version)
);

CREATE INDEX idx_artifacts_created
    ON release_artifacts(build_timestamp DESC);

CREATE INDEX idx_artifacts_commit
    ON release_artifacts(source_commit);

-- ---------------------------------------------------------------------------
-- 5. ENVIRONMENT CONFIGURATION
-- ---------------------------------------------------------------------------

CREATE TABLE configuration_items (
    configuration_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    application_id BIGINT NOT NULL,

    environment_id BIGINT NOT NULL,

    configuration_key VARCHAR(150) NOT NULL,

    configuration_value TEXT NOT NULL,

    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,

    version INTEGER NOT NULL DEFAULT 1,

    updated_by BIGINT REFERENCES users(user_id),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (application_id, environment_id)
        REFERENCES application_environments(
            application_id,
            environment_id
        ),

    UNIQUE (
        application_id,
        environment_id,
        configuration_key
    ),

    CHECK (version >= 1)
);

CREATE TABLE environment_secrets (
    secret_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    secret_name VARCHAR(150) NOT NULL,

    external_reference TEXT NOT NULL,

    is_available BOOLEAN NOT NULL DEFAULT FALSE,

    last_verified_at TIMESTAMPTZ,

    UNIQUE (environment_id, secret_name)
);

COMMENT ON TABLE environment_secrets IS
'Stores external secret references only. Actual credential values must remain outside PostgreSQL.';

-- ---------------------------------------------------------------------------
-- 6. RELEASE CHECKS
-- ---------------------------------------------------------------------------

CREATE TABLE check_definitions (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    check_code VARCHAR(80) NOT NULL UNIQUE,

    description TEXT NOT NULL
);

CREATE TABLE environment_required_checks (
    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    check_id BIGINT NOT NULL
        REFERENCES check_definitions(check_id),

    PRIMARY KEY (environment_id, check_id)
);

-- ---------------------------------------------------------------------------
-- 7. DEPLOYMENTS
-- ---------------------------------------------------------------------------

CREATE TABLE deployments (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    deployment_reference VARCHAR(40) NOT NULL UNIQUE,

    application_id BIGINT NOT NULL
        REFERENCES applications(application_id),

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    artifact_id BIGINT NOT NULL
        REFERENCES release_artifacts(artifact_id),

    deployed_by BIGINT NOT NULL
        REFERENCES users(user_id),

    status deployment_status NOT NULL DEFAULT 'pending',

    previous_deployment_id BIGINT
        REFERENCES deployments(deployment_id),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    healthy_replicas INTEGER,

    failure_reason TEXT,

    CONSTRAINT valid_healthy_replica_count
        CHECK (
            healthy_replicas IS NULL
            OR healthy_replicas >= 0
        ),

    CONSTRAINT valid_completion_time
        CHECK (
            completed_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT no_self_reference
        CHECK (
            previous_deployment_id IS NULL
            OR previous_deployment_id <> deployment_id
        )
);

CREATE INDEX idx_deployments_environment_time
    ON deployments(environment_id, started_at DESC);

CREATE INDEX idx_deployments_artifact
    ON deployments(artifact_id);

CREATE INDEX idx_deployments_status
    ON deployments(status);

CREATE INDEX idx_deployments_success
    ON deployments(environment_id, completed_at DESC)
    WHERE status = 'deployed';

-- ---------------------------------------------------------------------------
-- 8. APPROVAL WORKFLOW
-- ---------------------------------------------------------------------------

CREATE TABLE deployment_approvals (
    approval_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    deployment_id BIGINT NOT NULL
        REFERENCES deployments(deployment_id),

    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),

    required_role VARCHAR(60) NOT NULL,

    status approval_status NOT NULL DEFAULT 'pending',

    decision_reason TEXT,

    reviewed_at TIMESTAMPTZ,

    UNIQUE (deployment_id, reviewer_id),

    CHECK (
        status = 'pending'
        OR reviewed_at IS NOT NULL
    )
);

CREATE INDEX idx_approvals_pending
    ON deployment_approvals(deployment_id)
    WHERE status = 'pending';

-- ---------------------------------------------------------------------------
-- 9. DEPLOYMENT CHECK RESULTS
-- ---------------------------------------------------------------------------

CREATE TABLE deployment_checks (
    deployment_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    deployment_id BIGINT NOT NULL
        REFERENCES deployments(deployment_id),

    check_id BIGINT NOT NULL
        REFERENCES check_definitions(check_id),

    status check_status NOT NULL DEFAULT 'pending',

    executed_at TIMESTAMPTZ,

    execution_details JSONB NOT NULL DEFAULT '{}'::JSONB,

    UNIQUE (deployment_id, check_id)
);

CREATE INDEX idx_deployment_checks_status
    ON deployment_checks(deployment_id, status);

-- ---------------------------------------------------------------------------
-- 10. DEPLOYMENT AUDIT LOG
-- ---------------------------------------------------------------------------

CREATE TABLE deployment_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    deployment_id BIGINT NOT NULL
        REFERENCES deployments(deployment_id),

    action VARCHAR(60) NOT NULL,

    actor_id BIGINT REFERENCES users(user_id),

    details JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_deployment_time
    ON deployment_audit(deployment_id, occurred_at DESC);

-- ---------------------------------------------------------------------------
-- 11. REQUIRED CONFIGURATION RECORDS
-- ---------------------------------------------------------------------------

INSERT INTO users (username, email)
VALUES
    ('developer01', 'developer01@example.com'),
    ('ci_pipeline', 'ci@example.com'),
    ('qa_manager', 'qa@example.com'),
    ('production_manager', 'production@example.com'),
    ('incident_commander', 'incident@example.com')
ON CONFLICT (username) DO NOTHING;

INSERT INTO user_roles (user_id, role_name)
SELECT user_id, role_name
FROM (
    SELECT u.user_id, v.role_name
    FROM users u
    JOIN (
        VALUES
            ('qa_manager', 'QA_MANAGER'),
            ('production_manager', 'PRODUCTION_MANAGER'),
            ('incident_commander', 'INCIDENT_COMMANDER'),
            ('developer01', 'DEVELOPER'),
            ('ci_pipeline', 'CI_SERVICE')
    ) AS v(username, role_name)
    ON v.username = u.username
) roles
ON CONFLICT DO NOTHING;

INSERT INTO applications (
    application_name,
    description
)
VALUES (
    'enterprise-application',
    'Environment-managed enterprise application.'
)
ON CONFLICT (application_name) DO NOTHING;

INSERT INTO environments (
    environment_code,
    application_url,
    database_name,
    debug_enabled,
    replica_count,
    minimum_healthy_replicas,
    deployment_timeout_seconds,
    approval_required,
    secrets_required
)
VALUES
(
    'development',
    'http://localhost:8000',
    'app_development',
    TRUE,
    1,
    1,
    60,
    FALSE,
    FALSE
),
(
    'testing',
    'https://test.example.internal',
    'app_testing',
    FALSE,
    1,
    1,
    120,
    FALSE,
    TRUE
),
(
    'staging',
    'https://staging.example.com',
    'app_staging',
    FALSE,
    2,
    2,
    180,
    TRUE,
    TRUE
),
(
    'production',
    'https://app.example.com',
    'app_production',
    FALSE,
    3,
    3,
    300,
    TRUE,
    TRUE
)
ON CONFLICT (environment_code) DO NOTHING;

INSERT INTO application_environments (
    application_id,
    environment_id
)
SELECT a.application_id, e.environment_id
FROM applications a
CROSS JOIN environments e
WHERE a.application_name = 'enterprise-application'
ON CONFLICT DO NOTHING;

INSERT INTO check_definitions (check_code, description)
VALUES
    ('unit_tests', 'Unit test execution.'),
    ('integration_tests', 'Integration test execution.'),
    ('security_scan', 'Dependency and application security scan.'),
    ('smoke_tests', 'Post-deployment smoke tests.'),
    ('load_tests', 'Load and performance tests.')
ON CONFLICT (check_code) DO NOTHING;

INSERT INTO environment_required_checks (
    environment_id,
    check_id
)
SELECT e.environment_id, c.check_id
FROM environments e
JOIN check_definitions c
ON (
    (e.environment_code = 'testing'
        AND c.check_code IN (
            'unit_tests',
            'integration_tests',
            'security_scan'
        ))
    OR
    (e.environment_code = 'staging'
        AND c.check_code IN (
            'unit_tests',
            'integration_tests',
            'security_scan',
            'smoke_tests'
        ))
    OR
    (e.environment_code = 'production'
        AND c.check_code IN (
            'unit_tests',
            'integration_tests',
            'security_scan',
            'smoke_tests',
            'load_tests'
        ))
)
ON CONFLICT DO NOTHING;

INSERT INTO environment_secrets (
    environment_id,
    secret_name,
    external_reference,
    is_available,
    last_verified_at
)
SELECT
    e.environment_id,
    secret_name,
    'vault://' || e.environment_code || '/' || secret_name,
    TRUE,
    NOW()
FROM environments e
CROSS JOIN (
    VALUES
        ('DATABASE_PASSWORD'),
        ('APPLICATION_SECRET')
) AS secrets(secret_name)
WHERE e.environment_code <> 'development'
ON CONFLICT (environment_id, secret_name)
DO UPDATE SET
    is_available = EXCLUDED.is_available,
    last_verified_at = EXCLUDED.last_verified_at;

-- ---------------------------------------------------------------------------
-- 12. DEPLOYMENT STATE TRANSITION ENFORCEMENT
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_deployment_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.status <> 'pending' THEN
            RAISE EXCEPTION
                'New deployment must start in pending state.';
        END IF;

        RETURN NEW;
    END IF;

    IF NEW.status = OLD.status THEN
        RETURN NEW;
    END IF;

    IF NOT (
        (OLD.status = 'pending'
            AND NEW.status IN ('validating', 'failed'))
        OR
        (OLD.status = 'validating'
            AND NEW.status IN ('deployed', 'failed'))
        OR
        (OLD.status = 'deployed'
            AND NEW.status = 'rolled_back')
    ) THEN
        RAISE EXCEPTION
            'Invalid deployment transition: % -> %',
            OLD.status,
            NEW.status;
    END IF;

    IF NEW.status IN ('deployed', 'failed', 'rolled_back')
       AND NEW.completed_at IS NULL THEN
        NEW.completed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_deployment_transition
BEFORE INSERT OR UPDATE OF status
ON deployments
FOR EACH ROW
EXECUTE FUNCTION validate_deployment_transition();

-- ---------------------------------------------------------------------------
-- 13. AUDIT DEPLOYMENT STATE CHANGES
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION audit_deployment_changes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO deployment_audit (
        deployment_id,
        action,
        actor_id,
        details
    )
    VALUES (
        NEW.deployment_id,
        CASE
            WHEN TG_OP = 'INSERT' THEN 'deployment_created'
            ELSE 'deployment_status_changed'
        END,
        NEW.deployed_by,
        jsonb_build_object(
            'status', NEW.status,
            'environment_id', NEW.environment_id,
            'artifact_id', NEW.artifact_id,
            'previous_status',
                CASE
                    WHEN TG_OP = 'UPDATE' THEN OLD.status::TEXT
                    ELSE NULL
                END
        )
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_deployment_audit
AFTER INSERT OR UPDATE OF status
ON deployments
FOR EACH ROW
EXECUTE FUNCTION audit_deployment_changes();

-- ---------------------------------------------------------------------------
-- 14. APPROVAL VALIDATION
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_deployment_approval()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    deployment_actor BIGINT;
    required_role_exists BOOLEAN;
    reviewer_active BOOLEAN;
BEGIN
    SELECT deployed_by
    INTO deployment_actor
    FROM deployments
    WHERE deployment_id = NEW.deployment_id;

    IF NEW.status = 'approved' THEN

        IF NEW.reviewer_id = deployment_actor THEN
            RAISE EXCEPTION
                'Deployment actor cannot approve their own deployment.';
        END IF;

        SELECT is_active
        INTO reviewer_active
        FROM users
        WHERE user_id = NEW.reviewer_id;

        IF reviewer_active IS DISTINCT FROM TRUE THEN
            RAISE EXCEPTION
                'Reviewer account is inactive or missing.';
        END IF;

        SELECT EXISTS (
            SELECT 1
            FROM user_roles
            WHERE user_id = NEW.reviewer_id
              AND role_name = NEW.required_role
        )
        INTO required_role_exists;

        IF NOT required_role_exists THEN
            RAISE EXCEPTION
                'Reviewer lacks required role: %',
                NEW.required_role;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_approval_validation
BEFORE INSERT OR UPDATE OF status
ON deployment_approvals
FOR EACH ROW
EXECUTE FUNCTION validate_deployment_approval();

-- ---------------------------------------------------------------------------
-- 15. RELEASE ELIGIBILITY FUNCTION
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION evaluate_deployment(
    p_deployment_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    d deployments%ROWTYPE;
    e environments%ROWTYPE;
    missing_checks TEXT;
    missing_secrets TEXT;
    approved BOOLEAN;
    previous_successful BOOLEAN;
    current_digest CHAR(64);
    previous_digest CHAR(64);
BEGIN
    SELECT *
    INTO d
    FROM deployments
    WHERE deployment_id = p_deployment_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Deployment not found';
        RETURN;
    END IF;

    SELECT *
    INTO e
    FROM environments
    WHERE environment_id = d.environment_id;

    IF NOT FOUND OR NOT e.is_available THEN
        RETURN QUERY SELECT FALSE, 'Environment unavailable';
        RETURN;
    END IF;

    IF d.status NOT IN ('pending', 'validating') THEN
        RETURN QUERY SELECT FALSE, 'Deployment is not awaiting validation';
        RETURN;
    END IF;

    IF e.environment_code = 'production' AND e.debug_enabled THEN
        RETURN QUERY SELECT FALSE, 'Production debug mode is prohibited';
        RETURN;
    END IF;

    IF e.environment_code <> 'development'
       AND e.application_url NOT LIKE 'https://%' THEN
        RETURN QUERY SELECT FALSE, 'HTTPS is required';
        RETURN;
    END IF;

    SELECT string_agg(c.check_code, ', ')
    INTO missing_checks
    FROM environment_required_checks erc
    JOIN check_definitions c
        ON c.check_id = erc.check_id
    LEFT JOIN deployment_checks dc
        ON dc.check_id = c.check_id
       AND dc.deployment_id = d.deployment_id
       AND dc.status = 'passed'
    WHERE erc.environment_id = d.environment_id
      AND dc.deployment_check_id IS NULL;

    IF missing_checks IS NOT NULL THEN
        RETURN QUERY
        SELECT FALSE, 'Required checks missing or failed: ' || missing_checks;
        RETURN;
    END IF;

    IF e.secrets_required THEN
        SELECT string_agg(required.secret_name, ', ')
        INTO missing_secrets
        FROM (
            VALUES
                ('DATABASE_PASSWORD'),
                ('APPLICATION_SECRET')
        ) AS required(secret_name)
        LEFT JOIN environment_secrets s
            ON s.environment_id = d.environment_id
           AND s.secret_name = required.secret_name
           AND s.is_available = TRUE
        WHERE s.secret_id IS NULL;

        IF missing_secrets IS NOT NULL THEN
            RETURN QUERY
            SELECT FALSE, 'Required secrets unavailable: ' || missing_secrets;
            RETURN;
        END IF;
    END IF;

    IF e.approval_required THEN
        SELECT EXISTS (
            SELECT 1
            FROM deployment_approvals a
            JOIN users u
                ON u.user_id = a.reviewer_id
            JOIN user_roles r
                ON r.user_id = a.reviewer_id
               AND r.role_name = a.required_role
            WHERE a.deployment_id = d.deployment_id
              AND a.status = 'approved'
              AND u.is_active = TRUE
              AND a.reviewer_id <> d.deployed_by
        )
        INTO approved;

        IF NOT approved THEN
            RETURN QUERY
            SELECT FALSE, 'No eligible independent approval';
            RETURN;
        END IF;
    END IF;

    -- Promotion requires the exact same artifact digest.
    IF e.environment_code <> 'development' THEN
        SELECT previous.environment_id IS NOT NULL,
               current_artifact.sha256_digest,
               previous_artifact.sha256_digest
        INTO previous_successful, current_digest, previous_digest
        FROM environments current_environment
        JOIN environments previous_environment
            ON previous_environment.environment_code =
                CASE e.environment_code
                    WHEN 'testing' THEN 'development'::environment_name
                    WHEN 'staging' THEN 'testing'::environment_name
                    WHEN 'production' THEN 'staging'::environment_name
                END
        JOIN LATERAL (
            SELECT d2.*
            FROM deployments d2
            WHERE d2.environment_id =
                previous_environment.environment_id
              AND d2.status = 'deployed'
            ORDER BY d2.completed_at DESC, d2.deployment_id DESC
            LIMIT 1
        ) previous ON TRUE
        JOIN release_artifacts current_artifact
            ON current_artifact.artifact_id = d.artifact_id
        JOIN release_artifacts previous_artifact
            ON previous_artifact.artifact_id = previous.artifact_id
        WHERE current_environment.environment_id = d.environment_id;

        IF NOT FOUND OR NOT previous_successful THEN
            RETURN QUERY
            SELECT FALSE, 'Previous environment has no successful deployment';
            RETURN;
        END IF;

        IF current_digest <> previous_digest THEN
            RETURN QUERY
            SELECT FALSE, 'Artifact digest differs from previous environment';
            RETURN;
        END IF;
    END IF;

    RETURN QUERY SELECT TRUE, 'All release conditions satisfied';
END;
$$;

-- ---------------------------------------------------------------------------
-- 16. DEPLOYMENT PROCESSING PROCEDURE
-- ---------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE process_deployment(
    p_deployment_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    eligibility RECORD;
    d deployments%ROWTYPE;
    e environments%ROWTYPE;
BEGIN
    -- Serialize processing for a specific deployment.
    SELECT *
    INTO d
    FROM deployments
    WHERE deployment_id = p_deployment_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Deployment not found';
    END IF;

    SELECT *
    INTO e
    FROM environments
    WHERE environment_id = d.environment_id
    FOR UPDATE;

    IF NOT FOUND OR NOT e.is_available THEN
        RAISE EXCEPTION 'Environment unavailable';
    END IF;

    IF d.status <> 'pending' THEN
        RAISE EXCEPTION 'Deployment must be pending';
    END IF;

    UPDATE deployments
    SET status = 'validating'
    WHERE deployment_id = p_deployment_id;

    SELECT *
    INTO eligibility
    FROM evaluate_deployment(p_deployment_id);

    IF NOT eligibility.eligible THEN
        UPDATE deployments
        SET status = 'failed',
            failure_reason = eligibility.reason
        WHERE deployment_id = p_deployment_id;

        RETURN;
    END IF;

    IF e.minimum_healthy_replicas > e.replica_count THEN
        UPDATE deployments
        SET status = 'failed',
            failure_reason = 'Insufficient healthy replicas'
        WHERE deployment_id = p_deployment_id;

        RETURN;
    END IF;

    UPDATE deployments
    SET status = 'deployed',
        healthy_replicas = e.replica_count,
        completed_at = NOW()
    WHERE deployment_id = p_deployment_id;

    INSERT INTO deployment_audit (
        deployment_id,
        action,
        actor_id,
        details
    )
    VALUES (
        p_deployment_id,
        'deployment_completed',
        d.deployed_by,
        jsonb_build_object(
            'healthy_replicas', e.replica_count
        )
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- 17. ROLLBACK PROCEDURE
-- ---------------------------------------------------------------------------

CREATE OR REPLACE PROCEDURE rollback_deployment(
    p_environment_id BIGINT,
    p_requested_by BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    current_deployment deployments%ROWTYPE;
    previous_deployment deployments%ROWTYPE;
BEGIN
    PERFORM 1
    FROM environments
    WHERE environment_id = p_environment_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Environment not found';
    END IF;

    SELECT *
    INTO current_deployment
    FROM deployments
    WHERE environment_id = p_environment_id
      AND status = 'deployed'
    ORDER BY completed_at DESC, deployment_id DESC
    LIMIT 1
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No active deployment';
    END IF;

    SELECT *
    INTO previous_deployment
    FROM deployments
    WHERE environment_id = p_environment_id
      AND status = 'rolled_back'
      AND deployment_id = current_deployment.previous_deployment_id;

    -- The normal target is the preceding successful deployment.
    IF NOT FOUND THEN
        SELECT *
        INTO previous_deployment
        FROM deployments
        WHERE environment_id = p_environment_id
          AND status = 'deployed'
          AND deployment_id <> current_deployment.deployment_id
        ORDER BY completed_at DESC, deployment_id DESC
        LIMIT 1;
    END IF;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No previous successful deployment';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM users
        WHERE user_id = p_requested_by
          AND is_active = TRUE
    ) THEN
        RAISE EXCEPTION 'Invalid rollback actor';
    END IF;

    UPDATE deployments
    SET status = 'rolled_back',
        completed_at = NOW()
    WHERE deployment_id = current_deployment.deployment_id;

    INSERT INTO deployment_audit (
        deployment_id,
        action,
        actor_id,
        details
    )
    VALUES (
        current_deployment.deployment_id,
        'rollback_requested',
        p_requested_by,
        jsonb_build_object(
            'restored_deployment',
            previous_deployment.deployment_reference
        )
    );
END;
$$;

-- ---------------------------------------------------------------------------
-- 18. REPORTING VIEWS
-- ---------------------------------------------------------------------------

CREATE OR REPLACE VIEW environment_deployment_report AS
SELECT
    e.environment_id,
    e.environment_code,
    e.application_url,
    e.is_available,
    e.replica_count,
    e.minimum_healthy_replicas,
    d.deployment_id,
    d.deployment_reference,
    d.status,
    a.version,
    a.sha256_digest,
    d.started_at,
    d.completed_at,
    d.healthy_replicas,
    d.failure_reason
FROM environments e
LEFT JOIN LATERAL (
    SELECT *
    FROM deployments d2
    WHERE d2.environment_id = e.environment_id
      AND d2.status IN ('deployed', 'failed', 'rolled_back')
    ORDER BY d2.started_at DESC, d2.deployment_id DESC
    LIMIT 1
) d ON TRUE
LEFT JOIN release_artifacts a
    ON a.artifact_id = d.artifact_id;

CREATE OR REPLACE VIEW release_quality_report AS
SELECT
    d.deployment_id,
    d.deployment_reference,
    e.environment_code,
    a.version,
    COUNT(dc.deployment_check_id) AS total_checks,
    COUNT(*) FILTER (
        WHERE dc.status = 'passed'
    ) AS passed_checks,
    COUNT(*) FILTER (
        WHERE dc.status = 'failed'
    ) AS failed_checks,
    COUNT(*) FILTER (
        WHERE dc.status = 'pending'
    ) AS pending_checks
FROM deployments d
JOIN environments e
    ON e.environment_id = d.environment_id
JOIN release_artifacts a
    ON a.artifact_id = d.artifact_id
LEFT JOIN deployment_checks dc
    ON dc.deployment_id = d.deployment_id
GROUP BY
    d.deployment_id,
    d.deployment_reference,
    e.environment_code,
    a.version;

-- ---------------------------------------------------------------------------
-- 19. SAMPLE RELEASE ARTIFACTS
-- ---------------------------------------------------------------------------

INSERT INTO release_artifacts (
    artifact_name,
    version,
    source_commit,
    sha256_digest,
    created_by
)
SELECT
    'enterprise-application',
    '1.0.0',
    'a1b2c3d4e5f6',
    repeat('a', 64),
    user_id
FROM users
WHERE username = 'developer01'
ON CONFLICT (artifact_name, version) DO NOTHING;

INSERT INTO release_artifacts (
    artifact_name,
    version,
    source_commit,
    sha256_digest,
    created_by
)
SELECT
    'enterprise-application',
    '1.1.0',
    'b2c3d4e5f6a7',
    repeat('b', 64),
    user_id
FROM users
WHERE username = 'developer01'
ON CONFLICT (artifact_name, version) DO NOTHING;

-- ---------------------------------------------------------------------------
-- 20. SAMPLE DEPLOYMENT WORKFLOW
-- ---------------------------------------------------------------------------

DO $$
DECLARE
    app_id BIGINT;
    dev_id BIGINT;
    test_id BIGINT;
    staging_id BIGINT;
    production_id BIGINT;

    artifact_v1 BIGINT;
    developer_id BIGINT;
    ci_id BIGINT;
    qa_id BIGINT;
    production_manager_id BIGINT;

    deployment_id BIGINT;
    check_record RECORD;
    target_environment BIGINT;
    actor_id BIGINT;
    reviewer_id BIGINT;
    required_role TEXT;
    reference_prefix TEXT;
    environment_record RECORD;
BEGIN
    SELECT application_id
    INTO app_id
    FROM applications
    WHERE application_name = 'enterprise-application';

    SELECT environment_id INTO dev_id
    FROM environments
    WHERE environment_code = 'development';

    SELECT environment_id INTO test_id
    FROM environments
    WHERE environment_code = 'testing';

    SELECT environment_id INTO staging_id
    FROM environments
    WHERE environment_code = 'staging';

    SELECT environment_id INTO production_id
    FROM environments
    WHERE environment_code = 'production';

    SELECT artifact_id INTO artifact_v1
    FROM release_artifacts
    WHERE artifact_name = 'enterprise-application'
      AND version = '1.0.0';

    SELECT user_id INTO developer_id
    FROM users WHERE username = 'developer01';

    SELECT user_id INTO ci_id
    FROM users WHERE username = 'ci_pipeline';

    SELECT user_id INTO qa_id
    FROM users WHERE username = 'qa_manager';

    SELECT user_id INTO production_manager_id
    FROM users WHERE username = 'production_manager';

    FOR environment_record IN
        SELECT
            environment_id,
            environment_code
        FROM environments
        ORDER BY CASE environment_code
            WHEN 'development' THEN 1
            WHEN 'testing' THEN 2
            WHEN 'staging' THEN 3
            WHEN 'production' THEN 4
        END
    LOOP
        target_environment := environment_record.environment_id;

        IF environment_record.environment_code = 'development' THEN
            actor_id := developer_id;
        ELSE
            actor_id := ci_id;
        END IF;

        reference_prefix := 'DEMO-' ||
            upper(environment_record.environment_code) || '-';

        INSERT INTO deployments (
            deployment_reference,
            application_id,
            environment_id,
            artifact_id,
            deployed_by,
            status
        )
        VALUES (
            reference_prefix || '1001',
            app_id,
            target_environment,
            artifact_v1,
            actor_id,
            'pending'
        )
        RETURNING deployments.deployment_id INTO deployment_id;

        -- Populate all required checks for the target environment.
        INSERT INTO deployment_checks (
            deployment_id,
            check_id,
            status,
            executed_at,
            execution_details
        )
        SELECT
            deployment_id,
            erc.check_id,
            'passed',
            NOW(),
            jsonb_build_object(
                'runner', 'ci-pipeline',
                'result', 'successful'
            )
        FROM environment_required_checks erc
        WHERE erc.environment_id = target_environment;

        -- Staging and production require separate role-based approvals.
        IF environment_record.environment_code = 'staging' THEN
            reviewer_id := qa_id;
            required_role := 'QA_MANAGER';

        ELSIF environment_record.environment_code = 'production' THEN
            reviewer_id := production_manager_id;
            required_role := 'PRODUCTION_MANAGER';

        ELSE
            reviewer_id := NULL;
            required_role := NULL;
        END IF;

        IF reviewer_id IS NOT NULL THEN
            INSERT INTO deployment_approvals (
                deployment_id,
                reviewer_id,
                required_role,
                status,
                decision_reason,
                reviewed_at
            )
            VALUES (
                deployment_id,
                reviewer_id,
                required_role,
                'approved',
                'Release validation completed.',
                NOW()
            );
        END IF;

        CALL process_deployment(deployment_id);
    END LOOP;
END;
$$;

-- ---------------------------------------------------------------------------
-- 21. RETRIEVAL
-- ---------------------------------------------------------------------------

SELECT
    environment_code,
    application_url,
    database_name,
    debug_enabled,
    replica_count,
    approval_required,
    is_available
FROM environments
ORDER BY CASE environment_code
    WHEN 'development' THEN 1
    WHEN 'testing' THEN 2
    WHEN 'staging' THEN 3
    WHEN 'production' THEN 4
END;

-- ---------------------------------------------------------------------------
-- 22. DEPLOYMENT VALIDATION
-- ---------------------------------------------------------------------------

SELECT
    d.deployment_reference,
    e.environment_code,
    result.eligible,
    result.reason
FROM deployments d
JOIN environments e
    ON e.environment_id = d.environment_id
CROSS JOIN LATERAL evaluate_deployment(d.deployment_id) result
ORDER BY d.deployment_id;

-- ---------------------------------------------------------------------------
-- 23. AGGREGATION
-- ---------------------------------------------------------------------------

SELECT
    e.environment_code,
    COUNT(d.deployment_id) AS total_deployments,
    COUNT(*) FILTER (
        WHERE d.status = 'deployed'
    ) AS successful_deployments,
    COUNT(*) FILTER (
        WHERE d.status = 'failed'
    ) AS failed_deployments,
    COUNT(*) FILTER (
        WHERE d.status = 'rolled_back'
    ) AS rolled_back_deployments
FROM environments e
LEFT JOIN deployments d
    ON d.environment_id = e.environment_id
GROUP BY e.environment_id, e.environment_code
ORDER BY e.environment_id;

-- ---------------------------------------------------------------------------
-- 24. CTE: RELEASE PROMOTION HISTORY
-- ---------------------------------------------------------------------------

WITH promotion_history AS (
    SELECT
        e.environment_code,
        a.version,
        a.sha256_digest,
        d.deployment_reference,
        d.status,
        d.completed_at,
        ROW_NUMBER() OVER (
            PARTITION BY e.environment_id
            ORDER BY d.completed_at DESC NULLS LAST,
                     d.deployment_id DESC
        ) AS release_rank
    FROM deployments d
    JOIN environments e
        ON e.environment_id = d.environment_id
    JOIN release_artifacts a
        ON a.artifact_id = d.artifact_id
)
SELECT
    environment_code,
    version,
    sha256_digest,
    deployment_reference,
    status,
    completed_at
FROM promotion_history
WHERE release_rank = 1
ORDER BY CASE environment_code
    WHEN 'development' THEN 1
    WHEN 'testing' THEN 2
    WHEN 'staging' THEN 3
    WHEN 'production' THEN 4
END;

-- ---------------------------------------------------------------------------
-- 25. QUALITY REPORT
-- ---------------------------------------------------------------------------

SELECT *
FROM release_quality_report
ORDER BY deployment_id;

-- ---------------------------------------------------------------------------
-- 26. FAILURE AND POLICY-ISSUE REPORT
-- ---------------------------------------------------------------------------

SELECT
    d.deployment_reference,
    e.environment_code,
    d.failure_reason,
    d.started_at
FROM deployments d
JOIN environments e
    ON e.environment_id = d.environment_id
WHERE d.status = 'failed'
ORDER BY d.started_at DESC;

-- ---------------------------------------------------------------------------
-- 27. ENVIRONMENT HEALTH REPORT
-- ---------------------------------------------------------------------------

SELECT
    environment_code,
    replica_count,
    minimum_healthy_replicas,
    is_available,
    CASE
        WHEN NOT is_available THEN 'unavailable'
        WHEN replica_count < minimum_healthy_replicas THEN 'unhealthy'
        ELSE 'configured'
    END AS health_configuration
FROM environments;

COMMIT;

-- ---------------------------------------------------------------------------
-- 28. OPERATIONAL EXAMPLES
-- ---------------------------------------------------------------------------

-- Inspect a particular environment:
-- SELECT * FROM environment_deployment_report
-- WHERE environment_code = 'production';

-- Inspect release quality:
-- SELECT * FROM release_quality_report;

-- Inspect approval history:
-- SELECT * FROM deployment_approvals;

-- Inspect audit records:
-- SELECT * FROM deployment_audit
-- ORDER BY occurred_at DESC;

-- Example rollback, using the production environment and incident commander:
--
-- BEGIN;
-- CALL rollback_deployment(
--     (SELECT environment_id FROM environments
--      WHERE environment_code = 'production'),
--     (SELECT user_id FROM users
--      WHERE username = 'incident_commander')
-- );
-- COMMIT;

-- Example invalid transition:
-- UPDATE deployments
-- SET status = 'deployed'
-- WHERE deployment_id = -1;
--
-- Direct transition enforcement rejects invalid state changes.
