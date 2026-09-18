"""
Object-Oriented Programming Principles
=======================================

Topic:
    Encapsulation, inheritance, polymorphism, and abstraction.

This standalone study program progresses from beginner-level OOP concepts to
advanced design considerations. Every major principle is demonstrated with
executable Python code.

Requirements:
    Python 3.10+

No external packages are required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Callable, Iterable, Iterator, Protocol
import math
import statistics
import time


# ============================================================================
# 1. OBJECTS, CLASSES, ATTRIBUTES, AND METHODS
# ============================================================================

print("=" * 78)
print("1. OBJECTS, CLASSES, ATTRIBUTES, AND METHODS")
print("=" * 78)


class Person:
    """A simple class used to introduce objects and methods."""

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def introduce(self) -> str:
        return f"My name is {self.name} and I am {self.age} years old."


person = Person("Atul", 30)

print(person.introduce())
print("Object type:", type(person).__name__)
print("Object attributes:", person.__dict__)


# ============================================================================
# 2. ENCAPSULATION
# ============================================================================

print("\n" + "=" * 78)
print("2. ENCAPSULATION")
print("=" * 78)

"""
Encapsulation means keeping an object's data and the operations that govern
that data together while controlling how the internal state can be accessed.

Python does not enforce Java/C++-style private fields with a strict access
modifier. Instead, Python commonly uses:

    public_name
    _internal_name       -> conventionally internal/protected
    __private_name       -> name mangling

Properties provide a controlled public interface over internal state.
"""


class BankAccount:
    """Demonstrates controlled access to account state."""

    def __init__(self, owner: str, opening_balance: float = 0.0) -> None:
        if not owner.strip():
            raise ValueError("Owner name cannot be empty.")
        if opening_balance < 0:
            raise ValueError("Opening balance cannot be negative.")

        self.owner = owner
        self._balance = float(opening_balance)
        self.__transaction_count = 0

    @property
    def balance(self) -> float:
        """Read-only public access to the internal balance."""
        return self._balance

    @property
    def transaction_count(self) -> int:
        return self.__transaction_count

    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit must be positive.")

        self._balance += amount
        self.__transaction_count += 1

    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal must be positive.")
        if amount > self._balance:
            raise ValueError("Insufficient funds.")

        self._balance -= amount
        self.__transaction_count += 1


account = BankAccount("Atul", 10_000)
account.deposit(2_500)
account.withdraw(1_250)

print(f"Owner: {account.owner}")
print(f"Balance: {account.balance:.2f}")
print(f"Transactions: {account.transaction_count}")

try:
    account.withdraw(20_000)
except ValueError as error:
    print("Controlled error:", error)

try:
    account.deposit(-100)
except ValueError as error:
    print("Controlled error:", error)

# The double underscore causes name mangling.
print("Name-mangled private field exists internally as:",
      "_BankAccount__transaction_count" in account.__dict__)


# ============================================================================
# 3. PROPERTY VALIDATION
# ============================================================================

print("\n" + "=" * 78)
print("3. PROPERTIES AND INVARIANTS")
print("=" * 78)


class Temperature:
    """Stores Celsius internally while exposing a validated property."""

    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        if value < -273.15:
            raise ValueError("Temperature cannot be below absolute zero.")
        self._celsius = float(value)

    @property
    def fahrenheit(self) -> float:
        return self.celsius * 9 / 5 + 32

    @fahrenheit.setter
    def fahrenheit(self, value: float) -> None:
        self.celsius = (value - 32) * 5 / 9


temperature = Temperature(25)
print("Celsius:", temperature.celsius)
print("Fahrenheit:", temperature.fahrenheit)

temperature.fahrenheit = 212
print("After setting Fahrenheit to 212:", temperature.celsius)

try:
    temperature.celsius = -300
except ValueError as error:
    print("Validation error:", error)


# ============================================================================
# 4. INHERITANCE
# ============================================================================

print("\n" + "=" * 78)
print("4. INHERITANCE")
print("=" * 78)

"""
Inheritance creates a relationship in which a specialized class reuses or
extends behavior from a more general class.

Terminology:

    superclass / base class / parent class
    subclass / derived class / child class

Inheritance should represent a genuine "is-a" relationship.

Examples:
    Dog is an Animal.
    Manager is an Employee.

