import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.Deque;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.TreeMap;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.LongAdder;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Observability Engineering
 *
 * Enterprise-oriented observability platform.
 *
 * Java 17 features:
 * - Records and immutable domain objects
 * - Sealed-style domain separation through enums and interfaces
 * - Concurrent metric storage
 * - Structured logging
 * - Distributed trace relationships
 * - Explicit service and policy classes
 * - Alert state transitions
 * - Telemetry validation and reporting
 *
 * Compile:
 * javac ObservabilityEnterprise.java
 *
 * Run:
 * java ObservabilityEnterprise
 */
public class ObservabilityEnterprise {

    // ========================================================
    // 1. ENUMERATIONS
    // ========================================================

    enum Severity {
        DEBUG,
        INFO,
        WARNING,
        ERROR,
        CRITICAL
    }

    enum MetricType {
        COUNTER,
        GAUGE,
        HISTOGRAM
    }

    enum SpanStatus {
        UNSET,
        OK,
        ERROR
    }

    enum AlertState {
        NORMAL,
        FIRING,
        RESOLVED
    }

    // ========================================================
    // 2. EXCEPTIONS
    // ========================================================

    static class ObservabilityException extends RuntimeException {
        ObservabilityException(String message) {
            super(message);
        }
    }

    static class ValidationException extends ObservabilityException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class PolicyException extends ObservabilityException {
        PolicyException(String message) {
            super(message);
        }
    }

    // ========================================================
    // 3. VALIDATION
    // ========================================================

    static final class Validation {

        private Validation() {}

        static String name(String value, String field) {
            if (
                value == null ||
                value.isBlank() ||
                value.length() > 128 ||
                !value.matches("[A-Za-z0-9_.:/-]+")
            ) {
                throw new ValidationException(
                    "Invalid " + field
                );
            }

            return value;
        }

        static double finite(double value, String field) {
            if (!Double.isFinite(value)) {
                throw new ValidationException(
                    field + " must be finite"
                );
            }

            return value;
        }

        static Map<String, String> labels(
            Map<String, String> labels
        ) {
            Objects.requireNonNull(labels, "Labels cannot be null");

            if (labels.size() > 20) {
                throw new ValidationException("Label limit exceeded");
            }

            Map<String, String> result = new TreeMap<>();

            labels.forEach((key, value) -> {
                name(key, "label key");

                if (value == null || value.length() > 128) {
                    throw new ValidationException("Invalid label value");
                }

                result.put(key, value);
            });

            return Collections.unmodifiableMap(result);
        }
    }

    // ========================================================
    // 4. SECURITY AND REDACTION
    // ========================================================

    static final class Redactor {

        private static final Set<String> SENSITIVE = Set.of(
            "password",
            "token",
            "access_token",
            "refresh_token",
            "authorization",
            "api_key",
            "secret",
            "credit_card",
            "ssn"
        );

        private Redactor() {}

        static Map<String, String> sanitize(
            Map<String, String> attributes
        ) {
            Map<String, String> result = new TreeMap<>();

            attributes.forEach((key, value) -> {
                String safeValue = SENSITIVE.contains(
                    key.toLowerCase()
                )
                    ? "[REDACTED]"
                    : value;

                result.put(key, safeValue);
            });

            return Collections.unmodifiableMap(result);
        }
    }

    // ========================================================
    // 5. STRUCTURED LOGGING
    // ========================================================

    record LogRecord(
        Instant timestamp,
        Severity severity,
        String service,
        String message,
        String traceId,
        String spanId,
        Map<String, String> attributes
    ) {
        LogRecord {
            Objects.requireNonNull(timestamp);
            Objects.requireNonNull(severity);

            Validation.name(service, "service");

            if (
                message == null ||
                message.isBlank() ||
                message.length() > 4096
            ) {
                throw new ValidationException("Invalid log message");
            }

            attributes = Redactor.sanitize(attributes);

            traceId = traceId == null ? "" : traceId;
            spanId = spanId == null ? "" : spanId;
        }
    }

