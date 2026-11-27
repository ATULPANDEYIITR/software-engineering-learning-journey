-- ============================================================
-- DISTRIBUTED TRANSACTIONS
-- PostgreSQL 15+
--
-- Models:
--   1. Two-Phase Commit
--   2. Saga orchestration
--   3. Local participant transactions
--   4. Compensation operations
--   5. Durable coordinator decisions
--   6. Participant voting and acknowledgements
--   7. Transaction recovery and auditing
--
-- IMPORTANT:
-- This database models application-level distributed
-- transaction coordination.
--
-- It does not implement PostgreSQL's native PREPARE TRANSACTION
-- / COMMIT PREPARED protocol across independent databases.
-- ============================================================

DROP SCHEMA IF EXISTS distributed_tx CASCADE;

CREATE SCHEMA distributed_tx;

SET search_path TO distributed_tx, public;

-- ============================================================
-- 1. DOMAIN TYPES
-- ============================================================

CREATE TYPE transaction_mode AS ENUM (
    'TWO_PHASE_COMMIT',
    'SAGA'
);

CREATE TYPE transaction_state AS ENUM (
    'CREATED',
    'PREPARING',
    'PREPARED',
    'COMMIT_DECIDED',
    'COMMITTING',
    'COMMITTED',
    'ABORT_DECIDED',
    'ABORTING',
    'ABORTED',
    'COMPENSATING',
    'COMPENSATED',
    'IN_DOUBT',
    'FAILED'
);

CREATE TYPE participant_state AS ENUM (
    'ACTIVE',
    'PREPARED',
    'COMMITTED',
    'ABORTED',
    'FAILED'
);

CREATE TYPE vote_type AS ENUM (
    'YES',
    'NO',
    'NOT_RECEIVED'
);

CREATE TYPE event_type AS ENUM (
    'CREATED',
    'PREPARE_REQUEST',
    'VOTE_YES',
    'VOTE_NO',
    'COMMIT_DECISION',
    'ABORT_DECISION',
    'COMMIT_ACK',
    'LOCAL_COMMIT',
    'COMPENSATION_REQUEST',
    'COMPENSATION_SUCCESS',
    'COMPENSATION_FAILURE',
    'RECOVERY',
    'FAILURE'
);

CREATE TYPE saga_step_state AS ENUM (
    'PENDING',
    'EXECUTING',
    'COMPLETED',
    'FAILED',
    'COMPENSATING',
    'COMPENSATED',
    'COMPENSATION_FAILED'
);

-- ============================================================
-- 2. PARTICIPANTS AND SERVICES
-- ============================================================

CREATE TABLE services (
    service_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    service_name VARCHAR(100) NOT NULL UNIQUE,
    endpoint VARCHAR(255),
    is_available BOOLEAN NOT NULL DEFAULT TRUE,
    supports_prepare BOOLEAN NOT NULL DEFAULT TRUE,
    supports_compensation BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT service_name_not_blank
        CHECK (LENGTH(TRIM(service_name)) > 0)
);

INSERT INTO services (
    service_name,
    endpoint,
    supports_prepare,
    supports_compensation
)
VALUES
    (
        'InventoryService',
        'inventory.internal',
        TRUE,
        TRUE
    ),
    (
        'PaymentService',
        'payment.internal',
        TRUE,
        TRUE
    ),
    (
        'OrderService',
        'orders.internal',
        TRUE,
        TRUE
    ),
    (
        'ShippingService',
        'shipping.internal',
        FALSE,
        TRUE
    ),
    (
        'LedgerService',
        'ledger.internal',
        TRUE,
        TRUE
    );

-- ============================================================
-- 3. TRANSACTION COORDINATOR
-- ============================================================

CREATE TABLE distributed_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    transaction_reference VARCHAR(100) NOT NULL UNIQUE,

    mode transaction_mode NOT NULL,

    state transaction_state NOT NULL DEFAULT 'CREATED',

    idempotency_key VARCHAR(150) NOT NULL UNIQUE,

    business_reference VARCHAR(150) NOT NULL,

    payload JSONB NOT NULL DEFAULT '{}'::JSONB,

    coordinator_id VARCHAR(100) NOT NULL,

    decision_recorded_at TIMESTAMPTZ,

    deadline_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT transaction_reference_not_blank
        CHECK (LENGTH(TRIM(transaction_reference)) > 0),

    CONSTRAINT business_reference_not_blank
        CHECK (LENGTH(TRIM(business_reference)) > 0),

    CONSTRAINT decision_timestamp_rule
        CHECK (
            state NOT IN (
                'COMMIT_DECIDED',
                'COMMITTING',
                'COMMITTED',
                'ABORT_DECIDED',
                'ABORTING',
                'ABORTED'
            )
            OR decision_recorded_at IS NOT NULL
        )
);

CREATE INDEX idx_transactions_state
    ON distributed_transactions(state);

CREATE INDEX idx_transactions_mode_state
    ON distributed_transactions(mode, state);

CREATE INDEX idx_transactions_created
    ON distributed_transactions(created_at DESC);

CREATE INDEX idx_transactions_business_reference
    ON distributed_transactions(business_reference);

CREATE INDEX idx_transactions_payload
    ON distributed_transactions USING GIN(payload);

-- ============================================================
-- 4. TRANSACTION PARTICIPANTS
-- ============================================================

CREATE TABLE transaction_participants (
    participant_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID NOT NULL
        REFERENCES distributed_transactions(transaction_id)
        ON DELETE RESTRICT,

    service_id BIGINT NOT NULL
        REFERENCES services(service_id)
        ON DELETE RESTRICT,

    execution_order INTEGER NOT NULL,

    state participant_state NOT NULL DEFAULT 'ACTIVE',

    vote vote_type NOT NULL DEFAULT 'NOT_RECEIVED',

    vote_recorded_at TIMESTAMPTZ,

    commit_acknowledged_at TIMESTAMPTZ,

    last_error TEXT,

    idempotency_key VARCHAR(200) NOT NULL UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT participant_order_positive
        CHECK (execution_order > 0),

    CONSTRAINT unique_transaction_service
        UNIQUE(transaction_id, service_id),

    CONSTRAINT unique_transaction_order
        UNIQUE(transaction_id, execution_order),

    CONSTRAINT vote_timestamp_rule
        CHECK (
            vote = 'NOT_RECEIVED'
            OR vote_recorded_at IS NOT NULL
        )
);

