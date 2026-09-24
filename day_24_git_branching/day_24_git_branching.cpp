/*
 * Git Branching: Industry-Style Branch Integration Case Study
 *
 * C++17+
 *
 * This program models a software team's repository workflow around a
 * production application. It demonstrates:
 *
 *   - branch-oriented development
 *   - commits and immutable history concepts
 *   - fast-forward integration
 *   - three-way merge reasoning
 *   - merge conflicts
 *   - conflict resolution
 *   - rebase concepts
 *   - cherry-pick
 *   - release and hotfix branches
 *   - validation and integration testing
 *   - audit history
 *   - complexity and operational trade-offs
 *
 * The program is intentionally independent of a real Git executable.
 * Instead, it implements a simplified in-memory model of Git's branch,
 * commit, merge, and rebase concepts so the architectural mechanisms can
 * be inspected directly in C++.
 */

#include <algorithm>
#include <chrono>
#include <cstddef>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>


// ============================================================================
// Domain model
// ============================================================================

struct FileSnapshot {
    std::map<std::string, std::string> files;

    bool operator==(const FileSnapshot& other) const {
        return files == other.files;
    }

    bool operator!=(const FileSnapshot& other) const {
        return !(*this == other);
    }
};


struct Commit {
    std::string id;
    std::vector<std::string> parents;
    std::string author;
    std::string message;
    FileSnapshot snapshot;
    std::size_t generation = 0;
};


enum class MergeStatus {
    FastForward,
    Merged,
    Conflict,
    AlreadyIntegrated
};


struct MergeResult {
    MergeStatus status;
    std::string resultingCommit;
    std::vector<std::string> conflicts;
};


struct RebaseResult {
    bool success = false;
    std::string resultingCommit;
    std::vector<std::string> conflicts;
};


struct AuditEvent {
    std::string actor;
    std::string action;
    std::string branch;
    std::string commit;
    std::string details;
};


// ============================================================================
// Utility functions
// ============================================================================

std::string join(
    const std::vector<std::string>& values,
    const std::string& separator
) {
    std::ostringstream output;

    for (std::size_t i = 0; i < values.size(); ++i) {
        if (i != 0) {
            output << separator;
        }

        output << values[i];
    }

    return output.str();
}


std::string mergeStatusToString(MergeStatus status) {
    switch (status) {
        case MergeStatus::FastForward:
            return "fast-forward";
        case MergeStatus::Merged:
            return "merge commit";
        case MergeStatus::Conflict:
            return "conflict";
        case MergeStatus::AlreadyIntegrated:
            return "already integrated";
    }

    return "unknown";
}


// ============================================================================
// Repository
// ============================================================================

class Repository {
private:
    std::unordered_map<std::string, Commit> commits;
    std::map<std::string, std::string> branches;
    std::string currentBranch;
    std::vector<AuditEvent> auditTrail;
    std::size_t nextCommitNumber = 1;

    /*
     * In a real Git repository, commit IDs are cryptographic object IDs.
     * This educational implementation uses deterministic IDs so the
     * branch graph remains easy to inspect.
     */
    std::string generateCommitId() {
        std::ostringstream id;
        id << "c" << std::setw(4) << std::setfill('0') << nextCommitNumber++;
        return id.str();
    }

    static bool hasFile(
        const FileSnapshot& snapshot,
        const std::string& path
    ) {
        return snapshot.files.find(path) != snapshot.files.end();
    }

    static std::string fileContent(
        const FileSnapshot& snapshot,
        const std::string& path
    ) {
        const auto iterator = snapshot.files.find(path);

        if (iterator == snapshot.files.end()) {
            return "";
        }

        return iterator->second;
    }

    void recordAudit(
        const std::string& actor,
        const std::string& action,
        const std::string& branch,
        const std::string& commit,
        const std::string& details
    ) {
        auditTrail.push_back({
            actor,
            action,
            branch,
            commit,
            details
        });
    }

public:
    Repository() = default;

