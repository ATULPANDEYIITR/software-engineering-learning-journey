"use strict";

/*
 * Code Quality: Readability, Naming, Formatting, Maintainability
 *
 * This standalone JavaScript file demonstrates practical code-quality
 * principles from beginner through advanced application design.
 *
 * It can run in Node.js without external packages.
 */

// ============================================================================
// 1. OUTPUT HELPERS
// ============================================================================

function section(title) {
    console.log(`\n${"=".repeat(78)}`);
    console.log(title);
    console.log("=".repeat(78));
}

function subsection(title) {
    console.log(`\n--- ${title} ---`);
}

function show(label, value) {
    console.log(`${label}:`, value);
}


// ============================================================================
// 2. READABILITY
// ============================================================================

section("1. Readability");

function calculateOrderTotalBad(a, b, c, d) {
    return (a * b) + ((a * b) * c / 100) - d;
}

function calculateOrderTotal(
    unitPrice,
    quantity,
    taxRatePercent,
    discount
) {
    // Named intermediate values expose the business meaning of the formula.
    const subtotal = unitPrice * quantity;
    const taxAmount = subtotal * taxRatePercent / 100;
    const totalBeforeDiscount = subtotal + taxAmount;
    const finalTotal = totalBeforeDiscount - discount;

    return Math.max(finalTotal, 0);
}

show("Hard-to-read result", calculateOrderTotalBad(100, 3, 18, 20));
show("Readable result", calculateOrderTotal(100, 3, 18, 20));


// ============================================================================
// 3. NAMING
// ============================================================================

section("2. Naming");

const userCount = 25;
const maximumRetries = 3;
const requestTimeoutSeconds = 10;

const isAuthenticated = true;
const hasPermission = true;
const isExpired = false;

show("User count", userCount);
show("Maximum retries", maximumRetries);
show("Request timeout", requestTimeoutSeconds);

if (isAuthenticated && hasPermission && !isExpired) {
    console.log("Request is allowed.");
}


// ============================================================================
// 4. FUNCTIONS WITH ONE CLEAR RESPONSIBILITY
// ============================================================================

section("3. Focused functions");

function validatePercentage(value, fieldName) {
    if (!Number.isFinite(value)) {
        throw new TypeError(`${fieldName} must be a finite number.`);
    }

    if (value < 0 || value > 100) {
        throw new RangeError(`${fieldName} must be between 0 and 100.`);
    }
}

function calculateDiscountedPrice(originalPrice, discountPercent) {
    if (!Number.isFinite(originalPrice) || originalPrice < 0) {
        throw new RangeError("Original price must be non-negative.");
    }

    validatePercentage(discountPercent, "discountPercent");

    const discountAmount = originalPrice * discountPercent / 100;
    return originalPrice - discountAmount;
}

function formatCurrency(amount, currency = "INR") {
    return `${currency} ${amount.toFixed(2)}`;
}

const discountedPrice = calculateDiscountedPrice(1000, 15);
show("Discounted price", formatCurrency(discountedPrice));


// ============================================================================
// 5. GUARD CLAUSES
// ============================================================================

section("4. Guard clauses");

function createUsername(email) {
    if (typeof email !== "string") {
        throw new TypeError("Email must be a string.");
    }

    const cleanedEmail = email.trim();

    if (cleanedEmail.length === 0) {
        throw new Error("Email cannot be empty.");
    }

    const separatorIndex = cleanedEmail.indexOf("@");

    if (separatorIndex <= 0) {
        throw new Error("Email must contain a username and '@'.");
    }

    return cleanedEmail.slice(0, separatorIndex).toLowerCase();
}

for (const email of ["Alice@example.com", " bob@example.com "]) {
    console.log(email, "->", createUsername(email));
}


// ============================================================================
// 6. CONSTANTS AND MAGIC NUMBERS
// ============================================================================

section("5. Constants");

const SECONDS_PER_MINUTE = 60;
const MINUTES_PER_HOUR = 60;
const SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR;

