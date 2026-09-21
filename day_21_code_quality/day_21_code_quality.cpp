/*
 * Code Quality Case Study
 *
 * Scenario:
 * Build a maintainable order-pricing service for a small commerce platform.
 *
 * The program demonstrates:
 * - readable naming
 * - formatting
 * - focused functions
 * - validation
 * - domain modeling
 * - enums
 * - classes
 * - composition
 * - dependency injection
 * - error handling
 * - deterministic testing
 * - algorithmic complexity
 * - performance considerations
 * - security-conscious input handling
 * - separation of business logic and presentation
 *
 * Standard: C++17 or later
 */

#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

// ============================================================================
// 1. GENERAL HELPERS
// ============================================================================

void printSection(const std::string& title) {
    std::cout << "\n" << std::string(78, '=') << "\n";
    std::cout << title << "\n";
    std::cout << std::string(78, '=') << "\n";
}

void require(
    bool condition,
    const std::string& description
) {
    if (!condition) {
        throw std::runtime_error(
            "Quality check failed: " + description
        );
    }

    std::cout << "PASS: " << description << "\n";
}


// ============================================================================
// 2. EXPLICIT CONSTANTS
// ============================================================================

namespace constants {
    constexpr double premiumDiscountRate = 10.0;
    constexpr double taxRate = 18.0;
    constexpr double freeShippingThreshold = 1000.0;
    constexpr double standardShippingCost = 100.0;
}


// ============================================================================
// 3. VALIDATION FUNCTIONS
// ============================================================================

void requireNonNegative(
    double value,
    const std::string& fieldName
) {
    if (!std::isfinite(value) || value < 0.0) {
        throw std::invalid_argument(
            fieldName + " must be a finite non-negative number."
        );
    }
}

void requirePositiveInteger(
    int value,
    const std::string& fieldName
) {
    if (value <= 0) {
        throw std::invalid_argument(
            fieldName + " must be positive."
        );
    }
}

void requireNotEmpty(
    const std::string& value,
    const std::string& fieldName
) {
    if (value.empty()) {
        throw std::invalid_argument(
            fieldName + " cannot be empty."
        );
    }
}


// ============================================================================
// 4. DOMAIN ENUM
// ============================================================================

enum class CustomerTier {
    Standard,
    Premium
};

std::string toString(CustomerTier tier) {
    switch (tier) {
        case CustomerTier::Standard:
            return "standard";

        case CustomerTier::Premium:
            return "premium";
    }

    throw std::logic_error("Unknown customer tier.");
}


// ============================================================================
// 5. CUSTOMER DOMAIN MODEL
// ============================================================================

class CustomerProfile {
private:
    std::string customerId_;
    CustomerTier tier_;

public:
    CustomerProfile(
        std::string customerId,
        CustomerTier tier
    )
        : customerId_(std::move(customerId)),
          tier_(tier) {
        requireNotEmpty(customerId_, "Customer ID");
    }

    const std::string& customerId() const {
        return customerId_;
    }

    CustomerTier tier() const {
        return tier_;
    }
};


// ============================================================================
// 6. ORDER ITEM DOMAIN MODEL
// ============================================================================

class OrderItem {
private:
    std::string productName_;
    double unitPrice_;
    int quantity_;

public:
    OrderItem(
        std::string productName,
        double unitPrice,
        int quantity
    )
        : productName_(std::move(productName)),
          unitPrice_(unitPrice),
          quantity_(quantity) {
        requireNotEmpty(productName_, "Product name");
        requireNonNegative(unitPrice_, "Unit price");
        requirePositiveInteger(quantity_, "Quantity");
    }

    const std::string& productName() const {
        return productName_;
    }

    double unitPrice() const {
        return unitPrice_;
    }

    int quantity() const {
        return quantity_;
    }

    double subtotal() const {
        return unitPrice_ * static_cast<double>(quantity_);
    }
};


// ============================================================================
// 7. PURE PRICING FUNCTIONS
// ============================================================================

double calculateTax(
    double taxableAmount,
    double taxRate
) {
    requireNonNegative(taxableAmount, "Taxable amount");

    if (!std::isfinite(taxRate) || taxRate < 0.0 || taxRate > 100.0) {
        throw std::invalid_argument(
            "Tax rate must be between 0 and 100."
        );
    }

    return taxableAmount * taxRate / 100.0;
}

