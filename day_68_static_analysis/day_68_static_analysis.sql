-- ============================================================
-- STATIC ANALYSIS GOVERNANCE DATABASE
-- PostgreSQL 15+
--
-- Models:
-- 1. Software projects and source files
-- 2. Static analysis tools and rule registries
-- 3. Analysis executions
-- 4. Linter and analyzer findings
-- 5. Formatter executions
-- 6. Rule suppressions and approvals
-- 7. Quality gates and repository compliance
-- 8. Historical reporting and performance analysis
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS static_analysis;

SET search_path TO static_analysis, public;

-- ------------------------------------------------------------
-- ENUMERATED DOMAIN TYPES
-- ------------------------------------------------------------

CREATE TYPE severity_level AS ENUM (
    'error',
    'warning',
    'info'
);

CREATE TYPE rule_category AS ENUM (
    'security',
    'formatting',
    'reliability',
    'maintainability',
    'performance'
);

CREATE TYPE analysis_status AS ENUM (
    'queued',
    'running',
    'completed',
    'failed',
    'cancelled'
);

CREATE TYPE suppression_status AS ENUM (
    'pending',
    'approved',
    'rejected',
    'expired'
);

CREATE TYPE gate_status AS ENUM (
    'passed',
    'failed',
    'pending'
);

CREATE TYPE tool_type AS ENUM (
    'linter',
    'formatter',
    'security_analyzer',
    'complexity_analyzer'
);

-- ------------------------------------------------------------
-- PROJECTS
-- ------------------------------------------------------------

CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL UNIQUE,
    repository_url TEXT NOT NULL,
    default_branch VARCHAR(150) NOT NULL DEFAULT 'main',
    programming_language VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_project_name
        CHECK (length(trim(project_name)) >= 2),

    CONSTRAINT valid_repository_url
        CHECK (repository_url ~ '^https?://')
);

-- ------------------------------------------------------------
-- SOURCE FILE INVENTORY
-- ------------------------------------------------------------

CREATE TABLE source_files (
    file_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    file_path TEXT NOT NULL,
    language VARCHAR(50) NOT NULL,
    file_hash VARCHAR(128),
    file_size_bytes BIGINT NOT NULL DEFAULT 0,
    lines_of_code INTEGER NOT NULL DEFAULT 0,
    excluded BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(project_id, file_path),

    CHECK (file_size_bytes >= 0),
    CHECK (lines_of_code >= 0),
    CHECK (
        file_hash IS NULL OR
        file_hash ~ '^[A-Fa-f0-9]{32,128}$'
    )
);

-- ------------------------------------------------------------
-- STATIC ANALYSIS TOOLS
-- ------------------------------------------------------------

CREATE TABLE analysis_tools (
    tool_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tool_name VARCHAR(100) NOT NULL,
    tool_type tool_type NOT NULL,
    tool_version VARCHAR(50) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tool_name, tool_version)
);

-- ------------------------------------------------------------
-- ANALYSIS RULES
-- ------------------------------------------------------------

CREATE TABLE analysis_rules (
    rule_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_code VARCHAR(30) NOT NULL UNIQUE,
    rule_name VARCHAR(150) NOT NULL,
    category rule_category NOT NULL,
    default_severity severity_level NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (rule_code ~ '^[A-Z]+[0-9]{3}$'),
    CHECK (length(trim(rule_name)) > 0)
);

-- Tool-to-rule mapping supports multiple implementations
-- of the same quality rule.

CREATE TABLE tool_rules (
    tool_id BIGINT NOT NULL REFERENCES analysis_tools(tool_id),
    rule_id BIGINT NOT NULL REFERENCES analysis_rules(rule_id),
    supported BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY(tool_id, rule_id)
);

-- ------------------------------------------------------------
-- ANALYSIS EXECUTIONS
-- ------------------------------------------------------------

CREATE TABLE analysis_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    tool_id BIGINT NOT NULL REFERENCES analysis_tools(tool_id),
    commit_hash VARCHAR(128) NOT NULL,
    branch_name VARCHAR(150) NOT NULL,
    status analysis_status NOT NULL DEFAULT 'queued',
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    files_scanned INTEGER NOT NULL DEFAULT 0,
    lines_scanned BIGINT NOT NULL DEFAULT 0,
    execution_duration_ms BIGINT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (commit_hash ~ '^[A-Fa-f0-9]{7,128}$'),
    CHECK (files_scanned >= 0),
    CHECK (lines_scanned >= 0),
    CHECK (
        execution_duration_ms IS NULL OR
        execution_duration_ms >= 0
    ),
    CHECK (
        completed_at IS NULL OR started_at IS NULL OR
        completed_at >= started_at
    )
);

