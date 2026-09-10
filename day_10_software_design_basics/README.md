# Software design basics: modularity, abstraction, and encapsulation

## Introduction

Software design is the process of organizing software so that its behavior, responsibilities, dependencies, and internal structure remain understandable and manageable as the system evolves.

Correct output is only one measure of software quality. A program also needs a structure that supports maintenance, testing, debugging, security, performance, reuse, and controlled change.

Three foundational concepts are:

- **Modularity**: dividing software into meaningful components with clear responsibilities.
- **Abstraction**: exposing useful behavior while hiding unnecessary implementation details.
- **Encapsulation**: grouping state and behavior together while controlling how internal state can be accessed or changed.

These concepts are related but describe different aspects of design.

## What software design tries to achieve

A well-designed system generally aims to provide:

- Clear responsibilities
- Understandable components
- Controlled dependencies
- Reusable behavior
- Testable units
- Valid internal state
- Stable interfaces
- Limited exposure of implementation details
- Predictable error handling
- Controlled extensibility
- Appropriate performance
- Appropriate security boundaries

Good design is contextual. A small script may need only a few well-designed functions, while a large application may require multiple modules, interfaces, layers, repositories, services, and domain objects.

The goal is not maximum architectural complexity. The goal is an appropriate structure for the actual problem.

## Modularity

Modularity means dividing a program into separate components.

A component can be a:

- Function
- Class
- Python module
- Package
- Service
- Subsystem

The Python script demonstrates modularity first through separate functions such as validation, subtotal calculation, tax calculation, and total calculation.

Instead of placing all operations inside one large function, each operation receives a focused responsibility.

For example, validation can be changed independently from tax calculation, and tax calculation can be changed independently from output formatting.

### Benefits of modularity

Modularity can provide:

- Easier comprehension
- Easier testing
- Easier debugging
- Better reuse
- More controlled changes
- Reduced accidental dependencies
- Clearer ownership of responsibilities

### Modularity does not mean fragmentation

Creating many tiny functions or classes does not automatically improve design.

A module should represent a meaningful concept or responsibility. Excessive fragmentation can introduce:

- Unnecessary indirection
- More dependencies
- More files
- More interfaces
- More cognitive overhead

The appropriate level of modularity depends on the complexity of the problem.

## Cohesion

Cohesion describes how closely the responsibilities within a component belong together.

### High cohesion

A highly cohesive component has a focused purpose.

An invoice calculator that handles invoice-related calculations is cohesive because its operations belong to the same conceptual responsibility.

### Low cohesion

A low-cohesion component combines unrelated responsibilities.

A class containing invoice calculations, email delivery, image resizing, CSV parsing, and database administration is difficult to understand because its responsibilities have little conceptual relationship.

High cohesion generally improves:

- Readability
- Testability
- Maintainability
- Reuse
- Change isolation

## Coupling

Coupling describes how strongly components depend on one another.

High coupling occurs when one component knows many details about another component's implementation.

Low coupling occurs when components communicate through small, stable interfaces.

Coupling cannot be eliminated completely. Components must communicate to form a functioning system.

The design objective is to keep coupling intentional and manageable.

### High coupling example

If an order service directly constructs a particular database implementation, the order service becomes dependent on that implementation.

Changing the database technology may require changing the business logic.

### Lower coupling

A better structure can make the order service depend on a repository abstraction.

The concrete repository can then be replaced without changing the high-level order-processing logic.

## Separation of concerns

Separation of concerns means keeping different responsibilities apart.

Common concerns include:

- Input handling
- Validation
- Business rules
- Calculations
- Persistence
- Notifications
- Presentation
- External communication

The script demonstrates this using separate order, repository, notification, and service components.

The purpose is not to create a rigid number of layers. The purpose is to prevent unrelated responsibilities from becoming unnecessarily intertwined.

## Abstraction

Abstraction describes what a component does without requiring callers to understand every implementation detail.

A caller may use an operation such as:

`make_coffee()`

without knowing how water is heated, beans are ground, or coffee is brewed.

Similarly, a payment processor can expose:

`pay(amount)`

while hiding the details of a card payment or bank transfer.

### Why abstraction is useful

Abstraction can:

- Reduce cognitive load
- Hide implementation details
- Create stable interfaces
- Allow implementation replacement
- Improve reuse
- Support testing

### Good abstraction

A good abstraction represents a meaningful concept and exposes operations that callers genuinely need.

### Too little abstraction

Too little abstraction forces callers to understand internal details.

For example, requiring every caller of a cache to manipulate its internal dictionary exposes implementation details unnecessarily.

