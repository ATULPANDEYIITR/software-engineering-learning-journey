"use strict";

/*
 * Git Fundamentals: repositories, staging, commits, branches and history.
 *
 * This file complements the Python study implementation by demonstrating
 * Git concepts with JavaScript data structures, classes, Maps, validation,
 * immutable-style snapshots, and executable examples.
 *
 * Run:
 *   node git-fundamentals.js
 *
 * No external npm packages are required.
 */

const crypto = require("crypto");
const assert = require("assert");

// ---------------------------------------------------------------------------
// 1. Content-addressed hashing
// ---------------------------------------------------------------------------

function gitHash(type, content) {
    const bytes = Buffer.from(content, "utf8");
    const header = Buffer.from(`${type} ${bytes.length}\0`, "utf8");

    return crypto
        .createHash("sha1")
        .update(Buffer.concat([header, bytes]))
        .digest("hex");
}

function shortHash(objectId, length = 8) {
    return objectId.slice(0, length);
}

function normalizePath(path) {
    if (typeof path !== "string") {
        throw new TypeError("Path must be a string.");
    }

    const normalized = path.replaceAll("\\", "/").replace(/^\/+|\/+$/g, "");

    if (
        !normalized ||
        normalized === ".." ||
        normalized.startsWith("../") ||
        normalized.includes("/../") ||
        normalized.includes("\0")
    ) {
        throw new Error(`Invalid repository path: ${path}`);
    }

    return normalized;
}

function validateBranchName(name) {
    if (
        typeof name !== "string" ||
        !name ||
        name.startsWith("-") ||
        name.endsWith(".") ||
        name.endsWith("/") ||
        name.includes("..") ||
        name.includes(" ") ||
        name.includes("~") ||
        name.includes("^")
    ) {
        throw new Error(`Invalid branch name: ${name}`);
    }
}

// ---------------------------------------------------------------------------
// 2. Git-like objects
// ---------------------------------------------------------------------------

class Blob {
    constructor(content) {
        this.content = Buffer.from(content, "utf8");
    }

    serialize() {
        return this.content;
    }

    get id() {
        return gitHash("blob", this.content);
    }
}

class Tree {
    constructor(entries) {
        this.entries = new Map(entries);
    }

    serialize() {
        const lines = [...this.entries.entries()]
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([path, entry]) =>
                `${entry.mode} ${entry.type} ${entry.objectId} ${path}`
            );

        return lines.join("\n");
    }

    get id() {
        return gitHash("tree", this.serialize());
    }
}

class Commit {
    constructor({ treeId, parents, author, message }) {
        this.treeId = treeId;
        this.parents = [...parents];
        this.author = author;
        this.message = message.trim();

        if (!this.message) {
            throw new Error("Commit message cannot be empty.");
        }
    }

    serialize() {
        const lines = [`tree ${this.treeId}`];

        for (const parent of this.parents) {
            lines.push(`parent ${parent}`);
        }

        lines.push(`author ${this.author}`);
        lines.push("");
        lines.push(this.message);

        return lines.join("\n");
    }

    get id() {
        return gitHash("commit", this.serialize());
    }
}

// ---------------------------------------------------------------------------
// 3. Repository
// ---------------------------------------------------------------------------

class GitRepository {
    constructor(author = "Student <student@example.com>") {
        this.author = author;
        this.objects = new Map();
        this.workingTree = new Map();
        this.index = new Map();
        this.branches = new Map();

        this.headBranch = null;
        this.detachedHead = null;
    }

    init(branch = "main") {
        validateBranchName(branch);

        if (this.branches.size > 0) {
            throw new Error("Repository has already been initialized.");
        }

        this.branches.set(branch, null);
        this.headBranch = branch;
    }

    head() {
        if (this.headBranch !== null) {
            return this.branches.get(this.headBranch);
        }

        return this.detachedHead;
    }

    writeBlob(content) {
        const blob = new Blob(content);
        this.objects.set(blob.id, blob);
        return blob.id;
    }

    writeTree(files) {
        const entries = new Map();

        for (const path of [...files.keys()].sort()) {
            const normalized = normalizePath(path);
            const content = files.get(path);
            const blobId = this.writeBlob(content);

            entries.set(normalized, {
                mode: "100644",
                type: "blob",
                objectId: blobId
            });
        }

        const tree = new Tree(entries);
        this.objects.set(tree.id, tree);

        return tree.id;
    }

