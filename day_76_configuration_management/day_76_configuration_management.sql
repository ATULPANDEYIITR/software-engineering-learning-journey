-- ============================================================
-- CONFIGURATION MANAGEMENT DATABASE
-- Environment Variables, Secrets and Configuration Governance
--
-- PostgreSQL 15+
--
-- Includes:
--   1. Environment and repository modeling
--   2. Typed configuration definitions
--   3. Environment-specific configuration values
--   4. Secret references and metadata
--   5. Configuration versions and changesets
--   6. Review decisions and approvals
--   7. Automated validation checks
--   8. Configuration policies
--   9. Deployment eligibility
--  10. Audit logging and rollback records
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS config_mgmt;

SET search_path TO config_mgmt, public;

-- ============================================================
-- ENUMERATIONS
-- ============================================================

CREATE TYPE environment_type AS ENUM (
    'development',
    'testing',
    'staging',
    'production'
);

CREATE TYPE configuration_type AS ENUM (
    'string',
    'integer',
    'numeric',
    'boolean',
    'json'
);

CREATE TYPE principal_role AS ENUM (
    'developer',
    'reviewer',
    'security_officer',
    'administrator'
);

CREATE TYPE change_state AS ENUM (
    'draft',
    'validated',
    'approved',
    'rejected',
    'deployed',
    'rolled_back'
);

CREATE TYPE review_state AS ENUM (
    'approved',
    'changes_requested',
    'commented',
    'dismissed'
);

CREATE TYPE check_state AS ENUM (
    'pending',
    'passed',
    'failed',
    'cancelled'
);

CREATE TYPE secret_status AS ENUM (
    'active',
    'rotating',
    'revoked',
    'expired'
);

-- ============================================================
-- REPOSITORIES AND PRINCIPALS
-- ============================================================

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_name VARCHAR(150) NOT NULL UNIQUE,

    description TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE principals (
    principal_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    username VARCHAR(100) NOT NULL UNIQUE,

    role principal_role NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE repository_members (
    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,

    principal_id BIGINT NOT NULL
        REFERENCES principals(principal_id)
        ON DELETE CASCADE,

    member_role principal_role NOT NULL,

    PRIMARY KEY (repository_id, principal_id)
);

-- ============================================================
-- ENVIRONMENTS AND BRANCHES
-- ============================================================

CREATE TABLE environments (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    environment_name environment_type NOT NULL UNIQUE,

    is_production BOOLEAN GENERATED ALWAYS AS (
        environment_name = 'production'
    ) STORED,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,

    branch_name VARCHAR(150) NOT NULL,

    head_commit VARCHAR(64) NOT NULL,

    revision BIGINT NOT NULL DEFAULT 1,

    protected BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(repository_id, branch_name),

    CHECK (revision > 0),

    CHECK (head_commit ~ '^[a-f0-9]{7,64}$')
);

CREATE INDEX idx_branches_repository
    ON branches(repository_id);

-- ============================================================
-- COMMITS
-- ============================================================

CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    commit_hash VARCHAR(64) NOT NULL,

    author_id BIGINT NOT NULL
        REFERENCES principals(principal_id),

    message TEXT NOT NULL,

    committed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(repository_id, commit_hash),

    CHECK (commit_hash ~ '^[a-f0-9]{7,64}$')
);

CREATE INDEX idx_commits_branch_date
    ON commits(branch_id, committed_at DESC);

-- ============================================================
-- CONFIGURATION DEFINITIONS
-- ============================================================

CREATE TABLE configuration_definitions (
    definition_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id)
        ON DELETE CASCADE,

    configuration_key VARCHAR(150) NOT NULL,

    data_type configuration_type NOT NULL,

    description TEXT,

    required BOOLEAN NOT NULL DEFAULT FALSE,

    sensitive BOOLEAN NOT NULL DEFAULT FALSE,

    default_value JSONB,

    minimum_numeric NUMERIC,

    maximum_numeric NUMERIC,

    allowed_values JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(repository_id, configuration_key),

    CHECK (
        configuration_key ~ '^[A-Z][A-Z0-9_]*$'
    ),

    CHECK (
        minimum_numeric IS NULL OR
        maximum_numeric IS NULL OR
        minimum_numeric <= maximum_numeric
    ),

    CHECK (
        default_value IS NULL OR
        jsonb_typeof(default_value) IN (
            'string',
            'number',
            'boolean',
            'object',
            'array'
        )
    )
);

CREATE INDEX idx_config_definitions_repository
    ON configuration_definitions(repository_id);

-- ============================================================
-- CONFIGURATION VALUES
--
-- Secret values are never stored in this table.
-- Sensitive configurations contain a reference instead.
-- ============================================================

CREATE TABLE configuration_values (
    configuration_value_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    definition_id BIGINT NOT NULL
        REFERENCES configuration_definitions(definition_id)
        ON DELETE CASCADE,

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    configuration_value JSONB,

    secret_reference VARCHAR(255),

    version BIGINT NOT NULL DEFAULT 1,

    updated_by BIGINT NOT NULL
        REFERENCES principals(principal_id),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(definition_id, environment_id),

    CHECK (version > 0),

    CHECK (
        NOT (
            configuration_value IS NOT NULL AND
            secret_reference IS NOT NULL
        )
    )
);

CREATE INDEX idx_configuration_environment
    ON configuration_values(environment_id, definition_id);

