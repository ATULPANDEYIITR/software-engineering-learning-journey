"""
Algorithms: Searching, Sorting, and Algorithmic Thinking
=========================================================

A self-contained study program covering:
- Algorithmic thinking
- Complexity analysis
- Searching algorithms
- Sorting algorithms
- Stability and in-place behavior
- Divide and conquer
- Recursion
- Greedy reasoning
- Binary search variants
- Hash-based lookup
- Selection algorithms
- Real-world case study
- Testing, validation, edge cases, and performance measurement

Run with:
    python algorithms_searching_sorting.py
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import Counter, deque
from time import perf_counter
from typing import Callable, Iterable, Optional, TypeVar
import bisect
import heapq
import math
import random
import statistics


T = TypeVar("T")


# ---------------------------------------------------------------------------
# 1. ALGORITHMIC THINKING
# ---------------------------------------------------------------------------

def linear_search(items: list[T], target: T) -> int:
    """
    Search sequentially from left to right.

    Time:
        Best:    O(1)
        Average: O(n)
        Worst:   O(n)

    Space:
        O(1)
    """
    for index, item in enumerate(items):
        if item == target:
            return index
    return -1


def binary_search(items: list[T], target: T) -> int:
    """
    Binary search requires sorted input.

    Each comparison eliminates approximately half of the remaining
    search space.

    Time:  O(log n)
    Space: O(1)
    """
    left = 0
    right = len(items) - 1

    while left <= right:
        middle = left + (right - left) // 2

        if items[middle] == target:
            return middle

        if items[middle] < target:
            left = middle + 1
        else:
            right = middle - 1

    return -1


def recursive_binary_search(
    items: list[T],
    target: T,
    left: int = 0,
    right: Optional[int] = None,
) -> int:
    """Recursive binary search. The recursive depth is O(log n)."""
    if right is None:
        right = len(items) - 1

    if left > right:
        return -1

    middle = left + (right - left) // 2

    if items[middle] == target:
        return middle

    if items[middle] < target:
        return recursive_binary_search(items, target, middle + 1, right)

    return recursive_binary_search(items, target, left, middle - 1)


# ---------------------------------------------------------------------------
# 2. BASIC SORTING ALGORITHMS
# ---------------------------------------------------------------------------

def bubble_sort(items: list[T]) -> list[T]:
    """
    Bubble sort repeatedly exchanges adjacent elements.

    Worst/average: O(n^2)
    Best with early termination: O(n)
    Space: O(1) auxiliary space

    The implementation sorts a copy so the caller's list is preserved.
    """
    result = items.copy()

    for end in range(len(result) - 1, 0, -1):
        swapped = False

        for index in range(end):
            if result[index] > result[index + 1]:
                result[index], result[index + 1] = (
                    result[index + 1],
                    result[index],
                )
                swapped = True

        if not swapped:
            break

    return result


def selection_sort(items: list[T]) -> list[T]:
    """
    Selection sort repeatedly selects the smallest remaining element.

    Time:  O(n^2)
    Space: O(1) auxiliary space

    It performs relatively few swaps compared with bubble sort.
    """
    result = items.copy()

    for start in range(len(result)):
        minimum_index = start

        for index in range(start + 1, len(result)):
            if result[index] < result[minimum_index]:
                minimum_index = index

        result[start], result[minimum_index] = (
            result[minimum_index],
            result[start],
        )

    return result


def insertion_sort(items: list[T]) -> list[T]:
    """
    Insertion sort grows a sorted prefix.

    Best:    O(n)
    Average: O(n^2)
    Worst:   O(n^2)
    Space:   O(1) auxiliary space

    It performs particularly well on small or nearly sorted data.
    """
    result = items.copy()

    for index in range(1, len(result)):
        current = result[index]
        position = index - 1

        while position >= 0 and result[position] > current:
            result[position + 1] = result[position]
            position -= 1

        result[position + 1] = current

    return result


# ---------------------------------------------------------------------------
# 3. DIVIDE AND CONQUER SORTING
# ---------------------------------------------------------------------------

def merge(left: list[T], right: list[T]) -> list[T]:
    """Merge two already sorted lists in linear time."""
    merged: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        # <= preserves stability when equal elements exist.
        if left[left_index] <= right[right_index]:
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged


def merge_sort(items: list[T]) -> list[T]:
    """
    Merge sort applies divide and conquer.

    Recurrence:
        T(n) = 2T(n/2) + O(n)

    Time:  O(n log n)
    Space: O(n) for the returned arrays.

    Merge sort has predictable O(n log n) worst-case behavior.
    """
    if len(items) <= 1:
        return items.copy()

    middle = len(items) // 2
    left = merge_sort(items[:middle])
    right = merge_sort(items[middle:])

    return merge(left, right)


def quick_sort(items: list[T]) -> list[T]:
    """
    Quicksort using a three-way partition.

    Average: O(n log n)
    Worst:   O(n^2)
    Expected recursion depth: approximately O(log n) with good pivots.

    Three-way partitioning handles repeated values efficiently.
    """
    result = items.copy()

    def sort(left: int, right: int) -> None:
        if left >= right:
            return

        pivot = result[random.randint(left, right)]

        less = left
        current = left
        greater = right

        while current <= greater:
            if result[current] < pivot:
                result[less], result[current] = result[current], result[less]
                less += 1
                current += 1
            elif result[current] > pivot:
                result[current], result[greater] = (
                    result[greater],
                    result[current],
                )
                greater -= 1
            else:
                current += 1

        sort(left, less - 1)
        sort(greater + 1, right)

    sort(0, len(result) - 1)
    return result


# ---------------------------------------------------------------------------
# 4. HEAP SORT
# ---------------------------------------------------------------------------

def heap_sort(items: list[T]) -> list[T]:
    """
    Heap sort using Python's heap implementation.

    Time:  O(n log n)
    Space: O(n) here because heapq is used as an auxiliary structure.

    A traditional array-based heapsort can be implemented in O(1)
    auxiliary space.
    """
    heap = items.copy()
    heapq.heapify(heap)

    return [heapq.heappop(heap) for _ in range(len(heap))]


# ---------------------------------------------------------------------------
# 5. COUNTING SORT
# ---------------------------------------------------------------------------

def counting_sort(values: list[int]) -> list[int]:
    """
    Counting sort for integers over a reasonably small value range.

    Time:  O(n + k)
    Space: O(k)

    k is the numeric range from minimum to maximum.

    This algorithm can be much faster than comparison sorting when
    k is small relative to n.
    """
    if not values:
        return []

    minimum = min(values)
    maximum = max(values)
    range_size = maximum - minimum + 1

    # Avoid accidentally allocating enormous memory for sparse values.
    if range_size > 1_000_000:
        raise ValueError(
            "Counting sort is unsuitable for this numeric range."
        )

    counts = [0] * range_size

    for value in values:
        counts[value - minimum] += 1

    result: list[int] = []

    for offset, count in enumerate(counts):
        result.extend([offset + minimum] * count)

    return result


# ---------------------------------------------------------------------------
# 6. RADIX SORT
# ---------------------------------------------------------------------------

def radix_sort_non_negative(values: list[int]) -> list[int]:
    """
    Least-significant-digit radix sort for non-negative integers.

    Time: O(d * (n + b))
        d = number of digits
        b = base, here 10

    Radix sort is not a comparison sort.
    """
    if not values:
        return []

    if any(value < 0 for value in values):
        raise ValueError("This implementation accepts only non-negative integers.")

    result = values.copy()
    maximum = max(result)
    exponent = 1

    while maximum // exponent > 0:
        buckets = [[] for _ in range(10)]

        for value in result:
            digit = (value // exponent) % 10
            buckets[digit].append(value)

        result = [value for bucket in buckets for value in bucket]
        exponent *= 10

    return result


def radix_sort(values: list[int]) -> list[int]:
    """Radix sort extended to signed integers."""
    negatives = [-value for value in values if value < 0]
    positives = [value for value in values if value >= 0]

    sorted_negatives = radix_sort_non_negative(negatives)
    sorted_positives = radix_sort_non_negative(positives)

    # Negated negative values reverse their ordering.
    return [-value for value in reversed(sorted_negatives)] + sorted_positives


# ---------------------------------------------------------------------------
# 7. PYTHON'S PRODUCTION SORTING TOOLS
# ---------------------------------------------------------------------------

@dataclass
class Student:
    name: str
    score: float
    age: int


def demonstrate_key_sorting() -> None:
    students = [
        Student("Asha", 88, 21),
        Student("Rahul", 95, 22),
        Student("Meera", 88, 20),
        Student("Kabir", 95, 21),
    ]

    # Python's sort is stable, so equal scores retain their original order.
    by_score = sorted(students, key=lambda student: student.score, reverse=True)

    # Multiple stable sorting passes can build compound ordering.
    by_score_then_age = sorted(
        students,
        key=lambda student: (student.score, student.age),
        reverse=True,
    )

    print("\nStable key-based sorting:")
    print("By score:", by_score)
    print("By score then age:", by_score_then_age)


# ---------------------------------------------------------------------------
# 8. BINARY SEARCH VARIANTS
# ---------------------------------------------------------------------------

def first_occurrence(items: list[int], target: int) -> int:
    """Return the first index containing target, or -1."""
    left = 0
    right = len(items) - 1
    answer = -1

    while left <= right:
        middle = left + (right - left) // 2

        if items[middle] >= target:
            if items[middle] == target:
                answer = middle
            right = middle - 1
        else:
            left = middle + 1

    return answer


def last_occurrence(items: list[int], target: int) -> int:
    """Return the last index containing target, or -1."""
    left = 0
    right = len(items) - 1
    answer = -1

    while left <= right:
        middle = left + (right - left) // 2

        if items[middle] <= target:
            if items[middle] == target:
                answer = middle
            left = middle + 1
        else:
            right = middle - 1

    return answer


def lower_bound(items: list[int], target: int) -> int:
    """
    First position where target could be inserted while preserving order.

    Equivalent conceptually to bisect_left.
    """
    left = 0
    right = len(items)

    while left < right:
        middle = left + (right - left) // 2

        if items[middle] < target:
            left = middle + 1
        else:
            right = middle

    return left


def upper_bound(items: list[int], target: int) -> int:
    """
    First position after all occurrences of target.

    Equivalent conceptually to bisect_right.
    """
    left = 0
    right = len(items)

    while left < right:
        middle = left + (right - left) // 2

        if items[middle] <= target:
            left = middle + 1
        else:
            right = middle

    return left


def count_occurrences(items: list[int], target: int) -> int:
    """Count a target in sorted data in O(log n)."""
    return upper_bound(items, target) - lower_bound(items, target)


# ---------------------------------------------------------------------------
# 9. INTERPOLATION SEARCH
# ---------------------------------------------------------------------------

def interpolation_search(items: list[int], target: int) -> int:
    """
    Interpolation search estimates where a target should be.

    It can approach O(log log n) on uniformly distributed data,
    but its worst case is O(n).

    It is unsuitable for many non-uniform distributions.
    """
    left = 0
    right = len(items) - 1

    while (
        left <= right
        and items[left] <= target <= items[right]
    ):
        if items[left] == items[right]:
            return left if items[left] == target else -1

        position = left + (
            (target - items[left]) * (right - left)
            // (items[right] - items[left])
        )

        if items[position] == target:
            return position

        if items[position] < target:
            left = position + 1
        else:
            right = position - 1

    return -1


# ---------------------------------------------------------------------------
# 10. HASH-BASED SEARCHING
# ---------------------------------------------------------------------------

def hash_lookup_demo() -> None:
    """
    Dictionary lookup is based on hashing.

    Average expected lookup: O(1)
    Worst-case theoretical behavior depends on implementation/collisions.
    """
    employee_department = {
        "E101": "Engineering",
        "E102": "Finance",
        "E103": "Operations",
    }

    print("\nHash lookup:")
    print(employee_department.get("E102"))
    print(employee_department.get("E999", "Employee not found"))


# ---------------------------------------------------------------------------
# 11. TWO-POINTER AND BINARY-SEARCH THINKING
# ---------------------------------------------------------------------------

def two_sum_sorted(numbers: list[int], target: int) -> Optional[tuple[int, int]]:
    """
    Find two values whose sum equals target.

    Input must be sorted.

    Time: O(n)
    Space: O(1)
    """
    left = 0
    right = len(numbers) - 1

    while left < right:
        total = numbers[left] + numbers[right]

        if total == target:
            return numbers[left], numbers[right]

        if total < target:
            left += 1
        else:
            right -= 1

    return None


def integer_square_root(number: int) -> int:
    """
    Find floor(sqrt(number)) without calling math.sqrt.

    Demonstrates binary search over an answer space.
    """
    if number < 0:
        raise ValueError("Square root is undefined here for negative integers.")

    if number < 2:
        return number

    left = 1
    right = number // 2
    answer = 1

    while left <= right:
        middle = (left + right) // 2

        if middle * middle <= number:
            answer = middle
            left = middle + 1
        else:
            right = middle - 1

    return answer


# ---------------------------------------------------------------------------
# 12. GREEDY ALGORITHMIC THINKING
# ---------------------------------------------------------------------------

def activity_selection(
    activities: list[tuple[int, int]],
) -> list[tuple[int, int]]:
    """
    Select the maximum number of non-overlapping activities.

    Greedy rule:
        Always select the activity with the earliest finishing time.

    Time: O(n log n) because of sorting.
    """
    sorted_activities = sorted(activities, key=lambda activity: activity[1])

    selected: list[tuple[int, int]] = []
    current_end = -math.inf

    for start, end in sorted_activities:
        if start >= current_end:
            selected.append((start, end))
            current_end = end

    return selected


# ---------------------------------------------------------------------------
# 13. DYNAMIC PROGRAMMING EXAMPLE
# ---------------------------------------------------------------------------

def fibonacci_naive(n: int) -> int:
    """
    Naive recursive Fibonacci.

    Time is exponential, approximately O(2^n).
    This is intentionally included to demonstrate poor algorithmic design.
    """
    if n <= 1:
        return n

    return fibonacci_naive(n - 1) + fibonacci_naive(n - 2)


def fibonacci_dynamic(n: int) -> int:
    """
    Bottom-up dynamic programming.

    Time: O(n)
    Space: O(1)
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n <= 1:
        return n

    previous = 0
    current = 1

    for _ in range(2, n + 1):
        previous, current = current, previous + current

    return current


