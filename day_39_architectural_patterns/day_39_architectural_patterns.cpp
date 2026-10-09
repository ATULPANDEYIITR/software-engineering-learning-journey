#include <algorithm>
#include <cmath>
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
 * Architectural Patterns Case Study
 *
 * Scenario:
 * A technical organization operates an order-processing platform.
 * The same business capability is represented using:
 *
 *   Layered architecture
 *   MVC architecture
 *   Hexagonal architecture
 *
 * The case study focuses on the architectural boundary decisions,
 * not on generic C++ syntax.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic architecture_patterns.cpp -o architecture_patterns
 */

struct OrderItem {
    std::string productId;
    int quantity;
    double unitPrice;

    double subtotal() const {
        return quantity * unitPrice;
    }
};

class Order {
private:
    std::string id_;
    std::string customerId_;
    std::vector<OrderItem> items_;
    std::string status_ = "PENDING";

public:
    Order(
        std::string id,
        std::string customerId,
        std::vector<OrderItem> items
    )
        : id_(std::move(id)),
          customerId_(std::move(customerId)),
          items_(std::move(items)) {

        if (customerId_.empty()) {
            throw std::invalid_argument("Customer ID is required.");
        }

        if (items_.empty()) {
            throw std::invalid_argument(
                "An order must contain at least one item."
            );
        }

        for (const auto& item : items_) {
            if (item.quantity <= 0) {
                throw std::invalid_argument(
                    "Order quantities must be positive."
                );
            }

            if (!std::isfinite(item.unitPrice) || item.unitPrice < 0) {
                throw std::invalid_argument(
                    "Unit prices must be finite and non-negative."
                );
            }
        }
    }

    void confirm() {
        if (status_ != "PENDING") {
            throw std::logic_error(
                "Only pending orders can be confirmed."
            );
        }

        status_ = "CONFIRMED";
    }

    const std::string& id() const {
        return id_;
    }

    const std::string& customerId() const {
        return customerId_;
    }

    const std::vector<OrderItem>& items() const {
        return items_;
    }

    const std::string& status() const {
        return status_;
    }

    double total() const {
        double result = 0.0;

        for (const auto& item : items_) {
            result += item.subtotal();
        }

        return std::round(result * 100.0) / 100.0;
    }
};


// ============================================================
// LAYERED ARCHITECTURE
// ============================================================
//
// Presentation
//      |
// Application Service
//      |
// Domain
//      |
// Infrastructure
//
// The application service calls concrete infrastructure services.
// This is straightforward and familiar, but the application layer
// therefore knows which infrastructure implementations it uses.
// ============================================================

class LayeredRepository {
private:
    std::unordered_map<std::string, Order> orders_;

public:
    void save(Order order) {
        orders_.insert_or_assign(order.id(), std::move(order));
    }

    const Order* findById(const std::string& id) const {
        auto it = orders_.find(id);

        if (it == orders_.end()) {
            return nullptr;
        }

        return &it->second;
    }
};

class LayeredNotificationService {
public:
    void sendConfirmation(const Order& order) const {
        std::cout
            << "[Layered notification] Order "
            << order.id()
            << " confirmed for "
            << order.customerId()
            << '\n';
    }
};

class LayeredOrderService {
private:
    LayeredRepository& repository_;
    LayeredNotificationService& notification_;

public:
    LayeredOrderService(
        LayeredRepository& repository,
        LayeredNotificationService& notification
    )
        : repository_(repository),
          notification_(notification) {}

    const Order* createOrder(
        const std::string& customerId,
        const std::vector<OrderItem>& items
    ) {
        static int sequence = 1000;

        Order order(
            "LAYER-" + std::to_string(sequence++),
            customerId,
            items
        );

        order.confirm();
        repository_.save(std::move(order));

        const Order* saved = repository_.findById(
            "LAYER-" + std::to_string(sequence - 1)
        );

        if (saved != nullptr) {
            notification_.sendConfirmation(*saved);
        }

        return saved;
    }
};


