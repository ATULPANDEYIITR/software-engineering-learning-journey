import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;

/*
 * HTTP Deep Dive
 *
 * Enterprise-oriented HTTP governance model.
 *
 * The program models:
 * - method semantics
 * - request and response headers
 * - status classification
 * - cookies and authenticated sessions
 * - ETag-based conditional requests
 * - explicit resource state
 * - content-type validation
 * - rate limiting
 * - exception-based failure handling
 *
 * Java 17 or later.
 */

public class HttpDeepDive {

    enum HttpMethod {
        GET(true, true),
        HEAD(true, true),
        POST(false, false),
        PUT(false, true),
        PATCH(false, false),
        DELETE(true, true),
        OPTIONS(true, true);

        private final boolean safe;
        private final boolean idempotent;

        HttpMethod(boolean safe, boolean idempotent) {
            this.safe = safe;
            this.idempotent = idempotent;
        }

        boolean isSafe() {
            return safe;
        }

        boolean isIdempotent() {
            return idempotent;
        }
    }

    enum StatusClass {
        INFORMATIONAL,
        SUCCESS,
        REDIRECTION,
        CLIENT_ERROR,
        SERVER_ERROR;

        static StatusClass of(int code) {
            if (code >= 100 && code <= 199) {
                return INFORMATIONAL;
            }
            if (code >= 200 && code <= 299) {
                return SUCCESS;
            }
            if (code >= 300 && code <= 399) {
                return REDIRECTION;
            }
            if (code >= 400 && code <= 499) {
                return CLIENT_ERROR;
            }
            if (code >= 500 && code <= 599) {
                return SERVER_ERROR;
            }
            throw new IllegalArgumentException(
                "Invalid HTTP status code: " + code
            );
        }
    }

    record Status(int code, String reason) {
        Status {
            if (code < 100 || code > 599) {
                throw new IllegalArgumentException(
                    "HTTP status must be between 100 and 599."
                );
            }
            Objects.requireNonNull(reason);
        }

        StatusClass category() {
            return StatusClass.of(code);
        }
    }

    static final class Headers {
        private final Map<String, HeaderValue> values = new HashMap<>();

        void set(String name, String value) {
            requireHeaderName(name);
            values.put(
                normalize(name),
                new HeaderValue(name, Objects.requireNonNull(value))
            );
        }

        Optional<String> get(String name) {
            HeaderValue value = values.get(normalize(name));
            return value == null
                ? Optional.empty()
                : Optional.of(value.value());
        }

        boolean contains(String name) {
            return values.containsKey(normalize(name));
        }

        Map<String, String> asMap() {
            Map<String, String> result = new HashMap<>();

            for (HeaderValue value : values.values()) {
                result.put(value.originalName(), value.value());
            }

            return Map.copyOf(result);
        }

        private static String normalize(String name) {
            return name.toLowerCase();
        }

        private static void requireHeaderName(String name) {
            if (name == null ||
                name.isBlank() ||
                name.contains(" ") ||
                name.contains("\r") ||
                name.contains("\n")) {
                throw new IllegalArgumentException(
                    "Invalid HTTP header name."
                );
            }
        }
    }

    record HeaderValue(String originalName, String value) {
    }

    record HttpRequest(
        HttpMethod method,
        String path,
        Headers headers,
        String body
    ) {
        HttpRequest {
            Objects.requireNonNull(method);
            Objects.requireNonNull(path);
            Objects.requireNonNull(headers);
            Objects.requireNonNull(body);

            if (!path.startsWith("/")) {
                throw new IllegalArgumentException(
                    "Request path must begin with '/'."
                );
            }
        }
    }

    record HttpResponse(
        Status status,
        Headers headers,
        String body
    ) {
    }

    record Resource(
        long id,
        String name,
        int version,
        String etag
    ) {
        Resource rename(String newName) {
            return new Resource(
                id,
                newName,
                version + 1,
                "\"resource-" + id + "-v" + (version + 1) + "\""
            );
        }
    }

    record Session(
        String sessionId,
        String username,
        Instant expiresAt
    ) {
        boolean active() {
            return Instant.now().isBefore(expiresAt);
        }
    }

