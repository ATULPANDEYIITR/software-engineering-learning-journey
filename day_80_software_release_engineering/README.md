# Software Release Engineering

## 1. Release Engineering Fundamentals

Software Release Engineering is the discipline of preparing, validating, deploying, monitoring, and maintaining software versions across development, staging, and production environments.

A release is not simply a source-code change. It is a controlled delivery of a specific, identifiable software artifact into an operational environment.

The release process connects software development, automated testing, change management, deployment orchestration, operational monitoring, and incident recovery.

The implementations in this repository model these activities through five complementary technical approaches:

| Implementation | Engineering perspective |
|---|---|
| Python | Repository-independent release workflow simulation |
| JavaScript | Asynchronous and event-driven deployment orchestration |
| C++17 | Release governance and deployment eligibility engine |
| Java 17 | Enterprise domain model and controlled state transitions |
| PostgreSQL | Relational release management, approvals, deployment history, and auditing |

## 2. Release Lifecycle

A controlled software release follows a sequence of identifiable states.

**Development → Build → Artifact Validation → Change Approval → Deployment → Health Monitoring → Release Completion**

When deployment validation fails:

**Deployment Failure → Incident Assessment → Rollback → Previous Stable Version**

Each stage has a separate responsibility.

| Stage | Responsibility |
|---|---|
| Development | Implement and integrate application changes |
| Build | Produce a deployable software package |
| Artifact validation | Verify version, integrity, and build identity |
| Change management | Evaluate business and operational risk |
| Approval | Authorize the planned change |
| Deployment | Introduce the artifact into an environment |
| Health monitoring | Evaluate application behavior |
| Completion | Record the successful release |
| Rollback | Restore the previously active version when necessary |

### Release artifact

A release artifact is the specific output produced by a build process.

Examples include:

- Container images
- Compiled application packages
- Executable binaries
- Deployment bundles
- Versioned application archives

An artifact should have an immutable identity.

The implementations represent this identity through:

| Attribute | Purpose |
|---|---|
| Version | Identifies the software release |
| Commit hash | Identifies the source revision |
| SHA-256 digest | Identifies the artifact content |
| Build number | Identifies the build execution |

A version alone does not establish artifact integrity. Two artifacts can carry the same version label while containing different content.

The SHA-256 digest provides content identification. Production deployment should use immutable artifact references rather than rebuilding software independently in each environment.

## 3. Release Strategies

Deployment strategy determines how a new software version replaces an existing version.

The four implemented strategies have different traffic-management, infrastructure, availability, and recovery characteristics.

### 3.1 Rolling deployment

A rolling deployment replaces application instances gradually.

For example, a service running four instances can replace one instance at a time.

Conceptual sequence:

- Existing: 4 instances running version 1.0.
- First stage: 1 instance runs version 2.0.
- Second stage: 2 instances run version 2.0.
- Third stage: 3 instances run version 2.0.
- Final stage: all 4 instances run version 2.0.

The Python and C++ implementations represent this progression through traffic or rollout percentages of 25%, 50%, 75%, and 100%.

**Characteristics**

- Reuses the existing infrastructure.
- Reduces the need for a second complete production environment.
- Allows incremental replacement.
- Requires compatible application versions during the transition.
- Can expose users to mixed-version behavior.

Database schema compatibility is especially important. A database migration that removes a field still used by the previous application version can make a rolling deployment unsafe.

### 3.2 Canary deployment

A canary deployment introduces the new version to a small portion of production traffic.

The initial traffic allocation is intentionally limited.

The implementation uses this progression:

| Stage | Candidate traffic |
|---|---:|
| Initial | 5% |
| Second | 10% |
| Third | 25% |
| Fourth | 50% |
| Final | 100% |

At every stage, deployment health is evaluated.

Typical measurements include:

- Application error rate
- Response latency
- Availability
- Failed request count
- Successful request count

The deployment proceeds only when the configured health policy passes.

A canary deployment is useful when application behavior cannot be established entirely through pre-production testing.

Its principal advantage is reduced exposure to potentially defective software.

