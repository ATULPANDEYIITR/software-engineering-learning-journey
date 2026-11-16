import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.LongAdder;
import java.util.regex.Pattern;

/**
 * Structured Logging and Enterprise Observability
 *
 * Java 17 implementation.
 *
 * Features:
 * - Immutable structured log events
 * - Severity classification
 * - Correlation and request identifiers
 * - Explicit execution-context propagation
 * - Policy-based logging
 * - Sensitive-data redaction
 * - Exception serialization
 * - Concurrent metrics
 * - Multiple output destinations
 * - Enterprise application workflow
 */

public class StructuredLoggingEnterprise {

    // ---------------------------------------------------
    // 1. Severity model
    // ---------------------------------------------------

    enum LogLevel {
        DEBUG(10),
        INFO(20),
        WARNING(30),
        ERROR(40),
        CRITICAL(50);

        private final int severity;

        LogLevel(int severity) {
            this.severity = severity;
        }

        public int severity() {
            return severity;
        }
    }

    // ---------------------------------------------------
    // 2. Immutable execution context
    // ---------------------------------------------------

    record LogContext(
        String correlationId,
        String requestId,
        String userId,
        String environment
    ) {

        LogContext {
            requireText(correlationId, "correlationId");
            requireText(requestId, "requestId");
            requireText(userId, "userId");
            requireText(environment, "environment");
        }

        static LogContext create(String userId) {
            return new LogContext(
                UUID.randomUUID().toString(),
                UUID.randomUUID().toString(),
                userId,
                "production"
            );
        }
    }

    // ---------------------------------------------------
    // 3. Structured log event
    // ---------------------------------------------------

    record LogEvent(
        Instant timestamp,
        LogLevel level,
        String service,
        String message,
        LogContext context,
        Map<String, Object> attributes,
        String exception
    ) {

        LogEvent {
            Objects.requireNonNull(timestamp);
            Objects.requireNonNull(level);
            Objects.requireNonNull(context);

            requireText(service, "service");
            requireText(message, "message");

            attributes = Collections.unmodifiableMap(
                new HashMap<>(attributes)
            );
        }
    }

    // ---------------------------------------------------
    // 4. Validation
    // ---------------------------------------------------