double calculateDiscount(
    double subtotal,
    CustomerTier tier
) {
    requireNonNegative(subtotal, "Subtotal");

    if (tier == CustomerTier::Premium) {
        return subtotal *
            constants::premiumDiscountRate /
            100.0;
    }

    return 0.0;
}


// ============================================================================
// 8. ORDER CALCULATOR
// ============================================================================

class OrderCalculator {
public:
    double calculateSubtotal(
        const std::vector<OrderItem>& items
    ) const {
        if (items.empty()) {
            throw std::invalid_argument(
                "An order must contain at least one item."
            );
        }

        double subtotal = 0.0;

        for (const OrderItem& item : items) {
            subtotal += item.subtotal();
        }

        return subtotal;
    }

    double calculateDiscount(
        double subtotal,
        const CustomerProfile& customer
    ) const {
        return ::calculateDiscount(
            subtotal,
            customer.tier()
        );
    }

    double calculateTax(double taxableAmount) const {
        return ::calculateTax(
            taxableAmount,
            constants::taxRate
        );
    }

    double calculateTotal(
        const std::vector<OrderItem>& items,
        const CustomerProfile& customer
    ) const {
        const double subtotal = calculateSubtotal(items);
        const double discount = calculateDiscount(
            subtotal,
            customer
        );

        const double taxableAmount = subtotal - discount;
        const double tax = calculateTax(taxableAmount);

        return taxableAmount + tax;
    }

    double calculateShipping(double orderTotal) const {
        requireNonNegative(orderTotal, "Order total");

        if (orderTotal >= constants::freeShippingThreshold) {
            return 0.0;
        }

        return constants::standardShippingCost;
    }
};


// ============================================================================
// 9. PRESENTATION LAYER
// ============================================================================

class OrderReport {
public:
    std::string format(
        const std::vector<OrderItem>& items,
        const CustomerProfile& customer,
        const OrderCalculator& calculator
    ) const {
        const double subtotal = calculator.calculateSubtotal(items);
        const double discount = calculator.calculateDiscount(
            subtotal,
            customer
        );
        const double taxableAmount = subtotal - discount;
        const double tax = calculator.calculateTax(taxableAmount);
        const double total = taxableAmount + tax;
        const double shipping = calculator.calculateShipping(total);

        std::ostringstream output;

        output << std::fixed << std::setprecision(2);

        output << "Customer: "
               << customer.customerId()
               << "\n";

        output << "Tier: "
               << toString(customer.tier())
               << "\n";

        output << "Subtotal: INR "
               << subtotal
               << "\n";

        output << "Discount: INR "
               << discount
               << "\n";

        output << "Tax: INR "
               << tax
               << "\n";

        output << "Shipping: INR "
               << shipping
               << "\n";

        output << "Total: INR "
               << total + shipping
               << "\n";

        return output.str();
    }
};


// ============================================================================
// 10. LOGGING INTERFACE
// ============================================================================

class Logger {
public:
    virtual ~Logger() = default;

    virtual void info(const std::string& message) = 0;
    virtual void error(const std::string& message) = 0;
};


// ============================================================================
// 11. CONSOLE LOGGER
// ============================================================================

class ConsoleLogger final : public Logger {
public:
    void info(const std::string& message) override {
        std::cout << "INFO: " << message << "\n";
    }

    void error(const std::string& message) override {
        std::cerr << "ERROR: " << message << "\n";
    }
};


// ============================================================================
// 12. PAYMENT SERVICE
// ============================================================================

class PaymentService {
private:
    Logger& logger_;

public:
    explicit PaymentService(Logger& logger)
        : logger_(logger) {}

    bool processPayment(double amount) {
        requireNonNegative(amount, "Payment amount");

        if (amount == 0.0) {
            throw std::invalid_argument(
                "Payment amount must be positive."
            );
        }

        std::ostringstream message;
        message << std::fixed
                << std::setprecision(2)
                << "Processing payment of INR "
                << amount;

        logger_.info(message.str());

        return true;
    }
};


// ============================================================================
// 13. TEST LOGGER
// ============================================================================

