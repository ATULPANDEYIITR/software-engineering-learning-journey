"use strict";

/*
 * Continuous Integration Pipeline Engine
 *
 * Node.js 18+
 *
 * Features:
 * - Event-driven pipeline execution
 * - Asynchronous automated checks
 * - Concurrent independent checks
 * - Dependency-aware scheduling
 * - Retry policies
 * - Failure propagation
 * - Security scanning
 * - Artifact checksums
 * - Pipeline event history
 * - Execution reporting
 */

const crypto = require("node:crypto");
const EventEmitter = require("node:events");
const assert = require("node:assert/strict");

const PipelineState = Object.freeze({
    PENDING: "PENDING",
    RUNNING: "RUNNING",
    SUCCESS: "SUCCESS",
    FAILED: "FAILED",
    CANCELLED: "CANCELLED"
});

const JobState = Object.freeze({
    PENDING: "PENDING",
    RUNNING: "RUNNING",
    SUCCESS: "SUCCESS",
    FAILED: "FAILED",
    SKIPPED: "SKIPPED"
});

class CIError extends Error {}

class ConfigurationError extends CIError {}

class JobError extends CIError {}


function validateCommit(commit) {
    if (!commit || typeof commit !== "object") {
        throw new TypeError("Commit must be an object.");
    }

    if (!/^[a-f0-9]{7,40}$/.test(commit.id)) {
        throw new ConfigurationError("Invalid commit identifier.");
    }

    if (!/^[A-Za-z0-9._/-]+$/.test(commit.branch)) {
        throw new ConfigurationError("Invalid branch name.");
    }

    if (!commit.author || !commit.author.trim()) {
        throw new ConfigurationError("Commit author is required.");
    }

    return Object.freeze({
        id: commit.id,
        branch: commit.branch,
        author: commit.author,
        message: String(commit.message || "")
    });
}


class PipelineJob {

    constructor({
        name,
        dependencies = [],
        maxRetries = 0,
        execute
    }) {
        if (!name || typeof name !== "string") {
            throw new ConfigurationError("Invalid job name.");
        }

        if (!Number.isInteger(maxRetries) || maxRetries < 0) {
            throw new ConfigurationError("Invalid retry count.");
        }

        if (typeof execute !== "function") {
            throw new ConfigurationError(
                "Job requires an execution function."
            );
        }

        this.name = name;
        this.dependencies = [...dependencies];
        this.maxRetries = maxRetries;
        this.execute = execute;

        this.state = JobState.PENDING;
        this.attempts = 0;
        this.results = [];
        this.error = null;
        this.durationMs = 0;
    }
}


class PipelineValidator {

    static validate(jobs) {
        const names = new Set(jobs.map(job => job.name));

        if (names.size !== jobs.length) {
            throw new ConfigurationError("Duplicate job names.");
        }

        const graph = new Map();

        for (const job of jobs) {
            for (const dependency of job.dependencies) {
                if (!names.has(dependency)) {
                    throw new ConfigurationError(
                        `Unknown dependency: ${dependency}`
                    );
                }

                if (dependency === job.name) {
                    throw new ConfigurationError(
                        "Self-dependency is prohibited."
                    );
                }
            }

            graph.set(job.name, job.dependencies);
        }

        const visited = new Set();
        const active = new Set();

        function visit(name) {
            if (active.has(name)) {
                throw new ConfigurationError(
                    "Circular dependency detected."
                );
            }

            if (visited.has(name)) return;

            active.add(name);

            for (const dependency of graph.get(name)) {
                visit(dependency);
            }

            active.delete(name);
            visited.add(name);
        }

        for (const name of names) {
            visit(name);
        }
    }
}


class ArtifactStore {

    constructor() {
        this.artifacts = new Map();
    }

    publish(name, content) {
        if (!name || this.artifacts.has(name)) {
            throw new CIError("Invalid or duplicate artifact.");
        }

        const data = Buffer.from(content, "utf8");

        const checksum = crypto
            .createHash("sha256")
            .update(data)
            .digest("hex");

        const artifact = Object.freeze({
            name,
            content: data.toString("utf8"),
            checksum,
            size: data.length,
            createdAt: new Date().toISOString()
        });

        this.artifacts.set(name, artifact);

        return artifact;
    }

