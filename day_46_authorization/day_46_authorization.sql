-- PostgreSQL 15+
-- Repository authorization, RBAC, permission evaluation, and access auditing.
-- Execute in a disposable learning database. The script recreates its schema.

BEGIN;

DROP SCHEMA IF EXISTS authorization_lab CASCADE;
CREATE SCHEMA authorization_lab;
SET search_path TO authorization_lab, public;

CREATE TABLE app_users (
    user_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    department    TEXT NOT NULL,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(trim(username)) > 0),
    CHECK (length(trim(department)) > 0)
);

CREATE TABLE roles (
    role_id       BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_name     TEXT NOT NULL UNIQUE,
    description   TEXT NOT NULL,
    CHECK (length(trim(role_name)) > 0)
);

CREATE TABLE permissions (
    permission_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_type TEXT NOT NULL,
    action_name   TEXT NOT NULL,
    UNIQUE (resource_type, action_name),
    CHECK (length(trim(resource_type)) > 0),
    CHECK (length(trim(action_name)) > 0)
);

CREATE TABLE role_permissions (
    role_id       BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(permission_id)
                                  ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Role inheritance is explicit. A cycle check in the application and the
-- recursive resolution query prevent unbounded inheritance traversal.
CREATE TABLE role_inheritance (
    child_role_id  BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    parent_role_id BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    PRIMARY KEY (child_role_id, parent_role_id),
    CHECK (child_role_id <> parent_role_id)
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    assigned_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    assigned_by BIGINT REFERENCES app_users(user_id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    owner_user_id BIGINT NOT NULL REFERENCES app_users(user_id),
    environment TEXT NOT NULL CHECK (
        environment IN ('development', 'staging', 'production')
    ),
    classification TEXT NOT NULL CHECK (
        classification IN ('public', 'internal', 'restricted')
    ),
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    author_user_id BIGINT NOT NULL REFERENCES app_users(user_id),
    title TEXT NOT NULL,
    source_branch TEXT NOT NULL,
    target_branch TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open' CHECK (
        state IN ('draft', 'open', 'closed', 'merged')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(trim(title)) > 0),
    CHECK (source_branch <> target_branch)
);

CREATE TABLE repository_commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    commit_sha CHAR(40) NOT NULL,
    author_user_id BIGINT NOT NULL REFERENCES app_users(user_id),
    committed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (repository_id, commit_sha)
);

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    commit_id BIGINT NOT NULL REFERENCES repository_commits(commit_id),
    PRIMARY KEY (pull_request_id, commit_id)
);

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    reviewer_user_id BIGINT NOT NULL REFERENCES app_users(user_id),
    review_state TEXT NOT NULL CHECK (
        review_state IN ('commented', 'approved', 'changes_requested', 'dismissed')
    ),
    reviewed_head_sha CHAR(40),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (pull_request_id, reviewer_user_id, submitted_at)
);

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    comment_body TEXT NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (line_number IS NULL OR line_number > 0),
    CHECK (length(trim(comment_body)) > 0)
);

CREATE TABLE status_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    commit_sha CHAR(40) NOT NULL,
    check_state TEXT NOT NULL CHECK (
        check_state IN ('pending', 'success', 'failure', 'error')
    ),
    completed_at TIMESTAMPTZ,
    UNIQUE (pull_request_id, check_name, commit_sha)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id) ON DELETE CASCADE,
    branch_pattern TEXT NOT NULL,
    required_approvals INTEGER NOT NULL DEFAULT 1
        CHECK (required_approvals >= 0),
    require_status_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_conversation_resolution BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,
    allow_deletion BOOLEAN NOT NULL DEFAULT FALSE,
    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (length(trim(branch_pattern)) > 0),
    UNIQUE (repository_id, branch_pattern)
);

CREATE TABLE policy_required_checks (
    policy_id BIGINT NOT NULL
        REFERENCES branch_protection_policies(policy_id) ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    PRIMARY KEY (policy_id, check_name)
);

CREATE TABLE temporary_grants (
    grant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(permission_id),
    justification TEXT NOT NULL,
    granted_by BIGINT NOT NULL REFERENCES app_users(user_id),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at > created_at),
    CHECK (length(trim(justification)) > 0)
);

