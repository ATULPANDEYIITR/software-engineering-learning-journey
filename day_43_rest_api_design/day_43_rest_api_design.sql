-- REST API DESIGN
-- PostgreSQL-compatible relational model for:
-- URI resources, API versions, pagination policies,
-- repositories of API clients, requests, and version lifecycle.
--
-- The database does not attempt to replace an HTTP server.
-- It enforces durable API-governance rules that an application
-- should not be able to violate accidentally.

DROP SCHEMA IF EXISTS rest_api_lab CASCADE;
CREATE SCHEMA rest_api_lab;

SET search_path TO rest_api_lab;

CREATE TYPE api_version_state AS ENUM (
    'active',
    'deprecated',
    'retired'
);

CREATE TYPE pagination_type AS ENUM (
    'page_number',
    'cursor'
);

CREATE TYPE http_method AS ENUM (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS'
);

CREATE TYPE request_outcome AS ENUM (
    'accepted',
    'rejected'
);

CREATE TABLE api_versions (
    version_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_code TEXT NOT NULL UNIQUE,
    state api_version_state NOT NULL,
    released_at DATE NOT NULL,
    sunset_at DATE,
    CHECK (
        sunset_at IS NULL
        OR sunset_at >= released_at
    ),
    CHECK (
        state <> 'deprecated'
        OR sunset_at IS NOT NULL
    )
);

CREATE TABLE api_resources (
    resource_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_name TEXT NOT NULL UNIQUE,
    collection_uri TEXT NOT NULL UNIQUE,
    item_uri_template TEXT NOT NULL,
    supports_pagination BOOLEAN NOT NULL DEFAULT FALSE,
    pagination_type pagination_type,
    CHECK (
        supports_pagination = TRUE
        OR pagination_type IS NULL
    ),
    CHECK (
        supports_pagination = FALSE
        OR pagination_type IS NOT NULL
    ),
    CHECK (
        collection_uri LIKE '/api/%'
    ),
    CHECK (
        item_uri_template LIKE '/api/%/{id}'
    )
);

CREATE TABLE api_resource_versions (
    resource_id BIGINT NOT NULL
        REFERENCES api_resources(resource_id)
        ON DELETE CASCADE,
    version_id BIGINT NOT NULL
        REFERENCES api_versions(version_id)
        ON DELETE RESTRICT,
    collection_uri TEXT NOT NULL UNIQUE,
    item_uri_template TEXT NOT NULL,
    PRIMARY KEY (resource_id, version_id),
    CHECK (collection_uri LIKE '/api/%'),
    CHECK (item_uri_template LIKE '/api/%/{id}')
);

CREATE TABLE pagination_policies (
    pagination_policy_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pagination_type pagination_type NOT NULL UNIQUE,
    default_page_size INTEGER NOT NULL,
    maximum_page_size INTEGER NOT NULL,
    allow_page_number BOOLEAN NOT NULL,
    allow_cursor BOOLEAN NOT NULL,
    CHECK (default_page_size > 0),
    CHECK (maximum_page_size >= default_page_size),
    CHECK (
        allow_page_number
        OR allow_cursor
    )
);

CREATE TABLE api_clients (
    client_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_name TEXT NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_requests (
    request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id BIGINT
        REFERENCES api_clients(client_id)
        ON DELETE SET NULL,
    version_id BIGINT
        REFERENCES api_versions(version_id)
        ON DELETE RESTRICT,
    resource_id BIGINT
        REFERENCES api_resources(resource_id)
        ON DELETE RESTRICT,
    method http_method NOT NULL,
    request_path TEXT NOT NULL,
    page_number INTEGER,
    page_size INTEGER,
    cursor_value TEXT,
    outcome request_outcome NOT NULL,
    status_code INTEGER NOT NULL,
    rejection_reason TEXT,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        page_number IS NULL
        OR page_number > 0
    ),
    CHECK (
        page_size IS NULL
        OR page_size > 0
    ),
    CHECK (
        status_code BETWEEN 100 AND 599
    ),
    CHECK (
        outcome = 'accepted'
        OR rejection_reason IS NOT NULL
    ),
    CHECK (
        NOT (
            page_number IS NOT NULL
            AND cursor_value IS NOT NULL
        )
    )
);

CREATE INDEX idx_api_requests_version_time
ON api_requests (version_id, requested_at DESC);

CREATE INDEX idx_api_requests_resource_time
ON api_requests (resource_id, requested_at DESC);

CREATE INDEX idx_api_requests_status
ON api_requests (status_code);

CREATE INDEX idx_api_requests_client_time
ON api_requests (client_id, requested_at DESC);

