#include <algorithm>
#include <cctype>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace std;

enum class Environment {
    Development,
    Testing,
    Staging,
    Production
};

enum class ConfigType {
    String,
    Integer,
    Boolean
};

enum class ConfigState {
    Draft,
    Validated,
    Approved,
    Deployed,
    Rejected,
    RolledBack
};

enum class ActorRole {
    Developer,
    Reviewer,
    SecurityOfficer,
    Administrator
};

struct ConfigDefinition {
    string name;
    ConfigType type;
    bool required = false;
    bool secret = false;
    optional<long long> minimum;
    optional<long long> maximum;
    set<string> choices;
};

struct ConfigChange {
    string key;
    string value;
    string previousValue;
    bool sensitive = false;
};

struct Approval {
    string reviewer;
    ActorRole role;
    bool approved;
    string comment;
};

struct StatusCheck {
    string name;
    bool passed;
    string message;
};

struct BranchPolicy {
    int requiredApprovals = 2;
    bool requireSecurityApproval = true;
    bool requireTests = true;
    bool requireSecretScan = true;
    bool requireConversationsResolved = true;
    bool allowDirectPush = false;
    bool allowForcePush = false;
    bool allowDeletion = false;
    bool requireLinearHistory = true;
    bool allowAdministratorBypass = false;
};

struct PullRequest {
    int id = 0;
    string title;
    string sourceBranch;
    string targetBranch;
    string author;
    ConfigState state = ConfigState::Draft;

    vector<ConfigChange> changes;
    vector<Approval> approvals;
    vector<StatusCheck> checks;

    int unresolvedConversations = 0;
    bool sourceSynchronized = true;
    bool hasMergeConflict = false;
    bool linearHistory = true;
    bool authorApproval = false;
    bool changesValidated = false;
    int sourceRevision = 1;
    int reviewedRevision = 0;
};

class ConfigurationError : public runtime_error {
public:
    using runtime_error::runtime_error;
};

class ConfigurationSchema {
private:
    map<string, ConfigDefinition> definitions;

public:
    void registerSetting(const ConfigDefinition& definition) {
        if (definition.name.empty()) {
            throw ConfigurationError("Empty configuration name");
        }

        if (definitions.count(definition.name)) {
            throw ConfigurationError("Duplicate configuration name");
        }

        definitions.emplace(definition.name, definition);
    }

    const ConfigDefinition& get(const string& name) const {
        auto iterator = definitions.find(name);

        if (iterator == definitions.end()) {
            throw ConfigurationError(
                "Unknown configuration: " + name
            );
        }

        return iterator->second;
    }

    string validate(
        const string& name,
        const string& value
    ) const {
        const auto& definition = get(name);

        if (definition.secret) {
            throw ConfigurationError(
                "Secrets must use a dedicated secret provider"
            );
        }

        if (value.empty() && definition.required) {
            throw ConfigurationError(
                "Required configuration is empty: " + name
            );
        }

        if (definition.type == ConfigType::Integer) {
            size_t consumed = 0;
            long long parsed;

            try {
                parsed = stoll(value, &consumed);
            } catch (...) {
                throw ConfigurationError(
                    "Invalid integer: " + name
                );
            }

            if (consumed != value.size()) {
                throw ConfigurationError(
                    "Invalid integer format: " + name
                );
            }

            if (
                definition.minimum &&
                parsed < *definition.minimum
            ) {
                throw ConfigurationError(
                    "Value below minimum: " + name
                );
            }

            if (
                definition.maximum &&
                parsed > *definition.maximum
            ) {
                throw ConfigurationError(
                    "Value exceeds maximum: " + name
                );
            }

            return to_string(parsed);
        }

        if (definition.type == ConfigType::Boolean) {
            if (value == "true" || value == "false") {
                return value;
            }

            throw ConfigurationError(
                "Boolean must be true or false: " + name
            );
        }

        if (
            !definition.choices.empty() &&
            !definition.choices.count(value)
        ) {
            throw ConfigurationError(
                "Invalid allowed value: " + name
            );
        }

        return value;
    }
};

class ConfigurationRepository {
private:
    map<string, string> values;
    int revision = 0;

public:
    const map<string, string>& getValues() const {
        return values;
    }

    int getRevision() const {
        return revision;
    }

    void apply(
        const vector<ConfigChange>& changes,
        const ConfigurationSchema& schema
    ) {
        map<string, string> candidate = values;

        // Validate the entire changeset before modifying repository state.
        for (const auto& change : changes) {
            candidate[change.key] = schema.validate(
                change.key,
                change.value
            );
        }

        values.swap(candidate);
        revision++;
    }

    void restore(const map<string, string>& snapshot) {
        values = snapshot;
        revision++;
    }
};

