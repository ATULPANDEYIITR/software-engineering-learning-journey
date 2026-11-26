-- ============================================================
-- DISTRIBUTED DATABASE CONSISTENCY MODELS
-- PostgreSQL 15+
--
-- Models:
-- 1. Strong consistency
-- 2. Eventual consistency
-- 3. Causal consistency
--
-- The database simulates multiple logical replicas within
-- one PostgreSQL instance. It does not implement a distributed
-- consensus protocol or real network replication.
-- ============================================================

BEGIN;

DROP SCHEMA IF EXISTS consistency_lab CASCADE;
CREATE SCHEMA consistency_lab;

SET search_path TO consistency_lab, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE consistency_model AS ENUM (
    'strong',
    'eventual',
    'causal'
);

CREATE TYPE replica_status AS ENUM (
    'online',
    'offline'
);

CREATE TYPE event_status AS ENUM (
    'committed',
    'pending',
    'rejected'
);

CREATE TYPE conflict_resolution AS ENUM (
    'last_writer_wins',
    'manual_review'
);

-- ============================================================
-- 2. CORE ENTITIES
-- ============================================================

CREATE TABLE replicas (
    replica_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    replica_name VARCHAR(100) NOT NULL UNIQUE,
    region VARCHAR(100) NOT NULL,
    status replica_status NOT NULL DEFAULT 'online',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ
);

CREATE TABLE consistency_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    policy_name VARCHAR(100) NOT NULL UNIQUE,
    model consistency_model NOT NULL,
    minimum_replicas INTEGER NOT NULL DEFAULT 1,
    require_all_replicas BOOLEAN NOT NULL DEFAULT FALSE,
    resolution conflict_resolution NOT NULL DEFAULT 'last_writer_wins',
    max_pending_events INTEGER NOT NULL DEFAULT 10000,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT valid_minimum_replicas
        CHECK (minimum_replicas >= 1),

    CONSTRAINT valid_pending_limit
        CHECK (max_pending_events > 0)
);

CREATE TABLE data_items (
    item_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_key VARCHAR(200) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_item_key
        CHECK (
            LENGTH(TRIM(item_key)) BETWEEN 1 AND 200
        )
);

-- Each logical replica maintains its own value.
CREATE TABLE replica_values (
    replica_id BIGINT NOT NULL REFERENCES replicas(replica_id),
    item_id BIGINT NOT NULL REFERENCES data_items(item_id),
    item_value JSONB NOT NULL,

    version BIGINT NOT NULL DEFAULT 0,
    origin_replica_id BIGINT REFERENCES replicas(replica_id),
    event_id UUID,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (replica_id, item_id),

    CONSTRAINT valid_version
        CHECK (version >= 0)
);

CREATE TABLE write_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    item_id BIGINT NOT NULL REFERENCES data_items(item_id),
    origin_replica_id BIGINT NOT NULL REFERENCES replicas(replica_id),

    item_value JSONB NOT NULL,

    consistency consistency_model NOT NULL,
    status event_status NOT NULL DEFAULT 'pending',

    logical_version BIGINT NOT NULL,
    sequence_number BIGINT GENERATED ALWAYS AS IDENTITY,

    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),

    CONSTRAINT valid_logical_version
        CHECK (logical_version > 0)
);

-- Vector-clock components are stored separately.
CREATE TABLE event_clock_components (
    event_id UUID NOT NULL REFERENCES write_events(event_id)
        ON DELETE CASCADE,

    clock_replica_id BIGINT NOT NULL REFERENCES replicas(replica_id),

    clock_value BIGINT NOT NULL,

    PRIMARY KEY (event_id, clock_replica_id),

    CONSTRAINT valid_clock_value
        CHECK (clock_value >= 0)
);

-- Explicit causal dependency graph.
CREATE TABLE causal_dependencies (
    event_id UUID NOT NULL REFERENCES write_events(event_id)
        ON DELETE CASCADE,

    depends_on_event_id UUID NOT NULL REFERENCES write_events(event_id),

    PRIMARY KEY (event_id, depends_on_event_id),

    CONSTRAINT no_self_dependency
        CHECK (event_id <> depends_on_event_id)
);

