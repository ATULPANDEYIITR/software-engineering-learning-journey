/*
 * CONTINUOUS DELIVERY MANAGEMENT DATABASE
 *
 * PostgreSQL 15+
 *
 * Workflow:
 * Repository
 *   -> Branches
 *   -> Commits
 *   -> Pipeline Runs
 *   -> Build / Test / Security / Package
 *   -> Artifacts
 *   -> Approval
 *   -> Release
 *   -> Deployment
 *
 * Features:
 * - Relational pipeline management
 * - Stage execution tracking
 * - Artifact integrity
 * - Release approvals
 * - Environment policies
 * - Status-check enforcement
 * - Deployment history
 * - Audit logging
 * - Transaction-safe release processing
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS continuous_delivery;

SET search_path TO continuous_delivery, public;


/* ============================================================
   1. DOMAIN TYPES
   ============================================================ */

CREATE TYPE pipeline_status AS ENUM (
    'created',
    'running',
    'succeeded',
    'failed',
    'released',
    'cancelled'
);

CREATE TYPE stage_status AS ENUM (
    'pending',
    'running',
    'passed',
    'failed',
    'skipped'
);

CREATE TYPE stage_type AS ENUM (
    'build',
    'test',
    'security_scan',
    'package',
    'release'
);

CREATE TYPE deployment_environment AS ENUM (
    'development',
    'staging',
    'production'
);

CREATE TYPE approval_decision AS ENUM (
    'approved',
    'rejected',
    'dismissed'
);

CREATE TYPE merge_strategy AS ENUM (
    'merge_commit',
    'squash',
    'rebase'
);


/* ============================================================
   2. REPOSITORY AND SOURCE CONTROL
   ============================================================ */

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name VARCHAR(150) NOT NULL,
    owner_name VARCHAR(120) NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repository
        UNIQUE (owner_name, repository_name)
);


CREATE TABLE developers (
    developer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    branch_name VARCHAR(150) NOT NULL,
    head_commit_hash CHAR(40),

    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    allow_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_deletion BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repository_branch
        UNIQUE(repository_id, branch_name),

    CONSTRAINT ck_branch_protection
        CHECK (
            NOT is_protected OR
            (
                NOT allow_direct_push
                AND NOT allow_force_push
                AND NOT allow_deletion
            )
        )
);


CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    commit_hash CHAR(40) NOT NULL,
    developer_id BIGINT REFERENCES developers(developer_id),

    commit_message TEXT NOT NULL,
    parent_commit_hash CHAR(40),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_repository_commit
        UNIQUE(repository_id, commit_hash),

    CONSTRAINT ck_commit_message
        CHECK (LENGTH(TRIM(commit_message)) > 0)
);


ALTER TABLE branches
ADD CONSTRAINT fk_branch_head_commit
FOREIGN KEY (repository_id, head_commit_hash)
REFERENCES commits(repository_id, commit_hash)
DEFERRABLE INITIALLY DEFERRED;


/* ============================================================
   3. PULL REQUESTS AND REVIEW MANAGEMENT
   ============================================================ */

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    source_commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),

    target_commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),

    title VARCHAR(250) NOT NULL,

    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    has_merge_conflict BOOLEAN NOT NULL DEFAULT FALSE,

    conversations_resolved BOOLEAN NOT NULL DEFAULT FALSE,

    strategy merge_strategy NOT NULL DEFAULT 'squash',

    created_by BIGINT NOT NULL
        REFERENCES developers(developer_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,

    CONSTRAINT ck_pr_branches
        CHECK (source_branch_id <> target_branch_id),

    CONSTRAINT ck_pr_title
        CHECK (LENGTH(TRIM(title)) > 0)
);


CREATE TABLE reviewers (
    reviewer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    developer_id BIGINT NOT NULL UNIQUE
        REFERENCES developers(developer_id),

    is_eligible BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    expertise_area VARCHAR(150)
);


CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),

    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),

    decision approval_decision NOT NULL,

    is_stale BOOLEAN NOT NULL DEFAULT FALSE,

    review_commit_hash CHAR(40) NOT NULL,

    review_summary TEXT,

    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_reviewer_review
        UNIQUE(pull_request_id, reviewer_id, review_commit_hash)
);


CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id),

    file_path VARCHAR(500) NOT NULL,

    line_number INTEGER NOT NULL,

    comment_body TEXT NOT NULL,

    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,

    parent_comment_id BIGINT
        REFERENCES review_comments(comment_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_comment_line
        CHECK (line_number > 0),

    CONSTRAINT ck_comment_body
        CHECK (LENGTH(TRIM(comment_body)) > 0)
);


/* ============================================================
   4. DELIVERY PIPELINES
   ============================================================ */

CREATE TABLE pipelines (
    pipeline_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    pipeline_name VARCHAR(150) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    timeout_seconds INTEGER NOT NULL DEFAULT 1800,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pipeline_name
        UNIQUE(repository_id, pipeline_name),

    CONSTRAINT ck_pipeline_timeout
        CHECK (timeout_seconds BETWEEN 1 AND 86400)
);


CREATE TABLE pipeline_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    pipeline_id BIGINT NOT NULL
        REFERENCES pipelines(pipeline_id),

    pull_request_id BIGINT
        REFERENCES pull_requests(pull_request_id),

    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),

    run_number INTEGER NOT NULL,

    status pipeline_status NOT NULL DEFAULT 'created',

    environment deployment_environment NOT NULL DEFAULT 'staging',

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    triggered_by BIGINT
        REFERENCES developers(developer_id),

    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_pipeline_run_number
        UNIQUE(pipeline_id, run_number),

    CONSTRAINT ck_run_number
        CHECK (run_number > 0),

    CONSTRAINT ck_run_timestamps
        CHECK (
            completed_at IS NULL OR
            started_at IS NULL OR
            completed_at >= started_at
        )
);


CREATE TABLE pipeline_stages (
    stage_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(run_id),

    stage_name stage_type NOT NULL,

    execution_order INTEGER NOT NULL,

    status stage_status NOT NULL DEFAULT 'pending',

    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    duration_ms BIGINT,

    log_location TEXT,

    failure_message TEXT,

    CONSTRAINT uq_run_stage
        UNIQUE(run_id, stage_name),

    CONSTRAINT uq_run_stage_order
        UNIQUE(run_id, execution_order),

    CONSTRAINT ck_stage_order
        CHECK (execution_order > 0),

    CONSTRAINT ck_stage_duration
        CHECK (duration_ms IS NULL OR duration_ms >= 0)
);


/* ============================================================
   5. AUTOMATED STATUS CHECKS
   ============================================================ */

CREATE TABLE status_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(run_id),

    check_name VARCHAR(120) NOT NULL,

    status stage_status NOT NULL DEFAULT 'pending',

    details TEXT,

    execution_time_ms BIGINT,

    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_run_check
        UNIQUE(run_id, check_name),

    CONSTRAINT ck_check_duration
        CHECK (
            execution_time_ms IS NULL OR
            execution_time_ms >= 0
        )
);


/* ============================================================
   6. ARTIFACT REGISTRY
   ============================================================ */

CREATE TABLE artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(run_id),

    artifact_name VARCHAR(250) NOT NULL,

    version VARCHAR(100) NOT NULL,

    storage_location TEXT NOT NULL,

    sha256 CHAR(64) NOT NULL,

    size_bytes BIGINT NOT NULL,

    is_verified BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_artifact_version
        UNIQUE(artifact_name, version),

    CONSTRAINT ck_artifact_checksum
        CHECK (sha256 ~ '^[a-fA-F0-9]{64}$'),

    CONSTRAINT ck_artifact_size
        CHECK (size_bytes > 0)
);


/* ============================================================
   7. RELEASE POLICIES AND APPROVALS
   ============================================================ */

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    required_reviews INTEGER NOT NULL DEFAULT 1,

    require_build BOOLEAN NOT NULL DEFAULT TRUE,
    require_tests BOOLEAN NOT NULL DEFAULT TRUE,
    require_security_scan BOOLEAN NOT NULL DEFAULT TRUE,

    require_resolved_conversations BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT TRUE,

    prohibit_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    prohibit_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    prohibit_branch_deletion BOOLEAN NOT NULL DEFAULT TRUE,

    administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_branch_policy
        UNIQUE(branch_id),

    CONSTRAINT ck_required_reviews
        CHECK (required_reviews BETWEEN 0 AND 20)
);


