# Object-Oriented Programming Principles

## Encapsulation, inheritance, polymorphism, and abstraction

This repository studies the four foundational principles of object-oriented programming through three complete implementations in Python, JavaScript, and C++.

The implementations are intentionally different. Python emphasizes expressive object models, properties, abstract base classes, protocols, duck typing, dataclasses, and dynamic polymorphism. JavaScript emphasizes classes, private fields, prototype relationships, asynchronous objects, iterators, symbols, and event-driven design. C++ develops a larger industry-style order-processing system using explicit interfaces, ownership models, runtime polymorphism, dependency injection, repositories, domain exceptions, and event publishing.

---

## Topic introduction

Object-oriented programming, commonly abbreviated as OOP, is a programming paradigm in which software is organized around objects that combine state and behavior.

An object can contain:

- Data representing its current state
- Operations that work on that state
- Rules controlling valid state transitions
- Relationships with other objects
- A public interface through which other parts of the program interact with it

A class is a definition from which objects can be constructed. An object is a runtime instance of a class.

The four principles covered here are:

| Principle | Central idea |
|---|---|
| Encapsulation | Keep state and its governing behavior together and control access |
| Inheritance | Specialize an existing type through a valid subtype relationship |
| Polymorphism | Allow different implementations to respond through a common interface |
| Abstraction | Expose essential behavior while hiding unnecessary implementation details |

These principles are related but are not interchangeable.

Encapsulation concerns boundaries around state and behavior.

Inheritance concerns relationships between types.

Polymorphism concerns interchangeable behavior.

Abstraction concerns what an interface exposes and what implementation details it hides.

A well-designed system can use one principle without relying heavily on another. Composition and interfaces can often provide polymorphism without deep inheritance.

---

## Fundamental OOP terminology

### Class

A class describes the structure and behavior expected from objects.

Python uses the `class` statement. JavaScript uses `class` syntax. C++ uses the `class` keyword.

A simplified conceptual structure is:

`class -> attributes/state + methods/behavior`

### Object

An object is an instance of a class.

For example, a `Dog` class may produce multiple independent objects such as `dog1` and `dog2`.

Each object can have its own state while sharing the behavior defined by its class.

### Attribute

An attribute represents object or class state.

Examples include:

- customer name
- account balance
- product price
- employee identifier
- order status

### Method

A method is behavior associated with an object or class.

Examples include:

- `deposit()`
- `withdraw()`
- `reserve()`
- `process()`
- `calculateCost()`
- `speak()`

### Constructor

A constructor establishes an object's initial state.

Python normally uses `__init__`.

JavaScript uses `constructor`.

C++ commonly uses a constructor whose name matches the class.

### Interface

An interface describes capabilities that an implementation must provide.

Python can express interfaces using abstract base classes or `Protocol`.

JavaScript commonly expresses contracts through conventions, base classes, validation, or explicit capability checks.

C++ can express interfaces strongly through abstract classes containing pure virtual functions.

---

# Encapsulation

## Definition

Encapsulation is the practice of keeping data and the operations that control that data together while establishing a controlled boundary around internal state.

The important idea is not simply "make variables private."

A stronger interpretation is:

> The object should control the rules that determine whether its state can change.

Consider a bank account.

An account should not permit arbitrary code to change its balance to an invalid value. Instead of exposing unrestricted state modification, the account can provide operations such as `deposit()` and `withdraw()`.

This gives the object responsibility for maintaining its own invariants.

---

## Encapsulation and invariants

An invariant is a condition that should remain true for a valid object.

Examples:

- Account balance cannot be negative.
- Product stock cannot be negative.
- Temperature cannot be below absolute zero.
- Order quantity must be positive.
- A completed shipment cannot return to an earlier state.
- A payment amount must be positive.

An encapsulated class protects these rules.

For example, the Python `BankAccount` class stores balance internally and modifies it through `deposit()` and `withdraw()`.

The JavaScript version uses the `#balance` private field.

The C++ implementation uses private data members and public operations.

The languages implement the boundary differently, but the design objective is similar.

---

## Python encapsulation

The Python implementation demonstrates several levels of access conventions.

`name` is public.

`_balance` communicates that the attribute is intended for internal use.

`__transaction_count` triggers Python name mangling.

Properties expose controlled access through methods that look like attributes.

The `Temperature` class demonstrates a property setter that validates values before changing internal state.

This is useful because the public interface can remain simple:

`temperature.celsius = 25`

while the class still enforces:

`temperature.celsius >= -273.15`

---

## JavaScript encapsulation

Modern JavaScript supports true class private fields using the `#` syntax.

The JavaScript `BankAccount` implementation uses:

`#balance`

and:

`#transactionCount`

These fields cannot be accessed directly from outside the class body.

JavaScript getters expose controlled read access:

`account.balance`

