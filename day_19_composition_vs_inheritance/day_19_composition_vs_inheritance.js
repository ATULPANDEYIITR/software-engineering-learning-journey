/*
 * Composition vs Inheritance
 * ==========================
 *
 * A self-contained JavaScript study file progressing from basic object
 * relationships to dependency injection, strategy composition, inheritance,
 * coupling, maintainability, asynchronous composition, and testing.
 *
 * Compatible with modern Node.js.
 */

// ============================================================================
// 1. BASIC OBJECTS
// ============================================================================

class Customer {
    constructor(name, email) {
        this.name = name;
        this.email = email;
    }
}

class OrderItem {
    constructor(product, quantity, unitPrice) {
        if (quantity <= 0) {
            throw new Error("Quantity must be positive.");
        }
        if (unitPrice < 0) {
            throw new Error("Unit price cannot be negative.");
        }

        this.product = product;
        this.quantity = quantity;
        this.unitPrice = unitPrice;
    }

    get total() {
        return this.quantity * this.unitPrice;
    }
}

class Order {
    // An Order HAS OrderItems, which demonstrates composition.
    constructor(customer) {
        this.customer = customer;
        this.items = [];
    }

    addItem(item) {
        this.items.push(item);
    }

    getTotal() {
        return this.items.reduce((sum, item) => sum + item.total, 0);
    }
}

// ============================================================================
// 2. INHERITANCE
// ============================================================================

class Employee {
    constructor(name, employeeId) {
        this.name = name;
        this.employeeId = employeeId;
    }

    describe() {
        return `${this.name} (${this.employeeId})`;
    }
}

class Developer extends Employee {
    writeCode() {
        return `${this.name} is writing software.`;
    }
}

class Manager extends Employee {
    manage() {
        return `${this.name} is managing a team.`;
    }
}

// ============================================================================
// 3. IS-A AND HAS-A
// ============================================================================

class Vehicle {
    move() {
        return "Vehicle is moving.";
    }
}

class Car extends Vehicle {
    move() {
        return "Car is driving.";
    }
}

class Engine {
    constructor(horsepower) {
        this.horsepower = horsepower;
    }

    start() {
        return `Engine with ${this.horsepower} HP started.`;
    }
}

class ComposedCar {
    // The car HAS an engine instead of inheriting from Engine.
    constructor(engine) {
        this.engine = engine;
    }

    start() {
        return this.engine.start();
    }

    move() {
        return "Composed car is driving.";
    }
}

// ============================================================================
// 4. INHERITANCE-BASED TEMPLATE REUSE
// ============================================================================

class Report {
    header() {
        return "REPORT";
    }

    body() {
        return "Default report body.";
    }

    footer() {
        return "END";
    }

    render() {
        return [this.header(), this.body(), this.footer()].join("\n");
    }
}

class SalesReport extends Report {
    body() {
        return "Sales report data.";
    }
}

class FinancialReport extends Report {
    body() {
        return "Financial report data.";
    }
}

// ============================================================================
// 5. COMPOSITION-BASED FORMATTING
// ============================================================================

class PlainTextFormatter {
    format(title, body) {
        return `${title}\n${body}`;
    }
}

class MarkdownFormatter {
    format(title, body) {
        return `# ${title}\n\n${body}`;
    }
}

class HtmlFormatter {
    format(title, body) {
        return `<h1>${escapeHtml(title)}</h1><p>${escapeHtml(body)}</p>`;
    }
}

class ComposedReport {
    constructor(formatter) {
        this.formatter = formatter;
    }

    render(title, body) {
        return this.formatter.format(title, body);
    }
}

