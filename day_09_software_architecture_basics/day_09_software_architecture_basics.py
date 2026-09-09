"""
Software Architecture Basics
=============================

A self-contained study script covering:
- Architecture vs. design
- Architectural thinking and quality attributes
- Components, responsibilities, interfaces, and dependencies
- Boundaries and separation of concerns
- Layered architecture
- Modular architecture
- Monoliths and distributed systems
- Coupling and cohesion
- Dependency direction
- Dependency inversion
- Ports and adapters
- Architectural constraints
- Data ownership and transactional boundaries
- Synchronous and asynchronous communication
- Failure boundaries
- Security boundaries
- Architecture decision records
- Architecture fitness functions
- Testing architectural rules
- Performance, scalability, reliability, maintainability, and security
- A progressively evolved order-processing example
- Common architectural mistakes and trade-offs

The examples use only the Python standard library.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Protocol, Sequence
from uuid import uuid4
import asyncio
import time


# ============================================================================
# 1. ARCHITECTURE AND DESIGN: THE FUNDAMENTAL DISTINCTION
# ============================================================================

def architecture_vs_design() -> None:
    """
    Architecture is primarily about important structural decisions and
    constraints that shape a system as a whole.

    Design is primarily about how individual parts are organized and
    implemented inside those architectural boundaries.

    Example:
        Architecture:
            "Orders are isolated from payment infrastructure through a port."

        Design:
            "The payment adapter will expose a charge() method and map the
             external provider's response into PaymentResult."

    The distinction is not absolute. Architecture and design exist on a
    continuum, and a design decision becomes architectural when changing it
    has a large system-wide impact.
    """

    architectural_decisions = [
        "Orders and payments have separate responsibilities.",
        "The application depends on a payment abstraction rather than a vendor.",
        "Persistent data access is isolated behind a repository boundary.",
        "External services are accessed through adapters.",
    ]

    design_decisions = [
        "Use dataclasses for immutable value-like records.",
        "Name the payment operation charge().",
        "Represent money using integer cents rather than floating-point dollars.",
        "Use a dictionary as an in-memory repository.",
    ]

    print("\nARCHITECTURE VS DESIGN")
    print("Architectural decisions:")
    for decision in architectural_decisions:
        print(f"  - {decision}")

    print("Design decisions:")
    for decision in design_decisions:
        print(f"  - {decision}")


# ============================================================================
# 2. ARCHITECTURAL VOCABULARY
# ============================================================================

@dataclass(frozen=True)
class Component:
    """
    A component is a cohesive unit with a defined responsibility.

    A component can be:
    - a Python module,
    - a package,
    - a service,
    - a database subsystem,
    - a library,
    - or another independently meaningful architectural unit.

    The word "component" is contextual. The important properties are
    responsibility, boundary, interface, and dependency relationships.
    """

    name: str
    responsibility: str


@dataclass(frozen=True)
class Boundary:
    """
    A boundary defines where one responsibility, model, ownership area,
    technology, or trust level ends and another begins.
    """

    name: str
    purpose: str


def architecture_terminology() -> None:
    components = [
        Component("Order Service", "Validate and create orders"),
        Component("Payment Adapter", "Translate application payment requests"),
        Component("Repository", "Persist and retrieve orders"),
        Component("Notification Adapter", "Communicate with an external messaging system"),
    ]

    boundaries = [
        Boundary("Domain boundary", "Protect business rules from infrastructure"),
        Boundary("Module boundary", "Control which code can depend on which code"),
        Boundary("Data boundary", "Define ownership and access to persistent state"),
        Boundary("Security boundary", "Separate trusted and untrusted operations"),
    ]

    print("\nARCHITECTURAL VOCABULARY")
    for component in components:
        print(f"Component: {component.name} -> {component.responsibility}")

    for boundary in boundaries:
        print(f"Boundary: {boundary.name} -> {boundary.purpose}")


# ============================================================================
# 3. QUALITY ATTRIBUTES
# ============================================================================

@dataclass(frozen=True)
class QualityAttribute:
    name: str
    meaning: str
    architectural_implication: str


QUALITY_ATTRIBUTES = (
    QualityAttribute(
        "Maintainability",
        "How easily the system can be understood and changed.",
        "Use clear boundaries, cohesive components, and controlled dependencies.",
    ),
    QualityAttribute(
        "Scalability",
        "How well capacity can grow as workload increases.",
        "Identify bottlenecks and allow independently scalable components where justified.",
    ),
    QualityAttribute(
        "Reliability",
        "The ability to perform correctly over time.",
        "Control failure propagation and design explicit recovery behavior.",
    ),
    QualityAttribute(
        "Availability",
        "The proportion of time the system is operational.",
        "Avoid unnecessary single points of failure and use suitable redundancy.",
    ),
    QualityAttribute(
        "Performance",
        "How efficiently and quickly the system responds.",
        "Control expensive dependencies, latency, computation, and data access.",
    ),
    QualityAttribute(
        "Security",
        "Protection against unauthorized access and misuse.",
        "Define trust boundaries, minimize privileges, and validate untrusted input.",
    ),
    QualityAttribute(
        "Testability",
        "How easily behavior can be verified.",
        "Separate policy from infrastructure and inject dependencies.",
    ),
)


def demonstrate_quality_attributes() -> None:
    print("\nQUALITY ATTRIBUTES")
    for attribute in QUALITY_ATTRIBUTES:
        print(f"\n{attribute.name}")
        print(f"  Meaning: {attribute.meaning}")
        print(f"  Architectural implication: {attribute.architectural_implication}")


# ============================================================================
# 4. COHESION AND COUPLING
# ============================================================================

def calculate_dependency_density(
    component_count: int,
    dependency_count: int,
) -> float:
    """
    A simple educational metric.

    This is not a universal architecture-quality formula. It illustrates the
    idea that excessive dependencies can increase structural complexity.
    """
    if component_count <= 1:
        return 0.0

    possible_directed_dependencies = component_count * (component_count - 1)
    return dependency_count / possible_directed_dependencies


def cohesion_and_coupling() -> None:
    """
    Cohesion asks:
        "Do the responsibilities inside this component belong together?"

    Coupling asks:
        "How strongly does this component depend on other components?"

    Good architecture generally seeks:
        High cohesion + controlled coupling.

    Example of poor cohesion:
        UserService handles authentication, PDF generation, payments,
        email, analytics, and database migrations.

    Example of stronger cohesion:
        Authentication, payment, document generation, and analytics have
        distinct responsibilities.
    """

    components = 5
    dependencies = 7
    density = calculate_dependency_density(components, dependencies)

    print("\nCOHESION AND COUPLING")
    print("Component count:", components)
    print("Dependency count:", dependencies)
    print(f"Educational dependency density: {density:.3f}")
    print("Interpretation: lower dependency density can indicate fewer structural links,")
    print("but dependency count alone cannot determine architecture quality.")


# ============================================================================
# 5. BASIC DEPENDENCY GRAPH
# ============================================================================

@dataclass
class DependencyGraph:
    """
    A small directed graph representing component dependencies.

    A dependency A -> B means A knows about or relies upon B.
    """

    edges: dict[str, set[str]] = field(default_factory=dict)

    def add_component(self, component: str) -> None:
        self.edges.setdefault(component, set())

    def add_dependency(self, source: str, target: str) -> None:
        self.add_component(source)
        self.add_component(target)
        self.edges[source].add(target)

    def dependencies_of(self, component: str) -> set[str]:
        return set(self.edges.get(component, set()))

    def reverse_dependencies_of(self, component: str) -> set[str]:
        return {
            source
            for source, targets in self.edges.items()
            if component in targets
        }

    def has_cycle(self) -> bool:
        """
        Detect cycles using depth-first search.

        Cycles can make changes harder because components become mutually
        constrained.
        """
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False

            visiting.add(node)

            for dependency in self.edges.get(node, set()):
                if visit(dependency):
                    return True

            visiting.remove(node)
            visited.add(node)
            return False

        return any(visit(node) for node in self.edges)

    def print_graph(self) -> None:
        for source, targets in self.edges.items():
            target_text = ", ".join(sorted(targets)) or "(none)"
            print(f"  {source} -> {target_text}")


def dependency_graph_example() -> None:
    graph = DependencyGraph()

    graph.add_dependency("OrderApplication", "OrderDomain")
    graph.add_dependency("OrderApplication", "OrderRepositoryPort")
    graph.add_dependency("SqlOrderRepository", "Database")
    graph.add_dependency("PaymentAdapter", "PaymentProvider")
    graph.add_dependency("OrderApplication", "PaymentPort")

    print("\nDEPENDENCY GRAPH")
    graph.print_graph()
    print("Contains cycle:", graph.has_cycle())


# ============================================================================
# 6. A SIMPLE LAYERED ARCHITECTURE
# ============================================================================

@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    price_cents: int


@dataclass(frozen=True)
class OrderLine:
    product_id: str
    quantity: int
    unit_price_cents: int

    @property
    def subtotal_cents(self) -> int:
        return self.quantity * self.unit_price_cents


@dataclass
class Order:
    order_id: str
    customer_id: str
    lines: list[OrderLine]
    status: str = "PENDING"

    @property
    def total_cents(self) -> int:
        return sum(line.subtotal_cents for line in self.lines)


class ProductCatalog:
    """
    Data-access-like component in a simple layered design.
    """

    def __init__(self, products: Iterable[Product]) -> None:
        self._products = {product.product_id: product for product in products}

    def get(self, product_id: str) -> Product:
        try:
            return self._products[product_id]
        except KeyError as exc:
            raise ValueError(f"Unknown product: {product_id}") from exc


class OrderService:
    """
    Application/service layer.

    In a simple layered architecture, this class can coordinate domain
    behavior, data access, and other infrastructure directly.

    This approach is easy to understand but becomes problematic when the
    application layer becomes tightly coupled to specific infrastructure.
    """

    def __init__(self, catalog: ProductCatalog) -> None:
        self.catalog = catalog
        self.orders: dict[str, Order] = {}

    def create_order(
        self,
        customer_id: str,
        requested_lines: Sequence[tuple[str, int]],
    ) -> Order:
        if not customer_id.strip():
            raise ValueError("customer_id cannot be empty")

        if not requested_lines:
            raise ValueError("An order must contain at least one line")

        lines: list[OrderLine] = []

        for product_id, quantity in requested_lines:
            if quantity <= 0:
                raise ValueError("Quantity must be positive")

            product = self.catalog.get(product_id)

            lines.append(
                OrderLine(
                    product_id=product.product_id,
                    quantity=quantity,
                    unit_price_cents=product.price_cents,
                )
            )

        order = Order(
            order_id=str(uuid4()),
            customer_id=customer_id,
            lines=lines,
        )

        self.orders[order.order_id] = order
        return order


def layered_architecture_example() -> None:
    catalog = ProductCatalog(
        [
            Product("P100", "Keyboard", 5000),
            Product("P200", "Mouse", 2500),
        ]
    )

    service = OrderService(catalog)

    order = service.create_order(
        "customer-1",
        [
            ("P100", 2),
            ("P200", 1),
        ],
    )

    print("\nLAYERED ARCHITECTURE")
    print("Order:", order.order_id)
    print("Total cents:", order.total_cents)


# ============================================================================
# 7. MODULE BOUNDARIES
# ============================================================================

class BoundaryViolation(Exception):
    """Raised when an example intentionally violates a boundary."""


class ArchitectureBoundary:
    """
    A runtime illustration of an architectural rule.

    Real architectural boundaries are often enforced through:
    - package structure,
    - dependency rules,
    - code review,
    - static analysis,
    - module visibility,
    - API contracts,
    - deployment boundaries,
    - network controls.
    """

    def __init__(self, allowed_dependencies: dict[str, set[str]]) -> None:
        self.allowed_dependencies = allowed_dependencies

    def check(self, source: str, target: str) -> None:
        allowed = self.allowed_dependencies.get(source, set())

        if target not in allowed:
            raise BoundaryViolation(
                f"{source} is not allowed to depend directly on {target}"
            )


def boundary_example() -> None:
    boundary = ArchitectureBoundary(
        {
            "OrderDomain": set(),
            "OrderApplication": {"OrderDomain", "OrderRepositoryPort", "PaymentPort"},
            "Infrastructure": {"OrderRepositoryPort", "PaymentPort"},
        }
    )

    print("\nBOUNDARIES")

    boundary.check("OrderApplication", "OrderDomain")
    print("Allowed: OrderApplication -> OrderDomain")

    try:
        boundary.check("OrderDomain", "Database")
    except BoundaryViolation as exc:
        print("Rejected:", exc)


# ============================================================================
# 8. DEPENDENCY INVERSION
# ============================================================================

class OrderRepositoryPort(Protocol):
    """
    A port describes what the application needs rather than how infrastructure
    provides it.

    The application depends on this abstraction.
    """

    def save(self, order: Order) -> None:
        ...

    def get(self, order_id: str) -> Order | None:
        ...


class PaymentPort(Protocol):
    """Application-facing payment abstraction."""

    def charge(self, customer_id: str, amount_cents: int) -> bool:
        ...


class InMemoryOrderRepository:
    """Infrastructure implementation of the repository port."""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.order_id] = order

    def get(self, order_id: str) -> Order | None:
        return self._orders.get(order_id)


class FakePaymentGateway:
    """Test-friendly payment implementation."""

    def __init__(self, should_succeed: bool = True) -> None:
        self.should_succeed = should_succeed
        self.calls: list[tuple[str, int]] = []

    def charge(self, customer_id: str, amount_cents: int) -> bool:
        self.calls.append((customer_id, amount_cents))
        return self.should_succeed


class PaymentProviderAdapter:
    """
    Adapter around an external provider.

    The application does not need to know provider-specific request formats.
    """

    def __init__(self, provider: Callable[[str, int], bool]) -> None:
        self.provider = provider

    def charge(self, customer_id: str, amount_cents: int) -> bool:
        return self.provider(customer_id, amount_cents)


class OrderApplicationService:
    """
    Application layer using dependency inversion.

    The service receives abstractions rather than constructing concrete
    infrastructure itself.
    """

    def __init__(
        self,
        repository: OrderRepositoryPort,
        payment: PaymentPort,
    ) -> None:
        self.repository = repository
        self.payment = payment

    def place_order(self, order: Order) -> Order:
        if not order.lines:
            raise ValueError("Cannot place an empty order")

        if order.total_cents <= 0:
            raise ValueError("Order total must be positive")

        if not self.payment.charge(order.customer_id, order.total_cents):
            raise RuntimeError("Payment was declined")

        order.status = "PAID"
        self.repository.save(order)
        return order


def dependency_inversion_example() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway()

    application = OrderApplicationService(repository, payment)

    order = Order(
        order_id="ORD-100",
        customer_id="C-100",
        lines=[
            OrderLine(
                product_id="P100",
                quantity=2,
                unit_price_cents=5000,
            )
        ],
    )

    placed = application.place_order(order)

    print("\nDEPENDENCY INVERSION")
    print("Status:", placed.status)
    print("Payment calls:", payment.calls)
    print("Persisted:", repository.get("ORD-100") is not None)


# ============================================================================
# 9. DOMAIN, APPLICATION, AND INFRASTRUCTURE RESPONSIBILITIES
# ============================================================================

class OrderDomain:
    """
    Domain object responsible for business invariants.

    The domain should not need to know about HTTP, SQL, cloud SDKs, queues,
    frameworks, or specific infrastructure providers.
    """

    VALID_STATUSES = {"PENDING", "PAID", "CANCELLED"}

    def __init__(
        self,
        order_id: str,
        customer_id: str,
        lines: Sequence[OrderLine],
    ) -> None:
        if not order_id:
            raise ValueError("order_id is required")
        if not customer_id:
            raise ValueError("customer_id is required")
        if not lines:
            raise ValueError("At least one line is required")

        for line in lines:
            if line.quantity <= 0:
                raise ValueError("Quantity must be positive")
            if line.unit_price_cents < 0:
                raise ValueError("Unit price cannot be negative")

        self.order_id = order_id
        self.customer_id = customer_id
        self.lines = list(lines)
        self.status = "PENDING"

    @property
    def total_cents(self) -> int:
        return sum(line.subtotal_cents for line in self.lines)

    def mark_paid(self) -> None:
        if self.status != "PENDING":
            raise ValueError(
                f"Cannot mark order as paid from {self.status} state"
            )

        self.status = "PAID"

    def cancel(self) -> None:
        if self.status == "PAID":
            raise ValueError("A paid order cannot be cancelled directly")

        if self.status == "CANCELLED":
            raise ValueError("Order is already cancelled")

        self.status = "CANCELLED"


def domain_boundary_example() -> None:
    order = OrderDomain(
        order_id="ORD-200",
        customer_id="C-200",
        lines=[
            OrderLine("P100", 1, 5000),
        ],
    )

    print("\nDOMAIN BOUNDARY")
    print("Initial status:", order.status)

    order.mark_paid()
    print("After payment:", order.status)

    try:
        order.cancel()
    except ValueError as exc:
        print("Invalid transition rejected:", exc)


# ============================================================================
# 10. HEXAGONAL / PORTS AND ADAPTERS ARCHITECTURE
# ============================================================================

class NotificationPort(Protocol):
    def send(self, recipient: str, message: str) -> None:
        ...


class ConsoleNotificationAdapter:
    def send(self, recipient: str, message: str) -> None:
        print(f"Notification to {recipient}: {message}")


class OrderEventPublisher(Protocol):
    def publish(self, event_name: str, payload: dict[str, object]) -> None:
        ...


class InMemoryEventPublisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def publish(self, event_name: str, payload: dict[str, object]) -> None:
        self.events.append((event_name, payload))


class CheckoutApplication:
    """
    A ports-and-adapters example.

    The central application depends on ports.
    Adapters implement those ports.

    The architecture protects the core from technology-specific details.
    """

    def __init__(
        self,
        payment: PaymentPort,
        repository: OrderRepositoryPort,
        notification: NotificationPort,
        events: OrderEventPublisher,
    ) -> None:
        self.payment = payment
        self.repository = repository
        self.notification = notification
        self.events = events

    def checkout(self, order: OrderDomain) -> OrderDomain:
        if not self.payment.charge(order.customer_id, order.total_cents):
            raise RuntimeError("Payment failed")

        order.mark_paid()

        persistence_model = Order(
            order_id=order.order_id,
            customer_id=order.customer_id,
            lines=order.lines,
            status=order.status,
        )

        self.repository.save(persistence_model)

        self.events.publish(
            "OrderPaid",
            {
                "order_id": order.order_id,
                "amount_cents": order.total_cents,
            },
        )

        self.notification.send(
            order.customer_id,
            f"Order {order.order_id} was paid successfully.",
        )

        return order


def ports_and_adapters_example() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway()
    notification = ConsoleNotificationAdapter()
    events = InMemoryEventPublisher()

    application = CheckoutApplication(
        payment=payment,
        repository=repository,
        notification=notification,
        events=events,
    )

    order = OrderDomain(
        "ORD-300",
        "C-300",
        [OrderLine("P100", 1, 5000)],
    )

    application.checkout(order)

    print("\nPORTS AND ADAPTERS")
    print("Domain status:", order.status)
    print("Published events:", events.events)


# ============================================================================
# 11. ARCHITECTURE STYLES
# ============================================================================

def architecture_styles() -> None:
    styles = {
        "Layered": "Organizes software into layers with defined responsibilities.",
        "Modular monolith": "One deployable unit with strong internal module boundaries.",
        "Microservices": "Multiple independently deployable services communicating over boundaries.",
        "Event-driven": "Components communicate through events and asynchronous processing.",
        "Hexagonal": "Core application isolated from infrastructure through ports and adapters.",
        "Clean architecture": "Dependency direction points toward policy and business rules.",
        "Client-server": "Clients consume capabilities exposed by a server.",
    }

    print("\nARCHITECTURE STYLES")
    for style, description in styles.items():
        print(f"{style}: {description}")


# ============================================================================
# 12. MONOLITH VS MODULAR MONOLITH VS MICROSERVICES
# ============================================================================

def compare_deployment_styles() -> None:
    comparison = [
        (
            "Traditional monolith",
            "Single deployment",
            "Usually simple",
            "Can become tightly coupled",
        ),
        (
            "Modular monolith",
            "Single deployment",
            "Moderate",
            "Requires discipline around boundaries",
        ),
        (
            "Microservices",
            "Multiple deployments",
            "Operationally complex",
            "Independent scaling and deployment are possible",
        ),
    ]

    print("\nDEPLOYMENT STYLE COMPARISON")
    print(
        f"{'Style':<24} {'Deployment':<20} "
        f"{'Operational complexity':<24} {'Important trade-off'}"
    )

    for style, deployment, complexity, tradeoff in comparison:
        print(
            f"{style:<24} {deployment:<20} "
            f"{complexity:<24} {tradeoff}"
        )

    print(
        "\nArchitectural lesson: distributed deployment is not automatically "
        "better architecture. It introduces network, operational, consistency, "
        "observability, and failure costs."
    )


# ============================================================================
# 13. DISTRIBUTED SYSTEM BOUNDARIES
# ============================================================================

@dataclass(frozen=True)
class Service:
    name: str
    owns_data: set[str]


def distributed_boundary_example() -> None:
    """
    In distributed architecture, a service boundary is stronger than a Python
    module boundary.

    A network call can fail independently.
    Latency becomes variable.
    Serialization is required.
    Partial failure becomes possible.
    Data consistency becomes an architectural concern.
    """

    order_service = Service("OrderService", {"orders"})
    payment_service = Service("PaymentService", {"payments"})

    print("\nDISTRIBUTED SYSTEM BOUNDARIES")
    print(f"{order_service.name} owns: {sorted(order_service.owns_data)}")
    print(f"{payment_service.name} owns: {sorted(payment_service.owns_data)}")
    print(
        "Cross-service access should generally happen through an explicit API "
        "or event contract rather than direct database coupling."
    )


# ============================================================================
# 14. SYNCHRONOUS VS ASYNCHRONOUS COMMUNICATION
# ============================================================================

async def simulated_external_call(name: str, delay: float) -> str:
    await asyncio.sleep(delay)
    return f"{name} completed"


async def asynchronous_example() -> None:
    start = time.perf_counter()

    results = await asyncio.gather(
        simulated_external_call("Payment lookup", 0.20),
        simulated_external_call("Inventory lookup", 0.20),
        simulated_external_call("Customer lookup", 0.20),
    )

    elapsed = time.perf_counter() - start

    print("\nASYNCHRONOUS COMMUNICATION")
    print("Results:", results)
    print(f"Elapsed time: approximately {elapsed:.2f} seconds")
    print(
        "The example demonstrates concurrency for independent I/O-like work. "
        "Async execution does not automatically make CPU-bound work faster."
    )


def synchronous_vs_asynchronous() -> None:
    """
    Synchronous:
        Caller waits for a response.

    Asynchronous:
        Work can be accepted and processed separately.

    Synchronous communication is often easier to reason about.
    Asynchronous communication can improve decoupling and throughput but
    introduces eventual consistency, retries, duplicate delivery, ordering,
    observability, and failure-handling concerns.
    """

    print("\nSYNCHRONOUS VS ASYNCHRONOUS")
    print("Synchronous: request -> wait -> response")
    print("Asynchronous: request -> accepted -> process later")


# ============================================================================
# 15. FAILURE BOUNDARIES
# ============================================================================

class PaymentUnavailable(Exception):
    pass


class ResilientPaymentPort:
    """
    Educational retry wrapper.

    Real retry policy should account for:
    - idempotency,
    - error classification,
    - exponential backoff,
    - jitter,
    - maximum attempts,
    - time budgets,
    - provider limits.
    """

    def __init__(
        self,
        operation: Callable[[str, int], bool],
        max_attempts: int = 3,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")

        self.operation = operation
        self.max_attempts = max_attempts

    def charge(self, customer_id: str, amount_cents: int) -> bool:
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                return self.operation(customer_id, amount_cents)
            except PaymentUnavailable as exc:
                last_error = exc

                # The example does not sleep so the study script remains fast.
                print(f"Payment attempt {attempt} failed")

        raise PaymentUnavailable("Payment remained unavailable") from last_error


def failure_boundary_example() -> None:
    attempts = {"count": 0}

    def unreliable_provider(customer_id: str, amount_cents: int) -> bool:
        attempts["count"] += 1

        if attempts["count"] < 3:
            raise PaymentUnavailable("Temporary provider failure")

        return True

    payment = ResilientPaymentPort(unreliable_provider, max_attempts=3)

    result = payment.charge("C-400", 1000)

    print("\nFAILURE BOUNDARIES")
    print("Final payment result:", result)


# ============================================================================
# 16. IDEMPOTENCY
# ============================================================================

class IdempotentPaymentService:
    """
    An idempotency key allows a retrying client to avoid unintentionally
    performing the same logical operation multiple times.
    """

    def __init__(self) -> None:
        self.completed: dict[str, bool] = {}

    def charge(
        self,
        idempotency_key: str,
        customer_id: str,
        amount_cents: int,
    ) -> bool:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")

        if idempotency_key in self.completed:
            return self.completed[idempotency_key]

        # Simulate a successful payment.
        result = amount_cents > 0
        self.completed[idempotency_key] = result
        return result


def idempotency_example() -> None:
    payment = IdempotentPaymentService()

    first = payment.charge("payment-001", "C-500", 5000)
    second = payment.charge("payment-001", "C-500", 5000)

    print("\nIDEMPOTENCY")
    print("First result:", first)
    print("Repeated request result:", second)
    print("Stored operation count:", len(payment.completed))


# ============================================================================
# 17. DATA OWNERSHIP AND TRANSACTION BOUNDARIES
# ============================================================================

@dataclass
class Inventory:
    product_id: str
    available_quantity: int


class InventoryService:
    """
    Inventory owns its own invariant.

    The service should be the authority for changes to inventory rather than
    allowing unrelated components to modify its internal state arbitrarily.
    """

    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory

    def reserve(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if quantity > self.inventory.available_quantity:
            raise RuntimeError("Insufficient inventory")

        self.inventory.available_quantity -= quantity


def transaction_boundary_example() -> None:
    inventory = Inventory("P100", 10)
    service = InventoryService(inventory)

    service.reserve(3)

    print("\nDATA OWNERSHIP AND TRANSACTION BOUNDARIES")
    print("Remaining inventory:", inventory.available_quantity)
    print(
        "The inventory component owns the rule that reservations cannot "
        "exceed available quantity."
    )


# ============================================================================
# 18. BOUNDED CONTEXTS AND MODEL BOUNDARIES
# ============================================================================

@dataclass(frozen=True)
class SalesCustomer:
    """
    Sales context representation.

    A customer may be modeled differently in another context.
    """

    customer_id: str
    name: str
    credit_limit_cents: int


@dataclass(frozen=True)
class SupportCustomer:
    """
    Support context representation.

    The same real-world person does not require one universal object model.
    """

    customer_id: str
    display_name: str
    open_ticket_count: int


def bounded_context_example() -> None:
    sales_customer = SalesCustomer(
        customer_id="C-600",
        name="Asha",
        credit_limit_cents=100_000,
    )

    support_customer = SupportCustomer(
        customer_id="C-600",
        display_name="Asha",
        open_ticket_count=2,
    )

    print("\nMODEL BOUNDARIES")
    print("Sales representation:", sales_customer)
    print("Support representation:", support_customer)
    print(
        "Both use the same identity but serve different business purposes."
    )


# ============================================================================
# 19. API BOUNDARIES AND CONTRACTS
# ============================================================================

@dataclass(frozen=True)
class CreateOrderRequest:
    customer_id: str
    items: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class CreateOrderResponse:
    order_id: str
    total_cents: int
    status: str


def validate_create_order_request(
    request: CreateOrderRequest,
) -> None:
    """
    Boundary validation belongs near the boundary.

    Internal domain code should still enforce its own invariants because
    external validation is not sufficient protection.
    """
    if not request.customer_id.strip():
        raise ValueError("customer_id is required")

    if not request.items:
        raise ValueError("At least one item is required")

    for product_id, quantity in request.items:
        if not product_id:
            raise ValueError("product_id is required")
        if quantity <= 0:
            raise ValueError("quantity must be positive")


def api_boundary_example() -> None:
    request = CreateOrderRequest(
        customer_id="C-700",
        items=(("P100", 2),),
    )

    validate_create_order_request(request)

    response = CreateOrderResponse(
        order_id="ORD-700",
        total_cents=10_000,
        status="PENDING",
    )

    print("\nAPI BOUNDARY")
    print("Validated request:", request)
    print("Response contract:", response)


# ============================================================================
# 20. SECURITY BOUNDARIES
# ============================================================================

@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    roles: frozenset[str]


def require_role(
    user: AuthenticatedUser,
    required_role: str,
) -> None:
    """
    Authorization is a policy at a security boundary.

    Never assume that hiding a UI action is equivalent to authorization.
    Server-side authorization must enforce protected operations.
    """
    if required_role not in user.roles:
        raise PermissionError(
            f"User {user.user_id} lacks required role {required_role}"
        )


def security_boundary_example() -> None:
    user = AuthenticatedUser(
        user_id="U-100",
        roles=frozenset({"customer"}),
    )

    print("\nSECURITY BOUNDARY")

    try:
        require_role(user, "admin")
    except PermissionError as exc:
        print("Access denied:", exc)

    admin = AuthenticatedUser(
        user_id="U-200",
        roles=frozenset({"customer", "admin"}),
    )

    require_role(admin, "admin")
    print("Admin operation authorized")


# ============================================================================
# 21. CONFIGURATION BOUNDARIES
# ============================================================================

@dataclass(frozen=True)
class ApplicationConfig:
    payment_timeout_seconds: float
    database_timeout_seconds: float
    max_order_items: int

    def __post_init__(self) -> None:
        if self.payment_timeout_seconds <= 0:
            raise ValueError("Payment timeout must be positive")

        if self.database_timeout_seconds <= 0:
            raise ValueError("Database timeout must be positive")

        if self.max_order_items <= 0:
            raise ValueError("max_order_items must be positive")


def configuration_boundary_example() -> None:
    config = ApplicationConfig(
        payment_timeout_seconds=2.0,
        database_timeout_seconds=1.0,
        max_order_items=100,
    )

    print("\nCONFIGURATION BOUNDARY")
    print(config)


# ============================================================================
# 22. ARCHITECTURAL DECISION RECORD
# ============================================================================

@dataclass(frozen=True)
class ArchitectureDecision:
    title: str
    context: str
    decision: str
    consequences: tuple[str, ...]


def architecture_decision_record_example() -> None:
    adr = ArchitectureDecision(
        title="Use a modular monolith initially",
        context=(
            "The product has a small engineering team and moderate traffic. "
            "Independent deployment is not yet a demonstrated requirement."
        ),
        decision=(
            "Keep one deployable application while enforcing strong internal "
            "module boundaries."
        ),
        consequences=(
            "Simpler deployment",
            "Lower operational overhead",
            "Requires discipline to preserve module boundaries",
            "Future extraction of modules may remain possible",
        ),
    )

    print("\nARCHITECTURE DECISION RECORD")
    print("Title:", adr.title)
    print("Context:", adr.context)
    print("Decision:", adr.decision)
    print("Consequences:")
    for consequence in adr.consequences:
        print(f"  - {consequence}")


# ============================================================================
# 23. FITNESS FUNCTIONS
# ============================================================================

def assert_no_forbidden_dependencies(
    graph: DependencyGraph,
    forbidden_edges: set[tuple[str, str]],
) -> None:
    """
    A fitness function is an automated test that protects an architectural
    property.

    Example rule:
        Domain must not depend on infrastructure.
    """
    violations = []

    for source, targets in graph.edges.items():
        for target in targets:
            if (source, target) in forbidden_edges:
                violations.append((source, target))

    if violations:
        formatted = ", ".join(
            f"{source}->{target}" for source, target in violations
        )
        raise AssertionError(f"Architectural violations: {formatted}")


def architecture_fitness_function_example() -> None:
    graph = DependencyGraph()
    graph.add_dependency("OrderApplication", "OrderDomain")
    graph.add_dependency("OrderApplication", "PaymentPort")
    graph.add_dependency("Infrastructure", "PaymentPort")

    forbidden = {
        ("OrderDomain", "Database"),
        ("OrderDomain", "PaymentProvider"),
    }

    assert_no_forbidden_dependencies(graph, forbidden)

    print("\nARCHITECTURE FITNESS FUNCTION")
    print("Dependency rule passed.")


# ============================================================================
# 24. TESTABILITY AS AN ARCHITECTURAL PROPERTY
# ============================================================================

def test_payment_failure() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway(should_succeed=False)
    application = OrderApplicationService(repository, payment)

    order = Order(
        order_id="ORD-TEST",
        customer_id="C-TEST",
        lines=[OrderLine("P100", 1, 1000)],
    )

    try:
        application.place_order(order)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Payment failure should have been raised")

    if repository.get("ORD-TEST") is not None:
        raise AssertionError("Failed payment should not persist the order")

    print("\nTESTABILITY")
    print("Payment failure test passed.")


def test_successful_payment() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway(should_succeed=True)
    application = OrderApplicationService(repository, payment)

    order = Order(
        order_id="ORD-TEST-2",
        customer_id="C-TEST",
        lines=[OrderLine("P100", 2, 1000)],
    )

    result = application.place_order(order)

    assert result.status == "PAID"
    assert repository.get(order.order_id) is not None
    assert payment.calls == [("C-TEST", 2000)]

    print("Successful payment test passed.")


# ============================================================================
# 25. EDGE CASES AND INVARIANT TESTING
# ============================================================================

def edge_case_examples() -> None:
    print("\nEDGE CASES")

    cases = [
        ("empty customer", lambda: OrderDomain("O1", "", [OrderLine("P1", 1, 100)])),
        ("empty lines", lambda: OrderDomain("O2", "C1", [])),
        ("zero quantity", lambda: OrderDomain("O3", "C1", [OrderLine("P1", 0, 100)])),
        ("negative price", lambda: OrderDomain("O4", "C1", [OrderLine("P1", 1, -100)])),
    ]

    for name, operation in cases:
        try:
            operation()
        except ValueError as exc:
            print(f"{name}: rejected correctly -> {exc}")
        else:
            print(f"{name}: ERROR, invalid input was accepted")


# ============================================================================
# 26. PERFORMANCE CONSIDERATIONS
# ============================================================================

def performance_considerations() -> None:
    """
    Architecture affects performance through:
    - number of network hops,
    - serialization/deserialization,
    - database round trips,
    - synchronization,
    - contention,
    - caching,
    - computation placement,
    - data locality.

    A useful principle is to measure before introducing architectural
    complexity for performance reasons.
    """

    print("\nPERFORMANCE CONSIDERATIONS")
    print("Local function call: very low latency")
    print("In-process module call: low latency")
    print("Database call: network + database processing")
    print("Remote service call: network + serialization + remote processing")
    print(
        "Caching can reduce repeated work, but introduces invalidation and "
        "staleness concerns."
    )


# ============================================================================
# 27. SCALABILITY
# ============================================================================

def scalability_example() -> None:
    """
    Vertical scaling:
        Increase resources of an existing machine.

    Horizontal scaling:
        Add more instances.

    Stateless components are generally easier to scale horizontally because
    requests do not depend on local instance-specific session state.
    """

    print("\nSCALABILITY")
    print("Vertical scaling: larger machine")
    print("Horizontal scaling: more instances")
    print(
        "Architectural constraint: shared mutable state can become a scaling "
        "bottleneck."
    )


# ============================================================================
# 28. OBSERVABILITY BOUNDARIES
# ============================================================================

@dataclass
class OperationTelemetry:
    operation: str
    duration_ms: float
    success: bool


def observe_operation(
    operation: str,
    action: Callable[[], object],
) -> OperationTelemetry:
    start = time.perf_counter()

    try:
        action()
        success = True
    except Exception:
        success = False
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000

        telemetry = OperationTelemetry(
            operation=operation,
            duration_ms=duration_ms,
            success=success,
        )

        print(
            f"Telemetry: operation={telemetry.operation}, "
            f"duration_ms={telemetry.duration_ms:.3f}, "
            f"success={telemetry.success}"
        )

    return telemetry


def observability_example() -> None:
    print("\nOBSERVABILITY BOUNDARIES")

    observe_operation(
        "calculate-order-total",
        lambda: sum([100, 200, 300]),
    )


# ============================================================================
# 29. ANTI-CORRUPTION LAYER
# ============================================================================

@dataclass(frozen=True)
class ExternalPaymentResponse:
    provider_code: str
    provider_message: str
    provider_transaction_id: str


@dataclass(frozen=True)
class PaymentResult:
    successful: bool
    transaction_id: str | None
    reason: str | None


def translate_external_payment_response(
    response: ExternalPaymentResponse,
) -> PaymentResult:
    """
    An anti-corruption layer prevents an external model from spreading
    throughout the internal domain.

    This is particularly valuable when integrating with legacy systems or
    providers whose vocabulary differs from the application's model.
    """
    if response.provider_code == "00":
        return PaymentResult(
            successful=True,
            transaction_id=response.provider_transaction_id,
            reason=None,
        )

    return PaymentResult(
        successful=False,
        transaction_id=None,
        reason=response.provider_message,
    )


def anti_corruption_layer_example() -> None:
    external = ExternalPaymentResponse(
        provider_code="00",
        provider_message="APPROVED",
        provider_transaction_id="TX-900",
    )

    internal = translate_external_payment_response(external)

    print("\nANTI-CORRUPTION LAYER")
    print("External model:", external)
    print("Internal model:", internal)


# ============================================================================
# 30. EVENT-DRIVEN ARCHITECTURE
# ============================================================================

@dataclass(frozen=True)
class DomainEvent:
    event_type: str
    aggregate_id: str
    payload: dict[str, object]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[DomainEvent], None]]] = {}

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[DomainEvent], None],
    ) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(event.event_type, []):
            handler(event)


def event_driven_example() -> None:
    bus = EventBus()
    received: list[str] = []

    def send_notification(event: DomainEvent) -> None:
        received.append(f"notification:{event.aggregate_id}")

    def update_analytics(event: DomainEvent) -> None:
        received.append(f"analytics:{event.aggregate_id}")

    bus.subscribe("OrderPaid", send_notification)
    bus.subscribe("OrderPaid", update_analytics)

    bus.publish(
        DomainEvent(
            event_type="OrderPaid",
            aggregate_id="ORD-800",
            payload={"amount_cents": 5000},
        )
    )

    print("\nEVENT-DRIVEN ARCHITECTURE")
    print("Consumers processed:", received)


# ============================================================================
# 31. EVENTUAL CONSISTENCY
# ============================================================================

def eventual_consistency_example() -> None:
    """
    With asynchronous events, one component can temporarily have newer data
    than another.

    This is not necessarily incorrect. It becomes a problem when business
    requirements demand immediate consistency.
    """

    order_state = {"status": "PAID"}
    notification_state = {"status": "PENDING"}

    print("\nEVENTUAL CONSISTENCY")
    print("Immediately after payment:")
    print("  Order state:", order_state["status"])
    print("  Notification state:", notification_state["status"])

    # Simulate asynchronous event processing.
    notification_state["status"] = "SENT"

    print("After event processing:")
    print("  Notification state:", notification_state["status"])


# ============================================================================
# 32. CAPACITY, BOTTLENECKS, AND BACKPRESSURE
# ============================================================================

class BoundedQueue:
    """
    A simple bounded queue illustrating backpressure.

    In production systems, a message broker or bounded work queue can prevent
    unlimited memory growth when producers are faster than consumers.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")

        self.capacity = capacity
        self.items: list[str] = []

    def put(self, item: str) -> None:
        if len(self.items) >= self.capacity:
            raise OverflowError("Queue capacity exceeded")

        self.items.append(item)

    def get(self) -> str:
        if not self.items:
            raise IndexError("Queue is empty")

        return self.items.pop(0)


