'use strict';

/*
 * Database Fundamentals: Relational vs Non-Relational Databases
 *
 * This Node.js program focuses on JavaScript-specific modeling concerns:
 * - relational-style normalized entities represented with Maps
 * - document-oriented aggregate storage
 * - asynchronous event-driven persistence
 * - schema validation at the application boundary
 * - immutable event snapshots
 * - workload-specific query behavior
 *
 * It does not pretend that Maps are a relational or NoSQL database engine.
 * They are used to make the data-model differences visible without external
 * npm dependencies.
 */

const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const { EventEmitter } = require('node:events');
const crypto = require('node:crypto');

function heading(title) {
    console.log(`\n${'='.repeat(72)}`);
    console.log(title);
    console.log('='.repeat(72));
}

/* -------------------------------------------------------------------------
 * Relational-style normalized model
 * ---------------------------------------------------------------------- */

class RelationalRepository {
    constructor() {
        this.customers = new Map();
        this.products = new Map();
        this.orders = new Map();
        this.orderItems = new Map();
    }

    addCustomer(customer) {
        if (!customer.id || !customer.email) {
            throw new Error('Customer requires id and email');
        }

        if (this.customers.has(customer.id)) {
            throw new Error(`Customer ${customer.id} already exists`);
        }

        if ([...this.customers.values()].some(
            existing => existing.email === customer.email
        )) {
            throw new Error(`Email ${customer.email} already exists`);
        }

        this.customers.set(customer.id, structuredClone(customer));
    }

    addProduct(product) {
        if (!product.id || !product.sku) {
            throw new Error('Product requires id and SKU');
        }

        if (product.priceCents < 0) {
            throw new Error('Product price cannot be negative');
        }

        if ([...this.products.values()].some(
            existing => existing.sku === product.sku
        )) {
            throw new Error(`SKU ${product.sku} already exists`);
        }

        this.products.set(product.id, structuredClone(product));
    }

    addOrder(order) {
        if (!this.customers.has(order.customerId)) {
            throw new Error(
                `Cannot create order: customer ${order.customerId} does not exist`
            );
        }

        const validStatuses = new Set([
            'pending',
            'paid',
            'shipped',
            'cancelled'
        ]);

        if (!validStatuses.has(order.status)) {
            throw new Error(`Invalid order status: ${order.status}`);
        }

        this.orders.set(order.id, structuredClone(order));
    }

    addOrderItem(item) {
        if (!this.orders.has(item.orderId)) {
            throw new Error(`Order ${item.orderId} does not exist`);
        }

        if (!this.products.has(item.productId)) {
            throw new Error(`Product ${item.productId} does not exist`);
        }

        if (!Number.isInteger(item.quantity) || item.quantity <= 0) {
            throw new Error('Quantity must be a positive integer');
        }

        const key = `${item.orderId}:${item.productId}`;

        if (this.orderItems.has(key)) {
            throw new Error(`Duplicate order item ${key}`);
        }

        this.orderItems.set(key, structuredClone(item));
    }

    getOrderDetails(orderId) {
        const order = this.orders.get(orderId);

        if (!order) {
            return null;
        }

        const customer = this.customers.get(order.customerId);

        const items = [...this.orderItems.values()]
            .filter(item => item.orderId === orderId)
            .map(item => ({
                ...item,
                product: this.products.get(item.productId)
            }));

        const totalCents = items.reduce(
            (total, item) => (
                total + item.quantity * item.product.priceCents
            ),
            0
        );

        return {
            order,
            customer,
            items,
            totalCents
        };
    }
}

/* -------------------------------------------------------------------------
 * Document-oriented aggregate model
 * ---------------------------------------------------------------------- */

class DocumentValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'DocumentValidationError';
    }
}

function validateProductDocument(document) {
    const required = ['id', 'sku', 'name', 'category', 'priceCents'];

    for (const field of required) {
        if (!(field in document)) {
            throw new DocumentValidationError(
                `Missing document field: ${field}`
            );
        }
    }

    if (!Number.isInteger(document.priceCents) || document.priceCents < 0) {
        throw new DocumentValidationError(
            'priceCents must be a non-negative integer'
        );
    }

    if (!document.attributes || typeof document.attributes !== 'object') {
        throw new DocumentValidationError(
            'Product attributes must be an object'
        );
    }
}

