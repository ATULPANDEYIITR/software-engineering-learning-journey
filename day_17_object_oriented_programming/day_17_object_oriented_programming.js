/*
Object-Oriented Programming in JavaScript
==========================================

A self-contained executable study file covering:
- Objects and classes
- Constructors
- Instance properties and methods
- Static members
- Getters and setters
- Encapsulation
- Private fields
- Inheritance
- Method overriding
- Polymorphism
- Composition
- Prototypes
- Symbols
- Iterators
- Generators
- Mixins
- Abstract-style contracts
- Dependency injection
- Design patterns
- Asynchronous OOP
- Validation
- Error handling
- Performance considerations

Run with Node.js 18+.
*/

// =============================================================================
// 1. OBJECTS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("1. Objects and Basic Behavior");
console.log("=".repeat(78));

const student = {
    name: "Ananya",
    age: 21,

    introduce() {
        return `My name is ${this.name} and I am ${this.age} years old.`;
    }
};

console.log(student.introduce());
console.log("Object:", student);
console.log("Name:", student.name);


// =============================================================================
// 2. CLASSES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("2. Classes and Instances");
console.log("=".repeat(78));

class Student {
    constructor(name, age) {
        if (!name || typeof name !== "string") {
            throw new TypeError("Student name must be a non-empty string.");
        }

        if (!Number.isInteger(age) || age <= 0) {
            throw new RangeError("Age must be a positive integer.");
        }

        this.name = name;
        this.age = age;
    }

    introduce() {
        return `${this.name} is ${this.age} years old.`;
    }
}

const studentA = new Student("Riya", 20);
const studentB = new Student("Kabir", 22);

console.log(studentA.introduce());
console.log(studentB.introduce());
console.log(studentA instanceof Student);


// =============================================================================
// 3. INSTANCE VS STATIC MEMBERS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("3. Instance and Static Members");
console.log("=".repeat(78));

class Employee {
    static company = "Example Technologies";
    static employeeCount = 0;

    constructor(name, salary) {
        if (salary < 0) {
            throw new RangeError("Salary cannot be negative.");
        }

        this.name = name;
        this.salary = salary;
        Employee.employeeCount++;
    }

    describe() {
        return `${this.name}: ${this.salary.toFixed(2)}`;
    }

    static isValidSalary(salary) {
        return Number.isFinite(salary) && salary >= 0;
    }
}

const employeeA = new Employee("Amit", 80000);
const employeeB = new Employee("Meera", 95000);

console.log(employeeA.describe());
console.log(employeeB.describe());
console.log("Company:", Employee.company);
console.log("Employee count:", Employee.employeeCount);
console.log("Valid salary:", Employee.isValidSalary(50000));


// =============================================================================
// 4. GETTERS AND SETTERS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("4. Getters and Setters");
console.log("=".repeat(78));

class Product {
    constructor(name, price) {
        this.name = name;
        this.price = price;
    }

    get price() {
        return this._price;
    }

    set price(value) {
        if (!Number.isFinite(value) || value < 0) {
            throw new RangeError("Price must be a non-negative finite number.");
        }

        this._price = value;
    }

    get discountedPrice() {
        return this._price * 0.9;
    }
}

const keyboard = new Product("Keyboard", 2500);

console.log("Price:", keyboard.price);
console.log("Discounted price:", keyboard.discountedPrice);

keyboard.price = 2200;
console.log("Updated price:", keyboard.price);

try {
    keyboard.price = -1;
} catch (error) {
    console.log("Expected validation error:", error.message);
}


// =============================================================================
// 5. PRIVATE FIELDS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("5. JavaScript Private Fields");
console.log("=".repeat(78));

class BankAccount {
    #balance;
    #transactionCount = 0;

    constructor(owner, openingBalance = 0) {
        if (openingBalance < 0) {
            throw new RangeError("Opening balance cannot be negative.");
        }

        this.owner = owner;
        this.#balance = openingBalance;
    }

    deposit(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new RangeError("Deposit must be positive and finite.");
        }

