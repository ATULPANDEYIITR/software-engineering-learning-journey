#include <algorithm>
#include <chrono>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <random>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
    Object-Oriented Programming Case Study
    =======================================

    Scenario:
        A scalable order-processing platform for an online marketplace.

    The system demonstrates:
        - Encapsulation
        - Inheritance
        - Runtime polymorphism
        - Abstraction
        - Composition
        - Dependency injection
        - Interfaces through abstract classes
        - Validation and domain exceptions
        - State transitions
        - Factory-style creation
        - Event publishing
        - Pricing strategies
        - Payment providers
        - Shipping providers
        - Reporting
        - Smart pointers and ownership
        - Complexity and performance considerations

    Standard:
        C++17 or later

    Compile:
        g++ -std=c++17 -O2 -Wall -Wextra -pedantic main.cpp -o oop_case_study
*/

namespace oop_case_study {

// ============================================================================
// Utility Functions
// ============================================================================

void printSection(const std::string& title) {
    std::cout << "\n" << std::string(78, '=') << "\n";
    std::cout << title << "\n";
    std::cout << std::string(78, '=') << "\n";
}

std::string money(double value) {
    std::ostringstream stream;
    stream << std::fixed << std::setprecision(2) << "INR " << value;
    return stream.str();
}


// ============================================================================
// Domain Exceptions
// ============================================================================

class DomainError : public std::runtime_error {
public:
    explicit DomainError(const std::string& message)
        : std::runtime_error(message) {}
};

class ValidationError : public DomainError {
public:
    explicit ValidationError(const std::string& message)
        : DomainError(message) {}
};

class InsufficientFundsError : public DomainError {
public:
    explicit InsufficientFundsError(const std::string& message)
        : DomainError(message) {}
};

class InvalidStateError : public DomainError {
public:
    explicit InvalidStateError(const std::string& message)
        : DomainError(message) {}
};


// ============================================================================
// Encapsulation: Customer
// ============================================================================

class Customer {
private:
    // Private state cannot be modified directly by external code.
    std::string id_;
    std::string name_;
    std::string email_;

public:
    Customer(std::string id, std::string name, std::string email)
        : id_(std::move(id)),
          name_(std::move(name)),
          email_(std::move(email)) {

        if (id_.empty()) {
            throw ValidationError("Customer ID cannot be empty.");
        }

        if (name_.empty()) {
            throw ValidationError("Customer name cannot be empty.");
        }

        if (email_.find('@') == std::string::npos) {
            throw ValidationError("Customer email must contain '@'.");
        }
    }

    const std::string& id() const {
        return id_;
    }

    const std::string& name() const {
        return name_;
    }

    const std::string& email() const {
        return email_;
    }

    void changeEmail(const std::string& newEmail) {
        if (newEmail.find('@') == std::string::npos) {
            throw ValidationError("Invalid email address.");
        }

        email_ = newEmail;
    }
};


// ============================================================================
// Encapsulation: Product
// ============================================================================

class Product {
private:
    std::string sku_;
    std::string name_;
    double price_;
    int stock_;

public:
    Product(
        std::string sku,
        std::string name,
        double price,
        int stock
    )
        : sku_(std::move(sku)),
          name_(std::move(name)),
          price_(price),
          stock_(stock) {

        if (sku_.empty() || name_.empty()) {
            throw ValidationError("Product SKU and name are required.");
        }

        if (!std::isfinite(price_) || price_ < 0) {
            throw ValidationError("Product price must be non-negative.");
        }

        if (stock_ < 0) {
            throw ValidationError("Product stock cannot be negative.");
        }
    }

    const std::string& sku() const {
        return sku_;
    }

    const std::string& name() const {
        return name_;
    }

    double price() const {
        return price_;
    }

    int stock() const {
        return stock_;
    }

    void restock(int quantity) {
        if (quantity <= 0) {
            throw ValidationError("Restock quantity must be positive.");
        }

        stock_ += quantity;
    }

