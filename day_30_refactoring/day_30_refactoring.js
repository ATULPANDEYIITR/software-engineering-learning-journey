"use strict";

/*
 * Refactoring Techniques and Code Improvement
 *
 * This file approaches refactoring from JavaScript's perspective.
 * It demonstrates:
 * - extracting cohesive functions
 * - replacing magic values with policy objects
 * - encapsulating mutable state
 * - replacing large conditionals with strategies
 * - separating pure transformations from side effects
 * - dependency injection
 * - composing a domain pipeline
 * - event-driven change notification
 * - runtime validation
 * - asynchronous infrastructure boundaries
 *
 * The examples use modern Node.js features and require no external packages.
 */

// ---------------------------------------------------------------------------
// Code smell: a large conditional with duplicated business decisions
// ---------------------------------------------------------------------------

function legacyCalculateShipping(order) {
  if (order.method === "standard") {
    if (order.weightKg > 10) {
      return 100 + order.distanceKm * 0.5;
    }
    return 50 + order.distanceKm * 0.2;
  }

  if (order.method === "express") {
    if (order.weightKg > 10) {
      return 180 + order.distanceKm * 0.8;
    }
    return 120 + order.distanceKm * 0.35;
  }

  if (order.method === "pickup") {
    return 0;
  }

  throw new Error(`Unsupported shipping method: ${order.method}`);
}


// ---------------------------------------------------------------------------
// Replace Conditional with Strategy
// ---------------------------------------------------------------------------

const SHIPPING_RULES = Object.freeze({
  standard: Object.freeze({
    base: 50,
    weightRate: 12,
    distanceRate: 0.2,
  }),
  express: Object.freeze({
    base: 120,
    weightRate: 18,
    distanceRate: 0.35,
  }),
});

class StandardShipping {
  calculate(weightKg, distanceKm) {
    return 50 + weightKg * 12 + distanceKm * 0.2;
  }
}

class ExpressShipping {
  calculate(weightKg, distanceKm) {
    return 120 + weightKg * 18 + distanceKm * 0.35;
  }
}

class PickupShipping {
  calculate() {
    return 0;
  }
}

function validateNonNegativeNumber(value, fieldName) {
  if (!Number.isFinite(value) || value < 0) {
    throw new TypeError(`${fieldName} must be a non-negative number`);
  }
}

function calculateShipping(order) {
  validateNonNegativeNumber(order.weightKg, "weightKg");
  validateNonNegativeNumber(order.distanceKm, "distanceKm");

  const strategies = {
    standard: new StandardShipping(),
    express: new ExpressShipping(),
    pickup: new PickupShipping(),
  };

  const strategy = strategies[order.method];

  if (!strategy) {
    throw new Error(`Unsupported shipping method: ${order.method}`);
  }

  return Number(
    strategy.calculate(order.weightKg, order.distanceKm).toFixed(2)
  );
}


// ---------------------------------------------------------------------------
// Extract Method and Replace Magic Values
// ---------------------------------------------------------------------------

const PRICING_POLICY = Object.freeze({
  taxRate: 0.18,
  freeShippingThreshold: 1000,
  handlingFee: 80,
});

function validateLineItem(item) {
  if (!item.productId || typeof item.productId !== "string") {
    throw new TypeError("productId is required");
  }

  if (!Number.isFinite(item.unitPrice) || item.unitPrice < 0) {
    throw new TypeError("unitPrice must be non-negative");
  }

  if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
    throw new TypeError("quantity must be a positive integer");
  }
}

function calculateSubtotal(items) {
  if (!Array.isArray(items) || items.length === 0) {
    throw new Error("an order requires at least one item");
  }

  const productIds = new Set();
  let subtotal = 0;

  for (const item of items) {
    validateLineItem(item);

    if (productIds.has(item.productId)) {
      throw new Error(`Duplicate product: ${item.productId}`);
    }

    productIds.add(item.productId);
    subtotal += item.unitPrice * item.quantity;
  }

  return Number(subtotal.toFixed(2));
}