-- ------------------------------------------------------------
-- ANALYSIS FINDINGS
-- ------------------------------------------------------------

CREATE TABLE findings (
    finding_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES analysis_runs(run_id),
    file_id BIGINT NOT NULL REFERENCES source_files(file_id),
    rule_id BIGINT NOT NULL REFERENCES analysis_rules(rule_id),
    severity severity_level NOT NULL,
    line_number INTEGER NOT NULL,
    column_number INTEGER NOT NULL DEFAULT 1,
    message TEXT NOT NULL,
    code_excerpt TEXT,
    fingerprint VARCHAR(128) NOT NULL,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,

    UNIQUE(run_id, fingerprint),

    CHECK (line_number >= 1),
    CHECK (column_number >= 1),
    CHECK (length(trim(message)) > 0),
    CHECK (
        (resolved = FALSE AND resolved_at IS NULL)
        OR
        (resolved = TRUE AND resolved_at IS NOT NULL)
    )
);

-- ------------------------------------------------------------
-- FORMATTER EXECUTIONS
-- ------------------------------------------------------------

CREATE TABLE formatter_runs (
    formatter_run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES analysis_runs(run_id),
    file_id BIGINT NOT NULL REFERENCES source_files(file_id),
    changed BOOLEAN NOT NULL DEFAULT FALSE,
    original_hash VARCHAR(128),
    formatted_hash VARCHAR(128),
    changed_lines INTEGER NOT NULL DEFAULT 0,
    formatter_config JSONB NOT NULL DEFAULT '{}'::JSONB,
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (changed_lines >= 0),
    CHECK (
        original_hash IS NULL OR
        original_hash ~ '^[A-Fa-f0-9]{32,128}$'
    ),
    CHECK (
        formatted_hash IS NULL OR
        formatted_hash ~ '^[A-Fa-f0-9]{32,128}$'
    )
);

-- ------------------------------------------------------------
-- USERS AND REVIEW AUTHORIZATION
-- ------------------------------------------------------------

CREATE TABLE governance_users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    governance_role VARCHAR(30) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,

    CHECK (
        governance_role IN (
            'developer',
            'reviewer',
            'security_admin',
            'repository_admin'
        )
    )
);

-- ------------------------------------------------------------
-- FINDING SUPPRESSIONS
-- ------------------------------------------------------------

CREATE TABLE finding_suppressions (
    suppression_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    finding_id BIGINT NOT NULL REFERENCES findings(finding_id),
    requested_by BIGINT NOT NULL REFERENCES governance_users(user_id),
    approved_by BIGINT REFERENCES governance_users(user_id),
    reason TEXT NOT NULL,
    status suppression_status NOT NULL DEFAULT 'pending',
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (length(trim(reason)) >= 10),
    CHECK (
        expires_at IS NULL OR
        expires_at > created_at
    ),
    CHECK (
        status <> 'approved' OR approved_by IS NOT NULL
    )
);

-- ------------------------------------------------------------
-- QUALITY GATE POLICIES
-- ------------------------------------------------------------

CREATE TABLE quality_gate_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id),
    policy_name VARCHAR(120) NOT NULL,
    maximum_errors INTEGER NOT NULL DEFAULT 0,
    maximum_warnings INTEGER NOT NULL DEFAULT 10,
    maximum_critical_security_findings INTEGER NOT NULL DEFAULT 0,
    require_completed_analysis BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(project_id, policy_name),

    CHECK (maximum_errors >= 0),
    CHECK (maximum_warnings >= 0),
    CHECK (maximum_critical_security_findings >= 0)
);

CREATE TABLE quality_gate_evaluations (
    evaluation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    run_id BIGINT NOT NULL REFERENCES analysis_runs(run_id),
    policy_id BIGINT NOT NULL REFERENCES quality_gate_policies(policy_id),
    status gate_status NOT NULL DEFAULT 'pending',
    error_count INTEGER NOT NULL DEFAULT 0,
    warning_count INTEGER NOT NULL DEFAULT 0,
    critical_security_count INTEGER NOT NULL DEFAULT 0,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    explanation TEXT,

    UNIQUE(run_id, policy_id),

    CHECK (error_count >= 0),
    CHECK (warning_count >= 0),
    CHECK (critical_security_count >= 0)
);

