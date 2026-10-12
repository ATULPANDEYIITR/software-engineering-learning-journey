-- HTTP Deep Dive
-- PostgreSQL-compatible relational model for HTTP requests, responses,
-- headers, cookies, sessions, conditional requests, and status analysis.
--
-- The schema treats an HTTP exchange as observable protocol data while
-- retaining normalized entities for reusable resources, sessions, and
-- cookies.

DROP SCHEMA IF EXISTS http_deep_dive CASCADE;
CREATE SCHEMA http_deep_dive;

SET search_path TO http_deep_dive;

CREATE TYPE http_method AS ENUM (
    'GET',
    'HEAD',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
    'TRACE',
    'CONNECT'
);

CREATE TYPE status_class AS ENUM (
    'INFORMATIONAL',
    'SUCCESS',
    'REDIRECTION',
    'CLIENT_ERROR',
    'SERVER_ERROR'
);

CREATE TYPE cookie_same_site AS ENUM (
    'Strict',
    'Lax',
    'None'
);

CREATE TABLE repositories (
    repository_id BIGSERIAL PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE http_resources (
    resource_id BIGSERIAL PRIMARY KEY,
    repository_id BIGINT REFERENCES repositories(repository_id),
    resource_path TEXT NOT NULL,
    resource_name TEXT NOT NULL,
    current_etag TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, resource_path),
    CHECK (resource_path LIKE '/%'),
    CHECK (version > 0)
);

CREATE TABLE clients (
    client_id BIGSERIAL PRIMARY KEY,
    client_name TEXT NOT NULL UNIQUE,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    CHECK (expires_at > created_at),
    CHECK (revoked_at IS NULL OR revoked_at >= created_at)
);

CREATE TABLE cookies (
    cookie_id BIGSERIAL PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id),
    cookie_name TEXT NOT NULL,
    cookie_value TEXT NOT NULL,
    secure BOOLEAN NOT NULL DEFAULT FALSE,
    http_only BOOLEAN NOT NULL DEFAULT FALSE,
    same_site cookie_same_site NOT NULL DEFAULT 'Lax',
    path TEXT NOT NULL DEFAULT '/',
    max_age_seconds INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (cookie_name <> ''),
    CHECK (path LIKE '/%'),
    CHECK (max_age_seconds IS NULL OR max_age_seconds >= 0),
    CHECK (
        same_site <> 'None'
        OR secure = TRUE
    )
);

CREATE TABLE http_exchanges (
    exchange_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT REFERENCES clients(client_id),
    resource_id BIGINT REFERENCES http_resources(resource_id),
    method http_method NOT NULL,
    request_path TEXT NOT NULL,
    request_body BYTEA,
    request_received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    response_status INTEGER,
    response_reason TEXT,
    response_body BYTEA,
    response_sent_at TIMESTAMPTZ,
    CHECK (request_path LIKE '/%'),
    CHECK (
        response_status IS NULL
        OR response_status BETWEEN 100 AND 599
    ),
    CHECK (
        response_sent_at IS NULL
        OR response_sent_at >= request_received_at
    )
);

CREATE TABLE request_headers (
    exchange_id BIGINT NOT NULL REFERENCES http_exchanges(exchange_id)
        ON DELETE CASCADE,
    header_name TEXT NOT NULL,
    header_value TEXT NOT NULL,
    PRIMARY KEY (exchange_id, header_name)
);

CREATE TABLE response_headers (
    exchange_id BIGINT NOT NULL REFERENCES http_exchanges(exchange_id)
        ON DELETE CASCADE,
    header_name TEXT NOT NULL,
    header_value TEXT NOT NULL,
    PRIMARY KEY (exchange_id, header_name)
);

