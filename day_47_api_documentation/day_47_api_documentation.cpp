#include <algorithm>
#include <cctype>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

/*
 * Repository-independent API governance case study:
 * a release controller for a public operations API.
 *
 * The controller treats the OpenAPI contract as a versioned interface
 * specification, evaluates a candidate release against that specification,
 * and blocks deployment when documented behavior and implementation evidence
 * disagree.
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -Wpedantic api_governance.cpp -o api_governance
 */

enum class Severity {
    Error,
    Warning
};

struct Finding {
    Severity severity;
    std::string code;
    std::string message;
};

struct ResponseContract {
    int status;
    std::string schemaName;
    bool bodyRequired;
};

struct OperationContract {
    std::string operationId;
    std::string method;
    std::string path;
    std::set<int> documentedStatuses;
    std::set<std::string> requiredRequestFields;
    std::set<std::string> allowedRequestFields;
    bool authenticationRequired;
};

struct ImplementationEvidence {
    std::string operationId;
    std::set<int> emittedStatuses;
    std::set<std::string> acceptedRequestFields;
    bool enforcesAuthentication;
};

struct BranchPolicy {
    bool contractTestsRequired = true;
    bool schemaValidationRequired = true;
    bool authenticationReviewRequired = true;
    bool breakingChangeRequiresMajorVersion = true;
};

struct ApiRelease {
    std::string releaseVersion;
    std::string previousVersion;
    bool majorVersionChanged = false;
    bool schemaValidationPassed = false;
    bool contractTestsPassed = false;
    bool securityReviewPassed = false;
    std::vector<OperationContract> operations;
    std::vector<ImplementationEvidence> implementation;
};

class SemanticVersion {
public:
    int major;
    int minor;
    int patch;

    static SemanticVersion parse(const std::string& text) {
        SemanticVersion result{0, 0, 0};
        std::istringstream stream(text);
        char first = '\0';
        char second = '\0';

        if (!(stream >> result.major >> first >> result.minor >> second >> result.patch)
            || first != '.' || second != '.'
            || result.major < 0 || result.minor < 0 || result.patch < 0) {
            throw std::invalid_argument("Version must use MAJOR.MINOR.PATCH format");
        }

        std::string trailing;
        if (stream >> trailing) {
            throw std::invalid_argument("Unexpected text after semantic version");
        }

        return result;
    }
};

class ContractGovernanceEngine {
private:
    BranchPolicy policy_;

    static const ImplementationEvidence* findEvidence(
        const ApiRelease& release,
        const std::string& operationId
    ) {
        const auto iterator = std::find_if(
            release.implementation.begin(),
            release.implementation.end(),
            [&](const ImplementationEvidence& evidence) {
                return evidence.operationId == operationId;
            }
        );

        return iterator == release.implementation.end() ? nullptr : &*iterator;
    }

    static std::vector<std::string> sortedDifference(
        const std::set<std::string>& expected,
        const std::set<std::string>& actual
    ) {
        std::vector<std::string> missing;
        for (const auto& item : expected) {
            if (actual.find(item) == actual.end()) {
                missing.push_back(item);
            }
        }
        return missing;
    }

public:
    explicit ContractGovernanceEngine(BranchPolicy policy)
        : policy_(policy) {}