### Too much abstraction

Excessive abstraction creates unnecessary interfaces, classes, factories, or layers.

An abstraction should exist because it provides meaningful value, not merely because an architectural pattern is available.

## Encapsulation

Encapsulation combines state and the operations that control that state.

The Python script demonstrates encapsulation with a bank account.

An account should not allow arbitrary code to set its balance to an invalid value.

Instead, operations such as:

- `deposit()`
- `withdraw()`

control changes to the balance.

This allows the class to enforce business rules.

### Encapsulation and invariants

An invariant is a condition that should remain true for an object.

Examples include:

- A bank balance cannot become negative.
- An order quantity must be positive.
- A product price cannot be negative.
- A temperature in Kelvin cannot be below absolute zero.
- An order cannot move from shipped back to created.

Encapsulation provides a natural place to enforce these rules.

## Python's approach to encapsulation

Python does not enforce private members in exactly the same way as some languages.

Common conventions include:

- `_name`: conventionally internal
- `__name`: name mangling that reduces accidental access
- `@property`: controlled access to attributes

The underscore convention is not a security mechanism.

Encapsulation is primarily about designing responsible interfaces and protecting valid object state.

## Information hiding

Information hiding focuses on preventing other parts of the system from depending on implementation details that may change.

A cache can internally use a dictionary today and a different storage mechanism later.

If callers use:

- `put()`
- `get()`
- `contains()`

they do not need to know the internal storage structure.

This allows the implementation to evolve without requiring changes throughout the application.

## Interfaces

An interface describes operations that an implementation promises to provide.

In the script, payment processing is represented through an abstract `PaymentProcessor`.

Different implementations can provide:

- Card payments
- Bank transfers

while exposing the same essential operation.

This allows higher-level code to work with the abstraction instead of knowing the concrete implementation.

## Contracts

A contract defines expected behavior.

A useful contract can specify:

- Accepted inputs
- Returned values
- Possible exceptions
- State changes
- Invariants
- Preconditions
- Postconditions

For example, a withdrawal operation can specify that the amount must be positive and cannot exceed the available balance.

Contracts make component behavior easier to understand and test.

## Abstract base classes

Python's `ABC` and `abstractmethod` can be used when a formal inheritance-based interface is useful.

An abstract base class can define operations that subclasses must implement.

This is appropriate when the design benefits from an explicit hierarchy.

It is not necessary for every abstraction.

## Protocols and structural typing

Python's `Protocol` supports structural typing.

A component does not necessarily need to inherit from a particular base class. It can satisfy an interface by providing the required operations.

This fits Python's duck-typing model.

For example, a task can accept any logger with a compatible `write()` operation.

This can reduce unnecessary inheritance relationships.

## Composition

Composition means constructing a larger component from smaller components.

An order service can contain or use:

- A repository
- A pricing policy
- A notification service

Each component performs a focused responsibility.

Composition often provides flexibility without requiring deep inheritance hierarchies.

### Composition versus inheritance

Inheritance represents an "is-a" relationship and can be useful when a genuine subtype relationship exists.

Composition represents a "has-a" or "uses-a" relationship.

For many application designs, composition is easier to change because individual collaborators can be replaced independently.

## Dependency injection

Dependency injection means supplying a component's dependencies from outside.

Instead of a service creating its own database connection or notification provider, the dependency is supplied to it.

This has several benefits:

- Dependencies are explicit.
- Implementations can be replaced.
- Tests can use test doubles.
- Configuration is easier.
- Coupling is reduced.

The `UserService`, `OrderService`, and other examples in the script use constructor injection.

### Constructor injection

Constructor injection supplies required dependencies when an object is created.

This is often preferable when the dependency is essential for the object's operation because the object cannot be created without it.

## Dependency inversion

Dependency inversion reduces dependence of high-level business logic on concrete low-level implementations.

Instead of:

`Business service -> concrete database`

the structure can become:

`Business service -> repository abstraction <- concrete database`

The high-level policy depends on a stable abstraction.

This is especially useful when infrastructure is likely to change or when the high-level logic needs isolated testing.

## Separation of stable and volatile details

A useful design question is:

> What is likely to change?

Examples include:

- Database technology
- Payment provider
- Notification provider
- Tax rules
- User interface
- External API

If a likely-changing implementation detail is deeply embedded inside business logic, future changes become expensive.

A design can isolate that volatility behind a suitable boundary.

## Single Responsibility Principle

The Single Responsibility Principle is commonly expressed as the idea that a component should have one primary responsibility and one reason to change.

