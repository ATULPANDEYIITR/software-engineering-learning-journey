#include <algorithm>
#include <chrono>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

enum class StageStatus {
    PENDING,
    RUNNING,
    PASSED,
    FAILED,
    SKIPPED
};

enum class PipelineStatus {
    CREATED,
    RUNNING,
    FAILED,
    SUCCEEDED,
    RELEASED
};

enum class Environment {
    DEVELOPMENT,
    STAGING,
    PRODUCTION
};

enum class ReviewDecision {
    APPROVED,
    REJECTED,
    COMMENTED,
    DISMISSED
};

enum class MergeStrategy {
    MERGE_COMMIT,
    SQUASH,
    REBASE
};

string toString(StageStatus status) {
    switch (status) {
        case StageStatus::PENDING: return "PENDING";
        case StageStatus::RUNNING: return "RUNNING";
        case StageStatus::PASSED: return "PASSED";
        case StageStatus::FAILED: return "FAILED";
        case StageStatus::SKIPPED: return "SKIPPED";
    }
    return "UNKNOWN";
}

string toString(PipelineStatus status) {
    switch (status) {
        case PipelineStatus::CREATED: return "CREATED";
        case PipelineStatus::RUNNING: return "RUNNING";
        case PipelineStatus::FAILED: return "FAILED";
        case PipelineStatus::SUCCEEDED: return "SUCCEEDED";
        case PipelineStatus::RELEASED: return "RELEASED";
    }
    return "UNKNOWN";
}

string toString(Environment environment) {
    switch (environment) {
        case Environment::DEVELOPMENT: return "DEVELOPMENT";
        case Environment::STAGING: return "STAGING";
        case Environment::PRODUCTION: return "PRODUCTION";
    }
    return "UNKNOWN";
}

struct Commit {
    string hash;
    string message;
    string author;
};

struct Branch {
    string name;
    string headCommit;
    bool protectedBranch = false;
    bool allowDirectPush = true;
    bool allowForcePush = false;
    bool allowDeletion = true;
};

struct Review {
    string reviewer;
    ReviewDecision decision;
    bool eligible = true;
    bool stale = false;
};

struct StatusCheck {
    string name;
    StageStatus status = StageStatus::PENDING;
    string details;
};

struct PullRequest {
    int id;
    string title;
    string sourceBranch;
    string targetBranch;
    string sourceCommit;
    string targetCommit;

    bool draft = false;
    bool open = true;
    bool mergeConflict = false;
    bool conversationsResolved = false;

    vector<Commit> commits;
    vector<Review> reviews;
    vector<StatusCheck> checks;

    MergeStrategy strategy = MergeStrategy::SQUASH;
};

struct GovernancePolicy {
    int requiredApprovals = 2;
    bool requireBuild = true;
    bool requireTests = true;
    bool requireSecurityScan = true;
    bool requireConversationsResolved = true;
    bool requireLinearHistory = true;
    bool requireProductionAuthorization = true;
    bool prohibitDirectPush = true;
    bool prohibitForcePush = true;
    bool prohibitBranchDeletion = true;
    bool permitAdministratorBypass = false;
};

struct EligibilityResult {
    bool eligible = false;
    vector<string> failures;
};

class Repository {
private:
    string name;
    map<string, Branch> branches;
    map<string, Commit> commits;
    map<int, PullRequest> pullRequests;
    GovernancePolicy policy;
    set<string> releaseVersions;

public:
    explicit Repository(string repositoryName, GovernancePolicy governance)
        : name(std::move(repositoryName)),
          policy(std::move(governance)) {
        if (name.empty()) {
            throw invalid_argument("Repository name cannot be empty");
        }
    }

    void addCommit(const Commit& commit) {
        if (commit.hash.empty() || commit.author.empty()) {
            throw invalid_argument("Invalid commit");
        }

        if (!commits.emplace(commit.hash, commit).second) {
            throw invalid_argument("Duplicate commit hash");
        }
    }

    void addBranch(const Branch& branch) {
        if (branch.name.empty()) {
            throw invalid_argument("Branch name cannot be empty");
        }

        if (!commits.count(branch.headCommit)) {
            throw invalid_argument("Branch references an unknown commit");
        }

        if (!branches.emplace(branch.name, branch).second) {
            throw invalid_argument("Branch already exists");
        }
    }

