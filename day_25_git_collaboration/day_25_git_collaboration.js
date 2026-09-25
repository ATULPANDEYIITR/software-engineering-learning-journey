/*
 * Git Collaboration: Pull Requests, Code Review, and Git Workflows
 * =================================================================
 *
 * A self-contained JavaScript study implementation covering:
 * - Git repository concepts
 * - Branches and commits
 * - Fast-forward and three-way merges
 * - Pull requests
 * - Code review
 * - CI checks
 * - Branch protection
 * - Merge conflicts
 * - Rebase concepts
 * - Cherry-pick, revert, and reset
 * - Workflow comparison
 * - Security and performance considerations
 * - A complete collaboration simulation
 *
 * Run with:
 *     node git-collaboration.js
 *
 * No external npm packages are required.
 */

"use strict";


// ============================================================================
// 1. BASIC TYPES
// ============================================================================

const ReviewState = Object.freeze({
    COMMENTED: "commented",
    APPROVED: "approved",
    CHANGES_REQUESTED: "changes_requested"
});

const PullRequestState = Object.freeze({
    OPEN: "open",
    MERGED: "merged",
    CLOSED: "closed"
});

const CheckState = Object.freeze({
    PASS: "pass",
    FAIL: "fail",
    PENDING: "pending"
});


// ============================================================================
// 2. UTILITY FUNCTIONS
// ============================================================================

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function deepClone(value) {
    return JSON.parse(JSON.stringify(value));
}

function formatObject(value) {
    return JSON.stringify(value, null, 2);
}


// ============================================================================
// 3. COMMIT AND BRANCH MODELS
// ============================================================================

class Commit {
    constructor(id, author, message, parentIds = [], files = {}) {
        this.id = id;
        this.author = author;
        this.message = message;
        this.parentIds = [...parentIds];
        this.files = deepClone(files);
    }
}

class Branch {
    constructor(name, head = null) {
        this.name = name;
        this.head = head;
    }
}


// ============================================================================
// 4. EDUCATIONAL GIT REPOSITORY
// ============================================================================

class MiniGit {
    /*
     * This class models selected Git behavior.
     *
     * It is intentionally not a replacement for Git. The goal is to expose
     * the relationships between branches, commits, parents, merges, and
     * snapshots using ordinary JavaScript objects.
     */

    constructor() {
        this.commits = new Map();
        this.branches = new Map();
        this.currentBranch = "main";
        this.counter = 0;

        this.branches.set("main", new Branch("main"));
    }

    get head() {
        return this.branches.get(this.currentBranch).head;
    }

    createCommitId() {
        this.counter += 1;
        return `C${String(this.counter).padStart(4, "0")}`;
    }

    getSnapshot(commitId) {
        if (commitId === null) {
            return {};
        }

        const commit = this.commits.get(commitId);

        if (!commit) {
            throw new Error(`Unknown commit: ${commitId}`);
        }

        return deepClone(commit.files);
    }

    commit(author, message, changes) {
        const parentId = this.head;
        const snapshot = this.getSnapshot(parentId);

        for (const [filePath, content] of Object.entries(changes)) {
            if (content === null) {
                delete snapshot[filePath];
            } else {
                snapshot[filePath] = content;
            }
        }

        const commitId = this.createCommitId();
        const parentIds = parentId === null ? [] : [parentId];

        this.commits.set(
            commitId,
            new Commit(
                commitId,
                author,
                message,
                parentIds,
                snapshot
            )
        );

        this.branches.get(this.currentBranch).head = commitId;

        return commitId;
    }

    createBranch(name, fromCommit = this.head) {
        if (this.branches.has(name)) {
            throw new Error(`Branch already exists: ${name}`);
        }

        if (fromCommit !== null && !this.commits.has(fromCommit)) {
            throw new Error(`Unknown commit: ${fromCommit}`);
        }

        this.branches.set(name, new Branch(name, fromCommit));
    }

    checkout(name) {
        if (!this.branches.has(name)) {
            throw new Error(`Unknown branch: ${name}`);
        }

        this.currentBranch = name;
    }

