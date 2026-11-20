/*
===============================================================================
OPERATING SYSTEMS: RELATIONAL RESOURCE MANAGEMENT SIMULATOR
===============================================================================

PostgreSQL 14+

Models:
- Operating system instances.
- Processes and process lifecycle.
- Threads and CPU execution.
- Scheduling runs and execution slices.
- Physical memory allocations.
- Virtual pages and page faults.
- Files, directories, ownership, and permissions.
- Filesystem operations and audit records.
- Process resource accounting.
- Operational reporting.

The database represents an educational OS resource-management model.
It does not replace kernel memory management, hardware page tables,
filesystem drivers, or operating-system synchronization primitives.

The script is transactional and safe to execute repeatedly.
===============================================================================
*/

BEGIN;

CREATE SCHEMA IF NOT EXISTS os_lab;

SET search_path TO os_lab, public;

DROP VIEW IF EXISTS process_resource_report CASCADE;
DROP VIEW IF EXISTS memory_utilization CASCADE;
DROP VIEW IF EXISTS scheduling_report CASCADE;
DROP VIEW IF EXISTS filesystem_report CASCADE;

DROP PROCEDURE IF EXISTS terminate_process(BIGINT, INTEGER);
DROP PROCEDURE IF EXISTS allocate_memory(BIGINT, BIGINT);
DROP PROCEDURE IF EXISTS release_memory(BIGINT);

DROP FUNCTION IF EXISTS check_process_eligibility(BIGINT);
DROP FUNCTION IF EXISTS record_page_access(BIGINT, INTEGER);
DROP FUNCTION IF EXISTS enforce_process_state_transition();
DROP FUNCTION IF EXISTS validate_file_permission();

DROP TABLE IF EXISTS filesystem_audit CASCADE;
DROP TABLE IF EXISTS file_permissions CASCADE;
DROP TABLE IF EXISTS files CASCADE;
DROP TABLE IF EXISTS directories CASCADE;
DROP TABLE IF EXISTS page_accesses CASCADE;
DROP TABLE IF EXISTS virtual_pages CASCADE;
DROP TABLE IF EXISTS memory_allocations CASCADE;
DROP TABLE IF EXISTS execution_slices CASCADE;
DROP TABLE IF EXISTS scheduling_runs CASCADE;
DROP TABLE IF EXISTS threads CASCADE;
DROP TABLE IF EXISTS processes CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS operating_systems CASCADE;

-- ---------------------------------------------------------------------------
-- 1. OPERATING SYSTEM INSTANCES
-- ---------------------------------------------------------------------------

