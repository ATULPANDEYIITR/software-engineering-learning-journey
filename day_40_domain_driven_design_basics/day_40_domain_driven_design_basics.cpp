#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * C++17 case study: Repository aggregate-governance domain.
 *
 * The system models a software repository where a Pull Request aggregate
 * controls its commits and review decisions. The example deliberately
 * separates:
 *
 * Domain:
 *   The business space is collaborative source-code change management.
 *
 * Entity:
 *   PullRequest has identity and a lifecycle.
 *
 * Value object:
 *   BranchName and CommitId are represented by values whose meaning comes
 *   from their validated content.
 *
 * Aggregate:
 *   PullRequest is the consistency boundary for commits, reviews, status,
 *   and merge state. RepositoryPolicy is a separate policy object because
 *   it governs repository-level rules rather than one Pull Request's data.
 *
 * The implementation is an executable merge-eligibility engine rather than
 * a language-syntax demonstration.
 */

class DomainError : public std::runtime_error {
public:
    explicit DomainError(const std::string& message)
        : std::runtime_error(message) {}
};

class BranchName {
private:
    std::string value_;

public:
    explicit BranchName(std::string value) : value_(std::move(value)) {
        if (value_.empty()) {
            throw DomainError("Branch name cannot be empty");
        }

        if (value_.find(' ') != std::string::npos) {
            throw DomainError("Branch name cannot contain spaces");
        }
    }

    const std::string& value() const {
        return value_;
    }

    bool operator==(const BranchName& other) const {
        return value_ == other.value_;
    }
};

class CommitId {
private:
    std::string value_;

public:
    explicit CommitId(std::string value) : value_(std::move(value)) {
        if (value_.size() < 7) {
            throw DomainError("Commit identifier is too short");
        }
    }

    const std::string& value() const {
        return value_;
    }

    bool operator==(const CommitId& other) const {
        return value_ == other.value_;
    }
};

enum class PullRequestState {
    Draft,
    Open,
    Closed,
    Merged
};

enum class ReviewDecision {
    Commented,
    ChangesRequested,
    Approved
};

struct Review {
    std::string reviewer;
    ReviewDecision decision;
    std::string body;
};

struct StatusCheck {
    std::string name;
    bool passed;
};

class RepositoryPolicy {
private:
    BranchName protectedBranch_;
    int requiredApprovals_;
    std::vector<std::string> requiredChecks_;
    bool requireLinearHistory_;
    bool allowForcePush_;

public:
    RepositoryPolicy(
        BranchName protectedBranch,
        int requiredApprovals,
        std::vector<std::string> requiredChecks,
        bool requireLinearHistory,
        bool allowForcePush
    )
        : protectedBranch_(std::move(protectedBranch)),
          requiredApprovals_(requiredApprovals),
          requiredChecks_(std::move(requiredChecks)),
          requireLinearHistory_(requireLinearHistory),
          allowForcePush_(allowForcePush) {
        if (requiredApprovals_ < 0) {
            throw DomainError("Required approval count cannot be negative");
        }
    }

    const BranchName& protectedBranch() const {
        return protectedBranch_;
    }

    int requiredApprovals() const {
        return requiredApprovals_;
    }

    const std::vector<std::string>& requiredChecks() const {
        return requiredChecks_;
    }

    bool requireLinearHistory() const {
        return requireLinearHistory_;
    }

    bool allowForcePush() const {
        return allowForcePush_;
    }
};

class PullRequest {
private:
    std::string id_;
    std::string title_;
    BranchName source_;
    BranchName target_;
    PullRequestState state_;
    std::vector<CommitId> commits_;
    std::vector<Review> reviews_;
    std::map<std::string, StatusCheck> statusChecks_;
    bool hasMergeConflict_;
    bool baseBranchChanged_;

public:
    PullRequest(
        std::string id,
        std::string title,
        BranchName source,
        BranchName target
    )
        : id_(std::move(id)),
          title_(std::move(title)),
          source_(std::move(source)),
          target_(std::move(target)),
          state_(PullRequestState::Draft),
          hasMergeConflict_(false),
          baseBranchChanged_(false) {
        if (title_.empty()) {
            throw DomainError("Pull Request title cannot be empty");
        }

        if (source_ == target_) {
            throw DomainError("Source and target branches must differ");
        }
    }

