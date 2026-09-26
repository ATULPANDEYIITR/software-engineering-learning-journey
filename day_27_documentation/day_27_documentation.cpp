/*
 * Documentation, README, API Documentation, and Technical Documentation
 * =======================================================================
 *
 * C++17 industry-style case study:
 *
 * A Documentation Contract Registry for a versioned API.
 *
 * The program models a realistic documentation engineering problem:
 * maintaining structured API documentation alongside implementation
 * contracts, validating documentation, checking examples, tracking versions,
 * documenting errors, measuring coverage, and producing reference output.
 *
 * The design demonstrates:
 * - Classes and encapsulation
 * - Enumerations
 * - Structs
 * - STL containers
 * - Validation
 * - Exception handling
 * - Serialization-like output
 * - API contracts
 * - Documentation generation
 * - Documentation linting
 * - Security checks
 * - Versioning
 * - Change tracking
 * - Complexity considerations
 * - Unit-style assertions
 *
 * Compile:
 *   g++ -std=c++17 -Wall -Wextra -pedantic documentation_case_study.cpp -o documentation_case_study
 *
 * Run:
 *   ./documentation_case_study
 */

#include <algorithm>
#include <cassert>
#include <cctype>
#include <iomanip>
#include <iostream>
#include <map>
#include <regex>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

using namespace std;


// ===========================================================================
// 1. BASIC DOMAIN TYPES
// ===========================================================================

enum class HttpMethod {
    GET,
    POST,
    PUT,
    PATCH,
    DELETE_METHOD
};


string toString(HttpMethod method) {
    switch (method) {
        case HttpMethod::GET:
            return "GET";
        case HttpMethod::POST:
            return "POST";
        case HttpMethod::PUT:
            return "PUT";
        case HttpMethod::PATCH:
            return "PATCH";
        case HttpMethod::DELETE_METHOD:
            return "DELETE";
    }

    return "UNKNOWN";
}


enum class ParameterLocation {
    PATH,
    QUERY,
    HEADER,
    COOKIE
};


string toString(ParameterLocation location) {
    switch (location) {
        case ParameterLocation::PATH:
            return "path";
        case ParameterLocation::QUERY:
            return "query";
        case ParameterLocation::HEADER:
            return "header";
        case ParameterLocation::COOKIE:
            return "cookie";
    }

    return "unknown";
}


// ===========================================================================
// 2. SEMANTIC VERSIONING
// ===========================================================================

struct Version {
    int major;
    int minor;
    int patch;

    string toString() const {
        return std::to_string(major) + "." +
               std::to_string(minor) + "." +
               std::to_string(patch);
    }
};


string classifyVersionChange(
    const Version& oldVersion,
    const Version& newVersion
) {
    if (newVersion.major != oldVersion.major) {
        return "potentially breaking major contract change";
    }

    if (newVersion.minor != oldVersion.minor) {
        return "backward-compatible feature change";
    }

    if (newVersion.patch != oldVersion.patch) {
        return "backward-compatible correction";
    }

    return "no version change";
}


// ===========================================================================
// 3. API PARAMETER
// ===========================================================================

struct ApiParameter {
    string name;
    ParameterLocation location;
    string type;
    bool required;
    string description;
    string example;
};


// ===========================================================================
// 4. API ENDPOINT CONTRACT
// ===========================================================================

class ApiEndpoint {
private:
    HttpMethod method;
    string path;
    string summary;
    string description;

    vector<ApiParameter> parameters;

    string requestExample;
    int successStatus;

    string successResponse;

    map<int, string> errors;

public:
    ApiEndpoint(
        HttpMethod method,
        string path,
        string summary,
        string description,
        vector<ApiParameter> parameters,
        string requestExample,
        int successStatus,
        string successResponse,
        map<int, string> errors
    )
        : method(method),
          path(move(path)),
          summary(move(summary)),
          description(move(description)),
          parameters(move(parameters)),
          requestExample(move(requestExample)),
          successStatus(successStatus),
          successResponse(move(successResponse)),
          errors(move(errors)) {}