    static void requireText(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(
                field + " cannot be empty."
            );
        }
    }

    // ---------------------------------------------------
    // 5. Sensitive information handling
    // ---------------------------------------------------

    static final Set<String> SENSITIVE_FIELDS = Set.of(
        "password",
        "token",
        "access_token",
        "authorization",
        "secret",
        "api_key",
        "credit_card"
    );

    static Map<String, Object> sanitize(
        Map<String, Object> input
    ) {

        Map<String, Object> output = new HashMap<>();

        input.forEach((key, value) -> {
            requireText(key, "attribute key");

            output.put(
                key,
                SENSITIVE_FIELDS.contains(
                    key.toLowerCase()
                )
                    ? "[REDACTED]"
                    : sanitizeValue(value)
            );
        });

        return output;
    }

    static Object sanitizeValue(Object value) {

        if (value == null) {
            return null;
        }

        if (value instanceof Map<?, ?> map) {
            Map<String, Object> nested = new HashMap<>();

            map.forEach((key, nestedValue) -> {
                String name = String.valueOf(key);

                nested.put(
                    name,
                    SENSITIVE_FIELDS.contains(name.toLowerCase())
                        ? "[REDACTED]"
                        : sanitizeValue(nestedValue)
                );
            });

            return nested;
        }

        if (value instanceof List<?> list) {
            return list.stream()
                .map(StructuredLoggingEnterprise::sanitizeValue)
                .toList();
        }

        if (value instanceof Throwable throwable) {
            return throwable.getClass().getSimpleName()
                + ": " + throwable.getMessage();
        }

        if (
            value instanceof String ||
            value instanceof Number ||
            value instanceof Boolean
        ) {
            return value;
        }

        return String.valueOf(value);
    }

    // ---------------------------------------------------
    // 6. JSON serialization
    // ---------------------------------------------------

    static String jsonString(String value) {

        StringBuilder output = new StringBuilder("\"");

        for (char ch : value.toCharArray()) {
            switch (ch) {
                case '"' -> output.append("\\\"");
                case '\\' -> output.append("\\\\");
                case '\n' -> output.append("\\n");
                case '\r' -> output.append("\\r");
                case '\t' -> output.append("\\t");
                default -> {
                    if (ch < 0x20) {
                        output.append(String.format(
                            "\\u%04x",
                            (int) ch
                        ));
                    } else {
                        output.append(ch);
                    }
                }
            }
        }

        return output.append('"').toString();
    }

    static String jsonValue(Object value) {

        if (value == null) {
            return "null";
        }

        if (value instanceof String string) {
            return jsonString(string);
        }

        if (value instanceof Number || value instanceof Boolean) {
            return value.toString();
        }

        if (value instanceof Map<?, ?> map) {
            StringBuilder result = new StringBuilder("{");

            boolean first = true;

            for (Map.Entry<?, ?> entry : map.entrySet()) {
                if (!first) {
                    result.append(",");
                }

                first = false;

                result.append(
                    jsonString(String.valueOf(entry.getKey()))
                );

                result.append(":");
                result.append(jsonValue(entry.getValue()));
            }

            return result.append("}").toString();
        }

        if (value instanceof Iterable<?> iterable) {
            StringBuilder result = new StringBuilder("[");
            boolean first = true;

            for (Object item : iterable) {
                if (!first) {
                    result.append(",");
                }

                first = false;
                result.append(jsonValue(item));
            }

            return result.append("]").toString();
        }

        return jsonString(value.toString());
    }

    static String serialize(LogEvent event) {

        Map<String, Object> json = new java.util.LinkedHashMap<>();

        json.put("timestamp", event.timestamp().toString());
        json.put("level", event.level().name());
        json.put("severity", event.level().severity());
        json.put("service", event.service());
        json.put("message", event.message());

        json.put(
            "correlation_id",
            event.context().correlationId()
        );

        json.put(
            "request_id",
            event.context().requestId()
        );

        json.put(
            "user_id",
            event.context().userId()
        );

        json.put(
            "environment",
            event.context().environment()
        );

        json.put("attributes", event.attributes());

        if (event.exception() != null) {
            json.put("exception", event.exception());
        }

        return jsonValue(json);
    }

    // ---------------------------------------------------
    // 7. Output interface
    // ---------------------------------------------------

    interface LogSink {
        void write(LogEvent event);
    }

    static class ConsoleSink implements LogSink {

        @Override
        public synchronized void write(LogEvent event) {

            String output = serialize(event);

            if (event.level().severity() >= LogLevel.ERROR.severity()) {
                System.err.println(output);
            } else {
                System.out.println(output);
            }
        }
    }

    // ---------------------------------------------------
    // 8. Logging policy
    // ---------------------------------------------------

    record LoggingPolicy(
        LogLevel minimumLevel,
        Set<String> excludedServices,
        boolean includeDebug
    ) {

        LoggingPolicy {
            Objects.requireNonNull(minimumLevel);

            excludedServices = Set.copyOf(
                excludedServices
            );
        }

        boolean permits(String service, LogLevel level) {

            if (excludedServices.contains(service)) {
                return false;
            }

            if (
                level == LogLevel.DEBUG &&
                !includeDebug
            ) {
                return false;
            }

            return level.severity() >= minimumLevel.severity();
        }
    }

    // ---------------------------------------------------
    // 9. Concurrent metrics
    // ---------------------------------------------------

    static class LoggingMetrics {

        private final Map<LogLevel, LongAdder> counters =
            new ConcurrentHashMap<>();

        void increment(LogLevel level) {
            counters.computeIfAbsent(
                level,
                key -> new LongAdder()
            ).increment();
        }

        Map<String, Long> snapshot() {

            Map<String, Long> result = new HashMap<>();

            counters.forEach((level, count) ->
                result.put(level.name(), count.sum())
            );

            return Collections.unmodifiableMap(result);
        }
    }

    // ---------------------------------------------------
    // 10. Logging service
    // ---------------------------------------------------

    static class StructuredLogger {

        private final String service;
        private final LoggingPolicy policy;
        private final LogSink sink;
        private final LoggingMetrics metrics;

        StructuredLogger(
            String service,
            LoggingPolicy policy,
            LogSink sink,
            LoggingMetrics metrics
        ) {
            requireText(service, "service");

            this.service = service;
            this.policy = Objects.requireNonNull(policy);
            this.sink = Objects.requireNonNull(sink);
            this.metrics = Objects.requireNonNull(metrics);
        }

        void log(
            LogLevel level,
            String message,
            LogContext context,
            Map<String, Object> attributes
        ) {

            Objects.requireNonNull(level);
            Objects.requireNonNull(context);

            requireText(message, "message");

            if (!policy.permits(service, level)) {
                return;
            }

            LogEvent event = new LogEvent(
                Instant.now(),
                level,
                service,
                message,
                context,
                sanitize(attributes),
                null
            );

            sink.write(event);
            metrics.increment(level);
        }

        void logException(
            String message,
            Exception exception,
            LogContext context
        ) {

            Objects.requireNonNull(exception);

            if (!policy.permits(service, LogLevel.ERROR)) {
                return;
            }

            String details =
                exception.getClass().getName()
                + ": " + exception.getMessage();

            LogEvent event = new LogEvent(
                Instant.now(),
                LogLevel.ERROR,
                service,
                message,
                context,
                Map.of(),
                details
            );

            sink.write(event);
            metrics.increment(LogLevel.ERROR);
        }

        void info(
            String message,
            LogContext context,
            Map<String, Object> attributes
        ) {
            log(LogLevel.INFO, message, context, attributes);
        }

        void debug(
            String message,
            LogContext context,
            Map<String, Object> attributes
        ) {
            log(LogLevel.DEBUG, message, context, attributes);
        }

        void warning(
            String message,
            LogContext context,
            Map<String, Object> attributes
        ) {
            log(LogLevel.WARNING, message, context, attributes);
        }

        void error(
            String message,
            LogContext context,
            Map<String, Object> attributes
        ) {
            log(LogLevel.ERROR, message, context, attributes);
        }
    }

    // ---------------------------------------------------
    // 11. Enterprise order service
    // ---------------------------------------------------

    static class OrderService {

        private final StructuredLogger logger;
        private final Map<String, Map<String, Object>> orders =
            new ConcurrentHashMap<>();

        OrderService(StructuredLogger logger) {
            this.logger = logger;
        }

        Map<String, Object> createOrder(
            String customerId,
            double amount,
            LogContext context
        ) {

            requireText(customerId, "customerId");

            if (!Double.isFinite(amount) || amount <= 0) {
                throw new IllegalArgumentException(
                    "Order amount must be positive and finite."
                );
            }

            logger.info(
                "Order processing started",
                context,
                Map.of(
                    "customer_id", customerId,
                    "amount", amount
                )
            );

            String orderId = UUID.randomUUID().toString();

            Map<String, Object> order = Map.of(
                "order_id", orderId,
                "customer_id", customerId,
                "amount", amount,
                "status", "CREATED"
            );

            orders.put(orderId, order);

            logger.info(
                "Order successfully created",
                context,
                order
            );

            return order;
        }
    }

    // ---------------------------------------------------
    // 12. Automated tests
    // ---------------------------------------------------

    static void runTests() {

        Map<String, Object> sanitized = sanitize(
            Map.of(
                "password", "private",
                "customer_id", "C-100"
            )
        );

        if (!"[REDACTED]".equals(sanitized.get("password"))) {
            throw new AssertionError("Redaction failed.");
        }

        if (!"C-100".equals(sanitized.get("customer_id"))) {
            throw new AssertionError("Safe data was modified.");
        }

        String escaped = jsonString("line\nbreak");

        if (!escaped.equals("\"line\\nbreak\"")) {
            throw new AssertionError("JSON escaping failed.");
        }

        LoggingPolicy policy = new LoggingPolicy(
            LogLevel.INFO,
            Set.of("disabled-service"),
            false
        );

        if (policy.permits("disabled-service", LogLevel.ERROR)) {
            throw new AssertionError("Service exclusion failed.");
        }

        if (policy.permits("orders", LogLevel.DEBUG)) {
            throw new AssertionError("Debug filtering failed.");
        }

        try {
            requireText("", "test");
            throw new AssertionError("Empty value accepted.");
        } catch (IllegalArgumentException expected) {
            // Expected validation result.
        }

        System.out.println("All Java 17 tests passed.");
    }

    // ---------------------------------------------------
    // 13. Main enterprise workflow
    // ---------------------------------------------------

    public static void main(String[] args) {

        LoggingMetrics metrics = new LoggingMetrics();

        LoggingPolicy policy = new LoggingPolicy(
            LogLevel.DEBUG,
            Set.of(),
            true
        );

        StructuredLogger logger = new StructuredLogger(
            "enterprise-order-service",
            policy,
            new ConsoleSink(),
            metrics
        );

        OrderService orderService = new OrderService(logger);

        LogContext context = LogContext.create("USER-101");

        ExecutorService executor =
            Executors.newFixedThreadPool(2);

        try {

            logger.info(
                "Enterprise application started",
                context,
                Map.of(
                    "version", "1.0.0",
                    "region", "ap-south-1"
                )
            );

            orderService.createOrder(
                "CUSTOMER-101",
                5000.75,
                context
            );

            try {
                orderService.createOrder(
                    "CUSTOMER-102",
                    -100,
                    context
                );
            } catch (IllegalArgumentException exception) {
                logger.logException(
                    "Order validation failed",
                    exception,
                    context
                );
            }

            List<Future<?>> tasks = new ArrayList<>();

            for (int i = 0; i < 2; i++) {

                final int taskNumber = i + 1;

                tasks.add(executor.submit(() -> {

                    LogContext childContext = new LogContext(
                        context.correlationId(),
                        UUID.randomUUID().toString(),
                        context.userId(),
                        context.environment()
                    );

                    logger.info(
                        "Asynchronous operation completed",
                        childContext,
                        Map.of("task_number", taskNumber)
                    );
                }));
            }

            for (Future<?> task : tasks) {
                task.get();
            }

            logger.info(
                "Enterprise application completed",
                context,
                Map.of(
                    "metrics", metrics.snapshot()
                )
            );

            runTests();

        } catch (Exception exception) {

            logger.logException(
                "Enterprise application failure",
                exception,
                context
            );

            throw new RuntimeException(
                "Application execution failed.",
                exception
            );

        } finally {
            executor.shutdown();
        }

        System.out.println("\nLogging metrics:");

        metrics.snapshot().forEach(
            (level, count) ->
                System.out.println(level + ": " + count)
        );
    }
}
