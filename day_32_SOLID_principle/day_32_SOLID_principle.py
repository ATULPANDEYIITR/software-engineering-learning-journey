"""
SOLID Principles in Python
===========================

A self-contained progression from fundamental object-oriented design problems
to practical implementations of:

    SRP - Single Responsibility Principle
    OCP - Open/Closed Principle
    LSP - Liskov Substitution Principle
    ISP - Interface Segregation Principle
    DIP - Dependency Inversion Principle

The examples form a coherent order-processing system. Each principle is
demonstrated by identifying a concrete design problem, implementing a
solution, and exercising the resulting design.

The program uses only the Python standard library.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Callable, Iterable, Protocol, Sequence
import json
import tempfile
import unittest


# ---------------------------------------------------------------------------
# Shared domain model
# ---------------------------------------------------------------------------

CENT = Decimal("0.01")


def money(value: Decimal | int | float | str) -> Decimal:
    """Normalize monetary values to two decimal places."""
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid monetary value: {value!r}") from exc


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    price: Decimal


@dataclass(frozen=True)
class OrderLine:
    product: Product
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Order quantity must be greater than zero.")

    @property
    def subtotal(self) -> Decimal:
        return money(self.product.price * self.quantity)


@dataclass
class Order:
    order_id: str
    customer_email: str
    lines: list[OrderLine]
    status: str = "NEW"

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValueError("Order ID cannot be empty.")
        if "@" not in self.customer_email:
            raise ValueError("Customer email is invalid.")
        if not self.lines:
            raise ValueError("An order must contain at least one line.")

    @property
    def subtotal(self) -> Decimal:
        return money(sum((line.subtotal for line in self.lines), Decimal("0")))


def print_heading(title: str) -> None:
    print(f"\n{'=' * 78}")
    print(title)
    print("=" * 78)


# ===========================================================================
# SRP - Single Responsibility Principle
# ===========================================================================

"""
SRP says that a class should have one cohesive responsibility, often
described as having one reason to change.

The problematic design below mixes:

- order calculation
- persistence
- email notification
- formatting

Changing an email provider, storage format, or pricing calculation can all
force changes to the same class.
"""


class MonolithicOrderService:
    """Intentionally poor design used to expose SRP violations."""

    def create_order(self, order: Order, storage_file: Path) -> Decimal:
        total = order.subtotal

        record = {
            "order_id": order.order_id,
            "customer_email": order.customer_email,
            "total": str(total),
        }

        storage_file.write_text(json.dumps(record), encoding="utf-8")

        # In a real application this would send through an email provider.
        print(f"[MONOLITH] Sending confirmation to {order.customer_email}")

        return total


class OrderCalculator:
    """
    Responsible only for calculating financial values for an order.

    Tax is deliberately kept outside this class so that pricing policy can
    evolve independently from the basic order aggregate.
    """

    def subtotal(self, order: Order) -> Decimal:
        return order.subtotal

    def total(
        self,
        order: Order,
        tax_rate: Decimal = Decimal("0"),
        discount: Decimal = Decimal("0"),
    ) -> Decimal:
        if not Decimal("0") <= tax_rate <= Decimal("1"):
            raise ValueError("Tax rate must be between 0 and 1.")

        discount = money(discount)
        subtotal = order.subtotal

        if discount < 0 or discount > subtotal:
            raise ValueError("Discount must be between zero and the subtotal.")

        tax = money((subtotal - discount) * tax_rate)
        return money(subtotal - discount + tax)


class OrderRepository(ABC):
    """Persistence abstraction used by the SRP example."""

    @abstractmethod
    def save(self, order: Order, total: Decimal) -> None:
        raise NotImplementedError


class JsonOrderRepository(OrderRepository):
    """Responsible only for serializing orders to JSON."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def save(self, order: Order, total: Decimal) -> None:
        record = {
            "order_id": order.order_id,
            "customer_email": order.customer_email,
            "status": order.status,
            "lines": [
                {
                    "product_id": line.product.product_id,
                    "product_name": line.product.name,
                    "quantity": line.quantity,
                    "unit_price": str(line.product.price),
                    "subtotal": str(line.subtotal),
                }
                for line in order.lines
            ],
            "total": str(total),
        }

        self.path.write_text(
            json.dumps(record, indent=2),
            encoding="utf-8",
        )


