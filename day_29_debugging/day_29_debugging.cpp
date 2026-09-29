/*
 * Debugging Case Study: Reliable Order Processing System
 * ========================================================
 *
 * C++17 case study demonstrating:
 *   - debugging workflow
 *   - validation
 *   - exceptions
 *   - assertions
 *   - state inspection
 *   - diagnostic logging
 *   - root cause analysis
 *   - fault isolation
 *   - regression testing
 *   - performance measurement
 *   - security-aware diagnostics
 *   - modular design
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic debugging_case_study.cpp -o debugging
 *
 * Run:
 *   ./debugging
 *
 * The program intentionally keeps diagnostics in the standard library so it
 * remains portable and self-contained.
 */

#include <algorithm>
#include <cassert>
#include <chrono>
#include <cmath>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>


// ============================================================================
// 1. DIAGNOSTIC LOGGING
// ============================================================================

enum class LogLevel {
    Debug,
    Info,
    Warning,
    Error
};

std::string logLevelName(LogLevel level) {
    switch (level) {
        case LogLevel::Debug:
            return "DEBUG";
        case LogLevel::Info:
            return "INFO";
        case LogLevel::Warning:
            return "WARNING";
        case LogLevel::Error:
            return "ERROR";
    }

    return "UNKNOWN";
}

class Logger {
public:
    explicit Logger(LogLevel minimumLevel = LogLevel::Debug)
        : minimumLevel_(minimumLevel) {}

    void log(LogLevel level, const std::string& message) const {
        if (static_cast<int>(level) < static_cast<int>(minimumLevel_)) {
            return;
        }

        std::cout
            << "[" << logLevelName(level) << "] "
            << message
            << '\n';
    }

    void debug(const std::string& message) const {
        log(LogLevel::Debug, message);
    }

    void info(const std::string& message) const {
        log(LogLevel::Info, message);
    }

    void warning(const std::string& message) const {
        log(LogLevel::Warning, message);
    }

    void error(const std::string& message) const {
        log(LogLevel::Error, message);
    }

private:
    LogLevel minimumLevel_;
};


// ============================================================================
// 2. EXCEPTIONS
// ============================================================================

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};

class PricingError : public std::runtime_error {
public:
    explicit PricingError(const std::string& message)
        : std::runtime_error(message) {}
};


// ============================================================================
// 3. ORDER DOMAIN MODEL
// ============================================================================

struct OrderItem {
    std::string productId;
    double unitPrice;
    int quantity;

    double total() const {
        if (!std::isfinite(unitPrice)) {
            throw ValidationError("Unit price must be finite.");
        }

        if (unitPrice < 0.0) {
            throw ValidationError("Unit price cannot be negative.");
        }

        if (quantity <= 0) {
            throw ValidationError("Quantity must be positive.");
        }

        return unitPrice * static_cast<double>(quantity);
    }
};


class Order {
public:
    Order(
        std::string orderId,
        std::vector<OrderItem> items,
        double discountPercent
    )
        : orderId_(std::move(orderId)),
          items_(std::move(items)),
          discountPercent_(discountPercent) {}

    const std::string& id() const {
        return orderId_;
    }

    const std::vector<OrderItem>& items() const {
        return items_;
    }

    double discountPercent() const {
        return discountPercent_;
    }

    double subtotal() const {
        double result = 0.0;

        for (const auto& item : items_) {
            result += item.total();
        }

        return result;
    }

    double total() const {
        validateDiscount();

        const double subtotalValue = subtotal();

        const double discountAmount =
            subtotalValue * (discountPercent_ / 100.0);

        const double finalAmount =
            subtotalValue - discountAmount;

        // Internal invariant:
        // a valid non-negative discount cannot make a non-negative subtotal
        // negative.
        assert(finalAmount >= 0.0);

        return roundCurrency(finalAmount);
    }

private:
    static double roundCurrency(double value) {
        return std::round(value * 100.0) / 100.0;
    }

