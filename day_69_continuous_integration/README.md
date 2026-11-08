# Continuous Integration: CI Pipelines and Automated Checks

## 1. Technical Scope

Continuous Integration (CI) is a software development practice in which changes to a shared codebase are integrated frequently and validated through automated processes.

A CI system automatically executes a sequence of quality checks whenever a configured repository event occurs.

Typical triggering events include:

- A developer pushes a commit.
- A Pull Request is created or updated.
- A scheduled execution begins.
- An authorized developer manually starts a pipeline.

The primary objective is to identify integration problems early, establish repeatable validation, and produce reliable build artifacts.

This implementation develops a continuous integration model across five programming and database environments:

| Deliverable | Engineering perspective |
|---|---|
| Python | Pipeline simulation, validation, execution history, and reporting |
| JavaScript | Asynchronous execution, concurrent jobs, and event-driven monitoring |
| C++17 | Dependency-aware pipeline execution and state management |
| Java 17 | Enterprise CI domain modeling and concurrent execution |
| PostgreSQL | Relational pipeline management, execution records, governance, and reporting |

The implementations use simulated source code and automated checks. They do not connect to an external repository hosting service or execute an actual compiler, package manager, vulnerability scanner, or deployment platform.

## 2. Continuous Integration Architecture

A CI pipeline defines how source changes are validated.

A pipeline consists of jobs, dependencies, execution rules, and quality checks.

### 2.1 Core architecture

The following model represents the implemented workflow:

Repository
|
+-- Branch
|   |
|   +-- Commit
|       |
|       +-- Pipeline Trigger
|           |
|           +-- Pipeline Execution
|               |
|               +-- Lint
|               |
|               +-- Unit Tests
|               |
|               +-- Security Scan
|               |
|               +-- Build
|                   |
|                   +-- Artifact Generation
|                   |
|                   +-- Artifact Verification

A pipeline is an execution instance. A pipeline configuration defines how that instance should behave.

These concepts should not be confused:

| Concept | Meaning |
|---|---|
| Repository | Source code and associated development history |
| Branch | An independent line of development |
| Commit | A recorded source-code change |
| Trigger | An event that initiates a pipeline |
| Pipeline configuration | Definition of jobs and execution rules |
| Pipeline execution | One particular pipeline run |
| Job | An independently executable unit of work |
| Automated check | A validation performed within a job |
| Artifact | An output produced by a successful build |

## 3. CI Pipeline Configuration

A pipeline configuration specifies:

- Trigger conditions.
- Job definitions.
- Execution dependencies.
- Retry limits.
- Concurrency limits.
- Timeout settings.
- Failure-handling behavior.
- Required quality checks.

A configuration may define different workflows for different repository types.

For example, a backend service may require:

1. Source validation.
2. Unit testing.
3. Integration testing.
4. Dependency security scanning.
5. Application packaging.

A frontend application may require:

1. Linting.
2. Type checking.
3. Unit testing.
4. Production compilation.
5. Bundle validation.

The configuration should reflect actual application risks rather than impose identical checks on every repository.

### 3.1 Pipeline triggers

| Trigger | Description |
|---|---|
| Push | Starts validation after a commit is pushed |
| Pull Request | Validates proposed changes before integration |
| Schedule | Runs validation at configured intervals |
| Manual | Starts execution through an authorized user action |

The trigger identifies why a pipeline started. It does not determine whether the execution will succeed.

### 3.2 Example pipeline configuration

The implementations use the following logical structure:

| Job | Dependencies | Purpose |
|---|---|---|
| lint | None | Validate source formatting and basic structure |
| unit-tests | lint | Execute application-level tests |
| security | lint | Check for security-related problems |
| build | unit-tests, security | Produce the application build |

The dependency relationships form a directed acyclic graph (DAG).

A DAG contains directed relationships without circular dependencies.

For example:

lint
 |
 +---- unit-tests ----+
 |                    |
 +---- security ------+---- build

The build job cannot start until both unit testing and security validation have succeeded.

## 4. Automated Checks

Automated checks provide evidence about the quality and integrity of a software change.

They are executed automatically as part of the configured workflow.

