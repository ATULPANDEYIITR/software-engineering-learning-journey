# Design Patterns I: Factory, Builder, Singleton

## Scope

This module studies three object-creation and object-lifecycle patterns that solve different design problems:

- **Factory** centralizes the decision about which concrete product should be created.
- **Builder** separates the construction of a complex object from the representation of its final form.
- **Singleton** restricts a service to one shared instance within an application process.

The implementations use a deployment and notification domain because it makes the responsibilities of the patterns distinguishable. A system may need to select a deployment executor, construct a deployment request containing many optional settings, and expose one shared audit facility. These are different problems and therefore should not be collapsed into one pattern.

The six deliverables use different technical perspectives. Python emphasizes executable object modeling and validation. JavaScript uses an event-driven service and configuration boundary. C++ develops a deployment-governance case study with explicit ownership and polymorphism. Java models an enterprise service with immutable domain data and explicit domain types. PostgreSQL represents the same type of domain through relational integrity and transactional state transitions.

---

## Factory Pattern

The Factory Pattern is concerned with **object creation when the concrete implementation depends on information available at runtime**.

A client should normally depend on an abstraction rather than repeatedly performing concrete construction itself. If an application supports email, SMS, and push notification transports, code outside the creation boundary should not need to contain separate construction rules for `EmailSender`, `SmsSender`, and `PushSender`.

The important distinction is that a Factory is not primarily responsible for configuring every property of the resulting object. Its core responsibility is selecting and creating the appropriate product.

### Factory structure

The common relationship is:

`Client -> Factory -> Product abstraction -> Concrete product`

In the Python implementation, `NotificationFactory.create()` maps `NotificationChannel` values to concrete sender classes.

In JavaScript, `NotificationTransportFactory.create()` selects `EmailTransport`, `SmsTransport`, or `PushTransport`.

In C++, `DeploymentExecutorFactory` creates a `DeploymentExecutor` implementation based on `DeploymentTarget`. `std::unique_ptr` makes ownership explicit, so the caller owns the executor and does not need to manage raw memory.

In Java, `DeploymentExecutorFactory` maps a `DeploymentTarget` enum to an implementation of the `DeploymentExecutor` interface.

The PostgreSQL implementation takes a relational perspective. `deployment_targets` stores the supported target types and `executor_registrations` stores the registered execution implementation. The database does not instantiate Java or C++ objects. Instead, it provides a persistent registry that an application-level Factory can consume.

### Why the Factory boundary matters

Without a Factory, creation decisions become distributed:

`if target == Kubernetes -> create Kubernetes executor`

`if target == VM -> create VM executor`

`if target == Serverless -> create Serverless executor`

When these decisions appear throughout a codebase, changing construction rules requires finding every caller.

A Factory gives the decision a defined boundary. Client code asks for a product suitable for a target rather than knowing how every product is constructed.

The Factory does not automatically make a system extensible. If every new product requires modifying a large conditional statement, the Factory itself may become a maintenance hotspot. A registry, dependency injection mechanism, or abstract factory can become appropriate as the number of product families grows.

---

## Builder Pattern

The Builder Pattern addresses a different problem: **constructing an object whose configuration contains multiple required and optional properties or whose construction rules are significant**.

A constructor with many parameters can become difficult to understand:

`DeploymentRequest(application, version, owner, target, risk, replicas, rollback, environment, metadata)`

The meaning of positional arguments becomes unclear, and validation can become scattered.

A Builder provides a controlled construction sequence:

`required values -> optional configuration -> validation -> final object`

### Python Builder

`NotificationBuilder` requires the essential notification fields when the builder is created. Optional values such as priority, tags, metadata, and retry count are then configured through explicit methods.

The `build()` operation is the validation boundary. It checks required values, channel-specific recipient rules, and retry limits before producing the final `Notification`.

The final notification is represented as a frozen dataclass. The Builder remains mutable while it is being configured, while the resulting object is intentionally resistant to accidental top-level mutation.

An important property is demonstrated by building one notification and then modifying the Builder. The previously constructed notification retains its original tags. The final object therefore does not depend on later Builder mutation.

### C++ Builder

The C++ `DeploymentRequestBuilder` demonstrates fluent construction using references to the Builder itself. It validates:

- semantic-version formatting
- required application and owner
- replica limits
- the requirement for rollback on critical deployments
- serverless replica restrictions
- environment-variable syntax

The Builder returns a concrete `DeploymentRequest` by value. The resulting object owns its strings, vectors, and maps, avoiding references to temporary Builder state.

### Java Builder

The Java implementation places the Builder inside `DeploymentRequest`. This keeps the construction rules close to the object being constructed.