CREATE TABLE release_approvals (
    approval_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(run_id),

    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),

    decision approval_decision NOT NULL,

    approved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    comments TEXT,

    CONSTRAINT uq_run_release_reviewer
        UNIQUE(run_id, reviewer_id)
);


/* ============================================================
   8. DEPLOYMENT MANAGEMENT
   ============================================================ */

CREATE TABLE deployments (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES pipeline_runs(run_id),

    artifact_id BIGINT NOT NULL
        REFERENCES artifacts(artifact_id),

    environment deployment_environment NOT NULL,

    deployment_version VARCHAR(100) NOT NULL,

    deployed_by BIGINT NOT NULL
        REFERENCES developers(developer_id),

    is_successful BOOLEAN NOT NULL DEFAULT FALSE,

    deployed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    rollback_of BIGINT
        REFERENCES deployments(deployment_id),

    CONSTRAINT uq_run_environment
        UNIQUE(run_id, environment)
);


/* ============================================================
   9. AUDIT LOG
   ============================================================ */

CREATE TABLE audit_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT REFERENCES pipeline_runs(run_id),

    actor VARCHAR(150) NOT NULL,

    event_type VARCHAR(120) NOT NULL,

    event_details JSONB NOT NULL DEFAULT '{}'::JSONB,

    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


/* ============================================================
   10. PERFORMANCE INDEXES
   ============================================================ */

CREATE INDEX idx_runs_pipeline_status
ON pipeline_runs(pipeline_id, status, created_at DESC);

CREATE INDEX idx_runs_commit
ON pipeline_runs(commit_id);

CREATE INDEX idx_runs_environment
ON pipeline_runs(environment, status);

CREATE INDEX idx_stages_run_status
ON pipeline_stages(run_id, status);

CREATE INDEX idx_checks_run_status
ON status_checks(run_id, status);

CREATE INDEX idx_reviews_pr
ON reviews(pull_request_id, decision);

CREATE INDEX idx_comments_unresolved
ON review_comments(review_id)
WHERE is_resolved = FALSE;

CREATE INDEX idx_artifacts_run
ON artifacts(run_id);

CREATE INDEX idx_approvals_run_decision
ON release_approvals(run_id, decision);

CREATE INDEX idx_deployments_environment
ON deployments(environment, deployed_at DESC);

CREATE INDEX idx_audit_run_timestamp
ON audit_events(run_id, event_timestamp DESC);


/* ============================================================
   11. STAGE VALIDATION TRIGGER
   ============================================================ */

CREATE OR REPLACE FUNCTION validate_stage_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN

        IF OLD.status IN ('passed', 'failed', 'skipped')
           AND NEW.status <> OLD.status THEN

            RAISE EXCEPTION
                'Terminal stage status cannot be changed directly';
        END IF;

        IF OLD.status = 'pending'
           AND NEW.status NOT IN ('pending', 'running', 'skipped') THEN

            RAISE EXCEPTION
                'Pending stage must enter running state first';
        END IF;

        IF OLD.status = 'running'
           AND NEW.status NOT IN ('running', 'passed', 'failed') THEN

            RAISE EXCEPTION
                'Invalid running stage transition';
        END IF;

    END IF;

    IF NEW.status = 'running' AND NEW.started_at IS NULL THEN
        NEW.started_at := NOW();
    END IF;

    IF NEW.status IN ('passed', 'failed', 'skipped') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, NOW());

        IF NEW.started_at IS NOT NULL THEN
            NEW.duration_ms :=
                GREATEST(
                    0,
                    (EXTRACT(EPOCH FROM (
                        NEW.completed_at - NEW.started_at
                    )) * 1000)::BIGINT
                );
        END IF;
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_validate_stage_transition
BEFORE UPDATE ON pipeline_stages
FOR EACH ROW
EXECUTE FUNCTION validate_stage_transition();


/* ============================================================
   12. PIPELINE RUN STATE VALIDATION
   ============================================================ */

