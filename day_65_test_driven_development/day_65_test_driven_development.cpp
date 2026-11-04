#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace std;

// ============================================================
// ENUMERATIONS
// ============================================================

enum class ReviewDecision {
    Pending,
    Approved,
    ChangesRequested,
    Commented
};

enum class CheckStatus {
    Missing,
    Passed,
    Failed
};

enum class MergeStrategy {
    MergeCommit,
    Squash,
    Rebase
};

enum class PullRequestState {
    Draft,
    Open,
    Closed,
    Merged
};

// ============================================================
// DOMAIN STRUCTURES
// ============================================================

struct Commit {
    string hash;
    string message;

    Commit(string hash, string message)
        : hash(move(hash)), message(move(message)) {
        if (this->hash.empty() || this->message.empty()) {
            throw invalid_argument("Invalid commit.");
        }
    }
};

struct Review {
    string reviewer;
    ReviewDecision decision;
    bool eligible;
    bool stale;
    bool dismissed;

    Review(
        string reviewer,
        ReviewDecision decision,
        bool eligible = true
    )
        : reviewer(move(reviewer)),
          decision(decision),
          eligible(eligible),
          stale(false),
          dismissed(false) {}
};

struct StatusCheck {
    string name;
    CheckStatus status;
};

struct Branch {
    string name;
    bool protectedBranch;
    bool allowsDirectPush;
    bool allowsForcePush;
    bool allowsDeletion;
    int commitCount;

    Branch(
        string name,
        bool protectedBranch = false,
        bool directPush = true,
        bool forcePush = true,
        bool deletion = true
    )
        : name(move(name)),
          protectedBranch(protectedBranch),
          allowsDirectPush(directPush),
          allowsForcePush(forcePush),
          allowsDeletion(deletion),
          commitCount(0) {}
};

struct ProtectionPolicy {
    int requiredApprovals = 1;
    set<string> requiredChecks;
    bool requireResolvedConversations = true;
    bool requireLinearHistory = false;
    bool requireSynchronizedBase = true;
    bool allowAdministratorBypass = false;
};

// ============================================================
// PULL REQUEST
// ============================================================

class PullRequest {
private:
    string id;
    string sourceBranch;
    string targetBranch;

    vector<Commit> commits;
    map<string, Review> reviews;
    map<string, StatusCheck> checks;
    set<string> unresolvedConversations;

    PullRequestState state = PullRequestState::Draft;

    bool baseSynchronized = true;
    bool linearHistory = true;

public:
    PullRequest(
        string id,
        string sourceBranch,
        string targetBranch
    )
        : id(move(id)),
          sourceBranch(move(sourceBranch)),
          targetBranch(move(targetBranch)) {

        if (
            this->id.empty() ||
            this->sourceBranch.empty() ||
            this->targetBranch.empty()
        ) {
            throw invalid_argument("Invalid pull request.");
        }

        if (this->sourceBranch == this->targetBranch) {
            throw invalid_argument(
                "Source and target branches must differ."
            );
        }
    }

    const string& getId() const {
        return id;
    }

    PullRequestState getState() const {
        return state;
    }

    void addCommit(const Commit& commit) {
        if (state == PullRequestState::Merged ||
            state == PullRequestState::Closed) {
            throw logic_error("Cannot modify a closed pull request.");
        }

        auto duplicate = find_if(
            commits.begin(),
            commits.end(),
            [&](const Commit& existing) {
                return existing.hash == commit.hash;
            }
        );

        if (duplicate != commits.end()) {
            throw invalid_argument("Duplicate commit.");
        }

        commits.push_back(commit);

        // A new commit makes previous approvals stale.
        for (auto& entry : reviews) {
            if (entry.second.decision == ReviewDecision::Approved) {
                entry.second.stale = true;
            }
        }
    }

    void open() {
        if (state != PullRequestState::Draft) {
            throw logic_error("Only draft requests can be opened.");
        }

        if (commits.empty()) {
            throw logic_error("A pull request requires commits.");
        }

        state = PullRequestState::Open;
    }

