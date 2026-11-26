# Consistency Models: Strong, Eventual, and Causal Consistency

## 1. Technical Scope

Consistency models define the guarantees a distributed system provides when multiple clients access or modify replicated data.

A distributed database may maintain several copies of the same logical record across geographically separated nodes. Network latency, temporary partitions, concurrent writes, node failures, and asynchronous replication can cause these copies to contain different values.

A consistency model specifies which observations and ordering relationships clients are permitted to experience.

This project implements three distinct models:

| Model | Primary guarantee | Typical trade-off |
|---|---|---|
| Strong consistency | Reads observe the latest completed write according to the system's defined ordering | Coordination and availability costs |
| Eventual consistency | Replicas converge when updates stop and replication succeeds | Temporary stale reads |
| Causal consistency | Causally related operations are observed in an order that preserves their dependencies | Metadata and dependency tracking |

The implementations use a distributed key-value store as their common domain.

Four programming-language implementations demonstrate different engineering approaches, while the PostgreSQL implementation models the corresponding persistence and operational workflow.

## 2. Distributed Data Replication

### 2.1 Replicas

A replica is an independently maintained copy of application data.

Consider an online retail application operating across three regions:

- Mumbai
- Delhi
- Singapore

Each region maintains a local copy of product information and customer data.

A logical record might be represented as:

| Key | Value |
|---|---|
| `inventory:501` | `{"quantity": 200}` |
| `account:1001` | `{"balance": 50000}` |
| `order:9001` | `{"status": "CREATED"}` |

A write performed in Mumbai may need to become visible in Delhi and Singapore.

The system must determine:

1. When the write is considered committed.
2. Which replicas receive the update.
3. Whether a read can return an older value.
4. How concurrent writes are handled.
5. What happens when a replica becomes unavailable.

### 2.2 Proposed State and Replicated State

A write operation and a replica's stored state are different concepts.

A write event represents a proposed or accepted modification. A replica's state represents the value currently applied at that replica.

For example:

| Replica | Current quantity |
|---|---:|
| Mumbai | 150 |
| Delhi | 200 |
| Singapore | 200 |

The replicas are temporarily inconsistent.

This does not necessarily mean that the system has lost data. It may mean that replication is still in progress.

The distinction is essential when evaluating consistency guarantees.

### 2.3 Write Events

A write event contains information describing a modification.

The implementations use the following attributes:

| Attribute | Purpose |
|---|---|
| Event ID | Unique event identification |
| Key | Modified logical record |
| Value | New data |
| Origin | Replica that accepted the operation |
| Version | Logical ordering information |
| Dependencies | Previously observed causal operations |
| Timestamp | Conflict-resolution metadata |

Event-based replication separates the acceptance of a write from its propagation to other replicas.

## 3. Strong Consistency

### 3.1 Definition

Strong consistency ensures that completed operations are observed according to a globally valid ordering.

In a linearizable system, each operation appears to take effect at a single point between its invocation and completion.

A read initiated after a completed write must observe that write or a later write in the established order.

This guarantee is stronger than merely ensuring that all replicas eventually contain the same value.

### 3.2 Operational Mechanism

A typical strong-consistency operation follows this sequence:

1. A client submits a write.
2. The system validates the request.
3. The coordination mechanism establishes the required commit order.
4. The write is committed according to the configured replication protocol.
5. The operation is acknowledged.
6. Subsequent reads satisfy the required ordering guarantee.

Strong consistency may use leader-based coordination, quorum protocols, consensus, or synchronous replication.

The appropriate mechanism depends on the system architecture.

A single database transaction updating several logical replicas, as demonstrated in this project, is an educational simulation. It is not equivalent to a distributed consensus protocol.

### 3.3 Example: Financial Account

A customer has an account balance of INR 50,000.

Two withdrawal requests attempt to deduct INR 35,000 each.

Without appropriate coordination, both requests might independently observe the same initial balance.

A strong-consistency implementation must serialize or otherwise coordinate the operations so that the balance cannot be incorrectly updated based on stale observations.

The essential requirement is that acknowledged operations obey the system's declared consistency contract.

### 3.4 Advantages and Limitations

Advantages:

- Predictable read-after-write behavior.
- Easier reasoning about shared state.
- Appropriate for operations requiring strict ordering.
- Reduced exposure to stale reads.

Limitations:

