DROP SCHEMA IF EXISTS cache_demo CASCADE;
CREATE SCHEMA cache_demo;

SET search_path TO cache_demo, public;

-- The database represents the source of truth separately from cached data.
CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE branches (
    branch_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    is_protected BOOLEAN NOT NULL DEFAULT FALSE,
    head_commit_sha TEXT,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_sha TEXT PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    author_name TEXT NOT NULL,
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

ALTER TABLE branches
    ADD CONSTRAINT branches_head_commit_fk
    FOREIGN KEY (head_commit_sha)
    REFERENCES commits(commit_sha)
    DEFERRABLE INITIALLY DEFERRED;

CREATE TABLE pull_requests (
    pull_request_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL
        CHECK (state IN ('draft', 'open', 'closed', 'merged')),
    source_synchronized BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    closed_at TIMESTAMPTZ,
    CHECK (source_branch_id <> target_branch_id)
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    commit_sha TEXT NOT NULL
        REFERENCES commits(commit_sha),
    commit_order INTEGER NOT NULL CHECK (commit_order > 0),
    PRIMARY KEY (pull_request_id, commit_sha),
    UNIQUE (pull_request_id, commit_order)
);

CREATE TABLE reviewers (
    reviewer_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE reviews (
    review_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL
        REFERENCES reviewers(reviewer_id),
    review_state TEXT NOT NULL
        CHECK (
            review_state IN (
                'commented',
                'approved',
                'changes_requested',
                'dismissed'
            )
        ),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    commit_sha TEXT REFERENCES commits(commit_sha),
    stale BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE review_comments (
    comment_id BIGSERIAL PRIMARY KEY,
    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER NOT NULL CHECK (line_number > 0),
    body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE status_checks (
    status_check_id BIGSERIAL PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('pending', 'passed', 'failed')),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGSERIAL PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id) ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 1
        CHECK (required_approvals >= 0),
    require_successful_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_resolved_conversations BOOLEAN NOT NULL DEFAULT TRUE,
    prevent_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    prevent_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE cache_entries (
    cache_key TEXT PRIMARY KEY,
    resource_type TEXT NOT NULL,
    resource_id BIGINT NOT NULL,
    payload JSONB NOT NULL,
    version BIGINT NOT NULL CHECK (version > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    invalidated_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);

CREATE TABLE cache_invalidation_events (
    invalidation_id BIGSERIAL PRIMARY KEY,
    cache_key TEXT NOT NULL,
    reason TEXT NOT NULL
        CHECK (
            reason IN (
                'explicit',
                'source_update',
                'ttl_expired',
                'manual'
            )
        ),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX idx_pr_target_state
    ON pull_requests(target_branch_id, state);

CREATE INDEX idx_reviews_pr_state
    ON reviews(pull_request_id, review_state, stale);

CREATE INDEX idx_status_checks_pr_status
    ON status_checks(pull_request_id, status);

CREATE INDEX idx_cache_expiration
    ON cache_entries(expires_at)
    WHERE invalidated_at IS NULL;

CREATE INDEX idx_cache_resource
    ON cache_entries(resource_type, resource_id);

CREATE OR REPLACE FUNCTION prevent_invalid_cache_ttl()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.expires_at <= NEW.created_at THEN
        RAISE EXCEPTION
            'Cache entry expiration must be after creation time';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_cache_valid_ttl
BEFORE INSERT OR UPDATE ON cache_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_invalid_cache_ttl();

CREATE OR REPLACE FUNCTION invalidate_cache_after_source_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE cache_entries
       SET invalidated_at = clock_timestamp()
     WHERE resource_type = TG_ARGV[0]
       AND resource_id = NEW.pull_request_id
       AND invalidated_at IS NULL;

    INSERT INTO cache_invalidation_events(cache_key, reason)
    SELECT cache_key, 'source_update'
      FROM cache_entries
     WHERE resource_type = TG_ARGV[0]
       AND resource_id = NEW.pull_request_id
       AND invalidated_at IS NOT NULL
       AND invalidated_at >= clock_timestamp() - INTERVAL '1 second';

    RETURN NEW;
END;
$$;

INSERT INTO repositories(repository_name)
VALUES ('cache-governance-demo');

INSERT INTO commits(
    commit_sha,
    repository_id,
    author_name,
    message
)
SELECT
    'a1b2c3',
    repository_id,
    'developer-1',
    'Implement cache-aside reads'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO commits(
    commit_sha,
    repository_id,
    author_name,
    message
)
SELECT
    'd4e5f6',
    repository_id,
    'developer-1',
    'Add TTL expiration'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO commits(
    commit_sha,
    repository_id,
    author_name,
    message
)
SELECT
    '111aaa',
    repository_id,
    'developer-2',
    'Add explicit cache invalidation'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO branches(
    repository_id,
    branch_name,
    is_protected,
    head_commit_sha
)
SELECT
    repository_id,
    'main',
    TRUE,
    'd4e5f6'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO branches(
    repository_id,
    branch_name,
    is_protected,
    head_commit_sha
)
SELECT
    repository_id,
    'feature/cache-aside',
    FALSE,
    'd4e5f6'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO branches(
    repository_id,
    branch_name,
    is_protected,
    head_commit_sha
)
SELECT
    repository_id,
    'feature/cache-invalidation',
    FALSE,
    '111aaa'
FROM repositories
WHERE repository_name = 'cache-governance-demo';

INSERT INTO reviewers(username)
VALUES
    ('reviewer-1'),
    ('reviewer-2'),
    ('reviewer-3');

INSERT INTO branch_protection_policies(
    branch_id,
    required_approvals,
    require_successful_checks,
    require_resolved_conversations,
    prevent_direct_push,
    prevent_force_push,
    allow_administrator_bypass
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    FALSE
FROM branches
WHERE branch_name = 'main';

INSERT INTO pull_requests(
    repository_id,
    source_branch_id,
    target_branch_id,
    title,
    state,
    source_synchronized
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    'Implement cache-aside workflow',
    'open',
    TRUE
FROM repositories r
JOIN branches source
  ON source.repository_id = r.repository_id
 AND source.branch_name = 'feature/cache-aside'
JOIN branches target
  ON target.repository_id = r.repository_id
 AND target.branch_name = 'main'
WHERE r.repository_name = 'cache-governance-demo';

INSERT INTO pull_request_commits(
    pull_request_id,
    commit_sha,
    commit_order
)
SELECT
    pr.pull_request_id,
    c.commit_sha,
    ROW_NUMBER() OVER (ORDER BY c.commit_sha)
FROM pull_requests pr
JOIN commits c
  ON c.commit_sha IN ('a1b2c3', 'd4e5f6')
WHERE pr.title = 'Implement cache-aside workflow';

INSERT INTO reviews(
    pull_request_id,
    reviewer_id,
    review_state,
    commit_sha,
    stale
)
SELECT
    pr.pull_request_id,
    r.reviewer_id,
    'approved',
    'd4e5f6',
    FALSE
FROM pull_requests pr
CROSS JOIN reviewers r
WHERE pr.title = 'Implement cache-aside workflow'
  AND r.username IN ('reviewer-1', 'reviewer-2');

INSERT INTO review_comments(
    review_id,
    file_path,
    line_number,
    body,
    resolved
)
SELECT
    review_id,
    'cache_service.py',
    87,
    'Validate TTL before inserting the cache entry.',
    TRUE
FROM reviews
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    WHERE title = 'Implement cache-aside workflow'
)
LIMIT 1;

INSERT INTO status_checks(
    pull_request_id,
    check_name,
    status,
    completed_at
)
SELECT
    pull_request_id,
    check_name,
    'passed',
    clock_timestamp()
FROM pull_requests
CROSS JOIN (
    VALUES
        ('unit-tests'),
        ('integration-tests'),
        ('security-scan')
) AS checks(check_name)
WHERE title = 'Implement cache-aside workflow';

INSERT INTO pull_requests(
    repository_id,
    source_branch_id,
    target_branch_id,
    title,
    state,
    source_synchronized
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    'Implement cache invalidation',
    'open',
    TRUE
FROM repositories r
JOIN branches source
  ON source.repository_id = r.repository_id
 AND source.branch_name = 'feature/cache-invalidation'
JOIN branches target
  ON target.repository_id = r.repository_id
 AND target.branch_name = 'main'
WHERE r.repository_name = 'cache-governance-demo';

INSERT INTO reviews(
    pull_request_id,
    reviewer_id,
    review_state,
    commit_sha,
    stale
)
SELECT
    pr.pull_request_id,
    r.reviewer_id,
    'approved',
    '111aaa',
    CASE
        WHEN r.username = 'reviewer-1' THEN TRUE
        ELSE FALSE
    END
FROM pull_requests pr
CROSS JOIN reviewers r
WHERE pr.title = 'Implement cache invalidation'
  AND r.username IN ('reviewer-1', 'reviewer-2');

INSERT INTO status_checks(
    pull_request_id,
    check_name,
    status,
    completed_at
)
SELECT
    pull_request_id,
    'unit-tests',
    'passed',
    clock_timestamp()
FROM pull_requests
WHERE title = 'Implement cache invalidation';

-- A cache-aside entry represents a temporary copy, not authoritative data.
INSERT INTO cache_entries(
    cache_key,
    resource_type,
    resource_id,
    payload,
    version,
    created_at,
    expires_at
)
VALUES
(
    'pr:1',
    'pull_request',
    1,
    '{"title":"Implement cache-aside workflow","state":"open"}'::jsonb,
    1,
    clock_timestamp(),
    clock_timestamp() + INTERVAL '5 minutes'
);

-- Cache hits can be represented by a non-expired entry.
SELECT
    cache_key,
    payload,
    version,
    expires_at,
    CASE
        WHEN invalidated_at IS NOT NULL THEN 'invalidated'
        WHEN expires_at <= clock_timestamp() THEN 'expired'
        ELSE 'fresh'
    END AS cache_state
FROM cache_entries
ORDER BY cache_key;

-- Detect entries that have exceeded their TTL.
SELECT
    cache_key,
    resource_type,
    resource_id,
    expires_at
FROM cache_entries
WHERE invalidated_at IS NULL
  AND expires_at <= clock_timestamp();

-- Explicit invalidation is useful after a source-of-truth update.
UPDATE cache_entries
SET invalidated_at = clock_timestamp()
WHERE cache_key = 'pr:1'
  AND invalidated_at IS NULL;

INSERT INTO cache_invalidation_events(cache_key, reason)
VALUES ('pr:1', 'explicit');

-- Approval evaluation counts distinct, active, non-stale approvers.
WITH approval_counts AS (
    SELECT
        pr.pull_request_id,
        COUNT(DISTINCT r.reviewer_id)
            FILTER (
                WHERE rv.review_state = 'approved'
                  AND rv.stale = FALSE
                  AND r.active = TRUE
            ) AS approval_count
    FROM pull_requests pr
    LEFT JOIN reviews rv
      ON rv.pull_request_id = pr.pull_request_id
    LEFT JOIN reviewers r
      ON r.reviewer_id = rv.reviewer_id
    GROUP BY pr.pull_request_id
),
check_results AS (
    SELECT
        pr.pull_request_id,
        COUNT(*) FILTER (
            WHERE sc.status = 'passed'
        ) AS passed_checks,
        COUNT(*) AS total_checks
    FROM pull_requests pr
    LEFT JOIN status_checks sc
      ON sc.pull_request_id = pr.pull_request_id
    GROUP BY pr.pull_request_id
)
SELECT
    pr.pull_request_id,
    pr.title,
    bp.required_approvals,
    ac.approval_count,
    cr.passed_checks,
    cr.total_checks,
    CASE
        WHEN pr.state = 'open'
         AND pr.source_synchronized
         AND ac.approval_count >= bp.required_approvals
         AND (
             NOT bp.require_successful_checks
             OR (
                 cr.total_checks > 0
                 AND cr.passed_checks = cr.total_checks
             )
         )
         AND (
             NOT bp.require_resolved_conversations
             OR NOT EXISTS (
                 SELECT 1
                 FROM review_comments rc
                 JOIN reviews rv
                   ON rv.review_id = rc.review_id
                WHERE rv.pull_request_id = pr.pull_request_id
                  AND rc.resolved = FALSE
             )
         )
        THEN 'eligible'
        ELSE 'blocked'
    END AS merge_eligibility
FROM pull_requests pr
JOIN branches target
  ON target.branch_id = pr.target_branch_id
JOIN branch_protection_policies bp
  ON bp.branch_id = target.branch_id
JOIN approval_counts ac
  ON ac.pull_request_id = pr.pull_request_id
JOIN check_results cr
  ON cr.pull_request_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

-- Report the operational distinction between source state and cache state.
SELECT
    pr.pull_request_id,
    pr.title,
    pr.state AS source_state,
    ce.cache_key,
    ce.version AS cached_version,
    ce.created_at,
    ce.expires_at,
    ce.invalidated_at
FROM pull_requests pr
LEFT JOIN cache_entries ce
  ON ce.resource_type = 'pull_request'
 AND ce.resource_id = pr.pull_request_id
ORDER BY pr.pull_request_id;

-- Transactional source update followed by cache invalidation.
BEGIN;

UPDATE pull_requests
SET source_synchronized = TRUE
WHERE pull_request_id = 1;

UPDATE cache_entries
SET invalidated_at = clock_timestamp()
WHERE resource_type = 'pull_request'
  AND resource_id = 1
  AND invalidated_at IS NULL;

INSERT INTO cache_invalidation_events(cache_key, reason)
SELECT cache_key, 'source_update'
FROM cache_entries
WHERE resource_type = 'pull_request'
  AND resource_id = 1
  AND invalidated_at IS NOT NULL;

COMMIT;
