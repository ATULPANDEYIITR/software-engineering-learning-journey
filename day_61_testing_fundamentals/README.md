# Testing Fundamentals: Unit, Integration, and System Testing

## Scope

This project models software testing as three distinct levels:

| Level | Primary question | Typical boundary |
|---|---|---|
| Unit | Does one deterministic behavior work correctly? | Function, class, or isolated rule |
| Integration | Do collaborating components work correctly together? | Service, repository, database, or subsystem |
| System | Does the complete workflow satisfy its external contract? | Application and external system boundaries |

The implementations use a small user-management workflow because it exposes the differences between the three levels without introducing unrelated infrastructure.

The domain flow is:

`Input → Validation → Business Service → Repository → External File Boundary`

A unit test can stop at validation or a business rule. An integration test crosses the service and repository boundary. A system test exercises the complete registration and file-export workflow.

## Testing Model

The three levels have different responsibilities.

### Unit Testing

Unit tests isolate a small piece of behavior and make failures easy to localize.

The examples test:

- Email validation.
- Discount calculation.
- Boundary values such as `0%` and `100%`.
- Invalid negative totals.
- Invalid discount percentages.
- Invalid email structures.

The tests avoid persistence and filesystem dependencies. This keeps execution fast and makes a failing test point directly toward the business rule.

A useful unit test has a clear structure:

`Arrange → Act → Assert`

For failure cases, the expected exception is part of the behavior being verified.

### Integration Testing

Integration testing checks collaboration between components.

The project uses:

`UserService → UserRepository`

The repository stores users while the service owns the application-level operation. Integration tests therefore verify behavior that cannot be established by testing either class in isolation.

The integration cases cover:

- Successful persistence.
- Retrieval after persistence.
- Duplicate-user rejection.
- Missing-user behavior.
- Event emission in JavaScript.
- Repository contracts in Java.
- Repository and service collaboration in C++.

The important distinction is that the test crosses a component boundary while still remaining smaller than a complete application workflow.

### System Testing

System tests operate at the highest boundary represented by these examples.

The workflow is:

`Register User → Retrieve User → Export User → Read Exported Data`

The system tests interact with the filesystem. They therefore verify the combined behavior of validation, service logic, persistence, directory creation, serialization, file writing, and file reading.

System tests also verify failure at the application boundary, such as attempting to export a user that does not exist.

## Test Isolation

Isolation determines how much unrelated state can affect a result.

The implementations use fresh in-memory repositories for test cases. Filesystem tests use temporary directories and remove them after execution.

This prevents:

- Previous test data affecting later tests.
- Test order from becoming significant.
- Permanent files accumulating on the development machine.
- Shared mutable state from producing false positives or false failures.

A production system using a real database would normally isolate integration data with transactions, disposable schemas, dedicated test databases, or controlled fixtures.

## Python Implementation

The Python file uses `dataclass` for immutable user data and an in-memory repository for persistence simulation.

### Domain Model

`User` stores:

- `user_id`
- `name`
- `email`

`InMemoryUserRepository` provides:

- `save`
- `find`
- `delete`

`UserService` provides application operations:

- `register`
- `get_user`
- `export_user`

The repository validates identity and duplicate state. The service converts missing users into an explicit lookup failure.

### Python Unit Tests

`unittest.TestCase` isolates business rules.

The discount function demonstrates boundary testing:

| Input | Expected behavior |
|---|---|
| `1000, 20` | `800` |
| `1000, 0` | `1000` |
| `1000, 100` | `0` |
| Negative total | `ValueError` |
| Percentage above `100` | `ValueError` |

The email tests deliberately include valid and invalid forms.

### Python Integration Tests

The integration suite creates one repository and one service, registers a user, and verifies that the repository contains the resulting object.

Duplicate registration and missing-user retrieval are tested as failure paths.

### Python System Test

The system test creates a temporary directory, registers a user, exports JSON, reads the file, parses it, and verifies the resulting fields.

This tests a real serialization and filesystem boundary rather than a mocked file operation.

## JavaScript Implementation

The JavaScript implementation emphasizes asynchronous application behavior and event-driven state changes.

`UserRepository` uses a `Map` for efficient identity lookup.

