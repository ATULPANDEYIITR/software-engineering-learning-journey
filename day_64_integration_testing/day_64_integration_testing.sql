DROP SCHEMA IF EXISTS integration_testing CASCADE;

CREATE SCHEMA integration_testing;

SET search_path = integration_testing;

CREATE TYPE pull_request_state AS ENUM (
    'draft',
    'open',
    'closed',
    'merged'
);

CREATE TYPE review_state AS ENUM (
    'commented',
    'approved',
    'changes_requested',
    'dismissed'
);

CREATE TYPE merge_strategy AS ENUM (
    'merge_commit',
    'squash',
    'rebase'
);

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT false,
    deleted BOOLEAN NOT NULL DEFAULT false,
    current_commit_sha TEXT,
    UNIQUE (repository_id, name)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    sha TEXT NOT NULL,
    message TEXT NOT NULL,
    parent_sha TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (repository_id, sha),
    CHECK (length(sha) BETWEEN 7 AND 40),
    CHECK (btrim(message) <> '')
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    author TEXT NOT NULL,
    state pull_request_state NOT NULL DEFAULT 'open',
    draft BOOLEAN NOT NULL DEFAULT false,
    latest_commit_sha TEXT,
    merge_strategy merge_strategy,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    merged_at TIMESTAMPTZ,
    UNIQUE (repository_id, number),
    CHECK (source_branch_id <> target_branch_id),
    CHECK (btrim(title) <> '')
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id)
        ON DELETE RESTRICT,
    PRIMARY KEY (pull_request_id, commit_id)
);

CREATE TABLE pull_request_files (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    path TEXT NOT NULL,
    change_type TEXT NOT NULL
        CHECK (change_type IN ('added', 'modified', 'deleted', 'renamed')),
    PRIMARY KEY (pull_request_id, path)
);

CREATE TABLE reviewers (
    reviewer_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    username TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT true,
    UNIQUE (repository_id, username)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id)
        ON DELETE RESTRICT,
    state review_state NOT NULL,
    commit_sha TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pull_request_id, reviewer_id, commit_sha)
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    file_path TEXT,
    line_number INTEGER,
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (btrim(body) <> ''),
    CHECK (line_number IS NULL OR line_number > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    commit_sha TEXT NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_reviews INTEGER NOT NULL DEFAULT 0
        CHECK (required_reviews >= 0),
    allow_direct_push BOOLEAN NOT NULL DEFAULT false,
    allow_force_push BOOLEAN NOT NULL DEFAULT false,
    allow_branch_deletion BOOLEAN NOT NULL DEFAULT false,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT true,
    require_linear_history BOOLEAN NOT NULL DEFAULT false,
    administrator_bypass BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE required_status_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name)
);

CREATE INDEX idx_pr_target_state
    ON pull_requests(target_branch_id, state);

CREATE INDEX idx_reviews_pr_commit_state
    ON reviews(pull_request_id, commit_sha, state);

CREATE INDEX idx_status_checks_pr_commit
    ON status_checks(pull_request_id, commit_sha, name);

CREATE INDEX idx_comments_review_resolution
    ON review_comments(review_id, resolved);

CREATE INDEX idx_commits_branch_created
    ON commits(branch_id, created_at DESC);

CREATE OR REPLACE FUNCTION validate_pull_request()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.source_branch_id = NEW.target_branch_id THEN
        RAISE EXCEPTION
            'Source and target branches must be different';
    END IF;

    IF NEW.state = 'merged' AND NEW.merged_at IS NULL THEN
        NEW.merged_at := now();
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_pull_request
BEFORE INSERT OR UPDATE ON pull_requests
FOR EACH ROW
EXECUTE FUNCTION validate_pull_request();

CREATE OR REPLACE FUNCTION set_latest_commit()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    latest_sha TEXT;
BEGIN
    SELECT c.sha
    INTO latest_sha
    FROM pull_request_commits pc
    JOIN commits c
      ON c.commit_id = pc.commit_id
    WHERE pc.pull_request_id = NEW.pull_request_id
    ORDER BY c.created_at DESC, c.commit_id DESC
    LIMIT 1;

    UPDATE pull_requests
    SET latest_commit_sha = latest_sha
    WHERE pull_request_id = NEW.pull_request_id;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_set_latest_commit
AFTER INSERT ON pull_request_commits
FOR EACH ROW
EXECUTE FUNCTION set_latest_commit();

