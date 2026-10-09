# Architectural Patterns: Layered, MVC, and Hexagonal

## Scope

This project examines three architectural patterns that solve different organizational problems:

- **Layered architecture** separates a system into responsibility-oriented layers such as presentation, application, domain, and infrastructure.
- **Model-View-Controller (MVC)** separates interaction handling, application state, and presentation.
- **Hexagonal architecture**, also called **Ports and Adapters**, isolates the application core from technologies such as databases, HTTP frameworks, messaging systems, and external services.

The implementations use an order-processing domain so that the architectural differences can be observed without changing the fundamental business rule. The same kind of order must contain valid items, may be confirmed from a pending state, and must have its persistence and notification concerns handled somewhere outside the core business entity.

The important distinction is that these patterns organize dependencies and responsibilities differently. They are not three alternative names for the same structure.

---

## Core Domain Used by the Implementations

An order contains:

- an order identifier
- a customer identifier
- one or more order items
- a quantity and unit price for each item
- a lifecycle state such as `PENDING`, `CONFIRMED`, or `CANCELLED`

The domain enforces rules that should remain true regardless of whether the application uses a layered, MVC, or hexagonal architecture.

Examples include:

- an order cannot be empty
- an item quantity must be positive
- an item price cannot be negative
- a pending order can be confirmed
- an already confirmed order cannot be confirmed again
- persistence should occur only after the domain object has passed validation

This separation is important because an architectural pattern does not replace domain modeling. Architecture determines how components depend on one another, while domain logic determines what the system is allowed to do.

---

# Layered Architecture

## Structure

The Python, JavaScript, C++, Java, and SQL examples represent the conventional layered idea in different ways.

A typical structure is:

`Presentation → Application → Domain → Infrastructure`

The **presentation layer** handles an external interaction. It may be an HTTP controller, command-line interface, web endpoint, or other user-facing boundary.

The **application layer** coordinates a use case. It decides which domain operations must occur and which persistence or external services are needed.

The **domain layer** represents business concepts and rules. It should not need to know whether the application uses PostgreSQL, an HTTP framework, a message broker, or a console.

The **infrastructure layer** provides technical capabilities such as repositories, database access, notifications, filesystem operations, or external integrations.

The strength of the structure is its familiarity. It is straightforward to explain and works well when a system has conventional request-to-database flows.

The architectural risk appears when upper layers become tightly coupled to concrete infrastructure details. An application service that directly creates a specific database client, for example, becomes harder to test without that database.

---

## Python Layered Implementation

The Python implementation uses:

- `layered_controller()` as the presentation boundary
- `LayeredOrderService` as the application service
- `Order` and `OrderItem` as domain objects
- `InMemoryOrderRepository` and `ConsoleNotificationService` as infrastructure

The application service constructs the domain object, invokes the confirmation rule, persists the result, and requests a notification.

The repository uses a dictionary keyed by order ID. This gives average constant-time lookup for the in-memory demonstration and keeps persistence behavior separate from the domain object.

Validation occurs before persistence. An invalid quantity or negative price therefore produces an `OrderValidationError` rather than creating an invalid order.

---

## JavaScript Layered Implementation

The JavaScript version adds asynchronous behavior because JavaScript applications frequently cross asynchronous infrastructure boundaries.

`LayeredRepository.save()` and `LayeredNotificationService.sendConfirmation()` return promises. The application service therefore coordinates asynchronous persistence and notification using `await`.

The controller converts domain failures into an HTTP-like response object:

`{ statusCode: 400, body: { error: ... } }`

This illustrates a useful boundary rule: the domain should not need to know about HTTP status codes. The controller translates a domain failure into a transport representation.

---

## C++ Layered Implementation

The C++ example uses concrete repository and notification classes directly from `LayeredOrderService`.

This makes the dependency structure easy to see. The service receives references to infrastructure objects and uses them during the use case.

The repository uses `std::unordered_map`, giving average O(1) lookup by order ID. Order totals require traversal of the order's items and therefore have O(n) complexity with respect to the number of items.

The important architectural observation is that good algorithmic complexity does not automatically produce good architecture. The repository can be efficient while still being tightly coupled to the application service.

---

## Java Layered Implementation

The Java implementation represents the layered approach with:

- `LayeredOrderService`
- `LayeredRepository`
- `LayeredNotificationService`
- shared domain objects

Java's collections and immutable `List.copyOf()` usage help prevent accidental modification of the order's item collection after construction.

The service coordinates the business operation and infrastructure calls directly. This is simple, but replacing infrastructure implementations can require changes in the service when concrete dependencies become deeply embedded.

---

# Model-View-Controller

## MVC Responsibilities

MVC separates three major responsibilities.

### Model

The model represents application state and domain behavior relevant to that application.

