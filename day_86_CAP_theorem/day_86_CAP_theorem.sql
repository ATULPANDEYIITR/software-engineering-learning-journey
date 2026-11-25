/*
 * CAP THEOREM: DISTRIBUTED DATABASE AND REPLICATION MODEL
 *
 * PostgreSQL 14+
 *
 * Models:
 * - Distributed clusters
 * - Replica nodes
 * - Network partitions
 * - Replicated key-value records
 * - Versioned writes
 * - CP and AP policies
 * - Quorum requirements
 * - Conflict resolution
 * - Read and write operations
 * - Availability monitoring
 * - Operation auditing
 * - Reconciliation
 * - Reporting and eligibility evaluation
 *
 * Execute as a database owner with permission to create schemas.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS cap_lab;

SET search_path TO cap_lab, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE cap_mode AS ENUM ('CP', 'AP');

CREATE TYPE node_state AS ENUM (
    'ONLINE',
    'OFFLINE',
    'DEGRADED'
);

CREATE TYPE operation_type AS ENUM (
    'READ',
    'WRITE',
    'RECONCILE'
);

CREATE TYPE operation_status AS ENUM (
    'SUCCESS',
    'REJECTED',
    'UNAVAILABLE',
    'CONFLICT'
);

CREATE TYPE partition_status AS ENUM (
    'CONNECTED',
    'PARTITIONED',
    'HEALED'
);

-- ============================================================
-- 2. CLUSTERS
-- ============================================================

CREATE TABLE clusters (
    cluster_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_name VARCHAR(120) NOT NULL UNIQUE,
    mode cap_mode NOT NULL,
    expected_nodes INTEGER NOT NULL CHECK (expected_nodes > 0),
    quorum_size INTEGER GENERATED ALWAYS AS
        ((expected_nodes / 2) + 1) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (length(trim(cluster_name)) > 0)
);

COMMENT ON TABLE clusters IS
'Logical distributed storage clusters with a selected CAP operating policy.';

COMMENT ON COLUMN clusters.mode IS
'CP prioritizes consistency during partitions; AP prioritizes availability.';

-- ============================================================
-- 3. REPLICA NODES
-- ============================================================

CREATE TABLE replica_nodes (
    node_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(cluster_id)
        ON DELETE CASCADE,
    node_name VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    state node_state NOT NULL DEFAULT 'ONLINE',
    partition_group INTEGER NOT NULL DEFAULT 0,
    last_heartbeat TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cluster_id, node_name),
    CHECK (partition_group >= 0),
    CHECK (length(trim(region)) > 0)
);

CREATE INDEX idx_nodes_cluster_state
    ON replica_nodes(cluster_id, state);

CREATE INDEX idx_nodes_partition
    ON replica_nodes(cluster_id, partition_group, state);

-- ============================================================
-- 4. PARTITION HISTORY
-- ============================================================

CREATE TABLE network_partitions (
    partition_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(cluster_id)
        ON DELETE CASCADE,
    status partition_status NOT NULL,
    description TEXT NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    healed_at TIMESTAMPTZ,
    CHECK (
        (status = 'HEALED' AND healed_at IS NOT NULL)
        OR
        (status <> 'HEALED' AND healed_at IS NULL)
    )
);

CREATE INDEX idx_partitions_active
    ON network_partitions(cluster_id, detected_at DESC)
    WHERE status = 'PARTITIONED';

-- ============================================================
-- 5. KEY-VALUE RECORDS
-- ============================================================

CREATE TABLE replicated_records (
    record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(cluster_id)
        ON DELETE CASCADE,
    record_key VARCHAR(255) NOT NULL,
    record_value TEXT NOT NULL,
    logical_version BIGINT NOT NULL CHECK (logical_version > 0),
    writer_node_id BIGINT NOT NULL REFERENCES replica_nodes(node_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (cluster_id, record_key),
    CHECK (length(trim(record_key)) > 0)
);

CREATE INDEX idx_records_cluster_version
    ON replicated_records(cluster_id, logical_version DESC);

-- ============================================================
-- 6. REPLICA RECORD STATE
-- ============================================================

CREATE TABLE replica_records (
    replica_record_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_id BIGINT NOT NULL REFERENCES replica_nodes(node_id)
        ON DELETE CASCADE,
    record_key VARCHAR(255) NOT NULL,
    record_value TEXT NOT NULL,
    logical_version BIGINT NOT NULL CHECK (logical_version > 0),
    writer_node_id BIGINT NOT NULL REFERENCES replica_nodes(node_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (node_id, record_key)
);

CREATE INDEX idx_replica_records_key_version
    ON replica_records(record_key, logical_version DESC);

-- ============================================================
-- 7. OPERATION AUDIT
-- ============================================================

CREATE TABLE operation_logs (
    operation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(cluster_id)
        ON DELETE CASCADE,
    node_id BIGINT REFERENCES replica_nodes(node_id),
    operation operation_type NOT NULL,
    operation_status operation_status NOT NULL,
    record_key VARCHAR(255),
    request_value TEXT,
    reason TEXT,
    quorum_required INTEGER,
    connected_nodes INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_operation_cluster_time
    ON operation_logs(cluster_id, created_at DESC);

CREATE INDEX idx_operation_failures
    ON operation_logs(cluster_id, operation_status, created_at DESC)
    WHERE operation_status <> 'SUCCESS';

-- ============================================================
-- 8. CONSISTENCY AND VERSION MANAGEMENT
-- ============================================================

CREATE TABLE version_conflicts (
    conflict_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cluster_id BIGINT NOT NULL REFERENCES clusters(cluster_id)
        ON DELETE CASCADE,
    record_key VARCHAR(255) NOT NULL,
    selected_version BIGINT NOT NULL,
    conflicting_versions JSONB NOT NULL,
    resolution_policy VARCHAR(50) NOT NULL,
    resolved_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 9. NODE VALIDATION TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION validate_replica_cluster()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    configured_count INTEGER;
BEGIN
    SELECT expected_nodes
    INTO configured_count
    FROM clusters
    WHERE cluster_id = NEW.cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Cluster % does not exist', NEW.cluster_id;
    END IF;

    IF (
        SELECT count(*)
        FROM replica_nodes
        WHERE cluster_id = NEW.cluster_id
    ) >= configured_count THEN
        RAISE EXCEPTION
            'Cluster % already has its configured number of nodes',
            NEW.cluster_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_replica_cluster
BEFORE INSERT ON replica_nodes
FOR EACH ROW
EXECUTE FUNCTION validate_replica_cluster();

-- ============================================================
-- 10. OPERATION ELIGIBILITY
-- ============================================================

CREATE OR REPLACE FUNCTION evaluate_operation(
    p_cluster_id BIGINT,
    p_node_id BIGINT,
    p_operation operation_type
)
RETURNS TABLE (
    eligible BOOLEAN,
    connected_nodes INTEGER,
    required_quorum INTEGER,
    explanation TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_mode cap_mode;
    v_group INTEGER;
    v_node_state node_state;
    v_connected INTEGER;
    v_quorum INTEGER;
BEGIN
    SELECT c.mode, c.quorum_size,
           n.partition_group, n.state
    INTO v_mode, v_quorum, v_group, v_node_state
    FROM clusters c
    JOIN replica_nodes n
      ON n.cluster_id = c.cluster_id
    WHERE c.cluster_id = p_cluster_id
      AND n.node_id = p_node_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Invalid cluster or requesting node';
    END IF;

    SELECT count(*)::INTEGER
    INTO v_connected
    FROM replica_nodes
    WHERE cluster_id = p_cluster_id
      AND partition_group = v_group
      AND state = 'ONLINE';

    IF v_node_state <> 'ONLINE' THEN
        RETURN QUERY SELECT
            FALSE,
            v_connected,
            v_quorum,
            'Requesting node is offline';
        RETURN;
    END IF;

    IF v_connected = 0 THEN
        RETURN QUERY SELECT
            FALSE,
            v_connected,
            v_quorum,
            'No available replicas';
        RETURN;
    END IF;

    IF v_mode = 'CP' AND v_connected < v_quorum THEN
        RETURN QUERY SELECT
            FALSE,
            v_connected,
            v_quorum,
            'CP operation rejected because quorum is unavailable';
        RETURN;
    END IF;

    RETURN QUERY SELECT
        TRUE,
        v_connected,
        v_quorum,
        CASE
            WHEN v_mode = 'CP'
                THEN 'Majority quorum is available'
            ELSE 'AP local availability condition is satisfied'
        END;
END;
$$;

-- ============================================================
-- 11. WRITE PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE execute_write(
    p_cluster_id BIGINT,
    p_node_id BIGINT,
    p_key VARCHAR(255),
    p_value TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_mode cap_mode;
    v_eligible BOOLEAN;
    v_connected INTEGER;
    v_quorum INTEGER;
    v_explanation TEXT;
    v_version BIGINT;
    v_group INTEGER;
    v_record_version BIGINT;
BEGIN
    IF p_key IS NULL OR length(trim(p_key)) = 0 THEN
        RAISE EXCEPTION 'Record key cannot be empty';
    END IF;

    IF p_value IS NULL THEN
        RAISE EXCEPTION 'Record value cannot be NULL';
    END IF;

    SELECT mode
    INTO v_mode
    FROM clusters
    WHERE cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    SELECT *
    INTO v_eligible, v_connected, v_quorum, v_explanation
    FROM evaluate_operation(
        p_cluster_id,
        p_node_id,
        'WRITE'
    );

    IF NOT v_eligible THEN
        INSERT INTO operation_logs (
            cluster_id,
            node_id,
            operation,
            operation_status,
            record_key,
            request_value,
            reason,
            quorum_required,
            connected_nodes
        )
        VALUES (
            p_cluster_id,
            p_node_id,
            'WRITE',
            CASE
                WHEN v_connected = 0 THEN 'UNAVAILABLE'
                ELSE 'REJECTED'
            END,
            p_key,
            p_value,
            v_explanation,
            v_quorum,
            v_connected
        );

        RETURN;
    END IF;

    SELECT partition_group
    INTO v_group
    FROM replica_nodes
    WHERE node_id = p_node_id;

    /*
     * Lock the cluster row to serialize logical version allocation
     * among concurrent writers in this database model.
     */
    PERFORM 1
    FROM clusters
    WHERE cluster_id = p_cluster_id
    FOR UPDATE;

    SELECT COALESCE(MAX(logical_version), 0) + 1
    INTO v_version
    FROM replicated_records
    WHERE cluster_id = p_cluster_id;

    IF v_mode = 'CP' THEN
        /*
         * CP writes update all online replicas in the requester's
         * partition only after quorum eligibility is established.
         */
        FOR UPDATE IN
            SELECT node_id
            FROM replica_nodes
            WHERE cluster_id = p_cluster_id
              AND partition_group = v_group
              AND state = 'ONLINE'
            ORDER BY node_id
        LOOP
            NULL;
        END LOOP;

        INSERT INTO replica_records (
            node_id,
            record_key,
            record_value,
            logical_version,
            writer_node_id
        )
        SELECT
            node_id,
            p_key,
            p_value,
            v_version,
            p_node_id
        FROM replica_nodes
        WHERE cluster_id = p_cluster_id
          AND partition_group = v_group
          AND state = 'ONLINE'
        ON CONFLICT (node_id, record_key)
        DO UPDATE SET
            record_value = EXCLUDED.record_value,
            logical_version = EXCLUDED.logical_version,
            writer_node_id = EXCLUDED.writer_node_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE replica_records.logical_version
              < EXCLUDED.logical_version;

        INSERT INTO replicated_records (
            cluster_id,
            record_key,
            record_value,
            logical_version,
            writer_node_id
        )
        VALUES (
            p_cluster_id,
            p_key,
            p_value,
            v_version,
            p_node_id
        )
        ON CONFLICT (cluster_id, record_key)
        DO UPDATE SET
            record_value = EXCLUDED.record_value,
            logical_version = EXCLUDED.logical_version,
            writer_node_id = EXCLUDED.writer_node_id,
            updated_at = CURRENT_TIMESTAMP;

    ELSE
        -- AP accepts the write on the requesting replica.
        SELECT COALESCE(MAX(logical_version), 0) + 1
        INTO v_record_version
        FROM replica_records
        WHERE node_id = p_node_id;

        INSERT INTO replica_records (
            node_id,
            record_key,
            record_value,
            logical_version,
            writer_node_id
        )
        VALUES (
            p_node_id,
            p_key,
            p_value,
            v_record_version,
            p_node_id
        )
        ON CONFLICT (node_id, record_key)
        DO UPDATE SET
            record_value = EXCLUDED.record_value,
            logical_version = EXCLUDED.logical_version,
            writer_node_id = EXCLUDED.writer_node_id,
            updated_at = CURRENT_TIMESTAMP
        WHERE replica_records.logical_version
              < EXCLUDED.logical_version;
    END IF;

    INSERT INTO operation_logs (
        cluster_id,
        node_id,
        operation,
        operation_status,
        record_key,
        request_value,
        reason,
        quorum_required,
        connected_nodes
    )
    VALUES (
        p_cluster_id,
        p_node_id,
        'WRITE',
        'SUCCESS',
        p_key,
        p_value,
        v_explanation,
        v_quorum,
        v_connected
    );
