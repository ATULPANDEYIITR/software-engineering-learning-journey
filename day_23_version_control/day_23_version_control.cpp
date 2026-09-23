#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <map>
#include <queue>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * Git Fundamentals: C++ technical case study
 *
 * Scenario:
 *   A small engineering team maintains a configuration repository for a
 *   production service. The repository needs versioned snapshots, staging,
 *   commits, branches, history inspection, integrity checks, and a simplified
 *   three-way merge.
 *
 * The implementation is intentionally self-contained and uses only the C++17
 * standard library. It models Git concepts rather than implementing the full
 * Git storage format or cryptographic SHA-1 algorithm.
 *
 * The educational object ID below is a deterministic FNV-1a-style hash.
 * Real Git uses cryptographic object hashing and a specific binary object
 * format. The architectural concepts are the focus of this case study.
 *
 * Compile:
 *   g++ -std=c++17 -O2 -Wall -Wextra -pedantic git_fundamentals.cpp -o git_case
 *
 * Run:
 *   ./git_case
 */

using namespace std;

// ---------------------------------------------------------------------------
// 1. Utility hashing
// ---------------------------------------------------------------------------

class ObjectHasher {
public:
    static string hash(const string& type, const string& content) {
        const string material =
            type + " " + to_string(content.size()) + '\0' + content;

        uint64_t hashValue = 14695981039346656037ULL;

        for (unsigned char character : material) {
            hashValue ^= character;
            hashValue *= 1099511628211ULL;
        }

        ostringstream output;
        output << hex << setfill('0') << setw(16) << hashValue;
        return output.str();
    }

    static string shortId(const string& objectId, size_t length = 8) {
        return objectId.substr(0, min(length, objectId.size()));
    }
};

// ---------------------------------------------------------------------------
// 2. Core repository objects
// ---------------------------------------------------------------------------

struct Blob {
    string content;

    string id() const {
        return ObjectHasher::hash("blob", content);
    }
};

struct TreeEntry {
    string path;
    string mode;
    string objectId;
    string type;
};

struct Tree {
    map<string, TreeEntry> entries;

    string serialize() const {
        ostringstream output;

        for (const auto& [path, entry] : entries) {
            output << entry.mode << " "
                   << entry.type << " "
                   << entry.objectId << " "
                   << path << "\n";
        }

        return output.str();
    }

    string id() const {
        return ObjectHasher::hash("tree", serialize());
    }
};

struct Commit {
    string treeId;
    vector<string> parents;
    string author;
    string message;

    string serialize() const {
        ostringstream output;

        output << "tree " << treeId << "\n";

        for (const string& parent : parents) {
            output << "parent " << parent << "\n";
        }

        output << "author " << author << "\n";
        output << "\n";
        output << message;

        return output.str();
    }

    string id() const {
        return ObjectHasher::hash("commit", serialize());
    }
};

// ---------------------------------------------------------------------------
// 3. Repository
// ---------------------------------------------------------------------------

class Repository {
public:
    using Snapshot = map<string, string>;

private:
    string author;

    // Object storage. Each type has a separate map because this keeps the
    // educational implementation easy to inspect.
    map<string, Blob> blobs;
    map<string, Tree> trees;
    map<string, Commit> commits;

    // The working tree contains the files currently being edited.
    Snapshot workingTree;

    // The index is the proposed next snapshot.
    Snapshot index;

    // Branch names point to commit IDs.
    map<string, string> branches;

    // HEAD normally identifies a branch. When branchName is empty, HEAD is
    // detached and detachedHead contains the selected commit.
    string branchName;
    string detachedHead;

public:
    explicit Repository(string authorName)
        : author(std::move(authorName)) {}

    void init(const string& branch = "main") {
        validateBranchName(branch);

        if (!branches.empty()) {
            throw runtime_error("Repository is already initialized.");
        }

        branches[branch] = "";
        branchName = branch;
    }

    string head() const {
        if (!branchName.empty()) {
            auto iterator = branches.find(branchName);

            if (iterator == branches.end()) {
                return "";
            }

            return iterator->second;
        }

        return detachedHead;
    }