// ============================================================
// MVC ARCHITECTURE
// ============================================================
//
// Model:
//   Maintains order state and business operations.
//
// Controller:
//   Converts an external action into model operations.
//
// View:
//   Produces a presentation representation.
//
// The model does not format console output. The view does not mutate
// order state. The controller coordinates the interaction.
// ============================================================

class MvcModel {
private:
    std::unordered_map<std::string, Order> orders_;
    int sequence_ = 2000;

public:
    const Order& create(
        const std::string& customerId,
        const std::vector<OrderItem>& items
    ) {
        const std::string id = "MVC-" + std::to_string(sequence_++);

        Order order(id, customerId, items);
        order.confirm();

        auto result = orders_.emplace(id, std::move(order));
        return result.first->second;
    }

    const Order* find(const std::string& id) const {
        auto it = orders_.find(id);

        if (it == orders_.end()) {
            return nullptr;
        }

        return &it->second;
    }
};

class MvcView {
public:
    std::string render(const Order* order) const {
        if (order == nullptr) {
            return "Order not found.";
        }

        std::ostringstream output;

        output << "Order: " << order->id() << '\n'
               << "Customer: " << order->customerId() << '\n'
               << "Status: " << order->status() << '\n'
               << "Total: " << std::fixed << std::setprecision(2)
               << order->total();

        return output.str();
    }
};

class MvcController {
private:
    MvcModel& model_;
    const MvcView& view_;

public:
    MvcController(MvcModel& model, const MvcView& view)
        : model_(model), view_(view) {}

    std::string createOrder(
        const std::string& customerId,
        const std::vector<OrderItem>& items
    ) {
        try {
            const Order& order = model_.create(customerId, items);
            return view_.render(&order);
        } catch (const std::exception& error) {
            return std::string("Order error: ") + error.what();
        }
    }
};


// ============================================================
// HEXAGONAL ARCHITECTURE
// ============================================================
//
// The core knows only abstract ports.
//
// Driving side:
//   OrderApplication receives a use-case request.
//
// Driven side:
//   OrderRepositoryPort and NotificationPort describe capabilities.
//
// Adapters implement those ports.
//
// This dependency direction means a database implementation can be
// replaced by another adapter without changing the business core.
// ============================================================

class OrderRepositoryPort {
public:
    virtual ~OrderRepositoryPort() = default;

    virtual void save(Order order) = 0;

    virtual std::optional<Order> findById(
        const std::string& id
    ) const = 0;
};

class NotificationPort {
public:
    virtual ~NotificationPort() = default;

    virtual void sendConfirmation(const Order& order) = 0;
};


class MemoryOrderAdapter final : public OrderRepositoryPort {
private:
    std::unordered_map<std::string, Order> orders_;

public:
    void save(Order order) override {
        orders_.insert_or_assign(order.id(), std::move(order));
    }

    std::optional<Order> findById(
        const std::string& id
    ) const override {

        auto it = orders_.find(id);

        if (it == orders_.end()) {
            return std::nullopt;
        }

        return it->second;
    }
};


class ConsoleNotificationAdapter final : public NotificationPort {
public:
    void sendConfirmation(const Order& order) override {
        std::cout
            << "[Hexagonal notification] "
            << order.id()
            << " confirmed for "
            << order.customerId()
            << '\n';
    }
};


class RecordingNotificationAdapter final : public NotificationPort {
private:
    std::vector<std::string> confirmedOrders_;

public:
    void sendConfirmation(const Order& order) override {
        confirmedOrders_.push_back(order.id());
    }

    const std::vector<std::string>& confirmedOrders() const {
        return confirmedOrders_;
    }
};


class OrderApplication {
private:
    OrderRepositoryPort& repository_;
    NotificationPort& notification_;
    int sequence_ = 3000;

public:
    OrderApplication(
        OrderRepositoryPort& repository,
        NotificationPort& notification
    )
        : repository_(repository),
          notification_(notification) {}

