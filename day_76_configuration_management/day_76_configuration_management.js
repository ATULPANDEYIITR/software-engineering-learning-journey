'use strict';

/**
 * Configuration Management and Policy Evaluation.
 *
 * Node.js 18+
 *
 * Features:
 * - Environment-specific configuration
 * - Typed validation
 * - Secret references and redaction
 * - Asynchronous configuration loading
 * - Immutable configuration snapshots
 * - Event-driven updates
 * - Optimistic concurrency control
 * - Configuration policy evaluation
 * - Atomic file persistence
 */

const fs = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');
const EventEmitter = require('node:events');

class ConfigurationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ConfigurationError';
    }
}

class AuthorizationError extends Error {
    constructor(message) {
        super(message);
        this.name = 'AuthorizationError';
    }
}

class ConflictError extends Error {
    constructor(message) {
        super(message);
        this.name = 'ConflictError';
    }
}

const Environment = Object.freeze({
    DEVELOPMENT: 'development',
    TESTING: 'testing',
    STAGING: 'staging',
    PRODUCTION: 'production'
});

const ConfigType = Object.freeze({
    STRING: 'string',
    INTEGER: 'integer',
    NUMBER: 'number',
    BOOLEAN: 'boolean'
});

function deepFreeze(value) {
    if (value && typeof value === 'object' && !Object.isFrozen(value)) {
        Object.freeze(value);

        for (const child of Object.values(value)) {
            deepFreeze(child);
        }
    }

    return value;
}

function validateName(name) {
    if (
        typeof name !== 'string' ||
        !/^[A-Z][A-Z0-9_]*$/.test(name)
    ) {
        throw new ConfigurationError(
            `Invalid configuration name: ${name}`
        );
    }
}

function parseValue(definition, rawValue) {
    if (rawValue === undefined || rawValue === null) {
        if (definition.required) {
            throw new ConfigurationError(
                `${definition.name} is required`
            );
        }

        return definition.default;
    }

    let value;

    switch (definition.type) {
        case ConfigType.STRING:
            if (typeof rawValue !== 'string') {
                throw new ConfigurationError(
                    `${definition.name} must be a string`
                );
            }
            value = rawValue;
            break;

        case ConfigType.INTEGER:
            if (
                typeof rawValue === 'boolean' ||
                !/^-?\d+$/.test(String(rawValue))
            ) {
                throw new ConfigurationError(
                    `${definition.name} must be an integer`
                );
            }
            value = Number(rawValue);

            if (!Number.isSafeInteger(value)) {
                throw new ConfigurationError(
                    `${definition.name} exceeds safe integer limits`
                );
            }
            break;

        case ConfigType.NUMBER:
            if (
                typeof rawValue === 'boolean' ||
                String(rawValue).trim() === ''
            ) {
                throw new ConfigurationError(
                    `${definition.name} must be numeric`
                );
            }

            value = Number(rawValue);

            if (!Number.isFinite(value)) {
                throw new ConfigurationError(
                    `${definition.name} must be finite`
                );
            }
            break;

        case ConfigType.BOOLEAN:
            if (typeof rawValue === 'boolean') {
                value = rawValue;
            } else {
                const normalized = String(rawValue).toLowerCase();

                if (['true', '1', 'yes'].includes(normalized)) {
                    value = true;
                } else if (
                    ['false', '0', 'no'].includes(normalized)
                ) {
                    value = false;
                } else {
                    throw new ConfigurationError(
                        `${definition.name} must be boolean`
                    );
                }
            }
            break;

        default:
            throw new ConfigurationError(
                `Unsupported type: ${definition.type}`
            );
    }

    if (typeof value === 'number') {
        if (
            definition.minimum !== undefined &&
            value < definition.minimum
        ) {
            throw new ConfigurationError(
                `${definition.name} is below minimum`
            );
        }

        if (
            definition.maximum !== undefined &&
            value > definition.maximum
        ) {
            throw new ConfigurationError(
                `${definition.name} exceeds maximum`
            );
        }
    }

    if (
        definition.choices &&
        !definition.choices.includes(value)
    ) {
        throw new ConfigurationError(
            `${definition.name} has an invalid choice`
        );
    }

    return value;
}

class SchemaRegistry {
    #definitions = new Map();

    register(definition) {
        validateName(definition.name);

        if (this.#definitions.has(definition.name)) {
            throw new ConfigurationError(
                `Duplicate definition: ${definition.name}`
            );
        }

        if (!Object.values(ConfigType).includes(definition.type)) {
            throw new ConfigurationError(
                `Invalid type for ${definition.name}`
            );
        }

        if (
            definition.minimum !== undefined &&
            definition.maximum !== undefined &&
            definition.minimum > definition.maximum
        ) {
            throw new ConfigurationError(
                `Invalid range for ${definition.name}`
            );
        }

        this.#definitions.set(
            definition.name,
            Object.freeze({ ...definition })
        );
    }

    get(name) {
        return this.#definitions.get(name);
    }

    entries() {
        return this.#definitions.entries();
    }
}