### 4.1 Linting

Linting identifies source-code quality problems.

Typical findings include:

- Formatting violations.
- Unused variables.
- Suspicious expressions.
- Naming inconsistencies.
- Potential programming errors.
- Language-specific coding violations.

Linting does not establish that an application behaves correctly.

A program may pass linting and still contain functional defects.

The Python, JavaScript, C++17, and Java 17 examples implement basic source validation.

The PostgreSQL implementation records lint results as automated checks.

### 4.2 Unit testing

Unit tests validate individual functions, classes, and isolated application components.

A test compares actual behavior against expected behavior.

For example, an arithmetic service may validate:

| Input | Expected result |
|---|---:|
| 10 + 20 | 30 |
| 0 + 0 | 0 |
| -5 + 5 | 0 |

Unit testing helps detect:

- Incorrect business logic.
- Boundary-condition failures.
- Unexpected return values.
- Regression defects.
- Incorrect exception handling.

A successful unit-test job does not guarantee that different application components work correctly together.

### 4.3 Integration testing

Integration testing evaluates interactions between components.

Examples include:

- API-to-database communication.
- Authentication-service integration.
- Message-queue processing.
- External service communication.
- Transaction consistency.

Unit tests and integration tests serve different purposes.

| Unit testing | Integration testing |
|---|---|
| Tests isolated components | Tests component interactions |
| Usually executes quickly | May require additional infrastructure |
| Uses controlled dependencies | Uses integrated components or realistic substitutes |
| Identifies local functional defects | Identifies interface and integration defects |

The PostgreSQL model supports integration-test records through the `INTEGRATION_TEST` check category.

### 4.4 Security scanning

Security checks identify vulnerabilities and unsafe implementation practices.

Common CI security activities include:

- Static Application Security Testing (SAST).
- Software Composition Analysis (SCA).
- Dependency vulnerability scanning.
- Secret detection.
- Infrastructure configuration scanning.
- Container image scanning.

The examples implement simplified credential-detection logic.

The PostgreSQL model records structured security findings through JSONB metadata.

For example, a security result can contain:

| Attribute | Example |
|---|---|
| Critical findings | 0 |
| High findings | 0 |
| Medium findings | 2 |
| Check status | PASSED |

A real security scanner must evaluate actual source files, dependencies, configurations, and generated artifacts.

A basic regular-expression check is not a substitute for comprehensive security analysis.

### 4.5 Build validation

A build converts source code into an executable or distributable application package.

Depending on the technology, this may involve:

- Dependency resolution.
- Compilation.
- Resource processing.
- Package generation.
- Static linking.
- Container image construction.

The build job should execute only after its required dependencies succeed.

A successful build establishes that the configured build process completed. It does not independently establish application correctness or production readiness.

### 4.6 Code coverage

Code coverage measures which portions of a program are exercised during testing.

Common measures include:

| Coverage measure | Meaning |
|---|---|
| Line coverage | Percentage of executable lines exercised |
| Statement coverage | Percentage of statements executed |
| Branch coverage | Percentage of decision outcomes exercised |
| Function coverage | Percentage of functions called |

A coverage threshold can be incorporated into CI governance.

For example, a repository may require at least 80% line coverage.

High coverage does not necessarily indicate strong tests. Test assertions must evaluate meaningful application behavior.

## 5. Job Dependencies and Scheduling

Job dependencies determine execution eligibility.

A job is eligible when:

1. It is in the pending state.
2. Its parent dependencies have completed successfully.
3. Its pipeline is running.
4. Its execution policy permits it to start.

### 5.1 Dependency validation

Before execution, the implementations validate:

- Unique job names.
- Existing dependency references.
- Prohibited self-dependencies.
- Circular dependency conditions.

Circular dependencies prevent a valid execution order.

For example:

Job A depends on Job B.

Job B depends on Job C.

Job C depends on Job A.

No job can become eligible.

The Python, JavaScript, C++17, and Java 17 implementations use graph traversal to detect cycles.

The JavaScript implementation uses `Map` and `Set`, while the other implementations use language-specific collections.

### 5.2 Sequential and concurrent execution

Independent jobs can execute concurrently.

