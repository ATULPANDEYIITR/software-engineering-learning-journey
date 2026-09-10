"""
Software Design Basics: Modularity, Abstraction, and Encapsulation
===================================================================

A self-contained study script progressing from beginner concepts to
intermediate and advanced software-design techniques.

The examples use only the Python standard library.

Core topics:
    1. What software design means
    2. Modularity
    3. Cohesion and coupling
    4. Separation of concerns
    5. Abstraction
    6. Encapsulation
    7. Information hiding
    8. Interfaces and contracts
    9. Composition
    10. Dependency injection
    11. Layered design
    12. Refactoring procedural code into modules
    13. Abstract base classes
    14. Properties and controlled state
    15. Validation and invariants
    16. Immutability
    17. Dependency inversion
    18. Extensibility
    19. Testing design boundaries
    20. Design trade-offs
    21. Performance and security considerations
    22. Common design mistakes
    23. A larger integrated example

Run this file directly with Python 3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from math import sqrt
from typing import Callable, Iterable, Protocol


# ============================================================================
# 1. SOFTWARE DESIGN BASICS
# ============================================================================

def section(title: str) -> None:
    """Print a consistent section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    """Print a subsection heading."""
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


section("1. What Software Design Means")

print(
    """
Software design is the process of deciding how software should be structured
before and during implementation.

A well-designed program is not merely one that produces the correct output.
Its internal structure should also make it easier to:

    - understand
    - test
    - modify
    - reuse
    - extend
    - debug
    - secure
    - maintain

Three foundational ideas in this lesson are:

    Modularity:
        Divide a system into meaningful, relatively independent components.

    Abstraction:
        Expose important behavior while hiding unnecessary implementation
        details.

    Encapsulation:
        Keep data and the operations that control that data together, while
        restricting inappropriate direct access to internal state.

These ideas overlap, but they are not identical.
"""
)


# ============================================================================
# 2. A SMALL EXAMPLE OF POOR DESIGN
# ============================================================================

section("2. Why Software Structure Matters")

subsection("A tightly coupled example")

def process_order_poorly(
    customer_name: str,
    product_name: str,
    quantity: int,
    price: float,
) -> str:
    """
    Everything is placed into one function:
        validation
        calculation
        formatting
        persistence simulation
        notification simulation

    This works for a tiny example, but changes become difficult as the
    application grows.
    """
    if not customer_name:
        raise ValueError("Customer name is required")

    if quantity <= 0:
        raise ValueError("Quantity must be positive")

    subtotal = quantity * price
    tax = subtotal * 0.18
    total = subtotal + tax

    record = (
        f"customer={customer_name}, "
        f"product={product_name}, "
        f"quantity={quantity}, "
        f"total={total:.2f}"
    )

    print("Saving:", record)
    print("Sending notification to:", customer_name)

    return record


print(process_order_poorly("Atul", "Keyboard", 2, 1500.0))

print(
    """
The function is not inherently incorrect. Its design problem is that several
different responsibilities are coupled together.

If tax rules change, persistence changes, notification changes, or output
formatting changes, the same function becomes a modification point for many
unrelated concerns.
"""
)


# ============================================================================
# 3. MODULARITY
# ============================================================================

section("3. Modularity")

print(
    """
Modularity means organizing software into separate components with clear
responsibilities and boundaries.

A module can be:

    - a function
    - a class
    - a Python module
    - a package
    - a service
    - a subsystem

A good module generally has:

    - a focused purpose
    - a clear public interface
    - limited knowledge of unrelated components
    - minimal unnecessary dependencies
    - a predictable contract
"""
)


subsection("Simple functional modularity")

def validate_quantity(quantity: int) -> None:
    """Validate the business rule for quantity."""
    if not isinstance(quantity, int):
        raise TypeError("Quantity must be an integer")

    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")


def calculate_subtotal(quantity: int, unit_price: float) -> float:
    """Calculate an order subtotal."""
    validate_quantity(quantity)

    if unit_price < 0:
        raise ValueError("Unit price cannot be negative")

    return quantity * unit_price


def calculate_tax(amount: float, tax_rate: float = 0.18) -> float:
    """Calculate tax separately from the rest of the order."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    if not 0 <= tax_rate <= 1:
        raise ValueError("Tax rate must be between 0 and 1")

    return amount * tax_rate


def calculate_total(quantity: int, unit_price: float, tax_rate: float) -> float:
    """Compose smaller functions into a complete calculation."""
    subtotal = calculate_subtotal(quantity, unit_price)
    tax = calculate_tax(subtotal, tax_rate)
    return subtotal + tax


print("Modular total:", calculate_total(2, 1500.0, 0.18))


subsection("High cohesion")

print(
    """
Cohesion describes how strongly the responsibilities inside one component
belong together.

High cohesion:
    A component has a focused and closely related purpose.

Low cohesion:
    A component contains unrelated responsibilities.

Example:

    InvoiceCalculator
        - calculate subtotal
        - calculate tax
        - calculate discount

is generally more cohesive than:

    UtilityManager
        - calculate invoice
        - send email
        - resize image
        - parse CSV
        - encrypt password
"""
)


class InvoiceCalculator:
    """A cohesive component for invoice calculations."""

    def subtotal(self, quantity: int, unit_price: float) -> float:
        validate_quantity(quantity)

        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")

        return quantity * unit_price

    def tax(self, amount: float, rate: float) -> float:
        return calculate_tax(amount, rate)

    def total(self, quantity: int, unit_price: float, rate: float) -> float:
        subtotal = self.subtotal(quantity, unit_price)
        return subtotal + self.tax(subtotal, rate)


invoice_calculator = InvoiceCalculator()
print(invoice_calculator.total(3, 1000.0, 0.18))


subsection("Coupling")

print(
    """
Coupling describes how strongly components depend on one another.

High coupling:
    One component knows many implementation details of another.

Low coupling:
    Components communicate through small, stable interfaces.

The objective is not to eliminate coupling. Some coupling is necessary.
The objective is to keep coupling intentional, understandable, and limited.
"""
)


# ============================================================================
# 4. SEPARATION OF CONCERNS
# ============================================================================

section("4. Separation of Concerns")

print(
    """
Separation of concerns means keeping different kinds of responsibilities
separate.

Typical concerns in an application include:

    - input handling
    - validation
    - business rules
    - calculations
    - persistence
    - external communication
    - presentation

Separating these concerns reduces the number of reasons a component needs to
change.
"""
)


class Order:
    """Domain data and business behavior for an order."""

    def __init__(
        self,
        customer_name: str,
        product_name: str,
        quantity: int,
        unit_price: float,
    ) -> None:
        if not customer_name.strip():
            raise ValueError("Customer name is required")

        validate_quantity(quantity)

        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")

        self.customer_name = customer_name
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price

    def subtotal(self) -> float:
        return self.quantity * self.unit_price


class OrderRepository:
    """Persistence abstraction.

    This demonstration stores records in memory instead of using a database.
    """

    def __init__(self) -> None:
        self._orders: list[Order] = []

    def save(self, order: Order) -> None:
        self._orders.append(order)

    def all(self) -> list[Order]:
        return list(self._orders)


class OrderNotifier:
    """Notification concern kept separate from order calculations."""

    def send(self, order: Order) -> None:
        print(
            f"Notification: order for {order.customer_name} "
            f"was processed."
        )


class OrderService:
    """Application-level orchestration.

    It coordinates domain objects, persistence, and notifications without
    implementing all their internal details.
    """

    def __init__(
        self,
        repository: OrderRepository,
        notifier: OrderNotifier,
    ) -> None:
        self._repository = repository
        self._notifier = notifier

    def process(self, order: Order) -> float:
        total = order.subtotal() * 1.18
        self._repository.save(order)
        self._notifier.send(order)
        return total


repository = OrderRepository()
notifier = OrderNotifier()
service = OrderService(repository, notifier)

example_order = Order("Atul", "Monitor", 1, 12000.0)
print("Processed total:", service.process(example_order))


# ============================================================================
# 5. ABSTRACTION
# ============================================================================

section("5. Abstraction")

print(
    """