def backpressure_example() -> None:
    queue = BoundedQueue(capacity=2)

    queue.put("job-1")
    queue.put("job-2")

    print("\nBACKPRESSURE")
    print("Queue contains:", queue.items)

    try:
        queue.put("job-3")
    except OverflowError as exc:
        print("Producer constrained:", exc)

    print("Consumer received:", queue.get())


# ============================================================================
# 33. ARCHITECTURAL TRADE-OFFS
# ============================================================================

def architectural_tradeoffs() -> None:
    tradeoffs = {
        "Abstraction": (
            "Improves substitutability and testability, "
            "but excessive abstraction increases complexity."
        ),
        "Distribution": (
            "Allows independent deployment and scaling, "
            "but adds network and operational failure modes."
        ),
        "Caching": (
            "Improves latency and reduces load, "
            "but introduces stale data and invalidation complexity."
        ),
        "Asynchrony": (
            "Improves decoupling and can increase throughput, "
            "but complicates consistency and error handling."
        ),
        "Shared database": (
            "Can simplify transactions and reporting, "
            "but increases coupling between components."
        ),
        "Separate databases": (
            "Strengthens ownership boundaries, "
            "but makes cross-domain transactions and reporting harder."
        ),
    }

    print("\nARCHITECTURAL TRADE-OFFS")
    for decision, tradeoff in tradeoffs.items():
        print(f"{decision}: {tradeoff}")


