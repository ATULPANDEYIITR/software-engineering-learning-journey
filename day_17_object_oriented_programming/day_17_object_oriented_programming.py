"""
Object-Oriented Programming in Python
=====================================

A self-contained tutorial and executable study file covering:
- Classes and objects
- Attributes and methods
- Instance, class, and static methods
- Constructors and object lifecycle
- Encapsulation
- Properties
- Inheritance
- Method overriding
- Polymorphism
- Abstract base classes
- Composition and aggregation
- Special methods
- Dataclasses
- Class relationships
- Type hints
- Validation
- Exceptions
- Iteration
- Operator overloading
- Dependency injection
- SOLID-oriented design considerations
- Testing
- Performance and memory considerations
- Common mistakes and edge cases

Run with Python 3.10+.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import total_ordering
from typing import Callable, Iterable, Iterator, Optional, Protocol
import math
import time


# =============================================================================
# 1. FUNDAMENTAL CONCEPTS
# =============================================================================

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


section("1. Classes and Objects")


class Student:
    """
    A class is a blueprint for creating objects.

    Each Student object can have:
    - data: attributes
    - behavior: methods
    """

    def __init__(self, name: str, age: int) -> None:
        self.name = name
        self.age = age

    def introduce(self) -> str:
        return f"My name is {self.name} and I am {self.age} years old."


student_one = Student("Asha", 20)
student_two = Student("Rahul", 22)

print(student_one.introduce())
print(student_two.introduce())

print("student_one is an object:", isinstance(student_one, Student))
print("Class of student_one:", type(student_one).__name__)


# =============================================================================
# 2. ATTRIBUTES
# =============================================================================

section("2. Instance Attributes and Class Attributes")


class Employee:
    """Demonstrates instance attributes and shared class attributes."""

    company_name = "Example Technologies"
    employee_count = 0

    def __init__(self, name: str, salary: float) -> None:
        self.name = name
        self.salary = salary
        Employee.employee_count += 1

    def describe(self) -> str:
        return f"{self.name}: salary={self.salary:.2f}, company={self.company_name}"


employee_one = Employee("Priya", 75000)
employee_two = Employee("Vikram", 90000)

print(employee_one.describe())
print(employee_two.describe())
print("Employees created:", Employee.employee_count)

# Instance attributes normally belong to one object.
employee_one.salary = 80000
print("Updated employee_one salary:", employee_one.salary)
print("employee_two salary remains:", employee_two.salary)

# Class attributes are shared unless shadowed by an instance attribute.
print("Class attribute:", Employee.company_name)


# =============================================================================
# 3. METHODS
# =============================================================================

section("3. Instance, Class, and Static Methods")


class Temperature:
    """Demonstrates three important method types."""

    scale_name = "Celsius"

    def __init__(self, celsius: float) -> None:
        self.celsius = celsius

    def to_fahrenheit(self) -> float:
        """Instance method: receives self and works with object state."""
        return self.celsius * 9 / 5 + 32

    @classmethod
    def from_fahrenheit(cls, fahrenheit: float) -> "Temperature":
        """
        Class method: receives cls and can construct an object through the
        class itself.
        """
        celsius = (fahrenheit - 32) * 5 / 9
        return cls(celsius)

    @staticmethod
    def is_valid_celsius(value: float) -> bool:
        """Static method: related to the class but does not need self or cls."""
        return math.isfinite(value)


temperature = Temperature(25)
print("25 C in F:", temperature.to_fahrenheit())

converted = Temperature.from_fahrenheit(98.6)
print("98.6 F in C:", round(converted.celsius, 2))

print("Valid temperature:", Temperature.is_valid_celsius(25))
print("Invalid temperature:", Temperature.is_valid_celsius(float("nan")))


# =============================================================================
# 4. ENCAPSULATION
# =============================================================================

section("4. Encapsulation")


class BankAccount:
    """
    Encapsulation groups state and behavior together and controls how state
    should be changed.

    Python does not enforce traditional private fields in the same way as some
    languages. A leading underscore communicates protected/internal intent,
    while name mangling is available with a double underscore.
    """

    def __init__(self, owner: str, opening_balance: float = 0.0) -> None:
        if opening_balance < 0:
            raise ValueError("Opening balance cannot be negative.")

        self.owner = owner
        self._balance = opening_balance
        self.__transaction_count = 0

    def deposit(self, amount: float) -> None:
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Deposit must be a positive finite number.")

        self._balance += amount
        self.__transaction_count += 1

    def withdraw(self, amount: float) -> None:
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Withdrawal must be a positive finite number.")

        if amount > self._balance:
            raise ValueError("Insufficient funds.")

        self._balance -= amount
        self.__transaction_count += 1

    def get_balance(self) -> float:
        return self._balance

    def get_transaction_count(self) -> int:
        return self.__transaction_count


account = BankAccount("Neha", 1000)
account.deposit(500)
account.withdraw(250)

print("Balance:", account.get_balance())
print("Transactions:", account.get_transaction_count())

try:
    account.withdraw(5000)
except ValueError as error:
    print("Expected error:", error)


# =============================================================================
# 5. PROPERTIES
# =============================================================================

section("5. Properties")


class Product:
    """Uses a property to validate and control attribute access."""

    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price

    @property
    def price(self) -> float:
        return self._price

    @price.setter
    def price(self, value: float) -> None:
        if not math.isfinite(value) or value < 0:
            raise ValueError("Price must be a non-negative finite number.")
        self._price = value

    @property
    def discounted_price(self) -> float:
        return self._price * 0.90


product = Product("Keyboard", 2000)
print("Price:", product.price)
print("Discounted price:", product.discounted_price)

product.price = 1800
print("Updated price:", product.price)

try:
    product.price = -100
except ValueError as error:
    print("Expected validation error:", error)


# =============================================================================
# 6. INHERITANCE
# =============================================================================

section("6. Inheritance and Method Overriding")


class Vehicle:
    """Base class."""

    def __init__(self, brand: str) -> None:
        self.brand = brand

    def move(self) -> str:
        return f"{self.brand} vehicle is moving."


class Car(Vehicle):
    """Derived class inheriting from Vehicle."""

    def move(self) -> str:
        return f"{self.brand} car is driving on the road."


class ElectricCar(Car):
    """Multi-level inheritance example."""

    def __init__(self, brand: str, battery_kwh: float) -> None:
        super().__init__(brand)

        if battery_kwh <= 0:
            raise ValueError("Battery capacity must be positive.")

        self.battery_kwh = battery_kwh

    def move(self) -> str:
        return f"{self.brand} electric car is driving silently."


vehicles = [
    Vehicle("Generic"),
    Car("Toyota"),
    ElectricCar("Tesla", 75),
]

for vehicle in vehicles:
    print(vehicle.move())


# =============================================================================
# 7. POLYMORPHISM
# =============================================================================

section("7. Polymorphism")


class Dog:
    def speak(self) -> str:
        return "Woof"


class Cat:
    def speak(self) -> str:
        return "Meow"


class Cow:
    def speak(self) -> str:
        return "Moo"


def make_animal_speak(animal: object) -> str:
    """
    Duck typing: the function does not require a specific inheritance tree.
    It only needs the object to provide a compatible speak() method.
    """
    return animal.speak()  # type: ignore[attr-defined]


for animal in [Dog(), Cat(), Cow()]:
    print(make_animal_speak(animal))


# =============================================================================
# 8. ABSTRACT CLASSES
# =============================================================================

section("8. Abstract Base Classes")


class Shape(ABC):
    """Defines a contract that concrete shape classes must implement."""

    @abstractmethod
    def area(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def perimeter(self) -> float:
        raise NotImplementedError


class Rectangle(Shape):
    def __init__(self, width: float, height: float) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Dimensions must be positive.")

        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)


class Circle(Shape):
    def __init__(self, radius: float) -> None:
        if radius <= 0:
            raise ValueError("Radius must be positive.")

        self.radius = radius

    def area(self) -> float:
        return math.pi * self.radius**2

    def perimeter(self) -> float:
        return 2 * math.pi * self.radius


shapes: list[Shape] = [
    Rectangle(10, 5),
    Circle(3),
]

for shape in shapes:
    print(
        type(shape).__name__,
        "area=",
        round(shape.area(), 2),
        "perimeter=",
        round(shape.perimeter(), 2),
    )


# =============================================================================
# 9. COMPOSITION
# =============================================================================

section("9. Composition")


class Engine:
    def start(self) -> str:
        return "Engine started."


class CarWithEngine:
    """
    Composition means an object contains another object to implement part
    of its behavior.
    """

    def __init__(self, brand: str, engine: Engine) -> None:
        self.brand = brand
        self.engine = engine

    def start(self) -> str:
        return f"{self.brand}: {self.engine.start()}"


engine = Engine()
car = CarWithEngine("Honda", engine)

print(car.start())


# =============================================================================
# 10. AGGREGATION
# =============================================================================

section("10. Aggregation")


class Teacher:
    def __init__(self, name: str) -> None:
        self.name = name


class Classroom:
    """
    A classroom can refer to teachers that also exist independently.
    This is an example of aggregation.
    """

    def __init__(self, name: str, teachers: Iterable[Teacher]) -> None:
        self.name = name
        self.teachers = list(teachers)

    def teacher_names(self) -> list[str]:
        return [teacher.name for teacher in self.teachers]


teacher_a = Teacher("Meera")
teacher_b = Teacher("Arjun")

classroom = Classroom("Python Lab", [teacher_a, teacher_b])

print(classroom.teacher_names())


# =============================================================================
# 11. SPECIAL METHODS
# =============================================================================

section("11. Special Methods")


class Vector:
    """Demonstrates operator overloading and object representation."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Vector(x={self.x}, y={self.y})"

    def __add__(self, other: "Vector") -> "Vector":
        if not isinstance(other, Vector):
            return NotImplemented

        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector") -> "Vector":
        if not isinstance(other, Vector):
            return NotImplemented

        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector":
        if not isinstance(scalar, (int, float)):
            return NotImplemented

        return Vector(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)


