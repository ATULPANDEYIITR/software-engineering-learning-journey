#include <algorithm>
#include <iostream>
#include <memory>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
    Design Patterns II: Strategy, Observer, Adapter

    Technical case study:
    A repository governance engine determines whether a Pull Request may be
    merged into a protected production branch.

    Strategy:
      Merge policies are interchangeable objects. Development and production
      policies enforce different rules without changing PullRequest.

    Observer:
      Repository lifecycle events are published to independent observers such
      as audit logging, metrics, and notifications.

    Adapter:
      An external CI system exposes build results using its own terminology.
      The adapter converts those results into the governance engine's status
      model.

    Compile:
      g++ -std=c++17 -Wall -Wextra -pedantic design_patterns_ii.cpp -o app
*/

enum class PullRequestState {
    Open,
    Draft,
    Merged,
    Closed
};

enum class ReviewDecision {
    Approve,
    RequestChanges,
    Comment
};

enum class CheckStatus {
    Passing,
    Failing,
    Pending
};

std::string toString(PullRequestState state) {
    switch (state) {
        case PullRequestState::Open:
            return "open";
        case PullRequestState::Draft:
            return "draft";
        case PullRequestState::Merged:
            return "merged";
        case PullRequestState::Closed:
            return "closed";
    }
    return "unknown";
}

std::string toString(ReviewDecision decision) {
    switch (decision) {
        case ReviewDecision::Approve:
            return "approve";
        case ReviewDecision::RequestChanges:
            return "request_changes";
        case ReviewDecision::Comment:
            return "comment";
    }
    return "unknown";
}

std::string toString(CheckStatus status) {
    switch (status) {
        case CheckStatus::Passing:
            return "passing";
        case CheckStatus::Failing:
            return "failing";
        case CheckStatus::Pending:
            return "pending";
    }
    return "unknown";
}

struct Commit {
    std::string sha;
    std::string message;
};

struct Review {
    std::string reviewer;
    ReviewDecision decision;
    std::string commitSha;
    std::string comment;
};

struct StatusCheck {
    std::string name;
    CheckStatus status;
    std::string commitSha;
};

class PullRequest {
public:
    PullRequest(
        int number,
        std::string title,
        std::string author,
        std::string sourceBranch,
        std::string targetBranch,
        std::vector<Commit> commits
    )
        : number_(number),
          title_(std::move(title)),
          author_(std::move(author)),
          sourceBranch_(std::move(sourceBranch)),
          targetBranch_(std::move(targetBranch)),
          commits_(std::move(commits)) {

        if (number_ <= 0) {
            throw std::invalid_argument("Pull Request number must be positive.");
        }

        if (commits_.empty()) {
            throw std::invalid_argument(
                "Pull Request requires at least one commit."
            );
        }
    }

    const std::string& headSha() const {
        return commits_.back().sha;
    }

    PullRequestState state() const {
        return state_;
    }

    bool mergeable() const {
        return mergeable_;
    }

    void setMergeable(bool value) {
        mergeable_ = value;
    }

    void addReview(Review review) {
        if (state_ == PullRequestState::Merged ||
            state_ == PullRequestState::Closed) {
            throw std::logic_error(
                "Reviews cannot be added after merge or closure."
            );
        }

        if (review.commitSha != headSha()) {
            throw std::invalid_argument(
                "Review must explicitly identify the reviewed commit."
            );
        }

        reviews_.push_back(std::move(review));
    }

    void addCheck(StatusCheck check) {
        if (check.commitSha != headSha()) {
            throw std::invalid_argument(
                "Status check does not correspond to the current head."
            );
        }

        checks_.push_back(std::move(check));
    }

    const std::vector<Review>& reviews() const {
        return reviews_;
    }

    const std::vector<StatusCheck>& checks() const {
        return checks_;
    }

