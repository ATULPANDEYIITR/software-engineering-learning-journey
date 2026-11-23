# Distributed Systems: Nodes, Networks, and Distributed State

## 1. Technical Scope

Distributed systems consist of independent computing nodes that communicate through a network to coordinate operations, exchange information, and maintain shared application state.

Unlike a single-machine application, a distributed application must operate despite communication delays, partial failures, inconsistent observations, message duplication, and network partitions.

This project implements a distributed key-value storage scenario across multiple nodes and regions.

The five implementations examine complementary engineering perspectives:

| Implementation | Primary engineering perspective |
|---|---|
| Python | Distributed-system simulation and state convergence |
| JavaScript | Asynchronous communication and event-driven processing |
| C++17 | Quorum-based replication and consistency evaluation |
| Java 17 | Enterprise domain modeling and operation management |
| PostgreSQL | Persistent distributed metadata and relational workflows |

The implementations share the same fundamental domain concepts but use different programming techniques.

## 2. Distributed System Architecture

### 2.1 Fundamental components

A distributed system consists of multiple independent components.

| Component | Responsibility |
|---|---|
| Node | Executes operations and maintains local state |
| Cluster | Coordinates participating nodes |
| Network | Connects nodes and transports messages |
| Coordinator | Initiates an operation and coordinates replication |
| Replica | Maintains a copy of distributed data |
| Logical clock | Tracks logical event ordering |
| Message | Carries information between nodes |
| Failure detector | Identifies nodes that may be unavailable |
| Consistency policy | Defines the required level of replica acknowledgement |
| Replication mechanism | Transfers state between nodes |

A node can function as a coordinator for one operation and a replica for another. This distinction depends on the operation rather than permanent node identity.

### 2.2 Architectural relationship

    Distributed Application
            |
            v
       Cluster Manager
            |
       +----+----+
       |         |
       v         v
    Node A     Node B
       |         |
       +----+----+
            |
          Network
            |
       +----+----+
       |         |
       v         v
    Node C     Node D
       |         |
       v         v
    Local      Local
    State      State
       \         /
        \       /
         Replication
             |
        Consistency
             |
        Reconciliation

Every node maintains its own local state. Replication attempts to make relevant state available across participating nodes.

A shared logical dataset does not imply that every node has an identical physical copy at every moment.

## 3. Nodes and Distributed State

### 3.1 Node

A node is an independently operating participant in a distributed system.

It may be:

- A physical server.
- A virtual machine.
- A container.
- A cloud instance.
- A database server.
- A service process.

A node generally has:

- A unique identifier.
- A network endpoint.
- A local state store.
- A communication interface.
- An operational status.
- A mechanism for handling failures.

The implementations represent nodes using classes or relational records.

Node lifecycle states include:

| State | Meaning |
|---|---|
| ACTIVE | The node is available for operations |
| SUSPECTED | The node has not responded within an expected period |
| STOPPED | The node is known to be unavailable |

A suspected node is not necessarily stopped. Its failure may be caused by network congestion, routing problems, or delayed messages.

### 3.2 Local state

Distributed state is the collection of information maintained across participating nodes.

Consider an inventory record:

    product_id = 101
    quantity = 250
    warehouse = Lucknow

Node A might store quantity 250 while Node B temporarily stores quantity 240.

These different observations represent divergent replicas.

The system must determine how updates are ordered, propagated, reconciled, and exposed to applications.

### 3.3 Replicated state

Replication creates copies of information on multiple nodes.

For example:

| Node | Product | Quantity |
|---|---|---:|
| Node A | 101 | 250 |
| Node B | 101 | 250 |
| Node C | 101 | 250 |

Replication provides resilience and can improve read availability.

It also introduces additional engineering requirements:

- Conflict resolution.
- Replication acknowledgement.
- Version management.
- Duplicate message handling.
- Recovery after outages.
- Consistency guarantees.

