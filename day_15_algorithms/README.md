# Algorithms: searching, sorting, and algorithmic thinking

## Topic introduction

Algorithms are precise procedures for transforming input into a desired result. Searching and sorting are two of the most fundamental algorithmic problems because they appear inside databases, operating systems, web applications, analytics systems, compilers, recommendation systems, networking software, and many other computing systems.

Searching answers questions such as:

- Does a value exist?
- Where does a value occur?
- What is the first or last occurrence?
- Which records fall within a range?
- What is the shortest path between two nodes?

Sorting rearranges data according to an ordering rule. A sorted representation can make later operations substantially faster because algorithms such as binary search depend on ordered data.

Algorithmic thinking goes beyond knowing individual algorithms. It involves translating a problem into precise operations, identifying constraints, choosing appropriate data structures, reasoning about correctness, analyzing complexity, and understanding the trade-offs between competing approaches.

The three implementations in this project approach these ideas from different programming perspectives:

- Python emphasizes readable algorithm implementations, experimentation, validation, and high-level data structures.
- JavaScript demonstrates algorithms in a language commonly used for application and browser development, including asynchronous processing and JavaScript collection types.
- C++ develops an industry-style product catalog system where algorithm selection, data structures, memory behavior, validation, and performance are considered together.

## Fundamental terminology

### Algorithm

An algorithm is a finite, well-defined sequence of operations for solving a problem.

A useful algorithm normally has:

- clearly defined inputs
- clearly defined outputs
- deterministic or explicitly controlled behavior
- finite execution
- well-defined operations
- correctness requirements

For example, linear search examines elements one by one until it finds a target or reaches the end of the collection.

### Input

Input is the data supplied to an algorithm.

For a search algorithm, the input may be:

- an array of numbers
- strings
- records
- graph nodes
- database records

### Output

Output is the result produced by an algorithm.

A search algorithm may return an index, a Boolean result, a record, or a path.

### Data structure

A data structure organizes data so that operations can be performed efficiently.

Important structures demonstrated in this project include:

- arrays and vectors
- lists
- hash maps
- sets
- queues
- heaps
- graphs
- sorted arrays

Algorithm and data structure choices are closely related. A poor data structure can force an otherwise simple operation to scan a large collection repeatedly.

### Correctness

An algorithm is correct when it produces the required result for every valid input under its defined assumptions.

For example, ordinary binary search assumes sorted input. If the input is not sorted, the algorithm's reasoning no longer applies.

### Invariant

An invariant is a condition that remains true during an algorithm's execution.

Binary search commonly maintains an invariant that, if the target exists, it remains inside the current search interval.

Loop invariants are useful when proving correctness.

## Algorithmic thinking

A practical algorithmic design process is:

1. Define the problem precisely.
2. Define the required output.
3. Identify constraints.
4. Analyze the characteristics of the input.
5. Select suitable data structures.
6. Design a candidate algorithm.
7. Establish why it is correct.
8. Analyze time complexity.
9. Analyze space complexity.
10. Test normal, boundary, and adversarial cases.
11. Measure performance when real-world data makes it necessary.
12. Reconsider the design if the constraints change.

The same problem can have several valid solutions with very different performance characteristics.

For example, searching for one item in an unsorted array can require `O(n)` time. If the data is sorted, binary search can reduce the search to `O(log n)`. If an exact-key hash index can be maintained, expected lookup can approach `O(1)`.

The improvement does not come from making the same loop faster. It comes from changing the representation and algorithm.

## Time complexity

Time complexity describes how an algorithm's running work grows as input size increases.

Common complexity classes include:

| Complexity | General interpretation |
|---|---|
| `O(1)` | Constant time |
| `O(log n)` | Logarithmic growth |
| `O(n)` | Linear growth |
| `O(n log n)` | Common efficient sorting complexity |
| `O(n²)` | Quadratic growth |
| `O(2ⁿ)` | Exponential growth |
| `O(n!)` | Factorial growth |

Complexity describes growth rather than exact wall-clock time.

An `O(n)` algorithm can still be slower than an `O(n log n)` algorithm for a small input if its constant factors are much larger. For sufficiently large inputs, asymptotic behavior becomes increasingly important.

## Space complexity

Space complexity describes additional memory requirements as input grows.

Examples in this project include:

