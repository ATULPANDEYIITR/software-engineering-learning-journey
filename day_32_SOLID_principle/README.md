# SOLID Principles: SRP, OCP, LSP, ISP, DIP

## Purpose

This repository presents the five SOLID object-oriented design principles through a single technical domain: an order-processing platform.

The five principles address different design pressures:

| Principle | Core concern | Question it answers |
|---|---|---|
| **SRP** | Responsibility and cohesion | Does this component have one coherent reason to change? |
| **OCP** | Extensibility | Can new behavior be added without repeatedly modifying stable business logic? |
| **LSP** | Substitutability | Can an implementation replace its abstraction without violating its behavioral contract? |
| **ISP** | Interface size | Are clients forced to depend on operations they do not need? |
| **DIP** | Dependency direction | Does high-level business policy depend on abstractions rather than infrastructure details? |

SOLID is not a collection of five unrelated rules. The principles address different failure modes that often appear together in evolving object-oriented systems.

The implementations deliberately use the same broad business domain while solving different design problems. This makes the boundaries between the principles visible instead of presenting five disconnected syntax examples.

---

## Domain Used by the Implementations

The examples model an order-processing system containing:

- products and order lines
- order totals, tax, and discounts
- payment methods
- inventory reservation
- persistence
- customer notifications
- reporting
- audit events
- configurable discount policies

The domain is useful for SOLID analysis because it naturally contains several independent reasons for change.

Pricing rules may change without changing persistence. A new discount campaign may be introduced without rewriting checkout. A payment provider may support charging but not refunds. A reporting client may need read access without write access. A production checkout workflow may need to work with different payment, inventory, and notification implementations.

These differences provide concrete boundaries for the five principles.

---

## SRP: Single Responsibility Principle

SRP concerns **responsibility and reasons for change**, not simply class size.

A class containing ten short methods can still violate SRP if those methods belong to unrelated responsibilities. Conversely, a class can contain several closely related operations and still have one coherent responsibility.

### The problem demonstrated

The Python file first defines `MonolithicOrderService` as an intentionally poor design. Its `create_order()` method calculates an order total, serializes the order, writes a file, and sends a notification.

Those operations have different reasons to change:

- tax or pricing rules can change because the business changes its pricing policy
- JSON persistence can change because storage requirements change
- notification behavior can change because the messaging provider changes

Putting them together makes unrelated changes affect the same class.

### The separated design

The Python implementation divides those responsibilities among:

- `OrderCalculator`
- `JsonOrderRepository`
- `NotificationService`
- `SROrderApplicationService`

`SROrderApplicationService` still coordinates the workflow. Coordination itself is a responsibility of an application service and does not require it to own the implementation details of calculation, persistence, or notification.

The C++ implementation expresses the same architectural boundary using abstract classes and references. `PriceCalculator`, `OrderRepository`, and `NotificationService` each own a distinct concern.

The JavaScript implementation uses separate classes for calculation, repository behavior, and notification. Since JavaScript does not require classes for object-oriented design, the important distinction is behavioral ownership rather than the syntax used to express it.

### A useful SRP test

When considering a class, ask:

> "Which business or technical changes would require this class to change?"

If unrelated answers appear, the class may contain multiple responsibilities.

SRP does not mean that every method needs its own class. Excessive fragmentation can produce the opposite problem: many tiny objects with no meaningful cohesion.

---

## OCP: Open/Closed Principle

The Open/Closed Principle describes software that is:

- **open for extension**
- **closed for modification**

The goal is not to prohibit all changes to existing source files. Stable policy should not require repeated modification every time a new variation of a known behavior is introduced.

### Discount rules as an extension point

Discount calculation is a natural OCP example.

A naive implementation might contain a conditional structure such as:

- if customer is gold, apply one rate
- if customer is silver, apply another rate
- if quantity exceeds a threshold, apply another rule
- if a campaign is active, apply another rule

Every new pricing policy would then require modification of the central checkout calculation.

The implementations instead define a discount abstraction.

Python uses the `DiscountPolicy` protocol.

JavaScript uses objects that expose `calculateDiscount()`.

C++ uses the abstract `DiscountStrategy` class.

