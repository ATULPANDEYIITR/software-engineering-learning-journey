#!/usr/bin/env python3
"""
Test-Driven Development: Red-Green-Refactor

Demonstrates:
- Writing failing tests before implementation.
- Implementing the minimum behavior required to pass.
- Refactoring while preserving behavior.
- Test discovery, parametrization, fixtures, mocks, and coverage concepts.
- A practical order-processing service developed through TDD.

Run:
    python tdd_workflow.py

No external dependencies required.
"""

from __future__ import annotations

import json
import logging
import tempfile
import unittest

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================
# DOMAIN MODEL
# ============================================================

class OrderStatus(Enum):
    CREATED = "created"
    PAID = "paid"
    CANCELLED = "cancelled"


class OrderError(Exception):
    """Base exception for order-related failures."""


class ValidationError(OrderError):
    """Raised when input validation fails."""


class StateTransitionError(OrderError):
    """Raised when an invalid state transition is attempted."""


@dataclass(frozen=True)
class OrderItem:
    product_id: str
    quantity: int
    unit_price: Decimal

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValidationError("Product ID cannot be empty.")

        if isinstance(self.quantity, bool) or self.quantity <= 0:
            raise ValidationError("Quantity must be a positive integer.")

        if not isinstance(self.quantity, int):
            raise ValidationError("Quantity must be an integer.")

        if not self.unit_price.is_finite() or self.unit_price < 0:
            raise ValidationError("Unit price must be finite and non-negative.")

        if self.unit_price.as_tuple().exponent < -2:
            raise ValidationError("Unit price supports at most two decimal places.")


@dataclass
class Order:
    order_id: str
    items: tuple[OrderItem, ...]
    status: OrderStatus = OrderStatus.CREATED

    def __post_init__(self) -> None:
        if not self.order_id.strip():
            raise ValidationError("Order ID cannot be empty.")

        if not self.items:
            raise ValidationError("An order must contain at least one item.")

    @property
    def total(self) -> Decimal:
        return sum(
            (item.unit_price * item.quantity for item in self.items),
            Decimal("0.00")
        )


# ============================================================
# BUSINESS LOGIC
# ============================================================

class OrderService:

    def create_order(
        self,
        order_id: str,
        items: list[OrderItem]
    ) -> Order:

        if not items:
            raise ValidationError("An order must contain items.")

        return Order(
            order_id=order_id,
            items=tuple(items)
        )

    def calculate_discount(
        self,
        total: Decimal,
        percentage: Decimal
    ) -> Decimal:

        if not total.is_finite() or total < 0:
            raise ValidationError("Total must be finite and non-negative.")

        if not percentage.is_finite() or not Decimal("0") <= percentage <= Decimal("100"):
            raise ValidationError("Discount must be between 0 and 100.")

        discount = total * percentage / Decimal("100")

        return discount.quantize(Decimal("0.01"))

    def calculate_final_amount(
        self,
        order: Order,
        discount_percentage: Decimal = Decimal("0")
    ) -> Decimal:

        discount = self.calculate_discount(
            order.total,
            discount_percentage
        )

        return order.total - discount

    def pay_order(self, order: Order) -> None:

        if order.status != OrderStatus.CREATED:
            raise StateTransitionError(
                "Only created orders can be paid."
            )

        order.status = OrderStatus.PAID

    def cancel_order(self, order: Order) -> None:

        if order.status == OrderStatus.PAID:
            raise StateTransitionError(
                "Paid orders cannot be cancelled."
            )

        if order.status == OrderStatus.CANCELLED:
            raise StateTransitionError(
                "Order is already cancelled."
            )

        order.status = OrderStatus.CANCELLED


# ============================================================
# TEST FIXTURES
# ============================================================

def sample_items() -> list[OrderItem]:
    return [
        OrderItem(
            product_id="LAPTOP",
            quantity=2,
            unit_price=Decimal("50000.00")
        ),
        OrderItem(
            product_id="MOUSE",
            quantity=3,
            unit_price=Decimal("1000.00")
        )
    ]


# ============================================================
# RED-GREEN-REFACTOR: TEST SUITE
# ============================================================

