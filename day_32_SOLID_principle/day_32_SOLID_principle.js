/**
 * SOLID Principles in JavaScript
 *
 * This file models an order-processing domain and demonstrates:
 *
 * SRP - Single Responsibility Principle
 * OCP - Open/Closed Principle
 * LSP - Liskov Substitution Principle
 * ISP - Interface Segregation Principle
 * DIP - Dependency Inversion Principle
 *
 * Runtime: Node.js 18+
 *
 * No npm dependencies are required.
 */

"use strict";

const assert = require("node:assert/strict");

function heading(title) {
  console.log(`\n${"=".repeat(78)}\n${title}\n${"=".repeat(78)}`);
}

function roundMoney(value) {
  if (!Number.isFinite(value)) {
    throw new TypeError("Monetary value must be finite.");
  }

  return Math.round((value + Number.EPSILON) * 100) / 100;
}

// ---------------------------------------------------------------------------
// Domain objects
// ---------------------------------------------------------------------------

class Product {
  constructor(id, name, price) {
    if (!id || !name) {
      throw new Error("Product ID and name are required.");
    }

    if (!Number.isFinite(price) || price < 0) {
      throw new Error("Product price must be a non-negative number.");
    }

    this.id = id;
    this.name = name;
    this.price = roundMoney(price);
  }
}

class OrderLine {
  constructor(product, quantity) {
    if (!(product instanceof Product)) {
      throw new TypeError("OrderLine requires a Product.");
    }

    if (!Number.isInteger(quantity) || quantity <= 0) {
      throw new Error("Quantity must be a positive integer.");
    }

    this.product = product;
    this.quantity = quantity;
  }

  get subtotal() {
    return roundMoney(this.product.price * this.quantity);
  }
}

class Order {
  constructor(id, customerEmail, lines) {
    if (!id.trim()) {
      throw new Error("Order ID cannot be empty.");
    }

    if (!customerEmail.includes("@")) {
      throw new Error("Customer email is invalid.");
    }

    if (!Array.isArray(lines) || lines.length === 0) {
      throw new Error("Order must contain at least one line.");
    }

    this.id = id;
    this.customerEmail = customerEmail;
    this.lines = [...lines];
    this.status = "NEW";
  }

  get subtotal() {
    return roundMoney(
      this.lines.reduce((total, line) => total + line.subtotal, 0)
    );
  }
}

// ===========================================================================
// SRP
// ===========================================================================

/*
 * A class becomes difficult to maintain when one object owns unrelated
 * responsibilities. JavaScript makes this particularly easy to do because
 * objects can freely combine calculation, persistence, and notification.
 *
 * The solution below separates those responsibilities into independent
 * collaborators.
 */

class PriceCalculator {
  calculate(order, taxRate, discount = 0) {
    if (!(order instanceof Order)) {
      throw new TypeError("calculate expects an Order.");
    }

    if (!Number.isFinite(taxRate) || taxRate < 0 || taxRate > 1) {
      throw new Error("Tax rate must be between 0 and 1.");
    }

    if (!Number.isFinite(discount) || discount < 0) {
      throw new Error("Discount must be non-negative.");
    }

    if (discount > order.subtotal) {
      throw new Error("Discount cannot exceed subtotal.");
    }

    const taxable = order.subtotal - discount;
    const tax = roundMoney(taxable * taxRate);

    return {
      subtotal: order.subtotal,
      discount: roundMoney(discount),
      tax,
      total: roundMoney(taxable + tax),
    };
  }
}

class MemoryOrderRepository {
  constructor() {
    this.orders = new Map();
  }

  save(order, pricing) {
    this.orders.set(order.id, {
      orderId: order.id,
      email: order.customerEmail,
      status: order.status,
      total: pricing.total,
    });
  }

  find(orderId) {
    return this.orders.get(orderId) ?? null;
  }
}

class ConsoleNotifier {
  send(email, subject, message) {
    console.log(`[NOTIFICATION] ${email} | ${subject} | ${message}`);
  }
}

class SRPOrderService {
  constructor(calculator, repository, notifier) {
    this.calculator = calculator;
    this.repository = repository;
    this.notifier = notifier;
  }

