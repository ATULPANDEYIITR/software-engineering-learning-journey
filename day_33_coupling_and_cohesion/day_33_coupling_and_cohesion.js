'use strict';

/*
 * Coupling & Cohesion
 *
 * A JavaScript-specific architecture model for an order-processing system.
 *
 * The implementation emphasizes:
 * - high cohesion through focused classes and functions
 * - loose coupling through dependency injection
 * - event-driven communication
 * - asynchronous infrastructure boundaries
 * - policy composition
 * - validation and failure handling
 *
 * Runtime: Node.js 18+
 */

// ---------------------------------------------------------------------------
// Domain objects
// ---------------------------------------------------------------------------

class Product {
    constructor(id, name, unitPrice) {
        if (!id || !name) {
            throw new Error('Product id and name are required');
        }

        if (!Number.isFinite(unitPrice) || unitPrice < 0) {
            throw new Error('Product price must be a non-negative number');
        }

        this.id = id;
        this.name = name;
        this.unitPrice = unitPrice;
    }
}

class Order {
    constructor(id, customerEmail, items) {
        this.id = id;
        this.customerEmail = customerEmail;
        this.items = items;
        this.status = 'created';
    }

    get total() {
        return this.items.reduce(
            (sum, item) => sum + item.product.unitPrice * item.quantity,
            0
        );
    }

    markPaid() {
        if (this.status !== 'created') {
            throw new Error(
                `Only created orders can become paid; current status is ${this.status}`
            );
        }

        this.status = 'paid';
    }

    cancel() {
        if (this.status === 'shipped') {
            throw new Error('A shipped order cannot be cancelled');
        }

        this.status = 'cancelled';
    }
}


// ---------------------------------------------------------------------------
// A cohesive pricing module
// ---------------------------------------------------------------------------

class PricingService {
    calculateSubtotal(item) {
        return item.product.unitPrice * item.quantity;
    }

    calculateTotal(order) {
        return order.items.reduce(
            (total, item) => total + this.calculateSubtotal(item),
            0
        );
    }
}


// ---------------------------------------------------------------------------
// Focused validation
// ---------------------------------------------------------------------------

class OrderValidator {
    validate(order) {
        if (!(order instanceof Order)) {
            throw new TypeError('Expected an Order instance');
        }

        if (!order.id.trim()) {
            throw new Error('Order id cannot be empty');
        }

        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(order.customerEmail)) {
            throw new Error('Invalid customer email');
        }

        if (!Array.isArray(order.items) || order.items.length === 0) {
            throw new Error('Order must contain at least one item');
        }

        for (const item of order.items) {
            if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
                throw new Error('Quantity must be a positive integer');
            }
        }
    }
}


// ---------------------------------------------------------------------------
// Asynchronous infrastructure adapters
// ---------------------------------------------------------------------------

class MemoryInventory {
    constructor(stock) {
        this.stock = new Map(Object.entries(stock));
    }

    async reserve(productId, quantity) {
        const available = this.stock.get(productId) ?? 0;

        if (available < quantity) {
            throw new Error(
                `Insufficient inventory for ${productId}: requested ${quantity}, available ${available}`
            );
        }

        this.stock.set(productId, available - quantity);

        return {
            productId,
            quantity,
            reserved: true
        };
    }

    async release(productId, quantity) {
        const available = this.stock.get(productId) ?? 0;
        this.stock.set(productId, available + quantity);
    }

    available(productId) {
        return this.stock.get(productId) ?? 0;
    }
}

class PaymentGateway {
    constructor({ rejectOrders = new Set() } = {}) {
        this.rejectOrders = rejectOrders;
        this.charges = [];
    }

    async charge(orderId, amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error('Payment amount must be positive');
        }

        if (this.rejectOrders.has(orderId)) {
            throw new Error(`Payment rejected for ${orderId}`);
        }

        // A Promise boundary models the fact that a real payment provider
        // normally requires asynchronous I/O.
        await Promise.resolve();

        const transactionId = `PAY-${orderId}-${this.charges.length + 1}`;

        this.charges.push({
            orderId,
            amount,
            transactionId
        });

        return transactionId;
    }
}

class NotificationGateway {
    constructor() {
        this.sent = [];
    }

    async sendPaymentConfirmation(customerEmail, orderId, amount) {
        await Promise.resolve();

        this.sent.push({
            customerEmail,
            orderId,
            amount
        });

        return true;
    }
}

class MemoryOrderRepository {
    constructor() {
        this.orders = new Map();
    }

    async save(order) {
        this.orders.set(order.id, order);
    }

    async findById(orderId) {
        return this.orders.get(orderId) ?? null;
    }
}


// ---------------------------------------------------------------------------
// Event-driven communication
// ---------------------------------------------------------------------------

class DomainEventBus {
    constructor() {
        this.listeners = new Map();
    }

