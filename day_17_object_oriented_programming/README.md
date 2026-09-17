# Object-Oriented Programming: Classes, Objects, Methods, Attributes

## Topic introduction

Object-Oriented Programming (OOP) is a programming paradigm that organizes software around objects containing state and behavior.

An object generally combines:

- **State**, represented by attributes or data members.
- **Behavior**, represented by methods or member functions.
- **Identity**, which distinguishes one object instance from another.

A **class** defines the structure and behavior that its objects will follow. An **object** is a concrete instance of a class created during program execution.

OOP is particularly useful when software models entities that have both data and behavior, such as users, bank accounts, orders, vehicles, library books, employees, financial instruments, devices, or database records.

The three implementations in this repository approach OOP from different language perspectives:

- Python emphasizes flexible object models, duck typing, properties, dataclasses, protocols, and concise class definitions.
- JavaScript demonstrates the language's class syntax while also exposing its prototype-based object model, private fields, iterators, asynchronous behavior, and event-driven patterns.
- C++ demonstrates strongly typed object-oriented design, explicit access control, virtual dispatch, abstract classes, RAII, smart pointers, templates, and STL data structures through a library management system.

---

## Fundamental terminology

### Class

A class is a definition describing the data and operations associated with a type of object.

In Python, a class can be declared with `class`.

In JavaScript, classes are declared with `class` and normally use a `constructor()`.

In C++, a class is declared using the `class` keyword and can specify access sections such as `private`, `protected`, and `public`.

A class itself is not necessarily the same thing as an object. The class describes what an object should contain and do, while an object represents a concrete instance.

### Object

An object is an instance of a class.

For example, a `Student` class can represent the structure of students. An individual student such as `student_one` is an object created from that class.

Multiple objects can be created from the same class while holding different state.

### Attribute

An attribute stores data associated with an object or class.

Examples include:

- `name`
- `age`
- `salary`
- `balance`
- `batteryKWh`
- `isbn`

Python commonly uses instance attributes such as `self.name`.

JavaScript normally uses instance properties such as `this.name`.

C++ normally stores state as private or protected data members.

### Method

A method is a function associated with a class or object.

Methods describe behavior.

Examples include:

- `deposit()`
- `withdraw()`
- `move()`
- `borrowBook()`
- `returnBook()`
- `calculate()`
- `describe()`

Methods are important because OOP does not merely store data. It associates operations with the state they manipulate.

### Constructor

A constructor initializes an object when it is created.

Python commonly uses `__init__()`.

JavaScript uses `constructor()`.

C++ uses a constructor with the same name as the class.

Constructors in the implementations perform validation as well as initialization.

---

## The relationship between classes and objects

The basic relationship can be represented conceptually as:

`Class definition → object instance → attributes + methods`

For example, a `BankAccount` class defines operations such as `deposit()` and `withdraw()`. Each account object has its own balance.

Two accounts can therefore use the same behavior while maintaining independent state.

This is one of the fundamental reasons classes are useful in application design.

---

## Python implementation

The Python implementation begins with a basic `Student` class.

The constructor receives `name` and `age` and stores them using `self`.

The method `introduce()` operates on the object's state.

The example creates two independent objects:

`student_one = Student("Asha", 20)`

and

`student_two = Student("Rahul", 22)`

Both objects use the same class definition, but each maintains its own values.

### Python instance attributes

An instance attribute belongs to a particular object.

The `Employee` example demonstrates:

- `name`
- `salary`

Changing `employee_one.salary` does not change `employee_two.salary`.

### Python class attributes

The `Employee` class also defines:

`company_name`

and

`employee_count`.

A class attribute is associated with the class itself and can be shared by instances unless an instance creates an attribute that shadows it.

This distinction is important because accidentally modifying a class-level mutable object can cause state to be shared between objects when independent state was intended.

---

## Python method types

Python supports several important method forms.

### Instance methods

An instance method receives `self` and normally operates on one particular object.

The `Temperature.to_fahrenheit()` method demonstrates this model.

