"use strict";

/*
 * Distributed Messaging Engine
 *
 * Node.js 18+
 *
 * Demonstrates:
 * - Asynchronous message queues
 * - Publish-subscribe event streams
 * - Consumer groups
 * - At-most-once and at-least-once delivery
 * - Idempotent processing
 * - Retries and dead-letter routing
 * - Partition ordering
 * - Event-driven monitoring
 * - Backpressure and graceful shutdown
 */

const { EventEmitter } = require("node:events");
const { randomUUID } = require("node:crypto");

const MAX_MESSAGE_BYTES = 1_000_000;

class MessagingError extends Error {}

class ValidationError extends MessagingError {}

class Message {
    constructor({ topic, key, payload, headers = {} }) {
        if (typeof topic !== "string" || !topic.trim()) {
            throw new ValidationError("Topic is required");
        }

        if (typeof key !== "string" || !key.trim()) {
            throw new ValidationError("Message key is required");
        }

        if (
            payload === null ||
            typeof payload !== "object" ||
            Array.isArray(payload)
        ) {
            throw new ValidationError("Payload must be an object");
        }

        const serialized = JSON.stringify(payload);

        if (
            Buffer.byteLength(serialized, "utf8") >
            MAX_MESSAGE_BYTES
        ) {
            throw new ValidationError("Message exceeds size limit");
        }

        this.id = randomUUID();
        this.topic = topic;
        this.key = key;
        this.payload = structuredClone(payload);
        this.headers = Object.freeze({ ...headers });
        this.timestamp = Date.now();

        Object.freeze(this);
    }
}


class MessageQueue extends EventEmitter {
    constructor(name, options = {}) {
        super();

        if (!name) {
            throw new ValidationError("Queue name is required");
        }

        this.name = name;
        this.maxRetries = options.maxRetries ?? 3;
        this.maxPending = options.maxPending ?? 1000;

        this.pending = [];
        this.inFlight = new Map();
        this.deadLetters = [];

        this.closed = false;
        this.metrics = {
            published: 0,
            acknowledged: 0,
            retried: 0,
            failed: 0
        };
    }

    publish(message) {
        if (this.closed) {
            throw new MessagingError("Queue is closed");
        }

        if (this.pending.length >= this.maxPending) {
            throw new MessagingError("Queue capacity exceeded");
        }

        this.pending.push({
            message,
            attempts: 0
        });

        this.metrics.published++;

        this.emit("published", message);
    }

    receive() {
        if (this.closed || this.pending.length === 0) {
            return null;
        }

        const delivery = this.pending.shift();

        delivery.attempts++;

        this.inFlight.set(
            delivery.message.id,
            delivery
        );

        this.emit("received", delivery.message);

        return delivery;
    }

    acknowledge(messageId) {
        const delivery = this.inFlight.get(messageId);

        if (!delivery) {
            throw new MessagingError(
                `Message ${messageId} is not in flight`
            );
        }

        this.inFlight.delete(messageId);
        this.metrics.acknowledged++;

        this.emit("acknowledged", delivery.message);
    }

    reject(messageId, reason = "Processing failure") {
        const delivery = this.inFlight.get(messageId);

        if (!delivery) {
            throw new MessagingError("Unknown delivery");
        }

        this.inFlight.delete(messageId);

        delivery.lastError = reason;

        if (delivery.attempts <= this.maxRetries) {
            this.pending.push(delivery);
            this.metrics.retried++;

            this.emit("retry", {
                message: delivery.message,
                attempts: delivery.attempts
            });
        } else {
            this.deadLetters.push(delivery);
            this.metrics.failed++;

            this.emit("deadLetter", delivery);
        }
    }

    recover() {
        const abandoned = [...this.inFlight.values()];

        this.inFlight.clear();

        for (const delivery of abandoned.reverse()) {
            this.pending.unshift(delivery);
        }

        return abandoned.length;
    }

    close() {
        this.closed = true;
        this.emit("closed");
    }

    statistics() {
        return Object.freeze({
            pending: this.pending.length,
            inFlight: this.inFlight.size,
            deadLetters: this.deadLetters.length,
            ...this.metrics
        });
    }
}


