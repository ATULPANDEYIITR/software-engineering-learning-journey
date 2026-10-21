DROP SCHEMA IF EXISTS repository_governance CASCADE;
CREATE SCHEMA repository_governance;

SET search_path TO repository_governance;

-- Repository identity is separated from branch and Pull Request state.
CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (btrim(repository_name) <> ''),
    CHECK (btrim(default_branch) <> '')
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    CHECK (username ~ '^[A-Za-z0-9_.-]+$'),
    CHECK (btrim(display_name) <> '')
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE UNIQUE INDEX ux_one_default_branch
    ON branches(repository_id)
    WHERE is_default AND NOT is_deleted;

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    sha TEXT NOT NULL,
    author_id BIGINT NOT NULL REFERENCES users(user_id),
    message TEXT NOT NULL,
    parent_sha TEXT,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, sha),
    CHECK (sha ~ '^[0-9a-fA-F]{7,64}$'),
    CHECK (btrim(message) <> '')
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    number INTEGER NOT NULL,
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    author_id BIGINT NOT NULL REFERENCES users(user_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'draft',
    merge_strategy TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    opened_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    merged_at TIMESTAMPTZ,
    UNIQUE (repository_id, number),
    CHECK (number > 0),
    CHECK (state IN ('draft', 'open', 'closed', 'merged')),
    CHECK (
        merge_strategy IS NULL
        OR merge_strategy IN ('merge_commit', 'squash', 'rebase')
    ),
    CHECK (btrim(title) <> ''),
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    commit_id BIGINT NOT NULL REFERENCES commits(commit_id)
        ON DELETE RESTRICT,
    commit_position INTEGER NOT NULL,
    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, commit_position),
    CHECK (commit_position > 0)
);

CREATE TABLE review_requests (
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES users(user_id)
        ON DELETE RESTRICT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pull_request_id, reviewer_id)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES users(user_id)
        ON DELETE RESTRICT,
    commit_id BIGINT NOT NULL REFERENCES commits(commit_id)
        ON DELETE RESTRICT,
    state TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        state IN (
            'commented',
            'approved',
            'changes_requested',
            'dismissed'
        )
    )
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    body TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (btrim(body) <> ''),
    CHECK (line_number IS NULL OR line_number > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL,
    commit_id BIGINT REFERENCES commits(commit_id)
        ON DELETE RESTRICT,
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name),
    CHECK (status IN ('pending', 'passed', 'failed')),
    CHECK (btrim(check_name) <> '')
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_id BIGINT NOT NULL REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 1,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_direct_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_branch_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_id),
    CHECK (required_approvals >= 0)
);

CREATE TABLE required_status_checks (
    policy_id BIGINT NOT NULL REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name),
    CHECK (btrim(check_name) <> '')
);

CREATE TABLE policy_bypass_users (
    policy_id BIGINT NOT NULL REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    user_id BIGINT NOT NULL REFERENCES users(user_id)
        ON DELETE CASCADE,
    PRIMARY KEY (policy_id, user_id)
);

CREATE INDEX ix_pr_target_branch_state
    ON pull_requests(target_branch_id, state);

CREATE INDEX ix_reviews_pr_state
    ON reviews(pull_request_id, state);

CREATE INDEX ix_status_checks_pr
    ON status_checks(pull_request_id);

CREATE INDEX ix_review_comments_unresolved
    ON review_comments(review_id)
    WHERE NOT resolved;

-- Prevent a Pull Request author from approving their own Pull Request.
CREATE OR REPLACE FUNCTION reject_self_review()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    pr_author BIGINT;
BEGIN
    SELECT author_id
    INTO pr_author
    FROM pull_requests
    WHERE pull_request_id = NEW.pull_request_id;

    IF pr_author = NEW.reviewer_id THEN
        RAISE EXCEPTION
            'Pull Request author % cannot submit a review on their own Pull Request',
            NEW.reviewer_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_reject_self_review
BEFORE INSERT OR UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION reject_self_review();

-- Keep lifecycle timestamps consistent with the state.
CREATE OR REPLACE FUNCTION maintain_pull_request_timestamps()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.state = 'open' AND OLD.state <> 'open'
       AND NEW.opened_at IS NULL THEN
        NEW.opened_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.state IN ('closed', 'merged')
       AND OLD.state NOT IN ('closed', 'merged')
       AND NEW.closed_at IS NULL THEN
        NEW.closed_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.state = 'merged' AND OLD.state <> 'merged'
       AND NEW.merged_at IS NULL THEN
        NEW.merged_at := CURRENT_TIMESTAMP;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_pull_request_timestamps
