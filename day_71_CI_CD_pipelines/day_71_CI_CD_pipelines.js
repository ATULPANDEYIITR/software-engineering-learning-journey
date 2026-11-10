"use strict";

/*
 * CI/CD Event-Driven Pipeline Automation
 *
 * Runtime: Node.js 18+
 *
 * Features:
 * - Event-driven pipeline orchestration
 * - Asynchronous stage execution
 * - Dependency scheduling
 * - Retry and timeout handling
 * - Build artifact integrity
 * - Security and test gates
 * - Environment policies
 * - Deployment approvals
 * - Pipeline event history
 * - Failure propagation
 */

const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const EventEmitter = require("node:events");

const StageState = Object.freeze({
    PENDING: "PENDING",
    RUNNING: "RUNNING",
    SUCCESS: "SUCCESS",
    FAILED: "FAILED",
    SKIPPED: "SKIPPED"
});

const PipelineState = Object.freeze({
    CREATED: "CREATED",
    RUNNING: "RUNNING",
    SUCCESS: "SUCCESS",
    FAILED: "FAILED"
});

class PipelineError extends Error {
    constructor(message) {
        super(message);
        this.name = "PipelineError";
    }
}

class ValidationError extends PipelineError {
    constructor(message) {
        super(message);
        this.name = "ValidationError";
    }
}

class StageTimeoutError extends PipelineError {
    constructor(message) {
        super(message);
        this.name = "StageTimeoutError";
    }
}

class Artifact {
    constructor(name, content) {
        if (!name || typeof name !== "string") {
            throw new ValidationError("Invalid artifact name.");
        }

        this.name = name;
        this.content = content;

        this.sha256 = crypto
            .createHash("sha256")
            .update(content)
            .digest("hex");

        Object.freeze(this);
    }
}

class PipelineContext {
    constructor({
        repository,
        commit,
        environment,
        approval = false
    }) {
        if (!repository || !/^[a-f0-9]{40}$/i.test(commit)) {
            throw new ValidationError(
                "Repository and valid 40-character commit SHA are required."
            );
        }

        if (!["development", "staging", "production"].includes(environment)) {
            throw new ValidationError("Unsupported environment.");
        }

        this.pipelineId = crypto.randomUUID();
        this.repository = repository;
        this.commit = commit;
        this.environment = environment;
        this.approval = approval;

        this.artifacts = new Map();
        this.variables = new Map();
        this.results = new Map();
    }

    addArtifact(artifact) {
        if (this.artifacts.has(artifact.name)) {
            throw new ValidationError(
                `Duplicate artifact: ${artifact.name}`
            );
        }

        this.artifacts.set(artifact.name, artifact);
    }
}

class PipelineStage {
    constructor({
        name,
        action,
        dependencies = [],
        retries = 0,
        timeoutMs = 5000,
        approvalRequired = false
    }) {
        if (!name || typeof action !== "function") {
            throw new ValidationError(
                "Stage requires a name and executable action."
            );
        }

        if (
            !Number.isInteger(retries) ||
            retries < 0 ||
            timeoutMs <= 0 ||
            !Number.isFinite(timeoutMs)
        ) {
            throw new ValidationError("Invalid retry or timeout configuration.");
        }

        this.name = name;
        this.action = action;
        this.dependencies = [...new Set(dependencies)];
        this.retries = retries;
        this.timeoutMs = timeoutMs;
        this.approvalRequired = approvalRequired;
        this.state = StageState.PENDING;
    }
}

class Pipeline extends EventEmitter {
    constructor(context, concurrency = 2) {
        super();

        if (!Number.isInteger(concurrency) || concurrency < 1) {
            throw new ValidationError("Concurrency must be positive.");
        }

        this.context = context;
        this.concurrency = concurrency;
        this.stages = new Map();
        this.state = PipelineState.CREATED;
        this.history = [];
    }

    record(type, details = {}) {
        const event = Object.freeze({
            timestamp: new Date().toISOString(),
            type,
            ...details
        });

        this.history.push(event);
        this.emit(type, event);
    }

    addStage(stage) {
        if (this.state !== PipelineState.CREATED) {
            throw new PipelineError(
                "Stages cannot be modified after execution starts."
            );
        }

        if (this.stages.has(stage.name)) {
            throw new ValidationError(
                `Duplicate stage: ${stage.name}`
            );
        }

        this.stages.set(stage.name, stage);
    }