vector_a = Vector(3, 4)
vector_b = Vector(1, 2)

print("A:", vector_a)
print("B:", vector_b)
print("A + B:", vector_a + vector_b)
print("A - B:", vector_a - vector_b)
print("A * 2:", vector_a * 2)
print("Magnitude:", vector_a.magnitude())


# =============================================================================
# 12. EQUALITY AND ORDERING
# =============================================================================

section("12. Equality and Ordering")


@total_ordering
class Score:
    """Demonstrates custom equality and ordering."""

    def __init__(self, value: float) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Score):
            return NotImplemented

        return math.isclose(self.value, other.value)

    def __lt__(self, other: "Score") -> bool:
        if not isinstance(other, Score):
            return NotImplemented

        return self.value < other.value

    def __repr__(self) -> str:
        return f"Score({self.value})"


score_a = Score(80)
score_b = Score(90)

print("Equal:", score_a == score_b)
print("Less than:", score_a < score_b)
print("Greater than:", score_b > score_a)


# =============================================================================
# 13. DATACLASSES
# =============================================================================

section("13. Dataclasses")


@dataclass
class Address:
    city: str
    country: str


@dataclass
class Customer:
    name: str
    email: str
    address: Address
    tags: list[str] = field(default_factory=list)


customer = Customer(
    name="Riya",
    email="riya@example.com",
    address=Address("Lucknow", "India"),
    tags=["premium", "verified"],
)

