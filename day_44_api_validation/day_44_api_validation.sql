-- API Validation and Error Responses
-- PostgreSQL 14+
--
-- This script models an API device-registration workflow. It enforces
-- structural and domain constraints in the database while leaving HTTP
-- status mapping and JSON parsing at the application boundary.
--
-- Execute with:
--   psql -v ON_ERROR_STOP=1 -f api_validation.sql
--
-- PostgreSQL cannot validate raw HTTP JSON syntax, headers, authentication
-- tokens, or HTTP response status codes. Those belong to the API layer.

BEGIN;

DROP SCHEMA IF EXISTS api_validation_demo CASCADE;
CREATE SCHEMA api_validation_demo;
SET search_path TO api_validation_demo, public;

CREATE TYPE request_state AS ENUM (
    'received',
    'validated',
    'rejected',
    'completed'
);

CREATE TYPE api_error_category AS ENUM (
    'malformed_request',
    'validation',
    'authentication',
    'authorization',
    'conflict',
    'not_found',
    'internal'
);

CREATE TABLE api_clients (
    client_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_key TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    can_register_devices BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT api_clients_key_not_blank
        CHECK (length(btrim(client_key)) BETWEEN 3 AND 100),

    CONSTRAINT api_clients_name_not_blank
        CHECK (length(btrim(display_name)) BETWEEN 2 AND 120)
);

