#include <algorithm>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <tuple>
#include <utility>
#include <vector>

using namespace std;

struct FunctionalDependency {
    set<string> determinant;
    set<string> dependent;
};

struct PullLikeRelation {
    string name;
    vector<string> attributes;
    set<string> candidateKey;
    vector<FunctionalDependency> dependencies;
};

class NormalizationEngine {
public:
    static bool isSubset(const set<string>& left, const set<string>& right) {
        return includes(
            right.begin(), right.end(),
            left.begin(), left.end()
        );
    }

    static bool isProperSubset(
        const set<string>& left,
        const set<string>& right
    ) {
        return left.size() < right.size() && isSubset(left, right);
    }

    static vector<string> findPartialDependencies(
        const PullLikeRelation& relation
    ) {
        vector<string> findings;

        for (const auto& fd : relation.dependencies) {
            const bool determinantIsPartial =
                isProperSubset(fd.determinant, relation.candidateKey);

            bool determinesNonKeyAttribute = false;

            for (const auto& attribute : fd.dependent) {
                if (!relation.candidateKey.contains(attribute)) {
                    determinesNonKeyAttribute = true;
                    break;
                }
            }

            if (determinantIsPartial && determinesNonKeyAttribute) {
                findings.push_back(
                    "Partial dependency: " +
                    join(fd.determinant) +
                    " -> " +
                    join(fd.dependent)
                );
            }
        }

        return findings;
    }

    static vector<string> findTransitiveDependencies(
        const PullLikeRelation& relation
    ) {
        vector<string> findings;

        // A direct dependency from the complete key to an intermediate
        // non-key attribute followed by that attribute determining another
        // non-key attribute creates a transitive dependency.
        for (const auto& first : relation.dependencies) {
            if (first.determinant != relation.candidateKey) {
                continue;
            }

            for (const auto& middle : first.dependent) {
                for (const auto& second : relation.dependencies) {
                    if (second.determinant == set<string>{middle}) {
                        for (const auto& finalAttribute : second.dependent) {
                            if (!relation.candidateKey.contains(finalAttribute)) {
                                findings.push_back(
                                    "Transitive dependency: " +
                                    join(relation.candidateKey) +
                                    " -> " + middle +
                                    " -> " + finalAttribute
                                );
                            }
                        }
                    }
                }
            }
        }

        return findings;
    }

    static bool satisfies1NF(
        const vector<vector<string>>& rows,
        size_t expectedColumns
    ) {
        if (expectedColumns == 0) {
            return false;
        }

        for (const auto& row : rows) {
            if (row.size() != expectedColumns) {
                return false;
            }

            // This case study represents atomic values as strings. A row
            // therefore cannot contain a serialized collection such as
            // "[A,B]" in a single attribute.
            for (const auto& value : row) {
                if (value.find('[') != string::npos ||
                    value.find('{') != string::npos) {
                    return false;
                }
            }
        }

        return true;
    }

private:
    static string join(const set<string>& values) {
        string result;
        bool first = true;

        for (const auto& value : values) {
            if (!first) {
                result += ", ";
            }
            result += value;
            first = false;
        }

        return result;
    }
};

struct Customer {
    int id;
    string name;
    string city;
};

struct Order {
    int id;
    int customerId;
    double amount;
};

class ReportingStore {
public:
    void addCustomer(Customer customer) {
        if (customers.contains(customer.id)) {
            throw invalid_argument("duplicate customer identifier");
        }

        if (customer.name.empty() || customer.city.empty()) {
            throw invalid_argument("customer attributes cannot be empty");
        }

        customers.emplace(customer.id, move(customer));
    }

    void addOrder(Order order) {
        if (orders.contains(order.id)) {
            throw invalid_argument("duplicate order identifier");
        }

        if (!customers.contains(order.customerId)) {
            throw invalid_argument("order references unknown customer");
        }

        if (order.amount <= 0) {
            throw invalid_argument("order amount must be positive");
        }

        orders.emplace(order.id, move(order));
    }

