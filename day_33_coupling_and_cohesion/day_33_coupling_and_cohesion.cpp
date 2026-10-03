/*
 * Coupling & Cohesion
 *
 * C++17 case study:
 * A repository-independent order fulfillment engine.
 *
 * The system demonstrates how high cohesion and loose coupling affect
 * architecture when several business capabilities interact:
 *
 *   Order -> Inventory -> Payment -> Persistence -> Notification -> Shipping
 *
 * The application layer coordinates the use case while infrastructure
 * implementations are supplied through interfaces.
 */

#include <algorithm>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>


// ---------------------------------------------------------------------------
// Domain model
// ---------------------------------------------------------------------------

struct Product {
    std::string id;
    std::string name;
    double unit_price;
};


struct OrderItem {
    Product product;
    int quantity;

    double subtotal() const {
        return product.unit_price * static_cast<double>(quantity);
    }
};


enum class OrderStatus {
    Created,
    Paid,
    Cancelled,
    Shipped
};


std::string status_name(OrderStatus status) {
    switch (status) {
        case OrderStatus::Created:
            return "created";
        case OrderStatus::Paid:
            return "paid";
        case OrderStatus::Cancelled:
            return "cancelled";
        case OrderStatus::Shipped:
            return "shipped";
    }

    return "unknown";
}


class Order {
public:
    Order(
        std::string id,
        std::string customer_email,
        std::vector<OrderItem> items
    )
        : id_(std::move(id)),
          customer_email_(std::move(customer_email)),
          items_(std::move(items)),
          status_(OrderStatus::Created) {}

    const std::string& id() const {
        return id_;
    }

    const std::string& customer_email() const {
        return customer_email_;
    }

    const std::vector<OrderItem>& items() const {
        return items_;
    }

    OrderStatus status() const {
        return status_;
    }

    double total() const {
        double result = 0.0;

        for (const auto& item : items_) {
            result += item.subtotal();
        }

        return result;
    }

    void mark_paid() {
        if (status_ != OrderStatus::Created) {
            throw std::logic_error(
                "Only a created order can become paid"
            );
        }

        status_ = OrderStatus::Paid;
    }

    void mark_shipped() {
        if (status_ != OrderStatus::Paid) {
            throw std::logic_error(
                "Only a paid order can become shipped"
            );
        }

        status_ = OrderStatus::Shipped;
    }

private:
    std::string id_;
    std::string customer_email_;
    std::vector<OrderItem> items_;
    OrderStatus status_;
};


// ---------------------------------------------------------------------------
// High-cohesion validation
// ---------------------------------------------------------------------------

class OrderValidator {
public:
    void validate(const Order& order) const {
        if (order.id().empty()) {
            throw std::invalid_argument(
                "Order ID cannot be empty"
            );
        }

        if (order.customer_email().find('@') == std::string::npos) {
            throw std::invalid_argument(
                "Customer email is invalid"
            );
        }

        if (order.items().empty()) {
            throw std::invalid_argument(
                "Order must contain at least one item"
            );
        }

        for (const auto& item : order.items()) {
            if (item.product.id.empty()) {
                throw std::invalid_argument(
                    "Product ID cannot be empty"
                );
            }

            if (item.product.unit_price < 0.0) {
                throw std::invalid_argument(
                    "Product price cannot be negative"
                );
            }

            if (item.quantity <= 0) {
                throw std::invalid_argument(
                    "Quantity must be positive"
                );
            }
        }
    }
};


// ---------------------------------------------------------------------------
// Stable abstractions
// ---------------------------------------------------------------------------

class Inventory {
public:
    virtual ~Inventory() = default;

    virtual void reserve(
        const std::string& product_id,
        int quantity
    ) = 0;

    virtual void release(
        const std::string& product_id,
        int quantity
    ) = 0;

    virtual int available(
        const std::string& product_id
    ) const = 0;
};


