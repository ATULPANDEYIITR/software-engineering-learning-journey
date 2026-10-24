## Scope

A database transaction is a logical unit of work whose operations are treated as one controlled state transition.

This project models four central transaction mechanisms:

| Mechanism | Role |
|---|---|
| Atomicity | Ensures a transaction is applied completely or not applied at all |
| Consistency | Preserves declared data and business invariants |
| Isolation | Controls how concurrent transactions observe and affect one another |
| Durability | Ensures committed changes survive beyond the transaction |
| Commit | Makes the transaction's successful changes permanent |
| Rollback | Discards changes that must not become permanent |

The implementations deliberately use different engineering perspectives.

| File | Perspective |
|---|---|
| Python | In-memory transaction manager with staged writes and optimistic conflict detection |
| JavaScript | Event-driven transaction model using transaction lifecycle events |
| C++17 | Transaction engine using explicit state, version validation, and staged writes |
| Java 17 | Enterprise-oriented service model with domain types and explicit transaction policies |
| PostgreSQL | Relational transaction model using constraints, triggers, MVCC-compatible isolation, savepoints, and transactional DML |

The central workflow is:

`Begin → Read → Validate → Stage Changes → Commit`

or, when validation fails:

`Begin → Read → Stage Changes → Rollback`

A concurrent conflict can instead produce:

`Begin → Read → Concurrent Change → Commit Validation → Conflict → Rollback`

---

## Transaction Fundamentals

A transaction groups multiple database operations into one logical unit.

Consider a transfer of 250 from Alice to Bob:

1. Read Alice's balance.
2. Verify that Alice has sufficient funds.
3. Reduce Alice's balance by 250.
4. Increase Bob's balance by 250.
5. Commit both changes.

The two balance changes are logically dependent. Applying only one would create an invalid state.

A transaction therefore separates two concepts:

- **Working state**: changes being prepared by the transaction.
- **Committed state**: changes accepted as durable database state.

A rollback removes the transaction's uncommitted work.

A commit makes the transaction's successful work visible according to the database's concurrency and durability rules.

---

## ACID Properties

### Atomicity

Atomicity means that the transaction behaves as one unit.

For a transfer:

`Alice - 250` and `Bob + 250`

must succeed together.

If the withdrawal succeeds but the deposit fails, the transaction must not leave the database in that intermediate state.

The Python, JavaScript, C++17, and Java 17 implementations represent this by keeping writes in transaction-local structures until commit validation succeeds.

The PostgreSQL implementation uses actual database transactions with `BEGIN`, `COMMIT`, and `ROLLBACK`.

### Consistency

Consistency means that a committed transaction preserves all applicable integrity rules.

Examples include:

- account balances cannot be negative
- referenced accounts must exist
- transaction amounts must be positive
- transaction states must be valid
- ledger entries must satisfy their structural constraints
- a transfer must balance its debit and credit entries

Consistency is not simply another word for correctness of application code. Database constraints provide an enforcement layer independent of the calling application.

The PostgreSQL model therefore uses:

- primary keys
- foreign keys
- unique constraints
- check constraints
- indexes
- triggers

### Isolation

Isolation controls the interaction between concurrent transactions.

The four commonly exposed isolation levels are:

| Level | Main characteristic |
|---|---|
| Read Uncommitted | Allows the weakest visibility guarantees; PostgreSQL treats this as Read Committed |
| Read Committed | Statements observe committed data using statement-level snapshots |
| Repeatable Read | A transaction retains a stable view of data for its snapshot |
| Serializable | Provides the strongest standard isolation guarantee by preventing non-serializable committed outcomes |

Isolation is concerned with concurrency. It is different from atomicity.

Atomicity asks:

> Is this transaction applied as one unit?

Isolation asks:

> What can this transaction observe while other transactions execute?

### Durability

Durability means that after a successful commit, the committed result is expected to survive failures according to the database's durability configuration.

The in-memory implementations simulate transaction state but cannot provide physical storage durability.

PostgreSQL provides the real database durability mechanisms through its storage and write-ahead logging architecture.

Therefore, a software simulation can model the transaction lifecycle but cannot reproduce the full crash-recovery guarantees of a production database.

---

## Commit

Commit is the transition from an active transaction to a successful completed transaction.

The general model is:

`ACTIVE → COMMITTED`

Before the commit becomes successful, the implementation can validate:

- transaction state
- data versions
- balance constraints
- business rules
- concurrency conflicts

The Python implementation performs optimistic validation against account versions.

The C++ implementation separates validation from publication of staged writes.

The Java implementation places commit behavior inside a service that owns transaction validation.

The JavaScript implementation emits a commit event after successful validation and publication.

PostgreSQL uses `COMMIT` to complete a database transaction.

A committed transaction cannot logically be reopened and modified as though it were still active.

---

## Rollback

Rollback transitions an active transaction into a cancelled state:

`ACTIVE → ROLLED_BACK`

Rollback removes changes that have not been committed.

Typical rollback causes include:

- insufficient funds
- validation failure
- constraint violation
- application exception
- detected concurrency conflict
- explicit cancellation
- serialization failure

The implementations clear staged writes during rollback.

PostgreSQL also supports savepoints, which provide partial rollback inside a larger transaction.

The PostgreSQL example demonstrates:

`BEGIN → operation → SAVEPOINT → failed operation → ROLLBACK TO SAVEPOINT → COMMIT`

This differs from a complete transaction rollback because work performed before the savepoint remains available.

---

## Transaction State Model

The implementations use an explicit lifecycle:

    +-------------+
    |    ACTIVE   |
    +------+------+
           |
     +-----+-----+
     |           |
   COMMIT     ROLLBACK
     |           |
     v           v
+------------+ +--------------+
| COMMITTED  | | ROLLED BACK  |
+------------+ +--------------+

Terminal states cannot return to `ACTIVE`.

This prevents invalid operations such as:

- committing a transaction twice
- rolling back a committed transaction
- modifying a rolled-back transaction
- modifying a committed transaction

The explicit state model is implemented in the Python, JavaScript, C++17, and Java 17 source files.

---

## Isolation and Concurrency

Isolation becomes important when multiple transactions operate on the same data.

Suppose two transactions read the same account balance.

    Transaction A                    Transaction B

    Read balance = 1000
                                     Read balance = 1000
    Prepare balance = 900
                                     Prepare balance = 800
    Commit
                                     Commit

If both commits blindly overwrite the same account, one logical update can be lost.

The project addresses this with version-based conflict detection in the application-level implementations.

Each account has a version.

    Account
    ├── balance
    └── version

A transaction records the version it observed.

At commit time:

    observed version == current version
            |
           yes
            |
       publish writes

    observed version != current version
            |
           no
            |
         conflict
            |
         rollback

This is an optimistic concurrency strategy.

It is useful when conflicts are relatively uncommon because transactions do not have to acquire exclusive locks for every read.

A high-conflict workload may require a different strategy, such as stronger database locking or retry policies.

---

## Isolation Levels

### Read Uncommitted

Read Uncommitted provides the weakest isolation semantics in systems that implement it distinctly.

PostgreSQL does not provide dirty reads. A request for Read Uncommitted is effectively treated as Read Committed.

The project therefore treats this level as a conceptual isolation boundary rather than attempting to simulate dirty reads in the application model.

### Read Committed

Read Committed is PostgreSQL's default isolation level.

A statement sees data committed before that statement's snapshot was established.

This means two statements within the same transaction can observe different committed database states when other transactions commit between them.

This behavior is appropriate for many ordinary transactional workloads.

### Repeatable Read

Repeatable Read provides a stable transaction snapshot in PostgreSQL.

A transaction that reads a row does not simply receive an arbitrary later version of that row on subsequent reads.

Concurrent modification can cause a transaction to fail rather than silently produce a result that violates the isolation guarantee.

### Serializable

Serializable provides the strongest standard isolation level.

The objective is that successful concurrent transactions behave as though they had executed in some serial order.

Serializable execution can therefore reject transactions that cannot be safely serialized.

Applications using Serializable isolation need appropriate retry handling for serialization failures.

---

## Python Implementation

The Python file defines:

- `Account`
- `Transaction`
- `TransactionManager`
- `TransactionState`
- `IsolationLevel`
- transaction-specific exceptions

`Transaction.writes` stores changes before commit.

`Transaction.read_versions` stores versions observed by the transaction.

The transaction manager validates these versions before applying changes.

The transfer operation reads both accounts before staging the withdrawal and deposit.

This allows the implementation to enforce a key invariant:

`sum(account balances) remains constant for a pure transfer`

The Python implementation also checks that no account becomes negative.