class NotificationService:
    """Responsible only for customer notification."""

    def send_order_confirmation(self, order: Order, total: Decimal) -> None:
        print(
            f"[NOTIFICATION] Confirmation sent to "
            f"{order.customer_email}: order={order.order_id}, total={total}"
        )


class SROrderApplicationService:
    """
    Coordinates specialized services without taking over their individual
    responsibilities.
    """

    def __init__(
        self,
        calculator: OrderCalculator,
        repository: OrderRepository,
        notifier: NotificationService,
    ) -> None:
        self.calculator = calculator
        self.repository = repository
        self.notifier = notifier

    def create_order(self, order: Order) -> Decimal:
        total = self.calculator.total(
            order,
            tax_rate=Decimal("0.18"),
        )
        self.repository.save(order, total)
        self.notifier.send_order_confirmation(order, total)
        return total


def demonstrate_srp() -> None:
    print_heading("SRP: Separate calculation, persistence, and notification")

    product = Product("P100", "Mechanical Keyboard", money("79.99"))
    order = Order(
        "ORD-1001",
        "customer@example.com",
        [OrderLine(product, 2)],
    )

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "order.json"
        application = SROrderApplicationService(
            calculator=OrderCalculator(),
            repository=JsonOrderRepository(path),
            notifier=NotificationService(),
        )

        total = application.create_order(order)

        print(f"Calculated total: {total}")
        print(f"Persistence file exists: {path.exists()}")


# ===========================================================================
# OCP - Open/Closed Principle
# ===========================================================================

"""
OCP says software entities should be open for extension but closed for
modification.

A common violation is a large conditional that must be edited whenever a new
discount rule is introduced.

The extensible implementation uses a strategy abstraction. New policies can
be added without modifying the checkout engine.
"""


class DiscountPolicy(Protocol):
    def calculate_discount(self, order: Order) -> Decimal:
        ...


class NoDiscount:
    def calculate_discount(self, order: Order) -> Decimal:
        return money("0")


class PercentageDiscount:
    def __init__(self, percentage: Decimal) -> None:
        if not Decimal("0") <= percentage <= Decimal("1"):
            raise ValueError("Percentage must be between 0 and 1.")
        self.percentage = percentage

    def calculate_discount(self, order: Order) -> Decimal:
        return money(order.subtotal * self.percentage)


class BulkQuantityDiscount:
    """
    Discounts a product line when its quantity reaches the configured
    threshold.
    """

    def __init__(self, threshold: int, percentage: Decimal) -> None:
        if threshold <= 0:
            raise ValueError("Threshold must be positive.")
        if not Decimal("0") <= percentage <= Decimal("1"):
            raise ValueError("Percentage must be between 0 and 1.")

        self.threshold = threshold
        self.percentage = percentage

    def calculate_discount(self, order: Order) -> Decimal:
        discount = Decimal("0")

        for line in order.lines:
            if line.quantity >= self.threshold:
                discount += line.subtotal * self.percentage

        return money(discount)


class DiscountEngine:
    """
    The checkout engine depends on the discount abstraction.

    Adding a new discount policy does not require changing this class.
    """

    def __init__(self, policy: DiscountPolicy) -> None:
        self.policy = policy

    def final_total(
        self,
        order: Order,
        tax_rate: Decimal,
    ) -> tuple[Decimal, Decimal]:
        discount = self.policy.calculate_discount(order)

        if discount > order.subtotal:
            raise ValueError("Discount cannot exceed order subtotal.")

        taxable = order.subtotal - discount
        tax = money(taxable * tax_rate)
        total = money(taxable + tax)

        return discount, total


class CustomerTierDiscount:
    """
    A new extension point.

    The existing DiscountEngine requires no modification when this policy
    is introduced.
    """

    RATES = {
        "standard": Decimal("0"),
        "silver": Decimal("0.05"),
        "gold": Decimal("0.10"),
        "platinum": Decimal("0.15"),
    }

    def __init__(self, tier: str) -> None:
        normalized = tier.lower().strip()

        if normalized not in self.RATES:
            raise ValueError(f"Unknown customer tier: {tier!r}")

        self.tier = normalized

    def calculate_discount(self, order: Order) -> Decimal:
        return money(order.subtotal * self.RATES[self.tier])


