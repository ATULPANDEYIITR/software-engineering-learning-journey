from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Protocol
from uuid import uuid4


# ============================================================
# Architectural Patterns: Layered, MVC, and Hexagonal
# ============================================================
#
# This executable program uses one business domain, an order
# management service, to demonstrate three different ways of
# organizing the same responsibilities:
#
# Layered:
#   Presentation -> Application -> Domain -> Infrastructure
#
# MVC:
#   Controller -> Model -> View
#
# Hexagonal:
#   Domain/Application Core <- Ports <- Adapters
#
# The business rule is deliberately kept stable while the
# surrounding architecture changes. This makes the architectural
# boundaries visible instead of treating the patterns as syntax.
# ============================================================


# ------------------------------------------------------------
# Shared domain model
# ------------------------------------------------------------

@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    unit_price: float


@dataclass(frozen=True)
class OrderItem:
    product_id: str
    quantity: int
    unit_price: float

    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price


@dataclass
class Order:
    order_id: str
    customer_id: str
    items: List[OrderItem]
    status: str = "PENDING"

    @property
    def total(self) -> float:
        return round(sum(item.subtotal for item in self.items), 2)

    def mark_confirmed(self) -> None:
        if self.status != "PENDING":
            raise ValueError(f"Cannot confirm order in state {self.status}")
        self.status = "CONFIRMED"


class OrderValidationError(ValueError):
    """Raised when a business invariant is violated."""


def validate_order_items(items: List[OrderItem]) -> None:
    if not items:
        raise OrderValidationError("An order must contain at least one item.")

    for item in items:
        if item.quantity <= 0:
            raise OrderValidationError(
                f"Quantity must be positive for product {item.product_id}."
            )
        if item.unit_price < 0:
            raise OrderValidationError(
                f"Unit price cannot be negative for product {item.product_id}."
            )


# ============================================================
# LAYERED ARCHITECTURE
# ============================================================
#
# Presentation layer:
#   Receives and formats user-facing requests.
#
# Application layer:
#   Coordinates the use case.
#
# Domain layer:
#   Owns business entities and business rules.
#
# Infrastructure layer:
#   Persists data and talks to external systems.
#
# A key consequence is that each layer should communicate
# primarily with the layer immediately below it. This is useful
# when responsibilities are stable and a conventional enterprise
# structure is preferred.
# ============================================================


# Infrastructure layer

class InMemoryOrderRepository:
    """Infrastructure implementation of persistence."""

    def __init__(self) -> None:
        self._orders: Dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def find_by_id(self, order_id: str) -> Optional[Order]:
        return self._orders.get(order_id)


class ConsoleNotificationService:
    """Infrastructure service representing an external notification system."""

    def send_confirmation(self, order: Order) -> None:
        print(
            f"[Notification] Confirmation sent for {order.order_id} "
            f"to customer {order.customer_id}."
        )


# Application layer

class LayeredOrderService:
    """Application service coordinating the layered use case."""

    def __init__(
        self,
        repository: InMemoryOrderRepository,
        notification_service: ConsoleNotificationService,
    ) -> None:
        self.repository = repository
        self.notification_service = notification_service

    def create_order(
        self,
        customer_id: str,
        requested_items: List[tuple[str, int, float]],
    ) -> Order:
        if not customer_id.strip():
            raise OrderValidationError("Customer ID is required.")

        items = [
            OrderItem(
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price,
            )
            for product_id, quantity, unit_price in requested_items
        ]

        validate_order_items(items)

        order = Order(
            order_id=f"ORD-{uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            items=items,
        )

        order.mark_confirmed()
        self.repository.save(order)
        self.notification_service.send_confirmation(order)
        return order


# Presentation layer

def layered_controller(
    service: LayeredOrderService,
    customer_id: str,
    requested_items: List[tuple[str, int, float]],
) -> None:
    try:
        order = service.create_order(customer_id, requested_items)
        print(
            f"[Layered Presentation] {order.order_id}: "
            f"{order.status}, total={order.total:.2f}"
        )
    except OrderValidationError as exc:
        print(f"[Layered Presentation] Validation error: {exc}")


# ============================================================
# MVC ARCHITECTURE
# ============================================================
#
# Model:
#   Represents application/domain state.
#
# Controller:
#   Interprets an incoming action and updates the model.
#
# View:
#   Converts model state into a user-facing representation.
#
# MVC is particularly useful where the main architectural
# concern is separating input handling, state, and presentation.
# The controller should not become a second domain model. Business
# invariants remain inside the model/domain objects.
# ============================================================


