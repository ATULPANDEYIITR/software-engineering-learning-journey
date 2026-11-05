## 1. Introduction

Behavior-Driven Development (BDD) is a software development approach that describes system functionality through observable business behaviors.

It connects business requirements, software implementation, and acceptance testing through a common description of expected behavior.

BDD focuses on what a system must do rather than how its internal implementation works.

A typical BDD workflow involves:

1. Identifying a business requirement.
2. Discussing expected behavior with stakeholders.
3. Expressing that behavior through scenarios.
4. Implementing executable acceptance criteria.
5. Executing scenarios against the application.
6. Reviewing failures and refining the implementation.

The five implementations in this project model an e-commerce order-processing workflow. They demonstrate how customer authentication, inventory validation, payment authorization, order confirmation, and inventory updates can be expressed as business scenarios and verified through acceptance tests.

## 2. Core BDD concepts

### 2.1 Feature

A feature represents a business capability.

Examples include:

- Customer registration.
- Order placement.
- Payment processing.
- Inventory management.
- Account authentication.

A feature groups related scenarios under one business requirement.

In the implementations, the feature is named `Online order placement` or an equivalent enterprise-oriented description.

### 2.2 Behavior

A behavior describes an observable system response to a particular situation.

For example:

When an authenticated customer purchases two available products, the system must:

- Validate customer authentication.
- Check inventory availability.
- Calculate the order amount.
- Authorize payment.
- Confirm the order.
- Reduce available inventory.

The behavior is independent of the programming language, database implementation, and internal application architecture.

### 2.3 Scenario

A scenario represents one specific example of system behavior.

A scenario has:

- A business context.
- An action performed by an actor.
- An expected observable result.

A scenario should be sufficiently focused to identify the behavior being verified.

### 2.4 Given-When-Then structure

BDD commonly uses the Given-When-Then format.

| Keyword | Purpose | Example |
|---|---|---|
| Given | Establishes the initial context | Given the customer is authenticated |
| When | Describes the action | When the customer places an order |
| Then | Defines the expected outcome | Then the order is confirmed |
| And | Extends an existing step | And inventory decreases |

The three primary stages represent different parts of a behavior.

**Given** establishes the initial state.

**When** triggers the behavior.

**Then** checks the resulting state.

The `And` keyword improves readability when multiple conditions belong to the same stage.

### 2.5 Acceptance criteria

Acceptance criteria are specific conditions that must be satisfied before a feature or behavior can be considered acceptable.

For order placement, acceptance criteria include:

- Only authenticated customers can place orders.
- Order quantities must be positive.
- Requested quantities cannot exceed available inventory.
- Payment authorization must succeed.
- The calculated total must include applicable tax.
- Successful orders must receive a confirmation status.
- Failed transactions must not consume inventory.

Acceptance criteria should be measurable and testable.

## 3. The order-processing domain

The project uses a consistent business domain across all five source files.

### Business entities

| Entity | Responsibility |
|---|---|
| Customer | Initiates an order |
| Product | Defines product information and price |
| Inventory | Tracks available stock |
| Order | Records the purchase |
| Payment gateway | Authorizes payment |
| Feature | Groups related business requirements |
| Scenario | Describes one expected behavior |
| Step | Represents a Given, When, Then, or And condition |
| Execution | Records the outcome of a scenario |
| Acceptance criterion | Defines a condition for acceptance |

### Business rules

The example application uses the following rules:

| Rule | Expected behavior |
|---|---|
| Authentication | Unauthenticated customers are rejected |
| Product existence | Unknown products cannot be ordered |
| Quantity | Quantity must be greater than zero |
| Inventory | Requested quantity cannot exceed stock |
| Payment | Payment must be authorized |
| Tax | A 10% tax is applied |
| Confirmation | Valid purchases produce confirmed orders |
| Failure handling | Rejected orders must not reduce inventory |

The sample product has a unit price of 1000.00.

For a quantity of two:

- Subtotal: 2000.00
- Tax: 200.00
- Total: 2200.00

The calculation is:

\[
Total = Quantity \times Price \times (1 + TaxRate)
\]

Financial calculations should use decimal arithmetic rather than binary floating-point arithmetic where exact monetary values are required.

The Python and Java implementations use decimal arithmetic for this reason.

## 4. Scenario design and structure

### 4.1 Positive scenarios

Positive scenarios verify that the system performs the requested operation when all business conditions are satisfied.

