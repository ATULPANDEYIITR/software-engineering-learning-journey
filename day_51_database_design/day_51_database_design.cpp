#include <algorithm>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
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
    std::string author;
};

struct Review {
    std::string reviewer;
    ReviewState state;
    std::string commitSha;
    std::vector<std::string> comments;
};

struct StatusCheck {
    std::string name;
    bool passed;
};

struct BranchProtection {
    std::string branch;
    std::size_t requiredApprovals{1};
    std::set<std::string> requiredChecks;
    bool requireConversationResolution{true};
    bool requireLinearHistory{false};
    bool allowDirectPush{false};
    bool allowForcePush{false};
    bool allowDeletion{false};
    std::set<std::string> bypassUsers;
};

struct Evaluation {
    bool eligible{false};
    std::vector<std::string> failures;
};

class PullRequest {
private:
    int number_;
    std::string sourceBranch_;
    std::string targetBranch_;
    std::string author_;
    std::string title_;
    PRState state_{PRState::Draft};
    std::vector<Commit> commits_;
    std::set<std::string> reviewers_;
    std::vector<Review> reviews_;
    std::map<std::string, StatusCheck> checks_;
    std::map<int, bool> conversations_;
    std::optional<MergeStrategy> mergeStrategy_;

public:
    PullRequest(
        int number,
        std::string sourceBranch,
        std::string targetBranch,
        std::string author,
        std::string title
    )
        : number_(number),
          sourceBranch_(std::move(sourceBranch)),
          targetBranch_(std::move(targetBranch)),
          author_(std::move(author)),
          title_(std::move(title)) {
        if (number_ <= 0 || sourceBranch_.empty() ||
            targetBranch_.empty() || author_.empty()) {
            throw std::invalid_argument("Invalid Pull Request metadata.");
        }
    }

    void addCommit(Commit commit) {
        if (state_ == PRState::Closed || state_ == PRState::Merged) {
            throw std::logic_error("Closed or merged Pull Requests are immutable.");
        }

        if (commit.sha.empty()) {
            throw std::invalid_argument("Commit SHA cannot be empty.");
        }

        const auto duplicate = std::find_if(
            commits_.begin(),
            commits_.end(),
            [&](const Commit& existing) {
                return existing.sha == commit.sha;
            }
        );

        if (duplicate != commits_.end()) {
            throw std::invalid_argument("Duplicate commit SHA.");
        }

        commits_.push_back(std::move(commit));
    }

    void requestReview(const std::string& reviewer) {
        if (reviewer.empty() || reviewer == author_) {
            throw std::invalid_argument(
                "Author cannot be the requested reviewer for their own Pull Request."
            );
        }
        reviewers_.insert(reviewer);
    }

    void addReview(
        const std::string& reviewer,
        ReviewState state,
        const std::string& commitSha,
        std::vector<std::string> comments = {}
    ) {
        if (!reviewers_.contains(reviewer)) {
            throw std::invalid_argument("Reviewer was not requested.");
        }

        const bool commitExists = std::any_of(
            commits_.begin(),
            commits_.end(),
            [&](const Commit& commit) {
                return commit.sha == commitSha;
            }
        );

        if (!commitExists) {
            throw std::invalid_argument("Review references an unknown commit.");
        }

        reviews_.push_back({
            reviewer,
            state,
            commitSha,
            std::move(comments)
        });
    }

    void setStatusCheck(std::string name, bool passed) {
        if (name.empty()) {
            throw std::invalid_argument("Status-check name cannot be empty.");
        }
        checks_[name] = {std::move(name), passed};
    }

    void addConversation(int id, bool resolved) {
        if (id <= 0) {
            throw std::invalid_argument("Conversation ID must be positive.");
        }
        conversations_[id] = resolved;
    }

    void open() {
        if (state_ != PRState::Draft) {
            throw std::logic_error("Only draft Pull Requests can be opened.");
        }
        state_ = PRState::Open;
    }

    void close() {
        if (state_ == PRState::Merged) {
            throw std::logic_error("Merged Pull Requests cannot be closed.");
        }
        state_ = PRState::Closed;
    }

    void reopen() {
        if (state_ != PRState::Closed) {
            throw std::logic_error("Only closed Pull Requests can be reopened.");
        }
        state_ = PRState::Open;
    }

    int number() const {
        return number_;
    }

    const std::string& author() const {
        return author_;
    }

    const std::string& targetBranch() const {
        return targetBranch_;
    }

    PRState state() const {
        return state_;
    }

    void setMerged(MergeStrategy strategy) {
        mergeStrategy_ = strategy;
        state_ = PRState::Merged;
    }

    std::optional<std::string> latestCommitSha() const {
        if (commits_.empty()) {
            return std::nullopt;
        }
        return commits_.back().sha;
    }

    const std::set<std::string>& reviewers() const {
        return reviewers_;
    }

    const std::vector<Review>& reviews() const {
        return reviews_;
    }

    const std::map<std::string, StatusCheck>& checks() const {
        return checks_;
    }

    const std::map<int, bool>& conversations() const {
        return conversations_;
    }

    std::optional<MergeStrategy> mergeStrategy() const {
        return mergeStrategy_;
    }
};

class GovernanceEngine {
private:
    std::map<std::string, BranchProtection> protections_;

public:
    void protect(BranchProtection policy) {
        if (policy.branch.empty()) {
            throw std::invalid_argument("Protected branch must have a name.");
        }
        protections_[policy.branch] = std::move(policy);
    }