class SecretProvider {
    #secrets = new Map();

    async set(name, value) {
        validateName(name);

        if (typeof value !== 'string' || value.length === 0) {
            throw new ConfigurationError(
                'Secret must be a non-empty string'
            );
        }

        this.#secrets.set(name, value);
    }

    async get(name, principal) {
        if (!principal || principal.role !== 'secret-reader') {
            throw new AuthorizationError(
                'Principal is not authorized to read secrets'
            );
        }

        if (!this.#secrets.has(name)) {
            throw new ConfigurationError(
                `Secret not found: ${name}`
            );
        }

        return this.#secrets.get(name);
    }

    has(name) {
        return this.#secrets.has(name);
    }

    toJSON() {
        return {
            storedSecrets: this.#secrets.size,
            values: '[REDACTED]'
        };
    }
}

class ConfigurationPolicy {
    constructor(environment) {
        this.environment = environment;
    }

    evaluate(values) {
        const violations = [];

        if (
            this.environment === Environment.PRODUCTION &&
            values.DEBUG === true
        ) {
            violations.push(
                'Debug mode must be disabled in production'
            );
        }

        if (
            this.environment === Environment.PRODUCTION &&
            values.LOG_LEVEL === 'DEBUG'
        ) {
            violations.push(
                'Debug logging is prohibited in production'
            );
        }

        if (
            values.APP_PORT !== undefined &&
            values.APP_PORT < 1024
        ) {
            violations.push(
                'Application port must be unprivileged'
            );
        }

        if (
            values.DATABASE_POOL_SIZE !== undefined &&
            values.DATABASE_POOL_SIZE > 100
        ) {
            violations.push(
                'Database pool exceeds organizational limit'
            );
        }

        return Object.freeze({
            allowed: violations.length === 0,
            violations: Object.freeze(violations)
        });
    }
}

class ConfigurationManager extends EventEmitter {
    #schema;
    #secrets;
    #policy;
    #values = Object.freeze({});
    #version = 0;
    #environment;

    constructor(schema, secrets, environment) {
        super();

        if (!Object.values(Environment).includes(environment)) {
            throw new ConfigurationError(
                `Unsupported environment: ${environment}`
            );
        }

        this.#schema = schema;
        this.#secrets = secrets;
        this.#environment = environment;
        this.#policy = new ConfigurationPolicy(environment);
    }

    get version() {
        return this.#version;
    }

    get environment() {
        return this.#environment;
    }

    async load(source = process.env) {
        const candidate = {};

        for (const [name, definition] of this.#schema.entries()) {
            if (definition.secret) {
                if (
                    definition.required &&
                    !this.#secrets.has(name)
                ) {
                    throw new ConfigurationError(
                        `Missing required secret: ${name}`
                    );
                }
                continue;
            }

            const raw = Object.hasOwn(source, name)
                ? source[name]
                : undefined;

            const value = parseValue(definition, raw);

            if (value !== undefined) {
                candidate[name] = value;
            }
        }

        const decision = this.#policy.evaluate(candidate);

        if (!decision.allowed) {
            throw new ConfigurationError(
                decision.violations.join('; ')
            );
        }

        this.#values = deepFreeze(candidate);
        this.#version++;

        this.emit('loaded', {
            environment: this.#environment,
            version: this.#version
        });

        return this.snapshot();
    }

