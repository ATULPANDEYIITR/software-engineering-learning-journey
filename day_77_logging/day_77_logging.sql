-- =========================================================
-- STRUCTURED LOGGING, LOG LEVELS AND CORRELATION IDS
-- PostgreSQL 15+
--
-- Implements:
-- Structured JSON logging
-- Severity classification
-- Correlation and request identifiers
-- Distributed request tracking
-- Application and environment metadata
-- Sensitive-field redaction
-- Log retention
-- Aggregation and monitoring
-- Validation and error classification
-- Transactional log insertion
-- =========================================================

BEGIN;

CREATE SCHEMA IF NOT EXISTS observability;

SET search_path TO observability, public;

-- ---------------------------------------------------------
-- 1. Log severity
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS log_levels (
    level_id SMALLINT PRIMARY KEY,
    level_name VARCHAR(20) NOT NULL UNIQUE,
    severity SMALLINT NOT NULL UNIQUE,
    description TEXT NOT NULL,

    CONSTRAINT valid_level_name CHECK (
        level_name IN (
            'DEBUG',
            'INFO',
            'WARNING',
            'ERROR',
            'CRITICAL'
        )
    ),

    CONSTRAINT valid_severity CHECK (
        severity BETWEEN 10 AND 50
    )
);

INSERT INTO log_levels (
    level_id,
    level_name,
    severity,
    description
)
VALUES
    (1, 'DEBUG', 10, 'Detailed diagnostic information'),
    (2, 'INFO', 20, 'Normal application operation'),
    (3, 'WARNING', 30, 'Potential operational problem'),
    (4, 'ERROR', 40, 'Operation failed'),
    (5, 'CRITICAL', 50, 'Critical system failure')
ON CONFLICT DO NOTHING;

-- ---------------------------------------------------------
-- 2. Application registry
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS applications (
    application_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    application_name VARCHAR(120) NOT NULL UNIQUE,

    environment VARCHAR(30) NOT NULL,

    version VARCHAR(40) NOT NULL,

    minimum_severity SMALLINT NOT NULL DEFAULT 20
        REFERENCES log_levels(level_id),

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_environment CHECK (
        environment IN (
            'development',
            'testing',
            'staging',
            'production'
        )
    )
);

INSERT INTO applications (
    application_name,
    environment,
    version,
    minimum_severity
)
VALUES
    ('order-service', 'production', '1.0.0', 2),
    ('payment-service', 'production', '2.1.0', 2),
    ('identity-service', 'staging', '1.5.0', 1),
    ('inventory-service', 'production', '1.2.0', 3)
ON CONFLICT (application_name) DO NOTHING;

-- ---------------------------------------------------------
-- 3. Distributed correlation registry
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS correlation_contexts (
    correlation_id UUID PRIMARY KEY,

    root_request_id UUID NOT NULL,

    parent_correlation_id UUID
        REFERENCES correlation_contexts(correlation_id),

    originating_application_id BIGINT
        REFERENCES applications(application_id),

    initiated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    completed_at TIMESTAMPTZ,

    CONSTRAINT valid_completion_time CHECK (
        completed_at IS NULL OR completed_at >= initiated_at
    )
);

CREATE INDEX IF NOT EXISTS idx_correlation_parent
ON correlation_contexts(parent_correlation_id);

CREATE INDEX IF NOT EXISTS idx_correlation_root_request
ON correlation_contexts(root_request_id);

-- ---------------------------------------------------------
-- 4. Structured log records
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS log_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    application_id BIGINT NOT NULL
        REFERENCES applications(application_id),

    level_id SMALLINT NOT NULL
        REFERENCES log_levels(level_id),

    correlation_id UUID
        REFERENCES correlation_contexts(correlation_id),

    request_id UUID,

    trace_id VARCHAR(128),

    span_id VARCHAR(128),

    event_type VARCHAR(100) NOT NULL,

    message TEXT NOT NULL,

    attributes JSONB NOT NULL DEFAULT '{}'::JSONB,

    exception_type VARCHAR(200),

    exception_message TEXT,

    source_module VARCHAR(150),

    source_function VARCHAR(150),

    source_line INTEGER,

    host_name VARCHAR(150),

    CONSTRAINT valid_message CHECK (
        LENGTH(TRIM(message)) > 0
    ),

    CONSTRAINT valid_event_type CHECK (
        LENGTH(TRIM(event_type)) > 0
    ),

    CONSTRAINT valid_attributes CHECK (
        jsonb_typeof(attributes) = 'object'
    ),

    CONSTRAINT valid_source_line CHECK (
        source_line IS NULL OR source_line > 0
    )
);

