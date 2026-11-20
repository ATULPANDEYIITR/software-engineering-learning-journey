"use strict";

/*
 * Operating Systems: Event-Driven Resource Management Simulator.
 *
 * Demonstrates:
 * - Asynchronous process execution.
 * - Event-driven process lifecycle.
 * - Thread scheduling and time slicing.
 * - Promise-based synchronization.
 * - Memory allocation and fragmentation.
 * - Page replacement using FIFO.
 * - Filesystem operations and access control.
 * - Resource exhaustion and recovery.
 *
 * Runtime: Node.js 18+
 * Execute: node operating_systems.js
 */

const { EventEmitter } = require("node:events");
const { performance } = require("node:perf_hooks");
const path = require("node:path");

class OperatingSystemError extends Error {}
class ResourceExhaustionError extends OperatingSystemError {}
class InvalidTransitionError extends OperatingSystemError {}
class AccessDeniedError extends OperatingSystemError {}

const ProcessState = Object.freeze({
    NEW: "NEW",
    READY: "READY",
    RUNNING: "RUNNING",
    BLOCKED: "BLOCKED",
    TERMINATED: "TERMINATED"
});

const ThreadState = Object.freeze({
    READY: "READY",
    RUNNING: "RUNNING",
    BLOCKED: "BLOCKED",
    TERMINATED: "TERMINATED"
});

class Kernel extends EventEmitter {
    constructor({ memoryCapacity, quantum }) {
        super();

        if (!Number.isSafeInteger(memoryCapacity) || memoryCapacity <= 0) {
            throw new RangeError("Invalid memory capacity");
        }

        if (!Number.isSafeInteger(quantum) || quantum <= 0) {
            throw new RangeError("Invalid scheduling quantum");
        }

        this.memoryCapacity = memoryCapacity;
        this.availableMemory = memoryCapacity;
        this.quantum = quantum;

        this.processes = new Map();
        this.nextPid = 1000;
        this.nextTid = 1;
        this.clock = 0;
        this.readyQueue = [];
    }

    createProcess(name, memory) {
        if (typeof name !== "string" || !name.trim()) {
            throw new TypeError("Process name is required");
        }

        if (!Number.isSafeInteger(memory) || memory <= 0) {
            throw new RangeError("Memory allocation must be positive");
        }

        if (memory > this.availableMemory) {
            throw new ResourceExhaustionError(
                "Insufficient memory for process"
            );
        }

        const process = {
            pid: this.nextPid++,
            name,
            state: ProcessState.READY,
            memory,
            threads: new Map(),
            createdAt: performance.now(),
            cpuTime: 0
        };

        this.availableMemory -= memory;
        this.processes.set(process.pid, process);

        this.emit("process:created", {
            pid: process.pid,
            name,
            memory
        });

        return process;
    }

    createThread(pid, name, burstTime) {
        const process = this.getProcess(pid);

        if (process.state === ProcessState.TERMINATED) {
            throw new InvalidTransitionError(
                "Cannot create threads in a terminated process"
            );
        }

        if (!Number.isSafeInteger(burstTime) || burstTime <= 0) {
            throw new RangeError("Burst time must be positive");
        }

        const thread = {
            tid: this.nextTid++,
            name,
            state: ThreadState.READY,
            remainingTime: burstTime,
            burstTime,
            cpuTime: 0
        };

        process.threads.set(thread.tid, thread);

        this.readyQueue.push({
            pid,
            tid: thread.tid
        });

        this.emit("thread:ready", {
            pid,
            tid: thread.tid
        });

        return thread;
    }

    getProcess(pid) {
        const process = this.processes.get(pid);

        if (!process) {
            throw new OperatingSystemError(
                `Process ${pid} does not exist`
            );
        }

        return process;
    }

