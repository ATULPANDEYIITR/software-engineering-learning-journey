/*
    Software Design Principles Case Study
    DRY, KISS, YAGNI, and Separation of Concerns

    C++17+

    Scenario:
    A release-management service evaluates whether an application deployment
    can proceed. The system has distinct responsibilities for request
    validation, authorization, deployment policy, persistence, and execution.

    The case study deliberately uses C++ value types, enum classes, interfaces,
    dependency injection, unordered_map, filesystem persistence, and explicit
    result objects to show how the four design principles affect a real system.

    Compile:
        g++ -std=c++17 -Wall -Wextra -pedantic design_principles.cpp -o design_principles
*/

#include <algorithm>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>


// ---------------------------------------------------------------------------
// Domain model
// ---------------------------------------------------------------------------

enum class DeploymentStatus {
    Rejected,
    Deployed,
    Failed
};


std::string to_string(DeploymentStatus status) {
    switch (status) {
        case DeploymentStatus::Rejected:
            return "rejected";
        case DeploymentStatus::Deployed:
            return "deployed";
        case DeploymentStatus::Failed:
            return "failed";
    }

    return "unknown";
}


struct Developer {
    std::string username;
    std::string team;
    bool active;
};


struct DeploymentRequest {
    std::string id;
    std::string service;
    std::string version;
    std::string environment;
    std::string requester;
    bool tests_passed;
    int changed_files;
    int risk_score;
};


struct DeploymentRecord {
    DeploymentRequest request;
    DeploymentStatus status;
    std::string reason;
};


// ---------------------------------------------------------------------------
// KISS: small direct functions
// ---------------------------------------------------------------------------

std::string normalize_environment(std::string environment) {
    std::transform(
        environment.begin(),
        environment.end(),
        environment.begin(),
        [](unsigned char character) {
            return static_cast<char>(std::tolower(character));
        }
    );

    return environment;
}


bool is_numeric_component(const std::string& value) {
    if (value.empty()) {
        return false;
    }

    return std::all_of(
        value.begin(),
        value.end(),
        [](unsigned char character) {
            return std::isdigit(character) != 0;
        }
    );
}


bool is_valid_version(const std::string& version) {
    std::stringstream stream(version);
    std::string component;
    int component_count = 0;

    while (std::getline(stream, component, '.')) {
        if (!is_numeric_component(component)) {
            return false;
        }

        ++component_count;
    }

    return component_count == 3;
}


int calculate_risk(int changed_files, bool tests_passed) {
    if (changed_files < 0) {
        throw std::invalid_argument(
            "changed_files cannot be negative"
        );
    }

    int risk = std::min(changed_files / 10, 7);

    if (!tests_passed) {
        risk += 5;
    }

    return std::min(risk, 10);
}


// ---------------------------------------------------------------------------
// Validation responsibility
// ---------------------------------------------------------------------------

class ValidationError : public std::runtime_error {
public:
    explicit ValidationError(const std::string& message)
        : std::runtime_error(message) {}
};


class DeploymentValidator {
public:
    void validate(const DeploymentRequest& request) const {
        if (request.id.empty()) {
            throw ValidationError("deployment id is required");
        }

        if (request.service.empty()) {
            throw ValidationError("service is required");
        }

        if (!is_valid_version(request.version)) {
            throw ValidationError(
                "version must use numeric x.y.z format"
            );
        }

        const std::string environment =
            normalize_environment(request.environment);

        if (
            environment != "staging" &&
            environment != "production"
        ) {
            throw ValidationError(
                "environment must be staging or production"
            );
        }

        if (request.requester.empty()) {
            throw ValidationError("requester is required");
        }

        if (request.changed_files < 0) {
            throw ValidationError(
                "changed_files cannot be negative"
            );
        }

        if (request.risk_score < 0 || request.risk_score > 10) {
            throw ValidationError(
                "risk_score must be between 0 and 10"
            );
        }
    }
};


// ---------------------------------------------------------------------------
// Authorization responsibility
// ---------------------------------------------------------------------------