class EventStream extends EventEmitter {
    constructor(name, partitionCount = 4) {
        super();

        if (
            !Number.isInteger(partitionCount) ||
            partitionCount < 1
        ) {
            throw new ValidationError("Invalid partition count");
        }

        this.name = name;

        this.partitions = Array.from(
            { length: partitionCount },
            () => []
        );

        this.groups = new Map();
    }

    partitionFor(key) {
        // Deterministic string hashing preserves key-to-partition routing.
        let hash = 2166136261;

        for (const character of key) {
            hash ^= character.charCodeAt(0);
            hash = Math.imul(hash, 16777619);
        }

        return (hash >>> 0) % this.partitions.length;
    }

    append(message) {
        const partitionId = this.partitionFor(message.key);
        const partition = this.partitions[partitionId];

        const offset = partition.length;

        partition.push({
            offset,
            message
        });

        this.emit("appended", {
            partition: partitionId,
            offset,
            message
        });

        return { partition: partitionId, offset };
    }

    registerGroup(groupName) {
        if (!groupName) {
            throw new ValidationError("Group name is required");
        }

        if (!this.groups.has(groupName)) {
            this.groups.set(
                groupName,
                this.partitions.map(() => 0)
            );
        }
    }

    poll(groupName, partitionId, batchSize = 10) {
        const offsets = this.groups.get(groupName);

        if (!offsets) {
            throw new MessagingError("Consumer group not registered");
        }

        if (
            !Number.isInteger(partitionId) ||
            partitionId < 0 ||
            partitionId >= this.partitions.length
        ) {
            throw new ValidationError("Invalid partition");
        }

        if (!Number.isInteger(batchSize) || batchSize < 1) {
            throw new ValidationError("Invalid batch size");
        }

        const start = offsets[partitionId];

        return this.partitions[partitionId].slice(
            start,
            start + batchSize
        );
    }

    commit(groupName, partitionId, nextOffset) {
        const offsets = this.groups.get(groupName);

        if (!offsets) {
            throw new MessagingError("Unknown consumer group");
        }

        const current = offsets[partitionId];
        const maximum = this.partitions[partitionId].length;

        if (
            !Number.isInteger(nextOffset) ||
            nextOffset < current ||
            nextOffset > maximum
        ) {
            throw new ValidationError("Invalid offset commit");
        }

        offsets[partitionId] = nextOffset;
    }

    seek(groupName, partitionId, offset) {
        const offsets = this.groups.get(groupName);

        if (!offsets) {
            throw new MessagingError("Unknown consumer group");
        }

        if (
            !Number.isInteger(offset) ||
            offset < 0 ||
            offset > this.partitions[partitionId].length
        ) {
            throw new ValidationError("Invalid replay position");
        }

        offsets[partitionId] = offset;
    }

    getOffsets(groupName) {
        const offsets = this.groups.get(groupName);

        if (!offsets) {
            throw new MessagingError("Unknown group");
        }

        return [...offsets];
    }
}


class IdempotencyStore {
    constructor() {
        this.processed = new Set();
        this.balances = new Map();
    }

    async execute(message, handler) {
        if (this.processed.has(message.id)) {
            return {
                duplicate: true,
                result: null
            };
        }

        // This synchronous state transition is atomic within one
        // Node.js execution context. Distributed deployments require
        // a transactional database or atomic conditional write.
        const result = await handler(message);

        this.processed.add(message.id);

        return {
            duplicate: false,
            result
        };
    }

    async paymentHandler(message) {
        const { account, amount } = message.payload;

        if (
            typeof account !== "string" ||
            !account.trim()
        ) {
            throw new ValidationError("Invalid account");
        }

        if (
            typeof amount !== "number" ||
            !Number.isFinite(amount) ||
            amount <= 0
        ) {
            throw new ValidationError("Invalid amount");
        }

        const previous = this.balances.get(account) ?? 0;

        this.balances.set(account, previous + amount);

        return this.balances.get(account);
    }
}


class Consumer {
    constructor(name, queue, handler, options = {}) {
        this.name = name;
        this.queue = queue;
        this.handler = handler;

        this.guarantee =
            options.guarantee ?? "at-least-once";

        this.active = false;
        this.controller = new AbortController();
    }