Its limitation is that low traffic may not expose problems associated with particular users, workloads, data distributions, or peak traffic conditions.

Canary monitoring should therefore include sufficient observation time and representative traffic.

### 3.3 Blue-green deployment

Blue-green deployment maintains two application environments.

- Blue represents the currently active version.
- Green represents the candidate version.

The candidate is deployed and validated in the inactive environment.

After successful validation, traffic is switched to the candidate environment.

Conceptual architecture:

    Incoming Traffic
          |
       Router
          |
       Blue / Green
        /       \
    Version 1  Version 2
      Active    Candidate

The traffic switch is represented as a 0% to 100% transition in the implementations.

**Advantages**

- Fast traffic switching.
- Clear separation between existing and candidate environments.
- Straightforward application-level rollback.
- Reduced exposure during candidate validation.

**Limitations**

- Requires additional infrastructure capacity.
- Database changes may not be reversible.
- Background jobs and scheduled processes require careful coordination.
- Both environments must be compatible with shared infrastructure.

Blue-green deployment does not automatically guarantee an atomic rollback of databases, queues, external integrations, or persistent user data.

### 3.4 Recreate deployment

A recreate deployment stops the previous application instances before starting the new version.

Its simplified sequence is:

    Stop Version 1
          |
    Deploy Version 2
          |
    Validate Version 2
          |
    Activate Version 2

This approach is straightforward but may introduce downtime.

It is appropriate when the application cannot safely run multiple versions simultaneously or when infrastructure limitations prevent parallel execution.

It requires a tested recovery process because the previous application may not remain available during deployment.

### 3.5 Strategy comparison

| Criterion | Rolling | Canary | Blue-green | Recreate |
|---|---|---|---|---|
| Gradual replacement | Yes | Yes | No | No |
| Limited initial traffic | Possible | Yes | No | No |
| Parallel environments | Not essential | Usually partial | Yes | No |
| Infrastructure overhead | Moderate | Moderate | High | Low |
| Traffic switching | Progressive | Progressive | Switch-based | After restart |
| Downtime exposure | Low when configured correctly | Low | Low | Higher |
| Recovery approach | Restore previous instances | Reduce candidate traffic | Switch back | Redeploy previous version |

The choice depends on application architecture, infrastructure capacity, traffic characteristics, data compatibility, and recovery requirements.

## 4. Change Management

Change management controls the authorization and scheduling of modifications to operational systems.

A software release may be technically deployable but still be unsuitable for production without the required organizational approval.

A change request records:

- Change title
- Technical description
- Requesting individual
- Risk classification
- Approval decisions
- Scheduled implementation period
- Final implementation status

### 4.1 Risk classification

The implementations use four risk levels.

| Risk | Typical example | Required approvals in the implementations |
|---|---|---:|
| Low | Documentation correction | 1 |
| Medium | Minor application enhancement | 1 |
| High | Database execution or authentication changes | 2 |
| Critical | High-impact infrastructure or security changes | 3 |

These are example governance rules, not universal requirements.

Organizations should define approval thresholds according to their own operational and regulatory responsibilities.

### 4.2 Change request lifecycle

    Submitted
        |
        v
    Risk Assessment
        |
        v
    Independent Review
        |
        +------ Rejected
        |
        v
    Approved
        |
        v
    Deployment
        |
        v
    Implemented

A rejected request cannot be deployed under the implemented approval policy.

The Python, JavaScript, C++, and Java implementations require the requester to be different from the reviewer.

The PostgreSQL implementation enforces this condition using a database trigger.

### 4.3 Separation of responsibilities

Release governance should distinguish between the individual requesting a change and the individuals authorizing it.

This reduces conflicts of interest and improves accountability.

Typical responsibilities include:

| Role | Responsibility |
|---|---|
| Developer | Implements the software change |
| Change requester | Submits the proposed operational change |
| Technical reviewer | Evaluates technical risk |
| Security reviewer | Evaluates security implications |
| Release manager | Coordinates release execution |
| Operations engineer | Monitors deployment and infrastructure |
| Incident responder | Coordinates recovery when deployment fails |