class PaymentGateway {
public:
    virtual ~PaymentGateway() = default;

    virtual std::string charge(
        const std::string& order_id,
        double amount
    ) = 0;
};


class OrderRepository {
public:
    virtual ~OrderRepository() = default;

    virtual void save(const Order& order) = 0;

    virtual const Order* find(
        const std::string& order_id
    ) const = 0;
};


class NotificationGateway {
public:
    virtual ~NotificationGateway() = default;

    virtual void send_payment_confirmation(
        const std::string& email,
        const std::string& order_id,
        double amount
    ) = 0;
};


class ShippingGateway {
public:
    virtual ~ShippingGateway() = default;

    virtual std::string create_shipment(
        const Order& order
    ) = 0;
};


// ---------------------------------------------------------------------------
// Cohesive infrastructure implementations
// ---------------------------------------------------------------------------

class WarehouseInventory final : public Inventory {
public:
    explicit WarehouseInventory(
        std::unordered_map<std::string, int> stock
    )
        : stock_(std::move(stock)) {}

    void reserve(
        const std::string& product_id,
        int quantity
    ) override {
        if (quantity <= 0) {
            throw std::invalid_argument(
                "Reservation quantity must be positive"
            );
        }

        auto iterator = stock_.find(product_id);

        if (iterator == stock_.end() ||
            iterator->second < quantity) {
            throw std::runtime_error(
                "Insufficient inventory for " + product_id
            );
        }

        iterator->second -= quantity;
    }

    void release(
        const std::string& product_id,
        int quantity
    ) override {
        if (quantity <= 0) {
            throw std::invalid_argument(
                "Release quantity must be positive"
            );
        }

        stock_[product_id] += quantity;
    }

    int available(
        const std::string& product_id
    ) const override {
        auto iterator = stock_.find(product_id);

        if (iterator == stock_.end()) {
            return 0;
        }

        return iterator->second;
    }

private:
    std::unordered_map<std::string, int> stock_;
};


class SimulatedPaymentGateway final : public PaymentGateway {
public:
    explicit SimulatedPaymentGateway(
        std::vector<std::string> rejected_orders = {}
    )
        : rejected_orders_(std::move(rejected_orders)) {}

    std::string charge(
        const std::string& order_id,
        double amount
    ) override {
        if (amount <= 0.0) {
            throw std::invalid_argument(
                "Payment amount must be positive"
            );
        }

        const auto rejected = std::find(
            rejected_orders_.begin(),
            rejected_orders_.end(),
            order_id
        );

        if (rejected != rejected_orders_.end()) {
            throw std::runtime_error(
                "Payment provider rejected " + order_id
            );
        }

        ++transaction_counter_;

        return "PAY-" +
               order_id +
               "-" +
               std::to_string(transaction_counter_);
    }

private:
    std::vector<std::string> rejected_orders_;
    unsigned long long transaction_counter_ = 0;
};


class MemoryOrderRepository final : public OrderRepository {
public:
    void save(const Order& order) override {
        /*
         * The repository owns persistence responsibility.
         * The application service does not need to know whether the real
         * implementation later uses PostgreSQL, SQLite, or another store.
         */
        orders_[order.id()] = order;
    }

    const Order* find(
        const std::string& order_id
    ) const override {
        auto iterator = orders_.find(order_id);

        if (iterator == orders_.end()) {
            return nullptr;
        }

        return &iterator->second;
    }

private:
    std::unordered_map<std::string, Order> orders_;
};


class ConsoleNotificationGateway final
    : public NotificationGateway {
public:
    void send_payment_confirmation(
        const std::string& email,
        const std::string& order_id,
        double amount
    ) override {
        std::cout
            << "[notification] "
            << email
            << " received confirmation for "
            << order_id
            << " amount="
            << std::fixed
            << std::setprecision(2)
            << amount
            << '\n';
    }
};