    // -----------------------------------------------------------------------
    // Object database
    // -----------------------------------------------------------------------

    string writeBlob(const string& content) {
        Blob blob{content};
        const string objectId = blob.id();
        blobs[objectId] = blob;
        return objectId;
    }

    string writeTree(const Snapshot& snapshot) {
        Tree tree;

        for (const auto& [path, content] : snapshot) {
            validatePath(path);

            const string blobId = writeBlob(content);

            tree.entries[path] = TreeEntry{
                path,
                "100644",
                blobId,
                "blob"
            };
        }

        const string treeId = tree.id();
        trees[treeId] = tree;
        return treeId;
    }

    string writeCommit(
        const string& treeId,
        const vector<string>& parents,
        const string& message
    ) {
        if (message.empty()) {
            throw runtime_error("Commit message cannot be empty.");
        }

        Commit commit{
            treeId,
            parents,
            author,
            message
        };

        const string commitId = commit.id();
        commits[commitId] = commit;
        return commitId;
    }

    // -----------------------------------------------------------------------
    // Working tree and staging
    // -----------------------------------------------------------------------

    void writeFile(const string& path, const string& content) {
        validatePath(path);
        workingTree[path] = content;
    }

    void deleteFile(const string& path) {
        validatePath(path);
        workingTree.erase(path);
    }

    void stage(const string& path) {
        validatePath(path);

        auto iterator = workingTree.find(path);

        if (iterator == workingTree.end()) {
            // Removing the index entry stages a deletion in this simplified
            // representation.
            index.erase(path);
        } else {
            index[path] = iterator->second;
        }
    }

    void stageAll() {
        index = workingTree;
    }

    string commit(const string& message) {
        if (index.empty()) {
            throw runtime_error("Nothing is staged.");
        }

        const string treeId = writeTree(index);
        const string parent = head();

        vector<string> parents;

        if (!parent.empty()) {
            parents.push_back(parent);
        }

        const string commitId =
            writeCommit(treeId, parents, message);

        updateHead(commitId);

        workingTree = index;

        return commitId;
    }

    // -----------------------------------------------------------------------
    // Branch operations
    // -----------------------------------------------------------------------

    void createBranch(
        const string& name,
        const string& startingPoint = ""
    ) {
        validateBranchName(name);

        if (branches.count(name)) {
            throw runtime_error("Branch already exists: " + name);
        }

        const string target =
            startingPoint.empty() ? head() : startingPoint;

        if (target.empty()) {
            throw runtime_error(
                "Cannot create a branch without a starting commit."
            );
        }

        requireCommit(target);
        branches[name] = target;
    }

    void checkout(const string& target) {
        auto branchIterator = branches.find(target);

        if (branchIterator != branches.end()) {
            branchName = target;
            detachedHead.clear();

            if (!branchIterator->second.empty()) {
                restoreCommit(branchIterator->second);
            }

            return;
        }

        requireCommit(target);

        // A commit ID that is not a branch name enters detached HEAD state.
        branchName.clear();
        detachedHead = target;
        restoreCommit(target);
    }

    // -----------------------------------------------------------------------
    // Snapshots and inspection
    // -----------------------------------------------------------------------

    Snapshot snapshotFromCommit(const string& commitId) const {
        const Commit& commit = getCommit(commitId);
        const Tree& tree = getTree(commit.treeId);

        Snapshot snapshot;

        for (const auto& [path, entry] : tree.entries) {
            auto blobIterator = blobs.find(entry.objectId);

            if (blobIterator == blobs.end()) {
                throw runtime_error(
                    "Tree references a missing blob: " + path
                );
            }

            snapshot[path] = blobIterator->second.content;
        }

        return snapshot;
    }

    void restoreCommit(const string& commitId) {
        Snapshot snapshot = snapshotFromCommit(commitId);
        workingTree = snapshot;
        index = snapshot;
    }