-- ============================================================
-- SECRET METADATA
--
-- No plaintext secret material is stored here.
-- secret_reference points to an external secret manager.
-- ============================================================

CREATE TABLE secret_metadata (
    secret_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    secret_name VARCHAR(150) NOT NULL,

    secret_reference VARCHAR(255) NOT NULL,

    status secret_status NOT NULL DEFAULT 'active',

    version INTEGER NOT NULL DEFAULT 1,

    last_rotated_at TIMESTAMPTZ,

    expires_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(
        repository_id,
        environment_id,
        secret_name
    ),

    CHECK (version > 0),

    CHECK (
        expires_at IS NULL OR
        last_rotated_at IS NULL OR
        expires_at > last_rotated_at
    )
);

CREATE INDEX idx_secrets_status
    ON secret_metadata(status, expires_at);

-- ============================================================
-- BRANCH PROTECTION POLICIES
-- ============================================================

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    branch_id BIGINT NOT NULL UNIQUE
        REFERENCES branches(branch_id)
        ON DELETE CASCADE,

    required_approvals INTEGER NOT NULL DEFAULT 1,

    require_security_approval BOOLEAN NOT NULL DEFAULT FALSE,

    require_tests BOOLEAN NOT NULL DEFAULT TRUE,

    require_secret_scan BOOLEAN NOT NULL DEFAULT TRUE,

    require_conversations_resolved BOOLEAN NOT NULL DEFAULT TRUE,

    require_linear_history BOOLEAN NOT NULL DEFAULT TRUE,

    allow_direct_push BOOLEAN NOT NULL DEFAULT FALSE,

    allow_force_push BOOLEAN NOT NULL DEFAULT FALSE,

    allow_branch_deletion BOOLEAN NOT NULL DEFAULT FALSE,

    allow_administrator_bypass BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (required_approvals >= 0)
);

-- ============================================================
-- PULL REQUESTS
-- ============================================================

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    repository_id BIGINT NOT NULL
        REFERENCES repositories(repository_id),

    source_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    target_branch_id BIGINT NOT NULL
        REFERENCES branches(branch_id),

    author_id BIGINT NOT NULL
        REFERENCES principals(principal_id),

    title VARCHAR(250) NOT NULL,

    description TEXT,

    state change_state NOT NULL DEFAULT 'draft',

    is_draft BOOLEAN NOT NULL DEFAULT TRUE,

    source_revision BIGINT NOT NULL,

    target_revision BIGINT NOT NULL,

    reviewed_revision BIGINT,

    source_synchronized BOOLEAN NOT NULL DEFAULT TRUE,

    has_merge_conflict BOOLEAN NOT NULL DEFAULT FALSE,

    linear_history BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (source_revision > 0),

    CHECK (target_revision > 0),

    CHECK (source_branch_id <> target_branch_id)
);

CREATE INDEX idx_pull_requests_target_state
    ON pull_requests(target_branch_id, state);

CREATE INDEX idx_pull_requests_author
    ON pull_requests(author_id, created_at DESC);

-- ============================================================
-- CHANGESETS
-- ============================================================

CREATE TABLE configuration_changesets (
    changeset_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,

    definition_id BIGINT NOT NULL
        REFERENCES configuration_definitions(definition_id),

    old_value JSONB,

    new_value JSONB,

    secret_reference VARCHAR(255),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(pull_request_id, definition_id),

    CHECK (
        NOT (
            new_value IS NOT NULL AND
            secret_reference IS NOT NULL
        )
    )
);

CREATE INDEX idx_changesets_pull_request
    ON configuration_changesets(pull_request_id);

-- ============================================================
-- PULL REQUEST COMMITS
-- ============================================================

CREATE TABLE pull_request_commits (
    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,

    commit_id BIGINT NOT NULL
        REFERENCES commits(commit_id),

    PRIMARY KEY(pull_request_id, commit_id)
);

-- ============================================================
-- REVIEW RECORDS
-- ============================================================

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,

    reviewer_id BIGINT NOT NULL
        REFERENCES principals(principal_id),

    review_status review_state NOT NULL,

    reviewed_revision BIGINT NOT NULL,

    review_comment TEXT,

    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(pull_request_id, reviewer_id, reviewed_revision)
);

CREATE INDEX idx_reviews_request_status
    ON reviews(pull_request_id, review_status);

CREATE INDEX idx_reviews_reviewer
    ON reviews(reviewer_id, submitted_at DESC);