The setter in `Temperature` validates assignments before changing the private field.

This is stronger than merely naming a field `_balance`, because the language enforces the private-field boundary.

---

## C++ encapsulation

C++ provides explicit access control.

The case study uses:

`private:`

for internal state.

Public methods such as `reserve()`, `restock()`, `markPaid()`, and `markShipped()` control state changes.

The external caller does not directly modify the internal order status.

This is particularly important in domain models because invalid state transitions can produce incorrect business behavior.

---

# Inheritance

## Definition

Inheritance allows one class to derive from another class.

The general relationship is:

`base class -> derived class`

or:

`parent class -> child class`

Inheritance is most appropriate when there is a genuine behavioral subtype relationship.

Examples:

- `Dog` is an `Animal`.
- `Manager` is an `Employee`.
- `CardPayment` is a `PaymentProvider`.
- `ExpressShipping` is a `ShippingProvider`.

Inheritance should not be selected merely because two classes share a few lines of implementation.

---

## Python inheritance

The Python implementation contains:

`Animal`

with subclasses:

`Dog`

and:

`Cat`

The subclasses inherit `eat()` and override `speak()`.

The `Manager` class inherits from `Employee` and uses `super()` to initialize the parent portion of the object.

Python also supports multiple inheritance. The `Service` example inherits from `LoggerMixin` and `JsonMixin`.

Python resolves multiple inheritance through the Method Resolution Order, or MRO.

The example prints the MRO using:

`Service.mro()`

This is important because method lookup can become difficult to reason about in large multiple-inheritance hierarchies.

---

## JavaScript inheritance

JavaScript classes use:

`extends`

to establish class inheritance.

A derived constructor can invoke the base constructor through:

`super(...)`

A derived method can call the parent implementation through:

`super.methodName()`

The implementation also demonstrates that JavaScript classes are built on the prototype system.

For an object created from `Dog`, methods such as `speak()` are normally found through prototype lookup rather than being copied into every object.

---

## C++ inheritance

C++ expresses inheritance with syntax such as:

`class CardPayment : public PaymentProvider`

The C++ case study uses abstract base classes as interfaces.

Concrete classes derive from those interfaces.

For example:

- `CardPayment`
- `WalletPayment`
- `BankTransferPayment`

derive from:

`PaymentProvider`

Likewise:

- `StandardShipping`
- `ExpressShipping`
- `InternationalShipping`

derive from:

`ShippingProvider`

The `override` keyword explicitly tells the compiler that a derived class is overriding a virtual function.

This improves compile-time checking.

---

# Polymorphism

## Definition

Polymorphism means that different concrete objects can be used through a common operation or interface while each object supplies its own behavior.

The caller focuses on the required capability rather than the exact implementation.

For example, an order processor can ask a payment provider to authorize a transaction without knowing whether the provider is:

- a card processor
- a wallet
- a bank transfer system

The interface remains stable while the implementation varies.

---

## Method overriding

Method overriding occurs when a subclass supplies a specialized implementation of an inherited method.

The Python example uses:

`Dog.speak()`

and:

`Cat.speak()`

Both objects can be treated as animals while producing different results.

The JavaScript example uses the same conceptual pattern.

The C++ implementation uses virtual functions and `override`.

---

## Duck typing in Python

Python has a particularly flexible form of polymorphism called duck typing.

The important question is often:

"Does this object provide the required behavior?"

rather than:

"Does this object inherit from this particular class?"

The Python implementation defines `announce_speaker()`.

The function accepts:

- `Dog`
- `Robot`
- `Parrot`

because each object provides a callable `speak()` method.

This is behavioral polymorphism.

---

## Structural typing with Protocol

Python's `Protocol` provides a type-oriented way to describe behavior.

The `Exportable` protocol requires:

`export()`

The CSV and JSON report classes can satisfy that capability without being forced into a shared inheritance hierarchy.

This is an important distinction:

Inheritance describes a class relationship.

A protocol describes a required shape or capability.

---

## C++ runtime polymorphism

C++ uses virtual functions for traditional runtime polymorphism.

A base-class pointer or reference can refer to a derived object.

For example, the order processor stores:

`std::unique_ptr<PaymentProvider>`

The concrete object can be a `CardPayment`, `WalletPayment`, or `BankTransferPayment`.

The call to:

`authorize()`

is dynamically dispatched to the correct concrete implementation.

This is one of the central uses of virtual functions in C++.

---

# Abstraction

## Definition

Abstraction means exposing the essential operations required by a client while hiding implementation details that the client does not need to know.

A payment processor may expose:

- authorize
- capture

The calling code does not need to know the internal communication mechanism used by a card network or wallet provider.

The abstraction creates a boundary between policy and implementation.

---

## Abstract classes

Python uses the `abc` module for formal abstract base classes.

