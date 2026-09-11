"""
Programming Fundamentals: Variables, Data Types, Operators, and Expressions
===========================================================================
A comprehensive standalone study script progressing from absolute beginner
concepts to advanced Python behavior.

This file intentionally uses only the Python standard library.
"""

from __future__ import annotations

import math
import operator
import sys
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any


# ============================================================================
# 1. VARIABLES
# ============================================================================

print("\n" + "=" * 78)
print("1. VARIABLES")
print("=" * 78)

# A variable is a name bound to an object.
# Python does not require a separate declaration such as "int age".
age = 25
name = "Atul"
height = 1.75
is_student = True

print("name:", name)
print("age:", age)
print("height:", height)
print("is_student:", is_student)

# A variable can be rebound to an object of another type.
value = 100
print("value before rebinding:", value, type(value).__name__)

value = "one hundred"
print("value after rebinding:", value, type(value).__name__)

# Multiple assignment.
x, y, z = 10, 20, 30
print("x, y, z:", x, y, z)

# The same value can be assigned to multiple variables.
first = second = third = 0
print("first, second, third:", first, second, third)

# Swapping does not require a temporary variable.
x, y = y, x
print("after swapping x and y:", x, y)

# Variable names are case-sensitive.
score = 90
Score = 95
print("score:", score)
print("Score:", Score)

# Valid naming conventions:
student_name = "Ravi"
total_marks = 450
_private_value = 42
number2 = 10

print(student_name, total_marks, _private_value, number2)

# These would be invalid syntax and are intentionally represented as strings:
invalid_variable_names = [
    "2number",
    "student-name",
    "class",
]

print("Examples of invalid/reserved names:", invalid_variable_names)

# Python keywords cannot normally be used as variable names.
import keyword

print("Python keywords:", keyword.kwlist)


# ============================================================================
# 2. OBJECTS, REFERENCES, IDENTITY, AND MUTABILITY
# ============================================================================

print("\n" + "=" * 78)
print("2. OBJECTS, REFERENCES, IDENTITY, AND MUTABILITY")
print("=" * 78)

number_a = 500
number_b = number_a

print("number_a == number_b:", number_a == number_b)
print("number_a is number_b:", number_a is number_b)

# "==" compares values.
# "is" compares object identity.
list_a = [1, 2, 3]
list_b = [1, 2, 3]

print("list_a == list_b:", list_a == list_b)
print("list_a is list_b:", list_a is list_b)

list_c = list_a
list_c.append(4)

print("list_a after modifying list_c:", list_a)
print("list_c:", list_c)

# Both names refer to the same mutable list.
print("list_a is list_c:", list_a is list_c)

# Immutable objects cannot be modified in place.
immutable_number = 10
original_id = id(immutable_number)
immutable_number += 1

print("new immutable_number:", immutable_number)
print("object identity changed:", original_id != id(immutable_number))

# Common singleton checks.
nothing = None
print("nothing is None:", nothing is None)


# ============================================================================
# 3. CORE DATA TYPES
# ============================================================================

print("\n" + "=" * 78)
print("3. CORE DATA TYPES")
print("=" * 78)

integer_value = 42
negative_integer = -17
zero_integer = 0

floating_value = 3.14159
scientific_value = 6.022e23

complex_value = 3 + 4j

boolean_true = True
boolean_false = False

text = "Programming"
empty_text = ""

nothing_value = None

values = [
    ("integer", integer_value),
    ("negative integer", negative_integer),
    ("zero", zero_integer),
    ("float", floating_value),
    ("scientific notation", scientific_value),
    ("complex", complex_value),
    ("boolean", boolean_true),
    ("string", text),
    ("empty string", empty_text),
    ("None", nothing_value),
]

for label, value in values:
    print(f"{label:22}: {value!r:>25} -> {type(value).__name__}")


# ============================================================================
# 4. INTEGER
# ============================================================================

print("\n" + "=" * 78)
print("4. INTEGER")
print("=" * 78)

integer_examples = [0, 1, -1, 42, 10**50]

for value in integer_examples:
    print(value, type(value).__name__)

# Python integers have arbitrary precision.
very_large_integer = 10**100
print("100-digit power:", very_large_integer)
print("number of digits:", len(str(very_large_integer)))

# Different integer representations.
binary_number = 0b1010
octal_number = 0o12
hexadecimal_number = 0xA

print("binary 0b1010:", binary_number)
print("octal 0o12:", octal_number)
print("hexadecimal 0xA:", hexadecimal_number)

print("binary representation:", bin(42))
print("octal representation:", oct(42))
print("hexadecimal representation:", hex(42))


# ============================================================================
# 5. FLOAT
# ============================================================================

print("\n" + "=" * 78)
print("5. FLOAT")
print("=" * 78)

temperature = 36.5
price = 199.99
ratio = 0.75

print(temperature, price, ratio)

# Floating-point values are generally represented using binary floating point.
floating_result = 0.1 + 0.2

print("0.1 + 0.2:", floating_result)
print("exact equality with 0.3:", floating_result == 0.3)
print("math.isclose:", math.isclose(floating_result, 0.3))

# Special floating-point values.
positive_infinity = float("inf")
negative_infinity = float("-inf")
not_a_number = float("nan")

print("positive infinity:", positive_infinity)
print("negative infinity:", negative_infinity)
print("NaN:", not_a_number)
print("isinf:", math.isinf(positive_infinity))
print("isnan:", math.isnan(not_a_number))


# ============================================================================
# 6. DECIMAL AND FRACTION
# ============================================================================

print("\n" + "=" * 78)
print("6. DECIMAL AND FRACTION")
print("=" * 78)

# Decimal is useful when decimal arithmetic needs predictable precision.
decimal_a = Decimal("0.1")
decimal_b = Decimal("0.2")
decimal_result = decimal_a + decimal_b

print("Decimal 0.1 + 0.2:", decimal_result)
print("Decimal comparison:", decimal_result == Decimal("0.3"))

# Fraction represents rational numbers exactly.
fraction_a = Fraction(1, 3)
fraction_b = Fraction(1, 6)

print("1/3:", fraction_a)
print("1/6:", fraction_b)
print("1/3 + 1/6:", fraction_a + fraction_b)


# ============================================================================
# 7. COMPLEX NUMBERS
# ============================================================================

print("\n" + "=" * 78)
print("7. COMPLEX NUMBERS")
print("=" * 78)

complex_a = 3 + 4j
complex_b = 1 - 2j

print("complex_a:", complex_a)
print("complex_b:", complex_b)
print("addition:", complex_a + complex_b)
print("multiplication:", complex_a * complex_b)
print("real part:", complex_a.real)
print("imaginary part:", complex_a.imag)
print("magnitude:", abs(complex_a))
print("conjugate:", complex_a.conjugate())


# ============================================================================
# 8. BOOLEAN
# ============================================================================

print("\n" + "=" * 78)
print("8. BOOLEAN")
print("=" * 78)

is_authenticated = True
has_permission = False

print("is_authenticated:", is_authenticated)
print("has_permission:", has_permission)
print("True + True:", True + True)
print("True * 10:", True * 10)

# bool is a subclass of int in Python.
print("isinstance(True, int):", isinstance(True, int))


# ============================================================================
# 9. STRINGS
# ============================================================================