    void initialize(
        const std::string& actor,
        const FileSnapshot& initialSnapshot
    ) {
        if (!branches.empty()) {
            throw std::logic_error("Repository is already initialized.");
        }

        Commit root;
        root.id = generateCommitId();
        root.author = actor;
        root.message = "Initial application";
        root.snapshot = initialSnapshot;
        root.generation = 0;

        commits.emplace(root.id, root);
        branches["main"] = root.id;
        currentBranch = "main";

        recordAudit(
            actor,
            "create-branch",
            "main",
            root.id,
            "Initialized repository"
        );
    }

    const Commit& getCommit(const std::string& id) const {
        const auto iterator = commits.find(id);

        if (iterator == commits.end()) {
            throw std::runtime_error("Unknown commit: " + id);
        }

        return iterator->second;
    }

    const std::string& currentBranchName() const {
        return currentBranch;
    }

    const std::string& head() const {
        const auto iterator = branches.find(currentBranch);

        if (iterator == branches.end()) {
            throw std::logic_error("Current branch has no reference.");
        }

        return iterator->second;
    }

    const FileSnapshot& workingSnapshot() const {
        return getCommit(head()).snapshot;
    }

    void createBranch(
        const std::string& name,
        const std::string& startPoint = ""
    ) {
        if (branches.count(name) != 0) {
            throw std::runtime_error("Branch already exists: " + name);
        }

        const std::string base =
            startPoint.empty() ? head() : startPoint;

        getCommit(base);
        branches[name] = base;

        recordAudit(
            "system",
            "create-branch",
            name,
            base,
            "Branch created"
        );
    }

    void switchBranch(const std::string& name) {
        if (branches.count(name) == 0) {
            throw std::runtime_error("Unknown branch: " + name);
        }

        currentBranch = name;

        recordAudit(
            "system",
            "switch-branch",
            currentBranch,
            branches.at(currentBranch),
            "HEAD moved to branch"
        );
    }

    void deleteBranch(const std::string& name) {
        if (name == currentBranch) {
            throw std::runtime_error(
                "Cannot delete the currently checked-out branch."
            );
        }

        if (branches.erase(name) == 0) {
            throw std::runtime_error("Unknown branch: " + name);
        }
    }

    std::string createCommit(
        const std::string& author,
        const std::string& message,
        const FileSnapshot& snapshot
    ) {
        Commit newCommit;
        newCommit.id = generateCommitId();
        newCommit.parents.push_back(head());
        newCommit.author = author;
        newCommit.message = message;
        newCommit.snapshot = snapshot;
        newCommit.generation = getCommit(head()).generation + 1;

        commits.emplace(newCommit.id, newCommit);
        branches[currentBranch] = newCommit.id;

        recordAudit(
            author,
            "commit",
            currentBranch,
            newCommit.id,
            message
        );

        return newCommit.id;
    }

    /*
     * Determine whether ancestor is reachable from descendant.
     *
     * This is a graph traversal. In a repository with V reachable commits
     * and E parent edges, the traversal is O(V + E).
     */
    bool isAncestor(
        const std::string& ancestor,
        const std::string& descendant
    ) const {
        if (ancestor == descendant) {
            return true;
        }

        std::vector<std::string> stack{descendant};
        std::set<std::string> visited;

        while (!stack.empty()) {
            const std::string current = stack.back();
            stack.pop_back();

            if (!visited.insert(current).second) {
                continue;
            }

            const Commit& commit = getCommit(current);

            for (const std::string& parent : commit.parents) {
                if (parent == ancestor) {
                    return true;
                }

                stack.push_back(parent);
            }
        }

        return false;
    }

    /*
     * Find a common ancestor. For the educational repository, the candidate
     * with the greatest generation number is selected.
     */
    std::string mergeBase(
        const std::string& first,
        const std::string& second
    ) const {
        std::set<std::string> firstAncestors;
        std::vector<std::string> stack{first};

        while (!stack.empty()) {
            const std::string current = stack.back();
            stack.pop_back();

            if (!firstAncestors.insert(current).second) {
                continue;
            }

            for (const std::string& parent : getCommit(current).parents) {
                stack.push_back(parent);
            }
        }

        std::optional<std::string> best;
        std::vector<std::string> secondStack{second};
        std::set<std::string> visited;

        while (!secondStack.empty()) {
            const std::string current = secondStack.back();
            secondStack.pop_back();

            if (!visited.insert(current).second) {
                continue;
            }

            if (firstAncestors.count(current) != 0) {
                if (
                    !best.has_value() ||
                    getCommit(current).generation >
                        getCommit(*best).generation
                ) {
                    best = current;
                }
            }

            for (const std::string& parent : getCommit(current).parents) {
                secondStack.push_back(parent);
            }
        }

        if (!best.has_value()) {
            throw std::runtime_error("No common ancestor exists.");
        }

        return *best;
    }

