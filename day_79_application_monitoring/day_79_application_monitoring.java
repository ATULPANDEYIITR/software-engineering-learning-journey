import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Collectors;

/**
 * Enterprise Application Monitoring System.
 *
 * Java version: 17
 * Dependencies: Java standard library only.
 */
public class ApplicationMonitoring {

    // ========================================================
    // ENUMERATIONS
    // ========================================================

    enum HealthStatus {
        HEALTHY,
        DEGRADED,
        UNHEALTHY,
        UNKNOWN
    }

    enum Severity {
        INFO,
        WARNING,
        CRITICAL
    }

    enum AlertState {
        FIRING,
        RESOLVED
    }

    enum Environment {
        DEVELOPMENT,
        STAGING,
        PRODUCTION
    }

    // ========================================================
    // CUSTOM EXCEPTIONS
    // ========================================================

    static class MonitoringException extends RuntimeException {
        MonitoringException(String message) {
            super(message);
        }

        MonitoringException(String message, Throwable cause) {
            super(message, cause);
        }
    }

    // ========================================================
    // IMMUTABLE DOMAIN RECORDS
    // ========================================================

    record CheckResult(
        String checkId,
        String service,
        String checkName,
        HealthStatus status,
        double latencyMs,
        String message,
        Instant checkedAt
    ) {
        CheckResult {
            Objects.requireNonNull(service);
            Objects.requireNonNull(checkName);
            Objects.requireNonNull(status);
            Objects.requireNonNull(checkedAt);

            if (service.isBlank() || checkName.isBlank()) {
                throw new IllegalArgumentException(
                    "Service and check names are required"
                );
            }

            if (!Double.isFinite(latencyMs) || latencyMs < 0) {
                throw new IllegalArgumentException("Invalid latency");
            }
        }
    }

    record ServicePolicy(
        double warningLatencyMs,
        double criticalLatencyMs,
        int failureThreshold,
        int recoveryThreshold,
        Environment environment
    ) {
        ServicePolicy {
            Objects.requireNonNull(environment);

            if (!Double.isFinite(warningLatencyMs) ||
                !Double.isFinite(criticalLatencyMs) ||
                warningLatencyMs < 0 ||
                criticalLatencyMs < warningLatencyMs) {
                throw new IllegalArgumentException(
                    "Invalid latency policy"
                );
            }

            if (failureThreshold < 1 || recoveryThreshold < 1) {
                throw new IllegalArgumentException(
                    "Invalid state transition thresholds"
                );
            }
        }
    }

    record MetricSnapshot(
        String service,
        long sampleCount,
        double averageLatencyMs,
        double availabilityPercent,
        double maximumLatencyMs
    ) {}

    // ========================================================
    // HEALTH CHECK ABSTRACTION
    // ========================================================

    interface HealthCheck {
        String name();

        String service();

        CheckResult execute();
    }

    static final class SimulatedHealthCheck implements HealthCheck {

        private final String name;
        private final String service;
        private final AtomicBoolean available;
        private final double latencyMs;

        SimulatedHealthCheck(
            String name,
            String service,
            boolean available,
            double latencyMs
        ) {
            if (name == null || name.isBlank() ||
                service == null || service.isBlank()) {
                throw new IllegalArgumentException(
                    "Invalid health check identity"
                );
            }

            if (!Double.isFinite(latencyMs) || latencyMs < 0) {
                throw new IllegalArgumentException("Invalid latency");
            }

            this.name = name;
            this.service = service;
            this.available = new AtomicBoolean(available);
            this.latencyMs = latencyMs;
        }

        @Override
        public String name() {
            return name;
        }

        @Override
        public String service() {
            return service;
        }

        public void setAvailable(boolean value) {
            available.set(value);
        }

        @Override
        public CheckResult execute() {
            boolean success = available.get();

            return new CheckResult(
                UUID.randomUUID().toString(),
                service,
                name,
                success
                    ? HealthStatus.HEALTHY
                    : HealthStatus.UNHEALTHY,
                latencyMs,
                success
                    ? "Dependency responding"
                    : "Dependency unavailable",
                Instant.now()
            );
        }
    }

    // ========================================================
    // METRIC SERVICE
    // ========================================================

    static final class MetricService {

        private final Map<String, List<CheckResult>> history =
            new HashMap<>();

        private final int maximumSamples;

        MetricService(int maximumSamples) {
            if (maximumSamples < 1) {
                throw new IllegalArgumentException(
                    "Maximum samples must be positive"
                );
            }

            this.maximumSamples = maximumSamples;
        }