INSERT INTO api_versions (
    version_code,
    state,
    released_at,
    sunset_at
)
VALUES
    ('v1', 'active', DATE '2025-01-15', NULL),
    ('v2', 'deprecated', DATE '2026-02-01', DATE '2027-06-30'),
    ('v0', 'retired', DATE '2023-01-01', DATE '2026-01-31');

INSERT INTO api_resources (
    resource_name,
    collection_uri,
    item_uri_template,
    supports_pagination,
    pagination_type
)
VALUES
    (
        'books',
        '/api/v1/books',
        '/api/v1/books/{id}',
        TRUE,
        'page_number'
    ),
    (
        'orders',
        '/api/v1/orders',
        '/api/v1/orders/{id}',
        TRUE,
        'cursor'
    ),
    (
        'health',
        '/api/v1/health',
        '/api/v1/health',
        FALSE,
        NULL
    );

INSERT INTO api_resource_versions (
    resource_id,
    version_id,
    collection_uri,
    item_uri_template
)
SELECT
    resource_id,
    version_id,
    CASE
        WHEN version_code = 'v1'
            THEN '/api/v1/books'
        WHEN version_code = 'v2'
            THEN '/api/v2/books'
    END,
    CASE
        WHEN version_code = 'v1'
            THEN '/api/v1/books/{id}'
        WHEN version_code = 'v2'
            THEN '/api/v2/books/{id}'
    END
FROM api_resources
CROSS JOIN api_versions
WHERE resource_name = 'books'
  AND version_code IN ('v1', 'v2');

INSERT INTO api_resource_versions (
    resource_id,
    version_id,
    collection_uri,
    item_uri_template
)
SELECT
    resource_id,
    version_id,
    CASE
        WHEN version_code = 'v1'
            THEN '/api/v1/orders'
        WHEN version_code = 'v2'
            THEN '/api/v2/orders'
    END,
    CASE
        WHEN version_code = 'v1'
            THEN '/api/v1/orders/{id}'
        WHEN version_code = 'v2'
            THEN '/api/v2/orders/{id}'
    END
FROM api_resources
CROSS JOIN api_versions
WHERE resource_name = 'orders'
  AND version_code IN ('v1', 'v2');

INSERT INTO pagination_policies (
    pagination_type,
    default_page_size,
    maximum_page_size,
    allow_page_number,
    allow_cursor
)
VALUES
    ('page_number', 20, 100, TRUE, FALSE),
    ('cursor', 50, 100, FALSE, TRUE);

INSERT INTO api_clients (client_name)
VALUES
    ('web-portal'),
    ('mobile-app'),
    ('partner-integration');

-- Valid requests demonstrate separate collection and item URIs.
INSERT INTO api_requests (
    client_id,
    version_id,
    resource_id,
    method,
    request_path,
    page_number,
    page_size,
    outcome,
    status_code
)
SELECT
    c.client_id,
    v.version_id,
    r.resource_id,
    'GET',
    '/api/v1/books',
    1,
    20,
    'accepted',
    200
FROM api_clients c
CROSS JOIN api_versions v
CROSS JOIN api_resources r
WHERE c.client_name = 'web-portal'
  AND v.version_code = 'v1'
  AND r.resource_name = 'books';

INSERT INTO api_requests (
    client_id,
    version_id,
    resource_id,
    method,
    request_path,
    cursor_value,
    outcome,
    status_code
)
SELECT
    c.client_id,
    v.version_id,
    r.resource_id,
    'GET',
    '/api/v1/orders',
    'eyJpZCI6MTAw',
    'accepted',
    200
FROM api_clients c
CROSS JOIN api_versions v
CROSS JOIN api_resources r
WHERE c.client_name = 'partner-integration'
  AND v.version_code = 'v1'
  AND r.resource_name = 'orders';

-- A deprecated API version can remain callable while
-- the server signals migration requirements.
INSERT INTO api_requests (
    client_id,
    version_id,
    resource_id,
    method,
    request_path,
    page_number,
    page_size,
    outcome,
    status_code,
    rejection_reason
)
SELECT
    c.client_id,
    v.version_id,
    r.resource_id,
    'GET',
    '/api/v2/books',
    1,
    20,
    'accepted',
    200,
    'Deprecated API version; migrate before sunset.'
FROM api_clients c
CROSS JOIN api_versions v
CROSS JOIN api_resources r
WHERE c.client_name = 'mobile-app'
  AND v.version_code = 'v2'
  AND r.resource_name = 'books';

