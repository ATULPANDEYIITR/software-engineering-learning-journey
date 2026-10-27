DROP SCHEMA IF EXISTS nosql_lab CASCADE;
CREATE SCHEMA nosql_lab;

SET search_path TO nosql_lab;

-- The relational model is used here as a durable laboratory representation
-- of four NoSQL data models. JSONB represents document aggregates,
-- key/value rows represent direct lookup state, sparse columns represent
-- wide-column records, and node/edge tables represent a property graph.

CREATE TYPE nosql_model AS ENUM (
    'document',
    'key_value',
    'column_family',
    'graph'
);

CREATE TYPE document_state AS ENUM (
    'active',
    'archived',
    'blocked'
);

CREATE TYPE review_state AS ENUM (
    'new',
    'processing',
    'failed',
    'complete'
);

CREATE TABLE repositories (
    repository_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(repository_name)) >= 2)
);

CREATE TABLE document_records (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    document_key TEXT NOT NULL,
    payload JSONB NOT NULL,
    state document_state NOT NULL DEFAULT 'active',
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (repository_id, document_key),
    CHECK (jsonb_typeof(payload) = 'object'),
    CHECK (version > 0)
);

CREATE INDEX idx_document_payload_gin
    ON document_records USING GIN (payload);

CREATE INDEX idx_document_repository_state
    ON document_records(repository_id, state);

CREATE TABLE key_value_records (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    expires_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(key)) BETWEEN 1 AND 256),
    CHECK (version > 0)
);

CREATE INDEX idx_key_value_expiry
    ON key_value_records(expires_at)
    WHERE expires_at IS NOT NULL;

CREATE TABLE column_family_rows (
    row_key TEXT PRIMARY KEY,
    region TEXT,
    signal_quality INTEGER,
    temperature_c NUMERIC(6,2),
    firmware TEXT,
    status TEXT,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        signal_quality IS NULL
        OR signal_quality BETWEEN 0 AND 100
    )
);

CREATE INDEX idx_column_signal_quality
    ON column_family_rows(signal_quality)
    WHERE signal_quality IS NOT NULL;

CREATE TABLE graph_nodes (
    node_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_key TEXT NOT NULL UNIQUE,
    labels TEXT[] NOT NULL DEFAULT '{}',
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    CHECK (jsonb_typeof(properties) = 'object')
);

CREATE INDEX idx_graph_node_properties
    ON graph_nodes USING GIN (properties);

CREATE TABLE graph_edges (
    edge_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_node_id BIGINT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    target_node_id BIGINT NOT NULL REFERENCES graph_nodes(node_id) ON DELETE CASCADE,
    relationship TEXT NOT NULL,
    properties JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_node_id <> target_node_id),
    CHECK (length(trim(relationship)) > 0),
    UNIQUE (source_node_id, target_node_id, relationship)
);

CREATE INDEX idx_graph_edges_source
    ON graph_edges(source_node_id);

CREATE INDEX idx_graph_edges_target
    ON graph_edges(target_node_id);

CREATE TABLE review_workflows (
    workflow_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    repository_id BIGINT NOT NULL REFERENCES repositories(repository_id),
    workflow_name TEXT NOT NULL,
    state review_state NOT NULL DEFAULT 'new',
    attempts INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    failure_reason TEXT,
    CHECK (attempts >= 0),
    CHECK (
        state <> 'complete'
        OR completed_at IS NOT NULL
    )
);

CREATE OR REPLACE FUNCTION validate_workflow_state()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.state = 'processing' AND NEW.started_at IS NULL THEN
        NEW.started_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.state = 'complete' AND NEW.completed_at IS NULL THEN
        NEW.completed_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.state = 'failed'
       AND (NEW.failure_reason IS NULL OR length(trim(NEW.failure_reason)) = 0) THEN
        RAISE EXCEPTION 'Failed workflows require failure_reason';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_workflow_state
BEFORE INSERT OR UPDATE ON review_workflows
FOR EACH ROW
EXECUTE FUNCTION validate_workflow_state();

CREATE OR REPLACE FUNCTION update_document_version()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.version := OLD.version + 1;
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_document_version
BEFORE UPDATE ON document_records
FOR EACH ROW
EXECUTE FUNCTION update_document_version();

