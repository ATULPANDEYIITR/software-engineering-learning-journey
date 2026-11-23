'use strict';

/**
 * Distributed Systems: Event-Driven Node and Network Simulation
 *
 * Demonstrates:
 * - Event-driven communication
 * - Asynchronous message processing
 * - Distributed node membership
 * - Network partitions
 * - Message retries
 * - Idempotency
 * - Replicated key-value state
 * - Lamport logical clocks
 * - Conflict resolution
 * - Quorum evaluation
 * - Failure detection
 * - Anti-entropy synchronization
 *
 * Runtime: Node.js 18+
 *
 * Execute:
 * node distributed_systems.js
 */

const { randomUUID } = require('node:crypto');
const { EventEmitter } = require('node:events');

// ============================================================
// DOMAIN CONSTANTS
// ============================================================

const NodeStatus = Object.freeze({
    ACTIVE: 'ACTIVE',
    STOPPED: 'STOPPED',
    SUSPECTED: 'SUSPECTED'
});

const MessageType = Object.freeze({
    REPLICATION: 'REPLICATION',
    HEARTBEAT: 'HEARTBEAT',
    SYNC: 'SYNC'
});

const Consistency = Object.freeze({
    ONE: 'ONE',
    QUORUM: 'QUORUM',
    ALL: 'ALL'
});

class DistributedError extends Error {}

class QuorumError extends DistributedError {}

class NodeError extends DistributedError {}

class NetworkError extends DistributedError {}

// ============================================================
// VERSION COMPARISON
// ============================================================

function compareVersions(a, b) {
    if (a.clock !== b.clock) {
        return a.clock - b.clock;
    }

    return a.nodeId.localeCompare(b.nodeId);
}

function clone(value) {
    return structuredClone(value);
}

function validateKey(key) {
    if (typeof key !== 'string' || key.length === 0 || key.length > 256) {
        throw new TypeError('Invalid distributed key');
    }
}

function validateValue(value) {
    if (value === undefined) {
        throw new TypeError('Undefined values are not supported');
    }

    try {
        const serialized = JSON.stringify(value);

        if (serialized === undefined || serialized.length > 1_000_000) {
            throw new TypeError('Value exceeds serialization limits');
        }
    } catch (error) {
        throw new TypeError(`Invalid serializable value: ${error.message}`);
    }
}

// ============================================================
// NETWORK
// ============================================================

class Network extends EventEmitter {

    constructor({
        lossRate = 0,
        duplicateRate = 0,
        maxRetries = 3
    } = {}) {
        super();

        if (
            lossRate < 0 || lossRate > 1 ||
            duplicateRate < 0 || duplicateRate > 1 ||
            !Number.isInteger(maxRetries) || maxRetries < 0
        ) {
            throw new RangeError('Invalid network configuration');
        }

        this.lossRate = lossRate;
        this.duplicateRate = duplicateRate;
        this.maxRetries = maxRetries;

        this.partitions = new Set();
        this.nodes = new Map();

        this.metrics = {
            sent: 0,
            delivered: 0,
            dropped: 0,
            duplicated: 0,
            retries: 0
        };
    }

    register(node) {
        if (this.nodes.has(node.id)) {
            throw new Error(`Duplicate node: ${node.id}`);
        }

        this.nodes.set(node.id, node);
    }

    linkKey(a, b) {
        return [a, b].sort().join('|');
    }

    partition(a, b) {
        if (a === b) {
            throw new Error('Cannot partition a node from itself');
        }

        this.partitions.add(this.linkKey(a, b));
        this.emit('partition', { a, b });
    }

    heal() {
        this.partitions.clear();
        this.emit('networkRestored');
    }

    connected(a, b) {
        return (
            a !== b &&
            !this.partitions.has(this.linkKey(a, b))
        );
    }