    writeCommit(treeId, parents, message) {
        const commit = new Commit({
            treeId,
            parents,
            author: this.author,
            message
        });

        this.objects.set(commit.id, commit);
        return commit.id;
    }

    getCommit(commitId) {
        const object = this.objects.get(commitId);

        if (!(object instanceof Commit)) {
            throw new Error(`Commit not found: ${commitId}`);
        }

        return object;
    }

    getTree(treeId) {
        const object = this.objects.get(treeId);

        if (!(object instanceof Tree)) {
            throw new Error(`Tree not found: ${treeId}`);
        }

        return object;
    }

    writeFile(path, content) {
        const normalized = normalizePath(path);
        this.workingTree.set(normalized, Buffer.from(content, "utf8"));
    }

    deleteFile(path) {
        const normalized = normalizePath(path);
        this.workingTree.delete(normalized);
    }

    stage(...paths) {
        for (const path of paths) {
            const normalized = normalizePath(path);

            if (this.workingTree.has(normalized)) {
                this.index.set(
                    normalized,
                    Buffer.from(this.workingTree.get(normalized))
                );
            } else {
                this.index.delete(normalized);
            }
        }
    }

    stageAll() {
        this.index = cloneFileMap(this.workingTree);
    }

    snapshotFromCommit(commitId) {
        const commit = this.getCommit(commitId);
        const tree = this.getTree(commit.treeId);
        const snapshot = new Map();

        for (const [path, entry] of tree.entries) {
            const blob = this.objects.get(entry.objectId);

            if (!(blob instanceof Blob)) {
                throw new Error(`Tree entry is not a blob: ${path}`);
            }

            snapshot.set(path, Buffer.from(blob.content));
        }

        return snapshot;
    }

    commit(message) {
        if (this.index.size === 0) {
            throw new Error("Nothing is staged.");
        }

        const treeId = this.writeTree(this.index);
        const parent = this.head();
        const parents = parent ? [parent] : [];
        const commitId = this.writeCommit(treeId, parents, message);

        this.updateHead(commitId);
        this.workingTree = cloneFileMap(this.index);

        return commitId;
    }

    updateHead(commitId) {
        if (this.headBranch !== null) {
            this.branches.set(this.headBranch, commitId);
        } else {
            this.detachedHead = commitId;
        }
    }

    createBranch(name, startPoint = this.head()) {
        validateBranchName(name);

        if (this.branches.has(name)) {
            throw new Error(`Branch already exists: ${name}`);
        }

        if (!startPoint) {
            throw new Error("A branch needs a starting commit.");
        }

        this.getCommit(startPoint);
        this.branches.set(name, startPoint);
    }

    checkout(target) {
        if (this.branches.has(target)) {
            this.headBranch = target;
            this.detachedHead = null;

            const commitId = this.branches.get(target);

            if (commitId) {
                this.restoreCommit(commitId);
            }

            return;
        }

        this.getCommit(target);

        this.headBranch = null;
        this.detachedHead = target;
        this.restoreCommit(target);
    }

    restoreCommit(commitId) {
        const snapshot = this.snapshotFromCommit(commitId);
        this.workingTree = cloneFileMap(snapshot);
        this.index = cloneFileMap(snapshot);
    }

    status() {
        const headSnapshot = this.head()
            ? this.snapshotFromCommit(this.head())
            : new Map();

        const paths = new Set([
            ...headSnapshot.keys(),
            ...this.index.keys(),
            ...this.workingTree.keys()
        ]);

        const result = {
            staged: [],
            modified: [],
            deleted: [],
            untracked: []
        };

        for (const path of [...paths].sort()) {
            const head = headSnapshot.get(path);
            const staged = this.index.get(path);
            const working = this.workingTree.get(path);

            if (!buffersEqual(staged, head)) {
                if (staged === undefined) {
                    result.staged.push(`deleted: ${path}`);
                } else {
                    result.staged.push(`staged: ${path}`);
                }
            }

            if (!buffersEqual(working, staged)) {
                if (working === undefined && staged !== undefined) {
                    result.deleted.push(path);
                } else if (staged === undefined && working !== undefined) {
                    result.untracked.push(path);
                } else {
                    result.modified.push(path);
                }
            }
        }

        return result;
    }

    log(limit = 20) {
        const history = [];
        let current = this.head();

        while (current && history.length < limit) {
            const commit = this.getCommit(current);

            history.push({
                id: current,
                message: commit.message
            });

            current = commit.parents[0] ?? null;
        }

        return history;
    }