  place(order) {
    const pricing = this.calculator.calculate(order, 0.18);

    order.status = "PAID";
    this.repository.save(order, pricing);

    this.notifier.send(
      order.customerEmail,
      "Order confirmation",
      `Order ${order.id} total is ${pricing.total.toFixed(2)}`
    );

    return pricing;
  }
}

function demonstrateSRP() {
  heading("SRP: Cohesive responsibilities");

  const product = new Product("KB-1", "Mechanical Keyboard", 79.99);
  const order = new Order(
    "ORD-SRP",
    "srp@example.com",
    [new OrderLine(product, 2)]
  );

  const service = new SRPOrderService(
    new PriceCalculator(),
    new MemoryOrderRepository(),
    new ConsoleNotifier()
  );

  const pricing = service.place(order);

  console.log("Pricing result:", pricing);
}

// ===========================================================================
// OCP
// ===========================================================================

/*
 * JavaScript does not require formal interfaces, so a policy object can
 * satisfy a behavioral contract simply by exposing calculateDiscount().
 *
 * The checkout engine is closed to modification with respect to discount
 * rules. New objects can extend behavior without editing the engine.
 */

class NoDiscountPolicy {
  calculateDiscount(order) {
    return 0;
  }
}

class PercentageDiscountPolicy {
  constructor(rate) {
    if (!Number.isFinite(rate) || rate < 0 || rate > 1) {
      throw new Error("Discount rate must be between 0 and 1.");
    }

    this.rate = rate;
  }

  calculateDiscount(order) {
    return roundMoney(order.subtotal * this.rate);
  }
}

class QuantityDiscountPolicy {
  constructor(minimumQuantity, rate) {
    if (!Number.isInteger(minimumQuantity) || minimumQuantity <= 0) {
      throw new Error("Minimum quantity must be positive.");
    }

    if (!Number.isFinite(rate) || rate < 0 || rate > 1) {
      throw new Error("Discount rate must be between 0 and 1.");
    }

    this.minimumQuantity = minimumQuantity;
    this.rate = rate;
  }

  calculateDiscount(order) {
    return roundMoney(
      order.lines.reduce((discount, line) => {
        if (line.quantity >= this.minimumQuantity) {
          return discount + line.subtotal * this.rate;
        }

        return discount;
      }, 0)
    );
  }
}

class CustomerTierPolicy {
  static rates = Object.freeze({
    standard: 0,
    silver: 0.05,
    gold: 0.1,
    platinum: 0.15,
  });

  constructor(tier) {
    const normalizedTier = tier.toLowerCase();

    if (!(normalizedTier in CustomerTierPolicy.rates)) {
      throw new Error(`Unsupported customer tier: ${tier}`);
    }

    this.tier = normalizedTier;
  }

  calculateDiscount(order) {
    return roundMoney(
      order.subtotal * CustomerTierPolicy.rates[this.tier]
    );
  }
}

class CheckoutPricing {
  constructor(discountPolicy, calculator = new PriceCalculator()) {
    if (
      !discountPolicy ||
      typeof discountPolicy.calculateDiscount !== "function"
    ) {
      throw new TypeError(
        "Discount policy must expose calculateDiscount()."
      );
    }

    this.discountPolicy = discountPolicy;
    this.calculator = calculator;
  }

  calculate(order) {
    const discount = this.discountPolicy.calculateDiscount(order);

    return this.calculator.calculate(order, 0.18, discount);
  }
}

function demonstrateOCP() {
  heading("OCP: Add pricing policies without editing checkout");

  const product = new Product("DOCK-1", "USB-C Dock", 149.5);
  const order = new Order(
    "ORD-OCP",
    "ocp@example.com",
    [new OrderLine(product, 1)]
  );

  const policies = [
    ["No discount", new NoDiscountPolicy()],
    ["Percentage", new PercentageDiscountPolicy(0.1)],
    ["Customer tier", new CustomerTierPolicy("gold")],
    ["Bulk quantity", new QuantityDiscountPolicy(2, 0.15)],
  ];

  for (const [name, policy] of policies) {
    const pricing = new CheckoutPricing(policy).calculate(order);
    console.log(
      `${name}: discount=${pricing.discount.toFixed(2)}, ` +
      `total=${pricing.total.toFixed(2)}`
    );
  }
}

// ===========================================================================
// LSP
// ===========================================================================