print("\n" + "=" * 78)
print("9. STRINGS")
print("=" * 78)

single_quoted = 'Hello'
double_quoted = "World"
multiline_text = """This is
a multiline
string."""

print(single_quoted)
print(double_quoted)
print(multiline_text)

# Strings are sequences and are immutable.
message = "Python"
print("first character:", message[0])
print("last character:", message[-1])
print("slice:", message[1:4])
print("every second character:", message[::2])

# Concatenation.
full_name = "Atul" + " " + "Pandey"
print("concatenation:", full_name)

# Repetition.
separator = "-" * 20
print(separator)

# Length.
print("length:", len(message))

# Membership.
print("'Py' in message:", "Py" in message)
print("'Java' in message:", "Java" in message)

# Useful formatting.
person_name = "Atul"
person_age = 25

print(f"{person_name} is {person_age} years old.")
print("{} is {} years old.".format(person_name, person_age))

# String conversion.
number_as_text = str(12345)
print("str(12345):", number_as_text, type(number_as_text).__name__)


# ============================================================================
# 10. COLLECTION DATA TYPES
# ============================================================================

print("\n" + "=" * 78)
print("10. COLLECTION DATA TYPES")
print("=" * 78)

# List: ordered and mutable.
numbers_list = [10, 20, 30]
numbers_list.append(40)
numbers_list[0] = 5
print("list:", numbers_list)

# Tuple: ordered and immutable.
numbers_tuple = (10, 20, 30)
print("tuple:", numbers_tuple)

# Set: unordered collection of unique elements.
numbers_set = {1, 2, 2, 3, 3}
print("set:", numbers_set)

# Dictionary: mapping of keys to values.
student = {
    "name": "Atul",
    "age": 25,
    "marks": 88,
}
print("dictionary:", student)

# Mutability comparison.
mutable_objects = [numbers_list, student]
immutable_objects = [numbers_tuple, "Python", 42, True]

print("mutable examples:", mutable_objects)
print("immutable examples:", immutable_objects)


# ============================================================================
# 11. TYPE CONVERSION
# ============================================================================

print("\n" + "=" * 78)
print("11. TYPE CONVERSION")
print("=" * 78)

text_number = "100"
converted_integer = int(text_number)

decimal_text = "12.50"
converted_float = float(decimal_text)

integer_to_float = float(25)
float_to_integer = int(25.99)

print("int('100'):", converted_integer)
print("float('12.50'):", converted_float)
print("float(25):", integer_to_float)
print("int(25.99):", float_to_integer)

# Boolean conversion follows truth-value rules.
truth_values = [
    0,
    1,
    "",
    "Python",
    [],
    [1],
    None,
]

for value in truth_values:
    print(f"bool({value!r}) -> {bool(value)}")

# Conversion failures should be handled.
try:
    invalid_number = int("Python")
except ValueError as error:
    print("Conversion error:", error)


# ============================================================================
# 12. INPUT AND OUTPUT
# ============================================================================

print("\n" + "=" * 78)
print("12. INPUT AND OUTPUT")
print("=" * 78)

# input() always returns a string.
# Interactive input is demonstrated safely through a function that accepts
# an optional supplied value.
def parse_user_age(raw_age: str) -> int:
    """Convert text input to a validated integer age."""
    age_value = int(raw_age)

    if age_value < 0:
        raise ValueError("Age cannot be negative.")

    return age_value


sample_input = "25"
parsed_age = parse_user_age(sample_input)

print("sample input:", sample_input)
print("parsed age:", parsed_age)
print("type after conversion:", type(parsed_age).__name__)


# ============================================================================
# 13. ARITHMETIC OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("13. ARITHMETIC OPERATORS")
print("=" * 78)

a = 17
b = 5