- linear search using `O(1)` auxiliary space
- iterative binary search using `O(1)` auxiliary space
- merge sort using additional `O(n)` storage
- breadth-first search using `O(V)` storage for visited nodes and the queue

Input storage and auxiliary storage should be distinguished when analyzing memory requirements.

## Best, average, and worst cases

An algorithm can behave differently for different inputs of the same size.

Linear search:

- Best case: target is first, `O(1)`
- Worst case: target is absent or last, `O(n)`

Insertion sort:

- Best case: nearly sorted input, approximately `O(n)`
- Average case: `O(n²)`
- Worst case: reverse-sorted input, `O(n²)`

Quicksort:

- Average case: `O(n log n)`
- Worst case: `O(n²)`

Worst-case analysis is especially important in systems where predictable behavior matters.

## Searching algorithms

### Linear search

Linear search examines elements sequentially.

The Python implementation is `linear_search`, the JavaScript implementation is `linearSearch`, and the C++ implementation is `linearSearch`.

Conceptually:

`first element -> second element -> third element -> ...`

No ordering requirement exists.

Its main advantage is simplicity. Its main limitation is that the search can require examination of every element.

For an array containing one million elements, an unsuccessful search may require approximately one million comparisons.

### Binary search

Binary search requires sorted data.

Instead of examining every element, it examines the middle of the current interval and eliminates half of the remaining possibilities.

For an input containing `n` elements, the number of iterations grows logarithmically.

The core pattern is:

- calculate the middle
- compare the middle value with the target
- discard the impossible half
- repeat

The implementation uses the safe midpoint expression:

`left + (right - left) // 2`

in Python and:

`left + (right - left) / 2`

using integer division in C++ and JavaScript.

This form avoids a potential integer overflow that can occur in languages with bounded integer arithmetic when using `left + right` directly.

### Binary-search precondition

Binary search is not a general replacement for linear search.

The collection must satisfy the ordering assumption.

For example, searching `[10, 2, 8, 4]` with ordinary binary search is invalid because the collection is not sorted.

The cost of obtaining and maintaining sorted data must also be considered.

If data changes frequently, repeatedly sorting it merely to perform occasional searches may be worse than scanning it.

### First and last occurrence

A normal binary search can return any matching occurrence when duplicates exist.

The project also implements boundary searches:

- `lower_bound` or `lowerBound`
- `upper_bound` or `upperBound`
- first occurrence
- last occurrence
- duplicate counting

For sorted data `[1, 2, 2, 2, 3, 4]`, the first `2` occurs at index `1`, and the position after the final `2` is index `4`.

Therefore:

`count = upper_bound(target) - lower_bound(target)`

This technique is important because it solves more than simple membership testing.

### Searching a range

If values are sorted, binary search can locate the boundary of a range efficiently.

The Python product catalog maintains products ordered by price and uses `bisect` to find products up to a maximum price.

The JavaScript and C++ implementations reproduce the same algorithmic idea with explicit boundary searches.

This is a common pattern in database indexes and ordered in-memory structures.

## Hash-based searching

Hash tables provide a different approach to searching.

Python's `dict`, JavaScript's `Map`, and C++'s `unordered_map` can associate a key with a value.

The product catalog uses product IDs as keys.

Conceptually:

`product ID -> product record`

Expected lookup is approximately `O(1)` under normal hashing assumptions.

This is fundamentally different from binary search:

| Property | Binary search | Hash lookup |
|---|---|---|
| Main structure | Sorted sequence | Hash table |
| Expected lookup | `O(log n)` | Approximately `O(1)` |
| Ordering | Required | Not required |
| Range queries | Excellent with sorted data | Usually not directly supported |
| Exact-key lookup | Very good | Excellent |
| Ordered traversal | Natural | Not the primary purpose |

Hash tables require additional memory and depend on good hashing and collision handling.

They are particularly useful for exact-key lookups.

## Interpolation search

Interpolation search is included in the Python implementation.

Instead of always selecting the middle, it estimates the likely position based on the target's value relative to the endpoints.

It can perform very well on uniformly distributed numeric data and can approach `O(log log n)` behavior under suitable conditions.

Its worst case can be `O(n)`.

This illustrates an important algorithmic principle: an algorithm can outperform another under specific input assumptions while being worse under other distributions.

## Sorting algorithms

### Bubble sort

Bubble sort compares neighboring elements and swaps them when they are out of order.