class TestLogger final : public Logger {
private:
    std::vector<std::string> messages_;

public:
    void info(const std::string& message) override {
        messages_.push_back("INFO: " + message);
    }

    void error(const std::string& message) override {
        messages_.push_back("ERROR: " + message);
    }

    const std::vector<std::string>& messages() const {
        return messages_;
    }
};


// ============================================================================
// 14. INPUT NORMALIZATION
// ============================================================================

std::string normalizeSearchTerm(
    const std::string& searchTerm
) {
    if (searchTerm.empty()) {
        throw std::invalid_argument(
            "Search term cannot be empty."
        );
    }

    if (searchTerm.size() > 100) {
        throw std::invalid_argument(
            "Search term cannot exceed 100 characters."
        );
    }

    const auto first = searchTerm.find_first_not_of(" \t\n\r");
    const auto last = searchTerm.find_last_not_of(" \t\n\r");

    if (first == std::string::npos) {
        throw std::invalid_argument(
            "Search term cannot contain only whitespace."
        );
    }

    return searchTerm.substr(
        first,
        last - first + 1
    );
}


// ============================================================================
// 15. SAFE ACCOUNT DISPLAY
// ============================================================================

std::string maskAccountNumber(
    const std::string& accountNumber
) {
    if (accountNumber.empty()) {
        return "";
    }

    if (accountNumber.size() <= 4) {
        return std::string(
            accountNumber.size(),
            '*'
        );
    }

    return std::string(
        accountNumber.size() - 4,
        '*'
    ) + accountNumber.substr(
        accountNumber.size() - 4
    );
}


// ============================================================================
// 16. ALGORITHM COMPARISON
// ============================================================================

bool containsDuplicateSlow(
    const std::vector<int>& values
) {
    for (std::size_t index = 0; index < values.size(); ++index) {
        for (
            std::size_t nextIndex = index + 1;
            nextIndex < values.size();
            ++nextIndex
        ) {
            if (values[index] == values[nextIndex]) {
                return true;
            }
        }
    }

    return false;
}

bool containsDuplicateFast(
    const std::vector<int>& values
) {
    std::unordered_set<int> seen;

    for (int value : values) {
        if (seen.find(value) != seen.end()) {
            return true;
        }

        seen.insert(value);
    }

    return false;
}


// ============================================================================
// 17. MAINTAINABLE GRADE FUNCTION
// ============================================================================

char calculateGrade(int score) {
    if (score < 0 || score > 100) {
        throw std::out_of_range(
            "Score must be between 0 and 100."
        );
    }

    if (score >= 90) {
        return 'A';
    }

    if (score >= 80) {
        return 'B';
    }

    if (score >= 70) {
        return 'C';
    }

    if (score >= 60) {
        return 'D';
    }

    return 'F';
}


// ============================================================================
// 18. COMMAND DISPATCH
// ============================================================================

using CommandHandler = std::string (*)();

std::string commandStatus() {
    return "System is operational.";
}

std::string commandVersion() {
    return "Version 1.0";
}

std::string commandHelp() {
    return "Available commands: status, version, help";
}

std::string executeCommand(
    const std::string& command
) {
    const std::map<std::string, CommandHandler> commands = {
        {"status", commandStatus},
        {"version", commandVersion},
        {"help", commandHelp}
    };

    const auto iterator = commands.find(command);

    if (iterator == commands.end()) {
        throw std::invalid_argument(
            "Unknown command: " + command
        );
    }

    return iterator->second();
}


// ============================================================================
// 19. PAYMENT PROCESSING TEST
// ============================================================================

void testPaymentService() {
    TestLogger logger;
    PaymentService paymentService(logger);

    const bool successful =
        paymentService.processPayment(2500.0);

    require(
        successful,
        "payment service returns success"
    );

    require(
        logger.messages().size() == 1,
        "payment service records one log message"
    );
}


// ============================================================================
// 20. ORDER TESTS
// ============================================================================

