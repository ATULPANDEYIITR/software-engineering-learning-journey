"""
Composition vs Inheritance: Coupling, Reuse, and Maintainability
================================================================

A standalone study program that progresses from object-oriented fundamentals
to advanced design trade-offs involving inheritance, composition, coupling,
reuse, substitutability, dependency injection, delegation, and maintainability.

The program is executable with Python 3.10+ and uses only the standard library.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, Iterable, Callable, Optional
from collections import defaultdict
import math
import time


# ============================================================================
# 1. BASIC DOMAIN MODEL
# ============================================================================

@dataclass
class Customer:
    name: str
    email: str


@dataclass
class OrderItem:
    product: str
    quantity: int
    unit_price: float

    @property
    def total(self) -> float:
        return self.quantity * self.unit_price


class Order:
    """
    A simple object containing other objects.

    This is composition at the object level: an Order HAS OrderItems.
    The Order does not inherit from OrderItem.
    """

    def __init__(self, customer: Customer) -> None:
        self.customer = customer
        self.items: list[OrderItem] = []

    def add_item(self, item: OrderItem) -> None:
        if item.quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if item.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        self.items.append(item)

    def total(self) -> float:
        return sum(item.total for item in self.items)


# ============================================================================
# 2. INHERITANCE
# ============================================================================

class Employee:
    """Base class used to demonstrate inheritance."""

    def __init__(self, name: str, employee_id: str) -> None:
        self.name = name
        self.employee_id = employee_id

    def describe(self) -> str:
        return f"{self.name} ({self.employee_id})"


class Developer(Employee):
    """Developer IS an Employee."""

    def write_code(self) -> str:
        return f"{self.name} is writing software."


class Manager(Employee):
    """Manager IS an Employee."""

    def manage(self) -> str:
        return f"{self.name} is managing a team."


# ============================================================================
# 3. THE IS-A AND HAS-A DISTINCTION
# ============================================================================

class Vehicle:
    def move(self) -> str:
        return "Vehicle is moving."


class Car(Vehicle):
    """
    Car IS-A Vehicle.

    Inheritance is appropriate because the subtype satisfies the conceptual
    relationship with its parent and can normally be substituted for it.
    """

    def move(self) -> str:
        return "Car is driving."


@dataclass
class Engine:
    horsepower: int

    def start(self) -> str:
        return f"Engine with {self.horsepower} HP started."


class ComposedCar:
    """
    ComposedCar HAS-AN Engine.

    The car delegates engine-specific behavior to the contained object.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def start(self) -> str:
        return self.engine.start()

    def move(self) -> str:
        return "Composed car is driving."


# ============================================================================
# 4. INHERITANCE-BASED REUSE
# ============================================================================

class Report:
    def header(self) -> str:
        return "REPORT"

    def body(self) -> str:
        return "Default report body."

    def footer(self) -> str:
        return "END"

    def render(self) -> str:
        return "\n".join([self.header(), self.body(), self.footer()])


class SalesReport(Report):
    def body(self) -> str:
        return "Sales report data."


class FinancialReport(Report):
    def body(self) -> str:
        return "Financial report data."


# ============================================================================
# 5. COMPOSITION-BASED REUSE
# ============================================================================

class Formatter(Protocol):
    def format(self, title: str, body: str) -> str:
        ...


class PlainTextFormatter:
    def format(self, title: str, body: str) -> str:
        return f"{title}\n{body}"


class MarkdownFormatter:
    def format(self, title: str, body: str) -> str:
        return f"# {title}\n\n{body}"


class HtmlFormatter:
    def format(self, title: str, body: str) -> str:
        return f"<h1>{title}</h1><p>{body}</p>"


class ComposedReport:
    """
    The report is independent of a concrete formatting implementation.

    A formatter can be replaced without modifying ComposedReport.
    This reduces coupling.
    """

    def __init__(self, formatter: Formatter) -> None:
        self.formatter = formatter

    def render(self, title: str, body: str) -> str:
        return self.formatter.format(title, body)


# ============================================================================
# 6. COUPLING
# ============================================================================

