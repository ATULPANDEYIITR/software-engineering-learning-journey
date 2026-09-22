#include <algorithm>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

/*
 * Clean Code C++ Case Study
 *
 * Scenario:
 * A small order-management system needs to validate customers, create orders,
 * calculate totals, process payments, update inventory, and publish events.
 *
 * The program evolves the design through:
 * - meaningful names
 * - small functions
 * - strong types
 * - RAII
 * - const-correctness
 * - separation of concerns
 * - dependency injection
 * - interfaces
 * - repository abstraction
 * - validation
 * - exception handling
 * - event-driven behavior
 * - algorithmic complexity
 * - performance-aware data structures
 *
 * Compile:
 *     g++ -std=c++17 -Wall -Wextra -pedantic clean_code.cpp -o clean_code
 */

namespace clean_code {

// ============================================================================
// 1. DOMAIN CONSTANTS
// ============================================================================

constexpr double TAX_RATE = 0.18;
constexpr int MINIMUM_ORDER_QUANTITY = 1;


// ============================================================================
// 2. STRONG DOMAIN TYPES
// ============================================================================

using ProductId = std::string;
using CustomerId = std::string;
using OrderId = std::string;
using EmailAddress = std::string;


enum class OrderStatus {
    Created,
    Paid,
    Shipped,
    Cancelled
};


std::string toString(OrderStatus status) {
    switch (status) {
        case OrderStatus::Created:
            return "created";
        case OrderStatus::Paid:
            return "paid";
        case OrderStatus::Shipped:
            return "shipped";
        case OrderStatus::Cancelled:
            return "cancelled";
    }

    throw std::logic_error("Unknown order status.");
}


// ============================================================================
// 3. VALIDATION FUNCTIONS
// ============================================================================

bool isBlank(const std::string& value) {
    return value.empty() ||
           std::all_of(
               value.begin(),
               value.end(),
               [](unsigned char character) {
                   return std::isspace(character) != 0;
               }
           );
}


bool isValidEmail(const EmailAddress& email) {
    const auto atPosition = email.find('@');

    if (atPosition == std::string::npos) {
        return false;
    }

    const auto dotPosition = email.find('.', atPosition + 1);

    return dotPosition != std::string::npos &&
           atPosition > 0 &&
           dotPosition + 1 < email.size();
}


void validatePositiveQuantity(int quantity) {
    if (quantity < MINIMUM_ORDER_QUANTITY) {
        throw std::invalid_argument(
            "Quantity must be greater than zero."
        );
    }
}


void validateMoney(double amount) {
    if (!std::isfinite(amount) || amount < 0.0) {
        throw std::invalid_argument(
            "Money amount must be finite and non-negative."
        );
    }
}


// ============================================================================
// 4. PRODUCT ENTITY
// ============================================================================

class Product {
public:
    Product(
        ProductId productId,
        std::string name,
        double unitPrice
    )
        : productId_(std::move(productId)),
          name_(std::move(name)),
          unitPrice_(unitPrice) {

        if (isBlank(productId_)) {
            throw std::invalid_argument("Product ID is required.");
        }

        if (isBlank(name_)) {
            throw std::invalid_argument("Product name is required.");
        }

        validateMoney(unitPrice_);
    }

    const ProductId& id() const noexcept {
        return productId_;
    }

    const std::string& name() const noexcept {
        return name_;
    }

    double unitPrice() const noexcept {
        return unitPrice_;
    }

private:
    ProductId productId_;
    std::string name_;
    double unitPrice_;
};


// ============================================================================
// 5. ORDER ITEM
// ============================================================================

class OrderItem {
public:
    OrderItem(
        std::shared_ptr<const Product> product,
        int quantity
    )
        : product_(std::move(product)),
          quantity_(quantity) {

        if (!product_) {
            throw std::invalid_argument(
                "Order item requires a product."
            );
        }

        validatePositiveQuantity(quantity_);
    }

    const Product& product() const noexcept {
        return *product_;
    }

    int quantity() const noexcept {
        return quantity_;
    }

