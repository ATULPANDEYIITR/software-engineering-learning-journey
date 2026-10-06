#include <algorithm>
#include <chrono>
#include <iostream>
#include <memory>
#include <mutex>
#include <optional>
#include <regex>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Design Patterns I: Factory, Builder, Singleton
 *
 * Technical case study:
 * A deployment platform needs to construct deployment commands, select the
 * correct execution strategy, and maintain one process-wide audit service.
 *
 * Factory:
 *   Selects a concrete deployment executor from a deployment target.
 *
 * Builder:
 *   Constructs a complex deployment request with optional configuration and
 *   validates it before execution.
 *
 * Singleton:
 *   Provides one shared audit repository for the running process.
 *
 * The program is deliberately not a language-syntax tutorial. Every class
 * exists because it represents a responsibility in the deployment domain.
 */

enum class DeploymentTarget {
    KUBERNETES,
    VIRTUAL_MACHINE,
    SERVERLESS
};

enum class RiskLevel {
    LOW,
    MEDIUM,
    HIGH,
    CRITICAL
};

enum class DeploymentState {
    CREATED,
    VALIDATED,
    EXECUTING,
    COMPLETED,
    FAILED
};

std::string to_string(DeploymentTarget target) {
    switch (target) {
        case DeploymentTarget::KUBERNETES:
            return "kubernetes";
        case DeploymentTarget::VIRTUAL_MACHINE:
            return "virtual-machine";
        case DeploymentTarget::SERVERLESS:
            return "serverless";
    }

    throw std::invalid_argument("Unknown deployment target.");
}

std::string to_string(RiskLevel risk) {
    switch (risk) {
        case RiskLevel::LOW:
            return "low";
        case RiskLevel::MEDIUM:
            return "medium";
        case RiskLevel::HIGH:
            return "high";
        case RiskLevel::CRITICAL:
            return "critical";
    }

    throw std::invalid_argument("Unknown risk level.");
}

std::string to_string(DeploymentState state) {
    switch (state) {
        case DeploymentState::CREATED:
            return "created";
        case DeploymentState::VALIDATED:
            return "validated";
        case DeploymentState::EXECUTING:
            return "executing";
        case DeploymentState::COMPLETED:
            return "completed";
        case DeploymentState::FAILED:
            return "failed";
    }

    throw std::invalid_argument("Unknown deployment state.");
}


// ---------------------------------------------------------------------------
// Domain object
// ---------------------------------------------------------------------------

class DeploymentRequest {
public:
    DeploymentRequest(
        std::string application,
        std::string version,
        std::string owner,
        DeploymentTarget target,
        RiskLevel risk,
        int replicas,
        bool rollbackEnabled,
        std::vector<std::string> environmentVariables,
        std::unordered_map<std::string, std::string> metadata
    )
        : application_(std::move(application)),
          version_(std::move(version)),
          owner_(std::move(owner)),
          target_(target),
          risk_(risk),
          replicas_(replicas),
          rollbackEnabled_(rollbackEnabled),
          environmentVariables_(std::move(environmentVariables)),
          metadata_(std::move(metadata)) {}

    const std::string& application() const {
        return application_;
    }

    const std::string& version() const {
        return version_;
    }

    const std::string& owner() const {
        return owner_;
    }

    DeploymentTarget target() const {
        return target_;
    }

    RiskLevel risk() const {
        return risk_;
    }

    int replicas() const {
        return replicas_;
    }

    bool rollbackEnabled() const {
        return rollbackEnabled_;
    }

    const std::vector<std::string>& environmentVariables() const {
        return environmentVariables_;
    }

    const std::unordered_map<std::string, std::string>& metadata() const {
        return metadata_;
    }

private:
    std::string application_;
    std::string version_;
    std::string owner_;
    DeploymentTarget target_;
    RiskLevel risk_;
    int replicas_;
    bool rollbackEnabled_;
    std::vector<std::string> environmentVariables_;
    std::unordered_map<std::string, std::string> metadata_;
};


// ---------------------------------------------------------------------------
// Builder Pattern
// ---------------------------------------------------------------------------

class DeploymentRequestBuilder {
public:
    DeploymentRequestBuilder(
        std::string application,
        std::string version,
        std::string owner,
        DeploymentTarget target
    )
        : application_(std::move(application)),
          version_(std::move(version)),
          owner_(std::move(owner)),
          target_(target) {}

    DeploymentRequestBuilder& risk(RiskLevel value) {
        risk_ = value;
        return *this;
    }

    DeploymentRequestBuilder& replicas(int value) {
        replicas_ = value;
        return *this;
    }

    DeploymentRequestBuilder& rollback(bool enabled) {
        rollbackEnabled_ = enabled;
        return *this;
    }

    DeploymentRequestBuilder& addEnvironmentVariable(std::string variable) {
        if (variable.empty() || variable.find('=') == std::string::npos) {
            throw std::invalid_argument(
                "Environment variable must use KEY=VALUE format."
            );
        }

        environmentVariables_.push_back(std::move(variable));
        return *this;
    }

