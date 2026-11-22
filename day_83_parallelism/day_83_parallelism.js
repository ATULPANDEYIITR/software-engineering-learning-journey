"use strict";

/**
 * Parallelism: Multithreading and Multiprocessing
 *
 * Runtime: Node.js 18+
 *
 * Demonstrates:
 * - Event-loop concurrency
 * - Promise-based asynchronous operations
 * - Bounded asynchronous task execution
 * - Worker threads for CPU-bound work
 * - SharedArrayBuffer and Atomics
 * - Message-based worker communication
 * - Failure isolation and cancellation
 * - Performance measurement
 */

const {
    Worker,
    isMainThread,
    parentPort,
    workerData
} = require("node:worker_threads");

const os = require("node:os");
const { performance } = require("node:perf_hooks");
const { setTimeout: sleep } = require("node:timers/promises");


const CONFIG = Object.freeze({
    maxWorkers: Math.max(1, os.availableParallelism
        ? os.availableParallelism()
        : os.cpus().length),
    defaultConcurrency: 4,
    maximumTasks: 100
});


// --------------------------------------------------
// 1. Validation
// --------------------------------------------------

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

function validateTasks(tasks) {
    if (!Array.isArray(tasks)) {
        throw new ValidationError("Tasks must be an array.");
    }

    if (tasks.length > CONFIG.maximumTasks) {
        throw new ValidationError("Task limit exceeded.");
    }

    for (const task of tasks) {
        if (
            !Number.isSafeInteger(task.id) ||
            task.id < 0 ||
            !Number.isSafeInteger(task.limit) ||
            task.limit < 0
        ) {
            throw new ValidationError(
                "Each task requires a non-negative safe integer ID and limit."
            );
        }
    }

    const identifiers = new Set(tasks.map(task => task.id));

    if (identifiers.size !== tasks.length) {
        throw new ValidationError("Duplicate task identifiers.");
    }
}


// --------------------------------------------------
// 2. CPU-bound computation
// --------------------------------------------------

function isPrime(number) {
    if (number < 2) return false;
    if (number <= 3) return true;

    if (number % 2 === 0 || number % 3 === 0) {
        return false;
    }

    for (
        let divisor = 5;
        divisor * divisor <= number;
        divisor += 6
    ) {
        if (
            number % divisor === 0 ||
            number % (divisor + 2) === 0
        ) {
            return false;
        }
    }

    return true;
}

function countPrimes(limit) {
    let count = 0;

    for (let number = 2; number <= limit; number++) {
        if (isPrime(number)) {
            count++;
        }
    }

    return count;
}


// --------------------------------------------------
// 3. Event-loop concurrency
// --------------------------------------------------

async function simulateNetworkRequest(task) {
    const delay = 40 + (task.id % 4) * 20;

    await sleep(delay);

    return {
        id: task.id,
        response: `response-${task.id}`,
        duration: delay
    };
}


// --------------------------------------------------
// 4. Bounded Promise execution
// --------------------------------------------------

async function executeWithConcurrency(
    tasks,
    operation,
    concurrency = CONFIG.defaultConcurrency
) {
    validateTasks(tasks);

    if (!Number.isInteger(concurrency) || concurrency < 1) {
        throw new ValidationError(
            "Concurrency must be a positive integer."
        );
    }

    const results = new Array(tasks.length);
    const failures = [];

    let nextIndex = 0;

    async function worker() {
        while (true) {
            const index = nextIndex++;

            if (index >= tasks.length) {
                return;
            }

            try {
                results[index] = await operation(tasks[index]);
            } catch (error) {
                failures.push({
                    taskId: tasks[index].id,
                    message: error.message
                });
            }
        }
    }

    const workerCount = Math.min(concurrency, tasks.length);

    await Promise.all(
        Array.from(
            { length: workerCount },
            () => worker()
        )
    );

    return {
        results: results.filter(Boolean),
        failures
    };
}


// --------------------------------------------------
// 5. Worker-thread execution
// --------------------------------------------------

const WORKER_SOURCE = `
"use strict";

const { parentPort, workerData } =
    require("node:worker_threads");

function isPrime(number) {
    if (number < 2) return false;
    if (number <= 3) return true;

    if (number % 2 === 0 || number % 3 === 0) {
        return false;
    }

    for (
        let divisor = 5;
        divisor * divisor <= number;
        divisor += 6
    ) {
        if (
            number % divisor === 0 ||
            number % (divisor + 2) === 0
        ) {
            return false;
        }
    }

    return true;
}

function countPrimes(limit) {
    let count = 0;

    for (let number = 2; number <= limit; number++) {
        if (isPrime(number)) count++;
    }

    return count;
}

try {
    const result = workerData.tasks.map(task => ({
        id: task.id,
        count: countPrimes(task.limit)
    }));

    parentPort.postMessage({
        success: true,
        results: result
    });

} catch (error) {
    parentPort.postMessage({
        success: false,
        error: error.message
    });
}
`;


function executeWorkerBatch(tasks) {
    return new Promise((resolve, reject) => {
        const worker = new Worker(WORKER_SOURCE, {
            eval: true,
            workerData: { tasks }
        });

        let settled = false;

        function finish(callback, value) {
            if (settled) return;

            settled = true;
            callback(value);
        }

        worker.once("message", message => {
            if (message.success) {
                finish(resolve, message.results);
            } else {
                finish(
                    reject,
                    new Error(message.error)
                );
            }
        });

        worker.once("error", error => {
            finish(reject, error);
        });

        worker.once("exit", code => {
            if (code !== 0) {
                finish(
                    reject,
                    new Error(`Worker exited with code ${code}`)
                );
            }
        });
    });
}