Abstraction means representing a complex concept through the important
operations users of that concept need.

An abstraction answers:

    "What can this component do?"

It intentionally avoids forcing callers to understand:

    "How exactly does this component do it?"

Examples from everyday software:

    file.open()
    database.execute(...)
    list.append(...)
    payment.process()

A caller uses an operation without needing to understand every internal
implementation detail.
"""
)


subsection("A simple abstraction")

class CoffeeMachine:
    """The caller sees a simple operation."""

    def make_coffee(self) -> str:
        self._heat_water()
        self._grind_beans()
        self._brew()
        return "Coffee is ready"

    def _heat_water(self) -> None:
        print("Heating water")

    def _grind_beans(self) -> None:
        print("Grinding beans")

    def _brew(self) -> None:
        print("Brewing coffee")


machine = CoffeeMachine()
print(machine.make_coffee())


subsection("Abstraction versus implementation")

print(
    """
The public operation is:

    make_coffee()

The implementation details are:

    _heat_water()
    _grind_beans()
    _brew()

The caller does not need to coordinate those individual operations.

A useful abstraction is usually:

    - small enough to understand
    - stable enough to reuse
    - expressive enough to represent the required behavior
    - not overloaded with unrelated operations
"""
)


# ============================================================================
# 6. ENCAPSULATION
# ============================================================================

section("6. Encapsulation")

print(
    """
Encapsulation means grouping state and behavior together and controlling how
that state can be changed.

Python does not provide the same strict private-member mechanism as some
languages. Instead, Python commonly uses:

    _name
        A convention meaning internal use.

    __name
        Name mangling, which makes accidental external access less likely.

    @property
        A controlled interface for reading or changing state.

Encapsulation is primarily about protecting invariants and controlling
responsibility, not merely hiding variables.
"""
)


subsection("Why uncontrolled state can be dangerous")

class BankAccountPoorlyEncapsulated:
    def __init__(self, balance: float) -> None:
        self.balance = balance


bad_account = BankAccountPoorlyEncapsulated(1000.0)
bad_account.balance = -50000.0

print("Invalid state is possible:", bad_account.balance)


subsection("Controlled state")

class BankAccount:
    """A bank account that protects its balance invariant."""

    def __init__(self, opening_balance: float = 0.0) -> None:
        if opening_balance < 0:
            raise ValueError("Opening balance cannot be negative")

        self._balance = float(opening_balance)

    @property
    def balance(self) -> float:
        """Expose the balance for reading."""
        return self._balance

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit must be positive")

        self._balance += amount

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal must be positive")

        if amount > self._balance:
            raise ValueError("Insufficient funds")

        self._balance -= amount


account = BankAccount(1000.0)
account.deposit(500.0)
account.withdraw(250.0)

print("Controlled balance:", account.balance)

try:
    account.withdraw(5000.0)
except ValueError as error:
    print("Protected operation:", error)


# ============================================================================
# 7. INFORMATION HIDING
# ============================================================================

section("7. Information Hiding")

print(
    """
Information hiding is closely related to encapsulation.

The goal is to prevent other components from depending on details that are
likely to change.

Suppose a cache internally uses a dictionary today.

If callers directly depend on that dictionary, replacing it with another
implementation becomes difficult.

If callers only use:

    get()
    put()

the internal storage mechanism can change without changing callers.
"""
)


class SimpleCache:
    """Internal storage is deliberately hidden behind operations."""

    def __init__(self) -> None:
        self._storage: dict[str, object] = {}

    def put(self, key: str, value: object) -> None:
        self._storage[key] = value

    def get(self, key: str) -> object | None:
        return self._storage.get(key)

    def contains(self, key: str) -> bool:
        return key in self._storage


cache = SimpleCache()
cache.put("user:1", {"name": "Atul"})
print("Cached object:", cache.get("user:1"))
print("Contains key:", cache.contains("user:1"))


# ============================================================================
# 8. INTERFACES AND CONTRACTS
# ============================================================================

section("8. Interfaces and Contracts")

print(
    """
An interface defines what operations a component promises to provide.

A contract describes expected behavior.

A useful contract may specify:

    - accepted inputs
    - returned outputs
    - possible exceptions
    - state changes
    - important invariants

Python supports interface-like design through:

    - abstract base classes
    - protocols
    - duck typing

The implementation can vary as long as it satisfies the required behavior.
"""
)


class PaymentProcessor(ABC):
    """Abstract interface for payment processing."""

    @abstractmethod
    def pay(self, amount: float) -> str:
        """Process a payment and return a transaction identifier."""
        raise NotImplementedError


class CardPaymentProcessor(PaymentProcessor):
    def pay(self, amount: float) -> str:
        if amount <= 0:
            raise ValueError("Payment must be positive")

        return f"CARD-{amount:.2f}"


class BankTransferProcessor(PaymentProcessor):
    def pay(self, amount: float) -> str:
        if amount <= 0:
            raise ValueError("Payment must be positive")

        return f"BANK-{amount:.2f}"


def complete_payment(
    processor: PaymentProcessor,
    amount: float,
) -> str:
    """Depend on the interface rather than a specific payment mechanism."""
    return processor.pay(amount)


print(complete_payment(CardPaymentProcessor(), 500.0))
print(complete_payment(BankTransferProcessor(), 500.0))


# ============================================================================
# 9. DUCK TYPING AND PROTOCOLS
# ============================================================================

section("9. Duck Typing and Protocols")

print(
    """
Python frequently follows the principle:

    "If an object provides the required behavior, it can be used."

This is duck typing.

A Protocol provides a way to describe such a structural interface for
type-checking purposes.
"""
)


class Logger(Protocol):
    def write(self, message: str) -> None:
        ...


class ConsoleLogger:
    def write(self, message: str) -> None:
        print("LOG:", message)


class MemoryLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def write(self, message: str) -> None:
        self.messages.append(message)


def run_task(logger: Logger) -> str:
    logger.write("Task started")
    logger.write("Task completed")
    return "success"


console_logger = ConsoleLogger()
print("Task result:", run_task(console_logger))

memory_logger = MemoryLogger()
run_task(memory_logger)
print("Stored logs:", memory_logger.messages)


# ============================================================================
# 10. COMPOSITION
# ============================================================================

section("10. Composition")

print(
    """
Composition means building a larger object from smaller objects.

Instead of making one enormous class responsible for everything, a class can
delegate specific responsibilities to collaborating components.

For example:

    OrderService
        contains a repository
        contains a notifier
        uses a pricing policy

