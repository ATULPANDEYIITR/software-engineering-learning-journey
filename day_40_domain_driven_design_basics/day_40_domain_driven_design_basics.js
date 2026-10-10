"use strict";

/*
 * Domain-Driven Design in JavaScript
 *
 * This implementation models a fulfillment domain where:
 * - ProductCode and Money are value objects.
 * - OrderLine is an entity inside an Order aggregate.
 * - Order is the aggregate root.
 * - Domain events expose business facts without coupling the domain model
 *   directly to notification or persistence infrastructure.
 *
 * The JavaScript-specific perspective is event-driven: state changes emit
 * domain events, and an application-level event dispatcher reacts to them.
 */

const OrderStatus = Object.freeze({
  DRAFT: "DRAFT",
  CONFIRMED: "CONFIRMED",
  CANCELLED: "CANCELLED"
});

class DomainError extends Error {
  constructor(message) {
    super(message);
    this.name = "DomainError";
  }
}

class ProductCode {
  constructor(value) {
    const normalized = String(value).trim().toUpperCase();

    if (!normalized) {
      throw new DomainError("Product code cannot be empty.");
    }

    if (!/^[A-Z0-9-]{2,40}$/.test(normalized)) {
      throw new DomainError("Product code contains invalid characters.");
    }

    Object.defineProperty(this, "value", {
      value: normalized,
      enumerable: true,
      writable: false
    });

    Object.freeze(this);
  }

  equals(other) {
    return other instanceof ProductCode && this.value === other.value;
  }
}

class Money {
  constructor(amount, currency = "INR") {
    if (!Number.isFinite(amount) || amount < 0) {
      throw new DomainError("Money amount must be a finite non-negative number.");
    }

    const normalizedCurrency = String(currency).trim().toUpperCase();

    if (!/^[A-Z]{3}$/.test(normalizedCurrency)) {
      throw new DomainError("Currency must be a three-letter code.");
    }

    // A value object is immutable. Rounding is performed at construction
    // so arithmetic does not accidentally create inconsistent display values.
    this.amount = Math.round(amount * 100) / 100;
    this.currency = normalizedCurrency;

    Object.freeze(this);
  }

  add(other) {
    this.ensureSameCurrency(other);
    return new Money(this.amount + other.amount, this.currency);
  }

  multiply(quantity) {
    if (!Number.isInteger(quantity) || quantity < 0) {
      throw new DomainError("Quantity must be a non-negative integer.");
    }

    return new Money(this.amount * quantity, this.currency);
  }

  ensureSameCurrency(other) {
    if (!(other instanceof Money)) {
      throw new DomainError("Money operation requires another Money value.");
    }

    if (this.currency !== other.currency) {
      throw new DomainError("Currencies cannot be combined.");
    }
  }

  toString() {
    return `${this.currency} ${this.amount.toFixed(2)}`;
  }

  equals(other) {
    return (
      other instanceof Money &&
      this.amount === other.amount &&
      this.currency === other.currency
    );
  }
}

class ShippingAddress {
  constructor({ street, city, postalCode, country = "India" }) {
    const values = { street, city, postalCode, country };

    for (const [name, value] of Object.entries(values)) {
      if (!String(value ?? "").trim()) {
        throw new DomainError(`${name} cannot be empty.`);
      }
    }

    this.street = String(street).trim();
    this.city = String(city).trim();
    this.postalCode = String(postalCode).trim();
    this.country = String(country).trim();

    Object.freeze(this);
  }

  equals(other) {
    return (
      other instanceof ShippingAddress &&
      this.street === other.street &&
      this.city === other.city &&
      this.postalCode === other.postalCode &&
      this.country === other.country
    );
  }
}

/*
 * OrderLine is an entity because its identity remains meaningful while
 * quantity changes. The aggregate root controls access to it.
 */
class OrderLine {
  constructor({ lineId, productCode, quantity, unitPrice }) {
    if (!lineId) {
      throw new DomainError("Order line identity is required.");
    }

    if (!Number.isInteger(quantity) || quantity <= 0) {
      throw new DomainError("Order line quantity must be positive.");
    }

    this.lineId = lineId;
    this.productCode = productCode;
    this.quantity = quantity;
    this.unitPrice = unitPrice;
  }

  increaseQuantity(amount) {
    if (!Number.isInteger(amount) || amount <= 0) {
      throw new DomainError("Quantity increase must be positive.");
    }

    this.quantity += amount;
  }

  subtotal() {
    return this.unitPrice.multiply(this.quantity);
  }

  snapshot() {
    return Object.freeze({
      lineId: this.lineId,
      productCode: this.productCode.value,
      quantity: this.quantity,
      unitPrice: this.unitPrice.toString(),
      subtotal: this.subtotal().toString()
    });
  }
}

/*
 * Order is the aggregate root. It owns OrderLine entities and enforces
 * invariants that must remain true for the entire order.
 */
class Order {
  constructor({ orderId, customerId, shippingAddress }) {
    this.orderId = orderId;
    this.customerId = customerId;
    this.shippingAddress = shippingAddress;
    this.status = OrderStatus.DRAFT;
    this.lines = new Map();
  }

  addLine(productCode, quantity, unitPrice) {
    this.ensureDraft();

    for (const line of this.lines.values()) {
      if (line.productCode.equals(productCode)) {
        line.increaseQuantity(quantity);
        return line.lineId;
      }
    }

    const lineId = crypto.randomUUID();

    this.lines.set(
      lineId,
      new OrderLine({
        lineId,
        productCode,
        quantity,
        unitPrice
      })
    );

    return lineId;
  }