    void close() {
        if (state != PullRequestState::Open &&
            state != PullRequestState::Draft) {
            throw logic_error("Request cannot be closed.");
        }

        state = PullRequestState::Closed;
    }

    void reopen() {
        if (state != PullRequestState::Closed) {
            throw logic_error("Only closed requests can reopen.");
        }

        state = PullRequestState::Open;
    }

    void synchronizeBase() {
        if (state != PullRequestState::Open) {
            throw logic_error("Request must be open.");
        }

        baseSynchronized = true;

        // Synchronization can require a fresh review.
        for (auto& entry : reviews) {
            if (entry.second.decision == ReviewDecision::Approved) {
                entry.second.stale = true;
            }
        }
    }

    void markBaseOutdated() {
        baseSynchronized = false;
    }

    void setLinearHistory(bool value) {
        linearHistory = value;
    }

    void addReview(const Review& review) {
        if (state != PullRequestState::Open) {
            throw logic_error("Reviews require an open request.");
        }

        if (!review.eligible) {
            throw invalid_argument("Reviewer is not eligible.");
        }

        reviews[review.reviewer] = review;
    }

    void dismissReview(const string& reviewer) {
        auto it = reviews.find(reviewer);

        if (it == reviews.end()) {
            throw invalid_argument("Review does not exist.");
        }

        it->second.dismissed = true;
    }

    void addCheck(const string& name, CheckStatus status) {
        if (name.empty()) {
            throw invalid_argument("Check name cannot be empty.");
        }

        checks[name] = {name, status};
    }

    void addConversation(const string& conversationId) {
        unresolvedConversations.insert(conversationId);
    }

    void resolveConversation(const string& conversationId) {
        if (unresolvedConversations.erase(conversationId) == 0) {
            throw invalid_argument("Conversation does not exist.");
        }
    }

    int validApprovals() const {
        int count = 0;

        for (const auto& entry : reviews) {
            const Review& review = entry.second;

            if (
                review.eligible &&
                !review.stale &&
                !review.dismissed &&
                review.decision == ReviewDecision::Approved
            ) {
                ++count;
            }
        }

        return count;
    }

    bool hasRequestedChanges() const {
        return any_of(
            reviews.begin(),
            reviews.end(),
            [](const auto& entry) {
                const Review& review = entry.second;

                return review.eligible &&
                       !review.stale &&
                       !review.dismissed &&
                       review.decision == ReviewDecision::ChangesRequested;
            }
        );
    }

    const map<string, StatusCheck>& getChecks() const {
        return checks;
    }

    const set<string>& getConversations() const {
        return unresolvedConversations;
    }

    bool isBaseSynchronized() const {
        return baseSynchronized;
    }

    bool hasLinearHistory() const {
        return linearHistory;
    }

    size_t commitCount() const {
        return commits.size();
    }

    void markMerged() {
        state = PullRequestState::Merged;
    }
};

// ============================================================
// GOVERNANCE ENGINE
// ============================================================

struct EligibilityResult {
    bool eligible = false;
    vector<string> reasons;
    int approvalCount = 0;
};

