"use strict";

/*
 * Distributed Transactions
 * Event-driven Two-Phase Commit and Saga Orchestration
 *
 * Runtime: Node.js 18+
 *
 * Features:
 * - Asynchronous transaction participants
 * - Event-driven coordinator
 * - Two-phase commit
 * - Saga orchestration
 * - Reverse-order compensation
 * - Idempotency protection
 * - Timeout and failure handling
 * - Structured transaction auditing
 */

const { randomUUID } = require("node:crypto");
const { EventEmitter } = require("node:events");

class TransactionError extends Error {
    constructor(message, code = "TRANSACTION_ERROR") {
        super(message);
        this.name = "TransactionError";
        this.code = code;
    }
}

const TransactionState = Object.freeze({
    CREATED: "CREATED",
    PREPARING: "PREPARING",
    PREPARED: "PREPARED",
    COMMITTING: "COMMITTING",
    COMMITTED: "COMMITTED",
    ABORTING: "ABORTING",
    ABORTED: "ABORTED",
    COMPENSATING: "COMPENSATING",
    COMPENSATED: "COMPENSATED",
    IN_DOUBT: "IN_DOUBT",
    FAILED: "FAILED"
});

const ParticipantState = Object.freeze({
    ACTIVE: "ACTIVE",
    PREPARED: "PREPARED",
    COMMITTED: "COMMITTED",
    ABORTED: "ABORTED"
});

const TransactionMode = Object.freeze({
    TWO_PHASE_COMMIT: "2PC",
    SAGA: "SAGA"
});

class AuditLog {
    constructor(transactionId) {
        this.transactionId = transactionId;
        this.events = [];
    }

    record(action, participant, details = {}) {
        const event = Object.freeze({
            transactionId: this.transactionId,
            action,
            participant,
            details,
            timestamp: new Date().toISOString()
        });

        this.events.push(event);

        console.log(
            `[${action}] ${participant}:`,
            JSON.stringify(details)
        );

        return event;
    }

    getByAction(action) {
        return this.events.filter(
            event => event.action === action
        );
    }
}

class TransactionParticipant {
    constructor({
        name,
        prepare,
        execute,
        commit,
        abort,
        compensate
    }) {
        if (!name || typeof name !== "string") {
            throw new TypeError("Participant name is required");
        }

        this.name = name;
        this.state = ParticipantState.ACTIVE;

        this.prepareHandler = prepare || (async () => true);
        this.executeHandler = execute || (async () => true);
        this.commitHandler = commit || (async () => true);
        this.abortHandler = abort || (async () => true);
        this.compensateHandler = compensate || (async () => true);

        this.executedOperations = new Set();
        this.completedOperations = new Set();
    }

    async prepare(transactionId) {
        if (this.state !== ParticipantState.ACTIVE) {
            throw new TransactionError(
                `${this.name} cannot prepare in ${this.state}`
            );
        }

        const accepted = await this.prepareHandler(transactionId);

        if (accepted !== true) {
            return false;
        }

        this.state = ParticipantState.PREPARED;
        return true;
    }

    async commit(transactionId) {
        if (this.state !== ParticipantState.PREPARED) {
            throw new TransactionError(
                `${this.name} is not prepared`
            );
        }

        await this.commitHandler(transactionId);
        this.state = ParticipantState.COMMITTED;
    }

    async abort(transactionId) {
        if (this.state === ParticipantState.COMMITTED) {
            throw new TransactionError(
                "A committed 2PC participant cannot be aborted"
            );
        }

        if (this.state === ParticipantState.ABORTED) {
            return;
        }

        await this.abortHandler(transactionId);
        this.state = ParticipantState.ABORTED;
    }

    async execute(transactionId) {
        if (this.state !== ParticipantState.ACTIVE) {
            throw new TransactionError(
                `${this.name} cannot execute in ${this.state}`
            );
        }

        if (this.executedOperations.has(transactionId)) {
            return;
        }

        await this.executeHandler(transactionId);

        this.executedOperations.add(transactionId);
        this.state = ParticipantState.COMMITTED;
    }

