#include <algorithm>
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * C++17 repository-style indexing and query-performance engine.
 *
 * The engine models:
 *   - rows and table storage
 *   - composite B-tree-style indexes
 *   - covering indexes
 *   - partial indexes
 *   - selectivity-based cost estimation
 *   - sequential/index/index-only plans
 *   - merge eligibility-style rule evaluation for database access
 *
 * It intentionally uses an in-memory representation so that the
 * indexing decisions can be inspected without third-party libraries.
 */

enum class ScanType {
    Sequential,
    Index,
    IndexOnly
};

std::string toString(ScanType type) {
    switch (type) {
        case ScanType::Sequential:
            return "SEQUENTIAL_SCAN";
        case ScanType::Index:
            return "INDEX_SCAN";
        case ScanType::IndexOnly:
            return "INDEX_ONLY_SCAN";
    }
    return "UNKNOWN";
}

struct Order {
    int id;
    int customerId;
    std::string status;
    std::string region;
    double amount;
    std::string createdAt;
};

struct Query {
    std::map<std::string, std::string> equalityFilters;
    std::vector<std::string> selectedColumns;
};

struct QueryPlan {
    ScanType type;
    std::string indexName;
    std::size_t estimatedRows;
    double estimatedCost;
    std::string reason;
};

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};

class Index {
public:
    struct Entry {
        std::vector<std::string> key;
        int rowId;
    };

private:
    std::string name_;
    std::vector<std::string> columns_;
    std::vector<std::string> includedColumns_;
    std::optional<std::pair<std::string, std::string>> predicate_;
    std::vector<Entry> entries_;

public:
    Index(
        std::string name,
        std::vector<std::string> columns,
        std::vector<std::string> includedColumns = {},
        std::optional<std::pair<std::string, std::string>> predicate = std::nullopt
    )
        : name_(std::move(name)),
          columns_(std::move(columns)),
          includedColumns_(std::move(includedColumns)),
          predicate_(std::move(predicate)) {

        if (name_.empty() || columns_.empty()) {
            throw ValidationError("Index requires a name and at least one key column");
        }
    }

    const std::string& name() const {
        return name_;
    }

    const std::vector<std::string>& columns() const {
        return columns_;
    }

    bool applicable(const Order& order) const {
        if (!predicate_) {
            return true;
        }

        const auto& [column, expected] = *predicate_;

        if (column == "status") {
            return order.status == expected;
        }

        if (column == "region") {
            return order.region == expected;
        }

        if (column == "customerId") {
            return std::to_string(order.customerId) == expected;
        }

        return false;
    }

    bool matchesEqualityPrefix(
        const std::map<std::string, std::string>& filters
    ) const {
        bool matched = false;

        for (const auto& column : columns_) {
            if (filters.find(column) != filters.end()) {
                matched = true;
            } else {
                break;
            }
        }

        return matched;
    }

    bool covers(const std::vector<std::string>& selected) const {
        std::vector<std::string> available = columns_;
        available.insert(
            available.end(),
            includedColumns_.begin(),
            includedColumns_.end()
        );

        for (const auto& requested : selected) {
            if (std::find(
                    available.begin(),
                    available.end(),
                    requested
                ) == available.end()) {
                return false;
            }
        }

        return true;
    }

    std::vector<std::string> keyFor(const Order& order) const {
        std::vector<std::string> key;

        for (const auto& column : columns_) {
            if (column == "customerId") {
                key.push_back(std::to_string(order.customerId));
            } else if (column == "status") {
                key.push_back(order.status);
            } else if (column == "region") {
                key.push_back(order.region);
            } else if (column == "createdAt") {
                key.push_back(order.createdAt);
            } else if (column == "amount") {
                key.push_back(std::to_string(order.amount));
            } else {
                throw ValidationError("Unknown indexed column: " + column);
            }
        }

        return key;
    }

    void add(const Order& order) {
        entries_.push_back({keyFor(order), order.id});
    }

    void finalize() {
        std::sort(
            entries_.begin(),
            entries_.end(),
            [](const Entry& a, const Entry& b) {
                if (a.key == b.key) {
                    return a.rowId < b.rowId;
                }
                return a.key < b.key;
            }
        );
    }

    const std::vector<Entry>& entries() const {
        return entries_;
    }
};

