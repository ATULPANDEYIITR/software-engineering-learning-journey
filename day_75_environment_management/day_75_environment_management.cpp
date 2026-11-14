#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

/*
 * Environment Management
 *
 * C++17 repository release governance engine.
 *
 * Implements:
 * - Environment isolation
 * - Artifact promotion
 * - Deployment validation
 * - Environment-specific policies
 * - Automated status checks
 * - Independent approvals
 * - Deployment lifecycle
 * - Rollback
 *
 * Build:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic environment.cpp -o environment
 */

enum class Environment {
    Development,
    Testing,
    Staging,
    Production
};

enum class DeploymentStatus {
    Pending,
    Validating,
    Deployed,
    Failed,
    RolledBack
};

std::string toString(Environment environment) {
    switch (environment) {
        case Environment::Development: return "development";
        case Environment::Testing: return "testing";
        case Environment::Staging: return "staging";
        case Environment::Production: return "production";
    }

    throw std::runtime_error("Unknown environment.");
}

std::string toString(DeploymentStatus status) {
    switch (status) {
        case DeploymentStatus::Pending: return "pending";
        case DeploymentStatus::Validating: return "validating";
        case DeploymentStatus::Deployed: return "deployed";
        case DeploymentStatus::Failed: return "failed";
        case DeploymentStatus::RolledBack: return "rolled_back";
    }

    throw std::runtime_error("Unknown deployment status.");
}

class GovernanceError : public std::runtime_error {
public:
    explicit GovernanceError(const std::string& message)
        : std::runtime_error(message) {}
};

struct Artifact {
    std::string id;
    std::string version;
    std::string commit;
    std::string digest;
};

struct EnvironmentPolicy {
    Environment environment;
    int replicas;
    int minimumHealthyReplicas;
    bool debugAllowed;
    bool approvalRequired;
    bool secretsRequired;
    std::set<std::string> requiredChecks;
};

struct Deployment {
    std::string id;
    Artifact artifact;
    Environment environment;
    DeploymentStatus status;
    std::string deployedBy;
    std::optional<std::string> approvedBy;
    std::optional<std::string> previousDeployment;
    std::string failureReason;
};

struct DeploymentRequest {
    std::string artifactId;
    Environment target;
    std::string deployedBy;
    std::optional<std::string> approvedBy;
    bool debug;
    int replicas;
    bool environmentAvailable;
    std::set<std::string> availableSecrets;
    std::map<std::string, bool> checks;
};

struct EnvironmentState {
    Environment environment;
    bool available = true;
    std::optional<std::string> activeDeployment;
    std::vector<std::string> deploymentHistory;
};

class PolicyEngine {
private:
    std::map<Environment, EnvironmentPolicy> policies;

public:
    PolicyEngine() {
        policies[Environment::Development] = {
            Environment::Development,
            1, 1, true, false, false, {}
        };

        policies[Environment::Testing] = {
            Environment::Testing,
            1, 1, false, false, true,
            {"unit_tests", "integration_tests", "security_scan"}
        };

        policies[Environment::Staging] = {
            Environment::Staging,
            2, 2, false, true, true,
            {"unit_tests", "integration_tests",
             "security_scan", "smoke_tests"}
        };

        policies[Environment::Production] = {
            Environment::Production,
            3, 3, false, true, true,
            {"unit_tests", "integration_tests",
             "security_scan", "smoke_tests", "load_tests"}
        };
    }

    const EnvironmentPolicy& get(Environment environment) const {
        auto iterator = policies.find(environment);

        if (iterator == policies.end()) {
            throw GovernanceError("Missing environment policy.");
        }

        return iterator->second;
    }

    std::vector<std::string> evaluate(
        const DeploymentRequest& request
    ) const {
        const auto& policy = get(request.target);

        std::vector<std::string> failures;

        if (!request.environmentAvailable) {
            failures.push_back("Environment unavailable.");
        }

        if (request.deployedBy.empty()) {
            failures.push_back("Deployment actor is required.");
        }

        if (request.debug != policy.debugAllowed) {
            failures.push_back("Debug configuration violates policy.");
        }

        if (request.replicas < policy.minimumHealthyReplicas) {
            failures.push_back("Insufficient replicas.");
        }

        if (policy.approvalRequired && !request.approvedBy) {
            failures.push_back("Independent approval required.");
        }

        if (
            request.approvedBy &&
            *request.approvedBy == request.deployedBy
        ) {
            failures.push_back("Self-approval is prohibited.");
        }

        if (policy.secretsRequired) {
            const std::string prefix =
                [&]() {
                    switch (request.target) {
                        case Environment::Testing: return std::string("TESTING");
                        case Environment::Staging: return std::string("STAGING");
                        case Environment::Production: return std::string("PRODUCTION");
                        default: return std::string("DEVELOPMENT");
                    }
                }();

            for (const auto& suffix : {
                "_DATABASE_PASSWORD",
                "_APPLICATION_SECRET"
            }) {
                const std::string key = prefix + suffix;

                if (request.availableSecrets.count(key) == 0) {
                    failures.push_back("Missing secret: " + key);
                }
            }
        }

        for (const auto& required : policy.requiredChecks) {
            auto iterator = request.checks.find(required);

            if (
                iterator == request.checks.end() ||
                iterator->second != true
            ) {
                failures.push_back(
                    "Required check unsuccessful: " + required
                );
            }
        }

        return failures;
    }
};