    /*
     * Perform a three-way snapshot merge.
     *
     * For each path:
     *
     *   base == ours and theirs changed -> take theirs
     *   base == theirs and ours changed -> take ours
     *   ours == theirs                -> take either
     *   all three differ              -> conflict
     *
     * This is a simplified content model. Real Git performs considerably more
     * sophisticated file-level and rename-aware merge processing.
     */
    MergeResult mergeBranch(
        const std::string& sourceBranch,
        const std::string& actor
    ) {
        if (branches.count(sourceBranch) == 0) {
            throw std::runtime_error(
                "Unknown source branch: " + sourceBranch
            );
        }

        const std::string oursId = head();
        const std::string theirsId = branches.at(sourceBranch);

        if (oursId == theirsId || isAncestor(theirsId, oursId)) {
            return {
                MergeStatus::AlreadyIntegrated,
                oursId,
                {}
            };
        }

        if (isAncestor(oursId, theirsId)) {
            branches[currentBranch] = theirsId;

            recordAudit(
                actor,
                "fast-forward",
                currentBranch,
                theirsId,
                "Fast-forwarded from " + oursId
            );

            return {
                MergeStatus::FastForward,
                theirsId,
                {}
            };
        }

        const std::string baseId = mergeBase(oursId, theirsId);

        const FileSnapshot& base = getCommit(baseId).snapshot;
        const FileSnapshot& ours = getCommit(oursId).snapshot;
        const FileSnapshot& theirs = getCommit(theirsId).snapshot;

        std::set<std::string> paths;

        for (const auto& entry : base.files) {
            paths.insert(entry.first);
        }

        for (const auto& entry : ours.files) {
            paths.insert(entry.first);
        }

        for (const auto& entry : theirs.files) {
            paths.insert(entry.first);
        }

        FileSnapshot merged;
        std::vector<std::string> conflicts;

        for (const std::string& path : paths) {
            const bool baseHas = hasFile(base, path);
            const bool oursHas = hasFile(ours, path);
            const bool theirsHas = hasFile(theirs, path);

            const std::string baseValue =
                fileContent(base, path);
            const std::string oursValue =
                fileContent(ours, path);
            const std::string theirsValue =
                fileContent(theirs, path);

            if (oursHas == theirsHas && oursValue == theirsValue) {
                if (oursHas) {
                    merged.files[path] = oursValue;
                }

                continue;
            }

            if (baseHas == oursHas && baseValue == oursValue) {
                if (theirsHas) {
                    merged.files[path] = theirsValue;
                }

                continue;
            }

            if (baseHas == theirsHas && baseValue == theirsValue) {
                if (oursHas) {
                    merged.files[path] = oursValue;
                }

                continue;
            }

            conflicts.push_back(path);
        }

        if (!conflicts.empty()) {
            return {
                MergeStatus::Conflict,
                "",
                conflicts
            };
        }

        Commit mergeCommit;
        mergeCommit.id = generateCommitId();
        mergeCommit.parents = {oursId, theirsId};
        mergeCommit.author = actor;
        mergeCommit.message =
            "Merge " + sourceBranch + " into " + currentBranch;
        mergeCommit.snapshot = merged;
        mergeCommit.generation =
            std::max(
                getCommit(oursId).generation,
                getCommit(theirsId).generation
            ) + 1;

        commits.emplace(mergeCommit.id, mergeCommit);
        branches[currentBranch] = mergeCommit.id;

        recordAudit(
            actor,
            "merge",
            currentBranch,
            mergeCommit.id,
            "Three-way merge from " + sourceBranch
        );

        return {
            MergeStatus::Merged,
            mergeCommit.id,
            {}
        };
    }