# ---------------------------------------------------------------------------
# 14. SELECTION ALGORITHM
# ---------------------------------------------------------------------------

def kth_smallest_quickselect(values: list[int], k: int) -> int:
    """
    Return the k-th smallest value using Quickselect.

    k is zero-based.

    Average: O(n)
    Worst:   O(n^2)

    This is useful when the complete sorted order is unnecessary.
    """
    if not 0 <= k < len(values):
        raise IndexError("k is outside the valid range.")

    data = values.copy()
    left = 0
    right = len(data) - 1

    while True:
        if left == right:
            return data[left]

        pivot = data[random.randint(left, right)]

        lower = left
        current = left
        upper = right

        while current <= upper:
            if data[current] < pivot:
                data[lower], data[current] = data[current], data[lower]
                lower += 1
                current += 1
            elif data[current] > pivot:
                data[current], data[upper] = data[upper], data[current]
                upper -= 1
            else:
                current += 1

        if k < lower:
            right = lower - 1
        elif k > upper:
            left = upper + 1
        else:
            return data[k]


# ---------------------------------------------------------------------------
# 15. GRAPH SEARCHING
# ---------------------------------------------------------------------------

def breadth_first_search(
    graph: dict[str, list[str]],
    start: str,
    target: str,
) -> Optional[list[str]]:
    """
    BFS finds the shortest path in an unweighted graph.

    Time: O(V + E)
    Space: O(V)
    """
    if start not in graph:
        return None

    queue = deque([start])
    parent: dict[str, Optional[str]] = {start: None}

    while queue:
        current = queue.popleft()

        if current == target:
            path: list[str] = []
            node: Optional[str] = target

            while node is not None:
                path.append(node)
                node = parent[node]

            return list(reversed(path))

        for neighbor in graph.get(current, []):
            if neighbor not in parent:
                parent[neighbor] = current
                queue.append(neighbor)

    return None