print("a =", a)
print("b =", b)
print("a + b =", a + b)
print("a - b =", a - b)
print("a * b =", a * b)
print("a / b =", a / b)
print("a // b =", a // b)
print("a % b =", a % b)
print("a ** b =", a ** b)

# / always produces a floating-point result for ordinary numeric operands.
print("10 / 2:", 10 / 2)

# // performs floor division.
print("17 // 5:", 17 // 5)
print("-17 // 5:", -17 // 5)

# % gives the remainder according to Python's floor-division relationship.
print("17 % 5:", 17 % 5)
print("-17 % 5:", -17 % 5)

# Division by zero raises an exception.
try:
    print(10 / 0)
except ZeroDivisionError as error:
    print("Division error:", error)


# ============================================================================
# 14. COMPARISON OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("14. COMPARISON OPERATORS")
print("=" * 78)

left = 10
right = 20

print("left == right:", left == right)
print("left != right:", left != right)
print("left < right:", left < right)
print("left <= right:", left <= right)
print("left > right:", left > right)
print("left >= right:", left >= right)

# Chained comparisons are valid and readable.
temperature = 25
print("20 <= temperature <= 30:", 20 <= temperature <= 30)

# Strings can be compared lexicographically.
print("'apple' < 'banana':", "apple" < "banana")

# Equality and identity are different concepts.
string_a = "hello"
string_b = "".join(["he", "llo"])

print("string_a == string_b:", string_a == string_b)
print("string_a is string_b:", string_a is string_b)


# ============================================================================
# 15. LOGICAL OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("15. LOGICAL OPERATORS")
print("=" * 78)

has_id = True
has_ticket = False

print("has_id and has_ticket:", has_id and has_ticket)
print("has_id or has_ticket:", has_id or has_ticket)
print("not has_ticket:", not has_ticket)

# and/or return operands rather than necessarily returning True or False.
print("'Python' and 100:", "Python" and 100)
print("'' and 100:", "" and 100)
print("'Python' or 100:", "Python" or 100)
print("'' or 100:", "" or 100)

# Short-circuit evaluation.
def expensive_operation() -> str:
    print("expensive_operation() executed")
    return "result"


condition = False
result = condition and expensive_operation()
print("short-circuit result:", result)

condition = True
result = condition or expensive_operation()
print("short-circuit OR result:", result)


# ============================================================================
# 16. ASSIGNMENT OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("16. ASSIGNMENT OPERATORS")
print("=" * 78)

value = 10

value += 5
print("after += 5:", value)

value -= 3
print("after -= 3:", value)

value *= 2
print("after *= 2:", value)

value /= 4
print("after /= 4:", value)

value //= 2
print("after //= 2:", value)

value %= 3
print("after %= 3:", value)

value **= 3
print("after **= 3:", value)


# ============================================================================
# 17. BITWISE OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("17. BITWISE OPERATORS")
print("=" * 78)

binary_a = 0b1100
binary_b = 0b1010

print("a:", bin(binary_a))
print("b:", bin(binary_b))
print("a & b:", bin(binary_a & binary_b))
print("a | b:", bin(binary_a | binary_b))
print("a ^ b:", bin(binary_a ^ binary_b))
print("~a:", ~binary_a)
print("a << 2:", binary_a << 2)
print("a >> 2:", binary_a >> 2)

# Bit masks are useful for flags.
READ = 0b001
WRITE = 0b010
EXECUTE = 0b100

permissions = READ | WRITE

print("permissions:", bin(permissions))
print("has READ:", bool(permissions & READ))
print("has EXECUTE:", bool(permissions & EXECUTE))

permissions |= EXECUTE
print("after adding EXECUTE:", bin(permissions))

permissions &= ~WRITE
print("after removing WRITE:", bin(permissions))


# ============================================================================
# 18. MEMBERSHIP OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("18. MEMBERSHIP OPERATORS")
print("=" * 78)

languages = ["Python", "SQL", "Java"]
print("'Python' in languages:", "Python" in languages)
print("'C++' not in languages:", "C++" not in languages)

text = "programming"
print("'gram' in text:", "gram" in text)

student_record = {"name": "Atul", "age": 25}
print("'name' in student_record:", "name" in student_record)
print("'Atul' in student_record:", "Atul" in student_record)


# ============================================================================
# 19. OPERATOR PRECEDENCE
# ============================================================================

print("\n" + "=" * 78)
print("19. OPERATOR PRECEDENCE")
print("=" * 78)

expression_1 = 2 + 3 * 4
expression_2 = (2 + 3) * 4

print("2 + 3 * 4:", expression_1)
print("(2 + 3) * 4:", expression_2)

# A practical precedence ordering, from higher to lower:
# 1. Parentheses/grouping
# 2. Exponentiation **
# 3. Unary +, -, ~
# 4. *, /, //, %
# 5. +, -
# 6. Comparisons
# 7. not
# 8. and
# 9. or
#
# When readability matters, use parentheses even when precedence already
# determines the intended result.

complex_expression = (10 + 5) * 2 ** 3 - 4 / 2
print("complex expression:", complex_expression)


# ============================================================================
# 20. EXPRESSIONS
# ============================================================================

print("\n" + "=" * 78)
print("20. EXPRESSIONS")
print("=" * 78)

# An expression produces a value.
simple_expression = 10 + 20
mixed_expression = (10 * 5) > 20
string_expression = "Hello" + " " + "Python"

print("simple expression:", simple_expression)
print("comparison expression:", mixed_expression)
print("string expression:", string_expression)

# Function calls are expressions because they produce values.
expression_result = len("Python")
print("len('Python'):", expression_result)

# Conditional expressions.
age = 22
category = "adult" if age >= 18 else "minor"

print("category:", category)

# Assignment expressions using := can assign and evaluate in one expression.
if (length := len("Programming")) > 10:
    print("Length:", length)


# ============================================================================
# 21. UNARY OPERATORS
# ============================================================================

print("\n" + "=" * 78)
print("21. UNARY OPERATORS")
print("=" * 78)

number = 10

print("+number:", +number)
print("-number:", -number)
print("not True:", not True)
print("~number:", ~number)

# For integers, ~x is equivalent to -x - 1.
print("~10:", ~10)
print("-10 - 1:", -10 - 1)


# ============================================================================
# 22. OPERATOR OVERLOADING
# ============================================================================

print("\n" + "=" * 78)
print("22. OPERATOR OVERLOADING")
print("=" * 78)

# Operators can have different meanings depending on operand types.
print("2 + 3:", 2 + 3)
print("'2' + '3':", "2" + "3")
print("[1] + [2]:", [1] + [2])

# User-defined classes can define operator behavior.
class Money:
    """Simple monetary value demonstrating operator overloading."""

    def __init__(self, amount: Decimal, currency: str = "INR") -> None:
        self.amount = Decimal(amount)
        self.currency = currency

    def __add__(self, other: "Money") -> "Money":
        if not isinstance(other, Money):
            return NotImplemented

        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies.")

        return Money(self.amount + other.amount, self.currency)

    def __repr__(self) -> str:
        return f"Money({self.amount}, {self.currency!r})"


money_a = Money(Decimal("100.50"))
money_b = Money(Decimal("49.50"))
money_total = money_a + money_b

print("money_a:", money_a)
print("money_b:", money_b)
print("money_a + money_b:", money_total)


# ============================================================================
# 23. COMPOUND ASSIGNMENT AND MUTABLE OBJECTS
# ============================================================================

print("\n" + "=" * 78)
print("23. COMPOUND ASSIGNMENT AND MUTABLE OBJECTS")
print("=" * 78)

numbers = [1, 2]
same_reference = numbers

numbers += [3]

print("numbers:", numbers)
print("same_reference:", same_reference)
print("same object:", numbers is same_reference)

# For lists, += mutates the existing list.
# For immutable objects such as tuples, += creates a new object.
tuple_values = (1, 2)
old_tuple_id = id(tuple_values)

tuple_values += (3,)

print("tuple_values:", tuple_values)
print("tuple identity changed:", id(tuple_values) != old_tuple_id)


# ============================================================================
# 24. TRUTHINESS
# ============================================================================

print("\n" + "=" * 78)
print("24. TRUTHINESS")
print("=" * 78)

false_like_values = [
    False,
    None,
    0,
    0.0,
    0j,
    "",
    [],
    (),
    {},
    set(),
]

for value in false_like_values:
    print(f"{value!r:12} -> bool(value) = {bool(value)}")

true_like_values = [
    True,
    1,
    -1,
    3.14,
    "False",
    [0],
    {"x": 0},
]

for value in true_like_values:
    print(f"{value!r:12} -> bool(value) = {bool(value)}")


# ============================================================================
# 25. TYPE CHECKING
# ============================================================================

print("\n" + "=" * 78)
print("25. TYPE CHECKING")
print("=" * 78)

sample_values: list[Any] = [10, 3.14, "Python", True, None, [1, 2]]

for value in sample_values:
    print(
        repr(value),
        "type =", type(value).__name__,
        "is int =", isinstance(value, int),
    )

# isinstance() supports inheritance-aware checks.
print("isinstance(True, int):", isinstance(True, int))
print("type(True) is int:", type(True) is int)


# ============================================================================
# 26. CONVERSION AND VALIDATION FUNCTIONS
# ============================================================================

print("\n" + "=" * 78)
print("26. CONVERSION AND VALIDATION FUNCTIONS")
print("=" * 78)


def convert_percentage(value: Any) -> float:
    """
    Convert a numeric-like value into a percentage between 0 and 100.

    bool is explicitly rejected because True and False are technically ints
    in Python but should not represent a percentage in this API.
    """
    if isinstance(value, bool):
        raise TypeError("Boolean values are not valid percentages.")

    try:
        percentage = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Percentage must be numeric.") from error

    if not math.isfinite(percentage):
        raise ValueError("Percentage must be finite.")

    if not 0 <= percentage <= 100:
        raise ValueError("Percentage must be between 0 and 100.")

    return percentage


for candidate in [50, "75.5", 0, 100]:
    print(candidate, "->", convert_percentage(candidate))

for candidate in [-1, 101, "abc", True]:
    try:
        convert_percentage(candidate)
    except (TypeError, ValueError) as error:
        print(candidate, "-> rejected:", error)


# ============================================================================
# 27. NUMERIC COMPARISON AND PRECISION
# ============================================================================

print("\n" + "=" * 78)
print("27. NUMERIC COMPARISON AND PRECISION")
print("=" * 78)


def approximately_equal(first: float, second: float, tolerance: float = 1e-9) -> bool:
    """Compare floating-point values using an absolute tolerance."""
    return math.isclose(first, second, abs_tol=tolerance, rel_tol=tolerance)


print("approximately_equal(0.1 + 0.2, 0.3):",
      approximately_equal(0.1 + 0.2, 0.3))

# Decimal from a string preserves the intended decimal value.
print("Decimal from string:", Decimal("0.1"))
print("Decimal from float:", Decimal(0.1))


# ============================================================================
# 28. MATHEMATICAL FUNCTIONS
# ============================================================================

print("\n" + "=" * 78)
print("28. MATHEMATICAL FUNCTIONS")
print("=" * 78)

number = 16

print("abs(-16):", abs(-16))
print("round(3.14159, 2):", round(3.14159, 2))
print("pow(2, 5):", pow(2, 5))
print("math.sqrt(16):", math.sqrt(16))
print("math.floor(3.9):", math.floor(3.9))
print("math.ceil(3.1):", math.ceil(3.1))
print("math.factorial(5):", math.factorial(5))

# divmod returns quotient and remainder together.
quotient, remainder = divmod(17, 5)
print("divmod(17, 5):", quotient, remainder)


# ============================================================================
# 29. AUGMENTED ASSIGNMENT WITH DIFFERENT TYPES
# ============================================================================

print("\n" + "=" * 78)
print("29. AUGMENTED ASSIGNMENT WITH DIFFERENT TYPES")
print("=" * 78)

text_value = "Hello"
text_value += " Python"
print("string +=:", text_value)

list_value = [1, 2]
list_value += [3, 4]
print("list +=:", list_value)

number_value = 10
number_value *= 2
print("number *=:", number_value)


# ============================================================================
# 30. WALRUS OPERATOR
# ============================================================================

print("\n" + "=" * 78)
print("30. ASSIGNMENT EXPRESSIONS")
print("=" * 78)

# The assignment expression := both assigns a value and returns it.
data = "Programming"

if (data_length := len(data)) >= 10:
    print("data length:", data_length)

# It is useful when the computed value is needed immediately in a condition.
items = ["Python", "SQL", "Git"]
if (count := len(items)) > 0:
    print("There are", count, "items.")


# ============================================================================
# 31. CONDITIONAL EXPRESSIONS
# ============================================================================

print("\n" + "=" * 78)
print("31. CONDITIONAL EXPRESSIONS")
print("=" * 78)


def classify_number(number: float) -> str:
    """Return a simple classification using a conditional expression."""
    return "positive" if number > 0 else "negative" if number < 0 else "zero"


for value in [-10, 0, 25]:
    print(value, "->", classify_number(value))


# ============================================================================
# 32. EXPRESSION EVALUATION ORDER
# ============================================================================

print("\n" + "=" * 78)
print("32. EXPRESSION EVALUATION ORDER")
print("=" * 78)


def show(label: str, value: Any) -> Any:
    """Display evaluation order and return the supplied value."""
    print("evaluating:", label)
    return value


evaluation_result = show("first", 10) + show("second", 20)
print("evaluation result:", evaluation_result)

# Python evaluates operands from left to right in ordinary expressions,
# while respecting the operator's precedence and short-circuit rules.


# ============================================================================
# 33. BUILT-IN OPERATORS MODULE
# ============================================================================

print("\n" + "=" * 78)
print("33. OPERATOR FUNCTIONS")
print("=" * 78)

operation_functions = {
    "addition": operator.add,
    "subtraction": operator.sub,
    "multiplication": operator.mul,
    "division": operator.truediv,
    "floor division": operator.floordiv,
    "modulo": operator.mod,
    "power": operator.pow,
}

for operation_name, operation_function in operation_functions.items():
    print(operation_name, "->", operation_function(10, 3))

# operator.eq is equivalent to == for the supplied operands.
print("operator.eq(10, 10):", operator.eq(10, 10))
print("operator.lt(10, 20):", operator.lt(10, 20))


# ============================================================================
# 34. EXPRESSIONS WITH DIFFERENT TYPES
# ============================================================================

print("\n" + "=" * 78)
print("34. EXPRESSIONS WITH DIFFERENT TYPES")
print("=" * 78)

# Compatible numeric types may participate in arithmetic.
print("integer + float:", 10 + 2.5)
print("integer + complex:", 10 + 2j)

# Incompatible types usually raise TypeError.
try:
    print(10 + "5")
except TypeError as error:
    print("Type error:", error)

try:
    print("Age: " + 25)
except TypeError as error:
    print("String concatenation error:", error)

# Explicit conversion resolves the second case.
print("Age: " + str(25))


# ============================================================================
# 35. INTEGER DIVISION AND NEGATIVE VALUES
# ============================================================================

print("\n" + "=" * 78)
print("35. FLOOR DIVISION WITH NEGATIVE VALUES")
print("=" * 78)

examples = [
    (7, 3),
    (-7, 3),
    (7, -3),
    (-7, -3),
]

for numerator, denominator in examples:
    quotient = numerator // denominator
    remainder = numerator % denominator
    print(
        f"{numerator} // {denominator} = {quotient}, "
        f"{numerator} % {denominator} = {remainder}"
    )
    print(
        "reconstruction:",
        quotient * denominator + remainder
    )


# ============================================================================
# 36. FINANCIAL CALCULATION WITH DECIMAL
# ============================================================================

print("\n" + "=" * 78)
print("36. FINANCIAL CALCULATION WITH DECIMAL")
print("=" * 78)


def calculate_invoice(
    unit_price: Decimal,
    quantity: int,
    tax_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate subtotal, tax, and total using Decimal."""
    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative.")

    subtotal = unit_price * quantity
    tax = subtotal * tax_rate / Decimal("100")
    total = subtotal + tax

    return subtotal, tax, total


subtotal, tax, total = calculate_invoice(
    Decimal("199.99"),
    3,
    Decimal("18"),
)

print("subtotal:", subtotal)
print("tax:", tax)
print("total:", total)


# ============================================================================
# 37. EXPRESSION DECOMPOSITION
# ============================================================================

print("\n" + "=" * 78)
print("37. EXPRESSION DECOMPOSITION")
print("=" * 78)

# A long expression can be decomposed into meaningful intermediate variables.
price_per_item = Decimal("125.50")
quantity = 4
discount_rate = Decimal("10")
tax_rate = Decimal("18")

gross_amount = price_per_item * quantity
discount_amount = gross_amount * discount_rate / Decimal("100")
net_amount = gross_amount - discount_amount
tax_amount = net_amount * tax_rate / Decimal("100")
final_amount = net_amount + tax_amount

print("gross amount:", gross_amount)
print("discount amount:", discount_amount)
print("net amount:", net_amount)
print("tax amount:", tax_amount)
print("final amount:", final_amount)


# ============================================================================
# 38. SAFE NUMERIC PARSING
# ============================================================================

print("\n" + "=" * 78)
print("38. SAFE NUMERIC PARSING")
print("=" * 78)


def parse_number(value: str) -> int | float:
    """
    Parse an integer or floating-point string.

    The function rejects non-string inputs to keep the interface explicit.
    """
    if not isinstance(value, str):
        raise TypeError("parse_number expects a string.")

    stripped = value.strip()

    if not stripped:
        raise ValueError("Number cannot be empty.")

    try:
        return int(stripped)
    except ValueError:
        try:
            parsed_float = float(stripped)
        except ValueError as error:
            raise ValueError(f"Invalid numeric value: {value!r}") from error

        if not math.isfinite(parsed_float):
            raise ValueError("Number must be finite.")

        return parsed_float


for raw_value in ["42", "3.14", " -17 ", "0.25"]:
    print(raw_value, "->", parse_number(raw_value))

for raw_value in ["", "hello", "nan", "inf"]:
    try:
        parse_number(raw_value)
    except (TypeError, ValueError) as error:
        print(raw_value, "-> rejected:", error)


# ============================================================================
# 39. CONSTANTS
# ============================================================================

print("\n" + "=" * 78)
print("39. CONSTANTS")
print("=" * 78)

# Python has no enforced constant declaration.
# UPPER_CASE is the conventional notation for values intended not to change.
PI = math.pi
TAX_RATE = Decimal("18")
MAX_CONNECTIONS = 100

print("PI:", PI)
print("TAX_RATE:", TAX_RATE)
print("MAX_CONNECTIONS:", MAX_CONNECTIONS)


# ============================================================================
# 40. NAMING AND READABILITY
# ============================================================================

print("\n" + "=" * 78)
print("40. NAMING AND READABILITY")
print("=" * 78)

# Poor:
a = 500
b = 18
c = a * b / 100

# Better:
salary = 500
tax_percentage = 18
tax_amount = salary * tax_percentage / 100

print("tax amount:", tax_amount)


# ============================================================================
# 41. ALIASING AND COPYING
# ============================================================================

print("\n" + "=" * 78)
print("41. ALIASING AND COPYING")
print("=" * 78)

original = [1, 2, 3]
alias = original
shallow_copy = original.copy()

alias.append(4)

print("original after alias mutation:", original)
print("alias:", alias)
print("shallow_copy:", shallow_copy)

print("original is alias:", original is alias)
print("original is shallow_copy:", original is shallow_copy)


# ============================================================================
# 42. NESTED MUTABLE OBJECTS
# ============================================================================

print("\n" + "=" * 78)
print("42. NESTED MUTABLE OBJECTS")
print("=" * 78)

nested_original = [[1, 2], [3, 4]]
nested_copy = nested_original.copy()

nested_copy[0].append(99)

print("nested_original:", nested_original)
print("nested_copy:", nested_copy)

# A shallow copy copies only the outer container.
# Deep copying is required when independent nested mutable structures are needed.
import copy

nested_deep_copy = copy.deepcopy(nested_original)
nested_deep_copy[0].append(100)

print("nested_original after deep-copy mutation:", nested_original)
print("nested_deep_copy:", nested_deep_copy)


# ============================================================================
# 43. HASHABILITY
# ============================================================================

print("\n" + "=" * 78)
print("43. HASHABILITY")
print("=" * 78)

hashable_values = [
    42,
    3.14,
    "Python",
    (1, 2, 3),
]

for value in hashable_values:
    print(repr(value), "hash:", hash(value))

# Lists are mutable and therefore unhashable.
try:
    hash([1, 2, 3])
except TypeError as error:
    print("Unhashable list:", error)

# Hashability matters for dictionary keys and set members.


# ============================================================================
# 44. EXPRESSION-BASED DATA TRANSFORMATION
# ============================================================================

print("\n" + "=" * 78)
print("44. EXPRESSION-BASED DATA TRANSFORMATION")
print("=" * 78)

raw_scores = [55, 72, 88, 91, 64]

# List comprehensions are expressions that construct lists.
adjusted_scores = [score + 5 for score in raw_scores]
passing_scores = [score for score in raw_scores if score >= 60]

print("raw scores:", raw_scores)
print("adjusted scores:", adjusted_scores)
print("passing scores:", passing_scores)

# Dictionary comprehension.
score_labels = {
    score: "Pass" if score >= 60 else "Fail"
    for score in raw_scores
}

print("score labels:", score_labels)

# Set comprehension.
remainders = {score % 10 for score in raw_scores}
print("unique remainders:", remainders)


# ============================================================================
# 45. EXPRESSIONS WITH FUNCTIONS
# ============================================================================

print("\n" + "=" * 78)
print("45. EXPRESSIONS WITH FUNCTIONS")
print("=" * 78)


def calculate_area(length: float, width: float) -> float:
    """Return rectangle area."""
    if length < 0 or width < 0:
        raise ValueError("Dimensions cannot be negative.")

    return length * width


def calculate_perimeter(length: float, width: float) -> float:
    """Return rectangle perimeter."""
    if length < 0 or width < 0:
        raise ValueError("Dimensions cannot be negative.")

    return 2 * (length + width)


length = 10
width = 5

area = calculate_area(length, width)
perimeter = calculate_perimeter(length, width)

print("area:", area)
print("perimeter:", perimeter)
print("area-to-perimeter ratio:", area / perimeter)


# ============================================================================
# 46. EDGE CASES
# ============================================================================

print("\n" + "=" * 78)
print("46. IMPORTANT EDGE CASES")
print("=" * 78)

edge_cases = [
    ("empty string", ""),
    ("zero", 0),
    ("negative number", -1),
    ("very large integer", 10**100),
    ("negative zero float", -0.0),
    ("None", None),
    ("NaN", float("nan")),
    ("infinity", float("inf")),
]

for label, value in edge_cases:
    print(
        f"{label:22}: value={value!r}, "
        f"type={type(value).__name__}, "
        f"bool={bool(value)}"
    )

print("math.isnan(float('nan')):", math.isnan(float("nan")))
print("math.isfinite(100):", math.isfinite(100))
print("math.isfinite(float('inf')):", math.isfinite(float("inf")))


# ============================================================================
# 47. EXCEPTION TYPES RELATED TO EXPRESSIONS
# ============================================================================

print("\n" + "=" * 78)
print("47. COMMON EXPRESSION ERRORS")
print("=" * 78)

error_examples = [
    ("division by zero", lambda: 10 / 0),
    ("invalid conversion", lambda: int("abc")),
    ("unsupported operation", lambda: 10 + "10"),
    ("invalid sequence index", lambda: [1, 2][10]),
]

for description, operation in error_examples:
    try:
        operation()
    except Exception as error:
        print(f"{description}: {type(error).__name__}: {error}")


# ============================================================================
# 48. ERROR HANDLING STRATEGY
# ============================================================================

print("\n" + "=" * 78)
print("48. ERROR HANDLING STRATEGY")
print("=" * 78)


def safe_divide(dividend: float, divisor: float) -> float | None:
    """
    Divide two numbers and return None when the divisor is zero.

    A production API may instead choose to raise a domain-specific exception.
    The important point is to define the behavior deliberately.
    """
    if divisor == 0:
        return None

    return dividend / divisor


print("safe_divide(10, 2):", safe_divide(10, 2))
print("safe_divide(10, 0):", safe_divide(10, 0))


# ============================================================================
# 49. TYPE ANNOTATIONS
# ============================================================================

print("\n" + "=" * 78)
print("49. TYPE ANNOTATIONS")
print("=" * 78)


def calculate_discount(price: float, rate: float) -> float:
    """Calculate a discount amount."""
    return price * rate / 100


price: float = 1000.0
discount_rate: float = 15.0
discount: float = calculate_discount(price, discount_rate)

print("price:", price)
print("discount rate:", discount_rate)
print("discount:", discount)

# Type annotations document intended types but do not automatically enforce
# them at runtime.


# ============================================================================
# 50. DATATYPE CLASSIFICATION TABLE
# ============================================================================

print("\n" + "=" * 78)
print("50. DATA TYPE CLASSIFICATION")
print("=" * 78)

type_classification = {
    "int": ("numeric", "immutable"),
    "float": ("numeric", "immutable"),
    "complex": ("numeric", "immutable"),
    "bool": ("boolean", "immutable"),
    "str": ("sequence/text", "immutable"),
    "list": ("sequence", "mutable"),
    "tuple": ("sequence", "immutable"),
    "set": ("set", "mutable"),
    "frozenset": ("set", "immutable"),
    "dict": ("mapping", "mutable"),
    "NoneType": ("null/sentinel", "immutable"),
}

for type_name, (category, mutability) in type_classification.items():
    print(f"{type_name:12} | {category:16} | {mutability}")


# ============================================================================
# 51. FROZEN SET
# ============================================================================

print("\n" + "=" * 78)
print("51. FROZENSET")
print("=" * 78)

immutable_set = frozenset({1, 2, 3})

print("frozenset:", immutable_set)
print("contains 2:", 2 in immutable_set)
print("hash:", hash(immutable_set))


# ============================================================================
# 52. NONE AS A SENTINEL
# ============================================================================

print("\n" + "=" * 78)
print("52. NONE AS A SENTINEL")
print("=" * 78)


def find_first_even(numbers: list[int]) -> int | None:
    """Return the first even number or None when no match exists."""
    for number in numbers:
        if number % 2 == 0:
            return number

    return None


found = find_first_even([1, 3, 7, 10, 11])
missing = find_first_even([1, 3, 7, 11])

print("found:", found)
print("missing:", missing)

if missing is None:
    print("No even number was found.")


# ============================================================================
# 53. VARIABLE SCOPE
# ============================================================================

print("\n" + "=" * 78)
print("53. VARIABLE SCOPE")
print("=" * 78)

global_value = "global"


def demonstrate_scope() -> str:
    local_value = "local"
    return f"{global_value} + {local_value}"


print(demonstrate_scope())

# local_value does not exist outside the function.
try:
    print(local_value)
except NameError as error:
    print("Scope error:", error)


# ============================================================================
# 54. GLOBAL REBINDING
# ============================================================================

print("\n" + "=" * 78)
print("54. GLOBAL REBINDING")
print("=" * 78)

counter = 0


def increment_global_counter() -> int:
    global counter
    counter += 1
    return counter


print(increment_global_counter())
print(increment_global_counter())


# ============================================================================
# 55. NONLOCAL VARIABLES
# ============================================================================

print("\n" + "=" * 78)
print("55. NONLOCAL VARIABLES")
print("=" * 78)


def make_counter():
    count = 0

    def increment():
        nonlocal count
        count += 1
        return count

    return increment


counter_function = make_counter()

print(counter_function())
print(counter_function())
print(counter_function())


# ============================================================================
# 56. CONSTANT-LIKE CONFIGURATION
# ============================================================================

print("\n" + "=" * 78)
print("56. CONSTANT-LIKE CONFIGURATION")
print("=" * 78)

CONFIG = {
    "environment": "development",
    "timeout_seconds": 30,
    "debug": True,
}

print("CONFIG:", CONFIG)

# The name CONFIG signals intended immutability by convention, but Python
# does not prevent reassignment or mutation.


# ============================================================================
# 57. UNPACKING
# ============================================================================

print("\n" + "=" * 78)
print("57. UNPACKING")
print("=" * 78)

coordinates = (10, 20)
x_coordinate, y_coordinate = coordinates

print("x_coordinate:", x_coordinate)
print("y_coordinate:", y_coordinate)

first, *middle, last = [1, 2, 3, 4, 5]

print("first:", first)
print("middle:", middle)
print("last:", last)


# ============================================================================
# 58. STRUCTURED EXPRESSION
# ============================================================================

print("\n" + "=" * 78)
print("58. STRUCTURED EXPRESSIONS")
print("=" * 78)


def calculate_student_result(
    marks: list[float],
) -> tuple[float, bool]:
    """Calculate average and pass status."""
    if not marks:
        raise ValueError("At least one mark is required.")

    average = sum(marks) / len(marks)
    passed = average >= 40 and all(0 <= mark <= 100 for mark in marks)

    return average, passed


average, passed = calculate_student_result([75, 82, 68, 91])
print("average:", average)
print("passed:", passed)


# ============================================================================
# 59. PERFORMANCE CONSIDERATIONS
# ============================================================================

print("\n" + "=" * 78)
print("59. PERFORMANCE CONSIDERATIONS")
print("=" * 78)

import time

large_range = range(1_000_000)

start = time.perf_counter()
sum_result = sum(large_range)
elapsed = time.perf_counter() - start

print("sum result:", sum_result)
print(f"sum(range(1_000_000)) time: {elapsed:.6f} seconds")

# Avoid unnecessary conversions and intermediate objects when a direct
# operation is available. Performance should be measured rather than guessed.


# ============================================================================
# 60. MEMORY CONSIDERATIONS
# ============================================================================

print("\n" + "=" * 78)
print("60. MEMORY CONSIDERATIONS")
print("=" * 78)

small_integer = 42
small_string = "Python"
small_list = [1, 2, 3]

print("size of int:", sys.getsizeof(small_integer))
print("size of str:", sys.getsizeof(small_string))
print("size of list:", sys.getsizeof(small_list))

# getsizeof() reports the object's own memory footprint, not necessarily the
# complete memory used by objects referenced inside it.


# ============================================================================
# 61. SECURITY CONSIDERATIONS
# ============================================================================

print("\n" + "=" * 78)
print("61. SECURITY CONSIDERATIONS")
print("=" * 78)

# Never use eval() on untrusted user input.
#
# Unsafe conceptual pattern:
#     eval(user_input)
#
# An attacker could supply an expression that performs operations far beyond
# simple arithmetic. For arithmetic input, implement a parser or use a
# restricted, purpose-built approach instead.

print("Security rule: never evaluate untrusted input with eval().")


# ============================================================================
# 62. TESTING FUNDAMENTALS
# ============================================================================

print("\n" + "=" * 78)
print("62. TESTING FUNDAMENTALS")
print("=" * 78)


def calculate_total(price: float, quantity: int) -> float:
    """Return the total price."""
    if price < 0:
        raise ValueError("Price cannot be negative.")

    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")

    return price * quantity


# Simple executable assertions.
assert calculate_total(100, 3) == 300
assert calculate_total(0, 10) == 0
assert calculate_total(99.99, 2) == 199.98

try:
    calculate_total(-1, 2)
except ValueError:
    pass
else:
    raise AssertionError("Negative price should raise ValueError.")

print("All basic assertions passed.")


# ============================================================================
# 63. MINI PROJECT: EXPRESSION-BASED CALCULATOR
# ============================================================================

print("\n" + "=" * 78)
print("63. MINI PROJECT: EXPRESSION-BASED CALCULATOR")
print("=" * 78)


def calculator(
    first: float,
    second: float,
    operation: str,
) -> float:
    """
    Perform one validated arithmetic operation.

    Supported operations:
    +, -, *, /, //, %, **
    """
    operations = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
        "//": operator.floordiv,
        "%": operator.mod,
        "**": operator.pow,
    }

    if operation not in operations:
        raise ValueError(f"Unsupported operation: {operation!r}")

    if operation in {"/", "//", "%"} and second == 0:
        raise ZeroDivisionError("Cannot divide or take modulo by zero.")

    return operations[operation](first, second)


calculator_examples = [
    (10, 5, "+"),
    (10, 5, "-"),
    (10, 5, "*"),
    (10, 5, "/"),
    (10, 3, "//"),
    (10, 3, "%"),
    (2, 5, "**"),
]

for first, second, operation in calculator_examples:
    print(
        f"{first} {operation} {second} = "
        f"{calculator(first, second, operation)}"
    )


# ============================================================================
# 64. MINI PROJECT: SIMPLE UNIT CONVERSION
# ============================================================================

print("\n" + "=" * 78)
print("64. MINI PROJECT: SIMPLE UNIT CONVERSION")
print("=" * 78)


def kilometers_to_miles(kilometers: float) -> float:
    """Convert kilometers to miles."""
    return kilometers * 0.621371


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


print("10 km in miles:", kilometers_to_miles(10))
print("25 C in Fahrenheit:", celsius_to_fahrenheit(25))


# ============================================================================
# 65. MINI PROJECT: SIMPLE FINANCIAL EXPRESSION
# ============================================================================

print("\n" + "=" * 78)
print("65. MINI PROJECT: SIMPLE FINANCIAL EXPRESSION")
print("=" * 78)


def simple_interest(
    principal: float,
    annual_rate_percentage: float,
    years: float,
) -> float:
    """Calculate simple interest."""
    if principal < 0 or annual_rate_percentage < 0 or years < 0:
        raise ValueError("Financial inputs cannot be negative.")

    return principal * annual_rate_percentage * years / 100


principal = 100_000
annual_rate = 8
years = 3

interest = simple_interest(principal, annual_rate, years)
maturity_amount = principal + interest

print("principal:", principal)
print("interest:", interest)
print("maturity amount:", maturity_amount)


# ============================================================================
# 66. MINI PROJECT: BOOLEAN ACCESS RULE
# ============================================================================

print("\n" + "=" * 78)
print("66. MINI PROJECT: BOOLEAN ACCESS RULE")
print("=" * 78)


def can_access_dashboard(
    is_authenticated: bool,
    has_permission: bool,
    account_active: bool,
) -> bool:
    """Determine whether a user can access a dashboard."""
    return is_authenticated and has_permission and account_active


access_cases = [
    (True, True, True),
    (True, False, True),
    (True, True, False),
    (False, True, True),
]

for case in access_cases:
    print(case, "->", can_access_dashboard(*case))


# ============================================================================
# 67. MINI PROJECT: BITWISE FLAGS
# ============================================================================

print("\n" + "=" * 78)
print("67. MINI PROJECT: BITWISE FLAGS")
print("=" * 78)

FEATURE_SEARCH = 1 << 0
FEATURE_EXPORT = 1 << 1
FEATURE_ANALYTICS = 1 << 2
FEATURE_ADMIN = 1 << 3


def enable_feature(flags: int, feature: int) -> int:
    return flags | feature


def disable_feature(flags: int, feature: int) -> int:
    return flags & ~feature


def has_feature(flags: int, feature: int) -> bool:
    return bool(flags & feature)


user_features = 0
user_features = enable_feature(user_features, FEATURE_SEARCH)
user_features = enable_feature(user_features, FEATURE_ANALYTICS)

print("feature flags:", bin(user_features))
print("search enabled:", has_feature(user_features, FEATURE_SEARCH))
print("export enabled:", has_feature(user_features, FEATURE_EXPORT))

user_features = disable_feature(user_features, FEATURE_SEARCH)

print("after disabling search:", bin(user_features))
print("search enabled:", has_feature(user_features, FEATURE_SEARCH))


# ============================================================================
# 68. ADVANCED: DESCRIPTIVE VALUE OBJECT
# ============================================================================

print("\n" + "=" * 78)
print("68. ADVANCED: VALUE OBJECT")
print("=" * 78)


class Percentage:
    """Validated immutable-style percentage value."""

    def __init__(self, value: float) -> None:
        numeric_value = float(value)

        if not math.isfinite(numeric_value):
            raise ValueError("Percentage must be finite.")

        if not 0 <= numeric_value <= 100:
            raise ValueError("Percentage must be between 0 and 100.")

        self.value = numeric_value

    def __float__(self) -> float:
        return self.value

    def __repr__(self) -> str:
        return f"Percentage({self.value})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Percentage):
            return NotImplemented

        return math.isclose(self.value, other.value)


discount_percentage = Percentage(15)
print(discount_percentage)
print("as float:", float(discount_percentage))
print("equal:", discount_percentage == Percentage(15))


# ============================================================================
# 69. ADVANCED: DATACLASS FOR STRUCTURED DATA
# ============================================================================

print("\n" + "=" * 78)
print("69. ADVANCED: DATACLASS")
print("=" * 78)

from dataclasses import dataclass


@dataclass
class Product:
    """Structured product data."""

    name: str
    price: Decimal
    quantity: int = 1

    @property
    def total(self) -> Decimal:
        return self.price * self.quantity


product = Product(
    name="Keyboard",
    price=Decimal("2499.00"),
    quantity=2,
)

print("product:", product)
print("total:", product.total)


# ============================================================================
# 70. ADVANCED: ENUMERATION
# ============================================================================

print("\n" + "=" * 78)
print("70. ADVANCED: ENUMERATION")
print("=" * 78)

from enum import Enum


class Operation(Enum):
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"


def perform_operation(
    first: float,
    second: float,
    operation_type: Operation,
) -> float:
    """Perform an operation selected through an enum."""
    if operation_type is Operation.ADD:
        return first + second
    if operation_type is Operation.SUBTRACT:
        return first - second
    if operation_type is Operation.MULTIPLY:
        return first * second
    if operation_type is Operation.DIVIDE:
        if second == 0:
            raise ZeroDivisionError("Cannot divide by zero.")
        return first / second

    raise ValueError("Unsupported operation.")


print(
    "10 + 5 =",
    perform_operation(10, 5, Operation.ADD),
)
print(
    "10 / 5 =",
    perform_operation(10, 5, Operation.DIVIDE),
)


# ============================================================================
# 71. ADVANCED: STRUCTURAL PATTERN MATCHING
# ============================================================================

print("\n" + "=" * 78)
print("71. ADVANCED: STRUCTURAL PATTERN MATCHING")
print("=" * 78)


def describe_value(value: Any) -> str:
    """Classify selected values using match/case."""
    match value:
        case int() if value > 0:
            return "positive integer"
        case int():
            return "zero or negative integer"
        case float():
            return "floating-point number"
        case str():
            return "string"
        case None:
            return "None"
        case _:
            return "other"


for value in [10, -2, 3.14, "Python", None]:
    print(repr(value), "->", describe_value(value))


# ============================================================================
# 72. ADVANCED: OPERATOR PRECEDENCE WITH CUSTOM OBJECTS
# ============================================================================

print("\n" + "=" * 78)
print("72. ADVANCED: CUSTOM OPERATORS")
print("=" * 78)


class Vector2D:
    """Two-dimensional vector supporting basic arithmetic."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __add__(self, other: "Vector2D") -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented

        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented

        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        if not isinstance(scalar, (int, float)):
            return NotImplemented

        return Vector2D(self.x * scalar, self.y * scalar)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def __repr__(self) -> str:
        return f"Vector2D(x={self.x}, y={self.y})"


vector_a = Vector2D(3, 4)
vector_b = Vector2D(1, 2)

print("vector_a:", vector_a)
print("vector_b:", vector_b)
print("addition:", vector_a + vector_b)
print("subtraction:", vector_a - vector_b)
print("scalar multiplication:", vector_a * 2)
print("magnitude:", vector_a.magnitude())


# ============================================================================
# 73. ADVANCED: COMPLEX FINANCIAL EXPRESSION
# ============================================================================

print("\n" + "=" * 78)
print("73. ADVANCED: COMPOUND INTEREST")
print("=" * 78)


def compound_interest(
    principal: Decimal,
    annual_rate_percentage: Decimal,
    compounds_per_year: int,
    years: int,
) -> Decimal:
    """
    Calculate compound interest using Decimal.

    Formula:
        A = P(1 + r/n)^(nt)

    where r is expressed as a decimal.
    """
    if principal < 0:
        raise ValueError("Principal cannot be negative.")

    if annual_rate_percentage < 0:
        raise ValueError("Rate cannot be negative.")

    if compounds_per_year <= 0:
        raise ValueError("Compounding frequency must be positive.")

    if years < 0:
        raise ValueError("Years cannot be negative.")

    rate = annual_rate_percentage / Decimal("100")
    periodic_rate = rate / Decimal(compounds_per_year)

    amount = principal * (
        Decimal("1") + periodic_rate
    ) ** (compounds_per_year * years)

    return amount


compound_amount = compound_interest(
    Decimal("100000"),
    Decimal("8"),
    12,
    5,
)

print("compound amount:", compound_amount)


# ============================================================================
# 74. ADVANCED: EXPRESSION VALIDATION WITHOUT EVAL
# ============================================================================

print("\n" + "=" * 78)
print("74. ADVANCED: RESTRICTED ARITHMETIC EXPRESSION")
print("=" * 78)

# Python's ast module can inspect expressions without directly executing them.
# The example below permits only a small set of arithmetic syntax.
import ast


ALLOWED_AST_NODES = (
    ast.Expression,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.UAdd,
    ast.USub,
)


def validate_arithmetic_expression(expression: str) -> ast.Expression:
    """Validate that an expression contains only approved arithmetic nodes."""
    if not isinstance(expression, str):
        raise TypeError("Expression must be a string.")

    if len(expression) > 100:
        raise ValueError("Expression is too long.")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("Invalid expression syntax.") from error

    for node in ast.walk(tree):
        if not isinstance(node, ALLOWED_AST_NODES):
            raise ValueError(
                f"Unsupported expression element: {type(node).__name__}"
            )

        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError("Only numeric constants are allowed.")

            if isinstance(node.value, float) and not math.isfinite(node.value):
                raise ValueError("Non-finite values are not allowed.")

    return tree


safe_expression = "10 + 5 * 2"
tree = validate_arithmetic_expression(safe_expression)

print("validated expression:", safe_expression)
print("AST root:", type(tree).__name__)

for unsafe_expression in [
    "__import__('os')",
    "open('file.txt')",
    "10 + abc",
]:
    try:
        validate_arithmetic_expression(unsafe_expression)
    except (TypeError, ValueError) as error:
        print("rejected:", unsafe_expression, "->", error)


# ============================================================================
# 75. COMMON MISTAKES
# ============================================================================

print("\n" + "=" * 78)
print("75. COMMON MISTAKES")
print("=" * 78)

mistakes_and_corrections = {
    "Using = when comparison is intended": "Use == for equality.",
    "Using is for ordinary value comparison": "Use == for values and is for identity.",
    "Assuming 0.1 + 0.2 exactly equals 0.3": "Use tolerance-based comparison.",
    "Dividing by zero": "Validate the denominator.",
    "Converting invalid text to int": "Validate or catch ValueError.",
    "Concatenating strings with numbers directly": "Convert explicitly or use formatting.",
    "Using mutable objects without understanding aliases": "Understand references and copying.",
    "Using eval on untrusted input": "Use a restricted parser or explicit operations.",
    "Relying on variable names as enforced constants": "Treat uppercase names as conventions.",
    "Ignoring operator precedence": "Use parentheses for clarity.",
}

for mistake, correction in mistakes_and_corrections.items():
    print(f"{mistake} -> {correction}")


# ============================================================================
# 76. FINAL INTEGRATED EXAMPLE
# ============================================================================

print("\n" + "=" * 78)
print("76. FINAL INTEGRATED EXAMPLE")
print("=" * 78)


@dataclass
class SalesTransaction:
    """Represent a sales transaction using fundamental data types."""

    product_name: str
    unit_price: Decimal
    quantity: int
    discount_percentage: Decimal
    tax_percentage: Decimal

    def calculate_subtotal(self) -> Decimal:
        return self.unit_price * self.quantity

    def calculate_discount(self) -> Decimal:
        return (
            self.calculate_subtotal()
            * self.discount_percentage
            / Decimal("100")
        )

    def calculate_taxable_amount(self) -> Decimal:
        return self.calculate_subtotal() - self.calculate_discount()

    def calculate_tax(self) -> Decimal:
        return (
            self.calculate_taxable_amount()
            * self.tax_percentage
            / Decimal("100")
        )

    def calculate_total(self) -> Decimal:
        return self.calculate_taxable_amount() + self.calculate_tax()


transaction = SalesTransaction(
    product_name="Laptop",
    unit_price=Decimal("75000.00"),
    quantity=2,
    discount_percentage=Decimal("10"),
    tax_percentage=Decimal("18"),
)

print("product:", transaction.product_name)
print("unit price:", transaction.unit_price)
print("quantity:", transaction.quantity)
print("subtotal:", transaction.calculate_subtotal())
print("discount:", transaction.calculate_discount())
print("taxable amount:", transaction.calculate_taxable_amount())
print("tax:", transaction.calculate_tax())
print("final total:", transaction.calculate_total())


# ============================================================================
# 77. KNOWLEDGE CHECKS
# ============================================================================

print("\n" + "=" * 78)
print("77. KNOWLEDGE CHECKS")
print("=" * 78)

knowledge_checks = {
    "10 + 5 * 2": 20,
    "(10 + 5) * 2": 30,
    "17 // 5": 3,
    "17 % 5": 2,
    "2 ** 3": 8,
    "10 > 5 and 3 < 2": False,
    "bool([])": False,
    "bool([0])": True,
    "int(4.9)": 4,
    "float(10)": 10.0,
}

for expression, expected in knowledge_checks.items():
    actual = eval(expression, {"__builtins__": {}}, {})
    print(f"{expression:30} -> {actual!r:10} expected={expected!r}")

# The eval above is applied only to hard-coded developer-authored expressions
# in this study script. It must never be generalized to untrusted input.


print("\n" + "=" * 78)
print("END OF PROGRAMMING FUNDAMENTALS STUDY SCRIPT")
print("=" * 78)
