# Domain-Driven Design Basics: Domain, Entities, Value Objects, and Aggregates

## Purpose

This set of implementations models the core building blocks of Domain-Driven Design through concrete business domains rather than through generic object-oriented examples.

The central distinction is that DDD is concerned with representing business meaning and protecting business rules. A class is not automatically an entity, and an object is not automatically a value object simply because it contains data. The model must reflect how the business identifies, compares, changes, and governs the concept.

The implementations use different domains deliberately:

| Implementation | Domain scenario | Primary DDD perspective |
| --- | --- | --- |
| Python | Online ordering | Aggregate invariants, entity identity, immutable value objects, repositories, and domain events |
| JavaScript | Event-driven ordering | Aggregate lifecycle and domain events connected to an event-driven application boundary |
| C++ | Repository governance | Aggregate-based consistency around Pull Request governance and merge eligibility |
| Java | Enterprise subscriptions | Explicit domain types, policies, entity lifecycle, and aggregate state transitions |
| SQL | Relational ordering | Persistent representation of entities, value data, aggregate ownership, constraints, and transactional state changes |

The examples are intentionally different. The goal is to show that the same DDD concepts can be applied to different business domains without reducing DDD to a fixed class hierarchy.

## Domain

The **domain** is the business problem space being modeled.

For an ordering system, the domain includes concepts such as customers, products, orders, quantities, prices, addresses, and order lifecycle rules.

For a subscription system, the domain includes customers, plans, seats, billing identities, subscription states, and activation policies.

For repository governance, the domain includes Pull Requests, commits, reviews, status checks, protected branches, and merge eligibility.

The domain is more important than the programming language. A useful DDD model starts by identifying meaningful business concepts and their relationships before deciding how those concepts should be represented in code.

A domain concept should have behavior when the business concept has rules that belong to it. For example, an order should not merely expose a mutable `status` field and allow every caller to assign arbitrary values. The order should control valid transitions such as draft to confirmed or draft to cancelled.

## Entity

An **entity** is identified primarily by identity rather than by the complete set of its current attributes.

An entity can change while remaining the same conceptual object.

An `OrderLine` can change its quantity while remaining the same line entity. A `Subscription` can change from pending to active, suspended, and eventually cancelled while retaining its identity.

This is different from a value object. If two independent order lines have identical product, price, and quantity values, they can still represent different entities because their identities and relationships within their respective aggregates are different.

The Python `OrderLine` contains a `line_id`. Its quantity can change without replacing the identity. The Java `SubscriptionItem` follows the same principle with a UUID. In the C++ implementation, `PullRequest` has a stable identifier while its lifecycle and review state evolve.

Entity identity is therefore a domain decision, not simply a database primary-key decision.

## Value Objects

A **value object** represents a concept whose meaning comes from its values.

Value objects normally have no independent lifecycle. Replacing one equivalent value object with another equivalent instance does not change the business identity of the surrounding entity.

The implementations use several examples:

- `Money` represents an amount and currency.
- `ProductId` or `ProductCode` represents a validated product identifier.
- `Address` represents a complete location value.
- `EmailAddress` represents a validated email value.
- `BranchName` represents a validated branch-name value.
- `CommitId` represents a validated commit identifier.
- `PlanCode` represents a subscription-plan value.

The Python `Money` class is immutable through `@dataclass(frozen=True)`. Its arithmetic creates new `Money` objects instead of modifying an existing amount.

The Java implementation uses records for several value objects. This is a natural fit because Java records provide compact immutable value-oriented types with value-based equality.

The JavaScript implementation explicitly freezes value objects with `Object.freeze`. This prevents consumers from changing a `Money`, `ProductCode`, or `ShippingAddress` instance after construction.

Value objects are particularly useful for validation. Instead of passing an arbitrary string throughout an application and repeatedly asking whether it is a valid email address, a domain model can construct an `EmailAddress` only when the value satisfies the domain rule.

That moves the rule closer to the concept that owns it.

## Entity and Value Object Distinction

The distinction can be expressed through the question used to compare two objects.

| Question | Entity | Value object |
| --- | --- | --- |
| What defines identity? | Stable identity | Attribute values |
| Can attributes change? | Yes | Prefer replacement with a new value |
| Does lifecycle matter? | Yes | Usually no |
| Is identity meaningful independently? | Yes | No |
| Typical example | Order | Money |
| Typical example | Subscription | EmailAddress |
| Typical example | OrderLine | Address |

Consider two customers with the same name.

They can still be different customers because the business identifies customers independently of their names.

Now consider two `Money` instances containing INR 1,000.00. If all relevant monetary attributes are equal, there is normally no business reason to distinguish the objects merely because they occupy different memory locations.

That is the conceptual difference between identity equality and value equality.

## Aggregates

An **aggregate** is a consistency boundary around a group of related domain objects.