    async transmit(message, attempt = 0) {
        this.metrics.sent++;

        if (!this.connected(message.sender, message.receiver)) {
            this.metrics.dropped++;

            if (attempt < this.maxRetries) {
                this.metrics.retries++;
                return this.transmit(message, attempt + 1);
            }

            throw new NetworkError(
                `Network partition between ${message.sender} and ${message.receiver}`
            );
        }

        if (Math.random() < this.lossRate) {
            this.metrics.dropped++;

            if (attempt < this.maxRetries) {
                this.metrics.retries++;
                return this.transmit(message, attempt + 1);
            }

            throw new NetworkError('Message delivery failed after retries');
        }

        const receiver = this.nodes.get(message.receiver);

        if (!receiver || receiver.status !== NodeStatus.ACTIVE) {
            throw new NodeError(`Receiver unavailable: ${message.receiver}`);
        }

        // Yield to the event loop to model asynchronous network processing.
        await new Promise(resolve => setImmediate(resolve));

        await receiver.receive(clone(message));

        this.metrics.delivered++;

        if (Math.random() < this.duplicateRate) {
            this.metrics.duplicated++;

            // Re-delivery uses the same message identifier.
            await receiver.receive(clone(message));
        }

        this.emit('delivery', message);

        return true;
    }

    async broadcast(sender, targets, message) {
        const results = await Promise.allSettled(
            targets.map(receiver => this.transmit({
                ...clone(message),
                messageId: randomUUID(),
                sender,
                receiver
            }))
        );

        return results.filter(result => result.status === 'fulfilled').length;
    }
}

// ============================================================
// DISTRIBUTED NODE
// ============================================================

class DistributedNode extends EventEmitter {

    constructor(id, network) {
        super();

        if (!id || typeof id !== 'string') {
            throw new TypeError('Node identifier is required');
        }

        this.id = id;
        this.network = network;

        this.status = NodeStatus.ACTIVE;
        this.clock = 0;

        this.store = new Map();
        this.processed = new Set();

        this.metrics = {
            writes: 0,
            received: 0,
            stale: 0,
            duplicates: 0
        };

        network.register(this);
    }

    tick() {
        return ++this.clock;
    }

    observe(version) {
        this.clock = Math.max(this.clock, version.clock) + 1;
    }

    assertActive() {
        if (this.status !== NodeStatus.ACTIVE) {
            throw new NodeError(`Node ${this.id} is unavailable`);
        }
    }

    write(key, value) {
        this.assertActive();
        validateKey(key);
        validateValue(value);

        const record = Object.freeze({
            key,
            value: clone(value),
            version: Object.freeze({
                clock: this.tick(),
                nodeId: this.id
            }),
            updatedAt: new Date().toISOString()
        });

        this.store.set(key, record);
        this.metrics.writes++;

        this.emit('localWrite', record);

        return record;
    }

    apply(record) {
        const current = this.store.get(record.key);

        if (
            current &&
            compareVersions(current.version, record.version) >= 0
        ) {
            this.metrics.stale++;
            return false;
        }

        this.observe(record.version);

        this.store.set(record.key, clone(record));

        this.emit('replicatedWrite', record);

        return true;
    }

    async receive(message) {
        this.assertActive();

        if (this.processed.has(message.messageId)) {
            this.metrics.duplicates++;
            return;
        }

        // In production, durable deduplication must be committed
        // atomically with the corresponding state change.
        if (this.processed.size >= 100_000) {
            this.processed.clear();
        }

        this.processed.add(message.messageId);
        this.metrics.received++;

        switch (message.type) {
            case MessageType.REPLICATION:
                this.apply(message.payload);
                break;

            case MessageType.HEARTBEAT:
                this.emit('heartbeat', message.sender);
                break;

            case MessageType.SYNC:
                for (const record of message.payload) {
                    this.apply(record);
                }
                break;

            default:
                throw new DistributedError(
                    `Unsupported message type: ${message.type}`
                );
        }
    }

    get(key) {
        this.assertActive();

        const record = this.store.get(key);

        return record ? clone(record) : null;
    }

    snapshot() {
        return Object.fromEntries(
            [...this.store.entries()]
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([key, value]) => [key, clone(value)])
        );
    }
}

// ============================================================
// CLUSTER SERVICE
// ============================================================

class DistributedCluster {

