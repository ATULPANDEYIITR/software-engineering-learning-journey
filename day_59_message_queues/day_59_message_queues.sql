DROP SCHEMA IF EXISTS messaging_demo CASCADE;
CREATE SCHEMA messaging_demo;
SET search_path = messaging_demo, public;

CREATE TYPE message_state AS ENUM (
    'ready',
    'processing',
    'acknowledged',
    'failed',
    'dead_lettered'
);

CREATE TYPE consumer_status AS ENUM (
    'active',
    'paused',
    'disabled'
);

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(trim(repository_name)) > 0),
    CHECK (length(trim(default_branch)) > 0)
);

CREATE TABLE branches (
    branch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_name TEXT NOT NULL,
    protected BOOLEAN NOT NULL DEFAULT FALSE,
    allow_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    allow_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (repository_id, branch_name)
);

CREATE TABLE commits (
    commit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    branch_id BIGINT REFERENCES branches(branch_id)
        ON DELETE SET NULL,
    commit_hash TEXT NOT NULL UNIQUE,
    message TEXT NOT NULL,
    committed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(commit_hash) >= 7),
    CHECK (length(trim(message)) > 0)
);

CREATE TABLE message_queues (
    queue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT REFERENCES repositories(repository_id)
        ON DELETE SET NULL,
    queue_name TEXT NOT NULL UNIQUE,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    max_payload_bytes INTEGER NOT NULL DEFAULT 1048576,
    CHECK (max_attempts BETWEEN 1 AND 100),
    CHECK (max_payload_bytes > 0)
);

CREATE TABLE consumers (
    consumer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    queue_id BIGINT NOT NULL REFERENCES message_queues(queue_id)
        ON DELETE CASCADE,
    consumer_name TEXT NOT NULL,
    status consumer_status NOT NULL DEFAULT 'active',
    UNIQUE (queue_id, consumer_name)
);

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    queue_id BIGINT NOT NULL REFERENCES message_queues(queue_id)
        ON DELETE CASCADE,
    topic TEXT NOT NULL,
    payload JSONB NOT NULL,
    state message_state NOT NULL DEFAULT 'ready',
    attempt_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    available_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    acknowledged_at TIMESTAMPTZ,
    CHECK (length(trim(topic)) > 0),
    CHECK (attempt_count >= 0),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (
        acknowledged_at IS NULL
        OR state = 'acknowledged'
    )
);

CREATE TABLE message_attempts (
    attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id UUID NOT NULL REFERENCES messages(message_id)
        ON DELETE CASCADE,
    consumer_id BIGINT NOT NULL REFERENCES consumers(consumer_id)
        ON DELETE RESTRICT,
    attempt_number INTEGER NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    completed_at TIMESTAMPTZ,
    succeeded BOOLEAN,
    error_message TEXT,
    UNIQUE (message_id, attempt_number),
    CHECK (attempt_number > 0)
);

CREATE TABLE dead_letters (
    dead_letter_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_id UUID NOT NULL UNIQUE REFERENCES messages(message_id)
        ON DELETE CASCADE,
    reason TEXT NOT NULL,
    moved_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(trim(reason)) > 0)
);

CREATE TABLE pull_requests (
    pull_request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id)
        ON DELETE CASCADE,
    source_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    target_branch_id BIGINT NOT NULL REFERENCES branches(branch_id),
    title TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open',
    draft BOOLEAN NOT NULL DEFAULT FALSE,
    merge_conflict BOOLEAN NOT NULL DEFAULT FALSE,
    conversations_resolved BOOLEAN NOT NULL DEFAULT TRUE,
    base_synchronized BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    closed_at TIMESTAMPTZ,
    CHECK (state IN ('open', 'closed', 'merged')),
    CHECK (length(trim(title)) > 0),
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