The Python `PaymentProcessor` class declares abstract methods.

A concrete subclass must implement those methods before it can be instantiated.

JavaScript does not have a built-in abstract-class mechanism identical to Python's `ABC` or C++ pure virtual functions. The implementation therefore uses a base class whose methods throw errors when they are not implemented.

C++ provides a particularly explicit abstraction mechanism through pure virtual functions.

A C++ method such as:

`virtual bool authorize(double amount) = 0;`

makes the containing class abstract.

---

# Encapsulation, inheritance, polymorphism, and abstraction compared

| Principle | Primary concern | Typical mechanism |
|---|---|---|
| Encapsulation | Protecting and governing state | Private fields, properties, access modifiers |
| Inheritance | Reusing and specializing type behavior | `extends`, derived classes |
| Polymorphism | Interchangeable implementations | Overriding, interfaces, protocols, virtual functions |
| Abstraction | Defining essential capabilities | Abstract classes, interfaces, contracts |

The principles often work together.

For example, the C++ payment system uses:

1. Encapsulation to protect internal provider state.
2. Abstraction through `PaymentProvider`.
3. Inheritance to derive concrete payment providers.
4. Polymorphism to let `OrderProcessor` use any compatible provider.

---

# Composition

Composition represents a "has-a" relationship.

Examples:

- A car has an engine.
- An order has order items.
- An order item refers to a product.
- An order processor has payment, shipping, discount, repository, and event dependencies.

Composition is often preferable to inheritance when the relationship is not genuinely a subtype relationship.

The Python and JavaScript implementations use a `Car` containing an `Engine`.

The C++ implementation uses composition extensively in the order-processing system.

---

# Composition versus inheritance

| Characteristic | Inheritance | Composition |
|---|---|---|
| Relationship | Is-a | Has-a |
| Coupling | Often tighter | Often looser |
| Reuse mechanism | Type hierarchy | Contained object |
| Runtime replacement | Less flexible in many designs | Usually straightforward |
| Main risk | Fragile or overly deep hierarchies | More objects and delegation |
| Typical example | `Dog` is an `Animal` | `Car` has an `Engine` |

Inheritance is useful when the subtype must honor the behavioral contract of the base abstraction.

Composition is often useful when behavior can be supplied by interchangeable collaborators.

---

# Dependency injection

Dependency injection means supplying an object's dependencies from outside rather than making the object construct every dependency internally.

The C++ `OrderProcessor` receives:

- a payment provider
- a shipping provider
- a discount policy
- an order repository
- an event bus

The processor therefore does not need to know how those objects are created.

This improves:

- testing
- configurability
- separation of concerns
- replacement of infrastructure
- maintainability

The Python example uses an injected `AuditLogger`.

The JavaScript example uses an injected logger and injected services in the order-processing case study.

---

# Python implementation

The Python script progresses through the object model before developing more advanced designs.

## Basic objects

`Person` demonstrates:

- class definition
- constructor
- instance attributes
- instance methods
- object inspection

The object stores `name` and `age`, while `introduce()` provides behavior.

## Encapsulation

`BankAccount` demonstrates:

- internal state
- validation
- properties
- controlled state transitions
- name mangling
- custom error handling

`Temperature` demonstrates property getters and setters.

The setter is useful because it keeps validation close to the state it protects.

## Inheritance

`Animal`, `Dog`, and `Cat` demonstrate a basic hierarchy.

`Manager` demonstrates `super()`.

The multiple-inheritance example demonstrates mixins and Python's MRO.

## Polymorphism

The Python script demonstrates:

- method overriding
- duck typing
- protocols
- `singledispatch`
- operator overloading

The `Money` class implements addition, subtraction, comparison, equality, and representation.

## Abstraction

`PaymentProcessor` is an abstract base class.

`CardPayment` and `WalletPayment` provide concrete implementations.

The caller uses the common `process()` operation without knowing the details of authorization and capture.

## Composition

The `Car` and `Engine` example shows a simple "has-a" relationship.

The shipping system goes further by composing a calculator with interchangeable shipping providers.

## Value objects

`Coordinate` uses a frozen dataclass.

`Money` demonstrates an object whose identity is primarily determined by its value rather than by a database-style identity.

---

# JavaScript implementation

The JavaScript implementation focuses on object-oriented features that are especially important in modern JavaScript applications.

## Classes

`Person` demonstrates constructors, instance fields, and methods.

## Private fields

`BankAccount` uses:

`#balance`

and:

`#transactionCount`

These are genuine JavaScript private fields.

## Getters and setters

`Temperature` uses JavaScript accessors.

This permits validation while retaining property-like syntax.

## Inheritance

`Dog` and `Cat` extend `Animal`.

The implementation also demonstrates `super`.

## Prototype behavior

JavaScript class methods are associated with prototypes.

The program checks:

`Object.getPrototypeOf(Dog.prototype) === Animal.prototype`

This makes the prototype chain explicit.

## Symbol capabilities

The report example uses a `Symbol` as a capability key.

This avoids relying on an ordinary string property name for the export operation.

## Iterators

`Countdown` implements `Symbol.iterator`.

This allows:

`[...new Countdown(5)]`

to consume the object using JavaScript's iteration protocol.

## Asynchronous polymorphism

`DataSource` defines an asynchronous contract.

`MemoryDataSource` and `DelayedDataSource` provide different implementations.

Both can be consumed through the same `printRecords()` function.

This connects OOP with asynchronous application development.

## Event-driven architecture

`EventBus` stores event handlers and invokes them when events are published.

The order-processing example publishes events such as:

`order.paid`

and:

`order.shipped`

This demonstrates how object-oriented components can participate in event-driven systems.

---

# C++ case study

## Problem being modeled

The C++ implementation models an online marketplace order-processing platform.

An order contains:

- customer information
- products
- quantities
- shipping distance
- order state

The platform must support:

- different payment providers
- different shipping methods
- different discount policies
- order persistence
- domain validation
- event notifications
- reporting

The design intentionally separates business responsibilities.

---

## Major components

### Customer

`Customer` encapsulates:

- ID
- name
- email

The constructor validates initial data.

`changeEmail()` validates future changes.

The internal data remains private.

### Product

`Product` manages:

- SKU
- name
- price
- stock

Stock can be changed through:

`restock()`

and:

`reserve()`

This keeps inventory rules close to the inventory state.

### OrderItem

`OrderItem` connects a product with a quantity.

Its `subtotal()` method calculates the item value.

### Order

`Order` is the main domain aggregate.

It controls:

- item addition
- subtotal calculation
- order status
- payment transition
- shipping transition
- cancellation

The state transitions are protected by validation.

A created order can become paid.

A paid order can become shipped.

A shipped order cannot be moved back to an earlier state through the provided operations.

---

# Payment abstraction

The abstract `PaymentProvider` interface defines:

- `providerName()`
- `authorize()`
- `capture()`

Concrete implementations include:

- `CardPayment`
- `WalletPayment`
- `BankTransferPayment`

The order processor does not need to know which concrete payment class it received.

This is abstraction plus polymorphism.

---

# Shipping abstraction

`ShippingProvider` defines a common shipping-cost operation.

Concrete implementations calculate prices differently.

### Standard shipping

Uses a base fee, weight component, and distance component.

### Express shipping

Uses higher coefficients to represent a faster service.

### International shipping

Uses larger base and distance-related costs.

The formulas are intentionally simple so that the OOP structure remains clear.

---

# Discount abstraction

The `DiscountPolicy` abstraction allows different pricing rules.

The case study contains:

- `NoDiscount`
- `PercentageDiscount`

The order processor can therefore receive a different discount policy without modifying its core processing algorithm.

This demonstrates the Open/Closed design idea in a practical form.

A new discount policy can implement the same abstraction.

---

# Repository abstraction

The `OrderRepository` interface separates order-processing logic from persistence.

The case study provides:

`InMemoryOrderRepository`

The processor therefore does not depend directly on an in-memory map.

A different implementation could use another storage mechanism while preserving the same repository contract.

This is an example of dependency inversion.

---

# Event-driven behavior

The `EventBus` provides a simple publish-subscribe mechanism.

Listeners can subscribe to event names such as:

`order.paid`

and:

`order.shipped`

When an event occurs, all registered handlers receive the event.

This design separates the action that produces an event from independent consumers of that event.

For example:

- auditing can consume payment events
- notifications can consume shipping events
- analytics can consume order events

The case study keeps these listeners simple and synchronous.

A production event platform may use durable messaging, retries, delivery guarantees, authentication, authorization, and observability.

---

# Factory-style creation

The C++ case study provides factory functions:

`createPaymentProvider()`

and:

`createShippingProvider()`

These centralize the mapping from configuration names to concrete implementations.

For example:

`card`

creates `CardPayment`.

`express`

creates `ExpressShipping`.

Factories can become more sophisticated in large applications, especially when dependency graphs become complex.

---

# Smart pointers and ownership

C++ requires explicit consideration of object lifetime.

The case study uses:

`std::unique_ptr`

for processor-owned polymorphic dependencies.

This expresses exclusive ownership.

It uses:

`std::shared_ptr`

where multiple parts of the system need shared access, such as the order repository or event bus.

The distinction matters.

`unique_ptr` should generally be preferred when one object clearly owns another.

`shared_ptr` should be used when shared lifetime is actually required.

Using `shared_ptr` everywhere can obscure ownership and introduce unnecessary reference-counting overhead.

---

# Virtual destructors

Polymorphic C++ base classes use virtual destructors.