CREATE TABLE replication_queue (
    queue_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    event_id UUID NOT NULL REFERENCES write_events(event_id),
    replica_id BIGINT NOT NULL REFERENCES replicas(replica_id),

    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,

    queued_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMPTZ,

    CONSTRAINT unique_replication_target
        UNIQUE (event_id, replica_id),

    CONSTRAINT valid_attempts
        CHECK (attempts >= 0)
);

CREATE TABLE consistency_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    event_id UUID REFERENCES write_events(event_id),
    replica_id BIGINT REFERENCES replicas(replica_id),

    action VARCHAR(50) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}'::JSONB,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 3. PERFORMANCE INDEXES
-- ============================================================

CREATE INDEX idx_replicas_status
    ON replicas(status);

CREATE INDEX idx_write_events_item_sequence
    ON write_events(item_id, sequence_number DESC);

CREATE INDEX idx_write_events_status
    ON write_events(status, event_timestamp);

CREATE INDEX idx_event_clock_replica
    ON event_clock_components(clock_replica_id, clock_value);

CREATE INDEX idx_causal_dependencies_parent
    ON causal_dependencies(depends_on_event_id);

CREATE INDEX idx_replication_pending
    ON replication_queue(replica_id, queued_at)
    WHERE processed_at IS NULL;

CREATE INDEX idx_audit_timestamp
    ON consistency_audit(recorded_at DESC);

-- ============================================================
-- 4. SAMPLE REPLICAS AND POLICIES
-- ============================================================

INSERT INTO replicas (
    replica_name,
    region,
    status
)
VALUES
    ('mumbai-primary', 'India-West', 'online'),
    ('delhi-secondary', 'India-North', 'online'),
    ('singapore-edge', 'Asia-Pacific', 'online'),
    ('london-edge', 'Europe', 'online');

INSERT INTO consistency_policies (
    policy_name,
    model,
    minimum_replicas,
    require_all_replicas,
    resolution
)
VALUES
    ('financial-transactions', 'strong', 4, TRUE, 'manual_review'),
    ('product-catalog', 'eventual', 1, FALSE, 'last_writer_wins'),
    ('order-workflow', 'causal', 1, FALSE, 'manual_review');

INSERT INTO data_items (
    item_key,
    description
)
VALUES
    ('account:1001', 'Customer financial balance'),
    ('inventory:501', 'Product inventory quantity'),
    ('order:9001', 'Customer order state'),
    ('payment:9001', 'Payment state'),
    ('profile:1001', 'Customer profile');

-- ============================================================
-- 5. INITIAL REPLICA STATE
-- ============================================================

INSERT INTO replica_values (
    replica_id,
    item_id,
    item_value,
    version
)
SELECT
    r.replica_id,
    d.item_id,
    CASE
        WHEN d.item_key = 'account:1001'
            THEN '{"balance": 50000, "currency": "INR"}'::JSONB
        WHEN d.item_key = 'inventory:501'
            THEN '{"quantity": 200}'::JSONB
        WHEN d.item_key = 'order:9001'
            THEN '{"status": "CREATED"}'::JSONB
        WHEN d.item_key = 'payment:9001'
            THEN '{"status": "NOT_STARTED"}'::JSONB
        ELSE '{"name": "Customer A"}'::JSONB
    END,
    1
FROM replicas r
CROSS JOIN data_items d;

