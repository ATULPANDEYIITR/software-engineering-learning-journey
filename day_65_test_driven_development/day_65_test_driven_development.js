"use strict";

/*
 * Test-Driven Development: Red-Green-Refactor
 *
 * Event-driven test execution and policy evaluation for a
 * software release workflow.
 *
 * Run:
 *     node tdd_workflow.js
 *
 * Uses only Node.js standard-library functionality.
 */

const assert = require("node:assert/strict");
const { EventEmitter } = require("node:events");
const { randomUUID } = require("node:crypto");

// ============================================================
// DOMAIN ERRORS
// ============================================================

class TddError extends Error {}
class TestFailureError extends TddError {}
class WorkflowStateError extends TddError {}
class PolicyViolationError extends TddError {}

// ============================================================
// ENUMERATIONS
// ============================================================

const Stage = Object.freeze({
    RED: "RED",
    GREEN: "GREEN",
    REFACTOR: "REFACTOR"
});

const TestStatus = Object.freeze({
    PENDING: "PENDING",
    PASSED: "PASSED",
    FAILED: "FAILED",
    SKIPPED: "SKIPPED"
});

const ChangeStatus = Object.freeze({
    DRAFT: "DRAFT",
    REVIEW: "REVIEW",
    APPROVED: "APPROVED",
    MERGED: "MERGED",
    REJECTED: "REJECTED"
});

// ============================================================
// TEST CASE MODEL
// ============================================================

class TestCase {
    constructor(name, execute, options = {}) {
        if (!name || typeof name !== "string") {
            throw new TypeError("Test name must be a non-empty string.");
        }

        if (typeof execute !== "function") {
            throw new TypeError("Test execution must be a function.");
        }

        this.id = randomUUID();
        this.name = name;
        this.execute = execute;
        this.timeoutMs = options.timeoutMs ?? 2000;
        this.status = TestStatus.PENDING;
        this.durationMs = 0;
        this.error = null;

        if (!Number.isInteger(this.timeoutMs) || this.timeoutMs <= 0) {
            throw new RangeError("Timeout must be a positive integer.");
        }
    }
}

// ============================================================
// ASYNCHRONOUS TEST EXECUTION ENGINE
// ============================================================

class TestRunner extends EventEmitter {
    constructor(options = {}) {
        super();

        this.tests = new Map();
        this.maxConcurrency = options.maxConcurrency ?? 4;
        this.running = false;

        if (
            !Number.isInteger(this.maxConcurrency) ||
            this.maxConcurrency < 1
        ) {
            throw new RangeError("Concurrency must be positive.");
        }
    }

    register(testCase) {
        if (!(testCase instanceof TestCase)) {
            throw new TypeError("Expected a TestCase instance.");
        }

        if (this.tests.has(testCase.name)) {
            throw new TddError(
                `Duplicate test name: ${testCase.name}`
            );
        }

        this.tests.set(testCase.name, testCase);

        this.emit("registered", {
            id: testCase.id,
            name: testCase.name
        });
    }

    async executeWithTimeout(testCase) {
        let timer;

        try {
            await Promise.race([
                Promise.resolve().then(testCase.execute),
                new Promise((_, reject) => {
                    timer = setTimeout(
                        () => reject(
                            new Error(
                                `Test timed out after ${testCase.timeoutMs}ms`
                            )
                        ),
                        testCase.timeoutMs
                    );
                })
            ]);

            testCase.status = TestStatus.PASSED;
            testCase.error = null;

        } catch (error) {
            testCase.status = TestStatus.FAILED;
            testCase.error = error.message;

        } finally {
            clearTimeout(timer);
        }
    }

    async run() {
        if (this.running) {
            throw new WorkflowStateError(
                "Test runner is already executing."
            );
        }

        this.running = true;

        const queue = [...this.tests.values()];
        let nextIndex = 0;

        const worker = async () => {
            while (nextIndex < queue.length) {
                const testCase = queue[nextIndex++];

                const start = process.hrtime.bigint();

                await this.executeWithTimeout(testCase);

                testCase.durationMs = Number(
                    process.hrtime.bigint() - start
                ) / 1_000_000;

                this.emit("test-completed", {
                    name: testCase.name,
                    status: testCase.status,
                    durationMs: testCase.durationMs,
                    error: testCase.error
                });
            }
        };

        try {
            await Promise.all(
                Array.from(
                    {
                        length: Math.min(
                            this.maxConcurrency,
                            queue.length
                        )
                    },
                    worker
                )
            );

        } finally {
            this.running = false;
        }

        return this.report();
    }

    report() {
        const results = [...this.tests.values()];

        const passed = results.filter(
            test => test.status === TestStatus.PASSED
        ).length;

        const failed = results.filter(
            test => test.status === TestStatus.FAILED
        ).length;

        return {
            total: results.length,
            passed,
            failed,
            successful: failed === 0,
            tests: results.map(test => ({
                name: test.name,
                status: test.status,
                durationMs: Number(test.durationMs.toFixed(3)),
                error: test.error
            }))
        };
    }
}

