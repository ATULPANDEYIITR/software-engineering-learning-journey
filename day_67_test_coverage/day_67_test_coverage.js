"use strict";

/**
 * Test Coverage: Coverage Metrics and Meaningful Testing
 *
 * Node.js implementation using:
 * - Map and Set
 * - Event-driven coverage collection
 * - Async test execution
 * - Statement, branch and function coverage
 * - Coverage gates
 * - JSON reporting
 * - Boundary and failure testing
 */

const fs = require("node:fs/promises");
const path = require("node:path");
const { EventEmitter } = require("node:events");

class CoverageError extends Error {
    constructor(message) {
        super(message);
        this.name = "CoverageError";
    }
}

class CoverageMonitor extends EventEmitter {
    constructor() {
        super();

        this.metrics = new Map([
            ["statement", { total: new Set(), covered: new Set() }],
            ["branch", { total: new Set(), covered: new Set() }],
            ["function", { total: new Set(), covered: new Set() }]
        ]);

        this.tests = [];
    }

    register(type, id) {
        const metric = this.metrics.get(type);

        if (!metric) {
            throw new CoverageError(`Unknown metric: ${type}`);
        }

        metric.total.add(id);
    }

    record(type, id) {
        const metric = this.metrics.get(type);

        if (!metric || !metric.total.has(id)) {
            throw new CoverageError(`Unregistered coverage item: ${id}`);
        }

        if (!metric.covered.has(id)) {
            metric.covered.add(id);

            this.emit("coverage", {
                type,
                id,
                timestamp: new Date().toISOString()
            });
        }
    }

    recordTest(name, passed, error = null) {
        const result = {
            name,
            passed,
            error: error ? error.message : null
        };

        this.tests.push(result);
        this.emit("testCompleted", result);
    }

    calculate(type) {
        const metric = this.metrics.get(type);

        if (!metric) {
            throw new CoverageError(`Unknown metric: ${type}`);
        }

        const total = metric.total.size;
        const covered = metric.covered.size;

        return {
            total,
            covered,
            missed: [...metric.total].filter(
                item => !metric.covered.has(item)
            ),
            percentage: total === 0
                ? 100
                : Number((covered / total * 100).toFixed(2))
        };
    }

    report() {
        return {
            generatedAt: new Date().toISOString(),
            metrics: Object.fromEntries(
                [...this.metrics.keys()].map(type => [
                    type,
                    this.calculate(type)
                ])
            ),
            tests: {
                total: this.tests.length,
                passed: this.tests.filter(t => t.passed).length,
                failed: this.tests.filter(t => !t.passed).length
            }
        };
    }

    enforceThreshold(threshold) {
        if (!Number.isFinite(threshold) ||
            threshold < 0 ||
            threshold > 100) {
            throw new CoverageError("Invalid coverage threshold");
        }

        return [...this.metrics.keys()].every(
            type => this.calculate(type).percentage >= threshold
        );
    }
}

const monitor = new CoverageMonitor();

const definitions = {
    statement: [
        "divide.validation",
        "divide.calculation",
        "classify.validation",
        "classify.negative",
        "classify.zero",
        "classify.positive",
        "classify.large"
    ],
    branch: [
        "divide.zero",
        "classify.negative",
        "classify.zero",
        "classify.positive",
        "classify.large"
    ],
    function: [
        "safeDivide",
        "classifyNumber"
    ]
};

for (const [type, items] of Object.entries(definitions)) {
    for (const item of items) {
        monitor.register(type, item);
    }
}

monitor.on("coverage", event => {
    console.log(`[COVERAGE] ${event.type}: ${event.id}`);
});

monitor.on("testCompleted", result => {
    console.log(
        `[TEST] ${result.passed ? "PASS" : "FAIL"} ${result.name}`
    );
});

function safeDivide(a, b) {
    monitor.record("function", "safeDivide");
    monitor.record("statement", "divide.validation");

    if (typeof a !== "number" || !Number.isFinite(a)) {
        throw new TypeError("Numerator must be a finite number");
    }

    if (typeof b !== "number" || !Number.isFinite(b)) {
        throw new TypeError("Denominator must be a finite number");
    }

    if (b === 0) {
        monitor.record("branch", "divide.zero");
        throw new RangeError("Division by zero");
    }

    monitor.record("statement", "divide.calculation");

    const result = a / b;

    if (!Number.isFinite(result)) {
        throw new RangeError("Result is outside supported numeric range");
    }

    return result;
}

