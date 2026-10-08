# Design Patterns III: Repository, Facade, and Decorator

This learning artifact examines three structural and architectural patterns that solve different problems in application design:

- **Repository** separates domain behavior from persistence technology.
- **Facade** provides a controlled high-level interface over a group of collaborating services.
- **Decorator** adds behavior to an existing object dynamically while preserving its public contract.

The patterns can appear together in the same system, but they should not be treated as interchangeable abstractions. A repository answers questions about **where and how application data is persisted**. A facade answers **how a complex subsystem is presented to a caller**. A decorator answers **how additional behavior can be composed around an existing component**.

The implementations use different technical perspectives so that the patterns are understood as design mechanisms rather than as language-specific templates.

## Repository Pattern

The Repository pattern introduces an abstraction between domain or application services and the persistence mechanism.

A service should be able to request operations such as `findById`, `findByOwner`, `save`, or `delete` without knowing whether the underlying data comes from:

- an in-memory collection,
- a relational database,
- a document store,
- a file,
- a remote API,
- or another persistence mechanism.

The important boundary is the repository interface. The business service depends on that boundary rather than on a concrete storage implementation.

### Why the boundary matters

Without a repository abstraction, business logic can become tightly coupled to persistence operations. A service that directly manipulates dictionaries, SQL connections, ORM sessions, or filesystem records has to understand both the business rule and the storage mechanism.

The Python implementation demonstrates this with `ProductRepository`. `ProductService` receives a repository object and performs business operations through that abstraction.

The concrete `InMemoryProductRepository` stores records in a dictionary. The `JsonProductRepository` demonstrates a different persistence strategy while preserving the same repository-facing behavior.

This distinction is important:

`ProductService -> ProductRepository <- InMemoryProductRepository`

The service knows the repository contract. It does not need to know that one implementation uses a dictionary and another serializes JSON.

### Repository responsibilities

A repository is most useful when its operations correspond to domain persistence needs.

The Python example includes `save`, `find_by_id`, `find_by_category`, `list_active`, and `delete`. These operations represent product persistence rather than generic collection manipulation.

The C++ document case study applies the same boundary to controlled documents. `DocumentRepository` abstracts storage while `DocumentService` handles document creation and publication rules.

The Java implementation uses `DocumentRepository` with an `InMemoryDocumentRepository`. Java's `Optional` is used for potentially missing entities rather than returning `null` from repository lookups.

The SQL implementation represents the persistence layer directly through relational tables, primary keys, foreign keys, constraints, indexes, and queries. The database is not merely treated as a collection of arbitrary rows. Its constraints enforce rules that belong at the persistence boundary.

### Repository does not mean "one class per table"

A repository should be designed around meaningful application access patterns. It is not necessary to create a repository method for every possible SQL statement or collection operation.

For example, `findByCategory` is meaningful in the product domain because product category is an application-level query concept.

A repository that simply exposes unrestricted persistence operations can become a thin wrapper around a database driver without providing useful architectural separation.

## Facade Pattern

The Facade pattern provides a simplified interface to a subsystem containing several collaborating components.

A client might otherwise need to understand the order and responsibilities of multiple services.

Consider an order workflow:

`Client -> Inventory -> Payment -> Shipping -> Notification`

A facade can expose:

`Client -> OrderFacade.placeOrder(...)`

The caller does not need to coordinate the internal sequence.

### The Python order facade

The Python implementation models an order workflow using:

- `InventoryGateway`
- `PaymentGateway`
- `ShippingService`
- `NotificationService`
- `OrderFacade`

`OrderFacade.place_order` coordinates inventory reservation, payment, shipment creation, and confirmation notification.

The facade is responsible for orchestration. The underlying services remain separate because inventory, payment, shipping, and notification have different responsibilities.

The facade does not attempt to replace those services. It provides a convenient entry point for a common business workflow.

### Failure handling

The Python facade checks inventory before charging the customer. If a product cannot be reserved, the workflow stops before downstream operations occur.