CREATE INDEX idx_participants_transaction_state
    ON transaction_participants(transaction_id, state);

CREATE INDEX idx_participants_service
    ON transaction_participants(service_id);

-- ============================================================
-- 5. SAGA STEPS
-- ============================================================

CREATE TABLE saga_steps (
    saga_step_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    participant_id BIGINT NOT NULL
        REFERENCES transaction_participants(participant_id)
        ON DELETE RESTRICT,

    step_name VARCHAR(120) NOT NULL,

    execution_order INTEGER NOT NULL,

    state saga_step_state NOT NULL DEFAULT 'PENDING',

    command_payload JSONB NOT NULL DEFAULT '{}'::JSONB,

    compensation_payload JSONB NOT NULL DEFAULT '{}'::JSONB,

    executed_at TIMESTAMPTZ,

    compensated_at TIMESTAMPTZ,

    retry_count INTEGER NOT NULL DEFAULT 0,

    last_error TEXT,

    CONSTRAINT saga_step_name_not_blank
        CHECK (LENGTH(TRIM(step_name)) > 0),

    CONSTRAINT saga_step_order_positive
        CHECK (execution_order > 0),

    CONSTRAINT saga_retry_nonnegative
        CHECK (retry_count >= 0),

    CONSTRAINT unique_participant_step_order
        UNIQUE(participant_id, execution_order)
);

CREATE INDEX idx_saga_steps_execution
    ON saga_steps(state, execution_order);

-- ============================================================
-- 6. REVIEWABLE TRANSACTION DECISIONS
-- ============================================================

CREATE TABLE transaction_decisions (
    decision_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID NOT NULL
        REFERENCES distributed_transactions(transaction_id)
        ON DELETE RESTRICT,

    decision transaction_state NOT NULL,

    decision_reason TEXT NOT NULL,

    decided_by VARCHAR(100) NOT NULL,

    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_decision
        CHECK (
            decision IN (
                'COMMIT_DECIDED',
                'ABORT_DECIDED'
            )
        )
);

CREATE INDEX idx_decisions_transaction
    ON transaction_decisions(transaction_id, recorded_at DESC);

-- ============================================================
-- 7. TRANSACTION AUDIT
-- ============================================================