    ancestors(commitId) {
        const result = new Set();

        if (commitId === null) {
            return result;
        }

        const stack = [commitId];

        while (stack.length > 0) {
            const current = stack.pop();

            if (result.has(current)) {
                continue;
            }

            result.add(current);

            const commit = this.commits.get(current);

            for (const parent of commit.parentIds) {
                stack.push(parent);
            }
        }

        return result;
    }

    isAncestor(older, newer) {
        if (older === null) {
            return true;
        }

        return this.ancestors(newer).has(older);
    }

    findMergeBase(first, second) {
        if (first === null || second === null) {
            return null;
        }

        const firstAncestors = this.ancestors(first);
        const secondAncestors = this.ancestors(second);

        const common = [...firstAncestors].filter(
            commitId => secondAncestors.has(commitId)
        );

        if (common.length === 0) {
            return null;
        }

        return common.sort(
            (a, b) => this.commits.get(b).id.localeCompare(
                this.commits.get(a).id
            )
        )[0];
    }

    threeWayMerge(base, target, source) {
        const merged = {};
        const paths = new Set([
            ...Object.keys(base),
            ...Object.keys(target),
            ...Object.keys(source)
        ]);

        for (const path of paths) {
            const baseValue = base[path];
            const targetValue = target[path];
            const sourceValue = source[path];

            const targetChanged = targetValue !== baseValue;
            const sourceChanged = sourceValue !== baseValue;

            if (
                targetChanged &&
                sourceChanged &&
                targetValue !== sourceValue
            ) {
                throw new Error(
                    `Merge conflict in '${path}': both branches changed it.`
                );
            }

            const selectedValue = sourceChanged
                ? sourceValue
                : targetValue;

            if (selectedValue !== undefined) {
                merged[path] = selectedValue;
            }
        }

        return merged;
    }

    merge(sourceBranch, message = null) {
        const sourceBranchObject = this.branches.get(sourceBranch);

        if (!sourceBranchObject) {
            throw new Error(`Unknown source branch: ${sourceBranch}`);
        }

        const target = this.head;
        const source = sourceBranchObject.head;

        if (source === null) {
            throw new Error("Cannot merge an empty branch.");
        }

        if (target === source) {
            return source;
        }

        // Fast-forward: target is directly behind source.
        if (this.isAncestor(target, source)) {
            this.branches.get(this.currentBranch).head = source;
            return source;
        }

        // Already integrated.
        if (this.isAncestor(source, target)) {
            return target;
        }

        // Diverged histories require a three-way merge.
        const base = this.findMergeBase(target, source);
        const baseSnapshot = this.getSnapshot(base);
        const targetSnapshot = this.getSnapshot(target);
        const sourceSnapshot = this.getSnapshot(source);

        const mergedFiles = this.threeWayMerge(
            baseSnapshot,
            targetSnapshot,
            sourceSnapshot
        );

        const mergeCommitId = this.createCommitId();

        this.commits.set(
            mergeCommitId,
            new Commit(
                mergeCommitId,
                "merge-bot",
                message || `Merge ${sourceBranch} into ${this.currentBranch}`,
                [target, source],
                mergedFiles
            )
        );

        this.branches.get(this.currentBranch).head = mergeCommitId;

        return mergeCommitId;
    }

    status() {
        const branches = {};

        for (const [name, branch] of this.branches.entries()) {
            branches[name] = branch.head;
        }

        return {
            currentBranch: this.currentBranch,
            head: this.head,
            branches
        };
    }

    log(branchName = this.currentBranch) {
        const branch = this.branches.get(branchName);

        if (!branch) {
            throw new Error(`Unknown branch: ${branchName}`);
        }

        if (branch.head === null) {
            return [];
        }

        const commits = [];
        const visited = new Set();
        const stack = [branch.head];

        while (stack.length > 0) {
            const current = stack.pop();

            if (visited.has(current)) {
                continue;
            }

            visited.add(current);

            const commit = this.commits.get(current);
            commits.push(commit);

            for (const parent of commit.parentIds) {
                stack.push(parent);
            }
        }

        return commits;
    }
}


