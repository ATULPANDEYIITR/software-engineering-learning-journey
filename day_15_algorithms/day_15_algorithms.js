/**
 * Algorithms: Searching, Sorting, and Algorithmic Thinking
 * =========================================================
 *
 * A self-contained JavaScript study program covering:
 * - Algorithmic thinking
 * - Complexity
 * - Searching
 * - Sorting
 * - Binary search variants
 * - Hash-based lookup
 * - Divide and conquer
 * - Greedy algorithms
 * - Dynamic programming
 * - Graph traversal
 * - Real-world product search
 *
 * Run with:
 *     node algorithms_searching_sorting.js
 */

// ---------------------------------------------------------------------------
// 1. BASIC ALGORITHMIC THINKING
// ---------------------------------------------------------------------------

function linearSearch(items, target) {
    // Sequentially inspect every element until the target is found.
    // Worst-case time: O(n), auxiliary space: O(1).
    for (let index = 0; index < items.length; index += 1) {
        if (items[index] === target) {
            return index;
        }
    }

    return -1;
}

function binarySearch(items, target) {
    // Binary search is valid only when items are sorted.
    // Each comparison removes roughly half of the search space.
    // Time: O(log n), space: O(1).
    let left = 0;
    let right = items.length - 1;

    while (left <= right) {
        const middle = left + Math.floor((right - left) / 2);

        if (items[middle] === target) {
            return middle;
        }

        if (items[middle] < target) {
            left = middle + 1;
        } else {
            right = middle - 1;
        }
    }

    return -1;
}

// ---------------------------------------------------------------------------
// 2. SIMPLE SORTING ALGORITHMS
// ---------------------------------------------------------------------------

function bubbleSort(items) {
    const result = [...items];

    for (let end = result.length - 1; end > 0; end -= 1) {
        let swapped = false;

        for (let index = 0; index < end; index += 1) {
            if (result[index] > result[index + 1]) {
                [result[index], result[index + 1]] = [
                    result[index + 1],
                    result[index]
                ];
                swapped = true;
            }
        }

        // An already sorted array needs no additional passes.
        if (!swapped) {
            break;
        }
    }

    return result;
}

function insertionSort(items) {
    const result = [...items];

    for (let index = 1; index < result.length; index += 1) {
        const current = result[index];
        let position = index - 1;

        while (position >= 0 && result[position] > current) {
            result[position + 1] = result[position];
            position -= 1;
        }

        result[position + 1] = current;
    }

    return result;
}

function selectionSort(items) {
    const result = [...items];

    for (let start = 0; start < result.length; start += 1) {
        let minimumIndex = start;

        for (let index = start + 1; index < result.length; index += 1) {
            if (result[index] < result[minimumIndex]) {
                minimumIndex = index;
            }
        }

        [result[start], result[minimumIndex]] = [
            result[minimumIndex],
            result[start]
        ];
    }

    return result;
}

// ---------------------------------------------------------------------------
// 3. MERGE SORT
// ---------------------------------------------------------------------------

function merge(left, right) {
    const result = [];
    let leftIndex = 0;
    let rightIndex = 0;

    while (leftIndex < left.length && rightIndex < right.length) {
        if (left[leftIndex] <= right[rightIndex]) {
            // <= keeps equal values stable.
            result.push(left[leftIndex]);
            leftIndex += 1;
        } else {
            result.push(right[rightIndex]);
            rightIndex += 1;
        }
    }

    return result
        .concat(left.slice(leftIndex))
        .concat(right.slice(rightIndex));
}

function mergeSort(items) {
    if (items.length <= 1) {
        return [...items];
    }

    const middle = Math.floor(items.length / 2);
    const left = mergeSort(items.slice(0, middle));
    const right = mergeSort(items.slice(middle));

    return merge(left, right);
}

// ---------------------------------------------------------------------------
// 4. QUICK SORT
// ---------------------------------------------------------------------------

function quickSort(items) {
    // This recursive implementation chooses a middle value as pivot.
    // Average time: O(n log n), worst case: O(n²).
    if (items.length <= 1) {
        return [...items];
    }

    const pivot = items[Math.floor(items.length / 2)];
    const smaller = [];
    const equal = [];
    const greater = [];

    for (const item of items) {
        if (item < pivot) {
            smaller.push(item);
        } else if (item > pivot) {
            greater.push(item);
        } else {
            equal.push(item);
        }
    }

    return quickSort(smaller)
        .concat(equal)
        .concat(quickSort(greater));
}