// ============================================================
// CHANGESET AND REVIEW MODEL
// ============================================================

class ChangeSet {
    constructor(id, sourceBranch, targetBranch, commits) {
        if (!id || !sourceBranch || !targetBranch) {
            throw new TypeError("ChangeSet identifiers are required.");
        }

        if (sourceBranch === targetBranch) {
            throw new PolicyViolationError(
                "Source and target branches must differ."
            );
        }

        if (!Array.isArray(commits) || commits.length === 0) {
            throw new PolicyViolationError(
                "A changeset must contain commits."
            );
        }

        this.id = id;
        this.sourceBranch = sourceBranch;
        this.targetBranch = targetBranch;
        this.commits = [...new Set(commits)];
        this.status = ChangeStatus.DRAFT;
        this.reviewers = new Map();
        this.checks = new Map();
        this.conversations = new Set();
        this.baseSynchronized = true;
    }

    requestReview(reviewer, eligible = true) {
        if (!eligible) {
            throw new PolicyViolationError(
                "Reviewer is not eligible."
            );
        }

        if (!reviewer) {
            throw new TypeError("Reviewer identity is required.");
        }

        this.reviewers.set(reviewer, "PENDING");
    }

    recordReview(reviewer, decision) {
        if (!this.reviewers.has(reviewer)) {
            throw new PolicyViolationError(
                "Reviewer was not requested."
            );
        }

        if (!["APPROVED", "CHANGES_REQUESTED", "COMMENTED"].includes(decision)) {
            throw new TypeError("Invalid review decision.");
        }

        this.reviewers.set(reviewer, decision);
    }

    setCheck(name, passed) {
        if (typeof passed !== "boolean") {
            throw new TypeError("Check result must be boolean.");
        }

        this.checks.set(name, passed);
    }

    addConversation(id) {
        this.conversations.add(id);
    }

    resolveConversation(id) {
        if (!this.conversations.has(id)) {
            throw new TddError("Conversation does not exist.");
        }

        this.conversations.delete(id);
    }

    synchronizeBase() {
        this.baseSynchronized = true;
    }
}

// ============================================================
// BRANCH PROTECTION POLICY
// ============================================================

class BranchProtectionPolicy {
    constructor({
        requiredReviews = 1,
        requiredChecks = [],
        requireConversationsResolved = true,
        requireLinearHistory = true,
        allowDirectPush = false,
        allowForcePush = false,
        allowDeletion = false,
        allowAdministratorBypass = false
    } = {}) {
        if (
            !Number.isInteger(requiredReviews) ||
            requiredReviews < 0
        ) {
            throw new RangeError("Invalid review requirement.");
        }

        this.requiredReviews = requiredReviews;
        this.requiredChecks = new Set(requiredChecks);
        this.requireConversationsResolved =
            requireConversationsResolved;
        this.requireLinearHistory = requireLinearHistory;
        this.allowDirectPush = allowDirectPush;
        this.allowForcePush = allowForcePush;
        this.allowDeletion = allowDeletion;
        this.allowAdministratorBypass = allowAdministratorBypass;
    }
}

// ============================================================
// MERGE ELIGIBILITY ENGINE
// ============================================================

class MergePolicyEngine {
    evaluate(changeSet, policy, options = {}) {
        const reasons = [];

        const approvals = [...changeSet.reviewers.values()].filter(
            decision => decision === "APPROVED"
        ).length;

        const hasRequestedChanges = [...changeSet.reviewers.values()].some(
            decision => decision === "CHANGES_REQUESTED"
        );

        if (approvals < policy.requiredReviews) {
            reasons.push("Insufficient eligible approvals.");
        }

        if (hasRequestedChanges) {
            reasons.push("A reviewer has requested changes.");
        }

        for (const requiredCheck of policy.requiredChecks) {
            if (changeSet.checks.get(requiredCheck) !== true) {
                reasons.push(
                    `Required check failed or missing: ${requiredCheck}`
                );
            }
        }

        if (
            policy.requireConversationsResolved &&
            changeSet.conversations.size > 0
        ) {
            reasons.push("Unresolved review conversations exist.");
        }

        if (!changeSet.baseSynchronized) {
            reasons.push("Source branch is not synchronized.");
        }

        if (
            policy.requireLinearHistory &&
            options.linearHistory !== true
        ) {
            reasons.push("Linear history requirement is not satisfied.");
        }

        const bypassRequested = options.administratorBypass === true;

        if (bypassRequested && !policy.allowAdministratorBypass) {
            reasons.push("Administrator bypass is prohibited.");
        }

        const eligible =
            reasons.length === 0 ||
            (
                bypassRequested &&
                policy.allowAdministratorBypass
            );

        return {
            eligible,
            approvals,
            reasons: eligible && bypassRequested
                ? ["Authorized administrator bypass."]
                : reasons
        };
    }