    void merge() {
        if (state_ != PullRequestState::Open) {
            throw std::logic_error("Only open Pull Requests may be merged.");
        }

        state_ = PullRequestState::Merged;
    }

private:
    int number_;
    std::string title_;
    std::string author_;
    std::string sourceBranch_;
    std::string targetBranch_;
    std::vector<Commit> commits_;
    PullRequestState state_ = PullRequestState::Open;
    bool mergeable_ = true;
    std::vector<Review> reviews_;
    std::vector<StatusCheck> checks_;
};

// -----------------------------------------------------------------------------
// Strategy
// -----------------------------------------------------------------------------

struct MergeDecision {
    bool allowed;
    std::vector<std::string> reasons;
};

class MergeStrategy {
public:
    virtual ~MergeStrategy() = default;

    virtual MergeDecision evaluate(
        const PullRequest& pullRequest
    ) const = 0;
};

class DevelopmentMergeStrategy final : public MergeStrategy {
public:
    MergeDecision evaluate(
        const PullRequest& pullRequest
    ) const override {
        std::vector<std::string> reasons;

        if (pullRequest.state() != PullRequestState::Open) {
            reasons.push_back("Pull Request is not open.");
        }

        const auto& checks = pullRequest.checks();

        if (checks.empty()) {
            reasons.push_back("No status check exists for the current commit.");
        }

        for (const auto& check : checks) {
            if (check.status != CheckStatus::Passing) {
                reasons.push_back(
                    "Status check '" + check.name + "' is " +
                    toString(check.status) + "."
                );
            }
        }

        for (const auto& review : pullRequest.reviews()) {
            if (review.commitSha == pullRequest.headSha() &&
                review.decision == ReviewDecision::RequestChanges) {
                reasons.push_back(
                    "A reviewer requested changes on the current commit."
                );
            }
        }

        if (!pullRequest.mergeable()) {
            reasons.push_back("Pull Request contains unresolved conflicts.");
        }

        return {reasons.empty(), std::move(reasons)};
    }
};

class ProductionMergeStrategy final : public MergeStrategy {
public:
    ProductionMergeStrategy(
        std::set<std::string> eligibleReviewers,
        std::size_t requiredApprovals
    )
        : eligibleReviewers_(std::move(eligibleReviewers)),
          requiredApprovals_(requiredApprovals) {

        if (requiredApprovals_ == 0) {
            throw std::invalid_argument(
                "Production policy requires at least one approval."
            );
        }
    }

    MergeDecision evaluate(
        const PullRequest& pullRequest
    ) const override {
        std::vector<std::string> reasons;

        if (pullRequest.state() != PullRequestState::Open) {
            reasons.push_back("Pull Request is not open.");
        }

        std::set<std::string> approvals;

        for (const auto& review : pullRequest.reviews()) {
            if (review.commitSha == pullRequest.headSha() &&
                review.decision == ReviewDecision::Approve &&
                eligibleReviewers_.contains(review.reviewer)) {
                approvals.insert(review.reviewer);
            }

            if (review.commitSha == pullRequest.headSha() &&
                review.decision == ReviewDecision::RequestChanges) {
                reasons.push_back(
                    "Current commit has an outstanding change request."
                );
            }
        }

        if (approvals.size() < requiredApprovals_) {
            reasons.push_back(
                "Production branch requires " +
                std::to_string(requiredApprovals_) +
                " eligible approvals; only " +
                std::to_string(approvals.size()) +
                " are present."
            );
        }

        if (pullRequest.checks().empty()) {
            reasons.push_back("No status check exists for the current commit.");
        }

        for (const auto& check : pullRequest.checks()) {
            if (check.status != CheckStatus::Passing) {
                reasons.push_back(
                    "Required check '" + check.name + "' is " +
                    toString(check.status) + "."
                );
            }
        }

        if (!pullRequest.mergeable()) {
            reasons.push_back("Pull Request contains unresolved conflicts.");
        }

        return {reasons.empty(), std::move(reasons)};
    }

private:
    std::set<std::string> eligibleReviewers_;
    std::size_t requiredApprovals_;
};

