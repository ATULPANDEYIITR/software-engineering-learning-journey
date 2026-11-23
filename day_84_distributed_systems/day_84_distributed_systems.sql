/*
===============================================================================
DISTRIBUTED SYSTEMS: NODES, NETWORKS AND DISTRIBUTED STATE
PostgreSQL 18+

Relational model covering:
- Distributed clusters
- Nodes and node membership
- Network topology and partitions
- Node heartbeats
- Distributed messages
- Idempotent message processing
- Replicated key-value state
- Logical clocks and record versions
- Distributed operations
- Replication acknowledgements
- Consistency policies
- Quorum-based eligibility
- Node failure detection
- Anti-entropy synchronization
- Operational reporting

Execution:
Run this script using psql against a database where the executing
role has permission to create schemas, tables, functions and triggers.

The database models coordination metadata and a simulated distributed
workflow. PostgreSQL transactions do not themselves provide distributed
consensus across independent database servers.
===============================================================================
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS distributed_systems;

SET search_path TO distributed_systems, public;


-- ============================================================================
-- 1. ENUM TYPES
-- ============================================================================

CREATE TYPE node_status AS ENUM (
    'ACTIVE',
    'SUSPECTED',
    'STOPPED'
);

CREATE TYPE consistency_level AS ENUM (
    'ONE',
    'QUORUM',
    'ALL'
);

CREATE TYPE operation_status AS ENUM (
    'CREATED',
    'REPLICATING',
    'COMMITTED',
    'FAILED'
);

CREATE TYPE message_status AS ENUM (
    'PENDING',
    'DELIVERED',
    'DROPPED',
    'FAILED'
);

CREATE TYPE message_type AS ENUM (
    'REPLICATION',
    'HEARTBEAT',
    'ANTI_ENTROPY'
);


-- ============================================================================
-- 2. CLUSTERS
-- ============================================================================

CREATE TABLE clusters (
    cluster_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_name VARCHAR(120) NOT NULL UNIQUE,

    replication_factor SMALLINT NOT NULL DEFAULT 3,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (replication_factor >= 1)
);


-- ============================================================================
-- 3. DISTRIBUTED NODES
-- ============================================================================

CREATE TABLE nodes (
    node_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    node_name VARCHAR(120) NOT NULL,

    region VARCHAR(80) NOT NULL,

    endpoint VARCHAR(255) NOT NULL,

    status node_status NOT NULL DEFAULT 'ACTIVE',

    logical_clock BIGINT NOT NULL DEFAULT 0,

    last_heartbeat TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (cluster_id, node_name),

    UNIQUE (cluster_id, endpoint),

    CHECK (logical_clock >= 0)
);

CREATE INDEX idx_nodes_cluster_status
ON nodes(cluster_id, status);

CREATE INDEX idx_nodes_heartbeat
ON nodes(last_heartbeat);


-- ============================================================================
-- 4. NETWORK LINKS
-- ============================================================================

CREATE TABLE network_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    source_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    target_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    is_connected BOOLEAN NOT NULL DEFAULT TRUE,

    latency_ms INTEGER NOT NULL DEFAULT 1,

    packet_loss_rate NUMERIC(5,4) NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (source_node_id <> target_node_id),

    CHECK (latency_ms >= 0),

    CHECK (
        packet_loss_rate >= 0
        AND packet_loss_rate <= 1
    ),

    UNIQUE (source_node_id, target_node_id)
);

CREATE INDEX idx_network_links_connectivity
ON network_links(cluster_id, is_connected);


-- ============================================================================
-- 5. DISTRIBUTED OPERATIONS
-- ============================================================================

CREATE TABLE distributed_operations (
    operation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    coordinator_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    operation_key VARCHAR(256) NOT NULL,

    operation_value JSONB NOT NULL,

    consistency consistency_level NOT NULL DEFAULT 'QUORUM',

    status operation_status NOT NULL DEFAULT 'CREATED',

    required_acknowledgements SMALLINT NOT NULL,

    received_acknowledgements SMALLINT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    failure_reason TEXT,

    CHECK (required_acknowledgements >= 1),

    CHECK (received_acknowledgements >= 0),

    CHECK (
        received_acknowledgements <=
        required_acknowledgements
        OR status = 'FAILED'
    )
);

CREATE INDEX idx_operations_cluster_status
ON distributed_operations(cluster_id, status, created_at DESC);

CREATE INDEX idx_operations_key
ON distributed_operations(operation_key);


-- ============================================================================
-- 6. DISTRIBUTED STATE
-- ============================================================================

CREATE TABLE distributed_records (
    record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    operation_id UUID
        REFERENCES distributed_operations(operation_id),

    record_key VARCHAR(256) NOT NULL,

    record_value JSONB NOT NULL,

    logical_time BIGINT NOT NULL,

    origin_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (logical_time >= 0),

    UNIQUE (node_id, record_key)
);

CREATE INDEX idx_records_key
ON distributed_records(cluster_id, record_key);

CREATE INDEX idx_records_version
ON distributed_records(
    cluster_id,
    record_key,
    logical_time DESC,
    origin_node_id DESC
);

CREATE INDEX idx_records_value
ON distributed_records USING GIN(record_value);


-- ============================================================================
-- 7. NETWORK MESSAGES
-- ============================================================================

CREATE TABLE network_messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    sender_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    receiver_node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    operation_id UUID
        REFERENCES distributed_operations(operation_id),

    type message_type NOT NULL,

    payload JSONB NOT NULL DEFAULT '{}'::JSONB,

    status message_status NOT NULL DEFAULT 'PENDING',

    attempt_count SMALLINT NOT NULL DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    delivered_at TIMESTAMPTZ,

    failure_reason TEXT,

    CHECK (sender_node_id <> receiver_node_id),

    CHECK (attempt_count >= 0)
);

CREATE INDEX idx_messages_pending
ON network_messages(cluster_id, created_at)
WHERE status = 'PENDING';

CREATE INDEX idx_messages_receiver
ON network_messages(receiver_node_id, status);


-- ============================================================================
-- 8. MESSAGE DEDUPLICATION
-- ============================================================================

CREATE TABLE processed_messages (
    message_id UUID PRIMARY KEY
        REFERENCES network_messages(message_id),

    node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_processed_node_time
ON processed_messages(node_id, processed_at DESC);


-- ============================================================================
-- 9. REPLICATION ACKNOWLEDGEMENTS
-- ============================================================================

CREATE TABLE replication_acknowledgements (
    acknowledgement_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    operation_id UUID NOT NULL
        REFERENCES distributed_operations(operation_id),

    node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (operation_id, node_id)
);

CREATE INDEX idx_ack_operation
ON replication_acknowledgements(operation_id);


-- ============================================================================
-- 10. NODE HEARTBEATS
-- ============================================================================

CREATE TABLE node_heartbeats (
    heartbeat_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    sequence_number BIGINT NOT NULL,

    UNIQUE (node_id, sequence_number),

    CHECK (sequence_number >= 0)
);

CREATE INDEX idx_heartbeats_recent
ON node_heartbeats(node_id, observed_at DESC);


-- ============================================================================
-- 11. CONSISTENCY POLICIES
-- ============================================================================

CREATE TABLE consistency_policies (
    policy_id BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    policy_name VARCHAR(100) NOT NULL,

    consistency consistency_level NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (cluster_id, policy_name)
);


-- ============================================================================
-- 12. NODE MEMBERSHIP VALIDATION
-- ============================================================================

CREATE OR REPLACE FUNCTION validate_node_cluster()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    actual_cluster BIGINT;
BEGIN
    SELECT cluster_id
    INTO actual_cluster
    FROM nodes
    WHERE node_id = NEW.node_id;

    IF actual_cluster IS DISTINCT FROM NEW.cluster_id THEN
        RAISE EXCEPTION
            'Node % does not belong to cluster %',
            NEW.node_id,
            NEW.cluster_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_network_link
BEFORE INSERT OR UPDATE ON network_links
FOR EACH ROW
EXECUTE FUNCTION validate_node_cluster();


-- ============================================================================
-- 13. LOGICAL CLOCK MANAGEMENT
-- ============================================================================

CREATE OR REPLACE FUNCTION next_logical_clock(
    p_node_id BIGINT,
    p_observed_clock BIGINT DEFAULT 0
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    next_value BIGINT;
BEGIN
    IF p_observed_clock < 0 THEN
        RAISE EXCEPTION 'Observed clock cannot be negative';
    END IF;

    UPDATE nodes
    SET logical_clock =
        GREATEST(logical_clock, p_observed_clock) + 1
    WHERE node_id = p_node_id
      AND status = 'ACTIVE'
    RETURNING logical_clock INTO next_value;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Node % does not exist or is not active',
            p_node_id;
    END IF;

    RETURN next_value;
END;
$$;


-- ============================================================================
-- 14. VERSION COMPARISON AND CONFLICT RESOLUTION
-- ============================================================================

CREATE OR REPLACE FUNCTION compare_versions(
    p_clock_a BIGINT,
    p_origin_a BIGINT,
    p_clock_b BIGINT,
    p_origin_b BIGINT
)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_clock_a > p_clock_b THEN
        RETURN 1;
    ELSIF p_clock_a < p_clock_b THEN
        RETURN -1;
    ELSIF p_origin_a > p_origin_b THEN
        RETURN 1;
    ELSIF p_origin_a < p_origin_b THEN
        RETURN -1;
    END IF;

    RETURN 0;
END;
$$;


-- ============================================================================
-- 15. RECORD REPLICATION
-- ============================================================================

CREATE OR REPLACE FUNCTION apply_replica(
    p_cluster_id BIGINT,
    p_node_id BIGINT,
    p_operation_id UUID,
    p_key VARCHAR(256),
    p_value JSONB,
    p_logical_time BIGINT,
    p_origin_node_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    existing distributed_records%ROWTYPE;
    comparison INTEGER;
BEGIN
    IF p_key IS NULL OR LENGTH(p_key) = 0 THEN
        RAISE EXCEPTION 'Record key cannot be empty';
    END IF;

    IF p_logical_time < 0 THEN
        RAISE EXCEPTION 'Logical time cannot be negative';
    END IF;

    PERFORM 1
    FROM nodes
    WHERE node_id = p_node_id
      AND cluster_id = p_cluster_id
      AND status = 'ACTIVE'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target node is unavailable or invalid';
    END IF;

    SELECT *
    INTO existing
    FROM distributed_records
    WHERE node_id = p_node_id
      AND record_key = p_key
    FOR UPDATE;

    IF FOUND THEN
        comparison := compare_versions(
            p_logical_time,
            p_origin_node_id,
            existing.logical_time,
            existing.origin_node_id
        );

        IF comparison <= 0 THEN
            RETURN FALSE;
        END IF;

        UPDATE distributed_records
        SET
            record_value = p_value,
            logical_time = p_logical_time,
            origin_node_id = p_origin_node_id,
            operation_id = p_operation_id,
            created_at = NOW()
        WHERE record_id = existing.record_id;

    ELSE
        INSERT INTO distributed_records (
            cluster_id,
            node_id,
            operation_id,
            record_key,
            record_value,
            logical_time,
            origin_node_id
        )
        VALUES (
            p_cluster_id,
            p_node_id,
            p_operation_id,
            p_key,
            p_value,
            p_logical_time,
            p_origin_node_id
        );
    END IF;

    UPDATE nodes
    SET logical_clock =
        GREATEST(logical_clock, p_logical_time) + 1
    WHERE node_id = p_node_id;

    RETURN TRUE;
END;
$$;


-- ============================================================================
-- 16. QUORUM ELIGIBILITY
-- ============================================================================

CREATE OR REPLACE FUNCTION quorum_eligibility(
    p_cluster_id BIGINT,
    p_consistency consistency_level,
    p_available_nodes INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    replication_count INTEGER;
    required_count INTEGER;
BEGIN
    SELECT replication_factor
    INTO replication_count
    FROM clusters
    WHERE cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    required_count := CASE p_consistency
        WHEN 'ONE' THEN 1
        WHEN 'QUORUM' THEN replication_count / 2 + 1
        WHEN 'ALL' THEN replication_count
    END;

    RETURN p_available_nodes >= required_count;
END;
$$;


-- ============================================================================
-- 17. DISTRIBUTED WRITE WORKFLOW
-- ============================================================================

CREATE OR REPLACE FUNCTION create_distributed_operation(
    p_cluster_id BIGINT,
    p_coordinator BIGINT,
    p_key VARCHAR(256),
    p_value JSONB,
    p_consistency consistency_level
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    replication_count INTEGER;
    required_count INTEGER;
    logical_time BIGINT;
    new_operation UUID;
BEGIN
    IF p_key IS NULL OR LENGTH(p_key) = 0 THEN
        RAISE EXCEPTION 'Invalid distributed key';
    END IF;

    SELECT replication_factor
    INTO replication_count
    FROM clusters
    WHERE cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    required_count := CASE p_consistency
        WHEN 'ONE' THEN 1
        WHEN 'QUORUM' THEN replication_count / 2 + 1
        WHEN 'ALL' THEN replication_count
    END;

    logical_time := next_logical_clock(p_coordinator);

    INSERT INTO distributed_operations (
        cluster_id,
        coordinator_node_id,
        operation_key,
        operation_value,
        consistency,
        status,
        required_acknowledgements
    )
    VALUES (
        p_cluster_id,
        p_coordinator,
        p_key,
        p_value,
        p_consistency,
        'CREATED',
        required_count
    )
    RETURNING operation_id INTO new_operation;

    -- The coordinator's local copy is committed in this transaction.
    PERFORM apply_replica(
        p_cluster_id,
        p_coordinator,
        new_operation,
        p_key,
        p_value,
        logical_time,
        p_coordinator
    );

    INSERT INTO replication_acknowledgements (
        operation_id,
        node_id
    )
    VALUES (
        new_operation,
        p_coordinator
    );

    UPDATE distributed_operations
    SET
        received_acknowledgements = 1,
        status = 'REPLICATING'
    WHERE operation_id = new_operation;

    RETURN new_operation;
END;
$$;


-- ============================================================================
-- 18. PROCESS REPLICATION ACKNOWLEDGEMENT
-- ============================================================================

CREATE OR REPLACE FUNCTION acknowledge_replication(
    p_operation_id UUID,
    p_node_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    operation distributed_operations%ROWTYPE;
BEGIN
    SELECT *
    INTO operation
    FROM distributed_operations
    WHERE operation_id = p_operation_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown distributed operation';
    END IF;

    IF operation.status NOT IN ('CREATED', 'REPLICATING') THEN
        RAISE EXCEPTION
            'Operation cannot accept acknowledgements in state %',
            operation.status;
    END IF;

    PERFORM 1
    FROM nodes
    WHERE node_id = p_node_id
      AND cluster_id = operation.cluster_id
      AND status = 'ACTIVE';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Acknowledging node is unavailable';
    END IF;

    INSERT INTO replication_acknowledgements (
        operation_id,
        node_id
    )
    VALUES (
        p_operation_id,
        p_node_id
    )
    ON CONFLICT (operation_id, node_id)
    DO NOTHING;

    UPDATE distributed_operations
    SET received_acknowledgements = (
        SELECT COUNT(*)::SMALLINT
        FROM replication_acknowledgements
        WHERE operation_id = p_operation_id
    )
    WHERE operation_id = p_operation_id;

    RETURN TRUE;
END;
$$;


-- ============================================================================
-- 19. FINALIZE DISTRIBUTED OPERATION
-- ============================================================================

CREATE OR REPLACE FUNCTION finalize_distributed_operation(
    p_operation_id UUID
)
RETURNS operation_status
LANGUAGE plpgsql
AS $$
DECLARE
    operation distributed_operations%ROWTYPE;
    final_status operation_status;
BEGIN
    SELECT *
    INTO operation
    FROM distributed_operations
    WHERE operation_id = p_operation_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown operation';
    END IF;

    IF operation.status = 'COMMITTED' THEN
        RETURN 'COMMITTED';
    END IF;

    IF operation.received_acknowledgements >=
       operation.required_acknowledgements THEN

        final_status := 'COMMITTED';

        UPDATE distributed_operations
        SET
            status = 'COMMITTED',
            completed_at = NOW(),
            failure_reason = NULL
        WHERE operation_id = p_operation_id;

    ELSE
        final_status := 'FAILED';

        UPDATE distributed_operations
        SET
            status = 'FAILED',
            failure_reason = 'Insufficient replication acknowledgements'
        WHERE operation_id = p_operation_id;
    END IF;

    RETURN final_status;
END;
$$;


-- ============================================================================
-- 20. MESSAGE DELIVERY AND IDEMPOTENCY
-- ============================================================================

CREATE OR REPLACE FUNCTION process_message(
    p_message_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    message_row network_messages%ROWTYPE;
BEGIN
    SELECT *
    INTO message_row
    FROM network_messages
    WHERE message_id = p_message_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Message does not exist';
    END IF;

    IF message_row.status = 'DELIVERED' THEN
        RETURN FALSE;
    END IF;

    IF message_row.status <> 'PENDING' THEN
        RAISE EXCEPTION
            'Message cannot be processed in state %',
            message_row.status;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM processed_messages
        WHERE message_id = p_message_id
    ) THEN
        RETURN FALSE;
    END IF;

    INSERT INTO processed_messages (
        message_id,
        node_id
    )
    VALUES (
        p_message_id,
        message_row.receiver_node_id
    );

    UPDATE network_messages
    SET
        status = 'DELIVERED',
        delivered_at = NOW(),
        attempt_count = attempt_count + 1
    WHERE message_id = p_message_id;

    RETURN TRUE;
END;
$$;


-- ============================================================================
-- 21. FAILURE DETECTION
-- ============================================================================

CREATE OR REPLACE FUNCTION detect_failed_nodes(
    p_timeout INTERVAL DEFAULT INTERVAL '30 seconds'
)
RETURNS TABLE (
    detected_node_id BIGINT,
    detected_node_name VARCHAR,
    last_seen TIMESTAMPTZ
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_timeout <= INTERVAL '0 seconds' THEN
        RAISE EXCEPTION 'Timeout must be positive';
    END IF;

    UPDATE nodes
    SET status = 'SUSPECTED'
    WHERE status = 'ACTIVE'
      AND (
          last_heartbeat IS NULL
          OR last_heartbeat < NOW() - p_timeout
      );

    RETURN QUERY
    SELECT
        n.node_id,
        n.node_name::VARCHAR,
        n.last_heartbeat
    FROM nodes n
    WHERE n.status = 'SUSPECTED';
END;
$$;


-- ============================================================================
-- 22. ANTI-ENTROPY RECONCILIATION
-- ============================================================================

CREATE OR REPLACE FUNCTION reconcile_cluster(
    p_cluster_id BIGINT
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER := 0;
    current_node RECORD;
    winning_record RECORD;
    was_updated BOOLEAN;
BEGIN
    -- Reconciliation uses the highest logical version for each key.
    -- The origin node ID resolves equal logical-clock conflicts.
    FOR current_node IN
        SELECT node_id
        FROM nodes
        WHERE cluster_id = p_cluster_id
          AND status = 'ACTIVE'
    LOOP

        FOR winning_record IN
            SELECT DISTINCT ON (record_key)
                record_key,
                record_value,
                logical_time,
                origin_node_id,
                operation_id
            FROM distributed_records
            WHERE cluster_id = p_cluster_id
            ORDER BY
                record_key,
                logical_time DESC,
                origin_node_id DESC
        LOOP

            was_updated := apply_replica(
                p_cluster_id,
                current_node.node_id,
                winning_record.operation_id,
                winning_record.record_key,
                winning_record.record_value,
                winning_record.logical_time,
                winning_record.origin_node_id
            );

            IF was_updated THEN
                updated_count := updated_count + 1;
            END IF;

        END LOOP;
    END LOOP;

    RETURN updated_count;
END;
$$;


-- ============================================================================
-- 23. CONSISTENCY AND CONVERGENCE VIEW
-- ============================================================================

CREATE OR REPLACE VIEW record_replication_status AS
SELECT
    c.cluster_id,
    c.cluster_name,
    r.record_key,
    COUNT(DISTINCT r.node_id) AS replica_count,
    MAX(r.logical_time) AS highest_logical_time,
    COUNT(DISTINCT (
        r.record_value,
        r.logical_time,
        r.origin_node_id
    )) AS distinct_versions
FROM clusters c
JOIN distributed_records r
    ON r.cluster_id = c.cluster_id
GROUP BY
    c.cluster_id,
    c.cluster_name,
    r.record_key;


-- ============================================================================
-- 24. OPERATIONAL REPORTING VIEW
-- ============================================================================

CREATE OR REPLACE VIEW cluster_health_report AS
SELECT
    c.cluster_id,
    c.cluster_name,
    c.replication_factor,

    COUNT(n.node_id) AS total_nodes,

    COUNT(n.node_id) FILTER (
        WHERE n.status = 'ACTIVE'
    ) AS active_nodes,

    COUNT(n.node_id) FILTER (
        WHERE n.status = 'STOPPED'
    ) AS stopped_nodes,

    COUNT(n.node_id) FILTER (
        WHERE n.status = 'SUSPECTED'
    ) AS suspected_nodes,

    COUNT(DISTINCT r.record_id) AS stored_records,

    COUNT(DISTINCT o.operation_id) FILTER (
        WHERE o.status = 'COMMITTED'
    ) AS committed_operations,

    COUNT(DISTINCT o.operation_id) FILTER (
        WHERE o.status = 'FAILED'
    ) AS failed_operations

FROM clusters c

LEFT JOIN nodes n
    ON n.cluster_id = c.cluster_id

LEFT JOIN distributed_records r
    ON r.cluster_id = c.cluster_id

LEFT JOIN distributed_operations o
    ON o.cluster_id = c.cluster_id

GROUP BY
    c.cluster_id,
    c.cluster_name,
    c.replication_factor;


-- ============================================================================
-- 25. SAMPLE CLUSTER
-- ============================================================================

INSERT INTO clusters (
    cluster_name,
    replication_factor
)
VALUES (
    'global-commerce-cluster',
    3
);

INSERT INTO nodes (
    cluster_id,
    node_name,
    region,
    endpoint,
    status,
    logical_clock,
    last_heartbeat
)
SELECT
    cluster_id,
    node_name,
    region,
    endpoint,
    'ACTIVE',
    0,
    NOW()
FROM clusters
CROSS JOIN (
    VALUES
        (
            'india-node-1',
            'India',
            'https://india-node-1.internal'
        ),
        (
            'india-node-2',
            'India',
            'https://india-node-2.internal'
        ),
        (
            'europe-node-1',
            'Europe',
            'https://europe-node-1.internal'
        ),
        (
            'us-node-1',
            'United States',
            'https://us-node-1.internal'
        ),
        (
            'us-node-2',
            'United States',
            'https://us-node-2.internal'
        )
) AS sample_nodes(node_name, region, endpoint);


-- ============================================================================
-- 26. SAMPLE NETWORK TOPOLOGY
-- ============================================================================

INSERT INTO network_links (
    cluster_id,
    source_node_id,
    target_node_id,
    is_connected,
    latency_ms,
    packet_loss_rate
)
SELECT
    a.cluster_id,
    a.node_id,
    b.node_id,
    TRUE,
    CASE
        WHEN a.region = b.region THEN 10
        ELSE 120
    END,
    0.001
FROM nodes a
JOIN nodes b
    ON a.cluster_id = b.cluster_id
   AND a.node_id <> b.node_id;


-- ============================================================================
-- 27. SAMPLE CONSISTENCY POLICIES
-- ============================================================================

INSERT INTO consistency_policies (
    cluster_id,
    policy_name,
    consistency,
    enabled
)
SELECT
    cluster_id,
    policy_name,
    consistency,
    TRUE
FROM clusters
CROSS JOIN (
    VALUES
        ('fast-read', 'ONE'::consistency_level),
        ('balanced-read-write', 'QUORUM'::consistency_level),
        ('strict-replication', 'ALL'::consistency_level)
) AS policies(policy_name, consistency);


-- ============================================================================
-- 28. SAMPLE HEARTBEATS
-- ============================================================================

INSERT INTO node_heartbeats (
    node_id,
    sequence_number,
    observed_at
)
SELECT
    node_id,
    1,
    NOW()
FROM nodes;

UPDATE nodes
SET last_heartbeat = NOW();


-- ============================================================================
-- 29. SAMPLE DISTRIBUTED WRITE
-- ============================================================================

DO $$
DECLARE
    cluster_key BIGINT;
    coordinator BIGINT;
    operation UUID;
    node_record RECORD;
    logical_time BIGINT;
BEGIN
    SELECT cluster_id
    INTO cluster_key
    FROM clusters
    WHERE cluster_name = 'global-commerce-cluster';

    SELECT node_id
    INTO coordinator
    FROM nodes
    WHERE cluster_id = cluster_key
      AND node_name = 'india-node-1';

    operation := create_distributed_operation(
        cluster_key,
        coordinator,
        'order:9001',
        '{"order_id":9001,"amount":25000,"status":"PROCESSING"}',
        'QUORUM'
    );

    SELECT logical_time
    INTO logical_time
    FROM distributed_records
    WHERE node_id = coordinator
      AND record_key = 'order:9001';

    -- Replicate to two other nodes.
    FOR node_record IN
        SELECT node_id
        FROM nodes
        WHERE cluster_id = cluster_key
          AND node_id <> coordinator
          AND status = 'ACTIVE'
        ORDER BY node_id
        LIMIT 2
    LOOP

        PERFORM apply_replica(
            cluster_key,
            node_record.node_id,
            operation,
            'order:9001',
            '{"order_id":9001,"amount":25000,"status":"PROCESSING"}',
            logical_time,
            coordinator
        );

        PERFORM acknowledge_replication(
            operation,
            node_record.node_id
        );
    END LOOP;

    PERFORM finalize_distributed_operation(operation);
END;
$$;


-- ============================================================================
-- 30. SAMPLE FAILURE CASE: INSUFFICIENT QUORUM
-- ============================================================================

DO $$
DECLARE
    cluster_key BIGINT;
    coordinator BIGINT;
    operation UUID;
BEGIN
    SELECT cluster_id
    INTO cluster_key
    FROM clusters
    WHERE cluster_name = 'global-commerce-cluster';

    SELECT node_id
    INTO coordinator
    FROM nodes
    WHERE cluster_id = cluster_key
      AND node_name = 'india-node-1';

    operation := create_distributed_operation(
        cluster_key,
        coordinator,
        'order:9002',
        '{"order_id":9002,"status":"PENDING","amount":5000}',
        'QUORUM'
    );

    -- Only the coordinator acknowledges the operation.
    -- The finalization process must reject the operation.
    PERFORM finalize_distributed_operation(operation);
END;
$$;


-- ============================================================================
-- 31. SAMPLE MESSAGE AND IDEMPOTENCY
-- ============================================================================

DO $$
DECLARE
    sender_id BIGINT;
    receiver_id BIGINT;
    cluster_key BIGINT;
    new_message UUID;
BEGIN
    SELECT cluster_id
    INTO cluster_key
    FROM clusters
    WHERE cluster_name = 'global-commerce-cluster';

    SELECT node_id
    INTO sender_id
    FROM nodes
    WHERE node_name = 'india-node-1'
      AND cluster_id = cluster_key;

    SELECT node_id
    INTO receiver_id
    FROM nodes
    WHERE node_name = 'india-node-2'
      AND cluster_id = cluster_key;

    INSERT INTO network_messages (
        cluster_id,
        sender_node_id,
        receiver_node_id,
        type,
        payload
    )
    VALUES (
        cluster_key,
        sender_id,
        receiver_id,
        'HEARTBEAT',
        '{"sequence":1}'
    )
    RETURNING message_id INTO new_message;

    PERFORM process_message(new_message);

    -- Duplicate processing returns FALSE.
    PERFORM process_message(new_message);
END;
$$;


-- ============================================================================
-- 32. SAMPLE PARTITION
-- ============================================================================

UPDATE network_links
SET
    is_connected = FALSE,
    updated_at = NOW()
WHERE source_node_id IN (
    SELECT node_id
    FROM nodes
    WHERE node_name = 'india-node-1'
)
AND target_node_id IN (
    SELECT node_id
    FROM nodes
    WHERE node_name = 'europe-node-1'
);


-- ============================================================================
-- 33. RETRIEVAL QUERIES
-- ============================================================================

-- A. Retrieve all cluster members.
SELECT
    n.node_name,
    n.region,
    n.status,
    n.logical_clock,
    n.last_heartbeat
FROM nodes n
JOIN clusters c
    ON c.cluster_id = n.cluster_id
WHERE c.cluster_name = 'global-commerce-cluster'
ORDER BY n.node_name;


-- B. Retrieve distributed versions of an order.
SELECT
    n.node_name,
    r.record_key,
    r.record_value,
    r.logical_time,
    r.origin_node_id
FROM distributed_records r
JOIN nodes n
    ON n.node_id = r.node_id
WHERE r.record_key = 'order:9001'
ORDER BY r.logical_time DESC, r.origin_node_id DESC;


-- C. Retrieve pending network messages.
SELECT
    message_id,
    sender_node_id,
    receiver_node_id,
    type,
    attempt_count,
    created_at
FROM network_messages
WHERE status = 'PENDING'
ORDER BY created_at;


-- ============================================================================
-- 34. VALIDATION QUERIES
-- ============================================================================

-- Check which records have different versions across replicas.
SELECT
    cluster_name,
    record_key,
    replica_count,
    highest_logical_time,
    distinct_versions,
    CASE
        WHEN distinct_versions = 1 THEN 'CONVERGED'
        ELSE 'DIVERGENT'
    END AS consistency_state
FROM record_replication_status;


-- Check consistency policy eligibility.
SELECT
    consistency,
    quorum_eligibility(
        (
            SELECT cluster_id
            FROM clusters
            WHERE cluster_name = 'global-commerce-cluster'
        ),
        consistency,
        2
    ) AS eligible_with_two_nodes
FROM (
    VALUES
        ('ONE'::consistency_level),
        ('QUORUM'::consistency_level),
        ('ALL'::consistency_level)
) AS levels(consistency);


-- ============================================================================
-- 35. AGGREGATION AND REPORTING
-- ============================================================================

SELECT *
FROM cluster_health_report;


SELECT
    status,
    COUNT(*) AS operation_count,
    AVG(received_acknowledgements::NUMERIC)
        AS average_acknowledgements
FROM distributed_operations
GROUP BY status
ORDER BY status;


SELECT
    n.region,
    COUNT(DISTINCT n.node_id) AS node_count,
    COUNT(DISTINCT r.record_id) AS replicated_records,
    MAX(n.logical_clock) AS maximum_logical_clock
FROM nodes n
LEFT JOIN distributed_records r
    ON r.node_id = n.node_id
GROUP BY n.region
ORDER BY n.region;


-- ============================================================================
-- 36. FAILURE DETECTION QUERY
-- ============================================================================

-- Sample stale heartbeat detection is exposed through this function.
-- The interval is intentionally short for demonstration.
SELECT *
FROM detect_failed_nodes(INTERVAL '30 seconds');


-- ============================================================================
-- 37. ANTI-ENTROPY RECOVERY
-- ============================================================================

SELECT reconcile_cluster(
    (
        SELECT cluster_id
        FROM clusters
        WHERE cluster_name = 'global-commerce-cluster'
    )
) AS repaired_replica_count;


-- ============================================================================
-- 38. TRANSACTIONAL VALIDATION
-- ============================================================================

-- The following example demonstrates atomic acknowledgement processing.
-- A rollback leaves the persistent state unchanged.

SAVEPOINT before_test_acknowledgement;

DO $$
DECLARE
    operation_key UUID;
    receiver BIGINT;
BEGIN
    SELECT operation_id
    INTO operation_key
    FROM distributed_operations
    WHERE operation_key = 'order:9001'
    ORDER BY created_at DESC
    LIMIT 1;

    SELECT node_id
    INTO receiver
    FROM nodes
    WHERE node_name = 'us-node-1';

    IF operation_key IS NOT NULL THEN
        BEGIN
            PERFORM acknowledge_replication(
                operation_key,
                receiver
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE
                'Acknowledgement rejected: %',
                SQLERRM;
        END;
    END IF;
END;
$$;

ROLLBACK TO SAVEPOINT before_test_acknowledgement;


-- ============================================================================
-- 39. FINAL SYSTEM REPORT
-- ============================================================================

SELECT
    c.cluster_name,
    c.replication_factor,
    h.total_nodes,
    h.active_nodes,
    h.stopped_nodes,
    h.suspected_nodes,
    h.stored_records,
    h.committed_operations,
    h.failed_operations
FROM clusters c
JOIN cluster_health_report h
    ON h.cluster_id = c.cluster_id;


COMMIT;


/*
===============================================================================
IMPORTANT DATABASE DESIGN LIMITATIONS

1. The relational schema records distributed-system metadata and simulated
   replication operations. It does not establish consensus across independent
   PostgreSQL servers.

2. Logical clocks provide deterministic ordering metadata. They do not prove
   that two events are causally related.

3. Last-Write-Wins conflict resolution can discard concurrent business updates.
   Financial and inventory systems may require transactional conflict handling.

4. A database transaction can atomically update local metadata and records.
   It cannot guarantee that a remote node received a message.

5. Real production replication requires durable delivery, retry management,
   authenticated node identity, network timeouts, message retention and
   independently validated failure recovery.

6. The sample anti-entropy function assumes a fully connected recovery path.
   A production implementation must account for network partitions during
   reconciliation and concurrent updates.

7. Failure detection is based on heartbeat timeouts. A suspected node is not
   necessarily stopped; network congestion can produce false suspicions.

8. Database privileges should restrict direct modification of logical clocks,
   replication records, acknowledgements and processed-message metadata.
===============================================================================
*/