    /*
     * A controlled conflict-resolution operation.
     *
     * In real Git, the developer edits files and stages the result. Here,
     * resolution is modeled by supplying a complete merged snapshot.
     */
    std::string resolveMerge(
        const std::string& sourceBranch,
        const FileSnapshot& resolvedSnapshot,
        const std::string& actor
    ) {
        if (branches.count(sourceBranch) == 0) {
            throw std::runtime_error("Unknown source branch.");
        }

        const std::string oursId = head();
        const std::string theirsId = branches.at(sourceBranch);

        Commit mergeCommit;
        mergeCommit.id = generateCommitId();
        mergeCommit.parents = {oursId, theirsId};
        mergeCommit.author = actor;
        mergeCommit.message =
            "Resolve merge conflict: " + sourceBranch;
        mergeCommit.snapshot = resolvedSnapshot;
        mergeCommit.generation =
            std::max(
                getCommit(oursId).generation,
                getCommit(theirsId).generation
            ) + 1;

        commits.emplace(mergeCommit.id, mergeCommit);
        branches[currentBranch] = mergeCommit.id;

        recordAudit(
            actor,
            "resolve-conflict",
            currentBranch,
            mergeCommit.id,
            "Resolved merge conflict from " + sourceBranch
        );

        return mergeCommit.id;
    }

    /*
     * Simplified cherry-pick:
     * apply the entire snapshot from a selected commit as the new state.
     *
     * A production cherry-pick applies the selected commit's patch relative
     * to its parent rather than blindly replacing the entire tree.
     */
    std::string cherryPick(
        const std::string& commitId,
        const std::string& actor
    ) {
        const Commit& selected = getCommit(commitId);

        if (selected.parents.empty()) {
            throw std::runtime_error(
                "Cherry-picking the root commit is not supported here."
            );
        }

        const Commit& parent = getCommit(selected.parents.front());

        FileSnapshot result = workingSnapshot();

        std::set<std::string> paths;

        for (const auto& entry : parent.snapshot.files) {
            paths.insert(entry.first);
        }

        for (const auto& entry : selected.snapshot.files) {
            paths.insert(entry.first);
        }

        for (const std::string& path : paths) {
            const bool parentHas =
                hasFile(parent.snapshot, path);
            const bool selectedHas =
                hasFile(selected.snapshot, path);

            const std::string parentValue =
                fileContent(parent.snapshot, path);
            const std::string selectedValue =
                fileContent(selected.snapshot, path);

            if (parentHas == selectedHas &&
                parentValue == selectedValue) {
                continue;
            }

            if (!selectedHas) {
                result.files.erase(path);
            } else {
                result.files[path] = selectedValue;
            }
        }

        return createCommit(
            actor,
            "Cherry-pick: " + selected.message,
            result
        );
    }

    /*
     * Simplified rebase.
     *
     * The implementation discovers commits that are reachable from the
     * current branch but not from the target branch, then recreates those
     * commits in chronological order.
     *
     * Real Git computes and applies patches, detects conflicts during each
     * replay, and preserves selected metadata according to rebase options.
     */
    RebaseResult rebaseOnto(
        const std::string& targetBranch,
        const std::string& actor
    ) {
        if (branches.count(targetBranch) == 0) {
            throw std::runtime_error(
                "Unknown target branch: " + targetBranch
            );
        }

        const std::string oldHead = head();
        const std::string newBase = branches.at(targetBranch);

        if (isAncestor(oldHead, newBase)) {
            branches[currentBranch] = newBase;

            return {
                true,
                newBase,
                {}
            };
        }

        const std::string base = mergeBase(oldHead, newBase);

        std::vector<std::string> commitsToReplay;
        std::string cursor = oldHead;

        while (cursor != base) {
            commitsToReplay.push_back(cursor);

            const Commit& current = getCommit(cursor);

            if (current.parents.empty()) {
                throw std::runtime_error(
                    "Invalid history while calculating rebase."
                );
            }

            cursor = current.parents.front();
        }

        std::reverse(
            commitsToReplay.begin(),
            commitsToReplay.end()
        );

        std::string currentBase = newBase;

        for (const std::string& oldCommitId : commitsToReplay) {
            const Commit& oldCommit = getCommit(oldCommitId);

            Commit recreated;
            recreated.id = generateCommitId();
            recreated.parents = {currentBase};
            recreated.author = oldCommit.author;
            recreated.message =
                oldCommit.message + " [rebased]";
            recreated.snapshot = oldCommit.snapshot;
            recreated.generation =
                getCommit(currentBase).generation + 1;

            commits.emplace(recreated.id, recreated);
            currentBase = recreated.id;
        }

        branches[currentBranch] = currentBase;

        recordAudit(
            actor,
            "rebase",
            currentBranch,
            currentBase,
            "Rebased onto " + targetBranch
        );

        return {
            true,
            currentBase,
            {}
        };
    }

