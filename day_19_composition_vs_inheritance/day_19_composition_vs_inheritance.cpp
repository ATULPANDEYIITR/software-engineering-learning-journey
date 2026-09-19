/*
 * Composition vs Inheritance
 * ==========================
 *
 * Industry-style case study: an extensible order-processing platform.
 *
 * The system demonstrates:
 *   - inheritance
 *   - composition
 *   - dependency inversion
 *   - dependency injection
 *   - strategy objects
 *   - polymorphism
 *   - coupling
 *   - substitutability
 *   - validation
 *   - exception handling
 *   - test doubles
 *   - runtime configuration
 *   - complexity considerations
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic main.cpp -o composition_demo
 */

#include <algorithm>
#include <chrono>
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

// ============================================================================
// 1. DOMAIN TYPES
// ============================================================================

struct Customer {
    std::string name;
    std::string email;
};

struct Product {
    std::string name;
    double price;

    Product(std::string productName, double productPrice)
        : name(std::move(productName)), price(productPrice) {
        if (name.empty()) {
            throw std::invalid_argument("Product name cannot be empty.");
        }

        if (!std::isfinite(price) || price < 0.0) {
            throw std::invalid_argument("Product price must be non-negative.");
        }
    }
};

struct OrderItem {
    Product product;
    int quantity;

    OrderItem(Product productValue, int quantityValue)
        : product(std::move(productValue)), quantity(quantityValue) {
        if (quantity <= 0) {
            throw std::invalid_argument("Quantity must be positive.");
        }
    }

    double total() const {
        return product.price * quantity;
    }
};

// ============================================================================
// 2. COMPOSITION: ORDER HAS ORDER ITEMS
// ============================================================================

class Order {
private:
    Customer customer;
    std::vector<OrderItem> items;

public:
    explicit Order(Customer customerValue)
        : customer(std::move(customerValue)) {}

    void addItem(OrderItem item) {
        items.push_back(std::move(item));
    }

    double subtotal() const {
        double result = 0.0;

        for (const auto& item : items) {
            result += item.total();
        }

        return result;
    }

    const Customer& getCustomer() const {
        return customer;
    }

    std::size_t itemCount() const {
        return items.size();
    }
};

// ============================================================================
// 3. INHERITANCE: EMPLOYEE HIERARCHY
// ============================================================================

class Employee {
protected:
    std::string name;
    std::string employeeId;

public:
    Employee(std::string employeeName, std::string id)
        : name(std::move(employeeName)), employeeId(std::move(id)) {}

    virtual ~Employee() = default;

    virtual std::string role() const {
        return "Employee";
    }

    std::string describe() const {
        return name + " (" + employeeId + ") - " + role();
    }
};

class Developer : public Employee {
public:
    Developer(std::string name, std::string id)
        : Employee(std::move(name), std::move(id)) {}

    std::string role() const override {
        return "Developer";
    }
};

class Manager : public Employee {
public:
    Manager(std::string name, std::string id)
        : Employee(std::move(name), std::move(id)) {}

    std::string role() const override {
        return "Manager";
    }
};

// ============================================================================
// 4. POLYMORPHIC INTERFACES
// ============================================================================

class PaymentGateway {
public:
    virtual ~PaymentGateway() = default;

    virtual std::string charge(double amount) = 0;
};

class MockPaymentGateway final : public PaymentGateway {
private:
    std::vector<double> charges;

public:
    std::string charge(double amount) override {
        charges.push_back(amount);

        std::ostringstream output;
        output << "Mock payment authorized: $"
               << std::fixed << std::setprecision(2)
               << amount;

        return output.str();
    }

    const std::vector<double>& getCharges() const {
        return charges;
    }
};

class ConsolePaymentGateway final : public PaymentGateway {
public:
    std::string charge(double amount) override {
        std::ostringstream output;
        output << "Payment gateway charged $"
               << std::fixed << std::setprecision(2)
               << amount;

        return output.str();
    }
};

// ============================================================================
// 5. LOGGING ABSTRACTION
// ============================================================================

class Logger {
public:
    virtual ~Logger() = default;

