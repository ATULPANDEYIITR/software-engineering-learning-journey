import com.sun.net.httpserver.Headers;
import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.io.InputStream;
import java.net.InetSocketAddress;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * Enterprise-oriented REST API using Java 17 and the JDK HTTP server.
 *
 * Compile:
 *   javac --add-modules jdk.httpserver RestApiServer.java
 *
 * Run:
 *   java --add-modules jdk.httpserver RestApiServer
 */
public class RestApiServer {
    private static final int PORT =
            Integer.parseInt(System.getenv().getOrDefault("API_PORT", "8080"));

    private static final String HOST =
            System.getenv().getOrDefault("API_HOST", "127.0.0.1");

    private static final String API_TOKEN =
            System.getenv().getOrDefault(
                    "API_TOKEN",
                    "local-development-token"
            );

    private static final int MAX_BODY_BYTES = 1_048_576;
    private static final int MAX_TITLE_LENGTH = 160;
    private static final int MAX_DESCRIPTION_LENGTH = 2_000;
    private static final long IDEMPOTENCY_TTL_SECONDS = 86_400;

    private static final Set<String> TASK_STATUSES = Set.of(
            "pending",
            "in_progress",
            "completed",
            "cancelled"
    );

    private static final Map<String, Set<String>> ALLOWED_TRANSITIONS =
            Map.of(
                    "pending", Set.of("in_progress", "cancelled"),
                    "in_progress", Set.of(
                            "pending",
                            "completed",
                            "cancelled"
                    ),
                    "completed", Set.of(),
                    "cancelled", Set.of()
            );

    private static final Pattern VERSION_PATTERN =
            Pattern.compile("\"?([1-9][0-9]*)\"?");

    private static final Pattern ITEM_PATH_PATTERN =
            Pattern.compile("^/v1/tasks/([0-9a-fA-F-]{36})$");

    private final TaskStore store = new TaskStore();
    private final RateLimiter rateLimiter = new RateLimiter(120, 60);
    private final byte[] expectedTokenDigest = sha256(API_TOKEN);

    public static void main(String[] args) throws IOException {
        if (API_TOKEN.length() < 16) {
            throw new IllegalStateException(
                    "API_TOKEN must contain at least 16 characters."
            );
        }

        if ("local-development-token".equals(API_TOKEN)) {
            System.err.println(
                    "WARNING: Set API_TOKEN to a unique secret before deployment."
            );
        }

        new RestApiServer().start();
    }