async function executeWithWorkers(tasks, workerCount) {
    validateTasks(tasks);

    if (
        !Number.isInteger(workerCount) ||
        workerCount < 1 ||
        workerCount > CONFIG.maxWorkers
    ) {
        throw new ValidationError(
            `Worker count must be between 1 and ${CONFIG.maxWorkers}.`
        );
    }

    if (tasks.length === 0) {
        return [];
    }

    const batchCount = Math.min(workerCount, tasks.length);

    const batches = Array.from(
        { length: batchCount },
        () => []
    );

    // Distribute work using round-robin scheduling.
    tasks.forEach((task, index) => {
        batches[index % batchCount].push(task);
    });

    const batchResults = await Promise.all(
        batches.map(executeWorkerBatch)
    );

    return batchResults
        .flat()
        .sort((a, b) => a.id - b.id);
}


// --------------------------------------------------
// 6. Shared memory and atomic operations
// --------------------------------------------------

async function demonstrateSharedMemory() {
    const sharedBuffer = new SharedArrayBuffer(
        Int32Array.BYTES_PER_ELEMENT
    );

    const sharedCounter = new Int32Array(sharedBuffer);

    const workerCode = `
        const { parentPort, workerData } =
            require("node:worker_threads");

        const counter = new Int32Array(workerData.buffer);

        for (let i = 0; i < workerData.iterations; i++) {
            Atomics.add(counter, 0, 1);
        }

        parentPort.postMessage("completed");
    `;

    const workers = Array.from(
        { length: 4 },
        () => new Worker(workerCode, {
            eval: true,
            workerData: {
                buffer: sharedBuffer,
                iterations: 10000
            }
        })
    );

    await Promise.all(
        workers.map(worker => new Promise((resolve, reject) => {
            worker.once("message", resolve);
            worker.once("error", reject);

            worker.once("exit", code => {
                if (code !== 0) {
                    reject(
                        new Error(`Shared-memory worker exited: ${code}`)
                    );
                }
            });
        }))
    );

    return Atomics.load(sharedCounter, 0);
}


// --------------------------------------------------
// 7. Performance measurement
// --------------------------------------------------

async function benchmark(name, operation) {
    const start = performance.now();

    const result = await operation();

    const elapsed = performance.now() - start;

    return {
        name,
        elapsedMs: Number(elapsed.toFixed(3)),
        result
    };
}


// --------------------------------------------------
// 8. Main application
// --------------------------------------------------

async function main() {
    console.log("PARALLELISM ENGINEERING LAB");
    console.log(`Logical CPU cores: ${CONFIG.maxWorkers}`);

    const tasks = [
        { id: 1, limit: 50000 },
        { id: 2, limit: 55000 },
        { id: 3, limit: 60000 },
        { id: 4, limit: 65000 },
        { id: 5, limit: 70000 },
        { id: 6, limit: 75000 }
    ];

    validateTasks(tasks);

    // Sequential CPU execution.
    const sequential = await benchmark(
        "Sequential CPU",
        async () => tasks.map(task => ({
            id: task.id,
            count: countPrimes(task.limit)
        }))
    );

    // CPU work distributed to worker threads.
    const parallel = await benchmark(
        "Worker threads",
        () => executeWithWorkers(
            tasks,
            Math.min(4, CONFIG.maxWorkers)
        )
    );

    // I/O operations use asynchronous event-loop concurrency.
    const asynchronous = await benchmark(
        "Asynchronous I/O",
        () => executeWithConcurrency(
            tasks,
            simulateNetworkRequest,
            4
        )
    );

    console.log("\nBENCHMARK RESULTS");

    for (const result of [
        sequential,
        parallel,
        asynchronous
    ]) {
        console.log(
            `${result.name}: ${result.elapsedMs} ms`
        );
    }

    const normalizedParallel = parallel.result.map(item => ({
        id: item.id,
        count: item.count
    }));

    const normalizedSequential = sequential.result;

    if (
        JSON.stringify(normalizedParallel) !==
        JSON.stringify(normalizedSequential)
    ) {
        throw new Error("Parallel result validation failed.");
    }

    console.log("\nAll CPU results match.");

    const sharedCount = await demonstrateSharedMemory();

    console.log(`Atomic shared counter: ${sharedCount}`);

    if (sharedCount !== 40000) {
        throw new Error("Shared-memory synchronization failed.");
    }

    // Demonstrate task-level failure isolation.
    const failureResult = await executeWithConcurrency(
        [
            { id: 10, limit: 0 },
            { id: 11, limit: 10 }
        ],
        async task => {
            if (task.limit === 0) {
                throw new Error("Invalid workload.");
            }

            return task.id;
        },
        2
    );

    console.log("\nFAILURE ISOLATION");
    console.log(failureResult);

    if (failureResult.failures.length !== 1) {
        throw new Error("Failure isolation test failed.");
    }

    console.log("\nAll validation checks passed.");
}


// --------------------------------------------------
// 9. Runtime entry point
// --------------------------------------------------

if (isMainThread) {
    main().catch(error => {
        console.error("Application failure:", error);
        process.exitCode = 1;
    });
}