The pricing engine calls the abstraction without knowing which concrete rule is being used.

### Concrete extensions

The examples include different strategies such as:

- no discount
- percentage discount
- bulk quantity discount
- customer-tier discount

The important behavior is that `DiscountEngine`, `CheckoutPricing`, and `PricingEngine` do not need separate conditional branches for each strategy.

A new discount class can implement the existing contract.

This is meaningful OCP because the variation is isolated behind a stable extension point.

### OCP and abstraction quality

OCP does not mean that every possible variation must have an interface.

Creating abstractions before there is a real axis of variation can produce unnecessary complexity.

A useful abstraction generally appears where:

- behavior is expected to vary
- multiple implementations already exist
- different implementations are independently testable
- the high-level workflow should remain stable while the policy changes

---

## LSP: Liskov Substitution Principle

LSP concerns **behavioral substitutability**.

If code expects an object satisfying an abstraction, a valid subtype must preserve the expectations established by that abstraction.

This is stronger than matching method names or method signatures.

A subtype can compile successfully and still violate LSP if it changes the meaning of the contract.

### Payment example

The payment case study distinguishes two contracts.

`PaymentMethod` promises:

`charge(amount)`

A stronger capability is represented by:

`RefundablePaymentMethod`

which adds:

`refund(transaction_id, amount)`

A card implementation supports both operations.

A gift-card implementation supports charging but is not modeled as refundable through the same interface.

This is important because treating every payment method as refundable would create a false abstraction.

### Why this is an LSP issue

Suppose a base `PaymentMethod` required `refund()`.

A gift-card implementation might then be forced to:

- throw an exception for every refund
- silently ignore the request
- return an invalid result
- invent behavior that the payment system does not actually support

The subtype would technically implement the method but would not preserve the behavioral expectations of callers.

The better design places the refund guarantee in the stronger abstraction.

### Preconditions and postconditions

LSP can be analyzed using behavioral contracts.

A subtype should not arbitrarily strengthen preconditions.

For example, if a base payment abstraction accepts all positive charges, a subtype should not unexpectedly reject ordinary positive charges merely because it has a narrower internal implementation.

Likewise, a subtype should preserve postconditions expected by callers.

A successful `charge()` should produce a valid transaction identifier if that is the abstraction's contract.

### Inheritance is not automatically polymorphism

The fact that one class derives from another does not prove LSP compliance.

A good inheritance relationship represents an actual behavioral subtype relationship.

When the relationship is only code reuse, composition is often more appropriate.

---

## ISP: Interface Segregation Principle

ISP states that clients should not be forced to depend on methods they do not use.

This principle becomes important when an interface grows around one large service.

### The large-interface problem

Imagine an order repository with methods for:

- reading orders
- writing orders
- deleting orders
- auditing
- generating reports
- exporting data
- administering indexes

A reporting component that only needs to read an order would still be coupled to the entire interface.

That creates unnecessary dependency.

### Capability-specific contracts

The C++ implementation separates the repository capabilities into:

- `OrderReader`
- `OrderWriter`
- `OrderAuditor`

`ReportingService` receives only `OrderReader`.

`PersistenceService` receives `OrderWriter` and `OrderAuditor`.

The underlying `ModularOrderStore` implements all three because it happens to provide all those capabilities.

The important point is that the consumers do not depend on the complete implementation surface.

### Python representation

Python uses protocols:

- `OrderReader`
- `OrderWriter`
- `OrderAuditor`

The reporting service declares only the capability it requires.

This is particularly natural in Python because structural typing allows an object to satisfy a protocol by providing the required behavior.

### JavaScript representation

JavaScript has no built-in interface declaration comparable to a C++ abstract class.

The implementation therefore validates the required methods at construction boundaries.

`ReportingClient` requires `readOrder()`.

`PersistenceClient` requires `saveOrder()` and `recordEvent()`.

This produces capability-oriented dependencies without introducing an artificial interface hierarchy.

### ISP and security boundaries

ISP can also reduce accidental authority.

A component that receives only a read capability is less able to mutate state through that dependency.

This is not a complete security mechanism because the underlying object may expose other references elsewhere, but narrow interfaces can support least-authority architectural boundaries.

