# Dependency Injection

## Scope

Dependency Injection (DI) is an architectural technique in which an object receives the services it needs from an external composition mechanism instead of constructing those services itself.

The central distinction is between **using a dependency** and **creating a dependency**.

An application service may need a payment gateway, repository, or notification service. Its business logic should describe what it needs through a contract. The composition root decides which concrete implementation satisfies that contract.

A useful dependency direction is:

`Composition Root → Application Service → Dependency Contract`

and:

`Concrete Infrastructure → Dependency Contract`

This keeps business behavior separated from infrastructure construction.

The deliverables use an order-processing domain because it provides realistic boundaries between application logic, persistence, payment infrastructure, notification infrastructure, and replaceable test doubles.

---

## Core DI Concepts

### Dependency

A dependency is an external capability required by a component to perform its responsibility.

`OrderService` depends on an order repository because it must check whether an order already exists and persist successful orders. It depends on a payment gateway because payment is an external operation. It depends on a notification service because a successful payment produces a customer receipt.

The important design question is not merely whether a class has dependencies. It is whether the class controls their construction.

A class such as `HardWiredOrderService` creates its own payment and notification objects. This couples application behavior to particular infrastructure implementations.

The injected `OrderService` receives those dependencies through its constructor. The service can therefore operate with production infrastructure, in-memory infrastructure, or deterministic test doubles without modifying its business logic.

### Dependency Injection

DI moves object construction outside the component that uses the dependency.

The Python implementation demonstrates this through `OrderService(repository, payment_gateway, notification_service)`.

The Java implementation expresses the same architectural boundary with interfaces and a constructor whose parameters are `OrderRepository`, `PaymentGateway`, and `NotificationService`.

The C++ implementation uses abstract classes and references. The service retains references to interface types rather than concrete infrastructure classes.

The JavaScript implementation uses constructor parameters and runtime validation because JavaScript does not require interfaces at the language level.

### Inversion of Control

Without DI, a component commonly controls both behavior and dependency construction.

With DI, the component controls its own business behavior but the composition root controls which implementation is supplied.

This is an inversion of control because the application service no longer decides which concrete payment gateway or repository it will instantiate.

DI does not require a framework. A manually constructed object graph is already a valid DI implementation.

---

## Injection Forms

### Constructor Injection

Constructor injection is the primary pattern used throughout the implementations.

A constructor such as:

`OrderService(repository, paymentGateway, notificationService)`

makes dependencies explicit and mandatory.

This has several important properties:

- The object cannot be fully constructed without its required dependencies.
- Dependencies can normally be stored as immutable references.
- Tests can substitute fakes without modifying production code.
- The class signature communicates its collaboration boundary.
- Missing dependencies fail during construction rather than much later during execution.

Constructor injection is usually the strongest default for required dependencies.

### Function Injection

A dependency does not always need to be a class.

The Python, C++, JavaScript, and Java implementations inject pricing or tax policies as functions or functional objects.

For example, the pricing operation can receive either a standard tax calculation or a zero-tax calculation.

This is useful when the dependency is behavior rather than a stateful service.

Function injection avoids creating an unnecessary class merely to represent a small policy.

### Property Injection

The Python implementation contains `OptionalAuditOrderProcessor`, where an audit logger can be assigned after construction.

This is deliberately limited to an optional dependency.

Property injection has a significant weakness for required services: an object can exist in an incompletely configured state.

For that reason, a required payment gateway should normally be constructor-injected rather than assigned later.

---

## Dependency Contracts

A DI architecture benefits from contracts that describe what the application actually requires.

The domain does not need to know whether payment is implemented by a remote provider, a simulator, or a test double.

The relevant contract is simply the capability:

`charge(order)`

Similarly, the notification contract exposes the ability to send a receipt without exposing the details of an email API, message broker, or console implementation.

This creates a boundary between stable application behavior and replaceable infrastructure.

The C++ program represents contracts using abstract classes with virtual methods.

The Java program uses interfaces.

Python uses `Protocol`, allowing structural typing without forcing every implementation into an inheritance hierarchy.

JavaScript uses the expected method shape at runtime because the language does not require nominal interface declarations.

---

## Dependency Containers

A dependency injection container is a registry and object-construction mechanism that maps an abstraction or token to a provider.

A container commonly performs three tasks:

- Registration defines how a dependency should be created.
- Resolution requests the dependency.
- Lifetime management determines whether a new instance or an existing instance is returned.

