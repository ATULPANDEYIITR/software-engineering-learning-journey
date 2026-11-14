'use strict';

/**
 * Environment Management
 * Event-driven release orchestration using Node.js.
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 *
 * Focus:
 * - Asynchronous deployment lifecycle
 * - Environment-specific policies
 * - Immutable artifact promotion
 * - Deployment event handling
 * - Concurrent deployment protection
 * - Health verification
 * - Rollback
 */

const { EventEmitter } = require('node:events');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const ENVIRONMENTS = Object.freeze({
    DEVELOPMENT: 'development',
    TESTING: 'testing',
    STAGING: 'staging',
    PRODUCTION: 'production'
});

const DEPLOYMENT_STATES = Object.freeze({
    PENDING: 'pending',
    VALIDATING: 'validating',
    DEPLOYED: 'deployed',
    FAILED: 'failed',
    ROLLED_BACK: 'rolled_back'
});

const PROMOTION_ORDER = Object.freeze([
    ENVIRONMENTS.DEVELOPMENT,
    ENVIRONMENTS.TESTING,
    ENVIRONMENTS.STAGING,
    ENVIRONMENTS.PRODUCTION
]);

const POLICIES = Object.freeze({
    development: {
        debug: true,
        replicas: 1,
        minimumHealthy: 1,
        approvalRequired: false,
        requiredChecks: [],
        secretsRequired: false,
        httpsRequired: false
    },
    testing: {
        debug: false,
        replicas: 1,
        minimumHealthy: 1,
        approvalRequired: false,
        requiredChecks: [
            'unit_tests',
            'integration_tests',
            'security_scan'
        ],
        secretsRequired: true,
        httpsRequired: true
    },
    staging: {
        debug: false,
        replicas: 2,
        minimumHealthy: 2,
        approvalRequired: true,
        requiredChecks: [
            'unit_tests',
            'integration_tests',
            'security_scan',
            'smoke_tests'
        ],
        secretsRequired: true,
        httpsRequired: true
    },
    production: {
        debug: false,
        replicas: 3,
        minimumHealthy: 3,
        approvalRequired: true,
        requiredChecks: [
            'unit_tests',
            'integration_tests',
            'security_scan',
            'smoke_tests',
            'load_tests'
        ],
        secretsRequired: true,
        httpsRequired: true
    }
});

class EnvironmentError extends Error {}
class ValidationError extends EnvironmentError {}
class PolicyError extends EnvironmentError {}
class DeploymentError extends EnvironmentError {}
class ConcurrencyError extends EnvironmentError {}

function createArtifact(version, commit, contents) {
    if (!/^\d+\.\d+\.\d+$/.test(version)) {
        throw new ValidationError('Invalid semantic version.');
    }

    if (!/^[a-f0-9]{7,64}$/.test(commit)) {
        throw new ValidationError('Invalid source commit.');
    }

    if (!Buffer.isBuffer(contents) || contents.length === 0) {
        throw new ValidationError('Artifact contents must be nonempty bytes.');
    }

    const digest = crypto
        .createHash('sha256')
        .update(contents)
        .digest('hex');

    return Object.freeze({
        id: `artifact-${digest.slice(0, 12)}`,
        version,
        commit,
        digest,
        createdAt: new Date().toISOString()
    });
}

class EnvironmentRegistry {
    constructor() {
        this.environments = new Map();

        for (const name of PROMOTION_ORDER) {
            this.environments.set(name, {
                name,
                available: true,
                activeDeployment: null,
                history: []
            });
        }
    }

    get(name) {
        const state = this.environments.get(name);

        if (!state) {
            throw new ValidationError(`Unknown environment: ${name}`);
        }

        return state;
    }

    setAvailability(name, available) {
        if (typeof available !== 'boolean') {
            throw new ValidationError('Availability must be boolean.');
        }

        this.get(name).available = available;
    }
}

class DeploymentPolicy {
    constructor() {
        this.policies = POLICIES;
    }

    evaluate(environment, input) {
        const policy = this.policies[environment];

        if (!policy) {
            throw new ValidationError('Unknown deployment environment.');
        }

        const failures = [];

        if (input.debug !== policy.debug) {
            failures.push('Environment debug configuration mismatch.');
        }

        if (input.replicas < policy.minimumHealthy) {
            failures.push('Insufficient configured replicas.');
        }

        if (policy.httpsRequired && !input.url.startsWith('https://')) {
            failures.push('HTTPS is required.');
        }

        if (policy.secretsRequired) {
            const required = [
                `${environment.toUpperCase()}_DATABASE_PASSWORD`,
                `${environment.toUpperCase()}_APPLICATION_SECRET`
            ];

            for (const key of required) {
                if (!input.secrets?.has(key)) {
                    failures.push(`Missing secret: ${key}`);
                }
            }
        }

        for (const check of policy.requiredChecks) {
            if (input.checks?.get(check) !== true) {
                failures.push(`Required check failed: ${check}`);
            }
        }

        if (policy.approvalRequired && !input.approver) {
            failures.push('Independent approval is required.');
        }

        if (
            input.approver &&
            input.approver === input.deployer
        ) {
            failures.push('Approver and deployer must be different.');
        }

        if (
            environment === ENVIRONMENTS.PRODUCTION &&
            input.debug
        ) {
            failures.push('Production debugging is prohibited.');
        }

        return Object.freeze({
            allowed: failures.length === 0,
            failures
        });
    }
}