CREATE OR REPLACE FUNCTION merge_eligibility(
    p_pull_request_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    pr RECORD;
    policy RECORD;
    approval_count INTEGER;
    unresolved_count INTEGER;
    missing_check TEXT;
BEGIN
    SELECT *
    INTO pr
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT false, 'Pull Request does not exist';
        RETURN;
    END IF;

    IF pr.state <> 'open' THEN
        RETURN QUERY
        SELECT false, 'Pull Request is not open';
    END IF;

    IF pr.draft THEN
        RETURN QUERY
        SELECT false, 'Pull Request is still a draft';
    END IF;

    SELECT *
    INTO policy
    FROM branch_protection_policies
    WHERE branch_id = pr.target_branch_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT false, 'Target branch has no branch protection policy';
        RETURN;
    END IF;

    SELECT count(DISTINCT r.reviewer_id)
    INTO approval_count
    FROM reviews r
    JOIN reviewers rv
      ON rv.reviewer_id = r.reviewer_id
    WHERE r.pull_request_id = pr.pull_request_id
      AND r.state = 'approved'
      AND r.commit_sha = pr.latest_commit_sha
      AND rv.active = true
      AND rv.username <> pr.author;

    IF approval_count < policy.required_reviews THEN
        RETURN QUERY
        SELECT false,
            format(
                'Required current approvals: %s, found: %s',
                policy.required_reviews,
                approval_count
            );
    END IF;

    FOR missing_check IN
        SELECT rsc.check_name
        FROM required_status_checks rsc
        WHERE rsc.policy_id = policy.policy_id
          AND NOT EXISTS (
              SELECT 1
              FROM status_checks sc
              WHERE sc.pull_request_id = pr.pull_request_id
                AND sc.name = rsc.check_name
                AND sc.commit_sha = pr.latest_commit_sha
                AND sc.passed = true
          )
    LOOP
        RETURN QUERY
        SELECT false,
            'Required status check failed or missing: ' || missing_check;
    END LOOP;

    SELECT count(*)
    INTO unresolved_count
    FROM review_comments rc
    JOIN reviews r
      ON r.review_id = rc.review_id
    WHERE r.pull_request_id = pr.pull_request_id
      AND rc.resolved = false;

    IF policy.require_conversation_resolution
       AND unresolved_count > 0 THEN
        RETURN QUERY
        SELECT false,
            'Unresolved review conversations remain';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pull_request_files
        WHERE pull_request_id = pr.pull_request_id
    ) THEN
        RETURN QUERY
        SELECT false, 'Pull Request has no changed files';
    END IF;

    RETURN QUERY
    SELECT true, 'Merge eligible';
END;
$$;

INSERT INTO repositories (name)
VALUES ('integration-testing-platform');

INSERT INTO branches (
    repository_id,
    name,
    protected,
    current_commit_sha
)
SELECT repository_id, 'main', true, '1111111'
FROM repositories
WHERE name = 'integration-testing-platform';

INSERT INTO branches (
    repository_id,
    name,
    protected,
    current_commit_sha
)
SELECT repository_id, 'feature/integration-tests', false, '3333333'
FROM repositories
WHERE name = 'integration-testing-platform';

INSERT INTO commits (
    repository_id,
    branch_id,
    sha,
    message
)
SELECT
    r.repository_id,
    b.branch_id,
    '1111111',
    'Initial production release'
FROM repositories r
JOIN branches b
  ON b.repository_id = r.repository_id
WHERE r.name = 'integration-testing-platform'
  AND b.name = 'main';

INSERT INTO commits (
    repository_id,
    branch_id,
    sha,
    message,
    parent_sha
)
SELECT
    r.repository_id,
    b.branch_id,
    '2222222',
    'Add API integration test suite',
    '1111111'
FROM repositories r
JOIN branches b
  ON b.repository_id = r.repository_id
WHERE r.name = 'integration-testing-platform'
  AND b.name = 'feature/integration-tests';

INSERT INTO commits (
    repository_id,
    branch_id,
    sha,
    message,
    parent_sha
)
SELECT
    r.repository_id,
    b.branch_id,
    '3333333',
    'Add database transaction integration tests',
    '2222222'
FROM repositories r
JOIN branches b
  ON b.repository_id = r.repository_id
WHERE r.name = 'integration-testing-platform'
  AND b.name = 'feature/integration-tests';

INSERT INTO pull_requests (
    repository_id,
    number,
    title,
    source_branch_id,
    target_branch_id,
    author,
    state,
    draft
)
SELECT
    r.repository_id,
    1,
    'Add database and API integration testing',
    source.branch_id,
    target.branch_id,
    'alice',
    'open',
    false
FROM repositories r
JOIN branches source
  ON source.repository_id = r.repository_id
 AND source.name = 'feature/integration-tests'
JOIN branches target
  ON target.repository_id = r.repository_id
 AND target.name = 'main'
WHERE r.name = 'integration-testing-platform';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id
)
SELECT
    pr.pull_request_id,
    c.commit_id
FROM pull_requests pr
JOIN commits c
  ON c.sha IN ('2222222', '3333333')
WHERE pr.number = 1;

UPDATE pull_requests
SET latest_commit_sha = '3333333'
WHERE number = 1;

INSERT INTO pull_request_files (
    pull_request_id,
    path,
    change_type
)
SELECT
    pull_request_id,
    file_path,
    change_type
FROM pull_requests,
LATERAL (
    VALUES
        ('tests/api.integration.sql', 'added'),
        ('tests/database.integration.sql', 'added'),
        ('src/repository_service.py', 'modified')
) AS files(file_path, change_type)
WHERE number = 1;

INSERT INTO reviewers (
    repository_id,
    username
)
SELECT repository_id, username
FROM repositories
CROSS JOIN (
    VALUES
        ('bob'),
        ('carol'),
        ('dave')
) AS users(username)
WHERE name = 'integration-testing-platform';