        public synchronized void record(CheckResult result) {
            List<CheckResult> samples = history.computeIfAbsent(
                result.service(),
                key -> new ArrayList<>()
            );

            samples.add(result);

            if (samples.size() > maximumSamples) {
                samples.remove(0);
            }
        }

        public synchronized MetricSnapshot aggregate(
            String service
        ) {
            List<CheckResult> samples = history.getOrDefault(
                service,
                Collections.emptyList()
            );

            if (samples.isEmpty()) {
                return new MetricSnapshot(
                    service, 0, 0, 0, 0
                );
            }

            double average = samples.stream()
                .mapToDouble(CheckResult::latencyMs)
                .average()
                .orElse(0);

            double maximum = samples.stream()
                .mapToDouble(CheckResult::latencyMs)
                .max()
                .orElse(0);

            long successful = samples.stream()
                .filter(item ->
                    item.status() == HealthStatus.HEALTHY
                )
                .count();

            return new MetricSnapshot(
                service,
                samples.size(),
                average,
                successful * 100.0 / samples.size(),
                maximum
            );
        }
    }

    // ========================================================
    // ALERT DOMAIN
    // ========================================================

    static final class Alert {

        private final String id;
        private final String service;
        private final Instant createdAt;

        private Severity severity;
        private AlertState state;
        private Instant resolvedAt;
        private String message;
        private int occurrences;

        Alert(
            String service,
            Severity severity,
            String message
        ) {
            this.id = UUID.randomUUID().toString();
            this.service = service;
            this.severity = severity;
            this.message = message;
            this.state = AlertState.FIRING;
            this.createdAt = Instant.now();
            this.occurrences = 1;
        }

        void update(Severity severity, String message) {
            this.severity = severity;
            this.message = message;
            this.occurrences++;
        }

        void resolve() {
            if (state == AlertState.RESOLVED) {
                return;
            }

            state = AlertState.RESOLVED;
            resolvedAt = Instant.now();
        }

        String service() {
            return service;
        }

        AlertState state() {
            return state;
        }

        String describe() {
            return "Alert{id='" + id +
                "', service='" + service +
                "', severity=" + severity +
                ", state=" + state +
                ", occurrences=" + occurrences +
                ", message='" + message + "'}";
        }
    }

    static final class AlertService {

        private final Map<String, Alert> active =
            new LinkedHashMap<>();

        private final List<Alert> history =
            new ArrayList<>();

        public synchronized void process(
            String service,
            HealthStatus status
        ) {
            if (status == HealthStatus.HEALTHY ||
                status == HealthStatus.UNKNOWN) {

                Alert alert = active.remove(service);

                if (alert != null) {
                    alert.resolve();
                    history.add(alert);

                    System.out.println(
                        "Resolved alert: " + service
                    );
                }

                return;
            }

            Severity severity =
                status == HealthStatus.UNHEALTHY
                    ? Severity.CRITICAL
                    : Severity.WARNING;

            Alert existing = active.get(service);

            if (existing != null) {
                existing.update(
                    severity,
                    "Service status: " + status
                );

                return;
            }

            Alert alert = new Alert(
                service,
                severity,
                "Service status: " + status
            );

            active.put(service, alert);

            System.out.println(
                "ALERT: " + alert.describe()
            );
        }

        public synchronized List<Alert> activeAlerts() {
            return List.copyOf(active.values());
        }

        public synchronized List<Alert> history() {
            return List.copyOf(history);
        }
    }

    // ========================================================
    // POLICY EVALUATION
    // ========================================================

    static final class HealthPolicyEngine {

        public HealthStatus evaluate(
            List<CheckResult> results,
            ServicePolicy policy,
            int failures,
            int recoveries,
            HealthStatus previousStatus
        ) {
            if (results.isEmpty()) {
                throw new MonitoringException(
                    "Cannot evaluate empty check results"
                );
            }

            boolean failed = results.stream().anyMatch(
                result -> result.status() == HealthStatus.UNHEALTHY
            );

            boolean criticalLatency = results.stream().anyMatch(
                result ->
                    result.latencyMs() >= policy.criticalLatencyMs()
            );

            boolean warningLatency = results.stream().anyMatch(
                result ->
                    result.latencyMs() >= policy.warningLatencyMs()
            );

            if (failed || criticalLatency) {
                return failures >= policy.failureThreshold()
                    ? HealthStatus.UNHEALTHY
                    : HealthStatus.DEGRADED;
            }

            if (warningLatency) {
                return HealthStatus.DEGRADED;
            }

            if (recoveries >= policy.recoveryThreshold()) {
                return HealthStatus.HEALTHY;
            }

            return previousStatus == HealthStatus.UNKNOWN
                ? HealthStatus.DEGRADED
                : previousStatus;
        }
    }

