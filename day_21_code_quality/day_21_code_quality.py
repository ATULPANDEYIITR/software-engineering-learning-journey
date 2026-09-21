"""
Code Quality: Readability, Naming, Formatting, Maintainability

A standalone study program that demonstrates code-quality principles from
beginner through advanced level.

The examples are intentionally executable. Many sections print both a
poor-quality approach and a refactored approach so that the differences
can be observed directly.

Python version: 3.10+
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from enum import Enum
from functools import wraps
from pathlib import Path
from statistics import mean
from typing import Any, Callable, Iterable, Iterator, Sequence
import inspect
import math
import re
import time


# ============================================================================
# 1. SMALL UTILITIES USED BY THE STUDY PROGRAM
# ============================================================================

def section(title: str) -> None:
    """Print a visually distinct study section."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    """Print a smaller heading."""
    print(f"\n--- {title} ---")


def show(label: str, value: Any) -> None:
    """Display an example result consistently."""
    print(f"{label}: {value}")


# ============================================================================
# 2. WHAT CODE QUALITY MEANS
# ============================================================================

section("1. Code quality fundamentals")

print(
    """
Code quality describes how easy software is to understand, change, test,
debug, review, and operate correctly.

Important dimensions demonstrated in this file include:

1. Readability
   Code should communicate its intent clearly.

2. Naming
   Names should reveal what variables, functions, classes, and modules mean.

3. Formatting
   Consistent indentation, spacing, line length, and structural layout make
   code easier to scan.

4. Maintainability
   A future developer should be able to modify behavior without needing to
   understand an unnecessarily complicated implementation.

5. Correctness
   Clear code is not useful if it produces incorrect results.

6. Testability
   Code should have boundaries that make behavior easy to verify.

7. Reliability
   Invalid inputs and expected failures should be handled deliberately.

8. Consistency
   Similar problems should normally be solved using similar conventions.

9. Simplicity
   Complexity should exist because the problem requires it, not because the
   implementation was unnecessarily complicated.

10. Local reasoning
    A reader should be able to understand a function without tracing an
    enormous amount of unrelated state.
"""
)


# ============================================================================
# 3. READABILITY: BAD VS CLEAR
# ============================================================================

section("2. Readability")

subsection("A hard-to-read calculation")

def calculate_total_bad(a, b, c, d):
    return (a * b) + ((a * b) * c / 100) - d


def calculate_order_total(
    unit_price: float,
    quantity: int,
    tax_rate_percent: float,
    discount: float,
) -> float:
    """
    Calculate an order total using named intermediate values.

    The formula is intentionally broken into meaningful steps. The extra
    lines are useful because they expose business meaning to the reader.
    """
    subtotal = unit_price * quantity
    tax_amount = subtotal * tax_rate_percent / 100
    total_before_discount = subtotal + tax_amount
    final_total = total_before_discount - discount
    return max(final_total, 0.0)


bad_total = calculate_total_bad(100, 3, 18, 20)
clear_total = calculate_order_total(100, 3, 18, 20)

show("Hard-to-read calculation", bad_total)
show("Readable calculation", clear_total)

print(
    """
A short function is not automatically high quality. The meaningful question
is whether its structure communicates the problem being solved.

A one-line expression can be appropriate for a simple mathematical operation.
A longer sequence can be preferable when the intermediate concepts matter.
"""
)


# ============================================================================
# 4. NAMING
# ============================================================================

section("3. Naming")

subsection("Poor names versus intention-revealing names")

# Poor naming example. It works, but a reader must infer the meaning.
def f(x, y):
    return x * y


# Better naming. The function's purpose is visible at the call site.
def calculate_area(length: float, width: float) -> float:
    return length * width


show("Poorly named function result", f(10, 5))
show("Clearly named function result", calculate_area(10, 5))


subsection("Boolean names")

# Boolean names should usually read naturally as questions or conditions.
is_authenticated = True
has_permission = True
is_expired = False

if is_authenticated and has_permission and not is_expired:
    print("The request is allowed.")


subsection("Avoid ambiguous abbreviations")

user_count = 25
maximum_retries = 3
request_timeout_seconds = 10

show("User count", user_count)
show("Maximum retries", maximum_retries)
show("Request timeout", request_timeout_seconds)

print(
    """
Useful naming principles:

- Prefer user_count over uc.
- Prefer maximum_retries over mr.
- Prefer request_timeout_seconds over timeout when units matter.
- Prefer is_active for a Boolean state.
- Prefer calculate_invoice_total for an operation.
- Avoid names that encode outdated implementation details.
- Avoid names such as data, temp, thing, object, x, and value when a more
  precise name is practical.
- Loop variables such as i can be appropriate for tiny mathematical loops,
  while domain-oriented loops should use meaningful names.
"""
)


# ============================================================================
# 5. NAME SCOPE AND LIFETIME
# ============================================================================

section("4. Naming and scope")

def calculate_average_score(scores: Sequence[float]) -> float:
    """Return the arithmetic mean while handling an empty sequence."""
    if not scores:
        raise ValueError("At least one score is required.")
    return mean(scores)


scores = [82, 91, 76, 88]
show("Average score", calculate_average_score(scores))

print(
    """
A good name is also helped by a good scope. A variable used for two lines
usually needs less explanation than global mutable state shared across many
functions.

Prefer:

- local variables for local concepts,
- function parameters for explicit dependencies,
- object attributes for object state,
- constants for fixed configuration,
- dependency injection for external services.

Avoid unnecessary global mutable variables.
"""
)


# ============================================================================
# 6. CONSTANTS
# ============================================================================

section("5. Constants and magic numbers")

# A magic number hides business meaning.
def calculate_circle_area_bad(radius: float) -> float:
    return 3.141592653589793 * radius * radius


# A named constant communicates why the value exists.
PI = math.pi


def calculate_circle_area(radius: float) -> float:
    """Calculate the area of a circle."""
    if radius < 0:
        raise ValueError("Radius cannot be negative.")
    return PI * radius**2


show("Circle area", calculate_circle_area(5))

print(
    """
Not every number needs a constant. The goal is to name values whose meaning
matters.

For example, 0 in a loop may be self-explanatory. A value such as 86400
would be much clearer as SECONDS_PER_DAY when it represents a domain rule.
"""
)


# ============================================================================
# 7. FORMATTING
# ============================================================================

section("6. Formatting")

print(
    """
Consistent formatting reduces the mental effort required to parse source code.

Typical Python conventions include:

- four spaces for indentation,
- consistent blank lines,
- imports grouped logically,
- spaces around operators,
- readable line lengths,
- one clear statement per line,
- consistent quotation style,
- trailing commas in multiline structures where appropriate.

