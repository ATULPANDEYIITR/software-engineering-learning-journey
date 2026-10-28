'use strict';

const { EventEmitter } = require('node:events');
const { performance } = require('node:perf_hooks');

class CacheError extends Error {}
class CacheMissError extends CacheError {}
class CacheSourceError extends Error {}

class TTLCache extends EventEmitter {
    constructor({ defaultTtlMs = 5000, maxEntries = 1000 } = {}) {
        super();

        if (!Number.isFinite(defaultTtlMs) || defaultTtlMs <= 0) {
            throw new TypeError('defaultTtlMs must be positive');
        }
        if (!Number.isInteger(maxEntries) || maxEntries <= 0) {
            throw new TypeError('maxEntries must be a positive integer');
        }

        this.defaultTtlMs = defaultTtlMs;
        this.maxEntries = maxEntries;
        this.entries = new Map();

        this.metrics = {
            hits: 0,
            misses: 0,
            stale: 0,
            puts: 0,
            invalidations: 0
        };
    }

    #now() {
        return performance.now();
    }

    #validateKey(key) {
        if (typeof key !== 'string' || key.trim() === '') {
            throw new TypeError('Cache key must be a non-empty string');
        }
    }

    #evictIfNeeded() {
        if (this.entries.size < this.maxEntries) {
            return;
        }

        for (const [key, entry] of this.entries) {
            if (entry.expiresAt <= this.#now()) {
                this.entries.delete(key);
            }
        }

        while (this.entries.size >= this.maxEntries) {
            const oldest = this.entries.keys().next().value;
            this.entries.delete(oldest);
        }
    }

    get(key) {
        this.#validateKey(key);

        const entry = this.entries.get(key);

        if (!entry) {
            this.metrics.misses++;
            this.emit('miss', { key, reason: 'absent' });
            throw new CacheMissError(key);
        }

        if (entry.expiresAt <= this.#now()) {
            this.entries.delete(key);
            this.metrics.misses++;
            this.metrics.stale++;
            this.emit('stale', { key, version: entry.version });
            throw new CacheMissError(key);
        }

        this.metrics.hits++;
        this.emit('hit', {
            key,
            version: entry.version,
            remainingTtlMs: entry.expiresAt - this.#now()
        });

        return structuredClone(entry.value);
    }

    set(key, value, { ttlMs = this.defaultTtlMs, tags = [] } = {}) {
        this.#validateKey(key);

        if (!Number.isFinite(ttlMs) || ttlMs <= 0) {
            throw new TypeError('TTL must be positive');
        }

        if (!Array.isArray(tags)) {
            throw new TypeError('tags must be an array');
        }

        this.#evictIfNeeded();

        const previous = this.entries.get(key);
        const entry = {
            value: structuredClone(value),
            createdAt: this.#now(),
            expiresAt: this.#now() + ttlMs,
            version: previous ? previous.version + 1 : 1,
            tags: new Set(tags)
        };

        this.entries.set(key, entry);
        this.metrics.puts++;

        this.emit('set', {
            key,
            version: entry.version,
            ttlMs
        });

        return structuredClone(entry.value);
    }

    invalidate(key) {
        this.#validateKey(key);

        const existed = this.entries.delete(key);
        if (existed) {
            this.metrics.invalidations++;
            this.emit('invalidate', { key, reason: 'explicit' });
        }

        return existed;
    }

    invalidateByTag(tag) {
        if (typeof tag !== 'string' || tag.trim() === '') {
            throw new TypeError('Tag must be a non-empty string');
        }

        let count = 0;

        for (const [key, entry] of this.entries) {
            if (entry.tags.has(tag)) {
                this.entries.delete(key);
                count++;
            }
        }

        this.metrics.invalidations += count;

        if (count > 0) {
            this.emit('invalidateTag', { tag, count });
        }

        return count;
    }

    clear() {
        const count = this.entries.size;
        this.entries.clear();
        this.metrics.invalidations += count;
        this.emit('clear', { count });
    }

    snapshot() {
        return {
            entries: this.entries.size,
            ...this.metrics
        };
    }
}