Composition often provides flexibility without creating deep inheritance
hierarchies.
"""
)


class FixedTaxPolicy:
    def __init__(self, rate: float) -> None:
        if not 0 <= rate <= 1:
            raise ValueError("Tax rate must be between 0 and 1")

        self._rate = rate

    def calculate(self, subtotal: float) -> float:
        return subtotal * self._rate


class DiscountPolicy:
    def calculate(self, subtotal: float) -> float:
        if subtotal >= 10000:
            return subtotal * 0.10
        return 0.0


class PricingService:
    """Composes separate pricing policies."""

    def __init__(
        self,
        tax_policy: FixedTaxPolicy,
        discount_policy: DiscountPolicy,
    ) -> None:
        self._tax_policy = tax_policy
        self._discount_policy = discount_policy

    def calculate_total(self, subtotal: float) -> float:
        discount = self._discount_policy.calculate(subtotal)
        taxable_amount = subtotal - discount
        tax = self._tax_policy.calculate(taxable_amount)

        return taxable_amount + tax


pricing = PricingService(
    tax_policy=FixedTaxPolicy(0.18),
    discount_policy=DiscountPolicy(),
)

print("Composed pricing result:", pricing.calculate_total(15000.0))


# ============================================================================
# 11. DEPENDENCY INJECTION
# ============================================================================

section("11. Dependency Injection")

print(
    """
Dependency injection means giving an object the dependencies it needs
instead of forcing it to construct those dependencies internally.

Poor design:

    class Service:
        def __init__(self):
            self.database = RealDatabase()

Better design:

    class Service:
        def __init__(self, database):
            self.database = database

Benefits include:

    - easier testing
    - lower coupling
    - easier replacement
    - clearer dependencies
    - improved configuration
"""
)


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._users: dict[int, str] = {}

    def save(self, user_id: int, name: str) -> None:
        self._users[user_id] = name

    def find(self, user_id: int) -> str | None:
        return self._users.get(user_id)


class UserService:
    """The repository is injected from outside."""

    def __init__(self, repository: InMemoryUserRepository) -> None:
        self._repository = repository

    def register(self, user_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("Name cannot be empty")

        self._repository.save(user_id, name)

    def get_name(self, user_id: int) -> str | None:
        return self._repository.find(user_id)


user_repository = InMemoryUserRepository()
user_service = UserService(user_repository)

user_service.register(1, "Atul")
print("Registered user:", user_service.get_name(1))


# ============================================================================
# 12. LAYERED DESIGN
# ============================================================================

section("12. Layered Design")

print(
    """
A common architectural organization is:

    Presentation layer
        Handles interaction and formatting.

    Application/service layer
        Coordinates use cases.

    Domain layer
        Contains business concepts and rules.

    Infrastructure layer
        Handles databases, files, networks, and external systems.

The exact architecture depends on the system. The important design principle
is to avoid mixing unrelated responsibilities unnecessarily.
"""
)


@dataclass(frozen=True)
class Product:
    """Immutable domain data."""

    product_id: int
    name: str
    price: Decimal


class ProductRepository:
    """Infrastructure-like repository."""

    def __init__(self) -> None:
        self._products: dict[int, Product] = {}

    def save(self, product: Product) -> None:
        self._products[product.product_id] = product

    def find(self, product_id: int) -> Product | None:
        return self._products.get(product_id)


class ProductService:
    """Application service."""

    def __init__(self, repository: ProductRepository) -> None:
        self._repository = repository

    def create_product(
        self,
        product_id: int,
        name: str,
        price: Decimal,
    ) -> Product:
        if not name.strip():
            raise ValueError("Product name is required")

        if price < 0:
            raise ValueError("Product price cannot be negative")

        product = Product(product_id, name.strip(), price)
        self._repository.save(product)
        return product


product_repository = ProductRepository()
product_service = ProductService(product_repository)

product = product_service.create_product(
    101,
    "Laptop",
    Decimal("75000.00"),
)

print("Product:", product)


# ============================================================================
# 13. ABSTRACTION LEVELS
# ============================================================================

section("13. Choosing the Right Abstraction Level")

print(
    """
A common design mistake is either too little abstraction or too much.

Too little abstraction:
    A caller must understand implementation details.

Too much abstraction:
    Simple behavior is hidden behind many unnecessary classes.

A good abstraction should match the problem domain and provide a meaningful
boundary.

Example:

    calculate_emi(principal, rate, months)

can be a useful abstraction for callers that need an EMI result.

The caller usually does not need to know the exact intermediate arithmetic
steps.
"""
)


def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    months: int,
) -> float:
    """
    Calculate a standard reducing-balance EMI.

    Edge case:
        Zero interest produces principal / months.
    """
    if principal <= 0:
        raise ValueError("Principal must be positive")

    if annual_interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")

    if months <= 0:
        raise ValueError("Number of months must be positive")

    monthly_rate = annual_interest_rate / 12 / 100

    if monthly_rate == 0:
        return principal / months

    factor = (1 + monthly_rate) ** months
    return principal * monthly_rate * factor / (factor - 1)


print("EMI:", round(calculate_emi(500000, 8.5, 60), 2))
print("Zero-interest EMI:", calculate_emi(120000, 0, 12))


# ============================================================================
# 14. ENCAPSULATION WITH PROPERTIES
# ============================================================================

section("14. Properties and Invariants")

print(
    """
An invariant is a condition that should remain true for an object.

For a temperature object, an invariant might be:

    Kelvin >= 0

For a bank account:

    balance >= 0

For an order:

    quantity > 0

Encapsulation provides a natural location for enforcing these rules.
"""
)


class Temperature:
    """Temperature with Kelvin validation."""

    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Temperature cannot be below absolute zero")

        self._celsius = float(value)

    @property
    def fahrenheit(self) -> float:
        return self._celsius * 9 / 5 + 32

    @property
    def kelvin(self) -> float:
        return self._celsius + 273.15


temperature = Temperature(25)
print("Celsius:", temperature.celsius)
print("Fahrenheit:", temperature.fahrenheit)
print("Kelvin:", temperature.kelvin)

try:
    temperature.celsius = -500
except ValueError as error:
    print("Invariant protected:", error)


# ============================================================================
# 15. IMMUTABILITY
# ============================================================================

section("15. Immutability")

print(
    """
An immutable object cannot be changed after creation.

Benefits:

    - easier reasoning
    - fewer accidental state changes
    - safer sharing
    - simpler concurrency
    - predictable behavior

Python's frozen dataclasses provide convenient immutable-style value objects.
"""
)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money cannot be negative")

        if len(self.currency) != 3:
            raise ValueError("Currency must contain three characters")


money = Money(Decimal("2500.00"), "INR")
print("Money:", money)

try:
    money.amount = Decimal("5000.00")
except Exception as error:
    print("Immutable object rejected mutation:", type(error).__name__)


# ============================================================================
# 16. FUNCTIONAL MODULARITY
# ============================================================================

section("16. Functions as Small Modules")

print(
    """
Functions are one of the simplest forms of modularity.

A well-designed function usually has:

    - one clear purpose
    - explicit inputs
    - predictable output
    - limited side effects
    - manageable complexity

Pure functions are especially useful.

A pure function:

    - depends only on its inputs
    - does not modify external state
    - produces the same output for the same input
"""
)


def square(number: float) -> float:
    """Pure function."""
    return number * number


def cube(number: float) -> float:
    """Pure function."""
    return number * number * number


def apply_operation(
    value: float,
    operation: Callable[[float], float],
) -> float:
    """Accept behavior as a dependency."""
    return operation(value)


print("Square:", apply_operation(5, square))
print("Cube:", apply_operation(5, cube))


# ============================================================================
# 17. SINGLE RESPONSIBILITY
# ============================================================================

section("17. Single Responsibility")

print(
    """
