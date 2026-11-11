/*
 * BUILD SYSTEMS
 * PostgreSQL 15+
 *
 * Domain:
 *   Projects -> Build Targets -> Dependencies
 *   Build Runs -> Target Executions -> Artifacts
 *   Build Policies -> Validation -> Packaging
 *
 * Demonstrates:
 *   Dependency registration and validation
 *   Compilation states
 *   Build configuration
 *   Incremental-build fingerprints
 *   Artifact integrity
 *   Packaging workflows
 *   Transaction handling
 *   Audit history
 */

BEGIN;

CREATE SCHEMA IF NOT EXISTS build_management;

SET search_path TO build_management, public;

-- ============================================================
-- 1. ENUMERATIONS
-- ============================================================

CREATE TYPE target_type AS ENUM (
    'library',
    'executable'
);

CREATE TYPE build_profile AS ENUM (
    'debug',
    'release'
);

CREATE TYPE build_status AS ENUM (
    'pending',
    'running',
    'succeeded',
    'failed',
    'cancelled'
);

CREATE TYPE execution_status AS ENUM (
    'pending',
    'building',
    'succeeded',
    'failed',
    'cached',
    'skipped'
);

CREATE TYPE package_status AS ENUM (
    'pending',
    'validated',
    'published',
    'failed'
);

-- ============================================================
-- 2. PROJECTS
-- ============================================================

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_name VARCHAR(120) NOT NULL UNIQUE,

    version VARCHAR(30) NOT NULL,

    description TEXT,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_project_version
        CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$')
);

-- ============================================================
-- 3. BUILD TARGETS
-- ============================================================

CREATE TABLE build_targets (
    target_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id)
        ON DELETE CASCADE,

    target_name VARCHAR(120) NOT NULL,

    source_path TEXT NOT NULL,

    version VARCHAR(30) NOT NULL,

    target_kind target_type NOT NULL,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_project_target
        UNIQUE (project_id, target_name),

    CONSTRAINT valid_target_version
        CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),

    CONSTRAINT nonempty_source
        CHECK (LENGTH(TRIM(source_path)) > 0)
);

-- ============================================================
-- 4. TARGET DEPENDENCIES
-- ============================================================

CREATE TABLE target_dependencies (
    dependency_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL,

    target_id BIGINT NOT NULL,

    depends_on_target_id BIGINT NOT NULL,

    minimum_version VARCHAR(30),

    optional BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_dependency_target
        FOREIGN KEY (project_id, target_id)
        REFERENCES build_targets(project_id, target_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_dependency_parent
        FOREIGN KEY (project_id, depends_on_target_id)
        REFERENCES build_targets(project_id, target_id)
        ON DELETE CASCADE,

    CONSTRAINT unique_dependency
        UNIQUE (target_id, depends_on_target_id),

    CONSTRAINT no_self_dependency
        CHECK (target_id <> depends_on_target_id),

    CONSTRAINT valid_minimum_version
        CHECK (
            minimum_version IS NULL
            OR minimum_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'
        )
);

CREATE INDEX idx_dependency_parent
    ON target_dependencies(depends_on_target_id);

-- ============================================================
-- 5. BUILD CONFIGURATIONS
-- ============================================================

CREATE TABLE build_configurations (
    configuration_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id)
        ON DELETE CASCADE,

    configuration_name VARCHAR(100) NOT NULL,

    profile build_profile NOT NULL,

    compiler_name VARCHAR(100) NOT NULL,

    compiler_version VARCHAR(50) NOT NULL,

    compiler_flags TEXT[] NOT NULL DEFAULT '{}',

    environment JSONB NOT NULL DEFAULT '{}',

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (project_id, configuration_name),

    CONSTRAINT valid_environment
        CHECK (jsonb_typeof(environment) = 'object')
);

-- ============================================================
-- 6. BUILD RUNS
-- ============================================================