// ---------------------------------------------------------------------------
// 5. COUNTING SORT
// ---------------------------------------------------------------------------

function countingSort(values) {
    if (values.length === 0) {
        return [];
    }

    if (!values.every(Number.isInteger)) {
        throw new TypeError("Counting sort requires integers.");
    }

    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const range = maximum - minimum + 1;

    // Counting sort is inappropriate when the numeric range is enormous.
    if (range > 1_000_000) {
        throw new RangeError(
            "Numeric range is too large for this counting-sort implementation."
        );
    }

    const counts = new Array(range).fill(0);

    for (const value of values) {
        counts[value - minimum] += 1;
    }

    const result = [];

    for (let offset = 0; offset < counts.length; offset += 1) {
        for (let count = 0; count < counts[offset]; count += 1) {
            result.push(offset + minimum);
        }
    }

    return result;
}

// ---------------------------------------------------------------------------
// 6. BINARY SEARCH BOUNDARIES
// ---------------------------------------------------------------------------

function lowerBound(items, target) {
    // First index whose value is >= target.
    let left = 0;
    let right = items.length;

    while (left < right) {
        const middle = left + Math.floor((right - left) / 2);

        if (items[middle] < target) {
            left = middle + 1;
        } else {
            right = middle;
        }
    }

    return left;
}

function upperBound(items, target) {
    // First index whose value is > target.
    let left = 0;
    let right = items.length;

    while (left < right) {
        const middle = left + Math.floor((right - left) / 2);

        if (items[middle] <= target) {
            left = middle + 1;
        } else {
            right = middle;
        }
    }

    return left;
}

function countOccurrences(items, target) {
    return upperBound(items, target) - lowerBound(items, target);
}

// ---------------------------------------------------------------------------
// 7. JAVASCRIPT'S NATIVE SORT AND COMPARATORS
// ---------------------------------------------------------------------------

function demonstrateNativeSorting() {
    const students = [
        { name: "Asha", score: 88 },
        { name: "Rahul", score: 95 },
        { name: "Meera", score: 88 },
        { name: "Kabir", score: 95 }
    ];

    // Array.prototype.sort mutates the array, so copy it first when
    // immutability is desirable.
    const byScore = [...students].sort((a, b) => b.score - a.score);

    // A compound comparator expresses multiple ordering criteria.
    const byScoreThenName = [...students].sort((a, b) => {
        if (b.score !== a.score) {
            return b.score - a.score;
        }

        return a.name.localeCompare(b.name);
    });

    console.log("\nNative JavaScript sorting:");
    console.log("By score:", byScore);
    console.log("By score then name:", byScoreThenName);
}

// ---------------------------------------------------------------------------
// 8. TWO-POINTER ALGORITHM
// ---------------------------------------------------------------------------

function twoSumSorted(numbers, target) {
    let left = 0;
    let right = numbers.length - 1;

    while (left < right) {
        const total = numbers[left] + numbers[right];

        if (total === target) {
            return [numbers[left], numbers[right]];
        }

        if (total < target) {
            left += 1;
        } else {
            right -= 1;
        }
    }

    return null;
}

// ---------------------------------------------------------------------------
// 9. BINARY SEARCH OVER THE ANSWER SPACE
// ---------------------------------------------------------------------------

function integerSquareRoot(number) {
    if (!Number.isInteger(number) || number < 0) {
        throw new RangeError("Expected a non-negative integer.");
    }

    if (number < 2) {
        return number;
    }

    let left = 1;
    let right = Math.floor(number / 2);
    let answer = 1;

    while (left <= right) {
        const middle = left + Math.floor((right - left) / 2);

        if (middle * middle <= number) {
            answer = middle;
            left = middle + 1;
        } else {
            right = middle - 1;
        }
    }

    return answer;
}

// ---------------------------------------------------------------------------
// 10. HASH-BASED SEARCH
// ---------------------------------------------------------------------------

function hashLookupDemo() {
    // Map provides key-based lookup without scanning an array.
    // Expected lookup is approximately O(1).
    const employeeDepartments = new Map([
        ["E101", "Engineering"],
        ["E102", "Finance"],
        ["E103", "Operations"]
    ]);

    console.log("\nHash-based lookup:");
    console.log(employeeDepartments.get("E102"));
    console.log(employeeDepartments.get("E999") ?? "Employee not found");
}

