"use strict";

/*
 * Git Branching: branches, merge, rebase, conflicts, and advanced workflows.
 *
 * This file uses only Node.js built-in modules and creates a temporary
 * repository so the examples execute against real Git history.
 *
 * Requirements:
 *   Node.js 18+
 *   Git installed and available on PATH
 */

const fs = require("fs");
const os = require("os");
const path = require("path");
const { execFileSync, spawnSync } = require("child_process");


// ============================================================================
// Utility functions
// ============================================================================

function title(text) {
    console.log("\n" + "=".repeat(78));
    console.log(text);
    console.log("=".repeat(78));
}

function subtitle(text) {
    console.log(`\n--- ${text} ---`);
}

function explain(text) {
    console.log(text);
}

function run(command, args = [], cwd = null, options = {}) {
    const result = spawnSync(command, args, {
        cwd,
        encoding: "utf8",
        stdio: ["pipe", "pipe", "pipe"],
        env: { ...process.env, ...(options.env || {}) }
    });

    if (result.stdout) {
        process.stdout.write(result.stdout);
    }

    if (result.stderr) {
        process.stderr.write(result.stderr);
    }

    if (options.check !== false && result.status !== 0) {
        throw new Error(
            `Command failed: ${command} ${args.join(" ")}`
        );
    }

    return result;
}

function git(repository, ...args) {
    return run("git", args, repository);
}

function gitAllowFailure(repository, ...args) {
    return run("git", args, repository, { check: false });
}

function writeFile(repository, relativePath, content) {
    const target = path.join(repository, relativePath);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, content, "utf8");
}

function readFile(repository, relativePath) {
    return fs.readFileSync(
        path.join(repository, relativePath),
        "utf8"
    );
}

function commit(repository, message) {
    git(repository, "add", ".");
    git(repository, "commit", "-m", message);
}


// ============================================================================
// Repository setup
// ============================================================================

function createRepository() {
    const repository = fs.mkdtempSync(
        path.join(os.tmpdir(), "git-branching-study-")
    );

    git(repository, "init", "-b", "main");
    git(repository, "config", "user.name", "Git Branching Study");
    git(repository, "config", "user.email", "git-study@example.invalid");

    writeFile(
        repository,
        "README.txt",
        "Git Branching Study Repository\n"
    );

    writeFile(
        repository,
        "app.txt",
        "version=1\nstatus=stable\n"
    );

    commit(repository, "Create initial application");

    return repository;
}


// ============================================================================
// Commit graph
// ============================================================================

function demonstrateCommitGraph() {
    title("1. Commit Graph and Branch Fundamentals");

    explain(
        "A Git branch is a movable reference to a commit. It does not "
        + "represent a second physical copy of the repository."
    );

    explain(
        "A commit normally identifies a parent commit. A merge commit can "
        + "have two or more parents. Branch names point at commits in this "
        + "commit graph."
    );

    console.log(`
Conceptual graph:

A -- B -- C
          ^
          main

After creating feature at C:

A -- B -- C
          ^\\
          | feature
          main
`.trim());
}


// ============================================================================
// Basic branch operations
// ============================================================================

function demonstrateBasicBranches(repository) {
    title("2. Creating, Switching, Renaming, and Deleting Branches");

    explain(
        "git branch inspects or creates branch references. git switch moves "
        + "HEAD between branches. git branch -d safely deletes a merged branch."
    );

    subtitle("Initial branches");
    git(repository, "branch");

    git(repository, "switch", "-c", "feature/login");

    writeFile(
        repository,
        "login.txt",
        "login validation enabled\n"
    );

    commit(repository, "Add login validation");

    subtitle("Feature history");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "switch", "main");

    git(repository, "switch", "-c", "temporary");
    git(repository, "switch", "main");
    git(repository, "branch", "-m", "temporary", "renamed-temporary");
    git(repository, "branch", "-d", "renamed-temporary");

    subtitle("Final local branch list");
    git(repository, "branch", "-vv");
}


// ============================================================================
// Fast-forward merge
// ============================================================================