- Coordination introduces latency.
- Network partitions can prevent operations from completing.
- Synchronous replication increases dependency on replica availability.
- Geographic distance increases communication costs.

Strong consistency does not automatically provide application-level correctness. Business rules, transaction isolation, authorization, and concurrency controls remain necessary.

## 4. Eventual Consistency

### 4.1 Definition

Eventual consistency guarantees that, if no new updates occur and communication and replication continue successfully, replicas eventually converge to a consistent state.

It does not guarantee that every read immediately returns the latest globally accepted write.

Two replicas may temporarily return different values.

### 4.2 Operational Mechanism

Eventual replication commonly uses asynchronous propagation.

The workflow is:

1. A client submits a write to a local replica.
2. The local replica accepts and applies the write.
3. The event enters a replication queue.
4. Other replicas receive the event.
5. Each replica applies the event according to its conflict-resolution rules.
6. Replication retries continue until the required targets have processed the event.

The origin can accept writes without synchronously waiting for every remote replica.

This improves write responsiveness during normal operation but permits temporary inconsistency.

### 4.3 Example: Product Inventory

A retail platform stores a product's inventory across multiple regional replicas.

A purchase updates the Mumbai replica from 200 units to 175 units.

Before replication:

| Region | Quantity |
|---|---:|
| Mumbai | 175 |
| Delhi | 200 |
| Singapore | 200 |

After successful replication:

| Region | Quantity |
|---|---:|
| Mumbai | 175 |
| Delhi | 175 |
| Singapore | 175 |

The replicas converge.

### 4.4 Conflict Resolution

A conflict occurs when multiple replicas independently modify the same logical record before observing one another's changes.

A common strategy is Last-Writer-Wins (LWW).

The system selects one update using an ordering rule, such as:

- Logical timestamp
- Hybrid logical clock
- Physical timestamp with a deterministic tie-breaker
- Version metadata

The Python, JavaScript, and C++ demonstrations use deterministic timestamp and origin comparisons.

This is a simplified conflict-resolution mechanism.

Physical timestamps can be unreliable because machine clocks may drift or differ. A production system should use an explicitly defined ordering mechanism.

LWW can discard meaningful concurrent updates. It is not appropriate for every application.

Other approaches include:

- Application-specific conflict resolution.
- Operational transformation.
- Conflict-free replicated data types (CRDTs).
- Version-based reconciliation.
- Manual conflict resolution.

### 4.5 Advantages and Limitations

Advantages:

- Lower write latency in many architectures.
- Better tolerance of temporary network interruptions.
- Suitable for geographically distributed applications.
- Supports asynchronous replication.

Limitations:

- Reads may return stale values.
- Concurrent writes require conflict handling.
- Replication queues can accumulate.
- Application logic must tolerate temporary divergence.

Eventual consistency is a convergence guarantee, not a guarantee that every replica will converge automatically regardless of permanent failures or conflicting updates.

## 5. Causal Consistency

### 5.1 Definition

Causal consistency preserves the ordering of causally related operations.

If one operation depends on another, a replica must not expose the dependent operation before the dependency has been observed.

Independent operations do not necessarily require a common global order.

Causal consistency is weaker than linearizability but provides stronger ordering guarantees than unconstrained eventual consistency.

### 5.2 Causal Relationships

Consider an online ordering workflow:

1. A customer creates an order.
2. The payment service receives the order information.
3. The payment service initiates payment.
4. The fulfillment service processes the order.

The payment operation depends on the order creation operation.

The required relationship is:

`Order Created → Payment Initiated → Fulfillment`

A replica must not expose a causally dependent operation while omitting its required predecessor.

Two unrelated customer profile updates may remain concurrent without violating causal consistency.

### 5.3 Happens-Before Relationship

The happens-before relationship represents causal ordering.

Let A and B be operations.

The relationship A → B means that A causally precedes B.

It can arise from:

- Operations performed sequentially by one process.
- Communication between processes.
- Transitive dependencies between previously ordered operations.

If A → B, every replica exposing B must have observed A.

If neither A → B nor B → A, the operations may be concurrent.

### 5.4 Vector Clocks

A vector clock tracks logical progress across participating replicas.

For replicas A, B, and C, a vector might be:

`[2, 1, 0]`

This indicates two observed events from A, one from B, and none from C.

A vector clock supports three important comparisons.

