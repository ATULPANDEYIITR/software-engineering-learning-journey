# Coupling & Cohesion: Loose Coupling and High Cohesion

## Scope

Coupling and cohesion describe two complementary properties of software architecture.

**Coupling** describes how strongly one component depends on other components. High coupling means that a change in one component tends to force changes, knowledge, or coordination in other components.

**Cohesion** describes how closely related the responsibilities inside one component are. High cohesion means that the responsibilities of a component belong together and form a focused purpose.

A useful architectural direction is:

- **Loose coupling:** components communicate through stable contracts and avoid unnecessary knowledge of implementation details.
- **High cohesion:** each component concentrates on a closely related responsibility.

These properties are related but not interchangeable. A class can have a single responsibility and still be tightly coupled to a concrete implementation. A system can also contain many abstractions while putting unrelated responsibilities into the same abstraction.

The implementations in this repository use an order-processing system because it exposes meaningful architectural boundaries: validation, pricing, inventory, payment, persistence, notifications, shipping, auditing, and application orchestration.

## Core distinction

Consider an order-processing workflow.

The business operation can be described as:

`validate order → reserve inventory → charge payment → persist order → notify customer → fulfill shipment`

The important architectural question is not simply whether these operations are necessary. It is where the knowledge about each operation lives.

A tightly coupled design might place inventory access, payment-provider calls, email transmission, database statements, and shipping calls inside one `OrderService`.

That service then knows:

- which database is used;
- how inventory is represented;
- which payment provider is called;
- how payment failures are represented;
- how email is sent;
- how shipment creation works;
- how persistence records are formatted.

The service has many responsibilities, producing low cohesion, while also depending on many concrete mechanisms, producing high coupling.

A more modular design separates those responsibilities and gives the application layer contracts such as `PaymentGateway`, `InventoryRepository`, `OrderRepository`, and `NotificationSender`.

The application service still coordinates the business use case, but it does not need to know whether payment is implemented with a particular provider, whether persistence uses PostgreSQL, or whether notifications are delivered through SMTP, an HTTP API, or a test double.

## High cohesion

High cohesion is primarily concerned with the internal responsibility boundary of a component.

The Python implementation separates:

- `OrderValidator` for order validity;
- `OrderPricing` for pricing calculations;
- `InMemoryInventoryRepository` for inventory reservation;
- `FakePaymentGateway` for payment charging;
- `InMemoryOrderRepository` for order storage;
- `ConsoleNotificationSender` for notifications;
- `FakeShippingService` for shipment creation.

Each component has a small conceptual surface.

For example, `OrderPricing` does not know how payment works. This is more than a stylistic preference. Pricing changes for reasons that are related to pricing rules, while payment-provider changes occur for a different reason.

Keeping those concerns separate limits the scope of change.

### Cohesion is not merely "small classes"

A class with only one method is not automatically highly cohesive.

For example, a class containing methods for:

- calculating order totals;
- opening database connections;
- formatting email;
- validating authentication tokens;
- creating shipments;

may technically contain only a few methods, but those methods represent unrelated responsibilities.

High cohesion asks whether the behavior belongs together conceptually.

A `PaymentGateway` with several payment-related operations can be highly cohesive even if it contains substantially more code than a tiny utility class.

## Loose coupling

Loose coupling reduces the amount of implementation knowledge shared between components.

The Python application service receives dependencies through its constructor:

`OrderApplicationService(inventory, payments, notifications, orders)`

The service therefore depends on contracts rather than constructing concrete infrastructure internally.

The JavaScript implementation uses the same architectural principle but adds a JavaScript-specific event-driven boundary. The `DomainEventBus` publishes `order.paid` events, while independent consumers react to that event.

The C++ implementation uses abstract base classes such as `Inventory`, `PaymentGateway`, `OrderRepository`, `NotificationGateway`, and `ShippingGateway`.

The application service receives references to those abstractions. Concrete implementations are assembled at the composition boundary.