class AuthorizationService {
private:
    std::unordered_map<std::string, Developer> developers_;

public:
    explicit AuthorizationService(
        std::vector<Developer> developers
    ) {
        for (auto& developer : developers) {
            developers_.emplace(
                developer.username,
                std::move(developer)
            );
        }
    }

    bool can_deploy(
        const DeploymentRequest& request
    ) const {
        const auto iterator =
            developers_.find(request.requester);

        if (iterator == developers_.end()) {
            return false;
        }

        const Developer& developer = iterator->second;

        if (!developer.active) {
            return false;
        }

        const std::string environment =
            normalize_environment(request.environment);

        if (
            environment == "production" &&
            developer.team != "platform"
        ) {
            return false;
        }

        return true;
    }
};


// ---------------------------------------------------------------------------
// DRY: centralized policy configuration
// ---------------------------------------------------------------------------

struct DeploymentPolicy {
    int maximum_automatic_risk = 4;
    int maximum_changed_files = 50;
    bool production_requires_tests = true;
};


class PolicyEngine {
private:
    DeploymentPolicy policy_;

public:
    explicit PolicyEngine(DeploymentPolicy policy)
        : policy_(std::move(policy)) {}

    std::vector<std::string> violations(
        const DeploymentRequest& request
    ) const {
        std::vector<std::string> reasons;

        const std::string environment =
            normalize_environment(request.environment);

        if (
            environment == "production" &&
            policy_.production_requires_tests &&
            !request.tests_passed
        ) {
            reasons.emplace_back(
                "production requires passing tests"
            );
        }

        if (
            request.risk_score >
            policy_.maximum_automatic_risk
        ) {
            reasons.emplace_back(
                "risk exceeds automatic deployment threshold"
            );
        }

        if (
            request.changed_files >
            policy_.maximum_changed_files
        ) {
            reasons.emplace_back(
                "large changes require additional review"
            );
        }

        return reasons;
    }
};


// ---------------------------------------------------------------------------
// Separation of concerns: persistence interface
// ---------------------------------------------------------------------------

class DeploymentRepository {
public:
    virtual ~DeploymentRepository() = default;

    virtual void save(
        const DeploymentRecord& record
    ) = 0;

    virtual std::optional<DeploymentRecord> find(
        const std::string& request_id
    ) const = 0;
};


class MemoryDeploymentRepository : public DeploymentRepository {
private:
    std::unordered_map<std::string, DeploymentRecord> records_;

public:
    void save(
        const DeploymentRecord& record
    ) override {
        records_[record.request.id] = record;
    }

    std::optional<DeploymentRecord> find(
        const std::string& request_id
    ) const override {
        const auto iterator = records_.find(request_id);

        if (iterator == records_.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }
};


// ---------------------------------------------------------------------------
// File persistence
// ---------------------------------------------------------------------------

class AuditFileRepository : public DeploymentRepository {
private:
    std::filesystem::path file_path_;

public:
    explicit AuditFileRepository(
        std::filesystem::path file_path
    )
        : file_path_(std::move(file_path)) {}

    void save(
        const DeploymentRecord& record
    ) override {
        /*
            This deliberately uses a simple line-oriented audit format rather
            than introducing a JSON dependency. The persistence concern is
            separate from deployment policy.
        */
        std::ofstream output(
            file_path_,
            std::ios::app
        );

        if (!output) {
            throw std::runtime_error(
                "unable to open audit file"
            );
        }

        output
            << record.request.id << '|'
            << record.request.service << '|'
            << record.request.version << '|'
            << record.request.environment << '|'
            << record.request.requester << '|'
            << to_string(record.status) << '|'
            << record.reason
            << '\n';
    }

