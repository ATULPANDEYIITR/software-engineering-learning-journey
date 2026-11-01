# Unit Testing: Test Cases, Assertions, and Fixtures

## Scope

This project models unit testing through executable examples built around an order-processing domain.

The central testing relationship is:

`Fixture → Test Case → Action → Assertion → Result`

The implementations cover:

- deterministic test data
- test isolation
- assertions
- positive and negative test cases
- validation testing
- state-transition testing
- calculation testing
- exception testing
- rollback testing
- temporary-file fixtures
- policy evaluation
- test-run persistence
- aggregate test reporting

The domain contains products, inventory, orders, order items, payment state, cancellation, and repository-governance policy evaluation.

The implementation does not treat a test case as merely an example input. Each test defines an expected observable behavior and checks that behavior against an explicit assertion.

## Testing Model

A unit test isolates a small unit of behavior and verifies a defined contract.

A useful model for the project is:

    Fixture
       |
       v
    Arrange
       |
       v
    Act
       |
       v
    Assert
       |
       v
    Pass / Fail

The fixture supplies controlled data. The test arranges the initial state, performs an operation, and asserts the resulting state, returned value, or failure condition.

The project deliberately includes both successful and failing scenarios because validation of failure behavior is part of the unit contract.

## Test Cases

A test case identifies a specific behavior that must remain correct.

The source implementations test behaviors such as:

| Test category | Example behavior | Expected observation |
|---|---|---|
| Validation | Negative product price | Validation error |
| Validation | Zero quantity | Validation error |
| Calculation | Order subtotal | Exact monetary value |
| Calculation | Taxed total | Exact monetary value |
| State transition | Payment | `new` becomes `paid` |
| State transition | Cancellation | `paid` becomes `cancelled` |
| Failure handling | Insufficient inventory | Operation fails |
| Rollback | Partial reservation failure | Earlier reservations are released |
| Policy | Required approvals | Insufficient approvals block eligibility |
| Policy | Failed status check | Merge eligibility is denied |
| File behavior | Exported fixture | Stored data can be read back |

A good test case has one primary reason to fail. This makes a failure easier to diagnose and reduces accidental coupling between unrelated behaviors.

## Assertions

Assertions convert expected behavior into executable checks.

The Python implementation uses `unittest` assertions such as `assertEqual`, `assertTrue`, and `assertRaises`.

The JavaScript implementation uses Node's `assert` module and `assert.rejects` for asynchronous failure conditions.

The C++ implementation combines `assert` for invariants with an explicit test runner and exception checks.

The Java implementation provides explicit assertion helpers for equality, Boolean conditions, and expected exceptions.

The PostgreSQL implementation uses SQL comparisons, `DO` blocks, constraints, triggers, and query results to express database-level assertions.

An assertion should inspect observable behavior rather than implementation details. For example, a payment test checks the resulting order state and inventory quantity instead of checking how the service internally iterated over its data.

## Fixtures

Fixtures provide controlled input data.

The standard catalog contains:

| Product | Price | Initial stock |
|---|---:|---:|
| Mechanical Keyboard | 80.00 | 10 |
| Wireless Mouse | 25.00 | 20 |
| USB Headset | 45.00 | 5 |

The normal order fixture contains two keyboards and one mouse:

`2 × 80.00 + 1 × 25.00 = 185.00`

With an 18% tax rate:

`185.00 × 1.18 = 218.30`

A second fixture deliberately requests six headsets when only five exist. It is used to verify failure handling and rollback.

Fixtures should be stable and isolated. A test must not rely on inventory mutations left behind by another test.

## Test Isolation

Each language creates fresh domain state for its relevant tests.

Python uses `setUp()` to create a new inventory before each test.

JavaScript uses fixture factory functions so each test receives a new `Inventory`.

Java creates a new `Inventory` and order inside each test method.

C++ constructs independent objects inside each test function.

The PostgreSQL implementation stores reusable fixtures as database records and creates separate test-run and test-result records. Database constraints prevent invalid persisted test results.

Isolation matters because this sequence is unsafe:

    Test A changes shared state
             |
             v
    Test B reads changed state
             |
             v
    Test B passes or fails depending on execution order

A reliable test suite should produce the same result when tests are executed independently or in a different order, subject to explicitly documented integration dependencies.

## Python Implementation

The Python file uses `unittest`, `dataclasses`, `Enum`, `Decimal`, temporary directories, JSON serialization, and explicit domain exceptions.

`Product`, `OrderItem`, and `Order` model the test domain.

`Inventory` provides controlled stock operations. `OrderService` contains the behaviors under test.

The service uses `Decimal` for monetary calculations rather than binary floating-point arithmetic. This avoids common representation problems when comparing currency values.

The payment operation records successful inventory reservations. If a later reservation fails, previously reserved items are released. The tests verify this rollback behavior directly.

