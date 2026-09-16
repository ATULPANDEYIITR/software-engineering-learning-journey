#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

/*
 * COMPLEXITY ANALYSIS CASE STUDY
 *
 * Scenario:
 * A production-style log analytics service receives application events.
 * It must:
 *
 *   1. Validate records.
 *   2. Count event levels.
 *   3. Search for records efficiently.
 *   4. Rank frequent error messages.
 *   5. Traverse service dependencies.
 *   6. Demonstrate different complexity trade-offs.
 *
 * Compile:
 *   g++ -std=c++17 -O2 complexity_analysis.cpp -o complexity_analysis
 *
 * Complexity notation:
 *   n = number of log records
 *   k = number of distinct messages
 *   V = number of services
 *   E = number of dependency edges
 */

using namespace std;

// ============================================================================
// BASIC UTILITIES
// ============================================================================

void printSection(const string& title) {
    cout << "\n" << string(78, '=') << "\n";
    cout << title << "\n";
    cout << string(78, '=') << "\n";
}

// ============================================================================
// LOG DATA MODEL
// ============================================================================

enum class LogLevel {
    INFO,
    WARN,
    ERROR
};

string levelToString(LogLevel level) {
    switch (level) {
        case LogLevel::INFO:
            return "INFO";
        case LogLevel::WARN:
            return "WARN";
        case LogLevel::ERROR:
            return "ERROR";
    }

    return "UNKNOWN";
}

struct LogEntry {
    int id;
    LogLevel level;
    string service;
    string message;
    long long timestamp;
};

bool validLogEntry(const LogEntry& entry) {
    // Validation is O(1) because every check examines a fixed number
    // of fields regardless of the total number of records.
    return entry.id >= 0 &&
           !entry.service.empty() &&
           !entry.message.empty() &&
           entry.timestamp >= 0;
}

// ============================================================================
// LINEAR SEARCH
// ============================================================================

const LogEntry* linearSearch(
    const vector<LogEntry>& entries,
    int id
) {
    // Worst case: inspect every record.
    // Time: O(n)
    // Auxiliary space: O(1)
    for (const LogEntry& entry : entries) {
        if (entry.id == id) {
            return &entry;
        }
    }

    return nullptr;
}

// ============================================================================
// BINARY SEARCH
// ============================================================================

int binarySearchById(
    const vector<LogEntry>& entries,
    int id
) {
    // The vector must be sorted by id.
    // Each comparison approximately halves the remaining search interval.
    // Time: O(log n)
    // Auxiliary space: O(1)
    int left = 0;
    int right = static_cast<int>(entries.size()) - 1;

    while (left <= right) {
        const int middle = left + (right - left) / 2;

        if (entries[middle].id == id) {
            return middle;
        }

        if (entries[middle].id < id) {
            left = middle + 1;
        } else {
            right = middle - 1;
        }
    }

    return -1;
}

// ============================================================================
// MERGE SORT
// ============================================================================

void merge(
    vector<LogEntry>& entries,
    vector<LogEntry>& temporary,
    int left,
    int middle,
    int right
) {
    int i = left;
    int j = middle + 1;
    int position = left;

    while (i <= middle && j <= right) {
        if (entries[i].id <= entries[j].id) {
            temporary[position++] = entries[i++];
        } else {
            temporary[position++] = entries[j++];
        }
    }

    while (i <= middle) {
        temporary[position++] = entries[i++];
    }

    while (j <= right) {
        temporary[position++] = entries[j++];
    }

    for (int index = left; index <= right; ++index) {
        entries[index] = temporary[index];
    }
}

void mergeSort(
    vector<LogEntry>& entries,
    vector<LogEntry>& temporary,
    int left,
    int right
) {
    // T(n) = 2T(n/2) + O(n)
    // Therefore: O(n log n).
    if (left >= right) {
        return;
    }

    const int middle = left + (right - left) / 2;

    mergeSort(entries, temporary, left, middle);
    mergeSort(entries, temporary, middle + 1, right);
    merge(entries, temporary, left, middle, right);
}