    vector<string> validate() const {
        vector<string> problems;

        if (path.empty() || path.front() != '/') {
            problems.push_back("API path must begin with '/'.");
        }

        if (summary.empty()) {
            problems.push_back("API summary is missing.");
        }

        if (description.empty()) {
            problems.push_back("API description is missing.");
        }

        if (successStatus < 200 || successStatus >= 300) {
            problems.push_back("Success status must be in the 2xx range.");
        }

        if (successResponse.empty()) {
            problems.push_back("Success response is missing.");
        }

        unordered_set<string> parameterNames;

        for (const auto& parameter : parameters) {
            if (parameterNames.find(parameter.name) != parameterNames.end()) {
                problems.push_back(
                    "Duplicate parameter: " + parameter.name
                );
            }

            parameterNames.insert(parameter.name);

            if (parameter.name.empty()) {
                problems.push_back("Parameter name is empty.");
            }

            if (parameter.type.empty()) {
                problems.push_back(
                    "Parameter type is missing: " + parameter.name
                );
            }

            if (parameter.description.empty()) {
                problems.push_back(
                    "Parameter description is missing: " +
                    parameter.name
                );
            }

            if (parameter.required && parameter.example.empty()) {
                problems.push_back(
                    "Required parameter has no example: " +
                    parameter.name
                );
            }
        }

        return problems;
    }

    string toMarkdown() const {
        ostringstream output;

        output << "### `" << toString(method) << " " << path << "`\n\n";
        output << "**Summary:** " << summary << "\n\n";
        output << description << "\n\n";

        if (!parameters.empty()) {
            output << "#### Parameters\n\n";
            output << "| Name | Location | Type | Required | Example | Description |\n";
            output << "|---|---|---|---|---|---|\n";

            for (const auto& parameter : parameters) {
                output << "| `" << parameter.name << "`"
                       << " | `" << toString(parameter.location) << "`"
                       << " | `" << parameter.type << "`"
                       << " | " << (parameter.required ? "Yes" : "No")
                       << " | `" << parameter.example << "`"
                       << " | " << parameter.description
                       << " |\n";
            }

            output << "\n";
        }

        if (!requestExample.empty()) {
            output << "#### Request Example\n\n";
            output << requestExample << "\n\n";
        }

        output << "#### Success Response\n\n";
        output << "HTTP status: `" << successStatus << "`\n\n";
        output << successResponse << "\n\n";

        if (!errors.empty()) {
            output << "#### Errors\n\n";
            output << "| Status | Meaning |\n";
            output << "|---:|---|\n";

            for (const auto& [status, meaning] : errors) {
                output << "| `" << status << "` | "
                       << meaning << " |\n";
            }
        }

        return output.str();
    }

    const string& getPath() const {
        return path;
    }

    HttpMethod getMethod() const {
        return method;
    }
};


// ===========================================================================
// 5. ERROR CATALOG
// ===========================================================================

struct ErrorDefinition {
    string code;
    int httpStatus;
    string meaning;
    string resolution;
};


class ErrorCatalog {
private:
    vector<ErrorDefinition> errors;

public:
    void add(ErrorDefinition error) {
        errors.push_back(move(error));
    }

    const vector<ErrorDefinition>& all() const {
        return errors;
    }

    string toMarkdown() const {
        ostringstream output;

        output << "## Error Reference\n\n";
        output << "| Code | HTTP Status | Meaning | Resolution |\n";
        output << "|---|---:|---|---|\n";

        for (const auto& error : errors) {
            output << "| `" << error.code << "`"
                   << " | `" << error.httpStatus << "`"
                   << " | " << error.meaning
                   << " | " << error.resolution
                   << " |\n";
        }

        return output.str();
    }
};


// ===========================================================================
// 6. TECHNICAL SPECIFICATION
// ===========================================================================

class TechnicalSpecification {
private:
    string problem;
    string scope;