-- ============================================================
-- 6. VECTOR CLOCK FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION clock_dominates(
    p_left UUID,
    p_right UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT NOT EXISTS (
        SELECT 1
        FROM event_clock_components right_clock
        LEFT JOIN event_clock_components left_clock
            ON left_clock.event_id = p_left
           AND left_clock.clock_replica_id =
               right_clock.clock_replica_id
        WHERE right_clock.event_id = p_right
          AND COALESCE(left_clock.clock_value, 0)
              < right_clock.clock_value
    );
$$;

CREATE OR REPLACE FUNCTION clocks_concurrent(
    p_left UUID,
    p_right UUID
)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
AS $$
    SELECT
        NOT clock_dominates(p_left, p_right)
        AND NOT clock_dominates(p_right, p_left);
$$;

-- ============================================================
-- 7. REPLICA AVAILABILITY VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_strong_write(
    p_policy_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE PLPGSQL
STABLE
AS $$
DECLARE
    v_minimum INTEGER;
    v_require_all BOOLEAN;
    v_total INTEGER;
    v_online INTEGER;
BEGIN
    SELECT minimum_replicas, require_all_replicas
    INTO v_minimum, v_require_all
    FROM consistency_policies
    WHERE policy_id = p_policy_id
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consistency policy is missing or disabled';
    END IF;

    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE status = 'online')
    INTO v_total, v_online
    FROM replicas;

    IF v_online < v_minimum THEN
        RAISE EXCEPTION
            'Strong write rejected: available replicas %, required %',
            v_online, v_minimum;
    END IF;

    IF v_require_all AND v_online <> v_total THEN
        RAISE EXCEPTION
            'Strong write rejected: every replica must be online';
    END IF;

    RETURN TRUE;
END;
$$;

-- ============================================================
-- 8. EVENT CREATION
-- ============================================================

CREATE OR REPLACE FUNCTION create_write_event(
    p_policy_id BIGINT,
    p_replica_id BIGINT,
    p_item_key VARCHAR,
    p_value JSONB,
    p_context_event UUID DEFAULT NULL
)
RETURNS UUID
LANGUAGE PLPGSQL
AS $$
DECLARE
    v_model consistency_model;
    v_item_id BIGINT;
    v_event_id UUID;
    v_clock BIGINT;
    v_origin_clock BIGINT;
    v_pending INTEGER;
    v_limit INTEGER;
    v_replica_status replica_status;
    v_dependency RECORD;
BEGIN
    SELECT model, max_pending_events
    INTO v_model, v_limit
    FROM consistency_policies
    WHERE policy_id = p_policy_id
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Invalid or disabled consistency policy';
    END IF;

    IF p_item_key IS NULL
       OR LENGTH(TRIM(p_item_key)) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'Invalid item key';
    END IF;

    IF p_value IS NULL THEN
        RAISE EXCEPTION 'JSON value cannot be SQL NULL';
    END IF;

    SELECT status
    INTO v_replica_status
    FROM replicas
    WHERE replica_id = p_replica_id;

    IF NOT FOUND OR v_replica_status <> 'online' THEN
        RAISE EXCEPTION 'Origin replica is unavailable';
    END IF;

    SELECT item_id
    INTO v_item_id
    FROM data_items
    WHERE item_key = p_item_key;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown data item: %', p_item_key;
    END IF;

    -- Validate all causal dependencies before accepting the event.
    IF v_model = 'causal' AND p_context_event IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM write_events
            WHERE event_id = p_context_event
              AND status = 'committed'
        ) THEN
            RAISE EXCEPTION
                'Causal context event does not exist or is not committed';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM replica_values
            WHERE replica_id = p_replica_id
              AND event_id = p_context_event
        ) THEN
            RAISE EXCEPTION
                'Origin has not observed the causal dependency';
        END IF;
    END IF;

    IF v_model = 'strong' THEN
        PERFORM validate_strong_write(p_policy_id);
    END IF;

    SELECT COUNT(*)
    INTO v_pending
    FROM replication_queue
    WHERE replica_id <> p_replica_id
      AND processed_at IS NULL;

    IF v_pending >= v_limit THEN
        RAISE EXCEPTION 'Replication queue capacity exceeded';
    END IF;

    SELECT COALESCE(MAX(clock_value), 0) + 1
    INTO v_clock
    FROM event_clock_components
    WHERE clock_replica_id = p_replica_id;

    SELECT COALESCE(MAX(version), 0)
    INTO v_origin_clock
    FROM replica_values
    WHERE replica_id = p_replica_id
      AND item_id = v_item_id;

    IF v_model = 'causal' AND p_context_event IS NOT NULL THEN
        -- The new event inherits the maximum observed logical clock.
        SELECT COALESCE(MAX(clock_value), 0)
        INTO v_origin_clock
        FROM event_clock_components
        WHERE event_id = p_context_event;
    END IF;

    INSERT INTO write_events (
        item_id,
        origin_replica_id,
        item_value,
        consistency,
        status,
        logical_version
    )
    VALUES (
        v_item_id,
        p_replica_id,
        p_value,
        v_model,
        CASE
            WHEN v_model = 'strong' THEN 'committed'
            ELSE 'pending'
        END,
        GREATEST(v_clock, v_origin_clock + 1)
    )
    RETURNING event_id INTO v_event_id;

    -- Copy the origin's observed clock.
    IF v_model = 'causal' THEN
        INSERT INTO event_clock_components (
            event_id,
            clock_replica_id,
            clock_value
        )
        SELECT
            v_event_id,
            clock_replica_id,
            clock_value
        FROM event_clock_components
        WHERE event_id = p_context_event
        ON CONFLICT (event_id, clock_replica_id)
        DO UPDATE SET
            clock_value = EXCLUDED.clock_value;
    END IF;

    INSERT INTO event_clock_components (
        event_id,
        clock_replica_id,
        clock_value
    )
    VALUES (
        v_event_id,
        p_replica_id,
        GREATEST(v_clock, v_origin_clock + 1)
    )
    ON CONFLICT (event_id, clock_replica_id)
    DO UPDATE SET
        clock_value = GREATEST(
            event_clock_components.clock_value,
            EXCLUDED.clock_value
        );

    IF p_context_event IS NOT NULL THEN
        INSERT INTO causal_dependencies (
            event_id,
            depends_on_event_id
        )
        VALUES (
            v_event_id,
            p_context_event
        );
    END IF;

    -- Apply the originating write.
    INSERT INTO replica_values (
        replica_id,
        item_id,
        item_value,
        version,
        origin_replica_id,
        event_id
    )
    VALUES (
        p_replica_id,
        v_item_id,
        p_value,
        GREATEST(v_clock, v_origin_clock + 1),
        p_replica_id,
        v_event_id
    )
    ON CONFLICT (replica_id, item_id)
    DO UPDATE SET
        item_value = EXCLUDED.item_value,
        version = EXCLUDED.version,
        origin_replica_id = EXCLUDED.origin_replica_id,
        event_id = EXCLUDED.event_id,
        updated_at = CURRENT_TIMESTAMP;

    IF v_model = 'strong' THEN
        -- In this logical simulation, all replicas are updated
        -- inside the same PostgreSQL transaction.
        INSERT INTO replica_values (
            replica_id,
            item_id,
            item_value,
            version,
            origin_replica_id,
            event_id
        )
        SELECT
            replica_id,
            v_item_id,
            p_value,
            GREATEST(v_clock, v_origin_clock + 1),
            p_replica_id,
            v_event_id
        FROM replicas
        WHERE replica_id <> p_replica_id
          AND status = 'online'
        ON CONFLICT (replica_id, item_id)
        DO UPDATE SET
            item_value = EXCLUDED.item_value,
            version = EXCLUDED.version,
            origin_replica_id = EXCLUDED.origin_replica_id,
            event_id = EXCLUDED.event_id,
            updated_at = CURRENT_TIMESTAMP;

    ELSE
        INSERT INTO replication_queue (
            event_id,
            replica_id
        )
        SELECT
            v_event_id,
            replica_id
        FROM replicas
        WHERE replica_id <> p_replica_id;

    END IF;

    INSERT INTO consistency_audit (
        event_id,
        replica_id,
        action,
        details
    )
    VALUES (
        v_event_id,
        p_replica_id,
        'WRITE_ACCEPTED',
        jsonb_build_object(
            'key', p_item_key,
            'model', v_model,
            'logical_version', GREATEST(v_clock, v_origin_clock + 1)
        )
    );

    RETURN v_event_id;
