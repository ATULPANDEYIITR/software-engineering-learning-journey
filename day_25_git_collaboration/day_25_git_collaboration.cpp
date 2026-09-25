/*
 * Git Collaboration: Pull Requests, Code Review, and Git Workflows
 * =================================================================
 *
 * C++17 case study:
 * A realistic repository-management simulator for a software team.
 *
 * Scenario:
 *   A developer implements a user-profile feature.
 *   The developer creates a branch and commits changes.
 *   A pull request is opened.
 *   Automated checks run.
 *   Reviewers approve the change.
 *   Branch-protection rules are evaluated.
 *   The pull request is merged.
 *
 * The program also demonstrates:
 *   - Commit graphs
 *   - Branch references
 *   - Fast-forward and three-way merges
 *   - Conflict detection
 *   - Pull-request policies
 *   - Code-review states
 *   - CI checks
 *   - Audit logs
 *   - Security rules
 *   - Change-size analysis
 *   - Complexity considerations
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic git_collaboration.cpp -o git_collaboration
 *
 * Run:
 *   ./git_collaboration
 */

#include <algorithm>
#include <chrono>
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
// 1. ENUMERATIONS
// ============================================================================

enum class ReviewState {
    Commented,
    Approved,
    ChangesRequested
};

enum class PullRequestState {
    Open,
    Merged,
    Closed
};

enum class CheckState {
    Pass,
    Fail,
    Pending
};


// ============================================================================
// 2. HELPER FUNCTIONS
// ============================================================================

std::string toString(ReviewState state) {
    switch (state) {
        case ReviewState::Commented:
            return "commented";
        case ReviewState::Approved:
            return "approved";
        case ReviewState::ChangesRequested:
            return "changes_requested";
    }

    return "unknown";
}


std::string toString(PullRequestState state) {
    switch (state) {
        case PullRequestState::Open:
            return "open";
        case PullRequestState::Merged:
            return "merged";
        case PullRequestState::Closed:
            return "closed";
    }

    return "unknown";
}


std::string toString(CheckState state) {
    switch (state) {
        case CheckState::Pass:
            return "pass";
        case CheckState::Fail:
            return "fail";
        case CheckState::Pending:
            return "pending";
    }

    return "unknown";
}


// ============================================================================
// 3. COMMIT
// ============================================================================

struct Commit {
    std::string id;
    std::string author;
    std::string message;

    /*
     * A normal commit has one parent.
     * An initial commit has zero parents.
     * A merge commit has two or more parents.
     */
    std::vector<std::string> parents;

    /*
     * A simplified file snapshot.
     *
     * Real Git stores trees and blobs rather than duplicating complete
     * snapshots in each commit. The map makes this educational model easy
     * to inspect.
     */
    std::map<std::string, std::string> files;
};


// ============================================================================
// 4. BRANCH
// ============================================================================

struct Branch {
    std::string name;
    std::optional<std::string> head;
};


// ============================================================================
// 5. REVIEW
// ============================================================================

struct Review {
    std::string reviewer;
    ReviewState state;
    std::vector<std::string> comments;
};


// ============================================================================
// 6. PULL REQUEST
// ============================================================================

struct PullRequest {
    int number;
    std::string title;
    std::string author;
    std::string sourceBranch;
    std::string targetBranch;
    std::string description;

    PullRequestState state = PullRequestState::Open;

    std::vector<Review> reviews;
    std::map<std::string, CheckState> checks;

    int approvalCount() const {
        int count = 0;

        for (const auto& review : reviews) {
            if (review.state == ReviewState::Approved) {
                ++count;
            }
        }

        return count;
    }

    bool hasRequestedChanges() const {
        return std::any_of(
            reviews.begin(),
            reviews.end(),
            [](const Review& review) {
                return review.state == ReviewState::ChangesRequested;
            }
        );
    }
};


// ============================================================================
// 7. AUDIT EVENT
// ============================================================================

struct AuditEvent {
    std::string timestamp;
    std::string actor;
    std::string action;
    std::string objectId;
    std::string details;
};


// ============================================================================
// 8. AUDIT LOG
// ============================================================================