    record Cookie(
        String name,
        String value,
        boolean secure,
        boolean httpOnly,
        String sameSite,
        String path,
        Duration maxAge
    ) {
        Cookie {
            Objects.requireNonNull(name);
            Objects.requireNonNull(value);
            Objects.requireNonNull(sameSite);
            Objects.requireNonNull(path);
            Objects.requireNonNull(maxAge);

            if (name.isBlank()) {
                throw new IllegalArgumentException(
                    "Cookie name cannot be empty."
                );
            }

            if (sameSite.equals("None") && !secure) {
                throw new IllegalArgumentException(
                    "SameSite=None requires Secure."
                );
            }
        }

        String serialize() {
            StringBuilder result =
                new StringBuilder(name)
                    .append("=")
                    .append(value)
                    .append("; Path=")
                    .append(path);

            if (!maxAge.isZero()) {
                result
                    .append("; Max-Age=")
                    .append(maxAge.toSeconds());
            }

            if (httpOnly) {
                result.append("; HttpOnly");
            }

            if (secure) {
                result.append("; Secure");
            }

            result
                .append("; SameSite=")
                .append(sameSite);

            return result.toString();
        }
    }

    static final class CookieParser {

        static Map<String, String> parse(String header) {
            Map<String, String> cookies = new HashMap<>();

            if (header == null || header.isBlank()) {
                return cookies;
            }

            for (String pair : header.split(";")) {
                String[] pieces = pair.trim().split("=", 2);

                if (pieces.length == 2) {
                    cookies.put(
                        pieces[0].trim(),
                        pieces[1].trim()
                    );
                }
            }

            return Map.copyOf(cookies);
        }
    }

    static final class RateLimiter {
        private final int maximumRequests;
        private final Duration window;
        private final Map<String, List<Instant>> history =
            new HashMap<>();

        RateLimiter(int maximumRequests, Duration window) {
            if (maximumRequests <= 0) {
                throw new IllegalArgumentException(
                    "Maximum requests must be positive."
                );
            }

            this.maximumRequests = maximumRequests;
            this.window = Objects.requireNonNull(window);
        }

        boolean allow(String clientId) {
            Instant cutoff = Instant.now().minus(window);

            List<Instant> timestamps =
                history.computeIfAbsent(
                    clientId,
                    ignored -> new ArrayList<>()
                );

            timestamps.removeIf(timestamp ->
                timestamp.isBefore(cutoff)
            );

            if (timestamps.size() >= maximumRequests) {
                return false;
            }

            timestamps.add(Instant.now());
            return true;
        }
    }

    static final class HttpException extends Exception {
        private final Status status;

        HttpException(Status status, String message) {
            super(message);
            this.status = status;
        }

        Status status() {
            return status;
        }
    }

    static final class ResourceService {
        private Resource resource =
            new Resource(
                42,
                "HTTP protocol resource",
                3,
                "\"resource-42-v3\""
            );

        Resource get() {
            return resource;
        }

        void replace(String name) {
            resource = resource.rename(name);
        }

        void patch(String name) {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "PATCH name must not be blank."
                );
            }

