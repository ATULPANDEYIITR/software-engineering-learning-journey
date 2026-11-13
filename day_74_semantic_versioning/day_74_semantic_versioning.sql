-- ============================================================
-- SEMANTIC VERSIONING 2.0.0
-- PostgreSQL 15+
--
-- Release management and dependency compatibility database.
--
-- Models:
-- Projects -> Releases -> Release Changes
-- Projects -> Dependencies -> Compatibility Constraints
-- Releases -> Validation -> Publication -> Release History
--
-- All version precedence decisions use SemVer 2.0.0 rules.
-- Build metadata does not affect version precedence.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS semver;

SET search_path TO semver, public;

-- ------------------------------------------------------------
-- 1. ENUM TYPES
-- ------------------------------------------------------------

CREATE TYPE change_type AS ENUM (
    'major',
    'minor',
    'patch'
);

CREATE TYPE release_state AS ENUM (
    'draft',
    'validated',
    'published',
    'rejected',
    'deprecated'
);

CREATE TYPE change_category AS ENUM (
    'breaking',
    'feature',
    'bug_fix',
    'documentation',
    'security',
    'performance',
    'maintenance'
);

CREATE TYPE validation_status AS ENUM (
    'passed',
    'failed',
    'warning'
);

-- ------------------------------------------------------------
-- 2. PROJECTS
-- ------------------------------------------------------------

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_key VARCHAR(80) NOT NULL UNIQUE,
    project_name VARCHAR(200) NOT NULL,
    description TEXT,
    repository_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_project_key
        CHECK (project_key ~ '^[a-z0-9][a-z0-9_-]{1,79}$'),

    CONSTRAINT valid_project_name
        CHECK (length(trim(project_name)) > 0)
);

