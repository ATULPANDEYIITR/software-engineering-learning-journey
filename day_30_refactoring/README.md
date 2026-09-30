# Refactoring Techniques and Code Improvement

## Topic Scope

Refactoring is the disciplined restructuring of existing software while preserving the behavior that callers, users, integrations, and tests rely on.

The central distinction is between **changing what software does** and **changing how the software is organized internally**. A feature changes behavior intentionally. A refactoring changes structure so that existing behavior becomes easier to understand, test, extend, debug, or maintain.

This project treats code improvement as an engineering activity rather than a cosmetic formatting exercise. The implementations demonstrate how duplicated decisions, large functions, primitive data, excessive conditionals, mutable collections, tightly coupled infrastructure, and poorly separated responsibilities can be transformed into more explicit designs.

The three implementations use the same broad domain of order processing but approach refactoring differently:

- The Python program emphasizes executable refactoring patterns, domain objects, validation, testing, dependency boundaries, and characterization tests.
- The JavaScript program emphasizes encapsulation through private class fields, strategy objects, immutable policy data, asynchronous boundaries, dependency injection, and event-driven behavior.
- The C++ program presents a more structured case study using polymorphism, repository interfaces, value validation, dependency injection, and behavior-preservation checks.

The examples are deliberately scoped to refactoring and code improvement. They avoid treating language syntax itself as the subject.

## What Refactoring Changes

A useful refactoring changes the internal structure without intentionally changing the externally observable contract.

For example, a shipping calculation may initially contain several branches:

- standard shipping
- express shipping
- pickup
- special handling for different weights

Replacing that branching structure with strategy objects is a refactoring when the same shipping rules continue to produce the same results.

The important invariant is behavioral preservation. If an order previously produced a shipping cost of 74, the refactored implementation should continue to produce 74 unless a separate business change explicitly alters that rule.

Refactoring therefore requires a way to recognize the behavior that must remain stable. Tests, examples, domain invariants, API contracts, persisted data formats, and carefully selected characterization cases can all contribute to that contract.

## Code Smells That Motivate Refactoring

A code smell is an observable design characteristic that suggests a maintainability problem. A smell is not automatically a defect. It is a signal that the structure deserves examination.

### Duplicated logic

Duplicated business logic creates multiple locations that must remain synchronized.

The Python program begins with `calculate_legacy_discount`, where discount decisions are distributed across customer-type branches. The refactored `calculate_discount` moves the rates into a single policy structure.

The important improvement is not simply reducing the number of lines. The rule now has one authoritative representation. Changing the premium discount policy does not require finding several independent conditional branches.

### Long functions

A long function often performs several unrelated responsibilities:

- validation
- calculation
- transformation
- persistence
- notification
- formatting

Extracting cohesive operations gives each function a smaller reason to change.

The Python order implementation separates validation, subtotal calculation, shipping calculation, invoice construction, serialization, and persistence. The C++ order service follows a similar architectural boundary but uses separate classes and interfaces.

### Large conditional structures

Conditional logic becomes difficult to maintain when every new business variation requires editing the same function.

The shipping examples demonstrate replacing a conditional with a strategy abstraction. `StandardShipping`, `ExpressShipping`, and `PickupShipping` each own the calculation appropriate to their behavior.

This changes the extension point. A new shipping method can become a new strategy instead of another branch inside a large calculation routine.

### Primitive obsession

Passing raw strings and numbers everywhere can hide domain rules.

An email address is not simply an arbitrary string. It has validation requirements. Money is not merely a floating-point number because currency compatibility and non-negative values are meaningful domain constraints.

The Python `EmailAddress` and `Money` classes and the C++ `Money` value object demonstrate how domain concepts can own their invariants.

### Mutable collections exposed to callers

Returning internal mutable collections allows external code to bypass invariants.

The Python `ShoppingCart` exposes `items()` as a tuple. The JavaScript `ShoppingCart` stores products in a private `Map` and returns a new array when its contents are requested.

The purpose is encapsulation: the object controls how its state changes.

### Infrastructure mixed with business logic

A function that calculates a domain result and simultaneously writes files, sends messages, or performs network calls is harder to test.

The implementations separate pure or mostly deterministic domain calculations from infrastructure boundaries.

The Python program uses `NotificationGateway` and `OrderRepository` protocols. The JavaScript program injects notification and repository objects. The C++ program uses abstract interfaces for repositories and notification gateways.