    merge(changeSet, policy, options = {}) {
        if (changeSet.status === ChangeStatus.MERGED) {
            throw new WorkflowStateError("ChangeSet is already merged.");
        }

        const result = this.evaluate(
            changeSet,
            policy,
            options
        );

        if (!result.eligible) {
            throw new PolicyViolationError(
                result.reasons.join(" ")
            );
        }

        changeSet.status = ChangeStatus.MERGED;

        return result;
    }
}

// ============================================================
// RED-GREEN-REFACTOR WORKFLOW TRACKER
// ============================================================

class TddCycle {
    constructor() {
        this.stage = Stage.RED;
        this.history = [];
        this.implementationVersion = 0;
        this.lastTestReport = null;
    }

    transition(nextStage, evidence = {}) {
        const allowed = {
            [Stage.RED]: [Stage.GREEN],
            [Stage.GREEN]: [Stage.REFACTOR],
            [Stage.REFACTOR]: [Stage.RED, Stage.GREEN]
        };

        if (!allowed[this.stage].includes(nextStage)) {
            throw new WorkflowStateError(
                `Invalid transition: ${this.stage} -> ${nextStage}`
            );
        }

        if (
            nextStage === Stage.GREEN &&
            evidence.testsPassed !== true
        ) {
            throw new TestFailureError(
                "Green requires passing tests."
            );
        }

        if (
            nextStage === Stage.REFACTOR &&
            evidence.testsPassed !== true
        ) {
            throw new TestFailureError(
                "Refactoring requires a passing test suite."
            );
        }

        this.stage = nextStage;

        if (nextStage === Stage.REFACTOR) {
            this.implementationVersion++;
        }

        this.history.push({
            stage: nextStage,
            timestamp: new Date().toISOString(),
            evidence
        });
    }
}

// ============================================================
// DEMONSTRATION
// ============================================================

async function main() {
    const runner = new TestRunner({
        maxConcurrency: 3
    });

    runner.on("test-completed", event => {
        console.log(
            `[${event.status}] ${event.name} ` +
            `(${event.durationMs.toFixed(2)} ms)`
        );
    });

    const tests = [
        new TestCase("addition", async () => {
            assert.equal(2 + 3, 5);
        }),

        new TestCase("empty collection", () => {
            assert.deepEqual([], []);
        }),

        new TestCase("duplicate prevention", () => {
            assert.equal(new Set([1, 1, 2]).size, 2);
        }),

        new TestCase("invalid state detection", () => {
            assert.throws(
                () => {
                    throw new WorkflowStateError("Invalid transition");
                },
                WorkflowStateError
            );
        }),

        new TestCase("asynchronous operation", async () => {
            const value = await Promise.resolve(42);
            assert.equal(value, 42);
        }),

        new TestCase("intentional failure detection", () => {
            assert.equal(2 * 2, 4);
        })
    ];

    for (const test of tests) {
        runner.register(test);
    }

    const report = await runner.run();

    console.log("\nTEST REPORT");
    console.log(JSON.stringify(report, null, 2));

    const cycle = new TddCycle();

    cycle.transition(Stage.GREEN, {
        testsPassed: true
    });

    cycle.transition(Stage.REFACTOR, {
        testsPassed: true,
        behaviorPreserved: true
    });

    console.log("\nTDD CYCLE");
    console.log(JSON.stringify(cycle.history, null, 2));

    // Repository governance demonstration.
    const change = new ChangeSet(
        "PR-2026-001",
        "feature/payment-validation",
        "main",
        ["commit-a1", "commit-a2"]
    );

    change.requestReview("reviewer-1");
    change.requestReview("reviewer-2");

    change.recordReview("reviewer-1", "APPROVED");
    change.recordReview("reviewer-2", "APPROVED");

    change.setCheck("unit-tests", true);
    change.setCheck("integration-tests", true);

    const policy = new BranchProtectionPolicy({
        requiredReviews: 2,
        requiredChecks: [
            "unit-tests",
            "integration-tests"
        ],
        requireConversationsResolved: true,
        requireLinearHistory: true
    });

    const engine = new MergePolicyEngine();

    const eligibility = engine.evaluate(
        change,
        policy,
        { linearHistory: true }
    );

    console.log("\nMERGE ELIGIBILITY");
    console.log(JSON.stringify(eligibility, null, 2));

    if (eligibility.eligible) {
        engine.merge(
            change,
            policy,
            { linearHistory: true }
        );
    }

    console.log(`Final change status: ${change.status}`);

    // Exit non-zero if any test fails.
    if (!report.successful) {
        process.exitCode = 1;
    }
}

main().catch(error => {
    console.error("Execution failed:", error.message);
    process.exitCode = 1;
});
