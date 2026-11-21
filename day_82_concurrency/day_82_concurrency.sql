/*
===============================================================================
CONCURRENCY, RACE CONDITIONS, LOCKS, AND SYNCHRONIZATION
PostgreSQL 17+ compatible relational implementation.

Demonstrates:
1. Shared database state
2. Transaction isolation
3. Lost-update prevention
4. Row-level locking
5. SELECT FOR UPDATE
6. NOWAIT and SKIP LOCKED
7. Optimistic concurrency using version numbers
8. Atomic conditional updates
9. Advisory locks
10. Deadlock detection and prevention
11. Transactional producer-consumer processing
12. Concurrency auditing
13. Integrity constraints
14. Reporting and performance indexes

Execute the complete script in a dedicated learning database.
===============================================================================
*/

-- ============================================================================
-- 1. SCHEMA
-- ============================================================================

DROP SCHEMA IF EXISTS concurrency_lab CASCADE;

CREATE SCHEMA concurrency_lab;

SET search_path TO concurrency_lab, public;


-- ============================================================================
-- 2. DOMAIN TABLES
-- ============================================================================

CREATE TABLE resources (
    resource_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_code VARCHAR(40) NOT NULL UNIQUE,
    resource_name VARCHAR(150) NOT NULL,
    available_quantity INTEGER NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT resource_quantity_nonnegative
        CHECK (available_quantity >= 0),

    CONSTRAINT resource_version_nonnegative
        CHECK (version >= 0)
);


CREATE TABLE reservations (
    reservation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id BIGINT NOT NULL REFERENCES resources(resource_id),
    request_reference VARCHAR(80) NOT NULL UNIQUE,
    requested_quantity INTEGER NOT NULL,
    reservation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    CONSTRAINT reservation_quantity_positive
        CHECK (requested_quantity > 0),

    CONSTRAINT reservation_status_valid
        CHECK (
            reservation_status IN (
                'PENDING',
                'CONFIRMED',
                'REJECTED',
                'CANCELLED'
            )
        )
);


CREATE TABLE workers (
    worker_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    worker_name VARCHAR(100) NOT NULL,
    worker_status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',

    CONSTRAINT worker_status_valid
        CHECK (worker_status IN ('ACTIVE', 'INACTIVE'))
);


CREATE TABLE task_queue (
    task_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_type VARCHAR(80) NOT NULL,
    payload JSONB NOT NULL,
    task_status VARCHAR(20) NOT NULL DEFAULT 'READY',
    assigned_worker_id BIGINT REFERENCES workers(worker_id),
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    claimed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    CONSTRAINT task_status_valid
        CHECK (
            task_status IN (
                'READY',
                'PROCESSING',
                'COMPLETED',
                'FAILED'
            )
        ),

    CONSTRAINT task_attempts_nonnegative
        CHECK (attempts >= 0)
);


CREATE TABLE concurrency_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id BIGINT REFERENCES resources(resource_id),
    reservation_id BIGINT REFERENCES reservations(reservation_id),
    event_type VARCHAR(50) NOT NULL,
    event_details JSONB NOT NULL DEFAULT '{}'::JSONB,
    transaction_id BIGINT NOT NULL DEFAULT txid_current(),
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================================
-- 3. PERFORMANCE INDEXES
-- ============================================================================

CREATE INDEX idx_reservations_resource_status
    ON reservations(resource_id, reservation_status);

CREATE INDEX idx_reservations_created
    ON reservations(created_at DESC);

CREATE INDEX idx_task_queue_ready
    ON task_queue(created_at, task_id)
    WHERE task_status = 'READY';

CREATE INDEX idx_task_queue_worker
    ON task_queue(assigned_worker_id, task_status);

CREATE INDEX idx_concurrency_events_resource
    ON concurrency_events(resource_id, event_time DESC);


-- ============================================================================
-- 4. SAMPLE DATA
-- ============================================================================

INSERT INTO resources (
    resource_code,
    resource_name,
    available_quantity
)
VALUES
    ('LAPTOP-001', 'Enterprise Laptop', 20),
    ('MOUSE-001', 'Wireless Mouse', 100),
    ('KEYBOARD-001', 'Mechanical Keyboard', 50),
    ('SERVER-001', 'Compute Server', 5);


INSERT INTO workers(worker_name)
VALUES
    ('Worker Alpha'),
    ('Worker Beta'),
    ('Worker Gamma');


INSERT INTO reservations (
    resource_id,
    request_reference,
    requested_quantity
)
SELECT
    resource_id,
    'REQ-INITIAL-' || resource_code,
    2