The implementation uses `RLock` around shared in-memory state. This protects the manager's shared structures when operations are invoked concurrently within the same process.

The model is deliberately not presented as a replacement for a production database. It demonstrates transaction mechanics while leaving physical durability to a real storage engine.

---

## JavaScript Implementation

The JavaScript implementation uses Node.js standard-library `EventEmitter`.

The transaction lifecycle emits:

- `begin`
- `commit`
- `rollback`

This provides an event-driven representation of transaction state changes.

JavaScript `Map` objects represent:

- accounts
- transaction read versions
- staged writes
- repeatable-read values

The event-driven model is useful for connecting transaction lifecycle events to logging, monitoring, metrics, or audit processing.

The source avoids external npm dependencies.

Its asynchronous `main` function establishes a structure suitable for integration with asynchronous application services even though the in-memory operations themselves are synchronous.

---

## C++17 Implementation

The C++ implementation models the transaction engine using explicit domain structures.

Important types include:

- `Account`
- `Transaction`
- `TransactionManager`
- `IsolationLevel`
- `TransactionState`
- `ConflictException`

`std::map` stores accounts in deterministic identifier order.

`std::unordered_map` stores transaction-local read versions and pending writes.

The commit operation has two conceptual phases:

1. Validate versions and staged values.
2. Publish the writes and increment account versions.

The separation is important because publishing a subset of invalid transaction writes would violate atomicity.

The program uses C++ exceptions for invalid state transitions, invalid balances, insufficient funds, and concurrency conflicts.

---

## Java 17 Implementation

The Java implementation uses an enterprise-oriented service structure.

`RepositoryService` owns transaction operations and account state.

The model uses:

- enums for isolation and transaction state
- domain classes for accounts and transactions
- maps for transaction-local state
- custom exceptions for transaction failures
- explicit state transitions
- stream-based aggregation for total balances

The service boundary makes transaction behavior easier to separate from callers.

The Java implementation also exposes an immutable balance view through `Collections.unmodifiableMap`.

This prevents callers from bypassing the service and directly modifying the returned balance collection.

---

## PostgreSQL Implementation

The PostgreSQL script represents transaction processing using actual relational structures.

### Accounts

The `accounts` table stores:

- account identifier
- owner
- balance
- version
- creation time

The balance and version columns have database-level checks.

### Transaction Records

`ledger_transactions` stores:

- transaction type
- transaction reference
- status
- isolation level
- start time
- commit time

The status constraint restricts transactions to:

- `ACTIVE`
- `COMMITTED`
- `ROLLED_BACK`

A trigger prevents committed or rolled-back transactions from being moved back into another state.

### Transaction Entries

`transaction_entries` connects transactions to accounts.

Each entry records:

- debit or credit
- positive amount
- related transaction
- related account

Foreign keys prevent entries from referencing nonexistent resources.

### Transaction Events

`transaction_events` provides an audit-oriented event stream.

Events can represent:

- commit
- rollback
- validation
- other transaction lifecycle decisions

The JSONB details field allows structured event metadata without changing the table for every event attribute.

---

## Constraints and Database-Level Consistency

The PostgreSQL implementation demonstrates several layers of enforcement.

### Primary Keys

Primary keys uniquely identify:

- accounts
- transactions
- entries
- events
- customers

### Foreign Keys

Foreign keys connect transaction records to their dependent resources.

For example:

`transaction_entries.transaction_id`

references:

`ledger_transactions.transaction_id`

This prevents orphaned ledger entries.

### Check Constraints

Examples include:

- non-negative account balances
- positive transaction-entry amounts
- valid transaction states
- valid transaction types
- valid isolation-level names

### Unique Constraints

Transaction references and customer names demonstrate uniqueness requirements.

### Trigger Enforcement

The transaction-status trigger prevents invalid state transitions.

This matters because application-level validation alone can be bypassed by another database client.

---

## Savepoints

A savepoint is a transaction-local recovery point.

The PostgreSQL example uses:

`SAVEPOINT before_invalid_operation`

A later failure can be handled with:

`ROLLBACK TO SAVEPOINT before_invalid_operation`

This does not terminate the whole transaction.

The distinction is:

| Operation | Effect |
|---|---|
| `ROLLBACK` | Cancels the complete current transaction |
| `ROLLBACK TO SAVEPOINT` | Cancels work performed after a specific savepoint |
| `COMMIT` | Makes the remaining transaction successful |