## The dependency direction

A useful dependency arrangement is:

`Application workflow → abstraction ← infrastructure implementation`

For example:

`OrderApplicationService → PaymentGateway ← SimulatedPaymentGateway`

The application service knows the payment contract.

The concrete gateway satisfies that contract.

The application service does not need to know the gateway's internal implementation.

This is different from:

`OrderApplicationService → StripePaymentProvider`

where the application workflow becomes directly dependent on a particular infrastructure technology.

Loose coupling does not mean eliminating dependencies. A useful application must depend on something. The goal is to make dependencies explicit, narrow, replaceable, and stable.

## Python implementation

The Python program begins with `TightlyCoupledOrderService`.

That class intentionally demonstrates an undesirable boundary. It contains inventory management, payment behavior, email behavior, shipping behavior, and persistence formatting in the same operation.

The important lesson is not that a large class is inherently bad. The issue is that unrelated responsibilities and concrete implementation details are concentrated in the same component.

The redesigned Python implementation introduces protocols:

- `InventoryRepository`
- `PaymentGateway`
- `NotificationSender`
- `OrderRepository`
- `ShippingService`

Python's structural typing through `Protocol` is useful here because an implementation does not have to inherit from a particular base class to satisfy the interface.

The application service can therefore accept objects that expose the required behavior.

### Dependency injection

The following architectural relationship is used by the Python implementation:

`OrderApplicationService`

depends on:

`InventoryRepository`

`PaymentGateway`

`NotificationSender`

`OrderRepository`

The concrete implementations are supplied from outside the service.

This is dependency injection. It avoids creating infrastructure inside business orchestration code.

That boundary makes testing easier because a payment gateway can be replaced with `FakePaymentGateway`, and a notification sender can be replaced with a small test implementation.

### Failure compensation

The Python order workflow reserves inventory before charging the payment.

That creates a failure boundary.

If payment fails after inventory has been reserved, the system cannot simply ignore the reservation. The application service records successful reservations and releases them when a later operation fails.

This demonstrates an important distinction between loose coupling and distributed transaction semantics.

Loose coupling does not automatically provide atomicity.

When independent components are involved, the application must explicitly define failure behavior. The example uses compensation to restore inventory after a payment failure.

### Testing as an architectural signal

The Python tests deliberately replace collaborators.

A notification implementation can be substituted with a test object that records messages instead of sending them.

A payment implementation can reject a selected order.

The tests also verify that invalid input is rejected before infrastructure operations occur.

This is useful because testability is not merely a testing concern. Difficulty replacing a dependency can reveal excessive coupling.

## JavaScript implementation

The JavaScript implementation uses a different architectural perspective rather than translating the Python design line by line.

It uses asynchronous collaborators and an event bus.

`PaymentGateway`, `NotificationGateway`, `MemoryOrderRepository`, and `MemoryInventory` expose asynchronous operations. This represents the fact that real JavaScript applications frequently interact with remote services, databases, message brokers, or filesystem APIs asynchronously.

### Event-driven decoupling

After an order is paid, the application publishes:

`order.paid`

The event contains the information needed by consumers:

- order identifier;
- customer email;
- payment amount;
- transaction identifier.

Several independent consumers subscribe:

- `AuditLog`;
- `ShippingCoordinator`;
- notification handling;
- an analytics consumer in the demonstration.

The order application does not need to call each future consumer directly.

This reduces coupling between the producer and consumers.

Adding another consumer does not necessarily require changing the core payment workflow. The new consumer subscribes to the existing event contract.

### Subscription lifetime

The JavaScript event bus returns an unsubscribe function from `subscribe`.

This is an important operational detail.

Long-lived applications can leak resources or retain objects unexpectedly when event listeners are never removed. Explicit subscription lifetime makes the boundary easier to manage.

### Asynchronous failure

The JavaScript application uses `try` and `catch` around asynchronous operations.