For example:

`virtual ~PaymentProvider() = default;`

This is important when a derived object is destroyed through a pointer to the base class.

Without an appropriate virtual destructor, destruction through a base pointer can produce undefined behavior when the derived type requires cleanup.

---

# The role of `override`

The C++ implementations use:

`override`

on derived methods.

This tells the compiler that the programmer expects the function to override a virtual base-class function.

If the function signature does not correctly match a virtual base method, the compiler can diagnose the problem.

This reduces errors in polymorphic hierarchies.

---

# Error handling

The implementations demonstrate validation at domain boundaries.

Python uses exceptions such as:

`ValueError`

and custom exceptions.

JavaScript uses `Error` and `TypeError`.

C++ uses exception classes derived from `std::runtime_error`.

The C++ case study distinguishes:

- `ValidationError`
- `DomainError`
- `InvalidStateError`

This provides more specific failure information.

---

# State transitions

An object can be valid while still being in an incorrect state for a particular operation.

The order lifecycle demonstrates this distinction.

A simplified state model is:

`Created -> Paid -> Shipped`

Cancellation is restricted according to the current state.

The important design principle is that the `Order` object owns these rules.

External code should not directly assign arbitrary status values.

This is an important consequence of encapsulation.

---

# Liskov substitution

The Liskov Substitution Principle is concerned with behavioral compatibility between a base abstraction and its subtypes.

If code expects a `PaymentProvider` to authorize and capture payments according to the abstraction's contract, every valid implementation should respect that contract.

Inheritance alone does not guarantee substitutability.

A derived class can technically inherit from a base class while still violating assumptions made by clients.

This is why good abstraction design requires meaningful contracts rather than merely shared fields or methods.

---

# Why inheritance can be overused

Inheritance creates coupling between base and derived types.

A deep hierarchy can become difficult to understand because changes in a base class can affect many descendants.

Typical warning signs include:

- many levels of inheritance
- subclasses overriding most inherited behavior
- subclasses needing to disable parent behavior
- base classes containing unrelated responsibilities
- code using inheritance only for a small amount of reuse
- frequent `instanceof`, `isinstance`, or type checks

Composition often provides a simpler alternative.

---

# Common OOP mistakes

## Treating encapsulation as simply private variables

Private fields are useful, but encapsulation is primarily about protecting valid state and behavior.

A class with private fields can still have poor design if it exposes arbitrary setters that permit invalid states.

## Using inheritance for convenience

Shared code does not automatically mean that one class should inherit from another.

Inheritance should represent a meaningful subtype relationship.

## Creating overly large classes

A class that handles database access, validation, networking, reporting, authentication, logging, and business logic has many reasons to change.

This makes maintenance difficult.

## Exposing mutable collections

Returning an internal mutable collection directly can allow external code to bypass the object's rules.

Defensive copies, read-only interfaces, iterators, or controlled mutation methods may be preferable depending on the language and use case.

## Excessive type checking

Code that repeatedly checks concrete types can indicate that polymorphism or a better abstraction could simplify the design.

Type checks are not inherently wrong. They are useful when the actual domain requires different treatment based on type.

## Deep inheritance hierarchies

Deep hierarchies increase cognitive and maintenance costs.

A smaller hierarchy combined with composition is often easier to reason about.

---

# Edge cases demonstrated

The implementations explicitly test several invalid conditions.

Examples include:

- negative account deposits
- withdrawals greater than available balance
- invalid temperatures
- empty identifiers
- invalid email addresses
- negative inventory
- zero order quantities
- invalid money values
- incompatible currencies
- unsupported payment methods
- unsupported shipping methods
- invalid order state transitions
- insufficient product stock
- failed payment authorization
- invalid discount percentages

These checks demonstrate an important OOP principle:

Objects should reject invalid state at the boundary where that state would otherwise enter the system.

---

# Performance considerations

OOP does not automatically determine algorithmic complexity.

A poorly chosen data structure can dominate performance regardless of whether the code is procedural or object-oriented.

The Python implementation compares membership in a list and a set.

The C++ case study compares a vector search with an unordered-map lookup.

The JavaScript implementation compares array membership with `Set.has()`.

Typical complexities are:

| Operation | Typical complexity |
|---|---:|
| Vector/list sequential search | O(n) |
| Hash-set membership | Average O(1) |
| Hash-map lookup | Average O(1) |
| Iterating n elements | O(n) |
| Sorting n elements | O(n log n) with common comparison sorts |

Actual performance depends on implementation details, memory layout, workload, cache behavior, hashing, allocation, and input distribution.

OOP abstraction can introduce costs such as:

- dynamic dispatch
- additional object allocations
- indirection
- pointer chasing
- virtual-table lookup in languages such as C++

These costs should be considered when relevant, but they should not automatically be treated as reasons to avoid OOP.

