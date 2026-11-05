#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

// ============================================================
// 1. Domain types
// ============================================================

enum class OrderStatus {
    Pending,
    Confirmed,
    Rejected
};

enum class StepType {
    Given,
    When,
    Then,
    And
};

struct Product {
    string id;
    string name;
    double price;
    int stock;
};

struct Order {
    string id;
    string productId;
    int quantity;
    double total;
    OrderStatus status;
};

struct TestContext {
    map<string, Product> products;
    vector<Order> orders;
    vector<string> errors;
    bool authenticated = true;
    bool paymentApproved = true;
};

// ============================================================
// 2. Business service
// ============================================================

class OrderService {
private:
    double taxRate;

public:
    explicit OrderService(double tax = 0.10)
        : taxRate(tax) {

        if (!isfinite(taxRate) || taxRate < 0 || taxRate > 1) {
            throw invalid_argument("Invalid tax rate");
        }
    }

    double calculateTotal(
        const Product& product,
        int quantity
    ) const {

        if (quantity <= 0) {
            throw invalid_argument("Quantity must be positive");
        }

        double subtotal = product.price * quantity;

        return round(
            subtotal * (1.0 + taxRate) * 100.0
        ) / 100.0;
    }

    Order placeOrder(
        TestContext& context,
        const string& productId,
        int quantity
    ) const {

        if (!context.authenticated) {
            throw runtime_error("Authentication required");
        }

        if (!context.paymentApproved) {
            throw runtime_error("Payment authorization failed");
        }

        auto iterator = context.products.find(productId);

        if (iterator == context.products.end()) {
            throw runtime_error("Product not found");
        }

        if (quantity <= 0) {
            throw invalid_argument("Invalid quantity");
        }

        Product& product = iterator->second;

        if (product.stock < quantity) {
            throw runtime_error("Insufficient inventory");
        }

        double total = calculateTotal(product, quantity);

        // Validate before changing inventory.
        product.stock -= quantity;

        Order order{
            "ORD-" + to_string(context.orders.size() + 1),
            productId,
            quantity,
            total,
            OrderStatus::Confirmed
        };

        context.orders.push_back(order);

        return order;
    }
};

// ============================================================
// 3. BDD step representation
// ============================================================

using StepFunction = function<void(TestContext&)>;

struct BDDStep {
    StepType type;
    string description;
    StepFunction action;
};

struct Scenario {
    string name;
    string description;
    vector<BDDStep> steps;

    Scenario& addStep(
        StepType type,
        const string& description,
        StepFunction action
    ) {
        if (!action) {
            throw invalid_argument("Step action cannot be empty");
        }

        steps.push_back({type, description, move(action)});

        return *this;
    }
};

struct Feature {
    string name;
    string description;
    vector<Scenario> scenarios;

    void addScenario(Scenario scenario) {
        scenarios.push_back(move(scenario));
    }
};

// ============================================================
// 4. Scenario execution and reporting
// ============================================================

struct ScenarioResult {
    string name;
    bool passed;
    double durationMs;
    string error;
};

class BDDRunner {
public:
    ScenarioResult run(const Scenario& scenario) const {

        TestContext context;

        auto start = chrono::steady_clock::now();

        try {
            for (const auto& step : scenario.steps) {
                step.action(context);
            }

            auto end = chrono::steady_clock::now();

            double duration = chrono::duration<double, milli>(
                end - start
            ).count();

            return {
                scenario.name,
                true,
                duration,
                ""
            };

        } catch (const exception& error) {

            auto end = chrono::steady_clock::now();

            double duration = chrono::duration<double, milli>(
                end - start
            ).count();

            return {
                scenario.name,
                false,
                duration,
                error.what()
            };
        }
    }

    vector<ScenarioResult> runFeature(
        const Feature& feature
    ) const {

        cout << "\nFeature: " << feature.name << "\n";
        cout << feature.description << "\n\n";

        vector<ScenarioResult> results;

        for (const auto& scenario : feature.scenarios) {
            auto result = run(scenario);

            cout << "["
                 << (result.passed ? "PASSED" : "FAILED")
                 << "] "
                 << result.name
                 << " ("
                 << fixed << setprecision(3)
                 << result.durationMs
                 << " ms)\n";

            if (!result.error.empty()) {
                cout << "  Error: " << result.error << "\n";
            }

            results.push_back(result);
        }

        return results;
    }
};

