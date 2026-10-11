#include <algorithm>
#include <chrono>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

/*
 * API Fundamentals case study:
 * A repository service exposes REST resources through an in-memory HTTP-like
 * governance engine. The program focuses on how an API gateway can translate
 * HTTP requests into resource operations while enforcing endpoint contracts.
 *
 * It deliberately models the protocol boundary without requiring an external
 * HTTP library, so the program compiles with standard C++17.
 */

enum class HttpMethod {
    GET,
    POST,
    PUT,
    PATCH,
    DELETE_,
    HEAD
};

std::string toString(HttpMethod method) {
    switch (method) {
        case HttpMethod::GET: return "GET";
        case HttpMethod::POST: return "POST";
        case HttpMethod::PUT: return "PUT";
        case HttpMethod::PATCH: return "PATCH";
        case HttpMethod::DELETE_: return "DELETE";
        case HttpMethod::HEAD: return "HEAD";
    }
    return "UNKNOWN";
}

enum class Status {
    Active,
    Maintenance,
    Archived
};

std::string toString(Status status) {
    switch (status) {
        case Status::Active: return "active";
        case Status::Maintenance: return "maintenance";
        case Status::Archived: return "archived";
    }
    return "unknown";
}

struct Resource {
    int id;
    std::string name;
    std::string category;
    Status status;
    int version;
};

struct HttpRequest {
    HttpMethod method;
    std::string path;
    std::map<std::string, std::string> query;
    std::map<std::string, std::string> headers;
    std::optional<Resource> body;
};

struct HttpResponse {
    int status;
    std::map<std::string, std::string> headers;
    std::string body;
};

class ApiException : public std::runtime_error {
public:
    int status;

    ApiException(int statusCode, const std::string& message)
        : std::runtime_error(message), status(statusCode) {}
};

class ResourceService {
private:
    std::unordered_map<int, Resource> resources;
    int nextId = 1;

    static void validate(const Resource& candidate) {
        if (candidate.name.empty()) {
            throw ApiException(422, "Resource name cannot be empty");
        }

        if (candidate.name.size() > 100) {
            throw ApiException(422, "Resource name exceeds 100 characters");
        }

        if (candidate.category.empty()) {
            throw ApiException(422, "Resource category cannot be empty");
        }
    }

public:
    Resource create(
        const std::string& name,
        const std::string& category,
        Status status
    ) {
        Resource resource{
            nextId++,
            name,
            category,
            status,
            1
        };

        validate(resource);
        resources.emplace(resource.id, resource);
        return resource;
    }

    const Resource& get(int id) const {
        auto it = resources.find(id);

        if (it == resources.end()) {
            throw ApiException(404, "Resource does not exist");
        }

        return it->second;
    }

    Resource replace(int id, const Resource& replacement) {
        auto it = resources.find(id);

        if (it == resources.end()) {
            throw ApiException(404, "Resource does not exist");
        }

        Resource updated = replacement;
        updated.id = id;
        updated.version = it->second.version + 1;

        validate(updated);
        it->second = updated;
        return it->second;
    }

    Resource patch(
        int id,
        const std::optional<std::string>& name,
        const std::optional<std::string>& category,
        const std::optional<Status>& status
    ) {
        auto it = resources.find(id);

        if (it == resources.end()) {
            throw ApiException(404, "Resource does not exist");
        }

        Resource updated = it->second;

        if (name.has_value()) {
            updated.name = *name;
        }

        if (category.has_value()) {
            updated.category = *category;
        }

        if (status.has_value()) {
            updated.status = *status;
        }

        updated.version++;
        validate(updated);
        it->second = updated;

        return it->second;
    }

    void remove(int id) {
        if (resources.erase(id) == 0) {
            throw ApiException(404, "Resource does not exist");
        }
    }

    std::vector<Resource> list(
        const std::optional<std::string>& category
    ) const {
        std::vector<Resource> result;

        for (const auto& [id, resource] : resources) {
            if (!category.has_value() ||
                resource.category == *category) {
                result.push_back(resource);
            }
        }

        std::sort(
            result.begin(),
            result.end(),
            [](const Resource& a, const Resource& b) {
                return a.id < b.id;
            }
        );

        return result;
    }
};