    verify(name) {
        const artifact = this.artifacts.get(name);

        if (!artifact) return false;

        const calculated = crypto
            .createHash("sha256")
            .update(artifact.content, "utf8")
            .digest("hex");

        return calculated === artifact.checksum;
    }
}


class CIEngine extends EventEmitter {

    constructor({ maxConcurrency = 3 } = {}) {
        super();

        if (!Number.isInteger(maxConcurrency) || maxConcurrency < 1) {
            throw new ConfigurationError(
                "Concurrency must be a positive integer."
            );
        }

        this.maxConcurrency = maxConcurrency;
        this.artifacts = new ArtifactStore();
        this.history = [];
        this.running = false;
    }

    async runJob(job) {
        job.state = JobState.RUNNING;

        const start = performance.now();

        this.emit("jobStarted", {
            name: job.name,
            attempt: job.attempts + 1
        });

        for (
            let attempt = 0;
            attempt <= job.maxRetries;
            attempt++
        ) {
            job.attempts++;

            try {
                const result = await job.execute();

                if (!result || result.passed !== true) {
                    throw new JobError(
                        result?.message || "Job validation failed."
                    );
                }

                job.results.push(result);
                job.state = JobState.SUCCESS;

                job.durationMs = performance.now() - start;

                this.emit("jobSucceeded", {
                    name: job.name,
                    attempts: job.attempts
                });

                return true;

            } catch (error) {
                job.error = error.message;

                this.emit("jobAttemptFailed", {
                    name: job.name,
                    attempt: job.attempts,
                    error: error.message
                });
            }
        }

        job.state = JobState.FAILED;
        job.durationMs = performance.now() - start;

        this.emit("jobFailed", {
            name: job.name,
            error: job.error
        });

        return false;
    }

    async executePipeline({ id, commit, trigger, jobs }) {
        if (this.running) {
            throw new CIError("Engine already executing a pipeline.");
        }

        if (!id || typeof id !== "string") {
            throw new ConfigurationError("Pipeline ID is required.");
        }

        const validatedCommit = validateCommit(commit);

        if (!Array.isArray(jobs) || jobs.length === 0) {
            throw new ConfigurationError("Pipeline has no jobs.");
        }

        PipelineValidator.validate(jobs);

        if (jobs.some(job => job.state !== JobState.PENDING)) {
            throw new CIError("Jobs must be in their initial state.");
        }

        this.running = true;

        const pipeline = {
            id,
            commit: validatedCommit,
            trigger,
            state: PipelineState.RUNNING,
            startedAt: new Date().toISOString(),
            jobs
        };

        this.emit("pipelineStarted", {
            id,
            commit: validatedCommit.id
        });

        try {
            const remaining = new Map(
                jobs.map(job => [job.name, job])
            );

            while (remaining.size > 0) {
                const ready = [...remaining.values()].filter(job =>
                    job.dependencies.every(dependency => {
                        const parent = jobs.find(
                            candidate => candidate.name === dependency
                        );

                        return parent.state === JobState.SUCCESS;
                    })
                );

                const blocked = [...remaining.values()].filter(job =>
                    job.dependencies.some(dependency => {
                        const parent = jobs.find(
                            candidate => candidate.name === dependency
                        );

                        return [
                            JobState.FAILED,
                            JobState.SKIPPED
                        ].includes(parent.state);
                    })
                );

                for (const job of blocked) {
                    job.state = JobState.SKIPPED;
                    job.error = "Dependency failed.";
                    remaining.delete(job.name);
                }

                if (ready.length === 0) {
                    if (remaining.size > 0) {
                        throw new CIError(
                            "Pipeline cannot make further progress."
                        );
                    }

                    break;
                }

                const batch = ready.slice(0, this.maxConcurrency);

                const results = await Promise.all(
                    batch.map(async job => ({
                        job,
                        success: await this.runJob(job)
                    }))
                );

                for (const { job } of results) {
                    remaining.delete(job.name);
                }
            }

            const failed = jobs.some(job =>
                job.state === JobState.FAILED ||
                job.state === JobState.SKIPPED
            );

            pipeline.state = failed
                ? PipelineState.FAILED
                : PipelineState.SUCCESS;

            if (pipeline.state === PipelineState.SUCCESS) {
                const artifact = this.artifacts.publish(
                    `${id}.build.txt`,
                    JSON.stringify({
                        commit: validatedCommit.id,
                        branch: validatedCommit.branch,
                        status: "BUILD_SUCCESS"
                    })
                );

                if (!this.artifacts.verify(artifact.name)) {
                    throw new CIError("Artifact integrity check failed.");
                }
            }

            this.emit("pipelineCompleted", {
                id,
                state: pipeline.state
            });

        } catch (error) {
            pipeline.state = PipelineState.FAILED;
            pipeline.error = error.message;

            this.emit("pipelineError", {
                id,
                error: error.message
            });

        } finally {
            pipeline.completedAt = new Date().toISOString();
            this.history.push(pipeline);
            this.running = false;
        }

        return pipeline;
    }

