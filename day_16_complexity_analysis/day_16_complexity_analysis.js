"use strict";

/*
 * COMPLEXITY ANALYSIS IN JAVASCRIPT
 *
 * This file progresses from basic Big-O reasoning to practical algorithm
 * engineering. It runs with Node.js and requires no external packages.
 */

// ============================================================================
// 1. BASIC COMPLEXITY EXAMPLES
// ============================================================================

function constantTimeAccess(values, index) {
    // JavaScript arrays provide indexed access in ordinary implementations.
    // Complexity model: O(1) for direct indexed access.
    return values[index];
}

function linearSearch(values, target) {
    // At most n values are inspected.
    // Time: O(n), auxiliary space: O(1).
    for (let index = 0; index < values.length; index += 1) {
        if (values[index] === target) {
            return index;
        }
    }
    return -1;
}

function quadraticPairs(values) {
    // Two independent loops produce n * n work.
    // Time: O(n^2), auxiliary space: O(1).
    let count = 0;

    for (let i = 0; i < values.length; i += 1) {
        for (let j = 0; j < values.length; j += 1) {
            count += 1;
        }
    }

    return count;
}

function logarithmicSteps(n) {
    // Halving repeatedly creates logarithmic growth.
    let steps = 0;

    while (n > 1) {
        n = Math.floor(n / 2);
        steps += 1;
    }

    return steps;
}

// ============================================================================
// 2. BINARY SEARCH
// ============================================================================

function binarySearch(values, target) {
    // The input must be sorted.
    // Each iteration removes approximately half the search space.
    // Time: O(log n), auxiliary space: O(1).
    let left = 0;
    let right = values.length - 1;

    while (left <= right) {
        const middle = left + Math.floor((right - left) / 2);

        if (values[middle] === target) {
            return middle;
        }

        if (values[middle] < target) {
            left = middle + 1;
        } else {
            right = middle - 1;
        }
    }

    return -1;
}

// ============================================================================
// 3. MERGE SORT
// ============================================================================

function merge(left, right) {
    const result = [];
    let leftIndex = 0;
    let rightIndex = 0;

    while (leftIndex < left.length && rightIndex < right.length) {
        if (left[leftIndex] <= right[rightIndex]) {
            result.push(left[leftIndex]);
            leftIndex += 1;
        } else {
            result.push(right[rightIndex]);
            rightIndex += 1;
        }
    }

    while (leftIndex < left.length) {
        result.push(left[leftIndex]);
        leftIndex += 1;
    }

    while (rightIndex < right.length) {
        result.push(right[rightIndex]);
        rightIndex += 1;
    }

    return result;
}

function mergeSort(values) {
    // T(n) = 2T(n/2) + O(n) => O(n log n).
    // The output arrays require O(n) additional space.
    if (values.length <= 1) {
        return [...values];
    }

    const middle = Math.floor(values.length / 2);
    const left = mergeSort(values.slice(0, middle));
    const right = mergeSort(values.slice(middle));

    return merge(left, right);
}

// ============================================================================
// 4. ITERATIVE AND RECURSIVE FACTORIAL
// ============================================================================

function factorialRecursive(n) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer");
    }

    if (n <= 1) {
        return 1;
    }

    return n * factorialRecursive(n - 1);
}

function factorialIterative(n) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer");
    }

    let result = 1;

    for (let value = 2; value <= n; value += 1) {
        result *= value;
    }

    return result;
}

// ============================================================================
// 5. DYNAMIC PROGRAMMING
// ============================================================================

function fibonacciNaive(n) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer");
    }

    if (n <= 1) {
        return n;
    }

    return fibonacciNaive(n - 1) + fibonacciNaive(n - 2);
}

function fibonacciMemoized(n, memo = new Map()) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer");
    }

    if (n <= 1) {
        return n;
    }

    if (memo.has(n)) {
        return memo.get(n);
    }

    const result =
        fibonacciMemoized(n - 1, memo) +
        fibonacciMemoized(n - 2, memo);

    memo.set(n, result);
    return result;
}

function fibonacciIterative(n) {
    if (!Number.isInteger(n) || n < 0) {
        throw new RangeError("n must be a non-negative integer");
    }

    let previous = 0;
    let current = 1;

    for (let index = 0; index < n; index += 1) {
        [previous, current] = [current, previous + current];
    }

    return previous;
}

// ============================================================================
// 6. HASH MAP FREQUENCY COUNT
// ============================================================================

function frequencyTable(values) {
    // Map operations are expected O(1) under normal hash-table assumptions.
    // Building a frequency table over n items is expected O(n).
    const frequencies = new Map();

    for (const value of values) {
        frequencies.set(value, (frequencies.get(value) ?? 0) + 1);
    }

    return frequencies;
}

// ============================================================================
// 7. SLIDING WINDOW
// ============================================================================

