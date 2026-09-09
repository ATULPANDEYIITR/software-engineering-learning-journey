# Software Architecture Basics: Architecture vs Design, Components, and Boundaries

## 1. Topic Introduction

Software architecture describes the significant structural decisions that shape a software system. It determines how major responsibilities are divided, where boundaries exist, how components communicate, where data is owned, which dependencies are permitted, and how important quality attributes such as reliability, security, performance, and maintainability are achieved.

Software design operates at a more detailed level. It addresses the organization and implementation of individual components, classes, functions, algorithms, interfaces, and data structures.

The distinction is not absolute. A design decision becomes architectural when changing it has broad consequences for the structure, behavior, deployment, operation, or evolution of the system.

The accompanying Python script develops these ideas progressively. It begins with terminology and fundamental structural concepts, then introduces dependencies, boundaries, layered architecture, dependency inversion, ports and adapters, distributed systems, event-driven communication, security boundaries, architectural testing, and production concerns.

---

## 2. Architecture vs Design

### Architecture

Architecture focuses on decisions that affect the system as a whole.

Examples include:

- Whether an application is a monolith or distributed system
- Whether components communicate synchronously or asynchronously
- Where business logic resides
- Which component owns particular data
- Whether infrastructure dependencies are isolated behind abstractions
- Where security and trust boundaries exist
- How components are deployed
- How failures are isolated
- Which architectural constraints must always be preserved

Architecture is concerned with structural consequences and long-term system evolution.

### Design

Design focuses more closely on the implementation of a component or behavior.

Examples include:

- Choosing a class structure
- Selecting a data structure
- Naming methods
- Choosing an algorithm
- Representing money in integer cents
- Deciding whether to use a dataclass
- Designing an internal validation function

Architecture and design interact continuously. A system architecture establishes constraints within which detailed design takes place.

---

## 3. Core Architectural Vocabulary

### Component

A component is a cohesive unit with a meaningful responsibility.

Depending on the context, a component can be:

- A Python module
- A package
- A business subsystem
- A service
- A database subsystem
- An independently deployable application
- An adapter around an external system

The important characteristics are responsibility, interface, dependencies, and boundary.

The script represents components using the `Component` dataclass.

### Boundary

A boundary separates one responsibility, model, ownership area, technology, or trust level from another.

Important boundary types include:

- Domain boundaries
- Module boundaries
- Data ownership boundaries
- API boundaries
- Security boundaries
- Deployment boundaries
- Service boundaries

A boundary becomes valuable when it prevents unrelated concerns from leaking into each other.

---

## 4. Architectural Quality Attributes

Architecture is not evaluated only by whether the system produces correct output.

Important quality attributes include:

### Maintainability

Maintainability concerns how easily developers can understand, modify, test, and extend the system.

Strong cohesion and controlled coupling generally improve maintainability.

### Scalability

Scalability describes how effectively a system accommodates increased workload.

Two major forms are:

- **Vertical scaling:** increasing resources of existing machines
- **Horizontal scaling:** adding additional instances

Architecture influences whether components can scale independently.

### Reliability

Reliability concerns the ability of a system to perform correctly over time.

Architectural concerns include:

- Failure isolation
- Recovery
- Retry behavior
- Data integrity
- Redundancy
- Dependency failures

### Availability

Availability concerns whether the system is operational when required.

A design with unnecessary single points of failure can reduce availability.

### Performance

Performance includes:

- Response latency
- Throughput
- Resource consumption
- Database access time
- Network overhead
- Computational cost

Architecture influences performance through network boundaries, data locality, communication patterns, caching, and concurrency.

### Security

Security architecture determines where trust boundaries exist and how protected operations are enforced.

Important principles include:

- Least privilege
- Server-side authorization
- Input validation
- Isolation of sensitive operations
- Controlled access to data
- Authentication and authorization at appropriate boundaries

### Testability

Testability is strongly influenced by architecture.

Components that depend directly on databases, network providers, and framework internals are generally harder to test in isolation.

Dependency injection and ports can make testing substantially easier.

---

## 5. Cohesion and Coupling

### Cohesion

Cohesion measures how closely related the responsibilities within a component are.

A highly cohesive component focuses on a relatively narrow and meaningful responsibility.