The final object uses `List.copyOf()` and `Map.copyOf()`. This matters because a validated object should not become invalid simply because external code retains a reference to a mutable collection used during construction.

For example, a caller can add environment variables while configuring the Builder, but once `build()` returns, the resulting request contains immutable snapshots.

### JavaScript Builder

The JavaScript Builder creates a `DeploymentNotification` after validation and freezes the resulting top-level object. It also copies arrays and objects before freezing them.

This distinction matters because `Object.freeze()` only freezes the object on which it is called. A mutable nested array or object would otherwise remain an avenue for accidental mutation.

### Builder versus Factory

The two patterns can work together without being interchangeable.

A Builder answers:

**How should this complex object be assembled and validated?**

A Factory answers:

**Which concrete object should be created for this requested type?**

The combined Python workflow demonstrates this explicitly:

`NotificationBuilder -> Notification -> NotificationFactory -> NotificationSender`

The Builder first creates a valid domain object. The Factory then selects the transport needed to process it.

---

## Singleton Pattern

The Singleton Pattern ensures that a class exposes one shared instance within the intended scope.

The relevant scope in these examples is the **application process**. A Singleton does not automatically mean one object across every server, every container, every machine, or every database connection. Separate processes can have separate Singleton instances.

### Python Singleton

`AuditLogger` uses a class-level instance and a lock. The double-check inside the lock protects creation when multiple threads attempt to initialize the logger simultaneously.

The example also exposes why Singleton design needs discipline. A shared mutable object is global state in practice. It can create hidden dependencies and make tests order-dependent if state is not isolated or cleared.

The example therefore uses the Singleton for a specific process-wide audit responsibility rather than using it for every service in the application.

### JavaScript Singleton

JavaScript's module system frequently provides a simpler Singleton-like boundary because a module is normally evaluated once and its exported objects can be shared by importing code.

The example intentionally demonstrates explicit Singleton behavior through `AuditLog.instance`. Calling `new AuditLog()` repeatedly returns the same object.

This is useful for demonstrating identity, although module-scoped state or dependency injection is often preferable when testability and isolation are more important than explicit Singleton semantics.

### C++ Singleton

The C++ implementation uses a function-local static:

`static AuditService service;`

C++11 and later guarantee thread-safe initialization of function-local static objects. The design also deletes copy and move operations, preventing ordinary copying of the Singleton.

The Singleton contains a mutex because initialization safety and operational thread safety are different concerns. Safe creation does not automatically make subsequent mutation safe.

### Java Singleton

The Java implementation uses the initialization-on-demand holder idiom. The nested `Holder` class is initialized by the JVM only when `instance()` first accesses it.

This provides lazy initialization without manually implementing synchronization or double-checked locking.

The audit event collection is separately synchronized because Singleton identity does not make a mutable collection thread-safe.

### When Singleton is appropriate

A Singleton is most defensible when the application genuinely has one logical process-local resource, such as a process-wide registry or tightly controlled shared facility.

It becomes problematic when it is used simply to avoid passing dependencies. That approach turns ordinary dependencies into hidden global state.

A testable enterprise design will often prefer dependency injection:

`Service(AuditRegistry auditRegistry)`

The Java and C++ implementations use this principle even though the registry itself is Singleton-accessible. The service receives an explicit registry dependency, making the service easier to reason about and test.

---

## How the Three Patterns Work Together

The three patterns can form a coherent object-creation pipeline without having the same responsibility.

A deployment platform can follow this flow:

`Builder -> validated DeploymentRequest`

`Factory -> concrete DeploymentExecutor`

`Singleton -> shared AuditRegistry`

The Builder creates the domain object.

The Factory selects an execution implementation.

The Singleton supplies a process-wide audit facility.

This separation prevents an object responsible for one concern from becoming responsible for all three.

A common design mistake is to create a large Singleton that contains configuration, object construction, business rules, logging, database access, and networking. Such a class becomes difficult to test and changes for unrelated reasons.

The examples deliberately avoid that structure.

---

## Python Implementation

The Python script models a notification system.

`NotificationChannel` identifies the requested transport. `EmailSender`, `SmsSender`, and `PushSender` are concrete products. `NotificationFactory` owns the construction decision.

`NotificationBuilder` handles the more complex configuration of a `Notification`. It validates channel-specific recipient formats, retry limits, required fields, tags, and metadata.

`AuditLogger` demonstrates a thread-aware Singleton. `NotificationService` composes the patterns instead of inheriting from them.