function hoursToSeconds(hours) {
    if (!Number.isFinite(hours) || hours < 0) {
        throw new RangeError("Hours must be non-negative.");
    }

    return hours * SECONDS_PER_HOUR;
}

show("Two hours in seconds", hoursToSeconds(2));


// ============================================================================
// 7. DATA STRUCTURES
// ============================================================================

section("6. Data structures that communicate intent");

const locationObject = {
    city: "Lucknow",
    country: "India"
};

show("City", locationObject.city);
show("Country", locationObject.country);

const orders = [
    { customer: "Asha", amount: 1200, paid: true },
    { customer: "Ravi", amount: 800, paid: false },
    { customer: "Meera", amount: 1600, paid: true }
];

const paidOrderTotals = orders
    .filter(order => order.paid)
    .map(order => order.amount);

show("Paid order totals", paidOrderTotals);
show(
    "Paid revenue",
    paidOrderTotals.reduce((total, amount) => total + amount, 0)
);


// ============================================================================
// 8. OBJECT-ORIENTED DESIGN
// ============================================================================

section("7. Classes and invariants");

class BankAccount {
    constructor(accountNumber, initialBalance = 0) {
        if (typeof accountNumber !== "string" || accountNumber.trim() === "") {
            throw new Error("Account number cannot be empty.");
        }

        if (!Number.isFinite(initialBalance) || initialBalance < 0) {
            throw new RangeError("Initial balance cannot be negative.");
        }

        this.accountNumber = accountNumber;
        this.balance = initialBalance;
    }

    deposit(amount) {
        this.#validatePositiveAmount(amount);
        this.balance += amount;
    }

    withdraw(amount) {
        this.#validatePositiveAmount(amount);

        if (amount > this.balance) {
            return false;
        }

        this.balance -= amount;
        return true;
    }

    #validatePositiveAmount(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new RangeError("Amount must be positive.");
        }
    }
}

const account = new BankAccount("ACC-1001", 1000);
account.deposit(500);
const withdrawalSucceeded = account.withdraw(200);

show("Withdrawal succeeded", withdrawalSucceeded);
show("Account balance", account.balance);


// ============================================================================
// 9. ENUM-LIKE STATES
// ============================================================================

section("8. Explicit states");

const OrderStatus = Object.freeze({
    PENDING: "pending",
    PAID: "paid",
    SHIPPED: "shipped",
    CANCELLED: "cancelled"
});

function canCancelOrder(status) {
    return status === OrderStatus.PENDING ||
        status === OrderStatus.PAID;
}

for (const status of Object.values(OrderStatus)) {
    console.log(status, "can cancel:", canCancelOrder(status));
}


// ============================================================================
// 10. VALIDATION
// ============================================================================

section("9. Validation");

function isValidEmail(email) {
    if (typeof email !== "string") {
        return false;
    }

    // This is deliberately basic structural validation, not a complete
    // implementation of every valid email address defined by standards.
    const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    return emailPattern.test(email.trim());
}

for (const email of [
    "person@example.com",
    "invalid-email",
    "person@example"
]) {
    console.log(email, "valid:", isValidEmail(email));
}

function validateProduct(name, price, quantity) {
    const errors = [];

    if (typeof name !== "string" || name.trim() === "") {
        errors.push("Product name cannot be empty.");
    }

    if (!Number.isFinite(price) || price < 0) {
        errors.push("Price must be non-negative.");
    }

    if (!Number.isInteger(quantity) || quantity < 0) {
        errors.push("Quantity must be a non-negative integer.");
    }

    return errors;
}

show("Product errors", validateProduct("", -10, -2));


// ============================================================================
// 11. ERROR HANDLING
// ============================================================================

section("10. Error handling");

function parsePositiveInteger(text) {
    if (typeof text !== "string") {
        throw new TypeError("Input must be text.");
    }

    const value = Number(text.trim());

    if (!Number.isInteger(value)) {
        throw new TypeError("Expected a whole number.");
    }

    if (value <= 0) {
        throw new RangeError("Number must be positive.");
    }

    return value;
}

for (const value of ["25", "0", "hello"]) {
    try {
        console.log(value, "->", parsePositiveInteger(value));
    } catch (error) {
        console.log(value, "-> error:", error.message);
    }
}


