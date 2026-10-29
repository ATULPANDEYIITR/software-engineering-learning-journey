#include <algorithm>
#include <chrono>
#include <exception>
#include <iomanip>
#include <iostream>
#include <optional>
#include <queue>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

enum class MessageState {
    Ready,
    Processing,
    Acknowledged,
    Failed,
    DeadLettered
};

struct Message {
    std::string id;
    std::string topic;
    std::string payload;
    int attempts{0};
    MessageState state{MessageState::Ready};
    std::chrono::steady_clock::time_point availableAt{
        std::chrono::steady_clock::now()
    };
};

struct StatusCheck {
    std::string name;
    bool passed{false};
};

struct BranchPolicy {
    bool protectedBranch{true};
    int requiredApprovals{2};
    bool requireSuccessfulChecks{true};
    bool allowDirectPush{false};
    bool allowForcePush{false};
    bool requireLinearHistory{true};
};

struct PullRequest {
    int number{};
    std::string sourceBranch;
    std::string targetBranch;
    std::vector<std::string> commits;
    std::vector<StatusCheck> checks;
    std::unordered_map<std::string, bool> approvals;
    bool draft{false};
    bool mergeConflict{false};
    bool open{true};
    bool conversationsResolved{true};
};

class GovernanceEngine {
public:
    void setPolicy(const std::string& branch, BranchPolicy policy) {
        policies_[branch] = policy;
    }

    void registerReviewer(const std::string& reviewer) {
        if (reviewer.empty()) {
            throw std::invalid_argument("Reviewer name cannot be empty");
        }
        reviewers_.insert(reviewer);
    }

    bool eligible(const PullRequest& pr, std::string& reason) const {
        if (!pr.open) {
            reason = "Pull Request is closed";
            return false;
        }

        if (pr.draft) {
            reason = "Pull Request is still a draft";
            return false;
        }

        if (pr.sourceBranch.empty() || pr.targetBranch.empty()) {
            reason = "Source and target branches are required";
            return false;
        }

        if (pr.commits.empty()) {
            reason = "Pull Request contains no commits";
            return false;
        }

        if (pr.mergeConflict) {
            reason = "Merge conflicts must be resolved";
            return false;
        }

        auto policyIt = policies_.find(pr.targetBranch);
        if (policyIt == policies_.end()) {
            reason = "No branch policy exists for target branch";
            return false;
        }

        const BranchPolicy& policy = policyIt->second;

        if (!policy.protectedBranch) {
            reason = "Target branch is not protected";
            return true;
        }

        if (!pr.conversationsResolved) {
            reason = "Required conversations are unresolved";
            return false;
        }

        if (policy.requireSuccessfulChecks) {
            for (const auto& check : pr.checks) {
                if (!check.passed) {
                    reason = "A required status check has failed";
                    return false;
                }
            }
        }

        int validApprovals = 0;
        for (const auto& [reviewer, approved] : pr.approvals) {
            if (approved && reviewers_.contains(reviewer)) {
                ++validApprovals;
            }
        }

        if (validApprovals < policy.requiredApprovals) {
            reason = "Required approval count has not been reached";
            return false;
        }

        reason = "All protected-branch conditions are satisfied";
        return true;
    }

private:
    std::unordered_set<std::string> reviewers_;
    std::unordered_map<std::string, BranchPolicy> policies_;
};

class MessageBroker {
public:
    explicit MessageBroker(std::size_t capacity, int maxAttempts)
        : capacity_(capacity), maxAttempts_(maxAttempts) {
        if (capacity == 0 || maxAttempts <= 0) {
            throw std::invalid_argument("Invalid broker limits");
        }
    }

    void publish(Message message) {
        if (message.id.empty() || message.topic.empty()) {
            throw std::invalid_argument("Message ID and topic are required");
        }

        if (queue_.size() >= capacity_) {
            throw std::runtime_error("Broker queue is full");
        }

        queue_.push(std::move(message));
        ++published_;
    }

    std::optional<Message> receive() {
        if (queue_.empty()) {
            return std::nullopt;
        }

        Message message = queue_.front();
        queue_.pop();

        message.state = MessageState::Processing;
        ++message.attempts;
        return message;
    }