    get(name) {
        const definition = this.#schema.get(name);

        if (!definition) {
            throw new ConfigurationError(
                `Unknown setting: ${name}`
            );
        }

        if (definition.secret) {
            throw new AuthorizationError(
                'Use the authorized secret provider'
            );
        }

        if (!Object.hasOwn(this.#values, name)) {
            throw new ConfigurationError(
                `Setting is not loaded: ${name}`
            );
        }

        return this.#values[name];
    }

    async getSecret(name, principal) {
        const definition = this.#schema.get(name);

        if (!definition || !definition.secret) {
            throw new ConfigurationError(
                'Setting is not a registered secret'
            );
        }

        return this.#secrets.get(name, principal);
    }

    async update(changes, expectedVersion) {
        if (expectedVersion !== this.#version) {
            throw new ConflictError(
                `Version conflict: expected ${expectedVersion}, current ${this.#version}`
            );
        }

        const candidate = { ...this.#values };

        for (const [name, rawValue] of Object.entries(changes)) {
            const definition = this.#schema.get(name);

            if (!definition || definition.secret) {
                throw new ConfigurationError(
                    `Invalid update key: ${name}`
                );
            }

            candidate[name] = parseValue(
                definition,
                rawValue
            );
        }

        const decision = this.#policy.evaluate(candidate);

        if (!decision.allowed) {
            throw new ConfigurationError(
                decision.violations.join('; ')
            );
        }

        const previousVersion = this.#version;

        this.#values = deepFreeze(candidate);
        this.#version++;

        this.emit('updated', {
            previousVersion,
            currentVersion: this.#version,
            changedKeys: Object.keys(changes)
        });

        return this.snapshot();
    }

    snapshot() {
        const safe = {};

        for (const [name, definition] of this.#schema.entries()) {
            safe[name] = definition.secret
                ? '[REDACTED]'
                : this.#values[name] ?? null;
        }

        return deepFreeze({
            environment: this.#environment,
            version: this.#version,
            values: safe
        });
    }

    fingerprint() {
        const normalized = JSON.stringify(
            Object.keys(this.#values)
                .sort()
                .reduce((result, key) => {
                    result[key] = this.#values[key];
                    return result;
                }, {})
        );

        return crypto
            .createHash('sha256')
            .update(normalized)
            .digest('hex');
    }

    async persist(filePath) {
        const absolute = path.resolve(filePath);
        const temporary = `${absolute}.${crypto.randomUUID()}.tmp`;

        await fs.mkdir(path.dirname(absolute), {
            recursive: true
        });

        try {
            await fs.writeFile(
                temporary,
                JSON.stringify(this.snapshot(), null, 2),
                {
                    encoding: 'utf8',
                    mode: 0o600,
                    flag: 'wx'
                }
            );

            await fs.rename(temporary, absolute);
        } catch (error) {
            await fs.rm(temporary, { force: true });
            throw error;
        }
    }
}

async function main() {
    const schema = new SchemaRegistry();

    schema.register({
        name: 'APP_NAME',
        type: ConfigType.STRING,
        default: 'OrderService',
        required: true
    });

    schema.register({
        name: 'APP_PORT',
        type: ConfigType.INTEGER,
        default: 8000,
        minimum: 1024,
        maximum: 65535
    });

    schema.register({
        name: 'DEBUG',
        type: ConfigType.BOOLEAN,
        default: false
    });

    schema.register({
        name: 'DATABASE_POOL_SIZE',
        type: ConfigType.INTEGER,
        default: 10,
        minimum: 1,
        maximum: 100
    });

    schema.register({
        name: 'LOG_LEVEL',
        type: ConfigType.STRING,
        default: 'INFO',
        choices: ['DEBUG', 'INFO', 'WARNING', 'ERROR']
    });

    schema.register({
        name: 'DATABASE_PASSWORD',
        type: ConfigType.STRING,
        secret: true,
        required: true
    });

    const secrets = new SecretProvider();

    await secrets.set(
        'DATABASE_PASSWORD',
        'local-example-secret'
    );

    const manager = new ConfigurationManager(
        schema,
        secrets,
        Environment.DEVELOPMENT
    );

    manager.on('loaded', event => {
        console.log('Configuration loaded:', event);
    });

    manager.on('updated', event => {
        console.log('Configuration updated:', event);
    });

    await manager.load({
        APP_NAME: 'OrderService',
        APP_PORT: '8080',
        DEBUG: 'false',
        DATABASE_POOL_SIZE: '15',
        LOG_LEVEL: 'INFO'
    });

    console.log('\nSNAPSHOT');
    console.log(JSON.stringify(manager.snapshot(), null, 2));

    console.log('\nOPTIMISTIC UPDATE');

    await manager.update(
        {
            APP_PORT: '8081',
            DATABASE_POOL_SIZE: '20'
        },
        manager.version
    );

    console.log('New version:', manager.version);

    console.log('\nCONFIGURATION FINGERPRINT');
    console.log(manager.fingerprint());

    console.log('\nSECRET AUTHORIZATION');

    try {
        await manager.getSecret(
            'DATABASE_PASSWORD',
            { role: 'developer' }
        );
    } catch (error) {
        console.log(error.name, error.message);
    }

    const password = await manager.getSecret(
        'DATABASE_PASSWORD',
        { role: 'secret-reader' }
    );

    console.log('Authorized secret retrieved:', Boolean(password));

    console.log('\nINVALID PRODUCTION POLICY');

    const productionPolicy = new ConfigurationPolicy(
        Environment.PRODUCTION
    );

    console.log(
        productionPolicy.evaluate({
            DEBUG: true,
            LOG_LEVEL: 'DEBUG',
            APP_PORT: 8080
        })
    );

    console.log('\nCONCURRENT UPDATE');

    try {
        await manager.update(
            { APP_PORT: 9000 },
            1
        );
    } catch (error) {
        console.log(error.name, error.message);
    }

    console.log('\nPERSISTENCE');

    await manager.persist(
        path.join(process.cwd(), 'configuration-snapshot.json')
    );

    console.log('Safe configuration snapshot written.');
}

main().catch(error => {
    console.error('Configuration failure:', error.message);
    process.exitCode = 1;
});