CREATE TABLE status_codes (
    status_code INTEGER PRIMARY KEY,
    reason_phrase TEXT NOT NULL,
    class status_class NOT NULL,
    cacheable_by_default BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE allowed_resource_methods (
    resource_id BIGINT NOT NULL REFERENCES http_resources(resource_id)
        ON DELETE CASCADE,
    method http_method NOT NULL,
    PRIMARY KEY (resource_id, method)
);

CREATE TABLE rate_limit_events (
    rate_limit_event_id BIGSERIAL PRIMARY KEY,
    client_id BIGINT NOT NULL REFERENCES clients(client_id),
    exchange_id BIGINT REFERENCES http_exchanges(exchange_id),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    allowed BOOLEAN NOT NULL,
    limit_per_window INTEGER NOT NULL,
    window_seconds INTEGER NOT NULL,
    retry_after_seconds INTEGER,
    CHECK (limit_per_window > 0),
    CHECK (window_seconds > 0),
    CHECK (
        retry_after_seconds IS NULL
        OR retry_after_seconds >= 0
    )
);

CREATE INDEX idx_http_exchanges_path
    ON http_exchanges(request_path);

CREATE INDEX idx_http_exchanges_method_status
    ON http_exchanges(method, response_status);

CREATE INDEX idx_http_exchanges_received_at
    ON http_exchanges(request_received_at);

CREATE INDEX idx_request_headers_name
    ON request_headers(header_name);

CREATE INDEX idx_response_headers_name
    ON response_headers(header_name);

CREATE INDEX idx_sessions_user
    ON sessions(user_id);

CREATE INDEX idx_sessions_expiry
    ON sessions(expires_at);

CREATE INDEX idx_rate_limit_client_time
    ON rate_limit_events(client_id, occurred_at);

INSERT INTO status_codes
    (status_code, reason_phrase, class, cacheable_by_default)
VALUES
    (200, 'OK', 'SUCCESS', TRUE),
    (201, 'Created', 'SUCCESS', FALSE),
    (204, 'No Content', 'SUCCESS', FALSE),
    (301, 'Moved Permanently', 'REDIRECTION', TRUE),
    (302, 'Found', 'REDIRECTION', FALSE),
    (304, 'Not Modified', 'REDIRECTION', TRUE),
    (307, 'Temporary Redirect', 'REDIRECTION', FALSE),
    (308, 'Permanent Redirect', 'REDIRECTION', TRUE),
    (400, 'Bad Request', 'CLIENT_ERROR', FALSE),
    (401, 'Unauthorized', 'CLIENT_ERROR', FALSE),
    (403, 'Forbidden', 'CLIENT_ERROR', FALSE),
    (404, 'Not Found', 'CLIENT_ERROR', FALSE),
    (405, 'Method Not Allowed', 'CLIENT_ERROR', FALSE),
    (409, 'Conflict', 'CLIENT_ERROR', FALSE),
    (412, 'Precondition Failed', 'CLIENT_ERROR', FALSE),
    (415, 'Unsupported Media Type', 'CLIENT_ERROR', FALSE),
    (422, 'Unprocessable Content', 'CLIENT_ERROR', FALSE),
    (429, 'Too Many Requests', 'CLIENT_ERROR', FALSE),
    (500, 'Internal Server Error', 'SERVER_ERROR', FALSE),
    (502, 'Bad Gateway', 'SERVER_ERROR', FALSE),
    (503, 'Service Unavailable', 'SERVER_ERROR', FALSE),
    (504, 'Gateway Timeout', 'SERVER_ERROR', FALSE);

INSERT INTO repositories
    (repository_name, base_url)
VALUES
    ('http-protocol-demo', 'https://api.example.test');

INSERT INTO users
    (username, display_name)
VALUES
    ('developer@example.test', 'Protocol Developer'),
    ('reviewer@example.test', 'API Reviewer');

INSERT INTO clients
    (client_name, user_agent)
VALUES
    ('browser-client', 'Mozilla/5.0 HTTPDeepDive'),
    ('service-client', 'HTTPDeepDive-Service/1.0'),
    ('integration-client', 'IntegrationBot/3.2');

INSERT INTO http_resources
    (
        repository_id,
        resource_path,
        resource_name,
        current_etag,
        version
    )
SELECT
    repository_id,
    '/resource',
    'HTTP protocol resource',
    '"resource-v3"',
    3
FROM repositories
WHERE repository_name = 'http-protocol-demo';

INSERT INTO allowed_resource_methods
    (resource_id, method)
SELECT
    resource_id,
    method
FROM http_resources
CROSS JOIN (
    VALUES
        ('GET'::http_method),
        ('HEAD'::http_method),
        ('POST'::http_method),
        ('PUT'::http_method),
        ('PATCH'::http_method),
        ('DELETE'::http_method),
        ('OPTIONS'::http_method)
) AS methods(method);

INSERT INTO sessions
    (
        session_id,
        user_id,
        expires_at
    )
SELECT
    '11111111-1111-1111-1111-111111111111',
    user_id,
    CURRENT_TIMESTAMP + INTERVAL '1 hour'
FROM users
WHERE username = 'developer@example.test';

INSERT INTO cookies
    (
        session_id,
        cookie_name,
        cookie_value,
        secure,
        http_only,
        same_site,
        path,
        max_age_seconds
    )
VALUES
    (
        '11111111-1111-1111-1111-111111111111',
        'session_id',
        'session-demo-001',
        TRUE,
        TRUE,
        'Lax',
        '/',
        3600
    );

INSERT INTO http_exchanges
    (
        client_id,
        resource_id,
        method,
        request_path,
        request_body,
        response_status,
        response_reason,
        response_body,
        response_sent_at
    )
SELECT
    c.client_id,
    r.resource_id,
    'GET',
    '/resource',
    NULL,
    200,
    'OK',
    '{"id":42,"name":"HTTP protocol resource","version":3}',
    CURRENT_TIMESTAMP + INTERVAL '20 milliseconds'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'browser-client';

INSERT INTO http_exchanges
    (
        client_id,
        resource_id,
        method,
        request_path,
        request_body,
        response_status,
        response_reason,
        response_body,
        response_sent_at
    )
SELECT
    c.client_id,
    r.resource_id,
    'GET',
    '/resource',
    NULL,
    304,
    'Not Modified',
    NULL,
    CURRENT_TIMESTAMP + INTERVAL '15 milliseconds'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'browser-client';

INSERT INTO http_exchanges
    (
        client_id,
        resource_id,
        method,
        request_path,
        request_body,
        response_status,
        response_reason,
        response_body,
        response_sent_at
    )
SELECT
    c.client_id,
    r.resource_id,
    'POST',
    '/resource',
    '{"name":"new resource"}'::bytea,
    201,
    'Created',
    '{"created":true}',
    CURRENT_TIMESTAMP + INTERVAL '30 milliseconds'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'service-client';

INSERT INTO http_exchanges
    (
        client_id,
        resource_id,
        method,
        request_path,
        request_body,
        response_status,
        response_reason,
        response_body,
        response_sent_at
    )
SELECT
    c.client_id,
    r.resource_id,
    'POST',
    '/resource',
    'name=new resource'::bytea,
    415,
    'Unsupported Media Type',
    '{"error":"application_json_required"}',
    CURRENT_TIMESTAMP + INTERVAL '8 milliseconds'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'integration-client';

INSERT INTO http_exchanges
    (
        client_id,
        resource_id,
        method,
        request_path,
        response_status,
        response_reason,
        response_sent_at
    )
SELECT
    c.client_id,
    r.resource_id,
    'GET',
    '/resource',
    429,
    'Too Many Requests',
    CURRENT_TIMESTAMP + INTERVAL '5 milliseconds'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'integration-client';

INSERT INTO request_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Accept',
    'application/json'
FROM http_exchanges
WHERE method = 'GET';

INSERT INTO request_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'If-None-Match',
    '"resource-v3"'
FROM http_exchanges
WHERE response_status = 304;

INSERT INTO request_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Content-Type',
    'application/json'
FROM http_exchanges
WHERE method = 'POST'
  AND response_status = 201;

INSERT INTO request_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Content-Type',
    'application/x-www-form-urlencoded'
FROM http_exchanges
WHERE response_status = 415;

INSERT INTO response_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'ETag',
    '"resource-v3"'
FROM http_exchanges
WHERE response_status IN (200, 304);

INSERT INTO response_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Cache-Control',
    'private, max-age=60'
FROM http_exchanges
WHERE response_status IN (200, 304);

INSERT INTO response_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Location',
    '/resource/43'
FROM http_exchanges
WHERE response_status = 201;

INSERT INTO response_headers
    (exchange_id, header_name, header_value)
SELECT
    exchange_id,
    'Retry-After',
    '10'
FROM http_exchanges
WHERE response_status = 429;

INSERT INTO rate_limit_events
    (
        client_id,
        exchange_id,
        allowed,
        limit_per_window,
        window_seconds,
        retry_after_seconds
    )
SELECT
    c.client_id,
    e.exchange_id,
    FALSE,
    100,
    60,
    10
FROM clients c
JOIN http_exchanges e
    ON e.client_id = c.client_id
WHERE c.client_name = 'integration-client'
  AND e.response_status = 429;

CREATE OR REPLACE FUNCTION classify_http_status(
    p_status INTEGER
)
RETURNS status_class
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_status BETWEEN 100 AND 199 THEN
        RETURN 'INFORMATIONAL';
    ELSIF p_status BETWEEN 200 AND 299 THEN
        RETURN 'SUCCESS';
    ELSIF p_status BETWEEN 300 AND 399 THEN
        RETURN 'REDIRECTION';
    ELSIF p_status BETWEEN 400 AND 499 THEN
        RETURN 'CLIENT_ERROR';
    ELSIF p_status BETWEEN 500 AND 599 THEN
        RETURN 'SERVER_ERROR';
    END IF;

    RAISE EXCEPTION 'Invalid HTTP status: %', p_status;
END;
$$;

CREATE OR REPLACE FUNCTION validate_cookie_security()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.same_site = 'None' AND NOT NEW.secure THEN
        RAISE EXCEPTION
            'SameSite=None cookies must be Secure';
    END IF;

    IF NEW.max_age_seconds IS NOT NULL
       AND NEW.max_age_seconds < 0 THEN
        RAISE EXCEPTION
            'Cookie Max-Age cannot be negative';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER cookie_security_validation
BEFORE INSERT OR UPDATE ON cookies
FOR EACH ROW
EXECUTE FUNCTION validate_cookie_security();

CREATE OR REPLACE VIEW http_exchange_analysis AS
SELECT
    e.exchange_id,
    c.client_name,
    e.method,
    e.request_path,
    e.response_status,
    e.response_reason,
    classify_http_status(e.response_status) AS response_class,
    e.request_received_at,
    e.response_sent_at,
    CASE
        WHEN e.response_sent_at IS NOT NULL
        THEN EXTRACT(
            EPOCH FROM (
                e.response_sent_at - e.request_received_at
            )
        ) * 1000
        ELSE NULL
    END AS latency_ms
FROM http_exchanges e
LEFT JOIN clients c
    ON c.client_id = e.client_id;

CREATE OR REPLACE VIEW resource_method_policy AS
SELECT
    r.resource_path,
    arm.method,
    CASE arm.method
        WHEN 'GET' THEN TRUE
        WHEN 'HEAD' THEN TRUE
        WHEN 'OPTIONS' THEN TRUE
        WHEN 'PUT' THEN TRUE
        WHEN 'DELETE' THEN TRUE
        ELSE FALSE
    END AS safe_or_idempotent_characteristics
FROM http_resources r
JOIN allowed_resource_methods arm
    ON arm.resource_id = r.resource_id;

-- Status distribution by protocol class.
SELECT
    response_class,
    COUNT(*) AS exchange_count
FROM http_exchange_analysis
GROUP BY response_class
ORDER BY response_class;

-- Requests that resulted in client errors.
SELECT
    exchange_id,
    client_name,
    method,
    request_path,
    response_status,
    response_reason
FROM http_exchange_analysis
WHERE response_class = 'CLIENT_ERROR'
ORDER BY exchange_id;

-- Conditional requests can be identified by If-None-Match.
SELECT
    e.exchange_id,
    e.request_path,
    rh.header_value AS supplied_etag,
    e.response_status
FROM http_exchanges e
JOIN request_headers rh
    ON rh.exchange_id = e.exchange_id
WHERE LOWER(rh.header_name) = 'if-none-match';

-- Compare resource ETag with ETag response metadata.
SELECT
    r.resource_path,
    r.current_etag,
    e.response_status,
    h.header_value AS response_etag
FROM http_resources r
JOIN http_exchanges e
    ON e.resource_id = r.resource_id
JOIN response_headers h
    ON h.exchange_id = e.exchange_id
WHERE LOWER(h.header_name) = 'etag';

-- Find cookies that satisfy the strongest demonstration policy.
SELECT
    cookie_name,
    secure,
    http_only,
    same_site,
    path,
    max_age_seconds
FROM cookies
WHERE secure = TRUE
  AND http_only = TRUE
  AND same_site IN ('Strict', 'Lax');

-- Detect sessions that are already expired or revoked.
SELECT
    s.session_id,
    u.username,
    s.expires_at,
    s.revoked_at
FROM sessions s
JOIN users u
    ON u.user_id = s.user_id
WHERE s.expires_at <= CURRENT_TIMESTAMP
   OR s.revoked_at IS NOT NULL;

-- Determine which methods are configured for the resource.
SELECT
    resource_path,
    ARRAY_AGG(method ORDER BY method) AS allowed_methods
FROM resource_method_policy
GROUP BY resource_path;

-- Examine latency for successful and failed responses.
SELECT
    response_class,
    ROUND(AVG(latency_ms)::numeric, 3) AS average_latency_ms,
    ROUND(MAX(latency_ms)::numeric, 3) AS maximum_latency_ms
FROM http_exchange_analysis
WHERE latency_ms IS NOT NULL
GROUP BY response_class
ORDER BY response_class;

-- Demonstrate database-level transaction behavior.
BEGIN;

INSERT INTO http_exchanges (
    client_id,
    resource_id,
    method,
    request_path,
    request_body,
    response_status,
    response_reason
)
SELECT
    c.client_id,
    r.resource_id,
    'OPTIONS',
    '/resource',
    NULL,
    204,
    'No Content'
FROM clients c
CROSS JOIN http_resources r
WHERE c.client_name = 'browser-client';

INSERT INTO response_headers (
    exchange_id,
    header_name,
    header_value
)
SELECT
    MAX(exchange_id),
    'Allow',
    'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'
FROM http_exchanges
WHERE method = 'OPTIONS'
  AND request_path = '/resource';

COMMIT;

-- This final query exposes the complete protocol-oriented event stream.
SELECT
    exchange_id,
    client_name,
    method,
    request_path,
    response_status,
    response_reason,
    response_class,
    latency_ms
FROM http_exchange_analysis
ORDER BY exchange_id;