class OrderTable {
private:
    std::unordered_map<int, Order> rows_;
    std::map<std::string, Index> indexes_;
    std::size_t insertCount_ = 0;

    const Order& getRow(int id) const {
        auto it = rows_.find(id);

        if (it == rows_.end()) {
            throw std::logic_error("Index points to a missing row");
        }

        return it->second;
    }

    static bool matches(
        const Order& order,
        const std::map<std::string, std::string>& filters
    ) {
        for (const auto& [column, expected] : filters) {
            if (column == "customerId" &&
                std::to_string(order.customerId) != expected) {
                return false;
            }

            if (column == "status" && order.status != expected) {
                return false;
            }

            if (column == "region" && order.region != expected) {
                return false;
            }

            if (column == "createdAt" && order.createdAt != expected) {
                return false;
            }
        }

        return true;
    }

    static std::string valueFor(
        const Order& order,
        const std::string& column
    ) {
        if (column == "id") {
            return std::to_string(order.id);
        }
        if (column == "customerId") {
            return std::to_string(order.customerId);
        }
        if (column == "status") {
            return order.status;
        }
        if (column == "region") {
            return order.region;
        }
        if (column == "amount") {
            return std::to_string(order.amount);
        }
        if (column == "createdAt") {
            return order.createdAt;
        }

        throw ValidationError("Unknown selected column: " + column);
    }

public:
    void insert(const Order& order) {
        if (order.id <= 0) {
            throw ValidationError("Order ID must be positive");
        }

        if (rows_.contains(order.id)) {
            throw ValidationError("Duplicate order ID");
        }

        if (order.customerId <= 0) {
            throw ValidationError("Customer ID must be positive");
        }

        const std::vector<std::string> validStatuses{
            "pending", "paid", "shipped", "cancelled"
        };

        if (std::find(
                validStatuses.begin(),
                validStatuses.end(),
                order.status
            ) == validStatuses.end()) {
            throw ValidationError("Invalid order status");
        }

        if (order.amount < 0) {
            throw ValidationError("Amount cannot be negative");
        }

        rows_.emplace(order.id, order);
        ++insertCount_;

        for (auto& [name, index] : indexes_) {
            if (index.applicable(order)) {
                index.add(order);
            }
        }
    }

    void createIndex(
        const std::string& name,
        const std::vector<std::string>& columns,
        const std::vector<std::string>& included = {},
        std::optional<std::pair<std::string, std::string>> predicate = std::nullopt
    ) {
        if (indexes_.contains(name)) {
            throw ValidationError("Index already exists: " + name);
        }

        Index index(name, columns, included, predicate);

        for (const auto& [id, row] : rows_) {
            if (index.applicable(row)) {
                index.add(row);
            }
        }

        index.finalize();
        indexes_.emplace(name, std::move(index));
    }

    double selectivity(
        const std::map<std::string, std::string>& filters
    ) const {
        if (filters.empty()) {
            return 1.0;
        }

        double result = 1.0;

        for (const auto& [column, expected] : filters) {
            std::size_t matching = 0;

            for (const auto& [id, row] : rows_) {
                if (matches(row, {{column, expected}})) {
                    ++matching;
                }
            }

            if (rows_.empty()) {
                return 0.0;
            }

            result *= static_cast<double>(matching) /
                      static_cast<double>(rows_.size());
        }

        return std::min(1.0, result);
    }

    QueryPlan explain(const Query& query) const {
        const double sequentialCost =
            static_cast<double>(rows_.size());

        std::optional<QueryPlan> best;

        for (const auto& [name, index] : indexes_) {
            if (!index.matchesEqualityPrefix(query.equalityFilters)) {
                continue;
            }

            const double estimated =
                std::max(
                    1.0,
                    std::floor(
                        static_cast<double>(rows_.size()) *
                        selectivity(query.equalityFilters)
                    )
                );

            double cost = 3.0 + estimated * 0.8;

            ScanType type = ScanType::Index;
            std::string reason =
                name + " provides an equality-prefix lookup";

            if (index.covers(query.selectedColumns)) {
                type = ScanType::IndexOnly;
                cost *= 0.75;
                reason += " and covers the requested columns";
            }

            QueryPlan candidate{
                type,
                name,
                static_cast<std::size_t>(estimated),
                cost,
                reason
            };

            if (!best || candidate.estimatedCost < best->estimatedCost) {
                best = candidate;
            }
        }

        if (!best || best->estimatedCost >= sequentialCost) {
            return {
                ScanType::Sequential,
                "",
                rows_.size(),
                sequentialCost,
                "No index has a lower estimated cost"
            };
        }

        return *best;
    }

