"""
FUNCTIONS IN PYTHON
===================

Topic:
Functions, Parameters, Return Values, Scope, and Reusable Logic

This standalone study script progresses from absolute beginner concepts to
advanced function design, including:

1. What functions are and why they exist
2. Defining and calling functions
3. Parameters and arguments
4. Positional and keyword arguments
5. Default parameters
6. Return values
7. Multiple return values
8. Local, global, and nonlocal scope
9. Name resolution and LEGB
10. Mutable and immutable arguments
11. Pass-by-object-reference behavior
12. *args and **kwargs
13. Positional-only and keyword-only parameters
14. Type annotations
15. Docstrings
16. Functions as first-class objects
17. Higher-order functions
18. Nested functions
19. Closures
20. Decorators
21. Lambda functions
22. Recursion
23. Generator functions
24. Function factories
25. Partial application
26. Callable objects
27. Error handling and validation
28. Testing functions
29. Memoization and caching
30. Performance considerations
31. API design principles
32. Common mistakes and edge cases
33. Practical reusable mini-projects

The script uses only the Python standard library.
"""

from __future__ import annotations

from functools import lru_cache, partial, wraps
from inspect import signature
from math import factorial, sqrt
from statistics import mean
from time import perf_counter
from typing import Any, Callable, Iterable, Iterator, Optional


# =============================================================================
# 1. THE BASIC IDEA OF A FUNCTION
# =============================================================================

# A function is a named, reusable block of logic.
#
# Syntax:
#
# def function_name():
#     statements
#
# Calling the function:
#
# function_name()
#
# A function does not execute merely because it is defined.
# The body runs when the function is called.

def say_hello() -> None:
    """Print a simple greeting."""
    print("Hello from a function!")


say_hello()


# A function can be called multiple times.
say_hello()
say_hello()


# =============================================================================
# 2. FUNCTIONS WITH PARAMETERS
# =============================================================================

# A parameter is a variable listed in a function definition.
# An argument is the actual value supplied when calling the function.

def greet_person(name: str) -> None:
    """Print a personalized greeting."""
    print(f"Hello, {name}!")


greet_person("Atul")
greet_person("Priya")


def add_numbers(first_number: float, second_number: float) -> float:
    """Return the sum of two numbers."""
    return first_number + second_number


print("Addition:", add_numbers(10, 20))


# A parameter receives a value only for that function call.
# Different calls can provide different values.

print(add_numbers(5, 7))
print(add_numbers(100, 250))


# =============================================================================
# 3. RETURN VALUES
# =============================================================================

# print() displays something.
# return sends a value back to the caller.
#
# These are fundamentally different operations.

def calculate_square(number: float) -> float:
    """Return the square of a number."""
    return number * number


square_result = calculate_square(8)
print("Square:", square_result)


def calculate_cube(number: float) -> float:
    """Return the cube of a number."""
    return number ** 3


cube_result = calculate_cube(4)
print("Cube:", cube_result)


# A function stops executing when return is reached.

def return_example() -> str:
    """Demonstrate that statements after return are not executed."""
    return "Function finished"
    # This line is unreachable.
    # print("This will never execute.")


print(return_example())


# A function without an explicit return returns None.

def display_message(message: str) -> None:
    """Display a message without returning a useful value."""
    print(message)


result = display_message("Displayed on screen")
print("Returned value:", result)


# =============================================================================
# 4. MULTIPLE RETURN VALUES
# =============================================================================

# Python allows a function to return multiple values.
# Technically, Python packs them into a tuple.

def calculate_basic_operations(
    first_number: float,
    second_number: float,
) -> tuple[float, float, float, float]:
    """Return addition, subtraction, multiplication, and division."""
    if second_number == 0:
        raise ValueError("Division by zero is not allowed.")

    addition = first_number + second_number
    subtraction = first_number - second_number
    multiplication = first_number * second_number
    division = first_number / second_number

    return addition, subtraction, multiplication, division


addition, subtraction, multiplication, division = calculate_basic_operations(20, 5)

print("Add:", addition)
print("Subtract:", subtraction)
print("Multiply:", multiplication)
print("Divide:", division)


# =============================================================================
# 5. POSITIONAL ARGUMENTS
# =============================================================================

def introduce_person(name: str, age: int, city: str) -> str:
    """Create a short introduction."""
    return f"{name} is {age} years old and lives in {city}."


print(introduce_person("Atul", 30, "Lucknow"))


# Positional arguments are matched according to their position.
print(introduce_person("Priya", 28, "Delhi"))


# =============================================================================
# 6. KEYWORD ARGUMENTS
# =============================================================================

# Keyword arguments explicitly identify the parameter name.

print(
    introduce_person(
        name="Rahul",
        age=35,
        city="Mumbai",
    )
)


# Keyword arguments can be supplied in a different order.

print(
    introduce_person(
        city="Pune",
        name="Neha",
        age=27,
    )
)


# Positional arguments must appear before keyword arguments.

print(
    introduce_person(
        "Amit",
        city="Bengaluru",
        age=31,
    )
)


# =============================================================================
# 7. DEFAULT PARAMETERS
# =============================================================================

# A default parameter value is used when the caller does not provide
# an argument for that parameter.

def greet_with_title(name: str, title: str = "Mr.") -> str:
    """Return a greeting with a default title."""
    return f"Hello {title} {name}"


print(greet_with_title("Sharma"))
print(greet_with_title("Sharma", "Dr."))


def calculate_discount(price: float, discount_rate: float = 10.0) -> float:
    """Return the price after applying a percentage discount."""
    if price < 0:
        raise ValueError("Price cannot be negative.")

    if not 0 <= discount_rate <= 100:
        raise ValueError("Discount rate must be between 0 and 100.")

    return price * (1 - discount_rate / 100)


print("Discounted price:", calculate_discount(1000))
print("Discounted price:", calculate_discount(1000, 25))


# =============================================================================
# 8. IMPORTANT DEFAULT-ARGUMENT PITFALL: MUTABLE DEFAULTS
# =============================================================================

# Do NOT normally use mutable objects such as [] or {} as default values
# when the function intends to create a fresh object for every call.
#
# Problematic pattern:
#
# def add_item(item, items=[]):
#     items.append(item)
#     return items
#
# The same list would be reused between calls.

# Correct pattern:

def add_item(item: str, items: Optional[list[str]] = None) -> list[str]:
    """Add an item to a fresh list unless an existing list is supplied."""
    if items is None:
        items = []

    items.append(item)
    return items


print("Fresh list:", add_item("Python"))
print("Fresh list:", add_item("SQL"))


existing_items = ["Git"]
print("Existing list:", add_item("Python", existing_items))
print("Original list:", existing_items)


# =============================================================================
# 9. FUNCTION PARAMETERS ARE LOCAL NAMES
# =============================================================================

def demonstrate_parameter_scope(value: int) -> None:
    """Show that a parameter belongs to the function's local scope."""
    value = value + 10
    print("Inside function:", value)


number = 50
demonstrate_parameter_scope(number)
print("Outside function:", number)


# Reassigning a local parameter does not reassign the caller's variable.


# =============================================================================
# 10. MUTABLE VS IMMUTABLE OBJECTS
# =============================================================================

# Integers, floats, strings, tuples, and booleans are immutable.
# Lists, dictionaries, sets, and many custom objects are mutable.
#
# A function receives a reference to an object.
# Rebinding a local name is different from mutating the object.

def reassign_number(number: int) -> None:
    """Rebind a local name to a new integer."""
    number = 999


number = 10
reassign_number(number)
print("After integer reassignment:", number)


def mutate_list(numbers: list[int]) -> None:
    """Mutate the list received by the function."""
    numbers.append(999)


numbers = [1, 2, 3]
mutate_list(numbers)
print("After list mutation:", numbers)


# The key distinction is:
# - Reassignment changes what a local name refers to.
# - Mutation changes the existing object.


# =============================================================================
# 11. COPYING MUTABLE DATA TO AVOID UNINTENDED SIDE EFFECTS
# =============================================================================

def add_without_mutating(
    numbers: list[int],
    new_number: int,
) -> list[int]:
    """Return a new list instead of modifying the input list."""
    copied_numbers = numbers.copy()
    copied_numbers.append(new_number)
    return copied_numbers


original_numbers = [1, 2, 3]
new_numbers = add_without_mutating(original_numbers, 4)

print("Original:", original_numbers)
print("New:", new_numbers)


# =============================================================================
# 12. VARIABLE SCOPE
# =============================================================================

# A variable can exist in different scopes.
#
# Python commonly resolves names using LEGB:
#
# L = Local
# E = Enclosing
# G = Global
# B = Built-in

global_message = "Global value"


def scope_example() -> None:
    """Demonstrate a local variable."""
    local_message = "Local value"
    print(local_message)
    print(global_message)


scope_example()
print(global_message)


# The following would fail because local_message does not exist globally.
#
# print(local_message)


# =============================================================================
# 13. GLOBAL VARIABLES AND THE global KEYWORD
# =============================================================================

counter = 0


def increment_global_counter() -> None:
    """Modify a global variable using the global keyword."""
    global counter
    counter += 1


increment_global_counter()
increment_global_counter()
print("Global counter:", counter)


# Global state can make programs harder to reason about.
# Prefer passing values into functions and returning values when practical.


# Better design:

def increment_counter(current_counter: int) -> int:
    """Return an incremented counter without changing global state."""
    return current_counter + 1


counter = increment_counter(counter)
print("Controlled counter:", counter)