  removeLine(lineId) {
    this.ensureDraft();

    if (!this.lines.delete(lineId)) {
      throw new DomainError("Order line does not exist.");
    }
  }

  total() {
    return [...this.lines.values()].reduce(
      (sum, line) => sum.add(line.subtotal()),
      new Money(0, "INR")
    );
  }

  confirm() {
    this.ensureDraft();

    if (this.lines.size === 0) {
      throw new DomainError("An empty order cannot be confirmed.");
    }

    const total = this.total();

    if (total.amount <= 0) {
      throw new DomainError("Confirmed order must have a positive total.");
    }

    this.status = OrderStatus.CONFIRMED;

    return {
      type: "OrderConfirmed",
      aggregateId: this.orderId,
      customerId: this.customerId,
      total: total.toString(),
      occurredAt: new Date().toISOString()
    };
  }

  cancel(reason) {
    if (this.status === OrderStatus.CANCELLED) {
      throw new DomainError("Order is already cancelled.");
    }

    if (!String(reason).trim()) {
      throw new DomainError("Cancellation reason is required.");
    }

    this.status = OrderStatus.CANCELLED;

    return {
      type: "OrderCancelled",
      aggregateId: this.orderId,
      reason: String(reason).trim(),
      occurredAt: new Date().toISOString()
    };
  }

  viewLines() {
    return [...this.lines.values()].map((line) => line.snapshot());
  }

  ensureDraft() {
    if (this.status !== OrderStatus.DRAFT) {
      throw new DomainError(
        `Order modification is not permitted in ${this.status} state.`
      );
    }
  }
}

/*
 * Node.js EventEmitter provides a natural event-driven application boundary.
 * The aggregate emits plain domain-event data, while handlers decide what
 * infrastructure action should follow.
 */
const { EventEmitter } = require("node:events");

class DomainEventBus extends EventEmitter {
  publish(event) {
    this.emit(event.type, event);
  }
}

class OrderRepository {
  constructor() {
    this.orders = new Map();
  }

  save(order) {
    this.orders.set(order.orderId, order);
  }

  get(orderId) {
    const order = this.orders.get(orderId);

    if (!order) {
      throw new DomainError(`Order ${orderId} was not found.`);
    }

    return order;
  }
}

class FulfillmentProjection {
  constructor(eventBus) {
    this.confirmedOrders = new Map();

    eventBus.on("OrderConfirmed", (event) => {
      this.confirmedOrders.set(event.aggregateId, {
        customerId: event.customerId,
        total: event.total,
        confirmedAt: event.occurredAt
      });
    });

    eventBus.on("OrderCancelled", (event) => {
      this.confirmedOrders.delete(event.aggregateId);
    });
  }

  get(orderId) {
    return this.confirmedOrders.get(orderId) ?? null;
  }
}

class OrderApplicationService {
  constructor(repository, eventBus) {
    this.repository = repository;
    this.eventBus = eventBus;
  }

  confirm(orderId) {
    const order = this.repository.get(orderId);
    const event = order.confirm();

    this.repository.save(order);
    this.eventBus.publish(event);

    return event;
  }
}

function runScenario() {
  console.log("=== Domain-Driven Design: Event-Driven Order Domain ===");

  const eventBus = new DomainEventBus();
  const repository = new OrderRepository();
  const projection = new FulfillmentProjection(eventBus);
  const applicationService = new OrderApplicationService(repository, eventBus);

  const address = new ShippingAddress({
    street: "14 Gomti Nagar",
    city: "Lucknow",
    postalCode: "226010"
  });

  const order = new Order({
    orderId: crypto.randomUUID(),
    customerId: "CUS-1001",
    shippingAddress: address
  });

  repository.save(order);

  order.addLine(
    new ProductCode("LAPTOP-14"),
    1,
    new Money(79999)
  );

  order.addLine(
    new ProductCode("DOCK-USB-C"),
    2,
    new Money(2499.5)
  );

  // Reusing the same value-object value identifies the same product concept,
  // so the aggregate combines quantities rather than creating a duplicate.
  order.addLine(
    new ProductCode("LAPTOP-14"),
    1,
    new Money(79999)
  );

  console.log("\nAggregate state:");
  console.table(order.viewLines());
  console.log("Total:", order.total().toString());

  const confirmationEvent = applicationService.confirm(order.orderId);

  console.log("\nPublished domain event:");
  console.log(confirmationEvent);

  console.log("\nRead-model projection:");
  console.log(projection.get(order.orderId));

  try {
    order.addLine(
      new ProductCode("MOUSE"),
      1,
      new Money(1200)
    );
  } catch (error) {
    console.log("\nProtected aggregate invariant:");
    console.log(error.message);
  }

  const cancelledEvent = order.cancel("Customer changed delivery requirements");
  eventBus.publish(cancelledEvent);

  console.log("\nCancellation event:");
  console.log(cancelledEvent);

  console.log("\nProjection after cancellation:");
  console.log(projection.get(order.orderId));

  const moneyA = new Money(2500);
  const moneyB = new Money(2500);

  console.log("\nValue-object equality:", moneyA.equals(moneyB));
  console.log(
    "Value-object instances are immutable:",
    Object.isFrozen(moneyA)
  );
}

runScenario();