print(customer)


# =============================================================================
# 14. ITERABLE OBJECTS
# =============================================================================

section("14. Custom Iterable Class")


class NumberRange:
    """A simple iterable object with lazy iteration."""

    def __init__(self, start: int, stop: int) -> None:
        self.start = start
        self.stop = stop

    def __iter__(self) -> Iterator[int]:
        current = self.start

        while current < self.stop:
            yield current
            current += 1


numbers = NumberRange(2, 7)

print("Custom iterable:", list(numbers))


# =============================================================================
# 15. PROTOCOLS
# =============================================================================

section("15. Structural Typing with Protocol")


class Printable(Protocol):
    def describe(self) -> str:
        ...


class Report:
    def __init__(self, title: str) -> None:
        self.title = title

    def describe(self) -> str:
        return f"Report: {self.title}"


class Invoice:
    def __init__(self, invoice_number: str) -> None:
        self.invoice_number = invoice_number

    def describe(self) -> str:
        return f"Invoice: {self.invoice_number}"


def print_description(item: Printable) -> None:
    print(item.describe())


print_description(Report("Annual Analysis"))
print_description(Invoice("INV-1001"))


# =============================================================================
# 16. DEPENDENCY INJECTION
# =============================================================================

section("16. Dependency Injection")


class ConsoleNotifier:
    def send(self, message: str) -> None:
        print("NOTIFICATION:", message)


