-- ============================================================
-- TEST-DRIVEN DEVELOPMENT: RED-GREEN-REFACTOR
-- PostgreSQL 15+
--
-- Models:
--   TDD cycles
--   Test cases and test executions
--   Code changes and commits
--   Pull requests
--   Review decisions and discussions
--   Status checks
--   Branch protection
--   Approval eligibility
--   Merge enforcement
--
-- Execute the script in a dedicated learning database.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS tdd_lab;

SET search_path TO tdd_lab, public;

-- ============================================================
-- ENUMERATED DOMAIN TYPES
-- ============================================================

CREATE TYPE tdd_stage AS ENUM (
    'RED',
    'GREEN',
    'REFACTOR'
);

CREATE TYPE test_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED',
    'SKIPPED'
);

CREATE TYPE pull_request_status AS ENUM (
    'DRAFT',
    'OPEN',
    'CLOSED',
    'MERGED'
);

CREATE TYPE review_decision AS ENUM (
    'APPROVED',
    'CHANGES_REQUESTED',
    'COMMENTED'
);

CREATE TYPE check_status AS ENUM (
    'PENDING',
    'PASSED',
    'FAILED'
);

CREATE TYPE merge_strategy AS ENUM (
    'MERGE_COMMIT',
    'SQUASH',
    'REBASE'
);

-- ============================================================
-- REPOSITORIES
-- ============================================================

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name VARCHAR(150) NOT NULL UNIQUE,
    owner_name VARCHAR(100) NOT NULL,
    default_branch VARCHAR(100) NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT repository_name_not_empty
        CHECK (length(trim(repository_name)) > 0)
);

-- ============================================================
-- REPOSITORY USERS AND REVIEWER ELIGIBILITY
-- ============================================================

CREATE TABLE repository_users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    username VARCHAR(100) NOT NULL,
    role VARCHAR(30) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    can_review BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT valid_repository_role
        CHECK (
            role IN (
                'DEVELOPER',
                'MAINTAINER',
                'ADMINISTRATOR',
                'OBSERVER'
            )
        ),

    UNIQUE (repository_id, username),
    UNIQUE (repository_id, user_id)
);

CREATE INDEX idx_repository_users_active
    ON repository_users(repository_id, active, can_review);

-- ============================================================
-- BRANCHES
-- ============================================================

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    branch_name VARCHAR(150) NOT NULL,
    head_commit VARCHAR(80),
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    allows_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allows_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    allows_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (repository_id, branch_name),
    UNIQUE (repository_id, branch_id),

    CONSTRAINT branch_name_not_empty
        CHECK (length(trim(branch_name)) > 0),

    CONSTRAINT protected_branch_restrictions
        CHECK (
            NOT is_protected OR
            (
                NOT allows_direct_push AND
                NOT allows_force_push AND
                NOT allows_deletion
            )
        )
);

CREATE UNIQUE INDEX idx_one_default_branch
    ON branches(repository_id)
    WHERE is_default;

-- ============================================================
-- COMMITS
-- ============================================================

CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    commit_hash VARCHAR(80) NOT NULL,
    author_id BIGINT,
    commit_message TEXT NOT NULL,
    parent_hash VARCHAR(80),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (repository_id, commit_hash),

    CONSTRAINT commit_message_not_empty
        CHECK (length(trim(commit_message)) > 0),

    FOREIGN KEY (repository_id, author_id)
        REFERENCES repository_users(repository_id, user_id)
);

CREATE INDEX idx_commits_repository_date
    ON commits(repository_id, committed_at DESC);

-- ============================================================
-- BRANCH COMMIT MEMBERSHIP
-- ============================================================

CREATE TABLE branch_commits (
    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    position_number INTEGER NOT NULL,

    PRIMARY KEY (branch_id, commit_id),
    UNIQUE (branch_id, position_number),

    CHECK (position_number > 0)
);

-- ============================================================
-- TEST-DRIVEN DEVELOPMENT CYCLES
-- ============================================================

CREATE TABLE tdd_cycles (
    cycle_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    developer_id BIGINT NOT NULL,
    current_stage tdd_stage NOT NULL DEFAULT 'RED',
    implementation_version INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    FOREIGN KEY (repository_id, developer_id)
        REFERENCES repository_users(repository_id, user_id),

    CHECK (implementation_version >= 0),

    UNIQUE (cycle_id, repository_id)
);