// -----------------------------------------------------------------------------
// Observer
// -----------------------------------------------------------------------------

struct PullRequestEvent {
    std::string type;
    int pullRequestNumber;
    std::string actor;
    std::string message;
};

class Observer {
public:
    virtual ~Observer() = default;
    virtual void update(const PullRequestEvent& event) = 0;
};

class EventBus {
public:
    void subscribe(std::shared_ptr<Observer> observer) {
        observers_.push_back(std::move(observer));
    }

    void publish(const PullRequestEvent& event) const {
        // Copying shared_ptrs prevents observer collection changes during
        // callback execution from invalidating this iteration.
        const auto snapshot = observers_;

        for (const auto& observer : snapshot) {
            try {
                observer->update(event);
            } catch (const std::exception& error) {
                std::cerr
                    << "[observer-error] "
                    << error.what()
                    << '\n';
            }
        }
    }

private:
    std::vector<std::shared_ptr<Observer>> observers_;
};

class AuditObserver final : public Observer {
public:
    void update(const PullRequestEvent& event) override {
        entries_.push_back(
            event.type +
            ": PR #" +
            std::to_string(event.pullRequestNumber) +
            " by " +
            event.actor +
            " - " +
            event.message
        );

        std::cout << "[audit] " << entries_.back() << '\n';
    }

private:
    std::vector<std::string> entries_;
};

class MetricsObserver final : public Observer {
public:
    void update(const PullRequestEvent& event) override {
        ++counts_[event.type];
    }

    void print() const {
        for (const auto& [eventType, count] : counts_) {
            std::cout << "  " << eventType << ": " << count << '\n';
        }
    }

private:
    std::unordered_map<std::string, std::size_t> counts_;
};

class NotificationObserver final : public Observer {
public:
    void update(const PullRequestEvent& event) override {
        if (event.type == "review_requested" ||
            event.type == "changes_requested") {
            std::cout
                << "[notification] "
                << event.message
                << '\n';
        }
    }
};

// -----------------------------------------------------------------------------
// Adapter
// -----------------------------------------------------------------------------

struct ExternalBuild {
    std::string buildId;
    std::string result;
    std::string revision;
};

class ExternalCiClient {
public:
    ExternalCiClient() {
        builds_["abc123"] = {
            "build-1001",
            "SUCCESS",
            "abc123"
        };

        builds_["def456"] = {
            "build-1002",
            "FAILURE",
            "def456"
        };
    }

    std::optional<ExternalBuild> findBuild(
        const std::string& revision
    ) const {
        auto iterator = builds_.find(revision);

        if (iterator == builds_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }

private:
    std::unordered_map<std::string, ExternalBuild> builds_;
};

class StatusProvider {
public:
    virtual ~StatusProvider() = default;

    virtual StatusCheck getStatus(
        const std::string& commitSha
    ) const = 0;
};

class CiAdapter final : public StatusProvider {
public:
    explicit CiAdapter(const ExternalCiClient& client)
        : client_(client) {}

    StatusCheck getStatus(
        const std::string& commitSha
    ) const override {
        const auto build = client_.findBuild(commitSha);

        if (!build.has_value()) {
            // Unknown external state is conservatively represented as
            // pending. The governance engine must never interpret an unknown
            // external result as success.
            return {
                "external-ci",
                CheckStatus::Pending,
                commitSha
            };
        }

        CheckStatus status = CheckStatus::Pending;

        if (build->result == "SUCCESS") {
            status = CheckStatus::Passing;
        } else if (build->result == "FAILURE" ||
                   build->result == "CANCELLED") {
            status = CheckStatus::Failing;
        }

        return {
            "external-ci/" + build->buildId,
            status,
            commitSha
        };
    }

private:
    const ExternalCiClient& client_;
};

// -----------------------------------------------------------------------------
// Governance service
// -----------------------------------------------------------------------------

class GovernanceService {
public:
    GovernanceService(
        const MergeStrategy& strategy,
        const StatusProvider& statusProvider,
        EventBus& eventBus
    )
        : strategy_(strategy),
          statusProvider_(statusProvider),
          eventBus_(eventBus) {}