class TightlyCoupledInvoice:
    """
    The class directly constructs a concrete payment mechanism.

    This creates stronger coupling:
        Invoice -> StripePaymentGateway

    Replacing the payment provider requires modifying this class.
    """

    def __init__(self, amount: float) -> None:
        self.amount = amount

    def pay(self) -> str:
        gateway = StripeLikeGateway()
        return gateway.charge(self.amount)


class StripeLikeGateway:
    def charge(self, amount: float) -> str:
        return f"Stripe-like gateway charged ${amount:.2f}"


class PaymentGateway(Protocol):
    def charge(self, amount: float) -> str:
        ...


class MockPaymentGateway:
    def charge(self, amount: float) -> str:
        return f"Mock gateway charged ${amount:.2f}"


class Invoice:
    """
    Dependency injection changes the dependency from a concrete class
    to an abstraction/protocol.

    Invoice -> PaymentGateway
    """

    def __init__(self, amount: float, gateway: PaymentGateway) -> None:
        if amount < 0:
            raise ValueError("Invoice amount cannot be negative.")
        self.amount = amount
        self.gateway = gateway

    def pay(self) -> str:
        return self.gateway.charge(self.amount)


# ============================================================================
# 7. INHERITANCE CAN INCREASE COUPLING
# ============================================================================

class BaseConfiguration:
    """
    Changes to a base class can affect every subclass.

    This illustrates why inheritance is sometimes described as a strong
    coupling relationship.
    """

    timeout = 30

    def connect(self) -> str:
        return f"Connecting with timeout={self.timeout}"


class ProductionConfiguration(BaseConfiguration):
    pass


class TestConfiguration(BaseConfiguration):
    timeout = 1


# ============================================================================
# 8. LISKOV SUBSTITUTION PRINCIPLE
# ============================================================================

class Bird:
    def move(self) -> str:
        return "Bird moves."


class FlyingBird(Bird):
    def fly(self) -> str:
        return "Flying."


class Penguin(FlyingBird):
    """
    This demonstrates a poor inheritance hierarchy.

    A Penguin technically inherits from FlyingBird, but cannot fulfill the
    behavioral expectation represented by fly().
    """

    def fly(self) -> str:
        raise RuntimeError("Penguins cannot fly.")


def demonstrate_substitutability() -> None:
    birds: list[FlyingBird] = [FlyingBird()]
    for bird in birds:
        print(bird.fly())

    # The Penguin class is intentionally not placed in this collection.
    # This is evidence that the hierarchy itself communicates the wrong
    # abstraction.


# ============================================================================
# 9. COMPOSITION SOLUTION TO THE BIRD EXAMPLE
# ============================================================================

class FlightBehavior(Protocol):
    def fly(self) -> str:
        ...


class CanFly:
    def fly(self) -> str:
        return "Flying through the air."


class CannotFly:
    def fly(self) -> str:
        return "This animal cannot fly."


class BirdWithFlightBehavior:
    """
    Flight capability is composed rather than forced through inheritance.
    """

    def __init__(self, name: str, flight_behavior: FlightBehavior) -> None:
        self.name = name
        self.flight_behavior = flight_behavior

    def move(self) -> str:
        return f"{self.name} moves."

    def fly(self) -> str:
        return self.flight_behavior.fly()


# ============================================================================
# 10. STRATEGY PATTERN THROUGH COMPOSITION
# ============================================================================

class PricingStrategy(Protocol):
    def calculate(self, subtotal: float) -> float:
        ...


class RegularPricing:
    def calculate(self, subtotal: float) -> float:
        return subtotal


class TenPercentDiscount:
    def calculate(self, subtotal: float) -> float:
        return subtotal * 0.90


class TwentyPercentDiscount:
    def calculate(self, subtotal: float) -> float:
        return subtotal * 0.80


class ShoppingCart:
    """
    Pricing behavior can be changed at runtime.

    Inheritance would require a family of ShoppingCart subclasses.
    Composition lets the same cart use different strategies.
    """

    def __init__(self, pricing_strategy: PricingStrategy) -> None:
        self.pricing_strategy = pricing_strategy
        self.items: list[OrderItem] = []

    def add(self, item: OrderItem) -> None:
        self.items.append(item)

    def subtotal(self) -> float:
        return sum(item.total for item in self.items)

    def total(self) -> float:
        return self.pricing_strategy.calculate(self.subtotal())

    def change_pricing_strategy(self, strategy: PricingStrategy) -> None:
        self.pricing_strategy = strategy