END;
$$;

-- ============================================================
-- 9. REPLICATION PROCESSING
-- ============================================================

CREATE OR REPLACE FUNCTION process_replication_queue(
    p_batch_size INTEGER DEFAULT 100
)
RETURNS INTEGER
LANGUAGE PLPGSQL
AS $$
DECLARE
    v_job RECORD;
    v_event write_events%ROWTYPE;
    v_processed INTEGER := 0;
    v_dependency_count INTEGER;
    v_policy conflict_resolution;
    v_existing_event UUID;
BEGIN
    IF p_batch_size < 1 OR p_batch_size > 10000 THEN
        RAISE EXCEPTION 'Batch size must be between 1 and 10000';
    END IF;

    FOR v_job IN
        SELECT q.queue_id, q.event_id, q.replica_id
        FROM replication_queue q
        JOIN replicas r
          ON r.replica_id = q.replica_id
        WHERE q.processed_at IS NULL
          AND r.status = 'online'
        ORDER BY q.queued_at, q.queue_id
        LIMIT p_batch_size
        FOR UPDATE OF q SKIP LOCKED
    LOOP
        SELECT *
        INTO v_event
        FROM write_events
        WHERE event_id = v_job.event_id;

        -- Causal replication must not precede its dependencies.
        SELECT COUNT(*)
        INTO v_dependency_count
        FROM causal_dependencies d
        JOIN write_events dependency
          ON dependency.event_id = d.depends_on_event_id
        WHERE d.event_id = v_event.event_id
          AND NOT EXISTS (
              SELECT 1
              FROM replica_values rv
              WHERE rv.replica_id = v_job.replica_id
                AND rv.event_id = dependency.event_id
          );

        IF v_event.consistency = 'causal'
           AND v_dependency_count > 0 THEN

            UPDATE replication_queue
            SET attempts = attempts + 1,
                last_error = 'Waiting for causal dependencies'
            WHERE queue_id = v_job.queue_id;

            CONTINUE;
        END IF;

        SELECT resolution
        INTO v_policy
        FROM consistency_policies
        WHERE model = v_event.consistency
          AND enabled = TRUE
        ORDER BY policy_id
        LIMIT 1;

        SELECT event_id
        INTO v_existing_event
        FROM replica_values
        WHERE replica_id = v_job.replica_id
          AND item_id = v_event.item_id;

        IF v_existing_event IS NULL THEN
            INSERT INTO replica_values (
                replica_id,
                item_id,
                item_value,
                version,
                origin_replica_id,
                event_id
            )
            VALUES (
                v_job.replica_id,
                v_event.item_id,
                v_event.item_value,
                v_event.logical_version,
                v_event.origin_replica_id,
                v_event.event_id
            );
        ELSE
            -- Monotonic version check prevents stale overwrites.
            UPDATE replica_values rv
            SET item_value = v_event.item_value,
                version = v_event.logical_version,
                origin_replica_id = v_event.origin_replica_id,
                event_id = v_event.event_id,
                updated_at = CURRENT_TIMESTAMP
            WHERE rv.replica_id = v_job.replica_id
              AND rv.item_id = v_event.item_id
              AND (
                  rv.version < v_event.logical_version
                  OR (
                      rv.version = v_event.logical_version
                      AND rv.event_id < v_event.event_id
                      AND v_policy = 'last_writer_wins'
                  )
              );
        END IF;

        UPDATE replication_queue
        SET processed_at = CURRENT_TIMESTAMP,
            attempts = attempts + 1,
            last_error = NULL
        WHERE queue_id = v_job.queue_id;

        INSERT INTO consistency_audit (
            event_id,
            replica_id,
            action,
            details
        )
        VALUES (
            v_event.event_id,
            v_job.replica_id,
            'REPLICATED',
            jsonb_build_object(
                'item_id', v_event.item_id,
                'version', v_event.logical_version
            )
        );

        v_processed := v_processed + 1;
    END LOOP;

    -- An event is fully committed after all target replicas
    -- have acknowledged its replication.
    UPDATE write_events e
    SET status = 'committed'
    WHERE e.status = 'pending'
      AND NOT EXISTS (
          SELECT 1
          FROM replication_queue q
          WHERE q.event_id = e.event_id
            AND q.processed_at IS NULL
      );

    RETURN v_processed;
