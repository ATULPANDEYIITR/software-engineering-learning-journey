#include <algorithm>
#include <cassert>
#include <cmath>
#include <exception>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

enum class OrderStatus {
    New,
    Paid,
    Cancelled
};

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};

struct Product {
    std::string id;
    std::string name;
    double price;
    int stock;
};

struct OrderItem {
    std::string productId;
    int quantity;
};

struct Order {
    std::string id;
    std::string customer;
    std::vector<OrderItem> items;
    OrderStatus status{OrderStatus::New};
};

class Inventory {
private:
    std::map<std::string, Product> products_;

public:
    explicit Inventory(std::vector<Product> products) {
        for (const auto& product : products) {
            if (product.id.empty() || product.name.empty()) {
                throw ValidationError("product identity cannot be empty");
            }
            if (product.price < 0 || product.stock < 0) {
                throw ValidationError("product price and stock must be non-negative");
            }
            products_.emplace(product.id, product);
        }
    }

    Product& get(const std::string& productId) {
        auto it = products_.find(productId);
        if (it == products_.end()) {
            throw ValidationError("unknown product: " + productId);
        }
        return it->second;
    }

    const Product& get(const std::string& productId) const {
        auto it = products_.find(productId);
        if (it == products_.end()) {
            throw ValidationError("unknown product: " + productId);
        }
        return it->second;
    }

    void reserve(const std::string& productId, int quantity) {
        if (quantity <= 0) {
            throw ValidationError("quantity must be positive");
        }

        Product& product = get(productId);
        if (product.stock < quantity) {
            throw ValidationError("insufficient stock for " + productId);
        }

        product.stock -= quantity;
    }

    void release(const std::string& productId, int quantity) {
        if (quantity <= 0) {
            throw ValidationError("quantity must be positive");
        }

        get(productId).stock += quantity;
    }

    int stock(const std::string& productId) const {
        return get(productId).stock;
    }
};

class MergeEligibilityEngine {
private:
    int requiredApprovals_;
    bool requirePassingChecks_;
    bool requireResolvedConversations_;

public:
    MergeEligibilityEngine(
        int requiredApprovals,
        bool requirePassingChecks,
        bool requireResolvedConversations
    )
        : requiredApprovals_(requiredApprovals),
          requirePassingChecks_(requirePassingChecks),
          requireResolvedConversations_(requireResolvedConversations) {
        if (requiredApprovals < 0) {
            throw ValidationError("required approvals cannot be negative");
        }
    }

    bool eligible(
        int approvals,
        bool checksPassing,
        bool conversationsResolved,
        bool hasChanges
    ) const {
        if (!hasChanges) {
            return false;
        }
        if (approvals < requiredApprovals_) {
            return false;
        }
        if (requirePassingChecks_ && !checksPassing) {
            return false;
        }
        if (requireResolvedConversations_ && !conversationsResolved) {
            return false;
        }
        return true;
    }
};

class TestRunner {
private:
    int passed_{0};
    int failed_{0};

public:
    template <typename Function>
    void run(const std::string& name, Function function) {
        try {
            function();
            ++passed_;
            std::cout << "[PASS] " << name << '\n';
        } catch (const std::exception& error) {
            ++failed_;
            std::cout << "[FAIL] " << name << ": "
                      << error.what() << '\n';
        } catch (...) {
            ++failed_;
            std::cout << "[FAIL] " << name << ": unknown error\n";
        }
    }

    int exitCode() const {
        std::cout << "\nPassed: " << passed_
                  << ", Failed: " << failed_ << '\n';
        return failed_ == 0 ? 0 : 1;
    }
};

void expectThrows(const std::function<void()>& function) {
    bool thrown = false;

    try {
        function();
    } catch (const ValidationError&) {
        thrown = true;
    }

    if (!thrown) {
        throw std::runtime_error("expected ValidationError");
    }
}

void testProductValidation() {
    Inventory inventory({
        {"P1", "Keyboard", 50.0, 3}
    });

    assert(inventory.stock("P1") == 3);
}

void testNegativeProductData() {
    expectThrows([] {
        Inventory inventory({
            {"P1", "Keyboard", -1.0, 3}
        });
    });
}

void testInventoryReservation() {
    Inventory inventory({
        {"P1", "Keyboard", 50.0, 3}
    });

    inventory.reserve("P1", 2);
    assert(inventory.stock("P1") == 1);

    inventory.release("P1", 2);
    assert(inventory.stock("P1") == 3);
}

void testInventoryFailure() {
    Inventory inventory({
        {"P1", "Keyboard", 50.0, 3}
    });

    expectThrows([&] {
        inventory.reserve("P1", 4);
    });

    assert(inventory.stock("P1") == 3);
}

void testGovernanceEligibility() {
    MergeEligibilityEngine engine(2, true, true);

    assert(engine.eligible(2, true, true, true));
    assert(!engine.eligible(1, true, true, true));
    assert(!engine.eligible(2, false, true, true));
    assert(!engine.eligible(2, true, false, true));
    assert(!engine.eligible(2, true, true, false));
}

void testGovernancePolicyEdgeCase() {
    MergeEligibilityEngine engine(0, false, false);

    assert(engine.eligible(0, false, false, true));
    assert(!engine.eligible(0, false, false, false));
}

int main() {
    TestRunner runner;

    runner.run("valid product fixture", testProductValidation);
    runner.run("negative product validation", testNegativeProductData);
    runner.run("inventory reservation and release", testInventoryReservation);
    runner.run("inventory insufficient-stock failure", testInventoryFailure);
    runner.run("merge eligibility policy", testGovernanceEligibility);
    runner.run("zero-approval policy edge case", testGovernancePolicyEdgeCase);

    return runner.exitCode();
}