Example:

**Feature:** Online order placement

**Scenario:** Successful order placement

- Given the customer is authenticated.
- And the product has 10 units available.
- When the customer purchases two units.
- Then the order is confirmed.
- And the inventory contains eight units.
- And the total includes the applicable tax.

A positive scenario should verify both the primary outcome and important resulting state changes.

### 4.2 Negative scenarios

Negative scenarios verify that invalid operations are rejected correctly.

The implementations cover three important failure conditions.

| Scenario | Expected result |
|---|---|
| Insufficient inventory | Order rejected |
| Unauthenticated customer | Request rejected |
| Failed payment | Order rejected |

Negative acceptance testing is important because successful execution alone does not demonstrate that business restrictions are enforced.

A system that confirms valid orders but also accepts unauthorized purchases does not satisfy the intended behavior.

### 4.3 Scenario outlines

A Scenario Outline represents a behavior that must be evaluated using multiple input combinations.

For example:

| Quantity | Unit price | Tax | Expected total |
|---:|---:|---:|---:|
| 1 | 1000 | 10% | 1100 |
| 2 | 1000 | 10% | 2200 |
| 3 | 1000 | 10% | 3300 |

The same behavior is executed for each example.

This approach avoids creating several nearly identical scenarios.

The Python, JavaScript, C++17, and Java 17 programs implement data-driven acceptance tests.

PostgreSQL stores the corresponding examples as JSONB records.

## 5. Python implementation

**File:** `behavior_driven_development.py`

The Python implementation demonstrates a lightweight BDD execution framework using standard-library capabilities.

### 5.1 Domain modeling

The implementation uses dataclasses for:

- `Product`
- `Order`
- `ScenarioContext`
- `Step`
- `Scenario`
- `ScenarioResult`

The `OrderStatus` enumeration represents order states.

The scenario context stores test-specific state, including products, payment authorization, authentication, orders, and errors.

Using a separate context for every scenario prevents state from leaking between independent acceptance tests.

### 5.2 Business behavior

The `OrderService` implements the actual order-processing rules.

Its responsibilities include:

- Validating customer authentication.
- Checking product existence.
- Validating quantities.
- Checking inventory.
- Calculating totals.
- Processing payment authorization.
- Updating inventory.
- Creating confirmed orders.

Business validation takes place before inventory is modified.

This prevents failed authentication, inventory checks, and payment authorization from consuming stock.

### 5.3 Step registry

The `StepRegistry` provides a simple mechanism for associating BDD keywords with executable functions.

The supported keywords are:

- Given
- When
- Then
- And

The registry checks whether a requested step implementation exists.

An undefined step raises an exception instead of silently passing.

The example scenarios use executable step functions directly, while the registry demonstrates reusable keyword-based step registration.

### 5.4 Scenario execution

`BDDRunner` executes each scenario against a fresh `ScenarioContext`.

Each scenario receives an independent execution result.

The runner captures:

- Scenario name.
- Execution status.
- Execution duration.
- Failure information.

The implementation uses `time.perf_counter()` for elapsed-time measurement.

### 5.5 Failure handling

The business service rejects:

- Unknown products.
- Invalid quantities.
- Unauthenticated customers.
- Insufficient inventory.
- Failed payment authorization.

The runner distinguishes a failed scenario from a successfully completed scenario.

The final process returns a nonzero exit status when an acceptance scenario fails.

### 5.6 Practical limitations

The Python implementation is a compact educational BDD runner rather than a complete production framework.

It does not implement:

- Gherkin file parsing.
- External browser automation.
- Distributed execution.
- Persistent execution history.
- Real payment integration.
- Concurrent inventory reservation.

The in-memory inventory model also does not provide database-level transaction isolation.

A production implementation would require durable storage, concurrency control, payment idempotency, and integration-level acceptance tests.

## 6. JavaScript implementation

**File:** `behavior_driven_development.js`

The JavaScript implementation uses an event-driven architecture.

Its primary engineering perspective is the relationship between business behavior, domain events, asynchronous processing, and compensating actions.

### 6.1 Event-driven architecture

The `EventBus` maintains a mapping between event types and registered handlers.

The application publishes an `OrderConfirmed` event after creating an order.

Subscribers can respond to that event independently.

For example:

- Notification services can send order confirmations.
- Fulfillment services can initiate shipment processing.
- Analytics services can record order activity.

The event bus uses asynchronous functions and awaits registered handlers.

