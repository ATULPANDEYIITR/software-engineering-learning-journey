-- Dependency Injection demonstration database model
-- PostgreSQL 15+ compatible.
--
-- The database represents the configuration and execution side of DI:
-- services depend on contracts, contracts map to implementations, and
-- environments determine which implementation is composed at runtime.
--
-- Database constraints protect configuration integrity while application
-- code performs the actual object construction.

DROP SCHEMA IF EXISTS dependency_injection_demo CASCADE;
CREATE SCHEMA dependency_injection_demo;

SET search_path TO dependency_injection_demo;

-- ---------------------------------------------------------------------------
-- Service contracts
-- ---------------------------------------------------------------------------

CREATE TABLE service_contract (
    contract_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contract_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL
);

CREATE TABLE service_implementation (
    implementation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    contract_id BIGINT NOT NULL
        REFERENCES service_contract(contract_id)
        ON DELETE RESTRICT,
    implementation_name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    endpoint TEXT,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (contract_id, implementation_name),
    CHECK (length(trim(implementation_name)) > 0),
    CHECK (
        provider_type IN (
            'in_memory',
            'external_api',
            'console',
            'mock',
            'database'
        )
    )
);

-- ---------------------------------------------------------------------------
-- Environments and dependency registrations
-- ---------------------------------------------------------------------------

CREATE TABLE application_environment (
    environment_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    environment_name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    CHECK (
        environment_name IN (
            'development',
            'test',
            'staging',
            'production'
        )
    )
);

CREATE TABLE dependency_registration (
    registration_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    environment_id BIGINT NOT NULL
        REFERENCES application_environment(environment_id)
        ON DELETE CASCADE,
    contract_id BIGINT NOT NULL
        REFERENCES service_contract(contract_id)
        ON DELETE RESTRICT,
    implementation_id BIGINT NOT NULL
        REFERENCES service_implementation(implementation_id)
        ON DELETE RESTRICT,
    lifetime TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CHECK (lifetime IN ('singleton', 'transient', 'scoped')),
    UNIQUE (environment_id, contract_id)
);

CREATE INDEX idx_dependency_registration_environment
    ON dependency_registration(environment_id);

CREATE INDEX idx_dependency_registration_contract
    ON dependency_registration(contract_id);

-- ---------------------------------------------------------------------------
-- Domain data used by the injected application services
-- ---------------------------------------------------------------------------

CREATE TABLE customer_order (
    order_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_order_id TEXT NOT NULL UNIQUE,
    customer_email TEXT NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CHECK (amount > 0),
    CHECK (customer_email LIKE '%@%'),
    CHECK (
        status IN (
            'created',
            'paid',
            'payment_failed',
            'notification_failed'
        )
    )
);

CREATE INDEX idx_customer_order_status
    ON customer_order(status);

CREATE TABLE payment_attempt (
    payment_attempt_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES customer_order(order_id)
        ON DELETE CASCADE,
    provider_implementation_id BIGINT
        REFERENCES service_implementation(implementation_id)
        ON DELETE RESTRICT,
    success BOOLEAN NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    failure_reason TEXT
);

CREATE INDEX idx_payment_attempt_order
    ON payment_attempt(order_id);

CREATE TABLE notification_delivery (
    notification_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES customer_order(order_id)
        ON DELETE CASCADE,
    notifier_implementation_id BIGINT
        REFERENCES service_implementation(implementation_id)
        ON DELETE RESTRICT,
    destination TEXT NOT NULL,
    delivered BOOLEAN NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    failure_reason TEXT
);

CREATE INDEX idx_notification_order
    ON notification_delivery(order_id);

-- ---------------------------------------------------------------------------
-- Seed contracts
-- ---------------------------------------------------------------------------

INSERT INTO service_contract (contract_name, description)
VALUES
    (
        'OrderRepository',
        'Stores and retrieves orders required by the application service.'
    ),
    (
        'PaymentGateway',
        'Charges an order through an external or simulated payment provider.'
    ),
    (
        'NotificationService',
        'Delivers payment receipts to customers.'
    );

INSERT INTO application_environment (environment_name, description)
VALUES
    ('development', 'Local developer execution.'),
    ('test', 'Automated tests using deterministic doubles.'),
    ('staging', 'Pre-production integration environment.'),
    ('production', 'Production infrastructure.');

