# CAP Theorem: Consistency, Availability, and Partition Tolerance

## 1. Introduction

The CAP theorem describes a fundamental constraint in distributed systems. It explains the relationship between three properties:

- **Consistency (C):** Every successful read observes a value consistent with a single, valid ordering of completed operations. In the conventional CAP formulation, consistency refers to linearizability.
- **Availability (A):** Every request received by a non-failing node eventually receives a response. The response must not simply wait indefinitely for another partition to recover.
- **Partition Tolerance (P):** The system continues operating despite communication failures that prevent some nodes from exchanging messages.

A distributed system cannot guarantee both linearizable consistency and availability for every request while a network partition is occurring.

The important qualification is that this trade-off concerns partition scenarios. When communication is reliable, a distributed system may provide both strong consistency and availability.

## 2. Distributed System Architecture

A distributed database stores data across multiple independent nodes. Each node can maintain a replica of some or all of the system's data.

A simplified architecture is:

    Client
       |
       v
    Request Router
       |
       +-------------------+
       |                   |
       v                   v
    Node A               Node B
       |                   |
       +---------+---------+
                 |
                 v
               Node C

Each replica may contain:

- A local copy of a record.
- A version identifying the latest known update.
- Availability information.
- Communication state.
- A replication history.

Replication improves fault tolerance and can increase read throughput. It also introduces consistency challenges because replicas may receive updates at different times.

### Network partitions

A network partition occurs when communication between groups of nodes fails.

For example:

    Partition A             Partition B

    Node A                  Node B
                              |
                            Node C

    Communication between the two groups is unavailable.

Node A cannot communicate with Nodes B and C. The nodes may still operate locally, but they cannot coordinate with the other partition.

The system must decide whether to reject certain requests or accept operations that may temporarily produce divergent data.

## 3. Understanding the Three Properties

### 3.1 Consistency

Consistency ensures that operations observe an ordering that satisfies the selected consistency model.

Consider a banking account:

| Operation | Account balance |
|---|---:|
| Initial state | ₹5,000 |
| Withdrawal | ₹500 |
| Expected balance | ₹4,500 |

If a write succeeds, a subsequent read must not return an obsolete balance when the system promises linearizability.

Consistency is particularly important in:

- Banking ledgers.
- Financial transactions.
- Inventory reservation systems.
- Distributed locking.
- Payment authorization.
- Critical configuration management.

Several consistency models exist.

| Model | Characteristics |
|---|---|
| Linearizability | Operations appear to occur atomically in a real-time-compatible order |
| Sequential consistency | Operations follow a valid global sequence that respects each process's program order |
| Causal consistency | Causally related operations preserve their ordering |
| Eventual consistency | Replicas converge when updates stop and communication is restored |
| Read-your-writes | A client observes its own successful updates in subsequent reads |
| Monotonic reads | A client does not move backward to an older observed state |

These models are not interchangeable. Eventual consistency does not guarantee immediate consistency, and linearizability provides a stronger guarantee than eventual consistency.

### 3.2 Availability

Availability concerns whether requests receive responses.

A distributed service may remain available when some nodes become unreachable.

For example, a product catalogue may continue returning locally stored product information even if one replica cannot communicate with the others.

Availability does not guarantee that every response contains the newest value.

A service that returns an obsolete value may satisfy a weaker availability-oriented policy while violating linearizability.

Availability also differs from uptime. Uptime measures service accessibility over time, while CAP availability is a property of request handling during distributed failures.

### 3.3 Partition Tolerance

Partition tolerance concerns communication failures between distributed nodes.

Examples include:

- Network cable failures.
- Router failures.
- Data-centre connectivity failures.
- DNS resolution failures.
- Firewall misconfiguration.
- Inter-region network disruption.
- Network congestion and message loss.

Partition tolerance does not mean that partitions are prevented. It means the system has a defined behavior when they occur.

In a distributed deployment, partitions must be treated as realistic failure conditions rather than exceptional events that can be ignored.