    void createPullRequest(const PullRequest& request) {
        if (request.id <= 0 || request.title.empty()) {
            throw invalid_argument("Invalid Pull Request");
        }

        if (!branches.count(request.sourceBranch) ||
            !branches.count(request.targetBranch)) {
            throw invalid_argument("Unknown source or target branch");
        }

        if (request.sourceBranch == request.targetBranch) {
            throw invalid_argument("Source and target branches must differ");
        }

        if (!commits.count(request.sourceCommit) ||
            !commits.count(request.targetCommit)) {
            throw invalid_argument("Unknown proposed commit");
        }

        if (!pullRequests.emplace(request.id, request).second) {
            throw invalid_argument("Duplicate Pull Request ID");
        }
    }

    void updateCheck(
        int requestId,
        const string& checkName,
        StageStatus status,
        const string& details
    ) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        if (checkName.empty()) {
            throw invalid_argument("Check name is required");
        }

        auto& checks = it->second.checks;

        auto existing = find_if(
            checks.begin(),
            checks.end(),
            [&](const StatusCheck& check) {
                return check.name == checkName;
            }
        );

        if (existing == checks.end()) {
            checks.push_back({checkName, status, details});
        } else {
            existing->status = status;
            existing->details = details;
        }
    }

    void addReview(int requestId, const Review& review) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        if (review.reviewer.empty()) {
            throw invalid_argument("Reviewer identity is required");
        }

        it->second.reviews.push_back(review);
    }

    void setConversationsResolved(int requestId, bool resolved) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        it->second.conversationsResolved = resolved;
    }

    EligibilityResult evaluate(
        const PullRequest& request,
        Environment environment,
        bool productionAuthorized,
        bool administrator = false
    ) const {
        EligibilityResult result;

        auto failure = [&](const string& reason) {
            result.failures.push_back(reason);
        };

        if (!request.open) {
            failure("Pull Request is closed");
        }

        if (request.draft) {
            failure("Draft Pull Requests cannot be merged");
        }

        if (request.mergeConflict) {
            failure("Merge conflict exists");
        }

        auto target = branches.find(request.targetBranch);

        if (target == branches.end()) {
            failure("Target branch does not exist");
        } else if (
            policy.prohibitDirectPush &&
            !target->second.protectedBranch
        ) {
            failure("Target branch is not protected");
        }

        if (policy.requireConversationsResolved &&
            !request.conversationsResolved) {
            failure("Review conversations remain unresolved");
        }

        if (request.commits.empty()) {
            failure("No proposed commits exist");
        }

        if (policy.requireLinearHistory &&
            request.strategy == MergeStrategy::MERGE_COMMIT) {
            failure("Merge commit violates linear history policy");
        }

        // Count unique, eligible, current approvals.
        set<string> approvers;

        for (const auto& review : request.reviews) {
            if (
                review.eligible &&
                !review.stale &&
                review.decision == ReviewDecision::APPROVED
            ) {
                approvers.insert(review.reviewer);
            }
        }

        if (static_cast<int>(approvers.size()) <
            policy.requiredApprovals) {
            failure("Required approval threshold not satisfied");
        }

        // A current rejection blocks merging until a new decision
        // or an explicit dismissal policy is applied.
        for (const auto& review : request.reviews) {
            if (
                review.eligible &&
                !review.stale &&
                review.decision == ReviewDecision::REJECTED
            ) {
                failure("An eligible reviewer has rejected the changes");
                break;
            }
        }

        auto checkPassed = [&](const string& name) {
            auto it = find_if(
                request.checks.begin(),
                request.checks.end(),
                [&](const StatusCheck& check) {
                    return check.name == name;
                }
            );

            return it != request.checks.end() &&
                   it->status == StageStatus::PASSED;
        };

        if (policy.requireBuild && !checkPassed("build")) {
            failure("Build check is missing or unsuccessful");
        }

        if (policy.requireTests && !checkPassed("tests")) {
            failure("Automated tests are missing or unsuccessful");
        }

        if (
            policy.requireSecurityScan &&
            !checkPassed("security-scan")
        ) {
            failure("Security scan is missing or unsuccessful");
        }

        if (
            environment == Environment::PRODUCTION &&
            policy.requireProductionAuthorization &&
            !productionAuthorized
        ) {
            failure("Production release authorization is missing");
        }

        if (administrator && !policy.permitAdministratorBypass) {
            // Administrators are subject to the same policy.
            failure("Administrator bypass is prohibited");
        }

        result.eligible = result.failures.empty();

        return result;
    }

    void merge(
        int requestId,
        Environment environment,
        bool productionAuthorized = false
    ) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        PullRequest& request = it->second;

        EligibilityResult eligibility = evaluate(
            request,
            environment,
            productionAuthorized
        );

        if (!eligibility.eligible) {
            throw runtime_error(
                "Merge blocked by repository governance"
            );
        }

        auto branch = branches.find(request.targetBranch);

        if (branch == branches.end()) {
            throw runtime_error("Target branch disappeared");
        }

        // Simulate the target branch moving to the approved source commit.
        branch->second.headCommit = request.sourceCommit;
        request.open = false;

        cout << "Pull Request #" << request.id
             << " merged into " << request.targetBranch << "\n";
    }

    void setBranchHead(const string& branchName, const string& commitHash) {
        auto branch = branches.find(branchName);

        if (branch == branches.end() || !commits.count(commitHash)) {
            throw invalid_argument("Unknown branch or commit");
        }

        branch->second.headCommit = commitHash;

        // Existing approvals become stale after the proposed commit changes.
        for (auto& [id, request] : pullRequests) {
            if (
                request.sourceBranch == branchName &&
                request.open
            ) {
                for (auto& review : request.reviews) {
                    review.stale = true;
                }
            }
        }
    }

    void pushDirectly(
        const string& branchName,
        const string& commitHash,
        bool forcePush = false
    ) {
        auto branch = branches.find(branchName);

        if (branch == branches.end() || !commits.count(commitHash)) {
            throw invalid_argument("Unknown branch or commit");
        }

        if (branch->second.protectedBranch) {
            if (policy.prohibitDirectPush) {
                throw runtime_error("Direct push prohibited");
            }

            if (forcePush && policy.prohibitForcePush) {
                throw runtime_error("Force push prohibited");
            }
        }

        branch->second.headCommit = commitHash;
    }

    void deleteBranch(const string& branchName) {
        auto branch = branches.find(branchName);

        if (branch == branches.end()) {
            throw invalid_argument("Branch not found");
        }

        if (
            branch->second.protectedBranch &&
            policy.prohibitBranchDeletion
        ) {
            throw runtime_error("Protected branch deletion prohibited");
        }

        branches.erase(branch);
    }

    void closePullRequest(int requestId) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        it->second.open = false;
    }

    void reopenPullRequest(int requestId) {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        if (it->second.sourceBranch.empty()) {
            throw runtime_error("Source branch is unavailable");
        }

        it->second.open = true;
    }

    const PullRequest& getPullRequest(int requestId) const {
        auto it = pullRequests.find(requestId);

        if (it == pullRequests.end()) {
            throw invalid_argument("Pull Request not found");
        }

        return it->second;
    }

    void printEligibility(
        int requestId,
        Environment environment,
        bool productionAuthorized
    ) const {
        const auto& request = getPullRequest(requestId);

        auto result = evaluate(
            request,
            environment,
            productionAuthorized
        );

        cout << "\nMERGE ELIGIBILITY: #" << requestId << "\n";

        if (result.eligible) {
            cout << "ELIGIBLE\n";
        } else {
            cout << "BLOCKED\n";

            for (const auto& reason : result.failures) {
                cout << " - " << reason << "\n";
            }
        }
    }
};


