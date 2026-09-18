"use strict";

/*
 * Object-Oriented Programming Principles
 *
 * Topic:
 *   Encapsulation, inheritance, polymorphism, and abstraction.
 *
 * Runtime:
 *   Modern Node.js or a modern browser.
 *
 * This file complements the Python implementation by emphasizing
 * JavaScript-specific object behavior, prototypes, private fields,
 * getters/setters, classes, composition, asynchronous behavior,
 * symbols, iterators, and event-driven polymorphism.
 */

console.log("=".repeat(78));
console.log("OBJECT-ORIENTED PROGRAMMING IN JAVASCRIPT");
console.log("=".repeat(78));


// ============================================================================
// 1. OBJECTS AND CLASSES
// ============================================================================

console.log("\n1. OBJECTS AND CLASSES");

class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }

    introduce() {
        return `My name is ${this.name} and I am ${this.age} years old.`;
    }
}

const person = new Person("Atul", 30);

console.log(person.introduce());
console.log("Constructor:", person.constructor.name);
console.log("Own properties:", Object.keys(person));


// ============================================================================
// 2. ENCAPSULATION WITH PRIVATE FIELDS
// ============================================================================

console.log("\n2. ENCAPSULATION WITH PRIVATE FIELDS");

/*
 * JavaScript class private fields use #.
 *
 * Unlike a convention such as _balance, a #balance field cannot be accessed
 * directly from code outside the class body.
 */

class BankAccount {
    #balance;
    #transactionCount = 0;

    constructor(owner, openingBalance = 0) {
        if (!owner.trim()) {
            throw new Error("Owner name cannot be empty.");
        }

        if (!Number.isFinite(openingBalance) || openingBalance < 0) {
            throw new Error("Opening balance must be a non-negative number.");
        }

        this.owner = owner;
        this.#balance = openingBalance;
    }

    get balance() {
        return this.#balance;
    }

    get transactionCount() {
        return this.#transactionCount;
    }

    deposit(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Deposit must be positive.");
        }

        this.#balance += amount;
        this.#transactionCount += 1;
    }

    withdraw(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Withdrawal must be positive.");
        }

        if (amount > this.#balance) {
            throw new Error("Insufficient funds.");
        }

        this.#balance -= amount;
        this.#transactionCount += 1;
    }
}

const account = new BankAccount("Atul", 10000);
account.deposit(2500);
account.withdraw(1250);

console.log("Balance:", account.balance);
console.log("Transactions:", account.transactionCount);

try {
    account.withdraw(50000);
} catch (error) {
    console.log("Controlled error:", error.message);
}


// ============================================================================
// 3. GETTERS AND SETTERS
// ============================================================================

console.log("\n3. GETTERS AND SETTERS");

class Temperature {
    #celsius;

    constructor(celsius) {
        this.celsius = celsius;
    }

    get celsius() {
        return this.#celsius;
    }

    set celsius(value) {
        if (!Number.isFinite(value) || value < -273.15) {
            throw new Error("Temperature cannot be below absolute zero.");
        }

        this.#celsius = value;
    }

    get fahrenheit() {
        return this.celsius * 9 / 5 + 32;
    }

    set fahrenheit(value) {
        this.celsius = (value - 32) * 5 / 9;
    }
}

const temperature = new Temperature(25);

console.log("Celsius:", temperature.celsius);
console.log("Fahrenheit:", temperature.fahrenheit);

temperature.fahrenheit = 212;

console.log("After Fahrenheit assignment:", temperature.celsius);

try {
    temperature.celsius = -500;
} catch (error) {
    console.log("Validation error:", error.message);
}


// ============================================================================
// 4. INHERITANCE
// ============================================================================

console.log("\n4. INHERITANCE");

class Animal {
    constructor(name) {
        this.name = name;
    }

    eat() {
        return `${this.name} is eating.`;
    }

    speak() {
        return `${this.name} makes a sound.`;
    }
}

class Dog extends Animal {
    speak() {
        return `${this.name} says woof.`;
    }
}

class Cat extends Animal {
    speak() {
        return `${this.name} says meow.`;
    }
}

const dog = new Dog("Bruno");
const cat = new Cat("Luna");

console.log(dog.eat());
console.log(dog.speak());
console.log(cat.eat());
console.log(cat.speak());


// ============================================================================
// 5. SUPER
// ============================================================================

console.log("\n5. SUPER");