CREATE TABLE operating_systems (
    os_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    hostname VARCHAR(100) NOT NULL UNIQUE,

    architecture VARCHAR(20) NOT NULL
        CHECK (architecture IN ('x86_64', 'ARM64', 'RISCV64')),

    total_memory_mb BIGINT NOT NULL
        CHECK (total_memory_mb > 0),

    cpu_cores INTEGER NOT NULL
        CHECK (cpu_cores > 0),

    page_size_bytes INTEGER NOT NULL DEFAULT 4096
        CHECK (page_size_bytes > 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- 2. USERS
-- ---------------------------------------------------------------------------

CREATE TABLE users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL REFERENCES operating_systems(os_id),

    username VARCHAR(100) NOT NULL,

    role VARCHAR(20) NOT NULL
        CHECK (role IN ('ADMIN', 'OPERATOR', 'AUDITOR', 'USER')),

    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (os_id, username),
    UNIQUE (user_id, os_id)
);

-- ---------------------------------------------------------------------------
-- 3. PROCESSES
-- ---------------------------------------------------------------------------

CREATE TABLE processes (
    process_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL REFERENCES operating_systems(os_id),

    parent_process_id BIGINT REFERENCES processes(process_id),

    owner_id BIGINT NOT NULL,

    process_name VARCHAR(120) NOT NULL,

    state VARCHAR(20) NOT NULL DEFAULT 'READY'
        CHECK (
            state IN (
                'NEW',
                'READY',
                'RUNNING',
                'BLOCKED',
                'TERMINATED'
            )
        ),

    memory_requested_mb BIGINT NOT NULL
        CHECK (memory_requested_mb > 0),

    memory_allocated_mb BIGINT NOT NULL DEFAULT 0
        CHECK (
            memory_allocated_mb >= 0
            AND memory_allocated_mb <= memory_requested_mb
        ),

    priority INTEGER NOT NULL DEFAULT 5
        CHECK (priority BETWEEN 0 AND 10),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    terminated_at TIMESTAMPTZ,

    exit_code INTEGER,

    FOREIGN KEY (owner_id, os_id)
        REFERENCES users(user_id, os_id),

    CHECK (
        (state = 'TERMINATED' AND terminated_at IS NOT NULL)
        OR
        (state <> 'TERMINATED' AND terminated_at IS NULL)
    )
);

CREATE INDEX idx_process_os_state
    ON processes(os_id, state);

CREATE INDEX idx_process_parent
    ON processes(parent_process_id)
    WHERE parent_process_id IS NOT NULL;

CREATE INDEX idx_process_owner
    ON processes(owner_id, created_at DESC);

-- Process state transitions are checked centrally.
CREATE FUNCTION enforce_process_state_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.state = 'TERMINATED'
       AND NEW.state <> 'TERMINATED' THEN
        RAISE EXCEPTION
            'A terminated process cannot be restarted through a state update';
    END IF;

    IF NEW.state = 'TERMINATED' THEN
        NEW.terminated_at := COALESCE(
            NEW.terminated_at,
            CURRENT_TIMESTAMP
        );
    ELSE
        NEW.terminated_at := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_process_state_transition
BEFORE UPDATE OF state ON processes
FOR EACH ROW
EXECUTE FUNCTION enforce_process_state_transition();

-- ---------------------------------------------------------------------------
-- 4. THREADS
-- ---------------------------------------------------------------------------

CREATE TABLE threads (
    thread_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    process_id BIGINT NOT NULL
        REFERENCES processes(process_id),

    thread_name VARCHAR(120) NOT NULL,

    state VARCHAR(20) NOT NULL DEFAULT 'READY'
        CHECK (
            state IN (
                'READY',
                'RUNNING',
                'BLOCKED',
                'TERMINATED'
            )
        ),

    burst_time_ms INTEGER NOT NULL
        CHECK (burst_time_ms > 0),

    remaining_time_ms INTEGER NOT NULL
        CHECK (
            remaining_time_ms >= 0
            AND remaining_time_ms <= burst_time_ms
        ),

    cpu_time_ms BIGINT NOT NULL DEFAULT 0
        CHECK (cpu_time_ms >= 0),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (process_id, thread_name)
);

CREATE INDEX idx_threads_process_state
    ON threads(process_id, state);

CREATE INDEX idx_threads_ready
    ON threads(state, thread_id)
    WHERE state = 'READY';

-- ---------------------------------------------------------------------------
-- 5. CPU SCHEDULING
-- ---------------------------------------------------------------------------

CREATE TABLE scheduling_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL
        REFERENCES operating_systems(os_id),

    algorithm VARCHAR(30) NOT NULL
        CHECK (
            algorithm IN (
                'ROUND_ROBIN',
                'FCFS',
                'PRIORITY',
                'SHORTEST_JOB'
            )
        ),

    quantum_ms INTEGER
        CHECK (quantum_ms > 0),

    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    completed_at TIMESTAMPTZ,

    CHECK (
        completed_at IS NULL
        OR completed_at >= started_at
    )
);

CREATE TABLE execution_slices (
    slice_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES scheduling_runs(run_id),

    thread_id BIGINT NOT NULL
        REFERENCES threads(thread_id),

    sequence_number INTEGER NOT NULL
        CHECK (sequence_number > 0),

    start_time_ms BIGINT NOT NULL
        CHECK (start_time_ms >= 0),

    duration_ms INTEGER NOT NULL
        CHECK (duration_ms > 0),

    remaining_time_ms INTEGER NOT NULL
        CHECK (remaining_time_ms >= 0),

    UNIQUE (run_id, sequence_number)
);

CREATE INDEX idx_execution_thread
    ON execution_slices(thread_id, run_id);

-- ---------------------------------------------------------------------------
-- 6. PHYSICAL MEMORY
-- ---------------------------------------------------------------------------

CREATE TABLE memory_allocations (
    allocation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL
        REFERENCES operating_systems(os_id),

    process_id BIGINT NOT NULL
        REFERENCES processes(process_id),

    start_address BIGINT NOT NULL
        CHECK (start_address >= 0),

    size_mb BIGINT NOT NULL
        CHECK (size_mb > 0),

    allocated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    released_at TIMESTAMPTZ,

    CHECK (
        released_at IS NULL
        OR released_at >= allocated_at
    )
);

-- Prevent a process from receiving multiple simultaneous allocation records.
CREATE UNIQUE INDEX uq_active_process_allocation
    ON memory_allocations(process_id)
    WHERE released_at IS NULL;

CREATE INDEX idx_memory_os_active
    ON memory_allocations(os_id, start_address)
    WHERE released_at IS NULL;