# ============================================================================
# 34. COMMON ARCHITECTURAL MISTAKES
# ============================================================================

def common_architectural_mistakes() -> None:
    mistakes = {
        "Premature microservices":
            "Splitting a system before independent scaling or deployment is needed.",
        "Shared database coupling":
            "Allowing every component to modify every table directly.",
        "God component":
            "One component owns unrelated responsibilities and becomes a change hotspot.",
        "Circular dependencies":
            "Components depend on each other, making independent evolution difficult.",
        "Leaky abstraction":
            "Implementation details escape an abstraction and become part of its consumers.",
        "Distributed monolith":
            "Many services are deployed separately but remain tightly coupled operationally.",
        "Anemic boundaries":
            "Modules have names but no meaningful ownership or dependency rules.",
        "Framework-driven architecture":
            "Business structure follows framework mechanics instead of business responsibilities.",
        "Over-abstraction":
            "Interfaces exist without a real variability or boundary requirement.",
        "Ignoring failure":
            "Remote calls are treated as if they were local function calls.",
    }

    print("\nCOMMON ARCHITECTURAL MISTAKES")
    for mistake, explanation in mistakes.items():
        print(f"{mistake}: {explanation}")


# ============================================================================
# 35. ARCHITECTURE REVIEW CHECKLIST
# ============================================================================

