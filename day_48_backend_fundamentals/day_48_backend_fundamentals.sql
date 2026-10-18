DROP SCHEMA IF EXISTS backend_fundamentals CASCADE;
CREATE SCHEMA backend_fundamentals;
SET search_path TO backend_fundamentals;

-- PostgreSQL model for a backend service.
-- The database stores the resources and execution metadata that sit behind
-- an HTTP server. Routing itself normally lives in the application layer,
-- while relational constraints enforce durable domain invariants.

CREATE TYPE http_method AS ENUM (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE'
);

CREATE TYPE route_kind AS ENUM (
    'static',
    'parameterized'
);

CREATE TYPE request_status AS ENUM (
    'received',
    'authenticated',
    'authorized',
    'handled',
    'failed'
);

CREATE TYPE user_role AS ENUM (
    'user',
    'reviewer',
    'admin'
);

CREATE TABLE api_users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT username_length
        CHECK (char_length(username) BETWEEN 3 AND 80),
    CONSTRAINT display_name_not_blank
        CHECK (btrim(display_name) <> '')
);

CREATE TABLE api_routes (
    route_id BIGSERIAL PRIMARY KEY,
    method http_method NOT NULL,
    path_pattern TEXT NOT NULL,
    route_kind route_kind NOT NULL,
    handler_name TEXT NOT NULL,
    requires_authentication BOOLEAN NOT NULL DEFAULT FALSE,
    required_role user_role,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT route_pattern_valid
        CHECK (path_pattern LIKE '/%'),
    CONSTRAINT parameterized_route_has_parameter
        CHECK (
            route_kind = 'static'
            OR path_pattern LIKE '%:%'
        ),
    CONSTRAINT role_requires_authentication
        CHECK (
            required_role IS NULL
            OR requires_authentication = TRUE
        )
);

CREATE UNIQUE INDEX api_routes_method_path_unique
ON api_routes(method, path_pattern);

CREATE INDEX api_routes_lookup_idx
ON api_routes(method, enabled, path_pattern);

CREATE TABLE http_requests (
    request_id UUID PRIMARY KEY,
    method http_method NOT NULL,
    target_path TEXT NOT NULL,
    query_string TEXT,
    remote_address INET,
    user_id BIGINT REFERENCES api_users(user_id),
    route_id BIGINT REFERENCES api_routes(route_id),
    status request_status NOT NULL DEFAULT 'received',
    response_status INTEGER,
    response_bytes INTEGER,
    duration_microseconds BIGINT,
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,
    CONSTRAINT response_status_valid
        CHECK (
            response_status IS NULL
            OR response_status BETWEEN 100 AND 599
        ),
    CONSTRAINT response_bytes_valid
        CHECK (
            response_bytes IS NULL
            OR response_bytes >= 0
        ),
    CONSTRAINT duration_valid
        CHECK (
            duration_microseconds IS NULL
            OR duration_microseconds >= 0
        )
);

CREATE INDEX http_requests_route_time_idx
ON http_requests(route_id, received_at DESC);

CREATE INDEX http_requests_status_time_idx
ON http_requests(response_status, received_at DESC);

CREATE INDEX http_requests_user_time_idx
ON http_requests(user_id, received_at DESC);

CREATE TABLE middleware_execution (
    execution_id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL
        REFERENCES http_requests(request_id)
        ON DELETE CASCADE,
    middleware_name TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    allowed_to_continue BOOLEAN NOT NULL,
    failure_status INTEGER,
    execution_microseconds BIGINT NOT NULL DEFAULT 0,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT middleware_sequence_positive
        CHECK (sequence_number > 0),
    CONSTRAINT middleware_duration_nonnegative
        CHECK (execution_microseconds >= 0),
    CONSTRAINT middleware_failure_status_valid
        CHECK (
            failure_status IS NULL
            OR failure_status BETWEEN 400 AND 599
        )
);

CREATE UNIQUE INDEX middleware_request_sequence_unique
ON middleware_execution(request_id, sequence_number);

CREATE TABLE request_errors (
    error_id BIGSERIAL PRIMARY KEY,
    request_id UUID NOT NULL
        REFERENCES http_requests(request_id)
        ON DELETE CASCADE,
    error_code TEXT NOT NULL,
    http_status INTEGER NOT NULL,
    message TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT error_status_valid
        CHECK (http_status BETWEEN 400 AND 599)
);

CREATE INDEX request_errors_request_idx
ON request_errors(request_id);

CREATE TABLE api_tokens (
    token_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL
        REFERENCES api_users(user_id)
        ON DELETE CASCADE,
    token_fingerprint TEXT NOT NULL UNIQUE,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT token_dates_valid
        CHECK (
            expires_at IS NULL
            OR expires_at > issued_at
        ),
    CONSTRAINT revoked_after_issue
        CHECK (
            revoked_at IS NULL
            OR revoked_at >= issued_at
        )
);

