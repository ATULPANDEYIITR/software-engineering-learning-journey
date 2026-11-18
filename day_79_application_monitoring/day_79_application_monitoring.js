"use strict";

/*
 * Application Monitoring Platform
 * Event-driven health checks, alert policies, and dashboard metrics.
 *
 * Runtime: Node.js 18+
 * Dependencies: Node.js standard library only.
 */

const { EventEmitter } = require("node:events");
const crypto = require("node:crypto");
const os = require("node:os");

// ============================================================
// DOMAIN CONSTANTS
// ============================================================

const STATUS = Object.freeze({
    HEALTHY: "HEALTHY",
    DEGRADED: "DEGRADED",
    UNHEALTHY: "UNHEALTHY",
    UNKNOWN: "UNKNOWN"
});

const SEVERITY = Object.freeze({
    INFO: "INFO",
    WARNING: "WARNING",
    CRITICAL: "CRITICAL"
});

const ALERT_STATE = Object.freeze({
    FIRING: "FIRING",
    RESOLVED: "RESOLVED"
});

class MonitoringError extends Error {
    constructor(message, code = "MONITORING_ERROR") {
        super(message);
        this.name = "MonitoringError";
        this.code = code;
    }
}

function validateThreshold(value, name) {
    if (!Number.isFinite(value) || value < 0) {
        throw new MonitoringError(
            `${name} must be a non-negative finite number`,
            "INVALID_THRESHOLD"
        );
    }
}

function timestamp() {
    return new Date().toISOString();
}

// ============================================================
// METRICS COLLECTION
// ============================================================

class MetricStore {

    constructor(maxSamples = 500) {
        if (!Number.isInteger(maxSamples) || maxSamples < 1) {
            throw new MonitoringError("Invalid metric capacity");
        }

        this.maxSamples = maxSamples;
        this.metrics = new Map();
    }

    record(service, sample) {
        if (!service || typeof service !== "string") {
            throw new MonitoringError("Invalid service name");
        }

        if (!Number.isFinite(sample.latencyMs) || sample.latencyMs < 0) {
            throw new MonitoringError("Invalid latency metric");
        }

        if (!this.metrics.has(service)) {
            this.metrics.set(service, []);
        }

        const samples = this.metrics.get(service);

        samples.push({
            ...sample,
            recordedAt: timestamp()
        });

        if (samples.length > this.maxSamples) {
            samples.shift();
        }
    }

    query(service) {
        return [...(this.metrics.get(service) || [])];
    }

    aggregate(service) {
        const samples = this.query(service);

        if (samples.length === 0) {
            return {
                service,
                sampleCount: 0,
                averageLatencyMs: null,
                availabilityPercent: null
            };
        }

        const latencies = samples.map(item => item.latencyMs);

        const successful = samples.filter(
            item => item.status === STATUS.HEALTHY
        ).length;

        return {
            service,
            sampleCount: samples.length,
            averageLatencyMs:
                latencies.reduce((a, b) => a + b, 0) / samples.length,
            maximumLatencyMs: Math.max(...latencies),
            availabilityPercent: successful / samples.length * 100
        };
    }
}

// ============================================================
// HEALTH CHECKS
// ============================================================

class HealthCheck {

    constructor(name, service, handler, timeoutMs = 3000) {
        if (!name || !service || typeof handler !== "function") {
            throw new MonitoringError("Invalid health check definition");
        }

        if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) {
            throw new MonitoringError("Timeout must be positive");
        }