CREATE TABLE api_requests (
    request_id UUID PRIMARY KEY,
    client_id BIGINT REFERENCES api_clients(client_id),
    method TEXT NOT NULL,
    route TEXT NOT NULL,
    content_type TEXT,
    payload_bytes INTEGER NOT NULL,
    state request_state NOT NULL DEFAULT 'received',
    received_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT api_requests_method_allowed
        CHECK (method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')),

    CONSTRAINT api_requests_route_not_blank
        CHECK (length(btrim(route)) BETWEEN 1 AND 500),

    CONSTRAINT api_requests_payload_size_valid
        CHECK (payload_bytes BETWEEN 0 AND 1048576),

    CONSTRAINT api_requests_completion_consistent
        CHECK (
            (state IN ('received', 'validated') AND completed_at IS NULL)
            OR
            (state IN ('rejected', 'completed') AND completed_at IS NOT NULL)
        )
);

CREATE INDEX api_requests_received_idx
    ON api_requests (received_at DESC);

CREATE INDEX api_requests_state_received_idx
    ON api_requests (state, received_at DESC);

CREATE TABLE api_field_errors (
    field_error_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES api_requests(request_id)
        ON DELETE CASCADE,
    field_path TEXT NOT NULL,
    error_code TEXT NOT NULL,
    public_message TEXT NOT NULL,
    internal_detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT api_field_errors_path_not_blank
        CHECK (length(btrim(field_path)) BETWEEN 1 AND 300),

    CONSTRAINT api_field_errors_code_not_blank
        CHECK (length(btrim(error_code)) BETWEEN 1 AND 100),

    CONSTRAINT api_field_errors_message_not_blank
        CHECK (length(btrim(public_message)) BETWEEN 1 AND 500)
);

CREATE INDEX api_field_errors_request_idx
    ON api_field_errors (request_id, field_error_id);

CREATE TABLE devices (
    device_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    device_name TEXT NOT NULL,
    normalized_name TEXT GENERATED ALWAYS AS (
        lower(btrim(device_name))
    ) STORED,
    owner_email TEXT NOT NULL,
    firmware_major INTEGER NOT NULL,
    registered_by BIGINT NOT NULL REFERENCES api_clients(client_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT devices_name_length
        CHECK (length(btrim(device_name)) BETWEEN 3 AND 64),

    CONSTRAINT devices_email_length
        CHECK (length(owner_email) BETWEEN 3 AND 254),

    CONSTRAINT devices_email_basic_shape
        CHECK (owner_email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'),

    CONSTRAINT devices_firmware_range
        CHECK (firmware_major BETWEEN 1 AND 99),

    CONSTRAINT devices_normalized_name_unique
        UNIQUE (normalized_name)
);

CREATE INDEX devices_owner_email_idx
    ON devices (lower(owner_email));

-- The HTTP application records every accepted or rejected request using a
-- request ID. This function validates registration permission and data
-- constraints inside a transaction, preventing duplicate registrations.
CREATE OR REPLACE FUNCTION register_device(
    p_request_id UUID,
    p_client_key TEXT,
    p_device_name TEXT,
    p_owner_email TEXT,
    p_firmware_major INTEGER
)
RETURNS TABLE (
    result_device_id BIGINT,
    result_http_status INTEGER,
    result_code TEXT,
    result_message TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_client api_clients%ROWTYPE;
    v_request api_requests%ROWTYPE;
    v_device_id BIGINT;
    v_normalized_name TEXT;
BEGIN
    SELECT *
    INTO v_client
    FROM api_clients
    WHERE client_key = p_client_key
      AND active = TRUE
    FOR SHARE;

    IF NOT FOUND THEN
        INSERT INTO api_requests (
            request_id, method, route, content_type, payload_bytes,
            state, completed_at
        )
        VALUES (
            p_request_id, 'POST', '/devices', 'application/json',
            0, 'rejected', now()
        )
        ON CONFLICT (request_id) DO NOTHING;

        RETURN QUERY SELECT
            NULL::BIGINT,
            401,
            'authentication_required',
            'An active API client is required.';
        RETURN;
    END IF;

    IF NOT v_client.can_register_devices THEN
        INSERT INTO api_requests (
            request_id, client_id, method, route, content_type,
            payload_bytes, state, completed_at
        )
        VALUES (
            p_request_id, v_client.client_id, 'POST', '/devices',
            'application/json', 0, 'rejected', now()
        )
        ON CONFLICT (request_id) DO NOTHING;

        RETURN QUERY SELECT
            NULL::BIGINT,
            403,
            'registration_forbidden',
            'The client cannot register devices.';
        RETURN;
    END IF;

    INSERT INTO api_requests (
        request_id, client_id, method, route, content_type,
        payload_bytes, state
    )
    VALUES (
        p_request_id, v_client.client_id, 'POST', '/devices',
        'application/json', 0, 'validated'
    )
    ON CONFLICT (request_id) DO NOTHING;

    SELECT *
    INTO v_request
    FROM api_requests
    WHERE request_id = p_request_id
    FOR UPDATE;

    IF NOT FOUND OR v_request.state <> 'validated' THEN
        RETURN QUERY SELECT
            NULL::BIGINT,
            409,
            'request_state_conflict',
            'The request ID is already in use or is not in a valid state.';
        RETURN;
    END IF;

    IF p_device_name IS NULL
       OR length(btrim(p_device_name)) NOT BETWEEN 3 AND 64 THEN
        INSERT INTO api_field_errors (
            request_id, field_path, error_code, public_message
        )
        VALUES (
            p_request_id,
            'device_name',
            'invalid_length',
            'Device name must contain 3 to 64 characters.'
        );

        UPDATE api_requests
        SET state = 'rejected', completed_at = now()
        WHERE request_id = p_request_id;

        RETURN QUERY SELECT
            NULL::BIGINT,
            422,
            'validation_failed',
            'The device name is invalid.';
        RETURN;
    END IF;

    IF p_owner_email IS NULL
       OR length(p_owner_email) NOT BETWEEN 3 AND 254
       OR p_owner_email !~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$' THEN
        INSERT INTO api_field_errors (
            request_id, field_path, error_code, public_message
        )
        VALUES (
            p_request_id,
            'owner_email',
            'invalid_email',
            'Provide a valid owner email address.'
        );

        UPDATE api_requests
        SET state = 'rejected', completed_at = now()
        WHERE request_id = p_request_id;

        RETURN QUERY SELECT
            NULL::BIGINT,
            422,
            'validation_failed',
            'The owner email address is invalid.';
        RETURN;
    END IF;

    IF p_firmware_major IS NULL
       OR p_firmware_major NOT BETWEEN 1 AND 99 THEN
        INSERT INTO api_field_errors (
            request_id, field_path, error_code, public_message
        )
        VALUES (
            p_request_id,
            'firmware_major',
            'out_of_range',
            'Firmware major version must be between 1 and 99.'
        );

        UPDATE api_requests
        SET state = 'rejected', completed_at = now()
        WHERE request_id = p_request_id;

        RETURN QUERY SELECT
            NULL::BIGINT,
            422,
            'validation_failed',
            'The firmware version is outside the supported range.';
        RETURN;
    END IF;

    v_normalized_name := lower(btrim(p_device_name));

    -- The unique constraint is the final authority under concurrent inserts.
    -- The pre-check provides a useful conflict response for ordinary requests.
    IF EXISTS (
        SELECT 1
        FROM devices
        WHERE normalized_name = v_normalized_name
    ) THEN
        UPDATE api_requests
        SET state = 'rejected', completed_at = now()
        WHERE request_id = p_request_id;

        RETURN QUERY SELECT
            NULL::BIGINT,
            409,
            'device_name_conflict',
            'A device with this name already exists.';
        RETURN;
    END IF;

    INSERT INTO devices (
        device_name, owner_email, firmware_major, registered_by
    )
    VALUES (
        btrim(p_device_name),
        btrim(p_owner_email),
        p_firmware_major,
        v_client.client_id
    )
    ON CONFLICT (normalized_name) DO NOTHING
    RETURNING device_id INTO v_device_id;

    IF v_device_id IS NULL THEN
        UPDATE api_requests
        SET state = 'rejected', completed_at = now()
        WHERE request_id = p_request_id;

        RETURN QUERY SELECT
            NULL::BIGINT,
            409,
            'device_name_conflict',
            'A device with this name already exists.';
        RETURN;
    END IF;

    UPDATE api_requests
    SET state = 'completed', completed_at = now()
    WHERE request_id = p_request_id;

    RETURN QUERY SELECT
        v_device_id,
        201,
        'created',
        'Device registered successfully.';
END;
$$;

INSERT INTO api_clients (
    client_key, display_name, active, can_register_devices
)
VALUES
    ('operations-service', 'Operations Service', TRUE, TRUE),
    ('audit-service', 'Audit Service', TRUE, FALSE),
    ('disabled-service', 'Disabled Integration', FALSE, TRUE);

-- Successful registration.
SELECT *
FROM register_device(
    '11111111-1111-4111-8111-111111111111',
    'operations-service',
    'Pump Sensor A',
    'operations@example.com',
    4
);

-- The duplicate demonstrates application-level conflict handling and
-- database-level uniqueness protection.
SELECT *
FROM register_device(
    '22222222-2222-4222-8222-222222222222',
    'operations-service',
    'PUMP SENSOR A',
    'another@example.com',
    5
);

-- A read-only client cannot use a valid payload to gain registration rights.
SELECT *
FROM register_device(
    '33333333-3333-4333-8333-333333333333',
    'audit-service',
    'Pump Sensor B',
    'audit@example.com',
    2
);

-- Invalid domain data produces a field-level error and a rejected request.
SELECT *
FROM register_device(
    '44444444-4444-4444-8444-444444444444',
    'operations-service',
    'X',
    'invalid-email',
    150
);

-- A disabled integration is treated as unauthenticated.
SELECT *
FROM register_device(
    '55555555-5555-4555-8555-555555555555',
    'disabled-service',
    'Pump Sensor C',
    'disabled@example.com',
    2
);

-- Operational reporting: HTTP-layer outcomes are retained by request ID.
SELECT
    request_id,
    method,
    route,
    state,
    received_at,
    completed_at
FROM api_requests
ORDER BY received_at, request_id;

-- Field errors can be grouped to identify recurring client defects.
SELECT
    error_code,
    field_path,
    count(*) AS occurrences
FROM api_field_errors
GROUP BY error_code, field_path
ORDER BY occurrences DESC, field_path;

-- Requests with validation errors and their public-facing details.
SELECT
    r.request_id,
    r.state,
    e.field_path,
    e.error_code,
    e.public_message
FROM api_requests AS r
JOIN api_field_errors AS e USING (request_id)
ORDER BY r.received_at, e.field_error_id;

-- Verify that duplicate normalized device names cannot be persisted.
SELECT
    device_id,
    device_name,
    normalized_name,
    owner_email,
    firmware_major
FROM devices
ORDER BY device_id;

COMMIT;