    void reserve(int quantity) {
        if (quantity <= 0) {
            throw ValidationError("Reservation quantity must be positive.");
        }

        if (quantity > stock_) {
            throw DomainError("Insufficient product stock.");
        }

        stock_ -= quantity;
    }
};


// ============================================================================
// Order Item
// ============================================================================

class OrderItem {
private:
    std::shared_ptr<Product> product_;
    int quantity_;

public:
    OrderItem(std::shared_ptr<Product> product, int quantity)
        : product_(std::move(product)),
          quantity_(quantity) {

        if (!product_) {
            throw ValidationError("Order item requires a product.");
        }

        if (quantity_ <= 0) {
            throw ValidationError("Order quantity must be positive.");
        }
    }

    const Product& product() const {
        return *product_;
    }

    int quantity() const {
        return quantity_;
    }

    double subtotal() const {
        return product_->price() * quantity_;
    }
};


// ============================================================================
// Abstraction: Payment Provider
// ============================================================================

class PaymentProvider {
public:
    virtual ~PaymentProvider() = default;

    // Pure virtual functions form the abstraction contract.
    virtual std::string providerName() const = 0;
    virtual bool authorize(double amount) = 0;
    virtual bool capture(double amount) = 0;
};


// ============================================================================
// Inheritance + Polymorphism: Card Payment
// ============================================================================

class CardPayment final : public PaymentProvider {
private:
    double authorizationLimit_;

public:
    explicit CardPayment(double authorizationLimit = 100000.0)
        : authorizationLimit_(authorizationLimit) {}

    std::string providerName() const override {
        return "Card";
    }

    bool authorize(double amount) override {
        return amount > 0 && amount <= authorizationLimit_;
    }

    bool capture(double amount) override {
        return amount > 0 && amount <= authorizationLimit_;
    }
};


// ============================================================================
// Inheritance + Polymorphism: Wallet Payment
// ============================================================================

class WalletPayment final : public PaymentProvider {
private:
    double walletLimit_;

public:
    explicit WalletPayment(double walletLimit = 50000.0)
        : walletLimit_(walletLimit) {}

    std::string providerName() const override {
        return "Wallet";
    }

    bool authorize(double amount) override {
        return amount > 0 && amount <= walletLimit_;
    }

    bool capture(double amount) override {
        return amount > 0 && amount <= walletLimit_;
    }
};


// ============================================================================
// Inheritance + Polymorphism: Bank Transfer
// ============================================================================

class BankTransferPayment final : public PaymentProvider {
public:
    std::string providerName() const override {
        return "Bank Transfer";
    }

    bool authorize(double amount) override {
        return amount > 0;
    }

    bool capture(double amount) override {
        return amount > 0;
    }
};


// ============================================================================
// Abstraction: Shipping Provider
// ============================================================================

class ShippingProvider {
public:
    virtual ~ShippingProvider() = default;

    virtual std::string providerName() const = 0;

    virtual double calculateCost(
        double orderValue,
        double weightKg,
        double distanceKm
    ) const = 0;
};


// ============================================================================
// Concrete Shipping Providers
// ============================================================================

class StandardShipping final : public ShippingProvider {
public:
    std::string providerName() const override {
        return "Standard";
    }

    double calculateCost(
        double,
        double weightKg,
        double distanceKm
    ) const override {
        return 50.0 + weightKg * 20.0 + distanceKm * 0.50;
    }
};

class ExpressShipping final : public ShippingProvider {
public:
    std::string providerName() const override {
        return "Express";
    }

    double calculateCost(
        double,
        double weightKg,
        double distanceKm
    ) const override {
        return 150.0 + weightKg * 35.0 + distanceKm * 0.90;
    }
};

class InternationalShipping final : public ShippingProvider {
public:
    std::string providerName() const override {
        return "International";
    }

