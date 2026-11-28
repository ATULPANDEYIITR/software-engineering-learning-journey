# Distributed Messaging: Queues, Streams, and Delivery Guarantees

## 1. Distributed Messaging Architecture

Distributed messaging enables independent applications, services, and processing systems to exchange information without requiring both sides to execute simultaneously.

A producer creates a message or event. A messaging system accepts, stores, routes, and delivers it. A consumer processes the delivered information and communicates successful processing through an acknowledgement or committed offset.

The architecture separates message production from message consumption.

### Core components

| Component | Responsibility |
|---|---|
| Producer | Creates and publishes messages |
| Broker | Accepts, stores, and routes messages |
| Topic | Logical destination for messages or events |
| Queue | Stores work awaiting consumption |
| Stream | Maintains an ordered event log |
| Partition | Divides a stream into independently processed sequences |
| Consumer | Processes messages or events |
| Consumer group | Coordinates consumers sharing a workload |
| Offset | Identifies a position in a partition |
| Acknowledgement | Confirms successful queue processing |
| Dead-letter queue | Isolates messages that exceed retry limits |
| Idempotency store | Prevents duplicate business effects |

A typical architecture follows this relationship:

Producer
    |
    v
Messaging Broker
    |
    +----------------------+
    |                      |
    v                      v
Message Queue         Event Stream
    |                      |
    v                      v
Competing Consumers   Consumer Groups
    |                      |
    v                      v
Acknowledgement       Offset Commit
    |                      |
    v                      v
Business Processing   Event Processing
    |                      |
    +----------+-----------+
               |
               v
       Monitoring and Recovery

## 2. Message Queues

A message queue is primarily designed to distribute work between producers and consumers.

A producer publishes a message to a queue. A consumer receives that message, performs an operation, and acknowledges successful processing.

The queue generally removes or marks the message as completed after acknowledgement, subject to the broker's retention and implementation policies.

### Point-to-point messaging

In point-to-point messaging, multiple consumers can compete for messages from the same queue.

For example, an e-commerce application may generate payment requests. Several payment workers process the requests independently.

If three workers consume the same queue, each available message is normally assigned to one worker at a time.

    Payment Service
          |
          v
     Payment Queue
          |
     +----+----+
     |    |    |
     v    v    v
    W1   W2   W3

This architecture supports workload distribution and horizontal scaling.

### Queue delivery lifecycle

A typical message progresses through these states:

| State | Meaning |
|---|---|
| Pending | Waiting for a consumer |
| In-flight | Delivered but not acknowledged |
| Acknowledged | Successfully completed |
| Dead-lettered | Failed beyond the permitted retry policy |

A typical lifecycle is:

Pending → In-flight → Acknowledged

A failure produces an alternative path:

Pending → In-flight → Pending → In-flight

After retry exhaustion:

Pending → In-flight → Dead-lettered

An unacknowledged delivery may also be returned to the queue after a consumer crash or visibility timeout.

### Competing consumers

Competing consumers allow several worker processes to share a queue.

The broker must coordinate message ownership to avoid simultaneous delivery of the same active queue record.

The PostgreSQL implementation uses `FOR UPDATE SKIP LOCKED` when claiming deliveries. This allows independent database workers to claim different available records without waiting for records already locked by other workers.

### Acknowledgement

Acknowledgement communicates that a consumer has completed processing.

Two important operations are:

- ACK: confirms successful processing.
- NACK: rejects a delivery and requests retry or dead-letter routing.

An acknowledgement should be associated with the correct delivery and consumer ownership.

Acknowledging before processing creates a risk of message loss. Acknowledging after processing creates a risk of duplicate delivery if the consumer crashes after completing its business operation but before acknowledging.

This distinction determines the delivery guarantee.

## 3. Event Streams

An event stream is an append-oriented sequence of records representing events that have occurred.

Unlike a conventional work queue, a stream retains events for a defined period or according to a storage policy. Multiple consumer groups can independently read the same events.

Examples include:

- Customer registration events.
- Payment completion events.
- Inventory updates.
- Application activity records.
- Financial transaction events.
- System monitoring events.

### Stream structure

A stream can contain several partitions.

    Orders Stream
         |
    +----+----+
    |    |    |
    v    v    v
    P0   P1   P2
    |    |    |
    v    v    v
    E0   E0   E0
    E1   E1   E1
    E2   E2   E2

Each partition maintains its own sequence of offsets.

An offset identifies the position of an event within a particular partition.

For example:

| Partition | Offset | Event |
|---|---:|---|
| 0 | 0 | Order created |
| 0 | 1 | Order confirmed |
| 0 | 2 | Payment completed |
| 1 | 0 | Customer registered |
| 1 | 1 | Address updated |