    static final class StructuredLogger {

        private final String service;
        private final List<LogRecord> records =
            Collections.synchronizedList(new ArrayList<>());

        StructuredLogger(String service) {
            this.service = Validation.name(service, "service");
        }

        LogRecord write(
            Severity severity,
            String message,
            String traceId,
            String spanId,
            Map<String, String> attributes
        ) {
            LogRecord record = new LogRecord(
                Instant.now(),
                severity,
                service,
                message,
                traceId,
                spanId,
                attributes
            );

            records.add(record);
            return record;
        }

        List<LogRecord> find(Predicate<LogRecord> condition) {
            synchronized (records) {
                return records.stream()
                    .filter(condition)
                    .toList();
            }
        }

        List<LogRecord> findByTrace(String traceId) {
            return find(record -> record.traceId().equals(traceId));
        }

        List<LogRecord> snapshot() {
            synchronized (records) {
                return List.copyOf(records);
            }
        }
    }

    // ========================================================
    // 6. METRIC DOMAIN MODEL
    // ========================================================

    record MetricKey(
        String name,
        String service,
        Map<String, String> labels
    ) {
        MetricKey {
            Validation.name(name, "metric name");
            Validation.name(service, "service");
            labels = Validation.labels(labels);
        }
    }

    record HistogramSummary(
        long count,
        double sum,
        double average,
        double minimum,
        double maximum,
        double p50,
        double p95,
        double p99
    ) {}

    interface Metric {
        MetricType type();

        MetricKey key();
    }

    static final class CounterMetric implements Metric {

        private final MetricKey key;
        private final LongAdder count = new LongAdder();

        CounterMetric(MetricKey key) {
            this.key = key;
        }

        void increment(double amount) {
            Validation.finite(amount, "counter increment");

            if (amount < 0 || amount != Math.floor(amount)) {
                throw new ValidationException(
                    "Counter increment must be a non-negative integer"
                );
            }

            count.add((long) amount);
        }

        long value() {
            return count.sum();
        }

        @Override
        public MetricType type() {
            return MetricType.COUNTER;
        }

        @Override
        public MetricKey key() {
            return key;
        }
    }

    static final class GaugeMetric implements Metric {

        private final MetricKey key;
        private volatile double value;

        GaugeMetric(MetricKey key) {
            this.key = key;
        }

        void set(double value) {
            this.value = Validation.finite(value, "gauge");
        }

        double value() {
            return value;
        }

        @Override
        public MetricType type() {
            return MetricType.GAUGE;
        }

        @Override
        public MetricKey key() {
            return key;
        }
    }

    static final class HistogramMetric implements Metric {

        private final MetricKey key;
        private final List<Double> observations =
            Collections.synchronizedList(new ArrayList<>());

        HistogramMetric(MetricKey key) {
            this.key = key;
        }

        void observe(double value) {
            value = Validation.finite(value, "observation");

            if (value < 0) {
                throw new ValidationException(
                    "Negative histogram observation"
                );
            }

            observations.add(value);
        }

        private static double percentile(
            List<Double> sorted,
            double percentile
        ) {
            if (sorted.isEmpty()) {
                throw new ValidationException("Empty histogram");
            }

            double position =
                (sorted.size() - 1) * percentile / 100.0;

            int lower = (int) Math.floor(position);
            int upper = (int) Math.ceil(position);

            return sorted.get(lower) +
                (sorted.get(upper) - sorted.get(lower)) *
                (position - lower);
        }

        HistogramSummary summary() {
            List<Double> values;

            synchronized (observations) {
                values = new ArrayList<>(observations);
            }

            if (values.isEmpty()) {
                throw new ValidationException("Empty histogram");
            }

            values.sort(Comparator.naturalOrder());

            double sum = values.stream()
                .mapToDouble(Double::doubleValue)
                .sum();

            return new HistogramSummary(
                values.size(),
                sum,
                sum / values.size(),
                values.get(0),
                values.get(values.size() - 1),
                percentile(values, 50),
                percentile(values, 95),
                percentile(values, 99)
            );
        }