BEFORE UPDATE ON pull_requests
FOR EACH ROW
EXECUTE FUNCTION maintain_pull_request_timestamps();

INSERT INTO repositories (repository_name, default_branch)
VALUES ('payments-service', 'main');

INSERT INTO users (username, display_name)
VALUES
    ('alice', 'Alice Developer'),
    ('bob', 'Bob Reviewer'),
    ('carol', 'Carol Reviewer'),
    ('dave', 'Dave Maintainer');

INSERT INTO branches (repository_id, branch_name, is_default)
SELECT repository_id, 'main', TRUE
FROM repositories
WHERE repository_name = 'payments-service';

INSERT INTO branches (repository_id, branch_name)
SELECT repository_id, 'feature/payment-validation'
FROM repositories
WHERE repository_name = 'payments-service';

INSERT INTO commits (
    repository_id,
    sha,
    author_id,
    message
)
SELECT
    r.repository_id,
    'a100001',
    u.user_id,
    'Add payment validation'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.repository_name = 'payments-service';

INSERT INTO commits (
    repository_id,
    sha,
    author_id,
    message,
    parent_sha
)
SELECT
    r.repository_id,
    'a100002',
    u.user_id,
    'Add payment boundary tests',
    'a100001'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.repository_name = 'payments-service';

INSERT INTO commits (
    repository_id,
    sha,
    author_id,
    message,
    parent_sha
)
SELECT
    r.repository_id,
    'a100003',
    u.user_id,
    'Reject negative payment amounts',
    'a100002'
FROM repositories r
JOIN users u ON u.username = 'alice'
WHERE r.repository_name = 'payments-service';

INSERT INTO pull_requests (
    repository_id,
    number,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    state
)
SELECT
    r.repository_id,
    42,
    source_branch.branch_id,
    target_branch.branch_id,
    author.user_id,
    'Validate payment requests',
    'open'
FROM repositories r
JOIN branches source_branch
    ON source_branch.repository_id = r.repository_id
   AND source_branch.branch_name = 'feature/payment-validation'
JOIN branches target_branch
    ON target_branch.repository_id = r.repository_id
   AND target_branch.branch_name = 'main'
JOIN users author
    ON author.username = 'alice'
WHERE r.repository_name = 'payments-service';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    commit_position
)
SELECT pr.pull_request_id, c.commit_id, 1
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'a100001'
WHERE pr.number = 42;

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    commit_position
)
SELECT pr.pull_request_id, c.commit_id, 2
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'a100002'
WHERE pr.number = 42;

INSERT INTO review_requests (pull_request_id, reviewer_id)
SELECT pr.pull_request_id, u.user_id
FROM pull_requests pr
JOIN users u ON u.username IN ('bob', 'carol')
WHERE pr.number = 42;

-- Initial approval points to a100002 and becomes stale after a100003.
INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    commit_id,
    state
)
SELECT
    pr.pull_request_id,
    reviewer.user_id,
    c.commit_id,
    'approved'
FROM pull_requests pr
JOIN users reviewer ON reviewer.username = 'bob'
JOIN commits c ON c.sha = 'a100002'
WHERE pr.number = 42;

INSERT INTO review_comments (
    review_id,
    body,
    file_path,
    line_number,
    resolved
)
SELECT
    review_id,
    'Please reject negative payment amounts.',
    'src/payment.py',
    84,
    TRUE
FROM reviews
WHERE state = 'approved';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    status,
    commit_id
)
SELECT
    pr.pull_request_id,
    check_name,
    'passed',
    c.commit_id
FROM pull_requests pr
CROSS JOIN (
    VALUES ('unit-tests'), ('security-scan')
) AS required(check_name)
JOIN commits c ON c.sha = 'a100002'
WHERE pr.number = 42;

INSERT INTO branch_protection_policies (
    repository_id,
    branch_id,
    required_approvals,
    require_conversation_resolution,
    require_linear_history,
    allow_direct_push,
    allow_force_push,
    allow_branch_deletion
)
SELECT
    r.repository_id,
    b.branch_id,
    2,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    FALSE
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
   AND b.branch_name = 'main'
WHERE r.repository_name = 'payments-service';

INSERT INTO required_status_checks (policy_id, check_name)
SELECT policy_id, 'unit-tests'
FROM branch_protection_policies;