Offsets are partition-specific. Offset 2 in partition 0 does not identify the same event as offset 2 in partition 1.

### Partitioning

Partitioning distributes stream storage and processing across multiple workers.

A partitioning strategy commonly uses a message key.

For example, all events associated with the same customer can be routed to the same partition.

This supports ordering for events with the same key, provided the producer, broker, and consumer preserve the relevant ordering guarantees.

Partitioning introduces an important tradeoff:

- More partitions provide greater potential processing parallelism.
- Fewer partitions simplify coordination and resource management.
- Events in different partitions do not automatically have a global ordering relationship.

### Consumer groups

A consumer group represents an independent processing application or workload.

Consider an order stream with two consumer groups:

| Consumer group | Responsibility |
|---|---|
| Analytics | Calculate business metrics |
| Billing | Process financial events |

Both groups can consume the same stream independently.

Analytics committing an offset does not advance the billing group's offset.

This independence supports multiple applications without requiring duplicate event publication.

### Offset management

A consumer reads events starting at its committed offset.

After successful processing, it commits the next position from which it should continue.

For example:

- Committed offset: 5
- Events processed: offsets 5, 6, and 7
- Next committed offset: 8

The committed offset represents the next event position, not the last processed event number.

Offset management enables:

- Restarting after failure.
- Resuming processing.
- Independent consumer progress.
- Historical replay.
- Controlled recovery.

### Event replay

Replay means resetting a consumer group's reading position to an earlier offset.

For example, an analytics application may need to recalculate a report after its processing logic changes.

It can restart consumption from an earlier position without requiring the producer to publish the events again.

Replay requires sufficient event retention. If an event has been deleted, its original content cannot be recovered through offset management alone.

## 4. Delivery Guarantees

Delivery guarantees describe the relationship between message delivery, processing, acknowledgement, and duplicate handling.

Three commonly discussed guarantees are at-most-once, at-least-once, and exactly-once.

### At-most-once delivery

At-most-once processing prioritizes avoiding duplicate delivery at the expense of possible message loss.

The consumer acknowledges before processing.

    Receive
       |
       v
    Acknowledge
       |
       v
    Process

If the consumer crashes after acknowledgement but before processing, the message may be lost.

Characteristics:

- A message is processed zero or one times.
- Duplicate processing is avoided through early acknowledgement.
- Processing failure can cause permanent loss.
- Appropriate when occasional loss is acceptable.

### At-least-once delivery

At-least-once processing prioritizes successful delivery and recovery.

The consumer processes a message before acknowledging it.

    Receive
       |
       v
    Process
       |
       v
    Acknowledge

If processing succeeds but acknowledgement fails, the broker may deliver the message again.

Characteristics:

- A message can be delivered multiple times.
- Messages are retried after failures.
- Duplicate processing must be handled.
- Idempotent business operations are important.

This is a common practical choice for payment workflows, order processing, and background jobs.

### Exactly-once processing

Exactly-once processing aims to ensure that a logical event produces one committed business effect, even when delivery is repeated.

It is important to distinguish exactly-once delivery from exactly-once business processing.

A broker may support transactional publishing, transactional consumption, or atomic offset and output commits. Those guarantees do not automatically extend to arbitrary external databases, payment gateways, email providers, or HTTP services.

A robust implementation requires an atomic boundary.

One common approach is:

1. Receive the message.
2. Start a database transaction.
3. Insert the message identifier into an idempotency table.
4. Reject the operation if that identifier already exists.
5. Apply the business update.
6. Commit the transaction.
7. Acknowledge the message.

The idempotency record and business update must commit together.

| Guarantee | Duplicate delivery | Message loss risk | Typical mechanism |
|---|---|---|---|
| At-most-once | Prevented by delivery strategy | Possible | Acknowledge before processing |
| At-least-once | Possible | Reduced through retries | Process before acknowledgement |
| Exactly-once effect | Repeated delivery may occur | Controlled within the transaction boundary | Deduplication and atomic commit |

Exactly-once guarantees must always be described with their scope and transaction boundaries.

## 5. Idempotency and Deduplication

An operation is idempotent when repeating it produces the same final result as executing it once.

For example, setting an account status to `ACTIVE` is naturally idempotent.

Adding ₹1,000 to an account balance is not naturally idempotent. Executing the same operation twice adds ₹2,000.

An idempotency key identifies a logical operation independently of the number of delivery attempts.

Example:

| Message ID | Processing attempt | Result |
|---|---:|---|
| MSG-100 | 1 | Applied |
| MSG-100 | 2 | Duplicate ignored |
| MSG-100 | 3 | Duplicate ignored |
| MSG-101 | 1 | Applied |

The Python implementation uses a set of processed message identifiers and a synchronized business-state update.

The JavaScript implementation uses an idempotency store.

The C++ implementation models deduplication using an STL set.

The Java implementation uses a synchronized service and a set of UUID values.

The PostgreSQL implementation enforces uniqueness through a composite primary key on `(group_id, message_id)`.

For production systems, a database-backed idempotency record should have an appropriate retention period and a clearly defined transaction boundary.

## 6. Retry Policies and Dead-Letter Queues

Retries provide another opportunity to process a failed message.

Not all failures should be treated equally.

| Failure category | Example | Typical handling |
|---|---|---|
| Transient | Temporary network failure | Retry |
| Resource-related | Database unavailable | Retry with backoff |
| Rate limiting | HTTP 429 | Delay and retry |
| Permanent | Invalid account identifier | Dead-letter |
| Poison message | Invalid serialized payload | Dead-letter |
| Authentication | Invalid credentials | Alert and investigate |

### Exponential backoff

Immediate repeated retries can increase pressure on an already failing service.

Exponential backoff increases the delay between successive attempts.

A basic formula is:

\[
D_n = \min(D_{\max},D_0 \times 2^n)
\]

Where:

- \(D_n\) is the retry delay.
- \(D_0\) is the initial delay.
- \(D_{\max}\) is the maximum delay.
- \(n\) is the retry number.

Production systems commonly add random jitter to prevent many consumers from retrying simultaneously.

### Dead-letter queues

A dead-letter queue stores messages that cannot be processed within the configured retry policy.

A dead-letter record should preserve:

- Original message identifier.
- Original payload or a secure reference to it.
- Failure reason.
- Attempt count.
- Original destination.
- Failure timestamp.

Dead-letter processing should include monitoring, investigation, controlled replay, and auditability.

Repeatedly requeueing a poison message without changing its cause can prevent other messages from progressing.

## 7. Ordering and Concurrency

Message ordering is not a universal property of distributed messaging.

A single queue may preserve a defined enqueue order under its broker's delivery conditions, but multiple consumers can complete processing in a different order.

Streams generally preserve append order within individual partitions.

They do not provide a global order across independently processed partitions.

### Ordering strategies

| Strategy | Ordering characteristic |
|---|---|
| Single consumer | Simplifies processing order |
| Partition by entity key | Preserves partition assignment for related keys |
| Sequence numbers | Allows detection of gaps and reordering |
| Serialized processing | Reduces concurrent execution |
| Version checks | Rejects outdated state transitions |

For financial or inventory systems, ordering may be important for events associated with the same account or product.

Parallel processing must not violate business invariants.

## 8. Backpressure and Throughput

Backpressure prevents producers from overwhelming consumers.

A system should monitor queue depth, processing latency, consumer lag, failure rates, and available capacity.

Important techniques include:

- Bounded queue capacity.
- Batch consumption.
- Consumer concurrency limits.
- Producer rate limiting.
- Adaptive polling.
- Retry scheduling.
- Partition-level workload distribution.

### Consumer lag

Consumer lag measures the difference between the latest available stream position and the consumer's committed offset.

\[
Lag = LatestOffset - CommittedOffset
\]

A rising lag may indicate:

- Insufficient consumer capacity.
- Increased event production.
- Slow business processing.
- Repeated failures.
- An unavailable consumer.

The PostgreSQL implementation exposes lag through `consumer_lag_view`.

### Performance considerations

Let:

- \(P\) = number of partitions.
- \(C\) = number of active consumers.
- \(\lambda\) = incoming messages per second.
- \(\mu\) = processing capacity per consumer.

A simplified processing capacity estimate is:

\[
Capacity \approx \min(P,C)\times\mu
\]

This assumes that consumers can process their assigned partitions independently and that the broker and downstream systems are not bottlenecks.

A stable system generally requires sufficient processing capacity to handle the incoming rate.

Batching can reduce network and transaction overhead, but excessively large batches increase memory consumption and recovery costs.

## 9. Implementation Architecture

The five source implementations use different engineering approaches to represent the same messaging concepts.

### Python

The Python implementation focuses on workflow simulation and domain behavior.

| Module | Responsibility |
|---|---|
| `Message` | Validated immutable message representation |
| `MessageQueue` | Queue lifecycle and delivery state |
| `EventStream` | Partitioned event storage and offsets |
| `Consumer` | Delivery guarantee behavior |
| `IdempotentProcessor` | Duplicate prevention and business updates |
| `save_stream` | Snapshot persistence |