    report(pipeline) {
        return {
            id: pipeline.id,
            state: pipeline.state,
            commit: pipeline.commit,
            duration: {
                startedAt: pipeline.startedAt,
                completedAt: pipeline.completedAt
            },
            jobs: pipeline.jobs.map(job => ({
                name: job.name,
                state: job.state,
                attempts: job.attempts,
                durationMs: Number(job.durationMs.toFixed(2)),
                error: job.error
            })),
            error: pipeline.error || null
        };
    }
}


function createChecks() {

    return [
        new PipelineJob({
            name: "lint",
            execute: async () => ({
                passed: true,
                message: "Static formatting checks passed."
            })
        }),

        new PipelineJob({
            name: "unit-tests",
            dependencies: ["lint"],
            execute: async () => {
                const add = (a, b) => a + b;

                assert.equal(add(10, 20), 30);
                assert.equal(add(-5, 5), 0);
                assert.equal(add(0, 0), 0);

                return {
                    passed: true,
                    message: "Three unit tests passed."
                };
            }
        }),

        new PipelineJob({
            name: "security",
            dependencies: ["lint"],
            execute: async () => {
                const source = `
                    const token = process.env.API_TOKEN;
                    const password = process.env.DB_PASSWORD;
                `;

                const hardcodedSecret =
                    /\b(?:password|token|api_key)\s*=\s*["'][^"']+["']/i;

                return {
                    passed: !hardcodedSecret.test(source),
                    message: "Credential scanning completed."
                };
            }
        }),

        new PipelineJob({
            name: "build",
            dependencies: ["unit-tests", "security"],
            maxRetries: 1,
            execute: async () => ({
                passed: true,
                message: "Build package generated."
            })
        })
    ];
}


async function main() {
    const engine = new CIEngine({
        maxConcurrency: 2
    });

    engine.on("pipelineStarted", event =>
        console.log("Pipeline started:", event)
    );

    engine.on("jobSucceeded", event =>
        console.log("Job succeeded:", event.name)
    );

    engine.on("jobFailed", event =>
        console.error("Job failed:", event.name, event.error)
    );

    engine.on("pipelineCompleted", event =>
        console.log("Pipeline completed:", event)
    );

    const pipeline = await engine.executePipeline({
        id: "CI-1001",
        trigger: "PULL_REQUEST",
        commit: {
            id: "a123456",
            branch: "feature/payment",
            author: "developer@example.com",
            message: "Add payment validation"
        },
        jobs: createChecks()
    });

    console.log("\nPIPELINE REPORT");

    console.log(
        JSON.stringify(engine.report(pipeline), null, 2)
    );

    assert.equal(pipeline.state, PipelineState.SUCCESS);

    console.log("\nAll pipeline assertions passed.");
}


main().catch(error => {
    console.error("Fatal error:", error);
    process.exitCode = 1;
});