class OrderService:
    """
    The service receives its notification dependency instead of constructing
    it internally. This makes the class easier to test and replace.
    """

    def __init__(self, notifier: ConsoleNotifier) -> None:
        self.notifier = notifier

    def place_order(self, order_id: str, amount: float) -> None:
        if not order_id:
            raise ValueError("Order ID is required.")

        if amount <= 0:
            raise ValueError("Order amount must be positive.")

        self.notifier.send(
            f"Order {order_id} placed for {amount:.2f}."
        )


service = OrderService(ConsoleNotifier())
service.place_order("ORD-100", 1499.99)


# =============================================================================
# 17. REALISTIC OOP CASE STUDY
# =============================================================================

section("17. Industry-Style Case Study: Library Management System")


@dataclass(frozen=True)
class Book:
    isbn: str
    title: str
    author: str

    def __post_init__(self) -> None:
        if not self.isbn.strip():
            raise ValueError("ISBN cannot be empty.")

        if not self.title.strip():
            raise ValueError("Title cannot be empty.")

        if not self.author.strip():
            raise ValueError("Author cannot be empty.")


@dataclass
class LibraryMember:
    member_id: str
    name: str
    borrowed_isbns: set[str] = field(default_factory=set)

    def borrow(self, isbn: str) -> None:
        self.borrowed_isbns.add(isbn)

    def return_book(self, isbn: str) -> None:
        self.borrowed_isbns.discard(isbn)


class Library:
    """
    Coordinates books and members.

    Dictionaries provide average O(1) lookup by ISBN and member ID.
    Sets provide average O(1) membership checks for borrowed books.
    """

    MAX_BOOKS_PER_MEMBER = 3

    def __init__(self) -> None:
        self._books: dict[str, Book] = {}
        self._members: dict[str, LibraryMember] = {}

    def add_book(self, book: Book) -> None:
        if book.isbn in self._books:
            raise ValueError(f"Book already exists: {book.isbn}")

        self._books[book.isbn] = book

    def register_member(self, member: LibraryMember) -> None:
        if member.member_id in self._members:
            raise ValueError(
                f"Member already exists: {member.member_id}"
            )

        self._members[member.member_id] = member

    def borrow_book(self, member_id: str, isbn: str) -> str:
        member = self._get_member(member_id)
        self._get_book(isbn)

        if isbn in member.borrowed_isbns:
            raise ValueError("Member already borrowed this book.")

        if len(member.borrowed_isbns) >= self.MAX_BOOKS_PER_MEMBER:
            raise ValueError("Borrowing limit reached.")

        for other_member in self._members.values():
            if isbn in other_member.borrowed_isbns:
                raise ValueError("Book is currently unavailable.")

        member.borrow(isbn)
        return f"{member.name} borrowed {isbn}."

    def return_book(self, member_id: str, isbn: str) -> str:
        member = self._get_member(member_id)

        if isbn not in member.borrowed_isbns:
            raise ValueError("Member has not borrowed this book.")

        member.return_book(isbn)
        return f"{member.name} returned {isbn}."

    def search_by_author(self, author: str) -> list[Book]:
        normalized = author.casefold()

        return [
            book
            for book in self._books.values()
            if normalized in book.author.casefold()
        ]

    def available_books(self) -> list[Book]:
        borrowed = {
            isbn
            for member in self._members.values()
            for isbn in member.borrowed_isbns
        }

        return [
            book
            for isbn, book in self._books.items()
            if isbn not in borrowed
        ]

    def _get_book(self, isbn: str) -> Book:
        try:
            return self._books[isbn]
        except KeyError as error:
            raise ValueError(f"Unknown ISBN: {isbn}") from error

    def _get_member(self, member_id: str) -> LibraryMember:
        try:
            return self._members[member_id]
        except KeyError as error:
            raise ValueError(
                f"Unknown member ID: {member_id}"
            ) from error


library = Library()

library.add_book(
    Book("978-1", "Clean Code", "Robert C. Martin")
)
library.add_book(
    Book("978-2", "The Pragmatic Programmer", "Andrew Hunt")
)
library.add_book(
    Book("978-3", "Python Crash Course", "Eric Matthes")
)

library.register_member(
    LibraryMember("M001", "Ananya")
)
library.register_member(
    LibraryMember("M002", "Kabir")
)

print(library.borrow_book("M001", "978-1"))
print(library.borrow_book("M002", "978-2"))

try:
    library.borrow_book("M002", "978-1")
except ValueError as error:
    print("Expected library error:", error)