// ============================================================================
// FREQUENCY ANALYSIS
// ============================================================================

unordered_map<string, int> countErrorMessages(
    const vector<LogEntry>& entries
) {
    // Expected O(n) time under normal unordered_map assumptions.
    // Space: O(k), where k is the number of distinct error messages.
    unordered_map<string, int> counts;

    for (const LogEntry& entry : entries) {
        if (entry.level == LogLevel::ERROR) {
            ++counts[entry.message];
        }
    }

    return counts;
}

// ============================================================================
// TOP ERROR MESSAGES
// ============================================================================

struct MessageCount {
    string message;
    int count;
};

vector<MessageCount> rankErrorMessages(
    const vector<LogEntry>& entries
) {
    const auto counts = countErrorMessages(entries);

    vector<MessageCount> ranked;
    ranked.reserve(counts.size());

    for (const auto& [message, count] : counts) {
        ranked.push_back({message, count});
    }

    // Sorting k distinct messages costs O(k log k).
    sort(
        ranked.begin(),
        ranked.end(),
        [](const MessageCount& a, const MessageCount& b) {
            if (a.count != b.count) {
                return a.count > b.count;
            }
            return a.message < b.message;
        }
    );

    return ranked;
}

// ============================================================================
// GRAPH MODEL
// ============================================================================

class ServiceGraph {
private:
    unordered_map<string, vector<string>> adjacency;

public:
    void addService(const string& service) {
        adjacency.try_emplace(service);
    }

    void addDependency(
        const string& service,
        const string& dependency
    ) {
        adjacency[service].push_back(dependency);
        adjacency.try_emplace(dependency);
    }

    vector<string> breadthFirstTraversal(
        const string& start
    ) const {
        // Adjacency-list BFS:
        // Time O(V + E)
        // Auxiliary space O(V)
        if (!adjacency.count(start)) {
            return {};
        }

        queue<string> pending;
        unordered_set<string> visited;
        vector<string> order;

        pending.push(start);
        visited.insert(start);

        while (!pending.empty()) {
            const string current = pending.front();
            pending.pop();

            order.push_back(current);

            auto iterator = adjacency.find(current);

            if (iterator == adjacency.end()) {
                continue;
            }

            for (const string& neighbor : iterator->second) {
                if (!visited.count(neighbor)) {
                    visited.insert(neighbor);
                    pending.push(neighbor);
                }
            }
        }

        return order;
    }

    bool containsCycle() const {
        // A three-state DFS detects a directed cycle.
        // Time O(V + E)
        // Space O(V)
        enum class State {
            UNVISITED,
            ACTIVE,
            FINISHED
        };

        unordered_map<string, State> state;

        for (const auto& [service, _] : adjacency) {
            state[service] = State::UNVISITED;
        }

        function<bool(const string&)> visit =
            [&](const string& current) -> bool {
                state[current] = State::ACTIVE;

                const auto iterator = adjacency.find(current);

                if (iterator != adjacency.end()) {
                    for (const string& neighbor : iterator->second) {
                        if (state[neighbor] == State::ACTIVE) {
                            return true;
                        }

                        if (state[neighbor] == State::UNVISITED &&
                            visit(neighbor)) {
                            return true;
                        }
                    }
                }

                state[current] = State::FINISHED;
                return false;
            };

        for (const auto& [service, _] : adjacency) {
            if (state[service] == State::UNVISITED &&
                visit(service)) {
                return true;
            }
        }

        return false;
    }
};

// ============================================================================
// LOG ANALYZER
// ============================================================================

class LogAnalyzer {
private:
    vector<LogEntry> entries;

public:
    explicit LogAnalyzer(vector<LogEntry> input)
        : entries(std::move(input)) {
        for (const LogEntry& entry : entries) {
            if (!validLogEntry(entry)) {
                throw invalid_argument("invalid log record");
            }
        }
    }

