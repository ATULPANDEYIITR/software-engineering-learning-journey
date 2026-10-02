/*
 * SOLID Principles in C++17
 *
 * Technical case study:
 * A modular order-processing and fulfillment platform.
 *
 * The system demonstrates:
 *
 *   SRP - Single Responsibility Principle
 *   OCP - Open/Closed Principle
 *   LSP - Liskov Substitution Principle
 *   ISP - Interface Segregation Principle
 *   DIP - Dependency Inversion Principle
 *
 * The case study intentionally uses different C++ mechanisms from the
 * Python and JavaScript examples:
 *
 *   - abstract base classes for explicit contracts
 *   - value types for domain state
 *   - polymorphic services
 *   - capability-specific interfaces
 *   - dependency injection
 *   - strategy objects
 *   - ownership through references
 *   - exception-based failure handling
 *   - deterministic in-memory infrastructure
 *
 * Compile:
 *
 *   g++ -std=c++17 -Wall -Wextra -pedantic solid_case_study.cpp -o solid_case_study
 *
 * Run:
 *
 *   ./solid_case_study
 */

#include <algorithm>
#include <cassert>
#include <cmath>
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
// Shared domain model
// ============================================================================

double round_money(double value) {
    return std::round(value * 100.0) / 100.0;
}

struct Product {
    std::string id;
    std::string name;
    double price;

    Product(
        std::string product_id,
        std::string product_name,
        double product_price
    )
        : id(std::move(product_id)),
          name(std::move(product_name)),
          price(round_money(product_price)) {
        if (id.empty() || name.empty()) {
            throw std::invalid_argument(
                "Product ID and name are required."
            );
        }

        if (!std::isfinite(price) || price < 0.0) {
            throw std::invalid_argument(
                "Product price must be non-negative."
            );
        }
    }
};

struct OrderLine {
    Product product;
    int quantity;

    OrderLine(Product product_value, int quantity_value)
        : product(std::move(product_value)),
          quantity(quantity_value) {
        if (quantity <= 0) {
            throw std::invalid_argument(
                "Order quantity must be positive."
            );
        }
    }

    double subtotal() const {
        return round_money(product.price * quantity);
    }
};

struct Order {
    std::string id;
    std::string customer_email;
    std::vector<OrderLine> lines;
    std::string status = "NEW";

    double subtotal() const {
        double result = 0.0;

        for (const auto& line : lines) {
            result += line.subtotal();
        }

        return round_money(result);
    }
};

void heading(const std::string& title) {
    std::cout << "\n"
              << std::string(78, '=')
              << "\n"
              << title
              << "\n"
              << std::string(78, '=')
              << "\n";
}

// ============================================================================
// SRP - Separate responsibilities
// ============================================================================

/*
 * The order-processing system contains several reasons for change:
 *
 *   - price calculation rules
 *   - persistence format
 *   - notification delivery
 *
 * They are represented as separate abstractions rather than one large
 * OrderService class.
 */

class PriceCalculator {
public:
    double total(
        const Order& order,
        double tax_rate,
        double discount = 0.0
    ) const {
        if (tax_rate < 0.0 || tax_rate > 1.0) {
            throw std::invalid_argument(
                "Tax rate must be between zero and one."
            );
        }

        if (discount < 0.0 || discount > order.subtotal()) {
            throw std::invalid_argument(
                "Discount is outside the valid range."
            );
        }

        const double taxable = order.subtotal() - discount;
        const double tax = round_money(taxable * tax_rate);

        return round_money(taxable + tax);
    }
};

class OrderRepository {
public:
    virtual ~OrderRepository() = default;

    virtual void save(
        const Order& order,
        double total
    ) = 0;
};

class MemoryOrderRepository final : public OrderRepository {
private:
    struct Record {
        std::string customer_email;
        double total;
        std::string status;
    };