    ancestors(commitId) {
        if (!commitId) {
            return new Map();
        }

        const distances = new Map([[commitId, 0]]);
        const queue = [commitId];

        while (queue.length > 0) {
            const current = queue.shift();
            const distance = distances.get(current);
            const commit = this.getCommit(current);

            for (const parent of commit.parents) {
                if (!distances.has(parent)) {
                    distances.set(parent, distance + 1);
                    queue.push(parent);
                }
            }
        }

        return distances;
    }

    mergeBase(first, second) {
        const firstAncestors = this.ancestors(first);
        const secondAncestors = this.ancestors(second);

        const common = [...firstAncestors.keys()].filter((id) =>
            secondAncestors.has(id)
        );

        if (common.length === 0) {
            return null;
        }

        common.sort((a, b) => {
            const aDistance = Math.max(
                firstAncestors.get(a),
                secondAncestors.get(a)
            );

            const bDistance = Math.max(
                firstAncestors.get(b),
                secondAncestors.get(b)
            );

            return aDistance - bDistance;
        });

        return common[0];
    }

    verifyIntegrity() {
        const problems = [];

        for (const [id, object] of this.objects) {
            let expected;

            if (object instanceof Blob) {
                expected = object.id;
            } else if (object instanceof Tree) {
                expected = object.id;
            } else if (object instanceof Commit) {
                expected = object.id;
            } else {
                problems.push(`Unknown object type: ${id}`);
                continue;
            }

            if (expected !== id) {
                problems.push(
                    `Object ${id} failed integrity check; expected ${expected}`
                );
            }
        }

        for (const [branch, commitId] of this.branches) {
            if (commitId && !this.objects.has(commitId)) {
                problems.push(
                    `Branch ${branch} points to missing commit ${commitId}`
                );
            }
        }

        return problems;
    }
}

// ---------------------------------------------------------------------------
// 4. Utility functions
// ---------------------------------------------------------------------------

function cloneFileMap(source) {
    return new Map(
        [...source.entries()].map(([path, content]) => [
            path,
            Buffer.from(content)
        ])
    );
}

function buffersEqual(first, second) {
    if (first === undefined || second === undefined) {
        return first === second;
    }

    return Buffer.compare(first, second) === 0;
}

function printStatus(status) {
    for (const [category, entries] of Object.entries(status)) {
        console.log(`${category}:`, entries);
    }
}

// ---------------------------------------------------------------------------
// 5. Beginner workflow
// ---------------------------------------------------------------------------

function demonstrateBasicWorkflow() {
    console.log("\n" + "=".repeat(72));
    console.log("1. BASIC GIT WORKFLOW");
    console.log("=".repeat(72));

    const repo = new GitRepository();
    repo.init("main");

    repo.writeFile("README.md", "# Git Fundamentals\n");
    repo.writeFile("app.js", 'console.log("Hello, Git");\n');

    console.log("Before staging:");
    printStatus(repo.status());

    repo.stage("README.md", "app.js");

    console.log("\nAfter staging:");
    printStatus(repo.status());

    const first = repo.commit("Create initial project");

    repo.writeFile("app.js", 'console.log("Hello, Git version 2");\n');

    console.log("\nAfter editing app.js:");
    printStatus(repo.status());

    repo.stage("app.js");
    const second = repo.commit("Update application message");

    console.log("\nHistory:");

    for (const entry of repo.log()) {
        console.log(`${shortHash(entry.id)} ${entry.message}`);
    }

    console.log(`\nFirst commit:  ${shortHash(first)}`);
    console.log(`Second commit: ${shortHash(second)}`);

    return repo;
}

// ---------------------------------------------------------------------------
// 6. JavaScript-specific data-processing demonstration
// ---------------------------------------------------------------------------

function demonstrateMapsAndImmutability() {
    console.log("\n" + "=".repeat(72));
    console.log("2. JAVASCRIPT DATA STRUCTURES IN A REPOSITORY MODEL");
    console.log("=".repeat(72));

    const files = new Map([
        ["src/main.js", Buffer.from("export const value = 42;\n")],
        ["src/util.js", Buffer.from("export function add(a, b) { return a + b; }\n")]
    ]);

    // Map gives direct lookup by path and makes the snapshot model explicit.
    console.log("Tracked paths:", [...files.keys()]);

    const snapshot = cloneFileMap(files);
    files.set("src/main.js", Buffer.from("export const value = 100;\n"));

    console.log(
        "Original snapshot remains unchanged:",
        snapshot.get("src/main.js").toString().trim()
    );

    console.log(
        "Working data changed:",
        files.get("src/main.js").toString().trim()
    );
}

