# CI/CD Pipelines: Pipeline Stages and Automation

## 1. Project Overview

This project implements a Continuous Integration and Continuous Delivery/Deployment (CI/CD) pipeline architecture using Python, JavaScript, C++17, Java 17, and PostgreSQL.

The central engineering problem is automating the movement of software changes from source control through compilation, testing, security validation, artifact production, approval, and deployment.

A CI/CD pipeline establishes a repeatable sequence of operations that validates software changes and controls their release into target environments.

The implementations examine five complementary perspectives:

| Implementation | Primary responsibility |
|---|---|
| Python | Pipeline simulation and sequential stage orchestration |
| JavaScript | Asynchronous event-driven pipeline execution |
| C++17 | Pipeline execution and deployment governance |
| Java 17 | Enterprise pipeline lifecycle and deployment services |
| PostgreSQL | Persistent pipeline, artifact, approval, and deployment management |

## 2. CI/CD Fundamentals

### Continuous Integration

Continuous Integration (CI) is the practice of frequently integrating source-code changes into a shared repository and automatically validating those changes.

Typical CI operations include:

- Source checkout.
- Dependency installation.
- Compilation and build.
- Static code analysis.
- Unit testing.
- Integration testing.
- Security scanning.
- Test coverage evaluation.
- Build artifact creation.

The purpose is to detect defects close to the point where changes are introduced.

### Continuous Delivery

Continuous Delivery (CD) extends CI by preparing validated software for release.

The resulting artifact is deployable, but production release may require an explicit human approval.

### Continuous Deployment

Continuous Deployment automatically releases every qualifying change into production after all configured quality and governance requirements have passed.

The distinction is important:

| Practice | Production release |
|---|---|
| Continuous Integration | Not necessarily included |
| Continuous Delivery | Release-ready; may require approval |
| Continuous Deployment | Automatically released after successful validation |

A pipeline can implement CI and Continuous Delivery without permitting unrestricted production deployment.

## 3. Pipeline Architecture

A representative pipeline follows this execution structure:

Source Repository
    |
    v
Trigger Detection
    |
    v
Source Checkout
    |
    v
Build and Dependency Resolution
    |
    v
Unit Testing
    |
    v
Integration Testing
    |
    v
Static Analysis and Security Scanning
    |
    v
Artifact Packaging
    |
    v
Approval Gate
    |
    v
Deployment
    |
    v
Post-Deployment Validation
    |
    v
Monitoring and Audit

Each stage has a defined responsibility, execution result, dependency relationship, and failure policy.

Stages should not be treated as interchangeable operations. A successful compilation does not establish that an application is secure, functionally correct, or suitable for production.

## 4. Pipeline Stages

### 4.1 Trigger Detection

A trigger determines when a pipeline should execute.

The implementations model the following trigger categories:

| Trigger | Purpose |
|---|---|
| PUSH | Execute after a branch receives a commit |
| PULL_REQUEST | Validate proposed repository changes |
| SCHEDULED | Execute at a configured time |
| MANUAL | Execute through an authorized operator |
| RELEASE | Validate or publish a release |

Trigger filtering can use branch names, changed paths, tags, repository events, and release metadata.

A production implementation should authenticate incoming webhook events, verify their signatures, reject replayed events, and avoid executing untrusted event payloads as commands.

### 4.2 Source Checkout

Checkout retrieves the repository contents corresponding to a specific commit.

The commit SHA identifies the source revision used by the execution.

This distinction matters because branch names are mutable references. A branch can point to a different commit while an existing pipeline is executing.

Recording the exact commit SHA makes execution results traceable and reproducible.

### 4.3 Build

The build stage transforms source code into an executable application or distributable package.

Typical operations include:

- Dependency resolution.
- Compilation.
- Resource processing.
- Configuration validation.
- Executable generation.

Build failures prevent dependent stages from proceeding.

Dependencies should be pinned or locked to reduce unexpected differences between executions.