    Evaluation evaluate(const PullRequest& pr) const {
        Evaluation result;

        if (pr.state() != PRState::Open) {
            result.failures.push_back("Pull Request is not open.");
        }

        const auto latestSha = pr.latestCommitSha();
        if (!latestSha.has_value()) {
            result.failures.push_back("Pull Request contains no commits.");
        }

        const auto policyIt = protections_.find(pr.targetBranch());
        if (policyIt == protections_.end()) {
            result.failures.push_back(
                "Target branch has no protection policy."
            );
            return result;
        }

        const BranchProtection& policy = policyIt->second;

        // Explicit bypass is evaluated before normal merge requirements.
        if (policy.bypassUsers.contains(pr.author())) {
            result.eligible = true;
            return result;
        }

        std::set<std::string> currentApprovers;

        if (latestSha.has_value()) {
            for (const Review& review : pr.reviews()) {
                if (review.state == ReviewState::Approved &&
                    review.commitSha == latestSha.value() &&
                    pr.reviewers().contains(review.reviewer) &&
                    review.reviewer != pr.author()) {
                    currentApprovers.insert(review.reviewer);
                }
            }
        }

        if (currentApprovers.size() < policy.requiredApprovals) {
            std::ostringstream message;
            message << "Required approvals: "
                    << policy.requiredApprovals
                    << "; current approvals: "
                    << currentApprovers.size()
                    << ".";
            result.failures.push_back(message.str());
        }

        for (const std::string& requiredCheck : policy.requiredChecks) {
            const auto checkIt = pr.checks().find(requiredCheck);

            if (checkIt == pr.checks().end() || !checkIt->second.passed) {
                result.failures.push_back(
                    "Required status check failed or is missing: " +
                    requiredCheck
                );
            }
        }

        if (policy.requireConversationResolution) {
            for (const auto& [id, resolved] : pr.conversations()) {
                if (!resolved) {
                    result.failures.push_back(
                        "Unresolved review conversation: " +
                        std::to_string(id)
                    );
                }
            }
        }

        if (policy.requireLinearHistory &&
            pr.mergeStrategy().has_value() &&
            pr.mergeStrategy().value() == MergeStrategy::MergeCommit) {
            result.failures.push_back(
                "Merge commits are prohibited by linear-history policy."
            );
        }

        result.eligible = result.failures.empty();
        return result;
    }

    void merge(PullRequest& pr, MergeStrategy strategy) const {
        // Set the candidate strategy before evaluation so policy can reject
        // an incompatible merge method.
        const Evaluation beforeMerge = evaluate(pr);

        if (!beforeMerge.eligible) {
            std::ostringstream message;
            message << "Merge blocked:";
            for (const auto& failure : beforeMerge.failures) {
                message << "\n- " << failure;
            }
            throw std::runtime_error(message.str());
        }

        pr.setMerged(strategy);
    }
};

static const char* stateName(PRState state) {
    switch (state) {
        case PRState::Draft: return "draft";
        case PRState::Open: return "open";
        case PRState::Closed: return "closed";
        case PRState::Merged: return "merged";
    }
    return "unknown";
}

int main() {
    try {
        GovernanceEngine engine;

        engine.protect({
            "main",
            2,
            {"unit-tests", "security-scan"},
            true,
            true,
            false,
            false,
            false,
            {}
        });

        PullRequest pr(
            105,
            "feature/invoice-validation",
            "main",
            "alice",
            "Validate invoice boundaries"
        );

        pr.addCommit({"d001", "Add invoice validation", "alice"});
        pr.addCommit({"d002", "Add boundary tests", "alice"});

        pr.requestReview("bob");
        pr.requestReview("carol");
        pr.open();

        pr.setStatusCheck("unit-tests", true);
        pr.setStatusCheck("security-scan", true);

        pr.addConversation(201, true);
        pr.addConversation(202, false);

        pr.addReview(
            "bob",
            ReviewState::Approved,
            "d002"
        );

        Evaluation first = engine.evaluate(pr);

        std::cout << "Initial eligibility: "
                  << (first.eligible ? "eligible" : "blocked")
                  << "\n";

        for (const auto& failure : first.failures) {
            std::cout << "  - " << failure << "\n";
        }

        // A new commit makes approvals tied to d002 stale.
        pr.addCommit({"d003", "Reject negative invoice totals", "alice"});
        pr.addConversation(202, true);

        Evaluation second = engine.evaluate(pr);

        std::cout << "\nAfter synchronization: "
                  << (second.eligible ? "eligible" : "blocked")
                  << "\n";

        for (const auto& failure : second.failures) {
            std::cout << "  - " << failure << "\n";
        }

        pr.addReview(
            "bob",
            ReviewState::Approved,
            "d003"
        );

        pr.addReview(
            "carol",
            ReviewState::Approved,
            "d003"
        );

        Evaluation finalEvaluation = engine.evaluate(pr);

        std::cout << "\nFinal eligibility: "
                  << (finalEvaluation.eligible ? "eligible" : "blocked")
                  << "\n";

        if (finalEvaluation.eligible) {
            engine.merge(pr, MergeStrategy::Rebase);
        }

        std::cout << "Final Pull Request state: "
                  << stateName(pr.state())
                  << "\n";

    } catch (const std::exception& error) {
        std::cerr << "Governance error: "
                  << error.what()
                  << "\n";
        return 1;
    }

    return 0;
}