// ============================================================
// 5. Domain-specific step factories
// ============================================================

OrderService orderService;

BDDStep givenProduct(
    const string& id,
    double price,
    int stock
) {
    return {
        StepType::Given,
        "A product exists with available stock",
        [=](TestContext& context) {

            if (id.empty() || price <= 0 || stock < 0) {
                throw invalid_argument("Invalid product configuration");
            }

            if (context.products.count(id)) {
                throw runtime_error("Duplicate product");
            }

            context.products.emplace(
                id,
                Product{id, "Wireless Keyboard", price, stock}
            );
        }
    };
}

BDDStep givenAuthentication(bool authenticated) {
    return {
        StepType::Given,
        "Customer authentication state",
        [=](TestContext& context) {
            context.authenticated = authenticated;
        }
    };
}

BDDStep givenPayment(bool approved) {
    return {
        StepType::Given,
        "Payment authorization state",
        [=](TestContext& context) {
            context.paymentApproved = approved;
        }
    };
}

BDDStep whenPlaceOrder(
    const string& productId,
    int quantity
) {
    return {
        StepType::When,
        "Customer submits an order",
        [=](TestContext& context) {

            try {
                orderService.placeOrder(
                    context,
                    productId,
                    quantity
                );
            } catch (const exception& error) {
                context.errors.push_back(error.what());
            }
        }
    };
}

BDDStep thenOrderConfirmed() {
    return {
        StepType::Then,
        "Order must be confirmed",
        [](TestContext& context) {

            if (context.orders.empty()) {
                throw runtime_error("No confirmed order exists");
            }

            if (context.orders.back().status != OrderStatus::Confirmed) {
                throw runtime_error("Order is not confirmed");
            }
        }
    };
}

BDDStep thenOrderRejected() {
    return {
        StepType::Then,
        "Order must be rejected",
        [](TestContext& context) {

            if (!context.orders.empty()) {
                throw runtime_error("Unexpected order creation");
            }

            if (context.errors.empty()) {
                throw runtime_error("Expected rejection was not recorded");
            }
        }
    };
}

BDDStep thenStockEquals(
    const string& productId,
    int expected
) {
    return {
        StepType::Then,
        "Inventory must match expected quantity",
        [=](TestContext& context) {

            auto iterator = context.products.find(productId);

            if (iterator == context.products.end()) {
                throw runtime_error("Product not found in test context");
            }

            if (iterator->second.stock != expected) {
                throw runtime_error("Inventory assertion failed");
            }
        }
    };
}

BDDStep thenTotalEquals(double expected) {
    return {
        StepType::Then,
        "Order total must match expected amount",
        [=](TestContext& context) {

            if (context.orders.empty()) {
                throw runtime_error("Order does not exist");
            }

            if (abs(context.orders.back().total - expected) > 0.001) {
                throw runtime_error("Order total assertion failed");
            }
        }
    };
}

// ============================================================
// 6. Feature construction
// ============================================================