## 4. CAP Trade-offs

The three conventional CAP configurations are CP, AP, and CA.

| Configuration | Consistency | Availability | Partition tolerance |
|---|---|---|---|
| CP | Prioritized | May be sacrificed during a partition | Supported |
| AP | May be temporarily weakened | Prioritized | Supported |
| CA | Prioritized | Prioritized | Not guaranteed |

A CA configuration can provide consistency and availability when communication remains reliable. It cannot guarantee both during a network partition.

In practical distributed systems, partition tolerance is generally necessary because independent machines communicate over networks that can fail.

### 4.1 CP systems

A CP system prioritizes consistency when a partition occurs.

Suppose three replicas store the same account balance.

    Node A: ₹5,000
    Node B: ₹5,000
    Node C: ₹5,000

A network partition separates Node A from Nodes B and C.

If the system requires a majority quorum, Node A cannot independently authorize a write.

The two-node majority partition can continue processing eligible operations.

| Partition | Available replicas | Quorum | Write |
|---|---:|---:|---|
| A | 1 | 2 | Rejected |
| B + C | 2 | 2 | Accepted |

This behavior avoids independently committing conflicting operations under the modeled quorum policy.

Common CP-oriented technologies and architectures include:

- <Entity value="Apache ZooKeeper" category="software" disambig="Distributed coordination service"/>.
- <Entity value="etcd" category="software" disambig="Distributed key-value store"/>.
- <Entity value="Consul" category="software" disambig="Distributed service networking and configuration"/>.
- Raft-based replicated state machines.
- Strongly consistent distributed databases.

The exact guarantees depend on implementation, configuration, failure assumptions, and transaction semantics.

### 4.2 AP systems

An AP system prioritizes request availability during a partition.

Consider a product inventory system.

    Initial stock: 100

    Partition A:
        Node A receives a sale.
        Local stock becomes 80.

    Partition B:
        Node B receives another update.
        Local stock becomes 90.

Both partitions may accept their updates.

During the partition:

| Replica | Local stock |
|---|---:|
| Node A | 80 |
| Node B | 90 |
| Node C | 90 |

The replicas temporarily disagree.

When connectivity returns, the system must reconcile divergent records.

Possible conflict-resolution strategies include:

- Last-write-wins.
- Version vectors.
- Multi-value registers.
- Application-specific merging.
- Conflict-free replicated data types.
- Explicit conflict resolution by a business process.

AP behavior is appropriate when temporary inconsistency is acceptable and the application has a well-defined reconciliation strategy.

Examples include product catalogues, distributed caches, collaborative applications, and some geographically distributed content systems.

Availability does not automatically make an AP design correct. Business rules must account for concurrent operations.

## 5. Quorum-Based Replication

A quorum is the minimum number of participating replicas required to authorize an operation.

For a cluster containing \(N\) replicas, a simple majority quorum is:

\[
Q=\left\lfloor\frac{N}{2}\right\rfloor+1
\]

For three replicas:

\[
Q=\left\lfloor\frac{3}{2}\right\rfloor+1=2
\]

For five replicas:

\[
Q=\left\lfloor\frac{5}{2}\right\rfloor+1=3
\]

Majority quorums intersect when each operation uses a majority of the same replica membership.

This intersection property helps prevent two disjoint majorities from independently authorizing incompatible decisions.

It does not, by itself, implement a complete consensus protocol.

A production consensus algorithm also needs mechanisms for:

- Leader election.
- Term or epoch management.
- Log replication.
- Commit-index management.
- Membership changes.
- Recovery after failures.
- Protection against stale leaders.

Raft and Paxos provide consensus mechanisms that address these requirements under their respective assumptions.

The implementations in this project use majority counting to demonstrate partition behavior. They are not replacements for Raft, Paxos, or production-grade transactional storage.

## 6. CP, AP, and CA: Important Distinctions

### CP versus AP

