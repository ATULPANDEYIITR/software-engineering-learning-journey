#include <algorithm>
#include <chrono>
#include <exception>
#include <iomanip>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

using Clock = std::chrono::steady_clock;

enum class ReviewState {
    Draft,
    Open,
    Approved,
    ChangesRequested,
    Merged,
    Closed
};

enum class CheckState {
    Pending,
    Passed,
    Failed
};

struct Commit {
    std::string sha;
    std::string message;
};

struct StatusCheck {
    std::string name;
    CheckState state;
};

struct Review {
    std::string reviewer;
    ReviewState state;
    bool stale{false};
};

struct BranchProtectionPolicy {
    bool requireApproval{true};
    int requiredApprovals{2};
    bool requireSuccessfulChecks{true};
    bool forbidDirectPush{true};
    bool forbidForcePush{true};
    bool requireConversationResolution{true};
};

struct PullRequest {
    int id;
    std::string sourceBranch;
    std::string targetBranch;
    std::vector<Commit> commits;
    std::vector<Review> reviews;
    std::vector<StatusCheck> checks;
    int unresolvedConversations{0};
    bool draft{false};
    bool open{true};
    bool sourceSynchronized{true};
};

class RepositoryGovernanceEngine {
private:
    std::unordered_map<std::string, BranchProtectionPolicy> policies;

    static bool hasRequiredApprovals(const PullRequest& pr,
                                     const BranchProtectionPolicy& policy) {
        std::unordered_set<std::string> eligibleReviewers;

        for (const auto& review : pr.reviews) {
            if (!review.stale &&
                review.state == ReviewState::Approved) {
                eligibleReviewers.insert(review.reviewer);
            }
        }

        return static_cast<int>(eligibleReviewers.size()) >=
               policy.requiredApprovals;
    }

    static bool checksPassed(const PullRequest& pr) {
        if (pr.checks.empty()) {
            return false;
        }

        return std::all_of(
            pr.checks.begin(),
            pr.checks.end(),
            [](const StatusCheck& check) {
                return check.state == CheckState::Passed;
            });
    }

public:
    void protectBranch(const std::string& branch,
                        const BranchProtectionPolicy& policy) {
        if (branch.empty()) {
            throw std::invalid_argument("Branch name cannot be empty");
        }

        if (policy.requiredApprovals < 0) {
            throw std::invalid_argument(
                "Required approvals cannot be negative");
        }

        policies[branch] = policy;
    }

    bool canMerge(const PullRequest& pr, std::vector<std::string>& reasons) const {
        reasons.clear();

        if (!pr.open) {
            reasons.push_back("Pull Request is not open");
        }

        if (pr.draft) {
            reasons.push_back("Draft Pull Requests are not mergeable");
        }

        if (pr.sourceBranch.empty() || pr.targetBranch.empty()) {
            reasons.push_back("Source and target branches are required");
        }

        if (pr.commits.empty()) {
            reasons.push_back("Pull Request contains no commits");
        }

        auto policyIt = policies.find(pr.targetBranch);
        if (policyIt == policies.end()) {
            reasons.push_back("Target branch has no protection policy");
            return reasons.empty();
        }

        const auto& policy = policyIt->second;

        if (!pr.sourceSynchronized) {
            reasons.push_back("Source branch is behind the target branch");
        }

        if (policy.requireApproval &&
            !hasRequiredApprovals(pr, policy)) {
            reasons.push_back("Required non-stale approvals are missing");
        }

        if (policy.requireSuccessfulChecks && !checksPassed(pr)) {
            reasons.push_back("Required status checks have not all passed");
        }

        if (policy.requireConversationResolution &&
            pr.unresolvedConversations > 0) {
            reasons.push_back("Unresolved review conversations remain");
        }

        return reasons.empty();
    }

    bool merge(PullRequest& pr) const {
        std::vector<std::string> reasons;

        if (!canMerge(pr, reasons)) {
            return false;
        }

        pr.open = false;
        return true;
    }
};

static void printDecision(const RepositoryGovernanceEngine& engine,
                          const PullRequest& pr) {
    std::vector<std::string> reasons;

    if (engine.canMerge(pr, reasons)) {
        std::cout << "PR #" << pr.id << " is merge-eligible\n";
    } else {
        std::cout << "PR #" << pr.id << " is NOT merge-eligible\n";
        for (const auto& reason : reasons) {
            std::cout << "  - " << reason << '\n';
        }
    }
}

int main() {
    try {
        RepositoryGovernanceEngine engine;

        BranchProtectionPolicy mainPolicy;
        mainPolicy.requiredApprovals = 2;
        mainPolicy.requireSuccessfulChecks = true;
        mainPolicy.forbidDirectPush = true;
        mainPolicy.forbidForcePush = true;
        mainPolicy.requireConversationResolution = true;

        engine.protectBranch("main", mainPolicy);

        PullRequest pr{
            501,
            "feature/cache-aside",
            "main",
            {
                {"a1b2c3", "Add cache-aside repository service"},
                {"d4e5f6", "Add TTL expiration handling"}
            },
            {
                {"reviewer-1", ReviewState::Approved, false},
                {"reviewer-2", ReviewState::Approved, false}
            },
            {
                {"unit-tests", CheckState::Passed},
                {"integration-tests", CheckState::Passed},
                {"security-scan", CheckState::Passed}
            },
            0,
            false,
            true,
            true
        };

        printDecision(engine, pr);

        if (engine.merge(pr)) {
            std::cout << "PR #" << pr.id << " merged successfully\n";
        }

        PullRequest staleApprovalPr{
            502,
            "feature/cache-invalidation",
            "main",
            {
                {"111aaa", "Add explicit invalidation"}
            },
            {
                {"reviewer-1", ReviewState::Approved, true},
                {"reviewer-2", ReviewState::Approved, false}
            },
            {
                {"unit-tests", CheckState::Passed},
                {"integration-tests", CheckState::Passed},
                {"security-scan", CheckState::Passed}
            },
            0,
            false,
            true,
            true
        };

        printDecision(engine, staleApprovalPr);

        PullRequest failedCheckPr{
            503,
            "feature/cache-refresh",
            "main",
            {
                {"222bbb", "Add cache refresh workflow"}
            },
            {
                {"reviewer-1", ReviewState::Approved, false},
                {"reviewer-2", ReviewState::Approved, false}
            },
            {
                {"unit-tests", CheckState::Passed},
                {"integration-tests", CheckState::Failed},
                {"security-scan", CheckState::Passed}
            },
            0,
            false,
            true,
            true
        };

        printDecision(engine, failedCheckPr);

        PullRequest unresolvedPr{
            504,
            "feature/cache-policy",
            "main",
            {
                {"333ccc", "Add cache policy validation"}
            },
            {
                {"reviewer-1", ReviewState::Approved, false},
                {"reviewer-2", ReviewState::Approved, false}
            },
            {
                {"unit-tests", CheckState::Passed},
                {"integration-tests", CheckState::Passed},
                {"security-scan", CheckState::Passed}
            },
            2,
            false,
            true,
            true
        };

        printDecision(engine, unresolvedPr);

        std::cout << "\nGovernance model demonstrates:\n"
                  << "- Pull Request state\n"
                  << "- review and approval state\n"
                  << "- stale approvals\n"
                  << "- status checks\n"
                  << "- protected target branches\n"
                  << "- conversation requirements\n"
                  << "- final merge eligibility\n";

    } catch (const std::exception& ex) {
        std::cerr << "Fatal error: " << ex.what() << '\n';
        return 1;
    }

    return 0;
}