    subscribe(eventName, handler) {
        if (!this.listeners.has(eventName)) {
            this.listeners.set(eventName, new Set());
        }

        this.listeners.get(eventName).add(handler);

        // Returning an unsubscribe function keeps subscription management
        // explicit and prevents permanent event-handler registration.
        return () => {
            this.listeners.get(eventName)?.delete(handler);
        };
    }

    async publish(eventName, payload) {
        const handlers = this.listeners.get(eventName) ?? [];

        // Promise.all allows independent event consumers to run concurrently.
        await Promise.all(
            [...handlers].map(handler => handler(payload))
        );
    }
}


// ---------------------------------------------------------------------------
// Application orchestration
// ---------------------------------------------------------------------------

class OrderApplicationService {
    constructor({
        inventory,
        payments,
        notifications,
        repository,
        validator,
        pricing,
        eventBus
    }) {
        this.inventory = inventory;
        this.payments = payments;
        this.notifications = notifications;
        this.repository = repository;
        this.validator = validator;
        this.pricing = pricing;
        this.eventBus = eventBus;
    }

    async createAndPay(order) {
        this.validator.validate(order);

        const reservations = [];

        try {
            for (const item of order.items) {
                await this.inventory.reserve(
                    item.product.id,
                    item.quantity
                );

                reservations.push({
                    productId: item.product.id,
                    quantity: item.quantity
                });
            }

            const amount = this.pricing.calculateTotal(order);

            const transactionId = await this.payments.charge(
                order.id,
                amount
            );

            order.markPaid();
            await this.repository.save(order);

            await this.eventBus.publish('order.paid', {
                orderId: order.id,
                customerEmail: order.customerEmail,
                amount,
                transactionId
            });

            return transactionId;
        } catch (error) {
            // Compensating actions restore reservations if a later operation
            // fails. This is useful when one distributed operation cannot be
            // rolled back atomically with another.
            await Promise.all(
                reservations.map(reservation =>
                    this.inventory.release(
                        reservation.productId,
                        reservation.quantity
                    )
                )
            );

            throw error;
        }
    }
}


// ---------------------------------------------------------------------------
// Event consumers
// ---------------------------------------------------------------------------

class AuditLog {
    constructor() {
        this.events = [];
    }

    async recordPayment(event) {
        this.events.push({
            type: 'ORDER_PAID',
            orderId: event.orderId,
            transactionId: event.transactionId,
            amount: event.amount
        });
    }
}

class ShippingCoordinator {
    constructor() {
        this.shipments = [];
    }

    async createShipment(event) {
        this.shipments.push({
            shipmentId: `SHIP-${event.orderId}`,
            orderId: event.orderId
        });
    }
}


// ---------------------------------------------------------------------------
// Architecture assembly
// ---------------------------------------------------------------------------

function createOrderSystem({
    paymentRejections = new Set(),
    notifier = new NotificationGateway()
} = {}) {
    const inventory = new MemoryInventory({
        LAPTOP: 4,
        MOUSE: 20,
        KEYBOARD: 8
    });

    const payments = new PaymentGateway({
        rejectOrders: paymentRejections
    });

    const repository = new MemoryOrderRepository();
    const validator = new OrderValidator();
    const pricing = new PricingService();
    const eventBus = new DomainEventBus();

    const audit = new AuditLog();
    const shipping = new ShippingCoordinator();

    eventBus.subscribe('order.paid', event =>
        notifier.sendPaymentConfirmation(
            event.customerEmail,
            event.orderId,
            event.amount
        )
    );

    eventBus.subscribe('order.paid', event =>
        audit.recordPayment(event)
    );

    eventBus.subscribe('order.paid', event =>
        shipping.createShipment(event)
    );

    const application = new OrderApplicationService({
        inventory,
        payments,
        notifications: notifier,
        repository,
        validator,
        pricing,
        eventBus
    });

    return {
        application,
        inventory,
        payments,
        repository,
        eventBus,
        audit,
        shipping,
        notifier
    };
}


// ---------------------------------------------------------------------------
// Demonstration: high cohesion
// ---------------------------------------------------------------------------

function demonstrateCohesion() {
    console.log('\n=== High cohesion ===');

    const pricing = new PricingService();

    const product = new Product(
        'SSD',
        '1 TB NVMe SSD',
        110
    );

    const order = new Order(
        'ORD-COHESION-001',
        'engineer@example.com',
        [
            {
                product,
                quantity: 2
            }
        ]
    );

    console.log(
        `PricingService calculates the order total: ${pricing.calculateTotal(order)}`
    );

    console.log(
        'The pricing component does not validate email addresses, reserve inventory, send notifications, or persist orders.'
    );
}


// ---------------------------------------------------------------------------
// Demonstration: loose coupling
// ---------------------------------------------------------------------------

