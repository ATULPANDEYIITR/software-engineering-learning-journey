"""
DATA STRUCTURES IN PYTHON
=========================

Topic:
    Arrays, Lists, Stacks, and Queues

Purpose:
    A self-contained study and practice script that progresses from absolute
    beginner concepts to advanced implementation details, algorithms,
    complexity analysis, edge cases, testing, and practical applications.

Requirements:
    Python 3.9+ recommended.

The script uses only Python's standard library.
"""

from __future__ import annotations

from array import array
from collections import deque
from dataclasses import dataclass
from typing import Deque, Generic, Iterable, Iterator, Optional, TypeVar
import random
import time


# =============================================================================
# 1. INTRODUCTION TO DATA STRUCTURES
# =============================================================================

print("=" * 80)
print("DATA STRUCTURES: ARRAYS, LISTS, STACKS, AND QUEUES")
print("=" * 80)

print(
    """
A data structure is a way of organizing and storing data so that operations
such as access, insertion, deletion, searching, and traversal can be performed
efficiently.

This script studies four closely related structures:

1. Arrays
2. Python lists
3. Stacks
4. Queues

The choice of a data structure affects:
- How data is stored
- How quickly elements can be accessed
- How efficiently elements can be inserted or removed
- Memory usage
- Which algorithms can be implemented naturally
- The correctness of a solution

A useful distinction is:

    Abstract data type (ADT)
        Describes behavior and supported operations.

    Data structure
        Describes how the behavior is implemented.

For example, a stack is an ADT based on LIFO behavior. A Python list can
implement a stack, while a linked list can also implement a stack.
"""
)


# =============================================================================
# 2. BASIC TERMINOLOGY
# =============================================================================

print("\n" + "=" * 80)
print("2. BASIC TERMINOLOGY")
print("=" * 80)

print(
    """
Important terms:

Element:
    One individual item stored in a data structure.

Index:
    A numeric position used to access an element in an indexed structure.

Length:
    Number of elements currently stored.

Capacity:
    Amount of storage currently allocated by a resizable structure.

Traversal:
    Visiting elements systematically.

Access:
    Retrieving an element.

Insertion:
    Adding an element.

Deletion:
    Removing an element.

Search:
    Finding an element or determining whether it exists.

Update:
    Replacing the value stored at a position.

Overflow:
    An insertion cannot be performed because a bounded structure is full.

Underflow:
    A removal or access operation is attempted on an empty structure.

FIFO:
    First In, First Out. The first inserted element is removed first.

LIFO:
    Last In, First Out. The last inserted element is removed first.

Time complexity:
    Describes how execution time grows with input size.

Space complexity:
    Describes how additional memory requirements grow with input size.

Common Big-O complexities:
    O(1)       constant
    O(log n)   logarithmic
    O(n)       linear
    O(n log n) linearithmic
    O(n^2)     quadratic
"""
)


# =============================================================================
# 3. WHAT IS AN ARRAY?
# =============================================================================

print("\n" + "=" * 80)
print("3. ARRAYS")
print("=" * 80)

print(
    """
An array is a collection of elements stored in an ordered sequence.

A traditional fixed-size array generally has:
- A fixed capacity
- Indexed access
- Contiguous memory allocation
- Elements of the same data type

Conceptually:

    index:     0    1    2    3
               |    |    |    |
    value:    10   20   30   40

The index identifies the position of an element.

In many low-level languages, an array such as:

    int values[4];

reserves space for four integers.

Python's built-in list is not the same thing as a traditional fixed-size
typed array. Python lists are dynamic arrays of references.

Python also provides the standard-library `array` module for typed arrays.
"""
)

# Traditional conceptual array represented with a Python list.
conceptual_array = [10, 20, 30, 40]

print("Conceptual array:", conceptual_array)
print("First element:", conceptual_array[0])
print("Last element:", conceptual_array[-1])
print("Length:", len(conceptual_array))


# =============================================================================
# 4. INDEXING
# =============================================================================

print("\n" + "=" * 80)
print("4. ARRAY INDEXING")
print("=" * 80)

numbers = [10, 20, 30, 40, 50]

print("numbers =", numbers)
print("numbers[0] =", numbers[0])
print("numbers[2] =", numbers[2])
print("numbers[-1] =", numbers[-1])
print("numbers[-2] =", numbers[-2])

print(
    """
Python uses zero-based indexing.

For a sequence of length n:
    First index = 0
    Last index  = n - 1

Negative indexing counts backward:
    -1 = last element
    -2 = second-last element

Trying to access an index outside the valid range raises IndexError.
"""
)

try:
    print(numbers[100])
except IndexError as error:
    print("Handled invalid index:", error)


# =============================================================================
# 5. SLICING
# =============================================================================

print("\n" + "=" * 80)
print("5. SLICING")
print("=" * 80)

numbers = [10, 20, 30, 40, 50, 60]

print("numbers:", numbers)
print("numbers[1:4]:", numbers[1:4])
print("numbers[:3]:", numbers[:3])
print("numbers[3:]:", numbers[3:])
print("numbers[::2]:", numbers[::2])
print("numbers[::-1]:", numbers[::-1])

print(
    """
The general slicing form is:

    sequence[start:stop:step]

The stop position is excluded.

Examples:
    [1:4]  -> positions 1, 2, 3
    [:3]   -> first three elements
    [3:]   -> from index 3 to the end
    [::2]  -> every second element
    [::-1] -> reversed sequence

Slicing normally creates a new list rather than returning a view.
"""
)


# =============================================================================
# 6. PYTHON'S ARRAY MODULE
# =============================================================================

print("\n" + "=" * 80)
print("6. TYPED ARRAYS WITH THE ARRAY MODULE")
print("=" * 80)

typed_numbers = array("i", [10, 20, 30, 40])

print("Typed array:", typed_numbers)
print("First element:", typed_numbers[0])
print("Type code:", typed_numbers.typecode)
print("Length:", len(typed_numbers))

typed_numbers.append(50)
typed_numbers.extend([60, 70])
print("After append and extend:", typed_numbers)

typed_numbers.insert(1, 15)
print("After insertion:", typed_numbers)

typed_numbers.pop()
print("After pop:", typed_numbers)

print(
    """
The `array` module stores values using a specified machine-level type.

Examples of type codes include:
    'i' -> signed integer
    'f' -> floating-point value
    'd' -> double-precision floating-point value

Unlike a Python list, an array from the `array` module is intended for
homogeneous typed values.

Example:

    array("i", [1, 2, 3])

Attempting to insert an incompatible type raises an error.
"""
)

try:
    typed_numbers.append(3.14)
except TypeError as error:
    print("Handled incompatible array value:", error)


# =============================================================================
# 7. PYTHON LISTS
# =============================================================================

print("\n" + "=" * 80)
print("7. PYTHON LISTS")
print("=" * 80)

print(
    """
A Python list is an ordered, mutable sequence.

Important characteristics:
- Ordered
- Mutable
- Dynamically resizable
- Supports indexing
- Supports slicing
- Allows duplicate values
- Can contain objects of different types

Example:
"""
)

mixed_list = [10, "Python", 3.14, True, [1, 2, 3]]
print("mixed_list:", mixed_list)