The example also demonstrates a compensating action. If subscription-style downstream processing fails after a persistent record has been created, the record can be removed in the example implementation.

In production systems, compensation must be designed carefully. Removing a record is not always equivalent to reversing a payment or undoing an external API operation.

A facade therefore improves orchestration, but it does not automatically provide distributed transaction guarantees.

### C++ publication workflow

The C++ implementation uses a document publication scenario.

The publication workflow coordinates:

- repository retrieval,
- publication validation,
- state transition,
- search indexing,
- audit recording.

The client can call the workflow without directly coordinating all of those subsystems.

The implementation also shows why validation belongs in the workflow when the rule applies specifically to the complete publication operation. A document can exist in storage while still being unsuitable for publication.

### Java enterprise workflow

The Java implementation models a compliance document platform.

`PublicationFacade` coordinates:

- repository lookup,
- compliance validation,
- approval,
- publication,
- search indexing,
- audit recording.

The domain object itself enforces valid state transitions. A document cannot move directly from `DRAFT` to `PUBLISHED`. It must first become `APPROVED`.

This distinction keeps domain state rules inside the domain model while allowing the facade to coordinate the larger workflow.

## Decorator Pattern

The Decorator pattern wraps an object with another object implementing the same abstraction.

The wrapper can add behavior before, after, or around the wrapped operation.

The relationship can be visualized as:

`Client -> Decorator -> Decorator -> Concrete Component`

The decorators preserve the component's interface while adding behavior.

This differs from inheritance used simply to create many fixed subclasses. Decorators allow behavior to be composed dynamically.

## Decorator composition

The Python catalog implementation starts with `RepositoryCatalog`.

Additional behavior is then composed through:

`RepositoryCatalog`
`-> CategoryFilterDecorator`
`-> PriceRangeDecorator`
`-> LoggingDecorator`
`-> TimingDecorator`

Each layer receives another `ProductCatalog`.

The client still interacts with `get_products()`.

The filtering decorators modify the result set, while logging and timing decorators add operational behavior.

This is a useful example of separation between core business retrieval and cross-cutting behavior.

### Python function decorators

Python also has language-level decorator syntax.

The `audit` function returns a wrapper around another callable. The wrapper measures execution time and records success or failure while preserving the wrapped function's metadata with `functools.wraps`.

This demonstrates an important distinction:

- The **Decorator design pattern** is an object-structuring technique.
- Python's **decorator syntax** is a language feature for wrapping functions or classes.

The language feature can implement the design pattern, but the concepts are not identical.

## JavaScript Decorators Through Composition

The JavaScript implementation uses classes and asynchronous operations to model a subscription platform.

`SubscriptionRepository` defines the persistence boundary, while `MemorySubscriptionRepository` supplies an in-memory implementation.

The facade coordinates subscription creation, billing authorization, resource provisioning, and email notification.

The query system then uses decorator objects:

`RepositorySubscriptionQuery`
`-> ActiveOnlyQueryDecorator`
`-> TimingQueryDecorator`
`-> LoggingQueryDecorator`

JavaScript's asynchronous model makes the distinction particularly useful. Repository methods return Promises, so the service and decorator layers can preserve asynchronous behavior without exposing storage details to the caller.

The JavaScript file also contains a higher-order function called `withRetry`. It wraps an asynchronous operation and adds retry behavior without changing the original operation.

The retry example is intentionally separate from the query decorator chain because retry behavior is an operation wrapper rather than a filtering concern.

## C++ Case Study

The C++ implementation models a document platform using interfaces and ownership-aware composition.

`DocumentRepository` is an abstract persistence boundary. `InMemoryDocumentRepository` implements that boundary using `std::unordered_map`.

The document service operates against `DocumentRepository`, which means the domain service does not need to know the concrete storage structure.

The query decorator hierarchy uses `std::unique_ptr<DocumentQuery>`.

This is significant because the decorator chain owns its wrapped component. Moving a `unique_ptr` into another decorator establishes clear ownership and avoids manual memory management.