-- Prevent overlapping active physical memory regions.
ALTER TABLE memory_allocations
ADD CONSTRAINT unique_active_memory_start
UNIQUE (os_id, start_address, released_at);

-- ---------------------------------------------------------------------------
-- 7. VIRTUAL MEMORY
-- ---------------------------------------------------------------------------

CREATE TABLE virtual_pages (
    page_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    process_id BIGINT NOT NULL
        REFERENCES processes(process_id),

    virtual_page_number INTEGER NOT NULL
        CHECK (virtual_page_number >= 0),

    physical_frame_number INTEGER
        CHECK (
            physical_frame_number IS NULL
            OR physical_frame_number >= 0
        ),

    present BOOLEAN NOT NULL DEFAULT FALSE,

    dirty BOOLEAN NOT NULL DEFAULT FALSE,

    last_accessed_at TIMESTAMPTZ,

    UNIQUE (process_id, virtual_page_number),

    CHECK (
        (present = TRUE AND physical_frame_number IS NOT NULL)
        OR
        (present = FALSE AND physical_frame_number IS NULL)
    )
);

CREATE INDEX idx_virtual_pages_resident
    ON virtual_pages(process_id, physical_frame_number)
    WHERE present = TRUE;

CREATE TABLE page_accesses (
    access_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    page_id BIGINT NOT NULL
        REFERENCES virtual_pages(page_id),

    accessed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    access_type VARCHAR(10) NOT NULL
        CHECK (access_type IN ('READ', 'WRITE')),

    page_fault BOOLEAN NOT NULL,

    duration_us INTEGER NOT NULL DEFAULT 0
        CHECK (duration_us >= 0)
);

CREATE INDEX idx_page_access_history
    ON page_accesses(page_id, accessed_at DESC);

-- ---------------------------------------------------------------------------
-- 8. FILESYSTEM
-- ---------------------------------------------------------------------------

CREATE TABLE directories (
    directory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL
        REFERENCES operating_systems(os_id),

    parent_directory_id BIGINT
        REFERENCES directories(directory_id),

    directory_name VARCHAR(120) NOT NULL,

    owner_id BIGINT NOT NULL
        REFERENCES users(user_id),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (directory_id, os_id),

    UNIQUE NULLS NOT DISTINCT (
        os_id,
        parent_directory_id,
        directory_name
    ),

    CHECK (directory_name <> '')
);

CREATE TABLE files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    os_id BIGINT NOT NULL
        REFERENCES operating_systems(os_id),

    directory_id BIGINT NOT NULL,

    file_name VARCHAR(255) NOT NULL,

    owner_id BIGINT NOT NULL
        REFERENCES users(user_id),

    content TEXT NOT NULL DEFAULT '',

    file_size_bytes BIGINT NOT NULL DEFAULT 0
        CHECK (file_size_bytes >= 0),

    inode_number BIGINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    modified_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    deleted_at TIMESTAMPTZ,

    FOREIGN KEY (directory_id, os_id)
        REFERENCES directories(directory_id, os_id),

    UNIQUE (os_id, inode_number),

    CHECK (file_name <> ''),

    CHECK (modified_at >= created_at)
);

CREATE UNIQUE INDEX uq_active_file_name
    ON files(directory_id, file_name)
    WHERE deleted_at IS NULL;

CREATE INDEX idx_files_owner
    ON files(owner_id, modified_at DESC);

CREATE TABLE file_permissions (
    permission_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    file_id BIGINT NOT NULL
        REFERENCES files(file_id),

    user_id BIGINT NOT NULL
        REFERENCES users(user_id),

    can_read BOOLEAN NOT NULL DEFAULT FALSE,

    can_write BOOLEAN NOT NULL DEFAULT FALSE,

    can_delete BOOLEAN NOT NULL DEFAULT FALSE,

    UNIQUE (file_id, user_id)
);

CREATE TABLE filesystem_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    file_id BIGINT REFERENCES files(file_id),

    user_id BIGINT NOT NULL REFERENCES users(user_id),

    operation VARCHAR(20) NOT NULL
        CHECK (
            operation IN (
                'CREATE',
                'READ',
                'WRITE',
                'DELETE',
                'DENIED'
            )
        ),

    success BOOLEAN NOT NULL,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    details TEXT
);

CREATE INDEX idx_filesystem_audit_time
    ON filesystem_audit(occurred_at DESC);

-- ---------------------------------------------------------------------------
-- 9. FILE PERMISSION VALIDATION
-- ---------------------------------------------------------------------------

