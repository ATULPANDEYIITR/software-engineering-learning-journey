"use strict";

/**
 * Behavior-Driven Development
 * Event-driven acceptance testing using Node.js.
 *
 * Scenario:
 * An online payment and order fulfillment workflow.
 *
 * Run:
 * node behavior_driven_development.js
 */

const assert = require("node:assert/strict");

// ============================================================
// 1. Domain events
// ============================================================

class DomainEvent {
    constructor(type, payload) {
        this.type = type;
        this.payload = Object.freeze({ ...payload });
        this.timestamp = new Date().toISOString();
    }
}

class EventBus {
    #handlers = new Map();

    subscribe(eventType, handler) {
        if (typeof handler !== "function") {
            throw new TypeError("Handler must be a function");
        }

        if (!this.#handlers.has(eventType)) {
            this.#handlers.set(eventType, new Set());
        }

        this.#handlers.get(eventType).add(handler);
    }

    async publish(event) {
        const handlers = this.#handlers.get(event.type) ?? [];

        // Await every handler so failures are visible to the scenario.
        for (const handler of handlers) {
            await handler(event);
        }
    }
}

// ============================================================
// 2. Business domain
// ============================================================

class Inventory {
    #products = new Map();

    addProduct(id, price, stock) {
        if (!id || !Number.isSafeInteger(stock) || stock < 0) {
            throw new Error("Invalid product information");
        }

        if (!Number.isFinite(price) || price <= 0) {
            throw new Error("Price must be positive");
        }

        if (this.#products.has(id)) {
            throw new Error(`Duplicate product: ${id}`);
        }

        this.#products.set(id, {
            id,
            price,
            stock
        });
    }

    getProduct(id) {
        const product = this.#products.get(id);

        if (!product) {
            throw new Error("Product not found");
        }

        return product;
    }

    reserve(id, quantity) {
        if (!Number.isSafeInteger(quantity) || quantity <= 0) {
            throw new Error("Quantity must be a positive integer");
        }

        const product = this.getProduct(id);

        if (product.stock < quantity) {
            throw new Error("Insufficient inventory");
        }

        product.stock -= quantity;
    }

    release(id, quantity) {
        const product = this.getProduct(id);
        product.stock += quantity;
    }
}

class OrderService {
    constructor(inventory, eventBus, taxRate = 0.10) {
        if (!Number.isFinite(taxRate) ||
            taxRate < 0 ||
            taxRate > 1) {
            throw new Error("Invalid tax rate");
        }

        this.inventory = inventory;
        this.eventBus = eventBus;
        this.taxRate = taxRate;
        this.orders = new Map();
        this.nextId = 1;
    }

    async placeOrder({
        customer,
        productId,
        quantity,
        paymentApproved
    }) {
        if (!customer?.authenticated) {
            throw new Error("Authentication required");
        }

        if (!paymentApproved) {
            throw new Error("Payment authorization failed");
        }

        const product = this.inventory.getProduct(productId);

        if (!Number.isSafeInteger(quantity) || quantity <= 0) {
            throw new Error("Invalid quantity");
        }

        if (product.stock < quantity) {
            throw new Error("Insufficient inventory");
        }

        const subtotal = product.price * quantity;
        const total = Math.round(
            (subtotal * (1 + this.taxRate) + Number.EPSILON) * 100
        ) / 100;

        // Reserve inventory before publishing confirmation.
        this.inventory.reserve(productId, quantity);

        const order = {
            id: `ORD-${String(this.nextId++).padStart(4, "0")}`,
            customerId: customer.id,
            productId,
            quantity,
            total,
            status: "CONFIRMED"
        };

        this.orders.set(order.id, order);

        try {
            await this.eventBus.publish(
                new DomainEvent("OrderConfirmed", order)
            );
        } catch (error) {
            // Compensating action prevents an unreported order
            // from permanently consuming inventory.
            this.orders.delete(order.id);
            this.inventory.release(productId, quantity);
            throw new Error(
                `Order event processing failed: ${error.message}`
            );
        }

        return Object.freeze({ ...order });
    }
}

// ============================================================
// 3. BDD execution engine
// ============================================================

class Scenario {
    constructor(name, description) {
        this.name = name;
        this.description = description;
        this.steps = [];
    }

    given(description, action) {
        return this.#add("Given", description, action);
    }

    when(description, action) {
        return this.#add("When", description, action);
    }

    then(description, action) {
        return this.#add("Then", description, action);
    }

    and(description, action) {
        return this.#add("And", description, action);
    }

    #add(keyword, description, action) {
        if (typeof action !== "function") {
            throw new TypeError("A step must contain an executable action");
        }

        this.steps.push({
            keyword,
            description,
            action
        });

        return this;
    }
}

class Feature {
    constructor(name) {
        this.name = name;
        this.scenarios = [];
    }

    add(scenario) {
        this.scenarios.push(scenario);
        return this;
    }
}

class BDDRunner {
    async runScenario(scenario) {
        const context = {};
        const start = performance.now();

        try {
            for (const step of scenario.steps) {
                await step.action(context);
            }

            return {
                name: scenario.name,
                status: "PASSED",
                durationMs: performance.now() - start
            };
        } catch (error) {
            return {
                name: scenario.name,
                status: "FAILED",
                durationMs: performance.now() - start,
                error: error.message
            };
        }
    }

