"use strict";

/*
 * CAP Theorem: Consistency, Availability, Partition Tolerance
 *
 * Node.js 18+
 * No external dependencies.
 *
 * Engineering perspective:
 * - Event-driven replica updates
 * - Asynchronous operation processing
 * - CP quorum policy
 * - AP local-write policy
 * - Network partition simulation
 * - Deterministic conflict resolution
 * - Operation tracing and failure handling
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

const CAPMode = Object.freeze({
    CP: "CP",
    AP: "AP"
});

const Status = Object.freeze({
    SUCCESS: "SUCCESS",
    REJECTED: "REJECTED",
    UNAVAILABLE: "UNAVAILABLE"
});

class CAPError extends Error {
    constructor(message) {
        super(message);
        this.name = this.constructor.name;
    }
}

class ValidationError extends CAPError {}
class QuorumError extends CAPError {}

function validateIdentifier(value, field) {
    if (
        typeof value !== "string" ||
        value.trim().length === 0 ||
        value.length > 100
    ) {
        throw new ValidationError(`Invalid ${field}.`);
    }
}

class Replica {
    constructor(id) {
        validateIdentifier(id, "replica ID");

        this.id = id;
        this.available = true;
        this.partition = 0;
        this.data = new Map();
        this.sequence = 0;
    }

    apply(record) {
        if (!this.available) {
            throw new CAPError(`Replica ${this.id} is unavailable.`);
        }

        const current = this.data.get(record.key);

        if (
            !current ||
            compareVersion(record.version, current.version) > 0
        ) {
            this.data.set(record.key, structuredClone(record));
        }
    }
}

function compareVersion(a, b) {
    if (a.timestamp !== b.timestamp) {
        return a.timestamp - b.timestamp;
    }

    return a.writer.localeCompare(b.writer);
}

class CAPCluster extends EventEmitter {
    constructor({ mode, nodeCount = 3 }) {
        super();

        if (![CAPMode.CP, CAPMode.AP].includes(mode)) {
            throw new ValidationError("Mode must be CP or AP.");
        }

        if (!Number.isInteger(nodeCount) || nodeCount < 1 || nodeCount > 100) {
            throw new ValidationError("Node count must be between 1 and 100.");
        }

        this.mode = mode;
        this.nodes = new Map();
        this.logicalClock = 0;
        this.events = [];
        this.operationLock = Promise.resolve();

        for (let i = 1; i <= nodeCount; i++) {
            const id = `replica-${i}`;
            this.nodes.set(id, new Replica(id));
        }
    }

    get quorum() {
        return Math.floor(this.nodes.size / 2) + 1;
    }

    getNode(id) {
        const node = this.nodes.get(id);

        if (!node) {
            throw new ValidationError(`Unknown replica: ${id}`);
        }

        return node;
    }

    getConnectedNodes(nodeId) {
        const requester = this.getNode(nodeId);

        if (!requester.available) {
            return [];
        }

        return [...this.nodes.values()].filter(
            node =>
                node.available &&
                node.partition === requester.partition
        );
    }

    recordEvent(type, details) {
        const event = Object.freeze({
            id: crypto.randomUUID(),
            type,
            timestamp: new Date().toISOString(),
            ...details
        });

        this.events.push(event);
        this.emit(type, event);
    }

    partition(groups) {
        if (!Array.isArray(groups) || groups.length === 0) {
            throw new ValidationError("At least one partition is required.");
        }

        const assigned = new Set();

        groups.forEach((group, index) => {
            if (!Array.isArray(group) || group.length === 0) {
                throw new ValidationError("Empty partition group.");
            }

            for (const id of group) {
                this.getNode(id);

                if (assigned.has(id)) {
                    throw new ValidationError(`Duplicate node: ${id}`);
                }

                assigned.add(id);
                this.getNode(id).partition = index;
            }
        });

        let nextPartition = groups.length;

        for (const id of this.nodes.keys()) {
            if (!assigned.has(id)) {
                this.getNode(id).partition = nextPartition++;
            }
        }

        this.recordEvent("PARTITION_CREATED", {
            groups: structuredClone(groups)
        });
    }

    setAvailability(nodeId, available) {
        if (typeof available !== "boolean") {
            throw new ValidationError("Availability must be boolean.");
        }

        const node = this.getNode(nodeId);
        node.available = available;

        this.recordEvent("NODE_AVAILABILITY_CHANGED", {
            nodeId,
            available
        });
    }

    /*
     * Serializes state-changing operations within this process.
     * This prevents local asynchronous races but is not a
     * distributed consensus protocol.
     */
    serialize(operation) {
        const result = this.operationLock.then(operation);

        this.operationLock = result.catch(() => undefined);

        return result;
    }

    async write(nodeId, key, value) {
        validateIdentifier(key, "key");

        if (typeof value !== "string" || value.length > 10000) {
            throw new ValidationError("Invalid value.");
        }

        return this.serialize(async () => {
            const connected = this.getConnectedNodes(nodeId);

            if (connected.length === 0) {
                return {
                    status: Status.UNAVAILABLE,
                    message: "Requesting replica is unavailable."
                };
            }

            if (
                this.mode === CAPMode.CP &&
                connected.length < this.quorum
            ) {
                this.recordEvent("WRITE_REJECTED", {
                    nodeId,
                    key,
                    reason: "QUORUM_UNAVAILABLE"
                });

                return {
                    status: Status.REJECTED,
                    message: "A majority quorum is unavailable."
                };
            }

            const record = {
                key,
                value,
                version: {
                    timestamp: ++this.logicalClock,
                    writer: nodeId
                }
            };

            if (this.mode === CAPMode.CP) {
                // Acknowledge only after applying to a majority.
                for (const node of connected) {
                    node.apply(record);
                }
            } else {
                // AP accepts a write at the requesting replica.
                this.getNode(nodeId).apply(record);
            }

            this.recordEvent("WRITE_ACCEPTED", {
                nodeId,
                key,
                version: record.version
            });

            return {
                status: Status.SUCCESS,
                record
            };
        });
    }

    async read(nodeId, key) {
        validateIdentifier(key, "key");

        const connected = this.getConnectedNodes(nodeId);

        if (connected.length === 0) {
            return {
                status: Status.UNAVAILABLE,
                value: null
            };
        }

        if (
            this.mode === CAPMode.CP &&
            connected.length < this.quorum
        ) {
            return {
                status: Status.UNAVAILABLE,
                value: null,
                reason: "QUORUM_UNAVAILABLE"
            };
        }

        if (this.mode === CAPMode.AP) {
            const record = this.getNode(nodeId).data.get(key);

            return {
                status: Status.SUCCESS,
                value: record?.value ?? null,
                consistency: "LOCAL_REPLICA"
            };
        }

        const candidates = connected
            .map(node => node.data.get(key))
            .filter(Boolean);

        if (candidates.length === 0) {
            return {
                status: Status.SUCCESS,
                value: null
            };
        }

        const latest = candidates.reduce(
            (best, current) =>
                compareVersion(current.version, best.version) > 0
                    ? current
                    : best
        );

        return {
            status: Status.SUCCESS,
            value: latest.value,
            consistency: "QUORUM"
        };
    }

    async healPartition() {
        return this.serialize(async () => {
            for (const node of this.nodes.values()) {
                node.partition = 0;
            }

            const merged = new Map();

            for (const node of this.nodes.values()) {
                if (!node.available) continue;

                for (const [key, record] of node.data) {
                    const existing = merged.get(key);

                    if (
                        !existing ||
                        compareVersion(record.version, existing.version) > 0
                    ) {
                        merged.set(key, record);
                    }
                }
            }

            for (const node of this.nodes.values()) {
                if (!node.available) continue;

                for (const record of merged.values()) {
                    node.apply(record);
                }
            }

            this.recordEvent("PARTITION_HEALED", {
                reconciledKeys: merged.size
            });

            return this.report();
        });
    }

    report() {
        const replicas = {};

        for (const [id, node] of this.nodes) {
            replicas[id] = {
                available: node.available,
                data: Object.fromEntries(
                    [...node.data.entries()].map(([key, record]) => [
                        key,
                        record.value
                    ])
                )
            };
        }

        const snapshots = Object.values(replicas)
            .filter(replica => replica.available)
            .map(replica => JSON.stringify(replica.data));

        return {
            mode: this.mode,
            quorum: this.quorum,
            consistent: new Set(snapshots).size <= 1,
            replicas
        };
    }
}