CREATE TABLE build_runs (
    build_run_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    configuration_id BIGINT NOT NULL
        REFERENCES build_configurations(configuration_id),

    status build_status NOT NULL DEFAULT 'pending',

    requested_by VARCHAR(120) NOT NULL,

    source_revision VARCHAR(100) NOT NULL,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    error_message TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_run_times
        CHECK (
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT valid_successful_run
        CHECK (
            status <> 'succeeded'
            OR completed_at IS NOT NULL
        )
);

CREATE INDEX idx_build_runs_project_time
    ON build_runs(project_id, created_at DESC);

CREATE INDEX idx_build_runs_status
    ON build_runs(status, created_at DESC);

-- ============================================================
-- 7. TARGET EXECUTIONS
-- ============================================================

CREATE TABLE target_executions (
    execution_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    build_run_id BIGINT NOT NULL
        REFERENCES build_runs(build_run_id)
        ON DELETE CASCADE,

    target_id BIGINT NOT NULL
        REFERENCES build_targets(target_id),

    status execution_status NOT NULL DEFAULT 'pending',

    build_fingerprint VARCHAR(128) NOT NULL,

    compiler_output TEXT,

    error_message TEXT,

    started_at TIMESTAMPTZ,

    completed_at TIMESTAMPTZ,

    UNIQUE (build_run_id, target_id),

    CONSTRAINT valid_execution_times
        CHECK (
            completed_at IS NULL
            OR started_at IS NULL
            OR completed_at >= started_at
        ),

    CONSTRAINT valid_execution_success
        CHECK (
            status <> 'succeeded'
            OR completed_at IS NOT NULL
        )
);

CREATE INDEX idx_target_execution_run
    ON target_executions(build_run_id, status);

CREATE INDEX idx_target_execution_fingerprint
    ON target_executions(build_fingerprint);

-- ============================================================
-- 8. BUILD ARTIFACTS
-- ============================================================

CREATE TABLE build_artifacts (
    artifact_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    execution_id BIGINT NOT NULL UNIQUE
        REFERENCES target_executions(execution_id)
        ON DELETE CASCADE,

    artifact_name VARCHAR(255) NOT NULL,

    artifact_path TEXT NOT NULL,

    checksum_sha256 CHAR(64) NOT NULL,

    file_size BIGINT NOT NULL,

    build_fingerprint VARCHAR(128) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_checksum
        CHECK (checksum_sha256 ~ '^[a-fA-F0-9]{64}$'),

    CONSTRAINT nonnegative_file_size
        CHECK (file_size >= 0)
);

CREATE INDEX idx_artifact_fingerprint
    ON build_artifacts(build_fingerprint);

-- ============================================================
-- 9. BUILD CACHE
-- ============================================================

CREATE TABLE build_cache (
    cache_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    build_fingerprint VARCHAR(128) NOT NULL,

    artifact_id BIGINT NOT NULL
        REFERENCES build_artifacts(artifact_id),

    cache_valid BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (project_id, build_fingerprint)
);

CREATE INDEX idx_cache_lookup
    ON build_cache(
        project_id,
        build_fingerprint
    )
    WHERE cache_valid = TRUE;

-- ============================================================
-- 10. PACKAGES
-- ============================================================

CREATE TABLE packages (
    package_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    build_run_id BIGINT NOT NULL
        REFERENCES build_runs(build_run_id),

    package_name VARCHAR(150) NOT NULL,

    version VARCHAR(30) NOT NULL,

    status package_status NOT NULL DEFAULT 'pending',

    package_path TEXT,

    manifest JSONB NOT NULL DEFAULT '{}',

    checksum_sha256 CHAR(64),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    published_at TIMESTAMPTZ,

    UNIQUE (build_run_id, package_name, version),

    CONSTRAINT valid_package_version
        CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),

    CONSTRAINT valid_manifest
        CHECK (jsonb_typeof(manifest) = 'object'),

    CONSTRAINT valid_package_checksum
        CHECK (
            checksum_sha256 IS NULL
            OR checksum_sha256 ~ '^[a-fA-F0-9]{64}$'
        ),

    CONSTRAINT published_package_complete
        CHECK (
            status <> 'published'
            OR (
                package_path IS NOT NULL
                AND checksum_sha256 IS NOT NULL
                AND published_at IS NOT NULL
            )
        )
);

-- ============================================================
-- 11. PACKAGE CONTENTS
-- ============================================================

CREATE TABLE package_artifacts (
    package_id BIGINT NOT NULL
        REFERENCES packages(package_id)
        ON DELETE CASCADE,

    artifact_id BIGINT NOT NULL
        REFERENCES build_artifacts(artifact_id),

    PRIMARY KEY (package_id, artifact_id)
);

-- ============================================================
-- 12. BUILD AUDIT LOG
-- ============================================================

CREATE TABLE build_audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    build_run_id BIGINT
        REFERENCES build_runs(build_run_id),

    event_type VARCHAR(100) NOT NULL,

    event_details JSONB NOT NULL DEFAULT '{}',

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_build_audit_time
    ON build_audit_log(project_id, recorded_at DESC);