---

## DIP: Dependency Inversion Principle

DIP addresses the relationship between **high-level policy** and **low-level implementation details**.

The high-level part of a system contains business rules such as:

> Reserve the required products, charge the customer, mark the order as paid, and notify the customer.

The low-level parts may include:

- a payment provider
- a warehouse system
- a database
- an email service
- a message broker

DIP argues that the high-level policy should not be tightly coupled to those concrete infrastructure details.

### Direct dependency problem

A tightly coupled checkout service might construct:

`StripePaymentClient`

`PostgresOrderRepository`

`SmtpMailer`

and

`WarehouseApi`

directly inside its constructor.

Changing one infrastructure provider would then require modifying the high-level checkout code.

Testing would also become difficult because the business workflow would require real infrastructure or complicated global mocking.

### Dependency inversion in the examples

The checkout applications receive abstractions for:

- inventory
- payment
- notification
- pricing

The high-level checkout policy does not construct those implementations.

Python uses protocols.

JavaScript uses behavioral contracts checked at construction time.

C++ uses abstract base classes and dependency injection through references.

### Dependency injection versus dependency inversion

The two ideas are related but not identical.

**Dependency injection** is a technique for supplying dependencies from outside.

**Dependency inversion** is the architectural principle that high-level policy should depend on stable abstractions rather than concrete low-level details.

Constructor injection is one practical way to implement DIP.

---

## How the Five Principles Relate

The principles should not be treated as interchangeable.

A useful relationship in the case study is:

**SRP** establishes cohesive components.

Those components often expose stable behavioral boundaries.

**OCP** allows variations behind those boundaries without modifying the stable workflow.

**LSP** ensures implementations behind an abstraction actually honor its behavioral contract.

**ISP** keeps the abstractions focused so clients do not depend on unnecessary capabilities.

**DIP** makes high-level policy depend on those abstractions rather than directly on infrastructure.

The principles therefore operate at different design levels.

| Design problem | Relevant principle |
|---|---|
| One service calculates prices, stores records, and sends messages | SRP |
| Every new discount requires editing checkout logic | OCP |
| A subtype cannot honor the promises of its base abstraction | LSP |
| A read-only client depends on write and administrative methods | ISP |
| Business logic constructs concrete infrastructure services | DIP |

A design can satisfy one principle while violating another.

For example, a class can have a single responsibility but still depend directly on a concrete database implementation. That may satisfy an SRP analysis while creating a DIP problem.

---

## Python Implementation

The Python program is a complete executable case study.

It begins with the domain model:

- `Product`
- `OrderLine`
- `Order`

The model contains validation for identifiers, email-like values, quantities, and monetary values.

### Python SRP implementation

`OrderCalculator` owns calculation.

`JsonOrderRepository` owns JSON persistence.

`NotificationService` owns customer notification.

`SROrderApplicationService` coordinates those capabilities.

The repository is exercised against a temporary filesystem location so the persistence behavior is executable rather than merely described.

### Python OCP implementation

`DiscountPolicy` is represented as a protocol.

The checkout calculation accepts policies such as:

- `NoDiscount`
- `PercentageDiscount`
- `BulkQuantityDiscount`
- `CustomerTierDiscount`

The final customer-tier implementation demonstrates extension of the policy set without modifying `DiscountEngine`.

### Python LSP implementation

The payment hierarchy separates:

- `PaymentMethod`
- `RefundablePaymentMethod`

`CardPayment` supports both charging and refunds.

`GiftCardPayment` supports charging but does not claim the refundable contract.

The `process_payment()` function therefore accepts the weaker capability while `refund_payment()` explicitly requires the stronger capability.

### Python ISP implementation

The code defines:

- `OrderReader`
- `OrderWriter`
- `OrderAuditor`

`OrderReportingService` depends only on `OrderReader`.

This makes the client's dependency surface smaller than the concrete storage implementation.

### Python DIP implementation

`CheckoutService` receives:

- `InventoryGateway`
- `PaymentGateway`
- `NotificationGateway`
- `OrderCalculator`

The high-level workflow is therefore testable with in-memory infrastructure.