CREATE TABLE access_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id UUID NOT NULL,
    user_id BIGINT REFERENCES app_users(user_id),
    resource_type TEXT NOT NULL,
    resource_id BIGINT,
    action_name TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('allow', 'deny')),
    reason TEXT NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX idx_user_roles_role ON user_roles(role_id, user_id);
CREATE INDEX idx_role_inheritance_parent ON role_inheritance(parent_role_id);
CREATE INDEX idx_pull_requests_repo_state
    ON pull_requests(repository_id, state, target_branch);
CREATE INDEX idx_reviews_pr_state
    ON reviews(pull_request_id, review_state, submitted_at DESC);
CREATE INDEX idx_status_checks_pr_commit
    ON status_checks(pull_request_id, commit_sha, check_state);
CREATE INDEX idx_temporary_grants_user_expiry
    ON temporary_grants(user_id, expires_at)
    WHERE revoked_at IS NULL;
CREATE INDEX idx_access_audit_time
    ON access_audit(evaluated_at DESC);
CREATE INDEX idx_access_audit_denials
    ON access_audit(evaluated_at DESC)
    WHERE decision = 'deny';

INSERT INTO app_users (username, department, active) VALUES
    ('maya', 'engineering', TRUE),
    ('noah', 'security', TRUE),
    ('olivia', 'platform', TRUE),
    ('retired_account', 'engineering', FALSE);

INSERT INTO roles (role_name, description) VALUES
    ('reader', 'Read repository and pull request metadata'),
    ('developer', 'Modify repository content and open pull requests'),
    ('reviewer', 'Review and approve pull requests'),
    ('release_manager', 'Deploy and administer production releases'),
    ('security_admin', 'Perform security review and sensitive administration');

INSERT INTO permissions (resource_type, action_name) VALUES
    ('repository', 'read'),
    ('repository', 'write'),
    ('repository', 'deploy'),
    ('repository', 'delete'),
    ('pull_request', 'read'),
    ('pull_request', 'create'),
    ('pull_request', 'review'),
    ('pull_request', 'approve');

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM (VALUES
    ('reader', 'repository', 'read'),
    ('reader', 'pull_request', 'read'),
    ('developer', 'repository', 'write'),
    ('developer', 'pull_request', 'create'),
    ('reviewer', 'pull_request', 'review'),
    ('reviewer', 'pull_request', 'approve'),
    ('release_manager', 'repository', 'deploy'),
    ('release_manager', 'repository', 'delete'),
    ('security_admin', 'repository', 'read'),
    ('security_admin', 'repository', 'delete')
) AS mapping(role_name, resource_type, action_name)
JOIN roles r ON r.role_name = mapping.role_name
JOIN permissions p
  ON p.resource_type = mapping.resource_type
 AND p.action_name = mapping.action_name;

INSERT INTO role_inheritance (child_role_id, parent_role_id)
SELECT child.role_id, parent.role_id
FROM (VALUES ('developer', 'reader'), ('reviewer', 'reader'))
     AS inheritance(child_name, parent_name)
JOIN roles child ON child.role_name = inheritance.child_name
JOIN roles parent ON parent.role_name = inheritance.parent_name;

INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id
FROM (VALUES
    ('maya', 'developer'),
    ('noah', 'reviewer'),
    ('olivia', 'release_manager'),
    ('retired_account', 'reader')
) AS assignments(username, role_name)
JOIN app_users u ON u.username = assignments.username
JOIN roles r ON r.role_name = assignments.role_name;

INSERT INTO repositories (
    repository_name, owner_user_id, environment, classification
)
SELECT 'payments-service', user_id, 'production', 'restricted'
FROM app_users WHERE username = 'maya';

INSERT INTO pull_requests (
    repository_id, author_user_id, title, source_branch, target_branch, state
)
SELECT repository_id, owner_user_id,
       'Validate release authorization', 'feature/authorization',
       'main', 'open'
FROM repositories WHERE repository_name = 'payments-service';

INSERT INTO repository_commits (
    repository_id, commit_sha, author_user_id
)
SELECT repository_id,
       'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
       owner_user_id
FROM repositories WHERE repository_name = 'payments-service';

INSERT INTO pull_request_commits (pull_request_id, commit_id)
SELECT pr.pull_request_id, c.commit_id
FROM pull_requests pr
JOIN repositories r ON r.repository_id = pr.repository_id
JOIN repository_commits c ON c.repository_id = r.repository_id;