-- ============================================================
-- REVIEW CONVERSATIONS AND INLINE COMMENTS
-- ============================================================

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    review_id BIGINT NOT NULL
        REFERENCES reviews(review_id)
        ON DELETE CASCADE,

    file_path TEXT NOT NULL,

    line_number INTEGER,

    comment_body TEXT NOT NULL,

    resolved BOOLEAN NOT NULL DEFAULT FALSE,

    resolved_by BIGINT
        REFERENCES principals(principal_id),

    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (line_number IS NULL OR line_number > 0),

    CHECK (
        (resolved = FALSE AND resolved_at IS NULL)
        OR
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

CREATE INDEX idx_review_comments_unresolved
    ON review_comments(review_id)
    WHERE resolved = FALSE;

-- ============================================================
-- AUTOMATED STATUS CHECKS
-- ============================================================

CREATE TABLE status_checks (
    status_check_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,

    check_name VARCHAR(100) NOT NULL,

    checked_revision BIGINT NOT NULL,

    status check_state NOT NULL DEFAULT 'pending',

    details TEXT,

    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(
        pull_request_id,
        check_name,
        checked_revision
    )
);

CREATE INDEX idx_status_checks_request
    ON status_checks(pull_request_id, status);

-- ============================================================
-- DEPLOYMENT RECORDS
-- ============================================================

CREATE TABLE deployments (
    deployment_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    pull_request_id BIGINT NOT NULL
        REFERENCES pull_requests(pull_request_id),

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id),

    deployed_by BIGINT NOT NULL
        REFERENCES principals(principal_id),

    deployment_version BIGINT NOT NULL,

    deployment_status VARCHAR(20) NOT NULL,

    deployed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    rollback_of BIGINT
        REFERENCES deployments(deployment_id),

    CHECK (
        deployment_status IN (
            'successful',
            'failed',
            'rolled_back'
        )
    ),

    CHECK (deployment_version > 0)
);

CREATE INDEX idx_deployments_environment
    ON deployments(environment_id, deployed_at DESC);

-- ============================================================
-- AUDIT EVENTS
-- ============================================================

