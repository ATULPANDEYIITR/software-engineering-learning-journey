/*
 * Debugging: Debugging Workflow, Breakpoints, Logs, and Root Cause Analysis
 * ==========================================================================
 *
 * This standalone JavaScript file demonstrates debugging from beginner
 * concepts through practical application:
 *
 * - debugging terminology
 * - systematic workflow
 * - reproducibility and minimal examples
 * - console diagnostics
 * - debugger breakpoints
 * - conditional breakpoints
 * - assertions
 * - validation
 * - exceptions and stack traces
 * - structured diagnostic information
 * - asynchronous debugging
 * - state inspection
 * - root cause analysis
 * - fault isolation
 * - regression testing
 * - performance measurement
 * - security-aware logging
 * - a realistic order-processing case study
 *
 * It uses standard JavaScript APIs and runs in Node.js without npm packages.
 */

"use strict";


// ============================================================================
// 1. BASIC DEBUGGING TERMINOLOGY
// ============================================================================

function printHeading(title) {
    console.log("\n" + "=".repeat(78));
    console.log(title);
    console.log("=".repeat(78));
}

function debuggingTerminology() {
    printHeading("1. Debugging Terminology");

    const terms = {
        bug: "A defect that causes behavior to differ from the intended behavior.",
        failure: "An observable event showing that expected behavior was not achieved.",
        symptom: "The visible effect of an underlying problem.",
        exception: "A runtime object representing an abnormal condition.",
        breakpoint: "A location where a debugger pauses execution for inspection.",
        log: "A diagnostic record describing an application event.",
        rootCause: "The underlying condition responsible for the observed failure.",
        regression: "A previously working behavior that becomes broken after a change."
    };

    for (const [term, definition] of Object.entries(terms)) {
        console.log(`${term.padEnd(14)} -> ${definition}`);
    }
}


// ============================================================================
// 2. SYSTEMATIC WORKFLOW
// ============================================================================

function debuggingWorkflow() {
    printHeading("2. Systematic Debugging Workflow");

    const workflow = [
        "Observe the failure.",
        "Record exact inputs and expected behavior.",
        "Reproduce the failure.",
        "Minimize the failing case.",
        "Read the stack trace.",
        "Form explicit hypotheses.",
        "Collect evidence.",
        "Isolate the faulty component.",
        "Identify the root cause.",
        "Implement a focused fix.",
        "Add a regression test.",
        "Run related tests.",
        "Check for side effects and performance changes."
    ];

    workflow.forEach((step, index) => {
        console.log(`${index + 1}. ${step}`);
    });
}


// ============================================================================
// 3. VALIDATION AND ASSERTIONS
// ============================================================================

function calculateDiscountedPrice(price, discountPercent) {
    if (!Number.isFinite(price)) {
        throw new TypeError("Price must be a finite number.");
    }

    if (price < 0) {
        throw new RangeError("Price cannot be negative.");
    }

    if (!Number.isFinite(discountPercent) ||
        discountPercent < 0 ||
        discountPercent > 100) {
        throw new RangeError("Discount must be between 0 and 100.");
    }

    const finalPrice = price * (1 - discountPercent / 100);

    // Assertions are appropriate for internal assumptions.
    console.assert(
        finalPrice >= 0,
        "Invariant violated: final price must not be negative."
    );

    return finalPrice;
}

function validationDemo() {
    printHeading("3. Validation and Assertions");

    console.log(
        "Normal calculation:",
        calculateDiscountedPrice(100, 20)
    );

    try {
        calculateDiscountedPrice(-10, 20);
    } catch (error) {
        console.error("Validation error:", error.message);
    }

    try {
        calculateDiscountedPrice(100, 150);
    } catch (error) {
        console.error("Validation error:", error.message);
    }
}


// ============================================================================
// 4. BREAKPOINTS
// ============================================================================

function calculateStatistics(values) {
    if (!Array.isArray(values) || values.length === 0) {
        throw new Error("A non-empty array is required.");
    }

    const total = values.reduce((sum, value) => sum + value, 0);
    const average = total / values.length;
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);

    /*
     * Uncomment debugger when interactive inspection is desired.
     *
     * At this point an IDE or Node inspector can inspect:
     * values, total, average, minimum, and maximum.
     */
    // debugger;

    return {
        count: values.length,
        total,
        average,
        minimum,
        maximum
    };
}