    virtual void log(const std::string& message) = 0;
};

class ConsoleLogger final : public Logger {
public:
    void log(const std::string& message) override {
        std::cout << "[LOG] " << message << '\n';
    }
};

class MemoryLogger final : public Logger {
private:
    std::vector<std::string> messages;

public:
    void log(const std::string& message) override {
        messages.push_back(message);
    }

    const std::vector<std::string>& getMessages() const {
        return messages;
    }
};

// ============================================================================
// 6. INVENTORY COMPONENT
// ============================================================================

class Inventory {
private:
    std::unordered_map<std::string, int> stock;

public:
    void add(const std::string& product, int quantity) {
        if (quantity <= 0) {
            throw std::invalid_argument("Inventory quantity must be positive.");
        }

        stock[product] += quantity;
    }

    void reserve(const std::string& product, int quantity) {
        if (quantity <= 0) {
            throw std::invalid_argument("Reservation quantity must be positive.");
        }

        auto iterator = stock.find(product);

        if (iterator == stock.end() || iterator->second < quantity) {
            throw std::runtime_error("Insufficient inventory for " + product);
        }

        iterator->second -= quantity;
    }

    int available(const std::string& product) const {
        auto iterator = stock.find(product);

        if (iterator == stock.end()) {
            return 0;
        }

        return iterator->second;
    }
};

// ============================================================================
// 7. PRICING STRATEGY
// ============================================================================

class PricingStrategy {
public:
    virtual ~PricingStrategy() = default;

    virtual double calculate(double subtotal) const = 0;
};

class RegularPricing final : public PricingStrategy {
public:
    double calculate(double subtotal) const override {
        return subtotal;
    }
};

class PercentageDiscount final : public PricingStrategy {
private:
    double discountRate;

public:
    explicit PercentageDiscount(double rate)
        : discountRate(rate) {
        if (rate < 0.0 || rate > 1.0) {
            throw std::invalid_argument(
                "Discount rate must be between 0 and 1."
            );
        }
    }

    double calculate(double subtotal) const override {
        return subtotal * (1.0 - discountRate);
    }
};

// ============================================================================
// 8. TAX POLICY
// ============================================================================

class TaxPolicy {
public:
    virtual ~TaxPolicy() = default;

    virtual double calculate(double amount) const = 0;
};

class NoTax final : public TaxPolicy {
public:
    double calculate(double) const override {
        return 0.0;
    }
};

class FlatTax final : public TaxPolicy {
private:
    double rate;

public:
    explicit FlatTax(double taxRate)
        : rate(taxRate) {
        if (rate < 0.0 || rate > 1.0) {
            throw std::invalid_argument(
                "Tax rate must be between 0 and 1."
            );
        }
    }

    double calculate(double amount) const override {
        return amount * rate;
    }
};

// ============================================================================
// 9. SHIPPING POLICY
// ============================================================================

class ShippingPolicy {
public:
    virtual ~ShippingPolicy() = default;

    virtual double calculate(double amount) const = 0;
};

class FreeShipping final : public ShippingPolicy {
public:
    double calculate(double) const override {
        return 0.0;
    }
};

class FlatShipping final : public ShippingPolicy {
private:
    double fee;

public:
    explicit FlatShipping(double shippingFee)
        : fee(shippingFee) {
        if (fee < 0.0) {
            throw std::invalid_argument(
                "Shipping fee cannot be negative."
            );
        }
    }

    double calculate(double) const override {
        return fee;
    }
};

// ============================================================================
// 10. CHECKOUT COMPOSITION
// ============================================================================

class Checkout {
private:
    std::unique_ptr<PricingStrategy> pricing;
    std::unique_ptr<TaxPolicy> tax;
    std::unique_ptr<ShippingPolicy> shipping;

public:
    Checkout(
        std::unique_ptr<PricingStrategy> pricingStrategy,
        std::unique_ptr<TaxPolicy> taxPolicy,
        std::unique_ptr<ShippingPolicy> shippingPolicy
    )
        : pricing(std::move(pricingStrategy)),
          tax(std::move(taxPolicy)),
          shipping(std::move(shippingPolicy)) {}

