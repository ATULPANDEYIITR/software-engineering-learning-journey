# Distributed Transactions: Two-Phase Commit and Sagas

## 1. Technical Scope

Distributed transactions coordinate business operations that involve multiple independent services, databases, or transactional resources.

A distributed transaction must address failures that do not occur in the same way as failures inside a single database transaction.

Examples include:

- Reserving inventory and capturing payment.
- Transferring funds between banking accounts.
- Creating an order and scheduling shipment.
- Updating customer information across multiple services.
- Synchronizing financial records and settlement systems.

The central engineering problem is maintaining acceptable consistency when participants operate independently and communicate over unreliable networks.

This project implements two major coordination approaches:

1. Two-Phase Commit (2PC), a distributed atomic commit protocol.
2. Saga, a sequence of local transactions coordinated through compensating operations.

The five implementations demonstrate different engineering perspectives, including transaction simulation, asynchronous coordination, governance logic, enterprise domain modeling, and relational transaction management.

## 2. Distributed Transaction Fundamentals

### 2.1 Local Transactions

A local transaction operates within one transactional resource, usually one database.

The traditional ACID properties are:

| Property | Meaning |
|---|---|
| Atomicity | The local transaction succeeds or fails as one unit. |
| Consistency | Database constraints remain satisfied. |
| Isolation | Concurrent transactions follow the configured isolation rules. |
| Durability | Committed changes survive according to the database's durability guarantees. |

A local database transaction can atomically update multiple tables within that database.

It cannot automatically provide atomicity across independent services using separate databases.

### 2.2 Distributed Transaction

Consider an e-commerce order involving three services:

- Inventory Service reserves stock.
- Payment Service captures payment.
- Shipping Service creates a shipment.

Each service maintains its own local data.

A failure after inventory reservation but before shipment creation can leave the business process incomplete.

A distributed transaction protocol coordinates these independent operations.

### 2.3 Important Distinctions

| Concept | Responsibility |
|---|---|
| Local transaction | Maintains consistency within one resource. |
| Coordinator | Controls the distributed workflow. |
| Participant | Performs an operation or votes on a transaction. |
| Commit decision | Authorizes participants to commit. |
| Abort decision | Directs participants to discard prepared work. |
| Compensation | Performs a new business operation to reverse an earlier effect. |
| Idempotency | Prevents repeated requests from producing duplicate effects. |
| Recovery | Resolves transactions interrupted by failures. |

The coordinator's state and the actual state of individual participants must be treated separately.

A coordinator timeout does not prove that a participant failed to commit.

## 3. Two-Phase Commit

### 3.1 Definition

Two-Phase Commit is a distributed atomic commit protocol designed to coordinate a transaction across multiple participants.

Its objective is to ensure that participants follow one global commit or abort decision.

The protocol contains two phases:

1. Prepare phase.
2. Commit or abort phase.

### 3.2 Architecture

The protocol contains:

- One transaction coordinator.
- Multiple transactional participants.
- A communication mechanism.
- Durable transaction logs.
- A recovery mechanism.

The coordinator collects votes and records the global decision.

Participants prepare their local transactions and retain sufficient information to complete the coordinator's decision.

### 3.3 Prepare Phase

The coordinator sends a PREPARE request to every participant.

Each participant evaluates whether it can commit its local transaction.

A participant can return:

- YES: It successfully prepared the transaction.
- NO: It cannot commit the transaction.

A YES vote means that the participant promises it can commit when instructed.

It does not mean that the business transaction has already been committed.

The participant must preserve the required transactional state until it receives the final decision.

### 3.4 Commit Phase

The coordinator evaluates the collected votes.

| Voting result | Coordinator decision |
|---|---|
| Every participant votes YES | COMMIT |
| At least one participant votes NO | ABORT |
| One or more votes remain unavailable | Wait or enter an unresolved state |

After recording COMMIT, the coordinator broadcasts the commit instruction.

Participants commit their local transactions and acknowledge completion.

If the coordinator decides ABORT, participants discard their prepared work.

### 3.5 Protocol Flow

    Coordinator
         |
         | PREPARE
         |
         +----------> Participant A
         +----------> Participant B
         +----------> Participant C
         |
         | Collect votes
         |
         +<---------- YES
         +<---------- YES
         +<---------- YES
         |
         | Durable COMMIT decision
         |
         +----------> COMMIT A
         +----------> COMMIT B
         +----------> COMMIT C
         |
         | Collect acknowledgements
         |
         +<---------- ACK
         +<---------- ACK
         +<---------- ACK
         |
         v
       COMMITTED