Python's `deque` supports efficient queue operations. Dictionaries provide indexed delivery tracking, and sets provide efficient duplicate detection.

`RLock` protects shared state in the local demonstration.

The JSON snapshot is intended for learning and is not a substitute for a durable replicated event log.

### JavaScript

The JavaScript implementation emphasizes asynchronous and event-driven processing.

| Module | Responsibility |
|---|---|
| `Message` | Message validation and immutable metadata |
| `MessageQueue` | Queue operations and event notifications |
| `EventStream` | Partition assignment and independent offsets |
| `Consumer` | Asynchronous message processing |
| `IdempotencyStore` | Duplicate detection |
| `EventEmitter` | Operational event notifications |

Node.js asynchronous functions and Promises allow processing logic to perform non-blocking operations.

The implementation uses bounded queue capacity and explicit consumer shutdown behavior.

Its in-memory idempotency model is limited to a single JavaScript execution context. Distributed workers require persistent atomic deduplication.

### C++17

The C++ implementation emphasizes explicit state management, domain modeling, and predictable container operations.

| Component | Responsibility |
|---|---|
| `Message` | Message data structure |
| `Delivery` | Delivery lifecycle |
| `MessageQueue` | Pending and in-flight tracking |
| `EventStream` | Partition and offset management |
| `IdempotentProcessor` | Deduplication |
| `DeliveryService` | Processing and acknowledgement coordination |

STL containers serve distinct purposes:

- `deque` supports queue operations.
- `unordered_map` indexes in-flight messages.
- `vector` stores partitions and dead-letter records.
- `map` stores ordered consumer-group metadata.
- `set` maintains processed message identifiers.

`optional` represents the absence of a deliverable message.

Exceptions communicate invalid states and processing failures.

### Java 17

The Java implementation emphasizes enterprise domain modeling and explicit service responsibilities.

| Component | Responsibility |
|---|---|
| `Message` record | Immutable message representation |
| `Delivery` | Mutable delivery state |
| `QueuePolicy` record | Retry and capacity configuration |
| `MessageQueue` | Synchronized queue management |
| `ConsumerGroup` | Committed offset management |
| `EventStream` | Partitioned event log |
| `IdempotencyService` | Transactional processing simulation |
| `ConsumerService` | Consumer lifecycle |

Java records provide compact immutable data structures.

Synchronized service operations protect shared state in the local demonstration.

An enterprise deployment would normally replace in-memory synchronization with broker coordination, durable storage, and database transactions.

### PostgreSQL

The SQL implementation provides a relational representation of a messaging system.

| Database object | Responsibility |
|---|---|
| `topics` | Transport and retention configuration |
| `producers` | Publishing identities |
| `consumer_groups` | Independent processing groups |
| `messages` | Message metadata and payload |
| `queue_deliveries` | Queue delivery state |
| `stream_events` | Partitioned event records |
| `consumer_offsets` | Committed stream positions |
| `processed_messages` | Idempotency records |
| `payment_ledger` | Business processing records |
| `dead_letter_messages` | Failed delivery records |

The implementation uses constraints, foreign keys, indexes, triggers, views, functions, and procedures.

`publish_queue_message` creates queue messages and corresponding consumer deliveries.

`publish_stream_event` assigns events to partitions and allocates offsets.

`claim_queue_message` uses row locking and `SKIP LOCKED` for competing workers.

`acknowledge_delivery` validates the worker holding the delivery.

`reject_delivery` implements retry and dead-letter transitions.

`commit_stream_offset` validates consumer progress.

`process_payment_once` combines idempotency and business processing within a database transaction.

## 10. PostgreSQL Data Relationships

The relational model follows these relationships:

    Topics
      |
      +---- Producers
      |
      +---- Messages
      |       |
      |       +---- Queue Deliveries
      |       |       |
      |       |       +---- Dead-Letter Messages
      |       |
      |       +---- Stream Events
      |
      +---- Consumer Groups
              |
              +---- Consumer Offsets
              |
              +---- Processed Messages
                         |
                         +---- Payment Ledger

A topic defines the messaging destination.

Messages contain the published information.

Queue deliveries represent individual processing obligations for consumer groups.

Stream events represent immutable event positions.

Consumer offsets record independent stream progress.

Processed-message records prevent duplicate business operations.

The payment ledger demonstrates how messaging processing can produce auditable business records.

## 11. Failure Recovery and Transaction Boundaries

Distributed systems must account for partial failures.

A consumer may complete a business operation and crash before acknowledging the message.