The implementation includes early termination. If an entire pass makes no swaps, the input is already sorted.

Complexity:

- Best: `O(n)`
- Average: `O(n²)`
- Worst: `O(n²)`

Bubble sort is mainly valuable educationally. It is rarely the appropriate production choice for large collections.

### Selection sort

Selection sort finds the smallest remaining value and places it into the next position.

Complexity:

- Best: `O(n²)`
- Average: `O(n²)`
- Worst: `O(n²)`

It performs a relatively small number of swaps, which can matter when writes are unusually expensive.

### Insertion sort

Insertion sort maintains a sorted prefix and inserts each new element into its correct position.

Complexity:

- Best: `O(n)`
- Average: `O(n²)`
- Worst: `O(n²)`

It is useful for:

- small collections
- nearly sorted data
- incremental insertion into an ordered region

Many high-performance sorting systems use insertion sort internally for small partitions because its overhead is low.

### Merge sort

Merge sort uses divide and conquer.

The collection is divided into smaller parts, the parts are recursively sorted, and sorted parts are merged.

The recurrence is:

`T(n) = 2T(n/2) + O(n)`

which gives:

`O(n log n)`

worst-case time.

The implementation uses an auxiliary array for merging.

Merge sort has predictable complexity and can be stable.

Its principal trade-off is additional memory for the common array implementation.

### Quicksort

Quicksort partitions data around a pivot and recursively processes the partitions.

Average complexity is `O(n log n)`, while the worst case is `O(n²)`.

Pivot selection strongly influences behavior.

Poor pivot choices can repeatedly create highly unbalanced partitions.

The Python implementation uses randomized pivot selection and three-way partitioning. The JavaScript implementation uses three partitions:

- values smaller than the pivot
- values equal to the pivot
- values greater than the pivot

Three-way partitioning is useful when many duplicate values exist.

### Heap sort

Heap sort uses a binary heap.

Its complexity is:

- Best: `O(n log n)`
- Average: `O(n log n)`
- Worst: `O(n log n)`

A standard in-place implementation can use `O(1)` auxiliary space apart from the input array.

The Python demonstration uses `heapq`, which is intentionally simple and creates a separate heap representation. The C++ implementation uses standard heap operations.

This distinction illustrates an important engineering point: an algorithm's theoretical properties and a particular implementation's memory behavior are not always identical.

## Non-comparison sorting

Comparison sorting algorithms obtain ordering information by comparing elements.

Counting sort and radix sort exploit properties of the values instead.

### Counting sort

Counting sort stores the number of occurrences of each value.

For `n` elements and value range `k`, its complexity is approximately:

`O(n + k)`

It can be extremely efficient when `k` is small.

It becomes inappropriate when values are very sparse.

For example, sorting `[1, 10,000,000]` with a simple counting array would require an enormous range despite having only two values.

The implementations explicitly reject excessively large ranges.

### Radix sort

Radix sort processes digits or other fixed-width components.

The Python implementation handles signed integers by separating negative and non-negative values.

Radix sorting illustrates that `O(n log n)` is not a universal lower bound for all sorting problems. The comparison-sorting lower bound applies to comparison-based sorting models, while algorithms exploiting additional structure can use different complexity bounds.

## Stability

A stable sorting algorithm preserves the relative order of records that compare equal.

Suppose the original records are:

`Asha, score 88`

`Meera, score 88`

If sorting only by score, a stable algorithm keeps Asha before Meera.

Stability matters when sorting records using multiple criteria.

Python's built-in sorting is stable, and the examples demonstrate key-based ordering.

The merge operations also deliberately choose the left element when two values compare equally, preserving stability.

## In-place algorithms

An in-place algorithm performs its main transformation using limited additional memory.

Insertion sort, selection sort, and traditional heap sort can be implemented with constant auxiliary space.

Merge sort normally needs additional storage for array merging.

"In-place" does not necessarily mean zero additional memory. Variables, recursion stacks, temporary objects, and implementation details still consume resources.

## Divide and conquer

Divide and conquer separates a problem into smaller subproblems.

The general pattern is:

1. Divide.
2. Solve smaller instances.
3. Combine the results.

Merge sort is the clearest example.

Binary search also follows the divide-and-conquer idea because every comparison eliminates half of the remaining search interval.

Divide and conquer is powerful when the subproblems have manageable relationships and the combination step is efficient.

## Recursion