class DeliveryEngine {
private:
    PipelineStatus status = PipelineStatus::CREATED;
    map<string, StageStatus> stages;
    vector<string> eventLog;

    void executeStage(
        const string& name,
        bool simulatedSuccess
    ) {
        stages[name] = StageStatus::RUNNING;
        eventLog.push_back("Started: " + name);

        if (!simulatedSuccess) {
            stages[name] = StageStatus::FAILED;
            eventLog.push_back("Failed: " + name);
            throw runtime_error("Stage failed: " + name);
        }

        stages[name] = StageStatus::PASSED;
        eventLog.push_back("Passed: " + name);
    }

public:
    PipelineStatus execute(bool testsPass = true) {
        if (status != PipelineStatus::CREATED) {
            throw logic_error("Pipeline has already been executed");
        }

        status = PipelineStatus::RUNNING;

        vector<string> orderedStages = {
            "build",
            "tests",
            "package",
            "release"
        };

        try {
            executeStage("build", true);
            executeStage("tests", testsPass);
            executeStage("package", true);
            executeStage("release", true);

            status = PipelineStatus::RELEASED;

        } catch (const exception& error) {
            status = PipelineStatus::FAILED;

            for (const auto& stage : orderedStages) {
                if (!stages.count(stage)) {
                    stages[stage] = StageStatus::SKIPPED;
                }
            }

            eventLog.push_back(error.what());
        }

        return status;
    }