CREATE TABLE tdd_stage_history (
    history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cycle_id BIGINT NOT NULL
        REFERENCES tdd_cycles(cycle_id),
    previous_stage tdd_stage,
    new_stage tdd_stage NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tdd_stage_history_cycle
    ON tdd_stage_history(cycle_id, changed_at);

-- ============================================================
-- TEST CASES
-- ============================================================

CREATE TABLE test_cases (
    test_case_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cycle_id BIGINT NOT NULL
        REFERENCES tdd_cycles(cycle_id),
    test_name VARCHAR(200) NOT NULL,
    test_category VARCHAR(50) NOT NULL,
    test_description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (cycle_id, test_name),

    CHECK (
        test_category IN (
            'UNIT',
            'INTEGRATION',
            'REGRESSION',
            'SECURITY',
            'PERFORMANCE',
            'ACCEPTANCE'
        )
    )
);

CREATE TABLE test_executions (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    test_case_id BIGINT NOT NULL
        REFERENCES test_cases(test_case_id),
    implementation_version INTEGER NOT NULL,
    status test_status NOT NULL,
    duration_ms NUMERIC(12, 3),
    error_message TEXT,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    executed_by BIGINT REFERENCES repository_users(user_id),

    CHECK (implementation_version >= 0),
    CHECK (duration_ms IS NULL OR duration_ms >= 0),

    CHECK (
        (status = 'FAILED' AND error_message IS NOT NULL)
        OR
        (status <> 'FAILED')
    )
);

CREATE INDEX idx_test_executions_case_time
    ON test_executions(test_case_id, executed_at DESC);

CREATE INDEX idx_test_executions_failed
    ON test_executions(executed_at DESC)
    WHERE status = 'FAILED';

-- ============================================================
-- PULL REQUESTS
-- ============================================================

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),
    source_branch_id BIGINT NOT NULL,
    target_branch_id BIGINT NOT NULL,
    created_by BIGINT NOT NULL,
    title VARCHAR(250) NOT NULL,
    description TEXT,
    status pull_request_status NOT NULL DEFAULT 'DRAFT',
    base_synchronized BOOLEAN NOT NULL DEFAULT TRUE,
    is_linear_history BOOLEAN NOT NULL DEFAULT TRUE,
    draft BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    merged_at TIMESTAMPTZ,
    merge_commit_hash VARCHAR(80),
    selected_merge_strategy merge_strategy,

    FOREIGN KEY (repository_id, source_branch_id)
        REFERENCES branches(repository_id, branch_id),

    FOREIGN KEY (repository_id, target_branch_id)
        REFERENCES branches(repository_id, branch_id),

    FOREIGN KEY (repository_id, created_by)
        REFERENCES repository_users(repository_id, user_id),

    CHECK (source_branch_id <> target_branch_id),
    CHECK (length(trim(title)) > 0),

    CHECK (
        (status = 'MERGED' AND merged_at IS NOT NULL)
        OR
        (status <> 'MERGED' AND merged_at IS NULL)
    )
);

CREATE INDEX idx_pull_requests_target_status
    ON pull_requests(target_branch_id, status);

CREATE INDEX idx_pull_requests_repository_created
    ON pull_requests(repository_id, created_at DESC);

-- ============================================================
-- PULL REQUEST COMMITS
-- ============================================================

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    position_number INTEGER NOT NULL,

    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, position_number),

    CHECK (position_number > 0)
);

-- ============================================================
-- REVIEW REQUESTS
-- ============================================================

CREATE TABLE review_requests (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),
    reviewer_id BIGINT NOT NULL
        REFERENCES repository_users(user_id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    PRIMARY KEY (pull_request_id, reviewer_id)
);

-- ============================================================
-- CODE REVIEWS
-- ============================================================

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL,
    reviewer_id BIGINT NOT NULL,
    decision review_decision NOT NULL,
    eligible_at_submission BOOLEAN NOT NULL DEFAULT TRUE,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE,
    is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (pull_request_id, reviewer_id)
        REFERENCES review_requests(pull_request_id, reviewer_id),

    UNIQUE (pull_request_id, reviewer_id)
);

CREATE INDEX idx_reviews_approval_lookup
    ON reviews(pull_request_id, decision)
    WHERE eligible_at_submission
      AND NOT is_stale
      AND NOT is_dismissed;

-- ============================================================
-- REVIEW COMMENTS AND CONVERSATIONS
-- ============================================================