class SimulatedShippingGateway final
    : public ShippingGateway {
public:
    std::string create_shipment(
        const Order& order
    ) override {
        if (order.status() != OrderStatus::Paid) {
            throw std::logic_error(
                "Only paid orders can be shipped"
            );
        }

        ++shipment_counter_;

        return "SHIP-" +
               order.id() +
               "-" +
               std::to_string(shipment_counter_);
    }

private:
    unsigned long long shipment_counter_ = 0;
};


// ---------------------------------------------------------------------------
// A deliberately cohesive event record
// ---------------------------------------------------------------------------

struct PaymentCompletedEvent {
    std::string order_id;
    std::string transaction_id;
    double amount;
};


class AuditTrail {
public:
    void record(const PaymentCompletedEvent& event) {
        events_.push_back(
            event.order_id +
            ":" +
            event.transaction_id
        );
    }

    std::size_t size() const {
        return events_.size();
    }

private:
    std::vector<std::string> events_;
};


// ---------------------------------------------------------------------------
// Application service
// ---------------------------------------------------------------------------

class OrderApplicationService {
public:
    OrderApplicationService(
        Inventory& inventory,
        PaymentGateway& payment,
        OrderRepository& repository,
        NotificationGateway& notification,
        ShippingGateway& shipping,
        AuditTrail& audit
    )
        : inventory_(inventory),
          payment_(payment),
          repository_(repository),
          notification_(notification),
          shipping_(shipping),
          audit_(audit) {}

    std::string create_and_pay(Order& order) {
        validator_.validate(order);

        struct Reservation {
            std::string product_id;
            int quantity;
        };

        std::vector<Reservation> reservations;

        try {
            /*
             * The application service coordinates the business transaction.
             * It does not implement warehouse, payment, persistence, or
             * notification details itself.
             */
            for (const auto& item : order.items()) {
                inventory_.reserve(
                    item.product.id,
                    item.quantity
                );

                reservations.push_back({
                    item.product.id,
                    item.quantity
                });
            }

            const double amount = order.total();

            const std::string transaction =
                payment_.charge(order.id(), amount);

            order.mark_paid();

            repository_.save(order);

            PaymentCompletedEvent event{
                order.id(),
                transaction,
                amount
            };

            audit_.record(event);

            notification_.send_payment_confirmation(
                order.customer_email(),
                order.id(),
                amount
            );

            return transaction;
        }
        catch (...) {
            /*
             * A payment or persistence failure can occur after inventory has
             * already been reserved. Since the collaborators are not part of
             * one atomic transaction, compensation restores reservations.
             */
            for (auto iterator = reservations.rbegin();
                 iterator != reservations.rend();
                 ++iterator) {
                inventory_.release(
                    iterator->product_id,
                    iterator->quantity
                );
            }

            throw;
        }
    }

    std::string ship(Order& order) {
        if (order.status() != OrderStatus::Paid) {
            throw std::logic_error(
                "Only paid orders may be shipped"
            );
        }

        const std::string shipment =
            shipping_.create_shipment(order);

        order.mark_shipped();
        repository_.save(order);

        return shipment;
    }

private:
    OrderValidator validator_;

    Inventory& inventory_;
    PaymentGateway& payment_;
    OrderRepository& repository_;
    NotificationGateway& notification_;
    ShippingGateway& shipping_;
    AuditTrail& audit_;
};


// ---------------------------------------------------------------------------
// Alternative collaborators used to demonstrate loose coupling
// ---------------------------------------------------------------------------

class RecordingNotificationGateway final
    : public NotificationGateway {
public:
    void send_payment_confirmation(
        const std::string& email,
        const std::string& order_id,
        double amount
    ) override {
        messages.push_back(
            email +
            "|" +
            order_id +
            "|" +
            std::to_string(amount)
        );
    }

    std::vector<std::string> messages;
};


// ---------------------------------------------------------------------------
// Case-study scenarios
// ---------------------------------------------------------------------------