`UserService` extends `EventEmitter`. Successful registration emits `userRegistered`, allowing another component to observe the workflow without coupling the service to a particular notification implementation.

The file uses only Node.js standard-library modules:

- `node:assert/strict`
- `node:events`
- `node:fs/promises`
- `node:os`
- `node:path`

### Asynchronous Testing

Repository and service methods return promises. Tests therefore use `async` functions and `await`.

This reflects a realistic Node.js application where database and filesystem operations are asynchronous.

The system test uses `fs.mkdtemp` to create isolated temporary storage and removes it with `fs.rm`.

The export operation uses the `wx` file flag so an existing destination is not silently overwritten. This makes accidental replacement of an existing artifact an explicit failure.

## C++17 Implementation

The C++ implementation models the same testing concepts with a different engineering structure.

`UserRepository` uses `std::unordered_map<int, User>` for identity-based storage. `std::optional<User>` represents a lookup that may legitimately produce no user.

The service owns application operations while the repository owns persistence behavior.

### Exception Boundaries

The C++ program distinguishes invalid input from runtime workflow failures:

- `std::invalid_argument` represents invalid domain input.
- `std::runtime_error` represents failures such as duplicate records or missing users.

The system test uses `std::filesystem` for temporary directory management and `std::ofstream` for file creation.

### Complexity

Repository lookup and insertion are expected average `O(1)` with `unordered_map`.

The test runner itself is `O(n)` in the number of registered test cases.

Filesystem operations remain dependent on the operating system and storage device and should not be treated as constant-time application operations.

## Java 17 Implementation

The Java implementation models testing through domain types and service boundaries.

The `User` record provides immutable domain data. Its compact constructor performs validation before an object can enter the application.

`UserRepository` is an interface. `InMemoryUserRepository` is the concrete test implementation.

`UserService` depends on the interface rather than a concrete persistence implementation. This makes integration testing possible without coupling the service to a database.

### Explicit Failure Types

The Java implementation defines:

- `ValidationException`
- `UserAlreadyExistsException`
- `UserNotFoundException`

This makes expected failure behavior directly testable.

`assertThrows` verifies that the application rejects invalid operations with the correct exception category rather than merely checking that some exception occurred.

### Enterprise-Oriented Structure

The design separates:

`Domain Value → Repository Contract → Repository Implementation → Service → External File Boundary`

This separation allows a real database implementation to replace the in-memory repository without changing the service contract.

The `DiscountPolicy` interface also separates a business rule from the service layer.

## PostgreSQL Implementation

The PostgreSQL script represents testing as stored relational execution data rather than as application source code.

The schema contains:

- `projects`
- `test_suites`
- `test_cases`
- `test_runs`
- `test_results`

The relationships are:

`Project → Test Suites → Test Cases`

and:

`Project → Test Runs → Test Results`

A result also references the test case that produced it.

### Database Constraints

The schema enforces:

- Unique project keys.
- Unique suite names within a project.
- Unique test-case keys within a suite.
- Unique test results for a test case within a run.
- Non-negative durations.
- Valid test-level and status values.
- Failure results requiring an error message.
- Finished runs requiring a completion timestamp after the start.

These constraints move important integrity rules into the database.

### Trigger-Based Validation

A trigger verifies that a test result cannot combine:

- a test case from one project, and
- a test run from another project.

This protects a relationship that cannot be expressed by the individual foreign keys alone.

### Reporting

`test_run_report` aggregates:

- Executed tests.
- Passed tests.
- Failed tests.
- Skipped tests.
- Total execution duration.
- Pass rate.

The reporting view provides a stable relational interface for dashboards or operational queries.

### Transactional Execution

The staging example creates a test run and its results inside one transaction.

If the transaction fails, neither the run nor its associated results should be considered successfully recorded.

This is important because test execution metadata is meaningful only when its run and result records remain consistent.

## Testing Workflow

A practical workflow represented by the artifacts is:

`Write Test`
→ `Execute Isolated Behavior`
→ `Cross Component Boundary`
→ `Exercise Complete Workflow`
→ `Record Result`
→ `Analyze Failures`

The testing level should match the question being asked.

| Question | Appropriate level |
|---|---|
| Is discount calculation correct? | Unit |
| Does the service correctly persist a user? | Integration |
| Can a user be registered and exported successfully? | System |
| Does the complete production deployment work? | System or acceptance testing |