END;
$$;

-- ============================================================
-- 12. READ FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION execute_read(
    p_cluster_id BIGINT,
    p_node_id BIGINT,
    p_key VARCHAR(255)
)
RETURNS TABLE (
    result_status operation_status,
    result_value TEXT,
    explanation TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_mode cap_mode;
    v_eligible BOOLEAN;
    v_connected INTEGER;
    v_quorum INTEGER;
    v_reason TEXT;
    v_group INTEGER;
BEGIN
    SELECT mode
    INTO v_mode
    FROM clusters
    WHERE cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    SELECT partition_group
    INTO v_group
    FROM replica_nodes
    WHERE node_id = p_node_id
      AND cluster_id = p_cluster_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown requesting node';
    END IF;

    SELECT *
    INTO v_eligible, v_connected, v_quorum, v_reason
    FROM evaluate_operation(
        p_cluster_id,
        p_node_id,
        'READ'
    );

    IF NOT v_eligible THEN
        RETURN QUERY SELECT
            CASE
                WHEN v_connected = 0 THEN 'UNAVAILABLE'::operation_status
                ELSE 'REJECTED'::operation_status
            END,
            NULL::TEXT,
            v_reason;

        RETURN;
    END IF;

    IF v_mode = 'AP' THEN
        RETURN QUERY
        SELECT
            'SUCCESS'::operation_status,
            rr.record_value,
            'Local replica read'
        FROM replica_nodes rn
        LEFT JOIN replica_records rr
          ON rr.node_id = rn.node_id
         AND rr.record_key = p_key
        WHERE rn.node_id = p_node_id;

    ELSE
        RETURN QUERY
        SELECT
            'SUCCESS'::operation_status,
            (
                SELECT rr.record_value
                FROM replica_records rr
                JOIN replica_nodes rn
                  ON rn.node_id = rr.node_id
                WHERE rn.cluster_id = p_cluster_id
                  AND rn.partition_group = v_group
                  AND rn.state = 'ONLINE'
                  AND rr.record_key = p_key
                ORDER BY
                    rr.logical_version DESC,
                    rr.writer_node_id DESC
                LIMIT 1
            ),
            'Quorum-backed replica read';
    END IF;

    INSERT INTO operation_logs (
        cluster_id,
        node_id,
        operation,
        operation_status,
        record_key,
        reason,
        quorum_required,
        connected_nodes
    )
    VALUES (
        p_cluster_id,
        p_node_id,
        'READ',
        'SUCCESS',
        p_key,
        v_reason,
        v_quorum,
        v_connected
    );
END;
$$;

-- ============================================================
-- 13. RECONCILIATION PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE reconcile_cluster(
    p_cluster_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_conflicts JSONB;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM clusters
        WHERE cluster_id = p_cluster_id
    ) THEN
        RAISE EXCEPTION 'Unknown cluster';
    END IF;

    /*
     * A deterministic last-version-wins policy is used here.
     * Writer node ID resolves equal-version ties.
     * This is not universally suitable for business data.
     */
    WITH ranked AS (
        SELECT
            rr.record_key,
            rr.record_value,
            rr.logical_version,
            rr.writer_node_id,
            ROW_NUMBER() OVER (
                PARTITION BY rr.record_key
                ORDER BY
                    rr.logical_version DESC,
                    rr.writer_node_id DESC
            ) AS rank_number,
            COUNT(*) OVER (
                PARTITION BY rr.record_key
            ) AS replica_count
        FROM replica_records rr
        JOIN replica_nodes rn
          ON rn.node_id = rr.node_id
        WHERE rn.cluster_id = p_cluster_id
          AND rn.state = 'ONLINE'
    ),
    winners AS (
        SELECT
            record_key,
            record_value,
            logical_version,
            writer_node_id
        FROM ranked
        WHERE rank_number = 1
    )
    INSERT INTO version_conflicts (
        cluster_id,
        record_key,
        selected_version,
        conflicting_versions,
        resolution_policy
    )
    SELECT
        p_cluster_id,
        r.record_key,
        r.logical_version,
        jsonb_agg(
            jsonb_build_object(
                'value', rr.record_value,
                'version', rr.logical_version,
                'writer', rr.writer_node_id
            )
        ),
        'VERSION_THEN_WRITER'
    FROM winners r
    JOIN replica_records rr
      ON rr.record_key = r.record_key
    JOIN replica_nodes rn
      ON rn.node_id = rr.node_id
    WHERE rn.cluster_id = p_cluster_id
    GROUP BY r.record_key, r.logical_version
    HAVING COUNT(DISTINCT rr.record_value) > 1;

    WITH ranked AS (
        SELECT
            rr.record_key,
            rr.record_value,
            rr.logical_version,
            rr.writer_node_id,
            ROW_NUMBER() OVER (
                PARTITION BY rr.record_key
                ORDER BY
                    rr.logical_version DESC,
                    rr.writer_node_id DESC
            ) AS rank_number
        FROM replica_records rr
        JOIN replica_nodes rn
          ON rn.node_id = rr.node_id
        WHERE rn.cluster_id = p_cluster_id
          AND rn.state = 'ONLINE'
    ),
    winners AS (
        SELECT *
        FROM ranked
        WHERE rank_number = 1
    )
    INSERT INTO replica_records (
        node_id,
        record_key,
        record_value,
        logical_version,
        writer_node_id
    )
    SELECT
        rn.node_id,
        w.record_key,
        w.record_value,
        w.logical_version,
        w.writer_node_id
    FROM replica_nodes rn
    CROSS JOIN winners w
    WHERE rn.cluster_id = p_cluster_id
      AND rn.state = 'ONLINE'
    ON CONFLICT (node_id, record_key)
    DO UPDATE SET
        record_value = EXCLUDED.record_value,
        logical_version = EXCLUDED.logical_version,
        writer_node_id = EXCLUDED.writer_node_id,
        updated_at = CURRENT_TIMESTAMP
    WHERE
        replica_records.logical_version < EXCLUDED.logical_version
        OR (
            replica_records.logical_version = EXCLUDED.logical_version
            AND replica_records.writer_node_id < EXCLUDED.writer_node_id
        );

    INSERT INTO operation_logs (
        cluster_id,
        operation,
        operation_status,
        reason
    )
    VALUES (
        p_cluster_id,
        'RECONCILE',
        'SUCCESS',
        'Online replica records reconciled.'
    );

    UPDATE network_partitions
    SET status = 'HEALED',
        healed_at = CURRENT_TIMESTAMP
    WHERE cluster_id = p_cluster_id
      AND status = 'PARTITIONED';
END;
$$;

-- ============================================================
-- 14. MONITORING VIEWS
-- ============================================================

CREATE OR REPLACE VIEW cluster_availability AS
SELECT
    c.cluster_id,
    c.cluster_name,
    c.mode,
    c.expected_nodes,
    c.quorum_size,
    COUNT(rn.node_id) FILTER (
        WHERE rn.state = 'ONLINE'
    ) AS online_nodes,
    COUNT(rn.node_id) FILTER (
        WHERE rn.state <> 'ONLINE'
    ) AS unavailable_nodes,
    COUNT(DISTINCT rn.partition_group) FILTER (
        WHERE rn.state = 'ONLINE'
    ) AS active_partition_groups
FROM clusters c
LEFT JOIN replica_nodes rn
  ON rn.cluster_id = c.cluster_id
GROUP BY
    c.cluster_id,
    c.cluster_name,
    c.mode,
    c.expected_nodes,
    c.quorum_size;

CREATE OR REPLACE VIEW replica_consistency_report AS
SELECT
    rn.cluster_id,
    rr.record_key,
    COUNT(DISTINCT rr.record_value) AS distinct_values,
    COUNT(DISTINCT rr.logical_version) AS distinct_versions,
    MAX(rr.logical_version) AS highest_version,
    COUNT(DISTINCT rn.node_id) AS replica_count
FROM replica_nodes rn
JOIN replica_records rr
  ON rr.node_id = rn.node_id
WHERE rn.state = 'ONLINE'
GROUP BY rn.cluster_id, rr.record_key;

CREATE OR REPLACE VIEW operation_failure_report AS
SELECT
    cluster_id,
    operation,
    operation_status,
    COUNT(*) AS total_operations,
    MAX(created_at) AS latest_failure
FROM operation_logs
WHERE operation_status <> 'SUCCESS'
GROUP BY
    cluster_id,
    operation,
    operation_status;

-- ============================================================
-- 15. SAMPLE CLUSTERS
-- ============================================================

INSERT INTO clusters (
    cluster_name,
    mode,
    expected_nodes
)
VALUES
    ('banking-ledger-cluster', 'CP', 3),
    ('product-catalog-cluster', 'AP', 3);

INSERT INTO replica_nodes (
    cluster_id,
    node_name,
    region,
    partition_group
)
SELECT
    c.cluster_id,
    data.node_name,
    data.region,
    0
FROM clusters c
CROSS JOIN (
    VALUES
        ('node-a', 'Mumbai'),
        ('node-b', 'Delhi'),
        ('node-c', 'Bengaluru')
) AS data(node_name, region)
WHERE c.cluster_name = 'banking-ledger-cluster';

INSERT INTO replica_nodes (
    cluster_id,
    node_name,
    region,
    partition_group
)
SELECT
    c.cluster_id,
    data.node_name,
    data.region,
    0
FROM clusters c
CROSS JOIN (
    VALUES
        ('node-a', 'Mumbai'),
        ('node-b', 'Delhi'),
        ('node-c', 'Hyderabad')
) AS data(node_name, region)
WHERE c.cluster_name = 'product-catalog-cluster';

-- ============================================================
-- 16. INITIAL REPLICA DATA
-- ============================================================

INSERT INTO replica_records (
    node_id,
    record_key,
    record_value,
    logical_version,
    writer_node_id
)
SELECT
    node.node_id,
    'account-1001',
    '5000',
    1,
    node.node_id
FROM replica_nodes node
JOIN clusters c
  ON c.cluster_id = node.cluster_id
WHERE c.cluster_name = 'banking-ledger-cluster';

INSERT INTO replicated_records (
    cluster_id,
    record_key,
    record_value,
    logical_version,
    writer_node_id
)
SELECT
    c.cluster_id,
    'account-1001',
    '5000',
    1,
    MIN(node.node_id)
FROM clusters c
JOIN replica_nodes node
  ON node.cluster_id = c.cluster_id
WHERE c.cluster_name = 'banking-ledger-cluster'
GROUP BY c.cluster_id;

INSERT INTO replica_records (
    node_id,
    record_key,
    record_value,
    logical_version,
    writer_node_id
)
SELECT
    node.node_id,
    'product-101',
    '100',
    1,
    node.node_id
FROM replica_nodes node
JOIN clusters c
  ON c.cluster_id = node.cluster_id
WHERE c.cluster_name = 'product-catalog-cluster';

-- ============================================================
-- 17. TRANSACTIONAL CP AND AP DEMONSTRATIONS
-- ============================================================

-- CP: create a partition with one minority node and two majority nodes.

UPDATE replica_nodes node
SET partition_group = CASE
    WHEN node.node_name = 'node-a' THEN 1
    ELSE 2
END
FROM clusters c
WHERE node.cluster_id = c.cluster_id
  AND c.cluster_name = 'banking-ledger-cluster';

INSERT INTO network_partitions (
    cluster_id,
    status,
    description
)
SELECT
    cluster_id,
    'PARTITIONED',
    'Simulated one-node minority and two-node majority'
FROM clusters
WHERE cluster_name = 'banking-ledger-cluster';

-- The following minority write is rejected and audited.
CALL execute_write(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'banking-ledger-cluster'
    ),
    (
        SELECT node_id FROM replica_nodes
        WHERE node_name = 'node-a'
          AND cluster_id = (
              SELECT cluster_id FROM clusters
              WHERE cluster_name = 'banking-ledger-cluster'
          )
    ),
    'account-1001',
    '6000'
);