CREATE TABLE review_conversations (
    conversation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),
    created_by BIGINT NOT NULL
        REFERENCES repository_users(user_id),
    file_path TEXT NOT NULL,
    line_number INTEGER,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ,

    CHECK (line_number IS NULL OR line_number > 0),

    CHECK (
        (is_resolved AND resolved_at IS NOT NULL)
        OR
        (NOT is_resolved AND resolved_at IS NULL)
    )
);

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id BIGINT NOT NULL
        REFERENCES review_conversations(conversation_id),
    author_id BIGINT NOT NULL
        REFERENCES repository_users(user_id),
    comment_body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (length(trim(comment_body)) > 0)
);

CREATE INDEX idx_review_conversations_open
    ON review_conversations(pull_request_id)
    WHERE NOT is_resolved;

-- ============================================================
-- AUTOMATED STATUS CHECKS
-- ============================================================

CREATE TABLE status_checks (
    status_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),
    check_name VARCHAR(150) NOT NULL,
    status check_status NOT NULL DEFAULT 'PENDING',
    execution_reference VARCHAR(250),
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    UNIQUE (pull_request_id, check_name),

    CHECK (
        (status = 'PENDING' AND completed_at IS NULL)
        OR
        (status <> 'PENDING' AND completed_at IS NOT NULL)
    )
);

CREATE INDEX idx_status_checks_pr_status
    ON status_checks(pull_request_id, status);

-- ============================================================
-- BRANCH PROTECTION POLICIES
-- ============================================================

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id),
    required_reviews INTEGER NOT NULL DEFAULT 1,
    require_resolved_conversations BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    require_synchronized_base BOOLEAN NOT NULL DEFAULT TRUE,
    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,
    enforce_for_administrators BOOLEAN NOT NULL DEFAULT TRUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (required_reviews >= 0)
);

CREATE TABLE policy_required_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id),
    check_name VARCHAR(150) NOT NULL,

    PRIMARY KEY (policy_id, check_name)
);

-- ============================================================
-- MERGE AUDIT LOG
-- ============================================================

CREATE TABLE merge_audit (
    merge_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL UNIQUE
        REFERENCES pull_requests(pull_request_id),
    merged_by BIGINT NOT NULL
        REFERENCES repository_users(user_id),
    strategy merge_strategy NOT NULL,
    administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,
    merged_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    eligibility_snapshot JSONB NOT NULL
);

-- ============================================================
-- REVIEW ELIGIBILITY TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION validate_review_request()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    reviewer_active BOOLEAN;
    reviewer_eligible BOOLEAN;
    reviewer_role VARCHAR(30);
    request_status pull_request_status;
BEGIN
    SELECT active, can_review, role
    INTO reviewer_active, reviewer_eligible, reviewer_role
    FROM repository_users
    WHERE user_id = NEW.reviewer_id;

    IF NOT FOUND
       OR NOT reviewer_active
       OR NOT reviewer_eligible
       OR reviewer_role = 'OBSERVER' THEN
        RAISE EXCEPTION 'Reviewer is not eligible';
    END IF;

    SELECT status
    INTO request_status
    FROM pull_requests
    WHERE pull_request_id = NEW.pull_request_id;

    IF request_status <> 'OPEN' THEN
        RAISE EXCEPTION 'Reviews require an open pull request';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_review_request
BEFORE INSERT OR UPDATE
ON review_requests
FOR EACH ROW
EXECUTE FUNCTION validate_review_request();

-- ============================================================
-- STALE APPROVAL INVALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION invalidate_approvals_on_commit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE reviews
    SET is_stale = TRUE
    WHERE pull_request_id = NEW.pull_request_id
      AND decision = 'APPROVED'
      AND NOT is_dismissed;

    UPDATE pull_requests
    SET updated_at = CURRENT_TIMESTAMP
    WHERE pull_request_id = NEW.pull_request_id;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_invalidate_approvals
AFTER INSERT
ON pull_request_commits
FOR EACH ROW
EXECUTE FUNCTION invalidate_approvals_on_commit();

-- ============================================================
-- TDD STAGE TRANSITION VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_tdd_stage_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    allowed_transition BOOLEAN;
    all_tests_passed BOOLEAN;
