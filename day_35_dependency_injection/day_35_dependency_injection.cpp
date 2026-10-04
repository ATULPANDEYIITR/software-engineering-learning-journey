#include <algorithm>
#include <cassert>
#include <functional>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Dependency Injection: Repository Governance Case Study
 *
 * The system models a technical service whose business behavior depends on
 * replaceable interfaces. A composition root chooses concrete infrastructure.
 *
 * The same architectural principle used in enterprise systems is demonstrated
 * through an order-processing workflow:
 *
 *   Domain request -> application service -> injected dependencies
 *
 * The service never constructs its repository, payment gateway, or notifier.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic dependency_injection.cpp -o di
 */

struct Order {
    std::string id;
    std::string customerEmail;
    double amount;
};

struct Receipt {
    std::string orderId;
    double amount;
    std::string message;
};

// -----------------------------------------------------------------------------
// Dependency contracts
// -----------------------------------------------------------------------------

class IOrderRepository {
public:
    virtual ~IOrderRepository() = default;
    virtual void save(const Order& order) = 0;
    virtual std::optional<Order> find(const std::string& id) const = 0;
};

class IPaymentGateway {
public:
    virtual ~IPaymentGateway() = default;
    virtual bool charge(const Order& order) = 0;
};

class INotificationService {
public:
    virtual ~INotificationService() = default;
    virtual void send(const Order& order, const Receipt& receipt) = 0;
};

// -----------------------------------------------------------------------------
// Concrete infrastructure
// -----------------------------------------------------------------------------

class MemoryOrderRepository final : public IOrderRepository {
private:
    std::unordered_map<std::string, Order> orders_;

public:
    void save(const Order& order) override {
        auto [iterator, inserted] = orders_.emplace(order.id, order);

        if (!inserted) {
            throw std::runtime_error("Duplicate order: " + order.id);
        }
    }

    std::optional<Order> find(const std::string& id) const override {
        const auto iterator = orders_.find(id);

        if (iterator == orders_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }
};

class SimulatedPaymentGateway final : public IPaymentGateway {
private:
    bool available_;
    std::vector<std::string> chargedOrders_;

public:
    explicit SimulatedPaymentGateway(bool available)
        : available_(available) {}

    bool charge(const Order& order) override {
        if (!available_ || order.amount <= 0.0) {
            return false;
        }

        chargedOrders_.push_back(order.id);
        return true;
    }

    std::size_t chargeCount() const {
        return chargedOrders_.size();
    }
};

class ConsoleNotificationService final : public INotificationService {
public:
    void send(const Order& order, const Receipt& receipt) override {
        if (order.customerEmail.find('@') == std::string::npos) {
            throw std::invalid_argument("Invalid customer email");
        }

        std::cout << "Notification to " << order.customerEmail
                  << ": " << receipt.message << '\n';
    }
};

// -----------------------------------------------------------------------------
// Application service
// -----------------------------------------------------------------------------

class OrderService {
private:
    IOrderRepository& repository_;
    IPaymentGateway& payment_;
    INotificationService& notification_;

    static void validate(const Order& order) {
        if (order.id.empty()) {
            throw std::invalid_argument("Order ID is required");
        }

        if (order.customerEmail.empty() ||
            order.customerEmail.find('@') == std::string::npos) {
            throw std::invalid_argument("Customer email is invalid");
        }

        if (order.amount <= 0.0) {
            throw std::invalid_argument("Order amount must be positive");
        }
    }

public:
    OrderService(
        IOrderRepository& repository,
        IPaymentGateway& payment,
        INotificationService& notification
    )
        : repository_(repository),
          payment_(payment),
          notification_(notification) {}

    Receipt placeOrder(const Order& order) {
        validate(order);

        if (repository_.find(order.id).has_value()) {
            throw std::runtime_error("Order already exists: " + order.id);
        }

        if (!payment_.charge(order)) {
            throw std::runtime_error("Payment declined or unavailable");
        }

        repository_.save(order);

        Receipt receipt{
            order.id,
            order.amount,
            "Order " + order.id + " paid successfully"
        };

        notification_.send(order, receipt);

        return receipt;
    }
};

// -----------------------------------------------------------------------------
// Test doubles
// -----------------------------------------------------------------------------

class FakePaymentGateway final : public IPaymentGateway {
public:
    bool result;
    std::vector<std::string> calls;

    explicit FakePaymentGateway(bool result)
        : result(result) {}

    bool charge(const Order& order) override {
        calls.push_back(order.id);
        return result;
    }
};

class FakeNotificationService final : public INotificationService {
public:
    std::vector<std::string> notifications;

    void send(const Order& order, const Receipt&) override {
        notifications.push_back(order.id);
    }
};

// -----------------------------------------------------------------------------
// Function-level injection
// -----------------------------------------------------------------------------

using TaxPolicy = std::function<double(double)>;

double calculateTotal(double amount, const TaxPolicy& taxPolicy) {
    if (amount < 0.0) {
        throw std::invalid_argument("Amount cannot be negative");
    }

    return amount + taxPolicy(amount);
}

double standardTax(double amount) {
    return amount * 0.18;
}

double zeroTax(double) {
    return 0.0;
}

// -----------------------------------------------------------------------------
// Simple container
// -----------------------------------------------------------------------------

class Container {
private:
    using Factory = std::function<std::shared_ptr<void>()>;

    struct Registration {
        Factory factory;
        bool singleton;
        std::shared_ptr<void> instance;
    };