-- ------------------------------------------------------------
-- PERFORMANCE INDEXES
-- ------------------------------------------------------------

CREATE INDEX idx_runs_project_date
    ON analysis_runs(project_id, created_at DESC);

CREATE INDEX idx_runs_status
    ON analysis_runs(status);

CREATE INDEX idx_findings_run_severity
    ON findings(run_id, severity);

CREATE INDEX idx_findings_rule
    ON findings(rule_id, first_seen_at DESC);

CREATE INDEX idx_findings_unresolved
    ON findings(file_id, rule_id)
    WHERE resolved = FALSE;

CREATE INDEX idx_suppressions_pending
    ON finding_suppressions(created_at)
    WHERE status = 'pending';

CREATE INDEX idx_gate_evaluation_status
    ON quality_gate_evaluations(status, evaluated_at DESC);

CREATE INDEX idx_source_project
    ON source_files(project_id, file_path);

-- ------------------------------------------------------------
-- RUN STATE VALIDATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_analysis_run()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.status IN ('completed', 'failed', 'cancelled')
       AND NEW.status <> OLD.status THEN
        RAISE EXCEPTION
            'Terminal analysis status cannot be changed.';
    END IF;

    IF NEW.status = 'running' AND NEW.started_at IS NULL THEN
        NEW.started_at := NOW();
    END IF;

    IF NEW.status IN ('completed', 'failed', 'cancelled') THEN
        NEW.completed_at := COALESCE(NEW.completed_at, NOW());
    END IF;

    IF NEW.status = 'completed' AND NEW.error_message IS NOT NULL THEN
        RAISE EXCEPTION
            'Completed run cannot contain an execution error.';
    END IF;

    IF NEW.status = 'failed'
       AND NEW.error_message IS NULL THEN
        RAISE EXCEPTION
            'Failed run requires an error message.';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_analysis_run
BEFORE UPDATE ON analysis_runs
FOR EACH ROW
EXECUTE FUNCTION validate_analysis_run();

-- ------------------------------------------------------------
-- FINDING RESOLUTION AUDIT
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION maintain_finding_resolution()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.resolved AND NOT OLD.resolved THEN
        NEW.resolved_at := NOW();
    ELSIF NOT NEW.resolved THEN
        NEW.resolved_at := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_finding_resolution
BEFORE UPDATE OF resolved ON findings
FOR EACH ROW
EXECUTE FUNCTION maintain_finding_resolution();

-- ------------------------------------------------------------
-- SUPPRESSION AUTHORIZATION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_suppression_approval()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    approver_role VARCHAR(30);
BEGIN
    IF NEW.status = 'approved' THEN
        IF NEW.approved_by IS NULL THEN
            RAISE EXCEPTION 'An approver is required.';
        END IF;

        IF NEW.approved_by = NEW.requested_by THEN
            RAISE EXCEPTION
                'Users cannot approve their own suppressions.';
        END IF;

        SELECT governance_role
        INTO approver_role
        FROM governance_users
        WHERE user_id = NEW.approved_by
          AND active = TRUE;

        IF approver_role NOT IN (
            'security_admin',
            'repository_admin'
        ) THEN
            RAISE EXCEPTION
                'Approver lacks suppression authorization.';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_suppression_authorization
BEFORE INSERT OR UPDATE ON finding_suppressions
FOR EACH ROW
EXECUTE FUNCTION validate_suppression_approval();

-- ------------------------------------------------------------
-- ANALYSIS FINDING REPORT
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW finding_report AS
SELECT
    f.finding_id,
    p.project_name,
    sf.file_path,
    r.rule_code,
    r.rule_name,
    r.category,
    f.severity,
    f.line_number,
    f.column_number,
    f.message,
    f.resolved,
    f.first_seen_at,
    ar.commit_hash,
    ar.branch_name,
    ar.status AS analysis_status
FROM findings f
JOIN source_files sf
    ON sf.file_id = f.file_id
JOIN analysis_rules r
    ON r.rule_id = f.rule_id
JOIN analysis_runs ar
    ON ar.run_id = f.run_id
JOIN projects p
    ON p.project_id = ar.project_id;