    double total(double subtotal) const {
        if (subtotal < 0.0 || !std::isfinite(subtotal)) {
            throw std::invalid_argument(
                "Subtotal must be finite and non-negative."
            );
        }

        const double discounted = pricing->calculate(subtotal);
        const double taxAmount = tax->calculate(discounted);
        const double shippingAmount = shipping->calculate(discounted);

        return discounted + taxAmount + shippingAmount;
    }
};

// ============================================================================
// 11. ORDER PROCESSOR: COMPOSITION + DEPENDENCY INJECTION
// ============================================================================

class OrderProcessor {
private:
    Inventory& inventory;
    PaymentGateway& paymentGateway;
    Logger& logger;

public:
    OrderProcessor(
        Inventory& inventoryReference,
        PaymentGateway& paymentGatewayReference,
        Logger& loggerReference
    )
        : inventory(inventoryReference),
          paymentGateway(paymentGatewayReference),
          logger(loggerReference) {}

    std::string process(
        const std::string& product,
        int quantity,
        double unitPrice
    ) {
        if (product.empty()) {
            throw std::invalid_argument("Product name cannot be empty.");
        }

        if (quantity <= 0) {
            throw std::invalid_argument("Quantity must be positive.");
        }

        if (unitPrice < 0.0 || !std::isfinite(unitPrice)) {
            throw std::invalid_argument(
                "Unit price must be finite and non-negative."
            );
        }

        /*
         * The processor does not construct Inventory, PaymentGateway, or
         * Logger. Those collaborators are injected from outside.
         *
         * This lowers concrete coupling and makes testing easier.
         */
        inventory.reserve(product, quantity);

        const double amount = quantity * unitPrice;
        const std::string paymentResult = paymentGateway.charge(amount);

        logger.log(paymentResult);

        return paymentResult;
    }
};

// ============================================================================
// 12. TEST DOUBLE FOR INVENTORY
// ============================================================================

class TestInventory {
private:
    int quantity;

public:
    explicit TestInventory(int initialQuantity)
        : quantity(initialQuantity) {}

    void reserve(const std::string&, int requestedQuantity) {
        if (requestedQuantity <= 0) {
            throw std::invalid_argument("Quantity must be positive.");
        }

        if (requestedQuantity > quantity) {
            throw std::runtime_error("Test inventory is insufficient.");
        }

        quantity -= requestedQuantity;
    }

    int available() const {
        return quantity;
    }
};

// ============================================================================
// 13. BAD INHERITANCE EXAMPLE
// ============================================================================

class Bird {
public:
    virtual ~Bird() = default;

    virtual std::string move() const {
        return "Bird moves.";
    }
};

class FlyingBird : public Bird {
public:
    virtual std::string fly() const {
        return "Bird flies.";
    }
};

class Penguin : public FlyingBird {
public:
    /*
     * This method breaks the behavioral expectation created by FlyingBird.
     * The hierarchy therefore models the domain poorly.
     */
    std::string fly() const override {
        throw std::runtime_error("Penguins cannot fly.");
    }
};

// ============================================================================
// 14. COMPOSITION-BASED CAPABILITY MODEL
// ============================================================================

class FlightBehavior {
public:
    virtual ~FlightBehavior() = default;

    virtual std::string fly() const = 0;
};

class CanFly final : public FlightBehavior {
public:
    std::string fly() const override {
        return "Flying through the air.";
    }
};

class CannotFly final : public FlightBehavior {
public:
    std::string fly() const override {
        return "This animal cannot fly.";
    }
};

class ComposedBird {
private:
    std::string name;
    std::unique_ptr<FlightBehavior> flightBehavior;

public:
    ComposedBird(
        std::string birdName,
        std::unique_ptr<FlightBehavior> behavior
    )
        : name(std::move(birdName)),
          flightBehavior(std::move(behavior)) {}

    std::string fly() const {
        return name + ": " + flightBehavior->fly();
    }
};

// ============================================================================
// 15. IMMUTABLE VALUE TYPE
// ============================================================================

