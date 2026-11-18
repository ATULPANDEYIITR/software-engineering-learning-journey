-- ============================================================
-- APPLICATION MONITORING DATABASE
-- PostgreSQL 14+
--
-- Domain:
-- Applications -> Environments -> Services
-- -> Health Checks -> Monitoring Runs -> Results
-- -> Metrics -> Alert Policies -> Alerts
-- -> Dashboard Reporting
-- ============================================================

BEGIN;

DROP SCHEMA IF EXISTS app_monitoring CASCADE;

CREATE SCHEMA app_monitoring;

SET search_path TO app_monitoring, public;

-- ============================================================
-- 1. ENUMERATIONS
-- ============================================================

CREATE TYPE health_status AS ENUM (
    'HEALTHY',
    'DEGRADED',
    'UNHEALTHY',
    'UNKNOWN'
);

CREATE TYPE alert_severity AS ENUM (
    'INFO',
    'WARNING',
    'CRITICAL'
);

CREATE TYPE alert_state AS ENUM (
    'FIRING',
    'ACKNOWLEDGED',
    'RESOLVED'
);

CREATE TYPE check_type AS ENUM (
    'HTTP',
    'DATABASE',
    'MEMORY',
    'CPU',
    'DEPENDENCY',
    'QUEUE'
);

CREATE TYPE environment_type AS ENUM (
    'DEVELOPMENT',
    'STAGING',
    'PRODUCTION'
);

-- ============================================================
-- 2. APPLICATIONS
-- ============================================================

CREATE TABLE applications (
    application_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    application_name VARCHAR(120) NOT NULL UNIQUE,

    description TEXT,

    owner_team VARCHAR(100) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT application_name_nonempty
        CHECK (LENGTH(TRIM(application_name)) > 0)
);

-- ============================================================
-- 3. ENVIRONMENTS
-- ============================================================

CREATE TABLE environments (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    application_id BIGINT NOT NULL
        REFERENCES applications(application_id)
        ON DELETE CASCADE,

    environment_name environment_type NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    UNIQUE (application_id, environment_name)
);

-- ============================================================
-- 4. MONITORED SERVICES
-- ============================================================

CREATE TABLE monitored_services (
    service_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    environment_id BIGINT NOT NULL
        REFERENCES environments(environment_id)
        ON DELETE CASCADE,

    service_name VARCHAR(120) NOT NULL,

    current_status health_status NOT NULL DEFAULT 'UNKNOWN',

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    last_checked_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (environment_id, service_name),

    CONSTRAINT service_name_nonempty
        CHECK (LENGTH(TRIM(service_name)) > 0)
);

CREATE INDEX idx_services_environment
    ON monitored_services(environment_id);

CREATE INDEX idx_services_status
    ON monitored_services(current_status, enabled);

-- ============================================================
-- 5. HEALTH CHECK DEFINITIONS
-- ============================================================

CREATE TABLE health_checks (
    check_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES monitored_services(service_id)
        ON DELETE CASCADE,

    check_name VARCHAR(120) NOT NULL,

    check_category check_type NOT NULL,

    endpoint TEXT,

    timeout_ms INTEGER NOT NULL DEFAULT 3000,

    warning_latency_ms NUMERIC(12,2) NOT NULL DEFAULT 500,

    critical_latency_ms NUMERIC(12,2) NOT NULL DEFAULT 1500,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (service_id, check_name),

    CHECK (timeout_ms > 0),

    CHECK (warning_latency_ms >= 0),

    CHECK (critical_latency_ms >= warning_latency_ms)
);

CREATE INDEX idx_health_checks_service
    ON health_checks(service_id, enabled);

-- ============================================================
-- 6. MONITORING RUNS
-- ============================================================

CREATE TABLE monitoring_runs (
    run_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES monitored_services(service_id),

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    execution_status health_status NOT NULL DEFAULT 'UNKNOWN',

    execution_error TEXT,

    CHECK (
        completed_at IS NULL OR completed_at >= started_at
    )
);

CREATE INDEX idx_monitoring_runs_service_time
    ON monitoring_runs(service_id, started_at DESC);