        @Override
        public MetricType type() {
            return MetricType.HISTOGRAM;
        }

        @Override
        public MetricKey key() {
            return key;
        }
    }

    // ========================================================
    // 7. METRIC REGISTRY
    // ========================================================

    static final class MetricRegistry {

        private final ConcurrentHashMap<MetricKey, Metric> metrics =
            new ConcurrentHashMap<>();

        private <T extends Metric> T register(
            MetricKey key,
            MetricType expected,
            java.util.function.Supplier<T> factory
        ) {
            Metric metric = metrics.computeIfAbsent(
                key,
                ignored -> factory.get()
            );

            if (metric.type() != expected) {
                throw new ValidationException(
                    "Metric type conflict: " + key.name()
                );
            }

            @SuppressWarnings("unchecked")
            T result = (T) metric;

            return result;
        }

        void increment(
            String name,
            String service,
            long amount,
            Map<String, String> labels
        ) {
            MetricKey key = new MetricKey(name, service, labels);

            register(
                key,
                MetricType.COUNTER,
                () -> new CounterMetric(key)
            ).increment(amount);
        }

        void setGauge(
            String name,
            String service,
            double value,
            Map<String, String> labels
        ) {
            MetricKey key = new MetricKey(name, service, labels);

            register(
                key,
                MetricType.GAUGE,
                () -> new GaugeMetric(key)
            ).set(value);
        }

        void observe(
            String name,
            String service,
            double value,
            Map<String, String> labels
        ) {
            MetricKey key = new MetricKey(name, service, labels);

            register(
                key,
                MetricType.HISTOGRAM,
                () -> new HistogramMetric(key)
            ).observe(value);
        }

        HistogramSummary histogram(
            String name,
            String service,
            Map<String, String> labels
        ) {
            Metric metric = metrics.get(
                new MetricKey(name, service, labels)
            );

            if (!(metric instanceof HistogramMetric histogram)) {
                throw new ValidationException(
                    "Histogram not found"
                );
            }

            return histogram.summary();
        }

        List<Metric> snapshot() {
            return List.copyOf(metrics.values());
        }
    }

    // ========================================================
    // 8. DISTRIBUTED TRACING
    // ========================================================

    static final class Span {

        private final String traceId;
        private final String spanId;
        private final String parentSpanId;
        private final String service;
        private final String operation;
        private final long startNanos;

        private long endNanos;
        private SpanStatus status = SpanStatus.UNSET;

        private final Map<String, String> attributes;

        Span(
            String traceId,
            String spanId,
            String parentSpanId,
            String service,
            String operation,
            Map<String, String> attributes
        ) {
            this.traceId = traceId;
            this.spanId = spanId;
            this.parentSpanId = parentSpanId;
            this.service = Validation.name(service, "service");
            this.operation = Validation.name(operation, "operation");
            this.startNanos = System.nanoTime();
            this.attributes = Redactor.sanitize(attributes);
        }

        void finish(SpanStatus status) {
            if (endNanos != 0) {
                throw new ValidationException("Span already completed");
            }

            this.status = Objects.requireNonNull(status);
            this.endNanos = System.nanoTime();
        }

        double durationMs() {
            if (endNanos == 0) {
                throw new ValidationException("Span is active");
            }

            return (endNanos - startNanos) / 1_000_000.0;
        }

        String traceId() {
            return traceId;
        }

        String spanId() {
            return spanId;
        }

        String parentSpanId() {
            return parentSpanId;
        }

        String service() {
            return service;
        }

        String operation() {
            return operation;
        }

        SpanStatus status() {
            return status;
        }

        Map<String, String> attributes() {
            return attributes;
        }
    }

    static final class Trace {

        private final String traceId = UUID.randomUUID().toString();

        private final Map<String, Span> spans = new HashMap<>();