    constructor(nodeIds) {
        if (
            !Array.isArray(nodeIds) ||
            nodeIds.length < 3 ||
            new Set(nodeIds).size !== nodeIds.length
        ) {
            throw new Error('A cluster requires at least three unique nodes');
        }

        this.network = new Network();

        this.nodes = new Map(
            nodeIds.map(id => [
                id,
                new DistributedNode(id, this.network)
            ])
        );

        this.replicationFactor = Math.min(3, nodeIds.length);
        this.quorum = Math.floor(this.replicationFactor / 2) + 1;
    }

    activeNodes() {
        return [...this.nodes.values()].filter(
            node => node.status === NodeStatus.ACTIVE
        );
    }

    requiredAcknowledgements(consistency) {
        switch (consistency) {
            case Consistency.ONE:
                return 1;

            case Consistency.QUORUM:
                return this.quorum;

            case Consistency.ALL:
                return this.replicationFactor;

            default:
                throw new TypeError('Unknown consistency level');
        }
    }

    async put(coordinatorId, key, value, consistency = Consistency.QUORUM) {
        const coordinator = this.nodes.get(coordinatorId);

        if (!coordinator) {
            throw new NodeError('Unknown coordinator');
        }

        coordinator.assertActive();

        const required = this.requiredAcknowledgements(consistency);

        const record = coordinator.write(key, value);

        const targets = this.activeNodes()
            .filter(node =>
                node.id !== coordinatorId &&
                this.network.connected(coordinatorId, node.id)
            )
            .slice(0, this.replicationFactor - 1)
            .map(node => node.id);

        const acknowledgements = 1 + await this.network.broadcast(
            coordinatorId,
            targets,
            {
                type: MessageType.REPLICATION,
                payload: record
            }
        );

        if (acknowledgements < required) {
            throw new QuorumError(
                `Required ${required}, received ${acknowledgements}`
            );
        }

        return {
            record,
            acknowledgements,
            consistency
        };
    }

    async get(key, consistency = Consistency.QUORUM) {
        const required = this.requiredAcknowledgements(consistency);

        const replicas = this.activeNodes()
            .map(node => node.get(key))
            .filter(Boolean);

        if (replicas.length < required) {
            throw new QuorumError('Insufficient available replicas');
        }

        const latest = replicas.reduce((best, current) =>
            compareVersions(current.version, best.version) > 0
                ? current
                : best
        );

        if (consistency !== Consistency.ONE) {
            await this.repair(key, latest);
        }

        return clone(latest);
    }

    async repair(key, latest) {
        const operations = [];

        for (const node of this.activeNodes()) {
            if (this.network.connected(
                latest.version.nodeId,
                node.id
            )) {
                node.apply(latest);
            }
        }

        return operations.length;
    }

    async antiEntropy() {
        const active = this.activeNodes();

        // A snapshot is taken before synchronization so that each
        // transfer has a consistent source state.
        const snapshots = new Map(
            active.map(node => [node.id, node.snapshot()])
        );

        for (const source of active) {
            for (const target of active) {
                if (
                    source.id === target.id ||
                    !this.network.connected(source.id, target.id)
                ) {
                    continue;
                }

                const records = Object.values(snapshots.get(source.id));

                await this.network.transmit({
                    messageId: randomUUID(),
                    sender: source.id,
                    receiver: target.id,
                    type: MessageType.SYNC,
                    payload: records
                });
            }
        }
    }

    stopNode(id) {
        const node = this.nodes.get(id);

        if (!node) {
            throw new NodeError(`Unknown node: ${id}`);
        }

        node.status = NodeStatus.STOPPED;
    }

    startNode(id) {
        const node = this.nodes.get(id);

        if (!node) {
            throw new NodeError(`Unknown node: ${id}`);
        }

        node.status = NodeStatus.ACTIVE;
    }

    isConverged() {
        const nodes = this.activeNodes();

        if (nodes.length < 2) {
            return true;
        }

        const expected = JSON.stringify(nodes[0].snapshot());

        return nodes.every(
            node => JSON.stringify(node.snapshot()) === expected
        );
    }

