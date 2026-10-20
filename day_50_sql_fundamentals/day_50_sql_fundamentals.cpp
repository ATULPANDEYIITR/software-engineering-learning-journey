#include <algorithm>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

enum class PullRequestState {
    Open,
    Closed,
    Merged
};

enum class ReviewState {
    Approved,
    ChangesRequested,
    Commented
};

enum class CheckState {
    Passing,
    Failing,
    Pending
};

struct Review {
    std::string reviewer;
    ReviewState state;
    std::string comment;
};

struct StatusCheck {
    std::string name;
    CheckState state;
};

struct BranchProtection {
    std::string branch;
    int requiredApprovals = 0;
    std::set<std::string> requiredChecks;
    bool restrictDirectPush = true;
    bool restrictForcePush = true;
    bool requireConversationResolution = true;
    bool requireLinearHistory = false;
};

struct PullRequest {
    int number;
    std::string title;
    std::string sourceBranch;
    std::string targetBranch;
    std::string author;
    PullRequestState state = PullRequestState::Open;
    bool draft = false;
    std::vector<std::string> commits;
    std::vector<Review> reviews;
    std::map<std::string, CheckState> checks;
};

class GovernanceEngine {
private:
    std::map<std::string, std::string> branches;
    std::map<int, PullRequest> pullRequests;
    std::map<std::string, BranchProtection> protections;
    int nextPullRequest = 1;

    static bool validBranchName(const std::string& branch) {
        return !branch.empty() &&
               branch.find(' ') == std::string::npos;
    }

public:
    GovernanceEngine() {
        branches["main"] = "c100";
        branches["feature/sql-crud"] = "c104";
    }

    void protectBranch(const BranchProtection& policy) {
        if (!validBranchName(policy.branch)) {
            throw std::invalid_argument("Invalid protected branch name.");
        }

        if (policy.requiredApprovals < 0) {
            throw std::invalid_argument(
                "Required approvals cannot be negative."
            );
        }

        protections[policy.branch] = policy;
    }

    int createPullRequest(
        const std::string& title,
        const std::string& source,
        const std::string& target,
        const std::string& author,
        bool draft = false
    ) {
        if (title.empty() || author.empty()) {
            throw std::invalid_argument(
                "Title and author are required."
            );
        }

        if (!branches.count(source) || !branches.count(target)) {
            throw std::invalid_argument("Unknown source or target branch.");
        }

        if (source == target) {
            throw std::invalid_argument(
                "Source and target branches must differ."
            );
        }

        PullRequest pr{
            nextPullRequest++,
            title,
            source,
            target,
            author,
            PullRequestState::Open,
            draft
        };

        pullRequests.emplace(pr.number, std::move(pr));
        return nextPullRequest - 1;
    }

    void addCommit(int prNumber, const std::string& commitId) {
        auto& pr = getPullRequest(prNumber);

        if (pr.state == PullRequestState::Closed) {
            throw std::logic_error(
                "Closed pull requests cannot receive commits."
            );
        }

        if (commitId.empty()) {
            throw std::invalid_argument("Commit ID cannot be empty.");
        }

        if (std::find(
                pr.commits.begin(),
                pr.commits.end(),
                commitId
            ) == pr.commits.end()) {
            pr.commits.push_back(commitId);
        }
    }

    void addReview(
        int prNumber,
        const std::string& reviewer,
        ReviewState state,
        const std::string& comment
    ) {
        auto& pr = getPullRequest(prNumber);

        if (reviewer == pr.author &&
            state == ReviewState::Approved) {
            throw std::logic_error(
                "Authors cannot approve their own pull request."
            );
        }

        pr.reviews.push_back(
            Review{reviewer, state, comment}
        );
    }

    void setStatusCheck(
        int prNumber,
        const std::string& name,
        CheckState state
    ) {
        if (name.empty()) {
            throw std::invalid_argument(
                "Status-check name cannot be empty."
            );
        }

        auto& pr = getPullRequest(prNumber);
        pr.checks[name] = state;
    }