    void printBranches() const {
        std::cout << "\nBranches:\n";

        for (const auto& [name, commitId] : branches) {
            std::cout
                << (name == currentBranch ? "* " : "  ")
                << name
                << " -> "
                << commitId
                << "\n";
        }
    }

    void printHistory(
        const std::string& branch,
        std::size_t maximum = 20
    ) const {
        if (branches.count(branch) == 0) {
            throw std::runtime_error("Unknown branch.");
        }

        std::cout << "\nHistory for " << branch << ":\n";

        std::vector<std::string> stack{branches.at(branch)};
        std::set<std::string> visited;
        std::size_t count = 0;

        while (!stack.empty() && count < maximum) {
            const std::string current = stack.back();
            stack.pop_back();

            if (!visited.insert(current).second) {
                continue;
            }

            const Commit& commit = getCommit(current);

            std::cout
                << commit.id
                << " | generation=" << commit.generation
                << " | " << commit.message
                << " | parents=["
                << join(commit.parents, ", ")
                << "]\n";

            for (const std::string& parent : commit.parents) {
                stack.push_back(parent);
            }

            ++count;
        }
    }

    void printSnapshot() const {
        std::cout << "\nCurrent snapshot:\n";

        for (const auto& [path, content] : workingSnapshot().files) {
            std::cout
                << "\n[" << path << "]\n"
                << content;
        }
    }

    void printAuditTrail() const {
        std::cout << "\nAudit trail:\n";

        for (const AuditEvent& event : auditTrail) {
            std::cout
                << event.actor
                << " | "
                << event.action
                << " | branch=" << event.branch
                << " | commit=" << event.commit
                << " | "
                << event.details
                << "\n";
        }
    }
};


// ============================================================================
// Demonstration helpers
// ============================================================================

void printSection(const std::string& name) {
    std::cout << "\n"
              << std::string(78, '=')
              << "\n"
              << name
              << "\n"
              << std::string(78, '=')
              << "\n";
}


void demonstrateBasicDevelopment(Repository& repository) {
    printSection("1. Feature Branch Development");

    repository.createBranch("feature/payments");
    repository.switchBranch("feature/payments");

    FileSnapshot snapshot = repository.workingSnapshot();

    snapshot.files["payments.txt"] =
        "payment-provider=internal\n"
        "validation=strict\n";

    repository.createCommit(
        "developer",
        "Implement payment validation",
        snapshot
    );

    repository.printBranches();
    repository.printHistory("feature/payments");
}


void demonstrateMainProgress(Repository& repository) {
    printSection("2. Independent Main-Branch Progress");

    repository.switchBranch("main");

    FileSnapshot snapshot = repository.workingSnapshot();

    snapshot.files["operations.txt"] =
        "monitoring=enabled\n"
        "alerts=enabled\n";

    repository.createCommit(
        "platform-engineer",
        "Add operational monitoring",
        snapshot
    );

    repository.printHistory("main");
}