CREATE OR REPLACE FUNCTION validate_pipeline_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('released', 'failed', 'cancelled') THEN
        RAISE EXCEPTION
            'Terminal pipeline state cannot be changed';
    END IF;

    IF OLD.status = 'created'
       AND NEW.status NOT IN ('created', 'running', 'cancelled') THEN

        RAISE EXCEPTION 'Invalid pipeline transition';
    END IF;

    IF OLD.status = 'running'
       AND NEW.status NOT IN (
           'running',
           'succeeded',
           'failed',
           'cancelled'
       ) THEN

        RAISE EXCEPTION 'Invalid pipeline transition';
    END IF;

    IF OLD.status = 'succeeded'
       AND NEW.status NOT IN ('succeeded', 'released', 'failed') THEN

        RAISE EXCEPTION 'Invalid release transition';
    END IF;

    IF NEW.status = 'running' AND NEW.started_at IS NULL THEN
        NEW.started_at := NOW();
    END IF;

    IF NEW.status IN ('succeeded', 'failed', 'released', 'cancelled') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, NOW());
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_pipeline_transition
BEFORE UPDATE OF status ON pipeline_runs
FOR EACH ROW
WHEN (OLD.status IS DISTINCT FROM NEW.status)
EXECUTE FUNCTION validate_pipeline_transition();


/* ============================================================
   13. RELEASE ELIGIBILITY FUNCTION
   ============================================================ */

CREATE OR REPLACE FUNCTION evaluate_release_eligibility(
    p_run_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_run pipeline_runs%ROWTYPE;
    v_artifact artifacts%ROWTYPE;
    v_required_reviews INTEGER := 0;
    v_approval_count INTEGER := 0;
    v_build_required BOOLEAN := FALSE;
    v_tests_required BOOLEAN := FALSE;
    v_security_required BOOLEAN := FALSE;
BEGIN
    SELECT *
    INTO v_run
    FROM pipeline_runs
    WHERE run_id = p_run_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Pipeline run does not exist';
        RETURN;
    END IF;

    IF v_run.status <> 'succeeded' THEN
        RETURN QUERY
        SELECT FALSE, 'Pipeline has not succeeded';
        RETURN;
    END IF;

    SELECT *
    INTO v_artifact
    FROM artifacts
    WHERE run_id = p_run_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Release artifact is missing';
        RETURN;
    END IF;

    IF NOT v_artifact.is_verified THEN
        RETURN QUERY
        SELECT FALSE, 'Artifact integrity is not verified';
        RETURN;
    END IF;

    SELECT
        COALESCE(MAX(bp.required_reviews), 0),
        COALESCE(BOOL_OR(bp.require_build), FALSE),
        COALESCE(BOOL_OR(bp.require_tests), FALSE),
        COALESCE(BOOL_OR(bp.require_security_scan), FALSE)
    INTO
        v_required_reviews,
        v_build_required,
        v_tests_required,
        v_security_required
    FROM pipeline_runs pr
    LEFT JOIN pull_requests p
        ON p.pull_request_id = pr.pull_request_id
    LEFT JOIN branch_protection_policies bp
        ON bp.branch_id = p.target_branch_id
    WHERE pr.run_id = p_run_id;

    SELECT COUNT(DISTINCT ra.reviewer_id)
    INTO v_approval_count
    FROM release_approvals ra
    JOIN reviewers r
        ON r.reviewer_id = ra.reviewer_id
    JOIN developers d
        ON d.developer_id = r.developer_id
    WHERE ra.run_id = p_run_id
      AND ra.decision = 'approved'
      AND r.is_eligible
      AND r.is_active
      AND d.is_active;

    IF v_approval_count < v_required_reviews THEN
        RETURN QUERY
        SELECT FALSE, 'Required release approvals are missing';
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM release_approvals
        WHERE run_id = p_run_id
          AND decision = 'rejected'
    ) THEN
        RETURN QUERY
        SELECT FALSE, 'Release has a rejection decision';
        RETURN;
    END IF;

    IF v_build_required AND NOT EXISTS (
        SELECT 1
        FROM status_checks
        WHERE run_id = p_run_id
          AND check_name = 'build'
          AND status = 'passed'
    ) THEN
        RETURN QUERY
        SELECT FALSE, 'Build check is missing or unsuccessful';
        RETURN;
    END IF;

    IF v_tests_required AND NOT EXISTS (
        SELECT 1
        FROM status_checks
        WHERE run_id = p_run_id
          AND check_name = 'tests'
          AND status = 'passed'
    ) THEN
        RETURN QUERY
        SELECT FALSE, 'Test check is missing or unsuccessful';
        RETURN;
    END IF;

    IF v_security_required AND NOT EXISTS (
        SELECT 1
        FROM status_checks
        WHERE run_id = p_run_id
          AND check_name = 'security-scan'
          AND status = 'passed'
    ) THEN
        RETURN QUERY
        SELECT FALSE, 'Security check is missing or unsuccessful';
        RETURN;
    END IF;

    RETURN QUERY
    SELECT TRUE, 'All release eligibility conditions satisfied';
