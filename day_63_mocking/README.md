# Mocking: Mocks, Stubs, Fakes, and Dependency Isolation

## Scope

This project models dependency isolation for a payment-processing service. The central service validates a payment, evaluates fraud risk, authorizes the transaction through a gateway, and stores the resulting state.

The four testing techniques are kept distinct:

| Technique | Primary purpose | Behavior |
|---|---|---|
| Stub | Control input to the system under test | Returns predetermined data |
| Mock | Verify interactions with a dependency | Records calls and checks expectations |
| Fake | Replace an external dependency with a lightweight working implementation | Executes simplified but meaningful behavior |
| Dependency isolation | Prevent unrelated systems from affecting a test | Injects controlled implementations |

The project uses the following workflow:

`Payment → validation → fraud evaluation → gateway authorization → repository persistence`

A blocked customer is declined before the gateway is contacted. A normal customer reaches the gateway. Invalid input fails before either external dependency is invoked.

## Domain Model

The payment domain contains four relevant dependency boundaries:

- `PaymentGateway` represents an external authorization provider.
- `FraudService` represents fraud-risk evaluation.
- `PaymentRepository` represents persistence.
- `PaymentService` is the system under test.

The dependency direction is explicit:

`PaymentService → PaymentGateway`

`PaymentService → FraudService`

`PaymentService → PaymentRepository`

The service depends on interfaces or protocols rather than concrete external implementations. This allows each dependency to be replaced independently during testing.

## Stub

A stub supplies a predetermined answer.

The gateway stub always returns the configured `PaymentStatus`. It does not attempt to reproduce gateway internals. Its purpose is to make the service's behavior deterministic when the authorization result is the variable being tested.

The test verifies that an approved gateway response produces an approved payment and that the repository receives the resulting state.

A stub is useful when the returned value matters more than the exact interaction details.

## Mock

A mock focuses on interaction verification.

The gateway mock records every `authorize` invocation. The test can then assert:

- the dependency was called exactly once;
- the expected payment object was supplied;
- an unexpected second call is detected.

The fraud mock records its inputs as well. This makes interaction behavior observable without connecting to an external service.

The distinction is important: a stub primarily controls behavior, while a mock also establishes an expectation about how the system communicates with the dependency.

## Fake

A fake is a lightweight working implementation.

The fraud fake maintains a set of blocked customer identifiers. It performs a real lookup against that set rather than returning one fixed value for every request.

The repository fake stores payment states in memory. It therefore behaves like a small persistence layer while avoiding a database connection.

These fakes are useful when the test needs realistic stateful behavior but does not need the complexity, latency, or operational dependencies of production infrastructure.

## Dependency Isolation

Dependency isolation is broader than any one test-double type.

The implementation uses dependency injection so that `PaymentService` receives its gateway, fraud service, and repository from outside the service itself.

This creates a controlled boundary:

`Production adapter`
`        ↓`
`PaymentService`
`        ↑`
`Stub / Mock / Fake`

The production gateway can be composed with test doubles for the other dependencies. Tests can therefore isolate one behavior without replacing the entire application.

## Python Implementation

The Python implementation uses `Protocol` definitions to express dependency contracts without requiring a common concrete base class.

`dataclass(frozen=True)` provides an immutable payment value object. Enums provide explicit payment states. Dictionaries provide in-memory persistence, while `unittest` provides executable verification.

The tests cover:

- predetermined gateway behavior through a stub;
- customer blocking through a fake;
- exact gateway and fraud interactions through mocks;
- validation failure before dependency invocation;
- composition with production-style components.

The `main` function runs the test suite and exits with a failure status when a test fails.

## JavaScript Implementation

The JavaScript implementation uses classes, `Map`, `Set`, Promises, asynchronous dependency methods, and Node.js `EventEmitter`.

The asynchronous design reflects a realistic service boundary where gateway and repository operations may involve network or storage latency.

`StubGateway` controls the authorization result. `FakeFraudService` performs a deterministic customer-set lookup. `FakeRepository` stores state in a `Map`. `MockGateway` records complete payment objects so interaction expectations can be checked.

The `processed` event exposes an event-driven audit boundary after successful persistence.

Validation rejects malformed payment objects before dependency calls occur.

## C++17 Implementation

The C++ implementation uses abstract interfaces and concrete dependency implementations.

`IPaymentGateway`, `IFraudService`, and `IPaymentRepository` define narrow contracts. `PaymentService` receives references to those interfaces, making replacement explicit and avoiding ownership ambiguity.

The mock stores calls in a `std::vector`. The fake fraud service uses `std::set` for deterministic membership checks. The repository uses `std::map` for in-memory state.

The implementation also demonstrates exception-based validation and explicit verification of interaction expectations.

The tests verify that invalid payments produce no dependency calls. This is significant because a validation test should not accidentally exercise an external boundary.

## Java 17 Implementation

The Java implementation models the payment as an immutable record and uses interfaces for dependency contracts.

The service layer separates orchestration from dependency behavior. `ValidationException` represents domain validation failures.

The stub gateway provides deterministic authorization. The fake fraud service maintains blocked customers. The fake repository stores results in a `HashMap`. The mock gateway records every payment passed to it.

Java collections and immutable record values make the interaction assertions explicit while avoiding external testing libraries.