# =============================================================================
# 14. ENCLOSING SCOPE AND nonlocal
# =============================================================================

def make_counter() -> Callable[[], int]:
    """
    Create a function with private enclosed state.

    The nested function can access and modify 'count' using nonlocal.
    """
    count = 0

    def next_count() -> int:
        nonlocal count
        count += 1
        return count

    return next_count


counter_function = make_counter()

print(counter_function())
print(counter_function())
print(counter_function())


# Each call to make_counter() creates independent state.

another_counter = make_counter()

print("Second counter:", another_counter())
print("Second counter:", another_counter())
print("First counter:", counter_function())


# =============================================================================
# 15. LEGB NAME RESOLUTION
# =============================================================================

name = "global"


def outer_scope() -> None:
    name = "enclosing"

    def inner_scope() -> None:
        name = "local"
        print("Local:", name)

    inner_scope()
    print("Enclosing:", name)


outer_scope()
print("Global:", name)


# If Python does not find a name locally, it checks the enclosing scope,
# then global scope, then built-ins.


# =============================================================================
# 16. FUNCTION DOCSTRINGS
# =============================================================================

def calculate_area_of_circle(radius: float) -> float:
    """
    Calculate the area of a circle.

    Parameters
    ----------
    radius:
        Circle radius. Must not be negative.

    Returns
    -------
    float
        Area of the circle.

    Raises
    ------
    ValueError
        If radius is negative.
    """
    if radius < 0:
        raise ValueError("Radius cannot be negative.")

    return 3.141592653589793 * radius * radius


print("Circle area:", calculate_area_of_circle(5))


# Docstrings are available at runtime.

print(calculate_area_of_circle.__doc__)


# =============================================================================
# 17. TYPE ANNOTATIONS
# =============================================================================

# Type annotations document expected types.
# They are not automatic runtime validation.

def multiply_values(first: float, second: float) -> float:
    """Return the product of two numeric values."""
    return first * second


print(multiply_values(3, 4))


def create_profile(name: str, age: int) -> dict[str, Any]:
    """Create a simple profile dictionary."""
    return {
        "name": name,
        "age": age,
    }


print(create_profile("Atul", 30))


# Type annotations improve readability, editor support, and static analysis.


# =============================================================================
# 18. VALIDATION INSIDE FUNCTIONS
# =============================================================================

def calculate_percentage(part: float, whole: float) -> float:
    """Calculate what percentage part represents of whole."""
    if whole == 0:
        raise ValueError("Whole cannot be zero.")

    return (part / whole) * 100


try:
    print(calculate_percentage(25, 100))
    print(calculate_percentage(10, 0))
except ValueError as error:
    print("Validation error:", error)


# Validation should happen close to the boundary where invalid input enters
# the function when the function has a clear responsibility for validation.


# =============================================================================
# 19. FUNCTIONS AND CONDITIONAL LOGIC
# =============================================================================

def classify_number(number: float) -> str:
    """Classify a number as positive, negative, or zero."""
    if number > 0:
        return "positive"

    if number < 0:
        return "negative"

    return "zero"


for value in [10, -5, 0]:
    print(value, "->", classify_number(value))


# =============================================================================
# 20. FUNCTIONS AND LOOPS
# =============================================================================

def calculate_total(numbers: Iterable[float]) -> float:
    """Return the total of values in an iterable."""
    total = 0.0

    for number in numbers:
        total += number

    return total


print("Total:", calculate_total([10, 20, 30, 40]))


def calculate_average(numbers: Iterable[float]) -> float:
    """Return the arithmetic mean of a non-empty iterable."""
    values = list(numbers)

    if not values:
        raise ValueError("Cannot calculate average of an empty collection.")

    return sum(values) / len(values)


print("Average:", calculate_average([10, 20, 30, 40]))


# =============================================================================
# 21. REUSABLE DATA-PROCESSING FUNCTIONS
# =============================================================================

def filter_even_numbers(numbers: Iterable[int]) -> list[int]:
    """Return only even integers."""
    return [number for number in numbers if number % 2 == 0]


def square_numbers(numbers: Iterable[int]) -> list[int]:
    """Return squares of all supplied integers."""
    return [number * number for number in numbers]


sample_numbers = [1, 2, 3, 4, 5, 6]

print("Even numbers:", filter_even_numbers(sample_numbers))
print("Squares:", square_numbers(sample_numbers))


# Small focused functions can be combined to form larger processing pipelines.

even_numbers = filter_even_numbers(sample_numbers)
squared_even_numbers = square_numbers(even_numbers)

print("Squared even numbers:", squared_even_numbers)


# =============================================================================
# 22. FIRST-CLASS FUNCTIONS
# =============================================================================

# Functions are objects in Python.
# They can be:
# - assigned to variables
# - stored in lists
# - stored in dictionaries
# - passed to other functions
# - returned from functions

def add(a: float, b: float) -> float:
    return a + b


def subtract(a: float, b: float) -> float:
    return a - b


operation = add

print("Function assigned to variable:", operation(10, 5))


operations: dict[str, Callable[[float, float], float]] = {
    "add": add,
    "subtract": subtract,
}

print("Dictionary function:", operations["add"](7, 3))


# =============================================================================
# 23. FUNCTIONS AS ARGUMENTS
# =============================================================================

def apply_operation(
    first: float,
    second: float,
    operation: Callable[[float, float], float],
) -> float:
    """Apply a supplied binary operation."""
    return operation(first, second)


print("Apply add:", apply_operation(10, 3, add))
print("Apply subtract:", apply_operation(10, 3, subtract))


def apply_to_each(
    values: Iterable[int],
    transformation: Callable[[int], int],
) -> list[int]:
    """Apply a function to each value."""
    return [transformation(value) for value in values]


print("Doubled:", apply_to_each([1, 2, 3], lambda value: value * 2))
print("Cubed:", apply_to_each([1, 2, 3], lambda value: value ** 3))


# =============================================================================
# 24. LAMBDA FUNCTIONS
# =============================================================================

# Lambda creates a small anonymous function.
#
# Syntax:
# lambda parameters: expression
#
# Lambda functions are appropriate for short, simple expressions.

square = lambda number: number * number

print("Lambda square:", square(6))


# A normal def is generally clearer when logic becomes substantial.

people = [
    {"name": "A", "age": 35},
    {"name": "B", "age": 25},
    {"name": "C", "age": 30},
]

people_sorted_by_age = sorted(people, key=lambda person: person["age"])

print("Sorted people:", people_sorted_by_age)


# =============================================================================
# 25. HIGHER-ORDER FUNCTIONS
# =============================================================================

# A higher-order function either:
# - accepts another function as an argument, or
# - returns another function.

def create_multiplier(multiplier: float) -> Callable[[float], float]:
    """Return a function that multiplies values by multiplier."""

    def multiply(number: float) -> float:
        return number * multiplier

    return multiply


double = create_multiplier(2)
triple = create_multiplier(3)

print("Double:", double(10))
print("Triple:", triple(10))


# =============================================================================
# 26. NESTED FUNCTIONS
# =============================================================================

def calculate_with_logging(
    number: float,
    operation: Callable[[float], float],
) -> float:
    """Use a nested helper for simple logging."""

    def log(message: str) -> None:
        print("[LOG]", message)

    log(f"Processing {number}")
    result = operation(number)
    log(f"Result = {result}")

    return result


print(
    calculate_with_logging(
        5,
        lambda value: value * value,
    )
)


# =============================================================================
# 27. CLOSURES
# =============================================================================

# A closure is a function that remembers values from its enclosing scope
# after the outer function has finished executing.

def create_tax_calculator(tax_rate: float) -> Callable[[float], float]:
    """Create a reusable calculator bound to a tax rate."""
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative.")

    def calculate_tax(price: float) -> float:
        return price * tax_rate / 100

    return calculate_tax


gst_5 = create_tax_calculator(5)
gst_18 = create_tax_calculator(18)

print("5% tax:", gst_5(1000))
print("18% tax:", gst_18(1000))


# The returned functions retain access to tax_rate.


# =============================================================================
# 28. DECORATORS
# =============================================================================

# A decorator modifies or extends the behavior of another function.
#
# Decorator syntax:
#
# @decorator
# def function():
#     ...