class EnvironmentManager {
private:
    PolicyEngine policyEngine;

    std::map<std::string, Artifact> artifacts;
    std::map<Environment, EnvironmentState> states;
    std::map<std::string, Deployment> deployments;

    std::vector<Environment> promotionOrder = {
        Environment::Development,
        Environment::Testing,
        Environment::Staging,
        Environment::Production
    };

    int sequence = 0;

    int environmentIndex(Environment environment) const {
        auto iterator = std::find(
            promotionOrder.begin(),
            promotionOrder.end(),
            environment
        );

        if (iterator == promotionOrder.end()) {
            throw GovernanceError("Invalid promotion environment.");
        }

        return static_cast<int>(
            std::distance(promotionOrder.begin(), iterator)
        );
    }

    void validatePromotion(
        const Artifact& artifact,
        Environment target
    ) const {
        int index = environmentIndex(target);

        if (index == 0) {
            return;
        }

        Environment previous = promotionOrder[index - 1];
        const auto& previousState = states.at(previous);

        if (!previousState.activeDeployment) {
            throw GovernanceError(
                "Previous environment has no successful deployment."
            );
        }

        const auto& previousDeployment =
            deployments.at(*previousState.activeDeployment);

        if (
            previousDeployment.artifact.id != artifact.id ||
            previousDeployment.status != DeploymentStatus::Deployed
        ) {
            throw GovernanceError(
                "Artifact must be promoted unchanged from previous environment."
            );
        }
    }

public:
    EnvironmentManager() {
        for (Environment environment : promotionOrder) {
            states.emplace(
                environment,
                EnvironmentState{environment, true, std::nullopt, {}}
            );
        }
    }

    void registerArtifact(const Artifact& artifact) {
        if (
            artifact.id.empty() ||
            artifact.version.empty() ||
            artifact.digest.empty() ||
            artifact.commit.empty()
        ) {
            throw GovernanceError("Invalid artifact metadata.");
        }

        auto iterator = artifacts.find(artifact.id);

        if (
            iterator != artifacts.end() &&
            iterator->second.digest != artifact.digest
        ) {
            throw GovernanceError("Artifact digest mismatch.");
        }

        artifacts[artifact.id] = artifact;
    }

    Deployment deploy(const DeploymentRequest& request) {
        auto artifactIterator = artifacts.find(request.artifactId);

        if (artifactIterator == artifacts.end()) {
            throw GovernanceError("Unknown artifact.");
        }

        validatePromotion(artifactIterator->second, request.target);

        auto failures = policyEngine.evaluate(request);

        if (!failures.empty()) {
            std::ostringstream message;
            message << "Deployment rejected: ";

            for (std::size_t i = 0; i < failures.size(); ++i) {
                if (i > 0) message << "; ";
                message << failures[i];
            }

            throw GovernanceError(message.str());
        }

        auto& state = states.at(request.target);

        std::optional<std::string> previous =
            state.activeDeployment;

        std::ostringstream identifier;
        identifier << "DEP-" << std::setw(5)
                   << std::setfill('0') << ++sequence;

        Deployment deployment{
            identifier.str(),
            artifactIterator->second,
            request.target,
            DeploymentStatus::Validating,
            request.deployedBy,
            request.approvedBy,
            previous,
            ""
        };

        deployments.emplace(deployment.id, deployment);
        state.deploymentHistory.push_back(deployment.id);

        // Health verification represents the infrastructure adapter boundary.
        const auto& policy = policyEngine.get(request.target);

        if (request.replicas < policy.minimumHealthyReplicas) {
            deployments.at(deployment.id).status =
                DeploymentStatus::Failed;

            deployments.at(deployment.id).failureReason =
                "Health verification failed.";

            throw GovernanceError("Health verification failed.");
        }

        deployments.at(deployment.id).status =
            DeploymentStatus::Deployed;

        state.activeDeployment = deployment.id;

        std::cout
            << "[DEPLOYED] " << deployment.id
            << " | " << toString(request.target)
            << " | " << deployment.artifact.version
            << '\n';

        return deployments.at(deployment.id);
    }

