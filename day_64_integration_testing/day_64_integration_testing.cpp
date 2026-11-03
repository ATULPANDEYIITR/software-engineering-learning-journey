#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

enum class PRState {
    Draft,
    Open,
    Closed,
    Merged
};

enum class ReviewState {
    Commented,
    Approved,
    ChangesRequested,
    Dismissed
};

enum class MergeStrategy {
    MergeCommit,
    Squash,
    Rebase
};

struct Commit {
    std::string sha;
    std::string message;
    std::string branch;
};

struct Review {
    std::string reviewer;
    ReviewState state;
    std::string commitSha;
    bool resolved{true};
};

struct StatusCheck {
    std::string name;
    bool passed;
    std::string commitSha;
};

struct BranchProtection {
    std::size_t requiredReviews{2};
    std::set<std::string> requiredChecks;
    bool allowDirectPush{false};
    bool allowForcePush{false};
    bool allowDeletion{false};
    bool requireConversationResolution{true};
    bool requireLinearHistory{false};
};

struct Branch {
    std::string name;
    std::vector<Commit> commits;
    bool protectedBranch{false};
};

struct PullRequest {
    int number;
    std::string title;
    std::string sourceBranch;
    std::string targetBranch;
    std::string author;
    PRState state{PRState::Open};
    bool draft{false};
    std::vector<Commit> commits;
    std::vector<Review> reviews;
    std::vector<StatusCheck> checks;
    std::set<std::string> changedFiles;
    std::size_t unresolvedConversations{0};
    MergeStrategy strategy{MergeStrategy::MergeCommit};

    std::string latestCommit() const {
        if (commits.empty()) {
            return {};
        }
        return commits.back().sha;
    }
};

struct Eligibility {
    bool allowed;
    std::vector<std::string> reasons;
};

class Repository {
private:
    std::string name_;
    int nextPr_{1};
    std::map<std::string, Branch> branches_;
    std::map<int, PullRequest> pullRequests_;
    std::map<std::string, BranchProtection> protection_;

public:
    explicit Repository(std::string name)
        : name_(std::move(name)) {}

    void addBranch(const std::string& name) {
        if (branches_.contains(name)) {
            throw std::invalid_argument("Branch already exists: " + name);
        }
        branches_.emplace(name, Branch{name});
    }

    void protectBranch(
        const std::string& name,
        const BranchProtection& policy
    ) {
        auto it = branches_.find(name);

        if (it == branches_.end()) {
            throw std::invalid_argument("Unknown branch");
        }

        it->second.protectedBranch = true;
        protection_[name] = policy;
    }

    void addCommit(
        const std::string& branch,
        const std::string& sha,
        const std::string& message
    ) {
        auto it = branches_.find(branch);

        if (it == branches_.end()) {
            throw std::invalid_argument("Unknown branch");
        }

        if (sha.size() < 7 || sha.size() > 40) {
            throw std::invalid_argument("Invalid commit SHA length");
        }

        if (message.empty()) {
            throw std::invalid_argument("Commit message cannot be empty");
        }

        it->second.commits.push_back(
            Commit{sha, message, branch}
        );
    }

    int createPullRequest(
        const std::string& title,
        const std::string& source,
        const std::string& target,
        const std::string& author,
        const std::set<std::string>& changedFiles,
        bool draft = false
    ) {
        if (!branches_.contains(source) || !branches_.contains(target)) {
            throw std::invalid_argument("Both branches must exist");
        }

        if (source == target) {
            throw std::invalid_argument("Source and target must differ");
        }

        const auto& sourceBranch = branches_.at(source);

        if (sourceBranch.commits.empty()) {
            throw std::invalid_argument(
                "Pull Request requires at least one commit"
            );
        }

        PullRequest pr{
            nextPr_++,
            title,
            source,
            target,
            author,
            draft ? PRState::Draft : PRState::Open,
            draft
        };

        pr.commits = sourceBranch.commits;
        pr.changedFiles = changedFiles;

        pullRequests_.emplace(pr.number, std::move(pr));
        return nextPr_ - 1;
    }

