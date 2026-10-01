/**
 * Software Design Principles Case Study
 * DRY, KISS, YAGNI, and Separation of Concerns
 *
 * Runtime: Node.js 18+
 *
 * This program models a deployment workflow using JavaScript-specific
 * techniques:
 * - immutable configuration
 * - classes and composition
 * - event-driven lifecycle notifications
 * - asynchronous persistence
 * - explicit policy evaluation
 * - small pure functions
 *
 * The implementation is intentionally different from the Python program.
 * It uses an EventEmitter-style event bus and asynchronous repository
 * operations to show how the principles apply to event-driven JavaScript.
 */

"use strict";

const fs = require("node:fs/promises");
const os = require("node:os");
const path = require("node:path");
const { EventEmitter } = require("node:events");
const assert = require("node:assert/strict");


// ---------------------------------------------------------------------------
// KISS: pure functions for uncomplicated domain rules
// ---------------------------------------------------------------------------

function normalizeEnvironment(value) {
    if (typeof value !== "string") {
        return "";
    }

    return value.trim().toLowerCase();
}


function isValidVersion(version) {
    return /^\d+\.\d+\.\d+$/.test(version);
}


function calculateRisk({ changedFiles, testsPassed }) {
    if (!Number.isInteger(changedFiles) || changedFiles < 0) {
        throw new TypeError("changedFiles must be a non-negative integer");
    }

    let risk = Math.min(Math.floor(changedFiles / 10), 7);

    if (!testsPassed) {
        risk += 5;
    }

    return Math.min(risk, 10);
}


function isSmallSafeChange(change) {
    /*
     * The rule is intentionally expressed directly because there is only one
     * current definition of a small safe change.
     */
    return change.testsPassed === true &&
        Number.isInteger(change.changedFiles) &&
        change.changedFiles <= 10;
}


// ---------------------------------------------------------------------------
// Domain errors
// ---------------------------------------------------------------------------

class ValidationError extends Error {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}


class AuthorizationError extends Error {
    constructor(message) {
        super(message);
        this.name = "AuthorizationError";
    }
}


// ---------------------------------------------------------------------------
// Domain objects
// ---------------------------------------------------------------------------

class DeploymentRequest {
    constructor({
        id,
        service,
        version,
        environment,
        requester,
        testsPassed,
        changedFiles,
    }) {
        this.id = id;
        this.service = service;
        this.version = version;
        this.environment = normalizeEnvironment(environment);
        this.requester = requester;
        this.testsPassed = testsPassed;
        this.changedFiles = changedFiles;
        this.risk = calculateRisk({ changedFiles, testsPassed });

        Object.freeze(this);
    }
}


// ---------------------------------------------------------------------------
// Separation of concerns: validation
// ---------------------------------------------------------------------------

class DeploymentValidator {
    validate(request) {
        if (!(request instanceof DeploymentRequest)) {
            throw new ValidationError("request must be a DeploymentRequest");
        }

        if (!request.id || !request.id.trim()) {
            throw new ValidationError("deployment id is required");
        }

        if (!request.service || !request.service.trim()) {
            throw new ValidationError("service is required");
        }

        if (!isValidVersion(request.version)) {
            throw new ValidationError(
                "version must use the numeric x.y.z format"
            );
        }

        if (!["staging", "production"].includes(request.environment)) {
            throw new ValidationError(
                `unsupported environment: ${request.environment}`
            );
        }

        if (!request.requester || !request.requester.trim()) {
            throw new ValidationError("requester is required");
        }

        if (!Number.isInteger(request.changedFiles) || request.changedFiles < 0) {
            throw new ValidationError(
                "changedFiles must be a non-negative integer"
            );
        }

        if (typeof request.testsPassed !== "boolean") {
            throw new ValidationError("testsPassed must be boolean");
        }
    }
}


// ---------------------------------------------------------------------------
// Separation of concerns: authorization
// ---------------------------------------------------------------------------