CREATE FUNCTION validate_file_permission()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.user_id IS NULL OR NEW.file_id IS NULL THEN
        RAISE EXCEPTION 'File and user are required';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_file_permission
BEFORE INSERT OR UPDATE ON file_permissions
FOR EACH ROW
EXECUTE FUNCTION validate_file_permission();

-- ---------------------------------------------------------------------------
-- 10. PROCESS ELIGIBILITY
-- ---------------------------------------------------------------------------

CREATE FUNCTION check_process_eligibility(p_process_id BIGINT)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_state VARCHAR(20);
    v_memory BIGINT;
    v_threads INTEGER;
BEGIN
    SELECT p.state, p.memory_requested_mb
    INTO v_state, v_memory
    FROM processes p
    WHERE p.process_id = p_process_id;

    IF NOT FOUND THEN
        RETURN QUERY
        SELECT FALSE, 'Process does not exist'::TEXT;
        RETURN;
    END IF;

    IF v_state = 'TERMINATED' THEN
        RETURN QUERY
        SELECT FALSE, 'Process is terminated'::TEXT;
        RETURN;
    END IF;

    SELECT COUNT(*)::INTEGER
    INTO v_threads
    FROM threads t
    WHERE t.process_id = p_process_id
      AND t.state <> 'TERMINATED';

    IF v_threads = 0 THEN
        RETURN QUERY
        SELECT FALSE, 'No active threads'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT TRUE, 'Process is eligible for scheduling'::TEXT;
END;
$$;

-- ---------------------------------------------------------------------------
-- 11. PAGE ACCESS FUNCTION
-- ---------------------------------------------------------------------------