function breakpointDemo() {
    printHeading("4. Breakpoints");

    const result = calculateStatistics([10, 20, 30, 40]);
    console.log("Statistics:", result);

    console.log(
        "Place a debugger statement where execution should pause.",
        "\nUse the runtime debugger to inspect variables and call frames."
    );
}


// ============================================================================
// 5. CONDITIONAL BREAKPOINTS
// ============================================================================

function processMeasurements(measurements) {
    return measurements.map((measurement) => {
        /*
         * In an IDE, a breakpoint on the following statement can be made
         * conditional with: measurement < 0
         */
        if (measurement < 0) {
            console.warn("Unexpected negative measurement:", measurement);
        }

        return Number((measurement * 1.1).toFixed(2));
    });
}

function conditionalBreakpointDemo() {
    printHeading("5. Conditional Breakpoints");

    const values = processMeasurements([10, 15, -5, 20]);
    console.log("Processed values:", values);
}


// ============================================================================
// 6. LOGGING
// ============================================================================

function loggingDemo() {
    printHeading("6. Logging");

    console.debug("Detailed diagnostic information.");
    console.info("Normal application event.");
    console.warn("Potential problem detected.");
    console.error("Operation failed.");

    const diagnosticContext = {
        operation: "calculate-order-total",
        orderId: "ORD-1001",
        itemCount: 3
    };

    console.info("Diagnostic context:", diagnosticContext);
}


// ============================================================================
// 7. STACK TRACES
// ============================================================================

function divideNumbers(first, second) {
    if (second === 0) {
        throw new Error("Division by zero is not permitted.");
    }

    return first / second;
}

function performDivision() {
    return divideNumbers(10, 0);
}

function stackTraceDemo() {
    printHeading("7. Exceptions and Stack Traces");

    try {
        performDivision();
    } catch (error) {
        console.error("Message:", error.message);
        console.error("Name:", error.name);
        console.error("Stack:\n" + error.stack);
    }
}


// ============================================================================
// 8. ASYNCHRONOUS DEBUGGING
// ============================================================================

function simulateExternalService() {
    return new Promise((resolve) => {
        setTimeout(() => {
            resolve({
                status: 200,
                payload: { taxRate: 0.18 }
            });
        }, 30);
    });
}

async function asynchronousWorkflow() {
    console.debug("Starting asynchronous operation.");

    const response = await simulateExternalService();

    console.debug(
        "Received asynchronous response:",
        response.status
    );

    if (response.status !== 200) {
        throw new Error("External service returned an unexpected status.");
    }

    return response.payload.taxRate;
}

async function asynchronousDebuggingDemo() {
    printHeading("8. Asynchronous Debugging");

    try {
        const taxRate = await asynchronousWorkflow();
        console.log("Tax rate:", taxRate);
    } catch (error) {
        console.error("Async failure:", error);
    }
}


// ============================================================================
// 9. FAULT ISOLATION
// ============================================================================

function parseAmount(rawAmount) {
    const amount = Number(String(rawAmount).trim());

    if (!Number.isFinite(amount)) {
        throw new TypeError("Amount is not a valid number.");
    }

    return amount;
}

function applyTax(amount, taxRate) {
    if (amount < 0) {
        throw new RangeError("Amount cannot be negative.");
    }

    if (taxRate < 0 || taxRate > 1) {
        throw new RangeError("Tax rate must be between 0 and 1.");
    }

    return amount * (1 + taxRate);
}

function roundCurrency(amount) {
    return Math.round((amount + Number.EPSILON) * 100) / 100;
}

function pricingPipeline(rawAmount, taxRate) {
    const amount = parseAmount(rawAmount);
    const taxedAmount = applyTax(amount, taxRate);
    return roundCurrency(taxedAmount);
}

function faultIsolationDemo() {
    printHeading("9. Fault Isolation");

    try {
        const result = pricingPipeline("100.00", 0.18);
        console.log("Pipeline result:", result);
    } catch (error) {
        console.error("Pipeline failure:", error.message);
    }

    /*
     * Debugging each stage independently makes the faulty boundary visible.
     */
    const amount = parseAmount("100.00");
    console.log("Stage 1:", amount);

    const taxedAmount = applyTax(amount, 0.18);
    console.log("Stage 2:", taxedAmount);

    const finalAmount = roundCurrency(taxedAmount);
    console.log("Stage 3:", finalAmount);
}


// ============================================================================
// 10. ROOT CAUSE ANALYSIS
// ============================================================================

