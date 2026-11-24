"use strict";

/*
 * Distributed System Challenges
 *
 * Event-driven distributed key-value store:
 * - Asynchronous network communication
 * - Variable message latency
 * - Node failures and network partitions
 * - Quorum-based replication
 * - Strong and eventual consistency
 * - Idempotent operations
 * - Timeouts and retries
 * - Read repair
 * - Latency measurement
 */

const { performance } = require("node:perf_hooks");
const { randomUUID } = require("node:crypto");
const { EventEmitter } = require("node:events");

class DistributedError extends Error {}

class NetworkTimeout extends DistributedError {}

class QuorumError extends DistributedError {}

class ValidationError extends DistributedError {}

const NodeStatus = Object.freeze({
    HEALTHY: "HEALTHY",
    UNAVAILABLE: "UNAVAILABLE",
    PARTITIONED: "PARTITIONED"
});

const Consistency = Object.freeze({
    ONE: "ONE",
    QUORUM: "QUORUM",
    ALL: "ALL"
});

function validateConsistency(level) {
    if (!Object.values(Consistency).includes(level)) {
        throw new ValidationError(
            `Invalid consistency level: ${level}`
        );
    }
}

function delay(milliseconds) {
    return new Promise(resolve => {
        setTimeout(resolve, milliseconds);
    });
}

class DistributedNetwork {
    constructor({
        minimumLatency = 10,
        maximumLatency = 30,
        packetLoss = 0,
        timeout = 100
    } = {}) {
        if (
            minimumLatency < 0 ||
            maximumLatency < minimumLatency ||
            timeout <= 0 ||
            packetLoss < 0 ||
            packetLoss > 1
        ) {
            throw new ValidationError("Invalid network configuration");
        }

        this.minimumLatency = minimumLatency;
        this.maximumLatency = maximumLatency;
        this.packetLoss = packetLoss;
        this.timeout = timeout;
        this.partitions = new Set();
    }

    linkKey(source, destination) {
        return `${source}->${destination}`;
    }

    partition(source, destination) {
        this.partitions.add(this.linkKey(source, destination));
        this.partitions.add(this.linkKey(destination, source));
    }

    heal(source, destination) {
        this.partitions.delete(this.linkKey(source, destination));
        this.partitions.delete(this.linkKey(destination, source));
    }

    async transmit(source, destination) {
        if (
            this.partitions.has(
                this.linkKey(source, destination)
            )
        ) {
            throw new NetworkTimeout("Network partition");
        }

        if (Math.random() < this.packetLoss) {
            throw new NetworkTimeout("Packet dropped");
        }

        const latency =
            this.minimumLatency +
            Math.random() *
            (this.maximumLatency - this.minimumLatency);

        if (latency > this.timeout) {
            await delay(this.timeout);
            throw new NetworkTimeout("Request timeout");
        }

        await delay(latency);

        return latency;
    }
}

class Replica {
    constructor(id) {
        this.id = id;
        this.status = NodeStatus.HEALTHY;
        this.records = new Map();
        this.operations = new Set();
    }

    get available() {
        return this.status === NodeStatus.HEALTHY;
    }

    apply(record) {
        if (!this.available) {
            throw new NetworkTimeout(`${this.id} unavailable`);
        }

        if (this.operations.has(record.operationId)) {
            return true;
        }

        const current = this.records.get(record.key);

        if (!current || Replica.compare(record, current) > 0) {
            this.records.set(record.key, Object.freeze({ ...record }));
        }

        this.operations.add(record.operationId);
        return true;
    }

    read(key) {
        if (!this.available) {
            throw new NetworkTimeout(`${this.id} unavailable`);
        }

        return this.records.get(key) ?? null;
    }

    static compare(a, b) {
        if (a.version !== b.version) {
            return a.version - b.version;
        }

        if (a.timestamp !== b.timestamp) {
            return a.timestamp - b.timestamp;
        }

        return a.operationId.localeCompare(b.operationId);
    }
}