    double calculateCost(
        double,
        double weightKg,
        double distanceKm
    ) const override {
        return 500.0 + weightKg * 75.0 + distanceKm * 2.50;
    }
};


// ============================================================================
// Abstraction: Discount Strategy
// ============================================================================

class DiscountPolicy {
public:
    virtual ~DiscountPolicy() = default;

    virtual std::string name() const = 0;

    virtual double calculateDiscount(double subtotal) const = 0;
};


class NoDiscount final : public DiscountPolicy {
public:
    std::string name() const override {
        return "No Discount";
    }

    double calculateDiscount(double) const override {
        return 0.0;
    }
};


class PercentageDiscount final : public DiscountPolicy {
private:
    double percentage_;

public:
    explicit PercentageDiscount(double percentage)
        : percentage_(percentage) {

        if (percentage_ < 0 || percentage_ > 100) {
            throw ValidationError(
                "Discount percentage must be between 0 and 100."
            );
        }
    }

    std::string name() const override {
        return "Percentage Discount";
    }

    double calculateDiscount(double subtotal) const override {
        return subtotal * percentage_ / 100.0;
    }
};


// ============================================================================
// Order State
// ============================================================================

enum class OrderStatus {
    Created,
    Paid,
    Shipped,
    Cancelled
};

std::string statusName(OrderStatus status) {
    switch (status) {
        case OrderStatus::Created:
            return "Created";
        case OrderStatus::Paid:
            return "Paid";
        case OrderStatus::Shipped:
            return "Shipped";
        case OrderStatus::Cancelled:
            return "Cancelled";
    }

    return "Unknown";
}


// ============================================================================
// Order Aggregate
// ============================================================================

class Order {
private:
    std::string id_;
    Customer customer_;
    std::vector<OrderItem> items_;
    OrderStatus status_ = OrderStatus::Created;

    double weightKg_ = 0.0;
    double distanceKm_ = 0.0;

public:
    Order(
        std::string id,
        Customer customer,
        double distanceKm
    )
        : id_(std::move(id)),
          customer_(std::move(customer)),
          distanceKm_(distanceKm) {

        if (id_.empty()) {
            throw ValidationError("Order ID is required.");
        }

        if (distanceKm_ < 0) {
            throw ValidationError(
                "Shipping distance cannot be negative."
            );
        }
    }

    const std::string& id() const {
        return id_;
    }

    const Customer& customer() const {
        return customer_;
    }

    OrderStatus status() const {
        return status_;
    }

    double weightKg() const {
        return weightKg_;
    }

    double distanceKm() const {
        return distanceKm_;
    }

    void addItem(
        const std::shared_ptr<Product>& product,
        int quantity
    ) {
        if (status_ != OrderStatus::Created) {
            throw InvalidStateError(
                "Items cannot be added after order processing begins."
            );
        }

        if (!product) {
            throw ValidationError("Product cannot be null.");
        }

        product->reserve(quantity);

        items_.emplace_back(product, quantity);

        // The domain object owns the rule for computing total shipping weight.
        weightKg_ += quantity * 0.5;
    }

    const std::vector<OrderItem>& items() const {
        return items_;
    }

    double subtotal() const {
        double total = 0.0;

        for (const auto& item : items_) {
            total += item.subtotal();
        }

        return total;
    }

    void markPaid() {
        if (status_ != OrderStatus::Created) {
            throw InvalidStateError(
                "Only a created order can become paid."
            );
        }

        status_ = OrderStatus::Paid;
    }

    void markShipped() {
        if (status_ != OrderStatus::Paid) {
            throw InvalidStateError(
                "Only a paid order can become shipped."
            );
        }

        status_ = OrderStatus::Shipped;
    }