The examples implement independent approval checks, although a full enterprise authorization system would also enforce role membership, organizational boundaries, and time-limited permissions.

## 5. Release Health and Automated Validation

Successful artifact creation does not establish that the application is healthy after deployment.

A release must be evaluated using operational measurements.

### 5.1 Error rate

Error rate represents the proportion of requests that fail.

\[
\text{Error Rate} =
\frac{\text{Failed Requests}}
{\text{Total Requests}}
\]

A low error rate indicates that most requests are completing successfully.

The implementations use a maximum error rate of 2%.

### 5.2 Latency

Latency measures the time required to process a request.

It is expressed in milliseconds in the examples.

The implementations use a maximum latency of 500 milliseconds.

A production monitoring system should generally examine percentiles such as:

- p50
- p90
- p95
- p99

Average latency alone can conceal severe delays experienced by a small proportion of users.

### 5.3 Availability

Availability measures the proportion of time or requests during which a service remains operational, according to the selected measurement definition.

The examples use a minimum availability threshold of 99.5%.

Availability measurements should have a clearly defined observation window and denominator.

### 5.4 Health policy

The implemented health policy evaluates three conditions:

| Metric | Requirement |
|---|---|
| Error rate | At most 2% |
| Latency | At most 500 ms |
| Availability | At least 99.5% |

A candidate release fails when any required condition is violated.

These thresholds are illustrative and should be calibrated using service-level objectives and historical application behavior.

## 6. Rollback Engineering

Rollback restores an earlier known-good application version when a new release cannot operate safely.

A rollback is a recovery operation, not simply a change to a version label.

The implementations preserve the previous environment version before deployment begins.

The rollback process then restores that version and records the recovery operation.

### 6.1 Rollback workflow

    Active Version: 1.0.0
              |
       Deploy Version 2.0.0
              |
       Health Evaluation
              |
          Failure
              |
       Stop Candidate Traffic
              |
       Restore Version 1.0.0
              |
       Record Rollback Event
              |
       Verify Service Health

### 6.2 Rollback triggers

Common rollback conditions include:

- Increased application error rate.
- Excessive response latency.
- Reduced availability.
- Failed integration tests.
- Security validation failure.
- Incorrect application configuration.
- Database connectivity problems.
- Unexpected business transaction failures.

A rollback decision should use predefined operational criteria rather than relying entirely on manual judgment.

### 6.3 Application rollback versus database rollback

Application rollback and database rollback are different operations.

Application rollback restores a previous application artifact.

Database rollback attempts to restore a previous data structure or data state.

The second operation can be significantly more difficult because the candidate application may already have written data using a modified schema.

A safer migration pattern is expand-and-contract:

1. Add a backward-compatible database field or structure.
2. Deploy application code that supports both old and new structures.
3. Migrate existing data.
4. Verify the new application behavior.
5. Remove obsolete structures only after the previous application version is no longer required.

The supplied implementations restore application versions. They do not implement actual database migration reversal.

### 6.4 Rollback limitations

Rollback may not reverse:

- Completed financial transactions.
- Messages already published to queues.
- External API operations.
- Emails and notifications already sent.
- Data transformations.
- Irreversible schema changes.

For these situations, compensating transactions, idempotent operations, forward fixes, and data recovery procedures may be necessary.

## 7. Python Implementation

The Python implementation provides a repository-independent release workflow simulator.

### Architecture

| Component | Responsibility |
|---|---|
| `ReleaseArtifact` | Validates immutable artifact information |
| `ChangeRequest` | Tracks risk, approval, and rejection |
| `ChangeManager` | Creates and retrieves change requests |
| `DeploymentMetrics` | Represents operational health |
| `Release` | Maintains release state |
| `ReleaseEngine` | Controls deployment, rollback, and reporting |

### Important mechanisms

The implementation uses dataclasses to represent domain records and enums to restrict valid workflow states.

Dictionaries provide efficient lookup of releases and active environment versions.

Sets prevent duplicate reviewer approvals.

The deployment engine evaluates each traffic stage using a metrics provider.

When a health check fails, the exception-handling workflow marks the release as failed and invokes rollback.

