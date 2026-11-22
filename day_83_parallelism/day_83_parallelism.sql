-- ============================================================
-- PARALLELISM: MULTITHREADING AND MULTIPROCESSING
-- PostgreSQL 15+
--
-- Database model for a distributed parallel task-processing
-- platform.
--
-- Models:
-- 1. Compute clusters and worker processes.
-- 2. Workloads and execution tasks.
-- 3. Worker leases and task ownership.
-- 4. Concurrent task claiming.
-- 5. Retry handling and failure isolation.
-- 6. Worker heartbeats.
-- 7. Execution events and audit history.
-- 8. Resource limits and scheduling policies.
-- 9. Performance aggregation and reporting.
-- 10. Transaction-safe completion.
--
-- Important distinction:
-- PostgreSQL background parallel query execution is different
-- from application-managed worker processes and threads.
-- This schema models the latter.
--
-- Run using a PostgreSQL database with permission to create
-- schemas, tables, functions, and triggers.
-- ============================================================


-- ============================================================
-- 1. SCHEMA
-- ============================================================

DROP SCHEMA IF EXISTS parallel_lab CASCADE;

CREATE SCHEMA parallel_lab;

SET search_path TO parallel_lab, public;


-- ============================================================
-- 2. ENUM TYPES
-- ============================================================

CREATE TYPE worker_status AS ENUM (
    'ONLINE',
    'BUSY',
    'OFFLINE',
    'DRAINING'
);

CREATE TYPE execution_status AS ENUM (
    'QUEUED',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'CANCELLED'
);

CREATE TYPE execution_mode AS ENUM (
    'SEQUENTIAL',
    'MULTITHREADING',
    'MULTIPROCESSING',
    'DISTRIBUTED'
);

CREATE TYPE workload_type AS ENUM (
    'CPU_BOUND',
    'IO_BOUND',
    'MEMORY_BOUND',
    'MIXED'
);

CREATE TYPE event_type AS ENUM (
    'SUBMITTED',
    'CLAIMED',
    'STARTED',
    'HEARTBEAT',
    'COMPLETED',
    'FAILED',
    'RETRIED',
    'CANCELLED',
    'LEASE_EXPIRED'
);


-- ============================================================
-- 3. COMPUTE CLUSTERS
-- ============================================================

CREATE TABLE compute_clusters (
    cluster_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_name VARCHAR(100) NOT NULL UNIQUE,

    description TEXT,

    maximum_workers INTEGER NOT NULL DEFAULT 4,

    maximum_concurrent_tasks INTEGER NOT NULL DEFAULT 20,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT positive_maximum_workers
        CHECK (maximum_workers > 0),

    CONSTRAINT positive_maximum_tasks
        CHECK (maximum_concurrent_tasks > 0)
);


-- ============================================================
-- 4. WORKER REGISTRY
-- ============================================================

CREATE TABLE workers (
    worker_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    cluster_id BIGINT NOT NULL
        REFERENCES compute_clusters(cluster_id),

    worker_name VARCHAR(100) NOT NULL,

    execution_mode execution_mode NOT NULL,

    status worker_status NOT NULL DEFAULT 'ONLINE',

    cpu_cores INTEGER NOT NULL DEFAULT 1,

    memory_limit_mb INTEGER NOT NULL DEFAULT 1024,

    maximum_tasks INTEGER NOT NULL DEFAULT 1,

    active_tasks INTEGER NOT NULL DEFAULT 0,

    last_heartbeat TIMESTAMPTZ,

    registered_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_worker_name
        UNIQUE(cluster_id, worker_name),

    CONSTRAINT positive_cpu_cores
        CHECK (cpu_cores > 0),

    CONSTRAINT positive_memory
        CHECK (memory_limit_mb > 0),

    CONSTRAINT positive_maximum_tasks
        CHECK (maximum_tasks > 0),

    CONSTRAINT valid_active_tasks
        CHECK (
            active_tasks >= 0
            AND active_tasks <= maximum_tasks
        )
);

CREATE INDEX idx_workers_available
    ON workers(cluster_id, status)
    WHERE status = 'ONLINE';


-- ============================================================
-- 5. WORKLOAD DEFINITIONS
-- ============================================================