function calculateOrderTotals(items) {
  const subtotal = calculateSubtotal(items);

  const tax = Number(
    (subtotal * PRICING_POLICY.taxRate).toFixed(2)
  );

  const handling =
    subtotal >= PRICING_POLICY.freeShippingThreshold
      ? 0
      : PRICING_POLICY.handlingFee;

  return Object.freeze({
    subtotal,
    tax,
    handling,
    total: Number((subtotal + tax + handling).toFixed(2)),
  });
}


// ---------------------------------------------------------------------------
// Encapsulate Collection
// ---------------------------------------------------------------------------

class ShoppingCart {
  #items = new Map();

  add(item) {
    validateLineItem(item);

    if (this.#items.has(item.productId)) {
      throw new Error(`Product already exists: ${item.productId}`);
    }

    this.#items.set(item.productId, Object.freeze({ ...item }));
  }

  remove(productId) {
    if (!this.#items.delete(productId)) {
      throw new Error(`Product does not exist: ${productId}`);
    }
  }

  get items() {
    return [...this.#items.values()];
  }

  get total() {
    return calculateSubtotal(this.items);
  }
}


// ---------------------------------------------------------------------------
// Replace Primitive Obsession with Value Objects
// ---------------------------------------------------------------------------

class EmailAddress {
  #value;

  constructor(value) {
    const normalized = String(value).trim().toLowerCase();

    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) {
      throw new TypeError(`Invalid email address: ${value}`);
    }

    this.#value = normalized;
    Object.freeze(this);
  }

  toString() {
    return this.#value;
  }

  get value() {
    return this.#value;
  }
}

class Money {
  constructor(amount, currency = "INR") {
    if (!Number.isFinite(amount) || amount < 0) {
      throw new TypeError("Money amount must be non-negative");
    }

    if (!/^[A-Z]{3}$/.test(currency)) {
      throw new TypeError("Currency must use a three-letter code");
    }

    this.amount = Number(amount.toFixed(2));
    this.currency = currency;

    Object.freeze(this);
  }

  add(other) {
    if (this.currency !== other.currency) {
      throw new Error("Cannot add different currencies");
    }

    return new Money(
      this.amount + other.amount,
      this.currency
    );
  }
}


// ---------------------------------------------------------------------------
// Separate Pure Transformation from Side Effects
// ---------------------------------------------------------------------------

function buildInvoice({ invoiceId, email, amount }) {
  if (!invoiceId || typeof invoiceId !== "string") {
    throw new TypeError("invoiceId is required");
  }

  return Object.freeze({
    invoiceId,
    email: new EmailAddress(email),
    amount:
      amount instanceof Money
        ? amount
        : new Money(amount),
  });
}

function invoiceToJSON(invoice) {
  return JSON.stringify(
    {
      invoiceId: invoice.invoiceId,
      email: invoice.email.value,
      amount: invoice.amount.amount,
      currency: invoice.amount.currency,
    },
    null,
    2
  );
}


// ---------------------------------------------------------------------------
// Dependency Injection for an asynchronous infrastructure boundary
// ---------------------------------------------------------------------------

class ConsoleNotificationGateway {
  async send(recipient, subject, body) {
    await Promise.resolve();

    console.log(
      `[notification] ${recipient.value} | ${subject} | ${body}`
    );
  }
}

class InMemoryNotificationGateway {
  constructor() {
    this.messages = [];
  }

  async send(recipient, subject, body) {
    this.messages.push({
      recipient: recipient.value,
      subject,
      body,
    });
  }
}

class OrderNotifier {
  constructor(notificationGateway) {
    this.notificationGateway = notificationGateway;
  }

  async orderCreated(customerEmail, orderId, total) {
    await this.notificationGateway.send(
      customerEmail,
      `Order ${orderId} created`,
      `Order total: ${total.amount.toFixed(2)} ${total.currency}`
    );
  }
}


// ---------------------------------------------------------------------------
// Pipeline-style refactoring
// ---------------------------------------------------------------------------

