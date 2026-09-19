# Composition vs inheritance: coupling, reuse, and maintainability

## Introduction

Composition and inheritance are two fundamental mechanisms for constructing object-oriented software.

Inheritance creates a relationship between a general type and a more specialized type. A subclass receives behavior and structure from a base class and may extend or override that behavior.

Composition creates a relationship in which an object contains or collaborates with other objects. A composed object delegates part of its work to its collaborators.

The central distinction is commonly expressed as:

- **Inheritance:** an object is a specialized form of another object.
- **Composition:** an object is assembled from other objects.
- **Inheritance:** an **is-a** relationship.
- **Composition:** a **has-a** or **uses-a** relationship.

The distinction is not merely syntactic. It affects coupling, reuse, testing, extensibility, change propagation, runtime configuration, and long-term maintainability.

The three implementations in this repository demonstrate the same design principles from different perspectives:

- Python emphasizes rapid experimentation, protocols, dependency injection, delegation, and strategy composition.
- JavaScript emphasizes dynamic composition, runtime behavior replacement, asynchronous services, and object-oriented patterns in an application environment.
- C++ demonstrates explicit interfaces, ownership, polymorphism, dependency boundaries, resource management, and an industry-style order-processing architecture.

---

## Core terminology

### Class

A class defines a structure and behavior from which objects can be created.

Examples include `Order`, `Employee`, `Inventory`, `Checkout`, and `PaymentGateway`.

### Object

An object is an instance of a class with its own state and behavior.

For example, an `Order` object can contain customer information and a collection of order items.

### Inheritance

Inheritance allows one type to derive from another.

In Python, `Developer(Employee)` means `Developer` inherits from `Employee`.

In JavaScript, `class Developer extends Employee` establishes the corresponding relationship.

In C++, `class Developer : public Employee` creates public inheritance.

### Composition

Composition means that an object contains or collaborates with other objects.

An `Order` contains `OrderItem` objects.

A `Checkout` contains pricing, tax, and shipping policies.

An `OrderProcessor` collaborates with inventory, payment, and logging components.

### Delegation

Delegation occurs when one object passes responsibility to another object.

For example, `ComposedReport` delegates formatting to its formatter.

### Coupling

Coupling describes how strongly one component depends on another.

A tightly coupled component knows too much about a concrete dependency or directly constructs it.

A loosely coupled component depends on a stable abstraction or protocol and receives collaborators from outside.

Lower coupling generally makes independent modification easier, although reducing coupling without a clear architectural purpose can also add unnecessary abstraction.

### Cohesion

Cohesion describes how closely related the responsibilities inside a component are.

A highly cohesive class has responsibilities that naturally belong together.

Composition is most effective when each component has a focused responsibility.

### Reuse

Reuse means applying existing behavior or functionality in multiple contexts.

Inheritance can reuse implementation from a base class.

Composition can reuse independent components by placing them into different object configurations.

### Polymorphism

Polymorphism allows code to work with different implementations through a common interface or contract.

Examples include:

- `PaymentGateway`
- `PricingStrategy`
- `TaxPolicy`
- `ShippingPolicy`
- `Logger`
- `FlightBehavior`

---

## Inheritance fundamentals

Inheritance establishes a parent-child type relationship.

The basic conceptual structure is:

`BaseType <- SpecializedType`

A developer can be modeled as an employee because a developer is an employee.

The Python implementation demonstrates this through `Employee`, `Developer`, and `Manager`.

The JavaScript implementation uses `extends`.

The C++ implementation uses public inheritance and virtual functions.

Inheritance can provide:

- shared implementation
- shared state
- common interfaces
- polymorphism
- specialized behavior
- centralized default behavior

A simple inheritance hierarchy can be easy to understand when the domain relationship is stable.

The problem begins when inheritance is used primarily as a mechanism for code reuse without a genuine subtype relationship.

---

## The is-a rule

A useful test for inheritance is:

> Does the derived object genuinely satisfy the semantic contract of the base object?

For example:

`Car is a Vehicle`

is generally meaningful.

A car can normally be passed to code expecting a vehicle because the relevant vehicle behavior remains valid.

A different relationship is:

`Car has an Engine`

This is not an inheritance relationship.

An engine is not a specialized car.

The Python and JavaScript implementations demonstrate both relationships explicitly. The C++ implementation uses the same distinction in its order-processing architecture.

---

## The has-a rule

Composition is appropriate when one object contains another object or depends on another component.

Examples include:

- `Order` has `OrderItem` objects.
- `ComposedCar` has an `Engine`.
- `Checkout` has a pricing strategy.
- `Checkout` has a tax policy.
- `Checkout` has a shipping policy.
- `OrderProcessor` has access to inventory, payment, and logging abstractions.

Composition does not necessarily mean physical ownership.

An object may own a collaborator, borrow it, reference it, or depend on it through an interface.

The exact ownership semantics depend on the language and architecture.

---

## Inheritance and implementation reuse

Inheritance can be convenient because common behavior can be placed in a base class.

The Python report hierarchy demonstrates this with:

`Report -> SalesReport`

and:

`Report -> FinancialReport`

The base class provides `header()`, `footer()`, and `render()`, while subclasses provide specialized bodies.

This can be appropriate when the rendering lifecycle is genuinely shared and subclasses are valid specialized reports.

The same approach is demonstrated in JavaScript and C++.

The advantage is that common behavior is centralized.

The cost is that the subclasses become structurally coupled to the base class.

A change to the base class may affect many descendants.

---

## Composition and implementation reuse

Composition allows reusable behavior to remain independent.

The formatter examples use:

- `PlainTextFormatter`
- `MarkdownFormatter`
- `HtmlFormatter`

A `ComposedReport` does not need to inherit from a different report class for every output format.

Instead, the report receives a formatter.

The same report can therefore be configured as:

`ComposedReport(PlainTextFormatter())`

or:

`ComposedReport(MarkdownFormatter())`

or:

`ComposedReport(HtmlFormatter())`

This is an important property of composition: behavior can often be changed without creating another subclass.

---

## Coupling

### Tight coupling

Tightly coupled code directly depends on concrete implementations.

The `TightlyCoupledInvoice` examples construct a concrete payment gateway inside the `pay()` method.

Conceptually:

`Invoice -> creates StripeLikeGateway`

This creates several dependencies:

1. The invoice knows the concrete gateway.
2. The invoice knows how to construct it.
3. The invoice cannot easily select another gateway.
4. Tests require knowledge of the concrete implementation.
5. Changes to gateway construction can affect the invoice.

The class has therefore taken on a responsibility that does not belong to invoice calculation itself.

### Looser coupling

The alternative is dependency injection.

The invoice receives a `PaymentGateway`.

Conceptually:

`Invoice -> PaymentGateway`

The concrete implementation can be:

- a production gateway
- a test gateway
- a sandbox gateway
- a regional gateway
- a future provider

The invoice does not need to know which concrete implementation is being used.

---

## Dependency injection

Dependency injection means providing an object's dependencies from outside rather than making the object construct those dependencies itself.

The three implementations demonstrate constructor injection.

Python:

`Invoice(amount, gateway)`

JavaScript:

`new Invoice(amount, gateway)`

C++:

`OrderProcessor(inventory, paymentGateway, logger)`

Constructor injection has several useful properties:

- dependencies are explicit
- required collaborators exist at construction time
- tests can provide substitutes
- configuration remains outside business logic
- concrete implementations can be replaced

Dependency injection does not automatically guarantee good architecture. The injected dependency should also have a meaningful contract.

---

## Dependency inversion

A high-level component should avoid depending directly on unnecessary implementation details.

Instead, both high-level and low-level components can communicate through abstractions.

For example:

`OrderProcessor -> PaymentGateway`