function classifyNumber(value) {
    monitor.record("function", "classifyNumber");
    monitor.record("statement", "classify.validation");

    if (typeof value !== "number" || !Number.isFinite(value)) {
        throw new TypeError("Input must be a finite number");
    }

    if (value < 0) {
        monitor.record("branch", "classify.negative");
        monitor.record("statement", "classify.negative");
        return "negative";
    }

    if (value === 0) {
        monitor.record("branch", "classify.zero");
        monitor.record("statement", "classify.zero");
        return "zero";
    }

    monitor.record("branch", "classify.positive");
    monitor.record("statement", "classify.positive");

    if (value >= 100) {
        monitor.record("branch", "classify.large");
        monitor.record("statement", "classify.large");
        return "large";
    }

    return "positive";
}

async function executeTest(name, testFunction) {
    try {
        await testFunction();
        monitor.recordTest(name, true);
    } catch (error) {
        monitor.recordTest(name, false, error);
    }
}

function assertEqual(actual, expected) {
    if (!Object.is(actual, expected)) {
        throw new Error(
            `Expected ${expected}, received ${actual}`
        );
    }
}

function assertThrows(fn, ExpectedError) {
    let thrown = false;

    try {
        fn();
    } catch (error) {
        if (!(error instanceof ExpectedError)) {
            throw new Error(
                `Expected ${ExpectedError.name}, received ${error.name}`
            );
        }

        thrown = true;
    }

    if (!thrown) {
        throw new Error(`Expected ${ExpectedError.name} was not thrown`);
    }
}

async function runTests() {
    const tests = [
        ["normal division", () => {
            assertEqual(safeDivide(20, 4), 5);
        }],

        ["negative division", () => {
            assertEqual(safeDivide(-20, 4), -5);
        }],

        ["zero denominator", () => {
            assertThrows(
                () => safeDivide(10, 0),
                RangeError
            );
        }],

        ["invalid numerator", () => {
            assertThrows(
                () => safeDivide("10", 2),
                TypeError
            );
        }],

        ["invalid denominator", () => {
            assertThrows(
                () => safeDivide(10, NaN),
                TypeError
            );
        }],

        ["negative classification", () => {
            assertEqual(classifyNumber(-5), "negative");
        }],

        ["zero classification", () => {
            assertEqual(classifyNumber(0), "zero");
        }],

        ["positive classification", () => {
            assertEqual(classifyNumber(25), "positive");
        }],

        ["large classification", () => {
            assertEqual(classifyNumber(100), "large");
        }],

        ["invalid classification", () => {
            assertThrows(
                () => classifyNumber(Infinity),
                TypeError
            );
        }],

        ["decimal boundary", () => {
            assertEqual(classifyNumber(99.99), "positive");
        }]
    ];

    for (const [name, testFunction] of tests) {
        await executeTest(name, testFunction);
    }
}

async function saveReport(report) {
    const filename = path.resolve(
        process.cwd(),
        "coverage-report.json"
    );

    const safeDirectory = path.resolve(process.cwd());

    if (path.dirname(filename) !== safeDirectory) {
        throw new CoverageError("Unsafe report path");
    }

    await fs.writeFile(
        filename,
        JSON.stringify(report, null, 2),
        { encoding: "utf8", flag: "w" }
    );

    console.log(`Report saved: ${filename}`);
}

async function main() {
    await runTests();

    const report = monitor.report();

    console.log("\nCOVERAGE REPORT");

    for (const [type, metric] of Object.entries(report.metrics)) {
        console.log(
            `${type}: ${metric.covered}/${metric.total} ` +
            `(${metric.percentage}%)`
        );

        if (metric.missed.length > 0) {
            console.log("Uncovered:", metric.missed.join(", "));
        }
    }

    console.log("\nTEST RESULTS:", report.tests);

    const threshold = 80;
    const qualityGate = monitor.enforceThreshold(threshold);

    console.log(
        `Coverage gate (${threshold}%):`,
        qualityGate ? "PASSED" : "FAILED"
    );

    await saveReport(report);

    if (!qualityGate || report.tests.failed > 0) {
        process.exitCode = 1;
    }
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