function escapeHtml(value) {
    return value
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ============================================================================
// 6. TIGHT COUPLING VERSUS DEPENDENCY INJECTION
// ============================================================================

class StripeLikeGateway {
    charge(amount) {
        return `Stripe-like gateway charged $${amount.toFixed(2)}`;
    }
}

class TightlyCoupledInvoice {
    constructor(amount) {
        this.amount = amount;
    }

    pay() {
        // Concrete dependency is constructed internally.
        const gateway = new StripeLikeGateway();
        return gateway.charge(this.amount);
    }
}

class MockPaymentGateway {
    charge(amount) {
        return `Mock gateway charged $${amount.toFixed(2)}`;
    }
}

class Invoice {
    constructor(amount, gateway) {
        if (amount < 0) {
            throw new Error("Invoice amount cannot be negative.");
        }

        this.amount = amount;
        this.gateway = gateway;
    }

    pay() {
        return this.gateway.charge(this.amount);
    }
}

// ============================================================================
// 7. STRATEGY PATTERN THROUGH COMPOSITION
// ============================================================================

class RegularPricing {
    calculate(subtotal) {
        return subtotal;
    }
}

class TenPercentDiscount {
    calculate(subtotal) {
        return subtotal * 0.90;
    }
}

class TwentyPercentDiscount {
    calculate(subtotal) {
        return subtotal * 0.80;
    }
}

class ShoppingCart {
    constructor(pricingStrategy) {
        this.pricingStrategy = pricingStrategy;
        this.items = [];
    }

    add(item) {
        this.items.push(item);
    }

    subtotal() {
        return this.items.reduce((sum, item) => sum + item.total, 0);
    }

    total() {
        return this.pricingStrategy.calculate(this.subtotal());
    }

    changePricingStrategy(strategy) {
        this.pricingStrategy = strategy;
    }
}

// ============================================================================
// 8. BEHAVIOR COMPOSITION
// ============================================================================

class EmailChannel {
    async send(recipient, message) {
        return `EMAIL -> ${recipient}: ${message}`;
    }
}

class SmsChannel {
    async send(recipient, message) {
        return `SMS -> ${recipient}: ${message}`;
    }
}

class PushChannel {
    async send(recipient, message) {
        return `PUSH -> ${recipient}: ${message}`;
    }
}

class NotificationService {
    constructor(channel) {
        this.channel = channel;
    }

    async notify(recipient, message) {
        if (!recipient.trim()) {
            throw new Error("Recipient cannot be empty.");
        }

        return this.channel.send(recipient, message);
    }
}

// ============================================================================
// 9. ASYNCHRONOUS COMPOSITION
// ============================================================================

class InventoryService {
    constructor() {
        this.stock = new Map();
    }

    async add(product, quantity) {
        if (quantity <= 0) {
            throw new Error("Quantity must be positive.");
        }

        const current = this.stock.get(product) ?? 0;
        this.stock.set(product, current + quantity);
    }

    async reserve(product, quantity) {
        const available = this.stock.get(product) ?? 0;

        if (quantity <= 0) {
            throw new Error("Quantity must be positive.");
        }

        if (available < quantity) {
            throw new Error(`Insufficient stock for ${product}.`);
        }

        this.stock.set(product, available - quantity);
    }

    available(product) {
        return this.stock.get(product) ?? 0;
    }
}

class OrderProcessor {
    constructor(inventory, paymentGateway, logger) {
        // Three independently replaceable dependencies are composed here.
        this.inventory = inventory;
        this.paymentGateway = paymentGateway;
        this.logger = logger;
    }

    async process(product, quantity, price) {
        if (price < 0) {
            throw new Error("Price cannot be negative.");
        }

        await this.inventory.reserve(product, quantity);

        const result = await this.paymentGateway.charge(price * quantity);
        this.logger.log(result);

        return result;
    }
}

class AsyncPaymentGateway {
    async charge(amount) {
        await new Promise(resolve => setTimeout(resolve, 5));
        return `Payment authorized for $${amount.toFixed(2)}`;
    }
}

class ConsoleLogger {
    log(message) {
        console.log(`[LOG] ${message}`);
    }
}

// ============================================================================
// 10. BAD INHERITANCE MODEL
// ============================================================================

class Bird {
    move() {
        return "Bird moves.";
    }
}

class FlyingBird extends Bird {
    fly() {
        return "Flying.";
    }
}

class Penguin extends FlyingBird {
    fly() {
        throw new Error("Penguins cannot fly.");
    }
}

// ============================================================================
// 11. COMPOSITION FIX
// ============================================================================

class CanFly {
    fly() {
        return "Flying through the air.";
    }
}

class CannotFly {
    fly() {
        return "This animal cannot fly.";
    }
}

class BirdWithFlightBehavior {
    constructor(name, flightBehavior) {
        this.name = name;
        this.flightBehavior = flightBehavior;
    }

    move() {
        return `${this.name} moves.`;
    }

    fly() {
        return this.flightBehavior.fly();
    }
}

// ============================================================================
// 12. FUNCTION COMPOSITION
// ============================================================================

const trim = value => value.trim();
const normalizeCase = value => value.toLowerCase();
const replaceSpaces = value => value.replaceAll(" ", "_");

function compose(...functions) {
    return value => functions.reduce((result, fn) => fn(result), value);
}

// ============================================================================
// 13. MODULE-LIKE PLUGINS
// ============================================================================

class JsonSerializer {
    serialize(value) {
        return JSON.stringify(value);
    }
}

class TextSerializer {
    serialize(value) {
        return String(value);
    }
}

class ExportService {
    constructor(serializer) {
        this.serializer = serializer;
    }

    export(value) {
        return this.serializer.serialize(value);
    }
}

// ============================================================================
// 14. IMMUTABLE VALUE OBJECT
// ============================================================================

class Money {
    constructor(amount, currency = "USD") {
        if (!Number.isFinite(amount)) {
            throw new Error("Money amount must be finite.");
        }

        if (!/^[A-Z]{3}$/.test(currency)) {
            throw new Error("Currency must be a three-letter uppercase code.");
        }

        Object.defineProperty(this, "amount", {
            value: amount,
            writable: false,
            enumerable: true
        });

        Object.defineProperty(this, "currency", {
            value: currency,
            writable: false,
            enumerable: true
        });

        Object.freeze(this);
    }

    add(other) {
        if (this.currency !== other.currency) {
            throw new Error("Currencies must match.");
        }

        return new Money(this.amount + other.amount, this.currency);
    }
}

// ============================================================================
// 15. TEST DOUBLES
// ============================================================================

class RecordingGateway {
    constructor() {
        this.charges = [];
    }

    async charge(amount) {
        this.charges.push(amount);
        return `Recorded $${amount.toFixed(2)}`;
    }
}

class SilentLogger {
    constructor() {
        this.messages = [];
    }

    log(message) {
        this.messages.push(message);
    }
}

// ============================================================================
// 16. MAINTAINABILITY: DEPENDENCY GRAPH
// ============================================================================

class DependencyGraph {
    constructor() {
        this.dependencies = new Map();
    }

    addComponent(name, dependencies = []) {
        this.dependencies.set(name, new Set(dependencies));
    }

    getDependencies(name) {
        return [...(this.dependencies.get(name) ?? [])];
    }

    getAfferentCoupling(component) {
        let count = 0;

        for (const dependencies of this.dependencies.values()) {
            if (dependencies.has(component)) {
                count++;
            }
        }

        return count;
    }
}

// ============================================================================
// 17. ADVANCED CHECKOUT SYSTEM
// ============================================================================

class NoTax {
    calculate(amount) {
        return 0;
    }
}

class FlatTax {
    constructor(rate) {
        if (rate < 0 || rate > 1) {
            throw new Error("Tax rate must be between 0 and 1.");
        }

        this.rate = rate;
    }

    calculate(amount) {
        return amount * this.rate;
    }
}

class FreeShipping {
    calculate() {
        return 0;
    }
}

class FlatShipping {
    constructor(fee) {
        if (fee < 0) {
            throw new Error("Shipping fee cannot be negative.");
        }

        this.fee = fee;
    }

    calculate() {
        return this.fee;
    }
}

class Checkout {
    constructor(pricing, taxPolicy, shippingPolicy) {
        this.pricing = pricing;
        this.taxPolicy = taxPolicy;
        this.shippingPolicy = shippingPolicy;
    }

    calculateTotal(subtotal) {
        if (subtotal < 0) {
            throw new Error("Subtotal cannot be negative.");
        }

        const discounted = this.pricing.calculate(subtotal);
        const tax = this.taxPolicy.calculate(discounted);
        const shipping = this.shippingPolicy.calculate(discounted);

        return discounted + tax + shipping;
    }
}

// ============================================================================
// 18. PERFORMANCE COMPARISON
// ============================================================================

function benchmark(label, operation, iterations = 100_000) {
    const start = process.hrtime.bigint();

    for (let i = 0; i < iterations; i++) {
        operation();
    }

    const elapsedNanoseconds = Number(process.hrtime.bigint() - start);
    const milliseconds = elapsedNanoseconds / 1_000_000;

    console.log(
        `${label}: ${milliseconds.toFixed(3)} ms for ${iterations} iterations`
    );
}

// ============================================================================
// 19. DEMONSTRATION
// ============================================================================

async function main() {
    console.log("=".repeat(72));
    console.log("COMPOSITION VS INHERITANCE");
    console.log("=".repeat(72));

    console.log("\n1. Inheritance");
    const developer = new Developer("Asha", "D001");
    const manager = new Manager("Ravi", "M001");
    console.log(developer.describe());
    console.log(developer.writeCode());
    console.log(manager.describe());
    console.log(manager.manage());

    console.log("\n2. Composition");
    const customer = new Customer("Mira", "mira@example.com");
    const order = new Order(customer);
    order.addItem(new OrderItem("Laptop", 2, 800));
    order.addItem(new OrderItem("Mouse", 1, 25));
    console.log(`Order total: $${order.getTotal().toFixed(2)}`);

    console.log("\n3. IS-A versus HAS-A");
    console.log(new Car().move());
    const composedCar = new ComposedCar(new Engine(150));
    console.log(composedCar.start());
    console.log(composedCar.move());

    console.log("\n4. Inheritance-based report");
    console.log(new SalesReport().render());

    console.log("\n5. Composition-based formatters");
    const formatters = [
        new PlainTextFormatter(),
        new MarkdownFormatter(),
        new HtmlFormatter()
    ];

    for (const formatter of formatters) {
        console.log(new ComposedReport(formatter).render(
            "Sales",
            "Revenue increased."
        ));
    }

    console.log("\n6. Coupling");
    console.log(new TightlyCoupledInvoice(100).pay());
    console.log(new Invoice(100, new MockPaymentGateway()).pay());

    console.log("\n7. Runtime strategy replacement");
    const cart = new ShoppingCart(new RegularPricing());
    cart.add(new OrderItem("Book", 2, 30));
    console.log(`Regular: $${cart.total().toFixed(2)}`);
    cart.changePricingStrategy(new TenPercentDiscount());
    console.log(`Discounted: $${cart.total().toFixed(2)}`);

    console.log("\n8. Async notification");
    const channels = [
        new EmailChannel(),
        new SmsChannel(),
        new PushChannel()
    ];

    for (const channel of channels) {
        console.log(
            await new NotificationService(channel).notify(
                "user-42",
                "Order shipped."
            )
        );
    }

    console.log("\n9. Composed order processor");
    const inventory = new InventoryService();
    await inventory.add("SSD", 10);

    const processor = new OrderProcessor(
        inventory,
        new AsyncPaymentGateway(),
        new ConsoleLogger()
    );

    await processor.process("SSD", 2, 120);
    console.log(`Remaining SSD stock: ${inventory.available("SSD")}`);

    console.log("\n10. Poor inheritance model");
    try {
        new Penguin().fly();
    } catch (error) {
        console.log(`Failure demonstrates broken substitution: ${error.message}`);
    }

    console.log("\n11. Composed flight behavior");
    const birds = [
        new BirdWithFlightBehavior("Eagle", new CanFly()),
        new BirdWithFlightBehavior("Penguin", new CannotFly())
    ];

    for (const bird of birds) {
        console.log(`${bird.name}: ${bird.fly()}`);
    }

    console.log("\n12. Function composition");
    const normalizeIdentifier = compose(
        trim,
        normalizeCase,
        replaceSpaces
    );
    console.log(normalizeIdentifier("  Customer Order  "));

    console.log("\n13. Serializer composition");
    const data = { product: "SSD", quantity: 2 };
    console.log(new ExportService(new JsonSerializer()).export(data));
    console.log(new ExportService(new TextSerializer()).export(data));

    console.log("\n14. Immutable value object");
    const money = new Money(10).add(new Money(15));
    console.log(money);

    console.log("\n15. Test doubles");
    const recordingGateway = new RecordingGateway();
    const silentLogger = new SilentLogger();
    const testInventory = new InventoryService();

    await testInventory.add("Item", 5);

    const testProcessor = new OrderProcessor(
        testInventory,
        recordingGateway,
        silentLogger
    );

    await testProcessor.process("Item", 2, 50);

    console.log("Recorded charges:", recordingGateway.charges);
    console.log("Recorded logs:", silentLogger.messages);

    console.log("\n16. Dependency graph");
    const graph = new DependencyGraph();
    graph.addComponent("OrderProcessor", [
        "InventoryService",
        "PaymentGateway",
        "Logger"
    ]);
    graph.addComponent("Checkout", [
        "PricingStrategy",
        "TaxPolicy",
        "ShippingPolicy"
    ]);
    graph.addComponent("AdminPanel", ["OrderProcessor"]);

    console.log(
        "OrderProcessor dependencies:",
        graph.getDependencies("OrderProcessor")
    );
    console.log(
        "OrderProcessor afferent coupling:",
        graph.getAfferentCoupling("OrderProcessor")
    );

    console.log("\n17. Advanced checkout");
    const checkout = new Checkout(
        new TenPercentDiscount(),
        new FlatTax(0.18),
        new FlatShipping(50)
    );

    console.log(
        `Checkout total: $${checkout.calculateTotal(1000).toFixed(2)}`
    );

    console.log("\n18. Error handling");
    try {
        new OrderItem("Invalid", -1, 10);
    } catch (error) {
        console.log(error.message);
    }

    try {
        new Money(Number.NaN);
    } catch (error) {
        console.log(error.message);
    }

    console.log("\n19. Performance");
    benchmark(
        "Direct function invocation",
        () => Math.sqrt(144),
        100_000
    );

    const strategy = new RegularPricing();
    benchmark(
        "Composed strategy invocation",
        () => strategy.calculate(144),
        100_000
    );

    console.log("\n20. Design principle");
    console.log(
        "Composition is especially useful when behavior must be replaced, "
        + "combined, configured, or tested independently."
    );
    console.log(
        "Inheritance is useful when a stable subtype relationship exists "
        + "and subclasses remain behaviorally substitutable for the base type."
    );
}

main().catch(error => {
    console.error("Application failure:", error);
    process.exitCode = 1;
});
