"""
Debugging: Debugging Workflow, Breakpoints, Logs, and Root Cause Analysis
==========================================================================

A standalone study script covering debugging from beginner through advanced
practice. It demonstrates:

1. What debugging is and why it matters.
2. A systematic debugging workflow.
3. Reproducing failures and minimizing test cases.
4. Assertions and validation.
5. Python exceptions and tracebacks.
6. Breakpoints with pdb and breakpoint().
7. Conditional and programmatic breakpoints.
8. Logging levels, handlers, formatters, and contextual data.
9. Structured logging concepts using the standard logging module.
10. Root cause analysis.
11. Hypothesis-driven debugging.
12. Fault isolation.
13. Defensive programming.
14. Common debugging mistakes.
15. Performance and production considerations.
16. Security considerations for diagnostic information.
17. Automated regression tests.
18. A realistic order-processing debugging case study.

The file intentionally uses only Python's standard library.
"""

from __future__ import annotations

import logging
import math
import statistics
import sys
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from io import StringIO
from typing import Callable, Iterable, Optional


# ---------------------------------------------------------------------------
# 1. BASIC DEBUGGING CONCEPTS
# ---------------------------------------------------------------------------

def heading(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def explain_debugging_concept() -> None:
    heading("1. What Debugging Means")

    concepts = {
        "bug": "An incorrect or unexpected behavior in a program.",
        "failure": "An observable event showing that expected behavior was not achieved.",
        "error": "A condition indicating that something went wrong.",
        "exception": "A runtime object representing an abnormal condition.",
        "symptom": "The visible effect of a defect.",
        "root cause": "The underlying condition that produced the observed failure.",
        "regression": "A previously working behavior that becomes broken after a change.",
        "breakpoint": "A location where execution can pause for inspection.",
        "log": "A recorded diagnostic event containing useful execution information.",
    }

    for term, definition in concepts.items():
        print(f"{term:12} -> {definition}")


# ---------------------------------------------------------------------------
# 2. A SYSTEMATIC DEBUGGING WORKFLOW
# ---------------------------------------------------------------------------

def debugging_workflow() -> None:
    heading("2. Systematic Debugging Workflow")

    workflow = [
        "1. Observe the failure.",
        "2. Record the exact input, environment, and expected behavior.",
        "3. Reproduce the failure reliably.",
        "4. Minimize the failing example.",
        "5. Read the traceback or diagnostic output.",
        "6. Form one or more explicit hypotheses.",
        "7. Gather evidence using breakpoints, logs, assertions, and tests.",
        "8. Isolate the faulty component.",
        "9. Identify the root cause rather than only the symptom.",
        "10. Implement the smallest correct fix.",
        "11. Add or update a regression test.",
        "12. Run related tests.",
        "13. Check for side effects and performance changes.",
        "14. Document the cause and prevention when appropriate.",
    ]

    for step in workflow:
        print(step)


# ---------------------------------------------------------------------------
# 3. A DELIBERATE BUG FOR TRACEBACK ANALYSIS
# ---------------------------------------------------------------------------

def calculate_average(values: list[float]) -> float:
    """
    Calculate an average.

    This function deliberately does not silently convert an empty input into
    zero because zero and "no data" have different meanings.
    """
    if not values:
        raise ValueError("Cannot calculate an average from an empty sequence.")

    return sum(values) / len(values)


def demonstrate_traceback() -> None:
    heading("3. Exceptions and Tracebacks")

    try:
        calculate_average([])
    except ValueError as error:
        print("Caught exception:", error)
        print("Exception type:", type(error).__name__)


# ---------------------------------------------------------------------------
# 4. ASSERTIONS AND VALIDATION
# ---------------------------------------------------------------------------

def calculate_discounted_price(price: float, discount_percent: float) -> float:
    """
    Calculate a discounted price with explicit input validation.

    Assertions are useful for programmer assumptions. User-controlled input
    should normally be validated with explicit exceptions instead.
    """
    if not math.isfinite(price):
        raise ValueError("Price must be finite.")

    if price < 0:
        raise ValueError("Price cannot be negative.")

    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100.")

    final_price = price * (1 - discount_percent / 100)

    # This is an internal invariant established by the validation above.
    assert final_price >= 0

    return final_price


def demonstrate_validation() -> None:
    heading("4. Validation and Assertions")

    examples = [
        (100.0, 20.0),
        (250.0, 0.0),
        (80.0, 100.0),
    ]

    for price, discount in examples:
        result = calculate_discounted_price(price, discount)
        print(f"price={price:7.2f}, discount={discount:5.1f}% -> {result:7.2f}")

    try:
        calculate_discounted_price(-10, 20)
    except ValueError as error:
        print("Validation failure:", error)

    try:
        calculate_discounted_price(100, 120)
    except ValueError as error:
        print("Validation failure:", error)


# ---------------------------------------------------------------------------
# 5. BREAKPOINTS WITH pdb
# ---------------------------------------------------------------------------

def calculate_statistics(values: Iterable[float]) -> dict[str, float]:
    """
    Compute several statistics.

    A developer can place a breakpoint() immediately before the return and
    inspect values, total, count, average, and spread interactively.
    """
    values = list(values)

    if not values:
        raise ValueError("At least one value is required.")

    total = sum(values)
    count = len(values)
    average = total / count
    minimum = min(values)
    maximum = max(values)

    return {
        "count": count,
        "total": total,
        "average": average,
        "minimum": minimum,
        "maximum": maximum,
    }


def demonstrate_breakpoint_concept() -> None:
    heading("5. Breakpoints")

    values = [12, 15, 18, 21, 24]
    statistics_result = calculate_statistics(values)

    print("Statistics:", statistics_result)

    print(
        "Interactive breakpoint example:\n"
        "  Uncomment 'breakpoint()' inside calculate_statistics().\n"
        "  Useful pdb commands include:\n"
        "    p variable       inspect a value\n"
        "    n                execute the next line\n"
        "    s                step into a function\n"
        "    r                run until the current function returns\n"
        "    c                continue execution\n"
        "    l                display source context\n"
        "    q                quit the debugger"
    )


# ---------------------------------------------------------------------------
# 6. CONDITIONAL BREAKPOINT LOGIC
# ---------------------------------------------------------------------------

def process_measurements(measurements: list[float]) -> list[float]:
    """
    Demonstrate the idea behind a conditional breakpoint.

    In an IDE, a breakpoint can be configured to stop only when a condition
    such as 'measurement < 0' becomes true.
    """
    processed: list[float] = []

    for measurement in measurements:
        if measurement < 0:
            # A conditional debugger breakpoint could be placed here.
            print(f"Diagnostic condition reached: measurement={measurement}")

        processed.append(round(measurement * 1.1, 2))

    return processed


# ---------------------------------------------------------------------------
# 7. LOGGING FUNDAMENTALS
# ---------------------------------------------------------------------------

def create_demo_logger() -> logging.Logger:
    """
    Create an isolated logger.

    Using a dedicated logger avoids modifying the application's root logger.
    """
    logger = logging.getLogger("debugging.study")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Avoid adding duplicate handlers if this function is called repeatedly.
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def logging_demo() -> None:
    heading("6. Logging")

    logger = create_demo_logger()

    logger.debug("Detailed diagnostic information.")
    logger.info("Normal application event.")
    logger.warning("A condition deserves attention.")
    logger.error("An operation failed.")

    try:
        result = 10 / 0
        print(result)
    except ZeroDivisionError:
        # exc_info=True includes exception information without manually
        # formatting a traceback.
        logger.exception("Division operation failed.")


# ---------------------------------------------------------------------------
# 8. LOGGING WITH CONTEXT
# ---------------------------------------------------------------------------

def process_order_with_logging(
    order_id: str,
    quantity: int,
    unit_price: float,
    logger: logging.Logger,
) -> float:
    """
    Demonstrate contextual diagnostic logging.

    Sensitive information should not be logged merely because it is available.
    """
    logger.info(
        "Starting order processing: order_id=%s quantity=%d",
        order_id,
        quantity,
    )

    if quantity <= 0:
        logger.warning(
            "Invalid quantity: order_id=%s quantity=%d",
            order_id,
            quantity,
        )
        raise ValueError("Quantity must be positive.")

    if unit_price < 0:
        logger.error(
            "Invalid unit price: order_id=%s",
            order_id,
        )
        raise ValueError("Unit price cannot be negative.")

    total = quantity * unit_price

    logger.info(
        "Order calculation completed: order_id=%s total=%.2f",
        order_id,
        total,
    )

    return total


# ---------------------------------------------------------------------------
# 9. ROOT CAUSE ANALYSIS
# ---------------------------------------------------------------------------

@dataclass
class Incident:
    """A compact representation of a debugging incident."""

    symptom: str
    evidence: list[str]
    suspected_causes: list[str]
    root_cause: Optional[str] = None
    corrective_action: Optional[str] = None


def perform_root_cause_analysis(incident: Incident) -> Incident:
    """
    Perform a small deterministic RCA example.

    Real incidents usually require more evidence. The function demonstrates
    the reasoning structure rather than pretending that every bug has a
    single obvious explanation.
    """
    for evidence in incident.evidence:
        print("Evidence:", evidence)

    if (
        "discount" in incident.symptom.lower()
        and any("discount applied twice" in item.lower() for item in incident.evidence)
    ):
        incident.root_cause = (
            "The discount operation was invoked twice for the same order."
        )
        incident.corrective_action = (
            "Centralize discount application and add an invariant/regression test "
            "ensuring one discount is applied per order."
        )

    return incident


def root_cause_analysis_demo() -> None:
    heading("7. Root Cause Analysis")

    incident = Incident(
        symptom="Customer receives a price lower than expected.",
        evidence=[
            "The order enters the pricing function once.",
            "The discount operation is invoked twice.",
            "The calculated final amount is lower than the expected amount.",
        ],
        suspected_causes=[
            "Incorrect tax calculation",
            "Incorrect discount calculation",
            "Duplicate discount application",
            "Incorrect product price",
        ],
    )

    print("Symptom:", incident.symptom)
    print("Suspected causes:")
    for cause in incident.suspected_causes:
        print(" -", cause)

    perform_root_cause_analysis(incident)

    print("Root cause:", incident.root_cause)
    print("Corrective action:", incident.corrective_action)


# ---------------------------------------------------------------------------
# 10. HYPOTHESIS-DRIVEN DEBUGGING
# ---------------------------------------------------------------------------

def hypothesis_driven_debugging() -> None:
    heading("8. Hypothesis-Driven Debugging")

    hypotheses = [
        ("H1", "The input is invalid.", "Validate the raw input."),
        ("H2", "The transformation is incorrect.", "Inspect transformation output."),
        ("H3", "State is being modified unexpectedly.", "Inspect state before/after mutation."),
        ("H4", "The failure is caused by an external dependency.", "Replace dependency with a controlled test double."),
    ]

    for identifier, hypothesis, test in hypotheses:
        print(f"{identifier}: {hypothesis}")
        print(f"    Test: {test}")


# ---------------------------------------------------------------------------
# 11. FAULT ISOLATION WITH A PIPELINE
# ---------------------------------------------------------------------------

def parse_amount(raw_amount: str) -> float:
    return float(raw_amount.strip())


def apply_tax(amount: float, tax_rate: float) -> float:
    if amount < 0:
        raise ValueError("Amount cannot be negative.")
    if not 0 <= tax_rate <= 1:
        raise ValueError("Tax rate must be between 0 and 1.")
    return amount * (1 + tax_rate)


def round_currency(amount: float) -> float:
    return round(amount, 2)


def pricing_pipeline(raw_amount: str, tax_rate: float) -> float:
    """
    A small pipeline is easy to debug because each transformation has a
    clearly defined responsibility.
    """
    amount = parse_amount(raw_amount)
    taxed_amount = apply_tax(amount, tax_rate)
    return round_currency(taxed_amount)


def pipeline_debugging_demo() -> None:
    heading("9. Fault Isolation")

    raw_amount = "100.00"
    tax_rate = 0.18

    try:
        result = pricing_pipeline(raw_amount, tax_rate)
        print("Pipeline result:", result)
    except (ValueError, TypeError) as error:
        print("Pipeline failure:", error)

    # Debugging is easier when intermediate values are observable.
    amount = parse_amount(raw_amount)
    print("Stage 1 - parsed amount:", amount)

    taxed_amount = apply_tax(amount, tax_rate)
    print("Stage 2 - taxed amount:", taxed_amount)

    final_amount = round_currency(taxed_amount)
    print("Stage 3 - rounded amount:", final_amount)


# ---------------------------------------------------------------------------
# 12. A DECORATOR FOR FUNCTION-LEVEL DIAGNOSTICS
# ---------------------------------------------------------------------------

def debug_calls(function: Callable) -> Callable:
    """
    A simple diagnostic decorator.

    It records entry, exit, and exceptions. In production, diagnostic
    decorators should be used selectively because excessive logging can
    increase latency and log volume.
    """

    @wraps(function)
    def wrapper(*args, **kwargs):
        logger = create_demo_logger()
        logger.debug(
            "CALL %s args=%r kwargs=%r",
            function.__name__,
            args,
            kwargs,
        )

        start = time.perf_counter()

        try:
            result = function(*args, **kwargs)
        except Exception:
            logger.exception("ERROR in %s", function.__name__)
            raise

        elapsed = time.perf_counter() - start

        logger.debug(
            "RETURN %s result=%r elapsed=%.6fs",
            function.__name__,
            result,
            elapsed,
        )

        return result

    return wrapper


@debug_calls
def multiply_numbers(first: float, second: float) -> float:
    return first * second


def decorator_demo() -> None:
    heading("10. Function-Level Diagnostics")
    print("Result:", multiply_numbers(7, 6))


# ---------------------------------------------------------------------------
# 13. TESTABLE BEHAVIOR AND REGRESSION TESTS
# ---------------------------------------------------------------------------

def calculate_order_total(
    item_prices: list[float],
    discount_percent: float = 0.0,
) -> float:
    if any(price < 0 for price in item_prices):
        raise ValueError("Item prices cannot be negative.")

    if not 0 <= discount_percent <= 100:
        raise ValueError("Discount must be between 0 and 100.")

    subtotal = sum(item_prices)
    return round(subtotal * (1 - discount_percent / 100), 2)


def run_regression_tests() -> None:
    heading("11. Regression Tests")

    tests = [
        (
            "empty order",
            lambda: calculate_order_total([]) == 0,
        ),
        (
            "normal order",
            lambda: calculate_order_total([100, 50]) == 150,
        ),
        (
            "discount",
            lambda: calculate_order_total([100], 20) == 80,
        ),
        (
            "full discount",
            lambda: calculate_order_total([100], 100) == 0,
        ),
    ]

    passed = 0

    for name, test in tests:
        try:
            assert test(), f"Test failed: {name}"
            print(f"PASS: {name}")
            passed += 1
        except AssertionError as error:
            print(f"FAIL: {error}")

    print(f"{passed}/{len(tests)} tests passed.")


# ---------------------------------------------------------------------------
# 14. EDGE CASES
# ---------------------------------------------------------------------------

def edge_case_demo() -> None:
    heading("12. Important Edge Cases")

    cases = [
        ("empty list", []),
        ("single value", [42]),
        ("negative value", [-10, 20]),
        ("duplicate values", [5, 5, 5]),
        ("large values", [10**9, 10**9]),
        ("floating-point values", [0.1, 0.2]),
    ]

    for description, values in cases:
        try:
            result = calculate_average(values)
            print(f"{description:22} -> {result}")
        except ValueError as error:
            print(f"{description:22} -> handled: {error}")

    # Floating-point arithmetic can expose representation details.
    print("0.1 + 0.2 =", 0.1 + 0.2)
    print("Rounded representation =", round(0.1 + 0.2, 2))


# ---------------------------------------------------------------------------
# 15. PERFORMANCE-AWARE DEBUGGING
# ---------------------------------------------------------------------------

def performance_demo() -> None:
    heading("13. Performance Considerations")

    values = list(range(1, 100_001))

    start = time.perf_counter()
    result = sum(values)
    elapsed = time.perf_counter() - start

    print("Sum:", result)
    print(f"Elapsed time: {elapsed:.6f} seconds")

    print(
        "\nImportant distinction:\n"
        "A performance measurement tells you where time is spent; it does not\n"
        "automatically explain why the application is slow."
    )

    print(
        "\nUseful debugging measurements include:\n"
        "- elapsed time\n"
        "- CPU utilization\n"
        "- memory allocation\n"
        "- I/O latency\n"
        "- database query duration\n"
        "- network latency\n"
        "- cache hit/miss behavior"
    )


# ---------------------------------------------------------------------------
# 16. SECURITY-AWARE DEBUGGING
# ---------------------------------------------------------------------------

def security_logging_demo() -> None:
    heading("14. Security Considerations")

    logger = create_demo_logger()

    user_id = "user-12345"
    transaction_id = "txn-789"

    # Diagnostic identifiers may be useful. Passwords, access tokens,
    # private keys, session cookies, and full payment-card data should not
    # be written to logs merely for debugging convenience.
    logger.info(
        "Transaction diagnostic context: user_id=%s transaction_id=%s",
        user_id,
        transaction_id,
    )

    print(
        "Never treat logs as automatically safe.\n"
        "Logs may be copied, retained, indexed, exported, or viewed by\n"
        "people and systems outside the original application."
    )


# ---------------------------------------------------------------------------
# 17. EXCEPTION CHAINING
# ---------------------------------------------------------------------------

class ConfigurationError(Exception):
    """Application-specific configuration failure."""


def load_tax_rate(raw_value: str) -> float:
    try:
        value = float(raw_value)
    except ValueError as error:
        raise ConfigurationError(
            f"Invalid tax configuration: {raw_value!r}"
        ) from error

    if not 0 <= value <= 1:
        raise ConfigurationError(
            f"Tax rate outside valid range: {value}"
        )

    return value


def exception_chaining_demo() -> None:
    heading("15. Exception Chaining")

    try:
        load_tax_rate("not-a-number")
    except ConfigurationError as error:
        print("Application-level error:", error)
        print("Underlying cause:", repr(error.__cause__))


# ---------------------------------------------------------------------------
# 18. DEBUGGING STATE CHANGES
# ---------------------------------------------------------------------------

@dataclass
class ShoppingCart:
    items: list[float]

    def subtotal(self) -> float:
        return sum(self.items)

    def remove_item(self, index: int) -> float:
        if not 0 <= index < len(self.items):
            raise IndexError("Cart item index is out of range.")

        return self.items.pop(index)


def state_debugging_demo() -> None:
    heading("16. State Inspection")

    cart = ShoppingCart([100.0, 50.0, 25.0])

    before = list(cart.items)
    print("State before removal:", before)

    removed = cart.remove_item(1)

    after = list(cart.items)
    print("Removed item:", removed)
    print("State after removal:", after)
    print("Subtotal:", cart.subtotal())

    # Comparing state snapshots is a useful debugging technique for mutation
    # bugs because it makes unexpected changes visible.
    if len(after) != len(before) - 1:
        print("Unexpected state transition detected.")


# ---------------------------------------------------------------------------
# 19. DEBUGGING A REALISTIC ORDER SYSTEM
# ---------------------------------------------------------------------------

@dataclass
class OrderItem:
    product_id: str
    unit_price: float
    quantity: int

    def total(self) -> float:
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive.")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative.")

        return self.unit_price * self.quantity