Measure real bottlenecks before optimizing.

---

# Memory and ownership

Ownership is particularly important in C++.

The language exposes explicit lifetime-management tools.

`std::unique_ptr` expresses unique ownership.

`std::shared_ptr` expresses shared ownership.

References and raw pointers can express non-owning relationships when used carefully.

Python and JavaScript use automatic garbage collection, so the programmer generally does not explicitly free ordinary objects.

Automatic memory management does not eliminate resource-management concerns.

Files, sockets, database connections, locks, subscriptions, and external resources may still require explicit lifecycle management.

---

# Security considerations

OOP does not automatically make software secure.

Encapsulation can reduce accidental state manipulation, but access control and security authorization are separate concerns.

Production systems should consider:

- authentication
- authorization
- input validation
- secure secrets management
- audit logging
- protection against injection attacks
- secure serialization
- dependency security
- safe error reporting
- transaction integrity
- concurrency control
- data privacy
- rate limiting
- secure communication

For a payment platform, payment credentials should not be stored or logged casually.

Sensitive data should be minimized and protected according to the application's security requirements and applicable regulations.

A private field in a programming language is not equivalent to a security boundary between trusted and untrusted users.

---

# Design considerations

## Single Responsibility Principle

A class should have a focused responsibility.

The C++ case study separates:

- product management
- customer management
- order state
- payment
- shipping
- discounts
- persistence
- events
- reporting

This prevents one class from becoming responsible for every operation in the system.

## Open/Closed Principle

The order processor can work with new payment, shipping, and discount implementations through their abstractions.

This allows extension without requiring the central processing algorithm to understand every concrete provider.

## Liskov Substitution Principle

Derived classes must preserve the expectations of their abstraction.

A subtype that violates the base contract creates unreliable polymorphism.

## Interface Segregation Principle

Large interfaces can force implementations to provide operations they do not need.

Smaller capability-focused interfaces can reduce unnecessary coupling.

The Python `Protocol` examples illustrate this idea by describing specific capabilities.

## Dependency Inversion Principle

High-level business rules should depend on stable abstractions rather than concrete infrastructure.

The C++ `OrderProcessor` demonstrates this through injected interfaces.

---

# Python, JavaScript, and C++ differences

| Area | Python | JavaScript | C++ |
|---|---|---|---|
| Private state | Conventions, name mangling, properties | `#privateField` | `private:` |
| Abstract classes | `abc` module | Convention/base-class methods | Pure virtual functions |
| Typing | Dynamic with optional static typing | Dynamic with optional tooling | Static |
| Polymorphism | Duck typing, protocols, inheritance | Structural behavior, prototypes, inheritance | Virtual functions, templates, interfaces |
| Memory management | Garbage collected | Garbage collected | Explicit ownership models plus RAII |
| Multiple inheritance | Supported | Class inheritance is single-chain; behavior can be composed | Supported |
| Interfaces | ABC and `Protocol` | Conventions and base classes | Abstract classes |
| Operator overloading | Supported for selected operations | Limited compared with Python/C++ | Extensive operator overloading |
| Runtime flexibility | Very high | Very high | More constrained by static type system |
| Compile-time checking | Limited by default | Limited by default | Extensive |

The different language models make the three implementations useful for understanding the same OOP principles from different perspectives.

---

# Python-specific OOP features

The Python implementation demonstrates:

- classes
- objects
- properties
- name mangling
- inheritance
- multiple inheritance
- MRO
- `super()`
- abstract base classes
- protocols
- duck typing
- dataclasses
- frozen dataclasses
- operator overloading
- custom exceptions
- iterators
- `singledispatch`
- dependency injection
- composition

Python's flexibility makes it easy to express behavior-based interfaces.

This flexibility also means that architectural discipline remains important.

---

# JavaScript-specific OOP features

The JavaScript implementation demonstrates:

- class syntax
- constructors
- private fields
- getters
- setters
- `extends`
- `super`
- prototypes
- `instanceof`
- symbols
- static members
- iterators
- asynchronous methods
- promises
- event-driven design
- composition
- dependency injection

JavaScript's prototype-based foundation remains important even when developers primarily use modern class syntax.

A class is not equivalent to a C++ or Java class internally. JavaScript class syntax provides a more familiar object-oriented interface over the language's prototype model.

---

# C++-specific OOP features

The C++ implementation demonstrates:

- classes
- private members
- constructors
- inheritance
- abstract classes
- pure virtual functions
- virtual destructors
- `override`
- runtime polymorphism
- `std::unique_ptr`
- `std::shared_ptr`
- RAII-oriented ownership
- composition
- dependency injection
- custom exceptions
- `std::vector`
- `std::unordered_map`
- factories
- repositories
- event publishing
- state machines
- performance measurement

