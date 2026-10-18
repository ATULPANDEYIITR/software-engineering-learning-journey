#include <algorithm>
#include <chrono>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <regex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Technical case study:
 *
 * A backend gateway receives HTTP-like requests for a repository service.
 * The program models:
 *
 * - server-side request handling
 * - route registration and parameter extraction
 * - middleware execution
 * - authentication and authorization
 * - request validation
 * - centralized error responses
 * - protected administrative routes
 * - route precedence
 * - response timing
 *
 * It deliberately models the backend pipeline rather than relying on an
 * external networking framework, so the core server architecture is visible.
 */

struct Request {
    std::string method;
    std::string target;
    std::string path;
    std::map<std::string, std::string> headers;
    std::map<std::string, std::string> query;
    std::string body;
    std::map<std::string, std::string> params;
    std::map<std::string, std::string> context;
};

struct Response {
    int status;
    std::map<std::string, std::string> headers;
    std::string body;

    static Response json(
        int status,
        const std::string& body
    ) {
        return Response{
            status,
            {
                {"Content-Type", "application/json; charset=utf-8"},
                {"Cache-Control", "no-store"},
                {"X-Content-Type-Options", "nosniff"}
            },
            body
        };
    };
};

class HttpError : public std::runtime_error {
public:
    int status;
    std::string code;

    HttpError(
        int status,
        std::string code,
        std::string message
    )
        : std::runtime_error(std::move(message)),
          status(status),
          code(std::move(code)) {}
};

struct RouteMatch {
    std::map<std::string, std::string> params;
};

class Route {
private:
    std::string method;
    std::string pattern;
    std::regex expression;
    std::vector<std::string> parameterNames;
    int staticSegments;

    static std::string escapeRegex(const std::string& value) {
        std::string result;

        for (char c : value) {
            if (std::string(".^$|()[]*+?{}\\").find(c) != std::string::npos) {
                result += '\\';
            }
            result += c;
        }

        return result;
    }

public:
    Route(
        std::string method,
        std::string pattern
    )
        : method(std::move(method)),
          pattern(std::move(pattern)),
          expression(buildRegex(this->pattern)),
          staticSegments(countStaticSegments(this->pattern)) {
        extractParameters();
    }

    bool matchesMethod(const std::string& requestMethod) const {
        return method == requestMethod;
    }

    std::optional<RouteMatch> match(
        const std::string& requestPath
    ) const {
        std::smatch matches;

        if (!std::regex_match(requestPath, matches, expression)) {
            return std::nullopt;
        }

        RouteMatch result;

        for (std::size_t i = 0; i < parameterNames.size(); ++i) {
            result.params[parameterNames[i]] = matches[i + 1].str();
        }

        return result;
    }

    int staticScore() const {
        return staticSegments;
    }

    const std::string& getMethod() const {
        return method;
    }

private:
    static std::regex buildRegex(const std::string& routePattern) {
        if (routePattern == "/") {
            return std::regex("^/$");
        }

        std::stringstream stream(routePattern);
        std::string segment;
        std::string expressionText = "^";
        bool first = true;

        while (std::getline(stream, segment, '/')) {
            if (segment.empty()) {
                continue;
            }

            expressionText += "/";

            if (segment.front() == ':') {
                expressionText += "([^/]+)";
            } else {
                expressionText += escapeRegex(segment);
            }

            first = false;
        }

        expressionText += "/?$";
        return std::regex(expressionText);
    }

    static int countStaticSegments(const std::string& routePattern) {
        std::stringstream stream(routePattern);
        std::string segment;
        int count = 0;

        while (std::getline(stream, segment, '/')) {
            if (!segment.empty() && segment.front() != ':') {
                ++count;
            }
        }

        return count;
    }

    void extractParameters() {
        std::stringstream stream(pattern);
        std::string segment;

        while (std::getline(stream, segment, '/')) {
            if (segment.size() > 1 && segment.front() == ':') {
                parameterNames.push_back(segment.substr(1));
            }
        }
    }
};

using Handler = std::function<Response(Request&)>;

class Router {
private:
    struct RegisteredRoute {
        Route route;
        Handler handler;
    };

    std::vector<RegisteredRoute> routes;

public:
    void add(
        const std::string& method,
        const std::string& pattern,
        Handler handler
    ) {
        routes.push_back({
            Route(method, pattern),
            std::move(handler)
        });
    }

    Response dispatch(Request& request) const {
        std::vector<const RegisteredRoute*> candidates;

        for (const auto& route : routes) {
            if (route.route.matchesMethod(request.method)) {
                candidates.push_back(&route);
            }
        }

        std::sort(
            candidates.begin(),
            candidates.end(),
            [](const RegisteredRoute* a, const RegisteredRoute* b) {
                return a->route.staticScore() > b->route.staticScore();
            }
        );

        bool pathExistsForAnotherMethod = false;

        for (const auto& route : routes) {
            if (route.route.match(request.path).has_value()) {
                pathExistsForAnotherMethod = true;
                break;
            }
        }

        for (const auto* candidate : candidates) {
            auto matched = candidate->route.match(request.path);

            if (matched.has_value()) {
                request.params = matched->params;
                return candidate->handler(request);
            }
        }

        if (pathExistsForAnotherMethod) {
            throw HttpError(
                405,
                "method_not_allowed",
                "The route exists but does not support this HTTP method."
            );
        }

        throw HttpError(
            404,
            "not_found",
            "No route matches the requested resource."
        );
    }
};