    // ========================================================
    // SERVICE MONITOR
    // ========================================================

    static final class ServiceMonitor {

        private final String name;
        private final ServicePolicy policy;

        private final List<HealthCheck> checks =
            new ArrayList<>();

        private final Set<String> checkNames = new HashSet<>();

        private final MetricService metrics;
        private final AlertService alerts;
        private final HealthPolicyEngine policyEngine;

        private final ExecutorService executor;

        private HealthStatus status = HealthStatus.UNKNOWN;

        private int failures;
        private int recoveries;

        private final AtomicBoolean running =
            new AtomicBoolean(false);

        ServiceMonitor(
            String name,
            ServicePolicy policy,
            MetricService metrics,
            AlertService alerts,
            HealthPolicyEngine policyEngine,
            ExecutorService executor
        ) {
            this.name = Objects.requireNonNull(name);
            this.policy = Objects.requireNonNull(policy);
            this.metrics = metrics;
            this.alerts = alerts;
            this.policyEngine = policyEngine;
            this.executor = executor;
        }

        public synchronized void register(HealthCheck check) {
            if (!name.equals(check.service())) {
                throw new MonitoringException(
                    "Health check belongs to another service"
                );
            }

            if (!checkNames.add(check.name())) {
                throw new MonitoringException(
                    "Duplicate health check: " + check.name()
                );
            }

            checks.add(check);
        }

        public List<CheckResult> executeCycle() {
            if (!running.compareAndSet(false, true)) {
                throw new MonitoringException(
                    "Concurrent monitoring cycle rejected"
                );
            }

            try {
                List<HealthCheck> snapshot;

                synchronized (this) {
                    snapshot = List.copyOf(checks);
                }

                if (snapshot.isEmpty()) {
                    throw new MonitoringException(
                        "No checks registered for " + name
                    );
                }

                List<CompletableFuture<CheckResult>> futures =
                    snapshot.stream()
                        .map(check -> CompletableFuture.supplyAsync(
                            check::execute,
                            executor
                        ))
                        .toList();

                List<CheckResult> results = new ArrayList<>();

                for (CompletableFuture<CheckResult> future : futures) {
                    try {
                        results.add(future.join());
                    } catch (CompletionException error) {
                        throw new MonitoringException(
                            "Health check execution failed",
                            error
                        );
                    }
                }

                results.forEach(metrics::record);

                boolean failed = results.stream().anyMatch(
                    result ->
                        result.status() == HealthStatus.UNHEALTHY ||
                        result.latencyMs() >= policy.criticalLatencyMs()
                );

                if (failed) {
                    failures++;
                    recoveries = 0;
                } else {
                    failures = 0;
                    recoveries++;
                }

                HealthStatus previous = status;

                status = policyEngine.evaluate(
                    results,
                    policy,
                    failures,
                    recoveries,
                    previous
                );

                alerts.process(name, status);

                if (previous != status) {
                    System.out.println(
                        name + ": " + previous + " -> " + status
                    );
                }

                return List.copyOf(results);

            } finally {
                running.set(false);
            }
        }

        String name() {
            return name;
        }

        synchronized HealthStatus status() {
            return status;
        }

        MetricSnapshot metrics() {
            return metrics.aggregate(name);
        }
    }

    // ========================================================
    // DASHBOARD SERVICE
    // ========================================================

    static final class DashboardService {

        private final Map<String, ServiceMonitor> monitors;
        private final AlertService alerts;

        DashboardService(
            Map<String, ServiceMonitor> monitors,
            AlertService alerts
        ) {
            this.monitors = monitors;
            this.alerts = alerts;
        }