class DistributedStore extends EventEmitter {
    constructor({
        nodeCount = 5,
        replicationFactor = 3,
        network = new DistributedNetwork()
    } = {}) {
        super();

        if (
            !Number.isInteger(nodeCount) ||
            !Number.isInteger(replicationFactor) ||
            nodeCount < 1 ||
            replicationFactor < 1 ||
            replicationFactor > nodeCount
        ) {
            throw new ValidationError("Invalid cluster configuration");
        }

        this.nodes = Array.from(
            { length: nodeCount },
            (_, index) => new Replica(`node-${index + 1}`)
        );

        this.replicationFactor = replicationFactor;
        this.network = network;
        this.clock = 0;
        this.coordinator = "coordinator";

        this.operationResults = new Map();

        this.metrics = {
            writes: 0,
            reads: 0,
            failures: 0,
            retries: 0,
            timeouts: 0,
            latencies: []
        };
    }

    quorum() {
        return Math.floor(this.replicationFactor / 2) + 1;
    }

    required(level) {
        validateConsistency(level);

        switch (level) {
            case Consistency.ONE:
                return 1;
            case Consistency.QUORUM:
                return this.quorum();
            case Consistency.ALL:
                return this.replicationFactor;
            default:
                throw new ValidationError("Unknown consistency policy");
        }
    }

    replicas(key) {
        let hash = 0;

        for (const character of key) {
            hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
        }

        const start = hash % this.nodes.length;

        return Array.from(
            { length: this.replicationFactor },
            (_, offset) =>
                this.nodes[(start + offset) % this.nodes.length]
        );
    }

    async sendToReplica(node, record) {
        const latency = await this.network.transmit(
            this.coordinator,
            node.id
        );

        node.apply(record);

        this.emit("replica:write", {
            node: node.id,
            key: record.key,
            latency
        });

        return latency;
    }

    async write(
        key,
        value,
        {
            consistency = Consistency.QUORUM,
            operationId = randomUUID(),
            retries = 2
        } = {}
    ) {
        if (
            typeof key !== "string" ||
            !key.trim() ||
            typeof value !== "string" ||
            key.length > 256 ||
            value.length > 10000 ||
            !Number.isInteger(retries) ||
            retries < 0
        ) {
            throw new ValidationError("Invalid write request");
        }

        const required = this.required(consistency);

        if (this.operationResults.has(operationId)) {
            return this.operationResults.get(operationId);
        }

        const start = performance.now();
        const record = Object.freeze({
            key,
            value,
            version: ++this.clock,
            timestamp: Date.now(),
            operationId
        });

        const targets = this.replicas(key);
        const acknowledged = new Set();

        try {
            for (let attempt = 0; attempt <= retries; attempt++) {
                if (attempt > 0) {
                    this.metrics.retries++;
                }

                // Concurrent requests reduce write latency to the
                // duration of the required fastest acknowledgements.
                const results = await Promise.allSettled(
                    targets
                        .filter(node => !acknowledged.has(node.id))
                        .map(async node => ({
                            id: node.id,
                            latency: await this.sendToReplica(node, record)
                        }))
                );

                for (const result of results) {
                    if (result.status === "fulfilled") {
                        acknowledged.add(result.value.id);
                    } else if (
                        result.reason instanceof NetworkTimeout
                    ) {
                        this.metrics.timeouts++;
                    }
                }

                if (acknowledged.size >= required) {
                    this.operationResults.set(operationId, true);

                    this.emit("write:committed", {
                        key,
                        version: record.version,
                        acknowledgements: acknowledged.size
                    });

                    return true;
                }
            }

            throw new QuorumError(
                `Required ${required}, received ${acknowledged.size}`
            );
        } catch (error) {
            this.metrics.failures++;
            this.operationResults.set(operationId, false);
            this.emit("write:failed", { key, error: error.message });
            throw error;
        } finally {
            const elapsed = performance.now() - start;
            this.metrics.writes++;
            this.metrics.latencies.push(elapsed);
        }
    }