In the examples, `OrderModel` owns the collection of orders and creates valid order objects.

### Controller

The controller interprets an external action and decides what model operation should occur.

The controller should not become a second model. If business rules are duplicated inside controllers, the architecture develops inconsistent behavior because different entry points can implement the same rule differently.

### View

The view transforms model state into a representation suitable for presentation.

The Python view produces formatted text. The JavaScript view produces a structured object that could be consumed by a browser interface. The Java view constructs a textual representation.

The view should not decide whether an order can be confirmed. That decision belongs to the model or domain layer.

---

## MVC Versus Layered Architecture

MVC and layered architecture can coexist.

For example, a web application may have:

`HTTP Controller → Application Service → Domain → Repository`

while the web presentation itself follows an MVC organization.

The important difference is the concern each pattern emphasizes.

Layered architecture is primarily concerned with **separation into dependency layers**.

MVC is primarily concerned with **interaction between input control, state, and presentation**.

Calling a controller an "MVC controller" does not automatically make the entire system MVC. Similarly, placing classes in folders named `controller`, `service`, and `repository` does not by itself guarantee a meaningful layered architecture.

---

## Python MVC Implementation

The Python implementation uses:

- `OrderModel` for application state
- `OrderController` for command coordination
- `OrderView` for presentation

The controller converts raw tuples into `OrderItem` objects and invokes the model. The view receives the resulting domain object and formats it.

A validation failure is translated by the controller into a view-level error representation.

This demonstrates why presentation formatting should remain outside the domain entity.

---

## JavaScript MVC Implementation

The JavaScript version models a browser-oriented response more explicitly.

`OrderView.render()` produces an object containing:

- order identity
- customer identity
- status
- total
- individual line information

That object could be converted into HTML by a browser-specific rendering layer without changing the model.

The implementation therefore avoids coupling the model to DOM APIs.

---

## Java MVC Implementation

The Java MVC implementation uses separate `OrderModel`, `OrderController`, and `OrderView` classes.

The model owns its order collection.

The controller coordinates model creation and asks the view to render the resulting state.

The view has no authority to change the order lifecycle. This prevents presentation code from becoming a source of business-state corruption.

---

# Hexagonal Architecture

## Ports and Adapters

Hexagonal architecture puts the application and domain core at the center.

The core declares **ports** representing capabilities it needs or exposes.

Adapters implement those ports.

A simplified dependency relationship is:

`Driving Adapter → Application Port → Application Core`

and:

`Application Core → Driven Port ← Infrastructure Adapter`

A database adapter may implement a repository port.

A messaging adapter may implement a notification port.

An HTTP controller may act as a driving adapter that invokes the application.

The application core does not need to know that PostgreSQL, Kafka, an HTTP framework, or a specific cloud provider exists.

---

## Dependency Inversion

The key architectural mechanism is dependency inversion.

In a tightly coupled design, an application service might directly depend on:

`PostgresOrderRepository`

In a hexagonal design, the application depends on:

`OrderRepositoryPort`

and PostgreSQL-specific code implements that port.

The concrete dependency therefore points toward the abstraction rather than forcing the application core to depend on the infrastructure technology.

This is particularly valuable when:

- infrastructure changes independently of business rules
- the application requires fast unit tests
- several delivery mechanisms invoke the same use case
- external systems have unstable interfaces
- domain logic needs to remain independent of frameworks

---

## Python Hexagonal Implementation

The Python program defines `OrderRepositoryPort` and `NotificationPort` using `Protocol`.

`HexagonalOrderApplication` depends on those behavioral contracts.

`MemoryOrderRepositoryAdapter` and `ConsoleNotificationAdapter` implement the required behavior.

`RecordingNotificationAdapter` is used as a test adapter. The application core can therefore be tested without a real database or notification provider.

This is a concrete demonstration of the architectural advantage rather than merely a class hierarchy.

---

## JavaScript Hexagonal Implementation

JavaScript does not require compile-time interfaces, so the example represents ports through expected behavior and validates those capabilities when the application is composed.

`HexagonalApplication` requires a repository with `save()` and `findById()` operations and a notifier with `sendConfirmation()`.

The example also uses Node.js `EventEmitter` as an infrastructure mechanism. The application core does not depend on the event bus. The event-driven notification adapter translates the application-level notification request into an infrastructure event.

This demonstrates an important JavaScript architectural boundary: asynchronous infrastructure can be replaced without changing the order domain.

---

## C++ Hexagonal Implementation

The C++ implementation uses abstract base classes:

- `OrderRepositoryPort`
- `NotificationPort`

The application depends on references to those interfaces.

`MemoryOrderAdapter` and `ConsoleNotificationAdapter` provide concrete implementations.