    std::unordered_map<std::string, Record> records_;

public:
    void save(
        const Order& order,
        double total
    ) override {
        records_[order.id] = {
            order.customer_email,
            total,
            order.status
        };
    }

    std::optional<Record> find(
        const std::string& order_id
    ) const {
        const auto iterator = records_.find(order_id);

        if (iterator == records_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }
};

class NotificationService {
public:
    virtual ~NotificationService() = default;

    virtual void send(
        const std::string& recipient,
        const std::string& subject,
        const std::string& message
    ) = 0;
};

class ConsoleNotificationService final
    : public NotificationService {
public:
    void send(
        const std::string& recipient,
        const std::string& subject,
        const std::string& message
    ) override {
        std::cout
            << "[NOTIFICATION] "
            << recipient
            << " | "
            << subject
            << " | "
            << message
            << "\n";
    }
};

class OrderApplicationService {
private:
    PriceCalculator& calculator_;
    OrderRepository& repository_;
    NotificationService& notifier_;

public:
    OrderApplicationService(
        PriceCalculator& calculator,
        OrderRepository& repository,
        NotificationService& notifier
    )
        : calculator_(calculator),
          repository_(repository),
          notifier_(notifier) {}

    double place(Order& order) {
        const double total = calculator_.total(
            order,
            0.18
        );

        order.status = "PAID";

        repository_.save(order, total);

        notifier_.send(
            order.customer_email,
            "Order confirmation",
            "Order " + order.id +
            " total=" + std::to_string(total)
        );

        return total;
    }
};

// ============================================================================
// OCP - Extensible discount policies
// ============================================================================

/*
 * DiscountStrategy is the extension point.
 *
 * The pricing engine does not inspect customer types, product quantities,
 * or campaign names. Those rules live in separate strategy objects.
 *
 * A new discount policy can therefore be introduced without editing the
 * pricing engine.
 */

class DiscountStrategy {
public:
    virtual ~DiscountStrategy() = default;

    virtual double calculate(
        const Order& order
    ) const = 0;
};

class NoDiscount final : public DiscountStrategy {
public:
    double calculate(
        const Order&
    ) const override {
        return 0.0;
    }
};

class PercentageDiscount final : public DiscountStrategy {
private:
    double rate_;

public:
    explicit PercentageDiscount(double rate)
        : rate_(rate) {
        if (rate < 0.0 || rate > 1.0) {
            throw std::invalid_argument(
                "Percentage discount must be between zero and one."
            );
        }
    }

    double calculate(
        const Order& order
    ) const override {
        return round_money(order.subtotal() * rate_);
    }
};

class BulkDiscount final : public DiscountStrategy {
private:
    int minimum_quantity_;
    double rate_;

public:
    BulkDiscount(
        int minimum_quantity,
        double rate
    )
        : minimum_quantity_(minimum_quantity),
          rate_(rate) {
        if (minimum_quantity <= 0) {
            throw std::invalid_argument(
                "Bulk threshold must be positive."
            );
        }

        if (rate < 0.0 || rate > 1.0) {
            throw std::invalid_argument(
                "Bulk discount rate is invalid."
            );
        }
    }

    double calculate(
        const Order& order
    ) const override {
        double discount = 0.0;

        for (const auto& line : order.lines) {
            if (line.quantity >= minimum_quantity_) {
                discount += line.subtotal() * rate_;
            }
        }

        return round_money(discount);
    }
};

class TierDiscount final : public DiscountStrategy {
private:
    double rate_;

public:
    explicit TierDiscount(
        const std::string& tier
    ) {
        if (tier == "standard") {
            rate_ = 0.0;
        } else if (tier == "silver") {
            rate_ = 0.05;
        } else if (tier == "gold") {
            rate_ = 0.10;
        } else if (tier == "platinum") {
            rate_ = 0.15;
        } else {
            throw std::invalid_argument(
                "Unknown customer tier."
            );
        }
    }