END;
$$;


/* ============================================================
   14. TRANSACTION-SAFE RELEASE PROCEDURE
   ============================================================ */

CREATE OR REPLACE PROCEDURE promote_release(
    p_run_id BIGINT,
    p_environment deployment_environment,
    p_deployed_by BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_eligible BOOLEAN;
    v_reason TEXT;
    v_artifact_id BIGINT;
    v_version VARCHAR(100);
    v_status pipeline_status;
BEGIN
    /*
     * Lock the run so simultaneous release requests cannot
     * independently pass eligibility and publish the same run.
     */
    SELECT status
    INTO v_status
    FROM pipeline_runs
    WHERE run_id = p_run_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pipeline run not found';
    END IF;

    IF v_status <> 'succeeded' THEN
        RAISE EXCEPTION 'Pipeline is not ready for release';
    END IF;

    SELECT e.eligible, e.reason
    INTO v_eligible, v_reason
    FROM evaluate_release_eligibility(p_run_id) e;

    IF NOT v_eligible THEN
        RAISE EXCEPTION 'Release blocked: %', v_reason;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM developers
        WHERE developer_id = p_deployed_by
          AND is_active
    ) THEN
        RAISE EXCEPTION 'Invalid deployment operator';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM deployments
        WHERE run_id = p_run_id
          AND environment = p_environment
    ) THEN
        RAISE EXCEPTION 'Run already deployed to this environment';
    END IF;

    SELECT artifact_id, version
    INTO v_artifact_id, v_version
    FROM artifacts
    WHERE run_id = p_run_id
      AND is_verified;

    INSERT INTO deployments (
        run_id,
        artifact_id,
        environment,
        deployment_version,
        deployed_by,
        is_successful
    )
    VALUES (
        p_run_id,
        v_artifact_id,
        p_environment,
        v_version,
        p_deployed_by,
        TRUE
    );

    UPDATE pipeline_runs
    SET status = 'released'
    WHERE run_id = p_run_id;

    INSERT INTO audit_events (
        run_id,
        actor,
        event_type,
        event_details
    )
    VALUES (
        p_run_id,
        'release-service',
        'RELEASE_PUBLISHED',
        jsonb_build_object(
            'environment', p_environment,
            'version', v_version
        )
    );

END;
$$;


/* ============================================================
   15. REPORTING VIEW
   ============================================================ */

CREATE OR REPLACE VIEW delivery_run_report AS
SELECT
    pr.run_id,
    repo.repository_name,
    p.pipeline_name,
    c.commit_hash,
    pr.run_number,
    pr.status,
    pr.environment,

    COUNT(DISTINCT ps.stage_id) AS total_stages,

    COUNT(DISTINCT ps.stage_id)
        FILTER (WHERE ps.status = 'passed') AS passed_stages,

    COUNT(DISTINCT ps.stage_id)
        FILTER (WHERE ps.status = 'failed') AS failed_stages,

    COUNT(DISTINCT sc.check_id)
        FILTER (WHERE sc.status = 'passed') AS passed_checks,

    COUNT(DISTINCT a.artifact_id) AS artifact_count,

    pr.started_at,
    pr.completed_at,
    pr.failure_reason

FROM pipeline_runs pr

JOIN pipelines p
    ON p.pipeline_id = pr.pipeline_id

JOIN repositories repo
    ON repo.repository_id = p.repository_id

JOIN commits c
    ON c.commit_id = pr.commit_id

LEFT JOIN pipeline_stages ps
    ON ps.run_id = pr.run_id

LEFT JOIN status_checks sc
    ON sc.run_id = pr.run_id

LEFT JOIN artifacts a
    ON a.run_id = pr.run_id

GROUP BY
    pr.run_id,
    repo.repository_name,
    p.pipeline_name,
    c.commit_hash,
    pr.run_number,
    pr.status,
    pr.environment,
    pr.started_at,
    pr.completed_at,
    pr.failure_reason;


/* ============================================================
   16. SAMPLE DATA
   ============================================================ */