void demonstrateMerge(Repository& repository) {
    printSection("3. Three-Way Merge");

    repository.switchBranch("main");

    const MergeResult result =
        repository.mergeBranch("feature/payments", "release-manager");

    std::cout
        << "Merge result: "
        << mergeStatusToString(result.status)
        << "\n";

    if (result.status == MergeStatus::Merged) {
        std::cout
            << "Merge commit: "
            << result.resultingCommit
            << "\n";
    }

    if (!result.conflicts.empty()) {
        std::cout
            << "Conflicts: "
            << join(result.conflicts, ", ")
            << "\n";
    }

    repository.printHistory("main");
}


void demonstrateConflictScenario() {
    printSection("4. Conflict Scenario");

    Repository repository;

    FileSnapshot initial;
    initial.files["config.txt"] =
        "timeout=30\n"
        "mode=production\n";

    repository.initialize("system", initial);

    repository.createBranch("feature/config");
    repository.switchBranch("feature/config");

    FileSnapshot feature = repository.workingSnapshot();
    feature.files["config.txt"] =
        "timeout=60\n"
        "mode=production\n";

    repository.createCommit(
        "developer",
        "Increase feature timeout",
        feature
    );

    repository.switchBranch("main");

    FileSnapshot mainChange = repository.workingSnapshot();
    mainChange.files["config.txt"] =
        "timeout=15\n"
        "mode=production\n";

    repository.createCommit(
        "operations",
        "Reduce production timeout",
        mainChange
    );

    const MergeResult result =
        repository.mergeBranch("feature/config", "release-manager");

    std::cout
        << "Merge result: "
        << mergeStatusToString(result.status)
        << "\n";

    if (!result.conflicts.empty()) {
        std::cout
            << "Detected conflict paths: "
            << join(result.conflicts, ", ")
            << "\n";
    }

    /*
     * The team decides that 30 seconds is the safe production compromise.
     * A real Git workflow would edit the file, stage it, test it, and then
     * complete the merge.
     */
    FileSnapshot resolved = repository.workingSnapshot();
    resolved.files["config.txt"] =
        "timeout=30\n"
        "mode=production\n";

    const std::string mergeCommit =
        repository.resolveMerge(
            "feature/config",
            resolved,
            "release-manager"
        );

    std::cout
        << "Resolved merge commit: "
        << mergeCommit
        << "\n";

    repository.printSnapshot();
}


void demonstrateRebase() {
    printSection("5. Rebase Case Study");

    Repository repository;

    FileSnapshot initial;
    initial.files["application.txt"] =
        "release=1\n"
        "status=stable\n";

    repository.initialize("system", initial);

    repository.createBranch("feature/analytics");
    repository.switchBranch("feature/analytics");

    FileSnapshot firstFeature =
        repository.workingSnapshot();

    firstFeature.files["analytics.txt"] =
        "events=enabled\n";

    repository.createCommit(
        "developer",
        "Add analytics events",
        firstFeature
    );

    FileSnapshot secondFeature =
        repository.workingSnapshot();

    secondFeature.files["analytics.txt"] =
        "events=enabled\n"
        "retention-days=30\n";

    repository.createCommit(
        "developer",
        "Configure analytics retention",
        secondFeature
    );

    repository.switchBranch("main");

    FileSnapshot mainProgress =
        repository.workingSnapshot();

    mainProgress.files["application.txt"] =
        "release=1\n"
        "status=stable\n"
        "monitoring=enabled\n";

    repository.createCommit(
        "platform-engineer",
        "Enable production monitoring",
        mainProgress
    );

    std::cout << "\nBefore rebase:\n";
    repository.printHistory("feature/analytics");

    repository.switchBranch("feature/analytics");

    const RebaseResult result =
        repository.rebaseOnto(
            "main",
            "developer"
        );

    std::cout
        << "Rebase success: "
        << std::boolalpha
        << result.success
        << "\n";

    std::cout
        << "New feature tip: "
        << result.resultingCommit
        << "\n";

    std::cout << "\nAfter rebase:\n";
    repository.printHistory("feature/analytics");
}