It should not be used simply because two classes happen to share code.
"""


class Animal:
    def __init__(self, name: str) -> None:
        self.name = name

    def eat(self) -> str:
        return f"{self.name} is eating."

    def speak(self) -> str:
        return f"{self.name} makes a sound."


class Dog(Animal):
    def speak(self) -> str:
        return f"{self.name} says woof."


class Cat(Animal):
    def speak(self) -> str:
        return f"{self.name} says meow."


dog = Dog("Bruno")
cat = Cat("Luna")

print(dog.eat())
print(dog.speak())
print(cat.eat())
print(cat.speak())


# ============================================================================
# 5. MULTILEVEL AND HIERARCHICAL INHERITANCE
# ============================================================================

print("\n" + "=" * 78)
print("5. MULTILEVEL AND HIERARCHICAL INHERITANCE")
print("=" * 78)


class LivingThing:
    def breathe(self) -> str:
        return "Breathing."


class Mammal(LivingThing):
    def feed_milk(self) -> str:
        return "Produces milk for offspring."


class Human(Mammal):
    def think(self) -> str:
        return "Uses complex reasoning."


class Bird(LivingThing):
    def fly(self) -> str:
        return "Flying."


human = Human()
bird = Bird()

print("Multilevel inheritance:", human.breathe(), human.feed_milk(), human.think())
print("Hierarchical inheritance:", bird.breathe(), bird.fly())


# ============================================================================
# 6. MULTIPLE INHERITANCE
# ============================================================================

print("\n" + "=" * 78)
print("6. MULTIPLE INHERITANCE AND METHOD RESOLUTION ORDER")
print("=" * 78)


class LoggerMixin:
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class JsonMixin:
    def to_json_like(self) -> dict[str, str]:
        return self.__dict__.copy()


class Service(LoggerMixin, JsonMixin):
    def __init__(self, name: str) -> None:
        self.name = name


service = Service("Payment Service")
service.log("Service started.")
print("Serializable state:", service.to_json_like())
print("MRO:", [cls.__name__ for cls in Service.mro()])


# ============================================================================
# 7. SUPER()
# ============================================================================

print("\n" + "=" * 78)
print("7. SUPER()")
print("=" * 78)


class Employee:
    def __init__(self, name: str, employee_id: str) -> None:
        self.name = name
        self.employee_id = employee_id

    def describe(self) -> str:
        return f"{self.name} ({self.employee_id})"


class Manager(Employee):
    def __init__(self, name: str, employee_id: str, team_size: int) -> None:
        super().__init__(name, employee_id)
        if team_size < 0:
            raise ValueError("Team size cannot be negative.")
        self.team_size = team_size

    def describe(self) -> str:
        return f"{super().describe()}, manages {self.team_size} people"


manager = Manager("Priya", "M-100", 12)
print(manager.describe())


# ============================================================================
# 8. POLYMORPHISM
# ============================================================================

print("\n" + "=" * 78)
print("8. POLYMORPHISM")
print("=" * 78)

"""
Polymorphism means that the same interface or operation can work with objects
of different concrete types.

Python commonly achieves polymorphism through:

    method overriding
    duck typing
    abstract base classes
    protocols
    operator overloading

The calling code can focus on the behavior it needs instead of checking the
concrete class of every object.
"""


def make_animal_speak(animal: Animal) -> str:
    return animal.speak()


animals: list[Animal] = [Dog("Max"), Cat("Milo"), Dog("Rocky")]

for animal in animals:
    print(make_animal_speak(animal))


# ============================================================================
# 9. DUCK TYPING
# ============================================================================

print("\n" + "=" * 78)
print("9. DUCK TYPING")
print("=" * 78)


class Robot:
    def speak(self) -> str:
        return "Robot voice activated."


class Parrot:
    def speak(self) -> str:
        return "Parrot repeats the message."


def announce_speaker(speaker: object) -> str:
    """
    Python can use behavior without requiring a specific inheritance tree.
    Runtime validation makes the failure explicit when the method is absent.
    """
    speak_method = getattr(speaker, "speak", None)

    if not callable(speak_method):
        raise TypeError("Object must provide a callable speak() method.")

    return speak_method()


for speaker in [Dog("Buddy"), Robot(), Parrot()]:
    print(announce_speaker(speaker))


# ============================================================================
# 10. ABSTRACTION
# ============================================================================

print("\n" + "=" * 78)
print("10. ABSTRACTION")
print("=" * 78)

"""
Abstraction exposes the essential operations while hiding implementation
details.