INSERT INTO required_status_checks (policy_id, check_name)
SELECT policy_id, 'security-scan'
FROM branch_protection_policies;

-- Add the synchronized commit to the Pull Request.
INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    commit_position
)
SELECT
    pr.pull_request_id,
    c.commit_id,
    3
FROM pull_requests pr
JOIN commits c ON c.sha = 'a100003'
WHERE pr.number = 42;

-- Current reviews reference the latest commit.
INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    commit_id,
    state
)
SELECT
    pr.pull_request_id,
    u.user_id,
    c.commit_id,
    'approved'
FROM pull_requests pr
JOIN users u ON u.username IN ('bob', 'carol')
JOIN commits c ON c.sha = 'a100003'
WHERE pr.number = 42;

INSERT INTO review_comments (
    review_id,
    body,
    file_path,
    line_number,
    resolved
)
SELECT
    review_id,
    CASE
        WHEN reviewer_id = (
            SELECT user_id FROM users WHERE username = 'bob'
        )
        THEN 'Reviewed the synchronized commit.'
        ELSE 'Security and boundary conditions reviewed.'
    END,
    'src/payment.py',
    90,
    TRUE
FROM reviews
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 42
)
AND commit_id = (
    SELECT commit_id
    FROM commits
    WHERE sha = 'a100003'
);

-- View exposing the latest commit in each Pull Request.
CREATE OR REPLACE VIEW pull_request_latest_commit AS
SELECT DISTINCT ON (pr.pull_request_id)
    pr.pull_request_id,
    pr.number,
    pr.repository_id,
    c.commit_id,
    c.sha,
    c.message,
    c.committed_at
FROM pull_requests pr
JOIN pull_request_commits pc
    ON pc.pull_request_id = pr.pull_request_id
JOIN commits c
    ON c.commit_id = pc.commit_id
ORDER BY pr.pull_request_id, pc.commit_position DESC;

-- Current approval counts only include approvals for the latest commit.
CREATE OR REPLACE VIEW pull_request_approval_status AS
WITH latest AS (
    SELECT
        pull_request_id,
        commit_id
    FROM pull_request_latest_commit
),
eligible_approvals AS (
    SELECT DISTINCT
        r.pull_request_id,
        r.reviewer_id
    FROM reviews r
    JOIN latest l
      ON l.pull_request_id = r.pull_request_id
     AND l.commit_id = r.commit_id
    JOIN review_requests rr
      ON rr.pull_request_id = r.pull_request_id
     AND rr.reviewer_id = r.reviewer_id
    JOIN pull_requests pr
      ON pr.pull_request_id = r.pull_request_id
    WHERE r.state = 'approved'
      AND r.reviewer_id <> pr.author_id
)
SELECT
    pr.pull_request_id,
    pr.number,
    pr.author_id,
    p.required_approvals,
    COUNT(ea.reviewer_id) AS current_approvals,
    COUNT(ea.reviewer_id) >= p.required_approvals AS approvals_satisfied
FROM pull_requests pr
JOIN branch_protection_policies p
    ON p.branch_id = pr.target_branch_id
LEFT JOIN eligible_approvals ea
    ON ea.pull_request_id = pr.pull_request_id
GROUP BY
    pr.pull_request_id,
    pr.number,
    pr.author_id,
    p.required_approvals;

-- Complete merge-eligibility report.
CREATE OR REPLACE VIEW pull_request_merge_eligibility AS
WITH latest AS (
    SELECT
        pull_request_id,
        commit_id,
        sha
    FROM pull_request_latest_commit
),
approval AS (
    SELECT *
    FROM pull_request_approval_status
),
required_checks AS (
    SELECT
        p.policy_id,
        p.branch_id,
        COUNT(rsc.check_name) AS required_count,
        COUNT(sc.status_check_id) FILTER (
            WHERE sc.status = 'passed'
        ) AS passed_required_count
    FROM branch_protection_policies p
    LEFT JOIN required_status_checks rsc
        ON rsc.policy_id = p.policy_id
    LEFT JOIN status_checks sc
        ON sc.check_name = rsc.check_name
    GROUP BY p.policy_id, p.branch_id
),
unresolved AS (
    SELECT
        pr.pull_request_id,
        COUNT(rc.comment_id) AS unresolved_count
    FROM pull_requests pr
    LEFT JOIN reviews r
        ON r.pull_request_id = pr.pull_request_id
    LEFT JOIN review_comments rc
        ON rc.review_id = r.review_id
       AND NOT rc.resolved
    GROUP BY pr.pull_request_id
)
SELECT
    pr.number,
    pr.state,
    latest.sha AS latest_commit_sha,
    approval.required_approvals,
    approval.current_approvals,
    approval.approvals_satisfied,
    COALESCE(rc.required_count, 0) AS required_checks,
    COALESCE(rc.passed_required_count, 0) AS passed_required_checks,
    COALESCE(u.unresolved_count, 0) AS unresolved_conversations,
    CASE
        WHEN pr.state <> 'open'
            THEN FALSE
        WHEN NOT approval.approvals_satisfied
            THEN FALSE
        WHEN COALESCE(rc.required_count, 0)
             <> COALESCE(rc.passed_required_count, 0)
            THEN FALSE
        WHEN COALESCE(u.unresolved_count, 0) > 0
            THEN FALSE
        WHEN p.require_linear_history
             AND pr.merge_strategy = 'merge_commit'
            THEN FALSE
        ELSE TRUE
    END AS merge_eligible