CREATE FUNCTION record_page_access(
    p_process_id BIGINT,
    p_page_number INTEGER
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    v_page_id BIGINT;
    v_present BOOLEAN;
BEGIN
    IF p_page_number < 0 THEN
        RAISE EXCEPTION 'Page number cannot be negative';
    END IF;

    SELECT page_id, present
    INTO v_page_id, v_present
    FROM virtual_pages
    WHERE process_id = p_process_id
      AND virtual_page_number = p_page_number
    FOR UPDATE;

    IF NOT FOUND THEN
        INSERT INTO virtual_pages (
            process_id,
            virtual_page_number,
            present,
            physical_frame_number
        )
        VALUES (
            p_process_id,
            p_page_number,
            FALSE,
            NULL
        )
        RETURNING page_id INTO v_page_id;

        v_present := FALSE;
    END IF;

    UPDATE virtual_pages
    SET last_accessed_at = CURRENT_TIMESTAMP
    WHERE page_id = v_page_id;

    INSERT INTO page_accesses (
        page_id,
        access_type,
        page_fault
    )
    VALUES (
        v_page_id,
        'READ',
        NOT v_present
    );

    RETURN NOT v_present;
END;
$$;

-- ---------------------------------------------------------------------------
-- 12. MEMORY ALLOCATION PROCEDURE
-- ---------------------------------------------------------------------------

CREATE PROCEDURE allocate_memory(
    p_process_id BIGINT,
    p_size_mb BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_os_id BIGINT;
    v_capacity BIGINT;
    v_allocated BIGINT;
    v_start BIGINT;
    v_requested BIGINT;
BEGIN
    IF p_size_mb <= 0 THEN
        RAISE EXCEPTION 'Allocation size must be positive';
    END IF;

    SELECT os_id, memory_requested_mb
    INTO v_os_id, v_requested
    FROM processes
    WHERE process_id = p_process_id
      AND state <> 'TERMINATED'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active process not found';
    END IF;

    IF p_size_mb > v_requested THEN
        RAISE EXCEPTION 'Allocation exceeds process request';
    END IF;

    SELECT total_memory_mb
    INTO v_capacity
    FROM operating_systems
    WHERE os_id = v_os_id
    FOR UPDATE;

    SELECT COALESCE(SUM(size_mb), 0)
    INTO v_allocated
    FROM memory_allocations
    WHERE os_id = v_os_id
      AND released_at IS NULL;

    IF v_allocated + p_size_mb > v_capacity THEN
        RAISE EXCEPTION 'Physical memory exhausted';
    END IF;

    -- This educational model assigns a logical address after existing
    -- active allocations. It does not implement physical compaction.
    SELECT COALESCE(MAX(start_address + size_mb), 0)
    INTO v_start
    FROM memory_allocations
    WHERE os_id = v_os_id
      AND released_at IS NULL;

    INSERT INTO memory_allocations (
        os_id,
        process_id,
        start_address,
        size_mb
    )
    VALUES (
        v_os_id,
        p_process_id,
        v_start,
        p_size_mb
    );

    UPDATE processes
    SET memory_allocated_mb = p_size_mb
    WHERE process_id = p_process_id;
END;
$$;

-- ---------------------------------------------------------------------------
-- 13. MEMORY RELEASE PROCEDURE
-- ---------------------------------------------------------------------------

CREATE PROCEDURE release_memory(p_process_id BIGINT)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE memory_allocations
    SET released_at = CURRENT_TIMESTAMP
    WHERE process_id = p_process_id
      AND released_at IS NULL;

    UPDATE processes
    SET memory_allocated_mb = 0
    WHERE process_id = p_process_id;
END;
$$;

-- ---------------------------------------------------------------------------
-- 14. PROCESS TERMINATION PROCEDURE
-- ---------------------------------------------------------------------------

CREATE PROCEDURE terminate_process(
    p_process_id BIGINT,
    p_exit_code INTEGER DEFAULT 0
)
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE processes
    SET state = 'TERMINATED',
        exit_code = p_exit_code
    WHERE process_id = p_process_id
      AND state <> 'TERMINATED';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Process not found or already terminated';
    END IF;

    UPDATE threads
    SET state = 'TERMINATED',
        remaining_time_ms = 0
    WHERE process_id = p_process_id;

    CALL release_memory(p_process_id);
END;
$$;

-- ---------------------------------------------------------------------------
-- 15. REPORTING VIEWS
-- ---------------------------------------------------------------------------

CREATE VIEW process_resource_report AS
SELECT
    o.hostname,
    p.process_id,
    p.process_name,
    p.state,
    p.priority,
    p.memory_requested_mb,
    p.memory_allocated_mb,
    COUNT(t.thread_id) AS thread_count,
    COUNT(t.thread_id) FILTER (
        WHERE t.state = 'READY'
    ) AS ready_threads,
    COUNT(t.thread_id) FILTER (
        WHERE t.state = 'BLOCKED'
    ) AS blocked_threads,
    COALESCE(SUM(t.cpu_time_ms), 0) AS total_cpu_time_ms
FROM processes p
JOIN operating_systems o
    ON o.os_id = p.os_id
LEFT JOIN threads t
    ON t.process_id = p.process_id
GROUP BY
    o.hostname,
    p.process_id,
    p.process_name,
    p.state,
    p.priority,
    p.memory_requested_mb,
    p.memory_allocated_mb;

CREATE VIEW memory_utilization AS
SELECT
    o.hostname,
    o.total_memory_mb,
    COALESCE(
        SUM(a.size_mb) FILTER (
            WHERE a.released_at IS NULL
        ),
        0
    ) AS allocated_mb,
    o.total_memory_mb -
    COALESCE(
        SUM(a.size_mb) FILTER (
            WHERE a.released_at IS NULL
        ),
        0
    ) AS available_mb
FROM operating_systems o
LEFT JOIN memory_allocations a
    ON a.os_id = o.os_id
GROUP BY o.os_id, o.hostname, o.total_memory_mb;

CREATE VIEW scheduling_report AS
SELECT
    r.run_id,
    r.algorithm,
    COUNT(s.slice_id) AS execution_count,
    COALESCE(SUM(s.duration_ms), 0) AS total_cpu_time_ms,
    MAX(s.remaining_time_ms) AS maximum_remaining_time
FROM scheduling_runs r
LEFT JOIN execution_slices s
    ON s.run_id = r.run_id
GROUP BY r.run_id, r.algorithm;

CREATE VIEW filesystem_report AS
SELECT
    d.directory_name,
    f.file_id,
    f.file_name,
    u.username AS owner,
    f.file_size_bytes,
    f.created_at,
    f.modified_at,
    f.deleted_at
FROM files f
JOIN directories d
    ON d.directory_id = f.directory_id
JOIN users u
    ON u.user_id = f.owner_id;

-- ---------------------------------------------------------------------------
-- 16. SAMPLE OPERATING SYSTEM AND USERS
-- ---------------------------------------------------------------------------

INSERT INTO operating_systems (
    hostname,
    architecture,
    total_memory_mb,
    cpu_cores
)
VALUES (
    'production-node-01',
    'x86_64',
    8192,
    8
);

INSERT INTO users (os_id, username, role)
SELECT os_id, data.username, data.role
FROM operating_systems
CROSS JOIN (
    VALUES
        ('admin', 'ADMIN'),
        ('operator', 'OPERATOR'),
        ('auditor', 'AUDITOR'),
        ('application', 'USER')
) AS data(username, role);

-- ---------------------------------------------------------------------------
-- 17. SAMPLE PROCESSES AND THREADS
-- ---------------------------------------------------------------------------

INSERT INTO processes (
    os_id,
    owner_id,
    process_name,
    state,
    memory_requested_mb,
    priority
)
SELECT
    o.os_id,
    u.user_id,
    data.process_name,
    data.state,
    data.memory,
    data.priority
FROM operating_systems o
JOIN users u
    ON u.os_id = o.os_id
CROSS JOIN (
    VALUES
        ('WebServer', 'READY', 512::BIGINT, 2),
        ('Database', 'READY', 1024::BIGINT, 1),
        ('BackupWorker', 'BLOCKED', 256::BIGINT, 7),
        ('CompletedJob', 'TERMINATED', 128::BIGINT, 5)
) AS data(process_name, state, memory, priority)
WHERE u.username = 'application';

UPDATE processes
SET terminated_at = CURRENT_TIMESTAMP,
    exit_code = 0
WHERE process_name = 'CompletedJob';

INSERT INTO threads (
    process_id,
    thread_name,
    state,
    burst_time_ms,
    remaining_time_ms
)
SELECT
    p.process_id,
    data.thread_name,
    data.state,
    data.burst,
    data.remaining
FROM processes p
CROSS JOIN (
    VALUES
        ('HTTP-Worker', 'READY', 8, 8),
        ('Logger', 'READY', 4, 4),
        ('Query-Worker', 'READY', 10, 10),
        ('Cache-Worker', 'BLOCKED', 6, 6),
        ('Backup-Thread', 'BLOCKED', 12, 12)
) AS data(thread_name, state, burst, remaining)
WHERE
    (p.process_name = 'WebServer'
        AND data.thread_name IN ('HTTP-Worker', 'Logger'))
    OR
    (p.process_name = 'Database'
        AND data.thread_name IN ('Query-Worker', 'Cache-Worker'))
    OR
    (p.process_name = 'BackupWorker'
        AND data.thread_name = 'Backup-Thread');

-- ---------------------------------------------------------------------------
-- 18. SAMPLE SCHEDULING HISTORY
-- ---------------------------------------------------------------------------

INSERT INTO scheduling_runs (
    os_id,
    algorithm,
    quantum_ms,
    completed_at
)
SELECT
    os_id,
    'ROUND_ROBIN',
    2,
    CURRENT_TIMESTAMP
FROM operating_systems;

INSERT INTO execution_slices (
    run_id,
    thread_id,
    sequence_number,
    start_time_ms,
    duration_ms,
    remaining_time_ms
)
SELECT
    r.run_id,
    t.thread_id,
    data.sequence_number,
    data.start_time,
    data.duration,
    data.remaining
FROM scheduling_runs r
JOIN processes p
    ON p.os_id = r.os_id
JOIN threads t
    ON t.process_id = p.process_id
JOIN (
    VALUES
        ('HTTP-Worker', 1, 0, 2, 6),
        ('Query-Worker', 2, 2, 2, 8),
        ('Logger', 3, 4, 2, 2)
) AS data(
    thread_name,
    sequence_number,
    start_time,
    duration,
    remaining
)
    ON data.thread_name = t.thread_name
WHERE r.algorithm = 'ROUND_ROBIN';

-- ---------------------------------------------------------------------------
-- 19. SAMPLE MEMORY ALLOCATIONS
-- ---------------------------------------------------------------------------

CALL allocate_memory(
    (SELECT process_id FROM processes
     WHERE process_name = 'WebServer'),
    512
);

CALL allocate_memory(
    (SELECT process_id FROM processes
     WHERE process_name = 'Database'),
    1024
);

-- ---------------------------------------------------------------------------
-- 20. SAMPLE VIRTUAL MEMORY
-- ---------------------------------------------------------------------------

INSERT INTO virtual_pages (
    process_id,
    virtual_page_number,
    physical_frame_number,
    present,
    dirty
)
SELECT
    p.process_id,
    data.page_number,
    data.frame_number,
    data.present,
    data.dirty
FROM processes p
CROSS JOIN (
    VALUES
        (0, 0, TRUE, FALSE),
        (1, 1, TRUE, TRUE),
        (2, NULL::INTEGER, FALSE, FALSE),
        (3, NULL::INTEGER, FALSE, FALSE)
) AS data(
    page_number,
    frame_number,
    present,
    dirty
)
WHERE p.process_name = 'WebServer';

SELECT record_page_access(
    (SELECT process_id FROM processes
     WHERE process_name = 'WebServer'),
    0
);

SELECT record_page_access(
    (SELECT process_id FROM processes
     WHERE process_name = 'WebServer'),
    2
);

-- ---------------------------------------------------------------------------
-- 21. SAMPLE FILESYSTEM STRUCTURE
-- ---------------------------------------------------------------------------

INSERT INTO directories (
    os_id,
    parent_directory_id,
    directory_name,
    owner_id
)
SELECT
    o.os_id,
    NULL,
    'var',
    u.user_id
FROM operating_systems o
JOIN users u
    ON u.os_id = o.os_id
WHERE u.username = 'admin';

INSERT INTO directories (
    os_id,
    parent_directory_id,
    directory_name,
    owner_id
)
SELECT
    d.os_id,
    d.directory_id,
    'log',
    d.owner_id
FROM directories d
WHERE d.directory_name = 'var';

INSERT INTO files (
    os_id,
    directory_id,
    file_name,
    owner_id,
    content,
    file_size_bytes,
    inode_number
)
SELECT
    d.os_id,
    d.directory_id,
    'system.log',
    u.user_id,
    'Kernel startup completed successfully',
    38,
    10001
FROM directories d
JOIN users u
    ON u.os_id = d.os_id
WHERE d.directory_name = 'log'
  AND u.username = 'admin';

INSERT INTO files (
    os_id,
    directory_id,
    file_name,
    owner_id,
    content,
    file_size_bytes,
    inode_number
)
SELECT
    d.os_id,
    d.directory_id,
    'application.conf',
    u.user_id,
    'environment=production',
    22,
    10002
FROM directories d
JOIN users u
    ON u.os_id = d.os_id
WHERE d.directory_name = 'log'
  AND u.username = 'admin';

INSERT INTO file_permissions (
    file_id,
    user_id,
    can_read,
    can_write,
    can_delete
)
SELECT
    f.file_id,
    u.user_id,
    TRUE,
    FALSE,
    FALSE
FROM files f
JOIN users u
    ON u.username = 'auditor'
WHERE f.file_name = 'system.log';

INSERT INTO filesystem_audit (
    file_id,
    user_id,
    operation,
    success,
    details
)
SELECT
    f.file_id,
    u.user_id,
    'READ',
    TRUE,
    'Authorized audit read'
FROM files f
JOIN users u
    ON u.username = 'auditor'
WHERE f.file_name = 'system.log';

INSERT INTO filesystem_audit (
    file_id,
    user_id,
    operation,
    success,
    details
)
SELECT
    f.file_id,
    u.user_id,
    'DENIED',
    FALSE,
    'Attempted unauthorized write'
FROM files f
JOIN users u
    ON u.username = 'auditor'
WHERE f.file_name = 'system.log';

COMMIT;

-- ---------------------------------------------------------------------------
-- 22. PROCESS RETRIEVAL
-- ---------------------------------------------------------------------------

SELECT *
FROM process_resource_report
ORDER BY process_id;

-- ---------------------------------------------------------------------------
-- 23. PROCESS ELIGIBILITY EVALUATION
-- ---------------------------------------------------------------------------

SELECT
    p.process_id,
    p.process_name,
    eligibility.eligible,
    eligibility.reason
FROM processes p
CROSS JOIN LATERAL
    check_process_eligibility(p.process_id) AS eligibility
ORDER BY p.process_id;

-- ---------------------------------------------------------------------------
-- 24. MEMORY AGGREGATION
-- ---------------------------------------------------------------------------

SELECT *
FROM memory_utilization;

-- ---------------------------------------------------------------------------
-- 25. CPU SCHEDULING ANALYSIS
-- ---------------------------------------------------------------------------

SELECT *
FROM scheduling_report;

-- Calculate CPU time by process.
SELECT
    p.process_name,
    SUM(s.duration_ms) AS total_cpu_time_ms,
    COUNT(s.slice_id) AS execution_slices
FROM processes p
JOIN threads t
    ON t.process_id = p.process_id
JOIN execution_slices s
    ON s.thread_id = t.thread_id
GROUP BY p.process_id, p.process_name
ORDER BY total_cpu_time_ms DESC;

-- ---------------------------------------------------------------------------
-- 26. VIRTUAL MEMORY FAULT ANALYSIS
-- ---------------------------------------------------------------------------

SELECT
    p.process_name,
    COUNT(a.access_id) AS total_accesses,
    COUNT(*) FILTER (
        WHERE a.page_fault
    ) AS page_faults,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE a.page_fault
        ) / NULLIF(COUNT(a.access_id), 0),
        2
    ) AS fault_percentage