    validate() {
        if (this.stages.size === 0) {
            throw new ValidationError("Pipeline is empty.");
        }

        for (const stage of this.stages.values()) {
            for (const dependency of stage.dependencies) {
                if (!this.stages.has(dependency)) {
                    throw new ValidationError(
                        `Missing dependency ${dependency}.`
                    );
                }

                if (dependency === stage.name) {
                    throw new ValidationError(
                        "Stage cannot depend on itself."
                    );
                }
            }
        }

        // Three-color DFS detects cycles.
        const colors = new Map();

        const visit = name => {
            const color = colors.get(name) || 0;

            if (color === 1) {
                throw new ValidationError(
                    "Circular stage dependency detected."
                );
            }

            if (color === 2) return;

            colors.set(name, 1);

            const stage = this.stages.get(name);

            for (const dependency of stage.dependencies) {
                visit(dependency);
            }

            colors.set(name, 2);
        };

        for (const name of this.stages.keys()) {
            visit(name);
        }
    }

    async executeWithTimeout(stage) {
        let timer;

        try {
            return await Promise.race([
                Promise.resolve().then(() =>
                    stage.action(this.context)
                ),

                new Promise((_, reject) => {
                    timer = setTimeout(
                        () => reject(
                            new StageTimeoutError(
                                `${stage.name} exceeded ${stage.timeoutMs}ms`
                            )
                        ),
                        stage.timeoutMs
                    );
                })
            ]);
        } finally {
            clearTimeout(timer);
        }
    }

    async executeStage(stage) {
        stage.state = StageState.RUNNING;

        this.record("stage_started", {
            stage: stage.name
        });

        if (
            stage.approvalRequired &&
            !this.context.approval
        ) {
            stage.state = StageState.FAILED;

            throw new PipelineError(
                `Approval required for ${stage.name}.`
            );
        }

        const start = performance.now();
        let lastError;

        for (let attempt = 1; attempt <= stage.retries + 1; attempt++) {
            try {
                const output = await this.executeWithTimeout(stage);

                const result = {
                    state: StageState.SUCCESS,
                    attempts: attempt,
                    durationMs: performance.now() - start,
                    output
                };

                stage.state = StageState.SUCCESS;
                this.context.results.set(stage.name, result);

                this.record("stage_succeeded", {
                    stage: stage.name,
                    attempt
                });

                return result;
            } catch (error) {
                lastError = error;

                this.record("stage_attempt_failed", {
                    stage: stage.name,
                    attempt,
                    error: error.message
                });

                if (attempt <= stage.retries) {
                    await new Promise(resolve =>
                        setTimeout(resolve, 100 * attempt)
                    );
                }
            }
        }

        stage.state = StageState.FAILED;

        const result = {
            state: StageState.FAILED,
            attempts: stage.retries + 1,
            durationMs: performance.now() - start,
            error: lastError.message
        };

        this.context.results.set(stage.name, result);

        throw lastError;
    }

    async run() {
        if (this.state !== PipelineState.CREATED) {
            throw new PipelineError(
                "Pipeline can only run once."
            );
        }

        this.validate();
        this.state = PipelineState.RUNNING;

        this.record("pipeline_started", {
            pipelineId: this.context.pipelineId
        });

        const pending = new Set(this.stages.keys());
        const completed = new Set();
        const running = new Map();

        let failure = null;

        try {
            while (pending.size > 0 || running.size > 0) {
                let scheduled = false;

                if (!failure) {
                    for (const name of [...pending]) {
                        if (running.size >= this.concurrency) break;

                        const stage = this.stages.get(name);

                        const dependenciesReady =
                            stage.dependencies.every(
                                dependency => completed.has(dependency)
                            );

                        if (!dependenciesReady) continue;

                        pending.delete(name);

                        const task = this.executeStage(stage)
                            .then(() => {
                                completed.add(name);
                            })
                            .catch(error => {
                                failure = failure || error;
                            })
                            .finally(() => {
                                running.delete(name);
                            });

                        running.set(name, task);
                        scheduled = true;
                    }
                }

                if (running.size > 0) {
                    await Promise.race(running.values());
                } else if (pending.size > 0 && !scheduled) {
                    if (failure) break;

                    throw new PipelineError(
                        "Pipeline scheduler cannot make progress."
                    );
                }
            }

            // Allow already running stages to settle before reporting.
            await Promise.all(running.values());

            if (failure) throw failure;

            this.state = PipelineState.SUCCESS;

            this.record("pipeline_succeeded", {
                pipelineId: this.context.pipelineId
            });

            return this.report();

        } catch (error) {
            this.state = PipelineState.FAILED;

            for (const name of pending) {
                const stage = this.stages.get(name);
                stage.state = StageState.SKIPPED;

                this.context.results.set(name, {
                    state: StageState.SKIPPED,
                    reason: "Pipeline execution stopped."
                });
            }

            this.record("pipeline_failed", {
                error: error.message
            });

            throw error;
        }
    }