def demonstrate_ocp() -> None:
    print_heading("OCP: Extend discount behavior without modifying checkout")

    product = Product("P200", "USB-C Dock", money("149.50"))
    order = Order(
        "ORD-2001",
        "gold@example.com",
        [OrderLine(product, 1)],
    )

    policies: dict[str, DiscountPolicy] = {
        "no discount": NoDiscount(),
        "10% percentage": PercentageDiscount(Decimal("0.10")),
        "gold customer": CustomerTierDiscount("gold"),
    }

    for name, policy in policies.items():
        engine = DiscountEngine(policy)
        discount, total = engine.final_total(
            order,
            tax_rate=Decimal("0.18"),
        )
        print(f"{name:20} discount={discount:>8} total={total:>8}")


# ===========================================================================
# LSP - Liskov Substitution Principle
# ===========================================================================

"""
LSP requires that objects of a subtype can be used wherever the base type is
expected without breaking the behavioral expectations of that base type.

A classic example is a payment abstraction that promises `refund`.

If a subclass implements payment processing but cannot honor refund behavior,
it is not a valid subtype of an abstraction that promises refunds.

The solution separates capabilities rather than forcing every payment method
into an overly broad contract.
"""


class PaymentError(Exception):
    pass


class PaymentMethod(ABC):
    @abstractmethod
    def charge(self, amount: Decimal) -> str:
        raise NotImplementedError


class RefundablePaymentMethod(PaymentMethod):
    @abstractmethod
    def refund(self, transaction_id: str, amount: Decimal) -> None:
        raise NotImplementedError


class CardPayment(RefundablePaymentMethod):
    def __init__(self) -> None:
        self.transactions: dict[str, Decimal] = {}

    def charge(self, amount: Decimal) -> str:
        if amount <= 0:
            raise PaymentError("Charge amount must be positive.")

        transaction_id = f"CARD-{len(self.transactions) + 1:04d}"
        self.transactions[transaction_id] = amount
        return transaction_id

    def refund(self, transaction_id: str, amount: Decimal) -> None:
        if transaction_id not in self.transactions:
            raise PaymentError("Unknown card transaction.")

        original = self.transactions[transaction_id]

        if amount <= 0 or amount > original:
            raise PaymentError("Refund exceeds the original transaction.")

        self.transactions[transaction_id] = money(original - amount)


class GiftCardPayment(PaymentMethod):
    """
    Gift cards can charge orders but the business deliberately does not
    support reversing an already issued gift-card transaction through the
    same interface.

    It therefore implements only the contract it can honor.
    """

    def __init__(self, balance: Decimal) -> None:
        if balance < 0:
            raise ValueError("Gift-card balance cannot be negative.")
        self.balance = money(balance)

    def charge(self, amount: Decimal) -> str:
        amount = money(amount)

        if amount <= 0:
            raise PaymentError("Charge amount must be positive.")
        if amount > self.balance:
            raise PaymentError("Insufficient gift-card balance.")

        self.balance = money(self.balance - amount)
        return "GIFT-CHARGE"


def process_payment(
    payment_method: PaymentMethod,
    amount: Decimal,
) -> str:
    """
    This function requires only the behavior promised by PaymentMethod.

    Both CardPayment and GiftCardPayment can safely substitute for it.
    """
    return payment_method.charge(amount)


def refund_payment(
    payment_method: RefundablePaymentMethod,
    transaction_id: str,
    amount: Decimal,
) -> None:
    """
    Refund operations explicitly require the stronger capability.

    A non-refundable payment implementation is never passed here and cannot
    violate the refund contract.
    """
    payment_method.refund(transaction_id, amount)


def demonstrate_lsp() -> None:
    print_heading("LSP: Subtypes preserve the contracts they claim")

    card = CardPayment()
    gift_card = GiftCardPayment(money("100"))

    card_transaction = process_payment(card, money("40"))
    gift_transaction = process_payment(gift_card, money("25"))

    print(f"Card transaction: {card_transaction}")
    print(f"Gift-card transaction: {gift_transaction}")
    print(f"Remaining gift-card balance: {gift_card.balance}")

    refund_payment(card, card_transaction, money("10"))
    print(f"Card balance after partial refund: {card.transactions[card_transaction]}")

    try:
        # This is intentionally prevented at the type/design level. The
        # runtime check below demonstrates the conceptual boundary.
        refund_payment(
            gift_card,  # type: ignore[arg-type]
            gift_transaction,
            money("5"),
        )
    except AttributeError as exc:
        print(f"Invalid substitution rejected at runtime: {exc}")