For example, an inventory component responsible for stock reservation and inventory invariants is more cohesive than a `SystemManager` that handles inventory, payments, emails, authentication, and reporting.

### Coupling

Coupling describes dependencies between components.

High coupling means changes in one component are more likely to require changes elsewhere.

Good architecture generally seeks:

**High cohesion + controlled coupling**

Neither zero coupling nor zero dependency is realistic. Components need to collaborate. The architectural objective is to make those relationships intentional and manageable.

---

## 6. Dependency Graphs

A dependency can be represented as:

`A -> B`

This means component A depends on component B.

Dependency graphs are useful for identifying:

- Excessive coupling
- Circular dependencies
- Unexpected dependencies
- Architectural layering violations
- Dependency direction

The Python script implements a small directed dependency graph and provides cycle detection.

Circular dependencies are especially problematic because components become mutually constrained.

---

## 7. Layered Architecture

Layered architecture organizes software into conceptual levels.

A simplified structure might be:

1. Presentation
2. Application
3. Domain
4. Infrastructure

The presentation layer deals with external interaction.

The application layer coordinates use cases.

The domain layer contains business rules.

The infrastructure layer provides technology-specific mechanisms such as databases and external integrations.

A layered architecture can be simple and effective, particularly for applications whose responsibilities map naturally to layers.

A potential weakness is that a poorly implemented layered system can become tightly coupled. For example, business rules may begin depending directly on database frameworks or HTTP concerns.

---

## 8. Domain Responsibilities

The domain represents business concepts and rules.

The script introduces `OrderDomain`, which validates:

- Required identifiers
- Non-empty order lines
- Positive quantities
- Non-negative prices
- Valid state transitions

The domain does not need to know:

- Which database stores the order
- Which payment provider is used
- Which web framework receives the request
- Which message broker publishes an event

This separation protects business policy from infrastructure details.

---

## 9. Components and Responsibilities

A useful component should have a clear answer to:

> What responsibility does this component own?

Examples from the script include:

- `OrderDomain`: business invariants
- `OrderApplicationService`: application use-case coordination
- `InMemoryOrderRepository`: persistence implementation
- `FakePaymentGateway`: test payment implementation
- `PaymentProviderAdapter`: external provider integration
- `InventoryService`: inventory ownership and reservation rules
- `EventBus`: event dispatch

The goal is not to maximize the number of components. Excessive fragmentation can make a system harder to understand.

---

## 10. Dependency Direction

Dependency direction is one of the most important architectural concerns.

A poorly structured system might have:

`Domain -> Database`

This makes business rules aware of infrastructure.

A more isolated structure can use:

`Application -> Repository Port <- Infrastructure`

The application depends on an abstraction describing what it needs. Infrastructure implements that abstraction.

This is a practical expression of dependency inversion.

---

## 11. Dependency Inversion

Dependency inversion means high-level policy should not be forced to depend directly on low-level implementation details.

The Python script demonstrates this using protocols:

- `OrderRepositoryPort`
- `PaymentPort`
- `NotificationPort`
- `OrderEventPublisher`

The application service receives implementations of these interfaces instead of constructing infrastructure itself.

This provides several benefits:

- Easier unit testing
- Reduced vendor coupling
- Clearer responsibilities
- Easier substitution
- Better separation between policy and mechanism

Dependency inversion should not be confused with creating an interface for every class. Abstraction is useful when it protects a meaningful boundary or variation point.

---

## 12. Ports and Adapters

Ports and adapters architecture isolates application policy from external technologies.

The central concept is:

**Port:** an interface describing a capability required or provided by the application.

**Adapter:** an implementation that connects that interface to a particular technology or external system.

For example:

`Application -> PaymentPort <- PaymentProviderAdapter`

The application understands payment as a capability.

The adapter understands the provider's API.

This prevents provider-specific details from spreading through the application.

---

## 13. Anti-Corruption Layers

External systems frequently use different terminology and data models.

An anti-corruption layer translates between the external model and the internal model.

The script demonstrates this using:

- `ExternalPaymentResponse`
- `PaymentResult`
- `translate_external_payment_response()`

The internal application does not need to use provider-specific field names such as `provider_code`.

This technique is particularly useful when integrating:

- Legacy systems
- External vendors
- Acquired systems
- Systems with incompatible domain models

---

## 14. API Boundaries