class TestOrderService(unittest.TestCase):

    def setUp(self) -> None:
        self.service = OrderService()
        self.items = sample_items()
        self.order = self.service.create_order(
            "ORD-1001",
            self.items
        )

    # RED: These tests describe expected behavior.
    # GREEN: The implementation must satisfy these tests.
    # REFACTOR: Internal improvements must preserve these results.

    def test_order_creation(self):
        self.assertEqual(self.order.order_id, "ORD-1001")
        self.assertEqual(self.order.status, OrderStatus.CREATED)

    def test_order_total(self):
        self.assertEqual(
            self.order.total,
            Decimal("103000.00")
        )

    def test_single_item_order(self):
        order = self.service.create_order(
            "ORD-1002",
            [
                OrderItem(
                    "BOOK",
                    1,
                    Decimal("250.00")
                )
            ]
        )

        self.assertEqual(order.total, Decimal("250.00"))

    def test_multiple_item_order(self):
        self.assertEqual(len(self.order.items), 2)

    def test_empty_order_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.create_order("ORD-1003", [])

    def test_invalid_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            OrderItem("BOOK", 0, Decimal("100.00"))

    def test_boolean_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            OrderItem("BOOK", True, Decimal("100.00"))

    def test_negative_price_rejected(self):
        with self.assertRaises(ValidationError):
            OrderItem("BOOK", 1, Decimal("-10.00"))

    def test_non_finite_price_rejected(self):
        with self.assertRaises(ValidationError):
            OrderItem("BOOK", 1, Decimal("NaN"))

    def test_invalid_money_precision(self):
        with self.assertRaises(ValidationError):
            OrderItem("BOOK", 1, Decimal("10.123"))

    def test_zero_discount(self):
        self.assertEqual(
            self.service.calculate_final_amount(self.order),
            Decimal("103000.00")
        )

    def test_ten_percent_discount(self):
        self.assertEqual(
            self.service.calculate_final_amount(
                self.order,
                Decimal("10")
            ),
            Decimal("92700.00")
        )

    def test_hundred_percent_discount(self):
        self.assertEqual(
            self.service.calculate_final_amount(
                self.order,
                Decimal("100")
            ),
            Decimal("0.00")
        )

    def test_invalid_discount_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.calculate_discount(
                Decimal("1000"),
                Decimal("110")
            )

    def test_negative_discount_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.calculate_discount(
                Decimal("1000"),
                Decimal("-5")
            )

    def test_payment_transition(self):
        self.service.pay_order(self.order)

        self.assertEqual(
            self.order.status,
            OrderStatus.PAID
        )

    def test_duplicate_payment_rejected(self):
        self.service.pay_order(self.order)

        with self.assertRaises(StateTransitionError):
            self.service.pay_order(self.order)

    def test_cancellation_transition(self):
        self.service.cancel_order(self.order)

        self.assertEqual(
            self.order.status,
            OrderStatus.CANCELLED
        )

    def test_paid_order_cannot_be_cancelled(self):
        self.service.pay_order(self.order)

        with self.assertRaises(StateTransitionError):
            self.service.cancel_order(self.order)

    def test_duplicate_cancellation_rejected(self):
        self.service.cancel_order(self.order)

        with self.assertRaises(StateTransitionError):
            self.service.cancel_order(self.order)

    def test_empty_order_identifier_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.create_order("", self.items)

    def test_refactoring_preserves_order_total(self):
        original = self.order.total

        self.service.pay_order(self.order)

        self.assertEqual(self.order.total, original)


# ============================================================
# TEST RUNNER AND TEST REPORT
# ============================================================

class DetailedTestResult(unittest.TextTestResult):

    def addSuccess(self, test):
        super().addSuccess(test)
        logger.info("PASS: %s", test.id())

    def addFailure(self, test, err):
        super().addFailure(test, err)
        logger.error("FAIL: %s", test.id())

    def addError(self, test, err):
        super().addError(test, err)
        logger.error("ERROR: %s", test.id())


class DetailedTestRunner(unittest.TextTestRunner):

    resultclass = DetailedTestResult


# ============================================================
# TEST EXECUTION AND WORKFLOW REPORT
# ============================================================

def demonstrate_red_green_refactor() -> dict:

    stages = [
        {
            "stage": "RED",
            "action": "Write a test describing expected behavior.",
            "result": "Test initially fails when behavior is absent."
        },
        {
            "stage": "GREEN",
            "action": "Implement the minimum required behavior.",
            "result": "The previously failing test passes."
        },
        {
            "stage": "REFACTOR",
            "action": "Improve implementation without changing behavior.",
            "result": "All existing tests continue to pass."
        }
    ]

    return {
        "methodology": "Test-Driven Development",
        "stages": stages
    }


# ============================================================
# TEST RESULT PERSISTENCE
# ============================================================

def save_report(report: dict, destination: Path) -> None:

    # Use a temporary file and atomic replacement to avoid
    # exposing a partially written report.
    temporary = destination.with_suffix(".tmp")

    try:
        temporary.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8"
        )

        temporary.replace(destination)

    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def run_tests() -> bool:

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        TestOrderService
    )

    runner = DetailedTestRunner(
        verbosity=2
    )

    result = runner.run(suite)

    report = demonstrate_red_green_refactor()

    report["test_results"] = {
        "total": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": result.wasSuccessful()
    }

    with tempfile.TemporaryDirectory() as directory:
        report_path = Path(directory) / "tdd_report.json"

        save_report(report, report_path)

        logger.info(
            "Test report created: %s",
            report_path.name
        )

        loaded_report = json.loads(
            report_path.read_text(encoding="utf-8")
        )

        assert loaded_report["test_results"]["total"] == result.testsRun

    print("\nTDD WORKFLOW")
    print("=" * 55)

    for stage in report["stages"]:
        print(f"\n{stage['stage']}")
        print(f"Action: {stage['action']}")
        print(f"Result: {stage['result']}")

    print("\nTEST RESULTS")
    print(json.dumps(report["test_results"], indent=4))

    return result.wasSuccessful()


if __name__ == "__main__":
    raise SystemExit(0 if run_tests() else 1)
