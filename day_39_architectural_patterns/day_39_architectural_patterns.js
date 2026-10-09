"use strict";

/*
 * Architectural Patterns: Layered, MVC, and Hexagonal
 *
 * Domain: Order processing
 *
 * The same business capability is organized three different ways.
 * The implementations intentionally use JavaScript-specific behavior:
 * event-driven notifications, asynchronous adapters, controller/view
 * separation, and dependency injection through object composition.
 *
 * Run with:
 *   node architecture-patterns.js
 */

// ============================================================
// Shared domain objects
// ============================================================

class DomainError extends Error {
    constructor(message) {
        super(message);
        this.name = "DomainError";
    }
}

class Order {
    constructor(id, customerId, items) {
        if (!customerId?.trim()) {
            throw new DomainError("Customer ID is required.");
        }

        if (!Array.isArray(items) || items.length === 0) {
            throw new DomainError("An order must contain at least one item.");
        }

        for (const item of items) {
            if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
                throw new DomainError(
                    `Quantity must be positive for ${item.productId}.`
                );
            }

            if (!Number.isFinite(item.unitPrice) || item.unitPrice < 0) {
                throw new DomainError(
                    `Unit price must be a non-negative number for ${item.productId}.`
                );
            }
        }

        this.id = id;
        this.customerId = customerId;
        this.items = items.map(item => Object.freeze({ ...item }));
        this.status = "PENDING";
    }

    get total() {
        return Number(
            this.items
                .reduce(
                    (sum, item) => sum + item.quantity * item.unitPrice,
                    0
                )
                .toFixed(2)
        );
    }

    confirm() {
        if (this.status !== "PENDING") {
            throw new DomainError(
                `Cannot confirm an order in ${this.status} state.`
            );
        }

        this.status = "CONFIRMED";
    }
}

function orderId(prefix) {
    return `${prefix}-${crypto.randomUUID().slice(0, 8).toUpperCase()}`;
}

// ============================================================
// Layered architecture
// ============================================================
//
// HTTP/UI-like boundary
//        |
// Application service
//        |
// Domain model
//        |
// Infrastructure
//
// The application service coordinates the use case. Infrastructure
// implements persistence and notification concerns.
// ============================================================

class LayeredRepository {
    constructor() {
        this.orders = new Map();
    }

    async save(order) {
        this.orders.set(order.id, order);
    }

    async findById(id) {
        return this.orders.get(id) ?? null;
    }
}

class LayeredNotificationService {
    async sendConfirmation(order) {
        console.log(
            `[Layered notification] Confirmation sent for ${order.id}`
        );
    }
}

class LayeredOrderService {
    constructor(repository, notificationService) {
        this.repository = repository;
        this.notificationService = notificationService;
    }

    async createOrder(customerId, items) {
        const order = new Order(orderId("LAYER"), customerId, items);

        order.confirm();

        await this.repository.save(order);
        await this.notificationService.sendConfirmation(order);

        return order;
    }
}

async function layeredController(service, request) {
    try {
        const order = await service.createOrder(
            request.customerId,
            request.items
        );

        return {
            statusCode: 201,
            body: {
                id: order.id,
                status: order.status,
                total: order.total
            }
        };
    } catch (error) {
        if (error instanceof DomainError) {
            return {
                statusCode: 400,
                body: { error: error.message }
            };
        }

        throw error;
    }
}

// ============================================================
// MVC architecture
// ============================================================
//
// Controller:
//   Interprets an incoming action.
//
// Model:
//   Owns application state and domain behavior.
//
// View:
//   Converts model state into a representation.
//
// JavaScript's object model makes it natural to compose these
// responsibilities while keeping rendering independent from state.
// ============================================================

class OrderModel {
    constructor() {
        this.orders = new Map();
    }

    create(customerId, items) {
        const order = new Order(orderId("MVC"), customerId, items);
        order.confirm();
        this.orders.set(order.id, order);
        return order;
    }

    get(id) {
        return this.orders.get(id) ?? null;
    }
}

class OrderView {
    render(order) {
        if (!order) {
            return {
                page: "error",
                message: "Order not found."
            };
        }

        return {
            page: "order",
            orderId: order.id,
            customerId: order.customerId,
            status: order.status,
            total: order.total,
            lines: order.items.map(item => ({
                productId: item.productId,
                quantity: item.quantity,
                unitPrice: item.unitPrice,
                subtotal: Number(
                    (item.quantity * item.unitPrice).toFixed(2)
                )
            }))
        };
    }

    renderError(error) {
        return {
            page: "error",
            message: error.message
        };
    }
}

class OrderController {
    constructor(model, view) {
        this.model = model;
        this.view = view;
    }

    create(request) {
        try {
            const order = this.model.create(
                request.customerId,
                request.items
            );

            return this.view.render(order);
        } catch (error) {
            if (error instanceof DomainError) {
                return this.view.renderError(error);
            }

            throw error;
        }
    }
}

// ============================================================
// Hexagonal architecture
// ============================================================
//
// The application core depends on behavioral contracts rather than
// database or transport classes.
//
// Driving adapter:
//   Invokes the application.
//
// Application port:
//   Defines the use case.
//
// Driven ports:
//   Describe persistence and notification capabilities.
//
// Adapters:
//   Implement those ports.
//
// JavaScript does not require interfaces at runtime, so the port
// contract is represented by documented method expectations and
// runtime validation at the composition boundary.
// ============================================================

