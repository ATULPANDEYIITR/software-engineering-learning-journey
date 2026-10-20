DROP SCHEMA IF EXISTS repository_governance CASCADE;
CREATE SCHEMA repository_governance;
SET search_path TO repository_governance;

-- The schema uses CRUD operations against repository-development data.
-- Foreign keys and CHECK constraints prevent invalid workflow states.

CREATE TYPE pull_request_state AS ENUM ('OPEN', 'CLOSED', 'MERGED');
CREATE TYPE review_state AS ENUM (
    'APPROVED',
    'CHANGES_REQUESTED',
    'COMMENTED'
);
CREATE TYPE check_state AS ENUM ('PASSING', 'FAILING', 'PENDING');

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(name)) > 0)
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    CHECK (username ~ '^[A-Za-z0-9_.-]+$')
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    head_commit TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name),
    CHECK (length(trim(branch_name)) > 0),
    CHECK (length(trim(head_commit)) > 0)
);

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    author_id BIGINT NOT NULL
        REFERENCES users(user_id),
    title TEXT NOT NULL,
    state pull_request_state NOT NULL DEFAULT 'OPEN',
    draft BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(title)) BETWEEN 1 AND 200),
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE commits (
    commit_id TEXT PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    author_id BIGINT NOT NULL
        REFERENCES users(user_id),
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(commit_id)) >= 6),
    CHECK (length(trim(message)) > 0)
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    commit_id TEXT NOT NULL
        REFERENCES commits(commit_id),
    sequence_no INTEGER NOT NULL,
    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, sequence_no),
    CHECK (sequence_no > 0)
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES users(user_id),
    state review_state NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (reviewer_id IS NOT NULL)
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (line_number > 0),
    CHECK (length(trim(file_path)) > 0),
    CHECK (length(trim(body)) > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    state check_state NOT NULL,
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name),
    CHECK (length(trim(check_name)) > 0)
);

CREATE TABLE branch_protection (
    branch_id BIGINT PRIMARY KEY
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_reviews INTEGER NOT NULL DEFAULT 0,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_deletion BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_admin_bypass BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (required_reviews >= 0)
);

CREATE TABLE required_status_checks (
    branch_id BIGINT NOT NULL
        REFERENCES branch_protection(branch_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (branch_id, check_name),
    CHECK (length(trim(check_name)) > 0)
);

CREATE INDEX idx_pull_requests_repository_state
    ON pull_requests(repository_id, state);

CREATE INDEX idx_reviews_pull_request_state
    ON reviews(pull_request_id, state);

CREATE INDEX idx_status_checks_pull_request_state
    ON status_checks(pull_request_id, state);

CREATE INDEX idx_review_comments_unresolved
    ON review_comments(review_id)
    WHERE resolved = FALSE;

INSERT INTO repositories (name)
VALUES ('sql-crud-governance');

INSERT INTO users (username)
VALUES
    ('developer'),
    ('alice'),
    ('bob'),
    ('carol');

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit,
    protected
)
SELECT
    repository_id,
    'main',
    'c100aa',
    TRUE
FROM repositories
WHERE name = 'sql-crud-governance';

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit
)
SELECT
    repository_id,
    'feature/sql-crud',
    'c104bb'
FROM repositories
WHERE name = 'sql-crud-governance';

