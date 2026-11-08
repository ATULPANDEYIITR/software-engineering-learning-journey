/*
 * CONTINUOUS INTEGRATION DATABASE
 * PostgreSQL 14+
 *
 * Models:
 * - Repositories
 * - Branches
 * - Commits
 * - Pipeline configurations
 * - Pipeline executions
 * - CI jobs
 * - Automated checks
 * - Build artifacts
 * - Execution events
 * - Deployment eligibility
 * - CI governance policies
 *
 * Execute this script using a PostgreSQL account
 * authorized to create schemas, functions, and triggers.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS ci;

SET search_path TO ci, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE trigger_type AS ENUM (
    'PUSH',
    'PULL_REQUEST',
    'SCHEDULE',
    'MANUAL'
);

CREATE TYPE pipeline_status AS ENUM (
    'PENDING',
    'RUNNING',
    'SUCCESS',
    'FAILED',
    'CANCELLED'
);

CREATE TYPE job_status AS ENUM (
    'PENDING',
    'RUNNING',
    'SUCCESS',
    'FAILED',
    'SKIPPED'
);

CREATE TYPE check_type AS ENUM (
    'LINT',
    'UNIT_TEST',
    'INTEGRATION_TEST',
    'SECURITY',
    'BUILD',
    'COVERAGE'
);

CREATE TYPE check_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED',
    'WARNING',
    'SKIPPED'
);

-- ============================================================
-- 2. REPOSITORY AND SOURCE CONTROL
-- ============================================================

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    name VARCHAR(150) NOT NULL,

    owner VARCHAR(150) NOT NULL,

    default_branch VARCHAR(150) NOT NULL DEFAULT 'main',

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repository_name_owner
        UNIQUE (owner, name)
);

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    branch_name VARCHAR(150) NOT NULL,

    protected BOOLEAN NOT NULL DEFAULT FALSE,

    is_default BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repository_branch
        UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL,

    branch_id BIGINT NOT NULL,

    commit_hash CHAR(40) NOT NULL,

    author_email VARCHAR(255) NOT NULL,

    commit_message TEXT NOT NULL,

    committed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (repository_id)
        REFERENCES repositories(repository_id),

    FOREIGN KEY (branch_id)
        REFERENCES branches(branch_id),

    CONSTRAINT uq_repository_commit
        UNIQUE (repository_id, commit_hash)
);

CREATE INDEX idx_commits_branch_date
    ON commits(branch_id, committed_at DESC);

-- ============================================================
-- 3. CI CONFIGURATION
-- ============================================================

CREATE TABLE pipeline_configs (
    config_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    config_name VARCHAR(150) NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    trigger_on_push BOOLEAN NOT NULL DEFAULT TRUE,

    trigger_on_pull_request BOOLEAN NOT NULL DEFAULT TRUE,

    trigger_on_schedule BOOLEAN NOT NULL DEFAULT FALSE,

    max_concurrency INTEGER NOT NULL DEFAULT 3,

    timeout_seconds INTEGER NOT NULL DEFAULT 1800,

    fail_fast BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pipeline_config
        UNIQUE (repository_id, config_name),

    CHECK (max_concurrency BETWEEN 1 AND 100),

    CHECK (timeout_seconds BETWEEN 1 AND 86400)
);

CREATE TABLE pipeline_executions (
    pipeline_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    config_id BIGINT NOT NULL
        REFERENCES pipeline_configs(config_id),

    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),

    trigger trigger_type NOT NULL,

    status pipeline_status NOT NULL DEFAULT 'PENDING',

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    initiated_by VARCHAR(255),

    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        completed_at IS NULL OR
        started_at IS NULL OR
        completed_at >= started_at
    )
);

CREATE INDEX idx_pipeline_status_created
    ON pipeline_executions(status, created_at DESC);

CREATE INDEX idx_pipeline_commit
    ON pipeline_executions(commit_id);

-- ============================================================
-- 4. PIPELINE JOBS
-- ============================================================

CREATE TABLE pipeline_jobs (
    job_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_id BIGINT NOT NULL
        REFERENCES pipeline_executions(pipeline_id)
        ON DELETE CASCADE,

    job_name VARCHAR(150) NOT NULL,

    execution_order INTEGER NOT NULL,

    status job_status NOT NULL DEFAULT 'PENDING',

    max_retries INTEGER NOT NULL DEFAULT 0,

    attempts INTEGER NOT NULL DEFAULT 0,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    error_message TEXT,

    CONSTRAINT uq_pipeline_job
        UNIQUE (pipeline_id, job_name),

    CHECK (execution_order >= 0),

    CHECK (max_retries BETWEEN 0 AND 20),

    CHECK (attempts >= 0),

    CHECK (
        completed_at IS NULL OR
        started_at IS NULL OR
        completed_at >= started_at
    )
);

CREATE TABLE job_dependencies (
    job_id BIGINT NOT NULL
        REFERENCES pipeline_jobs(job_id)
        ON DELETE CASCADE,

    depends_on_job_id BIGINT NOT NULL
        REFERENCES pipeline_jobs(job_id)
        ON DELETE CASCADE,

    PRIMARY KEY (job_id, depends_on_job_id),

    CHECK (job_id <> depends_on_job_id)
);

CREATE INDEX idx_jobs_pipeline_status
    ON pipeline_jobs(pipeline_id, status);

CREATE INDEX idx_dependencies_parent
    ON job_dependencies(depends_on_job_id);

-- ============================================================
-- 5. AUTOMATED QUALITY CHECKS
-- ============================================================

CREATE TABLE automated_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    job_id BIGINT NOT NULL
        REFERENCES pipeline_jobs(job_id)
        ON DELETE CASCADE,

    check_name VARCHAR(150) NOT NULL,

    check_category check_type NOT NULL,

    status check_status NOT NULL DEFAULT 'PENDING',

    passed_count INTEGER NOT NULL DEFAULT 0,

    failed_count INTEGER NOT NULL DEFAULT 0,

    warning_count INTEGER NOT NULL DEFAULT 0,

    execution_duration_ms BIGINT,

    details JSONB NOT NULL DEFAULT '{}'::JSONB,

    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_job_check
        UNIQUE (job_id, check_name),

    CHECK (passed_count >= 0),

    CHECK (failed_count >= 0),

    CHECK (warning_count >= 0),

    CHECK (
        execution_duration_ms IS NULL OR
        execution_duration_ms >= 0
    )
);

CREATE INDEX idx_checks_category_status
    ON automated_checks(check_category, status);

CREATE INDEX idx_checks_details
    ON automated_checks USING GIN(details);

-- ============================================================
-- 6. BUILD ARTIFACTS
-- ============================================================

CREATE TABLE build_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_id BIGINT NOT NULL
        REFERENCES pipeline_executions(pipeline_id),

    artifact_name VARCHAR(255) NOT NULL,

    storage_location TEXT NOT NULL,

    sha256 CHAR(64) NOT NULL,

    file_size_bytes BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pipeline_artifact
        UNIQUE (pipeline_id, artifact_name),

    CHECK (sha256 ~ '^[a-f0-9]{64}$'),

    CHECK (file_size_bytes >= 0)
);

CREATE INDEX idx_artifacts_pipeline
    ON build_artifacts(pipeline_id);

-- ============================================================
-- 7. PIPELINE EVENT AUDIT
-- ============================================================

CREATE TABLE pipeline_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_id BIGINT NOT NULL
        REFERENCES pipeline_executions(pipeline_id),

    event_type VARCHAR(100) NOT NULL,

    event_message TEXT NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pipeline_events
    ON pipeline_events(pipeline_id, occurred_at);

-- ============================================================
-- 8. CI GOVERNANCE POLICY
-- ============================================================

CREATE TABLE ci_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    policy_name VARCHAR(150) NOT NULL,

    require_lint BOOLEAN NOT NULL DEFAULT TRUE,

    require_unit_tests BOOLEAN NOT NULL DEFAULT TRUE,

    require_integration_tests BOOLEAN NOT NULL DEFAULT FALSE,

    require_security_scan BOOLEAN NOT NULL DEFAULT TRUE,

    require_build BOOLEAN NOT NULL DEFAULT TRUE,

    minimum_coverage NUMERIC(5,2) NOT NULL DEFAULT 80.00,

    maximum_failed_tests INTEGER NOT NULL DEFAULT 0,

    block_on_warnings BOOLEAN NOT NULL DEFAULT FALSE,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(repository_id, policy_name),

    CHECK (minimum_coverage BETWEEN 0 AND 100),

    CHECK (maximum_failed_tests >= 0)
);

CREATE INDEX idx_active_ci_policies
    ON ci_policies(repository_id)
    WHERE active = TRUE;

-- ============================================================
-- 9. PIPELINE STATUS VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_pipeline_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status = NEW.status THEN
        RETURN NEW;
    END IF;

    IF OLD.status IN ('SUCCESS', 'FAILED', 'CANCELLED') THEN
        RAISE EXCEPTION
            'Terminal pipeline status cannot be changed from %',
            OLD.status;
    END IF;

    IF NEW.status = 'RUNNING' THEN
        IF OLD.status <> 'PENDING' THEN
            RAISE EXCEPTION
                'Only pending pipelines can start.';
        END IF;

        NEW.started_at := COALESCE(NEW.started_at, NOW());
    END IF;

    IF NEW.status IN ('SUCCESS', 'FAILED', 'CANCELLED') THEN
        IF OLD.status <> 'RUNNING' THEN
            RAISE EXCEPTION
                'Pipeline must be running before completion.';
        END IF;

        NEW.completed_at := NOW();
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_pipeline_transition
BEFORE UPDATE OF status
ON pipeline_executions
FOR EACH ROW
EXECUTE FUNCTION validate_pipeline_transition();

-- ============================================================
-- 10. JOB STATUS VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_job_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status = NEW.status THEN
        RETURN NEW;
    END IF;

    IF OLD.status IN ('SUCCESS', 'FAILED', 'SKIPPED') THEN
        RAISE EXCEPTION
            'Terminal job state cannot be modified.';
    END IF;

    IF NEW.status = 'RUNNING' THEN
        IF OLD.status <> 'PENDING' THEN
            RAISE EXCEPTION
                'Only pending jobs can start.';
        END IF;

        NEW.started_at := NOW();
    END IF;

    IF NEW.status IN ('SUCCESS', 'FAILED', 'SKIPPED') THEN
        NEW.completed_at := NOW();
    END IF;

    IF NEW.attempts < OLD.attempts THEN
        RAISE EXCEPTION
            'Job attempt count cannot decrease.';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_job_transition
BEFORE UPDATE OF status
ON pipeline_jobs
FOR EACH ROW
EXECUTE FUNCTION validate_job_transition();

-- ============================================================
-- 11. PIPELINE EXECUTION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION start_pipeline(
    p_pipeline_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_status pipeline_status;
    v_config_enabled BOOLEAN;
BEGIN
    SELECT pe.status, pc.enabled
    INTO v_status, v_config_enabled
    FROM pipeline_executions pe
    JOIN pipeline_configs pc
        ON pc.config_id = pe.config_id
    WHERE pe.pipeline_id = p_pipeline_id
    FOR UPDATE OF pe;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Pipeline % does not exist.',
            p_pipeline_id;
    END IF;

    IF NOT v_config_enabled THEN
        RAISE EXCEPTION
            'Pipeline configuration is disabled.';
    END IF;

    IF v_status <> 'PENDING' THEN
        RAISE EXCEPTION
            'Pipeline must be pending.';
    END IF;

    UPDATE pipeline_executions
    SET status = 'RUNNING'
    WHERE pipeline_id = p_pipeline_id;

    INSERT INTO pipeline_events (
        pipeline_id,
        event_type,
        event_message
    )
    VALUES (
        p_pipeline_id,
        'PIPELINE_STARTED',
        'Pipeline execution started.'
    );
END;
$$;

-- ============================================================
-- 12. JOB ELIGIBILITY FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION is_job_eligible(
    p_job_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_status job_status;
    v_pipeline_status pipeline_status;
    v_dependency_failed BOOLEAN;
    v_dependency_pending BOOLEAN;
BEGIN
    SELECT pj.status, pe.status
    INTO v_status, v_pipeline_status
    FROM pipeline_jobs pj
    JOIN pipeline_executions pe
        ON pe.pipeline_id = pj.pipeline_id
    WHERE pj.job_id = p_job_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Job % does not exist.',
            p_job_id;
    END IF;

    IF v_status <> 'PENDING' OR v_pipeline_status <> 'RUNNING' THEN
        RETURN FALSE;
    END IF;

    SELECT
        COALESCE(
            BOOL_OR(parent.status IN ('FAILED', 'SKIPPED')),
            FALSE
        ),
        COALESCE(
            BOOL_OR(parent.status <> 'SUCCESS'),
            FALSE
        )
    INTO v_dependency_failed, v_dependency_pending
    FROM job_dependencies jd
    JOIN pipeline_jobs parent
        ON parent.job_id = jd.depends_on_job_id
    WHERE jd.job_id = p_job_id;

    RETURN NOT v_dependency_failed
       AND NOT v_dependency_pending;
END;
$$;

-- ============================================================
-- 13. PIPELINE COMPLETION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION complete_pipeline(
    p_pipeline_id BIGINT
)
RETURNS pipeline_status
LANGUAGE plpgsql
AS $$
DECLARE
    v_status pipeline_status;
    v_failed BOOLEAN;
    v_pending BOOLEAN;
BEGIN
    SELECT status
    INTO v_status
    FROM pipeline_executions
    WHERE pipeline_id = p_pipeline_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pipeline does not exist.';
    END IF;

    IF v_status <> 'RUNNING' THEN
        RAISE EXCEPTION
            'Only running pipelines can complete.';
    END IF;

    SELECT
        COALESCE(
            BOOL_OR(status IN ('FAILED', 'SKIPPED')),
            FALSE
        ),
        COALESCE(
            BOOL_OR(status IN ('PENDING', 'RUNNING')),
            FALSE
        )
    INTO v_failed, v_pending
    FROM pipeline_jobs
    WHERE pipeline_id = p_pipeline_id;

    IF v_pending THEN
        RAISE EXCEPTION
            'Pipeline still contains unfinished jobs.';
    END IF;

    UPDATE pipeline_executions
    SET status = CASE
        WHEN v_failed THEN 'FAILED'::pipeline_status
        ELSE 'SUCCESS'::pipeline_status
    END
    WHERE pipeline_id = p_pipeline_id
    RETURNING status INTO v_status;

    INSERT INTO pipeline_events (
        pipeline_id,
        event_type,
        event_message
    )
    VALUES (
        p_pipeline_id,
        'PIPELINE_COMPLETED',
        'Pipeline status: ' || v_status::TEXT
    );

    RETURN v_status;
END;
$$;

-- ============================================================
-- 14. POLICY EVALUATION
-- ============================================================

CREATE OR REPLACE FUNCTION evaluate_ci_policy(
    p_pipeline_id BIGINT,
    p_policy_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_repository_id BIGINT;
    v_policy ci_policies%ROWTYPE;
    v_pipeline pipeline_executions%ROWTYPE;
    v_missing TEXT[] := ARRAY[]::TEXT[];
    v_coverage NUMERIC;
    v_failed_tests INTEGER;
BEGIN
    SELECT *
    INTO v_pipeline
    FROM pipeline_executions
    WHERE pipeline_id = p_pipeline_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pipeline does not exist.';
    END IF;

    SELECT repository_id
    INTO v_repository_id
    FROM pipeline_configs
    WHERE config_id = v_pipeline.config_id;

    SELECT *
    INTO v_policy
    FROM ci_policies
    WHERE policy_id = p_policy_id
      AND repository_id = v_repository_id
      AND active = TRUE;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'No active matching CI policy.';
        RETURN;
    END IF;

    IF v_pipeline.status <> 'SUCCESS' THEN
        RETURN QUERY
        SELECT FALSE, 'Pipeline has not succeeded.';
        RETURN;
    END IF;

    IF v_policy.require_lint AND NOT EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.check_category = 'LINT'
          AND ac.status = 'PASSED'
    ) THEN
        v_missing := array_append(v_missing, 'LINT');
    END IF;

    IF v_policy.require_unit_tests AND NOT EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.check_category = 'UNIT_TEST'
          AND ac.status = 'PASSED'
    ) THEN
        v_missing := array_append(v_missing, 'UNIT_TEST');
    END IF;

    IF v_policy.require_integration_tests AND NOT EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.check_category = 'INTEGRATION_TEST'
          AND ac.status = 'PASSED'
    ) THEN
        v_missing := array_append(v_missing, 'INTEGRATION_TEST');
    END IF;

    IF v_policy.require_security_scan AND NOT EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.check_category = 'SECURITY'
          AND ac.status = 'PASSED'
    ) THEN
        v_missing := array_append(v_missing, 'SECURITY');
    END IF;

    IF v_policy.require_build AND NOT EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.check_category = 'BUILD'
          AND ac.status = 'PASSED'
    ) THEN
        v_missing := array_append(v_missing, 'BUILD');
    END IF;

    SELECT COALESCE(
        MAX((ac.details ->> 'coverage')::NUMERIC),
        0
    )
    INTO v_coverage
    FROM pipeline_jobs pj
    JOIN automated_checks ac
        ON ac.job_id = pj.job_id
    WHERE pj.pipeline_id = p_pipeline_id
      AND ac.check_category = 'COVERAGE'
      AND ac.status = 'PASSED'
      AND ac.details ? 'coverage';

    IF v_coverage < v_policy.minimum_coverage THEN
        v_missing := array_append(
            v_missing,
            'COVERAGE_BELOW_THRESHOLD'
        );
    END IF;

    SELECT COALESCE(SUM(ac.failed_count), 0)
    INTO v_failed_tests
    FROM pipeline_jobs pj
    JOIN automated_checks ac
        ON ac.job_id = pj.job_id
    WHERE pj.pipeline_id = p_pipeline_id
      AND ac.check_category IN (
          'UNIT_TEST',
          'INTEGRATION_TEST'
      );

    IF v_failed_tests > v_policy.maximum_failed_tests THEN
        v_missing := array_append(
            v_missing,
            'FAILED_TEST_THRESHOLD_EXCEEDED'
        );
    END IF;

    IF v_policy.block_on_warnings AND EXISTS (
        SELECT 1
        FROM pipeline_jobs pj
        JOIN automated_checks ac
            ON ac.job_id = pj.job_id
        WHERE pj.pipeline_id = p_pipeline_id
          AND ac.status = 'WARNING'
    ) THEN
        v_missing := array_append(
            v_missing,
            'WARNINGS_PRESENT'
        );
    END IF;

    RETURN QUERY
    SELECT
        cardinality(v_missing) = 0,
        CASE
            WHEN cardinality(v_missing) = 0
                THEN 'All CI governance requirements satisfied.'
            ELSE array_to_string(v_missing, ', ')
        END;
END;
$$;

-- ============================================================
-- 15. REPORTING VIEW
-- ============================================================

CREATE OR REPLACE VIEW pipeline_execution_summary AS
SELECT
    pe.pipeline_id,
    r.owner,
    r.name AS repository_name,
    b.branch_name,
    c.commit_hash,
    pe.trigger,
    pe.status,
    pe.created_at,
    pe.started_at,
    pe.completed_at,

    COUNT(DISTINCT pj.job_id) AS total_jobs,

    COUNT(DISTINCT pj.job_id)
        FILTER (WHERE pj.status = 'SUCCESS')
        AS successful_jobs,

    COUNT(DISTINCT pj.job_id)
        FILTER (WHERE pj.status = 'FAILED')
        AS failed_jobs,

    COUNT(DISTINCT pj.job_id)
        FILTER (WHERE pj.status = 'SKIPPED')
        AS skipped_jobs,

    COUNT(DISTINCT ba.artifact_id) AS artifact_count

FROM pipeline_executions pe

JOIN pipeline_configs pc
    ON pc.config_id = pe.config_id

JOIN repositories r
    ON r.repository_id = pc.repository_id

JOIN commits c
    ON c.commit_id = pe.commit_id

JOIN branches b
    ON b.branch_id = c.branch_id

LEFT JOIN pipeline_jobs pj
    ON pj.pipeline_id = pe.pipeline_id

LEFT JOIN build_artifacts ba
    ON ba.pipeline_id = pe.pipeline_id

GROUP BY
    pe.pipeline_id,
    r.owner,
    r.name,
    b.branch_name,
    c.commit_hash,
    pe.trigger,
    pe.status,
    pe.created_at,
    pe.started_at,
    pe.completed_at;

-- ============================================================
-- 16. SAMPLE REPOSITORIES
-- ============================================================

INSERT INTO repositories (
    name,
    owner,
    default_branch
)
VALUES
    ('payment-service', 'engineering', 'main'),
    ('analytics-service', 'engineering', 'main');

INSERT INTO branches (
    repository_id,
    branch_name,
    protected,
    is_default
)
SELECT
    repository_id,
    'main',
    TRUE,
    TRUE
FROM repositories
WHERE name = 'payment-service';

INSERT INTO branches (
    repository_id,
    branch_name,
    protected,
    is_default
)
SELECT
    repository_id,
    'feature/payment',
    FALSE,
    FALSE
FROM repositories
WHERE name = 'payment-service';

INSERT INTO branches (
    repository_id,
    branch_name,
    protected,
    is_default
)
SELECT
    repository_id,
    'main',
    TRUE,
    TRUE
FROM repositories
WHERE name = 'analytics-service';

-- ============================================================
-- 17. SAMPLE COMMITS
-- ============================================================

INSERT INTO commits (
    repository_id,
    branch_id,
    commit_hash,
    author_email,
    commit_message
)
SELECT
    r.repository_id,
    b.branch_id,
    repeat('a', 40),
    'developer@example.com',
    'Implement payment validation'
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
WHERE r.name = 'payment-service'
  AND b.branch_name = 'feature/payment';

INSERT INTO commits (
    repository_id,
    branch_id,
    commit_hash,
    author_email,
    commit_message
)
SELECT
    r.repository_id,
    b.branch_id,
    repeat('b', 40),
    'developer@example.com',
    'Update analytics processing'
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
WHERE r.name = 'analytics-service'
  AND b.branch_name = 'main';

-- ============================================================
-- 18. SAMPLE PIPELINE CONFIGURATIONS
-- ============================================================

INSERT INTO pipeline_configs (
    repository_id,
    config_name,
    max_concurrency,
    timeout_seconds,
    fail_fast
)
SELECT
    repository_id,
    'standard-ci',
    3,
    1800,
    TRUE
FROM repositories
WHERE name = 'payment-service';

INSERT INTO pipeline_configs (
    repository_id,
    config_name,
    max_concurrency,
    timeout_seconds
)
SELECT
    repository_id,
    'analytics-ci',
    2,
    2400
FROM repositories
WHERE name = 'analytics-service';

-- ============================================================
-- 19. SAMPLE GOVERNANCE POLICIES
-- ============================================================

INSERT INTO ci_policies (
    repository_id,
    policy_name,
    require_lint,
    require_unit_tests,
    require_integration_tests,
    require_security_scan,
    require_build,
    minimum_coverage,
    maximum_failed_tests
)
SELECT
    repository_id,
    'production-quality-gate',
    TRUE,
    TRUE,
    FALSE,
    TRUE,
    TRUE,
    80.00,
    0
FROM repositories
WHERE name = 'payment-service';

-- ============================================================
-- 20. CREATE PIPELINE EXECUTION
-- ============================================================

INSERT INTO pipeline_executions (
    config_id,
    commit_id,
    trigger,
    status,
    initiated_by
)
SELECT
    pc.config_id,
    c.commit_id,
    'PULL_REQUEST',
    'PENDING',
    'developer@example.com'
FROM pipeline_configs pc
JOIN commits c
    ON c.repository_id = pc.repository_id
WHERE pc.config_name = 'standard-ci'
  AND c.commit_hash = repeat('a', 40);

-- ============================================================
-- 21. CREATE PIPELINE JOBS
-- ============================================================

INSERT INTO pipeline_jobs (
    pipeline_id,
    job_name,
    execution_order,
    max_retries
)
SELECT
    pipeline_id,
    job_name,
    execution_order,
    max_retries
FROM pipeline_executions
CROSS JOIN (
    VALUES
        ('lint', 1, 0),
        ('unit-tests', 2, 0),
        ('security', 3, 1),
        ('build', 4, 1)
) AS jobs(job_name, execution_order, max_retries)
WHERE pipeline_id = (
    SELECT MAX(pipeline_id)
    FROM pipeline_executions
);

-- ============================================================
-- 22. CREATE DEPENDENCIES
-- ============================================================

INSERT INTO job_dependencies (
    job_id,
    depends_on_job_id
)
SELECT
    child.job_id,
    parent.job_id
FROM pipeline_jobs child
JOIN pipeline_jobs parent
    ON parent.pipeline_id = child.pipeline_id
WHERE
    (child.job_name = 'unit-tests'
        AND parent.job_name = 'lint')
    OR
    (child.job_name = 'security'
        AND parent.job_name = 'lint')
    OR
    (child.job_name = 'build'
        AND parent.job_name IN ('unit-tests', 'security'));

-- ============================================================
-- 23. START PIPELINE
-- ============================================================

SELECT start_pipeline(
    (SELECT MAX(pipeline_id) FROM pipeline_executions)
);

-- ============================================================
-- 24. SIMULATE JOB EXECUTION
-- ============================================================

UPDATE pipeline_jobs
SET
    status = 'RUNNING',
    attempts = 1
WHERE job_name = 'lint'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

INSERT INTO automated_checks (
    job_id,
    check_name,
    check_category,
    status,
    passed_count,
    failed_count,
    execution_duration_ms
)
SELECT
    job_id,
    'source-lint',
    'LINT',
    'PASSED',
    25,
    0,
    150
FROM pipeline_jobs
WHERE job_name = 'lint'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

UPDATE pipeline_jobs
SET status = 'SUCCESS'
WHERE job_name = 'lint'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

-- Unit tests

UPDATE pipeline_jobs
SET
    status = 'RUNNING',
    attempts = 1
WHERE job_name = 'unit-tests'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

INSERT INTO automated_checks (
    job_id,
    check_name,
    check_category,
    status,
    passed_count,
    failed_count,
    execution_duration_ms
)
SELECT
    job_id,
    'unit-test-suite',
    'UNIT_TEST',
    'PASSED',
    120,
    0,
    2300
FROM pipeline_jobs
WHERE job_name = 'unit-tests'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

UPDATE pipeline_jobs
SET status = 'SUCCESS'
WHERE job_name = 'unit-tests'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

-- Security scan

UPDATE pipeline_jobs
SET
    status = 'RUNNING',
    attempts = 1
WHERE job_name = 'security'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

INSERT INTO automated_checks (
    job_id,
    check_name,
    check_category,
    status,
    passed_count,
    failed_count,
    execution_duration_ms,
    details
)
SELECT
    job_id,
    'dependency-security-scan',
    'SECURITY',
    'PASSED',
    42,
    0,
    1800,
    '{"critical": 0, "high": 0, "medium": 2}'::JSONB
FROM pipeline_jobs
WHERE job_name = 'security'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

UPDATE pipeline_jobs
SET status = 'SUCCESS'
WHERE job_name = 'security'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

-- Build

UPDATE pipeline_jobs
SET
    status = 'RUNNING',
    attempts = 1
WHERE job_name = 'build'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

INSERT INTO automated_checks (
    job_id,
    check_name,
    check_category,
    status,
    passed_count,
    failed_count,
    execution_duration_ms
)
SELECT
    job_id,
    'application-build',
    'BUILD',
    'PASSED',
    1,
    0,
    3200
FROM pipeline_jobs
WHERE job_name = 'build'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

UPDATE pipeline_jobs
SET status = 'SUCCESS'
WHERE job_name = 'build'
  AND pipeline_id = (
      SELECT MAX(pipeline_id)
      FROM pipeline_executions
  );

-- ============================================================
-- 25. REGISTER BUILD ARTIFACT
-- ============================================================

INSERT INTO build_artifacts (
    pipeline_id,
    artifact_name,
    storage_location,
    sha256,
    file_size_bytes
)
SELECT
    pipeline_id,
    'payment-service-1.0.0.zip',
    'artifact-store/payment-service-1.0.0.zip',
    repeat('c', 64),
    204800
FROM pipeline_executions
WHERE pipeline_id = (
    SELECT MAX(pipeline_id)
    FROM pipeline_executions
);

-- ============================================================
-- 26. COMPLETE PIPELINE
-- ============================================================

SELECT complete_pipeline(
    (SELECT MAX(pipeline_id) FROM pipeline_executions)
);

-- ============================================================
-- 27. POLICY EVALUATION
-- ============================================================

SELECT *
FROM evaluate_ci_policy(
    (SELECT MAX(pipeline_id) FROM pipeline_executions),
    (
        SELECT policy_id
        FROM ci_policies
        WHERE policy_name = 'production-quality-gate'
    )
);

-- ============================================================
-- 28. RETRIEVAL AND REPORTING
-- ============================================================

-- Pipeline execution history.
SELECT *
FROM pipeline_execution_summary
ORDER BY created_at DESC;

-- Individual jobs and their states.
SELECT
    pj.pipeline_id,
    pj.job_name,
    pj.status,
    pj.attempts,
    pj.error_message
FROM pipeline_jobs pj
ORDER BY pj.pipeline_id, pj.execution_order;

-- Automated check results.
SELECT
    pj.job_name,
    ac.check_name,
    ac.check_category,
    ac.status,
    ac.passed_count,
    ac.failed_count,
    ac.execution_duration_ms
FROM automated_checks ac
JOIN pipeline_jobs pj
    ON pj.job_id = ac.job_id
ORDER BY pj.execution_order;

-- Aggregated check statistics.
SELECT
    ac.check_category,
    COUNT(*) AS total_checks,
    COUNT(*) FILTER (
        WHERE ac.status = 'PASSED'
    ) AS passed_checks,
    COUNT(*) FILTER (
        WHERE ac.status = 'FAILED'
    ) AS failed_checks,
    ROUND(
        AVG(ac.execution_duration_ms),
        2
    ) AS average_duration_ms
FROM automated_checks ac
GROUP BY ac.check_category
ORDER BY ac.check_category;

-- Failed pipeline investigation.
SELECT
    pe.pipeline_id,
    pe.failure_reason,
    pj.job_name,
    pj.error_message
FROM pipeline_executions pe
JOIN pipeline_jobs pj
    ON pj.pipeline_id = pe.pipeline_id
WHERE pe.status = 'FAILED';

-- Artifact inventory.
SELECT
    pe.pipeline_id,
    ba.artifact_name,
    ba.storage_location,
    ba.sha256,
    ba.file_size_bytes
FROM build_artifacts ba
JOIN pipeline_executions pe
    ON pe.pipeline_id = ba.pipeline_id;

-- Event audit history.
SELECT
    pipeline_id,
    event_type,
    event_message,
    occurred_at
FROM pipeline_events
ORDER BY occurred_at;

-- ============================================================
-- 29. VALIDATION QUERIES
-- ============================================================

-- Detect jobs with unresolved dependencies.
SELECT
    child.job_name,
    parent.job_name AS dependency,
    parent.status AS dependency_status
FROM job_dependencies jd
JOIN pipeline_jobs child
    ON child.job_id = jd.job_id
JOIN pipeline_jobs parent
    ON parent.job_id = jd.depends_on_job_id
WHERE child.status = 'RUNNING'
  AND parent.status <> 'SUCCESS';

-- Detect pipelines marked successful with failed jobs.
SELECT pe.pipeline_id
FROM pipeline_executions pe
WHERE pe.status = 'SUCCESS'
  AND EXISTS (
      SELECT 1
      FROM pipeline_jobs pj
      WHERE pj.pipeline_id = pe.pipeline_id
        AND pj.status <> 'SUCCESS'
  );

-- Identify incomplete artifact records.
SELECT
    pipeline_id,
    artifact_name
FROM build_artifacts
WHERE storage_location IS NULL
   OR sha256 IS NULL;

-- ============================================================
-- 30. TRANSACTIONAL WORKFLOW EXAMPLE
-- ============================================================

-- A new pipeline can be registered atomically.
-- If any operation fails, PostgreSQL rolls back the transaction.

COMMIT;