class AuthorizationService {
    constructor(developers) {
        this.developers = new Map(
            developers.map((developer) => [developer.username, developer])
        );
    }

    authorize(request) {
        const developer = this.developers.get(request.requester);

        if (!developer || !developer.active) {
            throw new AuthorizationError("requester is inactive or unknown");
        }

        if (
            request.environment === "production" &&
            developer.team !== "platform"
        ) {
            throw new AuthorizationError(
                "production deployment requires a platform engineer"
            );
        }
    }
}


// ---------------------------------------------------------------------------
// DRY: one policy evaluator instead of duplicated environment checks
// ---------------------------------------------------------------------------

class DeploymentPolicy {
    constructor({
        maximumAutomaticRisk = 4,
        maximumChangedFiles = 50,
    } = {}) {
        this.maximumAutomaticRisk = maximumAutomaticRisk;
        this.maximumChangedFiles = maximumChangedFiles;

        Object.freeze(this);
    }

    violations(request) {
        const violations = [];

        if (
            request.environment === "production" &&
            !request.testsPassed
        ) {
            violations.push("production requires passing tests");
        }

        if (request.risk > this.maximumAutomaticRisk) {
            violations.push(
                `risk ${request.risk} exceeds automatic threshold ` +
                `${this.maximumAutomaticRisk}`
            );
        }

        if (request.changedFiles > this.maximumChangedFiles) {
            violations.push(
                "large changes require additional review"
            );
        }

        return violations;
    }
}


// ---------------------------------------------------------------------------
// Event-driven behavior
// ---------------------------------------------------------------------------

class DeploymentEvents extends EventEmitter {
    emitAccepted(request) {
        this.emit("deployment:accepted", {
            requestId: request.id,
            service: request.service,
            environment: request.environment,
        });
    }

    emitRejected(request, reason) {
        this.emit("deployment:rejected", {
            requestId: request.id,
            reason,
        });
    }

    emitDeployed(request) {
        this.emit("deployment:deployed", {
            requestId: request.id,
            service: request.service,
            version: request.version,
        });
    }
}


// ---------------------------------------------------------------------------
// Separation of concerns: notification subscriber
// ---------------------------------------------------------------------------

class NotificationSubscriber {
    constructor(events) {
        this.messages = [];

        events.on("deployment:accepted", (event) => {
            this.messages.push(
                `accepted ${event.requestId} for ${event.environment}`
            );
        });

        events.on("deployment:rejected", (event) => {
            this.messages.push(
                `rejected ${event.requestId}: ${event.reason}`
            );
        });

        events.on("deployment:deployed", (event) => {
            this.messages.push(
                `deployed ${event.service} ${event.version}`
            );
        });
    }
}


// ---------------------------------------------------------------------------
// YAGNI: the executor implements only the required deployment operation
// ---------------------------------------------------------------------------

class DeploymentExecutor {
    async execute(request) {
        /*
         * An actual production system would call a deployment provider here.
         * The case study keeps the boundary explicit without inventing a
         * plugin marketplace or multi-cloud abstraction that the requirements
         * do not need.
         */
        if (!request.testsPassed) {
            return {
                success: false,
                reason: "test suite did not pass",
            };
        }

        await Promise.resolve();

        return {
            success: true,
            reason: `deployed ${request.service}:${request.version}`,
        };
    }
}


// ---------------------------------------------------------------------------
// Asynchronous repository: JavaScript-specific I/O boundary
// ---------------------------------------------------------------------------

class JsonAuditRepository {
    constructor(filePath) {
        this.filePath = filePath;
    }

    async readAll() {
        try {
            const content = await fs.readFile(this.filePath, "utf8");
            return JSON.parse(content);
        } catch (error) {
            if (error.code === "ENOENT") {
                return {};
            }

            if (error instanceof SyntaxError) {
                throw new Error("audit file contains invalid JSON");
            }

            throw error;
        }
    }

