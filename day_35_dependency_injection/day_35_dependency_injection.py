"""
Dependency Injection in Python
==============================

A self-contained progression from constructor injection to a small dependency
injection container and testable application services.

The example models an order-processing system where business logic depends on
interfaces rather than concrete infrastructure.

Run:
    python dependency_injection.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Dict, Generic, List, Protocol, TypeVar


# ---------------------------------------------------------------------------
# Core domain model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Order:
    order_id: str
    customer_email: str
    amount: float


@dataclass(frozen=True)
class Receipt:
    order_id: str
    amount: float
    message: str


# ---------------------------------------------------------------------------
# Dependency contracts
# ---------------------------------------------------------------------------

class PaymentGateway(Protocol):
    """Contract required by the order service."""

    def charge(self, order: Order) -> bool:
        ...


class NotificationService(Protocol):
    """Contract required for customer notification."""

    def send_receipt(self, order: Order, receipt: Receipt) -> None:
        ...


class OrderRepository(Protocol):
    """Contract for persistent order storage."""

    def save(self, order: Order) -> None:
        ...

    def find(self, order_id: str) -> Order | None:
        ...


# ---------------------------------------------------------------------------
# Concrete infrastructure implementations
# ---------------------------------------------------------------------------

class InMemoryOrderRepository:
    """Simple repository useful for local execution and tests."""

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def save(self, order: Order) -> None:
        if order.order_id in self._orders:
            raise ValueError(f"Order already exists: {order.order_id}")
        self._orders[order.order_id] = order

    def find(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)


class ConsolePaymentGateway:
    """Infrastructure adapter that simulates a payment provider."""

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.charged_orders: List[str] = []

    def charge(self, order: Order) -> bool:
        if not self.available:
            return False

        if order.amount <= 0:
            return False

        self.charged_orders.append(order.order_id)
        return True


class ConsoleNotificationService:
    """Infrastructure adapter that emits receipts to the console."""

    def __init__(self) -> None:
        self.sent_receipts: List[str] = []

    def send_receipt(self, order: Order, receipt: Receipt) -> None:
        if not order.customer_email.strip():
            raise ValueError("Customer email cannot be empty")

        self.sent_receipts.append(order.order_id)
        print(f"Notification sent to {order.customer_email}: {receipt.message}")


# ---------------------------------------------------------------------------
# Constructor injection
# ---------------------------------------------------------------------------

class OrderService:
    """
    Application service using constructor injection.

    The service receives abstractions instead of constructing infrastructure
    internally. This separates business rules from infrastructure choices.
    """

    def __init__(
        self,
        repository: OrderRepository,
        payment_gateway: PaymentGateway,
        notification_service: NotificationService,
    ) -> None:
        self.repository = repository
        self.payment_gateway = payment_gateway
        self.notification_service = notification_service

    def place_order(self, order: Order) -> Receipt:
        self._validate_order(order)

        if self.repository.find(order.order_id) is not None:
            raise ValueError(f"Duplicate order: {order.order_id}")

        if not self.payment_gateway.charge(order):
            raise RuntimeError("Payment was declined or unavailable")

        self.repository.save(order)

        receipt = Receipt(
            order_id=order.order_id,
            amount=order.amount,
            message=f"Order {order.order_id} paid successfully: ${order.amount:.2f}",
        )

        self.notification_service.send_receipt(order, receipt)
        return receipt

    @staticmethod
    def _validate_order(order: Order) -> None:
        if not order.order_id.strip():
            raise ValueError("Order ID is required")
        if not order.customer_email.strip():
            raise ValueError("Customer email is required")
        if "@" not in order.customer_email:
            raise ValueError("Customer email is invalid")
        if order.amount <= 0:
            raise ValueError("Order amount must be greater than zero")


# ---------------------------------------------------------------------------
# Dependency inversion without a framework
# ---------------------------------------------------------------------------

class FakePaymentGateway:
    """Test double that records calls without contacting real infrastructure."""

    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls: List[Order] = []

    def charge(self, order: Order) -> bool:
        self.calls.append(order)
        return self.result


class FakeNotificationService:
    """Test double for deterministic service-level tests."""

    def __init__(self) -> None:
        self.calls: List[tuple[Order, Receipt]] = []

    def send_receipt(self, order: Order, receipt: Receipt) -> None:
        self.calls.append((order, receipt))


# ---------------------------------------------------------------------------
# Function injection
# ---------------------------------------------------------------------------

TaxCalculator = Callable[[float], float]


def calculate_total(amount: float, tax_calculator: TaxCalculator) -> float:
    """Function injection makes the pricing rule independently replaceable."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    return amount + tax_calculator(amount)


