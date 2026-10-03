"""
Coupling & Cohesion: Loose Coupling and High Cohesion

A self-contained technical study implemented as a small order-processing system.

The design evolves from tightly coupled code toward:
- high cohesion: each component has one closely related responsibility
- loose coupling: components depend on stable abstractions rather than concrete details

The examples use only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Callable, Iterable, Protocol
import json
import logging
import unittest


# ---------------------------------------------------------------------------
# Fundamental domain model
# ---------------------------------------------------------------------------

class OrderStatus(str, Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"
    SHIPPED = "shipped"


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    unit_price: Decimal


@dataclass(frozen=True)
class OrderItem:
    product: Product
    quantity: int

    @property
    def subtotal(self) -> Decimal:
        return self.product.unit_price * self.quantity


@dataclass
class Order:
    order_id: str
    customer_email: str
    items: list[OrderItem]
    status: OrderStatus = OrderStatus.CREATED

    @property
    def total(self) -> Decimal:
        return sum((item.subtotal for item in self.items), Decimal("0.00"))

    def mark_paid(self) -> None:
        if self.status != OrderStatus.CREATED:
            raise ValueError(
                f"Only a created order can become paid; current state is {self.status.value}"
            )
        self.status = OrderStatus.PAID

    def cancel(self) -> None:
        if self.status == OrderStatus.SHIPPED:
            raise ValueError("A shipped order cannot be cancelled")
        self.status = OrderStatus.CANCELLED


# ---------------------------------------------------------------------------
# A deliberately tightly coupled design
# ---------------------------------------------------------------------------

class TightlyCoupledOrderService:
    """
    This class demonstrates excessive coupling.

    One class knows about:
    - order validation
    - inventory storage
    - payment implementation
    - email implementation
    - shipping implementation
    - persistence format

    Changing one infrastructure mechanism therefore forces changes here.
    """

    def __init__(self) -> None:
        self.inventory_database = {
            "LAPTOP": 5,
            "MOUSE": 20,
            "KEYBOARD": 10,
        }

    def place_order(self, order: Order) -> str:
        if not order.items:
            raise ValueError("An order must contain at least one item")

        for item in order.items:
            product_id = item.product.product_id

            if item.quantity <= 0:
                raise ValueError("Quantity must be positive")

            if self.inventory_database.get(product_id, 0) < item.quantity:
                raise ValueError(f"Insufficient inventory for {product_id}")

        for item in order.items:
            self.inventory_database[item.product.product_id] -= item.quantity

        # Concrete payment behavior is embedded directly in the workflow.
        payment_reference = f"STRIPE-SIMULATED-{order.order_id}"

        # Concrete email behavior is also embedded directly.
        print(
            f"[EMAIL SMTP] Payment {payment_reference} confirmed for "
            f"{order.customer_email}"
        )

        # Shipping logic is embedded directly.
        print(f"[COURIER API] Shipping order {order.order_id}")

        order.mark_paid()

        # Persistence representation is embedded directly.
        record = {
            "order_id": order.order_id,
            "customer_email": order.customer_email,
            "total": str(order.total),
            "payment_reference": payment_reference,
            "status": order.status.value,
        }

        print("[DATABASE] INSERT", json.dumps(record))
        return payment_reference


# ---------------------------------------------------------------------------
# Coupling analysis
# ---------------------------------------------------------------------------

def demonstrate_tight_coupling() -> None:
    print("\n=== Tight coupling ===")

    laptop = Product("LAPTOP", "Developer Laptop", Decimal("1200.00"))
    order = Order(
        order_id="ORD-TIGHT-001",
        customer_email="developer@example.com",
        items=[OrderItem(laptop, 1)],
    )

    service = TightlyCoupledOrderService()
    service.place_order(order)

    print(
        "Problem demonstrated: changing the payment provider, mail transport, "
        "courier, or database representation requires editing the same service."
    )


# ---------------------------------------------------------------------------
# Abstractions used by the loosely coupled design
# ---------------------------------------------------------------------------

class InventoryRepository(Protocol):
    def reserve(self, product_id: str, quantity: int) -> None:
        ...

    def release(self, product_id: str, quantity: int) -> None:
        ...


class PaymentGateway(Protocol):
    def charge(self, order_id: str, amount: Decimal) -> str:
        ...


class NotificationSender(Protocol):
    def send_payment_confirmation(
        self,
        customer_email: str,
        order_id: str,
        amount: Decimal,
    ) -> None:
        ...


class OrderRepository(Protocol):
    def save(self, order: Order) -> None:
        ...

    def get(self, order_id: str) -> Order | None:
        ...


class ShippingService(Protocol):
    def create_shipment(self, order: Order) -> str:
        ...


# ---------------------------------------------------------------------------
# Highly cohesive infrastructure components
# ---------------------------------------------------------------------------

class InMemoryInventoryRepository:
    """
    Cohesion:
    This object only manages inventory availability and reservations.

    It does not know about payment, email, shipping, orders, or HTTP.
    """

    def __init__(self, initial_stock: dict[str, int]) -> None:
        self._stock = dict(initial_stock)

    def reserve(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Inventory reservation quantity must be positive")

        available = self._stock.get(product_id, 0)

        if available < quantity:
            raise ValueError(
                f"Insufficient inventory for {product_id}: "
                f"requested={quantity}, available={available}"
            )

        self._stock[product_id] = available - quantity

    def release(self, product_id: str, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Inventory release quantity must be positive")

        self._stock[product_id] = self._stock.get(product_id, 0) + quantity

    def available(self, product_id: str) -> int:
        return self._stock.get(product_id, 0)


class FakePaymentGateway:
    """
    Cohesion:
    This implementation is responsible only for charging payments.

    The application does not depend on the internal payment mechanism.
    """

    def __init__(self, fail_for_orders: set[str] | None = None) -> None:
        self.charges: list[tuple[str, Decimal]] = []
        self.fail_for_orders = fail_for_orders or set()

    def charge(self, order_id: str, amount: Decimal) -> str:
        if amount <= Decimal("0"):
            raise ValueError("Payment amount must be positive")

        if order_id in self.fail_for_orders:
            raise RuntimeError(f"Payment gateway rejected order {order_id}")

        self.charges.append((order_id, amount))
        return f"PAY-{order_id}"


class ConsoleNotificationSender:
    """Only responsible for rendering and sending payment notifications."""

    def send_payment_confirmation(
        self,
        customer_email: str,
        order_id: str,
        amount: Decimal,
    ) -> None:
        print(
            f"[NOTIFICATION] {customer_email}: "
            f"order {order_id} paid for {amount:.2f}"
        )


class InMemoryOrderRepository:
    """Only responsible for storing and retrieving order objects."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)