def depth_first_search(
    graph: dict[str, list[str]],
    start: str,
    target: str,
) -> Optional[list[str]]:
    """
    DFS explores deeply before backtracking.

    Time: O(V + E)
    Space: O(V) including visited state and recursion stack.
    """
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> bool:
        if node in visited:
            return False

        visited.add(node)
        path.append(node)

        if node == target:
            return True

        for neighbor in graph.get(node, []):
            if visit(neighbor):
                return True

        path.pop()
        return False

    return path.copy() if visit(start) else None


# ---------------------------------------------------------------------------
# 16. REAL-WORLD CASE STUDY: PRODUCT SEARCH
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Product:
    product_id: int
    name: str
    category: str
    price: float
    stock: int
    rating: float


class ProductCatalog:
    """
    A small in-memory catalog demonstrating multiple algorithmic choices.

    The catalog maintains:
        1. Original products.
        2. Products sorted by price.
        3. A hash index by product ID.
        4. A name index for exact lookup.

    Different queries benefit from different data structures.
    """

    def __init__(self, products: Iterable[Product]) -> None:
        self.products = list(products)

        self.by_id = {
            product.product_id: product
            for product in self.products
        }

        self.by_price = sorted(
            self.products,
            key=lambda product: product.price,
        )

        self.price_values = [
            product.price for product in self.by_price
        ]

        self.by_name = {
            product.name.casefold(): product
            for product in self.products
        }

    def find_by_id(self, product_id: int) -> Optional[Product]:
        """Expected O(1) hash lookup."""
        return self.by_id.get(product_id)

    def find_by_name(self, name: str) -> Optional[Product]:
        """Expected O(1) exact hash lookup."""
        return self.by_name.get(name.casefold())

    def products_up_to_price(self, maximum_price: float) -> list[Product]:
        """
        Return all products priced <= maximum_price.

        bisect finds the boundary in O(log n).
        Producing the result itself costs O(k).
        """
        boundary = bisect.bisect_right(
            self.price_values,
            maximum_price,
        )
        return self.by_price[:boundary]

    def top_rated_in_category(
        self,
        category: str,
        limit: int = 5,
    ) -> list[Product]:
        """
        Sort only the matching subset.

        For a small in-memory demonstration this is straightforward.
        Large systems may use database indexes or specialized ranking.
        """
        if limit <= 0:
            return []

        matching = [
            product
            for product in self.products
            if product.category.casefold() == category.casefold()
        ]

        return sorted(
            matching,
            key=lambda product: (
                -product.rating,
                product.price,
            ),
        )[:limit]

    def recommend(
        self,
        category: str,
        maximum_price: float,
        limit: int = 5,
    ) -> list[Product]:
        """
        Filter candidates, then rank them.

        Ranking formula:
            rating has stronger influence than price.

        This is a deliberately simple deterministic ranking algorithm.
        """
        candidates = [
            product
            for product in self.products
            if (
                product.category.casefold() == category.casefold()
                and product.price <= maximum_price
                and product.stock > 0
            )
        ]

        def score(product: Product) -> float:
            price_factor = 1 / (1 + product.price)
            return product.rating * 10 + price_factor * 100

        return sorted(
            candidates,
            key=score,
            reverse=True,
        )[:limit]