An API is a boundary between an external caller and an internal system.

Boundary validation should occur close to the boundary.

The script defines:

- `CreateOrderRequest`
- `CreateOrderResponse`
- `validate_create_order_request()`

Boundary validation protects the application from malformed input.

Internal business objects should still enforce their own invariants because boundary validation alone is not sufficient.

A secure architecture should assume that external callers can bypass client-side validation.

---

## 15. Security Boundaries

A security boundary separates operations or resources according to trust and authorization requirements.

The script demonstrates role-based authorization with:

`AuthenticatedUser`

and:

`require_role()`

Important principles include:

- Never treat UI visibility as authorization
- Enforce authorization on the server
- Minimize privileges
- Validate untrusted input
- Protect sensitive operations at the actual boundary
- Avoid trusting data merely because it originated from another component

Security should be an architectural property rather than an afterthought.

---

## 16. Data Ownership

Data ownership defines which component is responsible for maintaining the integrity of particular information.

The inventory example demonstrates a simple ownership rule.

`InventoryService` controls inventory reservations and prevents reservations greater than available quantity.

A component that owns data should normally own the business rules governing changes to that data.

Unrestricted direct modification by unrelated components weakens boundaries.

---

## 17. Transaction Boundaries

Transactions define the scope within which changes are expected to behave atomically.

A local database transaction can often roll back changes together.

Distributed operations are different.

Consider:

1. Reserve inventory
2. Charge payment
3. Update order

If these occur in separate systems, a failure after step 1 may not allow a conventional database rollback.

This creates the need for techniques such as:

- Compensation
- Idempotency
- Workflow coordination
- Saga-style processes
- Retry policies
- Explicit failure states

The script demonstrates a simple compensating transaction with `Reservation`.

---

## 18. Bounded Contexts

A bounded context defines where a particular domain model and vocabulary are valid.

The same real-world entity can have different representations in different contexts.

The script demonstrates this with:

- `SalesCustomer`
- `SupportCustomer`

Both refer to the same customer identity, but each model serves a different business purpose.

A common architectural mistake is attempting to create one universal model for every part of an organization.

---

## 19. Monoliths, Modular Monoliths, and Microservices

### Traditional Monolith

A traditional monolith is usually deployed as one application.

Advantages include:

- Simple deployment
- Simple local communication
- Easier debugging
- Straightforward transactions

A monolith can become problematic when internal boundaries are weak.

### Modular Monolith

A modular monolith remains one deployment while maintaining strong internal boundaries.

It can provide:

- Lower operational complexity
- Strong module ownership
- Easier transactions
- A possible path toward future extraction

The architectural benefit comes from modularity, not merely from the number of deployment units.

### Microservices

Microservices use independently deployable services.

Potential advantages include:

- Independent deployment
- Independent scaling
- Team autonomy
- Stronger service ownership

Costs include:

- Network latency
- Partial failure
- Distributed debugging
- Serialization
- Authentication between services
- Contract management
- Eventual consistency
- More operational infrastructure

Microservices are not inherently superior to modular monoliths.

---

## 20. Distributed System Boundaries

A network boundary introduces properties that do not exist in an ordinary function call.

A remote call can experience:

- Latency
- Timeout
- Connection failure
- Partial response
- Authentication failure
- Serialization failure
- Service overload

Therefore, remote operations should not be treated as ordinary local function calls.

Distributed architecture requires explicit thinking about failure and recovery.

---

## 21. Synchronous Communication

In synchronous communication:

`Request -> Wait -> Response`

The caller waits for the operation to complete.

Advantages include:

- Simple control flow
- Immediate feedback
- Easier reasoning about consistency

Costs can include:

- Higher latency
- Stronger temporal coupling
- Failure propagation

---

## 22. Asynchronous Communication

In asynchronous communication:

`Request -> Accepted -> Process Later`

The caller does not necessarily wait for the final result.

Advantages include:

- Reduced temporal coupling
- Potentially higher throughput
- Independent processing
- Better handling of background work

Costs include:

- Eventual consistency
- Duplicate events
- Ordering problems
- Retry behavior
- More complicated debugging
- More complicated failure handling

The script uses Python's asynchronous facilities to demonstrate concurrent independent I/O-like operations.

Asynchronous execution does not automatically improve CPU-bound workloads.

---