print("Author search:", library.search_by_author("matthes"))
print("Available books:", library.available_books())

print(library.return_book("M001", "978-1"))


# =============================================================================
# 18. MULTIPLE INHERITANCE
# =============================================================================

section("18. Multiple Inheritance and MRO")


class LoggerMixin:
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class TimestampMixin:
    def current_time(self) -> float:
        return time.time()


class Application(LoggerMixin, TimestampMixin):
    def run(self) -> None:
        self.log(f"Application started at {self.current_time()}")


application = Application()
application.run()

print(
    "Method Resolution Order:",
    [cls.__name__ for cls in Application.__mro__],
)


# =============================================================================
# 19. SUPER()
# =============================================================================

section("19. super()")


class Person:
    def __init__(self, name: str) -> None:
        self.name = name


class Developer(Person):
    def __init__(self, name: str, language: str) -> None:
        super().__init__(name)
        self.language = language

    def describe(self) -> str:
        return f"{self.name} develops software using {self.language}."


developer = Developer("Amit", "Python")
print(developer.describe())


# =============================================================================
# 20. IMMUTABILITY AND FROZEN DATACLASSES
# =============================================================================

section("20. Immutable Objects")


@dataclass(frozen=True)
class Coordinate:
    latitude: float
    longitude: float


coordinate = Coordinate(26.8467, 80.9462)
print("Coordinate:", coordinate)

try:
    coordinate.latitude = 27.0
except Exception as error:
    print("Expected immutability error:", type(error).__name__)


# =============================================================================
# 21. CLASS FACTORY
# =============================================================================

section("21. Factory Pattern")


class Notification(ABC):
    @abstractmethod
    def send(self, message: str) -> str:
        raise NotImplementedError


class EmailNotification(Notification):
    def send(self, message: str) -> str:
        return f"Email sent: {message}"


class SMSNotification(Notification):
    def send(self, message: str) -> str:
        return f"SMS sent: {message}"


class NotificationFactory:
    @staticmethod
    def create(channel: str) -> Notification:
        normalized = channel.casefold()

        if normalized == "email":
            return EmailNotification()

        if normalized == "sms":
            return SMSNotification()

        raise ValueError(f"Unsupported notification channel: {channel}")


for channel in ["email", "sms"]:
    notification = NotificationFactory.create(channel)
    print(notification.send("Your account was updated."))


# =============================================================================
# 22. STRATEGY PATTERN
# =============================================================================

section("22. Strategy Pattern")


class PricingStrategy(Protocol):
    def calculate(self, base_price: float) -> float:
        ...


class RegularPricing:
    def calculate(self, base_price: float) -> float:
        return base_price


class PremiumPricing:
    def calculate(self, base_price: float) -> float:
        return base_price * 0.90


class SeasonalPricing:
    def calculate(self, base_price: float) -> float:
        return base_price * 0.80


class Checkout:
    def __init__(self, pricing_strategy: PricingStrategy) -> None:
        self.pricing_strategy = pricing_strategy

    def final_price(self, base_price: float) -> float:
        if base_price < 0:
            raise ValueError("Price cannot be negative.")

        return self.pricing_strategy.calculate(base_price)


for strategy in [
    RegularPricing(),
    PremiumPricing(),
    SeasonalPricing(),
]:
    checkout = Checkout(strategy)
    print("Final price:", checkout.final_price(1000))


# =============================================================================
# 23. OOP TESTING
# =============================================================================

section("23. Lightweight Object-Oriented Testing")


def assert_equal(actual: object, expected: object, message: str = "") -> None:
    if actual != expected:
        raise AssertionError(
            f"{message} expected={expected!r}, actual={actual!r}"
        )


def assert_raises(
    exception_type: type[BaseException],
    function: Callable[[], object],
) -> None:
    try:
        function()
    except exception_type:
        return

    raise AssertionError(
        f"Expected {exception_type.__name__} to be raised."
    )


test_account = BankAccount("Tester", 100)
test_account.deposit(50)
assert_equal(test_account.get_balance(), 150)

assert_raises(
    ValueError,
    lambda: test_account.withdraw(1000),
)

test_product = Product("Test", 100)
assert_equal(test_product.discounted_price, 90)

print("Basic tests passed.")


# =============================================================================
# 24. COMMON EDGE CASES
# =============================================================================

section("24. Edge Cases")