    async save(record) {
        const records = await this.readAll();
        records[record.id] = record;

        await fs.mkdir(path.dirname(this.filePath), {
            recursive: true,
        });

        /*
         * The temporary file is written before rename so a partially written
         * JSON document is less likely to become the canonical audit file.
         */
        const temporaryPath = `${this.filePath}.tmp`;

        await fs.writeFile(
            temporaryPath,
            JSON.stringify(records, null, 2),
            "utf8"
        );

        await fs.rename(temporaryPath, this.filePath);
    }

    async find(id) {
        const records = await this.readAll();
        return records[id] ?? null;
    }
}


// ---------------------------------------------------------------------------
// Workflow orchestration
// ---------------------------------------------------------------------------

class DeploymentWorkflow {
    constructor({
        validator,
        authorization,
        policy,
        repository,
        executor,
        events,
    }) {
        this.validator = validator;
        this.authorization = authorization;
        this.policy = policy;
        this.repository = repository;
        this.executor = executor;
        this.events = events;
    }

    async process(request) {
        this.validator.validate(request);

        try {
            this.authorization.authorize(request);
        } catch (error) {
            const record = this.createRecord(
                request,
                "rejected",
                error.message
            );

            await this.repository.save(record);
            this.events.emitRejected(request, error.message);
            return record;
        }

        const violations = this.policy.violations(request);

        if (violations.length > 0) {
            const reason = violations.join("; ");

            const record = this.createRecord(
                request,
                "rejected",
                reason
            );

            await this.repository.save(record);
            this.events.emitRejected(request, reason);
            return record;
        }

        this.events.emitAccepted(request);

        const result = await this.executor.execute(request);

        const record = this.createRecord(
            request,
            result.success ? "deployed" : "failed",
            result.reason
        );

        await this.repository.save(record);

        if (result.success) {
            this.events.emitDeployed(request);
        } else {
            this.events.emitRejected(request, result.reason);
        }

        return record;
    }

    createRecord(request, status, reason) {
        return Object.freeze({
            id: request.id,
            service: request.service,
            version: request.version,
            environment: request.environment,
            requester: request.requester,
            status,
            reason,
            risk: request.risk,
            recordedAt: new Date().toISOString(),
        });
    }
}


// ---------------------------------------------------------------------------
// DRY failure example
// ---------------------------------------------------------------------------

function duplicatedPolicyExample(request) {
    /*
     * Both branches below repeat the same condition. In a growing application,
     * changing the risk threshold would require finding every copy.
     *
     * The actual workflow does not use this function. It exists as an
     * executable comparison showing the maintenance problem DRY addresses.
     */
    if (request.environment === "staging") {
        return request.testsPassed && request.risk <= 4;
    }

    if (request.environment === "production") {
        return request.testsPassed && request.risk <= 4;
    }

    return false;
}


// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

function createWorkflow(repository) {
    const developers = [
        {
            username: "maya",
            team: "platform",
            active: true,
        },
        {
            username: "leo",
            team: "application",
            active: true,
        },
        {
            username: "nina",
            team: "application",
            active: false,
        },
    ];

    const events = new DeploymentEvents();

    new NotificationSubscriber(events);

    return {
        workflow: new DeploymentWorkflow({
            validator: new DeploymentValidator(),
            authorization: new AuthorizationService(developers),
            policy: new DeploymentPolicy({
                maximumAutomaticRisk: 4,
                maximumChangedFiles: 50,
            }),
            repository,
            executor: new DeploymentExecutor(),
            events,
        }),
        events,
    };
}