class DocumentCollection {
    constructor() {
        this.documents = new Map();
    }

    async insert(document) {
        validateProductDocument(document);

        if (this.documents.has(document.id)) {
            throw new Error(`Document ${document.id} already exists`);
        }

        this.documents.set(document.id, structuredClone(document));
    }

    findByCategory(category) {
        return [...this.documents.values()]
            .filter(document => document.category === category)
            .map(document => structuredClone(document));
    }

    get(id) {
        const document = this.documents.get(id);
        return document ? structuredClone(document) : null;
    }

    updateAttribute(id, attribute, value) {
        const document = this.documents.get(id);

        if (!document) {
            throw new Error(`Document ${id} does not exist`);
        }

        document.attributes[attribute] = value;
    }

    all() {
        return [...this.documents.values()].map(
            document => structuredClone(document)
        );
    }
}

/* -------------------------------------------------------------------------
 * Event-driven behavior
 * ---------------------------------------------------------------------- */

class DatabaseActivityBus extends EventEmitter {}

class DocumentPersistence {
    constructor(filePath, eventBus) {
        this.filePath = filePath;
        this.eventBus = eventBus;
        this.eventBus.on(
            'document.changed',
            event => this.record(event)
        );
    }

    async record(event) {
        const line = JSON.stringify({
            timestamp: new Date().toISOString(),
            eventId: crypto.randomUUID(),
            ...event
        }) + '\n';

        await fs.appendFile(this.filePath, line, 'utf8');
    }
}

/* -------------------------------------------------------------------------
 * Demonstrations
 * ---------------------------------------------------------------------- */

function buildRelationalRepository() {
    const repository = new RelationalRepository();

    repository.addCustomer({
        id: 'C100',
        name: 'Aisha Khan',
        email: 'aisha@example.com',
        country: 'India'
    });

    repository.addCustomer({
        id: 'C200',
        name: 'Daniel Reed',
        email: 'daniel@example.com',
        country: 'United Kingdom'
    });

    repository.addProduct({
        id: 'P100',
        sku: 'KB-100',
        name: 'Mechanical Keyboard',
        category: 'electronics',
        priceCents: 8900
    });

    repository.addProduct({
        id: 'P200',
        sku: 'MS-200',
        name: 'Wireless Mouse',
        category: 'electronics',
        priceCents: 4200
    });

    repository.addOrder({
        id: 'O1000',
        customerId: 'C100',
        status: 'paid',
        createdAt: '2026-10-19T08:00:00Z'
    });

    repository.addOrderItem({
        orderId: 'O1000',
        productId: 'P100',
        quantity: 1
    });

    repository.addOrderItem({
        orderId: 'O1000',
        productId: 'P200',
        quantity: 2
    });

    return repository;
}

async function buildDocumentCollection(eventBus) {
    const collection = new DocumentCollection();

    const documents = [
        {
            id: 'P100',
            sku: 'KB-100',
            name: 'Mechanical Keyboard',
            category: 'electronics',
            priceCents: 8900,
            attributes: {
                switchType: 'tactile',
                layout: 'US',
                rgb: true
            }
        },
        {
            id: 'P200',
            sku: 'MS-200',
            name: 'Wireless Mouse',
            category: 'electronics',
            priceCents: 4200,
            attributes: {
                dpi: 1600,
                connection: 'Bluetooth',
                batteryMonths: 12
            }
        },
        {
            id: 'P300',
            sku: 'ST-300',
            name: 'Desk Stand',
            category: 'office',
            priceCents: 3500,
            attributes: {
                material: 'aluminium',
                adjustable: true,
                cableChannel: true,
                dimensions: {
                    widthMm: 250,
                    depthMm: 210
                }
            }
        }
    ];

    for (const document of documents) {
        await collection.insert(document);

        eventBus.emit('document.changed', {
            operation: 'insert',
            documentId: document.id
        });
    }

    return collection;
}