Recursion occurs when a function calls itself on a smaller version of the problem.

Merge sort and recursive binary search are examples.

A recursive algorithm needs:

- a base case
- progress toward that base case
- correct combination or return behavior

The Python and JavaScript implementations also include naive Fibonacci to illustrate poor recursive design.

Naive Fibonacci repeatedly solves the same subproblems and has exponential growth.

Dynamic programming avoids this repeated work.

## Dynamic programming

Dynamic programming is appropriate when a problem contains overlapping subproblems and useful reusable results.

The dynamic Fibonacci implementation stores only the previous two values.

This reduces:

`O(2ⁿ)`

style naive recursive growth to:

`O(n)`

time with:

`O(1)`

additional space.

Dynamic programming is not simply "using a loop." Its important idea is eliminating repeated computation by exploiting problem structure.

## Greedy algorithms

A greedy algorithm makes the best local decision according to a defined rule.

The activity-selection implementation sorts activities by finishing time and repeatedly chooses the next compatible activity.

For the classic activity-selection problem, this greedy rule produces an optimal maximum-cardinality schedule.

Greedy methods require proof or strong reasoning about why local choices lead to a globally valid solution.

A greedy strategy that works for one problem does not automatically work for another.

## Two-pointer technique

The two-pointer algorithm operates on a sorted sequence using two positions.

The product-independent example searches for two numbers whose sum equals a target.

For each step:

- if the sum is too small, move the left pointer forward
- if the sum is too large, move the right pointer backward
- if the sum matches, return the pair

The algorithm runs in `O(n)` time after sorting.

A brute-force approach would examine every pair and require `O(n²)` time.

If sorting is not already available, the total complexity becomes `O(n log n)` because sorting dominates.

## Binary search over the answer space

Binary search is not limited to finding an existing array element.

The integer square-root implementations demonstrate binary search over possible answers.

For a non-negative integer `N`, the algorithm searches for the largest integer `x` satisfying:

`x² <= N`

This is an important form of algorithmic thinking.

Instead of asking:

"Where is this value in the array?"

the algorithm asks:

"Is this candidate answer feasible?"

If feasibility is monotonic, binary search may be applicable.

## Selection algorithms

Sometimes complete sorting is unnecessary.

If only the third-smallest element is needed, fully sorting the collection may perform unnecessary work.

Quickselect can find the `k`-th smallest element with expected `O(n)` time.

This represents a broader principle:

> Solve exactly the problem that is required rather than performing unnecessary computation.

Selection algorithms are useful for:

- medians
- percentiles
- top-k problems
- threshold selection
- ranking systems

## Graph searching

Graphs represent relationships between entities.

The project includes:

- breadth-first search
- depth-first search

### Breadth-first search

BFS explores nodes in layers.

In an unweighted graph, BFS can find a shortest path in terms of number of edges.

Complexity:

`O(V + E)`

where:

- `V` is the number of vertices
- `E` is the number of edges

The implementation uses a queue and a parent mapping to reconstruct the path.

### Depth-first search

DFS explores deeply before backtracking.

It is useful for:

- connectivity
- cycle-related reasoning
- traversal
- component discovery
- backtracking problems

Its graph traversal complexity is also:

`O(V + E)`

The practical behavior and memory access pattern differ from BFS.

## C++ product catalog case study

The C++ implementation models a small product search and recommendation system.

Each product contains:

- ID
- name
- category
- price
- stock
- rating

The system maintains multiple representations because no single data structure is optimal for every query.

### Product ID index

An `unordered_map<int, size_t>` maps product IDs to positions.

This provides expected constant-time exact-key lookup.

The cost is additional memory.

### Name index

A second hash index supports case-insensitive exact name lookup.

This demonstrates a common production technique: maintaining multiple indexes when different query patterns need different access paths.

### Price ordering

Products are stored in a separate price order.

This makes price range queries efficient.

A binary search locates the first product whose price exceeds the requested maximum.

If there are `n` products and `k` products must be returned:

- boundary search: `O(log n)`
- result construction: `O(k)`

Therefore the complete operation is approximately:

`O(log n + k)`

This distinction is important. Finding the boundary can be fast, but returning many results still requires work proportional to the number of results.

## Recommendation algorithm

The product catalog filters products by:

- category
- maximum price
- availability

Candidates are then ranked.

The demonstration uses a simple score based on:

- product rating
- price

The formula is not a universal recommendation rule. It demonstrates the separation between:

1. candidate filtering
2. scoring
3. ranking
4. limiting the output

In production systems, ranking rules may incorporate many additional business and technical constraints.

## Why multiple indexes matter

Suppose a catalog contains ten million products.

A full linear scan for every product-ID lookup would scale poorly.

An ID hash index can make exact lookup much faster.

A price-sorted index can support range queries.

A category-oriented structure can improve category filtering.

The system therefore spends additional memory and preprocessing time to reduce query latency.

This is a central algorithmic trade-off:

`preprocessing + memory -> faster queries`

The correct balance depends on:

- read frequency
- write frequency
- memory limits
- latency requirements
- data size
- consistency requirements

## Searching versus sorting

Sorting and searching are often connected.

Sorting has an upfront cost but can improve subsequent operations.

Suppose an unsorted collection contains `n` records.

Repeated linear searches may cost approximately:

`O(qn)`

for `q` searches.

If the data is sorted once:

`O(n log n)`

and then searched `q` times using binary search:

`O(n log n + q log n)`

For sufficiently large `q`, the preprocessing cost can be justified.

If data changes constantly and searches are rare, sorting may not be worthwhile.

This is an example of amortized algorithmic reasoning.

## Python implementation

The Python script provides a broad educational implementation.

It demonstrates:

- linear search
- iterative binary search
- recursive binary search
- binary-search boundaries
- interpolation search
- bubble sort
- selection sort
- insertion sort
- merge sort
- quicksort
- heaps
- counting sort
- radix sort
- hash lookup
- two-pointer search
- binary search over an answer space
- greedy activity selection
- dynamic programming
- Quickselect
- BFS
- DFS
- stable key-based sorting
- validation
- performance measurement
- product catalog indexing

Python's standard library also illustrates production-oriented abstractions such as `dict`, `bisect`, `heapq`, and `sorted`.

The main benefit of the Python implementation is that the algorithmic structure remains easy to inspect.

## JavaScript implementation

The JavaScript implementation emphasizes application-oriented behavior.

It demonstrates:

- array-based searching
- custom sorting
- JavaScript comparators
- `Map`
- `Set`
- binary-search boundaries
- two-pointer processing
- greedy selection
- dynamic programming
- BFS
- DFS
- a product catalog class
- asynchronous data processing
- validation
- benchmarking

JavaScript's `Array.prototype.sort()` requires particular attention because the comparator determines numeric ordering.

For numeric ascending order, the appropriate comparator is conceptually:

`(a, b) => a - b`

Without a numeric comparator, JavaScript's default sorting behavior treats elements as strings for comparison.

The implementation also shows why copying an array before sorting can be important when mutation is undesirable.

The asynchronous example demonstrates that algorithmic processing and data acquisition can be separated. An application may obtain data asynchronously while applying an ordinary search algorithm after the data arrives.

## C++ implementation

The C++ implementation focuses on an industry-style system.

It demonstrates:

- vectors
- hash maps
- hash sets
- queues
- classes
- validation
- sorting
- binary search
- range searching
- graph traversal
- ranking
- exception handling
- performance measurement
- standard-library algorithms

The `ProductCatalog` class separates:

- product storage
- ID indexing
- name indexing
- price ordering
- filtering
- ranking
- result generation

This design makes the algorithmic decisions visible at the system level rather than treating algorithms as isolated functions.

C++ also makes memory and object-copying behavior more explicit than Python or JavaScript.

## Important distinctions

### Search algorithm versus index

A search algorithm operates on a representation of data.

An index is an additional structure created to accelerate specific queries.

A database index is therefore not simply another search loop. It changes the data-access strategy.

### Stable versus unstable sorting

Stable sorting preserves the relative order of equivalent records.

Unstable sorting may reorder equivalent records.

Stability matters when multiple sorting operations or secondary criteria are involved.

### In-place versus out-of-place

In-place algorithms use limited additional memory for transformation.

Out-of-place approaches create additional structures.

The best choice depends on memory limits, implementation complexity, stability requirements, and performance.

### Comparison sort versus non-comparison sort

Comparison sorts derive ordering through comparisons.

Counting and radix sorting exploit additional information about the data.

Non-comparison approaches can outperform comparison sorting under appropriate constraints but are not universally applicable.

### Worst-case versus expected complexity