-- ============================================================
-- 13. DEPENDENCY CYCLE DETECTION
-- ============================================================

CREATE OR REPLACE FUNCTION detect_dependency_cycle()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    cycle_found BOOLEAN;
BEGIN
    IF NEW.target_id = NEW.depends_on_target_id THEN
        RAISE EXCEPTION
            'A target cannot depend on itself';
    END IF;

    /*
     * Starting from the proposed dependency, follow its
     * dependencies. Reaching NEW.target_id creates a cycle.
     */
    WITH RECURSIVE dependency_path(target_id) AS (
        SELECT NEW.depends_on_target_id

        UNION

        SELECT d.depends_on_target_id
        FROM target_dependencies d
        JOIN dependency_path p
          ON d.target_id = p.target_id
        WHERE d.project_id = NEW.project_id
    )
    SELECT EXISTS (
        SELECT 1
        FROM dependency_path
        WHERE target_id = NEW.target_id
    )
    INTO cycle_found;

    IF cycle_found THEN
        RAISE EXCEPTION
            'Circular dependency detected between targets % and %',
            NEW.target_id,
            NEW.depends_on_target_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_detect_dependency_cycle
BEFORE INSERT OR UPDATE
ON target_dependencies
FOR EACH ROW
EXECUTE FUNCTION detect_dependency_cycle();

-- ============================================================
-- 14. AUDIT BUILD STATUS CHANGES
-- ============================================================

CREATE OR REPLACE FUNCTION audit_build_status()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN

        INSERT INTO build_audit_log (
            project_id,
            build_run_id,
            event_type,
            event_details
        )
        VALUES (
            NEW.project_id,
            NEW.build_run_id,
            'BUILD_STATUS_CHANGED',
            jsonb_build_object(
                'old_status', OLD.status,
                'new_status', NEW.status
            )
        );

    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_audit_build_status
AFTER UPDATE OF status
ON build_runs
FOR EACH ROW
EXECUTE FUNCTION audit_build_status();