FROM processes p
JOIN virtual_pages v
    ON v.process_id = p.process_id
LEFT JOIN page_accesses a
    ON a.page_id = v.page_id
GROUP BY p.process_id, p.process_name;

-- ---------------------------------------------------------------------------
-- 27. FILESYSTEM REPORT
-- ---------------------------------------------------------------------------

SELECT *
FROM filesystem_report
WHERE deleted_at IS NULL
ORDER BY directory_name, file_name;

-- ---------------------------------------------------------------------------
-- 28. FILE PERMISSION EVALUATION
-- ---------------------------------------------------------------------------

SELECT
    f.file_name,
    u.username,
    CASE
        WHEN u.user_id = f.owner_id THEN TRUE
        ELSE COALESCE(fp.can_read, FALSE)
    END AS can_read,
    COALESCE(fp.can_write, FALSE) AS delegated_write,
    COALESCE(fp.can_delete, FALSE) AS delegated_delete
FROM files f
CROSS JOIN users u
LEFT JOIN file_permissions fp
    ON fp.file_id = f.file_id
   AND fp.user_id = u.user_id
WHERE f.deleted_at IS NULL
ORDER BY f.file_name, u.username;

-- ---------------------------------------------------------------------------
-- 29. COMMON TABLE EXPRESSION: PROCESS TREE
-- ---------------------------------------------------------------------------