async function demonstrateCP() {
    console.log("\n========== CP SYSTEM ==========");

    const cluster = new CAPCluster({
        mode: CAPMode.CP,
        nodeCount: 3
    });

    cluster.on("WRITE_ACCEPTED", event => {
        console.log("Accepted:", event.key, event.nodeId);
    });

    await cluster.write("replica-1", "balance", "1000");

    cluster.partition([
        ["replica-1"],
        ["replica-2", "replica-3"]
    ]);

    const minority = await cluster.write(
        "replica-1",
        "balance",
        "2000"
    );

    const majority = await cluster.write(
        "replica-2",
        "balance",
        "1500"
    );

    console.log("Minority:", minority.status);
    console.log("Majority:", majority.status);

    await cluster.healPartition();

    console.log(JSON.stringify(cluster.report(), null, 2));
}

async function demonstrateAP() {
    console.log("\n========== AP SYSTEM ==========");

    const cluster = new CAPCluster({
        mode: CAPMode.AP,
        nodeCount: 3
    });

    await cluster.write("replica-1", "inventory", "100");

    cluster.partition([
        ["replica-1"],
        ["replica-2", "replica-3"]
    ]);

    await Promise.all([
        cluster.write("replica-1", "inventory", "80"),
        cluster.write("replica-2", "inventory", "90")
    ]);

    console.log("Before reconciliation:");
    console.log(JSON.stringify(cluster.report(), null, 2));

    await cluster.healPartition();

    console.log("After reconciliation:");
    console.log(JSON.stringify(cluster.report(), null, 2));
}