# ---------------------------------------------------------------------------
# 17. ALGORITHM CORRECTNESS AND VALIDATION
# ---------------------------------------------------------------------------

def validate_sorting_algorithm(
    sorting_function: Callable[[list[int]], list[int]],
    test_cases: list[list[int]],
) -> None:
    """Compare an implementation against Python's trusted sorted result."""
    for case in test_cases:
        actual = sorting_function(case)
        expected = sorted(case)

        if actual != expected:
            raise AssertionError(
                f"{sorting_function.__name__} failed for {case}: "
                f"got {actual}, expected {expected}"
            )


def validate_searching_algorithms() -> None:
    cases = [
        [],
        [1],
        [1, 2, 3],
        [1, 1, 1],
        [-10, -5, 0, 4, 8],
        list(range(100)),
    ]

    for items in cases:
        for target in [-10, 0, 1, 4, 50, 99, 100]:
            expected = (
                items.index(target)
                if target in items
                else -1
            )

            actual = binary_search(items, target)

            # Any matching occurrence is valid for ordinary binary search.
            if target in items:
                if actual == -1 or items[actual] != target:
                    raise AssertionError("Binary search returned an invalid index.")
            elif actual != expected:
                raise AssertionError("Binary search failed to report absence.")

    duplicate_case = [1, 2, 2, 2, 3, 4]
    assert first_occurrence(duplicate_case, 2) == 1
    assert last_occurrence(duplicate_case, 2) == 3
    assert count_occurrences(duplicate_case, 2) == 3