    std::vector<Finding> evaluate(const ApiRelease& release) const {
        std::vector<Finding> findings;
        const SemanticVersion current = SemanticVersion::parse(release.releaseVersion);
        const SemanticVersion previous = SemanticVersion::parse(release.previousVersion);

        const bool majorChanged = current.major > previous.major;
        if (policy_.breakingChangeRequiresMajorVersion
            && release.majorVersionChanged
            && !majorChanged) {
            findings.push_back({
                Severity::Error,
                "VERSION_POLICY",
                "A declared breaking change requires a higher major version."
            });
        }

        if (policy_.schemaValidationRequired && !release.schemaValidationPassed) {
            findings.push_back({
                Severity::Error,
                "SCHEMA_VALIDATION_FAILED",
                "The release has no passing OpenAPI schema-validation evidence."
            });
        }

        if (policy_.contractTestsRequired && !release.contractTestsPassed) {
            findings.push_back({
                Severity::Error,
                "CONTRACT_TESTS_FAILED",
                "The candidate has not passed its API contract tests."
            });
        }

        if (policy_.authenticationReviewRequired && !release.securityReviewPassed) {
            findings.push_back({
                Severity::Error,
                "SECURITY_REVIEW_FAILED",
                "Authentication and authorization review is incomplete."
            });
        }

        std::set<std::string> operationIds;
        for (const auto& operation : release.operations) {
            if (operation.operationId.empty()) {
                findings.push_back({
                    Severity::Error,
                    "EMPTY_OPERATION_ID",
                    "Every operation must have a stable operationId."
                });
                continue;
            }

            if (!operationIds.insert(operation.operationId).second) {
                findings.push_back({
                    Severity::Error,
                    "DUPLICATE_OPERATION_ID",
                    "Duplicate operationId: " + operation.operationId
                });
            }

            if (operation.path.empty() || operation.path.front() != '/') {
                findings.push_back({
                    Severity::Error,
                    "INVALID_PATH",
                    operation.operationId + " must use an absolute OpenAPI path."
                });
            }

            for (const auto& requiredField : operation.requiredRequestFields) {
                if (operation.allowedRequestFields.find(requiredField)
                    == operation.allowedRequestFields.end()) {
                    findings.push_back({
                        Severity::Error,
                        "INVALID_REQUEST_SCHEMA",
                        operation.operationId + " requires field '" + requiredField
                            + "' but does not allow it."
                    });
                }
            }

            if (operation.documentedStatuses.empty()) {
                findings.push_back({
                    Severity::Error,
                    "MISSING_RESPONSES",
                    operation.operationId + " documents no HTTP responses."
                });
            }

            const ImplementationEvidence* evidence =
                findEvidence(release, operation.operationId);

            if (evidence == nullptr) {
                findings.push_back({
                    Severity::Error,
                    "MISSING_IMPLEMENTATION_EVIDENCE",
                    operation.operationId + " has no implementation evidence."
                });
                continue;
            }

            for (int status : evidence->emittedStatuses) {
                if (operation.documentedStatuses.find(status)
                    == operation.documentedStatuses.end()) {
                    findings.push_back({
                        Severity::Error,
                        "UNDOCUMENTED_STATUS",
                        operation.operationId + " emits HTTP "
                            + std::to_string(status)
                            + " but the contract does not document it."
                    });
                }
            }

            for (int status : operation.documentedStatuses) {
                if (evidence->emittedStatuses.find(status)
                    == evidence->emittedStatuses.end()) {
                    findings.push_back({
                        Severity::Warning,
                        "UNOBSERVED_DOCUMENTED_STATUS",
                        operation.operationId + " documents HTTP "
                            + std::to_string(status)
                            + " but no implementation test exercises it."
                    });
                }
            }

            const auto unexpectedFields = sortedDifference(
                evidence->acceptedRequestFields,
                operation.allowedRequestFields
            );

            for (const auto& field : unexpectedFields) {
                findings.push_back({
                    Severity::Error,
                    "UNDOCUMENTED_REQUEST_FIELD",
                    operation.operationId + " accepts undocumented field '"
                        + field + "'."
                });
            }

            if (operation.authenticationRequired
                && !evidence->enforcesAuthentication) {
                findings.push_back({
                    Severity::Error,
                    "AUTHENTICATION_CONTRACT_MISMATCH",
                    operation.operationId
                        + " requires authentication in OpenAPI but the implementation "
                          "evidence does not demonstrate enforcement."
                });
            }
        }

        for (const auto& evidence : release.implementation) {
            if (operationIds.find(evidence.operationId) == operationIds.end()) {
                findings.push_back({
                    Severity::Error,
                    "UNDOCUMENTED_IMPLEMENTATION",
                    "Implementation exposes unregistered operation "
                        + evidence.operationId + "."
                });
            }
        }

        return findings;
    }

    bool canRelease(const ApiRelease& release) const {
        const auto findings = evaluate(release);
        return std::none_of(
            findings.begin(),
            findings.end(),
            [](const Finding& finding) {
                return finding.severity == Severity::Error;
            }
        );
    }
};

