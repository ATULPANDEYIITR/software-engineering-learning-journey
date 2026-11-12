-- ============================================================
-- PACKAGE MANAGEMENT: DEPENDENCY MANAGEMENT AND VERSIONING
-- PostgreSQL 15+
--
-- Models:
-- Registries, packages, semantic versions, dependencies,
-- version constraints, installations, lockfiles, security
-- advisories, installation policies and audit records.
--
-- All package-management objects are isolated in this schema.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS package_management;

SET search_path TO package_management, public;

-- ------------------------------------------------------------
-- 1. ENUMERATED DOMAIN STATES
-- ------------------------------------------------------------

CREATE TYPE package_status AS ENUM (
    'available',
    'deprecated',
    'withdrawn'
);

CREATE TYPE installation_status AS ENUM (
    'planned',
    'installed',
    'failed',
    'removed'
);

CREATE TYPE dependency_type AS ENUM (
    'runtime',
    'development',
    'optional',
    'peer'
);

CREATE TYPE advisory_severity AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- ------------------------------------------------------------
-- 2. SEMANTIC VERSIONING
-- ------------------------------------------------------------

CREATE TABLE semantic_versions (
    version_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    major INTEGER NOT NULL CHECK (major >= 0),
    minor INTEGER NOT NULL CHECK (minor >= 0),
    patch INTEGER NOT NULL CHECK (patch >= 0),

    version_string TEXT GENERATED ALWAYS AS (
        major::TEXT || '.' ||
        minor::TEXT || '.' ||
        patch::TEXT
    ) STORED,

    UNIQUE (major, minor, patch)
);

-- ------------------------------------------------------------
-- 3. PACKAGE REGISTRY
-- ------------------------------------------------------------

CREATE TABLE registries (
    registry_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    registry_name VARCHAR(100) NOT NULL UNIQUE,
    registry_url TEXT NOT NULL,
    is_trusted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (registry_name <> ''),
    CHECK (registry_url ~ '^https?://')
);

CREATE TABLE packages (
    package_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    registry_id BIGINT NOT NULL
        REFERENCES registries(registry_id),

    package_name VARCHAR(100) NOT NULL,

    description TEXT,

    maintainer VARCHAR(150) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (registry_id, package_name),

    CHECK (
        package_name ~ '^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}$'
    )
);

CREATE TABLE package_releases (
    release_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    package_id BIGINT NOT NULL
        REFERENCES packages(package_id),

    version_id BIGINT NOT NULL
        REFERENCES semantic_versions(version_id),

    release_status package_status NOT NULL DEFAULT 'available',

    checksum CHAR(64) NOT NULL,

    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    minimum_runtime_version VARCHAR(50),

    UNIQUE (package_id, version_id),

    CHECK (checksum ~ '^[a-f0-9]{64}$')
);

CREATE INDEX idx_package_releases_lookup
    ON package_releases(package_id, version_id);

CREATE INDEX idx_package_release_status
    ON package_releases(release_status, published_at DESC);

-- ------------------------------------------------------------
-- 4. DEPENDENCY RELATIONSHIPS
-- ------------------------------------------------------------

CREATE TABLE package_dependencies (
    dependency_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_id BIGINT NOT NULL
        REFERENCES package_releases(release_id)
        ON DELETE CASCADE,

    dependency_package_id BIGINT NOT NULL
        REFERENCES packages(package_id),

    version_constraint VARCHAR(200) NOT NULL,

    dependency_category dependency_type NOT NULL
        DEFAULT 'runtime',

    UNIQUE (
        release_id,
        dependency_package_id,
        dependency_category
    ),

    CHECK (version_constraint <> '')
);

CREATE INDEX idx_dependencies_release
    ON package_dependencies(release_id);

CREATE INDEX idx_dependencies_package
    ON package_dependencies(dependency_package_id);