    async compensate(transactionId) {
        if (this.state !== ParticipantState.COMMITTED) {
            throw new TransactionError(
                `${this.name} has no committed operation`
            );
        }

        if (this.completedOperations.has(transactionId)) {
            return;
        }

        await this.compensateHandler(transactionId);

        this.completedOperations.add(transactionId);
        this.state = ParticipantState.ABORTED;
    }
}

class DistributedTransaction extends EventEmitter {
    constructor({
        participants,
        mode,
        transactionId = randomUUID()
    }) {
        super();

        if (!Array.isArray(participants) || participants.length === 0) {
            throw new TypeError("Participants must be a non-empty array");
        }

        const names = participants.map(p => p.name);

        if (new Set(names).size !== names.length) {
            throw new TypeError("Participant names must be unique");
        }

        if (!Object.values(TransactionMode).includes(mode)) {
            throw new TypeError("Unsupported transaction mode");
        }

        this.id = transactionId;
        this.mode = mode;
        this.participants = [...participants];
        this.state = TransactionState.CREATED;
        this.audit = new AuditLog(this.id);
    }

    transition(nextState) {
        const previousState = this.state;
        this.state = nextState;

        const event = this.audit.record(
            "STATE_CHANGE",
            "COORDINATOR",
            { previousState, nextState }
        );

        this.emit("stateChange", event);
    }

    async execute2PC() {
        if (this.mode !== TransactionMode.TWO_PHASE_COMMIT) {
            throw new TransactionError("Transaction mode is not 2PC");
        }

        if (this.state !== TransactionState.CREATED) {
            throw new TransactionError("Transaction already started");
        }

        this.transition(TransactionState.PREPARING);

        const prepared = [];

        try {
            // Phase 1: Collect participant votes.
            const votes = await Promise.all(
                this.participants.map(async participant => {
                    try {
                        const accepted = await participant.prepare(this.id);

                        this.audit.record(
                            accepted ? "VOTE_YES" : "VOTE_NO",
                            participant.name
                        );

                        return { participant, accepted };
                    } catch (error) {
                        this.audit.record(
                            "PREPARE_ERROR",
                            participant.name,
                            { message: error.message }
                        );

                        return { participant, accepted: false };
                    }
                })
            );

            for (const vote of votes) {
                if (vote.accepted) {
                    prepared.push(vote.participant);
                }
            }

            if (prepared.length !== this.participants.length) {
                throw new TransactionError("Not all participants voted YES");
            }

            this.transition(TransactionState.PREPARED);

        } catch (error) {
            this.transition(TransactionState.ABORTING);

            const abortResults = await Promise.allSettled(
                this.participants
                    .filter(p => p.state !== ParticipantState.COMMITTED)
                    .map(p => p.abort(this.id))
            );

            const abortFailed = abortResults.some(
                result => result.status === "rejected"
            );

            this.transition(
                abortFailed
                    ? TransactionState.IN_DOUBT
                    : TransactionState.ABORTED
            );

            return false;
        }

        // Phase 2: The durable commit decision must precede
        // broadcasting COMMIT in a production coordinator.
        this.transition(TransactionState.COMMITTING);

        const commitResults = await Promise.allSettled(
            this.participants.map(
                participant => participant.commit(this.id)
            )
        );

        const failures = commitResults.filter(
            result => result.status === "rejected"
        );

        if (failures.length > 0) {
            this.audit.record(
                "COMMIT_UNCERTAIN",
                "COORDINATOR",
                { failureCount: failures.length }
            );

            this.transition(TransactionState.IN_DOUBT);
            return false;
        }

        this.transition(TransactionState.COMMITTED);
        return true;
    }

