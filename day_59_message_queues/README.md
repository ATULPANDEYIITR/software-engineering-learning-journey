# Message Queues: Producers, Consumers, and Asynchronous Processing

## Scope

This project models message queues as an asynchronous processing system in which producers publish work, queues retain messages, consumers retrieve work, processing succeeds or fails, and failed messages can be retried or moved to a dead-letter path.

The implementation separates six important responsibilities:

| Component | Responsibility |
|---|---|
| Producer | Creates and publishes messages |
| Queue | Buffers messages between producers and consumers |
| Consumer | Retrieves messages and performs business processing |
| Acknowledgement | Records successful processing |
| Retry mechanism | Makes recoverable failures available again |
| Dead-letter handling | Isolates messages that repeatedly fail |

A useful domain relationship is:

`Producer → Queue → Message → Consumer → Processing Result → Acknowledgement / Retry → Dead Letter`

The examples use orders, payments, notifications, and repository-development governance to show that message queues are infrastructure mechanisms rather than business logic by themselves.

## Core Concepts

### Message Queues

A message queue decouples the component producing work from the component processing it.

A producer does not need to execute the consumer's work synchronously. Instead, it publishes a message and continues. The consumer can process the message later.

This separation provides several useful properties:

- Temporal decoupling: producer and consumer do not need to run at the same time.
- Load buffering: a queue can absorb short periods of consumer overload.
- Independent scaling: consumers can be increased without changing producers.
- Failure isolation: a temporary consumer or dependency failure does not necessarily stop producers.
- Retry capability: recoverable failures can be processed again.
- Work distribution: multiple consumers can share queued work.

A queue does not automatically make a system reliable. Reliability depends on acknowledgement semantics, persistence, retry policy, idempotency, ordering requirements, monitoring, access control, and failure handling.

## Producers

A producer converts a business event or task into a message.

The Python implementation uses the `Message` dataclass to validate a topic and structured payload before publication. The JavaScript implementation uses immutable payload data and runtime validation. The C++ and Java implementations use strongly typed message objects.

A production producer should normally validate:

- Topic or routing destination.
- Required business identifiers.
- Payload structure.
- Payload size.
- Serialization format.
- Authentication and authorization context.
- Correlation or trace identifiers where required.

The producer should not assume that a successful publish means the business operation has already been completed. Publication only establishes that work has been accepted by the messaging layer.

## Consumers

A consumer retrieves messages and executes the corresponding business operation.

The Python example models an order worker. The JavaScript implementation uses an asynchronous worker. The Java implementation separates the message broker from enterprise policy services. The C++ program models explicit message state and bounded retry behavior.

A consumer must distinguish at least these situations:

| Situation | Appropriate behavior |
|---|---|
| Successful processing | Acknowledge |
| Temporary dependency failure | Retry |
| Invalid message | Reject or dead-letter according to policy |
| Repeated failure | Dead-letter |
| Duplicate delivery | Execute idempotently |
| Queue unavailable | Apply operational retry/backoff |

Consumer concurrency changes throughput but also creates race conditions if business state is not protected correctly.

## Message Lifecycle

The examples use a state model similar to:

`READY → PROCESSING → ACKNOWLEDGED`

A failure can produce:

`PROCESSING → READY`

after a retry is scheduled.

Repeated failures eventually produce:

`PROCESSING → DEAD_LETTERED`

The Python implementation exposes these states through `MessageState`. JavaScript uses a frozen state object. C++ uses an enum. Java uses an enum for the same domain concept.

A message should not normally be acknowledged before its required business operation has succeeded. Acknowledging too early can cause message loss from the perspective of the application.

## Acknowledgements

Acknowledgement is the consumer's explicit indication that processing completed successfully.

The Python queue rejects acknowledgement when the message is not in `PROCESSING` state. The JavaScript queue applies the same state restriction. These checks prevent invalid lifecycle transitions.

A practical consumer sequence is:

1. Receive message.
2. Mark or reserve it as being processed.
3. Validate the message.
4. Perform the business operation.
5. Persist required business state.
6. Acknowledge the message.

The exact ordering depends on the messaging system and its delivery guarantees.

## At-Least-Once Delivery and Idempotency

The retry implementations deliberately permit the possibility that a message may be delivered more than once.

At-least-once processing is common because systems generally prefer retrying uncertain work to silently losing it. The consequence is that consumers must tolerate duplicates.

An idempotent operation produces the same intended business state when the same logical message is processed repeatedly.

A common database pattern is to store a unique message identifier:

`message_id → processed result`

Before applying a non-repeatable side effect, the consumer can check whether that identifier has already been processed.

Idempotency is especially important when a consumer performs:

- Payments.
- Inventory changes.
- Notifications.
- External API calls.
- Account updates.
- Financial transactions.

## Retry Handling

Retries are useful for transient failures such as:

- Temporary network failures.
- Rate limiting.
- Database contention.
- Short-lived service outages.
- Dependency restarts.

The implementations use bounded retry counts. An unlimited retry loop is unsafe because one permanently invalid message can consume worker capacity indefinitely.

A production retry policy normally considers:

- Maximum attempts.
- Initial delay.
- Exponential backoff.
- Jitter.
- Failure classification.
- Maximum retry age.
- Dead-letter destination.
- Operational alerting.

The Python example uses a small retry delay. The JavaScript worker waits asynchronously. The C++ and Java models count attempts and transition repeatedly failing messages toward a dead-letter state.

## Dead-Letter Processing

A dead-letter queue or equivalent dead-letter store isolates messages that cannot be processed successfully.

A dead-lettered message should retain enough diagnostic information to investigate the failure:

- Original message identifier.
- Topic.
- Original payload or secure reference to it.
- Attempt count.
- Failure reason.
- Timestamps.
- Consumer identity.
- Correlation identifier.

Dead-lettering is not a substitute for monitoring. A growing dead-letter population indicates that the system requires investigation.

Sensitive payloads should not be copied into unrestricted logs. Access to dead-letter data should follow least-privilege rules.

## Python Implementation

The Python file implements an in-memory queue with:

- Dataclasses for messages.
- Enum-based message states.
- FIFO storage.
- Queue capacity enforcement.
- Payload validation.
- Consumer handlers.
- Acknowledgement.
- Bounded retries.
- Dead-letter storage.
- Operational counters.
- Failure demonstrations.

`MessageQueue.consume()` selects a ready message and changes its state to `PROCESSING`.

`acknowledge()` accepts only processing messages.

`reject()` either schedules another attempt or moves the message to the dead-letter collection after the configured attempt limit.

The example contains two workflows. Order processing demonstrates successful asynchronous work. Payment processing demonstrates repeated downstream failure and dead-letter handling.

The implementation intentionally avoids external dependencies. It is a learning-scale in-memory model rather than a replacement for a distributed broker.

## JavaScript Implementation

The JavaScript file uses Node.js standard-library functionality and emphasizes asynchronous processing.

`EventEmitter` exposes queue lifecycle events such as publication, consumption, acknowledgement, retry scheduling, and dead-lettering.

The worker invokes asynchronous handlers and waits for them with `await`. This models a realistic Node.js consumer in which message processing can include network or database operations.

The JavaScript implementation also uses:

- `Map`-compatible structured state patterns.
- `Set`-style domain validation concepts.
- `Promise`-based asynchronous delays.
- `crypto.randomUUID()` for message identifiers.
- Immutable message payloads.
- Event-driven observability.

The queue uses an array and a ready-message search. This is intentionally simple. A production implementation would normally use the ordering and delivery semantics provided by the selected messaging infrastructure rather than implementing broker persistence in application memory.

## C++17 Implementation

The C++ program provides a systems-oriented model.