INSERT INTO branch_protection_policies (
    branch_id,
    required_reviews,
    allow_direct_push,
    allow_force_push,
    allow_branch_deletion,
    require_conversation_resolution,
    require_linear_history,
    administrator_bypass
)
SELECT
    branch_id,
    2,
    false,
    false,
    false,
    true,
    false,
    false
FROM branches
WHERE name = 'main';

INSERT INTO required_status_checks (
    policy_id,
    check_name
)
SELECT policy_id, check_name
FROM branch_protection_policies
CROSS JOIN (
    VALUES
        ('api-integration'),
        ('database-integration'),
        ('security-scan')
) AS checks(check_name);

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    state,
    commit_sha
)
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    'approved',
    '3333333'
FROM pull_requests pr
JOIN reviewers rv
  ON rv.username = 'bob'
WHERE pr.number = 1;

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    state,
    commit_sha
)
SELECT
    pr.pull_request_id,
    rv.reviewer_id,
    'approved',
    '3333333'
FROM pull_requests pr
JOIN reviewers rv
  ON rv.username = 'carol'
WHERE pr.number = 1;

INSERT INTO review_comments (
    review_id,
    file_path,
    line_number,
    body,
    resolved
)
SELECT
    review_id,
    'tests/database.integration.sql',
    25,
    'Verify rollback behavior when the transaction fails.',
    true
FROM reviews
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 1
)
LIMIT 1;

INSERT INTO status_checks (
    pull_request_id,
    name,
    passed,
    commit_sha
)
SELECT
    pull_request_id,
    checks.name,
    checks.passed,
    '3333333'
FROM pull_requests
CROSS JOIN (
    VALUES
        ('api-integration', true),
        ('database-integration', true),
        ('security-scan', true)
) AS checks(name, passed)
WHERE number = 1;

-- Retrieval: proposed changes and current branch state.
SELECT
    pr.number,
    pr.title,
    source.name AS source_branch,
    target.name AS target_branch,
    pr.state,
    pr.latest_commit_sha
FROM pull_requests pr
JOIN branches source
  ON source.branch_id = pr.source_branch_id
JOIN branches target
  ON target.branch_id = pr.target_branch_id
ORDER BY pr.number;

-- Validation: current approvals for the exact latest commit.
SELECT
    pr.number,
    count(DISTINCT r.reviewer_id) AS current_approvals
FROM pull_requests pr
LEFT JOIN reviews r
  ON r.pull_request_id = pr.pull_request_id
 AND r.commit_sha = pr.latest_commit_sha
 AND r.state = 'approved'
WHERE pr.number = 1
GROUP BY pr.number;

-- Aggregation: status-check results by Pull Request.
SELECT
    pr.number,
    count(*) AS checks,
    count(*) FILTER (WHERE sc.passed) AS passed_checks,
    count(*) FILTER (WHERE NOT sc.passed) AS failed_checks
FROM pull_requests pr
LEFT JOIN status_checks sc
  ON sc.pull_request_id = pr.pull_request_id
GROUP BY pr.number;

-- Evaluation: every merge condition and its current result.
SELECT *
FROM merge_eligibility(
    (
        SELECT pull_request_id
        FROM pull_requests
        WHERE number = 1
    )
);

-- Workflow processing: identify required checks that are missing.
SELECT
    pr.number,
    rsc.check_name
FROM pull_requests pr
JOIN branch_protection_policies bp
  ON bp.branch_id = pr.target_branch_id
JOIN required_status_checks rsc
  ON rsc.policy_id = bp.policy_id
WHERE pr.number = 1
  AND NOT EXISTS (
      SELECT 1
      FROM status_checks sc
      WHERE sc.pull_request_id = pr.pull_request_id
        AND sc.name = rsc.check_name
        AND sc.commit_sha = pr.latest_commit_sha
        AND sc.passed = true
  );

-- Reporting: Pull Requests grouped by lifecycle state.
SELECT
    state,
    count(*) AS pull_request_count
FROM pull_requests
GROUP BY state
ORDER BY state;

-- Eligibility determination for all open Pull Requests.
SELECT
    pr.number,
    pr.title,
    eligibility.eligible,
    eligibility.reason
FROM pull_requests pr
CROSS JOIN LATERAL merge_eligibility(pr.pull_request_id)
    AS eligibility
ORDER BY pr.number, eligibility.eligible DESC;

-- Demonstrate transaction-safe merge-state processing.
BEGIN;

WITH eligibility AS (
    SELECT bool_and(eligible) AS can_merge
    FROM merge_eligibility(
        (
            SELECT pull_request_id
            FROM pull_requests
            WHERE number = 1
        )
    )
)
UPDATE pull_requests
SET
    state = 'merged',
    merge_strategy = 'squash',
    merged_at = now()
WHERE number = 1
  AND (SELECT can_merge FROM eligibility);

COMMIT;

-- The merged state is now auditable.
SELECT
    number,
    state,
    merge_strategy,
    latest_commit_sha,
    merged_at
FROM pull_requests
WHERE number = 1;