### 3.6 Blocking Behavior

A major limitation of conventional 2PC is blocking.

Suppose all participants vote YES, but the coordinator fails before participants receive the decision.

The participants may remain prepared while waiting for recovery information.

Prepared participants cannot independently decide to abort safely because the coordinator might already have recorded COMMIT.

The transaction therefore requires coordinator recovery and durable decision records.

### 3.7 Uncertain Commit Outcomes

Consider three participants:

| Participant | State |
|---|---|
| Inventory | COMMITTED |
| Payment | PREPARED |
| Order | COMMITTED |

The coordinator has already decided COMMIT.

Payment has not acknowledged the decision.

The correct state is not a successful global completion. It is an unresolved or in-doubt transaction.

The coordinator must recover its durable decision and retry delivery to Payment.

It must not issue a contradictory abort instruction.

### 3.8 Operational Characteristics

- Provides atomic commit semantics under the protocol's assumptions.
- Requires coordination and durable participant state.
- Can hold transactional resources while waiting.
- Requires reliable recovery.
- Can increase latency because of multiple communication rounds.
- May reduce availability during coordinator failures.

2PC is appropriate when atomic commitment across participating resources is a strict requirement and the infrastructure supports the protocol.

## 4. Saga Pattern

### 4.1 Definition

A Saga is a sequence of independent local transactions.

Each successful step commits locally.

If a later step fails, the coordinator executes compensating transactions for previously completed steps.

Unlike 2PC, a saga does not require every participant to hold a prepared transaction until a global decision.

### 4.2 Business Scenario

Consider an order-processing workflow:

| Order | Operation | Compensation |
|---|---|---|
| 1 | Reserve inventory | Release inventory |
| 2 | Capture payment | Refund payment |
| 3 | Create shipment | Cancel shipment |
| 4 | Notify customer | Send cancellation notification |

If shipment creation fails, the coordinator can request a refund and release the inventory reservation.

These operations are new business transactions.

They are not database rollbacks.

### 4.3 Saga Architecture

A saga consists of:

- A coordinator or choreography mechanism.
- Local transactions.
- Ordered business steps.
- Compensating operations.
- Persistent workflow state.
- Retry and recovery mechanisms.

Two implementation styles are common.

**Orchestration**

A central coordinator determines which step executes next and which compensation must follow a failure.

**Choreography**

Services communicate through events and independently determine their next actions.

### 4.4 Orchestration Flow

    Start
      |
      v
    Reserve Inventory
      |
      v
    Capture Payment
      |
      v
    Create Shipment
      |
      +---- Success ----> Complete
      |
      +---- Failure
                |
                v
          Refund Payment
                |
                v
          Release Inventory
                |
                v
          Compensated

Compensation generally proceeds in reverse order of successful execution because later operations may depend on earlier operations.

### 4.5 Compensation Semantics

Compensation does not necessarily restore the exact historical state.

For example:

- A payment refund can incur processing fees.
- A notification cannot be unsent.
- A shipment cancellation may be rejected after dispatch.
- A reserved product may already have been allocated elsewhere.

Consequently, compensation is a business-level recovery mechanism rather than a guarantee of perfect rollback.

### 4.6 Saga Failure States

| State | Meaning |
|---|---|
| CREATED | Workflow initialized. |
| EXECUTING | A local transaction is running. |
| COMMITTED | All required steps succeeded. |
| COMPENSATING | Previously completed operations are being reversed. |
| COMPENSATED | Required compensations succeeded. |
| FAILED | Execution or compensation requires intervention. |

A compensation failure must remain visible.

Silently marking a partially compensated saga as successful creates inconsistent business records.

### 4.7 Reliability Mechanisms

A production saga should implement:

- Durable workflow state.
- Idempotent execution.
- Idempotent compensation.
- Retry limits.
- Exponential backoff.
- Dead-letter handling.
- Timeouts.
- Correlation identifiers.
- Transactional outbox.
- Monitoring and manual recovery.

A retry must not create duplicate payments, duplicate reservations, or multiple shipments.

## 5. Two-Phase Commit Versus Sagas

The two patterns solve related problems but provide different consistency and availability trade-offs.

