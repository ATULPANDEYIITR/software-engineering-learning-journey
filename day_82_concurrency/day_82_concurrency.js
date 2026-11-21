"use strict";

/*
 * CONCURRENCY, RACE CONDITIONS, LOCKS, AND SYNCHRONIZATION
 *
 * Node.js implementation emphasizing:
 * - Event-loop concurrency
 * - Asynchronous race conditions
 * - Promise-based mutexes
 * - Semaphore-based resource limits
 * - Read/write synchronization
 * - Optimistic concurrency
 * - Cancellation and timeouts
 * - Event-driven task processing
 * - Atomic state transitions
 *
 * Run: node concurrency.js
 */

const { EventEmitter } = require("node:events");
const { randomInt } = require("node:crypto");


class ValidationError extends Error {}
class LockTimeoutError extends Error {}
class ConcurrencyConflictError extends Error {}


/* -------------------------------------------------------
   1. ASYNCHRONOUS RACE CONDITION
------------------------------------------------------- */

class UnsafeBalance {
    constructor(initialBalance) {
        if (!Number.isSafeInteger(initialBalance) || initialBalance < 0) {
            throw new ValidationError("Invalid initial balance");
        }

        this.balance = initialBalance;
    }

    async withdraw(amount) {
        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError("Invalid withdrawal");
        }

        const observed = this.balance;

        // Represents asynchronous external processing.
        await new Promise(resolve => setImmediate(resolve));

        if (observed < amount) {
            return false;
        }

        this.balance = observed - amount;
        return true;
    }
}


async function demonstrateAsyncRace() {
    const account = new UnsafeBalance(100);

    const results = await Promise.all([
        account.withdraw(80),
        account.withdraw(80)
    ]);

    console.log("\n1. Asynchronous race condition");
    console.log("Withdrawal results:", results);
    console.log("Final balance:", account.balance);
    console.log("Both operations may observe the same initial balance.");
}


/* -------------------------------------------------------
   2. FIFO ASYNCHRONOUS MUTEX
------------------------------------------------------- */

class AsyncMutex {
    constructor() {
        this.locked = false;
        this.waiters = [];
    }

    acquire({ timeoutMs = 0, signal } = {}) {
        if (signal?.aborted) {
            return Promise.reject(
                signal.reason || new Error("Operation aborted")
            );
        }

        return new Promise((resolve, reject) => {
            const waiter = {
                resolve,
                reject,
                timer: null,
                signal,
                abortHandler: null,
                active: true
            };

            const removeWaiter = () => {
                if (!waiter.active) return;

                waiter.active = false;

                const index = this.waiters.indexOf(waiter);

                if (index >= 0) {
                    this.waiters.splice(index, 1);
                }

                if (waiter.timer) {
                    clearTimeout(waiter.timer);
                }

                if (signal && waiter.abortHandler) {
                    signal.removeEventListener(
                        "abort",
                        waiter.abortHandler
                    );
                }
            };

            waiter.remove = removeWaiter;

            if (timeoutMs > 0) {
                waiter.timer = setTimeout(() => {
                    removeWaiter();
                    reject(new LockTimeoutError("Mutex acquisition timed out"));
                }, timeoutMs);
            }

            if (signal) {
                waiter.abortHandler = () => {
                    removeWaiter();
                    reject(
                        signal.reason || new Error("Operation aborted")
                    );
                };

                signal.addEventListener(
                    "abort",
                    waiter.abortHandler,
                    { once: true }
                );
            }

            if (!this.locked) {
                this.locked = true;
                this.grant(waiter);
            } else {
                this.waiters.push(waiter);
            }
        });
    }

    grant(waiter) {
        if (!waiter.active) {
            this.release();
            return;
        }

        waiter.active = false;

        if (waiter.timer) {
            clearTimeout(waiter.timer);
        }

        if (waiter.signal && waiter.abortHandler) {
            waiter.signal.removeEventListener(
                "abort",
                waiter.abortHandler
            );
        }

        let released = false;

        waiter.resolve(() => {
            if (released) {
                throw new Error("Mutex released more than once");
            }

            released = true;
            this.release();
        });
    }

    release() {
        while (this.waiters.length > 0) {
            const next = this.waiters.shift();

            if (next.active) {
                this.grant(next);
                return;
            }
        }

        this.locked = false;
    }

    async runExclusive(operation, options = {}) {
        const release = await this.acquire(options);

        try {
            return await operation();
        } finally {
            release();
        }
    }
}


/* -------------------------------------------------------
   3. THREAD-SAFE LOGICAL BANKING SERVICE
------------------------------------------------------- */

class BankingService {
    constructor() {
        this.accounts = new Map([
            ["A001", { balance: 10000, version: 0 }],
            ["A002", { balance: 10000, version: 0 }]
        ]);

        this.mutex = new AsyncMutex();
    }