def log_calls(function: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator that logs a function call and its result."""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        print(f"[CALL] {function.__name__}")
        result = function(*args, **kwargs)
        print(f"[RESULT] {result}")
        return result

    return wrapper


@log_calls
def calculate_sum(a: int, b: int) -> int:
    """Return the sum of two integers."""
    return a + b


print("Decorated function:", calculate_sum(5, 8))


# functools.wraps preserves useful metadata such as __name__ and __doc__.


# =============================================================================
# 29. DECORATOR WITH PARAMETERS
# =============================================================================

def repeat_call(times: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Create a decorator that calls a function a fixed number of times.

    The decorator itself receives configuration, then returns a decorator.
    """
    if times < 1:
        raise ValueError("times must be at least 1.")

    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = None

            for _ in range(times):
                result = function(*args, **kwargs)

            return result

        return wrapper

    return decorator


@repeat_call(3)
def announce(message: str) -> str:
    """Print and return a message."""
    print(message)
    return message


announce("Repeated function call")


# =============================================================================
# 30. *args
# =============================================================================

# *args collects additional positional arguments into a tuple.

def sum_all(*numbers: float) -> float:
    """Return the sum of any number of positional arguments."""
    return sum(numbers)


print(sum_all(1, 2, 3))
print(sum_all(10, 20, 30, 40, 50))
print(sum_all())


# =============================================================================
# 31. **kwargs
# =============================================================================

# **kwargs collects additional keyword arguments into a dictionary.

def describe_person(**details: Any) -> None:
    """Display arbitrary named details."""
    for key, value in details.items():
        print(f"{key}: {value}")


describe_person(
    name="Atul",
    age=30,
    city="Lucknow",
    occupation="Developer",
)


# =============================================================================
# 32. COMBINING NORMAL PARAMETERS, *args, AND **kwargs
# =============================================================================

def flexible_function(
    required_value: str,
    *values: int,
    **options: Any,
) -> None:
    """Demonstrate a flexible function signature."""
    print("Required:", required_value)
    print("Positional extras:", values)
    print("Keyword extras:", options)


flexible_function(
    "Python",
    10,
    20,
    30,
    level="advanced",
    active=True,
)


# =============================================================================
# 33. UNPACKING ARGUMENTS
# =============================================================================

def introduce(name: str, age: int, city: str) -> str:
    """Return a person's introduction."""
    return f"{name}, {age}, {city}"


person_data = ["Atul", 30, "Lucknow"]
print(introduce(*person_data))


person_dictionary = {
    "name": "Priya",
    "age": 28,
    "city": "Delhi",
}

print(introduce(**person_dictionary))


# =============================================================================
# 34. POSITIONAL-ONLY PARAMETERS
# =============================================================================

# Parameters before / cannot be passed by keyword.

def divide(dividend: float, divisor: float, /) -> float:
    """Divide two numbers using positional-only parameters."""
    if divisor == 0:
        raise ZeroDivisionError("Divisor cannot be zero.")

    return dividend / divisor


print(divide(10, 2))


# This would be invalid:
#
# divide(dividend=10, divisor=2)


# Positional-only parameters can make APIs clearer when parameter names
# should not be treated as part of the public calling convention.


# =============================================================================
# 35. KEYWORD-ONLY PARAMETERS
# =============================================================================

# Parameters after * must be supplied by keyword.

def create_user(
    username: str,
    *,
    active: bool = True,
    role: str = "user",
) -> dict[str, Any]:
    """Create a user record with explicit keyword-only options."""
    return {
        "username": username,
        "active": active,
        "role": role,
    }


print(create_user("atul"))
print(create_user("atul", active=False, role="admin"))


# This would be invalid:
#
# create_user("atul", False, "admin")


# Keyword-only parameters make optional configuration more readable.


# =============================================================================
# 36. ADVANCED FUNCTION SIGNATURE
# =============================================================================

def advanced_signature(
    positional: int,
    /,
    normal: int,
    *values: int,
    keyword_only: str = "default",
    **metadata: Any,
) -> dict[str, Any]:
    """
    Demonstrate positional-only, normal, variadic positional,
    keyword-only, and variadic keyword parameters.
    """
    return {
        "positional": positional,
        "normal": normal,
        "values": values,
        "keyword_only": keyword_only,
        "metadata": metadata,
    }


print(
    advanced_signature(
        1,
        2,
        3,
        4,
        keyword_only="custom",
        source="example",
    )
)


# =============================================================================
# 37. FUNCTION SIGNATURE INSPECTION
# =============================================================================

print("Signature:", signature(advanced_signature))


# inspect.signature can be useful for debugging, documentation systems,
# frameworks, and advanced function tooling.


# =============================================================================
# 38. RECURSION
# =============================================================================

# Recursion means a function calls itself.
#
# Every recursive algorithm needs:
# 1. A base case
# 2. A recursive case that moves toward the base case

def recursive_factorial(number: int) -> int:
    """Calculate factorial recursively."""
    if number < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    if number in (0, 1):
        return 1

    return number * recursive_factorial(number - 1)


print("Recursive factorial:", recursive_factorial(5))


# Recursive functions must eventually reach a base case.
# Otherwise Python eventually raises RecursionError.


# =============================================================================
# 39. ITERATIVE VS RECURSIVE FACTORIAL
# =============================================================================

def iterative_factorial(number: int) -> int:
    """Calculate factorial iteratively."""
    if number < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    result = 1

    for current in range(2, number + 1):
        result *= current

    return result


print("Iterative factorial:", iterative_factorial(5))


# For simple linear calculations, iteration often avoids recursion overhead
# and recursion-depth limitations.


# =============================================================================
# 40. RECURSIVE TREE TRAVERSAL
# =============================================================================

def sum_nested_numbers(data: Any) -> float:
    """
    Recursively sum numbers contained inside nested lists or tuples.

    Non-numeric scalar values are rejected rather than silently ignored.
    """
    if isinstance(data, (list, tuple)):
        return sum(sum_nested_numbers(item) for item in data)

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        return float(data)

    raise TypeError(f"Unsupported value: {data!r}")


nested_data = [1, [2, 3], [4, [5, 6]]]
print("Nested sum:", sum_nested_numbers(nested_data))


# =============================================================================
# 41. GENERATOR FUNCTIONS
# =============================================================================

# A generator function uses yield instead of returning all values at once.
# It produces values lazily.

def generate_squares(limit: int) -> Iterator[int]:
    """Yield squares from 0 through limit - 1."""
    if limit < 0:
        raise ValueError("Limit cannot be negative.")

    for number in range(limit):
        yield number * number


for square_value in generate_squares(5):
    print("Generated square:", square_value)


# Generators are useful when processing large or streaming datasets because
# they do not need to construct the entire result list in memory.


# =============================================================================
# 42. GENERATOR VS LIST
# =============================================================================

def create_square_list(limit: int) -> list[int]:
    """Create all squares immediately."""
    return [number * number for number in range(limit)]


def create_square_generator(limit: int) -> Iterator[int]:
    """Produce squares lazily."""
    for number in range(limit):
        yield number * number


small_list = create_square_list(5)
small_generator = create_square_generator(5)

print("List:", small_list)
print("Generator object:", small_generator)
print("Generator values:", list(small_generator))


# =============================================================================
# 43. CACHING AND MEMOIZATION
# =============================================================================

# Repeated calculations can sometimes be avoided by caching previous results.

@lru_cache(maxsize=None)
def fibonacci_cached(number: int) -> int:
    """Return Fibonacci number using memoization."""
    if number < 0:
        raise ValueError("Fibonacci index cannot be negative.")

    if number < 2:
        return number

    return fibonacci_cached(number - 1) + fibonacci_cached(number - 2)


print("Cached Fibonacci:", fibonacci_cached(20))
print("Cache information:", fibonacci_cached.cache_info())


# Caching is effective when:
# - the function is deterministic
# - the same inputs occur repeatedly
# - results are reusable
#
# It may be inappropriate when:
# - inputs are effectively unique
# - results depend on changing external state
# - cached objects consume too much memory


# =============================================================================
# 44. FUNCTION FACTORIES
# =============================================================================

def create_power_function(exponent: int) -> Callable[[float], float]:
    """Return a function that raises a number to a chosen exponent."""

    def power(number: float) -> float:
        return number ** exponent

    return power


square_function = create_power_function(2)
cube_function = create_power_function(3)

print("Factory square:", square_function(5))
print("Factory cube:", cube_function(5))


# =============================================================================
# 45. functools.partial
# =============================================================================

def calculate_power(base: float, exponent: float) -> float:
    """Raise base to exponent."""
    return base ** exponent


square_using_partial = partial(calculate_power, exponent=2)
cube_using_partial = partial(calculate_power, exponent=3)

print("Partial square:", square_using_partial(6))
print("Partial cube:", cube_using_partial(6))


# partial creates a callable with some arguments already fixed.


# =============================================================================
# 46. CALLABLE OBJECTS
# =============================================================================

# Any object implementing __call__ can be called like a function.

class Multiplier:
    """Callable object that multiplies a number by a stored factor."""

    def __init__(self, factor: float) -> None:
        self.factor = factor

    def __call__(self, value: float) -> float:
        return value * self.factor


double_object = Multiplier(2)

print("Callable object:", double_object(10))
print("Is callable:", callable(double_object))


# A callable object is useful when behavior needs state and potentially
# several related methods.


# =============================================================================
# 47. FUNCTION ATTRIBUTES
# =============================================================================

def sample_function() -> str:
    """A function can have attributes."""
    return "sample"


sample_function.category = "demonstration"  # type: ignore[attr-defined]

print("Function attribute:", sample_function.category)  # type: ignore[attr-defined]


# Function attributes exist, but they should be used deliberately.
# For complex state, a class is usually clearer.


# =============================================================================
# 48. SIDE EFFECTS
# =============================================================================

# A pure function:
# - depends only on its inputs
# - produces an output
# - does not change external state
#
# A function with side effects may:
# - modify a global variable
# - modify a passed mutable object
# - write a file
# - print output
# - perform network/database operations
#
# Pure functions are generally easier to test and reuse.

def pure_add(a: int, b: int) -> int:
    """Pure function."""
    return a + b


shared_values = []


def function_with_side_effect(value: int) -> None:
    """Modify external state."""
    shared_values.append(value)


print("Pure result:", pure_add(2, 3))

function_with_side_effect(10)
print("External state:", shared_values)


# =============================================================================
# 49. FUNCTION COMPOSITION
# =============================================================================

def compose(
    first_function: Callable[[Any], Any],
    second_function: Callable[[Any], Any],
) -> Callable[[Any], Any]:
    """
    Return a function equivalent to:
    second_function(first_function(value))
    """

    def composed(value: Any) -> Any:
        return second_function(first_function(value))

    return composed


add_one = lambda value: value + 1
multiply_by_two = lambda value: value * 2

add_then_double = compose(add_one, multiply_by_two)

print("Composed function:", add_then_double(5))


# Function composition allows small operations to be assembled into pipelines.


# =============================================================================
# 50. A REUSABLE VALIDATION FUNCTION
# =============================================================================

def validate_positive_number(value: float, field_name: str = "value") -> float:
    """Validate and return a positive numeric value."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be numeric.")

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero.")

    return float(value)


print(validate_positive_number(10, "price"))


# =============================================================================
# 51. BUILDING A FINANCIAL CALCULATION FUNCTION
# =============================================================================

def calculate_simple_interest(
    principal: float,
    annual_rate: float,
    years: float,
) -> float:
    """
    Calculate simple interest.

    Formula:
        interest = principal * rate * time
    """
    validate_positive_number(principal, "principal")

    if annual_rate < 0:
        raise ValueError("Annual rate cannot be negative.")

    if years < 0:
        raise ValueError("Years cannot be negative.")

    return principal * (annual_rate / 100) * years


print(
    "Simple interest:",
    calculate_simple_interest(100000, 7.5, 2),
)


# =============================================================================
# 52. COMBINING REUSABLE FUNCTIONS
# =============================================================================

def calculate_total_amount(
    principal: float,
    annual_rate: float,
    years: float,
) -> float:
    """Return principal plus simple interest."""
    interest = calculate_simple_interest(
        principal,
        annual_rate,
        years,
    )
    return principal + interest


print(
    "Total amount:",
    calculate_total_amount(100000, 7.5, 2),
)


# A larger function can remain readable when it delegates specialized
# responsibilities to smaller functions.


# =============================================================================
# 53. ERROR HANDLING IN REUSABLE FUNCTIONS
# =============================================================================

def safe_divide(
    numerator: float,
    denominator: float,
) -> Optional[float]:
    """Return a quotient or None when the denominator is zero."""
    if denominator == 0:
        return None

    return numerator / denominator


print("Safe divide:", safe_divide(10, 2))
print("Safe divide by zero:", safe_divide(10, 0))


# Returning None is appropriate when "no result" is a valid business outcome.
# Raising an exception is more appropriate when invalid input should be
# treated as an error that callers must address.


# =============================================================================
# 54. CUSTOM EXCEPTIONS FOR FUNCTION APIs
# =============================================================================

class InvalidAgeError(ValueError):
    """Raised when an age is outside the accepted range."""


def validate_age(age: int) -> int:
    """Validate an age value."""
    if not isinstance(age, int) or isinstance(age, bool):
        raise TypeError("Age must be an integer.")

    if not 0 <= age <= 150:
        raise InvalidAgeError("Age must be between 0 and 150.")

    return age


try:
    print("Validated age:", validate_age(30))
    print("Validated age:", validate_age(200))
except (TypeError, InvalidAgeError) as error:
    print("Age validation error:", error)


# =============================================================================
# 55. FUNCTIONS THAT ACCEPT ITERABLES
# =============================================================================

def maximum_value(values: Iterable[float]) -> float:
    """Return the largest value from a non-empty iterable."""
    iterator = iter(values)

    try:
        maximum = next(iterator)
    except StopIteration as error:
        raise ValueError("Iterable cannot be empty.") from error

    for value in iterator:
        if value > maximum:
            maximum = value

    return maximum


print(maximum_value([4, 10, 2, 8]))


# Accepting Iterable instead of list makes a function useful with lists,
# tuples, generators, sets, and many other iterable objects.


# =============================================================================
# 56. FUNCTIONS SHOULD MATCH THEIR RESPONSIBILITY
# =============================================================================

def clean_name(name: str) -> str:
    """Normalize whitespace around a name."""
    return name.strip()


def validate_name(name: str) -> str:
    """Validate that a name is not empty after trimming."""
    cleaned_name = clean_name(name)

    if not cleaned_name:
        raise ValueError("Name cannot be empty.")

    return cleaned_name


def create_customer(name: str) -> dict[str, str]:
    """Validate and create a customer record."""
    valid_name = validate_name(name)

    return {
        "name": valid_name,
    }


print(create_customer("  Atul Pandey  "))


# These functions demonstrate separation of responsibilities:
# - cleaning
# - validation
# - object construction


# =============================================================================
# 57. TESTING FUNCTIONS WITH ASSERTIONS
# =============================================================================

def multiply(a: int, b: int) -> int:
    """Return the product of two integers."""
    return a * b


assert multiply(2, 3) == 6
assert multiply(-2, 3) == -6
assert multiply(0, 100) == 0

print("Basic assertions passed.")


# Assertions are useful for internal invariants and simple educational tests.
# Production test suites generally use dedicated testing frameworks.


# =============================================================================
# 58. SIMPLE TEST RUNNER
# =============================================================================

def run_test(
    test_name: str,
    test_function: Callable[[], None],
) -> None:
    """Execute one test and display its result."""
    try:
        test_function()
    except AssertionError:
        print(f"FAIL: {test_name}")
    except Exception as error:
        print(f"ERROR: {test_name}: {error}")
    else:
        print(f"PASS: {test_name}")


def test_addition() -> None:
    assert add_numbers(2, 3) == 5


def test_discount() -> None:
    assert calculate_discount(100, 10) == 90


def test_square() -> None:
    assert calculate_square(5) == 25


run_test("Addition", test_addition)
run_test("Discount", test_discount)
run_test("Square", test_square)


# =============================================================================
# 59. TESTING ERROR CONDITIONS
# =============================================================================

def test_invalid_percentage() -> None:
    try:
        calculate_percentage(10, 0)
    except ValueError:
        return

    raise AssertionError("Expected ValueError was not raised.")


run_test("Invalid percentage", test_invalid_percentage)


# Testing only successful cases is incomplete.
# Good tests also cover invalid inputs and boundary conditions.


# =============================================================================
# 60. EDGE CASES
# =============================================================================

def safe_average(values: Iterable[float]) -> Optional[float]:
    """Return average or None for an empty iterable."""
    values_list = list(values)

    if not values_list:
        return None

    return mean(values_list)


print("Empty average:", safe_average([]))
print("Normal average:", safe_average([1, 2, 3]))


# Edge cases commonly include:
# - empty collections
# - zero
# - negative values
# - very large values
# - duplicate values
# - missing values
# - invalid types
# - boundary values


# =============================================================================
# 61. FUNCTION OVERLOADING CONCEPT
# =============================================================================

# Python does not support traditional signature-based function overloading
# in the same way as languages such as Java or C++.
#
# Defining the same function name again replaces the previous definition.

def overloaded_example(value: int) -> str:
    return f"Integer: {value}"


def overloaded_example(value: str) -> str:
    return f"String: {value}"


print(overloaded_example(10))
print(overloaded_example("Python"))


# The first definition has been replaced.
#
# Python commonly handles different input forms using:
# - default arguments
# - *args
# - type checks
# - singledispatch
# - separate functions


# =============================================================================
# 62. functools.singledispatch
# =============================================================================

from functools import singledispatch


@singledispatch
def describe_value(value: Any) -> str:
    """Provide a generic description."""
    return f"Value of type {type(value).__name__}"


@describe_value.register
def _(value: int) -> str:
    return f"Integer with value {value}"


@describe_value.register
def _(value: list) -> str:
    return f"List containing {len(value)} items"


print(describe_value(10))
print(describe_value([1, 2, 3]))
print(describe_value("Python"))


# singledispatch dispatches primarily according to the first argument's type.


# =============================================================================
# 63. OPTIONAL VALUES
# =============================================================================

def find_first_even(numbers: Iterable[int]) -> Optional[int]:
    """Return the first even number, or None if none exists."""
    for number in numbers:
        if number % 2 == 0:
            return number

    return None


result = find_first_even([1, 3, 7, 8, 9])

if result is not None:
    print("First even:", result)
else:
    print("No even number found.")


# Explicitly handling None prevents accidental assumptions about a result.


# =============================================================================
# 64. FUNCTIONS RETURNING DATA STRUCTURES
# =============================================================================

def calculate_statistics(numbers: Iterable[float]) -> dict[str, float]:
    """Return basic statistics for a non-empty iterable."""
    values = list(numbers)

    if not values:
        raise ValueError("At least one number is required.")

    return {
        "count": float(len(values)),
        "total": float(sum(values)),
        "minimum": float(min(values)),
        "maximum": float(max(values)),
        "average": float(mean(values)),
    }


print(calculate_statistics([10, 20, 30, 40, 50]))


# Returning structured data can make a function easier to consume than
# returning many unrelated values.


# =============================================================================
# 65. FUNCTION DESIGN WITH KEYWORD-ONLY CONFIGURATION
# =============================================================================

def paginate(
    items: list[Any],
    *,
    page: int = 1,
    page_size: int = 10,
) -> list[Any]:
    """Return one page of items."""
    if page < 1:
        raise ValueError("Page must be at least 1.")

    if page_size < 1:
        raise ValueError("Page size must be at least 1.")

    start = (page - 1) * page_size
    end = start + page_size

    return items[start:end]


items = list(range(1, 31))

print("Page 1:", paginate(items, page=1, page_size=10))
print("Page 2:", paginate(items, page=2, page_size=10))
print("Page 3:", paginate(items, page=3, page_size=10))


# =============================================================================
# 66. CALLBACK FUNCTIONS
# =============================================================================

def process_numbers(
    numbers: Iterable[int],
    callback: Callable[[int], None],
) -> None:
    """Send every number to a callback."""
    for number in numbers:
        callback(number)


def print_number(number: int) -> None:
    print("Callback received:", number)


process_numbers([10, 20, 30], print_number)


# Callbacks are useful when the caller wants to customize what happens
# during a reusable process.


# =============================================================================
# 67. FUNCTION REGISTRIES
# =============================================================================

def handle_addition(value: int) -> str:
    return f"Addition handler received {value}"


def handle_multiplication(value: int) -> str:
    return f"Multiplication handler received {value}"


handlers: dict[str, Callable[[int], str]] = {
    "add": handle_addition,
    "multiply": handle_multiplication,
}


def dispatch_operation(
    operation_name: str,
    value: int,
) -> str:
    """Dispatch to a registered operation."""
    try:
        handler = handlers[operation_name]
    except KeyError as error:
        raise ValueError(
            f"Unknown operation: {operation_name}"
        ) from error

    return handler(value)


print(dispatch_operation("add", 10))
print(dispatch_operation("multiply", 10))


# A function registry can replace long if/elif chains when operations are
# naturally represented as named callables.


# =============================================================================
# 68. SECURITY: DO NOT TRUST FUNCTION INPUT
# =============================================================================

def validate_command_name(command_name: str, allowed_commands: set[str]) -> str:
    """Accept only explicitly allowed command names."""
    if command_name not in allowed_commands:
        raise ValueError("Unsupported command.")

    return command_name


allowed = {"start", "stop", "status"}

print(validate_command_name("status", allowed))

try:
    print(validate_command_name("delete_all", allowed))
except ValueError as error:
    print("Security validation:", error)


# Functions that accept user-controlled values should validate:
# - types
# - ranges
# - allowed values
# - lengths
# - formats
# - permissions where relevant
#
# Avoid passing untrusted input directly into dangerous interpreters,
# operating-system commands, SQL strings, or dynamic code execution.


# =============================================================================
# 69. PERFORMANCE: FUNCTION CALL OVERHEAD
# =============================================================================

def add_one(value: int) -> int:
    return value + 1


start_time = perf_counter()

value = 0
for _ in range(100_000):
    value = add_one(value)

elapsed_function_calls = perf_counter() - start_time

print(
    "Time using repeated function calls:",
    elapsed_function_calls,
)


# Function calls have overhead, but readability and modularity usually matter
# more than eliminating tiny call costs.
#
# Optimize function-call overhead only after measurement demonstrates that
# it matters in the actual workload.


# =============================================================================
# 70. PERFORMANCE: CACHING EXPENSIVE WORK
# =============================================================================

@lru_cache(maxsize=128)
def expensive_square(number: int) -> int:
    """Demonstrate a cacheable deterministic function."""
    # Simulated expensive computation.
    result = 0

    for _ in range(1000):
        result += number * number

    return result


print(expensive_square(10))
print(expensive_square(10))
print(expensive_square.cache_info())


# =============================================================================
# 71. FUNCTION DOCUMENTATION AND METADATA
# =============================================================================

print("Name:", calculate_area_of_circle.__name__)
print("Documentation:", calculate_area_of_circle.__doc__)


# Decorators without functools.wraps can hide the original function metadata.
# Using @wraps is therefore a best practice for normal function decorators.


# =============================================================================
# 72. DECORATOR FOR VALIDATION
# =============================================================================

def require_positive(
    function: Callable[[float], float],
) -> Callable[[float], float]:
    """Decorate a single-number function with positive-value validation."""

    @wraps(function)
    def wrapper(value: float) -> float:
        if value <= 0:
            raise ValueError("Value must be positive.")

        return function(value)

    return wrapper


@require_positive
def calculate_reciprocal(value: float) -> float:
    """Return the reciprocal of a positive number."""
    return 1 / value


print("Reciprocal:", calculate_reciprocal(4))


try:
    calculate_reciprocal(-2)
except ValueError as error:
    print("Decorator validation:", error)


# =============================================================================
# 73. PARAMETER VALIDATION AND API CONTRACTS
# =============================================================================

def calculate_compound_interest(
    principal: float,
    annual_rate: float,
    years: float,
    *,
    compounds_per_year: int = 12,
) -> float:
    """
    Calculate compound interest.

    Formula:
        A = P * (1 + r/n) ** (n*t)

    Returns the final amount A.
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative.")

    if annual_rate < 0:
        raise ValueError("Annual rate cannot be negative.")

    if years < 0:
        raise ValueError("Years cannot be negative.")

    if compounds_per_year <= 0:
        raise ValueError("Compounds per year must be positive.")

    rate = annual_rate / 100

    return principal * (
        1 + rate / compounds_per_year
    ) ** (compounds_per_year * years)


print(
    "Compound amount:",
    calculate_compound_interest(
        100000,
        8,
        5,
        compounds_per_year=12,
    ),
)


# =============================================================================
# 74. FUNCTIONAL STYLE WITH MAP
# =============================================================================

numbers = [1, 2, 3, 4]

doubled_numbers = list(map(lambda number: number * 2, numbers))

print("map result:", doubled_numbers)


# List comprehensions are often more readable for straightforward transformations.

doubled_numbers_comprehension = [number * 2 for number in numbers]

print("Comprehension result:", doubled_numbers_comprehension)


# =============================================================================
# 75. FUNCTIONAL STYLE WITH FILTER
# =============================================================================

filtered_numbers = list(
    filter(lambda number: number > 2, numbers)
)

print("filter result:", filtered_numbers)


# A comprehension is often more direct:

filtered_numbers_comprehension = [
    number for number in numbers if number > 2
]

print("Filtered comprehension:", filtered_numbers_comprehension)


# =============================================================================
# 76. REDUCE
# =============================================================================

from functools import reduce


product_of_numbers = reduce(
    lambda first, second: first * second,
    [1, 2, 3, 4, 5],
)

print("Reduced product:", product_of_numbers)


# reduce can be useful when an operation naturally combines a sequence into
# one result. For simple sums, sum() is usually clearer.


# =============================================================================
# 77. CLOSURE INSPECTION
# =============================================================================

def create_message(prefix: str) -> Callable[[str], str]:
    """Create a message formatter that remembers prefix."""

    def format_message(message: str) -> str:
        return f"{prefix}: {message}"

    return format_message


error_message = create_message("ERROR")

print(error_message("File not found"))


if error_message.__closure__:
    print("Closure contains enclosed state.")


# =============================================================================
# 78. RECURSIVE FIBONACCI VS ITERATIVE FIBONACCI
# =============================================================================

def fibonacci_iterative(number: int) -> int:
    """Return Fibonacci number iteratively."""
    if number < 0:
        raise ValueError("Index cannot be negative.")

    first, second = 0, 1

    for _ in range(number):
        first, second = second, first + second

    return first


print("Iterative Fibonacci:", fibonacci_iterative(20))
print("Cached recursive Fibonacci:", fibonacci_cached(20))


# Naive recursive Fibonacci has exponential repeated work.
# Memoization or iteration avoids most of that repeated computation.


# =============================================================================
# 79. REUSABLE UNIT CONVERSION FUNCTIONS
# =============================================================================

def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return (celsius * 9 / 5) + 32


def fahrenheit_to_celsius(fahrenheit: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (fahrenheit - 32) * 5 / 9


print("25 C -> F:", celsius_to_fahrenheit(25))
print("77 F -> C:", fahrenheit_to_celsius(77))


# =============================================================================
# 80. A SMALL CALCULATOR USING FUNCTION REGISTRY
# =============================================================================

def calculator_add(a: float, b: float) -> float:
    return a + b


def calculator_subtract(a: float, b: float) -> float:
    return a - b


def calculator_multiply(a: float, b: float) -> float:
    return a * b


def calculator_divide(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero.")

    return a / b


calculator_operations: dict[
    str,
    Callable[[float, float], float],
] = {
    "+": calculator_add,
    "-": calculator_subtract,
    "*": calculator_multiply,
    "/": calculator_divide,
}


def calculate_expression(
    first: float,
    operator: str,
    second: float,
) -> float:
    """Execute one basic arithmetic operation."""
    if operator not in calculator_operations:
        raise ValueError(f"Unsupported operator: {operator}")

    return calculator_operations[operator](first, second)


print(calculate_expression(10, "+", 5))
print(calculate_expression(10, "*", 5))


# =============================================================================
# 81. FUNCTION-BASED DATA VALIDATION PIPELINE
# =============================================================================

def normalize_email(email: str) -> str:
    """Normalize an email string."""
    return email.strip().lower()


def validate_email(email: str) -> str:
    """Perform basic email validation."""
    normalized = normalize_email(email)

    if not normalized:
        raise ValueError("Email cannot be empty.")

    if "@" not in normalized:
        raise ValueError("Email must contain '@'.")

    local_part, domain = normalized.split("@", 1)

    if not local_part or not domain or "." not in domain:
        raise ValueError("Email format is invalid.")

    return normalized


def create_account(email: str) -> dict[str, str]:
    """Create an account after validating the email."""
    valid_email = validate_email(email)

    return {
        "email": valid_email,
    }


print(create_account("  USER@EXAMPLE.COM  "))


# This demonstrates a layered function design:
# normalize -> validate -> construct


# =============================================================================
# 82. FUNCTIONS AND IMMUTABILITY
# =============================================================================

def add_tag(
    tags: tuple[str, ...],
    new_tag: str,
) -> tuple[str, ...]:
    """Return a new tuple with a tag added."""
    return (*tags, new_tag)


original_tags = ("python", "functions")
updated_tags = add_tag(original_tags, "scope")

print("Original tags:", original_tags)
print("Updated tags:", updated_tags)


# Immutable inputs can make side effects easier to control.


# =============================================================================
# 83. FUNCTIONS THAT ACCEPT FUNCTIONS WITH TYPE ALIASES
# =============================================================================

NumberOperation = Callable[[float, float], float]


def execute_operation(
    operation: NumberOperation,
    first: float,
    second: float,
) -> float:
    """Execute a typed binary numeric operation."""
    return operation(first, second)


print(execute_operation(add, 4, 6))


# Type aliases can improve readability when complex callable types repeat.


# =============================================================================
# 84. CALLBACK-BASED RETRY SIMULATION
# =============================================================================

def retry_operation(
    operation: Callable[[], Any],
    *,
    attempts: int = 3,
) -> Any:
    """
    Retry a callable operation.

    The last exception is raised if every attempt fails.
    """
    if attempts < 1:
        raise ValueError("Attempts must be at least 1.")

    last_error: Optional[Exception] = None

    for _ in range(attempts):
        try:
            return operation()
        except Exception as error:
            last_error = error

    assert last_error is not None
    raise last_error


attempt_state = {"calls": 0}


def unreliable_operation() -> str:
    """Fail twice and succeed on the third attempt."""
    attempt_state["calls"] += 1

    if attempt_state["calls"] < 3:
        raise RuntimeError("Temporary failure.")

    return "Operation succeeded."


print(retry_operation(unreliable_operation, attempts=3))


# In production, retry policies should also consider:
# - which errors are retryable
# - exponential backoff
# - maximum delay
# - idempotency
# - external service limits
# - observability


# =============================================================================
# 85. DECORATOR FOR TIMING
# =============================================================================

def measure_time(function: Callable[..., Any]) -> Callable[..., Any]:
    """Measure execution time of a function."""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = perf_counter()

        result = function(*args, **kwargs)

        elapsed = perf_counter() - start

        print(
            f"{function.__name__} execution time: "
            f"{elapsed:.8f} seconds"
        )

        return result

    return wrapper


@measure_time
def sum_range(limit: int) -> int:
    """Calculate the sum of integers below limit."""
    return sum(range(limit))


print("Timed sum:", sum_range(100_000))


# Timing decorators are useful for diagnostics.
# They should not be used as the sole basis for performance decisions.


# =============================================================================
# 86. PRESERVING DECORATOR METADATA
# =============================================================================

@measure_time
def documented_function(value: int) -> int:
    """Return double the input."""
    return value * 2


print("Decorated name:", documented_function.__name__)
print("Decorated documentation:", documented_function.__doc__)


# Because @wraps was used, metadata is preserved.


# =============================================================================
# 87. FUNCTION FACTORY FOR VALIDATORS
# =============================================================================

def create_range_validator(
    minimum: float,
    maximum: float,
) -> Callable[[float], float]:
    """Create a reusable numeric range validator."""
    if minimum > maximum:
        raise ValueError("Minimum cannot exceed maximum.")

    def validate(value: float) -> float:
        if not minimum <= value <= maximum:
            raise ValueError(
                f"Value must be between {minimum} and {maximum}."
            )

        return value

    return validate


percentage_validator = create_range_validator(0, 100)

print("Valid percentage:", percentage_validator(75))


# =============================================================================
# 88. FUNCTION DESIGN: AVOIDING HIDDEN DEPENDENCIES
# =============================================================================

# Less explicit:
current_tax_rate = 18


def calculate_tax_hidden(price: float) -> float:
    return price * current_tax_rate / 100


# More explicit:
def calculate_tax_explicit(
    price: float,
    tax_rate: float,
) -> float:
    return price * tax_rate / 100


print("Explicit tax:", calculate_tax_explicit(1000, 18))


# Explicit dependencies generally make functions:
# - easier to test
# - easier to reuse
# - easier to reason about
# - less dependent on global state


# =============================================================================
# 89. FUNCTION DESIGN: RETURNING EARLY
# =============================================================================

def get_status_message(score: int) -> str:
    """Return a status using early returns."""
    if score < 0 or score > 100:
        raise ValueError("Score must be between 0 and 100.")

    if score >= 90:
        return "Excellent"

    if score >= 75:
        return "Very good"

    if score >= 60:
        return "Good"

    if score >= 40:
        return "Pass"

    return "Needs improvement"


for score in [95, 80, 65, 45, 20]:
    print(score, "->", get_status_message(score))


# Early returns can reduce deeply nested conditional structures.


# =============================================================================
# 90. FUNCTION DESIGN: SINGLE RESPONSIBILITY
# =============================================================================

def calculate_subtotal(prices: Iterable[float]) -> float:
    """Calculate subtotal."""
    return sum(prices)


def calculate_tax_amount(
    subtotal: float,
    tax_rate: float,
) -> float:
    """Calculate tax amount."""
    return subtotal * tax_rate / 100


def calculate_invoice_total(
    prices: Iterable[float],
    tax_rate: float,
) -> float:
    """Calculate an invoice total using specialized functions."""
    subtotal = calculate_subtotal(prices)
    tax = calculate_tax_amount(subtotal, tax_rate)

    return subtotal + tax


print(
    "Invoice total:",
    calculate_invoice_total(
        [100, 200, 300],
        18,
    ),
)


# Each function has a focused responsibility.
# This reduces duplication and makes individual behavior easier to test.


# =============================================================================
# 91. A PRACTICAL REUSABLE REPORT FUNCTION
# =============================================================================

def build_sales_report(
    sales: Iterable[float],
    *,
    tax_rate: float = 18,
) -> dict[str, float]:
    """Build a small sales report."""
    sales_values = list(sales)

    if any(value < 0 for value in sales_values):
        raise ValueError("Sales values cannot be negative.")

    subtotal = calculate_subtotal(sales_values)
    tax = calculate_tax_amount(subtotal, tax_rate)

    return {
        "transactions": float(len(sales_values)),
        "subtotal": subtotal,
        "tax": tax,
        "total": subtotal + tax,
    }


sales_report = build_sales_report(
    [1000, 2500, 1500],
    tax_rate=18,
)

print("Sales report:", sales_report)


# =============================================================================
# 92. FUNCTIONS AND DEFAULT OBJECT CREATION
# =============================================================================

def build_settings(
    settings: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Return settings safely.

    A fresh dictionary is created when no settings are supplied.
    """
    if settings is None:
        settings = {}

    return settings


print(build_settings())
print(build_settings({"theme": "dark"}))


# =============================================================================
# 93. FUNCTIONS AND BOOLEAN PARAMETERS
# =============================================================================

def format_name(
    first_name: str,
    last_name: str,
    *,
    uppercase: bool = False,
) -> str:
    """Format a full name."""
    full_name = f"{first_name.strip()} {last_name.strip()}"

    if uppercase:
        return full_name.upper()

    return full_name


print(format_name("Atul", "Pandey"))
print(format_name("Atul", "Pandey", uppercase=True))


# Too many boolean parameters can make an API difficult to understand.
# Keyword-only boolean options are clearer than positional booleans.


# =============================================================================
# 94. FUNCTIONS WITH NONE AS A VALID INPUT
# =============================================================================

def normalize_optional_name(name: Optional[str]) -> Optional[str]:
    """Normalize a name while allowing None."""
    if name is None:
        return None

    cleaned_name = name.strip()

    if not cleaned_name:
        return None

    return cleaned_name


print(normalize_optional_name("  Atul  "))
print(normalize_optional_name(None))
print(normalize_optional_name("   "))


# =============================================================================
# 95. EDGE CASE: BOOLEAN IS A SUBCLASS OF INTEGER
# =============================================================================

# In Python:
#
# isinstance(True, int) is True
#
# If a function requires a genuine integer and should reject booleans,
# explicitly test isinstance(value, bool).

def require_integer(value: int) -> int:
    """Require an integer but reject booleans."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("A non-boolean integer is required.")

    return value


print(require_integer(10))

try:
    require_integer(True)
except TypeError as error:
    print("Boolean rejected:", error)


# =============================================================================
# 96. EDGE CASE: ZERO VS NONE
# =============================================================================

def calculate_discount_safe(
    price: float,
    discount_rate: Optional[float] = None,
) -> float:
    """
    Apply a discount only when a discount rate was explicitly supplied.

    Zero means a real 0% discount.
    None means no discount configuration was supplied.
    """
    if price < 0:
        raise ValueError("Price cannot be negative.")

    if discount_rate is None:
        discount_rate = 0

    if not 0 <= discount_rate <= 100:
        raise ValueError("Discount rate must be between 0 and 100.")

    return price * (1 - discount_rate / 100)


print(calculate_discount_safe(1000))
print(calculate_discount_safe(1000, 0))
print(calculate_discount_safe(1000, 20))


# =============================================================================
# 97. ADVANCED: GENERIC REUSABLE FUNCTION
# =============================================================================

from typing import TypeVar


T = TypeVar("T")


def first_item(items: Iterable[T]) -> T:
    """Return the first item from a non-empty iterable."""
    iterator = iter(items)

    try:
        return next(iterator)
    except StopIteration as error:
        raise ValueError("Iterable is empty.") from error


print(first_item(["Python", "SQL", "Git"]))
print(first_item([10, 20, 30]))


# TypeVar communicates that the output type corresponds to the input item type.


# =============================================================================
# 98. ADVANCED: GENERIC TRANSFORMATION
# =============================================================================

U = TypeVar("U")


def transform_items(
    items: Iterable[T],
    transformer: Callable[[T], U],
) -> list[U]:
    """Transform each item using a supplied function."""
    return [transformer(item) for item in items]


print(
    transform_items(
        [1, 2, 3],
        lambda value: f"Number-{value}",
    )
)


# =============================================================================
# 99. ADVANCED: CALLABLE CLASS WITH CONFIGURATION
# =============================================================================

class ThresholdChecker:
    """Callable object that checks whether a value reaches a threshold."""

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def __call__(self, value: float) -> bool:
        return value >= self.threshold

    def describe(self) -> str:
        return f"Threshold = {self.threshold}"


checker = ThresholdChecker(75)

print(checker.describe())
print(checker(80))
print(checker(50))


# =============================================================================
# 100. ADVANCED: DECORATOR THAT VALIDATES RETURN VALUES
# =============================================================================

def require_numeric_return(
    function: Callable[..., Any],
) -> Callable[..., float]:
    """Ensure a decorated function returns a numeric value."""

    @wraps(function)
    def wrapper(*args: Any, **kwargs: Any) -> float:
        result = function(*args, **kwargs)

        if not isinstance(result, (int, float)) or isinstance(result, bool):
            raise TypeError("Function must return a numeric value.")

        return float(result)

    return wrapper


@require_numeric_return
def numeric_result(value: int) -> int:
    return value * 2


print("Validated return:", numeric_result(10))


# =============================================================================
# 101. ADVANCED: DECORATOR STACKING
# =============================================================================

@measure_time
@log_calls
def stacked_function(value: int) -> int:
    """Demonstrate multiple decorators."""
    return value * value


print("Stacked result:", stacked_function(12))


# Decorators are applied from the closest decorator to the function outward.
# Conceptually:
#
# stacked_function = measure_time(log_calls(stacked_function))
#
# The order of decorators can therefore affect behavior.


# =============================================================================
# 102. ADVANCED: CLOSURE VS CLASS
# =============================================================================

def make_threshold_function(threshold: float) -> Callable[[float], bool]:
    """Create a threshold checker using a closure."""

    def check(value: float) -> bool:
        return value >= threshold

    return check


closure_checker = make_threshold_function(50)

print("Closure checker:", closure_checker(60))


# A closure is concise for small stateful behavior.
# A class is often better when the object needs:
# - multiple methods
# - explicit state
# - inheritance
# - richer lifecycle behavior


# =============================================================================
# 103. ADVANCED: RECURSIVE DIRECTORY-LIKE STRUCTURE
# =============================================================================

def count_nested_items(data: Any) -> int:
    """Count leaf items recursively in nested lists and tuples."""
    if isinstance(data, (list, tuple)):
        return sum(count_nested_items(item) for item in data)

    return 1


nested_structure = [
    "file1",
    ["file2", "file3"],
    ["folder", ["file4", "file5"]],
]

print("Nested leaf count:", count_nested_items(nested_structure))


# =============================================================================
# 104. ADVANCED: FUNCTION PIPELINE
# =============================================================================

def pipeline(
    value: T,
    *functions: Callable[[Any], Any],
) -> Any:
    """Apply functions sequentially to a value."""
    current: Any = value

    for function in functions:
        current = function(current)

    return current


pipeline_result = pipeline(
    5,
    lambda value: value + 1,
    lambda value: value * 2,
    lambda value: value ** 2,
)

print("Pipeline result:", pipeline_result)


# A pipeline is useful when each stage has a compatible input/output contract.


# =============================================================================
# 105. ADVANCED: FUNCTION REGISTRY WITH DECORATOR
# =============================================================================

command_registry: dict[str, Callable[[], str]] = {}


def register_command(name: str) -> Callable[
    [Callable[[], str]],
    Callable[[], str],
]:
    """Register a function under a command name."""

    def decorator(
        function: Callable[[], str],
    ) -> Callable[[], str]:
        if name in command_registry:
            raise ValueError(f"Command already registered: {name}")

        command_registry[name] = function
        return function

    return decorator


@register_command("hello")
def command_hello() -> str:
    return "Hello command executed"


@register_command("status")
def command_status() -> str:
    return "System is operational"


def execute_command(name: str) -> str:
    """Execute a registered command."""
    if name not in command_registry:
        raise ValueError("Unknown command.")

    return command_registry[name]()


print(execute_command("hello"))
print(execute_command("status"))


# This pattern appears in plugin systems, command dispatchers,
# web routing, event handling, and extensible applications.


# =============================================================================
# 106. ADVANCED: EVENT CALLBACK SYSTEM
# =============================================================================

class EventManager:
    """Small event system based on registered callback functions."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable[[Any], None]]] = {}

    def subscribe(
        self,
        event_name: str,
        callback: Callable[[Any], None],
    ) -> None:
        """Register a callback for an event."""
        self._listeners.setdefault(event_name, []).append(callback)

    def publish(
        self,
        event_name: str,
        payload: Any,
    ) -> None:
        """Call all listeners registered for an event."""
        for callback in self._listeners.get(event_name, []):
            callback(payload)


event_manager = EventManager()


def on_user_created(payload: Any) -> None:
    print("User-created listener:", payload)


def on_user_created_audit(payload: Any) -> None:
    print("Audit listener:", payload)


event_manager.subscribe("user_created", on_user_created)
event_manager.subscribe("user_created", on_user_created_audit)

event_manager.publish(
    "user_created",
    {"username": "atul"},
)


# =============================================================================
# 107. PRODUCTION-STYLE FUNCTION DESIGN
# =============================================================================

def calculate_order_total(
    item_prices: Iterable[float],
    *,
    tax_rate: float = 18.0,
    discount_rate: float = 0.0,
    shipping_cost: float = 0.0,
) -> float:
    """
    Calculate an order's final total.

    Validation:
    - prices must not be negative
    - tax rate must be between 0 and 100
    - discount rate must be between 0 and 100
    - shipping cost must not be negative
    """
    prices = list(item_prices)

    if any(price < 0 for price in prices):
        raise ValueError("Item prices cannot be negative.")

    if not 0 <= tax_rate <= 100:
        raise ValueError("Tax rate must be between 0 and 100.")

    if not 0 <= discount_rate <= 100:
        raise ValueError("Discount rate must be between 0 and 100.")

    if shipping_cost < 0:
        raise ValueError("Shipping cost cannot be negative.")

    subtotal = sum(prices)

    discount = subtotal * discount_rate / 100
    taxable_amount = subtotal - discount
    tax = taxable_amount * tax_rate / 100

    return taxable_amount + tax + shipping_cost


print(
    "Order total:",
    calculate_order_total(
        [1000, 500, 250],
        tax_rate=18,
        discount_rate=10,
        shipping_cost=50,
    ),
)


# =============================================================================
# 108. PERFORMANCE CONSIDERATION: MATERIALIZATION
# =============================================================================

def average_without_materializing_twice(
    values: Iterable[float],
) -> float:
    """
    Calculate average while consuming the iterable once.

    This works with generators and avoids requiring a second traversal.
    """
    total = 0.0
    count = 0

    for value in values:
        total += value
        count += 1

    if count == 0:
        raise ValueError("Cannot average an empty iterable.")

    return total / count


print(
    "Generator average:",
    average_without_materializing_twice(
        (value for value in range(1, 6))
    ),
)


# =============================================================================
# 109. PERFORMANCE CONSIDERATION: LAZY PROCESSING
# =============================================================================

def generate_even_numbers(limit: int) -> Iterator[int]:
    """Yield even numbers lazily."""
    for number in range(limit):
        if number % 2 == 0:
            yield number


large_sequence = generate_even_numbers(1_000_000)

# Only the first five values are requested.
first_five = [next(large_sequence) for _ in range(5)]

print("First five lazy values:", first_five)


# Lazy processing avoids constructing one million results when only a few
# are needed.


# =============================================================================
# 110. SECURITY CONSIDERATION: AVOID eval FOR UNTRUSTED INPUT
# =============================================================================

# Never use eval() as a general-purpose way to process untrusted user input.
#
# For example, an unsafe pattern would conceptually be:
#
# user_expression = input(...)
# result = eval(user_expression)
#
# eval can execute arbitrary Python expressions and should not be treated
# as a safe calculator or validation mechanism.


def safe_operation(
    operation: str,
    first: float,
    second: float,
) -> float:
    """Execute only explicitly registered arithmetic operations."""
    allowed_operations = {
        "add": add,
        "subtract": subtract,
        "multiply": multiply,
        "divide": divide,
    }

    if operation not in allowed_operations:
        raise ValueError("Unsupported operation.")

    return allowed_operations[operation](first, second)


print(safe_operation("add", 10, 20))


# Explicit function registries are safer and easier to reason about than
# dynamically executing arbitrary input.


# =============================================================================
# 111. COMMON MISTAKE: FORGETTING PARENTHESES WHEN CALLING
# =============================================================================

def get_message() -> str:
    return "Hello"


function_reference = get_message
function_result = get_message()

print("Function reference:", function_reference)
print("Function result:", function_result)


# get_message refers to the function object.
# get_message() calls the function.


# =============================================================================
# 112. COMMON MISTAKE: RETURNING PRINTED OUTPUT
# =============================================================================

def incorrect_style(number: int) -> None:
    """Display a result but do not return it."""
    print(number * 2)


def reusable_style(number: int) -> int:
    """Return a result so the caller can decide what to do with it."""
    return number * 2


incorrect_result = incorrect_style(5)
reusable_result = reusable_style(5)

print("Printed function returned:", incorrect_result)
print("Reusable function returned:", reusable_result)


# A reusable function should generally return data when callers may need
# to process, store, test, or transform the result.


# =============================================================================
# 113. COMMON MISTAKE: TOO MANY RESPONSIBILITIES
# =============================================================================

# A function that validates data, performs database access, calculates
# financial values, formats HTML, sends an email, and logs everything
# becomes difficult to test and maintain.
#
# Prefer small functions with clear contracts and compose them.


# =============================================================================
# 114. COMMON MISTAKE: TOO MANY PARAMETERS
# =============================================================================

def create_report(
    title: str,
    author: str,
    department: str,
    format_name: str,
    include_summary: bool,
    include_charts: bool,
    page_size: str,
) -> dict[str, Any]:
    """Illustrate a large parameter list."""
    return {
        "title": title,
        "author": author,
        "department": department,
        "format": format_name,
        "include_summary": include_summary,
        "include_charts": include_charts,
        "page_size": page_size,
    }


# A complex configuration may be better represented by a dedicated data
# structure or configuration object rather than an enormous parameter list.


# =============================================================================
# 115. FUNCTION API STABILITY
# =============================================================================

# Public functions are part of an API when other code depends on them.
#
# Changing parameter names can break keyword callers:
#
# old:
# calculate_price(amount=100)
#
# renamed:
# calculate_price(value=100)
#
# Positional-only parameters can sometimes protect an implementation from
# making parameter names part of the public calling convention.


# =============================================================================
# 116. FUNCTION RETURN CONTRACTS
# =============================================================================

def find_discount_rate(customer_type: str) -> Optional[float]:
    """Return a discount rate for known customer types."""
    discount_rates = {
        "regular": 5.0,
        "premium": 10.0,
        "enterprise": 15.0,
    }

    return discount_rates.get(customer_type)


discount_rate = find_discount_rate("premium")

if discount_rate is not None:
    print("Discount rate:", discount_rate)


# A clear return contract should specify whether a function can return None,
# raise exceptions, or always return a concrete value.


# =============================================================================
# 117. FUNCTION COMPOSITION IN A DATA PIPELINE
# =============================================================================

def parse_integer(text: str) -> int:
    """Parse an integer from text."""
    return int(text.strip())


def double_integer(value: int) -> int:
    """Double an integer."""
    return value * 2


def format_integer(value: int) -> str:
    """Format an integer as text."""
    return f"Result = {value}"


text_value = " 21 "

parsed = parse_integer(text_value)
doubled = double_integer(parsed)
formatted = format_integer(doubled)

print(formatted)


# Explicit stages make debugging easier because every intermediate value
# can be inspected.


# =============================================================================
# 118. DEBUGGING FUNCTIONS
# =============================================================================

def debug_calculation(a: int, b: int) -> int:
    """A function whose intermediate state can be inspected."""
    product = a * b
    adjusted = product + 10

    print("Debug a:", a)
    print("Debug b:", b)
    print("Debug product:", product)
    print("Debug adjusted:", adjusted)

    return adjusted


print("Debug calculation result:", debug_calculation(5, 6))


# In real applications, structured logging is usually preferable to
# uncontrolled print statements.


# =============================================================================
# 119. TESTING BOUNDARY CONDITIONS
# =============================================================================

def percentage_score(score: float) -> str:
    """Classify a score using explicit boundaries."""
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


boundary_cases = [0, 59.999, 60, 69.999, 70, 79.999, 80, 89.999, 90, 100]

for boundary in boundary_cases:
    print(boundary, "->", percentage_score(boundary))


# Boundary tests are important because comparison operators such as < and <=
# can create subtle bugs.


# =============================================================================
# 120. FINAL INTEGRATED EXAMPLE: REUSABLE SALES ANALYSIS SYSTEM
# =============================================================================

def validate_sales_data(sales: Iterable[float]) -> list[float]:
    """Validate and materialize sales values."""
    values = list(sales)

    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        for value in values
    ):
        raise TypeError("Every sale must be numeric.")

    if any(value < 0 for value in values):
        raise ValueError("Sales values cannot be negative.")

    return [float(value) for value in values]


def calculate_sales_total(sales: Iterable[float]) -> float:
    """Return total sales."""
    validated_sales = validate_sales_data(sales)
    return sum(validated_sales)


def calculate_sales_average(sales: Iterable[float]) -> float:
    """Return average sale."""
    validated_sales = validate_sales_data(sales)

    if not validated_sales:
        raise ValueError("At least one sale is required.")

    return sum(validated_sales) / len(validated_sales)


def classify_sales_performance(total_sales: float) -> str:
    """Classify sales performance based on total revenue."""
    if total_sales < 10_000:
        return "Low"

    if total_sales < 50_000:
        return "Moderate"

    if total_sales < 100_000:
        return "High"

    return "Very high"


def build_sales_analysis(
    sales: Iterable[float],
) -> dict[str, Any]:
    """Build a complete reusable sales analysis."""
    validated_sales = validate_sales_data(sales)

    if not validated_sales:
        raise ValueError("Sales data cannot be empty.")

    total = calculate_sales_total(validated_sales)
    average = calculate_sales_average(validated_sales)
    performance = classify_sales_performance(total)

    return {
        "transaction_count": len(validated_sales),
        "total_sales": total,
        "average_sale": average,
        "performance": performance,
    }


sales_data = [12000, 18000, 9000, 25000, 31000]

analysis = build_sales_analysis(sales_data)

print("Sales analysis:")
for key, value in analysis.items():
    print(f"  {key}: {value}")


# =============================================================================
# 121. INTEGRATED FUNCTION TESTS
# =============================================================================

def test_sales_validation() -> None:
    assert validate_sales_data([1, 2, 3]) == [1.0, 2.0, 3.0]

    try:
        validate_sales_data([-1])
    except ValueError:
        pass
    else:
        raise AssertionError("Negative sales should fail validation.")


def test_sales_total() -> None:
    assert calculate_sales_total([100, 200, 300]) == 600


def test_sales_average() -> None:
    assert calculate_sales_average([10, 20, 30]) == 20


def test_sales_performance() -> None:
    assert classify_sales_performance(5000) == "Low"
    assert classify_sales_performance(20_000) == "Moderate"
    assert classify_sales_performance(70_000) == "High"
    assert classify_sales_performance(150_000) == "Very high"


def test_sales_analysis() -> None:
    result = build_sales_analysis([100, 200, 300])

    assert result["transaction_count"] == 3
    assert result["total_sales"] == 600
    assert result["average_sale"] == 200
    assert result["performance"] == "Low"


run_test("Sales validation", test_sales_validation)
run_test("Sales total", test_sales_total)
run_test("Sales average", test_sales_average)
run_test("Sales performance", test_sales_performance)
run_test("Sales analysis", test_sales_analysis)


# =============================================================================
# 122. KEY FUNCTION DESIGN CHECKLIST
# =============================================================================

def function_design_checklist() -> list[str]:
    """
    Return practical questions to consider when designing a function.

    This is executable data rather than a prose-only checklist.
    """
    return [
        "Does the function have one clear responsibility?",
        "Are parameter names meaningful?",
        "Are required parameters clearly separated from optional parameters?",
        "Should optional parameters be keyword-only?",
        "Are input values validated at the appropriate boundary?",
        "Is the return value clearly defined?",
        "Can the function avoid unnecessary side effects?",
        "Would a caller benefit from a reusable return value rather than print?",
        "Are edge cases handled?",
        "Are exceptions specific and meaningful?",
        "Is the function easy to test independently?",
        "Does it unnecessarily depend on global state?",
        "Would accepting Iterable improve reuse?",
        "Would caching actually improve performance?",
        "Could mutable default arguments create shared state?",
        "Is the public API stable and understandable?",
        "Are security-sensitive inputs validated?",
        "Has performance been measured before optimization?",
    ]


for question in function_design_checklist():
    print("CHECK:", question)


# =============================================================================
# 123. FINAL EXECUTABLE DEMONSTRATION
# =============================================================================

def main() -> None:
    """
    Run a concise integrated demonstration.

    Keeping executable entry logic inside main() prevents accidental execution
    when this file is imported as a module.
    """
    numbers = [10, 20, 30, 40, 50]

    total = calculate_total(numbers)
    average = calculate_average(numbers)
    squares = square_numbers(numbers)

    print("\nFinal demonstration")
    print("-------------------")
    print("Numbers:", numbers)
    print("Total:", total)
    print("Average:", average)
    print("Squares:", squares)

    calculator_result = calculate_expression(100, "*", 5)
    print("Calculator result:", calculator_result)

    tax_calculator = create_tax_calculator(18)
    print("Tax on 5000 at 18%:", tax_calculator(5000))

    fibonacci_result = fibonacci_cached(25)
    print("Fibonacci(25):", fibonacci_result)

    report = build_sales_analysis(
        [5000, 7500, 12500],
    )
    print("Sales report:", report)


if __name__ == "__main__":
    main()


# =============================================================================
# END OF STUDY SCRIPT
# =============================================================================