### Class methods

A class method uses `@classmethod` and receives `cls`.

The `Temperature.from_fahrenheit()` method demonstrates an alternative constructor. It creates a `Temperature` object from a Fahrenheit value.

Class methods are useful for:

- alternative constructors
- class-level operations
- factory-style construction

### Static methods

A static method uses `@staticmethod`.

It does not automatically receive `self` or `cls`.

`Temperature.is_valid_celsius()` is a static method because validation does not depend on a particular temperature object or the class state.

---

## Encapsulation

Encapsulation means grouping related data and behavior and controlling how internal state is manipulated.

The `BankAccount` implementation demonstrates encapsulation by providing operations such as `deposit()` and `withdraw()` instead of allowing every caller to manipulate the balance without validation.

The class verifies:

- opening balance
- deposit amount
- withdrawal amount
- sufficient funds

Python does not make ordinary attributes strictly private through a language-enforced access-control system comparable to C++. A leading underscore communicates that an attribute is intended for internal use.

Python also supports name mangling for names beginning with two underscores.

Encapsulation should be understood as a design mechanism rather than automatically as a security boundary.

---

## Properties in Python

Python properties allow attribute-like syntax to execute methods.

The `Product` class uses:

`@property`

for reading the price and a setter for validating assignments.

This permits code such as:

`product.price = 1800`

while still executing validation logic.

The `discounted_price` property computes a value dynamically.

Properties are useful when an attribute needs:

- validation
- computed behavior
- controlled assignment
- compatibility with attribute-style access

---

## Inheritance

Inheritance allows one class to derive from another.

The Python implementation contains:

- `Vehicle`
- `Car`
- `ElectricCar`

`Car` inherits from `Vehicle`.

`ElectricCar` inherits from `Car`.

Inheritance can provide reuse, specialization, and polymorphism, but it also creates coupling between classes. A deep inheritance hierarchy can become difficult to understand and maintain.

For that reason, inheritance should represent a meaningful type relationship rather than being used solely to reuse a few lines of code.

---

## Method overriding

A subclass can provide a different implementation of a method defined by its parent.

`Vehicle.move()` provides general behavior.

`Car.move()` provides car-specific behavior.

`ElectricCar.move()` provides electric-car-specific behavior.

The same method name therefore produces different results depending on the object's actual type.

---

## Polymorphism

Polymorphism means that code can operate through a common interface while different object types provide different implementations.

The Python example defines `Dog`, `Cat`, and `Cow`, each with `speak()`.

The `make_animal_speak()` function does not need a specific inheritance hierarchy. It relies on the presence of a compatible method.

This is commonly called **duck typing** in Python.

The principle is effectively:

If an object provides the required behavior, the code can use that behavior.

---

## Abstract base classes

The `Shape` example uses Python's `ABC` and `abstractmethod`.

A `Shape` defines an interface requiring:

- `area()`
- `perimeter()`

`Rectangle` and `Circle` implement those operations.

Abstract classes are useful when a family of classes must follow a common contract.

They are particularly valuable when designing larger systems in which different implementations need to be interchangeable.

---

## Composition

Composition builds an object from other objects.

The Python `CarWithEngine` class contains an `Engine` object.

The JavaScript implementation also demonstrates this concept.

The C++ case study uses composition through `ComposedCar`, which contains an `Engine` as a member.

Composition often produces flexible designs because components can be replaced without changing the identity of the containing object.

For example, a payment service can contain a payment gateway rather than inheriting from a gateway.

---

## Aggregation

Aggregation is a relationship in which one object refers to other objects that can exist independently.

The Python `Classroom` example receives a collection of `Teacher` objects.

The teachers can exist independently of the classroom.

This differs conceptually from stronger ownership relationships in which the lifetime of a component is directly controlled by the containing object.

The exact distinction between aggregation and composition can vary across modeling conventions, so the important engineering question is usually the ownership and lifetime relationship between the objects.

---

## Special methods in Python