-- ---------------------------------------------------------
-- 5. Log policies
-- ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS logging_policies (
    policy_id BIGINT GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    application_id BIGINT NOT NULL
        REFERENCES applications(application_id),

    minimum_level_id SMALLINT NOT NULL
        REFERENCES log_levels(level_id),

    retain_days INTEGER NOT NULL DEFAULT 30,

    capture_exceptions BOOLEAN NOT NULL DEFAULT TRUE,

    enabled BOOLEAN NOT NULL DEFAULT TRUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_application_policy
        UNIQUE (application_id),

    CONSTRAINT valid_retention CHECK (
        retain_days BETWEEN 1 AND 3650
    )
);

INSERT INTO logging_policies (
    application_id,
    minimum_level_id,
    retain_days
)
SELECT
    application_id,
    minimum_severity,
    90
FROM applications
ON CONFLICT (application_id) DO NOTHING;

-- ---------------------------------------------------------
-- 6. Event indexes
-- ---------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_logs_timestamp
ON log_events(event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_logs_application_time
ON log_events(application_id, event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_logs_level_time
ON log_events(level_id, event_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_logs_correlation
ON log_events(correlation_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_logs_request
ON log_events(request_id);

CREATE INDEX IF NOT EXISTS idx_logs_trace
ON log_events(trace_id)
WHERE trace_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_logs_attributes
ON log_events USING GIN(attributes);

-- ---------------------------------------------------------
-- 7. Sensitive-data redaction function
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION redact_log_attributes(
    input_attributes JSONB
)
RETURNS JSONB
LANGUAGE SQL
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT COALESCE(
        jsonb_object_agg(
            key,
            CASE
                WHEN LOWER(key) IN (
                    'password',
                    'token',
                    'access_token',
                    'authorization',
                    'secret',
                    'api_key',
                    'credit_card'
                )
                THEN '"[REDACTED]"'::JSONB

                ELSE value
            END
        ),
        '{}'::JSONB
    )
    FROM jsonb_each(
        CASE
            WHEN jsonb_typeof(input_attributes) = 'object'
            THEN input_attributes
            ELSE '{}'::JSONB
        END
    );
$$;

-- ---------------------------------------------------------
-- 8. Log insertion function
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION write_log_event(
    p_application_name VARCHAR,
    p_level_name VARCHAR,
    p_event_type VARCHAR,
    p_message TEXT,
    p_correlation_id UUID DEFAULT NULL,
    p_request_id UUID DEFAULT NULL,
    p_attributes JSONB DEFAULT '{}'::JSONB,
    p_exception_type VARCHAR DEFAULT NULL,
    p_exception_message TEXT DEFAULT NULL,
    p_trace_id VARCHAR DEFAULT NULL,
    p_span_id VARCHAR DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_application_id BIGINT;
    v_level_id SMALLINT;
    v_severity SMALLINT;
    v_minimum_severity SMALLINT;
    v_event_id BIGINT;
    v_policy_enabled BOOLEAN;
BEGIN

    IF p_message IS NULL OR LENGTH(TRIM(p_message)) = 0 THEN
        RAISE EXCEPTION 'Log message cannot be empty.';
    END IF;

    IF p_event_type IS NULL OR LENGTH(TRIM(p_event_type)) = 0 THEN
        RAISE EXCEPTION 'Event type cannot be empty.';
    END IF;

    IF p_attributes IS NULL OR
       jsonb_typeof(p_attributes) <> 'object' THEN
        RAISE EXCEPTION 'Attributes must be a JSON object.';
    END IF;

    SELECT application_id, minimum_severity, enabled
    INTO v_application_id, v_minimum_severity, v_policy_enabled
    FROM applications
    WHERE application_name = p_application_name;

    IF NOT FOUND OR NOT v_policy_enabled THEN
        RAISE EXCEPTION
            'Application is unknown or disabled: %',
            p_application_name;
    END IF;

    SELECT level_id, severity
    INTO v_level_id, v_severity
    FROM log_levels
    WHERE level_name = UPPER(p_level_name);

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Unknown log level: %', p_level_name;
    END IF;

    -- Suppress events below the configured application threshold.
    IF v_severity < v_minimum_severity THEN
        RETURN NULL;
    END IF;

    -- The database is a final redaction layer, not a substitute
    -- for preventing secrets from entering the logging pipeline.
    INSERT INTO log_events (
        application_id,
        level_id,
        correlation_id,
        request_id,
        trace_id,
        span_id,
        event_type,
        message,
        attributes,
        exception_type,
        exception_message
    )
    VALUES (
        v_application_id,
        v_level_id,
        p_correlation_id,
        p_request_id,
        p_trace_id,
        p_span_id,
        p_event_type,
        p_message,
        redact_log_attributes(p_attributes),
        p_exception_type,
        p_exception_message
    )
    RETURNING event_id INTO v_event_id;

    RETURN v_event_id;
END;
$$;

-- ---------------------------------------------------------
-- 9. Logging trigger
-- ---------------------------------------------------------

CREATE OR REPLACE FUNCTION validate_log_event()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN

    NEW.message := TRIM(NEW.message);
    NEW.event_type := TRIM(NEW.event_type);

    NEW.attributes := redact_log_attributes(
        NEW.attributes
    );

    IF NEW.event_timestamp > NOW() + INTERVAL '5 minutes' THEN
        RAISE EXCEPTION
            'Event timestamp is too far in the future.';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_validate_log_event
ON log_events;

CREATE TRIGGER trg_validate_log_event
BEFORE INSERT OR UPDATE ON log_events
FOR EACH ROW
EXECUTE FUNCTION validate_log_event();

-- ---------------------------------------------------------
-- 10. Monitoring views
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW log_event_details AS
SELECT
    e.event_id,
    e.event_timestamp,
    a.application_name,
    a.environment,
    a.version,
    l.level_name,
    l.severity,
    e.correlation_id,
    e.request_id,
    e.trace_id,
    e.span_id,
    e.event_type,
    e.message,
    e.attributes,
    e.exception_type,
    e.exception_message,
    e.host_name
FROM log_events e
JOIN applications a
    ON a.application_id = e.application_id
JOIN log_levels l
    ON l.level_id = e.level_id;

CREATE OR REPLACE VIEW application_log_summary AS
SELECT
    a.application_name,
    a.environment,
    l.level_name,
    COUNT(e.event_id) AS total_events,
    MIN(e.event_timestamp) AS first_event,
    MAX(e.event_timestamp) AS last_event
FROM applications a
CROSS JOIN log_levels l
LEFT JOIN log_events e
    ON e.application_id = a.application_id
    AND e.level_id = l.level_id
    AND e.event_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY
    a.application_name,
    a.environment,
    l.level_name;

-- ---------------------------------------------------------
-- 11. Correlation analysis
-- ---------------------------------------------------------

CREATE OR REPLACE VIEW correlation_event_summary AS
SELECT
    correlation_id,
    COUNT(*) AS event_count,
    COUNT(DISTINCT application_id) AS participating_services,
    MIN(event_timestamp) AS first_event,
    MAX(event_timestamp) AS last_event,
    MAX(
        CASE
            WHEN level_id >= 4 THEN 1
            ELSE 0
        END
    ) AS contains_error
FROM log_events
WHERE correlation_id IS NOT NULL
GROUP BY correlation_id;

-- ---------------------------------------------------------
-- 12. Log retention procedure
-- ---------------------------------------------------------

CREATE OR REPLACE PROCEDURE purge_expired_logs()
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted BIGINT;
BEGIN

    DELETE FROM log_events e
    USING logging_policies p
    WHERE e.application_id = p.application_id
      AND p.enabled = TRUE
      AND e.event_timestamp <
          NOW() - make_interval(days => p.retain_days);

    GET DIAGNOSTICS v_deleted = ROW_COUNT;

    RAISE NOTICE 'Deleted expired log events: %', v_deleted;
END;
$$;

COMMIT;

-- =========================================================
-- 13. SAMPLE DATA
-- =========================================================

BEGIN;

-- Correlation contexts.

INSERT INTO correlation_contexts (
    correlation_id,
    root_request_id,
    originating_application_id
)
SELECT
    '10000000-0000-4000-8000-000000000001'::UUID,
    '20000000-0000-4000-8000-000000000001'::UUID,
    application_id
FROM applications
WHERE application_name = 'order-service'
ON CONFLICT DO NOTHING;

INSERT INTO correlation_contexts (
    correlation_id,
    root_request_id,
    parent_correlation_id,
    originating_application_id
)
SELECT
    '10000000-0000-4000-8000-000000000002'::UUID,
    '20000000-0000-4000-8000-000000000001'::UUID,
    '10000000-0000-4000-8000-000000000001'::UUID,
    application_id
FROM applications
WHERE application_name = 'payment-service'
ON CONFLICT DO NOTHING;

-- Normal application events.

SELECT write_log_event(
    'order-service',
    'INFO',
    'ORDER_CREATED',
    'Order successfully created',
    '10000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000001',
    '{"order_id":"ORD-1001","amount":2500.50,"currency":"INR"}'
);

SELECT write_log_event(
    'order-service',
    'DEBUG',
    'REQUEST_RECEIVED',
    'Incoming order request',
    '10000000-0000-4000-8000-000000000001',
    '20000000-0000-4000-8000-000000000001',
    '{"method":"POST","endpoint":"/orders"}'
);

-- Cross-service event with the same root correlation.

SELECT write_log_event(
    'payment-service',
    'INFO',
    'PAYMENT_AUTHORIZED',
    'Payment authorization successful',
    '10000000-0000-4000-8000-000000000002',
    '20000000-0000-4000-8000-000000000001',
    '{"payment_id":"PAY-5001","amount":2500.50}'
);

-- Warning event.

SELECT write_log_event(
    'inventory-service',
    'WARNING',
    'LOW_STOCK',
    'Inventory reached warning threshold',
    NULL,
    NULL,
    '{"product_id":"PRD-101","available_units":3}'
);

-- Application failure.

SELECT write_log_event(
    'payment-service',
    'ERROR',
    'PAYMENT_FAILED',
    'Payment gateway rejected transaction',
    '10000000-0000-4000-8000-000000000002',
    '20000000-0000-4000-8000-000000000001',
    '{"gateway":"gateway-a","error_code":"GATEWAY_TIMEOUT"}',
    'GatewayTimeoutException',
    'Payment gateway timeout'
);

-- Critical event.

SELECT write_log_event(
    'payment-service',
    'CRITICAL',
    'SERVICE_UNAVAILABLE',
    'Payment service dependency unavailable',
    NULL,
    NULL,
    '{"dependency":"payment-gateway","retry_count":5}'
);

-- Sensitive-data test.
-- The password field is stored as [REDACTED].

SELECT write_log_event(
    'identity-service',
    'INFO',
    'AUTHENTICATION_ATTEMPT',
    'Authentication request processed',
    NULL,
    NULL,
    '{"username":"user-101","password":"private-value","result":"SUCCESS"}'
);

-- Invalid event examples are tested independently below.
-- They are intentionally handled so the complete script continues.

DO $$
BEGIN
    BEGIN
        PERFORM write_log_event(
            'order-service',
            'UNKNOWN',
            'INVALID_EVENT',
            'Invalid level test'
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Expected invalid level rejection: %', SQLERRM;
    END;

    BEGIN
        PERFORM write_log_event(
            'order-service',
            'INFO',
            'INVALID_EVENT',
            ''
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Expected empty message rejection: %', SQLERRM;
    END;

    BEGIN
        PERFORM write_log_event(
            'order-service',
            'INFO',
            'INVALID_EVENT',
            'Invalid attributes test',
            NULL,
            NULL,
            '[]'::JSONB
        );
    EXCEPTION WHEN OTHERS THEN
        RAISE NOTICE 'Expected invalid JSON object rejection: %', SQLERRM;
    END;
END;
$$;

COMMIT;

-- =========================================================
-- 14. RETRIEVAL QUERIES
-- =========================================================

-- Recent events with application and severity information.

SELECT *
FROM log_event_details
ORDER BY event_timestamp DESC
LIMIT 50;

-- Retrieve events from one correlation context.

SELECT
    correlation_id,
    request_id,
    application_name,
    level_name,
    event_type,
    message,
    event_timestamp
FROM log_event_details
WHERE correlation_id =
    '10000000-0000-4000-8000-000000000001'
   OR request_id =
    '20000000-0000-4000-8000-000000000001'
ORDER BY event_timestamp;

-- Retrieve errors and critical failures.

SELECT *
FROM log_event_details
WHERE severity >= 40
ORDER BY event_timestamp DESC;

-- =========================================================
-- 15. AGGREGATION AND REPORTING
-- =========================================================

SELECT *
FROM application_log_summary
ORDER BY application_name, level_name;

-- Application error rates over the last 24 hours.

SELECT
    application_name,
    COUNT(*) AS total_events,
    COUNT(*) FILTER (
        WHERE severity >= 40
    ) AS failed_events,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE severity >= 40
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS error_percentage
FROM log_event_details
WHERE event_timestamp >= NOW() - INTERVAL '24 hours'
GROUP BY application_name
ORDER BY error_percentage DESC;

-- Event counts by severity and environment.

SELECT
    environment,
    level_name,
    COUNT(*) AS event_count
FROM log_event_details
GROUP BY environment, level_name
ORDER BY environment, severity;

-- =========================================================
-- 16. CORRELATION AND DISTRIBUTED TRACE ANALYSIS
-- =========================================================

SELECT
    c.correlation_id,
    c.root_request_id,
    c.parent_correlation_id,
    a.application_name,
    COUNT(e.event_id) AS events_generated,
    MIN(e.event_timestamp) AS first_event,
    MAX(e.event_timestamp) AS last_event
FROM correlation_contexts c
LEFT JOIN applications a
    ON a.application_id = c.originating_application_id
LEFT JOIN log_events e
    ON e.correlation_id = c.correlation_id
GROUP BY
    c.correlation_id,
    c.root_request_id,
    c.parent_correlation_id,
    a.application_name
ORDER BY first_event;

-- Identify distributed requests containing failures.

SELECT
    correlation_id,
    event_count,
    participating_services,
    first_event,
    last_event
FROM correlation_event_summary
WHERE contains_error = 1
ORDER BY last_event DESC;

-- =========================================================
-- 17. JSON ATTRIBUTE QUERIES
-- =========================================================

SELECT
    event_id,
    message,
    attributes ->> 'order_id' AS order_id,
    attributes ->> 'amount' AS amount
FROM log_events
WHERE attributes ? 'order_id';

-- Verify that sensitive information was redacted.

SELECT
    event_id,
    attributes ->> 'password' AS stored_password
FROM log_events
WHERE attributes ? 'password';

-- =========================================================
-- 18. POLICY EVALUATION
-- =========================================================

SELECT
    a.application_name,
    l.level_name,
    l.severity,
    p.minimum_level_id,
    p.enabled,
    CASE
        WHEN p.enabled = FALSE THEN 'DISABLED'
        WHEN l.level_id >= p.minimum_level_id THEN 'ACCEPTED'
        ELSE 'SUPPRESSED'
    END AS policy_result
FROM applications a
JOIN logging_policies p
    ON p.application_id = a.application_id
CROSS JOIN log_levels l
ORDER BY a.application_name, l.severity;

-- =========================================================
-- 19. VALIDATION REPORT
-- =========================================================

SELECT
    COUNT(*) AS total_events,
    COUNT(*) FILTER (
        WHERE correlation_id IS NULL
    ) AS events_without_correlation,
    COUNT(*) FILTER (
        WHERE request_id IS NULL
    ) AS events_without_request_id,
    COUNT(*) FILTER (
        WHERE severity >= 40
    ) AS error_events,
    COUNT(DISTINCT application_id) AS participating_applications
FROM log_event_details;

-- =========================================================
-- 20. TRANSACTIONAL WORKFLOW
-- =========================================================

-- A transaction ensures that related application events
-- are committed together or rolled back together.

BEGIN;

DO $$
DECLARE
    v_correlation UUID :=
        '10000000-0000-4000-8000-000000000003';

    v_request UUID :=
        '20000000-0000-4000-8000-000000000003';
BEGIN

    INSERT INTO correlation_contexts (
        correlation_id,
        root_request_id,
        originating_application_id
    )
    SELECT
        v_correlation,
        v_request,
        application_id
    FROM applications
    WHERE application_name = 'order-service';

    PERFORM write_log_event(
        'order-service',
        'INFO',
        'TRANSACTION_STARTED',
        'Order workflow transaction started',
        v_correlation,
        v_request
    );

    PERFORM write_log_event(
        'order-service',
        'INFO',
        'TRANSACTION_COMPLETED',
        'Order workflow transaction completed',
        v_correlation,
        v_request
    );

END;
$$;

COMMIT;

-- =========================================================
-- 21. OPERATIONAL NOTES
-- =========================================================

-- For high-volume production logging:
--
-- 1. Partition log_events by event_timestamp.
-- 2. Use time-based partition maintenance.
-- 3. Move long-term logs to an external archive.
-- 4. Avoid indexing every JSONB attribute.
-- 5. Apply appropriate database permissions.
-- 6. Restrict direct access to sensitive event attributes.
-- 7. Use asynchronous ingestion for high-throughput systems.
-- 8. Keep application-side and database-side redaction.
-- 9. Do not treat missing correlation IDs as valid trace links.
-- 10. Coordinate retention with audit and legal requirements.
--
-- The database records structured events. It does not replace
-- a distributed tracing backend or a dedicated log platform.