CREATE TABLE transaction_events (
    event_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    transaction_id UUID NOT NULL
        REFERENCES distributed_transactions(transaction_id)
        ON DELETE RESTRICT,

    participant_id BIGINT
        REFERENCES transaction_participants(participant_id)
        ON DELETE RESTRICT,

    event event_type NOT NULL,

    description TEXT NOT NULL,

    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,

    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_transaction_time
    ON transaction_events(transaction_id, occurred_at);

CREATE INDEX idx_events_type
    ON transaction_events(event, occurred_at DESC);

-- ============================================================
-- 8. TRANSACTION STATE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_transaction_state()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.state IN (
        'COMMITTED',
        'ABORTED',
        'COMPENSATED'
    ) AND NEW.state <> OLD.state THEN
        RAISE EXCEPTION
            'Terminal transaction state cannot be changed: %',
            OLD.state;
    END IF;

    IF OLD.mode = 'TWO_PHASE_COMMIT'
       AND NEW.state IN (
           'COMPENSATING',
           'COMPENSATED'
       ) THEN
        RAISE EXCEPTION
            '2PC transactions cannot use saga compensation states';
    END IF;

    IF OLD.mode = 'SAGA'
       AND NEW.state IN (
           'PREPARED',
           'COMMIT_DECIDED',
           'ABORT_DECIDED'
       ) THEN
        RAISE EXCEPTION
            'Saga transactions cannot use 2PC decision states';
    END IF;

    NEW.updated_at = NOW();

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_transaction_state
BEFORE UPDATE ON distributed_transactions
FOR EACH ROW
EXECUTE FUNCTION validate_transaction_state();

-- ============================================================
-- 9. PARTICIPANT STATE VALIDATION
-- ============================================================

CREATE OR REPLACE FUNCTION validate_participant_state()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.state IN ('COMMITTED', 'ABORTED')
       AND NEW.state <> OLD.state THEN
        RAISE EXCEPTION
            'Terminal participant state cannot change';
    END IF;

    IF NEW.vote = 'YES'
       AND NEW.state NOT IN ('PREPARED', 'COMMITTED') THEN
        RAISE EXCEPTION
            'YES vote requires PREPARED or COMMITTED state';
    END IF;

    IF NEW.vote = 'NO'
       AND NEW.state NOT IN ('ACTIVE', 'ABORTED', 'FAILED') THEN
        RAISE EXCEPTION
            'NO vote conflicts with participant state';
    END IF;

    NEW.updated_at = NOW();

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_validate_participant_state
BEFORE UPDATE ON transaction_participants
FOR EACH ROW
EXECUTE FUNCTION validate_participant_state();

-- ============================================================
-- 10. AUDIT EVENT FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION record_transaction_event(
    p_transaction_id UUID,
    p_event event_type,
    p_description TEXT,
    p_participant_id BIGINT DEFAULT NULL,
    p_metadata JSONB DEFAULT '{}'::JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_event_id BIGINT;
BEGIN
    INSERT INTO transaction_events (
        transaction_id,
        participant_id,
        event,
        description,
        metadata
    )
    VALUES (
        p_transaction_id,
        p_participant_id,
        p_event,
        p_description,
        COALESCE(p_metadata, '{}'::JSONB)
    )
    RETURNING event_id INTO v_event_id;

    RETURN v_event_id;
END;
$$;

-- ============================================================
-- 11. CREATE A DISTRIBUTED TRANSACTION
-- ============================================================

CREATE OR REPLACE FUNCTION create_transaction(
    p_reference VARCHAR(100),
    p_mode transaction_mode,
    p_business_reference VARCHAR(150),
    p_idempotency_key VARCHAR(150),
    p_coordinator VARCHAR(100),
    p_payload JSONB DEFAULT '{}'::JSONB
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id UUID;
BEGIN
    IF NULLIF(TRIM(p_reference), '') IS NULL
       OR NULLIF(TRIM(p_business_reference), '') IS NULL
       OR NULLIF(TRIM(p_idempotency_key), '') IS NULL
       OR NULLIF(TRIM(p_coordinator), '') IS NULL THEN
        RAISE EXCEPTION 'Required transaction fields are missing';
    END IF;

    INSERT INTO distributed_transactions (
        transaction_reference,
        mode,
        business_reference,
        idempotency_key,
        coordinator_id,
        payload
    )
    VALUES (
        p_reference,
        p_mode,
        p_business_reference,
        p_idempotency_key,
        p_coordinator,
        COALESCE(p_payload, '{}'::JSONB)
    )
    ON CONFLICT (idempotency_key)
    DO NOTHING
    RETURNING transaction_id INTO v_transaction_id;

    IF v_transaction_id IS NULL THEN
        SELECT transaction_id
        INTO v_transaction_id
        FROM distributed_transactions
        WHERE idempotency_key = p_idempotency_key;

        IF EXISTS (
            SELECT 1
            FROM distributed_transactions
            WHERE transaction_id = v_transaction_id
              AND (
                  transaction_reference <> p_reference
                  OR mode <> p_mode
                  OR business_reference <> p_business_reference
                  OR coordinator_id <> p_coordinator
                  OR payload <> COALESCE(p_payload, '{}'::JSONB)
              )
        ) THEN
            RAISE EXCEPTION
                'Idempotency key reused with different request data';
        END IF;

        RETURN v_transaction_id;
    END IF;

    PERFORM record_transaction_event(
        v_transaction_id,
        'CREATED',
        'Distributed transaction created'
    );

    RETURN v_transaction_id;
END;
$$;

-- ============================================================
-- 12. REGISTER PARTICIPANTS
-- ============================================================

CREATE OR REPLACE FUNCTION register_participant(
    p_transaction_id UUID,
    p_service_name VARCHAR(100),
    p_execution_order INTEGER
)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    v_service_id BIGINT;
    v_participant_id BIGINT;
    v_mode transaction_mode;
BEGIN
    SELECT mode
    INTO v_mode
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
      AND state = 'CREATED'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Transaction missing or already started';
    END IF;

    SELECT service_id
    INTO v_service_id
    FROM services
    WHERE service_name = p_service_name
      AND is_available = TRUE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Service unavailable or not registered: %',
            p_service_name;
    END IF;

    IF v_mode = 'TWO_PHASE_COMMIT'
       AND NOT (
           SELECT supports_prepare
           FROM services
           WHERE service_id = v_service_id
       ) THEN
        RAISE EXCEPTION
            'Service does not support 2PC preparation';
    END IF;

    IF v_mode = 'SAGA'
       AND NOT (
           SELECT supports_compensation
           FROM services
           WHERE service_id = v_service_id
       ) THEN
        RAISE EXCEPTION
            'Saga participant lacks compensation support';
    END IF;

    INSERT INTO transaction_participants (
        transaction_id,
        service_id,
        execution_order,
        idempotency_key
    )
    VALUES (
        p_transaction_id,
        v_service_id,
        p_execution_order,
        p_transaction_id::TEXT || ':' || v_service_id::TEXT
    )
    RETURNING participant_id INTO v_participant_id;

    RETURN v_participant_id;
END;
$$;

-- ============================================================
-- 13. TWO-PHASE COMMIT: PREPARE PHASE
-- ============================================================

CREATE OR REPLACE FUNCTION prepare_transaction(
    p_transaction_id UUID,
    p_participant_id BIGINT,
    p_vote vote_type,
    p_reason TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_mode transaction_mode;
    v_state transaction_state;
    v_participant transaction_participants%ROWTYPE;
BEGIN
    SELECT mode, state
    INTO v_mode, v_state
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction not found';
    END IF;

    IF v_mode <> 'TWO_PHASE_COMMIT'
       OR v_state NOT IN ('CREATED', 'PREPARING') THEN
        RAISE EXCEPTION 'Transaction cannot accept prepare votes';
    END IF;

    IF p_vote NOT IN ('YES', 'NO') THEN
        RAISE EXCEPTION 'Vote must be YES or NO';
    END IF;

    SELECT *
    INTO v_participant
    FROM transaction_participants
    WHERE participant_id = p_participant_id
      AND transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Participant does not belong to transaction';
    END IF;

    IF v_participant.vote <> 'NOT_RECEIVED' THEN
        IF v_participant.vote = p_vote THEN
            RETURN;
        END IF;

        RAISE EXCEPTION 'Conflicting duplicate participant vote';
    END IF;

    IF v_participant.state <> 'ACTIVE' THEN
        RAISE EXCEPTION 'Participant is not active';
    END IF;

    UPDATE transaction_participants
    SET
        vote = p_vote,
        vote_recorded_at = NOW(),
        state = CASE
            WHEN p_vote = 'YES' THEN 'PREPARED'::participant_state
            ELSE 'ABORTED'::participant_state
        END,
        last_error = CASE
            WHEN p_vote = 'NO' THEN p_reason
            ELSE NULL
        END
    WHERE participant_id = p_participant_id;

    UPDATE distributed_transactions
    SET state = 'PREPARING'
    WHERE transaction_id = p_transaction_id
      AND state = 'CREATED';

    PERFORM record_transaction_event(
        p_transaction_id,
        CASE
            WHEN p_vote = 'YES' THEN 'VOTE_YES'::event_type
            ELSE 'VOTE_NO'::event_type
        END,
        COALESCE(p_reason, 'Participant vote recorded'),
        p_participant_id
    );
END;
$$;

-- ============================================================
-- 14. DETERMINE 2PC DECISION
-- ============================================================

CREATE OR REPLACE FUNCTION decide_2pc(
    p_transaction_id UUID,
    p_coordinator VARCHAR(100)
)
RETURNS transaction_state
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction distributed_transactions%ROWTYPE;
    v_total INTEGER;
    v_yes INTEGER;
    v_no INTEGER;
    v_decision transaction_state;
BEGIN
    SELECT *
    INTO v_transaction
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction not found';
    END IF;

    IF v_transaction.mode <> 'TWO_PHASE_COMMIT'
       OR v_transaction.state <> 'PREPARING' THEN
        RAISE EXCEPTION 'Transaction is not in PREPARING state';
    END IF;

    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE vote = 'YES'),
        COUNT(*) FILTER (WHERE vote = 'NO')
    INTO v_total, v_yes, v_no
    FROM transaction_participants
    WHERE transaction_id = p_transaction_id;

    IF v_total = 0 THEN
        RAISE EXCEPTION 'Transaction has no participants';
    END IF;

    IF v_yes + v_no <> v_total THEN
        RAISE EXCEPTION
            'Cannot decide while participant votes are outstanding';
    END IF;

    v_decision := CASE
        WHEN v_yes = v_total
            THEN 'COMMIT_DECIDED'::transaction_state
        ELSE 'ABORT_DECIDED'::transaction_state
    END;

    UPDATE distributed_transactions
    SET
        state = v_decision,
        decision_recorded_at = NOW()
    WHERE transaction_id = p_transaction_id;

    INSERT INTO transaction_decisions (
        transaction_id,
        decision,
        decision_reason,
        decided_by
    )
    VALUES (
        p_transaction_id,
        v_decision,
        CASE
            WHEN v_decision = 'COMMIT_DECIDED'
                THEN 'All participants voted YES'
            ELSE 'At least one participant voted NO'
        END,
        p_coordinator
    );

    PERFORM record_transaction_event(
        p_transaction_id,
        CASE
            WHEN v_decision = 'COMMIT_DECIDED'
                THEN 'COMMIT_DECISION'::event_type
            ELSE 'ABORT_DECISION'::event_type
        END,
        'Durable coordinator decision recorded'
    );

    RETURN v_decision;
END;
$$;

-- ============================================================
-- 15. TWO-PHASE COMMIT: COMMIT ACKNOWLEDGEMENT
-- ============================================================

CREATE OR REPLACE FUNCTION acknowledge_commit(
    p_transaction_id UUID,
    p_participant_id BIGINT
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_state transaction_state;
    v_participant_state participant_state;
BEGIN
    SELECT state
    INTO v_state
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF v_state NOT IN (
        'COMMIT_DECIDED',
        'COMMITTING'
    ) THEN
        RAISE EXCEPTION
            'Commit is not authorized by coordinator decision';
    END IF;

    SELECT state
    INTO v_participant_state
    FROM transaction_participants
    WHERE participant_id = p_participant_id
      AND transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Participant not found';
    END IF;

    IF v_participant_state = 'COMMITTED' THEN
        RETURN;
    END IF;

    IF v_participant_state <> 'PREPARED' THEN
        RAISE EXCEPTION 'Participant is not prepared';
    END IF;

    UPDATE transaction_participants
    SET
        state = 'COMMITTED',
        commit_acknowledged_at = NOW()
    WHERE participant_id = p_participant_id;

    UPDATE distributed_transactions
    SET state = 'COMMITTING'
    WHERE transaction_id = p_transaction_id
      AND state = 'COMMIT_DECIDED';

    PERFORM record_transaction_event(
        p_transaction_id,
        'COMMIT_ACK',
        'Participant acknowledged commit',
        p_participant_id
    );
END;
$$;

-- ============================================================
-- 16. FINALIZE 2PC
-- ============================================================

CREATE OR REPLACE FUNCTION finalize_2pc(
    p_transaction_id UUID
)
RETURNS transaction_state
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction distributed_transactions%ROWTYPE;
    v_total INTEGER;
    v_committed INTEGER;
    v_state transaction_state;
BEGIN
    SELECT *
    INTO v_transaction
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Transaction not found';
    END IF;

    IF v_transaction.mode <> 'TWO_PHASE_COMMIT' THEN
        RAISE EXCEPTION 'Transaction is not 2PC';
    END IF;

    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE state = 'COMMITTED')
    INTO v_total, v_committed
    FROM transaction_participants
    WHERE transaction_id = p_transaction_id;

    IF v_transaction.state = 'ABORT_DECIDED' THEN
        UPDATE transaction_participants
        SET state = 'ABORTED'
        WHERE transaction_id = p_transaction_id
          AND state IN ('ACTIVE', 'PREPARED');

        UPDATE distributed_transactions
        SET state = 'ABORTED'
        WHERE transaction_id = p_transaction_id;

        RETURN 'ABORTED';
    END IF;

    IF v_transaction.state NOT IN (
        'COMMIT_DECIDED',
        'COMMITTING'
    ) THEN
        RAISE EXCEPTION 'No finalizable commit decision exists';
    END IF;

    IF v_total <> v_committed THEN
        UPDATE distributed_transactions
        SET state = 'IN_DOUBT'
        WHERE transaction_id = p_transaction_id;

        RETURN 'IN_DOUBT';
    END IF;

    UPDATE distributed_transactions
    SET state = 'COMMITTED'
    WHERE transaction_id = p_transaction_id;

    RETURN 'COMMITTED';
END;
$$;

-- ============================================================
-- 17. SAGA STEP EXECUTION
-- ============================================================

CREATE OR REPLACE FUNCTION execute_saga_step(
    p_saga_step_id BIGINT,
    p_success BOOLEAN,
    p_error TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_transaction_id UUID;
    v_mode transaction_mode;
    v_step saga_steps%ROWTYPE;
BEGIN
    SELECT
        s.*,
        tp.transaction_id,
        dt.mode
    INTO v_step, v_transaction_id, v_mode
    FROM saga_steps s
    JOIN transaction_participants tp
        ON tp.participant_id = s.participant_id
    JOIN distributed_transactions dt
        ON dt.transaction_id = tp.transaction_id
    WHERE s.saga_step_id = p_saga_step_id
    FOR UPDATE OF s;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Saga step not found';
    END IF;

    IF v_mode <> 'SAGA' THEN
        RAISE EXCEPTION 'Step does not belong to a saga';
    END IF;

    IF v_step.state <> 'PENDING' THEN
        RAISE EXCEPTION 'Saga step is not pending';
    END IF;

    UPDATE saga_steps
    SET
        state = CASE
            WHEN p_success THEN 'COMPLETED'::saga_step_state
            ELSE 'FAILED'::saga_step_state
        END,
        executed_at = NOW(),
        last_error = p_error
    WHERE saga_step_id = p_saga_step_id;

    IF p_success THEN
        UPDATE transaction_participants
        SET state = 'COMMITTED'
        WHERE participant_id = v_step.participant_id;

        PERFORM record_transaction_event(
            v_transaction_id,
            'LOCAL_COMMIT',
            'Saga local transaction completed',
            v_step.participant_id
        );
    ELSE
        UPDATE transaction_participants
        SET
            state = 'FAILED',
            last_error = p_error
        WHERE participant_id = v_step.participant_id;

        UPDATE distributed_transactions
        SET state = 'COMPENSATING'
        WHERE transaction_id = v_transaction_id
          AND state IN ('CREATED', 'PREPARING');

        PERFORM record_transaction_event(
            v_transaction_id,
            'FAILURE',
            COALESCE(p_error, 'Saga step failed'),
            v_step.participant_id
        );
    END IF;
END;
$$;

-- ============================================================
-- 18. SAGA COMPENSATION
-- ============================================================

CREATE OR REPLACE FUNCTION compensate_saga_step(
    p_saga_step_id BIGINT,
    p_success BOOLEAN,
    p_error TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    v_step saga_steps%ROWTYPE;
    v_transaction_id UUID;
    v_order INTEGER;
    v_higher_pending INTEGER;
BEGIN
    SELECT s.*, tp.transaction_id
    INTO v_step, v_transaction_id
    FROM saga_steps s
    JOIN transaction_participants tp
        ON tp.participant_id = s.participant_id
    JOIN distributed_transactions dt
        ON dt.transaction_id = tp.transaction_id
    WHERE s.saga_step_id = p_saga_step_id
      AND dt.mode = 'SAGA'
    FOR UPDATE OF s;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Saga step not found';
    END IF;

    IF v_step.state NOT IN (
        'COMPLETED',
        'COMPENSATION_FAILED'
    ) THEN
        RAISE EXCEPTION 'Step is not eligible for compensation';
    END IF;

    SELECT MAX(execution_order)
    INTO v_order
    FROM saga_steps
    WHERE participant_id = v_step.participant_id;

    SELECT COUNT(*)
    INTO v_higher_pending
    FROM saga_steps s
    JOIN transaction_participants tp
        ON tp.participant_id = s.participant_id
    WHERE tp.transaction_id = v_transaction_id
      AND s.execution_order > v_step.execution_order
      AND s.state IN (
          'COMPLETED',
          'COMPENSATION_FAILED'
      );

    IF v_higher_pending > 0 THEN
        RAISE EXCEPTION
            'Compensate later saga steps before earlier steps';
    END IF;

    UPDATE saga_steps
    SET
        state = CASE
            WHEN p_success
                THEN 'COMPENSATED'::saga_step_state
            ELSE 'COMPENSATION_FAILED'::saga_step_state
        END,
        compensated_at = CASE
            WHEN p_success THEN NOW()
            ELSE NULL
        END,
        last_error = p_error,
        retry_count = retry_count + CASE
            WHEN p_success THEN 0
            ELSE 1
        END
    WHERE saga_step_id = p_saga_step_id;

    IF p_success THEN
        UPDATE transaction_participants
        SET state = 'ABORTED'
        WHERE participant_id = v_step.participant_id;

        PERFORM record_transaction_event(
            v_transaction_id,
            'COMPENSATION_SUCCESS',
            'Saga compensation completed',
            v_step.participant_id
        );
    ELSE
        PERFORM record_transaction_event(
            v_transaction_id,
            'COMPENSATION_FAILURE',
            COALESCE(p_error, 'Compensation failed'),
            v_step.participant_id
        );
    END IF;
END;
$$;

-- ============================================================
-- 19. FINALIZE SAGA
-- ============================================================

CREATE OR REPLACE FUNCTION finalize_saga(
    p_transaction_id UUID
)
RETURNS transaction_state
LANGUAGE plpgsql
AS $$
DECLARE
    v_total INTEGER;
    v_completed INTEGER;
    v_compensated INTEGER;
    v_failed INTEGER;
    v_state transaction_state;
BEGIN
    SELECT state
    INTO v_state
    FROM distributed_transactions
    WHERE transaction_id = p_transaction_id
      AND mode = 'SAGA'
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Saga transaction not found';
    END IF;

    SELECT
        COUNT(*),
        COUNT(*) FILTER (WHERE state = 'COMPLETED'),
        COUNT(*) FILTER (WHERE state = 'COMPENSATED'),
        COUNT(*) FILTER (
            WHERE state IN (
                'FAILED',
                'COMPENSATION_FAILED'
            )
        )
    INTO
        v_total,
        v_completed,
        v_compensated,
        v_failed
    FROM saga_steps s
    JOIN transaction_participants tp
        ON tp.participant_id = s.participant_id
    WHERE tp.transaction_id = p_transaction_id;

    IF v_total = 0 THEN
        RAISE EXCEPTION 'Saga contains no steps';
    END IF;

    IF v_completed = v_total THEN
        UPDATE distributed_transactions
        SET state = 'COMMITTED'
        WHERE transaction_id = p_transaction_id;

        RETURN 'COMMITTED';
    END IF;

    IF v_failed > 0 THEN
        UPDATE distributed_transactions
        SET state = 'FAILED'
        WHERE transaction_id = p_transaction_id;

        RETURN 'FAILED';
    END IF;

    IF v_compensated + (
        SELECT COUNT(*)
        FROM saga_steps s
        JOIN transaction_participants tp
            ON tp.participant_id = s.participant_id
        WHERE tp.transaction_id = p_transaction_id
          AND s.state = 'FAILED'
    ) = v_total THEN

        UPDATE distributed_transactions
        SET state = 'COMPENSATED'
        WHERE transaction_id = p_transaction_id;

        RETURN 'COMPENSATED';
    END IF;

    RETURN v_state;
END;
$$;

-- ============================================================
-- 20. MERGE-FREE REPORTING: TRANSACTION OVERVIEW
-- ============================================================

CREATE VIEW transaction_overview AS
SELECT
    dt.transaction_id,
    dt.transaction_reference,
    dt.business_reference,
    dt.mode,
    dt.state,
    COUNT(DISTINCT tp.participant_id) AS participant_count,
    COUNT(DISTINCT tp.participant_id)
        FILTER (WHERE tp.state = 'COMMITTED')
        AS committed_participants,
    COUNT(DISTINCT tp.participant_id)
        FILTER (WHERE tp.state = 'ABORTED')
        AS aborted_participants,
    COUNT(DISTINCT tp.participant_id)
        FILTER (WHERE tp.vote = 'YES')
        AS yes_votes,
    COUNT(DISTINCT tp.participant_id)
        FILTER (WHERE tp.vote = 'NO')
        AS no_votes,
    dt.created_at,
    dt.updated_at
FROM distributed_transactions dt
LEFT JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
GROUP BY
    dt.transaction_id,
    dt.transaction_reference,
    dt.business_reference,
    dt.mode,
    dt.state,
    dt.created_at,
    dt.updated_at;

-- ============================================================
-- 21. RECOVERY QUEUE
-- ============================================================

CREATE VIEW transaction_recovery_queue AS
SELECT
    dt.transaction_id,
    dt.transaction_reference,
    dt.mode,
    dt.state,
    dt.decision_recorded_at,
    COUNT(tp.participant_id) AS total_participants,
    COUNT(tp.participant_id)
        FILTER (
            WHERE tp.state = 'PREPARED'
        ) AS waiting_for_commit,
    COUNT(tp.participant_id)
        FILTER (
            WHERE tp.state = 'COMMITTED'
        ) AS committed_count
FROM distributed_transactions dt
LEFT JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
WHERE dt.state IN (
    'IN_DOUBT',
    'COMMIT_DECIDED',
    'COMMITTING',
    'ABORT_DECIDED',
    'ABORTING',
    'COMPENSATING',
    'FAILED'
)
GROUP BY
    dt.transaction_id,
    dt.transaction_reference,
    dt.mode,
    dt.state,
    dt.decision_recorded_at;

-- ============================================================
-- 22. REPORTING: SAGA COMPENSATION METRICS
-- ============================================================

CREATE VIEW saga_compensation_report AS
SELECT
    dt.transaction_reference,
    COUNT(*) AS total_steps,
    COUNT(*) FILTER (
        WHERE ss.state = 'COMPLETED'
    ) AS completed_steps,
    COUNT(*) FILTER (
        WHERE ss.state = 'COMPENSATED'
    ) AS compensated_steps,
    COUNT(*) FILTER (
        WHERE ss.state = 'COMPENSATION_FAILED'
    ) AS failed_compensations,
    SUM(ss.retry_count) AS total_retries
FROM distributed_transactions dt
JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
JOIN saga_steps ss
    ON ss.participant_id = tp.participant_id
WHERE dt.mode = 'SAGA'
GROUP BY dt.transaction_reference;

-- ============================================================
-- 23. SAMPLE DATA: SUCCESSFUL 2PC
-- ============================================================

DO $$
DECLARE
    v_tx UUID;
    v_inventory BIGINT;
    v_payment BIGINT;
    v_order BIGINT;
BEGIN
    v_tx := create_transaction(
        'TX-2PC-001',
        'TWO_PHASE_COMMIT',
        'ORDER-1001',
        'IDEMPOTENCY-1001',
        'Coordinator-A',
        '{"amount": 2500, "currency": "INR"}'
    );

    v_inventory := register_participant(
        v_tx,
        'InventoryService',
        1
    );

    v_payment := register_participant(
        v_tx,
        'PaymentService',
        2
    );

    v_order := register_participant(
        v_tx,
        'OrderService',
        3
    );

    PERFORM prepare_transaction(v_tx, v_inventory, 'YES');
    PERFORM prepare_transaction(v_tx, v_payment, 'YES');
    PERFORM prepare_transaction(v_tx, v_order, 'YES');

    PERFORM decide_2pc(v_tx, 'Coordinator-A');

    PERFORM acknowledge_commit(v_tx, v_inventory);
    PERFORM acknowledge_commit(v_tx, v_payment);
    PERFORM acknowledge_commit(v_tx, v_order);

    PERFORM finalize_2pc(v_tx);
END;
$$;

-- ============================================================
-- 24. SAMPLE DATA: 2PC REJECTION
-- ============================================================

DO $$
DECLARE
    v_tx UUID;
    v_inventory BIGINT;
    v_payment BIGINT;
BEGIN
    v_tx := create_transaction(
        'TX-2PC-002',
        'TWO_PHASE_COMMIT',
        'ORDER-1002',
        'IDEMPOTENCY-1002',
        'Coordinator-A',
        '{"amount": 9000, "currency": "INR"}'
    );

    v_inventory := register_participant(
        v_tx,
        'InventoryService',
        1
    );

    v_payment := register_participant(
        v_tx,
        'PaymentService',
        2
    );

    PERFORM prepare_transaction(v_tx, v_inventory, 'YES');

    PERFORM prepare_transaction(
        v_tx,
        v_payment,
        'NO',
        'Insufficient payment authorization'
    );

    PERFORM decide_2pc(v_tx, 'Coordinator-A');

    PERFORM finalize_2pc(v_tx);
END;
$$;

-- ============================================================
-- 25. SAMPLE DATA: IN-DOUBT COMMIT
-- ============================================================

DO $$
DECLARE
    v_tx UUID;
    v_inventory BIGINT;
    v_ledger BIGINT;
BEGIN
    v_tx := create_transaction(
        'TX-2PC-003',
        'TWO_PHASE_COMMIT',
        'TRANSFER-1003',
        'IDEMPOTENCY-1003',
        'Coordinator-B',
        '{"amount": 50000, "currency": "INR"}'
    );

    v_inventory := register_participant(
        v_tx,
        'InventoryService',
        1
    );

    v_ledger := register_participant(
        v_tx,
        'LedgerService',
        2
    );

    PERFORM prepare_transaction(v_tx, v_inventory, 'YES');
    PERFORM prepare_transaction(v_tx, v_ledger, 'YES');

    PERFORM decide_2pc(v_tx, 'Coordinator-B');

    -- Only one participant confirms commit.
    PERFORM acknowledge_commit(v_tx, v_inventory);

    -- The other participant remains PREPARED.
    PERFORM finalize_2pc(v_tx);
END;
$$;

-- ============================================================
-- 26. SAMPLE DATA: SUCCESSFUL SAGA
-- ============================================================

DO $$
DECLARE
    v_tx UUID;
    v_inventory BIGINT;
    v_payment BIGINT;
    v_shipping BIGINT;
    v_step BIGINT;
BEGIN
    v_tx := create_transaction(
        'TX-SAGA-001',
        'SAGA',
        'ORDER-2001',
        'IDEMPOTENCY-2001',
        'SagaCoordinator',
        '{"amount": 4500, "currency": "INR"}'
    );

    v_inventory := register_participant(
        v_tx,
        'InventoryService',
        1
    );

    v_payment := register_participant(
        v_tx,
        'PaymentService',
        2
    );

    v_shipping := register_participant(
        v_tx,
        'ShippingService',
        3
    );

    INSERT INTO saga_steps (
        participant_id,
        step_name,
        execution_order,
        command_payload,
        compensation_payload
    )
    VALUES
        (
            v_inventory,
            'Reserve inventory',
            1,
            '{"quantity": 2}',
            '{"action": "release_inventory"}'
        ),
        (
            v_payment,
            'Capture payment',
            2,
            '{"amount": 4500}',
            '{"action": "refund_payment"}'
        ),
        (
            v_shipping,
            'Create shipment',
            3,
            '{"destination": "Lucknow"}',
            '{"action": "cancel_shipment"}'
        );

    FOR v_step IN
        SELECT saga_step_id
        FROM saga_steps
        WHERE participant_id IN (
            v_inventory,
            v_payment,
            v_shipping
        )
        ORDER BY execution_order
    LOOP
        PERFORM execute_saga_step(v_step, TRUE);
    END LOOP;

    PERFORM finalize_saga(v_tx);
END;
$$;

-- ============================================================
-- 27. SAMPLE DATA: SAGA FAILURE AND COMPENSATION
-- ============================================================

DO $$
DECLARE
    v_tx UUID;
    v_inventory BIGINT;
    v_payment BIGINT;
    v_shipping BIGINT;
    v_step_1 BIGINT;
    v_step_2 BIGINT;
    v_step_3 BIGINT;
BEGIN
    v_tx := create_transaction(
        'TX-SAGA-002',
        'SAGA',
        'ORDER-2002',
        'IDEMPOTENCY-2002',
        'SagaCoordinator',
        '{"amount": 12000, "currency": "INR"}'
    );

    v_inventory := register_participant(
        v_tx,
        'InventoryService',
        1
    );

    v_payment := register_participant(
        v_tx,
        'PaymentService',
        2
    );

    v_shipping := register_participant(
        v_tx,
        'ShippingService',
        3
    );

    INSERT INTO saga_steps (
        participant_id,
        step_name,
        execution_order
    )
    VALUES
        (v_inventory, 'Reserve inventory', 1),
        (v_payment, 'Capture payment', 2),
        (v_shipping, 'Create shipment', 3);

    SELECT saga_step_id INTO v_step_1
    FROM saga_steps
    WHERE participant_id = v_inventory;

    SELECT saga_step_id INTO v_step_2
    FROM saga_steps
    WHERE participant_id = v_payment;

    SELECT saga_step_id INTO v_step_3
    FROM saga_steps
    WHERE participant_id = v_shipping;

    PERFORM execute_saga_step(v_step_1, TRUE);
    PERFORM execute_saga_step(v_step_2, TRUE);

    -- Shipping fails.
    PERFORM execute_saga_step(
        v_step_3,
        FALSE,
        'Shipping provider unavailable'
    );

    -- Compensation executes in reverse order.
    PERFORM compensate_saga_step(v_step_2, TRUE);
    PERFORM compensate_saga_step(v_step_1, TRUE);

    PERFORM finalize_saga(v_tx);
END;
$$;

-- ============================================================
-- 28. RETRIEVAL QUERIES
-- ============================================================

-- All transactions.
SELECT *
FROM transaction_overview
ORDER BY created_at DESC;

-- All participants and their votes.
SELECT
    dt.transaction_reference,
    s.service_name,
    tp.execution_order,
    tp.state,
    tp.vote,
    tp.last_error
FROM transaction_participants tp
JOIN distributed_transactions dt
    ON dt.transaction_id = tp.transaction_id
JOIN services s
    ON s.service_id = tp.service_id
ORDER BY dt.transaction_reference, tp.execution_order;

-- Detailed audit history.
SELECT
    dt.transaction_reference,
    te.event,
    te.description,
    te.occurred_at
FROM transaction_events te
JOIN distributed_transactions dt
    ON dt.transaction_id = te.transaction_id
ORDER BY te.occurred_at;

-- ============================================================
-- 29. VALIDATION QUERIES
-- ============================================================

-- Identify 2PC transactions with missing votes.
SELECT
    dt.transaction_reference,
    COUNT(*) FILTER (
        WHERE tp.vote = 'NOT_RECEIVED'
    ) AS outstanding_votes
FROM distributed_transactions dt
JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
WHERE dt.mode = 'TWO_PHASE_COMMIT'
GROUP BY dt.transaction_reference
HAVING COUNT(*) FILTER (
    WHERE tp.vote = 'NOT_RECEIVED'
) > 0;

-- Detect inconsistent committed transactions.
SELECT
    dt.transaction_reference,
    COUNT(*) AS participants,
    COUNT(*) FILTER (
        WHERE tp.state = 'COMMITTED'
    ) AS committed
FROM distributed_transactions dt
JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
WHERE dt.mode = 'TWO_PHASE_COMMIT'
  AND dt.state = 'COMMITTED'
GROUP BY dt.transaction_reference
HAVING COUNT(*) FILTER (
    WHERE tp.state = 'COMMITTED'
) <> COUNT(*);

-- ============================================================
-- 30. AGGREGATION AND EVALUATION
-- ============================================================

SELECT
    mode,
    state,
    COUNT(*) AS transaction_count
FROM distributed_transactions
GROUP BY mode, state
ORDER BY mode, state;

SELECT
    COUNT(*) AS total_transactions,
    COUNT(*) FILTER (
        WHERE state = 'COMMITTED'
    ) AS successful,
    COUNT(*) FILTER (
        WHERE state = 'ABORTED'
    ) AS aborted,
    COUNT(*) FILTER (
        WHERE state = 'IN_DOUBT'
    ) AS unresolved,
    COUNT(*) FILTER (
        WHERE state = 'COMPENSATED'
    ) AS compensated,
    COUNT(*) FILTER (
        WHERE state = 'FAILED'
    ) AS failed
FROM distributed_transactions;

-- Saga compensation effectiveness.
SELECT
    transaction_reference,
    total_steps,
    completed_steps,
    compensated_steps,
    failed_compensations,
    total_retries
FROM saga_compensation_report;

-- ============================================================
-- 31. ELIGIBILITY DETERMINATION
-- ============================================================

-- A 2PC transaction is eligible for a commit decision only
-- when every registered participant has voted YES.

WITH vote_summary AS (
    SELECT
        dt.transaction_id,
        dt.transaction_reference,
        COUNT(tp.participant_id) AS total_participants,
        COUNT(tp.participant_id)
            FILTER (WHERE tp.vote = 'YES') AS yes_votes,
        COUNT(tp.participant_id)
            FILTER (WHERE tp.vote = 'NO') AS no_votes,
        COUNT(tp.participant_id)
            FILTER (
                WHERE tp.vote = 'NOT_RECEIVED'
            ) AS pending_votes
    FROM distributed_transactions dt
    LEFT JOIN transaction_participants tp
        ON tp.transaction_id = dt.transaction_id
    WHERE dt.mode = 'TWO_PHASE_COMMIT'
      AND dt.state IN ('CREATED', 'PREPARING')
    GROUP BY
        dt.transaction_id,
        dt.transaction_reference
)
SELECT
    *,
    CASE
        WHEN total_participants = 0
            THEN 'INVALID'
        WHEN no_votes > 0
            THEN 'ABORT_REQUIRED'
        WHEN pending_votes > 0
            THEN 'WAITING'
        WHEN yes_votes = total_participants
            THEN 'COMMIT_ELIGIBLE'
        ELSE 'INVALID'
    END AS eligibility
FROM vote_summary;

-- ============================================================
-- 32. RECOVERY PROCESSING
-- ============================================================

-- Identify prepared participants whose coordinator decision
-- has already been recorded as COMMIT_DECIDED.
SELECT
    dt.transaction_reference,
    tp.participant_id,
    s.service_name,
    tp.state,
    dt.decision_recorded_at
FROM distributed_transactions dt
JOIN transaction_participants tp
    ON tp.transaction_id = dt.transaction_id
JOIN services s
    ON s.service_id = tp.service_id
WHERE dt.state IN ('COMMIT_DECIDED', 'COMMITTING', 'IN_DOUBT')
  AND tp.state = 'PREPARED'
ORDER BY dt.decision_recorded_at;

-- Identify compensation failures requiring operational recovery.
SELECT
    dt.transaction_reference,
    ss.saga_step_id,
    ss.step_name,
    ss.retry_count,
    ss.last_error
FROM saga_steps ss
JOIN transaction_participants tp
    ON tp.participant_id = ss.participant_id
JOIN distributed_transactions dt
    ON dt.transaction_id = tp.transaction_id
WHERE ss.state = 'COMPENSATION_FAILED'
ORDER BY ss.retry_count DESC;

-- ============================================================
-- 33. TRANSACTIONAL IDEMPOTENCY DEMONSTRATION
-- ============================================================

BEGIN;

SELECT create_transaction(
    'TX-IDEMPOTENT-001',
    'SAGA',
    'ORDER-3001',
    'IDEMPOTENCY-3001',
    'Coordinator-C',
    '{"amount": 1000, "currency": "INR"}'
);

-- Repeating the same request returns the original transaction ID.
SELECT create_transaction(
    'TX-IDEMPOTENT-001',
    'SAGA',
    'ORDER-3001',
    'IDEMPOTENCY-3001',
    'Coordinator-C',
    '{"amount": 1000, "currency": "INR"}'
);

COMMIT;

-- Reusing the same key with different data raises an exception.
-- Execute separately if testing the rejection:
--
-- SELECT create_transaction(
--     'TX-IDEMPOTENT-002',
--     'SAGA',
--     'ORDER-9999',
--     'IDEMPOTENCY-3001',
--     'Coordinator-C',
--     '{"amount": 9999}'
-- );

-- ============================================================
-- 34. FINAL OPERATIONAL REPORT
-- ============================================================

SELECT
    transaction_reference,
    mode,
    state,
    participant_count,
    committed_participants,
    aborted_participants,
    yes_votes,
    no_votes
FROM transaction_overview
ORDER BY created_at DESC;

SELECT *
FROM transaction_recovery_queue
ORDER BY decision_recorded_at;

SELECT *
FROM saga_compensation_report
ORDER BY transaction_reference;

-- ============================================================
-- PRODUCTION CONSIDERATIONS
--
-- 1. Keep coordinator decisions durable.
-- 2. Use transactional outbox records for reliable messaging.
-- 3. Use unique message IDs and idempotent consumers.
-- 4. Do not assume network timeout means operation failure.
-- 5. Never reverse a committed 2PC participant with ABORT.
-- 6. Retry saga compensation using bounded backoff.
-- 7. Preserve audit history.
-- 8. Restrict decision and state-changing functions using
--    database roles and EXECUTE privileges.
-- 9. Use separate local database transactions for each service.
-- 10. Native PREPARE TRANSACTION requires separate operational
--     recovery and monitoring procedures.
-- ============================================================
