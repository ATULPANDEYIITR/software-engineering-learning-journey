from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
import json
import tempfile
import unittest


class OrderStatus(Enum):
    NEW = "new"
    PAID = "paid"
    CANCELLED = "cancelled"


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    price: Decimal
    stock: int

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValidationError("product_id cannot be empty")
        if not self.name.strip():
            raise ValidationError("name cannot be empty")
        if self.price < Decimal("0"):
            raise ValidationError("price cannot be negative")
        if self.stock < 0:
            raise ValidationError("stock cannot be negative")


@dataclass
class OrderItem:
    product_id: str
    quantity: int

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValidationError("product_id cannot be empty")
        if self.quantity <= 0:
            raise ValidationError("quantity must be positive")


@dataclass
class Order:
    order_id: str
    customer: str
    items: list[OrderItem] = field(default_factory=list)
    status: OrderStatus = OrderStatus.NEW

    def add_item(self, product_id: str, quantity: int) -> None:
        self.items.append(OrderItem(product_id, quantity))


class Inventory:
    def __init__(self, products: list[Product] | None = None) -> None:
        self._products = {p.product_id: p for p in products or []}

    def get(self, product_id: str) -> Product:
        try:
            return self._products[product_id]
        except KeyError as exc:
            raise ValidationError(f"unknown product: {product_id}") from exc

    def reserve(self, product_id: str, quantity: int) -> None:
        product = self.get(product_id)
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        if product.stock < quantity:
            raise ValidationError(
                f"insufficient stock for {product_id}: "
                f"requested={quantity}, available={product.stock}"
            )
        self._products[product_id] = Product(
            product.product_id,
            product.name,
            product.price,
            product.stock - quantity,
        )

    def release(self, product_id: str, quantity: int) -> None:
        product = self.get(product_id)
        if quantity <= 0:
            raise ValidationError("quantity must be positive")
        self._products[product_id] = Product(
            product.product_id,
            product.name,
            product.price,
            product.stock + quantity,
        )

    def stock(self, product_id: str) -> int:
        return self.get(product_id).stock


class OrderService:
    TAX_RATE = Decimal("0.18")

    def __init__(self, inventory: Inventory) -> None:
        self.inventory = inventory

    def calculate_subtotal(self, order: Order) -> Decimal:
        if not order.items:
            raise ValidationError("order must contain at least one item")

        subtotal = Decimal("0")
        for item in order.items:
            product = self.inventory.get(item.product_id)
            subtotal += product.price * item.quantity
        return subtotal.quantize(Decimal("0.01"))

    def calculate_total(self, order: Order) -> Decimal:
        subtotal = self.calculate_subtotal(order)
        tax = (subtotal * self.TAX_RATE).quantize(Decimal("0.01"))
        return subtotal + tax

    def pay(self, order: Order) -> Decimal:
        if order.status is not OrderStatus.NEW:
            raise ValidationError(
                f"cannot pay an order in state {order.status.value}"
            )

        if not order.items:
            raise ValidationError("cannot pay an empty order")

        reserved: list[tuple[str, int]] = []
        try:
            for item in order.items:
                self.inventory.reserve(item.product_id, item.quantity)
                reserved.append((item.product_id, item.quantity))
        except ValidationError:
            for product_id, quantity in reserved:
                self.inventory.release(product_id, quantity)
            raise

        order.status = OrderStatus.PAID
        return self.calculate_total(order)

    def cancel(self, order: Order) -> None:
        if order.status is not OrderStatus.PAID:
            raise ValidationError("only paid orders can be cancelled")

        for item in order.items:
            self.inventory.release(item.product_id, item.quantity)

        order.status = OrderStatus.CANCELLED