class UserStore {
private:
    struct User {
        std::string id;
        std::string name;
        std::string role;
    };

    std::map<std::string, User> users{
        {"1001", {"1001", "Asha Sharma", "engineer"}},
        {"1002", {"1002", "Ravi Mehta", "reviewer"}}
    };

public:
    std::optional<User> find(const std::string& id) const {
        auto iterator = users.find(id);

        if (iterator == users.end()) {
            return std::nullopt;
        }

        return iterator->second;
    }

    User create(
        const std::string& name,
        const std::string& role
    ) {
        if (name.empty() || name.size() > 100) {
            throw HttpError(
                400,
                "invalid_name",
                "User name must contain between 1 and 100 characters."
            );
        }

        if (
            role != "engineer" &&
            role != "reviewer" &&
            role != "admin"
        ) {
            throw HttpError(
                400,
                "invalid_role",
                "Unsupported user role."
            );
        }

        int highestId = 1000;

        for (const auto& [id, user] : users) {
            highestId = std::max(highestId, std::stoi(id));
        }

        std::string id = std::to_string(highestId + 1);

        User user{id, name, role};
        users.emplace(id, user);

        return user;
    }

    bool erase(const std::string& id) {
        return users.erase(id) > 0;
    }

    std::string toJson(const User& user) const {
        return
            "{\"id\":\"" + user.id +
            "\",\"name\":\"" + user.name +
            "\",\"role\":\"" + user.role + "\"}";
    }

    std::string allAsJson() const {
        std::ostringstream output;
        output << "[";

        bool first = true;

        for (const auto& [id, user] : users) {
            if (!first) {
                output << ",";
            }

            output << toJson(user);
            first = false;
        }

        output << "]";
        return output.str();
    }
};

using Middleware = std::function<Response(Request&, const Handler&)>;

Handler compose(
    const std::vector<Middleware>& middlewares,
    Handler terminal
) {
    Handler current = std::move(terminal);

    for (auto iterator = middlewares.rbegin();
         iterator != middlewares.rend();
         ++iterator) {
        Middleware middleware = *iterator;
        Handler downstream = current;

        current = [
            middleware,
            downstream
        ](Request& request) {
            return middleware(request, downstream);
        };
    }

    return current;
}

std::string requestId() {
    static unsigned long long counter = 0;
    ++counter;

    return "req-" + std::to_string(counter);
}

Middleware requestIdMiddleware() {
    return [](Request& request, const Handler& next) {
        auto iterator = request.headers.find("X-Request-ID");

        if (
            iterator != request.headers.end() &&
            !iterator->second.empty() &&
            iterator->second.size() <= 80
        ) {
            request.context["request_id"] = iterator->second;
        } else {
            request.context["request_id"] = requestId();
        }

        Response response = next(request);
        response.headers["X-Request-ID"] =
            request.context["request_id"];

        return response;
    };
}

Middleware authenticationMiddleware() {
    return [](Request& request, const Handler& next) {
        auto iterator = request.headers.find("Authorization");

        if (
            iterator == request.headers.end() ||
            iterator->second.empty()
        ) {
            throw HttpError(
                401,
                "unauthorized",
                "Authentication is required."
            );
        }

        if (iterator->second == "Bearer demo-admin-token") {
            request.context["user_id"] = "admin-1";
            request.context["role"] = "admin";
        } else if (iterator->second == "Bearer demo-user-token") {
            request.context["user_id"] = "user-1";
            request.context["role"] = "user";
        } else {
            throw HttpError(
                401,
                "unauthorized",
                "The supplied bearer credential is invalid."
            );
        }

        return next(request);
    };
}

Middleware requireRole(const std::string& expectedRole) {
    return [
        expectedRole
    ](Request& request, const Handler& next) {
        auto iterator = request.context.find("role");

        if (
            iterator == request.context.end() ||
            iterator->second != expectedRole
        ) {
            throw HttpError(
                403,
                "forbidden",
                "The authenticated principal lacks the required role."
            );
        }

        return next(request);
    };
}

Middleware timingMiddleware() {
    return [](Request& request, const Handler& next) {
        const auto started =
            std::chrono::steady_clock::now();

        Response response = next(request);

        const auto finished =
            std::chrono::steady_clock::now();

        const auto elapsed =
            std::chrono::duration_cast<
                std::chrono::microseconds
            >(finished - started).count();

        response.headers["X-Response-Time-us"] =
            std::to_string(elapsed);

        return response;
    };
}

