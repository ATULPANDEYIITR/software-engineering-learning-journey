'use strict';

const { EventEmitter } = require('node:events');
const { randomUUID } = require('node:crypto');

const Consistency = Object.freeze({
    STRONG: 'strong',
    EVENTUAL: 'eventual',
    CAUSAL: 'causal'
});

class ConsistencyError extends Error {}
class ReplicaUnavailableError extends ConsistencyError {}
class DependencyError extends ConsistencyError {}
class ConflictError extends ConsistencyError {}

function validateValue(value) {
    try {
        const serialized = JSON.stringify(value);
        if (serialized === undefined) {
            throw new Error('Unsupported value');
        }
    } catch {
        throw new TypeError('Value must be JSON serializable.');
    }
}

function compareClocks(a, b) {
    let aGreater = false;
    let bGreater = false;

    const keys = new Set([...a.keys(), ...b.keys()]);

    for (const key of keys) {
        const x = a.get(key) || 0;
        const y = b.get(key) || 0;

        if (x > y) aGreater = true;
        if (y > x) bGreater = true;
    }

    if (aGreater && bGreater) return 'concurrent';
    if (aGreater) return 'after';
    if (bGreater) return 'before';
    return 'equal';
}

function mergeClocks(a, b) {
    const result = new Map(a);

    for (const [node, count] of b) {
        result.set(node, Math.max(result.get(node) || 0, count));
    }

    return result;
}

function cloneEvent(event) {
    return {
        ...event,
        value: structuredClone(event.value),
        clock: new Map(event.clock),
        dependencies: new Map(event.dependencies)
    };
}

class Replica {
    constructor(id) {
        this.id = id;
        this.online = true;
        this.data = new Map();
        this.clock = new Map();
        this.queue = [];
    }

    increment(clock) {
        const next = new Map(clock);
        next.set(this.id, (next.get(this.id) || 0) + 1);
        return next;
    }

    apply(event) {
        const current = this.data.get(event.key);

        if (current) {
            const relation = compareClocks(current.clock, event.clock);

            if (relation === 'after' || relation === 'equal') {
                return false;
            }

            if (relation === 'concurrent') {
                // Deterministic conflict resolution, not a substitute
                // for domain-specific conflict-free data types.
                if (
                    current.timestamp > event.timestamp ||
                    (
                        current.timestamp === event.timestamp &&
                        current.origin >= event.origin
                    )
                ) {
                    return false;
                }
            }
        }

        this.data.set(event.key, cloneEvent(event));
        this.clock = mergeClocks(this.clock, event.clock);
        return true;
    }

    get(key) {
        return this.data.get(key);
    }
}

class DistributedStore extends EventEmitter {
    constructor(replicaIds, options = {}) {
        super();

        if (!Array.isArray(replicaIds) || replicaIds.length < 2) {
            throw new TypeError('At least two replica IDs are required.');
        }

        if (new Set(replicaIds).size !== replicaIds.length) {
            throw new TypeError('Replica IDs must be unique.');
        }

        if (replicaIds.some(
            id => typeof id !== 'string' || id.trim() === ''
        )) {
            throw new TypeError('Replica IDs must be non-empty strings.');
        }

        this.replicas = new Map(
            replicaIds.map(id => [id, new Replica(id)])
        );

        this.mode = options.mode || Consistency.EVENTUAL;
        this.pendingLimit = options.pendingLimit || 10000;
        this.events = new Map();
        this.sequence = 0;
        this.mutex = Promise.resolve();

        this.validateMode(this.mode);
    }

    validateMode(mode) {
        if (!Object.values(Consistency).includes(mode)) {
            throw new TypeError(`Unknown consistency model: ${mode}`);
        }
    }

    getReplica(id) {
        const replica = this.replicas.get(id);

        if (!replica) {
            throw new RangeError(`Unknown replica: ${id}`);
        }

        return replica;
    }

    async exclusive(operation) {
        // Serialize state-changing operations inside this process.
        const previous = this.mutex;
        let release;

        this.mutex = new Promise(resolve => {
            release = resolve;
        });

        await previous;

        try {
            return await operation();
        } finally {
            release();
        }
    }

    setMode(mode) {
        this.validateMode(mode);
        this.mode = mode;
        this.emit('modeChanged', mode);
    }

    setOnline(id, online) {
        const replica = this.getReplica(id);
        replica.online = Boolean(online);
        this.emit('availabilityChanged', {
            replica: id,
            online: replica.online
        });
    }

    createEvent(replica, key, value, context) {
        const merged = mergeClocks(replica.clock, context || new Map());
        const clock = replica.increment(merged);

        this.sequence += 1;

        return {
            id: randomUUID(),
            key,
            value: structuredClone(value),
            origin: replica.id,
            clock,
            dependencies: new Map(merged),
            timestamp: Date.now() + this.sequence / 1000000
        };
    }