This does not mean a class must contain exactly one method.

A class can contain several closely related operations and still have one coherent responsibility.

For example, a report calculator can contain several report-related calculations without also becoming responsible for database persistence and user-interface rendering.

## Open/Closed Principle

The Open/Closed Principle describes components that are open for extension while avoiding unnecessary modification of stable existing logic.

The shape example in the script demonstrates this idea.

A `Shape` abstraction defines `area()`.

A circle and rectangle implement the abstraction.

A function that calculates the total area can operate on the abstraction without needing to know every concrete shape.

New shape implementations can be introduced without rewriting the total-area algorithm.

The principle should not be interpreted as a requirement to avoid all modification. Existing code will sometimes need to change when requirements genuinely change.

## Substitutability

A replacement implementation should honor the behavioral expectations of the abstraction it implements.

Matching method names alone is not enough.

For example, if an interface promises that `area()` returns a meaningful non-negative area, an implementation that violates those expectations is not a sound substitute even if its method signature matches.

This is the central design idea behind substitutability.

## Interface segregation

Large interfaces can force components to implement operations they do not need.

Smaller interfaces allow components to depend only on the capabilities they actually require.

For example, reading and writing can be represented as separate capabilities.

A read-only component should not need to implement a write operation merely because another component needs both.

## Immutability

An immutable object cannot be changed after creation.

The script uses frozen dataclasses and a `Money` value object to demonstrate immutable-style design.

Benefits include:

- Easier reasoning
- Reduced accidental mutation
- Predictable values
- Safer sharing
- Simpler concurrent designs

Immutability is particularly useful for value objects and configuration-like data.

## Validation

Validation should occur at meaningful system boundaries.

Potentially invalid data can enter through:

- User input
- Files
- APIs
- Databases
- Environment variables
- External services

Validation should prevent invalid information from entering sensitive business operations.

User-interface validation alone is insufficient because other callers may bypass the interface.

## State and state transitions

Encapsulation is especially important when objects have multiple states.

The order example defines states such as:

- Created
- Paid
- Shipped
- Cancelled

Only valid transitions are allowed.

This prevents callers from directly manipulating state into an invalid configuration.

State-transition rules are business rules and belong close to the domain concept they govern.

## Error handling as part of design

Errors are part of a component's interface.

A component should clearly distinguish between different types of failure, such as:

- Invalid input
- Invalid state
- Business-rule failure
- External-system failure
- Programming errors

Domain-specific exceptions can make expected business failures easier to handle.

For example, `InsufficientFundsError` communicates a specific business condition more clearly than a generic exception.

Errors should not be silently ignored when the caller needs to react to them.

## Security considerations

Software design directly affects security.

Important design principles include:

### Least privilege

A component should receive only the permissions it actually needs.

### Input validation

External input should be treated as potentially invalid.

### Encapsulation

Sensitive state should not be freely modifiable by unrelated code.

### Information hiding

Implementation details that contain sensitive behavior should not be unnecessarily exposed.

### Dependency control

Unnecessary dependencies increase the system's attack surface and maintenance burden.

### Secret management

Passwords, tokens, and API keys should not be embedded directly in source code.

### Safe error handling

Errors should not unnecessarily expose internal implementation details, credentials, database information, or other sensitive data.

A private-looking Python attribute is not itself a security boundary. Actual security requires appropriate authentication, authorization, validation, isolation, and secure infrastructure.

## Performance considerations

Modularity and abstraction can introduce some runtime overhead through:

- Additional function calls
- Additional objects
- Indirection
- Interface dispatch
- Data copying
- Extra validation

These costs should be considered in performance-sensitive systems.

At the same time, good modularity can make optimization easier because individual components can be profiled, replaced, cached, or optimized independently.

Performance decisions should be based on measurement rather than assumptions.

Prematurely removing useful abstractions can make software substantially harder to maintain without producing a meaningful performance improvement.

## Choosing appropriate data types

Data types are part of software design.

The script demonstrates the difference between binary floating-point arithmetic and decimal arithmetic.

Floating-point numbers are appropriate for many scientific and engineering calculations, but decimal financial values often require `Decimal` when exact decimal representation and predictable rounding are important.

The correct data type depends on the domain and precision requirements.

## Testability

Testability is strongly influenced by design.

A component is easier to test when it has:

- Explicit dependencies
- Predictable inputs
- Predictable outputs
- Limited side effects
- Small responsibilities
- Controlled state

Dependency injection makes it possible to replace real infrastructure with test doubles.