void demonstrateCherryPick() {
    printSection("6. Cherry-Pick Hotfix");

    Repository repository;

    FileSnapshot initial;
    initial.files["service.txt"] =
        "status=running\n";

    repository.initialize("system", initial);

    repository.createBranch("hotfix/security");
    repository.switchBranch("hotfix/security");

    FileSnapshot hotfix =
        repository.workingSnapshot();

    hotfix.files["service.txt"] =
        "status=running\n"
        "input-validation=strict\n";

    const std::string hotfixCommit =
        repository.createCommit(
            "security-engineer",
            "Harden input validation",
            hotfix
        );

    repository.switchBranch("main");

    const std::string cherryPicked =
        repository.cherryPick(
            hotfixCommit,
            "release-manager"
        );

    std::cout
        << "Original hotfix commit: "
        << hotfixCommit
        << "\n";

    std::cout
        << "Cherry-picked commit: "
        << cherryPicked
        << "\n";

    repository.printHistory("main");
}


void demonstrateReleaseFlow() {
    printSection("7. Release Branch and Hotfix Flow");

    Repository repository;

    FileSnapshot initial;
    initial.files["service.txt"] =
        "version=2.0\n"
        "status=development\n";

    repository.initialize("system", initial);

    repository.createBranch("release/2.0");
    repository.switchBranch("release/2.0");

    FileSnapshot release =
        repository.workingSnapshot();

    release.files["service.txt"] =
        "version=2.0\n"
        "status=release-candidate\n";

    repository.createCommit(
        "release-manager",
        "Prepare version 2.0",
        release
    );

    repository.createBranch("hotfix/2.0.1");
    repository.switchBranch("hotfix/2.0.1");

    FileSnapshot hotfix =
        repository.workingSnapshot();

    hotfix.files["security.txt"] =
        "patch=2.0.1\n"
        "validation=strict\n";

    const std::string hotfixCommit =
        repository.createCommit(
            "security-engineer",
            "Patch release security issue",
            hotfix
        );

    repository.switchBranch("release/2.0");

    const std::string appliedFix =
        repository.cherryPick(
            hotfixCommit,
            "release-manager"
        );

    std::cout
        << "Release branch received hotfix as commit "
        << appliedFix
        << "\n";

    repository.printHistory("release/2.0");
}


void demonstrateValidation() {
    printSection("8. Integration Validation");

    Repository repository;

    FileSnapshot initial;
    initial.files["application.txt"] =
        "version=1\n"
        "status=stable\n";

    repository.initialize("system", initial);

    repository.createBranch("feature/validation");
    repository.switchBranch("feature/validation");

    FileSnapshot feature =
        repository.workingSnapshot();

    feature.files["validation.txt"] =
        "schema=valid\n";

    repository.createCommit(
        "developer",
        "Add validation rules",
        feature
    );

    repository.switchBranch("main");

    const MergeResult result =
        repository.mergeBranch(
            "feature/validation",
            "release-manager"
        );

    if (
        result.status != MergeStatus::FastForward &&
        result.status != MergeStatus::Merged
    ) {
        throw std::runtime_error(
            "Integration validation failed: unexpected merge state."
        );
    }

    const FileSnapshot& snapshot =
        repository.workingSnapshot();

    if (
        snapshot.files.find("validation.txt") ==
        snapshot.files.end()
    ) {
        throw std::runtime_error(
            "Integration validation failed: validation file missing."
        );
    }

    std::cout
        << "Integration tests: PASS\n"
        << "Required validation artifact: PRESENT\n"
        << "Branch integration state: "
        << mergeStatusToString(result.status)
        << "\n";
}


// ============================================================================
// Architectural analysis
// ============================================================================

void explainArchitecture() {
    printSection("9. Architecture and Design Decisions");

    std::cout
        << "Repository: owns commits, branches, HEAD, and audit events.\n"
        << "Commit: immutable historical state with parent references.\n"
        << "Branch: a named pointer to a commit.\n"
        << "Snapshot: simplified representation of tracked files.\n"
        << "Merge: combines two histories using a common ancestor.\n"
        << "Rebase: recreates commits on a different parent chain.\n"
        << "Cherry-pick: transfers the effect of one selected commit.\n"
        << "Audit trail: records branch and history operations.\n";

    std::cout
        << "\nThis model intentionally separates repository state from "
        << "operations so the branching mechanisms can be tested without "
        << "depending on a filesystem or external process.\n";
}