# ---------------------------------------------------------------------------
# 18. COMPLEXITY DEMONSTRATION
# ---------------------------------------------------------------------------

def measure_runtime(
    function: Callable[[list[int]], object],
    values: list[int],
    repetitions: int = 3,
) -> float:
    """Return the median runtime in seconds."""
    durations = []

    for _ in range(repetitions):
        start = perf_counter()
        function(values)
        durations.append(perf_counter() - start)

    return statistics.median(durations)


def benchmark_sorting() -> None:
    """
    Small educational benchmark.

    Exact results depend on CPU, Python version, operating system,
    memory pressure, and implementation details.
    """
    random.seed(42)
    values = [random.randint(-10_000, 10_000) for _ in range(2_000)]

    algorithms = [
        ("Insertion sort", insertion_sort),
        ("Merge sort", merge_sort),
        ("Quick sort", quick_sort),
        ("Heap sort", heap_sort),
        ("Python sorted", sorted),
    ]

    print("\nSorting benchmark:")
    for name, function in algorithms:
        duration = measure_runtime(function, values)
        print(f"{name:20} {duration:.6f} seconds")


# ---------------------------------------------------------------------------
# 19. COMMON EDGE CASES
# ---------------------------------------------------------------------------

def demonstrate_edge_cases() -> None:
    print("\nEdge cases:")

    print("Empty linear search:", linear_search([], 10))
    print("Empty binary search:", binary_search([], 10))
    print("Single element:", binary_search([10], 10))
    print("Absent element:", binary_search([1, 2, 3], 99))
    print("Duplicates:", first_occurrence([2, 2, 2], 2))

    try:
        counting_sort([1, 10_000_000])
    except ValueError as error:
        print("Counting-sort limitation:", error)

    try:
        radix_sort_non_negative([-1, 2])
    except ValueError as error:
        print("Radix-sort validation:", error)

    try:
        kth_smallest_quickselect([1, 2, 3], 3)
    except IndexError as error:
        print("Quickselect validation:", error)


