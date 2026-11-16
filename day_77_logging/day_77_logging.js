"use strict";

/**
 * Structured Logging, Log Levels, and Correlation IDs
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 *
 * Features:
 * - JSON structured events
 * - AsyncLocalStorage correlation propagation
 * - Hierarchical log levels
 * - Request-scoped metadata
 * - Sensitive-data redaction
 * - Event-driven log processing
 * - Asynchronous file persistence
 * - Error serialization
 * - Log sampling and filtering
 * - Validation and automated tests
 */

const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const {
    AsyncLocalStorage
} = require("node:async_hooks");
const EventEmitter = require("node:events");

// -------------------------------------------------------
// 1. Configuration
// -------------------------------------------------------

const LEVELS = Object.freeze({
    DEBUG: 10,
    INFO: 20,
    WARN: 30,
    ERROR: 40,
    FATAL: 50
});

const LEVEL_NAMES = Object.freeze(
    Object.fromEntries(
        Object.entries(LEVELS).map(([name, value]) => [
            value,
            name
        ])
    )
);

const contextStorage = new AsyncLocalStorage();

const SENSITIVE_FIELDS = new Set([
    "password",
    "token",
    "access_token",
    "authorization",
    "secret",
    "api_key",
    "credit_card"
]);

// -------------------------------------------------------
// 2. Validation
// -------------------------------------------------------

function validateLevel(level) {
    if (!Object.hasOwn(LEVELS, level)) {
        throw new TypeError(`Unsupported log level: ${level}`);
    }

    return LEVELS[level];
}

function validateMessage(message) {
    if (typeof message !== "string" || !message.trim()) {
        throw new TypeError("Log message must be non-empty.");
    }
}

// -------------------------------------------------------
// 3. Context propagation
// -------------------------------------------------------

function withLoggingContext(metadata, callback) {
    if (!metadata || typeof metadata !== "object") {
        throw new TypeError("Context metadata must be an object.");
    }

    const context = {
        correlationId:
            metadata.correlationId || crypto.randomUUID(),

        requestId:
            metadata.requestId || crypto.randomUUID(),

        ...metadata
    };

    if (
        typeof context.correlationId !== "string" ||
        !context.correlationId.trim() ||
        typeof context.requestId !== "string" ||
        !context.requestId.trim()
    ) {
        throw new TypeError("Invalid correlation or request ID.");
    }

    return contextStorage.run(context, callback);
}

// -------------------------------------------------------
// 4. Recursive data sanitization
// -------------------------------------------------------

function redact(value, key = "", seen = new WeakSet()) {
    if (SENSITIVE_FIELDS.has(key.toLowerCase())) {
        return "[REDACTED]";
    }

    if (value === null || value === undefined) {
        return value;
    }

    if (value instanceof Error) {
        return {
            name: value.name,
            message: value.message,
            stack: value.stack
        };
    }

    if (typeof value === "bigint") {
        return value.toString();
    }

    if (typeof value !== "object") {
        return value;
    }

    if (seen.has(value)) {
        return "[CIRCULAR_REFERENCE]";
    }

    seen.add(value);

    let result;

    if (Array.isArray(value)) {
        result = value.map(item => redact(item, "", seen));
    } else {
        result = {};

        for (const [childKey, childValue] of Object.entries(value)) {
            result[childKey] = redact(
                childValue,
                childKey,
                seen
            );
        }
    }

    seen.delete(value);

    return result;
}

// -------------------------------------------------------
// 5. Asynchronous JSON file transport
// -------------------------------------------------------

class FileTransport {

    constructor(filename) {
        this.filename = filename;
        this.queue = Promise.resolve();
        this.closed = false;

        fs.mkdirSync(path.dirname(filename), {
            recursive: true
        });
    }

    write(event) {
        if (this.closed) {
            return Promise.reject(
                new Error("File transport is closed.")
            );
        }

        const line = JSON.stringify(event) + "\n";

        // Serialize writes to preserve event order.
        const operation = this.queue.then(() =>
            fs.promises.appendFile(
                this.filename,
                line,
                { encoding: "utf8", mode: 0o600 }
            )
        );

        this.queue = operation.catch(() => {});

        return operation;
    }

    async close() {
        await this.queue;
        this.closed = true;
    }
}

// -------------------------------------------------------
// 6. Structured logger
// -------------------------------------------------------

class StructuredLogger extends EventEmitter {

    constructor({
        service,
        minimumLevel = "INFO",
        transport = null,
        consoleOutput = true,
        sampleRate = 1
    }) {
        super();

        if (!service || typeof service !== "string") {
            throw new TypeError("Service name is required.");
        }

        this.service = service;
        this.minimumLevel = validateLevel(minimumLevel);
        this.transport = transport;
        this.consoleOutput = consoleOutput;

        if (
            !Number.isFinite(sampleRate) ||
            sampleRate < 0 ||
            sampleRate > 1
        ) {
            throw new RangeError("Sample rate must be between 0 and 1.");
        }

        this.sampleRate = sampleRate;
    }

    createEvent(level, message, attributes = {}) {
        validateMessage(message);

        if (
            !attributes ||
            typeof attributes !== "object" ||
            Array.isArray(attributes)
        ) {
            throw new TypeError("Attributes must be an object.");
        }

        const context = contextStorage.getStore() || {};

        const event = {
            timestamp: new Date().toISOString(),
            level,
            severity: LEVELS[level],
            service: this.service,
            message,
            correlation_id:
                context.correlationId || "system",
            request_id:
                context.requestId || "system",
            attributes: redact(attributes)
        };

        return Object.freeze(event);
    }