    vector<string> normalizedReport() const {
        vector<string> result;

        for (const auto& [orderId, order] : orders) {
            const auto& customer = customers.at(order.customerId);

            result.push_back(
                "order=" + to_string(orderId) +
                ", customer=" + customer.name +
                ", city=" + customer.city +
                ", amount=" + to_string(order.amount)
            );
        }

        return result;
    }

    vector<string> denormalizedSnapshot() const {
        // The snapshot intentionally duplicates customer attributes for a
        // reporting workload. It is not the authoritative source of truth.
        vector<string> result;

        for (const auto& [orderId, order] : orders) {
            const auto& customer = customers.at(order.customerId);

            result.push_back(
                "order=" + to_string(orderId) +
                ", customer=" + customer.name +
                ", city=" + customer.city
            );
        }

        return result;
    }

private:
    map<int, Customer> customers;
    map<int, Order> orders;
};

int main() {
    try {
        cout << "DATABASE NORMALIZATION ENGINE\n\n";

        PullLikeRelation enrollment{
            "enrollment",
            {"student_id", "course_id", "student_name", "course_name", "grade"},
            {"student_id", "course_id"},
            {
                {{"student_id"}, {"student_name"}},
                {{"course_id"}, {"course_name"}},
                {{"student_id", "course_id"}, {"grade"}}
            }
        };

        cout << "2NF dependency analysis:\n";
        for (const auto& finding :
             NormalizationEngine::findPartialDependencies(enrollment)) {
            cout << "  " << finding << '\n';
        }

        PullLikeRelation employee{
            "employee",
            {"employee_id", "employee_name", "department_id", "department_name"},
            {"employee_id"},
            {
                {{"employee_id"}, {"department_id"}},
                {{"department_id"}, {"department_name"}}
            }
        };

        cout << "\n3NF dependency analysis:\n";
        for (const auto& finding :
             NormalizationEngine::findTransitiveDependencies(employee)) {
            cout << "  " << finding << '\n';
        }

        vector<vector<string>> atomicRows{
            {"1", "A"},
            {"2", "B"}
        };

        vector<vector<string>> nonAtomicRows{
            {"1", "[A,B]"},
            {"2", "C"}
        };

        cout << "\n1NF atomic relation: "
             << (NormalizationEngine::satisfies1NF(atomicRows, 2) ? "valid" : "invalid")
             << '\n';

        cout << "1NF non-atomic relation: "
             << (NormalizationEngine::satisfies1NF(nonAtomicRows, 2) ? "valid" : "invalid")
             << '\n';

        ReportingStore store;

        store.addCustomer({1, "Nisha", "Lucknow"});
        store.addCustomer({2, "Arjun", "Delhi"});

        store.addOrder({9001, 1, 2500.00});
        store.addOrder({9002, 2, 1800.00});

        cout << "\nNormalized reporting view:\n";
        for (const auto& row : store.normalizedReport()) {
            cout << "  " << row << '\n';
        }

        cout << "\nDenormalized reporting snapshot:\n";
        for (const auto& row : store.denormalizedSnapshot()) {
            cout << "  " << row << '\n';
        }

        try {
            store.addOrder({9003, 99, 1000.00});
        } catch (const exception& error) {
            cout << "\nExpected referential-integrity failure: "
                 << error.what() << '\n';
        }

        try {
            store.addOrder({9004, 1, -500.00});
        } catch (const exception& error) {
            cout << "Expected domain-validation failure: "
                 << error.what() << '\n';
        }

        cout << "\nDesign decisions:\n";
        cout << "  1NF removes repeating or multivalued attributes.\n";
        cout << "  2NF removes dependencies on only part of a composite key.\n";
        cout << "  3NF removes non-key dependencies through another non-key attribute.\n";
        cout << "  Denormalization is treated as an explicit reporting optimization.\n";
        cout << "  Authoritative customer data remains normalized to control update anomalies.\n";

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