    PullRequest& pullRequest(int number) {
        auto it = pullRequests_.find(number);

        if (it == pullRequests_.end()) {
            throw std::out_of_range("Unknown Pull Request");
        }

        return it->second;
    }

    void synchronize(int number) {
        PullRequest& pr = pullRequest(number);
        pr.commits = branches_.at(pr.sourceBranch).commits;

        for (auto& review : pr.reviews) {
            if (review.commitSha != pr.latestCommit()) {
                review.state = ReviewState::Dismissed;
            }
        }
    }

    void addReview(
        int number,
        const std::string& reviewer,
        ReviewState state,
        const std::string& commitSha
    ) {
        PullRequest& pr = pullRequest(number);

        if (reviewer == pr.author) {
            throw std::invalid_argument(
                "Author cannot approve own Pull Request"
            );
        }

        if (commitSha != pr.latestCommit()) {
            state = ReviewState::Dismissed;
        }

        pr.reviews.push_back(
            Review{reviewer, state, commitSha, true}
        );
    }

    void addStatusCheck(
        int number,
        const std::string& name,
        bool passed,
        const std::string& commitSha
    ) {
        PullRequest& pr = pullRequest(number);

        pr.checks.push_back(
            StatusCheck{name, passed, commitSha}
        );
    }

    void addUnresolvedConversation(int number) {
        ++pullRequest(number).unresolvedConversations;
    }

    void resolveConversation(int number) {
        PullRequest& pr = pullRequest(number);

        if (pr.unresolvedConversations > 0) {
            --pr.unresolvedConversations;
        }
    }

    Eligibility evaluateMergeEligibility(int number) const {
        const auto& pr = pullRequests_.at(number);
        const auto policyIt = protection_.find(pr.targetBranch);

        std::vector<std::string> reasons;

        if (policyIt == protection_.end()) {
            reasons.push_back(
                "Target branch has no protection policy"
            );
            return {false, reasons};
        }

        const BranchProtection& policy = policyIt->second;

        if (pr.state != PRState::Open) {
            reasons.push_back("Pull Request is not open");
        }

        if (pr.draft) {
            reasons.push_back("Pull Request is still a draft");
        }

        const std::string latest = pr.latestCommit();

        std::set<std::string> approvers;

        for (const auto& review : pr.reviews) {
            if (
                review.state == ReviewState::Approved &&
                review.commitSha == latest
            ) {
                approvers.insert(review.reviewer);
            }
        }

        if (approvers.size() < policy.requiredReviews) {
            reasons.push_back(
                "Insufficient current approvals"
            );
        }

        for (const auto& required : policy.requiredChecks) {
            bool passed = false;

            for (const auto& check : pr.checks) {
                if (
                    check.name == required &&
                    check.commitSha == latest &&
                    check.passed
                ) {
                    passed = true;
                    break;
                }
            }

            if (!passed) {
                reasons.push_back(
                    "Required check failed or missing: " + required
                );
            }
        }

        if (
            policy.requireConversationResolution &&
            pr.unresolvedConversations > 0
        ) {
            reasons.push_back(
                "Unresolved review conversations remain"
            );
        }

        if (pr.changedFiles.empty()) {
            reasons.push_back("No changed files");
        }

        return {
            reasons.empty(),
            reasons
        };
    }

    void merge(int number, MergeStrategy strategy) {
        PullRequest& pr = pullRequest(number);
        const Eligibility result =
            evaluateMergeEligibility(number);

        if (!result.allowed) {
            throw std::runtime_error(
                "Merge rejected by branch protection"
            );
        }

        Branch& target = branches_.at(pr.targetBranch);

        if (strategy == MergeStrategy::MergeCommit) {
            target.commits.push_back(
                Commit{
                    "merge" + std::to_string(number),
                    "Merge Pull Request #" + std::to_string(number),
                    target.name
                }
            );
        } else if (strategy == MergeStrategy::Squash) {
            target.commits.push_back(
                Commit{
                    "squash" + std::to_string(number),
                    pr.title,
                    target.name
                }
            );
        } else {
            for (auto commit : pr.commits) {
                commit.branch = target.name;
                target.commits.push_back(commit);
            }
        }

        pr.strategy = strategy;
        pr.state = PRState::Merged;
    }
};

