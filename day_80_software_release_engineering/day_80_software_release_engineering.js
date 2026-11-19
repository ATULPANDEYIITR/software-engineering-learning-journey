"use strict";

/**
 * Software Release Engineering
 *
 * Event-driven release orchestration with:
 * - Release strategies
 * - Change approval policies
 * - Canary traffic progression
 * - Rolling and blue-green deployments
 * - Health monitoring
 * - Automatic rollback
 * - Deployment event history
 *
 * Runtime: Node.js 18+
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");

// ---------------------------------------------------------
// Domain configuration
// ---------------------------------------------------------

const Strategy = Object.freeze({
    CANARY: "canary",
    ROLLING: "rolling",
    BLUE_GREEN: "blue_green",
    RECREATE: "recreate"
});

const Risk = Object.freeze({
    LOW: "low",
    MEDIUM: "medium",
    HIGH: "high",
    CRITICAL: "critical"
});

const Status = Object.freeze({
    SUBMITTED: "submitted",
    APPROVED: "approved",
    REJECTED: "rejected",
    IMPLEMENTED: "implemented"
});

const ReleaseState = Object.freeze({
    CREATED: "created",
    VALIDATING: "validating",
    DEPLOYING: "deploying",
    SUCCEEDED: "succeeded",
    FAILED: "failed",
    ROLLED_BACK: "rolled_back"
});

const Environment = Object.freeze({
    STAGING: "staging",
    PRODUCTION: "production"
});

const APPROVAL_REQUIREMENTS = Object.freeze({
    low: 1,
    medium: 1,
    high: 2,
    critical: 3
});

const TRAFFIC_PLANS = Object.freeze({
    canary: [5, 10, 25, 50, 100],
    rolling: [25, 50, 75, 100],
    blue_green: [0, 100],
    recreate: [0, 100]
});

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function validateEnum(value, values, field) {
    assert(
        Object.values(values).includes(value),
        `Invalid ${field}: ${value}`
    );
}

// ---------------------------------------------------------
// Immutable artifact model
// ---------------------------------------------------------

class ReleaseArtifact {
    constructor({ version, commit, digest, buildNumber }) {
        assert(typeof version === "string" && version.trim(),
            "Version is required.");

        assert(typeof commit === "string" && commit.length >= 7,
            "Commit hash must contain at least seven characters.");

        assert(/^sha256:[a-f0-9]{64}$/.test(digest),
            "Invalid SHA-256 artifact digest.");

        assert(Number.isInteger(buildNumber) && buildNumber > 0,
            "Invalid build number.");

        this.version = version;
        this.commit = commit;
        this.digest = digest;
        this.buildNumber = buildNumber;

        Object.freeze(this);
    }
}

// ---------------------------------------------------------
// Change management
// ---------------------------------------------------------

class ChangeRequest {
    constructor({ title, description, risk, requester }) {
        assert(title && description && requester,
            "Change details are mandatory.");

        validateEnum(risk, Risk, "risk");

        this.id = crypto.randomUUID();
        this.title = title;
        this.description = description;
        this.risk = risk;
        this.requester = requester;
        this.status = Status.SUBMITTED;
        this.approvals = new Set();
        this.rejections = new Set();
        this.createdAt = new Date().toISOString();
    }

    approve(reviewer) {
        assert(this.status === Status.SUBMITTED,
            "Change is not awaiting approval.");

        assert(reviewer !== this.requester,
            "Self-approval is prohibited.");

        assert(!this.rejections.has(reviewer),
            "A rejecting reviewer cannot approve the same request.");

        this.approvals.add(reviewer);

        if (this.approvals.size >= APPROVAL_REQUIREMENTS[this.risk]) {
            this.status = Status.APPROVED;
        }
    }

    reject(reviewer) {
        assert(this.status === Status.SUBMITTED,
            "Change is not awaiting approval.");

        assert(reviewer !== this.requester,
            "Requester cannot reject their own change.");

        this.rejections.add(reviewer);
        this.status = Status.REJECTED;
    }
}

// ---------------------------------------------------------
// Health evaluation
// ---------------------------------------------------------

class HealthPolicy {
    constructor({
        maximumErrorRate = 0.02,
        maximumLatency = 500,
        minimumAvailability = 0.995
    } = {}) {
        assert(maximumErrorRate >= 0 && maximumErrorRate <= 1,
            "Invalid error threshold.");

        assert(maximumLatency > 0,
            "Latency threshold must be positive.");

        assert(minimumAvailability >= 0 && minimumAvailability <= 1,
            "Invalid availability threshold.");

        this.maximumErrorRate = maximumErrorRate;
        this.maximumLatency = maximumLatency;
        this.minimumAvailability = minimumAvailability;
    }

    evaluate(metrics) {
        const failures = [];

        if (!Number.isFinite(metrics.errorRate) ||
            metrics.errorRate < 0 ||
            metrics.errorRate > this.maximumErrorRate) {
            failures.push("Error rate exceeds threshold.");
        }

        if (!Number.isFinite(metrics.latency) ||
            metrics.latency < 0 ||
            metrics.latency > this.maximumLatency) {
            failures.push("Latency exceeds threshold.");
        }

        if (!Number.isFinite(metrics.availability) ||
            metrics.availability < this.minimumAvailability ||
            metrics.availability > 1) {
            failures.push("Availability is below threshold.");
        }

        return {
            healthy: failures.length === 0,
            failures
        };
    }
}

// ---------------------------------------------------------
// Release orchestration
// ---------------------------------------------------------

class ReleaseManager extends EventEmitter {
    constructor({
        healthPolicy = new HealthPolicy(),
        metricsProvider
    } = {}) {
        super();

        assert(typeof metricsProvider === "function",
            "A metrics provider is required.");

        this.healthPolicy = healthPolicy;
        this.metricsProvider = metricsProvider;

        this.activeVersions = new Map([
            [Environment.STAGING, null],
            [Environment.PRODUCTION, null]
        ]);

        this.releases = new Map();
        this.audit = [];
        this.environmentLocks = new Set();
    }

    record(event, release, details = {}) {
        const entry = Object.freeze({
            event,
            releaseId: release.id,
            version: release.artifact.version,
            timestamp: new Date().toISOString(),
            details
        });

        this.audit.push(entry);
        this.emit(event, entry);
    }

    createRelease({ artifact, change, environment, strategy }) {
        validateEnum(environment, Environment, "environment");
        validateEnum(strategy, Strategy, "strategy");

        assert(artifact instanceof ReleaseArtifact,
            "Invalid release artifact.");

        assert(change instanceof ChangeRequest,
            "Invalid change request.");

        assert(change.status === Status.APPROVED,
            "Only approved changes can be released.");

        assert(
            this.activeVersions.get(environment) !== artifact.version,
            "Version is already deployed."
        );

        const release = {
            id: crypto.randomUUID(),
            artifact,
            change,
            environment,
            strategy,
            state: ReleaseState.CREATED,
            previousVersion: this.activeVersions.get(environment),
            traffic: 0,
            createdAt: new Date().toISOString()
        };

        this.releases.set(release.id, release);

        this.record("release.created", release);

        return release;
    }

    async deploy(release) {
        assert(this.releases.get(release.id) === release,
            "Unknown release.");

        assert(release.state === ReleaseState.CREATED,
            "Release is not in the created state.");

        const environment = release.environment;

        assert(!this.environmentLocks.has(environment),
            "Another deployment is active in this environment.");

        this.environmentLocks.add(environment);

        try {
            release.state = ReleaseState.VALIDATING;
            this.record("release.validating", release);

            assert(release.change.status === Status.APPROVED,
                "Change approval is no longer valid.");

            assert(release.artifact.digest.startsWith("sha256:"),
                "Artifact integrity validation failed.");

            release.state = ReleaseState.DEPLOYING;
            this.record("release.deploying", release);

            const trafficPlan = TRAFFIC_PLANS[release.strategy];

            for (const percentage of trafficPlan) {
                release.traffic = percentage;

                this.record("traffic.updated", release, {
                    percentage
                });

                // Await asynchronous telemetry and health evaluation.
                const metrics = await this.metricsProvider({
                    release,
                    percentage
                });

                const evaluation = this.healthPolicy.evaluate(metrics);

                this.record("health.evaluated", release, {
                    percentage,
                    metrics,
                    evaluation
                });

                if (!evaluation.healthy) {
                    throw new Error(evaluation.failures.join(" "));
                }
            }

            release.state = ReleaseState.SUCCEEDED;
            this.activeVersions.set(environment, release.artifact.version);
            release.change.status = Status.IMPLEMENTED;

            this.record("release.succeeded", release);

            return true;

        } catch (error) {
            release.state = ReleaseState.FAILED;

            this.record("release.failed", release, {
                message: error.message
            });

            await this.rollback(release);

            return false;

        } finally {
            this.environmentLocks.delete(environment);
        }
    }

    async rollback(release) {
        assert(
            [ReleaseState.FAILED, ReleaseState.SUCCEEDED].includes(release.state),
            "Invalid rollback transition."
        );

        const environment = release.environment;

        this.activeVersions.set(
            environment,
            release.previousVersion
        );

        release.traffic = 0;
        release.state = ReleaseState.ROLLED_BACK;

        this.record("release.rolled_back", release, {
            restoredVersion: release.previousVersion
        });

        return true;
    }

    getReport() {
        return {
            activeVersions: Object.fromEntries(this.activeVersions),
            releases: [...this.releases.values()].map(release => ({
                id: release.id,
                version: release.artifact.version,
                strategy: release.strategy,
                environment: release.environment,
                state: release.state,
                previousVersion: release.previousVersion
            })),
            auditCount: this.audit.length
        };
    }
}

// ---------------------------------------------------------
// Metrics provider
// ---------------------------------------------------------

async function metricsProvider({ release, percentage }) {
    await new Promise(resolve => setImmediate(resolve));

    const unhealthy = (
        release.artifact.version === "2.0.0" &&
        percentage >= 25
    );

    return {
        errorRate: unhealthy ? 0.08 : 0.004,
        latency: unhealthy ? 900 : 150,
        availability: unhealthy ? 0.98 : 0.999
    };
}

// ---------------------------------------------------------
// Application workflow
// ---------------------------------------------------------

async function main() {
    const manager = new ReleaseManager({
        metricsProvider
    });

    manager.on("release.failed", event => {
        console.error("Release failure:", event.details.message);
    });

    manager.on("release.rolled_back", event => {
        console.log(
            "Rollback restored:",
            event.details.restoredVersion
        );
    });

    const initialChange = new ChangeRequest({
        title: "Initial production deployment",
        description: "Deploy stable application version.",
        risk: Risk.MEDIUM,
        requester: "release-manager"
    });

    initialChange.approve("engineering-lead");

    const artifact1 = new ReleaseArtifact({
        version: "1.0.0",
        commit: "a123456789",
        digest: "sha256:" + "a".repeat(64),
        buildNumber: 100
    });

    const release1 = manager.createRelease({
        artifact: artifact1,
        change: initialChange,
        environment: Environment.PRODUCTION,
        strategy: Strategy.BLUE_GREEN
    });

    assert(await manager.deploy(release1),
        "Initial deployment failed.");

    const change2 = new ChangeRequest({
        title: "Database query optimization",
        description: "Deploy an optimized database execution plan.",
        risk: Risk.HIGH,
        requester: "engineering-team"
    });

    change2.approve("technical-lead");
    change2.approve("security-lead");

    const artifact2 = new ReleaseArtifact({
        version: "2.0.0",
        commit: "b234567890",
        digest: "sha256:" + "b".repeat(64),
        buildNumber: 101
    });

    const release2 = manager.createRelease({
        artifact: artifact2,
        change: change2,
        environment: Environment.PRODUCTION,
        strategy: Strategy.CANARY
    });

    const success = await manager.deploy(release2);

    assert(!success, "Expected simulated deployment failure.");

    assert(
        manager.activeVersions.get(Environment.PRODUCTION) === "1.0.0",
        "Rollback failed to restore production."
    );

    console.log("\nFinal release report:");
    console.log(JSON.stringify(manager.getReport(), null, 2));

    console.log("\nAudit event count:", manager.audit.length);
}

main().catch(error => {
    console.error("Release orchestration stopped:", error.message);
    process.exitCode = 1;
});