| Relationship | Interpretation |
|---|---|
| X dominates Y | X includes at least all progress represented by Y |
| Y dominates X | Y includes at least all progress represented by X |
| Neither dominates the other | The events are concurrent |

For example:

- X = `[2, 1, 0]`
- Y = `[1, 1, 0]`

X dominates Y.

But:

- X = `[2, 0, 1]`
- Y = `[1, 1, 1]`

Neither dominates the other. The events are concurrent.

Vector clocks provide logical ordering information without depending on synchronized physical clocks.

### 5.5 Dependency Enforcement

A causally consistent replica should apply a dependent event only after its dependencies have been observed.

The project represents dependencies through vector-clock metadata and explicit event relationships.

The general processing rule is:

1. Retrieve the pending event.
2. Examine its dependencies.
3. Determine whether the destination replica has observed them.
4. Apply the event if the dependencies are satisfied.
5. Retain the event in the queue otherwise.
6. Retry when additional events arrive.

This prevents a dependent update from becoming visible prematurely.

### 5.6 Advantages and Limitations

Advantages:

- Preserves meaningful application-level ordering.
- Avoids requiring a single total order for independent operations.
- Supports distributed collaborative workflows.
- Provides a useful compromise between strong and eventual consistency.

Limitations:

- Requires dependency tracking.
- Vector clocks can grow with the number of participants.
- Delayed dependencies can block replication.
- Concurrent updates still require conflict-resolution policies.
- Incorrect dependency propagation can violate the intended guarantee.

## 6. Comparison of the Three Models

| Property | Strong | Eventual | Causal |
|---|---|---|---|
| Immediate global visibility | According to the consistency contract | Not guaranteed | Not guaranteed |
| Stale local reads | Restricted by the contract | Possible | Possible |
| Causal ordering | Preserved | Not inherently guaranteed | Preserved |
| Global total ordering | Available with linearizability | Not required | Not required |
| Replication | Commonly coordinated | Commonly asynchronous | Commonly asynchronous |
| Conflict handling | Controlled by ordering and transaction rules | Required where writes conflict | Required for concurrent writes |
| Metadata overhead | Coordination and version metadata | Replication metadata | Dependency metadata |
| Partition behavior | May reject or delay operations | Can accept local operations under suitable designs | Can accept operations subject to dependency availability |
| Typical application | Financial transactions | Product catalogs and distributed caching | Collaborative workflows |

The CAP theorem provides a related architectural perspective.

During a network partition, a distributed system cannot simultaneously guarantee linearizable consistency and successful availability for every request.

This does not mean that all distributed systems must permanently choose one fixed operating mode. Different operations and data domains may use different consistency guarantees.

## 7. Implementation Architecture

### 7.1 Python: Repository-Style Workflow Simulation

File purpose: standalone simulation of a replicated key-value store.

The Python implementation focuses on domain modeling and explicit state transitions.

Core components:

| Component | Responsibility |
|---|---|
| `ConsistencyModel` | Defines supported consistency modes |
| `VectorClock` | Tracks logical event ordering |
| `WriteEvent` | Represents an accepted modification |
| `Replica` | Maintains local data and pending events |
| `DistributedKeyValueStore` | Coordinates reads, writes, and synchronization |

Important mechanisms:

- Dataclasses provide structured event and replica representations.
- Dictionaries maintain replica state.
- Lists maintain pending replication events.
- An `RLock` serializes operations within the simulation.
- Exceptions distinguish unavailable replicas and causal violations.
- JSON validation restricts stored values to serializable data.

The demonstrations include synchronous strong writes, asynchronous eventual replication, causal event propagation, offline replicas, and validation failures.

The locking mechanism provides process-local synchronization only. It does not coordinate independent machines.

### 7.2 JavaScript: Event-Driven Consistency Engine

File purpose: asynchronous replication and event-driven state management.

The JavaScript implementation emphasizes asynchronous workflows and event notifications.

Core components:

| Component | Responsibility |
|---|---|
| `DistributedStore` | Main orchestration service |
| `Replica` | Local state and replication queue |
| `VectorClock` operations | Logical ordering and dependency comparison |
| `EventEmitter` | Publishes state-change notifications |
| `exclusive()` | Serializes operations within the process |

Events include:

- `write`
- `replication`
- `modeChanged`
- `availabilityChanged`

Promises allow clients to await operations without blocking the entire Node.js event loop.

The implementation also includes a configurable pending-event limit.