    async log(level, message, attributes = {}) {
        const severity = validateLevel(level);

        if (severity < this.minimumLevel) {
            return false;
        }

        // Sampling is applied to informational events.
        if (
            severity <= LEVELS.INFO &&
            Math.random() > this.sampleRate
        ) {
            return false;
        }

        const event = this.createEvent(
            level,
            message,
            attributes
        );

        if (this.consoleOutput) {
            const output = JSON.stringify(event);

            if (severity >= LEVELS.ERROR) {
                process.stderr.write(output + "\n");
            } else {
                process.stdout.write(output + "\n");
            }
        }

        this.emit("log", event);

        if (this.transport) {
            await this.transport.write(event);
        }

        return true;
    }

    debug(message, attributes) {
        return this.log("DEBUG", message, attributes);
    }

    info(message, attributes) {
        return this.log("INFO", message, attributes);
    }

    warn(message, attributes) {
        return this.log("WARN", message, attributes);
    }

    error(message, attributes) {
        return this.log("ERROR", message, attributes);
    }

    fatal(message, attributes) {
        return this.log("FATAL", message, attributes);
    }

    async logError(message, error, attributes = {}) {
        return this.error(message, {
            ...attributes,
            error
        });
    }
}

// -------------------------------------------------------
// 7. Request-processing service
// -------------------------------------------------------

class OrderService {

    constructor(logger) {
        this.logger = logger;
        this.orders = new Map();
    }

    async createOrder(order) {
        if (!order || typeof order !== "object") {
            throw new TypeError("Invalid order.");
        }

        const { customerId, amount } = order;

        if (
            typeof customerId !== "string" ||
            !customerId.trim()
        ) {
            throw new TypeError("Customer ID is required.");
        }

        if (
            typeof amount !== "number" ||
            !Number.isFinite(amount) ||
            amount <= 0
        ) {
            throw new RangeError("Invalid order amount.");
        }

        const orderId = crypto.randomUUID();

        this.logger.info("Order creation started", {
            customer_id: customerId,
            amount
        });

        const result = {
            orderId,
            customerId,
            amount,
            status: "CREATED"
        };

        this.orders.set(orderId, result);

        this.logger.info("Order created", {
            order_id: orderId,
            customer_id: customerId,
            status: result.status
        });

        return result;
    }
}

// -------------------------------------------------------
// 8. Event-based monitoring
// -------------------------------------------------------

function attachMonitoring(logger) {
    const metrics = new Map();

    logger.on("log", event => {
        const current = metrics.get(event.level) || 0;

        metrics.set(event.level, current + 1);
    });

    return metrics;
}

// -------------------------------------------------------
// 9. Execution tests
// -------------------------------------------------------

async function runTests(logger) {
    const event = logger.createEvent(
        "INFO",
        "Security test",
        { password: "secret" }
    );

    if (event.attributes.password !== "[REDACTED]") {
        throw new Error("Sensitive data redaction failed.");
    }

    const original = new Error("Test error");
    const safeError = redact(original);

    if (safeError.message !== "Test error") {
        throw new Error("Error serialization failed.");
    }

    try {
        validateLevel("UNKNOWN");
        throw new Error("Invalid level was accepted.");
    } catch (error) {
        if (!(error instanceof TypeError)) {
            throw error;
        }
    }

    try {
        validateMessage("");
        throw new Error("Empty message was accepted.");
    } catch (error) {
        if (!(error instanceof TypeError)) {
            throw error;
        }
    }

    const parent = await new Promise(resolve => {
        withLoggingContext(
            {
                correlationId: "CORR-TEST-100",
                requestId: "REQ-TEST-100"
            },
            async () => {
                await logger.info("Parent operation");

                const child = await Promise.resolve().then(
                    async () => {
                        await logger.debug("Child operation");

                        return contextStorage.getStore()
                            .correlationId;
                    }
                );

                resolve(child);
            }
        );
    });

    if (parent !== "CORR-TEST-100") {
        throw new Error("Async context propagation failed.");
    }

    process.stdout.write("All JavaScript tests passed.\n");
}

// -------------------------------------------------------
// 10. Main application
// -------------------------------------------------------

async function main() {
    const transport = new FileTransport(
        path.join(__dirname, "logs", "application.jsonl")
    );

    const logger = new StructuredLogger({
        service: "order-service",
        minimumLevel: "DEBUG",
        transport,
        consoleOutput: true,
        sampleRate: 1
    });

    const metrics = attachMonitoring(logger);
    const service = new OrderService(logger);

    try {
        await logger.info("Application started", {
            version: "1.0.0",
            environment: "development"
        });

        await withLoggingContext(
            {
                correlationId: "CORR-ORDER-1001",
                requestId: "REQ-ORDER-1001"
            },
            async () => {
                await logger.debug("Incoming request", {
                    method: "POST",
                    endpoint: "/orders"
                });

                await service.createOrder({
                    customerId: "CUSTOMER-101",
                    amount: 2500
                });

                try {
                    await service.createOrder({
                        customerId: "CUSTOMER-102",
                        amount: -50
                    });
                } catch (error) {
                    await logger.logError(
                        "Order validation rejected",
                        error,
                        { customer_id: "CUSTOMER-102" }
                    );
                }
            }
        );

        await runTests(logger);

        await logger.info("Application completed", {
            metrics: Object.fromEntries(metrics)
        });

    } finally {
        await transport.close();
    }
}

main().catch(error => {
    process.stderr.write(
        JSON.stringify({
            level: "FATAL",
            message: "Application startup failure",
            error: error.message
        }) + "\n"
    );

    process.exitCode = 1;
});