class AuditLog {
private:
    std::vector<AuditEvent> events;

public:
    void record(
        const std::string& actor,
        const std::string& action,
        const std::string& objectId,
        const std::string& details
    ) {
        const auto now =
            std::chrono::system_clock::now();

        const std::time_t timeValue =
            std::chrono::system_clock::to_time_t(now);

        std::ostringstream timestamp;
        timestamp << std::put_time(
            std::localtime(&timeValue),
            "%Y-%m-%d %H:%M:%S"
        );

        events.push_back({
            timestamp.str(),
            actor,
            action,
            objectId,
            details
        });
    }

    void print() const {
        for (const auto& event : events) {
            std::cout
                << event.timestamp
                << " | "
                << event.actor
                << " | "
                << event.action
                << " | "
                << event.objectId
                << " | "
                << event.details
                << '\n';
        }
    }

    std::size_t size() const {
        return events.size();
    }
};


// ============================================================================
// 9. EDUCATIONAL GIT REPOSITORY
// ============================================================================

class Repository {
private:
    std::map<std::string, Commit> commits;
    std::map<std::string, Branch> branches;

    std::string currentBranch = "main";
    int nextCommitNumber = 1;

    std::string generateCommitId() {
        std::ostringstream id;
        id << 'C'
           << std::setw(4)
           << std::setfill('0')
           << nextCommitNumber++;

        return id.str();
    }

public:
    Repository() {
        branches.emplace(
            "main",
            Branch{"main", std::nullopt}
        );
    }

    const std::string& getCurrentBranch() const {
        return currentBranch;
    }

    std::optional<std::string> getHead() const {
        const auto iterator = branches.find(currentBranch);

        if (iterator == branches.end()) {
            throw std::runtime_error(
                "Current branch does not exist."
            );
        }

        return iterator->second.head;
    }

    bool branchExists(const std::string& name) const {
        return branches.find(name) != branches.end();
    }

    const Commit& getCommit(const std::string& id) const {
        const auto iterator = commits.find(id);

        if (iterator == commits.end()) {
            throw std::runtime_error(
                "Unknown commit: " + id
            );
        }

        return iterator->second;
    }

    std::map<std::string, std::string> snapshot(
        const std::optional<std::string>& commitId
    ) const {
        if (!commitId.has_value()) {
            return {};
        }

        return getCommit(*commitId).files;
    }

    std::string commit(
        const std::string& author,
        const std::string& message,
        const std::map<std::string, std::optional<std::string>>& changes
    ) {
        const auto parent = getHead();

        auto files = snapshot(parent);

        for (const auto& [path, content] : changes) {
            if (content.has_value()) {
                files[path] = *content;
            } else {
                files.erase(path);
            }
        }

        const std::string id = generateCommitId();

        Commit newCommit{
            id,
            author,
            message,
            {},
            files
        };

        if (parent.has_value()) {
            newCommit.parents.push_back(*parent);
        }

        commits.emplace(id, std::move(newCommit));

        branches.at(currentBranch).head = id;

        return id;
    }

    void createBranch(
        const std::string& name,
        std::optional<std::string> fromCommit = std::nullopt
    ) {
        if (branchExists(name)) {
            throw std::runtime_error(
                "Branch already exists: " + name
            );
        }

        if (!fromCommit.has_value()) {
            fromCommit = getHead();
        }

        if (fromCommit.has_value()) {
            /*
             * Accessing getCommit validates that the supplied commit exists.
             */
            static_cast<void>(getCommit(*fromCommit));
        }

        branches.emplace(
            name,
            Branch{name, fromCommit}
        );
    }

    void checkout(const std::string& name) {
        if (!branchExists(name)) {
            throw std::runtime_error(
                "Unknown branch: " + name
            );
        }

        currentBranch = name;
    }

    std::set<std::string> ancestors(
        const std::optional<std::string>& commitId
    ) const {
        std::set<std::string> result;

        if (!commitId.has_value()) {
            return result;
        }

        std::vector<std::string> stack;
        stack.push_back(*commitId);

        while (!stack.empty()) {
            const std::string current = stack.back();
            stack.pop_back();

            if (result.count(current) > 0) {
                continue;
            }

            result.insert(current);

            const auto& commitObject = getCommit(current);

            for (const auto& parent : commitObject.parents) {
                stack.push_back(parent);
            }
        }

        return result;
    }

    bool isAncestor(
        const std::optional<std::string>& older,
        const std::optional<std::string>& newer
    ) const {
        if (!older.has_value()) {
            return true;
        }

        const auto reachable = ancestors(newer);

        return reachable.count(*older) > 0;
    }