class FakeShippingService:
    """Only responsible for creating shipment records."""

    def __init__(self) -> None:
        self.shipments: list[str] = []

    def create_shipment(self, order: Order) -> str:
        if order.status != OrderStatus.PAID:
            raise ValueError("Only paid orders can be shipped")

        shipment_id = f"SHIP-{order.order_id}"
        self.shipments.append(shipment_id)
        order.status = OrderStatus.SHIPPED
        return shipment_id


# ---------------------------------------------------------------------------
# Highly cohesive domain services
# ---------------------------------------------------------------------------

class OrderValidator:
    """
    Validation has high cohesion because every rule concerns order validity.

    It does not persist, charge, notify, or ship anything.
    """

    @staticmethod
    def validate(order: Order) -> None:
        if not order.order_id.strip():
            raise ValueError("Order ID cannot be empty")

        if "@" not in order.customer_email:
            raise ValueError("Customer email is invalid")

        if not order.items:
            raise ValueError("Order must contain at least one item")

        for item in order.items:
            if not item.product.product_id.strip():
                raise ValueError("Product ID cannot be empty")
            if item.product.unit_price < 0:
                raise ValueError("Product price cannot be negative")
            if item.quantity <= 0:
                raise ValueError("Quantity must be positive")


class OrderPricing:
    """Only calculates order totals and pricing-related values."""

    @staticmethod
    def subtotal(item: OrderItem) -> Decimal:
        return item.product.unit_price * item.quantity

    @staticmethod
    def total(order: Order) -> Decimal:
        return sum(
            (OrderPricing.subtotal(item) for item in order.items),
            Decimal("0.00"),
        )


class OrderApplicationService:
    """
    Coordinates cohesive components.

    This class still knows which operations form the use case, but it does not
    know how inventory, payment, persistence, notification, or shipping work.
    """

    def __init__(
        self,
        inventory: InventoryRepository,
        payments: PaymentGateway,
        notifications: NotificationSender,
        orders: OrderRepository,
    ) -> None:
        self.inventory = inventory
        self.payments = payments
        self.notifications = notifications
        self.orders = orders
        self.validator = OrderValidator()

    def create_and_pay(self, order: Order) -> str:
        self.validator.validate(order)

        reserved: list[tuple[str, int]] = []

        try:
            for item in order.items:
                self.inventory.reserve(
                    item.product.product_id,
                    item.quantity,
                )
                reserved.append(
                    (item.product.product_id, item.quantity)
                )

            amount = OrderPricing.total(order)
            payment_reference = self.payments.charge(
                order.order_id,
                amount,
            )

            order.mark_paid()
            self.orders.save(order)

            self.notifications.send_payment_confirmation(
                order.customer_email,
                order.order_id,
                amount,
            )

            return payment_reference

        except Exception:
            # Reservation compensation prevents a failed payment from leaving
            # inventory permanently reduced.
            for product_id, quantity in reversed(reserved):
                self.inventory.release(product_id, quantity)

            raise