is more flexible than:

`OrderProcessor -> StripeImplementation`

The Python `Protocol` types, JavaScript object contracts, and C++ abstract classes demonstrate different ways of expressing this idea.

C++ makes the distinction especially explicit because unrelated concrete classes do not automatically satisfy an interface merely because they happen to provide methods with similar names.

The C++ case study therefore evolves from concrete dependencies to explicit interface-based ports.

---

## Why inheritance creates coupling

A subclass depends on the structure and behavioral assumptions of its base class.

Consider:

`BaseConfiguration`

with a `timeout` field and a `connect()` method.

Subclasses inherit those assumptions.

If the base class changes:

- method behavior can change
- initialization requirements can change
- protected state can change
- invariants can change
- subclass overrides may become incorrect

The larger and deeper the inheritance hierarchy, the more difficult it can become to determine the consequences of a base-class change.

This is one reason deep inheritance trees are generally harder to maintain than small, stable hierarchies.

---

## The fragility of deep inheritance

A hierarchy such as:

`LevelOne -> LevelTwo -> LevelThree -> LevelFour`

creates a chain of implementation dependencies.

A method in the fourth level may rely on behavior supplied by all previous levels.

The problems become more serious when:

- multiple levels override the same method
- subclasses call `super`
- base classes contain mutable state
- constructors have complicated requirements
- protected members are widely used
- unrelated features are placed in one hierarchy

The C++ example intentionally demonstrates the mechanics of such a hierarchy while keeping it small enough to inspect.

---

## Liskov substitution and inheritance

A derived type should preserve the expectations established by its base type.

The bird example illustrates a common inheritance error.

Suppose:

`FlyingBird`

defines `fly()`.

If `Penguin` inherits from `FlyingBird` but cannot implement meaningful flying behavior, the hierarchy communicates an incorrect contract.

The implementation demonstrates the resulting failure.

The problem is not that overriding a method is inherently bad.

The problem is that the abstraction itself is incorrect.

A better model separates the capability of flying from the broader concept of being a bird.

---

## Capability composition

The composition-based bird model introduces:

- `CanFly`
- `CannotFly`
- `BirdWithFlightBehavior`

The bird contains a flight behavior.

This makes the capability independently replaceable.

An eagle can be configured with `CanFly`.

A penguin can be configured with `CannotFly`.

The model no longer requires every bird to inherit from a flying-bird type.

This technique generalizes to many domains:

- payment capability
- export capability
- compression capability
- authentication capability
- caching capability
- notification capability
- storage capability

---

## Strategy pattern

The pricing examples implement a strategy-oriented design.

The cart does not determine every possible pricing rule through a large conditional statement.

Instead, pricing is delegated to an object implementing a common contract.

Examples include:

- `RegularPricing`
- `TenPercentDiscount`
- `TwentyPercentDiscount`

The same `ShoppingCart` can use different strategies.

This is composition because the cart contains a pricing collaborator rather than inheriting from a different cart class for every pricing rule.

The strategy can also be changed at runtime.

---

## Composition avoids subclass explosion

Suppose a system needs:

- normal pricing
- discounted pricing
- premium pricing

and each pricing mode must also support:

- email notifications
- SMS notifications
- push notifications

Inheritance can produce a growing combination of subclasses.

Composition allows the independent dimensions to remain separate.

One component can handle pricing.

Another can handle notification.

Another can handle tax.

Another can handle shipping.

A system can then combine them.

This is often called favoring composition over inheritance.

The phrase is not an absolute prohibition against inheritance. It is a design heuristic intended to avoid using inheritance where independent behavioral variation would be more naturally represented through composition.

---

## The checkout example

The checkout system combines three policies:

- pricing
- tax
- shipping

The checkout itself does not implement every possible pricing, tax, or shipping rule.

Instead, it receives policies.

Conceptually:

`Checkout -> PricingStrategy`

`Checkout -> TaxPolicy`