def architecture_review_checklist() -> None:
    checklist = [
        "Are component responsibilities clear?",
        "Are boundaries explicit?",
        "Is dependency direction intentional?",
        "Are business rules protected from infrastructure details?",
        "Can components be tested independently where appropriate?",
        "Who owns each important piece of data?",
        "What happens when a dependency fails?",
        "Where are security trust boundaries?",
        "Where are transactions required?",
        "Which operations are synchronous and which can be asynchronous?",
        "What are the expected performance characteristics?",
        "What scales independently?",
        "How is the system observed in production?",
        "Which architectural decisions are difficult to reverse?",
        "Are architectural constraints automatically tested?",
    ]

    print("\nARCHITECTURE REVIEW CHECKLIST")
    for index, item in enumerate(checklist, start=1):
        print(f"{index:02d}. {item}")


# ============================================================================
# 36. PROGRESSIVE ARCHITECTURAL EVOLUTION
# ============================================================================

class BasicOrderSystem:
    """
    Stage 1:
        A simple in-process implementation.

    Appropriate for small systems where simplicity is the primary concern.
    """

    def __init__(self) -> None:
        self.orders: dict[str, Order] = {}

    def create(self, customer_id: str, total_cents: int) -> Order:
        if total_cents <= 0:
            raise ValueError("total_cents must be positive")

        order = Order(
            order_id=str(uuid4()),
            customer_id=customer_id,
            lines=[OrderLine("UNKNOWN", 1, total_cents)],
        )

        self.orders[order.order_id] = order
        return order