function demonstrateFastForwardMerge(repository) {
    title("3. Fast-Forward Merge");

    explain(
        "If the target branch has not diverged, Git can move its branch "
        + "pointer forward. This is called a fast-forward merge."
    );

    git(repository, "switch", "main");
    git(repository, "switch", "-c", "feature/search");

    writeFile(
        repository,
        "search.txt",
        "algorithm=linear\n"
    );

    commit(repository, "Add search feature");

    git(repository, "switch", "main");
    git(repository, "merge", "feature/search");

    subtitle("History after fast-forward");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "branch", "-d", "feature/search");
}


// ============================================================================
// Three-way merge
// ============================================================================

function demonstrateThreeWayMerge(repository) {
    title("4. Three-Way Merge and Merge Commits");

    explain(
        "When both branches contain new commits after their common ancestor, "
        + "Git performs a three-way merge."
    );

    git(repository, "switch", "main");

    writeFile(
        repository,
        "app.txt",
        "version=2\nstatus=stable\nmain-change=yes\n"
    );

    commit(repository, "Update application on main");

    git(repository, "switch", "-c", "feature/reporting");

    writeFile(
        repository,
        "report.txt",
        "reporting enabled\n"
    );

    commit(repository, "Add reporting");

    git(repository, "switch", "main");

    writeFile(
        repository,
        "operations.txt",
        "monitoring enabled\n"
    );

    commit(repository, "Add monitoring");

    subtitle("Diverged graph");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(
        repository,
        "merge",
        "--no-ff",
        "feature/reporting",
        "-m",
        "Merge reporting feature"
    );

    subtitle("Graph after merge");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "branch", "-d", "feature/reporting");
}


// ============================================================================
// Merge conflict
// ============================================================================

function demonstrateMergeConflict(repository) {
    title("5. Merge Conflicts");

    explain(
        "Git reports a conflict when it cannot safely combine changes. "
        + "Overlapping edits to the same lines are a common example."
    );

    git(repository, "switch", "main");

    writeFile(
        repository,
        "config.txt",
        "timeout=30\nmode=production\n"
    );

    commit(repository, "Add shared configuration");

    git(repository, "switch", "-c", "feature/config");

    writeFile(
        repository,
        "config.txt",
        "timeout=60\nmode=production\n"
    );

    commit(repository, "Increase feature timeout");

    git(repository, "switch", "main");

    writeFile(
        repository,
        "config.txt",
        "timeout=15\nmode=production\n"
    );

    commit(repository, "Reduce production timeout");

    const mergeResult = gitAllowFailure(
        repository,
        "merge",
        "feature/config"
    );

    if (mergeResult.status === 0) {
        throw new Error("Expected a merge conflict.");
    }

    subtitle("Conflict markers");
    console.log(readFile(repository, "config.txt"));

    explain(
        "A typical conflict contains <<<<<<<, =======, and >>>>>>> markers. "
        + "The current branch appears above the separator and the incoming "
        + "branch appears below it."
    );

    writeFile(
        repository,
        "config.txt",
        "timeout=30\nmode=production\n"
    );

    git(repository, "add", "config.txt");
    git(repository, "commit", "-m", "Resolve configuration conflict");

    subtitle("Resolved history");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "branch", "-d", "feature/config");
}


// ============================================================================
// Rebase
// ============================================================================

function demonstrateRebase(repository) {
    title("6. Rebase");

    explain(
        "Rebase replays commits from the current branch on top of another "
        + "base. Because parent relationships change, the replayed commits "
        + "normally receive new commit identities."
    );

    git(repository, "switch", "main");

    writeFile(
        repository,
        "release.txt",
        "release=1\n"
    );

    commit(repository, "Prepare release");

    git(repository, "switch", "-c", "feature/rebase-demo");

    writeFile(
        repository,
        "feature.txt",
        "step=one\n"
    );

    commit(repository, "Feature step one");

    writeFile(
        repository,
        "feature.txt",
        "step=two\n"
    );

    commit(repository, "Feature step two");

    git(repository, "switch", "main");

    writeFile(
        repository,
        "main-progress.txt",
        "main-progress=yes\n"
    );

    commit(repository, "Advance main");

    subtitle("Before rebase");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "switch", "feature/rebase-demo");
    git(repository, "rebase", "main");

    subtitle("After rebase");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "switch", "main");
    git(repository, "merge", "--ff-only", "feature/rebase-demo");
    git(repository, "branch", "-d", "feature/rebase-demo");
}


// ============================================================================
// Rebase conflict
// ============================================================================