class HexagonalApplication {
    constructor({ repository, notifier }) {
        if (
            typeof repository.save !== "function" ||
            typeof repository.findById !== "function"
        ) {
            throw new TypeError("Repository adapter does not implement its port.");
        }

        if (typeof notifier.sendConfirmation !== "function") {
            throw new TypeError("Notification adapter does not implement its port.");
        }

        this.repository = repository;
        this.notifier = notifier;
    }

    async placeOrder(customerId, items) {
        const order = new Order(orderId("HEX"), customerId, items);
        order.confirm();

        await this.repository.save(order);
        await this.notifier.sendConfirmation(order);

        return order;
    }
}

class MemoryOrderAdapter {
    constructor() {
        this.store = new Map();
    }

    async save(order) {
        this.store.set(order.id, structuredClone(order));
    }

    async findById(id) {
        const order = this.store.get(id);
        return order ? structuredClone(order) : null;
    }
}

class EventNotificationAdapter {
    constructor() {
        this.events = [];
    }

    async sendConfirmation(order) {
        this.events.push({
            type: "ORDER_CONFIRMED",
            orderId: order.id,
            customerId: order.customerId,
            createdAt: new Date().toISOString()
        });
    }
}

// ============================================================
// Event-driven adapter
// ============================================================
//
// EventEmitter is infrastructure. The domain does not need to know
// that notifications are delivered through an event bus.
//
// This demonstrates a realistic JavaScript advantage: asynchronous,
// event-driven integration can remain outside the application core.
// ============================================================

const { EventEmitter } = require("node:events");

class EventBusNotificationAdapter {
    constructor(eventBus) {
        this.eventBus = eventBus;
    }

    async sendConfirmation(order) {
        this.eventBus.emit("order.confirmed", {
            orderId: order.id,
            customerId: order.customerId
        });
    }
}

// ============================================================
// Test the hexagonal core with replaceable adapters
// ============================================================

async function testHexagonalCore() {
    const repository = new MemoryOrderAdapter();
    const notifier = new EventNotificationAdapter();

    const application = new HexagonalApplication({
        repository,
        notifier
    });

    const order = await application.placeOrder("TEST-001", [
        {
            productId: "SERVER",
            quantity: 1,
            unitPrice: 1500
        },
        {
            productId: "SSD",
            quantity: 2,
            unitPrice: 180
        }
    ]);

    if (order.total !== 1860) {
        throw new Error("Unexpected order total.");
    }

    if (notifier.events.length !== 1) {
        throw new Error("Expected one notification event.");
    }

    console.log("[Test] Hexagonal core test passed.");
}

// ============================================================
// Compare the three architectures
// ============================================================

async function demonstrateArchitectures() {
    console.log("\n=== Layered ===");

    const layeredRepository = new LayeredRepository();
    const layeredNotifications = new LayeredNotificationService();
    const layeredService = new LayeredOrderService(
        layeredRepository,
        layeredNotifications
    );

    console.log(
        await layeredController(layeredService, {
            customerId: "CUST-LAYER",
            items: [
                { productId: "KEYBOARD", quantity: 2, unitPrice: 75 },
                { productId: "MOUSE", quantity: 1, unitPrice: 40 }
            ]
        })
    );

    console.log("\n=== MVC ===");

    const model = new OrderModel();
    const view = new OrderView();
    const controller = new OrderController(model, view);

    console.log(
        controller.create({
            customerId: "CUST-MVC",
            items: [
                { productId: "MONITOR", quantity: 1, unitPrice: 300 },
                { productId: "CABLE", quantity: 3, unitPrice: 12.5 }
            ]
        })
    );

    console.log("\n=== Hexagonal ===");

    const eventBus = new EventEmitter();

    eventBus.on("order.confirmed", event => {
        console.log(
            `[Event adapter] ${event.orderId} confirmed for ${event.customerId}`
        );
    });

    const hexApplication = new HexagonalApplication({
        repository: new MemoryOrderAdapter(),
        notifier: new EventBusNotificationAdapter(eventBus)
    });

    const hexOrder = await hexApplication.placeOrder(
        "CUST-HEX",
        [
            { productId: "API-GATEWAY", quantity: 1, unitPrice: 500 },
            { productId: "CACHE", quantity: 2, unitPrice: 125 }
        ]
    );

    console.log({
        id: hexOrder.id,
        total: hexOrder.total,
        status: hexOrder.status
    });

    await testHexagonalCore();

    console.log("\n=== Failure handling ===");

    try {
        await hexApplication.placeOrder("CUST-BAD", [
            { productId: "INVALID", quantity: 0, unitPrice: 100 }
        ]);
    } catch (error) {
        console.log(`Rejected invalid order: ${error.message}`);
    }

    console.log("\n=== Architectural distinction ===");
    console.log(
        "Layered organizes responsibilities into conventional vertical layers."
    );
    console.log(
        "MVC separates input control, application state, and presentation."
    );
    console.log(
        "Hexagonal protects the core from transport and infrastructure choices."
    );
}

demonstrateArchitectures().catch(error => {
    console.error("Application failure:", error);
    process.exitCode = 1;
});
