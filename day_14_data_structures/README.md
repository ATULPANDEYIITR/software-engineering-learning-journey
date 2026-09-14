# Data structures: arrays, lists, stacks, and queues

## Introduction

Data structures are systematic ways of organizing and storing data so that common operations can be performed correctly and efficiently. The choice of data structure directly influences access time, insertion and deletion cost, memory usage, algorithm design, and the scalability of an application.

This study focuses on four closely related concepts:

- Arrays
- Python lists
- Stacks
- Queues

The Python script progresses from basic indexing and list manipulation to typed arrays, dynamic-array behavior, stack and queue implementations, graph traversal, expression processing, circular queues, priority queues, sliding-window algorithms, complexity analysis, testing, performance considerations, and production-oriented design.

The examples use Python's standard library and are designed to be executable as a standalone study file.

## Fundamental terminology

An **element** is an individual value stored in a data structure.

An **index** identifies the position of an element in an indexed sequence. Python uses zero-based indexing, so the first element has index `0`.

The **length** is the number of elements currently stored.

The **capacity** describes the amount of storage available to a structure before additional allocation or resizing is required. Capacity is particularly important for fixed-size arrays, bounded queues, and dynamic-array implementations.

**Traversal** means visiting elements systematically.

**Access** means retrieving an element.

**Insertion** means adding an element.

**Deletion** means removing an element.

**Search** means locating an element or determining whether it exists.

**Underflow** occurs when a removal or access operation is attempted on an empty stack or queue.

**Overflow** occurs when an insertion cannot be performed because a bounded structure is full.

Two important ordering models are:

- **LIFO**, or Last In, First Out, used by stacks.
- **FIFO**, or First In, First Out, used by queues.

## Arrays

An array is an ordered collection whose elements can be accessed using indexes. In traditional low-level implementations, an array normally has a fixed size and stores values of a defined type in contiguous memory.

A conceptual array can be represented as:

    Index:  0    1    2    3
    Value: 10   20   30   40

The position of an element can be calculated directly from its index. This is why indexed access to an array is generally constant time.

Traditional arrays differ from Python lists in important ways. A low-level typed array commonly stores values directly in a compact representation. A Python list is a dynamic array of references to Python objects and is considerably more general.

## Python's `array` module

Python provides the standard-library `array` module for typed arrays.

For example:

    array("i", [10, 20, 30, 40])

The type code determines the kind of values stored. The script demonstrates integer arrays and shows that incompatible values cannot simply be inserted into a typed array.

Typed arrays are useful when compact homogeneous storage is desired. They are less flexible than Python lists because their elements must conform to the declared type.

The exact memory behavior depends on the Python implementation and platform.

## Python lists

A Python list is an ordered, mutable, dynamically resizable sequence.

Important properties include:

- Ordered elements
- Mutable contents
- Indexed access
- Slicing
- Duplicate values
- Dynamic resizing
- Ability to contain objects of different types

A list can contain homogeneous data:

    [10, 20, 30, 40]

or mixed objects:

    [10, "Python", 3.14, True]

Although mixed types are valid, using a consistent logical type often produces clearer and more maintainable programs.

## Indexing

Python lists use zero-based indexing.

For a list of length `n`:

    First index = 0
    Last index  = n - 1

Negative indexes count backward:

    -1 -> last element
    -2 -> second-last element

For example:

    values = [10, 20, 30, 40]
    values[0]  -> 10
    values[-1] -> 40

An invalid index raises `IndexError`.

Indexed access is generally O(1) because the list can locate the requested position directly.

## Slicing

Python supports sequence slicing using:

    sequence[start:stop:step]

The stop position is excluded.

Examples include:

    values[1:4]
    values[:3]
    values[3:]
    values[::2]
    values[::-1]

Slicing normally creates a new list. It is therefore important not to confuse a slice with a view into the original list.

A slice can be convenient, but copying a large list through slicing requires O(n) time and additional memory.

## Creating lists

The script demonstrates several common construction techniques:

    []
    [1, 2, 3]
    [0] * 5
    list(range(1, 6))
    [value * value for value in range(1, 6)]

The `range` object itself is lazy, while converting it to a list materializes its values.

## List mutation operations

The most important list methods include:

### `append`

`append(value)` adds one object to the end of the list.

    values = [1, 2]
    values.append(3)