## Extract Method

Extract Method separates a coherent operation from a larger procedure.

A good extracted function has a clear purpose and a meaningful name. The caller should be able to understand the higher-level workflow without reading every implementation detail.

The Python program uses functions such as `validate_order_items`, `calculate_order_total`, `qualifies_for_senior_bonus`, and `serialize_invoice`.

For example, `calculate_bonus` expresses the business decision while `qualifies_for_senior_bonus` expresses the specific eligibility rule. This makes the decision easier to read and test independently.

Extraction should not be performed mechanically. Creating dozens of tiny functions with no meaningful cohesion can make code harder to navigate. The useful boundary is a responsibility or domain concept, not an arbitrary number of lines.

## Replace Magic Numbers with Named Policies

Hard-coded values become problematic when their meaning is unclear or when the same business rule appears in several locations.

The Python implementation places tax and shipping thresholds in `PricingRules`. The JavaScript implementation uses the immutable `PRICING_POLICY` object. The C++ implementation uses named `PricingPolicy` constants.

A named value communicates intent:

`free_shipping_threshold`

is more informative than an unexplained numeric literal.

The same technique is useful for:

- tax rates
- timeout values
- retry limits
- monetary thresholds
- scoring boundaries
- capacity limits
- feature-specific policies

The improvement comes from expressing the meaning of the value, not simply moving a number into another file.

## Replace Conditional with Polymorphism

Conditional logic is appropriate when a small number of stable cases exist. It becomes a maintenance problem when behavior varies independently and new variants are expected.

The shipping examples model each shipping method as a separate strategy.

In Python, `ShippingStrategy` is a protocol and concrete classes implement `cost`.

In JavaScript, `StandardShipping`, `ExpressShipping`, and `PickupShipping` expose the same `calculate` operation.

In C++, `ShippingStrategy` is an abstract base class and concrete implementations override the virtual `calculate` operation.

The design separates selection from behavior. The factory or dispatch boundary chooses the strategy, while each strategy owns its calculation.

This is useful when different implementations may grow substantially over time.

It is not automatically better than a conditional. If there are only two trivial cases that will never grow, polymorphism can introduce unnecessary abstraction.

## Replace Primitive Data with Value Objects

Value objects combine a value with the rules that make that value valid.

The Python `EmailAddress` normalizes and validates email input. `Money` prevents negative values and prevents adding incompatible currencies.

The C++ `Money` class validates the amount and currency during construction.

This produces a stronger invariant:

Once a valid `Money` object exists, downstream code does not need to repeatedly ask whether its amount is negative.

The same principle can apply to:

- URLs
- identifiers
- dates
- geographic coordinates
- percentages
- account numbers
- measurement units

Validation should be placed close to the invariant when doing so prevents invalid state from spreading through the system.

## Encapsulate Collection

An internal collection should remain under the control of the object responsible for maintaining its invariants.

The Python cart uses a private dictionary. Its `add` method prevents duplicate products. The JavaScript cart uses a private `Map`, with `#items` preventing direct external mutation.

This matters because a public collection can bypass rules such as:

- duplicate detection
- quantity validation
- state transitions
- authorization
- audit requirements

Encapsulation does not mean every collection must be hidden. It means the ownership of mutation should be deliberate.

## Replace Temporary Variables with Queries

A temporary variable can obscure the business meaning of a condition.

The Python employee bonus example uses `qualifies_for_senior_bonus` and `qualifies_for_standard_bonus` rather than putting every condition directly into the main calculation.

Named queries provide domain vocabulary.

Compare the conceptual difference between:

`years >= 5 and performance >= 4.5`

and:

`qualifies_for_senior_bonus(employee)`

The latter communicates intent immediately and gives the rule an independent testing boundary.

## Introduce Parameter Objects

Functions with many related parameters often indicate that the parameters represent a missing domain concept.

The Python `OrderRequest` groups customer, items, shipping method, and destination information.

This has several benefits:

- related data travels together
- function signatures become smaller
- validation can operate on a coherent object
- the domain boundary becomes explicit
- future fields can be added without repeatedly expanding unrelated function calls

Parameter objects should represent meaningful concepts rather than merely hiding an excessively large argument list.

## Separate Pure Logic from Side Effects

A pure calculation depends on its inputs and produces a result without changing external state.

`calculate_order_total`, `calculate_discount`, `aggregate_sales`, and `serialize_invoice` are examples of operations whose behavior can be tested without a network service or database.

