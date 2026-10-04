# Interfaces & Abstractions: Contracts and Dependency Boundaries

## Scope

Interfaces and abstractions provide stable boundaries between software components. A contract defines what a component expects and what it promises to provide, while a dependency boundary controls which implementation details are allowed to cross from one part of a system into another.

These ideas are closely related but are not identical.

An **interface** describes an interaction surface. It identifies operations that a consumer may rely on without requiring knowledge of the implementation.

An **abstraction** represents a useful concept while hiding details that are not required by its consumers. An abstraction can be represented by an interface, an abstract class, a protocol, a value object, or another stable domain boundary.

A **contract** defines the rules attached to an interaction. Those rules can cover valid inputs, outputs, state transitions, errors, timing assumptions, authorization, or invariants.

A **dependency boundary** determines where implementation knowledge stops. Application code should not need to know whether a dependency stores data in PostgreSQL, a file, memory, or a remote service when the application only needs the behavior expressed by its contract.

The three implementations in this artifact approach the subject from different angles:

- Python emphasizes abstract base classes, structural protocols, dependency injection, domain contracts, validation, and deterministic testing.
- JavaScript emphasizes runtime contracts, structural interfaces, asynchronous dependencies, event-driven boundaries, and implementation substitution.
- C++ presents a repository governance case study in which abstract interfaces isolate review storage, status-check infrastructure, audit persistence, and merge-policy evaluation.

---

## Interface, abstraction, contract, and dependency boundary

An interface answers:

> What operations can this consumer invoke?

An abstraction answers:

> What essential concept should the consumer understand while implementation details remain hidden?

A contract answers:

> What must be true before, during, and after this interaction?

A dependency boundary answers:

> Which component owns this decision, and which implementation details must remain outside it?

Consider an application service that needs to record an audit event. It does not inherently need to know whether the event is inserted into PostgreSQL or published to a message broker. Its dependency can instead expose a small operation such as `write(event)`.

The application then depends on a behavioral contract rather than on the database client.

This distinction is important because an interface alone does not guarantee good architecture. A badly designed interface can expose infrastructure-specific details and create tight coupling. The quality of the boundary depends on what it chooses to expose and what it deliberately hides.

---

## Contracts as executable boundaries

A useful contract usually specifies several dimensions.

| Contract dimension | Example in this artifact | Why it matters |
|---|---|---|
| Input validity | Repository names cannot contain unsupported characters | Prevents invalid state from entering the domain |
| Required operations | Notification channels expose `send` | Allows implementation substitution |
| Output semantics | Merge evaluation returns an allowed decision and blockers | Keeps policy results explicit |
| Dependency behavior | Review repositories return reviews for the requested Pull Request | Prevents callers from depending on storage details |
| Failure behavior | Missing status checks fail closed | Avoids treating unavailable validation as success |
| State assumptions | Reviews can be tied to a specific commit | Prevents stale decisions from being reused incorrectly |
| Ownership | Application services orchestrate dependencies | Keeps infrastructure outside business decisions |

A contract becomes particularly valuable when it is executable. Runtime validation, automated tests, type constraints, assertions, and explicit error handling turn architectural expectations into observable behavior.

---

## Python implementation

The Python implementation begins with an abstract `NotificationChannel`. The `NotificationChannel` class defines `send()` as the stable capability required by the application. `ConsoleNotification` and `InMemoryNotification` provide different implementations without changing the caller.

This demonstrates substitution at the interface boundary.

The Python implementation then uses `Protocol` for structural contracts. `Clock` does not require an inheritance relationship. Any object providing a compatible `now()` method satisfies the intended dependency. `SystemClock` supplies production behavior, while `FixedClock` makes application behavior deterministic during testing.

The `AuditService` demonstrates dependency inversion. It receives both a clock and an audit sink through its constructor. It does not construct either dependency internally. Consequently, the application logic is independent of the mechanism used to obtain the current time or persist an event.

The repository example introduces another boundary. `RepositoryService` works through `RepositoryRepository` rather than directly through a database library. `InMemoryRepositoryStore` is sufficient to execute the application without a database server.