-- The majority partition can accept a write.
CALL execute_write(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'banking-ledger-cluster'
    ),
    (
        SELECT node_id FROM replica_nodes
        WHERE node_name = 'node-b'
          AND cluster_id = (
              SELECT cluster_id FROM clusters
              WHERE cluster_name = 'banking-ledger-cluster'
          )
    ),
    'account-1001',
    '5500'
);

-- Restore communication.
UPDATE replica_nodes node
SET partition_group = 0
FROM clusters c
WHERE node.cluster_id = c.cluster_id
  AND c.cluster_name = 'banking-ledger-cluster';

CALL reconcile_cluster(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'banking-ledger-cluster'
    )
);

-- AP: independent partitions accept different local writes.

UPDATE replica_nodes node
SET partition_group = CASE
    WHEN node.node_name = 'node-a' THEN 1
    ELSE 2
END
FROM clusters c
WHERE node.cluster_id = c.cluster_id
  AND c.cluster_name = 'product-catalog-cluster';

INSERT INTO network_partitions (
    cluster_id,
    status,
    description
)
SELECT
    cluster_id,
    'PARTITIONED',
    'Simulated independent AP replica groups'
FROM clusters
WHERE cluster_name = 'product-catalog-cluster';

CALL execute_write(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'product-catalog-cluster'
    ),
    (
        SELECT node_id FROM replica_nodes
        WHERE node_name = 'node-a'
          AND cluster_id = (
              SELECT cluster_id FROM clusters
              WHERE cluster_name = 'product-catalog-cluster'
          )
    ),
    'product-101',
    '80'
);