## 23. Event-Driven Architecture

Event-driven systems communicate through events representing facts that have occurred.

Examples include:

- `OrderCreated`
- `OrderPaid`
- `PaymentFailed`
- `InventoryReserved`

The script implements a simple `EventBus`.

Multiple consumers can respond to the same event without the producer needing direct knowledge of every consumer.

This can reduce direct coupling, but event-driven systems introduce new concerns around:

- Event schemas
- Delivery guarantees
- Duplicate processing
- Ordering
- Idempotency
- Retry behavior
- Observability
- Event versioning

---

## 24. Eventual Consistency

With asynchronous communication, different components may temporarily contain different versions of information.

For example:

1. An order becomes `PAID`.
2. An event is published.
3. A notification component has not processed the event yet.
4. The notification state remains temporarily behind the order state.
5. The notification component eventually catches up.

This is eventual consistency.

It is appropriate when immediate consistency is not required by the business process.

It is inappropriate when a business invariant requires an immediate consistent view.

---

## 25. Failure Boundaries

Failure behavior should be designed explicitly.

The script demonstrates retry handling using `ResilientPaymentPort`.

A production retry mechanism should consider:

- Maximum attempts
- Timeouts
- Exponential backoff
- Jitter
- Error classification
- Rate limits
- Overall time budgets
- Idempotency

Blindly retrying every error can make outages worse.

For example, retrying a validation failure is usually pointless, while retrying a temporary network failure may be appropriate.

---

## 26. Idempotency

An operation is idempotent when repeating the same logical operation does not create an unintended additional effect.

Payment systems are an important example.

A network timeout can leave the caller uncertain whether the payment succeeded.

If the caller retries without protection, the same payment could potentially be processed twice.

An idempotency key gives repeated attempts a stable logical identity.

The script demonstrates this with `IdempotentPaymentService`.

Idempotency is particularly important for:

- Payments
- Order creation
- Resource provisioning
- Message processing
- Retried API requests

---

## 27. Backpressure

Backpressure occurs when a producer can generate work faster than a consumer can process it.

Without controls, queues can grow indefinitely and consume memory or overload downstream systems.

The script implements a small bounded queue.

A bounded queue demonstrates an important architectural principle:

> Capacity limits should be explicit.

Production systems may use bounded worker pools, broker limits, rate limits, admission control, or other mechanisms.

---

## 28. Contract Versioning

Distributed components communicate through contracts.

A contract can include:

- API schemas
- Event schemas
- Message formats
- Request structures
- Response structures

When contracts evolve, compatibility becomes important.

The script demonstrates separate `OrderCreatedV1` and `OrderCreatedV2` structures.

Versioning can allow independent evolution, but compatibility policies must be explicit.

---

## 29. Architecture Decision Records

Architectural decisions often have long-term consequences.

An Architecture Decision Record, or ADR, captures information such as:

- Context
- Decision
- Consequences

The script models this with `ArchitectureDecision`.

An ADR is particularly valuable when a decision has meaningful trade-offs and future developers need to understand why a particular architectural direction was chosen.

A useful decision record explains reasoning rather than merely documenting the final choice.

---

## 30. Architecture Fitness Functions

An architecture fitness function is an automated mechanism that verifies an architectural property.

Examples include:

- Domain code must not import infrastructure
- Certain modules must not depend on others
- APIs must satisfy compatibility rules
- A service must not access another service's database directly
- A component must remain below a dependency threshold

The script demonstrates dependency validation with:

`assert_no_forbidden_dependencies()`

Automated architecture checks help prevent gradual architectural erosion.

---

## 31. Testing as an Architectural Concern

Testing is not only about verifying individual functions.

Architecture influences how easily tests can be written.

The script tests:

- Payment failure
- Successful payment
- Persistence behavior
- Invalid quantities
- Invalid prices
- Invalid domain state

Dependency injection makes it possible to substitute a real payment system with `FakePaymentGateway`.

This allows application behavior to be tested without depending on an external payment provider.

---

## 32. Edge Cases and Invariants

Important business invariants should be enforced regardless of where the input originated.

The script rejects:

- Empty customer identifiers
- Empty orders
- Zero quantities
- Negative quantities
- Negative prices
- Invalid state transitions

An invariant is a condition that must remain true for a valid system state.