function validateCustomer(customer) {
  if (!customer || typeof customer !== "object") {
    throw new TypeError("customer is required");
  }

  if (!customer.id || typeof customer.id !== "string") {
    throw new TypeError("customer.id is required");
  }

  new EmailAddress(customer.email);
}

function createOrderModel(input) {
  validateCustomer(input.customer);

  const totals = calculateOrderTotals(input.items);

  const freight = calculateShipping({
    method: input.shippingMethod,
    weightKg: input.weightKg,
    distanceKm: input.distanceKm,
  });

  return Object.freeze({
    orderId: input.orderId,
    customerId: input.customer.id,
    subtotal: totals.subtotal,
    tax: totals.tax,
    handling: totals.handling,
    freight,
    total: Number(
      (totals.total + freight).toFixed(2)
    ),
  });
}


// ---------------------------------------------------------------------------
// Repository abstraction
// ---------------------------------------------------------------------------

class InMemoryOrderRepository {
  #orders = new Map();

  async save(order) {
    if (this.#orders.has(order.orderId)) {
      throw new Error(`Order already exists: ${order.orderId}`);
    }

    this.#orders.set(order.orderId, order);
  }

  async find(orderId) {
    return this.#orders.get(orderId) ?? null;
  }
}


// ---------------------------------------------------------------------------
// Event-driven architecture
// ---------------------------------------------------------------------------

class DomainEventBus {
  #listeners = new Map();

  on(eventName, handler) {
    if (!this.#listeners.has(eventName)) {
      this.#listeners.set(eventName, new Set());
    }

    this.#listeners.get(eventName).add(handler);

    // Returning an unsubscribe function prevents permanent event listeners
    // from becoming hidden memory leaks in long-running processes.
    return () => {
      this.#listeners.get(eventName)?.delete(handler);
    };
  }

  async emit(eventName, payload) {
    const listeners = this.#listeners.get(eventName) ?? [];

    for (const handler of listeners) {
      await handler(payload);
    }
  }
}


// ---------------------------------------------------------------------------
// Refactored application service
// ---------------------------------------------------------------------------

class OrderService {
  constructor(repository, notifier, eventBus) {
    this.repository = repository;
    this.notifier = notifier;
    this.eventBus = eventBus;
  }

  async placeOrder(input) {
    if (!input.orderId) {
      throw new TypeError("orderId is required");
    }

    const order = createOrderModel(input);

    await this.repository.save(order);

    const email = new EmailAddress(input.customer.email);
    const total = new Money(order.total);

    await this.notifier.orderCreated(
      email,
      order.orderId,
      total
    );

    await this.eventBus.emit("order.created", order);

    return order;
  }
}


// ---------------------------------------------------------------------------
// Characterization test helper
// ---------------------------------------------------------------------------

function assertEqual(actual, expected, message) {
  if (actual !== expected) {
    throw new Error(
      `${message}\nExpected: ${expected}\nActual: ${actual}`
    );
  }
}

function assertThrows(callback, message) {
  let threw = false;

  try {
    callback();
  } catch {
    threw = true;
  }

  if (!threw) {
    throw new Error(message);
  }
}