class Employee {
    constructor(name, employeeId) {
        this.name = name;
        this.employeeId = employeeId;
    }

    describe() {
        return `${this.name} (${this.employeeId})`;
    }
}

class Manager extends Employee {
    constructor(name, employeeId, teamSize) {
        super(name, employeeId);

        if (!Number.isInteger(teamSize) || teamSize < 0) {
            throw new Error("Team size must be a non-negative integer.");
        }

        this.teamSize = teamSize;
    }

    describe() {
        return `${super.describe()}, manages ${this.teamSize} people`;
    }
}

const manager = new Manager("Priya", "M-100", 12);
console.log(manager.describe());


// ============================================================================
// 6. POLYMORPHISM
// ============================================================================

console.log("\n6. POLYMORPHISM");

/*
 * JavaScript does not require a common base class for every polymorphic
 * operation. If objects provide the expected method, the function can use
 * that method.
 */

function makeAnimalSpeak(animal) {
    if (!animal || typeof animal.speak !== "function") {
        throw new TypeError("Object must provide speak().");
    }

    return animal.speak();
}

class Robot {
    speak() {
        return "Robot voice activated.";
    }
}

class Parrot {
    speak() {
        return "Parrot repeats the message.";
    }
}

for (const speaker of [dog, cat, new Robot(), new Parrot()]) {
    console.log(makeAnimalSpeak(speaker));
}


// ============================================================================
// 7. ABSTRACTION THROUGH CONTRACT VALIDATION
// ============================================================================

console.log("\n7. ABSTRACTION");

class PaymentProcessor {
    authorize(_amount) {
        throw new Error("authorize() must be implemented by a subclass.");
    }

    capture(_amount) {
        throw new Error("capture() must be implemented by a subclass.");
    }

    process(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new Error("Payment amount must be positive.");
        }

        if (!this.authorize(amount)) {
            return "Payment authorization failed.";
        }

        return this.capture(amount);
    }
}

class CardPayment extends PaymentProcessor {
    authorize(amount) {
        return amount <= 100000;
    }

    capture(amount) {
        return `Card payment captured: ${amount.toFixed(2)}`;
    }
}

class WalletPayment extends PaymentProcessor {
    authorize(amount) {
        return amount <= 50000;
    }

    capture(amount) {
        return `Wallet payment captured: ${amount.toFixed(2)}`;
    }
}

const processors = [
    new CardPayment(),
    new WalletPayment()
];

for (const processor of processors) {
    console.log(processor.process(2500));
}


// ============================================================================
// 8. COMPOSITION
// ============================================================================

console.log("\n8. COMPOSITION");

class Engine {
    start() {
        return "Engine started.";
    }

    stop() {
        return "Engine stopped.";
    }
}

class Car {
    constructor(engine) {
        if (!engine || typeof engine.start !== "function") {
            throw new TypeError("Car requires an engine capability.");
        }

        this.engine = engine;
    }

    start() {
        return this.engine.start();
    }
}

const car = new Car(new Engine());
console.log(car.start());


// ============================================================================
// 9. DEPENDENCY INJECTION
// ============================================================================

console.log("\n9. DEPENDENCY INJECTION");

class AuditLogger {
    record(message) {
        return `AUDIT: ${message}`;
    }
}

class OrderService {
    constructor(logger) {
        if (!logger || typeof logger.record !== "function") {
            throw new TypeError("A logger with record() is required.");
        }

        this.logger = logger;
    }

    createOrder(orderId) {
        return this.logger.record(`Order ${orderId} created.`);
    }
}

const orderService = new OrderService(new AuditLogger());
console.log(orderService.createOrder("ORD-001"));


// ============================================================================
// 10. OBJECT FACTORY
// ============================================================================

console.log("\n10. FACTORY");

class Report {
    render() {
        throw new Error("render() must be implemented.");
    }
}

class HtmlReport extends Report {
    render() {
        return "<h1>Sales Report</h1>";
    }
}

class TextReport extends Report {
    render() {
        return "SALES REPORT";
    }
}

function createReport(format) {
    switch (format.toLowerCase()) {
        case "html":
            return new HtmlReport();
        case "text":
            return new TextReport();
        default:
            throw new Error(`Unsupported format: ${format}`);
    }
}

console.log(createReport("html").render());
console.log(createReport("text").render());


// ============================================================================
// 11. SYMBOL-BASED CAPABILITY
// ============================================================================