C++ provides strong compile-time support for object-oriented designs while also exposing lower-level control over memory and object lifetime.

---

# Abstraction versus encapsulation

These terms are often confused.

Encapsulation asks:

"How should the object's internal state and operations be protected?"

Abstraction asks:

"What essential behavior should the client see?"

For example, a payment provider may encapsulate internal configuration and state.

Its abstraction may expose only:

`authorize()`

and:

`capture()`

The internal implementation can contain many details that remain invisible to the caller.

Therefore, encapsulation and abstraction often work together, but they solve different design problems.

---

# Inheritance versus polymorphism

Inheritance and polymorphism are also distinct.

Inheritance establishes a relationship between types.

Polymorphism allows code to use multiple implementations through a common operation.

Inheritance can enable polymorphism, but it is not the only mechanism.

Python can use duck typing or `Protocol`.

JavaScript can use structural behavior.

C++ can use templates or concepts for compile-time polymorphism and virtual functions for runtime polymorphism.

Therefore:

`inheritance != polymorphism`

Inheritance is one possible mechanism for implementing polymorphic designs.

---

# Runtime polymorphism versus compile-time polymorphism

Runtime polymorphism selects behavior while the program is running.

C++ virtual functions provide a common example.

Compile-time polymorphism selects or generates behavior during compilation.

Examples include:

- C++ function templates
- C++ class templates
- C++ overloaded functions
- C++ concepts

Python and JavaScript rely heavily on runtime behavior and dynamic dispatch.

The appropriate approach depends on the problem, performance requirements, type guarantees, and desired flexibility.

---

# Abstraction and interfaces

An interface should contain behavior that clients genuinely need.

A large interface containing unrelated operations increases coupling.

For example, a simple shipping provider needs to calculate shipping cost.

It should not necessarily be forced to implement:

- payment processing
- customer management
- analytics
- report generation

Separating capabilities makes implementations easier to understand and test.

---

# Testing object-oriented systems

Useful OOP tests generally verify behavior and invariants rather than implementation details.

Examples include:

- depositing increases balance
- withdrawing cannot exceed balance
- product reservation decreases stock
- invalid quantities are rejected
- an order cannot ship before payment
- a payment provider rejects values above its limit
- a discount policy produces the expected discount
- repository lookup returns the stored order
- event listeners receive the expected events

The implementations contain executable assertions and explicit failure demonstrations.

Good tests should verify externally observable behavior while avoiding unnecessary dependence on private implementation details.

---

# Production considerations

An educational object-oriented model must be expanded considerably before becoming a production financial or marketplace system.

A production system may require:

- transactional database operations
- concurrency control
- idempotency
- distributed locking where appropriate
- durable event delivery
- retry policies
- observability
- structured logging
- authentication
- authorization
- secure secret handling
- API validation
- rate limiting
- monitoring
- tracing
- fault isolation
- disaster recovery
- data retention controls
- regulatory compliance
- automated testing
- deployment automation

The four OOP principles provide design tools. They do not replace system architecture, security engineering, database design, distributed-systems principles, or operational engineering.

---

# Practical applications

OOP principles appear in many software systems.

## Banking

Objects can represent:

- accounts
- customers
- transactions
- payment methods
- loans
- financial instruments

Encapsulation can protect financial invariants.

Polymorphism can represent different payment or account types.

## E-commerce

Objects can represent:

- products
- carts
- orders
- discounts
- shipping providers
- payment gateways

The C++ case study is based on this domain.

## Software development tools

Objects can represent:

- files
- repositories
- commits
- users
- build jobs
- deployment environments

## Games

Objects can represent:

- players
- enemies
- weapons
- vehicles
- levels
- game states

Polymorphism can provide different behavior for different entity types.

## Enterprise applications

Objects commonly model:

- customers
- employees
- invoices
- workflows
- policies
- integrations
- reports

The principles are especially useful when business rules are complex and need clear ownership.

---

# When OOP may not be the best fit

OOP is not universally superior.

A procedural approach can be simpler for small scripts.

Functional programming can be particularly useful for transformations and immutable data pipelines.

Data-oriented designs can be appropriate for high-performance workloads where memory layout and cache behavior dominate.

Relational database operations are often naturally expressed using declarative SQL.

A good architecture selects the programming model based on the problem rather than forcing every problem into classes.

---

# Design checklist

When designing an object-oriented component, consider:

- What state does the object own?
- What invariants must always hold?
- Which operations are allowed to change the state?
- Which details should remain internal?
- What public behavior does a client actually need?
- Is inheritance representing a real subtype relationship?
- Would composition be simpler?
- Which behaviors need to be interchangeable?
- Is an abstraction stable enough to justify introducing it?
- Are dependencies injected where replacement or testing matters?
- Are invalid states rejected early?
- Are exceptions meaningful to callers?
- Is object ownership clear?
- Are mutable collections safely exposed?
- Is the chosen data structure appropriate?
- Has performance been measured rather than assumed?
- Are security controls separate from language-level encapsulation?
- Can the class be tested independently?