function maximumWindowSum(values, windowSize) {
    // Brute-force window calculation can be O(n*k).
    // Sliding-window preprocessing makes this O(n).
    if (!Number.isInteger(windowSize) || windowSize <= 0) {
        throw new RangeError("windowSize must be positive");
    }

    if (windowSize > values.length) {
        return null;
    }

    let currentSum = 0;

    for (let index = 0; index < windowSize; index += 1) {
        currentSum += values[index];
    }

    let maximum = currentSum;

    for (let right = windowSize; right < values.length; right += 1) {
        currentSum += values[right];
        currentSum -= values[right - windowSize];
        maximum = Math.max(maximum, currentSum);
    }

    return maximum;
}

// ============================================================================
// 8. GRAPH BFS
// ============================================================================

function breadthFirstSearch(graph, start) {
    // With adjacency lists, each reachable vertex and edge is processed
    // a bounded number of times.
    // Time: O(V + E), space: O(V).
    if (!graph.has(start)) {
        return [];
    }

    const queue = [start];
    const visited = new Set([start]);
    const order = [];
    let head = 0;

    while (head < queue.length) {
        const current = queue[head];
        head += 1;

        order.push(current);

        for (const neighbor of graph.get(current) ?? []) {
            if (!visited.has(neighbor)) {
                visited.add(neighbor);
                queue.push(neighbor);
            }
        }
    }

    return order;
}

// ============================================================================
// 9. PRIORITY QUEUE / MIN HEAP
// ============================================================================

class MinHeap {
    constructor() {
        this.values = [];
    }

    size() {
        return this.values.length;
    }

    peek() {
        return this.values.length === 0 ? undefined : this.values[0];
    }

    push(value) {
        this.values.push(value);
        this.bubbleUp();
    }

    pop() {
        if (this.values.length === 0) {
            return undefined;
        }

        const minimum = this.values[0];
        const last = this.values.pop();

        if (this.values.length > 0) {
            this.values[0] = last;
            this.bubbleDown();
        }

        return minimum;
    }

    bubbleUp() {
        let index = this.values.length - 1;

        while (index > 0) {
            const parent = Math.floor((index - 1) / 2);

            if (this.values[parent] <= this.values[index]) {
                break;
            }

            [this.values[parent], this.values[index]] =
                [this.values[index], this.values[parent]];

            index = parent;
        }
    }

    bubbleDown() {
        let index = 0;

        while (true) {
            const left = index * 2 + 1;
            const right = index * 2 + 2;
            let smallest = index;

            if (
                left < this.values.length &&
                this.values[left] < this.values[smallest]
            ) {
                smallest = left;
            }

            if (
                right < this.values.length &&
                this.values[right] < this.values[smallest]
            ) {
                smallest = right;
            }

            if (smallest === index) {
                break;
            }

            [this.values[index], this.values[smallest]] =
                [this.values[smallest], this.values[index]];

            index = smallest;
        }
    }
}

// ============================================================================
// 10. AMORTIZED ARRAY GROWTH
// ============================================================================

function demonstrateAmortizedPush() {
    // JavaScript arrays dynamically manage storage.
    // A resize can be expensive, but growth policies make repeated append
    // operations effectively O(1) amortized in standard dynamic-array models.
    const values = [];

    for (let index = 0; index < 32; index += 1) {
        values.push(index);
    }

    return values.length;
}

// ============================================================================
// 11. VALIDATION AND EDGE CASES
// ============================================================================

function safeBinarySearch(values, target) {
    if (!Number.isInteger(target)) {
        throw new TypeError("target must be an integer");
    }

    for (let index = 1; index < values.length; index += 1) {
        if (values[index - 1] > values[index]) {
            throw new Error("binary search requires sorted input");
        }
    }

    return binarySearch(values, target);
}

// ============================================================================
// 12. ASYNCHRONOUS COMPLEXITY
// ============================================================================

async function asynchronousPipeline(items) {
    // Asynchronous execution changes when work completes, but does not
    // automatically make an algorithm asymptotically cheaper.
    //
    // Sequential processing of n items: often O(n) total work.
    // Promise.all can overlap I/O, changing wall-clock behavior while total
    // computational or external work can remain O(n).
    const operations = items.map(async (item) => item * 2);
    return Promise.all(operations);
}

// ============================================================================
// 13. COMPLEXITY COMPARISON
// ============================================================================

function printComplexityTable() {
    console.log("\nComplexity reference:");
    console.log("O(1)       constant");
    console.log("O(log n)   logarithmic");
    console.log("O(n)       linear");
    console.log("O(n log n) linearithmic");
    console.log("O(n^2)     quadratic");
    console.log("O(n^3)     cubic");
    console.log("O(2^n)     exponential");
    console.log("O(n!)      factorial");
}

// ============================================================================
// 14. BENCHMARKING
// ============================================================================

function benchmark(functionToMeasure, argument, repetitions = 5) {
    const measurements = [];

    for (let repetition = 0; repetition < repetitions; repetition += 1) {
        const start = performance.now();
        functionToMeasure(argument);
        const elapsed = performance.now() - start;
        measurements.push(elapsed);
    }

    return Math.min(...measurements);
}

// ============================================================================
// 15. REALISTIC CASE STUDY: LOG ANALYSIS
// ============================================================================

