"use strict";

/*
 * Clean Code: Functions, Duplication, Comments, and Code Smells
 *
 * This file complements the Python implementation by emphasizing
 * JavaScript-specific function behavior, callbacks, closures, objects,
 * modules-by-convention, validation, asynchronous operations, and
 * maintainable application-level patterns.
 *
 * Runtime: Node.js
 */


// ============================================================================
// 1. BASIC UTILITIES
// ============================================================================

function section(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function subsection(title) {
    console.log(`\n--- ${title} ---`);
}


// ============================================================================
// 2. FUNCTIONS AND SINGLE RESPONSIBILITY
// ============================================================================

// Poor design: several responsibilities are combined in one function.
function badCalculateOrderTotal(items, taxRate, discountCode) {
    let total = 0;

    for (const item of items) {
        if (!item.price || item.quantity < 0) {
            throw new Error("Invalid item");
        }

        total += item.price * item.quantity;
    }

    if (discountCode === "SAVE10") {
        total *= 0.9;
    } else if (discountCode === "SAVE20") {
        total *= 0.8;
    }

    total += total * taxRate;
    return Number(total.toFixed(2));
}


// Refactored implementation.
function validateItem(item) {
    if (typeof item !== "object" || item === null) {
        throw new TypeError("Item must be an object.");
    }

    if (typeof item.price !== "number" || Number.isNaN(item.price)) {
        throw new TypeError("Price must be a number.");
    }

    if (!Number.isInteger(item.quantity)) {
        throw new TypeError("Quantity must be an integer.");
    }

    if (item.price < 0) {
        throw new RangeError("Price cannot be negative.");
    }

    if (item.quantity < 0) {
        throw new RangeError("Quantity cannot be negative.");
    }
}


function calculateSubtotal(items) {
    return items.reduce((subtotal, item) => {
        validateItem(item);
        return subtotal + item.price * item.quantity;
    }, 0);
}


function getDiscountRate(discountCode, subtotal) {
    const rates = {
        SAVE10: 0.10,
        SAVE20: 0.20,
    };

    const explicitRate = rates[discountCode] ?? 0;
    const volumeRate = subtotal > 1000 ? 0.05 : 0;

    return Math.max(explicitRate, volumeRate);
}


function calculateDiscount(subtotal, discountCode) {
    return subtotal * getDiscountRate(discountCode, subtotal);
}


function calculateTax(amount, taxRate) {
    if (taxRate < 0) {
        throw new RangeError("Tax rate cannot be negative.");
    }

    return amount * taxRate;
}


function calculateOrderTotal(items, taxRate, discountCode = null) {
    const subtotal = calculateSubtotal(items);
    const discount = calculateDiscount(subtotal, discountCode);
    const taxableAmount = subtotal - discount;
    const tax = calculateTax(taxableAmount, taxRate);

    return Number((taxableAmount + tax).toFixed(2));
}


// ============================================================================
// 3. PURE FUNCTIONS
// ============================================================================

function add(a, b) {
    return a + b;
}


function percentageOf(value, percentage) {
    if (percentage < 0 || percentage > 100) {
        throw new RangeError("Percentage must be between 0 and 100.");
    }

    return value * percentage / 100;
}


// ============================================================================
// 4. DUPLICATION AND SINGLE SOURCE OF TRUTH
// ============================================================================

function lineTotal(price, quantity) {
    if (price < 0 || quantity < 0) {
        throw new RangeError("Price and quantity cannot be negative.");
    }

    return price * quantity;
}


function calculateInvoice(items) {
    return items.reduce(
        (total, item) => total + lineTotal(item.price, item.quantity),
        0
    );
}


function calculateCart(items) {
    return items.reduce(
        (total, item) => total + lineTotal(item.price, item.quantity),
        0
    );
}


// ============================================================================
// 5. NAMING AND BOOLEAN EXPRESSIONS
// ============================================================================

function isAdult(age) {
    return age >= 18;
}


function canPlaceOrder(age, accountIsActive) {
    return isAdult(age) && accountIsActive;
}


function eligibilityMessage(age, accountIsActive) {
    if (canPlaceOrder(age, accountIsActive)) {
        return "Order permitted.";
    }

    return "Order not permitted.";
}


// ============================================================================
// 6. GUARD CLAUSES
// ============================================================================

function calculateShippingCost(weightKg, destination) {
    if (weightKg < 0) {
        throw new RangeError("Weight cannot be negative.");
    }

    if (!destination || destination.trim() === "") {
        throw new Error("Destination is required.");
    }

    if (weightKg === 0) {
        return 0;
    }

    if (destination.toUpperCase() === "LOCAL") {
        return Number((5 + weightKg * 1.5).toFixed(2));
    }

    return Number((10 + weightKg * 3).toFixed(2));
}


// ============================================================================
// 7. COMMENTS THAT EXPLAIN INTENT
// ============================================================================

function calculateNetRevenue(grossRevenue, refunds) {
    /*
     * Refunds must be removed before revenue is sent to the finance report.
     * The comment explains a business rule rather than describing subtraction.
     */
    return grossRevenue - refunds;
}


// ============================================================================
// 8. MAGIC NUMBERS REPLACED WITH NAMED CONSTANTS
// ============================================================================

const TAX_RATE = 0.18;
const FREE_SHIPPING_THRESHOLD = 1000;
const PREMIUM_DISCOUNT_RATE = 0.15;


function calculateOrderShipping(orderValue) {
    if (orderValue < 0) {
        throw new RangeError("Order value cannot be negative.");
    }

    return orderValue >= FREE_SHIPPING_THRESHOLD ? 0 : 80;
}


// ============================================================================
// 9. OBJECTS AND COHESION
// ============================================================================

class Product {
    constructor(productId, name, price) {
        if (!productId.trim()) {
            throw new Error("Product ID is required.");
        }

        if (!name.trim()) {
            throw new Error("Product name is required.");
        }

        if (price < 0) {
            throw new RangeError("Product price cannot be negative.");
        }

        this.productId = productId;
        this.name = name;
        this.price = price;
    }
}


class CartLine {
    constructor(product, quantity) {
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new RangeError("Quantity must be a positive integer.");
        }

        this.product = product;
        this.quantity = quantity;
    }

    get total() {
        return this.product.price * this.quantity;
    }
}