CREATE TABLE reviewers (
    reviewer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reviewer_name TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE reviews (
    review_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES reviewers(reviewer_id),
    review_state TEXT NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    stale BOOLEAN NOT NULL DEFAULT FALSE,
    dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (
        review_state IN (
            'commented',
            'approved',
            'changes_requested',
            'dismissed'
        )
    )
);

CREATE TABLE review_comments (
    comment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    review_id BIGINT NOT NULL REFERENCES reviews(review_id)
        ON DELETE CASCADE,
    body TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (length(trim(body)) > 0),
    CHECK (line_number IS NULL OR line_number > 0)
);

CREATE TABLE status_checks (
    status_check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pull_request_id BIGINT NOT NULL REFERENCES pull_requests(pull_request_id)
        ON DELETE CASCADE,
    check_name TEXT NOT NULL,
    passed BOOLEAN NOT NULL,
    completed_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (pull_request_id, check_name)
);

CREATE TABLE branch_protection_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    branch_id BIGINT NOT NULL UNIQUE REFERENCES branches(branch_id)
        ON DELETE CASCADE,
    required_approvals INTEGER NOT NULL DEFAULT 0,
    require_status_checks BOOLEAN NOT NULL DEFAULT TRUE,
    require_resolved_conversations BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_direct_push BOOLEAN NOT NULL DEFAULT TRUE,
    restrict_force_push BOOLEAN NOT NULL DEFAULT TRUE,
    require_linear_history BOOLEAN NOT NULL DEFAULT FALSE,
    CHECK (required_approvals >= 0)
);

CREATE TABLE approval_requirements (
    requirement_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_id BIGINT NOT NULL REFERENCES branch_protection_policies(policy_id)
        ON DELETE CASCADE,
    reviewer_id BIGINT NOT NULL REFERENCES reviewers(reviewer_id),
    UNIQUE (policy_id, reviewer_id)
);

CREATE INDEX idx_messages_ready
    ON messages (queue_id, available_at)
    WHERE state = 'ready';

CREATE INDEX idx_message_attempts_message
    ON message_attempts (message_id, attempt_number);

CREATE INDEX idx_pr_checks
    ON status_checks (pull_request_id, passed);

CREATE INDEX idx_reviews_pr_state
    ON reviews (pull_request_id, review_state, stale, dismissed);

CREATE INDEX idx_pr_target_state
    ON pull_requests (target_branch_id, state);

CREATE OR REPLACE FUNCTION validate_message_attempt()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    allowed_attempts INTEGER;
BEGIN
    SELECT max_attempts
    INTO allowed_attempts
    FROM message_queues
    WHERE queue_id = NEW.queue_id;

    IF NEW.attempt_count > allowed_attempts THEN
        RAISE EXCEPTION
            'Message % exceeded maximum attempts %',
            NEW.message_id,
            allowed_attempts;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_message_attempt
BEFORE INSERT OR UPDATE ON messages
FOR EACH ROW
EXECUTE FUNCTION validate_message_attempt();

