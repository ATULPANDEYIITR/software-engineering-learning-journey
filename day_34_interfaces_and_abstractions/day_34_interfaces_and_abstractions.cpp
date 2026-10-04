/*
 * Interfaces & Abstractions
 * Contracts, dependency boundaries
 *
 * C++17 case study:
 * A repository governance engine evaluates whether a Pull Request may enter
 * a protected branch. The design deliberately separates:
 *
 *   domain model       -> Pull Request, reviews, repository policy
 *   contracts          -> abstract interfaces for reviews, checks, audit
 *   application        -> merge-eligibility orchestration
 *   infrastructure     -> in-memory implementations
 *
 * The important boundary is that the application layer never needs to know
 * how review data, status checks, or audit events are physically stored.
 */

#include <algorithm>
#include <chrono>
#include <exception>
#include <iomanip>
#include <iostream>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>


// -----------------------------------------------------------------------------
// Domain value types
// -----------------------------------------------------------------------------

enum class ReviewState {
    Approved,
    ChangesRequested,
    Commented
};

struct Review {
    std::string reviewer;
    ReviewState state;
    std::string comment;
    std::string commitId;
};

struct PullRequest {
    int number;
    std::string repository;
    std::string sourceBranch;
    std::string targetBranch;
    std::string author;
    std::vector<std::string> changedFiles;
    std::string headCommit;
};

struct BranchPolicy {
    std::string protectedBranch;
    std::size_t requiredApprovals;
    bool requirePassingChecks;
    bool requireLinearHistory;
    bool allowDirectPush;
    bool allowForcePush;
};

struct StatusChecks {
    bool buildPassed;
    bool testsPassed;
    bool securityScanPassed;

    bool allRequiredChecksPassed() const {
        return buildPassed && testsPassed && securityScanPassed;
    }
};

struct MergeDecision {
    bool allowed;
    std::vector<std::string> blockers;
    std::set<std::string> eligibleApprovers;
};


// -----------------------------------------------------------------------------
// Contract: review source
// -----------------------------------------------------------------------------

class IReviewRepository {
public:
    virtual ~IReviewRepository() = default;

    virtual std::vector<Review> findReviews(
        const std::string& repository,
        int pullRequestNumber,
        const std::string& currentHeadCommit
    ) const = 0;
};


// -----------------------------------------------------------------------------
// Contract: status-check source
// -----------------------------------------------------------------------------

class IStatusCheckProvider {
public:
    virtual ~IStatusCheckProvider() = default;

    virtual StatusChecks getStatus(
        const std::string& repository,
        const std::string& commitId
    ) const = 0;
};


// -----------------------------------------------------------------------------
// Contract: audit sink
// -----------------------------------------------------------------------------

class IAuditSink {
public:
    virtual ~IAuditSink() = default;

    virtual void record(
        const std::string& event,
        const std::string& actor,
        const std::string& details
    ) = 0;
};


// -----------------------------------------------------------------------------
// Infrastructure implementations
// -----------------------------------------------------------------------------

class MemoryReviewRepository final : public IReviewRepository {
private:
    struct Key {
        std::string repository;
        int pullRequestNumber;

        bool operator==(const Key& other) const {
            return repository == other.repository &&
                   pullRequestNumber == other.pullRequestNumber;
        }
    };

    struct KeyHash {
        std::size_t operator()(const Key& key) const {
            const std::size_t h1 = std::hash<std::string>{}(key.repository);
            const std::size_t h2 = std::hash<int>{}(key.pullRequestNumber);
            return h1 ^ (h2 << 1);
        }
    };

    std::unordered_map<Key, std::vector<Review>, KeyHash> reviews_;

public:
    void addReview(
        const std::string& repository,
        int pullRequestNumber,
        Review review
    ) {
        reviews_[Key{repository, pullRequestNumber}].push_back(
            std::move(review)
        );
    }

    std::vector<Review> findReviews(
        const std::string& repository,
        int pullRequestNumber,
        const std::string& currentHeadCommit
    ) const override {
        const Key key{repository, pullRequestNumber};
        auto iterator = reviews_.find(key);

        if (iterator == reviews_.end()) {
            return {};
        }

        std::vector<Review> currentReviews;

        // An approval tied to an older commit is not treated as a current
        // approval. This models a common contract where synchronization with
        // the current Pull Request head invalidates stale review decisions.
        for (const Review& review : iterator->second) {
            if (review.commitId == currentHeadCommit) {
                currentReviews.push_back(review);
            }
        }

        return currentReviews;
    }
};


class MemoryStatusCheckProvider final : public IStatusCheckProvider {
private:
    std::unordered_map<std::string, StatusChecks> checks_;

public:
    void setStatus(
        const std::string& commitId,
        StatusChecks status
    ) {
        checks_[commitId] = status;
    }