The program also demonstrates a practical limitation: external operations such as inventory reservation and payment cannot necessarily be rolled back by simply catching a Python exception. Real systems need transaction coordination, compensation, idempotency, or workflow orchestration when multiple external systems are involved.

### Python verification

The `unittest` suite checks:

- pricing calculations
- discount extension
- payment substitution
- reporting through a narrow interface
- injected dependencies
- invalid quantities
- invalid discounts

The test suite makes the design contracts executable.

---

## JavaScript Implementation

The JavaScript program takes a complementary approach based on JavaScript's runtime object model.

It does not attempt to reproduce the Python class hierarchy line by line.

### JavaScript SRP

`PriceCalculator`, `MemoryOrderRepository`, and `ConsoleNotifier` own different concerns.

`SRPOrderService` coordinates them.

This demonstrates that SRP is about responsibility boundaries rather than a particular language feature.

### JavaScript OCP

Discount policies implement a behavioral contract through `calculateDiscount()`.

The implementation contains:

- `NoDiscountPolicy`
- `PercentageDiscountPolicy`
- `QuantityDiscountPolicy`
- `CustomerTierPolicy`

`CheckoutPricing` accepts any object satisfying that behavior.

This uses JavaScript's structural nature rather than requiring a formal interface declaration.

### JavaScript LSP

`CardPayment` and `GiftCardPayment` both support `charge()`.

Only `CardPayment` supports `refund()`.

The functions `chargePayment()` and `refundPayment()` therefore require different capability levels.

This avoids pretending that every payment implementation supports every operation.

### JavaScript ISP

`ReportingClient` requires only `readOrder()`.

`PersistenceClient` requires writing and auditing capabilities.

The underlying `OrderStore` can provide all capabilities, but individual consumers do not need to depend on all of them.

### JavaScript DIP

`CheckoutApplication` receives its infrastructure through its constructor.

The workflow is therefore independent of the concrete memory inventory, fake payment gateway, and console notification gateway.

The implementation also uses `async` notification delivery to show how dependency boundaries interact with asynchronous JavaScript workflows.

### Event-driven composition

The JavaScript program includes an `EventBus`, an `OrderAuditSubscriber`, and an `OrderPaid` event.

This demonstrates how SOLID boundaries can remain useful in event-driven systems.

The event publisher does not need to know how auditing is implemented. The subscriber owns the response to the event.

---

## C++ Case Study

The C++ program models a more explicit architecture using abstract base classes, polymorphism, references, and capability-specific interfaces.

The scenario is an order platform responsible for:

- pricing
- discounts
- payment
- inventory
- persistence
- notifications
- reporting
- auditing
- domain events

### C++ architecture

The high-level dependency flow is conceptually:

`CheckoutApplication`

→ `PricingEngine`

→ `DiscountStrategy`

and:

`CheckoutApplication`

→ `InventoryGateway`

→ `PaymentGateway`

→ `NotificationGateway`

Persistence is separated through:

`OrderWriter`

`OrderReader`

`OrderAuditor`

This prevents the checkout workflow from knowing concrete infrastructure details.

### C++ data structures

The program uses:

- `std::vector` for order lines and event handlers
- `std::unordered_map` for in-memory stock and transaction records
- `std::optional` for potentially absent records
- `std::unique_ptr` for owned polymorphic event handlers
- references for injected dependencies that are owned elsewhere

This ownership model is significant.

`CheckoutApplication` does not own the services passed to it. The caller controls their lifetime, and the application holds references to them.

The event dispatcher owns its handlers through `std::unique_ptr`, which makes ownership explicit.

### C++ OCP design

`DiscountStrategy` is an abstract extension point.

`NoDiscount`, `PercentageDiscount`, `BulkDiscount`, and `TierDiscount` implement it.

`PricingEngine` is unaware of the concrete strategy type.

### C++ LSP design

`PaymentMethod` guarantees charging.

`RefundablePaymentMethod` adds refund behavior.

`CardPayment` implements the stronger contract.

`GiftCardPayment` implements only the charge contract.

This prevents a payment object from claiming capabilities that it cannot honor.

### C++ ISP design

The store implements multiple small interfaces:

`OrderReader`

`OrderWriter`