INSERT INTO branch_protection (
    branch_id,
    required_reviews,
    restrict_direct_push,
    restrict_force_push,
    restrict_deletion,
    require_conversation_resolution,
    require_linear_history,
    allow_admin_bypass
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE
FROM branches
WHERE branch_name = 'main';

INSERT INTO required_status_checks (branch_id, check_name)
SELECT branch_id, 'unit-tests'
FROM branches
WHERE branch_name = 'main';

INSERT INTO required_status_checks (branch_id, check_name)
SELECT branch_id, 'sql-validation'
FROM branches
WHERE branch_name = 'main';

INSERT INTO commits (
    commit_id,
    repository_id,
    author_id,
    message
)
SELECT
    'a81f2d',
    r.repository_id,
    u.user_id,
    'Add SELECT and INSERT examples'
FROM repositories r
CROSS JOIN users u
WHERE r.name = 'sql-crud-governance'
  AND u.username = 'developer';

INSERT INTO commits (
    commit_id,
    repository_id,
    author_id,
    message
)
SELECT
    'b93c10',
    r.repository_id,
    u.user_id,
    'Add UPDATE and DELETE safeguards'
FROM repositories r
CROSS JOIN users u
WHERE r.name = 'sql-crud-governance'
  AND u.username = 'developer';

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    draft
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.user_id,
    'Add safe SQL CRUD examples',
    FALSE
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/sql-crud'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN users author
    ON author.username = 'developer'
WHERE r.name = 'sql-crud-governance';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    sequence_no
)
SELECT pull_request_id, 'a81f2d', 1
FROM pull_requests;

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    sequence_no
)
SELECT pull_request_id, 'b93c10', 2
FROM pull_requests;

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    state,
    body
)
SELECT
    pr.pull_request_id,
    u.user_id,
    'APPROVED',
    'CRUD constraints are appropriate.'
FROM pull_requests pr
JOIN users u ON u.username = 'alice';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    state,
    body
)
SELECT
    pr.pull_request_id,
    u.user_id,
    'APPROVED',
    'Transaction behavior is valid.'
FROM pull_requests pr
JOIN users u ON u.username = 'bob';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    state,
    completed_at
)
SELECT
    pull_request_id,
    'unit-tests',
    'PASSING',
    CURRENT_TIMESTAMP
FROM pull_requests;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    state,
    completed_at
)
SELECT
    pull_request_id,
    'sql-validation',
    'PASSING',
    CURRENT_TIMESTAMP
FROM pull_requests;

-- SELECT: retrieve the active pull-request changeset.
SELECT
    pr.pull_request_id,
    r.name AS repository,
    pr.title,
    source.branch_name AS source_branch,
    target.branch_name AS target_branch,
    u.username AS author,
    pr.state,
    pr.draft
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
JOIN branches source
    ON source.branch_id = pr.source_branch_id
JOIN branches target
    ON target.branch_id = pr.target_branch_id
JOIN users u
    ON u.user_id = pr.author_id
WHERE pr.state = 'OPEN'
ORDER BY pr.created_at;

-- SELECT with aggregation: count commits and unique approvals.
SELECT
    pr.pull_request_id,
    pr.title,
    COUNT(DISTINCT prc.commit_id) AS commit_count,
    COUNT(DISTINCT r.reviewer_id)
        FILTER (WHERE r.state = 'APPROVED') AS approval_count
FROM pull_requests pr
LEFT JOIN pull_request_commits prc
    ON prc.pull_request_id = pr.pull_request_id
LEFT JOIN reviews r
    ON r.pull_request_id = pr.pull_request_id
GROUP BY pr.pull_request_id, pr.title;

