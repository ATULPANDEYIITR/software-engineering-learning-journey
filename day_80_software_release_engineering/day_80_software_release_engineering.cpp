#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std;

/*
 * Software Release Engineering
 *
 * Repository-independent deployment governance engine.
 *
 * Implements:
 * - Release artifact management
 * - Change management
 * - Approval requirements
 * - Release strategies
 * - Environment state
 * - Status check evaluation
 * - Progressive traffic allocation
 * - Merge-independent release authorization
 * - Automatic rollback
 * - Release audit history
 */

// ---------------------------------------------------------
// Domain enumerations
// ---------------------------------------------------------

enum class Environment {
    Staging,
    Production
};

enum class Strategy {
    Canary,
    Rolling,
    BlueGreen,
    Recreate
};

enum class Risk {
    Low,
    Medium,
    High,
    Critical
};

enum class ChangeStatus {
    Submitted,
    Approved,
    Rejected,
    Implemented
};

enum class ReleaseStatus {
    Created,
    Validating,
    Deploying,
    Succeeded,
    Failed,
    RolledBack
};

enum class CheckStatus {
    Pending,
    Passed,
    Failed
};

string toString(Environment value) {
    return value == Environment::Production
        ? "production" : "staging";
}

string toString(Strategy value) {
    switch (value) {
        case Strategy::Canary: return "canary";
        case Strategy::Rolling: return "rolling";
        case Strategy::BlueGreen: return "blue-green";
        case Strategy::Recreate: return "recreate";
    }
    throw logic_error("Unknown strategy");
}

string toString(ReleaseStatus value) {
    switch (value) {
        case ReleaseStatus::Created: return "created";
        case ReleaseStatus::Validating: return "validating";
        case ReleaseStatus::Deploying: return "deploying";
        case ReleaseStatus::Succeeded: return "succeeded";
        case ReleaseStatus::Failed: return "failed";
        case ReleaseStatus::RolledBack: return "rolled-back";
    }
    throw logic_error("Unknown release state");
}

// ---------------------------------------------------------
// Data models
// ---------------------------------------------------------

struct Artifact {
    string version;
    string commit;
    string digest;
    int buildNumber;

    void validate() const {
        if (version.empty()) {
            throw invalid_argument("Artifact version is required");
        }

        if (commit.size() < 7) {
            throw invalid_argument("Invalid commit hash");
        }

        if (digest.size() != 71 ||
            digest.substr(0, 7) != "sha256:") {
            throw invalid_argument("Invalid SHA-256 digest");
        }

        if (!all_of(
            digest.begin() + 7,
            digest.end(),
            [](unsigned char c) {
                return isxdigit(c);
            })) {
            throw invalid_argument("Digest contains invalid characters");
        }

        if (buildNumber <= 0) {
            throw invalid_argument("Build number must be positive");
        }
    }
};

struct ChangeRequest {
    string id;
    string title;
    string requester;
    Risk risk;
    ChangeStatus status = ChangeStatus::Submitted;
    set<string> approvals;

    int requiredApprovals() const {
        switch (risk) {
            case Risk::Low: return 1;
            case Risk::Medium: return 1;
            case Risk::High: return 2;
            case Risk::Critical: return 3;
        }
        throw logic_error("Unknown risk");
    }

    void approve(const string& reviewer) {
        if (status != ChangeStatus::Submitted) {
            throw logic_error("Change is not awaiting approval");
        }

        if (reviewer.empty() || reviewer == requester) {
            throw invalid_argument("Invalid independent reviewer");
        }

        approvals.insert(reviewer);

        if (static_cast<int>(approvals.size()) >= requiredApprovals()) {
            status = ChangeStatus::Approved;
        }
    }

    void reject() {
        if (status != ChangeStatus::Submitted) {
            throw logic_error("Change is not awaiting approval");
        }

        status = ChangeStatus::Rejected;
    }
};

struct StatusCheck {
    string name;
    CheckStatus status;
    string details;
};

struct HealthMetrics {
    double errorRate;
    double latencyMs;
    double availability;

    bool healthy() const {
        return errorRate >= 0.0 &&
               errorRate <= 0.02 &&
               latencyMs >= 0.0 &&
               latencyMs <= 500.0 &&
               availability >= 0.995 &&
               availability <= 1.0;
    }
};

struct Release {
    string id;
    Artifact artifact;
    ChangeRequest change;
    Environment environment;
    Strategy strategy;
    ReleaseStatus status = ReleaseStatus::Created;