# ---------------------------------------------------------------------------
# Dependency injection and substitution
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    A separate cohesive component demonstrates another boundary.

    It records domain events without making the order service responsible for
    log formatting or storage.
    """

    def __init__(self) -> None:
        self.events: list[str] = []

    def record(self, event: str) -> None:
        self.events.append(event)


class AuditedOrderApplicationService:
    """
    Adds auditing through dependency injection.

    The original service does not need to know that auditing exists.
    """

    def __init__(
        self,
        inventory: InventoryRepository,
        payments: PaymentGateway,
        notifications: NotificationSender,
        orders: OrderRepository,
        audit: AuditLogger,
    ) -> None:
        self.inventory = inventory
        self.payments = payments
        self.notifications = notifications
        self.orders = orders
        self.audit = audit

    def create_and_pay(self, order: Order) -> str:
        OrderValidator.validate(order)

        reserved: list[tuple[str, int]] = []

        try:
            for item in order.items:
                self.inventory.reserve(
                    item.product.product_id,
                    item.quantity,
                )
                reserved.append(
                    (item.product.product_id, item.quantity)
                )

            amount = OrderPricing.total(order)
            payment_reference = self.payments.charge(
                order.order_id,
                amount,
            )

            order.mark_paid()
            self.orders.save(order)
            self.audit.record(
                f"ORDER_PAID:{order.order_id}:{payment_reference}"
            )

            self.notifications.send_payment_confirmation(
                order.customer_email,
                order.order_id,
                amount,
            )

            return payment_reference

        except Exception:
            for product_id, quantity in reversed(reserved):
                self.inventory.release(product_id, quantity)
            raise


# ---------------------------------------------------------------------------
# Failure and edge-case demonstrations
# ---------------------------------------------------------------------------

def demonstrate_loose_coupling() -> None:
    print("\n=== Loose coupling and high cohesion ===")

    laptop = Product(
        "LAPTOP",
        "Developer Laptop",
        Decimal("1200.00"),
    )

    mouse = Product(
        "MOUSE",
        "Wireless Mouse",
        Decimal("40.00"),
    )

    order = Order(
        order_id="ORD-LOOSE-001",
        customer_email="developer@example.com",
        items=[
            OrderItem(laptop, 1),
            OrderItem(mouse, 2),
        ],
    )

    inventory = InMemoryInventoryRepository(
        {
            "LAPTOP": 5,
            "MOUSE": 20,
        }
    )

    payments = FakePaymentGateway()
    notifications = ConsoleNotificationSender()
    repository = InMemoryOrderRepository()

    service = OrderApplicationService(
        inventory=inventory,
        payments=payments,
        notifications=notifications,
        orders=repository,
    )

    payment_reference = service.create_and_pay(order)

    print(f"Payment reference: {payment_reference}")
    print(f"Order total: {order.total:.2f}")
    print(f"Remaining laptops: {inventory.available('LAPTOP')}")
    print(f"Remaining mice: {inventory.available('MOUSE')}")


def demonstrate_payment_failure_rollback() -> None:
    print("\n=== Failure compensation ===")

    product = Product("KEYBOARD", "Mechanical Keyboard", Decimal("90.00"))
    order = Order(
        order_id="ORD-FAIL-001",
        customer_email="developer@example.com",
        items=[OrderItem(product, 2)],
    )

    inventory = InMemoryInventoryRepository({"KEYBOARD": 5})
    payments = FakePaymentGateway({"ORD-FAIL-001"})
    notifications = ConsoleNotificationSender()
    repository = InMemoryOrderRepository()

    service = OrderApplicationService(
        inventory,
        payments,
        notifications,
        repository,
    )

    before = inventory.available("KEYBOARD")

    try:
        service.create_and_pay(order)
    except RuntimeError as exc:
        print(f"Expected failure: {exc}")

    after = inventory.available("KEYBOARD")

    print(f"Inventory before failed transaction: {before}")
    print(f"Inventory after failed transaction:  {after}")
    print("Compensation restored the reserved inventory.")


def demonstrate_substitutability() -> None:
    print("\n=== Dependency substitution ===")

    class SilentNotificationSender:
        """A test double that satisfies NotificationSender."""

        def __init__(self) -> None:
            self.messages: list[str] = []

        def send_payment_confirmation(
            self,
            customer_email: str,
            order_id: str,
            amount: Decimal,
        ) -> None:
            self.messages.append(
                f"{customer_email}|{order_id}|{amount}"
            )

    product = Product("MOUSE", "Wireless Mouse", Decimal("40.00"))
    order = Order(
        order_id="ORD-TEST-001",
        customer_email="test@example.com",
        items=[OrderItem(product, 1)],
    )

    notification = SilentNotificationSender()

    service = OrderApplicationService(
        inventory=InMemoryInventoryRepository({"MOUSE": 10}),
        payments=FakePaymentGateway(),
        notifications=notification,
        orders=InMemoryOrderRepository(),
    )

    service.create_and_pay(order)

    print("No real email service was required.")
    print(f"Captured notification: {notification.messages[0]}")


# ---------------------------------------------------------------------------
# Dependency graph inspection
# ---------------------------------------------------------------------------

def dependency_graph() -> dict[str, list[str]]:
    """
    The graph makes architectural coupling visible.

    High-level application logic depends on abstractions. Concrete adapters
    implement those abstractions, rather than being constructed inside the
    application service.
    """

    return {
        "OrderApplicationService": [
            "InventoryRepository",
            "PaymentGateway",
            "NotificationSender",
            "OrderRepository",
            "OrderValidator",
            "OrderPricing",
        ],
        "InMemoryInventoryRepository": ["InventoryRepository"],
        "FakePaymentGateway": ["PaymentGateway"],
        "ConsoleNotificationSender": ["NotificationSender"],
        "InMemoryOrderRepository": ["OrderRepository"],
    }


def print_dependency_graph() -> None:
    print("\n=== Dependency graph ===")

    graph = dependency_graph()

    for component, dependencies in graph.items():
        print(f"{component} -> {', '.join(dependencies)}")


# ---------------------------------------------------------------------------
# Cohesion and coupling metrics
# ---------------------------------------------------------------------------

@dataclass
class ComponentProfile:
    name: str
    responsibilities: set[str]
    external_dependencies: set[str]

    @property
    def responsibility_count(self) -> int:
        return len(self.responsibilities)

    @property
    def dependency_count(self) -> int:
        return len(self.external_dependencies)


def compare_component_profiles() -> None:
    print("\n=== Architectural profile ===")

    profiles = [
        ComponentProfile(
            "TightlyCoupledOrderService",
            {
                "validation",
                "inventory",
                "payment",
                "notification",
                "shipping",
                "persistence",
            },
            {
                "inventory_database",
                "payment_provider",
                "smtp",
                "courier_api",
                "database_schema",
            },
        ),
        ComponentProfile(
            "OrderValidator",
            {"order validation"},
            set(),
        ),
        ComponentProfile(
            "OrderPricing",
            {"pricing calculation"},
            set(),
        ),
        ComponentProfile(
            "InMemoryInventoryRepository",
            {"inventory reservation"},
            set(),
        ),
        ComponentProfile(
            "FakePaymentGateway",
            {"payment charging"},
            set(),
        ),
        ComponentProfile(
            "OrderApplicationService",
            {"use-case orchestration"},
            {
                "InventoryRepository",
                "PaymentGateway",
                "NotificationSender",
                "OrderRepository",
            },
        ),
    ]

    for profile in profiles:
        print(
            f"{profile.name}: "
            f"responsibilities={profile.responsibility_count}, "
            f"external_dependencies={profile.dependency_count}"
        )

    print(
        "These counts are illustrative design signals, not universal "
        "software-quality metrics."
    )


# ---------------------------------------------------------------------------
# Parsing and validation of a small architecture configuration
# ---------------------------------------------------------------------------

def parse_component_configuration(raw: str) -> dict[str, list[str]]:
    """
    Parsing is intentionally kept separate from the domain model.

    This prevents configuration syntax from leaking into business logic.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid component configuration JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Configuration root must be an object")

    result: dict[str, list[str]] = {}

    for name, dependencies in data.items():
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Component names must be non-empty strings")

        if not isinstance(dependencies, list):
            raise ValueError(
                f"Dependencies for {name} must be represented as a list"
            )

        if not all(isinstance(dep, str) for dep in dependencies):
            raise ValueError(
                f"Dependencies for {name} must contain only strings"
            )

        result[name] = dependencies

    return result