The fixture class provides a repeatable catalog.

The file also contains a temporary-file test. The temporary directory is created for the test and automatically removed afterward. This prevents test artifacts from polluting the working directory.

The test suite can be executed directly with Python because the file invokes `unittest.main()`.

## JavaScript Implementation

The JavaScript implementation uses Node.js built-in modules rather than external packages.

Node's `node:test` module provides the test runner. `node:assert/strict` supplies assertions. `node:fs/promises` and `node:os` support the temporary-file fixture.

The implementation uses `Map` for inventory lookup and asynchronous `pay()` behavior to exercise Promise-based testing.

The failed payment scenario is particularly important. The service may reserve an earlier item successfully before discovering that a later item is unavailable. The test verifies that the earlier reservation is undone.

The temporary-file test demonstrates an external resource fixture. The test creates a temporary directory, writes structured JSON, reads it back, verifies the result, and removes the directory in a `finally` block.

Asynchronous failure is tested with `assert.rejects`, which ensures that rejected Promises are treated as expected test outcomes rather than unhandled failures.

## C++17 Implementation

The C++ program presents unit testing through a small explicit test runner.

The domain uses:

- `struct` for value-oriented records
- classes for inventory and policy behavior
- `std::map` for product lookup
- `std::vector` for ordered test data
- exceptions for invalid operations
- `assert` for simple invariants

The `TestRunner` captures exceptions and records passed and failed test cases.

The `expectThrows` helper verifies that a specific failure condition actually occurs.

The program also contains a repository-governance policy engine. This is intentionally separate from the inventory example. It evaluates merge eligibility using independent conditions:

- required approval count
- passing automated checks
- resolved conversations
- presence of proposed changes

This illustrates a unit-test principle: policy rules should be testable independently from the larger application workflow.

The governance tests cover both the successful condition and individual policy failures.

## Java 17 Implementation

The Java implementation uses records for immutable product and order-item values, an enum for order state, interfaces for policy behavior, collections for domain state, and custom exceptions for invalid operations.

`ProtectedBranchPolicy` implements `MergePolicy`, separating merge rules from the order-processing domain.

`OrderService` handles calculations, inventory reservations, payment, and cancellation.

The test methods explicitly create their own fixtures. This makes state dependencies visible and prevents a payment test from depending on a previous test's mutation.

The rollback test verifies that a multi-item operation behaves atomically from the domain perspective. If a later reservation fails, earlier reservations are released and the order remains `NEW`.

The Java assertion helper `assertThrows` checks failure contracts without requiring an external testing library.

## PostgreSQL Implementation

The PostgreSQL implementation treats test data and test execution as relational information.

The schema contains:

- `products`
- `customers`
- `orders`
- `order_items`
- `test_suites`
- `test_cases`
- `test_runs`
- `test_results`
- `fixtures`

Foreign keys maintain relationships between suites, cases, runs, and results.

Check constraints reject invalid quantities, prices, durations, and inconsistent test-result states.

A failed test result requires a failure message. A trigger enforces this rule at the database boundary.

The `calculate_order_subtotal` function evaluates order data. `calculate_order_total` applies the defined tax rate.

The `test_run_report` view aggregates execution information into total, passed, failed, and skipped counts.

The `failing_tests` view isolates failures for diagnostic reporting.

The fixture table stores structured JSONB data for reusable test inputs.

The transaction example demonstrates that database changes can be tested and rolled back without leaving persistent side effects.

## Positive and Negative Testing

A complete unit-testing strategy requires both valid and invalid inputs.

Positive tests establish that supported inputs work:

- valid products are accepted
- valid quantities are accepted
- correct totals are calculated
- payment changes state correctly
- cancellation restores inventory
- eligible policies return `true`

Negative tests establish that invalid operations are rejected:

- negative prices
- negative stock
- zero quantities
- unknown products
- insufficient stock
- payment of already-paid orders
- cancellation of unpaid orders
- insufficient approvals
- failed status checks
- unresolved conversations

The distinction is important because successful execution alone does not establish that validation rules are correct.

## State-Transition Testing

The order lifecycle is modeled as:

    NEW
      |
      | payment succeeds
      v
    PAID
      |
      | cancellation
      v
    CANCELLED

Invalid transitions are rejected.

A `NEW` order cannot be cancelled.

A `PAID` order cannot be paid again.

A cancelled order does not silently re-enter the payment workflow.

Testing state transitions prevents defects in which an operation succeeds even though the object is in an incompatible state.

## Rollback Testing

Rollback behavior is tested explicitly.

Consider an order containing:

- two keyboards
- six headsets

The keyboard reservation can succeed because ten are available. The headset reservation must fail because only five exist.

The expected behavior is not merely an error.

The complete contract is:

1. keyboard reservation is attempted
2. headset reservation fails
3. the operation reports failure
4. keyboard inventory is restored
5. headset inventory remains unchanged
6. the order remains `NEW`

This verifies atomic behavior at the service level.

The PostgreSQL transaction example demonstrates the corresponding database principle: changes that violate an invariant should not remain partially applied.

## Test Failure Diagnostics

A useful test failure should identify:

- which test failed
- the expected condition
- the actual condition
- the relevant domain state
- the failure message where appropriate

The PostgreSQL `test_results` table stores actual results and failure messages.

The C++ runner prints the test name and exception message.

The Java runner reports the test name and assertion failure.

Node's test runner provides structured failure information.

Python's `unittest` runner reports the failed test and assertion details.

Failure information should be sufficient to locate the violated behavior without requiring examination of unrelated tests.

## Test Granularity

The source files focus on units such as:

- product validation
- inventory lookup
- inventory reservation
- order calculations
- order state transitions
- rollback behavior
- policy eligibility

These are smaller units than an end-to-end repository or application test.

The PostgreSQL layer adds relational validation because database constraints and triggers are themselves important executable behavior.

Unit tests should remain focused enough that a failure identifies a narrow area of responsibility.

## Performance Considerations

The in-memory implementations use direct product lookup structures.

Python uses a dictionary.

JavaScript uses a `Map`.

Java uses a `HashMap`.

C++ uses a `std::map`, giving ordered lookup with logarithmic lookup complexity.

For the PostgreSQL model, indexes target actual access paths:

- test cases by suite
- test runs by suite and start time
- test results by run and status
- fixtures by type

A test suite should not create large amounts of unnecessary fixture data. Small deterministic fixtures make tests faster and reduce accidental dependencies.

## Security and Reliability Considerations

Test fixtures should not contain production credentials, authentication tokens, private keys, or real personal data.

The database model uses constraints to prevent invalid state from being stored.

The service implementations validate externally supplied identifiers and quantities before modifying state.

Temporary files are created in controlled temporary directories and removed after testing.

Database transactions are used when a test intentionally exercises state changes that should not persist.

Tests should not depend on system time, network availability, external services, or uncontrolled filesystem state unless those dependencies are explicitly part of the behavior being tested.

## Edge Cases

The implementations cover several important boundary conditions:

| Edge case | Expected behavior |
|---|---|
| Empty product ID | Reject |
| Empty customer | Reject |
| Negative price | Reject |
| Negative stock | Reject |
| Zero quantity | Reject |
| Unknown product | Reject |
| Empty order | Reject |
| Insufficient stock | Reject and restore prior reservations |
| Repeated payment | Reject |
| Cancellation before payment | Reject |
| Missing required approval | Merge eligibility denied |
| Failed status check | Merge eligibility denied |
| Unresolved conversation | Merge eligibility denied |
| Failed database test without message | Database trigger rejects result |

Boundary cases are especially valuable because defects often occur where normal assumptions stop being valid.

## Relationship Between Test Case, Assertion, and Fixture

These three concepts serve different purposes.

| Concept | Responsibility |
|---|---|
| Fixture | Provides controlled starting data |
| Test case | Defines one behavior under examination |
| Assertion | Verifies the expected observation |

A fixture is not itself a test.

An assertion is not itself a fixture.

A test case combines controlled setup, an operation, and one or more meaningful assertions.

For example:

    Fixture:
        Keyboard stock = 10
        Mouse stock = 20

    Test:
        Pay an order containing 2 keyboards and 1 mouse

    Assertions:
        total = 218.30
        order status = PAID
        keyboard stock = 8
        mouse stock = 19

This separation keeps test intent clear.

## Practical Test Workflow

A realistic development workflow represented by the project is:

    Define behavior
          |
          v
    Build fixture
          |
          v
    Arrange initial state
          |
          v
    Execute unit
          |
          v
    Assert result
          |
          v
    Record pass/failure
          |
          v
    Diagnose regression

When a failure occurs, the test result should identify the violated contract rather than simply reporting that the application stopped.

## Limitations

The implementations are unit-testing learning artifacts rather than complete production testing frameworks.

They do not attempt to model every feature of mature test systems such as parallel test scheduling, property-based generation, mutation testing, distributed test execution, code coverage instrumentation, browser automation, or service virtualization.

The PostgreSQL implementation tests database behavior directly but does not attempt to reproduce the full lifecycle of an external application test runner.

The C++ and Java examples use lightweight assertion infrastructure so that the domain behavior remains visible without third-party dependencies.

The Python and JavaScript files use standard runtime testing facilities available in their respective ecosystems.

The important boundary is that unit tests should validate isolated behavior with controlled inputs. Larger integration and end-to-end concerns require different test scopes and should not be forced into every unit test.