    StatusChecks getStatus(
        const std::string& repository,
        const std::string& commitId
    ) const override {
        static_cast<void>(repository);

        auto iterator = checks_.find(commitId);

        if (iterator == checks_.end()) {
            // Missing checks are not silently interpreted as success.
            return StatusChecks{false, false, false};
        }

        return iterator->second;
    }
};


class MemoryAuditSink final : public IAuditSink {
private:
    struct AuditRecord {
        std::string event;
        std::string actor;
        std::string details;
    };

    std::vector<AuditRecord> records_;

public:
    void record(
        const std::string& event,
        const std::string& actor,
        const std::string& details
    ) override {
        records_.push_back({event, actor, details});
    }

    std::size_t size() const {
        return records_.size();
    }

    void print() const {
        for (const auto& record : records_) {
            std::cout
                << "[AUDIT] event=" << record.event
                << " actor=" << record.actor
                << " details=" << record.details
                << '\n';
        }
    }
};


// -----------------------------------------------------------------------------
// Application service
// -----------------------------------------------------------------------------

class MergeEligibilityEngine {
private:
    const IReviewRepository& reviewRepository_;
    const IStatusCheckProvider& statusProvider_;

public:
    MergeEligibilityEngine(
        const IReviewRepository& reviewRepository,
        const IStatusCheckProvider& statusProvider
    )
        : reviewRepository_(reviewRepository),
          statusProvider_(statusProvider) {}

    MergeDecision evaluate(
        const PullRequest& pullRequest,
        const BranchPolicy& policy
    ) const {
        MergeDecision decision;
        decision.allowed = true;

        // This is a domain rule, not an infrastructure rule. The engine
        // only needs the policy value and the Pull Request target branch.
        if (pullRequest.targetBranch != policy.protectedBranch) {
            decision.allowed = false;
            decision.blockers.push_back(
                "Pull Request does not target the protected branch"
            );
        }

        if (pullRequest.sourceBranch == pullRequest.targetBranch) {
            decision.allowed = false;
            decision.blockers.push_back(
                "source and target branches must be distinct"
            );
        }

        if (pullRequest.changedFiles.empty()) {
            decision.allowed = false;
            decision.blockers.push_back(
                "Pull Request contains no changed files"
            );
        }

        const StatusChecks checks =
            statusProvider_.getStatus(
                pullRequest.repository,
                pullRequest.headCommit
            );

        if (
            policy.requirePassingChecks &&
            !checks.allRequiredChecksPassed()
        ) {
            decision.allowed = false;
            decision.blockers.push_back(
                "required status checks have not passed"
            );
        }

        const std::vector<Review> reviews =
            reviewRepository_.findReviews(
                pullRequest.repository,
                pullRequest.number,
                pullRequest.headCommit
            );

        for (const Review& review : reviews) {
            if (
                review.state == ReviewState::Approved &&
                review.reviewer != pullRequest.author
            ) {
                decision.eligibleApprovers.insert(review.reviewer);
            }

            if (review.state == ReviewState::ChangesRequested) {
                decision.allowed = false;
                decision.blockers.push_back(
                    "a current review requests changes"
                );
            }
        }

        if (
            decision.eligibleApprovers.size() <
            policy.requiredApprovals
        ) {
            decision.allowed = false;

            std::ostringstream message;
            message
                << "requires "
                << policy.requiredApprovals
                << " current eligible approval(s), found "
                << decision.eligibleApprovers.size();

            decision.blockers.push_back(message.str());
        }

        return decision;
    }
};


// -----------------------------------------------------------------------------
// Protected branch administration
// -----------------------------------------------------------------------------

class BranchGuard {
private:
    BranchPolicy policy_;

public:
    explicit BranchGuard(BranchPolicy policy)
        : policy_(std::move(policy)) {}

    void validateDirectPush(
        const std::string& branch,
        bool administratorBypass
    ) const {
        if (branch != policy_.protectedBranch) {
            return;
        }

        if (policy_.allowDirectPush) {
            return;
        }

        if (administratorBypass) {
            // An explicit bypass is auditable and policy-driven. It is not
            // silently inferred from administrator identity.
            return;
        }

        throw std::runtime_error(
            "direct push to protected branch is prohibited"
        );
    }

    void validateForcePush(
        const std::string& branch,
        bool administratorBypass
    ) const {
        if (branch != policy_.protectedBranch) {
            return;
        }

        if (policy_.allowForcePush) {
            return;
        }

        if (administratorBypass) {
            return;
        }

        throw std::runtime_error(
            "force push to protected branch is prohibited"
        );
    }
};


// -----------------------------------------------------------------------------
// Formatting helpers
// -----------------------------------------------------------------------------