Replication does not automatically guarantee consistency.

## 4. Networks and Communication

### 4.1 Network topology

Network topology describes how distributed nodes communicate.

Common arrangements include:

| Topology | Characteristics |
|---|---|
| Point-to-point | Direct communication between two participants |
| Star | Communication organized around a central coordinator |
| Ring | Nodes connected in a circular arrangement |
| Mesh | Multiple communication paths between nodes |
| Hierarchical | Communication organized into multiple levels |

The project uses a simplified mesh-style communication model.

Nodes can exchange messages directly when the corresponding network connection is available.

### 4.2 Message delivery

A distributed message typically contains:

- Message identifier.
- Sender.
- Receiver.
- Message type.
- Payload.
- Creation timestamp.
- Processing status.

The implementations distinguish replication, heartbeat, and synchronization messages.

Messages can experience several delivery conditions:

| Condition | Description |
|---|---|
| Successful delivery | Receiver processes the message |
| Message loss | The message never reaches the receiver |
| Duplication | The receiver receives the same message more than once |
| Delay | Delivery occurs later than expected |
| Partition | Communication between two nodes becomes unavailable |

Network communication must be treated as unreliable.

A successful local operation does not necessarily mean that every remote replica has received the corresponding update.

### 4.3 Network partitions

A network partition occurs when otherwise operational nodes cannot communicate across a network boundary.

Example:

    Partition A             Partition B

      Node A                 Node B
         |                      |
      Node C                 Node D

         X----------------------X

The nodes within each partition may continue performing some local operations.

Operations requiring communication across the partition may fail.

The implementations model partitions by marking particular node-to-node connections unavailable.

Healing the network restores communication paths, but it does not automatically reconcile previously divergent state.

That requires a recovery mechanism such as anti-entropy synchronization.

## 5. Logical Clocks and Event Ordering

### 5.1 Why physical clocks are insufficient

Physical clocks on different servers may disagree because of:

- Clock drift.
- Synchronization delays.
- Network latency.
- Time-source differences.
- Incorrect clock configuration.

Consequently, physical timestamps alone are not always suitable for determining the ordering of distributed events.

### 5.2 Lamport logical clocks

A Lamport logical clock provides a mechanism for ordering events without requiring perfectly synchronized physical clocks.

The main rules are:

1. Increment the local clock before a local event.
2. Include the logical timestamp when transmitting a message.
3. When receiving a message, update the local clock using the maximum of the local and received timestamps, then increment it.

The receive operation is:

\[
L_{\text{new}}=\max(L_{\text{local}},L_{\text{received}})+1
\]

For example:

| Event | Logical time |
|---|---:|
| Node A local write | 1 |
| Node A sends message | 2 |
| Node B receives message | 3 |
| Node B performs another event | 4 |

Lamport clocks preserve the implication that causally related events are correctly ordered.

They do not establish that every pair of events with different timestamps is causally related.

### 5.3 Deterministic conflict resolution

The implementations combine logical time with a node identifier.

A version is represented as:

\[
V=(L,N)
\]

Where:

- \(L\) is the logical timestamp.
- \(N\) is the originating node identifier.

Versions are compared lexicographically.

First, the logical timestamp is compared. If both timestamps are equal, the node identifier determines the winner.

This provides deterministic Last-Write-Wins resolution.

It is a simplified conflict-resolution policy. It does not guarantee that the selected record represents the most recent real-world business event.

## 6. Replication and Consistency

### 6.1 Replication factor

The replication factor represents the number of copies maintained for a particular logical record.

For example:

\[
N=3
\]

means that the intended replication group contains three copies.

Higher replication factors can improve resilience but increase:

- Storage consumption.
- Network traffic.
- Write coordination.
- Recovery complexity.

### 6.2 Replication acknowledgement

A replication acknowledgement indicates that a participating node has processed an operation according to the acknowledgement contract.