INSERT INTO reviews (
    pull_request_id, reviewer_user_id, review_state, reviewed_head_sha
)
SELECT pr.pull_request_id, u.user_id, 'approved',
       'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
FROM pull_requests pr
JOIN app_users u ON u.username = 'noah';

INSERT INTO review_comments (
    review_id, file_path, line_number, comment_body, resolved
)
SELECT review_id, 'src/authorization.py', 42,
       'Verify that inactive accounts are rejected before resource access.',
       TRUE
FROM reviews WHERE review_state = 'approved';

INSERT INTO status_checks (
    pull_request_id, check_name, commit_sha, check_state, completed_at
)
SELECT pull_request_id, check_name,
       'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'success',
       clock_timestamp()
FROM pull_requests
CROSS JOIN (VALUES ('unit-tests'), ('security-scan')) AS checks(check_name);

INSERT INTO branch_protection_policies (
    repository_id, branch_pattern, required_approvals,
    require_status_checks, require_conversation_resolution,
    require_linear_history, restrict_direct_push,
    allow_force_push, allow_deletion, allow_administrator_bypass
)
SELECT repository_id, 'main', 1, TRUE, TRUE, TRUE, TRUE,
       FALSE, FALSE, FALSE
FROM repositories WHERE repository_name = 'payments-service';

INSERT INTO policy_required_checks (policy_id, check_name)
SELECT policy_id, check_name
FROM branch_protection_policies
CROSS JOIN (VALUES ('unit-tests'), ('security-scan')) AS checks(check_name);

-- Temporary grants are narrowly scoped, justified, and time-limited.
INSERT INTO temporary_grants (
    user_id, permission_id, justification, granted_by, expires_at
)
SELECT recipient.user_id, p.permission_id,
       'Incident-approved deployment window',
       approver.user_id, clock_timestamp() + INTERVAL '15 minutes'
FROM app_users recipient
JOIN app_users approver ON approver.username = 'olivia'
JOIN permissions p
  ON p.resource_type = 'repository' AND p.action_name = 'deploy'
WHERE recipient.username = 'maya';

-- Effective permissions are resolved recursively. UNION rather than UNION ALL
-- removes duplicates and makes traversal terminate even if legacy data contains
-- a cycle that bypassed application-level validation.
CREATE VIEW effective_user_permissions AS
WITH RECURSIVE inherited_roles(user_id, role_id) AS (
    SELECT ur.user_id, ur.role_id
    FROM user_roles ur
    UNION
    SELECT ir.user_id, ri.parent_role_id
    FROM inherited_roles ir
    JOIN role_inheritance ri ON ri.child_role_id = ir.role_id
)
SELECT DISTINCT
    u.user_id,
    u.username,
    r.role_name,
    p.permission_id,
    p.resource_type,
    p.action_name
FROM inherited_roles ir
JOIN app_users u ON u.user_id = ir.user_id
JOIN roles r ON r.role_id = ir.role_id
JOIN role_permissions rp ON rp.role_id = ir.role_id
JOIN permissions p ON p.permission_id = rp.permission_id
WHERE u.active;

-- A review is current only when it evaluates the latest commit associated
-- with the pull request. Dismissed reviews never count as approvals.
CREATE VIEW current_pull_request_approvals AS
WITH latest_commit AS (
    SELECT
        prc.pull_request_id,
        c.commit_sha,
        row_number() OVER (
            PARTITION BY prc.pull_request_id
            ORDER BY c.committed_at DESC, c.commit_id DESC
        ) AS position
    FROM pull_request_commits prc
    JOIN repository_commits c ON c.commit_id = prc.commit_id
),
latest_reviewer_decision AS (
    SELECT DISTINCT ON (rv.pull_request_id, rv.reviewer_user_id)
        rv.pull_request_id,
        rv.reviewer_user_id,
        rv.review_state,
        rv.reviewed_head_sha,
        rv.submitted_at
    FROM reviews rv
    ORDER BY rv.pull_request_id, rv.reviewer_user_id,
             rv.submitted_at DESC, rv.review_id DESC
)
SELECT
    pr.pull_request_id,
    COUNT(DISTINCT latest.reviewer_user_id)
        FILTER (
            WHERE latest.review_state = 'approved'
              AND latest.reviewed_head_sha = lc.commit_sha
              AND reviewer.active
              AND latest.reviewer_user_id <> pr.author_user_id
        ) AS current_approval_count