        this.#balance += amount;
        this.#transactionCount++;
    }

    withdraw(amount) {
        if (!Number.isFinite(amount) || amount <= 0) {
            throw new RangeError("Withdrawal must be positive and finite.");
        }

        if (amount > this.#balance) {
            throw new Error("Insufficient funds.");
        }

        this.#balance -= amount;
        this.#transactionCount++;
    }

    get balance() {
        return this.#balance;
    }

    get transactionCount() {
        return this.#transactionCount;
    }
}

const account = new BankAccount("Neha", 1000);
account.deposit(500);
account.withdraw(250);

console.log("Balance:", account.balance);
console.log("Transactions:", account.transactionCount);

try {
    account.withdraw(5000);
} catch (error) {
    console.log("Expected bank error:", error.message);
}


// =============================================================================
// 6. INHERITANCE
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("6. Inheritance and Method Overriding");
console.log("=".repeat(78));

class Vehicle {
    constructor(brand) {
        this.brand = brand;
    }

    move() {
        return `${this.brand} vehicle is moving.`;
    }
}

class Car extends Vehicle {
    move() {
        return `${this.brand} car is driving.`;
    }
}

class ElectricCar extends Car {
    constructor(brand, batteryKWh) {
        super(brand);

        if (batteryKWh <= 0) {
            throw new RangeError("Battery capacity must be positive.");
        }

        this.batteryKWh = batteryKWh;
    }

    move() {
        return `${this.brand} electric car is driving silently.`;
    }
}

const vehicles = [
    new Vehicle("Generic"),
    new Car("Toyota"),
    new ElectricCar("Tesla", 75)
];

for (const vehicle of vehicles) {
    console.log(vehicle.move());
}


// =============================================================================
// 7. POLYMORPHISM
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("7. Polymorphism");
console.log("=".repeat(78));

class Dog {
    speak() {
        return "Woof";
    }
}

class Cat {
    speak() {
        return "Meow";
    }
}

class Cow {
    speak() {
        return "Moo";
    }
}

function makeAnimalSpeak(animal) {
    if (!animal || typeof animal.speak !== "function") {
        throw new TypeError("Object must provide a speak() method.");
    }

    return animal.speak();
}

for (const animal of [new Dog(), new Cat(), new Cow()]) {
    console.log(makeAnimalSpeak(animal));
}


// =============================================================================
// 8. COMPOSITION
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("8. Composition");
console.log("=".repeat(78));

class Engine {
    start() {
        return "Engine started.";
    }
}

class ComposedCar {
    constructor(brand, engine) {
        if (!engine || typeof engine.start !== "function") {
            throw new TypeError("A compatible engine is required.");
        }

        this.brand = brand;
        this.engine = engine;
    }

    start() {
        return `${this.brand}: ${this.engine.start()}`;
    }
}

const engine = new Engine();
const composedCar = new ComposedCar("Honda", engine);

console.log(composedCar.start());


// =============================================================================
// 9. PROTOTYPES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("9. Prototype-Based Object Model");
console.log("=".repeat(78));

function LegacyPerson(name) {
    this.name = name;
}

LegacyPerson.prototype.describe = function () {
    return `Person: ${this.name}`;
};

const legacyPerson = new LegacyPerson("Arjun");

console.log(legacyPerson.describe());
console.log(
    "Prototype:",
    Object.getPrototypeOf(legacyPerson) === LegacyPerson.prototype
);


// =============================================================================
// 10. SYMBOL-BASED CUSTOM REPRESENTATION
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("10. Symbol.toPrimitive and Custom Conversion");
console.log("=".repeat(78));

class Money {
    constructor(amount, currency = "INR") {
        if (!Number.isFinite(amount)) {
            throw new TypeError("Amount must be finite.");
        }

        this.amount = amount;
        this.currency = currency;
    }

    [Symbol.toPrimitive](hint) {
        if (hint === "string") {
            return `${this.currency} ${this.amount.toFixed(2)}`;
        }

        return this.amount;
    }
}

const money = new Money(1500);

console.log(String(money));
console.log(Number(money));
console.log(money + 500);