BEGIN
    IF NEW.current_stage = OLD.current_stage THEN
        RETURN NEW;
    END IF;

    allowed_transition :=
        (
            OLD.current_stage = 'RED'
            AND NEW.current_stage = 'GREEN'
        )
        OR
        (
            OLD.current_stage = 'GREEN'
            AND NEW.current_stage = 'REFACTOR'
        )
        OR
        (
            OLD.current_stage = 'REFACTOR'
            AND NEW.current_stage IN ('RED', 'GREEN')
        );

    IF NOT allowed_transition THEN
        RAISE EXCEPTION
            'Invalid TDD transition: % -> %',
            OLD.current_stage,
            NEW.current_stage;
    END IF;

    IF NEW.current_stage IN ('GREEN', 'REFACTOR') THEN

        SELECT COALESCE(
            bool_and(te.status = 'PASSED'),
            FALSE
        )
        INTO all_tests_passed
        FROM test_cases tc
        LEFT JOIN LATERAL (
            SELECT status
            FROM test_executions
            WHERE test_case_id = tc.test_case_id
            ORDER BY executed_at DESC, execution_id DESC
            LIMIT 1
        ) te ON TRUE
        WHERE tc.cycle_id = NEW.cycle_id
          AND tc.is_active;

        IF NOT all_tests_passed THEN
            RAISE EXCEPTION
                'All active tests must pass before GREEN or REFACTOR';
        END IF;
    END IF;

    IF NEW.current_stage = 'REFACTOR' THEN
        NEW.implementation_version :=
            OLD.implementation_version + 1;
    END IF;

    INSERT INTO tdd_stage_history (
        cycle_id,
        previous_stage,
        new_stage,
        evidence
    )
    VALUES (
        NEW.cycle_id,
        OLD.current_stage,
        NEW.current_stage,
        jsonb_build_object(
            'implementation_version',
            NEW.implementation_version
        )
    );

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_tdd_stage
BEFORE UPDATE OF current_stage
ON tdd_cycles
FOR EACH ROW
EXECUTE FUNCTION validate_tdd_stage_transition();

-- ============================================================
-- MERGE ELIGIBILITY FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION evaluate_merge_eligibility(
    p_pull_request_id BIGINT,
    p_administrator BOOLEAN DEFAULT FALSE
)
RETURNS TABLE (
    eligible BOOLEAN,
    valid_approvals BIGINT,
    reasons TEXT[]
)
LANGUAGE plpgsql
AS $$
DECLARE
    pr RECORD;
    policy RECORD;
    approval_count BIGINT;
    changes_requested BOOLEAN;
    unresolved_count BIGINT;
    missing_checks TEXT[];
    failure_reasons TEXT[] := ARRAY[]::TEXT[];
    bypass_allowed BOOLEAN := FALSE;
BEGIN

    SELECT
        pr.pull_request_id,
        pr.status,
        pr.target_branch_id,
        pr.base_synchronized,
        pr.is_linear_history,
        b.is_protected
    INTO pr
    FROM pull_requests pr
    JOIN branches b
      ON b.branch_id = pr.target_branch_id
    WHERE pr.pull_request_id = p_pull_request_id
    FOR UPDATE OF pr;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pull request % does not exist',
            p_pull_request_id;
    END IF;

    SELECT *
    INTO policy
    FROM branch_protection_policies bp
    WHERE bp.branch_id = pr.target_branch_id
      AND bp.enabled;

    IF NOT FOUND THEN
        failure_reasons := array_append(
            failure_reasons,
            'No active branch protection policy'
        );

        RETURN QUERY SELECT
            FALSE,
            0::BIGINT,
            failure_reasons;

        RETURN;
    END IF;

    bypass_allowed :=
        p_administrator
        AND policy.allow_administrator_bypass
        AND NOT policy.enforce_for_administrators;

    IF pr.status <> 'OPEN' THEN
        failure_reasons := array_append(
            failure_reasons,
            'Pull request must be open'
        );
    END IF;

    IF NOT pr.is_protected THEN
        failure_reasons := array_append(
            failure_reasons,
            'Target branch is not protected'
        );
    END IF;

    SELECT COUNT(*)
    INTO approval_count
    FROM reviews r
    WHERE r.pull_request_id = p_pull_request_id
      AND r.decision = 'APPROVED'
      AND r.eligible_at_submission
      AND NOT r.is_stale
      AND NOT r.is_dismissed;

    IF approval_count < policy.required_reviews THEN
        failure_reasons := array_append(
            failure_reasons,
            'Insufficient valid approvals'
        );
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM reviews r
        WHERE r.pull_request_id = p_pull_request_id
          AND r.decision = 'CHANGES_REQUESTED'
          AND r.eligible_at_submission
          AND NOT r.is_stale
          AND NOT r.is_dismissed
    )
    INTO changes_requested;

    IF changes_requested THEN
        failure_reasons := array_append(
            failure_reasons,
            'Changes requested by reviewer'
        );
    END IF;

    IF policy.require_resolved_conversations THEN
        SELECT COUNT(*)
        INTO unresolved_count
        FROM review_conversations rc
        WHERE rc.pull_request_id = p_pull_request_id
          AND NOT rc.is_resolved;

        IF unresolved_count > 0 THEN
            failure_reasons := array_append(
                failure_reasons,
                'Unresolved review conversations'
            );
        END IF;
    END IF;

    IF policy.require_synchronized_base
       AND NOT pr.base_synchronized THEN
        failure_reasons := array_append(
            failure_reasons,
            'Source branch must synchronize with target'
        );
    END IF;

    IF policy.require_linear_history
       AND NOT pr.is_linear_history THEN
        failure_reasons := array_append(
            failure_reasons,
            'Linear history requirement not satisfied'
        );
    END IF;

    SELECT COALESCE(
        array_agg(required.check_name),
        ARRAY[]::TEXT[]
    )
    INTO missing_checks
    FROM policy_required_checks required
    LEFT JOIN status_checks sc
      ON sc.pull_request_id = p_pull_request_id
     AND sc.check_name = required.check_name
    WHERE required.policy_id = policy.policy_id
      AND (
          sc.status IS NULL
          OR sc.status <> 'PASSED'
      );

    IF cardinality(missing_checks) > 0 THEN
        failure_reasons := array_append(
            failure_reasons,
            'Missing or failed checks: ' ||
            array_to_string(missing_checks, ', ')
        );
    END IF;

    IF bypass_allowed THEN
        failure_reasons := ARRAY[
            'Authorized administrator bypass'
        ];

        RETURN QUERY SELECT
            TRUE,
            approval_count,
            failure_reasons;

        RETURN;
    END IF;

    RETURN QUERY SELECT
        cardinality(failure_reasons) = 0,
        approval_count,
        failure_reasons;