    double total() const noexcept {
        return product_->unitPrice() *
               static_cast<double>(quantity_);
    }

private:
    std::shared_ptr<const Product> product_;
    int quantity_;
};


// ============================================================================
// 6. ORDER ENTITY
// ============================================================================

class Order {
public:
    Order(
        OrderId orderId,
        EmailAddress customerEmail
    )
        : orderId_(std::move(orderId)),
          customerEmail_(std::move(customerEmail)) {

        if (isBlank(orderId_)) {
            throw std::invalid_argument("Order ID is required.");
        }

        if (!isValidEmail(customerEmail_)) {
            throw std::invalid_argument(
                "Invalid customer email."
            );
        }
    }

    void addItem(
        const std::shared_ptr<const Product>& product,
        int quantity
    ) {
        if (status_ != OrderStatus::Created) {
            throw std::logic_error(
                "Items cannot be added after payment."
            );
        }

        items_.emplace_back(product, quantity);
    }

    double subtotal() const noexcept {
        double total = 0.0;

        for (const auto& item : items_) {
            total += item.total();
        }

        return total;
    }

    void markPaid() {
        if (status_ != OrderStatus::Created) {
            throw std::logic_error(
                "Only created orders can become paid."
            );
        }

        status_ = OrderStatus::Paid;
    }

    const OrderId& id() const noexcept {
        return orderId_;
    }

    const EmailAddress& customerEmail() const noexcept {
        return customerEmail_;
    }

    OrderStatus status() const noexcept {
        return status_;
    }

    bool isEmpty() const noexcept {
        return items_.empty();
    }

    const std::vector<OrderItem>& items() const noexcept {
        return items_;
    }

private:
    OrderId orderId_;
    EmailAddress customerEmail_;
    std::vector<OrderItem> items_;
    OrderStatus status_ = OrderStatus::Created;
};


// ============================================================================
// 7. MONEY CALCULATIONS
// ============================================================================

struct OrderTotals {
    double subtotal;
    double tax;
    double total;
};


OrderTotals calculateOrderTotals(
    const Order& order,
    double taxRate
) {
    if (taxRate < 0.0 || taxRate > 1.0) {
        throw std::invalid_argument(
            "Tax rate must be between 0 and 1."
        );
    }

    const double subtotal = order.subtotal();
    const double tax = subtotal * taxRate;

    return {
        subtotal,
        tax,
        subtotal + tax
    };
}


// ============================================================================
// 8. PAYMENT ABSTRACTION
// ============================================================================

class PaymentGateway {
public:
    virtual ~PaymentGateway() = default;

    virtual std::string charge(
        double amount,
        const EmailAddress& customerEmail
    ) = 0;
};


class InMemoryPaymentGateway final : public PaymentGateway {
public:
    std::string charge(
        double amount,
        const EmailAddress& customerEmail
    ) override {

        validateMoney(amount);

        if (amount <= 0.0) {
            throw std::invalid_argument(
                "Payment amount must be positive."
            );
        }

        ++paymentCounter_;

        std::ostringstream paymentId;
        paymentId << "PAY-"
                  << std::setw(4)
                  << std::setfill('0')
                  << paymentCounter_;

        charges_.emplace_back(
            paymentId.str(),
            amount,
            customerEmail
        );

        return paymentId.str();
    }

private:
    struct Charge {
        std::string paymentId;
        double amount;
        EmailAddress customerEmail;
    };

    int paymentCounter_ = 0;
    std::vector<Charge> charges_;
};


// ============================================================================
// 9. RECEIPT ABSTRACTION
// ============================================================================

class ReceiptSender {
public:
    virtual ~ReceiptSender() = default;

    virtual void send(
        const EmailAddress& customerEmail,
        const std::string& paymentId
    ) = 0;
};


class ConsoleReceiptSender final : public ReceiptSender {
public:
    void send(
        const EmailAddress& customerEmail,
        const std::string& paymentId
    ) override {

        std::cout
            << "Receipt sent to "
            << customerEmail
            << " for payment "
            << paymentId
            << '\n';
    }
};


// ============================================================================
// 10. ORDER PAYMENT SERVICE
// ============================================================================

class OrderPaymentService {
public:
    OrderPaymentService(
        PaymentGateway& paymentGateway,
        ReceiptSender& receiptSender
    )
        : paymentGateway_(paymentGateway),
          receiptSender_(receiptSender) {}