// =============================================================================
// 11. ITERATORS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("11. Custom Iterable Object");
console.log("=".repeat(78));

class NumberRange {
    constructor(start, end) {
        this.start = start;
        this.end = end;
    }

    *[Symbol.iterator]() {
        for (let value = this.start; value < this.end; value++) {
            yield value;
        }
    }
}

const range = new NumberRange(2, 7);

console.log([...range]);

for (const number of range) {
    process.stdout.write(`${number} `);
}

console.log();


// =============================================================================
// 12. MIXINS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("12. Mixins");
console.log("=".repeat(78));

const LoggerMixin = {
    log(message) {
        console.log(`[LOG] ${message}`);
    }
};

const TimestampMixin = {
    timestamp() {
        return new Date().toISOString();
    }
};

class Application {
    run() {
        this.log(`Application started at ${this.timestamp()}`);
    }
}

Object.assign(Application.prototype, LoggerMixin, TimestampMixin);

const application = new Application();
application.run();


// =============================================================================
// 13. ABSTRACT-STYLE CONTRACT
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("13. Abstract-Style Classes");
console.log("=".repeat(78));

class Shape {
    constructor() {
        if (new.target === Shape) {
            throw new Error("Shape is an abstract concept.");
        }
    }

    area() {
        throw new Error("Concrete shape must implement area().");
    }
}

class Rectangle extends Shape {
    constructor(width, height) {
        super();

        if (width <= 0 || height <= 0) {
            throw new RangeError("Dimensions must be positive.");
        }

        this.width = width;
        this.height = height;
    }

    area() {
        return this.width * this.height;
    }
}

class Circle extends Shape {
    constructor(radius) {
        super();

        if (radius <= 0) {
            throw new RangeError("Radius must be positive.");
        }

        this.radius = radius;
    }

    area() {
        return Math.PI * this.radius ** 2;
    }
}

for (const shape of [new Rectangle(10, 5), new Circle(3)]) {
    console.log(
        shape.constructor.name,
        "area =",
        shape.area().toFixed(2)
    );
}


// =============================================================================
// 14. DEPENDENCY INJECTION
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("14. Dependency Injection");
console.log("=".repeat(78));

class ConsoleNotifier {
    send(message) {
        console.log("NOTIFICATION:", message);
    }
}

class OrderService {
    constructor(notifier) {
        if (!notifier || typeof notifier.send !== "function") {
            throw new TypeError("Notifier must provide send().");
        }

        this.notifier = notifier;
    }

    placeOrder(orderId, amount) {
        if (!orderId) {
            throw new Error("Order ID is required.");
        }

        if (!Number.isFinite(amount) || amount <= 0) {
            throw new RangeError("Order amount must be positive.");
        }

        this.notifier.send(
            `Order ${orderId} placed for ${amount.toFixed(2)}.`
        );
    }
}

const orderService = new OrderService(new ConsoleNotifier());
orderService.placeOrder("ORD-100", 1499.99);


// =============================================================================
// 15. FACTORY PATTERN
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("15. Factory Pattern");
console.log("=".repeat(78));

class Notification {
    send() {
        throw new Error("send() must be implemented.");
    }
}

class EmailNotification extends Notification {
    send(message) {
        return `Email sent: ${message}`;
    }
}

class SMSNotification extends Notification {
    send(message) {
        return `SMS sent: ${message}`;
    }
}

class NotificationFactory {
    static create(channel) {
        switch (channel.toLowerCase()) {
            case "email":
                return new EmailNotification();

            case "sms":
                return new SMSNotification();

            default:
                throw new Error(`Unsupported channel: ${channel}`);
        }
    }
}

for (const channel of ["email", "sms"]) {
    const notification = NotificationFactory.create(channel);
    console.log(notification.send("Account updated."));
}


// =============================================================================
// 16. STRATEGY PATTERN
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("16. Strategy Pattern");
console.log("=".repeat(78));

class RegularPricing {
    calculate(price) {
        return price;
    }
}