    async schedule() {
        this.emit("scheduler:started");

        while (this.readyQueue.length > 0) {
            const task = this.readyQueue.shift();
            const process = this.getProcess(task.pid);
            const thread = process.threads.get(task.tid);

            if (!thread || thread.state === ThreadState.TERMINATED) {
                continue;
            }

            if (process.state === ProcessState.TERMINATED) {
                continue;
            }

            process.state = ProcessState.RUNNING;
            thread.state = ThreadState.RUNNING;

            const executionTime = Math.min(
                this.quantum,
                thread.remainingTime
            );

            await new Promise(resolve => setImmediate(resolve));

            this.clock += executionTime;
            thread.remainingTime -= executionTime;
            thread.cpuTime += executionTime;
            process.cpuTime += executionTime;

            this.emit("cpu:timeslice", {
                pid: process.pid,
                tid: thread.tid,
                executionTime,
                remainingTime: thread.remainingTime,
                clock: this.clock
            });

            if (thread.remainingTime === 0) {
                thread.state = ThreadState.TERMINATED;

                this.emit("thread:terminated", {
                    pid: process.pid,
                    tid: thread.tid
                });
            } else {
                thread.state = ThreadState.READY;

                this.readyQueue.push({
                    pid: process.pid,
                    tid: thread.tid
                });
            }

            const active = [...process.threads.values()]
                .some(t => t.state !== ThreadState.TERMINATED);

            if (!active) {
                process.state = ProcessState.READY;
            }
        }

        this.emit("scheduler:completed", {
            clock: this.clock
        });
    }

    terminateProcess(pid) {
        const process = this.getProcess(pid);

        if (process.state === ProcessState.TERMINATED) {
            throw new InvalidTransitionError(
                "Process already terminated"
            );
        }

        process.state = ProcessState.TERMINATED;

        for (const thread of process.threads.values()) {
            thread.state = ThreadState.TERMINATED;
        }

        this.readyQueue = this.readyQueue.filter(
            task => task.pid !== pid
        );

        this.availableMemory += process.memory;
        process.memory = 0;

        this.emit("process:terminated", { pid });
    }

    report() {
        return [...this.processes.values()].map(process => ({
            pid: process.pid,
            name: process.name,
            state: process.state,
            memory: process.memory,
            cpuTime: process.cpuTime,
            threadCount: process.threads.size
        }));
    }
}

/*
 * Promise-based mutex.
 * The promise chain serializes critical sections.
 */
class AsyncMutex {
    constructor() {
        this.tail = Promise.resolve();
        this.waiting = 0;
    }

    async runExclusive(callback) {
        this.waiting++;

        let release;
        const previous = this.tail;

        this.tail = new Promise(resolve => {
            release = resolve;
        });

        await previous;
        this.waiting--;

        try {
            return await callback();
        } finally {
            release();
        }
    }
}

class SharedCounter {
    constructor() {
        this.value = 0;
        this.mutex = new AsyncMutex();
    }

    async increment(count) {
        if (!Number.isSafeInteger(count) || count < 0) {
            throw new RangeError("Invalid increment count");
        }

        for (let i = 0; i < count; i++) {
            await this.mutex.runExclusive(async () => {
                this.value++;
            });
        }
    }
}

/*
 * Contiguous first-fit memory allocator.
 * Adjacent free blocks are merged during deallocation.
 */
class PhysicalMemory {
    constructor(capacity) {
        if (!Number.isSafeInteger(capacity) || capacity <= 0) {
            throw new RangeError("Invalid capacity");
        }

        this.capacity = capacity;
        this.blocks = [
            { start: 0, size: capacity, pid: null }
        ];
    }

    allocate(pid, size) {
        if (!Number.isSafeInteger(size) || size <= 0) {
            throw new RangeError("Invalid allocation size");
        }

        if (this.blocks.some(block => block.pid === pid)) {
            throw new OperatingSystemError(
                "Process already has an allocation"
            );
        }

        const index = this.blocks.findIndex(
            block => block.pid === null && block.size >= size
        );

        if (index === -1) {
            throw new ResourceExhaustionError(
                "No sufficiently large contiguous memory block"
            );
        }

        const block = this.blocks[index];

        const allocated = {
            start: block.start,
            size,
            pid
        };

        const remaining = block.size - size;
        const replacement = [allocated];

        if (remaining > 0) {
            replacement.push({
                start: block.start + size,
                size: remaining,
                pid: null
            });
        }

        this.blocks.splice(index, 1, ...replacement);

        return allocated;
    }