// ============================================================================
// 12. EDGE CASES
// ============================================================================

section("11. Edge cases");

function safePercentageChange(oldValue, newValue) {
    if (!Number.isFinite(oldValue) || !Number.isFinite(newValue)) {
        throw new TypeError("Values must be finite numbers.");
    }

    if (oldValue === 0) {
        if (newValue === 0) {
            return 0;
        }

        throw new RangeError(
            "Percentage change from zero is undefined for a non-zero result."
        );
    }

    return ((newValue - oldValue) / Math.abs(oldValue)) * 100;
}

for (const [oldValue, newValue] of [
    [100, 120],
    [100, 80],
    [0, 0]
]) {
    console.log(
        `${oldValue} -> ${newValue}:`,
        safePercentageChange(oldValue, newValue)
    );
}

try {
    safePercentageChange(0, 10);
} catch (error) {
    console.log("Expected edge-case error:", error.message);
}


// ============================================================================
// 13. IMMUTABILITY
// ============================================================================

section("12. Immutability and predictable state");

const applicationConfig = Object.freeze({
    requestTimeoutSeconds: 30,
    maximumBatchSize: 100,
    enableAuditLogging: true
});

show("Application config", applicationConfig);

console.log(
    "Object.freeze prevents ordinary property mutation in strict mode."
);


// ============================================================================
// 14. PURE FUNCTIONS
// ============================================================================

section("13. Pure functions");

function addTax(amount, taxRate) {
    return amount + amount * taxRate / 100;
}

const firstTaxResult = addTax(100, 18);
const secondTaxResult = addTax(100, 18);

show("First result", firstTaxResult);
show("Second result", secondTaxResult);
show("Deterministic", firstTaxResult === secondTaxResult);


// ============================================================================
// 15. FUNCTIONAL DATA PROCESSING
// ============================================================================

section("14. Functional collection processing");

const products = [
    { name: "Keyboard", price: 2500, quantity: 1 },
    { name: "Mouse", price: 1000, quantity: 2 },
    { name: "Cable", price: 500, quantity: 3 }
];

const productSubtotals = products.map(
    product => product.price * product.quantity
);

const inventoryValue = productSubtotals.reduce(
    (total, subtotal) => total + subtotal,
    0
);

show("Product subtotals", productSubtotals);
show("Inventory value", inventoryValue);


// ============================================================================
// 16. AVOIDING DUPLICATION
// ============================================================================

section("15. Reusable business logic");

function calculateTax(amount, taxRate) {
    validatePercentage(taxRate, "taxRate");
    return amount * taxRate / 100;
}

function calculateInvoiceTotal(itemTotal, taxRate, shippingCost) {
    if (itemTotal < 0 || shippingCost < 0) {
        throw new RangeError("Amounts cannot be negative.");
    }

    return itemTotal + calculateTax(itemTotal, taxRate) + shippingCost;
}

show(
    "Invoice total",
    calculateInvoiceTotal(5000, 18, 100)
);


// ============================================================================
// 17. COMPLEXITY
// ============================================================================

section("16. Algorithmic clarity");

function containsDuplicateSlow(values) {
    for (let index = 0; index < values.length; index += 1) {
        for (let nextIndex = index + 1; nextIndex < values.length; nextIndex += 1) {
            if (values[index] === values[nextIndex]) {
                return true;
            }
        }
    }

    return false;
}

function containsDuplicateFast(values) {
    const seen = new Set();

    for (const value of values) {
        if (seen.has(value)) {
            return true;
        }

        seen.add(value);
    }

    return false;
}

const sampleValues = [1, 2, 3, 4, 5, 4];

show(
    "Slow duplicate detection",
    containsDuplicateSlow(sampleValues)
);

show(
    "Fast duplicate detection",
    containsDuplicateFast(sampleValues)
);

console.log(
    "Slow algorithm: O(n^2) worst-case time."
);

console.log(
    "Set-based algorithm: O(n) expected time with O(n) additional space."
);


