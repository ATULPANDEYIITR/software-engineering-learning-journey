/**
 * Dependency Injection in JavaScript
 *
 * This Node.js-compatible file models an order workflow and demonstrates:
 * constructor injection, factory injection, event-driven dependencies,
 * dependency lifetimes, a small container, validation, test doubles,
 * and composition-root design.
 *
 * Run with:
 *   node dependency-injection.js
 */

"use strict";

// -----------------------------------------------------------------------------
// Domain object
// -----------------------------------------------------------------------------

class Order {
    constructor(id, customerEmail, amount) {
        if (!id || !customerEmail || !Number.isFinite(amount)) {
            throw new TypeError("Order requires an id, email, and numeric amount");
        }

        if (amount <= 0) {
            throw new RangeError("Order amount must be greater than zero");
        }

        if (!customerEmail.includes("@")) {
            throw new RangeError("Customer email is invalid");
        }

        this.id = id;
        this.customerEmail = customerEmail;
        this.amount = amount;
        Object.freeze(this);
    }
}

// -----------------------------------------------------------------------------
// Concrete dependencies
// -----------------------------------------------------------------------------

class MemoryOrderStore {
    constructor() {
        this.orders = new Map();
    }

    async save(order) {
        if (this.orders.has(order.id)) {
            throw new Error(`Order already exists: ${order.id}`);
        }

        this.orders.set(order.id, order);
    }

    async find(id) {
        return this.orders.get(id) ?? null;
    }
}

class PaymentProvider {
    constructor({ available = true } = {}) {
        this.available = available;
        this.charges = [];
    }

    async charge(order) {
        if (!this.available) {
            return false;
        }

        this.charges.push({
            orderId: order.id,
            amount: order.amount,
            timestamp: new Date().toISOString()
        });

        return true;
    }
}

class EmailNotifier {
    constructor() {
        this.messages = [];
    }

    async send(order, receipt) {
        this.messages.push({
            destination: order.customerEmail,
            message: receipt.message
        });

        console.log(`Email queued for ${order.customerEmail}`);
    }
}

// -----------------------------------------------------------------------------
// Constructor injection
// -----------------------------------------------------------------------------

class OrderApplicationService {
    /**
     * The constructor receives dependencies rather than creating them.
     * This keeps business behavior independent from infrastructure choices.
     */
    constructor({ store, payment, notifier }) {
        if (!store || !payment || !notifier) {
            throw new TypeError("All order service dependencies are required");
        }

        this.store = store;
        this.payment = payment;
        this.notifier = notifier;
    }

    async placeOrder(order) {
        const existing = await this.store.find(order.id);

        if (existing) {
            throw new Error(`Duplicate order: ${order.id}`);
        }

        const paid = await this.payment.charge(order);

        if (!paid) {
            throw new Error("Payment provider rejected the transaction");
        }

        await this.store.save(order);

        const receipt = {
            orderId: order.id,
            amount: order.amount,
            message: `Order ${order.id} paid successfully for $${order.amount.toFixed(2)}`
        };

        await this.notifier.send(order, receipt);
        return receipt;
    }
}

// -----------------------------------------------------------------------------
// Factory injection
// -----------------------------------------------------------------------------

function createPricingService(taxRule) {
    /**
     * Passing a function is dependency injection at function level.
     * The pricing service does not know which tax policy it receives.
     */
    if (typeof taxRule !== "function") {
        throw new TypeError("taxRule must be a function");
    }

    return {
        total(amount) {
            if (!Number.isFinite(amount) || amount < 0) {
                throw new RangeError("Amount must be a non-negative number");
            }

            return amount + taxRule(amount);
        }
    };
}

const standardTax = amount => amount * 0.18;
const zeroTax = () => 0;

// -----------------------------------------------------------------------------
// Event-driven dependency
// -----------------------------------------------------------------------------

class AuditBus {
    constructor() {
        this.listeners = new Map();
    }

    on(eventName, listener) {
        if (typeof listener !== "function") {
            throw new TypeError("Event listener must be a function");
        }

        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, new Set());
        }

        this.listeners.get(eventName).add(listener);

        return () => this.listeners.get(eventName)?.delete(listener);
    }

    emit(eventName, payload) {
        const listeners = this.listeners.get(eventName) ?? new Set();

        for (const listener of listeners) {
            listener(payload);
        }
    }
}

class AuditedOrderService {
    constructor(orderService, auditBus) {
        this.orderService = orderService;
        this.auditBus = auditBus;
    }

    async placeOrder(order) {
        const receipt = await this.orderService.placeOrder(order);

        this.auditBus.emit("order.paid", {
            orderId: receipt.orderId,
            amount: receipt.amount
        });

        return receipt;
    }
}

// -----------------------------------------------------------------------------
// Minimal dependency container
// -----------------------------------------------------------------------------

class Container {
    constructor() {
        this.providers = new Map();
    }

    singleton(token, factory) {
        this.providers.set(token, {
            factory,
            singleton: true,
            instance: undefined,
            created: false
        });

        return this;
    }

    transient(token, factory) {
        this.providers.set(token, {
            factory,
            singleton: false
        });

        return this;
    }

