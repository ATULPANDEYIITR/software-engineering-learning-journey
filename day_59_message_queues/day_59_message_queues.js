'use strict';

const crypto = require('node:crypto');
const { EventEmitter } = require('node:events');

const MessageState = Object.freeze({
  READY: 'ready',
  PROCESSING: 'processing',
  ACKNOWLEDGED: 'acknowledged',
  FAILED: 'failed',
  DEAD_LETTERED: 'dead_lettered'
});

class Message {
  constructor(topic, payload, options = {}) {
    if (typeof topic !== 'string' || topic.trim() === '') {
      throw new TypeError('Message topic cannot be empty');
    }
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new TypeError('Message payload must be an object');
    }

    this.id = options.id || crypto.randomUUID();
    this.topic = topic;
    this.payload = Object.freeze({ ...payload });
    this.attempts = 0;
    this.state = MessageState.READY;
    this.createdAt = Date.now();
    this.availableAt = 0;
  }
}

class AsyncMessageQueue extends EventEmitter {
  constructor(name, { maxSize = 100, maxAttempts = 3 } = {}) {
    super();

    if (maxSize <= 0 || maxAttempts <= 0) {
      throw new RangeError('Queue limits must be positive');
    }

    this.name = name;
    this.maxSize = maxSize;
    this.maxAttempts = maxAttempts;
    this.messages = [];
    this.deadLetters = [];
    this.stats = {
      published: 0,
      acknowledged: 0,
      failed: 0
    };
  }

  publish(message) {
    if (!(message instanceof Message)) {
      throw new TypeError('publish requires a Message');
    }

    if (this.messages.length >= this.maxSize) {
      throw new Error(`Queue ${this.name} is full`);
    }

    this.messages.push(message);
    this.stats.published += 1;
    this.emit('published', message);
    return message.id;
  }

  async consume() {
    const now = Date.now();

    const index = this.messages.findIndex(
      message =>
        message.state === MessageState.READY &&
        message.availableAt <= now
    );

    if (index === -1) {
      return null;
    }

    const [message] = this.messages.splice(index, 1);
    message.state = MessageState.PROCESSING;
    message.attempts += 1;
    this.emit('consumed', message);
    return message;
  }

  acknowledge(message) {
    if (message.state !== MessageState.PROCESSING) {
      throw new Error('Only processing messages can be acknowledged');
    }

    message.state = MessageState.ACKNOWLEDGED;
    this.stats.acknowledged += 1;
    this.emit('acknowledged', message);
  }

  reject(message, delayMs = 50) {
    if (message.state !== MessageState.PROCESSING) {
      throw new Error('Only processing messages can be rejected');
    }

    this.stats.failed += 1;

    if (message.attempts >= this.maxAttempts) {
      message.state = MessageState.DEAD_LETTERED;
      this.deadLetters.push(message);
      this.emit('deadLettered', message);
      return;
    }

    message.state = MessageState.READY;
    message.availableAt = Date.now() + Math.max(0, delayMs);
    this.messages.push(message);
    this.emit('retryScheduled', message);
  }
}

class Worker {
  constructor(name, queue, handler) {
    this.name = name;
    this.queue = queue;
    this.handler = handler;
    this.running = false;
  }

  async runUntilIdle() {
    this.running = true;

    while (this.running) {
      const message = await this.queue.consume();

      if (!message) {
        if (this.queue.messages.length === 0) {
          break;
        }
        await new Promise(resolve => setTimeout(resolve, 60));
        continue;
      }

      try {
        await this.handler(message);
        this.queue.acknowledge(message);
      } catch (error) {
        console.error(
          `[${this.name}] message=${message.id} error=${error.message}`
        );
        this.queue.reject(message);
      }
    }

    this.running = false;
  }

  stop() {
    this.running = false;
  }
}

async function processOrder(message) {
  const { orderId, amount } = message.payload;

  if (!/^ORD-[0-9]+$/.test(orderId)) {
    throw new Error('Invalid order ID');
  }

  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error('Order amount must be positive');
  }

  // A production consumer should persist an idempotency key before
  // performing a non-repeatable external side effect.
  await new Promise(resolve => setTimeout(resolve, 10));
  console.log(`processed order=${orderId} amount=${amount.toFixed(2)}`);
}

async function processNotification(message) {
  if (message.payload.failAlways === true) {
    throw new Error('Notification provider unavailable');
  }

  console.log(`notification sent id=${message.id}`);
}

async function main() {
  const orderQueue = new AsyncMessageQueue('orders', {
    maxSize: 20,
    maxAttempts: 3
  });

  orderQueue.on('deadLettered', message => {
    console.error(`dead-lettered message=${message.id}`);
  });

  orderQueue.on('retryScheduled', message => {
    console.log(
      `retry scheduled message=${message.id} attempt=${message.attempts}`
    );
  });

  orderQueue.publish(
    new Message('orders.created', {
      orderId: 'ORD-1001',
      amount: 425.75
    })
  );

  orderQueue.publish(
    new Message('orders.created', {
      orderId: 'ORD-1002',
      amount: 89.99
    })
  );

  const orderWorker = new Worker(
    'order-worker',
    orderQueue,
    processOrder
  );

  await orderWorker.runUntilIdle();

  const notificationQueue = new AsyncMessageQueue('notifications', {
    maxSize: 10,
    maxAttempts: 3
  });

  notificationQueue.publish(
    new Message('notification.send', {
      userId: 'USR-42',
      failAlways: true
    })
  );

  const notificationWorker = new Worker(
    'notification-worker',
    notificationQueue,
    processNotification
  );

  await notificationWorker.runUntilIdle();

  console.log(JSON.stringify({
    orderQueue: orderQueue.stats,
    notificationQueue: {
      ...notificationQueue.stats,
      deadLetters: notificationQueue.deadLetters.length
    }
  }, null, 2));

  // Security rule: payloads are treated as data, not executable content.
  // Production transports should also authenticate producers and consumers,
  // encrypt traffic, restrict queue permissions, and cap payload size.
}

main().catch(error => {
  console.error(`fatal_error=${error.message}`);
  process.exitCode = 1;
});