INSERT INTO repositories (repository_name, description)
VALUES
    ('security-platform', 'Security telemetry and device management'),
    ('research-analytics', 'Research and analytical workloads');

INSERT INTO document_records (
    repository_id,
    document_key,
    payload
)
SELECT
    repository_id,
    'device-gnss-01',
    '{
        "name": "GNSS-01",
        "department": "R&D",
        "active": true,
        "region": "Lucknow",
        "capabilities": ["positioning", "telemetry"],
        "security": {"classification": "internal"}
    }'::jsonb
FROM repositories
WHERE repository_name = 'security-platform';

INSERT INTO document_records (
    repository_id,
    document_key,
    payload,
    state
)
SELECT
    repository_id,
    'device-gnss-02',
    '{
        "name": "GNSS-02",
        "department": "R&D",
        "active": false,
        "region": "Delhi",
        "failure": {"code": "SIGNAL_LOW"}
    }'::jsonb,
    'blocked'
FROM repositories
WHERE repository_name = 'security-platform';

INSERT INTO key_value_records (key, value, expires_at)
VALUES
(
    'session:device-gnss-01',
    '{"authenticated": true, "operator": "r-and-d"}'::jsonb,
    CURRENT_TIMESTAMP + INTERVAL '30 minutes'
),
(
    'counter:telemetry-ingest',
    '{"value": 18425}'::jsonb,
    NULL
),
(
    'cache:expired-example',
    '{"state": "expired"}'::jsonb,
    CURRENT_TIMESTAMP - INTERVAL '5 minutes'
);

INSERT INTO column_family_rows (
    row_key,
    region,
    signal_quality,
    temperature_c,
    firmware,
    status
)
VALUES
(
    'device-gnss-01',
    'Lucknow',
    94,
    31.50,
    '3.2.1',
    'operational'
),
(
    'device-gnss-02',
    'Delhi',
    72,
    NULL,
    NULL,
    'degraded'
),
(
    'device-gnss-03',
    'Lucknow',
    88,
    29.80,
    '3.1.9',
    'operational'
);

INSERT INTO graph_nodes (node_key, labels, properties)
VALUES
    ('team-rnd', ARRAY['Team'], '{"name": "R&D"}'),
    ('repository-security', ARRAY['Repository'], '{"name": "security-platform"}'),
    ('service-telemetry', ARRAY['Service'], '{"name": "telemetry"}'),
    ('database-events', ARRAY['Database'], '{"name": "events"}'),
    ('device-gnss-01', ARRAY['Device'], '{"region": "Lucknow"}'),
    ('device-gnss-02', ARRAY['Device'], '{"region": "Delhi"}');

INSERT INTO graph_edges (
    source_node_id,
    target_node_id,
    relationship
)
SELECT source.node_id, target.node_id, 'OWNS'
FROM graph_nodes source
JOIN graph_nodes target
  ON source.node_key = 'team-rnd'
 AND target.node_key = 'repository-security';

INSERT INTO graph_edges (
    source_node_id,
    target_node_id,
    relationship
)
SELECT source.node_id, target.node_id, 'CONTAINS'
FROM graph_nodes source
JOIN graph_nodes target
  ON source.node_key = 'repository-security'
 AND target.node_key = 'service-telemetry';

INSERT INTO graph_edges (
    source_node_id,
    target_node_id,
    relationship
)
SELECT source.node_id, target.node_id, 'USES'
FROM graph_nodes source
JOIN graph_nodes target
  ON source.node_key = 'service-telemetry'
 AND target.node_key = 'database-events';

INSERT INTO graph_edges (
    source_node_id,
    target_node_id,
    relationship
)
SELECT source.node_id, target.node_id, 'MONITORS'
FROM graph_nodes source
JOIN graph_nodes target
  ON source.node_key = 'service-telemetry'
 AND target.node_key = 'device-gnss-01';

INSERT INTO review_workflows (
    repository_id,
    workflow_name,
    state,
    attempts,
    started_at,
    completed_at
)
SELECT
    repository_id,
    'telemetry-document-validation',
    'complete',
    1,
    CURRENT_TIMESTAMP - INTERVAL '20 minutes',
    CURRENT_TIMESTAMP - INTERVAL '18 minutes'