### 4.4 Unit Testing

Unit tests validate individual functions, methods, classes, and isolated application components.

The Python implementation models configuration, core logic, input validation, and error-handling tests.

The JavaScript implementation uses structured test-case results.

The Java implementation evaluates test results using collections and streams.

Unit-test reports should distinguish:

- Passed tests.
- Failed tests.
- Skipped tests.
- Total tests.
- Execution duration.
- Coverage percentage.

A successful build does not imply successful unit testing.

### 4.5 Integration Testing

Integration tests evaluate communication and behavior across multiple application components.

Examples include:

- Application-to-database communication.
- API-to-service integration.
- Authentication and authorization flows.
- Message queue processing.
- External service interaction.

Integration testing generally requires controlled infrastructure and test data.

Test environments should be isolated from production data and production credentials.

### 4.6 Security Scanning

Security validation examines application code, dependencies, configuration, and build artifacts.

Common categories include:

| Security validation | Purpose |
|---|---|
| SAST | Identifies potential vulnerabilities in source code |
| SCA | Identifies vulnerable or noncompliant dependencies |
| Secret scanning | Detects exposed credentials and tokens |
| Container scanning | Examines container images |
| Infrastructure scanning | Evaluates infrastructure configuration |
| DAST | Tests running application behavior |

The implementations model critical and high-severity findings as deployment-blocking conditions.

A real implementation should also define vulnerability exceptions, expiry dates, ownership, remediation deadlines, and audit records.

Security scan success must represent an actual scanner result rather than the absence of manually populated findings.

### 4.7 Packaging

Packaging creates a deployable software artifact.

An artifact can be:

- A container image.
- A compiled executable.
- A compressed application package.
- A library.
- A deployment bundle.

Each artifact is associated with a version and checksum.

The checksum supports integrity verification. It does not independently establish authenticity.

Artifact authenticity requires trusted provenance, access control, and, where appropriate, digital signatures.

### 4.8 Approval Gate

An approval gate introduces an explicit authorization decision before a controlled operation.

Typical approval scenarios include:

- Production deployment.
- High-risk releases.
- Security-sensitive changes.
- Regulated application releases.

The approval decision should be associated with an authorized reviewer, deployment environment, pipeline execution, timestamp, and decision.

A successful automated pipeline does not automatically imply production authorization.

### 4.9 Deployment

Deployment transfers an approved artifact into a target environment.

The implementations distinguish three environments:

| Environment | Purpose |
|---|---|
| Development | Early application validation |
| Staging | Pre-production verification |
| Production | Live application operation |

A production deployment should reference the same validated artifact produced by the pipeline.

Rebuilding different source after approval can invalidate the relationship between the reviewed changes, tested artifact, and deployed application.

### 4.10 Post-Deployment Validation

Post-deployment validation checks whether the application operates correctly after release.

Typical checks include:

- Application health endpoints.
- API availability.
- Database connectivity.
- Service readiness.
- Error rates.
- Response latency.
- Critical business transactions.

A deployment operation can complete successfully while the application remains unhealthy.

Therefore, deployment completion and application health should be represented as separate outcomes.

## 5. Pipeline Dependencies and Execution Models

### Directed Acyclic Graph

A pipeline can be represented as a Directed Acyclic Graph (DAG).

A stage is represented by a vertex. A dependency is represented by a directed edge.

For example:

    checkout
       |
       v
      build
     /  |  \
    v   v   v
   unit integration security
    \   |   /
     \  |  /
       v
     package
       |
       v
     approval
       |
       v
     deploy

The package stage depends on successful completion of all three validation stages.

A DAG provides two important properties:

1. Dependencies determine which stages can execute.
2. Independent stages can execute concurrently.

A cycle is invalid because it creates an impossible dependency sequence.

### Topological Sorting

The Python and C++ implementations use dependency-based topological ordering.

The JavaScript implementation uses depth-first traversal with three-color cycle detection.

