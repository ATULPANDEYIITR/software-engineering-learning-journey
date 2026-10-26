#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

enum class AccessPath {
    SequentialScan,
    IndexScan,
    IndexOnlyScan
};

enum class JoinAlgorithm {
    NestedLoop,
    HashJoin,
    MergeJoin
};

std::string toString(AccessPath path) {
    switch (path) {
        case AccessPath::SequentialScan: return "Sequential Scan";
        case AccessPath::IndexScan: return "Index Scan";
        case AccessPath::IndexOnlyScan: return "Index Only Scan";
    }
    return "Unknown";
}

std::string toString(JoinAlgorithm algorithm) {
    switch (algorithm) {
        case JoinAlgorithm::NestedLoop: return "Nested Loop";
        case JoinAlgorithm::HashJoin: return "Hash Join";
        case JoinAlgorithm::MergeJoin: return "Merge Join";
    }
    return "Unknown";
}

struct ColumnStats {
    std::string name;
    std::size_t distinctValues;
    double nullFraction{0.0};
};

struct Index {
    std::string name;
    std::vector<std::string> columns;
    std::vector<std::string> coveringColumns;
    bool unique{false};

    bool startsWith(const std::string& column) const {
        return !columns.empty() && columns.front() == column;
    }

    bool covers(const std::vector<std::string>& projected) const {
        for (const auto& column : projected) {
            bool found = std::find(columns.begin(), columns.end(), column) != columns.end();
            found = found ||
                    std::find(
                        coveringColumns.begin(),
                        coveringColumns.end(),
                        column
                    ) != coveringColumns.end();

            if (!found) {
                return false;
            }
        }
        return true;
    }
};

struct TableStats {
    std::string name;
    double rows;
    double pages;
    std::map<std::string, ColumnStats> columns;
    std::vector<Index> indexes;

    const Index* findIndex(const std::string& column) const {
        for (const auto& index : indexes) {
            if (index.startsWith(column)) {
                return &index;
            }
        }
        return nullptr;
    }
};

struct Predicate {
    std::string column;
    std::string op;
    std::string value;

    double selectivity(const TableStats& table) const {
        const auto iterator = table.columns.find(column);

        if (iterator == table.columns.end()) {
            return 0.1;
        }

        const auto& stats = iterator->second;

        if (op == "=") {
            return std::max(
                1.0 / static_cast<double>(std::max<std::size_t>(stats.distinctValues, 1)),
                0.000001
            );
        }

        if (op == "<" || op == "<=" || op == ">" || op == ">=") {
            return 0.33;
        }

        if (op == "IS NULL") {
            return std::max(stats.nullFraction, 0.000001);
        }

        if (op == "IS NOT NULL") {
            return std::max(1.0 - stats.nullFraction, 0.000001);
        }

        if (op == "LIKE") {
            return 0.05;
        }

        return 0.25;
    }
};

struct ScanPlan {
    const TableStats* table;
    AccessPath path;
    double estimatedRows;
    double startupCost;
    double totalCost;
    std::string reason;
};

struct JoinPlan {
    JoinAlgorithm algorithm;
    double leftRows;
    double rightRows;
    double outputRows;
    double cost;
    std::string reason;
};

struct QueryPlan {
    std::string sql;
    std::vector<ScanPlan> scans;
    std::vector<JoinPlan> joins;
    double sortCost;
    double aggregateCost;

    double totalCost() const {
        double total = sortCost + aggregateCost;

        for (const auto& scan : scans) {
            total += scan.totalCost;
        }

        for (const auto& join : joins) {
            total += join.cost;
        }

        return total;
    }
};