class PremiumPricing {
    calculate(price) {
        return price * 0.9;
    }
}

class SeasonalPricing {
    calculate(price) {
        return price * 0.8;
    }
}

class Checkout {
    constructor(pricingStrategy) {
        if (
            !pricingStrategy ||
            typeof pricingStrategy.calculate !== "function"
        ) {
            throw new TypeError("Invalid pricing strategy.");
        }

        this.pricingStrategy = pricingStrategy;
    }

    finalPrice(price) {
        if (!Number.isFinite(price) || price < 0) {
            throw new RangeError("Price must be non-negative.");
        }

        return this.pricingStrategy.calculate(price);
    }
}

for (const strategy of [
    new RegularPricing(),
    new PremiumPricing(),
    new SeasonalPricing()
]) {
    console.log(
        "Final price:",
        new Checkout(strategy).finalPrice(1000)
    );
}


// =============================================================================
// 17. REALISTIC CASE STUDY: LIBRARY SYSTEM
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("17. Industry-Style Case Study: Library Management");
console.log("=".repeat(78));

class Book {
    constructor(isbn, title, author) {
        if (!isbn?.trim()) {
            throw new Error("ISBN is required.");
        }

        if (!title?.trim()) {
            throw new Error("Title is required.");
        }

        if (!author?.trim()) {
            throw new Error("Author is required.");
        }

        this.isbn = isbn;
        this.title = title;
        this.author = author;
    }
}

class LibraryMember {
    constructor(memberId, name) {
        if (!memberId?.trim()) {
            throw new Error("Member ID is required.");
        }

        if (!name?.trim()) {
            throw new Error("Member name is required.");
        }

        this.memberId = memberId;
        this.name = name;
        this.borrowedIsbns = new Set();
    }

    borrow(isbn) {
        this.borrowedIsbns.add(isbn);
    }

    returnBook(isbn) {
        this.borrowedIsbns.delete(isbn);
    }
}

class Library {
    static MAX_BOOKS_PER_MEMBER = 3;

    #books = new Map();
    #members = new Map();

    addBook(book) {
        if (!(book instanceof Book)) {
            throw new TypeError("Only Book objects can be added.");
        }

        if (this.#books.has(book.isbn)) {
            throw new Error(`Book already exists: ${book.isbn}`);
        }

        this.#books.set(book.isbn, book);
    }

    registerMember(member) {
        if (!(member instanceof LibraryMember)) {
            throw new TypeError("Only LibraryMember objects are accepted.");
        }

        if (this.#members.has(member.memberId)) {
            throw new Error(`Member already exists: ${member.memberId}`);
        }

        this.#members.set(member.memberId, member);
    }

    #getMember(memberId) {
        const member = this.#members.get(memberId);

        if (!member) {
            throw new Error(`Unknown member: ${memberId}`);
        }

        return member;
    }

    #getBook(isbn) {
        const book = this.#books.get(isbn);

        if (!book) {
            throw new Error(`Unknown ISBN: ${isbn}`);
        }

        return book;
    }

    #isBorrowed(isbn) {
        for (const member of this.#members.values()) {
            if (member.borrowedIsbns.has(isbn)) {
                return true;
            }
        }

        return false;
    }

    borrowBook(memberId, isbn) {
        const member = this.#getMember(memberId);

        this.#getBook(isbn);

        if (member.borrowedIsbns.has(isbn)) {
            throw new Error("Member already borrowed this book.");
        }

        if (
            member.borrowedIsbns.size >=
            Library.MAX_BOOKS_PER_MEMBER
        ) {
            throw new Error("Borrowing limit reached.");
        }

        if (this.#isBorrowed(isbn)) {
            throw new Error("Book is currently unavailable.");
        }

        member.borrow(isbn);

        return `${member.name} borrowed ${isbn}.`;
    }

    returnBook(memberId, isbn) {
        const member = this.#getMember(memberId);

        if (!member.borrowedIsbns.has(isbn)) {
            throw new Error("Member has not borrowed this book.");
        }

        member.returnBook(isbn);

        return `${member.name} returned ${isbn}.`;
    }

    searchByAuthor(author) {
        const query = author.toLowerCase();

        return [...this.#books.values()].filter(book =>
            book.author.toLowerCase().includes(query)
        );
    }

    availableBooks() {
        return [...this.#books.values()].filter(
            book => !this.#isBorrowed(book.isbn)
        );
    }
}