    std::optional<std::string> findMergeBase(
        const std::optional<std::string>& first,
        const std::optional<std::string>& second
    ) const {
        if (!first.has_value() || !second.has_value()) {
            return std::nullopt;
        }

        const auto firstAncestors = ancestors(first);
        const auto secondAncestors = ancestors(second);

        std::vector<std::string> common;

        std::set_intersection(
            firstAncestors.begin(),
            firstAncestors.end(),
            secondAncestors.begin(),
            secondAncestors.end(),
            std::back_inserter(common)
        );

        if (common.empty()) {
            return std::nullopt;
        }

        /*
         * This educational model uses commit ID order as a simple proxy
         * for recency. Real Git merge-base selection follows graph topology.
         */
        return *std::max_element(
            common.begin(),
            common.end()
        );
    }

    static std::map<std::string, std::string> threeWayMerge(
        const std::map<std::string, std::string>& base,
        const std::map<std::string, std::string>& target,
        const std::map<std::string, std::string>& source
    ) {
        std::set<std::string> paths;

        for (const auto& [path, value] : base) {
            static_cast<void>(value);
            paths.insert(path);
        }

        for (const auto& [path, value] : target) {
            static_cast<void>(value);
            paths.insert(path);
        }

        for (const auto& [path, value] : source) {
            static_cast<void>(value);
            paths.insert(path);
        }

        std::map<std::string, std::string> result;

        for (const auto& path : paths) {
            const auto baseIterator = base.find(path);
            const auto targetIterator = target.find(path);
            const auto sourceIterator = source.find(path);

            const std::optional<std::string> baseValue =
                baseIterator == base.end()
                    ? std::nullopt
                    : std::optional<std::string>(baseIterator->second);

            const std::optional<std::string> targetValue =
                targetIterator == target.end()
                    ? std::nullopt
                    : std::optional<std::string>(targetIterator->second);

            const std::optional<std::string> sourceValue =
                sourceIterator == source.end()
                    ? std::nullopt
                    : std::optional<std::string>(sourceIterator->second);

            const bool targetChanged =
                targetValue != baseValue;

            const bool sourceChanged =
                sourceValue != baseValue;

            if (
                targetChanged &&
                sourceChanged &&
                targetValue != sourceValue
            ) {
                throw std::runtime_error(
                    "Merge conflict in file: " + path
                );
            }

            const auto selected =
                sourceChanged
                    ? sourceValue
                    : targetValue;

            if (selected.has_value()) {
                result[path] = *selected;
            }
        }

        return result;
    }

    std::string merge(
        const std::string& sourceBranch,
        const std::string& message
    ) {
        if (!branchExists(sourceBranch)) {
            throw std::runtime_error(
                "Unknown source branch: " + sourceBranch
            );
        }

        const auto target = getHead();
        const auto source =
            branches.at(sourceBranch).head;

        if (!source.has_value()) {
            throw std::runtime_error(
                "Cannot merge an empty branch."
            );
        }

        if (target == source) {
            return *source;
        }

        if (isAncestor(target, source)) {
            branches.at(currentBranch).head = source;
            return *source;
        }

        if (isAncestor(source, target)) {
            return *target;
        }

        const auto base = findMergeBase(
            target,
            source
        );

        const auto baseSnapshot = snapshot(base);
        const auto targetSnapshot = snapshot(target);
        const auto sourceSnapshot = snapshot(source);

        const auto mergedFiles = threeWayMerge(
            baseSnapshot,
            targetSnapshot,
            sourceSnapshot
        );

        const std::string mergeId =
            generateCommitId();

        Commit mergeCommit{
            mergeId,
            "merge-bot",
            message,
            {},
            mergedFiles
        };

        if (target.has_value()) {
            mergeCommit.parents.push_back(*target);
        }

        mergeCommit.parents.push_back(*source);

        commits.emplace(
            mergeId,
            std::move(mergeCommit)
        );

        branches.at(currentBranch).head = mergeId;

        return mergeId;
    }

    void printLog(const std::string& branchName) const {
        const auto iterator = branches.find(branchName);

        if (iterator == branches.end()) {
            throw std::runtime_error(
                "Unknown branch: " + branchName
            );
        }

        if (!iterator->second.head.has_value()) {
            std::cout
                << "Branch " << branchName
                << " has no commits.\n";
            return;
        }

        const auto reachable =
            ancestors(iterator->second.head);

        for (auto reverse = reachable.rbegin();
             reverse != reachable.rend();
             ++reverse) {
            const auto& commitObject =
                getCommit(*reverse);

            std::cout
                << commitObject.id
                << " | "
                << commitObject.author
                << " | "
                << commitObject.message
                << '\n';
        }
    }
};


