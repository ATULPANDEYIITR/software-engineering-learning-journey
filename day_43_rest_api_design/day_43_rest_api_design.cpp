#include <algorithm>
#include <cctype>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * REST API GOVERNANCE AND MERGE-STYLE ELIGIBILITY CASE STUDY
 *
 * The system models a realistic API catalog in which an API gateway
 * evaluates resource URIs, version policy, pagination parameters,
 * and compatibility rules before allowing a client request.
 *
 * The implementation is intentionally independent of an HTTP framework.
 * It focuses on the domain logic that should remain deterministic and
 * testable beneath an HTTP transport layer.
 */

enum class VersionStatus {
    Active,
    Deprecated,
    Retired
};

enum class PaginationStyle {
    PageNumber,
    Cursor
};

struct ApiVersion {
    std::string version;
    VersionStatus status;
    std::string sunsetDate;
};

struct Resource {
    std::string name;
    std::string collectionUri;
    std::string itemUri;
    bool supportsPagination;
    PaginationStyle paginationStyle;
};

struct Request {
    std::string method;
    std::string path;
    std::string query;
};

struct ValidationResult {
    bool accepted;
    int statusCode;
    std::string reason;
    std::vector<std::string> warnings;
};

class ApiCatalog {
private:
    std::vector<ApiVersion> versions;
    std::vector<Resource> resources;

public:
    void addVersion(ApiVersion version) {
        versions.push_back(std::move(version));
    }

    void addResource(Resource resource) {
        resources.push_back(std::move(resource));
    }

    const ApiVersion* findVersion(const std::string& version) const {
        for (const auto& candidate : versions) {
            if (candidate.version == version) {
                return &candidate;
            }
        }

        return nullptr;
    }

    const Resource* findResource(const std::string& path) const {
        for (const auto& resource : resources) {
            if (path == resource.collectionUri ||
                path.rfind(resource.collectionUri + "/", 0) == 0) {
                return &resource;
            }
        }

        return nullptr;
    }
};

class QueryParser {
public:
    static std::map<std::string, std::string> parse(
        const std::string& query
    ) {
        std::map<std::string, std::string> parameters;

        if (query.empty()) {
            return parameters;
        }

        std::stringstream stream(query);
        std::string pair;

        while (std::getline(stream, pair, '&')) {
            const auto delimiter = pair.find('=');

            if (delimiter == std::string::npos) {
                throw std::invalid_argument(
                    "Query parameter must use key=value syntax."
                );
            }

            const std::string key = pair.substr(0, delimiter);
            const std::string value = pair.substr(delimiter + 1);

            if (key.empty()) {
                throw std::invalid_argument(
                    "Query parameter names cannot be empty."
                );
            }

            parameters[key] = value;
        }

        return parameters;
    }

    static int positiveInteger(
        const std::map<std::string, std::string>& parameters,
        const std::string& key,
        int defaultValue
    ) {
        auto iterator = parameters.find(key);

        if (iterator == parameters.end()) {
            return defaultValue;
        }

        const std::string& value = iterator->second;

        if (value.empty()) {
            throw std::invalid_argument(
                key + " cannot be empty."
            );
        }

        for (char character : value) {
            if (!std::isdigit(static_cast<unsigned char>(character))) {
                throw std::invalid_argument(
                    key + " must be a positive integer."
                );
            }
        }

        const int parsed = std::stoi(value);

        if (parsed < 1) {
            throw std::invalid_argument(
                key + " must be greater than zero."
            );
        }

        return parsed;
    }
};

class RestPolicyEngine {
private:
    const ApiCatalog& catalog;

public:
    explicit RestPolicyEngine(const ApiCatalog& catalog)
        : catalog(catalog) {}