void successfulWorkflowTest() {
    Repository repository("integration-governance");

    repository.addBranch("main");
    repository.addBranch("feature/integration");

    BranchProtection policy;
    policy.requiredReviews = 2;
    policy.requiredChecks = {
        "api-integration",
        "database-integration"
    };
    policy.requireConversationResolution = true;

    repository.protectBranch("main", policy);

    repository.addCommit(
        "main",
        "1111111",
        "Initial production release"
    );

    repository.addCommit(
        "feature/integration",
        "2222222",
        "Add database and API integration tests"
    );

    const int pr = repository.createPullRequest(
        "Add integration test coverage",
        "feature/integration",
        "main",
        "alice",
        {
            "tests/api.integration.cpp",
            "tests/database.integration.cpp"
        }
    );

    repository.addReview(
        pr,
        "bob",
        ReviewState::Approved,
        "2222222"
    );

    repository.addReview(
        pr,
        "carol",
        ReviewState::Approved,
        "2222222"
    );

    repository.addStatusCheck(
        pr,
        "api-integration",
        true,
        "2222222"
    );

    repository.addStatusCheck(
        pr,
        "database-integration",
        true,
        "2222222"
    );

    repository.addUnresolvedConversation(pr);

    auto result =
        repository.evaluateMergeEligibility(pr);

    assert(!result.allowed);

    repository.resolveConversation(pr);

    result = repository.evaluateMergeEligibility(pr);

    assert(result.allowed);

    repository.merge(pr, MergeStrategy::Squash);

    assert(
        repository.pullRequest(pr).state ==
        PRState::Merged
    );

    std::cout
        << "PASS: successful integration workflow\n";
}

void staleApprovalTest() {
    Repository repository("stale-approval");

    repository.addBranch("main");
    repository.addBranch("feature");

    BranchProtection policy;
    policy.requiredReviews = 2;
    policy.requiredChecks = {"integration-tests"};

    repository.protectBranch("main", policy);

    repository.addCommit(
        "feature",
        "2222222",
        "Initial integration implementation"
    );

    const int pr = repository.createPullRequest(
        "Database integration tests",
        "feature",
        "main",
        "alice",
        {"database.integration.cpp"}
    );

    repository.addReview(
        pr,
        "bob",
        ReviewState::Approved,
        "2222222"
    );

    repository.addReview(
        pr,
        "carol",
        ReviewState::Approved,
        "2222222"
    );

    repository.addCommit(
        "feature",
        "3333333",
        "Fix transaction rollback assertion"
    );

    repository.synchronize(pr);

    repository.addStatusCheck(
        pr,
        "integration-tests",
        true,
        "3333333"
    );

    const auto result =
        repository.evaluateMergeEligibility(pr);

    assert(!result.allowed);
    assert(
        std::find(
            result.reasons.begin(),
            result.reasons.end(),
            "Insufficient current approvals"
        ) != result.reasons.end()
    );

    std::cout << "PASS: stale approval handling\n";
}

void failedCheckTest() {
    Repository repository("failed-check");

    repository.addBranch("main");
    repository.addBranch("feature");

    BranchProtection policy;
    policy.requiredReviews = 1;
    policy.requiredChecks = {"integration-tests"};

    repository.protectBranch("main", policy);

    repository.addCommit(
        "feature",
        "2222222",
        "Add API integration tests"
    );

    const int pr = repository.createPullRequest(
        "API integration validation",
        "feature",
        "main",
        "alice",
        {"api.integration.cpp"}
    );

    repository.addReview(
        pr,
        "bob",
        ReviewState::Approved,
        "2222222"
    );

    repository.addStatusCheck(
        pr,
        "integration-tests",
        false,
        "2222222"
    );

    const auto result =
        repository.evaluateMergeEligibility(pr);

    assert(!result.allowed);

    std::cout << "PASS: failed status check handling\n";
}

int main() {
    try {
        successfulWorkflowTest();
        staleApprovalTest();
        failedCheckTest();

        std::cout << "\nAll C++17 integration tests passed.\n";
    } catch (const std::exception& error) {
        std::cerr << "Test failure: "
                  << error.what()
                  << '\n';
        return 1;
    }

    return 0;
}
