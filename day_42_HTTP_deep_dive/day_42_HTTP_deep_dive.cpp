#include <algorithm>
#include <chrono>
#include <cstdint>
#include <iomanip>
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
 * HTTP Deep Dive Case Study
 *
 * Scenario:
 * A repository-like internal service exposes an HTTP API for a document
 * resource. The gateway must evaluate method semantics, conditional requests,
 * request headers, authentication cookies, rate limits, and response status.
 *
 * The implementation intentionally models HTTP protocol behavior rather than
 * performing real socket I/O. This keeps the case study self-contained while
 * making the protocol rules explicit and testable.
 */

enum class HttpMethod {
    GET,
    HEAD,
    POST,
    PUT,
    PATCH,
    DELETE_METHOD,
    OPTIONS
};

std::string toString(HttpMethod method) {
    switch (method) {
        case HttpMethod::GET: return "GET";
        case HttpMethod::HEAD: return "HEAD";
        case HttpMethod::POST: return "POST";
        case HttpMethod::PUT: return "PUT";
        case HttpMethod::PATCH: return "PATCH";
        case HttpMethod::DELETE_METHOD: return "DELETE";
        case HttpMethod::OPTIONS: return "OPTIONS";
    }

    throw std::logic_error("Unknown HTTP method");
}

bool isSafe(HttpMethod method) {
    return method == HttpMethod::GET ||
           method == HttpMethod::HEAD ||
           method == HttpMethod::OPTIONS;
}

bool isIdempotent(HttpMethod method) {
    return isSafe(method) ||
           method == HttpMethod::PUT ||
           method == HttpMethod::DELETE_METHOD;
}

enum class StatusCode {
    OK = 200,
    Created = 201,
    NoContent = 204,
    NotModified = 304,
    TemporaryRedirect = 302,
    BadRequest = 400,
    Unauthorized = 401,
    Forbidden = 403,
    NotFound = 404,
    MethodNotAllowed = 405,
    Conflict = 409,
    PreconditionFailed = 412,
    UnsupportedMediaType = 415,
    UnprocessableContent = 422,
    TooManyRequests = 429,
    InternalServerError = 500,
    ServiceUnavailable = 503
};

int statusNumber(StatusCode status) {
    return static_cast<int>(status);
}

std::string statusPhrase(StatusCode status) {
    switch (status) {
        case StatusCode::OK: return "OK";
        case StatusCode::Created: return "Created";
        case StatusCode::NoContent: return "No Content";
        case StatusCode::NotModified: return "Not Modified";
        case StatusCode::TemporaryRedirect: return "Found";
        case StatusCode::BadRequest: return "Bad Request";
        case StatusCode::Unauthorized: return "Unauthorized";
        case StatusCode::Forbidden: return "Forbidden";
        case StatusCode::NotFound: return "Not Found";
        case StatusCode::MethodNotAllowed: return "Method Not Allowed";
        case StatusCode::Conflict: return "Conflict";
        case StatusCode::PreconditionFailed: return "Precondition Failed";
        case StatusCode::UnsupportedMediaType: return "Unsupported Media Type";
        case StatusCode::UnprocessableContent: return "Unprocessable Content";
        case StatusCode::TooManyRequests: return "Too Many Requests";
        case StatusCode::InternalServerError: return "Internal Server Error";
        case StatusCode::ServiceUnavailable: return "Service Unavailable";
    }

    return "Unknown";
}

class Headers {
private:
    std::map<std::string, std::pair<std::string, std::string>> values;

    static std::string normalize(const std::string& name) {
        std::string result = name;

        std::transform(
            result.begin(),
            result.end(),
            result.begin(),
            [](unsigned char c) {
                return static_cast<char>(std::tolower(c));
            }
        );

        return result;
    }

public:
    void set(const std::string& name, const std::string& value) {
        values[normalize(name)] = {name, value};
    }

    bool contains(const std::string& name) const {
        return values.contains(normalize(name));
    }

    std::optional<std::string> get(const std::string& name) const {
        auto it = values.find(normalize(name));

        if (it == values.end()) {
            return std::nullopt;
        }

        return it->second.second;
    }

    const auto& entries() const {
        return values;
    }
};