    void validateDiscount() const {
        if (!std::isfinite(discountPercent_)) {
            throw ValidationError("Discount must be finite.");
        }

        if (discountPercent_ < 0.0 || discountPercent_ > 100.0) {
            throw ValidationError(
                "Discount must be between 0 and 100 percent."
            );
        }
    }

    std::string orderId_;
    std::vector<OrderItem> items_;
    double discountPercent_;
};


// ============================================================================
// 4. PRICE CALCULATION PIPELINE
// ============================================================================

double parseAmount(const std::string& rawAmount) {
    std::size_t processedCharacters = 0;

    try {
        const double amount = std::stod(rawAmount, &processedCharacters);

        if (processedCharacters != rawAmount.size()) {
            throw ValidationError(
                "Amount contains unexpected characters: " + rawAmount
            );
        }

        if (!std::isfinite(amount)) {
            throw ValidationError("Amount must be finite.");
        }

        return amount;
    } catch (const std::invalid_argument&) {
        throw ValidationError(
            "Amount is not a valid number: " + rawAmount
        );
    } catch (const std::out_of_range&) {
        throw ValidationError(
            "Amount is outside the supported numeric range."
        );
    }
}


double applyTax(double amount, double taxRate) {
    if (!std::isfinite(amount)) {
        throw PricingError("Amount must be finite.");
    }

    if (amount < 0.0) {
        throw PricingError("Amount cannot be negative.");
    }

    if (!std::isfinite(taxRate) || taxRate < 0.0 || taxRate > 1.0) {
        throw PricingError(
            "Tax rate must be between 0 and 1."
        );
    }

    return amount * (1.0 + taxRate);
}


double roundCurrency(double amount) {
    return std::round(amount * 100.0) / 100.0;
}


double pricingPipeline(
    const std::string& rawAmount,
    double taxRate,
    const Logger& logger
) {
    // Each stage has one responsibility. This makes fault isolation easier.
    const double amount = parseAmount(rawAmount);

    logger.debug(
        "Stage 1 parsed amount = " + std::to_string(amount)
    );

    const double taxedAmount = applyTax(amount, taxRate);

    logger.debug(
        "Stage 2 taxed amount = " + std::to_string(taxedAmount)
    );

    const double finalAmount = roundCurrency(taxedAmount);

    logger.debug(
        "Stage 3 rounded amount = " + std::to_string(finalAmount)
    );

    return finalAmount;
}


// ============================================================================
// 5. REGRESSION TEST FRAMEWORK
// ============================================================================

class TestRunner {
public:
    void expectTrue(
        const std::string& testName,
        bool condition
    ) {
        if (condition) {
            ++passed_;
            std::cout << "PASS: " << testName << '\n';
        } else {
            ++failed_;
            std::cout << "FAIL: " << testName << '\n';
        }
    }

    void expectNear(
        const std::string& testName,
        double actual,
        double expected,
        double tolerance = 1e-9
    ) {
        const bool passed =
            std::abs(actual - expected) <= tolerance;

        expectTrue(testName, passed);

        if (!passed) {
            std::cout
                << "       actual=" << actual
                << " expected=" << expected
                << '\n';
        }
    }

    void expectThrows(
        const std::string& testName,
        const std::function<void()>& operation
    ) {
        bool threw = false;

        try {
            operation();
        } catch (const std::exception&) {
            threw = true;
        }

        expectTrue(testName, threw);
    }

    int passed() const {
        return passed_;
    }

    int failed() const {
        return failed_;
    }

private:
    int passed_ = 0;
    int failed_ = 0;
};


// ============================================================================
// 6. UNIT AND REGRESSION TESTS
// ============================================================================