    void synchronizeCi(PullRequest& pullRequest, const std::string& actor) {
        auto status = statusProvider_.getStatus(pullRequest.headSha());

        pullRequest.addCheck(status);

        eventBus_.publish({
            "status_updated",
            42,
            actor,
            status.name + " is " + toString(status.status) + "."
        });
    }

    MergeDecision evaluate(
        const PullRequest& pullRequest
    ) const {
        return strategy_.evaluate(pullRequest);
    }

    bool merge(
        PullRequest& pullRequest,
        const std::string& actor
    ) {
        const auto decision = evaluate(pullRequest);

        if (!decision.allowed) {
            std::cout << "[merge] blocked\n";

            for (const auto& reason : decision.reasons) {
                std::cout << "  - " << reason << '\n';
            }

            return false;
        }

        pullRequest.merge();

        eventBus_.publish({
            "merged",
            42,
            actor,
            "Pull Request merged."
        });

        return true;
    }

private:
    const MergeStrategy& strategy_;
    const StatusProvider& statusProvider_;
    EventBus& eventBus_;
};

int main() {
    std::cout << "=== Repository Governance Case Study ===\n\n";

    PullRequest pullRequest(
        42,
        "Harden payment authorization",
        "alice",
        "feature/payment-auth",
        "main",
        {
            {"abc123", "Implement payment authorization"}
        }
    );

    // The external CI system is intentionally not exposed to the governance
    // service. Only the StatusProvider interface is visible to it.
    ExternalCiClient externalCi;
    CiAdapter ciAdapter(externalCi);

    EventBus eventBus;

    auto audit = std::make_shared<AuditObserver>();
    auto metrics = std::make_shared<MetricsObserver>();
    auto notifications = std::make_shared<NotificationObserver>();

    eventBus.subscribe(audit);
    eventBus.subscribe(metrics);
    eventBus.subscribe(notifications);

    ProductionMergeStrategy productionPolicy(
        {"bob", "carol", "david"},
        2
    );

    GovernanceService service(
        productionPolicy,
        ciAdapter,
        eventBus
    );

    eventBus.publish({
        "review_requested",
        42,
        "alice",
        "Review requested from bob and carol."
    });

    service.synchronizeCi(pullRequest, "ci-bot");

    pullRequest.addReview({
        "bob",
        ReviewDecision::Approve,
        pullRequest.headSha(),
        "Authorization boundaries are clear."
    });

    auto firstDecision = service.evaluate(pullRequest);

    std::cout
        << "\nProduction eligibility after one approval: "
        << (firstDecision.allowed ? "allowed" : "blocked")
        << '\n';

    for (const auto& reason : firstDecision.reasons) {
        std::cout << "  - " << reason << '\n';
    }

    pullRequest.addReview({
        "carol",
        ReviewDecision::Approve,
        pullRequest.headSha(),
        "Policy and failure handling are acceptable."
    });

    auto secondDecision = service.evaluate(pullRequest);

    std::cout
        << "\nProduction eligibility after two approvals: "
        << (secondDecision.allowed ? "allowed" : "blocked")
        << '\n';

    service.merge(pullRequest, "release-bot");

    std::cout << "\nFinal Pull Request state: "
              << toString(pullRequest.state())
              << '\n';

    std::cout << "\nEvent metrics:\n";
    metrics->print();

    // Adapter edge case: an unknown revision becomes pending rather than
    // passing, protecting the merge policy against fail-open behavior.
    const auto unknownStatus = ciAdapter.getStatus("unknown-sha");

    std::cout
        << "\nUnknown CI revision: "
        << toString(unknownStatus.status)
        << '\n';

    return 0;
}
