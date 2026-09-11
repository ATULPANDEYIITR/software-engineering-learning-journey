# Programming Fundamentals: Variables, Data Types, Operators, and Expressions

## Introduction

Programming fundamentals are the foundational concepts used to construct Python programs. Variables provide names for values, data types describe the kinds of values being represented, operators perform operations, and expressions combine values and operations to produce results.

This study material covers these concepts from absolute beginner level through advanced practical usage, including type conversion, mutability, object identity, truthiness, operator precedence, short-circuit evaluation, bitwise operations, numerical precision, scope, unpacking, operator overloading, validation, debugging, performance, security, and real-world implementation considerations.

## Variables

A variable is a name that refers to an object.

    age = 25
    name = "Atul"
    height = 1.75
    is_student = True

Python does not require a separate variable declaration before assignment.

A variable can later refer to an object of another type:

    value = 100
    value = "one hundred"

Python is dynamically typed. The object has a type, while the variable name can be rebound to objects of different types.

### Variable naming

Python variable names are case-sensitive.

    score = 90
    Score = 95

These are different names.

Recommended variable names use lowercase words separated by underscores:

    student_name
    total_marks
    tax_rate
    customer_count

A variable name cannot begin with a number, contain spaces, or use a Python keyword.

Constants are conventionally written in uppercase:

    MAX_CONNECTIONS = 100
    TAX_RATE = 18

Python does not enforce constants. The uppercase convention communicates programmer intent.

### Multiple assignment

Python allows multiple variables to be assigned in one statement:

    x, y, z = 10, 20, 30

The same value can be assigned to multiple names:

    first = second = third = 0

Variables can be swapped without a temporary variable:

    x, y = y, x

## Objects, references, and identity

Python variables refer to objects.

    number_a = 500
    number_b = number_a

Both names refer to the same object at that point.

The `==` operator compares values:

    number_a == number_b

The `is` operator compares object identity:

    number_a is number_b

Two separate objects can contain equal values.

    list_a = [1, 2, 3]
    list_b = [1, 2, 3]

The values are equal:

    list_a == list_b

but the objects are distinct:

    list_a is list_b

Identity checks are especially appropriate for singleton values such as `None`:

    if result is None:
        ...

Ordinary value comparisons should normally use `==`.

## Data types

Python provides many built-in data types.

| Type | Example | Category | Mutable |
|---|---|---|---|
| `int` | `42` | Integer | No |
| `float` | `3.14` | Floating point | No |
| `complex` | `3 + 4j` | Complex number | No |
| `bool` | `True` | Boolean | No |
| `str` | `"Python"` | Text | No |
| `list` | `[1, 2, 3]` | Ordered collection | Yes |
| `tuple` | `(1, 2, 3)` | Ordered collection | No |
| `set` | `{1, 2, 3}` | Unique collection | Yes |
| `frozenset` | `frozenset({1, 2})` | Immutable set | No |
| `dict` | `{"name": "Atul"}` | Mapping | Yes |
| `NoneType` | `None` | Null/sentinel value | No |

## Integers

The `int` type represents whole numbers.

    0
    1
    -1
    42
    100000000000000000000000

Python integers support arbitrary precision, subject primarily to available memory.

### Binary numbers

    0b1010

### Octal numbers

    0o12

### Hexadecimal numbers

    0xA

These three representations all represent decimal `10`.

Useful conversion functions include:

    bin(42)
    oct(42)
    hex(42)

## Floating-point numbers

The `float` type represents floating-point values.

Examples include:

    3.14159
    199.99
    0.75
    6.022e23

Scientific notation is useful for very large and very small values.

Floating-point numbers normally use binary floating-point representation. Some decimal values cannot be represented exactly.

For example:

    0.1 + 0.2

may produce:

    0.30000000000000004

Therefore, direct equality should not always be used for floating-point calculations.

An approximate comparison can use a tolerance:

    abs(a - b) < tolerance

