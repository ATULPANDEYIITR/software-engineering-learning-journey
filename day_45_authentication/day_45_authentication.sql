-- PostgreSQL 15+ compatible authentication model.
-- The schema separates identities, stateful sessions, access credentials,
-- refresh credentials, authentication events, and authorization roles.
--
-- Password hashes are supplied by an application-side password hashing
-- implementation. Plain passwords are deliberately never stored here.

DROP SCHEMA IF EXISTS authentication_demo CASCADE;
CREATE SCHEMA authentication_demo;
SET search_path = authentication_demo;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE user_status AS ENUM (
    'active',
    'disabled',
    'locked'
);

CREATE TYPE session_status AS ENUM (
    'active',
    'revoked',
    'expired'
);

CREATE TYPE refresh_token_status AS ENUM (
    'active',
    'rotated',
    'revoked',
    'expired'
);

CREATE TYPE authentication_method AS ENUM (
    'password',
    'session',
    'access_token',
    'refresh_token'
);

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    disabled_at TIMESTAMPTZ,

    CONSTRAINT users_username_not_blank
        CHECK (length(trim(username)) > 0),

    CONSTRAINT users_disabled_timestamp_consistency
        CHECK (
            (status = 'disabled' AND disabled_at IS NOT NULL)
            OR
            (status <> 'disabled' AND disabled_at IS NULL)
        )
);

CREATE UNIQUE INDEX users_username_lower_unique
    ON users (lower(username));

CREATE TABLE roles (
    role_id BIGSERIAL PRIMARY KEY,
    role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id BIGINT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    csrf_token_hash TEXT NOT NULL,
    status session_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    ip_address INET,
    user_agent TEXT,

    CONSTRAINT sessions_expiry_after_creation
        CHECK (expires_at > created_at)
);

CREATE INDEX sessions_user_status_idx
    ON sessions (user_id, status);

CREATE INDEX sessions_expiry_idx
    ON sessions (expires_at)
    WHERE status = 'active';

CREATE TABLE access_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,

    CONSTRAINT access_tokens_expiry_after_issue
        CHECK (expires_at > issued_at),

    CONSTRAINT access_tokens_revocation_consistency
        CHECK (
            (revoked_at IS NULL)
            OR
            (revoked_at >= issued_at)
        )
);

CREATE INDEX access_tokens_user_idx
    ON access_tokens (user_id);