        this.name = name;
        this.service = service;
        this.handler = handler;
        this.timeoutMs = timeoutMs;
    }

    async execute() {
        const started = process.hrtime.bigint();

        let timer;

        try {
            const timeout = new Promise((_, reject) => {
                timer = setTimeout(
                    () => reject(
                        new MonitoringError(
                            `Health check timed out: ${this.name}`,
                            "CHECK_TIMEOUT"
                        )
                    ),
                    this.timeoutMs
                );
            });

            const result = await Promise.race([
                Promise.resolve().then(() => this.handler()),
                timeout
            ]);

            if (!result || typeof result.healthy !== "boolean") {
                throw new MonitoringError(
                    "Health handler returned an invalid result"
                );
            }

            return this.createResult(
                result.healthy,
                result.message || "Check completed",
                started,
                result.metadata || {}
            );

        } catch (error) {
            return this.createResult(
                false,
                error instanceof Error ? error.message : "Unknown failure",
                started,
                { errorCode: error.code || "CHECK_FAILED" }
            );

        } finally {
            clearTimeout(timer);
        }
    }

    createResult(healthy, message, started, metadata) {
        const elapsed = Number(
            process.hrtime.bigint() - started
        ) / 1e6;

        return {
            checkId: crypto.randomUUID(),
            name: this.name,
            service: this.service,
            status: healthy ? STATUS.HEALTHY : STATUS.UNHEALTHY,
            latencyMs: Number(elapsed.toFixed(2)),
            message,
            metadata,
            checkedAt: timestamp()
        };
    }
}

// ============================================================
// ALERT POLICY
// ============================================================

class AlertPolicy {

    constructor({
        warningLatencyMs = 500,
        criticalLatencyMs = 1500,
        failureThreshold = 2,
        recoveryThreshold = 2
    } = {}) {
        validateThreshold(warningLatencyMs, "warningLatencyMs");
        validateThreshold(criticalLatencyMs, "criticalLatencyMs");

        if (criticalLatencyMs < warningLatencyMs) {
            throw new MonitoringError(
                "Critical latency must be at least warning latency"
            );
        }

        if (
            !Number.isInteger(failureThreshold) ||
            failureThreshold < 1 ||
            !Number.isInteger(recoveryThreshold) ||
            recoveryThreshold < 1
        ) {
            throw new MonitoringError("Invalid state transition thresholds");
        }

        this.warningLatencyMs = warningLatencyMs;
        this.criticalLatencyMs = criticalLatencyMs;
        this.failureThreshold = failureThreshold;
        this.recoveryThreshold = recoveryThreshold;
    }

    evaluate(results, state) {
        if (results.length === 0) {
            throw new MonitoringError("Cannot evaluate empty health results");
        }

        const failed = results.some(
            item => item.status === STATUS.UNHEALTHY
        );

        const criticalLatency = results.some(
            item => item.latencyMs >= this.criticalLatencyMs
        );

        const warningLatency = results.some(
            item => item.latencyMs >= this.warningLatencyMs
        );

        if (failed || criticalLatency) {
            state.failures++;
            state.recoveries = 0;

            return state.failures >= this.failureThreshold
                ? STATUS.UNHEALTHY
                : STATUS.DEGRADED;
        }

        state.failures = 0;
        state.recoveries++;

        if (warningLatency) {
            return STATUS.DEGRADED;
        }

        if (state.recoveries >= this.recoveryThreshold) {
            return STATUS.HEALTHY;
        }

        return state.status === STATUS.UNHEALTHY
            ? STATUS.DEGRADED
            : state.status;
    }
}

// ============================================================
// ALERT MANAGER
// ============================================================

class AlertManager extends EventEmitter {

    constructor() {
        super();
        this.active = new Map();
        this.history = [];
    }

    process(service, status) {
        const current = this.active.get(service);

        if (
            status === STATUS.HEALTHY ||
            status === STATUS.UNKNOWN
        ) {
            if (current) {
                current.state = ALERT_STATE.RESOLVED;
                current.resolvedAt = timestamp();

                this.history.push(current);
                this.active.delete(service);

                this.emit("alertResolved", { ...current });
            }

            return;
        }

        const severity = status === STATUS.UNHEALTHY
            ? SEVERITY.CRITICAL
            : SEVERITY.WARNING;

        if (current) {
            current.occurrences++;
            current.severity = severity;
            current.lastSeen = timestamp();

            this.emit("alertUpdated", { ...current });
            return;
        }

        const alert = {
            alertId: crypto.randomUUID(),
            service,
            severity,
            state: ALERT_STATE.FIRING,
            occurrences: 1,
            message: `Service status: ${status}`,
            firstSeen: timestamp(),
            lastSeen: timestamp()
        };

        this.active.set(service, alert);
        this.emit("alertFired", { ...alert });
    }