CREATE TABLE audit_events (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    principal_id BIGINT
        REFERENCES principals(principal_id),

    action VARCHAR(100) NOT NULL,

    resource_type VARCHAR(100) NOT NULL,

    resource_id BIGINT,

    successful BOOLEAN NOT NULL,

    detail JSONB NOT NULL DEFAULT '{}'::JSONB,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_resource
    ON audit_events(resource_type, resource_id, created_at DESC);

CREATE INDEX idx_audit_actor
    ON audit_events(principal_id, created_at DESC);

-- ============================================================
-- TRIGGER: CONFIGURATION VALUE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_configuration_value()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    definition configuration_definitions%ROWTYPE;
    environment environment_type;
    numeric_value NUMERIC;
BEGIN
    SELECT *
    INTO definition
    FROM configuration_definitions
    WHERE definition_id = NEW.definition_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Configuration definition not found';
    END IF;

    SELECT environment_name
    INTO environment
    FROM environments
    WHERE environment_id = NEW.environment_id;

    IF definition.sensitive THEN
        IF NEW.configuration_value IS NOT NULL THEN
            RAISE EXCEPTION
                'Sensitive configuration cannot contain plaintext';
        END IF;

        IF NEW.secret_reference IS NULL THEN
            RAISE EXCEPTION
                'Sensitive configuration requires a secret reference';
        END IF;

        RETURN NEW;
    END IF;

    IF NEW.secret_reference IS NOT NULL THEN
        RAISE EXCEPTION
            'Non-sensitive configuration cannot contain a secret reference';
    END IF;

    IF NEW.configuration_value IS NULL THEN
        IF definition.required THEN
            RAISE EXCEPTION
                'Required configuration cannot be null';
        END IF;

        RETURN NEW;
    END IF;

    IF definition.data_type = 'string' THEN
        IF jsonb_typeof(NEW.configuration_value) <> 'string' THEN
            RAISE EXCEPTION 'Expected string configuration';
        END IF;

    ELSIF definition.data_type = 'integer' THEN
        IF jsonb_typeof(NEW.configuration_value) <> 'number'
           OR NEW.configuration_value::TEXT !~ '^-?[0-9]+$' THEN
            RAISE EXCEPTION 'Expected integer configuration';
        END IF;

        numeric_value := (NEW.configuration_value #>> '{}')::NUMERIC;

        IF definition.minimum_numeric IS NOT NULL
           AND numeric_value < definition.minimum_numeric THEN
            RAISE EXCEPTION 'Configuration below minimum';
        END IF;

        IF definition.maximum_numeric IS NOT NULL
           AND numeric_value > definition.maximum_numeric THEN
            RAISE EXCEPTION 'Configuration above maximum';
        END IF;

    ELSIF definition.data_type = 'numeric' THEN
        IF jsonb_typeof(NEW.configuration_value) <> 'number' THEN
            RAISE EXCEPTION 'Expected numeric configuration';
        END IF;

        numeric_value := (NEW.configuration_value #>> '{}')::NUMERIC;

        IF definition.minimum_numeric IS NOT NULL
           AND numeric_value < definition.minimum_numeric THEN
            RAISE EXCEPTION 'Configuration below minimum';
        END IF;

        IF definition.maximum_numeric IS NOT NULL
           AND numeric_value > definition.maximum_numeric THEN
            RAISE EXCEPTION 'Configuration above maximum';
        END IF;

    ELSIF definition.data_type = 'boolean' THEN
        IF jsonb_typeof(NEW.configuration_value) <> 'boolean' THEN
            RAISE EXCEPTION 'Expected boolean configuration';
        END IF;

    ELSIF definition.data_type = 'json' THEN
        IF jsonb_typeof(NEW.configuration_value) NOT IN (
            'object',
            'array'
        ) THEN
            RAISE EXCEPTION 'Expected JSON object or array';
        END IF;
    END IF;

    IF definition.allowed_values IS NOT NULL THEN
        IF NOT (
            definition.allowed_values @>
            jsonb_build_array(NEW.configuration_value)
        ) THEN
            RAISE EXCEPTION 'Value is not in the allowed set';
        END IF;
    END IF;

    IF environment = 'production'
       AND definition.configuration_key = 'DEBUG'
       AND NEW.configuration_value = 'true'::JSONB THEN
        RAISE EXCEPTION
            'Debug mode is prohibited in production';
    END IF;

    NEW.updated_at := CURRENT_TIMESTAMP;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_configuration_value
BEFORE INSERT OR UPDATE ON configuration_values
FOR EACH ROW
EXECUTE FUNCTION validate_configuration_value();

-- ============================================================
-- TRIGGER: REVIEWER CANNOT APPROVE OWN REQUEST
-- ============================================================

CREATE OR REPLACE FUNCTION prevent_self_approval()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    request_author BIGINT;
BEGIN
    SELECT author_id
    INTO request_author
    FROM pull_requests
    WHERE pull_request_id = NEW.pull_request_id;

    IF request_author = NEW.reviewer_id
       AND NEW.review_status = 'approved' THEN
        RAISE EXCEPTION
            'Authors cannot approve their own pull requests';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_prevent_self_approval
BEFORE INSERT OR UPDATE ON reviews
FOR EACH ROW
EXECUTE FUNCTION prevent_self_approval();

-- ============================================================
-- FUNCTION: COUNT ELIGIBLE APPROVALS
-- ============================================================

CREATE OR REPLACE FUNCTION eligible_approval_count(
    p_pull_request_id BIGINT
)
RETURNS INTEGER
LANGUAGE SQL
STABLE
AS $$
    SELECT COUNT(DISTINCT r.reviewer_id)::INTEGER
    FROM reviews r
    JOIN pull_requests p
      ON p.pull_request_id = r.pull_request_id
    WHERE r.pull_request_id = p_pull_request_id
      AND r.review_status = 'approved'
      AND r.reviewer_id <> p.author_id
      AND r.reviewed_revision = p.source_revision
      AND p.reviewed_revision = p.source_revision;
$$;

-- ============================================================
-- FUNCTION: COUNT UNRESOLVED CONVERSATIONS
-- ============================================================

CREATE OR REPLACE FUNCTION unresolved_conversation_count(
    p_pull_request_id BIGINT
)
RETURNS INTEGER
LANGUAGE SQL
STABLE
AS $$
    SELECT COUNT(*)::INTEGER
    FROM review_comments c
    JOIN reviews r ON r.review_id = c.review_id
    WHERE r.pull_request_id = p_pull_request_id
      AND NOT c.resolved;
$$;

-- ============================================================
-- FUNCTION: EVALUATE MERGE ELIGIBILITY
-- ============================================================

CREATE OR REPLACE FUNCTION evaluate_merge_eligibility(
    p_pull_request_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    request_record pull_requests%ROWTYPE;
    policy_record branch_protection_policies%ROWTYPE;
    approvals INTEGER;
    unresolved INTEGER;
    failed_checks INTEGER;
    security_approved BOOLEAN;
BEGIN
    SELECT *
    INTO request_record
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Pull request does not exist'::TEXT;
        RETURN;
    END IF;

    SELECT bp.*
    INTO policy_record
    FROM branch_protection_policies bp
    WHERE bp.branch_id = request_record.target_branch_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Target branch has no protection policy'::TEXT;
        RETURN;
    END IF;

    IF request_record.is_draft
       OR request_record.state = 'draft' THEN
        RETURN QUERY
        SELECT FALSE, 'Draft request cannot be merged'::TEXT;
        RETURN;
    END IF;

    IF request_record.state IN ('rejected', 'deployed', 'rolled_back') THEN
        RETURN QUERY
        SELECT FALSE, 'Pull request state prohibits merging'::TEXT;
        RETURN;
    END IF;

    IF request_record.source_branch_id =
       request_record.target_branch_id THEN
        RETURN QUERY
        SELECT FALSE, 'Source and target branches must differ'::TEXT;
        RETURN;
    END IF;

    IF NOT request_record.source_synchronized THEN
        RETURN QUERY
        SELECT FALSE, 'Source branch is not synchronized'::TEXT;
        RETURN;
    END IF;

    IF request_record.has_merge_conflict THEN
        RETURN QUERY
        SELECT FALSE, 'Merge conflicts remain'::TEXT;
        RETURN;
    END IF;

    IF policy_record.require_linear_history
       AND NOT request_record.linear_history THEN
        RETURN QUERY
        SELECT FALSE, 'Linear history requirement failed'::TEXT;
        RETURN;
    END IF;

    IF request_record.reviewed_revision IS NULL
       OR request_record.reviewed_revision <>
          request_record.source_revision THEN
        RETURN QUERY
        SELECT FALSE, 'Review decisions are stale'::TEXT;
        RETURN;
    END IF;

    approvals := eligible_approval_count(p_pull_request_id);

    IF approvals < policy_record.required_approvals THEN
        RETURN QUERY
        SELECT FALSE, 'Insufficient eligible approvals'::TEXT;
        RETURN;
    END IF;

    IF policy_record.require_security_approval THEN
        SELECT EXISTS (
            SELECT 1
            FROM reviews r
            JOIN principals p
              ON p.principal_id = r.reviewer_id
            WHERE r.pull_request_id = p_pull_request_id
              AND r.review_status = 'approved'
              AND p.role = 'security_officer'
              AND r.reviewer_id <> request_record.author_id
              AND r.reviewed_revision = request_record.source_revision
        )
        INTO security_approved;

        IF NOT security_approved THEN
            RETURN QUERY
            SELECT FALSE, 'Security approval is required'::TEXT;
            RETURN;
        END IF;
    END IF;

    IF policy_record.require_tests THEN
        IF NOT EXISTS (
            SELECT 1
            FROM status_checks s
            WHERE s.pull_request_id = p_pull_request_id
              AND s.check_name = 'unit-tests'
              AND s.status = 'passed'
              AND s.checked_revision = request_record.source_revision
        ) THEN
            RETURN QUERY
            SELECT FALSE, 'Required unit tests have not passed'::TEXT;
            RETURN;
        END IF;
    END IF;

    IF policy_record.require_secret_scan THEN
        IF NOT EXISTS (
            SELECT 1
            FROM status_checks s
            WHERE s.pull_request_id = p_pull_request_id
              AND s.check_name = 'secret-scan'
              AND s.status = 'passed'
              AND s.checked_revision = request_record.source_revision
        ) THEN
            RETURN QUERY
            SELECT FALSE, 'Secret scan has not passed'::TEXT;
            RETURN;
        END IF;
    END IF;

    unresolved := unresolved_conversation_count(p_pull_request_id);

    IF policy_record.require_conversations_resolved
       AND unresolved > 0 THEN
        RETURN QUERY
        SELECT FALSE, 'Review conversations remain unresolved'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT TRUE, 'All governance requirements satisfied'::TEXT;
END;
$$;

-- ============================================================
-- PROCEDURE: DEPLOY CONFIGURATION
--
-- Uses a transaction and row locking to prevent concurrent
-- deployment decisions from silently overwriting each other.
-- ============================================================

CREATE OR REPLACE PROCEDURE deploy_configuration(
    p_pull_request_id BIGINT,
    p_environment_id BIGINT,
    p_actor_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    request_record pull_requests%ROWTYPE;
    environment_record environments%ROWTYPE;
    eligibility RECORD;
    next_version BIGINT;
BEGIN
    SELECT *
    INTO request_record
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pull request not found';
    END IF;

    SELECT *
    INTO environment_record
    FROM environments
    WHERE environment_id = p_environment_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Environment not found';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM repository_members
        WHERE repository_id = request_record.repository_id
          AND principal_id = p_actor_id
    ) THEN
        RAISE EXCEPTION
            'Deployment actor is not a repository member';
    END IF;

    IF environment_record.environment_name = 'production'
       AND request_record.target_branch_id IS NULL THEN
        RAISE EXCEPTION 'Invalid production deployment target';
    END IF;

    SELECT *
    INTO eligibility
    FROM evaluate_merge_eligibility(p_pull_request_id);

    IF NOT eligibility.eligible THEN
        RAISE EXCEPTION
            'Deployment rejected: %',
            eligibility.reason;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM configuration_changesets cs
        JOIN configuration_definitions cd
          ON cd.definition_id = cs.definition_id
        WHERE cs.pull_request_id = p_pull_request_id
          AND cd.repository_id <> request_record.repository_id
    ) THEN
        RAISE EXCEPTION
            'Changeset contains foreign repository configuration';
    END IF;

    UPDATE pull_requests
    SET state = 'deployed',
        is_draft = FALSE,
        updated_at = CURRENT_TIMESTAMP
    WHERE pull_request_id = p_pull_request_id;

    INSERT INTO deployments (
        pull_request_id,
        environment_id,
        deployed_by,
        deployment_version,
        deployment_status
    )
    VALUES (
        p_pull_request_id,
        p_environment_id,
        p_actor_id,
        request_record.source_revision,
        'successful'
    );

    INSERT INTO audit_events (
        principal_id,
        action,
        resource_type,
        resource_id,
        successful,
        detail
    )
    VALUES (
        p_actor_id,
        'CONFIGURATION_DEPLOYMENT',
        'pull_request',
        p_pull_request_id,
        TRUE,
        jsonb_build_object(
            'environment',
            environment_record.environment_name,
            'revision',
            request_record.source_revision
        )
    );
END;
$$;

-- ============================================================
-- VIEW: CONFIGURATION INVENTORY
--
-- Secret references are displayed as references only.
-- ============================================================

CREATE OR REPLACE VIEW configuration_inventory AS
SELECT
    r.repository_name,
    e.environment_name,
    d.configuration_key,
    d.data_type,
    d.required,
    d.sensitive,
    CASE
        WHEN d.sensitive THEN '[REDACTED]'
        ELSE COALESCE(
            cv.configuration_value::TEXT,
            '[NOT CONFIGURED]'
        )
    END AS displayed_value,
    CASE
        WHEN d.sensitive THEN '[SECRET REFERENCE]'
        ELSE NULL
    END AS secret_information,
    cv.version,
    cv.updated_at
FROM configuration_definitions d
JOIN repositories r
  ON r.repository_id = d.repository_id
CROSS JOIN environments e
LEFT JOIN configuration_values cv
  ON cv.definition_id = d.definition_id
 AND cv.environment_id = e.environment_id;

-- ============================================================
-- VIEW: PULL REQUEST GOVERNANCE REPORT
-- ============================================================

CREATE OR REPLACE VIEW pull_request_governance_report AS
SELECT
    pr.pull_request_id,
    repo.repository_name,
    pr.title,
    pr.state,
    source.branch_name AS source_branch,
    target.branch_name AS target_branch,
    author.username AS author,
    pr.source_revision,
    eligible_approval_count(pr.pull_request_id) AS approvals,
    unresolved_conversation_count(pr.pull_request_id)
        AS unresolved_conversations,
    pr.source_synchronized,
    pr.has_merge_conflict,
    pr.updated_at
FROM pull_requests pr
JOIN repositories repo
  ON repo.repository_id = pr.repository_id
JOIN branches source
  ON source.branch_id = pr.source_branch_id
JOIN branches target
  ON target.branch_id = pr.target_branch_id
JOIN principals author
  ON author.principal_id = pr.author_id;

-- ============================================================
-- SAMPLE DATA
-- ============================================================

INSERT INTO repositories (
    repository_name,
    description
)
VALUES (
    'inventory-platform',
    'Enterprise inventory application configuration'
);

INSERT INTO principals(username, role)
VALUES
    ('developer-01', 'developer'),
    ('reviewer-01', 'reviewer'),
    ('security-01', 'security_officer'),
    ('administrator-01', 'administrator');

INSERT INTO repository_members (
    repository_id,
    principal_id,
    member_role
)
SELECT
    r.repository_id,
    p.principal_id,
    p.role
FROM repositories r
CROSS JOIN principals p
WHERE r.repository_name = 'inventory-platform';

INSERT INTO environments(environment_name)
VALUES
    ('development'),
    ('testing'),
    ('staging'),
    ('production');

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit,
    revision,
    protected
)
SELECT
    repository_id,
    'main',
    'a1234567890abcd',
    4,
    TRUE
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO branches (
    repository_id,
    branch_name,
    head_commit,
    revision,
    protected
)
SELECT
    repository_id,
    'feature/database-config',
    'b1234567890abcd',
    3,
    FALSE
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO configuration_definitions (
    repository_id,
    configuration_key,
    data_type,
    description,
    required,
    sensitive,
    default_value,
    minimum_numeric,
    maximum_numeric,
    allowed_values
)
SELECT
    repository_id,
    'APP_PORT',
    'integer',
    'Application listening port',
    TRUE,
    FALSE,
    '8000'::JSONB,
    1024,
    65535,
    NULL
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO configuration_definitions (
    repository_id,
    configuration_key,
    data_type,
    description,
    required,
    sensitive,
    default_value
)
SELECT
    repository_id,
    'DEBUG',
    'boolean',
    'Application debug mode',
    TRUE,
    FALSE,
    'false'::JSONB
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO configuration_definitions (
    repository_id,
    configuration_key,
    data_type,
    description,
    required,
    sensitive,
    default_value,
    minimum_numeric,
    maximum_numeric
)
SELECT
    repository_id,
    'DATABASE_POOL_SIZE',
    'integer',
    'Maximum database connections',
    TRUE,
    FALSE,
    '10'::JSONB,
    1,
    100
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO configuration_definitions (
    repository_id,
    configuration_key,
    data_type,
    description,
    required,
    sensitive
)
SELECT
    repository_id,
    'DATABASE_PASSWORD',
    'string',
    'External database credential reference',
    TRUE,
    TRUE
FROM repositories
WHERE repository_name = 'inventory-platform';

INSERT INTO configuration_definitions (
    repository_id,
    configuration_key,
    data_type,
    description,
    required,
    sensitive,
    default_value,
    allowed_values
)
SELECT
    repository_id,
    'LOG_LEVEL',
    'string',
    'Application logging threshold',
    TRUE,
    FALSE,
    '"INFO"'::JSONB,
    '["DEBUG","INFO","WARNING","ERROR"]'::JSONB
FROM repositories
WHERE repository_name = 'inventory-platform';

-- Development and production configuration values.

INSERT INTO configuration_values (
    definition_id,
    environment_id,
    configuration_value,
    updated_by
)
SELECT
    d.definition_id,
    e.environment_id,
    CASE d.configuration_key
        WHEN 'APP_PORT' THEN '8000'::JSONB
        WHEN 'DEBUG' THEN 'true'::JSONB
        WHEN 'DATABASE_POOL_SIZE' THEN '10'::JSONB
        WHEN 'LOG_LEVEL' THEN '"DEBUG"'::JSONB
    END,
    p.principal_id
FROM configuration_definitions d
JOIN environments e
  ON e.environment_name = 'development'
JOIN principals p
  ON p.username = 'developer-01'
WHERE d.configuration_key IN (
    'APP_PORT',
    'DEBUG',
    'DATABASE_POOL_SIZE',
    'LOG_LEVEL'
);

INSERT INTO configuration_values (
    definition_id,
    environment_id,
    configuration_value,
    updated_by
)
SELECT
    d.definition_id,
    e.environment_id,
    CASE d.configuration_key
        WHEN 'APP_PORT' THEN '8080'::JSONB
        WHEN 'DEBUG' THEN 'false'::JSONB
        WHEN 'DATABASE_POOL_SIZE' THEN '25'::JSONB
        WHEN 'LOG_LEVEL' THEN '"INFO"'::JSONB
    END,
    p.principal_id
FROM configuration_definitions d
JOIN environments e
  ON e.environment_name = 'production'
JOIN principals p
  ON p.username = 'administrator-01'
WHERE d.configuration_key IN (
    'APP_PORT',
    'DEBUG',
    'DATABASE_POOL_SIZE',
    'LOG_LEVEL'
);

INSERT INTO secret_metadata (
    repository_id,
    environment_id,
    secret_name,
    secret_reference,
    status,
    version,
    last_rotated_at
)
SELECT
    r.repository_id,
    e.environment_id,
    'DATABASE_PASSWORD',
    'vault://inventory/production/database-password',
    'active',
    3,
    CURRENT_TIMESTAMP - INTERVAL '10 days'
FROM repositories r
JOIN environments e
  ON e.environment_name = 'production'
WHERE r.repository_name = 'inventory-platform';

INSERT INTO configuration_values (
    definition_id,
    environment_id,
    secret_reference,
    updated_by
)
SELECT
    d.definition_id,
    e.environment_id,
    'vault://inventory/production/database-password',
    p.principal_id
FROM configuration_definitions d
JOIN environments e
  ON e.environment_name = 'production'
JOIN principals p
  ON p.username = 'administrator-01'
WHERE d.configuration_key = 'DATABASE_PASSWORD';

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_security_approval,
    require_tests,
    require_secret_scan,
    require_conversations_resolved,
    require_linear_history,
    allow_direct_push,
    allow_force_push,
    allow_branch_deletion,
    allow_administrator_bypass
)
SELECT
    b.branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    FALSE,
    FALSE
FROM branches b
WHERE b.branch_name = 'main';

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    author_id,
    title,
    description,
    state,
    is_draft,
    source_revision,
    target_revision,
    reviewed_revision,
    source_synchronized,
    has_merge_conflict,
    linear_history
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    author.principal_id,
    'Update production database configuration',
    'Increase connection pool and update application port',
    'approved',
    FALSE,
    3,
    4,
    3,
    TRUE,
    FALSE,
    TRUE
FROM repositories r
JOIN branches source
  ON source.repository_id = r.repository_id
 AND source.branch_name = 'feature/database-config'
JOIN branches target
  ON target.repository_id = r.repository_id
 AND target.branch_name = 'main'
JOIN principals author
  ON author.username = 'developer-01'
WHERE r.repository_name = 'inventory-platform';

INSERT INTO configuration_changesets (
    pull_request_id,
    definition_id,
    old_value,
    new_value
)
SELECT
    pr.pull_request_id,
    d.definition_id,
    CASE d.configuration_key
        WHEN 'APP_PORT' THEN '8000'::JSONB
        WHEN 'DATABASE_POOL_SIZE' THEN '10'::JSONB
    END,
    CASE d.configuration_key
        WHEN 'APP_PORT' THEN '8080'::JSONB
        WHEN 'DATABASE_POOL_SIZE' THEN '25'::JSONB
    END
FROM pull_requests pr
JOIN configuration_definitions d
  ON d.configuration_key IN (
      'APP_PORT',
      'DATABASE_POOL_SIZE'
  )
WHERE pr.title = 'Update production database configuration';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_status,
    reviewed_revision,
    review_comment
)
SELECT
    pr.pull_request_id,
    p.principal_id,
    'approved',
    3,
    'Configuration reviewed'