const library = new Library();

library.addBook(
    new Book("978-1", "Clean Code", "Robert C. Martin")
);

library.addBook(
    new Book(
        "978-2",
        "The Pragmatic Programmer",
        "Andrew Hunt"
    )
);

library.addBook(
    new Book(
        "978-3",
        "JavaScript: The Good Parts",
        "Douglas Crockford"
    )
);

library.registerMember(
    new LibraryMember("M001", "Ananya")
);

library.registerMember(
    new LibraryMember("M002", "Kabir")
);

console.log(library.borrowBook("M001", "978-1"));
console.log(library.borrowBook("M002", "978-2"));

try {
    library.borrowBook("M002", "978-1");
} catch (error) {
    console.log("Expected library error:", error.message);
}

console.log(
    "Author search:",
    library.searchByAuthor("crockford")
);

console.log(
    "Available books:",
    library.availableBooks().map(book => book.title)
);

console.log(library.returnBook("M001", "978-1"));


// =============================================================================
// 18. ASYNCHRONOUS OOP
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("18. Asynchronous Object-Oriented Programming");
console.log("=".repeat(78));

class DataRepository {
    async fetchRecord(id) {
        if (!id) {
            throw new Error("Record ID is required.");
        }

        // Simulates I/O without requiring an external service.
        await new Promise(resolve => setTimeout(resolve, 20));

        return {
            id,
            status: "active",
            loadedAt: new Date().toISOString()
        };
    }
}

class UserService {
    constructor(repository) {
        this.repository = repository;
    }

    async getUser(id) {
        const record = await this.repository.fetchRecord(id);

        return {
            ...record,
            service: "UserService"
        };
    }
}

async function runAsyncExample() {
    const service = new UserService(new DataRepository());
    const user = await service.getUser("U-100");

    console.log("Async result:", user);
}


// =============================================================================
// 19. OBJECT CLONING AND REFERENCES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("19. References and Cloning");
console.log("=".repeat(78));

const original = {
    profile: {
        name: "Asha"
    }
};

const shallowCopy = { ...original };

shallowCopy.profile.name = "Changed";

console.log("Original after shallow copy mutation:", original.profile.name);

const deepCopy = structuredClone(original);

deepCopy.profile.name = "Deep Copy Name";

console.log("Original after deep clone mutation:", original.profile.name);
console.log("Deep copy:", deepCopy.profile.name);


// =============================================================================
// 20. OBJECT FREEZING
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("20. Immutability with Object.freeze");
console.log("=".repeat(78));

const configuration = Object.freeze({
    environment: "production",
    timeoutMs: 5000
});

try {
    configuration.timeoutMs = 1000;
} catch (error) {
    console.log("Expected strict-mode-style error:", error.message);
}

console.log("Configuration:", configuration);


// =============================================================================
// 21. VALIDATION AND ERROR TYPES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("21. Custom Error Classes");
console.log("=".repeat(78));

class ValidationError extends Error {
    constructor(message, field) {
        super(message);
        this.name = "ValidationError";
        this.field = field;
    }
}

class AccountService {
    createAccount(username) {
        if (!username || username.length < 3) {
            throw new ValidationError(
                "Username must contain at least three characters.",
                "username"
            );
        }

        return {
            username,
            created: true
        };
    }
}

try {
    new AccountService().createAccount("A");
} catch (error) {
    if (error instanceof ValidationError) {
        console.log(
            "Validation error:",
            error.field,
            error.message
        );
    }
}


// =============================================================================
// 22. EVENT-DRIVEN OOP WITHOUT EXTERNAL PACKAGES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("22. Event-Driven Object Design");
console.log("=".repeat(78));

class EventEmitterLite {
    #listeners = new Map();