An aggregate has an **aggregate root**. External application code normally interacts with the aggregate through that root rather than modifying internal members directly.

The aggregate root is responsible for maintaining invariants that must remain consistent across the boundary.

The Python implementation uses `Order` as the aggregate root and `OrderLine` as an internal entity.

The root controls operations such as:

- adding a line
- removing a line
- changing a quantity
- confirming the order
- cancelling the order
- calculating the aggregate total

The caller does not receive direct mutable access to the internal dictionary of order lines. `Order.lines()` returns immutable snapshots instead.

This is important because exposing mutable aggregate internals can bypass the rules that the aggregate is supposed to protect.

## Aggregate Invariants

An invariant is a condition that must remain true whenever the aggregate is in a valid state.

The Python order aggregate enforces several such conditions:

- An order line must have a positive quantity.
- An order cannot be confirmed without at least one line.
- A confirmed order cannot be modified as though it were still a draft.
- The same product is consolidated into one order line.
- A cancellation requires a meaningful reason.
- Monetary operations cannot silently combine different currencies.

The JavaScript order aggregate applies the same general business concepts but exposes domain events to an event-driven application boundary.

The Java subscription aggregate protects a different set of rules:

- A plan cannot have zero or negative seats.
- An active subscription cannot be modified as though it were pending.
- Activation requires a valid billing identity.
- Activation requires at least one plan item.
- A cancelled subscription cannot be reactivated.
- Suspension requires a reason.
- Reactivation requires the activation policy to pass again.

These are not generic programming rules. They are rules belonging to the selected business domains.

## Aggregate Size and Consistency

An aggregate should not automatically contain every object that happens to be related to another object.

The important question is which objects must be changed consistently as one transactional business operation.

An order can reasonably own its order lines because changing the order and its lines frequently requires the same consistency boundary.

A customer does not need to become a child object of every order. The order can retain a `CustomerId` reference instead.

This keeps the aggregate boundary smaller and reduces unnecessary coupling.

The same principle appears in the repository-governance case study. The C++ `PullRequest` owns its commits and review decisions for the purpose of evaluating its merge eligibility. Repository-level policy remains separate because the policy governs the repository rather than representing a child object of one Pull Request.

## Aggregate Root Behavior

The aggregate root should provide operations that express domain actions.

Compare these two approaches conceptually:

`order.status = CONFIRMED`

and

`order.confirm()`

The first exposes raw state mutation. It allows callers to attempt transitions without necessarily satisfying the required rules.

The second gives the aggregate an opportunity to validate its complete state before changing it.

The implementations use methods such as:

- `confirm()`
- `cancel()`
- `addLine()`
- `changeLineQuantity()`
- `activate()`
- `suspend()`
- `reactivate()`

These methods express business operations instead of merely exposing storage.

## Python Implementation

The Python program uses an online ordering domain to demonstrate the four fundamental DDD concepts together.

`Customer` is an entity because it has a `CustomerId` and can change attributes without becoming a different customer.

`Address`, `Money`, `ProductId`, and `OrderId` are value-oriented domain types. `Money` validates currency and prevents negative amounts. Its arithmetic creates new values.

`OrderLine` is an entity inside the `Order` aggregate. It has its own identity and mutable quantity.

`Order` is the aggregate root. Its private line collection prevents arbitrary external mutation and forces changes through domain operations.

The repository classes represent persistence boundaries without introducing an actual database dependency. The application service coordinates repository access and aggregate operations.

The aggregate also produces `OrderConfirmed` and `OrderCancelled` domain events. These events represent facts that occurred in the domain rather than commands telling another component what to do.

The script deliberately attempts invalid operations after confirmation. The resulting exceptions demonstrate that the aggregate boundary is executable behavior rather than documentation.

## JavaScript Implementation

The JavaScript implementation emphasizes an event-driven model.

The value objects use immutable objects. `ProductCode` normalizes and validates product identifiers, while `Money` validates monetary values and creates new instances during arithmetic.

`OrderLine` is an entity with a generated UUID. The `Order` aggregate owns the line map and controls modifications.

The application service calls the aggregate rather than manually changing its state.

A domain event such as `OrderConfirmed` is returned by the aggregate and published through a Node.js `EventEmitter`.

The `FulfillmentProjection` subscribes to the event bus and maintains a small read model of confirmed orders.

This illustrates an important separation: the aggregate does not need to know how a downstream projection works. It only records the domain fact. The event-driven application boundary decides what reacts to that fact.

The JavaScript example therefore adds an event-oriented perspective instead of merely translating the Python classes.

## C++ Case Study

The C++ implementation models repository governance around a Pull Request.

`PullRequest` is an entity because its identity remains stable while its state changes from draft to open and eventually merged or closed.

`BranchName` and `CommitId` are value objects. Their identity is based on validated values rather than an independent lifecycle.