class DeploymentCoordinator extends EventEmitter {
    constructor() {
        super();

        this.registry = new EnvironmentRegistry();
        this.policy = new DeploymentPolicy();

        this.artifacts = new Map();
        this.inFlight = new Set();

        this.sequence = 0;
        this.deploymentMutexes = new Map();
    }

    registerArtifact(artifact) {
        if (this.artifacts.has(artifact.id)) {
            const existing = this.artifacts.get(artifact.id);

            if (existing.digest !== artifact.digest) {
                throw new ValidationError('Artifact digest conflict.');
            }

            return;
        }

        this.artifacts.set(artifact.id, artifact);
        this.emit('artifact:registered', artifact);
    }

    async acquireLock(environment) {
        // A Promise chain serializes deployment operations per environment.
        const previous = this.deploymentMutexes.get(environment)
            || Promise.resolve();

        let release;

        const current = new Promise(resolve => {
            release = resolve;
        });

        this.deploymentMutexes.set(
            environment,
            previous.then(() => current)
        );

        await previous;

        return release;
    }

    validatePromotion(artifact, target) {
        const targetIndex = PROMOTION_ORDER.indexOf(target);

        if (targetIndex < 0) {
            throw new ValidationError('Unknown promotion target.');
        }

        if (targetIndex === 0) {
            return;
        }

        const previousEnvironment = PROMOTION_ORDER[targetIndex - 1];
        const previousState = this.registry.get(previousEnvironment);

        if (
            !previousState.activeDeployment ||
            previousState.activeDeployment.artifact.id !== artifact.id
        ) {
            throw new PolicyError(
                `Artifact must be deployed successfully in ${previousEnvironment}.`
            );
        }
    }

    async deploy(artifactId, environment, options = {}) {
        const artifact = this.artifacts.get(artifactId);

        if (!artifact) {
            throw new DeploymentError('Artifact not registered.');
        }

        const state = this.registry.get(environment);
        const policy = POLICIES[environment];

        if (this.inFlight.has(environment)) {
            throw new ConcurrencyError(
                `Deployment already running in ${environment}.`
            );
        }

        this.inFlight.add(environment);
        const release = await this.acquireLock(environment);

        let deployment;

        try {
            if (!state.available) {
                throw new DeploymentError('Environment unavailable.');
            }

            this.validatePromotion(artifact, environment);

            const input = {
                debug: options.debug ?? policy.debug,
                replicas: options.replicas ?? policy.replicas,
                url: options.url ?? (
                    environment === 'development'
                        ? 'http://localhost:8000'
                        : `https://${environment}.example.com`
                ),
                checks: options.checks ?? new Map(),
                secrets: options.secrets ?? new Set(),
                deployer: options.deployer ?? 'ci-pipeline',
                approver: options.approver ?? null
            };

            const evaluation = this.policy.evaluate(
                environment,
                input
            );

            if (!evaluation.allowed) {
                throw new PolicyError(
                    evaluation.failures.join('; ')
                );
            }

            deployment = {
                id: `DEP-${String(++this.sequence).padStart(5, '0')}`,
                artifact,
                environment,
                deployer: input.deployer,
                approver: input.approver,
                status: DEPLOYMENT_STATES.VALIDATING,
                createdAt: new Date().toISOString(),
                previousDeployment: state.activeDeployment?.id ?? null,
                failure: null
            };

            state.history.push(deployment);

            this.emit('deployment:started', deployment);

            // Real deployments replace this simulation with infrastructure
            // adapters and actual readiness probes.
            const healthyReplicas = await this.verifyHealth(
                environment,
                input.replicas,
                policy.minimumHealthy
            );

            if (!state.available) {
                throw new DeploymentError(
                    'Environment became unavailable during deployment.'
                );
            }

            deployment.healthyReplicas = healthyReplicas;
            deployment.status = DEPLOYMENT_STATES.DEPLOYED;

            state.activeDeployment = deployment;

            this.emit('deployment:succeeded', deployment);

            return deployment;

        } catch (error) {
            if (deployment) {
                deployment.status = DEPLOYMENT_STATES.FAILED;
                deployment.failure = error.message;

                this.emit('deployment:failed', {
                    deployment,
                    error
                });
            }

            throw error;

        } finally {
            this.inFlight.delete(environment);
            release();
        }
    }