function demonstrateRebaseConflict(repository) {
    title("7. Rebase Conflict and Recovery");

    explain(
        "During a rebase conflict, Git pauses while replaying one particular "
        + "commit. Resolve the files, stage them, and continue."
    );

    git(repository, "switch", "main");

    writeFile(
        repository,
        "policy.txt",
        "level=normal\n"
    );

    commit(repository, "Add policy");

    git(repository, "switch", "-c", "feature/rebase-conflict");

    writeFile(
        repository,
        "policy.txt",
        "level=high\n"
    );

    commit(repository, "Raise feature policy");

    git(repository, "switch", "main");

    writeFile(
        repository,
        "policy.txt",
        "level=low\n"
    );

    commit(repository, "Lower main policy");

    git(repository, "switch", "feature/rebase-conflict");

    const result = gitAllowFailure(
        repository,
        "rebase",
        "main"
    );

    if (result.status === 0) {
        throw new Error("Expected a rebase conflict.");
    }

    subtitle("Rebase conflict state");
    git(repository, "status", "--short", "--branch");
    console.log(readFile(repository, "policy.txt"));

    // Choose an explicit resolution for the demonstration.
    writeFile(
        repository,
        "policy.txt",
        "level=high\n"
    );

    git(repository, "add", "policy.txt");

    // GIT_EDITOR=true prevents Git from opening an interactive editor
    // while replaying the existing commit message.
    const continueResult = spawnSync(
        "git",
        ["-c", "core.editor=true", "rebase", "--continue"],
        {
            cwd: repository,
            encoding: "utf8",
            stdio: ["pipe", "pipe", "pipe"],
            env: process.env
        }
    );

    if (continueResult.stdout) {
        process.stdout.write(continueResult.stdout);
    }

    if (continueResult.stderr) {
        process.stderr.write(continueResult.stderr);
    }

    const stillRebasing =
        fs.existsSync(path.join(repository, ".git", "rebase-merge")) ||
        fs.existsSync(path.join(repository, ".git", "rebase-apply"));

    if (continueResult.status !== 0 || stillRebasing) {
        gitAllowFailure(repository, "rebase", "--abort");
        console.log(
            "The demonstration was safely aborted after showing the "
            + "rebase conflict."
        );
    } else {
        subtitle("Rebase completed");
        git(repository, "log", "--oneline", "--decorate", "--graph", "--all");
    }

    git(repository, "switch", "main");
    gitAllowFailure(repository, "branch", "-D", "feature/rebase-conflict");
}


// ============================================================================
// Detached HEAD
// ============================================================================

function demonstrateDetachedHead(repository) {
    title("8. Detached HEAD");

    explain(
        "HEAD normally identifies the current branch. In detached HEAD state, "
        + "HEAD identifies a commit directly."
    );

    const currentCommit = execFileSync(
        "git",
        ["rev-parse", "HEAD"],
        {
            cwd: repository,
            encoding: "utf8"
        }
    ).trim();

    git(repository, "switch", "--detach", currentCommit);

    subtitle("Detached state");
    git(repository, "status", "--short", "--branch");

    git(repository, "switch", "main");

    explain(
        "A commit made in detached HEAD is not automatically protected by a "
        + "branch name. Create a branch if the detached work should remain "
        + "easy to locate."
    );
}


// ============================================================================
// Diagnostics
// ============================================================================

function demonstrateDiagnostics(repository) {
    title("9. Branch Comparison and Diagnostics");

    subtitle("Current branch");
    git(repository, "branch", "--show-current");

    subtitle("All branches");
    git(repository, "branch", "--all", "--verbose");

    subtitle("Current commit");
    git(repository, "rev-parse", "HEAD");

    subtitle("Latest commit details");
    git(repository, "show", "--stat", "--oneline", "HEAD");

    subtitle("Last commit diff");
    git(repository, "diff", "HEAD~1", "HEAD", "--stat");

    subtitle("Common ancestor of HEAD and main");
    git(repository, "merge-base", "HEAD", "main");

    explain(
        "git status answers what is happening now. git log explains history. "
        + "git diff explains content differences. git merge-base helps explain "
        + "where two lines of development diverged."
    );
}


// ============================================================================
// Reflog
// ============================================================================