    vector<string> requirements;
    vector<string> architecture;
    vector<string> dataFlow;
    vector<string> failureModes;
    vector<string> operationalNotes;

public:
    TechnicalSpecification(
        string problem,
        string scope,
        vector<string> requirements,
        vector<string> architecture,
        vector<string> dataFlow,
        vector<string> failureModes,
        vector<string> operationalNotes
    )
        : problem(move(problem)),
          scope(move(scope)),
          requirements(move(requirements)),
          architecture(move(architecture)),
          dataFlow(move(dataFlow)),
          failureModes(move(failureModes)),
          operationalNotes(move(operationalNotes)) {}

    vector<string> validate() const {
        vector<string> problems;

        if (problem.empty()) {
            problems.push_back("Problem statement is missing.");
        }

        if (scope.empty()) {
            problems.push_back("Scope is missing.");
        }

        if (requirements.empty()) {
            problems.push_back("Requirements are missing.");
        }

        if (architecture.empty()) {
            problems.push_back("Architecture is missing.");
        }

        if (failureModes.empty()) {
            problems.push_back("Failure modes are missing.");
        }

        return problems;
    }

    string toMarkdown() const {
        ostringstream output;

        output << "# Technical Specification\n\n";

        output << "## Problem\n\n";
        output << problem << "\n\n";

        output << "## Scope\n\n";
        output << scope << "\n\n";

        output << "## Requirements\n\n";
        for (const auto& requirement : requirements) {
            output << "- " << requirement << "\n";
        }

        output << "\n## Architecture\n\n";
        for (const auto& component : architecture) {
            output << "- " << component << "\n";
        }

        output << "\n## Data Flow\n\n";
        for (const auto& step : dataFlow) {
            output << "- " << step << "\n";
        }

        output << "\n## Failure Modes\n\n";
        for (const auto& failure : failureModes) {
            output << "- " << failure << "\n";
        }

        output << "\n## Operational Notes\n\n";
        for (const auto& note : operationalNotes) {
            output << "- " << note << "\n";
        }

        return output.str();
    }
};


// ===========================================================================
// 7. DOCUMENTATION LINTER
// ===========================================================================

class DocumentationLinter {
public:
    vector<string> lint(const string& markdown) const {
        vector<string> problems;

        if (markdown.empty()) {
            problems.push_back("Document is empty.");
            return problems;
        }

        regex titlePattern(R"(^#\s+\S+)");
        bool hasTitle = false;

        {
            istringstream stream(markdown);
            string line;

            while (getline(stream, line)) {
                if (regex_search(line, titlePattern)) {
                    hasTitle = true;
                    break;
                }
            }
        }

        if (!hasTitle) {
            problems.push_back("Missing level-one Markdown heading.");
        }

        size_t fenceCount = 0;
        size_t position = 0;

        while ((position = markdown.find("```", position)) != string::npos) {
            ++fenceCount;
            position += 3;
        }

        if (fenceCount % 2 != 0) {
            problems.push_back("Unbalanced Markdown code fences.");
        }

        return problems;
    }
};


// ===========================================================================
// 8. SECURITY DOCUMENTATION SCANNER
// ===========================================================================

class DocumentationSecurityScanner {
public:
    vector<string> scan(const string& text) const {
        vector<string> findings;

        const regex secretPattern(
            R"((api[_-]?key|password|secret|token)\s*[:=]\s*\S+)",
            regex_constants::icase
        );

        sregex_iterator begin(
            text.begin(),
            text.end(),
            secretPattern
        );

        sregex_iterator end;

        for (auto iterator = begin; iterator != end; ++iterator) {
            findings.push_back(iterator->str());
        }

        return findings;
    }
};


// ===========================================================================
// 9. DOCUMENTATION METRICS
// ===========================================================================

struct DocumentationMetrics {
    size_t characters = 0;
    size_t words = 0;
    size_t lines = 0;
    size_t headings = 0;
};