    const vector<LogEntry>& getEntries() const {
        return entries;
    }

    unordered_map<LogLevel, int> countLevels() const {
        // The number of log levels is fixed, but a general hash-map approach
        // is shown to illustrate frequency analysis.
        // Time: O(n)
        // Space: O(1) with a fixed number of levels.
        unordered_map<LogLevel, int> counts;

        for (const LogEntry& entry : entries) {
            ++counts[entry.level];
        }

        return counts;
    }

    vector<LogEntry> errors() const {
        // Time O(n)
        // Output space O(k), where k is the number of error records.
        vector<LogEntry> result;

        for (const LogEntry& entry : entries) {
            if (entry.level == LogLevel::ERROR) {
                result.push_back(entry);
            }
        }

        return result;
    }

    vector<LogEntry> sortedById() const {
        vector<LogEntry> result = entries;

        if (result.empty()) {
            return result;
        }

        vector<LogEntry> temporary(result.size());

        mergeSort(
            result,
            temporary,
            0,
            static_cast<int>(result.size()) - 1
        );

        return result;
    }

    vector<MessageCount> topErrors() const {
        return rankErrorMessages(entries);
    }
};

// ============================================================================
// TWO-POINTER EXAMPLE
// ============================================================================

bool twoSumSorted(
    const vector<int>& values,
    int target
) {
    // Requires sorted input.
    // Time O(n)
    // Auxiliary space O(1)
    size_t left = 0;
    size_t right = values.size();

    if (values.size() < 2) {
        return false;
    }

    --right;

    while (left < right) {
        const long long sum =
            static_cast<long long>(values[left]) +
            static_cast<long long>(values[right]);

        if (sum == target) {
            return true;
        }

        if (sum < target) {
            ++left;
        } else {
            --right;
        }
    }

    return false;
}

// ============================================================================
// PREFIX SUM
// ============================================================================

class PrefixSum {
private:
    vector<long long> prefix;

public:
    explicit PrefixSum(const vector<int>& values) {
        // Preprocessing: O(n)
        // Space: O(n)
        prefix.reserve(values.size() + 1);
        prefix.push_back(0);

        for (int value : values) {
            prefix.push_back(prefix.back() + value);
        }
    }

    long long rangeSum(
        size_t left,
        size_t right
    ) const {
        if (left > right || right >= prefix.size() - 1) {
            throw out_of_range("invalid range");
        }

        // Every query is O(1).
        return prefix[right + 1] - prefix[left];
    }
};

// ============================================================================
// AMORTIZED ANALYSIS EXAMPLE
// ============================================================================

void demonstrateDynamicArrayGrowth() {
    printSection("Amortized dynamic-array growth");

    vector<int> values;

    size_t previousCapacity = values.capacity();
    int reallocations = 0;

    for (int value = 0; value < 64; ++value) {
        values.push_back(value);

        if (values.capacity() != previousCapacity) {
            ++reallocations;
            previousCapacity = values.capacity();
        }
    }

    cout << "Elements inserted: " << values.size() << "\n";
    cout << "Capacity: " << values.capacity() << "\n";
    cout << "Observed reallocations: " << reallocations << "\n";
    cout << "Repeated push_back is modeled as O(1) amortized.\n";
}

// ============================================================================
// RECURSION AND DYNAMIC PROGRAMMING
// ============================================================================

long long fibonacciNaive(int n) {
    if (n < 0) {
        throw invalid_argument("n must be non-negative");
    }

    if (n <= 1) {
        return n;
    }

    return fibonacciNaive(n - 1) + fibonacciNaive(n - 2);
}

long long fibonacciMemoized(
    int n,
    unordered_map<int, long long>& memo
) {
    if (n < 0) {
        throw invalid_argument("n must be non-negative");
    }

    if (n <= 1) {
        return n;
    }

    const auto found = memo.find(n);

    if (found != memo.end()) {
        return found->second;
    }

    const long long result =
        fibonacciMemoized(n - 1, memo) +
        fibonacciMemoized(n - 2, memo);

    memo[n] = result;
    return result;
}

