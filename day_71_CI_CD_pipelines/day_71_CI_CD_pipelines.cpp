#include <algorithm>
#include <chrono>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

/*
 * CI/CD Repository Governance and Merge Eligibility Engine
 *
 * Models:
 * - Repository branches
 * - Pull-request-triggered pipelines
 * - Pipeline stages
 * - Build and test results
 * - Security gates
 * - Approval requirements
 * - Protected environments
 * - Deployment eligibility
 * - Immutable artifact metadata
 *
 * Compile:
 * g++ -std=c++17 -O2 -Wall -Wextra -pedantic cicd.cpp -o cicd
 */

enum class StageStatus {
    Pending,
    Running,
    Success,
    Failed,
    Skipped
};

enum class PipelineStatus {
    Created,
    Running,
    Success,
    Failed
};

enum class Environment {
    Development,
    Staging,
    Production
};

enum class DeploymentStatus {
    NotDeployed,
    Deployed,
    Rejected
};

std::string toString(StageStatus status) {
    switch (status) {
        case StageStatus::Pending: return "PENDING";
        case StageStatus::Running: return "RUNNING";
        case StageStatus::Success: return "SUCCESS";
        case StageStatus::Failed: return "FAILED";
        case StageStatus::Skipped: return "SKIPPED";
    }
    return "UNKNOWN";
}

std::string toString(PipelineStatus status) {
    switch (status) {
        case PipelineStatus::Created: return "CREATED";
        case PipelineStatus::Running: return "RUNNING";
        case PipelineStatus::Success: return "SUCCESS";
        case PipelineStatus::Failed: return "FAILED";
    }
    return "UNKNOWN";
}

std::string toString(Environment environment) {
    switch (environment) {
        case Environment::Development: return "development";
        case Environment::Staging: return "staging";
        case Environment::Production: return "production";
    }
    return "unknown";
}

struct Branch {
    std::string name;
    std::string headCommit;
    bool protectedBranch = false;
};

struct Artifact {
    std::string name;
    std::string version;
    std::string checksum;
    std::size_t sizeBytes = 0;
};

struct PipelineStage {
    std::string name;
    std::vector<std::string> dependencies;
    std::function<bool()> execute;
    int maxAttempts = 1;
    StageStatus status = StageStatus::Pending;
    int attempts = 0;
    std::string error;
};

struct StageResult {
    std::string name;
    StageStatus status;
    int attempts;
    std::string error;
};

struct PipelineReport {
    PipelineStatus status = PipelineStatus::Created;
    std::vector<StageResult> stages;
    std::vector<std::string> executionOrder;
};

struct ApprovalPolicy {
    int requiredApprovals = 1;
    bool requireIndependentReviewer = true;
    bool requireSecurityApproval = true;
};

struct PullRequest {
    int id;
    std::string sourceBranch;
    std::string targetBranch;
    std::string sourceCommit;
    std::string targetCommit;
    bool open = true;
    bool draft = false;
    bool conversationsResolved = false;
    bool hasMergeConflict = false;
    int approvals = 0;
    int rejectedReviews = 0;
    bool independentApproval = false;
    bool securityApproval = false;
    bool sourceSynchronized = true;
};

struct DeploymentPolicy {
    bool requireSuccessfulPipeline = true;
    bool requireApproval = true;
    bool requireSecurityScan = true;
    bool immutableArtifacts = true;
    bool allowProductionDeployment = true;
};

struct DeploymentDecision {
    bool eligible = false;
    std::vector<std::string> reasons;
};

class Repository {
private:
    std::string name;
    std::map<std::string, Branch> branches;

public:
    explicit Repository(std::string repositoryName)
        : name(std::move(repositoryName)) {
        if (name.empty()) {
            throw std::invalid_argument(
                "Repository name cannot be empty."
            );
        }
    }

    void addBranch(const Branch& branch) {
        if (branch.name.empty() || branch.headCommit.empty()) {
            throw std::invalid_argument(
                "Branch name and commit are required."
            );
        }

        if (branches.count(branch.name)) {
            throw std::invalid_argument(
                "Duplicate branch: " + branch.name
            );
        }

        branches.emplace(branch.name, branch);
    }

    const Branch& getBranch(const std::string& branchName) const {
        auto iterator = branches.find(branchName);

        if (iterator == branches.end()) {
            throw std::out_of_range(
                "Branch does not exist: " + branchName
            );
        }

        return iterator->second;
    }

    bool exists(const std::string& branchName) const {
        return branches.count(branchName) > 0;
    }

    void updateBranch(
        const std::string& branchName,
        const std::string& commit
    ) {
        auto iterator = branches.find(branchName);

        if (iterator == branches.end()) {
            throw std::out_of_range("Unknown branch.");
        }

        if (commit.empty()) {
            throw std::invalid_argument("Commit cannot be empty.");
        }

        iterator->second.headCommit = commit;
    }