The Single Responsibility Principle is commonly summarized as:

    A component should have one primary responsibility and one reason to
    change.

This does not mean every class must contain exactly one method.

It means its responsibilities should form a coherent concept.
"""
)


class ReportCalculator:
    """Only performs report calculations."""

    def average(self, values: Iterable[float]) -> float:
        numbers = list(values)

        if not numbers:
            raise ValueError("At least one value is required")

        return sum(numbers) / len(numbers)


class ReportFormatter:
    """Only converts report data into presentation text."""

    def format_average(self, average: float) -> str:
        return f"Average: {average:.2f}"


calculator = ReportCalculator()
formatter = ReportFormatter()

average = calculator.average([10, 20, 30, 40])
print(formatter.format_average(average))


# ============================================================================
# 18. OPEN/CLOSED DESIGN
# ============================================================================

section("18. Extensibility and the Open/Closed Principle")

print(
    """
The Open/Closed Principle describes components that are:

    open for extension
    closed for unnecessary modification

The idea is to design stable abstractions so new behavior can often be added
through new implementations rather than repeatedly changing old logic.
"""
)


class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        raise NotImplementedError


@dataclass(frozen=True)
class Circle(Shape):
    radius: float

    def area(self) -> float:
        if self.radius < 0:
            raise ValueError("Radius cannot be negative")

        return 3.141592653589793 * self.radius ** 2


@dataclass(frozen=True)
class Rectangle(Shape):
    width: float
    height: float

    def area(self) -> float:
        if self.width < 0 or self.height < 0:
            raise ValueError("Dimensions cannot be negative")

        return self.width * self.height


def total_area(shapes: Iterable[Shape]) -> float:
    """Works with existing and future Shape implementations."""
    return sum(shape.area() for shape in shapes)


shapes = [
    Circle(5),
    Rectangle(10, 20),
]

print("Total shape area:", total_area(shapes))


# ============================================================================
# 19. DEPENDENCY INVERSION
# ============================================================================

section("19. Dependency Inversion")

print(
    """
Dependency inversion is about reducing high-level dependence on concrete
low-level implementation details.

Instead of:

    BusinessService -> SpecificDatabase

prefer:

    BusinessService -> Repository interface
                         ^
                         |
                  SpecificDatabase

The high-level policy depends on an abstraction.
"""
)


class UserStore(Protocol):
    def save(self, user_id: int, name: str) -> None:
        ...

    def find(self, user_id: int) -> str | None:
        ...


class InMemoryUserStore:
    def __init__(self) -> None:
        self._data: dict[int, str] = {}

    def save(self, user_id: int, name: str) -> None:
        self._data[user_id] = name

    def find(self, user_id: int) -> str | None:
        return self._data.get(user_id)


class FileLikeUserStore:
    """
    A second implementation demonstrating substitutability.

    This example keeps data in a supplied dictionary rather than actually
    writing a file, so the script remains self-contained.
    """

    def __init__(self) -> None:
        self._records: dict[int, str] = {}

    def save(self, user_id: int, name: str) -> None:
        self._records[user_id] = name

    def find(self, user_id: int) -> str | None:
        return self._records.get(user_id)


class RegistrationService:
    def __init__(self, store: UserStore) -> None:
        self._store = store

    def register(self, user_id: int, name: str) -> None:
        if not name.strip():
            raise ValueError("Name cannot be empty")

        self._store.save(user_id, name.strip())


service_a = RegistrationService(InMemoryUserStore())
service_b = RegistrationService(FileLikeUserStore())

service_a.register(1, "Atul")
service_b.register(2, "Student")

print("Two implementations satisfy the same dependency contract.")


# ============================================================================
# 20. LISKOV SUBSTITUTION
# ============================================================================

section("20. Substitutability")

print(
    """
A subtype should be usable wherever the abstraction promises it can be used.

If an implementation technically matches a method signature but violates the
behavioral expectations of the abstraction, substitutability has failed.

For example, if a Shape contract promises area(), every Shape implementation
should provide a meaningful area() operation.
"""
)


def describe_shape(shape: Shape) -> str:
    return f"Area = {shape.area():.2f}"


for shape in [Circle(2), Rectangle(3, 4)]:
    print(describe_shape(shape))


# ============================================================================
# 21. INTERFACE SEGREGATION
# ============================================================================

section("21. Small Interfaces")

print(
    """
Large interfaces can force implementations to support operations they do not
need.

A smaller interface is often easier to implement and test.

Instead of requiring every data component to implement:

    read
    write
    delete
    export
    synchronize
    backup

split behavior into focused interfaces when the domain requires it.
"""
)


class Reader(Protocol):
    def read(self, key: str) -> str | None:
        ...


class Writer(Protocol):
    def write(self, key: str, value: str) -> None:
        ...


class SimpleKeyValueStore:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def read(self, key: str) -> str | None:
        return self._data.get(key)

    def write(self, key: str, value: str) -> None:
        self._data[key] = value


def write_configuration(writer: Writer) -> None:
    writer.write("environment", "production")


def read_configuration(reader: Reader) -> str | None:
    return reader.read("environment")


store = SimpleKeyValueStore()
write_configuration(store)
print("Configuration:", read_configuration(store))


# ============================================================================
# 22. DRY, KISS, AND YAGNI
# ============================================================================

section("22. Practical Design Heuristics")

print(
    """
DRY:
    Don't Repeat Yourself.

    Avoid duplicating the same knowledge or rule in many places.

KISS:
    Keep It Simple.

    Prefer the simplest design that correctly satisfies the requirements.

YAGNI:
    You Aren't Gonna Need It.

    Do not build speculative complexity without a real requirement.

These are heuristics, not absolute laws.

For example, removing every small duplication can create an abstraction that
is harder to understand than the original code.
"""
)


def calculate_discount(amount: float, rate: float) -> float:
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    if not 0 <= rate <= 1:
        raise ValueError("Rate must be between 0 and 1")

    return amount * rate


print("Discount:", calculate_discount(1000, 0.10))


# ============================================================================
# 23. ERROR HANDLING AS A DESIGN CONCERN
# ============================================================================

section("23. Error Handling and Design")

print(
    """
Errors are part of a component's contract.

A component should distinguish between:

    - invalid input
    - invalid state
    - expected business-rule failures
    - programming errors
    - external failures

Use exceptions when callers need to react to failure.

Avoid silently hiding important failures.
"""
)


class InsufficientFundsError(ValueError):
    """Domain-specific error for a bank withdrawal."""

    pass


class SecureBankAccount:
    def __init__(self, balance: Decimal) -> None:
        if balance < 0:
            raise ValueError("Balance cannot be negative")

        self._balance = balance

    @property
    def balance(self) -> Decimal:
        return self._balance

    def withdraw(self, amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        if amount > self._balance:
            raise InsufficientFundsError("Insufficient funds")

        self._balance -= amount


secure_account = SecureBankAccount(Decimal("1000"))

try:
    secure_account.withdraw(Decimal("1500"))
except InsufficientFundsError as error:
    print("Expected domain error:", error)


# ============================================================================
# 24. VALIDATION AT BOUNDARIES
# ============================================================================

section("24. Validation at Boundaries")

print(
    """
External data should be treated as untrusted or potentially invalid.

Typical boundaries include:

    - user input
    - HTTP requests
    - files
    - databases
    - environment variables
    - external APIs

Validate data before allowing it into sensitive domain operations.