function demonstrateReflog(repository) {
    title("10. Reflog and Local Recovery");

    explain(
        "The reflog records local movements of references such as HEAD. It "
        + "can help locate commits after branch resets, rebases, or accidental "
        + "reference movement."
    );

    git(repository, "reflog", "-8");
}


// ============================================================================
// Restore, reset, revert
// ============================================================================

function demonstrateRecovery(repository) {
    title("11. Restore, Reset, and Revert");

    explain(
        "git restore is primarily for restoring file contents. git reset "
        + "moves references and can also change the index and working tree. "
        + "git revert creates a new commit that reverses an earlier commit."
    );

    git(repository, "switch", "main");
    git(repository, "switch", "-c", "recovery-demo");

    writeFile(
        repository,
        "recovery.txt",
        "original\n"
    );

    commit(repository, "Create recovery example");

    writeFile(
        repository,
        "recovery.txt",
        "uncommitted-edit\n"
    );

    subtitle("Before restore");
    console.log(readFile(repository, "recovery.txt"));

    git(repository, "restore", "recovery.txt");

    subtitle("After restore");
    console.log(readFile(repository, "recovery.txt"));

    writeFile(
        repository,
        "recovery.txt",
        "committed-change\n"
    );

    commit(repository, "Create change to revert");

    git(repository, "revert", "--no-edit", "HEAD");

    subtitle("History after revert");
    git(repository, "log", "--oneline", "--decorate", "-6");

    git(repository, "switch", "main");
    gitAllowFailure(repository, "branch", "-D", "recovery-demo");
}


// ============================================================================
// Cherry-pick
// ============================================================================

function demonstrateCherryPick(repository) {
    title("12. Cherry-Pick");

    explain(
        "Cherry-pick applies the changes from a selected commit to the "
        + "current branch. It is useful for selectively moving a fix."
    );

    git(repository, "switch", "main");
    git(repository, "switch", "-c", "feature/security-fix");

    writeFile(
        repository,
        "security.txt",
        "input-validation=enabled\n"
    );

    commit(repository, "Add input validation");

    const fixCommit = execFileSync(
        "git",
        ["rev-parse", "HEAD"],
        {
            cwd: repository,
            encoding: "utf8"
        }
    ).trim();

    git(repository, "switch", "main");
    git(repository, "cherry-pick", fixCommit);

    subtitle("Main after cherry-pick");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    gitAllowFailure(repository, "branch", "-D", "feature/security-fix");
}


// ============================================================================
// Interactive rebase concepts
// ============================================================================

function explainInteractiveRebase() {
    title("13. Interactive Rebase");

    const actions = {
        pick: "keep a commit",
        reword: "keep changes but change the commit message",
        edit: "pause after applying a commit",
        squash: "combine with the previous commit and edit messages",
        fixup: "combine with the previous commit while discarding its message",
        drop: "remove a commit from the rewritten sequence",
        exec: "execute a shell command during the sequence"
    };

    for (const [action, meaning] of Object.entries(actions)) {
        console.log(`${action.padEnd(8)} -> ${meaning}`);
    }

    explain(
        "Interactive rebase is useful for organizing unpublished local "
        + "commits. It should be used carefully on history already consumed "
        + "by other developers."
    );
}


// ============================================================================
// Remote branches
// ============================================================================

function explainRemoteBranches() {
    title("14. Remote Branches");

    console.log(`
git remote -v
git fetch origin
git branch -r
git switch -c feature origin/feature
git push -u origin feature
git branch -vv
`.trim());

    explain(
        "A remote-tracking branch such as origin/main records the last known "
        + "state of main obtained from the remote. git fetch updates that "
        + "information without automatically integrating it into your current "
        + "branch."
    );

    explain(
        "git pull combines fetching with an integration step. Depending on "
        + "configuration or command options, that integration can use merge "
        + "or rebase."
    );
}


// ============================================================================
// Branch strategy
// ============================================================================

function explainBranchStrategies() {
    title("15. Branching Strategies");

    const strategies = [
        [
            "Short-lived feature branches",
            "Isolate focused work and integrate frequently."
        ],
        [
            "Release branches",
            "Stabilize a planned release independently from ongoing development."
        ],
        [
            "Hotfix branches",
            "Isolate urgent production fixes."
        ],
        [
            "Trunk-based development",
            "Keep integration branches short-lived and integrate frequently."
        ],
        [
            "Long-lived development branches",
            "Maintain independent development lines while accepting greater drift."
        ]
    ];

    for (const [name, description] of strategies) {
        console.log(`${name}: ${description}`);
    }
}


