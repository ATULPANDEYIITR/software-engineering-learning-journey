#include <algorithm>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

/*
 * Structured Logging and Repository-Independent
 * Application Observability Engine.
 *
 * C++17 implementation.
 *
 * Features:
 * - Structured JSON output
 * - Typed severity levels
 * - Correlation and request identifiers
 * - Context propagation through explicit parameters
 * - Threshold-based filtering
 * - Sensitive-field redaction
 * - Thread-safe output
 * - Log event validation
 * - Mergeable logging metrics
 */

enum class LogLevel {
    DEBUG = 10,
    INFO = 20,
    WARNING = 30,
    ERROR = 40,
    CRITICAL = 50
};

std::string levelName(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO";
        case LogLevel::WARNING: return "WARNING";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::CRITICAL: return "CRITICAL";
    }

    throw std::invalid_argument("Unknown log level.");
}

struct LogContext {
    std::string correlationId;
    std::string requestId;
};

struct LogEvent {
    std::string timestamp;
    LogLevel level;
    std::string service;
    std::string message;
    LogContext context;
    std::map<std::string, std::string> attributes;
};

class JsonEncoder {

public:

    static std::string escape(const std::string& input) {
        std::ostringstream output;

        for (unsigned char ch : input) {
            switch (ch) {
                case '"': output << "\\\""; break;
                case '\\': output << "\\\\"; break;
                case '\b': output << "\\b"; break;
                case '\f': output << "\\f"; break;
                case '\n': output << "\\n"; break;
                case '\r': output << "\\r"; break;
                case '\t': output << "\\t"; break;

                default:
                    if (ch < 0x20) {
                        output << "\\u"
                               << std::hex
                               << std::setw(4)
                               << std::setfill('0')
                               << static_cast<int>(ch)
                               << std::dec;
                    } else {
                        output << ch;
                    }
            }
        }

        return output.str();
    }

    static bool sensitive(const std::string& key) {
        std::string normalized = key;

        std::transform(
            normalized.begin(),
            normalized.end(),
            normalized.begin(),
            [](unsigned char ch) {
                return static_cast<char>(std::tolower(ch));
            }
        );

        static const std::vector<std::string> fields = {
            "password",
            "token",
            "access_token",
            "authorization",
            "secret",
            "api_key",
            "credit_card"
        };

        return std::find(
            fields.begin(),
            fields.end(),
            normalized
        ) != fields.end();
    }

    static std::string encode(const LogEvent& event) {
        std::ostringstream json;

        json << "{"
             << "\"timestamp\":\"" << escape(event.timestamp) << "\","
             << "\"level\":\"" << levelName(event.level) << "\","
             << "\"service\":\"" << escape(event.service) << "\","
             << "\"message\":\"" << escape(event.message) << "\","
             << "\"correlation_id\":\""
             << escape(event.context.correlationId) << "\","
             << "\"request_id\":\""
             << escape(event.context.requestId) << "\","
             << "\"attributes\":{";

        bool first = true;

        for (const auto& [key, value] : event.attributes) {
            if (!first) {
                json << ",";
            }

            first = false;

            json << "\"" << escape(key) << "\":\""
                 << escape(
                     sensitive(key) ? "[REDACTED]" : value
                 )
                 << "\"";
        }

        json << "}}";

        return json.str();
    }
};

class LogMetrics {

private:
    std::map<LogLevel, std::size_t> counts;

public:

    void record(LogLevel level) {
        ++counts[level];
    }

    std::size_t count(LogLevel level) const {
        auto it = counts.find(level);

        return it == counts.end() ? 0 : it->second;
    }

    void print() const {
        std::cout << "\nLogging metrics\n";

        for (const auto& [level, count] : counts) {
            std::cout << levelName(level)
                      << ": " << count << '\n';
        }
    }
};

class StructuredLogger {

private:
    std::string service;
    LogLevel minimumLevel;
    LogMetrics metrics;

    static std::mutex outputMutex;