FROM pull_requests pr
LEFT JOIN latest_commit lc
       ON lc.pull_request_id = pr.pull_request_id AND lc.position = 1
LEFT JOIN latest_reviewer_decision latest
       ON latest.pull_request_id = pr.pull_request_id
LEFT JOIN app_users reviewer ON reviewer.user_id = latest.reviewer_user_id
GROUP BY pr.pull_request_id;

-- This view exposes branch-protection failures rather than pretending that
-- an assigned permission alone makes a pull request mergeable.
CREATE VIEW pull_request_merge_eligibility AS
SELECT
    pr.pull_request_id,
    r.repository_name,
    pr.target_branch,
    pr.state,
    COALESCE(approvals.current_approval_count, 0) AS current_approvals,
    COALESCE(policy.required_approvals, 0) AS required_approvals,
    CASE
        WHEN pr.state <> 'open' THEN FALSE
        WHEN NOT author.active THEN FALSE
        WHEN r.archived THEN FALSE
        WHEN COALESCE(approvals.current_approval_count, 0)
             < COALESCE(policy.required_approvals, 0) THEN FALSE
        WHEN COALESCE(policy.require_status_checks, FALSE)
             AND EXISTS (
                 SELECT 1
                 FROM policy_required_checks required
                 WHERE required.policy_id = policy.policy_id
                   AND NOT EXISTS (
                       SELECT 1
                       FROM status_checks sc
                       WHERE sc.pull_request_id = pr.pull_request_id
                         AND sc.check_name = required.check_name
                         AND sc.check_state = 'success'
                         AND sc.commit_sha = (
                             SELECT c.commit_sha
                             FROM pull_request_commits prc
                             JOIN repository_commits c
                               ON c.commit_id = prc.commit_id
                             WHERE prc.pull_request_id = pr.pull_request_id
                             ORDER BY c.committed_at DESC, c.commit_id DESC
                             LIMIT 1
                         )
                   )
             ) THEN FALSE
        WHEN COALESCE(policy.require_conversation_resolution, FALSE)
             AND EXISTS (
                 SELECT 1
                 FROM review_comments rc
                 JOIN reviews rv ON rv.review_id = rc.review_id
                 WHERE rv.pull_request_id = pr.pull_request_id
                   AND NOT rc.resolved
             ) THEN FALSE
        ELSE TRUE
    END AS merge_eligible
FROM pull_requests pr
JOIN repositories r ON r.repository_id = pr.repository_id
JOIN app_users author ON author.user_id = pr.author_user_id
LEFT JOIN branch_protection_policies policy
       ON policy.repository_id = pr.repository_id
      AND policy.branch_pattern = pr.target_branch
LEFT JOIN current_pull_request_approvals approvals
       ON approvals.pull_request_id = pr.pull_request_id;