END;
$$;

-- ============================================================
-- 10. READ SERVICE
-- ============================================================

CREATE OR REPLACE FUNCTION read_replica_value(
    p_replica_id BIGINT,
    p_item_key VARCHAR
)
RETURNS JSONB
LANGUAGE PLPGSQL
STABLE
AS $$
DECLARE
    v_value JSONB;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM replicas
        WHERE replica_id = p_replica_id
          AND status = 'online'
    ) THEN
        RAISE EXCEPTION 'Replica is unavailable';
    END IF;

    SELECT rv.item_value
    INTO v_value
    FROM replica_values rv
    JOIN data_items d
      ON d.item_id = rv.item_id
    WHERE rv.replica_id = p_replica_id
      AND d.item_key = p_item_key;

    RETURN v_value;
END;
$$;

-- ============================================================
-- 11. ELIGIBILITY AND REPORTING VIEWS
-- ============================================================

CREATE OR REPLACE VIEW replica_consistency_report AS
SELECT
    d.item_key,
    COUNT(rv.replica_id) AS replicas_with_value,
    COUNT(DISTINCT rv.item_value) AS distinct_values,
    MIN(rv.version) AS minimum_version,
    MAX(rv.version) AS maximum_version,
    COUNT(*) FILTER (
        WHERE r.status = 'online'
    ) AS online_replicas,
    COUNT(*) FILTER (
        WHERE r.status = 'offline'
    ) AS offline_replicas,
    (
        COUNT(DISTINCT rv.item_value) <= 1
        AND COUNT(rv.replica_id) = COUNT(r.replica_id)
    ) AS converged