    on(eventName, listener) {
        if (typeof listener !== "function") {
            throw new TypeError("Listener must be a function.");
        }

        if (!this.#listeners.has(eventName)) {
            this.#listeners.set(eventName, []);
        }

        this.#listeners.get(eventName).push(listener);
    }

    emit(eventName, payload) {
        const listeners = this.#listeners.get(eventName) ?? [];

        for (const listener of listeners) {
            listener(payload);
        }
    }
}

const eventBus = new EventEmitterLite();

eventBus.on("order.created", order => {
    console.log("Order created:", order.id);
});

eventBus.on("order.created", order => {
    console.log("Order amount:", order.amount);
});

eventBus.emit("order.created", {
    id: "ORD-200",
    amount: 4500
});


// =============================================================================
// 23. PERFORMANCE
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("23. Performance Considerations");
console.log("=".repeat(78));

class Counter {
    constructor() {
        this.value = 0;
    }

    increment() {
        this.value++;
    }
}

const counter = new Counter();

const startTime = process.hrtime.bigint();

for (let index = 0; index < 100000; index++) {
    counter.increment();
}

const elapsedNanoseconds =
    process.hrtime.bigint() - startTime;

console.log("Counter:", counter.value);
console.log(
    "100,000 method calls:",
    Number(elapsedNanoseconds) / 1_000_000,
    "ms approximately"
);


// =============================================================================
// 24. COMMON OOP ISSUE: THIS CONTEXT
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("24. this and Method Binding");
console.log("=".repeat(78));

class Greeter {
    constructor(name) {
        this.name = name;

        // Arrow functions retain lexical this.
        this.sayArrow = () => {
            return `Hello, ${this.name}`;
        };
    }

    sayMethod() {
        return `Hello, ${this.name}`;
    }
}

const greeter = new Greeter("Priya");

const detachedArrow = greeter.sayArrow;
console.log(detachedArrow());

const detachedMethod = greeter.sayMethod.bind(greeter);
console.log(detachedMethod());


// =============================================================================
// 25. INTEGRATED E-COMMERCE CASE STUDY
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("25. Integrated E-Commerce Domain");
console.log("=".repeat(78));

class LineItem {
    constructor(productName, unitPrice, quantity) {
        if (!productName?.trim()) {
            throw new ValidationError(
                "Product name is required.",
                "productName"
            );
        }

        if (!Number.isFinite(unitPrice) || unitPrice < 0) {
            throw new ValidationError(
                "Unit price must be non-negative.",
                "unitPrice"
            );
        }

        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new ValidationError(
                "Quantity must be a positive integer.",
                "quantity"
            );
        }

        this.productName = productName;
        this.unitPrice = unitPrice;
        this.quantity = quantity;
    }

    get subtotal() {
        return this.unitPrice * this.quantity;
    }
}

class NoDiscount {
    calculate(subtotal) {
        return 0;
    }
}

class PercentageDiscount {
    constructor(percentage) {
        if (percentage < 0 || percentage > 100) {
            throw new RangeError(
                "Discount must be between 0 and 100."
            );
        }

        this.percentage = percentage;
    }

    calculate(subtotal) {
        return subtotal * this.percentage / 100;
    }
}

class ShoppingCart {
    constructor(discountStrategy) {
        if (
            !discountStrategy ||
            typeof discountStrategy.calculate !== "function"
        ) {
            throw new TypeError("Invalid discount strategy.");
        }

        this.items = [];
        this.discountStrategy = discountStrategy;
    }

    addItem(item) {
        if (!(item instanceof LineItem)) {
            throw new TypeError("Only LineItem objects are accepted.");
        }

        this.items.push(item);
    }

    get subtotal() {
        return this.items.reduce(
            (sum, item) => sum + item.subtotal,
            0
        );
    }

    get discount() {
        return this.discountStrategy.calculate(this.subtotal);
    }

    get total() {
        return this.subtotal - this.discount;
    }