void runRegressionTests(const Logger& logger) {
    std::cout << "\n============================================================\n";
    std::cout << "REGRESSION TESTS\n";
    std::cout << "============================================================\n";

    TestRunner tests;

    {
        Order order(
            "TEST-001",
            {},
            0.0
        );

        tests.expectNear(
            "Empty order subtotal",
            order.subtotal(),
            0.0
        );

        tests.expectNear(
            "Empty order total",
            order.total(),
            0.0
        );
    }

    {
        Order order(
            "TEST-002",
            {
                {"A", 100.0, 1},
                {"B", 50.0, 2}
            },
            10.0
        );

        tests.expectNear(
            "Order subtotal",
            order.subtotal(),
            200.0
        );

        tests.expectNear(
            "Order discounted total",
            order.total(),
            180.0
        );
    }

    tests.expectThrows(
        "Negative item price rejected",
        [] {
            Order order(
                "TEST-003",
                {{"BAD", -10.0, 1}},
                0.0
            );

            static_cast<void>(order.total());
        }
    );

    tests.expectThrows(
        "Zero quantity rejected",
        [] {
            Order order(
                "TEST-004",
                {{"BAD", 10.0, 0}},
                0.0
            );

            static_cast<void>(order.total());
        }
    );

    tests.expectThrows(
        "Invalid discount rejected",
        [] {
            Order order(
                "TEST-005",
                {{"A", 10.0, 1}},
                101.0
            );

            static_cast<void>(order.total());
        }
    );

    tests.expectNear(
        "Currency rounding",
        roundCurrency(10.005),
        10.01,
        1e-9
    );

    tests.expectNear(
        "Pricing pipeline",
        pricingPipeline("100.00", 0.18, logger),
        118.00
    );

    std::cout
        << "Tests passed: " << tests.passed()
        << ", failed: " << tests.failed()
        << '\n';
}


// ============================================================================
// 7. ROOT CAUSE ANALYSIS MODEL
// ============================================================================

struct Incident {
    std::string symptom;
    std::vector<std::string> evidence;
    std::vector<std::string> hypotheses;
    std::optional<std::string> rootCause;
    std::optional<std::string> correctiveAction;
};


void performRootCauseAnalysis(Incident& incident) {
    std::cout << "\n============================================================\n";
    std::cout << "ROOT CAUSE ANALYSIS\n";
    std::cout << "============================================================\n";

    std::cout << "Symptom: " << incident.symptom << "\n\n";

    std::cout << "Evidence:\n";
    for (const auto& item : incident.evidence) {
        std::cout << " - " << item << '\n';
    }

    std::cout << "\nHypotheses:\n";
    for (const auto& hypothesis : incident.hypotheses) {
        std::cout << " - " << hypothesis << '\n';
    }

    /*
     * RCA should be evidence-driven. We identify the cause only because the
     * evidence specifically shows duplicate discount execution.
     */
    const bool duplicateDiscountConfirmed =
        std::any_of(
            incident.evidence.begin(),
            incident.evidence.end(),
            [](const std::string& evidence) {
                return evidence.find("discount applied twice") !=
                       std::string::npos;
            }
        );

    if (duplicateDiscountConfirmed) {
        incident.rootCause =
            "The discount operation was applied twice.";

        incident.correctiveAction =
            "Centralize discount application and add a regression test.";
    }

    if (incident.rootCause.has_value()) {
        std::cout
            << "\nRoot cause: "
            << incident.rootCause.value()
            << '\n';
    }

    if (incident.correctiveAction.has_value()) {
        std::cout
            << "Corrective action: "
            << incident.correctiveAction.value()
            << '\n';
    }
}


// ============================================================================
// 8. STATE INSPECTION
// ============================================================================

class ShoppingCart {
public:
    explicit ShoppingCart(std::vector<double> items)
        : items_(std::move(items)) {}

    const std::vector<double>& items() const {
        return items_;
    }

    double subtotal() const {
        double result = 0.0;

        for (double item : items_) {
            result += item;
        }

        return result;
    }

    double removeItem(std::size_t index) {
        if (index >= items_.size()) {
            throw std::out_of_range(
                "Shopping-cart index is out of range."
            );
        }

        const double removed = items_[index];

        items_.erase(items_.begin() + static_cast<std::ptrdiff_t>(index));

        return removed;
    }

private:
    std::vector<double> items_;
};