The Java implementation uses an indegree-based dependency traversal.

For a graph containing V stages and E dependency edges, topological sorting takes:

- Time complexity: O(V + E).
- Space complexity: O(V + E).

### Sequential and Parallel Execution

The Python implementation uses sequential execution.

This simplifies state management and makes failure propagation explicit.

The JavaScript implementation uses asynchronous execution with a configurable concurrency limit.

Independent stages can execute simultaneously.

For example, unit tests and security scans can run after the build stage without waiting for each other.

Concurrency improves throughput, but shared files, mutable artifacts, external service limits, and resource contention must be controlled.

The C++ and Java implementations use explicit sequential orchestration to demonstrate deterministic execution and enterprise governance decisions.

## 6. Failure Handling and Retry Policies

Pipeline failures can originate from:

- Compilation errors.
- Dependency resolution failures.
- Unit-test failures.
- Integration-test failures.
- Security violations.
- Artifact creation errors.
- Missing approvals.
- Deployment infrastructure failures.
- Application health-check failures.

The implementations use explicit stage states:

| State | Meaning |
|---|---|
| PENDING | Stage has not started |
| RUNNING | Stage is executing |
| SUCCESS | Stage completed successfully |
| FAILED | Stage execution failed |
| SKIPPED | Stage was not executed |

### Retry Mechanism

A retry policy defines the maximum execution attempts and optional delay.

For example, a stage with two retries can execute up to three times.

Retries are appropriate for temporary failures such as network interruptions or transient infrastructure errors.

They are not an appropriate response to deterministic failures such as compilation errors, invalid application configuration, or unresolved security violations.

Production systems should use bounded exponential backoff, jitter, and explicit retry classification.

### Timeout Management

Timeouts prevent an unresponsive stage from blocking the pipeline indefinitely.

The JavaScript implementation races stage execution against a timeout.

A timeout must also be propagated to the underlying operation. Merely stopping the wait does not necessarily terminate a process or network request that is still running.

### Failure Propagation

When a required stage fails, dependent stages must not proceed.

The implementations record skipped stages and preserve failure information.

A production scheduler may permit independent stages to finish after another branch fails, but it must not release an artifact until all required gates succeed.

## 7. Artifact Management and Integrity

A build artifact represents the output of a specific pipeline execution.

Its metadata includes:

- Artifact name.
- Version.
- Source commit.
- Checksum.
- Size.
- Storage location.
- Creation timestamp.
- Pipeline execution identifier.

The Python implementation calculates SHA-256 checksums using the standard library.

The JavaScript implementation uses Node.js cryptographic capabilities.

The C++ implementation models artifact metadata explicitly.

The Java implementation represents artifacts using immutable records.

PostgreSQL persists artifact metadata and enforces uniqueness within an execution.

### Reproducibility

Reproducible builds aim to produce equivalent outputs from identical source and controlled build inputs.

Factors affecting reproducibility include:

- Dependency versions.
- Compiler versions.
- Build environment.
- Operating system.
- Environment variables.
- Time-dependent build metadata.
- External package availability.

### Artifact Promotion

A preferred release model is:

    Build Once
        |
        v
    Validate Artifact
        |
        v
    Deploy to Development
        |
        v
    Promote to Staging
        |
        v
    Approve Release
        |
        v
    Promote to Production

The same artifact should be promoted across environments rather than independently rebuilt for each environment.

## 8. Python Implementation

The Python file implements a pipeline simulation engine using standard-library features.

### Main Components

| Component | Responsibility |
|---|---|
| `RetryPolicy` | Controls retry attempts and delay |
| `Artifact` | Stores artifact content and checksum |
| `StageResult` | Records execution outcomes |
| `PipelineContext` | Maintains pipeline-wide state |
| `Stage` | Defines executable stage behavior |
| `Pipeline` | Validates and executes the workflow |

### Execution Mechanism

The pipeline stores stages in a dictionary.