`Checkout -> ShippingPolicy`

This gives each policy a focused responsibility.

A new shipping rule does not require modification of the checkout algorithm.

A new tax rule does not require a new checkout subclass.

A new pricing rule can be implemented independently.

This structure reduces coupling between independent business rules.

---

## Maintainability

Maintainability is the ease with which software can be:

- understood
- modified
- tested
- corrected
- extended
- refactored
- deployed safely

Composition can improve maintainability when components have small responsibilities and clear contracts.

Inheritance can improve maintainability when a stable hierarchy represents a genuine domain taxonomy.

Neither mechanism is automatically maintainable.

A badly designed composition system can contain excessive interfaces and indirection.

A carefully designed inheritance hierarchy can be concise and highly readable.

The relevant question is whether the chosen relationship accurately represents the variation and dependencies in the domain.

---

## Change propagation

One important maintainability concern is change propagation.

Suppose a base class changes.

All subclasses may need to be inspected.

Suppose a strategy implementation changes.

Only users of that strategy may need attention.

This is not an absolute rule because dependencies can be indirect, but composition often provides smaller change boundaries when behaviors are independently encapsulated.

A useful architectural question is:

> If this behavior changes, how many unrelated components must change with it?

The answer provides practical information about coupling.

---

## Coupling dimensions

Coupling is not a single numerical property.

Important forms include:

### Concrete coupling

A class directly depends on a particular implementation.

Example:

`Invoice -> StripeLikeGateway`

### Structural coupling

A subclass depends on the internal structure of a base class.

### Temporal coupling

One operation must happen before another for the system to work correctly.

### Data coupling

Components depend on particular data formats or structures.

### Control coupling

One component passes control information that determines another component's behavior.

### Platform coupling

A component depends on a particular runtime, operating system, library, or infrastructure mechanism.

Good architecture does not attempt to eliminate all coupling. Software components must communicate.

The objective is to make important dependencies explicit, stable, and appropriate.

---

## Cohesion versus coupling

A maintainable component generally benefits from:

- high cohesion
- controlled coupling

A pricing strategy should primarily calculate prices.

A logger should primarily record messages.

A payment gateway should primarily handle payment operations.

An inventory component should primarily manage stock.

When a single class performs all of these responsibilities, coupling and change impact tend to increase.

Composition provides a way to separate these responsibilities while still allowing them to cooperate.

---

## Python implementation

The Python implementation demonstrates composition using normal object references and `Protocol`.

### Protocols

Python's `Protocol` provides structural typing.

A class does not necessarily need to explicitly inherit from a protocol to satisfy its expected interface.

For example, an object with:

`charge(amount)`

can be used where the `PaymentGateway` protocol is expected if its structure satisfies that contract.

This supports flexible composition.

### Dataclasses

`Customer`, `OrderItem`, and `Money` use dataclasses where appropriate.

This keeps value-oriented data models concise.

`Money` uses `frozen=True` to model an immutable value object.

### Dependency injection

`Invoice`, `OrderProcessor`, and `Checkout` receive collaborators.

This separates object construction from business operations.

### Strategy composition

Pricing, tax, and shipping policies are independently replaceable.

### Testing

`RecordingGateway`, `SilentLogger`, and `FakeInventory` demonstrate test doubles.

The goal is to test an object without requiring every production dependency.

---

## JavaScript implementation

JavaScript provides a different perspective because object behavior is dynamically composed.

### Classes and extends

JavaScript supports conventional class inheritance with `extends`.

The `Employee`, `Developer`, and `Manager` hierarchy demonstrates ordinary inheritance.

### Object composition

JavaScript objects can contain other objects without formal interface declarations.

The formatter, strategy, notification, serializer, and checkout examples use this mechanism.

### Runtime replacement

A strategy can be replaced during execution.

For example, the shopping cart can switch from regular pricing to discounted pricing.

This is one of the practical strengths of composition.

### Asynchronous composition