CALL execute_write(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'product-catalog-cluster'
    ),
    (
        SELECT node_id FROM replica_nodes
        WHERE node_name = 'node-b'
          AND cluster_id = (
              SELECT cluster_id FROM clusters
              WHERE cluster_name = 'product-catalog-cluster'
          )
    ),
    'product-101',
    '90'
);

-- Reconnect replicas and reconcile divergent values.
UPDATE replica_nodes node
SET partition_group = 0
FROM clusters c
WHERE node.cluster_id = c.cluster_id
  AND c.cluster_name = 'product-catalog-cluster';

CALL reconcile_cluster(
    (
        SELECT cluster_id FROM clusters
        WHERE cluster_name = 'product-catalog-cluster'
    )
);

COMMIT;

-- ============================================================
-- 18. RETRIEVAL QUERIES
-- ============================================================

SELECT *
FROM cluster_availability
ORDER BY cluster_name;

SELECT
    c.cluster_name,
    rn.node_name,
    rn.region,
    rn.state,
    rn.partition_group
FROM clusters c
JOIN replica_nodes rn
  ON rn.cluster_id = c.cluster_id
ORDER BY c.cluster_name, rn.node_name;

SELECT
    c.cluster_name,
    rr.record_key,
    rr.record_value,
    rr.logical_version,
    rn.node_name