class LogAnalyzer {
    constructor(logEntries) {
        this.logEntries = [...logEntries];
    }

    countByLevel() {
        // One pass over n records.
        // Expected O(n) time and O(k) space for k distinct levels.
        const counts = new Map();

        for (const entry of this.logEntries) {
            const level = entry.level;

            counts.set(level, (counts.get(level) ?? 0) + 1);
        }

        return counts;
    }

    findErrors() {
        // O(n) time and O(k) output space, where k is the number of errors.
        return this.logEntries.filter((entry) => entry.level === "ERROR");
    }

    topErrorMessages() {
        // Frequency counting is expected O(n).
        // Sorting k unique messages costs O(k log k).
        const frequencies = new Map();

        for (const entry of this.logEntries) {
            if (entry.level === "ERROR") {
                frequencies.set(
                    entry.message,
                    (frequencies.get(entry.message) ?? 0) + 1
                );
            }
        }

        return [...frequencies.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([message, count]) => ({ message, count }));
    }
}

// ============================================================================
// 16. MAIN DEMONSTRATION
// ============================================================================

async function main() {
    console.log("COMPLEXITY ANALYSIS");
    console.log("===================");
    console.log("Complexity describes how resource requirements grow with input size.");

    const values = [10, 20, 30, 40, 50];

    console.log("\nBasic examples:");
    console.log("Constant access:", constantTimeAccess(values, 2));
    console.log("Linear search:", linearSearch(values, 40));
    console.log("Quadratic pairs:", quadraticPairs(values));
    console.log("Logarithmic steps:", logarithmicSteps(100));

    console.log("\nBinary search:");
    const sortedValues = Array.from({ length: 100 }, (_, index) => index * 2);
    console.log("42 ->", binarySearch(sortedValues, 42));
    console.log("43 ->", binarySearch(sortedValues, 43));

    console.log("\nSorting:");
    const unsorted = [9, 2, 8, 1, 7, 3, 6, 4, 5];
    console.log("Input:", unsorted);
    console.log("Merge sort:", mergeSort(unsorted));

    console.log("\nRecursion:");
    console.log("Recursive factorial:", factorialRecursive(6));
    console.log("Iterative factorial:", factorialIterative(6));

    console.log("\nDynamic programming:");
    console.log("Naive Fibonacci(20):", fibonacciNaive(20));
    console.log("Memoized Fibonacci(40):", fibonacciMemoized(40));
    console.log("Iterative Fibonacci(40):", fibonacciIterative(40));

    console.log("\nHash map:");
    console.log(
        [...frequencyTable(["red", "blue", "red", "green", "blue"]).entries()]
    );

    console.log("\nSliding window:");
    console.log(
        "Maximum sum:",
        maximumWindowSum([2, 1, 5, 1, 3, 2], 3)
    );

    console.log("\nGraph BFS:");
    const graph = new Map([
        ["A", ["B", "C"]],
        ["B", ["A", "D"]],
        ["C", ["A", "E"]],
        ["D", ["B"]],
        ["E", ["C"]]
    ]);
    console.log(breadthFirstSearch(graph, "A"));

    console.log("\nMin heap:");
    const heap = new MinHeap();
    [7, 2, 9, 1, 5].forEach((value) => heap.push(value));

    const heapOutput = [];
    while (heap.size() > 0) {
        heapOutput.push(heap.pop());
    }
    console.log(heapOutput);

    console.log("\nValidation:");
    console.log("Empty search:", safeBinarySearch([], 1));
    try {
        safeBinarySearch([3, 1, 2], 2);
    } catch (error) {
        console.log("Rejected unsorted input:", error.message);
    }

    console.log("\nAsynchronous pipeline:");
    console.log(await asynchronousPipeline([1, 2, 3, 4]));

    console.log("\nAmortized dynamic-array example:");
    console.log("Inserted:", demonstrateAmortizedPush(), "items");

    console.log("\nLog analysis case study:");
    const analyzer = new LogAnalyzer([
        { level: "INFO", message: "Server started" },
        { level: "ERROR", message: "Database unavailable" },
        { level: "WARN", message: "Slow request" },
        { level: "ERROR", message: "Database unavailable" },
        { level: "ERROR", message: "Timeout" },
        { level: "INFO", message: "Health check" }
    ]);

    console.log(
        "Counts:",
        [...analyzer.countByLevel().entries()]
    );
    console.log("Errors:", analyzer.findErrors());
    console.log("Top errors:", analyzer.topErrorMessages());

    console.log("\nBenchmark:");
    const input = Array.from({ length: 100_000 }, (_, index) => index);
    console.log(
        "Linear search benchmark:",
        benchmark((data) => linearSearch(data, -1), input).toFixed(4),
        "ms"
    );

    printComplexityTable();

    console.log("\nImportant engineering distinction:");
    console.log(
        "Big-O describes asymptotic growth; measured runtime also depends on constants,"
        + " implementation, runtime behavior, memory hierarchy, input distribution,"
        + " and system load."
    );
}

main().catch((error) => {
    console.error("Program failed:", error);
    process.exitCode = 1;
});
