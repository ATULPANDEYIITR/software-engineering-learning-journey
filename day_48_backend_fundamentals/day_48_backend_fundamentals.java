import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/*
 * Enterprise-oriented backend fundamentals case study.
 *
 * The model separates:
 * - HTTP request and response representation
 * - route matching
 * - middleware policy
 * - authentication context
 * - domain validation
 * - endpoint services
 * - centralized error handling
 *
 * Java 17 features such as records, sealed-style domain boundaries through
 * interfaces, immutable request values, collections, and functional
 * composition make the backend pipeline explicit.
 */

public class BackendFundamentals {

    public record HttpRequest(
            String method,
            String path,
            Map<String, String> headers,
            Map<String, String> query,
            String body,
            Map<String, String> routeParameters,
            Map<String, Object> context
    ) {
        public HttpRequest {
            headers = Map.copyOf(headers);
            query = Map.copyOf(query);
            routeParameters = Map.copyOf(routeParameters);
            context = new HashMap<>(context);
        }

        public HttpRequest withRouteParameters(
                Map<String, String> parameters
        ) {
            return new HttpRequest(
                    method,
                    path,
                    headers,
                    query,
                    body,
                    parameters,
                    context
            );
        }
    }

    public record HttpResponse(
            int status,
            Map<String, String> headers,
            String body
    ) {
        public HttpResponse {
            headers = Map.copyOf(headers);
        }

        public HttpResponse withHeader(
                String name,
                String value
        ) {
            Map<String, String> updated =
                    new LinkedHashMap<>(headers);

            updated.put(name, value);

            return new HttpResponse(
                    status,
                    updated,
                    body
            );
        }

        public static HttpResponse json(
                int status,
                String body
        ) {
            return new HttpResponse(
                    status,
                    Map.of(
                            "Content-Type",
                            "application/json; charset=utf-8",
                            "Cache-Control",
                            "no-store",
                            "X-Content-Type-Options",
                            "nosniff"
                    ),
                    body
            );
        }
    }

    public static class HttpException extends RuntimeException {
        private final int status;
        private final String code;

        public HttpException(
                int status,
                String code,
                String message
        ) {
            super(message);
            this.status = status;
            this.code = code;
        }

        public int status() {
            return status;
        }

        public String code() {
            return code;
        }
    }

    @FunctionalInterface
    interface Handler {
        HttpResponse handle(HttpRequest request);
    }

    @FunctionalInterface
    interface Middleware {
        Handler wrap(Handler next);
    }

    record Route(
            String method,
            String pattern,
            Pattern regex,
            List<String> parameterNames,
            int staticSegments,
            Handler handler
    ) {
        Optional<Map<String, String>> match(
                String requestMethod,
                String requestPath
        ) {
            if (!method.equalsIgnoreCase(requestMethod)) {
                return Optional.empty();
            }

            Matcher matcher = regex.matcher(requestPath);

            if (!matcher.matches()) {
                return Optional.empty();
            }

            Map<String, String> parameters =
                    new LinkedHashMap<>();

            for (int i = 0; i < parameterNames.size(); i++) {
                parameters.put(
                        parameterNames.get(i),
                        matcher.group(i + 1)
                );
            }

            return Optional.of(parameters);
        }
    }

    static class Router {
        private final List<Route> routes = new ArrayList<>();

        void add(
                String method,
                String pattern,
                Handler handler
        ) {
            List<String> parameters = new ArrayList<>();
            StringBuilder regexBuilder =
                    new StringBuilder("^");

            int staticSegments = 0;

            for (String segment : pattern.split("/")) {
                if (segment.isEmpty()) {
                    continue;
                }

                regexBuilder.append("/");

                if (segment.startsWith(":")) {
                    parameters.add(
                            segment.substring(1)
                    );
                    regexBuilder.append("([^/]+)");
                } else {
                    staticSegments++;
                    regexBuilder.append(
                            Pattern.quote(segment)
                    );
                }
            }

            regexBuilder.append("/?$");

            routes.add(
                    new Route(
                            method.toUpperCase(),
                            pattern,
                            Pattern.compile(
                                    pattern.equals("/")
                                            ? "^/$"
                                            : regexBuilder.toString()
                            ),
                            List.copyOf(parameters),
                            staticSegments,
                            handler
                    )
            );
        }

        Handler resolve(
                String method,
                String path
        ) {
            List<Route> candidates =
                    routes.stream()
                            .filter(route ->
                                    route.method()
                                            .equalsIgnoreCase(method))
                            .sorted(
                                    Comparator.comparingInt(
                                            Route::staticSegments
                                    ).reversed()
                            )
                            .toList();

            for (Route route : candidates) {
                Optional<Map<String, String>> parameters =
                        route.match(method, path);

                if (parameters.isPresent()) {
                    Map<String, String> values =
                            parameters.get();

                    return request ->
                            route.handler().handle(
                                    request.withRouteParameters(
                                            values
                                    )
                            );
                }
            }

            boolean pathExists =
                    routes.stream()
                            .anyMatch(route ->
                                    route.regex().matcher(path).matches());

            if (pathExists) {
                throw new HttpException(
                        405,
                        "method_not_allowed",
                        "The resource exists but this method is not supported."
                );
            }

            throw new HttpException(
                    404,
                    "not_found",
                    "No route matches this path."
            );
        }
    }