The custom containers in the Python, JavaScript, C++, and Java implementations are intentionally small. They expose the mechanism instead of hiding it behind a framework.

A typical registration concept is:

`PaymentGateway → ProductionPaymentGateway`

A resolution operation then obtains the configured implementation without the consuming service directly constructing it.

A container is therefore not the definition of DI. It is infrastructure that can automate dependency composition.

---

## Composition Root

The composition root is the location where concrete implementations are selected and the application object graph is assembled.

The Python function `build_production_container()` performs this responsibility.

The JavaScript `buildApplication()` function registers the infrastructure and constructs the service graph.

The Java `buildProductionContainer()` method performs the same composition role.

The C++ `buildApplication()` function explicitly creates the concrete repository, payment gateway, notification service, and application service.

Keeping this decision in one place prevents infrastructure choices from leaking throughout the application.

For example, changing a production payment adapter should require changing the composition configuration rather than changing the order-processing algorithm.

---

## Dependency Lifetimes

The deliverables distinguish three common lifetime concepts.

### Transient

A transient dependency is created each time it is resolved.

The examples use payment gateways as transient registrations to demonstrate that two resolutions can produce distinct objects.

Transient scope can be appropriate when an object contains short-lived state or when sharing an instance would create unwanted coupling.

### Singleton

A singleton registration creates one shared instance for the relevant container.

The repositories and some notification services are configured as singleton examples.

Singleton lifetime is not automatically better. Shared mutable state can create concurrency problems, hidden coupling, and test contamination.

An object should be singleton only when its state and thread-safety characteristics justify shared lifetime.

### Scoped

A scoped lifetime represents one instance within a defined execution scope, such as an HTTP request or transaction.

The SQL model demonstrates `scoped` as a configuration value so that lifetime policy is represented explicitly in the relational dependency configuration.

A real container normally associates a scoped object with an execution context and disposes it when that context ends.

---

## Testability

DI improves testability by allowing a test to replace infrastructure with controlled implementations.

The tests use `FakePaymentGateway` and `FakeNotificationService`.

A successful-order test can verify that:

- the payment dependency was called,
- the order was persisted,
- a receipt was produced,
- notification was requested.

The payment-failure test verifies that the order is not persisted after payment rejection and that notification is not sent.

The duplicate-order test verifies an important ordering rule: the repository is checked before another payment attempt occurs.

These tests do not need a real payment provider, SMTP server, database server, or network connection.

The value of DI is therefore not simply easier mocking. It creates explicit architectural seams where behavior can be isolated.

---

## Python Implementation

The Python program progresses from direct constructor injection to function injection, optional property injection, a lightweight container, explicit lifetimes, and service-level test doubles.

`Protocol` defines dependency contracts without requiring infrastructure classes to inherit from a common base class.

`OrderService` contains the application rules:

- validate the order,
- reject duplicates,
- request payment,
- persist the order,
- create the receipt,
- request notification.

The composition function determines which implementations are used.

The `HardWiredOrderService` is intentionally included as a contrast. It creates `ConsolePaymentGateway` and `ConsoleNotificationService` internally, making replacement difficult.

The tests demonstrate the architectural benefit of the injected version rather than merely testing Python syntax.

---

## JavaScript Implementation

The JavaScript implementation emphasizes runtime composition and asynchronous dependencies.

The payment and notification operations return promises, reflecting the asynchronous behavior common in Node.js infrastructure.

`OrderApplicationService` receives a store, payment provider, and notifier through its constructor.

The pricing example uses function injection. A tax policy can be supplied as an ordinary JavaScript function, making the policy replaceable without introducing another object hierarchy.

`AuditBus` demonstrates event-driven dependency behavior. The order service can publish an `order.paid` event through an injected event bus while listeners decide what should happen with that event.

The container demonstrates singleton and transient lifetimes using factory functions.

The tests use fake dependencies and asynchronous assertions to isolate the application service from external infrastructure.

---

## C++ Case Study

The C++ program treats dependency injection as an enterprise service-design problem.

`IOrderRepository`, `IPaymentGateway`, and `INotificationService` define explicit contracts.

`OrderService` receives references to those contracts through constructor injection.

Concrete implementations include:

- `MemoryOrderRepository` for persistence without an external database.
- `SimulatedPaymentGateway` for infrastructure simulation.
- `ConsoleNotificationService` for observable notification behavior.
- `FakePaymentGateway` and `FakeNotificationService` for deterministic tests.