    void acknowledge(Message& message) {
        if (message.state != MessageState::Processing) {
            throw std::logic_error("Invalid acknowledgement state");
        }

        message.state = MessageState::Acknowledged;
        ++acknowledged_;
    }

    void reject(Message message) {
        if (message.state != MessageState::Processing) {
            throw std::logic_error("Invalid rejection state");
        }

        if (message.attempts >= maxAttempts_) {
            message.state = MessageState::DeadLettered;
            deadLetters_.push_back(std::move(message));
            return;
        }

        message.state = MessageState::Ready;
        queue_.push(std::move(message));
        ++retries_;
    }

    std::size_t depth() const {
        return queue_.size();
    }

    std::size_t deadLetterCount() const {
        return deadLetters_.size();
    }

    void printMetrics() const {
        std::cout << "published=" << published_
                  << " acknowledged=" << acknowledged_
                  << " retries=" << retries_
                  << " dead_letters=" << deadLetters_.size()
                  << " depth=" << queue_.size() << '\n';
    }

private:
    std::queue<Message> queue_;
    std::vector<Message> deadLetters_;
    std::size_t capacity_;
    int maxAttempts_;
    std::size_t published_{0};
    std::size_t acknowledged_{0};
    std::size_t retries_{0};
};

void runBrokerCaseStudy() {
    MessageBroker broker(20, 3);

    broker.publish({"MSG-001", "orders.created",
                    R"({"order_id":"ORD-1001","amount":450.25})"});
    broker.publish({"MSG-002", "orders.created",
                    R"({"order_id":"ORD-1002","amount":89.00})"});
    broker.publish({"MSG-003", "payments.authorize",
                    R"({"payment_id":"PAY-77","amount":89.00})"});

    while (broker.depth() > 0) {
        auto received = broker.receive();
        if (!received) {
            break;
        }

        Message message = *received;

        // The payment message models a downstream failure. Bounded retries
        // prevent an unavailable dependency from blocking the entire queue.
        if (message.topic == "payments.authorize") {
            broker.reject(std::move(message));
            continue;
        }

        broker.acknowledge(message);
    }

    // Retry the failed payment until it reaches the dead-letter queue.
    while (broker.depth() > 0) {
        auto received = broker.receive();
        if (!received) {
            break;
        }
        broker.reject(std::move(*received));
    }

    broker.printMetrics();
}

void runGovernanceCaseStudy() {
    GovernanceEngine engine;

    engine.registerReviewer("alice");
    engine.registerReviewer("bob");
    engine.registerReviewer("carol");

    BranchPolicy mainPolicy;
    mainPolicy.requiredApprovals = 2;
    mainPolicy.requireSuccessfulChecks = true;
    mainPolicy.allowDirectPush = false;
    mainPolicy.allowForcePush = false;
    mainPolicy.requireLinearHistory = true;

    engine.setPolicy("main", mainPolicy);

    PullRequest pr{
        42,
        "feature/order-consumer",
        "main",
        {"a1b2c3", "d4e5f6"},
        {{"unit-tests", true}, {"integration-tests", true}},
        {{"alice", true}, {"bob", true}},
        false,
        false,
        true,
        true
    };

    std::string reason;
    const bool canMerge = engine.eligible(pr, reason);

    std::cout << "PR #" << pr.number
              << " merge_eligible=" << std::boolalpha << canMerge
              << " reason=" << reason << '\n';

    // Demonstrate a failed policy evaluation without changing the original
    // Pull Request. This separates review decisions from branch enforcement.
    PullRequest failed = pr;
    failed.checks[1].passed = false;

    const bool failedEligibility = engine.eligible(failed, reason);
    std::cout << "PR #" << failed.number
              << " after_failed_check=" << failedEligibility
              << " reason=" << reason << '\n';
}

int main() {
    try {
        std::cout << std::fixed << std::setprecision(2);
        runBrokerCaseStudy();
        runGovernanceCaseStudy();
    } catch (const std::exception& error) {
        std::cerr << "fatal_error=" << error.what() << '\n';
        return 1;
    }

    return 0;
}