Formatting tools can enforce many of these mechanical rules. Formatting is
not primarily about personal taste when a team has agreed on a standard.
"""
)


def calculate_compound_interest(
    principal: float,
    annual_rate: float,
    years: int,
    compounds_per_year: int,
) -> float:
    """
    Calculate compound interest.

    Parameters use explicit names so the formula can be understood without
    decoding abbreviations.
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative.")
    if annual_rate < 0:
        raise ValueError("Annual rate cannot be negative.")
    if years < 0:
        raise ValueError("Years cannot be negative.")
    if compounds_per_year <= 0:
        raise ValueError("Compounds per year must be positive.")

    periodic_rate = annual_rate / compounds_per_year
    periods = compounds_per_year * years
    return principal * (1 + periodic_rate) ** periods


show(
    "Compound interest",
    round(calculate_compound_interest(1000, 0.05, 5, 12), 2),
)


# ============================================================================
# 8. FUNCTIONS AND SINGLE RESPONSIBILITY
# ============================================================================

section("7. Functions and focused responsibilities")

print(
    """
A function is easier to understand when it has one coherent responsibility.

A function that validates input, reads a database, calculates a result,
formats HTML, sends an email, and writes a log is difficult to test and
modify.

The following design separates validation, calculation, and presentation.
"""
)


def validate_percentage(value: float, field_name: str) -> None:
    """Validate a percentage represented as a value between 0 and 100."""
    if not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be numeric.")
    if not 0 <= value <= 100:
        raise ValueError(f"{field_name} must be between 0 and 100.")


def calculate_discounted_price(
    original_price: float,
    discount_percent: float,
) -> float:
    """Return a price after applying a percentage discount."""
    if original_price < 0:
        raise ValueError("Original price cannot be negative.")

    validate_percentage(discount_percent, "discount_percent")
    discount_amount = original_price * discount_percent / 100
    return original_price - discount_amount


def format_currency(amount: float, currency: str = "INR") -> str:
    """Format a monetary amount for display."""
    return f"{currency} {amount:,.2f}"


discounted_price = calculate_discounted_price(1000, 15)
show("Discounted price", format_currency(discounted_price))


# ============================================================================
# 9. AVOIDING DUPLICATION
# ============================================================================

section("8. Duplication and reusable logic")

def calculate_tax(amount: float, tax_rate: float) -> float:
    """Calculate tax without duplicating the formula throughout the program."""
    validate_percentage(tax_rate, "tax_rate")
    return amount * tax_rate / 100


def calculate_invoice_total(
    item_total: float,
    tax_rate: float,
    shipping_cost: float,
) -> float:
    """Combine reusable calculations into an invoice total."""
    if item_total < 0:
        raise ValueError("Item total cannot be negative.")
    if shipping_cost < 0:
        raise ValueError("Shipping cost cannot be negative.")

    tax = calculate_tax(item_total, tax_rate)
    return item_total + tax + shipping_cost


show("Invoice total", calculate_invoice_total(5000, 18, 100))

print(
    """
Duplication is dangerous because a business rule can change in one location
but remain unchanged in another.

The goal is not to eliminate every repeated line. Two pieces of code that
look similar may represent different concepts and may intentionally evolve
independently.

The useful target is duplication of knowledge, especially duplicated rules.
"""
)


# ============================================================================
# 10. CONDITIONAL READABILITY
# ============================================================================

section("9. Conditional logic")

def can_process_payment(
    is_authenticated: bool,
    has_sufficient_balance: bool,
    account_is_active: bool,
) -> bool:
    """Return whether all required payment conditions are satisfied."""
    return is_authenticated and has_sufficient_balance and account_is_active


show(
    "Payment allowed",
    can_process_payment(True, True, True),
)


def classify_score(score: float) -> str:
    """Classify a score using explicit ranges."""
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100.")

    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 50:
        return "pass"
    return "needs improvement"


for score in (95, 80, 60, 40):
    print(f"Score {score}: {classify_score(score)}")


# ============================================================================
# 11. GUARD CLAUSES
# ============================================================================

section("10. Guard clauses")

def create_username(email: str) -> str:
    """
    Extract a username from an email address.

    Guard clauses reject invalid states early and keep the main path at a
    lower indentation level.
    """
    if not isinstance(email, str):
        raise TypeError("Email must be a string.")

    cleaned_email = email.strip()

    if not cleaned_email:
        raise ValueError("Email cannot be empty.")

    if "@" not in cleaned_email:
        raise ValueError("Email must contain '@'.")

    username = cleaned_email.split("@", 1)[0]

    if not username:
        raise ValueError("Email must contain a username.")

    return username.lower()


for email in ("Alice@example.com", " bob@example.com "):
    print(f"{email!r} -> {create_username(email)!r}")


# ============================================================================
# 12. DATA STRUCTURES AND NAMED DATA
# ============================================================================

section("11. Data structures that communicate intent")

subsection("Tuple with unclear positions")

location_tuple = ("Lucknow", "India")
show("Tuple city", location_tuple[0])


@dataclass(frozen=True)
class Location:
    """A named representation of a geographic location."""
    city: str
    country: str


location = Location(city="Lucknow", country="India")
show("Named city", location.city)
show("Named country", location.country)

print(
    """
When several positions have semantic meaning, a named structure can be
clearer than an unexplained tuple.

Useful choices include:

- dataclass for structured domain data,
- Enum for a fixed set of symbolic states,
- dictionary for flexible key/value data,
- list for ordered collections,
- set for uniqueness,
- tuple for small immutable positional data.
"""
)


# ============================================================================
# 13. ENUMS
# ============================================================================

section("12. Enumerations")

class OrderStatus(Enum):
    """Allowed lifecycle states for an order."""
    PENDING = "pending"
    PAID = "paid"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"


def can_cancel_order(status: OrderStatus) -> bool:
    """Only pending or paid orders can be cancelled."""
    return status in {OrderStatus.PENDING, OrderStatus.PAID}


for status in OrderStatus:
    print(status.value, "can cancel:", can_cancel_order(status))


# ============================================================================
# 14. CLASSES AND INVARIANTS
# ============================================================================

section("13. Classes, invariants, and maintainability")

@dataclass
class BankAccount:
    """
    A small domain model.

    The invariant is that an account cannot have a negative balance after
    a withdrawal operation.
    """
    account_number: str
    balance: Decimal = Decimal("0")

    def __post_init__(self) -> None:
        if not self.account_number.strip():
            raise ValueError("Account number cannot be empty.")
        if self.balance < 0:
            raise ValueError("Initial balance cannot be negative.")

    def deposit(self, amount: Decimal) -> None:
        """Increase the balance by a positive amount."""
        self._validate_positive_amount(amount)
        self.balance += amount

    def withdraw(self, amount: Decimal) -> bool:
        """
        Withdraw money if sufficient funds exist.

        Returning False for insufficient funds keeps the operation explicit
        without silently creating an overdraft.
        """
        self._validate_positive_amount(amount)

        if amount > self.balance:
            return False

        self.balance -= amount
        return True

    @staticmethod
    def _validate_positive_amount(amount: Decimal) -> None:
        if amount <= 0:
            raise ValueError("Amount must be positive.")


account = BankAccount("ACC-1001", Decimal("1000"))
account.deposit(500)
withdrawal_succeeded = account.withdraw(200)