void explainComplexity() {
    printSection("10. Complexity Considerations");

    std::cout
        << "Branch creation: approximately O(1) reference insertion.\n"
        << "Branch switch in this model: O(1).\n"
        << "Ancestor search: O(V + E) over reachable commit graph.\n"
        << "Merge-base search: O(V + E) in the simplified implementation.\n"
        << "Snapshot three-way merge: O(P log P) due to ordered path storage,\n"
        << "where P is the number of distinct paths considered.\n"
        << "Rebase: O(C * snapshot-processing-cost), where C is replayed commits.\n";

    std::cout
        << "\nReal Git has additional optimizations and substantially more "
        << "complex object, index, rename, merge, and storage algorithms. "
        << "These complexity figures describe this educational model, not "
        << "the complete implementation of Git itself.\n";
}


void explainFailureModes() {
    printSection("11. Failure Conditions and Trade-offs");

    std::cout
        << "Merge conflict:\n"
        << "  Two branches make incompatible changes to the same logical path.\n\n"

        << "Rebase risk:\n"
        << "  Replayed commits receive new identities, so shared history can diverge.\n\n"

        << "Cherry-pick risk:\n"
        << "  A selected change can depend on context that does not exist on the target branch.\n\n"

        << "Long-lived branches:\n"
        << "  More isolation but potentially larger integration gaps.\n\n"

        << "Short-lived branches:\n"
        << "  Frequent integration but less long-term isolation.\n\n"

        << "Merge-heavy history:\n"
        << "  Preserves explicit integration points but can be more complex to read.\n\n"

        << "Linearized history:\n"
        << "  Easier chronological reading but can hide some branch topology after rebasing.\n";
}


void explainSecurity() {
    printSection("12. Security and Integrity");

    std::cout
        << "Git's real object IDs are cryptographic hashes that help detect "
        << "object modification.\n"
        << "Signed commits and tags can provide provenance information.\n"
        << "Protected branches can restrict direct updates to critical refs.\n"
        << "CI permissions should follow least-privilege principles.\n"
        << "Secrets should never be committed merely because a branch is private.\n"
        << "Deleting a secret-containing file later does not automatically erase "
        << "the secret from repository history.\n";
}


void explainProductionWorkflow() {
    printSection("13. Production Workflow");

    std::cout
        << "1. Create a focused feature branch.\n"
        << "2. Make small, coherent commits.\n"
        << "3. Run local validation.\n"
        << "4. Push the branch to a remote.\n"
        << "5. Review the diff.\n"
        << "6. Run CI validation.\n"
        << "7. Update the branch with the integration target when appropriate.\n"
        << "8. Resolve conflicts based on intended behavior.\n"
        << "9. Merge or rebase according to repository policy.\n"
        << "10. Tag stable releases when release identification is required.\n"
        << "11. Delete obsolete branches.\n";
}


// ============================================================================
// Main
// ============================================================================

int main() {
    try {
        printSection("Git Branching: Industry-Style Case Study");

        Repository repository;

        FileSnapshot initial;
        initial.files["application.txt"] =
            "name=BranchAwareService\n"
            "version=1.0\n"
            "status=stable\n";

        initial.files["README.txt"] =
            "Production service repository\n";

        repository.initialize(
            "platform-team",
            initial
        );

        demonstrateBasicDevelopment(repository);
        demonstrateMainProgress(repository);
        demonstrateMerge(repository);
        demonstrateConflictScenario();
        demonstrateRebase();
        demonstrateCherryPick();
        demonstrateReleaseFlow();
        demonstrateValidation();

        explainArchitecture();
        explainComplexity();
        explainFailureModes();
        explainSecurity();
        explainProductionWorkflow();

        printSection("14. Audit Trail");

        repository.printAuditTrail();

        printSection("15. Final Repository State");

        repository.printBranches();
        repository.switchBranch("main");
        repository.printSnapshot();

        std::cout
            << "\nCase study completed successfully.\n";

        return 0;
    }
    catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << "\n";

        return 1;
    }
}