def standard_tax(amount: float) -> float:
    return amount * 0.18


def zero_tax(amount: float) -> float:
    return 0.0


# ---------------------------------------------------------------------------
# Setter/property injection and its trade-off
# ---------------------------------------------------------------------------

class AuditLogger:
    def log(self, message: str) -> None:
        print(f"AUDIT: {message}")


class OptionalAuditOrderProcessor:
    """
    Property injection is useful when a dependency is genuinely optional.

    Unlike constructor injection, the object can temporarily exist without the
    dependency. That flexibility also means the class must handle a missing
    dependency explicitly.
    """

    def __init__(self) -> None:
        self.audit_logger: AuditLogger | None = None

    def set_audit_logger(self, logger: AuditLogger) -> None:
        self.audit_logger = logger

    def process(self, order: Order) -> str:
        message = f"Processed {order.order_id}"
        if self.audit_logger is not None:
            self.audit_logger.log(message)
        return message


# ---------------------------------------------------------------------------
# A lightweight dependency injection container
# ---------------------------------------------------------------------------

T = TypeVar("T")


class Provider(Generic[T]):
    """Stores a factory and optionally caches its produced object."""

    def __init__(self, factory: Callable[[], T], singleton: bool = False) -> None:
        self.factory = factory
        self.singleton = singleton
        self._instance: T | None = None

    def get(self) -> T:
        if self.singleton:
            if self._instance is None:
                self._instance = self.factory()
            return self._instance
        return self.factory()


class Container:
    """
    Minimal dependency injection container.

    This is intentionally small so the mechanics remain visible:
    registration maps an abstraction to a provider, while resolution asks the
    container for the configured implementation.
    """

    def __init__(self) -> None:
        self._providers: Dict[str, Provider[object]] = {}

    def register(
        self,
        abstraction: type,
        factory: Callable[[], object],
        *,
        singleton: bool = False,
    ) -> None:
        key = self._key(abstraction)
        self._providers[key] = Provider(factory, singleton)

    def resolve(self, abstraction: type[T]) -> T:
        key = self._key(abstraction)

        if key not in self._providers:
            raise LookupError(f"No dependency registered for {abstraction.__name__}")

        return self._providers[key].get()  # type: ignore[return-value]

    @staticmethod
    def _key(abstraction: type) -> str:
        return f"{abstraction.__module__}.{abstraction.__qualname__}"


class ProductionOrderApplication:
    """Composition-root example showing explicit object graph construction."""

    def __init__(self, service: OrderService) -> None:
        self.service = service

    def execute(self, order: Order) -> Receipt:
        return self.service.place_order(order)


def build_production_container() -> Container:
    """
    Composition root.

    Infrastructure choices are centralized here rather than scattered across
    domain and application classes.
    """
    container = Container()

    container.register(
        OrderRepository,
        lambda: InMemoryOrderRepository(),
        singleton=True,
    )

    container.register(
        PaymentGateway,
        lambda: ConsolePaymentGateway(),
    )

    container.register(
        NotificationService,
        lambda: ConsoleNotificationService(),
    )

    def build_order_service() -> OrderService:
        return OrderService(
            repository=container.resolve(OrderRepository),
            payment_gateway=container.resolve(PaymentGateway),
            notification_service=container.resolve(NotificationService),
        )

    container.register(OrderService, build_order_service)

    return container


# ---------------------------------------------------------------------------
# Testability demonstrations
# ---------------------------------------------------------------------------

def test_successful_order() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway(result=True)
    notification = FakeNotificationService()

    service = OrderService(repository, payment, notification)

    order = Order("ORD-100", "customer@example.com", 250.00)
    receipt = service.place_order(order)

    assert receipt.order_id == "ORD-100"
    assert repository.find("ORD-100") == order
    assert len(payment.calls) == 1
    assert len(notification.calls) == 1