The coordinator tracks acknowledgements to determine whether the requested consistency level has been satisfied.

An acknowledgement should not be confused with a guarantee that every replica is synchronized.

### 6.3 Consistency levels

The implementations support three acknowledgement policies.

| Policy | Required acknowledgements |
|---|---:|
| ONE | 1 |
| QUORUM | Majority |
| ALL | Replication factor |

For a replication factor of three:

\[
W_{\text{quorum}}=
\left\lfloor\frac{3}{2}\right\rfloor+1=2
\]

A quorum write therefore requires two acknowledgements.

For the simplified model, the coordinator's local acknowledgement counts as one.

### 6.4 Quorum intersection

For a fixed replication group containing \(N\) replicas, a read quorum \(R\) and write quorum \(W\) intersect when:

\[
R+W>N
\]

For example:

\[
N=3,\quad R=2,\quad W=2
\]

Therefore:

\[
R+W=4>3
\]

The read and write quorums must share at least one replica.

This intersection property is useful when designing consistency protocols.

It does not independently guarantee linearizability. A production system also needs appropriate version validation, operation ordering, membership management, and coordination rules.

### 6.5 Read repair

Read repair compares the available versions and propagates the selected newer version to outdated replicas.

The process is:

1. Collect available replicas.
2. Check whether the required read acknowledgement count is available.
3. Compare record versions.
4. Select the highest version.
5. Repair outdated reachable replicas.

The Python, JavaScript, C++, and Java implementations include simplified read-repair behavior.

### 6.6 Eventual consistency

Eventual consistency means that replicas can temporarily contain different values but may converge when updates stop and communication and synchronization continue successfully.

For example:

| Stage | Node A | Node B | Node C |
|---|---:|---:|---:|
| Initial | 100 | 100 | 100 |
| Local update | 150 | 100 | 100 |
| Replication | 150 | 150 | 100 |
| Synchronization | 150 | 150 | 150 |

Eventual consistency is not the same as immediate consistency.

It also does not guarantee that conflicting updates will always produce the desired business outcome.

## 7. CAP Theorem and Partial Failure

The CAP theorem concerns three properties:

| Property | Meaning |
|---|---|
| Consistency | Every successful read observes a value consistent with the system's chosen atomic consistency guarantee |
| Availability | Every request to a non-failing node receives a response |
| Partition tolerance | The system continues operating despite communication partitions |

During a network partition, a distributed system cannot guarantee both full availability and strong consistency under the classical CAP assumptions.

A system may reject operations that cannot satisfy its consistency policy, or it may permit operations with weaker consistency guarantees.

The project demonstrates this distinction through quorum failures.

When a three-node cluster loses communication between its coordinator and both remote nodes, a quorum write cannot receive the required two acknowledgements.

The coordinator may still retain its local write.

This distinction is important: a rejected distributed operation does not necessarily imply that no local state was modified.

A production implementation needs explicit handling for such uncertain outcomes, including operation identifiers, idempotent retries, and reconciliation.

## 8. Failure Detection

### 8.1 Heartbeats

A heartbeat is a periodic message that indicates a node is communicating.

A typical workflow is:

    Node A
       |
       | Heartbeat
       v
    Monitoring Service
       |
       | Record timestamp
       v
    Failure Detector
       |
       +---- Within timeout: reachable
       |
       +---- Beyond timeout: suspected

The Python, JavaScript, and Java implementations include heartbeat tracking and timeout-based suspicion.

The PostgreSQL implementation stores heartbeat timestamps and provides a function to identify nodes with stale heartbeats.

### 8.2 Failure detector limitations

A heartbeat timeout cannot conclusively prove that a server has failed.

A slow node may be incorrectly classified as unavailable.

This is called a false suspicion.

Production failure detectors need configurable timeouts, monitoring, retry policies, and membership-management procedures.

### 8.3 Recovery

When a stopped node returns:

1. It rejoins the cluster.
2. Its available local state is examined.
3. Missing or outdated records are identified.
4. Updates are synchronized.
5. Its operational state is validated.

A node restart must not automatically be treated as proof that its stored state is current.

## 9. Anti-Entropy Synchronization

Anti-entropy is a reconciliation process that compares replicas and transfers missing or outdated information.

The project uses a simplified full-snapshot comparison.

For every key:

1. Inspect the available replicas.
2. Identify the highest version.
3. Compare the version against each reachable node.
4. Apply the winning version where necessary.

The approach supports deterministic convergence when the version ordering is consistent and communication is restored.

Its main disadvantage is the cost of exchanging complete snapshots.

If a node stores \(K\) records and there are \(N\) nodes, repeated full-snapshot synchronization can require substantial network and processing resources.

More efficient production approaches include:

- Incremental replication.
- Merkle trees.
- Version vectors.
- Change logs.
- Partitioned synchronization.
- Background repair.

## 10. Python Implementation

**File:** `distributed_systems.py`

### Engineering approach

The Python implementation uses object-oriented modeling and an explicit message queue.

The main classes are:

| Class | Responsibility |
|---|---|
| `Network` | Manages partitions, message loss, duplication, and delivery |
| `Node` | Stores local records and processes incoming messages |
| `Version` | Represents logical record ordering |
| `Record` | Represents a versioned distributed value |
| `Message` | Encapsulates communication |
| `DistributedCluster` | Coordinates reads, writes, replication, and recovery |
| `FailureDetector` | Identifies nodes with expired heartbeat timestamps |

### Important mechanisms

**Message deduplication**

Each message has a unique identifier. The receiver records processed identifiers to avoid repeating the same operation.

**Version comparison**

The `Version` dataclass uses ordering based on logical time and node identifier.

**Network partition simulation**

The network maintains a set of unavailable node pairs.

**Quorum processing**

The cluster checks acknowledgement requirements before treating a distributed write as successful.

**Anti-entropy**

The cluster exchanges snapshots and reconciles records.

### Failure handling

The script demonstrates:

- Unavailable nodes.
- Insufficient quorum.
- Partition recovery.
- Stale replica rejection.
- Duplicate message processing.
- Invalid configuration.
- Missing records.

### Practical considerations

Python is useful for building distributed-system simulations, testing failure scenarios, developing operational automation, and validating algorithms.

The implementation is an in-memory simulator rather than a production distributed database.

Its message identifiers and node state are not durable across process restarts.

## 11. JavaScript Implementation

**File:** `distributed_systems.js`

### Engineering approach

The JavaScript implementation emphasizes asynchronous processing and event-driven communication.

It uses:

- Node.js standard libraries.
- `EventEmitter`.
- Promises.
- `async` and `await`.
- `Map` for node and record storage.
- `Set` for partitions and message deduplication.
- `Promise.allSettled()` for parallel replication.

### Event-driven architecture

The `Network` class emits events for:

- Network partitions.
- Successful deliveries.
- Network recovery.

Nodes emit events for local and replicated writes.

This separation makes communication and state transitions easier to observe.

### Asynchronous replication

The `broadcast()` method initiates deliveries concurrently.

`Promise.allSettled()` collects successful and failed outcomes without allowing one failed destination to discard the results from other destinations.

The cluster then evaluates the acknowledgement count.

### Idempotency

The receiver tracks message identifiers.

Repeated delivery of the same message identifier does not repeat its state-changing operation.

In production, deduplication records should be persisted and committed atomically with the corresponding state changes.

### Practical considerations

JavaScript is suitable for network-oriented services, asynchronous coordination, event processing, and distributed application gateways.

The implementation simulates network delivery within one Node.js process. It does not open real network connections or provide durable replication.

## 12. C++17 Implementation

**File:** `distributed_systems.cpp`

### Engineering approach

The C++ implementation concentrates on efficient state management and explicit quorum evaluation.

