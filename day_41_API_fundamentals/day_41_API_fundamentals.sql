-- API Fundamentals: REST, resources, endpoints, and HTTP
-- PostgreSQL-compatible relational model.
--
-- The schema separates:
--   resources        -> domain objects exposed through REST
--   endpoints        -> HTTP operations available at URI templates
--   http_requests    -> protocol-level observations
--   api_responses    -> resulting HTTP status and representation metadata
--
-- Constraints enforce resource validity at the database boundary.

DROP SCHEMA IF EXISTS api_fundamentals CASCADE;
CREATE SCHEMA api_fundamentals;
SET search_path TO api_fundamentals;

CREATE TYPE resource_status AS ENUM (
    'active',
    'inactive',
    'maintenance'
);

CREATE TYPE http_method AS ENUM (
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS'
);

CREATE TABLE resources (
    resource_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(80) NOT NULL,
    status resource_status NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT resources_name_not_blank
        CHECK (length(trim(name)) > 0),
    CONSTRAINT resources_category_not_blank
        CHECK (length(trim(category)) > 0),
    CONSTRAINT resources_version_positive
        CHECK (version > 0),
    CONSTRAINT resources_name_unique
        UNIQUE (name)
);

CREATE TABLE endpoints (
    endpoint_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    path_template VARCHAR(200) NOT NULL,
    method http_method NOT NULL,
    description TEXT NOT NULL,
    resource_scope VARCHAR(30) NOT NULL,
    CONSTRAINT endpoints_scope_valid
        CHECK (resource_scope IN ('collection', 'member', 'system')),
    CONSTRAINT endpoints_path_method_unique
        UNIQUE (path_template, method)
);