`OrderAuditor`

A reporting component accepts only `OrderReader`.

A persistence component accepts `OrderWriter` and `OrderAuditor`.

This makes the consumer dependencies explicit at compile time.

### C++ DIP design

`CheckoutApplication` depends on abstract gateways.

The program supplies:

- `MemoryInventory`
- `FakePaymentGateway`
- `ConsoleNotificationGateway`

The same high-level checkout policy could therefore operate with other implementations without changing its core logic.

---

## Validation and Failure Behavior

SOLID design does not eliminate runtime failures.

The implementations explicitly validate several domain conditions.

### Order validation

Invalid quantities are rejected because an order line with zero or negative quantity has no valid business meaning.

### Monetary validation

Negative discounts are rejected.

Discounts greater than the order subtotal are rejected.

Tax rates are constrained to valid ranges in the examples.

### Inventory failure

The inventory implementations reject reservations that exceed available stock.

This prevents checkout from silently creating impossible inventory state.

### Payment failure

The fake payment gateway can deliberately decline a transaction.

The checkout workflow propagates the failure rather than marking the order as successfully paid.

### Contract failure

The payment examples distinguish between a general charge contract and a refundable contract.

An object that does not satisfy the stronger capability should not be passed to an operation requiring that capability.

---

## Why Exceptions Do Not Solve Distributed Consistency

The examples intentionally expose an important production limitation.

A checkout operation can involve:

- inventory reservation
- payment authorization
- persistence
- notification

These operations may belong to different systems.

A local exception can stop the current program flow, but it cannot automatically undo an external side effect.

For example:

1. Inventory reservation succeeds.
2. Payment fails.
3. The process catches the payment exception.

The inventory reservation has already occurred.

A production system may therefore require:

- compensating actions
- idempotency keys
- transactional outbox patterns
- retry policies
- explicit order states
- reconciliation jobs
- workflow orchestration
- durable event processing

The exact solution depends on the consistency requirements of the business operation.

This issue is architectural rather than a direct SOLID rule, but it demonstrates why good dependency boundaries are useful when infrastructure behavior becomes more complex.

---

## Common Design Mistakes

### Treating SRP as "one method per class"

SRP is not a rule requiring every operation to have its own class.

The meaningful question is whether the operations belong to the same cohesive responsibility and change for related reasons.

Excessive fragmentation can make a system harder to understand.

### Using OCP to justify excessive abstraction

Not every `if` statement violates OCP.

A small, stable conditional may be clearer than a hierarchy of strategies.

Abstraction is valuable when the variation is meaningful and likely to evolve independently.

### Confusing inheritance with LSP

Inheritance does not guarantee substitutability.

A subtype that throws unsupported-operation exceptions for normal base-class operations may indicate that the base abstraction is too broad.

### Creating one giant interface

A large interface often forces unrelated consumers to depend on operations they do not need.

ISP encourages capability-oriented contracts.

### Calling every injected dependency "DIP"

Constructor injection alone does not guarantee good dependency inversion.

If the application depends on a concrete infrastructure class through the constructor, the dependency is still concrete.

DIP concerns the direction of dependency between high-level policy and implementation details.

---

## Design Trade-offs

SOLID improves some dimensions of software design while introducing costs.

Abstractions can improve testability and change isolation, but each abstraction also introduces concepts that developers must understand.

Polymorphism can make extension easier, but excessive polymorphism can obscure simple control flow.

Dependency injection reduces hard-coded infrastructure dependencies, but dependency graphs can become difficult to trace if the composition root is poorly organized.

Small interfaces reduce client coupling, but too many narrowly defined interfaces can become unnecessary ceremony.

The practical goal is not maximum abstraction. The goal is a design where the boundaries correspond to real responsibilities, meaningful variation, behavioral contracts, client needs, and architectural dependencies.

---

## Performance Considerations

The examples prioritize design clarity rather than benchmarking.

The computational behavior is straightforward:

- order subtotal calculation is generally `O(n)` in the number of order lines
- bulk discount calculation is `O(n)` over order lines
- in-memory lookup through `std::unordered_map`, Python dictionaries, or JavaScript `Map` is expected to be approximately constant time on average
- iterating over multiple strategy objects adds negligible overhead compared with typical database or network operations