The Pull Request aggregate contains commits, review decisions, and status-check results required to evaluate whether the change can be merged.

`RepositoryPolicy` is deliberately separate from the Pull Request aggregate. It represents repository-level rules such as:

- the protected target branch
- required approval count
- required status checks
- linear-history requirements
- force-push policy

The aggregate exposes `mergeEligible()` rather than allowing an external caller to assign a merged state directly.

Merge eligibility fails when:

- the Pull Request is not open
- there are no commits
- the target branch is not the protected branch
- there is a merge conflict
- the base branch changed and synchronization has not occurred
- a reviewer requested changes
- the approval count is insufficient
- a required status check is missing or failing

The review implementation also demonstrates an important entity-level rule: the latest decision from each reviewer determines that reviewer's current decision. This prevents an old approval from being counted simultaneously with a newer decision from the same reviewer.

The C++ case study therefore demonstrates how an aggregate can protect a compound business decision rather than merely store data.

## Java Implementation

The Java implementation models an enterprise subscription domain.

`Subscription` is the aggregate root. `SubscriptionItem` is an internal entity because a plan allocation has identity and can change its seat count.

`CustomerId`, `PlanCode`, `EmailAddress`, and `Money` are immutable value-oriented types.

The `SubscriptionPolicy` interface separates policy evaluation from aggregate identity. `StandardSubscriptionPolicy` determines whether activation is valid based on domain conditions.

The aggregate itself remains responsible for changing its state. The policy answers whether the business conditions for activation are satisfied, while the aggregate controls the actual transition.

The Java state model makes invalid transitions explicit:

`PENDING -> ACTIVE`

`ACTIVE -> SUSPENDED`

`SUSPENDED -> ACTIVE`

`PENDING -> CANCELLED`

`ACTIVE -> CANCELLED`

`SUSPENDED -> CANCELLED`

A cancelled subscription cannot be reactivated.

This state-oriented model is more expressive than exposing a mutable string status and allowing callers to assign arbitrary values.

Java records are used where value semantics are appropriate, while classes are used for entities whose identity and lifecycle matter.

## SQL Data Model

The SQL implementation maps the ordering domain to PostgreSQL.

`customer` represents a customer entity.

`customer_order` represents the Order aggregate root.

`order_line` represents entities owned by the order aggregate.

`product` provides product identity and current pricing information.

The schema uses a UUID primary key for entity identity. The `order_line` table contains a foreign key to `customer_order`, making ownership explicit at the relational level.

The constraint:

`UNIQUE (order_id, product_id)`

prevents the same product from appearing as multiple independent lines within one order.

The quantity constraint requires every line to have a positive quantity.

Currency and monetary constraints prevent invalid negative prices and malformed currency values.

The order status uses a PostgreSQL enum instead of arbitrary text. This restricts the persisted state to the domain's known states.

The confirmation and cancellation constraints connect status to its corresponding timestamps and cancellation reason. This prevents states such as a non-cancelled order carrying a cancellation timestamp or a confirmed order lacking a confirmation timestamp.

## Database Transactions and Aggregate Changes

The SQL transaction changes an order from draft to confirmed only when it has at least one line.

The update is conditional on the current state:

`status = 'DRAFT'`

This prevents a second confirmation operation from treating an already-confirmed order as a draft.

The cancellation transaction applies the same principle by allowing the operation only from the draft state in the supplied scenario.

The database therefore participates in enforcing domain integrity instead of treating the database as an unprotected storage bucket.

Application-level validation remains useful, but critical persistence invariants should not depend exclusively on every application path behaving correctly.

## Domain Logic Versus Persistence Logic

DDD does not require every domain concept to be a database table.

A value object can be embedded into an entity's persisted representation.

For example, `Address` can be represented through several columns of an order table. That does not make Address an entity.

Likewise, `Money` can be represented through an amount column and a currency column without acquiring independent entity identity.

The conceptual classification comes from domain meaning, not from how many tables or classes exist.

## Domain Events

A domain event records something meaningful that has already happened.

The Python example creates `OrderConfirmed` and `OrderCancelled`.

The JavaScript example makes domain events especially visible through an event bus. A confirmation event updates a fulfillment projection without placing projection logic inside the Order aggregate.

Domain events can therefore help maintain a clean separation between:

- the decision made inside the domain
- persistence of the aggregate
- downstream reactions

The aggregate should not become responsible for every side effect caused by its state transition.

## Entities, Aggregates, and Repositories

These concepts solve different problems.

An entity answers:

**What object has identity and lifecycle?**

An aggregate answers:

**Which related objects must be kept consistent as one boundary?**

A repository answers:

**How does the application retrieve and persist an aggregate?**

The Python repositories store objects in memory, but their important role is the boundary they represent. The application service retrieves an aggregate, invokes domain behavior, and saves the resulting aggregate.