-- Raw bearer tokens are deliberately not stored. A real service stores a
-- secure token hash/fingerprint and compares a derived representation.
CREATE INDEX api_tokens_user_active_idx
ON api_tokens(user_id)
WHERE revoked_at IS NULL;

INSERT INTO api_users (
    username,
    display_name,
    role
)
VALUES
    ('asha', 'Asha Sharma', 'user'),
    ('ravi-reviewer', 'Ravi Mehta', 'reviewer'),
    ('platform-admin', 'Platform Administrator', 'admin');

INSERT INTO api_routes (
    method,
    path_pattern,
    route_kind,
    handler_name,
    requires_authentication,
    required_role
)
VALUES
    ('GET', '/health', 'static', 'health_handler', FALSE, NULL),
    ('GET', '/users', 'static', 'list_users_handler', FALSE, NULL),
    ('GET', '/users/:id', 'parameterized', 'get_user_handler', FALSE, NULL),
    ('POST', '/users', 'static', 'create_user_handler', TRUE, 'admin'),
    ('DELETE', '/users/:id', 'parameterized', 'delete_user_handler', TRUE, 'admin');

INSERT INTO api_tokens (
    user_id,
    token_fingerprint,
    expires_at
)
SELECT
    user_id,
    'fingerprint-admin-demo',
    CURRENT_TIMESTAMP + INTERVAL '30 days'
FROM api_users
WHERE username = 'platform-admin';

-- A normal successful request passes through routing and middleware before
-- the endpoint produces an HTTP response.
INSERT INTO http_requests (
    request_id,
    method,
    target_path,
    query_string,
    remote_address,
    user_id,
    route_id,
    status,
    response_status,
    response_bytes,
    duration_microseconds,
    completed_at
)
SELECT
    '11111111-1111-1111-1111-111111111111',
    'GET',
    '/users/1001',
    NULL,
    '192.0.2.10',
    NULL,
    route_id,
    'handled',
    200,
    142,
    850,
    CURRENT_TIMESTAMP
FROM api_routes
WHERE method = 'GET'
  AND path_pattern = '/users/:id';

INSERT INTO middleware_execution (
    request_id,
    middleware_name,
    sequence_number,
    allowed_to_continue,
    execution_microseconds
)
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        'request_id',
        1,
        TRUE,
        12
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'security_headers',
        2,
        TRUE,
        8
    ),
    (
        '11111111-1111-1111-1111-111111111111',
        'request_logging',
        3,
        TRUE,
        17
    );

-- An unauthorized administrative request reaches the authentication
-- middleware but is rejected before the route handler executes.
INSERT INTO http_requests (
    request_id,
    method,
    target_path,
    query_string,
    remote_address,
    route_id,
    status,
    response_status,
    response_bytes,
    duration_microseconds,
    completed_at
)
SELECT
    '22222222-2222-2222-2222-222222222222',
    'POST',
    '/users',
    NULL,
    '198.51.100.20',
    route_id,
    'failed',
    401,
    118,
    410,
    CURRENT_TIMESTAMP
FROM api_routes
WHERE method = 'POST'
  AND path_pattern = '/users';

INSERT INTO middleware_execution (
    request_id,
    middleware_name,
    sequence_number,
    allowed_to_continue,
    failure_status,
    execution_microseconds
)
VALUES
    (
        '22222222-2222-2222-2222-222222222222',
        'request_id',
        1,
        TRUE,
        NULL,
        10
    ),
    (
        '22222222-2222-2222-2222-222222222222',
        'authentication',
        2,
        FALSE,
        401,
        19
    );

INSERT INTO request_errors (
    request_id,
    error_code,
    http_status,
    message
)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'unauthorized',
    401,
    'A valid authentication credential is required.'
);

-- A route can exist while a request uses an unsupported HTTP method.
-- This query exposes candidate methods before the application returns 405.
SELECT
    path_pattern,
    string_agg(method::TEXT, ', ' ORDER BY method::TEXT) AS allowed_methods
FROM api_routes
WHERE path_pattern = '/users'
  AND enabled = TRUE
GROUP BY path_pattern;

-- Route inventory shows which endpoints are public and which are protected.
SELECT
    method,
    path_pattern,
    route_kind,
    handler_name,
    requires_authentication,
    required_role
FROM api_routes
WHERE enabled
ORDER BY
    path_pattern,
    method;

-- Middleware failures identify where requests are rejected.
SELECT
    middleware_name,
    COUNT(*) AS executions,
    COUNT(*) FILTER (
        WHERE allowed_to_continue = FALSE
    ) AS blocked_requests,
    AVG(execution_microseconds)::NUMERIC(12, 2)
        AS average_microseconds
FROM middleware_execution
GROUP BY middleware_name
ORDER BY blocked_requests DESC, middleware_name;