Hash lookup is commonly described as expected `O(1)`, not an unconditional mathematical guarantee under every possible condition.

Quicksort is commonly described as average `O(n log n)` but can have `O(n²)` worst-case behavior.

Production engineering must consider both typical and pathological inputs.

## Edge cases

Algorithm implementations should explicitly consider:

- empty collections
- one-element collections
- duplicate values
- already sorted data
- reverse-sorted data
- absent search targets
- negative numbers
- extremely large numeric ranges
- invalid indices
- invalid limits
- invalid prices
- unavailable products
- duplicate product IDs
- duplicate product names
- invalid ratings
- disconnected graph nodes
- cycles in graphs
- large inputs
- integer overflow

The implementations intentionally include validation for several of these cases.

## Common mistakes

### Applying binary search to unsorted data

Binary search depends on ordering. Without sorted input, its elimination logic is invalid.

### Forgetting duplicate behavior

A standard binary search returning one matching index is not the same as finding the first occurrence, last occurrence, or number of occurrences.

### Ignoring preprocessing cost

Sorting data once may improve future queries, but the sorting cost must be included in the system-level analysis.

### Using counting sort on a huge sparse range

Counting sort's complexity depends on the numeric range as well as the number of elements.

### Assuming quicksort is always `O(n log n)`

Poor pivot choices can produce quadratic behavior.

### Using the wrong JavaScript sort comparator

JavaScript numeric sorting should use an explicit numeric comparator.

### Mutating input unintentionally

JavaScript's `sort()` modifies the array. Copying the array first is appropriate when callers expect immutable input.

### Treating hash lookup as universally constant time

Hash-table lookup is expected to be approximately constant time under normal assumptions. Collisions, implementation details, resizing, and poor hashing can affect actual behavior.

### Optimizing before understanding constraints

A more complicated algorithm is not automatically better.

The appropriate algorithm depends on:

- input size
- query frequency
- mutation frequency
- memory
- correctness requirements
- latency requirements
- maintainability

## Limitations

The implementations are educational and intentionally self-contained.

The product catalog uses in-memory data rather than a persistent database.

Real production systems would need to address:

- persistence
- concurrent updates
- transaction consistency
- distributed indexing
- caching
- fault tolerance
- authorization
- observability
- deployment
- data synchronization
- schema evolution

The ranking function is deliberately simple and should not be interpreted as a complete recommendation system.

The benchmark results are hardware-dependent. They are useful for observing relative behavior, not for establishing universal performance numbers.

## Performance considerations

Algorithmic complexity is necessary but not sufficient for performance engineering.

Real execution can also depend on:

- CPU cache locality
- memory allocation
- branch prediction
- object representation
- interpreter or compiler behavior
- garbage collection
- recursion overhead
- vector growth
- hash-table resizing
- input distribution
- operating-system scheduling

C++ often provides greater control over memory representation and allocation.

Python can provide very concise high-level implementations, with optimized built-in operations often outperforming manually implemented loops.

JavaScript engines perform sophisticated runtime optimization, while asynchronous execution affects application architecture even when the underlying algorithm remains synchronous.

## Security considerations

Algorithms themselves can create security-relevant risks when applied to untrusted input.

Examples include:

- deliberately adversarial inputs causing poor quicksort behavior
- excessive memory allocation from an inappropriate counting range
- oversized inputs causing resource exhaustion
- uncontrolled recursion depth
- malformed identifiers or records
- denial-of-service through expensive ranking or search operations

Production systems should validate input size and ranges before allocating resources.

Hash-based systems should also consider adversarial key distributions where relevant.

Algorithmic complexity can therefore be a security concern, not merely a performance concern.

## Implementation considerations

A production implementation should distinguish between:

- correctness
- asymptotic complexity
- constant factors
- memory usage
- concurrency
- persistence
- observability
- failure handling

An algorithm should be selected because it satisfies the complete set of system constraints.

For example, a theoretically efficient algorithm may still be unsuitable if its memory usage exceeds the available budget.

Likewise, a simple linear scan may be the correct choice for a collection containing only a few dozen records.

## Real-world applications

Searching and sorting algorithms appear in:

- database indexing
- search engines
- operating systems
- compilers
- file systems
- recommendation systems
- financial applications
- inventory management
- logistics
- networking
- geographic systems
- analytics platforms
- fraud detection
- scheduling
- resource allocation
- data processing pipelines
- graph-based applications