Dependencies are resolved using indegree-based topological sorting.

Each stage executes only after its dependencies succeed.

The execution engine records:

- Stage state.
- Attempt count.
- Duration.
- Error details.
- Output metadata.

The context stores artifacts and execution results separately.

This prevents the pipeline definition from becoming mixed with individual execution data.

### Validation and Failure Cases

The script checks:

- Duplicate stage names.
- Missing dependencies.
- Circular dependencies.
- Self-dependencies.
- Invalid retry settings.
- Missing artifacts.
- Missing deployment approvals.

It also executes assertions covering successful execution, dependency-cycle detection, and production approval rejection.

### Report Persistence

The report is serialized to JSON.

A production reporting service should additionally enforce restrictive file permissions, protect sensitive information, and use controlled artifact storage.

## 9. JavaScript Implementation

The JavaScript file provides an asynchronous event-driven execution model.

### Main Components

| Component | Responsibility |
|---|---|
| `PipelineContext` | Maintains execution state |
| `PipelineStage` | Defines stage configuration |
| `Artifact` | Stores immutable artifact metadata |
| `Pipeline` | Coordinates asynchronous execution |
| `EventEmitter` | Publishes lifecycle events |

### Event-Driven Execution

The pipeline emits events including:

- `pipeline_started`
- `stage_started`
- `stage_attempt_failed`
- `stage_succeeded`
- `pipeline_succeeded`
- `pipeline_failed`

These events provide a foundation for monitoring, logging, dashboards, and external notifications.

### Concurrency

The scheduler maintains three collections:

- Pending stages.
- Completed stages.
- Running stages.

A stage becomes eligible when all dependencies are completed successfully.

The configurable concurrency limit controls the number of simultaneous operations.

### Timeout and Retry Behavior

Each stage has a timeout and bounded retry count.

The implementation records individual failed attempts and applies a delay before retrying.

One important production limitation is that a Promise timeout does not cancel the underlying operation. Production integrations should use `AbortController` or an equivalent cancellation mechanism wherever supported.

The scheduler also waits for already-running tasks before returning its final execution result.

## 10. C++17 Implementation

The C++ implementation focuses on repository and deployment governance.

### Domain Components

| Component | Responsibility |
|---|---|
| `Repository` | Maintains repository branches |
| `Branch` | Represents source and target branch state |
| `PullRequest` | Represents a proposed repository change |
| `PipelineStage` | Defines a stage and its dependencies |
| `PipelineEngine` | Executes and evaluates stages |
| `Artifact` | Stores release artifact metadata |
| `GovernanceEngine` | Determines deployment eligibility |

### Repository State Versus Proposed Changes

A Pull Request proposes changes from a source branch to a target branch.

It does not itself change the target branch.

The repository maintains branch references and their commit identifiers.

The pipeline evaluates the proposed source revision independently of whether the target branch has subsequently changed.

This distinction is essential when validating a release.

### Governance Evaluation

The `GovernanceEngine` evaluates:

- Pull Request state.
- Draft status.
- Merge conflicts.
- Review conversation resolution.
- Source synchronization.
- Approval count.
- Independent reviewer approval.
- Security approval.
- Pipeline success.
- Artifact integrity metadata.
- Environment restrictions.

The engine returns a structured decision containing eligibility and rejection reasons.

### Complexity

The stage dependency ordering uses maps, sets, and vectors.

For V stages and E dependencies:

- Topological sorting: O(V + E) expected with the selected associative structures, excluding ordering overhead.
- Dependency lookup: O(log V) using `std::map`.
- Execution: Depends on individual stage operations.

The implementation uses standard C++17 facilities without third-party dependencies.

## 11. Java 17 Implementation

The Java implementation models an enterprise pipeline service with explicit domain types and controlled state transitions.

### Enterprise Domain Model