console.log("\n11. SYMBOL-BASED CAPABILITY");

const exportSymbol = Symbol("export");

class CsvReport {
    [exportSymbol]() {
        return "id,name\n1,Atul\n2,Priya";
    }
}

class JsonReport {
    [exportSymbol]() {
        return '[{"id":1,"name":"Atul"},{"id":2,"name":"Priya"}]';
    }
}

function exportReport(report) {
    if (!report || typeof report[exportSymbol] !== "function") {
        throw new TypeError("Report does not support the export capability.");
    }

    return report[exportSymbol]();
}

console.log(exportReport(new CsvReport()));
console.log(exportReport(new JsonReport()));


// ============================================================================
// 12. ITERATOR PROTOCOL
// ============================================================================

console.log("\n12. ITERATOR PROTOCOL");

class Countdown {
    constructor(start) {
        this.start = start;
    }

    *[Symbol.iterator]() {
        for (let current = this.start; current > 0; current -= 1) {
            yield current;
        }
    }
}

console.log([...new Countdown(5)]);


// ============================================================================
// 13. STATIC MEMBERS
// ============================================================================

console.log("\n13. STATIC MEMBERS");

class IdGenerator {
    static #nextId = 1;

    static next() {
        return this.#nextId++;
    }
}

console.log(IdGenerator.next());
console.log(IdGenerator.next());
console.log(IdGenerator.next());


// ============================================================================
// 14. OBJECT FREEZING
// ============================================================================

console.log("\n14. OBJECT FREEZING");

const configuration = Object.freeze({
    environment: "production",
    retryLimit: 3
});

console.log(configuration);

try {
    configuration.retryLimit = 10;
} catch (error) {
    console.log("Frozen object error:", error.message);
}

console.log("Retry limit remains:", configuration.retryLimit);


// ============================================================================
// 15. VALUE OBJECT WITH EQUALITY
// ============================================================================

console.log("\n15. VALUE OBJECT");

class Money {
    constructor(amount, currency = "INR") {
        if (!Number.isFinite(amount)) {
            throw new Error("Amount must be finite.");
        }

        if (!/^[A-Za-z]{3}$/.test(currency)) {
            throw new Error("Currency must contain three letters.");
        }

        this.amount = amount;
        this.currency = currency.toUpperCase();
        Object.freeze(this);
    }

    add(other) {
        if (!(other instanceof Money)) {
            throw new TypeError("Can only add Money objects.");
        }

        if (this.currency !== other.currency) {
            throw new Error("Currencies must match.");
        }

        return new Money(this.amount + other.amount, this.currency);
    }

    equals(other) {
        return (
            other instanceof Money &&
            this.currency === other.currency &&
            this.amount === other.amount
        );
    }

    toString() {
        return `${this.currency} ${this.amount.toFixed(2)}`;
    }
}

const moneyA = new Money(1000);
const moneyB = new Money(250);

console.log("Addition:", moneyA.add(moneyB).toString());
console.log("Equality:", new Money(1250).equals(moneyA.add(moneyB)));


// ============================================================================
// 16. ENCAPSULATED INVENTORY
// ============================================================================

console.log("\n16. ENCAPSULATED INVENTORY");

class InventoryItem {
    #quantity;

    constructor(sku, quantity = 0) {
        if (!sku.trim()) {
            throw new Error("SKU is required.");
        }

        if (!Number.isInteger(quantity) || quantity < 0) {
            throw new Error("Quantity must be a non-negative integer.");
        }

        this.sku = sku;
        this.#quantity = quantity;
    }

    get quantity() {
        return this.#quantity;
    }

    restock(quantity) {
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new Error("Restock quantity must be positive.");
        }

        this.#quantity += quantity;
    }

    reserve(quantity) {
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new Error("Reservation quantity must be positive.");
        }

        if (quantity > this.#quantity) {
            throw new Error("Insufficient inventory.");
        }

        this.#quantity -= quantity;
    }
}

const inventory = new InventoryItem("LAPTOP-001", 10);

inventory.reserve(3);
inventory.restock(5);

console.log("SKU:", inventory.sku);
console.log("Quantity:", inventory.quantity);


// ============================================================================
// 17. ASYNCHRONOUS POLYMORPHISM
// ============================================================================

console.log("\n17. ASYNCHRONOUS POLYMORPHISM");

class DataSource {
    async fetch() {
        throw new Error("fetch() must be implemented.");
    }
}