Do not rely only on the user interface for validation because other callers
may bypass that interface.
"""
)


def parse_positive_integer(value: str) -> int:
    """Validate textual input before returning a domain value."""
    try:
        number = int(value)
    except ValueError as error:
        raise ValueError("Expected an integer") from error

    if number <= 0:
        raise ValueError("Integer must be positive")

    return number


for raw_value in ["10", "0", "abc"]:
    try:
        print(raw_value, "->", parse_positive_integer(raw_value))
    except ValueError as error:
        print(raw_value, "-> invalid:", error)


# ============================================================================
# 25. SECURITY CONSIDERATIONS
# ============================================================================

section("25. Security Considerations in Design")

print(
    """
Software design influences security.

Important principles include:

    1. Least privilege
       Give a component only the access it needs.

    2. Encapsulation
       Restrict direct modification of sensitive state.

    3. Input validation
       Reject invalid or dangerous input at system boundaries.

    4. Separation of concerns
       Keep security-sensitive operations isolated and reviewable.

    5. Dependency control
       Avoid unnecessary dependencies and uncontrolled external behavior.

    6. Avoid secret exposure
       Do not place passwords, API keys, or tokens directly in source code.

    7. Fail safely
       Error handling should not disclose unnecessary sensitive information.

A design boundary can become a security boundary, but a class marked with
an underscore is not itself a security mechanism.
"""
)


# ============================================================================
# 26. PERFORMANCE CONSIDERATIONS
# ============================================================================

section("26. Performance and Modularity")

print(
    """
Modularity has costs as well as benefits.

Potential costs:

    - additional function or method calls
    - object creation
    - abstraction layers
    - indirection
    - more interfaces
    - more complex dependency graphs

Potential benefits:

    - easier optimization of isolated components
    - easier caching
    - easier profiling
    - simpler testing
    - reduced accidental work
    - better maintainability

Do not remove useful design boundaries merely because an abstraction exists.
Measure performance before optimizing.
"""
)


def sum_numbers(values: Iterable[int]) -> int:
    """Simple modular operation."""
    return sum(values)


print("Performance-friendly calculation:", sum_numbers(range(1_000)))


# ============================================================================
# 27. OVER-ENGINEERING
# ============================================================================

section("27. Avoiding Over-Engineering")

print(
    """
Not every program needs:

    - ten interfaces
    - dependency injection frameworks
    - complex factories
    - deep inheritance
    - elaborate design patterns

A small script may be best served by a few functions.

A larger application may benefit from classes, interfaces, modules, and
layers.

Design should follow actual complexity and change requirements.
"""
)


def simple_area(width: float, height: float) -> float:
    """A simple function is enough for a simple requirement."""
    return width * height


print("Simple design:", simple_area(10, 20))


# ============================================================================
# 28. TESTABLE DESIGN
# ============================================================================

section("28. Testability as a Design Property")

print(
    """
Good boundaries make testing easier.

A unit is easier to test when it:

    - has explicit inputs
    - has predictable outputs
    - has few dependencies
    - avoids unnecessary global state
    - isolates external systems

Dependency injection is particularly useful because test doubles can replace
real infrastructure.
"""
)


class FakePaymentProcessor(PaymentProcessor):
    """Test double for payment processing."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def pay(self, amount: float) -> str:
        self.calls.append(amount)
        return "FAKE-TRANSACTION"


fake_processor = FakePaymentProcessor()

transaction_id = complete_payment(fake_processor, 250.0)

assert transaction_id == "FAKE-TRANSACTION"
assert fake_processor.calls == [250.0]

print("Test double transaction:", transaction_id)
print("Test assertions passed.")


# ============================================================================
# 29. DESIGNING FOR CHANGE
# ============================================================================

section("29. Designing Around Expected Change")

print(
    """
A useful design question is:

    "What is likely to change?"

Examples:

    Tax rules may change.
        -> Isolate tax calculation.

    Database technology may change.
        -> Hide persistence behind an interface.

    Notification provider may change.
        -> Depend on a notification abstraction.

    User interface may change.
        -> Keep business logic independent of presentation.

Stable business concepts should not unnecessarily depend on unstable
implementation details.
"""
)


class TaxPolicy(Protocol):
    def calculate(self, amount: float) -> float:
        ...


class IndianGSTPolicy:
    def calculate(self, amount: float) -> float:
        return amount * 0.18


class NoTaxPolicy:
    def calculate(self, amount: float) -> float:
        return 0.0


def price_with_tax(amount: float, policy: TaxPolicy) -> float:
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    return amount + policy.calculate(amount)


print("GST price:", price_with_tax(1000, IndianGSTPolicy()))
print("No-tax price:", price_with_tax(1000, NoTaxPolicy()))


# ============================================================================
# 30. REFACTORING
# ============================================================================

section("30. Refactoring Toward Better Design")

print(
    """
Refactoring changes internal structure without intentionally changing the
observable behavior.

Typical refactoring operations include:

    - extracting functions
    - extracting classes
    - renaming unclear identifiers
    - removing duplication
    - reducing coupling
    - introducing interfaces
    - replacing condition-heavy code
    - moving responsibilities to the correct component

A safe refactoring process usually relies on tests so that behavior can be
checked before and after the structural change.
"""
)


subsection("Before: one responsibility mixed with another")

def calculate_and_format_score(scores: list[float]) -> str:
    if not scores:
        raise ValueError("Scores cannot be empty")

    average = sum(scores) / len(scores)

    if average >= 90:
        grade = "A"
    elif average >= 75:
        grade = "B"
    elif average >= 60:
        grade = "C"
    else:
        grade = "D"

    return f"Average={average:.2f}, Grade={grade}"


print(calculate_and_format_score([80, 90, 85]))


subsection("After: responsibilities separated")

def calculate_average(scores: Iterable[float]) -> float:
    values = list(scores)

    if not values:
        raise ValueError("Scores cannot be empty")

    return sum(values) / len(values)


def grade_from_average(average: float) -> str:
    if average >= 90:
        return "A"

    if average >= 75:
        return "B"

    if average >= 60:
        return "C"

    return "D"


def format_score_report(average: float, grade: str) -> str:
    return f"Average={average:.2f}, Grade={grade}"


average = calculate_average([80, 90, 85])
grade = grade_from_average(average)

print(format_score_report(average, grade))


# ============================================================================
# 31. CONDITIONAL COMPLEXITY AND STRATEGIES
# ============================================================================

section("31. Replacing Growing Conditional Logic")

print(
    """
A long conditional chain can be acceptable when the number of cases is small.

When rules grow, strategy objects or mappings can isolate individual
behaviors.

The correct choice depends on complexity. Do not replace a three-line
conditional with ten classes merely to apply a design pattern.
"""
)


class PricingStrategy(Protocol):
    def calculate(self, amount: float) -> float:
        ...


class RegularPricing:
    def calculate(self, amount: float) -> float:
        return amount


class PremiumPricing:
    def calculate(self, amount: float) -> float:
        return amount * 0.90


class EmployeePricing:
    def calculate(self, amount: float) -> float:
        return amount * 0.80


class Checkout:
    def __init__(self, pricing_strategy: PricingStrategy) -> None:
        self._pricing_strategy = pricing_strategy

    def final_price(self, amount: float) -> float:
        if amount < 0:
            raise ValueError("Amount cannot be negative")

        return self._pricing_strategy.calculate(amount)