    async transfer(sourceId, destinationId, amount) {
        if (sourceId === destinationId) {
            throw new ValidationError("Accounts must differ");
        }

        if (!Number.isSafeInteger(amount) || amount <= 0) {
            throw new ValidationError("Invalid transfer amount");
        }

        return this.mutex.runExclusive(async () => {
            const source = this.accounts.get(sourceId);
            const destination = this.accounts.get(destinationId);

            if (!source || !destination) {
                throw new ValidationError("Unknown account");
            }

            if (source.balance < amount) {
                throw new ValidationError("Insufficient funds");
            }

            // Validate before changing either account.
            const newDestinationBalance = destination.balance + amount;

            if (!Number.isSafeInteger(newDestinationBalance)) {
                throw new ValidationError("Balance overflow");
            }

            source.balance -= amount;
            destination.balance = newDestinationBalance;

            source.version++;
            destination.version++;

            return {
                sourceBalance: source.balance,
                destinationBalance: destination.balance
            };
        });
    }

    async snapshot() {
        return this.mutex.runExclusive(() => {
            return Object.fromEntries(
                [...this.accounts.entries()].map(([id, account]) => [
                    id,
                    { ...account }
                ])
            );
        });
    }
}


/* -------------------------------------------------------
   4. SEMAPHORE
------------------------------------------------------- */

class Semaphore {
    constructor(capacity) {
        if (!Number.isInteger(capacity) || capacity <= 0) {
            throw new ValidationError("Invalid semaphore capacity");
        }

        this.capacity = capacity;
        this.available = capacity;
        this.mutex = new AsyncMutex();
    }

    async acquire() {
        await this.mutex.runExclusive(() => {
            // The permit is acquired in the separate implementation below.
        });

        return new Promise(resolve => {
            const attempt = () => {
                if (this.available > 0) {
                    this.available--;

                    let released = false;

                    resolve(() => {
                        if (released) {
                            throw new Error("Permit already released");
                        }

                        released = true;
                        this.available++;

                        const next = this.waiters?.shift();
                        if (next) next();
                    });
                } else {
                    this.waiters ??= [];
                    this.waiters.push(attempt);
                }
            };

            attempt();
        });
    }

    async run(operation) {
        const release = await this.acquire();

        try {
            return await operation();
        } finally {
            release();
        }
    }
}


/* -------------------------------------------------------
   5. OPTIMISTIC CONCURRENCY
------------------------------------------------------- */

class VersionedDocument {
    constructor(initialData) {
        this.data = Object.freeze({ ...initialData });
        this.version = 0;
    }

    read() {
        return {
            data: { ...this.data },
            version: this.version
        };
    }

    update(expectedVersion, changes) {
        if (expectedVersion !== this.version) {
            throw new ConcurrencyConflictError(
                `Expected ${expectedVersion}, actual ${this.version}`
            );
        }

        if (!changes || typeof changes !== "object" || Array.isArray(changes)) {
            throw new ValidationError("Changes must be an object");
        }

        const updated = {
            ...this.data,
            ...changes
        };

        this.data = Object.freeze(updated);
        this.version++;

        return this.read();
    }
}


/* -------------------------------------------------------
   6. READ-WRITE LOCK
------------------------------------------------------- */

class ReadWriteLock {
    constructor() {
        this.readers = 0;
        this.writer = false;
        this.queue = [];
    }

    acquireRead() {
        return new Promise(resolve => {
            this.queue.push({
                type: "read",
                resolve
            });

            this.process();
        });
    }

    acquireWrite() {
        return new Promise(resolve => {
            this.queue.push({
                type: "write",
                resolve
            });

            this.process();
        });
    }

    process() {
        if (this.writer || this.queue.length === 0) return;

        if (this.queue[0].type === "write") {
            if (this.readers > 0) return;

            const waiter = this.queue.shift();
            this.writer = true;

            let released = false;

            waiter.resolve(() => {
                if (released) throw new Error("Already released");

                released = true;
                this.writer = false;
                this.process();
            });

            return;
        }

        while (
            this.queue.length > 0 &&
            this.queue[0].type === "read" &&
            !this.writer
        ) {
            const waiter = this.queue.shift();

            this.readers++;

            let released = false;

            waiter.resolve(() => {
                if (released) throw new Error("Already released");

                released = true;
                this.readers--;
                this.process();
            });
        }
    }

    async read(operation) {
        const release = await this.acquireRead();

        try {
            return await operation();
        } finally {
            release();
        }
    }

    async write(operation) {
        const release = await this.acquireWrite();

        try {
            return await operation();
        } finally {
            release();
        }
    }
}


/* -------------------------------------------------------
   7. EVENT-DRIVEN TASK PROCESSOR
------------------------------------------------------- */