It uses:

| C++ capability | Application |
|---|---|
| `struct` | Version, record, and operation results |
| `class` | Nodes, cluster, and network |
| `unordered_map` | Node and record storage |
| `unordered_set` | Message deduplication |
| `set` | Deterministic network partition representation |
| `optional` | Missing-record representation |
| STL algorithms | Version selection and ordering |
| Exceptions | Failure and validation handling |

### Repository-independent governance of state

The cluster is responsible for evaluating whether an operation can proceed under its selected consistency policy.

A node does not independently declare that a distributed operation has succeeded merely because it has updated its local store.

The coordinator counts acknowledgements and returns an operation status.

### Version selection

The C++ implementation uses a comparison operator for version ordering.

The winning record is selected using `max_element()`.

This makes the conflict-resolution rule explicit and reusable.

### Anti-entropy

The cluster collects the newest version of each key into a merged map and applies it to reachable active nodes.

The map provides efficient key-based lookup.

### Performance considerations

- Hash maps provide expected constant-time key lookup.
- Version comparison takes constant time.
- Full snapshot reconciliation requires work proportional to the number of stored records and participating nodes.
- The in-memory implementation avoids serialization and network overhead, so its runtime is not representative of a real deployment.

The implementation uses standard C++17 facilities and does not require external libraries.

## 13. Java 17 Implementation

**File:** `DistributedSystems.java`

### Enterprise-oriented domain architecture

The Java implementation separates business concepts into explicit domain types and service objects.

Its main components include:

- `DistributedNode`
- `DistributedRecord`
- `DistributedOperation`
- `ConsistencyPolicy`
- `Network`
- `Cluster`
- `FailureDetector`

### Records and immutable data

Java records represent:

- `Version`
- `DistributedRecord`
- `NetworkMessage`

These types make the structure of distributed data explicit.

Immutable record values reduce accidental modification of state during communication.

### Consistency policy

The `ConsistencyPolicy` class encapsulates the acknowledgement rules.

The cluster uses the policy instead of embedding consistency calculations throughout the application.

### Operation state transitions

The distributed operation has four states:

    CREATED
       |
       v
    REPLICATING
       |
       +------> COMMITTED
       |
       +------> FAILED

An operation must enter the replication stage before it can be finalized.

An operation with insufficient acknowledgements is rejected.

### Concurrent data structures

The implementation uses:

- `ConcurrentHashMap` for shared node state.
- `ConcurrentHashMap.newKeySet()` for message deduplication.
- `AtomicLong` for logical-clock increments.

These structures support concurrent access to individual local data structures.

They do not automatically provide a distributed transaction across nodes.

### Practical considerations

Java provides a suitable foundation for enterprise services that require explicit domain modeling, policy enforcement, operational reporting, and structured exception handling.

The implementation models distributed communication locally rather than using real remote procedure calls or a persistent transport layer.

## 14. PostgreSQL Implementation

**File:** `distributed_systems.sql`

### Relational architecture

The SQL implementation stores the metadata required to describe distributed operations and replication workflows.

The schema contains:

| Table | Purpose |
|---|---|
| `clusters` | Distributed cluster configuration |
| `nodes` | Node identity, region, status, and logical clock |
| `network_links` | Connectivity and network characteristics |
| `distributed_operations` | Coordinator operations and acknowledgement requirements |
| `distributed_records` | Versioned local replica state |
| `network_messages` | Message delivery metadata |
| `processed_messages` | Idempotency tracking |
| `replication_acknowledgements` | Replication acknowledgement records |
| `node_heartbeats` | Node liveness observations |
| `consistency_policies` | Configurable consistency levels |

### Database integrity

The schema uses:

- Primary keys.
- Foreign keys.
- Unique constraints.
- Check constraints.
- Enumerated types.
- Partial indexes.
- GIN indexes.
- Triggers.

These controls protect relational metadata from invalid references and inconsistent values.