This makes handler failures observable during scenario execution.

### 6.2 State management

The `Inventory` class uses a private `Map` to maintain product information.

It provides controlled methods for:

- Adding products.
- Retrieving products.
- Reserving inventory.
- Releasing inventory.

Private fields prevent external code from directly modifying the internal product collection.

### 6.3 Compensating actions

The order service reserves inventory and publishes an event.

If event processing fails, the service removes the order and releases the reserved inventory.

This is a compensating action.

It demonstrates a simplified transaction-like workflow across application components.

It is not equivalent to a distributed atomic transaction.

Production systems generally require durable event publication, an outbox pattern, idempotent consumers, and recovery mechanisms.

### 6.4 Asynchronous scenario execution

The BDD runner executes each step using `await`.

Sequential scenario execution is deliberate because multiple scenarios sharing mutable inventory could produce nondeterministic results.

Independent scenarios can be executed concurrently when they use isolated fixtures and independent resources.

### 6.5 Acceptance validation

The implementation uses Node.js assertion facilities to verify:

- Order confirmation.
- Inventory changes.
- Event publication.
- Authentication enforcement.
- Inventory rejection.
- Payment failure.

The scenario runner reports individual outcomes and returns an overall failure status.

### 6.6 Practical limitations

The event bus is an in-memory implementation.

It does not provide:

- Durable event delivery.
- Retry queues.
- Dead-letter handling.
- Distributed event ordering.
- Persistent order storage.
- Cross-service transaction guarantees.

These concerns become important when BDD scenarios are extended to distributed applications.

## 7. C++17 implementation

**File:** `behavior_driven_development.cpp`

The C++17 implementation emphasizes explicit domain modeling, typed scenario definitions, and controlled state transitions.

### 7.1 Strong domain types

The implementation defines:

- `OrderStatus`
- `StepType`
- `Product`
- `Order`
- `TestContext`
- `BDDStep`
- `Scenario`
- `Feature`
- `ScenarioResult`

Enumerations distinguish different workflow states.

Structures represent domain entities and test information.

The `TestContext` uses STL containers to maintain scenario-specific state.

### 7.2 Executable steps

The implementation defines:

`StepFunction` as a function accepting a mutable scenario context.

Each BDD step contains:

- A keyword.
- A description.
- An executable function.

The use of `std::function` allows individual steps to encapsulate different business operations.

Lambda expressions capture scenario-specific values such as product identifiers, prices, and quantities.

### 7.3 Scenario construction

The `Scenario` class provides an `addStep()` method.

This allows scenarios to be assembled using a fluent interface.

Each scenario stores its steps in execution order.

The `Feature` class groups related scenarios.

This separation keeps feature organization distinct from business behavior.

### 7.4 Execution engine

The `BDDRunner` creates a new `TestContext` for each scenario.

It executes each step sequentially.

Exceptions are captured and converted into failed scenario results.

The execution report includes duration and failure information.

### 7.5 Data-driven acceptance testing

The implementation uses a collection of example structures.

Each example contains:

- Quantity.
- Available stock.
- Expected total.

The same business service evaluates every example.

This illustrates parameterized scenario execution without requiring a separate scenario definition for each quantity.

### 7.6 Performance and limitations

The implementation uses:

- `std::map` for product storage.
- `std::vector` for scenario steps.
- `std::function` for executable behavior.
- `std::chrono` for timing.
- STL algorithms for reporting.

Product lookup using `std::map` takes logarithmic time.

Vector insertion at the end is amortized constant time.

The implementation is sequential and in-memory.

It does not provide concurrent inventory synchronization, durable test reporting, or external system integration.

The use of floating-point arithmetic for the demonstration should be replaced with an appropriate decimal or integer-minor-unit representation in a production financial application.

## 8. Java 17 implementation

**File:** `BehaviorDrivenDevelopment.java`

The Java implementation emphasizes enterprise domain modeling, service boundaries, policy interfaces, immutable structures, and acceptance validation.

### 8.1 Records and immutable domain objects

The implementation uses Java records for:

- `Product`
- `Order`
- `ScenarioResult`
- `BDDStep`

Records provide compact data models with generated accessors and value-based equality.

The `Product` constructor validates domain invariants.

The implementation uses `BigDecimal` for monetary calculations.

### 8.2 Service abstraction

The `PaymentGateway` interface separates payment authorization from order processing.