// ============================================================================
// 5. BASIC BRANCHING
// ============================================================================

function demonstrateBasicBranching() {
    console.log("\n=== BASIC BRANCHING ===");

    const repository = new MiniGit();

    repository.commit(
        "Atul",
        "Create application",
        {
            "README.md": "# Collaboration Application\n"
        }
    );

    repository.createBranch("feature/login");
    repository.checkout("feature/login");

    repository.commit(
        "Atul",
        "Add login validation",
        {
            "login.js": `
function validateLogin(username, password) {
    return Boolean(username && password);
}
`
        }
    );

    repository.checkout("main");

    const mergeCommit = repository.merge(
        "feature/login",
        "Merge login feature"
    );

    console.log("Merge result:", mergeCommit);
    console.log("Repository state:");
    console.log(formatObject(repository.status()));
}


// ============================================================================
// 6. FAST-FORWARD AND THREE-WAY MERGES
// ============================================================================

function demonstrateMergeTypes() {
    console.log("\n=== MERGE TYPES ===");

    const repository = new MiniGit();

    repository.commit(
        "Alice",
        "Initial commit",
        {
            "app.js": "console.log('v1');"
        }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    const featureCommit = repository.commit(
        "Bob",
        "Add feature",
        {
            "feature.js": "export function feature() {}"
        }
    );

    repository.checkout("main");

    const fastForwardResult = repository.merge("feature");

    console.log("Fast-forward result:", fastForwardResult);
    console.log("Expected feature commit:", featureCommit);

    repository.commit(
        "Alice",
        "Update documentation",
        {
            "README.md": "Version 2"
        }
    );

    repository.createBranch("metrics");
    repository.checkout("metrics");

    repository.commit(
        "Bob",
        "Add metrics",
        {
            "metrics.js": "export const metrics = true;"
        }
    );

    repository.checkout("main");

    repository.commit(
        "Alice",
        "Update configuration",
        {
            "config.json": "{\"debug\":false}"
        }
    );

    const mergeCommit = repository.merge(
        "metrics",
        "Merge metrics"
    );

    console.log("Three-way merge commit:", mergeCommit);
    console.log(
        "Merge parents:",
        repository.commits.get(mergeCommit).parentIds
    );
}


// ============================================================================
// 7. PULL REQUESTS
// ============================================================================

class PullRequest {
    constructor(
        number,
        title,
        author,
        sourceBranch,
        targetBranch,
        description
    ) {
        this.number = number;
        this.title = title;
        this.author = author;
        this.sourceBranch = sourceBranch;
        this.targetBranch = targetBranch;
        this.description = description;
        this.state = PullRequestState.OPEN;
        this.reviews = [];
        this.checks = new Map();
    }

    approvals() {
        return this.reviews.filter(
            review => review.state === ReviewState.APPROVED
        ).length;
    }

    hasRequestedChanges() {
        return this.reviews.some(
            review => review.state === ReviewState.CHANGES_REQUESTED
        );
    }
}


class PullRequestService {
    constructor(repository, options = {}) {
        this.repository = repository;
        this.requiredApprovals = options.requiredApprovals ?? 1;
        this.requiredChecks = new Set(options.requiredChecks ?? []);
        this.pullRequests = new Map();
        this.nextNumber = 1;
    }

    openPullRequest({
        title,
        author,
        sourceBranch,
        targetBranch,
        description
    }) {
        assert(
            this.repository.branches.has(sourceBranch),
            "Source branch does not exist."
        );

        assert(
            this.repository.branches.has(targetBranch),
            "Target branch does not exist."
        );

        assert(
            sourceBranch !== targetBranch,
            "Source and target branches must differ."
        );

        const pullRequest = new PullRequest(
            this.nextNumber++,
            title,
            author,
            sourceBranch,
            targetBranch,
            description
        );

        this.pullRequests.set(
            pullRequest.number,
            pullRequest
        );

        return pullRequest;
    }

    getOpenPullRequest(number) {
        const pullRequest = this.pullRequests.get(number);

        if (!pullRequest) {
            throw new Error(`Unknown pull request #${number}`);
        }

        if (pullRequest.state !== PullRequestState.OPEN) {
            throw new Error("Pull request is no longer open.");
        }

        return pullRequest;
    }

    submitReview(number, reviewer, state, comments = []) {
        const pullRequest = this.getOpenPullRequest(number);

        if (reviewer === pullRequest.author) {
            throw new Error("Self-approval is disabled.");
        }

        pullRequest.reviews.push({
            reviewer,
            state,
            comments: [...comments]
        });
    }

    setCheck(number, name, state) {
        const pullRequest = this.getOpenPullRequest(number);
        pullRequest.checks.set(name, state);
    }

    merge(number) {
        const pullRequest = this.getOpenPullRequest(number);

        if (pullRequest.hasRequestedChanges()) {
            throw new Error("Changes have been requested.");
        }

        if (pullRequest.approvals() < this.requiredApprovals) {
            throw new Error("Required approvals have not been received.");
        }

        for (const requiredCheck of this.requiredChecks) {
            if (!pullRequest.checks.has(requiredCheck)) {
                throw new Error(
                    `Missing required check: ${requiredCheck}`
                );
            }

            if (
                pullRequest.checks.get(requiredCheck) !==
                CheckState.PASS
            ) {
                throw new Error(
                    `Check '${requiredCheck}' is not passing.`
                );
            }
        }

        this.repository.checkout(pullRequest.targetBranch);

        const mergeCommit = this.repository.merge(
            pullRequest.sourceBranch,
            `Merge PR #${number}: ${pullRequest.title}`
        );

        pullRequest.state = PullRequestState.MERGED;

        return mergeCommit;
    }
}


function demonstratePullRequest() {
    console.log("\n=== PULL REQUEST ===");

    const repository = new MiniGit();

    repository.commit(
        "maintainer",
        "Initialize application",
        {
            "app.js": "export const application = true;"
        }
    );

    repository.createBranch("feature/audit");
    repository.checkout("feature/audit");

    repository.commit(
        "developer",
        "Add audit logger",
        {
            "audit.js": `
export function audit(event) {
    return {
        event,
        timestamp: Date.now()
    };
}
`
        }
    );

    const service = new PullRequestService(
        repository,
        {
            requiredApprovals: 1,
            requiredChecks: ["tests", "lint"]
        }
    );

    const pullRequest = service.openPullRequest({
        title: "Add audit logging",
        author: "developer",
        sourceBranch: "feature/audit",
        targetBranch: "main",
        description: "Adds a small audit-event abstraction."
    });

    service.submitReview(
        pullRequest.number,
        "reviewer",
        ReviewState.APPROVED,
        ["The change is focused."]
    );

    service.setCheck(
        pullRequest.number,
        "tests",
        CheckState.PASS
    );

    service.setCheck(
        pullRequest.number,
        "lint",
        CheckState.PASS
    );

    const mergeCommit = service.merge(pullRequest.number);

    console.log(
        `PR #${pullRequest.number} merged as ${mergeCommit}.`
    );
}


// ============================================================================
// 8. CODE REVIEW
// ============================================================================

function analyzeCodeChange(change) {
    const findings = [];

    if (!change.after.trim()) {
        findings.push({
            severity: "error",
            message: "Resulting file is empty."
        });
    }

    if (change.after.includes("TODO: SECURITY")) {
        findings.push({
            severity: "security",
            message: "Unresolved security marker found."
        });
    }

    if (
        change.after.includes("password =") &&
        !change.after.includes("hashPassword")
    ) {
        findings.push({
            severity: "security",
            message: "Password handling requires security review."
        });
    }

    const beforeLineCount = change.before.split("\n").length;
    const afterLineCount = change.after.split("\n").length;

    if (
        Math.abs(afterLineCount - beforeLineCount) > 200
    ) {
        findings.push({
            severity: "review",
            message: "Large change; consider splitting it."
        });
    }

    return findings;
}


function demonstrateCodeReview() {
    console.log("\n=== CODE REVIEW ===");

    const change = {
        path: "auth.js",
        before: `
function login(user, password) {
    return false;
}
`,
        after: `
function login(user, password) {
    password = password;
    // TODO: SECURITY
    return true;
}
`
    };

    const findings = analyzeCodeChange(change);

    for (const finding of findings) {
        console.log(
            `[${finding.severity.toUpperCase()}] ${finding.message}`
        );
    }

    console.log(
        "Automated review can enforce objective rules; human review " +
        "examines intent, architecture, maintainability, and context."
    );
}


// ============================================================================
// 9. MERGE CONFLICTS
// ============================================================================

function demonstrateConflict() {
    console.log("\n=== MERGE CONFLICT ===");

    const repository = new MiniGit();

    repository.commit(
        "Alice",
        "Initial configuration",
        {
            "config.txt": "timeout=30"
        }
    );

    repository.createBranch("feature-timeout");
    repository.checkout("feature-timeout");

    repository.commit(
        "Bob",
        "Feature timeout",
        {
            "config.txt": "timeout=60"
        }
    );

    repository.checkout("main");

    repository.commit(
        "Alice",
        "Production timeout",
        {
            "config.txt": "timeout=90"
        }
    );

    try {
        repository.merge("feature-timeout");
    } catch (error) {
        console.log("Expected conflict:", error.message);
    }

    console.log(
        "Conflict resolution requires a deliberate decision because " +
        "both branches changed the same base content differently."
    );
}


// ============================================================================
// 10. REVIEW STATE TRANSITIONS
// ============================================================================

function demonstrateReviewLifecycle() {
    console.log("\n=== REVIEW LIFECYCLE ===");

    const reviewSequence = [
        "open pull request",
        "automated checks start",
        "reviewer comments",
        "author pushes correction",
        "checks run again",
        "reviewer approves",
        "maintainer merges"
    ];

    reviewSequence.forEach(
        (event, index) => console.log(`${index + 1}. ${event}`)
    );
}


// ============================================================================
// 11. WORKFLOW COMPARISON
// ============================================================================

const workflows = [
    {
        name: "Feature Branch",
        branches: "main + short-lived feature branches",
        release: "Merge reviewed features into main",
        use: "General collaborative development"
    },
    {
        name: "GitHub Flow",
        branches: "main + short-lived branches",
        release: "Deploy from main after review",
        use: "Continuous delivery"
    },
    {
        name: "GitLab Flow",
        branches: "Feature branches plus environment/release conventions",
        release: "Promotion through defined environments",
        use: "Teams with explicit deployment environments"
    },
    {
        name: "Trunk-Based Development",
        branches: "Trunk with very short-lived branches or direct integration",
        release: "Frequent integration",
        use: "High integration frequency"
    },
    {
        name: "Git Flow",
        branches: "main, develop, feature, release, and hotfix",
        release: "Structured release branches",
        use: "Products with formal release cycles"
    }
];


function demonstrateWorkflows() {
    console.log("\n=== GIT WORKFLOWS ===");

    for (const workflow of workflows) {
        console.log(`\n${workflow.name}`);
        console.log(`  Branches: ${workflow.branches}`);
        console.log(`  Release: ${workflow.release}`);
        console.log(`  Typical use: ${workflow.use}`);
    }
}


// ============================================================================
// 12. REBASE, CHERRY-PICK, REVERT, RESET
// ============================================================================

function explainHistoryOperations() {
    console.log("\n=== HISTORY OPERATIONS ===");

    const operations = {
        merge: "Combines histories and may create a merge commit.",
        rebase: "Replays commits onto another base and creates new commit IDs.",
        cherryPick: "Applies the effect of an existing commit as a new commit.",
        revert: "Creates a new commit that reverses an earlier change.",
        reset: "Moves a branch reference and can alter index/working-tree state."
    };

    for (const [name, explanation] of Object.entries(operations)) {
        console.log(`${name}: ${explanation}`);
    }

    console.log(
        "\nRebase changes published history. Shared branches require special " +
        "care because rewriting commits changes the history collaborators see."
    );
}


// ============================================================================
// 13. COMMIT MESSAGE VALIDATION
// ============================================================================

function validateCommitMessage(message) {
    const findings = [];
    const cleaned = message.trim();

    if (!cleaned) {
        return ["Commit message is empty."];
    }

    if (cleaned.length > 72) {
        findings.push(
            "Subject is longer than 72 characters."
        );
    }

    if (cleaned.endsWith(".")) {
        findings.push(
            "Subject should normally omit the trailing period."
        );
    }

    const firstCharacter = cleaned[0];

    if (firstCharacter === firstCharacter.toLowerCase()) {
        findings.push(
            "Start the subject with a capitalized word."
        );
    }

    return findings;
}


function demonstrateCommitMessages() {
    console.log("\n=== COMMIT MESSAGE VALIDATION ===");

    const messages = [
        "add login",
        "Add login validation",
        "Add login validation.",
        ""
    ];

    for (const message of messages) {
        const findings = validateCommitMessage(message);

        console.log(`\nMessage: ${JSON.stringify(message)}`);

        if (findings.length === 0) {
            console.log("  Accepted by the example policy.");
        } else {
            findings.forEach(
                finding => console.log(`  - ${finding}`)
            );
        }
    }
}


// ============================================================================
// 14. BRANCH PROTECTION
// ============================================================================

class BranchProtectionPolicy {
    constructor({
        requirePullRequest = true,
        requiredApprovals = 1,
        requirePassingChecks = true,
        allowForcePush = false,
        allowDeletion = false
    } = {}) {
        this.requirePullRequest = requirePullRequest;
        this.requiredApprovals = requiredApprovals;
        this.requirePassingChecks = requirePassingChecks;
        this.allowForcePush = allowForcePush;
        this.allowDeletion = allowDeletion;
    }

    canDirectPush(actor) {
        if (this.requirePullRequest) {
            return {
                allowed: false,
                reason:
                    `Direct push denied for ${actor}: pull request required.`
            };
        }

        return {
            allowed: true,
            reason: `Direct push allowed for ${actor}.`
        };
    }
}


function demonstrateBranchProtection() {
    console.log("\n=== BRANCH PROTECTION ===");

    const policy = new BranchProtectionPolicy({
        requiredApprovals: 2
    });

    console.log(policy.canDirectPush("developer"));

    console.log(
        "Common controls include required reviews, required checks, " +
        "restricted force pushes, and restricted deletion."
    );
}


// ============================================================================
// 15. SECURITY RULES
// ============================================================================

function securityRules() {
    return {
        secrets:
            "Do not commit credentials, API keys, private keys, or passwords.",
        permissions:
            "Use least privilege for repository users, tokens, and automation.",
        pullRequests:
            "Treat external pull-request code as untrusted until validated.",
        ci:
            "Avoid exposing privileged secrets to untrusted CI execution.",
        dependencies:
            "Review dependency changes for security and supply-chain risk.",
        history:
            "Removing a secret from the latest commit does not necessarily " +
            "remove it from repository history.",
        forcePush:
            "Restrict force pushes on shared branches."
    };
}


function demonstrateSecurity() {
    console.log("\n=== SECURITY ===");

    for (const [topic, rule] of Object.entries(securityRules())) {
        console.log(`${topic}: ${rule}`);
    }
}


// ============================================================================
// 16. PERFORMANCE
// ============================================================================

function demonstratePerformanceConsiderations() {
    console.log("\n=== PERFORMANCE ===");

    const considerations = [
        [
            "Repository size",
            "Large binaries increase clone, fetch, and storage costs."
        ],
        [
            "History depth",
            "Shallow clones can reduce initial transfer for suitable CI jobs."
        ],
        [
            "CI duration",
            "Parallel jobs and caching can reduce feedback time."
        ],
        [
            "Pull-request size",
            "Large changes increase review and integration complexity."
        ],
        [
            "Branch lifetime",
            "Long-lived branches accumulate divergence and conflicts."
        ]
    ];

    for (const [topic, explanation] of considerations) {
        console.log(`${topic}: ${explanation}`);
    }
}


// ============================================================================
// 17. COMPLETE COLLABORATION SIMULATOR
// ============================================================================

class CollaborationSimulator {
    constructor() {
        this.repository = new MiniGit();

        this.pullRequests = new PullRequestService(
            this.repository,
            {
                requiredApprovals: 2,
                requiredChecks: [
                    "unit-tests",
                    "lint",
                    "security"
                ]
            }
        );

        this.auditEvents = [];
    }

    recordAudit(actor, action, objectId, details) {
        this.auditEvents.push({
            timestamp: new Date().toISOString(),
            actor,
            action,
            objectId,
            details
        });
    }

    initialize() {
        this.repository.commit(
            "maintainer",
            "Initialize application",
            {
                "README.md": "# Collaboration Application",
                "app.js": "export function main() { return 'ready'; }"
            }
        );
    }

    createFeature() {
        this.repository.createBranch("feature/profile");
        this.repository.checkout("feature/profile");

        const firstCommit = this.repository.commit(
            "developer",
            "Add profile model",
            {
                "profile.js": `
export class Profile {
    constructor(username) {
        this.username = username;
    }
}
`
            }
        );

        this.recordAudit(
            "developer",
            "commit",
            firstCommit,
            "Added profile model."
        );

        const secondCommit = this.repository.commit(
            "developer",
            "Validate profile username",
            {
                "profile.js": `
export class Profile {
    constructor(username) {
        if (!username || !username.trim()) {
            throw new Error("username is required");
        }

        this.username = username.trim();
    }
}
`
            }
        );

        this.recordAudit(
            "developer",
            "commit",
            secondCommit,
            "Added username validation."
        );

        const pullRequest = this.pullRequests.openPullRequest({
            title: "Add user profile validation",
            author: "developer",
            sourceBranch: "feature/profile",
            targetBranch: "main",
            description:
                "Adds a small profile model and username validation."
        });

        this.recordAudit(
            "developer",
            "open",
            `PR-${pullRequest.number}`,
            "Submitted feature for review."
        );

        return pullRequest;
    }

    completeReview(pullRequest) {
        this.pullRequests.submitReview(
            pullRequest.number,
            "reviewer-a",
            ReviewState.APPROVED,
            ["Validation behavior is explicit."]
        );

        this.pullRequests.submitReview(
            pullRequest.number,
            "reviewer-b",
            ReviewState.APPROVED,
            ["The change is focused."]
        );

        for (const check of [
            "unit-tests",
            "lint",
            "security"
        ]) {
            this.pullRequests.setCheck(
                pullRequest.number,
                check,
                CheckState.PASS
            );
        }

        this.recordAudit(
            "reviewer-a",
            "approve",
            `PR-${pullRequest.number}`,
            "Approved."
        );

        this.recordAudit(
            "reviewer-b",
            "approve",
            `PR-${pullRequest.number}`,
            "Approved."
        );

        const mergeCommit = this.pullRequests.merge(
            pullRequest.number
        );

        this.recordAudit(
            "maintainer",
            "merge",
            `PR-${pullRequest.number}`,
            mergeCommit
        );

        return mergeCommit;
    }
}


function demonstrateCompleteWorkflow() {
    console.log("\n=== COMPLETE WORKFLOW ===");

    const simulator = new CollaborationSimulator();

    simulator.initialize();

    const pullRequest = simulator.createFeature();

    console.log(
        `Opened PR #${pullRequest.number}: ${pullRequest.title}`
    );

    const mergeCommit =
        simulator.completeReview(pullRequest);

    console.log(
        `Merged PR #${pullRequest.number} as ${mergeCommit}.`
    );

    console.log("\nAudit trail:");
    console.log(formatObject(simulator.auditEvents));
}


// ============================================================================
// 18. EDGE CASES
// ============================================================================

function demonstrateEdgeCases() {
    console.log("\n=== EDGE CASES ===");

    const repository = new MiniGit();

    try {
        repository.checkout("missing");
    } catch (error) {
        console.log(
            "Unknown branch handled:",
            error.message
        );
    }

    try {
        validateCommitMessage("");
        console.log(
            "Empty commit message was inspected."
        );
    } catch (error) {
        console.log(
            "Unexpected validation error:",
            error.message
        );
    }

    try {
        repository.createBranch("main");
    } catch (error) {
        console.log(
            "Duplicate branch handled:",
            error.message
        );
    }
}


// ============================================================================
// 19. SIMPLE TEST SUITE
// ============================================================================

function testFastForwardMerge() {
    const repository = new MiniGit();

    repository.commit(
        "Alice",
        "Initial",
        { "a.txt": "A" }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    const featureCommit = repository.commit(
        "Bob",
        "Feature",
        { "b.txt": "B" }
    );

    repository.checkout("main");

    const result = repository.merge("feature");

    assert(
        result === featureCommit,
        "Fast-forward should point to the feature commit."
    );

    assert(
        repository.head === featureCommit,
        "Main should point to the feature commit."
    );
}


function testConflictDetection() {
    const repository = new MiniGit();

    repository.commit(
        "Alice",
        "Initial",
        { "config.txt": "A" }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    repository.commit(
        "Bob",
        "Feature change",
        { "config.txt": "B" }
    );

    repository.checkout("main");

    repository.commit(
        "Alice",
        "Main change",
        { "config.txt": "C" }
    );

    let conflictDetected = false;

    try {
        repository.merge("feature");
    } catch (error) {
        conflictDetected = true;
    }

    assert(
        conflictDetected,
        "Conflicting edits should be detected."
    );
}


function testPullRequestPolicy() {
    const repository = new MiniGit();

    repository.commit(
        "maintainer",
        "Initial",
        { "app.js": "x = 1;" }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    repository.commit(
        "developer",
        "Feature",
        { "app.js": "x = 2;" }
    );

    const service = new PullRequestService(
        repository,
        {
            requiredApprovals: 1,
            requiredChecks: ["tests"]
        }
    );

    const pullRequest = service.openPullRequest({
        title: "Feature",
        author: "developer",
        sourceBranch: "feature",
        targetBranch: "main",
        description: "Feature test."
    });

    let rejected = false;

    try {
        service.merge(pullRequest.number);
    } catch (error) {
        rejected = true;
    }

    assert(
        rejected,
        "PR without approval/checks should not merge."
    );

    service.submitReview(
        pullRequest.number,
        "reviewer",
        ReviewState.APPROVED
    );

    service.setCheck(
        pullRequest.number,
        "tests",
        CheckState.PASS
    );

    service.merge(pullRequest.number);

    assert(
        pullRequest.state === PullRequestState.MERGED,
        "Approved and passing PR should merge."
    );
}


function runTests() {
    console.log("\n=== TESTS ===");

    const tests = [
        ["fast-forward merge", testFastForwardMerge],
        ["conflict detection", testConflictDetection],
        ["pull-request policy", testPullRequestPolicy]
    ];

    let passed = 0;

    for (const [name, test] of tests) {
        try {
            test();
            console.log(`PASS: ${name}`);
            passed += 1;
        } catch (error) {
            console.log(
                `FAIL: ${name} -> ${error.message}`
            );
        }
    }

    console.log(
        `${passed}/${tests.length} tests passed.`
    );

    assert(
        passed === tests.length,
        "One or more tests failed."
    );
}


// ============================================================================
// 20. MAIN
// ============================================================================

function main() {
    console.log("=".repeat(78));
    console.log(
        "GIT COLLABORATION: PULL REQUESTS, CODE REVIEW, AND GIT WORKFLOWS"
    );
    console.log("=".repeat(78));

    demonstrateBasicBranching();
    demonstrateMergeTypes();
    demonstratePullRequest();
    demonstrateCodeReview();
    demonstrateConflict();
    demonstrateReviewLifecycle();
    demonstrateWorkflows();
    explainHistoryOperations();
    demonstrateCommitMessages();
    demonstrateBranchProtection();
    demonstrateSecurity();
    demonstratePerformanceConsiderations();
    demonstrateCompleteWorkflow();
    demonstrateEdgeCases();
    runTests();

    console.log("\nProgram completed successfully.");
}


main();