The result is:

    [1, 2, 3]

Appending is O(1) amortized.

### `extend`

`extend(iterable)` adds the elements produced by an iterable.

    values = [1, 2]
    values.extend([3, 4])

The result is:

    [1, 2, 3, 4]

### `insert`

`insert(index, value)` places an element at a particular position.

    values.insert(1, 99)

Elements after the insertion position must generally be shifted, making arbitrary-position insertion O(n).

### `pop`

`pop()` removes and returns the last element.

    value = values.pop()

Removing from the end is O(1).

`pop(index)` removes a specific position. `pop(0)` is O(n) because the remaining elements need to shift.

### `remove`

`remove(value)` removes the first matching value.

If the value is not present, Python raises `ValueError`.

Searching for the value is O(n), and removing it may also require shifting later elements.

## `append` versus `extend`

This distinction is important.

    values = [1, 2]
    values.append([3, 4])

produces a list containing the nested list:

    [1, 2, [3, 4]]

By contrast:

    values = [1, 2]
    values.extend([3, 4])

produces:

    [1, 2, 3, 4]

`append` adds one object. `extend` consumes an iterable and adds its elements.

## Searching lists

Common operations include:

    value in values
    values.index(value)
    values.count(value)

Membership testing and `index` are generally O(n).

`index` returns the first matching position. It raises `ValueError` when no match exists.

`count` scans the sequence and therefore also requires O(n) time.

## Sorting

Python provides both `sorted` and `list.sort`.

`sorted` creates a new list:

    sorted_values = sorted(values)

`sort` modifies the existing list:

    values.sort()

Sorting supports reverse ordering and custom keys:

    values.sort(reverse=True)

    sorted(records, key=lambda record: record.score)

Python's built-in sorting algorithm is Timsort. Its general worst-case complexity is O(n log n), and it can take advantage of existing ordering in the input.

Python's sorting algorithm is stable. If two elements have equal keys, their relative ordering is preserved.

## List comprehensions

A list comprehension provides a compact way to create a list:

    [expression for item in iterable]

A condition can also be included:

    [expression for item in iterable if condition]

For example, the script creates squares and even squares using comprehensions.

List comprehensions are particularly effective for straightforward transformations and filtering. Extremely complicated comprehensions can reduce readability, in which case an ordinary loop is often preferable.

## Nested lists

Nested lists are useful for representing matrices, tables, grids, and hierarchical data.

For example:

    [
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]

An element can be accessed with two indexes:

    matrix[1][2]

The first index selects the row and the second selects the column.

Nested structures require careful handling of object references because inner lists are mutable objects.

## Aliasing and copying

Assignment does not copy a list.

    original = [1, 2, 3]
    alias = original

Both names refer to the same list.

A modification through either name affects the same underlying object.

A shallow copy can be created with:

    original.copy()
    list(original)
    original[:]

A shallow copy duplicates the outer list but does not recursively duplicate nested objects.

This distinction becomes important with nested mutable data.

## Deep copying

`copy.deepcopy` recursively copies nested objects.

This can separate nested mutable objects from their originals, but deep copying may be expensive for large or complex object graphs.

Deep copying should therefore be used when independent nested state is actually required rather than as a default operation.

## Dynamic arrays and Python lists

Python lists behave conceptually like dynamic arrays.

A dynamic array maintains allocated storage and grows when more elements are required. Most append operations do not require a complete resize. Occasionally, the underlying storage must grow and references must be transferred to a larger allocation.

This produces the important distinction between worst-case and amortized complexity.

For a dynamic-array append:

- Individual worst-case operation: O(n)
- Amortized complexity: O(1)

The amortized analysis spreads occasional expensive resize operations across many inexpensive appends.

## List complexity

Typical Python list complexity is:

| Operation | Typical complexity |
|---|---:|
| Index access | O(1) |
| Index assignment | O(1) |
| Append | O(1) amortized |
| Pop from end | O(1) |
| Insert at beginning | O(n) |
| Insert in middle | O(n) |
| Delete from beginning | O(n) |
| Delete from middle | O(n) |
| Search by value | O(n) |
| Remove by value | O(n) |
| Count | O(n) |
| Sorting | O(n log n) |
| Reverse in place | O(n) |
| Copy | O(n) |

The exact implementation details can vary between Python implementations, but these are the standard complexity expectations for CPython lists.