// ============================================================================
// 10. BRANCH PROTECTION
// ============================================================================

struct BranchProtection {
    bool requirePullRequest = true;
    int requiredApprovals = 1;
    bool requirePassingChecks = true;
    bool allowForcePush = false;
    bool allowDeletion = false;
};


// ============================================================================
// 11. PULL REQUEST SERVICE
// ============================================================================

class PullRequestService {
private:
    Repository& repository;
    BranchProtection policy;

    int nextNumber = 1;
    std::map<int, PullRequest> pullRequests;

public:
    PullRequestService(
        Repository& repositoryReference,
        BranchProtection policyReference
    )
        : repository(repositoryReference),
          policy(std::move(policyReference)) {}

    PullRequest& open(
        const std::string& title,
        const std::string& author,
        const std::string& sourceBranch,
        const std::string& targetBranch,
        const std::string& description
    ) {
        if (!repository.branchExists(sourceBranch)) {
            throw std::runtime_error(
                "Source branch does not exist."
            );
        }

        if (!repository.branchExists(targetBranch)) {
            throw std::runtime_error(
                "Target branch does not exist."
            );
        }

        if (sourceBranch == targetBranch) {
            throw std::runtime_error(
                "Source and target branches must differ."
            );
        }

        PullRequest pullRequest{
            nextNumber++,
            title,
            author,
            sourceBranch,
            targetBranch,
            description
        };

        const int number = pullRequest.number;

        auto [iterator, inserted] =
            pullRequests.emplace(
                number,
                std::move(pullRequest)
            );

        if (!inserted) {
            throw std::runtime_error(
                "Failed to create pull request."
            );
        }

        return iterator->second;
    }

    PullRequest& getOpen(int number) {
        const auto iterator =
            pullRequests.find(number);

        if (iterator == pullRequests.end()) {
            throw std::runtime_error(
                "Unknown pull request."
            );
        }

        if (
            iterator->second.state !=
            PullRequestState::Open
        ) {
            throw std::runtime_error(
                "Pull request is no longer open."
            );
        }

        return iterator->second;
    }

    void review(
        int number,
        const std::string& reviewer,
        ReviewState state,
        const std::vector<std::string>& comments
    ) {
        auto& pullRequest = getOpen(number);

        if (reviewer == pullRequest.author) {
            throw std::runtime_error(
                "Self-approval is disabled."
            );
        }

        pullRequest.reviews.push_back({
            reviewer,
            state,
            comments
        });
    }

    void setCheck(
        int number,
        const std::string& name,
        CheckState state
    ) {
        auto& pullRequest = getOpen(number);

        pullRequest.checks[name] = state;
    }

    std::string merge(int number) {
        auto& pullRequest = getOpen(number);

        if (pullRequest.hasRequestedChanges()) {
            throw std::runtime_error(
                "Changes have been requested."
            );
        }

        if (
            pullRequest.approvalCount() <
            policy.requiredApprovals
        ) {
            throw std::runtime_error(
                "Required approvals are missing."
            );
        }

        if (policy.requirePassingChecks) {
            for (const auto& [name, state] :
                 pullRequest.checks) {
                if (state != CheckState::Pass) {
                    throw std::runtime_error(
                        "Check is not passing: " + name
                    );
                }
            }
        }

        repository.checkout(
            pullRequest.targetBranch
        );

        const std::string mergeCommit =
            repository.merge(
                pullRequest.sourceBranch,
                "Merge PR #" +
                    std::to_string(number) +
                    ": " +
                    pullRequest.title
            );

        pullRequest.state =
            PullRequestState::Merged;

        return mergeCommit;
    }
};


// ============================================================================
// 12. CHANGE REVIEW ANALYSIS
// ============================================================================

struct Change {
    std::string path;
    std::string before;
    std::string after;
};