FROM data_items d
CROSS JOIN replicas r
LEFT JOIN replica_values rv
    ON rv.item_id = d.item_id
   AND rv.replica_id = r.replica_id
GROUP BY d.item_id, d.item_key;

CREATE OR REPLACE VIEW replication_backlog AS
SELECT
    r.replica_name,
    r.status,
    COUNT(q.queue_id) AS pending_events,
    MIN(q.queued_at) AS oldest_pending_event,
    MAX(q.attempts) AS maximum_attempts
FROM replicas r
LEFT JOIN replication_queue q
    ON q.replica_id = r.replica_id
   AND q.processed_at IS NULL
GROUP BY r.replica_id, r.replica_name, r.status;

CREATE OR REPLACE VIEW consistency_event_report AS
SELECT
    e.event_id,
    d.item_key,
    origin.replica_name AS origin_replica,
    e.consistency,
    e.status,
    e.logical_version,
    e.event_timestamp,
    COUNT(q.queue_id) AS replication_targets,
    COUNT(q.queue_id) FILTER (
        WHERE q.processed_at IS NOT NULL
    ) AS completed_targets
FROM write_events e
JOIN data_items d
    ON d.item_id = e.item_id
JOIN replicas origin
    ON origin.replica_id = e.origin_replica_id
LEFT JOIN replication_queue q
    ON q.event_id = e.event_id
GROUP BY
    e.event_id,
    d.item_key,
    origin.replica_name;

-- ============================================================
-- 12. VALIDATION AND AGGREGATION QUERIES
-- ============================================================

-- Replica convergence by key.
SELECT *
FROM replica_consistency_report
ORDER BY item_key;

-- Pending replication workloads.
SELECT *
FROM replication_backlog
ORDER BY pending_events DESC;

-- Write events by consistency model.
SELECT
    consistency,
    status,
    COUNT(*) AS total_events,
    AVG(logical_version) AS average_logical_version
FROM write_events
GROUP BY consistency, status
ORDER BY consistency, status;

-- Causal dependencies.
SELECT
    child.event_id,
    parent.event_id AS dependency_event,
    child.item_id
FROM causal_dependencies dependency
JOIN write_events child
    ON child.event_id = dependency.event_id
JOIN write_events parent
    ON parent.event_id = dependency.depends_on_event_id;

-- Replicas with inconsistent values.
SELECT *
FROM replica_consistency_report
WHERE NOT converged;

-- ============================================================
-- 13. SAMPLE STRONG CONSISTENCY TRANSACTION
-- ============================================================

DO $$
DECLARE
    v_policy BIGINT;
    v_replica BIGINT;
    v_event UUID;
BEGIN
    SELECT policy_id
    INTO v_policy
    FROM consistency_policies
    WHERE policy_name = 'financial-transactions';

    SELECT replica_id
    INTO v_replica
    FROM replicas
    WHERE replica_name = 'mumbai-primary';

    v_event := create_write_event(
        v_policy,
        v_replica,
        'account:1001',
        '{"balance": 47500, "currency": "INR"}'::JSONB
    );

    RAISE NOTICE 'Strong transaction committed: %', v_event;
END;
$$;

-- ============================================================
-- 14. SAMPLE EVENTUAL CONSISTENCY TRANSACTION
-- ============================================================

DO $$
DECLARE
    v_policy BIGINT;
    v_replica BIGINT;
    v_event UUID;
BEGIN
    SELECT policy_id
    INTO v_policy
    FROM consistency_policies
    WHERE policy_name = 'product-catalog';

    SELECT replica_id
    INTO v_replica
    FROM replicas
    WHERE replica_name = 'mumbai-primary';

    v_event := create_write_event(
        v_policy,
        v_replica,
        'inventory:501',
        '{"quantity": 175}'::JSONB
    );

    RAISE NOTICE 'Eventual event accepted: %', v_event;
END;
$$;

-- ============================================================
-- 15. SAMPLE CAUSAL CONSISTENCY TRANSACTION
-- ============================================================

DO $$
DECLARE
    v_policy BIGINT;
    v_replica BIGINT;
    v_order_event UUID;
    v_payment_event UUID;