class EndpointParser {
public:
    static std::optional<int> resourceId(const std::string& path) {
        const std::string prefix = "/api/v1/resources/";

        if (path.rfind(prefix, 0) != 0) {
            return std::nullopt;
        }

        std::string idPart = path.substr(prefix.size());

        if (idPart.empty() ||
            !std::all_of(
                idPart.begin(),
                idPart.end(),
                [](unsigned char c) { return std::isdigit(c); }
            )) {
            return std::nullopt;
        }

        try {
            return std::stoi(idPart);
        } catch (...) {
            return std::nullopt;
        }
    }

    static bool isCollection(const std::string& path) {
        return path == "/api/v1/resources";
    }
};

class RestApi {
private:
    ResourceService& service;

    static std::string representation(const Resource& resource) {
        std::ostringstream out;

        out << "{"
            << "\"id\":" << resource.id << ","
            << "\"name\":\"" << resource.name << "\","
            << "\"category\":\"" << resource.category << "\","
            << "\"status\":\"" << toString(resource.status) << "\","
            << "\"version\":" << resource.version
            << "}";

        return out.str();
    }

    static std::string etag(const Resource& resource) {
        return "\"resource-" +
               std::to_string(resource.id) +
               "-v" +
               std::to_string(resource.version) +
               "\"";
    }

    HttpResponse error(int status, const std::string& message) const {
        return {
            status,
            {{"Content-Type", "application/json"}},
            "{\"error\":\"" + message + "\"}"
        };
    }

public:
    explicit RestApi(ResourceService& serviceRef)
        : service(serviceRef) {}

    HttpResponse handle(const HttpRequest& request) {
        try {
            if (EndpointParser::isCollection(request.path)) {
                return collection(request);
            }

            auto id = EndpointParser::resourceId(request.path);

            if (id.has_value()) {
                return member(request, *id);
            }

            return error(404, "Endpoint not found");
        } catch (const ApiException& ex) {
            return error(ex.status, ex.what());
        }
    }

private:
    HttpResponse collection(const HttpRequest& request) {
        if (request.method == HttpMethod::GET) {
            auto category = std::optional<std::string>{};

            auto it = request.query.find("category");
            if (it != request.query.end()) {
                category = it->second;
            }

            const auto resources = service.list(category);

            std::ostringstream body;
            body << "{\"data\":[";

            for (std::size_t i = 0; i < resources.size(); ++i) {
                if (i > 0) {
                    body << ",";
                }
                body << representation(resources[i]);
            }

            body << "]}";

            return {
                200,
                {
                    {"Content-Type", "application/json"},
                    {"Cache-Control", "no-store"}
                },
                body.str()
            };
        }

        if (request.method == HttpMethod::POST) {
            if (!request.body.has_value()) {
                throw ApiException(400, "POST requires a resource representation");
            }

            const Resource& input = *request.body;

            Resource created = service.create(
                input.name,
                input.category,
                input.status
            );

            return {
                201,
                {
                    {"Content-Type", "application/json"},
                    {"Location",
                     "/api/v1/resources/" + std::to_string(created.id)},
                    {"ETag", etag(created)}
                },
                representation(created)
            };
        }

        throw ApiException(405, "Method is not allowed on collection endpoint");
    }