    void markReadyForReview() {
        if (state_ != PullRequestState::Draft) {
            throw DomainError("Only a draft Pull Request can become ready");
        }

        state_ = PullRequestState::Open;
    }

    void addCommit(const CommitId& commit) {
        if (state_ != PullRequestState::Draft &&
            state_ != PullRequestState::Open) {
            throw DomainError("Commits cannot be added in the current state");
        }

        const auto exists = std::find(
            commits_.begin(),
            commits_.end(),
            commit
        );

        if (exists == commits_.end()) {
            commits_.push_back(commit);
        }
    }

    void recordReview(Review review) {
        if (state_ != PullRequestState::Open) {
            throw DomainError("Reviews require an open Pull Request");
        }

        if (review.reviewer.empty()) {
            throw DomainError("Reviewer identity is required");
        }

        reviews_.push_back(std::move(review));
    }

    void setStatusCheck(std::string name, bool passed) {
        if (name.empty()) {
            throw DomainError("Status check name cannot be empty");
        }

        statusChecks_[std::move(name)] = StatusCheck{
            statusChecks_.rbegin()->first,
            passed
        };
    }

    void updateStatusCheck(const std::string& name, bool passed) {
        statusChecks_[name] = StatusCheck{name, passed};
    }

    void markBaseBranchChanged() {
        baseBranchChanged_ = true;
    }

    void resolveBaseBranch() {
        baseBranchChanged_ = false;
    }

    void setMergeConflict(bool conflict) {
        hasMergeConflict_ = conflict;
    }

    void close() {
        if (state_ == PullRequestState::Merged) {
            throw DomainError("Merged Pull Request cannot be closed");
        }

        state_ = PullRequestState::Closed;
    }

    bool hasChangesRequested() const {
        return std::any_of(
            reviews_.begin(),
            reviews_.end(),
            [](const Review& review) {
                return review.decision == ReviewDecision::ChangesRequested;
            }
        );
    }

    int approvalCount() const {
        // Count the latest decision by each reviewer. A later review from
        // the same reviewer supersedes that reviewer's earlier decision.
        std::unordered_map<std::string, ReviewDecision> latest;

        for (const auto& review : reviews_) {
            latest[review.reviewer] = review.decision;
        }

        int count = 0;

        for (const auto& [reviewer, decision] : latest) {
            (void)reviewer;
            if (decision == ReviewDecision::Approved) {
                ++count;
            }
        }

        return count;
    }

    bool hasPassingRequiredChecks(
        const std::vector<std::string>& requiredChecks
    ) const {
        for (const auto& required : requiredChecks) {
            const auto it = statusChecks_.find(required);

            if (it == statusChecks_.end() || !it->second.passed) {
                return false;
            }
        }

        return true;
    }

    bool mergeEligible(const RepositoryPolicy& policy) const {
        if (state_ != PullRequestState::Open) {
            return false;
        }

        if (!(target_ == policy.protectedBranch())) {
            return false;
        }

        if (commits_.empty()) {
            return false;
        }

        if (hasMergeConflict_ || baseBranchChanged_) {
            return false;
        }

        if (hasChangesRequested()) {
            return false;
        }

        if (approvalCount() < policy.requiredApprovals()) {
            return false;
        }

        if (!hasPassingRequiredChecks(policy.requiredChecks())) {
            return false;
        }

        return true;
    }

    void merge(const RepositoryPolicy& policy) {
        if (!mergeEligible(policy)) {
            throw DomainError("Pull Request is not eligible for merge");
        }

        state_ = PullRequestState::Merged;
    }

    const std::string& id() const {
        return id_;
    }

    PullRequestState state() const {
        return state_;
    }

    std::size_t commitCount() const {
        return commits_.size();
    }
};