Side effects belong at controlled boundaries.

The Python `save_invoice` function performs filesystem I/O only after invoice construction and serialization are already separated.

The JavaScript notification gateway provides an asynchronous boundary. The business service does not need to know whether the notification implementation uses a console, database, queue, or external provider.

The C++ case study separates order calculation from repository persistence and notification.

This separation reduces the amount of infrastructure required for unit tests.

## Dependency Inversion

A high-level domain service should not need to know the implementation details of infrastructure.

The Python program defines `NotificationGateway` and `OrderRepository` protocols.

The JavaScript `OrderService` receives repository, notification, and event bus objects through its constructor.

The C++ `OrderService` receives references to `OrderRepository` and `NotificationGateway` abstractions.

This enables different implementations without rewriting the business service.

For example, production code could use a database repository while a test could use an in-memory repository.

The architectural relationship is:

`OrderService -> abstraction <- infrastructure implementation`

rather than:

`OrderService -> concrete database client`

This reduces coupling and makes replacement easier.

## Event-Driven Refactoring in JavaScript

The JavaScript implementation adds a `DomainEventBus`.

The order service emits `order.created` after the order has been persisted and the primary notification operation has completed.

The event bus demonstrates a useful separation between the operation that creates an event and subscribers that react to it.

The unsubscribe function is important. Event listeners that are never removed can accumulate in long-running applications and create memory or lifecycle problems.

Event-driven designs should also consider:

- event ordering
- duplicate delivery
- handler failures
- transaction boundaries
- retry behavior
- idempotency
- observability

An event bus is therefore not merely a stylistic replacement for function calls. It introduces a different operational model and should be used when decoupling is valuable.

## Characterization Tests

A characterization test records the current behavior of existing software before structural changes.

This is especially useful when the original implementation is complicated but its behavior is already relied upon.

The Python program compares the legacy discount calculation against the refactored implementation for representative scenarios.

The C++ program compares the legacy shipping calculation with the strategy-based implementation across multiple methods, weights, and distances.

These tests answer an important question:

> Did the restructuring accidentally change existing behavior?

A characterization test does not prove that the old behavior was correct. It protects the existing contract while the structure is being changed.

If the old behavior is known to be wrong, that correction should be treated as a deliberate behavior change rather than hidden inside a refactoring.

## Refactoring Safety

Refactoring is safest when performed through small, observable transformations.

A practical cycle is:

`existing behavior -> test or characterize -> make one structural change -> execute tests -> inspect the result -> continue`

The smaller the transformation, the easier it is to identify the source of a regression.

Useful safety mechanisms include:

- unit tests for domain rules
- characterization tests for legacy behavior
- integration tests for infrastructure boundaries
- static analysis
- compiler warnings
- type checking
- code review
- formatting and linting
- automated test execution

A refactoring should not rely solely on visual confidence.

## Python Implementation

The Python implementation is organized around an order-processing domain because that domain contains several independent refactoring opportunities.

`calculate_legacy_discount` provides a deliberately repetitive starting point. `calculate_discount` replaces repeated branching with a policy table.

`OrderItem`, `Customer`, and `OrderRequest` establish explicit domain structures. `validate_order_items` separates validation from total calculation.

`PricingRules` removes unexplained business literals from the pricing implementation.

`ShippingStrategy` demonstrates a protocol-based strategy design. Standard, express, and pickup shipping are represented by separate implementations.

`ShoppingCart` demonstrates collection encapsulation. Its internal dictionary cannot be directly modified by callers through the public interface.

`EmailAddress` and `Money` demonstrate value objects with validation at construction time.

`Invoice` construction and serialization remain separate from filesystem persistence. This creates a clean boundary between deterministic transformation and side effects.

`OrderRepository`, `NotificationGateway`, and `OrderService` demonstrate dependency inversion. The service coordinates business operations without requiring a concrete database or messaging provider.

The test suite deliberately checks both new behavior and behavior preservation. The legacy discount function is compared against the refactored discount function to make the distinction between restructuring and behavior change explicit.

## JavaScript Implementation

The JavaScript implementation uses language-specific features that make certain refactoring boundaries particularly visible.

Private class fields are used by `ShoppingCart` and `EmailAddress`. This prevents external code from directly modifying internal state.

`Object.freeze` is used for policy objects and returned domain structures where immutability is useful. Immutability reduces accidental state changes and makes data flow easier to reason about.