BEGIN
    SELECT policy_id
    INTO v_policy
    FROM consistency_policies
    WHERE policy_name = 'order-workflow';

    SELECT replica_id
    INTO v_replica
    FROM replicas
    WHERE replica_name = 'mumbai-primary';

    v_order_event := create_write_event(
        v_policy,
        v_replica,
        'order:9001',
        '{"status": "CONFIRMED"}'::JSONB
    );

    v_payment_event := create_write_event(
        v_policy,
        v_replica,
        'payment:9001',
        '{"status": "PAYMENT_INITIATED"}'::JSONB,
        v_order_event
    );

    RAISE NOTICE 'Order event: %', v_order_event;
    RAISE NOTICE 'Payment event: %', v_payment_event;
END;
$$;

-- ============================================================
-- 16. PROCESS REPLICATION
-- ============================================================

SELECT process_replication_queue(100);

-- ============================================================
-- 17. ELIGIBILITY AND POST-REPLICATION REPORTING
-- ============================================================

SELECT *
FROM consistency_event_report
ORDER BY event_timestamp DESC;

SELECT *
FROM replica_consistency_report
ORDER BY item_key;

SELECT *
FROM replication_backlog;

-- Read individual replica values.
SELECT
    r.replica_name,
    d.item_key,
    rv.item_value,
    rv.version,
    rv.updated_at
FROM replica_values rv
JOIN replicas r
    ON r.replica_id = rv.replica_id
JOIN data_items d
    ON d.item_id = rv.item_id
ORDER BY d.item_key, r.replica_name;

-- Audit history.
SELECT
    audit_id,
    action,
    event_id,
    replica_id,
    details,
    recorded_at
FROM consistency_audit
ORDER BY audit_id DESC;

-- ============================================================
-- 18. OFFLINE REPLICA FAILURE TEST
-- ============================================================

DO $$
DECLARE
    v_replica BIGINT;
BEGIN
    SELECT replica_id
    INTO v_replica
    FROM replicas
    WHERE replica_name = 'london-edge';

    UPDATE replicas
    SET status = 'offline'
    WHERE replica_id = v_replica;

    BEGIN
        PERFORM create_write_event(
            (
                SELECT policy_id
                FROM consistency_policies
                WHERE policy_name = 'financial-transactions'
            ),
            (
                SELECT replica_id
                FROM replicas
                WHERE replica_name = 'mumbai-primary'
            ),
            'account:1001',
            '{"balance": 45000, "currency": "INR"}'::JSONB
        );
    EXCEPTION
        WHEN OTHERS THEN
            RAISE NOTICE 'Expected strong consistency failure: %',
                SQLERRM;
    END;

    UPDATE replicas
    SET status = 'online'
    WHERE replica_id = v_replica;
END;
$$;

-- ============================================================
-- 19. CONCURRENCY AND OPERATIONAL QUERIES
-- ============================================================

-- Lock-aware queue inspection.
SELECT
    q.queue_id,
    e.event_id,
    r.replica_name,
    q.attempts,
    q.last_error,
    q.queued_at
FROM replication_queue q
JOIN write_events e
    ON e.event_id = q.event_id
JOIN replicas r
    ON r.replica_id = q.replica_id
WHERE q.processed_at IS NULL
ORDER BY q.queued_at;

-- Detect multiple unresolved values for the same key.
SELECT
    d.item_key,
    COUNT(DISTINCT rv.item_value) AS conflicting_versions
FROM data_items d
JOIN replica_values rv
    ON rv.item_id = d.item_id
GROUP BY d.item_id, d.item_key
HAVING COUNT(DISTINCT rv.item_value) > 1;

COMMIT;

-- ============================================================
-- OPERATIONAL NOTE
--
-- The script demonstrates logical replication and consistency
-- evaluation using relational tables and transactions.
--
-- Strong consistency is simulated using one PostgreSQL transaction
-- that updates all logical replicas. Real distributed strong
-- consistency requires an appropriate coordination protocol.
--
-- Eventual consistency uses a durable replication queue.
--
-- Causal consistency uses explicit event dependencies.
--
-- Production deployment would require durable retry workers,
-- idempotency controls, transaction isolation decisions,
-- conflict resolution, authentication, authorization, monitoring,
-- and actual cross-node replication.
-- ============================================================