    optional<string> previousVersion;
    int trafficPercentage = 0;

    vector<StatusCheck> checks;
};

// ---------------------------------------------------------
// Environment state
// ---------------------------------------------------------

class EnvironmentRegistry {
private:
    map<Environment, optional<string>> activeVersions;

public:
    EnvironmentRegistry() {
        activeVersions[Environment::Staging] = nullopt;
        activeVersions[Environment::Production] = nullopt;
    }

    optional<string> get(Environment environment) const {
        return activeVersions.at(environment);
    }

    void activate(
        Environment environment,
        const string& version
    ) {
        if (version.empty()) {
            throw invalid_argument("Cannot activate empty version");
        }

        activeVersions[environment] = version;
    }

    void restore(
        Environment environment,
        optional<string> version
    ) {
        activeVersions[environment] = version;
    }

    void print() const {
        for (const auto& entry : activeVersions) {
            cout << toString(entry.first) << ": ";

            if (entry.second.has_value()) {
                cout << *entry.second;
            } else {
                cout << "no active release";
            }

            cout << '\n';
        }
    }
};

// ---------------------------------------------------------
// Release governance engine
// ---------------------------------------------------------

class ReleaseEngine {
private:
    EnvironmentRegistry environments;
    map<string, Release> releases;
    vector<string> auditLog;
    set<Environment> lockedEnvironments;

    static vector<int> trafficPlan(Strategy strategy) {
        switch (strategy) {
            case Strategy::Canary:
                return {5, 10, 25, 50, 100};

            case Strategy::Rolling:
                return {25, 50, 75, 100};

            case Strategy::BlueGreen:
                return {0, 100};

            case Strategy::Recreate:
                return {0, 100};
        }

        throw logic_error("Unsupported strategy");
    }

    void audit(const string& message) {
        auditLog.push_back(message);
        cout << "[AUDIT] " << message << '\n';
    }

    void validateChecks(const Release& release) const {
        if (release.checks.empty()) {
            throw runtime_error("No deployment checks configured");
        }

        for (const auto& check : release.checks) {
            if (check.status != CheckStatus::Passed) {
                throw runtime_error(
                    "Status check failed or pending: " + check.name
                );
            }
        }
    }

public:
    ReleaseEngine() = default;

    const EnvironmentRegistry& registry() const {
        return environments;
    }

    void createRelease(
        const string& id,
        const Artifact& artifact,
        const ChangeRequest& change,
        Environment environment,
        Strategy strategy,
        vector<StatusCheck> checks
    ) {
        artifact.validate();

        if (id.empty()) {
            throw invalid_argument("Release ID is required");
        }

        if (releases.count(id)) {
            throw invalid_argument("Duplicate release ID");
        }

        if (change.status != ChangeStatus::Approved) {
            throw runtime_error("Change approval is mandatory");
        }

        if (environments.get(environment) == artifact.version) {
            throw runtime_error("Version is already active");
        }

        Release release{
            id,
            artifact,
            change,
            environment,
            strategy
        };

        release.previousVersion = environments.get(environment);
        release.checks = move(checks);

        releases.emplace(id, move(release));

        audit("Created release " + id);
    }

    bool deploy(
        const string& id,
        const vector<HealthMetrics>& observations,
        optional<size_t> failureStep = nullopt
    ) {
        auto iterator = releases.find(id);

        if (iterator == releases.end()) {
            throw invalid_argument("Release not found");
        }

        Release& release = iterator->second;

        if (release.status != ReleaseStatus::Created) {
            throw logic_error("Invalid deployment state");
        }

        if (lockedEnvironments.count(release.environment)) {
            throw runtime_error("Environment already has an active deployment");
        }

        lockedEnvironments.insert(release.environment);

        try {
            release.status = ReleaseStatus::Validating;

            release.artifact.validate();
            validateChecks(release);

            if (release.change.status != ChangeStatus::Approved) {
                throw runtime_error("Change approval revoked");
            }

            release.status = ReleaseStatus::Deploying;

            const vector<int> steps = trafficPlan(release.strategy);

            if (observations.size() < steps.size()) {
                throw runtime_error("Insufficient health observations");
            }

            for (size_t i = 0; i < steps.size(); ++i) {
                if (failureStep.has_value() &&
                    failureStep.value() == i + 1) {
                    throw runtime_error("Injected deployment failure");
                }

                release.trafficPercentage = steps[i];

                const HealthMetrics& metrics = observations[i];

                cout << "Traffic: " << steps[i]
                     << "% | Error rate: "
                     << fixed << setprecision(3)
                     << metrics.errorRate * 100
                     << "% | Latency: "
                     << metrics.latencyMs << " ms\n";

                if (!metrics.healthy()) {
                    throw runtime_error("Health threshold violated");
                }

                audit(
                    "Health check passed at " +
                    to_string(steps[i]) + "% traffic"
                );
            }

            environments.activate(
                release.environment,
                release.artifact.version
            );

            release.status = ReleaseStatus::Succeeded;

            release.change.status = ChangeStatus::Implemented;

            audit("Release succeeded: " + id);

            lockedEnvironments.erase(release.environment);

            return true;

        } catch (const exception& error) {
            release.status = ReleaseStatus::Failed;

            audit(
                "Release failed: " + string(error.what())
            );

            rollback(release);

            lockedEnvironments.erase(release.environment);

            return false;
        }
    }