    void printBranches() const {
        std::cout << "\nRepository: " << name << '\n';

        for (const auto& [branchName, branch] : branches) {
            std::cout
                << branchName
                << " | HEAD=" << branch.headCommit
                << " | protected="
                << std::boolalpha
                << branch.protectedBranch
                << '\n';
        }
    }
};

class PipelineEngine {
private:
    std::map<std::string, PipelineStage> stages;

    std::vector<std::string> topologicalSort() const {
        std::map<std::string, int> indegree;
        std::map<std::string, std::vector<std::string>> dependents;

        for (const auto& [name, stage] : stages) {
            indegree[name] = 0;
            dependents[name] = {};
        }

        for (const auto& [name, stage] : stages) {
            for (const auto& dependency : stage.dependencies) {
                if (!stages.count(dependency)) {
                    throw std::invalid_argument(
                        "Unknown dependency: " + dependency
                    );
                }

                if (dependency == name) {
                    throw std::invalid_argument(
                        "Stage cannot depend on itself."
                    );
                }

                ++indegree[name];
                dependents[dependency].push_back(name);
            }
        }

        std::set<std::string> ready;

        for (const auto& [name, degree] : indegree) {
            if (degree == 0) ready.insert(name);
        }

        std::vector<std::string> order;

        while (!ready.empty()) {
            std::string current = *ready.begin();
            ready.erase(ready.begin());

            order.push_back(current);

            for (const auto& dependent : dependents[current]) {
                if (--indegree[dependent] == 0) {
                    ready.insert(dependent);
                }
            }
        }

        if (order.size() != stages.size()) {
            throw std::invalid_argument(
                "Pipeline contains a dependency cycle."
            );
        }

        return order;
    }

public:
    void addStage(PipelineStage stage) {
        if (stage.name.empty() || !stage.execute) {
            throw std::invalid_argument(
                "Stage requires a name and executable function."
            );
        }

        if (stage.maxAttempts < 1) {
            throw std::invalid_argument(
                "At least one execution attempt is required."
            );
        }

        if (stages.count(stage.name)) {
            throw std::invalid_argument("Duplicate stage.");
        }

        stages.emplace(stage.name, std::move(stage));
    }

    PipelineReport execute() {
        if (stages.empty()) {
            throw std::invalid_argument("Pipeline is empty.");
        }

        PipelineReport report;
        report.status = PipelineStatus::Running;
        report.executionOrder = topologicalSort();

        bool pipelineFailed = false;

        for (const auto& name : report.executionOrder) {
            PipelineStage& stage = stages.at(name);

            bool dependenciesSucceeded = true;

            for (const auto& dependency : stage.dependencies) {
                if (stages.at(dependency).status !=
                    StageStatus::Success) {
                    dependenciesSucceeded = false;
                    break;
                }
            }

            if (!dependenciesSucceeded || pipelineFailed) {
                stage.status = StageStatus::Skipped;
                stage.error = "Dependency or pipeline failure.";
            } else {
                stage.status = StageStatus::Running;

                for (
                    int attempt = 1;
                    attempt <= stage.maxAttempts;
                    ++attempt
                ) {
                    stage.attempts = attempt;

                    try {
                        if (stage.execute()) {
                            stage.status = StageStatus::Success;
                            stage.error.clear();
                            break;
                        }

                        stage.error = "Stage returned failure.";
                    } catch (const std::exception& error) {
                        stage.error = error.what();
                    }
                }

                if (stage.status != StageStatus::Success) {
                    stage.status = StageStatus::Failed;
                    pipelineFailed = true;
                }
            }

            report.stages.push_back({
                stage.name,
                stage.status,
                stage.attempts,
                stage.error
            });
        }

        report.status = pipelineFailed
            ? PipelineStatus::Failed
            : PipelineStatus::Success;

        return report;
    }
};

class GovernanceEngine {
private:
    ApprovalPolicy approvalPolicy;
    DeploymentPolicy deploymentPolicy;

public:
    GovernanceEngine(
        ApprovalPolicy approvals,
        DeploymentPolicy deployment
    )
        : approvalPolicy(approvals),
          deploymentPolicy(deployment) {

        if (approvalPolicy.requiredApprovals < 0) {
            throw std::invalid_argument(
                "Approval count cannot be negative."
            );
        }
    }