// ============================================================================
// Merge versus rebase
// ============================================================================

function compareMergeAndRebase() {
    title("16. Merge versus Rebase");

    console.log(
        "Merge: combines histories and preserves the original commit identities."
    );

    console.log(
        "Rebase: replays commits on another base and normally creates new identities."
    );

    explain(
        "Commit identity depends on the commit metadata, tree, and parent "
        + "relationships. Rebase changes parent relationships, which is why "
        + "the resulting commits generally have different hashes."
    );
}


// ============================================================================
// Conflict resolution
// ============================================================================

function explainConflictResolution() {
    title("17. Conflict Resolution Principles");

    const principles = [
        "Run git status first.",
        "Identify the current branch and the incoming branch.",
        "Inspect the complete affected section, not only the marker lines.",
        "Preserve intended behavior rather than blindly choosing one side.",
        "Remove every conflict marker.",
        "Run tests after resolving.",
        "Use git diff --check for whitespace problems.",
        "Stage resolved files.",
        "Continue the active merge or rebase.",
        "Abort the operation when the safest decision is to return to the pre-operation state."
    ];

    for (const principle of principles) {
        console.log(`* ${principle}`);
    }
}


// ============================================================================
// Edge cases
// ============================================================================

function explainEdgeCases() {
    title("18. Important Edge Cases");

    const cases = [
        "Uncommitted changes can prevent switching branches if files would be overwritten.",
        "Untracked files can also block branch switching when paths collide.",
        "Binary files generally require manual conflict decisions.",
        "Rename and rename/delete conflicts can require semantic interpretation.",
        "A file-versus-directory conflict can prevent automatic integration.",
        "A merge can produce no new commit if histories are already integrated.",
        "A rebased remote branch may require collaborators to reconcile rewritten history.",
        "Detached HEAD commits can become difficult to locate without a reference."
    ];

    for (const item of cases) {
        console.log(`* ${item}`);
    }
}


// ============================================================================
// Performance
// ============================================================================

function explainPerformance() {
    title("19. Performance Considerations");

    explain(
        "Creating a branch is normally inexpensive because it primarily "
        + "creates or moves a reference. Large repository operations can "
        + "still involve object traversal, merge analysis, checkout work, "
        + "rebase replay, file operations, and conflict processing."
    );

    explain(
        "Short-lived branches reduce the amount of divergence that must be "
        + "integrated at one time. Repository maintenance, packfiles, commit "
        + "graphs, and efficient object storage are also important for large "
        + "repositories."
    );
}


// ============================================================================
// Security
// ============================================================================

function explainSecurity() {
    title("20. Security and Integrity");

    explain(
        "Git object identifiers are cryptographic hashes that help detect "
        + "unexpected object changes. Signed commits and tags can provide "
        + "additional provenance information."
    );

    explain(
        "Repository integrity is only one part of software security. Access "
        + "control, protected branches, CI permissions, review rules, "
        + "dependency management, secret handling, and release controls also "
        + "matter."
    );

    explain(
        "Never treat branch deletion as secure secret removal. Sensitive "
        + "credentials committed to history may remain recoverable even after "
        + "the file is deleted."
    );
}


// ============================================================================
// Best practices
// ============================================================================

function explainBestPractices() {
    title("21. Production Branching Practices");

    const practices = [
        "Keep commits focused.",
        "Use meaningful branch names.",
        "Integrate frequently.",
        "Review diffs before merging.",
        "Run automated tests before integration.",
        "Avoid rewriting history shared by other developers.",
        "Resolve conflicts based on intended behavior.",
        "Protect important shared branches.",
        "Use reproducible CI validation.",
        "Delete obsolete branches.",
        "Keep a recovery path through reflog and backups.",
        "Document unusual branching procedures."
    ];

    for (const practice of practices) {
        console.log(`* ${practice}`);
    }
}


// ============================================================================
// Common mistakes
// ============================================================================

