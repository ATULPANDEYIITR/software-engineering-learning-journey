-- ============================================================
-- OBSERVABILITY ENGINEERING
-- Logs, Metrics, Distributed Traces and Alert Management
--
-- PostgreSQL 15+
--
-- Models:
--   Services
--   Structured logs
--   Metric definitions and samples
--   Distributed traces
--   Trace spans
--   Span events
--   Alert policies
--   Alert evaluation history
--   Alert state transitions
--   Telemetry correlation
--
-- The script is repeatable and uses a dedicated schema.
-- ============================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS observability;

SET search_path TO observability, public;

-- ============================================================
-- 1. ENUMERATED DOMAIN TYPES
-- ============================================================

CREATE TYPE log_severity AS ENUM (
    'DEBUG',
    'INFO',
    'WARNING',
    'ERROR',
    'CRITICAL'
);

CREATE TYPE metric_type AS ENUM (
    'COUNTER',
    'GAUGE',
    'HISTOGRAM'
);

CREATE TYPE span_status AS ENUM (
    'UNSET',
    'OK',
    'ERROR'
);

CREATE TYPE alert_state AS ENUM (
    'NORMAL',
    'FIRING',
    'RESOLVED'
);

CREATE TYPE alert_operator AS ENUM (
    'GT',
    'GTE',
    'LT',
    'LTE'
);

-- ============================================================
-- 2. SERVICES
-- ============================================================

CREATE TABLE IF NOT EXISTS services (
    service_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_name VARCHAR(128) NOT NULL UNIQUE,

    environment VARCHAR(32) NOT NULL DEFAULT 'production',

    team_name VARCHAR(128) NOT NULL,

    service_version VARCHAR(64) NOT NULL,

    active BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT service_name_format
        CHECK (service_name ~ '^[A-Za-z0-9_.:/-]+$'),

    CONSTRAINT environment_valid
        CHECK (
            environment IN (
                'development',
                'testing',
                'staging',
                'production'
            )
        )
);

-- ============================================================
-- 3. TRACE MODEL
-- ============================================================

CREATE TABLE IF NOT EXISTS traces (
    trace_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    root_service_id BIGINT NOT NULL
        REFERENCES services(service_id),

    operation_name VARCHAR(256) NOT NULL,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    ended_at TIMESTAMPTZ,

    trace_status span_status NOT NULL DEFAULT 'UNSET',

    CONSTRAINT trace_time_valid
        CHECK (
            ended_at IS NULL OR ended_at >= started_at
        )
);