    async runFeature(feature) {
        console.log(`\nFeature: ${feature.name}`);

        const results = [];

        // Sequential execution prevents shared test resources
        // from creating nondeterministic inventory changes.
        for (const scenario of feature.scenarios) {
            const result = await this.runScenario(scenario);
            results.push(result);

            console.log(
                `[${result.status}] ${result.name} ` +
                `(${result.durationMs.toFixed(3)} ms)`
            );

            if (result.error) {
                console.error(`  ${result.error}`);
            }
        }

        return results;
    }
}

// ============================================================
// 4. Test environment factory
// ============================================================

function createEnvironment() {
    const bus = new EventBus();
    const inventory = new Inventory();

    inventory.addProduct("KB-101", 1000, 10);

    const service = new OrderService(inventory, bus);

    const publishedEvents = [];

    bus.subscribe("OrderConfirmed", async event => {
        publishedEvents.push(event);
    });

    return {
        bus,
        inventory,
        service,
        publishedEvents
    };
}

// ============================================================
// 5. Acceptance scenarios
// ============================================================

const feature = new Feature("Online order processing");

feature.add(
    new Scenario(
        "Successful customer purchase",
        "An authenticated customer purchases available inventory."
    )
        .given("the product is available", context => {
            context.env = createEnvironment();
        })
        .and("the customer is authenticated", context => {
            context.customer = {
                id: "CUS-101",
                authenticated: true
            };
        })
        .when("the customer places an order", async context => {
            context.order = await context.env.service.placeOrder({
                customer: context.customer,
                productId: "KB-101",
                quantity: 2,
                paymentApproved: true
            });
        })
        .then("the order is confirmed", context => {
            assert.equal(context.order.status, "CONFIRMED");
        })
        .and("the inventory is reduced", context => {
            assert.equal(
                context.env.inventory.getProduct("KB-101").stock,
                8
            );
        })
        .and("an order confirmation event is published", context => {
            assert.equal(context.env.publishedEvents.length, 1);
        })
);

feature.add(
    new Scenario(
        "Insufficient inventory",
        "A customer cannot purchase more units than available."
    )
        .given("the product has limited stock", context => {
            context.env = createEnvironment();
            context.env.inventory.getProduct("KB-101").stock = 1;
        })
        .when("the customer requests excessive quantity", async context => {
            await assert.rejects(
                context.env.service.placeOrder({
                    customer: {
                        id: "CUS-102",
                        authenticated: true
                    },
                    productId: "KB-101",
                    quantity: 5,
                    paymentApproved: true
                }),
                /Insufficient inventory/
            );
        })
        .then("the inventory remains unchanged", context => {
            assert.equal(
                context.env.inventory.getProduct("KB-101").stock,
                1
            );
        })
);

feature.add(
    new Scenario(
        "Unauthenticated purchase",
        "Unauthenticated customers cannot submit orders."
    )
        .given("the order service is available", context => {
            context.env = createEnvironment();
        })
        .when("an unauthenticated customer submits an order", async context => {
            await assert.rejects(
                context.env.service.placeOrder({
                    customer: {
                        id: "CUS-103",
                        authenticated: false
                    },
                    productId: "KB-101",
                    quantity: 1,
                    paymentApproved: true
                }),
                /Authentication required/
            );
        })
        .then("no order is created", context => {
            assert.equal(context.env.service.orders.size, 0);
        })
);

feature.add(
    new Scenario(
        "Payment authorization failure",
        "Failed payment authorization prevents inventory reservation."
    )
        .given("inventory is available", context => {
            context.env = createEnvironment();
        })
        .when("payment authorization is rejected", async context => {
            await assert.rejects(
                context.env.service.placeOrder({
                    customer: {
                        id: "CUS-104",
                        authenticated: true
                    },
                    productId: "KB-101",
                    quantity: 2,
                    paymentApproved: false
                }),
                /Payment authorization failed/
            );
        })
        .then("inventory remains available", context => {
            assert.equal(
                context.env.inventory.getProduct("KB-101").stock,
                10
            );
        })
);

// ============================================================
// 6. Data-driven scenario outline
// ============================================================

async function runScenarioOutline() {
    console.log("\nScenario Outline: Purchase quantities");

    const examples = [
        { quantity: 1, expected: 1100 },
        { quantity: 2, expected: 2200 },
        { quantity: 3, expected: 3300 }
    ];

    for (const example of examples) {
        const env = createEnvironment();

        const order = await env.service.placeOrder({
            customer: {
                id: "CUS-105",
                authenticated: true
            },
            productId: "KB-101",
            quantity: example.quantity,
            paymentApproved: true
        });

        assert.equal(order.total, example.expected);

        console.log(
            `[PASSED] quantity=${example.quantity}, ` +
            `total=${order.total.toFixed(2)}`
        );
    }
}

// ============================================================
// 7. Test report
// ============================================================

async function main() {
    const runner = new BDDRunner();

    const results = await runner.runFeature(feature);

    await runScenarioOutline();

    const passed = results.filter(
        result => result.status === "PASSED"
    ).length;

    const failed = results.length - passed;

    console.log("\nAcceptance Test Report");

    console.log(JSON.stringify({
        feature: feature.name,
        total: results.length,
        passed,
        failed,
        scenarios: results
    }, null, 2));

    if (failed > 0) {
        process.exitCode = 1;
    }
}

main().catch(error => {
    console.error("Test execution failed:", error);
    process.exitCode = 1;
});
