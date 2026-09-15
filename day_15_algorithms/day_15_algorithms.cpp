/*
    Algorithms: Searching, Sorting, and Algorithmic Thinking
    =========================================================

    C++17 industry-style case study:
    A product catalog search and recommendation engine.

    The program demonstrates:
    - Linear search
    - Binary search
    - Binary-search boundaries
    - Multiple sorting algorithms
    - Hash-based indexing
    - Range searching
    - Filtering and ranking
    - Greedy selection
    - Graph traversal
    - Validation and error handling
    - Complexity trade-offs
    - Modular system design

    Compile:
        g++ -std=c++17 -O2 algorithms_case_study.cpp -o algorithms

    Run:
        ./algorithms
*/

#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <queue>
#include <random>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;

// ---------------------------------------------------------------------------
// 1. SEARCHING
// ---------------------------------------------------------------------------

int linearSearch(const vector<int>& values, int target) {
    // Sequential scan.
    // Best case: O(1)
    // Worst case: O(n)
    for (size_t index = 0; index < values.size(); ++index) {
        if (values[index] == target) {
            return static_cast<int>(index);
        }
    }

    return -1;
}

int binarySearch(const vector<int>& values, int target) {
    // Requires sorted input.
    // Each comparison approximately halves the remaining search space.
    // Time: O(log n), auxiliary space: O(1)
    int left = 0;
    int right = static_cast<int>(values.size()) - 1;

    while (left <= right) {
        // This formulation avoids left + right overflow.
        int middle = left + (right - left) / 2;

        if (values[middle] == target) {
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

int lowerBoundIndex(const vector<int>& values, int target) {
    // First position whose value is >= target.
    int left = 0;
    int right = static_cast<int>(values.size());

    while (left < right) {
        int middle = left + (right - left) / 2;

        if (values[middle] < target) {
            left = middle + 1;
        } else {
            right = middle;
        }
    }

    return left;
}

int upperBoundIndex(const vector<int>& values, int target) {
    // First position whose value is > target.
    int left = 0;
    int right = static_cast<int>(values.size());

    while (left < right) {
        int middle = left + (right - left) / 2;

        if (values[middle] <= target) {
            left = middle + 1;
        } else {
            right = middle;
        }
    }

    return left;
}

// ---------------------------------------------------------------------------
// 2. BASIC SORTING
// ---------------------------------------------------------------------------

vector<int> bubbleSort(vector<int> values) {
    // Repeated adjacent swaps.
    // Worst case: O(n^2)
    // Best case with early termination: O(n)
    for (int end = static_cast<int>(values.size()) - 1; end > 0; --end) {
        bool swapped = false;

        for (int index = 0; index < end; ++index) {
            if (values[index] > values[index + 1]) {
                swap(values[index], values[index + 1]);
                swapped = true;
            }
        }

        if (!swapped) {
            break;
        }
    }

    return values;
}

vector<int> insertionSort(vector<int> values) {
    // Efficient for small or nearly sorted collections.
    // Worst case: O(n^2)
    // Best case: O(n)
    for (size_t index = 1; index < values.size(); ++index) {
        int current = values[index];
        int position = static_cast<int>(index) - 1;

        while (position >= 0 && values[position] > current) {
            values[position + 1] = values[position];
            --position;
        }

        values[position + 1] = current;
    }

    return values;
}

vector<int> selectionSort(vector<int> values) {
    // Select the smallest remaining element for each position.
    // Time: O(n^2)
    for (size_t start = 0; start < values.size(); ++start) {
        size_t minimumIndex = start;

        for (size_t index = start + 1; index < values.size(); ++index) {
            if (values[index] < values[minimumIndex]) {
                minimumIndex = index;
            }
        }

        swap(values[start], values[minimumIndex]);
    }

    return values;
}

// ---------------------------------------------------------------------------
// 3. MERGE SORT
// ---------------------------------------------------------------------------

void mergeParts(
    vector<int>& values,
    vector<int>& temporary,
    int left,
    int middle,
    int right
) {
    int leftIndex = left;
    int rightIndex = middle + 1;
    int writeIndex = left;

    while (leftIndex <= middle && rightIndex <= right) {
        // <= preserves stability for equal values.
        if (values[leftIndex] <= values[rightIndex]) {
            temporary[writeIndex++] = values[leftIndex++];
        } else {
            temporary[writeIndex++] = values[rightIndex++];
        }
    }

    while (leftIndex <= middle) {
        temporary[writeIndex++] = values[leftIndex++];
    }

    while (rightIndex <= right) {
        temporary[writeIndex++] = values[rightIndex++];
    }

    for (int index = left; index <= right; ++index) {
        values[index] = temporary[index];
    }
}

void mergeSortRecursive(
    vector<int>& values,
    vector<int>& temporary,
    int left,
    int right
) {
    if (left >= right) {
        return;
    }

    int middle = left + (right - left) / 2;

    mergeSortRecursive(values, temporary, left, middle);
    mergeSortRecursive(values, temporary, middle + 1, right);

    mergeParts(values, temporary, left, middle, right);
}

vector<int> mergeSort(vector<int> values) {
    if (values.empty()) {
        return values;
    }

    vector<int> temporary(values.size());

    mergeSortRecursive(
        values,
        temporary,
        0,
        static_cast<int>(values.size()) - 1
    );

    // Time: O(n log n)
    // Auxiliary space: O(n)
    return values;
}

// ---------------------------------------------------------------------------
// 4. QUICK SORT
// ---------------------------------------------------------------------------

int partitionValues(vector<int>& values, int low, int high) {
    int pivot = values[high];
    int boundary = low;

    for (int index = low; index < high; ++index) {
        if (values[index] <= pivot) {
            swap(values[index], values[boundary]);
            ++boundary;
        }
    }

    swap(values[boundary], values[high]);
    return boundary;
}

void quickSortRecursive(vector<int>& values, int low, int high) {
    if (low >= high) {
        return;
    }

    int pivotIndex = partitionValues(values, low, high);

    quickSortRecursive(values, low, pivotIndex - 1);
    quickSortRecursive(values, pivotIndex + 1, high);
}

vector<int> quickSort(vector<int> values) {
    if (!values.empty()) {
        quickSortRecursive(
            values,
            0,
            static_cast<int>(values.size()) - 1
        );
    }

    // Average: O(n log n)
    // Worst case: O(n^2)
    return values;
}

// ---------------------------------------------------------------------------
// 5. HEAP SORT
// ---------------------------------------------------------------------------

vector<int> heapSort(vector<int> values) {
    // Standard library heap operations use an array-backed binary heap.
    // Build heap: O(n)
    // Repeated extraction: O(n log n)
    make_heap(values.begin(), values.end());

    for (auto end = values.end(); end != values.begin(); --end) {
        pop_heap(values.begin(), end);
    }

    return values;
}

// ---------------------------------------------------------------------------
// 6. PRODUCT MODEL
// ---------------------------------------------------------------------------

struct Product {
    int id;
    string name;
    string category;
    double price;
    int stock;
    double rating;
};

ostream& operator<<(ostream& output, const Product& product) {
    output << product.id
           << " | " << product.name
           << " | " << product.category
           << " | $" << fixed << setprecision(2) << product.price
           << " | stock=" << product.stock
           << " | rating=" << setprecision(1) << product.rating;

    return output;
}

// ---------------------------------------------------------------------------
// 7. PRODUCT CATALOG ENGINE
// ---------------------------------------------------------------------------

class ProductCatalog {
private:
    vector<Product> products;

    // Hash index:
    // Expected lookup is approximately O(1).
    unordered_map<int, size_t> idIndex;

    // A sorted representation is maintained separately because
    // binary search and range queries require ordering.
    vector<size_t> priceOrder;

    // Product names are normalized to lowercase for case-insensitive
    // exact matching in this demonstration.
    unordered_map<string, size_t> nameIndex;

    static string normalizeName(string value) {
        transform(
            value.begin(),
            value.end(),
            value.begin(),
            [](unsigned char character) {
                return static_cast<char>(tolower(character));
            }
        );

        return value;
    }

public:
    explicit ProductCatalog(vector<Product> input)
        : products(move(input)) {

        idIndex.reserve(products.size() * 2 + 1);
        nameIndex.reserve(products.size() * 2 + 1);

        for (size_t index = 0; index < products.size(); ++index) {
            const Product& product = products[index];

            if (idIndex.contains(product.id)) {
                throw invalid_argument("Duplicate product ID.");
            }

            string normalizedName = normalizeName(product.name);

            if (nameIndex.contains(normalizedName)) {
                throw invalid_argument("Duplicate product name.");
            }

            if (product.price < 0.0) {
                throw invalid_argument("Product price cannot be negative.");
            }

            if (product.stock < 0) {
                throw invalid_argument("Product stock cannot be negative.");
            }

            if (product.rating < 0.0 || product.rating > 5.0) {
                throw invalid_argument("Rating must be between 0 and 5.");
            }

            idIndex[product.id] = index;
            nameIndex[normalizedName] = index;
            priceOrder.push_back(index);
        }

        sort(
            priceOrder.begin(),
            priceOrder.end(),
            [this](size_t left, size_t right) {
                if (products[left].price != products[right].price) {
                    return products[left].price < products[right].price;
                }

                return products[left].id < products[right].id;
            }
        );
    }

    optional<Product> findById(int id) const {
        auto iterator = idIndex.find(id);

        if (iterator == idIndex.end()) {
            return nullopt;
        }

        return products[iterator->second];
    }

    optional<Product> findByName(const string& name) const {
        string normalized = normalizeName(name);
        auto iterator = nameIndex.find(normalized);

        if (iterator == nameIndex.end()) {
            return nullopt;
        }

        return products[iterator->second];
    }

    vector<Product> productsUpToPrice(double maximumPrice) const {
        if (maximumPrice < 0.0) {
            return {};
        }

        // Find the first position with price > maximumPrice.
        size_t left = 0;
        size_t right = priceOrder.size();

        while (left < right) {
            size_t middle = left + (right - left) / 2;

            if (products[priceOrder[middle]].price <= maximumPrice) {
                left = middle + 1;
            } else {
                right = middle;
            }
        }

        vector<Product> result;
        result.reserve(left);

        for (size_t index = 0; index < left; ++index) {
            result.push_back(products[priceOrder[index]]);
        }

        // Boundary search is O(log n), but materializing k results
        // requires O(k) additional work.
        return result;
    }

    vector<Product> topRatedInCategory(
        const string& category,
        size_t limit
    ) const {
        if (limit == 0) {
            return {};
        }

        vector<Product> matching;

        for (const Product& product : products) {
            if (product.category == category) {
                matching.push_back(product);
            }
        }

        sort(
            matching.begin(),
            matching.end(),
            [](const Product& left, const Product& right) {
                if (left.rating != right.rating) {
                    return left.rating > right.rating;
                }

                return left.price < right.price;
            }
        );

        if (matching.size() > limit) {
            matching.resize(limit);
        }

        return matching;
    }

    vector<Product> recommend(
        const string& category,
        double maximumPrice,
        size_t limit
    ) const {
        if (maximumPrice < 0.0 || limit == 0) {
            return {};
        }

        vector<pair<double, size_t>> ranked;

        for (size_t index = 0; index < products.size(); ++index) {
            const Product& product = products[index];

            if (
                product.category == category
                && product.price <= maximumPrice
                && product.stock > 0
            ) {
                // The ranking formula is a domain-specific decision.
                // It favors rating while giving affordable products
                // a small additional score.
                double score =
                    product.rating * 10.0
                    + 100.0 / (1.0 + product.price);

                ranked.emplace_back(score, index);
            }
        }

        sort(
            ranked.begin(),
            ranked.end(),
            [](const auto& left, const auto& right) {
                if (left.first != right.first) {
                    return left.first > right.first;
                }

                return left.second < right.second;
            }
        );

        vector<Product> result;

        size_t count = min(limit, ranked.size());
        result.reserve(count);

        for (size_t index = 0; index < count; ++index) {
            result.push_back(products[ranked[index].second]);
        }

        return result;
    }

    size_t size() const {
        return products.size();
    }
};

// ---------------------------------------------------------------------------
// 8. GREEDY ALGORITHM
// ---------------------------------------------------------------------------

struct Activity {
    int start;
    int end;
};

vector<Activity> activitySelection(vector<Activity> activities) {
    // Earliest-finish-time greedy strategy maximizes the number
    // of compatible activities for the classic activity-selection problem.
    sort(
        activities.begin(),
        activities.end(),
        [](const Activity& left, const Activity& right) {
            if (left.end != right.end) {
                return left.end < right.end;
            }

            return left.start < right.start;
        }
    );

    vector<Activity> selected;
    int currentEnd = numeric_limits<int>::min();

    for (const Activity& activity : activities) {
        if (activity.start >= currentEnd) {
            selected.push_back(activity);
            currentEnd = activity.end;
        }
    }

    return selected;
}

// ---------------------------------------------------------------------------
// 9. GRAPH SEARCH
// ---------------------------------------------------------------------------

using Graph = unordered_map<string, vector<string>>;

optional<vector<string>> breadthFirstSearch(
    const Graph& graph,
    const string& start,
    const string& target
) {
    if (!graph.contains(start)) {
        return nullopt;
    }

    queue<string> pending;
    unordered_map<string, optional<string>> parent;

    pending.push(start);
    parent[start] = nullopt;

    while (!pending.empty()) {
        string current = pending.front();
        pending.pop();

        if (current == target) {
            vector<string> path;
            string node = target;

            while (true) {
                path.push_back(node);

                if (!parent[node].has_value()) {
                    break;
                }

                node = *parent[node];
            }

            reverse(path.begin(), path.end());
            return path;
        }

        auto iterator = graph.find(current);

        if (iterator == graph.end()) {
            continue;
        }

        for (const string& neighbor : iterator->second) {
            if (!parent.contains(neighbor)) {
                parent[neighbor] = current;
                pending.push(neighbor);
            }
        }
    }

    return nullopt;
}

optional<vector<string>> depthFirstSearch(
    const Graph& graph,
    const string& start,
    const string& target
) {
    unordered_set<string> visited;
    vector<string> path;

    function<bool(const string&)> visit =
        [&](const string& node) {
            if (visited.contains(node)) {
                return false;
            }

            visited.insert(node);
            path.push_back(node);

            if (node == target) {
                return true;
            }

            auto iterator = graph.find(node);

            if (iterator != graph.end()) {
                for (const string& neighbor : iterator->second) {
                    if (visit(neighbor)) {
                        return true;
                    }
                }
            }

            path.pop_back();
            return false;
        };

    if (visit(start)) {
        return path;
    }

    return nullopt;
}

// ---------------------------------------------------------------------------
// 10. INTEGER SQUARE ROOT USING BINARY SEARCH
// ---------------------------------------------------------------------------

long long integerSquareRoot(long long number) {
    if (number < 0) {
        throw invalid_argument(
            "Integer square root requires a non-negative value."
        );
    }

    if (number < 2) {
        return number;
    }

    long long left = 1;
    long long right = number / 2;
    long long answer = 1;

    while (left <= right) {
        long long middle = left + (right - left) / 2;

        // Avoid multiplication overflow:
        // middle <= number / middle is equivalent to middle² <= number
        // for positive middle.
        if (middle <= number / middle) {
            answer = middle;
            left = middle + 1;
        } else {
            right = middle - 1;
        }
    }

    return answer;
}

// ---------------------------------------------------------------------------
// 11. CORRECTNESS TESTS
// ---------------------------------------------------------------------------

void require(bool condition, const string& message) {
    if (!condition) {
        throw runtime_error("Test failure: " + message);
    }
}

void validateSortingAlgorithms() {
    vector<vector<int>> testCases = {
        {},
        {1},
        {2, 1},
        {3, 1, 2, 3, 2},
        {-5, 0, 7, -2, 4},
        {9, 9, 9, 1, 1, 5}
    };

    for (const auto& testCase : testCases) {
        vector<int> expected = testCase;
        sort(expected.begin(), expected.end());

        require(
            bubbleSort(testCase) == expected,
            "bubble sort"
        );

        require(
            insertionSort(testCase) == expected,
            "insertion sort"
        );

        require(
            selectionSort(testCase) == expected,
            "selection sort"
        );

        require(
            mergeSort(testCase) == expected,
            "merge sort"
        );

        require(
            quickSort(testCase) == expected,
            "quick sort"
        );

        require(
            heapSort(testCase) == expected,
            "heap sort"
        );
    }
}

void validateSearchAlgorithms() {
    vector<int> values = {1, 2, 2, 2, 3, 4};

    require(
        binarySearch(values, 3) != -1,
        "binary search should find 3"
    );

    require(
        binarySearch(values, 99) == -1,
        "binary search should reject absent value"
    );

    require(
        lowerBoundIndex(values, 2) == 1,
        "lower bound"
    );

    require(
        upperBoundIndex(values, 2) == 4,
        "upper bound"
    );

    require(
        upperBoundIndex(values, 2) - lowerBoundIndex(values, 2) == 3,
        "duplicate count"
    );
}

// ---------------------------------------------------------------------------
// 12. PERFORMANCE MEASUREMENT
// ---------------------------------------------------------------------------

template <typename Function>
double measureMilliseconds(Function algorithm, const vector<int>& values) {
    auto start = chrono::steady_clock::now();

    algorithm(values);

    auto finish = chrono::steady_clock::now();

    chrono::duration<double, milli> elapsed = finish - start;
    return elapsed.count();
}

void benchmarkAlgorithms() {
    mt19937 generator(42);
    uniform_int_distribution<int> distribution(-10000, 10000);

    vector<int> values(2000);

    for (int& value : values) {
        value = distribution(generator);
    }

    cout << "\nPerformance benchmark:\n";

    cout << fixed << setprecision(3);

    cout << "Insertion sort: "
         << measureMilliseconds(insertionSort, values)
         << " ms\n";

    cout << "Merge sort:     "
         << measureMilliseconds(mergeSort, values)
         << " ms\n";

    cout << "Quick sort:     "
         << measureMilliseconds(quickSort, values)
         << " ms\n";

    cout << "Heap sort:      "
         << measureMilliseconds(heapSort, values)
         << " ms\n";

    cout << "std::sort:      "
         << measureMilliseconds(
                [](const vector<int>& input) {
                    vector<int> copy = input;
                    sort(copy.begin(), copy.end());
                },
                values
            )
         << " ms\n";
}

// ---------------------------------------------------------------------------
// 13. OUTPUT HELPERS
// ---------------------------------------------------------------------------

void printProducts(
    const string& title,
    const vector<Product>& products
) {
    cout << "\n" << title << "\n";

    if (products.empty()) {
        cout << "No matching products.\n";
        return;
    }

    for (const Product& product : products) {
        cout << "  " << product << "\n";
    }
}

void printPath(
    const string& title,
    const optional<vector<string>>& path
) {
    cout << title;

    if (!path.has_value()) {
        cout << "not found\n";
        return;
    }

    for (size_t index = 0; index < path->size(); ++index) {
        if (index > 0) {
            cout << " -> ";
        }

        cout << (*path)[index];
    }

    cout << "\n";
}

// ---------------------------------------------------------------------------
// 14. MAIN CASE STUDY
// ---------------------------------------------------------------------------

int main() {
    try {
        cout << string(72, '=') << "\n";
        cout << "ALGORITHMS: SEARCHING, SORTING, AND ALGORITHMIC THINKING\n";
        cout << string(72, '=') << "\n";

        // -------------------------------------------------------------------
        // Basic searching and sorting
        // -------------------------------------------------------------------

        vector<int> data = {7, 2, 9, 4, 1, 8, 2, 5};

        cout << "\nOriginal data: ";

        for (int value : data) {
            cout << value << ' ';
        }

        cout << "\n";

        cout << "Linear search for 8: "
             << linearSearch(data, 8)
             << "\n";

        vector<int> sortedData = mergeSort(data);

        cout << "Sorted data: ";

        for (int value : sortedData) {
            cout << value << ' ';
        }

        cout << "\n";

        cout << "Binary search for 8: "
             << binarySearch(sortedData, 8)
             << "\n";

        // -------------------------------------------------------------------
        // Sorting comparison
        // -------------------------------------------------------------------

        cout << "\nSorting algorithms:\n";

        vector<vector<int>> sortedResults = {
            bubbleSort(data),
            insertionSort(data),
            selectionSort(data),
            mergeSort(data),
            quickSort(data),
            heapSort(data)
        };

        const vector<string> names = {
            "Bubble",
            "Insertion",
            "Selection",
            "Merge",
            "Quick",
            "Heap"
        };

        for (size_t index = 0; index < names.size(); ++index) {
            cout << names[index] << ": ";

            for (int value : sortedResults[index]) {
                cout << value << ' ';
            }

            cout << "\n";
        }

        // -------------------------------------------------------------------
        // Binary search boundaries
        // -------------------------------------------------------------------

        vector<int> duplicates = {1, 2, 2, 2, 3, 4};

        cout << "\nBinary-search boundaries:\n";
        cout << "First occurrence of 2: "
             << lowerBoundIndex(duplicates, 2)
             << "\n";

        cout << "Position after last 2: "
             << upperBoundIndex(duplicates, 2)
             << "\n";

        cout << "Number of 2s: "
             << upperBoundIndex(duplicates, 2)
                - lowerBoundIndex(duplicates, 2)
             << "\n";

        // -------------------------------------------------------------------
        // Binary search over an answer space
        // -------------------------------------------------------------------

        cout << "\nInteger square root:\n";

        for (long long value : {0LL, 1LL, 2LL, 10LL, 15LL, 100LL}) {
            cout << "floor(sqrt(" << value << ")) = "
                 << integerSquareRoot(value)
                 << "\n";
        }

        // -------------------------------------------------------------------
        // Greedy algorithm
        // -------------------------------------------------------------------

        vector<Activity> activities = {
            {1, 4},
            {3, 5},
            {0, 6},
            {5, 7},
            {3, 9},
            {5, 9},
            {6, 10},
            {8, 11}
        };

        vector<Activity> selected = activitySelection(activities);

        cout << "\nGreedy activity selection:\n";

        for (const Activity& activity : selected) {
            cout << "[" << activity.start
                 << ", " << activity.end
                 << "] ";
        }

        cout << "\n";

        // -------------------------------------------------------------------
        // Graph searching
        // -------------------------------------------------------------------

        Graph graph = {
            {"A", {"B", "C"}},
            {"B", {"D", "E"}},
            {"C", {"F"}},
            {"D", {}},
            {"E", {"F"}},
            {"F", {}}
        };

        cout << "\nGraph traversal:\n";

        printPath(
            "BFS A -> F: ",
            breadthFirstSearch(graph, "A", "F")
        );

        printPath(
            "DFS A -> F: ",
            depthFirstSearch(graph, "A", "F")
        );

        // -------------------------------------------------------------------
        // Product catalog system
        // -------------------------------------------------------------------

        vector<Product> products = {
            {
                101,
                "Laptop Pro",
                "Computers",
                1200.0,
                8,
                4.8
            },
            {
                102,
                "Laptop Air",
                "Computers",
                900.0,
                12,
                4.6
            },
            {
                103,
                "Workstation X",
                "Computers",
                2200.0,
                3,
                4.9
            },
            {
                104,
                "Mechanical Keyboard",
                "Accessories",
                120.0,
                40,
                4.7
            },
            {
                105,
                "Wireless Mouse",
                "Accessories",
                60.0,
                100,
                4.5
            },
            {
                106,
                "USB Hub",
                "Accessories",
                45.0,
                0,
                4.4
            }
        };

        ProductCatalog catalog(products);

        cout << "\nProduct catalog size: "
             << catalog.size()
             << "\n";

        optional<Product> byId = catalog.findById(103);

        if (byId.has_value()) {
            cout << "ID 103: " << *byId << "\n";
        }

        optional<Product> byName =
            catalog.findByName("laptop air");

        if (byName.has_value()) {
            cout << "Laptop Air: " << *byName << "\n";
        }

        printProducts(
            "Products priced at or below $1000:",
            catalog.productsUpToPrice(1000.0)
        );

        printProducts(
            "Top accessories:",
            catalog.topRatedInCategory("Accessories", 5)
        );

        printProducts(
            "Computer recommendations under $1500:",
            catalog.recommend("Computers", 1500.0, 5)
        );

        // -------------------------------------------------------------------
        // Correctness verification
        // -------------------------------------------------------------------

        validateSortingAlgorithms();
        validateSearchAlgorithms();

        cout << "\nAll correctness checks passed.\n";

        // -------------------------------------------------------------------
        // Performance measurement
        // -------------------------------------------------------------------

        benchmarkAlgorithms();

        // -------------------------------------------------------------------
        // Algorithmic engineering principles
        // -------------------------------------------------------------------

        cout << "\nAlgorithmic engineering checklist:\n";
        cout << "1. Define the problem precisely.\n";
        cout << "2. Identify input size and data characteristics.\n";
        cout << "3. Choose data structures deliberately.\n";
        cout << "4. Establish correctness requirements.\n";
        cout << "5. Analyze time and space complexity.\n";
        cout << "6. Consider preprocessing and indexing costs.\n";
        cout << "7. Test boundary and adversarial cases.\n";
        cout << "8. Measure real performance where appropriate.\n";
        cout << "9. Consider memory locality and allocation behavior.\n";
        cout << "10. Separate algorithmic logic from application architecture.\n";

        return 0;
    }
    catch (const exception& error) {
        cerr << "\nFatal error: " << error.what() << "\n";
        return 1;
    }
}