    private void start() throws IOException {
        HttpServer server = HttpServer.create(
                new InetSocketAddress(HOST, PORT),
                128
        );

        ExecutorService executor = Executors.newFixedThreadPool(8);
        server.setExecutor(executor);
        server.createContext("/", this::handle);

        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            server.stop(1);
            executor.shutdown();
        }));

        server.start();
        System.out.printf(
                "Task API listening on http://%s:%d%n",
                HOST,
                PORT
        );
    }

    private void handle(HttpExchange exchange) {
        String requestId = UUID.randomUUID().toString();
        long started = System.nanoTime();
        int status = 500;

        try {
            exchange.getResponseHeaders().set("X-Request-ID", requestId);
            exchange.getResponseHeaders().set(
                    "X-Content-Type-Options",
                    "nosniff"
            );
            exchange.getResponseHeaders().set("Cache-Control", "no-store");

            status = route(exchange, requestId);
        } catch (ApiException error) {
            status = error.status;
            sendJson(
                    exchange,
                    status,
                    requestId,
                    "{\"error\":{\"code\":" + quote(error.code) +
                            ",\"message\":" + quote(error.getMessage()) + "}}"
            );
        } catch (IllegalArgumentException error) {
            status = 400;
            sendJson(
                    exchange,
                    status,
                    requestId,
                    errorPayload(
                            "invalid_request",
                            error.getMessage()
                    )
            );
        } catch (Exception error) {
            status = 500;
            System.err.printf(
                    "request_id=%s error=%s%n",
                    requestId,
                    error.getClass().getSimpleName()
            );

            sendJson(
                    exchange,
                    status,
                    requestId,
                    errorPayload(
                            "internal_server_error",
                            "An unexpected server error occurred."
                    )
            );
        } finally {
            long elapsedMs =
                    (System.nanoTime() - started) / 1_000_000;

            System.out.printf(
                    "request_id=%s method=%s path=%s status=%d duration_ms=%d%n",
                    requestId,
                    exchange.getRequestMethod(),
                    exchange.getRequestURI().getPath(),
                    status,
                    elapsedMs
            );

            exchange.close();
        }
    }

    private int route(HttpExchange exchange, String requestId)
            throws IOException {
        String method = exchange.getRequestMethod().toUpperCase();
        String path = exchange.getRequestURI().getPath();

        if ("/health".equals(path)) {
            if (!"GET".equals(method)) {
                throw new ApiException(
                        405,
                        "method_not_allowed",
                        "Use GET for the health endpoint."
                );
            }

            sendJson(
                    exchange,
                    200,
                    requestId,
                    "{\"status\":\"healthy\"}"
            );
            return 200;
        }

        if (!path.startsWith("/v1/")) {
            throw new ApiException(
                    404,
                    "route_not_found",
                    "Route does not exist."
            );
        }

        String remoteAddress = exchange.getRemoteAddress()
                .getAddress()
                .getHostAddress();

        if (!rateLimiter.allow(remoteAddress)) {
            throw new ApiException(
                    429,
                    "rate_limit_exceeded",
                    "Too many requests."
            );
        }

        authenticate(exchange.getRequestHeaders());

        if ("/v1/tasks".equals(path)) {
            return handleCollection(exchange, method, requestId);
        }

        Matcher itemMatcher = ITEM_PATH_PATTERN.matcher(path);
        if (itemMatcher.matches()) {
            return handleItem(
                    exchange,
                    method,
                    requestId,
                    itemMatcher.group(1)
            );
        }

        throw new ApiException(
                404,
                "route_not_found",
                "Route does not exist."
        );
    }

    private void authenticate(Headers headers) {
        String authorization = headers.getFirst("Authorization");
        String supplied = authorization != null &&
                authorization.startsWith("Bearer ")
                ? authorization.substring(7)
                : "";

        // Digests have equal length before constant-time comparison.
        if (!MessageDigest.isEqual(
                sha256(supplied),
                expectedTokenDigest
        )) {
            throw new ApiException(
                    401,
                    "unauthorized",
                    "A valid bearer token is required."
            );
        }
    }

    private int handleCollection(
            HttpExchange exchange,
            String method,
            String requestId
    ) throws IOException {
        if ("GET".equals(method)) {
            Map<String, String> query = parseQuery(
                    exchange.getRequestURI().getRawQuery()
            );

            Integer limit = parseInteger(
                    query.get("limit"),
                    20,
                    1,
                    100,
                    "limit"
            );

            Integer offset = parseInteger(
                    query.get("offset"),
                    0,
                    0,
                    1_000_000,
                    "offset"
            );

            String status = query.get("status");
            if (status != null && !TASK_STATUSES.contains(status)) {
                throw new ApiException(
                        400,
                        "invalid_status",
                        "Unsupported task status."
                );
            }

            List<Task> tasks = store.list(status, limit, offset);
            String items = tasks.stream()
                    .map(Task::toJson)
                    .collect(Collectors.joining(","));

            String body =
                    "{\"data\":[" + items + "]," +
                    "\"pagination\":{\"limit\":" + limit +
                    ",\"offset\":" + offset +
                    ",\"returned\":" + tasks.size() + "}}";

            sendJson(exchange, 200, requestId, body);
            return 200;
        }

        if ("POST".equals(method)) {
            Map<String, String> body = readJsonObject(exchange);
            rejectUnknownFields(body, Set.of("title", "description"));

            String title = validateTitle(body.get("title"));
            String description = validateDescription(
                    body.getOrDefault("description", "")
            );

            String key = exchange.getRequestHeaders()
                    .getFirst("Idempotency-Key");

            validateIdempotencyKey(key);

            CreateResult result = store.create(
                    title,
                    description,
                    key
            );

            Headers responseHeaders =
                    exchange.getResponseHeaders();

            responseHeaders.set(
                    "ETag",
                    "\"" + result.task().version() + "\""
            );

            if (result.replayed()) {
                responseHeaders.set("Idempotent-Replayed", "true");
            }

            int responseStatus = result.replayed() ? 200 : 201;
            sendJson(
                    exchange,
                    responseStatus,
                    requestId,
                    "{\"data\":" + result.task().toJson() + "}"
            );
            return responseStatus;
        }

        throw new ApiException(
                405,
                "method_not_allowed",
                "Collection methods are GET and POST."
        );
    }

    private int handleItem(
            HttpExchange exchange,
            String method,
            String requestId,
            String taskId
    ) throws IOException {
        try {
            taskId = UUID.fromString(taskId).toString();
        } catch (IllegalArgumentException error) {
            throw new ApiException(
                    404,
                    "task_not_found",
                    "Task does not exist."
            );
        }

        if ("GET".equals(method)) {
            Task task = store.get(taskId);
            exchange.getResponseHeaders().set(
                    "ETag",
                    "\"" + task.version() + "\""
            );

            sendJson(
                    exchange,
                    200,
                    requestId,
                    "{\"data\":" + task.toJson() + "}"
            );
            return 200;
        }

        if ("PATCH".equals(method)) {
            int expectedVersion = parseIfMatch(
                    exchange.getRequestHeaders().getFirst("If-Match")
            );

            Map<String, String> changes = readJsonObject(exchange);
            rejectUnknownFields(
                    changes,
                    Set.of("title", "description", "status")
            );

            if (changes.isEmpty()) {
                throw new ApiException(
                        400,
                        "empty_patch",
                        "At least one field must be supplied."
                );
            }

            if (changes.containsKey("title")) {
                changes.put(
                        "title",
                        validateTitle(changes.get("title"))
                );
            }

            if (changes.containsKey("description")) {
                changes.put(
                        "description",
                        validateDescription(changes.get("description"))
                );
            }

            if (changes.containsKey("status")) {
                changes.put(
                        "status",
                        validateStatus(changes.get("status"))
                );
            }

            Task task = store.update(
                    taskId,
                    expectedVersion,
                    changes
            );

            exchange.getResponseHeaders().set(
                    "ETag",
                    "\"" + task.version() + "\""
            );

            sendJson(
                    exchange,
                    200,
                    requestId,
                    "{\"data\":" + task.toJson() + "}"
            );
            return 200;
        }

        if ("DELETE".equals(method)) {
            int expectedVersion = parseIfMatch(
                    exchange.getRequestHeaders().getFirst("If-Match")
            );

            store.delete(taskId, expectedVersion);

            sendJson(
                    exchange,
                    200,
                    requestId,
                    "{\"data\":{\"id\":" + quote(taskId) +
                    ",\"deleted\":true}}"
            );
            return 200;
        }

        throw new ApiException(
                405,
                "method_not_allowed",
                "Item methods are GET, PATCH and DELETE."
        );
    }

    private static Map<String, String> readJsonObject(
            HttpExchange exchange
    ) throws IOException {
        String contentType = exchange.getRequestHeaders()
                .getFirst("Content-Type");

        if (contentType == null ||
                !contentType.split(";")[0].trim()
                        .equalsIgnoreCase("application/json")) {
            throw new ApiException(
                    415,
                    "unsupported_media_type",
                    "Content-Type must be application/json."
            );
        }

        String lengthHeader = exchange.getRequestHeaders()
                .getFirst("Content-Length");

        if (lengthHeader != null) {
            try {
                if (Long.parseLong(lengthHeader) > MAX_BODY_BYTES) {
                    throw new ApiException(
                            413,
                            "payload_too_large",
                            "Request body is too large."
                    );
                }
            } catch (NumberFormatException error) {
                throw new ApiException(
                        400,
                        "invalid_content_length",
                        "Content-Length must be an integer."
                );
            }
        }

        byte[] bytes;
        try (InputStream input = exchange.getRequestBody()) {
            bytes = input.readNBytes(MAX_BODY_BYTES + 1);
        }

        if (bytes.length > MAX_BODY_BYTES) {
            throw new ApiException(
                    413,
                    "payload_too_large",
                    "Request body is too large."
            );
        }

        if (bytes.length == 0) {
            throw new ApiException(
                    400,
                    "empty_body",
                    "A JSON request body is required."
            );
        }

        String json = new String(bytes, StandardCharsets.UTF_8);
        return JsonObjectParser.parse(json);
    }

    private static Map<String, String> parseQuery(String rawQuery) {
        Map<String, String> result = new HashMap<>();
        if (rawQuery == null || rawQuery.isEmpty()) {
            return result;
        }

        for (String part : rawQuery.split("&")) {
            String[] pair = part.split("=", 2);
            String key = URLDecoder.decode(
                    pair[0],
                    StandardCharsets.UTF_8
            );
            String value = pair.length == 2
                    ? URLDecoder.decode(
                            pair[1],
                            StandardCharsets.UTF_8
                    )
                    : "";

            if (result.putIfAbsent(key, value) != null) {
                throw new ApiException(
                        400,
                        "duplicate_query_parameter",
                        "Duplicate query parameter: " + key
                );
            }
        }

        return result;
    }

    private static Integer parseInteger(
            String raw,
            int defaultValue,
            int minimum,
            int maximum,
            String field
    ) {
        if (raw == null) {
            return defaultValue;
        }

        try {
            int value = Integer.parseInt(raw);
            if (value < minimum || value > maximum) {
                throw new NumberFormatException();
            }
            return value;
        } catch (NumberFormatException error) {
            throw new ApiException(
                    400,
                    "invalid_" + field,
                    field + " must be between " + minimum +
                            " and " + maximum + "."
            );
        }
    }

    private static int parseIfMatch(String value) {
        if (value == null) {
            throw new ApiException(
                    428,
                    "precondition_required",
                    "If-Match is required for modification."
            );
        }

        Matcher matcher = VERSION_PATTERN.matcher(value.trim());
        if (!matcher.matches()) {
            throw new ApiException(
                    400,
                    "invalid_if_match",
                    "If-Match must contain a positive version number."
            );
        }

        try {
            return Integer.parseInt(matcher.group(1));
        } catch (NumberFormatException error) {
            throw new ApiException(
                    400,
                    "invalid_if_match",
                    "If-Match contains an invalid version."
            );
        }
    }

    private static String validateTitle(String value) {
        if (value == null) {
            throw new ApiException(
                    400,
                    "invalid_title",
                    "Title is required."
            );
        }

        String title = value.trim();
        if (title.isEmpty() || title.length() > MAX_TITLE_LENGTH) {
            throw new ApiException(
                    400,
                    "invalid_title",
                    "Title must contain between 1 and " +
                            MAX_TITLE_LENGTH + " characters."
            );
        }

        return title;
    }

    private static String validateDescription(String value) {
        if (value == null || value.length() > MAX_DESCRIPTION_LENGTH) {
            throw new ApiException(
                    400,
                    "invalid_description",
                    "Description must be a string of at most " +
                            MAX_DESCRIPTION_LENGTH + " characters."
            );
        }

        return value;
    }

    private static String validateStatus(String value) {
        if (value == null || !TASK_STATUSES.contains(value)) {
            throw new ApiException(
                    400,
                    "invalid_status",
                    "Unsupported task status."
            );
        }

        return value;
    }

    private static void validateIdempotencyKey(String key) {
        if (key == null ||
                !key.matches("[A-Za-z0-9._:-]{8,128}")) {
            throw new ApiException(
                    400,
                    "invalid_idempotency_key",
                    "Idempotency-Key must contain 8 to 128 permitted characters."
            );
        }
    }

    private static void rejectUnknownFields(
            Map<String, String> body,
            Set<String> allowed
    ) {
        Set<String> unknown = new HashSet<>(body.keySet());
        unknown.removeAll(allowed);

        if (!unknown.isEmpty()) {
            throw new ApiException(
                    400,
                    "unknown_fields",
                    "Unsupported fields: " + String.join(", ", unknown)
            );
        }
    }

    private static void sendJson(
            HttpExchange exchange,
            int status,
            String requestId,
            String payload
    ) {
        byte[] bytes = payload.getBytes(StandardCharsets.UTF_8);

        exchange.getResponseHeaders().set(
                "Content-Type",
                "application/json; charset=utf-8"
        );
        exchange.getResponseHeaders().set("X-Request-ID", requestId);
        exchange.getResponseHeaders().set("Cache-Control", "no-store");
        exchange.getResponseHeaders().set(
                "X-Content-Type-Options",
                "nosniff"
        );

        try {
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
        } catch (IOException error) {
            System.err.printf(
                    "response_write_failed request_id=%s%n",
                    requestId
            );
        }
    }

    private static String errorPayload(String code, String message) {
        return "{\"error\":{\"code\":" + quote(code) +
                ",\"message\":" + quote(message) + "}}";
    }

    private static String quote(String value) {
        StringBuilder output = new StringBuilder("\"");

        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);

            switch (character) {
                case '"':
                    output.append("\\\"");
                    break;
                case '\\':
                    output.append("\\\\");
                    break;
                case '\b':
                    output.append("\\b");
                    break;
                case '\f':
                    output.append("\\f");
                    break;
                case '\n':
                    output.append("\\n");
                    break;
                case '\r':
                    output.append("\\r");
                    break;
                case '\t':
                    output.append("\\t");
                    break;
                default:
                    if (character < 0x20) {
                        output.append(String.format(
                                "\\u%04x",
                                (int) character
                        ));
                    } else {
                        output.append(character);
                    }
            }
        }

        return output.append('"').toString();
    }

    private static byte[] sha256(String value) {
        return sha256(value.getBytes(StandardCharsets.UTF_8));
    }

    private static byte[] sha256(byte[] value) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(value);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException(
                    "SHA-256 is unavailable.",
                    error
            );
        }
    }

    private record Task(
            String id,
            String title,
            String description,
            String status,
            int version,
            String createdAt,
            String updatedAt
    ) {
        Task withChanges(Map<String, String> changes) {
            String nextStatus = changes.getOrDefault("status", status);

            if (!nextStatus.equals(status) &&
                    !ALLOWED_TRANSITIONS.get(status).contains(nextStatus)) {
                throw new ApiException(
                        409,
                        "invalid_state_transition",
                        "Cannot transition from " + status +
                                " to " + nextStatus + "."
                );
            }

            return new Task(
                    id,
                    changes.getOrDefault("title", title),
                    changes.getOrDefault("description", description),
                    nextStatus,
                    version + 1,
                    createdAt,
                    Instant.now().toString()
            );
        }

        String toJson() {
            return "{"
                    + "\"id\":" + quote(id) + ","
                    + "\"title\":" + quote(title) + ","
                    + "\"description\":" + quote(description) + ","
                    + "\"status\":" + quote(status) + ","
                    + "\"version\":" + version + ","
                    + "\"created_at\":" + quote(createdAt) + ","
                    + "\"updated_at\":" + quote(updatedAt)
                    + "}";
        }
    }

    private record IdempotencyEntry(
            String requestHash,
            String taskId,
            long expiresAt
    ) {}

    private record CreateResult(Task task, boolean replayed) {}

    private static final class TaskStore {
        private final Map<String, Task> tasks = new ConcurrentHashMap<>();
        private final Map<String, IdempotencyEntry> idempotency =
                new ConcurrentHashMap<>();

        synchronized CreateResult create(
                String title,
                String description,
                String key
        ) {
            long now = Instant.now().getEpochSecond();
            idempotency.entrySet().removeIf(
                    entry -> entry.getValue().expiresAt() <= now
            );

            String requestHash = hexDigest(title + "\u0000" + description);
            IdempotencyEntry previous = idempotency.get(key);

            if (previous != null) {
                if (!MessageDigest.isEqual(
                        previous.requestHash().getBytes(StandardCharsets.UTF_8),
                        requestHash.getBytes(StandardCharsets.UTF_8)
                )) {
                    throw new ApiException(
                            409,
                            "idempotency_conflict",
                            "This key was already used with a different request."
                    );
                }

                Task existing = tasks.get(previous.taskId());
                if (existing == null) {
                    throw new ApiException(
                            409,
                            "idempotency_record_unavailable",
                            "The original task is no longer available."
                    );
                }

                return new CreateResult(existing, true);
            }

            String id = UUID.randomUUID().toString();
            String nowText = Instant.now().toString();

            Task task = new Task(
                    id,
                    title,
                    description,
                    "pending",
                    1,
                    nowText,
                    nowText
            );

            tasks.put(id, task);
            idempotency.put(
                    key,
                    new IdempotencyEntry(
                            requestHash,
                            id,
                            now + IDEMPOTENCY_TTL_SECONDS
                    )
            );

            return new CreateResult(task, false);
        }

        synchronized Task get(String id) {
            Task task = tasks.get(id);
            if (task == null) {
                throw new ApiException(
                        404,
                        "task_not_found",
                        "Task does not exist."
                );
            }
            return task;
        }

        synchronized List<Task> list(
                String status,
                int limit,
                int offset
        ) {
            List<Task> filtered = tasks.values().stream()
                    .filter(task ->
                            status == null || status.equals(task.status())
                    )
                    .sorted(
                            Comparator.comparing(Task::createdAt)
                                    .reversed()
                                    .thenComparing(Task::id)
                    )
                    .collect(Collectors.toCollection(ArrayList::new));

            if (offset >= filtered.size()) {
                return List.of();
            }

            int end = Math.min(filtered.size(), offset + limit);
            return List.copyOf(filtered.subList(offset, end));
        }

        synchronized Task update(
                String id,
                int expectedVersion,
                Map<String, String> changes
        ) {
            Task current = get(id);

            if (current.version() != expectedVersion) {
                throw new ApiException(
                        412,
                        "version_conflict",
                        "The task changed. Retrieve its latest version."
                );
            }

            Task updated = current.withChanges(changes);
            tasks.put(id, updated);
            return updated;
        }

        synchronized void delete(String id, int expectedVersion) {
            Task current = get(id);

            if (current.version() != expectedVersion) {
                throw new ApiException(
                        412,
                        "version_conflict",
                        "The task changed before deletion."
                );
            }

            tasks.remove(id);
            idempotency.entrySet().removeIf(
                    entry -> entry.getValue().taskId().equals(id)
            );
        }

        private static String hexDigest(String value) {
            StringBuilder output = new StringBuilder();
            for (byte item : sha256(value)) {
                output.append(String.format("%02x", item));
            }
            return output.toString();
        }
    }

    private static final class RateLimiter {
        private final int maximum;
        private final long windowSeconds;
        private final Map<String, Bucket> buckets = new ConcurrentHashMap<>();

        private static final class Bucket {
            private long windowStart;
            private int count;

            private Bucket(long windowStart) {
                this.windowStart = windowStart;
                this.count = 0;
            }
        }

        RateLimiter(int maximum, long windowSeconds) {
            this.maximum = maximum;
            this.windowSeconds = windowSeconds;
        }

        synchronized boolean allow(String client) {
            long now = Instant.now().getEpochSecond();

            Bucket bucket = buckets.computeIfAbsent(
                    client,
                    ignored -> new Bucket(now)
            );

            if (now - bucket.windowStart >= windowSeconds) {
                bucket.windowStart = now;
                bucket.count = 0;
            }

            if (bucket.count >= maximum) {
                return false;
            }

            bucket.count++;

            if (buckets.size() > 10_000) {
                buckets.entrySet().removeIf(
                        entry -> now - entry.getValue().windowStart >
                                windowSeconds
                );
            }

            return true;
        }
    }

    private static final class ApiException extends RuntimeException {
        private final int status;
        private final String code;

        ApiException(int status, String code, String message) {
            super(message);
            this.status = status;
            this.code = code;
        }
    }

    /**
     * A deliberately bounded parser for REST request objects whose values
     * are strings. It supports JSON escapes and rejects duplicate keys,
     * nested values, malformed strings and trailing content.
     */
    private static final class JsonObjectParser {
        private final String input;
        private int position;

        private JsonObjectParser(String input) {
            this.input = input;
        }

        static Map<String, String> parse(String input) {
            JsonObjectParser parser = new JsonObjectParser(input);
            return parser.parseObject();
        }

        private Map<String, String> parseObject() {
            Map<String, String> values = new HashMap<>();

            skipWhitespace();
            expect('{');
            skipWhitespace();

            if (consume('}')) {
                finish();
                return values;
            }

            while (true) {
                skipWhitespace();
                String key = parseString();

                skipWhitespace();
                expect(':');
                skipWhitespace();

                String value = parseString();
                if (values.putIfAbsent(key, value) != null) {
                    throw invalid("Duplicate JSON object key.");
                }

                skipWhitespace();
                if (consume('}')) {
                    finish();
                    return values;
                }

                expect(',');
            }
        }

        private String parseString() {
            expect('"');
            StringBuilder result = new StringBuilder();

            while (position < input.length()) {
                char character = input.charAt(position++);

                if (character == '"') {
                    return result.toString();
                }

                if (character < 0x20) {
                    throw invalid("Control character in JSON string.");
                }

                if (character != '\\') {
                    result.append(character);
                    continue;
                }

                if (position >= input.length()) {
                    throw invalid("Incomplete JSON escape.");
                }

                char escaped = input.charAt(position++);
                switch (escaped) {
                    case '"':
                    case '\\':
                    case '/':
                        result.append(escaped);
                        break;
                    case 'b':
                        result.append('\b');
                        break;
                    case 'f':
                        result.append('\f');
                        break;
                    case 'n':
                        result.append('\n');
                        break;
                    case 'r':
                        result.append('\r');
                        break;
                    case 't':
                        result.append('\t');
                        break;
                    case 'u':
                        result.append(parseUnicodeEscape());
                        break;
                    default:
                        throw invalid("Invalid JSON escape.");
                }
            }

            throw invalid("Unterminated JSON string.");
        }

        private char parseUnicodeEscape() {
            if (position + 4 > input.length()) {
                throw invalid("Incomplete Unicode escape.");
            }

            String hex = input.substring(position, position + 4);
            position += 4;

            try {
                return (char) Integer.parseInt(hex, 16);
            } catch (NumberFormatException error) {
                throw invalid("Invalid Unicode escape.");
            }
        }

        private void skipWhitespace() {
            while (position < input.length() &&
                    Character.isWhitespace(input.charAt(position))) {
                position++;
            }
        }

        private void expect(char expected) {
            if (!consume(expected)) {
                throw invalid("Expected '" + expected + "'.");
            }
        }

        private boolean consume(char expected) {
            if (position < input.length() &&
                    input.charAt(position) == expected) {
                position++;
                return true;
            }
            return false;
        }

        private void finish() {
            skipWhitespace();
            if (position != input.length()) {
                throw invalid("Unexpected content after JSON object.");
            }
        }

        private ApiException invalid(String message) {
            return new ApiException(400, "invalid_json", message);
        }
    }
}