The same algorithmic concepts often appear indirectly inside higher-level software.

For example, a developer may call a library sort function without implementing quicksort or merge sort manually. Understanding the underlying algorithm remains useful because it helps explain performance, stability, memory usage, and appropriate use cases.

## Algorithm comparison

| Algorithm | Typical purpose | Best | Average | Worst | Main requirement or trade-off |
|---|---|---:|---:|---:|---|
| Linear search | Search unsorted data | `O(1)` | `O(n)` | `O(n)` | No ordering required |
| Binary search | Exact search | `O(1)` | `O(log n)` | `O(log n)` | Requires sorted data |
| Bubble sort | Educational/simple sorting | `O(n)` | `O(n²)` | `O(n²)` | Very inefficient at scale |
| Selection sort | Simple sorting | `O(n²)` | `O(n²)` | `O(n²)` | Few swaps |
| Insertion sort | Small/nearly sorted data | `O(n)` | `O(n²)` | `O(n²)` | Excellent for small inputs |
| Merge sort | Predictable sorting | `O(n log n)` | `O(n log n)` | `O(n log n)` | Additional memory |
| Quicksort | General sorting | `O(n log n)` | `O(n log n)` | `O(n²)` | Pivot selection matters |
| Heap sort | Predictable sorting | `O(n log n)` | `O(n log n)` | `O(n log n)` | Heap operations |
| Counting sort | Bounded integers | `O(n+k)` | `O(n+k)` | `O(n+k)` | Depends on value range |
| Radix sort | Structured integers/keys | `O(d(n+b))` | `O(d(n+b))` | Depends on implementation | Requires suitable representation |
| Hash lookup | Exact-key lookup | Expected `O(1)` | Expected `O(1)` | Implementation-dependent | Additional memory |
| BFS | Unweighted shortest path | `O(V+E)` | `O(V+E)` | `O(V+E)` | Uses queue and visited state |
| DFS | Graph traversal | `O(V+E)` | `O(V+E)` | `O(V+E)` | Uses traversal stack/recursion |

## Relationship between algorithms and data structures

An important lesson from the project is that algorithms cannot be evaluated independently from data structures.

For example:

`unsorted vector + linear search`

and:

`sorted vector + binary search`

are different systems even though both answer a search question.

Likewise:

`unordered_map + exact-key lookup`

and:

`sorted array + binary search`

have different performance characteristics and support different query patterns.

A useful engineering question is therefore not merely:

"Which algorithm is fastest?"

A better question is:

"Which algorithm and data representation best satisfy the workload and constraints?"

## Testing strategy

The implementations validate algorithms against known expected results.

Useful test categories include:

- empty input
- single-element input
- duplicate values
- negative values
- already sorted input
- reverse-sorted input
- missing search values
- boundary targets
- invalid parameters
- large ranges
- invalid product records

For sorting algorithms, the implementations compare results against the language's trusted standard sorting behavior.

This is a practical example of differential testing: an implementation is checked against a known-correct reference behavior.

## Production perspective

A production algorithmic system normally requires more than an efficient algorithm.

A complete design considers:

- workload
- data volume
- latency targets
- throughput
- memory limits
- concurrency
- failure behavior
- persistence
- data consistency
- security
- monitoring
- maintainability

The C++ product catalog illustrates this transition from an isolated algorithm to a system design.

The catalog uses multiple indexes because different queries require different access patterns.

That principle extends to large systems where databases, caches, search indexes, message queues, and distributed services are selected according to workload characteristics.

## Core algorithmic lessons

Searching demonstrates how assumptions about data organization change complexity.

Sorting demonstrates how algorithm design involves trade-offs between speed, memory, stability, predictability, and applicability.

Binary search demonstrates how ordered information can dramatically reduce search work.

Hashing demonstrates the value of indexing for exact-key access.

Divide and conquer demonstrates how large problems can be decomposed into smaller problems.

Greedy algorithms demonstrate the importance of proving that a local decision rule is globally appropriate.

Dynamic programming demonstrates how recognizing repeated subproblems can eliminate unnecessary computation.

Graph traversal demonstrates that the meaning of "search" extends beyond arrays and records into relationships between entities.

The central engineering principle is to match the algorithm and data structure to the actual problem constraints rather than selecting an algorithm based solely on its theoretical complexity.