The Pull Request example separates the domain object from review storage. `MergeEligibility` receives a `ReviewProvider`, evaluates a `PullRequest` against a `MergePolicy`, and returns explicit reasons when the contract is not satisfied.

This separation is deliberate. A Pull Request is domain information. A review provider is an external dependency. Merge eligibility is an application policy. These concepts should not become one class merely because they participate in the same workflow.

The script also demonstrates transport separation through `decision_to_json()`. The domain decision remains a Python object until a separate boundary converts it into JSON.

The tests verify contract behavior rather than infrastructure implementation. In particular, the tests establish that an author's own approval does not satisfy the external approval requirement and that a missing approval prevents a merge decision from being accepted.

---

## JavaScript implementation

JavaScript does not provide the same built-in nominal interface mechanism as Java or C#. The implementation therefore uses explicit runtime contracts and structural expectations.

`assertNotificationChannel()` establishes that a notification dependency must expose a `send()` function. Both `ConsoleNotificationChannel` and `MemoryNotificationChannel` satisfy that shape.

`NotificationService` does not instantiate either concrete implementation. It receives the dependency through its constructor. The same service can therefore operate with a real console-oriented implementation or a memory implementation used for testing.

The JavaScript version adds an event-driven boundary through `DomainEventBus`. Subscribers register handlers for domain events without forcing the publisher to know what those handlers do. The publisher owns the event contract, while consumers decide how to react.

The Pull Request model performs runtime validation when an object is constructed. Invalid numbers, branches, authors, changed-file collections, and status-check values are rejected before the object enters the application workflow.

`Review` defines explicit review states:

- `APPROVED` represents an approval decision.
- `CHANGES_REQUESTED` represents a blocking review decision in the merge policy.
- `COMMENTED` represents discussion without approval.

`MemoryReviewRepository` acts as an infrastructure implementation behind a repository-shaped contract. `MergeEligibilityService` uses its required behavior without depending on the repository's internal `Map`.

The application controller combines the policy evaluator, event bus, and clock through dependency injection. The controller produces a transport-neutral decision object. `serializeDecision()` handles JSON formatting separately.

This separation demonstrates an important JavaScript design principle: structural compatibility is useful, but it should be supported by explicit runtime validation when invalid dependencies would otherwise fail later and in less understandable locations.

---

## C++ case study: repository governance engine

The C++ program models a repository governance system that determines whether a Pull Request is eligible to enter a protected branch.

The scenario has four important boundaries:

- `IReviewRepository` supplies review information.
- `IStatusCheckProvider` supplies validation results for a commit.
- `IAuditSink` receives governance events.
- `MergeEligibilityEngine` owns the application-level merge decision.

The merge engine does not know whether reviews come from an API, SQL database, cache, or test fixture. It only knows the contract expressed by `IReviewRepository`.

Likewise, it does not execute a build system or query a CI platform directly. It requests status through `IStatusCheckProvider`.

`MemoryReviewRepository`, `MemoryStatusCheckProvider`, and `MemoryAuditSink` are infrastructure implementations. They make the complete case study executable without requiring external services.

This is a concrete application of dependency inversion: high-level merge-policy logic depends on abstractions, while infrastructure implements those abstractions.

---

## Review and commit-state contract in the C++ case study

The C++ review repository associates reviews with a commit identifier.

A Pull Request may receive an approval at one point and then receive additional commits. If the application treats every historical approval as permanently valid, the merge decision can be based on code that the reviewer never evaluated.

The case study therefore asks the review repository for reviews associated with the current Pull Request head commit.

This is an architectural contract rather than a storage detail. The merge engine needs current review decisions. The repository implementation determines how those decisions are located.

The example deliberately includes an approval for `commit-old` and a Pull Request whose current head is `commit-current`. The older approval is excluded from the current decision.

The same design could be extended to represent formal approval dismissal, reviewer eligibility, review freshness rules, or organization-specific policy without forcing those concepts into the storage implementation.

---

## Protected-branch boundary