function rootCauseAnalysisDemo() {
    printHeading("10. Root Cause Analysis");

    const incident = {
        symptom: "Final order price is lower than expected.",
        evidence: [
            "Product prices match the catalog.",
            "Tax calculation matches the configured tax rate.",
            "Discount operation executes twice.",
            "Removing the second discount operation restores the expected price."
        ],
        hypotheses: [
            "Incorrect catalog price",
            "Incorrect tax rate",
            "Duplicate discount application",
            "Rounding problem"
        ]
    };

    console.log("Symptom:", incident.symptom);
    console.log("Evidence:");

    incident.evidence.forEach((item) => {
        console.log(" -", item);
    });

    console.log("\nHypotheses:");
    incident.hypotheses.forEach((hypothesis) => {
        console.log(" -", hypothesis);
    });

    console.log(
        "\nEvidence-supported root cause:",
        "The discount operation is applied twice."
    );

    console.log(
        "Corrective action:",
        "Centralize discount application and add a regression test."
    );
}


// ============================================================================
// 11. HYPOTHESIS-DRIVEN DEBUGGING
// ============================================================================

function hypothesisDrivenDebugging() {
    printHeading("11. Hypothesis-Driven Debugging");

    const hypotheses = [
        {
            name: "Invalid input",
            test: "Validate the raw input before transformation."
        },
        {
            name: "Incorrect transformation",
            test: "Inspect input and output at the transformation boundary."
        },
        {
            name: "Unexpected state mutation",
            test: "Compare state before and after the operation."
        },
        {
            name: "External dependency failure",
            test: "Use a controlled response and compare behavior."
        }
    ];

    hypotheses.forEach((hypothesis, index) => {
        console.log(`${index + 1}. ${hypothesis.name}`);
        console.log(`   Evidence test: ${hypothesis.test}`);
    });
}


// ============================================================================
// 12. STATE INSPECTION
// ============================================================================

class ShoppingCart {
    constructor(items = []) {
        this.items = [...items];
    }

    subtotal() {
        return this.items.reduce((sum, price) => sum + price, 0);
    }

    removeItem(index) {
        if (!Number.isInteger(index)) {
            throw new TypeError("Index must be an integer.");
        }

        if (index < 0 || index >= this.items.length) {
            throw new RangeError("Index is outside the cart.");
        }

        return this.items.splice(index, 1)[0];
    }
}

function stateInspectionDemo() {
    printHeading("12. State Inspection");

    const cart = new ShoppingCart([100, 50, 25]);

    const before = [...cart.items];
    const removed = cart.removeItem(1);
    const after = [...cart.items];

    console.log("Before:", before);
    console.log("Removed:", removed);
    console.log("After:", after);
    console.log("Subtotal:", cart.subtotal());

    if (after.length !== before.length - 1) {
        console.error("Unexpected state transition.");
    }
}


// ============================================================================
// 13. REALISTIC ORDER SYSTEM
// ============================================================================

class OrderItem {
    constructor(productId, unitPrice, quantity) {
        this.productId = productId;
        this.unitPrice = unitPrice;
        this.quantity = quantity;
    }

    total() {
        if (!Number.isFinite(this.unitPrice) || this.unitPrice < 0) {
            throw new RangeError("Unit price must be non-negative.");
        }

        if (!Number.isInteger(this.quantity) || this.quantity <= 0) {
            throw new RangeError("Quantity must be a positive integer.");
        }

        return this.unitPrice * this.quantity;
    }
}

class Order {
    constructor(orderId, items, discountPercent = 0) {
        this.orderId = orderId;
        this.items = [...items];
        this.discountPercent = discountPercent;
    }

    subtotal() {
        return this.items.reduce(
            (total, item) => total + item.total(),
            0
        );
    }

    total() {
        if (
            !Number.isFinite(this.discountPercent) ||
            this.discountPercent < 0 ||
            this.discountPercent > 100
        ) {
            throw new RangeError("Invalid discount percentage.");
        }

        const subtotal = this.subtotal();

        const discountedTotal =
            subtotal * (1 - this.discountPercent / 100);

        console.assert(
            discountedTotal >= 0,
            "Order total invariant violated."
        );

        return roundCurrency(discountedTotal);
    }
}