for strategy in [
    RegularPricing(),
    PremiumPricing(),
    EmployeePricing(),
]:
    checkout = Checkout(strategy)
    print("Price:", checkout.final_price(1000))


# ============================================================================
# 32. FACTORIES AS A DESIGN TECHNIQUE
# ============================================================================

section("32. Factory Functions")

print(
    """
A factory centralizes object creation when creation logic itself needs a
meaningful abstraction.

A factory is useful when:

    - object construction is complex
    - the concrete implementation varies
    - callers should not depend on creation details

A factory is unnecessary when construction is already simple.
"""
)


class Notification(ABC):
    @abstractmethod
    def send(self, recipient: str, message: str) -> str:
        raise NotImplementedError


class EmailNotification(Notification):
    def send(self, recipient: str, message: str) -> str:
        return f"EMAIL to {recipient}: {message}"


class SMSNotification(Notification):
    def send(self, recipient: str, message: str) -> str:
        return f"SMS to {recipient}: {message}"


def create_notification(channel: str) -> Notification:
    normalized = channel.strip().lower()

    if normalized == "email":
        return EmailNotification()

    if normalized == "sms":
        return SMSNotification()

    raise ValueError(f"Unsupported notification channel: {channel}")


for channel in ["email", "sms"]:
    notification = create_notification(channel)
    print(notification.send("user@example.com", "Order processed"))


# ============================================================================
# 33. STATE AND CONTROLLED TRANSITIONS
# ============================================================================

section("33. Encapsulating State Transitions")