DocumentationMetrics calculateMetrics(const string& markdown) {
    DocumentationMetrics metrics;

    metrics.characters = markdown.size();

    if (!markdown.empty()) {
        metrics.lines =
            static_cast<size_t>(
                count(markdown.begin(), markdown.end(), '\n')
            ) + 1;
    }

    istringstream words(markdown);
    string word;

    while (words >> word) {
        ++metrics.words;
    }

    istringstream lines(markdown);
    string line;

    while (getline(lines, line)) {
        if (line.size() >= 2 &&
            line[0] == '#' &&
            line[1] == ' ') {
            ++metrics.headings;
        }
    }

    return metrics;
}


// ===========================================================================
// 10. CHANGELOG
// ===========================================================================

struct Change {
    string category;
    string description;
    string issue;
};


class Changelog {
private:
    vector<Change> changes;

public:
    void add(Change change) {
        changes.push_back(move(change));
    }

    string render(const Version& version) const {
        map<string, vector<Change>> grouped;

        for (const auto& change : changes) {
            grouped[change.category].push_back(change);
        }

        ostringstream output;

        output << "## [" << version.toString() << "]\n\n";

        for (const auto& [category, categoryChanges] : grouped) {
            output << "### " << category << "\n\n";

            for (const auto& change : categoryChanges) {
                output << "- " << change.description;

                if (!change.issue.empty()) {
                    output << " (" << change.issue << ")";
                }

                output << "\n";
            }

            output << "\n";
        }

        return output.str();
    }
};


// ===========================================================================
// 11. DOCUMENTATION REGISTRY
// ===========================================================================

class DocumentationRegistry {
private:
    map<string, ApiEndpoint> endpoints;
    ErrorCatalog errorCatalog;

public:
    void registerEndpoint(
        const string& key,
        const ApiEndpoint& endpoint
    ) {
        if (endpoints.find(key) != endpoints.end()) {
            throw runtime_error(
                "An endpoint with this registry key already exists."
            );
        }

        endpoints.emplace(key, endpoint);
    }

    void registerError(ErrorDefinition error) {
        errorCatalog.add(move(error));
    }

    vector<string> validateAll() const {
        vector<string> problems;

        for (const auto& [key, endpoint] : endpoints) {
            const auto endpointProblems = endpoint.validate();

            for (const auto& problem : endpointProblems) {
                problems.push_back(
                    "Endpoint [" + key + "]: " + problem
                );
            }
        }

        return problems;
    }

    string renderApiReference() const {
        ostringstream output;

        output << "# API Reference\n\n";
        output << "This reference describes the documented HTTP contracts.\n\n";

        for (const auto& [key, endpoint] : endpoints) {
            output << "<!-- Registry key: " << key << " -->\n\n";
            output << endpoint.toMarkdown() << "\n\n";
        }

        output << errorCatalog.toMarkdown();

        return output.str();
    }
};


// ===========================================================================
// 12. DOCUMENTATION BUILD PIPELINE
// ===========================================================================

class DocumentationPipeline {
private:
    DocumentationLinter linter;
    DocumentationSecurityScanner securityScanner;

public:
    bool run(const string& markdown) const {
        cout << "\nDocumentation build pipeline:\n";

        const auto lintProblems = linter.lint(markdown);

        if (lintProblems.empty()) {
            cout << "  PASS: Markdown structure\n";
        } else {
            cout << "  FAIL: Markdown structure\n";

            for (const auto& problem : lintProblems) {
                cout << "    - " << problem << "\n";
            }
        }

        const auto securityFindings = securityScanner.scan(markdown);

        if (securityFindings.empty()) {
            cout << "  PASS: security scan\n";
        } else {
            cout << "  FAIL: security scan\n";

            for (const auto& finding : securityFindings) {
                cout << "    - Potential secret: "
                     << finding << "\n";
            }
        }

        return lintProblems.empty() && securityFindings.empty();
    }
};


// ===========================================================================
// 13. USER DOMAIN MODEL
// ===========================================================================

struct User {
    string id;
    string name;
    string email;
};