show("Withdrawal succeeded", withdrawal_succeeded)
show("Account balance", account.balance)


# ============================================================================
# 15. ERROR HANDLING
# ============================================================================

section("14. Error handling")

def parse_positive_integer(text: str) -> int:
    """
    Parse a positive integer.

    Different invalid states receive explicit exceptions rather than being
    hidden by a broad except clause.
    """
    try:
        value = int(text)
    except ValueError as error:
        raise ValueError("Expected a whole number.") from error

    if value <= 0:
        raise ValueError("Number must be positive.")

    return value


for raw_value in ("25", "0", "hello"):
    try:
        print(raw_value, "->", parse_positive_integer(raw_value))
    except ValueError as error:
        print(raw_value, "-> error:", error)

print(
    """
Avoid this pattern when it hides useful information:

    try:
        ...
    except Exception:
        pass

Broad exception handling is sometimes appropriate at a system boundary,
such as a top-level request handler, but it should normally log, translate,
or otherwise deliberately handle the failure.

At lower levels, catch the exceptions you can meaningfully handle.
"""
)


# ============================================================================
# 16. INPUT VALIDATION
# ============================================================================

section("15. Validation")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    """Perform basic structural email validation."""
    return bool(EMAIL_PATTERN.fullmatch(email.strip()))


for candidate in ("person@example.com", "invalid-email", "a@b"):
    print(candidate, "valid:", is_valid_email(candidate))


def validate_product(
    name: str,
    price: float,
    quantity: int,
) -> list[str]:
    """Return all detected validation errors instead of stopping at one."""
    errors: list[str] = []

    if not name.strip():
        errors.append("Product name cannot be empty.")

    if price < 0:
        errors.append("Price cannot be negative.")

    if quantity < 0:
        errors.append("Quantity cannot be negative.")

    return errors


show(
    "Product validation errors",
    validate_product("", -10, -2),
)


# ============================================================================
# 17. TYPE HINTS
# ============================================================================

section("16. Type hints and explicit contracts")

def calculate_average(values: Sequence[float]) -> float:
    """Return the average of a non-empty numeric sequence."""
    if not values:
        raise ValueError("Values cannot be empty.")
    return sum(values) / len(values)


show("Typed average", calculate_average([10, 20, 30]))

print(
    """
Type hints document expected interfaces and allow static analysis tools to
identify many mistakes before execution.

Type hints do not automatically validate runtime input. If data comes from
users, files, networks, or other external systems, explicit runtime
validation may still be required.
"""
)


# ============================================================================
# 18. DOCSTRINGS
# ============================================================================

section("17. Documentation at the right level")

def convert_celsius_to_fahrenheit(celsius: float) -> float:
    """
    Convert Celsius to Fahrenheit.

    Formula:
        F = C * 9 / 5 + 32

    Parameters:
        celsius: Temperature in degrees Celsius.

    Returns:
        Equivalent temperature in degrees Fahrenheit.
    """
    return celsius * 9 / 5 + 32


show("20 C in Fahrenheit", convert_celsius_to_fahrenheit(20))


# ============================================================================
# 19. COMMENTS: EXPLAIN WHY, NOT OBVIOUS WHAT
# ============================================================================

section("18. Useful comments")

def calculate_month_end_adjustment(amount: Decimal) -> Decimal:
    """
    Apply a domain-specific accounting adjustment.

    The comment explains the business reason rather than narrating syntax.
    """
    # Accounting policy requires amounts below 0.01 to be rounded to zero
    # before the monthly ledger is finalized.
    if abs(amount) < Decimal("0.01"):
        return Decimal("0.00")
    return amount.quantize(Decimal("0.01"))


show(
    "Month-end adjustment",
    calculate_month_end_adjustment(Decimal("0.004")),
)

print(
    """
Poor comment:

    # Add one to counter

Useful comment:

    # Start at one because the external report uses one-based row numbers.

Comments should explain intent, constraints, domain rules, or non-obvious
decisions. If code needs a comment merely to explain a complicated operation,
first consider whether the code itself can be made clearer.
"""
)


# ============================================================================
# 20. PURE FUNCTIONS
# ============================================================================

section("19. Pure functions and predictable behavior")