FROM replica_records rr
JOIN replica_nodes rn
  ON rn.node_id = rr.node_id
JOIN clusters c
  ON c.cluster_id = rn.cluster_id
ORDER BY c.cluster_name, rr.record_key, rn.node_name;

-- ============================================================
-- 19. ELIGIBILITY EVALUATION
-- ============================================================

SELECT
    c.cluster_name,
    rn.node_name,
    result.eligible,
    result.connected_nodes,
    result.required_quorum,
    result.explanation
FROM clusters c
JOIN replica_nodes rn
  ON rn.cluster_id = c.cluster_id
CROSS JOIN LATERAL evaluate_operation(
    c.cluster_id,
    rn.node_id,
    'WRITE'
) result
ORDER BY c.cluster_name, rn.node_name;

-- ============================================================
-- 20. CONSISTENCY REPORTING
-- ============================================================

SELECT *
FROM replica_consistency_report
ORDER BY cluster_id, record_key;

-- A value of distinct_values greater than one indicates
-- divergent online replica values.

SELECT
    cluster_id,
    record_key,
    distinct_values,
    distinct_versions,
    highest_version,
    replica_count
FROM replica_consistency_report
WHERE distinct_values > 1
   OR distinct_versions > 1;

-- ============================================================
-- 21. OPERATION FAILURE ANALYSIS
-- ============================================================