# ---------------------------------------------------------------------------
# 20. COMPARISON TABLE AS DATA
# ---------------------------------------------------------------------------

def print_algorithm_comparison() -> None:
    algorithms = [
        ("Linear search", "O(1)", "O(n)", "No"),
        ("Binary search", "O(1)", "O(log n)", "Yes"),
        ("Bubble sort", "O(n)", "O(n²)", "No"),
        ("Insertion sort", "O(n)", "O(n²)", "No"),
        ("Selection sort", "O(n²)", "O(n²)", "No"),
        ("Merge sort", "O(n log n)", "O(n log n)", "No"),
        ("Quick sort", "O(n log n)", "O(n²)", "No"),
        ("Heap sort", "O(n log n)", "O(n log n)", "No"),
        ("Counting sort", "O(n+k)", "O(n+k)", "No"),
        ("Radix sort", "O(d(n+b))", "O(d(n+b))", "No"),
    ]

    print("\nAlgorithm comparison:")
    print(f"{'Algorithm':20} {'Best':14} {'Worst':14} {'Sorted input required'}")
    print("-" * 70)

    for name, best, worst, requirement in algorithms:
        print(f"{name:20} {best:14} {worst:14} {requirement}")


# ---------------------------------------------------------------------------
# 21. MAIN EDUCATIONAL DEMONSTRATION
# ---------------------------------------------------------------------------