        Span startSpan(
            String service,
            String operation,
            String parentSpanId,
            Map<String, String> attributes
        ) {
            if (parentSpanId != null) {
                Span parent = spans.get(parentSpanId);

                if (parent == null) {
                    throw new ValidationException(
                        "Parent span not found"
                    );
                }

                if (parent.endNanos != 0) {
                    throw new ValidationException(
                        "Parent span completed"
                    );
                }
            }

            String spanId = UUID.randomUUID()
                .toString()
                .replace("-", "")
                .substring(0, 16);

            Span span = new Span(
                traceId,
                spanId,
                parentSpanId,
                service,
                operation,
                attributes
            );

            spans.put(spanId, span);
            return span;
        }

        void validate() {
            for (Span span : spans.values()) {
                if (span.endNanos == 0) {
                    throw new ValidationException(
                        "Trace contains active spans"
                    );
                }

                Set<String> visited = new HashSet<>();
                Span current = span;

                while (current.parentSpanId() != null) {
                    if (!visited.add(current.spanId())) {
                        throw new ValidationException(
                            "Circular span relationship"
                        );
                    }

                    current = spans.get(current.parentSpanId());

                    if (current == null) {
                        throw new ValidationException(
                            "Broken parent relationship"
                        );
                    }
                }
            }
        }

        String traceId() {
            return traceId;
        }

        List<Span> spans() {
            return List.copyOf(spans.values());
        }
    }

    // ========================================================
    // 9. ALERT POLICY AND EVALUATION
    // ========================================================

    interface ComparisonPolicy {
        boolean evaluate(double value, double threshold);
    }

    static final class GreaterThanPolicy
        implements ComparisonPolicy {

        @Override
        public boolean evaluate(double value, double threshold) {
            return value > threshold;
        }
    }

    static final class GreaterThanOrEqualPolicy
        implements ComparisonPolicy {

        @Override
        public boolean evaluate(double value, double threshold) {
            return value >= threshold;
        }
    }

    record AlertRule(
        String name,
        String metric,
        double threshold,
        int windowSize,
        ComparisonPolicy comparison
    ) {
        AlertRule {
            Validation.name(name, "alert name");
            Validation.name(metric, "metric");
            Validation.finite(threshold, "threshold");

            if (windowSize < 1) {
                throw new ValidationException(
                    "Invalid evaluation window"
                );
            }

            Objects.requireNonNull(comparison);
        }
    }

    record AlertTransition(
        String rule,
        AlertState previous,
        AlertState current,
        double observed,
        Instant timestamp
    ) {}

    static final class AlertService {

        private final Map<String, AlertRule> rules = new HashMap<>();
        private final Map<String, Deque<Double>> history =
            new HashMap<>();
        private final Map<String, AlertState> states =
            new HashMap<>();
        private final List<AlertTransition> events =
            new ArrayList<>();

        void register(AlertRule rule) {
            if (rules.putIfAbsent(rule.name(), rule) != null) {
                throw new PolicyException("Duplicate alert rule");
            }

            history.put(rule.name(), new ArrayDeque<>());
            states.put(rule.name(), AlertState.NORMAL);
        }

        AlertState evaluate(String name, double value) {
            value = Validation.finite(value, "alert value");

            AlertRule rule = rules.get(name);

            if (rule == null) {
                throw new PolicyException("Alert rule not found");
            }

            Deque<Double> samples = history.get(name);

            samples.addLast(value);

            while (samples.size() > rule.windowSize()) {
                samples.removeFirst();
            }

            if (samples.size() < rule.windowSize()) {
                return states.get(name);
            }

            double average = samples.stream()
                .mapToDouble(Double::doubleValue)
                .average()
                .orElseThrow();

            AlertState next = rule.comparison().evaluate(
                average,
                rule.threshold()
            ) ? AlertState.FIRING : AlertState.NORMAL;

            AlertState previous = states.get(name);

            if (next != previous) {
                states.put(name, next);

                events.add(new AlertTransition(
                    name,
                    previous,
                    next,
                    average,
                    Instant.now()
                ));
            }

            return next;
        }