Python's `math.isclose()` provides a more robust implementation.

## Special floating-point values

Python supports infinity and NaN.

    float("inf")
    float("-inf")
    float("nan")

The `math` module provides:

    math.isinf(value)
    math.isnan(value)
    math.isfinite(value)

NaN has special comparison behavior.

    nan == nan

is false.

## Decimal numbers

`decimal.Decimal` provides decimal arithmetic with controlled precision.

For financial calculations, constructing decimals from strings is generally preferable:

    Decimal("0.1")
    Decimal("0.2")

Then:

    Decimal("0.1") + Decimal("0.2")

produces exactly:

    Decimal("0.3")

Constructing a `Decimal` directly from a binary floating-point number can preserve the float's existing approximation.

## Fractions

`fractions.Fraction` represents rational numbers exactly.

    Fraction(1, 3)
    Fraction(1, 6)

This calculation is exact:

    Fraction(1, 3) + Fraction(1, 6)

The result is:

    1/2

Fractions are useful when exact rational arithmetic is required.

## Complex numbers

Python supports complex numbers using `j` for the imaginary component.

    complex_number = 3 + 4j

The real and imaginary components can be accessed with:

    complex_number.real
    complex_number.imag

The magnitude is obtained with:

    abs(complex_number)

The conjugate is obtained with:

    complex_number.conjugate()

Complex numbers are useful in mathematics, engineering, signal processing, and scientific computing.

## Boolean values

Python has two Boolean values:

    True
    False

Comparisons commonly produce Boolean values:

    10 > 5

produces:

    True

Python's `bool` type is a subclass of `int`.

Therefore:

    isinstance(True, int)

is true.

Boolean values can participate in arithmetic:

    True + True

produces `2`.

This behavior is valid Python, but Boolean values should normally be used according to their logical meaning.

## Strings

Strings represent text.

    "Python"
    'Programming'

Strings are immutable sequences of characters.

### Indexing

    message = "Python"

    message[0]
    message[-1]

The first expression accesses the first character and the second accesses the last character.

### Slicing

    message[1:4]
    message[::2]

Slicing creates a new string.

### Concatenation

    "Hello" + " " + "Python"

### Repetition

    "-" * 20

### Length

    len("Python")

### Membership

    "Py" in "Python"

### String formatting

F-strings provide a concise formatting mechanism:

    name = "Atul"
    age = 25

    f"{name} is {age} years old."

Explicit conversion is possible with:

    str(12345)

## Lists

Lists are ordered and mutable collections.

    numbers = [10, 20, 30]

Elements can be changed:

    numbers[0] = 5

Elements can be added:

    numbers.append(40)

Because lists are mutable, aliases can observe changes made through another reference.

## Tuples

Tuples are ordered and immutable.

    coordinates = (10, 20)

They are useful for fixed collections of related values.

Tuple unpacking is possible:

    x, y = coordinates

## Sets

Sets contain unique elements.

    numbers = {1, 2, 2, 3}

The duplicate value is represented only once.

Sets are useful for membership testing and mathematical set operations.

## Dictionaries

Dictionaries store key-value relationships.

    student = {
        "name": "Atul",
        "age": 25,
        "marks": 88
    }

Dictionary membership tests keys:

    "name" in student

It does not search dictionary values.

## Frozensets

A `frozenset` is an immutable set.

    values = frozenset({1, 2, 3})

Because it is immutable and hashable, a frozenset can be used in contexts where a mutable set cannot.

## None

`None` represents the absence of a value.

    result = None

The preferred check is:

    if result is None:
        ...

## Type conversion

Python supports explicit type conversion.

### String to integer

    int("100")

### String to float

    float("12.50")

### Integer to float

    float(25)

### Float to integer

    int(25.99)

The fractional component is discarded when converting a positive float to an integer.

### Value to string

    str(12345)