        public void display() {
            Map<HealthStatus, Long> counts =
                new EnumMap<>(HealthStatus.class);

            for (HealthStatus status : HealthStatus.values()) {
                counts.put(status, 0L);
            }

            System.out.println(
                "\n========== ENTERPRISE DASHBOARD =========="
            );

            monitors.values().stream()
                .sorted((a, b) -> a.name().compareTo(b.name()))
                .forEach(monitor -> {
                    HealthStatus status = monitor.status();

                    counts.merge(status, 1L, Long::sum);

                    MetricSnapshot metric = monitor.metrics();

                    System.out.printf(
                        "%nService: %s%nStatus: %s%n" +
                        "Samples: %d%nAverage latency: %.2f ms%n" +
                        "Availability: %.2f%%%n",
                        monitor.name(),
                        status,
                        metric.sampleCount(),
                        metric.averageLatencyMs(),
                        metric.availabilityPercent()
                    );
                });

            System.out.println("\nService totals:");

            counts.forEach((status, count) ->
                System.out.println(status + ": " + count)
            );

            System.out.println(
                "Active alerts: " + alerts.activeAlerts().size()
            );

            System.out.println(
                "Generated at: " + Instant.now()
            );

            System.out.println(
                "============================================"
            );
        }
    }

    // ========================================================
    // MONITORING APPLICATION
    // ========================================================

    static final class MonitoringApplication
        implements AutoCloseable {

        private final MetricService metrics =
            new MetricService(500);

        private final AlertService alerts =
            new AlertService();

        private final HealthPolicyEngine policyEngine =
            new HealthPolicyEngine();

        private final ExecutorService executor =
            Executors.newFixedThreadPool(4);

        private final Map<String, ServiceMonitor> monitors =
            new LinkedHashMap<>();

        public void register(ServiceMonitor monitor) {
            if (monitors.putIfAbsent(
                monitor.name(),
                monitor
            ) != null) {
                throw new MonitoringException(
                    "Duplicate service registration"
                );
            }
        }

        public void runCycle() {
            monitors.values().forEach(monitor -> {
                try {
                    monitor.executeCycle();
                } catch (MonitoringException error) {
                    System.err.println(
                        "Monitoring failure for " +
                        monitor.name() + ": " + error.getMessage()
                    );
                }
            });
        }

        public void dashboard() {
            new DashboardService(monitors, alerts).display();
        }

        @Override
        public void close() {
            executor.shutdown();

            try {
                if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                    executor.shutdownNow();
                }
            } catch (InterruptedException error) {
                executor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }

        ServiceMonitor createMonitor(
            String name,
            ServicePolicy policy
        ) {
            return new ServiceMonitor(
                name,
                policy,
                metrics,
                alerts,
                policyEngine,
                executor
            );
        }
    }

    // ========================================================
    // TESTS
    // ========================================================

    static void runTests() {
        MetricService metrics = new MetricService(2);

        for (int i = 0; i < 3; i++) {
            metrics.record(new CheckResult(
                UUID.randomUUID().toString(),
                "test",
                "application",
                HealthStatus.HEALTHY,
                100,
                "Available",
                Instant.now()
            ));
        }

        if (metrics.aggregate("test").sampleCount() != 2) {
            throw new AssertionError("Metric retention test failed");
        }

        AlertService alerts = new AlertService();

        alerts.process("test", HealthStatus.UNHEALTHY);

        if (alerts.activeAlerts().size() != 1) {
            throw new AssertionError("Alert creation failed");
        }

        alerts.process("test", HealthStatus.HEALTHY);

        if (!alerts.activeAlerts().isEmpty()) {
            throw new AssertionError("Alert resolution failed");
        }

        System.out.println("All Java monitoring tests passed.");
    }

    // ========================================================
    // MAIN
    // ========================================================

    public static void main(String[] args) {
        runTests();

        try (MonitoringApplication application =
                 new MonitoringApplication()) {

            ServicePolicy productionPolicy = new ServicePolicy(
                300,
                1000,
                2,
                2,
                Environment.PRODUCTION
            );

            SimulatedHealthCheck appCheck =
                new SimulatedHealthCheck(
                    "application",
                    "payment-api",
                    true,
                    100
                );

            SimulatedHealthCheck databaseCheck =
                new SimulatedHealthCheck(
                    "database",
                    "payment-api",
                    false,
                    180
                );

            SimulatedHealthCheck providerCheck =
                new SimulatedHealthCheck(
                    "payment-provider",
                    "payment-api",
                    true,
                    220
                );

            ServiceMonitor payment = application.createMonitor(
                "payment-api",
                productionPolicy
            );

            payment.register(appCheck);
            payment.register(databaseCheck);
            payment.register(providerCheck);

            application.register(payment);

            for (int cycle = 1; cycle <= 4; cycle++) {
                System.out.println(
                    "\nENTERPRISE MONITORING CYCLE " + cycle
                );

                if (cycle == 3) {
                    databaseCheck.setAvailable(true);
                }

                application.runCycle();
                application.dashboard();
            }
        }
    }
}