    receipt() {
        const lines = [
            "Receipt",
            "-".repeat(30)
        ];

        for (const item of this.items) {
            lines.push(
                `${item.productName}: ` +
                `${item.quantity} x ${item.unitPrice.toFixed(2)} = ` +
                `${item.subtotal.toFixed(2)}`
            );
        }

        lines.push(
            "-".repeat(30),
            `Subtotal: ${this.subtotal.toFixed(2)}`,
            `Discount: ${this.discount.toFixed(2)}`,
            `Total: ${this.total.toFixed(2)}`
        );

        return lines.join("\n");
    }
}

const cart = new ShoppingCart(
    new PercentageDiscount(10)
);

cart.addItem(new LineItem("Laptop", 75000, 1));
cart.addItem(new LineItem("Mouse", 1500, 2));
cart.addItem(new LineItem("Keyboard", 2500, 1));

console.log(cart.receipt());


// =============================================================================
// 26. BASIC TESTING
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("26. Lightweight Tests");
console.log("=".repeat(78));

function assertEqual(actual, expected, message) {
    if (actual !== expected) {
        throw new Error(
            `${message}: expected ${expected}, got ${actual}`
        );
    }
}

function assertThrows(callback, expectedErrorType) {
    try {
        callback();
    } catch (error) {
        if (error instanceof expectedErrorType) {
            return;
        }

        throw new Error(
            `Expected ${expectedErrorType.name}, got ${error.constructor.name}`
        );
    }

    throw new Error(
        `Expected ${expectedErrorType.name} to be thrown.`
    );
}

assertEqual(
    new PercentageDiscount(10).calculate(1000),
    100,
    "Percentage discount"
);

assertEqual(
    new LineItem("Mouse", 500, 2).subtotal,
    1000,
    "Line item subtotal"
);

assertThrows(
    () => new LineItem("", 500, 1),
    ValidationError
);

console.log("Basic tests passed.");


// =============================================================================
// 27. SECURITY CONSIDERATIONS
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("27. Security Considerations");
console.log("=".repeat(78));

class Session {
    #token;

    constructor(userId, token) {
        if (!userId || !token) {
            throw new Error("User ID and token are required.");
        }

        this.userId = userId;
        this.#token = token;
    }

    hasToken(candidate) {
        return candidate === this.#token;
    }

    toJSON() {
        // Prevent accidental exposure of the private token.
        return {
            userId: this.userId
        };
    }
}

const session = new Session("U-500", "SECRET_TOKEN");

console.log("Token valid:", session.hasToken("SECRET_TOKEN"));
console.log("Safe serialized session:", JSON.stringify(session));


// =============================================================================
// 28. ADVANCED CLASS FEATURES
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("28. Advanced Class Features");
console.log("=".repeat(78));

class Statistics {
    static mean(values) {
        if (!Array.isArray(values) || values.length === 0) {
            throw new RangeError("A non-empty array is required.");
        }

        if (!values.every(Number.isFinite)) {
            throw new TypeError("All values must be finite numbers.");
        }

        return values.reduce(
            (sum, value) => sum + value,
            0
        ) / values.length;
    }

    static variance(values) {
        const mean = Statistics.mean(values);

        return values.reduce(
            (sum, value) => sum + (value - mean) ** 2,
            0
        ) / values.length;
    }

    static standardDeviation(values) {
        return Math.sqrt(Statistics.variance(values));
    }
}

const data = [10, 20, 30, 40, 50];

console.log("Mean:", Statistics.mean(data));
console.log("Variance:", Statistics.variance(data));
console.log(
    "Standard deviation:",
    Statistics.standardDeviation(data)
);


// =============================================================================
// 29. ASYNC EXECUTION
// =============================================================================

runAsyncExample()
    .then(() => {
        console.log("\nAsynchronous OOP example completed.");
    })
    .catch(error => {
        console.error("Async error:", error.message);
        process.exitCode = 1;
    });


// =============================================================================
// 30. FINAL CHECK
// =============================================================================

console.log("\n" + "=".repeat(78));
console.log("30. Execution Check");
console.log("=".repeat(78));
console.log("Core JavaScript OOP demonstrations completed.");