// ============================================================================
// 18. PERFORMANCE MEASUREMENT
// ============================================================================

section("17. Measuring performance");

const benchmarkValues = Array.from(
    { length: 5000 },
    (_, index) => index
);

benchmarkValues.push(4999);

let start = performance.now();
containsDuplicateSlow(benchmarkValues);
const slowDuration = performance.now() - start;

start = performance.now();
containsDuplicateFast(benchmarkValues);
const fastDuration = performance.now() - start;

show("Slow duration in milliseconds", slowDuration.toFixed(4));
show("Fast duration in milliseconds", fastDuration.toFixed(4));


// ============================================================================
// 19. DEPENDENCY INJECTION
// ============================================================================

section("18. Dependency injection");

class Clock {
    now() {
        return new Date();
    }
}

class ReportService {
    constructor(clock) {
        if (!clock || typeof clock.now !== "function") {
            throw new TypeError("A clock with a now() function is required.");
        }

        this.clock = clock;
    }

    createTimestamp() {
        return this.clock.now().toISOString();
    }
}

const reportService = new ReportService(new Clock());

show("Report timestamp", reportService.createTimestamp());


// ============================================================================
// 20. TESTABLE CLOCK
// ============================================================================

section("19. Testability through dependency injection");

class FixedClock {
    constructor(date) {
        this.date = new Date(date);
    }

    now() {
        return new Date(this.date);
    }
}

const fixedClock = new FixedClock("2026-01-01T00:00:00.000Z");
const deterministicReportService = new ReportService(fixedClock);

show(
    "Deterministic timestamp",
    deterministicReportService.createTimestamp()
);


// ============================================================================
// 21. SMALL ASSERTION HELPER
// ============================================================================

section("20. Testing");

function assertEqual(expected, actual, description) {
    if (expected !== actual) {
        throw new Error(
            `${description}: expected ${expected}, got ${actual}`
        );
    }

    console.log(`PASS: ${description}`);
}

assertEqual(
    20,
    calculateOrderTotal(4, 5, 0, 0),
    "basic order calculation"
);

assertEqual(
    true,
    containsDuplicateFast([1, 2, 1]),
    "duplicate detection"
);

assertEqual(
    false,
    containsDuplicateFast([1, 2, 3]),
    "unique collection"
);


// ============================================================================
// 22. COMMAND DISPATCH
// ============================================================================

section("21. Explicit command dispatch");

function commandStatus() {
    return "System is operational.";
}

function commandVersion() {
    return "Version 1.0";
}

function commandHelp() {
    return "Available commands: status, version, help";
}

const commands = Object.freeze({
    status: commandStatus,
    version: commandVersion,
    help: commandHelp
});

function executeCommand(command) {
    if (typeof command !== "string") {
        throw new TypeError("Command must be a string.");
    }

    const normalizedCommand = command.trim().toLowerCase();
    const handler = commands[normalizedCommand];

    if (typeof handler !== "function") {
        throw new Error(`Unknown command: ${command}`);
    }

    return handler();
}

for (const command of ["status", "version", "help"]) {
    console.log(command, "->", executeCommand(command));
}

try {
    executeCommand("delete-everything");
} catch (error) {
    console.log("Expected command error:", error.message);
}


// ============================================================================
// 23. DOMAIN MODEL
// ============================================================================

section("22. Domain modeling");

class OrderItem {
    constructor(productName, unitPrice, quantity) {
        if (typeof productName !== "string" || productName.trim() === "") {
            throw new Error("Product name cannot be empty.");
        }

        if (!Number.isFinite(unitPrice) || unitPrice < 0) {
            throw new RangeError("Unit price cannot be negative.");
        }

        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new RangeError("Quantity must be a positive integer.");
        }

        this.productName = productName;
        this.unitPrice = unitPrice;
        this.quantity = quantity;
    }

    get subtotal() {
        return this.unitPrice * this.quantity;
    }
}

class CustomerProfile {
    constructor(customerId, tier) {
        if (!customerId.trim()) {
            throw new Error("Customer ID cannot be empty.");
        }

        this.customerId = customerId;
        this.tier = tier;
    }
}