`MessageBroker` uses an STL queue for FIFO delivery and a vector for dead-lettered messages. `MessageState` provides explicit lifecycle states.

The implementation uses exceptions for invalid broker operations and validates broker limits during construction.

The program also includes a separate repository-governance case study to demonstrate how asynchronous processing infrastructure can coexist with repository workflows without conflating the two domains.

The governance engine evaluates:

- Pull Request state.
- Draft status.
- Source and target branches.
- Commit presence.
- Merge conflicts.
- Required status checks.
- Reviewer eligibility.
- Approval count.
- Resolved conversations.
- Protected target branches.

The governance model is deliberately separate from the message broker. Message delivery is an asynchronous transport concern, while merge eligibility is a repository-policy concern.

Common operations on the in-memory FIFO queue are constant time for insertion and removal. The design does not implement persistence, distributed coordination, network transport, or broker replication.

## Java 17 Implementation

The Java implementation models an enterprise service layer.

Records provide immutable representations for:

- Messages.
- Status checks.
- Reviews.
- Branch protection policies.
- Pull Requests.

The `ApprovalPolicyService` evaluates valid approvals independently from the merge-eligibility service. This prevents approval semantics from being mixed with the final policy decision.

An approval counts only when:

- The reviewer is eligible.
- The review state is `APPROVED`.
- The approval is not stale.

The `MergeEligibilityService` evaluates the complete policy:

`Pull Request state → synchronization → conflicts → conversations → status checks → valid approvals`

The message broker separately models bounded retries and dead-lettering.

Custom exceptions represent merge-policy failures rather than returning ambiguous boolean values alone.

## PostgreSQL Implementation

The PostgreSQL script models both messaging infrastructure and a repository-governance domain.

The messaging model contains:

- `message_queues`
- `consumers`
- `messages`
- `message_attempts`
- `dead_letters`

The repository model contains:

- `repositories`
- `branches`
- `commits`
- `pull_requests`
- `pull_request_commits`
- `reviewers`
- `reviews`
- `review_comments`
- `status_checks`
- `branch_protection_policies`
- `approval_requirements`

Foreign keys preserve relationships between entities. Check constraints prevent invalid values such as negative attempts or empty topics.

The partial index on ready messages supports worker-oriented queue retrieval without indexing every message state equally.

`FOR UPDATE SKIP LOCKED` demonstrates an important PostgreSQL pattern for concurrent workers. Multiple consumers can attempt to claim ready rows without waiting for rows already locked by another worker.

The `enqueue_message()` function validates the destination queue and configured payload-size limit before inserting a message.

The `validate_message_attempt()` trigger prevents a message from exceeding its configured retry limit.

`acknowledge_message()` enforces a valid state transition from `processing` to `acknowledged`.

## Transactional Message Processing

Database-backed consumers should consider transaction boundaries carefully.

A common relational pattern is:

`BEGIN → claim message → update business state → record processing result → COMMIT`

If the transaction rolls back, the business update and message-state update can be rolled back together.

This does not automatically make external API calls transactional. If the consumer calls an external system inside a database transaction, the external operation cannot normally be rolled back by PostgreSQL.

For operations spanning a database and an external system, designs such as an outbox pattern, idempotency keys, or compensating operations may be required.

## Ordering

Queue ordering is not universally guaranteed.

Even if a broker provides FIFO ordering, concurrency can cause processing completion to occur in a different order.

For example:

`Message A → Consumer 1`
`Message B → Consumer 2`

Consumer 2 may finish before Consumer 1.

If strict ordering is required, the design must constrain concurrency or partition messages by an ordering key.

The examples use simple FIFO structures but do not claim global ordering across concurrent consumers.

## Backpressure

Backpressure occurs when producers generate work faster than consumers can process it.

Without controls, backlog can grow until memory, storage, or broker limits are reached.

Useful controls include:

- Queue capacity limits.
- Producer rate limiting.
- Consumer autoscaling.
- Maximum payload size.
- Consumer concurrency limits.
- Dead-letter handling.
- Monitoring queue depth.
- Alert thresholds.