The `PRICING_POLICY` object centralizes business configuration.

Shipping strategies are represented as JavaScript classes rather than merely translating the Python protocol approach. The example also demonstrates asynchronous dependency boundaries through `async` notification methods.

`OrderService` receives its dependencies through its constructor. This is dependency injection without requiring a framework.

The event bus demonstrates another JavaScript-specific architectural option. The order service publishes `order.created`, while independent listeners can react without the service directly knowing their implementation.

The tests verify that the strategy refactoring preserves legacy shipping results, that collection invariants remain enforced, that invalid domain values are rejected, and that asynchronous service collaborators are invoked.

## C++ Case Study

The C++ program models a fulfillment service whose responsibilities have been separated from a large procedural design.

The central domain objects are:

- `Money`
- `ProductLine`
- `Customer`
- `Order`
- `OrderTotals`

`Money` protects basic monetary invariants and prevents arithmetic between incompatible currencies.

`PricingPolicy` owns order subtotal, tax, and free-shipping rules. It also validates duplicate product identifiers.

The shipping hierarchy uses `ShippingStrategy` as an abstraction. `StandardShipping`, `ExpressShipping`, and `PickupShipping` provide distinct implementations.

`ShippingStrategyFactory` owns strategy selection so the application service does not contain every shipping construction detail.

`OrderRepository` is an abstraction for persistence. `InMemoryOrderRepository` supplies a concrete implementation suitable for the case study and tests.

`NotificationGateway` is another abstraction. `ConsoleNotificationGateway` provides an infrastructure implementation without coupling the domain service to a specific messaging system.

`OrderService` coordinates validation, pricing, shipping, persistence, and notification. The individual responsibilities remain separated so each can evolve independently.

The characterization tests compare the original procedural shipping behavior with the strategy-based implementation over several input combinations. This demonstrates a practical method for validating that an architectural refactoring has not altered existing results.

## Refactoring Versus Feature Development

These activities should remain conceptually distinct.

A refactoring might transform:

`if method == "express": calculate one formula`

into:

`ExpressShipping.calculate()`

while preserving the same formula.

A feature change might introduce a new surcharge for international destinations. That changes business behavior.

Combining both changes in one large modification makes verification harder because a failing test could result from either the structural transformation or the new requirement.

Separating the changes gives each modification a clearer purpose and a smaller verification surface.

## Refactoring Versus Rewriting

Refactoring normally works incrementally on an existing implementation.

A rewrite replaces substantial portions of the system with a new implementation.

The distinction matters operationally. Incremental refactoring can preserve working behavior throughout the process and can be validated in small steps. A rewrite creates a larger period in which the old and new implementations differ and where behavioral compatibility must be established later.

Refactoring does not imply that rewriting is never appropriate. It means that the two activities have different risks, verification strategies, and migration characteristics.

## Behavioral Preservation

Behavior includes more than the final numerical result.

Depending on the system, observable behavior can include:

- return values
- exceptions
- error messages
- persistence formats
- ordering guarantees
- API responses
- side effects
- timing expectations
- authorization behavior
- transaction semantics

A refactoring that preserves successful outputs but accidentally changes an exception type can still break consumers.

The correct preservation boundary depends on the system's public contract.

## Edge Cases

The implementations deliberately reject invalid inputs rather than allowing bad state to propagate.

Examples include negative money values, invalid quantities, empty identifiers, duplicate products, unsupported shipping methods, incompatible currencies, missing customers, and negative physical measurements.

Boundary values also matter.

The free-shipping threshold is an example where the distinction between:

`subtotal >= threshold`

and:

`subtotal > threshold`

changes observable behavior.

Refactoring must preserve the original boundary unless the requirement itself changes.

## Common Refactoring Failure Modes

### Refactoring without tests

Without behavioral evidence, a structural change can silently alter existing behavior.

Characterization tests are especially useful when working with legacy code whose intended behavior is not fully documented.

### Combining too many transformations

Changing the architecture, naming, database access, business rules, and public API simultaneously makes failures difficult to isolate.

Small transformations produce smaller debugging surfaces.

### Abstraction for its own sake

Not every conditional requires polymorphism. Not every primitive needs a wrapper class. Not every function needs another layer of indirection.

An abstraction is useful when it represents a meaningful responsibility, variation point, or invariant.

### Moving code without improving responsibility

Changing a function's location does not automatically improve design.