An abstract base class can define a contract that concrete subclasses must
implement.

The user of the abstraction does not need to know how each implementation
performs its work.
"""


class PaymentProcessor(ABC):
    """Abstract contract for payment systems."""

    @abstractmethod
    def authorize(self, amount: float) -> bool:
        """Authorize a payment."""
        raise NotImplementedError

    @abstractmethod
    def capture(self, amount: float) -> str:
        """Capture an authorized payment."""
        raise NotImplementedError

    def process(self, amount: float) -> str:
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        if not self.authorize(amount):
            return "Payment authorization failed."

        return self.capture(amount)


class CardPayment(PaymentProcessor):
    def authorize(self, amount: float) -> bool:
        return amount <= 100_000

    def capture(self, amount: float) -> str:
        return f"Card payment captured: {amount:.2f}"


class WalletPayment(PaymentProcessor):
    def authorize(self, amount: float) -> bool:
        return amount <= 50_000

    def capture(self, amount: float) -> str:
        return f"Wallet payment captured: {amount:.2f}"


processors: list[PaymentProcessor] = [
    CardPayment(),
    WalletPayment(),
]

for processor in processors:
    print(processor.process(2_500))

try:
    PaymentProcessor()
except TypeError as error:
    print("Abstract-class error:", error)


# ============================================================================
# 11. ABSTRACT CLASS VS CONCRETE CLASS
# ============================================================================

print("\n" + "=" * 78)
print("11. ABSTRACT CLASS VS CONCRETE CLASS")
print("=" * 78)

print("PaymentProcessor defines what payment processors must do.")
print("CardPayment and WalletPayment define how those operations are performed.")


# ============================================================================
# 12. PROTOCOLS AND STRUCTURAL POLYMORPHISM
# ============================================================================

print("\n" + "=" * 78)
print("12. PROTOCOLS")
print("=" * 78)


class Exportable(Protocol):
    def export(self) -> str:
        ...


class CsvReport:
    def export(self) -> str:
        return "id,name\n1,Atul\n2,Priya"


class JsonReport:
    def export(self) -> str:
        return '[{"id":1,"name":"Atul"},{"id":2,"name":"Priya"}]'


def save_report(report: Exportable) -> str:
    """The function depends on a capability, not an inheritance hierarchy."""
    return report.export()


for report in [CsvReport(), JsonReport()]:
    print(save_report(report))


# ============================================================================
# 13. METHOD OVERRIDING
# ============================================================================

print("\n" + "=" * 78)
print("13. METHOD OVERRIDING")
print("=" * 78)


class Notification:
    def send(self, recipient: str, message: str) -> str:
        return f"Generic notification to {recipient}: {message}"


class EmailNotification(Notification):
    def send(self, recipient: str, message: str) -> str:
        return f"Email sent to {recipient}: {message}"


class SmsNotification(Notification):
    def send(self, recipient: str, message: str) -> str:
        return f"SMS sent to {recipient}: {message}"


notifications: list[Notification] = [
    EmailNotification(),
    SmsNotification(),
]

for notification in notifications:
    print(notification.send("user@example.com", "Account updated."))


# ============================================================================
# 14. OPERATOR OVERLOADING
# ============================================================================

print("\n" + "=" * 78)
print("14. OPERATOR OVERLOADING")
print("=" * 78)


@total_ordering
class Money:
    """A small immutable-style value object for monetary calculations."""

    def __init__(self, amount: float, currency: str = "INR") -> None:
        if not math.isfinite(amount):
            raise ValueError("Amount must be finite.")
        if len(currency) != 3:
            raise ValueError("Currency must use a three-letter code.")

        self.amount = float(amount)
        self.currency = currency.upper()

    def _check_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError("Cannot operate on different currencies.")

    def __add__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._check_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.currency == other.currency and math.isclose(
            self.amount, other.amount
        )

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_currency(other)
        return self.amount < other.amount

    def __repr__(self) -> str:
        return f"Money({self.amount:.2f}, {self.currency!r})"


money_a = Money(1000)
money_b = Money(250)

print("Addition:", money_a + money_b)
print("Subtraction:", money_a - money_b)
print("Comparison:", money_a > money_b)

try:
    print(money_a + Money(10, "USD"))
except ValueError as error:
    print("Currency error:", error)


# ============================================================================
# 15. DATACLASSES
# ============================================================================

print("\n" + "=" * 78)
print("15. DATACLASSES")
print("=" * 78)


@dataclass
class Product:
    """Dataclass automatically supplies useful object-model behavior."""

    product_id: int
    name: str
    price: float
    tags: list[str] = field(default_factory=list)

    def discounted_price(self, percentage: float) -> float:
        if not 0 <= percentage <= 100:
            raise ValueError("Discount must be between 0 and 100.")
        return self.price * (1 - percentage / 100)


product = Product(101, "Laptop", 80_000, ["computer", "electronics"])
print(product)
print("After 10% discount:", product.discounted_price(10))


# ============================================================================
# 16. COMPOSITION
# ============================================================================

print("\n" + "=" * 78)
print("16. COMPOSITION")
print("=" * 78)

"""
Composition means building an object from other objects.