async function demonstrateLooseCoupling() {
    console.log('\n=== Loose coupling ===');

    const system = createOrderSystem();

    const product = new Product(
        'MOUSE',
        'Wireless Mouse',
        40
    );

    const order = new Order(
        'ORD-LOOSE-001',
        'developer@example.com',
        [
            {
                product,
                quantity: 2
            }
        ]
    );

    const transactionId = await system.application.createAndPay(order);

    console.log(`Transaction: ${transactionId}`);
    console.log(`Order status: ${order.status}`);
    console.log(
        `Remaining mouse inventory: ${system.inventory.available('MOUSE')}`
    );
    console.log(`Audit events: ${system.audit.events.length}`);
    console.log(`Shipments: ${system.shipping.shipments.length}`);
}


// ---------------------------------------------------------------------------
// Demonstration: dependency substitution
// ---------------------------------------------------------------------------

async function demonstrateDependencySubstitution() {
    console.log('\n=== Dependency substitution ===');

    class TestNotificationGateway {
        constructor() {
            this.messages = [];
        }

        async sendPaymentConfirmation(
            customerEmail,
            orderId,
            amount
        ) {
            this.messages.push({
                customerEmail,
                orderId,
                amount
            });
        }
    }

    const notifier = new TestNotificationGateway();
    const system = createOrderSystem({ notifier });

    const product = new Product(
        'KEYBOARD',
        'Mechanical Keyboard',
        90
    );

    const order = new Order(
        'ORD-SUBSTITUTE-001',
        'test@example.com',
        [
            {
                product,
                quantity: 1
            }
        ]
    );

    await system.application.createAndPay(order);

    console.log(
        'The application service accepted a test notification implementation without changing its own code.'
    );

    console.log(
        `Captured notifications: ${notifier.messages.length}`
    );
}


// ---------------------------------------------------------------------------
// Demonstration: compensation after failure
// ---------------------------------------------------------------------------

async function demonstrateFailureHandling() {
    console.log('\n=== Failure and compensation ===');

    const rejectedOrderId = 'ORD-FAIL-001';

    const system = createOrderSystem({
        paymentRejections: new Set([rejectedOrderId])
    });

    const product = new Product(
        'LAPTOP',
        'Development Laptop',
        1500
    );

    const order = new Order(
        rejectedOrderId,
        'developer@example.com',
        [
            {
                product,
                quantity: 1
            }
        ]
    );

    const before = system.inventory.available('LAPTOP');

    try {
        await system.application.createAndPay(order);
    } catch (error) {
        console.log(`Expected failure: ${error.message}`);
    }

    const after = system.inventory.available('LAPTOP');

    console.log(`Inventory before: ${before}`);
    console.log(`Inventory after:  ${after}`);
    console.log(
        'The payment failure did not leave the inventory reservation behind.'
    );
}


// ---------------------------------------------------------------------------
// Demonstration: event-driven decoupling
// ---------------------------------------------------------------------------

async function demonstrateEventDecoupling() {
    console.log('\n=== Event-driven decoupling ===');

    const system = createOrderSystem();

    let analyticsEvents = 0;

    const unsubscribe = system.eventBus.subscribe(
        'order.paid',
        async event => {
            analyticsEvents += 1;

            console.log(
                `Analytics received payment event for ${event.orderId}`
            );
        }
    );

    const product = new Product(
        'MOUSE',
        'Wireless Mouse',
        40
    );

    const order = new Order(
        'ORD-EVENT-001',
        'analytics@example.com',
        [
            {
                product,
                quantity: 1
            }
        ]
    );

    await system.application.createAndPay(order);

    unsubscribe();

    console.log(`Analytics events received: ${analyticsEvents}`);
}


// ---------------------------------------------------------------------------
// Simple architecture checks
// ---------------------------------------------------------------------------

function assert(condition, message) {
    if (!condition) {
        throw new Error(`Assertion failed: ${message}`);
    }
}

async function runArchitectureChecks() {
    console.log('\n=== Architecture checks ===');

    const system = createOrderSystem();

    const product = new Product(
        'MOUSE',
        'Wireless Mouse',
        40
    );

    const order = new Order(
        'ORD-CHECK-001',
        'check@example.com',
        [
            {
                product,
                quantity: 2
            }
        ]
    );

    await system.application.createAndPay(order);

    assert(
        order.status === 'paid',
        'Successful payment must transition the order to paid'
    );

    assert(
        system.inventory.available('MOUSE') === 18,
        'Inventory must reflect the successful reservation'
    );

    assert(
        system.audit.events.length === 1,
        'Audit consumer must receive the payment event'
    );

    assert(
        system.shipping.shipments.length === 1,
        'Shipping consumer must receive the payment event'
    );

    console.log('All architecture checks passed.');
}


// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
    demonstrateCohesion();
    await demonstrateLooseCoupling();
    await demonstrateDependencySubstitution();
    await demonstrateFailureHandling();
    await demonstrateEventDecoupling();
    await runArchitectureChecks();

    console.log('\nArchitecture demonstration completed.');
}

main().catch(error => {
    console.error('Application failed:', error.message);
    process.exitCode = 1;
});
