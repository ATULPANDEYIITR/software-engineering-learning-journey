'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const test = require('node:test');

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ValidationError';
    }
}

const OrderStatus = Object.freeze({
    NEW: 'new',
    PAID: 'paid',
    CANCELLED: 'cancelled'
});

class Product {
    constructor(id, name, price, stock) {
        if (!id || !id.trim()) throw new ValidationError('product id is required');
        if (!name || !name.trim()) throw new ValidationError('product name is required');
        if (!Number.isFinite(price) || price < 0) {
            throw new ValidationError('price must be a non-negative number');
        }
        if (!Number.isInteger(stock) || stock < 0) {
            throw new ValidationError('stock must be a non-negative integer');
        }

        this.id = id;
        this.name = name;
        this.price = Number(price.toFixed(2));
        this.stock = stock;
    }
}

class Inventory {
    constructor(products = []) {
        this.products = new Map(products.map(product => [product.id, product]));
    }

    get(productId) {
        const product = this.products.get(productId);
        if (!product) {
            throw new ValidationError(`unknown product: ${productId}`);
        }
        return product;
    }

    reserve(productId, quantity) {
        const product = this.get(productId);
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new ValidationError('quantity must be positive');
        }
        if (product.stock < quantity) {
            throw new ValidationError(
                `insufficient stock: ${productId}, requested=${quantity}, available=${product.stock}`
            );
        }
        product.stock -= quantity;
    }

    release(productId, quantity) {
        const product = this.get(productId);
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new ValidationError('quantity must be positive');
        }
        product.stock += quantity;
    }

    stock(productId) {
        return this.get(productId).stock;
    }
}

class Order {
    constructor(id, customer) {
        if (!id || !id.trim()) throw new ValidationError('order id is required');
        if (!customer || !customer.trim()) {
            throw new ValidationError('customer is required');
        }

        this.id = id;
        this.customer = customer;
        this.items = [];
        this.status = OrderStatus.NEW;
    }

    addItem(productId, quantity) {
        if (!Number.isInteger(quantity) || quantity <= 0) {
            throw new ValidationError('quantity must be positive');
        }
        this.items.push({ productId, quantity });
    }
}

class OrderService {
    static TAX_RATE = 0.18;

    constructor(inventory) {
        this.inventory = inventory;
    }

    subtotal(order) {
        if (order.items.length === 0) {
            throw new ValidationError('order must contain items');
        }

        return Number(
            order.items
                .reduce((sum, item) => {
                    return sum + this.inventory.get(item.productId).price * item.quantity;
                }, 0)
                .toFixed(2)
        );
    }

    total(order) {
        const subtotal = this.subtotal(order);
        return Number((subtotal * (1 + OrderService.TAX_RATE)).toFixed(2));
    }

    async pay(order) {
        if (order.status !== OrderStatus.NEW) {
            throw new ValidationError(`cannot pay ${order.status} order`);
        }

        const reserved = [];

        try {
            for (const item of order.items) {
                this.inventory.reserve(item.productId, item.quantity);
                reserved.push(item);
                await Promise.resolve();
            }
        } catch (error) {
            for (const item of reserved) {
                this.inventory.release(item.productId, item.quantity);
            }
            throw error;
        }

        order.status = OrderStatus.PAID;
        return this.total(order);
    }

    cancel(order) {
        if (order.status !== OrderStatus.PAID) {
            throw new ValidationError('only paid orders can be cancelled');
        }

        for (const item of order.items) {
            this.inventory.release(item.productId, item.quantity);
        }

        order.status = OrderStatus.CANCELLED;
    }
}

function createFixture() {
    return new Inventory([
        new Product('KB-01', 'Mechanical Keyboard', 80, 10),
        new Product('MS-01', 'Wireless Mouse', 25, 20),
        new Product('HD-01', 'USB Headset', 45, 5)
    ]);
}

function createOrder() {
    const order = new Order('ORD-100', 'Test Customer');
    order.addItem('KB-01', 2);
    order.addItem('MS-01', 1);
    return order;
}

test('product validation accepts valid fixture', () => {
    const product = new Product('P1', 'Keyboard', 50, 3);
    assert.equal(product.price, 50);
    assert.equal(product.stock, 3);
});

test('negative price is rejected', () => {
    assert.throws(
        () => new Product('P1', 'Keyboard', -1, 1),
        ValidationError
    );
});

test('zero quantity is rejected', () => {
    const order = new Order('ORD-1', 'Customer');
    assert.throws(
        () => order.addItem('P1', 0),
        ValidationError
    );
});

test('subtotal is calculated from fixture data', () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    assert.equal(service.subtotal(order), 185);
});

test('total includes tax', () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    assert.equal(service.total(order), 218.3);
});

test('payment changes state and reserves stock', async () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    const total = await service.pay(order);

    assert.equal(total, 218.3);
    assert.equal(order.status, OrderStatus.PAID);
    assert.equal(inventory.stock('KB-01'), 8);
    assert.equal(inventory.stock('MS-01'), 19);
});

test('failed multi-item reservation rolls back previous reservations', async () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = new Order('ORD-2', 'Customer');
    order.addItem('KB-01', 2);
    order.addItem('HD-01', 6);

    await assert.rejects(
        () => service.pay(order),
        ValidationError
    );

    assert.equal(inventory.stock('KB-01'), 10);
    assert.equal(inventory.stock('HD-01'), 5);
    assert.equal(order.status, OrderStatus.NEW);
});

test('paid order cannot be paid twice', async () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    await service.pay(order);

    await assert.rejects(
        () => service.pay(order),
        ValidationError
    );

    assert.equal(inventory.stock('KB-01'), 8);
});

test('cancellation releases reserved inventory', async () => {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    await service.pay(order);
    service.cancel(order);

    assert.equal(order.status, OrderStatus.CANCELLED);
    assert.equal(inventory.stock('KB-01'), 10);
    assert.equal(inventory.stock('MS-01'), 20);
});

test('temporary file fixture can store structured test data', async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'unit-test-'));
    const file = path.join(directory, 'order.json');

    try {
        const order = createOrder();
        await fs.writeFile(
            file,
            JSON.stringify(order, null, 2),
            'utf8'
        );

        const loaded = JSON.parse(await fs.readFile(file, 'utf8'));

        assert.equal(loaded.id, 'ORD-100');
        assert.equal(loaded.items.length, 2);
    } finally {
        await fs.rm(directory, { recursive: true, force: true });
    }
});

async function runExample() {
    const inventory = createFixture();
    const service = new OrderService(inventory);
    const order = createOrder();

    console.log('Unit-testing case study');
    console.log(`Order: ${order.id}`);
    console.log(`Subtotal: ${service.subtotal(order).toFixed(2)}`);
    console.log(`Total: ${service.total(order).toFixed(2)}`);
}

runExample().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