The notification and payment examples use `async` and `await`.

This demonstrates that composition is not restricted to synchronous objects.

A service can compose asynchronous collaborators such as:

- network clients
- payment services
- message queues
- databases
- notification providers

### Dynamic contracts

JavaScript does not require a language-level interface declaration for every collaborator.

This provides flexibility but also means that incorrect contracts may be detected later at runtime.

Tests, documentation, validation, and disciplined design therefore remain important.

---

## C++ implementation

The C++ implementation models an order-processing platform.

The main components are:

- `Customer`
- `Product`
- `OrderItem`
- `Order`
- `PaymentGateway`
- `Logger`
- `Inventory`
- `PricingStrategy`
- `TaxPolicy`
- `ShippingPolicy`
- `Checkout`
- `OrderProcessor`

This is a realistic example of using multiple independent policies in a business system.

### Abstract classes

C++ uses abstract classes with pure virtual functions to define explicit polymorphic contracts.

For example, `PaymentGateway` defines `charge()`.

Different implementations can provide different payment behavior.

### Virtual dispatch

A pointer or reference to a base class can refer to a derived implementation.

The selected virtual function is determined at runtime.

This provides runtime polymorphism.

### Ownership

The checkout implementation uses `std::unique_ptr` for owned strategy objects.

This communicates ownership explicitly.

The order processor uses references because the processor does not own its collaborators.

This distinction is important in C++.

### Interface-based dependencies

The C++ case study demonstrates why interfaces should be defined at the correct architectural boundary.

An unrelated concrete type cannot safely substitute for `Inventory` merely because it has similarly named methods.

The later `InventoryPort` abstraction provides a proper interface.

---

## C++ memory and ownership considerations

Composition in C++ requires careful consideration of ownership.

Common choices include:

- direct member objects
- references
- pointers
- `std::unique_ptr`
- `std::shared_ptr`
- `std::weak_ptr`

Direct members are useful when the containing object owns the contained value and their lifetimes are naturally identical.

A reference is useful when the object borrows another object and does not own it.

`std::unique_ptr` expresses exclusive ownership.

`std::shared_ptr` expresses shared ownership but should not be used merely because it is convenient.

`std::weak_ptr` can help represent non-owning references in shared-ownership graphs.

The ownership model should follow the actual lifetime relationship.

---

## Composition versus inheritance comparison

| Concern | Inheritance | Composition |
|---|---|---|
| Primary relationship | Is-a | Has-a / uses-a |
| Reuse mechanism | Base implementation | Delegation and collaboration |
| Coupling | Often stronger | Often more localized |
| Runtime behavior replacement | Usually limited | Usually straightforward |
| Multiple independent behaviors | Can create subclass combinations | Natural through separate collaborators |
| Testing | May require hierarchy awareness | Collaborators can often be replaced |
| Extension | Subclassing | New component implementation |
| Runtime configuration | Less natural | Natural |
| Deep structures | Can become difficult to manage | Usually avoids inheritance depth |
| Domain taxonomy | Strong fit | Not always necessary |
| Behavioral capabilities | Often awkward | Strong fit |
| Ownership | Language-dependent | Language-dependent |
| Risk | Fragile base classes and rigid hierarchies | Excessive indirection or abstraction |

The table describes tendencies rather than absolute rules.

---

## When inheritance is appropriate

Inheritance is useful when all of the following are reasonably true:

1. There is a genuine subtype relationship.
2. The base abstraction has a stable contract.
3. Derived types preserve the behavioral expectations of the base type.
4. Shared behavior is genuinely common.
5. The hierarchy is unlikely to become a collection of unrelated responsibilities.
6. Polymorphism through the base type provides a meaningful benefit.

Examples can include:

- domain entities with stable taxonomies
- framework extension points
- controlled plugin hierarchies
- mathematical abstractions
- GUI component hierarchies
- language-defined polymorphic interfaces

Inheritance should not be selected merely because two classes share a few lines of code.