-- ------------------------------------------------------------
-- 5. PROJECTS AND PACKAGE INSTALLATIONS
-- ------------------------------------------------------------

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    project_name VARCHAR(150) NOT NULL UNIQUE,

    environment VARCHAR(30) NOT NULL
        CHECK (
            environment IN (
                'development',
                'testing',
                'staging',
                'production'
            )
        ),

    owner_name VARCHAR(150) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE package_installations (
    installation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    release_id BIGINT NOT NULL
        REFERENCES package_releases(release_id),

    status installation_status NOT NULL DEFAULT 'planned',

    installed_at TIMESTAMPTZ,

    installed_by VARCHAR(150) NOT NULL,

    UNIQUE (project_id, release_id),

    CHECK (
        (status = 'installed' AND installed_at IS NOT NULL)
        OR
        (status <> 'installed' AND installed_at IS NULL)
    )
);

CREATE INDEX idx_installations_project
    ON package_installations(project_id, status);

-- ------------------------------------------------------------
-- 6. SECURITY ADVISORIES
-- ------------------------------------------------------------

CREATE TABLE security_advisories (
    advisory_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    package_id BIGINT NOT NULL
        REFERENCES packages(package_id),

    affected_version_constraint VARCHAR(200) NOT NULL,

    severity advisory_severity NOT NULL,

    advisory_reference VARCHAR(200) NOT NULL UNIQUE,

    description TEXT NOT NULL,

    published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (affected_version_constraint <> '')
);

CREATE INDEX idx_advisory_package_severity
    ON security_advisories(package_id, severity);

-- ------------------------------------------------------------
-- 7. INSTALLATION POLICIES
-- ------------------------------------------------------------

CREATE TABLE installation_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    policy_name VARCHAR(100) NOT NULL,

    allow_deprecated BOOLEAN NOT NULL DEFAULT FALSE,

    allow_vulnerable BOOLEAN NOT NULL DEFAULT FALSE,

    allow_downgrades BOOLEAN NOT NULL DEFAULT FALSE,

    require_trusted_registry BOOLEAN NOT NULL DEFAULT TRUE,

    maximum_package_count INTEGER NOT NULL DEFAULT 100,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (project_id, policy_name),

    CHECK (maximum_package_count > 0)
);

-- ------------------------------------------------------------
-- 8. INSTALLATION AUDIT LOG
-- ------------------------------------------------------------

CREATE TABLE installation_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    package_id BIGINT
        REFERENCES packages(package_id),

    action VARCHAR(40) NOT NULL,

    outcome VARCHAR(20) NOT NULL,

    actor VARCHAR(150) NOT NULL,

    details JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (outcome IN ('success', 'rejected', 'failed'))
);

CREATE INDEX idx_installation_audit_project_date
    ON installation_audit(project_id, occurred_at DESC);

-- ------------------------------------------------------------
-- 9. SEMANTIC VERSION COMPARISON
-- ------------------------------------------------------------

CREATE FUNCTION version_compare(
    p_major INTEGER,
    p_minor INTEGER,
    p_patch INTEGER,
    q_major INTEGER,
    q_minor INTEGER,
    q_patch INTEGER
)
RETURNS INTEGER
LANGUAGE SQL
IMMUTABLE
STRICT
AS $$
    SELECT CASE
        WHEN (p_major, p_minor, p_patch) >
             (q_major, q_minor, q_patch) THEN 1

        WHEN (p_major, p_minor, p_patch) <
             (q_major, q_minor, q_patch) THEN -1

        ELSE 0
    END;
$$;

-- ------------------------------------------------------------
-- 10. VERSION CONSTRAINT EVALUATION
--
-- Supported examples:
-- 1.2.3
-- >=1.0.0
-- <2.0.0
-- ^1.2.0
-- ~1.2.0
-- >=1.0.0,<2.0.0
-- *
-- ------------------------------------------------------------