END;
$$;

-- ============================================================
-- TRANSACTIONAL MERGE PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE merge_pull_request(
    p_pull_request_id BIGINT,
    p_merger_id BIGINT,
    p_strategy merge_strategy,
    p_administrator BOOLEAN DEFAULT FALSE
)
LANGUAGE plpgsql
AS $$
DECLARE
    result RECORD;
    bypass_used BOOLEAN;
    snapshot JSONB;
BEGIN
    -- Lock the pull request to prevent concurrent merges.
    PERFORM 1
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pull request does not exist';
    END IF;

    SELECT *
    INTO result
    FROM evaluate_merge_eligibility(
        p_pull_request_id,
        p_administrator
    );

    IF NOT result.eligible THEN
        RAISE EXCEPTION
            'Merge blocked: %',
            array_to_string(result.reasons, '; ');
    END IF;

    bypass_used :=
        p_administrator
        AND result.reasons =
            ARRAY['Authorized administrator bypass']::TEXT[];

    SELECT jsonb_build_object(
        'valid_approvals', result.valid_approvals,
        'eligibility_reasons', result.reasons,
        'evaluated_at', CURRENT_TIMESTAMP,
        'administrator_bypass', bypass_used
    )
    INTO snapshot;

    UPDATE pull_requests
    SET status = 'MERGED',
        draft = FALSE,
        merged_at = CURRENT_TIMESTAMP,
        selected_merge_strategy = p_strategy,
        updated_at = CURRENT_TIMESTAMP
    WHERE pull_request_id = p_pull_request_id;

    INSERT INTO merge_audit (
        pull_request_id,
        merged_by,
        strategy,
        administrator_bypass,
        eligibility_snapshot
    )
    VALUES (
        p_pull_request_id,
        p_merger_id,
        p_strategy,
        bypass_used,
        snapshot
    );

END;
$$;

-- ============================================================
-- REPORTING VIEWS
-- ============================================================

CREATE OR REPLACE VIEW test_execution_summary AS
SELECT
    tc.cycle_id,
    tc.test_category,
    COUNT(te.execution_id) AS total_executions,
    COUNT(*) FILTER (
        WHERE te.status = 'PASSED'
    ) AS passed_executions,
    COUNT(*) FILTER (
        WHERE te.status = 'FAILED'
    ) AS failed_executions,
    ROUND(
        AVG(te.duration_ms),
        3
    ) AS average_duration_ms
FROM test_cases tc
LEFT JOIN test_executions te
    ON te.test_case_id = tc.test_case_id
GROUP BY
    tc.cycle_id,
    tc.test_category;