    DeploymentRequestBuilder& metadata(
        std::string key,
        std::string value
    ) {
        if (key.empty()) {
            throw std::invalid_argument("Metadata key cannot be empty.");
        }

        metadata_[std::move(key)] = std::move(value);
        return *this;
    }

    DeploymentRequest build() const {
        validate();

        return DeploymentRequest(
            application_,
            version_,
            owner_,
            target_,
            risk_,
            replicas_,
            rollbackEnabled_,
            environmentVariables_,
            metadata_
        );
    }

private:
    void validate() const {
        if (application_.empty()) {
            throw std::invalid_argument("Application is required.");
        }

        if (!std::regex_match(version_, std::regex(R"(^v?[0-9]+\.[0-9]+\.[0-9]+$)"))) {
            throw std::invalid_argument(
                "Version must use semantic version form such as 4.2.0."
            );
        }

        if (owner_.empty()) {
            throw std::invalid_argument("Deployment owner is required.");
        }

        if (replicas_ < 1 || replicas_ > 100) {
            throw std::invalid_argument(
                "Replica count must be between 1 and 100."
            );
        }

        if (risk_ == RiskLevel::CRITICAL && !rollbackEnabled_) {
            throw std::invalid_argument(
                "Critical deployments require rollback support."
            );
        }

        if (target_ == DeploymentTarget::SERVERLESS && replicas_ != 1) {
            throw std::invalid_argument(
                "Serverless deployment uses one logical deployment unit."
            );
        }
    }

    std::string application_;
    std::string version_;
    std::string owner_;
    DeploymentTarget target_;

    RiskLevel risk_ = RiskLevel::MEDIUM;
    int replicas_ = 1;
    bool rollbackEnabled_ = true;

    std::vector<std::string> environmentVariables_;
    std::unordered_map<std::string, std::string> metadata_;
};


// ---------------------------------------------------------------------------
// Singleton Pattern
// ---------------------------------------------------------------------------

class AuditService {
public:
    static AuditService& instance() {
        /*
         * Function-local static initialization is thread-safe in C++11 and
         * later. This avoids manual double-checked locking.
         */
        static AuditService service;
        return service;
    }

    AuditService(const AuditService&) = delete;
    AuditService& operator=(const AuditService&) = delete;
    AuditService(AuditService&&) = delete;
    AuditService& operator=(AuditService&&) = delete;

    void record(
        const std::string& event,
        const std::string& application
    ) {
        std::lock_guard<std::mutex> guard(mutex_);

        events_.push_back(event + " [" + application + "]");
    }

    std::vector<std::string> snapshot() const {
        std::lock_guard<std::mutex> guard(mutex_);
        return events_;
    }

private:
    AuditService() = default;

    mutable std::mutex mutex_;
    std::vector<std::string> events_;
};


// ---------------------------------------------------------------------------
// Factory Pattern
// ---------------------------------------------------------------------------

class DeploymentExecutor {
public:
    virtual ~DeploymentExecutor() = default;

    virtual std::string execute(
        const DeploymentRequest& request
    ) = 0;
};

class KubernetesExecutor final : public DeploymentExecutor {
public:
    std::string execute(
        const DeploymentRequest& request
    ) override {
        return "kubectl rollout application=" +
               request.application() +
               " version=" +
               request.version() +
               " replicas=" +
               std::to_string(request.replicas());
    }
};

class VirtualMachineExecutor final : public DeploymentExecutor {
public:
    std::string execute(
        const DeploymentRequest& request
    ) override {
        return "vm-deploy application=" +
               request.application() +
               " version=" +
               request.version() +
               " replicas=" +
               std::to_string(request.replicas());
    }
};

class ServerlessExecutor final : public DeploymentExecutor {
public:
    std::string execute(
        const DeploymentRequest& request
    ) override {
        return "serverless-publish function=" +
               request.application() +
               " version=" +
               request.version();
    }
};

class DeploymentExecutorFactory {
public:
    static std::unique_ptr<DeploymentExecutor> create(
        DeploymentTarget target
    ) {
        switch (target) {
            case DeploymentTarget::KUBERNETES:
                return std::make_unique<KubernetesExecutor>();

            case DeploymentTarget::VIRTUAL_MACHINE:
                return std::make_unique<VirtualMachineExecutor>();

            case DeploymentTarget::SERVERLESS:
                return std::make_unique<ServerlessExecutor>();
        }

        throw std::invalid_argument(
            "No executor exists for the requested target."
        );
    }
};


// ---------------------------------------------------------------------------
// Deployment governance engine
// ---------------------------------------------------------------------------

class DeploymentEngine {
public:
    explicit DeploymentEngine(AuditService& audit)
        : audit_(audit) {}