-- Record access outcomes with a caller-supplied request identifier.
CREATE FUNCTION record_access_decision(
    p_request_id UUID,
    p_username TEXT,
    p_resource_type TEXT,
    p_resource_id BIGINT,
    p_action TEXT,
    p_decision TEXT,
    p_reason TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_user_id BIGINT;
    v_audit_id BIGINT;
BEGIN
    IF p_decision NOT IN ('allow', 'deny') THEN
        RAISE EXCEPTION 'Invalid access decision: %', p_decision;
    END IF;

    SELECT user_id INTO v_user_id
    FROM app_users WHERE username = p_username;

    INSERT INTO access_audit (
        request_id, user_id, resource_type, resource_id,
        action_name, decision, reason
    )
    VALUES (
        p_request_id, v_user_id, p_resource_type, p_resource_id,
        p_action, p_decision, p_reason
    )
    RETURNING audit_id INTO v_audit_id;

    RETURN v_audit_id;
END;
$$;

-- Evaluate repository permissions with explicit active-user enforcement.
CREATE FUNCTION check_repository_access(
    p_username TEXT,
    p_repository_name TEXT,
    p_action TEXT
) RETURNS TABLE (
    allowed BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_user app_users%ROWTYPE;
    v_repository repositories%ROWTYPE;
    v_permission_exists BOOLEAN;
    v_grant_exists BOOLEAN;
BEGIN
    SELECT * INTO v_user
    FROM app_users WHERE username = p_username;

    IF NOT FOUND OR NOT v_user.active THEN
        RETURN QUERY SELECT FALSE, 'unknown_or_inactive_user'::TEXT;
        RETURN;
    END IF;

    SELECT * INTO v_repository
    FROM repositories WHERE repository_name = p_repository_name;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'unknown_repository'::TEXT;
        RETURN;
    END IF;

    IF v_repository.archived AND p_action <> 'read' THEN
        RETURN QUERY SELECT FALSE, 'repository_archived'::TEXT;
        RETURN;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM effective_user_permissions eup
        WHERE eup.user_id = v_user.user_id
          AND eup.resource_type = 'repository'
          AND eup.action_name = p_action
    ) INTO v_permission_exists;

    SELECT EXISTS (
        SELECT 1
        FROM temporary_grants tg
        JOIN permissions p ON p.permission_id = tg.permission_id
        WHERE tg.user_id = v_user.user_id
          AND tg.revoked_at IS NULL
          AND tg.expires_at > clock_timestamp()
          AND p.resource_type = 'repository'
          AND p.action_name = p_action
    ) INTO v_grant_exists;

    IF NOT v_permission_exists AND NOT v_grant_exists THEN
        RETURN QUERY SELECT FALSE, 'missing_permission'::TEXT;
        RETURN;
    END IF;

    IF v_repository.classification = 'restricted'
       AND p_action = 'read'
       AND v_user.department <> 'security'
       AND v_repository.owner_user_id <> v_user.user_id THEN
        RETURN QUERY SELECT FALSE, 'restricted_resource_policy'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'permission_granted'::TEXT;
END;
$$;

-- Inspect inherited permissions, including the reader permissions inherited
-- by developer and reviewer.
SELECT username, role_name, resource_type, action_name
FROM effective_user_permissions
ORDER BY username, role_name, resource_type, action_name;

-- Inspect approval freshness and branch-protection eligibility.
SELECT *
FROM current_pull_request_approvals
ORDER BY pull_request_id;

SELECT *
FROM pull_request_merge_eligibility
ORDER BY pull_request_id;

-- Compare permitted and denied repository operations.
SELECT 'maya' AS username, access.*
FROM check_repository_access('maya', 'payments-service', 'read') AS access
UNION ALL
SELECT 'noah', access.*
FROM check_repository_access('noah', 'payments-service', 'write') AS access
UNION ALL
SELECT 'olivia', access.*
FROM check_repository_access('olivia', 'payments-service', 'deploy') AS access
UNION ALL
SELECT 'retired_account', access.*
FROM check_repository_access('retired_account', 'payments-service', 'read')
    AS access;

-- Demonstrate integrity enforcement. The exception block rolls back only the
-- invalid assignment, allowing the rest of the transaction to continue.
DO $$
BEGIN
    BEGIN
        INSERT INTO user_roles (user_id, role_id)
        VALUES (-999, -999);
    EXCEPTION WHEN foreign_key_violation THEN
        RAISE NOTICE 'Rejected nonexistent user and role references.';
    END;

    BEGIN
        INSERT INTO branch_protection_policies (
            repository_id, branch_pattern, required_approvals
        )
        SELECT repository_id, 'main', -1
        FROM repositories
        WHERE repository_name = 'payments-service';
    EXCEPTION WHEN check_violation THEN
        RAISE NOTICE 'Rejected a negative approval requirement.';
    END;
END;
$$;

SELECT record_access_decision(
    gen_random_uuid(),
    'maya',
    'repository',
    (SELECT repository_id FROM repositories
     WHERE repository_name = 'payments-service'),
    'read',
    'allow',
    'Inherited reader permission'
);

SELECT record_access_decision(
    gen_random_uuid(),
    'noah',
    'repository',
    (SELECT repository_id FROM repositories
     WHERE repository_name = 'payments-service'),
    'write',
    'deny',
    'No repository write permission'
);

SELECT decision, reason, COUNT(*) AS event_count
FROM access_audit
GROUP BY decision, reason
ORDER BY decision, reason;

COMMIT;