The final query chain adds:

- published-document filtering,
- audit logging,
- execution timing.

The decorators all implement `DocumentQuery`, so each layer can be substituted for the original query.

### C++ validation and failure behavior

The case study validates document identifiers, titles, owners, and content.

Publication validation also requires sufficient document content and a valid owner.

Failure is represented through standard C++ exceptions such as `std::invalid_argument` and `std::runtime_error`.

The implementation catches exceptions at the application boundary and returns a nonzero process status when an unexpected application-level failure occurs.

## Java Domain Model

The Java implementation uses an explicit state model:

`DRAFT -> APPROVED -> PUBLISHED -> ARCHIVED`

The state transitions are methods on `Document`, rather than arbitrary assignments to a public state field.

This prevents invalid transitions such as publishing a draft directly.

The domain also contains `Employee` and `Permission`. Approval and publication permissions are evaluated by the service layer before the corresponding state transition is executed.

This creates two separate concerns:

- `Document` controls whether a transition is structurally valid.
- `DocumentService` controls whether the actor has permission to request that transition.

The facade coordinates the broader workflow.

## Java Decorator Chain

The Java query abstraction is `DocumentQuery`.

`RepositoryDocumentQuery` provides the base result.

Decorators can then be layered:

`RepositoryDocumentQuery`
`-> OwnerFilterDecorator`
`-> PublishedOnlyDecorator`
`-> AuditDecorator`
`-> TimingDecorator`

Each decorator preserves the `DocumentQuery` interface.

This allows different combinations to be constructed without creating a separate class for every possible combination.

For example, an application could create an owner-filtered query without timing or auditing, while another workflow could add both operational concerns.

The design is therefore compositional rather than combinatorial.

## SQL Data Model

The PostgreSQL implementation demonstrates how the three patterns relate to a relational persistence layer.

The repository-oriented domain uses:

- `products`
- `customers`
- `orders`
- `order_items`

The tables use primary keys and foreign keys to preserve entity relationships.

`CHECK` constraints prevent invalid values such as negative prices and non-positive quantities.

Indexes support common access paths such as category-based product retrieval and customer/order lookups.

### Database integrity

Application code should not be the only layer responsible for protecting persistent data.

For example:

`products_price_positive`

prevents negative product prices at the database level.

The foreign key from `orders.customer_id` to `customers.customer_id` prevents an order from referencing a customer that does not exist.

The foreign key from `order_items.product_id` to `products.product_id` prevents order items from referring to unknown products.

These constraints remain active even if data is inserted through another application, administrative script, or integration.

## SQL and the Facade Workflow

The SQL transaction demonstrates the database operations required for a simplified order workflow.

The transaction creates:

- an order,
- order items,
- a payment record,
- a shipment record,
- a final order state,
- an audit event.

`BEGIN` and `COMMIT` make the group of operations atomic at the database transaction level.

The SQL transaction does not turn the database into a facade. The facade remains an application-level architectural concept. The database transaction instead provides an important persistence mechanism that an application facade can use when the workflow contains several related database operations.

This distinction prevents the facade pattern from being confused with transaction management.

## SQL and Decorator-Like Query Composition

SQL does not implement the object-oriented Decorator pattern directly.

The `WITH` query demonstrates a related compositional idea using relational query transformations:

`catalog`

is the base relation.

`security_products`

adds a category restriction.

`premium_security_products`

adds a price restriction.

The final query projects and orders the resulting data.

This is useful for understanding the conceptual relationship without claiming that SQL CTEs are literally object decorators.

## Pattern Distinctions

| Pattern | Primary problem | Main mechanism | Typical boundary |
|---|---|---|---|
| Repository | Persistence coupling | Storage abstraction | Domain/application to persistence |
| Facade | Subsystem complexity | Coordinated high-level interface | Client to multiple services |
| Decorator | Extensible behavior | Wrapper composition | Client to component |

A repository is primarily about **persistence access**.

A facade is primarily about **subsystem orchestration and simplification**.

