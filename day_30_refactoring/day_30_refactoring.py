"""
Refactoring Techniques and Code Improvement
===========================================

A self-contained practical study of refactoring in Python.

The examples move from identifying code smells and applying small,
behavior-preserving transformations to larger architectural improvements.

Refactoring is the disciplined restructuring of existing code without
changing its externally observable behavior. The examples intentionally
separate refactoring from feature development: a refactoring should improve
the internal design while preserving the behavior covered by the contract.

This file uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Callable, Iterable, Protocol
import json
import re
import tempfile
import unittest


# ---------------------------------------------------------------------------
# Code smell: duplicated conditional logic
# ---------------------------------------------------------------------------

def calculate_legacy_discount(customer_type: str, amount: float) -> float:
    """
    A deliberately repetitive implementation.

    The same business rules appear in several branches. Repetition makes
    future changes risky because one branch can be updated while another
    remains stale.
    """
    if customer_type == "premium":
        if amount >= 1000:
            return amount * 0.20
        return amount * 0.10

    if customer_type == "business":
        if amount >= 1000:
            return amount * 0.15
        return amount * 0.05

    if amount >= 1000:
        return amount * 0.05

    return 0.0


def calculate_discount(customer_type: str, amount: Decimal) -> Decimal:
    """
    Refactored version.

    The decision data is separated from the calculation mechanism. This is
    an example of replacing repeated conditional structure with a small,
    explicit policy table.
    """
    if amount < 0:
        raise ValueError("amount cannot be negative")

    rates = {
        "premium": (Decimal("0.10"), Decimal("0.20")),
        "business": (Decimal("0.05"), Decimal("0.15")),
        "standard": (Decimal("0.00"), Decimal("0.05")),
    }

    if customer_type not in rates:
        raise ValueError(f"unknown customer type: {customer_type}")

    lower_rate, high_rate = rates[customer_type]
    rate = high_rate if amount >= Decimal("1000") else lower_rate
    return (amount * rate).quantize(Decimal("0.01"))


# ---------------------------------------------------------------------------
# Extract Method
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OrderItem:
    product_id: str
    description: str
    unit_price: Decimal
    quantity: int

    def subtotal(self) -> Decimal:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.unit_price < 0:
            raise ValueError("unit price cannot be negative")
        return self.unit_price * self.quantity


def validate_order_items(items: Iterable[OrderItem]) -> list[OrderItem]:
    """Extracted validation logic with one responsibility."""
    materialized = list(items)

    if not materialized:
        raise ValueError("an order must contain at least one item")

    product_ids: set[str] = set()

    for item in materialized:
        if not item.product_id.strip():
            raise ValueError("product_id cannot be empty")
        if item.product_id in product_ids:
            raise ValueError(f"duplicate product_id: {item.product_id}")
        product_ids.add(item.product_id)

        # Calling subtotal also validates quantity and price.
        item.subtotal()

    return materialized


# ---------------------------------------------------------------------------
# Replace Magic Numbers with Named Constants
# ---------------------------------------------------------------------------

class PricingRules:
    TAX_RATE = Decimal("0.18")
    FREE_SHIPPING_THRESHOLD = Decimal("1000")
    SHIPPING_FEE = Decimal("80")


def calculate_order_total(items: Iterable[OrderItem]) -> dict[str, Decimal]:
    """
    A cohesive pricing operation.

    Named business constants make policy visible and prevent unexplained
    literals from spreading throughout the codebase.
    """
    valid_items = validate_order_items(items)
    subtotal = sum((item.subtotal() for item in valid_items), Decimal("0"))

    tax = (subtotal * PricingRules.TAX_RATE).quantize(Decimal("0.01"))
    shipping = (
        Decimal("0")
        if subtotal >= PricingRules.FREE_SHIPPING_THRESHOLD
        else PricingRules.SHIPPING_FEE
    )

    total = subtotal + tax + shipping

    return {
        "subtotal": subtotal,
        "tax": tax,
        "shipping": shipping,
        "total": total,
    }


# ---------------------------------------------------------------------------
# Replace Conditional with Polymorphism
# ---------------------------------------------------------------------------

class ShippingStrategy(Protocol):
    def cost(self, weight_kg: Decimal, distance_km: Decimal) -> Decimal:
        ...


@dataclass(frozen=True)
class StandardShipping:
    def cost(self, weight_kg: Decimal, distance_km: Decimal) -> Decimal:
        return (
            Decimal("50")
            + weight_kg * Decimal("12")
            + distance_km * Decimal("0.20")
        ).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class ExpressShipping:
    def cost(self, weight_kg: Decimal, distance_km: Decimal) -> Decimal:
        return (
            Decimal("120")
            + weight_kg * Decimal("18")
            + distance_km * Decimal("0.35")
        ).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class PickupShipping:
    def cost(self, weight_kg: Decimal, distance_km: Decimal) -> Decimal:
        # Weight and distance are intentionally irrelevant for pickup.
        return Decimal("0")


def shipping_cost(
    method: str,
    weight_kg: Decimal,
    distance_km: Decimal,
) -> Decimal:
    """
    The selection boundary is centralized.

    Adding a new strategy does not require modifying a large nested
    conditional calculation.
    """
    if weight_kg < 0 or distance_km < 0:
        raise ValueError("weight and distance must be non-negative")

    strategies: dict[str, ShippingStrategy] = {
        "standard": StandardShipping(),
        "express": ExpressShipping(),
        "pickup": PickupShipping(),
    }

    try:
        strategy = strategies[method]
    except KeyError as exc:
        raise ValueError(f"unsupported shipping method: {method}") from exc

    return strategy.cost(weight_kg, distance_km)


# ---------------------------------------------------------------------------
# Introduce Parameter Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    email: str


@dataclass(frozen=True)
class OrderRequest:
    customer: Customer
    items: tuple[OrderItem, ...]
    shipping_method: str
    destination_distance_km: Decimal


def create_order(request: OrderRequest) -> dict[str, object]:
    """
    A parameter object replaces a long collection of loosely related
    arguments and gives the operation a stable domain boundary.
    """
    if not request.customer.customer_id:
        raise ValueError("customer_id is required")

    totals = calculate_order_total(request.items)

    total_weight = sum(
        (Decimal(item.quantity) * Decimal("0.5") for item in request.items),
        Decimal("0"),
    )

    freight = shipping_cost(
        request.shipping_method,
        total_weight,
        request.destination_distance_km,
    )

    grand_total = totals["total"] + freight

    return {
        "customer_id": request.customer.customer_id,
        "customer_name": request.customer.name,
        "subtotal": totals["subtotal"],
        "tax": totals["tax"],
        "shipping": freight,
        "grand_total": grand_total,
    }


# ---------------------------------------------------------------------------
# Encapsulate Collection
# ---------------------------------------------------------------------------

@dataclass
class ShoppingCart:
    """
    The collection is encapsulated instead of allowing arbitrary external
    mutation of its internal representation.
    """

    _items: dict[str, OrderItem] = field(default_factory=dict)

    def add(self, item: OrderItem) -> None:
        item.subtotal()

        if item.product_id in self._items:
            raise ValueError(
                f"product already exists in cart: {item.product_id}"
            )

        self._items[item.product_id] = item

    def remove(self, product_id: str) -> OrderItem:
        try:
            return self._items.pop(product_id)
        except KeyError as exc:
            raise KeyError(f"product not found: {product_id}") from exc

    def items(self) -> tuple[OrderItem, ...]:
        return tuple(self._items.values())

    @property
    def total(self) -> Decimal:
        return sum(
            (item.subtotal() for item in self._items.values()),
            Decimal("0"),
        )


# ---------------------------------------------------------------------------
# Replace Temporary Variable with Query
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Employee:
    employee_id: str
    name: str
    annual_salary: Decimal
    years_at_company: int
    performance_score: Decimal


def calculate_bonus(employee: Employee) -> Decimal:
    """
    The conditions remain readable because their meaning is expressed through
    named helper functions rather than deeply nested expressions.
    """
    if employee.annual_salary < 0:
        raise ValueError("salary cannot be negative")

    if qualifies_for_senior_bonus(employee):
        return (employee.annual_salary * Decimal("0.12")).quantize(
            Decimal("0.01")
        )

    if qualifies_for_standard_bonus(employee):
        return (employee.annual_salary * Decimal("0.06")).quantize(
            Decimal("0.01")
        )

    return Decimal("0")


def qualifies_for_senior_bonus(employee: Employee) -> bool:
    return (
        employee.years_at_company >= 5
        and employee.performance_score >= Decimal("4.5")
    )


def qualifies_for_standard_bonus(employee: Employee) -> bool:
    return (
        employee.years_at_company >= 2
        and employee.performance_score >= Decimal("3.5")
    )


# ---------------------------------------------------------------------------
# Replace Primitive Obsession with a Value Object
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmailAddress:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()

        if not re.fullmatch(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            normalized,
        ):
            raise ValueError(f"invalid email address: {self.value}")

        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("money amount cannot be negative")

        if not re.fullmatch(r"[A-Z]{3}", self.currency):
            raise ValueError("currency must be a three-letter ISO code")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("cannot add different currencies")

        return Money(
            (self.amount + other.amount).quantize(Decimal("0.01")),
            self.currency,
        )


# ---------------------------------------------------------------------------
# Separate Side Effects from Pure Business Logic
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    customer_email: EmailAddress
    amount: Money


def build_invoice(
    invoice_id: str,
    customer_email: EmailAddress,
    amount: Money,
) -> Invoice:
    """Pure domain construction: no filesystem, network, or console I/O."""
    if not invoice_id.strip():
        raise ValueError("invoice_id cannot be empty")

    return Invoice(invoice_id, customer_email, amount)


def serialize_invoice(invoice: Invoice) -> str:
    """Pure serialization function suitable for isolated testing."""
    return json.dumps(
        {
            "invoice_id": invoice.invoice_id,
            "customer_email": invoice.customer_email.value,
            "amount": str(invoice.amount.amount),
            "currency": invoice.amount.currency,
        },
        indent=2,
    )


def save_invoice(invoice: Invoice, directory: Path) -> Path:
    """
    The I/O boundary is kept separate from invoice construction and business
    rules. This makes filesystem behavior replaceable and testable.
    """
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / f"{invoice.invoice_id}.json"
    destination.write_text(
        serialize_invoice(invoice),
        encoding="utf-8",
    )
    return destination


# ---------------------------------------------------------------------------
# Replace Switch with a Dispatch Table
# ---------------------------------------------------------------------------

def format_invoice_text(invoice: Invoice) -> str:
    return (
        f"Invoice: {invoice.invoice_id}\n"
        f"Customer: {invoice.customer_email.value}\n"
        f"Amount: {invoice.amount.amount:.2f} "
        f"{invoice.amount.currency}"
    )


def format_invoice_json(invoice: Invoice) -> str:
    return serialize_invoice(invoice)


def render_invoice(invoice: Invoice, format_name: str) -> str:
    """
    A dispatch dictionary makes supported representations explicit and keeps
    the formatting implementations independent.
    """
    renderers: dict[str, Callable[[Invoice], str]] = {
        "text": format_invoice_text,
        "json": format_invoice_json,
    }

    try:
        renderer = renderers[format_name]
    except KeyError as exc:
        raise ValueError(f"unsupported format: {format_name}") from exc

    return renderer(invoice)


# ---------------------------------------------------------------------------
# Refactoring a Long Function into a Pipeline
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SalesRecord:
    region: str
    product: str
    revenue: Decimal


def validate_sales_record(record: SalesRecord) -> None:
    if not record.region.strip():
        raise ValueError("sales region cannot be empty")
    if not record.product.strip():
        raise ValueError("product cannot be empty")
    if record.revenue < 0:
        raise ValueError("revenue cannot be negative")


def aggregate_sales(records: Iterable[SalesRecord]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}

    for record in records:
        validate_sales_record(record)
        totals[record.region] = (
            totals.get(record.region, Decimal("0")) + record.revenue
        )

    return totals


def rank_regions_by_sales(
    records: Iterable[SalesRecord],
) -> list[tuple[str, Decimal]]:
    """
    Composition of small transformations is easier to inspect and test than
    one large function that validates, aggregates, sorts, and formats.
    """
    totals = aggregate_sales(records)

    return sorted(
        totals.items(),
        key=lambda pair: pair[1],
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Dependency Inversion for a Notification Boundary
# ---------------------------------------------------------------------------

class NotificationGateway(Protocol):
    def send(self, recipient: EmailAddress, subject: str, body: str) -> None:
        ...


@dataclass
class InMemoryNotificationGateway:
    messages: list[dict[str, str]] = field(default_factory=list)

    def send(
        self,
        recipient: EmailAddress,
        subject: str,
        body: str,
    ) -> None:
        self.messages.append(
            {
                "recipient": recipient.value,
                "subject": subject,
                "body": body,
            }
        )


class OrderNotifier:
    """
    The business service depends on an abstraction rather than directly on
    SMTP, HTTP, or another infrastructure mechanism.
    """

    def __init__(self, gateway: NotificationGateway) -> None:
        self.gateway = gateway

    def notify_order_created(
        self,
        customer_email: EmailAddress,
        order_id: str,
        amount: Money,
    ) -> None:
        self.gateway.send(
            customer_email,
            f"Order {order_id} created",
            f"Your order total is {amount.amount:.2f} {amount.currency}.",
        )


# ---------------------------------------------------------------------------
# A complete refactored domain service
# ---------------------------------------------------------------------------

@dataclass
class OrderRepository:
    _orders: dict[str, dict[str, object]] = field(default_factory=dict)

    def save(self, order_id: str, order: dict[str, object]) -> None:
        if order_id in self._orders:
            raise ValueError(f"order already exists: {order_id}")
        self._orders[order_id] = order

    def get(self, order_id: str) -> dict[str, object]:
        try:
            return self._orders[order_id]
        except KeyError as exc:
            raise KeyError(f"order does not exist: {order_id}") from exc


class OrderService:
    """
    Coordinates domain operations while delegating persistence and
    notification to separate collaborators.
    """

    def __init__(
        self,
        repository: OrderRepository,
        notifier: OrderNotifier,
    ) -> None:
        self.repository = repository
        self.notifier = notifier

    def place_order(self, order_id: str, request: OrderRequest) -> dict[str, object]:
        if not order_id.strip():
            raise ValueError("order_id cannot be empty")

        order = create_order(request)
        self.repository.save(order_id, order)

        self.notifier.notify_order_created(
            EmailAddress(request.customer.email),
            order_id,
            Money(order["grand_total"]),
        )

        return order


# ---------------------------------------------------------------------------
# Refactoring safety: characterization tests
# ---------------------------------------------------------------------------

class RefactoringTests(unittest.TestCase):
    def test_discount_behavior_is_preserved(self) -> None:
        scenarios = [
            ("premium", Decimal("500")),
            ("premium", Decimal("1500")),
            ("business", Decimal("500")),
            ("business", Decimal("1500")),
            ("standard", Decimal("500")),
            ("standard", Decimal("1500")),
        ]

        for customer_type, amount in scenarios:
            old_result = Decimal(
                str(calculate_legacy_discount(customer_type, float(amount)))
            ).quantize(Decimal("0.01"))

            new_result = calculate_discount(customer_type, amount)

            self.assertEqual(old_result, new_result)

    def test_order_totals(self) -> None:
        items = (
            OrderItem("P100", "Keyboard", Decimal("2500"), 1),
            OrderItem("P200", "Mouse", Decimal("800"), 2),
        )

        totals = calculate_order_total(items)

        self.assertEqual(totals["subtotal"], Decimal("4100"))
        self.assertEqual(totals["tax"], Decimal("738.00"))
        self.assertEqual(totals["shipping"], Decimal("0"))
        self.assertEqual(totals["total"], Decimal("4838.00"))

    def test_duplicate_cart_item_is_rejected(self) -> None:
        cart = ShoppingCart()
        item = OrderItem("P1", "Keyboard", Decimal("100"), 1)

        cart.add(item)

        with self.assertRaises(ValueError):
            cart.add(item)

    def test_money_cannot_mix_currencies(self) -> None:
        inr = Money(Decimal("100"), "INR")
        usd = Money(Decimal("100"), "USD")

        with self.assertRaises(ValueError):
            inr.add(usd)

    def test_invalid_email_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            EmailAddress("not-an-email")

    def test_invoice_file_boundary(self) -> None:
        invoice = build_invoice(
            "INV-100",
            EmailAddress("buyer@example.com"),
            Money(Decimal("1250.50")),
        )

        with tempfile.TemporaryDirectory() as directory:
            path = save_invoice(invoice, Path(directory))
            stored = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(stored["invoice_id"], "INV-100")
        self.assertEqual(stored["amount"], "1250.50")

    def test_shipping_strategy_selection(self) -> None:
        standard = shipping_cost(
            "standard",
            Decimal("2"),
            Decimal("100"),
        )
        pickup = shipping_cost(
            "pickup",
            Decimal("2"),
            Decimal("100"),
        )

        self.assertGreater(standard, Decimal("0"))
        self.assertEqual(pickup, Decimal("0"))

    def test_sales_ranking(self) -> None:
        records = [
            SalesRecord("North", "Laptop", Decimal("5000")),
            SalesRecord("South", "Laptop", Decimal("8000")),
            SalesRecord("North", "Monitor", Decimal("2000")),
        ]

        ranked = rank_regions_by_sales(records)

        self.assertEqual(ranked[0], ("South", Decimal("8000")))
        self.assertEqual(ranked[1], ("North", Decimal("7000")))

    def test_order_service_coordinates_dependencies(self) -> None:
        repository = OrderRepository()
        gateway = InMemoryNotificationGateway()
        service = OrderService(repository, OrderNotifier(gateway))

        customer = Customer(
            "C100",
            "Atul",
            "atul@example.com",
        )

        request = OrderRequest(
            customer=customer,
            items=(
                OrderItem(
                    "P100",
                    "Mechanical Keyboard",
                    Decimal("3000"),
                    1,
                ),
            ),
            shipping_method="pickup",
            destination_distance_km=Decimal("20"),
        )

        result = service.place_order("ORD-100", request)

        self.assertEqual(result["grand_total"], Decimal("3540.00"))
        self.assertEqual(len(gateway.messages), 1)
        self.assertEqual(
            gateway.messages[0]["recipient"],
            "atul@example.com",
        )


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def demonstrate() -> None:
    print("REFactoring and Code Improvement")
    print("=" * 45)

    amount = Decimal("1500")
    print(
        "Discount:",
        calculate_discount("premium", amount),
    )

    items = (
        OrderItem("KB", "Mechanical Keyboard", Decimal("2500"), 1),
        OrderItem("MS", "Wireless Mouse", Decimal("900"), 2),
    )

    print("\nOrder totals:")
    for name, value in calculate_order_total(items).items():
        print(f"  {name}: {value}")

    print("\nShipping strategies:")
    for method in ("standard", "express", "pickup"):
        print(
            f"  {method}:",
            shipping_cost(
                method,
                Decimal("2"),
                Decimal("150"),
            ),
        )

    print("\nBonus:")
    employee = Employee(
        "E-100",
        "Riya",
        Decimal("900000"),
        6,
        Decimal("4.7"),
    )
    print(f"  {employee.name}: {calculate_bonus(employee)}")

    print("\nInvoice rendering:")
    invoice = build_invoice(
        "INV-200",
        EmailAddress("customer@example.com"),
        Money(Decimal("2499.99")),
    )
    print(render_invoice(invoice, "text"))

    print("\nSales ranking:")
    records = [
        SalesRecord("North", "Laptop", Decimal("12000")),
        SalesRecord("West", "Laptop", Decimal("9000")),
        SalesRecord("North", "Monitor", Decimal("3000")),
    ]
    for region, revenue in rank_regions_by_sales(records):
        print(f"  {region}: {revenue}")

    print("\nService orchestration:")
    repository = OrderRepository()
    gateway = InMemoryNotificationGateway()
    service = OrderService(repository, OrderNotifier(gateway))

    request = OrderRequest(
        customer=Customer(
            "C-200",
            "Anita",
            "anita@example.com",
        ),
        items=(
            OrderItem(
                "CAM-1",
                "Conference Camera",
                Decimal("6500"),
                1,
            ),
        ),
        shipping_method="express",
        destination_distance_km=Decimal("45"),
    )

    order = service.place_order("ORD-200", request)
    print(f"  stored order total: {order['grand_total']}")
    print(f"  notifications sent: {len(gateway.messages)}")


if __name__ == "__main__":
    demonstrate()

    print("\nRunning refactoring safety tests...")
    test_result = unittest.main(
        argv=["ignored"],
        exit=False,
        verbosity=1,
    )

    if not test_result.result.wasSuccessful():
        raise SystemExit(1)