            resource = resource.rename(name);
        }

        void delete() {
            resource = null;
        }
    }

    static final class SessionService {
        private final Map<String, Session> sessions =
            new HashMap<>();

        Session create(String username) {
            String sessionId = UUID.randomUUID().toString();

            Session session =
                new Session(
                    sessionId,
                    username,
                    Instant.now().plus(Duration.ofHours(1))
                );

            sessions.put(sessionId, session);

            return session;
        }

        Optional<Session> authenticate(String cookieHeader) {
            Map<String, String> cookies =
                CookieParser.parse(cookieHeader);

            String sessionId = cookies.get("session_id");

            if (sessionId == null) {
                return Optional.empty();
            }

            Session session = sessions.get(sessionId);

            if (session == null || !session.active()) {
                return Optional.empty();
            }

            return Optional.of(session);
        }

        void remove(String sessionId) {
            sessions.remove(sessionId);
        }
    }

    static final class HttpService {
        private final ResourceService resourceService =
            new ResourceService();

        private final SessionService sessionService =
            new SessionService();

        private final RateLimiter rateLimiter =
            new RateLimiter(5, Duration.ofSeconds(10));

        HttpResponse handle(
            HttpRequest request,
            String clientId
        ) {
            try {
                if (!rateLimiter.allow(clientId)) {
                    Headers headers = new Headers();
                    headers.set("Retry-After", "10");

                    return response(
                        429,
                        "Too Many Requests",
                        headers,
                        "{\"error\":\"rate_limit_exceeded\"}"
                    );
                }

                if (request.method() == HttpMethod.OPTIONS) {
                    return optionsResponse();
                }

                if (request.path().equals("/login") &&
                    request.method() == HttpMethod.POST) {
                    return login();
                }

                if (request.path().equals("/logout") &&
                    request.method() == HttpMethod.POST) {
                    return logout(request);
                }

                if (request.path().equals("/me")) {
                    return authenticatedUser(request);
                }

                if (request.path().equals("/resource")) {
                    return resourceRequest(request);
                }

                if (request.path().equals("/redirect") &&
                    request.method() == HttpMethod.GET) {
                    Headers headers = new Headers();
                    headers.set("Location", "/resource");

                    return response(
                        302,
                        "Found",
                        headers,
                        ""
                    );
                }

                return response(
                    404,
                    "Not Found",
                    new Headers(),
                    "{\"error\":\"resource_not_found\"}"
                );

            } catch (HttpException exception) {
                return response(
                    exception.status().code(),
                    exception.status().reason(),
                    new Headers(),
                    "{\"error\":\"" +
                        exception.getMessage() +
                        "\"}"
                );
            } catch (IllegalArgumentException exception) {
                return response(
                    400,
                    "Bad Request",
                    new Headers(),
                    "{\"error\":\"" +
                        exception.getMessage() +
                        "\"}"
                );
            }
        }

        private HttpResponse resourceRequest(
            HttpRequest request
        ) throws HttpException {
            Resource resource = resourceService.get();

            if (resource == null) {
                throw new HttpException(
                    new Status(404, "Not Found"),
                    "resource_not_found"
                );
            }

            return switch (request.method()) {
                case GET -> getResource(request, resource);
                case HEAD -> headResource(resource);
                case POST -> createResource(request);
                case PUT -> replaceResource(request);
                case PATCH -> patchResource(request);
                case DELETE -> deleteResource();
                default -> methodNotAllowed();
            };
        }

        private HttpResponse getResource(
            HttpRequest request,
            Resource resource
        ) {
            Headers headers = resourceHeaders(resource);

            String clientEtag =
                request.headers()
                    .get("If-None-Match")
                    .orElse(null);

            if (resource.etag().equals(clientEtag)) {
                return response(
                    304,
                    "Not Modified",
                    headers,
                    ""
                );
            }

            String body =
                "{\"id\":" + resource.id() +
                ",\"name\":\"" + resource.name() +
                "\",\"version\":" +
                resource.version() + "}";

            return response(
                200,
                "OK",
                headers,
                body
            );
        }

        private HttpResponse headResource(
            Resource resource
        ) {
            return response(
                200,
                "OK",
                resourceHeaders(resource),
                ""
            );
        }

        private HttpResponse createResource(
            HttpRequest request
        ) throws HttpException {
            requireJson(request);

            if (request.body().isBlank()) {
                throw new HttpException(
                    new Status(400, "Bad Request"),
                    "body_required"
                );
            }

            Headers headers = new Headers();
            headers.set("Location", "/resource/43");

            return response(
                201,
                "Created",
                headers,
                "{\"created\":true}"
            );
        }

        private HttpResponse replaceResource(
            HttpRequest request
        ) throws HttpException {
            requireJson(request);

            if (request.body().isBlank()) {
                throw new HttpException(
                    new Status(400, "Bad Request"),
                    "replacement_required"
                );
            }

            resourceService.replace("replaced resource");

            return response(
                200,
                "OK",
                resourceHeaders(resourceService.get()),
                "{\"replaced\":true}"
            );
        }

        private HttpResponse patchResource(
            HttpRequest request
        ) throws HttpException {
            requireJson(request);

            if (request.body().isBlank()) {
                throw new HttpException(
                    new Status(422, "Unprocessable Content"),
                    "patch_document_required"
                );
            }

            resourceService.patch("partially updated resource");

            return response(
                200,
                "OK",
                resourceHeaders(resourceService.get()),
                "{\"patched\":true}"
            );
        }

        private HttpResponse deleteResource() {
            resourceService.delete();

            return response(
                204,
                "No Content",
                new Headers(),
                ""
            );
        }

        private HttpResponse authenticatedUser(
            HttpRequest request
        ) throws HttpException {
            Optional<Session> session =
                sessionService.authenticate(
                    request.headers()
                        .get("Cookie")
                        .orElse("")
                );

            if (session.isEmpty()) {
                Headers headers = new Headers();

                headers.set(
                    "WWW-Authenticate",
                    "Bearer realm=\"http-demo\""
                );

                throw new HttpException(
                    new Status(401, "Unauthorized"),
                    "authentication_required"
                );
            }

            return response(
                200,
                "OK",
                new Headers(),
                "{\"user\":\"" +
                    session.get().username() +
                    "\"}"
            );
        }

        private HttpResponse login() {
            Session session =
                sessionService.create(
                    "developer@example.test"
                );

            Cookie cookie =
                new Cookie(
                    "session_id",
                    session.sessionId(),
                    false,
                    true,
                    "Lax",
                    "/",
                    Duration.ofHours(1)
                );

            Headers headers = new Headers();
            headers.set(
                "Set-Cookie",
                cookie.serialize()
            );

            return response(
                200,
                "OK",
                headers,
                "{\"authenticated\":true}"
            );
        }

        private HttpResponse logout(
            HttpRequest request
        ) {
            Map<String, String> cookies =
                CookieParser.parse(
                    request.headers()
                        .get("Cookie")
                        .orElse("")
                );

            String sessionId =
                cookies.get("session_id");

            if (sessionId != null) {
                sessionService.remove(sessionId);
            }

            Cookie expired =
                new Cookie(
                    "session_id",
                    "",
                    false,
                    true,
                    "Lax",
                    "/",
                    Duration.ZERO
                );

            Headers headers = new Headers();
            headers.set(
                "Set-Cookie",
                expired.serialize()
            );

            return response(
                200,
                "OK",
                headers,
                "{\"authenticated\":false}"
            );
        }

        private HttpResponse optionsResponse() {
            Headers headers = new Headers();

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

            headers.set(
                "Access-Control-Max-Age",
                "600"
            );

            return response(
                204,
                "No Content",
                headers,
                ""
            );
        }

        private HttpResponse methodNotAllowed() {
            Headers headers = new Headers();

            headers.set(
                "Allow",
                "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS"
            );

            return response(
                405,
                "Method Not Allowed",
                headers,
                "{\"error\":\"method_not_allowed\"}"
            );
        }

        private Headers resourceHeaders(Resource resource) {
            Headers headers = new Headers();

            headers.set("ETag", resource.etag());
            headers.set(
                "Cache-Control",
                "private, max-age=60"
            );

            return headers;
        }

        private void requireJson(
            HttpRequest request
        ) throws HttpException {
            String contentType =
                request.headers()
                    .get("Content-Type")
                    .orElse("");

            if (!contentType
                .toLowerCase()
                .startsWith("application/json")) {
                throw new HttpException(
                    new Status(
                        415,
                        "Unsupported Media Type"
                    ),
                    "application_json_required"
                );
            }
        }

        private HttpResponse response(
            int code,
            String reason,
            Headers headers,
            String body
        ) {
            return new HttpResponse(
                new Status(code, reason),
                headers,
                body
            );
        }
    }

    private static HttpRequest request(
        HttpMethod method,
        String path,
        String body
    ) {
        return new HttpRequest(
            method,
            path,
            new Headers(),
            body
        );
    }

    private static void print(
        String title,
        HttpResponse response
    ) {
        System.out.println("[" + title + "]");
        System.out.println(
            response.status().code() +
            " " +
            response.status().reason()
        );
        System.out.println(
            "Class: " +
            response.status().category()
        );

        for (Map.Entry<String, String> entry :
            response.headers().asMap().entrySet()) {
            System.out.println(
                entry.getKey() + ": " + entry.getValue()
            );
        }

        if (!response.body().isBlank()) {
            System.out.println(response.body());
        }

        System.out.println();
    }

    public static void main(String[] args) {
        System.out.println(
            "HTTP Deep Dive: Enterprise HTTP Service Model"
        );
        System.out.println(
            "=============================================="
        );

        System.out.println("\nMethod semantics:");

        Set<HttpMethod> methods =
            EnumSet.allOf(HttpMethod.class);

        for (HttpMethod method : methods) {
            System.out.printf(
                "%-8s safe=%-5s idempotent=%s%n",
                method,
                method.isSafe(),
                method.isIdempotent()
            );
        }

        HttpService service = new HttpService();

        print(
            "GET resource",
            service.handle(
                request(
                    HttpMethod.GET,
                    "/resource",
                    ""
                ),
                "client-a"
            )
        );

        HttpRequest conditional =
            request(
                HttpMethod.GET,
                "/resource",
                ""
            );

        conditional.headers().set(
            "If-None-Match",
            "\"resource-42-v3\""
        );

        print(
            "Conditional GET",
            service.handle(
                conditional,
                "client-b"
            )
        );

        HttpRequest post =
            request(
                HttpMethod.POST,
                "/resource",
                "{\"name\":\"created\"}"
            );

        post.headers().set(
            "Content-Type",
            "application/json"
        );

        print(
            "POST resource",
            service.handle(post, "client-c")
        );

        print(
            "Login",
            service.handle(
                request(
                    HttpMethod.POST,
                    "/login",
                    ""
                ),
                "client-d"
            )
        );

        HttpRequest invalidPost =
            request(
                HttpMethod.POST,
                "/resource",
                "name=created"
            );

        print(
            "Invalid content type",
            service.handle(
                invalidPost,
                "client-e"
            )
        );

        print(
            "OPTIONS",
            service.handle(
                request(
                    HttpMethod.OPTIONS,
                    "/resource",
                    ""
                ),
                "client-f"
            )
        );

        System.out.println(
            "HTTP status classes, headers, cookies, and request "
            + "semantics are modeled as domain types rather than "
            + "unstructured strings wherever possible."
        );
    }
}
