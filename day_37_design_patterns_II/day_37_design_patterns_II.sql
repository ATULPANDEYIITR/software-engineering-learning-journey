-- Design Patterns II: Strategy, Observer, Adapter
--
-- PostgreSQL-compatible repository governance model.
--
-- Strategy is represented by merge policies and their configurable rules.
-- Observer is represented by repository events and independent subscribers.
-- Adapter is represented by external CI records normalized into status_checks.
--
-- The database enforces domain integrity while application code can select
-- and execute the appropriate strategy.

DROP SCHEMA IF EXISTS design_patterns_ii CASCADE;

CREATE SCHEMA design_patterns_ii;

SET search_path TO design_patterns_ii;

-- ---------------------------------------------------------------------------
-- Core repository domain
-- ---------------------------------------------------------------------------

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE repository_members (
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    role TEXT NOT NULL
        CHECK (role IN ('developer', 'reviewer', 'maintainer', 'admin')),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (repository_id, username)
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    sha TEXT NOT NULL,
    author TEXT NOT NULL,
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, sha)
);

-- ---------------------------------------------------------------------------
-- Pull Requests
-- ---------------------------------------------------------------------------

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    number INTEGER NOT NULL CHECK (number > 0),
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    source_branch TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    head_commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    state TEXT NOT NULL
        CHECK (
            state IN (
                'draft',
                'open',
                'changes_requested',
                'merged',
                'closed'
            )
        ),
    mergeable BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, number)
);

CREATE INDEX idx_pull_requests_target_state
    ON pull_requests(repository_id, target_branch, state);

CREATE INDEX idx_pull_requests_author
    ON pull_requests(repository_id, author);

-- ---------------------------------------------------------------------------
-- Pull Request commits
-- ---------------------------------------------------------------------------

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    sequence_number INTEGER NOT NULL CHECK (sequence_number > 0),
    PRIMARY KEY (pull_request_id, commit_id),
    UNIQUE (pull_request_id, sequence_number)
);

-- ---------------------------------------------------------------------------
-- Code Review
--
-- Reviews are tied to a specific commit. This is important because a review
-- evaluates a particular version of a Pull Request rather than an abstract
-- branch that may change later.
-- ---------------------------------------------------------------------------

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    reviewer TEXT NOT NULL,
    decision TEXT NOT NULL
        CHECK (
            decision IN (
                'approve',
                'request_changes',
                'comment'
            )
        ),
    reviewed_commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    body TEXT
);

CREATE INDEX idx_reviews_pr_commit
    ON reviews(pull_request_id, reviewed_commit_id);

CREATE INDEX idx_reviews_reviewer
    ON reviews(reviewer);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER CHECK (line_number > 0),
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_review_comments_unresolved
    ON review_comments(review_id, resolved)
    WHERE resolved = FALSE;

-- ---------------------------------------------------------------------------
-- Status checks
--
-- This table is the application's normalized status model. External CI
-- terminology is translated into these values by an Adapter in the
-- application layer.
-- ---------------------------------------------------------------------------

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    status TEXT NOT NULL
        CHECK (status IN ('passing', 'failing', 'pending')),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name, commit_id)
);

CREATE INDEX idx_status_checks_current
    ON status_checks(pull_request_id, commit_id, status);

-- ---------------------------------------------------------------------------
-- External CI records
--
-- The external provider has its own result vocabulary. These records preserve
-- the source-system representation while status_checks stores the normalized
-- Adapter output.
-- ---------------------------------------------------------------------------

CREATE TABLE external_ci_builds (
    external_build_id BIGSERIAL PRIMARY KEY,
    provider TEXT NOT NULL,
    external_build_key TEXT NOT NULL,
    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),
    external_result TEXT NOT NULL,
    UNIQUE (provider, external_build_key)
);

-- ---------------------------------------------------------------------------
-- Branch protection
--
-- These settings represent repository-level governance. They are distinct
-- from reviews themselves. A review is an evaluation; protection is policy
-- enforcement for the target branch.
-- ---------------------------------------------------------------------------

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id) ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 0
        CHECK (required_approvals >= 0),
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT FALSE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    enforce_for_administrators BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE required_status_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name)
);

CREATE TABLE protected_reviewers (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id) ON DELETE CASCADE,
    username TEXT NOT NULL,
    PRIMARY KEY (policy_id, username)
);

-- ---------------------------------------------------------------------------
-- Observer event log
-- ---------------------------------------------------------------------------