Python uses special methods to integrate user-defined classes with language operations.

Examples demonstrated in the Python implementation include:

- `__init__`
- `__repr__`
- `__add__`
- `__sub__`
- `__mul__`
- `__eq__`
- `__lt__`
- `__iter__`

The `Vector` class demonstrates operator overloading.

For example, `vector_a + vector_b` invokes the class's `__add__()` implementation.

Special methods allow user-defined objects to behave naturally with Python syntax.

---

## Equality versus identity

The Python implementation distinguishes:

`==`

from

`is`

`==` normally tests equality according to an object's equality implementation.

`is` tests object identity.

Two objects can contain equal values while still being different objects.

The `SimpleValue` example creates two separate objects with the same value. Their equality comparison can return true while their identity comparison is false.

Identity should generally be used when checking whether two references point to the exact same object.

---

## Dataclasses

Python's `dataclass` feature reduces boilerplate for classes primarily representing structured data.

The `Customer`, `Address`, `Book`, `LineItem`, and `Coordinate` examples use dataclasses.

Dataclasses can automatically provide useful methods such as:

- initialization
- representation
- equality

depending on configuration.

`field(default_factory=list)` is important when each object needs its own mutable list.

A mutable list should not be used as a shared default value for independent instances.

---

## Immutability

The Python implementation uses:

`@dataclass(frozen=True)`

for immutable-style objects such as `Address`, `Book`, and `Coordinate`.

The JavaScript implementation uses `Object.freeze()` for a configuration object.

C++ can express immutable access through `const` and can use value semantics and other mechanisms to restrict mutation.

Immutability reduces unintended state changes and can simplify reasoning about objects.

---

## Protocols and structural typing

Python's `Protocol` feature allows an interface-like contract based on supported operations rather than inheritance.

The `Printable` protocol requires a `describe()` method.

Both `Report` and `Invoice` satisfy that behavioral requirement.

This is related to duck typing but provides additional benefits for static type checking.

---

## Dependency injection

Dependency injection means providing an object with the dependencies it needs instead of forcing it to construct those dependencies internally.

The Python implementation passes a notifier into `OrderService`.

The JavaScript implementation does the same.

The C++ implementation passes a `Notifier` implementation into the `Library` and a pricing strategy into `Checkout`.

Dependency injection improves:

- testability
- configurability
- separation of responsibilities
- replacement of implementations
- maintainability

For example, a production application can use an email notifier while a test can inject a fake notifier.

---

## Factory pattern

The Python and JavaScript implementations include a notification factory.

A factory centralizes the creation of related object types.

Instead of directly constructing every concrete notification implementation throughout an application, the caller can request a channel such as `email` or `sms`.

Factories become particularly useful when object construction requires validation, configuration, dependencies, or selection logic.

---

## Strategy pattern

The strategy pattern encapsulates interchangeable algorithms or business rules behind a common interface.

The Python implementation uses pricing strategies:

- `RegularPricing`
- `PremiumPricing`
- `SeasonalPricing`

The JavaScript implementation uses pricing strategies in the same conceptual area.

The C++ implementation uses pricing strategies for checkout.

The major benefit is that the main class does not need a large conditional structure for every possible algorithm.

---

## JavaScript object-oriented programming

JavaScript has an important distinction from languages that were historically designed around classical classes.

JavaScript is fundamentally prototype-based.

Modern JavaScript provides `class` syntax, but class instances still participate in the prototype chain.

The JavaScript implementation deliberately demonstrates both models.

### JavaScript classes

A JavaScript class commonly contains:

- `constructor()`
- instance methods
- static properties
- static methods
- getters
- setters

The `Student`, `Employee`, `Product`, and `BankAccount` classes demonstrate these mechanisms.

### Private fields

JavaScript supports private class fields using `#`.

The `BankAccount` class contains:

`#balance`

and

`#transactionCount`.

These fields cannot be directly accessed through normal external property syntax.

Private fields provide language-level encapsulation that differs from a naming convention such as `_balance`.