def export_order(order: Order, path: Path) -> None:
    payload = {
        "order_id": order.order_id,
        "customer": order.customer,
        "status": order.status.value,
        "items": [
            {"product_id": item.product_id, "quantity": item.quantity}
            for item in order.items
        ],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class ProductFixture:
    @staticmethod
    def catalog() -> list[Product]:
        return [
            Product("KB-01", "Mechanical Keyboard", Decimal("80.00"), 10),
            Product("MS-01", "Wireless Mouse", Decimal("25.00"), 20),
            Product("HD-01", "USB Headset", Decimal("45.00"), 5),
        ]


class TestProductValidation(unittest.TestCase):
    def test_valid_product(self) -> None:
        product = Product("P1", "Test Product", Decimal("10.00"), 3)
        self.assertEqual(product.price, Decimal("10.00"))
        self.assertEqual(product.stock, 3)

    def test_empty_product_id_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Product("", "Keyboard", Decimal("10"), 1)

    def test_negative_price_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Product("P1", "Keyboard", Decimal("-1"), 1)

    def test_negative_stock_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            Product("P1", "Keyboard", Decimal("10"), -1)


class TestOrderItem(unittest.TestCase):
    def test_positive_quantity(self) -> None:
        item = OrderItem("P1", 2)
        self.assertEqual(item.quantity, 2)

    def test_zero_quantity_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            OrderItem("P1", 0)


class TestOrderService(unittest.TestCase):
    def setUp(self) -> None:
        self.inventory = Inventory(ProductFixture.catalog())
        self.service = OrderService(self.inventory)

    def make_order(self) -> Order:
        order = Order("ORD-100", "Test Customer")
        order.add_item("KB-01", 2)
        order.add_item("MS-01", 1)
        return order

    def test_subtotal(self) -> None:
        order = self.make_order()
        self.assertEqual(
            self.service.calculate_subtotal(order),
            Decimal("185.00"),
        )

    def test_total_includes_tax(self) -> None:
        order = self.make_order()
        self.assertEqual(
            self.service.calculate_total(order),
            Decimal("218.30"),
        )

    def test_payment_changes_state_and_inventory(self) -> None:
        order = self.make_order()

        total = self.service.pay(order)

        self.assertEqual(total, Decimal("218.30"))
        self.assertEqual(order.status, OrderStatus.PAID)
        self.assertEqual(self.inventory.stock("KB-01"), 8)
        self.assertEqual(self.inventory.stock("MS-01"), 19)

    def test_empty_order_cannot_be_paid(self) -> None:
        order = Order("ORD-101", "Customer")

        with self.assertRaises(ValidationError):
            self.service.pay(order)

    def test_unknown_product_fails(self) -> None:
        order = Order("ORD-102", "Customer")
        order.add_item("UNKNOWN", 1)

        with self.assertRaises(ValidationError):
            self.service.calculate_total(order)

    def test_insufficient_stock_rolls_back_previous_reservations(self) -> None:
        order = Order("ORD-103", "Customer")
        order.add_item("KB-01", 2)
        order.add_item("HD-01", 6)

        with self.assertRaises(ValidationError):
            self.service.pay(order)

        self.assertEqual(self.inventory.stock("KB-01"), 10)
        self.assertEqual(self.inventory.stock("HD-01"), 5)
        self.assertEqual(order.status, OrderStatus.NEW)

    def test_cancellation_releases_inventory(self) -> None:
        order = self.make_order()
        self.service.pay(order)

        self.service.cancel(order)

        self.assertEqual(order.status, OrderStatus.CANCELLED)
        self.assertEqual(self.inventory.stock("KB-01"), 10)
        self.assertEqual(self.inventory.stock("MS-01"), 20)

    def test_new_order_cannot_be_cancelled(self) -> None:
        order = self.make_order()

        with self.assertRaises(ValidationError):
            self.service.cancel(order)

    def test_paid_order_cannot_be_paid_twice(self) -> None:
        order = self.make_order()
        self.service.pay(order)

        with self.assertRaises(ValidationError):
            self.service.pay(order)

        self.assertEqual(self.inventory.stock("KB-01"), 8)

    def test_fixture_isolated_between_tests(self) -> None:
        order = self.make_order()
        self.service.pay(order)

        self.assertEqual(self.inventory.stock("KB-01"), 8)


class TestFileFixture(unittest.TestCase):
    def test_order_export(self) -> None:
        order = Order("ORD-200", "File Customer")
        order.add_item("KB-01", 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "order.json"
            export_order(order, path)

            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["order_id"], "ORD-200")
            self.assertEqual(data["items"][0]["quantity"], 1)


def run_demo() -> None:
    inventory = Inventory(ProductFixture.catalog())
    service = OrderService(inventory)

    order = Order("ORD-DEMO", "Alice")
    order.add_item("KB-01", 1)
    order.add_item("MS-01", 2)

    print("Unit-testing case study")
    print("-----------------------")
    print(f"Order: {order.order_id}")
    print(f"Subtotal: {service.calculate_subtotal(order)}")
    print(f"Total: {service.calculate_total(order)}")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "order.json"
        export_order(order, path)
        print(f"Fixture export created: {path.name}")


if __name__ == "__main__":
    run_demo()
    unittest.main(verbosity=2)