    async read(
        key,
        {
            consistency = Consistency.QUORUM,
            repair = true
        } = {}
    ) {
        if (typeof key !== "string" || !key.trim()) {
            throw new ValidationError("Invalid read key");
        }

        const required = this.required(consistency);
        const start = performance.now();

        try {
            const targets = this.replicas(key);

            const results = await Promise.allSettled(
                targets.map(async node => {
                    await this.network.transmit(
                        this.coordinator,
                        node.id
                    );

                    return {
                        node,
                        record: node.read(key)
                    };
                })
            );

            const responses = results
                .filter(result => result.status === "fulfilled")
                .map(result => result.value);

            this.metrics.timeouts += results.filter(
                result => result.status === "rejected"
            ).length;

            if (responses.length < required) {
                throw new QuorumError(
                    `Read requires ${required} responses`
                );
            }

            const records = responses
                .map(response => response.record)
                .filter(Boolean);

            if (records.length === 0) {
                return null;
            }

            const latest = records.reduce((a, b) =>
                Replica.compare(a, b) >= 0 ? a : b
            );

            if (repair) {
                for (const response of responses) {
                    const current = response.record;

                    if (
                        !current ||
                        Replica.compare(latest, current) > 0
                    ) {
                        response.node.apply(latest);
                    }
                }
            }

            return latest;
        } finally {
            this.metrics.reads++;
            this.metrics.latencies.push(
                performance.now() - start
            );
        }
    }

    async synchronize(key) {
        const replicas = this.replicas(key);

        const available = replicas.filter(node => node.available);

        const records = available
            .map(node => node.records.get(key))
            .filter(Boolean);

        if (records.length === 0) {
            return 0;
        }

        const latest = records.reduce((a, b) =>
            Replica.compare(a, b) >= 0 ? a : b
        );

        let repaired = 0;

        for (const node of available) {
            const current = node.records.get(key);

            if (
                !current ||
                Replica.compare(latest, current) > 0
            ) {
                node.apply(latest);
                repaired++;
            }
        }

        return repaired;
    }

    setNodeStatus(nodeId, status) {
        const node = this.nodes.find(item => item.id === nodeId);

        if (!node) {
            throw new ValidationError(`Unknown node: ${nodeId}`);
        }

        if (!Object.values(NodeStatus).includes(status)) {
            throw new ValidationError("Invalid node state");
        }

        node.status = status;

        this.emit("node:status", {
            node: nodeId,
            status
        });
    }

    report() {
        const sorted = [...this.metrics.latencies].sort(
            (a, b) => a - b
        );

        const average = sorted.length
            ? sorted.reduce((sum, item) => sum + item, 0) /
              sorted.length
            : 0;

        const p95 = sorted.length
            ? sorted[Math.min(
                sorted.length - 1,
                Math.ceil(sorted.length * 0.95) - 1
            )]
            : 0;

        return {
            ...this.metrics,
            averageLatencyMs: Number(average.toFixed(2)),
            p95LatencyMs: Number(p95.toFixed(2))
        };
    }
}

async function main() {
    const network = new DistributedNetwork({
        minimumLatency: 5,
        maximumLatency: 20,
        packetLoss: 0,
        timeout: 80
    });

    const store = new DistributedStore({
        nodeCount: 5,
        replicationFactor: 3,
        network
    });

    store.on("write:committed", event => {
        console.log("COMMIT:", event);
    });

    store.on("write:failed", event => {
        console.log("FAILED:", event);
    });

    store.on("node:status", event => {
        console.log("NODE STATUS:", event);
    });

    console.log("\n1. QUORUM WRITE");

    await store.write("order:5001", "PAYMENT_CONFIRMED", {
        consistency: Consistency.QUORUM,
        operationId: "order-payment-5001"
    });

    console.log("\n2. IDEMPOTENT RETRY");

    await store.write("order:5001", "PAYMENT_CONFIRMED", {
        operationId: "order-payment-5001"
    });

    console.log("\n3. QUORUM READ");

    const record = await store.read("order:5001");

    console.log("Read:", record);

    console.log("\n4. NODE FAILURE");

    store.setNodeStatus("node-1", NodeStatus.UNAVAILABLE);

    await store.write("order:5002", "SHIPPED");

    console.log("\n5. NETWORK PARTITION");

    network.partition("coordinator", "node-2");

    try {
        await store.write("order:5003", "PROCESSING", {
            consistency: Consistency.ALL,
            retries: 0
        });
    } catch (error) {
        console.log("Expected failure:", error.message);
    }

    console.log("\n6. RECOVERY");

    network.heal("coordinator", "node-2");

    store.setNodeStatus("node-1", NodeStatus.HEALTHY);

    console.log(
        "Replicas repaired:",
        await store.synchronize("order:5001")
    );

    console.log("\n7. PERFORMANCE METRICS");
    console.log(store.report());
}

main().catch(error => {
    console.error("Application failure:", error.message);
    process.exitCode = 1;
});