class MergeEligibilityReport {
public:
    static void print(
        const PullRequest& pullRequest,
        const RepositoryPolicy& policy
    ) {
        std::cout << "\nMerge eligibility report\n";
        std::cout << "Pull Request: " << pullRequest.id() << '\n';
        std::cout << "Commits: " << pullRequest.commitCount() << '\n';
        std::cout << "Approvals: " << pullRequest.approvalCount()
                  << " / " << policy.requiredApprovals() << '\n';
        std::cout << "Eligible: "
                  << (pullRequest.mergeEligible(policy) ? "yes" : "no")
                  << '\n';
    }
};

void demonstrateValueObjects() {
    std::cout << "=== Value objects ===\n";

    BranchName first("feature/payment");
    BranchName second("feature/payment");

    std::cout << "Equal branch values: "
              << (first == second ? "true" : "false")
              << '\n';

    CommitId commit("a83f91c");

    std::cout << "Validated commit value: "
              << commit.value()
              << "\n\n";
}

int main() {
    try {
        demonstrateValueObjects();

        RepositoryPolicy policy(
            BranchName("main"),
            2,
            {"build", "security-scan", "integration-tests"},
            true,
            false
        );

        PullRequest pullRequest(
            "PR-204",
            "Introduce payment reconciliation workflow",
            BranchName("feature/payment"),
            BranchName("main")
        );

        std::cout << "=== Repository aggregate case study ===\n";

        pullRequest.addCommit(CommitId("a83f91c"));
        pullRequest.addCommit(CommitId("bd1294e"));
        pullRequest.markReadyForReview();

        pullRequest.updateStatusCheck("build", true);
        pullRequest.updateStatusCheck("security-scan", true);
        pullRequest.updateStatusCheck("integration-tests", true);

        pullRequest.recordReview({
            "reviewer-alice",
            ReviewDecision::Approved,
            "The domain model preserves payment reconciliation invariants."
        });

        pullRequest.recordReview({
            "reviewer-bob",
            ReviewDecision::Approved,
            "Status handling and failure paths are covered."
        });

        MergeEligibilityReport::print(pullRequest, policy);

        pullRequest.merge(policy);

        std::cout << "Final state: merged\n";

        PullRequest blockedPullRequest(
            "PR-205",
            "Update settlement rules",
            BranchName("feature/settlement"),
            BranchName("main")
        );

        blockedPullRequest.addCommit(CommitId("f712aa9"));
        blockedPullRequest.markReadyForReview();

        blockedPullRequest.updateStatusCheck("build", true);
        blockedPullRequest.updateStatusCheck("security-scan", true);
        blockedPullRequest.updateStatusCheck("integration-tests", false);

        blockedPullRequest.recordReview({
            "reviewer-alice",
            ReviewDecision::Approved,
            "Business rules look consistent."
        });

        blockedPullRequest.recordReview({
            "reviewer-bob",
            ReviewDecision::Approved,
            "Awaiting integration test results."
        });

        MergeEligibilityReport::print(blockedPullRequest, policy);

        try {
            blockedPullRequest.merge(policy);
        } catch (const DomainError& error) {
            std::cout << "Protected merge attempt rejected: "
                      << error.what()
                      << '\n';
        }

        blockedPullRequest.updateStatusCheck("integration-tests", true);
        blockedPullRequest.markBaseBranchChanged();

        MergeEligibilityReport::print(blockedPullRequest, policy);

        try {
            blockedPullRequest.merge(policy);
        } catch (const DomainError& error) {
            std::cout << "Synchronization required before merge: "
                      << error.what()
                      << '\n';
        }

        blockedPullRequest.resolveBaseBranch();

        MergeEligibilityReport::print(blockedPullRequest, policy);

        blockedPullRequest.merge(policy);
        std::cout << "Second Pull Request merged after its invariants became valid.\n";

    } catch (const DomainError& error) {
        std::cerr << "Domain failure: " << error.what() << '\n';
        return 1;
    }

    return 0;
}