A decorator is primarily about **adding behavior while preserving an existing interface**.

A single system can use all three:

`Application`
`-> Facade`
`-> Domain Services`
`-> Repository`
`-> Persistence`

while a query service can separately use:

`Repository Query`
`-> Filtering Decorator`
`-> Logging Decorator`
`-> Timing Decorator`

The patterns solve different architectural problems even when they appear in the same call path.

## Common Design Errors

### Treating a facade as a god object

A facade should coordinate existing responsibilities rather than absorb every business rule in the system.

If the facade begins implementing inventory calculations, payment algorithms, shipping rules, persistence details, notification formatting, and unrelated domain policies, it becomes difficult to maintain.

The underlying services should retain cohesive responsibilities.

### Making a repository a generic collection wrapper

A repository should expose domain-relevant persistence operations.

Methods that simply expose every low-level storage operation can make the abstraction meaningless.

The repository should hide persistence details while exposing operations that application behavior actually requires.

### Using decorators for unrelated responsibilities

A decorator should have a clear reason for wrapping another component.

Logging, timing, caching, filtering, authorization checks, metrics, and retry policies can be good candidates when their behavior can be cleanly composed.

A decorator that contains unrelated business workflows makes the object chain difficult to understand.

### Confusing inheritance with decoration

Inheritance defines a type relationship.

Decoration wraps an existing object and adds behavior dynamically.

If behavior combinations are numerous, decorators can avoid creating a subclass for every combination.

For example, four independent optional behaviors can create many possible combinations if modeled entirely through subclasses. Composition allows those behaviors to be assembled as needed.

## Failure and Edge Cases

Repository implementations must handle missing entities, duplicate identifiers, invalid values, and persistence failures.

Facade workflows must consider failures in intermediate services. A workflow can succeed in one subsystem and fail in another, so compensation, idempotency, and transaction boundaries become important in production systems.

Decorators must preserve the expected contract of the wrapped component. A decorator that changes return types, silently suppresses exceptions, or alters important semantics can violate the abstraction even though its method signatures look correct.

Stateful decorators also require care. Caching decorators can return stale data, retry decorators can repeat non-idempotent operations, and timing decorators must avoid changing the execution path merely to measure it.

## Performance Considerations

Repositories can introduce useful optimization boundaries. Database indexes, batching, pagination, and query-specific methods can prevent inefficient persistence access.

Facades can reduce client-side coordination but may become expensive if a single operation triggers many remote calls. In distributed systems, the facade may need timeout handling, retries, circuit breakers, and compensation.

Decorators introduce additional calls through each wrapper layer. The overhead is usually small compared with network or database operations, but very deep decorator chains can complicate debugging and performance analysis.

The examples therefore include timing decorators to make operational cost observable without embedding timing logic inside the core query implementation.

## Security Considerations

Repositories should validate data and rely on persistence constraints for critical integrity rules.

Facades that coordinate sensitive operations should enforce appropriate authorization boundaries and avoid trusting identifiers or amounts supplied directly by untrusted callers.

The Java example separates document permissions from document state transitions. Having permission checks outside the domain model can still require careful service-layer design so that unauthorized callers cannot bypass the intended workflow.

Decorators can provide useful security layers such as authorization or audit logging, but security-critical checks should not depend on an accidental decorator ordering. The architecture should make mandatory security enforcement explicit.

## Production Considerations

A production repository may use a connection pool, transaction-aware persistence mechanism, ORM, query builder, or direct SQL.

A production facade may coordinate remote services and therefore require explicit timeout, retry, idempotency, compensation, observability, and failure policies.

A production decorator chain may contain caching, metrics, authorization, tracing, rate limiting, or auditing. The ordering of those decorators can affect semantics. For example, caching before authorization can create an inappropriate security boundary if authorization depends on the current caller.

The central architectural distinction remains stable:

**Repository isolates persistence. Facade simplifies subsystem interaction. Decorator composes additional behavior around an existing abstraction.**
