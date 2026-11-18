# Application Monitoring: Health Checks, Alerts, and Dashboards

## 1. Application Monitoring Fundamentals

Application monitoring is the continuous observation of software applications, their dependencies, infrastructure resources, and operational behavior.

Its primary purpose is to identify service failures, performance degradation, dependency problems, and resource constraints before they cause extended operational disruption.

A monitoring system collects observations, evaluates them against defined policies, records metrics, generates alerts, and presents operational information through dashboards.

The implemented monitoring architecture follows this workflow:

Application
→ Service
→ Health Checks
→ Monitoring Results
→ Status Evaluation
→ Metrics
→ Alert Processing
→ Dashboard

Three distinct monitoring concerns are addressed:

| Concern | Primary question | Operational outcome |
|---|---|---|
| Health checks | Is the component functioning? | Health status |
| Alerts | Does an observed condition require attention? | Notification and incident state |
| Dashboards | What is happening across monitored services? | Operational visibility |

These mechanisms complement one another but are not interchangeable.

A health check produces an observation. An alert policy determines whether that observation requires attention. A dashboard presents the resulting operational state and historical measurements.

## 2. Health Checks

A health check is an automated test that evaluates whether an application component or dependency satisfies a defined operational condition.

Health checks can examine application availability, database connectivity, memory utilization, external dependencies, message queues, and other critical components.

### 2.1 Types of Health Checks

| Check | Purpose | Example |
|---|---|---|
| Liveness | Determines whether an application process is functioning | Application responds to a local health endpoint |
| Readiness | Determines whether an instance can accept application traffic | Database connections are available |
| HTTP | Tests an HTTP endpoint | HTTP 200 response |
| Database | Tests database connectivity | Successful connection or query |
| Dependency | Evaluates an external service | Payment provider availability |
| Memory | Measures memory consumption | Memory utilization below 90% |
| CPU | Evaluates processor utilization | CPU usage within operational limits |
| Queue | Checks message-processing infrastructure | Queue depth within acceptable limits |

Liveness and readiness have different operational purposes.

Liveness indicates whether a process should continue running. Readiness indicates whether the process should receive traffic.

A process can remain alive while being unable to serve requests because its database or another dependency is unavailable.

### 2.2 Health Status Model

The implementations use four health states.

| Status | Meaning |
|---|---|
| HEALTHY | Required checks are successful and performance is within normal limits |
| DEGRADED | The service has a warning condition or has not yet satisfied recovery requirements |
| UNHEALTHY | Persistent failures or critical latency conditions have been detected |
| UNKNOWN | No completed health evaluation is available |

The distinction between `DEGRADED` and `UNHEALTHY` is important.

A single failed check does not necessarily indicate a sustained outage. A monitoring system can require multiple consecutive failures before declaring a service unhealthy.

This reduces sensitivity to transient network interruptions and short-lived infrastructure problems.

### 2.3 Health Check Execution

The Python implementation uses a common `HealthCheck` base class. Application, database, memory, and dependency checks provide independent implementations of the `perform()` operation.

Each execution produces a structured `CheckResult` containing:

- Check identifier.
- Service identifier.
- Health status.
- Execution latency.
- Diagnostic message.
- UTC timestamp.
- Additional metadata.

The JavaScript implementation uses asynchronous handlers and `Promise.race()` to enforce execution timeouts.

The Java implementation defines a `HealthCheck` interface and uses `CompletableFuture` to execute independent checks concurrently.

The C++ implementation uses the `IHealthCheck` interface and a concrete `FunctionalHealthCheck` class.

These approaches separate check definitions from the monitoring engine.

### 2.4 Timeouts and Failure Handling

Health checks should have bounded execution times.

Without a timeout, a blocked database connection or external HTTP request can prevent a monitoring cycle from completing.

A production implementation should distinguish:

- Connection failures.
- Request timeouts.
- Authentication failures.
- Invalid responses.
- Dependency failures.
- Monitoring infrastructure failures.

The JavaScript implementation converts asynchronous check failures into structured unsuccessful results.

The Python implementation records exceptions without terminating the complete monitoring process.

The C++ and Java implementations validate check results and report execution failures.

A timeout on a monitoring operation must not be interpreted as proof that the monitored application has permanently failed. It represents an unsuccessful observation that requires evaluation.