"Has-a" relationships are often better represented with composition.

A Car has an Engine.
A Computer has a CPU.

Composition usually produces less coupling than deep inheritance trees.
"""


class Engine:
    def start(self) -> str:
        return "Engine started."

    def stop(self) -> str:
        return "Engine stopped."


class Car:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def start(self) -> str:
        return self.engine.start()


car = Car(Engine())
print(car.start())


# ============================================================================
# 17. DEPENDENCY INJECTION
# ============================================================================

print("\n" + "=" * 78)
print("17. DEPENDENCY INJECTION")
print("=" * 78)


class AuditLogger:
    def record(self, message: str) -> str:
        return f"AUDIT: {message}"


class OrderService:
    """
    The logger is supplied from outside.

    This makes the class easier to test and replace without changing its
    business logic.
    """

    def __init__(self, logger: AuditLogger) -> None:
        self.logger = logger

    def create_order(self, order_id: str) -> str:
        return self.logger.record(f"Order {order_id} created.")


order_service = OrderService(AuditLogger())
print(order_service.create_order("ORD-001"))


# ============================================================================
# 18. ENCAPSULATED DOMAIN MODEL
# ============================================================================

print("\n" + "=" * 78)
print("18. ENCAPSULATED DOMAIN MODEL")
print("=" * 78)


class InventoryItem:
    """Demonstrates state, invariants, and domain operations."""

    def __init__(self, sku: str, quantity: int = 0) -> None:
        if not sku.strip():
            raise ValueError("SKU cannot be empty.")
        if quantity < 0:
            raise ValueError("Quantity cannot be negative.")

        self.sku = sku
        self._quantity = quantity

    @property
    def quantity(self) -> int:
        return self._quantity

    def restock(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Restock quantity must be positive.")
        self._quantity += quantity

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Reservation quantity must be positive.")
        if quantity > self._quantity:
            raise ValueError("Not enough inventory.")
        self._quantity -= quantity


inventory = InventoryItem("LAPTOP-001", 10)
inventory.reserve(3)
inventory.restock(5)

print("SKU:", inventory.sku)
print("Available:", inventory.quantity)


# ============================================================================
# 19. MULTIPLE DISPATCH AND SINGLE DISPATCH
# ============================================================================

print("\n" + "=" * 78)
print("19. POLYMORPHIC DISPATCH")
print("=" * 78)

"""
Traditional object-oriented polymorphism generally dispatches a method based
on the runtime type of one receiver object.

Python also provides functools.singledispatch for function-based dispatch.
"""


from functools import singledispatch


@singledispatch
def describe_value(value: object) -> str:
    return f"Generic object: {type(value).__name__}"


@describe_value.register
def _(value: int) -> str:
    return f"Integer: {value}"


@describe_value.register
def _(value: str) -> str:
    return f"String with {len(value)} characters"


@describe_value.register
def _(value: list) -> str:
    return f"List with {len(value)} elements"


for value in [42, "Python", [1, 2, 3]]:
    print(describe_value(value))


# ============================================================================
# 20. SOLID-RELATED DESIGN
# ============================================================================

print("\n" + "=" * 78)
print("20. SOLID-RELATED DESIGN PRINCIPLES")
print("=" * 78)

"""
The four OOP principles are closely related to larger design principles.