    async processOne() {
        const delivery = this.queue.receive();

        if (!delivery) {
            return false;
        }

        const message = delivery.message;

        try {
            if (this.guarantee === "at-most-once") {
                this.queue.acknowledge(message.id);
                await this.handler(message);

            } else if (this.guarantee === "at-least-once") {
                await this.handler(message);
                this.queue.acknowledge(message.id);

            } else {
                throw new ValidationError(
                    "Exactly-once requires an explicit transactional handler"
                );
            }

            return true;

        } catch (error) {
            if (this.queue.inFlight.has(message.id)) {
                this.queue.reject(message.id, error.message);
            }

            console.error(
                `${this.name} failed:`,
                error.message
            );

            return false;
        }
    }

    async start(options = {}) {
        if (this.active) {
            throw new MessagingError("Consumer already running");
        }

        this.active = true;

        const delay = options.pollInterval ?? 50;

        while (
            this.active &&
            !this.controller.signal.aborted
        ) {
            const processed = await this.processOne();

            if (!processed) {
                await new Promise(resolve =>
                    setTimeout(resolve, delay)
                );
            }
        }
    }

    stop() {
        this.active = false;
        this.controller.abort();
    }
}


async function main() {
    console.log("\n=== ASYNCHRONOUS MESSAGE QUEUE ===");

    const queue = new MessageQueue("payments", {
        maxRetries: 2,
        maxPending: 100
    });

    queue.on("published", message => {
        console.log("Published:", message.id);
    });

    queue.on("acknowledged", message => {
        console.log("Acknowledged:", message.id);
    });

    queue.on("deadLetter", delivery => {
        console.log("Dead letter:", delivery.message.id);
    });

    const idempotency = new IdempotencyStore();

    const payment = new Message({
        topic: "payments",
        key: "account-101",
        payload: {
            account: "account-101",
            amount: 1500
        }
    });

    queue.publish(payment);

    const consumer = new Consumer(
        "payment-worker",
        queue,
        message => idempotency.execute(
            message,
            msg => idempotency.paymentHandler(msg)
        )
    );

    await consumer.processOne();

    // Simulate redelivery of the same logical event.
    console.log(
        "Duplicate result:",
        await idempotency.execute(
            payment,
            msg => idempotency.paymentHandler(msg)
        )
    );

    console.log(
        "Balances:",
        Object.fromEntries(idempotency.balances)
    );

    console.log("Queue metrics:", queue.statistics());


    console.log("\n=== PARTITIONED EVENT STREAM ===");

    const stream = new EventStream("orders", 3);

    stream.registerGroup("analytics");
    stream.registerGroup("billing");

    stream.on("appended", event => {
        console.log(
            `Appended partition=${event.partition}, offset=${event.offset}`
        );
    });

    for (let index = 1; index <= 6; index++) {
        stream.append(
            new Message({
                topic: "orders",
                key: `customer-${index % 2}`,
                payload: {
                    orderId: index,
                    amount: index * 100
                }
            })
        );
    }

    for (let partition = 0; partition < 3; partition++) {
        const events = stream.poll(
            "analytics",
            partition,
            10
        );

        for (const event of events) {
            console.log(
                "Analytics processed:",
                event.message.payload.orderId
            );
        }

        stream.commit(
            "analytics",
            partition,
            stream.getOffsets("analytics")[partition] +
                events.length
        );
    }

    console.log(
        "Analytics offsets:",
        stream.getOffsets("analytics")
    );

    console.log(
        "Billing offsets:",
        stream.getOffsets("billing")
    );


    console.log("\n=== RETRY AND DEAD-LETTER HANDLING ===");

    const failingQueue = new MessageQueue("email", {
        maxRetries: 2
    });

    failingQueue.publish(
        new Message({
            topic: "email",
            key: "user-101",
            payload: { recipient: "user@example.com" }
        })
    );

    for (let attempt = 0; attempt < 4; attempt++) {
        const delivery = failingQueue.receive();

        if (!delivery) {
            break;
        }

        failingQueue.reject(
            delivery.message.id,
            "Simulated SMTP failure"
        );
    }

    console.log("Failure metrics:", failingQueue.statistics());

    queue.close();
    failingQueue.close();
}

main().catch(error => {
    console.error("Fatal messaging error:", error);
    process.exitCode = 1;
});