    DeploymentDecision evaluate(
        const PullRequest& pr,
        const PipelineReport& pipeline,
        const Artifact& artifact,
        Environment environment
    ) const {
        DeploymentDecision decision;

        auto reject = [&](const std::string& reason) {
            decision.reasons.push_back(reason);
        };

        if (!pr.open) reject("Pull Request is closed.");
        if (pr.draft) reject("Draft Pull Request cannot be deployed.");
        if (pr.hasMergeConflict) reject("Merge conflict exists.");
        if (!pr.conversationsResolved) {
            reject("Review conversations remain unresolved.");
        }
        if (!pr.sourceSynchronized) {
            reject("Source branch requires synchronization.");
        }

        if (
            deploymentPolicy.requireSuccessfulPipeline &&
            pipeline.status != PipelineStatus::Success
        ) {
            reject("Pipeline did not succeed.");
        }

        if (
            pr.approvals < approvalPolicy.requiredApprovals
        ) {
            reject("Insufficient approval count.");
        }

        if (
            approvalPolicy.requireIndependentReviewer &&
            !pr.independentApproval
        ) {
            reject("Independent reviewer approval missing.");
        }

        if (
            deploymentPolicy.requireSecurityScan &&
            approvalPolicy.requireSecurityApproval &&
            !pr.securityApproval
        ) {
            reject("Security approval missing.");
        }

        if (
            deploymentPolicy.requireApproval &&
            pr.rejectedReviews > 0
        ) {
            reject("Unresolved change request exists.");
        }

        if (artifact.name.empty() || artifact.checksum.empty()) {
            reject("Artifact integrity metadata missing.");
        }

        if (deploymentPolicy.immutableArtifacts &&
            artifact.version.empty()) {
            reject("Immutable artifact version missing.");
        }

        if (
            environment == Environment::Production &&
            !deploymentPolicy.allowProductionDeployment
        ) {
            reject("Production deployment disabled.");
        }

        decision.eligible = decision.reasons.empty();

        return decision;
    }
};

void printReport(const PipelineReport& report) {
    std::cout << "\n========== PIPELINE REPORT ==========\n";

    std::cout
        << "Pipeline: "
        << toString(report.status)
        << '\n';

    for (const auto& stage : report.stages) {
        std::cout
            << std::left
            << std::setw(20)
            << stage.name
            << std::setw(12)
            << toString(stage.status)
            << " Attempts=" << stage.attempts;

        if (!stage.error.empty()) {
            std::cout << " Error=" << stage.error;
        }

        std::cout << '\n';
    }
}

int main() {
    try {
        Repository repository("engineering/payment-service");

        repository.addBranch({
            "main",
            "commit-main-001",
            true
        });

        repository.addBranch({
            "feature/payment-validation",
            "commit-feature-009",
            false
        });

        repository.printBranches();

        PullRequest pr{
            104,
            "feature/payment-validation",
            "main",
            "commit-feature-009",
            "commit-main-001",
            true,
            false,
            true,
            false,
            2,
            0,
            true,
            true,
            true
        };

        PipelineEngine pipeline;

        pipeline.addStage({
            "checkout",
            {},
            []() {
                std::cout << "\nChecking out source commit...\n";
                return true;
            },
            1
        });

        pipeline.addStage({
            "build",
            {"checkout"},
            []() {
                std::cout << "Building application...\n";
                return true;
            },
            2
        });

        pipeline.addStage({
            "unit_tests",
            {"build"},
            []() {
                std::cout << "Executing unit tests...\n";
                return true;
            },
            2
        });

        pipeline.addStage({
            "integration_tests",
            {"build"},
            []() {
                std::cout << "Executing integration tests...\n";
                return true;
            },
            2
        });

        pipeline.addStage({
            "security_scan",
            {"build"},
            []() {
                std::cout << "Scanning source and dependencies...\n";
                return true;
            },
            1
        });

        pipeline.addStage({
            "package",
            {"unit_tests", "integration_tests", "security_scan"},
            []() {
                std::cout << "Creating immutable package...\n";
                return true;
            },
            1
        });

        PipelineReport report = pipeline.execute();
        printReport(report);

        Artifact artifact{
            "payment-service",
            "1.4.2",
            "sha256:abc123def456",
            5242880
        };

        GovernanceEngine governance(
            ApprovalPolicy{2, true, true},
            DeploymentPolicy{true, true, true, true, true}
        );

        DeploymentDecision decision = governance.evaluate(
            pr,
            report,
            artifact,
            Environment::Production
        );

        std::cout << "\n========== DEPLOYMENT DECISION ==========\n";

        if (decision.eligible) {
            std::cout
                << "ELIGIBLE: Deployment requirements satisfied.\n";

            repository.updateBranch(
                "main",
                "commit-feature-009"
            );

            std::cout
                << "Deployment environment: "
                << toString(Environment::Production)
                << '\n';
        } else {
            std::cout << "REJECTED:\n";

            for (const auto& reason : decision.reasons) {
                std::cout << " - " << reason << '\n';
            }
        }

        // Negative scenario: production deployment without approval.
        PullRequest invalidPR = pr;
        invalidPR.approvals = 0;
        invalidPR.securityApproval = false;

        DeploymentDecision rejected = governance.evaluate(
            invalidPR,
            report,
            artifact,
            Environment::Production
        );

        std::cout
            << "\nNegative scenario eligible: "
            << std::boolalpha
            << rejected.eligible
            << '\n';

        if (rejected.eligible) {
            throw std::logic_error(
                "Governance validation failed."
            );
        }

    } catch (const std::exception& error) {
        std::cerr
            << "Execution error: "
            << error.what()
            << '\n';

        return 1;
    }

    return 0;
}