## Stack abstract data type

A stack follows LIFO ordering.

If values are pushed in this order:

    A
    B
    C

then `C` is removed first.

The primary stack operations are:

- `push`
- `pop`
- `peek`
- `is_empty`

A stack can be implemented using a Python list because list append and end-pop are efficient.

## Stack using a list

The simplest Python stack is:

    stack = []

Push:

    stack.append(value)

Peek:

    stack[-1]

Pop:

    stack.pop()

This implementation is efficient because operations occur at the end of the list.

A list should generally not be used by repeatedly inserting or removing from the beginning when stack behavior is intended.

## Robust stack implementation

The script implements a generic `Stack` class using a Python list.

The implementation explicitly handles underflow:

    raise IndexError("Cannot pop from an empty stack.")

This makes invalid state visible instead of silently returning an incorrect value.

The class also provides `size`, `clear`, `__len__`, `__bool__`, and representation support.

## Stack underflow

Calling `pop` on an empty stack is an underflow condition.

A production implementation should define how this condition is handled.

Possible approaches include:

- Raise an exception
- Return a special value
- Use an optional result
- Block until data becomes available in a concurrent system

For a conventional Python data structure API, raising an appropriate exception is often the clearest choice.

## Stack application: reversing data

A stack naturally reverses a sequence.

If the input is:

    [1, 2, 3, 4, 5]

pushing all elements and then popping them produces:

    [5, 4, 3, 2, 1]

This demonstrates the direct relationship between LIFO behavior and reversal.

## Balanced parentheses

Stacks are a natural solution for checking balanced delimiters.

The algorithm:

1. Push every opening delimiter.
2. When a closing delimiter is encountered, compare it with the top opening delimiter.
3. Reject a mismatch.
4. Reject a closing delimiter when the stack is empty.
5. Require the stack to be empty at the end.

The script supports:

- `()`
- `[]`
- `{}`

The algorithm takes O(n) time and O(n) worst-case auxiliary space.

## Expression processing

Stacks are frequently used by expression-processing algorithms.

The script demonstrates conversion from simple infix notation to postfix notation.

For example:

    A + B * C

becomes:

    A B C * +

The operator stack stores operators until precedence determines when they can be emitted.

This demonstrates how stacks can encode temporary state required by parsing algorithms.

The example is intentionally limited to simple single-character operands and basic operators. A production expression parser must account for numbers, unary operators, functions, whitespace, associativity, errors, and other syntax.

## Postfix expression evaluation

Postfix notation allows expressions to be evaluated naturally with a stack.

For:

    2 3 * 4 +

the stack process is:

1. Push 2.
2. Push 3.
3. Multiply 2 and 3.
4. Push 4.
5. Add 6 and 4.

The result is 10.

The implementation validates insufficient operands and division by zero.

## Undo and redo

Undo and redo systems are a classic two-stack application.

One stack stores actions that can be undone. Another stores actions that have been undone and can potentially be redone.

When a new edit occurs, the redo history is cleared because the previous future history is no longer valid.

This is a practical example of how an abstract data structure can directly represent application behavior.

## Queues

A queue follows FIFO ordering.

If items enter in the order:

    A
    B
    C

then the removal order is:

    A
    B
    C

The main operations are:

- Enqueue
- Dequeue
- Front or peek
- Empty check

Queues model systems in which older work should generally be processed before newer work.

## Lists as queues

A list can technically represent a queue:

    queue.append(value)
    queue.pop(0)

The problem is performance.

Removing the first element requires the remaining elements to shift. Therefore `pop(0)` is O(n).

Repeatedly performing this operation can result in quadratic behavior.

For substantial FIFO workloads, `collections.deque` is usually more appropriate.

## `collections.deque`

A deque is a double-ended queue.

It supports efficient endpoint operations such as:

    append()
    appendleft()
    pop()
    popleft()

This makes it suitable for both queues and stacks.

For FIFO behavior:

    queue.append(value)
    queue.popleft()

For LIFO behavior:

    stack.append(value)
    stack.pop()

The deque is particularly useful when both ends must be manipulated efficiently.

## Queue implementation

The script implements a generic `Queue` class using `collections.deque`.

The queue provides:

- `enqueue`
- `dequeue`
- `front`
- `rear`
- `is_empty`
- `size`
- `clear`