def main() -> None:
    random.seed(7)

    print("=" * 72)
    print("ALGORITHMS: SEARCHING, SORTING, AND ALGORITHMIC THINKING")
    print("=" * 72)

    data = [7, 2, 9, 4, 1, 8, 2, 5]

    print("\nOriginal data:", data)
    print("Linear search for 8:", linear_search(data, 8))

    sorted_data = merge_sort(data)
    print("Sorted data:", sorted_data)
    print("Binary search for 8:", binary_search(sorted_data, 8))

    print("\nSorting examples:")
    print("Bubble:    ", bubble_sort(data))
    print("Selection: ", selection_sort(data))
    print("Insertion: ", insertion_sort(data))
    print("Merge:     ", merge_sort(data))
    print("Quick:     ", quick_sort(data))
    print("Heap:      ", heap_sort(data))
    print("Counting:  ", counting_sort(data))
    print("Radix:     ", radix_sort(data))

    print("\nBinary-search boundaries:")
    duplicates = [1, 2, 2, 2, 3, 3, 4]
    print("Data:", duplicates)
    print("First 2:", first_occurrence(duplicates, 2))
    print("Last 2:", last_occurrence(duplicates, 2))
    print("Lower bound of 2:", lower_bound(duplicates, 2))
    print("Upper bound of 2:", upper_bound(duplicates, 2))
    print("Count of 2:", count_occurrences(duplicates, 2))

    hash_lookup_demo()

    print("\nTwo-pointer algorithm:")
    numbers = [1, 2, 4, 5, 7, 9, 11]
    print("Numbers:", numbers)
    print("Pair summing to 16:", two_sum_sorted(numbers, 16))

    print("\nBinary search over answer space:")
    for number in [0, 1, 2, 10, 15, 100]:
        print(f"floor(sqrt({number})) =", integer_square_root(number))

    print("\nGreedy activity selection:")
    activities = [
        (1, 4),
        (3, 5),
        (0, 6),
        (5, 7),
        (3, 9),
        (5, 9),
        (6, 10),
        (8, 11),
        (8, 12),
        (2, 14),
        (12, 16),
    ]
    print(activity_selection(activities))

    print("\nDynamic programming:")
    print("Fibonacci(20), dynamic:", fibonacci_dynamic(20))

    print("\nQuickselect:")
    values = [9, 2, 7, 1, 8, 3, 5]
    print("Values:", values)
    print("3rd smallest:", kth_smallest_quickselect(values, 2))

    print("\nGraph search:")
    graph = {
        "A": ["B", "C"],
        "B": ["D", "E"],
        "C": ["F"],
        "D": [],
        "E": ["F"],
        "F": [],
    }
    print("BFS A -> F:", breadth_first_search(graph, "A", "F"))
    print("DFS A -> F:", depth_first_search(graph, "A", "F"))

    print("\nProduct catalog case study:")
    catalog = ProductCatalog(
        [
            Product(101, "Laptop Pro", "Computers", 1200.0, 8, 4.8),
            Product(102, "Laptop Air", "Computers", 900.0, 12, 4.6),
            Product(103, "Workstation X", "Computers", 2200.0, 3, 4.9),
            Product(104, "Mechanical Keyboard", "Accessories", 120.0, 40, 4.7),
            Product(105, "Wireless Mouse", "Accessories", 60.0, 100, 4.5),
            Product(106, "USB Hub", "Accessories", 45.0, 0, 4.4),
        ]
    )

    print("ID 103:", catalog.find_by_id(103))
    print("Laptop Air:", catalog.find_by_name("laptop air"))
    print("Products <= $1,000:", catalog.products_up_to_price(1000))
    print(
        "Top accessories:",
        catalog.top_rated_in_category("Accessories"),
    )
    print(
        "Computer recommendations:",
        catalog.recommend("Computers", 1500),
    )

    demonstrate_key_sorting()
    demonstrate_edge_cases()
    validate_searching_algorithms()

    test_cases = [
        [],
        [1],
        [2, 1],
        [3, 1, 2, 3, 2],
        [-5, 0, 7, -2, 4],
        [9, 9, 9, 1, 1, 5],
    ]

    validate_sorting_algorithm(bubble_sort, test_cases)
    validate_sorting_algorithm(selection_sort, test_cases)
    validate_sorting_algorithm(insertion_sort, test_cases)
    validate_sorting_algorithm(merge_sort, test_cases)
    validate_sorting_algorithm(quick_sort, test_cases)
    validate_sorting_algorithm(heap_sort, test_cases)
    validate_sorting_algorithm(counting_sort, test_cases)
    validate_sorting_algorithm(radix_sort, test_cases)

    print("\nAll correctness checks passed.")

    print_algorithm_comparison()

    # Keep the benchmark moderate so the educational script remains usable.
    benchmark_sorting()

    print("\nAlgorithmic thinking checklist:")
    print("1. Define the exact problem.")
    print("2. Identify constraints and input characteristics.")
    print("3. Establish correctness requirements.")
    print("4. Select an appropriate data structure.")
    print("5. Design an algorithm.")
    print("6. Analyze time and space complexity.")
    print("7. Test normal and adversarial cases.")
    print("8. Measure performance when real data matters.")
    print("9. Consider maintainability, security, and failure modes.")
    print("10. Reassess whether preprocessing or indexing changes the trade-off.")


if __name__ == "__main__":
    main()