    void rollback(Release& release) {
        if (release.status != ReleaseStatus::Failed &&
            release.status != ReleaseStatus::Succeeded) {
            throw logic_error("Invalid rollback transition");
        }

        environments.restore(
            release.environment,
            release.previousVersion
        );

        release.trafficPercentage = 0;
        release.status = ReleaseStatus::RolledBack;

        audit(
            "Rollback completed for " + release.id
        );
    }

    void printReport() const {
        cout << "\n========== RELEASE REPORT ==========\n";

        environments.print();

        cout << "\nRelease history:\n";

        for (const auto& entry : releases) {
            const Release& release = entry.second;

            cout << release.id
                 << " | "
                 << release.artifact.version
                 << " | "
                 << toString(release.strategy)
                 << " | "
                 << toString(release.status)
                 << '\n';
        }

        cout << "\nAudit entries: " << auditLog.size() << '\n';
    }
};

// ---------------------------------------------------------
// Demonstration
// ---------------------------------------------------------

int main() {
    try {
        ReleaseEngine engine;

        ChangeRequest initialChange{
            "CR-100",
            "Initial production release",
            "release-manager",
            Risk::Medium
        };

        initialChange.approve("engineering-lead");

        Artifact first{
            "1.0.0",
            "a123456789",
            "sha256:" + string(64, 'a'),
            100
        };

        vector<StatusCheck> initialChecks{
            {"unit-tests", CheckStatus::Passed, "Passed"},
            {"security-scan", CheckStatus::Passed, "Passed"},
            {"integration-tests", CheckStatus::Passed, "Passed"}
        };

        engine.createRelease(
            "REL-100",
            first,
            initialChange,
            Environment::Production,
            Strategy::BlueGreen,
            initialChecks
        );

        vector<HealthMetrics> initialMetrics{
            {0.003, 150, 0.999},
            {0.004, 160, 0.999}
        };

        if (!engine.deploy("REL-100", initialMetrics)) {
            throw runtime_error("Initial deployment failed");
        }

        cout << "\nInitial release deployed.\n";

        ChangeRequest secondChange{
            "CR-101",
            "Database optimization",
            "engineering-team",
            Risk::High
        };

        secondChange.approve("technical-lead");
        secondChange.approve("security-lead");

        Artifact second{
            "2.0.0",
            "b234567890",
            "sha256:" + string(64, 'b'),
            101
        };

        vector<StatusCheck> secondChecks{
            {"unit-tests", CheckStatus::Passed, "Passed"},
            {"security-scan", CheckStatus::Passed, "Passed"},
            {"integration-tests", CheckStatus::Passed, "Passed"}
        };

        engine.createRelease(
            "REL-101",
            second,
            secondChange,
            Environment::Production,
            Strategy::Canary,
            secondChecks
        );

        vector<HealthMetrics> candidateMetrics{
            {0.004, 150, 0.999},
            {0.006, 180, 0.999},
            {0.075, 900, 0.980},
            {0.004, 150, 0.999},
            {0.004, 150, 0.999}
        };

        bool deployed = engine.deploy(
            "REL-101",
            candidateMetrics
        );

        cout << "\nCandidate deployment result: "
             << (deployed ? "SUCCESS" : "ROLLED BACK")
             << '\n';

        engine.printReport();

        return 0;

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }
}