The implementation explicitly raises `IndexError` when a removal or inspection is attempted on an empty queue.

## Queue underflow

Queue underflow occurs when an operation requiring a front element is performed while the queue is empty.

The script demonstrates explicit exception handling for this condition.

The behavior of an empty queue should be part of the API design rather than an accidental implementation detail.

## Bounded queues

A bounded queue has a maximum capacity.

A full bounded queue requires a defined policy. Possible policies include:

- Rejecting the new item
- Raising an exception
- Blocking until space becomes available
- Discarding the oldest item
- Discarding the newest item

The script implements an explicit capacity and raises `OverflowError` when the queue is full.

Bounded queues are useful for resource control because they prevent unlimited accumulation of pending work.

## Circular queues

A circular queue uses fixed storage and treats the end of that storage as logically connected to the beginning.

For a capacity of `N`, the next position can be calculated as:

    (current_index + 1) % N

This modulo operation allows indexes to wrap around.

Circular queues are useful for:

- Fixed-size buffers
- Streaming systems
- Reusable memory regions
- Producer-consumer designs
- Continuous data collection

The script implements a circular queue using a Python list, a front index, a rear index, and a size counter.

## Priority queues

A priority queue is not a normal FIFO queue.

A FIFO queue chooses the next item according to arrival order. A priority queue chooses according to priority.

Python's `heapq` module provides heap operations that can be used to implement a priority queue.

The script uses tuples such as:

    (priority, task)

With a min-heap, the smallest priority value is retrieved first.

Priority queues are useful in scheduling, event processing, shortest-path algorithms, and systems in which urgency matters more than arrival order.

## Stack versus queue

The fundamental difference is ordering.

| Property | Stack | Queue |
|---|---|---|
| Ordering | LIFO | FIFO |
| Add operation | Top | Rear |
| Remove operation | Top | Front |
| Common implementation | list/deque | deque |
| Typical application | Undo, DFS, parsing | Scheduling, BFS |

A deque can support both patterns efficiently.

## Breadth-first search

Breadth-first search, or BFS, explores a graph level by level.

A queue is the natural supporting data structure because vertices discovered earlier should be processed before vertices discovered later.

For a graph with `V` vertices and `E` edges, BFS using adjacency lists generally takes:

    O(V + E)

time.

The visited set prevents a vertex from being processed repeatedly.

## Depth-first search

Depth-first search, or DFS, explores one branch as deeply as possible before backtracking.

An explicit stack can implement iterative DFS.

The script demonstrates:

    graph
       |
       v
    stack
       |
       v
    next vertex

DFS using adjacency lists generally takes O(V + E) time.

The primary distinction from BFS is the frontier structure:

- BFS uses a queue.
- DFS uses a stack.

## Recursion and the call stack

Function calls are managed using a call stack.

When a function calls another function, Python maintains execution state for the active call. Recursive algorithms therefore consume call-stack space.

The script demonstrates recursive factorial calculation.

Deep recursion can exceed Python's recursion limits. An iterative implementation can avoid this limitation when the algorithm naturally permits iteration.

## Explicit stack versus recursion

A recursive algorithm uses the language runtime's call stack.

An iterative implementation can use an explicit `Stack` object.

This can provide greater control over:

- State representation
- Memory management
- Error handling
- Very deep traversals
- Algorithm instrumentation

The choice depends on clarity, recursion depth, and the structure of the algorithm.

## Searching

The script demonstrates two fundamental search algorithms.

### Linear search

Linear search checks elements one at a time.

Worst-case time complexity:

    O(n)

It works whether or not the input is sorted.

### Binary search

Binary search repeatedly divides a sorted search interval in half.

Time complexity:

    O(log n)

The important precondition is that the data must be sorted according to the ordering used by the search.

Applying binary search to unsorted data can produce incorrect results.

## Two-pointer technique

Two pointers are useful for many sequence problems.

For a sorted array, the two-sum problem can be solved with:

- A left pointer at the beginning
- A right pointer at the end

If the current sum is too small, the left pointer moves right.

If the sum is too large, the right pointer moves left.

This reduces the simple brute-force O(n²) approach to O(n) for a sorted input.

## Sliding-window technique

A sliding window considers a contiguous region of a sequence and moves that region across the data.

The script implements maximum values for every window of size `k`.

A monotonic deque maintains candidate indexes in decreasing value order.