function orderCaseStudy() {
    printHeading("13. Realistic Order-Processing Case Study");

    const order = new Order(
        "ORD-1001",
        [
            new OrderItem("BOOK-01", 500, 2),
            new OrderItem("COURSE-01", 1200, 1)
        ],
        10
    );

    console.info("Processing order", {
        orderId: order.orderId,
        itemCount: order.items.length
    });

    try {
        const subtotal = order.subtotal();
        const total = order.total();

        console.debug("Pricing details", {
            orderId: order.orderId,
            subtotal,
            total
        });

        console.log("Subtotal:", subtotal.toFixed(2));
        console.log("Total:", total.toFixed(2));
    } catch (error) {
        console.error(
            "Order processing failed:",
            order.orderId,
            error
        );
    }
}


// ============================================================================
// 14. REGRESSION TESTS
// ============================================================================

function calculateOrderTotal(prices, discountPercent = 0) {
    if (!Array.isArray(prices)) {
        throw new TypeError("Prices must be an array.");
    }

    if (
        !Number.isFinite(discountPercent) ||
        discountPercent < 0 ||
        discountPercent > 100
    ) {
        throw new RangeError("Invalid discount percentage.");
    }

    if (prices.some((price) => !Number.isFinite(price) || price < 0)) {
        throw new RangeError("All prices must be finite and non-negative.");
    }

    const subtotal = prices.reduce((sum, price) => sum + price, 0);

    return roundCurrency(
        subtotal * (1 - discountPercent / 100)
    );
}

function runTest(name, testFunction) {
    try {
        const result = testFunction();

        if (!result) {
            throw new Error("Assertion returned false.");
        }

        console.log(`PASS: ${name}`);
        return true;
    } catch (error) {
        console.error(`FAIL: ${name}`, error.message);
        return false;
    }
}

function regressionTests() {
    printHeading("14. Regression Tests");

    const tests = [
        [
            "empty order",
            () => calculateOrderTotal([]) === 0
        ],
        [
            "normal order",
            () => calculateOrderTotal([100, 50]) === 150
        ],
        [
            "discount",
            () => calculateOrderTotal([100], 20) === 80
        ],
        [
            "full discount",
            () => calculateOrderTotal([100], 100) === 0
        ]
    ];

    let passed = 0;

    for (const [name, test] of tests) {
        if (runTest(name, test)) {
            passed++;
        }
    }

    console.log(`${passed}/${tests.length} tests passed.`);
}


// ============================================================================
// 15. EDGE CASES
// ============================================================================

function edgeCasesDemo() {
    printHeading("15. Edge Cases");

    const cases = [
        {
            description: "empty order",
            prices: []
        },
        {
            description: "single item",
            prices: [42]
        },
        {
            description: "duplicate values",
            prices: [5, 5, 5]
        },
        {
            description: "large values",
            prices: [1_000_000_000, 1_000_000_000]
        },
        {
            description: "decimal values",
            prices: [0.1, 0.2]
        }
    ];

    for (const testCase of cases) {
        try {
            console.log(
                `${testCase.description}:`,
                calculateOrderTotal(testCase.prices)
            );
        } catch (error) {
            console.error(
                `${testCase.description}:`,
                error.message
            );
        }
    }

    console.log("0.1 + 0.2 =", 0.1 + 0.2);
    console.log(
        "Rounded currency:",
        roundCurrency(0.1 + 0.2)
    );
}


// ============================================================================
// 16. PERFORMANCE MEASUREMENT
// ============================================================================

function performanceDemo() {
    printHeading("16. Performance Debugging");

    const values = Array.from(
        { length: 100_000 },
        (_, index) => index + 1
    );

    const start = performance.now();

    const result = values.reduce(
        (sum, value) => sum + value,
        0
    );

    const elapsed = performance.now() - start;

    console.log("Result:", result);
    console.log(`Elapsed time: ${elapsed.toFixed(4)} ms`);

    console.log(
        "A timing measurement identifies cost, but additional evidence",
        "is needed to explain the cause of a performance problem."
    );
}


// ============================================================================
// 17. SECURITY-AWARE DIAGNOSTICS
// ============================================================================

function securityLoggingDemo() {
    printHeading("17. Security Considerations");

    const diagnosticContext = {
        userId: "user-12345",
        transactionId: "txn-789"
    };

    console.info("Safe diagnostic context:", diagnosticContext);

    /*
     * Do not log passwords, authentication tokens, private keys, session
     * cookies, or complete payment-card information merely because debugging
     * would be easier with them.
     */
    console.warn(
        "Diagnostic data should be minimized and protected."
    );
}


// ============================================================================
// 18. ERROR WRAPPING
// ============================================================================

