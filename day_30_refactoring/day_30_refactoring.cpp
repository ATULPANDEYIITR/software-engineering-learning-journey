#include <algorithm>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Refactoring Techniques and Code Improvement
 *
 * Case study:
 * A fulfillment service originally calculates shipping, pricing, customer
 * eligibility, and order persistence inside one large procedural function.
 *
 * The refactored design separates:
 *   - domain values
 *   - pricing policy
 *   - shipping strategies
 *   - order validation
 *   - persistence
 *   - service orchestration
 *
 * The program intentionally demonstrates refactoring decisions rather than
 * merely presenting isolated C++ syntax.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic refactoring_case_study.cpp -o refactoring_case_study
 */

namespace domain {

class Money {
private:
    double amount_;
    std::string currency_;

public:
    Money(double amount, std::string currency = "INR")
        : amount_(amount), currency_(std::move(currency)) {
        if (!std::isfinite(amount_) || amount_ < 0.0) {
            throw std::invalid_argument(
                "money amount must be non-negative"
            );
        }

        if (currency_.size() != 3) {
            throw std::invalid_argument(
                "currency must use a three-character code"
            );
        }
    }

    double amount() const {
        return amount_;
    }

    const std::string& currency() const {
        return currency_;
    }

    Money add(const Money& other) const {
        if (currency_ != other.currency_) {
            throw std::invalid_argument(
                "cannot add different currencies"
            );
        }

        return Money(amount_ + other.amount_, currency_);
    }
};

struct ProductLine {
    std::string product_id;
    std::string description;
    Money unit_price;
    int quantity;

    double subtotal() const {
        if (quantity <= 0) {
            throw std::invalid_argument(
                "quantity must be positive"
            );
        }

        return unit_price.amount() *
               static_cast<double>(quantity);
    }
};

struct Customer {
    std::string id;
    std::string name;
    std::string email;
};

struct Order {
    std::string id;
    Customer customer;
    std::vector<ProductLine> items;
    std::string shipping_method;
    double weight_kg;
    double distance_km;
};

struct OrderTotals {
    Money subtotal;
    Money tax;
    Money shipping;
    Money total;
};

} // namespace domain


// ---------------------------------------------------------------------------
// Refactored pricing policy
// ---------------------------------------------------------------------------

class PricingPolicy {
public:
    static constexpr double tax_rate = 0.18;
    static constexpr double free_shipping_threshold = 1000.0;

    domain::OrderTotals calculate(
        const std::vector<domain::ProductLine>& items
    ) const {
        if (items.empty()) {
            throw std::invalid_argument(
                "order must contain at least one product"
            );
        }

        std::unordered_map<std::string, bool> seen_products;

        double subtotal = 0.0;

        for (const auto& item : items) {
            if (item.product_id.empty()) {
                throw std::invalid_argument(
                    "product ID cannot be empty"
                );
            }

            if (seen_products.contains(item.product_id)) {
                throw std::invalid_argument(
                    "duplicate product: " + item.product_id
                );
            }

            seen_products[item.product_id] = true;
            subtotal += item.subtotal();
        }

        const double tax = subtotal * tax_rate;

        const double shipping =
            subtotal >= free_shipping_threshold
                ? 0.0
                : 80.0;

        const double total =
            subtotal + tax + shipping;

        return {
            domain::Money(subtotal),
            domain::Money(tax),
            domain::Money(shipping),
            domain::Money(total)
        };
    }
};


// ---------------------------------------------------------------------------
// Replace Conditional with Polymorphism
// ---------------------------------------------------------------------------

class ShippingStrategy {
public:
    virtual ~ShippingStrategy() = default;

    virtual double calculate(
        double weight_kg,
        double distance_km
    ) const = 0;
};

class StandardShipping final : public ShippingStrategy {
public:
    double calculate(
        double weight_kg,
        double distance_km
    ) const override {
        return 50.0
             + weight_kg * 12.0
             + distance_km * 0.20;
    }
};

class ExpressShipping final : public ShippingStrategy {
public:
    double calculate(
        double weight_kg,
        double distance_km
    ) const override {
        return 120.0
             + weight_kg * 18.0
             + distance_km * 0.35;
    }
};

class PickupShipping final : public ShippingStrategy {
public:
    double calculate(
        double,
        double
    ) const override {
        return 0.0;
    }
};


// ---------------------------------------------------------------------------
// Strategy factory
// ---------------------------------------------------------------------------