-- ------------------------------------------------------------
-- 3. VERSION PARSING AND VALIDATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION is_valid_semver(
    p_version TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    RETURN p_version ~
        '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?(\+([0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*))?$'
    AND NOT EXISTS (
        SELECT 1
        FROM regexp_split_to_table(
            COALESCE(
                substring(
                    p_version
                    FROM '-([^+]+)'
                ),
                ''
            ),
            '\.'
        ) AS identifiers(identifier)
        WHERE
            identifier ~ '^[0-9]+$'
            AND length(identifier) > 1
            AND left(identifier, 1) = '0'
    );
END;
$$;

-- Extract the numeric core components.

CREATE OR REPLACE FUNCTION semver_major(
    p_version TEXT
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    IF NOT is_valid_semver(p_version) THEN
        RAISE EXCEPTION 'Invalid semantic version: %', p_version;
    END IF;

    RETURN split_part(p_version, '.', 1)::NUMERIC;
END;
$$;

CREATE OR REPLACE FUNCTION semver_minor(
    p_version TEXT
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    IF NOT is_valid_semver(p_version) THEN
        RAISE EXCEPTION 'Invalid semantic version: %', p_version;
    END IF;

    RETURN split_part(p_version, '.', 2)::NUMERIC;
END;
$$;

CREATE OR REPLACE FUNCTION semver_patch(
    p_version TEXT
)
RETURNS NUMERIC
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
BEGIN
    IF NOT is_valid_semver(p_version) THEN
        RAISE EXCEPTION 'Invalid semantic version: %', p_version;
    END IF;

    RETURN split_part(
        split_part(p_version, '-', 1),
        '.',
        3
    )::NUMERIC;
END;
$$;

-- Compare prerelease identifiers.
-- Numeric identifiers are compared numerically.
-- Numeric identifiers have lower precedence than nonnumeric ones.

CREATE OR REPLACE FUNCTION semver_compare_identifiers(
    p_left TEXT,
    p_right TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    left_numeric BOOLEAN;
    right_numeric BOOLEAN;
BEGIN
    left_numeric := p_left ~ '^[0-9]+$';
    right_numeric := p_right ~ '^[0-9]+$';

    IF left_numeric AND right_numeric THEN
        IF length(p_left) < length(p_right) THEN
            RETURN -1;
        ELSIF length(p_left) > length(p_right) THEN
            RETURN 1;
        END IF;

        IF p_left < p_right THEN
            RETURN -1;
        ELSIF p_left > p_right THEN
            RETURN 1;
        END IF;

        RETURN 0;
    END IF;

    IF left_numeric THEN
        RETURN -1;
    ELSIF right_numeric THEN
        RETURN 1;
    END IF;

    IF p_left < p_right THEN
        RETURN -1;
    ELSIF p_left > p_right THEN
        RETURN 1;
    END IF;

    RETURN 0;
END;
$$;

-- SemVer precedence comparison.
-- Build metadata is deliberately ignored.

CREATE OR REPLACE FUNCTION semver_compare(
    p_left TEXT,
    p_right TEXT
)
RETURNS INTEGER
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    left_pre TEXT;
    right_pre TEXT;
    left_ids TEXT[];
    right_ids TEXT[];
    left_count INTEGER;
    right_count INTEGER;
    comparison INTEGER;
    i INTEGER;
BEGIN
    IF NOT is_valid_semver(p_left)
       OR NOT is_valid_semver(p_right) THEN
        RAISE EXCEPTION 'Cannot compare invalid versions';
    END IF;

    IF semver_major(p_left) <> semver_major(p_right) THEN
        RETURN CASE
            WHEN semver_major(p_left) < semver_major(p_right)
            THEN -1 ELSE 1 END;
    END IF;

    IF semver_minor(p_left) <> semver_minor(p_right) THEN
        RETURN CASE
            WHEN semver_minor(p_left) < semver_minor(p_right)
            THEN -1 ELSE 1 END;
    END IF;

    IF semver_patch(p_left) <> semver_patch(p_right) THEN
        RETURN CASE
            WHEN semver_patch(p_left) < semver_patch(p_right)
            THEN -1 ELSE 1 END;
    END IF;

    left_pre := substring(p_left FROM '-([^+]+)');
    right_pre := substring(p_right FROM '-([^+]+)');

    IF left_pre IS NULL AND right_pre IS NULL THEN
        RETURN 0;
    END IF;

    IF left_pre IS NULL THEN
        RETURN 1;
    END IF;

    IF right_pre IS NULL THEN
        RETURN -1;
    END IF;

    left_ids := string_to_array(left_pre, '.');
    right_ids := string_to_array(right_pre, '.');

    left_count := cardinality(left_ids);
    right_count := cardinality(right_ids);

    FOR i IN 1..LEAST(left_count, right_count) LOOP
        comparison := semver_compare_identifiers(
            left_ids[i],
            right_ids[i]
        );

        IF comparison <> 0 THEN
            RETURN comparison;
        END IF;
    END LOOP;

    IF left_count < right_count THEN
        RETURN -1;
    ELSIF left_count > right_count THEN
        RETURN 1;
    END IF;

    RETURN 0;
END;
$$;

-- ------------------------------------------------------------
-- 4. RELEASES
-- ------------------------------------------------------------

CREATE TABLE releases (
    release_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    version VARCHAR(300) NOT NULL,

    major NUMERIC(20, 0) NOT NULL,
    minor NUMERIC(20, 0) NOT NULL,
    patch NUMERIC(20, 0) NOT NULL,

    change_kind change_type NOT NULL,

    state release_state NOT NULL DEFAULT 'draft',

    description TEXT NOT NULL,

    tests_passed BOOLEAN NOT NULL DEFAULT FALSE,
    documentation_updated BOOLEAN NOT NULL DEFAULT FALSE,
    migration_notes BOOLEAN NOT NULL DEFAULT FALSE,

    production_release BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ,

    CONSTRAINT valid_release_version
        CHECK (is_valid_semver(version)),

    CONSTRAINT unique_project_version
        UNIQUE (project_id, version),

    CONSTRAINT nonnegative_version_components
        CHECK (
            major >= 0 AND
            minor >= 0 AND
            patch >= 0
        ),

    CONSTRAINT valid_release_description
        CHECK (length(trim(description)) > 0),

    CONSTRAINT publication_timestamp_consistency
        CHECK (
            (state = 'published' AND published_at IS NOT NULL)
            OR
            (state <> 'published' AND published_at IS NULL)
        )
);

CREATE INDEX idx_releases_project
    ON releases(project_id, major, minor, patch);

CREATE INDEX idx_releases_state
    ON releases(state, created_at DESC);

CREATE INDEX idx_releases_published
    ON releases(project_id, published_at DESC)
    WHERE state = 'published';

-- Populate numeric components automatically.

CREATE OR REPLACE FUNCTION populate_release_components()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT is_valid_semver(NEW.version) THEN
        RAISE EXCEPTION 'Invalid version: %', NEW.version;
    END IF;

    NEW.major := semver_major(NEW.version);
    NEW.minor := semver_minor(NEW.version);
    NEW.patch := semver_patch(NEW.version);

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_release_components
BEFORE INSERT OR UPDATE OF version
ON releases
FOR EACH ROW
EXECUTE FUNCTION populate_release_components();

-- ------------------------------------------------------------
-- 5. RELEASE CHANGELOG
-- ------------------------------------------------------------

CREATE TABLE release_changes (
    change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_id BIGINT NOT NULL
        REFERENCES releases(release_id),

    category change_category NOT NULL,

    title VARCHAR(250) NOT NULL,
    details TEXT NOT NULL,

    breaking BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT valid_change_title
        CHECK (length(trim(title)) > 0)
);

CREATE INDEX idx_release_changes_release
    ON release_changes(release_id, category);

-- ------------------------------------------------------------
-- 6. DEPENDENCIES AND CONSTRAINTS
-- ------------------------------------------------------------

CREATE TABLE dependencies (
    dependency_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    consumer_project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    provider_project_id BIGINT NOT NULL
        REFERENCES projects(project_id),

    version_operator VARCHAR(2) NOT NULL,

    required_version VARCHAR(300) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT different_projects
        CHECK (consumer_project_id <> provider_project_id),

    CONSTRAINT valid_operator
        CHECK (
            version_operator IN ('=', '>', '>=', '<', '<=')
        ),

    CONSTRAINT valid_required_version
        CHECK (is_valid_semver(required_version)),

    CONSTRAINT unique_dependency
        UNIQUE (
            consumer_project_id,
            provider_project_id,
            version_operator,
            required_version
        )
);

CREATE INDEX idx_dependencies_consumer
    ON dependencies(consumer_project_id);

CREATE INDEX idx_dependencies_provider
    ON dependencies(provider_project_id);

-- Evaluate a version constraint.

CREATE OR REPLACE FUNCTION version_satisfies(
    p_candidate TEXT,
    p_operator TEXT,
    p_required TEXT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
IMMUTABLE
STRICT
AS $$
DECLARE
    comparison INTEGER;
BEGIN
    comparison := semver_compare(
        p_candidate,
        p_required
    );

    CASE p_operator
        WHEN '=' THEN RETURN comparison = 0;
        WHEN '>' THEN RETURN comparison > 0;
        WHEN '>=' THEN RETURN comparison >= 0;
        WHEN '<' THEN RETURN comparison < 0;
        WHEN '<=' THEN RETURN comparison <= 0;
        ELSE
            RAISE EXCEPTION
                'Unsupported version operator: %',
                p_operator;
    END CASE;
END;
$$;

-- ------------------------------------------------------------
-- 7. RELEASE VALIDATION HISTORY
-- ------------------------------------------------------------

CREATE TABLE release_validations (
    validation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_id BIGINT NOT NULL
        REFERENCES releases(release_id),

    rule_name VARCHAR(100) NOT NULL,

    status validation_status NOT NULL,

    message TEXT NOT NULL,

    validated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_validations_release
    ON release_validations(release_id, validated_at DESC);

-- ------------------------------------------------------------
-- 8. RELEASE AUDIT
-- ------------------------------------------------------------

CREATE TABLE release_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    release_id BIGINT NOT NULL
        REFERENCES releases(release_id),

    old_state release_state,
    new_state release_state NOT NULL,

    changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    details TEXT NOT NULL
);

CREATE INDEX idx_release_audit_history
    ON release_audit(release_id, changed_at DESC);

CREATE OR REPLACE FUNCTION audit_release_state()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.state IS DISTINCT FROM NEW.state THEN
        INSERT INTO release_audit (
            release_id,
            old_state,
            new_state,
            details
        )
        VALUES (
            NEW.release_id,
            OLD.state,
            NEW.state,
            'Release state transition'
        );
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_release_audit
AFTER UPDATE OF state
ON releases
FOR EACH ROW
EXECUTE FUNCTION audit_release_state();

-- ------------------------------------------------------------
-- 9. RELEASE GOVERNANCE AND VALIDATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_release(
    p_release_id BIGINT
)
RETURNS TABLE (
    rule_name TEXT,
    status validation_status,
    message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    release_record releases%ROWTYPE;
    change_count INTEGER;
BEGIN
    SELECT *
    INTO release_record
    FROM releases
    WHERE release_id = p_release_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Release % does not exist',
            p_release_id;
    END IF;

    rule_name := 'automated_tests';

    IF release_record.tests_passed THEN
        status := 'passed';
        message := 'Automated tests passed';
    ELSE
        status := 'failed';
        message := 'Automated tests have not passed';
    END IF;

    RETURN NEXT;

    rule_name := 'documentation';

    IF release_record.documentation_updated THEN
        status := 'passed';
        message := 'Documentation is updated';
    ELSE
        status := 'failed';
        message := 'Documentation is incomplete';
    END IF;

    RETURN NEXT;

    rule_name := 'breaking_change_notes';

    SELECT count(*)
    INTO change_count
    FROM release_changes
    WHERE release_id = p_release_id
      AND breaking = TRUE;

    IF change_count = 0 OR release_record.migration_notes THEN
        status := 'passed';
        message := 'Breaking change documentation requirement satisfied';
    ELSE
        status := 'failed';
        message := 'Breaking changes require migration notes';
    END IF;

    RETURN NEXT;

    rule_name := 'production_prerelease';

    IF NOT release_record.production_release
       OR substring(
           release_record.version
           FROM '-([^+]+)'
       ) IS NULL THEN
        status := 'passed';
        message := 'Production release classification is valid';
    ELSE
        status := 'failed';
        message := 'Prerelease cannot be marked as production release';
    END IF;

    RETURN NEXT;

    rule_name := 'major_release_version';

    IF release_record.change_kind <> 'major'
       OR (
           release_record.minor = 0
           AND release_record.patch = 0
       ) THEN
        status := 'passed';
        message := 'Major release version structure is valid';
    ELSE
        status := 'failed';
        message := 'Major release must increment major and reset minor and patch';
    END IF;

    RETURN NEXT;

    rule_name := 'minor_release_version';

    IF release_record.change_kind <> 'minor'
       OR release_record.patch = 0 THEN
        status := 'passed';
        message := 'Minor release version structure is valid';
    ELSE
        status := 'failed';
        message := 'Minor release must reset patch to zero';
    END IF;

    RETURN NEXT;
END;
$$;

-- ------------------------------------------------------------
-- 10. RELEASE ELIGIBILITY
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION release_is_eligible(
    p_release_id BIGINT
)
RETURNS BOOLEAN
LANGUAGE plpgsql
AS $$
DECLARE
    failures INTEGER;
BEGIN
    SELECT count(*)
    INTO failures
    FROM validate_release(p_release_id)
    WHERE status = 'failed';

    RETURN failures = 0;
END;
$$;

-- ------------------------------------------------------------
-- 11. RELEASE PUBLICATION PROCEDURE
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE publish_release(
    p_release_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    release_record releases%ROWTYPE;
    dependency_failure INTEGER;
BEGIN
    -- Lock the release to prevent concurrent publication.
    SELECT *
    INTO release_record
    FROM releases
    WHERE release_id = p_release_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Release does not exist';
    END IF;

    IF release_record.state <> 'draft' THEN
        RAISE EXCEPTION
            'Only draft releases can be published';
    END IF;

    -- Reject prereleases marked for production.
    IF release_record.production_release
       AND substring(
           release_record.version
           FROM '-([^+]+)'
       ) IS NOT NULL THEN
        RAISE EXCEPTION
            'Prerelease cannot be published as production';
    END IF;

    -- Validate release policy.
    IF NOT release_is_eligible(p_release_id) THEN

        INSERT INTO release_validations (
            release_id,
            rule_name,
            status,
            message
        )
        SELECT
            p_release_id,
            rule_name,
            status,
            message
        FROM validate_release(p_release_id);

        UPDATE releases
        SET state = 'rejected'
        WHERE release_id = p_release_id;

        RAISE EXCEPTION
            'Release failed governance validation';
    END IF;

    -- Verify that every dependency has a published compatible release.
    SELECT count(*)
    INTO dependency_failure
    FROM dependencies d
    WHERE d.consumer_project_id = release_record.project_id
      AND NOT EXISTS (
          SELECT 1
          FROM releases provider
          WHERE provider.project_id = d.provider_project_id
            AND provider.state = 'published'
            AND version_satisfies(
                provider.version,
                d.version_operator,
                d.required_version
            )
      );

    IF dependency_failure > 0 THEN
        RAISE EXCEPTION
            'One or more project dependencies are incompatible';
    END IF;

    INSERT INTO release_validations (
        release_id,
        rule_name,
        status,
        message
    )
    SELECT
        p_release_id,
        rule_name,
        status,
        message
    FROM validate_release(p_release_id);

    UPDATE releases
    SET
        state = 'validated',
        published_at = NULL
    WHERE release_id = p_release_id;

    UPDATE releases
    SET
        state = 'published',
        published_at = CURRENT_TIMESTAMP
    WHERE release_id = p_release_id;

END;
$$;

-- ------------------------------------------------------------
-- 12. VIEWS
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW published_release_catalog AS
SELECT
    p.project_key,
    p.project_name,
    r.release_id,
    r.version,
    r.major,
    r.minor,
    r.patch,
    r.change_kind,
    r.description,
    r.published_at
FROM projects p
JOIN releases r
    ON r.project_id = p.project_id
WHERE r.state = 'published';

CREATE OR REPLACE VIEW release_validation_report AS
SELECT
    p.project_key,
    r.version,
    r.state,
    rv.rule_name,
    rv.status,
    rv.message,
    rv.validated_at
FROM releases r
JOIN projects p
    ON p.project_id = r.project_id
LEFT JOIN release_validations rv
    ON rv.release_id = r.release_id;

CREATE OR REPLACE VIEW project_release_statistics AS
SELECT
    p.project_key,
    p.project_name,

    count(r.release_id) AS total_releases,

    count(r.release_id) FILTER (
        WHERE r.state = 'published'
    ) AS published_releases,

    count(r.release_id) FILTER (
        WHERE r.state = 'rejected'
    ) AS rejected_releases,

    count(r.release_id) FILTER (
        WHERE r.state = 'draft'
    ) AS draft_releases,

    max(r.published_at) AS last_published_at

FROM projects p
LEFT JOIN releases r
    ON r.project_id = p.project_id
GROUP BY p.project_id, p.project_key, p.project_name;

-- ------------------------------------------------------------
-- 13. SAMPLE PROJECTS
-- ------------------------------------------------------------

INSERT INTO projects (
    project_key,
    project_name,
    description
)
VALUES
(
    'payment-api',
    'Payment API',
    'Payment transaction and settlement service'
),
(
    'inventory-api',
    'Inventory API',
    'Inventory and stock management service'
),
(
    'customer-api',
    'Customer API',
    'Customer identity and profile service'
);

-- ------------------------------------------------------------
-- 14. SAMPLE RELEASES
-- ------------------------------------------------------------

INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '1.0.0',
    'major',
    'published',
    'Initial stable release',
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP
FROM projects
WHERE project_key = 'payment-api';

INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '1.1.0',
    'minor',
    'published',
    'Added transaction search',
    TRUE,
    TRUE,
    FALSE,
    TRUE,
    CURRENT_TIMESTAMP
FROM projects
WHERE project_key = 'payment-api';

INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '1.1.1',
    'patch',
    'published',
    'Fixed transaction pagination',
    TRUE,
    TRUE,
    FALSE,
    TRUE,
    CURRENT_TIMESTAMP
FROM projects
WHERE project_key = 'payment-api';

-- Inventory releases.

INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '2.0.0',
    'major',
    'published',
    'Initial version of redesigned inventory API',
    TRUE,
    TRUE,
    TRUE,
    TRUE,
    CURRENT_TIMESTAMP
FROM projects
WHERE project_key = 'inventory-api';

INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '2.1.0-beta.1',
    'minor',
    'draft',
    'Preview of inventory batch processing',
    TRUE,
    TRUE,
    FALSE,
    FALSE,
    NULL
FROM projects
WHERE project_key = 'inventory-api';

-- Invalid operational state: tests failed.
INSERT INTO releases (
    project_id,
    version,
    change_kind,
    state,
    description,
    tests_passed,
    documentation_updated,
    migration_notes,
    production_release,
    published_at
)
SELECT
    project_id,
    '1.2.0',
    'minor',
    'draft',
    'Candidate with failing automated tests',
    FALSE,
    TRUE,
    FALSE,
    TRUE,
    NULL
FROM projects
WHERE project_key = 'payment-api';

-- ------------------------------------------------------------
-- 15. SAMPLE CHANGELOG
-- ------------------------------------------------------------

INSERT INTO release_changes (
    release_id,
    category,
    title,
    details,
    breaking
)
SELECT
    r.release_id,
    'feature',
    'Transaction search',
    'Introduced filtered transaction search endpoint',
    FALSE
FROM releases r
JOIN projects p USING (project_id)
WHERE p.project_key = 'payment-api'
  AND r.version = '1.1.0';

INSERT INTO release_changes (
    release_id,
    category,
    title,
    details,
    breaking
)
SELECT
    r.release_id,
    'breaking',
    'Changed payment request schema',
    'Replaced the legacy payment request structure',
    TRUE
FROM releases r
JOIN projects p USING (project_id)
WHERE p.project_key = 'inventory-api'
  AND r.version = '2.0.0';

-- ------------------------------------------------------------
-- 16. SAMPLE DEPENDENCY POLICIES
-- ------------------------------------------------------------

INSERT INTO dependencies (
    consumer_project_id,
    provider_project_id,
    version_operator,
    required_version
)
SELECT
    consumer.project_id,
    provider.project_id,
    '>=',
    '1.0.0'
FROM projects consumer
CROSS JOIN projects provider
WHERE consumer.project_key = 'inventory-api'
  AND provider.project_key = 'payment-api';

INSERT INTO dependencies (
    consumer_project_id,
    provider_project_id,
    version_operator,
    required_version
)
SELECT
    consumer.project_id,
    provider.project_id,
    '<',
    '2.0.0'
FROM projects consumer
CROSS JOIN projects provider
WHERE consumer.project_key = 'inventory-api'
  AND provider.project_key = 'payment-api';

-- ------------------------------------------------------------
-- 17. SEMVER PRECEDENCE TESTS
-- ------------------------------------------------------------

DO $$
DECLARE
    sequence TEXT[] := ARRAY[
        '1.0.0-alpha',
        '1.0.0-alpha.1',
        '1.0.0-alpha.beta',
        '1.0.0-beta',
        '1.0.0-beta.2',
        '1.0.0-beta.11',
        '1.0.0-rc.1',
        '1.0.0'
    ];

    i INTEGER;
BEGIN
    FOR i IN 1..array_length(sequence, 1) - 1 LOOP
        IF semver_compare(
            sequence[i],
            sequence[i + 1]
        ) >= 0 THEN
            RAISE EXCEPTION
                'SemVer precedence test failed: % >= %',
                sequence[i],
                sequence[i + 1];
        END IF;
    END LOOP;

    IF semver_compare(
        '1.0.0+build.1',
        '1.0.0+build.2'
    ) <> 0 THEN
        RAISE EXCEPTION
            'Build metadata must not affect precedence';
    END IF;

    IF NOT is_valid_semver('1.2.3-rc.1+build.25') THEN
        RAISE EXCEPTION
            'Valid SemVer was rejected';
    END IF;

    IF is_valid_semver('01.2.3') THEN
        RAISE EXCEPTION
            'Leading zero in major component was accepted';
    END IF;

    IF is_valid_semver('1.2.3-01') THEN
        RAISE EXCEPTION
            'Leading zero in prerelease identifier was accepted';
    END IF;

    RAISE NOTICE 'SemVer precedence tests passed';
END;
$$;

-- ------------------------------------------------------------
-- 18. RETRIEVAL QUERIES
-- ------------------------------------------------------------

-- Published versions for every project.
SELECT *
FROM published_release_catalog
ORDER BY project_key, major, minor, patch;

-- Project-specific release history.
SELECT
    p.project_name,
    r.version,
    r.change_kind,
    r.state,
    r.description,
    r.published_at
FROM projects p
JOIN releases r USING (project_id)
WHERE p.project_key = 'payment-api'
ORDER BY r.created_at DESC;

-- ------------------------------------------------------------
-- 19. VALIDATION QUERIES
-- ------------------------------------------------------------

SELECT
    r.version,
    validation.rule_name,
    validation.status,
    validation.message
FROM releases r
CROSS JOIN LATERAL validate_release(r.release_id) validation
WHERE r.state = 'draft'
ORDER BY r.version, validation.rule_name;

-- ------------------------------------------------------------
-- 20. AGGREGATION AND REPORTING
-- ------------------------------------------------------------

SELECT *
FROM project_release_statistics
ORDER BY project_key;

-- Number of releases by change type.
SELECT
    change_kind,
    count(*) AS release_count,
    count(*) FILTER (
        WHERE state = 'published'
    ) AS published_count
FROM releases
GROUP BY change_kind
ORDER BY change_kind;

-- ------------------------------------------------------------
-- 21. ELIGIBILITY DETERMINATION
-- ------------------------------------------------------------

SELECT
    r.version,
    r.state,
    release_is_eligible(r.release_id) AS eligible
FROM releases r
ORDER BY r.project_id, r.created_at;

-- ------------------------------------------------------------
-- 22. CTE: PROJECT RELEASE ANALYSIS
-- ------------------------------------------------------------

WITH release_metrics AS (
    SELECT
        project_id,
        count(*) AS total,
        count(*) FILTER (
            WHERE state = 'published'
        ) AS published,
        count(*) FILTER (
            WHERE state = 'rejected'
        ) AS rejected
    FROM releases
    GROUP BY project_id
)
SELECT
    p.project_name,
    COALESCE(m.total, 0) AS total_releases,
    COALESCE(m.published, 0) AS published_releases,
    COALESCE(m.rejected, 0) AS rejected_releases,
    CASE
        WHEN COALESCE(m.total, 0) = 0 THEN 0
        ELSE round(
            100.0 * m.published / m.total,
            2
        )
    END AS publication_percentage
FROM projects p
LEFT JOIN release_metrics m USING (project_id)
ORDER BY p.project_name;

-- ------------------------------------------------------------
-- 23. TRANSACTIONAL WORKFLOW EXAMPLE
-- ------------------------------------------------------------

-- This example demonstrates atomic publication.
-- A failure rolls back every state change in the transaction.

DO $$
DECLARE
    target_release BIGINT;
BEGIN
    SELECT release_id
    INTO target_release
    FROM releases
    WHERE version = '1.1.0-beta.1'
      AND project_id = (
          SELECT project_id
          FROM projects
          WHERE project_key = 'inventory-api'
      );

    IF target_release IS NOT NULL THEN
        RAISE NOTICE
            'Prerelease candidate % remains unpublished',
            target_release;
    END IF;
END;
$$;

-- ------------------------------------------------------------
-- 24. SECURITY AND OPERATIONAL NOTES
-- ------------------------------------------------------------

-- Production deployment should assign schema permissions to
-- dedicated database roles instead of granting application users
-- unrestricted access to releases and audit records.
--
-- Example:
--
-- CREATE ROLE semver_reader NOLOGIN;
-- CREATE ROLE semver_release_manager NOLOGIN;
--
-- GRANT USAGE ON SCHEMA semver TO semver_reader;
-- GRANT SELECT ON ALL TABLES IN SCHEMA semver TO semver_reader;
--
-- GRANT USAGE ON SCHEMA semver TO semver_release_manager;
-- GRANT SELECT, INSERT ON projects, releases, release_changes,
--     dependencies, release_validations
-- TO semver_release_manager;
--
-- Grant EXECUTE on publication procedures separately.
--
-- A deployment should also protect audit records from modification
-- by ordinary application roles.

COMMIT;

-- ------------------------------------------------------------
-- 25. FINAL RELEASE HISTORY
-- ------------------------------------------------------------

SELECT
    p.project_key,
    r.version,
    r.change_kind,
    r.state,
    r.description,
    r.published_at
FROM semver.projects p
JOIN semver.releases r USING (project_id)
ORDER BY
    p.project_key,
    r.created_at,
    r.release_id;