print(
    """
Although mixed types are permitted, using one logical type consistently is
often clearer and easier to maintain.

A Python list behaves conceptually like a dynamic array.
"""


# =============================================================================
# 8. LIST CREATION
# =============================================================================

print("\n" + "=" * 80)
print("8. CREATING LISTS")
print("=" * 80)

empty_list = []
numbers = [1, 2, 3, 4, 5]
zeros = [0] * 5
range_list = list(range(1, 6))
generator_list = list(x * x for x in range(1, 6))

print("empty_list:", empty_list)
print("numbers:", numbers)
print("zeros:", zeros)
print("range_list:", range_list)
print("generator_list:", generator_list)


# =============================================================================
# 9. LIST MUTATION OPERATIONS
# =============================================================================

print("\n" + "=" * 80)
print("9. LIST MUTATION OPERATIONS")
print("=" * 80)

values = [10, 20, 30]

values.append(40)
print("append(40):", values)

values.extend([50, 60])
print("extend([50, 60]):", values)

values.insert(1, 15)
print("insert(1, 15):", values)

values[0] = 5
print("values[0] = 5:", values)

removed = values.pop()
print("pop(): removed", removed, "remaining:", values)

removed = values.pop(1)
print("pop(1): removed", removed, "remaining:", values)

values.remove(30)
print("remove(30):", values)

print(
    """
Important distinction:

append(x):
    Adds one object as one element.

extend(iterable):
    Adds each element from the iterable.

insert(index, value):
    Inserts at a position and shifts later elements.

pop():
    Removes and returns the last element by default.

pop(index):
    Removes and returns the element at the index.

remove(value):
    Removes the first matching value.
"""
)


# =============================================================================
# 10. APPEND VS EXTEND
# =============================================================================

print("\n" + "=" * 80)
print("10. APPEND VS EXTEND")
print("=" * 80)

a = [1, 2]
a.append([3, 4])

b = [1, 2]
b.extend([3, 4])

print("append result:", a)
print("extend result:", b)

print(
    """
append([3, 4]) treats [3, 4] as one element.

extend([3, 4]) adds 3 and 4 separately.

This distinction is a common source of mistakes.
"""
)


# =============================================================================
# 11. SEARCHING LISTS
# =============================================================================

print("\n" + "=" * 80)
print("11. SEARCHING LISTS")
print("=" * 80)

values = [10, 20, 30, 20, 40]

print("values:", values)
print("20 in values:", 20 in values)
print("99 in values:", 99 in values)
print("index of first 20:", values.index(20))
print("count of 20:", values.count(20))

try:
    print(values.index(99))
except ValueError as error:
    print("Handled missing value:", error)


# =============================================================================
# 12. LIST SORTING
# =============================================================================

print("\n" + "=" * 80)
print("12. LIST SORTING")
print("=" * 80)

values = [5, 2, 9, 1, 7]

sorted_copy = sorted(values)
print("Original:", values)
print("sorted(values):", sorted_copy)

values.sort()
print("After values.sort():", values)

values.sort(reverse=True)
print("Descending:", values)

words = ["banana", "Apple", "cherry"]
print("Case-sensitive sort:", sorted(words))
print("Case-insensitive sort:", sorted(words, key=str.lower))

print(
    """
sorted(iterable):
    Returns a new sorted list.

list.sort():
    Sorts the existing list in place and returns None.

Both use Python's highly optimized Timsort implementation.

Sorting generally has O(n log n) time complexity.
"""


# =============================================================================
# 13. LIST COMPREHENSIONS
# =============================================================================

print("\n" + "=" * 80)
print("13. LIST COMPREHENSIONS")
print("=" * 80)

squares = [number * number for number in range(10)]
even_squares = [number * number for number in range(10) if number % 2 == 0]

print("squares:", squares)
print("even_squares:", even_squares)

print(
    """
A list comprehension has the general structure:

    [expression for item in iterable if condition]

It is useful when the transformation is simple and readable.

Avoid excessively complicated comprehensions. A normal loop is often clearer
when multiple conditions or side effects are involved.
"""
)


# =============================================================================
# 14. NESTED LISTS
# =============================================================================

print("\n" + "=" * 80)
print("14. NESTED LISTS")
print("=" * 80)

matrix = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
]

print("matrix:", matrix)
print("matrix[0][0]:", matrix[0][0])
print("matrix[1][2]:", matrix[1][2])

print("Rows:")
for row in matrix:
    print(row)

print("Matrix elements:")
for row in matrix:
    for value in row:
        print(value, end=" ")
print()

print(
    """
A nested list can represent a matrix, table, grid, graph adjacency structure,
or hierarchical data.

Each inner list is a separate object.
"""
)


# =============================================================================
# 15. ALIASING VS COPYING
# =============================================================================

print("\n" + "=" * 80)
print("15. ALIASING VS COPYING")
print("=" * 80)

original = [1, 2, 3]
alias = original
shallow_copy = original.copy()

alias.append(4)
shallow_copy.append(5)

print("original:", original)
print("alias:", alias)
print("shallow_copy:", shallow_copy)

print(
    """
Assignment does not copy a list.

    alias = original

means both names refer to the same list.

Use:

    original.copy()
    list(original)
    original[:]

for a shallow copy.

A shallow copy is enough for a flat list of immutable values.

For nested mutable structures, a shallow copy does not recursively copy
inner objects.
"""
)

nested_original = [[1, 2], [3, 4]]
nested_copy = nested_original.copy()

nested_copy[0].append(99)

print("Nested original after shallow-copy mutation:", nested_original)
print("Nested copy:", nested_copy)


# =============================================================================
# 16. DEEP COPY
# =============================================================================

print("\n" + "=" * 80)
print("16. DEEP COPYING")
print("=" * 80)

import copy

nested_original = [[1, 2], [3, 4]]
deep_copy = copy.deepcopy(nested_original)

deep_copy[0].append(100)

print("Original:", nested_original)
print("Deep copy:", deep_copy)

print(
    """
`copy.deepcopy()` recursively copies nested objects.

Deep copying can be expensive for large or complex object graphs, so it
should be used deliberately rather than automatically.
"""
)


# =============================================================================
# 17. COMMON LIST EDGE CASES
# =============================================================================

print("\n" + "=" * 80)
print("17. LIST EDGE CASES")
print("=" * 80)

empty = []

print("Empty list:", empty)
print("Boolean value of empty list:", bool(empty))
print("Length:", len(empty))

try:
    empty.pop()
except IndexError as error:
    print("pop() on empty list:", error)

try:
    empty.remove(10)
except ValueError as error:
    print("remove() on empty list:", error)

print(
    """
Important empty-list behavior:

    bool([]) -> False
    len([])  -> 0
    [] + [1] -> [1]
    [] * 3   -> []

Accessing an invalid index raises IndexError.

Removing a value that does not exist raises ValueError.
"""
)


# =============================================================================
# 18. DYNAMIC ARRAY CONCEPT
# =============================================================================

print("\n" + "=" * 80)
print("18. HOW DYNAMIC LISTS GROW")
print("=" * 80)

print(
    """
A dynamic array starts with allocated storage and grows when more elements
must be stored.

Appending an element is usually O(1) amortized.

Why "amortized"?

Most append operations are inexpensive, but occasionally the underlying
storage must be resized and elements/references must be copied to a larger
memory region.

Thus:
    Individual worst-case append -> O(n)
    Amortized append             -> O(1)

This distinction is important when analyzing dynamic arrays.
"""
)

dynamic = []

for value in range(8):
    dynamic.append(value)
    print(f"After append({value}): length={len(dynamic)}, size={dynamic.__sizeof__()} bytes")


# =============================================================================
# 19. LIST COMPLEXITY
# =============================================================================

print("\n" + "=" * 80)
print("19. LIST TIME COMPLEXITY")
print("=" * 80)

print(
    """
Typical Python list complexities:

Operation                         Average complexity
----------------------------------------------------
Index access list[i]              O(1)
Index assignment                 O(1)
Append                            O(1) amortized
Pop from end                      O(1)
Insert at beginning              O(n)
Insert in middle                 O(n)
Delete from beginning            O(n)
Delete from middle               O(n)
Search by value                  O(n)
Remove by value                  O(n)
Count                            O(n)
Sort                              O(n log n)
Reverse in place                 O(n)
Copy                              O(n)

The O(n) cost for insertion/deletion away from the end comes primarily from
shifting elements.
"""
)


# =============================================================================
# 20. STACK ADT
# =============================================================================

print("\n" + "=" * 80)
print("20. STACKS")
print("=" * 80)

print(
    """
A stack is an abstract data type that follows LIFO:

    Last In, First Out

Imagine a stack of plates. The last plate placed on top is the first one
removed.

Core stack operations:

    push(x)
        Add an element.

    pop()
        Remove and return the top element.

    peek()
        Inspect the top element without removing it.

    is_empty()
        Determine whether the stack contains no elements.

A stack can be implemented using a Python list.
"""
)


# =============================================================================
# 21. STACK USING LIST
# =============================================================================

print("\n" + "=" * 80)
print("21. STACK IMPLEMENTATION USING A LIST")
print("=" * 80)

stack: list[int] = []

stack.append(10)
stack.append(20)
stack.append(30)

print("Stack:", stack)
print("Top:", stack[-1])

while stack:
    print("Popped:", stack.pop())

print("Stack after removals:", stack)


# =============================================================================
# 22. SAFE STACK IMPLEMENTATION
# =============================================================================

print("\n" + "=" * 80)
print("22. ROBUST STACK CLASS")
print("=" * 80)

T = TypeVar("T")


class Stack(Generic[T]):
    """
    A generic LIFO stack implemented with a Python list.

    List append() and pop() at the end are amortized O(1).
    """

    def __init__(self, values: Optional[Iterable[T]] = None) -> None:
        self._items: list[T] = list(values) if values is not None else []

    def push(self, value: T) -> None:
        """Add a value to the top of the stack."""
        self._items.append(value)

    def pop(self) -> T:
        """Remove and return the top value."""
        if self.is_empty():
            raise IndexError("Cannot pop from an empty stack.")
        return self._items.pop()

    def peek(self) -> T:
        """Return the top value without removing it."""
        if self.is_empty():
            raise IndexError("Cannot peek at an empty stack.")
        return self._items[-1]

    def is_empty(self) -> bool:
        """Return True when the stack has no elements."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of stored elements."""
        return len(self._items)

    def clear(self) -> None:
        """Remove every element."""
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return not self.is_empty()

    def __repr__(self) -> str:
        return f"Stack({self._items!r})"


stack = Stack[int]()

stack.push(100)
stack.push(200)
stack.push(300)

print("Stack:", stack)
print("Peek:", stack.peek())
print("Size:", stack.size())
print("Pop:", stack.pop())
print("Stack:", stack)

stack.clear()
print("After clear:", stack)


# =============================================================================
# 23. STACK UNDERFLOW
# =============================================================================

print("\n" + "=" * 80)
print("23. STACK UNDERFLOW")
print("=" * 80)

empty_stack = Stack[int]()

try:
    empty_stack.pop()
except IndexError as error:
    print("Handled stack underflow:", error)

try:
    empty_stack.peek()
except IndexError as error:
    print("Handled empty-stack peek:", error)


# =============================================================================
# 24. STACK APPLICATION: REVERSE DATA
# =============================================================================

print("\n" + "=" * 80)
print("24. STACK APPLICATION: REVERSING DATA")
print("=" * 80)


def reverse_with_stack(items: Iterable[T]) -> list[T]:
    """Reverse an iterable using explicit LIFO behavior."""
    stack = Stack[T](items)
    reversed_items: list[T] = []

    while stack:
        reversed_items.append(stack.pop())

    return reversed_items


print(reverse_with_stack([1, 2, 3, 4, 5]))
print(reverse_with_stack(["A", "B", "C"]))


# =============================================================================
# 25. STACK APPLICATION: BALANCED PARENTHESES
# =============================================================================

print("\n" + "=" * 80)
print("25. STACK APPLICATION: BALANCED PARENTHESES")
print("=" * 80)


def are_parentheses_balanced(expression: str) -> bool:
    """
    Determine whether (), [], and {} are correctly balanced and nested.

    Time: O(n)
    Space: O(n) in the worst case.
    """
    matching = {
        ")": "(",
        "]": "[",
        "}": "{",
    }

    stack: Stack[str] = Stack()

    for character in expression:
        if character in "([{":
            stack.push(character)
        elif character in ")]}":
            if stack.is_empty():
                return False

            if stack.pop() != matching[character]:
                return False

    return stack.is_empty()


expressions = [
    "(a + b)",
    "[1, 2, {3: 4}]",
    "([{}])",
    "([)]",
    "(((",
    "())",
]

for expression in expressions:
    print(expression, "->", are_parentheses_balanced(expression))


# =============================================================================
# 26. STACK APPLICATION: INFIX TO POSTFIX
# =============================================================================

print("\n" + "=" * 80)
print("26. STACK APPLICATION: INFIX TO POSTFIX")
print("=" * 80)

print(
    """
Infix notation:
    A + B * C

Postfix notation:
    A B C * +

Stacks are useful for handling operator precedence.

The implementation below supports:
    + - * / ^
    parentheses
    single-character operands

It is an educational implementation rather than a complete mathematical
expression parser.
"""
)


def infix_to_postfix(expression: str) -> str:
    """Convert a simple infix expression to postfix notation."""
    precedence = {
        "+": 1,
        "-": 1,
        "*": 2,
        "/": 2,
        "^": 3,
    }

    output: list[str] = []
    operators: Stack[str] = Stack()

    for token in expression.replace(" ", ""):
        if token.isalnum():
            output.append(token)

        elif token == "(":
            operators.push(token)

        elif token == ")":
            while not operators.is_empty() and operators.peek() != "(":
                output.append(operators.pop())

            if operators.is_empty():
                raise ValueError("Mismatched parentheses.")

            operators.pop()

        elif token in precedence:
            while (
                not operators.is_empty()
                and operators.peek() != "("
                and precedence[operators.peek()] >= precedence[token]
            ):
                output.append(operators.pop())

            operators.push(token)

        else:
            raise ValueError(f"Unsupported token: {token}")

    while not operators.is_empty():
        operator = operators.pop()

        if operator == "(":
            raise ValueError("Mismatched parentheses.")

        output.append(operator)

    return " ".join(output)


for expression in ["A+B*C", "(A+B)*C", "A+B*C-D", "A*(B+C)"]:
    print(expression, "->", infix_to_postfix(expression))


# =============================================================================
# 27. EVALUATING POSTFIX EXPRESSIONS
# =============================================================================

print("\n" + "=" * 80)
print("27. EVALUATING POSTFIX EXPRESSIONS")
print("=" * 80)


def evaluate_postfix(expression: str) -> float:
    """
    Evaluate a postfix expression containing numeric operands.

    Example:
        "2 3 * 4 +" -> 10
    """
    stack: Stack[float] = Stack()

    for token in expression.split():
        if token.replace(".", "", 1).isdigit():
            stack.push(float(token))
            continue

        if token in {"+", "-", "*", "/"}:
            if len(stack) < 2:
                raise ValueError("Invalid postfix expression.")

            right = stack.pop()
            left = stack.pop()

            if token == "+":
                result = left + right
            elif token == "-":
                result = left - right
            elif token == "*":
                result = left * right
            else:
                if right == 0:
                    raise ZeroDivisionError("Division by zero.")
                result = left / right

            stack.push(result)
        else:
            raise ValueError(f"Unsupported token: {token}")

    if len(stack) != 1:
        raise ValueError("Invalid postfix expression.")

    return stack.pop()


for postfix in ["2 3 * 4 +", "10 2 / 3 +", "5 1 2 + 4 * + 3 -"]:
    print(postfix, "->", evaluate_postfix(postfix))


# =============================================================================
# 28. STACK APPLICATION: UNDO/REDO
# =============================================================================

print("\n" + "=" * 80)
print("28. STACK APPLICATION: UNDO/REDO")
print("=" * 80)

print(
    """
Undo/redo systems commonly use two stacks:

    undo_stack
    redo_stack

When a new action occurs:
    1. Store it on the undo stack.
    2. Clear the redo stack.

Undo:
    1. Move the latest action from undo to redo.

Redo:
    1. Move the latest undone action from redo to undo.

This naturally follows LIFO behavior.
"""
)


@dataclass
class EditAction:
    old_text: str
    new_text: str


class TextEditorHistory:
    """Minimal two-stack undo/redo model."""

    def __init__(self, initial_text: str = "") -> None:
        self.text = initial_text
        self.undo_stack: Stack[EditAction] = Stack()
        self.redo_stack: Stack[EditAction] = Stack()

    def edit(self, new_text: str) -> None:
        action = EditAction(self.text, new_text)
        self.undo_stack.push(action)
        self.text = new_text
        self.redo_stack.clear()

    def undo(self) -> None:
        if self.undo_stack.is_empty():
            return

        action = self.undo_stack.pop()
        self.redo_stack.push(action)
        self.text = action.old_text

    def redo(self) -> None:
        if self.redo_stack.is_empty():
            return

        action = self.redo_stack.pop()
        self.undo_stack.push(action)
        self.text = action.new_text


editor = TextEditorHistory("Hello")
editor.edit("Hello world")
editor.edit("Hello world!")
print("Current:", editor.text)

editor.undo()
print("After undo:", editor.text)

editor.undo()
print("After second undo:", editor.text)

editor.redo()
print("After redo:", editor.text)

editor.edit("New content")
print("After new edit:", editor.text)


# =============================================================================
# 29. QUEUE ADT
# =============================================================================

print("\n" + "=" * 80)
print("29. QUEUES")
print("=" * 80)

print(
    """
A queue is an abstract data type that follows FIFO:

    First In, First Out

Imagine people standing in a line.

Core operations:

    enqueue(x)
        Add an item to the rear.

    dequeue()
        Remove and return the item at the front.

    front() / peek()
        Inspect the front item.

    is_empty()
        Check whether the queue is empty.

Typical applications:
- Print jobs
- Customer service systems
- Task scheduling
- Breadth-first search
- Network request processing
- Message processing
"""
)


# =============================================================================
# 30. WHY list.pop(0) IS A POOR GENERAL QUEUE IMPLEMENTATION
# =============================================================================

print("\n" + "=" * 80)
print("30. LIST AS A QUEUE: IMPORTANT PERFORMANCE ISSUE")
print("=" * 80)

queue_as_list = ["A", "B", "C", "D"]
print("Initial list queue:", queue_as_list)

first = queue_as_list.pop(0)
print("Removed:", first)
print("Remaining:", queue_as_list)

print(
    """
A list can represent a queue, but removing from index 0 is O(n) because the
remaining elements must shift toward the beginning.

For high-performance FIFO operations, collections.deque is generally a better
choice.

Use:

    append()   for enqueue
    popleft()  for dequeue
"""
)


# =============================================================================
# 31. DEQUE
# =============================================================================

print("\n" + "=" * 80)
print("31. COLLECTIONS.DEQUE")
print("=" * 80)

queue: Deque[str] = deque()

queue.append("Alice")
queue.append("Bob")
queue.append("Charlie")

print("Queue:", queue)
print("Front:", queue[0])

print("Dequeued:", queue.popleft())
print("Queue:", queue)

queue.appendleft("Zara")
print("After appendleft:", queue)

queue.pop()
print("After pop from right:", queue)

print(
    """
deque means double-ended queue.

It supports efficient insertion and removal from both ends:

    append(x)       -> right end
    appendleft(x)   -> left end
    pop()           -> right end
    popleft()       -> left end

These operations are designed for efficient endpoint manipulation.
"""
)


# =============================================================================
# 32. ROBUST QUEUE CLASS
# =============================================================================

print("\n" + "=" * 80)
print("32. ROBUST QUEUE CLASS")
print("=" * 80)


class Queue(Generic[T]):
    """
    FIFO queue implemented with collections.deque.

    Enqueue and dequeue operations at the ends are O(1).
    """

    def __init__(self, values: Optional[Iterable[T]] = None) -> None:
        self._items: Deque[T] = deque(values if values is not None else [])

    def enqueue(self, value: T) -> None:
        """Add an item to the rear."""
        self._items.append(value)

    def dequeue(self) -> T:
        """Remove and return the front item."""
        if self.is_empty():
            raise IndexError("Cannot dequeue from an empty queue.")
        return self._items.popleft()

    def front(self) -> T:
        """Return the front item without removing it."""
        if self.is_empty():
            raise IndexError("Cannot inspect an empty queue.")
        return self._items[0]

    def rear(self) -> T:
        """Return the rear item without removing it."""
        if self.is_empty():
            raise IndexError("Cannot inspect an empty queue.")
        return self._items[-1]

    def is_empty(self) -> bool:
        return not self._items

    def size(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return not self.is_empty()

    def __repr__(self) -> str:
        return f"Queue({list(self._items)!r})"


queue = Queue[int]()

queue.enqueue(10)
queue.enqueue(20)
queue.enqueue(30)

print("Queue:", queue)
print("Front:", queue.front())
print("Rear:", queue.rear())
print("Dequeue:", queue.dequeue())
print("Queue:", queue)


# =============================================================================
# 33. QUEUE UNDERFLOW
# =============================================================================

print("\n" + "=" * 80)
print("33. QUEUE UNDERFLOW")
print("=" * 80)

empty_queue = Queue[int]()

try:
    empty_queue.dequeue()
except IndexError as error:
    print("Handled queue underflow:", error)

try:
    empty_queue.front()
except IndexError as error:
    print("Handled empty-queue peek:", error)


# =============================================================================
# 34. BOUNDED QUEUE
# =============================================================================

print("\n" + "=" * 80)
print("34. BOUNDED QUEUE")
print("=" * 80)

print(
    """
A bounded queue has a maximum capacity.

When full, a policy must be defined:
- Reject the new item
- Raise an exception
- Remove the oldest item
- Block until space is available

The following implementation raises an OverflowError.
"""


class BoundedQueue(Generic[T]):
    """FIFO queue with an explicit maximum capacity."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive.")

        self.capacity = capacity
        self._items: Deque[T] = deque()

    def enqueue(self, value: T) -> None:
        if len(self._items) >= self.capacity:
            raise OverflowError("Queue is full.")
        self._items.append(value)

    def dequeue(self) -> T:
        if not self._items:
            raise IndexError("Queue is empty.")
        return self._items.popleft()

    def __len__(self) -> int:
        return len(self._items)


bounded = BoundedQueue[int](3)

for value in [10, 20, 30]:
    bounded.enqueue(value)

print("Bounded queue size:", len(bounded))

try:
    bounded.enqueue(40)
except OverflowError as error:
    print("Handled overflow:", error)


# =============================================================================
# 35. CIRCULAR QUEUE
# =============================================================================

print("\n" + "=" * 80)
print("35. CIRCULAR QUEUE")
print("=" * 80)

print(
    """
A circular queue treats the end of a fixed-size storage area as connected
to its beginning.

It is useful when:
- Capacity is fixed
- Memory should be reused
- Data arrives continuously
- A ring-buffer design is appropriate

The indices wrap around using modulo arithmetic.

For capacity N:

    next_index = (current_index + 1) % N
"""
)


class CircularQueue(Generic[T]):
    """
    Fixed-capacity circular queue implemented with a Python list.

    enqueue: O(1)
    dequeue: O(1)
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("Capacity must be positive.")

        self._data: list[Optional[T]] = [None] * capacity
        self._capacity = capacity
        self._front = 0
        self._rear = 0
        self._size = 0

    def enqueue(self, value: T) -> None:
        if self.is_full():
            raise OverflowError("Circular queue is full.")

        self._data[self._rear] = value
        self._rear = (self._rear + 1) % self._capacity
        self._size += 1

    def dequeue(self) -> T:
        if self.is_empty():
            raise IndexError("Circular queue is empty.")

        value = self._data[self._front]
        self._data[self._front] = None
        self._front = (self._front + 1) % self._capacity
        self._size -= 1

        # The check is logically guaranteed by the invariant, but it keeps
        # static type checkers aware that a real value is returned.
        if value is None:
            raise RuntimeError("Unexpected empty slot in circular queue.")

        return value

    def is_empty(self) -> bool:
        return self._size == 0

    def is_full(self) -> bool:
        return self._size == self._capacity

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        items: list[T] = []
        for offset in range(self._size):
            index = (self._front + offset) % self._capacity
            value = self._data[index]
            if value is not None:
                items.append(value)
        return f"CircularQueue({items!r})"


circular = CircularQueue[int](3)
circular.enqueue(1)
circular.enqueue(2)
circular.enqueue(3)

print(circular)

print("Dequeue:", circular.dequeue())
print("Dequeue:", circular.dequeue())

circular.enqueue(4)
circular.enqueue(5)

print("After wrap-around:", circular)


# =============================================================================
# 36. PRIORITY QUEUE
# =============================================================================

print("\n" + "=" * 80)
print("36. PRIORITY QUEUE")
print("=" * 80)

print(
    """
A priority queue is different from an ordinary FIFO queue.

An ordinary queue selects:
    earliest arrival

A priority queue selects:
    highest or lowest priority

Python's standard library provides heapq for heap-based priority queues.

A min-heap returns the smallest priority value first.
"""
)

import heapq

priority_queue: list[tuple[int, str]] = []

heapq.heappush(priority_queue, (3, "Low priority"))
heapq.heappush(priority_queue, (1, "Critical"))
heapq.heappush(priority_queue, (2, "Normal"))

while priority_queue:
    priority, task = heapq.heappop(priority_queue)
    print(priority, "->", task)


# =============================================================================
# 37. STACK VS QUEUE
# =============================================================================

print("\n" + "=" * 80)
print("37. STACK VS QUEUE")
print("=" * 80)

print(
    """
Stack:
    Ordering -> LIFO
    Add      -> top
    Remove   -> top
    Typical  -> undo, recursion, parsing, DFS

Queue:
    Ordering -> FIFO
    Add      -> rear
    Remove   -> front
    Typical  -> scheduling, BFS, task processing

Deque:
    Ordering -> both ends
    Add/remove -> front or rear
    Typical    -> sliding windows, buffers, flexible queues
"""
)


# =============================================================================
# 38. STACK VS QUEUE IMPLEMENTATION CHOICES
# =============================================================================

print("\n" + "=" * 80)
print("38. IMPLEMENTATION COMPARISON")
print("=" * 80)

print(
    """
Python list as stack:
    append() -> O(1) amortized
    pop()    -> O(1)

Python list as queue:
    append() -> O(1) amortized
    pop(0)   -> O(n)
    Usually not preferred for large FIFO workloads.

deque as queue:
    append()  -> efficient
    popleft() -> efficient

deque as stack:
    append()  -> efficient
    pop()     -> efficient

For a conventional queue, deque is usually the most natural standard-library
choice.
"""
)


# =============================================================================
# 39. BREADTH-FIRST SEARCH
# =============================================================================

print("\n" + "=" * 80)
print("39. QUEUE APPLICATION: BREADTH-FIRST SEARCH")
print("=" * 80)

print(
    """
Breadth-first search (BFS) explores a graph level by level.

A queue is essential because vertices discovered earlier must be processed
before vertices discovered later.

The graph below is represented using a dictionary whose values are lists of
neighboring vertices.
"""
)

graph = {
    "A": ["B", "C"],
    "B": ["D", "E"],
    "C": ["F"],
    "D": [],
    "E": ["F"],
    "F": [],
}


def breadth_first_search(graph: dict[str, list[str]], start: str) -> list[str]:
    """Return vertices in BFS traversal order."""
    if start not in graph:
        raise ValueError(f"Unknown start vertex: {start}")

    visited = {start}
    queue: Deque[str] = deque([start])
    traversal: list[str] = []

    while queue:
        vertex = queue.popleft()
        traversal.append(vertex)

        for neighbor in graph.get(vertex, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return traversal


print("BFS from A:", breadth_first_search(graph, "A"))


# =============================================================================
# 40. DEPTH-FIRST SEARCH WITH A STACK
# =============================================================================

print("\n" + "=" * 80)
print("40. STACK APPLICATION: DEPTH-FIRST SEARCH")
print("=" * 80)


def depth_first_search(graph: dict[str, list[str]], start: str) -> list[str]:
    """Return vertices in iterative DFS traversal order."""
    if start not in graph:
        raise ValueError(f"Unknown start vertex: {start}")

    visited: set[str] = set()
    stack = Stack[str]([start])
    traversal: list[str] = []

    while stack:
        vertex = stack.pop()

        if vertex in visited:
            continue

        visited.add(vertex)
        traversal.append(vertex)

        # Reverse pushes preserve the natural left-to-right order.
        for neighbor in reversed(graph.get(vertex, [])):
            if neighbor not in visited:
                stack.push(neighbor)

    return traversal


print("DFS from A:", depth_first_search(graph, "A"))

print(
    """
BFS and DFS differ primarily in their frontier data structure:

    BFS -> queue -> explores broadly
    DFS -> stack -> explores deeply

Both can visit all reachable vertices in O(V + E) time for a graph represented
with adjacency lists.
"""
)


# =============================================================================
# 41. RECURSION AND THE CALL STACK
# =============================================================================

print("\n" + "=" * 80)
print("41. THE CALL STACK")
print("=" * 80)

print(
    """
Function calls are managed using a call stack.

When a function calls another function:
    - A new stack frame is created.
    - Local variables and execution state are associated with that frame.
    - The called function executes.
    - Its frame is removed when it returns.

Recursive algorithms therefore consume call-stack space.

Example:
"""


def factorial_recursive(n: int) -> int:
    if n < 0:
        raise ValueError("Factorial is undefined for negative integers.")

    if n in (0, 1):
        return 1

    return n * factorial_recursive(n - 1)


print("5! =", factorial_recursive(5))

print(
    """
Python limits recursion depth to prevent uncontrolled stack growth.

For deep computations, an iterative approach may be safer.
"""
)


# =============================================================================
# 42. ITERATIVE FACTORIAL WITH A STACK
# =============================================================================

print("\n" + "=" * 80)
print("42. EXPLICIT STACK FOR ITERATIVE COMPUTATION")
print("=" * 80)


def factorial_with_stack(n: int) -> int:
    """Compute factorial using an explicit stack instead of recursion."""
    if n < 0:
        raise ValueError("Factorial requires a non-negative integer.")

    stack = Stack(range(2, n + 1))
    result = 1

    while stack:
        result *= stack.pop()

    return result


print("5! using explicit stack:", factorial_with_stack(5))


# =============================================================================
# 43. LIST OF OBJECTS
# =============================================================================

print("\n" + "=" * 80)
print("43. LISTS OF OBJECTS")
print("=" * 80)


@dataclass
class Student:
    name: str
    score: float


students = [
    Student("Asha", 91.5),
    Student("Ravi", 84.0),
    Student("Meera", 96.0),
]

for student in students:
    print(student)

students.sort(key=lambda student: student.score, reverse=True)

print("Sorted by score:")
for student in students:
    print(student)


# =============================================================================
# 44. STABLE SORTING
# =============================================================================

print("\n" + "=" * 80)
print("44. STABLE SORTING")
print("=" * 80)

records = [
    ("A", 90),
    ("B", 80),
    ("C", 90),
    ("D", 80),
]

records.sort(key=lambda record: record[1])

print(records)

print(
    """
Python's sort is stable.

If two elements have equal keys, their original relative ordering is
preserved.

This allows multi-stage sorting strategies.

For example:
    1. Sort by name.
    2. Sort by score.

The second stable sort can preserve name ordering among equal scores.
"""
)


# =============================================================================
# 45. SEARCHING: LINEAR SEARCH
# =============================================================================

print("\n" + "=" * 80)
print("45. LINEAR SEARCH")
print("=" * 80)


def linear_search(values: list[T], target: T) -> int:
    """
    Return the first index containing target, or -1 if absent.

    Time: O(n)
    Space: O(1)
    """
    for index, value in enumerate(values):
        if value == target:
            return index

    return -1


search_values = [12, 7, 19, 4, 25]

print("Index of 19:", linear_search(search_values, 19))
print("Index of 100:", linear_search(search_values, 100))


# =============================================================================
# 46. BINARY SEARCH
# =============================================================================

print("\n" + "=" * 80)
print("46. BINARY SEARCH")
print("=" * 80)

print(
    """
Binary search requires sorted data.

Instead of checking every element, it repeatedly divides the search interval
in half.

Time:
    O(log n)

Space:
    O(1) for the iterative implementation.
"""
)


def binary_search(values: list[int], target: int) -> int:
    """Return the target index or -1. Input must be sorted."""
    left = 0
    right = len(values) - 1

    while left <= right:
        middle = left + (right - left) // 2

        if values[middle] == target:
            return middle

        if values[middle] < target:
            left = middle + 1
        else:
            right = middle - 1

    return -1


sorted_values = [2, 4, 7, 9, 13, 18, 21, 30]

print("Index of 13:", binary_search(sorted_values, 13))
print("Index of 10:", binary_search(sorted_values, 10))


# =============================================================================
# 47. TWO-POINTER ARRAY TECHNIQUE
# =============================================================================

print("\n" + "=" * 80)
print("47. TWO-POINTER TECHNIQUE")
print("=" * 80)

print(
    """
Two pointers can reduce some array problems from O(n^2) to O(n).

For a sorted array, the two-sum problem can be solved by keeping:
    left  -> smallest candidate
    right -> largest candidate

If the sum is too small:
    move left forward.

If the sum is too large:
    move right backward.
"""
)


def two_sum_sorted(values: list[int], target: int) -> Optional[tuple[int, int]]:
    """Return indices of two values whose sum equals target."""
    left = 0
    right = len(values) - 1

    while left < right:
        total = values[left] + values[right]

        if total == target:
            return left, right

        if total < target:
            left += 1
        else:
            right -= 1

    return None


print(two_sum_sorted([1, 2, 4, 7, 11, 15], 15))


# =============================================================================
# 48. SLIDING WINDOW WITH A DEQUE
# =============================================================================

print("\n" + "=" * 80)
print("48. SLIDING WINDOW")
print("=" * 80)

print(
    """
A deque can maintain a moving window efficiently.

The following function computes the maximum value in every window of size k.
It uses a monotonic decreasing deque containing indices.

Each index enters and leaves the deque at most once, giving O(n) total time.
"""


def sliding_window_maximum(values: list[int], window_size: int) -> list[int]:
    """
    Return maximum value for every contiguous window.

    Time: O(n)
    Space: O(k)
    """
    if window_size <= 0:
        raise ValueError("Window size must be positive.")

    if not values:
        return []

    if window_size > len(values):
        raise ValueError("Window size cannot exceed the input length.")

    indices: Deque[int] = deque()
    result: list[int] = []

    for index, value in enumerate(values):
        # Remove indices that have moved outside the window.
        while indices and indices[0] <= index - window_size:
            indices.popleft()

        # Remove smaller values because they can never become the maximum
        # while the current larger value remains in the window.
        while indices and values[indices[-1]] <= value:
            indices.pop()

        indices.append(index)

        if index >= window_size - 1:
            result.append(values[indices[0]])

    return result


print(sliding_window_maximum([1, 3, -1, -3, 5, 3, 6, 7], 3))


# =============================================================================
# 49. ROTATING A LIST
# =============================================================================

print("\n" + "=" * 80)
print("49. LIST ROTATION")
print("=" * 80)


def rotate_right(values: list[T], positions: int) -> list[T]:
    """
    Return a rotated copy.

    Positive positions rotate right.
    Negative positions rotate left.

    Uses modulo so positions larger than the list length are handled.
    """
    if not values:
        return []

    positions %= len(values)

    if positions == 0:
        return values.copy()

    return values[-positions:] + values[:-positions]


print(rotate_right([1, 2, 3, 4, 5], 2))
print(rotate_right([1, 2, 3, 4, 5], -2))
print(rotate_right([1, 2, 3, 4, 5], 17))


# =============================================================================
# 50. REMOVING DUPLICATES WHILE PRESERVING ORDER
# =============================================================================

print("\n" + "=" * 80)
print("50. REMOVING DUPLICATES WHILE PRESERVING ORDER")
print("=" * 80)


def unique_preserving_order(values: Iterable[T]) -> list[T]:
    """
    Remove duplicate hashable values while preserving first occurrence order.

    Average time: O(n)
    Additional space: O(n)
    """
    seen: set[T] = set()
    result: list[T] = []

    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)

    return result


print(unique_preserving_order([3, 1, 3, 2, 1, 4, 2]))


# =============================================================================
# 51. WHEN ELEMENTS ARE NOT HASHABLE
# =============================================================================

print("\n" + "=" * 80)
print("51. HASHABILITY EDGE CASE")
print("=" * 80)

print(
    """
The previous duplicate-removal technique uses a set.

Set membership requires hashable elements.

Lists are mutable and therefore unhashable:

    [1, 2] cannot be an element of a set.

For arbitrary unhashable values, equality-based comparison can be used, but
the straightforward implementation is O(n^2).
"""


def unique_unhashable(values: Iterable[T]) -> list[T]:
    """Remove duplicates using equality rather than hashing."""
    result: list[T] = []

    for value in values:
        if value not in result:
            result.append(value)

    return result


print(unique_unhashable([[1, 2], [3], [1, 2], [4]]))


# =============================================================================
# 52. LIST MEMORY AND REFERENCES
# =============================================================================

print("\n" + "=" * 80)
print("52. LISTS STORE REFERENCES TO OBJECTS")
print("=" * 80)

first = ["shared"]
second = [first]

first.append("value")

print("first:", first)
print("second:", second)

print(
    """
A Python list contains references to Python objects rather than embedding all
object data directly inside the list in the same way a low-level typed array
would.

This explains behaviors involving:
- Aliasing
- Shallow copies
- Nested mutable objects
- Object identity
"""
)


# =============================================================================
# 53. MUTABLE DEFAULT ARGUMENT PITFALL
# =============================================================================

print("\n" + "=" * 80)
print("53. COMMON MISTAKE: MUTABLE DEFAULT ARGUMENTS")
print("=" * 80)


def safe_collect(value: int, items: Optional[list[int]] = None) -> list[int]:
    """
    Correct pattern for an optional mutable collection.

    A new list is created for each call when items is omitted.
    """
    if items is None:
        items = []

    items.append(value)
    return items


print(safe_collect(1))
print(safe_collect(2))

print(
    """
Avoid:

    def collect(value, items=[]):
        ...

because the default list is created once when the function is defined and
is reused across calls.

Use None and create the list inside the function instead.
"""
)


# =============================================================================
# 54. LIST MULTIPLICATION PITFALL WITH NESTED LISTS
# =============================================================================

print("\n" + "=" * 80)
print("54. COMMON MISTAKE: NESTED LIST MULTIPLICATION")
print("=" * 80)

wrong_matrix = [[0] * 3] * 3
wrong_matrix[0][0] = 99

print("Unexpected shared rows:", wrong_matrix)

correct_matrix = [[0] * 3 for _ in range(3)]
correct_matrix[0][0] = 99

print("Independent rows:", correct_matrix)

print(
    """
The expression:

    [[0] * 3] * 3

repeats references to the same inner list.

Use:

    [[0] * 3 for _ in range(3)]

to create independent rows.
"""
)


# =============================================================================
# 55. ITERATION SAFETY
# =============================================================================

print("\n" + "=" * 80)
print("55. COMMON MISTAKE: MODIFYING A LIST WHILE ITERATING")
print("=" * 80)

values = [1, 2, 3, 4, 5, 6]

for value in values[:]:
    if value % 2 == 0:
        values.remove(value)

print("After safe iteration over a copy:", values)

print(
    """
Removing elements directly from a list while iterating over that same list
can cause elements to be skipped because positions shift.

Safer patterns include:
    - Iterate over a copy
    - Build a filtered list
    - Use a list comprehension
"""
)

values = [1, 2, 3, 4, 5, 6]
values = [value for value in values if value % 2 != 0]

print("Filtering with comprehension:", values)


# =============================================================================
# 56. STACK WITH MAXIMUM VALUE SUPPORT
# =============================================================================

print("\n" + "=" * 80)
print("56. ADVANCED STACK: O(1) MINIMUM")
print("=" * 80)

print(
    """
A useful stack design can support:

    push
    pop
    minimum

all in O(1) time.

The technique maintains a second stack containing minimum values.
"""


class MinStack:
    """Stack supporting O(1) push, pop, peek, and minimum operations."""

    def __init__(self) -> None:
        self._values: list[int] = []
        self._minimums: list[int] = []

    def push(self, value: int) -> None:
        self._values.append(value)

        if not self._minimums or value <= self._minimums[-1]:
            self._minimums.append(value)

    def pop(self) -> int:
        if not self._values:
            raise IndexError("Cannot pop from an empty MinStack.")

        value = self._values.pop()

        if value == self._minimums[-1]:
            self._minimums.pop()

        return value

    def peek(self) -> int:
        if not self._values:
            raise IndexError("Cannot peek at an empty MinStack.")
        return self._values[-1]

    def minimum(self) -> int:
        if not self._minimums:
            raise IndexError("Minimum is undefined for an empty MinStack.")
        return self._minimums[-1]


min_stack = MinStack()

for value in [5, 3, 7, 2, 4]:
    min_stack.push(value)
    print(f"push({value}) -> minimum={min_stack.minimum()}")

print("pop:", min_stack.pop())
print("minimum:", min_stack.minimum())


# =============================================================================
# 57. TWO-STACK QUEUE
# =============================================================================

print("\n" + "=" * 80)
print("57. IMPLEMENTING A QUEUE USING TWO STACKS")
print("=" * 80)

print(
    """
A FIFO queue can be implemented using two LIFO stacks:

    input_stack
    output_stack

Enqueue:
    push into input_stack.

Dequeue:
    if output_stack is empty, transfer all items from input_stack to
    output_stack.

The transfer reverses the order and produces FIFO behavior.

This gives amortized O(1) queue operations.
"""


class QueueUsingTwoStacks(Generic[T]):
    """FIFO queue implemented with two stacks."""

    def __init__(self) -> None:
        self._input = Stack[T]()
        self._output = Stack[T]()

    def enqueue(self, value: T) -> None:
        self._input.push(value)

    def _transfer(self) -> None:
        if self._output.is_empty():
            while self._input:
                self._output.push(self._input.pop())

    def dequeue(self) -> T:
        self._transfer()

        if self._output.is_empty():
            raise IndexError("Cannot dequeue from an empty queue.")

        return self._output.pop()

    def front(self) -> T:
        self._transfer()

        if self._output.is_empty():
            raise IndexError("Cannot inspect an empty queue.")

        return self._output.peek()

    def __len__(self) -> int:
        return len(self._input) + len(self._output)


two_stack_queue = QueueUsingTwoStacks[int]()

for value in [1, 2, 3]:
    two_stack_queue.enqueue(value)

print("Front:", two_stack_queue.front())
print("Dequeue:", two_stack_queue.dequeue())
print("Dequeue:", two_stack_queue.dequeue())
two_stack_queue.enqueue(4)
print("Dequeue:", two_stack_queue.dequeue())
print("Dequeue:", two_stack_queue.dequeue())


# =============================================================================
# 58. DEQUE AS A GENERALIZED STRUCTURE
# =============================================================================

print("\n" + "=" * 80)
print("58. DEQUE AS A GENERALIZED STRUCTURE")
print("=" * 80)

double_ended = deque()

double_ended.append(2)
double_ended.appendleft(1)
double_ended.append(3)
double_ended.appendleft(0)

print("Deque:", double_ended)
print("Left removal:", double_ended.popleft())
print("Right removal:", double_ended.pop())
print("Remaining:", double_ended)

print(
    """
A deque can model:
    - A queue
    - A stack
    - A double-ended buffer
    - A sliding window
    - A work queue

Its flexibility is useful, but choosing the simplest suitable abstraction
usually makes code easier to understand.
"""
)


# =============================================================================
# 59. QUEUE SIMULATION
# =============================================================================

print("\n" + "=" * 80)
print("59. REAL-WORLD QUEUE SIMULATION")
print("=" * 80)


@dataclass
class Customer:
    name: str
    service_time: int


def simulate_service(customers: Iterable[Customer]) -> list[tuple[str, int]]:
    """
    Simulate a single-server FIFO service system.

    Returns:
        (customer_name, completion_time)
    """
    queue: Deque[Customer] = deque(customers)
    current_time = 0
    results: list[tuple[str, int]] = []

    while queue:
        customer = queue.popleft()
        current_time += customer.service_time
        results.append((customer.name, current_time))

    return results


customers = [
    Customer("Customer A", 3),
    Customer("Customer B", 2),
    Customer("Customer C", 4),
]

for name, completion_time in simulate_service(customers):
    print(name, "completed at time", completion_time)


# =============================================================================
# 60. PRODUCER-CONSUMER CONCEPT
# =============================================================================

print("\n" + "=" * 80)
print("60. PRODUCER-CONSUMER CONCEPT")
print("=" * 80)

print(
    """
A producer creates work items and places them into a queue.

A consumer removes work items and processes them.

Conceptually:

    Producer
       |
       v
    [ Queue ]
       |
       v
    Consumer

The queue decouples production from consumption.

In real concurrent applications, thread-safe queue implementations such as
queue.Queue may be appropriate. collections.deque itself does not provide the
same higher-level blocking coordination semantics as queue.Queue.
"""
)

from queue import Queue as ThreadSafeQueue

thread_safe_queue: ThreadSafeQueue[str] = ThreadSafeQueue()

thread_safe_queue.put("job-1")
thread_safe_queue.put("job-2")

print("Thread-safe queue item:", thread_safe_queue.get())
print("Thread-safe queue item:", thread_safe_queue.get())


# =============================================================================
# 61. ARRAY VS LIST VS DEQUE
# =============================================================================

print("\n" + "=" * 80)
print("61. ARRAY VS LIST VS DEQUE")
print("=" * 80)

print(
    """
array.array:
    - Typed homogeneous values
    - Useful when compact typed storage is desired
    - Less general than list

list:
    - Dynamic array
    - Fast indexing
    - Excellent general-purpose sequence
    - Efficient append/pop at the end
    - Expensive insertion/removal at the front

deque:
    - Efficient operations at both ends
    - Natural queue implementation
    - Natural stack implementation
    - Random indexing is not its primary strength

There is no universally best data structure. The operation pattern determines
the appropriate choice.
"""
)


# =============================================================================
# 62. LIST VS ARRAY MEMORY TRADE-OFF
# =============================================================================

print("\n" + "=" * 80)
print("62. LIST VS TYPED ARRAY")
print("=" * 80)

python_list = [1, 2, 3, 4, 5]
typed_array = array("i", [1, 2, 3, 4, 5])

print("Python list:", python_list)
print("Typed array:", typed_array)
print("List object size:", python_list.__sizeof__())
print("Typed array object size:", typed_array.__sizeof__())

print(
    """
The exact memory footprint depends on the Python implementation and platform.

A Python list stores references to Python objects. A typed array stores values
according to its declared type.

For numerical workloads, specialized numerical libraries may be more
appropriate than either structure, but such libraries are outside this
standard-library-only script.
"""
)


# =============================================================================
# 63. MEMORY COMPLEXITY
# =============================================================================

print("\n" + "=" * 80)
print("63. SPACE COMPLEXITY")
print("=" * 80)

print(
    """
Typical auxiliary-space examples:

Linear list copy:
    O(n)

Stack containing n items:
    O(n)

Queue containing n items:
    O(n)

BFS:
    O(V) auxiliary space in the worst case.

DFS with an explicit stack:
    O(V) auxiliary space in the worst case.

Sliding-window maximum:
    O(k) auxiliary space.

Binary search:
    O(1) auxiliary space when implemented iteratively.

Space complexity includes memory required beyond the input when discussing
auxiliary space. Conventions can differ when the input storage itself is
included.
"""
)


# =============================================================================
# 64. ERROR HANDLING PRINCIPLES
# =============================================================================

print("\n" + "=" * 80)
print("64. ERROR HANDLING")
print("=" * 80)

print(
    """
Data-structure implementations should define behavior for invalid states.

Important cases:
- Empty stack pop
- Empty queue dequeue
- Invalid index
- Invalid capacity
- Full bounded queue
- Invalid search assumptions
- Mismatched parentheses
- Division by zero
- Unsupported tokens

Good implementations raise meaningful exceptions instead of silently
returning incorrect results.
"""
)


# =============================================================================
# 65. INVARIANTS
# =============================================================================

print("\n" + "=" * 80)
print("65. DATA-STRUCTURE INVARIANTS")
print("=" * 80)

print(
    """
An invariant is a condition that must remain true throughout an implementation.

Examples:

Stack:
    The last element in the underlying sequence is the top.

Queue:
    The front item is the oldest unremoved item.

Circular queue:
    0 <= size <= capacity
    front and rear always remain valid circular indices.

BFS:
    A vertex is marked visited before it is added for processing, preventing
    repeated insertion.

Invariants are central to debugging and correctness proofs.
"""
)


# =============================================================================
# 66. ASSERTIONS FOR INVARIANTS
# =============================================================================

print("\n" + "=" * 80)
print("66. ASSERTIONS")
print("=" * 80)


def validate_circular_queue(queue_object: CircularQueue[T]) -> None:
    """Basic invariant validation for the circular queue implementation."""
    assert 0 <= queue_object._size <= queue_object._capacity
    assert 0 <= queue_object._front < queue_object._capacity
    assert 0 <= queue_object._rear < queue_object._capacity


test_circular = CircularQueue[int](4)
test_circular.enqueue(10)
test_circular.enqueue(20)
validate_circular_queue(test_circular)
print("Circular queue invariants validated.")


# =============================================================================
# 67. UNIT TESTING
# =============================================================================

print("\n" + "=" * 80)
print("67. UNIT TESTING DATA STRUCTURES")
print("=" * 80)

import unittest


class TestStack(unittest.TestCase):
    def test_push_peek_pop(self) -> None:
        stack = Stack[int]()
        stack.push(10)
        stack.push(20)

        self.assertEqual(stack.peek(), 20)
        self.assertEqual(stack.pop(), 20)
        self.assertEqual(stack.pop(), 10)
        self.assertTrue(stack.is_empty())

    def test_empty_pop(self) -> None:
        stack = Stack[int]()

        with self.assertRaises(IndexError):
            stack.pop()


class TestQueue(unittest.TestCase):
    def test_fifo_order(self) -> None:
        queue = Queue[str]()
        queue.enqueue("A")
        queue.enqueue("B")
        queue.enqueue("C")

        self.assertEqual(queue.dequeue(), "A")
        self.assertEqual(queue.dequeue(), "B")
        self.assertEqual(queue.dequeue(), "C")

    def test_empty_dequeue(self) -> None:
        queue = Queue[int]()

        with self.assertRaises(IndexError):
            queue.dequeue()


class TestAlgorithms(unittest.TestCase):
    def test_parentheses(self) -> None:
        self.assertTrue(are_parentheses_balanced("({[]})"))
        self.assertFalse(are_parentheses_balanced("([)]"))

    def test_binary_search(self) -> None:
        values = [1, 3, 5, 7, 9]
        self.assertEqual(binary_search(values, 7), 3)
        self.assertEqual(binary_search(values, 8), -1)

    def test_sliding_window(self) -> None:
        values = [1, 3, -1, -3, 5, 3, 6, 7]
        self.assertEqual(
            sliding_window_maximum(values, 3),
            [3, 3, 5, 5, 6, 7],
        )


# Run the tests without terminating the entire educational script.
test_result = unittest.TextTestRunner(verbosity=1).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(TestStack)
)

print("Stack test group successful:", test_result.wasSuccessful())

test_result = unittest.TextTestRunner(verbosity=1).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(TestQueue)
)

print("Queue test group successful:", test_result.wasSuccessful())

test_result = unittest.TextTestRunner(verbosity=1).run(
    unittest.defaultTestLoader.loadTestsFromTestCase(TestAlgorithms)
)

print("Algorithm test group successful:", test_result.wasSuccessful())


# =============================================================================
# 68. PERFORMANCE MEASUREMENT
# =============================================================================

print("\n" + "=" * 80)
print("68. PERFORMANCE COMPARISON: LIST QUEUE VS DEQUE")
print("=" * 80)

print(
    """
This small benchmark demonstrates the conceptual cost difference between:

    list.pop(0)
    deque.popleft()

The exact timing depends on hardware, Python version, operating system, and
system load. The important observation is the growth behavior, not one
particular timing number.
"""
)


def benchmark_list_queue(size: int) -> float:
    values = list(range(size))

    start = time.perf_counter()

    while values:
        values.pop(0)

    return time.perf_counter() - start


def benchmark_deque_queue(size: int) -> float:
    values = deque(range(size))

    start = time.perf_counter()

    while values:
        values.popleft()

    return time.perf_counter() - start


for size in [1_000, 5_000]:
    list_time = benchmark_list_queue(size)
    deque_time = benchmark_deque_queue(size)

    print(
        f"n={size:,}: "
        f"list.pop(0)={list_time:.6f}s, "
        f"deque.popleft()={deque_time:.6f}s"
    )


# =============================================================================
# 69. AMORTIZED COMPLEXITY EXAMPLE
# =============================================================================

print("\n" + "=" * 80)
print("69. AMORTIZED COMPLEXITY")
print("=" * 80)

print(
    """
Suppose a dynamic array has to resize occasionally.

Most append operations cost approximately constant time.

A resize may cost O(n), but it does not happen on every append.

Across a long sequence of appends, the total cost can be spread over all
operations, resulting in O(1) amortized cost per append.

This is an example of amortized analysis rather than worst-case analysis.
"""
)


# =============================================================================
# 70. CUSTOM DYNAMIC ARRAY
# =============================================================================

print("\n" + "=" * 80)
print("70. EDUCATIONAL DYNAMIC ARRAY IMPLEMENTATION")
print("=" * 80)

print(
    """
The following class illustrates the idea behind a resizable array.

It is intentionally educational. Python's built-in list is far more mature
and should normally be used instead of this class.
"""


class DynamicArray(Generic[T]):
    """
    Educational dynamic-array implementation.

    append:
        O(1) amortized

    index access:
        O(1)

    insertion/deletion in the middle:
        O(n)
    """

    def __init__(self, initial_capacity: int = 4) -> None:
        if initial_capacity <= 0:
            raise ValueError("Initial capacity must be positive.")

        self._capacity = initial_capacity
        self._size = 0
        self._data: list[Optional[T]] = [None] * self._capacity

    def _resize(self, new_capacity: int) -> None:
        new_data: list[Optional[T]] = [None] * new_capacity

        for index in range(self._size):
            new_data[index] = self._data[index]

        self._data = new_data
        self._capacity = new_capacity

    def append(self, value: T) -> None:
        if self._size == self._capacity:
            self._resize(self._capacity * 2)

        self._data[self._size] = value
        self._size += 1

    def get(self, index: int) -> T:
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range.")

        value = self._data[index]

        if value is None:
            raise RuntimeError("Unexpected empty slot.")

        return value

    def set(self, index: int, value: T) -> None:
        if index < 0 or index >= self._size:
            raise IndexError("DynamicArray index out of range.")

        self._data[index] = value

    def pop(self) -> T:
        if self._size == 0:
            raise IndexError("Cannot pop from an empty DynamicArray.")

        index = self._size - 1
        value = self._data[index]
        self._data[index] = None
        self._size -= 1

        if value is None:
            raise RuntimeError("Unexpected empty slot.")

        return value

    def __len__(self) -> int:
        return self._size

    def __repr__(self) -> str:
        values = [self.get(index) for index in range(self._size)]
        return (
            f"DynamicArray(values={values!r}, "
            f"size={self._size}, capacity={self._capacity})"
        )


dynamic_array = DynamicArray[int](2)

for value in range(1, 7):
    dynamic_array.append(value)
    print(dynamic_array)

print("Index 3:", dynamic_array.get(3))
dynamic_array.set(3, 99)
print("After set:", dynamic_array)
print("Popped:", dynamic_array.pop())
print("Final:", dynamic_array)


# =============================================================================
# 71. CACHE-FRIENDLY ACCESS CONSIDERATIONS
# =============================================================================

print("\n" + "=" * 80)
print("71. MEMORY LOCALITY AND PERFORMANCE")
print("=" * 80)

print(
    """
Contiguous or compact storage can improve CPU cache locality.

A low-level array of primitive values can often be processed efficiently
because nearby values are stored near each other in memory.

Python lists add object-reference and object-management overhead.

Performance depends on more than Big-O:
- Constant factors
- Memory locality
- Object allocation
- Interpreter overhead
- CPU cache behavior
- Data type
- Input size
- Access pattern

Big-O describes growth behavior, not every aspect of real execution speed.
"""
)


# =============================================================================
# 72. SECURITY CONSIDERATIONS
# =============================================================================

print("\n" + "=" * 80)
print("72. SECURITY CONSIDERATIONS")
print("=" * 80)

print(
    """
Data structures themselves are not usually security boundaries, but unsafe
use can create vulnerabilities.

Important considerations:

1. Unbounded memory growth
   A program that accepts unlimited input into a list, stack, or queue can
   consume excessive memory.

2. Denial of service
   Attackers may intentionally provide very large inputs that trigger
   expensive operations such as repeated front deletion from a list.

3. Recursion depth
   Deep recursive input can exhaust the Python call stack.

4. Input validation
   Stack and queue capacities should be validated when a bounded structure is
   required.

5. Algorithmic complexity
   Choosing O(n^2) processing for attacker-controlled input can create
   algorithmic denial-of-service risks.

6. Sensitive data retention
   Queues and lists may keep sensitive objects alive longer than necessary.
   Applications should remove or overwrite references when appropriate.

7. Resource limits
   Production systems should impose appropriate limits on queue sizes,
   request sizes, batch sizes, or stored history.
"""
)


# =============================================================================
# 73. PRODUCTION DESIGN CONSIDERATIONS
# =============================================================================

print("\n" + "=" * 80)
print("73. PRODUCTION DESIGN CONSIDERATIONS")
print("=" * 80)

print(
    """
When selecting among these structures, ask:

1. Do I need random indexed access?
    Use a list or array-like structure.

2. Do I need efficient append/pop at the end?
    Use a list.

3. Do I need FIFO behavior?
    Use deque or an appropriate queue abstraction.

4. Do I need LIFO behavior?
    Use a list or deque as a stack.

5. Do I need efficient operations at both ends?
    Use deque.

6. Do I need fixed capacity?
    Use a bounded structure or explicitly enforce a capacity.

7. Do I need priorities rather than arrival order?
    Use a priority queue such as heapq.

8. Do multiple threads coordinate around the queue?
    Use a synchronization-aware queue such as queue.Queue when appropriate.

9. Do I need compact homogeneous numerical storage?
    Consider array.array or a domain-specific numerical structure.

10. Is the data size untrusted?
    Apply resource limits and validate inputs.

The best data structure should match the dominant operations and correctness
requirements rather than being selected solely because it is familiar.
"""
)


# =============================================================================
# 74. PRACTICAL DECISION TABLE
# =============================================================================

print("\n" + "=" * 80)
print("74. PRACTICAL DECISION GUIDE")
print("=" * 80)

decision_table = [
    ("Random index access", "list / array"),
    ("Append at end", "list"),
    ("LIFO", "list / deque"),
    ("FIFO", "deque / queue.Queue"),
    ("Both-end insertion/removal", "deque"),
    ("Priority-based processing", "heapq"),
    ("Fixed-capacity ring buffer", "circular queue"),
    ("Typed homogeneous values", "array.array"),
    ("Graph BFS", "deque"),
    ("Graph DFS", "stack"),
    ("Undo/redo", "two stacks"),
    ("Sliding window", "deque"),
]

for requirement, structure in decision_table:
    print(f"{requirement:35} -> {structure}")


# =============================================================================
# 75. EDGE CASE TESTS
# =============================================================================

print("\n" + "=" * 80)
print("75. EDGE CASE TESTS")
print("=" * 80)

edge_cases = [
    ("Empty binary search", binary_search([], 1)),
    ("Single-item binary search", binary_search([5], 5)),
    ("Single-item rotation", rotate_right([5], 100)),
    ("Empty reversal", reverse_with_stack([])),
    ("Balanced empty expression", are_parentheses_balanced("")),
    ("Sliding window size one", sliding_window_maximum([7, 2, 9], 1)),
]

for description, result in edge_cases:
    print(f"{description}: {result}")


# =============================================================================
# 76. INVALID INPUT TESTS
# =============================================================================

print("\n" + "=" * 80)
print("76. INVALID INPUT TESTS")
print("=" * 80)

invalid_operations = [
    (
        "CircularQueue(0)",
        lambda: CircularQueue[int](0),
    ),
    (
        "rotate_right([], 3)",
        lambda: rotate_right([], 3),
    ),
    (
        "sliding_window_maximum([1, 2], 3)",
        lambda: sliding_window_maximum([1, 2], 3),
    ),
    (
        "factorial_recursive(-1)",
        lambda: factorial_recursive(-1),
    ),
]

for description, operation in invalid_operations:
    try:
        result = operation()
        print(description, "->", result)
    except (ValueError, IndexError, OverflowError, ZeroDivisionError) as error:
        print(description, "-> handled:", error)


# =============================================================================
# 77. COMMON MISTAKES
# =============================================================================

print("\n" + "=" * 80)
print("77. COMMON MISTAKES")
print("=" * 80)

print(
    """
1. Using pop(0) repeatedly for a large queue.
   Better: deque.popleft().

2. Forgetting that Python indexes from zero.
   Last index = len(values) - 1.

3. Confusing append() with extend().
   append adds one object; extend adds elements from an iterable.

4. Assuming list assignment copies a list.
   It creates another reference.

5. Using [[0] * columns] * rows for independent matrix rows.
   This creates shared inner-list references.

6. Modifying a list while iterating over the same list.
   Elements can be skipped.

7. Performing binary search on unsorted data.
   Binary search depends on ordering.

8. Ignoring empty-stack or empty-queue behavior.
   Define and test underflow behavior.

9. Assuming every append is always literally O(1).
   Dynamic arrays have occasional resize operations, so the correct general
   statement is O(1) amortized.

10. Choosing a data structure without considering operations.
    A theoretically suitable structure can still be inappropriate if the
    dominant operations are expensive.
"""
)


# =============================================================================
# 78. COMPREHENSIVE EXAMPLE: TASK PROCESSOR
# =============================================================================

print("\n" + "=" * 80)
print("78. COMPREHENSIVE EXAMPLE: TASK PROCESSOR")
print("=" * 80)


@dataclass
class Task:
    task_id: int
    description: str
    priority: int


class TaskProcessor:
    """
    Demonstrates multiple data structures in one application.

    - deque for FIFO tasks
    - list for completed-task history
    - Stack for undoing the most recently completed task
    """

    def __init__(self) -> None:
        self.pending: Deque[Task] = deque()
        self.completed: list[Task] = []
        self.undo_stack: Stack[Task] = Stack()

    def add_task(self, task: Task) -> None:
        self.pending.append(task)

    def process_next(self) -> Optional[Task]:
        if not self.pending:
            return None

        task = self.pending.popleft()
        self.completed.append(task)
        self.undo_stack.push(task)
        return task

    def undo_last_completion(self) -> Optional[Task]:
        if not self.undo_stack:
            return None

        task = self.undo_stack.pop()

        if self.completed and self.completed[-1] == task:
            self.completed.pop()

        self.pending.appendleft(task)
        return task


processor = TaskProcessor()

processor.add_task(Task(1, "Process report", 2))
processor.add_task(Task(2, "Send email", 3))
processor.add_task(Task(3, "Update database", 1))

print("Pending:", processor.pending)

processed = processor.process_next()
print("Processed:", processed)
print("Pending:", processor.pending)
print("Completed:", processor.completed)

undone = processor.undo_last_completion()
print("Undone:", undone)
print("Pending:", processor.pending)
print("Completed:", processor.completed)


# =============================================================================
# 79. DATA STRUCTURE SELECTION BY OPERATION
# =============================================================================

print("\n" + "=" * 80)
print("79. SELECTING A STRUCTURE BY OPERATION")
print("=" * 80)

print(
    """
If your dominant operation is...

Frequent index access:
    list

Frequent append/pop at the end:
    list

Frequent insertion/removal at both ends:
    deque

FIFO processing:
    deque or queue.Queue

LIFO processing:
    list or deque

Priority selection:
    heapq

Sorted searching:
    sorted list + binary search

Fixed-size circular buffering:
    circular queue

Undo/redo:
    two stacks

Level-order graph traversal:
    queue/deque

Depth-first graph traversal:
    stack
"""
)


# =============================================================================
# 80. FINAL INTEGRATED DEMONSTRATION
# =============================================================================

print("\n" + "=" * 80)
print("80. INTEGRATED DATA-STRUCTURE DEMONSTRATION")
print("=" * 80)

# List: general ordered storage.
inventory = ["keyboard", "mouse", "monitor"]

# Stack: most recently added inventory audit entry is inspected first.
audit_stack: Stack[str] = Stack()

for item in inventory:
    audit_stack.push(f"Added {item}")

# Queue: process customer requests in arrival order.
requests: Deque[str] = deque(
    [
        "Customer request 1",
        "Customer request 2",
        "Customer request 3",
    ]
)

print("Inventory:", inventory)

print("Audit stack:")
while audit_stack:
    print(" ", audit_stack.pop())

print("Requests:")
while requests:
    print(" ", requests.popleft())


# =============================================================================
# 81. CONCEPTUAL CHECKS
# =============================================================================

print("\n" + "=" * 80)
print("81. CONCEPTUAL CHECKS")
print("=" * 80)

conceptual_checks = {
    "List index access is generally O(1)": True,
    "List front deletion is generally O(n)": True,
    "Stack follows LIFO": True,
    "Queue follows FIFO": True,
    "deque is suitable for efficient endpoint operations": True,
    "Binary search requires sorted data": True,
    "BFS uses a queue": True,
    "DFS can use a stack": True,
    "Dynamic-array append is O(1) amortized": True,
}

for statement, expected in conceptual_checks.items():
    print(f"[{'PASS' if expected else 'FAIL'}] {statement}")


# =============================================================================
# 82. KEY TECHNICAL REFERENCE
# =============================================================================

print("\n" + "=" * 80)
print("82. TECHNICAL REFERENCE")
print("=" * 80)

print(
    """
DATA STRUCTURE
--------------
Array:
    Ordered indexed collection, traditionally fixed-size and homogeneous.

Python list:
    Mutable dynamic-array sequence.

Stack:
    LIFO abstract data type.

Queue:
    FIFO abstract data type.

Deque:
    Double-ended queue supporting efficient operations at both ends.


CORE OPERATIONS
---------------
List:
    access       -> O(1)
    append       -> O(1) amortized
    pop end      -> O(1)
    search       -> O(n)
    insert front -> O(n)

Stack:
    push         -> O(1) amortized with list
    pop          -> O(1)
    peek         -> O(1)

Queue with deque:
    enqueue      -> O(1)
    dequeue      -> O(1)
    front        -> O(1)

Binary search:
    O(log n), sorted input required.

BFS:
    O(V + E)

DFS:
    O(V + E)

Sliding-window maximum with monotonic deque:
    O(n)


PRIMARY PYTHON TOOLS
--------------------
list
    General-purpose dynamic array.

array.array
    Typed array.

collections.deque
    Efficient double-ended queue.

queue.Queue
    Thread-coordination-oriented queue abstraction.

heapq
    Heap-based priority queue functionality.


KEY DESIGN PRINCIPLE
--------------------
Choose the data structure according to the operations that dominate the
workload.

The correct structure is not simply the one with the most features. It is
the one whose behavior, complexity, memory characteristics, and correctness
properties fit the problem.
"""
)

print("\n" + "=" * 80)
print("END OF DATA STRUCTURES STUDY SCRIPT")
print("=" * 80)