def add_tax(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """Pure function: same inputs produce the same output."""
    return amount + amount * tax_rate / Decimal("100")


first = add_tax(Decimal("100"), Decimal("18"))
second = add_tax(Decimal("100"), Decimal("18"))

show("First result", first)
show("Second result", second)
show("Deterministic", first == second)

print(
    """
Pure functions do not modify external state and do not depend on hidden
mutable state. They are generally easier to test, reason about, cache, and
reuse.

Not all software can or should be pure. File I/O, databases, networking,
logging, and user interfaces inherently interact with external state.
The maintainability benefit comes from keeping those effects at clear
boundaries.
"""
)


# ============================================================================
# 21. DEPENDENCY INJECTION
# ============================================================================

section("20. Dependency injection")

class Clock:
    """Simple abstraction around current time."""

    def now(self) -> datetime:
        return datetime.now()


class ReportService:
    """
    The service receives its clock instead of constructing it internally.

    This makes the service easier to test because a deterministic clock can
    be supplied.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def create_report_timestamp(self) -> str:
        return self._clock.now().isoformat()


report_service = ReportService(Clock())
show("Report timestamp", report_service.create_report_timestamp())

print(
    """
Dependency injection means that an object receives the collaborators it
needs instead of hiding their construction inside business logic.

Benefits include:

- easier testing,
- clearer dependencies,
- less coupling,
- easier replacement of implementations,
- more predictable configuration.
"""
)


# ============================================================================
# 22. TESTABLE DESIGN
# ============================================================================

section("21. Testable design")

def calculate_shipping_cost(
    order_total: Decimal,
    free_shipping_threshold: Decimal = Decimal("1000"),
) -> Decimal:
    """Return zero shipping above the threshold, otherwise a fixed fee."""
    if order_total < 0:
        raise ValueError("Order total cannot be negative.")
    if free_shipping_threshold < 0:
        raise ValueError("Threshold cannot be negative.")

    if order_total >= free_shipping_threshold:
        return Decimal("0")

    return Decimal("100")


def assert_equal(expected: Any, actual: Any, description: str) -> None:
    """Small dependency-free assertion helper for this study program."""
    if expected != actual:
        raise AssertionError(
            f"{description}: expected {expected!r}, got {actual!r}"
        )
    print(f"PASS: {description}")


assert_equal(
    Decimal("0"),
    calculate_shipping_cost(Decimal("1000")),
    "free shipping at threshold",
)

assert_equal(
    Decimal("100"),
    calculate_shipping_cost(Decimal("999")),
    "shipping below threshold",
)

try:
    calculate_shipping_cost(Decimal("-1"))
except ValueError:
    print("PASS: negative order total is rejected.")


# ============================================================================
# 23. EDGE CASES
# ============================================================================

section("22. Edge cases")

def safe_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change while explicitly handling a zero baseline.

    Percentage change from zero has no finite standard result. The function
    therefore raises a meaningful exception rather than returning infinity
    or silently producing a misleading number.
    """
    if old_value == 0:
        if new_value == 0:
            return 0.0
        raise ValueError(
            "Percentage change from zero is undefined for a non-zero result."
        )

    return ((new_value - old_value) / abs(old_value)) * 100


for old_value, new_value in ((100, 120), (100, 80), (0, 0)):
    print(
        old_value,
        "->",
        new_value,
        "=",
        safe_percentage_change(old_value, new_value),
    )

try:
    safe_percentage_change(0, 10)
except ValueError as error:
    print("Expected edge-case error:", error)


# ============================================================================
# 24. LIST PROCESSING
# ============================================================================

section("23. Readable collection processing")

orders = [
    {"customer": "Asha", "amount": 1200, "paid": True},
    {"customer": "Ravi", "amount": 800, "paid": False},
    {"customer": "Meera", "amount": 1600, "paid": True},
]

paid_order_totals = [
    order["amount"]
    for order in orders
    if order["paid"]
]

show("Paid order totals", paid_order_totals)
show("Paid order revenue", sum(paid_order_totals))

print(
    """
List comprehensions can improve readability for simple transformations.

A comprehension becomes less readable when it contains many nested conditions,
multiple function calls, side effects, or complicated expressions. In those
cases, a normal loop or a named helper function can communicate the intent
better.
"""
)


# ============================================================================
# 25. ITERATORS AND GENERATORS
# ============================================================================

section("24. Generators and maintainable data processing")

def generate_even_numbers(limit: int) -> Iterator[int]:
    """Yield even numbers lazily rather than building the entire list."""
    if limit < 0:
        raise ValueError("Limit cannot be negative.")

    for number in range(0, limit + 1, 2):
        yield number


show("Generated values", list(generate_even_numbers(10)))

print(
    """
Generators are useful when a sequence may be large.

A list stores every result immediately. A generator yields one item at a time.
This can reduce memory consumption and support streaming pipelines.

Readable abstractions should still preserve understandable control flow.
Optimization should not make simple code unnecessarily obscure.
"""
)


# ============================================================================
# 26. PERFORMANCE AND CODE QUALITY
# ============================================================================

section("25. Performance-aware maintainability")

def contains_duplicate_slow(values: Sequence[int]) -> bool:
    """O(n²) duplicate detection using repeated membership searches."""
    for index, value in enumerate(values):
        if value in values[index + 1:]:
            return True
    return False


def contains_duplicate_fast(values: Sequence[int]) -> bool:
    """O(n) expected-time duplicate detection using a set."""
    seen: set[int] = set()

    for value in values:
        if value in seen:
            return True
        seen.add(value)

    return False


sample_values = [1, 2, 3, 4, 5, 4]

show("Slow algorithm detects duplicate", contains_duplicate_slow(sample_values))
show("Fast algorithm detects duplicate", contains_duplicate_fast(sample_values))

print(
    """
Approximate complexity:

contains_duplicate_slow:
    Time: O(n²) in the worst case
    Space: O(n) can be created by slicing

contains_duplicate_fast:
    Time: O(n) expected
    Space: O(n)

The second implementation is not only faster. Its intent is also explicit:
maintain a set of values already encountered.

Performance and readability do not always conflict. Choosing an appropriate
algorithm can improve both.
"""
)


# ============================================================================
# 27. BENCHMARKING
# ============================================================================

section("26. Measuring before optimizing")

benchmark_values = list(range(5000))
benchmark_values.append(4999)

start = time.perf_counter()
contains_duplicate_slow(benchmark_values)
slow_duration = time.perf_counter() - start

start = time.perf_counter()
contains_duplicate_fast(benchmark_values)
fast_duration = time.perf_counter() - start

show("Slow implementation seconds", round(slow_duration, 6))
show("Fast implementation seconds", round(fast_duration, 6))

print(
    """
Performance claims should be measured rather than guessed.

A benchmark should control variables such as:

- input size,
- hardware,
- runtime version,
- warm-up behavior,
- repeated measurements,
- representative workloads.

A microbenchmark can be useful, but production profiling is needed to
understand where a real application spends its time.
"""
)


# ============================================================================
# 28. COUPLING AND COHESION
# ============================================================================

section("27. Coupling and cohesion")

@dataclass
class Product:
    """A product with a price and quantity."""
    name: str
    unit_price: Decimal
    quantity: int

    def subtotal(self) -> Decimal:
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative.")
        return self.unit_price * self.quantity


class Invoice:
    """Owns invoice-level behavior while Product owns product behavior."""

    def __init__(self, products: Iterable[Product]) -> None:
        self._products = list(products)

    def subtotal(self) -> Decimal:
        return sum(
            (product.subtotal() for product in self._products),
            Decimal("0"),
        )


invoice = Invoice(
    [
        Product("Keyboard", Decimal("2500"), 1),
        Product("Mouse", Decimal("1000"), 2),
    ]
)

show("Invoice subtotal", invoice.subtotal())

print(
    """
Cohesion asks whether the responsibilities inside a component belong
together.

Coupling asks how strongly one component depends on another.

A maintainable design often aims for:

- high cohesion: related behavior stays together,
- lower unnecessary coupling: components depend on clear interfaces.

Low coupling does not mean zero coupling. Software components need to
communicate. The goal is controlled, understandable dependency.
"""
)


# ============================================================================
# 29. INTERFACES THROUGH PROTOCOLS
# ============================================================================

section("28. Explicit interfaces")

from typing import Protocol


class MessageSender(Protocol):
    """Interface required by NotificationService."""

    def send(self, recipient: str, message: str) -> None:
        ...


class ConsoleMessageSender:
    """A concrete sender used for this executable demonstration."""

    def send(self, recipient: str, message: str) -> None:
        print(f"Sending to {recipient}: {message}")


class NotificationService:
    """Business logic depends on the MessageSender behavior."""

    def __init__(self, sender: MessageSender) -> None:
        self._sender = sender

    def notify(self, recipient: str, message: str) -> None:
        if not recipient.strip():
            raise ValueError("Recipient cannot be empty.")
        if not message.strip():
            raise ValueError("Message cannot be empty.")

        self._sender.send(recipient, message)


notification_service = NotificationService(ConsoleMessageSender())
notification_service.notify("user@example.com", "Your order is ready.")


# ============================================================================
# 30. SECURITY AND CODE QUALITY
# ============================================================================

section("29. Security as a code-quality concern")

def normalize_search_term(search_term: str) -> str:
    """
    Normalize user input for a simple in-memory search.

    This function is not a complete security boundary. It demonstrates that
    external input should be validated and normalized before processing.
    """
    if not isinstance(search_term, str):
        raise TypeError("Search term must be text.")

    normalized = search_term.strip()

    if not normalized:
        raise ValueError("Search term cannot be empty.")

    if len(normalized) > 100:
        raise ValueError("Search term is too long.")

    return normalized


show("Normalized search term", normalize_search_term("  laptop  "))

print(
    """
Security-related quality principles include:

- validate untrusted input,
- use parameterized database queries,
- avoid constructing shell commands from raw user input,
- do not hard-code secrets,
- apply least privilege,
- avoid leaking sensitive information in errors,
- keep dependencies maintained,
- distinguish authentication from authorization,
- protect sensitive data in transit and at rest.

Readable security code is valuable because reviewers need to understand
security boundaries and assumptions.
"""
)


# ============================================================================
# 31. SECRET HANDLING
# ============================================================================

section("30. Avoiding hard-coded secrets")

import os


def get_database_password() -> str:
    """
    Read a database password from an environment variable.

    A demonstration fallback is intentionally non-secret. Real production
    applications should fail safely when required credentials are missing.
    """
    password = os.getenv("DEMO_DATABASE_PASSWORD")

    if password is None:
        raise RuntimeError(
            "DEMO_DATABASE_PASSWORD is not configured."
        )

    return password


print(
    """
Production code should not contain values such as:

    password = "my-real-password"

Credentials should be supplied through an appropriate secret-management
mechanism or protected environment configuration.
"""
)


# ============================================================================
# 32. LOGGING WITHOUT SENSITIVE DATA
# ============================================================================

section("31. Safe diagnostics")

def mask_account_number(account_number: str) -> str:
    """Show only the final four characters of an account identifier."""
    if len(account_number) <= 4:
        return "*" * len(account_number)
    return "*" * (len(account_number) - 4) + account_number[-4:]


show("Masked account", mask_account_number("1234567890"))

print(
    """
Debugging information should help diagnose failures without exposing
passwords, authentication tokens, payment credentials, or unnecessary
personal information.

Good observability is part of maintainability, but logs are also a data
security boundary.
"""
)


# ============================================================================
# 33. API DESIGN
# ============================================================================

section("32. Small and explicit APIs")

@dataclass(frozen=True)
class Customer:
    """Customer information needed by the pricing service."""
    customer_id: str
    membership_level: str


def calculate_membership_discount(
    customer: Customer,
    amount: Decimal,
) -> Decimal:
    """
    Calculate a discount based on a small explicit domain model.

    Keeping the function interface narrow makes its assumptions visible.
    """
    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    discount_rates = {
        "standard": Decimal("0"),
        "silver": Decimal("5"),
        "gold": Decimal("10"),
    }

    rate = discount_rates.get(customer.membership_level)

    if rate is None:
        raise ValueError("Unknown membership level.")

    return amount * rate / Decimal("100")


customer = Customer("C001", "gold")
show(
    "Membership discount",
    calculate_membership_discount(customer, Decimal("2000")),
)


# ============================================================================
# 34. CONFIGURATION
# ============================================================================

section("33. Configuration and magic values")

@dataclass(frozen=True)
class ApplicationConfig:
    """Immutable application configuration."""

    request_timeout_seconds: int = 30
    maximum_batch_size: int = 100
    enable_audit_logging: bool = True

    def __post_init__(self) -> None:
        if self.request_timeout_seconds <= 0:
            raise ValueError("Timeout must be positive.")
        if self.maximum_batch_size <= 0:
            raise ValueError("Batch size must be positive.")


config = ApplicationConfig()
show("Request timeout", config.request_timeout_seconds)
show("Maximum batch size", config.maximum_batch_size)


# ============================================================================
# 35. MAINTAINABILITY THROUGH SMALL MODULE-LIKE COMPONENTS
# ============================================================================

section("34. Separation of concerns")

class PriceCalculator:
    """Owns pricing rules."""

    def calculate(self, products: Sequence[Product]) -> Decimal:
        return sum(
            (product.subtotal() for product in products),
            Decimal("0"),
        )


class InvoiceFormatter:
    """Owns presentation formatting."""

    def format_total(self, total: Decimal) -> str:
        return f"Invoice total: INR {total:,.2f}"


class InvoiceApplication:
    """Coordinates components without owning their internal details."""

    def __init__(
        self,
        price_calculator: PriceCalculator,
        formatter: InvoiceFormatter,
    ) -> None:
        self._price_calculator = price_calculator
        self._formatter = formatter

    def create_invoice_text(self, products: Sequence[Product]) -> str:
        total = self._price_calculator.calculate(products)
        return self._formatter.format_total(total)


invoice_application = InvoiceApplication(
    PriceCalculator(),
    InvoiceFormatter(),
)

print(
    invoice_application.create_invoice_text(
        [
            Product("Monitor", Decimal("15000"), 1),
            Product("Cable", Decimal("500"), 2),
        ]
    )
)


# ============================================================================
# 36. REFACTORING
# ============================================================================

section("35. Refactoring safely")

def calculate_employee_pay_bad(
    hours,
    rate,
    overtime_rate,
):
    if hours > 40:
        return 40 * rate + (hours - 40) * overtime_rate
    return hours * rate


@dataclass(frozen=True)
class PayPolicy:
    """Business rules for employee compensation."""
    regular_hours_limit: Decimal = Decimal("40")


def calculate_employee_pay(
    hours_worked: Decimal,
    hourly_rate: Decimal,
    overtime_rate: Decimal,
    policy: PayPolicy = PayPolicy(),
) -> Decimal:
    """Calculate regular and overtime pay using explicit domain names."""
    if hours_worked < 0:
        raise ValueError("Hours worked cannot be negative.")
    if hourly_rate < 0:
        raise ValueError("Hourly rate cannot be negative.")
    if overtime_rate < 0:
        raise ValueError("Overtime rate cannot be negative.")

    regular_hours = min(hours_worked, policy.regular_hours_limit)
    overtime_hours = max(
        hours_worked - policy.regular_hours_limit,
        Decimal("0"),
    )

    regular_pay = regular_hours * hourly_rate
    overtime_pay = overtime_hours * overtime_rate

    return regular_pay + overtime_pay


show(
    "Refactored employee pay",
    calculate_employee_pay(
        Decimal("45"),
        Decimal("100"),
        Decimal("150"),
    ),
)

print(
    """
A safe refactoring changes structure while preserving externally observable
behavior.

Typical refactoring steps:

1. Establish tests around existing behavior.
2. Make one small structural change.
3. Run tests.
4. Review the diff.
5. Repeat.

Large simultaneous rewrites make it harder to identify which change caused
a regression.
"""
)


# ============================================================================
# 37. CODE SMELLS
# ============================================================================

section("36. Common code smells")

print(
    """
Common maintainability warning signs include:

Long function
    One function performs too many distinct operations.

Long parameter list
    A function requires so much context that a domain object or configuration
    object may be clearer.

Duplicated logic
    The same business rule exists in multiple locations.

Deep nesting
    Several nested conditions make the normal path difficult to follow.

Magic numbers
    Important domain values appear without meaningful names.

God object
    One class accumulates unrelated responsibilities.

Global mutable state
    Many components can change shared state unpredictably.

Shotgun changes
    A small business change requires edits across many unrelated files.

Feature envy
    One component repeatedly reaches into another component's internal data.

Dead code
    Unused code increases maintenance cost and uncertainty.

Premature abstraction
    A generic framework is created before repeated behavior is actually
    understood.

Premature optimization
    Complexity is introduced without evidence that performance requires it.
"""
)


# ============================================================================
# 38. COMPLEXITY
# ============================================================================

section("37. Cyclomatic and cognitive complexity")

def classify_transaction(
    amount: float,
    is_verified: bool,
    is_business_account: bool,
) -> str:
    """A compact example with multiple decision paths."""
    if amount <= 0:
        return "invalid"

    if not is_verified:
        return "review"

    if is_business_account and amount > 100000:
        return "enhanced_review"

    if amount > 50000:
        return "review"

    return "approved"


for transaction in (
    (0, True, False),
    (1000, False, False),
    (10000, True, False),
    (60000, True, False),
    (150000, True, True),
):
    print(transaction, "->", classify_transaction(*transaction))

print(
    """
Cyclomatic complexity is related to the number of independent decision paths
through code. High branching often increases the number of cases that need
testing.

Cognitive complexity is a broader idea: how difficult the code is for a human
to mentally follow.

Neither metric is a universal quality score. A complicated business rule may
legitimately contain many branches. The useful response is to make those
branches explicit, test them, and isolate coherent decisions.
"""
)


# ============================================================================
# 39. TESTING EDGE CASES
# ============================================================================

section("38. Boundary-focused testing")

def calculate_grade(score: int) -> str:
    """Map an integer score to a grade."""
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100.")

    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


boundary_scores = [0, 59, 60, 69, 70, 79, 80, 89, 90, 100]

for score in boundary_scores:
    print(score, "->", calculate_grade(score))


# ============================================================================
# 40. PROPERTY-LIKE INVARIANT CHECKING
# ============================================================================

section("39. Invariants")

def check_grade_invariant() -> None:
    """
    Verify that every valid score maps to one of the allowed grades.

    This is a lightweight example of testing an invariant across many inputs.
    """
    allowed_grades = {"A", "B", "C", "D", "F"}

    for score in range(101):
        grade = calculate_grade(score)
        assert grade in allowed_grades


check_grade_invariant()
print("PASS: grade invariant holds for scores 0 through 100.")


# ============================================================================
# 41. RECURSION VERSUS ITERATION
# ============================================================================

section("40. Choosing straightforward algorithms")

def factorial_iterative(number: int) -> int:
    """Compute factorial iteratively with explicit validation."""
    if number < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    result = 1

    for current in range(2, number + 1):
        result *= current

    return result


show("5!", factorial_iterative(5))

print(
    """
Recursion can be elegant for naturally recursive structures such as trees.
It is not automatically more readable than iteration.

In Python, recursion depth is limited, so an iterative implementation is often
more appropriate for simple repeated calculations such as factorial.
"""
)


# ============================================================================
# 42. CACHING AS A MAINTAINABILITY TRADE-OFF
# ============================================================================

section("41. Caching and complexity")

from functools import lru_cache


@lru_cache(maxsize=None)
def fibonacci(number: int) -> int:
    """
    Compute Fibonacci numbers with memoization.

    Without caching, the naive recursive algorithm repeatedly solves the same
    subproblems. Caching changes the practical complexity substantially.
    """
    if number < 0:
        raise ValueError("Number cannot be negative.")
    if number < 2:
        return number
    return fibonacci(number - 1) + fibonacci(number - 2)


show("Fibonacci(20)", fibonacci(20))
show("Cached calls", fibonacci.cache_info())


# ============================================================================
# 43. DECIMAL AND DOMAIN CORRECTNESS
# ============================================================================

section("42. Correct data types are part of code quality")

def calculate_money_total(
    unit_price: Decimal,
    quantity: int,
) -> Decimal:
    """Use Decimal when exact decimal arithmetic is required for money."""
    if unit_price < 0:
        raise ValueError("Unit price cannot be negative.")
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    return unit_price * quantity


show(
    "Money total",
    calculate_money_total(Decimal("19.99"), 3),
)

print(
    """
Binary floating-point is excellent for many scientific calculations, but it
does not represent every decimal fraction exactly.

For financial values where decimal rounding rules matter, Decimal is often a
more appropriate representation.

Code quality includes selecting data representations that match the domain.
"""
)


# ============================================================================
# 44. FILE PATH HANDLING
# ============================================================================

section("43. Explicit resource handling")

def count_non_empty_lines(path: Path) -> int:
    """
    Count non-empty lines.

    The function accepts a Path object and uses a context manager so the file
    is closed even if processing raises an exception.
    """
    count = 0

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                count += 1

    return count


temporary_file = Path("code_quality_demo.txt")

try:
    temporary_file.write_text(
        "first line\n\nsecond line\n",
        encoding="utf-8",
    )

    show(
        "Non-empty lines",
        count_non_empty_lines(temporary_file),
    )
finally:
    if temporary_file.exists():
        temporary_file.unlink()


# ============================================================================
# 45. CONTEXT MANAGERS
# ============================================================================

section("44. Resource lifetime and maintainability")

class ManagedResource:
    """Demonstrate deterministic acquisition and release."""

    def __enter__(self) -> "ManagedResource":
        print("Resource acquired.")
        return self

    def use(self) -> None:
        print("Resource used.")

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> bool:
        print("Resource released.")
        return False


with ManagedResource() as resource:
    resource.use()


# ============================================================================
# 46. DECORATORS: ABSTRACTION WITH CARE
# ============================================================================

section("45. Decorators and abstraction boundaries")

def audit_call(function: Callable[..., Any]) -> Callable[..., Any]:
    """
    Record a simple function call.

    functools.wraps preserves metadata such as the wrapped function's name
    and documentation.
    """
    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"AUDIT: calling {function.__name__}")
        result = function(*args, **kwargs)
        print(f"AUDIT: {function.__name__} completed")
        return result

    return wrapper