class ConfigurationError extends Error {
    constructor(message, cause) {
        super(message, { cause });
        this.name = "ConfigurationError";
    }
}

function loadTaxRate(rawValue) {
    try {
        const value = Number(rawValue);

        if (!Number.isFinite(value)) {
            throw new TypeError("Tax rate is not numeric.");
        }

        if (value < 0 || value > 1) {
            throw new RangeError("Tax rate must be between 0 and 1.");
        }

        return value;
    } catch (error) {
        throw new ConfigurationError(
            `Invalid tax configuration: ${rawValue}`,
            error
        );
    }
}

function errorWrappingDemo() {
    printHeading("18. Error Wrapping");

    try {
        loadTaxRate("invalid");
    } catch (error) {
        console.error("Application error:", error.message);

        if (error.cause) {
            console.error(
                "Underlying cause:",
                error.cause.message
            );
        }
    }
}


// ============================================================================
// 19. DEBUGGING CHECKLIST
// ============================================================================

function debuggingChecklist() {
    printHeading("19. Debugging Checklist");

    const checklist = [
        "Can the failure be reproduced?",
        "What exact input produces it?",
        "What should happen?",
        "What actually happens?",
        "Is the failure deterministic?",
        "What does the stack trace say?",
        "What changed recently?",
        "Which component first produces an incorrect value?",
        "Which hypothesis is being tested?",
        "What evidence supports or rejects it?",
        "What is the root cause?",
        "Does the fix address the cause?",
        "Is there a regression test?",
        "Could the fix introduce a performance or security problem?"
    ];

    checklist.forEach((item, index) => {
        console.log(`${index + 1}. ${item}`);
    });
}


// ============================================================================
// 20. COMMON DEBUGGING MISTAKES
// ============================================================================

function commonDebuggingMistakes() {
    printHeading("20. Common Debugging Mistakes");

    const mistakes = [
        "Changing code before reproducing the failure.",
        "Assuming the first visible symptom is the root cause.",
        "Changing several things at once.",
        "Ignoring configuration and environment differences.",
        "Using excessive logging without diagnostic purpose.",
        "Logging secrets.",
        "Ignoring asynchronous ordering.",
        "Fixing a symptom without adding a regression test.",
        "Assuming a successful execution proves correctness.",
        "Ignoring intermittent failures.",
        "Using assertions as a substitute for validating untrusted input.",
        "Optimizing before measuring."
    ];

    mistakes.forEach((mistake, index) => {
        console.log(`${index + 1}. ${mistake}`);
    });
}


// ============================================================================
// 21. ADVANCED PRINCIPLES
// ============================================================================

function advancedPrinciples() {
    printHeading("21. Advanced Debugging Principles");

    const principles = {
        reproducibility: "Make failures repeatable.",
        observability: "Expose meaningful system behavior.",
        isolation: "Reduce the failing boundary.",
        instrumentation: "Collect targeted evidence.",
        invariants: "Define conditions that must remain true.",
        correlation: "Connect related events with identifiers.",
        regressionPrevention: "Automate tests for discovered failures.",
        faultContainment: "Limit the impact of individual failures.",
        minimalIntervention: "Prefer evidence-producing changes over guesses."
    };

    Object.entries(principles).forEach(([name, explanation]) => {
        console.log(`${name.padEnd(24)} -> ${explanation}`);
    });
}


// ============================================================================
// 22. MAIN PROGRAM
// ============================================================================

async function main() {
    debuggingTerminology();
    debuggingWorkflow();
    validationDemo();
    breakpointDemo();
    conditionalBreakpointDemo();
    loggingDemo();
    stackTraceDemo();
    await asynchronousDebuggingDemo();
    faultIsolationDemo();
    rootCauseAnalysisDemo();
    hypothesisDrivenDebugging();
    stateInspectionDemo();
    orderCaseStudy();
    regressionTests();
    edgeCasesDemo();
    performanceDemo();
    securityLoggingDemo();
    errorWrappingDemo();
    debuggingChecklist();
    commonDebuggingMistakes();
    advancedPrinciples();

    printHeading("23. Practical Debugging Exercise");

    console.log(
        "Intentionally change one expression in an example, reproduce the",
        "failure, form a hypothesis, inspect state with a breakpoint or log,",
        "identify the root cause, apply the smallest correct fix, and add",
        "a regression test."
    );
}

main().catch((error) => {
    console.error("Unhandled application failure:", error);
    process.exitCode = 1;
});
