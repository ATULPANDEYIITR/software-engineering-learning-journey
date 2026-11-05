#!/usr/bin/env python3
"""
Behavior-Driven Development (BDD)
Scenario modeling, Given-When-Then execution, and acceptance testing.

Scenario:
An e-commerce customer places an order. The system validates inventory,
calculates totals, processes payment, and confirms the order.

Run:
    python behavior_driven_development.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Any
from decimal import Decimal, ROUND_HALF_UP
import json
import time
import traceback


# ============================================================
# 1. Domain models
# ============================================================

class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


@dataclass
class Product:
    product_id: str
    name: str
    price: Decimal
    stock: int

    def __post_init__(self):
        if not self.product_id:
            raise ValueError("Product ID cannot be empty")
        if self.price <= 0:
            raise ValueError("Product price must be positive")
        if self.stock < 0:
            raise ValueError("Stock cannot be negative")


@dataclass
class Order:
    order_id: str
    product_id: str
    quantity: int
    total: Decimal
    status: OrderStatus = OrderStatus.PENDING
    rejection_reason: str | None = None


@dataclass
class ScenarioContext:
    products: dict[str, Product] = field(default_factory=dict)
    order: Order | None = None
    payment_approved: bool = True
    customer_authenticated: bool = True
    events: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ============================================================
# 2. Application behavior
# ============================================================

class OrderService:

    def __init__(self, tax_rate: Decimal = Decimal("0.10")):
        if not Decimal("0") <= tax_rate <= Decimal("1"):
            raise ValueError("Tax rate must be between 0 and 1")

        self.tax_rate = tax_rate

    def calculate_total(
        self,
        product: Product,
        quantity: int
    ) -> Decimal:

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        subtotal = product.price * quantity
        total = subtotal * (Decimal("1") + self.tax_rate)

        return total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

    def place_order(
        self,
        context: ScenarioContext,
        product_id: str,
        quantity: int
    ) -> Order:

        if not context.customer_authenticated:
            raise PermissionError("Customer authentication required")

        if product_id not in context.products:
            raise ValueError("Product does not exist")

        product = context.products[product_id]

        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        if product.stock < quantity:
            raise ValueError("Insufficient inventory")

        if not context.payment_approved:
            raise RuntimeError("Payment authorization failed")

        total = self.calculate_total(product, quantity)

        # Inventory changes only after all validations succeed.
        product.stock -= quantity

        order = Order(
            order_id=f"ORD-{len(context.events) + 1:04d}",
            product_id=product_id,
            quantity=quantity,
            total=total,
            status=OrderStatus.CONFIRMED
        )

        context.order = order
        context.events.append(f"Order {order.order_id} confirmed")

        return order


# ============================================================
# 3. BDD step definitions
# ============================================================

class StepRegistry:

    def __init__(self):
        self.steps: dict[str, Callable] = {}

    def register(self, keyword: str, function: Callable):
        if keyword not in {"Given", "When", "Then", "And"}:
            raise ValueError(f"Unsupported step keyword: {keyword}")

        if keyword in self.steps:
            raise ValueError(f"Duplicate step: {keyword}")

        self.steps[keyword] = function

    def execute(
        self,
        keyword: str,
        context: ScenarioContext,
        **kwargs
    ):
        if keyword not in self.steps:
            raise LookupError(f"Undefined step: {keyword}")

        return self.steps[keyword](context, **kwargs)


registry = StepRegistry()
service = OrderService()


def given_product(
    context: ScenarioContext,
    product_id: str,
    price: str,
    stock: int
):
    context.products[product_id] = Product(
        product_id=product_id,
        name="Wireless Keyboard",
        price=Decimal(price),
        stock=stock
    )


def given_authenticated_customer(context: ScenarioContext):
    context.customer_authenticated = True


def given_unauthenticated_customer(context: ScenarioContext):
    context.customer_authenticated = False


def given_payment_failure(context: ScenarioContext):
    context.payment_approved = False


def when_customer_places_order(
    context: ScenarioContext,
    product_id: str,
    quantity: int
):
    try:
        service.place_order(context, product_id, quantity)
    except (ValueError, PermissionError, RuntimeError) as exc:
        context.errors.append(str(exc))


def then_order_is_confirmed(context: ScenarioContext):
    assert context.order is not None, "Order was not created"
    assert context.order.status == OrderStatus.CONFIRMED


def then_order_is_rejected(context: ScenarioContext):
    assert context.order is None, "Rejected order must not exist"
    assert len(context.errors) > 0, "Expected a rejection reason"


def then_stock_is(context: ScenarioContext, expected: int):
    product = context.products["KB-101"]
    assert product.stock == expected, (
        f"Expected stock {expected}, got {product.stock}"
    )


def then_total_is(context: ScenarioContext, expected: str):
    assert context.order is not None
    assert context.order.total == Decimal(expected)


registry.register("Given", given_product)
registry.register("And", given_authenticated_customer)
registry.register("When", when_customer_places_order)
registry.register("Then", then_order_is_confirmed)


# ============================================================
# 4. Scenario and feature models
# ============================================================

@dataclass
class Step:
    keyword: str
    function: Callable
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class Scenario:
    name: str
    description: str
    steps: list[Step]


@dataclass
class ScenarioResult:
    scenario_name: str
    status: str
    duration_ms: float
    error: str | None = None


class Feature:

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.scenarios: list[Scenario] = []

    def add_scenario(self, scenario: Scenario):
        self.scenarios.append(scenario)


# ============================================================
# 5. BDD test runner
# ============================================================

class BDDRunner:

    def run_scenario(self, scenario: Scenario) -> ScenarioResult:

        context = ScenarioContext()
        start = time.perf_counter()

        try:
            for step in scenario.steps:
                step.function(context, **step.arguments)

            return ScenarioResult(
                scenario_name=scenario.name,
                status="PASSED",
                duration_ms=(time.perf_counter() - start) * 1000
            )

        except Exception:
            return ScenarioResult(
                scenario_name=scenario.name,
                status="FAILED",
                duration_ms=(time.perf_counter() - start) * 1000,
                error=traceback.format_exc()
            )

    def run_feature(self, feature: Feature) -> list[ScenarioResult]:

        results = []

        print(f"\nFeature: {feature.name}")
        print(feature.description)

        for scenario in feature.scenarios:
            result = self.run_scenario(scenario)
            results.append(result)

            print(
                f"[{result.status}] {result.scenario_name} "
                f"({result.duration_ms:.3f} ms)"
            )

            if result.error:
                print(result.error)

        return results


# ============================================================
# 6. Acceptance test scenarios
# ============================================================

feature = Feature(
    name="Customer order placement",
    description=(
        "Customers can place orders when authentication, "
        "inventory, and payment requirements are satisfied."
    )
)

feature.add_scenario(
    Scenario(
        name="Successful order placement",
        description="A valid customer purchases available inventory.",
        steps=[
            Step(
                "Given",
                given_product,
                {"product_id": "KB-101", "price": "1000.00", "stock": 10}
            ),
            Step("And", given_authenticated_customer),
            Step(
                "When",
                when_customer_places_order,
                {"product_id": "KB-101", "quantity": 2}
            ),
            Step("Then", then_order_is_confirmed),
            Step("Then", then_stock_is, {"expected": 8}),
            Step("Then", then_total_is, {"expected": "2200.00"})
        ]
    )
)

feature.add_scenario(
    Scenario(
        name="Reject an order with insufficient inventory",
        description="An order cannot exceed available inventory.",
        steps=[
            Step(
                "Given",
                given_product,
                {"product_id": "KB-101", "price": "1000.00", "stock": 2}
            ),
            Step(
                "When",
                when_customer_places_order,
                {"product_id": "KB-101", "quantity": 5}
            ),
            Step("Then", then_order_is_rejected),
            Step("Then", then_stock_is, {"expected": 2})
        ]
    )
)

feature.add_scenario(
    Scenario(
        name="Reject an unauthenticated customer",
        description="Only authenticated customers can place orders.",
        steps=[
            Step(
                "Given",
                given_product,
                {"product_id": "KB-101", "price": "1000.00", "stock": 10}
            ),
            Step("Given", given_unauthenticated_customer),
            Step(
                "When",
                when_customer_places_order,
                {"product_id": "KB-101", "quantity": 1}
            ),
            Step("Then", then_order_is_rejected),
            Step("Then", then_stock_is, {"expected": 10})
        ]
    )
)

feature.add_scenario(
    Scenario(
        name="Reject a failed payment",
        description="Inventory must remain unchanged after payment failure.",
        steps=[
            Step(
                "Given",
                given_product,
                {"product_id": "KB-101", "price": "1000.00", "stock": 10}
            ),
            Step("Given", given_payment_failure),
            Step(
                "When",
                when_customer_places_order,
                {"product_id": "KB-101", "quantity": 1}
            ),
            Step("Then", then_order_is_rejected),
            Step("Then", then_stock_is, {"expected": 10})
        ]
    )
)


# ============================================================
# 7. Data-driven acceptance testing
# ============================================================

def run_quantity_examples():

    examples = [
        {"quantity": 1, "stock": 5, "expected": "1100.00"},
        {"quantity": 3, "stock": 5, "expected": "3300.00"},
        {"quantity": 5, "stock": 5, "expected": "5500.00"}
    ]

    print("\nScenario Outline: Calculate order totals")

    for example in examples:
        context = ScenarioContext()

        context.products["KB-101"] = Product(
            "KB-101",
            "Wireless Keyboard",
            Decimal("1000.00"),
            example["stock"]
        )

        order = service.place_order(
            context,
            "KB-101",
            example["quantity"]
        )

        assert order.total == Decimal(example["expected"])

        print(
            f"[PASSED] quantity={example['quantity']}, "
            f"total={order.total}"
        )


# ============================================================
# 8. Feature execution and reporting
# ============================================================

def main():

    runner = BDDRunner()
    results = runner.run_feature(feature)

    run_quantity_examples()

    passed = sum(r.status == "PASSED" for r in results)
    failed = len(results) - passed

    report = {
        "feature": feature.name,
        "total_scenarios": len(results),
        "passed": passed,
        "failed": failed,
        "results": [
            {
                "scenario": result.scenario_name,
                "status": result.status,
                "duration_ms": round(result.duration_ms, 3)
            }
            for result in results
        ]
    }

    print("\nAcceptance Test Report")
    print(json.dumps(report, indent=4))

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