CREATE TABLE repository_events (
    event_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    pull_request_id BIGINT
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_repository_events_pr_time
    ON repository_events(pull_request_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- Sample repository and members
-- ---------------------------------------------------------------------------

INSERT INTO repositories (repository_name)
VALUES ('payment-platform');

INSERT INTO repository_members
    (repository_id, username, role)
SELECT repository_id, username, role
FROM repositories
CROSS JOIN (
    VALUES
        ('alice', 'developer'),
        ('bob', 'reviewer'),
        ('carol', 'reviewer'),
        ('david', 'maintainer'),
        ('release-bot', 'maintainer')
) AS members(username, role)
WHERE repository_name = 'payment-platform';

INSERT INTO branches
    (repository_id, branch_name, protected)
SELECT repository_id, branch_name, protected
FROM repositories
CROSS JOIN (
    VALUES
        ('main', TRUE),
        ('develop', FALSE)
) AS branch_data(branch_name, protected)
WHERE repository_name = 'payment-platform';

-- ---------------------------------------------------------------------------
-- Production branch protection policy
-- ---------------------------------------------------------------------------

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_conversation_resolution,
    require_linear_history,
    allow_force_push,
    allow_deletion,
    restrict_direct_push,
    enforce_for_administrators
)
SELECT
    b.branch_id,
    2,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    TRUE,
    TRUE
FROM branches b
JOIN repositories r
    ON r.repository_id = b.repository_id
WHERE r.repository_name = 'payment-platform'
  AND b.branch_name = 'main';

INSERT INTO required_status_checks (policy_id, check_name)
SELECT policy_id, check_name
FROM branch_protection_policies
CROSS JOIN (
    VALUES
        ('unit-tests'),
        ('security-scan')
) AS checks(check_name);

INSERT INTO protected_reviewers (policy_id, username)
SELECT policy_id, username
FROM branch_protection_policies
CROSS JOIN (
    VALUES
        ('bob'),
        ('carol'),
        ('david')
) AS reviewers(username);

-- ---------------------------------------------------------------------------
-- Commits
-- ---------------------------------------------------------------------------

INSERT INTO commits (
    repository_id,
    sha,
    author,
    message
)
SELECT
    repository_id,
    'abc123',
    'alice',
    'Implement payment authorization'
FROM repositories
WHERE repository_name = 'payment-platform';

INSERT INTO commits (
    repository_id,
    sha,
    author,
    message
)
SELECT
    repository_id,
    'def456',
    'alice',
    'Harden authorization failure handling'
FROM repositories
WHERE repository_name = 'payment-platform';

-- ---------------------------------------------------------------------------
-- Pull Request
-- ---------------------------------------------------------------------------

INSERT INTO pull_requests (
    repository_id,
    number,
    title,
    author,
    source_branch,
    target_branch,
    head_commit_id,
    state
)
SELECT
    r.repository_id,
    42,
    'Harden payment authorization',
    'alice',
    'feature/payment-auth',
    'main',
    c.commit_id,
    'open'
FROM repositories r
JOIN commits c
    ON c.repository_id = r.repository_id
WHERE r.repository_name = 'payment-platform'
  AND c.sha = 'abc123';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    sequence_number
)
SELECT
    pr.pull_request_id,
    c.commit_id,
    1
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'abc123'
WHERE pr.number = 42;

-- ---------------------------------------------------------------------------
-- External CI source records
-- ---------------------------------------------------------------------------

INSERT INTO external_ci_builds (
    provider,
    external_build_key,
    commit_id,
    external_result
)
SELECT
    'AcmeCI',
    'build-9001',
    commit_id,
    'SUCCESS'
FROM commits
WHERE sha = 'abc123';

-- ---------------------------------------------------------------------------
-- Adapter-normalized checks
-- ---------------------------------------------------------------------------

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    commit_id,
    status,
    completed_at
)
SELECT
    pr.pull_request_id,
    'unit-tests',
    c.commit_id,
    'passing',
    CURRENT_TIMESTAMP
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'abc123'
WHERE pr.number = 42;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    commit_id,
    status,
    completed_at
)
SELECT
    pr.pull_request_id,
    'security-scan',
    c.commit_id,
    'passing',
    CURRENT_TIMESTAMP
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'abc123'
WHERE pr.number = 42;

-- ---------------------------------------------------------------------------
-- Code review records
-- ---------------------------------------------------------------------------