    getActiveAlerts() {
        return [...this.active.values()].map(
            alert => ({ ...alert })
        );
    }
}

// ============================================================
// SERVICE MONITOR
// ============================================================

class ServiceMonitor extends EventEmitter {

    constructor(name, policy, metricStore, alertManager) {
        super();

        if (!name || !(policy instanceof AlertPolicy)) {
            throw new MonitoringError("Invalid service configuration");
        }

        this.name = name;
        this.policy = policy;
        this.metricStore = metricStore;
        this.alertManager = alertManager;

        this.checks = new Map();

        this.state = {
            status: STATUS.UNKNOWN,
            failures: 0,
            recoveries: 0,
            lastCheckedAt: null
        };

        this.running = false;
    }

    register(check) {
        if (!(check instanceof HealthCheck)) {
            throw new MonitoringError("Expected HealthCheck instance");
        }

        if (check.service !== this.name) {
            throw new MonitoringError("Health check service mismatch");
        }

        if (this.checks.has(check.name)) {
            throw new MonitoringError("Duplicate health check");
        }

        this.checks.set(check.name, check);
    }

    async runCycle() {
        if (this.running) {
            throw new MonitoringError(
                `Concurrent cycle rejected for ${this.name}`
            );
        }

        if (this.checks.size === 0) {
            throw new MonitoringError("No health checks registered");
        }

        this.running = true;

        try {
            // Independent dependencies are checked concurrently.
            const results = await Promise.all(
                [...this.checks.values()].map(check => check.execute())
            );

            results.forEach(result => {
                this.metricStore.record(this.name, result);
            });

            const previous = this.state.status;

            this.state.status = this.policy.evaluate(
                results,
                this.state
            );

            this.state.lastCheckedAt = timestamp();

            this.alertManager.process(
                this.name,
                this.state.status
            );

            const event = {
                service: this.name,
                previousStatus: previous,
                status: this.state.status,
                results
            };

            this.emit("cycleCompleted", event);

            if (previous !== this.state.status) {
                this.emit("statusChanged", event);
            }

            return event;

        } finally {
            this.running = false;
        }
    }
}

// ============================================================
// DASHBOARD SERVICE
// ============================================================

class Dashboard {

    constructor(monitors, metricStore, alertManager) {
        this.monitors = monitors;
        this.metricStore = metricStore;
        this.alertManager = alertManager;
    }

    snapshot() {
        const services = [...this.monitors.values()].map(monitor => ({
            name: monitor.name,
            status: monitor.state.status,
            lastCheckedAt: monitor.state.lastCheckedAt,
            metrics: this.metricStore.aggregate(monitor.name)
        }));

        const count = status => services.filter(
            item => item.status === status
        ).length;

        return {
            generatedAt: timestamp(),
            hostname: os.hostname(),
            totalServices: services.length,
            healthy: count(STATUS.HEALTHY),
            degraded: count(STATUS.DEGRADED),
            unhealthy: count(STATUS.UNHEALTHY),
            unknown: count(STATUS.UNKNOWN),
            activeAlerts: this.alertManager.getActiveAlerts(),
            services
        };
    }
}

// ============================================================
// MONITORING APPLICATION
// ============================================================

class MonitoringApplication {

    constructor() {
        this.metricStore = new MetricStore();
        this.alertManager = new AlertManager();
        this.monitors = new Map();

        this.alertManager.on("alertFired", alert => {
            console.error(
                `[${alert.severity}] ${alert.service}: ${alert.message}`
            );
        });

        this.alertManager.on("alertResolved", alert => {
            console.log(`Resolved: ${alert.service}`);
        });
    }