`SimulatedPaymentGateway` provides a deterministic implementation for acceptance testing.

This allows the order service to depend on an abstraction rather than a particular payment provider.

A production gateway could implement the same interface while integrating with an external payment processor.

### 8.3 Acceptance policies

`AcceptancePolicy` defines an explicit validation contract.

`OrderConfirmationPolicy` checks whether the scenario produced a confirmed order.

This separates acceptance conditions from the underlying order-processing implementation.

The policy can be extended to verify additional enterprise conditions.

### 8.4 BDD execution model

The Java implementation models steps using:

- `StepKeyword`
- `BDDStep`
- `Scenario`
- `Feature`
- `BDDRunner`

The `Consumer<TestContext>` interface represents an executable step.

The runner evaluates steps sequentially and records individual outcomes.

Custom exceptions distinguish business-rule failures from acceptance-test failures.

### 8.5 State transitions

The application uses the following conceptual order lifecycle:

`PENDING → CONFIRMED`

An order is confirmed only after:

1. Customer authentication.
2. Product validation.
3. Quantity validation.
4. Inventory validation.
5. Payment authorization.

A rejected request does not create a confirmed order.

The context also records confirmation events.

### 8.6 Enterprise considerations

The Java implementation demonstrates:

- Dependency abstraction.
- Explicit validation.
- Domain-specific exceptions.
- Immutable records.
- Collection-based state management.
- Policy-driven acceptance conditions.
- Service-level business rules.

The simulated gateway is not a substitute for an actual payment integration.

The example also lacks persistent transaction management and distributed coordination.

An enterprise implementation would typically use database transactions, idempotency keys, durable event processing, structured logging, and isolated integration-test environments.

## 9. PostgreSQL implementation

**File:** `behavior_driven_development.sql`

The PostgreSQL implementation models BDD as a persistent acceptance-testing management system.

Unlike the application examples, which execute business behavior in memory, this implementation stores features, scenarios, steps, criteria, executions, and test results.

### 9.1 Relational architecture

The database contains the following primary relationships:

| Table | Purpose |
|---|---|
| users | Stores test participants and their roles |
| features | Stores business capabilities |
| scenarios | Stores individual behavior examples |
| scenario_steps | Stores ordered Given-When-Then steps |
| scenario_examples | Stores data-driven test parameters |
| test_environments | Identifies execution environments |
| acceptance_criteria | Stores explicit acceptance conditions |
| scenario_executions | Records execution attempts |
| step_execution_results | Records individual step outcomes |

The main relationship is:

`Feature → Scenario → Scenario Steps`

Execution information follows a separate relationship:

`Scenario → Execution → Step Execution Results`

This separates the specification of expected behavior from the history of actual test execution.

### 9.2 Constraints and integrity

The schema uses primary keys, foreign keys, unique constraints, and check constraints.

Examples include:

- Scenario names must be valid.
- Step sequence numbers must be positive.
- Scenario keys must be unique.
- Execution durations cannot be negative.
- JSONB example parameters must be objects.
- Completed execution states require completion timestamps.

These restrictions prevent invalid records from entering the database.

### 9.3 Scenario activation

The activation triggers validate that a scenario contains:

- At least one Given step.
- At least one When step.
- At least one Then step.
- At least one mandatory acceptance criterion.

This prevents incomplete scenarios from becoming active.

The trigger validates the transition into the active state.

It does not replace application-level validation or authorization.

### 9.4 Execution management

`scenario_executions` stores each execution attempt.

It identifies:

- The scenario.
- The environment.
- The executing user.
- The execution status.
- The start and completion timestamps.
- The execution duration.
- The associated build reference.
- Failure information.

`step_execution_results` records the outcome of each individual step.

The unique constraint on `(execution_id, step_id)` prevents duplicate results for the same step within an execution.

### 9.5 Completion procedure

The `complete_execution` procedure accepts an execution identifier and a terminal execution status.

It:

1. Validates the requested terminal state.
2. Locks the running execution.
3. Verifies that the execution exists and is running.
4. Calculates elapsed time.
5. Updates the execution status.
6. Records the completion timestamp.

The row lock prevents simultaneous completion operations from independently updating the same execution.

### 9.6 Execution result validation

The execution validation trigger checks whether:

- Every expected scenario step has a result.
- Passing executions contain no failed or blocked steps.
- Failed executions contain at least one failed or blocked step.

This provides consistency between scenario-level and step-level results.