CREATE FUNCTION version_satisfies(
    p_major INTEGER,
    p_minor INTEGER,
    p_patch INTEGER,
    p_constraint TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    v_expression TEXT;
    v_match TEXT[];
    v_operator TEXT;
    v_major INTEGER;
    v_minor INTEGER;
    v_patch INTEGER;
    v_result BOOLEAN;
    v_upper_major INTEGER;
    v_upper_minor INTEGER;
    v_upper_patch INTEGER;
BEGIN
    IF p_major < 0 OR p_minor < 0 OR p_patch < 0 THEN
        RAISE EXCEPTION 'Invalid version components';
    END IF;

    IF p_constraint = '*' THEN
        RETURN TRUE;
    END IF;

    IF p_constraint = '' THEN
        RAISE EXCEPTION 'Empty version constraint';
    END IF;

    FOREACH v_expression IN ARRAY string_to_array(
        p_constraint, ','
    )
    LOOP
        v_expression := btrim(v_expression);

        v_match := regexp_match(
            v_expression,
            '^(>=|<=|>|<|=|\^|~)?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$'
        );

        IF v_match IS NULL THEN
            RAISE EXCEPTION
                'Invalid version constraint: %',
                v_expression;
        END IF;

        v_operator := COALESCE(v_match[1], '=');
        v_major := v_match[2]::INTEGER;
        v_minor := v_match[3]::INTEGER;
        v_patch := v_match[4]::INTEGER;

        v_result := CASE v_operator
            WHEN '=' THEN
                (p_major, p_minor, p_patch) =
                (v_major, v_minor, v_patch)

            WHEN '>' THEN
                (p_major, p_minor, p_patch) >
                (v_major, v_minor, v_patch)

            WHEN '<' THEN
                (p_major, p_minor, p_patch) <
                (v_major, v_minor, v_patch)

            WHEN '>=' THEN
                (p_major, p_minor, p_patch) >=
                (v_major, v_minor, v_patch)

            WHEN '<=' THEN
                (p_major, p_minor, p_patch) <=
                (v_major, v_minor, v_patch)

            WHEN '^' THEN
                CASE
                    WHEN v_major > 0 THEN
                        (p_major, p_minor, p_patch) >=
                            (v_major, v_minor, v_patch)
                        AND
                        (p_major, p_minor, p_patch) <
                            (v_major + 1, 0, 0)

                    WHEN v_minor > 0 THEN
                        (p_major, p_minor, p_patch) >=
                            (v_major, v_minor, v_patch)
                        AND
                        (p_major, p_minor, p_patch) <
                            (0, v_minor + 1, 0)

                    ELSE
                        (p_major, p_minor, p_patch) >=
                            (v_major, v_minor, v_patch)
                        AND
                        (p_major, p_minor, p_patch) <
                            (0, 0, v_patch + 1)
                END

            WHEN '~' THEN
                (p_major, p_minor, p_patch) >=
                    (v_major, v_minor, v_patch)
                AND
                (p_major, p_minor, p_patch) <
                    (v_major, v_minor + 1, 0)

            ELSE FALSE
        END;

        IF NOT v_result THEN
            RETURN FALSE;
        END IF;
    END LOOP;

    RETURN TRUE;
END;
$$;

-- ------------------------------------------------------------
-- 11. RELEASE INTEGRITY TRIGGER
--
-- A package cannot depend on itself.
-- ------------------------------------------------------------

CREATE FUNCTION validate_package_dependency()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_parent_package BIGINT;
BEGIN
    SELECT package_id
    INTO v_parent_package
    FROM package_releases
    WHERE release_id = NEW.release_id;

    IF v_parent_package IS NULL THEN
        RAISE EXCEPTION 'Unknown parent release';
    END IF;

    IF v_parent_package = NEW.dependency_package_id THEN
        RAISE EXCEPTION
            'A package cannot directly depend on itself';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_package_dependency
BEFORE INSERT OR UPDATE ON package_dependencies
FOR EACH ROW
EXECUTE FUNCTION validate_package_dependency();

-- ------------------------------------------------------------
-- 12. INSTALLATION STATE VALIDATION TRIGGER
-- ------------------------------------------------------------

CREATE FUNCTION validate_installation_release()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_status package_status;
BEGIN
    IF NEW.status = 'installed' THEN
        SELECT release_status
        INTO v_status
        FROM package_releases
        WHERE release_id = NEW.release_id;

        IF v_status IS DISTINCT FROM 'available' THEN
            RAISE EXCEPTION
                'Only available package releases can be installed';
        END IF;

        IF NEW.installed_at IS NULL THEN
            NEW.installed_at := NOW();
        END IF;
    ELSE
        NEW.installed_at := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_installation
BEFORE INSERT OR UPDATE ON package_installations
FOR EACH ROW
EXECUTE FUNCTION validate_installation_release();

-- ------------------------------------------------------------
-- 13. INSTALLATION ELIGIBILITY FUNCTION
-- ------------------------------------------------------------

CREATE FUNCTION check_package_eligibility(
    p_project_id BIGINT,
    p_release_id BIGINT
)
RETURNS TABLE (
    eligible BOOLEAN,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_package_id BIGINT;
    v_status package_status;
    v_registry_trusted BOOLEAN;
    v_policy installation_policies%ROWTYPE;
    v_existing_count BIGINT;
    v_severe_advisory BOOLEAN;
BEGIN
    SELECT p.package_id, r.release_status, rg.is_trusted
    INTO v_package_id, v_status, v_registry_trusted
    FROM package_releases r
    JOIN packages p ON p.package_id = r.package_id
    JOIN registries rg ON rg.registry_id = p.registry_id
    WHERE r.release_id = p_release_id;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'Release does not exist';
        RETURN;
    END IF;

    SELECT *
    INTO v_policy
    FROM installation_policies
    WHERE project_id = p_project_id
      AND active = TRUE
    ORDER BY policy_id
    LIMIT 1;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'No active installation policy';
        RETURN;
    END IF;

    IF v_status = 'withdrawn' THEN
        RETURN QUERY SELECT FALSE, 'Release is withdrawn';
        RETURN;
    END IF;

    IF v_status = 'deprecated'
       AND NOT v_policy.allow_deprecated THEN
        RETURN QUERY SELECT FALSE, 'Deprecated release prohibited';
        RETURN;
    END IF;

    IF v_policy.require_trusted_registry
       AND NOT v_registry_trusted THEN
        RETURN QUERY SELECT FALSE, 'Untrusted registry';
        RETURN;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM security_advisories a
        JOIN package_releases r ON r.package_id = a.package_id
        JOIN semantic_versions v ON v.version_id = r.version_id
        WHERE r.release_id = p_release_id
          AND a.package_id = v_package_id
          AND version_satisfies(
              v.major,
              v.minor,
              v.patch,
              a.affected_version_constraint
          )
          AND a.severity IN ('high', 'critical')
    )
    INTO v_severe_advisory;

    IF v_severe_advisory AND NOT v_policy.allow_vulnerable THEN
        RETURN QUERY SELECT FALSE, 'High or critical vulnerability';
        RETURN;
    END IF;

    SELECT COUNT(DISTINCT p.package_id)
    INTO v_existing_count
    FROM package_installations i
    JOIN package_releases r ON r.release_id = i.release_id
    JOIN packages p ON p.package_id = r.package_id
    WHERE i.project_id = p_project_id
      AND i.status = 'installed'
      AND p.package_id <> v_package_id;

    IF NOT EXISTS (
        SELECT 1
        FROM package_installations i
        JOIN package_releases r ON r.release_id = i.release_id
        WHERE i.project_id = p_project_id
          AND r.package_id = v_package_id
          AND i.status = 'installed'
    ) AND v_existing_count >= v_policy.maximum_package_count THEN
        RETURN QUERY SELECT FALSE, 'Package count limit exceeded';
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'Eligible under active policy';
END;
$$;

-- ------------------------------------------------------------
-- 14. PACKAGE INSTALLATION PROCEDURE
--
-- Serializes installations for the same project.
-- Performs policy checks and records the operation.
-- ------------------------------------------------------------

CREATE PROCEDURE install_package(
    p_project_id BIGINT,
    p_release_id BIGINT,
    p_actor VARCHAR(150)
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_eligible BOOLEAN;
    v_reason TEXT;
    v_package_id BIGINT;
    v_existing_release BIGINT;
    v_existing_version BIGINT;
    v_new_version BIGINT;
    v_allow_downgrade BOOLEAN;
BEGIN
    PERFORM 1
    FROM projects
    WHERE project_id = p_project_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Project not found';
    END IF;

    SELECT package_id, version_id
    INTO v_package_id, v_new_version
    FROM package_releases
    WHERE release_id = p_release_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Package release not found';
    END IF;

    SELECT i.release_id, r.version_id
    INTO v_existing_release, v_existing_version
    FROM package_installations i
    JOIN package_releases r ON r.release_id = i.release_id
    WHERE i.project_id = p_project_id
      AND r.package_id = v_package_id
      AND i.status = 'installed'
    FOR UPDATE OF i;

    IF FOUND THEN
        SELECT allow_downgrades
        INTO v_allow_downgrade
        FROM installation_policies
        WHERE project_id = p_project_id
          AND active = TRUE
        ORDER BY policy_id
        LIMIT 1;

        IF NOT COALESCE(v_allow_downgrade, FALSE)
           AND EXISTS (
               SELECT 1
               FROM semantic_versions new_version
               JOIN semantic_versions old_version
                 ON old_version.version_id = v_existing_version
               WHERE new_version.version_id = v_new_version
                 AND (
                    new_version.major,
                    new_version.minor,
                    new_version.patch
                 ) < (
                    old_version.major,
                    old_version.minor,
                    old_version.patch
                 )
           ) THEN
            RAISE EXCEPTION 'Downgrade prohibited by policy';
        END IF;

        UPDATE package_installations
        SET status = 'removed',
            installed_at = NULL
        WHERE project_id = p_project_id
          AND release_id = v_existing_release;
    END IF;

    SELECT e.eligible, e.reason
    INTO v_eligible, v_reason
    FROM check_package_eligibility(
        p_project_id,
        p_release_id
    ) e;

    IF NOT v_eligible THEN
        INSERT INTO installation_audit (
            project_id,
            package_id,
            action,
            outcome,
            actor,
            details
        )
        VALUES (
            p_project_id,
            v_package_id,
            'install',
            'rejected',
            p_actor,
            jsonb_build_object('reason', v_reason)
        );

        RAISE EXCEPTION 'Installation rejected: %', v_reason;
    END IF;

    INSERT INTO package_installations (
        project_id,
        release_id,
        status,
        installed_by
    )
    VALUES (
        p_project_id,
        p_release_id,
        'installed',
        p_actor
    )
    ON CONFLICT (project_id, release_id)
    DO UPDATE SET
        status = 'installed',
        installed_at = NOW(),
        installed_by = EXCLUDED.installed_by;

    INSERT INTO installation_audit (
        project_id,
        package_id,
        action,
        outcome,
        actor,
        details
    )
    VALUES (
        p_project_id,
        v_package_id,
        'install',
        'success',
        p_actor,
        jsonb_build_object(
            'release_id', p_release_id,
            'reason', v_reason
        )
    );
END;
$$;

-- ------------------------------------------------------------
-- 15. DEPENDENCY REPORTING VIEW
-- ------------------------------------------------------------

CREATE VIEW package_dependency_report AS
SELECT
    parent.package_name AS package_name,
    version.version_string AS package_version,
    dependency.package_name AS dependency_name,
    dependency_record.version_constraint,
    dependency_record.dependency_category

FROM package_dependencies dependency_record

JOIN package_releases release
    ON release.release_id = dependency_record.release_id

JOIN packages parent
    ON parent.package_id = release.package_id

JOIN semantic_versions version
    ON version.version_id = release.version_id

JOIN packages dependency
    ON dependency.package_id =
       dependency_record.dependency_package_id;

-- ------------------------------------------------------------
-- 16. PROJECT INVENTORY VIEW
-- ------------------------------------------------------------

CREATE VIEW project_package_inventory AS
SELECT
    project.project_id,
    project.project_name,
    project.environment,
    package.package_name,
    version.version_string,
    installation.status,
    installation.installed_at,
    installation.installed_by

FROM package_installations installation

JOIN projects project
    ON project.project_id = installation.project_id

JOIN package_releases release
    ON release.release_id = installation.release_id

JOIN packages package
    ON package.package_id = release.package_id

JOIN semantic_versions version
    ON version.version_id = release.version_id;

-- ------------------------------------------------------------
-- 17. SAMPLE DATA
-- ------------------------------------------------------------

INSERT INTO registries (
    registry_name,
    registry_url,
    is_trusted
)
VALUES
    ('Internal Registry', 'https://packages.example.internal', TRUE),
    ('Community Registry', 'https://packages.example.org', FALSE);

INSERT INTO semantic_versions (major, minor, patch)
VALUES
    (1, 0, 0),
    (1, 2, 0),
    (2, 0, 0),
    (1, 1, 0),
    (0, 9, 0);

INSERT INTO packages (
    registry_id,
    package_name,
    description,
    maintainer
)
VALUES
    (
        1,
        'core-engine',
        'Shared application runtime',
        'Platform Team'
    ),
    (
        1,
        'database-driver',
        'Database connectivity library',
        'Data Engineering'
    ),
    (
        1,
        'api-framework',
        'HTTP application framework',
        'Backend Team'
    ),
    (
        2,
        'legacy-helper',
        'Legacy compatibility package',
        'Community Maintainers'
    );

INSERT INTO package_releases (
    package_id,
    version_id,
    release_status,
    checksum
)
VALUES
    (1, 1, 'available', repeat('a', 64)),
    (1, 2, 'available', repeat('b', 64)),
    (1, 3, 'available', repeat('c', 64)),
    (2, 1, 'available', repeat('d', 64)),
    (2, 3, 'available', repeat('e', 64)),
    (3, 1, 'available', repeat('f', 64)),
    (3, 4, 'available', repeat('1', 64)),
    (4, 5, 'deprecated', repeat('2', 64));

-- Dependency records:
-- database-driver 1.0.0 requires core-engine ^1.0.0.
-- database-driver 2.0.0 requires core-engine ^2.0.0.
-- api-framework 1.0.0 requires core-engine and database-driver.
-- api-framework 1.1.0 has the same compatibility requirements.

INSERT INTO package_dependencies (
    release_id,
    dependency_package_id,
    version_constraint,
    dependency_category
)
VALUES
    (4, 1, '^1.0.0', 'runtime'),
    (5, 1, '^2.0.0', 'runtime'),
    (6, 1, '^1.0.0', 'runtime'),
    (6, 2, '^1.0.0', 'runtime'),
    (7, 1, '^1.0.0', 'runtime'),
    (7, 2, '^1.0.0', 'runtime');

INSERT INTO projects (
    project_name,
    environment,
    owner_name
)
VALUES
    ('Payment API', 'production', 'Payments Team'),
    ('Analytics Platform', 'development', 'Analytics Team');

INSERT INTO installation_policies (
    project_id,
    policy_name,
    allow_deprecated,
    allow_vulnerable,
    allow_downgrades,
    require_trusted_registry,
    maximum_package_count
)
VALUES
    (1, 'Production Strict', FALSE, FALSE, FALSE, TRUE, 50),
    (2, 'Development Standard', TRUE, FALSE, TRUE, FALSE, 100);

INSERT INTO security_advisories (
    package_id,
    affected_version_constraint,
    severity,
    advisory_reference,
    description
)
VALUES
    (
        2,
        '^1.0.0',
        'high',
        'ADV-2026-001',
        'Known vulnerability in database driver 1.x'
    ),
    (
        4,
        '*',
        'medium',
        'ADV-2026-002',
        'Legacy compatibility package requires review'
    );

-- ------------------------------------------------------------
-- 18. RETRIEVAL QUERIES
-- ------------------------------------------------------------

-- List available versions of each package.

SELECT
    p.package_name,
    v.version_string,
    r.release_status,
    r.checksum
FROM package_releases r
JOIN packages p ON p.package_id = r.package_id
JOIN semantic_versions v ON v.version_id = r.version_id
ORDER BY p.package_name, v.major DESC, v.minor DESC, v.patch DESC;

-- Display dependency relationships.

SELECT *
FROM package_dependency_report
ORDER BY package_name, dependency_name;

-- ------------------------------------------------------------
-- 19. VERSION CONSTRAINT TESTS
-- ------------------------------------------------------------

SELECT
    '1.2.0' AS version,
    '^1.0.0' AS constraint,
    version_satisfies(1, 2, 0, '^1.0.0') AS matches;

SELECT
    version_satisfies(2, 0, 0, '^1.0.0')
        AS major_upgrade_rejected;

SELECT
    version_satisfies(1, 2, 0, '>=1.0.0,<2.0.0')
        AS range_matches;

SELECT
    version_satisfies(1, 3, 0, '~1.2.0')
        AS minor_upgrade_rejected;

-- ------------------------------------------------------------
-- 20. DEPENDENCY AGGREGATION
-- ------------------------------------------------------------

SELECT
    package_name,
    COUNT(*) AS dependency_count,
    ARRAY_AGG(dependency_name ORDER BY dependency_name)
        AS dependencies
FROM package_dependency_report
GROUP BY package_name
ORDER BY package_name;

-- ------------------------------------------------------------
-- 21. SECURITY REPORT
-- ------------------------------------------------------------

SELECT
    p.package_name,
    v.version_string,
    a.advisory_reference,
    a.severity,
    a.description
FROM security_advisories a
JOIN packages p ON p.package_id = a.package_id
JOIN package_releases r ON r.package_id = p.package_id
JOIN semantic_versions v ON v.version_id = r.version_id
WHERE version_satisfies(
    v.major,
    v.minor,
    v.patch,
    a.affected_version_constraint
)
ORDER BY a.severity DESC, p.package_name;

-- ------------------------------------------------------------
-- 22. ELIGIBILITY EVALUATION
-- ------------------------------------------------------------

SELECT *
FROM check_package_eligibility(1, 1);

SELECT *
FROM check_package_eligibility(1, 4);

-- ------------------------------------------------------------
-- 23. SUCCESSFUL INSTALLATION TRANSACTION
--
-- Installs core-engine 1.2.0.
-- The project row lock serializes installation operations
-- for the same project.
-- ------------------------------------------------------------

DO $$
BEGIN
    CALL install_package(
        1,
        2,
        'deployment-service'
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Installation failed: %', SQLERRM;
END;
$$;

-- ------------------------------------------------------------
-- 24. REJECTED INSTALLATION
--
-- The database-driver 1.0.0 release is vulnerable.
-- The production policy rejects it.
-- ------------------------------------------------------------

DO $$
BEGIN
    CALL install_package(
        1,
        4,
        'deployment-service'
    );
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Expected rejection: %', SQLERRM;
END;
$$;

-- ------------------------------------------------------------
-- 25. INSTALLATION INVENTORY
-- ------------------------------------------------------------

SELECT *
FROM project_package_inventory
ORDER BY project_name, package_name;

-- ------------------------------------------------------------
-- 26. AUDIT REPORT
-- ------------------------------------------------------------

SELECT
    project.project_name,
    audit.action,
    audit.outcome,
    audit.actor,
    audit.details,
    audit.occurred_at
FROM installation_audit audit
JOIN projects project
    ON project.project_id = audit.project_id
ORDER BY audit.occurred_at DESC;

-- ------------------------------------------------------------
-- 27. WORKFLOW AGGREGATION
-- ------------------------------------------------------------

SELECT
    project.project_name,
    COUNT(*) FILTER (
        WHERE installation.status = 'installed'
    ) AS installed_packages,

    COUNT(*) FILTER (
        WHERE installation.status = 'failed'
    ) AS failed_installations,

    COUNT(*) FILTER (
        WHERE installation.status = 'removed'
    ) AS removed_packages

FROM package_installations installation

JOIN projects project
    ON project.project_id = installation.project_id

GROUP BY project.project_id, project.project_name
ORDER BY project.project_name;

-- ------------------------------------------------------------
-- 28. DEMONSTRATE INVALID SELF-DEPENDENCY
--
-- This statement is isolated in an exception-handling block.
-- ------------------------------------------------------------

DO $$
BEGIN
    INSERT INTO package_dependencies (
        release_id,
        dependency_package_id,
        version_constraint,
        dependency_category
    )
    VALUES (
        1,
        1,
        '^1.0.0',
        'runtime'
    );

EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Expected dependency rejection: %', SQLERRM;
END;
$$;

COMMIT;

-- Production considerations:
-- 1. Use a cryptographically verified package artifact digest.
-- 2. Restrict registry and policy modification permissions.
-- 3. Add recursive graph validation before installation.
-- 4. Use immutable release records.
-- 5. Enforce environment-specific advisory policies.
-- 6. Execute installation procedures with restricted privileges.
-- 7. Do not treat a checksum alone as proof of publisher identity.