CREATE INDEX access_tokens_expiry_idx
    ON access_tokens (expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE refresh_tokens (
    refresh_token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    status refresh_token_status NOT NULL DEFAULT 'active',
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    rotated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    replaced_by UUID REFERENCES refresh_tokens(refresh_token_id),

    CONSTRAINT refresh_tokens_expiry_after_issue
        CHECK (expires_at > issued_at),

    CONSTRAINT refresh_tokens_rotation_timestamp
        CHECK (
            (status <> 'rotated')
            OR
            (rotated_at IS NOT NULL AND replaced_by IS NOT NULL)
        )
);

CREATE INDEX refresh_tokens_user_status_idx
    ON refresh_tokens (user_id, status);

CREATE INDEX refresh_tokens_expiry_idx
    ON refresh_tokens (expires_at)
    WHERE status = 'active';

CREATE TABLE authentication_events (
    event_id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    method authentication_method NOT NULL,
    successful BOOLEAN NOT NULL,
    reason TEXT NOT NULL,
    ip_address INET,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX authentication_events_user_time_idx
    ON authentication_events (user_id, occurred_at DESC);

CREATE INDEX authentication_events_failures_idx
    ON authentication_events (occurred_at DESC)
    WHERE successful = false;

INSERT INTO roles (role_name)
VALUES
    ('user'),
    ('reviewer'),
    ('administrator')
ON CONFLICT (role_name) DO NOTHING;

INSERT INTO users (
    user_id,
    username,
    password_hash,
    status
)
VALUES
    (
        '00000000-0000-0000-0000-000000000001',
        'alice@example.com',
        'pbkdf2_sha256$310000$example-salt$example-derived-key',
        'active'
    ),
    (
        '00000000-0000-0000-0000-000000000002',
        'disabled@example.com',
        'pbkdf2_sha256$310000$example-salt$example-derived-key',
        'disabled'
    );

UPDATE users
SET disabled_at = now()
WHERE user_id = '00000000-0000-0000-0000-000000000002';

INSERT INTO user_roles (user_id, role_id)
SELECT
    '00000000-0000-0000-0000-000000000001',
    role_id
FROM roles
WHERE role_name IN ('user', 'reviewer');

INSERT INTO user_roles (user_id, role_id)
SELECT
    '00000000-0000-0000-0000-000000000002',
    role_id
FROM roles
WHERE role_name = 'user';

INSERT INTO sessions (
    session_id,
    user_id,
    csrf_token_hash,
    status,
    created_at,
    last_seen_at,
    expires_at,
    ip_address,
    user_agent
)
VALUES
    (
        '10000000-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        encode(digest('csrf-example-1', 'sha256'), 'hex'),
        'active',
        now() - interval '20 minutes',
        now() - interval '2 minutes',
        now() + interval '7 hours 40 minutes',
        '203.0.113.20',
        'ExampleBrowser/1.0'
    ),
    (
        '10000000-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        encode(digest('csrf-example-2', 'sha256'), 'hex'),
        'revoked',
        now() - interval '2 days',
        now() - interval '2 days',
        now() + interval '6 hours',
        '203.0.113.21',
        'ExampleBrowser/1.0'
    );

INSERT INTO access_tokens (
    token_id,
    user_id,
    token_hash,
    issued_at,
    expires_at
)
VALUES (
    '20000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    encode(
        digest('opaque-access-token-example', 'sha256'),
        'hex'
    ),
    now() - interval '2 minutes',
    now() + interval '8 minutes'
);

INSERT INTO refresh_tokens (
    refresh_token_id,
    user_id,
    token_hash,
    status,
    issued_at,
    expires_at
)
VALUES (
    '30000000-0000-0000-0000-000000000001',
    '00000000-0000-0000-0000-000000000001',
    encode(
        digest('refresh-token-example', 'sha256'),
        'hex'
    ),
    'active',
    now() - interval '1 day',
    now() + interval '29 days'
);

INSERT INTO authentication_events (
    user_id,
    method,
    successful,
    reason,
    ip_address
)
VALUES
    (
        '00000000-0000-0000-0000-000000000001',
        'password',
        true,
        'password accepted',
        '203.0.113.20'
    ),
    (
        '00000000-0000-0000-0000-000000000001',
        'password',
        false,
        'incorrect password',
        '198.51.100.40'
    ),
    (
        '00000000-0000-0000-0000-000000000001',
        'refresh_token',
        true,
        'refresh token rotated',
        '203.0.113.20'
    );

CREATE OR REPLACE VIEW active_authenticated_users AS
SELECT
    u.user_id,
    u.username,
    u.status,
    count(DISTINCT s.session_id) AS active_sessions,
    count(DISTINCT at.token_id) AS active_access_tokens
FROM users u
LEFT JOIN sessions s
    ON s.user_id = u.user_id
    AND s.status = 'active'
    AND s.expires_at > now()
LEFT JOIN access_tokens at
    ON at.user_id = u.user_id
    AND at.revoked_at IS NULL
    AND at.expires_at > now()
WHERE u.status = 'active'
GROUP BY u.user_id, u.username, u.status;

CREATE OR REPLACE FUNCTION revoke_user_authentication(
    target_user UUID
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE sessions
    SET status = 'revoked'
    WHERE user_id = target_user
      AND status = 'active';

    UPDATE access_tokens
    SET revoked_at = now()
    WHERE user_id = target_user
      AND revoked_at IS NULL;

    UPDATE refresh_tokens
    SET status = 'revoked',
        revoked_at = now()
    WHERE user_id = target_user
      AND status = 'active';
END;
$$;

CREATE OR REPLACE FUNCTION rotate_refresh_token(
    presented_hash TEXT
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    current_token refresh_tokens%ROWTYPE;
    replacement_id UUID;
BEGIN
    SELECT *
    INTO current_token
    FROM refresh_tokens
    WHERE token_hash = presented_hash
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown refresh token';
    END IF;

    IF current_token.status <> 'active' THEN
        RAISE EXCEPTION
            'Refresh token cannot be reused because its state is %',
            current_token.status;
    END IF;

    IF current_token.expires_at <= now() THEN
        UPDATE refresh_tokens
        SET status = 'expired'
        WHERE refresh_token_id = current_token.refresh_token_id;

        RAISE EXCEPTION 'Refresh token has expired';
    END IF;

    replacement_id := gen_random_uuid();

    INSERT INTO refresh_tokens (
        refresh_token_id,
        user_id,
        token_hash,
        status,
        issued_at,
        expires_at
    )
    VALUES (
        replacement_id,
        current_token.user_id,
        encode(
            digest(replacement_id::text || clock_timestamp()::text, 'sha256'),
            'hex'
        ),
        'active',
        now(),
        now() + interval '30 days'
    );

    UPDATE refresh_tokens
    SET status = 'rotated',
        rotated_at = now(),
        replaced_by = replacement_id
    WHERE refresh_token_id = current_token.refresh_token_id;

    RETURN replacement_id;
END;
$$;

-- A transaction demonstrates how application-level logout can be made
-- atomic with database-side state changes.
BEGIN;

SELECT revoke_user_authentication(
    '00000000-0000-0000-0000-000000000001'
);

INSERT INTO authentication_events (
    user_id,
    method,
    successful,
    reason,
    ip_address
)
VALUES (
    '00000000-0000-0000-0000-000000000001',
    'session',
    true,
    'administrative global logout',
    '203.0.113.99'
);

COMMIT;

-- Authentication versus authorization:
-- this query proves that a valid user identity and a granted role
-- are separate database facts.
SELECT
    u.username,
    r.role_name
FROM users u
JOIN user_roles ur
    ON ur.user_id = u.user_id
JOIN roles r
    ON r.role_id = ur.role_id
WHERE u.username = 'alice@example.com'
  AND u.status = 'active'
ORDER BY r.role_name;

-- Find sessions that require expiration cleanup.
SELECT
    session_id,
    user_id,
    status,
    expires_at
FROM sessions
WHERE status = 'active'
  AND expires_at <= now()
ORDER BY expires_at;

-- Find refresh tokens that should no longer be accepted.
SELECT
    refresh_token_id,
    user_id,
    status,
    expires_at
FROM refresh_tokens
WHERE status = 'active'
  AND expires_at <= now()
ORDER BY expires_at;

-- Authentication failure analysis identifies repeated failures
-- without exposing password material or token values.
SELECT
    ip_address,
    count(*) AS failed_attempts,
    min(occurred_at) AS first_failure,
    max(occurred_at) AS latest_failure
FROM authentication_events
WHERE successful = false
  AND occurred_at >= now() - interval '1 hour'
GROUP BY ip_address
HAVING count(*) >= 2
ORDER BY failed_attempts DESC;

-- Active authentication state after the administrative revocation.
SELECT *
FROM active_authenticated_users
ORDER BY username;

-- Database-level integrity test:
-- this statement intentionally attempts to violate the session lifetime rule.
-- It is commented out so the complete script remains executable.
--
-- INSERT INTO sessions (
--     user_id,
--     csrf_token_hash,
--     created_at,
--     last_seen_at,
--     expires_at
-- )
-- VALUES (
--     '00000000-0000-0000-0000-000000000001',
--     'invalid-test',
--     now(),
--     now(),
--     now() - interval '1 hour'
-- );
--
-- PostgreSQL would reject that row because expires_at must be later
-- than created_at.