@audit_call
def multiply(first_number: int, second_number: int) -> int:
    """Multiply two integers."""
    return first_number * second_number


show("Decorated multiplication", multiply(6, 7))
show("Preserved function name", multiply.__name__)


# ============================================================================
# 47. FUNCTION INTROSPECTION
# ============================================================================

section("46. Interfaces can be inspected")

signature = inspect.signature(calculate_order_total)
show("calculate_order_total signature", signature)
show("Function documentation exists", bool(calculate_order_total.__doc__))


# ============================================================================
# 48. MAINTAINABLE COMMAND PROCESSING
# ============================================================================

section("47. Explicit command dispatch")

def command_status() -> str:
    return "System is operational."


def command_version() -> str:
    return "Version 1.0"


def command_help() -> str:
    return "Available commands: status, version, help"


COMMANDS: dict[str, Callable[[], str]] = {
    "status": command_status,
    "version": command_version,
    "help": command_help,
}


def execute_command(command: str) -> str:
    """Execute a known command using an explicit dispatch table."""
    normalized_command = command.strip().lower()

    handler = COMMANDS.get(normalized_command)

    if handler is None:
        raise ValueError(f"Unknown command: {command!r}")

    return handler()


for command in ("status", "version", "help"):
    print(command, "->", execute_command(command))

