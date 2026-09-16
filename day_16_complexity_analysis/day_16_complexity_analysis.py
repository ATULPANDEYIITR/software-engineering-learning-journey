"""
COMPLEXITY ANALYSIS: BIG-O, TIME COMPLEXITY, AND SPACE COMPLEXITY

A standalone study program progressing from beginner concepts to advanced
algorithmic analysis.

Run:
    python complexity_analysis.py

The examples use only Python's standard library.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import log2, sqrt
from random import Random
from time import perf_counter
from typing import Iterable, Sequence


# ============================================================================
# 1. FUNDAMENTAL TERMINOLOGY
# ============================================================================

def print_section(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_complexity(name: str, time_complexity: str, space_complexity: str) -> None:
    print(f"{name:<38} Time: {time_complexity:<15} Space: {space_complexity}")


def constant_time_access(values: Sequence[int], index: int) -> int:
    # Array/list indexing uses direct address calculation.
    # The operation does not grow with n, so it is O(1).
    return values[index]


def linear_search(values: Sequence[int], target: int) -> int:
    # In the worst case every element is inspected.
    # Time: O(n), auxiliary space: O(1).
    for index, value in enumerate(values):
        if value == target:
            return index
    return -1


def sum_values(values: Sequence[int]) -> int:
    # One pass through n values.
    # Time: O(n), auxiliary space: O(1).
    total = 0
    for value in values:
        total += value
    return total


def nested_pairs(values: Sequence[int]) -> int:
    # Each element is paired with every other element.
    # Approximately n*n iterations occur.
    # Time: O(n^2), auxiliary space: O(1).
    count = 0
    for _ in values:
        for _ in values:
            count += 1
    return count


def logarithmic_count(n: int) -> int:
    # Halving n repeatedly requires logarithmically many iterations.
    # Time: O(log n), auxiliary space: O(1).
    count = 0
    while n > 1:
        n //= 2
        count += 1
    return count


def polynomial_demo(n: int) -> int:
    # Three nested loops produce O(n^3) work.
    total = 0
    for _ in range(n):
        for _ in range(n):
            for _ in range(n):
                total += 1
    return total


def demonstrate_basic_classes() -> None:
    print_section("1. Common complexity classes")

    print_complexity("List indexing", "O(1)", "O(1)")
    print_complexity("Linear search", "O(n)", "O(1)")
    print_complexity("Binary search", "O(log n)", "O(1)")
    print_complexity("Single pass", "O(n)", "O(1)")
    print_complexity("Two nested loops", "O(n^2)", "O(1)")
    print_complexity("Three nested loops", "O(n^3)", "O(1)")
    print_complexity("Merge sort", "O(n log n)", "O(n)")
    print_complexity("Hash-table lookup", "O(1) average", "O(n)")
    print_complexity("Naive Fibonacci", "O(2^n)", "O(n)")
    print_complexity("Matrix multiplication", "O(n^3)", "O(n^2)")

    values = [10, 20, 30, 40, 50]
    print("\nExamples:")
    print("constant_time_access:", constant_time_access(values, 2))
    print("linear_search:", linear_search(values, 40))
    print("sum_values:", sum_values(values))
    print("nested_pairs:", nested_pairs(values))
    print("logarithmic_count(100):", logarithmic_count(100))


# ============================================================================
# 2. INPUT SIZE AND GROWTH
# ============================================================================

def demonstrate_growth_rates() -> None:
    print_section("2. Growth rates")

    n = 16
    growth = {
        "1": 1,
        "log2(n)": log2(n),
        "n": n,
        "n log2(n)": n * log2(n),
        "n^2": n**2,
        "n^3": n**3,
        "2^n": 2**n,
        "n!": 1,
    }

    # Compute factorial separately to avoid an unnecessary dependency.
    factorial = 1
    for value in range(1, n + 1):
        factorial *= value
    growth["n!"] = factorial

    for name, value in growth.items():
        print(f"{name:<12}: {value}")

    print(
        "\nThe important idea is not the exact number of operations but how "
        "the amount of work grows as the input size grows."
    )


# ============================================================================
# 3. BIG-O, BIG-OMEGA, AND BIG-THETA
# ============================================================================

def demonstrate_asymptotic_notation() -> None:
    print_section("3. O, Ω, and Θ")

    print("Big-O: an asymptotic upper bound.")
    print("Big-Omega (Ω): an asymptotic lower bound.")
    print("Big-Theta (Θ): a tight asymptotic bound.")

    print("\nFor f(n) = 3n^2 + 10n + 50:")
    print("    f(n) is O(n^2)")
    print("    f(n) is Ω(n^2)")
    print("    f(n) is Θ(n^2)")

    print(
        "\nConstants and lower-order terms are normally ignored because "
        "asymptotic analysis focuses on growth for large n."
    )


# ============================================================================
# 4. BEST, AVERAGE, AND WORST CASE
# ============================================================================

def demonstrate_cases() -> None:
    print_section("4. Best-case, average-case, and worst-case analysis")

    values = list(range(1, 101))

    # Linear search:
    # Best case: target is first -> O(1)
    # Worst case: target is absent or last -> O(n)
    # Average case under a uniform successful-search model -> Θ(n).
    for target in (1, 50, 100, 101):
        index = linear_search(values, target)
        print(f"target={target:<3} index={index}")

    print("\nLinear search therefore has different case-specific costs:")
    print("Best case:    O(1)")
    print("Average case: Θ(n)")
    print("Worst case:   O(n)")


# ============================================================================
# 5. LOOP ANALYSIS
# ============================================================================

def loop_examples(n: int) -> tuple[int, int, int, int]:
    # Example A: O(n)
    linear = 0
    for _ in range(n):
        linear += 1

    # Example B: O(n^2)
    quadratic = 0
    for _ in range(n):
        for _ in range(n):
            quadratic += 1

    # Example C: O(n log n)
    nlogn = 0
    outer = n
    while outer > 0:
        inner = 1
        while inner < n:
            nlogn += 1
            inner *= 2
        outer -= 1

    # Example D: O(log n)
    logarithmic = 0
    value = n
    while value > 1:
        value //= 2
        logarithmic += 1

    return linear, quadratic, nlogn, logarithmic


def demonstrate_loop_analysis() -> None:
    print_section("5. Analyzing loops")

    results = loop_examples(16)
    print("O(n) iterations:       ", results[0])
    print("O(n^2) iterations:     ", results[1])
    print("O(n log n) iterations: ", results[2])
    print("O(log n) iterations:   ", results[3])

    print("\nRules:")
    print("- Sequential loops usually add: O(n) + O(n) = O(n).")
    print("- Nested independent loops usually multiply: O(n) * O(n) = O(n^2).")
    print("- A variable repeatedly doubled or halved often creates O(log n).")
    print("- A loop whose bound changes with another loop needs careful analysis.")


# ============================================================================
# 6. BINARY SEARCH
# ============================================================================

def binary_search(values: Sequence[int], target: int) -> int:
    # The sequence must be sorted.
    # Each iteration removes roughly half the remaining search space.
    # Time: O(log n), auxiliary space: O(1).
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


def demonstrate_binary_search() -> None:
    print_section("6. Binary search")

    values = list(range(0, 100, 2))
    for target in (0, 42, 98, 99):
        print(f"{target:>3} -> index {binary_search(values, target)}")

    print("\nRequirement: sorted input.")
    print("Time: O(log n)")
    print("Auxiliary space: O(1)")


# ============================================================================
# 7. SORTING AND DIVIDE AND CONQUER
# ============================================================================

def merge(left: list[int], right: list[int]) -> list[int]:
    result: list[int] = []
    i = j = 0

    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    result.extend(left[i:])
    result.extend(right[j:])
    return result


def merge_sort(values: Sequence[int]) -> list[int]:
    # Divide and conquer:
    # T(n) = 2T(n/2) + O(n), which gives O(n log n).
    # The merged output requires O(n) additional space.
    if len(values) <= 1:
        return list(values)

    middle = len(values) // 2
    left = merge_sort(values[:middle])
    right = merge_sort(values[middle:])
    return merge(left, right)


def insertion_sort(values: Sequence[int]) -> list[int]:
    # Best case: O(n) for already sorted input.
    # Average/worst case: O(n^2).
    # Space: O(1) auxiliary if performed in-place; this version creates a copy.
    result = list(values)

    for i in range(1, len(result)):
        current = result[i]
        j = i - 1

        while j >= 0 and result[j] > current:
            result[j + 1] = result[j]
            j -= 1

        result[j + 1] = current

    return result


def demonstrate_sorting() -> None:
    print_section("7. Sorting and divide and conquer")

    values = [9, 1, 7, 3, 5, 2, 8, 4, 6]
    print("Original:       ", values)
    print("Insertion sort: ", insertion_sort(values))
    print("Merge sort:     ", merge_sort(values))

    print("\nInsertion sort:")
    print("Best:    O(n)")
    print("Average: O(n^2)")
    print("Worst:   O(n^2)")

    print("\nMerge sort:")
    print("Best:    O(n log n)")
    print("Average: O(n log n)")
    print("Worst:   O(n log n)")


# ============================================================================
# 8. RECURSION
# ============================================================================

def factorial_recursive(n: int) -> int:
    if n < 0:
        raise ValueError("factorial is undefined for negative integers")
    if n in (0, 1):
        return 1
    return n * factorial_recursive(n - 1)


def factorial_iterative(n: int) -> int:
    if n < 0:
        raise ValueError("factorial is undefined for negative integers")

    result = 1
    for value in range(2, n + 1):
        result *= value
    return result


def demonstrate_recursion() -> None:
    print_section("8. Recursion and stack space")

    print("factorial_recursive(6):", factorial_recursive(6))
    print("factorial_iterative(6):", factorial_iterative(6))

    print("\nRecursive factorial:")
    print("Time: O(n)")
    print("Call-stack space: O(n)")

    print("\nIterative factorial:")
    print("Time: O(n)")
    print("Auxiliary space: O(1)")


# ============================================================================
# 9. EXPONENTIAL RECURSION AND DYNAMIC PROGRAMMING
# ============================================================================

def fibonacci_naive(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


@lru_cache(maxsize=None)
def fibonacci_memoized(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n <= 1:
        return n
    return fibonacci_memoized(n - 1) + fibonacci_memoized(n - 2)


def fibonacci_iterative(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")

    previous, current = 0, 1
    for _ in range(n):
        previous, current = current, previous + current
    return previous


def demonstrate_dynamic_programming() -> None:
    print_section("9. Exponential recursion versus dynamic programming")

    n = 20
    print("Naive Fibonacci:", fibonacci_naive(n))
    print("Memoized Fibonacci:", fibonacci_memoized(n))
    print("Iterative Fibonacci:", fibonacci_iterative(n))

    print("\nNaive Fibonacci:")
    print("Time: approximately O(2^n)")
    print("Space: O(n) recursion depth")

    print("\nMemoized Fibonacci:")
    print("Time: O(n)")
    print("Space: O(n) cache + recursion")

    print("\nIterative Fibonacci:")
    print("Time: O(n)")
    print("Auxiliary space: O(1)")


# ============================================================================
# 10. SPACE COMPLEXITY
# ============================================================================

def create_copy(values: Sequence[int]) -> list[int]:
    # Creates storage proportional to n.
    # Auxiliary space: O(n).
    return list(values)


def sum_without_copy(values: Sequence[int]) -> int:
    # Does not create a second n-sized collection.
    # Auxiliary space: O(1).
    total = 0
    for value in values:
        total += value
    return total


def demonstrate_space_complexity() -> None:
    print_section("10. Space complexity")

    values = list(range(10))
    copied = create_copy(values)

    print("Original:", values)
    print("Copy:    ", copied)
    print("copy-based operation: O(n) auxiliary space")
    print("streaming-style sum:  O(1) auxiliary space")

    print(
        "\nInput space is often separated from auxiliary space. "
        "An algorithm receiving an existing O(n) input does not automatically "
        "have O(n) auxiliary space."
    )


# ============================================================================
# 11. HASH TABLES
# ============================================================================

def frequency_table(values: Iterable[str]) -> dict[str, int]:
    # Dictionary insertion and lookup are O(1) average under normal hashing
    # assumptions, giving O(n) expected total time for n values.
    counts: dict[str, int] = {}

    for value in values:
        counts[value] = counts.get(value, 0) + 1

    return counts


def demonstrate_hashing() -> None:
    print_section("11. Hash-table complexity")

    words = ["red", "blue", "red", "green", "blue", "red"]
    counts = frequency_table(words)

    print("Words:", words)
    print("Counts:", counts)

    print("\nExpected dictionary lookup: O(1)")
    print("Expected n-item frequency construction: O(n)")
    print("Storage for n distinct values: O(n)")

    print(
        "\nHash-table performance depends on a good hash function and collision "
        "handling. Worst-case behavior can differ from expected behavior."
    )


# ============================================================================
# 12. GRAPH TRAVERSAL
# ============================================================================

Graph = dict[str, list[str]]


def breadth_first_search(graph: Graph, start: str) -> list[str]:
    # BFS visits each reachable vertex and each adjacency-list edge once.
    # Time: O(V + E), space: O(V).
    if start not in graph:
        return []

    queue = [start]
    visited = {start}
    order: list[str] = []
    head = 0

    while head < len(queue):
        current = queue[head]
        head += 1
        order.append(current)

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return order


def depth_first_search(graph: Graph, start: str) -> list[str]:
    # Iterative DFS also visits each reachable vertex and edge at most
    # a constant number of times.
    # Time: O(V + E), auxiliary space: O(V).
    if start not in graph:
        return []

    stack = [start]
    visited = set()
    order: list[str] = []

    while stack:
        current = stack.pop()

        if current in visited:
            continue

        visited.add(current)
        order.append(current)

        for neighbor in reversed(graph.get(current, [])):
            if neighbor not in visited:
                stack.append(neighbor)

    return order


def demonstrate_graph_complexity() -> None:
    print_section("12. Graph algorithms")

    graph: Graph = {
        "A": ["B", "C"],
        "B": ["A", "D", "E"],
        "C": ["A", "F"],
        "D": ["B"],
        "E": ["B", "F"],
        "F": ["C", "E"],
    }

    print("BFS:", breadth_first_search(graph, "A"))
    print("DFS:", depth_first_search(graph, "A"))

    print("\nAdjacency-list BFS: O(V + E)")
    print("Adjacency-list DFS: O(V + E)")


# ============================================================================
# 13. AMORTIZED ANALYSIS
# ============================================================================

def demonstrate_amortized_analysis() -> None:
    print_section("13. Amortized analysis")

    values: list[int] = []
    capacity = 0
    resizing_events = 0

    for value in range(32):
        if len(values) == capacity:
            # Dynamic arrays typically grow capacity geometrically.
            capacity = 1 if capacity == 0 else capacity * 2
            resizing_events += 1
        values.append(value)

    print("Elements inserted:", len(values))
    print("Capacity:", capacity)
    print("Resizes:", resizing_events)

    print(
        "\nA particular append may trigger O(n) copying during a resize, "
        "but geometric capacity growth makes append O(1) amortized."
    )


# ============================================================================
# 14. RECURRENCE RELATIONS
# ============================================================================

def demonstrate_recurrences() -> None:
    print_section("14. Recurrence relations")

    print("Binary search:")
    print("T(n) = T(n/2) + O(1)")
    print("Result: O(log n)")

    print("\nMerge sort:")
    print("T(n) = 2T(n/2) + O(n)")
    print("Result: O(n log n)")

    print("\nNaive Fibonacci:")
    print("T(n) = T(n-1) + T(n-2) + O(1)")
    print("Result: exponential growth")

    print(
        "\nThe Master Theorem is useful for recurrences of the form "
        "T(n) = aT(n/b) + f(n), with appropriate regularity conditions."
    )


# ============================================================================
# 15. MASTER THEOREM EXAMPLES
# ============================================================================

def demonstrate_master_theorem() -> None:
    print_section("15. Master Theorem examples")

    cases = [
        ("2T(n/2) + O(1)", "O(n)"),
        ("2T(n/2) + O(n)", "O(n log n)"),
        ("2T(n/2) + O(n^2)", "O(n^2)"),
        ("8T(n/2) + O(n^2)", "O(n^3)"),
    ]

    for recurrence, result in cases:
        print(f"{recurrence:<28} -> {result}")

    print(
        "\nThe theorem should not be applied mechanically to recurrences "
        "outside its assumptions."
    )


# ============================================================================
# 16. TWO-POINTER TECHNIQUE
# ============================================================================

def two_sum_sorted(values: Sequence[int], target: int) -> tuple[int, int] | None:
    # Because values are sorted, two pointers eliminate many candidate pairs.
    # Time: O(n), auxiliary space: O(1).
    left = 0
    right = len(values) - 1

    while left < right:
        current = values[left] + values[right]

        if current == target:
            return left, right
        if current < target:
            left += 1
        else:
            right -= 1

    return None


def demonstrate_two_pointers() -> None:
    print_section("16. Algorithmic optimization: two pointers")

    values = [1, 3, 4, 6, 8, 10, 13]
    print("Input:", values)
    print("Target 14:", two_sum_sorted(values, 14))
    print("Target 20:", two_sum_sorted(values, 20))

    print("\nBrute-force pair search: O(n^2)")
    print("Two-pointer search on sorted input: O(n)")


# ============================================================================
# 17. PREFIX SUM
# ============================================================================

def build_prefix_sums(values: Sequence[int]) -> list[int]:
    # Preprocessing costs O(n), and each subsequent range-sum query is O(1).
    prefix = [0]

    for value in values:
        prefix.append(prefix[-1] + value)

    return prefix


def range_sum(prefix: Sequence[int], left: int, right: int) -> int:
    # Sum of values in [left, right].
    if left < 0 or right < left or right + 1 >= len(prefix):
        raise IndexError("invalid inclusive range")
    return prefix[right + 1] - prefix[left]


def demonstrate_prefix_sums() -> None:
    print_section("17. Time-space trade-off: prefix sums")

    values = [2, 4, 6, 8, 10, 12]
    prefix = build_prefix_sums(values)

    print("Values:", values)
    print("Prefix:", prefix)
    print("Range [1, 4]:", range_sum(prefix, 1, 4))

    print("\nWithout preprocessing: each range sum can be O(n).")
    print("With prefix sums:")
    print("Preprocessing: O(n)")
    print("Each query:    O(1)")
    print("Extra space:   O(n)")


# ============================================================================
# 18. PERFORMANCE MEASUREMENT
# ============================================================================

def benchmark(function, argument, repetitions: int = 3) -> float:
    durations = []

    for _ in range(repetitions):
        start = perf_counter()
        function(argument)
        durations.append(perf_counter() - start)

    return min(durations)


def demonstrate_empirical_measurement() -> None:
    print_section("18. Theoretical complexity versus measurement")

    small = list(range(1_000))
    large = list(range(100_000))

    small_time = benchmark(sum_values, small)
    large_time = benchmark(sum_values, large)

    print(f"O(n) sum of 1,000 values:   {small_time:.8f} seconds")
    print(f"O(n) sum of 100,000 values: {large_time:.8f} seconds")

    print(
        "\nRuntime measurements depend on hardware, interpreter overhead, "
        "cache behavior, memory allocation, system load, and implementation."
    )
    print("Big-O describes asymptotic growth; it is not a stopwatch.")


# ============================================================================
# 19. EDGE CASES AND VALIDATION
# ============================================================================

def safe_binary_search(values: Sequence[int], target: int) -> int:
    if not isinstance(target, int):
        raise TypeError("target must be an integer")

    if any(values[i] > values[i + 1] for i in range(len(values) - 1)):
        raise ValueError("binary search requires sorted input")

    return binary_search(values, target)


def demonstrate_edge_cases() -> None:
    print_section("19. Edge cases and common mistakes")

    print("Empty linear search:", linear_search([], 5))
    print("Single-element search:", linear_search([5], 5))
    print("Missing binary-search value:", safe_binary_search([1, 3, 5], 4))

    try:
        safe_binary_search([3, 1, 2], 2)
    except ValueError as error:
        print("Invalid sortedness detected:", error)

    try:
        factorial_recursive(-1)
    except ValueError as error:
        print("Invalid factorial detected:", error)

    print("\nCommon mistakes:")
    print("- Forgetting whether input must be sorted.")
    print("- Treating nested loops as automatically O(n^2).")
    print("- Ignoring recursion-stack space.")
    print("- Confusing expected hash-table complexity with guaranteed worst-case.")
    print("- Measuring one execution and calling it complexity analysis.")
    print("- Keeping exact constants when asymptotic growth is the question.")
    print("- Ignoring the cost of sorting before using a sorted-input algorithm.")


# ============================================================================
# 20. ADVANCED COMPLEXITY CONCEPTS
# ============================================================================

def demonstrate_advanced_concepts() -> None:
    print_section("20. Advanced complexity concepts")

    concepts = {
        "Input complexity": "How cost depends on input size and structure.",
        "Auxiliary space": "Extra memory beyond the supplied input.",
        "Amortized complexity": "Average cost per operation over a sequence.",
        "Expected complexity": "Expected cost under a probabilistic model.",
        "Worst-case complexity": "Maximum cost among valid inputs of size n.",
        "Output-sensitive": "Cost depends partly on output size.",
        "Parameterized": "Cost is expressed using multiple parameters.",
        "In-place": "Uses very little additional storage.",
        "Stable sorting": "Equal-key records retain relative ordering.",
        "Lower bound": "A provable limit on required computational work.",
    }

    for name, definition in concepts.items():
        print(f"{name:<22}: {definition}")

    print("\nExamples of multiple parameters:")
    print("Graph traversal: O(V + E)")
    print("Matrix operation: often expressed using matrix dimensions.")
    print("String algorithms: may depend on text length and pattern length.")


# ============================================================================
# 21. COMPLEXITY COMPARISON TABLE
# ============================================================================

def demonstrate_algorithm_table() -> None:
    print_section("21. Algorithm comparison")

    rows = [
        ("Linear search", "O(1)", "O(n)", "O(n)", "O(1)"),
        ("Binary search", "O(1)", "O(log n)", "O(log n)", "O(1)"),
        ("Insertion sort", "O(n)", "O(n^2)", "O(n^2)", "O(1)"),
        ("Merge sort", "O(n log n)", "O(n log n)", "O(n log n)", "O(n)"),
        ("Hash lookup", "O(1)", "O(1) avg", "O(n)", "O(n) table"),
        ("BFS", "O(V+E)", "O(V+E)", "O(V+E)", "O(V)"),
        ("DFS", "O(V+E)", "O(V+E)", "O(V+E)", "O(V)"),
    ]

    header = (
        f"{'Algorithm':<18} {'Best':<13} {'Average':<15} "
        f"{'Worst':<15} {'Space'}"
    )
    print(header)
    print("-" * len(header))

    for row in rows:
        print(
            f"{row[0]:<18} {row[1]:<13} {row[2]:<15} "
            f"{row[3]:<15} {row[4]}"
        )


# ============================================================================
# 22. REAL-WORLD ENGINEERING TRADE-OFF
# ============================================================================

@dataclass
class SearchResult:
    index: int
    comparisons: int


def counted_linear_search(values: Sequence[int], target: int) -> SearchResult:
    comparisons = 0

    for index, value in enumerate(values):
        comparisons += 1
        if value == target:
            return SearchResult(index, comparisons)

    return SearchResult(-1, comparisons)


def demonstrate_tradeoffs() -> None:
    print_section("22. Real-world trade-offs")

    values = list(range(1_000_000))
    target = 999_999

    result = counted_linear_search(values, target)

    print("Linear-search comparisons:", result.comparisons)
    print("Time complexity: O(n)")
    print("Space complexity: O(1)")

    print(
        "\nA binary-search solution can reduce search work to O(log n), "
        "but it requires sorted data. If the data is frequently changing, "
        "the cost of maintaining sorted order may matter."
    )

    print(
        "\nA hash table can provide expected O(1) lookup but requires extra "
        "memory and depends on hashing and collision behavior."
    )


# ============================================================================
# 23. SECURITY AND COMPLEXITY
# ============================================================================

def demonstrate_security_considerations() -> None:
    print_section("23. Security considerations")

    print("- Avoid algorithms whose runtime can be forced into expensive cases.")
    print("- Validate input sizes before allocating large structures.")
    print("- Consider denial-of-service risks from pathological inputs.")
    print("- Be careful with recursive algorithms on attacker-controlled depth.")
    print("- Hash-table implementations should account for collision attacks.")
    print("- Cryptographic algorithms require security properties beyond Big-O.")
    print("- Constant-time behavior can matter for side-channel resistance.")
    print("- Complexity analysis does not prove an algorithm is secure.")

    print(
        "\nSecurity engineering may intentionally trade performance for "
        "bounded resource use, stronger validation, or resistance to attacks."
    )


# ============================================================================
# 24. PRODUCTION CHECKLIST
# ============================================================================

def production_checklist() -> None:
    print_section("24. Production analysis checklist")

    checklist = [
        "Define the input size parameters.",
        "Identify the dominant operation.",
        "Analyze loops and recursion.",
        "Account for data-structure operations.",
        "Separate best, expected, and worst cases.",
        "Analyze auxiliary memory.",
        "Check preprocessing costs.",
        "Check output-size costs.",
        "Consider realistic constants and hardware.",
        "Benchmark representative workloads.",
        "Test adversarial and boundary inputs.",
        "Check memory limits and latency requirements.",
        "Evaluate concurrency and contention when applicable.",
        "Consider security-related resource exhaustion.",
    ]

    for item in checklist:
        print(f"- {item}")


# ============================================================================
# 25. INTEGRATED MINI CASE STUDY
# ============================================================================

def analyze_student_scores(scores: Sequence[int], threshold: int) -> list[int]:
    """
    Return all scores at or above threshold.

    The algorithm performs one pass and allocates output proportional to
    the number of qualifying records.

    Time: O(n)
    Auxiliary output space: O(k), where k is the number of selected scores.
    """
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")

    selected = []

    for score in scores:
        if not 0 <= score <= 100:
            raise ValueError("score must be between 0 and 100")
        if score >= threshold:
            selected.append(score)

    return selected


def demonstrate_case_study() -> None:
    print_section("25. Integrated case study")

    scores = [55, 91, 72, 88, 43, 96, 67]
    selected = analyze_student_scores(scores, 75)

    print("Scores:", scores)
    print("Scores >= 75:", selected)

    print("\nLet n be the number of scores and k the number selected.")
    print("Time: O(n)")
    print("Output space: O(k), worst case O(n)")
    print("Input validation remains O(n).")


# ============================================================================
# 26. FINAL CONCEPT MAP
# ============================================================================

def print_concept_map() -> None:
    print_section("26. Concept map")

    concepts = [
        "Input size n",
        "Primitive operation",
        "Growth rate",
        "Asymptotic notation",
        "Best / average / worst case",
        "Time complexity",
        "Auxiliary space",
        "Recursion and recurrences",
        "Divide and conquer",
        "Dynamic programming",
        "Greedy and graph algorithms",
        "Amortized analysis",
        "Expected complexity",
        "Lower bounds",
        "Time-space trade-offs",
        "Empirical benchmarking",
        "Production constraints",
        "Security and resource exhaustion",
    ]

    for index, concept in enumerate(concepts, start=1):
        print(f"{index:>2}. {concept}")


def main() -> None:
    demonstrate_basic_classes()
    demonstrate_growth_rates()
    demonstrate_asymptotic_notation()
    demonstrate_cases()
    demonstrate_loop_analysis()
    demonstrate_binary_search()
    demonstrate_sorting()
    demonstrate_recursion()
    demonstrate_dynamic_programming()
    demonstrate_space_complexity()
    demonstrate_hashing()
    demonstrate_graph_complexity()
    demonstrate_amortized_analysis()
    demonstrate_recurrences()
    demonstrate_master_theorem()
    demonstrate_two_pointers()
    demonstrate_prefix_sums()
    demonstrate_empirical_measurement()
    demonstrate_edge_cases()
    demonstrate_advanced_concepts()
    demonstrate_algorithm_table()
    demonstrate_tradeoffs()
    demonstrate_security_considerations()
    production_checklist()
    demonstrate_case_study()
    print_concept_map()

    print_section("Completed")
    print("Complexity analysis demonstrations completed successfully.")


if __name__ == "__main__":
    main()