CREATE TABLE IF NOT EXISTS spans (
    span_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    trace_id UUID NOT NULL
        REFERENCES traces(trace_id)
        ON DELETE CASCADE,

    parent_span_id UUID,

    service_id BIGINT NOT NULL
        REFERENCES services(service_id),

    operation_name VARCHAR(256) NOT NULL,

    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    ended_at TIMESTAMPTZ,

    status span_status NOT NULL DEFAULT 'UNSET',

    duration_ms NUMERIC(16, 4)
        GENERATED ALWAYS AS (
            CASE
                WHEN ended_at IS NULL THEN NULL
                ELSE EXTRACT(EPOCH FROM (ended_at - started_at))
                     * 1000
            END
        ) STORED,

    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT span_time_valid
        CHECK (
            ended_at IS NULL OR ended_at >= started_at
        ),

    CONSTRAINT span_attributes_object
        CHECK (jsonb_typeof(attributes) = 'object'),

    CONSTRAINT span_not_own_parent
        CHECK (parent_span_id IS NULL OR parent_span_id <> span_id),

    CONSTRAINT span_parent_fk
        FOREIGN KEY (parent_span_id)
        REFERENCES spans(span_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_spans_trace
    ON spans(trace_id);

CREATE INDEX IF NOT EXISTS idx_spans_service_time
    ON spans(service_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_spans_error_time
    ON spans(started_at DESC)
    WHERE status = 'ERROR';

-- ============================================================
-- 4. SPAN EVENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS span_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    span_id UUID NOT NULL
        REFERENCES spans(span_id)
        ON DELETE CASCADE,

    event_name VARCHAR(128) NOT NULL,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT span_event_attributes_object
        CHECK (jsonb_typeof(attributes) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_span_events_span_time
    ON span_events(span_id, occurred_at);

-- ============================================================
-- 5. STRUCTURED LOGGING
-- ============================================================

CREATE TABLE IF NOT EXISTS logs (
    log_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES services(service_id),

    trace_id UUID
        REFERENCES traces(trace_id),

    span_id UUID
        REFERENCES spans(span_id),

    severity log_severity NOT NULL,

    message TEXT NOT NULL,

    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT log_message_valid
        CHECK (
            length(message) BETWEEN 1 AND 4096
        ),

    CONSTRAINT log_attributes_object
        CHECK (jsonb_typeof(attributes) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_logs_service_time
    ON logs(service_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_logs_trace
    ON logs(trace_id)
    WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_logs_error_time
    ON logs(occurred_at DESC)
    WHERE severity IN ('ERROR', 'CRITICAL');

CREATE INDEX IF NOT EXISTS idx_logs_attributes
    ON logs USING GIN(attributes);

-- ============================================================
-- 6. METRIC DEFINITIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS metric_definitions (
    metric_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    service_id BIGINT NOT NULL
        REFERENCES services(service_id),

    metric_name VARCHAR(128) NOT NULL,

    metric_kind metric_type NOT NULL,

    unit VARCHAR(32) NOT NULL,

    description TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT metric_name_format
        CHECK (metric_name ~ '^[A-Za-z0-9_.:/-]+$'),

    CONSTRAINT metric_service_unique
        UNIQUE(service_id, metric_name)
);

CREATE TABLE IF NOT EXISTS metric_samples (
    sample_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    metric_id BIGINT NOT NULL
        REFERENCES metric_definitions(metric_id),

    observed_value DOUBLE PRECISION NOT NULL,

    observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    labels JSONB NOT NULL DEFAULT '{}'::JSONB,

    CONSTRAINT metric_value_finite
        CHECK (
            observed_value NOT IN (
                'Infinity'::DOUBLE PRECISION,
                '-Infinity'::DOUBLE PRECISION,
                'NaN'::DOUBLE PRECISION
            )
        ),

    CONSTRAINT metric_labels_object
        CHECK (jsonb_typeof(labels) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_metric_samples_time
    ON metric_samples(metric_id, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_metric_samples_labels
    ON metric_samples USING GIN(labels);

-- ============================================================
-- 7. ALERT POLICIES
-- ============================================================

CREATE TABLE IF NOT EXISTS alert_rules (
    alert_rule_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    metric_id BIGINT NOT NULL
        REFERENCES metric_definitions(metric_id),

    rule_name VARCHAR(128) NOT NULL UNIQUE,

    operator alert_operator NOT NULL,

    threshold DOUBLE PRECISION NOT NULL,

    evaluation_window INTEGER NOT NULL DEFAULT 1,

    minimum_samples INTEGER NOT NULL DEFAULT 1,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT alert_threshold_finite
        CHECK (
            threshold NOT IN (
                'Infinity'::DOUBLE PRECISION,
                '-Infinity'::DOUBLE PRECISION,
                'NaN'::DOUBLE PRECISION
            )
        ),

    CONSTRAINT alert_window_valid
        CHECK (
            evaluation_window BETWEEN 1 AND 10000
        ),

    CONSTRAINT alert_minimum_samples_valid
        CHECK (
            minimum_samples BETWEEN 1 AND evaluation_window
        )
);

CREATE TABLE IF NOT EXISTS alert_evaluations (
    evaluation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alert_rule_id BIGINT NOT NULL
        REFERENCES alert_rules(alert_rule_id),

    observed_value DOUBLE PRECISION NOT NULL,

    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    state alert_state NOT NULL,

    CONSTRAINT alert_observation_finite
        CHECK (
            observed_value NOT IN (
                'Infinity'::DOUBLE PRECISION,
                '-Infinity'::DOUBLE PRECISION,
                'NaN'::DOUBLE PRECISION
            )
        )
);

CREATE INDEX IF NOT EXISTS idx_alert_evaluations_rule_time
    ON alert_evaluations(alert_rule_id, evaluated_at DESC);

CREATE TABLE IF NOT EXISTS alert_transitions (
    transition_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    alert_rule_id BIGINT NOT NULL
        REFERENCES alert_rules(alert_rule_id),

    previous_state alert_state NOT NULL,

    current_state alert_state NOT NULL,

    observed_value DOUBLE PRECISION NOT NULL,

    transitioned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT transition_state_changed
        CHECK (previous_state <> current_state)
);

-- ============================================================
-- 8. SECURITY: SENSITIVE ATTRIBUTE REDACTION
-- ============================================================

CREATE OR REPLACE FUNCTION sanitize_telemetry_attributes(
    p_attributes JSONB
)
RETURNS JSONB
LANGUAGE SQL
IMMUTABLE
AS $$
    SELECT COALESCE(
        jsonb_object_agg(
            key,
            CASE
                WHEN lower(key) IN (
                    'password',
                    'token',
                    'access_token',
                    'refresh_token',
                    'authorization',
                    'api_key',
                    'secret',
                    'credit_card',
                    'ssn'
                )
                THEN '"[REDACTED]"'::JSONB
                ELSE value
            END
        ),
        '{}'::JSONB
    )
    FROM jsonb_each(
        CASE
            WHEN jsonb_typeof(p_attributes) = 'object'
            THEN p_attributes
            ELSE '{}'::JSONB
        END
    );
$$;

CREATE OR REPLACE FUNCTION redact_log_attributes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.attributes :=
        sanitize_telemetry_attributes(NEW.attributes);

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_redact_log_attributes ON logs;

CREATE TRIGGER trg_redact_log_attributes
BEFORE INSERT OR UPDATE OF attributes
ON logs
FOR EACH ROW
EXECUTE FUNCTION redact_log_attributes();

CREATE OR REPLACE FUNCTION redact_span_attributes()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.attributes :=
        sanitize_telemetry_attributes(NEW.attributes);

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_redact_span_attributes ON spans;

CREATE TRIGGER trg_redact_span_attributes
BEFORE INSERT OR UPDATE OF attributes
ON spans
FOR EACH ROW
EXECUTE FUNCTION redact_span_attributes();

-- ============================================================
-- 9. SPAN INTEGRITY
-- ============================================================

CREATE OR REPLACE FUNCTION validate_span_relationship()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    parent_trace UUID;
    parent_ended_at TIMESTAMPTZ;
BEGIN
    IF NEW.parent_span_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT trace_id, ended_at
    INTO parent_trace, parent_ended_at
    FROM spans
    WHERE span_id = NEW.parent_span_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Parent span does not exist';
    END IF;

    IF parent_trace <> NEW.trace_id THEN
        RAISE EXCEPTION
            'Parent and child spans must belong to the same trace';
    END IF;

    IF parent_ended_at IS NOT NULL
       AND TG_OP = 'INSERT' THEN
        RAISE EXCEPTION
            'Cannot create a child span under a completed parent';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_span_relationship ON spans;

CREATE TRIGGER trg_validate_span_relationship
BEFORE INSERT OR UPDATE OF parent_span_id, trace_id
ON spans
FOR EACH ROW
EXECUTE FUNCTION validate_span_relationship();

-- ============================================================
-- 10. TRACE COMPLETION
-- ============================================================

CREATE OR REPLACE FUNCTION complete_trace(
    p_trace_id UUID
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    total_spans INTEGER;
    active_spans INTEGER;
    error_spans INTEGER;
BEGIN
    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE ended_at IS NULL),
        COUNT(*) FILTER (WHERE status = 'ERROR')
    INTO
        total_spans,
        active_spans,
        error_spans
    FROM spans
    WHERE trace_id = p_trace_id;

    IF total_spans = 0 THEN
        RAISE EXCEPTION 'Trace has no spans';
    END IF;

    IF active_spans > 0 THEN
        RAISE EXCEPTION
            'Trace cannot complete while spans are active';
    END IF;

    UPDATE traces
    SET
        ended_at = NOW(),
        trace_status = CASE
            WHEN error_spans > 0 THEN 'ERROR'::span_status
            ELSE 'OK'::span_status
        END
    WHERE trace_id = p_trace_id;
END;
$$;

-- ============================================================
-- 11. ALERT EVALUATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION evaluate_alert(
    p_rule_id BIGINT,
    p_observed_value DOUBLE PRECISION
)
RETURNS alert_state
LANGUAGE plpgsql
AS $$
DECLARE
    rule_record RECORD;
    sample_average DOUBLE PRECISION;
    sample_count INTEGER;
    should_fire BOOLEAN;
    previous alert_state;
    current alert_state;
BEGIN
    IF p_observed_value IS NULL
       OR p_observed_value IN (
           'Infinity'::DOUBLE PRECISION,
           '-Infinity'::DOUBLE PRECISION,
           'NaN'::DOUBLE PRECISION
       ) THEN
        RAISE EXCEPTION 'Invalid alert observation';
    END IF;

    SELECT *
    INTO rule_record
    FROM alert_rules
    WHERE alert_rule_id = p_rule_id
      AND enabled = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Alert rule unavailable or disabled';
    END IF;

    INSERT INTO alert_evaluations (
        alert_rule_id,
        observed_value,
        state
    )
    VALUES (
        p_rule_id,
        p_observed_value,
        'NORMAL'
    );

    SELECT
        AVG(observed_value),
        COUNT(*)
    INTO
        sample_average,
        sample_count
    FROM (
        SELECT observed_value
        FROM alert_evaluations
        WHERE alert_rule_id = p_rule_id
        ORDER BY evaluated_at DESC, evaluation_id DESC
        LIMIT rule_record.evaluation_window
    ) recent;

    IF sample_count < rule_record.minimum_samples THEN
        RETURN 'NORMAL';
    END IF;

    should_fire := CASE rule_record.operator
        WHEN 'GT' THEN sample_average > rule_record.threshold
        WHEN 'GTE' THEN sample_average >= rule_record.threshold
        WHEN 'LT' THEN sample_average < rule_record.threshold
        WHEN 'LTE' THEN sample_average <= rule_record.threshold
    END;

    SELECT current_state
    INTO previous
    FROM alert_transitions
    WHERE alert_rule_id = p_rule_id
    ORDER BY transitioned_at DESC, transition_id DESC
    LIMIT 1;

    previous := COALESCE(previous, 'NORMAL'::alert_state);

    current := CASE
        WHEN should_fire THEN 'FIRING'::alert_state
        ELSE 'NORMAL'::alert_state
    END;

    UPDATE alert_evaluations
    SET state = current
    WHERE evaluation_id = (
        SELECT evaluation_id
        FROM alert_evaluations
        WHERE alert_rule_id = p_rule_id
        ORDER BY evaluated_at DESC, evaluation_id DESC
        LIMIT 1
    );

    IF current <> previous THEN
        INSERT INTO alert_transitions (
            alert_rule_id,
            previous_state,
            current_state,
            observed_value
        )
        VALUES (
            p_rule_id,
            previous,
            current,
            sample_average
        );
    END IF;

    RETURN current;
END;
$$;

-- ============================================================
-- 12. OBSERVABILITY VIEWS
-- ============================================================

CREATE OR REPLACE VIEW v_service_error_summary AS
SELECT
    s.service_name,
    COUNT(l.log_id) AS total_logs,
    COUNT(l.log_id) FILTER (
        WHERE l.severity IN ('ERROR', 'CRITICAL')
    ) AS error_logs,
    ROUND(
        100.0 * COUNT(l.log_id) FILTER (
            WHERE l.severity IN ('ERROR', 'CRITICAL')
        ) / NULLIF(COUNT(l.log_id), 0),
        2
    ) AS error_percentage
FROM services s
LEFT JOIN logs l
    ON l.service_id = s.service_id
GROUP BY s.service_id, s.service_name;

CREATE OR REPLACE VIEW v_trace_summary AS
SELECT
    t.trace_id,
    s.service_name AS root_service,
    t.operation_name,
    t.started_at,
    t.ended_at,
    t.trace_status,
    COUNT(sp.span_id) AS span_count,
    COUNT(sp.span_id) FILTER (
        WHERE sp.status = 'ERROR'
    ) AS failed_spans,
    ROUND(
        MAX(sp.duration_ms),
        3
    ) AS maximum_span_duration_ms
FROM traces t
JOIN services s
    ON s.service_id = t.root_service_id
LEFT JOIN spans sp
    ON sp.trace_id = t.trace_id
GROUP BY
    t.trace_id,
    s.service_name,
    t.operation_name,
    t.started_at,
    t.ended_at,
    t.trace_status;

CREATE OR REPLACE VIEW v_metric_summary AS
SELECT
    s.service_name,
    md.metric_name,
    md.metric_kind,
    md.unit,
    COUNT(ms.sample_id) AS sample_count,
    AVG(ms.observed_value) AS average_value,
    MIN(ms.observed_value) AS minimum_value,
    MAX(ms.observed_value) AS maximum_value,
    MAX(ms.observed_at) AS last_observed_at
FROM metric_definitions md
JOIN services s
    ON s.service_id = md.service_id
LEFT JOIN metric_samples ms
    ON ms.metric_id = md.metric_id
GROUP BY
    s.service_name,
    md.metric_name,
    md.metric_kind,
    md.unit;

CREATE OR REPLACE VIEW v_latest_alert_states AS
SELECT DISTINCT ON (at.alert_rule_id)
    ar.rule_name,
    at.previous_state,
    at.current_state,
    at.observed_value,
    at.transitioned_at
FROM alert_transitions at
JOIN alert_rules ar
    ON ar.alert_rule_id = at.alert_rule_id
ORDER BY
    at.alert_rule_id,
    at.transitioned_at DESC,
    at.transition_id DESC;

-- ============================================================
-- 13. TELEMETRY CORRELATION FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION get_trace_telemetry(
    p_trace_id UUID
)
RETURNS TABLE (
    event_type TEXT,
    service_name VARCHAR,
    event_time TIMESTAMPTZ,
    event_description TEXT,
    span_reference UUID
)
LANGUAGE SQL
STABLE
AS $$
    SELECT
        'LOG'::TEXT,
        s.service_name,
        l.occurred_at,
        l.severity::TEXT || ': ' || l.message,
        l.span_id
    FROM logs l
    JOIN services s
        ON s.service_id = l.service_id
    WHERE l.trace_id = p_trace_id

    UNION ALL

    SELECT
        'SPAN'::TEXT,
        s.service_name,
        sp.started_at,
        sp.operation_name || ' [' || sp.status::TEXT || ']',
        sp.span_id
    FROM spans sp
    JOIN services s
        ON s.service_id = sp.service_id
    WHERE sp.trace_id = p_trace_id

    ORDER BY event_time;
$$;

-- ============================================================
-- 14. SAMPLE SERVICE DATA
-- ============================================================

INSERT INTO services (
    service_name,
    environment,
    team_name,
    service_version
)
VALUES
    (
        'payment-api',
        'production',
        'Payments',
        '2.4.0'
    ),
    (
        'payment-database',
        'production',
        'DataPlatform',
        '16.2'
    ),
    (
        'payment-processor',
        'production',
        'Payments',
        '3.1.0'
    ),
    (
        'inventory-api',
        'staging',
        'Inventory',
        '1.8.0'
    )
ON CONFLICT (service_name) DO NOTHING;

-- ============================================================
-- 15. METRIC DEFINITIONS
-- ============================================================

INSERT INTO metric_definitions (
    service_id,
    metric_name,
    metric_kind,
    unit,
    description
)
SELECT
    service_id,
    metric_name,
    metric_kind::metric_type,
    unit,
    description
FROM services s
CROSS JOIN (
    VALUES
        (
            'payment_requests_total',
            'COUNTER',
            'requests',
            'Total incoming payment requests'
        ),
        (
            'payment_failures_total',
            'COUNTER',
            'requests',
            'Failed payment requests'
        ),
        (
            'payment_latency_ms',
            'HISTOGRAM',
            'milliseconds',
            'Payment request processing duration'
        ),
        (
            'active_connections',
            'GAUGE',
            'connections',
            'Current active connections'
        )
) AS metrics(
    metric_name,
    metric_kind,
    unit,
    description
)
WHERE s.service_name = 'payment-api'
ON CONFLICT (service_id, metric_name) DO NOTHING;

-- ============================================================
-- 16. SAMPLE DISTRIBUTED TRACE
-- ============================================================

DO $$
DECLARE
    payment_service BIGINT;
    database_service BIGINT;
    processor_service BIGINT;

    trace_identifier UUID := gen_random_uuid();

    root_span UUID := gen_random_uuid();
    database_span UUID := gen_random_uuid();
    processor_span UUID := gen_random_uuid();
BEGIN
    SELECT service_id
    INTO payment_service
    FROM services
    WHERE service_name = 'payment-api';

    SELECT service_id
    INTO database_service
    FROM services
    WHERE service_name = 'payment-database';

    SELECT service_id
    INTO processor_service
    FROM services
    WHERE service_name = 'payment-processor';

    INSERT INTO traces (
        trace_id,
        root_service_id,
        operation_name
    )
    VALUES (
        trace_identifier,
        payment_service,
        'POST /payments'
    );

    INSERT INTO spans (
        span_id,
        trace_id,
        parent_span_id,
        service_id,
        operation_name,
        started_at,
        ended_at,
        status,
        attributes
    )
    VALUES (
        root_span,
        trace_identifier,
        NULL,
        payment_service,
        'POST /payments',
        NOW() - INTERVAL '150 milliseconds',
        NOW(),
        'ERROR',
        '{"payment_amount": 1500, "password": "hidden"}'
    );

    INSERT INTO spans (
        span_id,
        trace_id,
        parent_span_id,
        service_id,
        operation_name,
        started_at,
        ended_at,
        status,
        attributes
    )
    VALUES (
        database_span,
        trace_identifier,
        root_span,
        database_service,
        'INSERT payment',
        NOW() - INTERVAL '140 milliseconds',
        NOW() - INTERVAL '110 milliseconds',
        'OK',
        '{"rows_affected": 1}'
    );

    INSERT INTO spans (
        span_id,
        trace_id,
        parent_span_id,
        service_id,
        operation_name,
        started_at,
        ended_at,
        status,
        attributes
    )
    VALUES (
        processor_span,
        trace_identifier,
        root_span,
        processor_service,
        'authorize transaction',
        NOW() - INTERVAL '100 milliseconds',
        NOW(),
        'ERROR',
        '{"processor": "gateway-a"}'
    );

    INSERT INTO span_events (
        span_id,
        event_name,
        attributes
    )
    VALUES (
        processor_span,
        'authorization_failed',
        '{"error_code": "PAYMENT_DECLINED"}'
    );

    INSERT INTO logs (
        service_id,
        trace_id,
        span_id,
        severity,
        message,
        attributes
    )
    VALUES
    (
        payment_service,
        trace_identifier,
        root_span,
        'INFO',
        'Payment request received',
        '{"amount": 1500}'
    ),
    (
        processor_service,
        trace_identifier,
        processor_span,
        'ERROR',
        'Payment authorization failed',
        '{"error_code": "PAYMENT_DECLINED"}'
    );

    PERFORM complete_trace(trace_identifier);
END;
$$;

-- ============================================================
-- 17. SAMPLE METRIC OBSERVATIONS
-- ============================================================

INSERT INTO metric_samples (
    metric_id,
    observed_value,
    labels
)
SELECT
    metric_id,
    sample.value,
    sample.labels::JSONB
FROM metric_definitions md
CROSS JOIN (
    VALUES
        (
            'payment_requests_total',
            1000.0,
            '{"environment":"production"}'
        ),
        (
            'payment_requests_total',
            1200.0,
            '{"environment":"production"}'
        ),
        (
            'payment_failures_total',
            45.0,
            '{"environment":"production"}'
        ),
        (
            'payment_latency_ms',
            125.0,
            '{"endpoint":"/payments"}'
        ),
        (
            'payment_latency_ms',
            180.0,
            '{"endpoint":"/payments"}'
        ),
        (
            'payment_latency_ms',
            250.0,
            '{"endpoint":"/payments"}'
        ),
        (
            'payment_latency_ms',
            300.0,
            '{"endpoint":"/payments"}'
        ),
        (
            'active_connections',
            24.0,
            '{"pool":"primary"}'
        )
) AS sample(metric_name, value, labels)
WHERE md.metric_name = sample.metric_name
AND md.service_id = (
    SELECT service_id
    FROM services
    WHERE service_name = 'payment-api'
);

-- ============================================================
-- 18. SAMPLE ALERT POLICIES
-- ============================================================

INSERT INTO alert_rules (
    metric_id,
    rule_name,
    operator,
    threshold,
    evaluation_window,
    minimum_samples
)
SELECT
    metric_id,
    'payment_latency_high',
    'GT',
    200,
    2,
    2
FROM metric_definitions
WHERE metric_name = 'payment_latency_ms'
AND service_id = (
    SELECT service_id
    FROM services
    WHERE service_name = 'payment-api'
)
ON CONFLICT (rule_name) DO NOTHING;

-- ============================================================
-- 19. ALERT PROCESSING
-- ============================================================

DO $$
DECLARE
    rule_identifier BIGINT;
    result alert_state;
BEGIN
    SELECT alert_rule_id
    INTO rule_identifier
    FROM alert_rules
    WHERE rule_name = 'payment_latency_high';

    result := evaluate_alert(rule_identifier, 240);
    RAISE NOTICE 'First alert evaluation: %', result;

    result := evaluate_alert(rule_identifier, 260);
    RAISE NOTICE 'Second alert evaluation: %', result;
END;
$$;

-- ============================================================
-- 20. RETRIEVAL QUERIES
-- ============================================================

-- Recent errors.
SELECT
    s.service_name,
    l.severity,
    l.message,
    l.trace_id,
    l.occurred_at
FROM logs l
JOIN services s
    ON s.service_id = l.service_id
WHERE l.severity IN ('ERROR', 'CRITICAL')
ORDER BY l.occurred_at DESC;

-- Complete trace hierarchy.
SELECT
    t.trace_id,
    sp.span_id,
    sp.parent_span_id,
    s.service_name,
    sp.operation_name,
    sp.status,
    sp.duration_ms
FROM traces t
JOIN spans sp
    ON sp.trace_id = t.trace_id
JOIN services s
    ON s.service_id = sp.service_id
ORDER BY t.started_at DESC, sp.started_at;

-- ============================================================
-- 21. VALIDATION QUERIES
-- ============================================================

-- Incomplete traces.
SELECT
    t.trace_id,
    COUNT(*) FILTER (
        WHERE sp.ended_at IS NULL
    ) AS active_spans
FROM traces t
JOIN spans sp
    ON sp.trace_id = t.trace_id
GROUP BY t.trace_id
HAVING COUNT(*) FILTER (
    WHERE sp.ended_at IS NULL
) > 0;

-- Logs without distributed trace context.
SELECT
    s.service_name,
    COUNT(*) AS uncorrelated_logs
FROM logs l
JOIN services s
    ON s.service_id = l.service_id
WHERE l.trace_id IS NULL
GROUP BY s.service_name;

-- Failed spans.
SELECT
    s.service_name,
    sp.operation_name,
    sp.duration_ms,
    sp.started_at
FROM spans sp
JOIN services s
    ON s.service_id = sp.service_id
WHERE sp.status = 'ERROR'
ORDER BY sp.started_at DESC;

-- ============================================================
-- 22. AGGREGATION AND PERFORMANCE REPORTING
-- ============================================================

-- Service-level error rates.
SELECT *
FROM v_service_error_summary
ORDER BY error_percentage DESC NULLS LAST;

-- Metric aggregation.
SELECT *
FROM v_metric_summary
ORDER BY service_name, metric_name;

-- Trace latency and error analysis.
SELECT *
FROM v_trace_summary
ORDER BY started_at DESC;

-- Histogram-style percentile calculation.
SELECT
    md.metric_name,
    COUNT(ms.sample_id) AS observations,
    ROUND(AVG(ms.observed_value)::NUMERIC, 3) AS average_value,
    ROUND(
        percentile_cont(0.50) WITHIN GROUP (
            ORDER BY ms.observed_value
        )::NUMERIC,
        3
    ) AS p50,
    ROUND(
        percentile_cont(0.95) WITHIN GROUP (
            ORDER BY ms.observed_value
        )::NUMERIC,
        3
    ) AS p95,
    ROUND(
        percentile_cont(0.99) WITHIN GROUP (
            ORDER BY ms.observed_value
        )::NUMERIC,
        3
    ) AS p99
FROM metric_definitions md
JOIN metric_samples ms
    ON ms.metric_id = md.metric_id
WHERE md.metric_kind = 'HISTOGRAM'
GROUP BY md.metric_name;

-- ============================================================
-- 23. LOG AND TRACE CORRELATION
-- ============================================================

SELECT *
FROM get_trace_telemetry(
    (SELECT trace_id FROM traces LIMIT 1)
);

-- ============================================================
-- 24. ALERT REPORTING
-- ============================================================

SELECT
    ar.rule_name,
    ae.observed_value,
    ae.state,
    ae.evaluated_at
FROM alert_evaluations ae
JOIN alert_rules ar
    ON ar.alert_rule_id = ae.alert_rule_id
ORDER BY ae.evaluated_at DESC;

SELECT *
FROM v_latest_alert_states;

-- ============================================================
-- 25. COMMON TABLE EXPRESSION: SERVICE HEALTH
-- ============================================================

WITH service_activity AS (
    SELECT
        s.service_name,
        COUNT(DISTINCT l.log_id) AS log_count,
        COUNT(DISTINCT sp.span_id) AS span_count,
        COUNT(DISTINCT sp.span_id) FILTER (
            WHERE sp.status = 'ERROR'
        ) AS failed_spans
    FROM services s
    LEFT JOIN logs l
        ON l.service_id = s.service_id
    LEFT JOIN spans sp
        ON sp.service_id = s.service_id
    GROUP BY s.service_name
),
service_health AS (
    SELECT
        service_name,
        log_count,
        span_count,
        failed_spans,
        CASE
            WHEN failed_spans > 0 THEN 'DEGRADED'
            WHEN log_count = 0 AND span_count = 0 THEN 'NO_DATA'
            ELSE 'OBSERVED'
        END AS health_state
    FROM service_activity
)
SELECT *
FROM service_health
ORDER BY service_name;

-- ============================================================
-- 26. TRANSACTIONAL TELEMETRY INGESTION EXAMPLE
-- ============================================================

-- A failed ingestion transaction rolls back the complete batch.
-- The sample below is isolated in a savepoint.

SAVEPOINT telemetry_ingestion;

DO $$
DECLARE
    payment_service BIGINT;
BEGIN
    SELECT service_id
    INTO payment_service
    FROM services
    WHERE service_name = 'payment-api';

    INSERT INTO logs (
        service_id,
        severity,
        message,
        attributes
    )
    VALUES (
        payment_service,
        'INFO',
        'Telemetry ingestion transaction completed',
        '{"batch_id": "batch-2026-001"}'
    );

    RAISE NOTICE 'Telemetry ingestion successful';
END;
$$;

RELEASE SAVEPOINT telemetry_ingestion;

COMMIT;

-- ============================================================
-- 27. OPERATIONAL NOTES
-- ============================================================

-- Retention policies should be implemented through scheduled
-- partition management or controlled deletion.
--
-- Production deployment should also use:
-- 1. Time partitioning for logs and metric_samples.
-- 2. Role-based access control.
-- 3. TLS connections and encrypted storage.
-- 4. Restricted permissions for telemetry ingestion.
-- 5. Bounded metric label cardinality.
-- 6. Sampling for high-volume distributed traces.
-- 7. Monitoring of telemetry ingestion failures.
-- 8. Backups and tested recovery procedures.
--
-- Database constraints protect structural integrity.
-- They do not replace application-level trace propagation,
-- sampling policy, access governance, or retention controls.