-- A retired API version must not be accepted.
INSERT INTO api_requests (
    client_id,
    version_id,
    resource_id,
    method,
    request_path,
    page_number,
    page_size,
    outcome,
    status_code,
    rejection_reason
)
SELECT
    c.client_id,
    v.version_id,
    r.resource_id,
    'GET',
    '/api/v0/books',
    1,
    20,
    'rejected',
    410,
    'API version is retired.'
FROM api_clients c
CROSS JOIN api_versions v
CROSS JOIN api_resources r
WHERE c.client_name = 'web-portal'
  AND v.version_code = 'v0'
  AND r.resource_name = 'books';

-- An excessive page size is rejected before application
-- processing can attempt to retrieve a large result set.
INSERT INTO api_requests (
    client_id,
    version_id,
    resource_id,
    method,
    request_path,
    page_number,
    page_size,
    outcome,
    status_code,
    rejection_reason
)
SELECT
    c.client_id,
    v.version_id,
    r.resource_id,
    'GET',
    '/api/v1/books',
    1,
    500,
    'rejected',
    400,
    'page_size exceeds maximum_page_size.'
FROM api_clients c
CROSS JOIN api_versions v
CROSS JOIN api_resources r
WHERE c.client_name = 'mobile-app'
  AND v.version_code = 'v1'
  AND r.resource_name = 'books';

-- This query exposes the API's version lifecycle.
SELECT
    version_code,
    state,
    released_at,
    sunset_at
FROM api_versions
ORDER BY released_at;

-- This query shows which resources support which pagination models.
SELECT
    resource_name,
    collection_uri,
    pagination_type,
    p.default_page_size,
    p.maximum_page_size
FROM api_resources r
LEFT JOIN pagination_policies p
    ON p.pagination_type = r.pagination_type
ORDER BY resource_name;

-- Operational view of rejected requests.
CREATE VIEW rejected_requests AS
SELECT
    ar.request_id,
    c.client_name,
    v.version_code,
    r.resource_name,
    ar.method,
    ar.request_path,
    ar.status_code,
    ar.rejection_reason,
    ar.requested_at
FROM api_requests ar
LEFT JOIN api_clients c
    ON c.client_id = ar.client_id
LEFT JOIN api_versions v
    ON v.version_id = ar.version_id
LEFT JOIN api_resources r
    ON r.resource_id = ar.resource_id
WHERE ar.outcome = 'rejected';

SELECT *
FROM rejected_requests
ORDER BY requested_at DESC;

-- Detect page-size violations in recorded traffic.
SELECT
    ar.request_id,
    ar.request_path,
    ar.page_size,
    pp.maximum_page_size,
    ar.status_code
FROM api_requests ar
JOIN api_resources r
    ON r.resource_id = ar.resource_id
JOIN pagination_policies pp
    ON pp.pagination_type = r.pagination_type
WHERE ar.page_size IS NOT NULL
  AND ar.page_size > pp.maximum_page_size;

-- Detect requests that mix pagination models.
-- The table constraint prevents this state from being inserted,
-- so this query should return zero rows.
SELECT
    request_id,
    request_path,
    page_number,
    cursor_value
FROM api_requests
WHERE page_number IS NOT NULL
  AND cursor_value IS NOT NULL;

-- Version usage is useful when planning a deprecation migration.
SELECT
    v.version_code,
    v.state,
    COUNT(ar.request_id) AS request_count
FROM api_versions v
LEFT JOIN api_requests ar
    ON ar.version_id = v.version_id
GROUP BY
    v.version_code,
    v.state
ORDER BY request_count DESC;

-- Transactional example: register a new API version and its
-- resource representation atomically. If any statement fails,
-- no partial version is committed.
BEGIN;

INSERT INTO api_versions (
    version_code,
    state,
    released_at,
    sunset_at
)
VALUES (
    'v3',
    'active',
    CURRENT_DATE,
    NULL
);

INSERT INTO api_resource_versions (
    resource_id,
    version_id,
    collection_uri,
    item_uri_template
)
SELECT
    r.resource_id,
    v.version_id,
    '/api/v3/books',
    '/api/v3/books/{id}'
FROM api_resources r
JOIN api_versions v
    ON v.version_code = 'v3'
WHERE r.resource_name = 'books';

COMMIT;

-- Verify the new version is registered consistently.
SELECT
    v.version_code,
    v.state,
    r.resource_name,
    rv.collection_uri,
    rv.item_uri_template
FROM api_resource_versions rv
JOIN api_versions v
    ON v.version_id = rv.version_id
JOIN api_resources r
    ON r.resource_id = rv.resource_id
WHERE v.version_code = 'v3';