| Dimension | Two-Phase Commit | Saga |
|---|---|---|
| Coordination | Central transaction coordinator | Orchestrator or event choreography |
| Atomicity | Distributed atomic commit | Sequence of local commits |
| Transaction duration | Can hold prepared resources | Local transactions commit independently |
| Rollback | Abort before global commit | Business compensation |
| Consistency | Atomic commit semantics | Eventual business consistency |
| Blocking | Can block during coordinator failures | Does not require prepared participants |
| Compensation | Not the normal rollback mechanism | Core recovery mechanism |
| Failure recovery | Durable decision and participant recovery | Retry and compensation |
| Availability | Can be reduced by coordination failures | Usually better operational flexibility |
| Complexity | Distributed transaction protocol | Distributed workflow management |

### 5.1 Choosing Between Them

Use 2PC when:

- A global atomic commit is mandatory.
- Participants support the required transactional protocol.
- Resource locking and blocking are acceptable.
- Recovery infrastructure is available.

Use sagas when:

- Services own independent databases.
- Business processes involve multiple local transactions.
- Long-running workflows are involved.
- Eventual consistency is acceptable.
- Business compensation is practical.

The choice depends on business invariants, failure semantics, participant capabilities, and operational requirements.

## 6. Python Implementation

**File perspective:** `distributed_transactions.py`

The Python implementation provides a transaction simulation framework.

### 6.1 Domain Modeling

The implementation defines:

- `Participant`
- `DistributedTransaction`
- `TransactionLog`
- `TransactionFactory`
- `TransactionState`
- `ParticipantState`
- `TransactionMode`

Enumerations prevent arbitrary transaction-state strings from being used throughout the implementation.

Dataclasses represent structured audit events and transaction logs.

### 6.2 Two-Phase Commit Implementation

`execute_2pc()` implements:

1. Transaction initialization.
2. Prepare requests.
3. YES and NO voting.
4. Prepare rejection handling.
5. Coordinator decision.
6. Commit requests.
7. Commit acknowledgement recording.
8. Uncertain commit handling.

A participant that rejects preparation causes the coordinator to abort the transaction.

A participant that fails during commit after the global commit decision produces an `IN_DOUBT` state.

This distinction is essential because committed participants cannot safely be rolled back through an ordinary abort.

### 6.3 Saga Implementation

`execute_saga()` performs local transactions sequentially.

Successfully completed participants are maintained in an ordered collection.

If an operation fails, compensation runs in reverse order.

The implementation distinguishes:

- Successful saga completion.
- Successful compensation.
- Failed compensation.

### 6.4 Validation and Testing

The script checks:

- Empty participant lists.
- Duplicate participant names.
- Invalid participant states.
- Repeated transaction execution.
- Prepare rejection.
- Commit failures.
- Saga execution failures.

Assertions verify expected transaction outcomes.

### 6.5 Performance Considerations

The implementation uses lists for ordered participants and audit records.

Saga compensation requires reverse traversal, giving linear time complexity relative to the number of completed participants.

For \(n\) participants:

- Prepare processing: \(O(n)\).
- Commit processing: \(O(n)\).
- Saga execution: \(O(n)\).
- Compensation: \(O(n)\).
- Audit storage: \(O(e)\), where \(e\) is the number of events.

The simulation uses in-memory state. Production deployments require durable persistence and distributed messaging.

## 7. JavaScript Implementation

**File perspective:** `distributed-transactions.js`

The JavaScript implementation focuses on asynchronous service coordination and event-driven transaction monitoring.

### 7.1 Event-Driven Architecture

`DistributedTransaction` extends Node.js `EventEmitter`.

It exposes events such as:

- `stateChange`
- `stepCompleted`

External observers can monitor transaction progress without coupling themselves to the internal execution logic.

### 7.2 Asynchronous Participants

Each `TransactionParticipant` accepts asynchronous handlers.

These represent service operations such as:

- Prepare.
- Commit.
- Abort.
- Execute.
- Compensate.

Promises allow the coordinator to work with remote service calls.

### 7.3 Parallel Preparation

The 2PC implementation uses `Promise.all()` to collect participant votes concurrently.

It records each participant's outcome and determines whether all participants accepted preparation.

`Promise.allSettled()` is used during commit and abort processing so that one rejected operation does not prevent the coordinator from observing the other outcomes.