    record User(
            String id,
            String name,
            String role
    ) {}

    interface UserRepository {
        Optional<User> find(String id);

        User save(String name, String role);

        boolean delete(String id);

        List<User> findAll();
    }

    static class InMemoryUserRepository
            implements UserRepository {

        private final Map<String, User> users =
                new LinkedHashMap<>(
                        Map.of(
                                "1001",
                                new User(
                                        "1001",
                                        "Asha Sharma",
                                        "engineer"
                                ),
                                "1002",
                                new User(
                                        "1002",
                                        "Ravi Mehta",
                                        "reviewer"
                                )
                        )
                );

        @Override
        public Optional<User> find(String id) {
            return Optional.ofNullable(users.get(id));
        }

        @Override
        public User save(
                String name,
                String role
        ) {
            validate(name, role);

            int maximumId =
                    users.keySet()
                            .stream()
                            .mapToInt(Integer::parseInt)
                            .max()
                            .orElse(1000);

            String id =
                    String.valueOf(maximumId + 1);

            User user =
                    new User(id, name.trim(), role);

            users.put(id, user);
            return user;
        }

        @Override
        public boolean delete(String id) {
            return users.remove(id) != null;
        }

        @Override
        public List<User> findAll() {
            return List.copyOf(users.values());
        }

        private void validate(
                String name,
                String role
        ) {
            if (name == null ||
                    name.isBlank() ||
                    name.length() > 100) {
                throw new HttpException(
                        400,
                        "invalid_name",
                        "A user name must contain between 1 and 100 characters."
                );
            }

            if (!List.of(
                    "engineer",
                    "reviewer",
                    "admin"
            ).contains(role)) {
                throw new HttpException(
                        400,
                        "invalid_role",
                        "Unsupported user role."
                );
            }
        }
    }

    static class AuthenticationService {

        void authenticate(HttpRequest request) {
            String authorization =
                    request.headers()
                            .getOrDefault(
                                    "Authorization",
                                    ""
                            );

            if (
                    authorization.equals(
                            "Bearer demo-admin-token"
                    )
            ) {
                request.context().put(
                        "userId",
                        "admin-1"
                );
                request.context().put(
                        "role",
                        "admin"
                );
                return;
            }

            if (
                    authorization.equals(
                            "Bearer demo-user-token"
                    )
            ) {
                request.context().put(
                        "userId",
                        "user-1"
                );
                request.context().put(
                        "role",
                        "user"
                );
                return;
            }

            throw new HttpException(
                    401,
                    "unauthorized",
                    "A valid bearer credential is required."
            );
        }
    }

    static Middleware requestIdMiddleware() {
        return next -> request -> {
            String supplied =
                    request.headers()
                            .getOrDefault(
                                    "X-Request-ID",
                                    ""
                            );

            String id =
                    supplied.length() > 0 &&
                            supplied.length() <= 80
                            ? supplied
                            : UUID.randomUUID().toString();

            request.context().put(
                    "requestId",
                    id
            );

            return next.handle(request)
                    .withHeader(
                            "X-Request-ID",
                            id
                    );
        };
    }

    static Middleware timingMiddleware() {
        return next -> request -> {
            Instant started = Instant.now();

            HttpResponse response =
                    next.handle(request);

            long elapsedMicros =
                    Duration.between(
                            started,
                            Instant.now()
                    ).toNanos() / 1_000;

            return response.withHeader(
                    "X-Response-Time-us",
                    String.valueOf(elapsedMicros)
            );
        };
    }

    static Middleware authenticationMiddleware(
            AuthenticationService authenticationService
    ) {
        return next -> request -> {
            authenticationService.authenticate(request);
            return next.handle(request);
        };
    }

    static Middleware requireRole(
            String expectedRole
    ) {
        return next -> request -> {
            Object role =
                    request.context().get("role");

            if (!expectedRole.equals(role)) {
                throw new HttpException(
                        403,
                        "forbidden",
                        "The authenticated principal lacks the required role."
                );
            }

            return next.handle(request);
        };
    }

    static Handler compose(
            List<Middleware> middlewares,
            Handler terminal
    ) {
        Handler current = terminal;

        for (int i = middlewares.size() - 1;
             i >= 0;
             i--) {
            current =
                    middlewares.get(i).wrap(current);
        }

        return current;
    }

    static String userJson(User user) {
        return """
                {"id":"%s","name":"%s","role":"%s"}
                """
                .strip()
                .formatted(
                        user.id(),
                        user.name(),
                        user.role()
                );
    }