-- ---------------------------------------------------------------------------
-- Seed implementations
-- ---------------------------------------------------------------------------

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'MemoryOrderRepository', 'in_memory', NULL
FROM service_contract
WHERE contract_name = 'OrderRepository';

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'ProductionOrderRepository', 'database',
       'postgresql://orders.internal'
FROM service_contract
WHERE contract_name = 'OrderRepository';

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'FakePaymentGateway', 'mock', NULL
FROM service_contract
WHERE contract_name = 'PaymentGateway';

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'ProductionPaymentGateway', 'external_api',
       'https://payments.internal'
FROM service_contract
WHERE contract_name = 'PaymentGateway';

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'FakeNotificationService', 'mock', NULL
FROM service_contract
WHERE contract_name = 'NotificationService';

INSERT INTO service_implementation (
    contract_id,
    implementation_name,
    provider_type,
    endpoint
)
SELECT contract_id, 'ProductionEmailNotification', 'external_api',
       'https://notifications.internal/email'
FROM service_contract
WHERE contract_name = 'NotificationService';

-- ---------------------------------------------------------------------------
-- Environment-specific dependency composition
-- ---------------------------------------------------------------------------

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'singleton'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'OrderRepository'
JOIN service_implementation i
    ON i.implementation_name = 'MemoryOrderRepository'
WHERE e.environment_name IN ('development', 'test');

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'singleton'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'OrderRepository'
JOIN service_implementation i
    ON i.implementation_name = 'ProductionOrderRepository'
WHERE e.environment_name IN ('staging', 'production');

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'transient'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'PaymentGateway'
JOIN service_implementation i
    ON i.implementation_name = 'FakePaymentGateway'
WHERE e.environment_name = 'test';

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'transient'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'PaymentGateway'
JOIN service_implementation i
    ON i.implementation_name = 'ProductionPaymentGateway'
WHERE e.environment_name IN ('development', 'staging', 'production');

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.contract_id,
    'singleton'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'NotificationService'
JOIN service_implementation i
    ON i.implementation_name = 'FakeNotificationService'
WHERE e.environment_name = 'test';

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'singleton'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'NotificationService'
JOIN service_implementation i
    ON i.implementation_name = 'ProductionEmailNotification'
WHERE e.environment_name IN ('development', 'staging', 'production');

-- Correct the intentionally different query above by validating all
-- registrations through the relational model.
DELETE FROM dependency_registration
WHERE implementation_id IS NULL;

-- ---------------------------------------------------------------------------
-- View: resolved dependency graph
-- ---------------------------------------------------------------------------

CREATE VIEW resolved_dependencies AS
SELECT
    e.environment_name,
    c.contract_name,
    i.implementation_name,
    i.provider_type,
    i.endpoint,
    r.lifetime,
    r.enabled
FROM dependency_registration r
JOIN application_environment e
    ON e.environment_id = r.environment_id
JOIN service_contract c
    ON c.contract_id = r.contract_id
JOIN service_implementation i
    ON i.implementation_id = r.implementation_id;

-- ---------------------------------------------------------------------------
-- Queries used by an application composition process
-- ---------------------------------------------------------------------------

SELECT
    environment_name,
    contract_name,
    implementation_name,
    lifetime,
    provider_type
FROM resolved_dependencies
WHERE environment_name = 'production'
  AND enabled = TRUE
ORDER BY contract_name;

SELECT
    e.environment_name,
    c.contract_name
FROM application_environment e
CROSS JOIN service_contract c
LEFT JOIN dependency_registration r
    ON r.environment_id = e.environment_id
   AND r.contract_id = c.contract_id
WHERE r.registration_id IS NULL
ORDER BY e.environment_name, c.contract_name;

-- A registered implementation must belong to the same contract as the
-- registration. PostgreSQL cannot enforce this cross-table relationship with
-- an ordinary CHECK constraint, so this query exposes configuration drift.
SELECT
    r.registration_id,
    c.contract_name AS requested_contract,
    i.contract_id AS implementation_contract_id
FROM dependency_registration r
JOIN service_contract c
    ON c.contract_id = r.contract_id
JOIN service_implementation i
    ON i.implementation_id = r.implementation_id
WHERE i.contract_id <> r.contract_id;