-- ============================================================
-- 7. HEALTH CHECK RESULTS
-- ============================================================

CREATE TABLE health_check_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    run_id BIGINT NOT NULL
        REFERENCES monitoring_runs(run_id)
        ON DELETE CASCADE,

    check_id BIGINT NOT NULL
        REFERENCES health_checks(check_id),

    status health_status NOT NULL,

    latency_ms NUMERIC(12,2) NOT NULL,

    message TEXT,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (run_id, check_id),

    CHECK (latency_ms >= 0),

    CHECK (jsonb_typeof(metadata) = 'object')
);

CREATE INDEX idx_results_check_time
    ON health_check_results(check_id, checked_at DESC);

CREATE INDEX idx_results_status_time
    ON health_check_results(status, checked_at DESC);

CREATE INDEX idx_results_metadata
    ON health_check_results USING GIN(metadata);

-- ============================================================
-- 8. ALERT POLICIES
-- ============================================================

CREATE TABLE alert_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES monitored_services(service_id)
        ON DELETE CASCADE,

    policy_name VARCHAR(120) NOT NULL,

    warning_latency_ms NUMERIC(12,2) NOT NULL,

    critical_latency_ms NUMERIC(12,2) NOT NULL,

    failure_threshold INTEGER NOT NULL DEFAULT 2,

    recovery_threshold INTEGER NOT NULL DEFAULT 2,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (service_id, policy_name),

    CHECK (warning_latency_ms >= 0),

    CHECK (critical_latency_ms >= warning_latency_ms),

    CHECK (failure_threshold >= 1),

    CHECK (recovery_threshold >= 1)
);

CREATE INDEX idx_alert_policies_service
    ON alert_policies(service_id, enabled);

-- ============================================================
-- 9. ALERTS
-- ============================================================

CREATE TABLE alerts (
    alert_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES monitored_services(service_id),

    policy_id BIGINT
        REFERENCES alert_policies(policy_id)
        ON DELETE SET NULL,

    severity alert_severity NOT NULL,

    state alert_state NOT NULL DEFAULT 'FIRING',

    message TEXT NOT NULL,

    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    acknowledged_at TIMESTAMPTZ,

    resolved_at TIMESTAMPTZ,

    occurrence_count INTEGER NOT NULL DEFAULT 1,

    CHECK (occurrence_count >= 1),

    CHECK (last_seen >= first_seen),

    CHECK (
        resolved_at IS NULL OR resolved_at >= first_seen
    ),

    CHECK (
        (state = 'RESOLVED' AND resolved_at IS NOT NULL)
        OR
        (state <> 'RESOLVED' AND resolved_at IS NULL)
    )
);

-- A service can have only one active firing alert.
CREATE UNIQUE INDEX uq_active_firing_alert
    ON alerts(service_id)
    WHERE state = 'FIRING';

CREATE INDEX idx_alerts_active
    ON alerts(state, severity, last_seen DESC);

-- ============================================================
-- 10. MONITORING EVENT AUDIT
-- ============================================================

CREATE TABLE monitoring_audit (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT
        REFERENCES monitored_services(service_id)
        ON DELETE SET NULL,

    event_type VARCHAR(80) NOT NULL,

    event_details JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CHECK (jsonb_typeof(event_details) = 'object')
);

CREATE INDEX idx_audit_service_time
    ON monitoring_audit(service_id, occurred_at DESC);

-- ============================================================
-- 11. ALERT STATE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_alert_transition()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN

        IF OLD.state = 'RESOLVED' THEN
            RAISE EXCEPTION
                'Resolved alerts cannot be reopened';
        END IF;

        IF OLD.state = 'ACKNOWLEDGED'
           AND NEW.state = 'FIRING' THEN
            RAISE EXCEPTION
                'Acknowledged alerts cannot return to firing';
        END IF;

        IF OLD.state = 'FIRING'
           AND NEW.state = 'ACKNOWLEDGED'
           AND NEW.acknowledged_at IS NULL THEN
            NEW.acknowledged_at := NOW();
        END IF;

        IF NEW.state = 'RESOLVED'
           AND NEW.resolved_at IS NULL THEN
            NEW.resolved_at := NOW();
        END IF;

    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_alert_transition