`RecordingNotificationAdapter` is a test adapter.

The C++ version makes the dependency inversion especially explicit because the compiler enforces the interface contract through virtual methods.

The application core can therefore be exercised without a database or external notification implementation.

---

## Java Hexagonal Implementation

Java interfaces provide explicit ports:

- `OrderRepositoryPort`
- `NotificationPort`

`OrderApplication` depends on those interfaces rather than concrete infrastructure classes.

`MemoryOrderAdapter` provides persistence.

`ConsoleNotificationAdapter` provides external notification behavior.

`RecordingNotificationAdapter` acts as a test double.

The Java implementation also uses `Objects.requireNonNull()` at composition time so that a missing adapter cannot silently produce a partially configured application.

---

# Architectural Relationships

The three patterns can be related without treating them as interchangeable.

| Concern | Layered | MVC | Hexagonal |
|---|---|---|---|
| Main focus | Responsibility layers | Interaction and presentation | Dependency isolation |
| Typical core idea | Presentation, application, domain, infrastructure | Model, view, controller | Ports and adapters |
| Primary architectural question | Which layer owns this responsibility? | Who handles input, state, and rendering? | Which side owns the dependency? |
| Infrastructure coupling | Can become direct | Depends on implementation | Explicitly isolated through ports |
| Testing benefit | Depends on dependency design | Controllers and models can be isolated | Strong isolation of application core |
| Presentation relationship | Usually an outer layer | Central architectural concern | Usually a driving adapter |
| Database relationship | Commonly infrastructure | Often behind model/service layers | Driven adapter |
| Best distinguishing feature | Vertical responsibility boundaries | Separation of interaction/state/view | Dependency direction |

A system can use more than one of these ideas.

For example, a web application may use MVC at the delivery boundary, layered organization for application services, and hexagonal dependency inversion around the domain core.

The patterns therefore operate at different architectural dimensions.

---

# Architecture Does Not Mean Folder Names

A directory such as:

`controller/`

`service/`

`repository/`

does not prove that the application has a good layered architecture.

Similarly, classes named `Model`, `View`, and `Controller` do not prove that the MVC responsibilities are correctly separated.

Hexagonal architecture is also not created merely by introducing interfaces. The important question is whether the application core actually depends on those ports and whether infrastructure depends on the core-facing abstractions rather than the reverse.

Architecture is demonstrated by dependency relationships, responsibility boundaries, and change isolation.

---

# SQL Data Model

The PostgreSQL script represents the persistence boundary for the same order domain.

The main entities are:

- `customers`
- `products`
- `orders`
- `order_items`

Foreign keys maintain relational integrity.

The `order_status` enum restricts lifecycle values to known states.

`CHECK` constraints protect important database-level invariants such as positive quantities and non-negative prices.

The unique constraint on `(order_id, product_id)` prevents duplicate product lines within one order.

The order summary view provides a read-oriented projection containing customer information, order status, total units, and calculated order value.

---

## Transaction Handling

Order creation is performed through transactions.

The order header and its line items are inserted as one logical operation.

The transaction then changes the order to `CONFIRMED`.

If an operation fails and the transaction is rolled back, the database does not leave a half-created order.

This is an important distinction between architectural responsibility and database responsibility. The application architecture decides where business operations are coordinated, while the database protects transactional and relational integrity.

---

# State Integrity

The SQL trigger prevents an already confirmed order from being returned to `PENDING`.

The domain objects in the programming languages enforce the same conceptual rule through methods such as `confirm()`.

Having both application-level and database-level protection is useful when the rule is critical.

Application validation provides immediate domain feedback.

Database constraints protect persistent state against:

- defective application code
- direct database access
- incorrect migration scripts
- integration jobs
- administrative operations that bypass normal application paths

The database should not necessarily contain every business rule, but invariants that must never be violated in persisted data are strong candidates for database enforcement.

---

# Edge Cases Demonstrated

The implementations explicitly handle several failure conditions.

An empty order is rejected because an order without lines has no meaningful transaction value.

A zero or negative quantity is rejected because it would invalidate the order line.

A negative price is rejected because monetary values cannot be negative in the demonstrated product model.

A confirmed order cannot be confirmed again because the lifecycle transition is not idempotent in the domain model.

The SQL trigger prevents a confirmed order from returning to `PENDING`.

Foreign-key enforcement prevents an order item from referencing a nonexistent product.

The Java implementation also demonstrates a transaction-value policy that rejects an order exceeding a configured business threshold.

These checks illustrate an important architectural principle: validation should occur at the boundary where the relevant invariant is owned, while critical persistence invariants can be reinforced at the database layer.

---

# Testing and Replaceable Infrastructure

The hexagonal examples use test-specific adapters.