void stateInspectionDemo() {
    std::cout << "\n============================================================\n";
    std::cout << "STATE INSPECTION\n";
    std::cout << "============================================================\n";

    ShoppingCart cart({100.0, 50.0, 25.0});

    const auto before = cart.items();

    const double removed = cart.removeItem(1);

    const auto after = cart.items();

    std::cout << "Items before mutation: ";
    for (double value : before) {
        std::cout << value << ' ';
    }

    std::cout << "\nRemoved item: " << removed << '\n';

    std::cout << "Items after mutation: ";
    for (double value : after) {
        std::cout << value << ' ';
    }

    std::cout << "\nSubtotal: " << cart.subtotal() << '\n';

    if (after.size() != before.size() - 1) {
        std::cerr << "Unexpected state transition detected.\n";
    }
}


// ============================================================================
// 9. PERFORMANCE DEBUGGING
// ============================================================================

void performanceDemo(const Logger& logger) {
    std::cout << "\n============================================================\n";
    std::cout << "PERFORMANCE DEBUGGING\n";
    std::cout << "============================================================\n";

    constexpr std::size_t elementCount = 1'000'000;

    std::vector<int> values;
    values.reserve(elementCount);

    for (std::size_t index = 0; index < elementCount; ++index) {
        values.push_back(static_cast<int>(index));
    }

    const auto start = std::chrono::steady_clock::now();

    long long total = 0;

    for (int value : values) {
        total += value;
    }

    const auto end = std::chrono::steady_clock::now();

    const auto elapsed =
        std::chrono::duration_cast<std::chrono::microseconds>(
            end - start
        );

    logger.info(
        "Performance measurement completed."
    );

    std::cout << "Total: " << total << '\n';
    std::cout << "Elapsed microseconds: "
              << elapsed.count()
              << '\n';

    /*
     * Complexity:
     *   Time:  O(n)
     *   Space: O(n) for the stored vector.
     *
     * A timing measurement indicates where cost occurs but does not prove
     * why the entire application is slow. Production profiling may be needed.
     */
}


// ============================================================================
// 10. DEBUGGING A FAILURE
// ============================================================================

void debuggingWorkflowDemo(const Logger& logger) {
    std::cout << "\n============================================================\n";
    std::cout << "DEBUGGING WORKFLOW DEMONSTRATION\n";
    std::cout << "============================================================\n";

    const std::string input = "100.00";
    const double taxRate = 0.18;

    logger.info("Reproducing pricing calculation failure.");

    try {
        const double result =
            pricingPipeline(input, taxRate, logger);

        std::cout
            << std::fixed
            << std::setprecision(2)
            << "Observed result: "
            << result
            << '\n';

        std::cout
            << "Expected result: 118.00\n";
    } catch (const std::exception& error) {
        logger.error(
            std::string("Failure reproduced: ") +
            error.what()
        );
    }

    std::cout
        << "\nDebugging procedure demonstrated:\n"
        << "1. Capture the failing input.\n"
        << "2. Reproduce it.\n"
        << "3. Isolate processing stages.\n"
        << "4. Inspect intermediate state.\n"
        << "5. Compare observed and expected values.\n"
        << "6. Form a testable hypothesis.\n"
        << "7. Correct the root cause.\n"
        << "8. Add a regression test.\n";
}


// ============================================================================
// 11. SECURITY-AWARE DIAGNOSTICS
// ============================================================================

void securityDiagnosticsDemo(const Logger& logger) {
    std::cout << "\n============================================================\n";
    std::cout << "SECURITY-AWARE DIAGNOSTICS\n";
    std::cout << "============================================================\n";

    const std::string userId = "user-12345";
    const std::string transactionId = "txn-789";

    logger.info(
        "Transaction diagnostic context: userId=" +
        userId +
        " transactionId=" +
        transactionId
    );

    std::cout
        << "Diagnostic logs should not contain passwords, access tokens,\n"
        << "private keys, session secrets, or complete payment-card data.\n";
}


// ============================================================================
// 12. EDGE CASES
// ============================================================================