The C++ `BranchGuard` represents a different boundary from Pull Request review evaluation.

The merge engine determines whether a Pull Request satisfies the application's merge conditions.

The branch guard determines whether direct or force pushes are permitted against a protected branch.

These are related but distinct responsibilities.

A Pull Request can satisfy its review and status-check conditions while a repository policy still prohibits direct modification of the protected branch. Conversely, a direct-push rule does not explain whether a Pull Request received enough valid reviews.

The policy therefore contains separate controls for:

- the protected branch name
- required approvals
- required status checks
- linear-history policy
- direct-push permission
- force-push permission

The example fails direct pushes and force pushes to `main` unless an explicit administrator bypass is supplied. The bypass is then written to the audit sink, illustrating why privileged exceptions should be observable rather than silently embedded in authorization logic.

---

## Dependency injection

Dependency injection means that a component receives a dependency instead of constructing the dependency internally.

Without injection, an application service might directly instantiate a database repository:

`this.repository = new PostgresRepository(...)`

That design makes the application aware of a specific infrastructure implementation.

With injection, the service receives something satisfying the required repository contract. The caller decides which implementation to supply.

The benefits are architectural rather than merely testing-related:

- infrastructure can change without rewriting business logic;
- tests can provide deterministic implementations;
- application services express their real dependencies explicitly;
- ownership of construction remains outside the business component;
- dependency graphs become easier to inspect.

Injection should still be used carefully. Injecting dozens of tiny abstractions into a class can produce an artificial architecture. A useful boundary should represent a meaningful capability or ownership boundary.

---

## Designing a useful abstraction

A good abstraction is usually smaller than the implementation behind it.

For example, an application that only needs to store an audit event should not expose every operation of a database client. A contract such as `write(event)` communicates the required capability while keeping SQL, connection pools, transactions, retry policies, and vendor-specific APIs outside the application layer.

An abstraction becomes problematic when it leaks infrastructure concepts into a higher-level component.

A contract such as `savePostgresRow()` is not a domain abstraction if the application does not care that PostgreSQL is being used.

A contract such as `saveRepository(repository)` is more stable because it expresses the application's concept rather than the storage mechanism.

The same principle applies to APIs, queues, file systems, payment processors, cloud services, and authentication providers.

---

## Interface granularity

Interfaces should be narrow enough that consumers depend only on behavior they actually require.

The Python notification example needs `send()`. It does not need to expose connection management, SMTP configuration, retry queues, or provider-specific response objects.

A narrow interface also reduces the number of reasons a consumer must change.

A broad interface can create accidental coupling. If a service depends on a large infrastructure interface containing twenty operations but uses only two, changes to the other eighteen operations can still affect the dependency relationship.

The goal is not to maximize the number of interfaces. The goal is to create meaningful boundaries around responsibilities.

---

## Contracts and failure behavior

A contract should define failure semantics where failure is meaningful.

The examples intentionally reject invalid input instead of allowing malformed data to propagate.

The C++ status-check provider treats missing status information as failure when required checks are mandatory. This is a fail-closed design: absence of evidence that the validation condition succeeded does not become evidence of success.

The same principle can be applied to authorization, security validation, financial transactions, deployment gates, and other safety-sensitive boundaries.

Failure behavior should also distinguish between different causes. A missing approval is not the same condition as a failing test, and a requested change is not the same condition as an unavailable status provider.

Explicit blockers make those distinctions observable.

---

## Contracts and state

Some contracts are valid only for a particular state.

A review can be associated with a particular revision of a Pull Request. If the revision changes, the applicability of the previous review can change.

This illustrates why a contract should sometimes include identity or version information.

The C++ implementation uses the current commit identifier as part of the review lookup. This prevents an approval tied to an older revision from automatically becoming a valid approval for a new revision.

The same pattern appears in other systems:

- a cached authorization decision may have an expiration;
- a payment authorization may apply to a particular transaction amount;
- a configuration validation may apply to a particular configuration version;
- a deployment approval may apply to a particular artifact digest.