This is important for distributed failure handling.

### 7.4 Event-Based Monitoring

The audit service records:

- Transaction identifiers.
- Participant identifiers.
- Action names.
- Structured metadata.
- Timestamps.

State-change listeners can connect monitoring and reporting components to the transaction lifecycle.

### 7.5 Saga Execution

The saga executes local operations sequentially.

If a step fails, completed operations are compensated in reverse order.

Compensation failures are recorded separately rather than being hidden by the original failure.

### 7.6 JavaScript Engineering Considerations

- Promises represent asynchronous operations.
- EventEmitter supports decoupled monitoring.
- Sets track executed and compensated transaction identifiers.
- Immutable event objects protect recorded audit entries.
- Structured errors distinguish transaction failures.
- `Promise.allSettled()` preserves visibility into partial failures.

The implementation is a single-process simulation. Production deployments need persistent idempotency records, durable orchestration, network timeouts, and message recovery.

## 8. C++17 Implementation

**File perspective:** `distributed_transactions.cpp`

The C++ implementation emphasizes explicit domain modeling, deterministic state transitions, and resource-conscious execution.

### 8.1 Domain Types

The implementation defines:

- `Participant`
- `DistributedTransaction`
- `AuditLog`
- `AuditEvent`
- `TransactionMode`
- `TransactionState`
- `ParticipantState`

Enums represent valid protocol states.

The participant class encapsulates its internal state and exposes controlled operations.

### 8.2 Governance of Commit Decisions

The coordinator validates participant responses before issuing the global decision.

A successful prepare phase requires every participant to vote YES.

If a participant rejects preparation, the coordinator issues abort requests.

During commit, a failure produces `IN_DOUBT` rather than an incorrect rollback.

### 8.3 Saga Processing

Completed participant indexes are stored in a vector.

Reverse iterators perform compensation in reverse execution order.

This preserves dependencies between business operations.

The implementation separately handles compensation failures.

### 8.4 Data Structures

| Structure | Purpose |
|---|---|
| `vector` | Maintains ordered participants and audit records. |
| `map` | Maps enumerated states to readable representations. |
| `set` | Supports uniqueness validation. |
| `exception` | Provides structured failure handling. |

### 8.5 Complexity

For \(n\) participants:

- Participant validation: \(O(n \log n)\) using an ordered set.
- Prepare phase: \(O(n)\).
- Commit phase: \(O(n)\).
- Saga execution: \(O(n)\).
- Reverse compensation: \(O(n)\).
- Reporting: \(O(n + e)\).

The implementation avoids unnecessary dynamic data structures and external dependencies.

### 8.6 Engineering Limitations

The program models coordinator decisions in memory.

It does not implement:

- Durable transaction logs.
- Network communication.
- Distributed locking.
- Concurrent coordinator recovery.
- Database-level prepared transactions.

These are necessary components of a production-grade distributed transaction system.

## 9. Java 17 Implementation

**File perspective:** `DistributedTransactions.java`

The Java implementation presents an enterprise-oriented transaction coordination model.

### 9.1 Domain Architecture

The implementation separates responsibilities through:

- `TransactionParticipant` interface.
- `ServiceParticipant` implementation.
- `TransactionCoordinator`.
- `TransactionPolicy`.
- `AuditService`.

Records represent immutable transaction events and participant results.

Enums provide explicit transaction and participant states.

### 9.2 Policy Validation

`TransactionPolicy` validates:

- Minimum participant count.
- Unique participant names.
- Whether every participant must vote YES.

The coordinator delegates validation to the policy object instead of embedding all rules directly into transaction execution.

### 9.3 Interface-Based Participant Design

The `TransactionParticipant` interface defines the contract that each participating service must implement.

This separates coordination logic from individual service behavior.

Different services can provide their own local transaction and compensation implementations while following the same contract.

### 9.4 Enterprise State Management

The coordinator performs explicit state transitions.

The audit service records previous and new states.

The implementation distinguishes:

- Preparation failure.
- Commit failure.
- Successful commit.
- Uncertain distributed outcome.
- Saga execution failure.
- Compensation failure.

### 9.5 Idempotency

Participant-level sets track transaction identifiers associated with execution and compensation.

This prevents repeated operations within the same in-memory participant instance.

Production idempotency must be persisted because application restarts destroy in-memory tracking information.

### 9.6 Java Engineering Considerations