---

## JavaScript prototypes

The `LegacyPerson` example uses a constructor function and explicitly assigns `describe()` to the prototype.

This demonstrates an important fact about JavaScript:

Methods do not necessarily need to be copied into every object instance.

Prototype-based lookup allows objects to find shared behavior through their prototype chain.

JavaScript `class` syntax provides a more familiar class-oriented programming style while retaining this underlying prototype model.

---

## JavaScript polymorphism

JavaScript allows polymorphic behavior through inheritance, interfaces expressed by convention, and structural checks.

The `Dog`, `Cat`, and `Cow` examples demonstrate a simple behavioral interface:

`speak()`

A function can work with any object that supplies the required method.

This is similar in spirit to duck typing.

---

## JavaScript getters and setters

The `Product` class uses a getter and setter for `price`.

The setter validates assignments.

The getter controls how the value is returned.

The `discountedPrice` getter provides a computed property.

Getters and setters can make APIs easier to use, but they should not hide expensive operations or surprising side effects behind ordinary property access.

---

## JavaScript iterators and generators

The `NumberRange` class implements `Symbol.iterator`.

Its generator function yields numbers lazily.

This allows:

`[...range]`

and

`for...of`

to operate directly on the custom object.

Generators are useful for:

- lazy sequences
- streaming
- large data sets
- stateful iteration
- asynchronous workflows when combined with related mechanisms

---

## JavaScript asynchronous objects

The `DataRepository` and `UserService` classes demonstrate asynchronous methods.

`DataRepository.fetchRecord()` simulates an I/O operation.

`UserService.getUser()` awaits the repository result.

This structure is common in web applications where classes coordinate:

- database calls
- network requests
- filesystem operations
- external APIs
- asynchronous services

Asynchronous code should propagate failures using rejected promises and appropriate error handling.

---

## Event-driven OOP

The JavaScript `EventEmitterLite` demonstrates an event-driven design.

Objects register listeners for named events.

When an event is emitted, the registered listeners are invoked.

Event-driven OOP is common in:

- web applications
- desktop applications
- servers
- user interfaces
- messaging systems
- distributed applications

The major design consideration is that event relationships can become difficult to trace if too many implicit dependencies are introduced.

---

# C++ implementation

The C++ implementation is organized as a realistic library management system.

The system models:

- books
- library members
- borrowing
- returning
- availability
- author search
- notifications
- pricing strategies
- repositories
- transactions

It also demonstrates lower-level object-oriented mechanisms that are particularly important in C++.

---

## C++ classes and access control

The `Student` class contains private data members:

- `name_`
- `age_`

Public methods provide controlled access.

This is a major difference from languages where access control is primarily conventional.

C++ provides explicit access specifiers:

- `private`
- `protected`
- `public`

The default access level for a C++ `class` is private.

---

## Constructors and initializer lists

The C++ constructors use initializer lists.

For example, member variables are initialized before the constructor body executes.

Initializer lists are important for:

- const members
- reference members
- member objects
- efficient initialization
- classes without default constructors

The `ComposedCar` example demonstrates member-object construction.

---

## Const correctness

The C++ implementation frequently uses `const`.

A method such as:

`double balance() const`

promises not to modify the object's observable state.

Const correctness improves:

- API clarity
- compiler checking
- safe access
- interoperability with const objects

It is a central aspect of professional C++ class design.

---

## Inheritance in C++

The C++ implementation contains:

- `Vehicle`
- `Car`
- `ElectricCar`

The derived classes override `move()`.

The base class destructor is virtual:

`virtual ~Vehicle() = default;`

This is important when deleting derived objects through base-class pointers.

---

## Virtual functions

C++ runtime polymorphism normally relies on virtual functions.

The `Shape` hierarchy demonstrates:

- a base interface
- pure virtual functions
- derived implementations
- polymorphic access through pointers

The declaration:

`virtual double area() const = 0;`

makes `area()` a pure virtual function.