class ShippingStrategyFactory {
public:
    static std::unique_ptr<ShippingStrategy> create(
        const std::string& method
    ) {
        if (method == "standard") {
            return std::make_unique<StandardShipping>();
        }

        if (method == "express") {
            return std::make_unique<ExpressShipping>();
        }

        if (method == "pickup") {
            return std::make_unique<PickupShipping>();
        }

        throw std::invalid_argument(
            "unsupported shipping method: " + method
        );
    }
};


// ---------------------------------------------------------------------------
// Repository abstraction
// ---------------------------------------------------------------------------

class OrderRepository {
public:
    virtual ~OrderRepository() = default;

    virtual void save(const domain::Order& order) = 0;

    virtual std::optional<domain::Order> find(
        const std::string& order_id
    ) const = 0;
};

class InMemoryOrderRepository final : public OrderRepository {
private:
    std::map<std::string, domain::Order> orders_;

public:
    void save(const domain::Order& order) override {
        if (orders_.contains(order.id)) {
            throw std::runtime_error(
                "order already exists: " + order.id
            );
        }

        orders_.emplace(order.id, order);
    }

    std::optional<domain::Order> find(
        const std::string& order_id
    ) const override {
        auto iterator = orders_.find(order_id);

        if (iterator == orders_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }
};


// ---------------------------------------------------------------------------
// Notification abstraction
// ---------------------------------------------------------------------------

class NotificationGateway {
public:
    virtual ~NotificationGateway() = default;

    virtual void send(
        const domain::Customer& customer,
        const domain::OrderTotals& totals
    ) = 0;
};

class ConsoleNotificationGateway final
    : public NotificationGateway {
public:
    void send(
        const domain::Customer& customer,
        const domain::OrderTotals& totals
    ) override {
        std::cout
            << "Notification to "
            << customer.email
            << ": order total = "
            << std::fixed
            << std::setprecision(2)
            << totals.total.amount()
            << ' '
            << totals.total.currency()
            << '\n';
    }
};


// ---------------------------------------------------------------------------
// Order service
// ---------------------------------------------------------------------------

class OrderService {
private:
    OrderRepository& repository_;
    NotificationGateway& notification_gateway_;
    PricingPolicy pricing_policy_;

    static void validate_order(
        const domain::Order& order
    ) {
        if (order.id.empty()) {
            throw std::invalid_argument(
                "order ID cannot be empty"
            );
        }

        if (order.customer.id.empty()) {
            throw std::invalid_argument(
                "customer ID cannot be empty"
            );
        }

        if (order.customer.email.empty()) {
            throw std::invalid_argument(
                "customer email cannot be empty"
            );
        }

        if (!std::isfinite(order.weight_kg) ||
            order.weight_kg < 0.0) {
            throw std::invalid_argument(
                "weight must be non-negative"
            );
        }

        if (!std::isfinite(order.distance_km) ||
            order.distance_km < 0.0) {
            throw std::invalid_argument(
                "distance must be non-negative"
            );
        }
    }

public:
    OrderService(
        OrderRepository& repository,
        NotificationGateway& notification_gateway
    )
        : repository_(repository),
          notification_gateway_(notification_gateway) {}