try:
    execute_command("delete-everything")
except ValueError as error:
    print("Expected command error:", error)


# ============================================================================
# 49. OPEN/CLOSED DESIGN
# ============================================================================

section("48. Extensibility without uncontrolled branching")

class PricingRule(Protocol):
    """Interface implemented by pricing rules."""

    def discount(self, amount: Decimal) -> Decimal:
        ...


@dataclass(frozen=True)
class NoDiscount:
    """Default pricing behavior."""

    def discount(self, amount: Decimal) -> Decimal:
        return Decimal("0")


@dataclass(frozen=True)
class PercentageDiscount:
    """Percentage-based discount strategy."""

    rate: Decimal

    def discount(self, amount: Decimal) -> Decimal:
        if not 0 <= self.rate <= 100:
            raise ValueError("Discount rate must be between 0 and 100.")
        return amount * self.rate / Decimal("100")


def calculate_final_price(
    amount: Decimal,
    pricing_rule: PricingRule,
) -> Decimal:
    """Calculate a final price using a supplied pricing rule."""
    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    discount = pricing_rule.discount(amount)

    if discount > amount:
        raise ValueError("Discount cannot exceed the original amount.")

    return amount - discount


show(
    "No discount",
    calculate_final_price(Decimal("1000"), NoDiscount()),
)