    void cancel() {
        if (status_ == OrderStatus::Shipped) {
            throw InvalidStateError(
                "A shipped order cannot be cancelled."
            );
        }

        if (status_ == OrderStatus::Cancelled) {
            throw InvalidStateError(
                "Order is already cancelled."
            );
        }

        status_ = OrderStatus::Cancelled;
    }
};


// ============================================================================
// Event System
// ============================================================================

struct OrderEvent {
    std::string type;
    std::string orderId;
    std::string message;
};

class EventBus {
private:
    using Handler = std::function<void(const OrderEvent&)>;

    std::unordered_map<std::string, std::vector<Handler>> handlers_;

public:
    void subscribe(
        const std::string& eventType,
        Handler handler
    ) {
        handlers_[eventType].push_back(std::move(handler));
    }

    void publish(const OrderEvent& event) const {
        auto iterator = handlers_.find(event.type);

        if (iterator == handlers_.end()) {
            return;
        }

        for (const auto& handler : iterator->second) {
            handler(event);
        }
    }
};


// ============================================================================
// Order Repository Abstraction
// ============================================================================

class OrderRepository {
public:
    virtual ~OrderRepository() = default;

    virtual void save(const std::shared_ptr<Order>& order) = 0;

    virtual std::shared_ptr<Order> findById(
        const std::string& id
    ) const = 0;
};


// ============================================================================
// In-Memory Repository
// ============================================================================

class InMemoryOrderRepository final : public OrderRepository {
private:
    std::unordered_map<std::string, std::shared_ptr<Order>> orders_;

public:
    void save(const std::shared_ptr<Order>& order) override {
        if (!order) {
            throw ValidationError("Cannot save a null order.");
        }

        orders_[order->id()] = order;
    }

    std::shared_ptr<Order> findById(
        const std::string& id
    ) const override {

        auto iterator = orders_.find(id);

        if (iterator == orders_.end()) {
            return nullptr;
        }

        return iterator->second;
    }
};


// ============================================================================
// Order Processor
// ============================================================================

class OrderProcessor {
private:
    // Dependency inversion:
    // high-level business logic depends on abstractions.
    std::unique_ptr<PaymentProvider> paymentProvider_;
    std::unique_ptr<ShippingProvider> shippingProvider_;
    std::unique_ptr<DiscountPolicy> discountPolicy_;
    std::shared_ptr<OrderRepository> repository_;
    std::shared_ptr<EventBus> eventBus_;

public:
    OrderProcessor(
        std::unique_ptr<PaymentProvider> paymentProvider,
        std::unique_ptr<ShippingProvider> shippingProvider,
        std::unique_ptr<DiscountPolicy> discountPolicy,
        std::shared_ptr<OrderRepository> repository,
        std::shared_ptr<EventBus> eventBus
    )
        : paymentProvider_(std::move(paymentProvider)),
          shippingProvider_(std::move(shippingProvider)),
          discountPolicy_(std::move(discountPolicy)),
          repository_(std::move(repository)),
          eventBus_(std::move(eventBus)) {

        if (!paymentProvider_ ||
            !shippingProvider_ ||
            !discountPolicy_ ||
            !repository_ ||
            !eventBus_) {
            throw ValidationError(
                "OrderProcessor dependencies cannot be null."
            );
        }
    }

    double finalAmount(const Order& order) const {
        const double subtotal = order.subtotal();
        const double discount =
            discountPolicy_->calculateDiscount(subtotal);

        const double shipping =
            shippingProvider_->calculateCost(
                subtotal,
                order.weightKg(),
                order.distanceKm()
            );

        return subtotal - discount + shipping;
    }