class OrderStatus(Enum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


class StatefulOrder:
    """Only valid state transitions are permitted."""

    def __init__(self) -> None:
        self._status = OrderStatus.CREATED

    @property
    def status(self) -> OrderStatus:
        return self._status

    def pay(self) -> None:
        if self._status != OrderStatus.CREATED:
            raise ValueError("Only created orders can be paid")

        self._status = OrderStatus.PAID

    def ship(self) -> None:
        if self._status != OrderStatus.PAID:
            raise ValueError("Only paid orders can be shipped")

        self._status = OrderStatus.SHIPPED

    def cancel(self) -> None:
        if self._status in {OrderStatus.SHIPPED, OrderStatus.CANCELLED}:
            raise ValueError("Order cannot be cancelled in this state")

        self._status = OrderStatus.CANCELLED


stateful_order = StatefulOrder()

print("Initial status:", stateful_order.status.value)

stateful_order.pay()
print("After payment:", stateful_order.status.value)

stateful_order.ship()
print("After shipping:", stateful_order.status.value)

try:
    stateful_order.cancel()
except ValueError as error:
    print("Invalid state transition:", error)


# ============================================================================
# 34. DEPENDENCY GRAPHS
# ============================================================================

section("34. Managing Dependencies")

print(
    """
A dependency graph describes which components depend on which other
components.

A healthy design generally aims for:

    - few unnecessary dependencies
    - clear dependency direction
    - stable abstractions
    - limited cycles

Circular dependencies can make initialization, testing, and maintenance more
difficult.

A useful conceptual direction is:

    Presentation
        |
        v
    Application
        |
        v
    Domain
        ^
        |
    Infrastructure

Exact architecture varies, but dependency direction should be intentional.
"""
)


# ============================================================================
# 35. DOCUMENTING PUBLIC INTERFACES
# ============================================================================

section("35. Documentation as Part of Design")

print(
    """
Public interfaces should communicate their purpose clearly.

Useful documentation includes:

    - what an operation does
    - parameter meaning
    - return value
    - important exceptions
    - assumptions
    - invariants

Names are also part of the interface.

Prefer:

    calculate_monthly_payment()

over:

    calc()

Prefer:

    customer_repository

over:

    repo1

Good names reduce the amount of documentation needed to understand the code.
"""
)


def calculate_monthly_payment(
    principal: float,
    annual_rate_percent: float,
    months: int,
) -> float:
    """
    Calculate a monthly loan payment.

    principal:
        Positive loan amount.

    annual_rate_percent:
        Annual interest rate expressed as a percentage.

    months:
        Positive repayment duration in months.
    """
    return calculate_emi(principal, annual_rate_percent, months)


print("Monthly payment:", round(calculate_monthly_payment(100000, 8, 24), 2))


# ============================================================================
# 36. DESIGN EDGE CASES
# ============================================================================

section("36. Edge Cases")

print(
    """
Good design explicitly considers unusual but valid or invalid situations.

Examples:

    - empty collections
    - zero values
    - negative values
    - duplicate identifiers
    - invalid state transitions
    - unsupported types
    - missing dependencies
    - boundary values
    - extremely large inputs
    - floating-point precision
"""
)


def safe_average(values: Iterable[float]) -> float | None:
    numbers = list(values)

    if not numbers:
        return None

    return sum(numbers) / len(numbers)


print("Average of empty collection:", safe_average([]))
print("Average of one value:", safe_average([100]))
print("Average of negative values:", safe_average([-10, -20]))


# ============================================================================
# 37. FLOATING-POINT DESIGN CONSIDERATION
# ============================================================================

section("37. Choosing Appropriate Data Types")

print(
    """
Data types are design decisions.

Binary floating-point numbers are useful for many scientific and engineering
calculations, but they do not represent every decimal fraction exactly.

Financial applications often use Decimal when exact decimal arithmetic is
required.

The earlier Money class therefore used Decimal rather than float.
"""
)


float_result = 0.1 + 0.2
decimal_result = Decimal("0.1") + Decimal("0.2")

print("Float result:", float_result)
print("Decimal result:", decimal_result)


# ============================================================================
# 38. MODULE BOUNDARIES IN A REAL PROJECT
# ============================================================================

section("38. Typical Python Project Structure")

print(
    """
A larger application might separate files conceptually like this:

    project/
        domain/
            models.py
            pricing.py
        application/
            services.py
        infrastructure/
            repositories.py
            notifications.py
        presentation/
            cli.py
        tests/
            test_pricing.py
            test_services.py

The exact folder structure should reflect actual responsibilities.

A package should not be split into many files merely to make the project look
architecturally sophisticated.
"""
)


# ============================================================================
# 39. DESIGNING A SMALL LIBRARY
# ============================================================================

section("39. Small Library Design Example")

print(
    """
A reusable component should expose a small public API.

Internal helper functions can remain implementation details.

The following calculator exposes a focused public operation while keeping
validation and intermediate calculations private.
"""
)


class LoanCalculator:
    """Reusable loan-calculation abstraction."""

    def calculate_payment(
        self,
        principal: Decimal,
        annual_rate_percent: Decimal,
        months: int,
    ) -> Decimal:
        self._validate(principal, annual_rate_percent, months)

        monthly_rate = annual_rate_percent / Decimal("1200")

        if monthly_rate == 0:
            return principal / Decimal(months)

        factor = (Decimal("1") + monthly_rate) ** months

        payment = principal * monthly_rate * factor / (factor - 1)

        return payment.quantize(Decimal("0.01"))

    @staticmethod
    def _validate(
        principal: Decimal,
        annual_rate_percent: Decimal,
        months: int,
    ) -> None:
        if principal <= 0:
            raise ValueError("Principal must be positive")

        if annual_rate_percent < 0:
            raise ValueError("Interest rate cannot be negative")

        if months <= 0:
            raise ValueError("Months must be positive")


loan_calculator = LoanCalculator()

print(
    "Precise loan payment:",
    loan_calculator.calculate_payment(
        Decimal("500000"),
        Decimal("8.5"),
        60,
    ),
)


# ============================================================================
# 40. PUBLIC API VERSUS INTERNAL IMPLEMENTATION
# ============================================================================

section("40. Public API and Internal Details")

print(
    """
A useful rule is:

    Make the public API as small as practical.

Every public method or attribute can become a dependency for other code.

Once many callers depend on an implementation detail, changing that detail
can become expensive.

A small public API gives maintainers more freedom to change internals.
"""
)


class TemperatureConverter:
    """Public API exposes conversion operations."""

    def celsius_to_fahrenheit(self, celsius: float) -> float:
        return self._to_fahrenheit(celsius)

    def fahrenheit_to_celsius(self, fahrenheit: float) -> float:
        return self._to_celsius(fahrenheit)

    @staticmethod
    def _to_fahrenheit(celsius: float) -> float:
        return celsius * 9 / 5 + 32

    @staticmethod
    def _to_celsius(fahrenheit: float) -> float:
        return (fahrenheit - 32) * 5 / 9


converter = TemperatureConverter()
print("25 C -> F:", converter.celsius_to_fahrenheit(25))
print("77 F -> C:", converter.fahrenheit_to_celsius(77))


# ============================================================================
# 41. DESIGN SMELLS
# ============================================================================

section("41. Common Design Smells")

print(
    """
A design smell is a warning sign that structure may need attention.

Common examples:

    God object:
        One class knows or controls too much.

    Long method:
        A method contains too many responsibilities or too much logic.

    Long parameter list:
        A function requires too many independent inputs.

    Feature envy:
        One component relies heavily on another component's internal data.

    Shotgun surgery:
        One conceptual change requires edits across many unrelated files.

    Duplicated logic:
        The same business rule appears in multiple places.

    Hidden dependency:
        A component secretly relies on global state or internally created
        services.

    Premature abstraction:
        A generalized structure exists without a real need.

A smell is not automatically a defect. Context determines whether refactoring
is appropriate.
"""
)


# ============================================================================
# 42. COMMON MISTAKES
# ============================================================================

section("42. Common Software Design Mistakes")

mistakes = [
    (
        "One giant class",
        "Mixing persistence, business rules, UI, validation, and networking.",
    ),
    (
        "Uncontrolled state",
        "Allowing callers to directly create invalid object state.",
    ),
    (
        "Too many abstractions",
        "Creating interfaces and factories for trivial behavior.",
    ),
    (
        "High coupling",
        "Making one component depend on many concrete implementation details.",
    ),
    (
        "Low cohesion",
        "Combining unrelated operations because they are all called utilities.",
    ),
    (
        "Premature optimization",
        "Complicating architecture before identifying an actual performance issue.",
    ),
    (
        "Global mutable state",
        "Allowing unrelated parts of the program to modify shared state.",
    ),
    (
        "Leaky abstraction",
        "Forcing callers to understand implementation details.",
    ),
    (
        "Weak validation",
        "Allowing invalid external data into domain logic.",
    ),
    (
        "Ignoring error contracts",
        "Allowing failures to be inconsistent or silently ignored.",
    ),
]

for name, description in mistakes:
    print(f"{name}: {description}")


# ============================================================================
# 43. DESIGN TRADE-OFFS
# ============================================================================

section("43. Design Trade-Offs")

print(
    """
Software design is a balancing activity.

                    Simplicity
                       /\
                      /  \
                     /    \
                    /      \
             Flexibility ---- Performance

There is no universally best architecture.

Increasing abstraction can improve flexibility but increase complexity.

Increasing modularity can improve maintainability but create more interfaces.

Increasing validation can improve correctness but add processing and code.

Increasing encapsulation can improve invariants but may make some operations
less direct.

Good design considers:

    - current requirements
    - expected change
    - team understanding
    - testing requirements
    - reliability
    - performance
    - security
    - operational constraints
"""
)


# ============================================================================
# 44. INTEGRATED DESIGN EXAMPLE
# ============================================================================

section("44. Integrated Example: Order Processing System")

print(
    """
The following example combines the main principles.

Responsibilities are separated into:

    Product
        Domain data.

    OrderLine
        Domain representation of one purchased product.

    PricingPolicy
        Pricing abstraction.

    OrderRepository
        Persistence abstraction.

    NotificationService
        Notification abstraction.

    OrderService
        Application orchestration.

The service depends on abstractions rather than concrete external systems.
"""


@dataclass(frozen=True)
class ProductRecord:
    product_id: int
    name: str
    price: Decimal

    def __post_init__(self) -> None:
        if self.product_id <= 0:
            raise ValueError("Product ID must be positive")

        if not self.name.strip():
            raise ValueError("Product name cannot be empty")

        if self.price < 0:
            raise ValueError("Product price cannot be negative")


@dataclass(frozen=True)
class OrderLine:
    product: ProductRecord
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")

    @property
    def subtotal(self) -> Decimal:
        return self.product.price * self.quantity


class OrderPricingPolicy(Protocol):
    def calculate_total(self, subtotal: Decimal) -> Decimal:
        ...


class StandardOrderPricing:
    """Standard 18% tax with a 10% discount for large orders."""

    def calculate_total(self, subtotal: Decimal) -> Decimal:
        if subtotal < 0:
            raise ValueError("Subtotal cannot be negative")

        discount = (
            subtotal * Decimal("0.10")
            if subtotal >= Decimal("10000")
            else Decimal("0")
        )

        taxable_amount = subtotal - discount
        tax = taxable_amount * Decimal("0.18")

        return (taxable_amount + tax).quantize(Decimal("0.01"))


class OrderStore(Protocol):
    def save(self, order_id: int, lines: list[OrderLine]) -> None:
        ...

    def find(self, order_id: int) -> list[OrderLine] | None:
        ...


class MemoryOrderStore:
    def __init__(self) -> None:
        self._orders: dict[int, list[OrderLine]] = {}

    def save(self, order_id: int, lines: list[OrderLine]) -> None:
        if order_id <= 0:
            raise ValueError("Order ID must be positive")

        # Copy the collection so callers cannot mutate our internal list.
        self._orders[order_id] = list(lines)

    def find(self, order_id: int) -> list[OrderLine] | None:
        lines = self._orders.get(order_id)

        if lines is None:
            return None

        # Return a copy to protect internal collection state.
        return list(lines)


class NotificationService(Protocol):
    def notify(self, message: str) -> None:
        ...


class ConsoleNotificationService:
    def notify(self, message: str) -> None:
        print("NOTIFICATION:", message)


class OrderService:
    """
    Coordinates the use case.

    It does not know how orders are physically stored or how notifications
    are delivered.
    """

    def __init__(
        self,
        store: OrderStore,
        pricing_policy: OrderPricingPolicy,
        notifier: NotificationService,
    ) -> None:
        self._store = store
        self._pricing_policy = pricing_policy
        self._notifier = notifier

    def create_order(
        self,
        order_id: int,
        lines: list[OrderLine],
    ) -> Decimal:
        if order_id <= 0:
            raise ValueError("Order ID must be positive")

        if not lines:
            raise ValueError("Order must contain at least one line")

        subtotal = sum(
            (line.subtotal for line in lines),
            Decimal("0"),
        )

        total = self._pricing_policy.calculate_total(subtotal)

        self._store.save(order_id, lines)

        self._notifier.notify(
            f"Order {order_id} created. Total={total}"
        )

        return total


laptop = ProductRecord(
    product_id=1,
    name="Laptop",
    price=Decimal("70000.00"),
)

mouse = ProductRecord(
    product_id=2,
    name="Mouse",
    price=Decimal("1500.00"),
)

lines = [
    OrderLine(laptop, 1),
    OrderLine(mouse, 2),
]

integrated_store = MemoryOrderStore()
integrated_notifier = ConsoleNotificationService()
integrated_pricing = StandardOrderPricing()

integrated_service = OrderService(
    store=integrated_store,
    pricing_policy=integrated_pricing,
    notifier=integrated_notifier,
)

order_total = integrated_service.create_order(
    order_id=1001,
    lines=lines,
)

print("Integrated order total:", order_total)


# ============================================================================
# 45. TESTING DESIGN BOUNDARIES
# ============================================================================

section("45. Testing the Integrated Design")

print(
    """
The design allows individual components to be tested independently.

The following assertions test domain behavior, pricing behavior, and service
behavior without requiring a real database or external notification provider.
"""


class RecordingNotifier:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def notify(self, message: str) -> None:
        self.messages.append(message)


test_product = ProductRecord(
    product_id=10,
    name="Test Product",
    price=Decimal("100"),
)

test_line = OrderLine(test_product, 2)

assert test_line.subtotal == Decimal("200")

test_pricing = StandardOrderPricing()

assert test_pricing.calculate_total(Decimal("100")) == Decimal("118.00")

test_store = MemoryOrderStore()
test_notifier = RecordingNotifier()

test_service = OrderService(
    store=test_store,
    pricing_policy=test_pricing,
    notifier=test_notifier,
)

test_total = test_service.create_order(
    500,
    [test_line],
)

assert test_total == Decimal("236.00")
assert test_store.find(500) is not None
assert len(test_notifier.messages) == 1

print("Integrated design tests passed.")


# ============================================================================
# 46. EDGE-CASE TESTS
# ============================================================================

section("46. Testing Invalid States")

invalid_tests = [
    (
        "negative product price",
        lambda: ProductRecord(1, "Product", Decimal("-1")),
    ),
    (
        "zero quantity",
        lambda: OrderLine(test_product, 0),
    ),
    (
        "empty order",
        lambda: integrated_service.create_order(999, []),
    ),
    (
        "negative order ID",
        lambda: integrated_service.create_order(-1, [test_line]),
    ),
]

for test_name, operation in invalid_tests:
    try:
        operation()
    except (ValueError, TypeError) as error:
        print(f"{test_name}: correctly rejected -> {error}")
    else:
        raise AssertionError(
            f"Expected {test_name} to be rejected"
        )


# ============================================================================
# 47. DESIGN REVIEW CHECKLIST
# ============================================================================

section("47. Practical Design Review Checklist")

design_review_questions = [
    "Does each component have a clear responsibility?",
    "Are related responsibilities grouped together?",
    "Are unrelated responsibilities separated?",
    "Can important business rules be located easily?",
    "Are implementation details hidden where appropriate?",
    "Are public interfaces small and meaningful?",
    "Can dependencies be replaced during testing?",
    "Are invalid states prevented?",
    "Are external inputs validated?",
    "Is dependency direction intentional?",
    "Are abstractions justified by real requirements?",
    "Is the design understandable to another developer?",
    "Can likely changes be made without widespread modification?",
    "Are performance-sensitive boundaries known?",
    "Are security-sensitive operations isolated and controlled?",
    "Are error conditions part of the component contract?",
    "Is mutable shared state minimized?",
]

for number, question in enumerate(design_review_questions, start=1):
    print(f"{number:02d}. {question}")


# ============================================================================
# 48. MODULARITY, ABSTRACTION, AND ENCAPSULATION COMPARED
# ============================================================================

section("48. Comparing the Three Core Concepts")

comparison = [
    (
        "Modularity",
        "How software is divided into components.",
        "Separate order processing from notification.",
    ),
    (
        "Abstraction",
        "What a component exposes while hiding unnecessary details.",
        "PaymentProcessor.pay(amount).",
    ),
    (
        "Encapsulation",
        "How state and behavior are grouped and controlled.",
        "BankAccount.withdraw() protects balance rules.",
    ),
    (
        "Information hiding",
        "Preventing external code from depending on volatile details.",
        "Cache users call get() rather than accessing its dictionary.",
    ),
]

for concept, meaning, example in comparison:
    print(f"\n{concept}")
    print(f"  Meaning: {meaning}")
    print(f"  Example: {example}")


# ============================================================================
# 49. ADVANCED DESIGN PRINCIPLES
# ============================================================================

section("49. Advanced Design Principles")

print(
    """
Important relationships:

    High cohesion
        Components focus on closely related responsibilities.

    Low coupling
        Components avoid unnecessary dependence on implementation details.

    Abstraction
        Defines meaningful behavior.

    Encapsulation
        Protects state and invariants.

    Dependency inversion
        Keeps high-level policy independent from volatile implementations.

    Composition
        Builds larger behavior from smaller components.

    Separation of concerns
        Prevents unrelated responsibilities from becoming intertwined.

These principles reinforce one another.

For example:

    dependency inversion
        encourages interfaces

    interfaces
        reduce coupling

    reduced coupling
        makes modular replacement easier

    encapsulation
        protects internal state

    protected state
        makes invariants easier to maintain

    cohesive modules
        make responsibilities easier to understand and test
"""
)


# ============================================================================
# 50. FINAL SELF-CONTAINED DESIGN DEMONSTRATION
# ============================================================================

section("50. Final Demonstration")

print(
    """
The final demonstration uses all three primary concepts directly.

Modularity:
    Pricing, storage, and notification are separate components.

Abstraction:
    Services depend on protocols rather than concrete implementations.

Encapsulation:
    Internal collections and state are protected behind methods.
"""
)


class AuditLog(Protocol):
    def record(self, event: str) -> None:
        ...


class InMemoryAuditLog:
    def __init__(self) -> None:
        self._events: list[str] = []

    def record(self, event: str) -> None:
        if not event.strip():
            raise ValueError("Audit event cannot be empty")

        self._events.append(event)

    @property
    def events(self) -> tuple[str, ...]:
        # A tuple prevents callers from modifying our internal list.
        return tuple(self._events)


class BusinessOperation:
    """Small high-level component depending on an abstraction."""

    def __init__(self, audit_log: AuditLog) -> None:
        self._audit_log = audit_log
        self._completed = False

    @property
    def completed(self) -> bool:
        return self._completed

    def execute(self, operation_name: str) -> None:
        if not operation_name.strip():
            raise ValueError("Operation name is required")

        self._audit_log.record(
            f"Operation executed: {operation_name}"
        )

        self._completed = True


audit_log = InMemoryAuditLog()
operation = BusinessOperation(audit_log)

operation.execute("Create customer")

print("Operation completed:", operation.completed)
print("Audit events:", audit_log.events)


# ============================================================================
# 51. EXECUTION CHECK
# ============================================================================

section("51. Execution Check")

print(
    """
The script has completed its executable demonstrations.

Key design vocabulary demonstrated in code:

    modularity
    cohesion
    coupling
    separation of concerns
    abstraction
    encapsulation
    information hiding
    interfaces
    contracts
    composition
    dependency injection
    dependency inversion
    immutability
    invariants
    validation
    substitutability
    interface segregation
    extensibility
    refactoring
    testability
    error handling
    security boundaries
    performance trade-offs
    design smells
    layered organization
"""
)

print("\nAll executable assertions completed successfully.")