    const Deployment& rollback(
        Environment environment,
        const std::string& requestedBy
    ) {
        if (requestedBy.empty()) {
            throw GovernanceError("Rollback actor required.");
        }

        auto& state = states.at(environment);

        if (!state.activeDeployment) {
            throw GovernanceError("No active deployment.");
        }

        auto currentId = *state.activeDeployment;
        auto& current = deployments.at(currentId);

        auto iterator = state.deploymentHistory.rbegin();

        std::optional<std::string> previousId;

        for (; iterator != state.deploymentHistory.rend(); ++iterator) {
            if (*iterator == currentId) {
                continue;
            }

            const auto& candidate = deployments.at(*iterator);

            if (candidate.status == DeploymentStatus::Deployed) {
                previousId = *iterator;
                break;
            }
        }

        if (!previousId) {
            throw GovernanceError("No successful rollback target.");
        }

        current.status = DeploymentStatus::RolledBack;
        state.activeDeployment = previousId;

        std::cout
            << "[ROLLBACK] " << toString(environment)
            << " restored " << deployments.at(*previousId).id
            << " by " << requestedBy << '\n';

        return deployments.at(*previousId);
    }

    void report() const {
        std::cout << "\nENVIRONMENT STATUS\n";

        for (Environment environment : promotionOrder) {
            const auto& state = states.at(environment);

            std::cout << toString(environment)
                      << " | available=" << std::boolalpha
                      << state.available
                      << " | active=";

            if (state.activeDeployment) {
                const auto& deployment =
                    deployments.at(*state.activeDeployment);

                std::cout << deployment.id
                          << " | version="
                          << deployment.artifact.version;
            } else {
                std::cout << "none";
            }

            std::cout << " | deployments="
                      << state.deploymentHistory.size()
                      << '\n';
        }
    }
};

int main() {
    try {
        EnvironmentManager manager;

        Artifact version1{
            "artifact-1001",
            "1.0.0",
            "a1b2c3d4e5f6",
            "sha256-release-1001"
        };

        Artifact version2{
            "artifact-1002",
            "1.1.0",
            "b2c3d4e5f6a7",
            "sha256-release-1002"
        };

        manager.registerArtifact(version1);

        std::map<std::string, bool> checks = {
            {"unit_tests", true},
            {"integration_tests", true},
            {"security_scan", true},
            {"smoke_tests", true},
            {"load_tests", true}
        };

        std::set<std::string> testingSecrets = {
            "TESTING_DATABASE_PASSWORD",
            "TESTING_APPLICATION_SECRET"
        };

        std::set<std::string> stagingSecrets = {
            "STAGING_DATABASE_PASSWORD",
            "STAGING_APPLICATION_SECRET"
        };

        std::set<std::string> productionSecrets = {
            "PRODUCTION_DATABASE_PASSWORD",
            "PRODUCTION_APPLICATION_SECRET"
        };

        manager.deploy({
            version1.id,
            Environment::Development,
            "developer",
            std::nullopt,
            true,
            1,
            true,
            {},
            {}
        });

        manager.deploy({
            version1.id,
            Environment::Testing,
            "ci-pipeline",
            std::nullopt,
            false,
            1,
            true,
            testingSecrets,
            checks
        });

        manager.deploy({
            version1.id,
            Environment::Staging,
            "release-engineer",
            std::string("qa-manager"),
            false,
            2,
            true,
            stagingSecrets,
            checks
        });

        manager.deploy({
            version1.id,
            Environment::Production,
            "release-engineer",
            std::string("production-manager"),
            false,
            3,
            true,
            productionSecrets,
            checks
        });

        manager.registerArtifact(version2);

        manager.deploy({
            version2.id,
            Environment::Development,
            "developer",
            std::nullopt,
            true,
            1,
            true,
            {},
            {}
        });

        manager.deploy({
            version2.id,
            Environment::Testing,
            "ci-pipeline",
            std::nullopt,
            false,
            1,
            true,
            testingSecrets,
            checks
        });

        manager.deploy({
            version2.id,
            Environment::Staging,
            "release-engineer",
            std::string("qa-manager"),
            false,
            2,
            true,
            stagingSecrets,
            checks
        });

        manager.deploy({
            version2.id,
            Environment::Production,
            "release-engineer",
            std::string("production-manager"),
            false,
            3,
            true,
            productionSecrets,
            checks
        });

        manager.rollback(
            Environment::Production,
            "incident-commander"
        );

        manager.report();

        // Demonstrate rejection of an incomplete production release.
        try {
            manager.deploy({
                version2.id,
                Environment::Production,
                "developer",
                std::nullopt,
                true,
                1,
                true,
                {},
                {}
            });
        } catch (const GovernanceError& error) {
            std::cout << "\nEXPECTED POLICY REJECTION: "
                      << error.what() << '\n';
        }

        return 0;

    } catch (const std::exception& error) {
        std::cerr << "Fatal error: " << error.what() << '\n';
        return 1;
    }
}