Consider the following workflow:

lint
 |
 +---- unit-tests
 |
 +---- security

The unit-test and security jobs can execute simultaneously after linting succeeds.

The build job waits for both.

Concurrent execution can reduce total pipeline duration.

If two independent jobs require 30 seconds and 40 seconds respectively, sequential execution takes approximately 70 seconds, while concurrent execution takes approximately 40 seconds, excluding scheduling overhead.

The JavaScript and Java implementations use asynchronous execution.

The Python and C++17 implementations demonstrate dependency-aware execution through sequential scheduling.

### 5.3 Concurrency controls

Unrestricted parallel execution can exhaust:

- CPU capacity.
- Memory.
- Database connections.
- Network bandwidth.
- External service quotas.

Concurrency limits control the number of simultaneously executing jobs.

The JavaScript implementation uses a configurable concurrency limit with `Promise.all`.

The Java implementation uses `ExecutorService` and `CompletableFuture`.

These approaches demonstrate different concurrency models.

## 6. Pipeline State Management

A pipeline has a lifecycle.

| State | Meaning |
|---|---|
| PENDING | Created but not started |
| RUNNING | Currently executing |
| SUCCESS | All required jobs completed successfully |
| FAILED | One or more required jobs failed |
| CANCELLED | Execution was terminated |

A job has its own lifecycle:

| State | Meaning |
|---|---|
| PENDING | Waiting for execution eligibility |
| RUNNING | Currently executing |
| SUCCESS | Completed successfully |
| FAILED | Execution exhausted its retry allowance |
| SKIPPED | Not executed because of an unsuccessful dependency |

The pipeline state and job state are separate.

A pipeline can contain several successful jobs and still finish as FAILED.

### 6.1 Failure propagation

Suppose the security scan fails.

The build job depends on that scan.

The build must therefore be skipped.

This prevents an invalid downstream operation from being treated as a successful pipeline result.

The implementations record the reason for unsuccessful execution.

### 6.2 Retry handling

Transient failures may occur because of:

- Temporary network interruptions.
- Service unavailability.
- Resource contention.
- External dependency timeouts.

A retry policy specifies how many additional attempts are permitted.

For example:

| Configuration | Behavior |
|---|---|
| Maximum retries = 0 | One execution attempt |
| Maximum retries = 1 | One initial attempt and one retry |
| Maximum retries = 2 | One initial attempt and two retries |

Retries should be applied selectively.

A deterministic compilation error usually requires a source correction rather than repeated execution.

Production retry mechanisms should include exponential backoff, timeout controls, and protection against duplicate side effects.

The implementations maintain attempt counters and record the final error.

## 7. Build Artifacts and Integrity

An artifact is an output produced by a successful pipeline.

Examples include:

- Executable files.
- Application packages.
- Container images.
- Compiled libraries.
- Deployment bundles.
- Test reports.

The examples generate representative build artifacts and calculate SHA-256 checksums.

### 7.1 Checksum verification

A checksum is a digest calculated from artifact content.

The verification process is:

1. Generate artifact content.
2. Calculate its SHA-256 digest.
3. Store the digest with the artifact metadata.
4. Recalculate the digest when verifying the artifact.
5. Compare the two values.

A matching digest provides evidence that the content has not changed since the recorded digest was calculated.

A checksum alone does not establish the identity of the producer or prevent an attacker from replacing both the artifact and its checksum.

Production systems should combine integrity verification with access controls, trusted build provenance, and protected artifact storage.

## 8. Python Implementation

**File:** `continuous_integration.py`

The Python implementation models pipeline execution as a collection of validated domain objects.

### 8.1 Important components

| Component | Responsibility |
|---|---|
| `Commit` | Represents validated source changes |
| `Stage` | Represents an executable pipeline stage |
| `Pipeline` | Stores pipeline execution state |
| `PipelineValidator` | Validates job dependencies |
| `AutomatedChecks` | Implements representative quality checks |
| `Artifact` | Stores build output and its checksum |
| `PipelineRunner` | Controls execution and reporting |
| `PipelineTests` | Validates important system behavior |

### 8.2 Implementation mechanisms

The script uses:

- Dataclasses for structured domain objects.
- Enums for controlled state values.
- Dictionaries for check registration and stage lookup.
- Lists for execution history.
- Sets for graph traversal.
- Exceptions for validation and execution failures.
- SHA-256 for artifact verification.
- JSON for report serialization.
- `unittest` for automated assertions.

The `PipelineValidator` uses depth-first search to identify dependency cycles.

The runner executes stages only when their dependencies have succeeded.

The implementation also records timestamps, retry attempts, execution results, and error messages.

### 8.3 Execution

Run the file using:

`python continuous_integration.py`

No third-party Python package is required.

The script prints a pipeline report and executes four validation tests.

## 9. JavaScript Implementation

**File:** `continuous-integration.js`

The JavaScript implementation emphasizes asynchronous job execution and event-driven monitoring.

### 9.1 Important components

| Component | Responsibility |
|---|---|
| `PipelineJob` | Defines a job and its execution function |
| `PipelineValidator` | Validates pipeline dependency structure |
| `ArtifactStore` | Stores and verifies artifacts |
| `CIEngine` | Coordinates asynchronous execution |
| `EventEmitter` | Publishes pipeline lifecycle events |

### 9.2 Event-driven architecture

The implementation emits events when:

- A pipeline starts.
- A job starts.
- A job succeeds.
- A job attempt fails.
- A job permanently fails.
- A pipeline completes.

This separates execution logic from monitoring logic.

For example, a monitoring service could subscribe to job failure events and create operational alerts.

### 9.3 Asynchronous execution

JavaScript uses:

- `async` functions.
- Promises.
- `Promise.all`.
- `EventEmitter`.
- `Map`.
- `Set`.

The engine schedules independent jobs in bounded batches.

Dependent jobs are scheduled only after their prerequisites succeed.

The artifact store uses Node.js cryptographic functionality to calculate SHA-256 checksums.

### 9.4 Execution

Run the file using:

`node continuous-integration.js`

The implementation requires Node.js 18 or later and no third-party npm packages.

## 10. C++17 Implementation

**File:** `continuous_integration.cpp`

The C++17 implementation emphasizes explicit domain modeling, validation, and controlled state transitions.

### 10.1 Domain structures

| Structure or class | Responsibility |
|---|---|
| `Commit` | Represents source-control information |
| `CheckResult` | Represents an automated check result |
| `Artifact` | Represents a generated build output |
| `Job` | Defines execution dependencies and behavior |
| `Pipeline` | Stores pipeline state and audit events |
| `PipelineEngine` | Validates and executes the pipeline |

### 10.2 Engineering decisions

The implementation uses:

- `enum class` for type-safe states.
- `struct` for domain records.
- `std::vector` for ordered execution.
- `std::map` for job lookup.
- `std::set` for dependency-cycle detection.
- `std::function` for executable job definitions.
- `std::all_of` and `std::any_of` for validation.
- Exceptions for invalid configurations.

The dependency graph is validated before execution.

The scheduler scans pending jobs and executes those whose dependencies have succeeded.

Failed dependencies cause downstream jobs to be skipped.

The checksum function is a deterministic demonstration hash, not a cryptographic integrity mechanism. Production implementations should use a SHA-256 implementation from a trusted cryptographic library.

### 10.3 Complexity

Let:

- V represent the number of jobs.
- E represent the number of dependency relationships.

Dependency graph validation takes O(V + E) time.

The current sequential scheduling implementation repeatedly scans jobs, resulting in O(V² + VE) worst-case scheduling behavior.

A production scheduler can use adjacency lists and a queue-based topological ordering algorithm to achieve O(V + E) scheduling overhead.

### 10.4 Compilation

Compile using:

`g++ -std=c++17 -O2 -Wall -Wextra -pedantic continuous_integration.cpp -o continuous_integration`

Execute using:

`./continuous_integration`

The program does not require external libraries.

## 11. Java 17 Implementation

**File:** `ContinuousIntegration.java`

The Java implementation models CI as an enterprise-oriented service.

It emphasizes explicit domain types, immutable records, service responsibilities, and controlled concurrent execution.

