"""
CONTROL FLOW IN PYTHON
======================

Topic:
    Conditions, loops, and branching

This standalone study script progresses from beginner-level control flow
through advanced patterns, edge cases, performance considerations, debugging,
validation, testing, and practical applications.

The script uses only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import perf_counter
from typing import Callable, Iterable, Iterator, Sequence


# ============================================================================
# 1. FUNDAMENTALS: SEQUENTIAL EXECUTION
# ============================================================================

def section(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def subsection(title: str) -> None:
    """Print a readable subsection heading."""
    print("\n" + "-" * 78)
    print(title)
    print("-" * 78)


def demonstrate_sequential_execution() -> None:
    """
    Python normally executes statements from top to bottom.

    Control flow changes that natural sequence by:
    - selecting one path,
    - selecting among multiple paths,
    - repeating statements,
    - skipping an iteration,
    - exiting a loop,
    - returning from a function,
    - raising or handling exceptions.
    """
    subsection("Sequential execution")

    first = 10
    second = 20
    total = first + second
    average = total / 2

    print("first =", first)
    print("second =", second)
    print("total =", total)
    print("average =", average)


# ============================================================================
# 2. BOOLEAN VALUES AND COMPARISONS
# ============================================================================

def demonstrate_boolean_logic() -> None:
    subsection("Boolean values and comparison operators")

    true_value = True
    false_value = False

    print("True:", true_value)
    print("False:", false_value)

    print("10 == 10:", 10 == 10)
    print("10 != 20:", 10 != 20)
    print("10 < 20:", 10 < 20)
    print("10 <= 10:", 10 <= 10)
    print("20 > 10:", 20 > 10)
    print("20 >= 20:", 20 >= 20)

    # Logical operators combine Boolean expressions.
    age = 25
    has_id = True
    is_member = False

    print("age >= 18:", age >= 18)
    print("age >= 18 and has_id:", age >= 18 and has_id)
    print("is_member or has_id:", is_member or has_id)
    print("not is_member:", not is_member)

    # Chained comparisons are evaluated as a logical chain.
    score = 82
    print("70 <= score <= 100:", 70 <= score <= 100)


# ============================================================================
# 3. TRUTHINESS
# ============================================================================

def demonstrate_truthiness() -> None:
    subsection("Truthiness")

    # Python does not require every condition to literally contain True
    # or False. Objects are converted to Boolean context.
    values = [
        True,
        False,
        0,
        1,
        0.0,
        3.14,
        "",
        "Python",
        [],
        [1, 2],
        {},
        {"name": "Atul"},
        None,
    ]

    for value in values:
        print(f"{value!r:20} -> bool(value) = {bool(value)}")

    # Empty collections are false; non-empty collections are true.
    names: list[str] = []

    if names:
        print("There are names.")
    else:
        print("The names collection is empty.")

    # This is often cleaner than explicitly comparing with [].
    names.append("Asha")

    if names:
        print("There is at least one name.")


# ============================================================================
# 4. IF STATEMENTS
# ============================================================================

def demonstrate_if() -> None:
    subsection("if statements")

    temperature = 32

    if temperature > 30:
        print("It is hot.")

    # If the condition is false, the body is skipped.
    temperature = 20

    if temperature > 30:
        print("This line will not execute.")

    print("Execution continues after the if statement.")


# ============================================================================
# 5. IF / ELSE
# ============================================================================

def demonstrate_if_else() -> None:
    subsection("if / else")

    number = 17

    if number % 2 == 0:
        print(number, "is even.")
    else:
        print(number, "is odd.")


# ============================================================================
# 6. IF / ELIF / ELSE
# ============================================================================

def classify_score(score: float) -> str:
    """Classify a percentage score."""
    if score < 0 or score > 100:
        return "invalid"

    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def demonstrate_elif() -> None:
    subsection("if / elif / else")

    for score in [95, 84, 73, 65, 42, 120, -5]:
        print(f"Score {score:>3}: grade = {classify_score(score)}")


# ============================================================================
# 7. BRANCH ORDER MATTERS
# ============================================================================

def demonstrate_branch_order() -> None:
    subsection("Branch ordering")

    age = 25

    # Only the first matching branch executes.
    if age >= 18:
        print("Adult branch selected.")
    elif age >= 65:
        print("Senior branch selected.")
    else:
        print("Minor branch selected.")

    print(
        "The example above demonstrates why more specific conditions "
        "sometimes need to appear before broader conditions."
    )

    if age >= 65:
        print("Senior")
    elif age >= 18:
        print("Adult")
    else:
        print("Minor")


# ============================================================================
# 8. NESTED CONDITIONS
# ============================================================================

def demonstrate_nested_conditions() -> None:
    subsection("Nested conditions")

    age = 22
    has_ticket = True
    has_valid_id = True

    if age >= 18:
        if has_ticket:
            if has_valid_id:
                print("Entry approved.")
            else:
                print("Entry denied: invalid identification.")
        else:
            print("Entry denied: ticket required.")
    else:
        print("Entry denied: age requirement not met.")

    # Compound conditions often reduce unnecessary nesting.
    if age >= 18 and has_ticket and has_valid_id:
        print("The same decision can be expressed with one compound condition.")


# ============================================================================
# 9. AND / OR / NOT
# ============================================================================

def access_decision(
    age: int,
    has_identity_document: bool,
    is_employee: bool,
) -> str:
    """Return an access decision using Boolean logic."""
    if age < 18:
        return "Denied: age requirement"

    if not has_identity_document:
        return "Denied: identity document required"

    if is_employee or age >= 60:
        return "Approved: eligible category"

    return "Approved: standard access"


def demonstrate_logical_operators() -> None:
    subsection("and, or, not")

    cases = [
        (17, True, True),
        (25, False, True),
        (25, True, False),
        (65, True, False),
    ]

    for age, has_id, employee in cases:
        result = access_decision(age, has_id, employee)
        print(age, has_id, employee, "->", result)


# ============================================================================
# 10. SHORT-CIRCUIT EVALUATION
# ============================================================================

def safe_division_check(numerator: float, denominator: float) -> bool:
    """
    Demonstrate short-circuit evaluation.

    The second expression is evaluated only when denominator is non-zero.
    """
    return denominator != 0 and numerator / denominator > 1


def demonstrate_short_circuiting() -> None:
    subsection("Short-circuit evaluation")

    print("safe_division_check(10, 2):", safe_division_check(10, 2))
    print("safe_division_check(10, 0):", safe_division_check(10, 0))

    # With 'and', Python stops when the left side is false.
    # With 'or', Python stops when the left side is true.
    result = False and (1 / 0)
    print("False and dangerous expression:", result)

    result = True or (1 / 0)
    print("True or dangerous expression:", result)


# ============================================================================
# 11. CONDITIONAL EXPRESSIONS
# ============================================================================

def demonstrate_conditional_expression() -> None:
    subsection("Conditional expressions")

    age = 20
    status = "adult" if age >= 18 else "minor"

    print("status =", status)

    score = 84
    result = "pass" if score >= 40 else "fail"
    print("result =", result)

    # Nested conditional expressions are possible but often reduce clarity.
    number = 7
    description = (
        "negative"
        if number < 0
        else "zero"
        if number == 0
        else "positive"
    )
    print("description =", description)


# ============================================================================
# 12. MATCH / CASE
# ============================================================================

def classify_http_status(status_code: int) -> str:
    """Use structural pattern matching for selected HTTP status codes."""
    match status_code:
        case 200:
            return "Success"
        case 201:
            return "Created"
        case 400:
            return "Bad request"
        case 401:
            return "Unauthorized"
        case 403:
            return "Forbidden"
        case 404:
            return "Not found"
        case 500:
            return "Server error"
        case _:
            return "Other status"


def demonstrate_match_case() -> None:
    subsection("match / case")

    for code in [200, 201, 404, 500, 418]:
        print(code, "->", classify_http_status(code))

    # match can also unpack structures.
    commands = [
        ("move", 10, 20),
        ("move", 5, 8),
        ("stop",),
        ("unknown", 1),
    ]

    for command in commands:
        match command:
            case ("move", x, y):
                print(f"Move to ({x}, {y})")
            case ("stop",):
                print("Stop")
            case _:
                print("Unknown command:", command)


# ============================================================================
# 13. RANGE AND FOR LOOPS
# ============================================================================

def demonstrate_for_loops() -> None:
    subsection("for loops")

    print("Iterating over a list:")
    for language in ["Python", "SQL", "Java"]:
        print(language)

    print("range(5):")
    for number in range(5):
        print(number)

    print("range(2, 7):")
    for number in range(2, 7):
        print(number)

    print("range(10, 0, -2):")
    for number in range(10, 0, -2):
        print(number)

    # range excludes its stop value.
    print("list(range(1, 5)) =", list(range(1, 5)))


# ============================================================================
# 14. ITERATING OVER STRINGS, TUPLES, SETS, AND DICTIONARIES
# ============================================================================

def demonstrate_iteration() -> None:
    subsection("Iteration over common collections")

    text = "Python"
    for character in text:
        print("character:", character)

    coordinates = (10, 20, 30)
    for coordinate in coordinates:
        print("coordinate:", coordinate)

    unique_numbers = {3, 1, 2}
    for number in unique_numbers:
        print("set value:", number)

    person = {"name": "Asha", "age": 28}

    for key in person:
        print("key:", key)

    for key, value in person.items():
        print(key, "=", value)


# ============================================================================
# 15. ENUMERATE
# ============================================================================

def demonstrate_enumerate() -> None:
    subsection("enumerate")

    names = ["Asha", "Ravi", "Meera"]

    for index, name in enumerate(names):
        print(index, name)

    for position, name in enumerate(names, start=1):
        print(position, name)


# ============================================================================
# 16. ZIP
# ============================================================================

def demonstrate_zip() -> None:
    subsection("zip")

    names = ["Asha", "Ravi", "Meera"]
    scores = [91, 84, 77]

    for name, score in zip(names, scores):
        print(name, "->", score)

    # zip stops when the shortest iterable is exhausted.
    short = [1, 2]
    long = ["a", "b", "c"]

    print("zip with unequal lengths:", list(zip(short, long)))

    # strict=True detects unequal lengths instead of silently truncating.
    try:
        print(list(zip(short, long, strict=True)))
    except ValueError as error:
        print("strict zip detected mismatch:", error)


# ============================================================================
# 17. WHILE LOOPS
# ============================================================================

def demonstrate_while() -> None:
    subsection("while loops")

    count = 1

    while count <= 5:
        print(count)
        count += 1

    print("Loop completed.")


# ============================================================================
# 18. INFINITE LOOPS AND TERMINATION
# ============================================================================

def controlled_retry(
    attempts: int,
    success_on: int,
) -> str:
    """Use a while loop with an explicit termination condition."""
    if attempts <= 0:
        return "No attempts available."

    attempt = 1

    while attempt <= attempts:
        print("Attempt", attempt)

        if attempt == success_on:
            return f"Success on attempt {attempt}"

        attempt += 1

    return "All attempts failed."


def demonstrate_loop_termination() -> None:
    subsection("Controlled repetition")

    print(controlled_retry(5, 3))
    print(controlled_retry(3, 8))

    # An intentional infinite loop would look like:
    #
    # while True:
    #     ...
    #
    # Such loops require an explicit break, return, exception, external
    # cancellation, or another reliable termination mechanism.


# ============================================================================
# 19. BREAK
# ============================================================================

def first_number_greater_than(numbers: Sequence[int], threshold: int) -> int | None:
    """Return the first number greater than threshold."""
    for number in numbers:
        if number > threshold:
            return number
    return None


def demonstrate_break() -> None:
    subsection("break")

    numbers = [4, 7, 12, 3, 20]

    for number in numbers:
        if number > 10:
            print("Found:", number)
            break

    print(
        "First number greater than 10:",
        first_number_greater_than(numbers, 10),
    )


# ============================================================================
# 20. CONTINUE
# ============================================================================

def demonstrate_continue() -> None:
    subsection("continue")

    numbers = range(1, 11)

    for number in numbers:
        if number % 2 == 0:
            continue

        print("Odd number:", number)


# ============================================================================
# 21. PASS
# ============================================================================

def demonstrate_pass() -> None:
    subsection("pass")

    # pass does nothing. It is syntactically valid where a statement is
    # required, but it does not skip an iteration like continue does.
    for number in range(3):
        if number == 1:
            pass
        print("number:", number)


# ============================================================================
# 22. ELSE ON LOOPS
# ============================================================================

def find_prime(number: int) -> bool:
    """
    Determine whether number is prime.

    The loop's else clause executes only if the loop finishes normally,
    meaning it was not terminated by break.
    """
    if number < 2:
        return False

    for divisor in range(2, int(number**0.5) + 1):
        if number % divisor == 0:
            break
    else:
        return True

    return False


def demonstrate_loop_else() -> None:
    subsection("for / else")

    for number in [1, 2, 7, 10, 13, 25]:
        print(number, "is prime:", find_prime(number))


# ============================================================================
# 23. NESTED LOOPS
# ============================================================================

def demonstrate_nested_loops() -> None:
    subsection("Nested loops")

    for row in range(1, 4):
        for column in range(1, 4):
            print(f"({row}, {column})", end=" ")
        print()

    print("Multiplication table:")
    for row in range(1, 6):
        for column in range(1, 6):
            print(f"{row * column:2}", end=" ")
        print()


# ============================================================================
# 24. SEARCHING A MATRIX
# ============================================================================

def find_in_matrix(
    matrix: Sequence[Sequence[int]],
    target: int,
) -> tuple[int, int] | None:
    """Return (row, column) of target or None."""
    for row_index, row in enumerate(matrix):
        for column_index, value in enumerate(row):
            if value == target:
                return row_index, column_index
    return None


def demonstrate_matrix_search() -> None:
    subsection("Nested-loop search")

    matrix = [
        [3, 8, 1],
        [9, 4, 7],
        [6, 2, 5],
    ]

    for target in [7, 10]:
        print(target, "->", find_in_matrix(matrix, target))


# ============================================================================
# 25. MULTIPLE LOOP TERMINATION STRATEGIES
# ============================================================================

def find_pair_with_sum(
    numbers: Sequence[int],
    target: int,
) -> tuple[int, int] | None:
    """Use a flag to communicate a result out of nested loops."""
    found_pair: tuple[int, int] | None = None

    for index, first in enumerate(numbers):
        for second in numbers[index + 1:]:
            if first + second == target:
                found_pair = (first, second)
                break

        if found_pair is not None:
            break

    return found_pair


def demonstrate_nested_loop_exit() -> None:
    subsection("Exiting nested loops")

    print(find_pair_with_sum([2, 4, 7, 9], 11))


# ============================================================================
# 26. COMPREHENSIONS AND CONDITIONAL FILTERING
# ============================================================================

def demonstrate_comprehensions() -> None:
    subsection("Comprehensions with conditions")

    squares_of_even_numbers = [
        number * number
        for number in range(1, 11)
        if number % 2 == 0
    ]

    print("Squares of even numbers:", squares_of_even_numbers)

    labels = [
        "even" if number % 2 == 0 else "odd"
        for number in range(1, 8)
    ]

    print("Labels:", labels)

    number_set = {
        number
        for number in range(1, 11)
        if number % 3 == 0
    }

    print("Multiples of 3:", number_set)

    number_map = {
        number: number**2
        for number in range(1, 6)
    }

    print("Square mapping:", number_map)


# ============================================================================
# 27. GENERATOR EXPRESSIONS
# ============================================================================

def demonstrate_generator_expression() -> None:
    subsection("Generator expressions")

    squares = (number * number for number in range(1, 6))

    print("Generator object:", squares)

    for square in squares:
        print(square)

    # Generators calculate values lazily rather than constructing the
    # complete result collection immediately.


# ============================================================================
# 28. FUNCTIONS AND EARLY RETURN
# ============================================================================

def validate_username(username: str) -> tuple[bool, str]:
    """
    Validate a username using early returns.

    Early returns can flatten deeply nested conditions.
    """
    if not username:
        return False, "Username cannot be empty."

    if len(username) < 3:
        return False, "Username must contain at least 3 characters."

    if len(username) > 20:
        return False, "Username cannot contain more than 20 characters."

    if not username[0].isalpha():
        return False, "Username must start with a letter."

    if not username.isalnum():
        return False, "Username must contain only letters and digits."

    return True, "Username is valid."


def demonstrate_early_return() -> None:
    subsection("Early return as branching")

    usernames = [
        "",
        "ab",
        "atul123",
        "123atul",
        "valid_user",
        "a" * 21,
    ]

    for username in usernames:
        print(username!r, "->", validate_username(username))


# ============================================================================
# 29. GUARD CLAUSES
# ============================================================================

def process_payment(
    amount: float,
    account_active: bool,
    sufficient_balance: bool,
) -> str:
    """
    Demonstrate guard clauses.

    Guard clauses reject invalid states early, keeping the main path flat.
    """
    if amount <= 0:
        return "Rejected: amount must be positive."

    if not account_active:
        return "Rejected: account is inactive."

    if not sufficient_balance:
        return "Rejected: insufficient balance."

    return "Payment processed."


def demonstrate_guard_clauses() -> None:
    subsection("Guard clauses")

    scenarios = [
        (0, True, True),
        (100, False, True),
        (100, True, False),
        (100, True, True),
    ]

    for scenario in scenarios:
        print(scenario, "->", process_payment(*scenario))


# ============================================================================
# 30. INPUT VALIDATION
# ============================================================================

def read_integer(
    prompt: str,
    input_function: Callable[[str], str] = input,
) -> int:
    """
    Read an integer repeatedly until valid input is provided.

    input_function is injectable so automated tests do not need real input.
    """
    while True:
        raw_value = input_function(prompt).strip()

        try:
            return int(raw_value)
        except ValueError:
            print("Please enter a valid integer.")


def demonstrate_input_validation() -> None:
    subsection("Input validation")

    simulated_inputs = iter(["abc", "10"])

    def simulated_input(_: str) -> str:
        return next(simulated_inputs)

    number = read_integer("Enter an integer: ", simulated_input)
    print("Validated value:", number)


# ============================================================================
# 31. TRY / EXCEPT AS CONTROL FLOW
# ============================================================================

def safe_integer_division(
    numerator_text: str,
    denominator_text: str,
) -> str:
    """Validate conversion and arithmetic using exceptions."""
    try:
        numerator = int(numerator_text)
        denominator = int(denominator_text)
        result = numerator / denominator
    except ValueError:
        return "Invalid integer input."
    except ZeroDivisionError:
        return "Division by zero is not allowed."
    else:
        return f"Result: {result}"
    finally:
        # finally runs whether an exception occurs or not.
        pass


def demonstrate_exception_control_flow() -> None:
    subsection("Exception-based control flow")

    examples = [
        ("10", "2"),
        ("ten", "2"),
        ("10", "0"),
    ]

    for numerator, denominator in examples:
        print(
            numerator,
            "/",
            denominator,
            "->",
            safe_integer_division(numerator, denominator),
        )


# ============================================================================
# 32. STATE MACHINES
# ============================================================================

class OrderState(Enum):
    CREATED = "created"
    PAID = "paid"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


@dataclass
class Order:
    state: OrderState = OrderState.CREATED

    def transition(self, event: str) -> str:
        """Apply an event according to the current state."""
        if self.state == OrderState.CREATED:
            if event == "pay":
                self.state = OrderState.PAID
                return "Payment accepted."
            if event == "cancel":
                self.state = OrderState.CANCELLED
                return "Order cancelled."
            return "Invalid event for CREATED state."

        if self.state == OrderState.PAID:
            if event == "ship":
                self.state = OrderState.SHIPPED
                return "Order shipped."
            if event == "cancel":
                self.state = OrderState.CANCELLED
                return "Order cancelled."
            return "Invalid event for PAID state."

        if self.state == OrderState.SHIPPED:
            if event == "deliver":
                self.state = OrderState.DELIVERED
                return "Order delivered."
            return "Invalid event for SHIPPED state."

        return "No further transitions are available."


def demonstrate_state_machine() -> None:
    subsection("State-machine branching")

    order = Order()

    events = ["pay", "ship", "deliver"]

    for event in events:
        print("Before:", order.state.value)
        print("Event:", event)
        print(order.transition(event))
        print("After:", order.state.value)


# ============================================================================
# 33. DISPATCH TABLES
# ============================================================================

def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


def multiply(a: float, b: float) -> float:
    return a * b


def divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero.")
    return a / b


OPERATION_HANDLERS: dict[str, Callable[[float, float], float]] = {
    "add": add,
    "subtract": subtract,
    "multiply": multiply,
    "divide": divide,
}


def calculate_with_dispatch(
    operation: str,
    a: float,
    b: float,
) -> float:
    """
    Use a dictionary as a dispatch table.

    This can be cleaner than a very large if/elif chain when operations are
    independent and map naturally to callables.
    """
    try:
        handler = OPERATION_HANDLERS[operation]
    except KeyError as error:
        raise ValueError(f"Unsupported operation: {operation}") from error

    return handler(a, b)


def demonstrate_dispatch_table() -> None:
    subsection("Dispatch tables")

    for operation in ["add", "subtract", "multiply", "divide"]:
        print(operation, "->", calculate_with_dispatch(operation, 12, 4))

    try:
        calculate_with_dispatch("power", 2, 3)
    except ValueError as error:
        print("Error:", error)


# ============================================================================
# 34. RECURSION AS CONTROL FLOW
# ============================================================================

def factorial_recursive(number: int) -> int:
    """Compute factorial recursively with validation."""
    if number < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    if number in (0, 1):
        return 1

    return number * factorial_recursive(number - 1)


def factorial_iterative(number: int) -> int:
    """Compute factorial iteratively."""
    if number < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    result = 1

    for value in range(2, number + 1):
        result *= value

    return result


def demonstrate_recursion() -> None:
    subsection("Recursion")

    for number in range(0, 6):
        print(
            number,
            "recursive =",
            factorial_recursive(number),
            "iterative =",
            factorial_iterative(number),
        )

    # Recursive solutions need a base case.
    # Without a terminating condition, recursion eventually raises
    # RecursionError after exceeding Python's recursion limit.


# ============================================================================
# 35. ITERATORS AND NEXT()
# ============================================================================

def demonstrate_iterator_control() -> None:
    subsection("Iterators")

    numbers = iter([10, 20, 30])

    while True:
        try:
            value = next(numbers)
        except StopIteration:
            break
        else:
            print("Next value:", value)


# ============================================================================
# 36. ANY AND ALL
# ============================================================================

def demonstrate_any_all() -> None:
    subsection("any and all")

    scores = [75, 82, 91, 68]

    print("At least one score >= 90:", any(score >= 90 for score in scores))
    print("Every score >= 50:", all(score >= 50 for score in scores))
    print("Every score >= 70:", all(score >= 70 for score in scores))

    # any() and all() also short-circuit.
    # any stops after the first truthy item.
    # all stops after the first falsy item.


# ============================================================================
# 37. SORTING WITH CONDITIONAL KEY FUNCTIONS
# ============================================================================

@dataclass
class Student:
    name: str
    score: float
    attendance: float


def demonstrate_sorted_control() -> None:
    subsection("Branch-aware sorting")

    students = [
        Student("Asha", 91, 94),
        Student("Ravi", 84, 98),
        Student("Meera", 91, 88),
        Student("Kabir", 72, 91),
    ]

    # Primary sort: score descending.
    # Secondary sort: attendance descending.
    students.sort(key=lambda student: (-student.score, -student.attendance))

    for student in students:
        print(student)


# ============================================================================
# 38. COMPLEX BUSINESS RULES
# ============================================================================

def calculate_shipping_cost(
    order_value: float,
    distance_km: float,
    is_member: bool,
    is_express: bool,
) -> float:
    """
    Demonstrate layered business branching.

    Rules:
    - Invalid negative values are rejected.
    - Orders >= 1000 receive free standard shipping.
    - Members receive free standard shipping.
    - Express shipping adds a distance-independent surcharge.
    - Otherwise cost depends on distance bands.
    """
    if order_value < 0:
        raise ValueError("Order value cannot be negative.")

    if distance_km < 0:
        raise ValueError("Distance cannot be negative.")

    if order_value >= 1000 or is_member:
        cost = 0.0
    elif distance_km <= 5:
        cost = 50.0
    elif distance_km <= 15:
        cost = 100.0
    else:
        cost = 150.0

    if is_express:
        cost += 100.0

    return cost


def demonstrate_business_rules() -> None:
    subsection("Business-rule branching")

    scenarios = [
        (500, 3, False, False),
        (500, 10, False, False),
        (500, 30, False, False),
        (1000, 30, False, False),
        (500, 30, True, False),
        (500, 30, True, True),
    ]

    for scenario in scenarios:
        print(scenario, "->", calculate_shipping_cost(*scenario))


# ============================================================================
# 39. EDGE CASES
# ============================================================================

def safe_percentage(part: float, total: float) -> float | None:
    """Return a percentage, or None when total is zero."""
    if total == 0:
        return None

    return part / total * 100


def demonstrate_edge_cases() -> None:
    subsection("Edge cases")

    edge_cases = [
        ("empty string", ""),
        ("zero", 0),
        ("negative", -1),
        ("empty list", []),
        ("None", None),
    ]

    for label, value in edge_cases:
        print(label, "-> truthy:", bool(value))

    print("0 / 0 represented safely:", safe_percentage(0, 0))
    print("25 / 0 represented safely:", safe_percentage(25, 0))
    print("25 / 100:", safe_percentage(25, 100))


# ============================================================================
# 40. OFF-BY-ONE ERRORS
# ============================================================================

def demonstrate_off_by_one() -> None:
    subsection("Off-by-one errors")

    # range(1, 6) includes 1, 2, 3, 4, 5 but excludes 6.
    print("Correct inclusive-looking range 1..5:")
    for number in range(1, 6):
        print(number, end=" ")
    print()

    print("A common mistake is range(1, 5), which stops before 5:")
    for number in range(1, 5):
        print(number, end=" ")
    print()


# ============================================================================
# 41. MUTATING A COLLECTION DURING ITERATION
# ============================================================================

def demonstrate_safe_collection_filtering() -> None:
    subsection("Safe collection filtering")

    numbers = [1, 2, 3, 4, 5, 6]

    # Do not remove items directly from a list while iterating over that
    # same list unless the algorithm is deliberately designed for mutation.
    #
    # Build a new collection instead.
    even_numbers = [number for number in numbers if number % 2 == 0]

    print("Original:", numbers)
    print("Filtered:", even_numbers)


# ============================================================================
# 42. LOOP INVARIANTS AND ACCUMULATION
# ============================================================================

def sum_numbers(numbers: Iterable[int]) -> int:
    """
    Accumulate a total.

    Loop invariant:
        after processing each item, total equals the sum of all processed
        items.
    """
    total = 0

    for number in numbers:
        total += number

    return total


def demonstrate_accumulation() -> None:
    subsection("Accumulation")

    values = [4, 8, 15, 16, 23, 42]
    print("Sum:", sum_numbers(values))


# ============================================================================
# 43. COUNTING WITH A LOOP
# ============================================================================

def count_vowels(text: str) -> int:
    """Count vowels using branching inside a loop."""
    vowels = {"a", "e", "i", "o", "u"}
    count = 0

    for character in text.lower():
        if character in vowels:
            count += 1

    return count


def demonstrate_counting() -> None:
    subsection("Counting")

    text = "Control flow is fundamental to programming."
    print("Text:", text)
    print("Vowel count:", count_vowels(text))


# ============================================================================
# 44. SEARCH AND VALIDATION
# ============================================================================

def contains_duplicate(numbers: Sequence[int]) -> bool:
    """Stop immediately after detecting a duplicate."""
    seen: set[int] = set()

    for number in numbers:
        if number in seen:
            return True

        seen.add(number)

    return False


def demonstrate_search_and_validation() -> None:
    subsection("Search and validation")

    examples = [
        [1, 2, 3, 4],
        [1, 2, 3, 2],
        [],
    ]

    for example in examples:
        print(example, "contains duplicate:", contains_duplicate(example))


# ============================================================================
# 45. PRIME NUMBER GENERATION
# ============================================================================

def primes_up_to(limit: int) -> list[int]:
    """Generate prime numbers using trial division."""
    if limit < 2:
        return []

    primes: list[int] = []

    for candidate in range(2, limit + 1):
        is_prime = True

        for divisor in range(2, int(candidate**0.5) + 1):
            if candidate % divisor == 0:
                is_prime = False
                break

        if is_prime:
            primes.append(candidate)

    return primes


def demonstrate_prime_generation() -> None:
    subsection("Algorithmic branching")

    print("Primes up to 50:")
    print(primes_up_to(50))


# ============================================================================
# 46. FIZZBUZZ
# ============================================================================

def fizzbuzz(limit: int) -> list[str]:
    """
    Classic branching exercise.

    Order matters:
    multiples of both 3 and 5 must be checked before individual cases.
    """
    result: list[str] = []

    for number in range(1, limit + 1):
        if number % 15 == 0:
            result.append("FizzBuzz")
        elif number % 3 == 0:
            result.append("Fizz")
        elif number % 5 == 0:
            result.append("Buzz")
        else:
            result.append(str(number))

    return result


def demonstrate_fizzbuzz() -> None:
    subsection("FizzBuzz")

    print(fizzbuzz(20))


# ============================================================================
# 47. RETRY LOGIC
# ============================================================================

class TemporaryFailure(Exception):
    """Represents a retryable operation failure."""


def unreliable_operation(attempt: int) -> str:
    """
    Simulate an operation that fails for the first two attempts.
    """
    if attempt < 3:
        raise TemporaryFailure("Temporary failure")

    return "Operation succeeded."


def run_with_retry(max_attempts: int) -> str:
    """Retry only when the exception represents a temporary failure."""
    for attempt in range(1, max_attempts + 1):
        try:
            return unreliable_operation(attempt)
        except TemporaryFailure as error:
            print(f"Attempt {attempt} failed: {error}")

    return "Operation failed after all retries."


def demonstrate_retry_logic() -> None:
    subsection("Retry logic")

    print(run_with_retry(5))
    print(run_with_retry(2))


# ============================================================================
# 48. MENU-DRIVEN CONTROL FLOW
# ============================================================================

def menu_action(choice: str) -> str:
    """Implement a small command menu."""
    normalized = choice.strip().lower()

    if normalized == "start":
        return "Starting..."
    elif normalized == "pause":
        return "Paused."
    elif normalized == "stop":
        return "Stopped."
    elif normalized == "quit":
        return "Quitting..."
    else:
        return "Unknown command."


def demonstrate_menu_logic() -> None:
    subsection("Menu-driven branching")

    for choice in ["start", "pause", "stop", "invalid", "quit"]:
        print(choice, "->", menu_action(choice))


# ============================================================================
# 49. BOOLEAN FLAGS
# ============================================================================

def has_passing_subjects(scores: Sequence[float]) -> bool:
    """
    Demonstrate a flag-based approach.

    A flag is useful when a later action depends on something discovered
    during iteration.
    """
    passed = True

    for score in scores:
        if score < 40:
            passed = False
            break

    return passed


def demonstrate_flags() -> None:
    subsection("Boolean flags")

    print(has_passing_subjects([55, 61, 78]))
    print(has_passing_subjects([55, 31, 78]))


# ============================================================================
# 50. LOOP CONTROL WITH RETURN
# ============================================================================

def find_first_negative(numbers: Sequence[int]) -> int | None:
    """
    return exits both the loop and the containing function.
    """
    for number in numbers:
        if number < 0:
            return number

    return None


def demonstrate_return_control() -> None:
    subsection("return inside a loop")

    print(find_first_negative([4, 8, -2, 10]))
    print(find_first_negative([4, 8, 2, 10]))


# ============================================================================
# 51. PERFORMANCE: EARLY EXIT
# ============================================================================

def contains_value_linear(
    numbers: Sequence[int],
    target: int,
) -> bool:
    for number in numbers:
        if number == target:
            return True

    return False


def contains_value_with_set(
    numbers: Sequence[int],
    target: int,
) -> bool:
    return target in set(numbers)


def demonstrate_performance() -> None:
    subsection("Performance considerations")

    values = list(range(100_000))
    target = 99_999

    start = perf_counter()
    linear_result = contains_value_linear(values, target)
    linear_time = perf_counter() - start

    start = perf_counter()
    set_result = contains_value_with_set(values, target)
    set_time = perf_counter() - start

    print("Linear search result:", linear_result)
    print("Set-based result:", set_result)
    print(f"Linear search time: {linear_time:.6f} seconds")
    print(f"Set construction + lookup: {set_time:.6f} seconds)

    print(
        "For repeated membership checks, building a set can be worthwhile. "
        "For a single lookup, construction cost matters."
    )


# ============================================================================
# 52. COMPLEXITY OF NESTED LOOPS
# ============================================================================

def all_pairs(numbers: Sequence[int]) -> list[tuple[int, int]]:
    """Generate every ordered pair."""
    pairs: list[tuple[int, int]] = []

    for first in numbers:
        for second in numbers:
            pairs.append((first, second))

    return pairs


def demonstrate_nested_complexity() -> None:
    subsection("Nested-loop complexity")

    pairs = all_pairs([1, 2, 3])
    print("Pairs:", pairs)

    print(
        "A loop nested inside another loop often leads to O(n²) work "
        "when both loops process n items."
    )


# ============================================================================
# 53. LAZY ITERATION FOR LARGE DATA
# ============================================================================

def even_numbers(limit: int) -> Iterator[int]:
    """Yield even numbers lazily."""
    for number in range(limit + 1):
        if number % 2 == 0:
            yield number


def demonstrate_lazy_control_flow() -> None:
    subsection("Lazy iteration")

    generator = even_numbers(10)

    print("First value:", next(generator))
    print("Second value:", next(generator))

    print("Remaining values:")
    for number in generator:
        print(number)


# ============================================================================
# 54. CONTROL FLOW IN A DATA PIPELINE
# ============================================================================

@dataclass
class Transaction:
    transaction_id: int
    amount: float
    status: str


def approved_positive_amounts(
    transactions: Iterable[Transaction],
) -> list[float]:
    """
    Filter a transaction stream.

    Branching decisions:
    - skip transactions that are not approved,
    - skip non-positive amounts,
    - retain valid approved amounts.
    """
    amounts: list[float] = []

    for transaction in transactions:
        if transaction.status != "approved":
            continue

        if transaction.amount <= 0:
            continue

        amounts.append(transaction.amount)

    return amounts


def demonstrate_data_pipeline() -> None:
    subsection("Control flow in data processing")

    transactions = [
        Transaction(1, 1000, "approved"),
        Transaction(2, 500, "pending"),
        Transaction(3, -20, "approved"),
        Transaction(4, 750, "approved"),
    ]

    print(approved_positive_amounts(transactions))


# ============================================================================
# 55. CONDITIONAL AGGREGATION
# ============================================================================

def total_approved_amount(
    transactions: Iterable[Transaction],
) -> float:
    """Aggregate only approved transactions."""
    total = 0.0

    for transaction in transactions:
        if transaction.status == "approved":
            total += transaction.amount

    return total


def demonstrate_conditional_aggregation() -> None:
    subsection("Conditional aggregation")

    transactions = [
        Transaction(1, 100, "approved"),
        Transaction(2, 200, "rejected"),
        Transaction(3, 300, "approved"),
    ]

    print("Approved total:", total_approved_amount(transactions))


# ============================================================================
# 56. LOOPING OVER FILE-LIKE DATA
# ============================================================================

def parse_positive_integers(lines: Iterable[str]) -> list[int]:
    """
    Parse text records.

    Invalid lines are skipped deliberately.
    """
    values: list[int] = []

    for line in lines:
        text = line.strip()

        if not text:
            continue

        try:
            value = int(text)
        except ValueError:
            continue

        if value > 0:
            values.append(value)

    return values


def demonstrate_text_processing() -> None:
    subsection("Control flow in text processing")

    lines = ["10", "", "abc", "25", "-4", "  30  "]
    print("Parsed:", parse_positive_integers(lines))


# ============================================================================
# 57. CONTROL FLOW AND SECURITY VALIDATION
# ============================================================================

def validate_transfer(
    amount: float,
    daily_limit: float,
    available_balance: float,
    account_locked: bool,
) -> tuple[bool, str]:
    """
    Example of security-sensitive validation.

    Security-sensitive decisions should fail closed:
    invalid or unsafe states should not accidentally grant access.
    """
    if account_locked:
        return False, "Account is locked."

    if amount <= 0:
        return False, "Transfer amount must be positive."

    if amount > daily_limit:
        return False, "Daily transfer limit exceeded."

    if amount > available_balance:
        return False, "Insufficient balance."

    return True, "Transfer approved."


def demonstrate_security_validation() -> None:
    subsection("Security-oriented control flow")

    cases = [
        (100, 1000, 500, False),
        (1500, 1000, 5000, False),
        (100, 1000, 50, False),
        (100, 1000, 500, True),
    ]

    for case in cases:
        print(case, "->", validate_transfer(*case))


# ============================================================================
# 58. AVOIDING DANGEROUS ASSUMPTIONS
# ============================================================================

def get_discount(
    customer_type: str,
    order_total: float,
) -> float:
    """
    Apply discounts using explicit recognized states.

    Unknown customer types receive no discount rather than accidentally
    receiving privileged treatment.
    """
    normalized = customer_type.strip().lower()

    if order_total < 0:
        raise ValueError("Order total cannot be negative.")

    if normalized == "premium":
        return 0.20 if order_total >= 1000 else 0.10

    if normalized == "standard":
        return 0.05 if order_total >= 1000 else 0.0

    if normalized == "guest":
        return 0.0

    return 0.0


def demonstrate_safe_defaults() -> None:
    subsection("Explicit states and safe defaults")

    cases = [
        ("premium", 1500),
        ("premium", 500),
        ("standard", 1500),
        ("guest", 1500),
        ("unknown", 1500),
    ]

    for case in cases:
        print(case, "->", get_discount(*case))


# ============================================================================
# 59. TESTABLE CONTROL FLOW
# ============================================================================

def test_classify_score() -> None:
    """Simple assertion-based tests."""
    assert classify_score(95) == "A"
    assert classify_score(85) == "B"
    assert classify_score(75) == "C"
    assert classify_score(65) == "D"
    assert classify_score(40) == "F"
    assert classify_score(-1) == "invalid"
    assert classify_score(101) == "invalid"


def test_prime_logic() -> None:
    """Test important boundary cases for prime detection."""
    assert find_prime(-10) is False
    assert find_prime(0) is False
    assert find_prime(1) is False
    assert find_prime(2) is True
    assert find_prime(3) is True
    assert find_prime(4) is False
    assert find_prime(13) is True
    assert find_prime(25) is False


def test_shipping_rules() -> None:
    """Test representative branches and edge conditions."""
    assert calculate_shipping_cost(1000, 100, False, False) == 0
    assert calculate_shipping_cost(500, 5, False, False) == 50
    assert calculate_shipping_cost(500, 15, False, False) == 100
    assert calculate_shipping_cost(500, 16, False, False) == 150
    assert calculate_shipping_cost(500, 16, True, False) == 0
    assert calculate_shipping_cost(500, 16, True, True) == 100


def run_tests() -> None:
    subsection("Control-flow tests")

    test_classify_score()
    test_prime_logic()
    test_shipping_rules()

    print("All assertions passed.")


# ============================================================================
# 60. DEBUGGING CONTROL FLOW
# ============================================================================

def debug_grade_pipeline(scores: Sequence[float]) -> list[str]:
    """
    A small function suitable for debugging.

    The explicit intermediate variable makes the decision process visible.
    """
    labels: list[str] = []

    for score in scores:
        if score < 0 or score > 100:
            label = "invalid"
        elif score >= 90:
            label = "excellent"
        elif score >= 60:
            label = "pass"
        else:
            label = "fail"

        labels.append(label)

    return labels


def demonstrate_debugging() -> None:
    subsection("Debugging branch logic")

    scores = [95, 75, 45, 110, -1]
    print("Scores:", scores)
    print("Labels:", debug_grade_pipeline(scores))

    print(
        "Useful debugging questions include: "
        "Which branch executed? What values entered the condition? "
        "Was the condition ordered correctly? Did the loop terminate?"
    )


# ============================================================================
# 61. REFACTORING DEEPLY NESTED CONDITIONS
# ============================================================================

def deeply_nested_decision(
    user_exists: bool,
    account_active: bool,
    has_permission: bool,
) -> str:
    if user_exists:
        if account_active:
            if has_permission:
                return "Access granted."
            return "Permission denied."
        return "Account inactive."
    return "User not found."


def flattened_decision(
    user_exists: bool,
    account_active: bool,
    has_permission: bool,
) -> str:
    if not user_exists:
        return "User not found."

    if not account_active:
        return "Account inactive."

    if not has_permission:
        return "Permission denied."

    return "Access granted."


def demonstrate_refactoring() -> None:
    subsection("Reducing unnecessary nesting")

    scenarios = [
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
    ]

    for scenario in scenarios:
        nested = deeply_nested_decision(*scenario)
        flat = flattened_decision(*scenario)

        assert nested == flat
        print(scenario, "->", flat)


# ============================================================================
# 62. COMPARING IF/ELIF WITH DISPATCH
# ============================================================================

def status_with_if(status: str) -> str:
    if status == "pending":
        return "Waiting"
    elif status == "approved":
        return "Accepted"
    elif status == "rejected":
        return "Declined"
    else:
        return "Unknown"


STATUS_MESSAGES = {
    "pending": "Waiting",
    "approved": "Accepted",
    "rejected": "Declined",
}


def status_with_mapping(status: str) -> str:
    return STATUS_MESSAGES.get(status, "Unknown")


def demonstrate_branching_strategies() -> None:
    subsection("Alternative branching strategies")

    statuses = ["pending", "approved", "rejected", "other"]

    for status in statuses:
        print(
            status,
            "if/elif =",
            status_with_if(status),
            "mapping =",
            status_with_mapping(status),
        )

    print(
        "if/elif is often clearer for ranges, complex conditions, or "
        "different actions. A mapping is useful when values directly map "
        "to outputs."
    )


# ============================================================================
# 63. PATTERN MATCHING WITH GUARDS
# ============================================================================

def classify_point(point: tuple[int, int]) -> str:
    """Use pattern matching plus guards."""
    match point:
        case (0, 0):
            return "origin"
        case (x, 0) if x > 0:
            return "positive x-axis"
        case (x, 0):
            return "negative x-axis"
        case (0, y) if y > 0:
            return "positive y-axis"
        case (0, y):
            return "negative y-axis"
        case (x, y) if x > 0 and y > 0:
            return "first quadrant"
        case (x, y) if x < 0 and y > 0:
            return "second quadrant"
        case (x, y) if x < 0 and y < 0:
            return "third quadrant"
        case (x, y):
            return "fourth quadrant"


def demonstrate_match_guards() -> None:
    subsection("Pattern matching with guards")

    points = [
        (0, 0),
        (5, 0),
        (-5, 0),
        (0, 5),
        (0, -5),
        (2, 3),
        (-2, 3),
        (-2, -3),
        (2, -3),
    ]

    for point in points:
        print(point, "->", classify_point(point))


# ============================================================================
# 64. A MINI RULE ENGINE
# ============================================================================

@dataclass(frozen=True)
class Rule:
    name: str
    condition: Callable[[dict[str, object]], bool]
    action: Callable[[dict[str, object]], str]


def premium_rule(context: dict[str, object]) -> bool:
    return (
        context.get("customer_type") == "premium"
        and float(context.get("order_total", 0)) >= 1000
    )


def premium_action(_: dict[str, object]) -> str:
    return "Apply 20% premium discount."


def member_rule(context: dict[str, object]) -> bool:
    return context.get("is_member") is True


def member_action(_: dict[str, object]) -> str:
    return "Apply 10% member discount."


def default_action(_: dict[str, object]) -> str:
    return "No special discount."


RULES = [
    Rule("premium", premium_rule, premium_action),
    Rule("member", member_rule, member_action),
]


def evaluate_rules(context: dict[str, object]) -> str:
    """Return the action associated with the first matching rule."""
    for rule in RULES:
        if rule.condition(context):
            return rule.action(context)

    return default_action(context)


def demonstrate_rule_engine() -> None:
    subsection("Rule-engine pattern")

    contexts = [
        {"customer_type": "premium", "order_total": 1500, "is_member": False},
        {"customer_type": "standard", "order_total": 500, "is_member": True},
        {"customer_type": "standard", "order_total": 500, "is_member": False},
    ]

    for context in contexts:
        print(context, "->", evaluate_rules(context))


# ============================================================================
# 65. PRACTICAL MINI-PROJECT: ATM CONTROL FLOW
# ============================================================================

@dataclass
class ATM:
    balance: float
    pin: str
    attempts_remaining: int = 3
    locked: bool = False

    def authenticate(self, entered_pin: str) -> bool:
        if self.locked:
            return False

        if entered_pin == self.pin:
            self.attempts_remaining = 3
            return True

        self.attempts_remaining -= 1

        if self.attempts_remaining <= 0:
            self.locked = True

        return False

    def withdraw(self, amount: float) -> str:
        if self.locked:
            return "ATM is locked."

        if amount <= 0:
            return "Amount must be positive."

        if amount % 100 != 0:
            return "Amount must be a multiple of 100."

        if amount > self.balance:
            return "Insufficient balance."

        self.balance -= amount
        return f"Withdrawal successful. Remaining balance: {self.balance:.2f}"


def demonstrate_atm() -> None:
    subsection("Mini-project: ATM")

    atm = ATM(balance=10_000, pin="1234")

    for entered_pin in ["0000", "1234"]:
        print("PIN accepted:", atm.authenticate(entered_pin))

    print(atm.withdraw(150))
    print(atm.withdraw(1000))
    print(atm.withdraw(20_000))
    print(atm.withdraw(-100))


# ============================================================================
# 66. PRACTICAL MINI-PROJECT: NUMBER GUESSING SIMULATION
# ============================================================================

def evaluate_guess(secret: int, guess: int) -> str:
    if guess < secret:
        return "Too low."
    elif guess > secret:
        return "Too high."
    else:
        return "Correct."


def run_guess_simulation(secret: int, guesses: Iterable[int]) -> str:
    """Use a loop and break on a successful guess."""
    attempts = 0

    for guess in guesses:
        attempts += 1
        message = evaluate_guess(secret, guess)
        print(f"Attempt {attempts}: {guess} -> {message}")

        if guess == secret:
            return f"Won in {attempts} attempts."

    return "No correct guess."


def demonstrate_guessing() -> None:
    subsection("Mini-project: guessing simulation")

    print(run_guess_simulation(42, [10, 50, 30, 42]))


# ============================================================================
# 67. PRACTICAL MINI-PROJECT: LOGIN CONTROL FLOW
# ============================================================================

@dataclass
class LoginSystem:
    correct_username: str
    correct_password: str
    max_attempts: int = 3

    def login(self, attempts: Iterable[tuple[str, str]]) -> str:
        attempt_number = 0

        for username, password in attempts:
            attempt_number += 1

            if attempt_number > self.max_attempts:
                return "Account temporarily locked."

            if username != self.correct_username:
                print("Unknown username.")
                continue

            if password != self.correct_password:
                print("Incorrect password.")
                continue

            return "Login successful."

        if attempt_number >= self.max_attempts:
            return "Login failed. Attempt limit reached."

        return "Login failed."


def demonstrate_login() -> None:
    subsection("Mini-project: login validation")

    system = LoginSystem("admin", "secure123")

    attempts = [
        ("admin", "wrong"),
        ("unknown", "secure123"),
        ("admin", "secure123"),
    ]

    print(system.login(attempts))


# ============================================================================
# 68. PRACTICAL MINI-PROJECT: TRAFFIC LIGHT
# ============================================================================

def traffic_light_action(light: str) -> str:
    normalized = light.strip().lower()

    match normalized:
        case "red":
            return "Stop."
        case "yellow":
            return "Prepare to stop."
        case "green":
            return "Proceed."
        case _:
            return "Invalid signal."


def demonstrate_traffic_light() -> None:
    subsection("Mini-project: traffic-light branching")

    for light in ["red", "yellow", "green", "blue"]:
        print(light, "->", traffic_light_action(light))


# ============================================================================
# 69. CONTROL FLOW PITFALLS
# ============================================================================

def demonstrate_common_mistakes() -> None:
    subsection("Common mistakes")

    print("Mistake 1: assignment versus comparison")
    print("Correct comparison uses ==, not =.")

    print("Mistake 2: forgetting to update a while-loop variable.")
    print("A loop such as while count < 5 requires progress toward termination.")

    print("Mistake 3: incorrect condition ordering.")
    print("A broad condition can prevent later, more specific branches.")

    print("Mistake 4: accidental truthiness.")
    print("if value checks truthiness, not necessarily value == True.")

    print("Mistake 5: changing a collection while iterating over it.")
    print("Prefer filtering into a new collection when practical.")

    print("Mistake 6: excessive nesting.")
    print("Guard clauses and extracted functions can simplify decision logic.")

    print("Mistake 7: catching every exception indiscriminately.")
    print("Catch specific expected exceptions and allow programming errors to surface.")

    print("Mistake 8: assuming zip() detects unequal lengths.")
    print("Normal zip() stops at the shortest iterable; strict=True detects mismatch.")


# ============================================================================
# 70. CONTROL FLOW DESIGN PRINCIPLES
# ============================================================================

def demonstrate_design_principles() -> None:
    subsection("Control-flow design principles")

    principles = [
        "Keep conditions understandable.",
        "Use meaningful names instead of complicated expressions.",
        "Validate input before performing sensitive operations.",
        "Prefer guard clauses when they reduce nesting.",
        "Use early exit when later work is unnecessary.",
        "Keep loop bodies focused.",
        "Use the appropriate data structure for repeated membership checks.",
        "Avoid accidental infinite loops.",
        "Test boundary conditions and every important branch.",
        "Make failure states explicit.",
        "Prefer clear control flow over clever but obscure expressions.",
    ]

    for number, principle in enumerate(principles, start=1):
        print(f"{number}. {principle}")


# ============================================================================
# 71. BRANCH COVERAGE THINKING
# ============================================================================

def classify_temperature(celsius: float) -> str:
    if celsius < 0:
        return "freezing"
    elif celsius < 15:
        return "cold"
    elif celsius < 30:
        return "moderate"
    elif celsius < 40:
        return "hot"
    else:
        return "extreme"


def demonstrate_branch_coverage() -> None:
    subsection("Testing branches")

    test_values = [-10, 0, 14.9, 15, 29.9, 30, 39.9, 40]

    for value in test_values:
        print(value, "->", classify_temperature(value))

    print(
        "Boundary-oriented testing is important because branch conditions "
        "often change behavior exactly at threshold values."
    )


# ============================================================================
# 72. PERFORMANCE: BREAK VERSUS FULL SCAN
# ============================================================================

def find_first_even(numbers: Sequence[int]) -> int | None:
    for number in numbers:
        if number % 2 == 0:
            return number

    return None


def demonstrate_early_exit_performance() -> None:
    subsection("Early exit and performance")

    values = [2] + list(range(1, 100_000))

    start = perf_counter()
    result = find_first_even(values)
    elapsed = perf_counter() - start

    print("First even:", result)
    print(f"Time with immediate return: {elapsed:.8f} seconds")

    print(
        "Early termination can reduce work dramatically when a result is "
        "usually found before the end of the input."
    )


# ============================================================================
# 73. CONTROL FLOW WITH OPTIONAL VALUES
# ============================================================================

def format_name(first_name: str | None, last_name: str | None) -> str:
    """Handle missing optional values explicitly."""
    if first_name is None and last_name is None:
        return "Unknown"

    if first_name is None:
        return last_name or "Unknown"

    if last_name is None:
        return first_name

    return f"{first_name} {last_name}"


def demonstrate_optional_values() -> None:
    subsection("Optional values and None")

    cases = [
        ("Atul", "Pandey"),
        ("Atul", None),
        (None, "Pandey"),
        (None, None),
    ]

    for case in cases:
        print(case, "->", format_name(*case))


# ============================================================================
# 74. CONTROL FLOW WITH ENUMS
# ============================================================================

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def response_time(priority: Priority) -> int:
    """Return a response target in minutes."""
    if priority == Priority.CRITICAL:
        return 5
    elif priority == Priority.HIGH:
        return 30
    elif priority == Priority.MEDIUM:
        return 120
    else:
        return 480


def demonstrate_enum_branching() -> None:
    subsection("Enum-based branching")

    for priority in Priority:
        print(priority.value, "->", response_time(priority), "minutes")


# ============================================================================
# 75. CONTROL FLOW WITH OBJECT STATE
# ============================================================================

@dataclass
class BankAccount:
    balance: float = 0.0
    frozen: bool = False

    def deposit(self, amount: float) -> str:
        if self.frozen:
            return "Account is frozen."

        if amount <= 0:
            return "Deposit must be positive."

        self.balance += amount
        return f"Deposited {amount:.2f}. Balance: {self.balance:.2f}"

    def withdraw(self, amount: float) -> str:
        if self.frozen:
            return "Account is frozen."

        if amount <= 0:
            return "Withdrawal must be positive."

        if amount > self.balance:
            return "Insufficient funds."

        self.balance -= amount
        return f"Withdrew {amount:.2f}. Balance: {self.balance:.2f}"


def demonstrate_object_control_flow() -> None:
    subsection("Control flow with object state")

    account = BankAccount(balance=1000)

    print(account.deposit(500))
    print(account.withdraw(200))
    print(account.withdraw(2000))

    account.frozen = True
    print(account.deposit(100))


# ============================================================================
# 76. ADVANCED: CONTROL FLOW ABSTRACTION
# ============================================================================

def apply_if(
    condition: bool,
    true_action: Callable[[], str],
    false_action: Callable[[], str],
) -> str:
    """
    Demonstrate passing behavior as functions.

    This is intentionally illustrative. For ordinary application logic,
    a direct if/else is often clearer.
    """
    if condition:
        return true_action()

    return false_action()


def demonstrate_behavior_as_data() -> None:
    subsection("Behavior as data")

    result = apply_if(
        10 > 5,
        lambda: "Condition was true.",
        lambda: "Condition was false.",
    )

    print(result)


# ============================================================================
# 77. ADVANCED: SHORT-CIRCUIT DEFAULT VALUES
# ============================================================================

def demonstrate_default_selection() -> None:
    subsection("Short-circuit value selection")

    configured_name = ""
    fallback_name = "Default User"

    display_name = configured_name or fallback_name

    print("Display name:", display_name)

    configured_timeout = 0
    timeout = configured_timeout or 30

    print("Timeout:", timeout)

    print(
        "The pattern is useful when zero or an empty string genuinely means "
        "'missing'. It is not appropriate when zero is a valid intentional value."
    )


# ============================================================================
# 78. ADVANCED: SENTINEL VALUES
# ============================================================================

_MISSING = object()


def lookup_setting(
    settings: dict[str, object],
    key: str,
) -> object:
    """
    Use a unique sentinel to distinguish:
    - key absent
    - key present with value None
    """
    value = settings.get(key, _MISSING)

    if value is _MISSING:
        return "setting is absent"

    if value is None:
        return "setting exists with None"

    return value


def demonstrate_sentinel() -> None:
    subsection("Sentinel-based branching")

    settings = {
        "name": None,
        "timeout": 30,
    }

    print(lookup_setting(settings, "name"))
    print(lookup_setting(settings, "timeout"))
    print(lookup_setting(settings, "missing"))


# ============================================================================
# 79. ADVANCED: WALRUS OPERATOR IN CONDITIONS
# ============================================================================

def demonstrate_assignment_expression() -> None:
    subsection("Assignment expressions")

    values = ["10", "20", "30"]

    iterator = iter(values)

    while (value := next(iterator, None)) is not None:
        print("Read:", value)

    print(
        "The := operator can assign and test a value in one expression. "
        "It should be used only when it improves clarity."
    )


# ============================================================================
# 80. ADVANCED: STRUCTURAL PATTERN MATCHING
# ============================================================================

def describe_command(command: object) -> str:
    """
    Match several shapes of input data.
    """
    match command:
        case {"action": "create", "name": str(name)}:
            return f"Create record {name}."

        case {"action": "delete", "id": int(record_id)}:
            return f"Delete record {record_id}."

        case ["add", int(a), int(b)]:
            return f"Add result: {a + b}."

        case _:
            return "Unsupported command."


def demonstrate_structural_matching() -> None:
    subsection("Structural pattern matching")

    commands: list[object] = [
        {"action": "create", "name": "Project"},
        {"action": "delete", "id": 42},
        ["add", 10, 20],
        {"action": "unknown"},
    ]

    for command in commands:
        print(command, "->", describe_command(command))


# ============================================================================
# 81. ADVANCED: CONTROL FLOW AND RESOURCE MANAGEMENT
# ============================================================================

def demonstrate_context_control_flow() -> None:
    subsection("Context managers")

    # A context manager controls setup and cleanup around a block.
    # This example uses an in-memory standard-library object so no external
    # file is created.
    from io import StringIO

    with StringIO("line one\nline two\n") as stream:
        for line in stream:
            cleaned = line.strip()

            if not cleaned:
                continue

            print("Processed:", cleaned)

    print("The context manager has completed cleanup.")


# ============================================================================
# 82. ADVANCED: ASYNC CONTROL FLOW CONCEPT
# ============================================================================

def explain_async_control_flow() -> None:
    subsection("Asynchronous control flow")

    print(
        "Asynchronous programs introduce await points where execution can "
        "cooperate with other tasks while waiting for I/O."
    )
    print(
        "The important control-flow distinction is that waiting for I/O "
        "does not necessarily mean blocking the entire event loop."
    )
    print(
        "This standalone script does not perform network I/O, so no external "
        "async package or service is required."
    )


# ============================================================================
# 83. CONTROL FLOW DECISION TABLE
# ============================================================================

def demonstrate_decision_table() -> None:
    subsection("Decision-table thinking")

    decisions = [
        ("age < 18", "deny"),
        ("age >= 18 and no ID", "deny"),
        ("age >= 18 and ID", "allow"),
    ]

    for condition, outcome in decisions:
        print(f"{condition:30} -> {outcome}")

    print(
        "For complicated business logic, writing the possible states and "
        "outcomes explicitly can reveal missing branches and contradictory rules."
    )


# ============================================================================
# 84. CONTROL FLOW AND INVARIANTS
# ============================================================================

def running_maximum(numbers: Iterable[int]) -> list[int]:
    """Track a running maximum."""
    result: list[int] = []
    current_max: int | None = None

    for number in numbers:
        if current_max is None or number > current_max:
            current_max = number

        result.append(current_max)

    return result


def demonstrate_invariants() -> None:
    subsection("Maintaining state through loops")

    values = [4, 2, 9, 3, 12, 1]
    print("Values:", values)
    print("Running maximum:", running_maximum(values))


# ============================================================================
# 85. PRACTICAL: GRADEBOOK PROCESSOR
# ============================================================================

def process_gradebook(
    records: Sequence[tuple[str, Sequence[float]]],
) -> dict[str, str]:
    """
    Classify students using average score.

    Empty score lists are explicitly handled.
    """
    result: dict[str, str] = {}

    for name, scores in records:
        if not scores:
            result[name] = "no scores"
            continue

        average = sum(scores) / len(scores)

        if average >= 90:
            result[name] = "excellent"
        elif average >= 75:
            result[name] = "good"
        elif average >= 40:
            result[name] = "pass"
        else:
            result[name] = "fail"

    return result


def demonstrate_gradebook() -> None:
    subsection("Practical gradebook processor")

    records = [
        ("Asha", [90, 95, 88]),
        ("Ravi", [75, 78, 80]),
        ("Meera", [40, 45, 39]),
        ("Kabir", [20, 30, 25]),
        ("Nisha", []),
    ]

    print(process_gradebook(records))


# ============================================================================
# 86. PRACTICAL: INVENTORY PROCESSOR
# ============================================================================

@dataclass
class Product:
    name: str
    stock: int
    reorder_level: int


def inventory_actions(products: Iterable[Product]) -> list[str]:
    """Identify inventory states."""
    actions: list[str] = []

    for product in products:
        if product.stock < 0:
            actions.append(f"{product.name}: invalid stock")
            continue

        if product.stock == 0:
            actions.append(f"{product.name}: out of stock")
        elif product.stock <= product.reorder_level:
            actions.append(f"{product.name}: reorder")
        else:
            actions.append(f"{product.name}: sufficient stock")

    return actions


def demonstrate_inventory() -> None:
    subsection("Practical inventory processor")

    products = [
        Product("Laptop", 10, 5),
        Product("Mouse", 3, 5),
        Product("Keyboard", 0, 5),
        Product("Monitor", -1, 2),
    ]

    for action in inventory_actions(products):
        print(action)


# ============================================================================
# 87. PRACTICAL: ACCESS CONTROL
# ============================================================================

@dataclass
class User:
    username: str
    role: str
    active: bool


def authorize(
    user: User | None,
    required_role: str,
) -> tuple[bool, str]:
    """Perform ordered authorization checks."""
    if user is None:
        return False, "Authentication required."

    if not user.active:
        return False, "Account inactive."

    if user.role != required_role:
        return False, "Insufficient privileges."

    return True, "Access granted."


def demonstrate_authorization() -> None:
    subsection("Practical authorization")

    users = [
        None,
        User("alice", "admin", False),
        User("bob", "user", True),
        User("carol", "admin", True),
    ]

    for user in users:
        print(authorize(user, "admin"))


# ============================================================================
# 88. CONTROL FLOW WITH EXCEPTIONS: FINALLY
# ============================================================================

def demonstrate_finally() -> None:
    subsection("finally")

    for denominator in [2, 0]:
        try:
            result = 10 / denominator
        except ZeroDivisionError:
            print("Cannot divide by zero.")
        else:
            print("Result:", result)
        finally:
            print("Cleanup step executes for denominator:", denominator)


# ============================================================================
# 89. COMMON LOOP PATTERNS
# ============================================================================

def demonstrate_common_loop_patterns() -> None:
    subsection("Common loop patterns")

    # Counter
    count = 0
    for _ in range(5):
        count += 1
    print("Counter:", count)

    # Accumulator
    total = 0
    for number in range(1, 6):
        total += number
    print("Accumulator:", total)

    # Search
    found = False
    for number in [3, 7, 9]:
        if number == 7:
            found = True
            break
    print("Found:", found)

    # Filter
    filtered = []
    for number in range(10):
        if number % 2 == 0:
            filtered.append(number)
    print("Filtered:", filtered)

    # Transform
    transformed = []
    for number in range(5):
        transformed.append(number**2)
    print("Transformed:", transformed)


# ============================================================================
# 90. ADVANCED COMBINED EXAMPLE: FRAUD SCREENING
# ============================================================================

@dataclass
class Payment:
    amount: float
    country: str
    attempts: int
    customer_age: int
    known_device: bool


def fraud_screen(payment: Payment) -> tuple[str, list[str]]:
    """
    A deterministic rule-based screening example.

    This demonstrates:
    - validation,
    - multiple conditions,
    - flags,
    - early rejection,
    - accumulation of reasons,
    - final classification.
    """
    reasons: list[str] = []

    if payment.amount <= 0:
        return "rejected", ["Invalid payment amount."]

    if payment.customer_age < 18:
        return "rejected", ["Customer does not meet age requirement."]

    if payment.attempts > 5:
        reasons.append("Too many payment attempts.")

    if not payment.known_device:
        reasons.append("Unknown device.")

    high_risk_countries = {"X", "Y"}
    if payment.country.upper() in high_risk_countries:
        reasons.append("High-risk country.")

    if payment.amount >= 100_000:
        reasons.append("Unusually large transaction.")

    if len(reasons) >= 3:
        return "blocked", reasons

    if reasons:
        return "review", reasons

    return "approved", reasons


def demonstrate_fraud_screening() -> None:
    subsection("Combined example: fraud screening")

    payments = [
        Payment(500, "IN", 1, 30, True),
        Payment(150_000, "IN", 1, 30, True),
        Payment(200, "X", 7, 30, False),
        Payment(0, "IN", 1, 30, True),
    ]

    for payment in payments:
        decision, reasons = fraud_screen(payment)
        print(payment)
        print("Decision:", decision)
        print("Reasons:", reasons)


# ============================================================================
# 91. CONTROL FLOW CHECKLIST
# ============================================================================

def print_control_flow_checklist() -> None:
    subsection("Control-flow checklist")

    checklist = [
        "Is every important condition explicit?",
        "Are boundary values handled?",
        "Can a while loop fail to terminate?",
        "Does every loop make measurable progress?",
        "Could an early return simplify the function?",
        "Does branch ordering match business priority?",
        "Are unexpected values handled safely?",
        "Are empty collections handled?",
        "Are None values handled where relevant?",
        "Could short-circuit evaluation change whether an expression runs?",
        "Could a loop process unnecessarily large amounts of data?",
        "Are exception handlers specific enough?",
        "Are important branches covered by tests?",
        "Is the code easier to understand than the alternative?",
    ]

    for item in checklist:
        print("[ ]", item)


# ============================================================================
# 92. MAIN DEMONSTRATION
# ============================================================================

def main() -> None:
    section("CONTROL FLOW: CONDITIONS, LOOPS, AND BRANCHING")

    demonstrate_sequential_execution()
    demonstrate_boolean_logic()
    demonstrate_truthiness()

    demonstrate_if()
    demonstrate_if_else()
    demonstrate_elif()
    demonstrate_branch_order()
    demonstrate_nested_conditions()
    demonstrate_logical_operators()
    demonstrate_short_circuiting()
    demonstrate_conditional_expression()
    demonstrate_match_case()

    demonstrate_for_loops()
    demonstrate_iteration()
    demonstrate_enumerate()
    demonstrate_zip()
    demonstrate_while()
    demonstrate_loop_termination()
    demonstrate_break()
    demonstrate_continue()
    demonstrate_pass()
    demonstrate_loop_else()
    demonstrate_nested_loops()
    demonstrate_matrix_search()
    demonstrate_nested_loop_exit()

    demonstrate_comprehensions()
    demonstrate_generator_expression()
    demonstrate_early_return()
    demonstrate_guard_clauses()
    demonstrate_input_validation()
    demonstrate_exception_control_flow()

    demonstrate_state_machine()
    demonstrate_dispatch_table()
    demonstrate_recursion()
    demonstrate_iterator_control()
    demonstrate_any_all()
    demonstrate_sorted_control()
    demonstrate_business_rules()

    demonstrate_edge_cases()
    demonstrate_off_by_one()
    demonstrate_safe_collection_filtering()
    demonstrate_accumulation()
    demonstrate_counting()
    demonstrate_search_and_validation()
    demonstrate_prime_generation()
    demonstrate_fizzbuzz()
    demonstrate_retry_logic()
    demonstrate_menu_logic()
    demonstrate_flags()
    demonstrate_return_control()

    demonstrate_performance()
    demonstrate_lazy_control_flow()
    demonstrate_data_pipeline()
    demonstrate_conditional_aggregation()
    demonstrate_text_processing()
    demonstrate_security_validation()
    demonstrate_safe_defaults()

    run_tests()
    demonstrate_debugging()
    demonstrate_refactoring()
    demonstrate_branching_strategies()
    demonstrate_match_guards()
    demonstrate_rule_engine()

    demonstrate_atm()
    demonstrate_guessing()
    demonstrate_login()
    demonstrate_traffic_light()
    demonstrate_common_mistakes()
    demonstrate_design_principles()
    demonstrate_branch_coverage()
    demonstrate_early_exit_performance()
    demonstrate_optional_values()
    demonstrate_enum_branching()
    demonstrate_object_control_flow()
    demonstrate_behavior_as_data()
    demonstrate_default_selection()
    demonstrate_sentinel()
    demonstrate_assignment_expression()
    demonstrate_structural_matching()
    demonstrate_context_control_flow()
    explain_async_control_flow()
    demonstrate_decision_table()
    demonstrate_invariants()

    demonstrate_gradebook()
    demonstrate_inventory()
    demonstrate_authorization()
    demonstrate_finally()
    demonstrate_common_loop_patterns()
    demonstrate_fraud_screening()

    print_control_flow_checklist()

    section("END OF CONTROL-FLOW STUDY SCRIPT")
    print(
        "All demonstrations completed. "
        "The script can be read from top to bottom as a structured study file."
    )


if __name__ == "__main__":
    main()