The local mutex prevents overlapping state transitions inside the process. It is not a distributed lock or consensus mechanism.

### 7.3 C++17: Lightweight Consistency Engine

File purpose: explicit domain modeling and efficient state management.

The C++ implementation emphasizes STL containers, value types, and predictable memory ownership.

Core components:

| Component | Responsibility |
|---|---|
| `VectorClock` | Logical version comparison |
| `WriteEvent` | Immutable-style event data |
| `Replica` | Local replicated state |
| `DistributedStore` | Write, read, and synchronization operations |
| `optional` | Represents missing records |
| `map` and `unordered_map` | Store metadata and key-value state |

The implementation uses ordered maps for vector-clock components and hash maps for local key-value lookup.

The demonstration covers financial balances, inventory updates, causal order workflows, and offline recovery.

The program uses standard C++17 facilities and requires no external libraries.

### 7.4 Java 17: Enterprise Consistency Architecture

File purpose: policy-driven distributed data management.

The Java implementation separates consistency policy, domain entities, replica state, and service operations.

Core domain types:

| Type | Responsibility |
|---|---|
| `ConsistencyModel` | Defines consistency semantics |
| `ReplicaStatus` | Tracks replica availability |
| `OperationStatus` | Represents operation outcomes |
| `Version` | Immutable vector-clock representation |
| `WriteEvent` | Immutable event record |
| `ConsistencyPolicy` | Defines replication requirements |
| `Replica` | Maintains local state |
| `ConsistencyService` | Enforces policy and coordinates operations |

Java records provide immutable data-transfer objects.

The policy object separates the consistency model from operational requirements such as minimum replica count and whether every replica must be available.

The synchronized service methods provide process-local thread safety.

The model also demonstrates custom exceptions, validation, optional reads, immutable metadata, and structured operation results.

The approval policy type illustrates how reviewer eligibility and approval requirements can be represented as independent domain rules. It is not part of consistency enforcement.

## 8. PostgreSQL Relational Architecture

### 8.1 Schema Design

The SQL implementation uses the `consistency_lab` schema.

Its principal entities are:

| Table | Purpose |
|---|---|
| `replicas` | Registered logical replicas |
| `consistency_policies` | Configured consistency rules |
| `data_items` | Logical records |
| `replica_values` | Values maintained by each replica |
| `write_events` | Accepted modification events |
| `event_clock_components` | Vector-clock components |
| `causal_dependencies` | Explicit dependency relationships |
| `replication_queue` | Pending propagation tasks |
| `consistency_audit` | Operational event history |

### 8.2 Referential Integrity

Primary keys identify entities.

Foreign keys enforce relationships between:

- Replicas and stored values.
- Data items and replica values.
- Write events and originating replicas.
- Events and causal dependencies.
- Replication tasks and their destination replicas.

Check constraints enforce valid versions, logical clock values, queue limits, and key lengths.

Unique constraints prevent duplicate replica identities and duplicate replication targets.

### 8.3 Replication Queue

The replication queue represents asynchronous propagation work.

Each queue entry identifies:

- The event to replicate.
- The destination replica.
- Number of processing attempts.
- Last processing error.
- Queue creation time.
- Successful processing time.

The partial index on unprocessed events improves the efficiency of backlog queries.

`FOR UPDATE SKIP LOCKED` allows multiple database workers to claim separate queue entries without unnecessarily blocking one another.

### 8.4 Vector Clock Storage

The `event_clock_components` table stores vector-clock components as relational rows.

This design avoids requiring a fixed number of replicas in a JSON structure.

The `clock_dominates` function compares two event clocks.

The `clocks_concurrent` function identifies events that are not ordered by their vector clocks.

The `causal_dependencies` table stores explicit event-level dependencies.

### 8.5 Transactional Write Processing

The `create_write_event` function:

1. Validates the consistency policy.
2. Checks the origin replica.
3. Validates the data key and value.
4. Verifies causal dependencies when required.
5. Checks strong-consistency availability requirements.
6. Creates a write event.
7. Stores logical clock information.
8. Applies the origin's value.
9. Updates all logical replicas for strong consistency, or queues propagation for asynchronous models.
10. Records the operation in the audit table.

PostgreSQL transactions ensure that database changes within the same transaction either commit together or roll back together.

### 8.6 Replication Processing

The `process_replication_queue` function processes pending events in batches.

Its behavior includes:

- Skipping offline replicas.
- Checking causal dependencies.
- Avoiding stale-version overwrites.
- Updating destination replica state.
- Recording replication attempts.
- Marking successfully processed queue entries.
- Updating event status when all replication targets are complete.

This models durable asynchronous work rather than directly coupling every remote update to the originating request.

### 8.7 Reporting

Three principal views provide operational visibility.

**`replica_consistency_report`**

Measures replica convergence and version differences for each logical key.

**`replication_backlog`**

Measures outstanding replication work and processing delays.

**`consistency_event_report`**

Provides event status, originating replica, consistency model, and replication progress.

These reports help identify stale replicas, replication bottlenecks, and incomplete propagation.

## 9. Consistency Evaluation Scenarios

The following scenarios describe the behavior implemented in the five source files.

| Scenario | Expected behavior |
|---|---|
| All replicas online, strong write | All logical replicas receive the update |
| One replica offline, strong write | Operation is rejected under the all-replica policy |
| Local eventual write | Origin updates immediately |
| Remote eventual read before propagation | May return an older value |
| Eventual synchronization | Pending events are propagated |
| Concurrent writes | Deterministic conflict handling is applied |
| Causal write with observed dependency | Operation is accepted |
| Causal write with missing dependency | Operation is rejected |
| Offline asynchronous replica | Pending events remain queued |
| Replica recovery | Pending events can be processed |

These scenarios distinguish the acceptance of an operation from its visibility across the distributed system.

## 10. Edge Cases and Failure Handling

### 10.1 Replica Failure

An unavailable replica may prevent a strong write from completing when the configured policy requires every replica.

An asynchronous design can continue accepting eligible local writes while remote replicas are unavailable.

The resulting replication backlog must be monitored.

### 10.2 Concurrent Writes

Two replicas may independently update the same key.

Neither update necessarily causally precedes the other.

A system must define a conflict-resolution strategy.

A timestamp-based strategy is simple but may discard meaningful changes.

### 10.3 Missing Causal Dependencies

A dependent event cannot safely become visible before its predecessor.

The replication worker must retain the event until its dependency becomes available.

### 10.4 Replication Backlog

A growing queue can indicate:

- Network disruption.
- Offline destinations.
- Insufficient processing capacity.
- Repeated application failures.
- Excessive write throughput.

Production systems should use bounded queues, retry policies, dead-letter handling, and operational alerts.

### 10.5 Duplicate Delivery

Network retries can deliver the same event more than once.

Replication should therefore be idempotent.

A stable event identifier and a unique event-destination constraint help prevent duplicate queue entries.

Production systems should also ensure that applying an event repeatedly does not produce unintended business effects.

### 10.6 Clock Drift

Physical timestamps are not always reliable for determining distributed ordering.

Vector clocks provide causal relationships, but they do not independently establish a total order for concurrent events.

A deterministic tie-breaking rule or domain-specific conflict resolver is still necessary.

## 11. Performance and Complexity

Let:

- N represent the number of replicas.
- K represent the number of stored keys.
- V represent the number of vector-clock participants.
- Q represent the number of pending replication events.

Approximate complexity of the educational implementations:

| Operation | Approximate complexity | Explanation |
|---|---|---|
| Local hash-map read | O(1) average | Direct key lookup |
| Local hash-map write | O(1) average | Direct key update |
| Vector-clock merge | O(V) | Compare logical components |
| Vector-clock dominance | O(V) | Examine clock components |
| Synchronous propagation | O(N) | Apply the update to every replica |
| Queue insertion | O(N) | Create destination tasks |
| Queue synchronization | O(Q × V) in causal processing | Dependency checks across pending events |
| Replica inspection | O(N) | Examine each replica |

Actual complexity depends on the selected data structures and implementation details.

In PostgreSQL, indexes improve selective retrieval and pending-queue inspection. They introduce additional storage and write-maintenance costs.

For large systems, vector-clock metadata may become expensive as the number of independent participants grows. Dotted version vectors, hierarchical clocks, and other causal metadata designs may be more suitable.

## 12. Security and Operational Controls

Consistency guarantees do not replace security controls.

A production distributed data platform should implement:

- Authenticated replica identities.
- Role-based access control.
- Authorization for write and replication operations.
- TLS for network communication.
- Encryption at rest.
- Audit logging.
- Input validation.
- Resource limits.
- Protected administrative operations.
- Replication queue monitoring.
- Backup and recovery procedures.
- Data-retention policies.