class GovernanceEngine {
private:
    BranchPolicy policy;
    Environment environment;

    static bool hasSuccessfulCheck(
        const PullRequest& request,
        const string& name
    ) {
        return any_of(
            request.checks.begin(),
            request.checks.end(),
            [&](const StatusCheck& check) {
                return check.name == name && check.passed;
            }
        );
    }

    static int eligibleApprovals(
        const PullRequest& request
    ) {
        set<string> reviewers;

        for (const auto& approval : request.approvals) {
            if (
                approval.approved &&
                approval.reviewer != request.author &&
                approval.reviewer != ""
            ) {
                if (
                    reviewers.insert(approval.reviewer).second
                ) {
                    // Duplicate approvals do not increase the count.
                }
            }
        }

        return static_cast<int>(reviewers.size());
    }

public:
    GovernanceEngine(
        BranchPolicy branchPolicy,
        Environment targetEnvironment
    ) :
        policy(std::move(branchPolicy)),
        environment(targetEnvironment) {}

    vector<string> evaluate(
        const PullRequest& request
    ) const {
        vector<string> violations;

        if (request.state == ConfigState::Draft) {
            violations.push_back(
                "Draft pull requests cannot be merged"
            );
        }

        if (request.state == ConfigState::Rejected) {
            violations.push_back(
                "Rejected pull request must be revised"
            );
        }

        if (request.sourceBranch.empty() ||
            request.targetBranch.empty()) {
            violations.push_back(
                "Source and target branches are required"
            );
        }

        if (request.sourceBranch == request.targetBranch) {
            violations.push_back(
                "Source and target branches must differ"
            );
        }

        if (!request.sourceSynchronized) {
            violations.push_back(
                "Source branch must synchronize with target"
            );
        }

        if (request.hasMergeConflict) {
            violations.push_back(
                "Merge conflicts must be resolved"
            );
        }

        if (policy.requireLinearHistory && !request.linearHistory) {
            violations.push_back(
                "Linear history requirement failed"
            );
        }

        if (!request.changesValidated) {
            violations.push_back(
                "Configuration changes are not validated"
            );
        }

        int approvalCount = eligibleApprovals(request);

        if (approvalCount < policy.requiredApprovals) {
            violations.push_back(
                "Insufficient eligible approvals"
            );
        }

        if (
            policy.requireSecurityApproval &&
            environment == Environment::Production
        ) {
            bool securityApproved = any_of(
                request.approvals.begin(),
                request.approvals.end(),
                [&](const Approval& approval) {
                    return approval.approved &&
                        approval.role == ActorRole::SecurityOfficer &&
                        approval.reviewer != request.author;
                }
            );

            if (!securityApproved) {
                violations.push_back(
                    "Production requires security approval"
                );
            }
        }

        if (policy.requireTests &&
            !hasSuccessfulCheck(request, "unit-tests")) {
            violations.push_back(
                "Required unit tests have not passed"
            );
        }

        if (policy.requireSecretScan &&
            !hasSuccessfulCheck(request, "secret-scan")) {
            violations.push_back(
                "Required secret scan has not passed"
            );
        }

        if (
            policy.requireConversationsResolved &&
            request.unresolvedConversations > 0
        ) {
            violations.push_back(
                "Review conversations remain unresolved"
            );
        }

        if (
            request.reviewedRevision != request.sourceRevision
        ) {
            violations.push_back(
                "Approvals are stale because the source changed"
            );
        }

        return violations;
    }

    bool eligible(const PullRequest& request) const {
        return evaluate(request).empty();
    }

    void printDecision(const PullRequest& request) const {
        auto violations = evaluate(request);

        cout << "\nPull Request #" << request.id << "\n";

        if (violations.empty()) {
            cout << "MERGE ELIGIBLE\n";
        } else {
            cout << "MERGE BLOCKED\n";

            for (const auto& violation : violations) {
                cout << " - " << violation << "\n";
            }
        }
    }
};

class SecretProvider {
private:
    map<string, string> secrets;

public:
    void store(const string& key, const string& value) {
        if (key.empty() || value.empty()) {
            throw ConfigurationError(
                "Secret key and value are required"
            );
        }

        secrets[key] = value;
    }

    string retrieve(
        const string& key,
        ActorRole role
    ) const {
        if (
            role != ActorRole::Administrator &&
            role != ActorRole::SecurityOfficer
        ) {
            throw ConfigurationError(
                "Secret retrieval is unauthorized"
            );
        }

        auto iterator = secrets.find(key);

        if (iterator == secrets.end()) {
            throw ConfigurationError(
                "Secret does not exist"
            );
        }

        return iterator->second;
    }

    void displayMetadata() const {
        cout << "Stored secrets: " << secrets.size()
             << ", values: [REDACTED]\n";
    }
};