class GovernanceEngine {
public:
    EligibilityResult evaluate(
        const PullRequest& request,
        const Branch& target,
        const ProtectionPolicy& policy,
        bool administrator = false
    ) const {

        EligibilityResult result;

        result.approvalCount = request.validApprovals();

        if (request.getState() != PullRequestState::Open) {
            result.reasons.push_back("Pull request is not open.");
        }

        if (request.commitCount() == 0) {
            result.reasons.push_back("No commits are available.");
        }

        if (!target.protectedBranch) {
            result.reasons.push_back(
                "Target branch has no protection policy."
            );
        }

        if (result.approvalCount < policy.requiredApprovals) {
            result.reasons.push_back("Required approvals are missing.");
        }

        if (request.hasRequestedChanges()) {
            result.reasons.push_back("Changes have been requested.");
        }

        for (const string& required : policy.requiredChecks) {
            auto it = request.getChecks().find(required);

            if (
                it == request.getChecks().end() ||
                it->second.status != CheckStatus::Passed
            ) {
                result.reasons.push_back(
                    "Required check not passed: " + required
                );
            }
        }

        if (
            policy.requireResolvedConversations &&
            !request.getConversations().empty()
        ) {
            result.reasons.push_back(
                "Review conversations remain unresolved."
            );
        }

        if (
            policy.requireSynchronizedBase &&
            !request.isBaseSynchronized()
        ) {
            result.reasons.push_back(
                "Source branch must be synchronized."
            );
        }

        if (
            policy.requireLinearHistory &&
            !request.hasLinearHistory()
        ) {
            result.reasons.push_back(
                "Linear history is required."
            );
        }

        if (administrator && !policy.allowAdministratorBypass) {
            result.reasons.push_back(
                "Administrator bypass is not permitted."
            );
        }

        bool bypass = administrator &&
                      policy.allowAdministratorBypass;

        result.eligible = result.reasons.empty() || bypass;

        if (bypass && result.eligible) {
            result.reasons.clear();
            result.reasons.push_back(
                "Authorized administrator bypass."
            );
        }

        return result;
    }

    void merge(
        PullRequest& request,
        const Branch& target,
        const ProtectionPolicy& policy,
        MergeStrategy strategy,
        bool administrator = false
    ) const {

        EligibilityResult result = evaluate(
            request,
            target,
            policy,
            administrator
        );

        if (!result.eligible) {
            string message = "Merge rejected:";

            for (const string& reason : result.reasons) {
                message += "\n- " + reason;
            }

            throw runtime_error(message);
        }

        if (
            strategy == MergeStrategy::Rebase &&
            policy.requireLinearHistory &&
            !request.hasLinearHistory()
        ) {
            throw runtime_error("Rebase history validation failed.");
        }

        request.markMerged();
    }
};

// ============================================================
// RED-GREEN-REFACTOR TEST FRAMEWORK
// ============================================================

struct TestResult {
    string name;
    bool passed;
    string message;
    double durationMs;
};

class TestSuite {
private:
    vector<pair<string, function<void()>>> tests;
    vector<TestResult> results;

public:
    void add(const string& name, function<void()> test) {
        if (name.empty() || !test) {
            throw invalid_argument("Invalid test registration.");
        }

        tests.push_back({name, move(test)});
    }

    void run() {
        results.clear();

        for (const auto& test : tests) {
            auto start = chrono::steady_clock::now();

            try {
                test.second();

                auto end = chrono::steady_clock::now();

                double duration = chrono::duration<double, milli>(
                    end - start
                ).count();

                results.push_back({
                    test.first,
                    true,
                    "",
                    duration
                });

            } catch (const exception& error) {
                auto end = chrono::steady_clock::now();

                double duration = chrono::duration<double, milli>(
                    end - start
                ).count();

                results.push_back({
                    test.first,
                    false,
                    error.what(),
                    duration
                });
            }
        }
    }

    int passed() const {
        return count_if(
            results.begin(),
            results.end(),
            [](const TestResult& result) {
                return result.passed;
            }
        );
    }

    int failed() const {
        return static_cast<int>(results.size()) - passed();
    }

    void print() const {
        cout << "\nTEST RESULTS\n";

        for (const auto& result : results) {
            cout << (result.passed ? "[PASS] " : "[FAIL] ")
                 << result.name
                 << " (" << fixed << setprecision(3)
                 << result.durationMs << " ms)";

            if (!result.passed) {
                cout << " : " << result.message;
            }

            cout << '\n';
        }

        cout << "\nPassed: " << passed()
             << "\nFailed: " << failed()
             << "\nTotal: " << results.size()
             << '\n';
    }
};

void require(bool condition, const string& message) {
    if (!condition) {
        throw runtime_error(message);
    }
}

// ============================================================
// INTEGRATION SCENARIO
// ============================================================