CREATE TABLE workloads (
    workload_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    workload_name VARCHAR(150) NOT NULL,

    workload_type workload_type NOT NULL,

    execution_mode execution_mode NOT NULL,

    priority INTEGER NOT NULL DEFAULT 5,

    expected_duration_ms BIGINT,

    required_memory_mb INTEGER NOT NULL DEFAULT 128,

    required_cpu_cores INTEGER NOT NULL DEFAULT 1,

    submitted_by VARCHAR(100) NOT NULL,

    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_priority
        CHECK (priority BETWEEN 1 AND 10),

    CONSTRAINT positive_expected_duration
        CHECK (
            expected_duration_ms IS NULL
            OR expected_duration_ms > 0
        ),

    CONSTRAINT positive_required_memory
        CHECK (required_memory_mb > 0),

    CONSTRAINT positive_required_cpu
        CHECK (required_cpu_cores > 0)
);


-- ============================================================
-- 6. TASK EXECUTION TABLE
-- ============================================================

CREATE TABLE execution_tasks (
    task_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    workload_id BIGINT NOT NULL
        REFERENCES workloads(workload_id),

    task_name VARCHAR(150) NOT NULL,

    task_sequence INTEGER NOT NULL,

    status execution_status NOT NULL DEFAULT 'QUEUED',

    assigned_worker_id BIGINT
        REFERENCES workers(worker_id),

    input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,

    output_payload JSONB,

    attempt_count INTEGER NOT NULL DEFAULT 0,

    maximum_attempts INTEGER NOT NULL DEFAULT 3,

    available_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    lease_expires_at TIMESTAMPTZ,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    duration_ms BIGINT,

    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_workload_sequence
        UNIQUE(workload_id, task_sequence),

    CONSTRAINT valid_attempt_count
        CHECK (
            attempt_count >= 0
            AND maximum_attempts > 0
            AND attempt_count <= maximum_attempts
        ),

    CONSTRAINT valid_duration
        CHECK (
            duration_ms IS NULL
            OR duration_ms >= 0
        ),

    CONSTRAINT valid_task_assignment
        CHECK (
            (status = 'RUNNING' AND assigned_worker_id IS NOT NULL)
            OR
            (status <> 'RUNNING' AND assigned_worker_id IS NULL)
        ),

    CONSTRAINT valid_lease
        CHECK (
            (status = 'RUNNING' AND lease_expires_at IS NOT NULL)
            OR
            (status <> 'RUNNING' AND lease_expires_at IS NULL)
        ),

    CONSTRAINT valid_completion
        CHECK (
            (status = 'COMPLETED'
                AND completed_at IS NOT NULL
                AND output_payload IS NOT NULL)
            OR
            (status <> 'COMPLETED')
        )
);

-- Queue retrieval benefits from priority and submission ordering.
CREATE INDEX idx_execution_queue
    ON execution_tasks(
        available_at,
        created_at,
        task_id
    )
    WHERE status = 'QUEUED';

CREATE INDEX idx_execution_workload
    ON execution_tasks(workload_id, status);

CREATE INDEX idx_execution_worker
    ON execution_tasks(assigned_worker_id)
    WHERE status = 'RUNNING';

CREATE INDEX idx_expired_leases
    ON execution_tasks(lease_expires_at)
    WHERE status = 'RUNNING';


-- ============================================================
-- 7. EXECUTION EVENT AUDIT
-- ============================================================

CREATE TABLE execution_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    task_id BIGINT NOT NULL
        REFERENCES execution_tasks(task_id),

    worker_id BIGINT
        REFERENCES workers(worker_id),

    event event_type NOT NULL,

    event_details JSONB NOT NULL DEFAULT '{}'::jsonb,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_execution_events_task
    ON execution_events(task_id, occurred_at DESC);