Each element is inserted and removed from the deque at most once, resulting in:

    O(n)

time and:

    O(k)

auxiliary space.

This is substantially more efficient than independently scanning every window.

## Advanced stack: minimum in O(1)

The script implements a stack that supports:

- Push
- Pop
- Peek
- Minimum

while maintaining the minimum operation in O(1) time.

A second stack stores minimum values corresponding to relevant states of the primary stack.

This illustrates an important data-structure design principle: additional storage can sometimes reduce the time required for derived operations.

## Queue implemented with two stacks

A FIFO queue can be constructed from two LIFO stacks.

One stack receives new values.

When the output stack is empty, all values from the input stack are transferred to the output stack. The transfer reverses their order and produces FIFO behavior.

Individual transfers can cost O(n), but each element is transferred only a limited number of times. Consequently, enqueue and dequeue operations have O(1) amortized complexity.

## Lists of objects

Lists are not limited to primitive-looking values.

A list can store instances of classes and dataclasses.

The script defines a `Student` dataclass and stores multiple students in a list.

Sorting can then use an attribute:

    students.sort(key=lambda student: student.score)

This pattern is common in business applications, data processing, APIs, and object-oriented systems.

## Hashability and duplicate removal

A set provides efficient average-case membership testing, making it useful for duplicate removal.

For hashable values, a set can track previously seen elements.

The resulting algorithm is typically O(n) average time.

Mutable lists are unhashable, so a set cannot directly store lists as elements.

For arbitrary unhashable objects, an equality-based approach can be used, but a straightforward implementation can require O(n²) time.

## Common aliasing problems

Python variables refer to objects.

This means:

    first = [1, 2]
    second = first

does not create an independent list.

Both names refer to the same object.

This behavior is useful when intentional shared state is required, but it can cause subtle bugs when independent data was expected.

## Mutable default arguments

A common Python error is using a mutable object as a function default:

    def collect(value, items=[]):
        ...

The default list is created once when the function is defined and is reused across calls.

The safer pattern is:

    def collect(value, items=None):
        if items is None:
            items = []

This principle applies to lists, dictionaries, sets, and other mutable objects.

## Nested-list multiplication

This expression is dangerous when independent rows are intended:

    [[0] * 3] * 3

It repeats references to the same inner list.

Changing one row can therefore change all rows.

The correct pattern for independent rows is:

    [[0] * 3 for _ in range(3)]

The list comprehension creates a separate inner list during every iteration.

## Modifying a list while iterating

Removing elements from a list while iterating over that same list can cause elements to be skipped because indexes shift.

Safer alternatives include:

- Iterate over a copy.
- Build a filtered list.
- Use a list comprehension.

For example:

    values = [value for value in values if condition]

is often clearer and safer than repeated removal during traversal.

## Error handling

Robust data structures must define invalid states.

Important cases include:

- Empty stack
- Empty queue
- Full bounded queue
- Invalid capacity
- Invalid indexes
- Mismatched delimiters
- Invalid postfix expressions
- Division by zero
- Unsupported expression tokens
- Incorrect assumptions about sorted data

The script uses exceptions such as `IndexError`, `ValueError`, `OverflowError`, and `ZeroDivisionError` where they appropriately describe invalid operations.

## Invariants

An invariant is a condition that should remain true throughout the lifetime of a data structure.

Examples include:

For a stack:

    The final stored element represents the top.

For a queue:

    The front element is the oldest element that has not been removed.

For a circular queue:

    0 <= size <= capacity

    front and rear remain valid indexes.

For BFS:

    A vertex is marked visited before it is scheduled for processing.

Maintaining invariants makes implementation reasoning, testing, and debugging substantially easier.

## Testing data structures

The script includes unit tests for:

- Stack push, pop, and peek
- Stack underflow
- Queue FIFO behavior
- Queue underflow
- Balanced parentheses
- Binary search
- Sliding-window maximum

Data structures should be tested for both normal and invalid states.

Important test categories include:

- Empty input
- Single-element input
- Duplicate values
- Maximum capacity
- Full structures
- Underflow
- Overflow
- Invalid indexes
- Large input
- Boundary values
- Repeated operations

## Performance considerations

Big-O notation describes how resource requirements grow as the input becomes larger.

The script also demonstrates why Big-O alone does not describe every aspect of practical performance.