-- ------------------------------------------------------------
-- PROJECT QUALITY METRICS
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW project_quality_metrics AS
SELECT
    p.project_id,
    p.project_name,
    COUNT(DISTINCT ar.run_id) AS total_runs,
    COUNT(DISTINCT f.finding_id) AS total_findings,
    COUNT(f.finding_id) FILTER (
        WHERE f.severity = 'error'
    ) AS errors,
    COUNT(f.finding_id) FILTER (
        WHERE f.severity = 'warning'
    ) AS warnings,
    COUNT(f.finding_id) FILTER (
        WHERE f.resolved = TRUE
    ) AS resolved_findings,
    COUNT(f.finding_id) FILTER (
        WHERE f.resolved = FALSE
    ) AS unresolved_findings
FROM projects p
LEFT JOIN analysis_runs ar
    ON ar.project_id = p.project_id
LEFT JOIN findings f
    ON f.run_id = ar.run_id
GROUP BY p.project_id, p.project_name;

-- ------------------------------------------------------------
-- RULE DISTRIBUTION REPORT
-- ------------------------------------------------------------

CREATE OR REPLACE VIEW rule_distribution AS
SELECT
    r.rule_code,
    r.rule_name,
    r.category,
    r.default_severity,
    COUNT(f.finding_id) AS occurrence_count,
    COUNT(f.finding_id) FILTER (
        WHERE f.resolved = FALSE
    ) AS unresolved_count
FROM analysis_rules r
LEFT JOIN findings f
    ON f.rule_id = r.rule_id
GROUP BY
    r.rule_id,
    r.rule_code,
    r.rule_name,
    r.category,
    r.default_severity;

-- ------------------------------------------------------------
-- QUALITY GATE EVALUATION FUNCTION
-- ------------------------------------------------------------

CREATE OR REPLACE FUNCTION evaluate_quality_gate(
    p_run_id BIGINT,
    p_policy_id BIGINT
)
RETURNS gate_status
LANGUAGE plpgsql
AS $$
DECLARE
    policy_row quality_gate_policies%ROWTYPE;
    run_row analysis_runs%ROWTYPE;

    error_total INTEGER;
    warning_total INTEGER;
    critical_total INTEGER;
    final_status gate_status;