# ===========================================================================
# ISP - Interface Segregation Principle
# ===========================================================================

"""
ISP says clients should not be forced to depend on methods they do not use.

A large repository-style interface often becomes problematic when different
clients need different capabilities.

The implementation below uses small protocols:

    OrderReader
    OrderWriter
    OrderAuditor

A read-only reporting service depends only on OrderReader. It does not need
write or audit permissions.
"""


@dataclass(frozen=True)
class OrderSummary:
    order_id: str
    customer_email: str
    total: Decimal


class OrderReader(Protocol):
    def get(self, order_id: str) -> OrderSummary | None:
        ...


class OrderWriter(Protocol):
    def save_summary(self, summary: OrderSummary) -> None:
        ...


class OrderAuditor(Protocol):
    def record_event(self, order_id: str, event: str) -> None:
        ...


class InMemoryOrderStore(OrderReader, OrderWriter, OrderAuditor):
    def __init__(self) -> None:
        self._orders: dict[str, OrderSummary] = {}
        self._events: list[tuple[str, str]] = []

    def get(self, order_id: str) -> OrderSummary | None:
        return self._orders.get(order_id)

    def save_summary(self, summary: OrderSummary) -> None:
        self._orders[summary.order_id] = summary

    def record_event(self, order_id: str, event: str) -> None:
        self._events.append((order_id, event))

    @property
    def events(self) -> list[tuple[str, str]]:
        return list(self._events)


class OrderReportingService:
    """
    This client needs only OrderReader.

    It cannot accidentally mutate storage through its declared dependency.
    """

    def __init__(self, reader: OrderReader) -> None:
        self.reader = reader

    def customer_report(self, order_id: str) -> str:
        summary = self.reader.get(order_id)

        if summary is None:
            raise LookupError(f"Order {order_id} was not found.")

        return (
            f"Order {summary.order_id}: "
            f"customer={summary.customer_email}, "
            f"total={summary.total}"
        )


class OrderWriteService:
    """This client needs only OrderWriter and OrderAuditor."""

    def __init__(
        self,
        writer: OrderWriter,
        auditor: OrderAuditor,
    ) -> None:
        self.writer = writer
        self.auditor = auditor

    def store(self, summary: OrderSummary) -> None:
        self.writer.save_summary(summary)
        self.auditor.record_event(
            summary.order_id,
            "ORDER_SUMMARY_STORED",
        )


def demonstrate_isp() -> None:
    print_heading("ISP: Small capability-specific interfaces")

    store = InMemoryOrderStore()

    writer = OrderWriteService(
        writer=store,
        auditor=store,
    )

    summary = OrderSummary(
        order_id="ORD-3001",
        customer_email="report@example.com",
        total=money("212.99"),
    )

    writer.store(summary)

    reporting = OrderReportingService(reader=store)
    print(reporting.customer_report("ORD-3001"))
    print(f"Audit events: {store.events}")


# ===========================================================================
# DIP - Dependency Inversion Principle
# ===========================================================================

"""
DIP states that high-level policy should not depend directly on low-level
implementation details. Both should depend on abstractions.

The high-level checkout workflow below does not know whether inventory is
stored in memory, whether payment is provided by a real gateway, or whether
notifications are delivered through SMTP, a queue, or another provider.

That separation makes testing and replacement practical.
"""


class InventoryGateway(Protocol):
    def reserve(self, product_id: str, quantity: int) -> None:
        ...


class PaymentGateway(Protocol):
    def charge(self, amount: Decimal) -> str:
        ...


class NotificationGateway(Protocol):
    def send(self, recipient: str, subject: str, body: str) -> None:
        ...