CREATE OR REPLACE VIEW pull_request_review_summary AS
SELECT
    pr.pull_request_id,
    pr.title,
    pr.status,
    COUNT(r.review_id) FILTER (
        WHERE r.decision = 'APPROVED'
          AND r.eligible_at_submission
          AND NOT r.is_stale
          AND NOT r.is_dismissed
    ) AS valid_approvals,
    COUNT(rc.conversation_id) FILTER (
        WHERE NOT rc.is_resolved
    ) AS unresolved_conversations,
    COUNT(sc.status_check_id) FILTER (
        WHERE sc.status = 'FAILED'
    ) AS failed_checks
FROM pull_requests pr
LEFT JOIN reviews r
    ON r.pull_request_id = pr.pull_request_id
LEFT JOIN review_conversations rc
    ON rc.pull_request_id = pr.pull_request_id
LEFT JOIN status_checks sc
    ON sc.pull_request_id = pr.pull_request_id
GROUP BY
    pr.pull_request_id,
    pr.title,
    pr.status;

-- ============================================================
-- SAMPLE DATA
-- ============================================================

INSERT INTO repositories (
    repository_name,
    owner_name,
    default_branch
)
VALUES (
    'payment-service',
    'engineering',
    'main'
);

INSERT INTO repository_users (
    repository_id,
    username,
    role,
    active,
    can_review
)
SELECT
    repository_id,
    user_data.username,
    user_data.role,
    TRUE,
    user_data.can_review
FROM repositories
CROSS JOIN (
    VALUES
        ('developer-1', 'DEVELOPER', TRUE),
        ('reviewer-1', 'MAINTAINER', TRUE),
        ('reviewer-2', 'MAINTAINER', TRUE),
        ('admin-1', 'ADMINISTRATOR', TRUE),
        ('observer-1', 'OBSERVER', FALSE)
) AS user_data(username, role, can_review)
WHERE repository_name = 'payment-service';

INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected,
    allows_direct_push,
    allows_force_push,
    allows_deletion,
    is_default
)
SELECT
    repository_id,
    'main',
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    TRUE
FROM repositories
WHERE repository_name = 'payment-service';

INSERT INTO branches (
    repository_id,
    branch_name,
    is_protected,
    allows_direct_push,
    allows_force_push,
    allows_deletion
)
SELECT
    repository_id,
    'feature/payment-validation',
    FALSE,
    TRUE,
    TRUE,
    TRUE
FROM repositories
WHERE repository_name = 'payment-service';

INSERT INTO commits (
    repository_id,
    commit_hash,
    author_id,
    commit_message
)
SELECT
    r.repository_id,
    'commit-a001',
    u.user_id,
    'Add payment validation'
FROM repositories r
JOIN repository_users u
    ON u.repository_id = r.repository_id
WHERE r.repository_name = 'payment-service'
  AND u.username = 'developer-1';

INSERT INTO commits (
    repository_id,
    commit_hash,
    author_id,
    commit_message
)
SELECT
    r.repository_id,
    'commit-a002',
    u.user_id,
    'Handle invalid payment amounts'
FROM repositories r
JOIN repository_users u
    ON u.repository_id = r.repository_id
WHERE r.repository_name = 'payment-service'
  AND u.username = 'developer-1';

-- ============================================================
-- TDD SAMPLE WORKFLOW
-- ============================================================

INSERT INTO tdd_cycles (
    repository_id,
    branch_id,
    developer_id
)
SELECT
    r.repository_id,
    b.branch_id,
    u.user_id
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
JOIN repository_users u
    ON u.repository_id = r.repository_id
WHERE r.repository_name = 'payment-service'
  AND b.branch_name = 'feature/payment-validation'
  AND u.username = 'developer-1';

INSERT INTO test_cases (
    cycle_id,
    test_name,
    test_category,
    test_description
)
SELECT
    cycle_id,
    test_data.test_name,
    test_data.test_category,
    test_data.description
FROM tdd_cycles tc
CROSS JOIN (
    VALUES
        (
            'valid_payment',
            'UNIT',
            'Accept valid payment amount'
        ),
        (
            'negative_payment',
            'UNIT',
            'Reject negative payment amount'
        ),
        (
            'payment_boundary',
            'BOUNDARY',
            'Validate payment limits'
        )
) AS test_data(test_name, test_category, description);