The enterprise-oriented design makes it possible to replace infrastructure adapters without modifying the service's business workflow.

## PostgreSQL Implementation

The PostgreSQL model represents mocking metadata and test execution as relational data.

The principal tables are:

| Table | Purpose |
|---|---|
| `services` | Systems under test |
| `test_cases` | Individual behavioral tests |
| `dependencies` | Real, stub, fake, and mock dependency definitions |
| `dependency_calls` | Recorded dependency interactions |
| `test_executions` | Test outcomes |
| `payments` | Domain payment state |

The `dependency_kind` enum explicitly distinguishes `real`, `stub`, `fake`, and `mock`.

Foreign keys prevent dependency calls from referencing unknown dependencies or test cases. Unique constraints prevent duplicate invocation numbers for the same dependency and test case.

The payment table uses a primary key, amount validation, currency validation, and an enumerated status.

## Database Workflow

The SQL script inserts realistic dependencies and test cases, records dependency interactions, and records execution outcomes.

A successful stub test records one gateway call with an approved response.

A fake fraud test records a suspicious result for a blocked customer.

A mock test records one authorization interaction.

An invalid-input test records that no dependency interaction was needed.

A deliberately failing interaction test records two mock calls where exactly one was expected. This represents a useful failure mode for interaction-based testing.

The `record_dependency_call` function calculates the next invocation number within the test and dependency boundary. This keeps interaction history ordered without requiring application-side numbering.

## Validation Rules

The implementations enforce the same essential domain conditions:

- payment identifier must be present;
- customer identifier must be present;
- amount must be positive;
- currency must contain exactly three uppercase letters;
- validation must happen before external dependency calls.

This ordering protects tests from accidental side effects and makes failures easier to diagnose.

## Failure Modes

Important failure cases include:

| Failure | Expected behavior |
|---|---|
| Missing payment ID | Reject before dependencies |
| Missing customer ID | Reject before dependencies |
| Non-positive amount | Reject before dependencies |
| Invalid currency | Reject before dependencies |
| Blocked customer | Decline without gateway authorization |
| Unexpected mock call | Fail interaction verification |
| Missing repository persistence | Detect through stored-state assertions |

A mock that records two calls when one was expected demonstrates why interaction verification must be explicit.

## Performance Considerations

The examples use in-memory collections for test doubles because tests should avoid unnecessary network and database latency.

Typical lookup costs are approximately:

- Python set membership: average `O(1)`;
- JavaScript `Set` membership: average `O(1)`;
- C++ `std::set` membership: `O(log n)`;
- Java `HashSet` membership: average `O(1)`;
- PostgreSQL indexed dependency and execution queries: dependent on planner choice and data volume, with indexes supplied for the primary reporting access paths.

Mocks should record only information required by the assertions. Excessive interaction logging increases memory usage and makes tests harder to maintain.

## Security Considerations

Test doubles must not accidentally expose production secrets or credentials.

The implementations use synthetic payment identifiers and customer identifiers. No real credentials, payment tokens, or external service credentials are required.

Production adapters should keep authentication material outside source code and should avoid logging sensitive payment information.

Mocks and fakes should not weaken authorization logic in integration environments where real security controls are being evaluated. Their purpose is isolation, not bypassing security requirements.

## Design Trade-offs

Mocks provide precise interaction verification but can make tests sensitive to implementation details. A refactoring that preserves behavior may require mock expectations to change.

Stubs are less coupled to implementation details but provide limited verification of interactions.

Fakes provide stronger behavioral realism than fixed stubs but require maintenance because their simplified behavior must remain aligned with the contract they represent.

Dependency injection introduces explicit constructor dependencies, but that complexity is useful because it makes external boundaries visible and replaceable.

## Practical Testing Boundary

The four concepts operate at different levels:

`Dependency isolation`
`        ↓`
`Choose a replacement`
`        ↓`
`Stub / Fake / Mock`
`        ↓`
`Exercise the system under test`
`        ↓`
`Verify output and, where required, interaction`

A good unit test replaces dependencies only to the extent necessary for the behavior under examination. A test should not use a mock merely because mocking is available.

## Files

| File | Technical focus |
|---|---|
| Python | Protocol-based dependency injection, dataclasses, stubs, mocks, fakes, assertions, executable tests |
| JavaScript | Asynchronous dependencies, Promises, Maps, Sets, EventEmitter, interaction verification |
| C++17 | Abstract interfaces, value types, STL containers, exception handling, explicit mock verification |
| Java 17 | Records, interfaces, immutable collections, service classes, validation exceptions, domain-oriented testing |
| PostgreSQL | Relational dependency model, enums, constraints, functions, triggers, transactions, reporting views |

## Execution

Python requires Python 3.10 or later because the implementation uses modern typing and dataclass features. Run the file directly with `python`.

JavaScript requires a current Node.js runtime. Run the file with `node`.

C++ requires a compiler with C++17 support. Compile with the C++17 language standard and execute the resulting binary.

Java requires Java 17 or later. Compile the source file and run the resulting class.

PostgreSQL requires a database session capable of creating schemas, tables, functions, triggers, views, and enum types. The SQL script creates its own `mocking_demo` schema and removes an existing schema of the same name before rebuilding the model.