The demonstration performs two deployments:

- Version 1.0.0 succeeds through blue-green deployment.
- Version 2.0.0 encounters a canary health failure and is rolled back.

The assertions verify that production returns to version 1.0.0.

### Design considerations

The simulator is intentionally in-memory.

It does not provide persistent storage, distributed locks, real infrastructure deployment, or integration with a container orchestrator.

The traffic percentages represent rollout stages rather than actual network routing.

The audit collection is suitable for demonstration but would require durable, append-only storage in production.

## 8. JavaScript Implementation

The JavaScript implementation focuses on asynchronous release orchestration and event-driven monitoring.

### Architecture

| Component | Responsibility |
|---|---|
| `ReleaseArtifact` | Validates immutable artifact metadata |
| `ChangeRequest` | Manages independent approvals |
| `HealthPolicy` | Evaluates operational measurements |
| `ReleaseManager` | Orchestrates deployment |
| `EventEmitter` | Publishes release lifecycle events |
| `metricsProvider` | Supplies asynchronous health measurements |

### Event-driven architecture

The `ReleaseManager` extends Node.js `EventEmitter`.

It publishes events representing important workflow transitions:

- `release.created`
- `release.validating`
- `release.deploying`
- `traffic.updated`
- `health.evaluated`
- `release.succeeded`
- `release.failed`
- `release.rolled_back`

Event consumers can observe release activity without being tightly coupled to the deployment implementation.

The metrics provider returns a Promise, allowing deployment orchestration to wait for external monitoring operations.

### Concurrency control

The manager uses an environment lock represented by a `Set`.

This prevents two deployments from modifying the same environment simultaneously within the process.

The lock is released through a `finally` block, including when deployment fails.

This mechanism is process-local. Distributed deployment systems require shared coordination through a database, lease service, or deployment platform.

### Failure handling

The example intentionally introduces excessive error rates and latency for version 2.0.0 when traffic reaches 25%.

The health policy rejects the deployment.

The manager restores the previous environment version and publishes a rollback event.

## 9. C++17 Implementation

The C++ implementation emphasizes domain modeling, controlled state changes, and explicit release governance.

### Main components

| Component | Responsibility |
|---|---|
| `Artifact` | Validates artifact metadata |
| `ChangeRequest` | Enforces risk-based approval |
| `StatusCheck` | Represents automated validation |
| `HealthMetrics` | Evaluates deployment health |
| `Release` | Stores deployment state |
| `EnvironmentRegistry` | Tracks active versions |
| `ReleaseEngine` | Enforces deployment rules |

### Data structures

The implementation uses:

- `map` for environment and release registries.
- `set` for unique reviewer identities.
- `vector` for traffic stages, checks, and observations.
- `optional` for environments without a previous active version.

The environment registry provides a clear separation between the candidate release and the currently active software version.

A release can be created without changing the active environment.

The active version changes only after successful deployment.

### Failure handling

The engine validates automated status checks before entering the deployment process.

It then evaluates each traffic stage using supplied health observations.

A failed observation raises an exception, causing the deployment to enter the failed state.

Rollback restores the stored previous version.

The environment lock prevents simultaneous deployments within the engine instance.

### Complexity considerations

| Operation | Expected complexity |
|---|---|
| Release lookup | O(log n) |
| Environment lookup | O(log n) |
| Reviewer insertion | O(log r) |
| Status-check evaluation | O(c) |
| Traffic progression | O(t) |
| Report generation | O(n) |

Here, n represents releases, r represents reviewers, c represents checks, and t represents deployment stages.

The implementation uses the standard library and requires no external dependencies.

## 10. Java 17 Implementation

The Java implementation models enterprise release governance through explicit domain types and service boundaries.

### Architecture

| Component | Responsibility |
|---|---|
| `Artifact` record | Immutable artifact metadata |
| `ChangeRequest` | Change approval and state |
| `StatusCheck` record | Automated validation |
| `HealthPolicy` | Operational thresholds |
| `Metrics` record | Deployment observations |
| `Release` | Release lifecycle |
| `EnvironmentRegistry` | Active environment state |
| `ReleaseService` | Deployment and rollback orchestration |
| `AuditEvent` record | Structured audit history |
| `MetricsProvider` | Health measurement interface |