Feature buildFeature() {

    Feature feature{
        "Online order acceptance",
        "Validate customer, inventory, and payment behavior.",
        {}
    };

    Scenario success{
        "Successful order placement",
        "A valid customer purchases available inventory.",
        {}
    };

    success
        .addStep(
            StepType::Given,
            "Product is available",
            givenProduct("KB-101", 1000.00, 10).action
        )
        .addStep(
            StepType::And,
            "Customer is authenticated",
            givenAuthentication(true).action
        )
        .addStep(
            StepType::When,
            "Customer orders two units",
            whenPlaceOrder("KB-101", 2).action
        )
        .addStep(
            StepType::Then,
            "Order is confirmed",
            thenOrderConfirmed().action
        )
        .addStep(
            StepType::And,
            "Stock becomes eight",
            thenStockEquals("KB-101", 8).action
        )
        .addStep(
            StepType::And,
            "Total includes tax",
            thenTotalEquals(2200.00).action
        );

    feature.addScenario(move(success));

    Scenario insufficient{
        "Insufficient inventory",
        "The requested quantity exceeds available stock.",
        {}
    };

    insufficient
        .addStep(
            StepType::Given,
            "Only two units exist",
            givenProduct("KB-101", 1000.00, 2).action
        )
        .addStep(
            StepType::When,
            "Customer requests five units",
            whenPlaceOrder("KB-101", 5).action
        )
        .addStep(
            StepType::Then,
            "Order is rejected",
            thenOrderRejected().action
        )
        .addStep(
            StepType::And,
            "Stock remains unchanged",
            thenStockEquals("KB-101", 2).action
        );

    feature.addScenario(move(insufficient));

    Scenario unauthenticated{
        "Unauthenticated purchase",
        "A customer without authentication cannot order.",
        {}
    };

    unauthenticated
        .addStep(
            StepType::Given,
            "Product exists",
            givenProduct("KB-101", 1000.00, 10).action
        )
        .addStep(
            StepType::Given,
            "Customer is unauthenticated",
            givenAuthentication(false).action
        )
        .addStep(
            StepType::When,
            "Customer submits an order",
            whenPlaceOrder("KB-101", 1).action
        )
        .addStep(
            StepType::Then,
            "Order is rejected",
            thenOrderRejected().action
        )
        .addStep(
            StepType::And,
            "Stock remains unchanged",
            thenStockEquals("KB-101", 10).action
        );

    feature.addScenario(move(unauthenticated));

    Scenario paymentFailure{
        "Payment authorization failure",
        "Failed payment must not reserve inventory.",
        {}
    };

    paymentFailure
        .addStep(
            StepType::Given,
            "Product exists",
            givenProduct("KB-101", 1000.00, 10).action
        )
        .addStep(
            StepType::Given,
            "Payment is rejected",
            givenPayment(false).action
        )
        .addStep(
            StepType::When,
            "Customer submits an order",
            whenPlaceOrder("KB-101", 1).action
        )
        .addStep(
            StepType::Then,
            "Order is rejected",
            thenOrderRejected().action
        )
        .addStep(
            StepType::And,
            "Stock remains unchanged",
            thenStockEquals("KB-101", 10).action
        );

    feature.addScenario(move(paymentFailure));

    return feature;
}

// ============================================================
// 7. Data-driven acceptance tests
// ============================================================

void runScenarioOutline() {

    cout << "\nScenario Outline: Order quantity examples\n";

    struct Example {
        int quantity;
        int stock;
        double expected;
    };

    vector<Example> examples = {
        {1, 5, 1100.00},
        {2, 5, 2200.00},
        {3, 5, 3300.00}
    };

    for (const auto& example : examples) {

        TestContext context;

        context.products.emplace(
            "KB-101",
            Product{"KB-101", "Wireless Keyboard", 1000.00, example.stock}
        );

        Order order = orderService.placeOrder(
            context,
            "KB-101",
            example.quantity
        );

        if (abs(order.total - example.expected) > 0.001) {
            throw runtime_error("Scenario outline assertion failed");
        }

        cout << "[PASSED] Quantity: "
             << example.quantity
             << ", Total: "
             << fixed << setprecision(2)
             << order.total << "\n";
    }
}

// ============================================================
// 8. Application entry point
// ============================================================

int main() {

    try {

        Feature feature = buildFeature();

        BDDRunner runner;

        vector<ScenarioResult> results =
            runner.runFeature(feature);

        runScenarioOutline();

        int passed = count_if(
            results.begin(),
            results.end(),
            [](const ScenarioResult& result) {
                return result.passed;
            }
        );

        int failed = static_cast<int>(results.size()) - passed;

        cout << "\nAcceptance Test Report\n";
        cout << "Total: " << results.size() << "\n";
        cout << "Passed: " << passed << "\n";
        cout << "Failed: " << failed << "\n";

        return failed == 0 ? 0 : 1;

    } catch (const exception& error) {

        cerr << "Execution error: " << error.what() << "\n";
        return 1;
    }
}