/*
 * JavaScript is structurally typed at runtime. LSP therefore depends heavily
 * on behavioral contracts rather than inheritance syntax.
 *
 * A useful contract for a payment object is:
 *
 * charge(amount) -> transaction identifier
 *
 * A refundable payment method has a stronger capability:
 *
 * refund(transactionId, amount)
 *
 * A payment provider that cannot refund must not pretend to satisfy the
 * stronger contract.
 */

class CardPayment {
  constructor() {
    this.transactions = new Map();
    this.sequence = 0;
  }

  charge(amount) {
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new Error("Charge must be positive.");
    }

    this.sequence += 1;

    const transactionId = `CARD-${String(this.sequence).padStart(4, "0")}`;

    this.transactions.set(transactionId, roundMoney(amount));

    return transactionId;
  }

  refund(transactionId, amount) {
    if (!this.transactions.has(transactionId)) {
      throw new Error("Unknown card transaction.");
    }

    const originalAmount = this.transactions.get(transactionId);

    if (!Number.isFinite(amount) || amount <= 0 || amount > originalAmount) {
      throw new Error("Refund amount is invalid.");
    }

    this.transactions.set(
      transactionId,
      roundMoney(originalAmount - amount)
    );
  }
}

class GiftCardPayment {
  constructor(balance) {
    if (!Number.isFinite(balance) || balance < 0) {
      throw new Error("Gift-card balance must be non-negative.");
    }

    this.balance = roundMoney(balance);
  }

  charge(amount) {
    if (!Number.isFinite(amount) || amount <= 0) {
      throw new Error("Charge must be positive.");
    }

    if (amount > this.balance) {
      throw new Error("Insufficient gift-card balance.");
    }

    this.balance = roundMoney(this.balance - amount);

    return "GIFT-CHARGE";
  }
}

function chargePayment(paymentMethod, amount) {
  if (!paymentMethod || typeof paymentMethod.charge !== "function") {
    throw new TypeError("Payment method must provide charge().");
  }

  return paymentMethod.charge(amount);
}

function refundPayment(refundablePayment, transactionId, amount) {
  if (
    !refundablePayment ||
    typeof refundablePayment.refund !== "function"
  ) {
    throw new TypeError(
      "The supplied payment object does not satisfy the refundable contract."
    );
  }

  refundablePayment.refund(transactionId, amount);
}

function demonstrateLSP() {
  heading("LSP: Preserve behavioral contracts");

  const card = new CardPayment();
  const giftCard = new GiftCardPayment(100);

  const cardTransaction = chargePayment(card, 40);
  const giftTransaction = chargePayment(giftCard, 25);

  console.log("Card transaction:", cardTransaction);
  console.log("Gift-card transaction:", giftTransaction);
  console.log("Gift-card balance:", giftCard.balance);

  refundPayment(card, cardTransaction, 10);

  assert.equal(
    card.transactions.get(cardTransaction),
    30
  );

  try {
    refundPayment(giftCard, giftTransaction, 5);
  } catch (error) {
    console.log("Invalid stronger-contract substitution rejected:", error.message);
  }
}

// ===========================================================================
// ISP
// ===========================================================================

/*
 * JavaScript has no built-in interface keyword. Small interfaces can instead
 * be represented by the smallest method sets expected by each client.
 *
 * A reporting component needs readOrder().
 * A persistence component needs saveOrder().
 * An auditing component needs recordEvent().
 *
 * No consumer is forced to depend on methods unrelated to its responsibility.
 */

class OrderStore {
  constructor() {
    this.orders = new Map();
    this.events = [];
  }

  saveOrder(summary) {
    this.orders.set(summary.orderId, { ...summary });
  }

  readOrder(orderId) {
    return this.orders.get(orderId) ?? null;
  }

  recordEvent(orderId, eventName) {
    this.events.push({
      orderId,
      eventName,
      timestamp: new Date().toISOString(),
    });
  }
}

class ReportingClient {
  constructor(reader) {
    if (!reader || typeof reader.readOrder !== "function") {
      throw new TypeError("ReportingClient requires readOrder().");
    }

    this.reader = reader;
  }

  render(orderId) {
    const order = this.reader.readOrder(orderId);

    if (!order) {
      throw new Error(`Order ${orderId} was not found.`);
    }

    return (
      `Order ${order.orderId} | ` +
      `customer=${order.customerEmail} | ` +
      `total=${order.total.toFixed(2)}`
    );
  }
}