std::vector<std::string> analyzeChange(
    const Change& change
) {
    std::vector<std::string> findings;

    if (change.after.empty()) {
        findings.push_back(
            "ERROR: resulting file is empty."
        );
    }

    if (
        change.after.find("TODO: SECURITY") !=
        std::string::npos
    ) {
        findings.push_back(
            "SECURITY: unresolved security marker."
        );
    }

    if (
        change.after.find("password =") !=
            std::string::npos &&
        change.after.find("hashPassword") ==
            std::string::npos
    ) {
        findings.push_back(
            "SECURITY: password handling requires review."
        );
    }

    const auto beforeLines =
        static_cast<int>(
            std::count(
                change.before.begin(),
                change.before.end(),
                '\n'
            )
        ) + 1;

    const auto afterLines =
        static_cast<int>(
            std::count(
                change.after.begin(),
                change.after.end(),
                '\n'
            )
        ) + 1;

    if (
        std::abs(afterLines - beforeLines) >
        200
    ) {
        findings.push_back(
            "REVIEW: unusually large change."
        );
    }

    return findings;
}


// ============================================================================
// 13. SECURITY POLICY
// ============================================================================

class SecurityPolicy {
public:
    static std::vector<std::string> rules() {
        return {
            "Never commit passwords, API keys, private keys, or production secrets.",
            "Use least privilege for repository identities and automation tokens.",
            "Treat external pull-request code as untrusted.",
            "Do not expose privileged CI secrets to untrusted code.",
            "Review dependency changes for supply-chain risk.",
            "Removing a secret from the latest commit does not remove it from history.",
            "Restrict force pushes on protected shared branches."
        };
    }

    static void print() {
        for (const auto& rule : rules()) {
            std::cout << "- " << rule << '\n';
        }
    }
};


// ============================================================================
// 14. COMPLETE DEVELOPMENT SCENARIO
// ============================================================================

class CollaborationSystem {
private:
    Repository repository;
    PullRequestService pullRequests;
    AuditLog audit;

public:
    CollaborationSystem()
        : repository(),
          pullRequests(
              repository,
              BranchProtection{
                  true,
                  2,
                  true,
                  false,
                  false
              }
          ) {}

    void initialize() {
        repository.commit(
            "maintainer",
            "Initialize application",
            {
                {
                    "README.md",
                    std::string("# Profile Service\n")
                },
                {
                    "app.cpp",
                    std::string(
                        "int main() { return 0; }\n"
                    )
                }
            }
        );

        audit.record(
            "maintainer",
            "commit",
            "main",
            "Initialized repository."
        );
    }

    PullRequest& developFeature() {
        repository.createBranch(
            "feature/profile"
        );

        repository.checkout(
            "feature/profile"
        );

        const std::string firstCommit =
            repository.commit(
                "developer",
                "Add profile model",
                {
                    {
                        "profile.cpp",
                        std::string(
                            "#include <string>\n\n"
                            "class Profile {\n"
                            "public:\n"
                            "    explicit Profile(std::string username)\n"
                            "        : username_(std::move(username)) {}\n"
                            "\n"
                            "private:\n"
                            "    std::string username_;\n"
                            "};\n"
                        )
                    }
                }
            );

        audit.record(
            "developer",
            "commit",
            firstCommit,
            "Added profile model."
        );

        const std::string secondCommit =
            repository.commit(
                "developer",
                "Add profile validation",
                {
                    {
                        "profile.cpp",
                        std::string(
                            "#include <stdexcept>\n"
                            "#include <string>\n"
                            "\n"
                            "class Profile {\n"
                            "public:\n"
                            "    explicit Profile(std::string username) {\n"
                            "        if (username.empty()) {\n"
                            "            throw std::invalid_argument(\n"
                            "                \"username is required\"\n"
                            "            );\n"
                            "        }\n"
                            "\n"
                            "        username_ = std::move(username);\n"
                            "    }\n"
                            "\n"
                            "private:\n"
                            "    std::string username_;\n"
                            "};\n"
                        )
                    }
                }
            );

        audit.record(
            "developer",
            "commit",
            secondCommit,
            "Added username validation."
        );

        auto& pullRequest =
            pullRequests.open(
                "Add user profile validation",
                "developer",
                "feature/profile",
                "main",
                "Adds a profile model and username validation."
            );

        audit.record(
            "developer",
            "open",
            "PR-" + std::to_string(
                pullRequest.number
            ),
            "Submitted feature for review."
        );

        return pullRequest;
    }