WITH RECURSIVE process_tree AS (
    SELECT
        process_id,
        parent_process_id,
        process_name,
        0 AS depth,
        ARRAY[process_id] AS ancestry
    FROM processes
    WHERE parent_process_id IS NULL

    UNION ALL

    SELECT
        child.process_id,
        child.parent_process_id,
        child.process_name,
        parent.depth + 1,
        parent.ancestry || child.process_id
    FROM processes child
    JOIN process_tree parent
        ON child.parent_process_id = parent.process_id
    WHERE NOT child.process_id = ANY(parent.ancestry)
)
SELECT
    process_id,
    process_name,
    depth,
    ancestry
FROM process_tree
ORDER BY ancestry;

-- ---------------------------------------------------------------------------
-- 30. WORKFLOW PROCESSING: TERMINATE A PROCESS
-- ---------------------------------------------------------------------------

BEGIN;

CALL terminate_process(
    (
        SELECT process_id
        FROM processes
        WHERE process_name = 'BackupWorker'
    ),
    0
);

COMMIT;

-- ---------------------------------------------------------------------------
-- 31. VALIDATION: RESOURCE LIMITS
-- ---------------------------------------------------------------------------

SELECT
    o.hostname,
    o.total_memory_mb,
    COALESCE(SUM(a.size_mb), 0) AS allocated_memory,
    CASE
        WHEN COALESCE(SUM(a.size_mb), 0) <= o.total_memory_mb
        THEN 'VALID'
        ELSE 'INVALID'
    END AS resource_status