class ModularOrderSystem:
    """
    Stage 2:
        Separate domain, application, and infrastructure responsibilities.
    """

    def __init__(
        self,
        repository: OrderRepositoryPort,
        payment: PaymentPort,
    ) -> None:
        self.repository = repository
        self.payment = payment

    def create_and_pay(self, order: OrderDomain) -> OrderDomain:
        if not self.payment.charge(order.customer_id, order.total_cents):
            raise RuntimeError("Payment failed")

        order.mark_paid()

        self.repository.save(
            Order(
                order_id=order.order_id,
                customer_id=order.customer_id,
                lines=order.lines,
                status=order.status,
            )
        )

        return order


class DistributedOrderSystem:
    """
    Stage 3 conceptual boundary.

    The class represents an application coordinator that communicates with
    remote capabilities through explicit interfaces.

    A production distributed implementation would require real transport,
    timeouts, retries, authentication, tracing, idempotency, and contract
    versioning.
    """

    def __init__(
        self,
        payment: PaymentPort,
        inventory: InventoryService,
    ) -> None:
        self.payment = payment
        self.inventory = inventory

    def process(self, order: OrderDomain) -> OrderDomain:
        self.inventory.reserve(sum(line.quantity for line in order.lines))

        if not self.payment.charge(order.customer_id, order.total_cents):
            raise RuntimeError(
                "Payment failed after inventory reservation; "
                "compensation may be required."
            )

        order.mark_paid()
        return order