-- ---------------------------------------------------------------------------
-- Example order workflow
-- ---------------------------------------------------------------------------

INSERT INTO customer_order (
    external_order_id,
    customer_email,
    amount,
    status
)
VALUES
    ('SQL-ORD-001', 'buyer@example.com', 250.00, 'paid'),
    ('SQL-ORD-002', 'failed@example.com', 300.00, 'payment_failed');

INSERT INTO payment_attempt (
    order_id,
    provider_implementation_id,
    success,
    failure_reason
)
SELECT
    o.order_id,
    i.implementation_id,
    TRUE,
    NULL
FROM customer_order o
JOIN service_implementation i
    ON i.implementation_name = 'ProductionPaymentGateway'
WHERE o.external_order_id = 'SQL-ORD-001';

INSERT INTO payment_attempt (
    order_id,
    provider_implementation_id,
    success,
    failure_reason
)
SELECT
    o.order_id,
    i.implementation_id,
    FALSE,
    'Provider unavailable'
FROM customer_order o
JOIN service_implementation i
    ON i.implementation_name = 'ProductionPaymentGateway'
WHERE o.external_order_id = 'SQL-ORD-002';

INSERT INTO notification_delivery (
    order_id,
    notifier_implementation_id,
    destination,
    delivered
)
SELECT
    o.order_id,
    i.implementation_id,
    o.customer_email,
    TRUE
FROM customer_order o
JOIN service_implementation i
    ON i.implementation_name = 'ProductionEmailNotification'
WHERE o.external_order_id = 'SQL-ORD-001';

-- ---------------------------------------------------------------------------
-- Transactional configuration change
-- ---------------------------------------------------------------------------

BEGIN;

UPDATE dependency_registration r
SET lifetime = 'scoped'
FROM application_environment e
JOIN service_contract c
    ON c.contract_id = r.contract_id
WHERE r.environment_id = e.environment_id
  AND c.contract_name = 'OrderRepository'
  AND e.environment_name = 'staging';

-- Inspect the changed composition before committing.
SELECT *
FROM resolved_dependencies
WHERE environment_name = 'staging'
ORDER BY contract_name;

COMMIT;

-- ---------------------------------------------------------------------------
-- Failure conditions
-- ---------------------------------------------------------------------------

-- This statement demonstrates database-level protection against invalid
-- amounts. It is intentionally rolled back so the script remains successful.
BEGIN;

INSERT INTO customer_order (
    external_order_id,
    customer_email,
    amount,
    status
)
VALUES ('SQL-INVALID-001', 'invalid@example.com', -5.00, 'created');

ROLLBACK;

-- The unique environment/contract constraint prevents two competing
-- implementations from being simultaneously registered for one contract.
BEGIN;

INSERT INTO dependency_registration (
    environment_id,
    contract_id,
    implementation_id,
    lifetime
)
SELECT
    e.environment_id,
    c.contract_id,
    i.implementation_id,
    'singleton'
FROM application_environment e
JOIN service_contract c
    ON c.contract_name = 'PaymentGateway'
JOIN service_implementation i
    ON i.implementation_name = 'FakePaymentGateway'
WHERE e.environment_name = 'test';

ROLLBACK;

-- ---------------------------------------------------------------------------
-- Operational dependency report
-- ---------------------------------------------------------------------------

SELECT
    e.environment_name,
    COUNT(*) AS registered_contracts,
    COUNT(*) FILTER (WHERE r.enabled) AS enabled_contracts,
    COUNT(*) FILTER (WHERE r.lifetime = 'singleton') AS singleton_count,
    COUNT(*) FILTER (WHERE r.lifetime = 'transient') AS transient_count,
    COUNT(*) FILTER (WHERE r.lifetime = 'scoped') AS scoped_count
FROM application_environment e
LEFT JOIN dependency_registration r
    ON r.environment_id = e.environment_id
GROUP BY e.environment_id, e.environment_name
ORDER BY e.environment_name;

SELECT
    o.external_order_id,
    o.status,
    o.amount,
    p.success AS payment_success,
    n.delivered AS notification_delivered
FROM customer_order o
LEFT JOIN payment_attempt p
    ON p.order_id = o.order_id
LEFT JOIN notification_delivery n
    ON n.order_id = o.order_id
ORDER BY o.order_id;
