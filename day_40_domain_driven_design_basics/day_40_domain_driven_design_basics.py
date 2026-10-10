from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Iterable
from uuid import UUID, uuid4


# Domain-Driven Design models business rules in the language of the domain.
# This example uses an online order domain to distinguish:
# - entities: objects with identity and lifecycle
# - value objects: immutable concepts defined by their values
# - aggregates: consistency boundaries with a designated root
# - domain: the business space and rules being modeled


class OrderStatus(Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class CustomerId:
    value: UUID

    @classmethod
    def new(cls) -> "CustomerId":
        return cls(uuid4())


@dataclass(frozen=True)
class OrderId:
    value: UUID

    @classmethod
    def new(cls) -> "OrderId":
        return cls(uuid4())


@dataclass(frozen=True)
class ProductId:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise ValueError("ProductId cannot be empty")
        if len(normalized) > 50:
            raise ValueError("ProductId is too long")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str = "INR"

    def __post_init__(self) -> None:
        if self.amount < Decimal("0"):
            raise ValueError("Money amount cannot be negative")
        currency = self.currency.strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            raise ValueError("Currency must be a three-letter code")
        object.__setattr__(self, "currency", currency)

    @classmethod
    def from_text(cls, value: str, currency: str = "INR") -> "Money":
        try:
            amount = Decimal(value).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid monetary value: {value}") from exc
        return cls(amount, currency)

    def add(self, other: "Money") -> "Money":
        self._ensure_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def multiply(self, quantity: int) -> "Money":
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        return Money(
            (self.amount * quantity).quantize(Decimal("0.01")),
            self.currency,
        )

    def _ensure_same_currency(self, other: "Money") -> None:
        if self.currency != other.currency:
            raise ValueError("Cannot operate on different currencies")


@dataclass(frozen=True)
class Address:
    street: str
    city: str
    postal_code: str
    country: str = "India"

    def __post_init__(self) -> None:
        fields = {
            "street": self.street,
            "city": self.city,
            "postal_code": self.postal_code,
            "country": self.country,
        }
        for name, value in fields.items():
            if not value.strip():
                raise ValueError(f"{name} cannot be empty")

        if len(self.postal_code.strip()) < 4:
            raise ValueError("Postal code is too short")


@dataclass(frozen=True)
class OrderLineSnapshot:
    product_id: ProductId
    quantity: int
    unit_price: Money

    @property
    def subtotal(self) -> Money:
        return self.unit_price.multiply(self.quantity)


# OrderLine is an entity inside the Order aggregate.
# It has identity within the aggregate and can change quantity over time.
@dataclass
class OrderLine:
    line_id: UUID
    product_id: ProductId
    quantity: int
    unit_price: Money

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Order line quantity must be positive")

    def increase_quantity(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Quantity increase must be positive")
        self.quantity += amount

    def change_quantity(self, quantity: int) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        self.quantity = quantity

    @property
    def subtotal(self) -> Money:
        return self.unit_price.multiply(self.quantity)

    def snapshot(self) -> OrderLineSnapshot:
        return OrderLineSnapshot(
            product_id=self.product_id,
            quantity=self.quantity,
            unit_price=self.unit_price,
        )


# Customer is a separate entity because identity matters independently
# of its current attributes. Two customers may have identical names
# but still represent different domain participants.
@dataclass
class Customer:
    customer_id: CustomerId
    name: str
    shipping_address: Address

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Customer name cannot be empty")

    def change_shipping_address(self, address: Address) -> None:
        self.shipping_address = address


@dataclass(frozen=True)
class DomainEvent:
    event_name: str
    aggregate_id: UUID


@dataclass(frozen=True)
class OrderConfirmed(DomainEvent):
    total: Money


@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    reason: str


# Order is the aggregate root.
# External code should ask Order to modify its lines rather than directly
# manipulating internal OrderLine objects. This keeps invariants inside
# the consistency boundary.
@dataclass
class Order:
    order_id: OrderId
    customer_id: CustomerId
    shipping_address: Address
    status: OrderStatus = OrderStatus.DRAFT
    _lines: dict[UUID, OrderLine] = field(default_factory=dict, repr=False)
    _events: list[DomainEvent] = field(default_factory=list, repr=False)

    @classmethod
    def create(
        cls,
        customer_id: CustomerId,
        shipping_address: Address,
    ) -> "Order":
        return cls(
            order_id=OrderId.new(),
            customer_id=customer_id,
            shipping_address=shipping_address,
        )

    def add_line(
        self,
        product_id: ProductId,
        quantity: int,
        unit_price: Money,
    ) -> UUID:
        self._ensure_draft()

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        # The aggregate prevents duplicate products from creating
        # independent lines. It consolidates them into one line.
        for line in self._lines.values():
            if line.product_id == product_id:
                line.increase_quantity(quantity)
                return line.line_id

        line_id = uuid4()
        self._lines[line_id] = OrderLine(
            line_id=line_id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
        )
        return line_id

    def remove_line(self, line_id: UUID) -> None:
        self._ensure_draft()
        if line_id not in self._lines:
            raise KeyError("Order line does not exist")
        del self._lines[line_id]

    def change_line_quantity(self, line_id: UUID, quantity: int) -> None:
        self._ensure_draft()
        line = self._lines.get(line_id)
        if line is None:
            raise KeyError("Order line does not exist")
        line.change_quantity(quantity)

    def confirm(self) -> None:
        self._ensure_draft()

        if not self._lines:
            raise ValueError("An order cannot be confirmed without lines")

        total = self.total()
        if total.amount <= Decimal("0"):
            raise ValueError("An order must have a positive total")

        self.status = OrderStatus.CONFIRMED
        self._events.append(
            OrderConfirmed(
                event_name="OrderConfirmed",
                aggregate_id=self.order_id.value,
                total=total,
            )
        )

    def cancel(self, reason: str) -> None:
        if self.status == OrderStatus.CANCELLED:
            raise ValueError("Order is already cancelled")

        if not reason.strip():
            raise ValueError("Cancellation reason is required")

        if self.status not in {
            OrderStatus.DRAFT,
            OrderStatus.CONFIRMED,
        }:
            raise ValueError("Order cannot be cancelled from its current state")

        self.status = OrderStatus.CANCELLED
        self._events.append(
            OrderCancelled(
                event_name="OrderCancelled",
                aggregate_id=self.order_id.value,
                reason=reason.strip(),
            )
        )

    def total(self) -> Money:
        total = Money(Decimal("0"), "INR")
        for line in self._lines.values():
            total = total.add(line.subtotal)
        return total

    def lines(self) -> tuple[OrderLineSnapshot, ...]:
        # Returning snapshots prevents callers from modifying the aggregate
        # through a mutable internal object.
        return tuple(line.snapshot() for line in self._lines.values())

    def pull_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def _ensure_draft(self) -> None:
        if self.status != OrderStatus.DRAFT:
            raise ValueError(
                f"Order modification is not allowed while status is {self.status.value}"
            )


class CustomerRepository:
    """Small in-memory repository representing an aggregate/entity persistence boundary."""

    def __init__(self) -> None:
        self._customers: dict[UUID, Customer] = {}

    def save(self, customer: Customer) -> None:
        self._customers[customer.customer_id.value] = customer

    def get(self, customer_id: CustomerId) -> Customer:
        customer = self._customers.get(customer_id.value)
        if customer is None:
            raise KeyError("Customer was not found")
        return customer


class OrderRepository:
    def __init__(self) -> None:
        self._orders: dict[UUID, Order] = {}

    def save(self, order: Order) -> None:
        self._orders[order.order_id.value] = order

    def get(self, order_id: OrderId) -> Order:
        order = self._orders.get(order_id.value)
        if order is None:
            raise KeyError("Order was not found")
        return order


class OrderApplicationService:
    """
    Application-layer orchestration.

    The service coordinates repositories and aggregate operations. The
    business invariant itself remains inside Order rather than being
    duplicated in this service.
    """

    def __init__(
        self,
        customers: CustomerRepository,
        orders: OrderRepository,
    ) -> None:
        self.customers = customers
        self.orders = orders

    def create_order(self, customer_id: CustomerId) -> Order:
        customer = self.customers.get(customer_id)
        order = Order.create(
            customer_id=customer.customer_id,
            shipping_address=customer.shipping_address,
        )
        self.orders.save(order)
        return order

    def confirm_order(self, order_id: OrderId) -> list[DomainEvent]:
        order = self.orders.get(order_id)
        order.confirm()
        self.orders.save(order)
        return order.pull_events()


class DomainScenario:
    """
    A deterministic demonstration of DDD building blocks.

    The scenario deliberately exercises both valid and invalid states so
    that aggregate boundaries are observable rather than merely described.
    """

    @staticmethod
    def run() -> None:
        print("=== Domain-Driven Design: Order Domain ===")

        address = Address(
            street="14 Gomti Nagar",
            city="Lucknow",
            postal_code="226010",
        )

        customer = Customer(
            customer_id=CustomerId.new(),
            name="Atul Pandey",
            shipping_address=address,
        )

        customers = CustomerRepository()
        orders = OrderRepository()
        customers.save(customer)

        service = OrderApplicationService(customers, orders)
        order = service.create_order(customer.customer_id)

        print(f"Customer identity: {customer.customer_id.value}")
        print(f"Order aggregate identity: {order.order_id.value}")
        print(f"Initial order status: {order.status.value}")

        laptop_id = ProductId("LAPTOP-14")
        laptop_price = Money.from_text("79999.00")

        line_id = order.add_line(
            product_id=laptop_id,
            quantity=1,
            unit_price=laptop_price,
        )

        order.add_line(
            product_id=ProductId("USB-C-HUB"),
            quantity=2,
            unit_price=Money.from_text("2499.50"),
        )

        # Adding the same product again changes the existing entity rather
        # than violating the aggregate's uniqueness rule.
        order.add_line(
            product_id=laptop_id,
            quantity=1,
            unit_price=laptop_price,
        )

        print("\nOrder lines:")
        for line in order.lines():
            print(
                f"  {line.product_id.value}: "
                f"quantity={line.quantity}, "
                f"unit_price={line.unit_price.amount}, "
                f"subtotal={line.subtotal.amount}"
            )

        print(f"Order total: {order.total().amount} {order.total().currency}")

        events = service.confirm_order(order.order_id)
        print(f"Confirmed status: {order.status.value}")

        for event in events:
            if isinstance(event, OrderConfirmed):
                print(
                    f"Domain event: {event.event_name}, "
                    f"aggregate={event.aggregate_id}, "
                    f"total={event.total.amount} {event.total.currency}"
                )

        try:
            order.change_line_quantity(line_id, 3)
        except ValueError as exc:
            print(f"Protected invariant: {exc}")

        try:
            order.confirm()
        except ValueError as exc:
            print(f"Invalid state transition: {exc}")

        order.cancel("Customer requested cancellation")
        print(f"After cancellation: {order.status.value}")

        print("\nValue-object equality:")
        first_price = Money.from_text("100.00")
        second_price = Money.from_text("100.00")
        print(
            "Money(100.00) == Money(100.00):",
            first_price == second_price,
            "(value-based equality)",
        )

        print("\nEntity identity:")
        customer_copy = Customer(
            customer_id=customer.customer_id,
            name="Different Representation",
            shipping_address=address,
        )
        print(
            "Customers with the same CustomerId represent the same entity:",
            customer.customer_id == customer_copy.customer_id,
        )

        print("\nAggregate boundary:")
        print(
            "Order exposes immutable line snapshots rather than its mutable "
            "internal OrderLine instances."
        )


def main() -> None:
    DomainScenario.run()


if __name__ == "__main__":
    main()