    void reviewAndMerge(PullRequest& pullRequest) {
        pullRequests.review(
            pullRequest.number,
            "reviewer-a",
            ReviewState::Approved,
            {
                "Validation is explicit."
            }
        );

        pullRequests.review(
            pullRequest.number,
            "reviewer-b",
            ReviewState::Approved,
            {
                "Change is focused."
            }
        );

        pullRequests.setCheck(
            pullRequest.number,
            "unit-tests",
            CheckState::Pass
        );

        pullRequests.setCheck(
            pullRequest.number,
            "lint",
            CheckState::Pass
        );

        pullRequests.setCheck(
            pullRequest.number,
            "security",
            CheckState::Pass
        );

        audit.record(
            "reviewer-a",
            "approve",
            "PR-" + std::to_string(
                pullRequest.number
            ),
            "Approved."
        );

        audit.record(
            "reviewer-b",
            "approve",
            "PR-" + std::to_string(
                pullRequest.number
            ),
            "Approved."
        );

        const std::string mergeCommit =
            pullRequests.merge(
                pullRequest.number
            );

        audit.record(
            "maintainer",
            "merge",
            "PR-" + std::to_string(
                pullRequest.number
            ),
            mergeCommit
        );

        std::cout
            << "Merged PR #"
            << pullRequest.number
            << " as "
            << mergeCommit
            << ".\n";
    }

    void printResults() const {
        std::cout
            << "\nFinal main branch history:\n";

        repository.printLog("main");

        std::cout
            << "\nAudit trail:\n";

        audit.print();
    }
};


// ============================================================================
// 15. CONFLICT CASE STUDY
// ============================================================================

void demonstrateConflict() {
    std::cout
        << "\n=== CONFLICT CASE STUDY ===\n";

    Repository repository;

    repository.commit(
        "Alice",
        "Initial configuration",
        {
            {
                "config.txt",
                std::string("timeout=30\n")
            }
        }
    );

    repository.createBranch(
        "feature-timeout"
    );

    repository.checkout(
        "feature-timeout"
    );

    repository.commit(
        "Bob",
        "Feature timeout",
        {
            {
                "config.txt",
                std::string("timeout=60\n")
            }
        }
    );

    repository.checkout("main");

    repository.commit(
        "Alice",
        "Production timeout",
        {
            {
                "config.txt",
                std::string("timeout=90\n")
            }
        }
    );

    try {
        repository.merge(
            "feature-timeout",
            "Merge feature timeout"
        );

        std::cout
            << "Unexpectedly merged without conflict.\n";
    } catch (const std::exception& error) {
        std::cout
            << "Expected conflict: "
            << error.what()
            << '\n';
    }
}


// ============================================================================
// 16. WORKFLOW TABLE
// ============================================================================

struct Workflow {
    std::string name;
    std::string branchModel;
    std::string releaseModel;
    std::string typicalUse;
};


std::vector<Workflow> workflowCatalog() {
    return {
        {
            "Feature Branch",
            "main plus short-lived feature branches",
            "Merge reviewed features into main",
            "General collaborative development"
        },
        {
            "GitHub Flow",
            "main plus short-lived branches",
            "Deploy from main after review",
            "Continuous delivery"
        },
        {
            "GitLab Flow",
            "feature branches plus environment conventions",
            "Promote changes through environments",
            "Environment-oriented delivery"
        },
        {
            "Trunk-Based Development",
            "trunk with very short-lived branches",
            "Frequent integration",
            "High integration frequency"
        },
        {
            "Git Flow",
            "main, develop, feature, release, hotfix",
            "Structured release branches",
            "Formal release cycles"
        }
    };
}


void printWorkflows() {
    std::cout
        << "\n=== WORKFLOW MODELS ===\n";

    for (const auto& workflow : workflowCatalog()) {
        std::cout
            << "\n"
            << workflow.name
            << "\n  Branch model: "
            << workflow.branchModel
            << "\n  Release model: "
            << workflow.releaseModel
            << "\n  Typical use: "
            << workflow.typicalUse
            << '\n';
    }
}


// ============================================================================
// 17. TESTS
// ============================================================================