The Python and JavaScript examples explicitly enforce queue capacity.

## Failure Modes

Important failure scenarios include:

| Failure | Typical control |
|---|---|
| Consumer crashes | Redelivery or visibility timeout |
| Temporary dependency failure | Retry with backoff |
| Permanent invalid message | Dead-letter |
| Duplicate delivery | Idempotency |
| Queue overload | Backpressure |
| Large payload | Payload-size limit |
| Unauthorized producer | Authentication and authorization |
| Unauthorized consumer | Queue-level access control |
| Poison message | Bounded retries and dead-lettering |
| Database contention | Transactions and row locking |

A robust system classifies failures instead of retrying every exception indiscriminately.

## Security Controls

Message queues can contain sensitive business information and should be treated as security boundaries.

Important controls include:

- Authenticate producers and consumers.
- Authorize access per queue or topic.
- Encrypt traffic in transit.
- Encrypt sensitive data at rest.
- Limit payload sizes.
- Avoid sensitive payloads in application logs.
- Restrict dead-letter access.
- Validate message schemas.
- Prevent arbitrary executable content from being interpreted as configuration.
- Rotate credentials.
- Monitor unusual publishing and consumption patterns.

The examples treat payloads as structured data rather than executable instructions.

## Performance Considerations

For an in-memory FIFO queue, ordinary enqueue and dequeue operations can be constant time.

Real distributed brokers introduce additional costs:

- Serialization.
- Network transfer.
- Persistence.
- Replication.
- Consumer coordination.
- Acknowledgement traffic.
- Storage retention.
- Monitoring.

Throughput should be evaluated separately from latency. Increasing batch size may improve throughput but can increase processing latency and failure blast radius.

Concurrency can increase throughput until the system becomes limited by CPU, storage, network bandwidth, downstream services, or database locks.

## Practical Workflow

A realistic asynchronous order workflow can be represented as:

`Order Service`
`    ↓`
`orders.created`
`    ↓`
`Message Queue`
`    ↓`
`Order Consumer`
`    ↓`
`Validate`
`    ↓`
`Persist Business Result`
`    ↓`
`ACK`

For a temporary dependency failure:

`Consumer`
`    ↓`
`Failure`
`    ↓`
`Retry Delay`
`    ↓`
`Consumer`
`    ↓`
`Repeated Failure`
`    ↓`
`Dead-Letter Queue`

The queue is therefore a coordination mechanism between independently operating components, not the owner of the business operation itself.

## Relationship to Repository Development

Repository development can itself contain asynchronous work.

A Pull Request proposes a changeset. Code review evaluates the changes. Approvals represent reviewer decisions. Branch protection enforces repository-level conditions before merging.

These concepts are separate from message queues:

| Repository concept | Message-processing counterpart |
|---|---|
| Pull Request | Proposed change or work item |
| Code review | Evaluation activity |
| Approval | Review decision |
| Branch protection | Policy enforcement |
| Merge | Final repository state transition |
| Queue | Asynchronous work transport |
| Consumer | Worker |
| Acknowledgement | Processing completion |

The C++ and Java implementations intentionally keep repository governance separate from message processing while showing both in the same technical environment.

## Limitations

The source implementations are executable models, not distributed production brokers.

They do not implement:

- Network protocols.
- Replicated broker storage.
- Cross-process consumer coordination.
- Durable disk-based message retention.
- Consumer-group rebalancing.
- Partition replication.
- TLS configuration.
- External identity providers.
- Distributed tracing infrastructure.
- Production-grade exponential backoff.
- Exactly-once distributed transaction semantics.

The PostgreSQL implementation provides the strongest persistence-oriented model because queue state and processing records are stored transactionally in relational tables.

The in-memory implementations are useful for understanding state transitions, retries, acknowledgement, consumer behavior, and failure handling before introducing distributed infrastructure.