@dataclass
class Order:
    order_id: str
    items: list[OrderItem]
    discount_percent: float = 0.0

    def subtotal(self) -> float:
        return sum(item.total() for item in self.items)

    def total(self) -> float:
        if not 0 <= self.discount_percent <= 100:
            raise ValueError("Invalid discount percentage.")

        subtotal = self.subtotal()
        discounted = subtotal * (1 - self.discount_percent / 100)

        # This invariant is useful during debugging.
        assert discounted >= 0

        return round(discounted, 2)


def order_system_debugging_demo() -> None:
    heading("17. Realistic Order-System Case Study")

    logger = create_demo_logger()

    order = Order(
        order_id="ORD-1001",
        items=[
            OrderItem("BOOK-01", 500.0, 2),
            OrderItem("COURSE-01", 1200.0, 1),
        ],
        discount_percent=10,
    )

    logger.info(
        "Processing order: order_id=%s item_count=%d",
        order.order_id,
        len(order.items),
    )

    try:
        subtotal = order.subtotal()
        total = order.total()

        logger.debug(
            "Order calculation: order_id=%s subtotal=%.2f total=%.2f",
            order.order_id,
            subtotal,
            total,
        )

        print(f"Subtotal: {subtotal:.2f}")
        print(f"Total after discount: {total:.2f}")

    except Exception:
        logger.exception(
            "Order processing failed: order_id=%s",
            order.order_id,
        )
        raise