BEFORE UPDATE ON alerts
FOR EACH ROW
EXECUTE FUNCTION validate_alert_transition();

-- ============================================================
-- 12. SERVICE STATUS AUDIT
-- ============================================================

CREATE OR REPLACE FUNCTION audit_service_status_change()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.current_status IS DISTINCT FROM NEW.current_status THEN

        INSERT INTO monitoring_audit (
            service_id,
            event_type,
            event_details
        )
        VALUES (
            NEW.service_id,
            'SERVICE_STATUS_CHANGED',
            jsonb_build_object(
                'previous_status', OLD.current_status,
                'new_status', NEW.current_status
            )
        );

    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_service_status_audit
AFTER UPDATE OF current_status ON monitored_services
FOR EACH ROW
EXECUTE FUNCTION audit_service_status_change();

-- ============================================================
-- 13. COMPLETE A MONITORING RUN
-- ============================================================

CREATE OR REPLACE FUNCTION complete_monitoring_run(
    p_run_id BIGINT
)
RETURNS health_status
LANGUAGE plpgsql
AS $$
DECLARE
    v_service_id BIGINT;
    v_status health_status;
    v_result_count INTEGER;
BEGIN
    SELECT service_id
    INTO v_service_id
    FROM monitoring_runs
    WHERE run_id = p_run_id
      AND completed_at IS NULL
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Monitoring run % does not exist or is already completed',
            p_run_id;
    END IF;

    SELECT
        COUNT(*),
        CASE
            WHEN BOOL_OR(status = 'UNHEALTHY')
                THEN 'UNHEALTHY'::health_status
            WHEN BOOL_OR(status = 'DEGRADED')
                THEN 'DEGRADED'::health_status
            WHEN COUNT(*) > 0
                 AND BOOL_AND(status = 'HEALTHY')
                THEN 'HEALTHY'::health_status
            ELSE 'UNKNOWN'::health_status
        END
    INTO v_result_count, v_status
    FROM health_check_results
    WHERE run_id = p_run_id;

    IF v_result_count = 0 THEN
        v_status := 'UNKNOWN';
    END IF;

    UPDATE monitoring_runs
    SET
        completed_at = NOW(),
        execution_status = v_status
    WHERE run_id = p_run_id;

    UPDATE monitored_services
    SET
        current_status = v_status,
        last_checked_at = NOW()
    WHERE service_id = v_service_id;

    RETURN v_status;
END;
$$;

-- ============================================================
-- 14. ALERT PROCESSING PROCEDURE
-- ============================================================