S - Single Responsibility Principle:
    A class should have a focused reason to change.

O - Open/Closed Principle:
    Software should be open for extension while avoiding unnecessary changes
    to stable existing behavior.

L - Liskov Substitution Principle:
    A subtype should behave consistently with expectations established by its
    base abstraction.

I - Interface Segregation Principle:
    Clients should not be forced to depend on operations they do not use.

D - Dependency Inversion Principle:
    High-level policy should depend on abstractions rather than concrete
    implementation details.

These are design guidelines, not absolute laws.
"""


class DiscountPolicy(Protocol):
    def calculate(self, price: float) -> float:
        ...


class NoDiscount:
    def calculate(self, price: float) -> float:
        return price


class PercentageDiscount:
    def __init__(self, percentage: float) -> None:
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100.")
        self.percentage = percentage

    def calculate(self, price: float) -> float:
        return price * (1 - self.percentage / 100)


def final_price(price: float, policy: DiscountPolicy) -> float:
    if price < 0:
        raise ValueError("Price cannot be negative.")
    return policy.calculate(price)


print("No discount:", final_price(1000, NoDiscount()))
print("20% discount:", final_price(1000, PercentageDiscount(20)))


# ============================================================================
# 21. LISKOV SUBSTITUTION PITFALL
# ============================================================================

print("\n" + "=" * 78)
print("21. INHERITANCE PITFALL: LISKOV SUBSTITUTION")
print("=" * 78)

"""
A classic conceptual problem is modeling Square as a subclass of Rectangle
when Rectangle permits width and height to vary independently.

The issue is not that inheritance syntax fails. The problem is that the
subclass changes assumptions made by code using the parent abstraction.