class Money {
private:
    const double amount;
    const std::string currency;

public:
    explicit Money(double value, std::string currencyCode = "USD")
        : amount(value), currency(std::move(currencyCode)) {
        if (!std::isfinite(amount)) {
            throw std::invalid_argument("Money must be finite.");
        }

        if (currency.size() != 3) {
            throw std::invalid_argument(
                "Currency must have three characters."
            );
        }
    }

    double getAmount() const {
        return amount;
    }

    const std::string& getCurrency() const {
        return currency;
    }

    Money add(const Money& other) const {
        if (currency != other.currency) {
            throw std::invalid_argument(
                "Cannot add different currencies."
            );
        }

        return Money(amount + other.amount, currency);
    }
};

// ============================================================================
// 16. MAINTAINABILITY METRICS
// ============================================================================

struct ComponentInfo {
    std::string name;
    std::vector<std::string> dependencies;
};

class DependencyRegistry {
private:
    std::vector<ComponentInfo> components;

public:
    void add(
        std::string name,
        std::vector<std::string> dependencies
    ) {
        components.push_back({
            std::move(name),
            std::move(dependencies)
        });
    }

    std::size_t afferentCoupling(
        const std::string& target
    ) const {
        std::size_t count = 0;

        for (const auto& component : components) {
            const auto found = std::find(
                component.dependencies.begin(),
                component.dependencies.end(),
                target
            );

            if (found != component.dependencies.end()) {
                ++count;
            }
        }

        return count;
    }
};

// ============================================================================
// 17. CASE STUDY: APPLICATION SERVICE
// ============================================================================

class Application {
private:
    Inventory inventory;
    ConsolePaymentGateway paymentGateway;
    ConsoleLogger logger;
    OrderProcessor processor;

public:
    Application()
        : processor(inventory, paymentGateway, logger) {}

    void seed() {
        inventory.add("SSD", 100);
        inventory.add("Keyboard", 50);
        inventory.add("Monitor", 25);
    }

    void purchase(
        const std::string& product,
        int quantity,
        double unitPrice
    ) {
        const std::string result =
            processor.process(product, quantity, unitPrice);

        std::cout << result << '\n';
        std::cout
            << "Remaining "
            << product
            << ": "
            << inventory.available(product)
            << '\n';
    }
};

// ============================================================================
// 18. COMPLEXITY DEMONSTRATION
// ============================================================================

double linearTotal(const std::vector<OrderItem>& items) {
    /*
     * O(n) time and O(1) additional space.
     *
     * Composition itself does not determine algorithmic complexity.
     * The algorithms implemented by the composed objects determine it.
     */
    double total = 0.0;

    for (const auto& item : items) {
        total += item.total();
    }

    return total;
}

// ============================================================================
// 19. SAFE EXECUTION HELPER
// ============================================================================

template <typename Function>
void runSafely(const std::string& title, Function function) {
    std::cout << "\n[" << title << "]\n";

    try {
        function();
    } catch (const std::exception& exception) {
        std::cout << "Handled error: "
                  << exception.what()
                  << '\n';
    }
}

// ============================================================================
// 20. MAIN CASE STUDY
// ============================================================================