A class containing pure virtual functions is abstract and cannot normally be instantiated directly.

---

## Smart pointers

The C++ implementation uses:

- `std::unique_ptr`
- `std::shared_ptr`

`unique_ptr` represents exclusive ownership.

The vehicle collection uses `unique_ptr` because each object has a single owning collection.

`shared_ptr` is used for injected dependencies such as the notifier.

Ownership should be explicit because object lifetime is an important part of C++ design.

---

## RAII

RAII stands for **Resource Acquisition Is Initialization**.

It is one of the most important C++ resource-management techniques.

An object's constructor acquires or establishes a resource, and its destructor releases or finalizes it.

The `TransactionGuard` example demonstrates deterministic cleanup.

When the object leaves scope, its destructor runs automatically.

This is especially useful for:

- files
- locks
- memory
- database transactions
- sockets
- other resources requiring cleanup

RAII reduces the risk of resource leaks and makes exception-safe programming easier.

---

## Composition in C++

The `ComposedCar` class contains an `Engine` object directly.

This means the engine is part of the car's object structure.

This is a stronger ownership relationship than simply storing an external reference.

Composition is often preferred when a component is conceptually part of the containing object.

---

## Operator overloading

The `Money` class overloads:

- `operator+`
- `operator-`
- `operator==`
- `operator<`

It also defines `operator<<` for output.

Operator overloading allows domain objects to integrate naturally with C++ syntax.

It should be used when the overloaded operation has an intuitive and consistent meaning.

Financial code should generally use integer minor units, fixed-point representations, or appropriate decimal arithmetic rather than relying blindly on binary floating-point values.

The `Money` example therefore stores cents as an integer.

---

# C++ library management case study

## Problem being modeled

The case study models a library in which:

- books can be registered
- members can be registered
- members can borrow books
- members can return books
- a book cannot be borrowed by two members simultaneously
- each member has a borrowing limit
- books can be searched by author
- available books can be listed
- notifications can be generated

The purpose of the case study is to demonstrate how OOP structures a non-trivial domain rather than merely presenting isolated class syntax.

---

## Major components

### `Book`

`Book` represents immutable-style book metadata through private members and accessor methods.

The main properties are:

- ISBN
- title
- author

Validation occurs during construction.

### `LibraryMember`

`LibraryMember` represents a registered library user.

It stores:

- member ID
- name
- borrowed ISBNs

A `std::set` is used for borrowed ISBNs.

This provides ordered storage and logarithmic lookup, insertion, and removal.

### `Library`

`Library` coordinates the domain.

It stores books and members using `std::unordered_map`.

The key is the ISBN for books and the member ID for members.

This provides average constant-time lookup for the common lookup operations.

### `Notifier`

`Notifier` defines a polymorphic interface.

`ConsoleNotifier` is one concrete implementation.

The library does not need to know how notifications are delivered.

This is dependency inversion through an interface-like abstraction.

---

## Borrowing algorithm

The borrowing operation performs several validation steps:

1. Locate the member.
2. Locate the book.
3. Check whether the member already borrowed the book.
4. Check the member borrowing limit.
5. Check whether another member currently has the book.
6. Record the borrowing.
7. Send a notification.

The implementation throws exceptions when an operation cannot be completed.

This is preferable to silently modifying state after a failed validation.

---

## Returning algorithm

The return operation:

1. Locates the member.
2. Checks whether the member currently has the book.
3. Removes the ISBN from the member's borrowed set.
4. Sends a notification.

The operation fails if the member did not borrow the specified book.

---

## Searching

The `searchByAuthor()` function iterates through stored books and selects books whose author contains the requested string.

The current implementation performs a linear scan.

For `N` books, a simple search is approximately `O(N)`.

For small collections this can be adequate.

For large production systems, search may use:

- database indexes
- search indexes
- inverted indexes
- normalized lookup keys
- specialized search infrastructure

The appropriate solution depends on data volume, query requirements, and operational constraints.

---

## Data structures and complexity