FROM repositories
WHERE repository_name = 'security-platform';

INSERT INTO review_workflows (
    repository_id,
    workflow_name,
    state,
    attempts,
    failure_reason
)
SELECT
    repository_id,
    'expired-cache-reconciliation',
    'failed',
    3,
    'Cache record expired before reconciliation'
FROM repositories
WHERE repository_name = 'security-platform';

-- Document retrieval: JSONB containment is useful for flexible attributes.
SELECT
    document_key,
    payload ->> 'region' AS region,
    payload ->> 'department' AS department
FROM document_records
WHERE payload @> '{"active": true}'::jsonb;

-- Nested document access.
SELECT
    document_key,
    payload #>> '{security,classification}' AS classification
FROM document_records
WHERE payload ? 'security';

-- Key-value expiration validation.
SELECT
    key,
    value,
    CASE
        WHEN expires_at IS NULL THEN 'persistent'
        WHEN expires_at > CURRENT_TIMESTAMP THEN 'valid'
        ELSE 'expired'
    END AS lifecycle
FROM key_value_records
ORDER BY key;

-- Sparse wide-column reporting.
SELECT
    region,
    COUNT(*) AS devices,
    AVG(signal_quality) AS average_signal,
    COUNT(*) FILTER (
        WHERE status = 'operational'
    ) AS operational_devices
FROM column_family_rows
GROUP BY region
ORDER BY region;

-- Graph relationship retrieval.
SELECT
    source.node_key AS source_node,
    edge.relationship,
    target.node_key AS target_node
FROM graph_edges edge
JOIN graph_nodes source
  ON source.node_id = edge.source_node_id
JOIN graph_nodes target
  ON target.node_id = edge.target_node_id
ORDER BY source.node_key, edge.relationship, target.node_key;

-- Two-hop graph traversal using a recursive CTE.
WITH RECURSIVE traversal AS (
    SELECT
        node.node_id,
        node.node_key,
        0 AS depth,
        ARRAY[node.node_id] AS path
    FROM graph_nodes node
    WHERE node.node_key = 'team-rnd'

    UNION ALL

    SELECT
        target.node_id,
        target.node_key,
        traversal.depth + 1,
        traversal.path || target.node_id
    FROM traversal
    JOIN graph_edges edge
      ON edge.source_node_id = traversal.node_id
    JOIN graph_nodes target
      ON target.node_id = edge.target_node_id
    WHERE traversal.depth < 4
      AND NOT target.node_id = ANY(traversal.path)
)
SELECT
    node_key,
    depth
FROM traversal
ORDER BY depth, node_key;

-- Aggregated model comparison based on actual stored records.
SELECT
    'document'::nosql_model AS model,
    COUNT(*) AS record_count
FROM document_records
UNION ALL
SELECT
    'key_value'::nosql_model,
    COUNT(*)
FROM key_value_records
UNION ALL
SELECT
    'column_family'::nosql_model,
    COUNT(*)
FROM column_family_rows
UNION ALL
SELECT
    'graph'::nosql_model,
    (SELECT COUNT(*) FROM graph_nodes) +
    (SELECT COUNT(*) FROM graph_edges);

-- Transactional state transition:
-- the workflow and its audit state are committed together.
BEGIN;

UPDATE review_workflows
SET
    state = 'processing',
    attempts = attempts + 1
WHERE workflow_name = 'telemetry-document-validation'
  AND state = 'complete';

UPDATE review_workflows
SET
    state = 'complete'
WHERE workflow_name = 'telemetry-document-validation'
  AND state = 'processing';

COMMIT;

-- Eligibility report combining flexible document attributes with
-- structured operational telemetry.
SELECT
    d.document_key,
    d.payload ->> 'region' AS document_region,
    c.signal_quality,
    c.status,
    CASE
        WHEN d.state <> 'active' THEN 'BLOCKED'
        WHEN COALESCE(c.signal_quality, 0) < 80 THEN 'BLOCKED'
        WHEN c.status <> 'operational' THEN 'BLOCKED'
        ELSE 'ELIGIBLE'
    END AS eligibility
FROM document_records d
LEFT JOIN column_family_rows c
  ON c.row_key = d.document_key
ORDER BY d.document_key;