        List<AlertTransition> events() {
            return List.copyOf(events);
        }
    }

    // ========================================================
    // 10. ENTERPRISE OBSERVABILITY SERVICE
    // ========================================================

    static final class ObservabilityService {

        private final ConcurrentHashMap<String, StructuredLogger> loggers =
            new ConcurrentHashMap<>();

        private final MetricRegistry metrics = new MetricRegistry();

        private final ConcurrentHashMap<String, Trace> traces =
            new ConcurrentHashMap<>();

        private final AlertService alerts = new AlertService();

        StructuredLogger logger(String service) {
            return loggers.computeIfAbsent(
                service,
                StructuredLogger::new
            );
        }

        Trace createTrace() {
            Trace trace = new Trace();

            if (traces.putIfAbsent(trace.traceId(), trace) != null) {
                throw new ObservabilityException(
                    "Duplicate trace identifier"
                );
            }

            return trace;
        }

        List<LogRecord> correlate(String traceId) {
            return loggers.values().stream()
                .flatMap(logger -> logger.findByTrace(traceId).stream())
                .collect(Collectors.toList());
        }

        MetricRegistry metrics() {
            return metrics;
        }

        AlertService alerts() {
            return alerts;
        }

        List<Trace> traces() {
            return List.copyOf(traces.values());
        }

        List<StructuredLogger> loggers() {
            return List.copyOf(loggers.values());
        }
    }

    // ========================================================
    // 11. PAYMENT WORKFLOW
    // ========================================================

    static String executePayment(
        ObservabilityService service,
        double amount,
        boolean shouldFail
    ) {
        amount = Validation.finite(amount, "payment amount");

        if (amount <= 0 || amount > 1_000_000) {
            throw new ValidationException(
                "Payment amount outside permitted limits"
            );
        }

        Trace trace = service.createTrace();

        StructuredLogger logger = service.logger("payment-api");

        Span root = trace.startSpan(
            "payment-api",
            "POST /payments",
            null,
            Map.of("amount", Double.toString(amount))
        );

        logger.write(
            Severity.INFO,
            "Payment request received",
            trace.traceId(),
            root.spanId(),
            Map.of()
        );

        service.metrics().increment(
            "payment_requests_total",
            "payment-api",
            1,
            Map.of("environment", "production")
        );

        Span database = trace.startSpan(
            "payment-database",
            "INSERT payment",
            root.spanId(),
            Map.of()
        );

        database.finish(SpanStatus.OK);

        Span processor = trace.startSpan(
            "payment-processor",
            "authorize transaction",
            root.spanId(),
            Map.of()
        );

        if (shouldFail) {
            processor.finish(SpanStatus.ERROR);
            root.finish(SpanStatus.ERROR);

            logger.write(
                Severity.ERROR,
                "Payment authorization failed",
                trace.traceId(),
                processor.spanId(),
                Map.of("error_code", "PAYMENT_DECLINED")
            );

            service.metrics().increment(
                "payment_failures_total",
                "payment-api",
                1,
                Map.of()
            );
        } else {
            processor.finish(SpanStatus.OK);
            root.finish(SpanStatus.OK);

            logger.write(
                Severity.INFO,
                "Payment completed",
                trace.traceId(),
                root.spanId(),
                Map.of()
            );

            service.metrics().increment(
                "payment_success_total",
                "payment-api",
                1,
                Map.of()
            );
        }

        service.metrics().observe(
            "payment_latency_ms",
            "payment-api",
            shouldFail ? 250 : 125,
            Map.of()
        );

        trace.validate();

        return trace.traceId();
    }

    // ========================================================
    // 12. REPORTING
    // ========================================================