The script demonstrates this with a fake payment processor and a recording notification service.

## Refactoring

Refactoring means changing the internal structure of software while preserving intended observable behavior.

Common refactoring techniques include:

- Extracting functions
- Extracting classes
- Renaming unclear identifiers
- Removing duplication
- Separating responsibilities
- Reducing coupling
- Introducing abstractions where justified
- Moving behavior to the component that owns the relevant concept

Tests are valuable during refactoring because they provide evidence that behavior remains correct.

## DRY

DRY means "Don't Repeat Yourself."

The principle discourages repeated representations of the same knowledge or business rule.

If the same tax rule is independently implemented in several locations, those implementations can become inconsistent.

DRY does not mean that every similar-looking line of code must be forced into a shared abstraction. Sometimes apparent duplication represents different concepts that may evolve independently.

## KISS

KISS means "Keep It Simple."

A simple design is generally preferable when it satisfies the requirements.

Complexity should have a reason.

A three-line conditional does not necessarily need a strategy hierarchy, factory, abstract base class, and dependency-injection framework.

## YAGNI

YAGNI means "You Aren't Gonna Need It."

The principle discourages implementing speculative features before there is a genuine requirement.

Premature generalization often creates:

- More code
- More concepts
- More testing requirements
- More maintenance
- More opportunities for confusion

Design should remain flexible where useful without becoming speculative.

## Factory functions

A factory can centralize object creation when object construction itself is meaningful or variable.

A factory is appropriate when:

- Construction is complex.
- The concrete implementation varies.
- Callers should not know creation details.
- Creation requires configuration or validation.

A factory is unnecessary when constructing an object is already simple and obvious.

## Design smells

Design smells are warning signs that a structure may be difficult to maintain.

Common examples include:

### God object

One class controls too much of the system.

### Long method

One method contains too much logic or too many responsibilities.

### Long parameter list

A function requires many independent arguments.

### Feature envy

One component depends heavily on another component's data or behavior.

### Shotgun surgery

One conceptual change requires edits in many unrelated locations.

### Duplicated logic

The same business rule is implemented in multiple places.

### Hidden dependency

A component silently depends on global state or internally created services.

### Leaky abstraction

An abstraction exposes details that callers should not need to understand.

### Premature abstraction

Generalized structures are introduced before a real need exists.

A design smell is not automatically a defect. Context determines whether restructuring is justified.

## Common design mistakes

### One giant class

Combining business logic, database access, networking, presentation, and validation into one class produces excessive responsibility.

### Uncontrolled mutable state

Allowing external code to change important state directly makes invariants difficult to protect.

### Excessive abstractions

Too many interfaces and layers can make a simple system difficult to understand.

### High coupling

Direct dependence on concrete implementation details makes change expensive.

### Low cohesion

Unrelated functionality placed into the same component makes responsibilities unclear.

### Global mutable state

Global state can make behavior unpredictable and tests difficult to isolate.

### Premature optimization

Optimizing without evidence can produce complex designs without meaningful performance benefits.

### Weak validation

Allowing invalid external data into business logic can produce inconsistent or insecure states.

### Inconsistent errors

Unclear exception behavior makes components difficult to use correctly.

## Layered design

A common organization for larger systems is:

- Presentation layer
- Application or service layer
- Domain layer
- Infrastructure layer

The presentation layer handles interaction and formatting.

The application layer coordinates use cases.

The domain layer represents business concepts and rules.

The infrastructure layer handles external systems such as databases, files, networks, and third-party services.

This is a conceptual model rather than a mandatory folder structure.

The important consideration is that dependencies and responsibilities should have intentional direction.

## Dependency direction

A system becomes easier to change when high-level business rules do not unnecessarily depend on low-level implementation details.

A conceptual structure can be:

Presentation → Application → Domain

with infrastructure connected through suitable abstractions.

This reduces the risk that a database, notification mechanism, or external service dictates the structure of core business logic.

## Public API design

Every public function, method, attribute, or class can become a dependency for other code.

Once external code depends on an implementation detail, changing it may become difficult.

A small and meaningful public API provides more freedom to change internal implementation later.

Good public APIs generally have:

- Clear names
- Predictable behavior
- Explicit inputs
- Defined outputs
- Appropriate validation
- Meaningful error behavior
- Minimal unnecessary exposure

## Naming as a design tool

Names communicate structure.

Prefer names such as:

`calculate_monthly_payment`

over:

`calc`

Prefer:

`customer_repository`

over:

`repo1`

Clear naming reduces the amount of documentation required to understand code.