int main() {
    TestSuite suite;

    suite.add("valid pull request creation", [] {
        PullRequest pr("PR-101", "feature/login", "main");

        pr.addCommit(Commit("a1", "Add login validation"));
        pr.open();

        require(
            pr.getState() == PullRequestState::Open,
            "Request should be open."
        );
    });

    suite.add("source and target must differ", [] {
        bool rejected = false;

        try {
            PullRequest pr("PR-102", "main", "main");
        } catch (const invalid_argument&) {
            rejected = true;
        }

        require(rejected, "Identical branches must be rejected.");
    });

    suite.add("eligible approval counting", [] {
        PullRequest pr("PR-103", "feature/api", "main");

        pr.addCommit(Commit("b1", "Add API"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        require(pr.validApprovals() == 1, "Expected one approval.");
    });

    suite.add("new commit invalidates approval", [] {
        PullRequest pr("PR-104", "feature/api", "main");

        pr.addCommit(Commit("c1", "Initial API"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        pr.addCommit(Commit("c2", "Fix API"));

        require(
            pr.validApprovals() == 0,
            "Approval should be stale."
        );
    });

    suite.add("required checks must pass", [] {
        PullRequest pr("PR-105", "feature/db", "main");

        pr.addCommit(Commit("d1", "Add migration"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        Branch main("main", true, false, false, false);

        ProtectionPolicy policy;
        policy.requiredApprovals = 1;
        policy.requiredChecks.insert("unit-tests");

        GovernanceEngine engine;

        auto result = engine.evaluate(pr, main, policy);

        require(!result.eligible, "Missing check must block merge.");
    });

    suite.add("unresolved conversations block merge", [] {
        PullRequest pr("PR-106", "feature/ui", "main");

        pr.addCommit(Commit("e1", "Add UI"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        pr.addConversation("discussion-1");

        Branch main("main", true, false, false, false);

        ProtectionPolicy policy;
        policy.requiredApprovals = 1;

        GovernanceEngine engine;

        auto result = engine.evaluate(pr, main, policy);

        require(!result.eligible, "Discussion must block merge.");
    });

    suite.add("complete merge workflow", [] {
        PullRequest pr("PR-107", "feature/payment", "main");

        pr.addCommit(Commit("f1", "Add payment service"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        pr.addCheck("unit-tests", CheckStatus::Passed);
        pr.addCheck("integration-tests", CheckStatus::Passed);

        Branch main("main", true, false, false, false);

        ProtectionPolicy policy;
        policy.requiredApprovals = 1;
        policy.requiredChecks = {
            "unit-tests",
            "integration-tests"
        };

        GovernanceEngine engine;

        engine.merge(
            pr,
            main,
            policy,
            MergeStrategy::Squash
        );

        require(
            pr.getState() == PullRequestState::Merged,
            "Pull request should be merged."
        );
    });

    suite.add("dismissed approval does not count", [] {
        PullRequest pr("PR-108", "feature/search", "main");

        pr.addCommit(Commit("g1", "Add search"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::Approved)
        );

        pr.dismissReview("reviewer-1");

        require(pr.validApprovals() == 0, "Dismissed review counted.");
    });

    suite.add("requested changes block merge", [] {
        PullRequest pr("PR-109", "feature/cache", "main");

        pr.addCommit(Commit("h1", "Add cache"));
        pr.open();

        pr.addReview(
            Review("reviewer-1", ReviewDecision::ChangesRequested)
        );

        Branch main("main", true, false, false, false);

        ProtectionPolicy policy;
        policy.requiredApprovals = 0;

        GovernanceEngine engine;

        auto result = engine.evaluate(pr, main, policy);

        require(!result.eligible, "Requested changes must block merge.");
    });

    suite.add("force-push policy remains independent", [] {
        Branch main("main", true, false, false, false);

        require(!main.allowsForcePush, "Force push must be restricted.");
        require(!main.allowsDirectPush, "Direct push must be restricted.");
    });

    suite.run();
    suite.print();

    cout << "\nRED-GREEN-REFACTOR\n";
    cout << "RED: Define behavior with failing tests.\n";
    cout << "GREEN: Implement the smallest passing solution.\n";
    cout << "REFACTOR: Improve structure while preserving behavior.\n";

    if (suite.failed() > 0) {
        return 1;
    }

    cout << "\nAll governance tests passed.\n";

    return 0;
}