The SQL script uses database constraints and an audit table, but it does not configure database users, authentication, encryption, or row-level security.

The programming-language examples are simulations and do not provide production network security.

## 13. Important Technical Limitations

The implementations deliberately demonstrate consistency mechanisms without claiming to implement a production distributed database.

| Implementation | Limitation |
|---|---|
| Python | Process-local locking; simplified timestamp-based conflict resolution |
| JavaScript | Process-local serialization; in-memory replication queues |
| C++17 | No network transport, durable storage, or distributed locking |
| Java 17 | Synchronized in-process services rather than distributed coordination |
| PostgreSQL | Logical replicas share one database transaction and one database instance |

The strong-consistency examples simulate coordinated updates but do not implement Raft, Paxos, distributed two-phase commit, or a complete linearizable replication protocol.

The eventual-consistency implementations demonstrate asynchronous propagation but do not provide a complete production retry and dead-letter architecture.

The causal implementations demonstrate vector clocks and dependency-aware processing. They use simplified dependency representations and do not implement every aspect of a production causal broadcast protocol.

The PostgreSQL implementation provides relational modeling, transactional operations, logical replication simulation, and reporting. Its version-based conflict handling is not a complete vector-clock reconciliation engine.

These limitations are important because an educational consistency simulation and a production distributed storage system provide different levels of correctness and fault tolerance.

## 14. Cross-Language Implementation Map

| Technical concept | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Consistency modes | Enum | Frozen object | Enum class | Enum | PostgreSQL enum |
| Replica state | Dataclass | Class | Struct | Class | Table |
| Write event | Dataclass | Object | Struct | Record | Table |
| Vector clocks | Dictionary | Map | Ordered map | Immutable map | Relational components |
| Replication queue | List | Array | Vector | ArrayList | Queue table |
| Error handling | Exceptions | Custom errors | Exceptions | Custom exceptions | SQL exceptions |
| Concurrency control | RLock | Promise serialization | Sequential execution | Synchronized methods | Transactions and row locks |
| Reporting | Dictionaries | Objects | Output methods | Maps | Views and queries |

## 15. Execution Requirements

| Deliverable | Runtime | External dependencies |
|---|---|---|
| Python | Python 3.10+ | None |
| JavaScript | Node.js 18+ | None |
| C++17 | C++17-compatible compiler | None |
| Java | JDK 17+ | None |
| PostgreSQL | PostgreSQL 15+ | `pgcrypto` for UUID generation |

### Python

The Python file runs directly with the Python interpreter.

It uses standard-library modules for dataclasses, enums, synchronization, JSON serialization, and UUID generation.

### JavaScript

The JavaScript file runs under Node.js.

It uses built-in modules for event handling and UUID generation.

### C++17

Compile the program with a C++17-compatible compiler.

The implementation uses only standard-library headers.

### Java 17

The Java source file is named `ConsistencyEnterprise.java`.

It uses records, streams, collections, and other Java 17 language features.

### PostgreSQL

The SQL script creates and populates its own schema.

It uses PostgreSQL procedural language functions, JSONB, identity columns, foreign keys, transactions, partial indexes, and queue-processing queries.

The script drops and recreates the `consistency_lab` schema. It should therefore be executed only in a database where replacing that schema is acceptable.

## 16. Practical Model Selection

The appropriate consistency model depends on the meaning of the data and the consequences of stale or reordered observations.

| Application requirement | Suitable starting point | Reason |
|---|---|---|
| Financial balance updates | Strong | Strictly ordered account operations |
| Product descriptions | Eventual | Temporary regional differences may be acceptable |
| Distributed caching | Eventual | Recalculation and refresh can reconcile stale values |
| Collaborative editing | Causal or specialized CRDT-based design | Preserves meaningful operation relationships |
| Order and payment workflows | Causal or strong, depending on business invariants | Preserves dependencies and transaction requirements |
| Inventory reservation | Strong or a carefully designed transactional allocation model | Prevents overselling |
| Social activity feeds | Eventual or causal | Temporary differences may be acceptable while user-visible ordering remains meaningful |

A consistency model must be selected according to application-level invariants, not merely implementation convenience.

The key distinction is that strong consistency governs globally valid operation ordering, eventual consistency governs convergence, and causal consistency governs dependency-preserving observation. These guarantees address different distributed-systems problems and should be evaluated independently.