def architectural_evolution_example() -> None:
    print("\nPROGRESSIVE ARCHITECTURAL EVOLUTION")

    basic = BasicOrderSystem()
    basic_order = basic.create("C-900", 2000)
    print("Stage 1 basic order:", basic_order.order_id)

    modular = ModularOrderSystem(
        repository=InMemoryOrderRepository(),
        payment=FakePaymentGateway(),
    )

    modular_order = OrderDomain(
        "ORD-901",
        "C-901",
        [OrderLine("P100", 1, 2000)],
    )

    modular.processed_order = modular.create_and_pay(modular_order)
    print("Stage 2 modular status:", modular.processed_order.status)

    distributed = DistributedOrderSystem(
        payment=FakePaymentGateway(),
        inventory=InventoryService(Inventory("P100", 5)),
    )

    distributed_order = OrderDomain(
        "ORD-902",
        "C-902",
        [OrderLine("P100", 1, 2000)],
    )

    distributed.process(distributed_order)
    print("Stage 3 distributed-style status:", distributed_order.status)

    print(
        "Architectural complexity should increase because a requirement "
        "requires it, not merely because a more complex style exists."
    )


# ============================================================================
# 37. COMPENSATING TRANSACTIONS
# ============================================================================

class Reservation:
    def __init__(self, inventory: InventoryService, quantity: int) -> None:
        self.inventory = inventory
        self.quantity = quantity
        self.active = False

    def reserve(self) -> None:
        self.inventory.reserve(self.quantity)
        self.active = True

    def compensate(self) -> None:
        """
        Compensation restores the business effect.

        This is not necessarily equivalent to a database rollback because
        distributed operations may already have crossed system boundaries.
        """
        if self.active:
            self.inventory.inventory.available_quantity += self.quantity
            self.active = False