The script also introduces a JSON configuration boundary. External JSON is parsed, required fields are checked, enum values are validated, and the Builder becomes the domain validation boundary. This prevents malformed configuration from entering the notification workflow unchecked.

The final invariant tests verify three important properties:

- Factory calls return the correct concrete products.
- Builder mutation after `build()` does not modify an already constructed notification.
- Repeated Singleton access returns the same object.

---

## JavaScript Implementation

The JavaScript program uses a deployment-notification system with Node.js APIs.

The Factory selects email, SMS, or push transports.

The Builder constructs a notification containing priority, tags, metadata, and retry policy.

The Singleton supplies an audit log shared by the application.

The JavaScript-specific perspective comes from the event-driven layer. `DeploymentEventBus` registers listeners and emits `notification.sent` and `notification.failed` events. The notification service records those events through the shared audit facility.

The configuration example uses asynchronous filesystem APIs to read JSON configuration. The Builder remains the boundary that converts external values into a validated domain object.

The program also uses `crypto.randomUUID()` for delivery identifiers, which makes each simulated delivery distinguishable without introducing an external dependency.

---

## C++ Case Study

The C++ program models a deployment platform.

A `DeploymentRequest` contains application identity, version, ownership, target infrastructure, risk level, replica count, rollback configuration, environment variables, and metadata.

The Builder validates the aggregate before creating it.

The Factory creates one of three executor implementations:

- `KubernetesExecutor` produces a Kubernetes-style rollout command.
- `VirtualMachineExecutor` produces a VM deployment command.
- `ServerlessExecutor` produces a serverless publication command.

The executors share the `DeploymentExecutor` interface, allowing the governance engine to work with polymorphic objects without knowing their concrete implementation.

The Singleton is represented by `AuditService`. It uses C++'s function-local static initialization guarantee and a mutex for concurrent access to its event collection.

`DeploymentEngine` demonstrates the relationship between the patterns. It validates policy, requests an executor from the Factory, executes the deployment, and records state transitions in the shared audit service.

The case study also demonstrates a failure condition: critical deployments must have rollback enabled. The Builder rejects such an invalid configuration before it becomes a deployment request.

---

## Java Implementation

The Java program models the same general domain from an enterprise-oriented perspective.

`DeploymentRequest` contains immutable deployment configuration. Its nested Builder makes the construction process explicit and keeps validation close to the domain object.

The Factory maps deployment targets to executor implementations through an `EnumMap`. This avoids repeatedly constructing equivalent stateless executors and makes the supported product family explicit.

The Singleton is `AuditRegistry`. The initialization-on-demand holder idiom provides lazy, thread-safe initialization. The registry stores immutable `AuditEvent` records and exposes snapshots rather than its mutable internal collection.

`DeploymentGovernanceService` is intentionally not a Singleton. It receives an `AuditRegistry` dependency through its constructor. This illustrates an important distinction: using a Singleton for one infrastructure responsibility does not require every service to become a Singleton.

The Java program also models deployment state explicitly through `DeploymentState`, making successful and failed transitions easier to reason about than unstructured status strings.

---

## SQL Data Model

The PostgreSQL script represents the domain relationally.

`repositories` identifies owning applications and teams.

`deployment_targets` defines the target categories supported by the platform.

`executor_registrations` acts as a persistent registry that can support an application-level Factory.

`deployment_requests` stores the final deployment aggregate.

`deployment_environment` and `deployment_metadata` normalize repeatable configuration instead of storing arbitrary comma-separated values.

`audit_events` records the deployment lifecycle.

The database uses primary keys and foreign keys to maintain entity relationships. Unique constraints prevent duplicate registry entries. Check constraints enforce domain rules such as valid risk levels, semantic version syntax, replica limits, deployment states, and the requirement that critical deployments have rollback enabled.

The `deployment_validation` view evaluates whether a deployment can proceed using the current target, executor, risk, state, and replica rules.

The state transition examples use transactions and `SELECT ... FOR UPDATE`. The row lock is important when multiple workers could otherwise attempt to process the same deployment concurrently.

The SQL script deliberately does not pretend that SQL creates Java or C++ objects. The relational database provides persistent state, integrity, registry information, and transactional coordination. The application layer remains responsible for constructing runtime objects through Factory and Builder implementations.

---

## Pattern Distinctions

| Pattern | Primary question | Main responsibility | Typical result |
|---|---|---|---|
| Factory | Which concrete product should I create? | Encapsulates product selection and construction | Concrete implementation behind an abstraction |
| Builder | How should I assemble this complex object? | Controls configuration and final validation | Fully configured domain object |
| Singleton | How should one process-wide instance be shared? | Controls instance identity and access | One shared instance within a defined scope |