    std::vector<std::map<std::string, std::string>>
    execute(const Query& query) const {
        QueryPlan plan = explain(query);

        std::vector<const Order*> candidates;

        if (plan.type == ScanType::Sequential) {
            for (const auto& [id, row] : rows_) {
                candidates.push_back(&row);
            }
        } else {
            const auto& index = indexes_.at(plan.indexName);

            for (const auto& entry : index.entries()) {
                candidates.push_back(&getRow(entry.rowId));
            }
        }

        std::vector<std::map<std::string, std::string>> results;

        for (const Order* order : candidates) {
            if (!matches(*order, query.equalityFilters)) {
                continue;
            }

            std::map<std::string, std::string> result;

            for (const auto& column : query.selectedColumns) {
                result[column] = valueFor(*order, column);
            }

            results.push_back(std::move(result));
        }

        return results;
    }

    void printPlan(const Query& query) const {
        const auto plan = explain(query);

        std::cout << "Plan: " << toString(plan.type) << '\n'
                  << "Index: "
                  << (plan.indexName.empty() ? "(none)" : plan.indexName)
                  << '\n'
                  << "Estimated rows: " << plan.estimatedRows << '\n'
                  << "Estimated cost: "
                  << std::fixed << std::setprecision(2)
                  << plan.estimatedCost << '\n'
                  << "Reason: " << plan.reason << "\n\n";
    }

    std::size_t rowCount() const {
        return rows_.size();
    }

    std::size_t insertCount() const {
        return insertCount_;
    }
};

OrderTable seed() {
    OrderTable table;

    const std::vector<std::string> statuses{
        "pending", "paid", "shipped", "cancelled"
    };

    const std::vector<std::string> regions{
        "north", "south", "east", "west"
    };

    for (int id = 1; id <= 1000; ++id) {
        table.insert({
            id,
            (id * 17) % 100 + 1,
            statuses[id % statuses.size()],
            regions[id % regions.size()],
            100.0 + ((id * 37) % 4900),
            "2026-10-" + std::to_string((id % 28) + 1)
        });
    }

    return table;
}

int main() {
    try {
        OrderTable table = seed();

        table.createIndex(
            "idx_customer",
            {"customerId"}
        );

        table.createIndex(
            "idx_status_region",
            {"status", "region"},
            {"amount", "createdAt"}
        );

        table.createIndex(
            "idx_paid_customer",
            {"customerId"},
            {"amount"},
            std::make_pair("status", "paid")
        );

        Query customerQuery{
            {{"customerId", "42"}},
            {"id", "customerId", "amount"}
        };

        Query compositeQuery{
            {{"status", "paid"}, {"region", "north"}},
            {"id", "amount", "createdAt"}
        };

        Query nonLeadingQuery{
            {{"region", "north"}},
            {"id", "customerId"}
        };

        std::cout << "CUSTOMER QUERY\n";
        table.printPlan(customerQuery);
        std::cout
            << "Rows returned: "
            << table.execute(customerQuery).size()
            << "\n\n";

        std::cout << "COMPOSITE QUERY\n";
        table.printPlan(compositeQuery);
        std::cout
            << "Rows returned: "
            << table.execute(compositeQuery).size()
            << "\n\n";

        std::cout << "NON-LEADING COLUMN QUERY\n";
        table.printPlan(nonLeadingQuery);
        std::cout
            << "Rows returned: "
            << table.execute(nonLeadingQuery).size()
            << "\n\n";

        table.insert({
            5001,
            42,
            "paid",
            "north",
            725.50,
            "2026-10-25"
        });

        std::cout << "Rows after insert: "
                  << table.rowCount() << '\n'
                  << "Base inserts: "
                  << table.insertCount() << "\n\n";

        try {
            table.insert({
                5002,
                43,
                "invalid",
                "north",
                100.0,
                "2026-10-25"
            });
        } catch (const ValidationError& ex) {
            std::cerr << "Rejected write: "
                      << ex.what() << '\n';
        }

    } catch (const std::exception& ex) {
        std::cerr << "Fatal error: " << ex.what() << '\n';
        return 1;
    }

    return 0;
}