class TaskProcessor extends EventEmitter {
    constructor(concurrency) {
        super();

        this.semaphore = new Semaphore(concurrency);
        this.completed = 0;
        this.failed = 0;
    }

    async execute(task) {
        if (typeof task !== "function") {
            throw new ValidationError("Task must be a function");
        }

        return this.semaphore.run(async () => {
            this.emit("started");

            try {
                const result = await task();

                this.completed++;
                this.emit("completed", result);

                return result;
            } catch (error) {
                this.failed++;
                this.emit("failed", error);

                throw error;
            }
        });
    }

    statistics() {
        return {
            completed: this.completed,
            failed: this.failed
        };
    }
}


/* -------------------------------------------------------
   8. CONCURRENT INVENTORY
------------------------------------------------------- */

class Inventory {
    constructor(stock) {
        this.stock = new Map(Object.entries(stock));
        this.lock = new AsyncMutex();
    }

    async reserve(product, quantity) {
        if (!Number.isSafeInteger(quantity) || quantity <= 0) {
            throw new ValidationError("Invalid quantity");
        }

        return this.lock.runExclusive(() => {
            if (!this.stock.has(product)) {
                throw new ValidationError("Unknown product");
            }

            const current = this.stock.get(product);

            if (current < quantity) {
                return false;
            }

            this.stock.set(product, current - quantity);

            return true;
        });
    }

    async snapshot() {
        return this.lock.runExclusive(() => {
            return Object.fromEntries(this.stock);
        });
    }
}


/* -------------------------------------------------------
   9. EXECUTABLE VALIDATION
------------------------------------------------------- */

async function main() {
    console.log("CONCURRENCY ENGINEERING LABORATORY");

    await demonstrateAsyncRace();

    const banking = new BankingService();

    await Promise.all(
        Array.from({ length: 100 }, (_, index) => {
            return index % 2 === 0
                ? banking.transfer("A001", "A002", 10)
                : banking.transfer("A002", "A001", 10);
        })
    );

    const bankState = await banking.snapshot();

    const total =
        bankState.A001.balance + bankState.A002.balance;

    if (total !== 20000) {
        throw new Error("Banking invariant violated");
    }

    console.log("\n2. Mutex-protected banking");
    console.log(bankState);

    const semaphore = new Semaphore(3);
    let active = 0;
    let maximumActive = 0;

    await Promise.all(
        Array.from({ length: 20 }, () =>
            semaphore.run(async () => {
                active++;
                maximumActive = Math.max(maximumActive, active);

                await new Promise(resolve =>
                    setTimeout(resolve, randomInt(5, 20))
                );

                active--;
            })
        )
    );

    if (maximumActive > 3) {
        throw new Error("Semaphore capacity violated");
    }

    console.log("\n3. Semaphore");
    console.log("Maximum simultaneous tasks:", maximumActive);

    const document = new VersionedDocument({
        title: "Concurrency",
        status: "draft"
    });

    const firstRead = document.read();

    document.update(firstRead.version, {
        status: "reviewed"
    });

    try {
        document.update(firstRead.version, {
            status: "published"
        });
    } catch (error) {
        console.log("\n4. Optimistic concurrency conflict:", error.message);
    }

    const rwLock = new ReadWriteLock();
    let sharedValue = 0;

    await Promise.all([
        rwLock.write(async () => {
            sharedValue = 100;
        }),
        rwLock.read(async () => sharedValue),
        rwLock.read(async () => sharedValue)
    ]);

    console.log("\n5. Read-write synchronization:", sharedValue);

    const inventory = new Inventory({
        LAPTOP: 20,
        MOUSE: 50
    });

    const reservations = await Promise.all(
        Array.from(
            { length: 100 },
            () => inventory.reserve("MOUSE", 1)
        )
    );

    const successful = reservations.filter(Boolean).length;
    const inventoryState = await inventory.snapshot();

    if (successful !== 50 || inventoryState.MOUSE !== 0) {
        throw new Error("Inventory invariant violated");
    }

    console.log("\n6. Inventory reservations");
    console.log("Successful reservations:", successful);
    console.log(inventoryState);

    const processor = new TaskProcessor(2);

    processor.on("completed", result => {
        console.log("Task completed:", result);
    });

    processor.on("failed", error => {
        console.log("Task failed:", error.message);
    });

    await Promise.allSettled([
        processor.execute(async () => "Task A"),
        processor.execute(async () => "Task B"),
        processor.execute(async () => {
            throw new Error("Simulated processing failure");
        })
    ]);

    console.log("\n7. Event-driven processing");
    console.log(processor.statistics());

    console.log("\nAll concurrency checks completed.");
}


main().catch(error => {
    console.error("Fatal execution error:", error);
    process.exitCode = 1;
});