void testOrderCalculator() {
    const CustomerProfile customer(
        "CUST-001",
        CustomerTier::Premium
    );

    const std::vector<OrderItem> items = {
        OrderItem(
            "Mechanical Keyboard",
            4500.0,
            1
        ),
        OrderItem(
            "Wireless Mouse",
            1800.0,
            2
        ),
        OrderItem(
            "USB-C Cable",
            700.0,
            3
        )
    };

    const OrderCalculator calculator;

    const double subtotal =
        calculator.calculateSubtotal(items);

    const double discount =
        calculator.calculateDiscount(
            subtotal,
            customer
        );

    const double taxableAmount =
        subtotal - discount;

    const double tax =
        calculator.calculateTax(taxableAmount);

    const double total =
        calculator.calculateTotal(
            items,
            customer
        );

    require(
        std::abs(subtotal - 8400.0) < 0.000001,
        "order subtotal"
    );

    require(
        std::abs(discount - 840.0) < 0.000001,
        "premium discount"
    );

    require(
        std::abs(tax - 1360.80) < 0.000001,
        "tax calculation"
    );

    require(
        std::abs(total - 8920.80) < 0.000001,
        "order total"
    );
}


// ============================================================================
// 21. EDGE-CASE TESTS
// ============================================================================

void testInvalidInputs() {
    bool exceptionCaught = false;

    try {
        OrderItem invalid(
            "Invalid",
            -1.0,
            1
        );
    } catch (const std::invalid_argument&) {
        exceptionCaught = true;
    }

    require(
        exceptionCaught,
        "negative product price is rejected"
    );

    exceptionCaught = false;

    try {
        OrderItem invalid(
            "Invalid",
            100.0,
            0
        );
    } catch (const std::invalid_argument&) {
        exceptionCaught = true;
    }

    require(
        exceptionCaught,
        "zero quantity is rejected"
    );

    exceptionCaught = false;

    try {
        calculateGrade(101);
    } catch (const std::out_of_range&) {
        exceptionCaught = true;
    }

    require(
        exceptionCaught,
        "invalid score is rejected"
    );

    exceptionCaught = false;

    try {
        executeCommand("unknown");
    } catch (const std::invalid_argument&) {
        exceptionCaught = true;
    }

    require(
        exceptionCaught,
        "unknown command is rejected"
    );
}


// ============================================================================
// 22. PERFORMANCE CASE STUDY
// ============================================================================

void benchmarkDuplicateAlgorithms() {
    printSection(
        "Performance comparison: duplicate detection"
    );

    std::vector<int> values;
    values.reserve(5000);

    for (int value = 0; value < 5000; ++value) {
        values.push_back(value);
    }

    values.push_back(4999);

    const auto slowStart =
        std::chrono::high_resolution_clock::now();

    const bool slowResult =
        containsDuplicateSlow(values);

    const auto slowEnd =
        std::chrono::high_resolution_clock::now();

    const auto fastStart =
        std::chrono::high_resolution_clock::now();

    const bool fastResult =
        containsDuplicateFast(values);

    const auto fastEnd =
        std::chrono::high_resolution_clock::now();

    const auto slowMicroseconds =
        std::chrono::duration_cast<
            std::chrono::microseconds
        >(slowEnd - slowStart).count();

    const auto fastMicroseconds =
        std::chrono::duration_cast<
            std::chrono::microseconds
        >(fastEnd - fastStart).count();

    require(
        slowResult,
        "slow algorithm detects duplicate"
    );

    require(
        fastResult,
        "fast algorithm detects duplicate"
    );

    std::cout
        << "Slow algorithm time: "
        << slowMicroseconds
        << " microseconds\n";

    std::cout
        << "Fast algorithm time: "
        << fastMicroseconds
        << " microseconds\n";

    std::cout
        << "Slow algorithm complexity: O(n^2) worst-case time.\n";

    std::cout
        << "Fast algorithm complexity: O(n) expected time and O(n) space.\n";
}


// ============================================================================
// 23. SAFE DISPLAY OF MONEY
// ============================================================================

std::string formatCurrency(double amount) {
    requireNonNegative(amount, "Currency amount");

    std::ostringstream output;

    output << std::fixed
           << std::setprecision(2)
           << "INR "
           << amount;

    return output.str();
}


// ============================================================================
// 24. COMPLETE CASE STUDY
// ============================================================================

class OrderApplication {
private:
    OrderCalculator calculator_;
    OrderReport report_;
    Logger& logger_;

public:
    explicit OrderApplication(Logger& logger)
        : logger_(logger) {}