Savepoints are useful when an application can recover from a partial operation without discarding the entire unit of work.

---

## Transactional Failure Scenarios

### Insufficient Funds

A withdrawal must not produce a negative account balance.

The application implementations reject the operation before commit.

The PostgreSQL model uses a balance condition when updating the source account.

### Invalid Transaction State

A transaction that is already committed or rolled back cannot be reused.

The source implementations explicitly check transaction state.

### Concurrent Modification

If an account version changes after a transaction reads it, the application-level models reject the commit.

The transaction must be retried using current state.

### Constraint Violation

PostgreSQL constraints provide a second line of protection even when application validation is incorrect.

### Serialization Failure

At Serializable isolation, PostgreSQL can reject a transaction that cannot safely participate in a serializable execution.

A production application should treat such failures as retryable when the operation is designed to be safely repeated.

---

## Performance Considerations

Transaction performance depends on more than the number of SQL statements.

Important factors include:

- transaction duration
- lock duration
- contention
- number of rows modified
- index maintenance
- isolation level
- transaction retry rate
- disk and WAL activity
- network round trips

Long transactions generally increase the period during which resources and snapshots remain active.

Short transactions reduce the amount of work held in an unfinished state.

Indexes improve lookup performance but introduce write-maintenance overhead.

The PostgreSQL script therefore creates indexes on transaction identifiers and account-related transaction entries where they directly support expected access patterns.

Application-level version validation has approximately linear validation cost in the size of the transaction's read set.

---

## Security Considerations

Transactions do not automatically make an application secure.

A secure transactional system should also consider:

- authorization before modifying an account
- authentication of the caller
- least-privilege database roles
- protection of transaction identifiers
- audit logging
- input validation
- prevention of SQL injection
- appropriate error reporting
- protection against replayed financial operations
- idempotency where requests can be retried

A transaction can preserve atomicity while still performing an unauthorized operation.

Authorization and transaction integrity are separate security concerns.

---

## Durability and Recovery

The in-memory Python, JavaScript, C++17, and Java 17 programs cannot provide physical durability because their primary state exists in process memory.

If the process terminates, that state disappears.

A production database uses persistent storage and recovery mechanisms to make committed transactions durable.

PostgreSQL uses write-ahead logging and crash-recovery mechanisms to recover committed and uncommitted database activity according to its configured durability guarantees.

The distinction is important:

    Application transaction model
            |
            v
    Logical state transition
            |
            v
    Database transaction engine
            |
            v
    Persistent storage + recovery

A complete production system requires all three layers.

---

## Practical Transaction Workflow

A robust transactional operation can be organized as follows:

    Validate request
          |
          v
    Begin transaction
          |
          v
    Read current state
          |
          v
    Check business rules
          |
          v
    Stage or execute changes
          |
          v
    Validate constraints
          |
          +------ failure ------> Rollback
          |
          v
    Commit
          |
          v
    Return successful result

For concurrency-sensitive operations:

    Read state
       |
       v
    Perform work
       |
       v
    Commit validation
       |
       +---- conflict ----> Rollback / Retry
       |
       v
    Commit

---

## Distinguishing the Core Concepts

| Concept | Primary question |
|---|---|
| Transaction | What operations belong to one logical unit of work? |
| Atomicity | Are all changes applied together? |
| Consistency | Does committed state satisfy the required rules? |
| Isolation | What can concurrent transactions observe? |
| Durability | What happens to committed state after failure? |
| Commit | How does successful work become permanent? |
| Rollback | How is unfinished work discarded? |
| Savepoint | How can part of a transaction be undone without cancelling all work? |
| Version validation | Has data changed since this transaction observed it? |
| Serializable isolation | Can concurrent execution produce only serializable outcomes? |

These mechanisms interact, but they are not interchangeable.

---

## Learning Outcomes

The project provides concrete implementations for:

- transaction lifecycle management
- ACID reasoning
- staged writes
- commit validation
- rollback
- optimistic conflict detection
- transaction state transitions
- isolation-level modeling
- database constraints
- database triggers
- savepoints
- transaction reporting
- integrity invariants
- concurrency failure handling

The main distinction is between **logical transaction behavior** and **database-engine transaction guarantees**.

The application implementations model transaction logic in memory.

The PostgreSQL implementation demonstrates mechanisms enforced by a real relational database system.