| Component | Responsibility |
|---|---|
| `Commit` | Identifies the exact source revision |
| `Artifact` | Represents an immutable release artifact |
| `PipelineContext` | Stores execution-level information |
| `PipelineStage` | Defines stage behavior |
| `StageAction` | Provides the execution interface |
| `Pipeline` | Manages lifecycle and dependencies |
| `ApprovalPolicy` | Defines approval requirements |
| `PullRequest` | Stores release-related repository state |
| `MergeEligibilityService` | Evaluates merge requirements |
| `DeploymentService` | Controls deployment and rollback |

### Records and Immutability

Java records represent immutable data structures such as:

- Commit.
- Artifact.
- AuditEvent.
- StageExecution.
- ApprovalPolicy.
- PullRequest.
- EligibilityResult.

Immutable structures reduce accidental changes to execution evidence and governance decisions.

### Service Separation

The pipeline engine performs stage execution.

The merge eligibility service evaluates repository and review conditions.

The deployment service performs deployment-state transitions.

This separation prevents a successful pipeline from being treated as automatic permission to deploy.

### State Transitions

A pipeline moves through:

    CREATED
       |
       v
    RUNNING
       |
       +------> FAILED
       |
       v
    SUCCESS

A deployment has a separate lifecycle:

    NOT_STARTED
       |
       +------> REJECTED
       |
       v
    DEPLOYED
       |
       v
    ROLLED_BACK

A rollback is valid only after a completed deployment.

The sample program records audit events for important operations.

## 12. PostgreSQL Database Architecture

The SQL implementation provides persistent relational storage for the pipeline workflow.

It uses the `cicd` schema to separate pipeline-related data from unrelated application data.

### Core Entity Relationships

    Users
      |
      +------ Repositories
                 |
                 +------ Branches
                 |          |
                 |          +------ Commits
                 |
                 +------ Pull Requests
                 |
                 +------ Pipelines
                            |
                            +------ Pipeline Stages
                            |          |
                            |          +------ Dependencies
                            |
                            +------ Pipeline Runs
                                       |
                                       +------ Stage Executions
                                       |          |
                                       |          +------ Test Results
                                       |          |
                                       |          +------ Security Results
                                       |
                                       +------ Artifacts
                                       |
                                       +------ Deployment Approvals
                                       |
                                       +------ Deployments
                                                  |
                                                  +------ Environments

### Principal Tables

| Table | Purpose |
|---|---|
| `users` | Repository and deployment identities |
| `repositories` | Repository metadata |
| `branches` | Branch references and protection state |
| `commits` | Commit metadata |
| `pull_requests` | Proposed repository changes |
| `pull_request_commits` | Commit membership in Pull Requests |
| `pipelines` | Pipeline definitions |
| `pipeline_stages` | Configured execution stages |
| `stage_dependencies` | Stage dependency relationships |
| `pipeline_runs` | Individual pipeline executions |
| `stage_executions` | Individual stage results |
| `artifacts` | Build artifact metadata |
| `test_results` | Test execution evidence |
| `security_scan_results` | Security validation evidence |
| `deployment_environments` | Deployment targets |
| `deployment_policies` | Environment-specific requirements |
| `deployment_approvals` | Release authorization decisions |
| `deployments` | Deployment history |
| `audit_events` | Operational audit information |

### Referential Integrity

Foreign keys ensure that pipeline executions, artifacts, approvals, and deployments reference valid records.

Unique constraints prevent duplicate repository names within an owner, duplicate pipeline names within a repository, and duplicate stage names within a pipeline.

Check constraints restrict invalid status values, negative retry counts, invalid coverage percentages, and inconsistent test totals.

### Dependency Integrity

The `validate_stage_dependency()` trigger ensures that a stage cannot depend on a stage belonging to another pipeline.

Self-dependencies are rejected through a check constraint.

The implementation does not provide a recursive cycle-detection trigger for the entire dependency graph. The application execution engines perform cycle validation before running a pipeline.

### Deployment Integrity