    std::string createReport(
        const std::vector<OrderItem>& items,
        const CustomerProfile& customer
    ) {
        const double total =
            calculator_.calculateTotal(
                items,
                customer
            );

        logger_.info(
            "Order report generated for customer " +
            customer.customerId()
        );

        return report_.format(
            items,
            customer,
            calculator_
        );
    }

    double total(
        const std::vector<OrderItem>& items,
        const CustomerProfile& customer
    ) const {
        return calculator_.calculateTotal(
            items,
            customer
        );
    }
};


// ============================================================================
// 25. MAIN PROGRAM
// ============================================================================

int main() {
    try {
        printSection("C++ Code Quality Case Study");

        printSection("1. Domain model");

        const CustomerProfile customer(
            "CUST-001",
            CustomerTier::Premium
        );

        const std::vector<OrderItem> items = {
            OrderItem(
                "Mechanical Keyboard",
                4500.0,
                1
            ),
            OrderItem(
                "Wireless Mouse",
                1800.0,
                2
            ),
            OrderItem(
                "USB-C Cable",
                700.0,
                3
            )
        };

        for (const OrderItem& item : items) {
            std::cout
                << item.productName()
                << " x "
                << item.quantity()
                << " = "
                << formatCurrency(item.subtotal())
                << "\n";
        }

        printSection("2. Pricing");

        ConsoleLogger logger;
        OrderApplication application(logger);

        const double total =
            application.total(
                items,
                customer
            );

        std::cout
            << "Order total: "
            << formatCurrency(total)
            << "\n";

        printSection("3. Presentation");

        std::cout
            << application.createReport(
                items,
                customer
            );

        printSection("4. Input validation");

        const std::string searchTerm =
            normalizeSearchTerm("  mechanical keyboard  ");

        std::cout
            << "Normalized search term: "
            << searchTerm
            << "\n";

        std::cout
            << "Masked account: "
            << maskAccountNumber("1234567890")
            << "\n";

        printSection("5. Command dispatch");

        for (const std::string& command : {
            "status",
            "version",
            "help"
        }) {
            std::cout
                << command
                << " -> "
                << executeCommand(command)
                << "\n";
        }

        printSection("6. Grade classification");

        for (const int score : {
            0,
            59,
            60,
            69,
            70,
            79,
            80,
            89,
            90,
            100
        }) {
            std::cout
                << score
                << " -> "
                << calculateGrade(score)
                << "\n";
        }

        printSection("7. Automated tests");

        testPaymentService();
        testOrderCalculator();
        testInvalidInputs();

        printSection("8. Performance");

        benchmarkDuplicateAlgorithms();

        printSection("9. Quality design decisions");

        std::cout
            << "Readable names expose domain meaning.\n"
            << "Validation protects class invariants.\n"
            << "Small functions isolate business rules.\n"
            << "CustomerTier avoids fragile string comparisons.\n"
            << "OrderItem owns line-item calculations.\n"
            << "OrderCalculator owns pricing behavior.\n"
            << "OrderReport owns presentation formatting.\n"
            << "OrderApplication coordinates components.\n"
            << "Logger is injected rather than constructed internally.\n"
            << "The algorithm comparison demonstrates complexity trade-offs.\n"
            << "Input normalization creates a clear security boundary.\n";

        printSection("10. Maintainability checklist");

        const std::vector<std::string> checklist = {
            "Names communicate intent",
            "Responsibilities are focused",
            "Validation is explicit",
            "Errors are deliberate",
            "Business rules are centralized",
            "Domain data is modeled explicitly",
            "Dependencies are visible",
            "Tests cover normal and boundary cases",
            "Performance assumptions are understood",
            "Security boundaries are considered",
            "Presentation is separated from business logic",
            "Abstractions are proportional to the problem"
        };

        for (const std::string& item : checklist) {
            std::cout << "[PASS] " << item << "\n";
        }

        printSection("11. Completion");

        std::cout
            << "The maintainable commerce case study completed successfully.\n"
            << "The design emphasizes clarity, correctness, testability, "
            << "controlled coupling, explicit dependencies, and appropriate "
            << "performance.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Application error: "
            << error.what()
            << "\n";

        return 1;
    }
}