-- ============================================================
-- 15. BUILD RUN CREATION PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE create_build_run(
    p_project_id BIGINT,
    p_configuration_id BIGINT,
    p_requested_by VARCHAR,
    p_source_revision VARCHAR,
    OUT p_build_run_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    configuration_project_id BIGINT;
BEGIN
    SELECT project_id
    INTO configuration_project_id
    FROM build_configurations
    WHERE configuration_id = p_configuration_id
      AND active = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Build configuration is missing or inactive';
    END IF;

    IF configuration_project_id <> p_project_id THEN
        RAISE EXCEPTION
            'Configuration belongs to another project';
    END IF;

    IF p_requested_by IS NULL
       OR LENGTH(TRIM(p_requested_by)) = 0 THEN
        RAISE EXCEPTION
            'Requested-by field cannot be empty';
    END IF;

    INSERT INTO build_runs (
        project_id,
        configuration_id,
        requested_by,
        source_revision
    )
    VALUES (
        p_project_id,
        p_configuration_id,
        p_requested_by,
        p_source_revision
    )
    RETURNING build_run_id INTO p_build_run_id;

    INSERT INTO build_audit_log (
        project_id,
        build_run_id,
        event_type,
        event_details
    )
    VALUES (
        p_project_id,
        p_build_run_id,
        'BUILD_CREATED',
        jsonb_build_object(
            'requested_by', p_requested_by,
            'revision', p_source_revision
        )
    );
END;
$$;

-- ============================================================
-- 16. DEPENDENCY ORDER QUERY
-- ============================================================

CREATE OR REPLACE FUNCTION get_build_order(
    p_project_id BIGINT
)
RETURNS TABLE (
    target_id BIGINT,
    target_name VARCHAR,
    build_level INTEGER
)
LANGUAGE sql
STABLE
AS $$
    WITH RECURSIVE levels AS (
        SELECT
            t.target_id,
            t.target_name,
            0 AS build_level
        FROM build_targets t
        WHERE t.project_id = p_project_id
          AND NOT EXISTS (
              SELECT 1
              FROM target_dependencies d
              WHERE d.target_id = t.target_id
                AND d.project_id = p_project_id
          )

        UNION ALL

        SELECT
            t.target_id,
            t.target_name,
            l.build_level + 1
        FROM levels l
        JOIN target_dependencies d
          ON d.depends_on_target_id = l.target_id
         AND d.project_id = p_project_id
        JOIN build_targets t
          ON t.target_id = d.target_id
         AND t.project_id = p_project_id
    )
    SELECT
        target_id,
        target_name,
        MAX(build_level)::INTEGER
    FROM levels
    GROUP BY target_id, target_name
    ORDER BY MAX(build_level), target_name;
$$;

-- ============================================================
-- 17. BUILD ELIGIBILITY VIEW
-- ============================================================

CREATE OR REPLACE VIEW build_eligibility AS
SELECT
    br.build_run_id,
    p.project_name,
    br.status,

    COUNT(te.execution_id) AS total_targets,

    COUNT(*) FILTER (
        WHERE te.status IN ('succeeded', 'cached')
    ) AS successful_targets,

    COUNT(*) FILTER (
        WHERE te.status = 'failed'
    ) AS failed_targets,

    CASE
        WHEN br.status <> 'succeeded'
            THEN FALSE

        WHEN COUNT(te.execution_id) = 0
            THEN FALSE

        WHEN COUNT(*) FILTER (
            WHERE te.status NOT IN ('succeeded', 'cached')
        ) > 0
            THEN FALSE

        ELSE TRUE
    END AS package_eligible

FROM build_runs br

JOIN projects p
  ON p.project_id = br.project_id

LEFT JOIN target_executions te
  ON te.build_run_id = br.build_run_id

GROUP BY
    br.build_run_id,
    p.project_name,
    br.status;

-- ============================================================
-- 18. REPORTING VIEW
-- ============================================================

CREATE OR REPLACE VIEW build_statistics AS
SELECT
    p.project_id,
    p.project_name,

    COUNT(DISTINCT br.build_run_id) AS total_builds,

    COUNT(DISTINCT br.build_run_id) FILTER (
        WHERE br.status = 'succeeded'
    ) AS successful_builds,

    COUNT(DISTINCT br.build_run_id) FILTER (
        WHERE br.status = 'failed'
    ) AS failed_builds,

    COUNT(DISTINCT a.artifact_id) AS artifacts_created,

    ROUND(
        100.0 *
        COUNT(DISTINCT br.build_run_id) FILTER (
            WHERE br.status = 'succeeded'
        ) /
        NULLIF(COUNT(DISTINCT br.build_run_id), 0),
        2
    ) AS success_percentage

FROM projects p

LEFT JOIN build_runs br
  ON br.project_id = p.project_id

LEFT JOIN target_executions te
  ON te.build_run_id = br.build_run_id

LEFT JOIN build_artifacts a
  ON a.execution_id = te.execution_id

GROUP BY p.project_id, p.project_name;

-- ============================================================
-- 19. SAMPLE DATA
-- ============================================================

INSERT INTO projects (
    project_name,
    version,
    description
)
VALUES (
    'enterprise_application',
    '1.0.0',
    'Enterprise application build pipeline'
);

INSERT INTO build_configurations (
    project_id,
    configuration_name,
    profile,
    compiler_name,
    compiler_version,
    compiler_flags,
    environment
)
SELECT
    project_id,
    'release-gcc',
    'release',
    'GCC',
    '14.2.0',
    ARRAY['-O2', '-Wall', '-Wextra'],
    '{"platform":"linux","architecture":"x86_64"}'
FROM projects
WHERE project_name = 'enterprise_application';

INSERT INTO build_configurations (
    project_id,
    configuration_name,
    profile,
    compiler_name,
    compiler_version,
    compiler_flags
)
SELECT
    project_id,
    'debug-gcc',
    'debug',
    'GCC',
    '14.2.0',
    ARRAY['-g', '-O0']
FROM projects
WHERE project_name = 'enterprise_application';

INSERT INTO build_targets (
    project_id,
    target_name,
    source_path,
    version,
    target_kind
)
SELECT
    project_id,
    'core',
    'src/core.cpp',
    '1.0.0',
    'library'
FROM projects
WHERE project_name = 'enterprise_application';

INSERT INTO build_targets (
    project_id,
    target_name,
    source_path,
    version,
    target_kind
)
SELECT
    project_id,
    'database',
    'src/database.cpp',
    '1.0.0',
    'library'
FROM projects
WHERE project_name = 'enterprise_application';

INSERT INTO build_targets (
    project_id,
    target_name,
    source_path,
    version,
    target_kind
)
SELECT
    project_id,
    'network',
    'src/network.cpp',
    '1.0.0',
    'library'
FROM projects
WHERE project_name = 'enterprise_application';

INSERT INTO build_targets (
    project_id,
    target_name,
    source_path,
    version,
    target_kind
)
SELECT
    project_id,
    'application',
    'src/main.cpp',
    '1.0.0',
    'executable'
FROM projects
WHERE project_name = 'enterprise_application';

-- Register dependency relationships.

INSERT INTO target_dependencies (
    project_id,
    target_id,
    depends_on_target_id,
    minimum_version
)
SELECT
    p.project_id,
    dependent.target_id,
    required.target_id,
    '1.0.0'
FROM projects p

JOIN build_targets dependent
  ON dependent.project_id = p.project_id

JOIN build_targets required
  ON required.project_id = p.project_id

WHERE p.project_name = 'enterprise_application'
  AND (
      (dependent.target_name = 'database'
       AND required.target_name = 'core')

      OR

      (dependent.target_name = 'network'
       AND required.target_name = 'core')

      OR

      (dependent.target_name = 'application'
       AND required.target_name = 'database')

      OR

      (dependent.target_name = 'application'
       AND required.target_name = 'network')
  );

-- ============================================================
-- 20. CREATE BUILD RUN
-- ============================================================

DO $$
DECLARE
    v_project_id BIGINT;
    v_configuration_id BIGINT;
    v_build_run_id BIGINT;
BEGIN
    SELECT project_id
    INTO v_project_id
    FROM projects
    WHERE project_name = 'enterprise_application';

    SELECT configuration_id
    INTO v_configuration_id
    FROM build_configurations
    WHERE project_id = v_project_id
      AND configuration_name = 'release-gcc';

    CALL create_build_run(
        v_project_id,
        v_configuration_id,
        'build-engineer',
        'commit-a1b2c3d4',
        v_build_run_id
    );

    -- Register compilation tasks for the run.

    INSERT INTO target_executions (
        build_run_id,
        target_id,
        build_fingerprint
    )
    SELECT
        v_build_run_id,
        target_id,
        MD5(
            target_name ||
            source_path ||
            version ||
            'release-gcc'
        )
    FROM build_targets
    WHERE project_id = v_project_id
      AND enabled = TRUE;

    UPDATE build_runs
    SET
        status = 'running',
        started_at = NOW()
    WHERE build_run_id = v_build_run_id;

END;
$$;

-- ============================================================
-- 21. SIMULATED COMPILATION RESULTS
-- ============================================================

/*
 * The database records compiler outcomes.
 * Actual compiler execution belongs to an external build worker.
 */

DO $$
DECLARE
    v_run_id BIGINT;
    v_execution RECORD;
    v_checksum CHAR(64);
BEGIN
    SELECT MAX(build_run_id)
    INTO v_run_id
    FROM build_runs;

    FOR v_execution IN
        SELECT
            te.execution_id,
            te.build_fingerprint,
            t.target_id,
            t.target_name,
            t.source_path
        FROM target_executions te
        JOIN build_targets t
          ON t.target_id = te.target_id
        WHERE te.build_run_id = v_run_id
        ORDER BY t.target_name
    LOOP

        v_checksum := MD5(
            v_execution.target_name ||
            v_execution.build_fingerprint
        ) ||
        MD5(v_execution.source_path);

        UPDATE target_executions
        SET
            status = 'succeeded',
            compiler_output = 'Compilation completed successfully',
            started_at = NOW(),
            completed_at = NOW()
        WHERE execution_id = v_execution.execution_id;

        INSERT INTO build_artifacts (
            execution_id,
            artifact_name,
            artifact_path,
            checksum_sha256,
            file_size,
            build_fingerprint
        )
        VALUES (
            v_execution.execution_id,
            v_execution.target_name || '.artifact',
            'artifacts/' ||
                v_execution.target_name || '.artifact',
            v_checksum,
            LENGTH(v_execution.source_path) * 1024,
            v_execution.build_fingerprint
        );

    END LOOP;

    UPDATE build_runs
    SET
        status = 'succeeded',
        completed_at = NOW()
    WHERE build_run_id = v_run_id;
END;
$$;

-- ============================================================
-- 22. INCREMENTAL BUILD CACHE REGISTRATION
-- ============================================================

INSERT INTO build_cache (
    project_id,
    build_fingerprint,
    artifact_id
)
SELECT
    br.project_id,
    a.build_fingerprint,
    a.artifact_id
FROM build_artifacts a

JOIN target_executions te
  ON te.execution_id = a.execution_id

JOIN build_runs br
  ON br.build_run_id = te.build_run_id

ON CONFLICT (project_id, build_fingerprint)
DO UPDATE SET
    artifact_id = EXCLUDED.artifact_id,
    cache_valid = TRUE,
    last_accessed_at = NOW();

-- ============================================================
-- 23. PACKAGE CREATION
-- ============================================================

DO $$
DECLARE
    v_run_id BIGINT;
    v_package_id BIGINT;
    v_eligible BOOLEAN;
BEGIN
    SELECT MAX(build_run_id)
    INTO v_run_id
    FROM build_runs;

    SELECT package_eligible
    INTO v_eligible
    FROM build_eligibility
    WHERE build_run_id = v_run_id;

    IF NOT COALESCE(v_eligible, FALSE) THEN
        RAISE EXCEPTION
            'Build is not eligible for packaging';
    END IF;

    INSERT INTO packages (
        build_run_id,
        package_name,
        version,
        status,
        package_path,
        manifest,
        checksum_sha256,
        published_at
    )
    VALUES (
        v_run_id,
        'enterprise_application',
        '1.0.0',
        'published',
        'packages/enterprise_application-1.0.0',
        jsonb_build_object(
            'build_run_id', v_run_id,
            'profile', 'release',
            'format', 'application-bundle'
        ),
        MD5('enterprise_application') ||
            MD5(v_run_id::TEXT),
        NOW()
    )
    RETURNING package_id INTO v_package_id;

    INSERT INTO package_artifacts (
        package_id,
        artifact_id
    )
    SELECT
        v_package_id,
        a.artifact_id
    FROM build_artifacts a
    JOIN target_executions te
      ON te.execution_id = a.execution_id
    WHERE te.build_run_id = v_run_id;

END;
$$;

-- ============================================================
-- 24. RETRIEVAL AND REPORTING
-- ============================================================

-- Project dependency order.

SELECT *
FROM get_build_order(
    (
        SELECT project_id
        FROM projects
        WHERE project_name = 'enterprise_application'
    )
);

-- Build execution details.

SELECT
    br.build_run_id,
    br.status AS build_status,
    t.target_name,
    te.status AS compilation_status,
    te.build_fingerprint,
    te.error_message
FROM build_runs br
JOIN target_executions te
  ON te.build_run_id = br.build_run_id
JOIN build_targets t
  ON t.target_id = te.target_id
ORDER BY br.build_run_id, t.target_name;

-- Artifact integrity information.

SELECT
    t.target_name,
    a.artifact_name,
    a.checksum_sha256,
    a.file_size,
    a.build_fingerprint
FROM build_artifacts a
JOIN target_executions te
  ON te.execution_id = a.execution_id
JOIN build_targets t
  ON t.target_id = te.target_id;

-- Incremental cache utilization.

SELECT
    project_id,
    COUNT(*) AS cached_artifacts,
    COUNT(*) FILTER (
        WHERE cache_valid
    ) AS valid_cache_entries
FROM build_cache
GROUP BY project_id;

-- Build eligibility.

SELECT *
FROM build_eligibility;

-- Project build performance statistics.

SELECT *
FROM build_statistics;

-- Package contents.

SELECT
    p.package_name,
    p.version,
    p.status,
    a.artifact_name,
    a.checksum_sha256
FROM packages p
JOIN package_artifacts pa
  ON pa.package_id = p.package_id
JOIN build_artifacts a
  ON a.artifact_id = pa.artifact_id;

-- Audit history.

SELECT
    event_type,
    event_details,
    recorded_at
FROM build_audit_log
ORDER BY recorded_at DESC;

-- ============================================================
-- 25. TRANSACTIONAL CACHE INVALIDATION
-- ============================================================

/*
 * A changed source revision invalidates prior cache entries
 * for a project. In a production system, invalidation should
 * be based on dependency fingerprints rather than deleting
 * every cache entry indiscriminately.
 */

-- Example:
--
-- BEGIN;
--
-- UPDATE build_cache
-- SET
--     cache_valid = FALSE,
--     last_accessed_at = NOW()
-- WHERE project_id = (
--     SELECT project_id
--     FROM projects
--     WHERE project_name = 'enterprise_application'
-- );
--
-- COMMIT;

COMMIT;