class Optimizer {
private:
    static constexpr double seqPageCost = 1.0;
    static constexpr double randomPageCost = 4.0;
    static constexpr double cpuTupleCost = 0.01;
    static constexpr double cpuIndexTupleCost = 0.005;

public:
    ScanPlan estimateScan(
        const TableStats& table,
        const std::vector<Predicate>& predicates,
        const std::vector<std::string>& projected
    ) const {
        double selectivity = 1.0;

        for (const auto& predicate : predicates) {
            selectivity *= predicate.selectivity(table);
        }

        const double estimatedRows =
            std::max(1.0, table.rows * selectivity);

        const Index* usableIndex = nullptr;

        for (const auto& predicate : predicates) {
            usableIndex = table.findIndex(predicate.column);
            if (usableIndex != nullptr) {
                break;
            }
        }

        const bool selective = estimatedRows < table.rows * 0.20;

        if (usableIndex != nullptr && selective) {
            const bool covering = usableIndex->covers(projected);

            const double indexPages =
                std::max(1.0, std::log2(std::max(table.pages, 2.0)));

            const double heapPages =
                std::min(
                    table.pages,
                    std::max(
                        1.0,
                        estimatedRows / std::max(table.rows / table.pages, 1.0)
                    )
                );

            const double startup = indexPages * randomPageCost;

            const double total =
                startup +
                heapPages * randomPageCost +
                estimatedRows * cpuIndexTupleCost;

            return {
                &table,
                covering ? AccessPath::IndexOnlyScan : AccessPath::IndexScan,
                estimatedRows,
                startup,
                total,
                "Selective predicates justify indexed access."
            };
        }

        const double total =
            table.pages * seqPageCost +
            table.rows * cpuTupleCost;

        return {
            &table,
            AccessPath::SequentialScan,
            estimatedRows,
            0.0,
            total,
            usableIndex
                ? "The index is not selective enough under this cost model."
                : "No suitable predicate index exists."
        };
    }

    JoinPlan chooseJoin(
        double leftRows,
        double rightRows,
        double selectivity,
        bool indexedInner
    ) const {
        const double outputRows =
            std::max(1.0, leftRows * rightRows * selectivity);

        const double nestedLoop =
            leftRows *
            (indexedInner
                 ? std::log2(std::max(rightRows, 2.0))
                 : rightRows) *
            0.01;

        const double hashJoin =
            (leftRows + rightRows) * 0.03;

        const double mergeJoin =
            (
                leftRows * std::log2(std::max(leftRows, 2.0)) +
                rightRows * std::log2(std::max(rightRows, 2.0))
            ) *
            0.005;

        struct Candidate {
            JoinAlgorithm algorithm;
            double cost;
            std::string reason;
        };

        std::vector<Candidate> candidates{
            {
                JoinAlgorithm::NestedLoop,
                nestedLoop,
                "Efficient when the outer input is small or the inner side is indexed."
            },
            {
                JoinAlgorithm::HashJoin,
                hashJoin,
                "Suitable for large equality joins."
            },
            {
                JoinAlgorithm::MergeJoin,
                mergeJoin,
                "Useful when both inputs are ordered."
            }
        };

        const auto best = std::min_element(
            candidates.begin(),
            candidates.end(),
            [](const Candidate& a, const Candidate& b) {
                return a.cost < b.cost;
            }
        );

        return {
            best->algorithm,
            leftRows,
            rightRows,
            outputRows,
            best->cost,
            best->reason
        };
    }
};

class GovernanceEngine {
public:
    static void validate(const TableStats& table) {
        if (table.name.empty()) {
            throw std::invalid_argument("Table name cannot be empty.");
        }

        if (table.rows <= 0 || table.pages <= 0) {
            throw std::invalid_argument("Rows and pages must be positive.");
        }

        for (const auto& [name, stats] : table.columns) {
            if (name.empty() || stats.distinctValues == 0) {
                throw std::invalid_argument(
                    "Column statistics contain invalid values."
                );
            }
        }
    }
};

TableStats createOrders(bool optimized) {
    TableStats table{
        "orders",
        2500000,
        125000,
        {
            {"id", {"id", 2500000, 0.0}},
            {"customer_id", {"customer_id", 180000, 0.0}},
            {"status", {"status", 5, 0.0}},
            {"created_at", {"created_at", 900, 0.0}},
            {"total_amount", {"total_amount", 1000000, 0.0}}
        },
        {
            {"orders_pkey", {"id"}, {}, true},
            {"idx_orders_customer", {"customer_id"}, {}, false},
            {"idx_orders_created", {"created_at"}, {}, false},
            {"idx_orders_status_created", {"status", "created_at"}, {}, false}
        }
    };

    if (optimized) {
        table.indexes.push_back({
            "idx_orders_status_created_covering",
            {"status", "created_at"},
            {"customer_id", "total_amount"},
            false
        });
    }

    return table;
}

TableStats createCustomers() {
    return {
        "customers",
        180000,
        12000,
        {
            {"id", {"id", 180000, 0.0}},
            {"region", {"region", 8, 0.0}},
            {"customer_tier", {"customer_tier", 4, 0.0}},
            {"email", {"email", 180000, 0.0}}
        },
        {
            {"customers_pkey", {"id"}, {}, true},
            {"idx_customers_region", {"region"}, {}, false}
        }
    };
}