class UserRepository {
    constructor() {
        this.users = new Map([
            [
                'user:101',
                { id: 101, name: 'Atul', role: 'developer', version: 1 }
            ],
            [
                'user:102',
                { id: 102, name: 'Priya', role: 'reviewer', version: 1 }
            ]
        ]);
    }

    async get(key) {
        await new Promise(resolve => setTimeout(resolve, 15));

        const user = this.users.get(key);
        if (!user) {
            throw new CacheSourceError(`User does not exist: ${key}`);
        }

        return structuredClone(user);
    }

    async update(key, changes) {
        await new Promise(resolve => setTimeout(resolve, 15));

        const current = this.users.get(key);
        if (!current) {
            throw new CacheSourceError(`Cannot update missing user: ${key}`);
        }

        const updated = {
            ...current,
            ...changes,
            version: current.version + 1
        };

        this.users.set(key, updated);
        return structuredClone(updated);
    }
}

class UserService {
    constructor(repository, cache, ttlMs = 2000) {
        this.repository = repository;
        this.cache = cache;
        this.ttlMs = ttlMs;
    }

    async getUser(id) {
        const key = `user:${id}`;

        try {
            return this.cache.get(key);
        } catch (error) {
            if (!(error instanceof CacheMissError)) {
                throw error;
            }
        }

        const sourceValue = await this.repository.get(key);

        this.cache.set(key, sourceValue, {
            ttlMs: this.ttlMs,
            tags: [`user:${id}`, 'users']
        });

        return sourceValue;
    }

    async updateUser(id, changes) {
        if (!Number.isInteger(id) || id <= 0) {
            throw new TypeError('User ID must be a positive integer');
        }

        const key = `user:${id}`;

        // The source of truth is updated first. The cached representation is
        // invalidated after a successful source update.
        const updated = await this.repository.update(key, changes);
        this.cache.invalidate(key);

        return updated;
    }
}

async function run() {
    const cache = new TTLCache({
        defaultTtlMs: 1000,
        maxEntries: 100
    });

    cache.on('hit', event => {
        console.log('CACHE HIT', event.key, `v${event.version}`);
    });

    cache.on('miss', event => {
        console.log('CACHE MISS', event.key, event.reason);
    });

    cache.on('stale', event => {
        console.log('CACHE STALE', event.key, `v${event.version}`);
    });

    const repository = new UserRepository();
    const service = new UserService(repository, cache, 1000);

    console.log('First read:', await service.getUser(101));
    console.log('Second read:', await service.getUser(101));

    console.log('Metrics:', cache.snapshot());

    await service.updateUser(101, { role: 'senior-developer' });

    console.log('After explicit invalidation:', await service.getUser(101));

    console.log('Waiting for TTL expiration...');
    await new Promise(resolve => setTimeout(resolve, 1100));

    console.log('After TTL expiration:', await service.getUser(101));

    await service.getUser(102);
    console.log('Invalidated by tag:', cache.invalidateByTag('users'));

    try {
        await service.getUser(999);
    } catch (error) {
        console.log('Expected source failure:', error.message);
    }

    console.log('Final metrics:', cache.snapshot());
}

async function runTests() {
    const cache = new TTLCache({ defaultTtlMs: 50, maxEntries: 2 });

    cache.set('a', { value: 10 });
    if (cache.get('a').value !== 10) {
        throw new Error('Cache hit test failed');
    }

    cache.invalidate('a');

    try {
        cache.get('a');
        throw new Error('Expected cache miss');
    } catch (error) {
        if (!(error instanceof CacheMissError)) {
            throw error;
        }
    }

    cache.set('x', 1, { tags: ['group'] });
    cache.set('y', 2, { tags: ['group'] });

    if (cache.invalidateByTag('group') !== 2) {
        throw new Error('Tag invalidation test failed');
    }

    console.log('Self-tests passed');
}

runTests()
    .then(run)
    .catch(error => {
        console.error('Fatal error:', error);
        process.exitCode = 1;
    });