INSERT INTO reviews (
    pull_request_id,
    reviewer,
    decision,
    reviewed_commit_id,
    body
)
SELECT
    pr.pull_request_id,
    'bob',
    'approve',
    c.commit_id,
    'Authorization boundaries are clear.'
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'abc123'
WHERE pr.number = 42;

INSERT INTO reviews (
    pull_request_id,
    reviewer,
    decision,
    reviewed_commit_id,
    body
)
SELECT
    pr.pull_request_id,
    'carol',
    'approve',
    c.commit_id,
    'Failure handling is acceptable.'
FROM pull_requests pr
JOIN commits c
    ON c.sha = 'abc123'
WHERE pr.number = 42;

INSERT INTO review_comments (
    review_id,
    file_path,
    line_number,
    body,
    resolved
)
SELECT
    review_id,
    'src/payment/authorization.py',
    87,
    'Please document the rejected-transaction path.',
    TRUE
FROM reviews
WHERE reviewer = 'bob'
  AND pull_request_id = (
      SELECT pull_request_id
      FROM pull_requests
      WHERE number = 42
  );

-- ---------------------------------------------------------------------------
-- Observer event records
-- ---------------------------------------------------------------------------

INSERT INTO repository_events (
    repository_id,
    pull_request_id,
    event_type,
    actor,
    payload
)
SELECT
    pr.repository_id,
    pr.pull_request_id,
    event_type,
    actor,
    payload
FROM pull_requests pr
CROSS JOIN (
    VALUES
        (
            'review_requested',
            'alice',
            '{"reviewers":["bob","carol"]}'::jsonb
        ),
        (
            'status_updated',
            'ci-bot',
            '{"provider":"AcmeCI","status":"passing"}'::jsonb
        ),
        (
            'review_submitted',
            'bob',
            '{"decision":"approve"}'::jsonb
        ),
        (
            'review_submitted',
            'carol',
            '{"decision":"approve"}'::jsonb
        )
) AS events(event_type, actor, payload)
WHERE pr.number = 42;

-- ---------------------------------------------------------------------------
-- Strategy-style merge eligibility query
--
-- The query evaluates the production branch policy without assuming that
-- "has a review" means "has an approval". It checks the current head commit,
-- eligible reviewers, required checks, and unresolved discussions.
-- ---------------------------------------------------------------------------

WITH current_pr AS (
    SELECT
        pr.pull_request_id,
        pr.repository_id,
        pr.target_branch,
        pr.head_commit_id
    FROM pull_requests pr
    WHERE pr.number = 42
      AND pr.state = 'open'
),
policy AS (
    SELECT
        bp.policy_id,
        bp.required_approvals,
        bp.require_conversation_resolution
    FROM branch_protection_policies bp
    JOIN branches b
        ON b.branch_id = bp.branch_id
    JOIN current_pr pr
        ON pr.repository_id = b.repository_id
       AND pr.target_branch = b.branch_name
),
approval_count AS (
    SELECT COUNT(DISTINCT r.reviewer) AS approvals
    FROM reviews r
    JOIN current_pr pr
        ON pr.pull_request_id = r.pull_request_id
    JOIN protected_reviewers eligible
        ON eligible.policy_id = (
            SELECT policy_id FROM policy
        )
       AND eligible.username = r.reviewer
    WHERE r.reviewed_commit_id = pr.head_commit_id
      AND r.decision = 'approve'
),
required_checks AS (
    SELECT
        COUNT(*) AS required_count,
        COUNT(sc.status_check_id)
            FILTER (WHERE sc.status = 'passing') AS passing_count
    FROM required_status_checks required
    LEFT JOIN current_pr pr
        ON TRUE
    LEFT JOIN status_checks sc
        ON sc.pull_request_id = pr.pull_request_id
       AND sc.commit_id = pr.head_commit_id
       AND sc.check_name = required.check_name
    WHERE required.policy_id = (
        SELECT policy_id FROM policy
    )
),
unresolved_conversations AS (
    SELECT COUNT(*) AS unresolved_count
    FROM review_comments rc
    JOIN reviews r
        ON r.review_id = rc.review_id
    JOIN current_pr pr
        ON pr.pull_request_id = r.pull_request_id
    WHERE rc.resolved = FALSE
)
SELECT
    pr.pull_request_id,
    approval_count.approvals,
    policy.required_approvals,
    required_checks.required_count,
    required_checks.passing_count,
    unresolved_conversations.unresolved_count,
    (
        approval_count.approvals >= policy.required_approvals
        AND required_checks.passing_count = required_checks.required_count
        AND (
            NOT policy.require_conversation_resolution
            OR unresolved_conversations.unresolved_count = 0
        )
    ) AS merge_eligible