async function main() {
    heading('Database Fundamentals: Relational vs Non-Relational');

    const relational = buildRelationalRepository();

    heading('Normalized relational-style representation');

    const order = relational.getOrderDetails('O1000');

    console.log(
        `Customer: ${order.customer.name}`
    );

    console.log(
        `Items: ${order.items.length}`
    );

    console.log(
        `Total: $${(order.totalCents / 100).toFixed(2)}`
    );

    console.log(
        'Customer, order, product, and order-item information is stored '
        + 'separately and combined through explicit relationships.'
    );

    try {
        relational.addOrder({
            id: 'O1001',
            customerId: 'UNKNOWN',
            status: 'paid',
            createdAt: new Date().toISOString()
        });
    } catch (error) {
        console.log(`Referential-integrity failure: ${error.message}`);
    }

    heading('Document-oriented representation');

    const eventBus = new DatabaseActivityBus();

    const temporaryDirectory = await fs.mkdtemp(
        path.join(os.tmpdir(), 'database-fundamentals-')
    );

    const eventFile = path.join(temporaryDirectory, 'events.jsonl');

    const persistence = new DocumentPersistence(eventFile, eventBus);
    const documents = await buildDocumentCollection(eventBus);

    const electronics = documents.findByCategory('electronics');

    for (const document of electronics) {
        console.log(
            `${document.sku}: ${document.name}, `
            + `attributes=${JSON.stringify(document.attributes)}`
        );
    }

    await new Promise(resolve => setTimeout(resolve, 20));

    documents.updateAttribute('P100', 'switchType', 'linear');

    console.log(
        'Changed P100.switchType to:',
        documents.get('P100').attributes.switchType
    );

    heading('Flexible document shape');

    await documents.insert({
        id: 'P400',
        sku: 'CAM-400',
        name: 'Web Camera',
        category: 'electronics',
        priceCents: 12500,
        attributes: {
            resolution: '4K',
            microphone: {
                noiseReduction: true,
                channels: 2
            },
            supportedModes: ['conference', 'streaming', 'recording']
        },
        regionalMetadata: {
            india: {
                warrantyMonths: 24
            }
        }
    });

    console.log(
        'P400 contains nested fields that do not have to appear in '
        + 'every other product document.'
    );

    heading('Embedded aggregate');

    const orderDocument = {
        id: 'O-DOC-100',
        customer: {
            id: 'C100',
            name: 'Aisha Khan',
            email: 'aisha@example.com'
        },
        shippingAddress: {
            city: 'Lucknow',
            country: 'India',
            postalCode: '226001'
        },
        items: [
            {
                sku: 'KB-100',
                name: 'Mechanical Keyboard',
                quantity: 1,
                unitPriceCents: 8900
            },
            {
                sku: 'MS-200',
                name: 'Wireless Mouse',
                quantity: 2,
                unitPriceCents: 4200
            }
        ],
        payment: {
            method: 'card',
            currency: 'INR',
            state: 'authorized'
        },
        status: 'paid'
    };

    const documentTotal = orderDocument.items.reduce(
        (sum, item) => sum + item.quantity * item.unitPriceCents,
        0
    );

    console.log(
        `Embedded order total: $${(documentTotal / 100).toFixed(2)}`
    );

    heading('Model-selection implications');

    console.log(
        'Relational model: strong referential integrity, normalized shared '
        + 'entities, joins, and transaction-oriented updates.'
    );

    console.log(
        'Document model: aggregate-oriented retrieval, flexible attributes, '
        + 'and natural embedding of data read together.'
    );

    console.log(
        'Document flexibility shifts part of schema and relationship '
        + 'validation from the database layer into application logic.'
    );

    heading('Asynchronous persistence observation');

    const eventLog = await fs.readFile(eventFile, 'utf8');

    console.log(
        `Document change events persisted: `
        + `${eventLog.trim().split('\n').filter(Boolean).length}`
    );

    console.log(
        `Event persistence file: ${eventFile}`
    );

    /*
     * Event-driven persistence illustrates a common application pattern:
     * a data operation can emit a domain event while a separate consumer
     * performs audit or integration work asynchronously.
     */
    await persistence.record({
        operation: 'comparison.completed',
        documentId: null
    });

    await fs.rm(temporaryDirectory, {
        recursive: true,
        force: true
    });
}

main().catch(error => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});
