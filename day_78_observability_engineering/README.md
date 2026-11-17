# Observability Engineering: Logs, Metrics, and Distributed Traces

## 1. Technical Scope

Observability is the engineering discipline of understanding the internal state and behavior of a software system through the telemetry it produces.

The implementation covers three complementary telemetry signals:

| Signal | Primary purpose | Typical questions |
|---|---|---|
| Logs | Record individual events | What happened? |
| Metrics | Measure numerical behavior | How much? How often? |
| Traces | Represent request execution paths | Where did the request spend time or fail? |

The project models an enterprise payment-processing environment containing:

- Payment API
- Payment database
- Payment processor
- Security service
- Telemetry collection infrastructure
- Alert evaluation service

A payment request generates logs, numerical measurements, and distributed spans. These signals can be correlated through trace identifiers and evaluated for operational failures.

## 2. Observability Architecture

The system follows a collection, processing, storage, correlation, and analysis architecture.

    Application Services
           |
           v
    Instrumentation
           |
           +----------------+
           |        |       |
           v        v       v
          Logs   Metrics  Traces
           |        |       |
           +--------+-------+
                    |
                    v
            Telemetry Collection
                    |
                    v
             Validation and
                Redaction
                    |
                    v
             Processing Layer
                    |
          +---------+----------+
          |         |          |
          v         v          v
        Storage   Alerts    Correlation
          |         |          |
          +---------+----------+
                    |
                    v
             Operational Reports

The five implementations demonstrate different approaches to this architecture:

| Implementation | Engineering perspective |
|---|---|
| Python | Integrated observability simulation and telemetry export |
| JavaScript | Event-driven collection and asynchronous processing |
| C++17 | Explicit data structures and efficient telemetry evaluation |
| Java 17 | Enterprise domain modeling and concurrent metric management |
| PostgreSQL | Relational persistence, integrity enforcement, aggregation, and reporting |

## 3. Logs: Event-Level Observability

### 3.1 Definition

A log is a timestamped record describing an event that occurred within an application or infrastructure component.

Examples include:

- Payment request received.
- Database transaction completed.
- Authorization rejected.
- Authentication attempt failed.
- External service timed out.
- Application configuration changed.

Logs preserve event context and are particularly useful for investigating individual failures.

### 3.2 Structured logging

The implementations use structured log records rather than relying exclusively on free-form text.

A log record contains:

| Field | Description |
|---|---|
| Timestamp | Event occurrence time |
| Severity | Event importance |
| Service | Originating service |
| Message | Human-readable event description |
| Trace ID | Associated distributed request |
| Span ID | Specific operation within the trace |
| Attributes | Additional structured context |

Severity levels are:

| Severity | Meaning |
|---|---|
| DEBUG | Detailed diagnostic information |
| INFO | Normal application activity |
| WARNING | Unexpected but recoverable behavior |
| ERROR | An operation failed |
| CRITICAL | A serious system-level failure |

Structured attributes support filtering, aggregation, and correlation without repeatedly parsing message text.

### 3.3 Log correlation

A payment request may generate several log records across different services.

The trace identifier connects these records to the same logical request.

For example:

| Service | Event | Severity |
|---|---|---|
| payment-api | Payment request received | INFO |
| payment-database | Database insertion completed | INFO |
| payment-processor | Authorization rejected | ERROR |
| payment-api | Request processing failed | ERROR |

The Python, JavaScript, C++17, and Java 17 implementations provide trace-based log retrieval.

The PostgreSQL implementation stores trace identifiers and span identifiers as relational references.

### 3.4 Security and log management

Logs frequently contain information that should not be collected or exposed.

The implementations redact sensitive attribute names such as:

- `password`
- `token`
- `access_token`
- `authorization`
- `api_key`
- `secret`
- `credit_card`
- `ssn`

Redaction is applied before telemetry is exported or persisted.

This mechanism is a basic protection rather than a complete data-loss-prevention system. Production logging should use explicit attribute allowlists, controlled access, encryption, retention policies, and additional protection against sensitive information embedded in arbitrary text.

## 4. Metrics: Numerical System Behavior

### 4.1 Definition

Metrics are numerical measurements collected over time.