### Value to Boolean

    bool(value)

Conversion can fail.

    int("Python")

raises `ValueError`.

## Truthiness

Python evaluates objects in Boolean contexts.

Common false-like values include:

    False
    None
    0
    0.0
    0j
    ""
    []
    ()
    {}
    set()

Most non-empty objects are true-like.

An important distinction is:

    bool("False")

which is `True` because the string is non-empty.

## Arithmetic operators

Python provides several arithmetic operators.

| Operator | Meaning | Example |
|---|---|---|
| `+` | Addition | `10 + 5` |
| `-` | Subtraction | `10 - 5` |
| `*` | Multiplication | `10 * 5` |
| `/` | True division | `10 / 5` |
| `//` | Floor division | `10 // 3` |
| `%` | Modulo | `10 % 3` |
| `**` | Exponentiation | `2 ** 3` |

### Addition

    10 + 5

produces `15`.

### Subtraction

    10 - 5

produces `5`.

### Multiplication

    10 * 5

produces `50`.

### True division

    10 / 4

produces `2.5`.

### Floor division

    10 // 4

produces `2`.

Floor division rounds toward negative infinity.

Therefore:

    -7 // 3

produces `-3`.

This differs from truncating toward zero.

### Modulo

    10 % 3

produces `1`.

Python maintains the relationship:

    a == (a // b) * b + (a % b)

for valid numeric operands.

### Exponentiation

    2 ** 3

produces `8`.

## Division by zero

Division by zero raises `ZeroDivisionError`.

    10 / 0

The same principle applies to floor division and modulo.

Applications should validate denominators when zero is not an acceptable domain value.

## Comparison operators

Python provides:

| Operator | Meaning |
|---|---|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `<=` | Less than or equal |
| `>` | Greater than |
| `>=` | Greater than or equal |

Examples:

    10 == 10
    10 != 5
    10 < 20
    10 <= 10
    20 > 10
    20 >= 20

Comparison expressions normally produce Boolean results.

## Chained comparisons

Python supports chained comparisons:

    20 <= temperature <= 30

This is a concise way to test whether a value lies within a range.

The expression is not simply interpreted as ordinary arithmetic. Python evaluates the comparisons according to its comparison chaining rules.

## Logical operators

Python provides:

    and
    or
    not

### `and`

`and` evaluates operands from left to right and stops when a false-like operand is encountered.

    is_authenticated and has_permission

### `or`

`or` evaluates operands from left to right and stops when a truthy operand is found.

    username or "Guest"

### `not`

`not` reverses truthiness:

    not True

produces `False`.

## Short-circuit evaluation

Logical operators use short-circuit evaluation.

For:

    condition and expensive_operation()

the function call is skipped when `condition` is false.

For:

    condition or expensive_operation()

the function call is skipped when `condition` is true.

Short-circuit evaluation can improve efficiency and prevent unnecessary or unsafe operations.

An important detail is that `and` and `or` return operands rather than always returning `True` or `False`.

For example:

    result = "" or "default"

produces:

    "default"

## Assignment operators

The standard assignment operator is:

    =

Python also provides augmented assignment operators:

    +=
    -=
    *=
    /=
    //=
    %=
    **=
    &=
    |=
    ^=
    <<=
    >>=

Examples:

    value += 5
    value -= 3
    value *= 2
    value /= 4

Augmented assignment can have important behavior for mutable objects.

## Bitwise operators

Bitwise operators operate on integer bit patterns.

| Operator | Meaning |
|---|---|
| `&` | Bitwise AND |
| `|` | Bitwise OR |
| `^` | Bitwise XOR |
| `~` | Bitwise NOT |
| `<<` | Left shift |
| `>>` | Right shift |

Example:

    a = 0b1100
    b = 0b1010

    a & b
    a | b
    a ^ b

Bitwise operations are common in low-level programming, permissions, flags, binary protocols, embedded systems, and systems programming.

## Bit masks

Individual bits can represent independent Boolean features.

    READ = 0b001
    WRITE = 0b010
    EXECUTE = 0b100

A combined permission set can be created with:

    permissions = READ | WRITE

A permission can be tested with:

    bool(permissions & READ)

A permission can be added with:

    permissions |= EXECUTE

A permission can be removed with:

    permissions &= ~WRITE

## Membership operators

Python provides:

    in
    not in

Examples:

    "Python" in ["Python", "SQL"]
    "Java" not in ["Python", "SQL"]

For strings:

    "gram" in "programming"

For dictionaries:

    "name" in student

checks whether `"name"` is a key.

## Identity operators

Python provides:

    is
    is not

These compare object identity.

Correct:

    value is None

Ordinary value comparisons should use:

    value == expected_value

Using `is` for ordinary numeric or string equality is unreliable because object identity and value equality are different concepts.

## Operator precedence

Operator precedence determines how an expression is grouped.

For example:

    2 + 3 * 4

produces `14` because multiplication has higher precedence than addition.

Parentheses change grouping:

    (2 + 3) * 4

produces `20`.

A simplified precedence hierarchy from stronger to weaker binding is:

1. Parentheses and grouping
2. Exponentiation
3. Unary operators
4. Multiplication, division, floor division, and modulo
5. Addition and subtraction
6. Shifts
7. Bitwise AND
8. Bitwise XOR
9. Bitwise OR
10. Comparisons, membership, and identity
11. `not`
12. `and`
13. `or`
14. Conditional expressions
15. Assignment expressions

The complete Python precedence rules contain additional details, particularly around exponentiation and unary operators.

Parentheses should be used when they make the intended evaluation order clearer.

## Expressions

An expression is a piece of Python code that produces a value.

Examples include:

    10 + 20
    10 * 5 > 20
    len("Python")
    "Hello" + " Python"

Expressions can contain:

- literals
- variables
- operators
- function calls
- indexing
- attribute access
- comparisons
- conditional expressions
- comprehensions
- assignment expressions

## Literals

A literal directly represents a value in source code.

Examples include:

    42
    3.14
    "Python"
    True
    None
    [1, 2, 3]
    {"name": "Atul"}

Different literal forms create objects of different types.

## Unary operators

Unary operators operate on one operand.

Examples:

    +x
    -x
    not x
    ~x

For integers:

    ~x

has the relationship:

    ~x == -x - 1

## Conditional expressions

Python supports conditional expressions:

    result = "adult" if age >= 18 else "minor"

The expression evaluates to one of two values.

Conditional expressions are useful when the decision is simple enough to remain readable.

## Assignment expressions

The assignment expression operator is:

    :=

It assigns a value while also producing that value.

Example:

    if (length := len(data)) > 10:
        print(length)

Assignment expressions can reduce duplicated computation when the assigned value is immediately needed.

They should be avoided when they make the code harder to read.

## Type annotations

Python supports optional type annotations.

    age: int = 25
    name: str = "Atul"
    price: float = 199.99

Annotations document intended types and can support static analysis tools.

They do not normally enforce runtime type safety by themselves.

A function can also use annotations:

    def calculate_total(price: float, quantity: int) -> float:
        return price * quantity

## Dynamic typing and duck typing

Python does not require variables to have permanently fixed declared types.

A function may operate on any object supporting the required behavior.

For example, code that requires an object to support addition can often work with multiple numeric types.

This style is commonly associated with duck typing: behavior matters more than an object's declared class.

Good design should still make expected inputs and supported behavior clear.

## Mutability

Mutability determines whether an object can be changed after creation.

Immutable types include:

- `int`
- `float`
- `complex`
- `bool`
- `str`
- `tuple`
- `frozenset`

Mutable types include:

- `list`
- `dict`
- `set`

Mutability affects aliases.

    numbers = [1, 2, 3]
    alias = numbers

    alias.append(4)

Both references observe the modification because they refer to the same list.

## Shallow and deep copying

A shallow copy creates a new outer container.

    copy_of_list = original.copy()

For nested mutable structures, inner objects can remain shared.

Example:

    original = [[1, 2], [3, 4]]
    copy_of_original = original.copy()

The outer lists are different, but their inner lists can be shared.

`copy.deepcopy()` recursively copies nested objects when independent structures are required.

Deep copying should not be used automatically. It can be expensive and may copy objects whose shared identity is intentional.

## Hashability

Hashable objects can generally be used as dictionary keys and set elements.

Examples:

    42
    "Python"
    (1, 2, 3)

A list is not hashable because it is mutable.

Hashability is important for dictionaries, sets, caches, and other hash-based data structures.

## Scope

Python uses lexical name resolution and multiple namespaces.

Important scopes include:

- local scope
- enclosing function scope
- global/module scope
- built-in scope

This is commonly described through the LEGB lookup model:

- Local
- Enclosing
- Global
- Built-in

A local variable normally exists within the function where it is created.

An inner function can access variables from an enclosing function.

The `global` keyword allows a function to rebind a global variable.

The `nonlocal` keyword allows an inner function to rebind a variable from an enclosing function.

Global mutable state should be used carefully because it can make testing and reasoning about a program harder.

## Unpacking

Sequence unpacking assigns multiple values to multiple variables.

    coordinates = (10, 20)
    x, y = coordinates

Extended unpacking allows one variable to collect multiple values:

    first, *middle, last = [1, 2, 3, 4, 5]

The result is conceptually:

    first = 1
    middle = [2, 3, 4]
    last = 5

Unpacking is useful for returning multiple values from functions, processing records, and swapping variables.

## Augmented assignment and mutability

Augmented assignment can have different observable behavior depending on the object's implementation.

For an immutable object:

    x = 10
    x += 5

a new integer object is produced and `x` is rebound.

For a mutable object:

    items = [1, 2]
    items += [3]

the list can be modified in place.

This distinction matters when aliases exist.

## Numeric precision and comparison

Floating-point arithmetic requires care in scientific and financial applications.

Instead of:

    if calculated == expected:
        ...

an approximate comparison may be appropriate:

    math.isclose(calculated, expected, rel_tol=1e-9, abs_tol=0.0)

The appropriate tolerance depends on the domain and magnitude of the values.

For financial calculations, decimal arithmetic is generally more suitable when exact decimal semantics are required.

## Operator overloading

Python classes can implement special methods that define operator behavior.

Examples include:

    __add__
    __sub__
    __mul__
    __eq__
    __lt__

A custom class can therefore support expressions such as:

    vector_a + vector_b
    vector_a * 2

Operator overloading should represent meaningful domain semantics.

It should not be used merely to make unusual syntax possible.

## Comparison methods and ordering

Classes can define comparison behavior through special methods.

For example:

    __eq__
    __lt__
    __le__
    __gt__
    __ge__
    __ne__

When implementing custom value objects, equality should normally be based on the logical attributes that define the object's identity within the domain.

Ordering should only be implemented when a meaningful ordering exists.

## Type checking

Two common mechanisms are:

    type(value)
    isinstance(value, SomeType)

`type()` reports the exact runtime type.

`isinstance()` also considers inheritance.

For example:

    isinstance(True, int)

returns `True`.

`isinstance()` is often preferable when subclasses should be accepted.

## Input validation

User input should be validated before it is used in calculations.

For example, a percentage rate expected to lie between zero and one can be checked explicitly:

    if not 0 <= rate <= 1:
        raise ValueError("Rate must be between 0 and 1.")

Validation should reflect domain rules rather than merely checking Python types.

A value can have the correct type and still be invalid.

For example:

    age = -10

has type `int` but may violate the application's domain requirements.

## Exceptions related to fundamentals

Common exceptions include:

| Exception | Typical cause |
|---|---|
| `TypeError` | Operation applied to incompatible types |
| `ValueError` | Correct type but invalid value |
| `ZeroDivisionError` | Division or modulo by zero |
| `OverflowError` | Numeric operation exceeds supported range in a context where overflow is reported |
| `IndexError` | Invalid sequence index |
| `KeyError` | Missing dictionary key |
| `NameError` | Undefined variable name |

Example:

    try:
        result = numerator / denominator
    except ZeroDivisionError:
        result = None

Exceptions should be handled at a meaningful boundary rather than broadly suppressing all errors.

## Common mistakes

### Confusing `=` and `==`

Assignment:

    x = 10

Comparison:

    x == 10

These operators have completely different purposes.

### Using `is` instead of `==`

Incorrect for ordinary value comparison:

    x is 10

Preferred:

    x == 10

Use `is` for identity checks such as:

    x is None

### Assuming decimal arithmetic is exact with floats

This assumption can cause incorrect financial or numerical results.

Use appropriate numerical types and comparison strategies.

### Forgetting that strings are immutable

This does not modify the original string:

    name.upper()

The result must be stored if it is needed:

    name = name.upper()

### Confusing `/` and `//`

    7 / 2

produces `3.5`.

    7 // 2

produces `3`.

### Ignoring negative floor division

    -7 // 3

produces `-3`, not `-2`.

Floor division moves toward negative infinity.

### Assuming `bool("False")` is false

    bool("False")

is `True`.

The string is non-empty.

### Mutating a shared object accidentally

    original = [1, 2, 3]
    alias = original
    alias.append(4)

`original` is also changed.

### Relying on implicit conversion

Python does not automatically convert arbitrary incompatible types.

For example:

    "10" + 5

raises `TypeError`.

Explicit conversion is usually required:

    int("10") + 5

## Performance considerations

The choice of data type can affect performance.

Lists provide efficient indexed access and are suitable for ordered collections.

Sets and dictionaries generally provide average-case constant-time membership or key lookup because they use hash tables.

Repeated string concatenation in large loops can be inefficient. Building a sequence of strings and joining it can be more appropriate:

    parts = ["Python", "is", "useful"]
    result = " ".join(parts)

Creating unnecessary copies of large mutable structures increases memory usage.

The correct data structure should be chosen according to the required operations rather than based only on familiarity.

## Security considerations

Fundamental data types and operators become security concerns when they process untrusted input.

User-provided strings should not automatically be treated as executable Python expressions.

Avoid evaluating arbitrary input with mechanisms such as:

    eval(user_input)

unless the input is strictly controlled and the execution environment is appropriately isolated.

Input validation should enforce expected formats, ranges, and lengths.

Numeric calculations should also account for extreme values that could cause excessive resource consumption or unexpected application behavior.

## Debugging considerations

When an expression produces an unexpected result, inspect intermediate values.

Useful debugging techniques include:

    print(value)
    print(type(value))
    print(repr(value))

`repr()` is especially useful when whitespace, escape sequences, or object representations are relevant.

For numerical problems, inspect the exact values and units involved.

For collection problems, inspect:

- length
- type
- contents
- identity
- mutability
- aliases

For type-related errors, determine whether the problem is:

1. the wrong type
2. the right type with an invalid value
3. an unexpected conversion
4. an unexpected object reference
5. an incorrect operator

## Real-world applications

Variables, data types, operators, and expressions are used throughout software development.

### Financial calculations

    principal = 100000
    annual_rate = 0.08
    years = 5
    interest = principal * annual_rate * years

Financial software often requires `Decimal` rather than ordinary floating-point arithmetic when exact decimal representation is required.

### Statistics

    total = sum(values)
    count = len(values)
    mean = total / count

### Business calculations

    revenue = units_sold * price_per_unit
    cost = units_sold * cost_per_unit
    profit = revenue - cost

### Programming and systems

Bitwise operators can represent flags and permissions.

### Scientific computing

Floating-point and complex numbers are widely used for numerical models and simulations.

### Data processing

Lists, tuples, sets, and dictionaries represent structured data.

### Application validation

Comparison and logical operators enforce business rules.

    if age >= 18 and account_active:
        allow_access = True

## Practical design principles

A robust program should:

- use meaningful variable names
- choose data types based on domain requirements
- validate external input
- avoid unnecessary conversions
- use explicit parentheses when they improve clarity
- distinguish value equality from object identity
- understand mutable versus immutable objects
- use suitable numeric representations
- avoid unnecessary global state
- handle expected exceptions deliberately
- avoid unsafe evaluation of untrusted expressions
- measure performance before optimizing
- preserve domain units and assumptions in numerical calculations

## Conceptual distinctions

### Variable versus value

A variable is a name referring to an object.

A value is represented by the object itself.

### Type versus variable

The object has a runtime type. A variable name does not permanently own a single type.

### Equality versus identity

`==` compares values.

`is` compares object identity.

### Mutable versus immutable

Mutable objects can be changed after creation.

Immutable objects cannot be modified in place.

### `/` versus `//`

`/` performs true division.

`//` performs floor division.

### `and` versus `&`

`and` is logical short-circuit evaluation.

`&` is bitwise AND.

### `or` versus `|`

`or` is logical short-circuit evaluation.

`|` is bitwise OR.

### `in` versus `is`

`in` tests membership.

`is` tests identity.

### `int()` versus rounding

`int()` converts by truncating toward zero for floating-point input.

It is not equivalent to mathematical rounding.

## Advanced numerical example

A robust financial calculation may combine validation, decimal arithmetic, and explicit rounding.

    from decimal import Decimal, ROUND_HALF_UP

    principal = Decimal("100000.00")
    annual_rate = Decimal("0.08")
    years = Decimal("5")

    if principal < 0:
        raise ValueError("Principal cannot be negative.")

    if annual_rate < 0:
        raise ValueError("Interest rate cannot be negative.")

    interest = principal * annual_rate * years
    total = principal + interest

    rounded_total = total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

The example demonstrates several fundamental principles:

- variables hold references to values
- `Decimal` is suitable for controlled decimal arithmetic
- validation checks domain constraints
- arithmetic operators form expressions
- explicit rounding defines the required financial precision

## Advanced expression example

Expressions can combine multiple operators:

    total_cost = (
        quantity
        * unit_price
        * (1 - discount_rate)
        * (1 + tax_rate)
    )

Parentheses make the intended order easier to understand.

The expression can be decomposed when readability or debugging requires it:

    discounted_price = unit_price * (1 - discount_rate)
    subtotal = quantity * discounted_price
    total_cost = subtotal * (1 + tax_rate)

The second form can make intermediate values easier to inspect and test.

## Testing fundamental behavior

Small tests help verify assumptions.

Examples:

    assert 2 + 3 == 5
    assert 10 // 3 == 3
    assert 10 % 3 == 1
    assert 2 ** 3 == 8
    assert "Py" in "Python"
    assert bool([]) is False
    assert bool([1]) is True

Floating-point behavior should be tested with an appropriate tolerance rather than assuming exact equality.

## A compact mental model

When reading a Python expression, ask:

1. What objects are involved?
2. What are their types?
3. Are any objects mutable?
4. What does each operator mean for these types?
5. What is the operator precedence?
6. Does short-circuit evaluation apply?
7. Is the expression comparing values or identities?
8. Can conversion fail?
9. Can the operation raise an exception?
10. Is numerical precision important?
11. Does the operation modify an existing object?
12. Are any inputs untrusted?
13. Does the chosen data type match the real-world domain?

These questions provide a practical framework for understanding both simple statements and complex Python expressions.
