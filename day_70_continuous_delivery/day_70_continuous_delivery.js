"use strict";

/*
 * Continuous Delivery: Event-Driven Pipeline
 *
 * Node.js implementation using:
 * - EventEmitter
 * - Promises and async/await
 * - Maps and Sets
 * - Cryptographic artifact verification
 * - Build and test execution
 * - Package generation
 * - Release policy evaluation
 * - Approval and status-check gates
 * - Atomic artifact publication
 *
 * Requires Node.js 18 or later.
 */

const fs = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");
const EventEmitter = require("node:events");


class PipelineError extends Error {
    constructor(message, stage = "unknown") {
        super(message);
        this.name = "PipelineError";
        this.stage = stage;
    }
}


class ValidationError extends PipelineError {
    constructor(message) {
        super(message, "validation");
        this.name = "ValidationError";
    }
}


const PipelineState = Object.freeze({
    CREATED: "created",
    RUNNING: "running",
    FAILED: "failed",
    SUCCEEDED: "succeeded",
    RELEASED: "released"
});


const StageState = Object.freeze({
    PENDING: "pending",
    RUNNING: "running",
    PASSED: "passed",
    FAILED: "failed",
    SKIPPED: "skipped"
});


class Artifact {
    constructor(filename, filepath, checksum, size, version) {
        this.filename = filename;
        this.filepath = filepath;
        this.checksum = checksum;
        this.size = size;
        this.version = version;
        Object.freeze(this);
    }
}


class DeliveryPolicy {
    constructor({
        requiredChecks = ["build", "unit-tests", "security-scan"],
        minimumApprovals = 1,
        productionApproval = true,
        allowDraft = false,
        immutableArtifacts = true
    } = {}) {
        this.requiredChecks = new Set(requiredChecks);
        this.minimumApprovals = minimumApprovals;
        this.productionApproval = productionApproval;
        this.allowDraft = allowDraft;
        this.immutableArtifacts = immutableArtifacts;

        if (!Number.isInteger(minimumApprovals) || minimumApprovals < 0) {
            throw new ValidationError("Invalid approval threshold");
        }
    }

    evaluate(context) {
        const failures = [];

        if (context.draft && !this.allowDraft) {
            failures.push("Draft release is prohibited");
        }

        for (const required of this.requiredChecks) {
            if (context.checks.get(required) !== "passed") {
                failures.push(`Required check failed or missing: ${required}`);
            }
        }

        const eligibleApprovers = new Set(
            context.approvals
                .filter(item => item.eligible && item.decision === "approved")
                .map(item => item.reviewer)
        );

        if (eligibleApprovers.size < this.minimumApprovals) {
            failures.push("Insufficient eligible approvals");
        }

        if (
            context.environment === "production" &&
            this.productionApproval &&
            !context.productionApproved
        ) {
            failures.push("Production authorization missing");
        }

        if (!context.artifactVerified) {
            failures.push("Artifact integrity verification failed");
        }

        return Object.freeze({
            eligible: failures.length === 0,
            failures
        });
    }
}


class DeliveryPipeline extends EventEmitter {
    constructor({
        application,
        version,
        environment,
        workspace,
        policy = new DeliveryPolicy()
    }) {
        super();

        if (!/^[a-zA-Z0-9_-]+$/.test(application)) {
            throw new ValidationError("Invalid application name");
        }

        if (!/^[a-zA-Z0-9.+-]+$/.test(version)) {
            throw new ValidationError("Invalid application version");
        }

        if (!["development", "staging", "production"].includes(environment)) {
            throw new ValidationError("Unsupported environment");
        }

        if (!workspace) {
            throw new ValidationError("Workspace is required");
        }

        this.application = application;
        this.version = version;
        this.environment = environment;
        this.workspace = path.resolve(workspace);
        this.policy = policy;

        this.state = PipelineState.CREATED;
        this.stages = new Map();
        this.checks = new Map();
        this.approvals = [];
        this.artifact = null;
        this.events = [];
        this.draft = false;
        this.productionApproved = false;

        this.directories = {
            source: path.join(this.workspace, "source"),
            build: path.join(this.workspace, "build"),
            packages: path.join(this.workspace, "packages"),
            releases: path.join(this.workspace, "releases")
        };

        this.on("stage-completed", event => {
            this.events.push(event);
        });

        this.on("pipeline-error", event => {
            this.events.push(event);
        });
    }