The `validate_deployment()` trigger verifies that:

- The artifact belongs to the selected pipeline execution.
- The deployment environment belongs to the same repository.
- The environment is enabled.
- A successful pipeline is required before recording a successful deployment.

The `evaluate_deployment()` function performs additional policy evaluation.

### Deployment Eligibility

Eligibility is determined from several independent sources:

1. Pipeline execution status.
2. Artifact immutability.
3. Test coverage.
4. Security scan results.
5. Approval decisions.
6. Environment-specific policy.

The function returns a Boolean eligibility decision and an explanatory reason.

The `process_deployment()` procedure performs eligibility evaluation and records the deployment and audit event within the calling transaction.

The row lock on the pipeline run reduces the risk of concurrent deployment processing for the same run.

Production systems should also use appropriate uniqueness constraints, isolation policies, and deployment locks to prevent conflicting releases.

### Reporting

The database includes:

- `pipeline_run_summary` for execution reporting.
- `deployment_audit_summary` for release history.
- CTE-based approval aggregation.
- Stage-level failure and duration analysis.
- Direct deployment eligibility evaluation.
- Audit event aggregation.

Indexes support common repository, pipeline, execution-status, commit, deployment, and audit retrieval operations.

## 13. Four Distinct CI/CD Control Layers

The implementations distinguish pipeline automation from repository governance.

These mechanisms are related but perform different responsibilities.

| Mechanism | Responsibility |
|---|---|
| Pull Request | Provides the workflow for proposing repository changes |
| Code Review | Evaluates the quality and correctness of proposed changes |
| Approvals | Record review and authorization decisions |
| Branch Protection | Enforces repository-level requirements before merging |
| CI Pipeline | Automatically validates source changes |
| Deployment Policy | Controls release eligibility |
| Deployment Approval | Authorizes a controlled release operation |

A successful CI pipeline does not replace Code Review.

A reviewer approval does not establish that automated tests passed.

A successful pipeline and sufficient approvals do not bypass protected-branch requirements.

Similarly, merge eligibility and production deployment eligibility are separate decisions.

The source branch, target branch, proposed changes, pipeline execution, and deployed artifact should remain independently identifiable.

## 14. Security and Operational Controls

A production CI/CD system should enforce the following controls.

### Access Control

- Use least-privilege service identities.
- Restrict production deployment permissions.
- Separate build and deployment identities.
- Require authorized release approvers.
- Prevent unauthorized pipeline modification.

### Secrets Management

- Store credentials in an approved secrets manager.
- Avoid hardcoded passwords and API keys.
- Mask sensitive values in pipeline logs.
- Rotate deployment credentials.
- Use short-lived credentials where possible.

### Supply Chain Security

- Pin dependencies.
- Verify dependency integrity.
- Scan source and third-party packages.
- Generate software bills of materials.
- Preserve artifact provenance.
- Sign release artifacts.
- Verify signatures before deployment.

### Pipeline Isolation

- Use isolated execution environments.
- Restrict network access where possible.
- Avoid sharing privileged runners with untrusted builds.
- Prevent untrusted Pull Request code from accessing production secrets.
- Use resource quotas and execution limits.

### Auditability

Record:

- Pipeline initiator.
- Repository and commit.
- Pipeline version.
- Stage outcomes.
- Artifact checksum.
- Security scan results.
- Approval decisions.
- Deployment identity.
- Deployment environment.
- Rollback operations.

Audit records should be access-controlled and protected against unauthorized modification.

## 15. Performance and Scalability

Pipeline efficiency depends on execution time, dependency structure, resource availability, and external service performance.

| Technique | Engineering benefit |
|---|---|
| Parallel stage execution | Reduces independent stage waiting time |
| Dependency caching | Reduces repeated downloads |
| Incremental builds | Avoids unnecessary compilation |
| Test partitioning | Distributes test execution |
| Artifact reuse | Avoids unnecessary rebuilds |
| Containerized runners | Improves environment consistency |
| Bounded concurrency | Controls resource consumption |
| Retention policies | Limits storage growth |