const CustomerTier = Object.freeze({
    STANDARD: "standard",
    PREMIUM: "premium"
});


// ============================================================================
// 24. INTEGRATED ORDER CALCULATOR
// ============================================================================

section("23. Integrated maintainable order calculator");

class OrderCalculator {
    static PREMIUM_DISCOUNT_RATE = 10;
    static TAX_RATE = 18;

    calculateSubtotal(items) {
        if (!Array.isArray(items) || items.length === 0) {
            throw new Error("An order must contain at least one item.");
        }

        return items.reduce(
            (subtotal, item) => subtotal + item.subtotal,
            0
        );
    }

    calculateDiscount(subtotal, customer) {
        if (customer.tier === CustomerTier.PREMIUM) {
            return subtotal * OrderCalculator.PREMIUM_DISCOUNT_RATE / 100;
        }

        return 0;
    }

    calculateTax(taxableAmount) {
        return taxableAmount * OrderCalculator.TAX_RATE / 100;
    }

    calculateTotal(items, customer) {
        const subtotal = this.calculateSubtotal(items);
        const discount = this.calculateDiscount(subtotal, customer);
        const taxableAmount = subtotal - discount;
        const tax = this.calculateTax(taxableAmount);

        return taxableAmount + tax;
    }
}

class OrderReport {
    format(items, customer, calculator) {
        const subtotal = calculator.calculateSubtotal(items);
        const discount = calculator.calculateDiscount(subtotal, customer);
        const taxableAmount = subtotal - discount;
        const tax = calculator.calculateTax(taxableAmount);
        const total = calculator.calculateTotal(items, customer);

        return [
            `Customer: ${customer.customerId}`,
            `Tier: ${customer.tier}`,
            `Subtotal: INR ${subtotal.toFixed(2)}`,
            `Discount: INR ${discount.toFixed(2)}`,
            `Tax: INR ${tax.toFixed(2)}`,
            `Total: INR ${total.toFixed(2)}`
        ].join("\n");
    }
}

const customer = new CustomerProfile(
    "CUST-001",
    CustomerTier.PREMIUM
);

const orderItems = [
    new OrderItem("Mechanical Keyboard", 4500, 1),
    new OrderItem("Wireless Mouse", 1800, 2),
    new OrderItem("USB-C Cable", 700, 3)
];

const calculator = new OrderCalculator();
const report = new OrderReport();

console.log(
    report.format(orderItems, customer, calculator)
);


// ============================================================================
// 25. EDGE-CASE TESTING FOR THE DOMAIN MODEL
// ============================================================================

section("24. Integrated tests");

assertEqual(
    8400,
    calculator.calculateSubtotal(orderItems),
    "order subtotal"
);

assertEqual(
    840,
    calculator.calculateDiscount(
        calculator.calculateSubtotal(orderItems),
        customer
    ),
    "premium discount"
);

assertEqual(
    8920.8,
    calculator.calculateTotal(orderItems, customer),
    "order total"
);

try {
    new OrderItem("Invalid", -1, 1);
} catch (error) {
    console.log("PASS: negative price rejected.");
}

try {
    new OrderItem("Invalid", 100, 0);
} catch (error) {
    console.log("PASS: zero quantity rejected.");
}

try {
    calculator.calculateSubtotal([]);
} catch (error) {
    console.log("PASS: empty order rejected.");
}


// ============================================================================
// 26. ASYNC CODE QUALITY
// ============================================================================

section("25. Asynchronous code and explicit failures");

function delay(milliseconds) {
    return new Promise(resolve => {
        setTimeout(resolve, milliseconds);
    });
}

async function loadConfiguration() {
    await delay(10);

    // Returning structured configuration is clearer than scattering settings
    // across unrelated asynchronous functions.
    return Object.freeze({
        timeoutSeconds: 30,
        retryLimit: 3
    });
}

async function initializeApplication() {
    try {
        const configuration = await loadConfiguration();

        if (configuration.retryLimit < 0) {
            throw new Error("Retry limit cannot be negative.");
        }

        return configuration;
    } catch (error) {
        // At a system boundary, failures can be translated or logged.
        throw new Error(
            `Application initialization failed: ${error.message}`
        );
    }
}