class ShoppingCart {
    constructor() {
        this.lines = [];
    }

    add(product, quantity = 1) {
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new RangeError("Quantity must be positive.");
        }

        const existingLine = this.lines.find(
            line => line.product.productId === product.productId
        );

        if (existingLine) {
            existingLine.quantity += quantity;
            return;
        }

        this.lines.push(new CartLine(product, quantity));
    }

    subtotal() {
        return this.lines.reduce(
            (total, line) => total + line.total,
            0
        );
    }

    itemCount() {
        return this.lines.reduce(
            (count, line) => count + line.quantity,
            0
        );
    }

    isEmpty() {
        return this.lines.length === 0;
    }
}


// ============================================================================
// 10. VALIDATION HELPERS
// ============================================================================

function requireNonEmpty(value, fieldName) {
    if (typeof value !== "string" || value.trim() === "") {
        throw new Error(`${fieldName} cannot be empty.`);
    }

    return value.trim();
}


function normalizeEmail(email) {
    return requireNonEmpty(email, "Email").toLowerCase();
}


function isValidEmail(email) {
    const normalizedEmail = normalizeEmail(email);
    return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(normalizedEmail);
}


function createUser(name, email) {
    const cleanName = requireNonEmpty(name, "Name");
    const cleanEmail = normalizeEmail(email);

    if (!isValidEmail(cleanEmail)) {
        throw new Error("Invalid email address.");
    }

    return {
        name: cleanName,
        email: cleanEmail,
    };
}


// ============================================================================
// 11. HIGHER-ORDER FUNCTIONS
// ============================================================================

function applyDiscount(price, discountFunction) {
    if (price < 0) {
        throw new RangeError("Price cannot be negative.");
    }

    if (typeof discountFunction !== "function") {
        throw new TypeError("A discount function is required.");
    }

    return discountFunction(price);
}


const tenPercentDiscount = price => price * 0.90;
const twentyPercentDiscount = price => price * 0.80;


// ============================================================================
// 12. CLOSURES
// ============================================================================