The case study deliberately uses different containers according to their roles.

### `std::unordered_map`

Used for books and members.

Average lookup:

`O(1)`

Worst-case lookup can degrade toward `O(N)` depending on hashing behavior and collisions.

### `std::set`

Used for borrowed ISBNs.

Lookup:

`O(log N)`

Insertion:

`O(log N)`

Removal:

`O(log N)`

### `std::vector`

Used for collections where sequential traversal is appropriate.

Indexed access:

`O(1)`

Linear search:

`O(N)`

The choice of data structure is part of object-oriented design because the object's behavior depends on how its state is represented.

---

# Important OOP principles

## Encapsulation

Keep internal state controlled and expose operations that preserve valid invariants.

A bank account should not allow arbitrary invalid balance manipulation.

## Abstraction

Expose what users of a class need while hiding implementation details that should not be depended upon.

The `Shape` interface is an example.

## Inheritance

Use inheritance when a genuine substitutable type relationship exists.

Avoid inheritance solely because two classes happen to share implementation.

## Polymorphism

Use common interfaces to allow multiple implementations.

This reduces coupling between consumers and concrete classes.

## Composition

Build complex objects from smaller components when their responsibilities can vary independently.

Composition is frequently useful for services and application architecture.

---

# Inheritance versus composition

Inheritance expresses a relationship similar to:

`ElectricCar is a Vehicle`

Composition expresses a relationship similar to:

`Car has an Engine`

These relationships are conceptually different.

Inheritance can provide:

- subtype polymorphism
- shared interface
- specialized behavior

Composition can provide:

- replaceable components
- lower coupling
- explicit ownership
- easier independent testing

A useful design question is whether the relationship describes identity or assembly.

---

# Common mistakes

## Excessive inheritance

A large inheritance tree can make behavior difficult to trace.

Deep hierarchies can also increase coupling between base and derived classes.

## Public mutable state

Allowing unrestricted modification of internal state can make invariants difficult to maintain.

Validation should normally occur at meaningful boundaries.

## God classes

A class that performs database access, business logic, notification, validation, reporting, and user-interface operations simultaneously becomes difficult to test and maintain.

Responsibilities should be separated when the domain and system size justify it.

## Mutable shared defaults

In Python, using a mutable default such as a list directly as a function default can accidentally share state between calls.

`default_factory` is used by dataclasses to avoid this problem.

## Confusing identity and equality

Two objects can represent equal values while still being separate objects.

This distinction is particularly important when implementing equality, hashing, collections, and caching.

## Ignoring ownership in C++

Raw pointers do not by themselves communicate ownership.

Modern C++ generally favors RAII and smart pointers when dynamic ownership is required.

## Incorrect virtual destructors

A polymorphic C++ base class normally needs a virtual destructor when derived objects may be destroyed through base pointers.

## Hidden expensive operations

A getter or property should not unexpectedly perform expensive database or network operations merely because it looks like ordinary attribute access.

---

# Exceptions and error handling

The three implementations validate invalid operations.

Examples include:

- negative balances
- invalid prices
- invalid ages
- unknown books
- unknown members
- duplicate records
- unavailable books
- borrowing-limit violations
- invalid strategies
- invalid collection indexes

Python uses exception classes such as `ValueError` and `TypeError`.

JavaScript uses `Error`, `TypeError`, `RangeError`, and a custom `ValidationError`.

C++ uses standard exceptions such as:

- `std::invalid_argument`
- `std::logic_error`
- `std::out_of_range`
- `std::runtime_error`

Exception handling should represent genuinely exceptional or invalid operations rather than normal control flow.

---

# Validation and invariants

An invariant is a condition that should remain true for an object while it is in a valid state.

Examples:

A bank account:

`balance >= 0`

A product:

`price >= 0`

A library member:

`borrowedCount <= maximumBorrowingLimit`

A line item:

`quantity > 0`

Constructors and mutating methods are appropriate locations for enforcing these rules.

Maintaining invariants reduces the number of invalid states that the rest of the application must handle.