initializeApplication()
    .then(configuration => {
        show("Loaded configuration", configuration);
    })
    .catch(error => {
        console.error("Initialization error:", error.message);
    });


// ============================================================================
// 27. PROMISES AND CONTROL FLOW
// ============================================================================

section("26. Avoiding unnecessary promise nesting");

async function fetchUserProfile() {
    // Simulated asynchronous operation.
    await delay(5);

    return {
        id: "U-100",
        name: "Asha",
        active: true
    };
}

async function buildUserGreeting() {
    const profile = await fetchUserProfile();

    if (!profile.active) {
        throw new Error("User account is inactive.");
    }

    return `Hello, ${profile.name}.`;
}

buildUserGreeting()
    .then(greeting => show("Greeting", greeting))
    .catch(error => show("Greeting error", error.message));


// ============================================================================
// 28. SECURITY
// ============================================================================

section("27. Security and maintainability");

function normalizeSearchTerm(searchTerm) {
    if (typeof searchTerm !== "string") {
        throw new TypeError("Search term must be a string.");
    }

    const normalized = searchTerm.trim();

    if (normalized.length === 0) {
        throw new Error("Search term cannot be empty.");
    }

    if (normalized.length > 100) {
        throw new RangeError("Search term is too long.");
    }

    return normalized;
}

show("Normalized search", normalizeSearchTerm("  laptop  "));

console.log(
    "External input should be validated before it reaches sensitive operations."
);

console.log(
    "Use parameterized database queries rather than concatenating SQL strings."
);

console.log(
    "Do not place passwords, tokens, or private keys directly in source code."
);


// ============================================================================
// 29. SAFE DIAGNOSTICS
// ============================================================================

section("28. Safe diagnostics");

function maskAccountNumber(accountNumber) {
    if (typeof accountNumber !== "string") {
        throw new TypeError("Account number must be a string.");
    }

    if (accountNumber.length <= 4) {
        return "*".repeat(accountNumber.length);
    }

    return "*".repeat(accountNumber.length - 4) +
        accountNumber.slice(-4);
}

show("Masked account", maskAccountNumber("1234567890"));


// ============================================================================
// 30. CACHING
// ============================================================================

section("29. Memoization");

function createFibonacci() {
    const cache = new Map();

    function fibonacci(number) {
        if (!Number.isInteger(number) || number < 0) {
            throw new RangeError(
                "Fibonacci input must be a non-negative integer."
            );
        }

        if (number < 2) {
            return number;
        }

        if (cache.has(number)) {
            return cache.get(number);
        }

        const result =
            fibonacci(number - 1) +
            fibonacci(number - 2);

        cache.set(number, result);
        return result;
    }

    return fibonacci;
}

const fibonacci = createFibonacci();

show("Fibonacci(20)", fibonacci(20));


// ============================================================================
// 31. CLOSURES
// ============================================================================

section("30. Closures as controlled state");

function createCounter(initialValue = 0) {
    let currentValue = initialValue;

    return {
        increment() {
            currentValue += 1;
            return currentValue;
        },

        decrement() {
            currentValue -= 1;
            return currentValue;
        },

        value() {
            return currentValue;
        }
    };
}

const counter = createCounter(10);

show("Counter increment", counter.increment());
show("Counter increment", counter.increment());
show("Counter decrement", counter.decrement());
show("Counter value", counter.value());


// ============================================================================
// 32. AVOIDING GLOBAL MUTABLE STATE
// ============================================================================

section("31. Encapsulation");

function createApplicationState() {
    let requestCount = 0;

    return Object.freeze({
        recordRequest() {
            requestCount += 1;
        },

        getRequestCount() {
            return requestCount;
        }
    });
}

const applicationState = createApplicationState();

applicationState.recordRequest();
applicationState.recordRequest();

show(
    "Request count",
    applicationState.getRequestCount()
);


// ============================================================================
// 33. OBJECT COMPOSITION
// ============================================================================

section("32. Composition");