SELECT *
FROM operation_failure_report
ORDER BY total_operations DESC;

SELECT
    operation,
    operation_status,
    reason,
    COUNT(*) AS occurrences
FROM operation_logs
GROUP BY operation, operation_status, reason
ORDER BY occurrences DESC;

-- ============================================================
-- 22. CONFLICT HISTORY
-- ============================================================

SELECT
    c.cluster_name,
    vc.record_key,
    vc.selected_version,
    vc.conflicting_versions,
    vc.resolution_policy,
    vc.resolved_at
FROM version_conflicts vc
JOIN clusters c
  ON c.cluster_id = vc.cluster_id
ORDER BY vc.resolved_at DESC;

-- ============================================================
-- 23. OPERATIONAL CAP ASSESSMENT
-- ============================================================

SELECT
    cluster_name,
    mode,
    expected_nodes,
    online_nodes,
    quorum_size,
    active_partition_groups,
    CASE
        WHEN mode = 'CP'
             AND online_nodes >= quorum_size
            THEN 'QUORUM_AVAILABLE'
        WHEN mode = 'CP'
            THEN 'QUORUM_UNAVAILABLE'
        WHEN mode = 'AP'
             AND online_nodes > 0
            THEN 'LOCAL_SERVICE_AVAILABLE'
        ELSE 'SERVICE_UNAVAILABLE'
    END AS operational_assessment
FROM cluster_availability
ORDER BY cluster_name;