void successful_fulfillment_case() {
    std::cout << "\n=== Successful fulfillment ===\n";

    Product laptop{
        "LAPTOP",
        "Developer Laptop",
        1500.00
    };

    Product mouse{
        "MOUSE",
        "Wireless Mouse",
        40.00
    };

    Order order(
        "ORD-1001",
        "developer@example.com",
        {
            {laptop, 1},
            {mouse, 2}
        }
    );

    WarehouseInventory inventory({
        {"LAPTOP", 5},
        {"MOUSE", 20}
    });

    SimulatedPaymentGateway payment;
    MemoryOrderRepository repository;
    ConsoleNotificationGateway notification;
    SimulatedShippingGateway shipping;
    AuditTrail audit;

    OrderApplicationService application(
        inventory,
        payment,
        repository,
        notification,
        shipping,
        audit
    );

    const std::string transaction =
        application.create_and_pay(order);

    const std::string shipment =
        application.ship(order);

    std::cout
        << "transaction=" << transaction << '\n'
        << "shipment=" << shipment << '\n'
        << "status=" << status_name(order.status()) << '\n'
        << "remaining_laptops="
        << inventory.available("LAPTOP")
        << '\n'
        << "remaining_mice="
        << inventory.available("MOUSE")
        << '\n'
        << "audit_events="
        << audit.size()
        << '\n';
}


void payment_failure_case() {
    std::cout << "\n=== Payment failure and compensation ===\n";

    Product keyboard{
        "KEYBOARD",
        "Mechanical Keyboard",
        90.00
    };

    Order order(
        "ORD-1002",
        "developer@example.com",
        {
            {keyboard, 2}
        }
    );

    WarehouseInventory inventory({
        {"KEYBOARD", 5}
    });

    SimulatedPaymentGateway payment({
        "ORD-1002"
    });

    MemoryOrderRepository repository;
    ConsoleNotificationGateway notification;
    SimulatedShippingGateway shipping;
    AuditTrail audit;

    OrderApplicationService application(
        inventory,
        payment,
        repository,
        notification,
        shipping,
        audit
    );

    const int before =
        inventory.available("KEYBOARD");

    try {
        application.create_and_pay(order);
    }
    catch (const std::exception& error) {
        std::cout
            << "expected failure: "
            << error.what()
            << '\n';
    }

    const int after =
        inventory.available("KEYBOARD");

    std::cout
        << "inventory_before="
        << before
        << '\n'
        << "inventory_after="
        << after
        << '\n'
        << "compensation_preserved_inventory="
        << std::boolalpha
        << (before == after)
        << '\n';
}


void dependency_substitution_case() {
    std::cout << "\n=== Dependency substitution ===\n";

    Product storage{
        "SSD",
        "1 TB SSD",
        110.00
    };

    Order order(
        "ORD-1003",
        "test@example.com",
        {
            {storage, 1}
        }
    );

    WarehouseInventory inventory({
        {"SSD", 10}
    });

    SimulatedPaymentGateway payment;
    MemoryOrderRepository repository;
    RecordingNotificationGateway notification;
    SimulatedShippingGateway shipping;
    AuditTrail audit;

    /*
     * Only the notification implementation changed.
     * OrderApplicationService did not need to change because it depends on
     * the NotificationGateway abstraction.
     */
    OrderApplicationService application(
        inventory,
        payment,
        repository,
        notification,
        shipping,
        audit
    );

    application.create_and_pay(order);

    std::cout
        << "recorded_notifications="
        << notification.messages.size()
        << '\n';
}