    std::string payOrder(Order& order) {
        if (order.isEmpty()) {
            throw std::logic_error(
                "Cannot pay for an empty order."
            );
        }

        if (order.status() != OrderStatus::Created) {
            throw std::logic_error(
                "Order is not eligible for payment."
            );
        }

        const auto paymentId = paymentGateway_.charge(
            order.subtotal(),
            order.customerEmail()
        );

        order.markPaid();

        receiptSender_.send(
            order.customerEmail(),
            paymentId
        );

        return paymentId;
    }

private:
    PaymentGateway& paymentGateway_;
    ReceiptSender& receiptSender_;
};


// ============================================================================
// 11. INVENTORY SERVICE
// ============================================================================

class InventoryService {
public:
    void addStock(
        const ProductId& productId,
        int quantity
    ) {
        validatePositiveQuantity(quantity);
        stock_[productId] += quantity;
    }

    bool hasEnoughStock(
        const ProductId& productId,
        int requestedQuantity
    ) const {
        validatePositiveQuantity(requestedQuantity);

        const auto iterator = stock_.find(productId);

        if (iterator == stock_.end()) {
            return false;
        }

        return iterator->second >= requestedQuantity;
    }

    void reserveStock(
        const ProductId& productId,
        int quantity
    ) {
        validatePositiveQuantity(quantity);

        auto iterator = stock_.find(productId);

        if (
            iterator == stock_.end() ||
            iterator->second < quantity
        ) {
            throw std::runtime_error(
                "Insufficient inventory."
            );
        }

        iterator->second -= quantity;
    }

    int availableQuantity(
        const ProductId& productId
    ) const {
        const auto iterator = stock_.find(productId);

        if (iterator == stock_.end()) {
            return 0;
        }

        return iterator->second;
    }

private:
    std::unordered_map<ProductId, int> stock_;
};


// ============================================================================
// 12. EVENT SYSTEM
// ============================================================================

struct OrderPaidEvent {
    OrderId orderId;
    std::string paymentId;
};


class EventPublisher {
public:
    virtual ~EventPublisher() = default;

    virtual void publish(
        const OrderPaidEvent& event
    ) = 0;
};


class ConsoleEventPublisher final : public EventPublisher {
public:
    void publish(
        const OrderPaidEvent& event
    ) override {

        std::cout
            << "Event: order "
            << event.orderId
            << " paid with "
            << event.paymentId
            << '\n';
    }
};


// ============================================================================
// 13. ORDER APPLICATION SERVICE
// ============================================================================

class OrderApplicationService {
public:
    OrderApplicationService(
        OrderPaymentService& paymentService,
        InventoryService& inventoryService,
        EventPublisher& eventPublisher
    )
        : paymentService_(paymentService),
          inventoryService_(inventoryService),
          eventPublisher_(eventPublisher) {}

    std::string submitPayment(Order& order) {
        validateInventory(order);

        reserveInventory(order);

        try {
            const auto paymentId =
                paymentService_.payOrder(order);

            eventPublisher_.publish(
                OrderPaidEvent{
                    order.id(),
                    paymentId
                }
            );

            return paymentId;
        } catch (...) {
            /*
             * This example demonstrates a critical production concern:
             * inventory reservation and payment are separate operations.
             *
             * A real distributed system would need an explicit transaction
             * or compensation strategy. Here we restore the in-memory
             * inventory to keep the case study deterministic.
             */
            restoreInventory(order);
            throw;
        }
    }

private:
    void validateInventory(const Order& order) const {
        for (const auto& item : order.items()) {
            if (
                !inventoryService_.hasEnoughStock(
                    item.product().id(),
                    item.quantity()
                )
            ) {
                throw std::runtime_error(
                    "Insufficient stock for product: " +
                    item.product().id()
                );
            }
        }
    }

    void reserveInventory(const Order& order) {
        for (const auto& item : order.items()) {
            inventoryService_.reserveStock(
                item.product().id(),
                item.quantity()
            );
        }
    }