Reservations are tracked so that failed payment can trigger compensating inventory releases.

`Promise.all` is used for independent event handlers and compensation operations where concurrent execution is appropriate.

The implementation therefore demonstrates a JavaScript-specific consequence of loose coupling: independent collaborators can execute asynchronously without making the application service responsible for their internal mechanics.

## C++ case study

The C++ implementation models the same architectural problem as a repository fulfillment engine.

Its primary scenario is:

`OrderApplicationService`

coordinates:

`Inventory`

`PaymentGateway`

`OrderRepository`

`NotificationGateway`

`ShippingGateway`

`AuditTrail`

The application service does not own these infrastructure objects. References are supplied to it from the composition boundary.

### Abstract interfaces

The C++ interfaces define stable contracts.

`Inventory` defines reservation, release, and availability behavior.

`PaymentGateway` defines charging behavior.

`OrderRepository` defines persistence behavior.

`NotificationGateway` defines customer notification behavior.

`ShippingGateway` defines shipment creation behavior.

The concrete classes such as `WarehouseInventory` and `SimulatedPaymentGateway` implement those contracts.

This allows the application layer to remain independent of the concrete infrastructure implementation.

### RAII and ownership

The case study uses `std::unique_ptr` at the architecture-composition boundary.

The composition code owns the lifetime of infrastructure objects.

`OrderApplicationService` receives references instead of owning those objects.

This creates a clear distinction between:

- ownership;
- dependency;
- orchestration.

A dependency does not have to imply ownership.

That distinction is particularly important in larger C++ systems because unclear ownership can create lifetime errors, dangling references, double deletion, or unnecessary copies.

### Failure handling

The C++ service tracks inventory reservations.

If payment fails, the catch block releases the reservations in reverse order.

Reverse-order compensation is useful when multiple resources have been reserved and later operations depend on earlier reservations.

The design is not a replacement for a true distributed transaction. It is an explicit compensation strategy appropriate for the simplified case study.

## Responsibility boundaries

A useful way to reason about cohesion is to ask why a component would change.

Examples from the implementations:

| Component | Primary reason to change |
|---|---|
| `OrderValidator` | Order validity rules change |
| `OrderPricing` | Pricing rules change |
| `Inventory` implementation | Inventory storage or reservation mechanism changes |
| `PaymentGateway` implementation | Payment provider behavior changes |
| `OrderRepository` implementation | Persistence mechanism changes |
| `NotificationGateway` implementation | Notification transport changes |
| `ShippingGateway` implementation | Shipping provider or fulfillment mechanism changes |
| `OrderApplicationService` | The business workflow itself changes |

These are not absolute laws. Some changes naturally cross boundaries. The architectural objective is to avoid unrelated changes becoming unnecessarily coupled.

## Coupling types visible in the examples

### Concrete coupling

Concrete coupling occurs when one component directly depends on a particular implementation.

An order service that constructs `StripePaymentProvider` internally is concretely coupled to that provider.

Replacing the provider requires changing the service.

The implementations avoid this by supplying payment collaborators through abstractions.

### Temporal coupling

Temporal coupling occurs when components must execute in a strict sequence because one operation depends on another operation having already occurred.

The fulfillment workflow contains legitimate temporal relationships:

`payment must succeed before shipping`

This dependency should not automatically be interpreted as bad coupling. It represents a real business constraint.

The goal is to isolate the dependency so that shipping does not need to know how payment was processed.

### Data coupling

Data coupling occurs when one component receives only the data it needs.

The `PaymentGateway` receives an order identifier and amount rather than an entire database connection, application configuration object, notification service, and inventory repository.

Narrow data contracts reduce unnecessary knowledge.

### Control coupling

Control coupling occurs when one component tells another component how to perform its internal work, often through flags or mode values.

For example, a generic service with an argument such as `processOrder(order, "paymentThenEmailThenShip")` can become difficult to understand because the caller controls internal behavior.