CREATE OR REPLACE FUNCTION acknowledge_message(
    p_message_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE messages
    SET state = 'acknowledged',
        acknowledged_at = clock_timestamp()
    WHERE message_id = p_message_id
      AND state = 'processing';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Message % is not in processing state',
            p_message_id;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION enqueue_message(
    p_queue_name TEXT,
    p_topic TEXT,
    p_payload JSONB
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_queue_id BIGINT;
    v_message_id UUID;
    v_limit INTEGER;
BEGIN
    SELECT queue_id, max_payload_bytes
    INTO v_queue_id, v_limit
    FROM message_queues
    WHERE queue_name = p_queue_name;

    IF v_queue_id IS NULL THEN
        RAISE EXCEPTION 'Unknown queue: %', p_queue_name;
    END IF;

    IF octet_length(p_payload::text) > v_limit THEN
        RAISE EXCEPTION 'Message payload exceeds configured limit';
    END IF;

    INSERT INTO messages (
        queue_id,
        topic,
        payload
    )
    VALUES (
        v_queue_id,
        p_topic,
        p_payload
    )
    RETURNING message_id INTO v_message_id;

    RETURN v_message_id;
END;
$$;

CREATE OR REPLACE FUNCTION evaluate_pull_request(
    p_pull_request_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT,
    valid_approvals INTEGER,
    failed_checks INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_required_approvals INTEGER;
    v_require_checks BOOLEAN;
    v_require_conversations BOOLEAN;
    v_target_protected BOOLEAN;
    v_pr pull_requests%ROWTYPE;
BEGIN
    SELECT *
    INTO v_pr
    FROM pull_requests
    WHERE pull_request_id = p_pull_request_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request does not exist', 0, 0;
        RETURN;
    END IF;

    SELECT
        b.protected,
        p.required_approvals,
        p.require_status_checks,
        p.require_resolved_conversations
    INTO
        v_target_protected,
        v_required_approvals,
        v_require_checks,
        v_require_conversations
    FROM branches b
    LEFT JOIN branch_protection_policies p
        ON p.branch_id = b.branch_id
    WHERE b.branch_id = v_pr.target_branch_id;

    SELECT count(*)
    INTO valid_approvals
    FROM reviews r
    JOIN approval_requirements ar
        ON ar.reviewer_id = r.reviewer_id
    JOIN branch_protection_policies bp
        ON bp.policy_id = ar.policy_id
    WHERE bp.branch_id = v_pr.target_branch_id
      AND r.pull_request_id = p_pull_request_id
      AND r.review_state = 'approved'
      AND r.stale = FALSE
      AND r.dismissed = FALSE;

    SELECT count(*)
    INTO failed_checks
    FROM status_checks
    WHERE pull_request_id = p_pull_request_id
      AND passed = FALSE;

    IF v_pr.state <> 'open' THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request is not open',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF v_pr.draft THEN
        RETURN QUERY
        SELECT FALSE, 'Pull Request is a draft',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF NOT v_pr.base_synchronized THEN
        RETURN QUERY
        SELECT FALSE, 'Source branch is behind target branch',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF v_pr.merge_conflict THEN
        RETURN QUERY
        SELECT FALSE, 'Merge conflict exists',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF v_target_protected AND v_require_conversations
       AND NOT v_pr.conversations_resolved THEN
        RETURN QUERY
        SELECT FALSE, 'Unresolved required conversation',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF v_target_protected AND v_require_checks AND failed_checks > 0 THEN
        RETURN QUERY
        SELECT FALSE, 'Required status check failed',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    IF v_target_protected
       AND valid_approvals < COALESCE(v_required_approvals, 0) THEN
        RETURN QUERY
        SELECT FALSE, 'Required approvals are missing',
               valid_approvals, failed_checks;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT TRUE, 'Pull Request is merge eligible',
           valid_approvals, failed_checks;
END;
$$;

INSERT INTO repositories (repository_name)
VALUES ('order-platform');

INSERT INTO branches (
    repository_id,
    branch_name,
    protected,
    allow_direct_push,
    allow_force_push,
    require_linear_history
)
SELECT repository_id, 'main', TRUE, FALSE, FALSE, TRUE
FROM repositories
WHERE repository_name = 'order-platform';

INSERT INTO branches (
    repository_id,
    branch_name,
    protected,
    allow_direct_push,
    allow_force_push,
    require_linear_history
)
SELECT repository_id, 'feature/message-consumer', FALSE, TRUE, TRUE, FALSE
FROM repositories
WHERE repository_name = 'order-platform';

INSERT INTO commits (
    repository_id,
    branch_id,
    commit_hash,
    message
)
SELECT
    r.repository_id,
    b.branch_id,
    'a1b2c3d4e5f6',
    'Add asynchronous order consumer'
FROM repositories r
JOIN branches b
    ON b.repository_id = r.repository_id
WHERE r.repository_name = 'order-platform'
  AND b.branch_name = 'feature/message-consumer';

INSERT INTO message_queues (
    repository_id,
    queue_name,
    max_attempts,
    max_payload_bytes
)
SELECT repository_id, 'orders', 3, 65536
FROM repositories
WHERE repository_name = 'order-platform';

INSERT INTO consumers (queue_id, consumer_name)
SELECT queue_id, 'order-worker'
FROM message_queues
WHERE queue_name = 'orders';

SELECT enqueue_message(
    'orders',
    'orders.created',
    '{"order_id":"ORD-1001","amount":450.25}'::jsonb
);

SELECT enqueue_message(
    'orders',
    'orders.created',
    '{"order_id":"ORD-1002","amount":89.00}'::jsonb
);

INSERT INTO reviewers (reviewer_name)
VALUES ('alice'), ('bob'), ('carol');

INSERT INTO branch_protection_policies (
    branch_id,
    required_approvals,
    require_status_checks,
    require_resolved_conversations,
    restrict_direct_push,
    restrict_force_push,
    require_linear_history
)
SELECT
    branch_id,
    2,
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    TRUE
FROM branches
WHERE branch_name = 'main';

INSERT INTO approval_requirements (policy_id, reviewer_id)
SELECT bp.policy_id, r.reviewer_id
FROM branch_protection_policies bp
CROSS JOIN reviewers r
JOIN branches b ON b.branch_id = bp.branch_id
WHERE b.branch_name = 'main'
  AND r.reviewer_name IN ('alice', 'bob');

INSERT INTO pull_requests (
    repository_id,
    source_branch_id,
    target_branch_id,
    title,
    draft,
    merge_conflict,
    conversations_resolved,
    base_synchronized
)
SELECT
    r.repository_id,
    source.branch_id,
    target.branch_id,
    'Introduce asynchronous order processing',
    FALSE,
    FALSE,
    TRUE,
    TRUE
FROM repositories r
JOIN branches source
    ON source.repository_id = r.repository_id
   AND source.branch_name = 'feature/message-consumer'
JOIN branches target
    ON target.repository_id = r.repository_id
   AND target.branch_name = 'main'
WHERE r.repository_name = 'order-platform';

INSERT INTO pull_request_commits (
    pull_request_id,
    commit_id,
    commit_position
)
SELECT pr.pull_request_id, c.commit_id, 1
FROM pull_requests pr
JOIN commits c
    ON c.commit_hash = 'a1b2c3d4e5f6';

INSERT INTO reviews (
    pull_request_id,
    reviewer_id,
    review_state
)
SELECT pr.pull_request_id, r.reviewer_id, 'approved'
FROM pull_requests pr
JOIN reviewers r
    ON r.reviewer_name IN ('alice', 'bob');

INSERT INTO review_comments (
    review_id,
    body,
    file_path,
    line_number,
    resolved
)
SELECT
    review_id,
    'Retry policy is bounded and failures reach a dead-letter path.',
    'consumer.java',
    120,
    TRUE
FROM reviews
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    ORDER BY pull_request_id DESC
    LIMIT 1
)
LIMIT 1;

INSERT INTO status_checks (
    pull_request_id,
    check_name,
    passed
)
SELECT pull_request_id, 'unit-tests', TRUE
FROM pull_requests
UNION ALL
SELECT pull_request_id, 'integration-tests', TRUE
FROM pull_requests;

-- Retrieval and queue-state reporting.
SELECT
    q.queue_name,
    m.topic,
    m.state,
    m.attempt_count,
    m.created_at
FROM messages m
JOIN message_queues q ON q.queue_id = m.queue_id
ORDER BY m.created_at;

-- Aggregation by queue and state.
SELECT
    q.queue_name,
    m.state,
    count(*) AS message_count
FROM messages m
JOIN message_queues q ON q.queue_id = m.queue_id
GROUP BY q.queue_name, m.state
ORDER BY q.queue_name, m.state;

-- Transactional acknowledgement example.
BEGIN;

WITH next_message AS (
    SELECT message_id
    FROM messages
    WHERE state = 'ready'
      AND available_at <= clock_timestamp()
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
UPDATE messages m
SET state = 'processing',
    attempt_count = attempt_count + 1
FROM next_message n
WHERE m.message_id = n.message_id;

COMMIT;

-- Merge eligibility report.
SELECT *
FROM evaluate_pull_request(
    (SELECT pull_request_id
     FROM pull_requests
     ORDER BY pull_request_id DESC
     LIMIT 1)
);

-- Demonstrate a policy failure without mutating the source record.
UPDATE status_checks
SET passed = FALSE
WHERE pull_request_id = (
    SELECT pull_request_id
    FROM pull_requests
    ORDER BY pull_request_id DESC
    LIMIT 1
)
AND check_name = 'integration-tests';

SELECT *
FROM evaluate_pull_request(
    (SELECT pull_request_id
     FROM pull_requests
     ORDER BY pull_request_id DESC
     LIMIT 1)
);

-- PostgreSQL's row-level locking and SKIP LOCKED support concurrent workers:
-- each worker can claim a different ready message without waiting on rows
-- already claimed by another worker.
SELECT
    m.message_id,
    m.topic,
    m.attempt_count
FROM messages m
WHERE m.state = 'ready'
ORDER BY m.created_at
FOR UPDATE SKIP LOCKED;
