"""
Clean Code: Functions, Duplication, Comments, and Code Smells

A self-contained study program that progresses from basic clean-code principles
to practical refactoring, code-smell detection, validation, testing, and
production-oriented design.

The examples intentionally begin with poorly structured code and then transform
it into clearer, more maintainable implementations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable, Iterable, Sequence
import math
import re
import statistics
import time


# ============================================================================
# 1. FUNDAMENTALS: WHAT CLEAN CODE MEANS
# ============================================================================

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    print(f"\n--- {title} ---")


def explain_basic_terms() -> None:
    """
    Clean code is code whose intent can be understood with little effort.

    Important properties:
    - meaningful names
    - small, focused functions
    - low duplication
    - comments that explain intent rather than obvious syntax
    - predictable behavior
    - clear boundaries
    - limited complexity
    - useful error handling
    - testability
    - maintainability
    """
    terms = {
        "Cohesion": "How strongly the responsibilities of a unit belong together.",
        "Coupling": "How strongly one component depends on other components.",
        "Duplication": "Repeated knowledge, logic, or rules that should often have one source.",
        "Code smell": "A sign that code may have a design or maintenance problem.",
        "Refactoring": "Changing internal structure without intentionally changing behavior.",
        "Side effect": "A function behavior that changes state outside its local calculation.",
        "Cyclomatic complexity": "A rough measure of independent decision paths.",
        "Abstraction": "Representing essential behavior while hiding unnecessary details.",
    }

    for name, meaning in terms.items():
        print(f"{name}: {meaning}")


# ============================================================================
# 2. FUNCTIONS: RESPONSIBILITY AND SIZE
# ============================================================================

def bad_order_total(items: list[dict], tax_rate: float, discount_code: str) -> float:
    """
    Deliberately poor example.

    One function performs:
    - validation
    - pricing
    - discount selection
    - tax calculation
    - formatting concerns
    - business decisions

    It is difficult to test individual rules independently.
    """
    total = 0.0

    for item in items:
        if "price" not in item or "quantity" not in item:
            raise ValueError("Invalid item")

        if item["quantity"] < 0:
            raise ValueError("Negative quantity")

        total += item["price"] * item["quantity"]

    if discount_code == "SAVE10":
        total *= 0.90
    elif discount_code == "SAVE20":
        total *= 0.80

    if total > 1000:
        total *= 0.95

    total += total * tax_rate
    return round(total, 2)


def validate_item(item: dict) -> None:
    """Validate one order item."""
    if "price" not in item or "quantity" not in item:
        raise ValueError("Each item requires price and quantity.")

    if not isinstance(item["price"], (int, float)):
        raise TypeError("Price must be numeric.")

    if not isinstance(item["quantity"], int):
        raise TypeError("Quantity must be an integer.")

    if item["price"] < 0:
        raise ValueError("Price cannot be negative.")

    if item["quantity"] < 0:
        raise ValueError("Quantity cannot be negative.")


def calculate_subtotal(items: Iterable[dict]) -> float:
    """Calculate the subtotal independently from discounts and taxes."""
    subtotal = 0.0

    for item in items:
        validate_item(item)
        subtotal += item["price"] * item["quantity"]

    return subtotal


def discount_rate_for(code: str | None, subtotal: float) -> float:
    """Return the percentage discount represented by the business rules."""
    rates = {
        "SAVE10": 0.10,
        "SAVE20": 0.20,
    }

    explicit_rate = rates.get(code, 0.0)
    volume_rate = 0.05 if subtotal > 1000 else 0.0
    return max(explicit_rate, volume_rate)


def calculate_discount(subtotal: float, discount_code: str | None) -> float:
    """Calculate the discount amount."""
    return subtotal * discount_rate_for(discount_code, subtotal)


def calculate_tax(taxable_amount: float, tax_rate: float) -> float:
    """Calculate tax after validating the tax rate."""
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative.")

    return taxable_amount * tax_rate


def calculate_order_total(
    items: Sequence[dict],
    tax_rate: float,
    discount_code: str | None = None,
) -> float:
    """
    Coordinate small, focused operations.

    The function reads almost like a business description:
    subtotal -> discount -> taxable amount -> tax -> total.
    """
    subtotal = calculate_subtotal(items)
    discount = calculate_discount(subtotal, discount_code)
    taxable_amount = subtotal - discount
    tax = calculate_tax(taxable_amount, tax_rate)
    return round(taxable_amount + tax, 2)


# ============================================================================
# 3. FUNCTION DESIGN: PARAMETERS, RETURN VALUES, AND PREDICTABILITY
# ============================================================================

def is_valid_percentage(value: float) -> bool:
    """Return whether a number represents a percentage between 0 and 100."""
    return 0 <= value <= 100


def percentage_of(value: float, percentage: float) -> float:
    """Calculate a percentage without modifying external state."""
    if not is_valid_percentage(percentage):
        raise ValueError("Percentage must be between 0 and 100.")

    return value * percentage / 100


def normalize_email(email: str) -> str:
    """Normalize an email address for comparison and storage."""
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    """
    Perform a deliberately simple application-level validation.

    Production systems may need stronger domain-specific validation, but
    validation should still remain isolated from unrelated business logic.
    """
    normalized = normalize_email(email)
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    return bool(re.fullmatch(pattern, normalized))


# ============================================================================
# 4. PURE FUNCTIONS VERSUS SIDE EFFECTS
# ============================================================================

def pure_add(a: int, b: int) -> int:
    """Same inputs produce the same output and no external state changes."""
    return a + b


event_log: list[str] = []


def impure_record_event(message: str) -> None:
    """Example of a side effect: modifying external state."""
    event_log.append(message)


def pure_build_event(message: str) -> dict:
    """Prefer returning data when the caller does not need immediate I/O."""
    return {
        "message": message,
        "created": True,
    }


# ============================================================================
# 5. DUPLICATION
# ============================================================================

def duplicated_invoice_price_v1(price: float, quantity: int) -> float:
    return price * quantity


def duplicated_invoice_price_v2(price: float, quantity: int) -> float:
    # This is intentionally the same rule in a different location.
    return price * quantity


def line_total(price: float, quantity: int) -> float:
    """Single source of truth for the line-item calculation."""
    if price < 0:
        raise ValueError("Price cannot be negative.")
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")
    return price * quantity


def calculate_invoice(items: Sequence[dict]) -> float:
    return sum(line_total(item["price"], item["quantity"]) for item in items)


def calculate_cart(items: Sequence[dict]) -> float:
    return sum(line_total(item["price"], item["quantity"]) for item in items)


# ============================================================================
# 6. DUPLICATION IS NOT ALWAYS BAD
# ============================================================================

def display_customer_name(first_name: str, last_name: str) -> str:
    return f"{first_name.strip()} {last_name.strip()}".strip()


def display_employee_name(first_name: str, last_name: str) -> str:
    # Similar code may be acceptable if the concepts have different reasons
    # to change. Removing every repeated line can create harmful coupling.
    return f"{first_name.strip()} {last_name.strip()}".strip()


# ============================================================================
# 7. COMMENTS: USE THEM FOR INTENT, NOT OBVIOUS SYNTAX
# ============================================================================

def bad_comment_example(items: list[int]) -> int:
    # Loop through items.
    total = 0

    # Add each item.
    for item in items:
        total += item

    # Return total.
    return total


def calculate_net_revenue(gross_revenue: float, refunds: float) -> float:
    """
    The formula itself is obvious. The business reason may not be.

    This comment explains the policy rather than repeating the code:
    refunds must be excluded before revenue is reported to the finance system.
    """
    return gross_revenue - refunds


# ============================================================================
# 8. NAMING
# ============================================================================

def calculate_monthly_subscription_cost(
    monthly_price: float,
    active_months: int,
) -> float:
    """Meaningful names reduce the need for explanatory comments."""
    if monthly_price < 0 or active_months < 0:
        raise ValueError("Inputs cannot be negative.")

    return monthly_price * active_months


# Poor names are shown as an anti-pattern, not as preferred style.
def poor_naming(a: float, b: int) -> float:
    return a * b


# ============================================================================
# 9. BOOLEAN AND CONDITIONAL CLARITY
# ============================================================================

def is_adult(age: int) -> bool:
    return age >= 18


def can_place_order(age: int, account_active: bool) -> bool:
    return is_adult(age) and account_active


def eligibility_message(age: int, account_active: bool) -> str:
    if can_place_order(age, account_active):
        return "Order permitted."
    return "Order not permitted."


# ============================================================================
# 10. GUARD CLAUSES
# ============================================================================

def calculate_shipping_cost(weight_kg: float, destination: str) -> float:
    """
    Guard clauses prevent deeply nested conditionals.
    """
    if weight_kg < 0:
        raise ValueError("Weight cannot be negative.")

    if not destination.strip():
        raise ValueError("Destination is required.")

    if weight_kg == 0:
        return 0.0

    if destination.upper() == "LOCAL":
        return round(5 + weight_kg * 1.5, 2)

    return round(10 + weight_kg * 3.0, 2)


# ============================================================================
# 11. DEFAULTS AND ARGUMENT DESIGN
# ============================================================================

def paginate(
    values: Sequence,
    page: int = 1,
    page_size: int = 10,
) -> list:
    """A focused function with validated arguments."""
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if page_size < 1:
        raise ValueError("Page size must be at least 1.")

    start = (page - 1) * page_size
    end = start + page_size
    return list(values[start:end])


# ============================================================================
# 12. CODE SMELLS
# ============================================================================

@dataclass
class Smell:
    name: str
    symptom: str
    risk: str
    refactoring_direction: str


CODE_SMELLS = [
    Smell(
        "Long Function",
        "One function performs many unrelated operations.",
        "Changes become risky and testing becomes difficult.",
        "Extract focused functions.",
    ),
    Smell(
        "Duplicate Code",
        "The same business rule appears in multiple places.",
        "One copy can be changed while another remains stale.",
        "Centralize shared knowledge where the concepts are genuinely shared.",
    ),
    Smell(
        "Long Parameter List",
        "A function requires many independent arguments.",
        "Call sites become difficult to understand.",
        "Group coherent data into a meaningful object.",
    ),
    Smell(
        "Deep Nesting",
        "Many conditional levels obscure the main path.",
        "Control flow becomes difficult to reason about.",
        "Use guard clauses and focused functions.",
    ),
    Smell(
        "Magic Numbers",
        "Unexplained numeric constants appear throughout code.",
        "The meaning and business rule become unclear.",
        "Name meaningful constants.",
    ),
    Smell(
        "Feature Envy",
        "A function repeatedly depends on another object's internals.",
        "Responsibilities may be placed in the wrong abstraction.",
        "Move behavior closer to the data it conceptually belongs to.",
    ),
    Smell(
        "God Object",
        "One class owns many unrelated responsibilities.",
        "Changes in one area can affect unrelated behavior.",
        "Split responsibilities around cohesive concepts.",
    ),
    Smell(
        "Shotgun Surgery",
        "One small change requires edits across many unrelated files.",
        "Maintenance becomes slow and error-prone.",
        "Improve boundaries and centralize related behavior.",
    ),
    Smell(
        "Dead Code",
        "Unused functions, variables, imports, or branches remain.",
        "Readers must process irrelevant information.",
        "Remove it after verifying that it is genuinely unused.",
    ),
    Smell(
        "Comment Smell",
        "Comments compensate for unclear names or structure.",
        "The comment can become stale when the code changes.",
        "Improve the code first; retain comments that explain non-obvious intent.",
    ),
]


def display_code_smells() -> None:
    for smell in CODE_SMELLS:
        print(f"\n{smell.name}")
        print(f"  Symptom: {smell.symptom}")
        print(f"  Risk: {smell.risk}")
        print(f"  Direction: {smell.refactoring_direction}")


# ============================================================================
# 13. MAGIC NUMBERS
# ============================================================================

STANDARD_TAX_RATE = 0.18
PREMIUM_DISCOUNT_RATE = 0.15
FREE_SHIPPING_THRESHOLD = 1000.0


def calculate_shipping_for_order(order_value: float) -> float:
    """Named constants expose business meaning."""
    if order_value < 0:
        raise ValueError("Order value cannot be negative.")

    if order_value >= FREE_SHIPPING_THRESHOLD:
        return 0.0

    return 80.0


# ============================================================================
# 14. LONG CONDITIONALS AND POLICY FUNCTIONS
# ============================================================================

def customer_discount(customer_type: str) -> float:
    """
    Move a business decision into a named function.

    This is easier to test than repeating the conditional throughout an
    application.
    """
    normalized_type = customer_type.strip().lower()

    rates = {
        "regular": 0.0,
        "student": 0.10,
        "premium": PREMIUM_DISCOUNT_RATE,
        "enterprise": 0.20,
    }

    if normalized_type not in rates:
        raise ValueError(f"Unknown customer type: {customer_type}")

    return rates[normalized_type]


def discounted_price(price: float, customer_type: str) -> float:
    if price < 0:
        raise ValueError("Price cannot be negative.")

    return price * (1 - customer_discount(customer_type))


# ============================================================================
# 15. DATA CLASSES AND COHESIVE OBJECTS
# ============================================================================

@dataclass(frozen=True)
class Product:
    product_id: str
    name: str
    price: float

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValueError("Product ID cannot be empty.")
        if not self.name.strip():
            raise ValueError("Product name cannot be empty.")
        if self.price < 0:
            raise ValueError("Product price cannot be negative.")


@dataclass
class CartLine:
    product: Product
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")

    @property
    def total(self) -> float:
        return self.product.price * self.quantity


class ShoppingCart:
    """A cohesive abstraction for cart-specific behavior."""

    def __init__(self) -> None:
        self._lines: list[CartLine] = []

    def add(self, product: Product, quantity: int = 1) -> None:
        if quantity <= 0:
            raise ValueError("Quantity must be positive.")

        for line in self._lines:
            if line.product.product_id == product.product_id:
                line.quantity += quantity
                return

        self._lines.append(CartLine(product, quantity))

    def subtotal(self) -> float:
        return sum(line.total for line in self._lines)

    def item_count(self) -> int:
        return sum(line.quantity for line in self._lines)

    def is_empty(self) -> bool:
        return not self._lines


# ============================================================================
# 16. LONG PARAMETER LIST REFACTORING
# ============================================================================

@dataclass(frozen=True)
class ShippingAddress:
    street: str
    city: str
    postal_code: str
    country: str


@dataclass(frozen=True)
class Customer:
    customer_id: str
    name: str
    email: str


def create_order(
    customer: Customer,
    address: ShippingAddress,
    cart: ShoppingCart,
) -> dict:
    """Group related data instead of passing many independent arguments."""
    if not is_valid_email(customer.email):
        raise ValueError("Customer email is invalid.")

    if not address.city.strip() or not address.country.strip():
        raise ValueError("Shipping address is incomplete.")

    if cart.is_empty():
        raise ValueError("Cannot create an order from an empty cart.")

    return {
        "customer_id": customer.customer_id,
        "customer_name": customer.name,
        "email": normalize_email(customer.email),
        "city": address.city,
        "country": address.country,
        "item_count": cart.item_count(),
        "subtotal": round(cart.subtotal(), 2),
    }


# ============================================================================
# 17. ERROR HANDLING
# ============================================================================

class PaymentError(Exception):
    """Base exception for payment-related failures."""


class InvalidAmountError(PaymentError):
    """Raised when an amount is invalid."""


class PaymentDeclinedError(PaymentError):
    """Raised when a payment provider declines a payment."""


def charge_payment(amount: float, available_balance: float) -> str:
    """
    Errors represent exceptional conditions.

    Avoid returning ambiguous values such as None, -1, or False when callers
    need to distinguish multiple failure causes.
    """
    if amount <= 0:
        raise InvalidAmountError("Payment amount must be positive.")

    if amount > available_balance:
        raise PaymentDeclinedError("Insufficient balance.")

    return f"Payment approved for {amount:.2f}"


# ============================================================================
# 18. TESTABLE DESIGN
# ============================================================================

def assert_equal(actual, expected, description: str) -> None:
    if actual != expected:
        raise AssertionError(
            f"{description}: expected {expected!r}, got {actual!r}"
        )
    print(f"PASS: {description}")


def run_tests() -> None:
    section("Automated examples and regression tests")

    assert_equal(
        calculate_subtotal(
            [
                {"price": 100, "quantity": 2},
                {"price": 50, "quantity": 1},
            ]
        ),
        250,
        "subtotal calculation",
    )

    assert_equal(
        discount_rate_for("SAVE10", 500),
        0.10,
        "SAVE10 discount",
    )

    assert_equal(
        discount_rate_for(None, 1500),
        0.05,
        "volume discount",
    )

    assert_equal(
        calculate_order_total(
            [{"price": 100, "quantity": 2}],
            tax_rate=0.10,
            discount_code="SAVE10",
        ),
        198.0,
        "order total",
    )

    assert_equal(
        normalize_email("  USER@Example.COM "),
        "user@example.com",
        "email normalization",
    )

    assert_equal(
        is_valid_email("person@example.com"),
        True,
        "valid email",
    )

    assert_equal(
        is_valid_email("invalid-email"),
        False,
        "invalid email",
    )

    assert_equal(
        paginate(list(range(20)), page=2, page_size=5),
        [5, 6, 7, 8, 9],
        "pagination",
    )


def run_error_tests() -> None:
    subsection("Expected failures")

    cases: list[tuple[str, Callable[[], object]]] = [
        (
            "negative price",
            lambda: calculate_subtotal([{"price": -1, "quantity": 2}]),
        ),
        (
            "negative quantity",
            lambda: calculate_subtotal([{"price": 10, "quantity": -1}]),
        ),
        (
            "invalid percentage",
            lambda: percentage_of(100, 120),
        ),
        (
            "invalid payment",
            lambda: charge_payment(0, 100),
        ),
        (
            "declined payment",
            lambda: charge_payment(200, 100),
        ),
    ]

    for description, operation in cases:
        try:
            operation()
        except (ValueError, TypeError, PaymentError) as error:
            print(f"PASS: {description} -> {type(error).__name__}: {error}")
        else:
            raise AssertionError(f"Expected {description} to fail.")


# ============================================================================
# 19. CALLBACKS AND HIGHER-ORDER FUNCTIONS
# ============================================================================

def apply_discount(
    price: float,
    discount_function: Callable[[float], float],
) -> float:
    """Accept behavior as a function rather than hard-coding one policy."""
    if price < 0:
        raise ValueError("Price cannot be negative.")

    return discount_function(price)


def ten_percent_discount(price: float) -> float:
    return price * 0.90


def twenty_percent_discount(price: float) -> float:
    return price * 0.80


# ============================================================================
# 20. DEPENDENCY INJECTION
# ============================================================================

class TaxService:
    """A small dependency whose behavior can be replaced during testing."""

    def __init__(self, rate: float) -> None:
        if rate < 0:
            raise ValueError("Tax rate cannot be negative.")
        self.rate = rate

    def calculate(self, amount: float) -> float:
        return amount * self.rate


class CheckoutService:
    """
    The checkout service receives a TaxService instead of creating one itself.

    This reduces hard-coded dependencies and makes testing easier.
    """

    def __init__(self, tax_service: TaxService) -> None:
        self.tax_service = tax_service

    def total(self, subtotal: float) -> float:
        if subtotal < 0:
            raise ValueError("Subtotal cannot be negative.")

        return subtotal + self.tax_service.calculate(subtotal)


class ZeroTaxService(TaxService):
    """A test-friendly tax policy."""

    def __init__(self) -> None:
        super().__init__(0.0)


# ============================================================================
# 21. PERFORMANCE: AVOIDING UNNECESSARY WORK
# ============================================================================

def slow_unique_values(values: Sequence[int]) -> list[int]:
    """Educational example with O(n^2) membership checks."""
    result: list[int] = []

    for value in values:
        if value not in result:
            result.append(value)

    return result


def fast_unique_values(values: Sequence[int]) -> list[int]:
    """
    Average-case O(n) membership using a set while retaining insertion order
    through the list.
    """
    seen: set[int] = set()
    result: list[int] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


# ============================================================================
# 22. ALGORITHMIC COMPLEXITY AND CLEAN DESIGN
# ============================================================================

def benchmark_function(
    function: Callable[[Sequence[int]], list[int]],
    values: Sequence[int],
) -> float:
    start = time.perf_counter()
    function(values)
    return time.perf_counter() - start


# ============================================================================
# 23. REFACTORING A CODE SMELL: GOD FUNCTION
# ============================================================================

def bad_employee_report(employees: list[dict]) -> str:
    """
    Deliberately overburdened function.

    It validates data, calculates salary, filters records, formats text, and
    builds the final report.
    """
    lines = []

    for employee in employees:
        if "name" not in employee or "salary" not in employee:
            continue

        if employee["salary"] < 0:
            continue

        if employee.get("active", False):
            annual = employee["salary"] * 12
            lines.append(f"{employee['name']}: {annual:.2f}")

    return "\n".join(lines)


def is_valid_employee(employee: dict) -> bool:
    return (
        bool(employee.get("name"))
        and isinstance(employee.get("salary"), (int, float))
        and employee["salary"] >= 0
    )


def annual_salary(employee: dict) -> float:
    return employee["salary"] * 12


def format_employee_report_line(employee: dict) -> str:
    return f"{employee['name']}: {annual_salary(employee):.2f}"


def employee_report(employees: Sequence[dict]) -> str:
    """Refactored version with separated responsibilities."""
    lines = [
        format_employee_report_line(employee)
        for employee in employees
        if employee.get("active", False) and is_valid_employee(employee)
    ]

    return "\n".join(lines)


# ============================================================================
# 24. REFACTORING CONDITIONAL COMPLEXITY
# ============================================================================

def shipping_zone_rate(zone: str) -> float:
    rates = {
        "LOCAL": 1.0,
        "NATIONAL": 2.0,
        "INTERNATIONAL": 5.0,
    }

    normalized_zone = zone.strip().upper()

    if normalized_zone not in rates:
        raise ValueError(f"Unknown shipping zone: {zone}")

    return rates[normalized_zone]


def shipping_price(weight: float, zone: str) -> float:
    if weight < 0:
        raise ValueError("Weight cannot be negative.")

    base_charge = 5.0
    return base_charge + weight * shipping_zone_rate(zone)


# ============================================================================
# 25. REFACTORING REPEATED VALIDATION
# ============================================================================

def require_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} cannot be empty.")

    return normalized


def create_user(name: str, email: str) -> dict:
    clean_name = require_non_empty(name, "Name")
    clean_email = normalize_email(require_non_empty(email, "Email"))

    if not is_valid_email(clean_email):
        raise ValueError("Email format is invalid.")

    return {
        "name": clean_name,
        "email": clean_email,
    }


# ============================================================================
# 26. REAL-WORLD MINI DOMAIN
# ============================================================================

@dataclass(frozen=True)
class InvoiceLine:
    description: str
    unit_price: float
    quantity: int

    def __post_init__(self) -> None:
        require_non_empty(self.description, "Description")

        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")

    @property
    def amount(self) -> float:
        return self.unit_price * self.quantity


@dataclass
class Invoice:
    invoice_number: str
    customer: Customer
    lines: list[InvoiceLine]

    def subtotal(self) -> float:
        return sum(line.amount for line in self.lines)

    def tax(self, rate: float) -> float:
        return self.subtotal() * rate

    def total(self, rate: float) -> float:
        return self.subtotal() + self.tax(rate)


# ============================================================================
# 27. COMMENTS THAT PRESERVE IMPORTANT KNOWLEDGE
# ============================================================================

def calculate_age(birth_date: date, today: date | None = None) -> int:
    """
    The adjustment is necessary because subtracting years alone is incorrect
    before the birthday in the current year.
    """
    today = today or date.today()

    age = today.year - birth_date.year

    if (today.month, today.day) < (birth_date.month, birth_date.day):
        age -= 1

    return age


# ============================================================================
# 28. EDGE CASES
# ============================================================================

def demonstrate_edge_cases() -> None:
    subsection("Edge cases")

    print("Empty pagination:", paginate([], 1, 10))
    print("Empty unique values:", fast_unique_values([]))
    print("Zero shipping:", calculate_shipping_cost(0, "LOCAL"))
    print("Age before birthday:", calculate_age(date(2000, 12, 31), date(2026, 9, 22)))
    print("Age after birthday:", calculate_age(date(2000, 1, 1), date(2026, 9, 22)))


# ============================================================================
# 29. MAIN DEMONSTRATION
# ============================================================================

def main() -> None:
    section("Clean Code: Functions, Duplication, Comments, and Code Smells")

    subsection("Core terminology")
    explain_basic_terms()

    subsection("Focused function design")
    items = [
        {"price": 250.0, "quantity": 2},
        {"price": 100.0, "quantity": 1},
    ]

    print("Poor-style calculation:", bad_order_total(items, 0.18, "SAVE10"))
    print("Refactored calculation:", calculate_order_total(items, 0.18, "SAVE10"))

    subsection("Pure functions and side effects")
    print("Pure addition:", pure_add(10, 20))
    print("Pure event object:", pure_build_event("Order created"))
    impure_record_event("Order created")
    print("External event log:", event_log)

    subsection("Duplication")
    print("Invoice:", calculate_invoice(items))
    print("Cart:", calculate_cart(items))
    print("Shared line rule:", line_total(25, 4))

    subsection("Meaningful names")
    print(
        "Subscription cost:",
        calculate_monthly_subscription_cost(999, 12),
    )
    print(
        "Eligibility:",
        eligibility_message(25, True),
    )

    subsection("Guard clauses")
    print("Shipping:", calculate_shipping_cost(5, "LOCAL"))

    subsection("Code smells")
    display_code_smells()

    subsection("Named business rules")
    print("Shipping:", calculate_shipping_for_order(1500))
    print("Premium price:", discounted_price(1000, "premium"))

    subsection("Cohesive classes")
    product = Product("P001", "Keyboard", 2500)
    cart = ShoppingCart()
    cart.add(product, 2)
    print("Cart subtotal:", cart.subtotal())
    print("Cart item count:", cart.item_count())

    customer = Customer(
        "C001",
        "Atul Pandey",
        "person@example.com",
    )

    address = ShippingAddress(
        "10 Main Street",
        "Lucknow",
        "226001",
        "India",
    )

    print("Created order:", create_order(customer, address, cart))

    subsection("Exceptions")
    try:
        print(charge_payment(500, 1000))
    except PaymentError as error:
        print("Unexpected payment failure:", error)

    try:
        charge_payment(1500, 1000)
    except PaymentDeclinedError as error:
        print("Expected decline:", error)

    subsection("Higher-order functions")
    print(
        "10% discount:",
        apply_discount(1000, ten_percent_discount),
    )
    print(
        "20% discount:",
        apply_discount(1000, twenty_percent_discount),
    )

    subsection("Dependency injection")
    checkout = CheckoutService(TaxService(0.18))
    print("Taxed total:", checkout.total(1000))

    test_checkout = CheckoutService(ZeroTaxService())
    print("Test total with zero tax:", test_checkout.total(1000))

    subsection("Refactored report")
    employees = [
        {"name": "Asha", "salary": 50000, "active": True},
        {"name": "Ravi", "salary": 60000, "active": False},
        {"name": "Neha", "salary": 70000, "active": True},
        {"name": "", "salary": 50000, "active": True},
    ]

    print(employee_report(employees))

    subsection("Invoice domain")
    invoice = Invoice(
        "INV-1001",
        customer,
        [
            InvoiceLine("Keyboard", 2500, 2),
            InvoiceLine("Mouse", 1200, 1),
        ],
    )

    print("Invoice subtotal:", invoice.subtotal())
    print("Invoice tax:", invoice.tax(STANDARD_TAX_RATE))
    print("Invoice total:", invoice.total(STANDARD_TAX_RATE))

    subsection("Comments and intent")
    print(
        "Net revenue:",
        calculate_net_revenue(100000, 7500),
    )

    subsection("Performance comparison")
    values = list(range(3000)) * 2
    slow_time = benchmark_function(slow_unique_values, values)
    fast_time = benchmark_function(fast_unique_values, values)

    print(f"Slow unique implementation: {slow_time:.6f} seconds")
    print(f"Set-based implementation: {fast_time:.6f} seconds")
    print("Unique values:", len(fast_unique_values(values)))

    demonstrate_edge_cases()
    run_tests()
    run_error_tests()

    section("Study checklist represented by this program")
    checklist = [
        "Functions should have focused responsibilities.",
        "Names should communicate intent.",
        "Duplication should be evaluated at the level of knowledge and responsibility.",
        "Comments should explain intent, constraints, or non-obvious decisions.",
        "Code smells are warning signs, not automatic proof of bad code.",
        "Refactoring should preserve intended behavior.",
        "Small functions and clear boundaries improve testability.",
        "Exceptions should communicate meaningful failure conditions.",
        "Abstraction should reduce complexity rather than merely hide it.",
        "Performance improvements should be based on actual constraints and measurements.",
    ]

    for item in checklist:
        print(f"[x] {item}")


if __name__ == "__main__":
    main()