    addService(monitor) {
        if (this.monitors.has(monitor.name)) {
            throw new MonitoringError("Duplicate monitored service");
        }

        this.monitors.set(monitor.name, monitor);
    }

    async runCycle() {
        const outcomes = await Promise.allSettled(
            [...this.monitors.values()].map(
                monitor => monitor.runCycle()
            )
        );

        return outcomes.map((outcome, index) => ({
            service: [...this.monitors.keys()][index],
            success: outcome.status === "fulfilled",
            error: outcome.status === "rejected"
                ? outcome.reason.message
                : null
        }));
    }

    dashboard() {
        return new Dashboard(
            this.monitors,
            this.metricStore,
            this.alertManager
        ).snapshot();
    }
}

// ============================================================
// TESTS
// ============================================================

async function runTests() {
    const store = new MetricStore(3);

    for (let i = 0; i < 5; i++) {
        store.record("test", {
            latencyMs: i * 10,
            status: STATUS.HEALTHY
        });
    }

    console.assert(store.query("test").length === 3);

    const policy = new AlertPolicy({
        failureThreshold: 2,
        recoveryThreshold: 2
    });

    const state = {
        status: STATUS.UNKNOWN,
        failures: 0,
        recoveries: 0
    };

    const failed = [{
        status: STATUS.UNHEALTHY,
        latencyMs: 10
    }];

    console.assert(
        policy.evaluate(failed, state) === STATUS.DEGRADED
    );

    console.assert(
        policy.evaluate(failed, state) === STATUS.UNHEALTHY
    );

    const alerts = new AlertManager();

    alerts.process("test", STATUS.UNHEALTHY);
    console.assert(alerts.getActiveAlerts().length === 1);

    alerts.process("test", STATUS.HEALTHY);
    console.assert(alerts.getActiveAlerts().length === 0);

    let invalidRejected = false;

    try {
        new AlertPolicy({
            warningLatencyMs: 1000,
            criticalLatencyMs: 500
        });
    } catch (error) {
        invalidRejected = error instanceof MonitoringError;
    }

    console.assert(invalidRejected);

    console.log("All JavaScript monitoring tests passed.");
}

// ============================================================
// EXECUTION
// ============================================================

async function main() {
    await runTests();

    const application = new MonitoringApplication();

    let databaseAvailable = true;
    let externalDependencyAvailable = true;

    const payment = new ServiceMonitor(
        "payment-api",
        new AlertPolicy({
            warningLatencyMs: 300,
            criticalLatencyMs: 1000,
            failureThreshold: 2,
            recoveryThreshold: 2
        }),
        application.metricStore,
        application.alertManager
    );

    payment.register(new HealthCheck(
        "application",
        "payment-api",
        async () => ({
            healthy: true,
            message: "Application responding",
            metadata: { endpoint: "/health" }
        })
    ));

    payment.register(new HealthCheck(
        "database",
        "payment-api",
        async () => ({
            healthy: databaseAvailable,
            message: databaseAvailable
                ? "Database available"
                : "Database connection failed"
        })
    ));

    payment.register(new HealthCheck(
        "external-provider",
        "payment-api",
        async () => ({
            healthy: externalDependencyAvailable,
            message: "External provider check"
        })
    ));

    application.addService(payment);

    payment.on("statusChanged", event => {
        console.log(
            `${event.service}: ${event.previousStatus} -> ${event.status}`
        );
    });

    for (let cycle = 1; cycle <= 4; cycle++) {
        console.log(`\nMonitoring cycle ${cycle}`);

        if (cycle === 3) {
            databaseAvailable = true;
            externalDependencyAvailable = true;
        }

        const outcomes = await application.runCycle();

        console.log(JSON.stringify(outcomes, null, 2));
        console.log(
            JSON.stringify(application.dashboard(), null, 2)
        );
    }
}

main().catch(error => {
    console.error("Monitoring application failed:", error.message);
    process.exitCode = 1;
});