# ---------------------------------------------------------------------------
# 20. DEBUGGING DECISION TREE
# ---------------------------------------------------------------------------

def debugging_decision_tree() -> None:
    heading("18. Practical Debugging Decision Tree")

    decisions = [
        ("Can the failure be reproduced?", "If no, collect more diagnostic context."),
        ("Can the failure be minimized?", "Reduce input and execution path."),
        ("Is there a traceback?", "Read it from the bottom upward and inspect the call chain."),
        ("Is the failure deterministic?", "Use controlled inputs and isolate state."),
        ("Is the failure data-dependent?", "Compare working and failing inputs."),
        ("Is the failure timing-dependent?", "Investigate concurrency, ordering, retries, and races."),
        ("Is external I/O involved?", "Capture timing, status, response category, and correlation identifiers."),
        ("Did a recent change precede the regression?", "Inspect the relevant diff and run targeted regression tests."),
        ("Is the symptom fixed?", "Verify the original failure and related behavior."),
        ("Is the root cause understood?", "Document evidence, cause, fix, and prevention."),
    ]

    for question, action in decisions:
        print(f"{question}\n  -> {action}")


# ---------------------------------------------------------------------------
# 21. COMMON DEBUGGING MISTAKES
# ---------------------------------------------------------------------------

def common_mistakes() -> None:
    heading("19. Common Debugging Mistakes")

    mistakes = [
        "Changing code before reproducing the failure.",
        "Guessing the root cause from the first symptom.",
        "Changing multiple variables simultaneously.",
        "Deleting error handling instead of understanding the error.",
        "Logging sensitive information.",
        "Logging everything without a diagnostic purpose.",
        "Ignoring the environment and configuration.",
        "Fixing the symptom without identifying the underlying cause.",
        "Failing to add a regression test.",
        "Assuming a successful run proves correctness.",
        "Ignoring intermittent or timing-dependent failures.",
        "Using assertions as a substitute for validating untrusted input.",
        "Measuring performance only after making assumptions about the bottleneck.",
    ]

    for number, mistake in enumerate(mistakes, start=1):
        print(f"{number:02d}. {mistake}")