---

## When composition is appropriate

Composition is especially useful when:

- behavior changes independently
- behavior must be selected at runtime
- multiple capabilities must be combined
- collaborators have separate responsibilities
- dependencies should be replaceable
- testing requires substitutes
- configuration varies between deployments
- the relationship is has-a or uses-a rather than is-a

Examples include:

- payment providers
- storage backends
- serializers
- pricing policies
- authentication mechanisms
- logging implementations
- notification channels
- caching strategies
- database adapters

---

## Common mistake: inheritance for code reuse

Consider two classes that share one utility method.

It may be tempting to make one class inherit from the other.

This can create an incorrect semantic relationship.

If `ReportGenerator` and `EmailSender` both need string normalization, neither should inherit from the other merely to reuse that method.

A separate utility or collaborator is usually a more accurate model.

The purpose of inheritance should primarily be type specialization and polymorphic substitution, not simply copying implementation.

---

## Common mistake: giant base classes

A base class containing dozens of unrelated methods can force subclasses to inherit behavior they do not need.

This produces:

- unnecessary coupling
- unclear responsibilities
- difficult testing
- fragile overrides
- large change surfaces

Composition allows separate capabilities to remain separate.

---

## Common mistake: subclass explosion

A system can become difficult to maintain when every variation is represented by a subclass.

For example:

`EmailDiscountedCart`

`SmsDiscountedCart`

`PushDiscountedCart`

`EmailPremiumCart`

`SmsPremiumCart`

`PushPremiumCart`

The combinations multiply.

Separate strategies and collaborators can represent the independent dimensions more cleanly.

---

## Common mistake: excessive composition

Composition also has a failure mode.

A design can become unnecessarily fragmented:

`OrderService -> PricingFacade -> PricingAdapter -> PricingStrategyFactory -> PricingImplementation`

If every two-line operation receives an interface and several wrappers, understanding the execution path becomes difficult.

The objective is not maximum composition.

The objective is appropriate separation.

Abstraction should have a reason.

---

## Common mistake: confusing interfaces with abstraction quality

An interface does not automatically produce good architecture.

An interface with twenty unrelated methods is still a poor abstraction.

Good interfaces generally have:

- clear responsibility
- meaningful names
- coherent behavior
- stable expectations
- minimal unnecessary dependencies

The examples use small interfaces such as `PaymentGateway`, `Logger`, `PricingStrategy`, and `TaxPolicy`.

---

## Edge cases

### Invalid quantities

The Python, JavaScript, and C++ implementations reject zero or negative quantities.

This prevents nonsensical inventory and order operations.

### Negative prices

Prices are validated before processing.

Negative prices may have legitimate meanings in some accounting systems, but such semantics should be explicit rather than accidental.

### Invalid tax rates

Tax and discount rates are restricted to meaningful ranges in the examples.

### Empty identifiers

The implementations validate empty product and recipient values where appropriate.

### Currency mismatch

The `Money` value objects reject addition of different currencies.

### Insufficient inventory

Inventory reservation fails when the requested quantity exceeds available stock.

### Invalid subtype behavior

The penguin example demonstrates an architectural failure caused by an unsuitable inheritance relationship.

---

## Exceptions and error handling

Validation should occur close to the boundary where invalid data enters a component.

The implementations use exceptions for invalid state and failed operations.

Examples include:

- `ValueError` in Python
- `Error` in JavaScript
- `std::invalid_argument` in C++
- `std::runtime_error` in C++

Production systems should distinguish between expected business failures and unexpected programming errors.

Error handling should also preserve useful diagnostic information without exposing sensitive implementation details.

---

## Testing and replaceable dependencies

Composition supports testing because collaborators can be replaced.

The examples include:

- `MockPaymentGateway`
- `RecordingGateway`
- `SilentLogger`
- `FakeInventory`
- `MemoryLogger`

A test can therefore verify the behavior of a service without invoking a real payment provider or production logger.