int main() {
    std::cout << std::string(72, '=') << '\n';
    std::cout << "COMPOSITION VS INHERITANCE CASE STUDY\n";
    std::cout << std::string(72, '=') << '\n';

    // ------------------------------------------------------------------------
    // Inheritance
    // ------------------------------------------------------------------------

    Developer developer("Asha", "D001");
    Manager manager("Ravi", "M001");

    std::cout << "\nInheritance:\n";
    std::cout << developer.describe() << '\n';
    std::cout << manager.describe() << '\n';

    // ------------------------------------------------------------------------
    // Composition
    // ------------------------------------------------------------------------

    Customer customer{"Mira", "mira@example.com"};

    Order order(customer);
    order.addItem(OrderItem(Product("Laptop", 800.0), 2));
    order.addItem(OrderItem(Product("Mouse", 25.0), 1));

    std::cout << "\nComposed order:\n";
    std::cout << "Customer: "
              << order.getCustomer().name
              << '\n';

    std::cout << "Items: "
              << order.itemCount()
              << '\n';

    std::cout << "Subtotal: $"
              << std::fixed
              << std::setprecision(2)
              << order.subtotal()
              << '\n';

    // ------------------------------------------------------------------------
    // Strategy composition
    // ------------------------------------------------------------------------

    auto checkout = Checkout(
        std::make_unique<PercentageDiscount>(0.10),
        std::make_unique<FlatTax>(0.18),
        std::make_unique<FlatShipping>(50.0)
    );

    std::cout << "\nComposed checkout total: $"
              << checkout.total(order.subtotal())
              << '\n';

    // ------------------------------------------------------------------------
    // Dependency injection
    // ------------------------------------------------------------------------

    Inventory inventory;
    inventory.add("SSD", 10);

    MockPaymentGateway mockGateway;
    MemoryLogger memoryLogger;

    OrderProcessor processor(
        inventory,
        mockGateway,
        memoryLogger
    );

    std::cout << "\nDependency-injected processing:\n";

    const std::string result =
        processor.process("SSD", 2, 120.0);

    std::cout << result << '\n';
    std::cout << "Remaining SSD: "
              << inventory.available("SSD")
              << '\n';

    // ------------------------------------------------------------------------
    // Testability
    // ------------------------------------------------------------------------

    TestInventory testInventory(10);
    MockPaymentGateway testGateway;
    MemoryLogger testLogger;

    OrderProcessor testProcessor(
        reinterpret_cast<Inventory&>(testInventory),
        testGateway,
        testLogger
    );

    /*
     * The example above intentionally exposes a C++ type-system limitation:
     * unrelated concrete types cannot safely substitute for Inventory merely
     * because they have similar methods.
     *
     * The production design should therefore depend on an Inventory
     * abstraction rather than a concrete Inventory class when independent
     * implementations are required.
     *
     * We do not execute testProcessor because the reinterpret_cast would be
     * undefined behavior. This illustrates why abstractions should be designed
     * at dependency boundaries rather than retrofitted later.
     */

    std::cout << "\nC++ design observation:\n";
    std::cout
        << "Dependency injection is strongest when injected dependencies "
        << "are expressed through explicit interfaces.\n";

    // ------------------------------------------------------------------------
    // Correct polymorphic abstraction
    // ------------------------------------------------------------------------

    class InventoryPort {
    public:
        virtual ~InventoryPort() = default;

        virtual void reserve(
            const std::string& product,
            int quantity
        ) = 0;

        virtual int available(
            const std::string& product
        ) const = 0;
    };

    class InventoryAdapter final : public InventoryPort {
    private:
        Inventory& inventoryReference;

    public:
        explicit InventoryAdapter(Inventory& inventoryValue)
            : inventoryReference(inventoryValue) {}

        void reserve(
            const std::string& product,
            int quantity
        ) override {
            inventoryReference.reserve(product, quantity);
        }

        int available(
            const std::string& product
        ) const override {
            return inventoryReference.available(product);
        }
    };

    class PortBasedOrderProcessor {
    private:
        InventoryPort& inventoryPort;
        PaymentGateway& paymentGateway;
        Logger& logger;

    public:
        PortBasedOrderProcessor(
            InventoryPort& inventoryValue,
            PaymentGateway& paymentValue,
            Logger& loggerValue
        )
            : inventoryPort(inventoryValue),
              paymentGateway(paymentValue),
              logger(loggerValue) {}

        std::string process(
            const std::string& product,
            int quantity,
            double unitPrice
        ) {
            if (quantity <= 0) {
                throw std::invalid_argument(
                    "Quantity must be positive."
                );
            }

            if (unitPrice < 0.0) {
                throw std::invalid_argument(
                    "Unit price cannot be negative."
                );
            }

            inventoryPort.reserve(product, quantity);

            const std::string result =
                paymentGateway.charge(quantity * unitPrice);

            logger.log(result);

            return result;
        }
    };

    InventoryAdapter inventoryAdapter(inventory);

    PortBasedOrderProcessor robustProcessor(
        inventoryAdapter,
        mockGateway,
        memoryLogger
    );

    runSafely("Interface-based dependency injection", [&]() {
        std::cout
            << robustProcessor.process("SSD", 1, 120.0)
            << '\n';
    });

    // ------------------------------------------------------------------------
    // Composition-based capabilities
    // ------------------------------------------------------------------------

    std::cout << "\nCapability composition:\n";

    auto eagle = ComposedBird(
        "Eagle",
        std::make_unique<CanFly>()
    );

    auto penguin = ComposedBird(
        "Penguin",
        std::make_unique<CannotFly>()
    );

    std::cout << eagle.fly() << '\n';
    std::cout << penguin.fly() << '\n';

    // ------------------------------------------------------------------------
    // Bad inheritance
    // ------------------------------------------------------------------------

    runSafely("Broken inheritance hierarchy", []() {
        Penguin penguinObject;
        std::cout << penguinObject.fly() << '\n';
    });

    // ------------------------------------------------------------------------
    // Immutable value type
    // ------------------------------------------------------------------------

    Money first(10.0);
    Money second(15.0);
    Money combined = first.add(second);

    std::cout << "\nMoney value object: "
              << combined.getAmount()
              << ' '
              << combined.getCurrency()
              << '\n';

    // ------------------------------------------------------------------------
    // Edge cases
    // ------------------------------------------------------------------------

    runSafely("Invalid product", []() {
        Product invalid("", 10.0);
    });

    runSafely("Invalid quantity", []() {
        Product product("Keyboard", 50.0);
        OrderItem invalid(product, 0);
    });

    runSafely("Invalid discount", []() {
        PercentageDiscount invalid(1.5);
    });

    runSafely("Insufficient stock", [&]() {
        inventory.reserve("SSD", 1000);
    });

    // ------------------------------------------------------------------------
    // Complexity
    // ------------------------------------------------------------------------

    std::vector<OrderItem> items;

    for (int i = 0; i < 10'000; ++i) {
        items.emplace_back(
            Product("Item", 1.0),
            1
        );
    }

    const auto start =
        std::chrono::high_resolution_clock::now();

    const double total = linearTotal(items);

    const auto end =
        std::chrono::high_resolution_clock::now();

    const auto elapsed =
        std::chrono::duration_cast<std::chrono::microseconds>(
            end - start
        );

    std::cout << "\nComplexity demonstration:\n";
    std::cout << "Total: " << total << '\n';
    std::cout << "Linear traversal time: "
              << elapsed.count()
              << " microseconds\n";

    // ------------------------------------------------------------------------
    // Coupling registry
    // ------------------------------------------------------------------------

    DependencyRegistry registry;

    registry.add(
        "OrderProcessor",
        {
            "InventoryPort",
            "PaymentGateway",
            "Logger"
        }
    );

    registry.add(
        "Checkout",
        {
            "PricingStrategy",
            "TaxPolicy",
            "ShippingPolicy"
        }
    );

    registry.add(
        "AdminPanel",
        {
            "OrderProcessor"
        }
    );

    registry.add(
        "CustomerPortal",
        {
            "OrderProcessor"
        }
    );

    std::cout << "\nAfferent coupling of OrderProcessor: "
              << registry.afferentCoupling("OrderProcessor")
              << '\n';

    // ------------------------------------------------------------------------
    // Final architectural demonstration
    // ------------------------------------------------------------------------

    Application application;
    application.seed();

    std::cout << "\nIntegrated application:\n";

    runSafely("Successful application purchase", [&]() {
        application.purchase("Keyboard", 2, 75.0);
    });

    runSafely("Application failure", [&]() {
        application.purchase("Monitor", 1000, 200.0);
    });

    std::cout << "\nArchitectural principle demonstrated:\n";
    std::cout
        << "The order-processing workflow composes independent policies "
        << "and services rather than inheriting behavior from a large "
        << "base class.\n";

    std::cout
        << "Inheritance remains appropriate for stable subtype contracts, "
        << "while composition is useful for replaceable capabilities and "
        << "independent variation.\n";

    return 0;
}