# ---------------------------------------------------------------------------
# 22. ADVANCED DEBUGGING PRINCIPLES
# ---------------------------------------------------------------------------

def advanced_principles() -> None:
    heading("20. Advanced Debugging Principles")

    principles = {
        "observability": "Make relevant system behavior measurable and inspectable.",
        "reproducibility": "A deterministic reproduction reduces uncertainty.",
        "isolation": "Separate components until the failing boundary becomes clear.",
        "instrumentation": "Add targeted diagnostic information where evidence is missing.",
        "invariants": "State conditions that must remain true throughout execution.",
        "regression prevention": "Turn discovered failures into automated tests.",
        "correlation": "Use identifiers to connect events across components.",
        "change analysis": "Compare working and failing versions or configurations.",
        "fault containment": "Prevent one failure from causing unnecessary secondary failures.",
        "minimal intervention": "Prefer evidence-producing changes over random code changes.",
    }

    for principle, explanation in principles.items():
        print(f"{principle:22} -> {explanation}")


# ---------------------------------------------------------------------------
# 23. COMPARING DEBUGGING TECHNIQUES
# ---------------------------------------------------------------------------

def compare_techniques() -> None:
    heading("21. Debugging Technique Comparison")

    techniques = [
        ("Print statements", "Fast, simple", "Can become noisy and difficult to manage"),
        ("Logging", "Persistent structured diagnostics", "Needs careful volume and data control"),
        ("Breakpoints", "Interactive state inspection", "Less useful for some production failures"),
        ("Assertions", "Detect violated assumptions", "Not a replacement for input validation"),
        ("Unit tests", "Repeatable behavior checks", "May miss integration/environment problems"),
        ("Profiling", "Finds performance hotspots", "Does not automatically identify logical causes"),
        ("Tracing", "Follows execution across components", "Requires appropriate instrumentation"),
        ("Core dumps/debuggers", "Deep failure analysis", "More complex operationally"),
    ]

    for method, strength, limitation in techniques:
        print(f"\n{method}")
        print(f"  Strength:   {strength}")
        print(f"  Limitation: {limitation}")