Examples:

- An order must contain at least one item.
- Quantity must be positive.
- Inventory cannot become negative.
- A paid order cannot transition through an invalid state.
- A payment amount must be positive.

---

## 33. Performance Considerations

Architectural performance is affected by:

- Number of network calls
- Database round trips
- Serialization
- Data movement
- Caching
- Concurrency
- Computation placement
- Contention
- Data locality

A local function call is fundamentally different from a remote service call.

Introducing additional service boundaries can increase latency because each boundary may require:

1. Request construction
2. Serialization
3. Network transmission
4. Remote processing
5. Response transmission
6. Deserialization

Performance-driven architecture should be based on measured requirements rather than assumptions.

---

## 34. Scalability Considerations

A scalable architecture identifies what limits capacity.

Potential bottlenecks include:

- Database writes
- Shared mutable state
- Network bandwidth
- CPU-intensive operations
- Memory
- Lock contention
- External service limits

Stateless components are often easier to scale horizontally because requests do not depend on state stored only inside one application instance.

Scaling one component independently can be valuable when that component has substantially different workload characteristics.

---

## 35. Observability

Production architecture requires visibility into system behavior.

Important observability signals include:

- Logs
- Metrics
- Traces
- Error rates
- Latency
- Throughput
- Resource utilization

The script includes an `OperationTelemetry` structure and an `observe_operation()` function to demonstrate measuring operation duration and success.

Distributed systems require especially careful observability because a single user request can cross multiple services.

---

## 36. Architectural Trade-offs

Architecture is fundamentally about trade-offs.

### Abstraction

Benefits:

- Testability
- Substitution
- Decoupling

Costs:

- More code
- More concepts
- Potentially unnecessary indirection

### Distribution

Benefits:

- Independent deployment
- Independent scaling
- Stronger service boundaries

Costs:

- Network failures
- Operational complexity
- Distributed consistency

### Caching

Benefits:

- Lower latency
- Reduced backend load

Costs:

- Stale data
- Invalidation complexity
- Additional state

### Asynchronous Processing

Benefits:

- Decoupling
- Background processing
- Potential throughput improvements

Costs:

- Eventual consistency
- Retry complexity
- More difficult debugging

### Shared Database

Benefits:

- Simple transactions
- Easy relational queries across data

Costs:

- Strong coupling
- Weak ownership boundaries

### Separate Databases

Benefits:

- Clear ownership
- Greater isolation

Costs:

- Cross-domain queries become harder
- Distributed transactions become more complicated

No architecture style eliminates trade-offs.

---

## 37. Common Architectural Mistakes

### Premature Microservices

Splitting a system into services before independent deployment or scaling is actually required can introduce complexity without providing meaningful benefits.

### Shared Database Coupling

If every module can directly modify every table, logical component boundaries become weak.

### God Component

A single component that owns unrelated responsibilities becomes a change hotspot and creates excessive coupling.

### Circular Dependencies

Circular dependencies make independent evolution difficult.

### Leaky Abstractions

An abstraction fails when consumers must understand its underlying implementation details.

### Distributed Monolith

A system can contain many services while remaining tightly coupled. If every request requires several services to be available simultaneously, the architecture may behave like a distributed monolith.

### Over-Abstraction

Creating interfaces without a meaningful boundary or variation point can increase complexity without improving architecture.

### Ignoring Failure

Remote dependencies must be assumed to fail.

### Framework-Driven Architecture

Business boundaries should not automatically be dictated by framework structure.

---

## 38. Progressive Architectural Evolution

The script presents three conceptual stages.

### Stage 1: Simple System

A small in-process implementation minimizes complexity.

This is appropriate when requirements are simple and the system is small.

### Stage 2: Modular System

Responsibilities are separated into:

- Domain
- Application
- Infrastructure
- Ports

This improves testability and structural clarity.

### Stage 3: Distributed System

Some capabilities cross network boundaries.

This may enable independent deployment or scaling, but introduces:

- Network failure
- Timeouts
- Serialization
- Authentication
- Distributed consistency
- Contract management
- Observability requirements

The key architectural principle is to increase complexity because requirements justify it, not because a more complex architecture is fashionable.

---

## 39. Compensation in Distributed Workflows

A conventional database rollback can undo changes within a transaction.

