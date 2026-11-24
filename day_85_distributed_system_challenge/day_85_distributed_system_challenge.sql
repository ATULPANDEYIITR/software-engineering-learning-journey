-- ============================================================
-- DISTRIBUTED SYSTEM CHALLENGES
-- PostgreSQL 16+
--
-- Models:
--   Distributed clusters
--   Nodes and network topology
--   Versioned replicated records
--   Network messages and latency
--   Failure detection
--   Network partitions
--   Write operations and idempotency
--   Replica acknowledgements
--   Read operations and consistency
--   Read repair and synchronization
--   Consistency policies
--   Quorum calculations
--   Operational monitoring
--
-- Run as a database owner in a dedicated learning database.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS distributed_systems;

SET search_path TO distributed_systems, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE node_status AS ENUM (
    'healthy',
    'unavailable',
    'partitioned',
    'recovering'
);

CREATE TYPE consistency_level AS ENUM (
    'one',
    'quorum',
    'all'
);

CREATE TYPE operation_type AS ENUM (
    'read',
    'write',
    'repair',
    'synchronization'
);

CREATE TYPE operation_status AS ENUM (
    'pending',
    'committed',
    'failed',
    'timed_out'
);

CREATE TYPE message_status AS ENUM (
    'pending',
    'delivered',
    'dropped',
    'timed_out'
);

CREATE TYPE failure_type AS ENUM (
    'node_failure',
    'network_partition',
    'packet_loss',
    'high_latency',
    'timeout',
    'disk_failure'
);

-- ============================================================
-- 2. CLUSTERS
-- ============================================================

CREATE TABLE clusters (
    cluster_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_name VARCHAR(100) NOT NULL UNIQUE,

    node_count INTEGER NOT NULL CHECK (node_count > 0),

    replication_factor INTEGER NOT NULL,

    base_latency_ms NUMERIC(12, 3) NOT NULL DEFAULT 10
        CHECK (base_latency_ms >= 0),

    timeout_ms NUMERIC(12, 3) NOT NULL DEFAULT 100
        CHECK (timeout_ms > 0),

    packet_loss_rate NUMERIC(5, 4) NOT NULL DEFAULT 0
        CHECK (packet_loss_rate BETWEEN 0 AND 1),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (
        replication_factor BETWEEN 1 AND node_count
    )
);

-- ============================================================
-- 3. DISTRIBUTED NODES
-- ============================================================