void validation_failure_case() {
    std::cout << "\n=== Validation failure before infrastructure work ===\n";

    Product product{
        "MOUSE",
        "Mouse",
        40.00
    };

    Order invalid_order(
        "ORD-1004",
        "invalid-email",
        {
            {product, 1}
        }
    );

    WarehouseInventory inventory({
        {"MOUSE", 10}
    });

    SimulatedPaymentGateway payment;
    MemoryOrderRepository repository;
    ConsoleNotificationGateway notification;
    SimulatedShippingGateway shipping;
    AuditTrail audit;

    OrderApplicationService application(
        inventory,
        payment,
        repository,
        notification,
        shipping,
        audit
    );

    try {
        application.create_and_pay(invalid_order);
    }
    catch (const std::exception& error) {
        std::cout
            << "validation rejected request: "
            << error.what()
            << '\n';
    }

    std::cout
        << "inventory remains="
        << inventory.available("MOUSE")
        << '\n';
}


void architecture_boundary_case() {
    std::cout << "\n=== Architecture boundary ===\n";

    /*
     * unique_ptr demonstrates ownership at the composition boundary.
     * The application service itself receives references and does not own
     * infrastructure lifetime.
     */
    auto inventory =
        std::make_unique<WarehouseInventory>(
            std::unordered_map<std::string, int>{
                {"CAMERA", 3}
            }
        );

    auto payment =
        std::make_unique<SimulatedPaymentGateway>();

    auto repository =
        std::make_unique<MemoryOrderRepository>();

    auto notification =
        std::make_unique<RecordingNotificationGateway>();

    auto shipping =
        std::make_unique<SimulatedShippingGateway>();

    auto audit =
        std::make_unique<AuditTrail>();

    Product camera{
        "CAMERA",
        "Development Camera",
        700.00
    };

    Order order(
        "ORD-1005",
        "architect@example.com",
        {
            {camera, 1}
        }
    );

    OrderApplicationService application(
        *inventory,
        *payment,
        *repository,
        *notification,
        *shipping,
        *audit
    );

    application.create_and_pay(order);

    std::cout
        << "Composition root assembled "
        << "independent cohesive components.\n";
}


// ---------------------------------------------------------------------------
// Lightweight executable checks
// ---------------------------------------------------------------------------

void require(
    bool condition,
    const std::string& message
) {
    if (!condition) {
        throw std::runtime_error(
            "Architecture check failed: " + message
        );
    }
}


void run_checks() {
    std::cout << "\n=== Architecture checks ===\n";

    Product product{
        "BOOK",
        "Architecture Book",
        50.00
    };

    Order order(
        "ORD-CHECK",
        "check@example.com",
        {
            {product, 2}
        }
    );

    WarehouseInventory inventory({
        {"BOOK", 10}
    });

    SimulatedPaymentGateway payment;
    MemoryOrderRepository repository;
    RecordingNotificationGateway notification;
    SimulatedShippingGateway shipping;
    AuditTrail audit;

    OrderApplicationService application(
        inventory,
        payment,
        repository,
        notification,
        shipping,
        audit
    );

    application.create_and_pay(order);

    require(
        order.status() == OrderStatus::Paid,
        "successful payment should produce Paid state"
    );

    require(
        inventory.available("BOOK") == 8,
        "inventory should be reduced after reservation"
    );

    require(
        repository.find("ORD-CHECK") != nullptr,
        "repository should contain the paid order"
    );

    require(
        notification.messages.size() == 1,
        "notification collaborator should receive one message"
    );

    require(
        audit.size() == 1,
        "audit component should record one payment event"
    );

    const std::string shipment =
        application.ship(order);

    require(
        !shipment.empty(),
        "shipping should return a shipment identifier"
    );

    require(
        order.status() == OrderStatus::Shipped,
        "successful shipping should update order state"
    );

    std::cout << "All architecture checks passed.\n";
}


// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

int main() {
    try {
        successful_fulfillment_case();
        payment_failure_case();
        dependency_substitution_case();
        validation_failure_case();
        architecture_boundary_case();
        run_checks();

        std::cout
            << "\nCoupling and cohesion case study completed successfully.\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }
}