Naming also helps reveal design problems. If a class cannot be given a concise, meaningful description, its responsibilities may be too broad.

## Edge cases

Important edge cases demonstrated in the script include:

- Empty collections
- Zero values
- Negative values
- Invalid quantities
- Invalid prices
- Unsupported notification channels
- Invalid order IDs
- Invalid state transitions
- Insufficient bank balances
- Zero-interest loans
- Invalid temperatures
- Floating-point precision
- Attempts to mutate immutable values

Edge cases are part of software design rather than an afterthought.

## Design trade-offs

There is no universally perfect software architecture.

Increasing abstraction can improve flexibility but also increase complexity.

Increasing modularity can improve maintainability but introduce additional interfaces and dependencies.

Increasing validation can improve correctness but requires additional processing and code.

Increasing encapsulation can improve state safety but may make some operations less direct.

The appropriate choice depends on:

- Requirements
- Expected change
- Application size
- Team familiarity
- Testing requirements
- Performance requirements
- Security requirements
- Reliability requirements
- Operational constraints

## Modularity, abstraction, and encapsulation compared

| Concept | Primary concern | Example |
|---|---|---|
| Modularity | How software is divided | Separate order processing and notification |
| Abstraction | What a component exposes | `PaymentProcessor.pay()` |
| Encapsulation | How state is controlled | `BankAccount.withdraw()` |
| Information hiding | Which implementation details remain private | Cache users call `get()` rather than accessing storage directly |
| Composition | How components are combined | Service uses repository and notifier |
| Dependency injection | How dependencies are supplied | Repository passed to a service |
| Dependency inversion | Which direction dependencies point | Business logic depends on repository abstraction |

## Practical design review

Before considering a component well designed, useful questions include:

- Does the component have a clear responsibility?
- Are closely related responsibilities kept together?
- Are unrelated responsibilities separated?
- Are important business rules easy to locate?
- Are implementation details hidden appropriately?
- Is the public interface small and meaningful?
- Can dependencies be replaced during testing?
- Are invalid states prevented?
- Is external input validated?
- Is dependency direction intentional?
- Are abstractions justified by real requirements?
- Can another developer understand the component without reconstructing the entire system?
- Can likely changes be made without modifying many unrelated components?
- Are performance-sensitive areas known?
- Are security-sensitive operations controlled?
- Are error conditions clearly defined?
- Is shared mutable state minimized?

## Real-world relevance

These principles apply across software domains.

### Web applications

Modularity can separate:

- Routing
- Authentication
- Business logic
- Database access
- External APIs
- Presentation

Abstraction can hide database-specific details behind repositories or data-access interfaces.

Encapsulation can protect domain state and authorization-related rules.

### Financial software

Encapsulation can protect account and transaction invariants.

Abstraction can isolate payment providers and financial calculation implementations.

Modularity can separate pricing, risk calculations, persistence, reporting, and external integrations.

### Data and analytics systems

Modularity can separate:

- Data ingestion
- Validation
- Transformation
- Analysis
- Reporting

Abstraction can hide storage-specific implementation details.

Encapsulation can protect configuration and processing state.

### Machine learning systems

A pipeline can separate:

- Data loading
- Validation
- Feature preparation
- Model training
- Evaluation
- Prediction
- Monitoring

This makes individual stages easier to test and replace.

### Enterprise systems

Large systems frequently benefit from boundaries between:

- Domain logic
- Application services
- Infrastructure
- External integrations
- User interfaces

The value of these boundaries increases when the system has many developers, changing requirements, or multiple external dependencies.

## Production considerations

Production software requires more than clean class structure.

Design should also account for:

- Logging
- Monitoring
- Error reporting
- Configuration
- Dependency management
- Security controls
- Data validation
- Failure recovery
- Performance
- Scalability
- Testing
- Deployment constraints

A well-encapsulated class does not compensate for an insecure architecture, poorly controlled database access, or inadequate operational monitoring.

Software design must therefore be considered at multiple levels, from individual functions and classes to modules, packages, services, and the overall system architecture.

## Core relationship among the concepts

The three central ideas can be understood together.

**Modularity** determines how responsibilities are divided.

**Abstraction** determines what each component exposes to its users.

**Encapsulation** determines how each component protects and controls its internal state.

Together they support a broader design goal:

> Build components with focused responsibilities, meaningful interfaces, controlled state, and limited unnecessary dependencies.

The Python script demonstrates these principles progressively through functions, classes, protocols, abstract base classes, immutable value objects, dependency injection, repositories, services, validation, state transitions, test doubles, and an integrated order-processing example.