long long fibonacciIterative(int n) {
    if (n < 0) {
        throw invalid_argument("n must be non-negative");
    }

    long long previous = 0;
    long long current = 1;

    for (int index = 0; index < n; ++index) {
        const long long next = previous + current;
        previous = current;
        current = next;
    }

    return previous;
}

// ============================================================================
// BENCHMARK
// ============================================================================

template <typename Function>
double benchmarkMilliseconds(
    Function function,
    int repetitions = 5
) {
    double best = numeric_limits<double>::max();

    for (int repetition = 0; repetition < repetitions; ++repetition) {
        const auto start = chrono::steady_clock::now();

        function();

        const auto finish = chrono::steady_clock::now();

        const double elapsed =
            chrono::duration<double, milli>(finish - start).count();

        best = min(best, elapsed);
    }

    return best;
}

// ============================================================================
// MAIN CASE STUDY
// ============================================================================

int main() {
    try {
        printSection("Complexity analysis: production log analytics");

        cout << fixed << setprecision(4);

        // --------------------------------------------------------------------
        // Basic asymptotic classes
        // --------------------------------------------------------------------

        printSection("Asymptotic classes");

        cout << "O(1):       constant\n";
        cout << "O(log n):   logarithmic\n";
        cout << "O(n):       linear\n";
        cout << "O(n log n): linearithmic\n";
        cout << "O(n^2):     quadratic\n";
        cout << "O(n^3):     cubic\n";
        cout << "O(2^n):     exponential\n";
        cout << "O(n!):      factorial\n";

        // --------------------------------------------------------------------
        // Build realistic data
        // --------------------------------------------------------------------

        vector<LogEntry> entries = {
            {100, LogLevel::INFO, "gateway", "Request accepted", 1000},
            {101, LogLevel::ERROR, "database", "Connection timeout", 1001},
            {102, LogLevel::WARN, "gateway", "Slow request", 1002},
            {103, LogLevel::ERROR, "database", "Connection timeout", 1003},
            {104, LogLevel::ERROR, "payments", "Payment provider unavailable", 1004},
            {105, LogLevel::INFO, "gateway", "Health check", 1005},
            {106, LogLevel::ERROR, "database", "Connection timeout", 1006},
            {107, LogLevel::WARN, "search", "Slow query", 1007},
            {108, LogLevel::INFO, "search", "Index loaded", 1008}
        };

        LogAnalyzer analyzer(entries);

        // --------------------------------------------------------------------
        // Validation
        // --------------------------------------------------------------------

        printSection("Validation");

        cout << "Validated " << entries.size() << " records.\n";

        // --------------------------------------------------------------------
        // Linear search
        // --------------------------------------------------------------------

        printSection("Linear search");

        const LogEntry* found = linearSearch(entries, 106);

        if (found != nullptr) {
            cout << "Found ID 106: "
                 << found->service << " / "
                 << found->message << "\n";
        } else {
            cout << "ID 106 not found.\n";
        }

        cout << "Time: O(n)\n";
        cout << "Auxiliary space: O(1)\n";

        // --------------------------------------------------------------------
        // Sorting and binary search
        // --------------------------------------------------------------------

        printSection("Sorting followed by binary search");

        vector<LogEntry> sortedEntries = analyzer.sortedById();

        cout << "Sorted IDs: ";

        for (const LogEntry& entry : sortedEntries) {
            cout << entry.id << ' ';
        }

        cout << "\n";

        const int position = binarySearchById(sortedEntries, 106);

        cout << "Binary-search position of ID 106: "
             << position << "\n";

        cout << "Merge sort: O(n log n)\n";
        cout << "Merge-sort auxiliary storage: O(n)\n";
        cout << "Binary search: O(log n)\n";
        cout << "Combined one-time pipeline: O(n log n)\n";

        // --------------------------------------------------------------------
        // Frequency analysis
        // --------------------------------------------------------------------

        printSection("Frequency analysis");

        const auto levelCounts = analyzer.countLevels();

        for (const auto& [level, count] : levelCounts) {
            cout << levelToString(level) << ": " << count << "\n";
        }

        cout << "Expected time: O(n)\n";
        cout << "Auxiliary space: O(1) for fixed levels\n";

        // --------------------------------------------------------------------
        // Top errors
        // --------------------------------------------------------------------

        printSection("Top error messages");

        const auto topErrors = analyzer.topErrors();

        for (const MessageCount& item : topErrors) {
            cout << item.message << ": "
                 << item.count << "\n";
        }

        cout << "Counting: expected O(n)\n";
        cout << "Ranking k messages: O(k log k)\n";
        cout << "Total: O(n + k log k)\n";

        // --------------------------------------------------------------------
        // Graph case study
        // --------------------------------------------------------------------

        printSection("Service dependency graph");

        ServiceGraph services;

        services.addDependency("gateway", "auth");
        services.addDependency("gateway", "search");
        services.addDependency("auth", "database");
        services.addDependency("payments", "database");
        services.addDependency("search", "database");

        const auto traversal =
            services.breadthFirstTraversal("gateway");

        cout << "BFS from gateway: ";

        for (const string& service : traversal) {
            cout << service << ' ';
        }

        cout << "\n";

        cout << "BFS time: O(V + E)\n";
        cout << "BFS space: O(V)\n";
        cout << "Contains dependency cycle: "
             << (services.containsCycle() ? "yes" : "no")
             << "\n";

        // --------------------------------------------------------------------
        // Two-pointer optimization
        // --------------------------------------------------------------------

        printSection("Two-pointer optimization");

        const vector<int> responseTimes = {
            10, 20, 30, 40, 50, 60, 70
        };

        cout << "Pair totaling 90 exists: "
             << (twoSumSorted(responseTimes, 90) ? "yes" : "no")
             << "\n";

        cout << "Brute-force pair search: O(n^2)\n";
        cout << "Two-pointer search: O(n)\n";
        cout << "Requirement: sorted input\n";

        // --------------------------------------------------------------------
        // Prefix sums
        // --------------------------------------------------------------------

        printSection("Prefix sums");

        const vector<int> requestsPerMinute = {
            10, 12, 15, 9, 20, 18, 11
        };

        PrefixSum prefix(requestsPerMinute);

        cout << "Requests from minute 1 through 4: "
             << prefix.rangeSum(1, 4)
             << "\n";

        cout << "Preprocessing: O(n)\n";
        cout << "Each range query: O(1)\n";
        cout << "Extra storage: O(n)\n";

        // --------------------------------------------------------------------
        // Fibonacci comparison
        // --------------------------------------------------------------------

        printSection("Recursion versus dynamic programming");

        cout << "Naive Fibonacci(20): "
             << fibonacciNaive(20) << "\n";

        unordered_map<int, long long> memo;

        cout << "Memoized Fibonacci(40): "
             << fibonacciMemoized(40, memo) << "\n";

        cout << "Iterative Fibonacci(40): "
             << fibonacciIterative(40) << "\n";

        cout << "Naive Fibonacci time: approximately O(2^n)\n";
        cout << "Memoized Fibonacci time: O(n)\n";
        cout << "Memoized space: O(n)\n";
        cout << "Iterative Fibonacci space: O(1)\n";

        // --------------------------------------------------------------------
        // Amortized complexity
        // --------------------------------------------------------------------

        demonstrateDynamicArrayGrowth();

        // --------------------------------------------------------------------
        // Empirical measurement
        // --------------------------------------------------------------------

        printSection("Empirical measurement");

        vector<LogEntry> largeDataset;

        constexpr int datasetSize = 100000;

        largeDataset.reserve(datasetSize);

        for (int index = 0; index < datasetSize; ++index) {
            largeDataset.push_back({
                index,
                index % 10 == 0 ? LogLevel::ERROR : LogLevel::INFO,
                "service",
                "Synthetic event",
                index
            });
        }

        const double linearTime =
            benchmarkMilliseconds(
                [&]() {
                    volatile const LogEntry* result =
                        linearSearch(largeDataset, -1);
                    (void)result;
                }
            );

        const double sortTime =
            benchmarkMilliseconds(
                [&]() {
                    vector<LogEntry> copy = largeDataset;
                    vector<LogEntry> temporary(copy.size());

                    mergeSort(
                        copy,
                        temporary,
                        0,
                        static_cast<int>(copy.size()) - 1
                    );
                },
                1
            );

        cout << "Linear-search benchmark: "
             << linearTime << " ms\n";

        cout << "Merge-sort benchmark: "
             << sortTime << " ms\n";

        cout << "Measurements vary with hardware, compiler optimization, "
                "cache state, memory allocation, and system load.\n";

        // --------------------------------------------------------------------
        // Edge cases
        // --------------------------------------------------------------------

        printSection("Edge cases");

        vector<LogEntry> empty;

        cout << "Empty linear search: "
             << (linearSearch(empty, 1) == nullptr ? "not found" : "found")
             << "\n";

        cout << "Empty binary search: "
             << binarySearchById(empty, 1)
             << "\n";

        try {
            LogEntry invalidEntry{
                -1,
                LogLevel::ERROR,
                "",
                "",
                -1
            };

            if (!validLogEntry(invalidEntry)) {
                throw invalid_argument("invalid record rejected");
            }
        } catch (const exception& error) {
            cout << "Validation failure handled: "
                 << error.what() << "\n";
        }

        // --------------------------------------------------------------------
        // Complexity and engineering trade-offs
        // --------------------------------------------------------------------

        printSection("Engineering trade-offs");

        cout << "1. Linear search needs no preprocessing but costs O(n) per query.\n";
        cout << "2. Sorting costs O(n log n), after which binary search is O(log n).\n";
        cout << "3. Hash maps provide expected O(1) lookup but consume memory.\n";
        cout << "4. Prefix sums spend O(n) preprocessing and O(n) memory to make "
                "range queries O(1).\n";
        cout << "5. Merge sort offers predictable O(n log n) time but needs "
                "additional memory.\n";
        cout << "6. Graph traversal naturally depends on both V and E.\n";

        // --------------------------------------------------------------------
        // Security considerations
        // --------------------------------------------------------------------

        printSection("Security and resource considerations");

        cout << "Untrusted input can create resource-exhaustion risks.\n";
        cout << "Production systems should enforce input-size limits.\n";
        cout << "Recursive algorithms should not accept uncontrolled depth.\n";
        cout << "Hash-based structures should consider adversarial collision behavior.\n";
        cout << "Complexity analysis does not by itself establish security.\n";

        // --------------------------------------------------------------------
        // Final reference
        // --------------------------------------------------------------------

        printSection("Complexity reference");

        cout << left;
        cout << setw(24) << "Algorithm"
             << setw(18) << "Typical time"
             << "Typical space\n";

        cout << string(58, '-') << "\n";

        cout << setw(24) << "Array access"
             << setw(18) << "O(1)"
             << "O(1)\n";

        cout << setw(24) << "Linear search"
             << setw(18) << "O(n)"
             << "O(1)\n";

        cout << setw(24) << "Binary search"
             << setw(18) << "O(log n)"
             << "O(1)\n";

        cout << setw(24) << "Merge sort"
             << setw(18) << "O(n log n)"
             << "O(n)\n";

        cout << setw(24) << "Hash lookup"
             << setw(18) << "O(1) expected"
             << "O(n)\n";

        cout << setw(24) << "BFS / DFS"
             << setw(18) << "O(V + E)"
             << "O(V)\n";

        cout << setw(24) << "Naive Fibonacci"
             << setw(18) << "O(2^n) approx."
             << "O(n)\n";

        cout << "\nCase study completed successfully.\n";

        return 0;
    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }
}