    release(pid) {
        const block = this.blocks.find(
            item => item.pid === pid
        );

        if (!block) {
            throw new OperatingSystemError(
                "Process allocation not found"
            );
        }

        block.pid = null;

        const merged = [];

        for (const current of this.blocks) {
            const previous = merged[merged.length - 1];

            if (
                previous &&
                previous.pid === null &&
                current.pid === null
            ) {
                previous.size += current.size;
            } else {
                merged.push({ ...current });
            }
        }

        this.blocks = merged;
    }

    report() {
        return this.blocks.map(block => ({
            ...block,
            status: block.pid === null ? "FREE" : "ALLOCATED"
        }));
    }
}

/*
 * FIFO page replacement.
 * A page hit does not change insertion order.
 */
class PageTable {
    constructor(frameCount) {
        if (!Number.isSafeInteger(frameCount) || frameCount <= 0) {
            throw new RangeError("Frame count must be positive");
        }

        this.frameCount = frameCount;
        this.frames = [];
        this.resident = new Set();
        this.faults = 0;
        this.hits = 0;
    }

    access(page) {
        if (!Number.isSafeInteger(page) || page < 0) {
            throw new RangeError("Invalid page number");
        }

        if (this.resident.has(page)) {
            this.hits++;
            return { type: "HIT", page };
        }

        this.faults++;

        let evicted = null;

        if (this.frames.length === this.frameCount) {
            evicted = this.frames.shift();
            this.resident.delete(evicted);
        }

        this.frames.push(page);
        this.resident.add(page);

        return {
            type: "FAULT",
            page,
            evicted,
            frames: [...this.frames]
        };
    }

    statistics() {
        const total = this.hits + this.faults;

        return {
            hits: this.hits,
            faults: this.faults,
            hitRatio: total === 0 ? 0 : this.hits / total
        };
    }
}

class VirtualFileSystem {
    constructor() {
        this.files = new Map();
    }

    normalize(filePath) {
        if (
            typeof filePath !== "string" ||
            !filePath.startsWith("/") ||
            filePath.includes("\0")
        ) {
            throw new TypeError("Invalid absolute file path");
        }

        const segments = filePath.split("/");

        if (segments.includes("..")) {
            throw new AccessDeniedError(
                "Path traversal is prohibited"
            );
        }

        const normalized = path.posix.normalize(filePath);

        if (normalized === "/") {
            throw new TypeError("Root cannot be a file");
        }

        return normalized;
    }

    create(filePath, owner, content, permissions = {}) {
        const normalized = this.normalize(filePath);

        if (this.files.has(normalized)) {
            throw new OperatingSystemError(
                "File already exists"
            );
        }

        if (typeof owner !== "string" || !owner.trim()) {
            throw new TypeError("File owner is required");
        }

        const access = new Map();

        access.set(owner, new Set(["read", "write", "delete"]));

        for (const [user, actions] of Object.entries(permissions)) {
            access.set(user, new Set(actions));
        }

        this.files.set(normalized, {
            owner,
            content: String(content),
            permissions: access
        });
    }

    authorize(filePath, user, action) {
        const normalized = this.normalize(filePath);
        const file = this.files.get(normalized);

        if (!file) {
            throw new OperatingSystemError("File not found");
        }

        if (!file.permissions.get(user)?.has(action)) {
            throw new AccessDeniedError(
                `${user} cannot ${action} ${normalized}`
            );
        }

        return file;
    }

    read(filePath, user) {
        return this.authorize(filePath, user, "read").content;
    }

    write(filePath, user, content) {
        this.authorize(filePath, user, "write").content =
            String(content);
    }

    delete(filePath, user) {
        const normalized = this.normalize(filePath);
        this.authorize(normalized, user, "delete");
        this.files.delete(normalized);
    }