BEGIN
    SELECT *
    INTO policy_row
    FROM quality_gate_policies
    WHERE policy_id = p_policy_id
      AND active = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Active quality policy not found.';
    END IF;

    SELECT *
    INTO run_row
    FROM analysis_runs
    WHERE run_id = p_run_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Analysis run not found.';
    END IF;

    IF run_row.project_id <> policy_row.project_id THEN
        RAISE EXCEPTION
            'Analysis run and policy belong to different projects.';
    END IF;

    IF policy_row.require_completed_analysis
       AND run_row.status <> 'completed' THEN
        final_status := 'pending';

        INSERT INTO quality_gate_evaluations (
            run_id, policy_id, status, explanation
        )
        VALUES (
            p_run_id,
            p_policy_id,
            final_status,
            'Analysis execution has not completed successfully.'
        )
        ON CONFLICT (run_id, policy_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            explanation = EXCLUDED.explanation,
            evaluated_at = NOW();

        RETURN final_status;
    END IF;

    SELECT
        COUNT(*) FILTER (
            WHERE f.severity = 'error'
              AND NOT EXISTS (
                  SELECT 1
                  FROM finding_suppressions fs
                  WHERE fs.finding_id = f.finding_id
                    AND fs.status = 'approved'
                    AND (
                        fs.expires_at IS NULL
                        OR fs.expires_at > NOW()
                    )
              )
        ),
        COUNT(*) FILTER (
            WHERE f.severity = 'warning'
              AND NOT EXISTS (
                  SELECT 1
                  FROM finding_suppressions fs
                  WHERE fs.finding_id = f.finding_id
                    AND fs.status = 'approved'
                    AND (
                        fs.expires_at IS NULL
                        OR fs.expires_at > NOW()
                    )
              )
        ),
        COUNT(*) FILTER (
            WHERE r.category = 'security'
              AND f.severity = 'error'
              AND NOT EXISTS (
                  SELECT 1
                  FROM finding_suppressions fs
                  WHERE fs.finding_id = f.finding_id
                    AND fs.status = 'approved'
                    AND (
                        fs.expires_at IS NULL
                        OR fs.expires_at > NOW()
                    )
              )
        )
    INTO error_total, warning_total, critical_total
    FROM findings f
    JOIN analysis_rules r
        ON r.rule_id = f.rule_id
    WHERE f.run_id = p_run_id;

    final_status := CASE
        WHEN error_total <= policy_row.maximum_errors
         AND warning_total <= policy_row.maximum_warnings
         AND critical_total <=
             policy_row.maximum_critical_security_findings
        THEN 'passed'::gate_status
        ELSE 'failed'::gate_status
    END;

    INSERT INTO quality_gate_evaluations (
        run_id,
        policy_id,
        status,
        error_count,
        warning_count,
        critical_security_count,
        explanation
    )
    VALUES (
        p_run_id,
        p_policy_id,
        final_status,
        error_total,
        warning_total,
        critical_total,
        'Evaluation performed against active repository policy.'
    )
    ON CONFLICT (run_id, policy_id)
    DO UPDATE SET
        status = EXCLUDED.status,
        error_count = EXCLUDED.error_count,
        warning_count = EXCLUDED.warning_count,
        critical_security_count =
            EXCLUDED.critical_security_count,
        explanation = EXCLUDED.explanation,
        evaluated_at = NOW();

    RETURN final_status;
END;
$$;

-- ------------------------------------------------------------
-- PROCEDURE: COMPLETE AN ANALYSIS RUN
-- ------------------------------------------------------------

CREATE OR REPLACE PROCEDURE complete_analysis_run(
    p_run_id BIGINT,
    p_files INTEGER,
    p_lines BIGINT,
    p_duration BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF p_files < 0 OR p_lines < 0 OR p_duration < 0 THEN
        RAISE EXCEPTION 'Analysis metrics cannot be negative.';
    END IF;

    UPDATE analysis_runs
    SET
        status = 'completed',
        files_scanned = p_files,
        lines_scanned = p_lines,
        execution_duration_ms = p_duration,
        error_message = NULL
    WHERE run_id = p_run_id
      AND status = 'running';

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Only a running analysis can be completed.';
    END IF;
END;
$$;

-- ------------------------------------------------------------
-- SAMPLE PROJECTS
-- ------------------------------------------------------------

INSERT INTO projects (
    project_name,
    repository_url,
    default_branch,
    programming_language
)
VALUES
(
    'Payment Platform',
    'https://github.com/example/payment-platform',
    'main',
    'Python'
),
(
    'Inventory Service',
    'https://github.com/example/inventory-service',
    'main',
    'JavaScript'
);

-- ------------------------------------------------------------
-- SAMPLE SOURCE FILES
-- ------------------------------------------------------------

INSERT INTO source_files (
    project_id,
    file_path,
    language,
    file_hash,
    file_size_bytes,
    lines_of_code
)
SELECT
    project_id,
    'src/payment_service.py',
    'Python',
    repeat('a', 64),
    4200,
    150
FROM projects
WHERE project_name = 'Payment Platform';

INSERT INTO source_files (
    project_id,
    file_path,
    language,
    file_hash,
    file_size_bytes,
    lines_of_code
)
SELECT
    project_id,
    'src/inventory.js',
    'JavaScript',
    repeat('b', 64),
    2800,
    100
FROM projects
WHERE project_name = 'Inventory Service';

-- ------------------------------------------------------------
-- SAMPLE TOOLS
-- ------------------------------------------------------------

INSERT INTO analysis_tools (
    tool_name,
    tool_type,
    tool_version
)
VALUES
('SourceLint', 'linter', '1.0.0'),
('FormatEngine', 'formatter', '2.1.0'),
('SecurityScan', 'security_analyzer', '3.0.0'),
('ComplexityCheck', 'complexity_analyzer', '1.5.0');

-- ------------------------------------------------------------
-- SAMPLE RULES
-- ------------------------------------------------------------

INSERT INTO analysis_rules (
    rule_code,
    rule_name,
    category,
    default_severity,
    description,
    recommendation
)
VALUES
(
    'SEC001',
    'Dynamic Code Evaluation',
    'security',
    'error',
    'Dynamic evaluation can execute untrusted input.',
    'Replace dynamic execution with validated operations.'
),
(
    'SEC002',
    'Unsafe Shell Execution',
    'security',
    'error',
    'Shell execution can introduce command injection.',
    'Avoid shell execution and validate process arguments.'
),
(
    'FMT001',
    'Maximum Line Length',
    'formatting',
    'warning',
    'Source line exceeds the configured limit.',
    'Split long expressions.'
),
(
    'FMT002',
    'Trailing Whitespace',
    'formatting',
    'warning',
    'Whitespace occurs at the end of a line.',
    'Remove trailing whitespace.'
),
(
    'REL001',
    'Bare Exception Handling',
    'reliability',
    'warning',
    'Broad exception handling may conceal failures.',
    'Catch specific exception classes.'
),
(
    'MAINT001',
    'Excessive Complexity',
    'maintainability',
    'warning',
    'Function complexity exceeds the configured threshold.',
    'Decompose the function into smaller units.'
),
(
    'PERF001',
    'Repeated Expensive Search',
    'performance',
    'info',
    'Repeated linear searches may increase execution cost.',
    'Use an appropriate indexed data structure.'
);

-- ------------------------------------------------------------
-- TOOL RULE REGISTRATION
-- ------------------------------------------------------------

INSERT INTO tool_rules(tool_id, rule_id)
SELECT t.tool_id, r.rule_id
FROM analysis_tools t
CROSS JOIN analysis_rules r
WHERE
    (t.tool_name = 'SourceLint'
        AND r.category IN (
            'formatting', 'reliability', 'maintainability'
        ))
    OR
    (t.tool_name = 'SecurityScan'
        AND r.category = 'security')
    OR
    (t.tool_name = 'ComplexityCheck'
        AND r.category IN (
            'maintainability', 'performance'
        ))
    OR
    (t.tool_name = 'FormatEngine'
        AND r.category = 'formatting');

-- ------------------------------------------------------------
-- GOVERNANCE USERS
-- ------------------------------------------------------------

INSERT INTO governance_users (
    username,
    email,
    governance_role
)
VALUES
('developer01', 'developer01@example.com', 'developer'),
('reviewer01', 'reviewer01@example.com', 'reviewer'),
('securityadmin', 'security@example.com', 'security_admin'),
('repositoryadmin', 'repo-admin@example.com', 'repository_admin');

-- ------------------------------------------------------------
-- QUALITY POLICIES
-- ------------------------------------------------------------

INSERT INTO quality_gate_policies (
    project_id,
    policy_name,
    maximum_errors,
    maximum_warnings,
    maximum_critical_security_findings,
    require_completed_analysis
)
SELECT
    project_id,
    'Production Release Gate',
    0,
    5,
    0,
    TRUE
FROM projects
WHERE project_name = 'Payment Platform';

-- ------------------------------------------------------------
-- ANALYSIS EXECUTIONS
-- ------------------------------------------------------------

INSERT INTO analysis_runs (
    project_id,
    tool_id,
    commit_hash,
    branch_name,
    status,
    started_at
)
SELECT
    p.project_id,
    t.tool_id,
    repeat('c', 40),
    'feature/payment-validation',
    'running',
    NOW() - INTERVAL '2 minutes'
FROM projects p
CROSS JOIN analysis_tools t
WHERE p.project_name = 'Payment Platform'
  AND t.tool_name = 'SourceLint';

-- ------------------------------------------------------------
-- FINDINGS
-- ------------------------------------------------------------

INSERT INTO findings (
    run_id,
    file_id,
    rule_id,
    severity,
    line_number,
    column_number,
    message,
    code_excerpt,
    fingerprint
)
SELECT
    ar.run_id,
    sf.file_id,
    r.rule_id,
    'error',
    42,
    15,
    'Unsafe dynamic evaluation detected.',
    'result = eval(user_input)',
    repeat('d', 64)
FROM analysis_runs ar
JOIN projects p
    ON p.project_id = ar.project_id
JOIN source_files sf
    ON sf.project_id = p.project_id
JOIN analysis_rules r
    ON r.rule_code = 'SEC001'
WHERE p.project_name = 'Payment Platform';

INSERT INTO findings (
    run_id,
    file_id,
    rule_id,
    severity,
    line_number,
    column_number,
    message,
    code_excerpt,
    fingerprint
)
SELECT
    ar.run_id,
    sf.file_id,
    r.rule_id,
    'warning',
    85,
    1,
    'Trailing whitespace detected.',
    'total = calculate_total()',
    repeat('e', 64)
FROM analysis_runs ar
JOIN projects p
    ON p.project_id = ar.project_id
JOIN source_files sf
    ON sf.project_id = p.project_id
JOIN analysis_rules r
    ON r.rule_code = 'FMT002'
WHERE p.project_name = 'Payment Platform';

-- ------------------------------------------------------------
-- FORMATTER EXECUTION
-- ------------------------------------------------------------

INSERT INTO formatter_runs (
    run_id,
    file_id,
    changed,
    original_hash,
    formatted_hash,
    changed_lines,
    formatter_config
)
SELECT
    ar.run_id,
    sf.file_id,
    TRUE,
    repeat('a', 64),
    repeat('f', 64),
    3,
    '{"line_length": 88, "indentation": 4}'::JSONB
FROM analysis_runs ar
JOIN projects p
    ON p.project_id = ar.project_id
JOIN source_files sf
    ON sf.project_id = p.project_id
WHERE p.project_name = 'Payment Platform';

-- ------------------------------------------------------------
-- SUPPRESSION REQUEST
-- ------------------------------------------------------------

INSERT INTO finding_suppressions (
    finding_id,
    requested_by,
    reason,
    status
)
SELECT
    f.finding_id,
    u.user_id,
    'Temporary exception requested for a documented legacy issue.',
    'pending'
FROM findings f
JOIN governance_users u
    ON u.username = 'developer01'
JOIN analysis_rules r
    ON r.rule_id = f.rule_id
WHERE r.rule_code = 'FMT002';

-- ------------------------------------------------------------
-- COMPLETE ANALYSIS
-- ------------------------------------------------------------

CALL complete_analysis_run(
    (
        SELECT run_id
        FROM analysis_runs
        WHERE commit_hash = repeat('c', 40)
    ),
    1,
    150,
    1200
);

-- ------------------------------------------------------------
-- TRANSACTIONAL QUALITY GATE EVALUATION
-- ------------------------------------------------------------

DO $$
DECLARE
    current_run BIGINT;
    current_policy BIGINT;
    result gate_status;
BEGIN
    SELECT run_id
    INTO current_run
    FROM analysis_runs
    WHERE commit_hash = repeat('c', 40);

    SELECT policy_id
    INTO current_policy
    FROM quality_gate_policies
    WHERE policy_name = 'Production Release Gate';

    result := evaluate_quality_gate(
        current_run,
        current_policy
    );

    RAISE NOTICE 'Quality gate result: %', result;
END;
$$;

COMMIT;

-- ============================================================
-- RETRIEVAL QUERIES
-- ============================================================

-- 1. All findings for a project.

SELECT *
FROM finding_report
WHERE project_name = 'Payment Platform'
ORDER BY line_number, column_number;

-- 2. Unresolved security findings.

SELECT
    project_name,
    file_path,
    rule_code,
    message,
    line_number
FROM finding_report
WHERE category = 'security'
  AND resolved = FALSE
ORDER BY first_seen_at DESC;

-- 3. Latest analysis execution.

SELECT
    p.project_name,
    ar.commit_hash,
    ar.branch_name,
    ar.status,
    ar.files_scanned,
    ar.lines_scanned,
    ar.execution_duration_ms
FROM analysis_runs ar
JOIN projects p
    ON p.project_id = ar.project_id
ORDER BY ar.created_at DESC
LIMIT 10;

-- ============================================================
-- VALIDATION QUERIES
-- ============================================================

-- 4. Findings without an enabled rule.

SELECT f.finding_id, r.rule_code, r.enabled
FROM findings f
JOIN analysis_rules r
    ON r.rule_id = f.rule_id
WHERE r.enabled = FALSE;

-- 5. Expired approved suppressions.

SELECT suppression_id, finding_id, expires_at
FROM finding_suppressions
WHERE status = 'approved'
  AND expires_at < NOW();

-- 6. Analysis executions that did not complete.

SELECT run_id, project_id, status, error_message
FROM analysis_runs
WHERE status IN ('failed', 'cancelled', 'running');

-- ============================================================
-- AGGREGATION QUERIES
-- ============================================================

-- 7. Findings by severity and category.

SELECT
    r.category,
    f.severity,
    COUNT(*) AS finding_count
FROM findings f
JOIN analysis_rules r
    ON r.rule_id = f.rule_id
GROUP BY r.category, f.severity
ORDER BY r.category, f.severity;

-- 8. Most frequently triggered rules.

SELECT *
FROM rule_distribution
ORDER BY occurrence_count DESC
LIMIT 10;

-- 9. Project quality metrics.

SELECT *
FROM project_quality_metrics
ORDER BY unresolved_findings DESC;

-- ============================================================
-- CTE: FINDING RESOLUTION RATE
-- ============================================================

WITH finding_statistics AS (
    SELECT
        project_id,
        COUNT(*) AS total_findings,
        COUNT(*) FILTER (
            WHERE resolved = TRUE
        ) AS resolved_findings
    FROM findings f
    JOIN analysis_runs ar
        ON ar.run_id = f.run_id
    GROUP BY project_id
)
SELECT
    p.project_name,
    fs.total_findings,
    fs.resolved_findings,
    ROUND(
        100.0 * fs.resolved_findings /
        NULLIF(fs.total_findings, 0),
        2
    ) AS resolution_percentage
FROM finding_statistics fs
JOIN projects p
    ON p.project_id = fs.project_id;

-- ============================================================
-- WORKFLOW PROCESSING
-- ============================================================

-- 10. Pending suppressions requiring administrative review.

SELECT
    fs.suppression_id,
    f.finding_id,
    r.rule_code,
    requester.username AS requested_by,
    fs.reason,
    fs.created_at
FROM finding_suppressions fs
JOIN findings f
    ON f.finding_id = fs.finding_id
JOIN analysis_rules r
    ON r.rule_id = f.rule_id
JOIN governance_users requester
    ON requester.user_id = fs.requested_by
WHERE fs.status = 'pending'
ORDER BY fs.created_at;

-- 11. Approve a suppression using an authorized account.
-- The trigger rejects self-approval and unauthorized users.

UPDATE finding_suppressions
SET
    status = 'approved',
    approved_by = (
        SELECT user_id
        FROM governance_users
        WHERE username = 'securityadmin'
    ),
    expires_at = NOW() + INTERVAL '30 days'
WHERE status = 'pending'
  AND suppression_id = (
      SELECT MIN(suppression_id)
      FROM finding_suppressions
      WHERE status = 'pending'
  );

-- ============================================================
-- ELIGIBILITY DETERMINATION
-- ============================================================

-- 12. Determine whether each completed run passes its policy.

SELECT
    ar.run_id,
    p.project_name,
    qgp.policy_name,
    qge.status,
    qge.error_count,
    qge.warning_count,
    qge.critical_security_count,
    qge.explanation
FROM quality_gate_evaluations qge
JOIN analysis_runs ar
    ON ar.run_id = qge.run_id
JOIN quality_gate_policies qgp
    ON qgp.policy_id = qge.policy_id
JOIN projects p
    ON p.project_id = ar.project_id
ORDER BY qge.evaluated_at DESC;

-- ============================================================
-- REPORTING: ANALYSIS PERFORMANCE
-- ============================================================

-- 13. Average execution duration by tool.

SELECT
    t.tool_name,
    t.tool_version,
    COUNT(ar.run_id) AS total_runs,
    ROUND(AVG(ar.execution_duration_ms), 2)
        AS average_duration_ms,
    MAX(ar.execution_duration_ms)
        AS maximum_duration_ms
FROM analysis_tools t
LEFT JOIN analysis_runs ar
    ON ar.tool_id = t.tool_id
   AND ar.status = 'completed'
GROUP BY t.tool_id, t.tool_name, t.tool_version
ORDER BY average_duration_ms DESC;

-- ============================================================
-- REPORTING: QUALITY TREND
-- ============================================================

-- 14. Daily finding counts.

SELECT
    DATE_TRUNC('day', first_seen_at)::DATE AS finding_date,
    severity,
    COUNT(*) AS finding_count
FROM findings
GROUP BY DATE_TRUNC('day', first_seen_at)::DATE, severity
ORDER BY finding_date, severity;

-- ============================================================
-- REPORTING: FILE QUALITY
-- ============================================================

-- 15. Findings per thousand lines of code.

SELECT
    sf.file_path,
    sf.lines_of_code,
    COUNT(f.finding_id) AS total_findings,
    ROUND(
        1000.0 * COUNT(f.finding_id) /
        NULLIF(sf.lines_of_code, 0),
        2
    ) AS findings_per_thousand_lines
FROM source_files sf
LEFT JOIN findings f
    ON f.file_id = sf.file_id
GROUP BY sf.file_id, sf.file_path, sf.lines_of_code
ORDER BY findings_per_thousand_lines DESC NULLS LAST;

-- ============================================================
-- END OF STATIC ANALYSIS GOVERNANCE WORKFLOW
-- ============================================================