struct HttpRequest {
    HttpMethod method;
    std::string path;
    Headers headers;
    std::string body;
};

struct HttpResponse {
    StatusCode status;
    Headers headers;
    std::string body;
};

struct Resource {
    int id;
    std::string name;
    int version;
    std::string etag;
};

struct Session {
    std::string user;
    std::chrono::system_clock::time_point expiresAt;
};

class Cookie {
public:
    std::string name;
    std::string value;
    bool secure{false};
    bool httpOnly{false};
    std::string sameSite{"Lax"};
    std::string path{"/"};
    int maxAge{-1};

    std::string serialize() const {
        std::ostringstream output;

        output << name << "=" << value;
        output << "; Path=" << path;

        if (maxAge >= 0) {
            output << "; Max-Age=" << maxAge;
        }

        if (httpOnly) {
            output << "; HttpOnly";
        }

        if (secure) {
            output << "; Secure";
        }

        if (!sameSite.empty()) {
            output << "; SameSite=" << sameSite;
        }

        return output.str();
    }
};

class CookieJar {
public:
    static std::unordered_map<std::string, std::string>
    parse(const std::string& header) {
        std::unordered_map<std::string, std::string> cookies;
        std::stringstream stream(header);
        std::string part;

        while (std::getline(stream, part, ';')) {
            const auto separator = part.find('=');

            if (separator == std::string::npos) {
                continue;
            }

            std::string name = part.substr(0, separator);
            std::string value = part.substr(separator + 1);

            while (!name.empty() && std::isspace(
                static_cast<unsigned char>(name.front()))) {
                name.erase(name.begin());
            }

            while (!name.empty() && std::isspace(
                static_cast<unsigned char>(name.back()))) {
                name.pop_back();
            }

            cookies[name] = value;
        }

        return cookies;
    }
};

class RateLimiter {
private:
    struct Window {
        std::chrono::steady_clock::time_point started;
        int requests{0};
    };

    int limit;
    std::chrono::seconds windowSize;
    std::unordered_map<std::string, Window> clients;

public:
    RateLimiter(int limit, std::chrono::seconds windowSize)
        : limit(limit), windowSize(windowSize) {}

    bool allow(const std::string& clientId) {
        const auto now = std::chrono::steady_clock::now();
        auto& window = clients[clientId];

        if (window.requests == 0) {
            window.started = now;
        }

        if (now - window.started >= windowSize) {
            window.started = now;
            window.requests = 0;
        }

        if (window.requests >= limit) {
            return false;
        }

        ++window.requests;
        return true;
    }
};

class HttpGateway {
private:
    std::unordered_map<int, Resource> resources;
    std::unordered_map<std::string, Session> sessions;
    RateLimiter rateLimiter{5, std::chrono::seconds(10)};

    static std::string generateSessionId() {
        /*
         * A production session identifier must come from a cryptographically
         * secure random generator. This deterministic-looking case-study
         * token is only a model of the protocol state.
         */
        static std::uint64_t sequence = 1000;
        return "session-" + std::to_string(++sequence);
    }

    HttpResponse json(
        StatusCode status,
        std::string body,
        Headers headers = {}
    ) {
        headers.set("Content-Type", "application/json; charset=utf-8");
        headers.set("Cache-Control", "no-store");

        return {
            status,
            std::move(headers),
            std::move(body)
        };
    }

    std::optional<Session> authenticatedSession(
        const HttpRequest& request
    ) const {
        const auto cookieHeader = request.headers.get("Cookie");

        if (!cookieHeader) {
            return std::nullopt;
        }

        const auto cookies = CookieJar::parse(*cookieHeader);
        const auto sessionIt = cookies.find("session_id");

        if (sessionIt == cookies.end()) {
            return std::nullopt;
        }

        const auto sessionIt2 = sessions.find(sessionIt->second);

        if (sessionIt2 == sessions.end()) {
            return std::nullopt;
        }

        if (std::chrono::system_clock::now() >= sessionIt2->second.expiresAt) {
            return std::nullopt;
        }

        return sessionIt2->second;
    }

public:
    HttpGateway() {
        resources.emplace(
            42,
            Resource{
                42,
                "HTTP protocol resource",
                3,
                "\"resource-42-v3\""
            }
        );
    }