    void process(const std::shared_ptr<Order>& order) {
        if (!order) {
            throw ValidationError("Order cannot be null.");
        }

        const double subtotal = order->subtotal();
        const double discount =
            discountPolicy_->calculateDiscount(subtotal);

        const double shipping =
            shippingProvider_->calculateCost(
                subtotal,
                order->weightKg(),
                order->distanceKm()
            );

        const double total = subtotal - discount + shipping;

        std::cout << "\nProcessing order " << order->id() << "\n";
        std::cout << "Customer: " << order->customer().name() << "\n";
        std::cout << "Subtotal: " << money(subtotal) << "\n";
        std::cout << "Discount: " << money(discount) << "\n";
        std::cout << "Shipping: " << money(shipping) << "\n";
        std::cout << "Total:    " << money(total) << "\n";
        std::cout << "Payment:  "
                  << paymentProvider_->providerName()
                  << "\n";

        if (!paymentProvider_->authorize(total)) {
            throw DomainError("Payment authorization failed.");
        }

        if (!paymentProvider_->capture(total)) {
            throw DomainError("Payment capture failed.");
        }

        order->markPaid();

        eventBus_->publish({
            "order.paid",
            order->id(),
            "Payment captured successfully."
        });

        order->markShipped();

        eventBus_->publish({
            "order.shipped",
            order->id(),
            "Shipment created successfully."
        });

        repository_->save(order);
    }
};


// ============================================================================
// Factory
// ============================================================================

std::unique_ptr<PaymentProvider> createPaymentProvider(
    const std::string& method
) {
    if (method == "card") {
        return std::make_unique<CardPayment>();
    }

    if (method == "wallet") {
        return std::make_unique<WalletPayment>();
    }

    if (method == "bank") {
        return std::make_unique<BankTransferPayment>();
    }

    throw ValidationError(
        "Unsupported payment method: " + method
    );
}


std::unique_ptr<ShippingProvider> createShippingProvider(
    const std::string& type
) {
    if (type == "standard") {
        return std::make_unique<StandardShipping>();
    }

    if (type == "express") {
        return std::make_unique<ExpressShipping>();
    }

    if (type == "international") {
        return std::make_unique<InternationalShipping>();
    }

    throw ValidationError(
        "Unsupported shipping type: " + type
    );
}


// ============================================================================
// Reporting
// ============================================================================

class ReportGenerator {
public:
    virtual ~ReportGenerator() = default;