FROM pull_requests pr
CROSS JOIN principals p
WHERE pr.title = 'Update production database configuration'
  AND p.username = 'reviewer-01';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_status,
    reviewed_revision,
    review_comment
)
SELECT
    pr.pull_request_id,
    p.principal_id,
    'approved',
    3,
    'Production security requirements satisfied'
FROM pull_requests pr
CROSS JOIN principals p
WHERE pr.title = 'Update production database configuration'
  AND p.username = 'security-01';

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    checked_revision,
    status,
    details
)
SELECT
    pr.pull_request_id,
    checks.check_name,
    3,
    'passed',
    checks.details
FROM pull_requests pr
CROSS JOIN (
    VALUES
        ('unit-tests', 'All unit tests passed'),
        ('secret-scan', 'No credentials detected'),
        ('configuration-validation', 'Configuration schema validated')
) AS checks(check_name, details)
WHERE pr.title = 'Update production database configuration';

-- ============================================================
-- RETRIEVAL: CONFIGURATION INVENTORY
-- ============================================================

SELECT *
FROM configuration_inventory
ORDER BY repository_name, environment_name, configuration_key;

-- ============================================================
-- VALIDATION: CONFIGURATION TYPES AND SECRET REFERENCES
-- ============================================================

SELECT
    d.configuration_key,
    d.data_type,
    e.environment_name,
    cv.configuration_value,
    cv.secret_reference,
    CASE
        WHEN d.sensitive AND cv.configuration_value IS NOT NULL
            THEN 'INVALID PLAINTEXT SECRET'
        WHEN d.sensitive AND cv.secret_reference IS NULL
            THEN 'MISSING SECRET REFERENCE'
        WHEN NOT d.sensitive AND cv.secret_reference IS NOT NULL
            THEN 'UNEXPECTED SECRET REFERENCE'
        ELSE 'STRUCTURALLY VALID'
    END AS validation_status