| Dimension | CP | AP |
|---|---|---|
| Primary objective | Consistent decisions | Continued request handling |
| Partition behavior | Rejects operations lacking required coordination | Accepts eligible local operations |
| Read behavior | Requires the configured consistency conditions | May return locally available data |
| Write behavior | Requires sufficient coordination | May accept independent updates |
| Recovery | Restore agreement through replication | Reconcile divergent replica state |
| Main risk | Temporary request rejection | Temporary inconsistent data |

The CAP theorem does not state that every operation in a CP system must fail during a partition.

A majority partition may continue operating while a minority partition rejects operations.

Likewise, AP does not mean that every operation must be accepted. An offline node, exhausted resource, invalid request, or failed process may still reject a request.

### CAP versus PACELC

CAP describes the consistency-availability trade-off during network partitions.

PACELC extends this reasoning:

- If a partition occurs (P), the system chooses between availability (A) and consistency (C).
- Else (E), when the system is operating normally, it chooses between latency (L) and consistency (C).

PACELC highlights that consistency and latency trade-offs also exist outside partition events.

This distinction is important when evaluating geographically distributed databases.

## 7. Python Implementation: Distributed Storage Simulation

The Python implementation models a distributed key-value cluster using classes and dataclasses.

### Domain objects

| Object | Responsibility |
|---|---|
| `DistributedCluster` | Controls cluster behavior |
| `Node` | Stores a local replica |
| `Record` | Represents a versioned key-value entry |
| `Version` | Identifies the logical update order |
| `OperationResult` | Represents request outcomes |
| `CAPMode` | Selects CP or AP behavior |

### CP execution

The CP write procedure:

1. Identifies the requesting node.
2. Finds available nodes in the same partition.
3. Calculates the majority quorum.
4. Rejects the write if the quorum is unavailable.
5. Creates a versioned record.
6. Applies the record to the connected majority.

The implementation also applies quorum requirements to reads.

### AP execution

The AP write procedure:

1. Identifies the local replica.
2. Verifies that the replica is available.
3. Creates a versioned record.
4. Updates the requesting replica.
5. Acknowledges the write without requiring majority participation.

Reads return locally available values.

### Conflict resolution

When communication is restored, the implementation selects the record with the greatest version.

Version ordering uses:

- Logical timestamp.
- Writer identifier as a deterministic tie-breaker.

This approach makes the demonstration reproducible. It is not a universal conflict-resolution rule for financial or inventory records.

### Validation and testing

The script tests:

- CP minority rejection.
- CP majority acceptance.
- AP local-write acceptance.
- Partition recovery.
- Replica consistency after reconciliation.
- Offline-node behavior.
- Invalid cluster configuration.

## 8. JavaScript Implementation: Event-Driven Distributed Storage

The JavaScript implementation provides an event-driven perspective.

### Architectural components

| Component | Responsibility |
|---|---|
| `Replica` | Maintains local records |
| `CAPCluster` | Coordinates cluster operations |
| `EventEmitter` | Publishes operational events |
| `serialize()` | Serializes local state-changing operations |
| `compareVersion()` | Determines version precedence |
| `recordEvent()` | Maintains operation history |

### Asynchronous operations

The implementation uses asynchronous methods and promises to represent distributed request processing.

Operations are serialized within the local JavaScript process to prevent competing writes from racing against the same in-memory state.

This mechanism is not distributed locking or consensus.

### Event-driven monitoring

The cluster publishes events such as:

- `WRITE_ACCEPTED`
- `WRITE_REJECTED`
- `PARTITION_CREATED`
- `NODE_AVAILABILITY_CHANGED`
- `PARTITION_HEALED`

Applications can subscribe to these events for monitoring and operational reporting.

### Engineering considerations

The implementation uses:

- `Map` for replica membership and key-value storage.
- `Set` for consistency comparison.
- `Promise` for asynchronous operation handling.
- `EventEmitter` for event publication.
- `structuredClone()` for independent record copies.
- `crypto.randomUUID()` for event identifiers.