// ---------------------------------------------------------------------------
// 7. Branches and detached HEAD
// ---------------------------------------------------------------------------

function demonstrateBranches() {
    console.log("\n" + "=".repeat(72));
    console.log("3. BRANCHES AND DETACHED HEAD");
    console.log("=".repeat(72));

    const repo = new GitRepository();
    repo.init();

    repo.writeFile("notes.txt", "base\n");
    repo.stageAll();
    const base = repo.commit("Create notes");

    repo.createBranch("feature");

    repo.writeFile("notes.txt", "main version\n");
    repo.stage("notes.txt");
    const mainCommit = repo.commit("Update main");

    repo.checkout("feature");

    repo.writeFile("notes.txt", "feature version\n");
    repo.stage("notes.txt");
    const featureCommit = repo.commit("Update feature");

    console.log("Branches:");

    for (const [branch, commitId] of repo.branches) {
        console.log(
            `${branch}: ${commitId ? shortHash(commitId) : "(unborn)"}`
        );
    }

    console.log("\nCommit graph:");
    console.log(`          ${shortHash(mainCommit)} main`);
    console.log(`         /`);
    console.log(`base ${shortHash(base)}`);
    console.log(`         \\`);
    console.log(`          ${shortHash(featureCommit)} feature`);

    repo.checkout(featureCommit);

    console.log(
        "\nDetached HEAD:",
        shortHash(repo.head()),
        "branch:",
        repo.headBranch
    );
}

// ---------------------------------------------------------------------------
// 8. Three-way merge analysis
// ---------------------------------------------------------------------------

function threeWayMerge(base, ours, theirs) {
    const merged = new Map();
    const conflicts = [];

    const paths = new Set([
        ...base.keys(),
        ...ours.keys(),
        ...theirs.keys()
    ]);

    for (const path of [...paths].sort()) {
        const baseValue = base.get(path);
        const oursValue = ours.get(path);
        const theirsValue = theirs.get(path);

        if (buffersEqual(oursValue, theirsValue)) {
            if (oursValue !== undefined) {
                merged.set(path, Buffer.from(oursValue));
            }
        } else if (buffersEqual(oursValue, baseValue)) {
            if (theirsValue !== undefined) {
                merged.set(path, Buffer.from(theirsValue));
            }
        } else if (buffersEqual(theirsValue, baseValue)) {
            if (oursValue !== undefined) {
                merged.set(path, Buffer.from(oursValue));
            }
        } else {
            conflicts.push(path);
        }
    }

    return { merged, conflicts };
}

function demonstrateMerge() {
    console.log("\n" + "=".repeat(72));
    console.log("4. THREE-WAY MERGE");
    console.log("=".repeat(72));

    const repo = new GitRepository();
    repo.init();

    repo.writeFile("document.txt", "line 1\nline 2\n");
    repo.stageAll();
    const baseCommit = repo.commit("Create document");

    repo.createBranch("feature");

    repo.writeFile("document.txt", "line 1\nmain change\n");
    repo.stage("document.txt");
    const mainCommit = repo.commit("Change document on main");

    repo.checkout("feature");

    repo.writeFile("document.txt", "line 1\nfeature change\n");
    repo.stage("document.txt");
    const featureCommit = repo.commit("Change document on feature");

    const base = repo.snapshotFromCommit(baseCommit);
    const ours = repo.snapshotFromCommit(mainCommit);
    const theirs = repo.snapshotFromCommit(featureCommit);

    const result = threeWayMerge(base, ours, theirs);

    console.log("Merge base:", shortHash(repo.mergeBase(mainCommit, featureCommit)));
    console.log("Conflicts:", result.conflicts);

    if (result.conflicts.length > 0) {
        console.log(
            "The same file was changed differently relative to the common base."
        );
    }
}

// ---------------------------------------------------------------------------
// 9. Validation and failure conditions
// ---------------------------------------------------------------------------