# ---------------------------------------------------------------------------
# 24. FULL DEMONSTRATION
# ---------------------------------------------------------------------------

def main() -> None:
    explain_debugging_concept()
    debugging_workflow()
    demonstrate_traceback()
    demonstrate_validation()
    demonstrate_breakpoint_concept()

    print("\nConditional breakpoint example:")
    print(process_measurements([10, 20, -5, 30]))

    logging_demo()

    logger = create_demo_logger()
    print(
        "\nOrder logging result:",
        process_order_with_logging("ORD-42", 3, 25.50, logger),
    )

    root_cause_analysis_demo()
    hypothesis_driven_debugging()
    pipeline_debugging_demo()
    decorator_demo()
    run_regression_tests()
    edge_case_demo()
    performance_demo()
    security_logging_demo()
    exception_chaining_demo()
    state_debugging_demo()
    order_system_debugging_demo()
    debugging_decision_tree()
    common_mistakes()
    advanced_principles()
    compare_techniques()

    heading("22. Study Exercise Built Into This File")
    print(
        "To practice debugging, intentionally change one expression in an\n"
        "example, reproduce the resulting failure, form a hypothesis, inspect\n"
        "state with a breakpoint or log, identify the root cause, restore the\n"
        "correct behavior, and add a regression test."
    )


if __name__ == "__main__":
    main()