This demonstrates why inheritance should be based on behavioral contracts,
not merely shared attributes.
"""


class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        if width < 0 or height < 0:
            raise ValueError("Dimensions cannot be negative.")
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height


class Square:
    """A separate model avoids pretending it supports Rectangle semantics."""

    def __init__(self, side: float) -> None:
        if side < 0:
            raise ValueError("Side cannot be negative.")
        self.side = side

    def area(self) -> float:
        return self.side * self.side


print("Rectangle area:", Rectangle(4, 5).area())
print("Square area:", Square(4).area())


# ============================================================================
# 22. IMMUTABILITY AND VALUE OBJECTS
# ============================================================================

print("\n" + "=" * 78)
print("22. IMMUTABILITY AND VALUE OBJECTS")
print("=" * 78)


@dataclass(frozen=True)
class Coordinate:
    """Frozen dataclasses prevent ordinary attribute reassignment."""

    x: float
    y: float

    def distance_from_origin(self) -> float:
        return math.hypot(self.x, self.y)


point = Coordinate(3, 4)
print(point)
print("Distance:", point.distance_from_origin())

try:
    point.x = 10
except Exception as error:
    print("Immutable object error:", error)


# ============================================================================
# 23. ITERATORS AS OBJECTS
# ============================================================================

print("\n" + "=" * 78)
print("23. OBJECTS CAN IMPLEMENT PROTOCOLS")
print("=" * 78)


class Countdown:
    """A custom iterable demonstrating __iter__ and __next__."""

    def __init__(self, start: int) -> None:
        self.start = start

    def __iter__(self) -> Iterator[int]:
        current = self.start

        while current > 0:
            yield current
            current -= 1


print("Countdown:", list(Countdown(5)))


# ============================================================================
# 24. ADVANCED CASE: PLUGGABLE SHIPPING SYSTEM
# ============================================================================

print("\n" + "=" * 78)
print("24. ADVANCED CASE: PLUGGABLE SHIPPING SYSTEM")
print("=" * 78)


@dataclass(frozen=True)
class Shipment:
    shipment_id: str
    weight_kg: float
    distance_km: float

    def __post_init__(self) -> None:
        if not self.shipment_id.strip():
            raise ValueError("Shipment ID is required.")
        if self.weight_kg <= 0:
            raise ValueError("Weight must be positive.")
        if self.distance_km < 0:
            raise ValueError("Distance cannot be negative.")


class ShippingProvider(ABC):
    @abstractmethod
    def quote(self, shipment: Shipment) -> float:
        raise NotImplementedError

    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError


class StandardShipping(ShippingProvider):
    def quote(self, shipment: Shipment) -> float:
        return 50 + shipment.weight_kg * 20 + shipment.distance_km * 0.50

    def name(self) -> str:
        return "Standard"


class ExpressShipping(ShippingProvider):
    def quote(self, shipment: Shipment) -> float:
        return 150 + shipment.weight_kg * 35 + shipment.distance_km * 0.90

    def name(self) -> str:
        return "Express"


class InternationalShipping(ShippingProvider):
    def quote(self, shipment: Shipment) -> float:
        return 500 + shipment.weight_kg * 75 + shipment.distance_km * 2.50

    def name(self) -> str:
        return "International"


class ShippingCalculator:
    """
    Depends on the ShippingProvider abstraction.

    New providers can be introduced without changing the calculator.
    """

    def calculate(self, shipment: Shipment, provider: ShippingProvider) -> float:
        return provider.quote(shipment)


shipment = Shipment("SHP-1001", 4.5, 800)

calculator = ShippingCalculator()

for provider in [
    StandardShipping(),
    ExpressShipping(),
    InternationalShipping(),
]:
    print(
        f"{provider.name():15} "
        f"₹{calculator.calculate(shipment, provider):,.2f}"
    )


# ============================================================================
# 25. ERROR HANDLING IN OBJECT-ORIENTED SYSTEMS
# ============================================================================

print("\n" + "=" * 78)
print("25. CUSTOM EXCEPTIONS")
print("=" * 78)


class DomainError(Exception):
    """Base exception for expected business-rule failures."""


class InsufficientFundsError(DomainError):
    pass


class SecureAccount(BankAccount):
    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Withdrawal must be positive.")
        if amount > self.balance:
            raise InsufficientFundsError(
                f"Cannot withdraw {amount:.2f}; balance is {self.balance:.2f}."
            )

        super().withdraw(amount)


secure_account = SecureAccount("Customer", 500)

try:
    secure_account.withdraw(700)
except InsufficientFundsError as error:
    print("Domain exception:", error)


# ============================================================================
# 26. TESTABLE POLYMORPHIC FUNCTION
# ============================================================================

print("\n" + "=" * 78)
print("26. TESTABLE POLYMORPHIC FUNCTION")
print("=" * 78)


def calculate_shipping_cost(
    shipment: Shipment,
    provider: ShippingProvider,
) -> float:
    if not isinstance(provider, ShippingProvider):
        raise TypeError("provider must implement ShippingProvider.")
    return provider.quote(shipment)


assert math.isclose(
    calculate_shipping_cost(
        Shipment("TEST", 1, 100),
        StandardShipping(),
    ),
    120,
)

print("Assertion-based test passed.")


# ============================================================================
# 27. PERFORMANCE: METHOD CALLS AND OBJECT CREATION
# ============================================================================

print("\n" + "=" * 78)
print("27. PERFORMANCE CONSIDERATIONS")
print("=" * 78)

"""
OOP itself does not determine algorithmic complexity.

For example:
    list membership       -> O(n)
    set membership        -> average O(1)
    dictionary lookup     -> average O(1)

Method dispatch and object allocation also have runtime costs, but algorithm
choice generally has a much larger effect on performance.