INSERT INTO repositories (
    repository_name,
    owner_name,
    default_branch
)
VALUES
    ('payment-platform', 'enterprise', 'main'),
    ('inventory-platform', 'enterprise', 'main');


INSERT INTO developers (
    username,
    email
)
VALUES
    ('developer_a', 'developer_a@example.com'),
    ('developer_b', 'developer_b@example.com'),
    ('reviewer_a', 'reviewer_a@example.com'),
    ('reviewer_b', 'reviewer_b@example.com'),
    ('release_operator', 'release@example.com');


INSERT INTO reviewers (
    developer_id,
    is_eligible,
    expertise_area
)
SELECT developer_id, TRUE, 'Software Engineering'
FROM developers
WHERE username IN ('reviewer_a', 'reviewer_b');


INSERT INTO commits (
    repository_id,
    commit_hash,
    developer_id,
    commit_message
)
SELECT
    r.repository_id,
    data.commit_hash,
    d.developer_id,
    data.commit_message
FROM repositories r
CROSS JOIN (
    VALUES
        ('1111111111111111111111111111111111111111',
         'Initial application'),
        ('2222222222222222222222222222222222222222',
         'Implement payment validation')
) AS data(commit_hash, commit_message)
JOIN developers d
    ON d.username = 'developer_a'
WHERE r.repository_name = 'payment-platform';


INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected,
    allow_direct_push,
    allow_force_push,
    allow_deletion
)
SELECT
    repository_id,
    'main',
    TRUE,
    FALSE,
    FALSE,
    FALSE
FROM repositories
WHERE repository_name = 'payment-platform';


INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected,
    allow_direct_push,
    allow_force_push,
    allow_deletion
)
SELECT
    repository_id,
    'feature/payment-validation',
    FALSE,
    TRUE,
    FALSE,
    TRUE
FROM repositories
WHERE repository_name = 'payment-platform';


UPDATE branches b
SET head_commit_hash = c.commit_hash
FROM commits c
WHERE b.repository_id = c.repository_id
  AND b.branch_name = 'main'
  AND c.commit_message = 'Initial application';


UPDATE branches b
SET head_commit_hash = c.commit_hash
FROM commits c
WHERE b.repository_id = c.repository_id
  AND b.branch_name = 'feature/payment-validation'
  AND c.commit_message = 'Implement payment validation';


INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    source_commit_id,
    target_commit_id,
    title,
    conversations_resolved,
    created_by
)
SELECT
    r.repository_id,
    source_branch.branch_id,
    target_branch.branch_id,
    source_commit.commit_id,
    target_commit.commit_id,
    'Implement payment validation',
    TRUE,
    d.developer_id
FROM repositories r

JOIN branches source_branch
    ON source_branch.repository_id = r.repository_id
   AND source_branch.branch_name = 'feature/payment-validation'

JOIN branches target_branch
    ON target_branch.repository_id = r.repository_id
   AND target_branch.branch_name = 'main'

JOIN commits source_commit
    ON source_commit.repository_id = r.repository_id
   AND source_commit.commit_message = 'Implement payment validation'

JOIN commits target_commit
    ON target_commit.repository_id = r.repository_id
   AND target_commit.commit_message = 'Initial application'

JOIN developers d
    ON d.username = 'developer_a'

WHERE r.repository_name = 'payment-platform';


INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    decision,
    review_commit_hash,
    review_summary
)
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    'approved',
    '2222222222222222222222222222222222222222',
    'Implementation reviewed successfully'
FROM pull_requests pr
CROSS JOIN reviewers rv
WHERE pr.title = 'Implement payment validation';


INSERT INTO review_comments (
    review_id,
    file_path,
    line_number,
    comment_body,
    is_resolved
)
SELECT
    review_id,
    'src/payment.py',
    25,
    'Input validation reviewed and resolved',
    TRUE
FROM reviews
LIMIT 1;


INSERT INTO pipelines (
    repository_id,
    pipeline_name
)
SELECT repository_id, 'main-delivery-pipeline'
FROM repositories
WHERE repository_name = 'payment-platform';


INSERT INTO pipeline_runs (
    pipeline_id,
    pull_request_id,
    commit_id,
    run_number,
    status,
    environment,
    started_at,
    completed_at,
    triggered_by
)
SELECT
    p.pipeline_id,
    pr.pull_request_id,
    c.commit_id,
    1,
    'succeeded',
    'production',
    NOW() - INTERVAL '10 minutes',
    NOW(),
    d.developer_id