    std::optional<DeploymentRecord> find(
        const std::string&
    ) const override {
        /*
            The current requirements only require append-only audit storage.
            Random lookup is deliberately not implemented because adding an
            indexing subsystem would be speculative for this case study.
        */
        return std::nullopt;
    }
};


// ---------------------------------------------------------------------------
// Deployment execution
// ---------------------------------------------------------------------------

class DeploymentExecutor {
public:
    DeploymentStatus execute(
        const DeploymentRequest& request
    ) const {
        if (!request.tests_passed) {
            return DeploymentStatus::Failed;
        }

        std::cout
            << "deploying "
            << request.service
            << " version "
            << request.version
            << " to "
            << normalize_environment(request.environment)
            << '\n';

        return DeploymentStatus::Deployed;
    }
};


// ---------------------------------------------------------------------------
// Notification responsibility
// ---------------------------------------------------------------------------

class NotificationService {
public:
    void notify(
        const DeploymentRecord& record
    ) const {
        std::cout
            << "notification: "
            << record.request.id
            << " -> "
            << to_string(record.status)
            << " ("
            << record.reason
            << ")\n";
    }
};


// ---------------------------------------------------------------------------
// Orchestration
// ---------------------------------------------------------------------------

class DeploymentService {
private:
    const DeploymentValidator& validator_;
    const AuthorizationService& authorization_;
    const PolicyEngine& policy_;
    DeploymentRepository& repository_;
    const DeploymentExecutor& executor_;
    const NotificationService& notifier_;

    static DeploymentRecord make_record(
        const DeploymentRequest& request,
        DeploymentStatus status,
        const std::string& reason
    ) {
        return DeploymentRecord{
            request,
            status,
            reason
        };
    }

public:
    DeploymentService(
        const DeploymentValidator& validator,
        const AuthorizationService& authorization,
        const PolicyEngine& policy,
        DeploymentRepository& repository,
        const DeploymentExecutor& executor,
        const NotificationService& notifier
    )
        : validator_(validator),
          authorization_(authorization),
          policy_(policy),
          repository_(repository),
          executor_(executor),
          notifier_(notifier) {}

    DeploymentRecord process(
        const DeploymentRequest& request
    ) {
        validator_.validate(request);

        if (
            !authorization_.can_deploy(request)
        ) {
            auto record = make_record(
                request,
                DeploymentStatus::Rejected,
                "requester is not authorized"
            );

            repository_.save(record);
            notifier_.notify(record);
            return record;
        }

        const auto violations =
            policy_.violations(request);

        if (!violations.empty()) {
            std::ostringstream reason;

            for (std::size_t index = 0;
                 index < violations.size();
                 ++index) {
                if (index > 0) {
                    reason << "; ";
                }

                reason << violations[index];
            }

            auto record = make_record(
                request,
                DeploymentStatus::Rejected,
                reason.str()
            );

            repository_.save(record);
            notifier_.notify(record);
            return record;
        }

        const DeploymentStatus status =
            executor_.execute(request);

        const std::string reason =
            status == DeploymentStatus::Deployed
                ? "deployment completed"
                : "deployment execution failed";

        auto record = make_record(
            request,
            status,
            reason
        );

        repository_.save(record);
        notifier_.notify(record);

        return record;
    }
};


// ---------------------------------------------------------------------------
// DRY contrast
// ---------------------------------------------------------------------------

class DuplicatedRulesExample {
public:
    bool allows_staging(
        const DeploymentRequest& request
    ) const {
        /*
            This condition duplicates a policy rule that should normally have
            one source of truth.
        */
        return request.tests_passed &&
               request.risk_score <= 4;
    }