    std::pair<bool, std::vector<std::string>>
    evaluateMerge(int prNumber) const {
        const auto& pr = getPullRequest(prNumber);
        std::vector<std::string> failures;

        auto protection = protections.find(pr.targetBranch);

        if (protection == protections.end()) {
            return {true, failures};
        }

        const auto& policy = protection->second;

        if (pr.state != PullRequestState::Open) {
            failures.push_back("Pull request is not open.");
        }

        if (pr.draft) {
            failures.push_back("Draft pull requests cannot be merged.");
        }

        std::set<std::string> uniqueApprovers;

        for (const auto& review : pr.reviews) {
            if (review.state == ReviewState::Approved) {
                uniqueApprovers.insert(review.reviewer);
            }
        }

        if (static_cast<int>(uniqueApprovers.size()) <
            policy.requiredApprovals) {
            failures.push_back(
                "Insufficient unique approvals."
            );
        }

        for (const auto& required : policy.requiredChecks) {
            auto check = pr.checks.find(required);

            if (check == pr.checks.end() ||
                check->second != CheckState::Passing) {
                failures.push_back(
                    "Required check is not passing: " + required
                );
            }
        }

        if (policy.requireConversationResolution) {
            const auto unresolved = std::count_if(
                pr.reviews.begin(),
                pr.reviews.end(),
                [](const Review& review) {
                    return review.state ==
                           ReviewState::ChangesRequested;
                }
            );

            if (unresolved > 0) {
                failures.push_back(
                    "Review discussions still require resolution."
                );
            }
        }

        return {failures.empty(), failures};
    }

    void merge(int prNumber) {
        auto decision = evaluateMerge(prNumber);

        if (!decision.first) {
            std::string message = "Merge blocked:";
            for (const auto& failure : decision.second) {
                message += "\n - " + failure;
            }
            throw std::logic_error(message);
        }

        auto& pr = getPullRequest(prNumber);
        branches[pr.targetBranch] = branches.at(pr.sourceBranch);
        pr.state = PullRequestState::Merged;
    }

    void printPullRequest(int prNumber) const {
        const auto& pr = getPullRequest(prNumber);

        std::cout
            << "PR #" << pr.number
            << "\nTitle: " << pr.title
            << "\nSource: " << pr.sourceBranch
            << "\nTarget: " << pr.targetBranch
            << "\nAuthor: " << pr.author
            << "\nCommits: " << pr.commits.size()
            << "\nReviews: " << pr.reviews.size()
            << "\n";
    }

private:
    PullRequest& getPullRequest(int number) {
        auto it = pullRequests.find(number);

        if (it == pullRequests.end()) {
            throw std::out_of_range(
                "Pull request does not exist."
            );
        }

        return it->second;
    }

    const PullRequest& getPullRequest(int number) const {
        auto it = pullRequests.find(number);

        if (it == pullRequests.end()) {
            throw std::out_of_range(
                "Pull request does not exist."
            );
        }

        return it->second;
    }
};

int main() {
    try {
        GovernanceEngine engine;

        engine.protectBranch(
            BranchProtection{
                "main",
                2,
                {"unit-tests", "sql-validation"},
                true,
                true,
                true,
                false
            }
        );

        int pr = engine.createPullRequest(
            "Add safe SQL CRUD examples",
            "feature/sql-crud",
            "main",
            "developer"
        );

        engine.addCommit(pr, "a81f2d");
        engine.addCommit(pr, "b93c10");

        engine.addReview(
            pr,
            "alice",
            ReviewState::Approved,
            "CRUD constraints are clear."
        );

        engine.addReview(
            pr,
            "bob",
            ReviewState::Approved,
            "Transaction handling is valid."
        );

        engine.setStatusCheck(
            pr,
            "unit-tests",
            CheckState::Passing
        );

        engine.setStatusCheck(
            pr,
            "sql-validation",
            CheckState::Passing
        );

        engine.printPullRequest(pr);

        auto decision = engine.evaluateMerge(pr);

        std::cout
            << "\nMerge eligible: "
            << (decision.first ? "yes" : "no")
            << "\n";

        if (!decision.first) {
            for (const auto& failure : decision.second) {
                std::cout << "Blocked: " << failure << "\n";
            }
        } else {
            engine.merge(pr);
            std::cout << "Pull request merged successfully.\n";
        }
    }
    catch (const std::exception& error) {
        std::cerr
            << "Operation failed: "
            << error.what()
            << '\n';
        return 1;
    }

    return 0;
}