    double calculate(
        const Order& order
    ) const override {
        return round_money(order.subtotal() * rate_);
    }
};

class PricingEngine {
private:
    const DiscountStrategy& discount_strategy_;
    const PriceCalculator& calculator_;

public:
    PricingEngine(
        const DiscountStrategy& discount_strategy,
        const PriceCalculator& calculator
    )
        : discount_strategy_(discount_strategy),
          calculator_(calculator) {}

    double calculate(
        const Order& order
    ) const {
        const double discount =
            discount_strategy_.calculate(order);

        return calculator_.total(
            order,
            0.18,
            discount
        );
    }
};

// ============================================================================
// LSP - Payment capability hierarchy
// ============================================================================

/*
 * LSP is enforced here by not claiming that every PaymentMethod is
 * refundable.
 *
 * PaymentMethod guarantees charge().
 * RefundablePaymentMethod adds a stronger contract.
 *
 * A payment provider that cannot support refunds is valid as a PaymentMethod
 * but is not incorrectly modeled as RefundablePaymentMethod.
 */

class PaymentMethod {
public:
    virtual ~PaymentMethod() = default;

    virtual std::string charge(
        double amount
    ) = 0;
};

class RefundablePaymentMethod
    : public PaymentMethod {
public:
    virtual void refund(
        const std::string& transaction_id,
        double amount
    ) = 0;
};

class CardPayment final
    : public RefundablePaymentMethod {
private:
    std::unordered_map<std::string, double> transactions_;
    int sequence_ = 0;

public:
    std::string charge(
        double amount
    ) override {
        if (amount <= 0.0) {
            throw std::invalid_argument(
                "Charge must be positive."
            );
        }

        ++sequence_;

        const std::string id =
            "CARD-" + std::to_string(sequence_);

        transactions_[id] = round_money(amount);

        return id;
    }

    void refund(
        const std::string& transaction_id,
        double amount
    ) override {
        const auto iterator =
            transactions_.find(transaction_id);

        if (iterator == transactions_.end()) {
            throw std::runtime_error(
                "Unknown card transaction."
            );
        }

        if (
            amount <= 0.0 ||
            amount > iterator->second
        ) {
            throw std::invalid_argument(
                "Refund exceeds transaction."
            );
        }

        iterator->second =
            round_money(iterator->second - amount);
    }

    double remainingCharge(
        const std::string& transaction_id
    ) const {
        const auto iterator =
            transactions_.find(transaction_id);

        if (iterator == transactions_.end()) {
            throw std::runtime_error(
                "Unknown transaction."
            );
        }

        return iterator->second;
    }
};

class GiftCardPayment final
    : public PaymentMethod {
private:
    double balance_;

public:
    explicit GiftCardPayment(
        double balance
    )
        : balance_(round_money(balance)) {
        if (balance < 0.0) {
            throw std::invalid_argument(
                "Gift-card balance cannot be negative."
            );
        }
    }

    std::string charge(
        double amount
    ) override {
        if (amount <= 0.0) {
            throw std::invalid_argument(
                "Charge must be positive."
            );
        }

        if (amount > balance_) {
            throw std::runtime_error(
                "Insufficient gift-card balance."
            );
        }

        balance_ =
            round_money(balance_ - amount);

        return "GIFT-CHARGE";
    }

    double balance() const {
        return balance_;
    }
};

std::string processPayment(
    PaymentMethod& payment,
    double amount
) {
    return payment.charge(amount);
}

void processRefund(
    RefundablePaymentMethod& payment,
    const std::string& transaction_id,
    double amount
) {
    payment.refund(transaction_id, amount);
}

// ============================================================================
// ISP - Capability-specific interfaces
// ============================================================================

/*
 * A single large Repository interface would force read-only clients to
 * depend on write and audit operations.
 *
 * The following interfaces model separate capabilities.
 */

struct OrderSummary {
    std::string order_id;
    std::string customer_email;
    double total;
};

class OrderReader {
public:
    virtual ~OrderReader() = default;