    bool allows_production(
        const DeploymentRequest& request
    ) const {
        /*
            Copying the condition means policy changes can become inconsistent.
        */
        return request.tests_passed &&
               request.risk_score <= 4;
    }
};


// ---------------------------------------------------------------------------
// KISS contrast
// ---------------------------------------------------------------------------

bool is_small_safe_change(
    const DeploymentRequest& request
) {
    /*
        A simple predicate is sufficient. A strategy/factory/registry hierarchy
        would add complexity without representing a current requirement.
    */
    return request.tests_passed &&
           request.changed_files <= 10;
}


// ---------------------------------------------------------------------------
// Assertions
// ---------------------------------------------------------------------------

void run_tests(
    DeploymentService& service,
    DeploymentRepository& repository
) {
    const DeploymentRequest valid_request{
        "DEP-001",
        "payments-api",
        "2.4.1",
        "production",
        "maya",
        true,
        8,
        3
    };

    const DeploymentRecord deployed =
        service.process(valid_request);

    assert(
        deployed.status == DeploymentStatus::Deployed
    );

    const auto stored =
        repository.find("DEP-001");

    assert(stored.has_value());
    assert(
        stored->request.service == "payments-api"
    );


    const DeploymentRequest unauthorized_request{
        "DEP-002",
        "catalog-api",
        "1.2.0",
        "production",
        "leo",
        true,
        4,
        2
    };

    const DeploymentRecord unauthorized =
        service.process(unauthorized_request);

    assert(
        unauthorized.status ==
        DeploymentStatus::Rejected
    );


    const DeploymentRequest risky_request{
        "DEP-003",
        "search-api",
        "3.0.0",
        "staging",
        "leo",
        true,
        80,
        8
    };

    const DeploymentRecord risky =
        service.process(risky_request);

    assert(
        risky.status ==
        DeploymentStatus::Rejected
    );


    const DeploymentRequest failing_tests_request{
        "DEP-004",
        "billing-api",
        "4.0.0",
        "production",
        "maya",
        false,
        2,
        2
    };

    const DeploymentRecord failing_tests =
        service.process(failing_tests_request);

    assert(
        failing_tests.status ==
        DeploymentStatus::Rejected
    );


    try {
        const DeploymentRequest invalid_version{
            "DEP-005",
            "identity-api",
            "not-a-version",
            "staging",
            "maya",
            true,
            2,
            1
        };

        service.process(invalid_version);

        assert(false);
    } catch (const ValidationError&) {
        std::cout
            << "validation edge case correctly rejected\n";
    }
}


// ---------------------------------------------------------------------------
// Main case study
// ---------------------------------------------------------------------------

int main() {
    std::cout
        << "=== Software Design Principles Case Study ===\n"
        << "DRY, KISS, YAGNI, and Separation of Concerns\n\n";


    std::cout << "=== KISS ===\n";

    const DeploymentRequest small_change{
        "KISS-001",
        "profile-api",
        "1.0.0",
        "staging",
        "leo",
        true,
        5,
        1
    };

    std::cout
        << "small safe change: "
        << std::boolalpha
        << is_small_safe_change(small_change)
        << "\n\n";


    std::cout << "=== DRY ===\n";

    DeploymentPolicy policy{
        4,
        50,
        true
    };

    PolicyEngine policy_engine(policy);

    const DeploymentRequest policy_request{
        "DRY-001",
        "analytics-api",
        "2.0.0",
        "production",
        "maya",
        false,
        12,
        6
    };

    const auto findings =
        policy_engine.violations(policy_request);

    for (const auto& finding : findings) {
        std::cout
            << "central policy finding: "
            << finding
            << '\n';
    }

    std::cout << '\n';


    std::cout << "=== Separation of Concerns ===\n";

    DeploymentValidator validator;

    AuthorizationService authorization({
        {"maya", "platform", true},
        {"leo", "application", true},
        {"nina", "application", false}
    });

    MemoryDeploymentRepository repository;
    DeploymentExecutor executor;
    NotificationService notifier;

    DeploymentService service(
        validator,
        authorization,
        policy_engine,
        repository,
        executor,
        notifier
    );

    run_tests(service, repository);

    std::cout << '\n';


    std::cout << "=== YAGNI ===\n";

    std::cout
        << "The system implements the current deployment requirements "
        << "without speculative multi-cloud infrastructure.\n";

    std::cout
        << "The repository abstraction exists because persistence is an "
        << "actual boundary used by the workflow.\n";

    std::cout
        << "A plugin marketplace, workflow DSL, and predictive scaling "
        << "engine are intentionally absent.\n\n";


    std::cout << "=== Design consequences ===\n";

    std::cout
        << "Validation changes belong to DeploymentValidator.\n";

    std::cout
        << "Authorization changes belong to AuthorizationService.\n";

    std::cout
        << "Business policy changes belong to PolicyEngine.\n";

    std::cout
        << "Storage changes occur behind DeploymentRepository.\n";

    std::cout
        << "Execution changes occur inside DeploymentExecutor.\n";

    std::cout
        << "Notification changes do not require policy changes.\n\n";


    std::cout
        << "case study completed successfully\n";

    return 0;
}