    async write(id, key, value, context = new Map()) {
        if (typeof key !== 'string' || !key.trim() || key.length > 200) {
            throw new TypeError('Key must contain 1 to 200 characters.');
        }

        if (!(context instanceof Map)) {
            throw new TypeError('Causal context must be a Map.');
        }

        validateValue(value);

        return this.exclusive(async () => {
            const origin = this.getReplica(id);

            if (!origin.online) {
                throw new ReplicaUnavailableError(`${id} is offline.`);
            }

            if (this.mode === Consistency.CAUSAL) {
                if (compareClocks(origin.clock, context) === 'before') {
                    throw new DependencyError(
                        'Origin has not observed the causal context.'
                    );
                }
            }

            const event = this.createEvent(origin, key, value, context);

            if (this.mode === Consistency.STRONG) {
                const unavailable = [...this.replicas.values()]
                    .filter(replica => !replica.online);

                if (unavailable.length > 0) {
                    throw new ReplicaUnavailableError(
                        'Strong write requires all replicas to be available.'
                    );
                }

                // Check the whole operation before committing.
                for (const replica of this.replicas.values()) {
                    replica.apply(event);
                }
            } else {
                origin.apply(event);
                this.events.set(event.id, event);

                for (const replica of this.replicas.values()) {
                    if (replica.id === id) continue;

                    if (replica.queue.length >= this.pendingLimit) {
                        throw new ConflictError(
                            `Replication queue limit exceeded at ${replica.id}.`
                        );
                    }

                    replica.queue.push(cloneEvent(event));
                }
            }

            this.emit('write', {
                id: event.id,
                key,
                origin: id,
                consistency: this.mode
            });

            return cloneEvent(event);
        });
    }

    async read(id, key, context = null) {
        return this.exclusive(async () => {
            const replica = this.getReplica(id);

            if (!replica.online) {
                throw new ReplicaUnavailableError(`${id} is offline.`);
            }

            let event = replica.get(key);

            if (this.mode === Consistency.STRONG) {
                event = this.getStrongValue(key);
            }

            if (!event) return null;

            if (
                context &&
                compareClocks(event.clock, context) === 'before'
            ) {
                throw new DependencyError(
                    'Read does not satisfy the supplied causal context.'
                );
            }

            return structuredClone(event.value);
        });
    }

    getStrongValue(key) {
        const values = [...this.replicas.values()]
            .map(replica => replica.get(key))
            .filter(Boolean);

        if (values.length === 0) return null;

        return values.reduce((latest, candidate) => {
            if (
                compareClocks(candidate.clock, latest.clock) === 'after'
            ) {
                return candidate;
            }

            return latest;
        });
    }

    async replicate() {
        return this.exclusive(async () => {
            let applied = 0;

            for (const replica of this.replicas.values()) {
                if (!replica.online) continue;

                let progress = true;

                while (progress && replica.queue.length > 0) {
                    progress = false;
                    const remaining = [];

                    for (const event of replica.queue) {
                        if (this.mode === Consistency.CAUSAL) {
                            if (
                                compareClocks(
                                    replica.clock,
                                    event.dependencies
                                ) === 'before'
                            ) {
                                remaining.push(event);
                                continue;
                            }
                        }

                        if (replica.apply(event)) {
                            applied++;
                        }

                        progress = true;
                    }

                    replica.queue = remaining;
                }
            }

            this.emit('replication', { applied });
            return applied;
        });
    }

    inspect(key) {
        return [...this.replicas.values()].map(replica => {
            const event = replica.get(key);

            return {
                replica: replica.id,
                online: replica.online,
                value: event ? event.value : null,
                clock: event
                    ? Object.fromEntries(event.clock)
                    : {},
                queued: replica.queue.length
            };
        });
    }

    convergence(key) {
        const rows = this.inspect(key);
        const values = rows.map(row => JSON.stringify(row.value));

        return {
            key,
            converged: values.every(value => value === values[0]),
            replicas: rows
        };
    }
}

async function demonstrate() {
    const store = new DistributedStore(
        ['mumbai', 'delhi', 'singapore']
    );

    store.on('write', event => {
        console.log('WRITE:', event);
    });

    store.on('replication', event => {
        console.log('REPLICATION:', event);
    });

    console.log('\n1. STRONG CONSISTENCY');

    store.setMode(Consistency.STRONG);

    await store.write('mumbai', 'account:1', {
        balance: 25000,
        currency: 'INR'
    });

    console.log(
        'Read from Delhi:',
        await store.read('delhi', 'account:1')
    );

    store.setOnline('singapore', false);

    try {
        await store.write('mumbai', 'account:1', {
            balance: 20000
        });
    } catch (error) {
        console.log('Expected rejection:', error.message);
    }

    store.setOnline('singapore', true);

    console.log('\n2. EVENTUAL CONSISTENCY');

    store.setMode(Consistency.EVENTUAL);

    await store.write('mumbai', 'inventory:1', {
        quantity: 100
    });

    console.log('Before replication:', store.inspect('inventory:1'));

    await store.replicate();

    console.log('After replication:', store.convergence('inventory:1'));

    console.log('\n3. CAUSAL CONSISTENCY');

    store.setMode(Consistency.CAUSAL);

    const first = await store.write(
        'mumbai',
        'order:1',
        { status: 'created' }
    );

    const second = await store.write(
        'mumbai',
        'payment:1',
        { status: 'initiated' },
        first.clock
    );

    console.log('First clock:', Object.fromEntries(first.clock));
    console.log('Second clock:', Object.fromEntries(second.clock));

    await store.replicate();

    console.log(
        'Payment:',
        await store.read('delhi', 'payment:1')
    );

    console.log('\n4. VALIDATION');

    try {
        await store.write('mumbai', '', 'invalid');
    } catch (error) {
        console.log('Invalid key:', error.message);
    }

    try {
        await store.read('unknown', 'order:1');
    } catch (error) {
        console.log('Invalid replica:', error.message);
    }
}

demonstrate().catch(error => {
    console.error('Execution failed:', error);
    process.exitCode = 1;
});