They provide a quantitative view of service performance, workload, availability, resource utilization, and application behavior.

Unlike logs, metrics are primarily designed for aggregation and time-based analysis.

### 4.2 Metric types

The implementations distinguish three fundamental metric types.

| Type | Behavior | Example |
|---|---|---|
| Counter | Monotonically increases | Total payment requests |
| Gauge | Can increase or decrease | Active connections |
| Histogram | Records numerical observations | Request duration |

**Counter**

A counter records cumulative events.

Examples:

- `payment_requests_total`
- `payment_success_total`
- `payment_failures_total`

A counter must not decrease. If a process restarts, the exported cumulative value may reset depending on the collection and storage model.

**Gauge**

A gauge represents a value that can move in either direction.

Examples:

- Active database connections
- Current queue depth
- Memory consumption
- Number of active workers

A gauge should not be interpreted as a cumulative event count.

**Histogram**

A histogram records observations belonging to a distribution.

Examples:

- HTTP request duration
- Database query duration
- Message processing duration
- External API response time

The implementations calculate:

- Observation count
- Sum
- Average
- Minimum
- Maximum
- P50
- P95
- P99

### 4.3 Percentiles

Percentiles describe the distribution of measured values.

| Percentile | Interpretation |
|---|---|
| P50 | Median observation |
| P95 | 95% of observations are at or below this value |
| P99 | 99% of observations are at or below this value |

Consider these request durations:

`10, 20, 30, 40, 100`

The median is 30 milliseconds.

The P95 value indicates the upper end of the observed latency distribution.

Tail latency matters because a service can have a reasonable average response time while a significant minority of requests remain slow.

The source implementations use interpolated percentiles over retained observations. These are suitable for demonstrations and bounded datasets. Production monitoring generally uses bucket-based histograms or mergeable distribution sketches instead of retaining every observation in application memory.

### 4.4 Metric labels and cardinality

Labels provide dimensions for filtering and grouping.

Example:

| Metric | Label | Value |
|---|---|---|
| payment_requests_total | environment | production |
| payment_latency_ms | endpoint | /payments |
| active_connections | pool | primary |

A metric series is identified by its metric name, service, and label combination.

Unbounded label values create high cardinality.

Examples of unsuitable metric labels include:

- Unique customer identifiers
- Request identifiers
- Random UUIDs
- Individual email addresses
- Unbounded transaction identifiers

These values can create excessive time-series storage and indexing costs.

The implementations impose label-count and value-length restrictions. Production systems should also use controlled label vocabularies.

## 5. Distributed Tracing

### 5.1 Definition

Distributed tracing follows a logical request across multiple application components.

A trace represents the complete execution path of a request.

A span represents one operation within that trace.

For example, a payment request can execute the following operations:

    Trace: POST /payments
        |
        +-- payment-api
        |      |
        |      +-- Request validation
        |
        +-- payment-database
        |      |
        |      +-- INSERT payment
        |
        +-- payment-processor
               |
               +-- Authorize transaction

### 5.2 Trace identifiers

A trace ID identifies an entire distributed request.

All spans belonging to that request share the same trace ID.

The trace ID makes it possible to correlate:

- Logs generated by different services
- Spans representing different operations
- Error events
- Service-level measurements

A trace ID should be propagated across service boundaries rather than regenerated independently by every service.

### 5.3 Span identifiers

Each span has its own span ID.

A child span references its parent span through the parent span ID.

The resulting relationship represents the execution hierarchy.

| Attribute | Purpose |
|---|---|
| Trace ID | Identifies the complete request |
| Span ID | Identifies an individual operation |
| Parent Span ID | Identifies the operation that initiated the current operation |
| Service | Identifies the executing component |
| Operation | Identifies the work being performed |
| Start time | Operation start |
| End time | Operation completion |
| Duration | Time spent in the operation |
| Status | Operation result |
| Attributes | Additional diagnostic context |

### 5.4 Span status

The implementations use three span states:

- `UNSET`: No explicit completion status has been assigned.
- `OK`: The operation completed successfully.
- `ERROR`: The operation encountered an error.

An error in a child span does not automatically imply that every other child operation failed.

A root span can nevertheless be marked as failed when the complete request fails.