class PersistenceClient {
  constructor(writer, auditor) {
    if (!writer || typeof writer.saveOrder !== "function") {
      throw new TypeError("PersistenceClient requires saveOrder().");
    }

    if (!auditor || typeof auditor.recordEvent !== "function") {
      throw new TypeError("PersistenceClient requires recordEvent().");
    }

    this.writer = writer;
    this.auditor = auditor;
  }

  save(summary) {
    this.writer.saveOrder(summary);
    this.auditor.recordEvent(summary.orderId, "ORDER_SAVED");
  }
}

function demonstrateISP() {
  heading("ISP: Clients depend only on required capabilities");

  const store = new OrderStore();

  const persistence = new PersistenceClient(store, store);

  persistence.save({
    orderId: "ORD-ISP",
    customerEmail: "isp@example.com",
    total: 125.5,
  });

  const reporting = new ReportingClient(store);

  console.log(reporting.render("ORD-ISP"));
  console.log("Audit events:", store.events);
}

// ===========================================================================
// DIP
// ===========================================================================

/*
 * The checkout workflow below is a high-level policy.
 *
 * It does not construct a concrete database, payment vendor, inventory
 * service, or notification provider. Dependencies are injected.
 *
 * The small adapters below act as infrastructure implementations.
 */

class MemoryInventory {
  constructor(initialStock) {
    this.stock = new Map(Object.entries(initialStock));
  }

  reserve(productId, quantity) {
    const available = this.stock.get(productId) ?? 0;

    if (quantity > available) {
      throw new Error(
        `Insufficient stock for ${productId}: ` +
        `requested=${quantity}, available=${available}`
      );
    }

    this.stock.set(productId, available - quantity);
  }
}

class FakePaymentGateway {
  constructor({ decline = false } = {}) {
    this.decline = decline;
    this.transactions = [];
  }

  charge(amount) {
    if (this.decline) {
      throw new Error("Payment gateway declined the charge.");
    }

    const transactionId =
      `PAY-${String(this.transactions.length + 1).padStart(4, "0")}`;

    this.transactions.push({
      transactionId,
      amount,
    });

    return transactionId;
  }
}

class ConsoleNotificationGateway {
  async send(email, subject, body) {
    console.log(
      `[ASYNC NOTIFICATION] ${email} | ${subject} | ${body}`
    );
  }
}

class CheckoutApplication {
  constructor({
    inventory,
    payment,
    notifier,
    pricing,
  }) {
    if (!inventory || typeof inventory.reserve !== "function") {
      throw new TypeError("Inventory dependency is invalid.");
    }

    if (!payment || typeof payment.charge !== "function") {
      throw new TypeError("Payment dependency is invalid.");
    }

    if (!notifier || typeof notifier.send !== "function") {
      throw new TypeError("Notification dependency is invalid.");
    }

    if (!pricing || typeof pricing.calculate !== "function") {
      throw new TypeError("Pricing dependency is invalid.");
    }

    this.inventory = inventory;
    this.payment = payment;
    this.notifier = notifier;
    this.pricing = pricing;
  }

  async place(order) {
    const result = this.pricing.calculate(order);

    for (const line of order.lines) {
      this.inventory.reserve(line.product.id, line.quantity);
    }

    const transactionId = this.payment.charge(result.total);

    order.status = "PAID";

    await this.notifier.send(
      order.customerEmail,
      "Order paid",
      `Order ${order.id}; transaction=${transactionId}; total=${result.total.toFixed(2)}`
    );

    return {
      transactionId,
      pricing: result,
    };
  }
}

async function demonstrateDIP() {
  heading("DIP: Inject infrastructure into high-level policy");

  const product = new Product("SEC-1", "Security Token", 59);

  const order = new Order(
    "ORD-DIP",
    "dip@example.com",
    [new OrderLine(product, 2)]
  );

  const pricing = new CheckoutPricing(
    new CustomerTierPolicy("silver")
  );

  const application = new CheckoutApplication({
    inventory: new MemoryInventory({
      "SEC-1": 10,
    }),
    payment: new FakePaymentGateway(),
    notifier: new ConsoleNotificationGateway(),
    pricing,
  });

  const result = await application.place(order);

  console.log("Transaction:", result.transactionId);
  console.log("Pricing:", result.pricing);
  console.log("Order status:", order.status);
}