FROM current_pr pr
CROSS JOIN policy
CROSS JOIN approval_count
CROSS JOIN required_checks
CROSS JOIN unresolved_conversations;

-- ---------------------------------------------------------------------------
-- Review quality query
-- ---------------------------------------------------------------------------
SELECT
    r.reviewer,
    COUNT(*) AS reviews_submitted,
    COUNT(*) FILTER (
        WHERE r.decision = 'approve'
    ) AS approvals,
    COUNT(*) FILTER (
        WHERE r.decision = 'request_changes'
    ) AS change_requests,
    COUNT(rc.comment_id) AS comments
FROM reviews r
LEFT JOIN review_comments rc
    ON rc.review_id = r.review_id
GROUP BY r.reviewer
ORDER BY r.reviewer;

-- ---------------------------------------------------------------------------
-- Observer event stream
-- ---------------------------------------------------------------------------
SELECT
    event_type,
    actor,
    created_at,
    payload
FROM repository_events
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE number = 42
)
ORDER BY created_at, event_id;

-- ---------------------------------------------------------------------------
-- Transactional governance operation
--
-- The transaction demonstrates a safe database-level state transition:
-- re-evaluate the current state, then mark the Pull Request merged only when
-- all required production conditions are satisfied.
-- ---------------------------------------------------------------------------

BEGIN;

SELECT
    pr.pull_request_id,
    pr.state,
    pr.mergeable,
    bp.required_approvals
FROM pull_requests pr
JOIN branches b
    ON b.repository_id = pr.repository_id
   AND b.branch_name = pr.target_branch
JOIN branch_protection_policies bp
    ON bp.branch_id = b.branch_id
WHERE pr.number = 42
FOR UPDATE;

-- The UPDATE is deliberately conditional. If the policy requirements are
-- no longer satisfied because data changed between evaluation and mutation,
-- zero rows are updated and the Pull Request remains open.
WITH eligible AS (
    SELECT pr.pull_request_id
    FROM pull_requests pr
    JOIN branches b
        ON b.repository_id = pr.repository_id
       AND b.branch_name = pr.target_branch
    JOIN branch_protection_policies bp
        ON bp.branch_id = b.branch_id
    WHERE pr.number = 42
      AND pr.state = 'open'
      AND pr.mergeable = TRUE
      AND (
          SELECT COUNT(DISTINCT r.reviewer)
          FROM reviews r
          JOIN protected_reviewers protected
            ON protected.policy_id = bp.policy_id
           AND protected.username = r.reviewer
          WHERE r.pull_request_id = pr.pull_request_id
            AND r.reviewed_commit_id = pr.head_commit_id
            AND r.decision = 'approve'
      ) >= bp.required_approvals
      AND NOT EXISTS (
          SELECT 1
          FROM required_status_checks required
          WHERE required.policy_id = bp.policy_id
            AND NOT EXISTS (
                SELECT 1
                FROM status_checks sc
                WHERE sc.pull_request_id = pr.pull_request_id
                  AND sc.commit_id = pr.head_commit_id
                  AND sc.check_name = required.check_name
                  AND sc.status = 'passing'
            )
      )
      AND (
          bp.require_conversation_resolution = FALSE
          OR NOT EXISTS (
              SELECT 1
              FROM review_comments rc
              JOIN reviews r
                ON r.review_id = rc.review_id
              WHERE r.pull_request_id = pr.pull_request_id
                AND rc.resolved = FALSE
          )
      )
)
UPDATE pull_requests pr
SET state = 'merged'
FROM eligible
WHERE pr.pull_request_id = eligible.pull_request_id;

INSERT INTO repository_events (
    repository_id,
    pull_request_id,
    event_type,
    actor,
    payload
)
SELECT
    pr.repository_id,
    pr.pull_request_id,
    'merged',
    'release-bot',
    '{"strategy":"protected-main"}'::jsonb
FROM pull_requests pr
WHERE pr.number = 42
  AND pr.state = 'merged';

COMMIT;

-- ---------------------------------------------------------------------------
-- Final state inspection
-- ---------------------------------------------------------------------------

SELECT
    repository_name,
    number,
    title,
    source_branch,
    target_branch,
    state,
    mergeable
FROM pull_requests pr
JOIN repositories r
    ON r.repository_id = pr.repository_id
WHERE pr.number = 42;