### Logical-clock function

`next_logical_clock()` increments a node's logical clock while considering an observed remote clock.

The update uses a row lock through the SQL update operation.

This prevents concurrent transactions from independently allocating the same next clock value for the same node.

### Replica application

`apply_replica()` compares incoming and stored versions.

It rejects older or equal versions and updates the local record when the incoming version wins.

The operation executes within the surrounding PostgreSQL transaction.

### Quorum evaluation

`quorum_eligibility()` evaluates the minimum acknowledgement count for ONE, QUORUM, and ALL.

The calculation depends on the cluster's configured replication factor.

### Distributed operation workflow

The SQL implementation separates:

1. Operation creation.
2. Local coordinator persistence.
3. Acknowledgement collection.
4. Finalization.
5. Reporting.

The functions `create_distributed_operation()`, `acknowledge_replication()`, and `finalize_distributed_operation()` implement these stages.

### Idempotent message processing

`process_message()` checks whether a message has already been processed.

The `processed_messages` primary key prevents duplicate processing records.

For production systems, message processing and business-state updates must be performed atomically in the same transaction.

### Anti-entropy reconciliation

`reconcile_cluster()` identifies the winning version for each key and attempts to apply it to active nodes.

The implementation uses PostgreSQL's `DISTINCT ON` capability to select the highest version for each record key.

### Important distinction

PostgreSQL transaction atomicity applies to the database transaction being executed.

It does not automatically extend to remote PostgreSQL servers.

The schema is a distributed-system metadata and workflow model, not an implementation of distributed consensus or a replacement for a real distributed storage engine.

## 15. Important Distributed-System Design Trade-offs

### 15.1 Strong consistency versus availability

| Design objective | Engineering implication |
|---|---|
| Strong consistency | May reject operations when coordination requirements cannot be satisfied |
| Higher availability | May permit operations under weaker consistency guarantees |
| Eventual consistency | Requires reconciliation and conflict-resolution rules |
| Strict quorum | Requires enough reachable members to satisfy the acknowledgement policy |

The appropriate policy depends on application requirements.

A financial transaction system may require stronger guarantees than an analytics platform that can tolerate temporarily stale information.

### 15.2 Replication versus coordination overhead

Increasing replication can improve resilience, but it increases the number of messages and acknowledgements involved in operations.

The replication factor should reflect:

- Failure tolerance.
- Storage capacity.
- Network characteristics.
- Read and write workload.
- Consistency requirements.

### 15.3 Full snapshots versus incremental synchronization

Full snapshots are straightforward to implement and useful for learning.

Their limitations become significant as datasets grow.

Incremental replication transfers only changes since a known version or synchronization position.

Merkle trees can help identify which portions of two datasets differ without comparing every record individually.

### 15.4 Last-Write-Wins versus business conflict resolution

Last-Write-Wins is deterministic but may discard legitimate concurrent changes.

Consider two nodes independently updating an inventory quantity.

| Node | Local quantity |
|---|---:|
| Node A | 100 |
| Node B | 90 |

Selecting one version does not necessarily produce the correct business result.

Inventory systems may need reservation transactions, atomic counters, conflict-free replicated data types, or centralized coordination.

The appropriate mechanism depends on the meaning of the stored data.

## 16. Security and Reliability Considerations

A production distributed system requires additional controls beyond those implemented in the simulators.

### Node authentication

Every participating node should have a verifiable identity.

Unauthenticated nodes must not be allowed to submit replication messages or participate in membership decisions.

### Transport security

Communication should use encrypted transport with certificate validation.

### Authorization

Different operations should have explicit permissions.

For example:

- Read replicated state.
- Write local state.
- Replicate records.
- Change membership.
- Modify consistency policies.
- Trigger reconciliation.

### Message validation

Incoming messages should be checked for:

- Valid sender.
- Authorized receiver.
- Valid message type.
- Payload size.
- Valid version.
- Message identifier.
- Replay conditions.

### Durable processing

A production system should persist:

- Accepted operations.
- Replication positions.
- Processed message identifiers.
- Acknowledgements.
- Recovery checkpoints.

In-memory deduplication is insufficient when nodes restart.

### Observability

Operational monitoring should include:

- Node availability.
- Heartbeat delays.
- Network latency.
- Packet loss.
- Replication lag.
- Quorum failures.
- Message retry counts.
- Divergent replica counts.
- Reconciliation duration.
- Storage utilization.

## 17. Algorithmic Complexity

Let:

- \(N\) = number of nodes.
- \(K\) = number of records per node.
- \(R\) = replication factor.
- \(M\) = number of messages.

| Operation | Approximate complexity |
|---|---|
| Hash-based local lookup | Expected \(O(1)\) |
| Local record insertion | Expected \(O(1)\) |
| Version comparison | \(O(1)\) |
| Quorum calculation | \(O(1)\) |
| Replica selection by sorting | \(O(R\log R)\) |
| Full snapshot collection | \(O(NK)\) |
| Full snapshot reconciliation | Approximately \(O(NK)\), excluding storage and communication overhead |
| Message deduplication lookup | Expected \(O(1)\) |
| Network connectivity lookup | Expected \(O(1)\) with hash-based representations |

Actual distributed-system performance also depends on network latency, serialization cost, message scheduling, storage I/O, contention, and failure-recovery overhead.

## 18. Testing and Validation

The implementations include executable tests for important distributed-system conditions.

| Test | Expected behavior |
|---|---|
| Basic write | Record is created |
| Replication | Reachable replicas receive the update |
| Quorum write | Required acknowledgements are obtained |
| Partition | Insufficient quorum causes rejection |
| Node shutdown | Unavailable node is excluded |
| Node recovery | Node becomes eligible for synchronization |
| Duplicate message | Repeated delivery is ignored |
| Stale update | Older version cannot replace a newer version |
| Anti-entropy | Reachable replicas converge |
| Failure detection | Expired heartbeat is identified |
| Invalid configuration | Invalid node or policy settings are rejected |

The tests validate the modeled mechanisms, not the correctness of a production consensus protocol.

## 19. Execution Requirements

| File | Runtime or environment | Execution |
|---|---|---|
| Python | Python 3.10+ | `python distributed_systems.py` |
| JavaScript | Node.js 18+ | `node distributed_systems.js` |
| C++17 | C++17 compiler | `g++ -std=c++17 -O2 -Wall -Wextra -pedantic distributed_systems.cpp -o distributed_systems` |
| Java | JDK 17 | `javac DistributedSystems.java` followed by `java -ea DistributedSystems` |
| PostgreSQL | PostgreSQL 18+ | `psql -d database_name -f distributed_systems.sql` |

The Python, JavaScript, C++, and Java programs are independent executable simulations.

The PostgreSQL implementation requires a database role with permission to create the schema objects.

The Java program uses assertions for its test suite. The `-ea` option enables assertion checking.

## 20. Technical Limitations

The implementations deliberately use simplified in-memory communication and replication models.

They do not implement:

- Raft consensus.
- Paxos consensus.
- Byzantine fault tolerance.
- Real inter-process network communication.
- Distributed transactions across independent database servers.
- Durable distributed logs.
- Production-grade leader election.
- Dynamic replica placement.
- Consistent hashing.
- Vector clocks.
- Merkle-tree synchronization.
- Automatic split-brain prevention.
- Production authentication and encryption.
- Exactly-once end-to-end message processing.

Quorum acknowledgement, deterministic conflict resolution, and eventual convergence are distinct mechanisms. None should be treated as a complete substitute for a formally specified distributed consistency protocol.

The central engineering challenge is maintaining useful application behavior while independent nodes operate with incomplete, delayed, or conflicting information.