FROM pipelines p
JOIN repositories r
    ON r.repository_id = p.repository_id
JOIN pull_requests pr
    ON pr.repository_id = r.repository_id
JOIN commits c
    ON c.repository_id = r.repository_id
   AND c.commit_message = 'Implement payment validation'
JOIN developers d
    ON d.username = 'developer_a'
WHERE p.pipeline_name = 'main-delivery-pipeline';


INSERT INTO pipeline_stages (
    run_id,
    stage_name,
    execution_order,
    status,
    started_at,
    completed_at,
    log_location
)
SELECT
    run_id,
    data.stage_name::stage_type,
    data.execution_order,
    'passed',
    NOW() - INTERVAL '10 minutes',
    NOW(),
    '/pipeline/logs/' || run_id || '/' || data.stage_name
FROM pipeline_runs
CROSS JOIN (
    VALUES
        ('build', 1),
        ('test', 2),
        ('security_scan', 3),
        ('package', 4),
        ('release', 5)
) AS data(stage_name, execution_order);


INSERT INTO status_checks (
    run_id,
    check_name,
    status,
    details,
    execution_time_ms
)
SELECT
    run_id,
    data.check_name,
    data.status::stage_status,
    data.details,
    data.duration
FROM pipeline_runs
CROSS JOIN (
    VALUES
        ('build', 'passed', 'Compilation successful', 1200),
        ('tests', 'passed', '128 tests passed', 3400),
        ('security-scan', 'passed', 'No blocking findings', 2200)
) AS data(check_name, status, details, duration);


INSERT INTO artifacts (
    run_id,
    artifact_name,
    version,
    storage_location,
    sha256,
    size_bytes,
    is_verified
)
SELECT
    run_id,
    'payment-platform',
    '1.0.0',
    'artifact-registry/payment-platform/1.0.0',
    repeat('a', 64),
    1048576,
    TRUE
FROM pipeline_runs;


INSERT INTO branch_protection_policies (
    repository_id,
    branch_id,
    required_reviews
)
SELECT
    r.repository_id,
    b.branch_id,
    2
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
WHERE r.repository_name = 'payment-platform'
  AND b.branch_name = 'main';


INSERT INTO release_approvals (
    run_id,
    reviewer_id,
    decision,
    comments
)
SELECT
    pr.run_id,
    rv.reviewer_id,
    'approved',
    'Production release approved'
FROM pipeline_runs pr
CROSS JOIN reviewers rv;


/* ============================================================
   17. SAMPLE FAILURE SCENARIO
   ============================================================ */

INSERT INTO pipeline_runs (
    pipeline_id,
    commit_id,
    run_number,
    status,
    environment,
    started_at,
    completed_at,
    failure_reason
)
SELECT
    p.pipeline_id,
    c.commit_id,
    2,
    'failed',
    'staging',
    NOW() - INTERVAL '5 minutes',
    NOW(),
    'Automated tests failed'
FROM pipelines p
JOIN repositories r
    ON r.repository_id = p.repository_id
JOIN commits c
    ON c.repository_id = r.repository_id
WHERE p.pipeline_name = 'main-delivery-pipeline'
  AND c.commit_message = 'Implement payment validation';


/* ============================================================
   18. RETRIEVAL AND REPORTING QUERIES
   ============================================================ */

-- Pipeline execution history.
SELECT *
FROM delivery_run_report
ORDER BY created_at DESC NULLS LAST;


/*
 * Per-stage execution statistics.
 */
SELECT
    stage_name,
    status,
    COUNT(*) AS executions,
    ROUND(AVG(duration_ms), 2) AS average_duration_ms
FROM pipeline_stages
GROUP BY stage_name, status
ORDER BY stage_name, status;


/*
 * Pipeline success and failure rates.
 */
SELECT
    pipeline_id,
    COUNT(*) AS total_runs,
    COUNT(*) FILTER (
        WHERE status IN ('succeeded', 'released')
    ) AS successful_runs,
    COUNT(*) FILTER (
        WHERE status = 'failed'
    ) AS failed_runs,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE status IN ('succeeded', 'released')
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS success_percentage
FROM pipeline_runs
GROUP BY pipeline_id;