-- Correct the category constraint for this demonstration:
-- The domain accepts UNIT, INTEGRATION, REGRESSION,
-- SECURITY, PERFORMANCE, and ACCEPTANCE.
-- Use ACCEPTANCE for the boundary scenario.
UPDATE test_cases
SET test_category = 'ACCEPTANCE'
WHERE test_name = 'payment_boundary';

-- Each active test must have a passing latest execution
-- before the cycle can advance to GREEN.
INSERT INTO test_executions (
    test_case_id,
    implementation_version,
    status,
    duration_ms,
    executed_by
)
SELECT
    tc.test_case_id,
    0,
    'PASSED',
    CASE tc.test_name
        WHEN 'valid_payment' THEN 1.250
        WHEN 'negative_payment' THEN 0.950
        ELSE 1.800
    END,
    u.user_id
FROM test_cases tc
JOIN tdd_cycles cycle
    ON cycle.cycle_id = tc.cycle_id
JOIN repositories r
    ON r.repository_id = cycle.repository_id
JOIN repository_users u
    ON u.repository_id = r.repository_id
WHERE r.repository_name = 'payment-service'
  AND u.username = 'developer-1';

-- RED -> GREEN.
UPDATE tdd_cycles
SET current_stage = 'GREEN'
WHERE cycle_id = 1;

-- GREEN -> REFACTOR.
UPDATE tdd_cycles
SET current_stage = 'REFACTOR'
WHERE cycle_id = 1;

-- ============================================================
-- PULL REQUEST SAMPLE
-- ============================================================

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    created_by,
    title,
    description,
    status,
    draft,
    base_synchronized,
    is_linear_history
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    developer.user_id,
    'Validate payment amounts',
    'Introduces payment amount validation and regression tests.',
    'OPEN',
    FALSE,
    TRUE,
    TRUE
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/payment-validation'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN repository_users developer
    ON developer.repository_id = r.repository_id
   AND developer.username = 'developer-1'
WHERE r.repository_name = 'payment-service';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    position_number
)
SELECT
    pr.pull_request_id,
    c.commit_id,
    ROW_NUMBER() OVER (ORDER BY c.commit_hash)
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
JOIN commits c
    ON c.repository_id = r.repository_id
WHERE pr.title = 'Validate payment amounts'
  AND c.commit_hash IN ('commit-a001', 'commit-a002');

-- ============================================================
-- BRANCH PROTECTION CONFIGURATION
-- ============================================================

INSERT INTO branch_protection_policies (
    branch_id,
    required_reviews,
    require_resolved_conversations,
    require_linear_history,
    require_synchronized_base,
    allow_administrator_bypass,
    enforce_for_administrators
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    TRUE
FROM branches
WHERE branch_name = 'main';

INSERT INTO policy_required_checks (
    policy_id,
    check_name
)
SELECT
    policy_id,
    required_check
FROM branch_protection_policies
CROSS JOIN (
    VALUES
        ('unit-tests'),
        ('integration-tests'),
        ('security-scan')
) AS required(required_check);

-- ============================================================
-- REVIEW REQUESTS
-- ============================================================

INSERT INTO review_requests (
    pull_request_id,
    reviewer_id
)
SELECT
    pr.pull_request_id,
    reviewer.user_id
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
JOIN repository_users reviewer
    ON reviewer.repository_id = r.repository_id
WHERE pr.title = 'Validate payment amounts'
  AND reviewer.username IN (
      'reviewer-1',
      'reviewer-2'
  );

-- ============================================================
-- REVIEW DECISIONS
-- ============================================================

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    decision,
    eligible_at_submission
)
SELECT
    pr.pull_request_id,
    reviewer.user_id,
    'APPROVED',
    TRUE
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
JOIN repository_users reviewer
    ON reviewer.repository_id = r.repository_id
WHERE pr.title = 'Validate payment amounts'
  AND reviewer.username IN (
      'reviewer-1',
      'reviewer-2'
  );

-- ============================================================
-- AUTOMATED CHECK RESULTS
-- ============================================================

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    status,
    execution_reference,
    completed_at
)
SELECT
    pr.pull_request_id,
    check_data.check_name,
    check_data.status::check_status,
    check_data.execution_reference,
    CURRENT_TIMESTAMP
FROM pull_requests pr
CROSS JOIN (
    VALUES
        (
            'unit-tests',
            'PASSED',
            'pipeline-001-unit'
        ),
        (
            'integration-tests',
            'PASSED',
            'pipeline-001-integration'
        ),
        (
            'security-scan',
            'PASSED',
            'pipeline-001-security'
        )
) AS check_data(
    check_name,
    status,
    execution_reference
)
WHERE pr.title = 'Validate payment amounts';