FROM configuration_definitions d
CROSS JOIN environments e
LEFT JOIN configuration_values cv
  ON cv.definition_id = d.definition_id
 AND cv.environment_id = e.environment_id
ORDER BY d.configuration_key, e.environment_name;

-- ============================================================
-- AGGREGATION: CONFIGURATION COUNTS
-- ============================================================

SELECT
    e.environment_name,
    COUNT(cv.configuration_value_id) AS configured_settings,
    COUNT(*) FILTER (
        WHERE d.sensitive
    ) AS sensitive_definitions
FROM environments e
CROSS JOIN configuration_definitions d
LEFT JOIN configuration_values cv
  ON cv.environment_id = e.environment_id
 AND cv.definition_id = d.definition_id
GROUP BY e.environment_name
ORDER BY e.environment_name;

-- ============================================================
-- REPORTING: SECRET ROTATION STATUS
-- ============================================================

SELECT
    secret_name,
    secret_reference,
    status,
    version,
    last_rotated_at,
    expires_at,
    CASE
        WHEN status = 'revoked' THEN 'REVOKED'
        WHEN status = 'expired' THEN 'EXPIRED'
        WHEN expires_at < CURRENT_TIMESTAMP THEN 'EXPIRY PASSED'
        WHEN expires_at < CURRENT_TIMESTAMP + INTERVAL '14 days'
            THEN 'ROTATION REQUIRED'
        ELSE 'CURRENT'
    END AS rotation_assessment
