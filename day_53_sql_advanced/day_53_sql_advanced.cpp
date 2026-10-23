#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

struct Sale {
    int id;
    int customerId;
    std::string customer;
    std::string region;
    std::string product;
    std::string category;
    double amount;
    std::string month;
};

struct Customer {
    int id;
    std::string name;
};

struct CustomerMetric {
    int customerId;
    double total;
};

class AnalyticsEngine {
private:
    std::vector<Sale> sales;

    static void validate(const Sale& sale) {
        if (sale.id <= 0 || sale.customerId <= 0) {
            throw std::invalid_argument("Invalid sale/customer identifier");
        }

        if (sale.amount < 0.0) {
            throw std::invalid_argument("Sale amount cannot be negative");
        }

        if (sale.month.size() != 7 ||
            sale.month[4] != '-') {
            throw std::invalid_argument("Invalid month format");
        }
    }

public:
    explicit AnalyticsEngine(std::vector<Sale> input)
        : sales(std::move(input)) {
        for (const auto& sale : sales) {
            validate(sale);
        }
    }

    // Hash-indexed join models the physical idea of building an index on
    // the smaller relation before matching keys.
    std::vector<std::pair<Sale, Customer>>
    innerJoin(const std::vector<Customer>& customers) const {
        std::unordered_map<int, Customer> index;

        for (const auto& customer : customers) {
            index.emplace(customer.id, customer);
        }

        std::vector<std::pair<Sale, Customer>> result;

        for (const auto& sale : sales) {
            auto it = index.find(sale.customerId);
            if (it != index.end()) {
                result.emplace_back(sale, it->second);
            }
        }

        return result;
    }

    std::vector<CustomerMetric> customerTotals() const {
        std::map<int, double> totals;

        for (const auto& sale : sales) {
            totals[sale.customerId] += sale.amount;
        }

        std::vector<CustomerMetric> result;
        result.reserve(totals.size());

        for (const auto& [customerId, total] : totals) {
            result.push_back({customerId, total});
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const CustomerMetric& a, const CustomerMetric& b) {
                return a.total > b.total;
            }
        );

        return result;
    }

    // Represents a subquery whose aggregate result becomes the threshold
    // for the outer query.
    std::vector<CustomerMetric> customersAboveAverage() const {
        const auto totals = customerTotals();

        if (totals.empty()) {
            return {};
        }

        const double sum = std::accumulate(
            totals.begin(),
            totals.end(),
            0.0,
            [](double current, const CustomerMetric& metric) {
                return current + metric.total;
            }
        );

        const double average = sum / totals.size();

        std::vector<CustomerMetric> result;

        for (const auto& metric : totals) {
            if (metric.total >= average) {
                result.push_back(metric);
            }
        }

        return result;
    }

    // CTE-style staged aggregation. The intermediate map represents the
    // named relational result produced before the final reporting query.
    std::map<std::string, double> monthlyTotals() const {
        std::map<std::string, double> totals;

        for (const auto& sale : sales) {
            totals[sale.month] += sale.amount;
        }

        return totals;
    }

    // Window-function style running total partitioned by customer.
    void printRunningTotals() const {
        std::map<int, std::vector<Sale>> partitions;

        for (const auto& sale : sales) {
            partitions[sale.customerId].push_back(sale);
        }

        for (auto& [customerId, rows] : partitions) {
            std::sort(
                rows.begin(),
                rows.end(),
                [](const Sale& a, const Sale& b) {
                    if (a.month != b.month) {
                        return a.month < b.month;
                    }
                    return a.id < b.id;
                }
            );

            double running = 0.0;

            for (const auto& sale : rows) {
                running += sale.amount;

                std::cout
                    << "customer=" << customerId
                    << " month=" << sale.month
                    << " sale=" << sale.id
                    << " amount=" << sale.amount
                    << " running=" << running
                    << '\n';
            }
        }
    }

    // Dense ranking is deliberately implemented separately from row-number
    // ranking so ties receive the same rank.
    void printRegionRanks() const {
        std::map<std::string, std::map<int, double>> regions;

        for (const auto& sale : sales) {
            regions[sale.region][sale.customerId] += sale.amount;
        }

        for (const auto& [region, customerTotals] : regions) {
            std::vector<CustomerMetric> ranked;

            for (const auto& [customerId, total] : customerTotals) {
                ranked.push_back({customerId, total});
            }

            std::sort(
                ranked.begin(),
                ranked.end(),
                [](const CustomerMetric& a, const CustomerMetric& b) {
                    if (a.total != b.total) {
                        return a.total > b.total;
                    }
                    return a.customerId < b.customerId;
                }
            );

            int rank = 0;
            double previous = -1.0;

            for (std::size_t i = 0; i < ranked.size(); ++i) {
                if (rank == 0 || ranked[i].total != previous) {
                    rank = static_cast<int>(i) + 1;
                    previous = ranked[i].total;
                }

                std::cout
                    << "region=" << region
                    << " customer=" << ranked[i].customerId
                    << " total=" << ranked[i].total
                    << " dense_rank=" << rank
                    << '\n';
            }
        }
    }
};

int main() {
    std::cout << std::fixed << std::setprecision(2);

    const std::vector<Sale> sales = {
        {1, 101, "Asha", "North", "Laptop", "Electronics", 1200.00, "2026-01"},
        {2, 102, "Ravi", "South", "Phone", "Electronics", 850.00, "2026-01"},
        {3, 103, "Meera", "North", "Desk", "Furniture", 450.00, "2026-01"},
        {4, 101, "Asha", "North", "Monitor", "Electronics", 400.00, "2026-02"},
        {5, 104, "Kabir", "West", "Chair", "Furniture", 300.00, "2026-02"},
        {6, 102, "Ravi", "South", "Laptop", "Electronics", 1300.00, "2026-02"},
        {7, 105, "Nisha", "West", "Phone", "Electronics", 900.00, "2026-03"},
        {8, 103, "Meera", "North", "Chair", "Furniture", 280.00, "2026-03"},
        {9, 101, "Asha", "North", "Phone", "Electronics", 820.00, "2026-03"},
        {10, 104, "Kabir", "West", "Laptop", "Electronics", 1250.00, "2026-04"}
    };

    const std::vector<Customer> customers = {
        {101, "Asha"},
        {102, "Ravi"},
        {103, "Meera"},
        {104, "Kabir"},
        {105, "Nisha"},
        {106, "Dev"}
    };

    try {
        AnalyticsEngine engine(sales);

        std::cout << "INNER JOIN\n";
        for (const auto& [sale, customer] : engine.innerJoin(customers)) {
            std::cout
                << sale.id << " "
                << customer.id << " "
                << customer.name << '\n';
        }

        std::cout << "\nCUSTOMERS ABOVE AVERAGE\n";
        for (const auto& metric : engine.customersAboveAverage()) {
            std::cout
                << metric.customerId << " "
                << metric.total << '\n';
        }

        std::cout << "\nCTE-STYLE MONTHLY TOTALS\n";
        for (const auto& [month, total] : engine.monthlyTotals()) {
            std::cout << month << " " << total << '\n';
        }

        std::cout << "\nWINDOW RUNNING TOTALS\n";
        engine.printRunningTotals();

        std::cout << "\nREGIONAL DENSE RANK\n";
        engine.printRegionRanks();
    }
    catch (const std::exception& error) {
        std::cerr << "Analytics error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