Parallel execution must respect dependency ordering.

A pipeline with ten independent tests can benefit from parallel execution, while a deployment stage must still wait for all required validation stages.

Caching must account for dependency versions, compiler settings, platform differences, and cache integrity.

## 16. Failure Scenarios and Expected Behavior

| Scenario | Expected response |
|---|---|
| Checkout failure | Stop dependent stages |
| Build failure | Do not execute dependent tests |
| Unit-test failure | Block packaging |
| Security violation | Block release |
| Missing artifact | Reject deployment |
| Missing approval | Reject protected deployment |
| Outdated source branch | Require synchronization and validation |
| Dependency cycle | Reject pipeline configuration |
| Stage timeout | Record failure and apply retry policy |
| Deployment failure | Record failure and initiate controlled recovery |
| Unhealthy application | Stop rollout or perform rollback |
| Missing audit evidence | Reject operations requiring that evidence |

A failed deployment should not automatically trigger an uncontrolled rollback.

Rollback should be an explicit operation using a known-good artifact and a defined recovery policy.

## 17. Limitations and Design Boundaries

These implementations are educational execution and governance models rather than complete distributed CI/CD platforms.

| Area | Current implementation | Production consideration |
|---|---|---|
| Source checkout | Simulated metadata | Actual version-control integration |
| Build | Simulated build output | Real compiler and build system |
| Testing | Deterministic sample results | Actual test runners |
| Security scanning | Modeled scanner findings | Integrated security scanners |
| Artifact storage | Metadata and sample content | Durable object or registry storage |
| Deployment | Modeled state transitions | Infrastructure deployment integration |
| Monitoring | Event and audit records | Centralized observability |
| Scheduling | Sequential or bounded concurrency | Distributed job scheduling |
| Approval | Local approval state or records | Authenticated identity and authorization |
| Recovery | Basic rollback state | Versioned deployment and recovery orchestration |

The SQL schema records pipeline evidence but does not implement a complete distributed worker queue.

The C++ and Java programs provide local governance models rather than production repository-hosting integrations.

The Python implementation is sequential and does not provide distributed execution.

The JavaScript implementation provides bounded asynchronous scheduling but requires cancellation-aware operations for complete timeout enforcement.

## 18. Execution Requirements

| File | Runtime | External dependencies |
|---|---|---|
| Python | Python 3.10+ | None |
| JavaScript | Node.js 18+ | None |
| C++17 | C++17 compiler | None |
| Java | Java 17 | None |
| PostgreSQL | PostgreSQL 15+ | `pgcrypto` extension |

The Python script writes `pipeline_report.json` in its working directory.

The JavaScript program writes `pipeline_report.json` in its working directory.

The C++ program prints repository state, pipeline execution results, and deployment eligibility.

The Java program prints pipeline results, merge eligibility, deployment state, rollback state, and audit-event count.

The SQL script creates the schema, tables, constraints, functions, procedures, triggers, indexes, views, sample records, and reporting queries.

## 19. Technical Learning Outcomes

The five implementations demonstrate the relationship between automated execution and release governance.

The central engineering principles are:

- A pipeline is an executable dependency graph, not merely a list of shell commands.
- Each stage should have a clearly defined input, output, state, and failure condition.
- Automated tests and security scans provide independent validation evidence.
- Artifacts should be versioned and traceable to their source commits.
- Retry policies should distinguish temporary failures from deterministic failures.
- Parallel execution should preserve dependency correctness.
- Approval decisions should be explicit and attributable.
- Production deployment should evaluate environment-specific policies.
- Audit records should connect source changes, pipeline results, artifacts, and releases.
- Deployment success and application health should be measured independently.

The resulting architecture provides a structured foundation for understanding pipeline orchestration, automated validation, artifact management, release authorization, and controlled software deployment.