The event log is held in memory. Production implementations should use durable event storage, bounded retention, authentication, authorization, and appropriate backpressure.

## 9. C++17 Implementation: Quorum and Replica Engine

The C++17 implementation focuses on domain modeling and state management.

### Data structures

| Structure | Purpose |
|---|---|
| `Replica` | Represents an individual storage node |
| `Record` | Stores the replicated value |
| `Version` | Provides deterministic version ordering |
| `OperationResult` | Communicates request outcomes |
| `DistributedCluster` | Implements replication policies |

The implementation uses:

- `std::vector` for replica membership.
- `std::unordered_map` for local record storage.
- `std::optional` for missing records.
- `std::find_if` for replica identification.
- `std::map` for ordered reporting.

### Complexity

Let:

- \(N\) represent the total number of replicas.
- \(K\) represent the number of records stored on a replica.
- \(G\) represent the number of replicas in the requesting partition.

| Operation | Approximate complexity |
|---|---|
| Quorum calculation | \(O(1)\) |
| Replica lookup | \(O(N)\) |
| Partition discovery | \(O(N)\) |
| CP write | \(O(N)\) |
| AP write | Average \(O(1)\) |
| AP local read | Average \(O(1)\) |
| CP read | \(O(G)\) |
| Reconciliation | \(O(NK)\) |

The implementation favors clarity over optimized replica indexing.

A production system would generally use indexed membership structures and asynchronous network communication.

## 10. Java 17 Implementation: Enterprise Storage Governance

The Java implementation separates domain models, consistency policies, and cluster services.

### Policy abstraction

The `ConsistencyPolicy` interface defines two decisions:

- Whether a write can proceed.
- Whether a read can proceed.

`CPPolicy` requires quorum participation.

`APPolicy` requires at least one available replica.

This separation allows policy behavior to be changed without rewriting the entire storage service.

### Enterprise domain model

Java records represent immutable data structures:

- `Version`
- `DataRecord`
- `OperationResult`
- `AuditEvent`

The `Replica` class manages mutable local storage, while `DistributedCluster` coordinates operations.

### State transitions

The implementation supports:

- Replica online and offline transitions.
- Network partition creation.
- Partition healing.
- Write acceptance and rejection.
- Read availability evaluation.
- Conflict reconciliation.

### Auditability

Each operation records:

- Timestamp.
- Operation type.
- Requesting replica.
- Record key.
- Outcome.

The audit structure provides a foundation for operational analysis. A production implementation would persist these events and protect them against unauthorized modification.

## 11. PostgreSQL Implementation: Relational CAP Model

The PostgreSQL implementation models distributed storage operations relationally.

### Database architecture

| Database object | Purpose |
|---|---|
| `clusters` | Cluster configuration and CAP policy |
| `replica_nodes` | Replica membership and partition state |
| `network_partitions` | Network partition history |
| `replicated_records` | Cluster-level reference records |
| `replica_records` | Individual replica contents |
| `operation_logs` | Request outcomes |
| `version_conflicts` | Conflict-resolution history |

### Relational relationships

    clusters
       |
       +---- replica_nodes
       |         |
       |         +---- replica_records
       |
       +---- replicated_records
       |
       +---- network_partitions
       |
       +---- operation_logs
       |
       +---- version_conflicts

The cluster configuration determines the selected policy and quorum size.

Replica nodes identify the communication group to which they belong.

Replica records preserve individual copies of distributed data.

### Integrity constraints

The database uses:

- Primary keys.
- Foreign keys.
- Unique constraints.
- Check constraints.
- Enumerated data types.
- Insert validation triggers.
- Referential deletion rules.

Indexes support cluster membership, replica availability, version retrieval, and operational failure reporting.

### Stored functions and procedures

`evaluate_operation()` determines whether a request satisfies the cluster's configured availability and quorum requirements.

`execute_write()` performs the selected CP or AP write workflow.

`execute_read()` returns an appropriate local or quorum-based result.