Important factors include:

- Constant factors
- Memory allocation
- CPU cache locality
- Object creation
- Interpreter overhead
- Memory usage
- Input size
- Access patterns

For example, both a list and a deque can remove elements, but removing from the front of a list has a different growth behavior from removing from the front of a deque.

## Amortized analysis

Dynamic arrays provide a useful example of amortized analysis.

Most append operations are inexpensive. Occasionally, the structure must allocate larger storage and move existing references.

Although an individual resize can cost O(n), a long sequence of appends has O(1) amortized cost per append.

Amortized complexity should not be confused with saying that every individual operation has O(1) worst-case complexity.

## Memory considerations

A Python list stores references to Python objects. The objects themselves may be stored elsewhere in memory.

This creates overhead compared with compact typed storage.

A typed `array.array` can store values according to a defined type representation.

Memory requirements depend on:

- Number of elements
- Object types
- References
- Allocated capacity
- Python implementation
- Platform

The correct structure depends on whether flexibility, compactness, or operation efficiency is most important.

## Security considerations

Poor data-structure choices can contribute to security problems when processing untrusted input.

### Unbounded memory growth

A program that continually appends attacker-controlled data to a list or queue can consume excessive memory.

### Algorithmic denial of service

An inefficient algorithm applied to large attacker-controlled input can consume excessive CPU time.

Repeated `pop(0)` operations on large lists are one simple example of a design that can become unnecessarily expensive.

### Resource limits

Bounded queues and explicit limits can prevent uncontrolled accumulation of work.

### Deep recursion

Untrusted structures that cause excessive recursion can exhaust the Python call stack or trigger recursion-limit failures.

### Input validation

Data structures should validate capacities, indexes, syntax, and other externally controlled parameters where appropriate.

### Sensitive data retention

Lists, queues, and histories can retain references to sensitive objects. Applications should avoid retaining sensitive information longer than required.

## Concurrent queue considerations

`collections.deque` is useful for ordinary single-threaded endpoint operations.

Concurrent applications may require stronger coordination semantics, such as:

- Blocking when a queue is empty
- Blocking when a queue is full
- Thread coordination
- Task completion tracking

Python's `queue.Queue` is designed for thread-oriented producer-consumer scenarios and is demonstrated in the script.

The appropriate queue abstraction depends on whether the problem is simply FIFO storage or concurrent coordination.

## Production implementation considerations

A practical decision should begin with the dominant operations.

Use a **list** when:

- Indexed access is important.
- Appending at the end is common.
- General-purpose sequence behavior is required.

Use **`array.array`** when:

- Homogeneous typed values are required.
- Compact standard-library storage is useful.

Use a **stack** when:

- The most recent item should be processed first.
- Undo behavior is required.
- Depth-first processing is appropriate.
- Parsing requires nested state.

Use a **deque** when:

- FIFO behavior is required.
- Both ends need efficient operations.
- Sliding-window algorithms are required.

Use a **priority queue** when:

- The next item is selected by priority rather than arrival order.

Use a **bounded queue** when:

- Work must have a maximum backlog.
- Resource consumption needs explicit limits.

Use a **circular queue** when:

- Storage capacity is fixed.
- Memory reuse and wrap-around behavior are useful.

## Comparison of the main structures

| Feature | Array | Python list | Stack | Queue |
|---|---|---|---|---|
| Indexed access | Yes | Yes | Usually not the abstraction | Usually not the abstraction |
| Dynamic size | Depends on implementation | Yes | Depends on implementation | Depends on implementation |
| Ordering | Sequential | Sequential | LIFO | FIFO |
| Front removal | Implementation-dependent | O(n) | Not normally used | O(1) with deque |
| End append | Typically efficient | O(1) amortized | O(1) amortized | O(1) with deque |
| Random access | Common | O(1) | Not central | Not central |
| Typical Python tool | `array.array` | `list` | `list` or `deque` | `deque` or `queue.Queue` |

## Complexity reference