void testFastForward() {
    Repository repository;

    repository.commit(
        "Alice",
        "Initial",
        {
            {"a.txt", std::string("A")}
        }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    const auto featureCommit =
        repository.commit(
            "Bob",
            "Feature",
            {
                {"b.txt", std::string("B")}
            }
        );

    repository.checkout("main");

    const auto result =
        repository.merge(
            "feature",
            "Merge feature"
        );

    if (result != featureCommit) {
        throw std::runtime_error(
            "Fast-forward test failed."
        );
    }
}


void testConflict() {
    Repository repository;

    repository.commit(
        "Alice",
        "Initial",
        {
            {"config", std::string("A")}
        }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    repository.commit(
        "Bob",
        "Feature",
        {
            {"config", std::string("B")}
        }
    );

    repository.checkout("main");

    repository.commit(
        "Alice",
        "Main",
        {
            {"config", std::string("C")}
        }
    );

    bool conflictDetected = false;

    try {
        repository.merge(
            "feature",
            "Merge feature"
        );
    } catch (const std::exception&) {
        conflictDetected = true;
    }

    if (!conflictDetected) {
        throw std::runtime_error(
            "Conflict test failed."
        );
    }
}


void testPullRequestPolicy() {
    Repository repository;

    repository.commit(
        "maintainer",
        "Initial",
        {
            {"app", std::string("v1")}
        }
    );

    repository.createBranch("feature");
    repository.checkout("feature");

    repository.commit(
        "developer",
        "Feature",
        {
            {"app", std::string("v2")}
        }
    );

    PullRequestService service(
        repository,
        BranchProtection{
            true,
            1,
            true,
            false,
            false
        }
    );

    auto& pullRequest =
        service.open(
            "Feature",
            "developer",
            "feature",
            "main",
            "Test feature."
        );

    bool rejected = false;

    try {
        service.merge(pullRequest.number);
    } catch (const std::exception&) {
        rejected = true;
    }

    if (!rejected) {
        throw std::runtime_error(
            "Pull-request policy test failed."
        );
    }

    service.review(
        pullRequest.number,
        "reviewer",
        ReviewState::Approved,
        {}
    );

    service.setCheck(
        pullRequest.number,
        "tests",
        CheckState::Pass
    );

    service.merge(
        pullRequest.number
    );

    if (
        pullRequest.state !=
        PullRequestState::Merged
    ) {
        throw std::runtime_error(
            "Pull-request merge test failed."
        );
    }
}


void runTests() {
    std::cout
        << "\n=== TEST SUITE ===\n";

    struct TestCase {
        std::string name;
        void (*function)();
    };

    const std::vector<TestCase> tests = {
        {"Fast-forward merge", testFastForward},
        {"Merge conflict", testConflict},
        {"Pull-request policy", testPullRequestPolicy}
    };

    int passed = 0;

    for (const auto& test : tests) {
        try {
            test.function();

            ++passed;

            std::cout
                << "PASS: "
                << test.name
                << '\n';
        } catch (const std::exception& error) {
            std::cout
                << "FAIL: "
                << test.name
                << " -> "
                << error.what()
                << '\n';
        }
    }

    std::cout
        << passed
        << "/"
        << tests.size()
        << " tests passed.\n";

    if (passed != static_cast<int>(tests.size())) {
        throw std::runtime_error(
            "One or more tests failed."
        );
    }
}


// ============================================================================
// 18. MAIN
// ============================================================================

int main() {
    try {
        std::cout
            << "============================================================\n"
            << "GIT COLLABORATION CASE STUDY\n"
            << "Pull Requests, Code Review, and Git Workflows\n"
            << "============================================================\n";

        std::cout
            << "\n=== COMPLETE COLLABORATION SCENARIO ===\n";

        CollaborationSystem system;

        system.initialize();

        auto& pullRequest =
            system.developFeature();

        std::cout
            << "Opened PR #"
            << pullRequest.number
            << ": "
            << pullRequest.title
            << '\n';

        system.reviewAndMerge(
            pullRequest
        );

        system.printResults();

        demonstrateConflict();

        printWorkflows();

        std::cout
            << "\n=== SECURITY POLICY ===\n";

        SecurityPolicy::print();

        std::cout
            << "\n=== REPOSITORY DESIGN NOTES ===\n"
            << "Commit lookup uses ordered maps for deterministic output.\n"
            << "Ancestor traversal uses a stack and visits each reachable "
               "commit at most once.\n"
            << "Three-way merging examines each affected path once after "
               "the snapshots have been constructed.\n"
            << "For V reachable commits and F paths, the educational merge "
               "is approximately O(V + F log F) because ordered maps/sets "
               "are used.\n"
            << "Production Git uses highly optimized object storage, "
               "indexing, compression, hashing, and graph algorithms.\n";

        runTests();

        std::cout
            << "\nProgram completed successfully.\n";

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }
}