// ===========================================================================
// Event-driven SOLID composition
// ===========================================================================

/*
 * Event-driven systems make dependency boundaries particularly visible.
 * The domain event publisher owns event delivery, while subscribers own the
 * response to a particular event.
 */

class EventBus {
  constructor() {
    this.handlers = new Map();
  }

  on(eventName, handler) {
    if (typeof handler !== "function") {
      throw new TypeError("Event handler must be a function.");
    }

    const handlers = this.handlers.get(eventName) ?? [];

    handlers.push(handler);
    this.handlers.set(eventName, handlers);
  }

  async emit(eventName, payload) {
    const handlers = this.handlers.get(eventName) ?? [];

    for (const handler of handlers) {
      await handler(payload);
    }
  }
}

class OrderAuditSubscriber {
  constructor(auditWriter) {
    if (
      !auditWriter ||
      typeof auditWriter.recordEvent !== "function"
    ) {
      throw new TypeError("Audit writer is invalid.");
    }

    this.auditWriter = auditWriter;
  }

  async handle(event) {
    this.auditWriter.recordEvent(
      event.orderId,
      `EVENT:${event.type}`
    );
  }
}

async function demonstrateEventDrivenComposition() {
  heading("SOLID with an event-driven boundary");

  const store = new OrderStore();
  const bus = new EventBus();

  const auditSubscriber = new OrderAuditSubscriber(store);

  bus.on(
    "order.paid",
    event => auditSubscriber.handle(event)
  );

  await bus.emit("order.paid", {
    type: "ORDER_PAID",
    orderId: "ORD-EVENT",
  });

  console.log("Event audit:", store.events);
}

// ===========================================================================
// Automated verification
// ===========================================================================

async function runTests() {
  heading("Automated verification");

  const product = new Product("TEST", "Test Product", 100);

  const order = new Order(
    "TEST-ORDER",
    "test@example.com",
    [new OrderLine(product, 2)]
  );

  const calculator = new PriceCalculator();

  assert.equal(
    calculator.calculate(order, 0.1).total,
    220
  );

  const goldPricing = new CheckoutPricing(
    new CustomerTierPolicy("gold")
  );

  assert.equal(
    goldPricing.calculate(order).discount,
    20
  );

  const card = new CardPayment();
  const transaction = chargePayment(card, 50);

  assert.match(transaction, /^CARD-/);

  refundPayment(card, transaction, 10);

  assert.equal(
    card.transactions.get(transaction),
    40
  );

  const store = new OrderStore();

  store.saveOrder({
    orderId: "READ-1",
    customerEmail: "read@example.com",
    total: 75,
  });

  const reporting = new ReportingClient(store);

  assert.match(
    reporting.render("READ-1"),
    /total=75\.00/
  );

  const inventory = new MemoryInventory({
    TEST: 3,
  });

  const payment = new FakePaymentGateway();

  const checkout = new CheckoutApplication({
    inventory,
    payment,
    notifier: new ConsoleNotificationGateway(),
    pricing: new CheckoutPricing(new NoDiscountPolicy()),
  });

  const result = await checkout.place(
    new Order(
      "DIP-TEST",
      "dip-test@example.com",
      [new OrderLine(product, 2)]
    )
  );

  assert.equal(result.transactionId, "PAY-0001");
  assert.equal(inventory.stock.get("TEST"), 1);

  assert.throws(
    () => new OrderLine(product, 0),
    /Quantity must be a positive integer/
  );

  assert.throws(
    () => new CustomerTierPolicy("unknown"),
    /Unsupported customer tier/
  );

  assert.throws(
    () => new GiftCardPayment(-1),
    /non-negative/
  );

  console.log("All SOLID design tests passed.");
}

// ===========================================================================
// Main
// ===========================================================================

async function main() {
  heading("SOLID PRINCIPLES: PRACTICAL JAVASCRIPT CASE STUDY");

  demonstrateSRP();
  demonstrateOCP();
  demonstrateLSP();
  demonstrateISP();

  await demonstrateDIP();
  await demonstrateEventDrivenComposition();
  await runTests();
}

main().catch(error => {
  console.error("Application failed:", error.message);
  process.exitCode = 1;
});