FROM pull_requests pr
JOIN branch_protection_policies p
    ON p.branch_id = pr.target_branch_id
JOIN latest
    ON latest.pull_request_id = pr.pull_request_id
JOIN approval
    ON approval.pull_request_id = pr.pull_request_id
LEFT JOIN required_checks rc
    ON rc.policy_id = p.policy_id
LEFT JOIN unresolved u
    ON u.pull_request_id = pr.pull_request_id;

-- Transactional merge operation. It locks the Pull Request while checking
-- eligibility so concurrent changes cannot silently bypass governance.
CREATE OR REPLACE FUNCTION merge_pull_request(
    p_pull_request_id BIGINT,
    p_strategy TEXT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    eligible BOOLEAN;
    current_state TEXT;
BEGIN
    IF p_strategy NOT IN ('merge_commit', 'squash', 'rebase') THEN
        RAISE EXCEPTION 'Unsupported merge strategy: %', p_strategy;
    END IF;

    SELECT state
    INTO current_state
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id
    FOR UPDATE;

    IF current_state IS NULL THEN
        RAISE EXCEPTION 'Pull Request % does not exist', p_pull_request_id;
    END IF;

    SELECT merge_eligible
    INTO eligible
    FROM pull_request_merge_eligibility
    WHERE number = (
        SELECT number
        FROM pull_requests
        WHERE pull_request_id = p_pull_request_id
    );

    IF NOT COALESCE(eligible, FALSE) THEN
        RAISE EXCEPTION
            'Pull Request % is not eligible for merging',
            p_pull_request_id;
    END IF;

    UPDATE pull_requests
    SET state = 'merged',
        merge_strategy = p_strategy,
        merged_at = CURRENT_TIMESTAMP,
        closed_at = CURRENT_TIMESTAMP
    WHERE pull_request_id = p_pull_request_id;
END;
$$;

-- Demonstrate the eligibility report before the transactional merge.
SELECT
    number,
    state,
    latest_commit_sha,
    required_approvals,
    current_approvals,
    required_checks,
    passed_required_checks,
    unresolved_conversations,
    merge_eligible
FROM pull_request_merge_eligibility
ORDER BY number;

-- Demonstrate a policy-oriented audit query.
SELECT
    pr.number,
    u.username AS author,
    tb.branch_name AS target_branch,
    pr.state,
    pr.merge_strategy,
    COUNT(DISTINCT r.review_id) AS review_count,
    COUNT(DISTINCT rc.comment_id) FILTER (
        WHERE NOT rc.resolved
    ) AS unresolved_comments
FROM pull_requests pr
JOIN users u ON u.user_id = pr.author_id
JOIN branches tb ON tb.branch_id = pr.target_branch_id
LEFT JOIN reviews r ON r.pull_request_id = pr.pull_request_id
LEFT JOIN review_comments rc ON rc.review_id = r.review_id
GROUP BY
    pr.number,
    u.username,
    tb.branch_name,
    pr.state,
    pr.merge_strategy
ORDER BY pr.number;

-- PostgreSQL transaction demonstrating the final merge.
BEGIN;

SELECT merge_pull_request(
    (
        SELECT pull_request_id
        FROM pull_requests
        WHERE number = 42
    ),
    'rebase'
);

COMMIT;

SELECT
    number,
    state,
    merge_strategy,
    merged_at
FROM pull_requests
WHERE number = 42;