    log(event, details = {}) {
        const record = Object.freeze({
            timestamp: new Date().toISOString(),
            event,
            details
        });

        this.events.push(record);
        this.emit("pipeline-event", record);
    }

    async initialize() {
        for (const directory of Object.values(this.directories)) {
            await fs.mkdir(directory, { recursive: true });
        }

        const manifest = {
            application: this.application,
            version: this.version,
            entrypoint: "application.json"
        };

        await fs.writeFile(
            path.join(this.directories.source, "application.json"),
            JSON.stringify(manifest, null, 2),
            { flag: "wx" }
        ).catch(async error => {
            if (error.code !== "EEXIST") throw error;
        });

        const source = [
            "function calculateTotal(values) {",
            "  if (!Array.isArray(values)) throw new TypeError('Expected an array');",
            "  if (!values.every(Number.isFinite)) throw new TypeError('Invalid number');",
            "  return values.reduce((total, value) => total + value, 0);",
            "}",
            "",
            "module.exports = { calculateTotal };"
        ].join("\n");

        await fs.writeFile(
            path.join(this.directories.source, "application.js"),
            source,
            { flag: "wx" }
        ).catch(async error => {
            if (error.code !== "EEXIST") throw error;
        });
    }

    async runStage(name, operation) {
        const started = Date.now();

        const stage = {
            name,
            status: StageState.RUNNING,
            startedAt: new Date(started).toISOString(),
            durationMs: 0,
            message: ""
        };

        this.stages.set(name, stage);
        this.log("stage-started", { name });

        try {
            stage.message = await operation();
            stage.status = StageState.PASSED;
            this.log("stage-completed", { name, status: stage.status });

            return stage;

        } catch (error) {
            stage.status = StageState.FAILED;
            stage.message = error.message;

            this.log("stage-failed", {
                name,
                message: error.message
            });

            throw new PipelineError(error.message, name);

        } finally {
            stage.durationMs = Date.now() - started;
            stage.completedAt = new Date().toISOString();
        }
    }

    async build() {
        await this.initialize();

        const source = path.join(
            this.directories.source,
            "application.js"
        );

        const destination = path.join(
            this.directories.build,
            "application.js"
        );

        await fs.copyFile(source, destination);

        const manifest = path.join(
            this.directories.source,
            "application.json"
        );

        const data = JSON.parse(await fs.readFile(manifest, "utf8"));

        if (data.version !== this.version) {
            throw new ValidationError("Manifest version mismatch");
        }

        this.checks.set("build", "passed");

        return "Application build completed";
    }

    async test() {
        const sourcePath = path.join(
            this.directories.build,
            "application.js"
        );

        const source = await fs.readFile(sourcePath, "utf8");

        // Execute the built module in an isolated Node.js module context.
        const Module = require("node:module");
        const testModule = new Module(sourcePath, module);

        testModule.filename = sourcePath;
        testModule.paths = Module._nodeModulePaths(
            path.dirname(sourcePath)
        );

        testModule._compile(source, sourcePath);

        const calculateTotal = testModule.exports.calculateTotal;

        if (typeof calculateTotal !== "function") {
            throw new ValidationError("Application entrypoint is invalid");
        }

        const testCases = [
            { input: [10, 20, 30], expected: 60 },
            { input: [], expected: 0 },
            { input: [-10, 10], expected: 0 },
            { input: [5], expected: 5 }
        ];

        for (const testCase of testCases) {
            const actual = calculateTotal(testCase.input);

            if (actual !== testCase.expected) {
                throw new PipelineError("Functional test failed", "test");
            }
        }

        try {
            calculateTotal([1, "invalid"]);
            throw new PipelineError("Invalid input was accepted", "test");
        } catch (error) {
            if (!(error instanceof TypeError)) throw error;
        }

        this.checks.set("unit-tests", "passed");

        return `${testCases.length + 1} tests passed`;
    }