A repository should not become a replacement for domain behavior. A method such as `save()` persists state; it should not become the place where order confirmation rules are scattered.

## Common Modeling Mistakes

### Treating every class as an entity

Creating an ID for every object can produce artificial identity and unnecessary lifecycle management.

A postal address normally does not need an independent identity merely because it is represented by a class.

### Treating every object as a value object

A subscription cannot be treated purely as a value because its identity and lifecycle matter.

Replacing a subscription with an equivalent object could incorrectly imply that the original subscription ceased to exist.

### Exposing aggregate internals

Returning mutable internal collections lets callers bypass invariants.

The Python order returns snapshots, and the Java subscription keeps its item map private.

### Putting all related objects into one aggregate

Relationships do not automatically imply aggregate membership.

A customer can be referenced by an order without becoming part of the order aggregate's consistency boundary.

### Allowing arbitrary state mutation

A public status setter makes invalid transitions easy.

Explicit domain operations such as `confirm()`, `cancel()`, `activate()`, and `suspend()` allow the model to protect state transitions.

### Using primitive strings for important concepts

Passing raw strings for currency, plan codes, emails, branch names, or product codes makes validation easy to forget.

Value objects centralize the rules associated with those concepts.

## Edge Cases Demonstrated

The Python implementation rejects empty orders during confirmation, rejects modifications after confirmation, validates positive quantities, and prevents incompatible currency operations.

The JavaScript implementation rejects malformed product codes, invalid monetary values, duplicate product lines, and modifications after confirmation.

The C++ implementation rejects invalid Pull Request states, insufficient approvals, failed status checks, unresolved base-branch changes, merge conflicts, and requested changes.

The Java implementation rejects invalid subscription transitions, missing plans, invalid seat counts, invalid email addresses, and reactivation after cancellation.

The SQL implementation uses relational constraints to prevent invalid quantities, malformed states, duplicate products inside one order, invalid monetary values, and inconsistent confirmation or cancellation data.

## Performance Considerations

Aggregate boundaries also have performance implications.

An excessively large aggregate can require loading and validating many objects for a single operation. It can also increase transaction contention when multiple users attempt unrelated changes to objects inside the same boundary.

A smaller aggregate can reduce transaction cost and make concurrency easier to manage.

The Python and JavaScript examples use maps for direct access to internal entities by identity.

The SQL implementation adds indexes on customer references, order status, and product references because those columns participate in common retrieval and filtering operations.

The C++ case study uses hash-based lookup for reviewer decisions, allowing the latest review decision for each reviewer to be consolidated efficiently.

The correct optimization depends on domain access patterns. Data structures should support the actual consistency and lookup requirements rather than being selected merely because they are familiar.

## Security and Integrity Considerations

Domain validation is not a complete security boundary.

An application still needs authentication and authorization to determine who is allowed to invoke a domain operation.

The DDD model is responsible for business correctness within the domain boundary. A separate authorization layer can determine whether the caller is permitted to invoke that operation.

The repository-governance case demonstrates the distinction clearly. A Pull Request can be technically eligible for merging, while a separate authorization mechanism may still determine whether a particular actor is allowed to perform the merge.

Persistence constraints provide another integrity layer. Database checks should protect critical invariants against accidental or unexpected writes from alternate application paths.

## Testing Implications

DDD models are particularly suitable for behavior-focused tests.

Tests should verify business rules rather than only checking whether fields contain expected values.

Useful behavioral assertions include:

- A draft order with no lines cannot be confirmed.
- Adding the same product increases the existing line quantity.
- A confirmed order cannot receive a new line.
- A cancelled subscription cannot be reactivated.
- A Pull Request with a failing required status check cannot be merged.
- A database order cannot contain duplicate products within the same aggregate.
- Equivalent value objects compare according to their values rather than object identity.

These tests protect domain rules even when implementation details change.

## Relationship Between the Four Core Concepts

The concepts become most useful when viewed together.

A **domain** defines the business language and rules.

An **entity** represents something whose identity and lifecycle matter within that domain.

A **value object** represents a descriptive concept whose meaning comes from its values.

An **aggregate** establishes a consistency boundary around entities and value objects and provides an aggregate root through which important state changes are controlled.

A typical relationship is:

`Domain -> Aggregate Root -> Entity / Value Object`

For the ordering example:

`Ordering Domain -> Order -> OrderLine / Money / Address / ProductId`

For the subscription example:

`Subscription Domain -> Subscription -> SubscriptionItem / Money / PlanCode / EmailAddress`

For repository governance:

`Repository Governance Domain -> PullRequest -> Commit / Review state`

The purpose of these relationships is not to create a complicated object graph. The purpose is to make business rules explicit, localize invariants, protect meaningful state transitions, and give domain concepts precise representations.