## 3. Monitoring Metrics

Metrics are numerical observations collected over time.

They provide information that cannot be obtained from a single health status.

The implementations calculate latency, availability, sample counts, and maximum response time.

### 3.1 Response Latency

Latency measures the time required to complete an operation.

\[
Latency = CompletionTime - StartTime
\]

The implementations express latency in milliseconds.

Three useful latency measurements are:

- Average latency.
- Maximum latency.
- Minimum latency.

Average latency is useful for general performance assessment, but it can hide occasional slow requests.

Production dashboards should also consider percentile measurements.

| Metric | Meaning |
|---|---|
| p50 | Median latency |
| p90 | 90% of observations are at or below this value |
| p95 | 95% of observations are at or below this value |
| p99 | 99% of observations are at or below this value |

Percentiles provide better visibility into slow requests affecting a smaller proportion of users.

### 3.2 Availability

Availability represents the proportion of successful observations within a measurement period.

\[
Availability(\%) =
\frac{SuccessfulChecks}{TotalChecks}
\times 100
\]

For example, if a service produces 9,900 successful observations from 10,000 checks:

\[
Availability = 99\%
\]

The implementations calculate sample-based availability.

This is not automatically equivalent to contractual uptime. A production service-level agreement should define its measurement window, eligible requests, exclusions, and monitoring source.

### 3.3 Resource Metrics

Memory and CPU utilization provide information about infrastructure pressure.

A service may respond successfully while consuming excessive resources.

Monitoring resource consumption helps identify:

- Memory exhaustion.
- Excessive garbage collection.
- CPU saturation.
- Connection pool exhaustion.
- Queue accumulation.
- Resource contention.

Resource thresholds should reflect actual workload characteristics rather than arbitrary universal values.

### 3.4 Metric Retention

Metric history must be bounded or managed through retention policies.

The Python implementation uses a bounded `deque`.

The JavaScript implementation uses bounded arrays in `MetricStore`.

The Java implementation maintains bounded collections.

The C++ implementation accumulates service metrics for the lifetime of its demonstration process.

The PostgreSQL implementation stores individual health results in relational tables.

For large monitoring environments, time-series storage, aggregation, retention, and partitioning become important architectural considerations.

## 4. Alert Management

An alert is an operational event generated when a monitored condition satisfies an alerting rule.

Alerts communicate conditions requiring investigation or intervention.

An alert is not simply another health check result.

A health check may fail temporarily without generating a critical alert. Alert policies introduce thresholds, persistence requirements, and severity classifications.

### 4.1 Alert Severity

The implementations use three severity levels.

| Severity | Meaning | Example |
|---|---|---|
| INFO | Informational operational event | Service recovery |
| WARNING | Performance degradation or developing problem | Elevated response latency |
| CRITICAL | Significant operational failure | Persistent database outage |

Severity communicates operational importance.

It does not necessarily represent the duration of an incident or the number of affected users.

### 4.2 Alert Lifecycle

The basic alert lifecycle is:

Condition Detected
→ Alert Created
→ Alert Updated
→ Acknowledged
→ Condition Recovered
→ Alert Resolved

The implementations explicitly represent `FIRING` and `RESOLVED` states.

The PostgreSQL implementation also includes `ACKNOWLEDGED`.

Acknowledgement means an operator has recognized the alert. It does not mean that the underlying problem has been corrected.

Resolution means the monitoring system has detected that the condition no longer satisfies the firing rule.

### 4.3 Alert Deduplication

Without deduplication, repeated monitoring cycles can generate hundreds of alerts for one continuous incident.

The Python implementation maintains an active-alert index by service.

The JavaScript implementation uses a `Map` keyed by service.

The C++ implementation uses a map from service names to active alert positions.

The Java implementation uses a synchronized map.

The PostgreSQL implementation enforces one active firing alert per service through a partial unique index:

- The service identifier is indexed.
- Only alerts in the `FIRING` state participate.
- Resolved and acknowledged alerts do not occupy the active firing constraint.

Repeated observations update the existing firing alert and increment its occurrence count.

This design reduces duplicate incidents.

### 4.4 Alert Thresholds

The implementations distinguish:

- Warning latency threshold.
- Critical latency threshold.
- Consecutive failure threshold.
- Consecutive recovery threshold.

For example:

| Policy | Value |
|---|---:|
| Warning latency | 300 ms |
| Critical latency | 1,000 ms |
| Consecutive failures | 2 |
| Consecutive recoveries | 2 |

Two consecutive failures are required before the service becomes unhealthy.

Two successful recovery observations are required before a previously unhealthy service returns to healthy status.

This introduces hysteresis into monitoring.

Hysteresis prevents rapid switching between healthy and unhealthy states when measurements fluctuate near a threshold.

A production implementation may use separate policies for different services, environments, business criticality levels, and operating periods.

### 4.5 Alert Fatigue

Excessive alerts reduce the effectiveness of operational monitoring.

Common causes include:

- Poorly selected thresholds.
- Duplicate alerts.
- Repeated transient failures.
- Alerts without actionable information.
- Missing dependency relationships.
- Insufficient maintenance-window handling.

Alert grouping, suppression, escalation, ownership, and notification delivery should be managed independently from the underlying health-check execution.

The sample implementations model alert state and deduplication. They do not implement external email, SMS, or incident-management delivery.

## 5. Monitoring Dashboards

A monitoring dashboard provides a consolidated view of application health and operational metrics.

It transforms individual health observations and alerts into information that engineers and operational teams can interpret.

### 5.1 Dashboard Components

The implementations generate service-level and system-level dashboard information.

| Component | Information |
|---|---|
| Service inventory | Registered services |
| Health indicators | Healthy, degraded, unhealthy, and unknown counts |
| Latency | Average and maximum latency |
| Availability | Successful observation percentage |
| Active alerts | Currently firing alerts |
| Alert history | Previously generated incidents |
| Timestamps | Last monitoring execution |
| Environment | Development, staging, or production |

### 5.2 Service-Level Dashboard

A service-level dashboard focuses on an individual application component.

For a payment API, useful measurements include:

- Application endpoint availability.
- Database connectivity.
- Payment-provider availability.
- Response latency.
- Memory utilization.
- Active critical alerts.

This allows engineers to identify whether a failure originates in the application or an external dependency.

### 5.3 System-Level Dashboard

A system-level dashboard combines multiple service observations.

For example:

Payment Platform
- Payment API
- Payment Database
- Payment Provider

Analytics Platform
- Analytics API
- Analytics Worker
- Reporting Database

The dashboard aggregates the status of individual services without assuming that every component has the same operational importance.

A production dashboard should distinguish application health from overall business-service availability.

A payment platform might remain partially operational even if a nonessential reporting component is unavailable.

### 5.4 Dashboard Accuracy

Dashboards should display:

- The observation timestamp.
- The measurement window.
- The number of available samples.
- Missing or delayed measurements.
- The difference between zero failures and missing data.

An empty metric collection must not be displayed as 100% availability.

The implementations return zero samples and an unavailable availability measurement when no observations exist.

This avoids incorrectly interpreting missing measurements as successful service operation.

## 6. Monitoring Architecture

The five implementations represent the same operational domain through different engineering approaches.

### 6.1 Logical Architecture

Application
   |
   v
Service Registry
   |
   v
Health Check Scheduler
   |
   +---- Application Check
   |
   +---- Database Check
   |
   +---- Dependency Check
   |
   +---- Resource Check
   |
   v
Health Result Collection
   |
   v
Status Evaluation Engine
   |
   +---- Healthy
   |
   +---- Degraded
   |
   +---- Unhealthy
   |
   v
Metric Storage
   |
   v
Alert Policy Engine
   |
   +---- Alert Creation
   |
   +---- Alert Deduplication
   |
   +---- Alert Resolution
   |
   v
Dashboard and Reporting

The architecture separates observation, evaluation, storage, alerting, and presentation.

This separation allows each component to evolve independently.

### 6.2 Monitoring Cycle

A monitoring cycle consists of the following operations:

1. Select enabled services.
2. Retrieve registered health checks.
3. Execute checks.
4. Measure execution latency.
5. Record results.
6. Evaluate service status.
7. Update consecutive failure or recovery counters.
8. Process alert state transitions.
9. Refresh dashboard measurements.

A monitoring cycle should be isolated from the failure of an individual service.

The Python monitoring engine catches failures for individual services so other services can continue to be evaluated.

The JavaScript implementation uses `Promise.allSettled()` to retain independent service outcomes.