    vector<pair<string, string>> log(size_t limit = 20) const {
        vector<pair<string, string>> history;
        string current = head();

        while (!current.empty() && history.size() < limit) {
            const Commit& commit = getCommit(current);

            history.push_back({
                current,
                commit.message
            });

            if (commit.parents.empty()) {
                break;
            }

            current = commit.parents.front();
        }

        return history;
    }

    void printStatus() const {
        Snapshot headSnapshot;

        if (!head().empty()) {
            headSnapshot = snapshotFromCommit(head());
        }

        set<string> paths;

        for (const auto& [path, value] : headSnapshot) {
            (void)value;
            paths.insert(path);
        }

        for (const auto& [path, value] : index) {
            (void)value;
            paths.insert(path);
        }

        for (const auto& [path, value] : workingTree) {
            (void)value;
            paths.insert(path);
        }

        cout << "Status:\n";

        for (const string& path : paths) {
            const auto headValue = findValue(headSnapshot, path);
            const auto indexValue = findValue(index, path);
            const auto workingValue = findValue(workingTree, path);

            if (headValue != indexValue) {
                cout << "  staged change: " << path << "\n";
            }

            if (indexValue != workingValue) {
                if (!workingValue.has_value() && indexValue.has_value()) {
                    cout << "  deleted from working tree: " << path << "\n";
                } else if (!indexValue.has_value() &&
                           workingValue.has_value()) {
                    cout << "  untracked: " << path << "\n";
                } else {
                    cout << "  modified: " << path << "\n";
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // History graph
    // -----------------------------------------------------------------------

    map<string, int> ancestors(const string& commitId) const {
        map<string, int> distance;

        if (commitId.empty()) {
            return distance;
        }

        queue<string> pending;
        pending.push(commitId);
        distance[commitId] = 0;

        while (!pending.empty()) {
            const string current = pending.front();
            pending.pop();

            const int currentDistance = distance[current];
            const Commit& commit = getCommit(current);

            for (const string& parent : commit.parents) {
                if (!distance.count(parent)) {
                    distance[parent] = currentDistance + 1;
                    pending.push(parent);
                }
            }
        }

        return distance;
    }

    string mergeBase(
        const string& first,
        const string& second
    ) const {
        const auto firstAncestors = ancestors(first);
        const auto secondAncestors = ancestors(second);

        string best;
        int bestDistance = numeric_limits<int>::max();

        for (const auto& [candidate, firstDistance] : firstAncestors) {
            auto iterator = secondAncestors.find(candidate);

            if (iterator == secondAncestors.end()) {
                continue;
            }

            const int distance =
                max(firstDistance, iterator->second);

            if (distance < bestDistance) {
                bestDistance = distance;
                best = candidate;
            }
        }

        return best;
    }

    // -----------------------------------------------------------------------
    // Three-way merge
    // -----------------------------------------------------------------------

    struct MergeResult {
        Snapshot merged;
        vector<string> conflicts;
    };

    MergeResult threeWayMerge(
        const Snapshot& base,
        const Snapshot& ours,
        const Snapshot& theirs
    ) const {
        MergeResult result;

        set<string> paths;

        for (const auto& [path, value] : base) {
            (void)value;
            paths.insert(path);
        }

        for (const auto& [path, value] : ours) {
            (void)value;
            paths.insert(path);
        }

        for (const auto& [path, value] : theirs) {
            (void)value;
            paths.insert(path);
        }

        for (const string& path : paths) {
            const auto baseValue = findValue(base, path);
            const auto oursValue = findValue(ours, path);
            const auto theirsValue = findValue(theirs, path);

            if (oursValue == theirsValue) {
                if (oursValue.has_value()) {
                    result.merged[path] = *oursValue;
                }
            } else if (oursValue == baseValue) {
                if (theirsValue.has_value()) {
                    result.merged[path] = *theirsValue;
                }
            } else if (theirsValue == baseValue) {
                if (oursValue.has_value()) {
                    result.merged[path] = *oursValue;
                }
            } else {
                result.conflicts.push_back(path);
            }
        }

        return result;
    }

    // -----------------------------------------------------------------------
    // Integrity
    // -----------------------------------------------------------------------

    vector<string> verifyIntegrity() const {
        vector<string> problems;

        for (const auto& [storedId, blob] : blobs) {
            if (blob.id() != storedId) {
                problems.push_back(
                    "Blob integrity failure: " + storedId
                );
            }
        }

        for (const auto& [storedId, tree] : trees) {
            if (tree.id() != storedId) {
                problems.push_back(
                    "Tree integrity failure: " + storedId
                );
            }
        }

        for (const auto& [storedId, commit] : commits) {
            if (commit.id() != storedId) {
                problems.push_back(
                    "Commit integrity failure: " + storedId
                );
            }
        }

        for (const auto& [branch, commitId] : branches) {
            if (!commitId.empty() && !commits.count(commitId)) {
                problems.push_back(
                    "Branch " + branch +
                    " references a missing commit."
                );
            }
        }

        return problems;
    }

    void printRepositoryStatistics() const {
        cout << "\nRepository statistics:\n";
        cout << "  blobs:   " << blobs.size() << "\n";
        cout << "  trees:   " << trees.size() << "\n";
        cout << "  commits: " << commits.size() << "\n";
        cout << "  branches:" << branches.size() << "\n";
    }

private:
    void updateHead(const string& commitId) {
        if (!branchName.empty()) {
            branches[branchName] = commitId;
        } else {
            detachedHead = commitId;
        }
    }

    const Commit& getCommit(const string& commitId) const {
        auto iterator = commits.find(commitId);

        if (iterator == commits.end()) {
            throw runtime_error(
                "Commit not found: " + commitId
            );
        }

        return iterator->second;
    }

    const Tree& getTree(const string& treeId) const {
        auto iterator = trees.find(treeId);

        if (iterator == trees.end()) {
            throw runtime_error(
                "Tree not found: " + treeId
            );
        }

        return iterator->second;
    }

    void requireCommit(const string& commitId) const {
        (void)getCommit(commitId);
    }

    static optional<string> findValue(
        const Snapshot& snapshot,
        const string& path
    ) {
        auto iterator = snapshot.find(path);

        if (iterator == snapshot.end()) {
            return nullopt;
        }

        return iterator->second;
    }

    static void validatePath(const string& path) {
        if (
            path.empty() ||
            path == ".." ||
            path.rfind("../", 0) == 0 ||
            path.find("/../") != string::npos ||
            path.find('\0') != string::npos
        ) {
            throw invalid_argument(
                "Invalid repository path: " + path
            );
        }
    }

    static void validateBranchName(const string& name) {
        if (
            name.empty() ||
            name.front() == '-' ||
            name.back() == '.' ||
            name.back() == '/' ||
            name.find("..") != string::npos ||
            name.find(' ') != string::npos ||
            name.find('~') != string::npos ||
            name.find('^') != string::npos
        ) {
            throw invalid_argument(
                "Invalid branch name: " + name
            );
        }
    }
};

// ---------------------------------------------------------------------------
// 4. Case study workflow
// ---------------------------------------------------------------------------

void demonstrateProductionConfigurationRepository() {
    cout << string(72, '=') << "\n";
    cout << "GIT CASE STUDY: PRODUCTION CONFIGURATION REPOSITORY\n";
    cout << string(72, '=') << "\n";

    Repository repository("Engineering Team <engineering@example.com>");
    repository.init("main");

    // Step 1: Create the initial configuration.
    repository.writeFile(
        "config/app.conf",
        "service=payments\n"
        "port=8080\n"
        "environment=development\n"
    );

    repository.writeFile(
        "README.md",
        "# Payments Service\n"
        "Configuration repository for the service.\n"
    );

    repository.stageAll();

    const string initialCommit =
        repository.commit("Create service configuration");

    cout << "\nInitial commit: "
         << ObjectHasher::shortId(initialCommit)
         << "\n";

    // Step 2: Make a focused production-related change.
    repository.writeFile(
        "config/app.conf",
        "service=payments\n"
        "port=8080\n"
        "environment=production\n"
    );

    repository.stage("config/app.conf");

    const string productionCommit =
        repository.commit("Set production environment");

    cout << "Production commit: "
         << ObjectHasher::shortId(productionCommit)
         << "\n";

    // Step 3: Create an isolated feature branch.
    repository.createBranch("feature/security-settings");

    // Step 4: Continue main development.
    repository.writeFile(
        "config/app.conf",
        "service=payments\n"
        "port=8443\n"
        "environment=production\n"
    );

    repository.stage("config/app.conf");

    const string mainCommit =
        repository.commit("Enable secure service port");

    cout << "Main branch commit: "
         << ObjectHasher::shortId(mainCommit)
         << "\n";

    // Step 5: Work independently on the feature branch.
    repository.checkout("feature/security-settings");

    repository.writeFile(
        "config/security.conf",
        "tls=enabled\n"
        "minimum_protocol=TLS1.2\n"
    );

    repository.stage("config/security.conf");

    const string featureCommit =
        repository.commit("Add security configuration");

    cout << "Feature commit: "
         << ObjectHasher::shortId(featureCommit)
         << "\n";

    // Step 6: Inspect history.
    cout << "\nFeature history:\n";

    for (const auto& [commitId, message] : repository.log()) {
        cout << "  "
             << ObjectHasher::shortId(commitId)
             << " "
             << message
             << "\n";
    }

    // Step 7: Identify the merge base.
    const string base =
        repository.mergeBase(mainCommit, featureCommit);

    cout << "\nMerge base: "
         << ObjectHasher::shortId(base)
         << "\n";

    // Step 8: Perform a three-way merge analysis.
    const auto baseSnapshot =
        repository.snapshotFromCommit(base);

    const auto mainSnapshot =
        repository.snapshotFromCommit(mainCommit);

    const auto featureSnapshot =
        repository.snapshotFromCommit(featureCommit);

    const auto mergeResult =
        repository.threeWayMerge(
            baseSnapshot,
            mainSnapshot,
            featureSnapshot
        );

    cout << "Merge conflicts: "
         << mergeResult.conflicts.size()
         << "\n";

    for (const string& conflict : mergeResult.conflicts) {
        cout << "  conflict: " << conflict << "\n";
    }

    if (mergeResult.conflicts.empty()) {
        cout << "The snapshots can be combined automatically.\n";

        cout << "Merged files:\n";

        for (const auto& [path, content] : mergeResult.merged) {
            cout << "  " << path
                 << " (" << content.size()
                 << " bytes)\n";
        }
    }

    // Step 9: Inspect repository integrity.
    const auto integrityProblems =
        repository.verifyIntegrity();

    cout << "\nIntegrity problems: "
         << integrityProblems.size()
         << "\n";

    for (const string& problem : integrityProblems) {
        cout << "  " << problem << "\n";
    }

    repository.printRepositoryStatistics();
}

// ---------------------------------------------------------------------------
// 5. Conflict case
// ---------------------------------------------------------------------------

void demonstrateConflictCase() {
    cout << "\n" << string(72, '=') << "\n";
    cout << "CONFLICT CASE\n";
    cout << string(72, '=') << "\n";

    Repository repository("Developer <developer@example.com>");
    repository.init("main");

    repository.writeFile(
        "settings.txt",
        "timeout=30\n"
        "mode=normal\n"
    );

    repository.stageAll();
    const string base = repository.commit("Create settings");

    repository.createBranch("feature");

    repository.writeFile(
        "settings.txt",
        "timeout=60\n"
        "mode=normal\n"
    );

    repository.stage("settings.txt");
    const string mainCommit =
        repository.commit("Increase timeout");

    repository.checkout("feature");

    repository.writeFile(
        "settings.txt",
        "timeout=15\n"
        "mode=normal\n"
    );

    repository.stage("settings.txt");
    const string featureCommit =
        repository.commit("Reduce timeout");

    const auto result = repository.threeWayMerge(
        repository.snapshotFromCommit(base),
        repository.snapshotFromCommit(mainCommit),
        repository.snapshotFromCommit(featureCommit)
    );

    cout << "Common ancestor: "
         << ObjectHasher::shortId(
                repository.mergeBase(mainCommit, featureCommit)
            )
         << "\n";

    cout << "Conflict count: "
         << result.conflicts.size()
         << "\n";

    for (const string& path : result.conflicts) {
        cout << "Conflict requires manual resolution: "
             << path << "\n";
    }
}

// ---------------------------------------------------------------------------
// 6. Error handling and edge cases
// ---------------------------------------------------------------------------

void demonstrateFailureConditions() {
    cout << "\n" << string(72, '=') << "\n";
    cout << "VALIDATION AND FAILURE CONDITIONS\n";
    cout << string(72, '=') << "\n";

    Repository repository("Developer <developer@example.com>");
    repository.init();

    try {
        repository.commit("Empty commit");
    } catch (const exception& error) {
        cout << "Expected commit error: "
             << error.what()
             << "\n";
    }

    try {
        repository.checkout("0000000000000000");
    } catch (const exception& error) {
        cout << "Expected checkout error: "
             << error.what()
             << "\n";
    }

    try {
        repository.createBranch("invalid..branch");
    } catch (const exception& error) {
        cout << "Expected branch error: "
             << error.what()
             << "\n";
    }

    try {
        repository.writeFile("../outside.txt", "unsafe");
    } catch (const exception& error) {
        cout << "Expected path error: "
             << error.what()
             << "\n";
    }
}

// ---------------------------------------------------------------------------
// 7. Tests
// ---------------------------------------------------------------------------

void runTests() {
    cout << "\n" << string(72, '=') << "\n";
    cout << "SELF-TESTS\n";
    cout << string(72, '=') << "\n";

    Repository repository("Test <test@example.com>");
    repository.init();

    repository.writeFile("test.txt", "hello\n");
    repository.stage("test.txt");

    const string first =
        repository.commit("Initial test");

    assert(repository.head() == first);
    assert(
        repository.snapshotFromCommit(first).at("test.txt")
        == "hello\n"
    );

    repository.writeFile("test.txt", "changed\n");

    repository.stage("test.txt");

    const string second =
        repository.commit("Change test");

    assert(repository.commitsForTesting(second).size() == 2);
    assert(repository.verifyIntegrity().empty());

    repository.createBranch("feature");
    repository.checkout("feature");

    assert(repository.currentBranchForTesting() == "feature");

    repository.checkout(second);

    assert(repository.currentBranchForTesting().empty());

    cout << "All assertions passed.\n";
}

// ---------------------------------------------------------------------------
// 8. Public testing helpers
// ---------------------------------------------------------------------------
//
// These small accessors keep the actual repository data encapsulated while
// allowing the educational self-tests to inspect important relationships.

int main() {
    try {
        demonstrateProductionConfigurationRepository();
        demonstrateConflictCase();
        demonstrateFailureConditions();

        cout << "\n" << string(72, '=') << "\n";
        cout << "CASE STUDY COMPLETE\n";
        cout << string(72, '=') << "\n";

        /*
         * A separate test block is shown below using the same public API.
         * The repository implementation intentionally exposes enough behavior
         * for realistic validation without making its object store public.
         */

        Repository testRepository("Test <test@example.com>");
        testRepository.init();

        testRepository.writeFile("test.txt", "hello\n");
        testRepository.stage("test.txt");

        const string first =
            testRepository.commit("Initial test");

        assert(testRepository.head() == first);
        assert(
            testRepository.snapshotFromCommit(first).at("test.txt")
            == "hello\n"
        );

        testRepository.writeFile("test.txt", "changed\n");

        assert(
            testRepository.snapshotFromCommit(first).at("test.txt")
            == "hello\n"
        );

        testRepository.stage("test.txt");
        const string second =
            testRepository.commit("Change test");

        assert(
            testRepository.getCommitForTesting(second).parents.size() == 1
        );

        testRepository.createBranch("feature");
        testRepository.checkout("feature");

        assert(
            testRepository.currentBranchForTesting() == "feature"
        );

        testRepository.checkout(second);

        assert(
            testRepository.currentBranchForTesting().empty()
        );

        assert(testRepository.verifyIntegrity().empty());

        cout << "\nAll self-tests passed.\n";
    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