A small benchmark can illustrate measurement rather than speculation.
"""

large_values = list(range(100_000))
large_set = set(large_values)

start = time.perf_counter()
_ = 99_999 in large_values
list_time = time.perf_counter() - start

start = time.perf_counter()
_ = 99_999 in large_set
set_time = time.perf_counter() - start

print(f"List membership time: {list_time:.8f}s")
print(f"Set membership time:  {set_time:.8f}s")


# ============================================================================
# 28. OBJECT IDENTITY VS VALUE EQUALITY
# ============================================================================

print("\n" + "=" * 78)
print("28. IDENTITY VS EQUALITY")
print("=" * 78)


class User:
    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.user_id == other.user_id


user_a = User(1, "Atul")
user_b = User(1, "Atul")

print("Same identity:", user_a is user_b)
print("Equal values:", user_a == user_b)


# ============================================================================
# 29. CLASS ATTRIBUTES AND INSTANCE ATTRIBUTES
# ============================================================================

print("\n" + "=" * 78)
print("29. CLASS ATTRIBUTES VS INSTANCE ATTRIBUTES")
print("=" * 78)


class Counter:
    created_objects = 0

    def __init__(self) -> None:
        Counter.created_objects += 1
        self.local_value = 0


counter_a = Counter()
counter_b = Counter()

print("Class-level count:", Counter.created_objects)
print("Instance values:", counter_a.local_value, counter_b.local_value)


# ============================================================================
# 30. FACTORY PATTERN
# ============================================================================

print("\n" + "=" * 78)
print("30. FACTORY-STYLE OBJECT CREATION")
print("=" * 78)


class Report(ABC):
    @abstractmethod
    def render(self) -> str:
        raise NotImplementedError


class HtmlReport(Report):
    def render(self) -> str:
        return "<h1>Sales Report</h1>"


class TextReport(Report):
    def render(self) -> str:
        return "SALES REPORT"


def create_report(format_name: str) -> Report:
    normalized = format_name.lower()

    if normalized == "html":
        return HtmlReport()
    if normalized == "text":
        return TextReport()

    raise ValueError(f"Unsupported report format: {format_name}")


for format_name in ["html", "text"]:
    report = create_report(format_name)
    print(report.render())


# ============================================================================
# 31. COMMON MISTAKES
# ============================================================================

print("\n" + "=" * 78)
print("31. COMMON OOP MISTAKES")
print("=" * 78)

mistakes = [
    "Using inheritance only to reuse a few lines of code.",
    "Exposing mutable internal state without validation.",
    "Creating deep inheritance trees that are difficult to understand.",
    "Making every attribute private without considering whether it needs to be.",
    "Writing subclasses that violate assumptions established by the base class.",
    "Using isinstance() everywhere instead of designing useful interfaces.",
    "Creating huge classes with unrelated responsibilities.",
    "Using global mutable state when dependency injection would be clearer.",
    "Ignoring object lifecycle, error handling, and invalid states.",
    "Optimizing object-oriented code before measuring actual bottlenecks.",
]

for number, mistake in enumerate(mistakes, start=1):
    print(f"{number:02}. {mistake}")


# ============================================================================
# 32. PRINCIPLE COMPARISON
# ============================================================================

print("\n" + "=" * 78)
print("32. THE FOUR CORE OOP PRINCIPLES")
print("=" * 78)

principles = {
    "Encapsulation": "Control access to state and keep behavior with the data it governs.",
    "Inheritance": "Create specialized types from generalized types when the relationship is valid.",
    "Polymorphism": "Use a common operation/interface across different concrete implementations.",
    "Abstraction": "Expose essential behavior while hiding unnecessary implementation details.",
}

for principle, definition in principles.items():
    print(f"{principle}: {definition}")


# ============================================================================
# 33. WHEN TO PREFER COMPOSITION OVER INHERITANCE
# ============================================================================

print("\n" + "=" * 78)
print("33. COMPOSITION VS INHERITANCE")
print("=" * 78)

comparison = [
    ("Inheritance", "is-a relationship", "often tighter coupling"),
    ("Composition", "has-a relationship", "often more flexible"),
    ("Inheritance", "reuse through a type hierarchy", "subclasses inherit contracts"),
    ("Composition", "reuse through contained objects", "dependencies can be replaced"),
]

for mechanism, relationship, characteristic in comparison:
    print(f"{mechanism:12} | {relationship:24} | {characteristic}")


# ============================================================================
# 34. FINAL EXECUTABLE SELF-CHECK
# ============================================================================

print("\n" + "=" * 78)
print("34. SELF-CHECK")
print("=" * 78)

assert isinstance(dog, Animal)
assert isinstance(cat, Animal)
assert dog.speak() != cat.speak()
assert account.balance == 11_250
assert temperature.celsius == 100
assert Money(100) + Money(50) == Money(150)
assert Coordinate(3, 4).distance_from_origin() == 5
assert final_price(1000, PercentageDiscount(25)) == 750
assert calculator.calculate(shipment, StandardShipping()) > 0

print("All core OOP demonstrations completed successfully.")
print("Study sequence: objects -> encapsulation -> inheritance -> polymorphism")
print("                -> abstraction -> composition -> advanced design.")