FROM operating_systems o
LEFT JOIN memory_allocations a
    ON a.os_id = o.os_id
   AND a.released_at IS NULL
GROUP BY o.os_id, o.hostname, o.total_memory_mb;

-- ---------------------------------------------------------------------------
-- 32. AUDIT REPORT
-- ---------------------------------------------------------------------------

SELECT
    a.audit_id,
    u.username,
    f.file_name,
    a.operation,
    a.success,
    a.occurred_at,
    a.details
FROM filesystem_audit a
JOIN users u
    ON u.user_id = a.user_id
LEFT JOIN files f
    ON f.file_id = a.file_id
ORDER BY a.occurred_at DESC;

-- ---------------------------------------------------------------------------
-- 33. FAILURE-CASE QUERY: RESOURCE EXHAUSTION DETECTION
-- ---------------------------------------------------------------------------

SELECT
    o.hostname,
    p.process_name,
    p.memory_requested_mb,
    p.memory_allocated_mb,
    m.available_mb,
    CASE
        WHEN p.memory_requested_mb > m.available_mb
        THEN 'INSUFFICIENT_AVAILABLE_MEMORY'
        ELSE 'CAPACITY_AVAILABLE'
    END AS allocation_assessment
FROM processes p
JOIN operating_systems o
    ON o.os_id = p.os_id
JOIN memory_utilization m
    ON m.hostname = o.hostname
WHERE p.state <> 'TERMINATED'
ORDER BY p.process_name;

-- ---------------------------------------------------------------------------
-- 34. FINAL RESOURCE REPORT
-- ---------------------------------------------------------------------------

SELECT
    hostname,
    total_memory_mb,
    allocated_mb,
    available_mb,
    ROUND(
        100.0 * allocated_mb / total_memory_mb,
        2
    ) AS utilization_percentage
FROM memory_utilization;

-- End of operating-system relational simulation.