    HttpResponse process(
        const HttpRequest& request,
        const std::string& clientId
    ) {
        if (!rateLimiter.allow(clientId)) {
            Headers headers;
            headers.set("Retry-After", "10");

            return json(
                StatusCode::TooManyRequests,
                R"({"error":"rate_limit_exceeded"})",
                headers
            );
        }

        if (request.method == HttpMethod::OPTIONS) {
            Headers headers;
            headers.set(
                "Allow",
                "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
            );
            headers.set(
                "Access-Control-Allow-Methods",
                "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            );
            headers.set(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization"
            );

            return {
                StatusCode::NoContent,
                headers,
                ""
            };
        }

        if (request.path == "/login" &&
            request.method == HttpMethod::POST) {
            const auto sessionId = generateSessionId();

            Session session{
                "developer@example.test",
                std::chrono::system_clock::now() +
                    std::chrono::hours(1)
            };

            sessions[sessionId] = session;

            Cookie cookie;
            cookie.name = "session_id";
            cookie.value = sessionId;
            cookie.httpOnly = true;
            cookie.sameSite = "Lax";
            cookie.path = "/";
            cookie.maxAge = 3600;

            Headers headers;
            headers.set("Set-Cookie", cookie.serialize());

            return json(
                StatusCode::OK,
                R"({"authenticated":true})",
                headers
            );
        }

        if (request.path == "/me" &&
            (request.method == HttpMethod::GET ||
             request.method == HttpMethod::HEAD)) {
            const auto session = authenticatedSession(request);

            if (!session) {
                Headers headers;
                headers.set(
                    "WWW-Authenticate",
                    R"(Bearer realm="http-demo")"
                );

                return json(
                    StatusCode::Unauthorized,
                    R"({"error":"authentication_required"})",
                    headers
                );
            }

            return json(
                StatusCode::OK,
                "{\"user\":\"" + session->user + "\"}"
            );
        }

        if (request.path != "/resource") {
            return json(
                StatusCode::NotFound,
                R"({"error":"resource_not_found"})"
            );
        }

        auto resourceIt = resources.find(42);

        if (resourceIt == resources.end()) {
            return json(
                StatusCode::NotFound,
                R"({"error":"resource_not_found"})"
            );
        }

        Resource& resource = resourceIt->second;

        if (request.method == HttpMethod::GET ||
            request.method == HttpMethod::HEAD) {
            const auto requestEtag =
                request.headers.get("If-None-Match");

            if (requestEtag &&
                *requestEtag == resource.etag) {
                Headers headers;
                headers.set("ETag", resource.etag);
                headers.set(
                    "Cache-Control",
                    "private, max-age=60"
                );

                return {
                    StatusCode::NotModified,
                    headers,
                    ""
                };
            }

            Headers headers;
            headers.set("ETag", resource.etag);
            headers.set(
                "Cache-Control",
                "private, max-age=60"
            );

            std::string body =
                "{\"id\":" + std::to_string(resource.id) +
                ",\"name\":\"" + resource.name +
                "\",\"version\":" +
                std::to_string(resource.version) + "}";

            if (request.method == HttpMethod::HEAD) {
                return {
                    StatusCode::OK,
                    headers,
                    ""
                };
            }

            return json(StatusCode::OK, body, headers);
        }

        if (request.method == HttpMethod::POST) {
            if (!request.headers.contains("Content-Type") ||
                request.headers.get("Content-Type")->find(
                    "application/json"
                ) == std::string::npos) {
                return json(
                    StatusCode::UnsupportedMediaType,
                    R"({"error":"application_json_required"})"
                );
            }

            if (request.body.empty()) {
                return json(
                    StatusCode::BadRequest,
                    R"({"error":"empty_body"})"
                );
            }

            return json(
                StatusCode::Created,
                R"({"created":true,"location":"/resource/43"})"
            );
        }

        if (request.method == HttpMethod::PUT) {
            resource.name = "replaced resource";
            ++resource.version;
            resource.etag =
                "\"resource-42-v" +
                std::to_string(resource.version) +
                "\"";

            return json(
                StatusCode::OK,
                R"({"replaced":true})"
            );
        }

        if (request.method == HttpMethod::PATCH) {
            if (request.body.empty()) {
                return json(
                    StatusCode::UnprocessableContent,
                    R"({"error":"patch_document_required"})"
                );
            }

            ++resource.version;
            resource.etag =
                "\"resource-42-v" +
                std::to_string(resource.version) +
                "\"";

            return json(
                StatusCode::OK,
                R"({"patched":true})"
            );
        }

        if (request.method == HttpMethod::DELETE_METHOD) {
            resources.erase(resourceIt);

            return {
                StatusCode::NoContent,
                Headers{},
                ""
            };
        }

        return json(
            StatusCode::MethodNotAllowed,
            R"({"error":"method_not_allowed"})"
        );
    }
};

void printResponse(const HttpResponse& response) {
    std::cout
        << statusNumber(response.status)
        << " "
        << statusPhrase(response.status)
        << "\n";

    for (const auto& [normalized, originalAndValue]
         : response.headers.entries()) {
        std::cout
            << originalAndValue.first
            << ": "
            << originalAndValue.second
            << "\n";
    }

    if (!response.body.empty()) {
        std::cout << response.body << "\n";
    }

    std::cout << "----------------------------------------\n";
}

int main() {
    std::cout << "HTTP Deep Dive: C++ Repository-Style Gateway\n";
    std::cout << "============================================\n\n";

    std::cout << "Method properties:\n";

    for (const auto method : {
        HttpMethod::GET,
        HttpMethod::HEAD,
        HttpMethod::POST,
        HttpMethod::PUT,
        HttpMethod::PATCH,
        HttpMethod::DELETE_METHOD,
        HttpMethod::OPTIONS
    }) {
        std::cout
            << std::left
            << std::setw(8)
            << toString(method)
            << " safe=" << std::boolalpha << isSafe(method)
            << " idempotent=" << isIdempotent(method)
            << "\n";
    }

    std::cout << "\nGateway requests:\n";

    HttpGateway gateway;

    HttpRequest getResource{
        HttpMethod::GET,
        "/resource",
        Headers{},
        ""
    };

    printResponse(
        gateway.process(getResource, "client-1")
    );

    HttpRequest conditionalGet{
        HttpMethod::GET,
        "/resource",
        Headers{},
        ""
    };

    conditionalGet.headers.set(
        "If-None-Match",
        "\"resource-42-v3\""
    );

    printResponse(
        gateway.process(conditionalGet, "client-1")
    );

    HttpRequest unsupportedMedia{
        HttpMethod::POST,
        "/resource",
        Headers{},
        R"({"name":"new"})"
    };

    printResponse(
        gateway.process(unsupportedMedia, "client-1")
    );

    HttpRequest validPost{
        HttpMethod::POST,
        "/resource",
        Headers{},
        R"({"name":"new"})"
    };

    validPost.headers.set(
        "Content-Type",
        "application/json"
    );

    printResponse(
        gateway.process(validPost, "client-2")
    );

    HttpRequest login{
        HttpMethod::POST,
        "/login",
        Headers{},
        ""
    };

    const auto loginResponse =
        gateway.process(login, "client-3");

    printResponse(loginResponse);

    const auto cookie =
        loginResponse.headers.get("Set-Cookie");

    if (cookie) {
        const auto separator = cookie->find(';');
        const std::string cookieHeader =
            separator == std::string::npos
                ? *cookie
                : cookie->substr(0, separator);

        HttpRequest me{
            HttpMethod::GET,
            "/me",
            Headers{},
            ""
        };

        me.headers.set("Cookie", cookieHeader);

        printResponse(
            gateway.process(me, "client-3")
        );
    }

    std::cout << "\nSecurity and protocol observations:\n";
    std::cout
        << "A 401 response identifies missing authentication, while 403\n"
        << "represents refusal after the server has understood the request.\n";

    std::cout
        << "ETag and If-None-Match allow the server and client to avoid\n"
        << "transferring an unchanged representation.\n";

    std::cout
        << "HttpOnly, Secure, SameSite, Path, and Max-Age are cookie\n"
        << "attributes with different security and delivery effects.\n";

    std::cout
        << "Rate limiting is represented as a policy layer that can return\n"
        << "429 with Retry-After instead of allowing unlimited requests.\n";

    return 0;
}