def demonstrate_configuration_boundary() -> None:
    print("\n=== Configuration boundary ===")

    raw = """
    {
        "OrderApplicationService": [
            "InventoryRepository",
            "PaymentGateway",
            "NotificationSender",
            "OrderRepository"
        ],
        "OrderValidator": [],
        "OrderPricing": []
    }
    """

    configuration = parse_component_configuration(raw)

    for component, dependencies in configuration.items():
        print(f"{component}: {dependencies}")


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class CouplingCohesionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.product = Product(
            "BOOK",
            "Architecture Book",
            Decimal("50.00"),
        )

    def build_service(
        self,
        payment: PaymentGateway | None = None,
        notification: NotificationSender | None = None,
    ) -> tuple[
        OrderApplicationService,
        InMemoryInventoryRepository,
        InMemoryOrderRepository,
    ]:
        inventory = InMemoryInventoryRepository({"BOOK": 10})
        repository = InMemoryOrderRepository()

        service = OrderApplicationService(
            inventory=inventory,
            payments=payment or FakePaymentGateway(),
            notifications=notification or ConsoleNotificationSender(),
            orders=repository,
        )

        return service, inventory, repository

    def test_pricing_is_cohesive(self) -> None:
        order = Order(
            "T1",
            "user@example.com",
            [OrderItem(self.product, 3)],
        )

        self.assertEqual(OrderPricing.total(order), Decimal("150.00"))

    def test_dependency_can_be_replaced(self) -> None:
        messages: list[str] = []

        class TestNotifier:
            def send_payment_confirmation(
                self,
                customer_email: str,
                order_id: str,
                amount: Decimal,
            ) -> None:
                messages.append(order_id)

        service, _, _ = self.build_service(
            notification=TestNotifier()
        )

        order = Order(
            "T2",
            "user@example.com",
            [OrderItem(self.product, 1)],
        )

        service.create_and_pay(order)

        self.assertEqual(messages, ["T2"])

    def test_failed_payment_restores_inventory(self) -> None:
        payment = FakePaymentGateway({"T3"})

        service, inventory, _ = self.build_service(payment)

        order = Order(
            "T3",
            "user@example.com",
            [OrderItem(self.product, 4)],
        )

        with self.assertRaises(RuntimeError):
            service.create_and_pay(order)

        self.assertEqual(inventory.available("BOOK"), 10)

    def test_invalid_order_is_rejected_before_infrastructure(self) -> None:
        payment = FakePaymentGateway()
        service, inventory, _ = self.build_service(payment)

        invalid = Order(
            "T4",
            "not-an-email",
            [OrderItem(self.product, 1)],
        )

        with self.assertRaises(ValueError):
            service.create_and_pay(invalid)

        self.assertEqual(payment.charges, [])
        self.assertEqual(inventory.available("BOOK"), 10)

    def test_shipping_depends_on_paid_state(self) -> None:
        shipping = FakeShippingService()

        order = Order(
            "T5",
            "user@example.com",
            [OrderItem(self.product, 1)],
        )

        with self.assertRaises(ValueError):
            shipping.create_shipment(order)

        order.mark_paid()
        shipment = shipping.create_shipment(order)

        self.assertEqual(shipment, "SHIP-T5")
        self.assertEqual(order.status, OrderStatus.SHIPPED)