// ---------------------------------------------------------------------------
// 11. GREEDY ALGORITHM
// ---------------------------------------------------------------------------

function activitySelection(activities) {
    // Greedy rule: choose the activity that finishes earliest.
    // Sorting dominates the complexity: O(n log n).
    const sorted = [...activities].sort((a, b) => a.end - b.end);

    const selected = [];
    let currentEnd = -Infinity;

    for (const activity of sorted) {
        if (activity.start >= currentEnd) {
            selected.push(activity);
            currentEnd = activity.end;
        }
    }

    return selected;
}

// ---------------------------------------------------------------------------
// 12. DYNAMIC PROGRAMMING
// ---------------------------------------------------------------------------

function fibonacciNaive(n) {
    // Deliberately inefficient: repeated subproblems produce exponential
    // growth. It is useful for seeing why dynamic programming matters.
    if (n <= 1) {
        return n;
    }

    return fibonacciNaive(n - 1) + fibonacciNaive(n - 2);
}

function fibonacciDynamic(n) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer.");
    }

    if (n <= 1) {
        return n;
    }

    let previous = 0;
    let current = 1;

    for (let index = 2; index <= n; index += 1) {
        [previous, current] = [current, previous + current];
    }

    return current;
}

// ---------------------------------------------------------------------------
// 13. BREADTH-FIRST SEARCH
// ---------------------------------------------------------------------------

function breadthFirstSearch(graph, start, target) {
    if (!Object.hasOwn(graph, start)) {
        return null;
    }

    const queue = [start];
    let queueIndex = 0;
    const parent = new Map([[start, null]]);

    while (queueIndex < queue.length) {
        const current = queue[queueIndex];
        queueIndex += 1;

        if (current === target) {
            const path = [];
            let node = target;

            while (node !== null) {
                path.push(node);
                node = parent.get(node);
            }

            return path.reverse();
        }

        for (const neighbor of graph[current] ?? []) {
            if (!parent.has(neighbor)) {
                parent.set(neighbor, current);
                queue.push(neighbor);
            }
        }
    }

    return null;
}

// ---------------------------------------------------------------------------
// 14. DEPTH-FIRST SEARCH
// ---------------------------------------------------------------------------

function depthFirstSearch(graph, start, target) {
    const visited = new Set();
    const path = [];

    function visit(node) {
        if (visited.has(node)) {
            return false;
        }

        visited.add(node);
        path.push(node);

        if (node === target) {
            return true;
        }

        for (const neighbor of graph[node] ?? []) {
            if (visit(neighbor)) {
                return true;
            }
        }

        path.pop();
        return false;
    }

    return visit(start) ? [...path] : null;
}

// ---------------------------------------------------------------------------
// 15. REAL-WORLD CASE STUDY: PRODUCT CATALOG
// ---------------------------------------------------------------------------

class ProductCatalog {
    constructor(products) {
        this.products = [...products];

        // Map creates a direct product-ID index.
        this.byId = new Map(
            this.products.map(product => [product.id, product])
        );

        this.byName = new Map(
            this.products.map(product => [product.name.toLowerCase(), product])
        );

        // Sorted representation supports range queries efficiently.
        this.byPrice = [...this.products].sort(
            (a, b) => a.price - b.price
        );

        this.priceValues = this.byPrice.map(product => product.price);
    }

    findById(id) {
        return this.byId.get(id) ?? null;
    }

    findByName(name) {
        return this.byName.get(name.toLowerCase()) ?? null;
    }

    productsUpToPrice(maximumPrice) {
        // lowerBound-like binary search locates the first price > limit.
        const index = upperBound(this.priceValues, maximumPrice);
        return this.byPrice.slice(0, index);
    }

    topRatedInCategory(category, limit = 5) {
        if (limit <= 0) {
            return [];
        }

        const matching = this.products.filter(
            product =>
                product.category.toLowerCase() === category.toLowerCase()
        );

        return matching
            .sort((a, b) => {
                if (b.rating !== a.rating) {
                    return b.rating - a.rating;
                }

                return a.price - b.price;
            })
            .slice(0, limit);
    }