function createPercentageDiscount(rate) {
    if (rate < 0 || rate > 1) {
        throw new RangeError("Rate must be between 0 and 1.");
    }

    /*
     * The returned function retains access to rate after this function ends.
     * That retained environment is a closure.
     */
    return function applyStoredDiscount(price) {
        return price * (1 - rate);
    };
}


const studentDiscount = createPercentageDiscount(0.10);


// ============================================================================
// 13. ARRAY TRANSFORMATIONS
// ============================================================================

function calculateActiveEmployeeSalaries(employees) {
    return employees
        .filter(employee => employee.active)
        .map(employee => employee.salary * 12);
}


function totalValues(values) {
    return values.reduce((total, value) => total + value, 0);
}


// ============================================================================
// 14. ERROR TYPES
// ============================================================================

class PaymentError extends Error {
    constructor(message) {
        super(message);
        this.name = "PaymentError";
    }
}


class InvalidAmountError extends PaymentError {
    constructor(message) {
        super(message);
        this.name = "InvalidAmountError";
    }
}


class PaymentDeclinedError extends PaymentError {
    constructor(message) {
        super(message);
        this.name = "PaymentDeclinedError";
    }
}


function chargePayment(amount, balance) {
    if (amount <= 0) {
        throw new InvalidAmountError("Payment amount must be positive.");
    }

    if (amount > balance) {
        throw new PaymentDeclinedError("Insufficient balance.");
    }

    return `Payment approved for ${amount.toFixed(2)}`;
}


// ============================================================================
// 15. DEPENDENCY INJECTION
// ============================================================================

class TaxService {
    constructor(rate) {
        if (rate < 0) {
            throw new RangeError("Tax rate cannot be negative.");
        }

        this.rate = rate;
    }

    calculate(amount) {
        return amount * this.rate;
    }
}


class CheckoutService {
    constructor(taxService) {
        if (!taxService || typeof taxService.calculate !== "function") {
            throw new TypeError("A compatible tax service is required.");
        }

        this.taxService = taxService;
    }

    total(subtotal) {
        if (subtotal < 0) {
            throw new RangeError("Subtotal cannot be negative.");
        }

        return subtotal + this.taxService.calculate(subtotal);
    }
}


// A test double can be supplied without changing CheckoutService.
const zeroTaxService = {
    calculate() {
        return 0;
    },
};


// ============================================================================
// 16. ASYNCHRONOUS FUNCTIONS
// ============================================================================

function fakeUserRepository(userId) {
    return new Promise((resolve, reject) => {
        setTimeout(() => {
            if (!userId) {
                reject(new Error("User ID is required."));
                return;
            }

            resolve({
                id: userId,
                name: "Example User",
                active: true,
            });
        }, 20);
    });
}


async function loadActiveUser(userId) {
    const user = await fakeUserRepository(userId);

    if (!user.active) {
        throw new Error("User account is inactive.");
    }

    return user;
}


// ============================================================================
// 17. CODE SMELL CATALOGUE
// ============================================================================

const codeSmells = [
    {
        name: "Long Function",
        symptom: "One function performs many unrelated tasks.",
        response: "Extract focused functions.",
    },
    {
        name: "Duplicate Code",
        symptom: "The same business knowledge exists in several places.",
        response: "Centralize genuinely shared knowledge.",
    },
    {
        name: "Long Parameter List",
        symptom: "A function needs many loosely related arguments.",
        response: "Group coherent data into an object.",
    },
    {
        name: "Deep Nesting",
        symptom: "Several levels of conditionals hide the main path.",
        response: "Use guard clauses and smaller functions.",
    },
    {
        name: "Magic Numbers",
        symptom: "Unexplained constants are scattered throughout code.",
        response: "Name meaningful business constants.",
    },
    {
        name: "God Object",
        symptom: "One class owns unrelated responsibilities.",
        response: "Split cohesive responsibilities.",
    },
    {
        name: "Dead Code",
        symptom: "Unused code remains after requirements change.",
        response: "Remove it after verifying it is unused.",
    },
    {
        name: "Comment Smell",
        symptom: "Comments explain confusing code instead of important intent.",
        response: "Improve names and structure first.",
    },
];