FROM secret_metadata;

-- ============================================================
-- REPORTING: PULL REQUEST GOVERNANCE
-- ============================================================

SELECT *
FROM pull_request_governance_report
ORDER BY updated_at DESC;

-- ============================================================
-- EVALUATION: MERGE ELIGIBILITY
-- ============================================================

SELECT *
FROM evaluate_merge_eligibility(
    (
        SELECT pull_request_id
        FROM pull_requests
        WHERE title =
            'Update production database configuration'
    )
);

-- ============================================================
-- CTE: CONFIGURATION CHANGE IMPACT
-- ============================================================

WITH changes AS (
    SELECT
        pr.pull_request_id,
        pr.title,
        d.configuration_key,
        cs.old_value,
        cs.new_value,
        d.sensitive
    FROM pull_requests pr
    JOIN configuration_changesets cs
      ON cs.pull_request_id = pr.pull_request_id
    JOIN configuration_definitions d
      ON d.definition_id = cs.definition_id
),
impact AS (
    SELECT
        pull_request_id,
        title,
        COUNT(*) AS changed_settings,
        COUNT(*) FILTER (
            WHERE sensitive
        ) AS sensitive_changes
    FROM changes
    GROUP BY pull_request_id, title
)
SELECT *
FROM impact;

-- ============================================================
-- WORKFLOW: DEPLOYMENT TRANSACTION
--
-- This sample executes the procedure against the eligible
-- development environment. It does not expose secret values.
-- ============================================================