CREATE TABLE nodes (
    node_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    node_name VARCHAR(100) NOT NULL,

    region VARCHAR(80) NOT NULL,

    status node_status NOT NULL DEFAULT 'healthy',

    last_heartbeat TIMESTAMPTZ,

    cpu_utilization NUMERIC(5, 2)
        CHECK (
            cpu_utilization BETWEEN 0 AND 100
        ),

    memory_utilization NUMERIC(5, 2)
        CHECK (
            memory_utilization BETWEEN 0 AND 100
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (cluster_id, node_name),

    UNIQUE (cluster_id, node_id)
);

CREATE INDEX idx_nodes_cluster_status
    ON nodes(cluster_id, status);

CREATE INDEX idx_nodes_heartbeat
    ON nodes(last_heartbeat);

-- ============================================================
-- 4. NETWORK LINKS AND PARTITIONS
-- ============================================================

CREATE TABLE network_links (
    link_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    source_node_id BIGINT NOT NULL,

    destination_node_id BIGINT NOT NULL,

    latency_ms NUMERIC(12, 3) NOT NULL
        CHECK (latency_ms >= 0),

    packet_loss_rate NUMERIC(5, 4) NOT NULL DEFAULT 0
        CHECK (packet_loss_rate BETWEEN 0 AND 1),

    is_partitioned BOOLEAN NOT NULL DEFAULT FALSE,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (cluster_id, source_node_id)
        REFERENCES nodes(cluster_id, node_id),

    FOREIGN KEY (cluster_id, destination_node_id)
        REFERENCES nodes(cluster_id, node_id),

    CHECK (source_node_id <> destination_node_id),

    UNIQUE (source_node_id, destination_node_id)
);

CREATE INDEX idx_network_links_partition
    ON network_links(cluster_id, is_partitioned);

-- ============================================================
-- 5. REPLICATED DATA RECORDS
-- ============================================================

CREATE TABLE distributed_records (
    record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    record_key VARCHAR(256) NOT NULL,

    record_value TEXT NOT NULL,

    logical_version BIGINT NOT NULL
        CHECK (logical_version > 0),

    operation_id UUID NOT NULL,

    record_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (cluster_id, record_key, logical_version),

    UNIQUE (cluster_id, operation_id),

    UNIQUE (cluster_id, record_id)
);

CREATE INDEX idx_records_key_version
    ON distributed_records(
        cluster_id,
        record_key,
        logical_version DESC
    );

-- ============================================================
-- 6. REPLICA STORAGE
-- ============================================================

CREATE TABLE replicas (
    replica_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL,

    node_id BIGINT NOT NULL,

    record_id BIGINT NOT NULL,

    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    is_synchronized BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (cluster_id, node_id)
        REFERENCES nodes(cluster_id, node_id),

    FOREIGN KEY (cluster_id, record_id)
        REFERENCES distributed_records(cluster_id, record_id),

    UNIQUE (node_id, record_id)
);

CREATE INDEX idx_replicas_node
    ON replicas(node_id, applied_at DESC);

CREATE INDEX idx_replicas_record
    ON replicas(record_id);

-- ============================================================
-- 7. DISTRIBUTED OPERATIONS
-- ============================================================

CREATE TABLE operations (
    operation_id UUID PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    operation_type operation_type NOT NULL,

    consistency consistency_level NOT NULL,

    operation_status operation_status NOT NULL DEFAULT 'pending',

    record_key VARCHAR(256) NOT NULL,

    requested_value TEXT,

    required_acknowledgements INTEGER NOT NULL
        CHECK (required_acknowledgements > 0),

    received_acknowledgements INTEGER NOT NULL DEFAULT 0
        CHECK (received_acknowledgements >= 0),

    latency_ms NUMERIC(14, 3)
        CHECK (latency_ms IS NULL OR latency_ms >= 0),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    error_message TEXT,

    CHECK (
        received_acknowledgements <=
        required_acknowledgements
        OR operation_status = 'committed'
    ),

    CHECK (
        completed_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE INDEX idx_operations_cluster_status
    ON operations(
        cluster_id,
        operation_status,
        started_at DESC
    );

CREATE INDEX idx_operations_key
    ON operations(cluster_id, record_key);

-- ============================================================
-- 8. OPERATION ACKNOWLEDGEMENTS
-- ============================================================

CREATE TABLE acknowledgements (
    acknowledgement_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    operation_id UUID NOT NULL
        REFERENCES operations(operation_id),

    node_id BIGINT NOT NULL
        REFERENCES nodes(node_id),

    acknowledged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    latency_ms NUMERIC(12, 3) NOT NULL
        CHECK (latency_ms >= 0),

    success BOOLEAN NOT NULL,

    error_message TEXT,

    UNIQUE (operation_id, node_id)
);

CREATE INDEX idx_acknowledgements_operation
    ON acknowledgements(operation_id, success);

-- ============================================================
-- 9. NETWORK MESSAGES
-- ============================================================

CREATE TABLE network_messages (
    message_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    operation_id UUID
        REFERENCES operations(operation_id),

    source_node_id BIGINT
        REFERENCES nodes(node_id),

    destination_node_id BIGINT
        REFERENCES nodes(node_id),

    message_status message_status NOT NULL DEFAULT 'pending',

    latency_ms NUMERIC(12, 3)
        CHECK (latency_ms IS NULL OR latency_ms >= 0),

    payload_size_bytes INTEGER NOT NULL DEFAULT 0
        CHECK (payload_size_bytes >= 0),

    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    received_at TIMESTAMPTZ,

    error_message TEXT
);

CREATE INDEX idx_messages_status_time
    ON network_messages(message_status, sent_at DESC);

CREATE INDEX idx_messages_operation
    ON network_messages(operation_id);

-- ============================================================
-- 10. FAILURE EVENTS
-- ============================================================

CREATE TABLE failure_events (
    failure_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    node_id BIGINT
        REFERENCES nodes(node_id),

    failure_category failure_type NOT NULL,

    severity SMALLINT NOT NULL
        CHECK (severity BETWEEN 1 AND 5),

    description TEXT NOT NULL,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    recovered_at TIMESTAMPTZ,

    CHECK (
        recovered_at IS NULL
        OR recovered_at >= occurred_at
    )
);

CREATE INDEX idx_failures_cluster_time
    ON failure_events(cluster_id, occurred_at DESC);

-- ============================================================
-- 11. CONSISTENCY CHECKS
-- ============================================================

CREATE TABLE consistency_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES clusters(cluster_id),

    record_key VARCHAR(256) NOT NULL,

    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    replicas_examined INTEGER NOT NULL
        CHECK (replicas_examined >= 0),

    distinct_versions INTEGER NOT NULL
        CHECK (distinct_versions >= 0),

    latest_version BIGINT,

    is_consistent BOOLEAN NOT NULL,

    repair_required BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX idx_consistency_checks_key
    ON consistency_checks(cluster_id, record_key, checked_at DESC);

-- ============================================================
-- 12. HELPER FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION required_acknowledgements(
    p_replication_factor INTEGER,
    p_consistency consistency_level
)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
AS $$
BEGIN
    IF p_replication_factor < 1 THEN
        RAISE EXCEPTION 'Replication factor must be positive';
    END IF;

    CASE p_consistency
        WHEN 'one' THEN
            RETURN 1;

        WHEN 'quorum' THEN
            RETURN (p_replication_factor / 2) + 1;

        WHEN 'all' THEN
            RETURN p_replication_factor;

        ELSE
            RAISE EXCEPTION 'Unsupported consistency level';
    END CASE;
END;
$$;

CREATE OR REPLACE FUNCTION calculate_quorum(
    p_replication_factor INTEGER
)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT (p_replication_factor / 2) + 1;
$$;

-- ============================================================
-- 13. CLUSTER CONFIGURATION VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_cluster_capacity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.replication_factor > NEW.node_count THEN
        RAISE EXCEPTION
            'Replication factor cannot exceed node count';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_cluster_capacity
BEFORE INSERT OR UPDATE ON clusters
FOR EACH ROW
EXECUTE FUNCTION validate_cluster_capacity();

-- ============================================================
-- 14. OPERATION IDEMPOTENCY
-- ============================================================

CREATE OR REPLACE FUNCTION prevent_duplicate_operation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM operations
        WHERE operation_id = NEW.operation_id
    ) THEN
        RAISE EXCEPTION
            'Duplicate operation identifier: %',
            NEW.operation_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_operation_idempotency
BEFORE INSERT ON operations
FOR EACH ROW
EXECUTE FUNCTION prevent_duplicate_operation();

-- The primary key on operation_id is the final concurrency-safe
-- idempotency constraint. The trigger provides an explicit error.

-- ============================================================
-- 15. OPERATION STATE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_operation_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.operation_status <> 'pending'
       AND NEW.operation_status <> OLD.operation_status THEN
        RAISE EXCEPTION
            'Terminal operation status cannot be changed';
    END IF;

    IF NEW.operation_status IN (
        'committed',
        'failed',
        'timed_out'
    ) AND NEW.completed_at IS NULL THEN
        NEW.completed_at := NOW();
    END IF;

    IF NEW.operation_status = 'committed'
       AND NEW.received_acknowledgements <
           NEW.required_acknowledgements THEN
        RAISE EXCEPTION
            'Cannot commit without required acknowledgements';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_operation_transition
BEFORE UPDATE ON operations
FOR EACH ROW
EXECUTE FUNCTION validate_operation_transition();

-- ============================================================
-- 16. OPERATIONAL VIEWS
-- ============================================================

CREATE OR REPLACE VIEW cluster_health AS
SELECT
    c.cluster_id,
    c.cluster_name,
    c.node_count,
    COUNT(n.node_id) AS registered_nodes,
    COUNT(n.node_id) FILTER (
        WHERE n.status = 'healthy'
    ) AS healthy_nodes,
    COUNT(n.node_id) FILTER (
        WHERE n.status = 'unavailable'
    ) AS unavailable_nodes,
    COUNT(n.node_id) FILTER (
        WHERE n.status = 'partitioned'
    ) AS partitioned_nodes,
    c.replication_factor,
    calculate_quorum(c.replication_factor) AS quorum_size
FROM clusters c
LEFT JOIN nodes n
    ON n.cluster_id = c.cluster_id
GROUP BY
    c.cluster_id,
    c.cluster_name,
    c.node_count,
    c.replication_factor;

CREATE OR REPLACE VIEW operation_performance AS
SELECT
    cluster_id,
    operation_type,
    COUNT(*) AS total_operations,
    COUNT(*) FILTER (
        WHERE operation_status = 'committed'
    ) AS successful_operations,
    COUNT(*) FILTER (
        WHERE operation_status = 'failed'
    ) AS failed_operations,
    COUNT(*) FILTER (
        WHERE operation_status = 'timed_out'
    ) AS timed_out_operations,
    ROUND(AVG(latency_ms), 3) AS average_latency_ms,
    ROUND(
        PERCENTILE_CONT(0.95)
        WITHIN GROUP (ORDER BY latency_ms)::NUMERIC,
        3
    ) AS p95_latency_ms
FROM operations
GROUP BY cluster_id, operation_type;

CREATE OR REPLACE VIEW replica_distribution AS
SELECT
    n.node_name,
    n.status,
    COUNT(r.replica_id) AS replica_count,
    COUNT(r.replica_id) FILTER (
        WHERE r.is_synchronized
    ) AS synchronized_replicas,
    COUNT(r.replica_id) FILTER (
        WHERE NOT r.is_synchronized
    ) AS unsynchronized_replicas
FROM nodes n
LEFT JOIN replicas r
    ON r.node_id = n.node_id
GROUP BY n.node_id, n.node_name, n.status;

-- ============================================================
-- 17. WRITE ELIGIBILITY
-- ============================================================

CREATE OR REPLACE FUNCTION check_write_eligibility(
    p_cluster_id BIGINT,
    p_consistency consistency_level
)
RETURNS TABLE (
    eligible BOOLEAN,
    required_nodes INTEGER,
    available_nodes BIGINT,
    explanation TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_replication INTEGER;
    v_required INTEGER;
    v_available BIGINT;
BEGIN
    SELECT
        c.replication_factor,
        COUNT(n.node_id) FILTER (
            WHERE n.status = 'healthy'
        )
    INTO
        v_replication,
        v_available
    FROM clusters c
    LEFT JOIN nodes n
        ON n.cluster_id = c.cluster_id
    WHERE c.cluster_id = p_cluster_id
    GROUP BY c.replication_factor;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cluster not found';
    END IF;

    v_required := required_acknowledgements(
        v_replication,
        p_consistency
    );

    RETURN QUERY
    SELECT
        v_available >= v_required,
        v_required,
        v_available,
        CASE
            WHEN v_available >= v_required
                THEN 'Required acknowledgement capacity available'
            ELSE 'Insufficient healthy replicas'
        END;
END;
$$;

-- ============================================================
-- 18. RECORD CONSISTENCY AUDIT
-- ============================================================

CREATE OR REPLACE FUNCTION audit_record_consistency(
    p_cluster_id BIGINT,
    p_record_key VARCHAR
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_replicas INTEGER;
    v_versions INTEGER;
    v_latest BIGINT;
    v_check_id BIGINT;
BEGIN
    SELECT
        COUNT(DISTINCT r.node_id),
        COUNT(DISTINCT d.logical_version),
        MAX(d.logical_version)
    INTO
        v_replicas,
        v_versions,
        v_latest
    FROM replicas r
    JOIN distributed_records d
        ON d.record_id = r.record_id
    JOIN nodes n
        ON n.node_id = r.node_id
    WHERE r.cluster_id = p_cluster_id
      AND d.record_key = p_record_key
      AND n.status = 'healthy';

    INSERT INTO consistency_checks (
        cluster_id,
        record_key,
        replicas_examined,
        distinct_versions,
        latest_version,
        is_consistent,
        repair_required
    )
    VALUES (
        p_cluster_id,
        p_record_key,
        v_replicas,
        v_versions,
        v_latest,
        v_versions <= 1,
        v_versions > 1
    )
    RETURNING check_id INTO v_check_id;

    RETURN v_check_id;
END;
$$;

-- ============================================================
-- 19. REPLICA REPAIR
-- ============================================================

CREATE OR REPLACE FUNCTION repair_record_replicas(
    p_cluster_id BIGINT,
    p_record_key VARCHAR
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_latest_record BIGINT;
    v_repaired INTEGER;
BEGIN
    SELECT d.record_id
    INTO v_latest_record
    FROM distributed_records d
    WHERE d.cluster_id = p_cluster_id
      AND d.record_key = p_record_key
    ORDER BY
        d.logical_version DESC,
        d.record_timestamp DESC,
        d.operation_id DESC
    LIMIT 1;

    IF v_latest_record IS NULL THEN
        RETURN 0;
    END IF;

    WITH latest AS (
        SELECT record_id
        FROM distributed_records
        WHERE record_id = v_latest_record
    ),
    inserted AS (
        INSERT INTO replicas (
            cluster_id,
            node_id,
            record_id,
            is_synchronized
        )
        SELECT
            p_cluster_id,
            n.node_id,
            latest.record_id,
            TRUE
        FROM nodes n
        CROSS JOIN latest
        WHERE n.cluster_id = p_cluster_id
          AND n.status = 'healthy'
        ON CONFLICT (node_id, record_id)
        DO UPDATE SET
            is_synchronized = TRUE,
            applied_at = NOW()
        RETURNING replica_id
    )
    SELECT COUNT(*)::INTEGER
    INTO v_repaired
    FROM inserted;

    RETURN v_repaired;
END;
$$;

-- ============================================================
-- 20. OPERATION PROCESSING PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE process_write_operation(
    p_operation_id UUID,
    p_cluster_id BIGINT,
    p_record_key VARCHAR,
    p_record_value TEXT,
    p_consistency consistency_level
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_replication INTEGER;
    v_required INTEGER;
    v_healthy INTEGER;
    v_version BIGINT;
    v_record_id BIGINT;
    v_acknowledgements INTEGER;
    v_node RECORD;
    v_inserted_operation UUID;
BEGIN
    -- Serialize operations for this cluster and key.
    PERFORM pg_advisory_xact_lock(
        p_cluster_id,
        hashtext(p_record_key)
    );

    SELECT replication_factor
    INTO v_replication
    FROM clusters
    WHERE cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    v_required := required_acknowledgements(
        v_replication,
        p_consistency
    );

    INSERT INTO operations (
        operation_id,
        cluster_id,
        operation_type,
        consistency,
        operation_status,
        record_key,
        requested_value,
        required_acknowledgements
    )
    VALUES (
        p_operation_id,
        p_cluster_id,
        'write',
        p_consistency,
        'pending',
        p_record_key,
        p_record_value,
        v_required
    )
    ON CONFLICT (operation_id) DO NOTHING
    RETURNING operation_id INTO v_inserted_operation;

    IF v_inserted_operation IS NULL THEN
        RAISE EXCEPTION
            'Operation already exists; inspect its previous result';
    END IF;

    SELECT COUNT(*)
    INTO v_healthy
    FROM nodes
    WHERE cluster_id = p_cluster_id
      AND status = 'healthy';

    IF v_healthy < v_required THEN
        UPDATE operations
        SET
            operation_status = 'failed',
            error_message = 'Insufficient healthy nodes'
        WHERE operation_id = p_operation_id;

        RETURN;
    END IF;

    SELECT COALESCE(MAX(logical_version), 0) + 1
    INTO v_version
    FROM distributed_records
    WHERE cluster_id = p_cluster_id
      AND record_key = p_record_key;

    INSERT INTO distributed_records (
        cluster_id,
        record_key,
        record_value,
        logical_version,
        operation_id
    )
    VALUES (
        p_cluster_id,
        p_record_key,
        p_record_value,
        v_version,
        p_operation_id
    )
    RETURNING record_id INTO v_record_id;

    v_acknowledgements := 0;

    -- This procedure models successful local replication acknowledgements.
    -- A production implementation must obtain real remote acknowledgements
    -- from the distributed transport layer, not from database row inserts.
    FOR v_node IN
        SELECT node_id
        FROM nodes
        WHERE cluster_id = p_cluster_id
          AND status = 'healthy'
        ORDER BY node_id
        LIMIT v_replication
    LOOP
        INSERT INTO replicas (
            cluster_id,
            node_id,
            record_id,
            is_synchronized
        )
        VALUES (
            p_cluster_id,
            v_node.node_id,
            v_record_id,
            TRUE
        );

        INSERT INTO acknowledgements (
            operation_id,
            node_id,
            latency_ms,
            success
        )
        VALUES (
            p_operation_id,
            v_node.node_id,
            10,
            TRUE
        );

        v_acknowledgements :=
            v_acknowledgements + 1;
    END LOOP;

    UPDATE operations
    SET
        received_acknowledgements = v_acknowledgements,
        operation_status = CASE
            WHEN v_acknowledgements >= v_required
                THEN 'committed'::operation_status
            ELSE 'failed'::operation_status
        END,
        completed_at = NOW(),
        latency_ms = 10
    WHERE operation_id = p_operation_id;

END;
$$;

-- ============================================================
-- 21. SAMPLE CLUSTER
-- ============================================================

INSERT INTO clusters (
    cluster_name,
    node_count,
    replication_factor,
    base_latency_ms,
    timeout_ms,
    packet_loss_rate
)
VALUES (
    'commerce-cluster',
    5,
    3,
    12,
    100,
    0.01
);

INSERT INTO nodes (
    cluster_id,
    node_name,
    region,
    status,
    last_heartbeat,
    cpu_utilization,
    memory_utilization
)
SELECT
    c.cluster_id,
    sample.node_name,
    sample.region,
    sample.status,
    NOW(),
    sample.cpu,
    sample.memory
FROM clusters c
CROSS JOIN (
    VALUES
        ('node-1', 'mumbai', 'healthy'::node_status, 45.0, 62.0),
        ('node-2', 'delhi', 'healthy'::node_status, 38.0, 55.0),
        ('node-3', 'bengaluru', 'healthy'::node_status, 52.0, 68.0),
        ('node-4', 'hyderabad', 'unavailable'::node_status, 0.0, 0.0),
        ('node-5', 'pune', 'healthy'::node_status, 30.0, 47.0)
) AS sample(
    node_name,
    region,
    status,
    cpu,
    memory
)
WHERE c.cluster_name = 'commerce-cluster';

-- ============================================================
-- 22. SAMPLE NETWORK TOPOLOGY
-- ============================================================

INSERT INTO network_links (
    cluster_id,
    source_node_id,
    destination_node_id,
    latency_ms,
    packet_loss_rate,
    is_partitioned
)
SELECT
    a.cluster_id,
    a.node_id,
    b.node_id,
    CASE
        WHEN a.region = b.region THEN 2
        ELSE 18
    END,
    0.01,
    FALSE
FROM nodes a
JOIN nodes b
    ON a.cluster_id = b.cluster_id
   AND a.node_id <> b.node_id
WHERE a.cluster_id = (
    SELECT cluster_id
    FROM clusters
    WHERE cluster_name = 'commerce-cluster'
);

-- ============================================================
-- 23. SAMPLE DISTRIBUTED RECORDS
-- ============================================================

INSERT INTO distributed_records (
    cluster_id,
    record_key,
    record_value,
    logical_version,
    operation_id,
    record_timestamp
)
SELECT
    c.cluster_id,
    sample.record_key,
    sample.record_value,
    sample.version,
    sample.operation_id::UUID,
    NOW() - sample.age
FROM clusters c
CROSS JOIN (
    VALUES
        (
            'account:1001',
            'balance:10000',
            1,
            '10000000-0000-0000-0000-000000000001',
            INTERVAL '5 minutes'
        ),
        (
            'account:1001',
            'balance:9500',
            2,
            '10000000-0000-0000-0000-000000000002',
            INTERVAL '1 minute'
        ),
        (
            'inventory:2001',
            'quantity:250',
            1,
            '10000000-0000-0000-0000-000000000003',
            INTERVAL '2 minutes'
        ),
        (
            'order:3001',
            'payment_confirmed',
            1,
            '10000000-0000-0000-0000-000000000004',
            INTERVAL '30 seconds'
        )
) AS sample(
    record_key,
    record_value,
    version,
    operation_id,
    age
)
WHERE c.cluster_name = 'commerce-cluster';

-- ============================================================
-- 24. SAMPLE REPLICAS
-- ============================================================

INSERT INTO replicas (
    cluster_id,
    node_id,
    record_id,
    is_synchronized
)
SELECT
    d.cluster_id,
    n.node_id,
    d.record_id,
    CASE
        WHEN d.record_key = 'account:1001'
         AND d.logical_version = 1
         AND n.node_name = 'node-3'
        THEN FALSE
        ELSE TRUE
    END
FROM distributed_records d
JOIN nodes n
    ON n.cluster_id = d.cluster_id
WHERE n.node_name IN ('node-1', 'node-2', 'node-3')
  AND (
      d.record_key <> 'account:1001'
      OR (
          d.record_key = 'account:1001'
          AND (
              d.logical_version = 2
              OR (
                  d.logical_version = 1
                  AND n.node_name = 'node-3'
              )
          )
      )
  );

-- ============================================================
-- 25. SAMPLE OPERATIONS
-- ============================================================

INSERT INTO operations (
    operation_id,
    cluster_id,
    operation_type,
    consistency,
    operation_status,
    record_key,
    requested_value,
    required_acknowledgements,
    received_acknowledgements,
    latency_ms,
    completed_at,
    error_message
)
SELECT
    sample.operation_id::UUID,
    c.cluster_id,
    sample.operation_type,
    sample.consistency,
    sample.status,
    sample.record_key,
    sample.requested_value,
    sample.required_acks,
    sample.received_acks,
    sample.latency,
    NOW(),
    sample.error
FROM clusters c
CROSS JOIN (
    VALUES
        (
            '20000000-0000-0000-0000-000000000001',
            'write'::operation_type,
            'quorum'::consistency_level,
            'committed'::operation_status,
            'account:1001',
            'balance:9500',
            2,
            2,
            22.5::NUMERIC,
            NULL::TEXT
        ),
        (
            '20000000-0000-0000-0000-000000000002',
            'write'::operation_type,
            'all'::consistency_level,
            'failed'::operation_status,
            'account:1002',
            'balance:5000',
            3,
            2,
            105.0::NUMERIC,
            'Node unavailable'
        ),
        (
            '20000000-0000-0000-0000-000000000003',
            'read'::operation_type,
            'one'::consistency_level,
            'committed'::operation_status,
            'account:1001',
            NULL,
            1,
            1,
            8.5::NUMERIC,
            NULL::TEXT
        ),
        (
            '20000000-0000-0000-0000-000000000004',
            'write'::operation_type,
            'quorum'::consistency_level,
            'timed_out'::operation_status,
            'order:3002',
            'processing',
            2,
            0,
            120.0::NUMERIC,
            'Network partition'
        )
) AS sample(
    operation_id,
    operation_type,
    consistency,
    status,
    record_key,
    requested_value,
    required_acks,
    received_acks,
    latency,
    error
)
WHERE c.cluster_name = 'commerce-cluster';

-- ============================================================
-- 26. SAMPLE FAILURE EVENTS
-- ============================================================

INSERT INTO failure_events (
    cluster_id,
    node_id,
    failure_category,
    severity,
    description,
    occurred_at
)
SELECT
    c.cluster_id,
    n.node_id,
    sample.failure_category,
    sample.severity,
    sample.description,
    NOW() - sample.age
FROM clusters c
CROSS JOIN (
    VALUES
        (
            'node-4',
            'node_failure'::failure_type,
            4,
            'Replica became unavailable',
            INTERVAL '20 minutes'
        ),
        (
            'node-2',
            'network_partition'::failure_type,
            5,
            'Coordinator could not reach replica',
            INTERVAL '10 minutes'
        ),
        (
            'node-3',
            'high_latency'::failure_type,
            2,
            'Cross-region latency increased',
            INTERVAL '5 minutes'
        )
) AS sample(
    node_name,
    failure_category,
    severity,
    description,
    age
)
JOIN nodes n
    ON n.cluster_id = c.cluster_id
   AND n.node_name = sample.node_name
WHERE c.cluster_name = 'commerce-cluster';

-- ============================================================
-- 27. SAMPLE NETWORK MESSAGES
-- ============================================================

INSERT INTO network_messages (
    cluster_id,
    operation_id,
    source_node_id,
    destination_node_id,
    message_status,
    latency_ms,
    payload_size_bytes,
    received_at,
    error_message
)
SELECT
    c.cluster_id,
    NULL,
    source.node_id,
    destination.node_id,
    sample.message_status,
    sample.latency,
    sample.payload_size,
    CASE
        WHEN sample.message_status = 'delivered'
            THEN NOW()
        ELSE NULL
    END,
    sample.error
FROM clusters c
JOIN nodes source
    ON source.cluster_id = c.cluster_id
   AND source.node_name = 'node-1'
JOIN nodes destination
    ON destination.cluster_id = c.cluster_id
   AND destination.node_name = sample_placeholder.node_name
CROSS JOIN (
    VALUES
        ('node-2', 'delivered'::message_status, 12.5::NUMERIC, 1024, NULL::TEXT),
        ('node-3', 'delivered'::message_status, 18.0::NUMERIC, 2048, NULL::TEXT),
        ('node-4', 'timed_out'::message_status, 110.0::NUMERIC, 1024, 'Node unavailable')
) AS sample_placeholder(
    node_name,
    message_status,
    latency,
    payload_size,
    error
)
WHERE c.cluster_name = 'commerce-cluster';

-- ============================================================
-- 28. SAMPLE ACKNOWLEDGEMENTS
-- ============================================================

INSERT INTO acknowledgements (
    operation_id,
    node_id,
    latency_ms,
    success,
    error_message
)
SELECT
    o.operation_id,
    n.node_id,
    sample.latency,
    sample.success,
    sample.error
FROM operations o
JOIN clusters c
    ON c.cluster_id = o.cluster_id
JOIN (
    VALUES
        (
            '20000000-0000-0000-0000-000000000001',
            'node-1',
            10.0::NUMERIC,
            TRUE,
            NULL::TEXT
        ),
        (
            '20000000-0000-0000-0000-000000000001',
            'node-2',
            12.0::NUMERIC,
            TRUE,
            NULL::TEXT
        ),
        (
            '20000000-0000-0000-0000-000000000002',
            'node-1',
            15.0::NUMERIC,
            TRUE,
            NULL::TEXT
        ),
        (
            '20000000-0000-0000-0000-000000000002',
            'node-4',
            105.0::NUMERIC,
            FALSE,
            'Node unavailable'
        )
) AS sample(
    operation_id,
    node_name,
    latency,
    success,
    error
)
    ON o.operation_id = sample.operation_id::UUID
JOIN nodes n
    ON n.cluster_id = c.cluster_id
   AND n.node_name = sample.node_name;

-- ============================================================
-- 29. TRANSACTIONAL WORKFLOW EXAMPLE
-- ============================================================

-- The procedure records the operation and its simulated local
-- replica acknowledgements in the same database transaction.
-- A real distributed commit requires remote coordination and
-- cannot be guaranteed by a local PostgreSQL transaction alone.

DO $$
DECLARE
    v_cluster_id BIGINT;
BEGIN
    SELECT cluster_id
    INTO v_cluster_id
    FROM distributed_systems.clusters
    WHERE cluster_name = 'commerce-cluster';

    CALL distributed_systems.process_write_operation(
        '30000000-0000-0000-0000-000000000001',
        v_cluster_id,
        'inventory:5001',
        'quantity:400',
        'quorum'
    );
END;
$$;

-- ============================================================
-- 30. QUERY: CLUSTER HEALTH
-- ============================================================

SELECT *
FROM cluster_health
ORDER BY cluster_id;

-- ============================================================
-- 31. QUERY: QUORUM CALCULATION
-- ============================================================

SELECT
    cluster_name,
    replication_factor,
    required_acknowledgements(
        replication_factor,
        'one'
    ) AS one_required,
    required_acknowledgements(
        replication_factor,
        'quorum'
    ) AS quorum_required,
    required_acknowledgements(
        replication_factor,
        'all'
    ) AS all_required
FROM clusters;

-- ============================================================
-- 32. QUERY: WRITE ELIGIBILITY
-- ============================================================

SELECT *
FROM check_write_eligibility(
    (
        SELECT cluster_id
        FROM clusters
        WHERE cluster_name = 'commerce-cluster'
    ),
    'quorum'
);

-- ============================================================
-- 33. QUERY: OPERATION PERFORMANCE
-- ============================================================

SELECT *
FROM operation_performance
ORDER BY operation_type;

-- ============================================================
-- 34. QUERY: REPLICA DISTRIBUTION
-- ============================================================

SELECT *
FROM replica_distribution
ORDER BY node_name;

-- ============================================================
-- 35. QUERY: LATEST VERSION PER KEY
-- ============================================================

WITH ranked_records AS (
    SELECT
        cluster_id,
        record_key,
        record_value,
        logical_version,
        record_timestamp,
        ROW_NUMBER() OVER (
            PARTITION BY cluster_id, record_key
            ORDER BY
                logical_version DESC,
                record_timestamp DESC,
                operation_id DESC
        ) AS version_rank
    FROM distributed_records
)
SELECT
    record_key,
    record_value,
    logical_version,
    record_timestamp
FROM ranked_records
WHERE version_rank = 1
ORDER BY record_key;

-- ============================================================
-- 36. QUERY: CONSISTENCY AUDIT
-- ============================================================

SELECT audit_record_consistency(
    (
        SELECT cluster_id
        FROM clusters
        WHERE cluster_name = 'commerce-cluster'
    ),
    'account:1001'
);

SELECT *
FROM consistency_checks
ORDER BY checked_at DESC;

-- ============================================================
-- 37. QUERY: FAILURE ANALYSIS
-- ============================================================

SELECT
    failure_category,
    severity,
    COUNT(*) AS incident_count,
    MAX(occurred_at) AS latest_occurrence,
    COUNT(*) FILTER (
        WHERE recovered_at IS NULL
    ) AS unresolved_incidents
FROM failure_events
GROUP BY failure_category, severity
ORDER BY severity DESC, incident_count DESC;

-- ============================================================
-- 38. QUERY: NETWORK LATENCY
-- ============================================================

SELECT
    c.cluster_name,
    n1.node_name AS source_node,
    n2.node_name AS destination_node,
    l.latency_ms,
    l.packet_loss_rate,
    l.is_partitioned
FROM network_links l
JOIN clusters c
    ON c.cluster_id = l.cluster_id
JOIN nodes n1
    ON n1.node_id = l.source_node_id
JOIN nodes n2
    ON n2.node_id = l.destination_node_id
WHERE l.is_partitioned = TRUE
   OR l.latency_ms > c.base_latency_ms * 2
ORDER BY l.latency_ms DESC;

-- ============================================================
-- 39. QUERY: OPERATION FAILURE RATE
-- ============================================================

SELECT
    cluster_id,
    COUNT(*) AS total_operations,
    COUNT(*) FILTER (
        WHERE operation_status IN ('failed', 'timed_out')
    ) AS unsuccessful_operations,
    ROUND(
        100.0 *
        COUNT(*) FILTER (
            WHERE operation_status IN ('failed', 'timed_out')
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS failure_percentage
FROM operations
GROUP BY cluster_id;

-- ============================================================
-- 40. QUERY: REPLICA REPAIR
-- ============================================================

SELECT repair_record_replicas(
    (
        SELECT cluster_id
        FROM clusters
        WHERE cluster_name = 'commerce-cluster'
    ),
    'account:1001'
);

-- ============================================================
-- 41. QUERY: REPLICATION DIVERGENCE
-- ============================================================

SELECT
    d.record_key,
    d.logical_version,
    COUNT(DISTINCT r.node_id) AS replica_count,
    COUNT(DISTINCT r.node_id) FILTER (
        WHERE r.is_synchronized
    ) AS synchronized_count
FROM distributed_records d
JOIN replicas r
    ON r.record_id = d.record_id
GROUP BY
    d.record_key,
    d.logical_version
HAVING COUNT(DISTINCT r.node_id) > 0
ORDER BY d.record_key, d.logical_version DESC;

COMMIT;

-- ============================================================
-- END OF DISTRIBUTED SYSTEM CHALLENGES DATABASE MODEL
-- ============================================================