def compensating_transaction_example() -> None:
    inventory = InventoryService(Inventory("P100", 5))
    reservation = Reservation(inventory, 2)

    reservation.reserve()

    print("\nCOMPENSATING TRANSACTION")
    print("After reservation:", inventory.inventory.available_quantity)

    # Simulate downstream payment failure.
    reservation.compensate()

    print("After compensation:", inventory.inventory.available_quantity)


# ============================================================================
# 38. VERSIONED CONTRACTS
# ============================================================================

@dataclass(frozen=True)
class OrderCreatedV1:
    order_id: str
    total_cents: int


@dataclass(frozen=True)
class OrderCreatedV2:
    order_id: str
    total_cents: int
    currency: str


def contract_versioning_example() -> None:
    """
    Explicit contract versions can allow producers and consumers to evolve
    independently.

    Compatibility policy must be defined rather than assumed.
    """

    v1 = OrderCreatedV1("ORD-1000", 5000)
    v2 = OrderCreatedV2("ORD-1000", 5000, "INR")

    print("\nCONTRACT VERSIONING")
    print("V1:", v1)
    print("V2:", v2)


# ============================================================================
# 39. ARCHITECTURAL PRINCIPLES IN EXECUTABLE FORM
# ============================================================================

def architectural_principles() -> None:
    principles = [
        "Separate responsibilities that change for different reasons.",
        "Keep boundaries explicit.",
        "Prefer high cohesion within components.",
        "Control coupling between components.",
        "Make dependency direction intentional.",
        "Protect business rules from infrastructure details.",
        "Give important data clear ownership.",
        "Treat remote calls as failure-prone operations.",
        "Design security boundaries explicitly.",
        "Use abstraction when it protects a real boundary or variation point.",
        "Measure quality attributes instead of assuming them.",
        "Automate important architectural constraints.",
        "Prefer the simplest architecture that satisfies current requirements.",
        "Recognize that every architectural decision creates trade-offs.",
    ]

    print("\nARCHITECTURAL PRINCIPLES")
    for number, principle in enumerate(principles, start=1):
        print(f"{number:02d}. {principle}")