    void report() const {
        cout << "\nDELIVERY PIPELINE\n";
        cout << "Status: " << toString(status) << "\n";

        for (const auto& [name, stageStatus] : stages) {
            cout << left << setw(15) << name
                 << toString(stageStatus) << "\n";
        }

        cout << "\nEVENT LOG\n";

        for (const auto& event : eventLog) {
            cout << event << "\n";
        }
    }
};


int main() {
    try {
        GovernancePolicy policy;
        policy.requiredApprovals = 2;

        Repository repository(
            "enterprise-payment-platform",
            policy
        );

        repository.addCommit({
            "c001",
            "Initial application",
            "developer-a"
        });

        repository.addCommit({
            "c002",
            "Add payment validation",
            "developer-b"
        });

        repository.addCommit({
            "c003",
            "Integrate release configuration",
            "developer-c"
        });

        repository.addBranch({
            "main",
            "c001",
            true,
            false,
            false,
            false
        });

        repository.addBranch({
            "feature/payment-validation",
            "c002",
            false,
            true,
            false,
            true
        });

        PullRequest request;
        request.id = 101;
        request.title = "Introduce payment validation";
        request.sourceBranch = "feature/payment-validation";
        request.targetBranch = "main";
        request.sourceCommit = "c002";
        request.targetCommit = "c001";
        request.strategy = MergeStrategy::SQUASH;
        request.commits.push_back({
            "c002",
            "Add payment validation",
            "developer-b"
        });

        repository.createPullRequest(request);

        repository.addReview(
            101,
            {"reviewer-a", ReviewDecision::APPROVED, true, false}
        );

        repository.addReview(
            101,
            {"reviewer-b", ReviewDecision::APPROVED, true, false}
        );

        repository.updateCheck(
            101,
            "build",
            StageStatus::PASSED,
            "Compilation successful"
        );

        repository.updateCheck(
            101,
            "tests",
            StageStatus::PASSED,
            "128 tests passed"
        );

        repository.updateCheck(
            101,
            "security-scan",
            StageStatus::PASSED,
            "No blocking findings"
        );

        repository.setConversationsResolved(101, true);

        repository.printEligibility(
            101,
            Environment::PRODUCTION,
            true
        );

        repository.merge(
            101,
            Environment::PRODUCTION,
            true
        );

        // A protected branch rejects direct modifications.
        try {
            repository.pushDirectly("main", "c003");
        } catch (const exception& error) {
            cout << "\nExpected governance rejection: "
                 << error.what() << "\n";
        }

        // A changed source commit invalidates previous approvals.
        repository.addBranch({
            "feature/new-release",
            "c003",
            false,
            true,
            false,
            true
        });

        PullRequest second;
        second.id = 102;
        second.title = "Prepare release configuration";
        second.sourceBranch = "feature/new-release";
        second.targetBranch = "main";
        second.sourceCommit = "c003";
        second.targetCommit = "c002";
        second.commits.push_back({
            "c003",
            "Integrate release configuration",
            "developer-c"
        });

        repository.createPullRequest(second);

        repository.addReview(
            102,
            {"reviewer-a", ReviewDecision::APPROVED, true, false}
        );

        repository.updateCheck(
            102, "build", StageStatus::PASSED, "Build passed"
        );

        repository.updateCheck(
            102, "tests", StageStatus::PASSED, "Tests passed"
        );

        repository.updateCheck(
            102, "security-scan", StageStatus::FAILED, "Critical finding"
        );

        repository.setConversationsResolved(102, true);

        repository.printEligibility(
            102,
            Environment::PRODUCTION,
            false
        );

        DeliveryEngine delivery;

        delivery.execute(true);
        delivery.report();

        DeliveryEngine failedDelivery;
        failedDelivery.execute(false);
        failedDelivery.report();

        cout << "\nAll governance scenarios executed.\n";

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