The Java implementation uses concurrent health-check execution through an executor service.

The C++ implementation evaluates each registered service and handles individual monitoring exceptions.

## 7. Python Implementation

**File:** `application_monitoring.py`

The Python implementation focuses on simulation, domain modeling, and operational behavior.

### 7.1 Core Classes

| Class | Responsibility |
|---|---|
| `HealthCheck` | Common health-check execution interface |
| `ApplicationCheck` | Application availability |
| `DatabaseCheck` | Database connectivity |
| `MemoryCheck` | Memory threshold evaluation |
| `DependencyCheck` | External dependency availability |
| `ServiceMonitor` | Service-level status evaluation |
| `AlertManager` | Alert creation and resolution |
| `MonitoringDashboard` | Dashboard generation |
| `MonitoringEngine` | Coordinates monitoring cycles |

### 7.2 Data Structures

The implementation uses:

- Dictionaries for service registries and active-alert indexing.
- Lists for health-check registration.
- Deques for bounded monitoring history.
- Dataclasses for structured results, policies, and alerts.
- Enums for explicit operational states.

The bounded history prevents indefinite in-memory metric growth.

### 7.3 Exception Handling

Health-check exceptions are converted into unsuccessful observations.

Monitoring failures are logged with diagnostic information.

Invalid policies and configurations are rejected during object creation.

The implementation also includes executable assertions covering alert creation, failure thresholds, recovery, and policy validation.

### 7.4 Execution

Run using:

`python application_monitoring.py`

The script executes tests before simulating payment API and database monitoring.

It generates JSON dashboard output for each monitoring cycle.

## 8. JavaScript Implementation

**File:** `application-monitoring.js`

The JavaScript implementation focuses on asynchronous monitoring and event-driven alert processing.

### 8.1 Asynchronous Execution

Health checks are independent asynchronous operations.

The `HealthCheck` class uses `Promise.race()` to implement timeout behavior.

`Promise.all()` executes the checks for one service concurrently.

`Promise.allSettled()` allows the application to collect independent monitoring outcomes across services.

This approach avoids making one service's failure prevent the evaluation of other services.

### 8.2 Event-Driven Architecture

The implementation uses Node.js `EventEmitter`.

The monitoring system exposes events such as:

| Event | Purpose |
|---|---|
| `alertFired` | A new alert is created |
| `alertUpdated` | An existing alert receives another observation |
| `alertResolved` | An alert is resolved |
| `cycleCompleted` | A monitoring cycle finishes |
| `statusChanged` | A service changes health status |

Event-driven behavior separates monitoring decisions from downstream consumers.

A production notification service could subscribe to alert events without changing the health-check implementation.

### 8.3 Metric Store

`MetricStore` stores bounded service-specific samples.

It provides:

- Metric recording.
- Sample retrieval.
- Average latency.
- Maximum latency.
- Availability calculation.

The `Map` structure provides direct service-level lookup.

### 8.4 Execution

Run using:

`node application-monitoring.js`

The program executes asynchronous tests and demonstrates a payment API with simulated database recovery.

## 9. C++17 Implementation

**File:** `application_monitoring.cpp`

The C++ implementation focuses on explicit domain modeling, interface-based design, and efficient in-memory monitoring.

### 9.1 Interface-Based Design

`IHealthCheck` defines the contract for monitoring components.

`FunctionalHealthCheck` implements that contract.

This separates the monitoring engine from the implementation details of individual checks.

New health-check types can implement the interface without changing the service-monitoring architecture.

### 9.2 Service Policy

`ServicePolicy` defines:

- Warning latency.
- Critical latency.
- Failure threshold.
- Recovery threshold.

Policy validation occurs when the service monitor is constructed.

### 9.3 Metric Aggregation

`ServiceMetrics` maintains:

- Total observations.
- Successful observations.
- Total latency.
- Maximum latency.

Average latency and availability are calculated from accumulated values.

This avoids repeatedly traversing the complete observation history for simple aggregate measurements.

### 9.4 Alert Indexing

The alert manager uses:

- A vector for alert history.
- A map for active service-to-alert indexing.

The map provides efficient lookup of active alerts.

The vector retains alert records for reporting.

The demonstration uses service-specific status transitions and dependency recovery.

### 9.5 Execution

Compile using:

`g++ -std=c++17 -O2 -Wall -Wextra -pedantic application_monitoring.cpp -o application_monitoring`

Run using:

`./application_monitoring`

The executable runs metric and alert assertions before processing monitoring cycles.

## 10. Java 17 Implementation

**File:** `ApplicationMonitoring.java`

The Java implementation represents an enterprise-oriented monitoring service using immutable records, interfaces, policy objects, concurrent execution, and explicit service boundaries.

### 10.1 Domain Records

The implementation uses Java 17 records for:

- `CheckResult`
- `ServicePolicy`
- `MetricSnapshot`

Records provide concise data models and compact-constructor validation.

This reduces unnecessary mutable state in monitoring observations and configuration objects.

### 10.2 Service Abstractions

The `HealthCheck` interface defines the monitoring contract.

`SimulatedHealthCheck` supplies a concrete implementation with configurable availability.

`ServiceMonitor` owns service-specific check registration, execution, and state transitions.

`HealthPolicyEngine` evaluates health observations against configured thresholds.

`MetricService` maintains bounded metric history.

`AlertService` manages active and historical alerts.

`DashboardService` generates consolidated operational information.

### 10.3 Concurrent Execution

The implementation uses:

- `ExecutorService`
- `CompletableFuture`
- `AtomicBoolean`
- Synchronized state-management methods

Independent health checks execute concurrently.

The `AtomicBoolean` prevents overlapping monitoring cycles for an individual service.

The executor uses a fixed-size thread pool to limit concurrent execution resources.

The application shuts down the executor when its lifecycle ends.

### 10.4 Enterprise Considerations

The implementation includes an environment model:

- DEVELOPMENT
- STAGING
- PRODUCTION

This allows policies to carry environment-specific configuration.

A production deployment should also consider tenant isolation, authorization, durable alert history, distributed scheduling, and external notification delivery.

### 10.5 Execution

Compile using:

`javac ApplicationMonitoring.java`

Run using:

`java ApplicationMonitoring`

The program executes metric and alert tests before demonstrating service recovery.

## 11. PostgreSQL Implementation

**File:** `application_monitoring.sql`

The PostgreSQL implementation provides a relational monitoring data model with integrity enforcement, operational queries, aggregation, and workflow procedures.

### 11.1 Relational Architecture

The database models the following relationships:

| Table | Responsibility |
|---|---|
| `applications` | Application ownership and identity |
| `environments` | Development, staging, and production environments |
| `monitored_services` | Individual application services |
| `health_checks` | Registered health-check definitions |
| `monitoring_runs` | Individual monitoring executions |
| `health_check_results` | Results produced by health checks |
| `alert_policies` | Service-specific alert thresholds |
| `alerts` | Alert lifecycle and severity |
| `monitoring_audit` | Operational state-change history |

The principal relationship is:

`applications`
→ `environments`
→ `monitored_services`
→ `health_checks`
→ `monitoring_runs`
→ `health_check_results`

Alert processing is associated with monitored services and their policies.

### 11.2 Referential Integrity

Primary keys identify individual records.

Foreign keys maintain relationships between applications, environments, services, checks, and monitoring executions.

Unique constraints prevent duplicate application names, duplicate service names within an environment, and duplicate check names within a service.

Check constraints enforce valid thresholds, nonnegative latency, valid occurrence counts, and valid timestamp relationships.

### 11.3 Monitoring Results

The `health_check_results` table stores individual observations.

Its `metadata` column uses PostgreSQL `JSONB`.

This permits structured supplementary information, including HTTP response codes, dependency details, and retry information.

The JSONB column also supports indexing through a GIN index.

Sensitive credentials, tokens, and connection strings must not be stored in this field.

### 11.4 Alert Lifecycle Enforcement

The `alerts` table stores alert state, severity, timestamps, and occurrence counts.

A partial unique index prevents multiple simultaneously firing alerts for one service.

The `validate_alert_transition()` trigger prevents modification of resolved alerts and invalid state transitions.

Acknowledgement and resolution are represented separately.

The trigger provides database-level enforcement rather than relying exclusively on application validation.

### 11.5 Stored Functions and Procedures

The implementation includes:

| Database object | Responsibility |
|---|---|
| `complete_monitoring_run()` | Aggregates health results and updates service status |
| `process_service_alert()` | Creates, updates, or resolves alerts |
| `eligible_health_checks()` | Retrieves checks belonging to enabled services |
| `start_monitoring_run()` | Creates an eligible monitoring execution |
| `audit_service_status_change()` | Records service status transitions |

The monitoring workflow separates individual check results from the final service status.

A monitoring run can contain multiple health-check observations.

The completion function evaluates those observations and updates the associated service.

### 11.6 Views and Reporting

`service_metrics` aggregates observations into service-level measurements.

It calculates:

- Total checks.
- Successful checks.
- Failed checks.
- Average latency.
- Maximum latency.
- Availability percentage.

`active_alert_dashboard` joins application, environment, service, and alert information.

These views simplify operational reporting without duplicating the underlying records.

### 11.7 Indexing

The implementation creates indexes for common access patterns:

- Service status and enabled state.
- Service-specific health-check retrieval.
- Monitoring history ordered by timestamp.
- Recent health-check results.
- Alert state and severity.
- Audit history.
- JSONB metadata searches.

Time-based retrieval is particularly important because monitoring systems can generate large volumes of observations.

Large deployments should evaluate time-based partitioning for `monitoring_runs` and `health_check_results`.

### 11.8 Transactions

The SQL script uses a transaction to create the schema, tables, constraints, functions, procedures, sample records, and reporting objects.

The sample monitoring workflow starts a run, inserts a result, and completes the run within a database transaction.

This prevents partially committed monitoring operations when an execution fails.

Database transactions do not guarantee successful external notification delivery. A production notification system should use a durable outbox and retry mechanism.

### 11.9 Execution

Execute using PostgreSQL:

`psql -U postgres -d monitoring_database -f application_monitoring.sql`

The script creates the `app_monitoring` schema and its database objects.

The sample queries demonstrate service retrieval, health-check eligibility, failed-check detection, metrics aggregation, active alerts, recent failures, and audit reporting.

## 12. Monitoring Policy and State Transitions

The most important operational distinction is between an observation and an evaluated service state.

A health check reports whether one particular condition succeeded.

The service monitor combines multiple observations.

The policy engine evaluates the observations using configured thresholds.

The alert manager determines whether the resulting state requires a new alert, an update, or resolution.

The dashboard displays the resulting state.

### 12.1 Example State Evaluation

Assume a payment service has three health checks:

| Component | Result | Latency |
|---|---|---:|
| Application | Healthy | 100 ms |
| Database | Unhealthy | 180 ms |
| External provider | Healthy | 220 ms |

The database check fails.

With a failure threshold of two:

| Monitoring cycle | Consecutive failures | Service state |
|---|---:|---|
| Initial evaluation | 1 | DEGRADED |
| Second evaluation | 2 | UNHEALTHY |
| First recovery evaluation | 0 | DEGRADED |
| Second recovery evaluation | 0 | HEALTHY |

The first successful recovery observation does not immediately restore the service to healthy status.

This avoids unstable state changes during intermittent recovery.

### 12.2 Policy Differences

Not every application requires identical thresholds.

A payment service may require stricter latency and availability requirements than an internal reporting worker.

Policies should consider:

- Business criticality.
- Expected traffic.
- Dependency behavior.
- Operating environment.
- Recovery objectives.
- Alert ownership.
- Maintenance schedules.

Thresholds should be reviewed using historical performance measurements.

## 13. Reliability and Security Considerations

Application monitoring itself is an operational dependency and must be designed to remain reliable.

### 13.1 Monitoring Failures

A monitoring failure can occur independently of an application failure.

Examples include:

- Scheduler failure.
- Network interruption.
- Database unavailability.
- Monitoring worker exhaustion.
- Incorrect health-check configuration.
- Delayed metric ingestion.

A production system should distinguish monitoring-system health from monitored-application health.

Missing observations should be treated as missing data, not successful observations.

### 13.2 Authentication and Access Control

Administrative health endpoints should not expose internal infrastructure information publicly.

Monitoring systems should use:

- Authenticated service-to-service communication.
- Least-privilege database roles.
- Restricted administrative operations.
- Secure transport.
- Protected operational dashboards.
- Audited alert acknowledgements.

Health endpoints intended for public load balancers should expose only the minimum required information.

### 13.3 Sensitive Information