This is an important maintainability benefit.

The class under test can be isolated from infrastructure.

---

## Performance considerations

Composition itself does not automatically make a system slower.

The cost depends on:

- object creation
- dynamic dispatch
- memory layout
- cache behavior
- allocation frequency
- algorithmic complexity
- number of calls
- abstraction implementation

The examples use simple O(n) operations for order totals.

The number of order items determines the traversal cost.

A design should not sacrifice correctness and maintainability for extremely small abstraction overhead without evidence that the overhead matters.

Performance-sensitive systems should measure actual workloads.

---

## Dynamic dispatch

Inheritance and interface-based composition may use dynamic dispatch.

Python method lookup is dynamic.

JavaScript method dispatch is dynamic.

C++ virtual functions may perform indirect calls through virtual dispatch mechanisms.

The cost of an indirect call is usually small relative to expensive operations such as network requests or database queries, but high-frequency low-level code may require more detailed analysis.

Performance decisions should be based on measurement rather than assumptions.

---

## Security considerations

Composition can help security by isolating sensitive responsibilities.

For example:

- payment operations can be isolated behind a gateway interface
- authentication can be isolated behind an authentication component
- authorization can be represented as a policy
- logging can be separated from business logic
- input validation can be centralized at appropriate boundaries

The architecture does not itself guarantee security.

Security still requires:

- input validation
- authorization checks
- secure credential handling
- least privilege
- secure transport
- correct error handling
- dependency management
- auditing

Avoid allowing an abstraction boundary to become a false assumption that a component is automatically trusted.

---

## Maintainability and testing relationship

A component that has fewer independent dependencies is often easier to test.

For example:

`Checkout(pricing, tax, shipping)`

can be tested with simple policy implementations.

The test does not need to construct an entire production infrastructure.

This reduces test setup complexity and makes failures easier to localize.

Composition therefore supports a useful relationship:

`small responsibilities -> replaceable collaborators -> focused tests -> easier maintenance`

This is a design tendency, not a guarantee.

---

## Dependency graphs

The implementations include simple dependency registries to illustrate coupling conceptually.

If several components depend on one component, that component has higher afferent coupling.

For example:

`AdminPanel -> OrderProcessor`

`CustomerPortal -> OrderProcessor`

means `OrderProcessor` has multiple incoming dependencies.

High incoming dependency counts are not automatically bad.

A stable, well-designed abstraction may intentionally have many clients.

The concern is whether changes to that component unnecessarily disrupt those clients.

---

## Afferent and efferent coupling

### Afferent coupling

Afferent coupling represents incoming dependencies.

It asks:

> How many other components depend on this component?

### Efferent coupling

Efferent coupling represents outgoing dependencies.

It asks:

> How many other components does this component depend on?

A component with many incoming dependencies should generally have a stable contract because changes can affect many consumers.

A component with many outgoing dependencies may be difficult to test and maintain because it has many external assumptions.

---

## Reuse: inheritance versus composition

Inheritance reuses implementation by receiving behavior from a base class.

Composition reuses implementation by collaborating with an existing object.

Inheritance tends to bind reuse to a type hierarchy.

Composition tends to bind reuse to a collaboration relationship.

For behavior that should be independently reused, configured, or replaced, composition is often more flexible.

For a stable family of substitutable types, inheritance can express the domain relationship more directly.

---

## Runtime configuration

One major advantage of composition is runtime configuration.

A shopping cart can receive one pricing strategy today and another tomorrow.

A notification service can receive email, SMS, or push behavior.

A report can receive a text, Markdown, or HTML formatter.

The containing object does not need a new subclass for each configuration.

This is particularly valuable in applications where behavior is controlled by configuration, deployment environment, customer plan, or runtime state.

---

## Compile-time versus runtime concerns

C++ provides stronger compile-time type checking than Python and ordinary JavaScript.

This can expose architectural mistakes earlier.