class MemoryDataSource extends DataSource {
    constructor(records) {
        super();
        this.records = [...records];
    }

    async fetch() {
        return [...this.records];
    }
}

class DelayedDataSource extends DataSource {
    constructor(records, delayMilliseconds = 10) {
        super();
        this.records = [...records];
        this.delayMilliseconds = delayMilliseconds;
    }

    async fetch() {
        await new Promise(resolve => {
            setTimeout(resolve, this.delayMilliseconds);
        });

        return [...this.records];
    }
}

async function printRecords(source) {
    const records = await source.fetch();
    console.log("Records:", records);
}

(async () => {
    await printRecords(
        new MemoryDataSource(["A", "B", "C"])
    );

    await printRecords(
        new DelayedDataSource(["X", "Y", "Z"])
    );

    await runAdvancedCaseStudy();
})();


// ============================================================================
// 18. EVENT-DRIVEN POLYMORPHISM
// ============================================================================

class EventBus {
    #handlers = new Map();

    subscribe(eventName, handler) {
        if (typeof handler !== "function") {
            throw new TypeError("Handler must be a function.");
        }

        if (!this.#handlers.has(eventName)) {
            this.#handlers.set(eventName, new Set());
        }

        this.#handlers.get(eventName).add(handler);

        return () => {
            this.#handlers.get(eventName)?.delete(handler);
        };
    }

    publish(eventName, payload) {
        const handlers = this.#handlers.get(eventName) ?? [];

        for (const handler of handlers) {
            handler(payload);
        }
    }
}

const eventBus = new EventBus();

const unsubscribe = eventBus.subscribe("order.created", order => {
    console.log("Audit listener:", order.id);
});

eventBus.subscribe("order.created", order => {
    console.log("Notification listener:", order.customer);
});

eventBus.publish("order.created", {
    id: "ORD-100",
    customer: "Atul"
});

unsubscribe();


// ============================================================================
// 19. ADVANCED CASE STUDY: ORDER PROCESSING PLATFORM
// ============================================================================