    async securityScan() {
        const source = await fs.readFile(
            path.join(this.directories.build, "application.js"),
            "utf8"
        );

        const prohibitedPatterns = [
            /eval\s*\(/,
            /new\s+Function\s*\(/,
            /child_process/
        ];

        const findings = prohibitedPatterns.filter(
            pattern => pattern.test(source)
        );

        if (findings.length > 0) {
            this.checks.set("security-scan", "failed");
            throw new PipelineError(
                "Prohibited code pattern detected",
                "security-scan"
            );
        }

        this.checks.set("security-scan", "passed");

        return "Static security checks passed";
    }

    async package() {
        const buildPath = path.join(
            this.directories.build,
            "application.js"
        );

        const manifestPath = path.join(
            this.directories.build,
            "application.json"
        );

        await fs.copyFile(
            path.join(this.directories.source, "application.json"),
            manifestPath
        ).catch(error => {
            if (error.code !== "EEXIST") throw error;
        });

        const payload = {
            application: this.application,
            version: this.version,
            files: {
                "application.js": await fs.readFile(buildPath, "utf8"),
                "application.json": await fs.readFile(manifestPath, "utf8")
            }
        };

        // Canonical serialization gives the package stable byte content.
        const content = Buffer.from(
            JSON.stringify(payload),
            "utf8"
        );

        const checksum = crypto
            .createHash("sha256")
            .update(content)
            .digest("hex");

        const filename = `${this.application}-${this.version}.json`;

        const destination = path.join(
            this.directories.packages,
            filename
        );

        const temporary = `${destination}.${crypto.randomUUID()}.tmp`;

        try {
            await fs.writeFile(temporary, content, { flag: "wx" });
            await fs.rename(temporary, destination);
        } finally {
            await fs.rm(temporary, { force: true });
        }

        this.artifact = new Artifact(
            filename,
            destination,
            checksum,
            content.length,
            this.version
        );

        return `Package generated: ${filename}`;
    }

    async verifyArtifact() {
        if (!this.artifact) {
            throw new PipelineError("Package is unavailable");
        }

        const content = await fs.readFile(this.artifact.filepath);

        const actual = crypto
            .createHash("sha256")
            .update(content)
            .digest("hex");

        if (actual !== this.artifact.checksum) {
            throw new PipelineError("Artifact checksum mismatch");
        }

        const payload = JSON.parse(content.toString("utf8"));

        if (
            payload.application !== this.application ||
            payload.version !== this.version
        ) {
            throw new PipelineError("Artifact identity mismatch");
        }

        return true;
    }

    addApproval(reviewer, decision, eligible = true) {
        if (!reviewer || !["approved", "rejected"].includes(decision)) {
            throw new ValidationError("Invalid approval record");
        }

        this.approvals.push(Object.freeze({
            reviewer,
            decision,
            eligible
        }));

        this.log("approval-recorded", {
            reviewer,
            decision,
            eligible
        });
    }

    async release() {
        const artifactVerified = await this.verifyArtifact();

        const result = this.policy.evaluate({
            environment: this.environment,
            checks: this.checks,
            approvals: this.approvals,
            artifactVerified,
            productionApproved: this.productionApproved,
            draft: this.draft
        });

        if (!result.eligible) {
            throw new PipelineError(
                `Release blocked: ${result.failures.join("; ")}`,
                "release"
            );
        }

        const directory = path.join(
            this.directories.releases,
            this.environment
        );

        await fs.mkdir(directory, { recursive: true });

        const destination = path.join(directory, this.artifact.filename);

        if (this.policy.immutableArtifacts) {
            try {
                await fs.access(destination);
                throw new PipelineError("Release already exists");
            } catch (error) {
                if (error.code !== "ENOENT") throw error;
            }
        }

        const temporary = `${destination}.${crypto.randomUUID()}.tmp`;

        try {
            await fs.copyFile(
                this.artifact.filepath,
                temporary,
                fs.constants.COPYFILE_EXCL
            );

            const copied = await fs.readFile(temporary);

            const checksum = crypto
                .createHash("sha256")
                .update(copied)
                .digest("hex");

            if (checksum !== this.artifact.checksum) {
                throw new PipelineError("Release integrity failure");
            }

            // A same-filesystem rename makes publication atomic.
            await fs.rename(temporary, destination);

        } finally {
            await fs.rm(temporary, { force: true });
        }

        this.state = PipelineState.RELEASED;

        this.log("release-published", {
            destination,
            checksum: this.artifact.checksum
        });

        return destination;
    }

    async execute({ productionApproved = false } = {}) {
        if (this.state !== PipelineState.CREATED) {
            throw new PipelineError("Pipeline cannot be executed twice");
        }

        this.state = PipelineState.RUNNING;
        this.productionApproved = productionApproved;

        this.log("pipeline-started", {
            application: this.application,
            version: this.version,
            environment: this.environment
        });

        const stages = [
            ["build", () => this.build()],
            ["test", () => this.test()],
            ["security-scan", () => this.securityScan()],
            ["package", () => this.package()],
            ["release", () => this.release()]
        ];

        try {
            for (const [name, operation] of stages) {
                await this.runStage(name, operation);
            }

            return this.state;

        } catch (error) {
            this.state = PipelineState.FAILED;

            for (const [name] of stages) {
                if (!this.stages.has(name)) {
                    this.stages.set(name, {
                        name,
                        status: StageState.SKIPPED,
                        message: "An upstream stage failed"
                    });
                }
            }

            this.log("pipeline-error", {
                message: error.message,
                stage: error.stage || "unknown"
            });

            return this.state;
        }
    }

    report() {
        return {
            application: this.application,
            version: this.version,
            environment: this.environment,
            state: this.state,
            stages: Array.from(this.stages.values()),
            checks: Object.fromEntries(this.checks),
            artifact: this.artifact,
            events: this.events
        };
    }
}


async function runDemo() {
    const os = require("node:os");
    const workspace = await fs.mkdtemp(
        path.join(os.tmpdir(), "continuous-delivery-")
    );

    try {
        const policy = new DeliveryPolicy({
            requiredChecks: [
                "build",
                "unit-tests",
                "security-scan"
            ],
            minimumApprovals: 1,
            productionApproval: true
        });

        const pipeline = new DeliveryPipeline({
            application: "order-service",
            version: "2.5.0",
            environment: "production",
            workspace,
            policy
        });

        pipeline.on("pipeline-event", event => {
            console.log(`[EVENT] ${event.event}`);
        });

        pipeline.addApproval(
            "release-engineer",
            "approved",
            true
        );

        const state = await pipeline.execute({
            productionApproved: true
        });

        console.log("\nPIPELINE REPORT");
        console.log(JSON.stringify(pipeline.report(), null, 2));

        if (state !== PipelineState.RELEASED) {
            throw new PipelineError("Production release failed");
        }

        // Demonstrate approval-policy enforcement.
        const blockedPolicy = new DeliveryPolicy({
            requiredChecks: ["build"],
            minimumApprovals: 2
        });

        const blocked = blockedPolicy.evaluate({
            environment: "production",
            checks: new Map([["build", "passed"]]),
            approvals: [
                { reviewer: "reviewer-a", decision: "approved", eligible: true }
            ],
            artifactVerified: true,
            productionApproved: true,
            draft: false
        });

        console.log("\nPOLICY VALIDATION");
        console.log(blocked);

        if (blocked.eligible) {
            throw new Error("Approval policy validation failed");
        }

    } finally {
        await fs.rm(workspace, {
            recursive: true,
            force: true
        });
    }
}


runDemo().catch(error => {
    console.error("Delivery execution failed:", error.message);
    process.exitCode = 1;
});