def test_payment_failure_does_not_persist_order() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway(result=False)
    notification = FakeNotificationService()

    service = OrderService(repository, payment, notification)
    order = Order("ORD-101", "customer@example.com", 300.00)

    try:
        service.place_order(order)
    except RuntimeError as exc:
        assert "Payment" in str(exc)
    else:
        raise AssertionError("Expected payment failure")

    assert repository.find("ORD-101") is None
    assert notification.calls == []


def test_duplicate_order_is_rejected_before_payment() -> None:
    repository = InMemoryOrderRepository()
    existing = Order("ORD-102", "existing@example.com", 50.00)
    repository.save(existing)

    payment = FakePaymentGateway()
    notification = FakeNotificationService()
    service = OrderService(repository, payment, notification)

    try:
        service.place_order(existing)
    except ValueError as exc:
        assert "Duplicate" in str(exc)
    else:
        raise AssertionError("Expected duplicate-order failure")

    assert payment.calls == []


def test_invalid_email_is_rejected() -> None:
    service = OrderService(
        InMemoryOrderRepository(),
        FakePaymentGateway(),
        FakeNotificationService(),
    )

    try:
        service.place_order(Order("ORD-103", "invalid-email", 20.00))
    except ValueError as exc:
        assert "email" in str(exc).lower()
    else:
        raise AssertionError("Expected invalid email failure")


def test_function_injection() -> None:
    assert calculate_total(100.0, standard_tax) == 118.0
    assert calculate_total(100.0, zero_tax) == 100.0


# ---------------------------------------------------------------------------
# Anti-pattern demonstration
# ---------------------------------------------------------------------------

class HardWiredOrderService:
    """
    Deliberately demonstrates the problem DI solves.

    The class creates its own dependencies, so tests cannot easily replace the
    payment provider or notification mechanism.
    """

    def place_order(self, order: Order) -> Receipt:
        payment_gateway = ConsolePaymentGateway()
        notification_service = ConsoleNotificationService()

        if not payment_gateway.charge(order):
            raise RuntimeError("Payment failed")

        receipt = Receipt(
            order.order_id,
            order.amount,
            f"Order {order.order_id} processed",
        )
        notification_service.send_receipt(order, receipt)
        return receipt


# ---------------------------------------------------------------------------
# Scope and lifecycle behavior
# ---------------------------------------------------------------------------

def demonstrate_lifetimes() -> None:
    container = Container()

    container.register(
        OrderRepository,
        lambda: InMemoryOrderRepository(),
        singleton=True,
    )

    first = container.resolve(OrderRepository)
    second = container.resolve(OrderRepository)

    assert first is second

    container.register(
        PaymentGateway,
        lambda: ConsolePaymentGateway(),
        singleton=False,
    )

    first_payment = container.resolve(PaymentGateway)
    second_payment = container.resolve(PaymentGateway)

    assert first_payment is not second_payment


# ---------------------------------------------------------------------------
# Executable demonstration
# ---------------------------------------------------------------------------

def main() -> None:
    print("Dependency Injection demonstration")

    print("\nConstructor injection")
    container = build_production_container()
    application = ProductionOrderApplication(container.resolve(OrderService))

    receipt = application.execute(
        Order(
            order_id="ORD-200",
            customer_email="buyer@example.com",
            amount=149.99,
        )
    )
    print(receipt.message)

    print("\nFunction injection")
    print(f"Taxed total: ${calculate_total(100, standard_tax):.2f}")
    print(f"Tax-exempt total: ${calculate_total(100, zero_tax):.2f}")

    print("\nOptional property injection")
    processor = OptionalAuditOrderProcessor()
    processor.set_audit_logger(AuditLogger())
    processor.process(Order("ORD-201", "audit@example.com", 75.00))

    print("\nTestability")
    test_successful_order()
    test_payment_failure_does_not_persist_order()
    test_duplicate_order_is_rejected_before_payment()
    test_invalid_email_is_rejected()
    test_function_injection()
    demonstrate_lifetimes()
    print("All dependency-injection tests passed.")

    print("\nDI design boundary")
    print(
        "Application services own business decisions; the composition root "
        "selects concrete infrastructure."
    )


if __name__ == "__main__":
    main()