The C++ design uses RAII and smart pointers at the composition boundary. `Application` owns concrete service objects through `std::unique_ptr`, while `OrderService` operates through references to the required abstractions.

The case study also demonstrates function injection through `std::function<double(double)>`.

The tests verify failure behavior as well as successful execution. In particular, payment failure must not result in order persistence, and a duplicate order must be rejected before another payment operation is attempted.

---

## Java Enterprise Model

The Java implementation models DI using explicit interfaces and immutable record-based domain objects.

`Order`, `Receipt`, and the application contracts have clear boundaries.

`OrderService` depends on `OrderRepository`, `PaymentGateway`, and `NotificationService`. Its constructor uses `Objects.requireNonNull` to prevent silently accepting an invalid dependency graph.

`OrderProcessingException` represents an application-level failure that the caller can handle without depending on infrastructure-specific exceptions.

`PricingService` demonstrates policy injection with `Function<Double, Double>`.

The container uses Java's generic types and a provider abstraction. Its singleton provider caches the created object, while transient providers execute the factory on every resolution.

The Java tests demonstrate how interfaces make infrastructure substitution explicit and compile-time visible.

---

## SQL Dependency Model

The PostgreSQL script models DI configuration as relational data.

`service_contract` represents dependency abstractions.

`service_implementation` represents concrete implementations that satisfy those contracts.

`application_environment` represents execution contexts such as development, test, staging, and production.

`dependency_registration` connects an environment to one implementation for a particular contract and records the lifetime policy.

The unique constraint on `(environment_id, contract_id)` prevents two competing implementations from being registered for the same contract in one environment.

This is important because an application composition graph should not silently contain ambiguous implementations for a single required contract.

The `resolved_dependencies` view provides a readable representation of the configured dependency graph.

---

## Database-Level Integrity

The SQL script uses constraints for rules that belong to the data layer.

The order model prevents:

- duplicate external order identifiers,
- non-positive order amounts,
- malformed customer email values,
- unsupported order states.

Foreign keys prevent orphaned payment attempts and notification records.

The dependency tables use foreign keys so that a registration cannot reference a nonexistent environment, contract, or implementation.

The relational model also exposes a limitation of ordinary SQL constraints: verifying that an implementation belongs to exactly the contract requested by a registration requires a cross-row or cross-table rule that is not represented by a simple `CHECK`.

The diagnostic query against `dependency_registration` and `service_implementation` makes that configuration inconsistency visible.

---

## Transactional Configuration

The SQL script changes a staging dependency lifetime inside a transaction.

The sequence is:

`BEGIN → UPDATE → inspect → COMMIT`

This matters when dependency configuration is stored as operational data. A partial configuration update can create an application that starts with only part of its intended dependency graph.

Transactions allow a configuration change to be inspected and committed atomically.

The invalid negative order example is intentionally wrapped in a transaction and rolled back. PostgreSQL's `CHECK` constraint rejects the invalid data.

---

## DI and Testability Relationship

DI does not automatically make code testable.

A class can technically receive a dependency and still be difficult to test if the dependency is excessively broad, mutable, stateful, or difficult to control.

Good DI design therefore starts with useful dependency boundaries.

For the order service, the payment contract contains the payment capability required by the application. It does not expose every operation of a complete payment SDK.

This reduces the surface that tests must replace and reduces coupling between application logic and infrastructure.

A useful dependency should represent the smallest stable capability that the consuming component actually needs.

---

## DI and Separation of Concerns

Dependency Injection separates **composition decisions** from **business decisions**.

The order service decides whether an order is valid, whether a duplicate exists, and what sequence of operations constitutes successful processing.

The composition root decides whether the repository is in-memory or database-backed and whether payment is simulated or provided by an external service.

The dependency implementation decides how the infrastructure operation is performed.

These responsibilities should not be mixed.

A service that both validates business rules and constructs an HTTP payment client has two different reasons to change.

---

## Common Failure Modes

### Service Locator Misuse

A container can become a service locator when application classes repeatedly ask a global registry for arbitrary dependencies.

That hides dependencies from constructors and makes the class contract harder to understand.

The examples keep resolution in the composition layer instead of passing a container into `OrderService`.

### Over-Injection

A class requiring a very large constructor often has too many responsibilities.

If a service needs twelve unrelated dependencies, the DI container is not necessarily the problem. The service boundary may need redesign.

DI makes excessive coupling visible because the dependency list appears explicitly.

### Incorrect Singleton State