### 11.1 Enterprise domain model

| Component | Responsibility |
|---|---|
| `Repository` | Repository identity and configuration |
| `Commit` | Validated source-control metadata |
| `Pipeline` | Pipeline state and execution history |
| `Job` | Job definition and runtime state |
| `CheckResult` | Quality-check result |
| `BuildArtifact` | Verified build output |
| `PipelineValidator` | Configuration validation |
| `AutomatedChecks` | Automated quality-check logic |
| `ArtifactService` | Artifact creation and integrity verification |
| `PipelineService` | Execution coordination |
| `PipelineReport` | Immutable execution report |

### 11.2 Records and immutability

Java records represent structured data whose components are immutable.

The implementation uses records for:

- Repository metadata.
- Commit metadata.
- Check results.
- Build artifacts.
- Job reports.
- Pipeline reports.

Runtime execution state remains inside controlled service objects.

This separation makes the domain model easier to reason about and reduces unnecessary mutation.

### 11.3 Concurrency

The service uses:

- `ExecutorService`.
- `CompletableFuture`.
- `AtomicBoolean`.
- Java collections.
- Streams.

Independent jobs are submitted to a bounded executor.

Their completion is coordinated before dependent jobs are scheduled.

### 11.4 Failure management

The implementation distinguishes:

- Configuration failures.
- Job execution failures.
- Dependency failures.
- Artifact integrity failures.
- Pipeline-level failures.

A failed job prevents dependent jobs from being treated as successful.

The service also shuts down its executor to release application resources.

### 11.5 Compilation

Compile using:

`javac ContinuousIntegration.java`

Execute using:

`java ContinuousIntegration`

Java 17 is required. No third-party dependency is necessary.

## 12. PostgreSQL Database Design

**File:** `continuous_integration.sql`

The PostgreSQL implementation models the relational structure of a CI management system.

### 12.1 Relational entities

| Table | Purpose |
|---|---|
| `repositories` | Repository information |
| `branches` | Repository branches |
| `commits` | Source-control commits |
| `pipeline_configs` | Pipeline configuration |
| `pipeline_executions` | Individual pipeline runs |
| `pipeline_jobs` | Executable jobs |
| `job_dependencies` | Job dependency relationships |
| `automated_checks` | Quality-check results |
| `build_artifacts` | Generated build outputs |
| `pipeline_events` | Execution audit events |
| `ci_policies` | CI governance requirements |

### 12.2 Referential integrity

Primary keys uniquely identify database records.

Foreign keys preserve relationships between repositories, commits, pipeline executions, jobs, and artifacts.

Unique constraints prevent duplicate repository names within an owner and duplicate job names within an execution.

Check constraints validate:

- Retry counts.
- Execution durations.
- Coverage thresholds.
- Artifact checksums.
- Job dependency relationships.

These controls prevent invalid records from entering the relational model.

### 12.3 Dependency relationships

The `job_dependencies` table represents the pipeline DAG.

It contains two references to `pipeline_jobs`:

- `job_id`: the dependent job.
- `depends_on_job_id`: the prerequisite job.

A job can have multiple dependencies.

The `is_job_eligible` function checks whether all prerequisite jobs have succeeded.

The function also verifies that the parent pipeline is running.

The database enforces direct dependency integrity. Full cycle detection for dependency records should also be enforced through a controlled dependency-registration procedure or application-level graph validation before production execution.

### 12.4 Database functions

The SQL implementation includes:

| Function | Responsibility |
|---|---|
| `validate_pipeline_transition` | Enforces pipeline state transitions |
| `validate_job_transition` | Enforces job state transitions |
| `start_pipeline` | Starts an eligible pipeline |
| `is_job_eligible` | Determines job execution eligibility |
| `complete_pipeline` | Determines final pipeline status |
| `evaluate_ci_policy` | Evaluates configured quality requirements |

The state-validation triggers prevent terminal states from being modified through ordinary status updates.

The completion function rejects pipelines containing unfinished jobs.

### 12.5 CI governance policies

The `ci_policies` table stores repository-level quality requirements.

Policy attributes include:

- Mandatory lint checks.
- Mandatory unit tests.
- Mandatory integration tests.
- Mandatory security scans.
- Mandatory build validation.
- Minimum code coverage.
- Maximum permitted failed tests.
- Warning restrictions.

The `evaluate_ci_policy` function checks recorded pipeline results against these requirements.

A successful pipeline does not automatically satisfy every governance policy.

For example, a pipeline may complete successfully but fail a policy requiring 80% coverage.

This distinction separates execution success from organizational acceptance criteria.

### 12.6 Database indexes

Indexes support common retrieval operations.

Examples include:

| Index | Query workload |
|---|---|
| `idx_commits_branch_date` | Recent commits by branch |
| `idx_pipeline_status_created` | Pipeline status and history |
| `idx_pipeline_commit` | Pipeline lookup by commit |
| `idx_jobs_pipeline_status` | Job retrieval by execution and state |
| `idx_checks_category_status` | Quality-check reporting |
| `idx_artifacts_pipeline` | Artifact retrieval |
| `idx_pipeline_events` | Audit-event retrieval |
| `idx_active_ci_policies` | Active repository policies |

The GIN index on `automated_checks.details` supports JSONB queries.

Indexes improve suitable retrieval patterns but introduce additional storage and write-maintenance costs.

### 12.7 Views and reporting

The `pipeline_execution_summary` view combines repository, branch, commit, execution, job, and artifact information.

The reporting queries support:

- Pipeline execution history.
- Successful and failed job counts.
- Check execution statistics.
- Failure investigation.
- Artifact inventory.
- Dependency validation.
- Event auditing.
- Governance evaluation.

### 12.8 Transaction handling

The SQL script uses a transaction to group schema creation, sample configuration, execution simulation, and reporting setup.

A failure before commit allows the transaction to be rolled back.

The `start_pipeline` function also locks the target execution row while changing its state.

This reduces the risk of concurrent callers starting the same pipeline simultaneously.

The sample workflow simulates job results through SQL statements. An actual CI worker would execute jobs outside the database and persist their results through a controlled application interface.

## 13. Failure Scenarios and Operational Controls

Reliable CI systems must handle failures explicitly.

| Failure scenario | Appropriate handling |
|---|---|
| Invalid pipeline configuration | Reject execution |
| Duplicate job identifier | Reject configuration |
| Unknown dependency | Reject configuration |
| Circular dependency | Reject configuration |
| Lint failure | Stop dependent execution |
| Unit-test failure | Block dependent build |
| Security scan failure | Block dependent build |
| Temporary infrastructure failure | Apply bounded retries |
| Exhausted retries | Mark job as failed |
| Missing prerequisite | Keep job ineligible |
| Artifact checksum mismatch | Reject artifact |
| Pipeline timeout | Terminate or cancel execution |
| Unauthorized execution | Reject the request |

### 13.1 Timeout management

A production CI system should enforce time limits at multiple levels:

- Pipeline timeout.
- Individual job timeout.
- External command timeout.
- Network request timeout.

The SQL configuration includes a pipeline timeout attribute.

The executable simulations demonstrate retry and state management but do not implement real process-level timeout enforcement.

### 13.2 Cancellation

Cancellation should be treated as a distinct pipeline outcome.

A production implementation should:

1. Receive an authorized cancellation request.
2. Prevent new jobs from starting.
3. Signal running workers.
4. Release temporary resources.
5. Record cancellation metadata.
6. Mark the pipeline as cancelled.

Cancellation must not be confused with ordinary job failure.

### 13.3 Security considerations

CI systems frequently handle sensitive credentials and privileged infrastructure.

Important security controls include:

- Least-privilege execution identities.
- Protected environment variables.
- Secret masking in logs.
- Short-lived credentials.
- Restricted artifact access.
- Dependency integrity validation.
- Trusted build environments.
- Restricted external network access.
- Auditable execution records.
- Isolation between untrusted contributions and privileged workflows.

Untrusted Pull Request code should not receive unrestricted deployment credentials.

Security scans should also distinguish exploitable findings from informational results and enforce clearly defined severity policies.

## 14. Performance and Scalability

Pipeline performance depends on the number of jobs, dependency structure, execution time, resource allocation, and infrastructure capacity.