// ============================================================================
// 18. REFACTORING CONDITIONALS
// ============================================================================

const SHIPPING_ZONE_RATES = Object.freeze({
    LOCAL: 1,
    NATIONAL: 2,
    INTERNATIONAL: 5,
});


function shippingPrice(weight, zone) {
    if (weight < 0) {
        throw new RangeError("Weight cannot be negative.");
    }

    const normalizedZone = zone.trim().toUpperCase();
    const rate = SHIPPING_ZONE_RATES[normalizedZone];

    if (rate === undefined) {
        throw new Error(`Unknown shipping zone: ${zone}`);
    }

    return 5 + weight * rate;
}


// ============================================================================
// 19. TESTING
// ============================================================================

function assertEqual(actual, expected, description) {
    if (!Object.is(actual, expected)) {
        throw new Error(
            `${description}: expected ${expected}, received ${actual}`
        );
    }

    console.log(`PASS: ${description}`);
}


function assertThrows(operation, expectedErrorType, description) {
    try {
        operation();
    } catch (error) {
        if (!(error instanceof expectedErrorType)) {
            throw new Error(
                `${description}: wrong error type ${error.constructor.name}`
            );
        }

        console.log(`PASS: ${description}`);
        return;
    }

    throw new Error(`${description}: expected an exception.`);
}


function runTests() {
    section("Tests");

    assertEqual(
        calculateSubtotal([
            { price: 100, quantity: 2 },
            { price: 50, quantity: 1 },
        ]),
        250,
        "subtotal"
    );

    assertEqual(
        calculateOrderTotal(
            [{ price: 100, quantity: 2 }],
            0.10,
            "SAVE10"
        ),
        198,
        "order total"
    );

    assertEqual(
        normalizeEmail(" USER@EXAMPLE.COM "),
        "user@example.com",
        "email normalization"
    );

    assertEqual(
        isValidEmail("person@example.com"),
        true,
        "valid email"
    );

    assertEqual(
        isValidEmail("bad-email"),
        false,
        "invalid email"
    );

    assertEqual(
        studentDiscount(1000),
        900,
        "closure discount"
    );

    assertThrows(
        () => calculateSubtotal([{ price: -1, quantity: 1 }]),
        RangeError,
        "negative price"
    );

    assertThrows(
        () => chargePayment(0, 100),
        InvalidAmountError,
        "invalid payment amount"
    );

    assertThrows(
        () => chargePayment(200, 100),
        PaymentDeclinedError,
        "declined payment"
    );
}


// ============================================================================
// 20. REALISTIC REPORT GENERATION
// ============================================================================

function isValidEmployee(employee) {
    return (
        typeof employee.name === "string" &&
        employee.name.trim() !== "" &&
        typeof employee.salary === "number" &&
        employee.salary >= 0
    );
}


function annualSalary(employee) {
    return employee.salary * 12;
}


function formatEmployeeReportLine(employee) {
    return `${employee.name}: ${annualSalary(employee).toFixed(2)}`;
}


function employeeReport(employees) {
    return employees
        .filter(employee => employee.active && isValidEmployee(employee))
        .map(formatEmployeeReportLine)
        .join("\n");
}


// ============================================================================
// 21. PERFORMANCE-AWARE UNIQUE VALUES
// ============================================================================

function slowUniqueValues(values) {
    const result = [];

    for (const value of values) {
        if (!result.includes(value)) {
            result.push(value);
        }
    }

    return result;
}


function fastUniqueValues(values) {
    const seen = new Set();
    const result = [];

    for (const value of values) {
        if (!seen.has(value)) {
            seen.add(value);
            result.push(value);
        }
    }

    return result;
}


function benchmark(functionToMeasure, values) {
    const start = process.hrtime.bigint();
    functionToMeasure(values);
    const end = process.hrtime.bigint();

    return Number(end - start) / 1_000_000;
}


// ============================================================================
// 22. MAIN APPLICATION DEMONSTRATION
// ============================================================================