-- Endpoint-level latency provides a database-side operational view.
SELECT
    r.method,
    r.path_pattern,
    COUNT(h.request_id) AS request_count,
    ROUND(
        AVG(h.duration_microseconds),
        2
    ) AS average_duration_us,
    MAX(h.duration_microseconds) AS maximum_duration_us,
    COUNT(*) FILTER (
        WHERE h.response_status >= 400
    ) AS failed_requests
FROM api_routes r
LEFT JOIN http_requests h
    ON h.route_id = r.route_id
GROUP BY r.method, r.path_pattern
ORDER BY average_duration_us DESC NULLS LAST;

-- The following function evaluates whether a request can reach a protected
-- handler based on route policy and the authenticated user's role.
CREATE OR REPLACE FUNCTION route_access_allowed(
    p_route_id BIGINT,
    p_user_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT
        r.enabled
        AND (
            NOT r.requires_authentication
            OR (
                p_user_id IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM api_users u
                    WHERE u.user_id = p_user_id
                      AND u.active
                      AND (
                          r.required_role IS NULL
                          OR u.role = r.required_role
                      )
                )
            )
        )
    FROM api_routes r
    WHERE r.route_id = p_route_id
$$;

-- Public health route can be reached without a user.
SELECT
    route_id,
    method,
    path_pattern,
    route_access_allowed(route_id, NULL)
        AS anonymous_access
FROM api_routes
WHERE path_pattern = '/health';

-- The admin can access the protected POST route.
SELECT
    route_id,
    method,
    path_pattern,
    route_access_allowed(
        route_id,
        (
            SELECT user_id
            FROM api_users
            WHERE username = 'platform-admin'
        )
    ) AS admin_access
FROM api_routes
WHERE method = 'POST'
  AND path_pattern = '/users';

-- The ordinary user cannot satisfy the same admin policy.
SELECT
    route_access_allowed(
        (
            SELECT route_id
            FROM api_routes
            WHERE method = 'POST'
              AND path_pattern = '/users'
        ),
        (
            SELECT user_id
            FROM api_users
            WHERE username = 'asha'
        )
    ) AS ordinary_user_can_create_users;

-- Transactional insertion keeps request metadata and its middleware audit
-- records consistent. If any statement fails, the complete audit operation
-- can be rolled back rather than leaving a partial request record.
BEGIN;

INSERT INTO http_requests (
    request_id,
    method,
    target_path,
    remote_address,
    status
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    'GET',
    '/health',
    '203.0.113.30',
    'received'
);

INSERT INTO middleware_execution (
    request_id,
    middleware_name,
    sequence_number,
    allowed_to_continue,
    execution_microseconds
)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    'request_id',
    1,
    TRUE,
    7
);

UPDATE http_requests
SET
    status = 'handled',
    response_status = 200,
    response_bytes = 72,
    duration_microseconds = 390,
    completed_at = CURRENT_TIMESTAMP
WHERE request_id =
    '33333333-3333-3333-3333-333333333333';

COMMIT;

-- Database constraints reject malformed states such as a role-specific
-- route that does not require authentication. The following transaction
-- demonstrates the constraint without permanently changing the schema.
BEGIN;

SAVEPOINT invalid_route_test;

-- This statement violates role_requires_authentication because an admin
-- role is specified while authentication is disabled.
DO $$
BEGIN
    BEGIN
        INSERT INTO api_routes (
            method,
            path_pattern,
            route_kind,
            handler_name,
            requires_authentication,
            required_role
        )
        VALUES (
            'GET',
            '/invalid-admin-route',
            'static',
            'invalid_handler',
            FALSE,
            'admin'
        );
    EXCEPTION
        WHEN check_violation THEN
            RAISE NOTICE
                'Database correctly rejected an unauthenticated role-protected route.';
    END;
END;
$$;

ROLLBACK TO SAVEPOINT invalid_route_test;
COMMIT;

-- Operational view: a single query exposes route, authentication policy,
-- response outcome, and request latency.
CREATE OR REPLACE VIEW route_runtime_metrics AS
SELECT
    r.route_id,
    r.method,
    r.path_pattern,
    r.requires_authentication,
    r.required_role,
    COUNT(h.request_id) AS requests,
    COUNT(*) FILTER (
        WHERE h.response_status BETWEEN 200 AND 399
    ) AS successful_responses,
    COUNT(*) FILTER (
        WHERE h.response_status >= 400
    ) AS failed_responses,
    ROUND(
        AVG(h.duration_microseconds),
        2
    ) AS average_duration_us
FROM api_routes r
LEFT JOIN http_requests h
    ON h.route_id = r.route_id
GROUP BY
    r.route_id,
    r.method,
    r.path_pattern,
    r.requires_authentication,
    r.required_role;

SELECT *
FROM route_runtime_metrics
ORDER BY path_pattern, method;