    static String usersJson(
            List<User> users
    ) {
        return users.stream()
                .map(BackendFundamentals::userJson)
                .reduce(
                        (left, right) ->
                                left + "," + right
                )
                .map(value ->
                        "{\"users\":[" + value + "]}"
                )
                .orElse("{\"users\":[]}");
    }

    public static void main(String[] args) {

        UserRepository repository =
                new InMemoryUserRepository();

        AuthenticationService authenticationService =
                new AuthenticationService();

        Router router = new Router();

        router.add(
                "GET",
                "/health",
                request ->
                        HttpResponse.json(
                                200,
                                """
                                {"status":"healthy","service":"enterprise-backend"}
                                """
                        )
        );

        router.add(
                "GET",
                "/users",
                request ->
                        HttpResponse.json(
                                200,
                                usersJson(
                                        repository.findAll()
                                )
                        )
        );

        router.add(
                "GET",
                "/users/:id",
                request -> {
                    String id =
                            request.routeParameters()
                                    .get("id");

                    User user =
                            repository.find(id)
                                    .orElseThrow(() ->
                                            new HttpException(
                                                    404,
                                                    "user_not_found",
                                                    "The requested user does not exist."
                                            )
                                    );

                    return HttpResponse.json(
                            200,
                            userJson(user)
                    );
                }
        );

        Handler createUser =
                request -> {
                    /*
                     * The example uses headers for compact scenario input.
                     * A real HTTP adapter would parse JSON and validate a
                     * typed request DTO before invoking this service layer.
                     */
                    String name =
                            request.headers()
                                    .getOrDefault(
                                            "X-User-Name",
                                            ""
                                    );

                    String role =
                            request.headers()
                                    .getOrDefault(
                                            "X-User-Role",
                                            ""
                                    );

                    User user =
                            repository.save(
                                    name,
                                    role
                            );

                    return HttpResponse.json(
                            201,
                            userJson(user)
                    );
                };

        router.add(
                "POST",
                "/users",
                compose(
                        List.of(
                                authenticationMiddleware(
                                        authenticationService
                                ),
                                requireRole("admin")
                        ),
                        createUser
                )
        );

        Handler deleteUser =
                request -> {
                    String id =
                            request.routeParameters()
                                    .get("id");

                    if (!repository.delete(id)) {
                        throw new HttpException(
                                404,
                                "user_not_found",
                                "The requested user does not exist."
                        );
                    }

                    return HttpResponse.json(
                            200,
                            """
                            {"deleted":true}
                            """
                    );
                };

        router.add(
                "DELETE",
                "/users/:id",
                compose(
                        List.of(
                                authenticationMiddleware(
                                        authenticationService
                                ),
                                requireRole("admin")
                        ),
                        deleteUser
                )
        );

        Handler application =
                compose(
                        List.of(
                                requestIdMiddleware(),
                                timingMiddleware()
                        ),
                        request ->
                                router.resolve(
                                        request.method(),
                                        request.path()
                                ).handle(request)
                );

        List<HttpRequest> scenarios =
                List.of(
                        new HttpRequest(
                                "GET",
                                "/health",
                                Map.of(),
                                Map.of(),
                                "",
                                Map.of(),
                                new HashMap<>()
                        ),
                        new HttpRequest(
                                "GET",
                                "/users/1001",
                                Map.of(),
                                Map.of(),
                                "",
                                Map.of(),
                                new HashMap<>()
                        ),
                        new HttpRequest(
                                "GET",
                                "/users/9999",
                                Map.of(),
                                Map.of(),
                                "",
                                Map.of(),
                                new HashMap<>()
                        ),
                        new HttpRequest(
                                "POST",
                                "/users",
                                Map.of(
                                        "Authorization",
                                        "Bearer demo-user-token",
                                        "X-User-Name",
                                        "Unauthorized",
                                        "X-User-Role",
                                        "reviewer"
                                ),
                                Map.of(),
                                "",
                                Map.of(),
                                new HashMap<>()
                        ),
                        new HttpRequest(
                                "POST",
                                "/users",
                                Map.of(
                                        "Authorization",
                                        "Bearer demo-admin-token",
                                        "X-User-Name",
                                        "Neha Singh",
                                        "X-User-Role",
                                        "reviewer"
                                ),
                                Map.of(),
                                "",
                                Map.of(),
                                new HashMap<>()
                        )
                );

        for (HttpRequest request : scenarios) {
            try {
                HttpResponse response =
                        application.handle(request);

                System.out.println(
                        request.method()
                                + " "
                                + request.path()
                                + " -> "
                                + response.status()
                );

                System.out.println(
                        response.body()
                );

                System.out.println(
                        "request-id="
                                + response.headers()
                                .get("X-Request-ID")
                );

                System.out.println();
            } catch (HttpException exception) {
                System.out.println(
                        request.method()
                                + " "
                                + request.path()
                                + " -> "
                                + exception.status()
                );

                System.out.println(
                        """
                        {"error":"%s","message":"%s"}
                        """
                        .formatted(
                                exception.code(),
                                exception.getMessage()
                        )
                );

                System.out.println();
            }
        }
    }
}