### 5.5 Trace integrity

A valid trace should satisfy these conditions:

1. Every span belongs to an existing trace.
2. Every referenced parent exists.
3. Parent and child spans belong to the same trace.
4. A completed trace contains no active spans.
5. Span relationships do not contain cycles.
6. Span identifiers are unique within their trace.

These conditions are checked by the implementations.

### 5.6 Distributed context propagation

The examples maintain trace context inside a single simulated application workflow.

A production distributed system needs an explicit context propagation mechanism.

A common propagation structure includes:

- Trace ID
- Parent span ID
- Trace flags
- Optional trace state

HTTP services generally propagate this information through standardized request headers.

Message-based systems must preserve the context when publishing and consuming messages.

Without propagation, separate services may generate unrelated traces, preventing accurate end-to-end request analysis.

## 6. Correlation of Logs, Metrics, and Traces

The three signals answer different questions.

| Investigation question | Most useful signal |
|---|---|
| Which request failed? | Logs and traces |
| Which service generated the error? | Logs and traces |
| How frequently does failure occur? | Metrics |
| Which operation caused latency? | Traces |
| What happened immediately before failure? | Logs |
| Is the problem affecting many requests? | Metrics |
| Which downstream dependency is slow? | Traces |

Consider a payment-processing incident.

**Stage 1: Metrics identify degradation**

The payment latency metric increases beyond its expected range.

**Stage 2: Logs identify the failure**

Error records indicate that payment authorization is being rejected.

**Stage 3: Traces identify the affected operation**

The distributed trace shows that the payment processor is the failing downstream component.

**Stage 4: Correlation establishes context**

The shared trace ID connects the log records and span hierarchy.

The combined signals provide stronger diagnostic information than any individual telemetry source.

## 7. Telemetry Collection and Processing

### 7.1 Collection

Applications generate telemetry through instrumentation.

Instrumentation can be:

- Manual, through explicit logging and measurement calls.
- Automatic, through supported framework or runtime instrumentation.
- Infrastructure-based, through operating-system and platform collectors.

The implementations use explicit instrumentation to make telemetry generation and state transitions visible.

### 7.2 Processing

Telemetry processing includes:

1. Input validation.
2. Sensitive-data redaction.
3. Metric and trace classification.
4. Correlation.
5. Aggregation.
6. Alert evaluation.
7. Export and persistence.

The Python implementation exports telemetry as JSON Lines.

The JavaScript implementation introduces an asynchronous event-driven pipeline with batch processing and queue-capacity controls.

The PostgreSQL implementation stores telemetry using relational structures and JSONB attributes.

### 7.3 Backpressure

A telemetry system must handle situations in which incoming telemetry exceeds processing capacity.

Backpressure can be managed through:

- Bounded queues
- Batch processing
- Sampling
- Controlled dropping
- Retry mechanisms
- Exporter health monitoring

The JavaScript pipeline demonstrates bounded queue capacity, batch processing, dropped-event accounting, and explicit handling of failed processing.

A production implementation should also distinguish retryable failures from permanent failures and use durable buffering where telemetry loss is unacceptable.

## 8. Alerting and Incident Detection

### 8.1 Alert rules

An alert rule evaluates a metric against a configured condition.

Example:

| Property | Configuration |
|---|---|
| Rule | high_latency |
| Metric | payment_latency_ms |
| Operator | Greater than |
| Threshold | 200 ms |
| Evaluation window | 2 observations |

The system calculates the average of the configured recent observations and compares it with the threshold.

### 8.2 Alert states

The implementations use:

| State | Meaning |
|---|---|
| NORMAL | Condition is not currently breached |
| FIRING | Condition is breached |
| RESOLVED | Previously firing condition has recovered |

The transition sequence is:

    NORMAL
       |
       | Threshold exceeded
       v
    FIRING
       |
       | Threshold no longer exceeded
       v
    RESOLVED
       |
       v
    NORMAL

The implementations record state changes rather than generating a new transition for every repeated evaluation.

### 8.3 Evaluation windows

A single measurement may be misleading.

A moving evaluation window reduces sensitivity to isolated observations.

For example, with a two-observation window:

| Observation | Value |
|---|---:|
| First | 220 ms |
| Second | 240 ms |
| Average | 230 ms |

For a threshold of 200 milliseconds, the rule enters the firing state.

A subsequent recovery requires the evaluation window to fall below the threshold.

### 8.4 Practical alerting considerations

Production alerting should consider:

- Evaluation frequency
- Sustained threshold violations
- Missing telemetry
- Service dependencies
- Alert severity
- Notification routing
- Recovery behavior
- Alert deduplication
- Maintenance windows
- Escalation policies

A missing measurement should not automatically be interpreted as a healthy service.

## 9. Python Implementation

The Python implementation is an integrated observability simulation.

### Main components

| Component | Responsibility |
|---|---|
| `SecurityPolicy` | Sensitive-data redaction |
| `StructuredLogger` | Structured log creation and retrieval |
| `MetricsRegistry` | Counter, gauge, and histogram storage |
| `Trace` | Span hierarchy and lifecycle |
| `TracingRegistry` | Trace creation and retrieval |
| `AlertManager` | Alert rules and state transitions |
| `ObservabilityPlatform` | Central coordination and export |

### Engineering decisions

Dataclasses provide explicit telemetry structures.

Enums restrict severity, metric type, span status, and alert state.

Dictionaries provide direct access to services, traces, and metric series.

Sets and validation routines help enforce domain constraints.

The JSON Lines exporter creates a temporary file before replacing the final output, reducing the risk of leaving a partially written report.

The script includes assertions for trace correlation, histogram calculations, redaction, alert transitions, and invalid inputs.

### Execution

Run the file using Python 3.10 or later.

The execution creates an `observability_data` directory containing `observability.jsonl`.

## 10. JavaScript Implementation

The JavaScript implementation emphasizes asynchronous processing and event-driven telemetry management.

### Main components

| Component | Responsibility |
|---|---|
| `Redactor` | Sensitive-data protection |
| `LogCollector` | Structured logging |
| `MetricRegistry` | Metric-series management |
| `Span` | Individual traced operation |
| `Trace` | Distributed request hierarchy |
| `TelemetryPipeline` | Asynchronous batch processing |
| `AlertEngine` | Event-driven alert transitions |
| `ObservabilityApplication` | Service coordination |

### Event-driven processing

The pipeline extends Node.js `EventEmitter`.

It exposes events for:

- Published telemetry
- Dropped telemetry
- Processed batches
- Processing failures
- Pipeline closure

The queue has a maximum capacity. When the queue is full, the pipeline records the dropped-event count rather than allowing unbounded memory growth.

The batch processor uses asynchronous execution to establish an exporter boundary.

The alert engine emits events only when the state changes.

### Engineering decisions

JavaScript Maps provide efficient keyed access to metric series and service collectors.

Sets provide efficient membership checks for sensitive fields.

Promises support asynchronous telemetry processing.

`process.hrtime.bigint()` provides high-resolution duration measurement without relying on wall-clock adjustments.

The export routine uses a temporary file and an atomic rename operation within the same filesystem.

### Execution

Run the file using Node.js 18 or later.

The application creates `observability-report.json` in the current working directory.

## 11. C++17 Implementation

The C++ implementation emphasizes explicit domain structures, STL containers, and deterministic validation.

### Main components

| Component | Responsibility |
|---|---|
| `Logger` | Structured event collection |
| `MetricRegistry` | Typed metric series |
| `Trace` | Parent-child span management |
| `AlertEngine` | Rule evaluation |
| `ObservabilityEngine` | Coordination of telemetry |
| `SecurityRedactor` | Sensitive attribute filtering |

### Data structures

The implementation uses:

- `std::map` for ordered metric and service registries.
- `std::vector` for log records and histogram observations.
- `std::deque` for bounded alert evaluation history.
- `std::set` for cycle detection and security-key membership.
- `std::optional` for root-span parent references.
- `std::unique_ptr` for explicit trace ownership.

The metric registry uses a composite key containing metric name, service, and labels.

The histogram implementation sorts a copy of the observations before percentile calculations. This preserves the original stored observations.

### Complexity considerations