async function runTests() {
    const cp = new CAPCluster({
        mode: CAPMode.CP,
        nodeCount: 3
    });

    await cp.write("replica-1", "test", "initial");

    cp.partition([
        ["replica-1"],
        ["replica-2", "replica-3"]
    ]);

    const rejected = await cp.write("replica-1", "test", "new");

    if (rejected.status !== Status.REJECTED) {
        throw new Error("CP minority partition test failed.");
    }

    const accepted = await cp.write("replica-2", "test", "updated");

    if (accepted.status !== Status.SUCCESS) {
        throw new Error("CP majority partition test failed.");
    }

    await cp.healPartition();

    if (!cp.report().consistent) {
        throw new Error("CP reconciliation failed.");
    }

    const ap = new CAPCluster({
        mode: CAPMode.AP,
        nodeCount: 3
    });

    ap.partition([
        ["replica-1"],
        ["replica-2", "replica-3"]
    ]);

    const results = await Promise.all([
        ap.write("replica-1", "item", "A"),
        ap.write("replica-2", "item", "B")
    ]);

    if (!results.every(result => result.status === Status.SUCCESS)) {
        throw new Error("AP local availability test failed.");
    }

    await ap.healPartition();

    if (!ap.report().consistent) {
        throw new Error("AP reconciliation test failed.");
    }

    ap.setAvailability("replica-1", false);

    const unavailable = await ap.read("replica-1", "item");

    if (unavailable.status !== Status.UNAVAILABLE) {
        throw new Error("Node failure test failed.");
    }

    console.log("\nAll JavaScript assertions passed.");
}

async function main() {
    await demonstrateCP();
    await demonstrateAP();
    await runTests();
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