class OrderModel:
    """MVC model containing order state and domain behavior."""

    def __init__(self) -> None:
        self.orders: Dict[str, Order] = {}

    def create_order(
        self,
        customer_id: str,
        items: List[OrderItem],
    ) -> Order:
        if not customer_id.strip():
            raise OrderValidationError("Customer ID is required.")

        validate_order_items(items)

        order = Order(
            order_id=f"MVC-{uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            items=items,
        )
        order.mark_confirmed()
        self.orders[order.order_id] = order
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)


class OrderView:
    """MVC view. It knows how to render, not how to apply business rules."""

    @staticmethod
    def render_order(order: Optional[Order]) -> str:
        if order is None:
            return "Order not found."

        lines = [
            f"Order: {order.order_id}",
            f"Customer: {order.customer_id}",
            f"Status: {order.status}",
            f"Total: {order.total:.2f}",
        ]

        for item in order.items:
            lines.append(
                f"  {item.product_id}: "
                f"{item.quantity} x {item.unit_price:.2f} = {item.subtotal:.2f}"
            )

        return "\n".join(lines)

    @staticmethod
    def render_error(message: str) -> str:
        return f"Order error: {message}"


class OrderController:
    """MVC controller translating input into model operations."""

    def __init__(self, model: OrderModel, view: OrderView) -> None:
        self.model = model
        self.view = view

    def create_order(
        self,
        customer_id: str,
        requested_items: List[tuple[str, int, float]],
    ) -> str:
        try:
            items = [
                OrderItem(product_id, quantity, unit_price)
                for product_id, quantity, unit_price in requested_items
            ]
            order = self.model.create_order(customer_id, items)
            return self.view.render_order(order)
        except OrderValidationError as exc:
            return self.view.render_error(str(exc))


# ============================================================
# HEXAGONAL ARCHITECTURE
# ============================================================
#
# Hexagonal architecture, also called Ports and Adapters, places
# the application/domain core at the center.
#
# The core declares what it needs through ports. Adapters implement
# those ports for databases, HTTP, messaging, files, or other
# technologies.
#
# Dependency direction:
#
#     Database Adapter ---> Repository Port
#     HTTP Adapter -------> Application Core
#                              ^
#                              |
#                        Domain rules
#
# The core does not import or instantiate a database technology.
# This makes the business logic testable without infrastructure.
# ============================================================


class OrderRepositoryPort(Protocol):
    def save(self, order: Order) -> None:
        ...

    def find_by_id(self, order_id: str) -> Optional[Order]:
        ...


class NotificationPort(Protocol):
    def send_confirmation(self, order: Order) -> None:
        ...


class HexagonalOrderApplication:
    """Application core depending only on ports."""

    def __init__(
        self,
        repository: OrderRepositoryPort,
        notification: NotificationPort,
    ) -> None:
        self.repository = repository
        self.notification = notification

    def place_order(
        self,
        customer_id: str,
        requested_items: List[tuple[str, int, float]],
    ) -> Order:
        items = [
            OrderItem(product_id, quantity, unit_price)
            for product_id, quantity, unit_price in requested_items
        ]

        validate_order_items(items)

        order = Order(
            order_id=f"HEX-{uuid4().hex[:8].upper()}",
            customer_id=customer_id,
            items=items,
        )
        order.mark_confirmed()

        self.repository.save(order)
        self.notification.send_confirmation(order)
        return order


# Primary adapter

class MemoryOrderRepositoryAdapter:
    """A primary adapter implementing the repository output port."""

    def __init__(self) -> None:
        self.orders: Dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self.orders[order.order_id] = order

    def find_by_id(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)


class ConsoleNotificationAdapter:
    """A secondary adapter for notification delivery."""

    def __init__(self) -> None:
        self.messages: List[str] = []

    def send_confirmation(self, order: Order) -> None:
        message = f"Order {order.order_id} confirmed for {order.customer_id}"
        self.messages.append(message)
        print(f"[Hexagonal Adapter] {message}")


# An alternative adapter demonstrates that the core is not coupled
# to the console implementation.