def safe_divide(dividend: float, divisor: float) -> Optional[float]:
    """
    Explicitly handles division by zero and non-finite inputs.
    Returning None communicates that no valid numeric result exists.
    """
    if not math.isfinite(dividend) or not math.isfinite(divisor):
        return None

    if divisor == 0:
        return None

    return dividend / divisor


for dividend, divisor in [
    (10, 2),
    (10, 0),
    (float("nan"), 2),
    (10, float("inf")),
]:
    print(
        f"safe_divide({dividend}, {divisor}) =",
        safe_divide(dividend, divisor),
    )


# =============================================================================
# 25. OOP DESIGN COMPARISON
# =============================================================================

section("25. Inheritance vs Composition")


class PaymentGateway:
    def charge(self, amount: float) -> str:
        return f"Charged {amount:.2f}"


class Order:
    """
    Composition is often useful when behavior can vary independently from
    the main object's identity.
    """

    def __init__(self, order_id: str, gateway: PaymentGateway) -> None:
        self.order_id = order_id
        self.gateway = gateway

    def pay(self, amount: float) -> str:
        if amount <= 0:
            raise ValueError("Payment must be positive.")

        return self.gateway.charge(amount)


order = Order("ORD-500", PaymentGateway())
print(order.pay(2500))


# =============================================================================
# 26. PERFORMANCE CONSIDERATIONS
# =============================================================================

section("26. Performance Considerations")


class CounterObject:
    def __init__(self, value: int) -> None:
        self.value = value

    def increment(self) -> None:
        self.value += 1


counter = CounterObject(0)

start = time.perf_counter()

for _ in range(100_000):
    counter.increment()

elapsed = time.perf_counter() - start

print("Counter value:", counter.value)
print("100,000 method calls took approximately:", f"{elapsed:.6f}", "seconds")

"""
Performance principles:

1. Object creation has memory and CPU cost.
2. Attribute lookup and method dispatch have overhead.
3. OOP does not automatically make an algorithm efficient.
4. Data structures and algorithmic complexity usually matter more than
   small syntax-level optimizations.
5. __slots__ can reduce per-instance memory for suitable classes, but it
   removes or restricts some normal instance behavior.
"""


# =============================================================================
# 27. __SLOTS__
# =============================================================================

section("27. __slots__")


class CompactPoint:
    """
    __slots__ can avoid a normal per-instance __dict__.

    It is useful for large numbers of simple objects, but it reduces
    flexibility and should be chosen deliberately.
    """

    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


compact_point = CompactPoint(10, 20)
print("Compact point:", compact_point.x, compact_point.y)

try:
    compact_point.extra = 5  # type: ignore[attr-defined]
except AttributeError as error:
    print("Expected __slots__ behavior:", error)


# =============================================================================
# 28. OOP SECURITY CONSIDERATIONS
# =============================================================================

section("28. Security-Oriented OOP Design")


class User:
    """
    Authentication and authorization data should be validated and handled
    carefully.

    This example intentionally stores only a password hash placeholder.
    It does not demonstrate real password hashing.
    """

    def __init__(self, username: str, password_hash: str) -> None:
        if not username or not username.strip():
            raise ValueError("Username cannot be empty.")

        if not password_hash:
            raise ValueError("Password hash is required.")

        self.username = username
        self._password_hash = password_hash

    def verify_hash(self, candidate_hash: str) -> bool:
        return self._password_hash == candidate_hash


user = User("alice", "HASHED_VALUE")

print("Authentication result:", user.verify_hash("HASHED_VALUE"))

"""
Production security considerations include:

- Never store plaintext passwords.
- Use established password hashing algorithms rather than inventing one.
- Validate authorization at trust boundaries.
- Do not expose internal secrets through __repr__.
- Avoid unsafe deserialization of untrusted objects.
- Do not assume encapsulation is a security boundary.
- Validate external input before converting it into domain objects.
"""


# =============================================================================
# 29. COMMON OOP MISTAKES
# =============================================================================

section("29. Common Mistakes")


class CorrectCollection:
    """
    Use default_factory for mutable dataclass fields so each object receives
    its own collection.
    """

    def __init__(self) -> None:
        self.items: list[str] = []


collection_a = CorrectCollection()
collection_b = CorrectCollection()

collection_a.items.append("A")

print("collection_a:", collection_a.items)
print("collection_b:", collection_b.items)