### Records and immutability

Java records represent immutable values such as artifacts, metrics, status checks, and audit events.

This reduces accidental modification of data that should remain stable throughout a deployment.

Release objects maintain mutable lifecycle state because their status and traffic allocation change during execution.

### Service separation

The `ReleaseService` coordinates:

- Change authorization.
- Status-check validation.
- Deployment strategy selection.
- Environment locking.
- Health evaluation.
- Successful activation.
- Rollback.
- Audit recording.

The `MetricsProvider` interface separates deployment orchestration from the source of monitoring measurements.

An actual implementation could obtain these measurements from an observability platform or deployment monitoring service.

### Thread safety

The Java implementation uses `ReentrantLock` to prevent simultaneous deployments in the same environment.

Change approval methods are synchronized.

Environment operations use synchronized methods.

These controls demonstrate in-process concurrency management. A multi-instance deployment platform requires distributed coordination.

## 11. PostgreSQL Implementation

The PostgreSQL implementation models release management as a relational workflow.

### Relational architecture

    Repositories
        |
        +---- Release Users
        |         |
        |      Repository Roles
        |
        +---- Environments
        |
        +---- Release Artifacts
        |
        +---- Change Requests
        |         |
        |      Change Approvals
        |
        +---- Releases
                  |
                  +---- Deployment Checks
                  |
                  +---- Deployments
                  |         |
                  |      Deployment Metrics
                  |
                  +---- Rollback Events
                  |
                  +---- Release Audit

### Main tables

| Table | Purpose |
|---|---|
| `repositories` | Stores software repository information |
| `release_users` | Stores release participants |
| `release_roles` | Defines organizational roles |
| `user_repository_roles` | Associates users with repository roles |
| `environments` | Stores environment and active version |
| `release_artifacts` | Stores immutable artifact identities |
| `change_requests` | Records requested changes |
| `change_approvals` | Records approval decisions |
| `releases` | Stores release execution state |
| `deployment_checks` | Records automated validation |
| `deployments` | Stores deployment executions |
| `deployment_metrics` | Stores health observations |
| `rollback_events` | Records rollback operations |
| `release_audit` | Stores lifecycle events |
| `release_policies` | Defines environment-specific rules |

### Constraints and integrity

Primary keys uniquely identify records.

Foreign keys maintain relationships between repositories, artifacts, changes, users, and deployments.

Unique constraints prevent duplicate repository names, versions within a repository, build numbers, and reviewer decisions for a change.

Check constraints validate:

- Artifact digest structure.
- Build numbers.
- Traffic percentages.
- Health metric ranges.
- Deployment execution numbers.
- Approval decision values.
- Change scheduling intervals.

### Approval automation

The function `required_change_approvals()` calculates approval requirements according to change risk.

The trigger `trg_validate_change_approval` prevents requesters from approving their own changes.

The trigger `trg_update_change_approval_status` updates the change status when sufficient independent approvals are received.

The implementation also rejects approval attempts from inactive users.

### Release eligibility

The function `check_release_eligibility()` evaluates whether a release can proceed.

It examines:

- Release existence.
- Current release state.
- Change approval.
- Repository and environment association.
- Release policy availability.
- Artifact integrity.
- Required automated checks.

The function returns a Boolean eligibility result and an explanatory reason.

The deployment policy is stored independently from the release record so that different environments can apply different requirements.

### State transition enforcement

The trigger `trg_release_state_transition` restricts release state transitions.

The permitted progression is:

    created
       |
       v
    validating
       |
       v
    deploying
       |
       +------ succeeded
       |
       +------ failed
                   |
                   v
               rolled_back

A successfully deployed release can also be rolled back when operational conditions require recovery.

The trigger prevents arbitrary transitions such as moving directly from `created` to `succeeded`.

### Transactional rollback

The procedure `rollback_release()` restores the previously recorded environment version.

It also:

- Updates the release state.
- Resets traffic allocation.
- Creates a rollback event.
- Records the initiating user.
- Writes an audit entry.

The procedure should be executed within a transaction so that the recovery records and environment update remain consistent.

### Indexing

The implementation creates indexes for frequently accessed data:

- Change status and risk.
- Repository change history.
- Release environment and status.
- Release creation time.
- Deployment execution history.
- Deployment metrics by observation time.
- Release audit history.
- JSONB audit details.

A partial unique index prevents multiple active deployments in the same environment.

This is particularly important because application-level validation alone cannot reliably prevent concurrent deployment attempts.

## 12. Release Governance and Operational Security

Release engineering must protect both the deployment process and the software being deployed.

### Artifact security

Production artifacts should be traceable to their source commits and build executions.

Recommended controls within a release platform include:

- Immutable artifact storage.
- SHA-256 digest verification.
- Signed build provenance.
- Software composition analysis.
- Vulnerability scanning.
- Restricted production deployment permissions.
- Artifact retention policies.

A digest establishes artifact identity but does not independently prove that the artifact is trustworthy.

### Approval security

Approval decisions should be associated with authenticated users.

Production systems should enforce:

- Role-based authorization.
- Independent approval.
- Separation of duties.
- Reviewer eligibility.
- Approval expiry where appropriate.
- Recorded rejection reasons.
- Complete audit history.

The sample implementations demonstrate independent reviewers but do not provide a complete identity and access management system.

### Deployment security

Deployment credentials should have restricted permissions.

Secrets should not be embedded in application source files, artifact metadata, or audit messages.

Production deployment should use controlled service identities, encrypted communication, and environment-specific permissions.

### Auditability

A release audit should answer:

- Who requested the change?
- Who approved it?
- Which artifact was deployed?
- Which environment received it?
- Which deployment strategy was used?
- Which checks passed or failed?
- What operational measurements were observed?
- Was the deployment successful?
- Was rollback performed?
- Which version was restored?

The PostgreSQL audit table provides a structured foundation for these records.

A production audit system should additionally restrict modification and deletion of historical records.

## 13. Failure Scenarios and Recovery

| Failure | Detection mechanism | Appropriate response |
|---|---|---|
| Invalid artifact digest | Artifact validation | Reject release |
| Missing approval | Change authorization | Block deployment |
| Failed unit tests | Deployment checks | Block deployment |
| Security scan failure | Security validation | Block deployment |
| High error rate | Health monitoring | Stop rollout and assess rollback |
| Excessive latency | Performance monitoring | Stop rollout and investigate |
| Low availability | Availability monitoring | Initiate recovery |
| Concurrent deployment | Environment locking | Reject competing deployment |
| Incorrect database migration | Migration validation | Apply recovery or compensating migration |
| Failed rollback | Recovery verification | Escalate to incident response |

Rollback should itself be monitored and validated.

A completed rollback command does not establish that the application is healthy. Recovery verification must confirm that the previous version is serving traffic and that critical business operations are functioning.

## 14. Implementation Limitations

The five implementations are educational release-governance models rather than production deployment platforms.

| Capability | Implemented | Not implemented |
|---|---|---|
| Release artifact validation | Yes | Signed provenance verification |
| Risk-based change approvals | Yes | Complete enterprise identity management |
| Rolling deployment model | Yes | Real instance replacement |
| Canary deployment model | Yes | Actual load-balancer routing |
| Blue-green deployment model | Yes | Infrastructure provisioning |
| Recreate deployment model | Yes | Real service shutdown and startup |
| Health evaluation | Yes | External monitoring integration |
| Automatic rollback logic | Yes | Guaranteed distributed recovery |
| Environment version tracking | Yes | Multi-region synchronization |
| Audit history | Yes | Tamper-proof external audit storage |
| Relational workflow | Yes | Distributed transaction coordination |
| Environment locking | In-process implementations | Distributed lease management |

The implementations intentionally separate release orchestration, change authorization, operational health, and persistent data management.

This separation makes it possible to evaluate a deployment independently from the correctness of the artifact, the approval decision, and the operational condition of the target environment.