The abstraction should preserve whatever identity is necessary to make its contract meaningful.

---

## Testing at the boundary

Boundary tests should verify behavior that consumers are entitled to rely on.

The Python tests verify that a valid repository can be registered through an in-memory contract implementation, that duplicate registration fails, and that merge eligibility requires an eligible external approval.

The JavaScript tests verify that structural dependencies work through the expected method contract, that event publication occurs, and that failed status checks remain blocking conditions.

The C++ tests verify several architectural invariants:

- valid current approvals can satisfy the approval requirement;
- an author's own approval is not counted;
- an approval associated with an old commit is not treated as current;
- missing status checks fail closed.

These tests are more valuable than testing implementation details such as the internal layout of a `Map` or `unordered_map`. The contract is what the consuming component depends upon.

---

## Common boundary failures

### Concrete infrastructure inside business logic

When a domain or application service directly constructs a database client, HTTP client, cloud SDK, or filesystem adapter, the implementation detail has crossed the dependency boundary.

This increases coupling and makes replacement more expensive.

### Abstractions that expose implementation details

An interface does not become useful merely because it is named `IWhatever`. If its methods expose SQL rows, HTTP response objects, provider-specific error codes, or SDK classes, the abstraction may still be tightly coupled to infrastructure.

### Weak contracts

A method such as `process(data)` is often too vague to establish a useful boundary. Consumers cannot easily determine valid inputs, output semantics, or failure behavior.

### Hidden construction

A class that silently constructs all of its collaborators hides its dependency graph. Constructor injection or another explicit composition mechanism makes dependencies visible.

### Treating missing data as success

When a required dependency cannot establish that a condition has passed, silently accepting the operation can violate the intended contract.

The C++ status-check example deliberately avoids this behavior.

### Over-abstraction

Creating an interface for every class can make a codebase harder to understand. An abstraction should exist because a boundary has architectural meaning, not because every concrete class is expected to have an interface.

---

## Performance considerations

An abstraction normally adds little runtime cost compared with the cost of the external operation it represents. The important performance question is usually what happens behind the boundary.

The C++ implementation uses `unordered_map` for memory-backed lookup and `set` for unique eligible reviewers. Review evaluation therefore avoids repeatedly scanning an unrelated collection when identifying distinct approvers.

The Python implementation uses sets to deduplicate reviewers. The JavaScript implementation uses `Set` for the same semantic requirement.

For real infrastructure, contract design also affects performance indirectly. A repository contract that forces one network request per entity can create an inefficient application even if the interface itself looks clean. A useful abstraction should expose operations that match the actual access patterns of its consumers.

---

## Security considerations

Dependency boundaries are security boundaries when the dependency controls authorization, secrets, data access, or privileged operations.

A caller should not be able to bypass a protected operation simply by supplying an object that claims to satisfy an interface. Authentication and authorization remain separate responsibilities.

Runtime contract validation also should not be confused with security validation. Checking that an object contains a `send()` method proves very little about whether that implementation is trusted.

Privileged bypasses should be explicit and auditable. The C++ protected-branch example records an administrator bypass rather than treating administrator status as an invisible exception.

Sensitive dependencies should also avoid leaking provider-specific credentials or secret-bearing configuration into domain objects.

---

## Production considerations

In production systems, interfaces and contracts should be designed around ownership and change frequency.

A stable domain or application boundary should avoid exposing infrastructure types that are likely to change independently.

External service adapters should translate provider-specific representations into application-level concepts. This prevents a vendor API's object model from becoming the application's internal model.

Contracts should also define observable failure behavior. Network timeouts, unavailable dependencies, malformed responses, duplicate operations, authorization failures, and partial failures should not be collapsed into one generic exception when callers need to react differently.

For distributed systems, the contract may need to specify idempotency, retry safety, timeout expectations, consistency assumptions, and version compatibility.

For security-sensitive systems, the contract may also need explicit authorization requirements and audit behavior.

The central architectural objective remains the same: a component should depend on the smallest stable capability it actually needs, while implementation details remain behind the boundary that owns them.