| Operation | Approximate complexity |
|---|---|
| Ordered metric lookup | O(log n) |
| Metric insertion | O(log n) |
| Counter update after lookup | O(1) |
| Histogram observation | Amortized O(1) |
| Histogram percentile calculation | O(n log n) |
| Log correlation | O(L), where L is the total number of stored log records |
| Trace validation | O(S × H), where S is the number of spans and H is maximum hierarchy depth |

The implementation prioritizes explicit ownership and straightforward correctness over highly optimized production telemetry throughput.

### Execution

Compile with a C++17-compatible compiler.

The program uses no external libraries.

## 12. Java 17 Implementation

The Java implementation models observability as an enterprise service with explicit domain types and policy objects.

### Main components

| Component | Responsibility |
|---|---|
| `LogRecord` | Immutable structured event |
| `StructuredLogger` | Log collection and filtering |
| `MetricKey` | Metric-series identity |
| `CounterMetric` | Monotonic event counting |
| `GaugeMetric` | Mutable numerical state |
| `HistogramMetric` | Distribution analysis |
| `Trace` | Distributed trace lifecycle |
| `AlertRule` | Alert configuration |
| `ComparisonPolicy` | Alert comparison behavior |
| `AlertService` | Evaluation and transitions |
| `ObservabilityService` | Enterprise coordination |

### Records and immutable structures

Java records model log records, metric keys, histogram summaries, alert rules, and state transitions.

Record constructors validate their inputs and establish immutable attribute collections.

This reduces accidental modification of telemetry data after creation.

### Concurrent metric management

`ConcurrentHashMap` manages shared metric-series references.

`LongAdder` is used for counters to reduce contention in concurrent update scenarios.

Gauge values use volatile state.

Histogram observations use synchronized collections and snapshots for calculations.

### Policy-based alerting

The alert service uses a `ComparisonPolicy` interface.

Separate implementations define greater-than and greater-than-or-equal comparisons.

This separates comparison behavior from the alert evaluation workflow.

Additional policies can be introduced without embedding every comparison rule inside the service.

### Execution

Compile and execute with Java 17.

The implementation has no third-party dependencies.

## 13. PostgreSQL Implementation

The database implementation models observability as a relational telemetry platform.

It uses a dedicated `observability` schema.

### Relational domain model

| Table | Purpose |
|---|---|
| `services` | Registered application services |
| `traces` | Distributed request records |
| `spans` | Individual operations within traces |
| `span_events` | Events attached to spans |
| `logs` | Structured log records |
| `metric_definitions` | Metric metadata |
| `metric_samples` | Numerical observations |
| `alert_rules` | Alert configurations |
| `alert_evaluations` | Individual rule evaluations |
| `alert_transitions` | Alert state changes |

### Referential integrity

Foreign keys connect telemetry records to their originating services and traces.

The span parent reference creates a hierarchical relationship between operations.

The database trigger validates that parent and child spans belong to the same trace.

The deferred foreign-key relationship permits controlled insertion of related span records within a transaction.

### JSONB attributes

PostgreSQL JSONB stores structured telemetry attributes.

This supports:

- Flexible service-specific metadata
- Attribute filtering
- JSON containment queries
- GIN indexing

Sensitive fields are redacted by database triggers before log and span attributes are persisted.

### Functions and views

The SQL implementation includes:

| Database object | Function |
|---|---|
| `sanitize_telemetry_attributes` | Sensitive-field redaction |
| `validate_span_relationship` | Parent-child integrity |
| `complete_trace` | Trace completion and status determination |
| `evaluate_alert` | Threshold evaluation and state transitions |
| `get_trace_telemetry` | Combined log and span retrieval |
| `v_service_error_summary` | Service error reporting |
| `v_trace_summary` | Trace-level reporting |
| `v_metric_summary` | Metric aggregation |
| `v_latest_alert_states` | Latest recorded alert transitions |

### Performance design

Indexes support:

- Recent service logs
- Trace-level retrieval
- Error-log investigation
- Service-specific spans
- Recent metric samples
- Alert evaluation history
- JSONB attribute searches

The schema is suitable as an educational relational model. A high-volume production deployment would require time partitioning, retention automation, ingestion batching, and potentially separate storage systems for high-cardinality metrics and trace data.