# Mutable default argument mistake:
def add_item_bad(item: str, items: list[str] = []) -> list[str]:
    items.append(item)
    return items


# Correct approach:
def add_item_good(item: str, items: Optional[list[str]] = None) -> list[str]:
    if items is None:
        items = []

    items.append(item)
    return items


print("Bad function first call:", add_item_bad("A"))
print("Bad function second call:", add_item_bad("B"))

print("Good function first call:", add_item_good("A"))
print("Good function second call:", add_item_good("B"))


# =============================================================================
# 30. OBJECT IDENTITY VS EQUALITY
# =============================================================================

section("30. Identity vs Equality")


class SimpleValue:
    def __init__(self, value: int) -> None:
        self.value = value

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SimpleValue):
            return NotImplemented

        return self.value == other.value


value_a = SimpleValue(10)
value_b = SimpleValue(10)
value_c = value_a

print("value_a == value_b:", value_a == value_b)
print("value_a is value_b:", value_a is value_b)
print("value_a is value_c:", value_a is value_c)


# =============================================================================
# 31. FINAL INTEGRATED EXAMPLE
# =============================================================================

section("31. Integrated OOP Example: E-Commerce Domain")


@dataclass(frozen=True)
class LineItem:
    product_name: str
    unit_price: float
    quantity: int

    def __post_init__(self) -> None:
        if not self.product_name.strip():
            raise ValueError("Product name is required.")

        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")

    @property
    def subtotal(self) -> float:
        return self.unit_price * self.quantity


class DiscountPolicy(Protocol):
    def discount(self, subtotal: float) -> float:
        ...


class NoDiscount:
    def discount(self, subtotal: float) -> float:
        return 0.0


class PercentageDiscount:
    def __init__(self, percentage: float) -> None:
        if not 0 <= percentage <= 100:
            raise ValueError("Percentage must be between 0 and 100.")

        self.percentage = percentage

    def discount(self, subtotal: float) -> float:
        return subtotal * self.percentage / 100


class ShoppingCart:
    def __init__(self, discount_policy: DiscountPolicy) -> None:
        self._items: list[LineItem] = []
        self.discount_policy = discount_policy

    def add_item(self, item: LineItem) -> None:
        self._items.append(item)

    @property
    def subtotal(self) -> float:
        return sum(item.subtotal for item in self._items)

    @property
    def discount_amount(self) -> float:
        return self.discount_policy.discount(self.subtotal)

    @property
    def total(self) -> float:
        return self.subtotal - self.discount_amount

    def receipt(self) -> str:
        lines = ["Receipt", "-" * 30]

        for item in self._items:
            lines.append(
                f"{item.product_name}: "
                f"{item.quantity} x {item.unit_price:.2f} = "
                f"{item.subtotal:.2f}"
            )

        lines.extend(
            [
                "-" * 30,
                f"Subtotal: {self.subtotal:.2f}",
                f"Discount: {self.discount_amount:.2f}",
                f"Total: {self.total:.2f}",
            ]
        )

        return "\n".join(lines)


cart = ShoppingCart(PercentageDiscount(10))

cart.add_item(LineItem("Laptop", 75000, 1))
cart.add_item(LineItem("Mouse", 1500, 2))
cart.add_item(LineItem("Keyboard", 2500, 1))

print(cart.receipt())


# =============================================================================
# 32. CONCEPTUAL CHECKS
# =============================================================================

section("32. Conceptual Checks")

questions_and_answers = {
    "What is a class?":
        "A blueprint or definition describing data and behavior.",
    "What is an object?":
        "A runtime instance created from a class.",
    "What is an attribute?":
        "Data associated with an object or class.",
    "What is a method?":
        "A function defined within a class.",
    "What is inheritance?":
        "A mechanism through which one class derives behavior and structure from another.",
    "What is polymorphism?":
        "The ability to use a common interface while allowing different implementations.",
    "What is encapsulation?":
        "Combining state and behavior while controlling how internal state is accessed or modified.",
    "What is composition?":
        "Building an object from other objects rather than relying on inheritance.",
    "What is abstraction?":
        "Representing essential behavior while hiding unnecessary implementation details.",
}

for question, answer in questions_and_answers.items():
    print(f"{question}\n  {answer}")


# =============================================================================
# 33. COMPLETION CHECK
# =============================================================================

section("34. Execution Check")

print("All major OOP demonstrations completed successfully.")
print("Python version:", __import__("sys").version.split()[0])