---

# Core relationships

A useful conceptual model is:

`Encapsulation -> protects state`

`Abstraction -> defines essential behavior`

`Inheritance -> establishes subtype relationships`

`Polymorphism -> permits interchangeable implementations`

`Composition -> assembles independent components`

`Dependency injection -> supplies replaceable collaborators`

These mechanisms are complementary.

A sophisticated OOP design does not necessarily maximize the use of inheritance. It usually uses the smallest set of relationships needed to represent the domain clearly.

---

# Implementation map

| Concept | Python | JavaScript | C++ |
|---|---|---|---|
| Basic class | `Person` | `Person` | `Customer` |
| Encapsulation | `BankAccount`, `Temperature` | `BankAccount`, `Temperature` | `Customer`, `Product`, `Order` |
| Inheritance | `Animal`, `Dog`, `Cat` | `Animal`, `Dog`, `Cat` | Provider classes |
| Polymorphism | Duck typing, ABC, protocol | Base classes and capability checks | Virtual functions |
| Abstraction | `PaymentProcessor` | `PaymentProcessor` | `PaymentProvider` |
| Composition | `Car` and `Engine` | `Car` and `Engine` | `Order`, `OrderItem`, dependencies |
| Dependency injection | `OrderService` | `OrderService`, `OrderProcessor` | `OrderProcessor` |
| Exceptions | Built-in and custom | `Error`, `TypeError` | Domain exception hierarchy |
| Iterators | `Countdown` | `Symbol.iterator` | Range-based collections |
| Value objects | `Money`, `Coordinate` | `Money` | Domain classes |
| Events | Indirect examples | `EventBus` | `EventBus` |
| Factory | `create_report()` | `createReport()` | Provider factory functions |
| Performance | List versus set | Array versus Set | Vector versus unordered map |

---

# File responsibilities

## Python

The Python file is a comprehensive language-level study.

It is especially useful for understanding:

- dynamic dispatch
- duck typing
- properties
- abstract base classes
- protocols
- Python data model methods
- dataclasses
- composition
- flexible object interfaces

## JavaScript

The JavaScript file concentrates on:

- private fields
- getters and setters
- prototypes
- classes
- symbols
- iterators
- asynchronous polymorphism
- event-driven systems

## C++

The C++ program is the most system-oriented implementation.

It models an order-processing platform and integrates:

- domain objects
- state transitions
- polymorphic services
- dependency injection
- repository abstraction
- events
- pricing strategies
- exception handling
- ownership
- performance measurement

---

# Important distinctions

### Class versus object

A class defines a type.

An object is an instance of that type.

### Encapsulation versus abstraction

Encapsulation controls state and implementation boundaries.

Abstraction defines the essential interface presented to users of the component.

### Inheritance versus composition

Inheritance represents an "is-a" relationship.

Composition represents a "has-a" relationship.

### Interface versus implementation

An interface describes required behavior.

An implementation provides the actual behavior.

### Equality versus identity

Two objects may contain equal values while still being different object instances.

The Python implementation demonstrates this distinction with `is` and `==`.

JavaScript has similar distinctions between object identity and value comparison.

---

# Limitations of the examples

The examples are designed to isolate OOP concepts and therefore simplify several real-world concerns.

The payment system does not connect to actual financial networks.

The shipping formulas are illustrative.

The repository is in memory rather than persistent.

The event bus is local and synchronous in C++.

The JavaScript event system is intentionally lightweight.

The Python examples do not model database transactions or distributed execution.

These limitations are deliberate because the focus is on object-oriented design rather than infrastructure integration.

---

# Security boundary versus encapsulation boundary

A private field prevents ordinary application code from directly accessing implementation state through the language's normal object interface.

That does not automatically establish a security boundary.

For example:

- Python name mangling is not a security mechanism.
- JavaScript private fields are not an authorization system.
- C++ private members do not prevent a compromised process from accessing process memory.

Application security requires explicit controls around identity, permissions, secrets, communication, data handling, and system boundaries.

---

# Final conceptual model

A useful way to reason about the four principles is to ask four different questions about a class.

**Encapsulation**

"What state does this object own, and how should that state be changed safely?"

**Abstraction**

"What behavior should clients be allowed to depend on?"

**Inheritance**

"Is this object genuinely a specialized form of another abstraction?"

**Polymorphism**

"Can different implementations satisfy the same required behavior?"

If the answers are clear, the resulting object model is usually easier to test, maintain, extend, and reason about.

The Python, JavaScript, and C++ implementations demonstrate these questions at different levels of abstraction, from small classes and value objects to a multi-component order-processing system.