function explainCommonMistakes() {
    title("22. Common Mistakes");

    const mistakes = [
        [
            "Thinking a branch is a folder",
            "A branch is a reference into the commit graph."
        ],
        [
            "Merging from the wrong current branch",
            "Check git branch --show-current first."
        ],
        [
            "Rebasing shared history casually",
            "Rewritten commits can disrupt collaborators."
        ],
        [
            "Ignoring git status during a conflict",
            "Status identifies unresolved paths and active operations."
        ],
        [
            "Choosing one side without understanding behavior",
            "The result can compile while still being logically wrong."
        ],
        [
            "Using force push casually",
            "Use deliberate history-rewrite procedures and understand their impact."
        ]
    ];

    for (const [mistake, correction] of mistakes) {
        console.log(`${mistake}: ${correction}`);
    }
}


// ============================================================================
// Advanced concepts
// ============================================================================

function explainAdvancedConcepts() {
    title("23. Advanced Concepts");

    const concepts = [
        [
            "Reachability",
            "A commit is reachable when a reference can traverse parent links to it."
        ],
        [
            "Merge base",
            "A common ancestor used as a basis for three-way integration."
        ],
        [
            "First-parent history",
            "A view emphasizing the mainline ancestry through merge commits."
        ],
        [
            "Patch replay",
            "A conceptual model for how rebase reapplies commit changes."
        ],
        [
            "Bisect",
            "A binary-search workflow for locating a regression in history."
        ],
        [
            "Worktree",
            "Multiple working directories sharing one Git repository object database."
        ],
        [
            "Tag",
            "A reference normally used to identify a stable point in history."
        ]
    ];

    for (const [name, definition] of concepts) {
        console.log(`${name}: ${definition}`);
    }
}


// ============================================================================
// Worktree
// ============================================================================

function demonstrateWorktree(repository) {
    title("24. Multiple Working Trees");

    explain(
        "git worktree allows multiple branches to be checked out in separate "
        + "directories while sharing the repository's object database."
    );

    const secondaryPath = path.join(
        path.dirname(repository),
        "git-branching-secondary-worktree"
    );

    git(repository, "switch", "main");
    git(repository, "switch", "-c", "feature/worktree");

    writeFile(
        repository,
        "worktree-feature.txt",
        "worktree demonstration\n"
    );

    commit(repository, "Add worktree feature");

    git(repository, "switch", "main");

    try {
        git(
            repository,
            "worktree",
            "add",
            secondaryPath,
            "feature/worktree"
        );

        subtitle("Registered worktrees");
        git(repository, "worktree", "list");
    } finally {
        gitAllowFailure(
            repository,
            "worktree",
            "remove",
            "--force",
            secondaryPath
        );

        gitAllowFailure(
            repository,
            "branch",
            "-D",
            "feature/worktree"
        );
    }
}


// ============================================================================
// Tags
// ============================================================================

function demonstrateTags(repository) {
    title("25. Tags and Branches");

    explain(
        "Branches are normally movable references. A release tag normally "
        + "identifies a particular point and is intended to remain stable."
    );

    git(repository, "switch", "main");
    git(repository, "tag", "v1.0.0");

    subtitle("Tags");
    git(repository, "tag", "--list");
}


// ============================================================================
// Integration verification
// ============================================================================

function demonstrateVerification(repository) {
    title("26. Integration Verification");

    explain(
        "Git can verify history and content relationships, but a successful "
        + "merge does not prove that the resulting application is correct."
    );

    const application = readFile(repository, "app.txt");

    if (!application.includes("version=")) {
        throw new Error("Application verification failed.");
    }

    git(repository, "diff", "--check");

    console.log("Application content check: passed.");
    console.log("Git whitespace check: passed.");
}


// ============================================================================
// CI
// ============================================================================

function explainCI() {
    title("27. Branches and Continuous Integration");

    explain(
        "A branch isolates a change set while CI can automatically test that "
        + "change against the repository's integration rules."
    );

    explain(
        "A production pipeline can include formatting checks, linting, unit "
        + "tests, integration tests, builds, security checks, and deployment "
        + "verification. Git provides the history model; CI provides automated "
        + "verification."
    );
}


// ============================================================================
// Complete workflow
// ============================================================================