CREATE OR REPLACE PROCEDURE process_service_alert(
    p_service_id BIGINT,
    p_policy_id BIGINT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status health_status;
    v_warning NUMERIC(12,2);
    v_critical NUMERIC(12,2);
    v_severity alert_severity;
    v_message TEXT;
BEGIN
    SELECT current_status
    INTO v_status
    FROM monitored_services
    WHERE service_id = p_service_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Service does not exist';
    END IF;

    SELECT warning_latency_ms, critical_latency_ms
    INTO v_warning, v_critical
    FROM alert_policies
    WHERE policy_id = p_policy_id
      AND service_id = p_service_id
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'No applicable alert policy';
    END IF;

    IF v_status IN ('HEALTHY', 'UNKNOWN') THEN

        UPDATE alerts
        SET
            state = 'RESOLVED',
            resolved_at = NOW(),
            last_seen = NOW()
        WHERE service_id = p_service_id
          AND state = 'FIRING';

        RETURN;
    END IF;

    v_severity := CASE
        WHEN v_status = 'UNHEALTHY'
            THEN 'CRITICAL'::alert_severity
        ELSE 'WARNING'::alert_severity
    END;

    v_message := 'Service status: ' || v_status::TEXT;

    INSERT INTO alerts (
        service_id,
        policy_id,
        severity,
        state,
        message
    )
    VALUES (
        p_service_id,
        p_policy_id,
        v_severity,
        'FIRING',
        v_message
    )
    ON CONFLICT (service_id)
        WHERE state = 'FIRING'
    DO UPDATE SET
        severity = EXCLUDED.severity,
        message = EXCLUDED.message,
        last_seen = NOW(),
        occurrence_count = alerts.occurrence_count + 1;

END;
$$;

-- ============================================================
-- 15. METRICS VIEW
-- ============================================================

CREATE OR REPLACE VIEW service_metrics AS
SELECT
    s.service_id,
    s.service_name,
    e.environment_name,
    a.application_name,
    s.current_status,

    COUNT(r.result_id) AS total_checks,

    COUNT(r.result_id) FILTER (
        WHERE r.status = 'HEALTHY'
    ) AS successful_checks,

    COUNT(r.result_id) FILTER (
        WHERE r.status = 'UNHEALTHY'
    ) AS failed_checks,

    ROUND(
        AVG(r.latency_ms),
        2
    ) AS average_latency_ms,

    ROUND(
        MAX(r.latency_ms),
        2
    ) AS maximum_latency_ms,

    ROUND(
        100.0 *
        COUNT(r.result_id) FILTER (
            WHERE r.status = 'HEALTHY'
        ) /
        NULLIF(COUNT(r.result_id), 0),
        2
    ) AS availability_percent

FROM monitored_services s

JOIN environments e
    ON e.environment_id = s.environment_id

JOIN applications a
    ON a.application_id = e.application_id

LEFT JOIN monitoring_runs mr
    ON mr.service_id = s.service_id

LEFT JOIN health_check_results r
    ON r.run_id = mr.run_id

GROUP BY
    s.service_id,
    s.service_name,
    e.environment_name,
    a.application_name,
    s.current_status;

-- ============================================================
-- 16. ACTIVE ALERT DASHBOARD VIEW
-- ============================================================

CREATE OR REPLACE VIEW active_alert_dashboard AS
SELECT
    al.alert_id,
    a.application_name,
    e.environment_name,
    s.service_name,
    al.severity,
    al.state,
    al.message,
    al.first_seen,
    al.last_seen,
    al.occurrence_count

FROM alerts al

JOIN monitored_services s
    ON s.service_id = al.service_id

JOIN environments e
    ON e.environment_id = s.environment_id

JOIN applications a
    ON a.application_id = e.application_id

WHERE al.state IN ('FIRING', 'ACKNOWLEDGED');

-- ============================================================
-- 17. HEALTH CHECK ELIGIBILITY
-- ============================================================

CREATE OR REPLACE FUNCTION eligible_health_checks(
    p_service_id BIGINT
)
RETURNS TABLE (
    check_id BIGINT,
    check_name VARCHAR(120),
    check_category check_type,
    timeout_ms INTEGER
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        hc.check_id,
        hc.check_name,
        hc.check_category,
        hc.timeout_ms
    FROM health_checks hc
    JOIN monitored_services s
        ON s.service_id = hc.service_id
    JOIN environments e
        ON e.environment_id = s.environment_id
    WHERE hc.service_id = p_service_id
      AND hc.enabled = TRUE
      AND s.enabled = TRUE
      AND e.active = TRUE
    ORDER BY hc.check_id;
$$;

-- ============================================================
-- 18. SAMPLE APPLICATION DATA
-- ============================================================

INSERT INTO applications (
    application_name,
    description,
    owner_team
)
VALUES
(
    'Payment Platform',
    'Enterprise payment processing application',
    'Payments Engineering'
),
(
    'Analytics Platform',
    'Business analytics and reporting application',
    'Data Engineering'
);

INSERT INTO environments (
    application_id,
    environment_name
)
SELECT application_id, 'PRODUCTION'
FROM applications
WHERE application_name = 'Payment Platform';

INSERT INTO environments (
    application_id,
    environment_name
)
SELECT application_id, 'STAGING'
FROM applications
WHERE application_name = 'Analytics Platform';

INSERT INTO monitored_services (
    environment_id,
    service_name,
    current_status
)
SELECT
    environment_id,
    'payment-api',
    'HEALTHY'
FROM environments
WHERE environment_name = 'PRODUCTION';

INSERT INTO monitored_services (
    environment_id,
    service_name,
    current_status
)
SELECT
    environment_id,
    'payment-database',
    'DEGRADED'
FROM environments
WHERE environment_name = 'PRODUCTION';

INSERT INTO monitored_services (
    environment_id,
    service_name,
    current_status
)
SELECT
    environment_id,
    'analytics-worker',
    'UNKNOWN'
FROM environments
WHERE environment_name = 'STAGING';

-- ============================================================
-- 19. HEALTH CHECK CONFIGURATION
-- ============================================================

INSERT INTO health_checks (
    service_id,
    check_name,
    check_category,
    endpoint,
    timeout_ms,
    warning_latency_ms,
    critical_latency_ms
)
SELECT
    service_id,
    'application-liveness',
    'HTTP',
    '/health/live',
    3000,
    300,
    1000
FROM monitored_services
WHERE service_name = 'payment-api';

INSERT INTO health_checks (
    service_id,
    check_name,
    check_category,
    endpoint,
    timeout_ms,
    warning_latency_ms,
    critical_latency_ms
)
SELECT
    service_id,
    'database-connectivity',
    'DATABASE',
    NULL,
    3000,
    500,
    1500
FROM monitored_services
WHERE service_name = 'payment-database';

INSERT INTO health_checks (
    service_id,
    check_name,
    check_category,
    endpoint,
    timeout_ms
)
SELECT
    service_id,
    'worker-dependency',
    'DEPENDENCY',
    NULL,
    5000
FROM monitored_services
WHERE service_name = 'analytics-worker';

-- ============================================================
-- 20. ALERT POLICY CONFIGURATION
-- ============================================================

INSERT INTO alert_policies (
    service_id,
    policy_name,
    warning_latency_ms,
    critical_latency_ms,
    failure_threshold,
    recovery_threshold
)
SELECT
    service_id,
    'production-default',
    500,
    1500,
    2,
    2
FROM monitored_services
WHERE service_name IN (
    'payment-api',
    'payment-database'
);

-- ============================================================
-- 21. SAMPLE MONITORING RUNS
-- ============================================================

INSERT INTO monitoring_runs (
    service_id,
    execution_status
)
SELECT service_id, 'UNKNOWN'
FROM monitored_services
WHERE service_name IN (
    'payment-api',
    'payment-database'
);

-- ============================================================
-- 22. SAMPLE HEALTH RESULTS
-- ============================================================

INSERT INTO health_check_results (
    run_id,
    check_id,
    status,
    latency_ms,
    message,
    metadata
)
SELECT
    mr.run_id,
    hc.check_id,
    'HEALTHY',
    120,
    'Application responding normally',
    '{"http_status": 200, "endpoint": "/health/live"}'::JSONB
FROM monitoring_runs mr
JOIN health_checks hc
    ON hc.service_id = mr.service_id
WHERE hc.check_name = 'application-liveness';

INSERT INTO health_check_results (
    run_id,
    check_id,
    status,
    latency_ms,
    message,
    metadata
)
SELECT
    mr.run_id,
    hc.check_id,
    'UNHEALTHY',
    1800,
    'Database connection timeout',
    '{"connection": "timeout", "retryable": true}'::JSONB
FROM monitoring_runs mr
JOIN health_checks hc
    ON hc.service_id = mr.service_id
WHERE hc.check_name = 'database-connectivity';

-- ============================================================
-- 23. COMPLETE SAMPLE RUNS
-- ============================================================

DO $$
DECLARE
    item RECORD;
BEGIN
    FOR item IN
        SELECT run_id
        FROM monitoring_runs
    LOOP
        PERFORM complete_monitoring_run(item.run_id);
    END LOOP;
END;
$$;

-- ============================================================
-- 24. SAMPLE ALERT GENERATION
-- ============================================================

DO $$
DECLARE
    v_service_id BIGINT;
    v_policy_id BIGINT;
BEGIN
    SELECT s.service_id, p.policy_id
    INTO v_service_id, v_policy_id
    FROM monitored_services s
    JOIN alert_policies p
        ON p.service_id = s.service_id
    WHERE s.service_name = 'payment-database'
      AND p.enabled = TRUE;

    IF FOUND THEN
        CALL process_service_alert(
            v_service_id,
            v_policy_id
        );
    END IF;
END;
$$;

-- ============================================================
-- 25. SAMPLE ALERT ACKNOWLEDGEMENT
-- ============================================================

UPDATE alerts
SET
    state = 'ACKNOWLEDGED',
    acknowledged_at = NOW()
WHERE service_id = (
    SELECT service_id
    FROM monitored_services
    WHERE service_name = 'payment-database'
)
AND state = 'FIRING';

-- ============================================================
-- 26. RETRIEVAL QUERIES
-- ============================================================

-- Registered services and their environments.

SELECT
    a.application_name,
    e.environment_name,
    s.service_name,
    s.current_status,
    s.enabled
FROM applications a
JOIN environments e
    ON e.application_id = a.application_id
JOIN monitored_services s
    ON s.environment_id = e.environment_id
ORDER BY a.application_name, s.service_name;

-- Available health checks for a service.

SELECT *
FROM eligible_health_checks(
    (
        SELECT service_id
        FROM monitored_services
        WHERE service_name = 'payment-api'
    )
);

-- ============================================================
-- 27. VALIDATION QUERIES
-- ============================================================

-- Detect services without enabled health checks.

SELECT
    s.service_id,
    s.service_name
FROM monitored_services s
LEFT JOIN health_checks hc
    ON hc.service_id = s.service_id
   AND hc.enabled = TRUE
WHERE s.enabled = TRUE
GROUP BY s.service_id, s.service_name
HAVING COUNT(hc.check_id) = 0;

-- Detect checks exceeding their configured critical latency.

SELECT
    hc.check_name,
    s.service_name,
    r.latency_ms,
    hc.critical_latency_ms
FROM health_check_results r
JOIN health_checks hc
    ON hc.check_id = r.check_id
JOIN monitored_services s
    ON s.service_id = hc.service_id
WHERE r.latency_ms >= hc.critical_latency_ms;

-- ============================================================
-- 28. AGGREGATION AND REPORTING
-- ============================================================

SELECT *
FROM service_metrics
ORDER BY availability_percent NULLS LAST;

SELECT *
FROM active_alert_dashboard
ORDER BY
    CASE severity
        WHEN 'CRITICAL' THEN 1
        WHEN 'WARNING' THEN 2
        ELSE 3
    END,
    first_seen DESC;

-- Environment-level availability.

SELECT
    environment_name,
    COUNT(*) AS total_services,
    COUNT(*) FILTER (
        WHERE current_status = 'HEALTHY'
    ) AS healthy_services,
    COUNT(*) FILTER (
        WHERE current_status = 'DEGRADED'
    ) AS degraded_services,
    COUNT(*) FILTER (
        WHERE current_status = 'UNHEALTHY'
    ) AS unhealthy_services,
    COUNT(*) FILTER (
        WHERE current_status = 'UNKNOWN'
    ) AS unknown_services
FROM service_metrics
GROUP BY environment_name
ORDER BY environment_name;

-- ============================================================
-- 29. COMMON TABLE EXPRESSION: RECENT FAILURES
-- ============================================================

WITH recent_failures AS (
    SELECT
        s.service_name,
        hc.check_name,
        r.status,
        r.latency_ms,
        r.checked_at,
        ROW_NUMBER() OVER (
            PARTITION BY hc.check_id
            ORDER BY r.checked_at DESC
        ) AS failure_rank
    FROM health_check_results r
    JOIN health_checks hc
        ON hc.check_id = r.check_id
    JOIN monitored_services s
        ON s.service_id = hc.service_id
    WHERE r.status = 'UNHEALTHY'
      AND r.checked_at >= NOW() - INTERVAL '24 hours'
)
SELECT
    service_name,
    check_name,
    latency_ms,
    checked_at
FROM recent_failures
WHERE failure_rank <= 5
ORDER BY checked_at DESC;

-- ============================================================
-- 30. WORKFLOW PROCESSING
-- ============================================================

-- Create a new monitoring run transactionally.
-- The caller can add health results before completion.

CREATE OR REPLACE PROCEDURE start_monitoring_run(
    p_service_id BIGINT,
    INOUT p_run_id BIGINT DEFAULT NULL
)
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM monitored_services s
        JOIN environments e
            ON e.environment_id = s.environment_id
        WHERE s.service_id = p_service_id
          AND s.enabled = TRUE
          AND e.active = TRUE
    ) THEN
        RAISE EXCEPTION
            'Service is not eligible for monitoring';
    END IF;

    INSERT INTO monitoring_runs (
        service_id,
        execution_status
    )
    VALUES (
        p_service_id,
        'UNKNOWN'
    )
    RETURNING run_id INTO p_run_id;
END;
$$;

-- ============================================================
-- 31. TRANSACTIONAL MONITORING EXAMPLE
-- ============================================================

DO $$
DECLARE
    v_service_id BIGINT;
    v_check_id BIGINT;
    v_run_id BIGINT;
BEGIN
    SELECT s.service_id
    INTO v_service_id
    FROM monitored_services s
    WHERE s.service_name = 'payment-api';

    SELECT check_id
    INTO v_check_id
    FROM health_checks
    WHERE service_id = v_service_id
      AND check_name = 'application-liveness';

    IF v_service_id IS NOT NULL
       AND v_check_id IS NOT NULL THEN

        CALL start_monitoring_run(
            v_service_id,
            v_run_id
        );

        INSERT INTO health_check_results (
            run_id,
            check_id,
            status,
            latency_ms,
            message,
            metadata
        )
        VALUES (
            v_run_id,
            v_check_id,
            'HEALTHY',
            135,
            'Transactional monitoring execution',
            '{"http_status": 200}'::JSONB
        );

        PERFORM complete_monitoring_run(v_run_id);

    END IF;
END;
$$;

-- ============================================================
-- 32. AUDIT RETRIEVAL
-- ============================================================

SELECT
    audit_id,
    service_id,
    event_type,
    event_details,
    occurred_at
FROM monitoring_audit
ORDER BY occurred_at DESC;

-- ============================================================
-- 33. OPERATIONAL DIAGNOSTICS
-- ============================================================

-- Current unresolved alerts.

SELECT
    service_name,
    severity,
    state,
    message,
    occurrence_count,
    first_seen
FROM active_alert_dashboard;

-- Monitoring execution errors.

SELECT
    run_id,
    service_id,
    started_at,
    execution_error
FROM monitoring_runs
WHERE execution_error IS NOT NULL
ORDER BY started_at DESC;

-- Recent monitoring activity.

SELECT
    service_id,
    COUNT(*) AS runs_last_24_hours,
    MAX(completed_at) AS latest_completion
FROM monitoring_runs
WHERE started_at >= NOW() - INTERVAL '24 hours'
GROUP BY service_id;

COMMIT;

-- ============================================================
-- SECURITY AND OPERATIONAL NOTES
-- ============================================================
--
-- 1. Application credentials and secrets must not be stored in
--    health-check metadata or monitoring result messages.
--
-- 2. Use a restricted database role for monitoring ingestion.
--
-- 3. Separate read-only dashboard access from alert-management
--    permissions.
--
-- 4. Apply row-level security when multiple tenants share the
--    same monitoring database.
--
-- 5. Partition large health_check_results and monitoring_runs
--    tables by time in high-volume deployments.
--
-- 6. Configure retention and archival for monitoring history.
--
-- 7. Use authenticated internal endpoints for administrative
--    health checks. Avoid exposing dependency diagnostics to
--    unauthenticated public callers.
--
-- 8. A successful database transaction does not prove that
--    an external notification was delivered. Notification
--    delivery should use a durable outbox and retry mechanism.
--
-- 9. Service status in this schema is based on the latest
--    completed monitoring run, not a guarantee of continuous
--    availability.
-- ============================================================