bool looksLikeEmail(const string& email) {
    /*
     * This is intentionally a lightweight syntax check rather than a complete
     * RFC email validator. Documentation should accurately state the limits
     * of validation rather than implying that a simple regular expression
     * proves an address is deliverable.
     */

    const auto atPosition = email.find('@');

    if (atPosition == string::npos) {
        return false;
    }

    if (atPosition == 0 || atPosition == email.size() - 1) {
        return false;
    }

    const auto dotPosition = email.find('.', atPosition);

    return dotPosition != string::npos &&
           dotPosition > atPosition + 1 &&
           dotPosition < email.size() - 1;
}


class UserService {
private:
    vector<User> users;

public:
    User createUser(const string& name, const string& email) {
        if (name.empty()) {
            throw invalid_argument(
                "name is required and cannot be empty."
            );
        }

        if (!looksLikeEmail(email)) {
            throw invalid_argument(
                "email has invalid basic syntax."
            );
        }

        for (const auto& user : users) {
            if (user.email == email) {
                throw runtime_error(
                    "A user with this email already exists."
                );
            }
        }

        User user{
            "usr_" + to_string(users.size() + 1001),
            name,
            email
        };

        users.push_back(user);

        return user;
    }

    const vector<User>& allUsers() const {
        return users;
    }
};


// ===========================================================================
// 14. API CONTRACT TESTING
// ===========================================================================

void testValidUserCreation(UserService& service) {
    User user = service.createUser(
        "Ada Lovelace",
        "ada@example.com"
    );

    assert(user.id == "usr_1001");
    assert(user.name == "Ada Lovelace");
    assert(user.email == "ada@example.com");
}


void testInvalidName(UserService& service) {
    bool threw = false;

    try {
        service.createUser("", "person@example.com");
    } catch (const invalid_argument&) {
        threw = true;
    }

    assert(threw);
}


void testInvalidEmail(UserService& service) {
    bool threw = false;

    try {
        service.createUser("Grace Hopper", "invalid");
    } catch (const invalid_argument&) {
        threw = true;
    }

    assert(threw);
}


void testDuplicateUser(UserService& service) {
    bool threw = false;

    try {
        service.createUser("Ada Duplicate", "ada@example.com");
    } catch (const runtime_error&) {
        threw = true;
    }

    assert(threw);
}


// ===========================================================================
// 15. MAIN INDUSTRY CASE STUDY
// ===========================================================================