DO $$
DECLARE
    request_id BIGINT;
    environment_id_value BIGINT;
    administrator_id BIGINT;
BEGIN
    SELECT pull_request_id
    INTO request_id
    FROM pull_requests
    WHERE title = 'Update production database configuration';

    SELECT environment_id
    INTO environment_id_value
    FROM environments
    WHERE environment_name = 'production';

    SELECT principal_id
    INTO administrator_id
    FROM principals
    WHERE username = 'administrator-01';

    CALL deploy_configuration(
        request_id,
        environment_id_value,
        administrator_id
    );

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Deployment transaction rejected: %', SQLERRM;
END;
$$;

-- ============================================================
-- FAILURE TEST: INVALID PRODUCTION DEBUG CONFIGURATION
--
-- The trigger rejects this operation.
-- The exception block preserves the surrounding transaction.
-- ============================================================

DO $$
DECLARE
    definition_id_value BIGINT;
    production_id BIGINT;
    administrator_id BIGINT;
BEGIN
    SELECT definition_id
    INTO definition_id_value
    FROM configuration_definitions
    WHERE configuration_key = 'DEBUG';

    SELECT environment_id
    INTO production_id
    FROM environments
    WHERE environment_name = 'production';

    SELECT principal_id
    INTO administrator_id
    FROM principals
    WHERE username = 'administrator-01';

    BEGIN
        INSERT INTO configuration_values (
            definition_id,
            environment_id,
            configuration_value,
            updated_by
        )
        VALUES (
            definition_id_value,
            production_id,
            'true'::JSONB,
            administrator_id
        )
        ON CONFLICT (definition_id, environment_id)
        DO UPDATE SET
            configuration_value = EXCLUDED.configuration_value,
            updated_by = EXCLUDED.updated_by;

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Expected policy rejection: %', SQLERRM;
    END;
END;
$$;

-- ============================================================
-- FAILURE TEST: SELF-APPROVAL
-- ============================================================

DO $$
DECLARE
    request_id BIGINT;
    author_id BIGINT;
BEGIN
    SELECT pull_request_id, pull_requests.author_id
    INTO request_id, author_id
    FROM pull_requests
    WHERE title = 'Update production database configuration';

    BEGIN
        INSERT INTO reviews (
            pull_request_id,
            reviewer_id,
            review_status,
            reviewed_revision,
            review_comment
        )
        VALUES (
            request_id,
            author_id,
            'approved',
            3,
            'Self-approval attempt'
        );

    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Expected review rejection: %', SQLERRM;
    END;
END;
$$;

-- ============================================================
-- AUDIT REPORT
-- ============================================================

SELECT
    a.audit_id,
    p.username,
    a.action,
    a.resource_type,
    a.resource_id,
    a.successful,
    a.detail,
    a.created_at
FROM audit_events a
LEFT JOIN principals p
  ON p.principal_id = a.principal_id
ORDER BY a.created_at DESC;

COMMIT;