async function main() {
    section("Clean Code: Functions, Duplication, Comments, and Code Smells");

    subsection("Focused functions");

    const items = [
        { price: 250, quantity: 2 },
        { price: 100, quantity: 1 },
    ];

    console.log(
        "Poor-style total:",
        badCalculateOrderTotal(items, 0.18, "SAVE10")
    );

    console.log(
        "Refactored total:",
        calculateOrderTotal(items, 0.18, "SAVE10")
    );

    subsection("Pure functions");
    console.log("10 + 20 =", add(10, 20));
    console.log("20% of 500 =", percentageOf(500, 20));

    subsection("Duplication");
    console.log("Invoice:", calculateInvoice(items));
    console.log("Cart:", calculateCart(items));

    subsection("Boolean clarity");
    console.log("Eligibility:", eligibilityMessage(25, true));

    subsection("Guard clauses");
    console.log("Shipping:", calculateShippingCost(5, "LOCAL"));

    subsection("Named constants");
    console.log("Free shipping:", calculateOrderShipping(1500));
    console.log("Tax rate:", TAX_RATE);

    subsection("Cohesive classes");
    const keyboard = new Product("P001", "Keyboard", 2500);
    const cart = new ShoppingCart();

    cart.add(keyboard, 2);

    console.log("Cart subtotal:", cart.subtotal());
    console.log("Cart item count:", cart.itemCount());

    subsection("Validation");
    console.log(
        "Created user:",
        createUser("Atul Pandey", " USER@EXAMPLE.COM ")
    );

    subsection("Higher-order functions");
    console.log(
        "10% discount:",
        applyDiscount(1000, tenPercentDiscount)
    );

    console.log(
        "20% discount:",
        applyDiscount(1000, twentyPercentDiscount)
    );

    subsection("Dependency injection");
    const productionCheckout = new CheckoutService(new TaxService(0.18));
    console.log("Production total:", productionCheckout.total(1000));

    const testCheckout = new CheckoutService(zeroTaxService);
    console.log("Test total:", testCheckout.total(1000));

    subsection("Asynchronous function");
    try {
        console.log("Loaded user:", await loadActiveUser("U001"));
    } catch (error) {
        console.error("Unexpected error:", error.message);
    }

    subsection("Expected asynchronous failure");
    try {
        await loadActiveUser("");
    } catch (error) {
        console.log("Expected failure:", error.message);
    }

    subsection("Code smells");

    for (const smell of codeSmells) {
        console.log(`\n${smell.name}`);
        console.log(`  Symptom: ${smell.symptom}`);
        console.log(`  Refactoring direction: ${smell.response}`);
    }

    subsection("Refactored report");

    const employees = [
        { name: "Asha", salary: 50000, active: true },
        { name: "Ravi", salary: 60000, active: false },
        { name: "Neha", salary: 70000, active: true },
        { name: "", salary: 50000, active: true },
    ];

    console.log(employeeReport(employees));

    subsection("Performance comparison");

    const values = Array.from({ length: 6000 }, (_, index) => index % 3000);

    console.log(
        "Slow implementation:",
        benchmark(slowUniqueValues, values).toFixed(3),
        "ms"
    );

    console.log(
        "Set-based implementation:",
        benchmark(fastUniqueValues, values).toFixed(3),
        "ms"
    );

    console.log(
        "Unique values:",
        fastUniqueValues(values).length
    );

    runTests();

    section("Clean-code principles demonstrated");

    const principles = [
        "Keep functions focused on one coherent responsibility.",
        "Prefer names that communicate business meaning.",
        "Centralize shared knowledge when duplication represents the same rule.",
        "Do not remove all repetition mechanically when concepts have different reasons to change.",
        "Use comments to explain intent, constraints, or non-obvious decisions.",
        "Use guard clauses to reduce unnecessary nesting.",
        "Prefer explicit validation at important boundaries.",
        "Use exceptions when callers need to distinguish failure conditions.",
        "Use dependency injection to reduce hard-coded dependencies.",
        "Measure performance rather than assuming that shorter code is faster.",
        "Treat code smells as signals requiring engineering judgment.",
        "Refactor in small behavior-preserving steps.",
    ];

    for (const principle of principles) {
        console.log(`[x] ${principle}`);
    }
}


main().catch(error => {
    console.error("Application failure:", error);
    process.exitCode = 1;
});