class InMemoryInventory(InventoryGateway):
    def __init__(self, quantities: dict[str, int]) -> None:
        self.quantities = dict(quantities)

    def reserve(self, product_id: str, quantity: int) -> None:
        available = self.quantities.get(product_id, 0)

        if quantity > available:
            raise RuntimeError(
                f"Insufficient inventory for {product_id}: "
                f"requested={quantity}, available={available}"
            )

        self.quantities[product_id] = available - quantity


class FakePaymentGateway(PaymentGateway):
    def __init__(self, decline: bool = False) -> None:
        self.decline = decline
        self.charges: list[Decimal] = []

    def charge(self, amount: Decimal) -> str:
        if self.decline:
            raise PaymentError("Payment gateway declined the transaction.")

        self.charges.append(amount)
        return f"PAY-{len(self.charges):04d}"


class ConsoleNotificationGateway(NotificationGateway):
    def send(self, recipient: str, subject: str, body: str) -> None:
        print(f"[EMAIL] To: {recipient}")
        print(f"[EMAIL] Subject: {subject}")
        print(f"[EMAIL] {body}")


class CheckoutService:
    """
    High-level checkout policy.

    Dependencies are injected through abstractions. No concrete database,
    payment vendor, or messaging implementation is constructed here.
    """

    def __init__(
        self,
        inventory: InventoryGateway,
        payment: PaymentGateway,
        notification: NotificationGateway,
        calculator: OrderCalculator,
    ) -> None:
        self.inventory = inventory
        self.payment = payment
        self.notification = notification
        self.calculator = calculator

    def checkout(self, order: Order) -> str:
        total = self.calculator.total(
            order,
            tax_rate=Decimal("0.18"),
        )

        reserved: list[OrderLine] = []

        try:
            for line in order.lines:
                self.inventory.reserve(
                    line.product.product_id,
                    line.quantity,
                )
                reserved.append(line)

            transaction_id = self.payment.charge(total)

        except Exception:
            # A production system would need an explicit compensation or
            # transaction mechanism because external systems cannot always
            # be rolled back atomically.
            order.status = "PAYMENT_FAILED"
            raise

        order.status = "PAID"

        self.notification.send(
            order.customer_email,
            "Order confirmation",
            (
                f"Order {order.order_id} was paid successfully. "
                f"Transaction={transaction_id}, total={total}"
            ),
        )

        return transaction_id


def demonstrate_dip() -> None:
    print_heading("DIP: High-level checkout depends on abstractions")

    product = Product("P400", "Security Token", money("59.00"))

    order = Order(
        "ORD-4001",
        "buyer@example.com",
        [OrderLine(product, 2)],
    )

    checkout = CheckoutService(
        inventory=InMemoryInventory({"P400": 10}),
        payment=FakePaymentGateway(),
        notification=ConsoleNotificationGateway(),
        calculator=OrderCalculator(),
    )

    transaction = checkout.checkout(order)

    print(f"Transaction: {transaction}")
    print(f"Order status: {order.status}")


# ===========================================================================
# Combining the principles
# ===========================================================================

"""
The principles reinforce each other but are not interchangeable.

SRP keeps each component cohesive.
OCP makes policy variations extensible.
LSP protects substitutability when inheritance is used.
ISP keeps contracts focused on actual client needs.
DIP separates high-level business policy from infrastructure details.

The following composition intentionally combines all five.
"""


@dataclass(frozen=True)
class ApplicationConfig:
    tax_rate: Decimal
    customer_tier: str


class ProductionOrderApplication:
    """
    Application-level orchestration.

    Its constructor receives capabilities rather than concrete infrastructure.
    """

    def __init__(
        self,
        config: ApplicationConfig,
        calculator: OrderCalculator,
        repository: OrderWriter,
        inventory: InventoryGateway,
        payment: PaymentGateway,
        notifier: NotificationGateway,
    ) -> None:
        self.config = config
        self.calculator = calculator
        self.repository = repository
        self.inventory = inventory
        self.payment = payment
        self.notifier = notifier

    def place(self, order: Order) -> str:
        discount_policy = CustomerTierDiscount(self.config.customer_tier)
        discount = discount_policy.calculate_discount(order)

        taxable = money(order.subtotal - discount)
        tax = money(taxable * self.config.tax_rate)
        total = money(taxable + tax)

        for line in order.lines:
            self.inventory.reserve(
                line.product.product_id,
                line.quantity,
            )

        transaction_id = self.payment.charge(total)

        self.repository.save_summary(
            OrderSummary(
                order_id=order.order_id,
                customer_email=order.customer_email,
                total=total,
            )
        )

        self.notifier.send(
            order.customer_email,
            "Order placed",
            (
                f"Order={order.order_id}; "
                f"discount={discount}; "
                f"tax={tax}; "
                f"total={total}; "
                f"transaction={transaction_id}"
            ),
        )

        order.status = "PAID"
        return transaction_id