async function runAdvancedCaseStudy() {
    console.log("\n19. ADVANCED CASE STUDY: ORDER PROCESSING PLATFORM");

    class Order {
        #status = "created";

        constructor(id, customer, total) {
            if (!id.trim()) {
                throw new Error("Order ID is required.");
            }

            if (!customer.trim()) {
                throw new Error("Customer is required.");
            }

            if (!Number.isFinite(total) || total <= 0) {
                throw new Error("Order total must be positive.");
            }

            this.id = id;
            this.customer = customer;
            this.total = total;
        }

        get status() {
            return this.#status;
        }

        markPaid() {
            if (this.#status !== "created") {
                throw new Error("Only created orders can be paid.");
            }

            this.#status = "paid";
        }

        markShipped() {
            if (this.#status !== "paid") {
                throw new Error("Only paid orders can be shipped.");
            }

            this.#status = "shipped";
        }
    }

    class PaymentGateway {
        async charge(_amount) {
            throw new Error("charge() must be implemented.");
        }
    }

    class CardGateway extends PaymentGateway {
        async charge(amount) {
            if (amount > 100000) {
                return false;
            }

            return true;
        }
    }

    class WalletGateway extends PaymentGateway {
        async charge(amount) {
            if (amount > 50000) {
                return false;
            }

            return true;
        }
    }

    class ShippingProvider {
        quote(_order) {
            throw new Error("quote() must be implemented.");
        }
    }

    class StandardShipping extends ShippingProvider {
        quote(order) {
            return 100 + order.total * 0.02;
        }
    }

    class ExpressShipping extends ShippingProvider {
        quote(order) {
            return 250 + order.total * 0.05;
        }
    }

    class OrderProcessor {
        constructor(paymentGateway, shippingProvider, eventBus) {
            if (!(paymentGateway instanceof PaymentGateway)) {
                throw new TypeError("Invalid payment gateway.");
            }

            if (!(shippingProvider instanceof ShippingProvider)) {
                throw new TypeError("Invalid shipping provider.");
            }

            this.paymentGateway = paymentGateway;
            this.shippingProvider = shippingProvider;
            this.eventBus = eventBus;
        }

        async process(order) {
            const charged = await this.paymentGateway.charge(order.total);

            if (!charged) {
                throw new Error("Payment was declined.");
            }

            order.markPaid();

            const shippingCost = this.shippingProvider.quote(order);

            this.eventBus.publish("order.paid", {
                orderId: order.id,
                shippingCost
            });

            order.markShipped();

            this.eventBus.publish("order.shipped", {
                orderId: order.id
            });

            return {
                orderId: order.id,
                status: order.status,
                shippingCost
            };
        }
    }

    const localBus = new EventBus();

    localBus.subscribe("order.paid", data => {
        console.log("Payment event:", data);
    });

    localBus.subscribe("order.shipped", data => {
        console.log("Shipping event:", data);
    });

    const order = new Order("ORD-9001", "Atul", 5000);

    const processor = new OrderProcessor(
        new CardGateway(),
        new ExpressShipping(),
        localBus
    );

    const result = await processor.process(order);

    console.log("Processed order:", result);

    try {
        order.markPaid();
    } catch (error) {
        console.log("Invalid state transition:", error.message);
    }


    // ========================================================================
    // 20. EDGE CASES AND VALIDATION
    // ========================================================================

    console.log("\n20. EDGE CASES AND VALIDATION");

    const invalidCases = [
        () => new BankAccount("", 100),
        () => new BankAccount("A", -1),
        () => new InventoryItem("SKU", -2),
        () => new Money(Infinity),
        () => new Money(100, "INR").add(new Money(20, "USD")),
        () => new Order("ORDER", "Customer", 0)
    ];

    for (const test of invalidCases) {
        try {
            test();
        } catch (error) {
            console.log("Expected failure:", error.message);
        }
    }


    // ========================================================================
    // 21. PROTOTYPE RELATIONSHIPS
    // ========================================================================

    console.log("\n21. PROTOTYPE RELATIONSHIPS");

    console.log(
        "dog instanceof Dog:",
        dog instanceof Dog
    );

    console.log(
        "dog instanceof Animal:",
        dog instanceof Animal
    );

    console.log(
        "Dog.prototype inherits from Animal.prototype:",
        Object.getPrototypeOf(Dog.prototype) === Animal.prototype
    );


    // ========================================================================
    // 22. OWN PROPERTIES VS INHERITED METHODS
    // ========================================================================

    console.log("\n22. OWN PROPERTIES VS INHERITED METHODS");

    console.log(
        "name is an own property:",
        Object.hasOwn(dog, "name")
    );

    console.log(
        "speak is an own property:",
        Object.hasOwn(dog, "speak")
    );

    console.log(
        "speak exists through prototype lookup:",
        typeof dog.speak === "function"
    );


    // ========================================================================
    // 23. PERFORMANCE CONSIDERATIONS
    // ========================================================================

    console.log("\n23. PERFORMANCE CONSIDERATIONS");

    const values = Array.from({ length: 100000 }, (_, index) => index);
    const lookupSet = new Set(values);

    const listStart = performance.now();
    values.includes(99999);
    const listDuration = performance.now() - listStart;

    const setStart = performance.now();
    lookupSet.has(99999);
    const setDuration = performance.now() - setStart;

    console.log(`Array membership: ${listDuration.toFixed(6)} ms`);
    console.log(`Set membership:   ${setDuration.toFixed(6)} ms`);


    // ========================================================================
    // 24. FOUR CORE PRINCIPLES
    // ========================================================================

    console.log("\n24. FOUR CORE PRINCIPLES");

    const principles = {
        Encapsulation:
            "Control access to state and keep state-changing rules with the object.",
        Inheritance:
            "Specialize an existing type when the subtype relationship is valid.",
        Polymorphism:
            "Use one operation or contract with multiple concrete implementations.",
        Abstraction:
            "Expose essential behavior while hiding implementation details."
    };

    for (const [principle, definition] of Object.entries(principles)) {
        console.log(`${principle}: ${definition}`);
    }


    // ========================================================================
    // 25. SELF-CHECKS
    // ========================================================================

    console.log("\n25. SELF-CHECKS");

    console.assert(dog instanceof Animal);
    console.assert(cat instanceof Animal);
    console.assert(dog.speak() !== cat.speak());
    console.assert(account.balance === 11250);
    console.assert(Math.abs(temperature.celsius - 100) < 1e-10);
    console.assert(moneyA.add(moneyB).equals(new Money(1250)));
    console.assert(inventory.quantity === 12);
    console.assert(order.status === "shipped");

    console.log("All JavaScript OOP demonstrations completed successfully.");
}
