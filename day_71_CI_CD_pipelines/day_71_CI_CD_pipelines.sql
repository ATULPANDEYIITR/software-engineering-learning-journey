/*
 * CI/CD PIPELINE AUTOMATION AND GOVERNANCE DATABASE
 *
 * PostgreSQL 15+
 *
 * Models:
 * - Organizations and repositories
 * - Branches and commits
 * - Pull Requests
 * - Pipeline definitions and executions
 * - Pipeline stages and dependencies
 * - Build artifacts
 * - Automated test results
 * - Security scan results
 * - Deployment environments
 * - Approval policies
 * - Pipeline approvals
 * - Deployment records
 * - Audit events
 *
 * Execute as a database owner with schema creation privileges.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS cicd;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

SET search_path TO cicd, public;

-- ---------------------------------------------------------
-- 1. Repository and identity management
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repositories (
    repository_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_name VARCHAR(150) NOT NULL,
    owner_name VARCHAR(150) NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    visibility VARCHAR(20) NOT NULL DEFAULT 'private'
        CHECK (visibility IN ('private', 'internal', 'public')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (owner_name, repository_name)
);

CREATE TABLE IF NOT EXISTS branches (
    branch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL
        REFERENCES repositories(repository_id),
    branch_name VARCHAR(150) NOT NULL,
    head_commit_sha VARCHAR(40),
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (repository_id, branch_name)
);

CREATE INDEX IF NOT EXISTS idx_branches_repository
ON branches(repository_id);

CREATE TABLE IF NOT EXISTS commits (
    commit_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL
        REFERENCES repositories(repository_id),
    commit_sha VARCHAR(40) NOT NULL,
    author_id UUID REFERENCES users(user_id),
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(repository_id, commit_sha)
);

-- ---------------------------------------------------------
-- 2. Pull Requests
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS pull_requests (
    pull_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL
        REFERENCES repositories(repository_id),
    source_branch_id UUID NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id UUID NOT NULL
        REFERENCES branches(branch_id),
    created_by UUID NOT NULL REFERENCES users(user_id),
    title VARCHAR(250) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN'
        CHECK (status IN (
            'OPEN', 'CLOSED', 'MERGED'
        )),
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    source_head_sha VARCHAR(40) NOT NULL,
    target_head_sha VARCHAR(40) NOT NULL,
    has_conflicts BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    merged_at TIMESTAMPTZ,
    CHECK (source_branch_id <> target_branch_id),
    CHECK (
        (status = 'MERGED' AND merged_at IS NOT NULL)
        OR
        (status <> 'MERGED' AND merged_at IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_pr_repository_status
ON pull_requests(repository_id, status);

CREATE INDEX IF NOT EXISTS idx_pr_target_branch
ON pull_requests(target_branch_id, status);

CREATE TABLE IF NOT EXISTS pull_request_commits (
    pull_request_id UUID NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    commit_id UUID NOT NULL REFERENCES commits(commit_id),
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    PRIMARY KEY(pull_request_id, commit_id),
    UNIQUE(pull_request_id, sequence_number)
);

-- ---------------------------------------------------------
-- 3. Pipeline definitions
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipelines (
    pipeline_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL
        REFERENCES repositories(repository_id),
    pipeline_name VARCHAR(150) NOT NULL,
    trigger_type VARCHAR(30) NOT NULL
        CHECK (trigger_type IN (
            'PUSH',
            'PULL_REQUEST',
            'SCHEDULED',
            'MANUAL',
            'RELEASE'
        )),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(repository_id, pipeline_name)
);

CREATE TABLE IF NOT EXISTS pipeline_stages (
    stage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL
        REFERENCES pipelines(pipeline_id) ON DELETE CASCADE,
    stage_name VARCHAR(100) NOT NULL,
    stage_type VARCHAR(30) NOT NULL
        CHECK (stage_type IN (
            'CHECKOUT',
            'BUILD',
            'UNIT_TEST',
            'INTEGRATION_TEST',
            'SECURITY_SCAN',
            'PACKAGE',
            'APPROVAL',
            'DEPLOY',
            'POST_DEPLOYMENT_TEST'
        )),
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    retry_limit INTEGER NOT NULL DEFAULT 0 CHECK (retry_limit >= 0),
    timeout_seconds INTEGER NOT NULL DEFAULT 300
        CHECK (timeout_seconds > 0),
    required BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(pipeline_id, stage_name),
    UNIQUE(pipeline_id, sequence_number)
);

CREATE TABLE IF NOT EXISTS stage_dependencies (
    stage_id UUID NOT NULL
        REFERENCES pipeline_stages(stage_id) ON DELETE CASCADE,
    depends_on_stage_id UUID NOT NULL
        REFERENCES pipeline_stages(stage_id) ON DELETE CASCADE,
    PRIMARY KEY(stage_id, depends_on_stage_id),
    CHECK(stage_id <> depends_on_stage_id)
);

-- Ensure dependencies belong to the same pipeline.
CREATE OR REPLACE FUNCTION validate_stage_dependency()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    dependent_pipeline UUID;
    prerequisite_pipeline UUID;
BEGIN
    SELECT pipeline_id INTO dependent_pipeline
    FROM pipeline_stages
    WHERE stage_id = NEW.stage_id;

    SELECT pipeline_id INTO prerequisite_pipeline
    FROM pipeline_stages
    WHERE stage_id = NEW.depends_on_stage_id;

    IF dependent_pipeline IS NULL
       OR prerequisite_pipeline IS NULL THEN
        RAISE EXCEPTION 'Referenced stage does not exist.';
    END IF;

    IF dependent_pipeline <> prerequisite_pipeline THEN
        RAISE EXCEPTION
            'Stage dependencies must belong to the same pipeline.';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_stage_dependency
ON stage_dependencies;

CREATE TRIGGER trg_validate_stage_dependency
BEFORE INSERT OR UPDATE ON stage_dependencies
FOR EACH ROW
EXECUTE FUNCTION validate_stage_dependency();

-- ---------------------------------------------------------
-- 4. Pipeline executions
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pipeline_id UUID NOT NULL REFERENCES pipelines(pipeline_id),
    pull_request_id UUID REFERENCES pull_requests(pull_request_id),
    branch_id UUID REFERENCES branches(branch_id),
    commit_sha VARCHAR(40) NOT NULL,
    environment VARCHAR(20) NOT NULL
        CHECK (environment IN (
            'DEVELOPMENT', 'STAGING', 'PRODUCTION'
        )),
    status VARCHAR(20) NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN (
            'QUEUED',
            'RUNNING',
            'SUCCESS',
            'FAILED',
            'CANCELLED'
        )),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    triggered_by UUID REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        completed_at IS NULL
        OR started_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status
ON pipeline_runs(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_commit
ON pipeline_runs(commit_sha);

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline
ON pipeline_runs(pipeline_id, created_at DESC);

CREATE TABLE IF NOT EXISTS stage_executions (
    execution_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL
        REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
    stage_id UUID NOT NULL REFERENCES pipeline_stages(stage_id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN (
            'PENDING',
            'RUNNING',
            'SUCCESS',
            'FAILED',
            'SKIPPED'
        )),
    attempt_number INTEGER NOT NULL DEFAULT 0
        CHECK (attempt_number >= 0),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    output_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    UNIQUE(run_id, stage_id),
    CHECK (
        completed_at IS NULL
        OR started_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE INDEX IF NOT EXISTS idx_stage_execution_status
ON stage_executions(run_id, status);

-- ---------------------------------------------------------
-- 5. Artifacts and quality results
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
    artifact_name VARCHAR(200) NOT NULL,
    artifact_version VARCHAR(100) NOT NULL,
    sha256 VARCHAR(64) NOT NULL
        CHECK (sha256 ~ '^[a-f0-9]{64}$'),
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    immutable BOOLEAN NOT NULL DEFAULT TRUE,
    storage_uri TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(run_id, artifact_name, artifact_version)
);

CREATE TABLE IF NOT EXISTS test_results (
    test_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL
        REFERENCES stage_executions(execution_id) ON DELETE CASCADE,
    test_suite VARCHAR(150) NOT NULL,
    total_tests INTEGER NOT NULL CHECK (total_tests >= 0),
    passed_tests INTEGER NOT NULL CHECK (passed_tests >= 0),
    failed_tests INTEGER NOT NULL CHECK (failed_tests >= 0),
    skipped_tests INTEGER NOT NULL DEFAULT 0
        CHECK (skipped_tests >= 0),
    coverage_percentage NUMERIC(5,2)
        CHECK (
            coverage_percentage BETWEEN 0 AND 100
        ),
    CHECK (
        total_tests =
        passed_tests + failed_tests + skipped_tests
    )
);

CREATE TABLE IF NOT EXISTS security_scan_results (
    scan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL
        REFERENCES stage_executions(execution_id) ON DELETE CASCADE,
    scanner_name VARCHAR(100) NOT NULL,
    critical_count INTEGER NOT NULL DEFAULT 0 CHECK (critical_count >= 0),
    high_count INTEGER NOT NULL DEFAULT 0 CHECK (high_count >= 0),
    medium_count INTEGER NOT NULL DEFAULT 0 CHECK (medium_count >= 0),
    low_count INTEGER NOT NULL DEFAULT 0 CHECK (low_count >= 0),
    scan_passed BOOLEAN NOT NULL,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------
-- 6. Deployment environments and policies
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS deployment_environments (
    environment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL
        REFERENCES repositories(repository_id),
    environment_name VARCHAR(20) NOT NULL
        CHECK (environment_name IN (
            'DEVELOPMENT', 'STAGING', 'PRODUCTION'
        )),
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(repository_id, environment_name)
);

CREATE TABLE IF NOT EXISTS deployment_policies (
    policy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    environment_id UUID NOT NULL UNIQUE
        REFERENCES deployment_environments(environment_id),
    require_successful_pipeline BOOLEAN NOT NULL DEFAULT TRUE,
    require_security_scan BOOLEAN NOT NULL DEFAULT TRUE,
    require_approval BOOLEAN NOT NULL DEFAULT FALSE,
    require_immutable_artifact BOOLEAN NOT NULL DEFAULT TRUE,
    minimum_test_coverage NUMERIC(5,2) NOT NULL DEFAULT 0
        CHECK (minimum_test_coverage BETWEEN 0 AND 100),
    minimum_approvals INTEGER NOT NULL DEFAULT 0
        CHECK (minimum_approvals >= 0),
    prevent_direct_deployment BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS deployment_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
    environment_id UUID NOT NULL
        REFERENCES deployment_environments(environment_id),
    reviewer_id UUID NOT NULL REFERENCES users(user_id),
    decision VARCHAR(20) NOT NULL
        CHECK (decision IN ('APPROVED', 'REJECTED')),
    comments TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(run_id, environment_id, reviewer_id)
);

CREATE TABLE IF NOT EXISTS deployments (
    deployment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES pipeline_runs(run_id),
    artifact_id UUID NOT NULL REFERENCES artifacts(artifact_id),
    environment_id UUID NOT NULL
        REFERENCES deployment_environments(environment_id),
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN (
            'PENDING', 'DEPLOYED', 'FAILED', 'ROLLED_BACK'
        )),
    deployed_by UUID REFERENCES users(user_id),
    deployed_at TIMESTAMPTZ,
    version VARCHAR(100) NOT NULL,
    rollback_of UUID REFERENCES deployments(deployment_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployments_environment
ON deployments(environment_id, created_at DESC);

-- ---------------------------------------------------------
-- 7. Audit records
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID REFERENCES pipeline_runs(run_id),
    actor_id UUID REFERENCES users(user_id),
    event_type VARCHAR(100) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_run_time
ON audit_events(run_id, created_at DESC);

-- ---------------------------------------------------------
-- 8. Pipeline execution integrity triggers
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_stage_execution()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    run_pipeline UUID;
    stage_pipeline UUID;
BEGIN
    SELECT pipeline_id INTO run_pipeline
    FROM pipeline_runs
    WHERE run_id = NEW.run_id;

    SELECT pipeline_id INTO stage_pipeline
    FROM pipeline_stages
    WHERE stage_id = NEW.stage_id;

    IF run_pipeline IS NULL OR stage_pipeline IS NULL THEN
        RAISE EXCEPTION 'Run or stage does not exist.';
    END IF;

    IF run_pipeline <> stage_pipeline THEN
        RAISE EXCEPTION
            'Execution stage must belong to the run pipeline.';
    END IF;

    IF NEW.status = 'SUCCESS'
       AND NEW.completed_at IS NULL THEN
        NEW.completed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_stage_execution
ON stage_executions;

CREATE TRIGGER trg_validate_stage_execution
BEFORE INSERT OR UPDATE ON stage_executions
FOR EACH ROW
EXECUTE FUNCTION validate_stage_execution();

CREATE OR REPLACE FUNCTION validate_deployment()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    run_status VARCHAR(20);
    artifact_run UUID;
    target_repository UUID;
    pipeline_repository UUID;
    environment_enabled BOOLEAN;
BEGIN
    SELECT status INTO run_status
    FROM pipeline_runs
    WHERE run_id = NEW.run_id;

    SELECT run_id INTO artifact_run
    FROM artifacts
    WHERE artifact_id = NEW.artifact_id;

    IF artifact_run <> NEW.run_id THEN
        RAISE EXCEPTION
            'Artifact must belong to the specified pipeline run.';
    END IF;

    SELECT repository_id, enabled
    INTO target_repository, environment_enabled
    FROM deployment_environments
    WHERE environment_id = NEW.environment_id;

    SELECT p.repository_id INTO pipeline_repository
    FROM pipeline_runs pr
    JOIN pipelines p ON p.pipeline_id = pr.pipeline_id
    WHERE pr.run_id = NEW.run_id;

    IF target_repository <> pipeline_repository THEN
        RAISE EXCEPTION
            'Deployment environment belongs to another repository.';
    END IF;

    IF NOT environment_enabled THEN
        RAISE EXCEPTION 'Deployment environment is disabled.';
    END IF;

    IF NEW.status = 'DEPLOYED' AND run_status <> 'SUCCESS' THEN
        RAISE EXCEPTION
            'Only successful pipeline runs can be deployed.';
    END IF;

    IF NEW.status = 'DEPLOYED' AND NEW.deployed_at IS NULL THEN
        NEW.deployed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_deployment
ON deployments;

CREATE TRIGGER trg_validate_deployment
BEFORE INSERT OR UPDATE ON deployments
FOR EACH ROW
EXECUTE FUNCTION validate_deployment();

-- ---------------------------------------------------------
-- 9. Deployment eligibility function
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION evaluate_deployment(
    p_run_id UUID,
    p_environment_id UUID
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    run_status VARCHAR(20);
    policy deployment_policies%ROWTYPE;
    artifact_is_immutable BOOLEAN;
    coverage NUMERIC(5,2);
    critical_findings INTEGER;
    high_findings INTEGER;
    approval_count INTEGER;
    rejected_count INTEGER;
    security_passed BOOLEAN;
BEGIN
    SELECT status INTO run_status
    FROM pipeline_runs
    WHERE run_id = p_run_id;

    IF run_status IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Pipeline run not found';
        RETURN;
    END IF;

    SELECT * INTO policy
    FROM deployment_policies
    WHERE environment_id = p_environment_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Deployment policy not found';
        RETURN;
    END IF;

    IF policy.require_successful_pipeline
       AND run_status <> 'SUCCESS' THEN
        RETURN QUERY SELECT FALSE, 'Pipeline unsuccessful';
        RETURN;
    END IF;

    SELECT COALESCE(BOOL_AND(a.immutable), FALSE)
    INTO artifact_is_immutable
    FROM artifacts a
    WHERE a.run_id = p_run_id;

    IF policy.require_immutable_artifact
       AND NOT artifact_is_immutable THEN
        RETURN QUERY SELECT FALSE, 'No immutable artifact';
        RETURN;
    END IF;

    SELECT COALESCE(MAX(tr.coverage_percentage), 0)
    INTO coverage
    FROM stage_executions se
    JOIN test_results tr ON tr.execution_id = se.execution_id
    WHERE se.run_id = p_run_id;

    IF coverage < policy.minimum_test_coverage THEN
        RETURN QUERY SELECT FALSE, 'Minimum test coverage not met';
        RETURN;
    END IF;

    SELECT
        COALESCE(SUM(ss.critical_count), 0),
        COALESCE(SUM(ss.high_count), 0),
        COALESCE(BOOL_AND(ss.scan_passed), FALSE)
    INTO critical_findings, high_findings, security_passed
    FROM stage_executions se
    JOIN security_scan_results ss
        ON ss.execution_id = se.execution_id
    WHERE se.run_id = p_run_id;

    IF policy.require_security_scan AND
       (
           critical_findings > 0
           OR high_findings > 0
           OR NOT security_passed
       ) THEN
        RETURN QUERY SELECT FALSE, 'Security policy failed';
        RETURN;
    END IF;

    SELECT
        COUNT(*) FILTER (WHERE decision = 'APPROVED'),
        COUNT(*) FILTER (WHERE decision = 'REJECTED')
    INTO approval_count, rejected_count
    FROM deployment_approvals
    WHERE run_id = p_run_id
      AND environment_id = p_environment_id;

    IF rejected_count > 0 THEN
        RETURN QUERY SELECT FALSE, 'Approval rejected';
        RETURN;
    END IF;

    IF policy.require_approval
       AND approval_count < policy.minimum_approvals THEN
        RETURN QUERY SELECT FALSE, 'Insufficient approvals';
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'All deployment conditions satisfied';
END;
$$;

-- ---------------------------------------------------------
-- 10. Deployment processing procedure
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE process_deployment(
    p_run_id UUID,
    p_artifact_id UUID,
    p_environment_id UUID,
    p_deployer_id UUID
)
LANGUAGE plpgsql
AS $$
DECLARE
    eligibility RECORD;
    artifact_version VARCHAR(100);
BEGIN
    -- Row locking protects concurrent deployment processing.
    PERFORM 1
    FROM pipeline_runs
    WHERE run_id = p_run_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pipeline run not found.';
    END IF;

    SELECT *
    INTO eligibility
    FROM evaluate_deployment(
        p_run_id,
        p_environment_id
    );

    IF NOT eligibility.eligible THEN
        RAISE EXCEPTION
            'Deployment rejected: %',
            eligibility.reason;
    END IF;

    SELECT version INTO artifact_version
    FROM artifacts
    WHERE artifact_id = p_artifact_id
      AND run_id = p_run_id;

    IF artifact_version IS NULL THEN
        RAISE EXCEPTION 'Artifact not found in pipeline run.';
    END IF;

    INSERT INTO deployments (
        run_id,
        artifact_id,
        environment_id,
        status,
        deployed_by,
        deployed_at,
        version
    )
    VALUES (
        p_run_id,
        p_artifact_id,
        p_environment_id,
        'DEPLOYED',
        p_deployer_id,
        NOW(),
        artifact_version
    );

    INSERT INTO audit_events (
        run_id,
        actor_id,
        event_type,
        details
    )
    VALUES (
        p_run_id,
        p_deployer_id,
        'DEPLOYMENT_COMPLETED',
        jsonb_build_object(
            'artifact_version', artifact_version,
            'environment_id', p_environment_id
        )
    );
END;
$$;

-- ---------------------------------------------------------
-- 11. Reporting views
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW pipeline_run_summary AS
SELECT
    pr.run_id,
    p.pipeline_name,
    r.repository_name,
    pr.commit_sha,
    pr.environment,
    pr.status,
    COUNT(se.execution_id) AS total_stages,
    COUNT(se.execution_id)
        FILTER (WHERE se.status = 'SUCCESS') AS successful_stages,
    COUNT(se.execution_id)
        FILTER (WHERE se.status = 'FAILED') AS failed_stages,
    pr.created_at
FROM pipeline_runs pr
JOIN pipelines p ON p.pipeline_id = pr.pipeline_id
JOIN repositories r ON r.repository_id = p.repository_id
LEFT JOIN stage_executions se ON se.run_id = pr.run_id
GROUP BY
    pr.run_id,
    p.pipeline_name,
    r.repository_name;

CREATE OR REPLACE VIEW deployment_audit_summary AS
SELECT
    d.deployment_id,
    r.repository_name,
    e.environment_name,
    d.version,
    d.status,
    d.deployed_at,
    u.username AS deployed_by
FROM deployments d
JOIN pipeline_runs pr ON pr.run_id = d.run_id
JOIN pipelines p ON p.pipeline_id = pr.pipeline_id
JOIN repositories r ON r.repository_id = p.repository_id
JOIN deployment_environments e
    ON e.environment_id = d.environment_id
LEFT JOIN users u ON u.user_id = d.deployed_by;

-- ---------------------------------------------------------
-- 12. Sample organization and repository
-- ---------------------------------------------------------

INSERT INTO users (
    username, email
)
VALUES
    ('atul', 'atul@example.org'),
    ('reviewer_one', 'reviewer1@example.org'),
    ('security_lead', 'security@example.org'),
    ('release_manager', 'release@example.org')
ON CONFLICT DO NOTHING;

INSERT INTO repositories (
    repository_name,
    owner_name,
    default_branch,
    visibility
)
VALUES (
    'payment-service',
    'engineering',
    'main',
    'private'
)
ON CONFLICT (owner_name, repository_name) DO NOTHING;

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit_sha,
    protected
)
SELECT
    repository_id,
    'main',
    repeat('a', 40),
    TRUE
FROM repositories
WHERE owner_name = 'engineering'
  AND repository_name = 'payment-service'
ON CONFLICT DO NOTHING;

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit_sha,
    protected
)
SELECT
    repository_id,
    'feature/payment-validation',
    repeat('b', 40),
    FALSE
FROM repositories
WHERE owner_name = 'engineering'
  AND repository_name = 'payment-service'
ON CONFLICT DO NOTHING;

INSERT INTO commits (
    repository_id,
    commit_sha,
    author_id,
    message
)
SELECT
    r.repository_id,
    repeat('a', 40),
    u.user_id,
    'Initial main branch commit'
FROM repositories r
CROSS JOIN users u
WHERE r.repository_name = 'payment-service'
  AND u.username = 'atul'
ON CONFLICT DO NOTHING;

INSERT INTO commits (
    repository_id,
    commit_sha,
    author_id,
    message
)
SELECT
    r.repository_id,
    repeat('b', 40),
    u.user_id,
    'Add payment validation'
FROM repositories r
CROSS JOIN users u
WHERE r.repository_name = 'payment-service'
  AND u.username = 'atul'
ON CONFLICT DO NOTHING;

INSERT INTO pipelines (
    repository_id,
    pipeline_name,
    trigger_type
)
SELECT
    repository_id,
    'payment-ci-cd',
    'PULL_REQUEST'
FROM repositories
WHERE repository_name = 'payment-service'
  AND owner_name = 'engineering'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 13. Pipeline stages and dependency graph
-- ---------------------------------------------------------

INSERT INTO pipeline_stages (
    pipeline_id,
    stage_name,
    stage_type,
    sequence_number,
    retry_limit,
    timeout_seconds
)
SELECT
    p.pipeline_id,
    stages.stage_name,
    stages.stage_type,
    stages.sequence_number,
    stages.retry_limit,
    stages.timeout_seconds
FROM pipelines p
CROSS JOIN (
    VALUES
        ('checkout', 'CHECKOUT', 1, 0, 120),
        ('build', 'BUILD', 2, 2, 600),
        ('unit-tests', 'UNIT_TEST', 3, 2, 600),
        ('integration-tests', 'INTEGRATION_TEST', 4, 1, 900),
        ('security-scan', 'SECURITY_SCAN', 5, 1, 600),
        ('package', 'PACKAGE', 6, 1, 300),
        ('approval', 'APPROVAL', 7, 0, 3600),
        ('deploy', 'DEPLOY', 8, 1, 600)
) AS stages(
    stage_name,
    stage_type,
    sequence_number,
    retry_limit,
    timeout_seconds
)
WHERE p.pipeline_name = 'payment-ci-cd'
ON CONFLICT DO NOTHING;

INSERT INTO stage_dependencies (
    stage_id,
    depends_on_stage_id
)
SELECT dependent.stage_id, prerequisite.stage_id
FROM (
    VALUES
        ('build', 'checkout'),
        ('unit-tests', 'build'),
        ('integration-tests', 'build'),
        ('security-scan', 'build'),
        ('package', 'unit-tests'),
        ('package', 'integration-tests'),
        ('package', 'security-scan'),
        ('approval', 'package'),
        ('deploy', 'approval')
) AS dependency(dependent_name, prerequisite_name)
JOIN pipeline_stages dependent
    ON dependent.stage_name = dependency.dependent_name
JOIN pipeline_stages prerequisite
    ON prerequisite.stage_name = dependency.prerequisite_name
JOIN pipelines p
    ON p.pipeline_id = dependent.pipeline_id
WHERE p.pipeline_name = 'payment-ci-cd'
  AND prerequisite.pipeline_id = dependent.pipeline_id
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 14. Pull Request sample
-- ---------------------------------------------------------

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    created_by,
    title,
    source_head_sha,
    target_head_sha
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    u.user_id,
    'Add payment validation and CI/CD checks',
    repeat('b', 40),
    repeat('a', 40)
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
JOIN branches target
    ON target.repository_id = r.repository_id
CROSS JOIN users u
WHERE r.repository_name = 'payment-service'
  AND source.branch_name = 'feature/payment-validation'
  AND target.branch_name = 'main'
  AND u.username = 'atul'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 15. Deployment configuration
-- ---------------------------------------------------------

INSERT INTO deployment_environments (
    repository_id,
    environment_name,
    protected
)
SELECT
    repository_id,
    environment_name,
    environment_name = 'PRODUCTION'
FROM repositories
CROSS JOIN (
    VALUES
        ('DEVELOPMENT'),
        ('STAGING'),
        ('PRODUCTION')
) AS env(environment_name)
WHERE repository_name = 'payment-service'
ON CONFLICT DO NOTHING;

INSERT INTO deployment_policies (
    environment_id,
    require_successful_pipeline,
    require_security_scan,
    require_approval,
    require_immutable_artifact,
    minimum_test_coverage,
    minimum_approvals,
    prevent_direct_deployment
)
SELECT
    environment_id,
    TRUE,
    TRUE,
    environment_name = 'PRODUCTION',
    TRUE,
    CASE
        WHEN environment_name = 'PRODUCTION' THEN 80
        ELSE 60
    END,
    CASE
        WHEN environment_name = 'PRODUCTION' THEN 2
        ELSE 0
    END,
    environment_name = 'PRODUCTION'
FROM deployment_environments
ON CONFLICT (environment_id) DO NOTHING;

-- ---------------------------------------------------------
-- 16. Sample pipeline execution
-- ---------------------------------------------------------

INSERT INTO pipeline_runs (
    pipeline_id,
    pull_request_id,
    branch_id,
    commit_sha,
    environment,
    status,
    started_at,
    completed_at,
    triggered_by
)
SELECT
    p.pipeline_id,
    pr.pull_request_id,
    b.branch_id,
    repeat('b', 40),
    'PRODUCTION',
    'SUCCESS',
    NOW() - INTERVAL '10 minutes',
    NOW(),
    u.user_id
FROM pipelines p
JOIN repositories r
    ON r.repository_id = p.repository_id
JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
JOIN branches b
    ON b.branch_name = 'feature/payment-validation'
   AND b.repository_id = r.repository_id
CROSS JOIN users u
WHERE p.pipeline_name = 'payment-ci-cd'
  AND u.username = 'atul'
ON CONFLICT DO NOTHING;

-- Create successful stage executions.
INSERT INTO stage_executions (
    run_id,
    stage_id,
    status,
    attempt_number,
    started_at,
    completed_at,
    output_data
)
SELECT
    run.run_id,
    stage.stage_id,
    'SUCCESS',
    1,
    NOW() - INTERVAL '9 minutes',
    NOW() - INTERVAL '8 minutes',
    jsonb_build_object(
        'result', 'passed',
        'stage', stage.stage_name
    )
FROM pipeline_runs run
JOIN pipelines p ON p.pipeline_id = run.pipeline_id
JOIN pipeline_stages stage ON stage.pipeline_id = p.pipeline_id
WHERE p.pipeline_name = 'payment-ci-cd'
  AND run.status = 'SUCCESS'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 17. Test and security evidence
-- ---------------------------------------------------------

INSERT INTO test_results (
    execution_id,
    test_suite,
    total_tests,
    passed_tests,
    failed_tests,
    skipped_tests,
    coverage_percentage
)
SELECT
    se.execution_id,
    'payment-service-suite',
    120,
    118,
    0,
    2,
    86.50
FROM stage_executions se
JOIN pipeline_stages ps ON ps.stage_id = se.stage_id
WHERE ps.stage_name = 'unit-tests'
ON CONFLICT DO NOTHING;

INSERT INTO security_scan_results (
    execution_id,
    scanner_name,
    critical_count,
    high_count,
    medium_count,
    low_count,
    scan_passed
)
SELECT
    se.execution_id,
    'dependency-and-source-scanner',
    0,
    0,
    2,
    4,
    TRUE
FROM stage_executions se
JOIN pipeline_stages ps ON ps.stage_id = se.stage_id
WHERE ps.stage_name = 'security-scan'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 18. Build artifact
-- ---------------------------------------------------------

INSERT INTO artifacts (
    run_id,
    artifact_name,
    artifact_version,
    sha256,
    size_bytes,
    immutable,
    storage_uri
)
SELECT
    run_id,
    'payment-service',
    '1.4.2',
    encode(digest('payment-service-build-1.4.2', 'sha256'), 'hex'),
    5242880,
    TRUE,
    's3://engineering-artifacts/payment-service/1.4.2'
FROM pipeline_runs
WHERE status = 'SUCCESS'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 19. Deployment approval
-- ---------------------------------------------------------

INSERT INTO deployment_approvals (
    run_id,
    environment_id,
    reviewer_id,
    decision,
    comments
)
SELECT
    run.run_id,
    env.environment_id,
    reviewer.user_id,
    'APPROVED',
    'Production release approved after technical review.'
FROM pipeline_runs run
JOIN deployment_environments env
    ON env.environment_name = 'PRODUCTION'
JOIN repositories r
    ON r.repository_id = env.repository_id
JOIN users reviewer
    ON reviewer.username IN ('reviewer_one', 'security_lead')
WHERE r.repository_name = 'payment-service'
  AND run.status = 'SUCCESS'
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 20. Pipeline retrieval and aggregation
-- ---------------------------------------------------------

SELECT *
FROM pipeline_run_summary
ORDER BY created_at DESC;

SELECT
    p.pipeline_name,
    COUNT(*) AS executions,
    COUNT(*) FILTER (
        WHERE pr.status = 'SUCCESS'
    ) AS successful,
    COUNT(*) FILTER (
        WHERE pr.status = 'FAILED'
    ) AS failed,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE pr.status = 'SUCCESS'
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS success_percentage
FROM pipeline_runs pr
JOIN pipelines p ON p.pipeline_id = pr.pipeline_id
GROUP BY p.pipeline_name;

-- Stage performance and failure analysis.
SELECT
    ps.stage_name,
    COUNT(*) AS execution_count,
    COUNT(*) FILTER (
        WHERE se.status = 'FAILED'
    ) AS failure_count,
    ROUND(
        AVG(
            EXTRACT(EPOCH FROM (
                se.completed_at - se.started_at
            ))
        )::NUMERIC,
        2
    ) AS average_duration_seconds
FROM stage_executions se
JOIN pipeline_stages ps ON ps.stage_id = se.stage_id
GROUP BY ps.stage_name
ORDER BY failure_count DESC;

-- ---------------------------------------------------------
-- 21. CTE-based deployment eligibility reporting
-- ---------------------------------------------------------

WITH production_runs AS (
    SELECT
        pr.run_id,
        pr.status
    FROM pipeline_runs pr
    WHERE pr.environment = 'PRODUCTION'
),
approval_summary AS (
    SELECT
        run_id,
        COUNT(*) FILTER (
            WHERE decision = 'APPROVED'
        ) AS approvals,
        COUNT(*) FILTER (
            WHERE decision = 'REJECTED'
        ) AS rejections
    FROM deployment_approvals
    GROUP BY run_id
)
SELECT
    run.run_id,
    run.status,
    COALESCE(approval.approvals, 0) AS approvals,
    COALESCE(approval.rejections, 0) AS rejections,
    CASE
        WHEN run.status <> 'SUCCESS' THEN 'INELIGIBLE'
        WHEN COALESCE(approval.rejections, 0) > 0 THEN 'INELIGIBLE'
        WHEN COALESCE(approval.approvals, 0) < 2 THEN 'PENDING_APPROVAL'
        ELSE 'APPROVAL_COUNT_MET'
    END AS approval_status
FROM production_runs run
LEFT JOIN approval_summary approval
    ON approval.run_id = run.run_id;

-- ---------------------------------------------------------
-- 22. Direct eligibility evaluation
-- ---------------------------------------------------------

SELECT
    pr.run_id,
    env.environment_name,
    result.eligible,
    result.reason
FROM pipeline_runs pr
JOIN deployment_environments env
    ON env.environment_name = 'PRODUCTION'
CROSS JOIN LATERAL evaluate_deployment(
    pr.run_id,
    env.environment_id
) result
WHERE pr.environment = 'PRODUCTION';

-- ---------------------------------------------------------
-- 23. Transactional deployment processing
-- ---------------------------------------------------------

DO $$
DECLARE
    selected_run UUID;
    selected_artifact UUID;
    selected_environment UUID;
    deployer UUID;
BEGIN
    SELECT run_id INTO selected_run
    FROM pipeline_runs
    WHERE status = 'SUCCESS'
    ORDER BY created_at DESC
    LIMIT 1;

    SELECT artifact_id INTO selected_artifact
    FROM artifacts
    WHERE run_id = selected_run
    ORDER BY created_at DESC
    LIMIT 1;

    SELECT environment_id INTO selected_environment
    FROM deployment_environments
    WHERE environment_name = 'PRODUCTION'
    LIMIT 1;

    SELECT user_id INTO deployer
    FROM users
    WHERE username = 'release_manager';

    IF selected_run IS NOT NULL
       AND selected_artifact IS NOT NULL
       AND selected_environment IS NOT NULL
       AND deployer IS NOT NULL THEN

        CALL process_deployment(
            selected_run,
            selected_artifact,
            selected_environment,
            deployer
        );
    ELSE
        RAISE NOTICE
            'Deployment skipped: required records unavailable.';
    END IF;
END;
$$;

COMMIT;

-- ---------------------------------------------------------
-- 24. Final deployment and audit reporting
-- ---------------------------------------------------------

SELECT *
FROM deployment_audit_summary
ORDER BY deployed_at DESC NULLS LAST;

SELECT
    event_type,
    COUNT(*) AS event_count,
    MAX(created_at) AS last_occurrence
FROM audit_events
GROUP BY event_type
ORDER BY event_count DESC;

SELECT
    d.deployment_id,
    d.version,
    d.status,
    e.environment_name,
    a.sha256,
    a.immutable
FROM deployments d
JOIN artifacts a ON a.artifact_id = d.artifact_id
JOIN deployment_environments e
    ON e.environment_id = d.environment_id
ORDER BY d.created_at DESC;