# ===========================================================================
# Testing the design
# ===========================================================================

class SolidDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keyboard = Product(
            "TEST-1",
            "Test Keyboard",
            money("100"),
        )

    def test_srp_calculates_tax_correctly(self) -> None:
        order = Order(
            "T-1",
            "test@example.com",
            [OrderLine(self.keyboard, 2)],
        )

        calculator = OrderCalculator()

        self.assertEqual(
            calculator.total(order, Decimal("0.10")),
            money("220"),
        )

    def test_ocp_customer_discount_is_extensible(self) -> None:
        order = Order(
            "T-2",
            "test@example.com",
            [OrderLine(self.keyboard, 1)],
        )

        policy = CustomerTierDiscount("gold")
        self.assertEqual(
            policy.calculate_discount(order),
            money("10"),
        )

    def test_lsp_payment_substitution(self) -> None:
        card = CardPayment()
        transaction = process_payment(card, money("50"))

        self.assertTrue(transaction.startswith("CARD-"))

    def test_isp_reporting_uses_reader_capability(self) -> None:
        store = InMemoryOrderStore()

        store.save_summary(
            OrderSummary(
                "T-3",
                "reader@example.com",
                money("75"),
            )
        )

        report = OrderReportingService(store).customer_report("T-3")

        self.assertIn("75.00", report)

    def test_dip_allows_fake_dependencies(self) -> None:
        inventory = InMemoryInventory({"TEST-1": 3})
        payment = FakePaymentGateway()

        checkout = CheckoutService(
            inventory=inventory,
            payment=payment,
            notification=ConsoleNotificationGateway(),
            calculator=OrderCalculator(),
        )

        order = Order(
            "T-4",
            "dip@example.com",
            [OrderLine(self.keyboard, 2)],
        )

        transaction = checkout.checkout(order)

        self.assertEqual(transaction, "PAY-0001")
        self.assertEqual(inventory.quantities["TEST-1"], 1)

    def test_invalid_quantity_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            OrderLine(self.keyboard, 0)

    def test_invalid_discount_is_rejected(self) -> None:
        order = Order(
            "T-5",
            "test@example.com",
            [OrderLine(self.keyboard, 1)],
        )

        calculator = OrderCalculator()

        with self.assertRaises(ValueError):
            calculator.total(
                order,
                tax_rate=Decimal("0.10"),
                discount=money("200"),
            )


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        SolidDesignTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)


# ===========================================================================
# Main executable demonstration
# ===========================================================================

def main() -> None:
    print_heading("SOLID PRINCIPLES: PRACTICAL PYTHON CASE STUDY")

    demonstrate_srp()
    demonstrate_ocp()
    demonstrate_lsp()
    demonstrate_isp()
    demonstrate_dip()

    print_heading("Combined SOLID Design")

    product = Product(
        "P500",
        "Developer Laptop Stand",
        money("89.00"),
    )

    order = Order(
        "ORD-5001",
        "developer@example.com",
        [OrderLine(product, 3)],
    )

    store = InMemoryOrderStore()

    application = ProductionOrderApplication(
        config=ApplicationConfig(
            tax_rate=Decimal("0.18"),
            customer_tier="silver",
        ),
        calculator=OrderCalculator(),
        repository=store,
        inventory=InMemoryInventory({"P500": 10}),
        payment=FakePaymentGateway(),
        notifier=ConsoleNotificationGateway(),
    )

    transaction = application.place(order)

    print(f"Final transaction: {transaction}")
    print(f"Final order status: {order.status}")
    print(f"Persisted order: {store.get(order.order_id)}")

    print_heading("Automated Verification")
    run_tests()


if __name__ == "__main__":
    main()