FROM resources
WHERE resource_code IN ('LAPTOP-001', 'MOUSE-001');


INSERT INTO task_queue(task_type, payload)
VALUES
    ('INVENTORY_AUDIT', '{"resource":"LAPTOP-001"}'),
    ('INVENTORY_AUDIT', '{"resource":"MOUSE-001"}'),
    ('REPORT_GENERATION', '{"report":"daily"}'),
    ('DATA_VALIDATION', '{"dataset":"inventory"}');


-- ============================================================================
-- 5. RESOURCE UPDATE AUDIT
-- ============================================================================

CREATE OR REPLACE FUNCTION audit_resource_update()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;

    NEW.version := OLD.version + 1;

    IF NEW.available_quantity < 0 THEN
        RAISE EXCEPTION
            'Resource quantity cannot become negative';
    END IF;

    INSERT INTO concurrency_events (
        resource_id,
        event_type,
        event_details
    )
    VALUES (
        OLD.resource_id,
        'RESOURCE_UPDATED',
        jsonb_build_object(
            'old_quantity', OLD.available_quantity,
            'new_quantity', NEW.available_quantity,
            'old_version', OLD.version,
            'new_version', NEW.version
        )
    );

    RETURN NEW;
END;
$$;


CREATE TRIGGER trg_resource_update
BEFORE UPDATE ON resources
FOR EACH ROW
EXECUTE FUNCTION audit_resource_update();


-- ============================================================================
-- 6. SAFE ATOMIC RESERVATION
-- ============================================================================