# ============================================================================
# 40. INTEGRATED ARCHITECTURE EXAMPLE
# ============================================================================

class IntegratedOrderSystem:
    """
    A compact example combining the major ideas.

    Structure:

        External Request
              |
              v
        Application Service
              |
        +-----+------+----------------+
        |            |                |
        v            v                v
    Domain       Repository       Payment Port
                                  |
                                  v
                              Adapter
                                  |
                                  v
                           External Provider

    The domain owns business rules.
    The application coordinates a use case.
    Ports express required capabilities.
    Adapters connect technology.
    """

    def __init__(
        self,
        repository: OrderRepositoryPort,
        payment: PaymentPort,
        events: OrderEventPublisher,
    ) -> None:
        self.repository = repository
        self.payment = payment
        self.events = events

    def place_order(
        self,
        order_id: str,
        customer_id: str,
        lines: Sequence[OrderLine],
    ) -> OrderDomain:
        order = OrderDomain(
            order_id=order_id,
            customer_id=customer_id,
            lines=lines,
        )

        if not self.payment.charge(
            order.customer_id,
            order.total_cents,
        ):
            raise RuntimeError("Payment was declined")

        order.mark_paid()

        self.repository.save(
            Order(
                order_id=order.order_id,
                customer_id=order.customer_id,
                lines=order.lines,
                status=order.status,
            )
        )

        self.events.publish(
            "OrderPaid",
            {
                "order_id": order.order_id,
                "total_cents": order.total_cents,
            },
        )

        return order


def integrated_example() -> None:
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway()
    events = InMemoryEventPublisher()

    system = IntegratedOrderSystem(
        repository=repository,
        payment=payment,
        events=events,
    )

    order = system.place_order(
        order_id="ORD-INTEGRATED",
        customer_id="C-INTEGRATED",
        lines=[
            OrderLine("P100", 2, 5000),
            OrderLine("P200", 1, 2500),
        ],
    )

    print("\nINTEGRATED ARCHITECTURE")
    print("Order status:", order.status)
    print("Order total:", order.total_cents)
    print("Stored order:", repository.get(order.order_id))
    print("Events:", events.events)


# ============================================================================
# 41. KNOWLEDGE CHECKS
# ============================================================================

def knowledge_checks() -> None:
    """
    These checks convert architectural principles into concrete assertions.
    """

    # A domain object should reject invalid business state.
    try:
        OrderDomain(
            "CHECK-1",
            "C-1",
            [OrderLine("P1", 0, 100)],
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid quantity was accepted")

    # A successful payment should result in persistence.
    repository = InMemoryOrderRepository()
    payment = FakePaymentGateway()
    application = OrderApplicationService(repository, payment)

    order = Order(
        "CHECK-2",
        "C-2",
        [OrderLine("P1", 1, 100)],
    )

    application.place_order(order)

    assert order.status == "PAID"
    assert repository.get(order.order_id) is order

    # Dependency graph should reject an explicitly forbidden dependency.
    graph = DependencyGraph()
    graph.add_dependency("Domain", "Application")
    graph.add_dependency("Application", "Port")

    assert_no_forbidden_dependencies(
        graph,
        {("Domain", "Database")},
    )

    print("\nKNOWLEDGE CHECKS")
    print("All executable checks passed.")


# ============================================================================
# 42. MAIN PROGRAM
# ============================================================================

def main() -> None:
    print("=" * 80)
    print("SOFTWARE ARCHITECTURE BASICS")
    print("Architecture vs Design, Components, and Boundaries")
    print("=" * 80)

    architecture_vs_design()
    architecture_terminology()
    demonstrate_quality_attributes()
    cohesion_and_coupling()
    dependency_graph_example()
    layered_architecture_example()
    boundary_example()
    dependency_inversion_example()
    domain_boundary_example()
    ports_and_adapters_example()
    architecture_styles()
    compare_deployment_styles()
    distributed_boundary_example()
    synchronous_vs_asynchronous()
    asyncio.run(asynchronous_example())
    failure_boundary_example()
    idempotency_example()
    transaction_boundary_example()
    bounded_context_example()
    api_boundary_example()
    security_boundary_example()
    configuration_boundary_example()
    architecture_decision_record_example()
    architecture_fitness_function_example()
    test_payment_failure()
    test_successful_payment()
    edge_case_examples()
    performance_considerations()
    scalability_example()
    observability_example()
    anti_corruption_layer_example()
    event_driven_example()
    eventual_consistency_example()
    backpressure_example()
    architectural_tradeoffs()
    common_architectural_mistakes()
    architecture_review_checklist()
    architectural_evolution_example()
    compensating_transaction_example()
    contract_versioning_example()
    architectural_principles()
    integrated_example()
    knowledge_checks()

    print("\n" + "=" * 80)
    print("END OF SOFTWARE ARCHITECTURE STUDY SCRIPT")
    print("=" * 80)


if __name__ == "__main__":
    main()