-- CTE evaluates whether every required status check passes.
WITH required_checks AS (
    SELECT
        pr.pull_request_id,
        rsc.check_name,
        sc.state
    FROM pull_requests pr
    JOIN branches b
        ON b.branch_id = pr.target_branch_id
    JOIN required_status_checks rsc
        ON rsc.branch_id = b.branch_id
    LEFT JOIN status_checks sc
        ON sc.pull_request_id = pr.pull_request_id
       AND sc.check_name = rsc.check_name
),
check_summary AS (
    SELECT
        pull_request_id,
        COUNT(*) AS required_count,
        COUNT(*) FILTER (WHERE state = 'PASSING') AS passing_count
    FROM required_checks
    GROUP BY pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    cs.required_count,
    cs.passing_count,
    cs.required_count = cs.passing_count AS all_checks_pass
FROM pull_requests pr
JOIN check_summary cs
    ON cs.pull_request_id = pr.pull_request_id;

-- UPDATE: change a pull request title safely.
UPDATE pull_requests
SET
    title = 'Add validated SQL CRUD examples',
    updated_at = CURRENT_TIMESTAMP
WHERE pull_request_id = 1
  AND state = 'OPEN';

-- INSERT a review comment demonstrating review-discussion state.
INSERT INTO review_comments (
    review_id,
    file_path,
    line_number,
    body,
    resolved
)
SELECT
    review_id,
    'crud.sql',
    42,
    'Verify that the DELETE operation is scoped by the primary key.',
    TRUE
FROM reviews
WHERE pull_request_id = 1
  AND reviewer_id = (
      SELECT user_id
      FROM users
      WHERE username = 'alice'
  )
LIMIT 1;

-- Transaction: UPDATE a status check and then inspect the resulting state.
BEGIN;

UPDATE status_checks
SET
    state = 'PASSING',
    completed_at = CURRENT_TIMESTAMP
WHERE pull_request_id = 1
  AND check_name = 'sql-validation';

SELECT
    pull_request_id,
    check_name,
    state
FROM status_checks
WHERE pull_request_id = 1;

COMMIT;

-- View: centralized merge-eligibility report.
CREATE VIEW merge_eligibility AS
WITH approvals AS (
    SELECT
        pull_request_id,
        COUNT(DISTINCT reviewer_id)
            FILTER (WHERE state = 'APPROVED') AS approval_count
    FROM reviews
    GROUP BY pull_request_id
),
required_checks AS (
    SELECT
        pr.pull_request_id,
        COUNT(rsc.check_name) AS required_check_count,
        COUNT(sc.check_name)
            FILTER (WHERE sc.state = 'PASSING') AS passing_check_count
    FROM pull_requests pr
    JOIN required_status_checks rsc
        ON rsc.branch_id = pr.target_branch_id
    LEFT JOIN status_checks sc
        ON sc.pull_request_id = pr.pull_request_id
       AND sc.check_name = rsc.check_name
    GROUP BY pr.pull_request_id
),
unresolved AS (
    SELECT
        pr.pull_request_id,
        COUNT(rc.comment_id)
            FILTER (WHERE rc.resolved = FALSE) AS unresolved_comments
    FROM pull_requests pr
    LEFT JOIN reviews r
        ON r.pull_request_id = pr.pull_request_id
    LEFT JOIN review_comments rc
        ON rc.review_id = r.review_id
    GROUP BY pr.pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    pr.state,
    pr.draft,
    COALESCE(a.approval_count, 0) AS approval_count,
    bp.required_reviews,
    COALESCE(rc.required_check_count, 0) AS required_check_count,
    COALESCE(rc.passing_check_count, 0) AS passing_check_count,
    COALESCE(u.unresolved_comments, 0) AS unresolved_comments,
    (
        pr.state = 'OPEN'
        AND NOT pr.draft
        AND COALESCE(a.approval_count, 0) >= bp.required_reviews
        AND COALESCE(rc.required_check_count, 0)
            = COALESCE(rc.passing_check_count, 0)
        AND (
            NOT bp.require_conversation_resolution
            OR COALESCE(u.unresolved_comments, 0) = 0
        )
    ) AS eligible_for_merge
FROM pull_requests pr
JOIN branch_protection bp
    ON bp.branch_id = pr.target_branch_id
LEFT JOIN approvals a
    ON a.pull_request_id = pr.pull_request_id
LEFT JOIN required_checks rc
    ON rc.pull_request_id = pr.pull_request_id
LEFT JOIN unresolved u
    ON u.pull_request_id = pr.pull_request_id;

SELECT *
FROM merge_eligibility
ORDER BY pull_request_id;

-- DELETE: remove only a non-merged demonstration pull request.
-- Foreign keys cascade its dependent reviews, checks, comments, and
-- changeset rows. Merged history is deliberately preserved.
INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    state
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    u.user_id,
    'Temporary draft for DELETE demonstration',
    'CLOSED'
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/sql-crud'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
JOIN users u
    ON u.username = 'developer'
WHERE r.name = 'sql-crud-governance';

DELETE FROM pull_requests
WHERE title = 'Temporary draft for DELETE demonstration'
  AND state = 'CLOSED';

-- Final retrieval confirms that the merged learning example remains.
SELECT
    pr.pull_request_id,
    pr.title,
    pr.state,
    pr.updated_at
FROM pull_requests pr
ORDER BY pr.pull_request_id;