A producer may publish successfully but fail before receiving confirmation.

A consumer may restart with an outdated offset.

A network partition may temporarily prevent communication with the broker.

A downstream service may process a request while the caller receives a timeout.

These scenarios require carefully defined recovery behavior.

### Transactional outbox

The transactional outbox pattern addresses consistency between a business database update and message publication.

Instead of updating business data and publishing directly to a broker as two unrelated operations, an application writes an outbox record in the same database transaction as the business change.

A separate publisher reads committed outbox records and publishes them.

    Business Request
          |
          v
    Database Transaction
          |
          +---- Business Update
          |
          +---- Outbox Record
          |
          v
    Outbox Publisher
          |
          v
    Message Broker
          |
          v
    Consumer

The publisher may publish the same outbox record more than once if confirmation is lost. Consumer-side idempotency remains important.

### Transactional consumption

A database transaction can combine:

1. Deduplication record insertion.
2. Business state update.
3. Processing-result persistence.

The transaction must either commit all three operations or roll them all back.

An external API call cannot automatically participate in this local database transaction. Such integrations require idempotency keys, transactional messaging patterns, or compensating operations.

## 12. Security and Reliability

Distributed messaging infrastructure can expose sensitive information and operational capabilities.

Important security controls include:

| Control | Purpose |
|---|---|
| Authentication | Verifies producer and consumer identity |
| Authorization | Restricts topic and queue access |
| TLS | Protects communication in transit |
| Encryption at rest | Protects stored messages |
| Payload validation | Prevents malformed input |
| Size limits | Controls memory and storage consumption |
| Audit logging | Records important operations |
| Secret management | Protects credentials and encryption keys |
| Retention policies | Limits unnecessary data storage |
| Dead-letter access controls | Restricts sensitive failed messages |

Production deployments should also consider:

- Broker replication.
- Durable storage.
- Leader election.
- Partition reassignment.
- Consumer heartbeats.
- Delivery leases.
- Network timeouts.
- Monitoring and alerting.
- Disaster recovery.
- Schema evolution.
- Access to replay operations.

The local implementations simulate messaging behavior. They do not provide replicated broker storage, distributed consensus, network-level delivery, or production-grade authentication.

## 13. Failure Scenarios and Expected Behavior

| Scenario | Expected behavior |
|---|---|
| Consumer crashes before processing | Recover or redeliver the message |
| Consumer crashes after processing but before ACK | Redelivery with idempotency protection |
| Invalid payload | Reject or route to dead-letter storage |
| Retry limit exceeded | Dead-letter the message |
| Duplicate message | Detect and avoid duplicate business effects |
| Consumer group restarts | Resume from committed offsets |
| Consumer requests historical data | Replay from an earlier offset |
| Queue capacity exceeded | Apply backpressure |
| One stream partition falls behind | Monitor partition-specific lag |
| Producer is disabled | Reject publication |
| Consumer attempts unauthorized ACK | Reject acknowledgement |
| Database transaction fails | Roll back related business updates |

## 14. Complexity and Performance

The implementations use appropriate data structures for their respective operations.

| Operation | Typical complexity |
|---|---|
| Python deque append/pop | O(1) |
| Python set membership | O(1) average |
| JavaScript Map lookup | O(1) average |
| C++ unordered_map lookup | O(1) average |
| Java HashSet lookup | O(1) average |
| Stream append to in-memory partition | O(1) amortized |
| Sequential batch retrieval | O(B), where B is batch size |
| PostgreSQL indexed message lookup | Approximately O(log N) |
| PostgreSQL unique-key validation | Index-dependent |
| Partition offset retrieval | O(log N) with suitable indexing |

Actual distributed-system performance also depends on network latency, replication, serialization, storage throughput, transaction overhead, message size, and consumer concurrency.

## 15. Practical Distinctions

The three delivery concepts solve different problems and should not be treated as interchangeable.

| Dimension | Queue | Stream |
|---|---|---|
| Primary purpose | Distribute work | Retain and distribute events |
| Consumption | Competing consumers | Independent consumer groups |
| Completion tracking | Acknowledgement | Offset commit |
| Historical replay | Depends on retention and broker support | Core stream capability |
| Processing position | Delivery state | Partition offset |
| Typical application | Background jobs | Event-driven analytics |
| Ordering | Broker-dependent | Within a partition |

Similarly, delivery guarantees describe processing semantics rather than the transport type.

A queue can provide at-least-once delivery. A stream consumer can also process events at least once. Both can use idempotency to protect business operations.

The correct design depends on the application's ordering requirements, recovery strategy, processing cost, retention requirements, and tolerance for duplicate delivery.