    virtual std::string generate(
        const Order& order
    ) const = 0;
};


class TextReportGenerator final : public ReportGenerator {
public:
    std::string generate(const Order& order) const override {
        std::ostringstream output;

        output << "ORDER REPORT\n";
        output << "ID: " << order.id() << "\n";
        output << "Customer: " << order.customer().name() << "\n";
        output << "Status: " << statusName(order.status()) << "\n";
        output << "Subtotal: " << money(order.subtotal()) << "\n";
        output << "Items: " << order.items().size() << "\n";

        return output.str();
    }
};


// ============================================================================
// Unit-Style Assertions
// ============================================================================

void require(
    bool condition,
    const std::string& message
) {
    if (!condition) {
        throw std::runtime_error(
            "Self-check failed: " + message
        );
    }
}


// ============================================================================
// Main Case Study
// ============================================================================

int main() {
    try {
        printSection("1. ENCAPSULATION");

        Customer customer(
            "CUS-001",
            "Atul Pandey",
            "atul@example.com"
        );

        std::cout << "Customer ID: " << customer.id() << "\n";
        std::cout << "Customer name: " << customer.name() << "\n";
        std::cout << "Customer email: " << customer.email() << "\n";

        customer.changeEmail("updated@example.com");

        std::cout << "Updated email: "
                  << customer.email()
                  << "\n";


        printSection("2. PRODUCT DOMAIN MODEL");

        auto laptop = std::make_shared<Product>(
            "LAPTOP-001",
            "Business Laptop",
            80000.0,
            10
        );

        auto mouse = std::make_shared<Product>(
            "MOUSE-001",
            "Wireless Mouse",
            1500.0,
            50
        );

        std::cout << laptop->name()
                  << " stock: "
                  << laptop->stock()
                  << "\n";

        laptop->restock(5);

        std::cout << "After restocking: "
                  << laptop->stock()
                  << "\n";


        printSection("3. ORDER CREATION AND COMPOSITION");

        /*
            Order contains OrderItem objects.
            OrderItem contains a shared reference to Product.

            This is composition:
                Order has OrderItems.
                OrderItems reference Products.

            The Order class also protects its state-transition rules.
        */

        auto order = std::make_shared<Order>(
            "ORD-9001",
            customer,
            800.0
        );

        order->addItem(laptop, 2);
        order->addItem(mouse, 3);

        std::cout << "Order subtotal: "
                  << money(order->subtotal())
                  << "\n";

        std::cout << "Remaining laptop stock: "
                  << laptop->stock()
                  << "\n";


        printSection("4. POLYMORPHIC PAYMENT PROVIDERS");

        std::vector<std::unique_ptr<PaymentProvider>> paymentProviders;

        paymentProviders.push_back(
            std::make_unique<CardPayment>()
        );

        paymentProviders.push_back(
            std::make_unique<WalletPayment>()
        );

        paymentProviders.push_back(
            std::make_unique<BankTransferPayment>()
        );

        for (const auto& provider : paymentProviders) {
            std::cout
                << provider->providerName()
                << " authorization for INR 5000: "
                << std::boolalpha
                << provider->authorize(5000.0)
                << "\n";
        }


        printSection("5. POLYMORPHIC SHIPPING PROVIDERS");

        std::vector<std::unique_ptr<ShippingProvider>> shippingProviders;

        shippingProviders.push_back(
            std::make_unique<StandardShipping>()
        );

        shippingProviders.push_back(
            std::make_unique<ExpressShipping>()
        );

        shippingProviders.push_back(
            std::make_unique<InternationalShipping>()
        );

        for (const auto& provider : shippingProviders) {
            const double cost =
                provider->calculateCost(
                    order->subtotal(),
                    order->weightKg(),
                    order->distanceKm()
                );

            std::cout
                << provider->providerName()
                << ": "
                << money(cost)
                << "\n";
        }


        printSection("6. POLYMORPHIC DISCOUNT POLICIES");

        std::vector<std::unique_ptr<DiscountPolicy>> policies;

        policies.push_back(
            std::make_unique<NoDiscount>()
        );

        policies.push_back(
            std::make_unique<PercentageDiscount>(10.0)
        );

        for (const auto& policy : policies) {
            std::cout
                << policy->name()
                << " discount: "
                << money(
                    policy->calculateDiscount(
                        order->subtotal()
                    )
                )
                << "\n";
        }


        printSection("7. EVENT-DRIVEN BEHAVIOR");

        auto eventBus = std::make_shared<EventBus>();

        eventBus->subscribe(
            "order.paid",
            [](const OrderEvent& event) {
                std::cout
                    << "[AUDIT] "
                    << event.orderId
                    << ": "
                    << event.message
                    << "\n";
            }
        );

        eventBus->subscribe(
            "order.shipped",
            [](const OrderEvent& event) {
                std::cout
                    << "[NOTIFICATION] "
                    << event.orderId
                    << ": "
                    << event.message
                    << "\n";
            }
        );


        printSection("8. DEPENDENCY INJECTION");

        auto repository =
            std::make_shared<InMemoryOrderRepository>();

        auto processor =
            OrderProcessor(
                createPaymentProvider("card"),
                createShippingProvider("express"),
                std::make_unique<PercentageDiscount>(10.0),
                repository,
                eventBus
            );

        std::cout
            << "Final amount before processing: "
            << money(processor.finalAmount(*order))
            << "\n";


        printSection("9. COMPLETE ORDER PROCESSING");

        processor.process(order);

        std::cout
            << "Final order status: "
            << statusName(order->status())
            << "\n";


        printSection("10. REPOSITORY LOOKUP");

        const auto storedOrder =
            repository->findById("ORD-9001");

        if (storedOrder) {
            std::cout
                << "Repository found order: "
                << storedOrder->id()
                << "\n";
        }


        printSection("11. REPORT GENERATION");

        std::unique_ptr<ReportGenerator> report =
            std::make_unique<TextReportGenerator>();

        std::cout << report->generate(*order);


        printSection("12. EDGE CASE: INVALID ORDER STATE");

        try {
            order->markPaid();
        }
        catch (const InvalidStateError& error) {
            std::cout
                << "Expected state error: "
                << error.what()
                << "\n";
        }


        printSection("13. EDGE CASE: INSUFFICIENT STOCK");

        try {
            order->addItem(laptop, 1000);
        }
        catch (const DomainError& error) {
            std::cout
                << "Expected stock error: "
                << error.what()
                << "\n";
        }


        printSection("14. EDGE CASE: INVALID CUSTOMER");

        try {
            Customer invalid(
                "CUS-X",
                "Invalid",
                "not-an-email"
            );

            (void)invalid;
        }
        catch (const ValidationError& error) {
            std::cout
                << "Expected validation error: "
                << error.what()
                << "\n";
        }


        printSection("15. PERFORMANCE EXAMPLE");

        /*
            unordered_map lookup is average O(1).
            vector search is O(n).

            The benchmark demonstrates why data-structure selection can matter
            more than small object-oriented implementation details.
        */

        constexpr int itemCount = 100000;

        std::vector<int> values;
        values.reserve(itemCount);

        std::unordered_map<int, bool> lookup;

        for (int i = 0; i < itemCount; ++i) {
            values.push_back(i);
            lookup[i] = true;
        }

        const auto vectorStart =
            std::chrono::high_resolution_clock::now();

        volatile bool vectorFound =
            std::find(
                values.begin(),
                values.end(),
                itemCount - 1
            ) != values.end();

        const auto vectorEnd =
            std::chrono::high_resolution_clock::now();

        const auto mapStart =
            std::chrono::high_resolution_clock::now();

        volatile bool mapFound =
            lookup.find(itemCount - 1) != lookup.end();

        const auto mapEnd =
            std::chrono::high_resolution_clock::now();

        const auto vectorTime =
            std::chrono::duration_cast<
                std::chrono::nanoseconds
            >(vectorEnd - vectorStart).count();

        const auto mapTime =
            std::chrono::duration_cast<
                std::chrono::nanoseconds
            >(mapEnd - mapStart).count();

        std::cout
            << "Vector found: "
            << vectorFound
            << ", time: "
            << vectorTime
            << " ns\n";

        std::cout
            << "Hash map found: "
            << mapFound
            << ", time: "
            << mapTime
            << " ns\n";


        printSection("16. OOP PRINCIPLE CHECKS");

        require(
            order->status() == OrderStatus::Shipped,
            "Order should be shipped."
        );

        require(
            order->subtotal() > 0,
            "Order subtotal should be positive."
        );

        require(
            laptop->stock() >= 0,
            "Inventory cannot become negative."
        );

        require(
            repository->findById("ORD-9001") != nullptr,
            "Repository should contain the order."
        );

        require(
            CardPayment().providerName() == "Card",
            "Card provider should identify itself."
        );

        require(
            StandardShipping().providerName() == "Standard",
            "Standard shipping should identify itself."
        );


        printSection("17. ARCHITECTURAL INTERPRETATION");

        std::cout
            << "Encapsulation: domain classes protect state and enforce rules.\n"
            << "Inheritance: concrete providers specialize abstract contracts.\n"
            << "Polymorphism: OrderProcessor works with provider abstractions.\n"
            << "Abstraction: interfaces expose required behavior, not details.\n"
            << "Composition: Order is built from Customer and OrderItem objects.\n"
            << "Dependency injection: infrastructure is supplied to the processor.\n"
            << "Events: independent listeners react to domain events.\n"
            << "Factory: concrete provider creation is centralized.\n";


        printSection("18. COMPLETION");

        std::cout
            << "The complete OOP case study executed successfully.\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "\nFatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}

} // namespace oop_case_study