The important question is whether the new location gives the code a clearer ownership boundary.

### Changing behavior accidentally

Refactoring should not quietly fix unrelated bugs unless the behavioral change is intentional and verified separately.

The characterization tests in the examples exist specifically to expose accidental changes.

### Preserving a bad abstraction

Refactoring is not synonymous with making the existing design prettier.

If the current abstraction represents the wrong concept, the useful refactoring may be to replace the abstraction entirely while keeping the externally required behavior stable.

## Performance Considerations

Refactoring can improve performance, preserve performance, or reduce performance depending on the chosen structure.

A strategy hierarchy introduces object dispatch where a conditional may be cheaper. In most business applications, this overhead is negligible compared with database, network, or filesystem operations.

Collections have more meaningful performance implications.

The Python and JavaScript examples use maps or dictionaries for product lookup and duplicate detection. Average hash-table lookup is generally expected to be O(1), while sorting regional sales results is O(n log n).

The C++ repository uses `std::map`, giving logarithmic lookup and ordered keys. An unordered container could provide expected constant-time lookup if ordering is unnecessary.

Performance refactoring should be evidence-driven. Structural clarity should not be sacrificed for hypothetical micro-optimizations without measurements showing that the operation is significant.

## Complexity of the Demonstrated Algorithms

The main order calculations iterate over the order items once, giving O(n) processing for n line items.

Duplicate detection through a hash-based set or map is expected O(n) overall under normal hash-table assumptions.

Sales aggregation is O(n), while ranking the aggregated regions requires sorting and therefore O(r log r) for r regions.

Repository lookup in the C++ `std::map` is O(log n).

These characteristics show why refactoring should consider the data structures behind an abstraction rather than focusing only on the visual appearance of the code.

## Security Considerations

Refactoring does not automatically make software secure.

Separating validation from business logic can make security controls easier to locate, but the controls still need to exist.

Important concerns in production systems include:

- validating untrusted input at system boundaries
- preventing unauthorized state changes
- protecting credentials
- avoiding sensitive information in logs
- validating serialized data
- controlling filesystem paths
- handling external API failures safely
- preventing injection vulnerabilities
- applying authorization independently of presentation logic

The invoice serialization example is intentionally simple. A production implementation should define its serialization contract and protect filesystem and identity boundaries appropriately.

## Debugging Considerations

A refactored system can initially feel harder to debug because a single large function has become several collaborating objects.

That trade-off is worthwhile when the new boundaries reflect actual responsibilities.

Good names become important. A stack trace containing:

`calculate_order_total -> shipping_cost -> ExpressShipping.cost`

can be more informative than a large function with several nested conditions.

Logging should also follow architectural boundaries. Important domain transitions, external calls, and failures should be observable without exposing sensitive information.

## Production Considerations

A production refactoring should account for the complete system rather than only source-code structure.

Relevant considerations include:

- public API compatibility
- database schema compatibility
- migration sequencing
- backward-compatible configuration
- observability
- rollback strategy
- test coverage
- deployment risk
- performance measurements
- concurrency behavior
- transaction boundaries
- error recovery

A locally successful refactoring can still fail in production if the software has undocumented consumers or side effects outside the immediate codebase.

## A Practical Refactoring Workflow

A disciplined workflow keeps structural changes observable.

Start by identifying a concrete smell or maintenance problem rather than deciding on a pattern first.

Establish the behavior that must remain stable through existing tests, characterization tests, examples, or an explicit contract.

Choose one cohesive transformation, such as extracting a method, introducing a value object, encapsulating a collection, or separating an infrastructure dependency.

Run the relevant verification immediately.

Review the resulting structure for responsibility, coupling, duplication, naming, and unnecessary abstraction.

Only after the first transformation is stable should another structural change be introduced.

This approach keeps each change understandable and makes regression diagnosis substantially easier.

## Design Relationships

The examples demonstrate a progression from local code improvement to architectural restructuring:

`duplicated rules -> centralized policy`

`large function -> cohesive functions`

`primitive data -> domain value objects`

`conditional variation -> strategy objects`

`exposed mutable state -> encapsulated collection`

`concrete infrastructure -> injected abstraction`

`direct coordination -> event-driven boundary`

These transformations are related because each reduces a different form of accidental complexity.

The objective is not to maximize the number of patterns. The objective is to make the system's responsibilities, invariants, variation points, and dependencies easier to understand and change safely.