The patterns solve different axes of design.

Factory addresses **selection**.

Builder addresses **construction complexity**.

Singleton addresses **instance multiplicity and shared access**.

A Factory can return an object built by a Builder. A Singleton can contain a registry used by a Factory. A Builder can receive a Singleton-backed service as a dependency. None of those combinations changes the fundamental responsibility of the patterns.

---

## Validation and Failure Boundaries

Validation should occur as close as practical to the boundary where invalid state would otherwise enter the system.

The Builders validate object construction rules such as:

- required values
- valid enumerations
- recipient or version formats
- allowed ranges
- combinations of properties that are not logically compatible

Factories validate whether a requested product type is supported.

Services validate business policies that depend on the broader workflow.

The SQL schema enforces rules that belong at the database integrity layer.

This layered approach is important because application validation alone cannot protect a database from every independent writer, migration, script, or operational process.

---

## Common Design Errors

### Using Factory as a generic utility class

A Factory should have a meaningful creation responsibility. Turning every constructor call into a Factory call adds indirection without improving design.

### Using Builder for a trivial object

A Builder is valuable when configuration is complex, optional, conditional, or validation-heavy. A simple object with two obvious required properties usually does not need one.

### Treating Singleton as dependency injection

A Singleton gives global access to one instance. Dependency injection makes dependencies explicit.

Global access can hide coupling. Explicit dependencies generally make testing and architectural reasoning easier.

### Combining all three patterns into one class

A class that constructs every object, stores every global service, and controls all configuration is difficult to maintain.

The patterns should remain separate even when the application uses them in the same workflow.

### Ignoring concurrency

Singleton identity does not imply thread safety.

A thread-safe initialization mechanism prevents two threads from creating two instances, but mutable data inside the instance may still require synchronization.

The C++ and Python examples make this distinction explicit.

### Forgetting object ownership

C++ makes ownership particularly important. The Factory returns `std::unique_ptr`, which gives a clear ownership model and prevents the raw-pointer lifetime problems common in older Factory implementations.

---

## Performance Considerations

A Factory generally adds negligible computational overhead compared with the work performed by the created object. The main performance concern is usually not the Factory itself but expensive construction or unnecessary repeated creation.

A Builder usually has little performance significance relative to the clarity it provides. The main concern is excessive copying of large configuration structures. The C++ implementation transfers ownership of constructed vectors and maps where appropriate.

Singleton access is normally cheap, but contention can occur when a shared Singleton contains heavily synchronized mutable state. A Singleton should therefore not become a high-contention global lock.

The SQL model uses indexes on repository, target, state, and audit-history access paths because those columns participate in common operational queries. Indexes are not free: they consume storage and add write overhead, so they should correspond to actual access patterns.

---

## Security Considerations

Design patterns do not automatically make an application secure.

The examples validate externally supplied values before they enter domain objects, but production systems need stronger controls for secrets, authorization, audit integrity, and external infrastructure credentials.

Environment variables and metadata can contain sensitive information. A production deployment platform should distinguish ordinary configuration from credentials and should avoid writing secret values directly into general audit logs.

A Factory that selects infrastructure executors should also operate behind authorization checks. Preventing an invalid target value is different from determining whether the caller is allowed to deploy to that target.

A Singleton audit service also does not automatically provide tamper-resistant auditing. If audit records have regulatory or forensic significance, durable storage, access controls, integrity protection, and retention policies must be designed separately.

---

## Testing Considerations

Factory tests should verify that each supported input selects the correct concrete product and that unsupported values fail predictably.

Builder tests should concentrate on valid combinations and invalid combinations. Boundary tests are particularly important for numeric ranges, required values, enum values, and mutually dependent properties.

Singleton tests should verify identity when Singleton behavior is actually required. They should also verify that shared state does not leak between tests.

The C++ and Python programs include direct invariant checks. The Java implementation checks Factory identity, Builder output, and Singleton identity. The JavaScript program tests both object construction and event-driven delivery behavior.

A larger production system would usually prefer dependency injection around services so tests can provide isolated fake or in-memory implementations instead of relying heavily on global Singleton state.

---

## Production Design Implications

These patterns are most useful when they make a real architectural boundary visible.

A Factory is valuable when the application must support multiple concrete implementations behind one abstraction.

A Builder is valuable when object construction has meaningful configuration complexity or validation rules.

A Singleton is valuable only when one process-local instance is itself a legitimate domain or infrastructure requirement.

The strongest design is not the one containing the most patterns. It is the one where each pattern reduces a specific form of coupling or construction complexity without introducing unnecessary global state or indirection.