    virtual std::optional<OrderSummary> read(
        const std::string& order_id
    ) const = 0;
};

class OrderWriter {
public:
    virtual ~OrderWriter() = default;

    virtual void write(
        const OrderSummary& summary
    ) = 0;
};

class OrderAuditor {
public:
    virtual ~OrderAuditor() = default;

    virtual void audit(
        const std::string& order_id,
        const std::string& event
    ) = 0;
};

class ModularOrderStore final
    : public OrderReader,
      public OrderWriter,
      public OrderAuditor {
private:
    std::unordered_map<
        std::string,
        OrderSummary
    > records_;

    std::vector<std::string> audit_events_;

public:
    std::optional<OrderSummary> read(
        const std::string& order_id
    ) const override {
        const auto iterator =
            records_.find(order_id);

        if (iterator == records_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }

    void write(
        const OrderSummary& summary
    ) override {
        records_[summary.order_id] = summary;
    }

    void audit(
        const std::string& order_id,
        const std::string& event
    ) override {
        audit_events_.push_back(
            order_id + ":" + event
        );
    }

    const std::vector<std::string>& auditEvents() const {
        return audit_events_;
    }
};

class ReportingService {
private:
    const OrderReader& reader_;

public:
    explicit ReportingService(
        const OrderReader& reader
    )
        : reader_(reader) {}

    std::string render(
        const std::string& order_id
    ) const {
        const auto result =
            reader_.read(order_id);

        if (!result.has_value()) {
            throw std::runtime_error(
                "Order was not found."
            );
        }

        std::ostringstream output;

        output << "Order "
               << result->order_id
               << " | customer="
               << result->customer_email
               << " | total="
               << std::fixed
               << std::setprecision(2)
               << result->total;

        return output.str();
    }
};

class PersistenceService {
private:
    OrderWriter& writer_;
    OrderAuditor& auditor_;

public:
    PersistenceService(
        OrderWriter& writer,
        OrderAuditor& auditor
    )
        : writer_(writer),
          auditor_(auditor) {}

    void save(
        const OrderSummary& summary
    ) {
        writer_.write(summary);

        auditor_.audit(
            summary.order_id,
            "ORDER_SAVED"
        );
    }
};

// ============================================================================
// DIP - High-level checkout workflow
// ============================================================================

/*
 * The checkout policy depends only on abstractions.
 *
 * No concrete payment vendor, database, inventory engine, or message broker
 * is constructed inside this class.
 *
 * This also makes deterministic testing possible because each dependency
 * can be replaced with a small in-memory implementation.
 */

class InventoryGateway {
public:
    virtual ~InventoryGateway() = default;

    virtual void reserve(
        const std::string& product_id,
        int quantity
    ) = 0;
};

class PaymentGateway {
public:
    virtual ~PaymentGateway() = default;

    virtual std::string charge(
        double amount
    ) = 0;
};

class NotificationGateway {
public:
    virtual ~NotificationGateway() = default;

    virtual void notify(
        const std::string& email,
        const std::string& subject,
        const std::string& message
    ) = 0;
};

class MemoryInventory final
    : public InventoryGateway {
private:
    std::unordered_map<std::string, int> stock_;

public:
    explicit MemoryInventory(
        std::unordered_map<std::string, int> stock
    )
        : stock_(std::move(stock)) {}

    void reserve(
        const std::string& product_id,
        int quantity
    ) override {
        auto iterator =
            stock_.find(product_id);

        const int available =
            iterator == stock_.end()
                ? 0
                : iterator->second;

        if (quantity > available) {
            throw std::runtime_error(
                "Insufficient inventory for " +
                product_id
            );
        }

        iterator->second -= quantity;
    }

    int available(
        const std::string& product_id
    ) const {
        const auto iterator =
            stock_.find(product_id);

        return iterator == stock_.end()
            ? 0
            : iterator->second;
    }
};

class FakePaymentGateway final
    : public PaymentGateway {
private:
    bool decline_;
    int sequence_ = 0;
    std::vector<double> charges_;

public:
    explicit FakePaymentGateway(
        bool decline = false
    )
        : decline_(decline) {}

    std::string charge(
        double amount
    ) override {
        if (decline_) {
            throw std::runtime_error(
                "Payment was declined."
            );
        }

        if (amount <= 0.0) {
            throw std::invalid_argument(
                "Payment amount must be positive."
            );
        }

        ++sequence_;

        charges_.push_back(
            round_money(amount)
        );

        return "PAY-" +
               std::to_string(sequence_);
    }

    const std::vector<double>& charges() const {
        return charges_;
    }
};

class ConsoleNotificationGateway final
    : public NotificationGateway {
public:
    void notify(
        const std::string& email,
        const std::string& subject,
        const std::string& message
    ) override {
        std::cout
            << "[ASYNC-CAPABLE NOTIFICATION] "
            << email
            << " | "
            << subject
            << " | "
            << message
            << "\n";
    }
};

class CheckoutApplication {
private:
    InventoryGateway& inventory_;
    PaymentGateway& payment_;
    NotificationGateway& notification_;
    const PricingEngine& pricing_;

public:
    CheckoutApplication(
        InventoryGateway& inventory,
        PaymentGateway& payment,
        NotificationGateway& notification,
        const PricingEngine& pricing
    )
        : inventory_(inventory),
          payment_(payment),
          notification_(notification),
          pricing_(pricing) {}

    std::string place(
        Order& order
    ) {
        const double total =
            pricing_.calculate(order);

        /*
         * Inventory reservation and payment are separate external operations.
         * If a later operation fails, a real distributed system needs a
         * compensation strategy or transactional workflow. A C++ exception
         * alone cannot undo an external payment or warehouse reservation.
         */
        for (const auto& line : order.lines) {
            inventory_.reserve(
                line.product.id,
                line.quantity
            );
        }

        const std::string transaction =
            payment_.charge(total);

        order.status = "PAID";

        notification_.notify(
            order.customer_email,
            "Order paid",
            "Order " + order.id +
            " transaction=" + transaction
        );

        return transaction;
    }
};

// ============================================================================
// Event processing demonstrates compositional boundaries
// ============================================================================

struct OrderPaidEvent {
    std::string order_id;
    std::string transaction_id;
};

class EventHandler {
public:
    virtual ~EventHandler() = default;

    virtual void handle(
        const OrderPaidEvent& event
    ) = 0;
};

class AuditEventHandler final
    : public EventHandler {
private:
    OrderAuditor& auditor_;

public:
    explicit AuditEventHandler(
        OrderAuditor& auditor
    )
        : auditor_(auditor) {}

    void handle(
        const OrderPaidEvent& event
    ) override {
        auditor_.audit(
            event.order_id,
            "ORDER_PAID:" + event.transaction_id
        );
    }
};

class EventDispatcher {
private:
    std::vector<std::unique_ptr<EventHandler>>
        handlers_;

public:
    void addHandler(
        std::unique_ptr<EventHandler> handler
    ) {
        handlers_.push_back(std::move(handler));
    }

    void dispatch(
        const OrderPaidEvent& event
    ) {
        for (const auto& handler : handlers_) {
            handler->handle(event);
        }
    }
};

// ============================================================================
// Demonstrations
// ============================================================================

void demonstrateSRP() {
    heading("SRP: Separate calculation, persistence, and notification");

    Product product(
        "SRP-1",
        "Mechanical Keyboard",
        80.0
    );

    Order order{
        "ORD-SRP",
        "srp@example.com",
        {OrderLine(product, 2)}
    };

    PriceCalculator calculator;
    MemoryOrderRepository repository;
    ConsoleNotificationService notifier;

    OrderApplicationService application(
        calculator,
        repository,
        notifier
    );

    const double total =
        application.place(order);

    std::cout
        << "Calculated total: "
        << std::fixed
        << std::setprecision(2)
        << total
        << "\n";

    const auto record =
        repository.find(order.id);

    assert(record.has_value());
    assert(record->status == "PAID");
}

void demonstrateOCP() {
    heading("OCP: New discount strategies without changing the engine");

    Product product(
        "OCP-1",
        "USB-C Dock",
        150.0
    );

    Order order{
        "ORD-OCP",
        "ocp@example.com",
        {OrderLine(product, 1)}
    };

    PriceCalculator calculator;

    NoDiscount no_discount;
    PercentageDiscount percentage(0.10);
    TierDiscount gold("gold");

    PricingEngine standard(
        no_discount,
        calculator
    );

    PricingEngine percentage_engine(
        percentage,
        calculator
    );

    PricingEngine gold_engine(
        gold,
        calculator
    );

    std::cout
        << "No discount: "
        << standard.calculate(order)
        << "\n";

    std::cout
        << "Percentage discount: "
        << percentage_engine.calculate(order)
        << "\n";

    std::cout
        << "Gold discount: "
        << gold_engine.calculate(order)
        << "\n";
}

void demonstrateLSP() {
    heading("LSP: Valid substitution preserves the contract");

    CardPayment card;
    GiftCardPayment gift_card(100.0);

    PaymentMethod& card_reference = card;
    PaymentMethod& gift_reference = gift_card;

    const std::string card_transaction =
        processPayment(card_reference, 40.0);

    const std::string gift_transaction =
        processPayment(gift_reference, 25.0);

    std::cout
        << "Card transaction: "
        << card_transaction
        << "\n";

    std::cout
        << "Gift-card transaction: "
        << gift_transaction
        << "\n";

    /*
     * Only the refundable abstraction is passed to processRefund().
     * GiftCardPayment is deliberately not treated as refundable.
     */
    processRefund(
        card,
        card_transaction,
        10.0
    );

    assert(
        card.remainingCharge(card_transaction)
        == 30.0
    );

    std::cout
        << "Remaining card transaction amount: "
        << card.remainingCharge(card_transaction)
        << "\n";

    std::cout
        << "Remaining gift-card balance: "
        << gift_card.balance()
        << "\n";
}

void demonstrateISP() {
    heading("ISP: Clients consume narrow capability interfaces");

    ModularOrderStore store;

    PersistenceService persistence(
        store,
        store
    );

    persistence.save({
        "ORD-ISP",
        "isp@example.com",
        199.95
    });

    /*
     * ReportingService receives only OrderReader.
     * It does not depend on write or audit operations.
     */
    ReportingService reporting(store);

    std::cout
        << reporting.render("ORD-ISP")
        << "\n";

    assert(
        store.auditEvents().size() == 1
    );
}

void demonstrateDIP() {
    heading("DIP: High-level checkout with injected infrastructure");

    Product product(
        "DIP-1",
        "Security Token",
        59.0
    );

    Order order{
        "ORD-DIP",
        "dip@example.com",
        {OrderLine(product, 2)}
    };

    PriceCalculator calculator;
    TierDiscount silver("silver");

    PricingEngine pricing(
        silver,
        calculator
    );

    MemoryInventory inventory({
        {"DIP-1", 10}
    });

    FakePaymentGateway payment;
    ConsoleNotificationGateway notification;

    CheckoutApplication application(
        inventory,
        payment,
        notification,
        pricing
    );

    const std::string transaction =
        application.place(order);

    std::cout
        << "Transaction: "
        << transaction
        << "\n";

    std::cout
        << "Order status: "
        << order.status
        << "\n";

    std::cout
        << "Remaining inventory: "
        << inventory.available("DIP-1")
        << "\n";

    assert(order.status == "PAID");
    assert(inventory.available("DIP-1") == 8);
}

void demonstrateEventComposition() {
    heading("SOLID composition with domain events");

    ModularOrderStore store;

    EventDispatcher dispatcher;

    dispatcher.addHandler(
        std::make_unique<AuditEventHandler>(
            store
        )
    );

    dispatcher.dispatch({
        "ORD-EVENT",
        "PAY-0001"
    });

    assert(
        store.auditEvents().size() == 1
    );

    std::cout
        << "Recorded event: "
        << store.auditEvents().front()
        << "\n";
}

// ============================================================================
// Failure-path tests
// ============================================================================

void runTests() {
    heading("Automated verification");

    Product product(
        "TEST",
        "Test Product",
        100.0
    );

    Order order{
        "TEST-ORDER",
        "test@example.com",
        {OrderLine(product, 2)}
    };

    PriceCalculator calculator;

    assert(
        calculator.total(order, 0.10)
        == 220.0
    );

    PercentageDiscount discount(0.10);

    assert(
        discount.calculate(order)
        == 20.0
    );

    CardPayment card;

    const std::string transaction =
        processPayment(card, 50.0);

    processRefund(
        card,
        transaction,
        10.0
    );

    assert(
        card.remainingCharge(transaction)
        == 40.0
    );

    ModularOrderStore store;

    store.write({
        "READ-1",
        "reader@example.com",
        75.0
    });

    ReportingService reporting(store);

    const std::string report =
        reporting.render("READ-1");

    assert(
        report.find("75.00")
        != std::string::npos
    );

    MemoryInventory inventory({
        {"TEST", 3}
    });

    FakePaymentGateway payment;

    NoDiscount no_discount;

    PricingEngine pricing(
        no_discount,
        calculator
    );

    ConsoleNotificationGateway notification;

    CheckoutApplication checkout(
        inventory,
        payment,
        notification,
        pricing
    );

    Order checkout_order{
        "DIP-TEST",
        "checkout@example.com",
        {OrderLine(product, 2)}
    };

    const std::string checkout_transaction =
        checkout.place(checkout_order);

    assert(
        checkout_transaction == "PAY-1"
    );

    assert(
        inventory.available("TEST") == 1
    );

    bool invalid_quantity_rejected = false;

    try {
        OrderLine invalid_line(
            product,
            0
        );
    } catch (const std::invalid_argument&) {
        invalid_quantity_rejected = true;
    }

    assert(invalid_quantity_rejected);

    bool invalid_discount_rejected = false;

    try {
        calculator.total(
            order,
            0.18,
            500.0
        );
    } catch (const std::invalid_argument&) {
        invalid_discount_rejected = true;
    }

    assert(invalid_discount_rejected);

    bool payment_failure_rejected = false;

    try {
        FakePaymentGateway declining_payment(true);

        CheckoutApplication failing_checkout(
            inventory,
            declining_payment,
            notification,
            pricing
        );

        Order failing_order{
            "FAIL-1",
            "failure@example.com",
            {OrderLine(product, 1)}
        };

        failing_checkout.place(failing_order);
    } catch (const std::runtime_error&) {
        payment_failure_rejected = true;
    }

    assert(payment_failure_rejected);

    std::cout
        << "All SOLID design tests passed.\n";
}

// ============================================================================
// Main
// ============================================================================

int main() {
    try {
        heading(
            "SOLID PRINCIPLES: C++17 ORDER PLATFORM CASE STUDY"
        );

        demonstrateSRP();
        demonstrateOCP();
        demonstrateLSP();
        demonstrateISP();
        demonstrateDIP();
        demonstrateEventComposition();

        runTests();

        heading("Program completed successfully");
        return 0;
    } catch (const std::exception& exception) {
        std::cerr
            << "Application failure: "
            << exception.what()
            << "\n";

        return 1;
    }
}