    Order placeOrder(
        const std::string& customerId,
        const std::vector<OrderItem>& items
    ) {
        const std::string id =
            "HEX-" + std::to_string(sequence_++);

        Order order(id, customerId, items);
        order.confirm();

        repository_.save(order);
        notification_.sendConfirmation(order);

        return order;
    }
};


// ============================================================
// Hexagonal core test with fake adapters
// ============================================================
//
// No database, HTTP server, console notifier, or filesystem is
// required. This demonstrates that the core's dependencies are
// architectural ports rather than technologies.
// ============================================================

void testHexagonalApplication() {
    MemoryOrderAdapter repository;
    RecordingNotificationAdapter notification;

    OrderApplication application(repository, notification);

    Order order = application.placeOrder(
        "TEST-CUSTOMER",
        {
            {"SERVER", 1, 1500.00},
            {"SSD", 2, 180.00}
        }
    );

    if (std::abs(order.total() - 1860.00) > 0.0001) {
        throw std::runtime_error("Incorrect order total.");
    }

    if (notification.confirmedOrders().size() != 1) {
        throw std::runtime_error(
            "Expected exactly one confirmation."
        );
    }

    auto persisted = repository.findById(order.id());

    if (!persisted.has_value()) {
        throw std::runtime_error(
            "Order was not persisted through the repository port."
        );
    }

    std::cout << "[Test] Hexagonal application passed.\n";
}


// ============================================================
// Performance and boundary demonstration
// ============================================================
//
// unordered_map provides average O(1) lookup for repository IDs.
// Vector traversal of order items is O(n), which is appropriate
// because every item contributes to the total.
//
// The architecture itself does not automatically make an operation
// faster. It changes dependency structure and responsibility
// boundaries. Performance must still be designed at the relevant
// data and infrastructure boundaries.
// ============================================================

void demonstrateArchitectures() {
    std::cout << "=== Layered Architecture ===\n";

    LayeredRepository layeredRepository;
    LayeredNotificationService layeredNotification;
    LayeredOrderService layeredService(
        layeredRepository,
        layeredNotification
    );

    const Order* layeredOrder = layeredService.createOrder(
        "CUST-LAYER",
        {
            {"KEYBOARD", 2, 75.00},
            {"MOUSE", 1, 40.00}
        }
    );

    if (layeredOrder != nullptr) {
        std::cout
            << "Layered total: "
            << std::fixed << std::setprecision(2)
            << layeredOrder->total()
            << "\n\n";
    }

    std::cout << "=== MVC Architecture ===\n";

    MvcModel model;
    MvcView view;
    MvcController controller(model, view);

    std::cout
        << controller.createOrder(
            "CUST-MVC",
            {
                {"MONITOR", 1, 300.00},
                {"CABLE", 3, 12.50}
            }
        )
        << "\n\n";

    std::cout << "=== Hexagonal Architecture ===\n";

    MemoryOrderAdapter repository;
    ConsoleNotificationAdapter notification;

    OrderApplication application(repository, notification);

    Order hexOrder = application.placeOrder(
        "CUST-HEX",
        {
            {"API-GATEWAY", 1, 500.00},
            {"CACHE", 2, 125.00}
        }
    );

    std::cout
        << "Hexagonal total: "
        << std::fixed << std::setprecision(2)
        << hexOrder.total()
        << "\n\n";

    std::cout << "=== Failure Handling ===\n";

    try {
        application.placeOrder(
            "CUST-INVALID",
            {
                {"BROKEN", 0, 100.00}
            }
        );
    } catch (const std::exception& error) {
        std::cout
            << "Rejected invalid order: "
            << error.what()
            << '\n';
    }

    std::cout << "\n=== Port Isolation Test ===\n";
    testHexagonalApplication();

    std::cout << "\n=== Architectural Distinction ===\n";
    std::cout
        << "Layered: responsibility is organized into vertical layers.\n"
        << "MVC: input control, state, and presentation are separated.\n"
        << "Hexagonal: the application core depends on ports, while "
           "adapters depend on those ports.\n";
}


int main() {
    try {
        demonstrateArchitectures();
        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Fatal application error: "
            << error.what()
            << '\n';

        return 1;
    }
}