For example, the C++ case study demonstrates that a class with similar method names is not automatically a substitute for another unrelated concrete class.

An explicit interface solves that problem.

Python protocols can communicate intended structure to type checkers while remaining flexible at runtime.

JavaScript generally discovers many contract violations during execution unless additional static tooling is used.

The three languages therefore demonstrate different trade-offs between flexibility and explicitness.

---

## Design decision process

When deciding between inheritance and composition, examine the relationship first.

Ask:

1. Is this genuinely an is-a relationship?
2. Does the derived type preserve the base contract?
3. Is the behavior expected to vary independently?
4. Will the behavior need runtime replacement?
5. Would subclasses multiply combinations?
6. Does the component need to be tested independently?
7. Does the containing object naturally own or use the collaborator?
8. Is the abstraction stable?
9. Would a base-class change affect many unrelated components?
10. Does the design remain understandable after future extensions?

These questions help identify whether inheritance or composition represents the actual design.

---

## Architectural principles demonstrated

The implementations illustrate several broader object-oriented principles.

### Single Responsibility Principle

Separate pricing, tax, shipping, logging, payment, inventory, and formatting responsibilities.

### Open-Closed Principle

New strategy implementations can often be added without modifying the code that consumes the strategy.

### Liskov Substitution Principle

Derived classes should preserve the contract of their base classes.

The problematic `Penguin` hierarchy demonstrates what happens when that principle is violated.

### Interface Segregation Principle

Small focused interfaces such as `Logger` and `PaymentGateway` avoid forcing clients to depend on unrelated operations.

### Dependency Inversion Principle

High-level services should communicate through appropriate abstractions rather than unnecessary concrete implementation details.

---

## Practical applications

### E-commerce

Composition is useful for:

- pricing rules
- tax policies
- payment providers
- shipping providers
- inventory systems
- notification channels

### Financial software

Composition can represent:

- valuation strategies
- risk models
- fee policies
- tax rules
- data providers
- execution mechanisms

### Cloud systems

Composition can represent:

- storage adapters
- message publishers
- authentication providers
- monitoring clients
- retry policies
- serialization formats

### Enterprise applications

Composition can isolate:

- repositories
- service clients
- business rules
- audit logging
- authorization
- workflow policies

### User interfaces

Composition can represent:

- rendering strategies
- input behaviors
- validation policies
- accessibility behaviors
- data sources

---

## Production considerations

A production architecture should consider more than inheritance versus composition.

Important concerns include:

- API stability
- observability
- logging
- error classification
- dependency lifecycle
- configuration management
- security boundaries
- performance
- testing
- deployment
- backward compatibility
- versioning
- failure recovery

Composition can make these concerns easier to isolate, but it does not remove the need to design them explicitly.

---

## Practical distinction

A useful conceptual distinction is:

**Inheritance answers:**

> What kind of thing is this?

**Composition answers:**

> What does this thing use or contain?

If a `Developer` is an `Employee`, inheritance can be appropriate.

If an `OrderProcessor` uses an `Inventory`, a `PaymentGateway`, and a `Logger`, composition is generally a natural representation.

If an object can gain or lose a capability independently, composition is often a better model than subclassing.

---

## Final design guidance

Inheritance and composition are complementary mechanisms rather than mutually exclusive technologies.

Inheritance is useful for genuine subtype relationships with stable behavioral contracts.

Composition is useful for assembling independent capabilities and isolating change.

Coupling should not be eliminated completely. Dependencies are necessary for software components to collaborate. The objective is to control the dependency structure so that changes remain understandable and localized.

A maintainable design therefore focuses on:

- accurate relationships
- stable contracts
- focused responsibilities
- replaceable dependencies
- explicit ownership
- testable components
- controlled coupling
- appropriate abstraction

The most important practical distinction is not whether a design uses inheritance or composition. It is whether the chosen relationship accurately represents the behavior, responsibility, and expected future variation of the system.