The implementation uses:

- Java 17 records.
- Interfaces.
- Enums.
- Immutable collection snapshots.
- Generics through Java collections.
- Streams for policy evaluation.
- Custom exceptions.
- Supplier and Runnable functional interfaces.
- Service-oriented domain separation.

The design supports extension toward persistent transaction coordinators and remote participant adapters.

## 10. PostgreSQL Implementation

**File perspective:** `distributed_transactions.sql`

The PostgreSQL implementation models the relational structure required for transaction coordination and operational reporting.

### 10.1 Database Architecture

The `distributed_tx` schema contains the following primary tables:

| Table | Responsibility |
|---|---|
| `services` | Registered participating services. |
| `distributed_transactions` | Coordinator-level transaction records. |
| `transaction_participants` | Participant state and voting information. |
| `saga_steps` | Ordered saga operations and compensation states. |
| `transaction_decisions` | Durable coordinator decisions. |
| `transaction_events` | Transaction audit history. |

### 10.2 Referential Integrity

Foreign keys connect participants to transactions and registered services.

Saga steps reference their associated participants.

Audit events reference the transaction and, where applicable, the participant.

Unique constraints prevent duplicate transaction references, idempotency keys, participant registrations, and execution orders.

Check constraints enforce valid business values.

### 10.3 Two-Phase Commit Workflow

The SQL implementation separates the protocol into functions.

| Function | Responsibility |
|---|---|
| `create_transaction()` | Creates an idempotent transaction record. |
| `register_participant()` | Registers a valid service participant. |
| `prepare_transaction()` | Records a participant's vote. |
| `decide_2pc()` | Determines the global commit or abort decision. |
| `acknowledge_commit()` | Records participant commit acknowledgement. |
| `finalize_2pc()` | Determines the final coordinator state. |

The coordinator decision is recorded in `transaction_decisions`.

The implementation distinguishes a durable decision from participant acknowledgement.

A transaction whose commit decision exists but whose participants have not all acknowledged completion remains unresolved.

### 10.4 Saga Workflow

The saga implementation uses:

- `saga_steps`
- `execute_saga_step()`
- `compensate_saga_step()`
- `finalize_saga()`

Each step has its own state, execution timestamp, compensation timestamp, retry count, and error information.

Compensation checks execution order to prevent an earlier operation from being compensated while a later operation remains uncompensated.

### 10.5 Database Integrity

The implementation uses:

- Primary keys.
- Foreign keys.
- Unique constraints.
- Check constraints.
- State-validation triggers.
- Transactional functions.
- JSONB payloads.
- Indexes for operational queries.

The state-validation triggers prevent terminal transaction states from being changed and prevent mixing incompatible 2PC and saga states.

### 10.6 Recovery and Reporting

The database provides reporting views.

`transaction_overview` displays participant counts, voting results, and transaction states.

`transaction_recovery_queue` identifies unresolved transactions requiring operational attention.

`saga_compensation_report` measures completed operations, compensation results, and retries.

The reporting queries also identify outstanding votes and inconsistencies between transaction-level and participant-level states.

### 10.7 Performance Considerations

Indexes target common operational access patterns:

- Transaction state.
- Transaction mode and state.
- Participant state.
- Transaction audit history.
- Service relationships.
- Saga execution state.
- JSONB payload searches.

Composite indexes support transaction-level recovery and monitoring.

The database design avoids repeatedly scanning the complete transaction history for common recovery queries.

## 11. Failure Handling and Recovery

Distributed transaction failures can occur at multiple stages.

| Failure | 2PC response | Saga response |
|---|---|---|
| Participant rejects request | Abort decision | Stop workflow |
| Participant unavailable during preparation | Wait, timeout, or abort according to protocol | Retry or fail step |
| Coordinator crashes | Recover durable decision | Recover workflow state |
| Commit acknowledgement lost | Retry commit delivery | Not applicable as a global commit |
| Local transaction fails | Follow global decision | Start compensation |
| Compensation fails | Not the normal 2PC mechanism | Retry and escalate |
| Duplicate message | Idempotent participant processing | Idempotent step processing |
| Network timeout | Outcome may be uncertain | Outcome may be uncertain |

### 11.1 Durable Recovery

A production coordinator must persist its transaction state before communicating a final decision.

For 2PC, the global decision must be durable before commit instructions are sent.