    void restoreInventory(const Order& order) {
        for (const auto& item : order.items()) {
            inventoryService_.addStock(
                item.product().id(),
                item.quantity()
            );
        }
    }

    OrderPaymentService& paymentService_;
    InventoryService& inventoryService_;
    EventPublisher& eventPublisher_;
};


// ============================================================================
// 14. TEST DOUBLE FOR THE RECEIPT SENDER
// ============================================================================

class RecordingReceiptSender final : public ReceiptSender {
public:
    void send(
        const EmailAddress& customerEmail,
        const std::string& paymentId
    ) override {
        messages_.emplace_back(
            customerEmail,
            paymentId
        );
    }

    std::size_t messageCount() const noexcept {
        return messages_.size();
    }

private:
    std::vector<std::pair<EmailAddress, std::string>> messages_;
};


// ============================================================================
// 15. SIMPLE ASSERTIONS
// ============================================================================

void assertTrue(
    bool condition,
    const std::string& message
) {
    if (!condition) {
        throw std::runtime_error(
            "Assertion failed: " + message
        );
    }
}


void assertEqual(
    double actual,
    double expected,
    const std::string& message
) {
    constexpr double EPSILON = 1e-9;

    if (std::abs(actual - expected) > EPSILON) {
        std::ostringstream error;

        error << "Assertion failed: "
              << message
              << " expected="
              << expected
              << " actual="
              << actual;

        throw std::runtime_error(error.str());
    }
}


template <typename ExceptionType, typename Function>
void assertThrows(
    Function operation,
    const std::string& message
) {
    bool didThrow = false;

    try {
        operation();
    } catch (const ExceptionType&) {
        didThrow = true;
    }

    if (!didThrow) {
        throw std::runtime_error(
            "Assertion failed: " + message
        );
    }
}


// ============================================================================
// 16. REPOSITORY ABSTRACTION
// ============================================================================

struct Customer {
    CustomerId id;
    EmailAddress email;
};


class CustomerRepository {
public:
    virtual ~CustomerRepository() = default;

    virtual void save(const Customer& customer) = 0;