---

# Performance considerations

OOP introduces some overhead through object allocation, method dispatch, attribute access, and indirection.

The significance of this overhead depends on the application.

For most business applications, clarity and correct architecture are generally more important than eliminating tiny object-level costs prematurely.

Performance-sensitive systems should measure actual bottlenecks.

The examples include timing demonstrations, but those measurements are environment-dependent and should not be treated as universal benchmarks.

Important performance factors include:

- algorithmic complexity
- data structures
- allocation frequency
- cache locality
- memory usage
- virtual dispatch
- object lifetime
- copying
- serialization
- I/O
- database access

The C++ case study makes ownership and object lifetime explicit because those factors can have substantial performance consequences in systems programming.

---

# Memory considerations

Python objects carry runtime metadata and generally have more memory overhead than primitive C-style representations.

Python's `__slots__` can reduce per-instance memory in suitable classes by restricting normal instance dictionaries.

The Python example demonstrates `CompactPoint`.

`__slots__` should not be used automatically. It changes class behavior and can restrict dynamic attributes.

C++ provides much more direct control over object layout and ownership.

C++ objects can often be stored contiguously in vectors, which can provide favorable cache behavior.

JavaScript engines perform extensive runtime optimization, but developers should still avoid unnecessary object creation and excessive memory retention in high-throughput code.

---

# Security considerations

OOP mechanisms should not be confused with complete security boundaries.

Encapsulation can reduce accidental misuse, but application security requires controls at trust boundaries.

Important practices include:

- validate untrusted input
- avoid storing plaintext passwords
- protect authentication secrets
- avoid exposing sensitive state through serialization
- use established cryptographic primitives
- enforce authorization independently of object visibility
- avoid unsafe deserialization
- prevent sensitive data from appearing in logs
- validate data received from databases and external services

The JavaScript `Session` class demonstrates controlled serialization so that a private token is not included in JSON output.

---

# Python, JavaScript, and C++ comparison

| Concept | Python | JavaScript | C++ |
|---|---|---|---|
| Class declaration | `class` | `class` | `class` |
| Constructor | `__init__` | `constructor` | class-named constructor |
| Instance reference | `self` | `this` | implicit object context through member functions |
| Instance methods | Yes | Yes | Yes |
| Class/static methods | `@classmethod`, `@staticmethod` | `static` | `static` |
| Encapsulation | conventions, properties, name mangling | private `#` fields, closures | `private`, `protected`, `public` |
| Inheritance | supported | supported | supported |
| Runtime polymorphism | duck typing, inheritance | prototype/class behavior | virtual functions |
| Abstract classes | `ABC` | convention/runtime checks | pure virtual functions |
| Composition | objects containing objects | objects containing objects | member objects, smart pointers |
| Operator overloading | special methods | limited language mechanisms | extensive operator overloading |
| Automatic memory management | garbage collection/reference counting mechanisms | garbage collection | deterministic lifetime and RAII |
| Generic programming | typing and dynamic mechanisms | generic functions/classes | templates |
| Strong compile-time type system | optional type checking | dynamic typing | strong static typing |
| Prototypes | not applicable | fundamental object mechanism | not applicable |

---

# Design considerations

Good OOP design is not simply the creation of many classes.

A useful design should consider:

- responsibility
- cohesion
- coupling
- object lifetime
- ownership
- invariants
- interfaces
- dependency direction
- testability
- data structures
- performance
- security
- maintainability

A class should have a coherent reason to exist.

The implementation should expose a useful public interface while minimizing unnecessary dependencies on internal representation.

---

# SOLID-oriented considerations

## Single Responsibility Principle

A class should have a focused responsibility.

The library example separates books, members, notifications, pricing, and library coordination.

## Open/Closed Principle

Software should be designed so that new behavior can often be introduced through new implementations rather than extensive modification of existing code.

The pricing strategy classes demonstrate this approach.

## Liskov Substitution Principle

A derived class should behave consistently with the expectations established by its base abstraction.