-- ============================================================
-- RETRIEVAL QUERIES
-- ============================================================

-- Repository branches and protection state.
SELECT
    r.repository_name,
    b.branch_name,
    b.is_protected,
    b.allows_direct_push,
    b.allows_force_push,
    b.allows_deletion
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
ORDER BY b.branch_name;

-- Pull request changeset.
SELECT
    pr.pull_request_id,
    pr.title,
    source.branch_name AS source_branch,
    target.branch_name AS target_branch,
    c.commit_hash,
    c.commit_message
FROM pull_requests pr
JOIN branches source
    ON source.branch_id = pr.source_branch_id
JOIN branches target
    ON target.branch_id = pr.target_branch_id
JOIN pull_request_commits pc
    ON pc.pull_request_id = pr.pull_request_id
JOIN commits c
    ON c.commit_id = pc.commit_id
ORDER BY pr.pull_request_id, pc.position_number;

-- ============================================================
-- TEST VALIDATION AND AGGREGATION
-- ============================================================

SELECT *
FROM test_execution_summary
ORDER BY cycle_id, test_category;

-- Latest test result per test case.
WITH latest_execution AS (
    SELECT DISTINCT ON (test_case_id)
        test_case_id,
        status,
        executed_at,
        duration_ms
    FROM test_executions
    ORDER BY
        test_case_id,
        executed_at DESC,
        execution_id DESC
)
SELECT
    tc.test_name,
    latest.status,
    latest.duration_ms
FROM test_cases tc
LEFT JOIN latest_execution latest
    ON latest.test_case_id = tc.test_case_id
ORDER BY tc.test_case_id;

-- ============================================================
-- CODE REVIEW REPORTING
-- ============================================================

SELECT
    pr.pull_request_id,
    reviewer.username,
    rv.decision,
    rv.is_stale,
    rv.is_dismissed,
    rv.reviewed_at
FROM reviews rv
JOIN pull_requests pr
    ON pr.pull_request_id = rv.pull_request_id
JOIN repository_users reviewer
    ON reviewer.user_id = rv.reviewer_id
ORDER BY rv.reviewed_at;

-- Review discussions.
SELECT
    rc.conversation_id,
    rc.file_path,
    rc.line_number,
    rc.is_resolved,
    COUNT(comment.comment_id) AS comment_count
FROM review_conversations rc
LEFT JOIN review_comments comment
    ON comment.conversation_id = rc.conversation_id
GROUP BY
    rc.conversation_id,
    rc.file_path,
    rc.line_number,
    rc.is_resolved;

-- ============================================================
-- MERGE ELIGIBILITY EVALUATION
-- ============================================================

SELECT *
FROM evaluate_merge_eligibility(
    (
        SELECT pull_request_id
        FROM pull_requests
        WHERE title = 'Validate payment amounts'
    ),
    FALSE
);

-- ============================================================
-- ELIGIBILITY REPORT
-- ============================================================

SELECT
    pr.pull_request_id,
    pr.title,
    pr.status,
    eligibility.eligible,
    eligibility.valid_approvals,
    eligibility.reasons
FROM pull_requests pr
CROSS JOIN LATERAL evaluate_merge_eligibility(
    pr.pull_request_id,
    FALSE
) eligibility;

-- ============================================================
-- MERGE TRANSACTION
-- ============================================================

-- The savepoint demonstrates rollback of a rejected operation.
-- The successful merge is committed atomically with its audit row.

SAVEPOINT before_merge;

CALL merge_pull_request(
    (
        SELECT pull_request_id
        FROM pull_requests
        WHERE title = 'Validate payment amounts'
    ),
    (
        SELECT user_id
        FROM repository_users
        WHERE username = 'admin-1'
    ),
    'SQUASH',
    FALSE
);

RELEASE SAVEPOINT before_merge;

-- ============================================================
-- FINAL REPORTING
-- ============================================================

SELECT
    pr.pull_request_id,
    pr.title,
    pr.status,
    pr.selected_merge_strategy,
    pr.merged_at,
    audit.administrator_bypass,
    audit.eligibility_snapshot
FROM pull_requests pr
LEFT JOIN merge_audit audit
    ON audit.pull_request_id = pr.pull_request_id;

SELECT
    current_stage,
    implementation_version,
    COUNT(*) AS cycle_count
FROM tdd_cycles
GROUP BY current_stage, implementation_version;

SELECT *
FROM pull_request_review_summary;

COMMIT;