std::string decisionToText(const MergeDecision& decision) {
    std::ostringstream output;

    output << "merge_allowed="
           << (decision.allowed ? "true" : "false")
           << '\n';

    output << "eligible_approvers=";

    bool first = true;
    for (const auto& approver : decision.eligibleApprovers) {
        if (!first) {
            output << ',';
        }
        output << approver;
        first = false;
    }

    output << '\n';

    output << "blockers=" << '\n';

    if (decision.blockers.empty()) {
        output << "  none\n";
    } else {
        for (const auto& blocker : decision.blockers) {
            output << "  - " << blocker << '\n';
        }
    }

    return output.str();
}


// -----------------------------------------------------------------------------
// Case-study scenarios
// -----------------------------------------------------------------------------

void runCaseStudy() {
    MemoryReviewRepository reviewRepository;
    MemoryStatusCheckProvider statusProvider;
    MemoryAuditSink audit;

    BranchPolicy policy{
        "main",
        2,
        true,
        true,
        false,
        false
    };

    BranchGuard branchGuard(policy);

    // The current Pull Request head is "commit-current".
    PullRequest pullRequest{
        104,
        "payments-platform",
        "feature/contract-boundary",
        "main",
        "developer",
        {
            "domain/payment_policy.cpp",
            "application/payment_service.cpp",
            "tests/payment_policy_test.cpp"
        },
        "commit-current"
    };

    // Two valid approvals belong to the current head. A third review exists
    // for an older commit and therefore does not satisfy the current contract.
    reviewRepository.addReview(
        pullRequest.repository,
        pullRequest.number,
        Review{
            "security-reviewer",
            ReviewState::Approved,
            "Boundary validation is isolated.",
            "commit-current"
        }
    );

    reviewRepository.addReview(
        pullRequest.repository,
        pullRequest.number,
        Review{
            "platform-reviewer",
            ReviewState::Approved,
            "Infrastructure dependencies remain injected.",
            "commit-current"
        }
    );

    reviewRepository.addReview(
        pullRequest.repository,
        pullRequest.number,
        Review{
            "old-reviewer",
            ReviewState::Approved,
            "Approved before the latest changes.",
            "commit-old"
        }
    );

    statusProvider.setStatus(
        "commit-current",
        StatusChecks{
            true,
            true,
            true
        }
    );

    MergeEligibilityEngine engine(
        reviewRepository,
        statusProvider
    );

    MergeDecision decision =
        engine.evaluate(pullRequest, policy);

    std::cout << "\n=== Current Pull Request ===\n";
    std::cout << decisionToText(decision);

    audit.record(
        "merge_evaluation",
        "merge-controller",
        decision.allowed
            ? "eligible"
            : "blocked"
    );

    // A status-check failure blocks the merge independently of the review
    // count. This demonstrates why contracts are composed rather than merged
    // into one vague "approved" flag.
    PullRequest failingChecks = pullRequest;
    failingChecks.number = 105;
    failingChecks.headCommit = "commit-failing";

    reviewRepository.addReview(
        failingChecks.repository,
        failingChecks.number,
        Review{
            "security-reviewer",
            ReviewState::Approved,
            "Review complete.",
            "commit-failing"
        }
    );

    reviewRepository.addReview(
        failingChecks.repository,
        failingChecks.number,
        Review{
            "platform-reviewer",
            ReviewState::Approved,
            "Review complete.",
            "commit-failing"
        }
    );

    statusProvider.setStatus(
        "commit-failing",
        StatusChecks{
            true,
            false,
            true
        }
    );

    MergeDecision failedDecision =
        engine.evaluate(failingChecks, policy);

    std::cout << "\n=== Failed Status Check ===\n";
    std::cout << decisionToText(failedDecision);

    // A requested-change review blocks the merge even when approval count
    // might otherwise be sufficient.
    PullRequest requestedChanges = pullRequest;
    requestedChanges.number = 106;
    requestedChanges.headCommit = "commit-review-blocked";

    reviewRepository.addReview(
        requestedChanges.repository,
        requestedChanges.number,
        Review{
            "security-reviewer",
            ReviewState::Approved,
            "Security checks are good.",
            "commit-review-blocked"
        }
    );

    reviewRepository.addReview(
        requestedChanges.repository,
        requestedChanges.number,
        Review{
            "platform-reviewer",
            ReviewState::ChangesRequested,
            "Dependency crosses the infrastructure boundary.",
            "commit-review-blocked"
        }
    );

    statusProvider.setStatus(
        "commit-review-blocked",
        StatusChecks{true, true, true}
    );

    MergeDecision reviewBlockedDecision =
        engine.evaluate(requestedChanges, policy);

    std::cout << "\n=== Requested Changes ===\n";
    std::cout << decisionToText(reviewBlockedDecision);

    // Branch-level governance is evaluated separately from Pull Request
    // eligibility. A caller cannot turn a failed protected-branch rule into a
    // successful merge merely by presenting a Pull Request.
    std::cout << "\n=== Protected Branch Boundary ===\n";

    try {
        branchGuard.validateDirectPush("main", false);
        std::cout << "unexpected: direct push allowed\n";
    } catch (const std::exception& error) {
        std::cout << "direct push rejected: "
                  << error.what()
                  << '\n';
    }

    try {
        branchGuard.validateForcePush("main", false);
        std::cout << "unexpected: force push allowed\n";
    } catch (const std::exception& error) {
        std::cout << "force push rejected: "
                  << error.what()
                  << '\n';
    }

    // An explicit administrator bypass is permitted by this policy. A real
    // system should record identity, reason, timestamp, and authorization.
    try {
        branchGuard.validateDirectPush("main", true);
        audit.record(
            "protected_branch_bypass",
            "repository-admin",
            "direct push bypass was explicitly authorized"
        );
        std::cout << "administrator bypass accepted and audited\n";
    } catch (const std::exception& error) {
        std::cout << "unexpected bypass rejection: "
                  << error.what()
                  << '\n';
    }

    std::cout << "\n=== Audit Records ===\n";
    audit.print();
}