# ---------------------------------------------------------------------------
# Operational considerations
# ---------------------------------------------------------------------------

def demonstrate_logging_boundary() -> None:
    print("\n=== Logging as a replaceable concern ===")

    logger = logging.getLogger("coupling_demo")
    logger.handlers.clear()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)

    logger.info(
        "A cohesive component should use an established logging boundary "
        "rather than embedding file, console, or remote-log implementation."
    )


def demonstrate_decimal_validation() -> None:
    print("\n=== Boundary validation ===")

    raw_prices = ["19.99", "0.00", "-5.00", "invalid"]

    for raw in raw_prices:
        try:
            price = Decimal(raw)

            if price < 0:
                raise ValueError("Price cannot be negative")

            print(f"Accepted price: {price:.2f}")

        except (InvalidOperation, ValueError) as exc:
            print(f"Rejected price {raw!r}: {exc}")


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main() -> None:
    demonstrate_tight_coupling()
    demonstrate_loose_coupling()
    demonstrate_payment_failure_rollback()
    demonstrate_substitutability()
    print_dependency_graph()
    compare_component_profiles()
    demonstrate_configuration_boundary()
    demonstrate_logging_boundary()
    demonstrate_decimal_validation()

    print("\n=== Executing focused tests ===")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        CouplingCohesionTests
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    print("\nAll coupling and cohesion tests passed.")


if __name__ == "__main__":
    main()