A singleton with mutable request-specific state can leak information between users or requests.

The examples use singleton lifetime to illustrate lifecycle management, but production systems must evaluate thread safety, state ownership, and concurrency before sharing instances.

### Circular Dependencies

A dependency graph such as:

`Service A → Service B → Service A`

cannot be resolved cleanly without introducing another design boundary.

A container may report a circular dependency, recurse indefinitely, or require special lazy-resolution behavior.

The better solution is normally to identify the responsibility that creates the cycle and redesign the dependency boundary.

### Hidden Construction

Calling a concrete constructor inside a supposedly injected service defeats the architectural purpose of DI.

For example, constructing `ProductionPaymentGateway` inside `OrderService` creates a hidden dependency even if another dependency was injected correctly.

---

## Failure Ordering

Dependency injection does not determine business transaction ordering.

The application service still needs an explicit policy for operations such as payment and persistence.

The examples use:

`validate → duplicate check → payment → persistence → notification`

This sequence has a practical limitation: if payment succeeds but persistence fails, the external payment may already have occurred.

Real systems may therefore require transaction coordination, idempotency keys, compensating actions, an outbox pattern, or provider-specific transaction semantics.

DI makes the payment and persistence boundaries replaceable, but it does not magically make distributed operations atomic.

---

## Performance Considerations

Dependency injection adds little runtime cost when dependencies are assembled once at application startup.

Container resolution can introduce overhead through reflection, factory lookup, synchronization, object creation, or graph traversal depending on the implementation.

The larger performance concern is usually inappropriate lifetime management.

Creating expensive infrastructure objects repeatedly can increase latency and resource usage.

Sharing an object that should be isolated can create contention or state corruption.

The lifetime should therefore follow the resource's semantics rather than an arbitrary container convention.

---

## Security Considerations

DI configuration can influence which infrastructure a production application connects to.

An incorrect registration can route a production service to a development database or test payment provider.

Configuration should therefore be treated as operationally sensitive.

External endpoints and credentials should not be embedded directly in source code or committed as ordinary configuration values.

DI containers should also avoid exposing unrestricted runtime resolution to arbitrary application code when doing so could bypass security boundaries.

The SQL model separates implementation metadata from the domain workflow, making dependency configuration auditable.

---

## Debugging Considerations

A useful DI diagnostic should answer:

`Which contract was requested?`

`Which implementation was registered?`

`For which environment?`

`Which lifetime was selected?`

`Where was the object constructed?`

The custom containers intentionally throw explicit errors such as an unregistered dependency rather than allowing a later null-reference failure.

Production containers should provide similar diagnostics without leaking credentials, connection strings, tokens, or other secrets.

---

## Production Design

A production DI architecture should have a clear composition boundary.

Application services should normally depend on interfaces or narrow contracts.

Concrete infrastructure should be selected by configuration or composition code.

Lifetimes should be deliberate.

Required dependencies should normally use constructor injection.

Optional behavior can use explicit policies or carefully controlled optional dependencies.

Infrastructure failures should be translated at appropriate boundaries rather than leaking provider-specific implementation details throughout the domain.

Testing should replace external infrastructure where the test is intended to verify application behavior rather than integration behavior.

DI should support architecture, not become an abstraction layer added to every class without a meaningful dependency boundary.

---

## Relationship Between DI Mechanisms

The implementations preserve a distinction between several mechanisms that are often conflated.

**Dependency Injection** describes the architectural act of supplying a dependency externally.

**Dependency Container** is an optional mechanism that automates registration, construction, and lifetime management.

**Composition Root** is where concrete implementations are selected and the object graph is assembled.

**Test Double** is a replacement dependency used to control or observe behavior during testing.

These mechanisms work together but are not synonymous.

An application can use DI without a container.

A container can exist without producing good architecture.

A test can use a fake dependency without using a container.

The important architectural property is that the consuming component does not own the construction decision for its required infrastructure.

---

## Practical Dependency Graph

The production object graph in the examples can be represented as:

`OrderService`

→ `OrderRepository`

→ `Production repository implementation`

and:

`OrderService`

→ `PaymentGateway`

→ `Production payment implementation`

and:

`OrderService`

→ `NotificationService`

→ `Production notification implementation`

During a unit test, the graph changes to:

`OrderService`

→ `InMemoryOrderRepository`

→ `FakePaymentGateway`

→ `FakeNotificationService`

The business service remains unchanged. Only the composition changes.

This is the core practical value demonstrated across all five programming implementations.