OperationContract makeOperation(
    std::string operationId,
    std::string method,
    std::string path,
    std::set<int> statuses,
    std::set<std::string> requiredFields,
    std::set<std::string> allowedFields,
    bool authenticationRequired
) {
    return {
        std::move(operationId),
        std::move(method),
        std::move(path),
        std::move(statuses),
        std::move(requiredFields),
        std::move(allowedFields),
        authenticationRequired
    };
}

ApiRelease createCandidateRelease() {
    ApiRelease release;
    release.releaseVersion = "2.4.0";
    release.previousVersion = "2.3.1";
    release.majorVersionChanged = false;
    release.schemaValidationPassed = true;
    release.contractTestsPassed = true;
    release.securityReviewPassed = true;

    release.operations = {
        makeOperation(
            "listIncidents", "GET", "/incidents",
            {200, 401}, {}, {}, true
        ),
        makeOperation(
            "createIncident", "POST", "/incidents",
            {201, 400, 401, 409},
            {"title", "severity"},
            {"title", "severity", "description"},
            true
        ),
        makeOperation(
            "getIncident", "GET", "/incidents/{incidentId}",
            {200, 400, 401, 404}, {}, {}, true
        )
    };

    release.implementation = {
        {
            "listIncidents",
            {200, 401},
            {},
            true
        },
        {
            "createIncident",
            {201, 400, 401, 409},
            {"title", "severity", "description"},
            true
        },
        {
            "getIncident",
            {200, 400, 401, 404},
            {},
            true
        }
    };

    return release;
}

void printFindings(const std::vector<Finding>& findings) {
    if (findings.empty()) {
        std::cout << "No contract governance findings.\n";
        return;
    }

    for (const auto& finding : findings) {
        const std::string severity =
            finding.severity == Severity::Error ? "ERROR" : "WARNING";

        std::cout << "[" << severity << "] "
                  << finding.code << ": "
                  << finding.message << '\n';
    }
}

int main() {
    try {
        const BranchPolicy protectedReleasePolicy{
            true,  // OpenAPI schema validation is mandatory.
            true,  // Contract tests must pass before release.
            true,  // Authentication enforcement needs security evidence.
            true   // Breaking changes require a major version increment.
        };

        ContractGovernanceEngine engine(protectedReleasePolicy);
        ApiRelease candidate = createCandidateRelease();

        std::cout << "API Release Governance\n";
        std::cout << "Candidate: " << candidate.releaseVersion << '\n';
        std::cout << "Previous:  " << candidate.previousVersion << "\n\n";

        auto findings = engine.evaluate(candidate);
        printFindings(findings);
        std::cout << "Release eligible: "
                  << (engine.canRelease(candidate) ? "YES" : "NO") << "\n\n";

        // Inject a realistic contract defect: the implementation emits HTTP 429
        // for throttling, but the OpenAPI response map does not document it.
        candidate.implementation[0].emittedStatuses.insert(429);
        candidate.contractTestsPassed = false;

        std::cout << "Evaluating candidate with missing rate-limit documentation\n";
        findings = engine.evaluate(candidate);
        printFindings(findings);
        std::cout << "Release eligible: "
                  << (engine.canRelease(candidate) ? "YES" : "NO") << "\n\n";

        // A security review cannot compensate for an inaccurate API contract.
        candidate.implementation[0].emittedStatuses.erase(429);
        candidate.contractTestsPassed = true;
        candidate.operations[1].allowedRequestFields.insert("internalAdminFlag");
        candidate.implementation[1].acceptedRequestFields.insert("internalAdminFlag");

        std::cout << "Evaluating undocumented request field\n";
        findings = engine.evaluate(candidate);
        printFindings(findings);
        std::cout << "Release eligible: "
                  << (engine.canRelease(candidate) ? "YES" : "NO") << '\n';

        return engine.canRelease(candidate) ? 0 : 2;
    } catch (const std::exception& exception) {
        std::cerr << "Governance execution failed: "
                  << exception.what() << '\n';
        return 1;
    }
}