# ============================================================================
# 11. MULTIPLE VARIATIONS WITHOUT SUBCLASS EXPLOSION
# ============================================================================

class NotificationChannel(Protocol):
    def send(self, recipient: str, message: str) -> str:
        ...


class EmailChannel:
    def send(self, recipient: str, message: str) -> str:
        return f"EMAIL -> {recipient}: {message}"


class SmsChannel:
    def send(self, recipient: str, message: str) -> str:
        return f"SMS -> {recipient}: {message}"


class PushChannel:
    def send(self, recipient: str, message: str) -> str:
        return f"PUSH -> {recipient}: {message}"


class NotificationService:
    def __init__(self, channel: NotificationChannel) -> None:
        self.channel = channel

    def notify(self, recipient: str, message: str) -> str:
        if not recipient.strip():
            raise ValueError("Recipient cannot be empty.")
        return self.channel.send(recipient, message)


# ============================================================================
# 12. COMPOSITION OF MULTIPLE COMPONENTS
# ============================================================================

class Logger(Protocol):
    def log(self, message: str) -> None:
        ...


class ConsoleLogger:
    def log(self, message: str) -> None:
        print(f"[LOG] {message}")


class Inventory:
    def __init__(self) -> None:
        self._stock: dict[str, int] = defaultdict(int)

    def add(self, product: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        self._stock[product] += quantity

    def remove(self, product: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if self._stock[product] < quantity:
            raise ValueError(f"Insufficient stock for {product}.")
        self._stock[product] -= quantity

    def available(self, product: str) -> int:
        return self._stock[product]


class OrderProcessor:
    """
    A service composed from several independent collaborators.

    This is an example of dependency injection and low coupling.
    """

    def __init__(
        self,
        inventory: Inventory,
        payment_gateway: PaymentGateway,
        logger: Logger,
    ) -> None:
        self.inventory = inventory
        self.payment_gateway = payment_gateway
        self.logger = logger

    def process(self, product: str, quantity: int, price: float) -> str:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if price < 0:
            raise ValueError("Price cannot be negative.")

        self.inventory.remove(product, quantity)
        result = self.payment_gateway.charge(price * quantity)
        self.logger.log(result)
        return result


# ============================================================================
# 13. INTERFACE SEGREGATION THROUGH SMALL PROTOCOLS
# ============================================================================

class Reader(Protocol):
    def read(self) -> str:
        ...


class Writer(Protocol):
    def write(self, value: str) -> None:
        ...


class MemoryBuffer:
    def __init__(self) -> None:
        self.value = ""

    def read(self) -> str:
        return self.value

    def write(self, value: str) -> None:
        self.value = value


def copy_text(reader: Reader, writer: Writer) -> None:
    writer.write(reader.read())


# ============================================================================
# 14. FUNCTIONAL COMPOSITION
# ============================================================================

def trim(value: str) -> str:
    return value.strip()


def normalize_case(value: str) -> str:
    return value.lower()


def remove_spaces(value: str) -> str:
    return value.replace(" ", "_")


def compose(*functions: Callable[[str], str]) -> Callable[[str], str]:
    """
    Function composition creates reusable behavior without inheritance.
    """
    def composed(value: str) -> str:
        result = value
        for function in functions:
            result = function(result)
        return result

    return composed


# ============================================================================
# 15. TESTABLE COMPONENTS
# ============================================================================

class FakeInventory:
    def __init__(self, available_quantity: int) -> None:
        self.quantity = available_quantity

    def remove(self, product: str, quantity: int) -> None:
        if quantity > self.quantity:
            raise ValueError("Not enough stock.")
        self.quantity -= quantity


class RecordingGateway:
    def __init__(self) -> None:
        self.charges: list[float] = []

    def charge(self, amount: float) -> str:
        self.charges.append(amount)
        return f"Recorded ${amount:.2f}"


class SilentLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def log(self, message: str) -> None:
        self.messages.append(message)


# ============================================================================
# 16. MAINTAINABILITY METRICS
# ============================================================================

def afferent_coupling(dependents: dict[str, set[str]], component: str) -> int:
    """
    Afferent coupling approximates how many components depend on a component.
    """
    return sum(component in dependencies for dependencies in dependents.values())


def cyclomatic_like_branch_count(function_source: str) -> int:
    """
    A simple educational approximation, not a complete static-analysis tool.
    """
    keywords = ("if ", "for ", "while ", "except ", " and ", " or ")
    return 1 + sum(function_source.count(keyword) for keyword in keywords)


# ============================================================================
# 17. IMMUTABILITY AND VALUE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class Money:
    amount: float
    currency: str = "USD"

    def __post_init__(self) -> None:
        if not math.isfinite(self.amount):
            raise ValueError("Money amount must be finite.")
        if len(self.currency) != 3:
            raise ValueError("Currency must use a three-letter code.")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Currencies must match.")
        return Money(self.amount + other.amount, self.currency)


# ============================================================================
# 18. ADVANCED EXAMPLE: PLUGGABLE ORDER SYSTEM
# ============================================================================

class TaxPolicy(Protocol):
    def calculate(self, amount: float) -> float:
        ...


class NoTax:
    def calculate(self, amount: float) -> float:
        return 0.0


class FlatTax:
    def __init__(self, rate: float) -> None:
        if not 0 <= rate <= 1:
            raise ValueError("Tax rate must be between 0 and 1.")
        self.rate = rate

    def calculate(self, amount: float) -> float:
        return amount * self.rate


class ShippingPolicy(Protocol):
    def calculate(self, amount: float) -> float:
        ...


class FreeShipping:
    def calculate(self, amount: float) -> float:
        return 0.0


class FlatShipping:
    def __init__(self, fee: float) -> None:
        if fee < 0:
            raise ValueError("Shipping fee cannot be negative.")
        self.fee = fee

    def calculate(self, amount: float) -> float:
        return self.fee


class Checkout:
    """
    Checkout is composed from pricing, tax, and shipping policies.

    Each policy can evolve independently.
    """

    def __init__(
        self,
        pricing: PricingStrategy,
        tax: TaxPolicy,
        shipping: ShippingPolicy,
    ) -> None:
        self.pricing = pricing
        self.tax = tax
        self.shipping = shipping

    def calculate_total(self, subtotal: float) -> float:
        if subtotal < 0:
            raise ValueError("Subtotal cannot be negative.")

        discounted = self.pricing.calculate(subtotal)
        tax = self.tax.calculate(discounted)
        shipping = self.shipping.calculate(discounted)

        return discounted + tax + shipping


# ============================================================================
# 19. WHEN INHERITANCE IS APPROPRIATE
# ============================================================================

class Storage(ABC):
    """
    Inheritance can be useful when a stable abstraction defines a common
    contract and implementations genuinely represent specialized forms.
    """

    @abstractmethod
    def save(self, key: str, value: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def load(self, key: str) -> Optional[str]:
        raise NotImplementedError


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def save(self, key: str, value: str) -> None:
        self._data[key] = value

    def load(self, key: str) -> Optional[str]:
        return self._data.get(key)


class FileLikeStorage(Storage):
    """
    A simplified storage implementation kept in memory to remain
    self-contained. The interface demonstrates substitutability.
    """

    def __init__(self) -> None:
        self._records: dict[str, str] = {}

    def save(self, key: str, value: str) -> None:
        self._records[key] = value

    def load(self, key: str) -> Optional[str]:
        return self._records.get(key)


# ============================================================================
# 20. COMMON ANTI-PATTERN: DEEP INHERITANCE
# ============================================================================

class LevelOne:
    def operation(self) -> str:
        return "Level one"


class LevelTwo(LevelOne):
    def operation(self) -> str:
        return super().operation() + " -> level two"


class LevelThree(LevelTwo):
    def operation(self) -> str:
        return super().operation() + " -> level three"


class LevelFour(LevelThree):
    def operation(self) -> str:
        return super().operation() + " -> level four"


# ============================================================================
# 21. EDGE CASES
# ============================================================================

def validate_composition_edge_cases() -> None:
    try:
        OrderItem("Keyboard", 0, 50)
    except ValueError:
        pass

    try:
        Money(float("nan"))
    except ValueError:
        pass

    try:
        FlatTax(2.0)
    except ValueError:
        pass

    try:
        Inventory().remove("unknown", 1)
    except ValueError:
        pass


# ============================================================================
# 22. DEMONSTRATION
# ============================================================================

def main() -> None:
    print("=" * 72)
    print("COMPOSITION VS INHERITANCE")
    print("=" * 72)

    print("\n1. Inheritance")
    developer = Developer("Asha", "D001")
    manager = Manager("Ravi", "M001")
    print(developer.describe())
    print(developer.write_code())
    print(manager.describe())
    print(manager.manage())

    print("\n2. Composition")
    customer = Customer("Mira", "mira@example.com")
    order = Order(customer)
    order.add_item(OrderItem("Laptop", 2, 800))
    order.add_item(OrderItem("Mouse", 1, 25))
    print(f"Order total: ${order.total():.2f}")

    print("\n3. IS-A versus HAS-A")
    print(Car().move())
    composed_car = ComposedCar(Engine(150))
    print(composed_car.start())
    print(composed_car.move())

    print("\n4. Inheritance-based report reuse")
    print(SalesReport().render())

    print("\n5. Composition-based formatting")
    for formatter in (PlainTextFormatter(), MarkdownFormatter(), HtmlFormatter()):
        report = ComposedReport(formatter)
        print(report.render("Sales", "Revenue increased."))

    print("\n6. Coupling")
    print(TightlyCoupledInvoice(100).pay())
    print(Invoice(100, MockPaymentGateway()).pay())

    print("\n7. Runtime strategy replacement")
    cart = ShoppingCart(RegularPricing())
    cart.add(OrderItem("Book", 2, 30))
    print(f"Regular: ${cart.total():.2f}")
    cart.change_pricing_strategy(TenPercentDiscount())
    print(f"Discounted: ${cart.total():.2f}")

    print("\n8. Composed notification service")
    for channel in (EmailChannel(), SmsChannel(), PushChannel()):
        print(NotificationService(channel).notify("user-42", "Order shipped."))

    print("\n9. Composed order processing")
    inventory = Inventory()
    inventory.add("SSD", 10)
    processor = OrderProcessor(
        inventory=inventory,
        payment_gateway=MockPaymentGateway(),
        logger=ConsoleLogger(),
    )
    processor.process("SSD", 2, 120)
    print(f"Remaining SSD stock: {inventory.available('SSD')}")

    print("\n10. Interface segregation")
    source = MemoryBuffer()
    target = MemoryBuffer()
    source.write("Reusable component")
    copy_text(source, target)
    print(target.read())

    print("\n11. Functional composition")
    normalize_identifier = compose(trim, normalize_case, remove_spaces)
    print(normalize_identifier("  Customer Order  "))

    print("\n12. Test doubles")
    fake_inventory = FakeInventory(5)
    recording_gateway = RecordingGateway()
    silent_logger = SilentLogger()

    processor = OrderProcessor(
        fake_inventory,
        recording_gateway,
        silent_logger,
    )
    processor.process("item", 2, 50)
    print(recording_gateway.charges)
    print(silent_logger.messages)

    print("\n13. Value object")
    money_a = Money(10)
    money_b = Money(15)
    print(money_a.add(money_b))

    print("\n14. Advanced composed checkout")
    checkout = Checkout(
        pricing=TenPercentDiscount(),
        tax=FlatTax(0.18),
        shipping=FlatShipping(50),
    )
    print(f"Checkout total: ${checkout.calculate_total(1000):.2f}")

    print("\n15. Abstract storage")
    storage: Storage = InMemoryStorage()
    storage.save("language", "Python")
    print(storage.load("language"))

    print("\n16. Deep inheritance")
    print(LevelFour().operation())

    print("\n17. Edge-case validation")
    validate_composition_edge_cases()
    print("Expected validation errors were handled.")

    print("\n18. Substitutability")
    demonstrate_substitutability()

    print("\n19. Performance note")
    start = time.perf_counter()
    result = sum(i * i for i in range(100_000))
    elapsed = time.perf_counter() - start
    print(f"Computation result: {result}")
    print(f"Elapsed time: {elapsed:.6f} seconds")

    print("\nKey design rule:")
    print(
        "Prefer composition when behavior should be replaceable, combined, "
        "configured, or varied independently. Use inheritance when there "
        "is a stable subtype relationship and substitutability is genuine."
    )


if __name__ == "__main__":
    main()