CREATE TABLE api_clients (
    client_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_name VARCHAR(120) NOT NULL UNIQUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE http_requests (
    request_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_id BIGINT REFERENCES api_clients(client_id),
    endpoint_id BIGINT REFERENCES endpoints(endpoint_id),
    method http_method NOT NULL,
    request_path VARCHAR(500) NOT NULL,
    resource_id BIGINT REFERENCES resources(resource_id),
    content_type VARCHAR(100),
    accept_type VARCHAR(100),
    if_none_match VARCHAR(100),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE api_responses (
    response_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id BIGINT NOT NULL
        REFERENCES http_requests(request_id)
        ON DELETE CASCADE,
    status_code INTEGER NOT NULL,
    etag VARCHAR(100),
    location VARCHAR(300),
    response_content_type VARCHAR(100),
    response_time_ms INTEGER NOT NULL,
    CONSTRAINT response_status_valid
        CHECK (status_code BETWEEN 100 AND 599),
    CONSTRAINT response_time_nonnegative
        CHECK (response_time_ms >= 0)
);

CREATE TABLE resource_change_log (
    change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id BIGINT,
    old_version INTEGER,
    new_version INTEGER,
    operation http_method NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT change_versions_valid
        CHECK (
            old_version IS NULL
            OR new_version IS NULL
            OR new_version > old_version
        )
);

CREATE INDEX idx_resources_category
    ON resources(category);

CREATE INDEX idx_resources_status
    ON resources(status);

CREATE INDEX idx_http_requests_resource_time
    ON http_requests(resource_id, requested_at DESC);

CREATE INDEX idx_api_responses_status
    ON api_responses(status_code);

CREATE INDEX idx_endpoints_method
    ON endpoints(method);

INSERT INTO endpoints (
    path_template,
    method,
    description,
    resource_scope
)
VALUES
(
    '/api/v1/resources',
    'GET',
    'Retrieve a representation of the resource collection',
    'collection'
),
(
    '/api/v1/resources',
    'POST',
    'Create a new resource member',
    'collection'
),
(
    '/api/v1/resources/{id}',
    'GET',
    'Retrieve one resource representation',
    'member'
),
(
    '/api/v1/resources/{id}',
    'HEAD',
    'Retrieve representation metadata without a response body',
    'member'
),
(
    '/api/v1/resources/{id}',
    'PUT',
    'Replace the selected resource representation',
    'member'
),
(
    '/api/v1/resources/{id}',
    'PATCH',
    'Partially modify the selected resource',
    'member'
),
(
    '/api/v1/resources/{id}',
    'DELETE',
    'Remove the selected resource',
    'member'
),
(
    '/api/v1/health',
    'GET',
    'Return service health information',
    'system'
);

INSERT INTO api_clients (client_name)
VALUES
('Operations Dashboard'),
('Order Management Service'),
('Reporting Client');

INSERT INTO resources (name, category, status)
VALUES
('Identity API', 'security', 'active'),
('Order Processing API', 'application', 'active'),
('Reporting API', 'data', 'maintenance'),
('Notification API', 'application', 'active');

-- The transaction models creation of a resource together with an audit entry.
BEGIN;

WITH created AS (
    INSERT INTO resources (
        name,
        category,
        status
    )
    VALUES (
        'Payment API',
        'application',
        'active'
    )
    RETURNING resource_id, version
)
INSERT INTO resource_change_log (
    resource_id,
    old_version,
    new_version,
    operation
)
SELECT
    resource_id,
    NULL,
    version,
    'POST'
FROM created;

COMMIT;

-- An application would normally use a database transaction around an
-- update and its audit record so the resource cannot advance without its
-- corresponding history entry.
BEGIN;

WITH updated AS (
    UPDATE resources
    SET
        status = 'maintenance',
        version = version + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE name = 'Order Processing API'
    RETURNING resource_id, version
)
INSERT INTO resource_change_log (
    resource_id,
    old_version,
    new_version,
    operation
)
SELECT
    resource_id,
    version - 1,
    version,
    'PATCH'
FROM updated;

COMMIT;

-- A REST collection query. Pagination belongs to the representation of the
-- collection rather than changing the identity of an individual resource.
SELECT
    resource_id,
    name,
    category,
    status,
    version,
    created_at,
    updated_at
FROM resources
WHERE category = 'application'
ORDER BY resource_id
LIMIT 20
OFFSET 0;

-- Member-resource lookup.
SELECT
    resource_id,
    name,
    category,
    status,
    version,
    created_at,
    updated_at
FROM resources
WHERE resource_id = 2;

-- HTTP endpoint catalog.
SELECT
    method,
    path_template,
    resource_scope,
    description
FROM endpoints
ORDER BY
    resource_scope,
    path_template,
    method;

-- Simulate requests made against actual endpoints.
INSERT INTO http_requests (
    client_id,
    endpoint_id,
    method,
    request_path,
    resource_id,
    content_type,
    accept_type
)
SELECT
    c.client_id,
    e.endpoint_id,
    'GET',
    '/api/v1/resources/2',
    2,
    NULL,
    'application/json'
FROM api_clients c
JOIN endpoints e
    ON e.path_template = '/api/v1/resources/{id}'
    AND e.method = 'GET'
WHERE c.client_name = 'Operations Dashboard';

INSERT INTO api_responses (
    request_id,
    status_code,
    etag,
    response_content_type,
    response_time_ms
)
SELECT
    request_id,
    200,
    '"resource-2-v2"',
    'application/json',
    14
FROM http_requests
WHERE request_path = '/api/v1/resources/2'
ORDER BY request_id DESC
LIMIT 1;

-- A conditional GET can produce 304 when the client's ETag still matches.
INSERT INTO http_requests (
    client_id,
    endpoint_id,
    method,
    request_path,
    resource_id,
    if_none_match,
    accept_type
)
SELECT
    c.client_id,
    e.endpoint_id,
    'GET',
    '/api/v1/resources/2',
    2,
    '"resource-2-v2"',
    'application/json'
FROM api_clients c
JOIN endpoints e
    ON e.path_template = '/api/v1/resources/{id}'
    AND e.method = 'GET'
WHERE c.client_name = 'Reporting Client';

INSERT INTO api_responses (
    request_id,
    status_code,
    etag,
    response_content_type,
    response_time_ms
)
SELECT
    request_id,
    304,
    '"resource-2-v2"',
    'application/json',
    3
FROM http_requests
WHERE request_path = '/api/v1/resources/2'
ORDER BY request_id DESC
LIMIT 1;

-- Locate endpoint failures separately from successful protocol exchanges.
INSERT INTO http_requests (
    client_id,
    endpoint_id,
    method,
    request_path,
    accept_type
)
SELECT
    c.client_id,
    NULL,
    'GET',
    '/api/v1/does-not-exist',
    'application/json'
FROM api_clients c
WHERE c.client_name = 'Operations Dashboard';

INSERT INTO api_responses (
    request_id,
    status_code,
    response_content_type,
    response_time_ms
)
SELECT
    request_id,
    404,
    'application/json',
    2
FROM http_requests
WHERE request_path = '/api/v1/does-not-exist'
ORDER BY request_id DESC
LIMIT 1;

-- API health and performance analysis.
SELECT
    r.status_code,
    COUNT(*) AS response_count,
    ROUND(AVG(r.response_time_ms), 2) AS average_ms
FROM api_responses r
GROUP BY r.status_code
ORDER BY r.status_code;

-- Endpoint usage analysis connects HTTP behavior to resource operations.
SELECT
    e.method,
    e.path_template,
    COUNT(h.request_id) AS request_count,
    COUNT(*) FILTER (WHERE r.status_code >= 400) AS failure_count
FROM endpoints e
LEFT JOIN http_requests h
    ON h.endpoint_id = e.endpoint_id
LEFT JOIN api_responses r
    ON r.request_id = h.request_id
GROUP BY
    e.method,
    e.path_template
ORDER BY
    e.path_template,
    e.method;

-- Resource history shows that a REST representation can evolve through
-- mutations while the resource identifier remains stable.
SELECT
    r.name,
    r.version AS current_version,
    l.operation,
    l.old_version,
    l.new_version,
    l.changed_at
FROM resources r
LEFT JOIN resource_change_log l
    ON l.resource_id = r.resource_id
ORDER BY
    r.resource_id,
    l.changed_at;

-- Database-level validation exposes invalid resource states.
-- The following statement is intentionally commented out because it would
-- fail the resources_status enum constraint:
--
-- INSERT INTO resources(name, category, status)
-- VALUES ('Invalid API', 'application', 'deleted');

-- The unique resource-name constraint prevents accidental duplicate domain
-- identities even when requests arrive concurrently.
-- The following statement is intentionally commented out because it violates
-- the database constraint:
--
-- INSERT INTO resources(name, category, status)
-- VALUES ('Order Processing API', 'application', 'active');

-- A CTE can calculate the proportion of unsuccessful HTTP responses.
WITH response_totals AS (
    SELECT
        COUNT(*) AS total,
        COUNT(*) FILTER (
            WHERE status_code >= 400
        ) AS failures
    FROM api_responses
)
SELECT
    total,
    failures,
    ROUND(
        failures::numeric / NULLIF(total, 0) * 100,
        2
    ) AS failure_percentage
FROM response_totals;