    resolve(token) {
        const registration = this.providers.get(token);

        if (!registration) {
            throw new Error(`Dependency is not registered: ${token}`);
        }

        if (registration.singleton) {
            if (!registration.created) {
                registration.instance = registration.factory(this);
                registration.created = true;
            }

            return registration.instance;
        }

        return registration.factory(this);
    }
}

// -----------------------------------------------------------------------------
// Composition root
// -----------------------------------------------------------------------------

function buildApplication() {
    /**
     * The composition root is the place where concrete implementations are
     * selected. Application classes remain unaware of these infrastructure
     * decisions.
     */
    const container = new Container();

    container.singleton("store", () => new MemoryOrderStore());

    container.transient(
        "payment",
        () => new PaymentProvider({ available: true })
    );

    container.singleton("notifier", () => new EmailNotifier());

    container.singleton(
        "orderService",
        c => new OrderApplicationService({
            store: c.resolve("store"),
            payment: c.resolve("payment"),
            notifier: c.resolve("notifier")
        })
    );

    container.singleton("auditBus", () => new AuditBus());

    container.singleton(
        "auditedService",
        c => new AuditedOrderService(
            c.resolve("orderService"),
            c.resolve("auditBus")
        )
    );

    return container;
}

// -----------------------------------------------------------------------------
// Test doubles
// -----------------------------------------------------------------------------

class FakePayment {
    constructor(result = true) {
        this.result = result;
        this.calls = [];
    }

    async charge(order) {
        this.calls.push(order);
        return this.result;
    }
}

class FakeNotifier {
    constructor() {
        this.calls = [];
    }

    async send(order, receipt) {
        this.calls.push({ order, receipt });
    }
}

async function testSuccessfulOrder() {
    const store = new MemoryOrderStore();
    const payment = new FakePayment(true);
    const notifier = new FakeNotifier();

    const service = new OrderApplicationService({
        store,
        payment,
        notifier
    });

    const order = new Order("ORD-JS-1", "buyer@example.com", 250);

    const receipt = await service.placeOrder(order);

    console.assert(receipt.orderId === "ORD-JS-1");
    console.assert((await store.find("ORD-JS-1")) === order);
    console.assert(payment.calls.length === 1);
    console.assert(notifier.calls.length === 1);
}

async function testPaymentFailureDoesNotPersist() {
    const store = new MemoryOrderStore();
    const payment = new FakePayment(false);
    const notifier = new FakeNotifier();

    const service = new OrderApplicationService({
        store,
        payment,
        notifier
    });

    const order = new Order("ORD-JS-2", "buyer@example.com", 300);

    await assertRejects(
        () => service.placeOrder(order),
        "Payment provider rejected"
    );

    console.assert((await store.find(order.id)) === null);
    console.assert(notifier.calls.length === 0);
}

async function testDuplicateOrderIsRejected() {
    const store = new MemoryOrderStore();
    const existing = new Order("ORD-JS-3", "existing@example.com", 50);

    await store.save(existing);

    const payment = new FakePayment(true);
    const notifier = new FakeNotifier();

    const service = new OrderApplicationService({
        store,
        payment,
        notifier
    });

    await assertRejects(
        () => service.placeOrder(existing),
        "Duplicate order"
    );

    console.assert(payment.calls.length === 0);
}

async function assertRejects(operation, expectedText) {
    try {
        await operation();
    } catch (error) {
        console.assert(error.message.includes(expectedText));
        return;
    }

    throw new Error(`Expected rejection containing: ${expectedText}`);
}

// -----------------------------------------------------------------------------
// Container lifetime test
// -----------------------------------------------------------------------------

function testContainerLifetimes() {
    const container = new Container();

    container.singleton("store", () => new MemoryOrderStore());
    container.transient("payment", () => new PaymentProvider());

    console.assert(container.resolve("store") === container.resolve("store"));
    console.assert(container.resolve("payment") !== container.resolve("payment"));
}

// -----------------------------------------------------------------------------
// Demonstration
// -----------------------------------------------------------------------------

async function main() {
    console.log("Dependency Injection in JavaScript");

    const container = buildApplication();
    const auditBus = container.resolve("auditBus");

    auditBus.on("order.paid", event => {
        console.log(
            `Audit event: ${event.orderId} paid $${event.amount.toFixed(2)}`
        );
    });

    const service = container.resolve("auditedService");

    await service.placeOrder(
        new Order("ORD-PROD-1", "customer@example.com", 149.99)
    );

    const standardPricing = createPricingService(standardTax);
    const exemptPricing = createPricingService(zeroTax);

    console.log(`Standard total: $${standardPricing.total(100).toFixed(2)}`);
    console.log(`Tax-exempt total: $${exemptPricing.total(100).toFixed(2)}`);

    await testSuccessfulOrder();
    await testPaymentFailureDoesNotPersist();
    await testDuplicateOrderIsRejected();
    testContainerLifetimes();

    console.log("All dependency-injection tests passed.");
}

main().catch(error => {
    console.error(`Application failed: ${error.message}`);
    process.exitCode = 1;
});