The Python program uses `FakeOrderRepository` and `RecordingNotificationAdapter`.

The JavaScript program uses `MemoryOrderAdapter` and `EventNotificationAdapter`.

The C++ program uses `MemoryOrderAdapter` and `RecordingNotificationAdapter`.

The Java program uses `MemoryOrderAdapter` and `RecordingNotificationAdapter`.

These are not merely convenient mocks. They demonstrate an architectural consequence of dependency inversion: the application core can be exercised without installing or connecting to its production infrastructure.

This reduces test setup cost and allows failures in business logic to be distinguished from failures in external systems.

---

# Performance Considerations

Architectural patterns do not automatically improve runtime performance.

Layer boundaries can introduce additional object creation, method calls, serialization, or network boundaries if they are implemented across processes.

MVC does not inherently make rendering faster. Its value comes from separating presentation responsibilities from application state and control flow.

Hexagonal architecture does not make a database query faster. Its value is that database access can be changed, optimized, cached, batched, or replaced without requiring business rules to depend directly on the database technology.

The examples use in-memory maps for demonstration. Their average lookup behavior is suitable for the small educational workload but does not represent the characteristics of a production database.

The SQL script adds indexes specifically for common lookup patterns such as finding orders by customer and finding items belonging to an order.

---

# Security Considerations

Architecture should also establish security boundaries.

Authentication and authorization decisions should not be hidden inside presentation formatting.

An HTTP controller should validate external input, but sensitive authorization rules should be represented in an appropriate application or domain policy rather than trusting client-supplied state.

Infrastructure adapters should control access to external systems.

Database credentials should not be embedded in domain objects.

SQL parameters should be used instead of concatenating untrusted input into SQL statements.

The examples use fixed values and therefore do not require parameter-binding code, but a production implementation should treat all external input as untrusted.

---

# Common Architectural Failure Modes

## Anemic Layered Design

A project may create many layers while placing nearly all logic in one service class. This produces structural separation without meaningful responsibility separation.

The solution is to place domain invariants with the domain objects and keep application services focused on use-case coordination.

## Fat Controllers

An MVC controller that calculates totals, validates every business rule, performs persistence, and formats HTML has accumulated several unrelated responsibilities.

The controller should coordinate the interaction rather than become the entire application.

## Fat Views

A view that decides whether an order is valid or changes its lifecycle state has crossed into domain behavior.

Views should represent state rather than own business rules.

## Fake Hexagonal Architecture

Adding interfaces without changing dependency direction does not create a useful ports-and-adapters design.

If the application still directly constructs a PostgreSQL repository, the abstraction exists but the dependency remains tightly coupled.

## Excessive Abstraction

Interfaces for every class can make a small application harder to understand.

Hexagonal architecture is most useful when the boundary represents a meaningful external dependency or architectural seam.

---

# Practical Design Decisions

The examples deliberately use an order-processing domain because it creates meaningful boundaries.

Persistence is separate because data storage is an infrastructure concern.

Notification is separate because it represents an external capability.

Order validation remains close to the order because it expresses a domain invariant.

Presentation formatting remains outside the domain because formatting is not a business rule.

Application services coordinate operations because a use case may involve several domain operations and external capabilities.

These boundaries remain useful even if the actual infrastructure changes from memory storage to PostgreSQL or from console output to an external messaging service.

---

# Implementation Mapping

| Implementation | Main architectural focus | Concrete mechanism |
|---|---|---|
| Python | All three patterns in one executable comparison | Protocols, classes, adapters, repositories, test doubles |
| JavaScript | Async and event-driven architectural boundaries | Promises, `EventEmitter`, object composition |
| C++ | Explicit dependency inversion | Abstract port classes and concrete adapters |
| Java | Enterprise domain modeling and explicit interfaces | Enums, records, collections, interfaces, immutable lists |
| PostgreSQL | Persistence boundary and integrity | Foreign keys, constraints, indexes, views, transactions, triggers |

The implementations are intentionally complementary rather than line-by-line translations.

---

# When the Patterns Fit

Layered architecture is appropriate when a team needs a clear conventional separation between presentation, application logic, domain logic, and infrastructure.

MVC is appropriate when the system has a substantial interaction and presentation concern where input control, application state, and representation need explicit separation.

Hexagonal architecture is particularly valuable when the application core must remain independent from external technologies and when testing, replaceable infrastructure, or multiple delivery mechanisms are important.

A mature system can combine these patterns. For example:

`Web MVC Controller → Application Service → Domain Core ← Ports ← Infrastructure Adapters`

In that arrangement, MVC organizes the interaction boundary, layered thinking organizes application responsibilities, and hexagonal dependency inversion protects the core from infrastructure.

The patterns are therefore better understood as complementary architectural tools than as mutually exclusive templates.