-- ============================================================
-- 8. EVENT LOGGING FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION log_execution_event(
    p_task_id BIGINT,
    p_worker_id BIGINT,
    p_event event_type,
    p_details JSONB DEFAULT '{}'::jsonb
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO execution_events (
        task_id,
        worker_id,
        event,
        event_details
    )
    VALUES (
        p_task_id,
        p_worker_id,
        p_event,
        COALESCE(p_details, '{}'::jsonb)
    );
END;
$$;


-- ============================================================
-- 9. TASK SUBMISSION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION submit_task(
    p_workload_id BIGINT,
    p_task_name VARCHAR,
    p_sequence INTEGER,
    p_payload JSONB DEFAULT '{}'::jsonb,
    p_maximum_attempts INTEGER DEFAULT 3
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_task_id BIGINT;
BEGIN
    IF p_sequence < 1 THEN
        RAISE EXCEPTION 'Task sequence must be positive';
    END IF;

    IF p_maximum_attempts < 1
       OR p_maximum_attempts > 10 THEN
        RAISE EXCEPTION 'Invalid maximum attempt count';
    END IF;

    PERFORM 1
    FROM workloads
    WHERE workload_id = p_workload_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Workload % does not exist',
            p_workload_id;
    END IF;

    INSERT INTO execution_tasks (
        workload_id,
        task_name,
        task_sequence,
        input_payload,
        maximum_attempts
    )
    VALUES (
        p_workload_id,
        p_task_name,
        p_sequence,
        COALESCE(p_payload, '{}'::jsonb),
        p_maximum_attempts
    )
    RETURNING task_id INTO v_task_id;

    PERFORM log_execution_event(
        v_task_id,
        NULL,
        'SUBMITTED',
        jsonb_build_object(
            'task_name', p_task_name,
            'sequence', p_sequence
        )
    );

    RETURN v_task_id;
END;
$$;


-- ============================================================
-- 10. WORKER CAPACITY TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION enforce_worker_capacity()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.status = 'RUNNING'
       AND NEW.assigned_worker_id IS NOT NULL THEN

        PERFORM 1
        FROM workers
        WHERE worker_id = NEW.assigned_worker_id
          AND (
              status = 'ONLINE'
              OR status = 'BUSY'
          )
          AND active_tasks < maximum_tasks
        FOR UPDATE;

        IF NOT FOUND THEN
            RAISE EXCEPTION
                'Worker is unavailable or has no capacity';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_enforce_worker_capacity
BEFORE INSERT OR UPDATE OF
    status,
    assigned_worker_id
ON execution_tasks
FOR EACH ROW
EXECUTE FUNCTION enforce_worker_capacity();


-- ============================================================
-- 11. TASK STATE AND WORKER CAPACITY TRIGGER
-- ============================================================

CREATE OR REPLACE FUNCTION synchronize_task_state()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_old_worker BIGINT;
    v_new_worker BIGINT;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF OLD.status IN (
            'COMPLETED',
            'CANCELLED'
        ) AND NEW.status <> OLD.status THEN

            RAISE EXCEPTION
                'Terminal task state cannot be changed';
        END IF;

        IF OLD.status = 'FAILED'
           AND NEW.status NOT IN ('FAILED', 'QUEUED') THEN

            RAISE EXCEPTION
                'Failed task must be requeued before execution';
        END IF;

        IF NEW.status = 'QUEUED'
           AND NEW.assigned_worker_id IS NOT NULL THEN

            RAISE EXCEPTION
                'Queued task cannot have an assigned worker';
        END IF;

        IF OLD.status = 'RUNNING'
           AND NEW.status = 'COMPLETED'
           AND NEW.completed_at IS NULL THEN

            NEW.completed_at := CURRENT_TIMESTAMP;
        END IF;

        v_old_worker := OLD.assigned_worker_id;
    END IF;

    v_new_worker := NEW.assigned_worker_id;

    IF TG_OP = 'INSERT' THEN
        v_old_worker := NULL;
    END IF;

    IF v_old_worker IS DISTINCT FROM v_new_worker
       OR (
           TG_OP = 'UPDATE'
           AND OLD.status IS DISTINCT FROM NEW.status
       ) THEN

        IF v_old_worker IS NOT NULL THEN

            UPDATE workers
            SET active_tasks = active_tasks - 1,
                status = CASE
                    WHEN status = 'BUSY'
                         AND active_tasks <= 1
                    THEN 'ONLINE'::worker_status
                    ELSE status
                END
            WHERE worker_id = v_old_worker;

        END IF;

        IF v_new_worker IS NOT NULL THEN

            UPDATE workers
            SET active_tasks = active_tasks + 1,
                status = CASE
                    WHEN active_tasks + 1 >= maximum_tasks
                    THEN 'BUSY'::worker_status
                    ELSE 'BUSY'::worker_status
                END
            WHERE worker_id = v_new_worker;

        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_synchronize_task_state
BEFORE INSERT OR UPDATE
ON execution_tasks
FOR EACH ROW
EXECUTE FUNCTION synchronize_task_state();


-- ============================================================
-- 12. TASK CLAIMING
-- ============================================================

CREATE OR REPLACE FUNCTION claim_next_task(
    p_worker_id BIGINT,
    p_lease_seconds INTEGER DEFAULT 60
)
RETURNS TABLE (
    claimed_task_id BIGINT,
    claimed_task_name VARCHAR,
    claimed_payload JSONB
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_task execution_tasks%ROWTYPE;
    v_worker workers%ROWTYPE;
BEGIN
    IF p_lease_seconds < 5 OR p_lease_seconds > 3600 THEN
        RAISE EXCEPTION 'Lease duration must be 5 to 3600 seconds';
    END IF;

    SELECT *
    INTO v_worker
    FROM workers
    WHERE worker_id = p_worker_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Worker does not exist';
    END IF;

    IF v_worker.status NOT IN ('ONLINE', 'BUSY') THEN
        RAISE EXCEPTION 'Worker is not available';
    END IF;

    IF v_worker.active_tasks >= v_worker.maximum_tasks THEN
        RETURN;
    END IF;

    SELECT t.*
    INTO v_task
    FROM execution_tasks t
    JOIN workloads w
      ON w.workload_id = t.workload_id
    WHERE t.status = 'QUEUED'
      AND t.available_at <= CURRENT_TIMESTAMP
      AND t.attempt_count < t.maximum_attempts
      AND w.required_memory_mb <= v_worker.memory_limit_mb
      AND w.required_cpu_cores <= v_worker.cpu_cores
    ORDER BY
        w.priority DESC,
        t.available_at,
        t.created_at,
        t.task_id
    FOR UPDATE OF t SKIP LOCKED
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    UPDATE execution_tasks
    SET status = 'RUNNING',
        assigned_worker_id = p_worker_id,
        attempt_count = attempt_count + 1,
        started_at = CURRENT_TIMESTAMP,
        completed_at = NULL,
        lease_expires_at =
            CURRENT_TIMESTAMP
            + make_interval(secs => p_lease_seconds),
        duration_ms = NULL,
        error_message = NULL,
        output_payload = NULL
    WHERE task_id = v_task.task_id;

    PERFORM log_execution_event(
        v_task.task_id,
        p_worker_id,
        'CLAIMED',
        jsonb_build_object(
            'attempt', v_task.attempt_count + 1,
            'lease_seconds', p_lease_seconds
        )
    );

    RETURN QUERY
    SELECT
        v_task.task_id,
        v_task.task_name,
        v_task.input_payload;
END;
$$;


-- ============================================================
-- 13. WORKER HEARTBEAT
-- ============================================================

CREATE OR REPLACE FUNCTION update_worker_heartbeat(
    p_worker_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE workers
    SET last_heartbeat = CURRENT_TIMESTAMP
    WHERE worker_id = p_worker_id
      AND status IN ('ONLINE', 'BUSY');

    RETURN FOUND;
END;
$$;


-- ============================================================
-- 14. TASK COMPLETION
-- ============================================================

CREATE OR REPLACE FUNCTION complete_task(
    p_task_id BIGINT,
    p_worker_id BIGINT,
    p_output JSONB,
    p_duration_ms BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_task execution_tasks%ROWTYPE;
BEGIN
    IF p_duration_ms < 0 THEN
        RAISE EXCEPTION 'Duration cannot be negative';
    END IF;

    SELECT *
    INTO v_task
    FROM execution_tasks
    WHERE task_id = p_task_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Task does not exist';
    END IF;

    IF v_task.status <> 'RUNNING'
       OR v_task.assigned_worker_id <> p_worker_id THEN

        RAISE EXCEPTION
            'Worker does not own the running task';
    END IF;

    IF v_task.lease_expires_at < CURRENT_TIMESTAMP THEN
        RAISE EXCEPTION 'Task execution lease has expired';
    END IF;

    UPDATE execution_tasks
    SET status = 'COMPLETED',
        output_payload = COALESCE(p_output, '{}'::jsonb),
        duration_ms = p_duration_ms,
        completed_at = CURRENT_TIMESTAMP,
        assigned_worker_id = NULL,
        lease_expires_at = NULL
    WHERE task_id = p_task_id;

    PERFORM log_execution_event(
        p_task_id,
        p_worker_id,
        'COMPLETED',
        jsonb_build_object(
            'duration_ms', p_duration_ms
        )
    );
END;
$$;


-- ============================================================
-- 15. FAILURE AND RETRY HANDLING
-- ============================================================

CREATE OR REPLACE FUNCTION fail_task(
    p_task_id BIGINT,
    p_worker_id BIGINT,
    p_error TEXT
)
RETURNS execution_status
LANGUAGE plpgsql
AS $$
DECLARE
    v_task execution_tasks%ROWTYPE;
    v_new_status execution_status;
BEGIN
    SELECT *
    INTO v_task
    FROM execution_tasks
    WHERE task_id = p_task_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Task does not exist';
    END IF;

    IF v_task.status <> 'RUNNING'
       OR v_task.assigned_worker_id <> p_worker_id THEN

        RAISE EXCEPTION 'Worker does not own this task';
    END IF;

    IF v_task.attempt_count < v_task.maximum_attempts THEN
        v_new_status := 'QUEUED';
    ELSE
        v_new_status := 'FAILED';
    END IF;

    UPDATE execution_tasks
    SET status = v_new_status,
        assigned_worker_id = NULL,
        lease_expires_at = NULL,
        started_at = NULL,
        available_at = CASE
            WHEN v_new_status = 'QUEUED'
            THEN CURRENT_TIMESTAMP
                 + make_interval(
                     secs => LEAST(
                         300,
                         5 * power(2, v_task.attempt_count - 1)::INTEGER
                     )
                 )
            ELSE available_at
        END,
        error_message = LEFT(p_error, 2000)
    WHERE task_id = p_task_id;

    PERFORM log_execution_event(
        p_task_id,
        p_worker_id,
        CASE
            WHEN v_new_status = 'QUEUED'
            THEN 'RETRIED'::event_type
            ELSE 'FAILED'::event_type
        END,
        jsonb_build_object(
            'error', LEFT(p_error, 500),
            'next_status', v_new_status
        )
    );

    RETURN v_new_status;
END;
$$;


-- ============================================================
-- 16. EXPIRED LEASE RECOVERY
-- ============================================================

CREATE OR REPLACE FUNCTION recover_expired_tasks()
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_count INTEGER;
BEGIN
    WITH expired AS (
        SELECT
            task_id,
            assigned_worker_id,
            attempt_count,
            maximum_attempts
        FROM execution_tasks
        WHERE status = 'RUNNING'
          AND lease_expires_at < CURRENT_TIMESTAMP
        FOR UPDATE SKIP LOCKED
    ),
    recovered AS (
        UPDATE execution_tasks t
        SET status = CASE
                WHEN e.attempt_count < e.maximum_attempts
                THEN 'QUEUED'::execution_status
                ELSE 'FAILED'::execution_status
            END,
            assigned_worker_id = NULL,
            lease_expires_at = NULL,
            started_at = NULL,
            available_at = CURRENT_TIMESTAMP,
            error_message = 'Execution lease expired'
        FROM expired e
        WHERE t.task_id = e.task_id
        RETURNING
            t.task_id,
            e.assigned_worker_id,
            t.status
    )
    INSERT INTO execution_events (
        task_id,
        worker_id,
        event,
        event_details
    )
    SELECT
        task_id,
        assigned_worker_id,
        'LEASE_EXPIRED',
        jsonb_build_object(
            'recovered_status', status
        )
    FROM recovered;

    GET DIAGNOSTICS v_count = ROW_COUNT;

    RETURN v_count;
END;
$$;


-- ============================================================
-- 17. WORKER REGISTRATION
-- ============================================================

INSERT INTO compute_clusters (
    cluster_name,
    description,
    maximum_workers,
    maximum_concurrent_tasks
)
VALUES
(
    'cpu-cluster',
    'CPU-intensive parallel processing cluster',
    8,
    40
),
(
    'io-cluster',
    'Asynchronous I/O workload cluster',
    6,
    30
);


INSERT INTO workers (
    cluster_id,
    worker_name,
    execution_mode,
    status,
    cpu_cores,
    memory_limit_mb,
    maximum_tasks
)
VALUES
(
    1,
    'cpu-worker-01',
    'MULTIPROCESSING',
    'ONLINE',
    8,
    8192,
    4
),
(
    1,
    'cpu-worker-02',
    'MULTIPROCESSING',
    'ONLINE',
    4,
    4096,
    2
),
(
    2,
    'io-worker-01',
    'MULTITHREADING',
    'ONLINE',
    4,
    4096,
    6
);


-- ============================================================
-- 18. WORKLOAD REGISTRATION
-- ============================================================

INSERT INTO workloads (
    workload_name,
    workload_type,
    execution_mode,
    priority,
    expected_duration_ms,
    required_memory_mb,
    required_cpu_cores,
    submitted_by
)
VALUES
(
    'Prime Number Benchmark',
    'CPU_BOUND',
    'MULTIPROCESSING',
    9,
    5000,
    1024,
    2,
    'research-team'
),
(
    'Network Data Collection',
    'IO_BOUND',
    'MULTITHREADING',
    7,
    2000,
    256,
    1,
    'operations-team'
),
(
    'Memory Intensive Aggregation',
    'MEMORY_BOUND',
    'DISTRIBUTED',
    5,
    10000,
    12000,
    2,
    'analytics-team'
);


-- ============================================================
-- 19. TASK SUBMISSION
-- ============================================================

SELECT submit_task(
    1,
    'Prime range 1',
    1,
    '{"start": 2, "end": 50000}'::jsonb,
    3
);

SELECT submit_task(
    1,
    'Prime range 2',
    2,
    '{"start": 50001, "end": 100000}'::jsonb,
    3
);

SELECT submit_task(
    1,
    'Prime range 3',
    3,
    '{"start": 100001, "end": 150000}'::jsonb,
    3
);

SELECT submit_task(
    2,
    'Network request batch 1',
    1,
    '{"requests": 100}'::jsonb,
    3
);

SELECT submit_task(
    2,
    'Network request batch 2',
    2,
    '{"requests": 200}'::jsonb,
    3
);


-- ============================================================
-- 20. RETRIEVAL: AVAILABLE WORKERS
-- ============================================================

SELECT
    w.worker_id,
    w.worker_name,
    w.execution_mode,
    w.cpu_cores,
    w.memory_limit_mb,
    w.maximum_tasks,
    w.active_tasks,
    w.status
FROM workers w
WHERE w.status IN ('ONLINE', 'BUSY')
  AND w.active_tasks < w.maximum_tasks
ORDER BY w.worker_name;


-- ============================================================
-- 21. WORKFLOW PROCESSING
--
-- In production, each worker claims tasks in its own database
-- transaction and commits immediately after claiming.
--
-- FOR UPDATE SKIP LOCKED prevents two workers from claiming
-- the same queued task.
-- ============================================================

BEGIN;

SELECT *
FROM claim_next_task(1, 60);

COMMIT;


-- ============================================================
-- 22. COMPLETE A CLAIMED TASK
--
-- The demonstration identifies the task through its current
-- assignment rather than assuming a fixed identity value.
-- ============================================================

DO $$
DECLARE
    v_task_id BIGINT;
BEGIN
    SELECT task_id
    INTO v_task_id
    FROM execution_tasks
    WHERE assigned_worker_id = 1
      AND status = 'RUNNING'
    ORDER BY task_id
    LIMIT 1;

    IF v_task_id IS NOT NULL THEN
        PERFORM complete_task(
            v_task_id,
            1,
            '{"prime_count": 5133}'::jsonb,
            1500
        );
    END IF;
END;
$$;


-- ============================================================
-- 23. RETRY DEMONSTRATION
-- ============================================================

BEGIN;

SELECT *
FROM claim_next_task(2, 60);

COMMIT;

DO $$
DECLARE
    v_task_id BIGINT;
BEGIN
    SELECT task_id
    INTO v_task_id
    FROM execution_tasks
    WHERE assigned_worker_id = 2
      AND status = 'RUNNING'
    ORDER BY task_id
    LIMIT 1;

    IF v_task_id IS NOT NULL THEN
        PERFORM fail_task(
            v_task_id,
            2,
            'Simulated worker computation failure'
        );
    END IF;
END;
$$;


-- ============================================================
-- 24. VALIDATION QUERIES
-- ============================================================

-- Invalid worker capacity is rejected by CHECK constraints.
-- Invalid task states are rejected by state constraints.

SELECT
    task_id,
    task_name,
    status,
    attempt_count,
    maximum_attempts,
    error_message
FROM execution_tasks
ORDER BY task_id;


-- Detect queued tasks that have exceeded their retry limit.
SELECT
    task_id,
    task_name,
    attempt_count,
    maximum_attempts
FROM execution_tasks
WHERE status = 'QUEUED'
  AND attempt_count >= maximum_attempts;


-- Identify workers with inconsistent heartbeat activity.
SELECT
    worker_id,
    worker_name,
    status,
    last_heartbeat
FROM workers
WHERE last_heartbeat IS NULL
   OR last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '5 minutes';


-- ============================================================
-- 25. AGGREGATION: WORKLOAD PERFORMANCE
-- ============================================================

SELECT
    w.workload_id,
    w.workload_name,
    w.workload_type,
    COUNT(t.task_id) AS total_tasks,

    COUNT(*) FILTER (
        WHERE t.status = 'COMPLETED'
    ) AS completed_tasks,

    COUNT(*) FILTER (
        WHERE t.status = 'FAILED'
    ) AS failed_tasks,

    COUNT(*) FILTER (
        WHERE t.status = 'QUEUED'
    ) AS queued_tasks,

    COUNT(*) FILTER (
        WHERE t.status = 'RUNNING'
    ) AS running_tasks,

    ROUND(
        AVG(t.duration_ms) FILTER (
            WHERE t.status = 'COMPLETED'
        ),
        2
    ) AS average_duration_ms,

    MAX(t.duration_ms) AS maximum_duration_ms

FROM workloads w
LEFT JOIN execution_tasks t
    ON t.workload_id = w.workload_id

GROUP BY
    w.workload_id,
    w.workload_name,
    w.workload_type

ORDER BY w.priority DESC;


-- ============================================================
-- 26. WORKER UTILIZATION
-- ============================================================

CREATE OR REPLACE VIEW worker_utilization AS
SELECT
    w.worker_id,
    w.worker_name,
    w.execution_mode,
    w.cpu_cores,
    w.memory_limit_mb,
    w.maximum_tasks,
    w.active_tasks,

    ROUND(
        100.0 * w.active_tasks
        / NULLIF(w.maximum_tasks, 0),
        2
    ) AS task_capacity_percentage,

    w.status,
    w.last_heartbeat

FROM workers w;


SELECT *
FROM worker_utilization
ORDER BY task_capacity_percentage DESC;


-- ============================================================
-- 27. EXECUTION MODE COMPARISON
-- ============================================================

SELECT
    wl.execution_mode,
    wl.workload_type,
    COUNT(DISTINCT wl.workload_id) AS workloads,
    COUNT(t.task_id) AS total_tasks,

    ROUND(
        AVG(t.duration_ms) FILTER (
            WHERE t.status = 'COMPLETED'
        ),
        2
    ) AS average_duration_ms,

    SUM(t.duration_ms) FILTER (
        WHERE t.status = 'COMPLETED'
    ) AS total_execution_ms

FROM workloads wl
LEFT JOIN execution_tasks t
    ON t.workload_id = wl.workload_id

GROUP BY
    wl.execution_mode,
    wl.workload_type

ORDER BY wl.execution_mode;


-- ============================================================
-- 28. EVENT AUDIT REPORT
-- ============================================================

SELECT
    e.event_id,
    e.task_id,
    t.task_name,
    e.worker_id,
    e.event,
    e.event_details,
    e.occurred_at
FROM execution_events e
JOIN execution_tasks t
    ON t.task_id = e.task_id
ORDER BY e.occurred_at DESC;


-- ============================================================
-- 29. ELIGIBILITY DETERMINATION
--
-- Determines whether a worker can execute a queued workload.
-- This is a scheduling decision, not a task assignment.
-- ============================================================

CREATE OR REPLACE FUNCTION worker_is_eligible(
    p_worker_id BIGINT,
    p_workload_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
    v_eligible BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM workers wr
        JOIN workloads wl
            ON wl.workload_id = p_workload_id
        WHERE wr.worker_id = p_worker_id
          AND wr.status IN ('ONLINE', 'BUSY')
          AND wr.active_tasks < wr.maximum_tasks
          AND wr.memory_limit_mb >= wl.required_memory_mb
          AND wr.cpu_cores >= wl.required_cpu_cores
          AND (
              wl.execution_mode = wr.execution_mode
              OR wl.execution_mode = 'DISTRIBUTED'
          )
    )
    INTO v_eligible;

    RETURN v_eligible;
END;
$$;


SELECT
    wr.worker_name,
    wl.workload_name,
    worker_is_eligible(
        wr.worker_id,
        wl.workload_id
    ) AS eligible
FROM workers wr
CROSS JOIN workloads wl
ORDER BY wr.worker_id, wl.workload_id;


-- ============================================================
-- 30. ELIGIBLE WORKER REPORT
-- ============================================================

CREATE OR REPLACE VIEW eligible_worker_report AS
SELECT
    t.task_id,
    t.task_name,
    wl.workload_name,
    wr.worker_id,
    wr.worker_name,
    wr.cpu_cores,
    wr.memory_limit_mb,
    wr.active_tasks,
    wr.maximum_tasks

FROM execution_tasks t

JOIN workloads wl
    ON wl.workload_id = t.workload_id

CROSS JOIN workers wr

WHERE t.status = 'QUEUED'
  AND wr.status IN ('ONLINE', 'BUSY')
  AND wr.active_tasks < wr.maximum_tasks
  AND wr.memory_limit_mb >= wl.required_memory_mb
  AND wr.cpu_cores >= wl.required_cpu_cores
  AND (
      wl.execution_mode = wr.execution_mode
      OR wl.execution_mode = 'DISTRIBUTED'
  );


SELECT *
FROM eligible_worker_report
ORDER BY task_id, worker_id;


-- ============================================================
-- 31. QUEUE HEALTH REPORT
-- ============================================================

SELECT
    COUNT(*) FILTER (
        WHERE status = 'QUEUED'
    ) AS queued,

    COUNT(*) FILTER (
        WHERE status = 'RUNNING'
    ) AS running,

    COUNT(*) FILTER (
        WHERE status = 'COMPLETED'
    ) AS completed,

    COUNT(*) FILTER (
        WHERE status = 'FAILED'
    ) AS failed,

    COUNT(*) FILTER (
        WHERE status = 'CANCELLED'
    ) AS cancelled,

    COUNT(*) FILTER (
        WHERE status = 'QUEUED'
          AND available_at < CURRENT_TIMESTAMP - INTERVAL '5 minutes'
    ) AS delayed_queue_tasks

FROM execution_tasks;


-- ============================================================
-- 32. CTE-BASED RETRY ANALYSIS
-- ============================================================

WITH task_attempts AS (
    SELECT
        task_id,
        workload_id,
        attempt_count,
        maximum_attempts,
        status
    FROM execution_tasks
),
retry_statistics AS (
    SELECT
        workload_id,
        COUNT(*) AS task_count,

        AVG(attempt_count) AS average_attempts,

        COUNT(*) FILTER (
            WHERE attempt_count > 1
        ) AS retried_tasks,

        COUNT(*) FILTER (
            WHERE status = 'FAILED'
        ) AS permanently_failed_tasks

    FROM task_attempts
    GROUP BY workload_id
)
SELECT
    wl.workload_name,
    rs.task_count,
    ROUND(rs.average_attempts, 2) AS average_attempts,
    rs.retried_tasks,
    rs.permanently_failed_tasks
FROM retry_statistics rs
JOIN workloads wl
    ON wl.workload_id = rs.workload_id
ORDER BY wl.workload_name;


-- ============================================================
-- 33. TRANSACTIONAL CANCELLATION
-- ============================================================

CREATE OR REPLACE FUNCTION cancel_queued_task(
    p_task_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_task execution_tasks%ROWTYPE;
BEGIN
    SELECT *
    INTO v_task
    FROM execution_tasks
    WHERE task_id = p_task_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    IF v_task.status <> 'QUEUED' THEN
        RETURN FALSE;
    END IF;

    UPDATE execution_tasks
    SET status = 'CANCELLED'
    WHERE task_id = p_task_id;

    PERFORM log_execution_event(
        p_task_id,
        NULL,
        'CANCELLED',
        '{"reason": "Administrative cancellation"}'::jsonb
    );

    RETURN TRUE;
END;
$$;


-- ============================================================
-- 34. PERFORMANCE AND OPERATIONAL NOTES
-- ============================================================

-- Inspect query plans:
EXPLAIN (ANALYZE, BUFFERS)
SELECT task_id, task_name
FROM execution_tasks
WHERE status = 'QUEUED'
  AND available_at <= CURRENT_TIMESTAMP
ORDER BY available_at, created_at, task_id
LIMIT 10;


-- ============================================================
-- 35. FINAL DATABASE STATE
-- ============================================================

SELECT
    'Clusters' AS entity,
    COUNT(*) AS total
FROM compute_clusters

UNION ALL

SELECT
    'Workers',
    COUNT(*)
FROM workers

UNION ALL

SELECT
    'Workloads',
    COUNT(*)
FROM workloads

UNION ALL

SELECT
    'Execution tasks',
    COUNT(*)
FROM execution_tasks

UNION ALL

SELECT
    'Execution events',
    COUNT(*)
FROM execution_events;