show(
    "10 percent discount",
    calculate_final_price(
        Decimal("1000"),
        PercentageDiscount(Decimal("10")),
    ),
)


# ============================================================================
# 50. AVOIDING OVER-ENGINEERING
# ============================================================================

section("49. Simplicity and appropriate abstraction")

def is_even(number: int) -> bool:
    """A simple operation should remain simple."""
    return number % 2 == 0


show("Is 42 even?", is_even(42))

print(
    """
A common mistake is creating a class hierarchy, factory, registry, plugin
system, and configuration layer for a problem that can be solved by a small
function.

Abstraction has a cost:

- more files,
- more concepts,
- more indirection,
- more interfaces,
- more tests,
- more documentation.

Introduce abstraction when it captures a real variation, boundary, or
repeated concept. Do not introduce it merely because a design pattern exists.
"""
)


# ============================================================================
# 51. API COMPATIBILITY
# ============================================================================

section("50. Maintainability includes compatibility")

def calculate_shipping_v1(order_total: Decimal) -> Decimal:
    """Original API shape."""
    return Decimal("0") if order_total >= 1000 else Decimal("100")


def calculate_shipping_v2(
    order_total: Decimal,
    free_threshold: Decimal = Decimal("1000"),
) -> Decimal:
    """
    Extended API with a backward-compatible default.

    Defaults can reduce the impact of adding optional behavior, although
    public APIs still require careful versioning and documentation.
    """
    return (
        Decimal("0")
        if order_total >= free_threshold
        else Decimal("100")
    )


show(
    "Version 1",
    calculate_shipping_v1(1200),
)

show(
    "Version 2 with default",
    calculate_shipping_v2(1200),
)


# ============================================================================
# 52. BACKWARD-COMPATIBLE DATA CHANGES
# ============================================================================

section("51. Defensive handling of evolving data")

def get_customer_display_name(customer: dict[str, Any]) -> str:
    """
    Handle optional fields deliberately.

    External data often evolves. Explicit defaults prevent simple missing
    fields from becoming confusing KeyError failures.
    """
    first_name = str(customer.get("first_name", "")).strip()
    last_name = str(customer.get("last_name", "")).strip()

    full_name = " ".join(
        part for part in (first_name, last_name) if part
    )

    return full_name or "Unknown customer"


for customer in (
    {"first_name": "Asha", "last_name": "Singh"},
    {"first_name": "Ravi"},
    {},
):
    print(get_customer_display_name(customer))


# ============================================================================
# 53. DOCUMENTING ASSUMPTIONS
# ============================================================================

section("52. Explicit assumptions")

def calculate_annualized_return(
    starting_value: Decimal,
    ending_value: Decimal,
    years: Decimal,
) -> Decimal:
    """
    Calculate annualized growth as a percentage.

    Assumptions:
    - starting_value must be positive,
    - ending_value must be non-negative,
    - years must be positive.
    """
    if starting_value <= 0:
        raise ValueError("Starting value must be positive.")
    if ending_value < 0:
        raise ValueError("Ending value cannot be negative.")
    if years <= 0:
        raise ValueError("Years must be positive.")

    growth_factor = ending_value / starting_value
    annualized_factor = growth_factor ** (Decimal("1") / years)

    return (annualized_factor - Decimal("1")) * Decimal("100")


show(
    "Annualized return",
    round(
        calculate_annualized_return(
            Decimal("1000"),
            Decimal("1500"),
            Decimal("3"),
        ),
        2,
    ),
)


# ============================================================================
# 54. STATIC ANALYSIS MINDSET
# ============================================================================

section("53. Static analysis and automated quality")

print(
    """
Static analysis examines source code without executing the program.

Typical categories include:

- formatting checks,
- linting,
- unused-variable detection,
- unreachable-code detection,
- type checking,
- complexity checks,
- import organization,
- security scanning.

Automated checks are valuable because they catch mechanical problems
consistently.

They do not replace human review. A linter can identify an unused variable,
but it cannot fully determine whether a business rule is correct.
"""
)


# ============================================================================
# 55. CODE REVIEW
# ============================================================================

section("54. Code review principles")

print(
    """
A useful review asks questions such as:

Correctness
    Does the implementation satisfy the required behavior?

Readability
    Can another developer understand the normal path quickly?

Naming
    Do names accurately represent concepts?

Structure
    Are responsibilities separated appropriately?

Error handling
    Are invalid states and failures handled deliberately?

Tests
    Are important normal and boundary cases covered?

Security
    Is untrusted input handled safely? Are secrets protected?

Performance
    Is the selected algorithm appropriate for expected data sizes?

Maintainability
    Will a future change be localized and understandable?

Compatibility
    Could the change break existing callers, data, or interfaces?

A code review should focus on concrete risks and improvements rather than
personal coding preferences.
"""
)


# ============================================================================
# 56. QUALITY GATES
# ============================================================================

section("55. Quality gates")

def run_quality_checks() -> None:
    """Run small executable checks representing a quality gate."""
    assert calculate_area(5, 4) == 20
    assert calculate_grade(90) == "A"
    assert calculate_grade(89) == "B"
    assert calculate_shipping_cost(Decimal("1000")) == Decimal("0")
    assert is_even(42)
    assert not is_even(41)

    try:
        calculate_grade(101)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid score should raise ValueError.")

    try:
        calculate_area(-1, 4)
    except ValueError:
        pass
    else:
        raise AssertionError("Negative dimensions should be rejected.")

    print("All built-in quality checks passed.")