A clearer design usually exposes meaningful operations or events with explicit contracts.

## Cohesion and coupling interact

High cohesion and loose coupling reinforce each other.

Suppose payment behavior, email formatting, inventory reservation, and persistence all exist in one class.

The class has low cohesion because its responsibilities are unrelated.

It is also likely to have high coupling because it must know about several infrastructure systems.

Separating those responsibilities creates focused components. Interfaces then allow the application workflow to depend on those components through narrow contracts.

This creates a useful architectural boundary:

`focused responsibility + narrow dependency contract`

Neither property alone guarantees good architecture.

A class can be highly cohesive but tightly coupled to a concrete database library.

A system can be loosely coupled through many interfaces while still having poorly designed abstractions with unrelated responsibilities.

## Composition root

Dependency injection requires a place where the concrete implementations are assembled.

The Python demonstrations construct the inventory, payment, notification, and repository objects before creating the application service.

The JavaScript `createOrderSystem` function acts as a composition boundary.

The C++ `architecture_boundary_case` explicitly constructs infrastructure objects and passes references into `OrderApplicationService`.

This arrangement keeps infrastructure construction away from business logic.

A useful rule is:

> Business components should use dependencies; a composition boundary should decide which concrete implementations they receive.

This also makes configuration changes more localized.

## Edge cases represented by the implementations

The examples intentionally handle failure conditions rather than assuming every dependency succeeds.

Relevant cases include:

- empty orders;
- invalid customer email;
- non-positive quantities;
- negative prices;
- insufficient inventory;
- payment rejection;
- invalid payment amounts;
- attempting to ship an unpaid order;
- attempting to change an order that is already in an incompatible state;
- replacing infrastructure with test doubles;
- restoring reservations after downstream failure.

These cases are particularly important when assessing coupling because a highly coupled implementation often spreads failure handling across unrelated infrastructure code.

## Common architectural mistakes

### One service owns every responsibility

An `OrderService` that validates input, calculates prices, executes SQL, calls a payment provider, sends email, and calls a shipping API has a broad responsibility boundary.

The problem is not simply class size. The problem is that unrelated reasons for change are concentrated in one component.

### Interfaces created without meaningful boundaries

Adding interfaces everywhere does not automatically produce loose coupling.

An interface such as `IApplicationEverything` with dozens of unrelated methods simply moves the coupling behind another name.

Useful interfaces should represent a meaningful capability.

### Excessive abstraction

Abstraction has a cost.

Introducing five interfaces around a simple calculation that will never have another implementation can make the design harder to understand without providing meaningful flexibility.

The examples use interfaces where there is an actual boundary between application logic and infrastructure.

### Global service access

A global payment service, global database object, or global notification object makes dependencies implicit.

A developer reading the constructor cannot determine what the component actually requires.

Explicit dependency injection makes those relationships visible.

### Passing giant context objects

A component that receives an enormous `ApplicationContext` containing every service is technically using dependency injection, but the coupling has merely been hidden inside the context object.

Narrow interfaces and focused data contracts provide stronger boundaries.

## Performance implications

Loose coupling does not automatically improve runtime performance.

Abstractions can introduce:

- additional indirection;
- virtual dispatch in some C++ designs;
- additional allocations;
- event-dispatch overhead;
- serialization costs when events cross process boundaries.

These costs must be considered against the architectural benefits.

For most business applications, the cost of a clean application boundary is usually much smaller than the cost of remote I/O such as database queries or HTTP requests.

Performance-sensitive systems should measure rather than assume that abstraction is expensive.

The C++ implementation uses virtual interfaces to demonstrate runtime polymorphism. In performance-critical paths, alternatives such as templates, static polymorphism, direct value types, or carefully designed function objects may be appropriate when measurement demonstrates a real bottleneck.

## Security considerations

Loose coupling can improve security boundaries when sensitive infrastructure access is isolated.

For example:

- payment credentials should remain inside the payment adapter;
- database credentials should remain inside persistence infrastructure;
- notification credentials should remain inside the notification adapter;
- business logic should not receive secrets it does not require.

The application service should receive the capability it needs rather than unrestricted infrastructure access.

This follows the principle of least privilege.

Loose coupling does not itself make a system secure. Authentication, authorization, secret management, input validation, transport security, audit controls, and dependency security remain separate concerns.

## Debugging considerations

Highly coupled systems often make failures difficult to localize because one component performs many operations.

A failure such as "order processing failed" could originate from:

- validation;
- inventory;
- payment;
- persistence;
- notification;
- shipping.

Focused components make those boundaries easier to observe.

The examples use explicit errors and event records to preserve information about where failures occurred.

In production systems, structured logging should include identifiers such as order ID, transaction ID, correlation ID, and relevant component name without exposing credentials or sensitive payment information.

## Practical architecture

The implementations demonstrate the following conceptual flow:

`Client`

→ `OrderApplicationService`

→ `OrderValidator`

→ `InventoryRepository`

→ `PaymentGateway`

→ `OrderRepository`

→ `NotificationSender`

and, where appropriate:

`order.paid event`

→ `Audit`

→ `Shipping`

→ `Analytics`

The arrows represent dependencies or communication relationships, not necessarily direct function calls.

The important property is that the application workflow does not need to know the internal details of every infrastructure mechanism.

## When tighter coupling can be reasonable

Loose coupling is not an unconditional requirement.

A small utility with one stable implementation may be clearer when it directly calls the implementation it needs.

A temporary script may not justify an elaborate dependency architecture.

A performance-critical inner loop may benefit from direct calls when abstraction overhead is measured and significant.

A tightly integrated component can also be appropriate when two responsibilities genuinely change together and separating them would create unnecessary complexity.

The objective is not maximum abstraction.

The objective is an appropriate dependency boundary.

## Relationship between the three implementation perspectives

The Python implementation emphasizes explicit protocols, dependency injection, compensation, and executable unit tests.

The JavaScript implementation emphasizes asynchronous boundaries, event-driven communication, subscription management, and replacement of infrastructure services.

The C++ implementation emphasizes abstract interfaces, reference-based dependency injection, ownership boundaries, runtime polymorphism, exception-safe compensation, and a concrete fulfillment-engine case study.

All three represent the same architectural principles from different language-specific perspectives rather than serving as identical translations of one program.

## Architectural decision criteria

When evaluating a component boundary, the most useful questions are:

- Does this component have a focused responsibility?
- Does it depend on implementation details that could reasonably change?
- Can its infrastructure collaborator be replaced without changing business logic?
- Does it require more data or capabilities than it actually needs?
- Do unrelated changes repeatedly force modifications to the same component?
- Are failure and compensation rules explicit?
- Is the abstraction representing a real capability rather than merely adding another layer?
- Can the component be tested without requiring every external system?
- Does the dependency direction keep volatile infrastructure details away from stable business rules?

These questions provide a more useful architectural assessment than measuring class size alone.

## Repository structure

A practical repository arrangement for these artifacts is:

`coupling_cohesion.py`

`coupling_cohesion.js`

`coupling_cohesion.cpp`

`README.md`

The Python file can be executed directly with the standard Python runtime.

The JavaScript file is designed for Node.js and uses no external npm dependency.

The C++ program requires C++17 or later and uses only the standard library.

## Key technical takeaway

High cohesion keeps related behavior together while separating unrelated reasons for change.

Loose coupling keeps components from depending unnecessarily on each other's implementation details.

The strongest relationship between the two is architectural rather than syntactic:

`high cohesion` defines meaningful component boundaries

`loose coupling` defines controlled relationships between those boundaries

A well-designed system therefore does not attempt to eliminate dependencies. It makes necessary dependencies explicit, narrow, stable, testable, and aligned with real business or technical responsibilities.