int main() {
    cout << string(78, '=') << "\n";
    cout << "DOCUMENTATION ENGINEERING CASE STUDY\n";
    cout << string(78, '=') << "\n";

    /*
     * Business/technical scenario:
     *
     * A service team owns a versioned user API. The team needs documentation
     * that can be reviewed, validated, generated, tested, and kept aligned
     * with implementation behavior.
     */

    cout << "\nCASE STUDY\n";
    cout << "Problem: maintain a reliable documented API contract.\n";
    cout << "Audience: developers, integrators, operators, and maintainers.\n";


    // -----------------------------------------------------------------------
    // Create endpoint documentation.
    // -----------------------------------------------------------------------

    ApiEndpoint createUserEndpoint(
        HttpMethod::POST,
        "/v1/users",
        "Create a user",
        "Creates a new user after validating the supplied identity fields.",
        {
            {
                "Content-Type",
                ParameterLocation::HEADER,
                "string",
                true,
                "Media type of the request body.",
                "application/json"
            }
        },
        R"({"name":"Ada Lovelace","email":"ada@example.com"})",
        201,
        R"({"id":"usr_1001","name":"Ada Lovelace","email":"ada@example.com"})",
        {
            {400, "The request is malformed or fails validation."},
            {401, "Authentication credentials are missing or invalid."},
            {409, "A user with the same unique identity already exists."},
            {500, "An unexpected server-side failure occurred."}
        }
    );


    ApiEndpoint getUserEndpoint(
        HttpMethod::GET,
        "/v1/users/{id}",
        "Retrieve a user",
        "Returns the user identified by the path parameter.",
        {
            {
                "id",
                ParameterLocation::PATH,
                "string",
                true,
                "Unique user identifier.",
                "usr_1001"
            }
        },
        "",
        200,
        R"({"id":"usr_1001","name":"Ada Lovelace","email":"ada@example.com"})",
        {
            {401, "Authentication credentials are missing or invalid."},
            {404, "The user does not exist."},
            {500, "An unexpected server-side failure occurred."}
        }
    );


    // -----------------------------------------------------------------------
    // Register contracts.
    // -----------------------------------------------------------------------

    DocumentationRegistry registry;

    registry.registerEndpoint(
        "create-user",
        createUserEndpoint
    );

    registry.registerEndpoint(
        "get-user",
        getUserEndpoint
    );


    registry.registerError({
        "INVALID_REQUEST",
        400,
        "The request cannot be parsed or validated.",
        "Correct the request according to the API contract."
    });

    registry.registerError({
        "UNAUTHORIZED",
        401,
        "Authentication is absent or invalid.",
        "Provide valid authentication credentials."
    });

    registry.registerError({
        "NOT_FOUND",
        404,
        "The requested resource does not exist.",
        "Verify the resource identifier."
    });

    registry.registerError({
        "CONFLICT",
        409,
        "The operation conflicts with current resource state.",
        "Refresh state and retry when appropriate."
    });

    registry.registerError({
        "INTERNAL_ERROR",
        500,
        "The server encountered an unexpected condition.",
        "Use the correlation identifier for operational investigation."
    });


    // -----------------------------------------------------------------------
    // Validate API documentation.
    // -----------------------------------------------------------------------

    cout << "\nAPI contract validation:\n";

    const auto contractProblems = registry.validateAll();

    if (contractProblems.empty()) {
        cout << "  PASS: all API contracts are structurally complete.\n";
    } else {
        for (const auto& problem : contractProblems) {
            cout << "  ERROR: " << problem << "\n";
        }
    }


    // -----------------------------------------------------------------------
    // Generate API reference.
    // -----------------------------------------------------------------------

    const string apiReference = registry.renderApiReference();

    cout << "\nGENERATED API REFERENCE\n";
    cout << string(78, '-') << "\n";
    cout << apiReference;


    // -----------------------------------------------------------------------
    // Technical specification.
    // -----------------------------------------------------------------------

    TechnicalSpecification specification(
        "Provide a predictable documented interface for creating and "
        "retrieving users.",
        "The example covers the HTTP contract, validation behavior, "
        "documented failures, and operational considerations.",
        {
            "Requests must use the documented HTTP methods.",
            "Required parameters must be identified.",
            "Request and response examples must correspond to the contract.",
            "Failure conditions must have documented status codes.",
            "Public errors must not reveal internal implementation details."
        },
        {
            "HTTP request layer",
            "Validation layer",
            "Application service",
            "Persistence abstraction",
            "Response serialization",
            "Documentation validation pipeline"
        },
        {
            "Client sends HTTP request.",
            "Request is parsed.",
            "Input is validated.",
            "Application service executes.",
            "Response is serialized.",
            "Documentation contract is tested independently."
        },
        {
            "Malformed request",
            "Missing required value",
            "Invalid value",
            "Duplicate resource",
            "Authentication failure",
            "Unexpected internal failure"
        },
        {
            "Use structured logs.",
            "Monitor latency and error rates.",
            "Do not store credentials in documentation.",
            "Version public contracts deliberately.",
            "Review documentation when implementation changes."
        }
    );


    cout << "\nTECHNICAL SPECIFICATION VALIDATION\n";

    const auto specificationProblems = specification.validate();

    if (specificationProblems.empty()) {
        cout << "  PASS\n";
    } else {
        for (const auto& problem : specificationProblems) {
            cout << "  ERROR: " << problem << "\n";
        }
    }


    // -----------------------------------------------------------------------
    // Documentation linting.
    // -----------------------------------------------------------------------

    DocumentationLinter linter;

    string generatedDocumentation =
        "# User API Documentation\n\n" +
        "This document describes the versioned user API.\n\n" +
        apiReference +
        "\n" +
        specification.toMarkdown();

    const auto lintProblems =
        linter.lint(generatedDocumentation);

    cout << "\nDOCUMENTATION LINT\n";

    if (lintProblems.empty()) {
        cout << "  PASS: no structural Markdown problems.\n";
    } else {
        for (const auto& problem : lintProblems) {
            cout << "  ERROR: " << problem << "\n";
        }
    }


    // -----------------------------------------------------------------------
    // Security scanning.
    // -----------------------------------------------------------------------

    DocumentationSecurityScanner securityScanner;

    const string unsafeExample =
        "# Configuration\n\n"
        "api_key = sk-example-secret-value\n";

    const auto securityFindings =
        securityScanner.scan(unsafeExample);

    cout << "\nSECURITY DOCUMENTATION SCAN\n";

    if (securityFindings.empty()) {
        cout << "  PASS: no obvious secret-like values found.\n";
    } else {
        cout << "  FAIL: possible secret-like values detected.\n";

        for (const auto& finding : securityFindings) {
            cout << "    - " << finding << "\n";
        }
    }


    // -----------------------------------------------------------------------
    // Metrics.
    // -----------------------------------------------------------------------

    const DocumentationMetrics metrics =
        calculateMetrics(generatedDocumentation);

    cout << "\nDOCUMENTATION METRICS\n";
    cout << "  Characters: " << metrics.characters << "\n";
    cout << "  Words:      " << metrics.words << "\n";
    cout << "  Lines:      " << metrics.lines << "\n";
    cout << "  Headings:   " << metrics.headings << "\n";


    // -----------------------------------------------------------------------
    // Semantic versioning.
    // -----------------------------------------------------------------------

    const Version version1{1, 4, 2};
    const Version patchVersion{1, 4, 3};
    const Version minorVersion{1, 5, 0};
    const Version majorVersion{2, 0, 0};

    cout << "\nVERSIONING\n";
    cout << "  " << version1.toString()
         << " -> " << patchVersion.toString()
         << ": "
         << classifyVersionChange(version1, patchVersion)
         << "\n";

    cout << "  " << version1.toString()
         << " -> " << minorVersion.toString()
         << ": "
         << classifyVersionChange(version1, minorVersion)
         << "\n";

    cout << "  " << version1.toString()
         << " -> " << majorVersion.toString()
         << ": "
         << classifyVersionChange(version1, majorVersion)
         << "\n";


    // -----------------------------------------------------------------------
    // Changelog.
    // -----------------------------------------------------------------------

    Changelog changelog;

    changelog.add({
        "Added",
        "Documented user creation endpoint.",
        "#101"
    });

    changelog.add({
        "Changed",
        "Clarified email validation behavior.",
        "#102"
    });

    changelog.add({
        "Fixed",
        "Corrected duplicate-user error documentation.",
        "#103"
    });

    cout << "\nCHANGELOG\n";
    cout << changelog.render(minorVersion);


    // -----------------------------------------------------------------------
    // Application implementation.
    // -----------------------------------------------------------------------

    cout << "\nAPPLICATION BEHAVIOR TESTS\n";

    UserService userService;

    testValidUserCreation(userService);
    cout << "  PASS: valid user creation\n";

    testInvalidName(userService);
    cout << "  PASS: invalid name rejected\n";

    testInvalidEmail(userService);
    cout << "  PASS: invalid email rejected\n";

    testDuplicateUser(userService);
    cout << "  PASS: duplicate user rejected\n";


    // -----------------------------------------------------------------------
    // Edge cases.
    // -----------------------------------------------------------------------

    cout << "\nEDGE CASES\n";

    vector<pair<string, string>> edgeCases = {
        {"", "person@example.com"},
        {"User", "invalid"},
        {"User", "person@example"},
        {"User", "person@example.com"},
        {"Another", "another@example.com"}
    };

    for (const auto& [name, email] : edgeCases) {
        try {
            User user = userService.createUser(name, email);

            cout << "  ACCEPTED: "
                 << user.name
                 << " / "
                 << user.email
                 << "\n";
        } catch (const exception& error) {
            cout << "  REJECTED: "
                 << name
                 << " / "
                 << email
                 << " -> "
                 << error.what()
                 << "\n";
        }
    }


    // -----------------------------------------------------------------------
    // Documentation trade-offs.
    // -----------------------------------------------------------------------

    cout << "\nDOCUMENTATION DESIGN TRADE-OFFS\n";

    cout << "  Generated reference:\n";
    cout << "    Benefit: keeps structured API details synchronized.\n";
    cout << "    Limitation: generated output does not replace rationale.\n";

    cout << "  Large README:\n";
    cout << "    Benefit: central entry point.\n";
    cout << "    Limitation: becomes harder to scan as scope grows.\n";

    cout << "  Focused documentation:\n";
    cout << "    Benefit: separates tutorials, how-to material, concepts, "
            "and reference.\n";
    cout << "    Limitation: requires reliable navigation.\n";

    cout << "  Executable examples:\n";
    cout << "    Benefit: implementation drift can be detected.\n";
    cout << "    Limitation: examples must be maintained and tested.\n";


    // -----------------------------------------------------------------------
    // Production checklist.
    // -----------------------------------------------------------------------

    cout << "\nPRODUCTION CHECKLIST\n";

    const vector<string> checklist = {
        "Audience and purpose are explicit.",
        "Installation and usage instructions are reproducible.",
        "API request and response contracts are complete.",
        "Required and optional values are distinguished.",
        "Errors and recovery behavior are documented.",
        "Authentication and authorization are documented.",
        "Examples contain no real credentials or personal secrets.",
        "Version changes are communicated.",
        "Links are validated.",
        "Documentation examples are tested.",
        "Operational procedures document failure and recovery.",
        "Implementation changes trigger documentation review."
    };

    for (const auto& item : checklist) {
        cout << "  [ ] " << item << "\n";
    }


    // -----------------------------------------------------------------------
    // Complexity discussion.
    // -----------------------------------------------------------------------

    cout << "\nPERFORMANCE CONSIDERATIONS\n";
    cout << "  Endpoint parameter validation: O(P), where P is parameter count.\n";
    cout << "  Documentation heading scan: O(N), where N is document length.\n";
    cout << "  Secret-pattern scan: approximately O(N * R), where R is the number "
            "of patterns.\n";
    cout << "  User duplicate lookup in this demo: O(U), where U is user count.\n";
    cout << "  Production systems can use indexed persistence for faster lookup.\n";


    // -----------------------------------------------------------------------
    // Build final artifact.
    // -----------------------------------------------------------------------

    DocumentationPipeline pipeline;

    const bool buildPassed =
        pipeline.run(generatedDocumentation);

    cout << "\nFINAL DOCUMENTATION BUILD STATUS: "
         << (buildPassed ? "PASS" : "FAIL")
         << "\n";

    cout << "\nINDUSTRY DESIGN PRINCIPLES\n";
    cout << "  1. Documentation is an interface between the system and its users.\n";
    cout << "  2. Reference documentation should describe exact observable behavior.\n";
    cout << "  3. Tutorials should optimize for successful learning workflows.\n";
    cout << "  4. How-to documents should optimize for task completion.\n";
    cout << "  5. Technical documents should record constraints, architecture, "
            "and rationale.\n";
    cout << "  6. Examples should be realistic and tested where practical.\n";
    cout << "  7. Public documentation must never expose secrets.\n";
    cout << "  8. Documentation quality requires accuracy, discoverability, "
            "clarity, and maintainability.\n";

    cout << "\n";
    cout << string(78, '=') << "\n";
    cout << "CASE STUDY COMPLETE\n";
    cout << string(78, '=') << "\n";

    return 0;
}