| Operation or algorithm | Typical complexity |
|---|---:|
| List index access | O(1) |
| List append | O(1) amortized |
| List end pop | O(1) |
| List front deletion | O(n) |
| List search | O(n) |
| List insertion in middle | O(n) |
| List sorting | O(n log n) |
| Stack push | O(1) amortized |
| Stack pop | O(1) |
| Stack peek | O(1) |
| Deque append | O(1) |
| Deque appendleft | O(1) |
| Deque pop | O(1) |
| Deque popleft | O(1) |
| Linear search | O(n) |
| Binary search | O(log n) |
| BFS | O(V + E) |
| DFS | O(V + E) |
| Sliding-window maximum with monotonic deque | O(n) |
| Queue using two stacks | O(1) amortized per operation |

## Real-world applications

### Arrays and lists

Common uses include:

- Tables
- Records
- Collections of objects
- Numerical sequences
- Configuration data
- API response processing
- In-memory datasets
- Search and sorting algorithms

### Stacks

Common uses include:

- Undo and redo
- Function call management
- Expression parsing
- Parentheses validation
- Depth-first search
- Backtracking
- Browser history models
- State restoration

### Queues

Common uses include:

- Print processing
- Customer service systems
- Job scheduling
- Network requests
- Message processing
- Breadth-first search
- Producer-consumer architectures
- Task pipelines

### Circular queues

Common uses include:

- Audio buffers
- Streaming systems
- Fixed-size telemetry buffers
- Network buffering
- Real-time data pipelines

### Priority queues

Common uses include:

- Scheduling
- Event processing
- Pathfinding
- Resource allocation
- Emergency task handling
- Simulation systems

## Integrated design example

The script includes a task processor that combines several structures.

A deque stores pending tasks because tasks are processed in arrival order.

A list stores completed tasks because historical access and ordered storage are useful.

A stack stores recently completed tasks so the latest completion can be undone first.

This illustrates an important principle: one application can legitimately use several data structures, with each structure serving a different operational requirement.

## Choosing the right data structure

The central design question is not simply which data structure is easiest to write. It is which structure provides the required behavior at an acceptable computational and memory cost.

Useful questions include:

1. Is random index access required?
2. Are elements usually added at the end?
3. Are elements frequently removed from the front?
4. Is the required ordering LIFO or FIFO?
5. Are both ends accessed frequently?
6. Is the data sorted?
7. Is priority more important than arrival order?
8. Is the capacity bounded?
9. Is the input potentially very large or untrusted?
10. Is the application single-threaded or concurrent?
11. Is memory usage a significant constraint?
12. Which operation dominates the workload?

The dominant operation pattern should guide the final selection.

## Important distinctions

### Array versus list

A traditional array generally emphasizes fixed-size, indexed, homogeneous storage.

A Python list is a dynamic array abstraction designed for general-purpose Python objects.

### Stack versus list

A list is a concrete sequence implementation.

A stack is an abstract behavior based on LIFO ordering.

A list can implement a stack, but a stack can also be implemented using other structures.

### Queue versus deque

A queue describes FIFO behavior.

A deque describes a concrete double-ended structure.

A deque can implement a queue, but it can also implement a stack or support algorithms that need both endpoints.

### Queue versus priority queue

A queue processes by arrival order.

A priority queue processes according to priority.

Confusing these models can produce logically incorrect scheduling behavior even when the implementation is technically valid.

## Limitations and implementation boundaries

The script uses standard-library structures to focus on core concepts.

The custom dynamic array, circular queue, stack, and queue implementations are educational demonstrations. Python's built-in data structures are generally preferable in production unless there is a specific reason to create a custom implementation.

The expression parser is intentionally limited and should not be interpreted as a complete programming-language parser.

The benchmark results are environment-dependent. Timing numbers vary according to processor, operating system, Python version, workload, and system activity. The complexity difference between list front removal and deque front removal is more important than any individual measured timing.

## Practical implementation principles

A reliable data-structure implementation should:

- Define its supported operations clearly.
- Define behavior for empty and full states.
- Validate invalid parameters.
- Maintain internal invariants.
- Use appropriate exception types.
- Avoid unnecessary copying.
- Consider amortized complexity where dynamic storage is involved.
- Avoid expensive operations that conflict with the intended workload.
- Test boundary conditions.
- Apply resource limits to untrusted input.
- Select the simplest structure that satisfies the required behavior.

The central relationship demonstrated throughout the script is between **data organization, operation semantics, algorithmic complexity, and application requirements**. Arrays and lists provide ordered storage, stacks provide LIFO behavior, queues provide FIFO behavior, and deques provide efficient operations at both ends. These structures form the basis for many higher-level algorithms and software systems.