A distributed workflow may cross multiple systems that cannot participate in one atomic transaction.

For example:

1. Inventory is reserved.
2. Payment fails.
3. Inventory must be released.

The release is a compensating action.

Compensation is a business-level reversal rather than necessarily a technical database rollback.

Distributed workflows often require explicit state machines and recovery behavior.

---

## 40. Architecture Review Checklist

The script provides a practical review checklist covering:

1. Component responsibilities
2. Boundary clarity
3. Dependency direction
4. Infrastructure isolation
5. Testability
6. Data ownership
7. Failure handling
8. Security boundaries
9. Transaction requirements
10. Communication style
11. Performance
12. Scalability
13. Production observability
14. Reversibility of decisions
15. Automated architectural constraints

These questions can be applied during architecture reviews before implementation and during maintenance when the system evolves.

---

## 41. Important Distinctions

| Concept | Primary Question |
|---|---|
| Architecture | What major structural decisions shape the system? |
| Design | How should a specific part be organized and implemented? |
| Component | What cohesive responsibility does this unit own? |
| Boundary | Where does one responsibility, model, or trust area end? |
| Coupling | How strongly are components dependent on each other? |
| Cohesion | How closely related are responsibilities within a component? |
| Port | What capability does the application require or provide? |
| Adapter | How is a port connected to a specific technology? |
| Monolith | Is the application deployed as one unit? |
| Modular monolith | Is one deployment internally divided into strong modules? |
| Microservice | Is a capability independently deployable and operationally isolated? |
| Event | What fact has occurred? |
| Transaction | What operations must satisfy atomic consistency requirements? |
| Idempotency | What happens when the same logical request is repeated? |
| Bounded context | Where is a particular model and vocabulary valid? |
| ADR | Why was an important architectural decision made? |
| Fitness function | How can an architectural rule be automatically verified? |

---

## 42. Implementation Principles Demonstrated by the Script

The Python implementation applies several architectural principles directly:

- Dataclasses model domain data and value-like structures.
- Protocols represent ports.
- Dependency injection separates policy from infrastructure.
- In-memory repositories support testing.
- Fake payment gateways isolate external dependencies.
- Domain objects enforce business invariants.
- Dependency graphs model structural relationships.
- Runtime checks demonstrate boundary enforcement.
- Events demonstrate asynchronous-style decoupling.
- Idempotency keys demonstrate safe retry semantics.
- Compensation demonstrates distributed failure recovery.
- Versioned structures demonstrate contract evolution.
- Telemetry demonstrates production observability.

The implementations remain intentionally self-contained so that the architectural concepts can be studied without requiring external infrastructure.

---

## 43. Production Considerations

A production architecture must account for concerns beyond the basic examples:

### Reliability

Define:

- Timeouts
- Retry policies
- Recovery behavior
- Failure isolation
- Graceful degradation

### Security

Define:

- Authentication
- Authorization
- Secret management
- Encryption
- Auditability
- Input validation
- Least-privilege access

### Performance

Define:

- Latency objectives
- Throughput requirements
- Capacity limits
- Database behavior
- Network budgets

### Observability

Define:

- Metrics
- Logs
- Traces
- Correlation identifiers
- Alerting conditions

### Operations

Define:

- Deployment strategy
- Rollback behavior
- Configuration management
- Health checks
- Dependency monitoring
- Capacity planning

### Evolution

Define:

- API compatibility
- Event compatibility
- Database migration strategy
- Module ownership
- Deprecation policies

Architecture is successful when these concerns are deliberately addressed within the system's actual constraints.

---

## 44. Central Architectural Principles

The examples in the script demonstrate several recurring principles:

1. Separate responsibilities that change for different reasons.
2. Prefer high cohesion.
3. Control coupling.
4. Make dependency direction intentional.
5. Protect business rules from infrastructure details.
6. Establish clear ownership of important data.
7. Treat remote operations as failure-prone.
8. Make security boundaries explicit.
9. Use abstractions when they protect meaningful boundaries.
10. Test important architectural constraints automatically.
11. Measure quality attributes rather than assuming them.
12. Keep distributed workflows explicit about consistency and failure.
13. Prefer the simplest architecture that satisfies current requirements.
14. Recognize that architectural decisions create trade-offs.
15. Design for evolution rather than assuming requirements will remain unchanged.