// -----------------------------------------------------------------------------
// Contract-focused tests
// -----------------------------------------------------------------------------

void runTests() {
    MemoryReviewRepository reviews;
    MemoryStatusCheckProvider checks;

    BranchPolicy policy{
        "main",
        1,
        true,
        true,
        false,
        false
    };

    PullRequest pr{
        1,
        "contracts",
        "feature/a",
        "main",
        "alice",
        {"contract.cpp"},
        "head-a"
    };

    reviews.addReview(
        "contracts",
        1,
        Review{
            "bob",
            ReviewState::Approved,
            "approved",
            "head-a"
        }
    );

    checks.setStatus(
        "head-a",
        StatusChecks{true, true, true}
    );

    MergeEligibilityEngine engine(reviews, checks);

    MergeDecision accepted = engine.evaluate(pr, policy);

    if (!accepted.allowed) {
        throw std::runtime_error(
            "contract test failed: valid Pull Request rejected"
        );
    }

    // Self approval must not satisfy the external approval contract.
    PullRequest selfApproved{
        2,
        "contracts",
        "feature/b",
        "main",
        "alice",
        {"contract.cpp"},
        "head-b"
    };

    reviews.addReview(
        "contracts",
        2,
        Review{
            "alice",
            ReviewState::Approved,
            "self approval",
            "head-b"
        }
    );

    checks.setStatus(
        "head-b",
        StatusChecks{true, true, true}
    );

    MergeDecision rejectedSelfApproval =
        engine.evaluate(selfApproved, policy);

    if (rejectedSelfApproval.allowed) {
        throw std::runtime_error(
            "contract test failed: self approval was accepted"
        );
    }

    // Stale approval must not satisfy the current-head contract.
    PullRequest staleApproval{
        3,
        "contracts",
        "feature/c",
        "main",
        "alice",
        {"contract.cpp"},
        "head-new"
    };

    reviews.addReview(
        "contracts",
        3,
        Review{
            "bob",
            ReviewState::Approved,
            "approved old version",
            "head-old"
        }
    );

    checks.setStatus(
        "head-new",
        StatusChecks{true, true, true}
    );

    MergeDecision rejectedStale =
        engine.evaluate(staleApproval, policy);

    if (rejectedStale.allowed) {
        throw std::runtime_error(
            "contract test failed: stale approval was accepted"
        );
    }

    // Missing status checks fail closed.
    PullRequest missingChecks{
        4,
        "contracts",
        "feature/d",
        "main",
        "alice",
        {"contract.cpp"},
        "unknown-head"
    };

    reviews.addReview(
        "contracts",
        4,
        Review{
            "bob",
            ReviewState::Approved,
            "approved",
            "unknown-head"
        }
    );

    MergeDecision rejectedMissingChecks =
        engine.evaluate(missingChecks, policy);

    if (rejectedMissingChecks.allowed) {
        throw std::runtime_error(
            "contract test failed: missing checks were treated as success"
        );
    }

    std::cout << "All C++ contract tests passed.\n";
}


int main() {
    try {
        std::cout
            << "INTERFACES, ABSTRACTIONS, AND DEPENDENCY BOUNDARIES\n"
            << "===================================================\n";

        runTests();
        runCaseStudy();

        return 0;
    } catch (const std::exception& error) {
        std::cerr
            << "Fatal error: "
            << error.what()
            << '\n';

        return 1;
    }
}