    DeploymentState execute(const DeploymentRequest& request) {
        DeploymentState state = DeploymentState::CREATED;

        audit_.record(
            "deployment.created:" + to_string(request.target()),
            request.application()
        );

        try {
            validateOperationalPolicy(request);
            state = DeploymentState::VALIDATED;

            audit_.record(
                "deployment.validated:risk=" + to_string(request.risk()),
                request.application()
            );

            auto executor = DeploymentExecutorFactory::create(
                request.target()
            );

            state = DeploymentState::EXECUTING;

            audit_.record(
                "deployment.executing",
                request.application()
            );

            std::cout << executor->execute(request) << '\n';

            state = DeploymentState::COMPLETED;

            audit_.record(
                "deployment.completed",
                request.application()
            );

            return state;
        } catch (const std::exception& exception) {
            state = DeploymentState::FAILED;

            audit_.record(
                "deployment.failed:" + std::string(exception.what()),
                request.application()
            );

            throw;
        }
    }

private:
    static void validateOperationalPolicy(
        const DeploymentRequest& request
    ) {
        if (request.risk() == RiskLevel::CRITICAL &&
            !request.rollbackEnabled()) {
            throw std::logic_error(
                "Critical deployment cannot proceed without rollback."
            );
        }

        if (request.target() == DeploymentTarget::SERVERLESS &&
            request.replicas() != 1) {
            throw std::logic_error(
                "Serverless deployment has an invalid replica policy."
            );
        }
    }

    AuditService& audit_;
};


// ---------------------------------------------------------------------------
// Case study execution
// ---------------------------------------------------------------------------

DeploymentRequest buildProductionDeployment() {
    return DeploymentRequestBuilder(
        "payment-api",
        "4.2.0",
        "platform-team",
        DeploymentTarget::KUBERNETES
    )
        .risk(RiskLevel::HIGH)
        .replicas(6)
        .rollback(true)
        .addEnvironmentVariable("ENVIRONMENT=production")
        .addEnvironmentVariable("REGION=ap-south-1")
        .metadata("change_ticket", "CHG-2026-1042")
        .metadata("owner_team", "platform")
        .build();
}

void demonstrateInvalidBuild() {
    std::cout << "\n=== Invalid Builder State ===\n";

    try {
        auto invalid = DeploymentRequestBuilder(
            "payment-api",
            "4.2.0",
            "platform-team",
            DeploymentTarget::KUBERNETES
        )
            .risk(RiskLevel::CRITICAL)
            .replicas(4)
            .rollback(false)
            .build();

        (void)invalid;
    } catch (const std::exception& exception) {
        std::cout << "Rejected: " << exception.what() << '\n';
    }
}

void demonstrateFactory() {
    std::cout << "\n=== Factory Selection ===\n";

    auto kubernetes = DeploymentExecutorFactory::create(
        DeploymentTarget::KUBERNETES
    );
    auto vm = DeploymentExecutorFactory::create(
        DeploymentTarget::VIRTUAL_MACHINE
    );
    auto serverless = DeploymentExecutorFactory::create(
        DeploymentTarget::SERVERLESS
    );

    auto serverlessRequest = DeploymentRequestBuilder(
        "billing-worker",
        "2.1.0",
        "platform-team",
        DeploymentTarget::SERVERLESS
    )
        .risk(RiskLevel::LOW)
        .replicas(1)
        .build();

    auto vmRequest = DeploymentRequestBuilder(
        "legacy-reporting",
        "3.4.1",
        "operations-team",
        DeploymentTarget::VIRTUAL_MACHINE
    )
        .risk(RiskLevel::MEDIUM)
        .replicas(2)
        .build();

    std::cout << kubernetes->execute(buildProductionDeployment()) << '\n';
    std::cout << vm->execute(vmRequest) << '\n';
    std::cout << serverless->execute(serverlessRequest) << '\n';
}

void verifyPatterns() {
    std::cout << "\n=== Pattern Verification ===\n";

    auto request = buildProductionDeployment();

    if (request.application() != "payment-api") {
        throw std::runtime_error("Builder produced incorrect application.");
    }

    if (request.replicas() != 6) {
        throw std::runtime_error("Builder lost replica configuration.");
    }

    auto executor = DeploymentExecutorFactory::create(
        request.target()
    );

    if (!executor) {
        throw std::runtime_error("Factory returned a null executor.");
    }

    AuditService& first = AuditService::instance();
    AuditService& second = AuditService::instance();

    if (&first != &second) {
        throw std::runtime_error("Singleton invariant failed.");
    }

    std::cout << "Factory invariant passed.\n";
    std::cout << "Builder invariant passed.\n";
    std::cout << "Singleton invariant passed.\n";
}

int main() {
    try {
        std::cout << "=== Repository-Style Deployment Case Study ===\n";

        auto productionDeployment = buildProductionDeployment();

        AuditService& audit = AuditService::instance();
        DeploymentEngine engine(audit);

        const DeploymentState state =
            engine.execute(productionDeployment);

        std::cout
            << "Final deployment state: "
            << to_string(state)
            << '\n';

        demonstrateFactory();
        demonstrateInvalidBuild();
        verifyPatterns();

        std::cout << "\n=== Shared Audit Log ===\n";

        for (const auto& event : audit.snapshot()) {
            std::cout << event << '\n';
        }

        return 0;
    } catch (const std::exception& exception) {
        std::cerr << "Fatal error: "
                  << exception.what()
                  << '\n';

        return 1;
    }
}