    recommend(category, maximumPrice, limit = 5) {
        const candidates = this.products.filter(product =>
            product.category.toLowerCase() === category.toLowerCase()
            && product.price <= maximumPrice
            && product.stock > 0
        );

        // Ranking is a domain decision rather than a universal algorithm.
        const score = product =>
            product.rating * 10 + 100 / (1 + product.price);

        return candidates
            .sort((a, b) => score(b) - score(a))
            .slice(0, limit);
    }
}

// ---------------------------------------------------------------------------
// 16. ASYNCHRONOUS ALGORITHMIC PROCESSING
// ---------------------------------------------------------------------------

function delay(milliseconds) {
    return new Promise(resolve => setTimeout(resolve, milliseconds));
}

async function asynchronousSearchSimulation(items, target) {
    // Real applications often receive data asynchronously.
    // The search algorithm itself remains separate from data retrieval.
    await delay(10);
    return linearSearch(items, target);
}

// ---------------------------------------------------------------------------
// 17. VALIDATION AND TESTING
// ---------------------------------------------------------------------------

function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

function validateSortAlgorithm(sortFunction, testCases) {
    for (const testCase of testCases) {
        const actual = sortFunction(testCase);
        const expected = [...testCase].sort((a, b) => a - b);

        assert(
            JSON.stringify(actual) === JSON.stringify(expected),
            `${sortFunction.name} failed for ${JSON.stringify(testCase)}`
        );
    }
}

function validateAlgorithms() {
    const testCases = [
        [],
        [1],
        [2, 1],
        [3, 1, 2, 3, 2],
        [-5, 0, 7, -2, 4],
        [9, 9, 9, 1, 1, 5]
    ];

    validateSortAlgorithm(bubbleSort, testCases);
    validateSortAlgorithm(insertionSort, testCases);
    validateSortAlgorithm(selectionSort, testCases);
    validateSortAlgorithm(mergeSort, testCases);
    validateSortAlgorithm(quickSort, testCases);
    validateSortAlgorithm(countingSort, testCases);

    const sorted = [1, 2, 2, 2, 3, 4];

    assert(firstOccurrence(sorted, 2) === 1, "first occurrence");
    assert(lastOccurrence(sorted, 2) === 3, "last occurrence");
    assert(countOccurrences(sorted, 2) === 3, "occurrence count");
}

// Helper required by validation and demonstrations.
function firstOccurrence(items, target) {
    const index = lowerBound(items, target);
    return index < items.length && items[index] === target ? index : -1;
}

function lastOccurrence(items, target) {
    const index = upperBound(items, target) - 1;
    return index >= 0 && items[index] === target ? index : -1;
}

// ---------------------------------------------------------------------------
// 18. PERFORMANCE MEASUREMENT
// ---------------------------------------------------------------------------

function benchmarkSort(sortFunction, values) {
    const start = performance.now();
    sortFunction(values);
    return performance.now() - start;
}

function benchmark() {
    // A deterministic pseudo-random generator makes the demonstration
    // reproducible without external packages.
    let seed = 123456789;

    function randomInteger(min, max) {
        seed = (1664525 * seed + 1013904223) >>> 0;
        return min + (seed % (max - min + 1));
    }

    const values = Array.from(
        { length: 2000 },
        () => randomInteger(-10000, 10000)
    );

    const algorithms = [
        ["Insertion sort", insertionSort],
        ["Merge sort", mergeSort],
        ["Quick sort", quickSort],
        ["Native sort", values => [...values].sort((a, b) => a - b)]
    ];

    console.log("\nPerformance benchmark:");

    for (const [name, sortFunction] of algorithms) {
        const duration = benchmarkSort(sortFunction, values);
        console.log(`${name.padEnd(20)} ${duration.toFixed(3)} ms`);
    }
}

// ---------------------------------------------------------------------------
// 19. MAIN
// ---------------------------------------------------------------------------

