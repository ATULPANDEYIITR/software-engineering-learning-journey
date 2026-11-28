/*
 * DISTRIBUTED MESSAGING
 * Queues, Streams, and Delivery Guarantees
 *
 * PostgreSQL 14+
 *
 * Features:
 * - Relational message broker model
 * - Point-to-point queues
 * - Append-only partitioned event streams
 * - Consumer groups
 * - Delivery attempts and acknowledgements
 * - At-most-once and at-least-once delivery policies
 * - Idempotency and deduplication
 * - Dead-letter queues
 * - Offset management and replay
 * - Message retention
 * - Transactional publishing
 * - Operational reporting
 *
 * Run as a database owner in a dedicated development database.
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS messaging;

SET search_path TO messaging, public;


-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE delivery_guarantee AS ENUM (
    'at_most_once',
    'at_least_once',
    'exactly_once'
);

CREATE TYPE message_state AS ENUM (
    'pending',
    'in_flight',
    'acknowledged',
    'dead_lettered'
);

CREATE TYPE transport_type AS ENUM (
    'queue',
    'stream'
);

CREATE TYPE consumer_state AS ENUM (
    'active',
    'paused',
    'stopped'
);


-- ============================================================
-- 2. TOPICS AND TRANSPORT CONFIGURATION
-- ============================================================

CREATE TABLE topics (
    topic_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    topic_name VARCHAR(128) NOT NULL UNIQUE,

    transport transport_type NOT NULL,

    partition_count INTEGER NOT NULL DEFAULT 1,

    retention_seconds BIGINT NOT NULL DEFAULT 604800,

    max_message_bytes INTEGER NOT NULL DEFAULT 1000000,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_partition_count
        CHECK (partition_count BETWEEN 1 AND 1024),

    CONSTRAINT valid_retention
        CHECK (retention_seconds > 0),

    CONSTRAINT valid_message_size
        CHECK (max_message_bytes BETWEEN 1 AND 10000000),

    CONSTRAINT queue_single_partition
        CHECK (
            transport <> 'queue'
            OR partition_count = 1
        )
);


-- ============================================================
-- 3. PRODUCERS
-- ============================================================

CREATE TABLE producers (
    producer_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    producer_name VARCHAR(128) NOT NULL UNIQUE,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. CONSUMER GROUPS
-- ============================================================

CREATE TABLE consumer_groups (
    group_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    topic_id BIGINT NOT NULL REFERENCES topics(topic_id),

    group_name VARCHAR(128) NOT NULL,

    guarantee delivery_guarantee NOT NULL,

    state consumer_state NOT NULL DEFAULT 'active',

    max_retries INTEGER NOT NULL DEFAULT 3,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(topic_id, group_name),

    UNIQUE(group_id, topic_id),

    CONSTRAINT valid_retry_count
        CHECK (max_retries BETWEEN 0 AND 100)
);


-- ============================================================
-- 5. MESSAGES
-- ============================================================

CREATE TABLE messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    topic_id BIGINT NOT NULL REFERENCES topics(topic_id),

    producer_id BIGINT NOT NULL REFERENCES producers(producer_id),

    message_key VARCHAR(256) NOT NULL,

    payload JSONB NOT NULL,

    headers JSONB NOT NULL DEFAULT '{}'::jsonb,

    state message_state NOT NULL DEFAULT 'pending',

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    expires_at TIMESTAMPTZ,

    CONSTRAINT payload_must_be_object
        CHECK (jsonb_typeof(payload) = 'object'),

    CONSTRAINT headers_must_be_object
        CHECK (jsonb_typeof(headers) = 'object'),

    CONSTRAINT valid_expiration
        CHECK (expires_at IS NULL OR expires_at > created_at)
);


-- ============================================================
-- 6. QUEUE DELIVERIES
-- ============================================================

CREATE TABLE queue_deliveries (
    delivery_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    message_id UUID NOT NULL REFERENCES messages(message_id),

    consumer_group_id BIGINT NOT NULL
        REFERENCES consumer_groups(group_id),

    attempts INTEGER NOT NULL DEFAULT 0,

    state message_state NOT NULL DEFAULT 'pending',

    available_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    locked_at TIMESTAMPTZ,

    locked_by VARCHAR(128),

    acknowledged_at TIMESTAMPTZ,

    last_error TEXT,

    UNIQUE(message_id, consumer_group_id),

    CONSTRAINT valid_attempts
        CHECK (attempts >= 0),

    CONSTRAINT valid_lock_state
        CHECK (
            (state = 'in_flight' AND locked_at IS NOT NULL)
            OR
            (state <> 'in_flight' AND locked_at IS NULL)
        )
);


-- ============================================================
-- 7. EVENT STREAM PARTITIONS
-- ============================================================

CREATE TABLE stream_events (
    topic_id BIGINT NOT NULL REFERENCES topics(topic_id),

    partition_id INTEGER NOT NULL,

    event_offset BIGINT NOT NULL,

    message_id UUID NOT NULL REFERENCES messages(message_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY(topic_id, partition_id, event_offset),

    UNIQUE(topic_id, message_id),

    CONSTRAINT valid_partition
        CHECK (partition_id >= 0),

    CONSTRAINT valid_offset
        CHECK (event_offset >= 0)
);


-- ============================================================
-- 8. CONSUMER OFFSETS
-- ============================================================

CREATE TABLE consumer_offsets (
    group_id BIGINT NOT NULL REFERENCES consumer_groups(group_id),

    topic_id BIGINT NOT NULL REFERENCES topics(topic_id),

    partition_id INTEGER NOT NULL,

    committed_offset BIGINT NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY(group_id, partition_id),

    FOREIGN KEY(group_id, topic_id)
        REFERENCES consumer_groups(group_id, topic_id),

    CONSTRAINT nonnegative_offset
        CHECK (committed_offset >= 0),

    CONSTRAINT valid_offset_partition
        CHECK (partition_id >= 0)
);


-- ============================================================
-- 9. IDEMPOTENCY RECORDS
-- ============================================================

CREATE TABLE processed_messages (
    group_id BIGINT NOT NULL REFERENCES consumer_groups(group_id),

    message_id UUID NOT NULL REFERENCES messages(message_id),

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    result JSONB NOT NULL DEFAULT '{}'::jsonb,

    PRIMARY KEY(group_id, message_id)
);


-- ============================================================
-- 10. DEAD-LETTER RECORDS
-- ============================================================

CREATE TABLE dead_letter_messages (
    dead_letter_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    delivery_id BIGINT NOT NULL UNIQUE
        REFERENCES queue_deliveries(delivery_id),

    message_id UUID NOT NULL REFERENCES messages(message_id),

    failure_reason TEXT NOT NULL,

    attempts INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_dead_letter_attempts
        CHECK (attempts > 0)
);


-- ============================================================
-- 11. OPERATIONAL INDEXES
-- ============================================================

CREATE INDEX idx_messages_topic_created
    ON messages(topic_id, created_at DESC);

CREATE INDEX idx_messages_pending
    ON messages(topic_id, created_at)
    WHERE state = 'pending';

CREATE INDEX idx_queue_ready
    ON queue_deliveries(available_at, delivery_id)
    WHERE state = 'pending';

CREATE INDEX idx_queue_inflight
    ON queue_deliveries(locked_at)
    WHERE state = 'in_flight';

CREATE INDEX idx_stream_replay
    ON stream_events(topic_id, partition_id, event_offset);

CREATE INDEX idx_dead_letter_created
    ON dead_letter_messages(created_at DESC);

CREATE INDEX idx_processed_group_time
    ON processed_messages(group_id, processed_at DESC);


-- ============================================================
-- 12. MESSAGE SIZE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_message_size()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    maximum_size INTEGER;
    actual_size INTEGER;
BEGIN
    SELECT max_message_bytes
    INTO maximum_size
    FROM topics
    WHERE topic_id = NEW.topic_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Topic does not exist';
    END IF;

    actual_size := octet_length(
        convert_to(
            NEW.payload::text,
            'UTF8'
        )
    );

    IF actual_size > maximum_size THEN
        RAISE EXCEPTION
            'Message size % exceeds topic limit %',
            actual_size,
            maximum_size;
    END IF;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_validate_message_size
BEFORE INSERT OR UPDATE OF payload, topic_id
ON messages
FOR EACH ROW
EXECUTE FUNCTION validate_message_size();


-- ============================================================
-- 13. CONSUMER OFFSET INITIALIZATION
-- ============================================================

CREATE OR REPLACE FUNCTION initialize_consumer_offsets()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    partition_total INTEGER;
BEGIN
    SELECT partition_count
    INTO partition_total
    FROM topics
    WHERE topic_id = NEW.topic_id;

    INSERT INTO consumer_offsets (
        group_id,
        topic_id,
        partition_id,
        committed_offset
    )
    SELECT
        NEW.group_id,
        NEW.topic_id,
        generate_series(0, partition_total - 1),
        0;

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_initialize_offsets
AFTER INSERT ON consumer_groups
FOR EACH ROW
EXECUTE FUNCTION initialize_consumer_offsets();


-- ============================================================
-- 14. QUEUE PUBLISHING
-- ============================================================

CREATE OR REPLACE FUNCTION publish_queue_message(
    p_topic_id BIGINT,
    p_producer_id BIGINT,
    p_key VARCHAR,
    p_payload JSONB
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    new_message_id UUID;
    target_group RECORD;
BEGIN
    PERFORM 1
    FROM topics
    WHERE topic_id = p_topic_id
      AND transport = 'queue';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target is not a queue topic';
    END IF;

    PERFORM 1
    FROM producers
    WHERE producer_id = p_producer_id
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Producer is missing or disabled';
    END IF;

    INSERT INTO messages (
        topic_id,
        producer_id,
        message_key,
        payload
    )
    VALUES (
        p_topic_id,
        p_producer_id,
        p_key,
        p_payload
    )
    RETURNING message_id INTO new_message_id;

    INSERT INTO queue_deliveries (
        message_id,
        consumer_group_id
    )
    SELECT
        new_message_id,
        group_id
    FROM consumer_groups
    WHERE topic_id = p_topic_id
      AND state = 'active';

    RETURN new_message_id;
END;
$$;


-- ============================================================
-- 15. STREAM PUBLISHING
-- ============================================================

CREATE OR REPLACE FUNCTION publish_stream_event(
    p_topic_id BIGINT,
    p_producer_id BIGINT,
    p_key VARCHAR,
    p_payload JSONB
)
RETURNS TABLE (
    new_message_id UUID,
    new_partition INTEGER,
    new_offset BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    total_partitions INTEGER;
    selected_partition INTEGER;
    next_position BIGINT;
BEGIN
    SELECT partition_count
    INTO total_partitions
    FROM topics
    WHERE topic_id = p_topic_id
      AND transport = 'stream';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Target is not a stream topic';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM producers
        WHERE producer_id = p_producer_id
          AND enabled = TRUE
    ) THEN
        RAISE EXCEPTION 'Producer disabled or missing';
    END IF;

    -- A stable key maps related events to the same partition.
    selected_partition :=
        mod(
            hashtext(p_key)::bigint & 2147483647,
            total_partitions
        )::integer;

    INSERT INTO messages (
        topic_id,
        producer_id,
        message_key,
        payload
    )
    VALUES (
        p_topic_id,
        p_producer_id,
        p_key,
        p_payload
    )
    RETURNING message_id INTO new_message_id;

    -- Serialize offset allocation for the selected partition.
    PERFORM pg_advisory_xact_lock(
        p_topic_id,
        selected_partition
    );

    SELECT COALESCE(MAX(event_offset) + 1, 0)
    INTO next_position
    FROM stream_events
    WHERE topic_id = p_topic_id
      AND partition_id = selected_partition;

    INSERT INTO stream_events (
        topic_id,
        partition_id,
        event_offset,
        message_id
    )
    VALUES (
        p_topic_id,
        selected_partition,
        next_position,
        new_message_id
    );

    new_partition := selected_partition;
    new_offset := next_position;

    RETURN NEXT;
END;
$$;


-- ============================================================
-- 16. QUEUE CLAIMING
-- ============================================================

CREATE OR REPLACE FUNCTION claim_queue_message(
    p_group_id BIGINT,
    p_worker VARCHAR
)
RETURNS TABLE (
    claimed_delivery_id BIGINT,
    claimed_message_id UUID,
    claimed_payload JSONB,
    claimed_attempts INTEGER
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH selected AS (
        SELECT q.delivery_id
        FROM queue_deliveries q
        JOIN consumer_groups g
          ON g.group_id = q.consumer_group_id
        WHERE q.consumer_group_id = p_group_id
          AND q.state = 'pending'
          AND q.available_at <= NOW()
          AND g.state = 'active'
        ORDER BY q.available_at, q.delivery_id
        FOR UPDATE OF q SKIP LOCKED
        LIMIT 1
    ),
    updated AS (
        UPDATE queue_deliveries q
        SET
            state = 'in_flight',
            attempts = q.attempts + 1,
            locked_at = NOW(),
            locked_by = p_worker
        FROM selected s
        WHERE q.delivery_id = s.delivery_id
        RETURNING q.delivery_id,
                  q.message_id,
                  q.attempts
    )
    SELECT
        u.delivery_id,
        u.message_id,
        m.payload,
        u.attempts
    FROM updated u
    JOIN messages m
      ON m.message_id = u.message_id;
END;
$$;


-- ============================================================
-- 17. ACKNOWLEDGEMENT
-- ============================================================

CREATE OR REPLACE FUNCTION acknowledge_delivery(
    p_delivery_id BIGINT,
    p_worker VARCHAR
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    updated_count INTEGER;
BEGIN
    UPDATE queue_deliveries
    SET
        state = 'acknowledged',
        acknowledged_at = NOW(),
        locked_at = NULL,
        locked_by = NULL
    WHERE delivery_id = p_delivery_id
      AND state = 'in_flight'
      AND locked_by = p_worker;

    GET DIAGNOSTICS updated_count = ROW_COUNT;

    IF updated_count = 0 THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END;
$$;


-- ============================================================
-- 18. NEGATIVE ACKNOWLEDGEMENT AND DEAD-LETTER ROUTING
-- ============================================================

CREATE OR REPLACE FUNCTION reject_delivery(
    p_delivery_id BIGINT,
    p_worker VARCHAR,
    p_reason TEXT
)
RETURNS message_state
LANGUAGE plpgsql
AS $$
DECLARE
    delivery RECORD;
    maximum_retries INTEGER;
    resulting_state message_state;
BEGIN
    SELECT
        q.delivery_id,
        q.message_id,
        q.attempts,
        q.consumer_group_id,
        q.state,
        q.locked_by,
        g.max_retries
    INTO delivery
    FROM queue_deliveries q
    JOIN consumer_groups g
      ON g.group_id = q.consumer_group_id
    WHERE q.delivery_id = p_delivery_id
    FOR UPDATE OF q;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Delivery not found';
    END IF;

    IF delivery.state <> 'in_flight'
       OR delivery.locked_by <> p_worker THEN
        RAISE EXCEPTION 'Worker does not own delivery';
    END IF;

    maximum_retries := delivery.max_retries;

    IF delivery.attempts <= maximum_retries THEN

        UPDATE queue_deliveries
        SET
            state = 'pending',
            available_at = NOW() +
                LEAST(
                    300,
                    power(2, delivery.attempts)::integer
                ) * INTERVAL '1 second',
            locked_at = NULL,
            locked_by = NULL,
            last_error = p_reason
        WHERE delivery_id = p_delivery_id;

        resulting_state := 'pending';

    ELSE

        UPDATE queue_deliveries
        SET
            state = 'dead_lettered',
            locked_at = NULL,
            locked_by = NULL,
            last_error = p_reason
        WHERE delivery_id = p_delivery_id;

        UPDATE messages
        SET state = 'dead_lettered'
        WHERE message_id = delivery.message_id;

        INSERT INTO dead_letter_messages (
            delivery_id,
            message_id,
            failure_reason,
            attempts
        )
        VALUES (
            delivery.delivery_id,
            delivery.message_id,
            p_reason,
            delivery.attempts
        );

        resulting_state := 'dead_lettered';

    END IF;

    RETURN resulting_state;
END;
$$;


-- ============================================================
-- 19. STREAM OFFSET COMMIT
-- ============================================================

CREATE OR REPLACE FUNCTION commit_stream_offset(
    p_group_id BIGINT,
    p_partition INTEGER,
    p_next_offset BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    target_topic BIGINT;
    maximum_offset BIGINT;
    current_offset BIGINT;
BEGIN
    SELECT topic_id
    INTO target_topic
    FROM consumer_groups
    WHERE group_id = p_group_id
      AND state = 'active';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consumer group unavailable';
    END IF;

    PERFORM 1
    FROM consumer_offsets
    WHERE group_id = p_group_id
      AND partition_id = p_partition
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Partition offset not registered';
    END IF;

    SELECT COALESCE(MAX(event_offset) + 1, 0)
    INTO maximum_offset
    FROM stream_events
    WHERE topic_id = target_topic
      AND partition_id = p_partition;

    SELECT committed_offset
    INTO current_offset
    FROM consumer_offsets
    WHERE group_id = p_group_id
      AND partition_id = p_partition;

    IF p_next_offset < current_offset
       OR p_next_offset > maximum_offset THEN
        RAISE EXCEPTION 'Invalid offset commit';
    END IF;

    UPDATE consumer_offsets
    SET
        committed_offset = p_next_offset,
        updated_at = NOW()
    WHERE group_id = p_group_id
      AND partition_id = p_partition;

    RETURN TRUE;
END;
$$;


-- ============================================================
-- 20. IDEMPOTENT BUSINESS PROCESSING
-- ============================================================

CREATE TABLE payment_ledger (
    transaction_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    group_id BIGINT NOT NULL,

    message_id UUID NOT NULL,

    account_number VARCHAR(64) NOT NULL,

    amount NUMERIC(18, 2) NOT NULL,

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(group_id, message_id),

    FOREIGN KEY(group_id, message_id)
        REFERENCES processed_messages(group_id, message_id),

    CHECK (amount > 0)
);


CREATE OR REPLACE FUNCTION process_payment_once(
    p_group_id BIGINT,
    p_message_id UUID
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    payment JSONB;
    account VARCHAR(64);
    amount_value NUMERIC(18, 2);
    target_topic BIGINT;
BEGIN
    SELECT topic_id
    INTO target_topic
    FROM consumer_groups
    WHERE group_id = p_group_id
      AND state = 'active';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Consumer group unavailable';
    END IF;

    SELECT payload
    INTO payment
    FROM messages
    WHERE message_id = p_message_id
      AND topic_id = target_topic;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Payment message not found';
    END IF;

    account := payment->>'account';
    amount_value := (payment->>'amount')::numeric;

    IF account IS NULL OR account = '' THEN
        RAISE EXCEPTION 'Account is required';
    END IF;

    IF amount_value IS NULL OR amount_value <= 0 THEN
        RAISE EXCEPTION 'Invalid payment amount';
    END IF;

    -- The unique key provides the deduplication boundary.
    INSERT INTO processed_messages (
        group_id,
        message_id,
        result
    )
    VALUES (
        p_group_id,
        p_message_id,
        jsonb_build_object('status', 'processed')
    )
    ON CONFLICT DO NOTHING;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    INSERT INTO payment_ledger (
        group_id,
        message_id,
        account_number,
        amount
    )
    VALUES (
        p_group_id,
        p_message_id,
        account,
        amount_value
    );

    RETURN TRUE;
END;
$$;


-- ============================================================
-- 21. STREAM REPLAY VIEW
-- ============================================================

CREATE VIEW stream_replay_view AS
SELECT
    t.topic_name,
    s.partition_id,
    s.event_offset,
    m.message_id,
    m.message_key,
    m.payload,
    m.created_at
FROM stream_events s
JOIN topics t
  ON t.topic_id = s.topic_id
JOIN messages m
  ON m.message_id = s.message_id;


-- ============================================================
-- 22. QUEUE MONITORING VIEW
-- ============================================================

CREATE VIEW queue_monitoring_view AS
SELECT
    t.topic_name,
    g.group_name,
    COUNT(*) FILTER (
        WHERE q.state = 'pending'
    ) AS pending_messages,

    COUNT(*) FILTER (
        WHERE q.state = 'in_flight'
    ) AS in_flight_messages,

    COUNT(*) FILTER (
        WHERE q.state = 'acknowledged'
    ) AS acknowledged_messages,

    COUNT(*) FILTER (
        WHERE q.state = 'dead_lettered'
    ) AS dead_letter_messages,

    COALESCE(AVG(q.attempts), 0) AS average_attempts

FROM queue_deliveries q
JOIN consumer_groups g
  ON g.group_id = q.consumer_group_id
JOIN topics t
  ON t.topic_id = g.topic_id

GROUP BY
    t.topic_name,
    g.group_name;


-- ============================================================
-- 23. CONSUMER LAG VIEW
-- ============================================================

CREATE VIEW consumer_lag_view AS
SELECT
    g.group_name,
    t.topic_name,
    o.partition_id,
    o.committed_offset,

    COALESCE(MAX(s.event_offset) + 1, 0)
        AS latest_offset,

    GREATEST(
        COALESCE(MAX(s.event_offset) + 1, 0)
        - o.committed_offset,
        0
    ) AS consumer_lag

FROM consumer_offsets o

JOIN consumer_groups g
  ON g.group_id = o.group_id

JOIN topics t
  ON t.topic_id = o.topic_id

LEFT JOIN stream_events s
  ON s.topic_id = o.topic_id
 AND s.partition_id = o.partition_id

GROUP BY
    g.group_name,
    t.topic_name,
    o.partition_id,
    o.committed_offset;


-- ============================================================
-- 24. SAMPLE CONFIGURATION
-- ============================================================

INSERT INTO topics (
    topic_name,
    transport,
    partition_count,
    retention_seconds
)
VALUES
    ('payments', 'queue', 1, 604800),
    ('orders', 'stream', 3, 2592000),
    ('notifications', 'queue', 1, 86400);

INSERT INTO producers (producer_name)
VALUES
    ('payment-service'),
    ('order-service'),
    ('notification-service');

INSERT INTO consumer_groups (
    topic_id,
    group_name,
    guarantee,
    max_retries
)
SELECT
    topic_id,
    'payment-workers',
    'at_least_once',
    3
FROM topics
WHERE topic_name = 'payments';

INSERT INTO consumer_groups (
    topic_id,
    group_name,
    guarantee,
    max_retries
)
SELECT
    topic_id,
    'analytics',
    'at_least_once',
    3
FROM topics
WHERE topic_name = 'orders';

INSERT INTO consumer_groups (
    topic_id,
    group_name,
    guarantee,
    max_retries
)
SELECT
    topic_id,
    'billing',
    'exactly_once',
    3
FROM topics
WHERE topic_name = 'orders';

INSERT INTO consumer_groups (
    topic_id,
    group_name,
    guarantee,
    max_retries
)
SELECT
    topic_id,
    'notification-workers',
    'at_least_once',
    2
FROM topics
WHERE topic_name = 'notifications';


-- ============================================================
-- 25. SAMPLE QUEUE PUBLISHING
-- ============================================================

SELECT publish_queue_message(
    (SELECT topic_id FROM topics WHERE topic_name = 'payments'),
    (SELECT producer_id FROM producers WHERE producer_name = 'payment-service'),
    'ACCOUNT-100',
    '{"account":"ACCOUNT-100","amount":2500.00}'::jsonb
);

SELECT publish_queue_message(
    (SELECT topic_id FROM topics WHERE topic_name = 'payments'),
    (SELECT producer_id FROM producers WHERE producer_name = 'payment-service'),
    'ACCOUNT-200',
    '{"account":"ACCOUNT-200","amount":1500.00}'::jsonb
);


-- ============================================================
-- 26. SAMPLE STREAM PUBLISHING
-- ============================================================

SELECT *
FROM publish_stream_event(
    (SELECT topic_id FROM topics WHERE topic_name = 'orders'),
    (SELECT producer_id FROM producers WHERE producer_name = 'order-service'),
    'CUSTOMER-100',
    '{"order_id":"ORD-100","amount":5000}'::jsonb
);

SELECT *
FROM publish_stream_event(
    (SELECT topic_id FROM topics WHERE topic_name = 'orders'),
    (SELECT producer_id FROM producers WHERE producer_name = 'order-service'),
    'CUSTOMER-100',
    '{"order_id":"ORD-101","amount":7500}'::jsonb
);

SELECT *
FROM publish_stream_event(
    (SELECT topic_id FROM topics WHERE topic_name = 'orders'),
    (SELECT producer_id FROM producers WHERE producer_name = 'order-service'),
    'CUSTOMER-200',
    '{"order_id":"ORD-102","amount":3000}'::jsonb
);


-- ============================================================
-- 27. QUEUE WORKER TRANSACTION
-- ============================================================

DO $$
DECLARE
    claimed RECORD;
    worker_name VARCHAR := 'worker-01';
    target_group BIGINT;
    processed BOOLEAN;
BEGIN
    SELECT group_id
    INTO target_group
    FROM consumer_groups
    WHERE group_name = 'payment-workers';

    FOR claimed IN
        SELECT *
        FROM claim_queue_message(
            target_group,
            worker_name
        )
    LOOP

        -- Business update and acknowledgement share a transaction.
        processed := process_payment_once(
            target_group,
            claimed.claimed_message_id
        );

        IF NOT acknowledge_delivery(
            claimed.claimed_delivery_id,
            worker_name
        ) THEN
            RAISE EXCEPTION 'Acknowledgement rejected';
        END IF;

        RAISE NOTICE
            'Processed message %, new processing=%',
            claimed.claimed_message_id,
            processed;
    END LOOP;
END;
$$;


-- ============================================================
-- 28. STREAM CONSUMPTION AND OFFSET COMMIT
-- ============================================================

DO $$
DECLARE
    target_group BIGINT;
    target_topic BIGINT;
    partition_number INTEGER;
    next_position BIGINT;
    maximum_position BIGINT;
BEGIN
    SELECT group_id, topic_id
    INTO target_group, target_topic
    FROM consumer_groups
    WHERE group_name = 'analytics';

    FOR partition_number IN
        SELECT partition_id
        FROM consumer_offsets
        WHERE group_id = target_group
        ORDER BY partition_id
    LOOP

        SELECT committed_offset
        INTO next_position
        FROM consumer_offsets
        WHERE group_id = target_group
          AND partition_id = partition_number;

        SELECT COALESCE(MAX(event_offset) + 1, 0)
        INTO maximum_position
        FROM stream_events
        WHERE topic_id = target_topic
          AND partition_id = partition_number;

        -- Simulated successful batch consumption.
        PERFORM 1
        FROM stream_events
        WHERE topic_id = target_topic
          AND partition_id = partition_number
          AND event_offset >= next_position
          AND event_offset < maximum_position;

        PERFORM commit_stream_offset(
            target_group,
            partition_number,
            maximum_position
        );
    END LOOP;
END;
$$;


-- ============================================================
-- 29. FAILURE SCENARIO
-- ============================================================

SELECT publish_queue_message(
    (SELECT topic_id FROM topics WHERE topic_name = 'notifications'),
    (SELECT producer_id FROM producers WHERE producer_name = 'notification-service'),
    'USER-500',
    '{"recipient":"user500@example.com","event":"password_changed"}'::jsonb
);


-- ============================================================
-- 30. DATA RETRIEVAL
-- ============================================================

-- Queue messages.
SELECT
    m.message_id,
    m.message_key,
    m.payload,
    q.state,
    q.attempts
FROM messages m
JOIN queue_deliveries q
  ON q.message_id = m.message_id
WHERE m.topic_id = (
    SELECT topic_id
    FROM topics
    WHERE topic_name = 'payments'
)
ORDER BY m.created_at;


-- Stream events.
SELECT *
FROM stream_replay_view
WHERE topic_name = 'orders'
ORDER BY partition_id, event_offset;


-- Consumer group offsets.
SELECT
    g.group_name,
    t.topic_name,
    o.partition_id,
    o.committed_offset
FROM consumer_offsets o
JOIN consumer_groups g
  ON g.group_id = o.group_id
JOIN topics t
  ON t.topic_id = o.topic_id
ORDER BY g.group_name, o.partition_id;


-- ============================================================
-- 31. VALIDATION AND ELIGIBILITY REPORTING
-- ============================================================

-- Delivery guarantee configuration.
SELECT
    t.topic_name,
    g.group_name,
    t.transport,
    g.guarantee,
    g.max_retries,
    g.state
FROM consumer_groups g
JOIN topics t
  ON t.topic_id = g.topic_id
ORDER BY t.topic_name;


-- Consumer lag.
SELECT *
FROM consumer_lag_view
ORDER BY consumer_lag DESC;


-- Queue health.
SELECT *
FROM queue_monitoring_view
ORDER BY topic_name;


-- Dead-letter analysis.
SELECT
    t.topic_name,
    d.failure_reason,
    COUNT(*) AS failed_messages,
    MAX(d.created_at) AS latest_failure
FROM dead_letter_messages d
JOIN messages m
  ON m.message_id = d.message_id
JOIN topics t
  ON t.topic_id = m.topic_id
GROUP BY t.topic_name, d.failure_reason;


-- Payment ledger.
SELECT
    account_number,
    COUNT(*) AS transaction_count,
    SUM(amount) AS total_amount
FROM payment_ledger
GROUP BY account_number;


-- ============================================================
-- 32. RETENTION PROCESSING
-- ============================================================

CREATE OR REPLACE PROCEDURE purge_expired_messages()
LANGUAGE plpgsql
AS $$
BEGIN
    DELETE FROM messages m
    USING topics t
    WHERE m.topic_id = t.topic_id
      AND m.created_at <
          NOW() - t.retention_seconds * INTERVAL '1 second'
      AND m.expires_at IS NOT NULL
      AND m.expires_at <= NOW()
      AND NOT EXISTS (
          SELECT 1
          FROM queue_deliveries q
          WHERE q.message_id = m.message_id
            AND q.state IN ('pending', 'in_flight')
      )
      AND NOT EXISTS (
          SELECT 1
          FROM stream_events s
          WHERE s.message_id = m.message_id
      );
END;
$$;


-- ============================================================
-- 33. TRANSACTIONAL CONSISTENCY CHECKS
-- ============================================================

-- A message can only be claimed by one worker at a time.
-- FOR UPDATE SKIP LOCKED supports competing queue workers.
--
-- An acknowledgement is accepted only from the worker holding
-- the current delivery lock.
--
-- Stream offsets are independent for every consumer group.
--
-- Unique(group_id, message_id) prevents duplicate business
-- processing when the idempotency operation is transactional.
--
-- The sample schema is a learning broker model, not a replacement
-- for a distributed broker with replicated durable storage.

COMMIT;