QueryPlan buildPlan(bool optimized) {
    const TableStats orders = createOrders(optimized);
    const TableStats customers = createCustomers();

    GovernanceEngine::validate(orders);
    GovernanceEngine::validate(customers);

    Optimizer optimizer;

    const std::vector<Predicate> predicates{
        {"status", "=", "completed"},
        {"created_at", ">=", "2026-01-01"}
    };

    const auto orderScan = optimizer.estimateScan(
        orders,
        predicates,
        {"customer_id", "total_amount"}
    );

    const auto customerScan = optimizer.estimateScan(
        customers,
        {},
        {"id", "region"}
    );

    const auto join = optimizer.chooseJoin(
        orderScan.estimatedRows,
        customerScan.estimatedRows,
        1.0 / customers.rows,
        true
    );

    return {
        R"(
SELECT c.region, SUM(o.total_amount)
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.status = 'completed'
  AND o.created_at >= DATE '2026-01-01'
GROUP BY c.region
ORDER BY SUM(o.total_amount) DESC;
)",
        {orderScan, customerScan},
        {join},
        join.outputRows *
            std::log2(std::max(join.outputRows, 2.0)) *
            0.02,
        join.outputRows * 0.02
    };
}

void printPlan(const QueryPlan& plan, const std::string& label) {
    std::cout << "\n" << std::string(78, '=') << '\n';
    std::cout << label << '\n';
    std::cout << std::string(78, '=') << '\n';

    std::cout << "Estimated total cost: "
              << std::fixed << std::setprecision(2)
              << plan.totalCost() << "\n\n";

    for (const auto& scan : plan.scans) {
        std::cout << "Table:          " << scan.table->name << '\n'
                  << "Access path:    " << toString(scan.path) << '\n'
                  << "Estimated rows: " << scan.estimatedRows << '\n'
                  << "Total cost:     " << scan.totalCost << '\n'
                  << "Reason:         " << scan.reason << "\n\n";
    }

    for (const auto& join : plan.joins) {
        std::cout << "Join:            " << toString(join.algorithm) << '\n'
                  << "Left rows:       " << join.leftRows << '\n'
                  << "Right rows:      " << join.rightRows << '\n'
                  << "Output rows:     " << join.outputRows << '\n'
                  << "Join cost:       " << join.cost << '\n'
                  << "Reason:          " << join.reason << "\n\n";
    }

    std::cout << "Sort cost:       " << plan.sortCost << '\n'
              << "Aggregate cost:  " << plan.aggregateCost << '\n';
}

void runEdgeCases() {
    Optimizer optimizer;
    TableStats orders = createOrders(false);

    const auto fullScan = optimizer.estimateScan(
        orders,
        {},
        {"id"}
    );

    if (fullScan.path != AccessPath::SequentialScan) {
        throw std::runtime_error("Full-table scan edge case failed.");
    }

    const auto unknownPredicate = optimizer.estimateScan(
        orders,
        {{"unknown", "=", "value"}},
        {"id"}
    );

    if (unknownPredicate.estimatedRows < 1) {
        throw std::runtime_error("Unknown-column validation failed.");
    }
}

int main() {
    try {
        runEdgeCases();

        const QueryPlan baseline = buildPlan(false);
        const QueryPlan optimized = buildPlan(true);

        printPlan(baseline, "BASELINE QUERY");
        printPlan(optimized, "OPTIMIZED QUERY");

        const double improvement =
            ((baseline.totalCost() - optimized.totalCost()) /
             baseline.totalCost()) *
            100.0;

        std::cout << "\n" << std::string(78, '=') << '\n';
        std::cout << "OPTIMIZATION RESULT\n";
        std::cout << std::string(78, '=') << '\n';
        std::cout << "Baseline cost:  " << baseline.totalCost() << '\n';
        std::cout << "Optimized cost: " << optimized.totalCost() << '\n';
        std::cout << "Change:         " << improvement << "%\n";

        std::cout << "\nENGINEERING CONTROLS\n";
        std::cout << "1. Compare estimated rows with actual execution rows.\n";
        std::cout << "2. Refresh statistics after major data changes.\n";
        std::cout << "3. Avoid indexes that provide little read benefit but add write cost.\n";
        std::cout << "4. Use parameterized SQL in application code.\n";
        std::cout << "5. Benchmark plans with production-like cardinalities.\n";
        std::cout << "6. Treat memory limits as part of join and sort planning.\n";
    }
    catch (const std::exception& error) {
        std::cerr << "Optimization analysis failed: "
                  << error.what() << '\n';
        return 1;
    }

    return 0;
}