async function main() {
    console.log("=".repeat(72));
    console.log("ALGORITHMS: SEARCHING, SORTING, AND ALGORITHMIC THINKING");
    console.log("=".repeat(72));

    const data = [7, 2, 9, 4, 1, 8, 2, 5];

    console.log("\nOriginal data:", data);
    console.log("Linear search for 8:", linearSearch(data, 8));

    const sorted = mergeSort(data);
    console.log("Sorted:", sorted);
    console.log("Binary search for 8:", binarySearch(sorted, 8));

    console.log("\nSorting:");
    console.log("Bubble:", bubbleSort(data));
    console.log("Insertion:", insertionSort(data));
    console.log("Selection:", selectionSort(data));
    console.log("Merge:", mergeSort(data));
    console.log("Quick:", quickSort(data));
    console.log("Counting:", countingSort(data));

    const duplicates = [1, 2, 2, 2, 3, 4];

    console.log("\nBinary-search boundaries:");
    console.log("Data:", duplicates);
    console.log("First 2:", firstOccurrence(duplicates, 2));
    console.log("Last 2:", lastOccurrence(duplicates, 2));
    console.log("Lower bound:", lowerBound(duplicates, 2));
    console.log("Upper bound:", upperBound(duplicates, 2));
    console.log("Count:", countOccurrences(duplicates, 2));

    console.log("\nTwo-pointer search:");
    console.log(
        twoSumSorted([1, 2, 4, 5, 7, 9, 11], 16)
    );

    console.log("\nBinary search over answer space:");
    for (const number of [0, 1, 2, 10, 15, 100]) {
        console.log(
            `floor(sqrt(${number})) = ${integerSquareRoot(number)}`
        );
    }

    console.log("\nGreedy activity selection:");
    console.log(
        activitySelection([
            { start: 1, end: 4 },
            { start: 3, end: 5 },
            { start: 0, end: 6 },
            { start: 5, end: 7 },
            { start: 3, end: 9 },
            { start: 5, end: 9 },
            { start: 6, end: 10 },
            { start: 8, end: 11 }
        ])
    );

    console.log("\nDynamic programming:");
    console.log("Fibonacci(20):", fibonacciDynamic(20));

    hashLookupDemo();
    demonstrateNativeSorting();

    console.log("\nGraph search:");

    const graph = {
        A: ["B", "C"],
        B: ["D", "E"],
        C: ["F"],
        D: [],
        E: ["F"],
        F: []
    };

    console.log("BFS:", breadthFirstSearch(graph, "A", "F"));
    console.log("DFS:", depthFirstSearch(graph, "A", "F"));

    console.log("\nProduct catalog:");

    const catalog = new ProductCatalog([
        {
            id: 101,
            name: "Laptop Pro",
            category: "Computers",
            price: 1200,
            stock: 8,
            rating: 4.8
        },
        {
            id: 102,
            name: "Laptop Air",
            category: "Computers",
            price: 900,
            stock: 12,
            rating: 4.6
        },
        {
            id: 103,
            name: "Workstation X",
            category: "Computers",
            price: 2200,
            stock: 3,
            rating: 4.9
        },
        {
            id: 104,
            name: "Mechanical Keyboard",
            category: "Accessories",
            price: 120,
            stock: 40,
            rating: 4.7
        },
        {
            id: 105,
            name: "Wireless Mouse",
            category: "Accessories",
            price: 60,
            stock: 100,
            rating: 4.5
        },
        {
            id: 106,
            name: "USB Hub",
            category: "Accessories",
            price: 45,
            stock: 0,
            rating: 4.4
        }
    ]);

    console.log("ID 103:", catalog.findById(103));
    console.log("Laptop Air:", catalog.findByName("laptop air"));
    console.log(
        "Products <= 1000:",
        catalog.productsUpToPrice(1000)
    );
    console.log(
        "Top accessories:",
        catalog.topRatedInCategory("Accessories")
    );
    console.log(
        "Computer recommendations:",
        catalog.recommend("Computers", 1500)
    );

    console.log("\nAsynchronous search:");
    console.log(
        "Target index:",
        await asynchronousSearchSimulation([10, 20, 30, 40], 30)
    );

    validateAlgorithms();
    console.log("\nAll correctness checks passed.");

    benchmark();

    console.log("\nAlgorithmic design checklist:");
    console.log("1. Define the exact problem and desired output.");
    console.log("2. Identify input size and input characteristics.");
    console.log("3. Select data structures deliberately.");
    console.log("4. Establish correctness conditions.");
    console.log("5. Choose an algorithm that fits the constraints.");
    console.log("6. Analyze time and space complexity.");
    console.log("7. Test empty, duplicate, invalid, and boundary cases.");
    console.log("8. Separate data acquisition from algorithmic processing.");
    console.log("9. Benchmark when real performance matters.");
    console.log("10. Consider maintainability, security, and failure modes.");
}

main().catch(error => {
    console.error("Program failed:", error.message);
    process.exitCode = 1;
});