Polymorphic calls and interface indirection have a runtime cost, but in business applications the cost of database access, network calls, serialization, and external services is usually much larger.

Performance-sensitive systems should measure real workloads rather than rejecting abstractions based only on theoretical dispatch overhead.

---

## Testing Strategy

SOLID-oriented design creates useful testing seams.

A calculation component can be tested without a database.

A discount strategy can be tested without checkout infrastructure.

A payment implementation can be tested without inventory.

A reporting component can receive a read-only capability.

A checkout application can use fake inventory, payment, and notification implementations.

The provided tests exploit these boundaries.

This is one practical reason SOLID matters: well-separated dependencies can make the behavior of individual components easier to isolate and verify.

---

## Production Considerations

The examples use in-memory and console infrastructure so they remain self-contained.

A production implementation would need additional concerns such as:

- durable persistence
- transactional boundaries
- authentication and authorization
- payment-provider security
- secrets management
- idempotent payment requests
- concurrency control for inventory
- structured logging
- observability
- retry and timeout policies
- audit retention
- data validation at trust boundaries
- explicit failure and recovery states

Those concerns should still be assigned to cohesive components rather than being accumulated inside a single application service.

The SOLID principles provide boundaries for organizing such infrastructure, but they do not replace security architecture, distributed-systems design, database transaction design, or operational engineering.

---

## Security Implications of the Design

Dependency boundaries can also affect security.

A component that only receives an order-reading capability has less authority than a component that receives a complete mutable repository.

Payment implementations should keep credentials and provider-specific secrets inside infrastructure adapters rather than exposing them to high-level business logic.

Notification adapters should validate recipient data and protect credentials.

Inventory operations should enforce authorization at the service boundary rather than assuming that an injected dependency is automatically trusted.

Interfaces improve separation, but an interface is not itself a security boundary. Authorization, identity verification, secret management, and network controls remain necessary.

---

## Practical Decision Model

When designing a new object-oriented component, the following questions help distinguish the principles without treating them as a checklist:

**SRP:** What coherent responsibility does this component own, and what different changes could force it to change?

**OCP:** Which behavior is expected to vary while the surrounding workflow remains stable?

**LSP:** If another implementation replaces this one, what behavioral promises must remain true?

**ISP:** What is the smallest capability this particular consumer actually requires?

**DIP:** Does high-level policy depend directly on an implementation detail, or can both sides depend on a stable abstraction?

These questions are more useful than mechanically adding interfaces or subclasses.

---

## Implementation Relationship

The three implementations deliberately emphasize different language mechanisms.

| Concern | Python | JavaScript | C++ |
|---|---|---|---|
| SRP | Classes, protocols, composition | Classes and runtime contracts | Classes and abstract services |
| OCP | `Protocol`-based strategies | Behavioral policy objects | Abstract `DiscountStrategy` |
| LSP | Capability-specific ABCs | Runtime capability checks | Explicit inheritance hierarchy |
| ISP | Structural protocols | Small required method sets | Separate abstract interfaces |
| DIP | Constructor injection with protocols | Constructor injection with behavioral contracts | References to abstract base classes |
| Testing | `unittest` | Node `assert` | `assert` and exception checks |
| Persistence example | JSON repository | `Map` store | `unordered_map` store |
| Event composition | Service composition | `EventBus` | Polymorphic event handlers |

The implementations therefore demonstrate the same architectural principles through language-appropriate mechanisms rather than translating one source file mechanically into another language.

---

## Scope of SOLID

SOLID is primarily concerned with object-oriented design and dependency relationships.

It does not by itself prescribe:

- a database architecture
- a microservices architecture
- a particular framework
- a deployment model
- a testing framework
- a programming language
- a specific inheritance hierarchy

A system can be object-oriented without applying SOLID well, and a system can use functional or procedural techniques where SOLID is less directly applicable.

The value of the principles comes from applying them to real sources of change and coupling.

A useful SOLID design is therefore not the one containing the most interfaces. It is the one whose responsibilities, extension points, contracts, capabilities, and dependency directions correspond to the actual structure of the problem.