    report() {
        return {
            replicationFactor: this.replicationFactor,
            quorum: this.quorum,
            nodes: Object.fromEntries(
                [...this.nodes.entries()].map(([id, node]) => [
                    id,
                    {
                        status: node.status,
                        records: node.store.size,
                        clock: node.clock,
                        metrics: node.metrics
                    }
                ])
            ),
            network: this.network.metrics,
            converged: this.isConverged()
        };
    }
}

// ============================================================
// FAILURE DETECTOR
// ============================================================

class FailureDetector {

    constructor(timeoutMs = 5000) {
        if (timeoutMs <= 0) {
            throw new RangeError('Timeout must be positive');
        }

        this.timeoutMs = timeoutMs;
        this.lastHeartbeat = new Map();
    }

    record(nodeId, timestamp = Date.now()) {
        this.lastHeartbeat.set(nodeId, timestamp);
    }

    detect(now = Date.now()) {
        const suspected = [];

        for (const [nodeId, lastSeen] of this.lastHeartbeat) {
            if (now - lastSeen > this.timeoutMs) {
                suspected.push(nodeId);
            }
        }

        return suspected;
    }
}

// ============================================================
// INTEGRATION TESTS
// ============================================================

async function runTests() {
    const cluster = new DistributedCluster([
        'node-A',
        'node-B',
        'node-C'
    ]);

    const result = await cluster.put(
        'node-A',
        'customer:1001',
        { name: 'Customer A', balance: 10000 }
    );

    console.assert(result.acknowledgements === 3);

    const read = await cluster.get('customer:1001');

    console.assert(read.value.balance === 10000);
    console.assert(cluster.isConverged());

    // Duplicate messages are ignored.
    const nodeB = cluster.nodes.get('node-B');

    const duplicateMessage = {
        messageId: 'test-id',
        sender: 'node-A',
        receiver: 'node-B',
        type: MessageType.HEARTBEAT,
        payload: {}
    };

    await nodeB.receive(duplicateMessage);
    await nodeB.receive(duplicateMessage);

    console.assert(nodeB.metrics.duplicates === 1);

    // Partition isolates one node.
    cluster.network.partition('node-A', 'node-B');
    cluster.network.partition('node-A', 'node-C');

    let quorumFailed = false;

    try {
        await cluster.put(
            'node-A',
            'customer:1001',
            { balance: 5000 }
        );
    } catch (error) {
        quorumFailed = error instanceof QuorumError;
    }

    console.assert(quorumFailed);

    // Recovery and anti-entropy.
    cluster.network.heal();
    await cluster.antiEntropy();

    console.assert(cluster.isConverged());

    // Node restart.
    cluster.stopNode('node-C');
    cluster.startNode('node-C');

    await cluster.antiEntropy();

    console.assert(cluster.isConverged());

    // Failure detector.
    const detector = new FailureDetector(5000);

    detector.record('node-A', 1000);

    console.assert(detector.detect(7000).includes('node-A'));

    console.log('All JavaScript distributed-system tests passed.');
}

// ============================================================
// EXECUTION
// ============================================================

async function main() {
    console.log('DISTRIBUTED SYSTEMS: EVENT-DRIVEN SIMULATION');

    await runTests();

    const cluster = new DistributedCluster([
        'region-1-node-1',
        'region-1-node-2',
        'region-2-node-1',
        'region-2-node-2',
        'region-3-node-1'
    ]);

    console.log('\n1. Writing distributed state');

    await cluster.put(
        'region-1-node-1',
        'order:5001',
        {
            orderId: 5001,
            status: 'PROCESSING',
            amount: 4500,
            region: 'India'
        },
        Consistency.QUORUM
    );

    console.log('\n2. Reading replicated state');

    console.log(
        await cluster.get('order:5001', Consistency.QUORUM)
    );

    console.log('\n3. Simulating regional partition');

    cluster.network.partition(
        'region-1-node-1',
        'region-2-node-1'
    );

    console.log('\n4. Recovering network');

    cluster.network.heal();

    await cluster.antiEntropy();

    console.log('\n5. Operational report');

    console.log(JSON.stringify(cluster.report(), null, 2));
}

main().catch(error => {
    console.error('Distributed system execution failed:', error);
    process.exitCode = 1;
});