    static std::string currentTimestamp() {
        const auto now =
            std::chrono::system_clock::now();

        const auto time =
            std::chrono::system_clock::to_time_t(now);

        std::tm utc{};

#ifdef _WIN32
        gmtime_s(&utc, &time);
#else
        gmtime_r(&time, &utc);
#endif

        std::ostringstream output;

        output << std::put_time(
            &utc,
            "%Y-%m-%dT%H:%M:%SZ"
        );

        return output.str();
    }

public:

    StructuredLogger(
        std::string serviceName,
        LogLevel threshold
    )
        : service(std::move(serviceName)),
          minimumLevel(threshold) {

        if (service.empty()) {
            throw std::invalid_argument(
                "Service name cannot be empty."
            );
        }
    }

    void log(
        LogLevel level,
        const std::string& message,
        const LogContext& context,
        const std::map<std::string, std::string>& attributes = {}
    ) {

        if (static_cast<int>(level) <
            static_cast<int>(minimumLevel)) {
            return;
        }

        if (message.empty()) {
            throw std::invalid_argument(
                "Log message cannot be empty."
            );
        }

        if (
            context.correlationId.empty() ||
            context.requestId.empty()
        ) {
            throw std::invalid_argument(
                "Correlation and request IDs are required."
            );
        }

        LogEvent event{
            currentTimestamp(),
            level,
            service,
            message,
            context,
            attributes
        };

        const std::string output =
            JsonEncoder::encode(event);

        // Protect the complete event from interleaved writes.
        {
            std::lock_guard<std::mutex> lock(outputMutex);

            if (static_cast<int>(level) >=
                static_cast<int>(LogLevel::ERROR)) {
                std::cerr << output << '\n';
            } else {
                std::cout << output << '\n';
            }

            metrics.record(level);
        }
    }

    void debug(
        const std::string& message,
        const LogContext& context
    ) {
        log(LogLevel::DEBUG, message, context);
    }

    void info(
        const std::string& message,
        const LogContext& context
    ) {
        log(LogLevel::INFO, message, context);
    }

    void warning(
        const std::string& message,
        const LogContext& context
    ) {
        log(LogLevel::WARNING, message, context);
    }

    void error(
        const std::string& message,
        const LogContext& context
    ) {
        log(LogLevel::ERROR, message, context);
    }

    void printMetrics() const {
        metrics.print();
    }
};

// -------------------------------------------------------
// Repository governance example
// -------------------------------------------------------

enum class CheckStatus {
    PENDING,
    PASSED,
    FAILED
};

struct StatusCheck {
    std::string name;
    CheckStatus status;
};

struct ReviewDecision {
    std::string reviewer;
    std::string decision;
    bool eligible;
};

struct BranchPolicy {
    int requiredApprovals = 2;
    bool requirePassingChecks = true;
    bool requireResolvedConversations = true;
    bool restrictDirectPush = true;
};

struct PullRequest {
    int id;
    std::string sourceBranch;
    std::string targetBranch;
    bool isDraft;
    bool isOpen;
    bool hasConflicts;
    bool conversationsResolved;

    std::vector<ReviewDecision> reviews;
    std::vector<StatusCheck> checks;
};

struct EligibilityResult {
    bool eligible;
    std::vector<std::string> reasons;
};

class MergeEligibilityEngine {

public:

    static EligibilityResult evaluate(
        const PullRequest& pr,
        const BranchPolicy& policy
    ) {

        std::vector<std::string> failures;

        if (!pr.isOpen) {
            failures.push_back("Pull Request is not open.");
        }

        if (pr.isDraft) {
            failures.push_back("Draft Pull Requests cannot merge.");
        }

        if (pr.hasConflicts) {
            failures.push_back("Merge conflicts must be resolved.");
        }

        if (policy.requireResolvedConversations &&
            !pr.conversationsResolved) {
            failures.push_back(
                "Review conversations remain unresolved."
            );
        }

        std::map<std::string, std::string> latestReviews;

        for (const auto& review : pr.reviews) {
            if (!review.eligible) {
                continue;
            }

            if (review.decision == "APPROVED" ||
                review.decision == "CHANGES_REQUESTED" ||
                review.decision == "DISMISSED") {
                latestReviews[review.reviewer] =
                    review.decision;
            }
        }

        int approvals = 0;
        bool changesRequested = false;

        for (const auto& [reviewer, decision] : latestReviews) {
            if (decision == "APPROVED") {
                ++approvals;
            }

            if (decision == "CHANGES_REQUESTED") {
                changesRequested = true;
            }
        }

        if (approvals < policy.requiredApprovals) {
            failures.push_back(
                "Insufficient eligible approvals."
            );
        }

        if (changesRequested) {
            failures.push_back(
                "An eligible reviewer requested changes."
            );
        }

        if (policy.requirePassingChecks) {
            for (const auto& check : pr.checks) {
                if (check.status != CheckStatus::PASSED) {
                    failures.push_back(
                        "Required status check not passed: " +
                        check.name
                    );
                }
            }

            if (pr.checks.empty()) {
                failures.push_back(
                    "No required status checks were reported."
                );
            }
        }

        return {
            failures.empty(),
            failures
        };
    }
};

std::mutex StructuredLogger::outputMutex;

// -------------------------------------------------------
// Main
// -------------------------------------------------------

int main() {

    try {

        StructuredLogger logger(
            "repository-governance",
            LogLevel::DEBUG
        );

        const LogContext context{
            "CORR-PR-2026-1001",
            "REQ-PR-1001"
        };

        logger.info(
            "Repository governance evaluation started",
            context
        );

        logger.debug(
            "Loading branch protection policy",
            context
        );

        BranchPolicy policy{
            2,
            true,
            true,
            true
        };

        PullRequest pr{
            1001,
            "feature/structured-logging",
            "main",
            false,
            true,
            false,
            true,
            {
                {"reviewer-a", "APPROVED", true},
                {"reviewer-b", "APPROVED", true},
                {"external-user", "APPROVED", false}
            },
            {
                {"unit-tests", CheckStatus::PASSED},
                {"security-scan", CheckStatus::PASSED},
                {"lint", CheckStatus::PASSED}
            }
        };

        const EligibilityResult result =
            MergeEligibilityEngine::evaluate(pr, policy);

        if (result.eligible) {
            logger.info(
                "Pull Request is eligible for merge",
                context
            );
        } else {
            logger.warning(
                "Pull Request is blocked by governance policy",
                context
            );

            for (const auto& reason : result.reasons) {
                logger.warning(reason, context);
            }
        }

        // Demonstrate a failing status check.
        pr.checks[1].status = CheckStatus::FAILED;

        const EligibilityResult failedResult =
            MergeEligibilityEngine::evaluate(pr, policy);

        logger.info(
            "Second governance evaluation completed",
            context
        );

        for (const auto& reason : failedResult.reasons) {
            logger.error(reason, context);
        }

        // Demonstrate independent concurrent request contexts.
        std::thread worker([&logger]() {
            LogContext child{
                "CORR-ASYNC-2001",
                "REQ-ASYNC-2001"
            };

            logger.info(
                "Background operation completed",
                child
            );
        });

        worker.join();

        logger.printMetrics();

        std::cout << "\nC++17 tests\n";

        if (JsonEncoder::escape("a\nb") != "a\\nb") {
            throw std::runtime_error(
                "JSON escaping test failed."
            );
        }

        if (result.eligible) {
            std::cout << "Passing policy test: PASSED\n";
        } else {
            throw std::runtime_error(
                "Expected Pull Request to be eligible."
            );
        }

        if (!failedResult.eligible) {
            std::cout << "Failed check test: PASSED\n";
        } else {
            throw std::runtime_error(
                "Failed status check was accepted."
            );
        }

        std::cout << "All C++17 tests passed.\n";

    } catch (const std::exception& error) {

        std::cerr << "Fatal error: "
                  << error.what()
                  << '\n';

        return 1;
    }

    return 0;
}