`reconcile_cluster()` identifies divergent versions and synchronizes available replicas using the configured demonstration policy.

### Database transactions

The write procedure uses a cluster-row lock when allocating a logical version.

This serializes version allocation for writers using this database implementation.

It does not coordinate independent database servers or establish distributed consensus.

The SQL demonstrates relational workflow management, not a real multi-region distributed database implementation.

### Reporting

The reporting views expose:

- Online replica counts.
- Quorum availability.
- Active partition groups.
- Replica value divergence.
- Failed operations.
- Conflict history.

These reports help distinguish node availability from data consistency.

## 12. Last-Write-Wins and Conflict Resolution

A distributed system needs a policy for handling concurrent updates.

Consider two replicas independently modifying the same record:

| Replica | Version | Value |
|---|---:|---|
| Node A | 10 | 80 |
| Node B | 11 | 90 |

A last-write-wins strategy chooses version 11.

The implementation uses logical versions and writer identifiers to create a deterministic ordering.

This is useful for demonstrations and selected data types, but it has limitations.

A higher logical version does not necessarily represent the business-correct update.

For example, if two customers independently purchase the final available inventory item, choosing the latest value may silently discard one transaction.

Alternative strategies include:

| Strategy | Characteristics |
|---|---|
| Last-write-wins | Selects a deterministic winning version |
| Version vectors | Detects concurrent updates |
| Multi-value registers | Preserves concurrent values |
| Application-level merge | Applies domain-specific business rules |
| CRDTs | Provide convergent operations under defined mathematical conditions |
| Manual resolution | Requires an authorized decision |

Conflict resolution must be selected according to the data's business meaning.

## 13. Practical Applications

### Banking and financial systems

Banking ledgers generally require strong consistency for critical financial transactions.

A partition must not permit incompatible financial decisions to be committed independently.

CP-oriented coordination is therefore appropriate for many critical ledger operations.

### E-commerce

Different e-commerce functions may need different consistency models.

| Function | Typical requirement |
|---|---|
| Product descriptions | Eventual consistency may be acceptable |
| Product recommendations | Availability and low latency |
| Shopping cart | Session-aware or application-specific consistency |
| Payment authorization | Strong consistency |
| Inventory reservation | Strong coordination or carefully designed reservation mechanisms |
| Product search indexing | Asynchronous replication |

A single application does not necessarily need one consistency model for every data category.

### Healthcare systems

Clinical records require careful control of conflicting updates.

Patient records may be replicated geographically for accessibility, but concurrent modifications to medication orders or critical clinical information require application-specific validation and reconciliation.

### Telecommunications

Distributed network services may prioritize availability for certain operational functions while maintaining stronger consistency for critical subscriber and charging records.

### Content delivery networks

Content delivery networks frequently replicate content across geographically distributed locations.

Temporary differences in cached content can be acceptable when expiration, invalidation, and refresh mechanisms are properly designed.

## 14. CAP Limitations and Design Considerations

The CAP theorem is a conceptual model, not a complete distributed-system design methodology.

Important considerations include:

- CAP describes behavior during network partitions, not every ordinary database operation.
- Consistency has multiple meanings; linearizability is the conventional CAP definition.
- A CP system can remain operational through a majority partition.
- AP systems need explicit conflict-resolution behavior.
- Network partitions and process failures are different failure categories.
- Quorum calculations alone do not establish consensus.
- Availability does not guarantee low latency or correct business outcomes.
- Eventual consistency requires convergence assumptions and a reconciliation strategy.
- Read and write policies may differ.
- A distributed application may use different consistency guarantees for different data types.

The Python, JavaScript, C++, and Java programs simulate partition behavior using in-memory replicas. The PostgreSQL script provides a relational representation of cluster configuration and replica operations. None of these implementations should be treated as a production consensus or distributed transaction protocol.

## 15. Security and Operational Considerations

Distributed systems introduce additional security requirements.