### 14.1 Pipeline optimization

Useful optimization techniques include:

- Running independent jobs concurrently.
- Caching verified dependencies.
- Reusing build layers.
- Avoiding unnecessary test execution.
- Splitting large test suites.
- Using incremental compilation.
- Reusing immutable build artifacts.
- Selecting appropriate worker sizes.

### 14.2 Build caching

A cache stores reusable outputs from earlier executions.

A cache key should incorporate relevant inputs such as:

- Dependency lockfile.
- Compiler version.
- Build configuration.
- Operating system.
- Source inputs.

Incorrect cache keys can cause stale or incompatible outputs.

Caches should not be treated as authoritative artifact storage.

### 14.3 Execution metrics

Important CI performance measurements include:

| Metric | Interpretation |
|---|---|
| Pipeline duration | Time from pipeline start to completion |
| Queue duration | Time spent waiting for execution resources |
| Job duration | Time required by an individual job |
| Success rate | Proportion of successful executions |
| Failure rate | Proportion of failed executions |
| Retry rate | Frequency of repeated attempts |
| Test duration | Time spent executing automated tests |
| Cache hit rate | Proportion of cache requests successfully reused |

These measurements help identify inefficient jobs and recurring infrastructure problems.

## 15. Important Architectural Distinctions

Continuous Integration is related to, but distinct from, several other software delivery practices.

| Practice | Primary responsibility |
|---|---|
| Continuous Integration | Frequently integrate and validate source changes |
| Continuous Delivery | Keep software in a deployable state |
| Continuous Deployment | Automatically release qualifying changes into production |
| Continuous Testing | Execute relevant tests throughout the delivery lifecycle |
| Continuous Monitoring | Observe application behavior after execution and deployment |

A successful CI pipeline does not necessarily mean that software has been deployed.

The build and validation stages establish evidence about the proposed software changes.

Deployment requires separate authorization, environment configuration, operational controls, and release policies.

## 16. Limitations of the Implementations

The five implementations are educational execution models rather than complete production CI platforms.

| Area | Current implementation | Production requirement |
|---|---|---|
| Repository integration | Simulated commit metadata | Repository hosting integration |
| Linting | Basic validation | Language-specific lint engines |
| Testing | Representative assertions | Real application test suites |
| Security | Simplified checks | Dedicated security scanners |
| Build | Simulated package creation | Actual compilation and packaging |
| Scheduling | In-memory dependency scheduling | Distributed worker orchestration |
| Retry | Bounded retry counts | Backoff and transient-error classification |
| Artifact storage | In-memory or relational metadata | Durable artifact storage |
| Integrity | Demonstration verification | Trusted SHA-256 and signed provenance |
| Monitoring | Console and database reports | Centralized telemetry and alerting |
| Cancellation | State representation | Worker cancellation and cleanup |
| Deployment | Not implemented | Separate release and deployment controls |

The C++17 checksum is explicitly non-cryptographic.

The Python and JavaScript examples use simplified security checks.

The PostgreSQL implementation stores artifact metadata rather than transferring or storing the actual artifact bytes.

These boundaries are important when interpreting execution results.

## 17. Cross-Language Implementation Comparison

| Engineering concern | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Configuration validation | Dataclasses and exceptions | Classes and validation methods | Explicit validation | Domain constructors | Constraints |
| Dependency graph | Dictionaries and sets | Map and Set | STL containers | Collections | Relational table |
| Execution | Sequential | Asynchronous | Sequential | Concurrent | Transactional workflow |
| State management | Enums and dataclasses | Object state | Enum classes | Domain objects | Enum types |
| Error handling | Exceptions | Promise rejection | Exceptions | Custom exceptions | SQL exceptions |
| Artifact integrity | SHA-256 | SHA-256 | Demonstration hash | SHA-256 | Stored digest |
| Reporting | JSON | Structured objects | Console report | Immutable records | Views and queries |

Each implementation demonstrates a different engineering approach to the same CI domain.

The central architectural principle remains consistent: validate configuration, establish execution eligibility, run automated checks, propagate failures, verify outputs, and record execution evidence.