    list() {
        return [...this.files.entries()].map(
            ([filePath, file]) => ({
                path: filePath,
                owner: file.owner,
                size: Buffer.byteLength(file.content, "utf8")
            })
        );
    }
}

async function main() {
    const kernel = new Kernel({
        memoryCapacity: 2048,
        quantum: 3
    });

    kernel.on("process:created", event => {
        console.log("PROCESS CREATED:", event);
    });

    kernel.on("cpu:timeslice", event => {
        console.log(
            `CPU PID=${event.pid} TID=${event.tid} ` +
            `TIME=${event.executionTime} REMAINING=${event.remainingTime}`
        );
    });

    kernel.on("thread:terminated", event => {
        console.log("THREAD COMPLETED:", event);
    });

    kernel.on("process:terminated", event => {
        console.log("PROCESS TERMINATED:", event);
    });

    console.log("\n1. PROCESS AND THREAD MANAGEMENT");

    const webServer = kernel.createProcess("WebServer", 512);
    const database = kernel.createProcess("Database", 768);

    kernel.createThread(webServer.pid, "HTTP-Worker", 8);
    kernel.createThread(webServer.pid, "Logger", 4);
    kernel.createThread(database.pid, "Query-Worker", 6);
    kernel.createThread(database.pid, "Cache-Worker", 3);

    await kernel.schedule();

    console.log("PROCESS REPORT:", kernel.report());

    console.log("\n2. THREAD SYNCHRONIZATION");

    const counter = new SharedCounter();

    await Promise.all([
        counter.increment(1000),
        counter.increment(1000),
        counter.increment(1000)
    ]);

    console.log("Expected counter: 3000");
    console.log("Actual counter:", counter.value);

    if (counter.value !== 3000) {
        throw new OperatingSystemError(
            "Synchronization invariant failed"
        );
    }

    console.log("\n3. CONTIGUOUS MEMORY ALLOCATION");

    const physicalMemory = new PhysicalMemory(1024);

    physicalMemory.allocate(1001, 256);
    physicalMemory.allocate(1002, 384);
    physicalMemory.allocate(1003, 128);

    console.table(physicalMemory.report());

    physicalMemory.release(1002);

    console.log("After releasing PID 1002:");
    console.table(physicalMemory.report());

    try {
        physicalMemory.allocate(1004, 700);
    } catch (error) {
        console.log("EXPECTED ALLOCATION FAILURE:", error.message);
    }

    physicalMemory.release(1001);
    physicalMemory.release(1003);

    console.log("After coalescing free blocks:");
    console.table(physicalMemory.report());

    console.log("\n4. VIRTUAL MEMORY");

    const pageTable = new PageTable(3);

    for (const page of [1, 2, 3, 1, 4, 2, 5]) {
        console.log(pageTable.access(page));
    }

    console.log("PAGE STATISTICS:", pageTable.statistics());

    console.log("\n5. FILESYSTEM AND ACCESS CONTROL");

    const fileSystem = new VirtualFileSystem();

    fileSystem.create(
        "/var/log/system.log",
        "administrator",
        "System initialized",
        {
            operator: ["read"]
        }
    );

    console.log(
        "Operator read:",
        fileSystem.read("/var/log/system.log", "operator")
    );

    try {
        fileSystem.write(
            "/var/log/system.log",
            "operator",
            "Unauthorized update"
        );
    } catch (error) {
        console.log("ACCESS CONTROL:", error.message);
    }

    try {
        fileSystem.read(
            "/var/../../etc/passwd",
            "administrator"
        );
    } catch (error) {
        console.log("PATH SECURITY:", error.message);
    }

    console.log("FILES:", fileSystem.list());

    console.log("\n6. PROCESS CLEANUP");

    kernel.terminateProcess(webServer.pid);
    kernel.terminateProcess(database.pid);

    console.log("Available kernel memory:", kernel.availableMemory);
    console.log("Simulation completed.");
}

main().catch(error => {
    console.error("KERNEL SIMULATION FAILURE:", error);
    process.exitCode = 1;
});