int main() {
    UserStore store;
    Router router;

    router.add(
        "GET",
        "/health",
        [](Request&) {
            return Response::json(
                200,
                "{\"status\":\"healthy\",\"service\":\"repository-api\"}"
            );
        }
    );

    router.add(
        "GET",
        "/users",
        [&store](Request&) {
            return Response::json(
                200,
                "{\"users\":" + store.allAsJson() + "}"
            );
        }
    );

    router.add(
        "GET",
        "/users/:id",
        [&store](Request& request) {
            const auto user = store.find(request.params.at("id"));

            if (!user.has_value()) {
                throw HttpError(
                    404,
                    "user_not_found",
                    "The requested user does not exist."
                );
            }

            return Response::json(
                200,
                store.toJson(user.value())
            );
        }
    );

    Handler createUser = [&store](Request& request) {
        /*
         * The case study keeps JSON parsing intentionally small because the
         * important backend boundary is validation after routing and
         * authentication. Production services should use a strict JSON
         * parser and schema validation rather than ad-hoc parsing.
         */
        const auto nameIterator =
            request.headers.find("X-User-Name");

        const auto roleIterator =
            request.headers.find("X-User-Role");

        if (
            nameIterator == request.headers.end() ||
            roleIterator == request.headers.end()
        ) {
            throw HttpError(
                400,
                "missing_user_data",
                "X-User-Name and X-User-Role are required."
            );
        }

        auto user = store.create(
            nameIterator->second,
            roleIterator->second
        );

        return Response::json(
            201,
            store.toJson(user)
        );
    };

    Handler protectedCreate = compose(
        {
            authenticationMiddleware(),
            requireRole("admin")
        },
        createUser
    );

    router.add(
        "POST",
        "/users",
        protectedCreate
    );

    Handler deleteUser = [&store](Request& request) {
        const std::string id = request.params.at("id");

        if (!store.erase(id)) {
            throw HttpError(
                404,
                "user_not_found",
                "The requested user does not exist."
            );
        }

        return Response::json(
            200,
            "{\"deleted\":true,\"id\":\"" + id + "\"}"
        );
    };

    Handler protectedDelete = compose(
        {
            authenticationMiddleware(),
            requireRole("admin")
        },
        deleteUser
    );

    router.add(
        "DELETE",
        "/users/:id",
        protectedDelete
    );

    Handler application = compose(
        {
            requestIdMiddleware(),
            timingMiddleware()
        },
        [&router](Request& request) {
            return router.dispatch(request);
        }
    );

    std::vector<Request> scenarios{
        {
            "GET",
            "/health",
            "/health",
            {},
            {},
            "",
            {},
            {}
        },
        {
            "GET",
            "/users/1001",
            "/users/1001",
            {},
            {},
            "",
            {},
            {}
        },
        {
            "GET",
            "/users/9999",
            "/users/9999",
            {},
            {},
            "",
            {},
            {}
        },
        {
            "POST",
            "/users",
            "/users",
            {
                {"Authorization", "Bearer demo-user-token"},
                {"X-User-Name", "Unauthorized Admin Attempt"},
                {"X-User-Role", "admin"}
            },
            {},
            "",
            {},
            {}
        },
        {
            "POST",
            "/users",
            "/users",
            {
                {"Authorization", "Bearer demo-admin-token"},
                {"X-User-Name", "Neha Singh"},
                {"X-User-Role", "reviewer"}
            },
            {},
            "",
            {},
            {}
        },
        {
            "DELETE",
            "/users/1002",
            "/users/1002",
            {
                {"Authorization", "Bearer demo-admin-token"}
            },
            {},
            "",
            {},
            {}
        }
    };

    for (auto& request : scenarios) {
        try {
            Response response = application(request);

            std::cout
                << request.method << " "
                << request.target
                << " -> "
                << response.status
                << "\n";

            std::cout
                << response.body
                << "\n";

            auto id = response.headers.find("X-Request-ID");

            if (id != response.headers.end()) {
                std::cout
                    << "request-id="
                    << id->second
                    << "\n";
            }

            std::cout << "\n";
        } catch (const HttpError& error) {
            std::cout
                << request.method << " "
                << request.target
                << " -> "
                << error.status
                << "\n";

            std::cout
                << "{\"error\":\""
                << error.code
                << "\",\"message\":\""
                << error.what()
                << "\"}\n\n";
        } catch (const std::exception& error) {
            std::cout
                << "500 internal_server_error: "
                << error.what()
                << "\n\n";
        }
    }

    /*
     * The architecture separates concerns:
     *
     * Router: maps HTTP method and path to a handler.
     * Middleware: applies cross-cutting behavior around handlers.
     * Handler: implements endpoint-specific business behavior.
     * Store: owns domain persistence in this in-memory case study.
     *
     * A real network listener can replace the scenario vector without
     * changing these boundaries.
     */

    return 0;
}