async function runAssertions(workflow) {
    const successfulRequest = new DeploymentRequest({
        id: "DEP-001",
        service: "payments-api",
        version: "2.4.1",
        environment: "production",
        requester: "maya",
        testsPassed: true,
        changedFiles: 8,
    });

    const successfulRecord = await workflow.process(successfulRequest);

    assert.equal(successfulRecord.status, "deployed");


    const unauthorizedRequest = new DeploymentRequest({
        id: "DEP-002",
        service: "catalog-api",
        version: "1.2.0",
        environment: "production",
        requester: "leo",
        testsPassed: true,
        changedFiles: 4,
    });

    const unauthorizedRecord = await workflow.process(
        unauthorizedRequest
    );

    assert.equal(unauthorizedRecord.status, "rejected");
    assert.match(
        unauthorizedRecord.reason,
        /platform engineer/
    );


    const riskyRequest = new DeploymentRequest({
        id: "DEP-003",
        service: "search-api",
        version: "3.0.0",
        environment: "staging",
        requester: "leo",
        testsPassed: true,
        changedFiles: 80,
    });

    const riskyRecord = await workflow.process(riskyRequest);

    assert.equal(riskyRecord.status, "rejected");
    assert.match(riskyRecord.reason, /risk/);


    const failedTestRequest = new DeploymentRequest({
        id: "DEP-004",
        service: "billing-api",
        version: "4.0.0",
        environment: "production",
        requester: "maya",
        testsPassed: false,
        changedFiles: 2,
    });

    const failedTestRecord = await workflow.process(failedTestRequest);

    assert.equal(failedTestRecord.status, "rejected");
    assert.match(failedTestRecord.reason, /passing tests/);
}


// ---------------------------------------------------------------------------
// Main demonstration
// ---------------------------------------------------------------------------

async function main() {
    console.log("=== Software Design Principles Case Study ===");
    console.log("DRY, KISS, YAGNI, and Separation of Concerns");
    console.log();

    console.log("=== KISS ===");

    const smallChange = {
        testsPassed: true,
        changedFiles: 5,
    };

    console.log(
        "small safe change:",
        isSmallSafeChange(smallChange)
    );

    console.log();


    console.log("=== DRY ===");

    const dryRequest = new DeploymentRequest({
        id: "DRY-001",
        service: "analytics-api",
        version: "1.0.0",
        environment: "production",
        requester: "maya",
        testsPassed: true,
        changedFiles: 6,
    });

    console.log(
        "centralized policy result:",
        duplicatedPolicyExample(dryRequest)
    );

    console.log();


    console.log("=== Event-driven workflow ===");

    const temporaryDirectory = await fs.mkdtemp(
        path.join(os.tmpdir(), "design-principles-")
    );

    const auditPath = path.join(
        temporaryDirectory,
        "deployments.json"
    );

    const repository = new JsonAuditRepository(auditPath);
    const { workflow, events } = createWorkflow(repository);

    const observedEvents = [];

    events.on("deployment:accepted", (event) => {
        observedEvents.push({
            type: "accepted",
            requestId: event.requestId,
        });
    });

    events.on("deployment:rejected", (event) => {
        observedEvents.push({
            type: "rejected",
            requestId: event.requestId,
        });
    });

    events.on("deployment:deployed", (event) => {
        observedEvents.push({
            type: "deployed",
            requestId: event.requestId,
        });
    });

    await runAssertions(workflow);

    console.log("observed events:", observedEvents);

    const persisted = await repository.find("DEP-001");

    assert.ok(persisted);
    assert.equal(persisted.status, "deployed");

    console.log(
        "persisted record:",
        JSON.stringify(persisted, null, 2)
    );

    console.log();


    console.log("=== YAGNI ===");
    console.log(
        "The current workflow has no speculative multi-cloud plugin system."
    );
    console.log(
        "The current requirement is satisfied by one executor boundary."
    );

    console.log();


    console.log("=== Design consequences ===");
    console.log(
        "Validation changes remain inside DeploymentValidator."
    );
    console.log(
        "Authorization changes remain inside AuthorizationService."
    );
    console.log(
        "Business policy changes remain inside DeploymentPolicy."
    );
    console.log(
        "Persistence changes remain behind JsonAuditRepository."
    );
    console.log(
        "Observers can subscribe to lifecycle events without modifying policy."
    );

    console.log();
    console.log("all assertions passed");
}


main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