Polymorphism is useful only when substitutions remain semantically valid.

## Interface Segregation Principle

Clients should not be forced to depend on methods they do not need.

Small interfaces such as `Notifier` can be easier to implement and test.

## Dependency Inversion Principle

High-level logic should depend on abstractions rather than unnecessary concrete implementations.

The `Library` depends on `Notifier`, while `Checkout` depends on `PricingStrategy`.

These principles are design guidelines rather than rigid rules. Applying them mechanically can create unnecessary abstraction.

---

# Production considerations

A production OOP system normally requires more than the domain classes shown here.

Important production concerns can include:

- persistent storage
- database transactions
- authentication
- authorization
- logging
- monitoring
- metrics
- configuration management
- concurrency
- distributed communication
- retries
- timeouts
- validation at system boundaries
- API contracts
- automated testing
- deployment
- observability
- data migration
- failure recovery

The educational case study intentionally keeps infrastructure self-contained so that the OOP mechanisms remain visible.

---

# Testing considerations

OOP makes testing easier when classes have focused responsibilities and explicit dependencies.

The examples include lightweight assertions.

A production test suite would normally separate:

- unit tests
- integration tests
- component tests
- end-to-end tests

Dependency injection is particularly valuable for testing because external services can be replaced by controlled implementations.

For example, the library's `Notifier` can be replaced by a test implementation that records messages without actually sending them.

---

# Edge cases demonstrated

The implementations deliberately handle cases such as:

- negative financial values
- zero values where inappropriate
- non-finite numeric values
- empty names
- duplicate ISBNs
- duplicate member IDs
- unknown records
- duplicate borrowing
- unavailable books
- borrowing limits
- returning an unborrowed book
- invalid discount percentages
- invalid repository indexes
- null or invalid dependencies
- immutable object modification
- invalid class construction

Edge-case handling is part of class design because public methods define the valid state transitions of an object.

---

# Implementation structure

The Python file progresses from basic objects to more advanced OOP concepts.

Its major stages include:

- basic classes
- attributes
- methods
- encapsulation
- properties
- inheritance
- polymorphism
- abstract classes
- composition
- aggregation
- special methods
- dataclasses
- iterables
- protocols
- dependency injection
- design patterns
- testing
- performance
- security
- an integrated e-commerce example

The JavaScript file complements this with:

- object literals
- classes
- prototypes
- private fields
- getters and setters
- inheritance
- polymorphism
- symbols
- iterators
- generators
- mixins
- asynchronous classes
- event-driven design
- custom errors
- dependency injection
- strategy and factory patterns

The C++ program focuses on a complete library management domain and emphasizes:

- explicit access control
- inheritance
- virtual dispatch
- abstract classes
- smart pointers
- composition
- RAII
- STL containers
- templates
- exception handling
- dependency injection
- strategy-based design
- complexity and performance

---

# Running the implementations

## Python

Use Python 3.10 or later and execute the Python file directly.

The implementation uses only the Python standard library.

## JavaScript

Use Node.js 18 or later and execute the JavaScript file.

The implementation does not require external npm packages.

## C++

Compile the program with C++17 or a later standard.

A typical compilation command is:

`g++ -std=c++17 -Wall -Wextra -pedantic main.cpp -o oop_case_study`

The program uses the C++ standard library and requires no external libraries.

---

# Real-world relevance

Object-oriented programming is widely used in systems where entities have persistent state, behavior, and relationships.

Examples include:

- banking systems
- e-commerce platforms
- enterprise applications
- content-management systems
- game engines
- desktop applications
- web backends
- scientific software
- simulation systems
- financial systems
- inventory management
- logistics
- telecommunications
- embedded systems
- operating-system components
- developer tools

The appropriate programming paradigm depends on the problem. OOP is particularly useful when domain entities and their interactions form a meaningful part of the system's structure.

The central engineering concern is not the number of classes but whether the resulting object model accurately represents responsibilities, dependencies, state, and behavior.