Health-check messages and metadata should not contain:

- Passwords.
- API keys.
- Access tokens.
- Database connection credentials.
- Private customer information.
- Sensitive infrastructure configuration.

Logs and monitoring records should be reviewed for accidental sensitive-data collection.

### 13.4 Scalability

Monitoring frequency and sample retention affect system resource consumption.

If 1,000 services execute five checks every 30 seconds:

\[
ChecksPerSecond =
\frac{1000 \times 5}{30}
\]

\[
ChecksPerSecond \approx 166.67
\]

This produces approximately 14.4 million individual observations per day.

A production system must therefore consider:

- Bounded metric retention.
- Database partitioning.
- Metric aggregation.
- Asynchronous ingestion.
- Query optimization.
- Scheduler distribution.
- Monitoring worker concurrency.
- Alert deduplication.

### 13.5 Observability Distinctions

Application monitoring is closely related to observability, but the concepts are not identical.

| Concept | Purpose |
|---|---|
| Monitoring | Tracks known operational conditions |
| Logging | Records discrete application events |
| Metrics | Quantifies system behavior over time |
| Tracing | Follows requests across distributed components |
| Alerting | Identifies conditions requiring operational attention |
| Dashboarding | Presents monitoring and observability information |

Health checks are useful for detecting known failure conditions.

Logs help explain individual events.

Metrics reveal patterns and trends.

Distributed traces help identify latency and failure propagation across service boundaries.

A complete production observability architecture combines these mechanisms.

## 14. Limitations of the Implementations

The five implementations are executable monitoring models. They demonstrate the principal domain mechanisms but are not complete distributed monitoring platforms.

| Area | Current implementation | Production consideration |
|---|---|---|
| Scheduling | Explicit monitoring cycles | Distributed scheduling and leader election |
| Health checks | Simulated application and dependency checks | Real HTTP, database, and infrastructure probes |
| Metrics | In-memory or relational storage | Dedicated time-series storage |
| Alerting | Local alert state management | Durable notification delivery |
| Dashboards | Structured terminal or JSON reporting | Authenticated interactive visualization |
| Recovery | Consecutive-success evaluation | Incident correlation and recovery verification |
| Scalability | Bounded in-memory collections and local execution | Distributed ingestion and aggregation |
| Security | Input validation and basic state protection | Full identity, authorization, encryption, and audit controls |

The JavaScript timeout example does not cancel an underlying handler automatically. Production checks should use cancellation signals and transport-level timeouts.

The C++ implementation uses references to externally owned health-check objects. Those objects must remain alive for the lifetime of their service monitors.

The Java implementation uses concurrent execution but does not provide distributed coordination between multiple application instances.

The PostgreSQL monitoring functions evaluate recorded observations. They do not independently execute HTTP requests or connect to external infrastructure.

These limitations distinguish a monitoring domain model from a fully deployed monitoring service.

## 15. Technical Concepts Implemented Across the Five Languages

| Technical area | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Health-check abstraction | Base class | Handler class | Interface | Interface | Check definitions |
| State management | Enum and dataclass | Objects and maps | Enum and structs | Enum and records | Enum columns |
| Metrics | Bounded deque | MetricStore | Accumulators | MetricService | Aggregate views |
| Alerts | AlertManager | EventEmitter | AlertManager | AlertService | Tables and procedures |
| Policy evaluation | ServiceMonitor | AlertPolicy | ServicePolicy | HealthPolicyEngine | SQL functions |
| Failure handling | Exceptions | Promise rejection | Exceptions | Custom exceptions | Constraints and triggers |
| Concurrency | Sequential cycle | Promises | Sequential evaluation | ExecutorService | Transaction processing |
| Dashboard | JSON output | Dashboard snapshot | Terminal dashboard | DashboardService | SQL views |

The implementations demonstrate different approaches to the same monitoring domain.

Python emphasizes readable simulation and rapid policy experimentation.

JavaScript emphasizes asynchronous operations and event-driven integration.

C++ emphasizes explicit interfaces and efficient in-memory state.

Java emphasizes enterprise domain modeling and concurrent execution.

PostgreSQL provides persistent relational state, integrity enforcement, workflow processing, and reporting.

The central architectural principle remains consistent: health observations, evaluated service states, alert decisions, and dashboard representations are separate operational responsibilities.