For sagas, each completed local transaction and its workflow progress must be recorded durably.

Recovery workers can then identify interrupted transactions and resume the appropriate operation.

### 11.2 Transactional Outbox

The transactional outbox pattern addresses the dual-write problem.

Suppose a service updates its local database and then publishes an event.

If the database commit succeeds but event publication fails, other services never receive the event.

The outbox pattern writes the business update and an outgoing event record within the same local database transaction.

A separate publisher delivers the recorded event.

Consumers use message identifiers and idempotency checks to avoid duplicate effects.

### 11.3 Idempotency

An idempotent operation produces the same effective business result when the same logical request is repeated.

For example, processing the same payment-capture command twice should not charge the customer twice.

A reliable implementation typically stores:

- Idempotency key.
- Request identity or payload hash.
- Processing status.
- Result reference.
- Completion timestamp.

The key must be unique within its intended business scope.

## 12. Security and Operational Governance

Distributed transaction systems exchange commands, decisions, and business data across service boundaries.

Important controls include:

- Authenticated service-to-service communication.
- Authorization for coordinator operations.
- Restricted database privileges.
- Protected transaction identifiers.
- Secure transport.
- Input validation.
- Audit retention.
- Sensitive payload encryption.
- Rate limiting.
- Duplicate-message protection.
- Operational monitoring.

Coordinator decisions should not be directly modifiable by ordinary participant credentials.

Participants should only acknowledge operations belonging to transactions for which they are registered.

Sensitive payment information should not be copied into unrestricted audit metadata.

## 13. Performance and Scalability

### Two-Phase Commit

2PC performance is influenced by:

- Number of participants.
- Network latency.
- Participant preparation time.
- Lock duration.
- Coordinator availability.
- Recovery frequency.

Parallel preparation can reduce the time required to collect votes, but the protocol still requires coordination and participant readiness.

### Sagas

Saga performance is influenced by:

- Number of workflow steps.
- Dependency relationships.
- Local transaction latency.
- Message delivery delays.
- Retry frequency.
- Compensation complexity.

Independent saga steps may execute concurrently when business dependencies permit.

Sequential workflows remain appropriate when later operations depend on earlier results.

### Comparative Operational Trade-Offs

| Factor | 2PC | Saga |
|---|---|---|
| Resource locking | Potentially long-lived | Usually limited to local transactions |
| Global coordination | Required | Required for orchestration, optional centralization in choreography |
| Failure recovery | Decision-based | Workflow and compensation-based |
| Business reversibility | Not required for normal abort | Requires compensating operations |
| Monitoring | Votes and acknowledgements | Steps, retries, and compensations |
| Long-running processes | Less suitable | Well suited |

## 14. Testing Scenarios

The implementations exercise the following scenarios.

| Scenario | Expected behavior |
|---|---|
| Every 2PC participant votes YES | COMMITTED |
| One 2PC participant votes NO | ABORTED |
| Commit acknowledgement unavailable | IN_DOUBT |
| Every saga step succeeds | COMMITTED |
| Final saga step fails | Earlier steps compensated |
| Compensation succeeds | COMPENSATED |
| Compensation fails | FAILED |
| Duplicate participant registration | Rejected |
| Invalid transaction mode | Rejected |
| Repeated idempotent creation request | Existing transaction returned |

These scenarios cover the major coordination and failure-handling distinctions.

## 15. Important Implementation Limitations

The five implementations are executable learning models rather than production distributed transaction platforms.

The Python, JavaScript, C++17, and Java 17 implementations maintain participant and coordinator state in process memory.

The PostgreSQL implementation persists application-level transaction states and provides relational coordination operations.

The following capabilities require additional production infrastructure:

- Network communication between independent services.
- Durable message brokers.
- Distributed leader election.
- Coordinator failover.
- Persistent retry scheduling.
- Transactional outbox publishers.
- Dead-letter queues.
- Distributed tracing.
- Authentication and authorization integration.
- Operational alerting.
- Concurrency control across independent coordinators.
- Native database-level distributed commit integration.

The PostgreSQL schema models application-level 2PC decisions. It does not execute native PostgreSQL prepared transactions across independent database instances.

The implementations also assume that compensation operations are defined by the business domain. Some real-world operations cannot be perfectly reversed.

These limitations distinguish protocol simulation and workflow modeling from a complete production distributed transaction infrastructure.