    domain::OrderTotals place_order(
        const domain::Order& order
    ) {
        validate_order(order);

        const auto totals =
            pricing_policy_.calculate(order.items);

        auto shipping =
            ShippingStrategyFactory::create(
                order.shipping_method
            );

        const double freight =
            shipping->calculate(
                order.weight_kg,
                order.distance_km
            );

        domain::OrderTotals final_totals{
            totals.subtotal,
            totals.tax,
            domain::Money(freight),
            domain::Money(
                totals.subtotal.amount()
                + totals.tax.amount()
                + freight
            )
        };

        repository_.save(order);
        notification_gateway_.send(
            order.customer,
            final_totals
        );

        return final_totals;
    }
};


// ---------------------------------------------------------------------------
// Refactoring safety checks
// ---------------------------------------------------------------------------

double legacy_shipping(
    const std::string& method,
    double weight_kg,
    double distance_km
) {
    if (method == "standard") {
        if (weight_kg > 10.0) {
            return 100.0 + distance_km * 0.5;
        }

        return 50.0 + distance_km * 0.2;
    }

    if (method == "express") {
        if (weight_kg > 10.0) {
            return 180.0 + distance_km * 0.8;
        }

        return 120.0 + distance_km * 0.35;
    }

    if (method == "pickup") {
        return 0.0;
    }

    throw std::invalid_argument(
        "unsupported legacy shipping method"
    );
}

double refactored_shipping(
    const std::string& method,
    double weight_kg,
    double distance_km
) {
    auto strategy =
        ShippingStrategyFactory::create(method);

    return strategy->calculate(
        weight_kg,
        distance_km
    );
}

void require_close(
    double actual,
    double expected,
    const std::string& message
) {
    if (std::abs(actual - expected) > 0.000001) {
        throw std::runtime_error(
            message
            + " expected="
            + std::to_string(expected)
            + " actual="
            + std::to_string(actual)
        );
    }
}

void run_characterization_tests() {
    const std::vector<std::string> methods{
        "standard",
        "express",
        "pickup"
    };

    const std::vector<double> weights{
        1.0,
        5.0,
        10.0
    };

    const std::vector<double> distances{
        0.0,
        50.0,
        250.0
    };

    for (const auto& method : methods) {
        for (double weight : weights) {
            for (double distance : distances) {
                require_close(
                    refactored_shipping(
                        method,
                        weight,
                        distance
                    ),
                    legacy_shipping(
                        method,
                        weight,
                        distance
                    ),
                    "Refactoring changed shipping behavior"
                );
            }
        }
    }

    PricingPolicy policy;

    const std::vector<domain::ProductLine> items{
        {
            "LAPTOP",
            "Business Laptop",
            domain::Money(75000.0),
            1
        },
        {
            "MOUSE",
            "Wireless Mouse",
            domain::Money(1800.0),
            2
        }
    };

    const auto totals = policy.calculate(items);

    require_close(
        totals.subtotal.amount(),
        78600.0,
        "Subtotal calculation failed"
    );

    require_close(
        totals.tax.amount(),
        14148.0,
        "Tax calculation failed"
    );

    require_close(
        totals.shipping.amount(),
        0.0,
        "Free shipping threshold failed"
    );

    require_close(
        totals.total.amount(),
        92748.0,
        "Total calculation failed"
    );

    bool duplicate_rejected = false;

    try {
        const std::vector<domain::ProductLine> duplicates{
            {
                "P1",
                "Product",
                domain::Money(100.0),
                1
            },
            {
                "P1",
                "Product Again",
                domain::Money(200.0),
                1
            }
        };

        policy.calculate(duplicates);
    } catch (const std::invalid_argument&) {
        duplicate_rejected = true;
    }

    if (!duplicate_rejected) {
        throw std::runtime_error(
            "Duplicate products were not rejected"
        );
    }
}


// ---------------------------------------------------------------------------
// Demonstration
// ---------------------------------------------------------------------------

int main() {
    try {
        std::cout
            << "REFACTORING AND CODE IMPROVEMENT\n"
            << "================================\n\n";

        run_characterization_tests();

        std::cout
            << "Characterization tests passed.\n\n";

        InMemoryOrderRepository repository;
        ConsoleNotificationGateway notification_gateway;

        OrderService service(
            repository,
            notification_gateway
        );

        domain::Customer customer{
            "CUS-CPP-100",
            "Anita Sharma",
            "anita@example.com"
        };

        domain::Order order{
            "ORD-CPP-100",
            customer,
            {
                {
                    "CAMERA",
                    "Conference Camera",
                    domain::Money(8500.0),
                    1
                },
                {
                    "MIC",
                    "USB Microphone",
                    domain::Money(3200.0),
                    2
                }
            },
            "express",
            3.5,
            75.0
        };

        const auto totals =
            service.place_order(order);

        std::cout
            << "\nRefactored order result\n"
            << "-----------------------\n"
            << std::fixed
            << std::setprecision(2)
            << "Subtotal: "
            << totals.subtotal.amount()
            << ' '
            << totals.subtotal.currency()
            << '\n'
            << "Tax: "
            << totals.tax.amount()
            << ' '
            << totals.tax.currency()
            << '\n'
            << "Shipping: "
            << totals.shipping.amount()
            << ' '
            << totals.shipping.currency()
            << '\n'
            << "Total: "
            << totals.total.amount()
            << ' '
            << totals.total.currency()
            << '\n';

        const auto stored =
            repository.find(order.id);

        std::cout
            << "\nRepository lookup: "
            << (stored.has_value()
                ? "order found"
                : "order missing")
            << '\n';

        std::cout
            << "\nDesign characteristics demonstrated:\n"
            << "Pure pricing rules are isolated from persistence.\n"
            << "Shipping behavior is selected through polymorphic strategies.\n"
            << "Infrastructure dependencies are injected into the service.\n"
            << "Domain values validate their own invariants.\n"
            << "Characterization tests protect behavior during restructuring.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Application error: "
            << error.what()
            << '\n';

        return 1;
    }
}