    virtual std::optional<Customer> findById(
        const CustomerId& customerId
    ) const = 0;
};


class InMemoryCustomerRepository final
    : public CustomerRepository {

public:
    void save(const Customer& customer) override {
        customers_[customer.id] = customer;
    }

    std::optional<Customer> findById(
        const CustomerId& customerId
    ) const override {

        const auto iterator =
            customers_.find(customerId);

        if (iterator == customers_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }

private:
    std::unordered_map<CustomerId, Customer> customers_;
};


class CustomerService {
public:
    explicit CustomerService(
        CustomerRepository& repository
    )
        : repository_(repository) {}

    Customer registerCustomer(
        CustomerId customerId,
        EmailAddress email
    ) {
        if (isBlank(customerId)) {
            throw std::invalid_argument(
                "Customer ID is required."
            );
        }

        if (!isValidEmail(email)) {
            throw std::invalid_argument(
                "Valid email is required."
            );
        }

        if (repository_.findById(customerId)) {
            throw std::invalid_argument(
                "Customer already exists."
            );
        }

        Customer customer{
            std::move(customerId),
            std::move(email)
        };

        repository_.save(customer);

        return customer;
    }

private:
    CustomerRepository& repository_;
};


// ============================================================================
// 17. ALGORITHM AND DATA-STRUCTURE CASE STUDY
// ============================================================================

bool containsDuplicateUsingVector(
    const std::vector<int>& values
) {
    for (std::size_t first = 0;
         first < values.size();
         ++first) {

        for (std::size_t second = first + 1;
             second < values.size();
             ++second) {

            if (values[first] == values[second]) {
                return true;
            }
        }
    }

    return false;
}


bool containsDuplicateUsingHashSet(
    const std::vector<int>& values
) {
    std::unordered_set<int> seen;

    for (const int value : values) {
        if (!seen.insert(value).second) {
            return true;
        }
    }

    return false;
}


// The first implementation uses O(n^2) comparisons in the worst case.
// The hash-set implementation uses O(n) expected time and O(n) additional
// memory. The trade-off is memory consumption and hashing overhead.


// ============================================================================
// 18. PERFORMANCE MEASUREMENT
// ============================================================================

void demonstrateDuplicateSearchPerformance() {
    constexpr int VALUE_COUNT = 10000;

    std::vector<int> values;
    values.reserve(VALUE_COUNT);

    for (int value = 0; value < VALUE_COUNT; ++value) {
        values.push_back(value);
    }

    const auto hashSetStart =
        std::chrono::steady_clock::now();

    const bool hashSetResult =
        containsDuplicateUsingHashSet(values);

    const auto hashSetEnd =
        std::chrono::steady_clock::now();

    const auto hashSetDuration =
        std::chrono::duration_cast<
            std::chrono::microseconds
        >(hashSetEnd - hashSetStart);

    std::cout
        << "Hash-set duplicate result: "
        << std::boolalpha
        << hashSetResult
        << '\n';

    std::cout
        << "Hash-set search duration: "
        << hashSetDuration.count()
        << " microseconds\n";

    /*
     * The quadratic implementation is intentionally not benchmarked against
     * a 10,000-element unique vector because it would perform about 50
     * million comparisons. The implementation is retained as an algorithmic
     * comparison rather than an unnecessarily expensive runtime operation.
     */
}


// ============================================================================
// 19. BUSINESS SCENARIO CONSTRUCTION
// ============================================================================

std::shared_ptr<const Product> createLaptop() {
    return std::make_shared<const Product>(
        "LAP-001",
        "Developer Laptop",
        70000.0
    );
}


std::shared_ptr<const Product> createMonitor() {
    return std::make_shared<const Product>(
        "MON-001",
        "4K Monitor",
        25000.0
    );
}


Order createSampleOrder(
    const std::shared_ptr<const Product>& laptop,
    const std::shared_ptr<const Product>& monitor
) {
    Order order(
        "ORD-1001",
        "customer@example.com"
    );

    order.addItem(laptop, 1);
    order.addItem(monitor, 2);

    return order;
}


// ============================================================================
// 20. INTEGRATION-STYLE DEMONSTRATION
// ============================================================================

void runCaseStudy() {
    std::cout
        << "=== Clean Code C++ Case Study ===\n";

    const auto laptop = createLaptop();
    const auto monitor = createMonitor();

    Order order = createSampleOrder(
        laptop,
        monitor
    );

    const auto totals =
        calculateOrderTotals(
            order,
            TAX_RATE
        );

    std::cout
        << std::fixed
        << std::setprecision(2);

    std::cout
        << "Subtotal: ₹"
        << totals.subtotal
        << '\n';

    std::cout
        << "Tax: ₹"
        << totals.tax
        << '\n';

    std::cout
        << "Total: ₹"
        << totals.total
        << '\n';

    InventoryService inventoryService;

    inventoryService.addStock(
        laptop->id(),
        5
    );

    inventoryService.addStock(
        monitor->id(),
        10
    );

    InMemoryPaymentGateway paymentGateway;
    ConsoleReceiptSender receiptSender;

    OrderPaymentService paymentService(
        paymentGateway,
        receiptSender
    );

    ConsoleEventPublisher eventPublisher;

    OrderApplicationService applicationService(
        paymentService,
        inventoryService,
        eventPublisher
    );

    const std::string paymentId =
        applicationService.submitPayment(order);

    std::cout
        << "Payment ID: "
        << paymentId
        << '\n';

    std::cout
        << "Order status: "
        << toString(order.status())
        << '\n';

    std::cout
        << "Remaining laptop stock: "
        << inventoryService.availableQuantity(
            laptop->id()
        )
        << '\n';

    std::cout
        << "Remaining monitor stock: "
        << inventoryService.availableQuantity(
            monitor->id()
        )
        << '\n';
}


// ============================================================================
// 21. UNIT-STYLE TESTS
// ============================================================================

void runTests() {
    assertEqual(
        calculateOrderTotals(
            Order(
                "TEMP-001",
                "customer@example.com"
            ),
            TAX_RATE
        ).total,
        0.0,
        "Empty order should have zero total."
    );

    assertThrows<std::invalid_argument>(
        [] {
            Product(
                "",
                "Keyboard",
                100.0
            );
        },
        "Empty product ID should be rejected."
    );

    assertThrows<std::invalid_argument>(
        [] {
            Product(
                "P1",
                "Keyboard",
                -100.0
            );
        },
        "Negative price should be rejected."
    );

    assertThrows<std::invalid_argument>(
        [] {
            Order(
                "O1",
                "invalid-email"
            );
        },
        "Invalid email should be rejected."
    );

    const auto product =
        std::make_shared<const Product>(
            "P1",
            "Keyboard",
            1000.0
        );

    Order order(
        "O1",
        "customer@example.com"
    );

    order.addItem(product, 2);

    assertEqual(
        order.subtotal(),
        2000.0,
        "Order subtotal should be correct."
    );

    RecordingReceiptSender receiptSender;
    InMemoryPaymentGateway paymentGateway;

    OrderPaymentService paymentService(
        paymentGateway,
        receiptSender
    );

    const auto paymentId =
        paymentService.payOrder(order);

    assertTrue(
        paymentId == "PAY-0001",
        "Payment ID should be generated."
    );

    assertTrue(
        order.status() == OrderStatus::Paid,
        "Order should become paid."
    );

    assertTrue(
        receiptSender.messageCount() == 1,
        "Exactly one receipt should be sent."
    );

    assertThrows<std::logic_error>(
        [&] {
            paymentService.payOrder(order);
        },
        "A paid order cannot be paid twice."
    );

    CustomerRepository* repository =
        new InMemoryCustomerRepository();

    CustomerService customerService(*repository);

    const Customer customer =
        customerService.registerCustomer(
            "CUS-001",
            "customer@example.com"
        );

    assertTrue(
        customer.id == "CUS-001",
        "Customer should be registered."
    );

    assertThrows<std::invalid_argument>(
        [&] {
            customerService.registerCustomer(
                "CUS-001",
                "customer@example.com"
            );
        },
        "Duplicate customers should be rejected."
    );

    delete repository;

    std::vector<int> duplicateValues{
        1, 2, 3, 4, 3
    };

    assertTrue(
        containsDuplicateUsingVector(duplicateValues),
        "Vector duplicate detection should work."
    );

    assertTrue(
        containsDuplicateUsingHashSet(duplicateValues),
        "Hash-set duplicate detection should work."
    );
}


// ============================================================================
// 22. EDGE-CASE DEMONSTRATIONS
// ============================================================================

void demonstrateFailureConditions() {
    std::cout
        << "\n=== Expected Failure Conditions ===\n";

    try {
        Order invalidOrder(
            "O2",
            "not-an-email"
        );
    } catch (const std::exception& error) {
        std::cout
            << "Validation error: "
            << error.what()
            << '\n';
    }

    try {
        auto product =
            std::make_shared<const Product>(
                "P2",
                "Mouse",
                500.0
            );

        Order order(
            "O3",
            "customer@example.com"
        );

        order.addItem(
            product,
            0
        );
    } catch (const std::exception& error) {
        std::cout
            << "Quantity error: "
            << error.what()
            << '\n';
    }

    try {
        Order emptyOrder(
            "O4",
            "customer@example.com"
        );

        InMemoryPaymentGateway paymentGateway;
        ConsoleReceiptSender receiptSender;

        OrderPaymentService service(
            paymentGateway,
            receiptSender
        );

        service.payOrder(emptyOrder);
    } catch (const std::exception& error) {
        std::cout
            << "Payment error: "
            << error.what()
            << '\n';
    }
}


// ============================================================================
// 23. MAIN
// ============================================================================

} // namespace clean_code


int main() {
    try {
        clean_code::runTests();

        std::cout
            << "All tests passed.\n\n";

        clean_code::runCaseStudy();

        clean_code::demonstrateFailureConditions();

        clean_code::demonstrateDuplicateSearchPerformance();

        std::cout
            << "\nClean Code case study completed.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Program failed: "
            << error.what()
            << '\n';

        return 1;
    }
}