### Transaction handling

The sample ingestion section demonstrates transactional execution and a savepoint.

This illustrates how related telemetry writes can be grouped into a database transaction.

## 14. Operational Reliability and Failure Modes

Observability infrastructure can itself become a source of operational problems.

| Failure mode | Consequence | Engineering control |
|---|---|---|
| Excessive logging | Storage and processing costs increase | Severity filtering and sampling |
| Sensitive information in logs | Confidentiality exposure | Redaction and field allowlists |
| High metric cardinality | Excessive time-series growth | Controlled labels |
| Missing trace propagation | Broken request correlation | Context propagation |
| Incomplete spans | Incorrect trace analysis | Lifecycle validation |
| Queue overflow | Telemetry loss | Bounded queues and backpressure |
| Export failure | Telemetry unavailable downstream | Retry and durable buffering |
| Incorrect alert threshold | False or missed incidents | Window-based evaluation and calibration |
| Clock inconsistency | Incorrect event ordering | UTC timestamps and synchronized clocks |
| Excessive trace collection | Increased overhead | Sampling and retention controls |
| Telemetry storage growth | Infrastructure cost escalation | Retention and partitioning |

### Observability overhead

Instrumentation consumes resources.

Important costs include:

- CPU used for serialization and aggregation
- Memory used for telemetry buffering
- Network traffic generated by exporters
- Database storage and indexing
- Processing overhead from high-volume traces

Instrumentation should be designed to provide useful diagnostic information without materially degrading application performance.

## 15. Important Technical Distinctions

| Concept | Distinction |
|---|---|
| Monitoring | Evaluates known system conditions and predefined indicators |
| Observability | Supports investigation of internal system behavior using available evidence |
| Logging | Records discrete events |
| Metrics | Quantifies system behavior |
| Tracing | Represents request execution across operations and services |
| Instrumentation | Produces telemetry from applications and infrastructure |
| Collection | Receives telemetry from instrumented components |
| Aggregation | Combines observations into meaningful measurements |
| Correlation | Connects related telemetry records |
| Sampling | Selects a subset of telemetry for processing or retention |
| Alerting | Identifies conditions requiring operational attention |
| Retention | Determines how long telemetry remains available |

Observability and monitoring are related but are not interchangeable.

Monitoring commonly evaluates predefined conditions. Observability provides the supporting evidence needed to investigate conditions, including failures that were not anticipated when monitoring rules were configured.

## 16. Implementation Limitations

The five implementations deliberately demonstrate core observability mechanisms without claiming to provide a complete production telemetry platform.

| Area | Current implementation | Production consideration |
|---|---|---|
| Log storage | In-memory or PostgreSQL | Durable distributed storage |
| Metric aggregation | Local numerical observations | Time-series aggregation |
| Histograms | Retained observations | Mergeable bucket or sketch representations |
| Tracing | Local simulated context | Cross-process context propagation |
| Trace sampling | Not implemented | Head-based or tail-based sampling |
| Alerting | Window-based threshold rules | Evaluation scheduling and notification routing |
| Telemetry transport | Local processing | Reliable distributed transport |
| Authentication | Not fully implemented | Service identity and authorization |
| Retention | Not automated | Scheduled deletion and partition management |
| High availability | Not implemented | Replication and recovery |
| Clock synchronization | UTC timestamps and monotonic durations | Consistent distributed time handling |

These limitations are important when interpreting the examples.

The implementations demonstrate domain logic and data handling, not production-scale throughput or guaranteed delivery.

## 17. Practical Engineering Applications

The implemented mechanisms apply to:

- Microservice performance monitoring
- Distributed payment systems
- Database performance investigations
- API reliability analysis
- Cloud application operations
- Authentication and security event analysis
- Transaction failure investigation
- Infrastructure health monitoring
- Service-level objective measurement
- Incident diagnosis and root-cause analysis

The payment-processing scenario demonstrates how numerical degradation, structured error events, and distributed execution details combine to explain an application failure.

The central engineering principle is that logs, metrics, and traces should be designed as complementary sources of operational evidence, with consistent identifiers, controlled telemetry collection, secure data handling, and reliable processing.