| Area | Control |
|---|---|
| Node authentication | Mutual TLS and node identity verification |
| Communication | Encryption in transit |
| Authorization | Role-based access control |
| Data integrity | Checksums and authenticated messages |
| Audit | Durable, access-controlled operation logs |
| Replication | Authenticated replication channels |
| Configuration | Restricted administrative access |
| Recovery | Verified backups and recovery procedures |
| Monitoring | Quorum, latency, replication lag, and partition alerts |
| Conflict management | Explicit and auditable resolution policies |

Production deployments should also consider:

- Split-brain prevention.
- Stale leader rejection.
- Clock synchronization limitations.
- Replica membership changes.
- Network timeouts.
- Retry behavior.
- Idempotency.
- Backpressure.
- Recovery after prolonged outages.

Retries must be designed carefully. Retrying a non-idempotent financial operation without a unique operation identifier can cause duplicate processing.

## 16. Comparative Implementation Matrix

| Capability | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| CP behavior | Yes | Yes | Yes | Yes | Yes |
| AP behavior | Yes | Yes | Yes | Yes | Yes |
| Replica management | Yes | Yes | Yes | Yes | Yes |
| Partition simulation | Yes | Yes | Yes | Yes | Yes |
| Majority quorum | Yes | Yes | Yes | Yes | Yes |
| Version management | Yes | Yes | Yes | Yes | Yes |
| Conflict resolution | Yes | Yes | Yes | Yes | Yes |
| Operation logging | Yes | Yes | Console | In-memory audit | Persistent |
| Automated assertions | Yes | Yes | Yes | Yes | SQL reporting |
| Event-driven behavior | No | Yes | No | No | Database procedures |

## 17. Execution and Verification

### Python

Run the file using Python 3.10 or later.

The program demonstrates both CAP configurations and executes built-in assertions.

### JavaScript

Run using Node.js 18 or later.

The asynchronous demonstration uses the built-in Node.js event system and does not require npm installation.

### C++17

Compile using a C++17-compatible compiler.

The program uses only the standard library.

### Java 17

Save the source as `Main.java` and compile using Java 17.

The program uses records, streams, collections, and standard Java concurrency utilities.

Assertions should be enabled with the Java assertion flag during execution.

### PostgreSQL

Execute the SQL script against PostgreSQL 14 or later using a database account authorized to create schemas, types, tables, functions, procedures, and triggers.

The script creates the `cap_lab` schema and populates it with two sample clusters:

- `banking-ledger-cluster`: CP.
- `product-catalog-cluster`: AP.

The sample workflows create partitions, perform operations, restore communication, and reconcile replicas.

The SQL demonstration uses one PostgreSQL database to represent multiple logical replicas. It does not establish physical replication between independent PostgreSQL servers.

## 18. Technical Terminology

| Term | Definition |
|---|---|
| Distributed system | A system composed of multiple communicating independent processes |
| Replica | A copy of data maintained by a distributed node |
| Replication | The process of distributing data updates among replicas |
| Network partition | A communication failure separating groups of nodes |
| Quorum | Minimum participating replica count required for an operation |
| Linearizability | Consistency model preserving a real-time-compatible order of operations |
| Eventual consistency | Guarantee of convergence under specified recovery conditions |
| Logical clock | A mechanism for ordering distributed events without relying solely on wall-clock time |
| Split brain | A condition in which multiple components act as independent authorities |
| Reconciliation | Process of resolving divergent replica state |
| Conflict resolution | Selection or combination of concurrent updates |
| Consensus | Agreement among distributed processes on a value or sequence of decisions |
| Replication lag | Delay between an update and its application to another replica |
| CRDT | Conflict-free replicated data type with mathematically defined convergence properties |
| PACELC | Extension of CAP describing partition-time and normal-operation trade-offs |

The central engineering decision is not simply whether a system is labelled CP or AP. It is how each operation behaves when coordination is unavailable, which guarantees the application actually requires, and how the system recovers without violating its business rules.