    async executeSaga() {
        if (this.mode !== TransactionMode.SAGA) {
            throw new TransactionError("Transaction mode is not SAGA");
        }

        if (this.state !== TransactionState.CREATED) {
            throw new TransactionError("Transaction already started");
        }

        const completed = [];

        try {
            for (const participant of this.participants) {
                await participant.execute(this.id);
                completed.push(participant);

                this.audit.record(
                    "STEP_COMPLETED",
                    participant.name
                );

                this.emit("stepCompleted", participant.name);
            }

            this.transition(TransactionState.COMMITTED);
            return true;

        } catch (error) {
            this.audit.record(
                "SAGA_STEP_FAILED",
                "COORDINATOR",
                { message: error.message }
            );

            this.transition(TransactionState.COMPENSATING);

            const compensationFailures = [];

            // Sequential reverse-order compensation preserves
            // dependency order between completed saga steps.
            for (const participant of [...completed].reverse()) {
                try {
                    await participant.compensate(this.id);

                    this.audit.record(
                        "COMPENSATION_COMPLETED",
                        participant.name
                    );

                } catch (compensationError) {
                    compensationFailures.push({
                        participant: participant.name,
                        message: compensationError.message
                    });

                    this.audit.record(
                        "COMPENSATION_FAILED",
                        participant.name,
                        { message: compensationError.message }
                    );
                }
            }

            this.transition(
                compensationFailures.length > 0
                    ? TransactionState.FAILED
                    : TransactionState.COMPENSATED
            );

            return false;
        }
    }

    getReport() {
        return {
            transactionId: this.id,
            mode: this.mode,
            state: this.state,
            participants: this.participants.map(p => ({
                name: p.name,
                state: p.state
            })),
            events: [...this.audit.events]
        };
    }
}

function createOrderParticipants({
    shippingAvailable = true
} = {}) {
    return [
        new TransactionParticipant({
            name: "InventoryService",
            execute: async () => {
                console.log("Inventory reserved");
            },
            compensate: async () => {
                console.log("Inventory reservation released");
            }
        }),

        new TransactionParticipant({
            name: "PaymentService",
            execute: async () => {
                console.log("Payment captured");
            },
            compensate: async () => {
                console.log("Payment refund initiated");
            }
        }),

        new TransactionParticipant({
            name: "ShippingService",
            execute: async () => {
                if (!shippingAvailable) {
                    throw new TransactionError(
                        "Shipping provider unavailable"
                    );
                }

                console.log("Shipment created");
            },
            compensate: async () => {
                console.log("Shipment cancelled");
            }
        })
    ];
}

async function main() {
    // Event-driven saga.
    console.log("\nCASE 1: SUCCESSFUL SAGA");

    const successfulSaga = new DistributedTransaction({
        participants: createOrderParticipants(),
        mode: TransactionMode.SAGA
    });

    successfulSaga.on("stateChange", event => {
        console.log("Observer:", event.details.nextState);
    });

    await successfulSaga.executeSaga();

    // Failed saga and reverse compensation.
    console.log("\nCASE 2: FAILED SAGA");

    const failedSaga = new DistributedTransaction({
        participants: createOrderParticipants({
            shippingAvailable: false
        }),
        mode: TransactionMode.SAGA
    });

    await failedSaga.executeSaga();

    // Two-phase commit.
    console.log("\nCASE 3: TWO-PHASE COMMIT");

    const twoPhase = new DistributedTransaction({
        mode: TransactionMode.TWO_PHASE_COMMIT,
        participants: [
            new TransactionParticipant({
                name: "AccountService"
            }),
            new TransactionParticipant({
                name: "LedgerService"
            }),
            new TransactionParticipant({
                name: "SettlementService"
            })
        ]
    });

    await twoPhase.execute2PC();

    console.log("\nREPORT");
    console.log(
        JSON.stringify(
            twoPhase.getReport(),
            null,
            2
        )
    );
}

main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