The implementation uses an immediate validation trigger. Step results must therefore be recorded before the execution is marked as completed.

### 9.7 Scenario outlines with JSONB

The `scenario_examples` table stores input combinations in JSONB.

Example parameters include:

- Quantity.
- Product price.
- Tax rate.
- Expected total.

JSONB provides flexible parameter storage while retaining PostgreSQL's ability to extract and evaluate individual values.

The scenario outline query calculates the expected amount and compares it with the stored result.

### 9.8 Reporting

The SQL implementation provides several reporting mechanisms.

**Feature retrieval**

The `feature_scenario_details` view displays feature and scenario information with step and acceptance-criteria counts.

**Execution reporting**

The `scenario_execution_report` view joins scenario executions with environments and users.

**Aggregation**

The execution aggregation CTE calculates:

- Total executions.
- Passed executions.
- Failed executions.
- Blocked executions.
- Pass percentage.

**Failure analysis**

The step-level report identifies failed and blocked steps.

**Eligibility determination**

The eligibility query evaluates whether a scenario:

- Is active.
- Contains mandatory acceptance criteria.
- Has at least one successful execution.

Eligibility in this schema represents the presence of a qualifying historical successful execution. It does not establish that the latest execution passed or that every deployment environment has passed acceptance testing.

### 9.9 Transaction handling

The SQL script includes a transaction rollback demonstration.

A temporary scenario is inserted inside a nested PL/pgSQL exception block.

An intentional exception causes the nested operation to roll back.

The surrounding transaction continues.

This demonstrates how PostgreSQL subtransactions can isolate failed operations without discarding unrelated work.

### 9.10 Security and performance

The schema uses foreign keys, constraints, and indexes to enforce data integrity and support common reporting queries.

The indexes focus on:

- Scenario step ordering.
- Enabled scenario examples.
- Scenario execution history.
- Execution status.
- Step-level execution results.

The script defines role information but does not implement PostgreSQL authentication, row-level security, or database grants.

A production deployment should restrict database permissions and protect sensitive execution logs.

## 10. Distinctions between BDD and related testing approaches

BDD is related to several other testing practices, but the terms describe different purposes.

| Approach | Primary purpose |
|---|---|
| BDD | Describes expected business behavior |
| Unit testing | Verifies individual functions or components |
| Integration testing | Verifies interactions between components |
| Acceptance testing | Determines whether specified acceptance conditions are satisfied |
| End-to-end testing | Verifies complete application workflows |
| Regression testing | Detects unintended changes to previously working behavior |
| Performance testing | Evaluates speed, throughput, and resource consumption |

BDD can be used to define acceptance tests, integration tests, and end-to-end scenarios.

It is not restricted to one testing level.

A Given-When-Then description does not automatically make a test an end-to-end test. The actual scope depends on which application components and external systems are exercised.

## 11. BDD execution workflow

The five implementations collectively demonstrate this workflow:

Business Requirement
        |
        v
      Feature
        |
        v
     Scenario
        |
        v
 Given - When - Then
        |
        v
   Step Definitions
        |
        v
 Business Application
        |
        v
  Acceptance Assertions
        |
        v
 Scenario Execution
        |
        v
  Passed / Failed
        |
        v
     Test Report
The feature and scenario describe expected behavior.

Step definitions translate the descriptions into executable operations.

The application performs the actual business logic.

Assertions compare the resulting state with acceptance criteria.

The execution report records whether the expected behavior was satisfied.

## 12. Scenario quality and design rules

A reliable BDD specification should describe meaningful business behavior.

### Clear scenarios

Scenario names should identify the behavior being verified.

Prefer:

- Successful order placement.
- Rejection of an unauthenticated purchase.
- Payment failure without inventory reservation.

Avoid names that only describe implementation details.

### Observable outcomes

A Then step should verify something measurable.

Examples:

- The order status is confirmed.
- The remaining inventory equals eight.
- The payment authorization is rejected.
- No order record is created.

An assertion that merely verifies that a function executed does not necessarily establish that the business requirement was satisfied.

### Independent scenarios

Every scenario should establish its own required context.

One scenario should not depend on a preceding scenario having passed.

This improves repeatability and makes individual failures easier to diagnose.

### Controlled test data

Test fixtures should be deterministic.

Scenarios should use known:

- Customers.
- Product prices.
- Inventory quantities.
- Payment outcomes.
- Expected totals.

Sensitive production customer information should not be copied into ordinary acceptance-test environments.