int main() {
    try {
        ConfigurationSchema schema;

        schema.registerSetting({
            "APP_PORT",
            ConfigType::Integer,
            true,
            false,
            1024,
            65535,
            {}
        });

        schema.registerSetting({
            "DEBUG",
            ConfigType::Boolean,
            true,
            false,
            {},
            {},
            {}
        });

        schema.registerSetting({
            "DATABASE_POOL_SIZE",
            ConfigType::Integer,
            true,
            false,
            1,
            100,
            {}
        });

        schema.registerSetting({
            "LOG_LEVEL",
            ConfigType::String,
            true,
            false,
            {},
            {},
            {"DEBUG", "INFO", "WARNING", "ERROR"}
        });

        schema.registerSetting({
            "DATABASE_PASSWORD",
            ConfigType::String,
            true,
            true,
            {},
            {},
            {}
        });

        cout << "CONFIGURATION REPOSITORY\n";

        ConfigurationRepository repository;

        repository.apply({
            {"APP_PORT", "8000", "", false},
            {"DEBUG", "false", "", false},
            {"DATABASE_POOL_SIZE", "15", "", false},
            {"LOG_LEVEL", "INFO", "", false}
        }, schema);

        cout << "Revision: "
             << repository.getRevision() << "\n";

        cout << "APP_PORT: "
             << repository.getValues().at("APP_PORT") << "\n";

        cout << "\nATOMIC VALIDATION\n";

        try {
            repository.apply({
                {"APP_PORT", "8080", "", false},
                {"DATABASE_POOL_SIZE", "500", "", false}
            }, schema);
        } catch (const exception& error) {
            cout << "Changeset rejected: "
                 << error.what() << "\n";
        }

        cout << "Revision after failed update: "
             << repository.getRevision() << "\n";

        SecretProvider secretProvider;

        secretProvider.store(
            "DATABASE_PASSWORD",
            "example-local-secret"
        );

        secretProvider.displayMetadata();

        BranchPolicy productionPolicy;
        productionPolicy.requiredApprovals = 2;

        GovernanceEngine engine(
            productionPolicy,
            Environment::Production
        );

        PullRequest request;

        request.id = 104;
        request.title = "Update production database settings";
        request.sourceBranch = "feature/database-config";
        request.targetBranch = "main";
        request.author = "developer-01";
        request.state = ConfigState::Validated;
        request.changesValidated = true;
        request.sourceSynchronized = true;
        request.hasMergeConflict = false;
        request.linearHistory = true;
        request.sourceRevision = 4;
        request.reviewedRevision = 4;

        request.changes = {
            {"APP_PORT", "8080", "8000", false},
            {"DATABASE_POOL_SIZE", "25", "15", false}
        };

        request.approvals = {
            {
                "reviewer-01",
                ActorRole::Reviewer,
                true,
                "Configuration reviewed"
            },
            {
                "security-01",
                ActorRole::SecurityOfficer,
                true,
                "Production policy reviewed"
            }
        };

        request.checks = {
            {"unit-tests", true, "All tests passed"},
            {"secret-scan", true, "No credentials detected"}
        };

        request.unresolvedConversations = 0;

        cout << "\nINITIAL GOVERNANCE EVALUATION\n";
        engine.printDecision(request);

        cout << "\nSTALE APPROVAL SCENARIO\n";

        request.sourceRevision = 5;
        engine.printDecision(request);

        cout << "\nREAPPROVAL\n";

        request.approvals.clear();
        request.reviewedRevision = 5;

        request.approvals = {
            {
                "reviewer-01",
                ActorRole::Reviewer,
                true,
                "Updated changes reviewed"
            },
            {
                "security-01",
                ActorRole::SecurityOfficer,
                true,
                "Updated security review completed"
            }
        };

        cout << "\nFINAL EVALUATION\n";
        engine.printDecision(request);

        if (engine.eligible(request)) {
            cout << "\nMERGE EXECUTION\n";

            auto previous = repository.getValues();

            try {
                repository.apply(
                    request.changes,
                    schema
                );

                request.state = ConfigState::Deployed;

                cout << "Configuration deployed successfully.\n";
                cout << "New repository revision: "
                     << repository.getRevision() << "\n";

            } catch (...) {
                repository.restore(previous);
                request.state = ConfigState::RolledBack;
                throw;
            }
        }

        cout << "\nSECURITY CHECK\n";

        try {
            secretProvider.retrieve(
                "DATABASE_PASSWORD",
                ActorRole::Developer
            );
        } catch (const exception& error) {
            cout << "Access denied: "
                 << error.what() << "\n";
        }

        cout << "\nExecution completed.\n";

    } catch (const exception& error) {
        cerr << "Fatal error: " << error.what() << "\n";
        return 1;
    }

    return 0;
}