    ValidationResult evaluate(const Request& request) const {
        ValidationResult result{
            true,
            200,
            "Request accepted",
            {}
        };

        if (
            request.method != "GET" &&
            request.method != "POST" &&
            request.method != "PUT" &&
            request.method != "PATCH" &&
            request.method != "DELETE" &&
            request.method != "OPTIONS"
        ) {
            return {
                false,
                405,
                "HTTP method is not supported by the API policy.",
                {}
            };
        }

        if (request.path.rfind("/api/", 0) != 0) {
            return {
                false,
                404,
                "URI must begin with the API resource namespace.",
                {}
            };
        }

        const std::string versionPrefix = "/api/";
        const std::size_t versionStart = versionPrefix.size();
        const std::size_t versionEnd =
            request.path.find('/', versionStart);

        if (versionEnd == std::string::npos) {
            return {
                false,
                400,
                "A versioned API URI must identify a resource.",
                {}
            };
        }

        const std::string version =
            request.path.substr(
                versionStart,
                versionEnd - versionStart
            );

        const ApiVersion* apiVersion =
            catalog.findVersion(version);

        if (apiVersion == nullptr) {
            return {
                false,
                404,
                "Requested API version does not exist.",
                {}
            };
        }

        if (apiVersion->status == VersionStatus::Retired) {
            return {
                false,
                410,
                "Requested API version has been retired.",
                {"Migrate to a currently supported version."}
            };
        }

        if (apiVersion->status == VersionStatus::Deprecated) {
            result.warnings.push_back(
                "The API version is deprecated."
            );

            result.warnings.push_back(
                "Sunset date: " + apiVersion->sunsetDate
            );
        }

        const Resource* resource =
            catalog.findResource(request.path);

        if (resource == nullptr) {
            return {
                false,
                404,
                "The requested resource URI is unknown.",
                {}
            };
        }

        if (request.method == "GET" &&
            resource->supportsPagination) {
            try {
                const auto parameters =
                    QueryParser::parse(request.query);

                if (resource->paginationStyle ==
                    PaginationStyle::PageNumber) {
                    const int page =
                        QueryParser::positiveInteger(
                            parameters,
                            "page",
                            1
                        );

                    const int pageSize =
                        QueryParser::positiveInteger(
                            parameters,
                            "page_size",
                            20
                        );

                    if (pageSize > 100) {
                        return {
                            false,
                            400,
                            "page_size exceeds the API maximum of 100.",
                            {}
                        };
                    }

                    if (page > 1 && pageSize == 1) {
                        result.warnings.push_back(
                            "Small page sizes can increase request volume."
                        );
                    }
                }
            } catch (const std::exception& error) {
                return {
                    false,
                    400,
                    error.what(),
                    {}
                };
            }
        }

        if (
            request.method == "POST" &&
            request.path.find("?") != std::string::npos
        ) {
            return {
                false,
                400,
                "Collection creation should not encode resource state in the URI.",
                {}
            };
        }

        return result;
    }
};

void printResult(
    const Request& request,
    const ValidationResult& result
) {
    std::cout << "\n"
              << request.method
              << " "
              << request.path;

    if (!request.query.empty()) {
        std::cout << "?" << request.query;
    }

    std::cout << "\n"
              << "HTTP " << result.statusCode
              << "\n"
              << result.reason
              << "\n";

    for (const auto& warning : result.warnings) {
        std::cout << "Warning: " << warning << "\n";
    }
}

int main() {
    ApiCatalog catalog;

    catalog.addVersion({
        "v1",
        VersionStatus::Active,
        ""
    });

    catalog.addVersion({
        "v2",
        VersionStatus::Deprecated,
        "2027-06-30"
    });

    catalog.addVersion({
        "v0",
        VersionStatus::Retired,
        "2026-01-31"
    });

    catalog.addResource({
        "books",
        "/api/v1/books",
        "/api/v1/books/{id}",
        true,
        PaginationStyle::PageNumber
    });

    catalog.addResource({
        "orders",
        "/api/v1/orders",
        "/api/v1/orders/{id}",
        true,
        PaginationStyle::Cursor
    });

    RestPolicyEngine engine(catalog);

    const std::vector<Request> requests = {
        {"GET", "/api/v1/books", "page=1&page_size=20"},
        {"GET", "/api/v1/books/42", ""},
        {"GET", "/api/v1/books", "page=2&page_size=50"},
        {"GET", "/api/v1/books", "page=0&page_size=20"},
        {"GET", "/api/v1/books", "page=1&page_size=500"},
        {"GET", "/api/v2/books", "page=1&page_size=20"},
        {"GET", "/api/v0/books", "page=1&page_size=20"},
        {"GET", "/api/v9/books", "page=1&page_size=20"},
        {"PATCH", "/api/v1/books/42", ""},
        {"TRACE", "/api/v1/books", ""}
    };

    for (const auto& request : requests) {
        try {
            printResult(
                request,
                engine.evaluate(request)
            );
        } catch (const std::exception& error) {
            std::cout
                << "\nInternal policy evaluation error: "
                << error.what()
                << "\n";
        }
    }

    std::cout << "\nArchitecture decisions\n";
    std::cout
        << "Resource URIs describe nouns rather than controller actions.\n";
    std::cout
        << "Version policy is evaluated independently from resource policy.\n";
    std::cout
        << "Pagination limits are enforced before expensive downstream work.\n";
    std::cout
        << "Deprecated versions can remain callable while returning migration warnings.\n";
    std::cout
        << "Retired versions return 410 rather than pretending that the resource never existed.\n";

    return 0;
}