/*
 * Identify unresolved review conversations.
 */
SELECT
    pr.pull_request_id,
    pr.title,
    COUNT(rc.comment_id) AS unresolved_comments
FROM pull_requests pr
JOIN reviews r
    ON r.pull_request_id = pr.pull_request_id
JOIN review_comments rc
    ON rc.review_id = r.review_id
WHERE rc.is_resolved = FALSE
GROUP BY pr.pull_request_id, pr.title;


/*
 * Artifact inventory and integrity status.
 */
SELECT
    a.artifact_name,
    a.version,
    a.sha256,
    a.size_bytes,
    a.is_verified,
    pr.status AS pipeline_status
FROM artifacts a
JOIN pipeline_runs pr
    ON pr.run_id = a.run_id
ORDER BY a.created_at DESC;


/*
 * Deployment history.
 */
SELECT
    deployment_id,
    deployment_version,
    environment,
    is_successful,
    deployed_at
FROM deployments
ORDER BY deployed_at DESC;


/* ============================================================
   19. RELEASE ELIGIBILITY EVALUATION
   ============================================================ */

SELECT
    pr.run_id,
    evaluation.eligible,
    evaluation.reason
FROM pipeline_runs pr
CROSS JOIN LATERAL
    evaluate_release_eligibility(pr.run_id) evaluation;


/* ============================================================
   20. WORKFLOW PROCESSING EXAMPLE
   ============================================================ */

-- Retrieve the latest failed pipeline executions.
WITH failed_runs AS (
    SELECT
        run_id,
        pipeline_id,
        failure_reason,
        ROW_NUMBER() OVER (
            PARTITION BY pipeline_id
            ORDER BY created_at DESC
        ) AS failure_rank
    FROM pipeline_runs
    WHERE status = 'failed'
)
SELECT *
FROM failed_runs
WHERE failure_rank = 1;


/*
 * Find successful runs without deployment records.
 */
SELECT
    pr.run_id,
    pr.environment,
    pr.status
FROM pipeline_runs pr
WHERE pr.status = 'succeeded'
  AND NOT EXISTS (
      SELECT 1
      FROM deployments d
      WHERE d.run_id = pr.run_id
  );


/* ============================================================
   21. TRANSACTION-SAFE PROMOTION DEMONSTRATION
   ============================================================ */

-- The procedure validates policy and locks the pipeline run.
-- This sample transaction rolls back its changes after execution.

DO $$
DECLARE
    v_run_id BIGINT;
    v_operator BIGINT;
BEGIN
    SELECT run_id
    INTO v_run_id
    FROM pipeline_runs
    WHERE status = 'succeeded'
    ORDER BY run_id
    LIMIT 1;

    SELECT developer_id
    INTO v_operator
    FROM developers
    WHERE username = 'release_operator';

    IF v_run_id IS NOT NULL AND v_operator IS NOT NULL THEN
        RAISE NOTICE
            'Eligible run candidate: %, operator: %',
            v_run_id,
            v_operator;
    END IF;
END;
$$;


/* ============================================================
   22. GOVERNANCE VALIDATION QUERIES
   ============================================================ */

-- Identify protected branches with unsafe permissions.
SELECT
    repository_id,
    branch_name
FROM branches
WHERE is_protected
  AND (
      allow_direct_push
      OR allow_force_push
      OR allow_deletion
  );


-- Identify approvals from ineligible reviewers.
SELECT
    ra.run_id,
    ra.approval_id,
    d.username
FROM release_approvals ra
JOIN reviewers rv
    ON rv.reviewer_id = ra.reviewer_id
JOIN developers d
    ON d.developer_id = rv.developer_id
WHERE ra.decision = 'approved'
  AND (
      NOT rv.is_eligible
      OR NOT rv.is_active
      OR NOT d.is_active
  );


-- Identify pipeline runs with missing required checks.
SELECT
    pr.run_id,
    required.check_name
FROM pipeline_runs pr
CROSS JOIN (
    VALUES
        ('build'),
        ('tests'),
        ('security-scan')
) AS required(check_name)
LEFT JOIN status_checks sc
    ON sc.run_id = pr.run_id
   AND sc.check_name = required.check_name
WHERE sc.check_id IS NULL
   OR sc.status <> 'passed';


COMMIT;