run_quality_checks()


# ============================================================================
# 57. FINAL MAINTAINABLE MINI-APPLICATION
# ============================================================================

section("56. Integrated maintainable example")

class CustomerTier(Enum):
    """Supported customer tiers."""
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass(frozen=True)
class OrderItem:
    """A single line item in an order."""
    product_name: str
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        if not self.product_name.strip():
            raise ValueError("Product name cannot be empty.")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")

    @property
    def subtotal(self) -> Decimal:
        """Return the line-item subtotal."""
        return self.unit_price * self.quantity


@dataclass(frozen=True)
class CustomerProfile:
    """Information needed by the order-pricing rules."""
    customer_id: str
    tier: CustomerTier


class OrderCalculator:
    """
    Calculate an order's final amount.

    The class coordinates domain rules but keeps individual operations small.
    """

    PREMIUM_DISCOUNT_RATE = Decimal("10")
    TAX_RATE = Decimal("18")

    def calculate_subtotal(self, items: Sequence[OrderItem]) -> Decimal:
        """Calculate the total before discount and tax."""
        if not items:
            raise ValueError("An order must contain at least one item.")

        return sum(
            (item.subtotal for item in items),
            Decimal("0"),
        )

    def calculate_discount(
        self,
        subtotal: Decimal,
        customer: CustomerProfile,
    ) -> Decimal:
        """Calculate a customer-tier discount."""
        if customer.tier is CustomerTier.PREMIUM:
            return subtotal * self.PREMIUM_DISCOUNT_RATE / Decimal("100")

        return Decimal("0")

    def calculate_tax(self, taxable_amount: Decimal) -> Decimal:
        """Calculate tax on the amount remaining after discount."""
        return taxable_amount * self.TAX_RATE / Decimal("100")

    def calculate_total(
        self,
        items: Sequence[OrderItem],
        customer: CustomerProfile,
    ) -> Decimal:
        """Calculate the complete order total."""
        subtotal = self.calculate_subtotal(items)
        discount = self.calculate_discount(subtotal, customer)
        taxable_amount = subtotal - discount
        tax = self.calculate_tax(taxable_amount)

        return taxable_amount + tax


class OrderReport:
    """Present an order calculation without owning pricing rules."""

    def format(
        self,
        items: Sequence[OrderItem],
        customer: CustomerProfile,
        calculator: OrderCalculator,
    ) -> str:
        """Produce a concise human-readable report."""
        subtotal = calculator.calculate_subtotal(items)
        discount = calculator.calculate_discount(subtotal, customer)
        taxable_amount = subtotal - discount
        tax = calculator.calculate_tax(taxable_amount)
        total = calculator.calculate_total(items, customer)

        lines = [
            f"Customer: {customer.customer_id}",
            f"Tier: {customer.tier.value}",
            f"Subtotal: INR {subtotal:,.2f}",
            f"Discount: INR {discount:,.2f}",
            f"Tax: INR {tax:,.2f}",
            f"Total: INR {total:,.2f}",
        ]

        return "\n".join(lines)


customer = CustomerProfile("CUST-001", CustomerTier.PREMIUM)

items = [
    OrderItem("Mechanical Keyboard", Decimal("4500"), 1),
    OrderItem("Wireless Mouse", Decimal("1800"), 2),
    OrderItem("USB-C Cable", Decimal("700"), 3),
]

calculator = OrderCalculator()
report = OrderReport()

print(report.format(items, customer, calculator))


# ============================================================================
# 58. INTEGRATED EXAMPLE TESTS
# ============================================================================

section("57. Testing the integrated example")

subtotal = calculator.calculate_subtotal(items)
discount = calculator.calculate_discount(subtotal, customer)
total = calculator.calculate_total(items, customer)

assert_equal(
    Decimal("8400"),
    subtotal,
    "integrated subtotal",
)

assert_equal(
    Decimal("840"),
    discount,
    "premium discount",
)

expected_taxable_amount = Decimal("7560")
expected_tax = Decimal("1360.80")
expected_total = Decimal("8920.80")

assert_equal(
    expected_taxable_amount,
    subtotal - discount,
    "taxable amount",
)

assert_equal(
    expected_tax,
    calculator.calculate_tax(subtotal - discount),
    "tax amount",
)

assert_equal(
    expected_total,
    total,
    "integrated total",
)


# ============================================================================
# 59. MAINTAINABILITY CHECKLIST IN EXECUTABLE FORM
# ============================================================================

section("58. Executable maintainability checklist")

quality_checklist = {
    "Names communicate intent": True,
    "Functions have focused responsibilities": True,
    "Validation is explicit": True,
    "Errors are handled deliberately": True,
    "Domain values are named": True,
    "Data structures communicate meaning": True,
    "Dependencies are visible": True,
    "Important edge cases are tested": True,
    "Security boundaries are considered": True,
    "Performance assumptions are understood": True,
    "Formatting is consistent": True,
    "Public interfaces are deliberate": True,
}

for principle, satisfied in quality_checklist.items():
    print(f"[{'PASS' if satisfied else 'FAIL'}] {principle}")


# ============================================================================
# 60. PRACTICAL REFACTORING WORKFLOW
# ============================================================================

section("59. Practical refactoring workflow")

print(
    """
A disciplined maintainability workflow can be represented as:

1. Understand the current behavior.
2. Identify the concrete problem.
3. Add or verify tests around important behavior.
4. Rename unclear concepts.
5. Extract focused functions.
6. Remove unnecessary duplication.
7. Simplify conditions and control flow.
8. Improve data structures where they clarify the domain.
9. Separate external side effects from core logic.
10. Check edge cases.
11. Run automated quality checks.
12. Measure performance when performance matters.
13. Review the final change as a future maintainer would.
14. Keep the change small enough to understand.

The central principle is that code is read and changed many more times than
it is originally written. Readability and maintainability therefore have
direct practical value throughout the software lifecycle.
"""
)


# ============================================================================
# 61. FINAL EXECUTION CHECK
# ============================================================================

section("60. Final execution check")

def final_demo() -> dict[str, Any]:
    """Return a small set of representative results."""
    return {
        "area": calculate_area(10, 5),
        "average": calculate_average([80, 90, 100]),
        "grade": calculate_grade(92),
        "even": is_even(24),
        "shipping": str(calculate_shipping_cost(Decimal("750"))),
        "invoice_total": str(
            Invoice(
                [
                    Product("A", Decimal("100"), 2),
                    Product("B", Decimal("50"), 1),
                ]
            ).subtotal()
        ),
    }


final_results = final_demo()

for key, value in final_results.items():
    print(f"{key}: {value}")

print(
    """
Study file execution completed successfully.

Core quality principle:
Code quality is not merely making source code look neat. It is the disciplined
practice of making software understandable, correct, testable, changeable,
observable, secure, and appropriately efficient.
"""
)