class RecordingNotificationAdapter:
    def __init__(self) -> None:
        self.confirmed_order_ids: List[str] = []

    def send_confirmation(self, order: Order) -> None:
        self.confirmed_order_ids.append(order.order_id)


# ============================================================
# Dependency inversion demonstration
# ============================================================

class FakeOrderRepository:
    """Test adapter used without a real database."""

    def __init__(self) -> None:
        self.saved: List[Order] = []

    def save(self, order: Order) -> None:
        self.saved.append(order)

    def find_by_id(self, order_id: str) -> Optional[Order]:
        return next(
            (order for order in self.saved if order.order_id == order_id),
            None,
        )


def test_hexagonal_core_without_infrastructure() -> None:
    repository = FakeOrderRepository()
    notification = RecordingNotificationAdapter()
    application = HexagonalOrderApplication(repository, notification)

    order = application.place_order(
        "CUST-TEST",
        [
            ("LAPTOP", 2, 850.00),
            ("DOCK", 1, 120.00),
        ],
    )

    assert order.total == 1820.00
    assert repository.saved[0].order_id == order.order_id
    assert notification.confirmed_order_ids == [order.order_id]


# ============================================================
# Architecture comparison through one execution
# ============================================================

def demonstrate_architectures() -> None:
    print("\n=== Layered Architecture ===")
    layered_repository = InMemoryOrderRepository()
    layered_notifications = ConsoleNotificationService()
    layered_service = LayeredOrderService(
        layered_repository,
        layered_notifications,
    )

    layered_controller(
        layered_service,
        "CUST-100",
        [
            ("KEYBOARD", 2, 75.00),
            ("MOUSE", 1, 40.00),
        ],
    )

    print("\n=== MVC Architecture ===")
    mvc_model = OrderModel()
    mvc_view = OrderView()
    mvc_controller = OrderController(mvc_model, mvc_view)

    print(
        mvc_controller.create_order(
            "CUST-200",
            [
                ("MONITOR", 1, 300.00),
                ("CABLE", 3, 12.50),
            ],
        )
    )

    print("\n=== Hexagonal Architecture ===")
    repository_adapter = MemoryOrderRepositoryAdapter()
    notification_adapter = ConsoleNotificationAdapter()
    hexagonal_application = HexagonalOrderApplication(
        repository_adapter,
        notification_adapter,
    )

    order = hexagonal_application.place_order(
        "CUST-300",
        [
            ("SERVER", 1, 1500.00),
            ("SSD", 2, 180.00),
        ],
    )

    print(
        f"[Hexagonal Driving Adapter] "
        f"{order.order_id} total={order.total:.2f}"
    )

    print("\n=== Invalid State Demonstration ===")
    try:
        hexagonal_application.place_order(
            "CUST-400",
            [("INVALID", 0, 100.00)],
        )
    except OrderValidationError as exc:
        print(f"Rejected invalid order: {exc}")

    print("\n=== Architecture Testability ===")
    test_hexagonal_core_without_infrastructure()
    print("Hexagonal application core test passed.")


# ============================================================
# Production-oriented design notes encoded as executable checks
# ============================================================

def demonstrate_boundary_rules() -> None:
    print("\n=== Boundary Rules ===")

    valid_item = OrderItem("BOOK", 1, 25.00)
    validate_order_items([valid_item])
    print("Valid domain data accepted.")

    for invalid_items in (
        [],
        [OrderItem("BOOK", 0, 25.00)],
        [OrderItem("BOOK", 1, -10.00)],
    ):
        try:
            validate_order_items(invalid_items)
        except OrderValidationError as exc:
            print(f"Invalid domain data rejected: {exc}")

    order = Order(
        order_id="STATE-1",
        customer_id="CUST-STATE",
        items=[valid_item],
    )
    order.mark_confirmed()

    try:
        order.mark_confirmed()
    except ValueError as exc:
        print(f"Invalid state transition rejected: {exc}")


def main() -> None:
    demonstrate_architectures()
    demonstrate_boundary_rules()

    print("\n=== Architectural Interpretation ===")
    print(
        "Layered architecture emphasizes vertical separation of responsibilities."
    )
    print(
        "MVC emphasizes coordination among input handling, application state, "
        "and presentation."
    )
    print(
        "Hexagonal architecture emphasizes an isolated core and explicit "
        "ports implemented by replaceable adapters."
    )


if __name__ == "__main__":
    main()