### Failure isolation

A failed scenario should not corrupt subsequent scenarios.

The Python, C++17, and Java implementations use independent in-memory contexts.

The JavaScript implementation uses isolated environment instances.

The PostgreSQL implementation maintains separate execution records.

## 13. Failure modes and engineering considerations

| Failure mode | Engineering response |
|---|---|
| Undefined BDD step | Report the missing implementation |
| Invalid test data | Validate fixtures before execution |
| Shared mutable state | Isolate scenario contexts |
| Payment rejection | Prevent order confirmation |
| Insufficient inventory | Reject the requested quantity |
| Incorrect calculated amount | Verify monetary arithmetic |
| Event-handler failure | Execute compensating recovery |
| Incomplete execution results | Reject invalid completion |
| Duplicate execution results | Enforce uniqueness |
| Database transaction failure | Roll back affected operations |
| Flaky external dependencies | Isolate or control integration boundaries |

BDD specifications should remain stable even when internal implementation details change.

If a business rule changes, its corresponding scenarios and acceptance criteria should be updated.

## 14. Performance and scalability

BDD execution performance depends on the size of the feature suite, the cost of each scenario, and the systems involved.

Important considerations include:

- **Scenario isolation:** Independent scenarios can run in parallel when their data and external resources are isolated.
- **Test data preparation:** Reusable fixtures can reduce setup overhead, but shared mutable fixtures can introduce interference.
- **External dependencies:** Real payment gateways, databases, and network services can increase execution time and failure variability.
- **Execution reporting:** Persistent execution records support trend analysis and failure investigation.
- **Database indexing:** Indexes on scenario identifiers, execution timestamps, and execution statuses improve common retrieval operations.
- **Failure diagnosis:** Step-level execution results help locate the precise business condition that failed.

A larger acceptance suite should distinguish fast deterministic tests from slower integration and end-to-end tests.

## 15. Limitations of the implementations

The implementations are independent learning artifacts rather than a single integrated testing platform.

| Implementation | Primary strength | Main limitation |
|---|---|---|
| Python | Reusable step registry and scenario execution | No Gherkin parser |
| JavaScript | Asynchronous event processing and compensating actions | In-memory event delivery |
| C++17 | Typed domain model and executable scenario composition | No external test integration |
| Java 17 | Enterprise service and policy abstractions | Simulated payment gateway |
| PostgreSQL | Persistent BDD specifications and execution reporting | Does not execute application behavior |

None of the implementations integrates directly with a browser automation framework or a real payment processor.

The SQL schema manages test specifications and results. It does not execute the Python, JavaScript, C++, or Java application code.

## 16. Source file execution

| File | Execution command |
|---|---|
| Python | `python behavior_driven_development.py` |
| JavaScript | `node behavior_driven_development.js` |
| C++17 | `g++ -std=c++17 -O2 behavior_driven_development.cpp -o bdd && ./bdd` |
| Java 17 | `javac BehaviorDrivenDevelopment.java` followed by `java BehaviorDrivenDevelopment` |
| PostgreSQL | Execute `behavior_driven_development.sql` using PostgreSQL |

The Python and JavaScript implementations use built-in runtime capabilities.

The C++17 implementation requires a C++17-compatible compiler.

The Java implementation requires Java 17.

The SQL implementation requires PostgreSQL 14 or later.

## 17. Technical relationships across the implementations

The implementations share one business domain but use different architectural approaches.

| BDD responsibility | Python | JavaScript | C++17 | Java 17 | PostgreSQL |
|---|---|---|---|---|---|
| Feature definition | `Feature` | `Feature` | `Feature` | `Feature` | `features` |
| Scenario definition | `Scenario` | `Scenario` | `Scenario` | `Scenario` | `scenarios` |
| Step execution | Callable functions | Async functions | `std::function` | `Consumer` | Step records |
| Business logic | `OrderService` | `OrderService` | `OrderService` | `OrderService` | Relational workflow |
| State management | Dataclasses and dictionaries | Maps and private fields | STL containers | Collections | Relational tables |
| Acceptance validation | Assertions | Node assertions | Exceptions and checks | Acceptance policies | Constraints and triggers |
| Reporting | JSON report | JSON report | Console report | Scenario results | Views and queries |

The central principle remains consistent across all implementations:

**Business behavior is specified through scenarios, executed through application operations, and verified against explicit acceptance conditions.**