void edgeCaseDemo(const Logger& logger) {
    std::cout << "\n============================================================\n";
    std::cout << "EDGE CASES\n";
    std::cout << "============================================================\n";

    const std::vector<std::string> invalidAmounts = {
        "",
        "abc",
        "100abc",
        "nan",
        "inf"
    };

    for (const auto& rawAmount : invalidAmounts) {
        try {
            const double value = parseAmount(rawAmount);

            std::cout
                << "Accepted amount "
                << rawAmount
                << " = "
                << value
                << '\n';
        } catch (const std::exception& error) {
            logger.warning(
                "Rejected input '" +
                rawAmount +
                "': " +
                error.what()
            );
        }
    }

    /*
     * The purpose of this test is not merely to reject invalid data. It
     * demonstrates that edge cases are deliberate inputs to a debugging
     * strategy rather than unexpected surprises discovered in production.
     */
}


// ============================================================================
// 13. COMPARISON OF DEBUGGING TECHNIQUES
// ============================================================================

void compareTechniques() {
    std::cout << "\n============================================================\n";
    std::cout << "DEBUGGING TECHNIQUE COMPARISON\n";
    std::cout << "============================================================\n";

    const std::map<std::string, std::string> techniques = {
        {
            "Print statements",
            "Simple but can become noisy and difficult to manage."
        },
        {
            "Logging",
            "Persistent diagnostic events with levels and context."
        },
        {
            "Breakpoints",
            "Interactive inspection of execution state."
        },
        {
            "Assertions",
            "Useful for detecting violated programmer assumptions."
        },
        {
            "Regression tests",
            "Repeatable verification that a known defect stays fixed."
        },
        {
            "Profiling",
            "Measures performance hotspots rather than logical correctness."
        }
    };

    for (const auto& [technique, description] : techniques) {
        std::cout
            << technique
            << ": "
            << description
            << '\n';
    }
}


// ============================================================================
// 14. MAIN
// ============================================================================

int main() {
    const Logger logger(LogLevel::Debug);

    std::cout
        << "DEBUGGING CASE STUDY: ORDER PROCESSING SYSTEM\n";

    debuggingWorkflowDemo(logger);

    std::cout << "\n============================================================\n";
    std::cout << "SUCCESSFUL ORDER\n";
    std::cout << "============================================================\n";

    try {
        Order order(
            "ORD-1001",
            {
                {"BOOK-01", 500.0, 2},
                {"COURSE-01", 1200.0, 1}
            },
            10.0
        );

        const double subtotal = order.subtotal();
        const double total = order.total();

        logger.info(
            "Order processed successfully: id=" +
            order.id()
        );

        std::cout
            << std::fixed
            << std::setprecision(2)
            << "Subtotal: "
            << subtotal
            << "\nTotal: "
            << total
            << '\n';

    } catch (const std::exception& error) {
        logger.error(
            std::string("Order processing failed: ") +
            error.what()
        );
    }

    stateInspectionDemo();

    Incident incident{
        "Customer receives a price lower than expected.",
        {
            "Catalog prices match expected values.",
            "Tax calculation is correct.",
            "discount applied twice",
            "Removing the duplicate operation restores expected pricing."
        },
        {
            "Incorrect catalog price",
            "Incorrect tax calculation",
            "Duplicate discount application",
            "Currency rounding problem"
        },
        std::nullopt,
        std::nullopt
    };

    performRootCauseAnalysis(incident);

    securityDiagnosticsDemo(logger);
    edgeCaseDemo(logger);
    performanceDemo(logger);

    runRegressionTests(logger);

    compareTechniques();

    std::cout << "\n============================================================\n";
    std::cout << "CASE STUDY COMPLETE\n";
    std::cout << "============================================================\n";

    std::cout
        << "The implementation demonstrates a complete debugging cycle:\n"
        << "reproduce -> observe -> isolate -> hypothesize -> verify -> fix ->\n"
        << "regression test -> monitor.\n";

    return 0;
}