function demonstrateErrors() {
    console.log("\n" + "=".repeat(72));
    console.log("5. VALIDATION AND FAILURE CONDITIONS");
    console.log("=".repeat(72));

    try {
        normalizePath("../secret.txt");
    } catch (error) {
        console.log("Path validation:", error.message);
    }

    try {
        validateBranchName("feature..broken");
    } catch (error) {
        console.log("Branch validation:", error.message);
    }

    const repo = new GitRepository();
    repo.init();

    try {
        repo.commit("Empty commit");
    } catch (error) {
        console.log("Commit validation:", error.message);
    }

    try {
        repo.checkout("0".repeat(40));
    } catch (error) {
        console.log("Checkout validation:", error.message);
    }
}

// ---------------------------------------------------------------------------
// 10. Integrity
// ---------------------------------------------------------------------------

function demonstrateIntegrity() {
    console.log("\n" + "=".repeat(72));
    console.log("6. CONTENT-ADDRESSABLE INTEGRITY");
    console.log("=".repeat(72));

    const repo = new GitRepository();
    repo.init();

    repo.writeFile("data.txt", "important data\n");
    repo.stageAll();

    const commitId = repo.commit("Store data");

    console.log("Commit:", shortHash(commitId));
    console.log("Integrity:", repo.verifyIntegrity());

    const commit = repo.getCommit(commitId);

    // This simulates tampering with an object without changing its stored key.
    const tampered = new Commit({
        treeId: commit.treeId,
        parents: commit.parents,
        author: commit.author,
        message: "Tampered commit"
    });

    repo.objects.set(commitId, tampered);

    console.log("After simulated tampering:");
    console.log(repo.verifyIntegrity());
}

// ---------------------------------------------------------------------------
// 11. Tests
// ---------------------------------------------------------------------------

function runTests() {
    console.log("\n" + "=".repeat(72));
    console.log("7. SELF-TESTS");
    console.log("=".repeat(72));

    const repo = new GitRepository();
    repo.init();

    repo.writeFile("test.txt", "hello\n");
    repo.stage("test.txt");

    const first = repo.commit("Initial test");

    assert.strictEqual(repo.head(), first);
    assert.strictEqual(
        repo.snapshotFromCommit(first).get("test.txt").toString(),
        "hello\n"
    );

    repo.writeFile("test.txt", "changed\n");

    assert.deepStrictEqual(repo.status().modified, ["test.txt"]);

    repo.stage("test.txt");

    const second = repo.commit("Change test");

    assert.deepStrictEqual(repo.getCommit(second).parents, [first]);
    assert.deepStrictEqual(repo.verifyIntegrity(), []);

    repo.createBranch("feature");
    assert.strictEqual(repo.branches.get("feature"), second);

    repo.checkout("feature");
    assert.strictEqual(repo.headBranch, "feature");

    repo.checkout(second);
    assert.strictEqual(repo.headBranch, null);
    assert.strictEqual(repo.detachedHead, second);

    console.log("All assertions passed.");
}

// ---------------------------------------------------------------------------
// 12. Real Git command reference
// ---------------------------------------------------------------------------

function printGitCommands() {
    console.log("\n" + "=".repeat(72));
    console.log("8. REAL GIT COMMAND REFERENCE");
    console.log("=".repeat(72));

    const commands = [
        ["git init", "Create a repository."],
        ["git status", "Inspect working-tree and staging state."],
        ["git add file", "Stage a file."],
        ["git add .", "Stage changes under the current directory."],
        ['git commit -m "message"', "Create a commit."],
        ["git log", "Inspect commit history."],
        ["git diff", "Inspect unstaged changes."],
        ["git diff --staged", "Inspect staged changes."],
        ["git branch", "List branches."],
        ["git switch -c feature", "Create and switch to a branch."],
        ["git switch main", "Switch branches."],
        ["git merge feature", "Merge a branch."],
        ["git show <commit>", "Inspect a commit."],
        ["git restore file", "Restore file content."],
        ["git clone <url>", "Create a local copy of a repository."],
        ["git fetch", "Download remote objects and references."],
        ["git pull", "Fetch and integrate remote changes."],
        ["git push", "Send local commits and references to a remote."]
    ];

    for (const [command, purpose] of commands) {
        console.log(`${command.padEnd(30)} ${purpose}`);
    }
}

// ---------------------------------------------------------------------------
// 13. Main
// ---------------------------------------------------------------------------

function main() {
    demonstrateBasicWorkflow();
    demonstrateMapsAndImmutability();
    demonstrateBranches();
    demonstrateMerge();
    demonstrateErrors();
    demonstrateIntegrity();
    runTests();
    printGitCommands();

    console.log("\nGit fundamentals demonstration complete.");
}

main();