    async verifyHealth(environment, replicas, minimumHealthy) {
        await new Promise(resolve => setImmediate(resolve));

        const state = this.registry.get(environment);

        if (!state.available || replicas < minimumHealthy) {
            throw new DeploymentError('Health verification failed.');
        }

        return replicas;
    }

    async rollback(environment, requestedBy) {
        const release = await this.acquireLock(environment);

        try {
            const state = this.registry.get(environment);

            if (!requestedBy?.trim()) {
                throw new ValidationError('Rollback actor required.');
            }

            const current = state.activeDeployment;

            if (!current) {
                throw new DeploymentError('No active deployment.');
            }

            const previous = [...state.history]
                .reverse()
                .find(item =>
                    item.id !== current.id &&
                    item.status === DEPLOYMENT_STATES.DEPLOYED
                );

            if (!previous) {
                throw new DeploymentError('No successful rollback target.');
            }

            current.status = DEPLOYMENT_STATES.ROLLED_BACK;
            state.activeDeployment = previous;

            this.emit('deployment:rolled_back', {
                environment,
                previous,
                current,
                requestedBy
            });

            return previous;

        } finally {
            release();
        }
    }

    report() {
        return [...this.registry.environments.values()].map(state => ({
            environment: state.name,
            available: state.available,
            activeDeployment: state.activeDeployment?.id ?? null,
            activeVersion: state.activeDeployment?.artifact.version ?? null,
            historyCount: state.history.length
        }));
    }
}

function successfulChecks() {
    return new Map([
        ['unit_tests', true],
        ['integration_tests', true],
        ['security_scan', true],
        ['smoke_tests', true],
        ['load_tests', true]
    ]);
}

function requiredSecrets(environment) {
    const prefix = environment.toUpperCase();

    return new Set([
        `${prefix}_DATABASE_PASSWORD`,
        `${prefix}_APPLICATION_SECRET`
    ]);
}

async function main() {
    const manager = new DeploymentCoordinator();

    manager.on('deployment:succeeded', deployment => {
        console.log(
            `[SUCCESS] ${deployment.id} -> ${deployment.environment}`
        );
    });

    manager.on('deployment:failed', ({ deployment, error }) => {
        console.error(
            `[FAILED] ${deployment.id}: ${error.message}`
        );
    });

    const artifact1 = createArtifact(
        '1.0.0',
        'a1b2c3d4e5f6',
        Buffer.from('release-1.0.0')
    );

    const artifact2 = createArtifact(
        '1.1.0',
        'b2c3d4e5f6a7',
        Buffer.from('release-1.1.0')
    );

    manager.registerArtifact(artifact1);

    await manager.deploy(artifact1.id, 'development', {
        deployer: 'developer-01'
    });

    for (const environment of ['testing', 'staging', 'production']) {
        await manager.deploy(artifact1.id, environment, {
            deployer: 'release-engineer',
            approver: environment === 'testing'
                ? null
                : 'independent-manager',
            checks: successfulChecks(),
            secrets: requiredSecrets(environment)
        });
    }

    manager.registerArtifact(artifact2);

    await manager.deploy(artifact2.id, 'development');

    await manager.deploy(artifact2.id, 'testing', {
        checks: successfulChecks(),
        secrets: requiredSecrets('testing')
    });

    await manager.deploy(artifact2.id, 'staging', {
        checks: successfulChecks(),
        secrets: requiredSecrets('staging'),
        approver: 'qa-manager'
    });

    await manager.deploy(artifact2.id, 'production', {
        checks: successfulChecks(),
        secrets: requiredSecrets('production'),
        approver: 'production-manager'
    });

    console.log('\nROLLBACK');

    const rollback = await manager.rollback(
        'production',
        'incident-commander'
    );

    console.log('Restored artifact:', rollback.artifact.version);

    console.log('\nENVIRONMENT REPORT');

    console.table(manager.report());

    // Demonstrate policy rejection.
    const rejected = manager.policy.evaluate('production', {
        debug: true,
        replicas: 1,
        url: 'http://localhost:8000',
        checks: new Map(),
        secrets: new Set(),
        deployer: 'developer-01',
        approver: 'developer-01'
    });

    assert.equal(rejected.allowed, false);

    console.log('\nEXPECTED POLICY REJECTION');
    console.log(rejected.failures);
}

main().catch(error => {
    console.error('Environment management error:', error.message);
    process.exitCode = 1;
});