A higher-level test should not replace lower-level tests when a lower-level test can identify a failure more precisely.

## Failure Handling

The examples deliberately test failure conditions rather than only successful paths.

Important cases include:

- Missing required fields.
- Invalid email addresses.
- Negative monetary values.
- Out-of-range percentages.
- Duplicate identities.
- Missing users.
- Existing export destinations.
- Filesystem write failures.
- Cross-project database relationships.
- Failed tests without diagnostic messages.

A useful test suite verifies both the expected result and the expected failure mechanism.

## Test Data and State

Test data should be deterministic where deterministic behavior is required.

The examples create isolated repository instances for each test group. Filesystem state is created inside temporary locations.

For database-backed testing, the schema provides explicit test-run identities and commit identifiers. This allows results to be associated with a particular execution context.

Production test systems should avoid using uncontrolled shared data because concurrent execution can create:

- Race conditions.
- Duplicate-key failures unrelated to the feature.
- Order-dependent results.
- Contaminated state.
- Difficult-to-reproduce defects.

## Performance Considerations

Unit tests should normally form the largest and fastest layer because they avoid expensive boundaries.

Integration tests are slower because they cross component boundaries.

System tests are usually slower still because they may involve filesystem, network, database, browser, or deployment infrastructure.

A practical distribution is therefore:

`Many fast unit tests → fewer integration tests → smaller set of system tests`

This is not a strict numerical rule. The correct distribution depends on application architecture and risk.

The repository examples use hash-based structures where appropriate:

- Python dictionary.
- JavaScript `Map`.
- C++ `unordered_map`.
- Java `ConcurrentHashMap`.

These provide efficient identity-based lookups for the in-memory examples.

## Security Considerations

Tests must not weaken production security merely to make testing convenient.

Important controls include:

- Never placing real credentials in test source.
- Using synthetic users and email addresses.
- Isolating temporary files.
- Avoiding production databases for ordinary test execution.
- Preventing uncontrolled file overwrites.
- Validating input at domain boundaries.
- Treating externally supplied data as untrusted.
- Cleaning temporary test artifacts.
- Keeping test fixtures free of real personal information.

Database tests should use dedicated credentials with only the permissions required for the test environment.

## Common Failure Modes

| Failure mode | Typical cause | Better test design |
|---|---|---|
| False positive | Test never reaches the important assertion | Verify the observable outcome |
| Flaky test | Time, network, random data, or shared state | Control dependencies and isolate state |
| Slow suite | Too many expensive system tests | Push deterministic checks toward unit tests |
| Weak integration coverage | Only classes are tested independently | Test important component boundaries |
| Brittle system test | Depends on exact internal implementation | Assert external behavior |
| Poor diagnostics | Generic assertion or missing failure data | Include expected and actual values |
| Test pollution | Shared database or files | Fresh fixtures and cleanup |
| Order dependency | Earlier test changes later state | Independent setup and teardown |

## Test Scope and Assertions

Assertions should verify behavior that matters to the contract.

For example, a system test should not require an exact internal serialization layout unless that layout is part of the public contract.

A useful distinction is:

`Implementation detail ≠ observable requirement`

Tests that assert only externally meaningful behavior survive internal refactoring more easily.

At the same time, integration tests should verify important contracts between components. The goal is not to eliminate all implementation-level checks but to place each assertion at the level where it provides the strongest signal.

## Relationship Between the Five Implementations

| Implementation | Primary testing perspective |
|---|---|
| Python | Structured unit, integration, and system test suite using `unittest` |
| JavaScript | Asynchronous and event-driven testing with Node.js standard APIs |
| C++17 | Exception-safe repository/service case study with filesystem testing |
| Java 17 | Enterprise-style domain model with interfaces, records, policies, and typed failures |
| PostgreSQL | Persistent test metadata, constraints, trigger validation, transactions, and reporting |

The implementations intentionally use the same core domain while emphasizing different engineering mechanisms.

The common testing boundary remains:

`Business Rule → Component Collaboration → Complete Workflow`

This preserves the conceptual distinction between unit, integration, and system testing while showing how the same testing principles map to different execution environments.