    static void printReport(ObservabilityService service) {
        System.out.println("\nENTERPRISE OBSERVABILITY REPORT");
        System.out.println("================================");

        System.out.println("\nLOGS");

        for (StructuredLogger logger : service.loggers()) {
            for (LogRecord record : logger.snapshot()) {
                System.out.printf(
                    "%s %-8s %-18s %s%n",
                    record.timestamp(),
                    record.severity(),
                    record.service(),
                    record.message()
                );
            }
        }

        System.out.println("\nMETRIC TYPES");

        for (Metric metric : service.metrics().snapshot()) {
            System.out.println(
                metric.key() + " " + metric.type()
            );

            if (metric instanceof CounterMetric counter) {
                System.out.println("Value: " + counter.value());
            } else if (metric instanceof GaugeMetric gauge) {
                System.out.println("Value: " + gauge.value());
            } else if (metric instanceof HistogramMetric histogram) {
                System.out.println(histogram.summary());
            }
        }

        System.out.println("\nDISTRIBUTED TRACES");

        for (Trace trace : service.traces()) {
            System.out.println("\nTrace: " + trace.traceId());

            for (Span span : trace.spans()) {
                System.out.printf(
                    "%-20s %-28s %-8s %.3f ms%n",
                    span.service(),
                    span.operation(),
                    span.status(),
                    span.durationMs()
                );
            }
        }

        System.out.println("\nALERT TRANSITIONS");

        service.alerts().events().forEach(System.out::println);
    }

    // ========================================================
    // 13. AUTOMATED VALIDATION
    // ========================================================

    static void runTests() {
        ObservabilityService service = new ObservabilityService();

        String successTrace = executePayment(
            service,
            1500,
            false
        );

        String failureTrace = executePayment(
            service,
            2500,
            true
        );

        if (service.correlate(successTrace).size() != 2) {
            throw new AssertionError("Successful trace correlation failed");
        }

        if (service.correlate(failureTrace).size() != 2) {
            throw new AssertionError("Failed trace correlation failed");
        }

        StructuredLogger security = service.logger("security-service");

        LogRecord protectedRecord = security.write(
            Severity.WARNING,
            "Authentication event",
            "",
            "",
            Map.of(
                "username", "operator",
                "password", "confidential"
            )
        );

        if (!protectedRecord.attributes().get("password")
            .equals("[REDACTED]")) {
            throw new AssertionError("Redaction failed");
        }

        service.metrics().observe(
            "test_latency",
            "test",
            10,
            Map.of()
        );

        service.metrics().observe(
            "test_latency",
            "test",
            20,
            Map.of()
        );

        service.metrics().observe(
            "test_latency",
            "test",
            30,
            Map.of()
        );

        HistogramSummary summary = service.metrics().histogram(
            "test_latency",
            "test",
            Map.of()
        );

        if (summary.count() != 3 || summary.p50() != 20) {
            throw new AssertionError("Histogram validation failed");
        }

        service.metrics().setGauge(
            "active_connections",
            "payment-api",
            12,
            Map.of()
        );

        service.alerts().register(
            new AlertRule(
                "high_latency",
                "payment_latency_ms",
                200,
                2,
                new GreaterThanPolicy()
            )
        );

        service.alerts().evaluate("high_latency", 220);
        service.alerts().evaluate("high_latency", 240);

        if (
            service.alerts().events().get(0).current()
                != AlertState.FIRING
        ) {
            throw new AssertionError("Alert did not fire");
        }

        service.alerts().evaluate("high_latency", 100);
        service.alerts().evaluate("high_latency", 120);

        if (
            service.alerts().events().get(1).current()
                != AlertState.NORMAL
        ) {
            throw new AssertionError("Alert did not resolve");
        }

        try {
            executePayment(service, -100, false);
            throw new AssertionError("Invalid payment accepted");
        } catch (ValidationException expected) {
            // Expected validation result.
        }

        printReport(service);

        System.out.println(
            "\nALL JAVA 17 OBSERVABILITY TESTS PASSED"
        );
    }

    // ========================================================
    // 14. MAIN
    // ========================================================

    public static void main(String[] args) {
        try {
            runTests();
        } catch (Exception exception) {
            System.err.println(
                "Execution failed: " + exception.getMessage()
            );

            exception.printStackTrace();
            System.exit(1);
        }
    }
}