    HttpResponse member(
        const HttpRequest& request,
        int id
    ) {
        const Resource& current = service.get(id);

        if (request.method == HttpMethod::GET) {
            const std::string currentEtag = etag(current);

            auto condition = request.headers.find("If-None-Match");

            if (condition != request.headers.end() &&
                condition->second == currentEtag) {
                return {
                    304,
                    {{"ETag", currentEtag}},
                    ""
                };
            }

            return {
                200,
                {
                    {"Content-Type", "application/json"},
                    {"ETag", currentEtag}
                },
                representation(current)
            };
        }

        if (request.method == HttpMethod::HEAD) {
            return {
                200,
                {
                    {"Content-Type", "application/json"},
                    {"ETag", etag(current)}
                },
                ""
            };
        }

        if (request.method == HttpMethod::PUT) {
            if (!request.body.has_value()) {
                throw ApiException(400, "PUT requires a complete representation");
            }

            Resource updated = service.replace(id, *request.body);

            return {
                200,
                {
                    {"Content-Type", "application/json"},
                    {"ETag", etag(updated)}
                },
                representation(updated)
            };
        }

        if (request.method == HttpMethod::PATCH) {
            if (!request.body.has_value()) {
                throw ApiException(400, "PATCH requires a representation");
            }

            const Resource& patch = *request.body;

            Resource updated = service.patch(
                id,
                patch.name.empty()
                    ? std::nullopt
                    : std::optional<std::string>(patch.name),
                patch.category.empty()
                    ? std::nullopt
                    : std::optional<std::string>(patch.category),
                std::optional<Status>(patch.status)
            );

            return {
                200,
                {
                    {"Content-Type", "application/json"},
                    {"ETag", etag(updated)}
                },
                representation(updated)
            };
        }

        if (request.method == HttpMethod::DELETE_) {
            service.remove(id);

            return {
                204,
                {},
                ""
            };
        }

        throw ApiException(405, "Method is not allowed on member endpoint");
    }
};

void printResponse(
    const std::string& description,
    const HttpResponse& response
) {
    std::cout << "\n" << description << "\n";
    std::cout << "HTTP status: " << response.status << "\n";

    for (const auto& [name, value] : response.headers) {
        std::cout << name << ": " << value << "\n";
    }

    if (!response.body.empty()) {
        std::cout << response.body << "\n";
    }
}

int main() {
    ResourceService service;

    service.create(
        "Customer Identity API",
        "security",
        Status::Active
    );

    service.create(
        "Order Management API",
        "application",
        Status::Active
    );

    service.create(
        "Analytics API",
        "data",
        Status::Maintenance
    );

    RestApi api(service);

    HttpRequest listRequest{
        HttpMethod::GET,
        "/api/v1/resources",
        {},
        {{"Accept", "application/json"}},
        std::nullopt
    };

    printResponse(
        "Retrieve the resource collection",
        api.handle(listRequest)
    );

    HttpRequest getRequest{
        HttpMethod::GET,
        "/api/v1/resources/2",
        {},
        {{"Accept", "application/json"}},
        std::nullopt
    };

    HttpResponse getResponse = api.handle(getRequest);

    printResponse(
        "Retrieve one resource",
        getResponse
    );

    const auto etagHeader = getResponse.headers.at("ETag");

    HttpRequest conditionalRequest{
        HttpMethod::GET,
        "/api/v1/resources/2",
        {},
        {
            {"Accept", "application/json"},
            {"If-None-Match", etagHeader}
        },
        std::nullopt
    };

    printResponse(
        "Conditional GET with If-None-Match",
        api.handle(conditionalRequest)
    );

    HttpRequest updateRequest{
        HttpMethod::PATCH,
        "/api/v1/resources/2",
        {},
        {{"Content-Type", "application/json"}},
        Resource{
            2,
            "Order Management API",
            "application",
            Status::Maintenance,
            0
        }
    };

    printResponse(
        "Partial resource modification",
        api.handle(updateRequest)
    );

    HttpRequest invalidRequest{
        HttpMethod::GET,
        "/api/v1/resources/999",
        {},
        {},
        std::nullopt
    };

    printResponse(
        "Missing resource",
        api.handle(invalidRequest)
    );

    HttpRequest deleteRequest{
        HttpMethod::DELETE_,
        "/api/v1/resources/3",
        {},
        {},
        std::nullopt
    };

    printResponse(
        "Delete a resource",
        api.handle(deleteRequest)
    );

    std::cout
        << "\nCase-study design:\n"
        << "Resource URIs identify domain objects; endpoints expose those "
        << "resources through HTTP methods.\n"
        << "The service layer owns domain validation while the API layer "
        << "translates protocol requests into domain operations.\n"
        << "ETags connect a representation version to HTTP conditional "
        << "requests without changing the resource identity.\n";

    return 0;
}