    report() {
        return {
            pipelineId: this.context.pipelineId,
            repository: this.context.repository,
            commit: this.context.commit,
            environment: this.context.environment,
            state: this.state,
            stages: Object.fromEntries(
                this.context.results
            ),
            artifacts: Array.from(
                this.context.artifacts.values(),
                artifact => ({
                    name: artifact.name,
                    sha256: artifact.sha256
                })
            ),
            history: this.history
        };
    }
}

// ---------------------- Stage definitions ----------------------

async function checkout(context) {
    return {
        repository: context.repository,
        commit: context.commit,
        checkedOut: true
    };
}

async function build(context) {
    const content = `Build:${context.commit}`;

    const artifact = new Artifact(
        "application-build",
        content
    );

    context.addArtifact(artifact);

    return {
        artifact: artifact.name,
        checksum: artifact.sha256
    };
}

async function test(context) {
    const testCases = [
        { name: "configuration", passed: true },
        { name: "business_logic", passed: true },
        { name: "input_validation", passed: true },
        { name: "error_handling", passed: true }
    ];

    const failed = testCases.filter(item => !item.passed);

    if (failed.length > 0) {
        throw new PipelineError("Automated tests failed.");
    }

    return {
        executed: testCases.length,
        passed: testCases.length,
        failed: 0
    };
}

async function securityScan() {
    const findings = [];

    if (findings.length > 0) {
        throw new PipelineError(
            `Security policy failed: ${findings.length} findings`
        );
    }

    return {
        critical: 0,
        high: 0,
        result: "PASSED"
    };
}

async function packageApplication(context) {
    const artifact = context.artifacts.get("application-build");

    if (!artifact) {
        throw new PipelineError("Build artifact unavailable.");
    }

    return {
        package: "application.tar",
        checksum: artifact.sha256
    };
}

async function deploy(context) {
    if (
        context.environment === "production" &&
        !context.approval
    ) {
        throw new PipelineError(
            "Production approval missing."
        );
    }

    return {
        environment: context.environment,
        deployment: "SUCCESS",
        commit: context.commit
    };
}

// ---------------------- Execution ----------------------

async function main() {
    const context = new PipelineContext({
        repository: "engineering/payment-service",
        commit: "a".repeat(40),
        environment: "production",
        approval: true
    });

    const pipeline = new Pipeline(context, 2);

    pipeline.on("stage_succeeded", event => {
        console.log(
            `[SUCCESS] ${event.stage}`
        );
    });

    pipeline.on("stage_attempt_failed", event => {
        console.error(
            `[RETRY] ${event.stage}: ${event.error}`
        );
    });

    pipeline.addStage(
        new PipelineStage({
            name: "checkout",
            action: checkout
        })
    );

    pipeline.addStage(
        new PipelineStage({
            name: "build",
            action: build,
            dependencies: ["checkout"]
        })
    );

    pipeline.addStage(
        new PipelineStage({
            name: "test",
            action: test,
            dependencies: ["build"],
            retries: 2
        })
    );

    pipeline.addStage(
        new PipelineStage({
            name: "security_scan",
            action: securityScan,
            dependencies: ["build"]
        })
    );

    pipeline.addStage(
        new PipelineStage({
            name: "package",
            action: packageApplication,
            dependencies: ["test", "security_scan"]
        })
    );

    pipeline.addStage(
        new PipelineStage({
            name: "deploy",
            action: deploy,
            dependencies: ["package"],
            approvalRequired: true
        })
    );

    try {
        const report = await pipeline.run();

        await fs.writeFile(
            "pipeline_report.json",
            JSON.stringify(report, null, 2),
            { encoding: "utf8", flag: "w" }
        );

        console.log(JSON.stringify(report, null, 2));

    } catch (error) {
        console.error(
            "Pipeline execution failed:",
            error.message
        );

        process.exitCode = 1;
    }
}

if (require.main === module) {
    main().catch(error => {
        console.error(error);
        process.exitCode = 1;
    });
}

module.exports = {
    Pipeline,
    PipelineContext,
    PipelineStage,
    Artifact,
    PipelineError,
    ValidationError,
    StageState,
    PipelineState
};