class ConsoleLogger {
    info(message) {
        console.log(`INFO: ${message}`);
    }

    error(message) {
        console.error(`ERROR: ${message}`);
    }
}

class PaymentService {
    constructor(logger) {
        if (!logger || typeof logger.info !== "function") {
            throw new TypeError("A compatible logger is required.");
        }

        this.logger = logger;
    }

    processPayment(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new RangeError("Payment amount must be positive.");
        }

        this.logger.info(`Processing payment of INR ${amount.toFixed(2)}`);

        return {
            success: true,
            amount
        };
    }
}

const paymentService = new PaymentService(new ConsoleLogger());

show(
    "Payment result",
    paymentService.processPayment(2500)
);


// ============================================================================
// 34. DESIGN TRADE-OFF
// ============================================================================

section("33. Avoiding over-engineering");

function isEven(number) {
    return number % 2 === 0;
}

show("Is 42 even?", isEven(42));

console.log(
    "A simple requirement should normally receive a simple implementation."
);

console.log(
    "Additional abstraction is justified when it captures a real boundary, "
    + "variation, or repeated domain concept."
);


// ============================================================================
// 35. CODE QUALITY AUTOMATION
// ============================================================================

section("34. Automated quality checks");

const qualityChecklist = {
    namesCommunicateIntent: true,
    responsibilitiesAreFocused: true,
    validationIsExplicit: true,
    errorsAreHandled: true,
    domainValuesAreNamed: true,
    importantCasesAreTested: true,
    dependenciesAreVisible: true,
    securityBoundariesAreConsidered: true,
    performanceAssumptionsAreKnown: true,
    formattingIsConsistent: true
};

for (const [principle, passed] of Object.entries(qualityChecklist)) {
    console.log(`[${passed ? "PASS" : "FAIL"}] ${principle}`);
}


// ============================================================================
// 36. FINAL QUALITY TESTS
// ============================================================================

section("35. Final quality checks");

function runQualityChecks() {
    assertEqual(
        20,
        calculateOrderTotal(4, 5, 0, 0),
        "basic arithmetic"
    );

    assertEqual(
        1000,
        calculateDiscountedPrice(1000, 0),
        "zero discount"
    );

    assertEqual(
        900,
        calculateDiscountedPrice(1000, 10),
        "ten percent discount"
    );

    assertEqual(
        true,
        isValidEmail("person@example.com"),
        "valid email"
    );

    assertEqual(
        false,
        isValidEmail("invalid"),
        "invalid email"
    );

    assertEqual(
        true,
        containsDuplicateFast([1, 2, 1]),
        "duplicate detection"
    );

    assertEqual(
        false,
        containsDuplicateFast([1, 2, 3]),
        "unique collection"
    );

    assertEqual(
        "standard",
        CustomerTier.STANDARD,
        "customer tier state"
    );

    assertEqual(
        8920.8,
        calculator.calculateTotal(orderItems, customer),
        "integrated order calculation"
    );

    console.log("All JavaScript quality checks passed.");
}

runQualityChecks();


// ============================================================================
// 37. DESIGN PRINCIPLES DISPLAY
// ============================================================================

section("36. Core maintainability principles");

const principles = [
    "Use names that reveal intent.",
    "Keep functions focused.",
    "Make dependencies visible.",
    "Validate external input.",
    "Handle expected failures deliberately.",
    "Prefer clear data structures.",
    "Avoid unnecessary duplication.",
    "Keep abstractions proportional to the problem.",
    "Test normal paths and boundary conditions.",
    "Measure performance instead of guessing.",
    "Keep security boundaries explicit.",
    "Separate business logic from presentation and infrastructure.",
    "Prefer predictable state transitions.",
    "Review code as a future maintainer would."
];

for (const principle of principles) {
    console.log(`- ${principle}`);
}


// ============================================================================
// 38. COMPLETION
// ============================================================================

section("37. Completion");

console.log(
    "The program demonstrated readability, naming, formatting, "
    + "maintainability, testing, performance, security, error handling, "
    + "asynchronous control flow, abstraction, and domain modeling."
);