async function runTests() {
  const legacyCases = [
    {
      order: {
        method: "standard",
        weightKg: 2,
        distanceKm: 100,
      },
      expected: 74,
    },
    {
      order: {
        method: "express",
        weightKg: 2,
        distanceKm: 100,
      },
      expected: 155,
    },
    {
      order: {
        method: "pickup",
        weightKg: 2,
        distanceKm: 100,
      },
      expected: 0,
    },
  ];

  for (const testCase of legacyCases) {
    assertEqual(
      calculateShipping(testCase.order),
      testCase.expected,
      "Refactored shipping behavior changed"
    );
  }

  const cart = new ShoppingCart();

  cart.add({
    productId: "KB-1",
    unitPrice: 2500,
    quantity: 1,
  });

  assertEqual(
    cart.total,
    2500,
    "Cart total should equal item subtotal"
  );

  assertThrows(
    () =>
      cart.add({
        productId: "KB-1",
        unitPrice: 2500,
        quantity: 1,
      }),
    "Duplicate cart products should be rejected"
  );

  assertThrows(
    () => new EmailAddress("invalid"),
    "Invalid email should be rejected"
  );

  assertThrows(
    () => new Money(100, "USD").add(new Money(50, "INR")),
    "Mixed currencies should be rejected"
  );

  const gateway = new InMemoryNotificationGateway();
  const repository = new InMemoryOrderRepository();
  const eventBus = new DomainEventBus();

  const receivedEvents = [];
  eventBus.on("order.created", async (event) => {
    receivedEvents.push(event.orderId);
  });

  const service = new OrderService(
    repository,
    new OrderNotifier(gateway),
    eventBus
  );

  const order = await service.placeOrder({
    orderId: "ORD-JS-100",
    customer: {
      id: "CUS-100",
      email: "customer@example.com",
    },
    items: [
      {
        productId: "CAM-1",
        unitPrice: 5000,
        quantity: 1,
      },
      {
        productId: "MIC-1",
        unitPrice: 1500,
        quantity: 2,
      },
    ],
    shippingMethod: "express",
    weightKg: 3,
    distanceKm: 25,
  });

  assertEqual(
    order.total,
    9228.75,
    "Order total should follow the refactored pricing pipeline"
  );

  assertEqual(
    gateway.messages.length,
    1,
    "Exactly one notification should be emitted"
  );

  assertEqual(
    receivedEvents[0],
    "ORD-JS-100",
    "Order-created event should contain the order ID"
  );

  const stored = await repository.find("ORD-JS-100");

  if (!stored) {
    throw new Error("Order should be persisted");
  }

  console.log("JavaScript tests passed.");
}


// ---------------------------------------------------------------------------
// Practical demonstration
// ---------------------------------------------------------------------------

async function main() {
  console.log("REFACTORING AND CODE IMPROVEMENT");
  console.log("================================");

  const orderItems = [
    {
      productId: "LAPTOP-1",
      unitPrice: 75000,
      quantity: 1,
    },
    {
      productId: "MOUSE-1",
      unitPrice: 1800,
      quantity: 1,
    },
  ];

  console.log("\nOrder totals:");
  console.log(calculateOrderTotals(orderItems));

  console.log("\nShipping strategies:");

  for (const method of ["standard", "express", "pickup"]) {
    console.log(
      method,
      calculateShipping({
        method,
        weightKg: 4,
        distanceKm: 120,
      })
    );
  }

  console.log("\nEncapsulated cart:");
  const cart = new ShoppingCart();

  cart.add({
    productId: "MONITOR-1",
    unitPrice: 24000,
    quantity: 1,
  });

  cart.add({
    productId: "STAND-1",
    unitPrice: 4500,
    quantity: 2,
  });

  console.log({
    items: cart.items,
    total: cart.total,
  });

  console.log("\nInvoice:");
  const invoice = buildInvoice({
    invoiceId: "INV-JS-100",
    email: "buyer@example.com",
    amount: 3499.99,
  });

  console.log(invoiceToJSON(invoice));

  console.log("\nAsynchronous order service:");

  const repository = new InMemoryOrderRepository();
  const gateway = new InMemoryNotificationGateway();
  const eventBus = new DomainEventBus();

  eventBus.on("order.created", async (order) => {
    console.log(
      `Event received for ${order.orderId}; total=${order.total}`
    );
  });

  const service = new OrderService(
    repository,
    new OrderNotifier(gateway),
    eventBus
  );

  const order = await service.placeOrder({
    orderId: "ORD-JS-200",
    customer: {
      id: "CUS-JS-200",
      email: "buyer@example.com",
    },
    items: [
      {
        productId: "HEADSET-1",
        unitPrice: 6500,
        quantity: 1,
      },
    ],
    shippingMethod: "standard",
    weightKg: 1.5,
    distanceKm: 50,
  });

  console.log(order);
  console.log("Notifications:", gateway.messages.length);

  await runTests();
}

main().catch((error) => {
  console.error("Application failure:", error.message);
  process.exitCode = 1;
});