function demonstrateCompleteWorkflow(repository) {
    title("28. Complete Feature Workflow");

    git(repository, "switch", "main");
    git(repository, "switch", "-c", "feature/audit");

    writeFile(
        repository,
        "audit.txt",
        "audit-log=enabled\n"
    );

    commit(repository, "Enable audit logging");

    writeFile(
        repository,
        "audit.txt",
        "audit-log=enabled\nretention-days=90\n"
    );

    commit(repository, "Configure audit retention");

    subtitle("Feature branch");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "switch", "main");

    git(
        repository,
        "merge",
        "--no-ff",
        "feature/audit",
        "-m",
        "Merge audit feature"
    );

    subtitle("Integrated branch history");
    git(repository, "log", "--oneline", "--decorate", "--graph", "--all");

    git(repository, "branch", "-d", "feature/audit");
}


// ============================================================================
// Command reference
// ============================================================================

function commandReference() {
    title("29. Practical Command Reference");

    const commands = [
        ["git branch", "List local branches."],
        ["git branch <name>", "Create a branch."],
        ["git switch <name>", "Switch branches."],
        ["git switch -c <name>", "Create and switch branches."],
        ["git branch -m <old> <new>", "Rename a branch."],
        ["git branch -d <name>", "Delete a merged branch."],
        ["git branch -D <name>", "Force-delete a branch."],
        ["git merge <branch>", "Merge a branch into the current branch."],
        ["git merge --no-ff <branch>", "Force a merge commit."],
        ["git merge --abort", "Abort an active merge."],
        ["git rebase <base>", "Replay commits onto a new base."],
        ["git rebase --continue", "Continue a paused rebase."],
        ["git rebase --abort", "Abort an active rebase."],
        ["git status", "Inspect repository state."],
        ["git log --graph --oneline --all", "Visualize commit history."],
        ["git diff", "Inspect content differences."],
        ["git fetch", "Update remote-tracking references."],
        ["git push", "Send references and commits to a remote."],
        ["git pull", "Fetch and integrate changes."],
        ["git cherry-pick <commit>", "Apply a selected commit."],
        ["git reflog", "Inspect local reference movements."],
        ["git merge-base A B", "Find a common ancestor."],
        ["git worktree add", "Create another working directory."],
        ["git revert <commit>", "Create a reversing commit."],
        ["git restore <path>", "Restore file content."],
        ["git reset", "Move/reset references and optionally index/worktree."],
        ["git tag <name>", "Create a tag."],
        ["git bisect", "Binary-search history for a regression."]
    ];

    const width = Math.max(...commands.map(([command]) => command.length));

    for (const [command, description] of commands) {
        console.log(command.padEnd(width) + "  " + description);
    }
}


// ============================================================================
// Main
// ============================================================================

function main() {
    title("Git Branching: Complete Practical Study");

    try {
        execFileSync("git", ["--version"], {
            encoding: "utf8",
            stdio: ["ignore", "pipe", "pipe"]
        });
    } catch {
        throw new Error(
            "Git was not found on PATH. Install Git before running this program."
        );
    }

    console.log(execFileSync("git", ["--version"], { encoding: "utf8" }).trim());

    const repository = createRepository();
    console.log(`Temporary repository: ${repository}`);

    try {
        demonstrateCommitGraph();
        demonstrateBasicBranches(repository);
        demonstrateFastForwardMerge(repository);
        demonstrateThreeWayMerge(repository);
        demonstrateMergeConflict(repository);
        demonstrateRebase(repository);
        demonstrateRebaseConflict(repository);
        demonstrateDetachedHead(repository);
        demonstrateDiagnostics(repository);
        demonstrateReflog(repository);
        demonstrateRecovery(repository);
        demonstrateCherryPick(repository);
        explainInteractiveRebase();
        explainRemoteBranches();
        explainBranchStrategies();
        compareMergeAndRebase();
        explainConflictResolution();
        explainEdgeCases();
        explainPerformance();
        explainSecurity();
        explainBestPractices();
        explainCommonMistakes();
        explainAdvancedConcepts();
        demonstrateWorktree(repository);
        demonstrateTags(repository);
        demonstrateVerification(repository);
        explainCI();
        demonstrateCompleteWorkflow(repository);
        commandReference();

        title("Final Repository State");
        git(repository, "status", "--short", "--branch");
        git(repository, "branch", "-vv");
        git(repository, "log", "--oneline", "--decorate", "--graph", "--all", "-12");

        console.log("\nAll demonstrations completed.");
    } finally {
        fs.rmSync(repository, {
            recursive: true,
            force: true
        });
    }
}

main();