CREATE OR REPLACE FUNCTION reserve_resource(
    p_resource_code VARCHAR,
    p_reference VARCHAR,
    p_quantity INTEGER
)
RETURNS TABLE (
    result_status VARCHAR,
    resulting_quantity INTEGER,
    resulting_version BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_resource_id BIGINT;
    v_quantity INTEGER;
    v_version BIGINT;
BEGIN
    IF p_quantity IS NULL OR p_quantity <= 0 THEN
        RAISE EXCEPTION 'Reservation quantity must be positive';
    END IF;

    IF p_reference IS NULL OR length(trim(p_reference)) = 0 THEN
        RAISE EXCEPTION 'Request reference cannot be empty';
    END IF;

    /*
       Atomic conditional UPDATE.

       PostgreSQL locks the matching row during the update.
       Concurrent updates to the same resource cannot independently
       consume the same available quantity.

       The WHERE condition is rechecked against the current row
       after waiting for a concurrent updater.
    */

    UPDATE resources
    SET available_quantity = available_quantity - p_quantity
    WHERE resource_code = p_resource_code
      AND available_quantity >= p_quantity
    RETURNING
        resource_id,
        resources.available_quantity,
        resources.version
    INTO
        v_resource_id,
        v_quantity,
        v_version;

    IF NOT FOUND THEN
        IF NOT EXISTS (
            SELECT 1
            FROM resources
            WHERE resource_code = p_resource_code
        ) THEN
            RAISE EXCEPTION 'Unknown resource: %', p_resource_code;
        END IF;

        RETURN QUERY
        SELECT
            'REJECTED'::VARCHAR,
            NULL::INTEGER,
            NULL::BIGINT;

        RETURN;
    END IF;

    INSERT INTO reservations (
        resource_id,
        request_reference,
        requested_quantity,
        reservation_status,
        completed_at
    )
    VALUES (
        v_resource_id,
        p_reference,
        p_quantity,
        'CONFIRMED',
        CURRENT_TIMESTAMP
    );

    INSERT INTO concurrency_events (
        resource_id,
        event_type,
        event_details
    )
    VALUES (
        v_resource_id,
        'RESERVATION_CONFIRMED',
        jsonb_build_object(
            'reference', p_reference,
            'quantity', p_quantity
        )
    );

    RETURN QUERY
    SELECT
        'CONFIRMED'::VARCHAR,
        v_quantity,
        v_version;
END;
$$;


-- ============================================================================
-- 7. OPTIMISTIC CONCURRENCY CONTROL
-- ============================================================================

CREATE OR REPLACE FUNCTION update_resource_optimistically(
    p_resource_code VARCHAR,
    p_expected_version BIGINT,
    p_new_quantity INTEGER
)
RETURNS TABLE (
    update_status VARCHAR,
    current_version BIGINT,
    current_quantity INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_version BIGINT;
    v_quantity INTEGER;
BEGIN
    IF p_new_quantity < 0 THEN
        RAISE EXCEPTION 'Quantity cannot be negative';
    END IF;

    /*
       Compare-and-update.

       The version predicate ensures that an update based on an
       outdated snapshot cannot overwrite a newer committed update.
    */

    UPDATE resources
    SET available_quantity = p_new_quantity
    WHERE resource_code = p_resource_code
      AND version = p_expected_version
    RETURNING version, available_quantity
    INTO v_version, v_quantity;

    IF FOUND THEN
        RETURN QUERY
        SELECT
            'UPDATED'::VARCHAR,
            v_version,
            v_quantity;

        RETURN;
    END IF;

    SELECT version, available_quantity
    INTO v_version, v_quantity
    FROM resources
    WHERE resource_code = p_resource_code;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Resource not found';
    END IF;

    RETURN QUERY
    SELECT
        'CONFLICT'::VARCHAR,
        v_version,
        v_quantity;
END;
$$;


-- ============================================================================
-- 8. PESSIMISTIC LOCKING
-- ============================================================================

CREATE OR REPLACE FUNCTION inspect_resource_with_lock(
    p_resource_code VARCHAR
)
RETURNS TABLE (
    resource_code VARCHAR,
    quantity INTEGER,
    current_version BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    /*
       FOR UPDATE obtains a row-level lock.

       Other transactions attempting conflicting updates or
       FOR UPDATE locks must wait until this transaction ends.
    */

    RETURN QUERY
    SELECT
        r.resource_code,
        r.available_quantity,
        r.version
    FROM resources r
    WHERE r.resource_code = p_resource_code
    FOR UPDATE;
END;
$$;


-- ============================================================================
-- 9. TASK CLAIMING WITH SKIP LOCKED
-- ============================================================================

CREATE OR REPLACE FUNCTION claim_next_task(
    p_worker_id BIGINT
)
RETURNS TABLE (
    claimed_task_id BIGINT,
    claimed_task_type VARCHAR,
    claimed_payload JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_task_id BIGINT;
    v_task_type VARCHAR;
    v_payload JSONB;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM workers
        WHERE worker_id = p_worker_id
          AND worker_status = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'Worker is not active';
    END IF;

    /*
       SKIP LOCKED prevents workers from waiting for tasks
       already claimed by other workers.

       The claim and state transition occur in one transaction.
    */

    SELECT
        t.task_id,
        t.task_type,
        t.payload
    INTO
        v_task_id,
        v_task_type,
        v_payload
    FROM task_queue t
    WHERE t.task_status = 'READY'
    ORDER BY t.created_at, t.task_id
    LIMIT 1
    FOR UPDATE SKIP LOCKED;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    UPDATE task_queue
    SET
        task_status = 'PROCESSING',
        assigned_worker_id = p_worker_id,
        claimed_at = CURRENT_TIMESTAMP,
        attempts = attempts + 1
    WHERE task_id = v_task_id;

    RETURN QUERY
    SELECT v_task_id, v_task_type, v_payload;
END;
$$;


-- ============================================================================
-- 10. COMPLETE A CLAIMED TASK
-- ============================================================================

CREATE OR REPLACE FUNCTION complete_task(
    p_task_id BIGINT,
    p_worker_id BIGINT,
    p_success BOOLEAN
)
RETURNS VARCHAR
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR;
BEGIN
    UPDATE task_queue
    SET
        task_status = CASE
            WHEN p_success THEN 'COMPLETED'
            ELSE 'FAILED'
        END,
        completed_at = CURRENT_TIMESTAMP
    WHERE task_id = p_task_id
      AND assigned_worker_id = p_worker_id
      AND task_status = 'PROCESSING'
    RETURNING task_status
    INTO v_status;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Task is not assigned to this worker or is not processing';
    END IF;

    RETURN v_status;
END;
$$;


-- ============================================================================
-- 11. ADVISORY LOCK DEMONSTRATION
-- ============================================================================

CREATE OR REPLACE FUNCTION acquire_resource_advisory_lock(
    p_resource_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    /*
       Transaction-level advisory lock.

       The application defines the meaning of the integer lock key.
       It is separate from ordinary table-row locking.
    */

    RETURN pg_try_advisory_xact_lock(
        91001,
        p_resource_id::INTEGER
    );
END;
$$;


-- ============================================================================
-- 12. ELIGIBILITY AND REPORTING VIEWS
-- ============================================================================

CREATE OR REPLACE VIEW resource_availability_report AS
SELECT
    r.resource_id,
    r.resource_code,
    r.resource_name,
    r.available_quantity,
    r.version,
    COUNT(res.reservation_id) FILTER (
        WHERE res.reservation_status = 'CONFIRMED'
    ) AS confirmed_reservations,
    COALESCE(
        SUM(res.requested_quantity) FILTER (
            WHERE res.reservation_status = 'CONFIRMED'
        ),
        0
    ) AS total_reserved
FROM resources r
LEFT JOIN reservations res
    ON res.resource_id = r.resource_id
GROUP BY
    r.resource_id,
    r.resource_code,
    r.resource_name,
    r.available_quantity,
    r.version;


CREATE OR REPLACE VIEW concurrency_workload_report AS
SELECT
    task_status,
    COUNT(*) AS task_count,
    AVG(attempts)::NUMERIC(10,2) AS average_attempts
FROM task_queue
GROUP BY task_status;


-- ============================================================================
-- 13. RESERVATION ELIGIBILITY
-- ============================================================================

CREATE OR REPLACE FUNCTION check_reservation_eligibility(
    p_resource_code VARCHAR,
    p_quantity INTEGER
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT,
    available INTEGER
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        CASE
            WHEN p_quantity IS NULL OR p_quantity <= 0 THEN FALSE
            WHEN r.resource_id IS NULL THEN FALSE
            WHEN r.available_quantity >= p_quantity THEN TRUE
            ELSE FALSE
        END,
        CASE
            WHEN p_quantity IS NULL OR p_quantity <= 0
                THEN 'Invalid requested quantity'
            WHEN r.resource_id IS NULL
                THEN 'Resource does not exist'
            WHEN r.available_quantity >= p_quantity
                THEN 'Eligible'
            ELSE 'Insufficient available quantity'
        END,
        r.available_quantity
    FROM (SELECT 1) input
    LEFT JOIN resources r
        ON r.resource_code = p_resource_code;
$$;


-- ============================================================================
-- 14. TRANSACTIONAL EXECUTION EXAMPLES
-- ============================================================================

/*
   Example A: Safe reservation.

   The function's atomic UPDATE and reservation insertion execute
   within the caller's transaction.
*/

BEGIN;

SELECT *
FROM reserve_resource(
    'LAPTOP-001',
    'REQ-2026-001',
    2
);

COMMIT;


/*
   Example B: Failed reservation.

   A rejected reservation does not reduce stock.
*/

BEGIN;

SELECT *
FROM reserve_resource(
    'SERVER-001',
    'REQ-2026-002',
    100
);

COMMIT;


/*
   Example C: Optimistic update.

   The expected version must match the current version.
*/

BEGIN;

SELECT
    resource_code,
    version,
    available_quantity
FROM resources
WHERE resource_code = 'MOUSE-001';

-- Supply the version read by the application.
SELECT *
FROM update_resource_optimistically(
    'MOUSE-001',
    0,
    95
);

COMMIT;


/*
   Example D: Row-level lock.

   The lock remains held until COMMIT or ROLLBACK.
*/

BEGIN;

SELECT *
FROM inspect_resource_with_lock('KEYBOARD-001');

COMMIT;


/*
   Example E: Advisory lock.

   The transaction-level lock is released automatically
   when the transaction completes.
*/

BEGIN;

SELECT acquire_resource_advisory_lock(1);

COMMIT;


/*
   Example F: Claim a task.

   In concurrent sessions, SKIP LOCKED allows different workers
   to claim different READY tasks.
*/

BEGIN;

SELECT *
FROM claim_next_task(1);

COMMIT;


/*
   Example G: Complete an assigned task.

   Use a task ID returned by claim_next_task.
*/

-- SELECT complete_task(1, 1, TRUE);


/*
   Example H: Explicit transaction rollback.

   The attempted update is discarded.
*/

BEGIN;

UPDATE resources
SET available_quantity = available_quantity + 100
WHERE resource_code = 'LAPTOP-001';

ROLLBACK;


-- ============================================================================
-- 15. RETRIEVAL AND VALIDATION QUERIES
-- ============================================================================

-- Current resource state.
SELECT *
FROM resources
ORDER BY resource_code;


-- Confirmed reservations.
SELECT
    request_reference,
    resource_code,
    requested_quantity,
    reservation_status,
    created_at
FROM reservations
JOIN resources USING (resource_id)
WHERE reservation_status = 'CONFIRMED'
ORDER BY created_at DESC;


-- Eligibility evaluation.
SELECT *
FROM check_reservation_eligibility('MOUSE-001', 10);


-- Invalid eligibility evaluation.
SELECT *
FROM check_reservation_eligibility('SERVER-001', 100);


-- Version conflicts and updates.
SELECT
    resource_code,
    available_quantity,
    version
FROM resources
WHERE version > 0;


-- Resource aggregation.
SELECT *
FROM resource_availability_report
ORDER BY total_reserved DESC;


-- Task workload aggregation.
SELECT *
FROM concurrency_workload_report;


-- Event history.
SELECT
    event_id,
    event_type,
    event_details,
    transaction_id,
    event_time
FROM concurrency_events
ORDER BY event_time DESC;


-- ============================================================================
-- 16. CTE-BASED CONCURRENCY ANALYSIS
-- ============================================================================

WITH reservation_totals AS (
    SELECT
        resource_id,
        COUNT(*) AS reservation_count,
        SUM(requested_quantity) AS total_requested
    FROM reservations
    WHERE reservation_status = 'CONFIRMED'
    GROUP BY resource_id
),
resource_analysis AS (
    SELECT
        r.resource_code,
        r.available_quantity,
        COALESCE(rt.reservation_count, 0) AS reservation_count,
        COALESCE(rt.total_requested, 0) AS total_requested
    FROM resources r
    LEFT JOIN reservation_totals rt
        ON rt.resource_id = r.resource_id
)
SELECT
    resource_code,
    available_quantity,
    reservation_count,
    total_requested,
    CASE
        WHEN available_quantity = 0 THEN 'EXHAUSTED'
        WHEN available_quantity < 10 THEN 'LOW_STOCK'
        ELSE 'AVAILABLE'
    END AS resource_state
FROM resource_analysis
ORDER BY total_requested DESC;


-- ============================================================================
-- 17. TRANSACTION ISOLATION INFORMATION
-- ============================================================================

SELECT
    current_setting('transaction_isolation') AS isolation_level,
    current_setting('default_transaction_isolation')
        AS default_isolation_level;


-- ============================================================================
-- 18. DEADLOCK AND LOCK INSPECTION
-- ============================================================================

/*
   Deadlock scenario to reproduce in TWO separate sessions:

   Session A:
       BEGIN;
       UPDATE resources
       SET available_quantity = available_quantity - 1
       WHERE resource_code = 'LAPTOP-001';

       UPDATE resources
       SET available_quantity = available_quantity - 1
       WHERE resource_code = 'MOUSE-001';

   Session B:
       BEGIN;
       UPDATE resources
       SET available_quantity = available_quantity - 1
       WHERE resource_code = 'MOUSE-001';

       UPDATE resources
       SET available_quantity = available_quantity - 1
       WHERE resource_code = 'LAPTOP-001';

   If each session holds one lock while waiting for the other,
   PostgreSQL detects the deadlock and aborts one transaction.

   Prevention:
   Acquire resources in a consistent order, for example by
   ascending resource_id, or lock all required rows in one
   deterministically ordered operation.
*/

SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    query
FROM pg_stat_activity
WHERE datname = current_database()
  AND pid <> pg_backend_pid();


SELECT
    locktype,
    relation::REGCLASS AS relation_name,
    mode,
    granted,
    pid
FROM pg_locks
WHERE pid <> pg_backend_pid()
ORDER BY relation_name, pid;


-- ============================================================================
-- 19. PERFORMANCE ANALYSIS
-- ============================================================================

EXPLAIN (ANALYZE, BUFFERS)
SELECT task_id, task_type
FROM task_queue
WHERE task_status = 'READY'
ORDER BY created_at, task_id
LIMIT 1;


EXPLAIN (ANALYZE, BUFFERS)
SELECT *
FROM reservations
WHERE resource_id = 1
  AND reservation_status = 'CONFIRMED';


-- ============================================================================
-- 20. DATABASE CONCURRENCY PRINCIPLES
-- ============================================================================

/*
   ATOMIC UPDATE:
   Prevents competing transactions from independently consuming
   the same resource quantity.

   FOR UPDATE:
   Acquires pessimistic row-level locks.

   SKIP LOCKED:
   Enables concurrent workers to claim separate available tasks.

   NOWAIT:
   Can be used with FOR UPDATE NOWAIT when waiting is unacceptable.
   A conflicting lock causes an immediate error.

   VERSION CHECK:
   Rejects updates based on stale application snapshots.

   ADVISORY LOCK:
   Coordinates application-defined logical resources.

   TRANSACTION ISOLATION:
   Determines which concurrent transaction effects are visible.

   DEADLOCK DETECTION:
   PostgreSQL detects circular lock dependencies and aborts
   one participating transaction.

   IMPORTANT:
   A database transaction is not automatically a distributed
   transaction. External side effects require separate reliability
   mechanisms such as idempotency keys and transactional outbox
   processing.
*/

-- End of concurrency laboratory.