    std::unordered_map<std::string, Registration> registrations_;

public:
    template <typename Interface, typename Implementation, typename... Args>
    void registerTransient(const std::string& token, Args&&... args) {
        registrations_[token] = Registration{
            [arguments = std::make_tuple(std::forward<Args>(args)...)]() mutable {
                return std::apply(
                    [](auto&&... values) {
                        return std::static_pointer_cast<void>(
                            std::make_shared<Implementation>(
                                std::forward<decltype(values)>(values)...
                            )
                        );
                    },
                    arguments
                );
            },
            false,
            nullptr
        };
    }

    template <typename Implementation>
    void registerSingleton(
        const std::string& token,
        std::shared_ptr<Implementation> instance
    ) {
        registrations_[token] = Registration{
            [instance]() {
                return std::static_pointer_cast<void>(instance);
            },
            true,
            std::static_pointer_cast<void>(instance)
        };
    }

    template <typename Interface>
    std::shared_ptr<Interface> resolve(
        const std::string& token,
        const std::function<std::shared_ptr<Interface>()>& adapter
    ) {
        auto iterator = registrations_.find(token);

        if (iterator == registrations_.end()) {
            throw std::runtime_error("Unregistered dependency: " + token);
        }

        if (iterator->second.singleton) {
            return adapter(iterator->second.instance);
        }

        return adapter(iterator->second.factory());
    }
};

// -----------------------------------------------------------------------------
// Tests
// -----------------------------------------------------------------------------

void testSuccessfulOrder() {
    MemoryOrderRepository repository;
    FakePaymentGateway payment(true);
    FakeNotificationService notification;

    OrderService service(repository, payment, notification);

    const Order order{"CPP-001", "buyer@example.com", 250.0};
    const Receipt receipt = service.placeOrder(order);

    assert(receipt.orderId == "CPP-001");
    assert(repository.find("CPP-001").has_value());
    assert(payment.calls.size() == 1);
    assert(notification.notifications.size() == 1);
}

void testPaymentFailure() {
    MemoryOrderRepository repository;
    FakePaymentGateway payment(false);
    FakeNotificationService notification;

    OrderService service(repository, payment, notification);
    const Order order{"CPP-002", "buyer@example.com", 300.0};

    bool failed = false;

    try {
        service.placeOrder(order);
    } catch (const std::runtime_error& error) {
        failed = std::string(error.what()).find("Payment") != std::string::npos;
    }

    assert(failed);
    assert(!repository.find("CPP-002").has_value());
    assert(notification.notifications.empty());
}

void testDuplicateOrderDoesNotChargeAgain() {
    MemoryOrderRepository repository;
    FakePaymentGateway payment(true);
    FakeNotificationService notification;

    const Order existing{"CPP-003", "existing@example.com", 50.0};
    repository.save(existing);

    OrderService service(repository, payment, notification);

    bool failed = false;

    try {
        service.placeOrder(existing);
    } catch (const std::runtime_error& error) {
        failed = std::string(error.what()).find("already exists") != std::string::npos;
    }

    assert(failed);
    assert(payment.calls.empty());
}

void testInvalidOrder() {
    MemoryOrderRepository repository;
    FakePaymentGateway payment(true);
    FakeNotificationService notification;

    OrderService service(repository, payment, notification);

    bool failed = false;

    try {
        service.placeOrder({"CPP-004", "not-an-email", 20.0});
    } catch (const std::invalid_argument&) {
        failed = true;
    }

    assert(failed);
    assert(payment.calls.empty());
}

void testFunctionInjection() {
    assert(calculateTotal(100.0, standardTax) == 118.0);
    assert(calculateTotal(100.0, zeroTax) == 100.0);
}

// -----------------------------------------------------------------------------
// Composition root
// -----------------------------------------------------------------------------

struct Application {
    std::unique_ptr<IOrderRepository> repository;
    std::unique_ptr<IPaymentGateway> payment;
    std::unique_ptr<INotificationService> notification;
    std::unique_ptr<OrderService> service;
};

Application buildApplication() {
    Application application;

    application.repository = std::make_unique<MemoryOrderRepository>();
    application.payment = std::make_unique<SimulatedPaymentGateway>(true);
    application.notification = std::make_unique<ConsoleNotificationService>();

    application.service = std::make_unique<OrderService>(
        *application.repository,
        *application.payment,
        *application.notification
    );

    return application;
}

int main() {
    std::cout << std::fixed << std::setprecision(2);
    std::cout << "Dependency Injection: C++ enterprise case study\n\n";

    Application application = buildApplication();

    const Order productionOrder{
        "CPP-PROD-001",
        "customer@example.com",
        149.99
    };

    const Receipt receipt = application.service->placeOrder(productionOrder);

    std::cout << receipt.message << '\n';

    std::cout << "\nFunction injection\n";
    std::cout << "Standard total: $"
              << calculateTotal(100.0, standardTax) << '\n';
    std::cout << "Zero-tax total: $"
              << calculateTotal(100.0, zeroTax) << '\n';

    testSuccessfulOrder();
    testPaymentFailure();
    testDuplicateOrderDoesNotChargeAgain();
    testInvalidOrder();
    testFunctionInjection();

    std::cout << "\nAll DI tests passed.\n";
    std::cout << "The application service depends on abstractions, while the "
                 "composition root selects concrete implementations.\n";

    return 0;
}
