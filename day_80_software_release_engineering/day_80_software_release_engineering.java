import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.locks.ReentrantLock;

/**
 * Software Release Engineering
 *
 * Enterprise release governance and deployment orchestration.
 *
 * Features:
 * - Typed release domain
 * - Change management
 * - Risk-based approvals
 * - Reviewer independence
 * - Immutable release artifacts
 * - Deployment strategies
 * - Health policy evaluation
 * - Environment locking
 * - Rollback and audit events
 *
 * Runtime: Java 17
 */

public class SoftwareReleaseEngineering {

    // -----------------------------------------------------
    // Enumerations
    // -----------------------------------------------------

    enum Environment {
        STAGING,
        PRODUCTION
    }

    enum Strategy {
        CANARY,
        ROLLING,
        BLUE_GREEN,
        RECREATE
    }

    enum Risk {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    enum ChangeStatus {
        SUBMITTED,
        APPROVED,
        REJECTED,
        IMPLEMENTED
    }

    enum ReleaseStatus {
        CREATED,
        VALIDATING,
        DEPLOYING,
        SUCCEEDED,
        FAILED,
        ROLLED_BACK
    }

    enum CheckStatus {
        PENDING,
        PASSED,
        FAILED
    }

    // -----------------------------------------------------
    // Domain exceptions
    // -----------------------------------------------------

    static class GovernanceException extends RuntimeException {
        GovernanceException(String message) {
            super(message);
        }
    }

    static class DeploymentException extends RuntimeException {
        DeploymentException(String message) {
            super(message);
        }
    }

    // -----------------------------------------------------
    // Immutable release artifact
    // -----------------------------------------------------

    record Artifact(
        String version,
        String commitHash,
        String digest,
        int buildNumber
    ) {
        Artifact {
            Objects.requireNonNull(version);
            Objects.requireNonNull(commitHash);
            Objects.requireNonNull(digest);

            if (version.isBlank()) {
                throw new IllegalArgumentException(
                    "Version is required."
                );
            }

            if (commitHash.length() < 7) {
                throw new IllegalArgumentException(
                    "Invalid commit hash."
                );
            }

            if (!digest.matches("sha256:[a-fA-F0-9]{64}")) {
                throw new IllegalArgumentException(
                    "Invalid SHA-256 digest."
                );
            }

            if (buildNumber <= 0) {
                throw new IllegalArgumentException(
                    "Build number must be positive."
                );
            }
        }
    }

    // -----------------------------------------------------
    // Change management
    // -----------------------------------------------------

    static final class ChangeRequest {

        private final String id;
        private final String title;
        private final String requester;
        private final Risk risk;
        private final Set<String> approvals = new HashSet<>();

        private ChangeStatus status = ChangeStatus.SUBMITTED;

        ChangeRequest(
            String title,
            String requester,
            Risk risk
        ) {
            if (title == null || title.isBlank() ||
                requester == null || requester.isBlank()) {
                throw new IllegalArgumentException(
                    "Change title and requester are required."
                );
            }

            this.id = UUID.randomUUID().toString();
            this.title = title;
            this.requester = requester;
            this.risk = Objects.requireNonNull(risk);
        }

        private int requiredApprovals() {
            return switch (risk) {
                case LOW, MEDIUM -> 1;
                case HIGH -> 2;
                case CRITICAL -> 3;
            };
        }

        synchronized void approve(String reviewer) {
            if (status != ChangeStatus.SUBMITTED) {
                throw new GovernanceException(
                    "Change is not awaiting approval."
                );
            }

            if (reviewer == null || reviewer.isBlank() ||
                reviewer.equals(requester)) {
                throw new GovernanceException(
                    "Invalid independent reviewer."
                );
            }

            approvals.add(reviewer);

            if (approvals.size() >= requiredApprovals()) {
                status = ChangeStatus.APPROVED;
            }
        }

        synchronized void reject() {
            if (status != ChangeStatus.SUBMITTED) {
                throw new GovernanceException(
                    "Change is not awaiting approval."
                );
            }

            status = ChangeStatus.REJECTED;
        }

        synchronized void markImplemented() {
            if (status != ChangeStatus.APPROVED) {
                throw new GovernanceException(
                    "Only approved changes can be implemented."
                );
            }

            status = ChangeStatus.IMPLEMENTED;
        }

        synchronized ChangeStatus status() {
            return status;
        }

        String id() {
            return id;
        }

        String title() {
            return title;
        }

        Set<String> approvals() {
            return Set.copyOf(approvals);
        }
    }

    // -----------------------------------------------------
    // Automated checks
    // -----------------------------------------------------

    record StatusCheck(
        String name,
        CheckStatus status,
        String details
    ) {
        StatusCheck {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException(
                    "Status check name is required."
                );
            }

            Objects.requireNonNull(status);
            Objects.requireNonNull(details);
        }
    }

    // -----------------------------------------------------
    // Health monitoring
    // -----------------------------------------------------

    record Metrics(
        double errorRate,
        double latencyMs,
        double availability
    ) {}

    static final class HealthPolicy {

        private final double maximumErrorRate;
        private final double maximumLatency;
        private final double minimumAvailability;

        HealthPolicy(
            double maximumErrorRate,
            double maximumLatency,
            double minimumAvailability
        ) {
            if (maximumErrorRate < 0 ||
                maximumErrorRate > 1 ||
                maximumLatency <= 0 ||
                minimumAvailability < 0 ||
                minimumAvailability > 1) {
                throw new IllegalArgumentException(
                    "Invalid health policy."
                );
            }

            this.maximumErrorRate = maximumErrorRate;
            this.maximumLatency = maximumLatency;
            this.minimumAvailability = minimumAvailability;
        }

        List<String> evaluate(Metrics metrics) {
            List<String> failures = new ArrayList<>();

            if (!Double.isFinite(metrics.errorRate()) ||
                metrics.errorRate() < 0 ||
                metrics.errorRate() > maximumErrorRate) {
                failures.add("Error rate threshold violated.");
            }

            if (!Double.isFinite(metrics.latencyMs()) ||
                metrics.latencyMs() < 0 ||
                metrics.latencyMs() > maximumLatency) {
                failures.add("Latency threshold violated.");
            }

            if (!Double.isFinite(metrics.availability()) ||
                metrics.availability() < minimumAvailability ||
                metrics.availability() > 1) {
                failures.add("Availability threshold violated.");
            }

            return List.copyOf(failures);
        }
    }

    // -----------------------------------------------------
    // Release domain object
    // -----------------------------------------------------

    static final class Release {

        private final String id;
        private final Artifact artifact;
        private final ChangeRequest change;
        private final Environment environment;
        private final Strategy strategy;
        private final List<StatusCheck> checks;
        private final String previousVersion;

        private ReleaseStatus status = ReleaseStatus.CREATED;
        private int trafficPercentage;

        Release(
            Artifact artifact,
            ChangeRequest change,
            Environment environment,
            Strategy strategy,
            List<StatusCheck> checks,
            String previousVersion
        ) {
            this.id = UUID.randomUUID().toString();
            this.artifact = Objects.requireNonNull(artifact);
            this.change = Objects.requireNonNull(change);
            this.environment = Objects.requireNonNull(environment);
            this.strategy = Objects.requireNonNull(strategy);
            this.checks = List.copyOf(checks);
            this.previousVersion = previousVersion;
        }

        String id() {
            return id;
        }

        ReleaseStatus status() {
            return status;
        }

        Artifact artifact() {
            return artifact;
        }

        String previousVersion() {
            return previousVersion;
        }
    }

    // -----------------------------------------------------
    // Environment registry
    // -----------------------------------------------------

    static final class EnvironmentRegistry {

        private final Map<Environment, String> activeVersions =
            new EnumMap<>(Environment.class);

        EnvironmentRegistry() {
            for (Environment environment : Environment.values()) {
                activeVersions.put(environment, null);
            }
        }

        synchronized String get(Environment environment) {
            return activeVersions.get(environment);
        }

        synchronized void activate(
            Environment environment,
            String version
        ) {
            activeVersions.put(environment, version);
        }

        synchronized void restore(
            Environment environment,
            String version
        ) {
            activeVersions.put(environment, version);
        }

        synchronized Map<Environment, String> snapshot() {
            return Map.copyOf(
                activeVersions.entrySet().stream()
                    .filter(entry -> entry.getValue() != null)
                    .collect(
                        () -> new EnumMap<>(Environment.class),
                        (map, entry) -> map.put(
                            entry.getKey(),
                            entry.getValue()
                        ),
                        EnumMap::putAll
                    )
            );
        }
    }

    // -----------------------------------------------------
    // Audit record
    // -----------------------------------------------------

    record AuditEvent(
        Instant timestamp,
        String releaseId,
        String event,
        String details
    ) {}

    // -----------------------------------------------------
    // Deployment metrics provider
    // -----------------------------------------------------

    interface MetricsProvider {
        Metrics collect(Release release, int trafficPercentage);
    }

    // -----------------------------------------------------
    // Release management service
    // -----------------------------------------------------

    static final class ReleaseService {

        private final EnvironmentRegistry registry =
            new EnvironmentRegistry();

        private final Map<String, Release> releases =
            new HashMap<>();

        private final List<AuditEvent> audit =
            new ArrayList<>();

        private final Map<Environment, ReentrantLock> locks =
            new EnumMap<>(Environment.class);

        private final HealthPolicy healthPolicy;

        ReleaseService(HealthPolicy healthPolicy) {
            this.healthPolicy = Objects.requireNonNull(healthPolicy);

            for (Environment environment : Environment.values()) {
                locks.put(environment, new ReentrantLock());
            }
        }

        synchronized Release createRelease(
            Artifact artifact,
            ChangeRequest change,
            Environment environment,
            Strategy strategy,
            List<StatusCheck> checks
        ) {
            if (change.status() != ChangeStatus.APPROVED) {
                throw new GovernanceException(
                    "Approved change required."
                );
            }

            if (checks == null || checks.isEmpty()) {
                throw new GovernanceException(
                    "Deployment checks are mandatory."
                );
            }

            String currentVersion = registry.get(environment);

            if (Objects.equals(currentVersion, artifact.version())) {
                throw new GovernanceException(
                    "Version is already active."
                );
            }

            Release release = new Release(
                artifact,
                change,
                environment,
                strategy,
                checks,
                currentVersion
            );

            releases.put(release.id(), release);

            record(release, "RELEASE_CREATED", strategy.name());

            return release;
        }

        private synchronized void record(
            Release release,
            String event,
            String details
        ) {
            audit.add(new AuditEvent(
                Instant.now(),
                release.id(),
                event,
                details
            ));
        }

        private void validateChecks(Release release) {
            for (StatusCheck check : release.checks) {
                if (check.status() != CheckStatus.PASSED) {
                    throw new GovernanceException(
                        "Deployment check not passed: " + check.name()
                    );
                }
            }
        }

        private List<Integer> trafficPlan(Strategy strategy) {
            return switch (strategy) {
                case CANARY -> List.of(5, 10, 25, 50, 100);
                case ROLLING -> List.of(25, 50, 75, 100);
                case BLUE_GREEN, RECREATE -> List.of(0, 100);
            };
        }

        boolean deploy(
            Release release,
            MetricsProvider metricsProvider
        ) {
            if (releases.get(release.id()) != release) {
                throw new GovernanceException("Unknown release.");
            }

            if (release.status != ReleaseStatus.CREATED) {
                throw new GovernanceException(
                    "Invalid release state."
                );
            }

            ReentrantLock lock = locks.get(release.environment);

            if (!lock.tryLock()) {
                throw new GovernanceException(
                    "Another deployment is running in this environment."
                );
            }

            try {
                release.status = ReleaseStatus.VALIDATING;
                record(release, "VALIDATION_STARTED", "Artifact validation");

                if (release.change.status() != ChangeStatus.APPROVED) {
                    throw new GovernanceException(
                        "Change approval is no longer valid."
                    );
                }

                validateChecks(release);

                release.status = ReleaseStatus.DEPLOYING;

                record(release, "DEPLOYMENT_STARTED", release.strategy.name());

                for (int traffic : trafficPlan(release.strategy)) {
                    release.trafficPercentage = traffic;

                    Metrics metrics = metricsProvider.collect(
                        release,
                        traffic
                    );

                    List<String> failures = healthPolicy.evaluate(metrics);

                    record(
                        release,
                        "HEALTH_CHECK",
                        "Traffic=" + traffic + "%; " + failures
                    );

                    if (!failures.isEmpty()) {
                        throw new DeploymentException(
                            String.join(" ", failures)
                        );
                    }
                }

                registry.activate(
                    release.environment,
                    release.artifact.version()
                );

                release.status = ReleaseStatus.SUCCEEDED;
                release.change.markImplemented();

                record(
                    release,
                    "RELEASE_SUCCEEDED",
                    release.artifact.version()
                );

                return true;

            } catch (RuntimeException error) {
                release.status = ReleaseStatus.FAILED;

                record(
                    release,
                    "RELEASE_FAILED",
                    error.getMessage()
                );

                rollback(release);

                return false;

            } finally {
                lock.unlock();
            }
        }

        synchronized void rollback(Release release) {
            if (release.status != ReleaseStatus.FAILED &&
                release.status != ReleaseStatus.SUCCEEDED) {
                throw new GovernanceException(
                    "Invalid rollback transition."
                );
            }

            registry.restore(
                release.environment,
                release.previousVersion
            );

            release.trafficPercentage = 0;
            release.status = ReleaseStatus.ROLLED_BACK;

            record(
                release,
                "ROLLBACK_COMPLETED",
                "Restored version: " + release.previousVersion
            );
        }

        void printReport() {
            System.out.println("\nActive environments:");

            registry.snapshot().forEach(
                (environment, version) ->
                    System.out.println(
                        environment + " = " + version
                    )
            );

            System.out.println("\nRelease records:");

            releases.values().stream()
                .forEach(release ->
                    System.out.println(
                        release.id() + " | " +
                        release.artifact.version() + " | " +
                        release.status()
                    )
                );

            System.out.println("\nAudit events: " + audit.size());

            audit.forEach(event ->
                System.out.println(
                    event.timestamp() + " | " +
                    event.event() + " | " +
                    event.details()
                )
            );
        }
    }

    // -----------------------------------------------------
    // Demonstration
    // -----------------------------------------------------

    public static void main(String[] args) {

        HealthPolicy policy = new HealthPolicy(
            0.02,
            500,
            0.995
        );

        ReleaseService service = new ReleaseService(policy);

        ChangeRequest initialChange = new ChangeRequest(
            "Initial production deployment",
            "release-manager",
            Risk.MEDIUM
        );

        initialChange.approve("engineering-lead");

        Artifact initialArtifact = new Artifact(
            "1.0.0",
            "a123456789",
            "sha256:" + "a".repeat(64),
            100
        );

        List<StatusCheck> checks = List.of(
            new StatusCheck(
                "unit-tests",
                CheckStatus.PASSED,
                "All tests passed"
            ),
            new StatusCheck(
                "security-scan",
                CheckStatus.PASSED,
                "No critical vulnerabilities"
            ),
            new StatusCheck(
                "integration-tests",
                CheckStatus.PASSED,
                "Integration successful"
            )
        );

        Release first = service.createRelease(
            initialArtifact,
            initialChange,
            Environment.PRODUCTION,
            Strategy.BLUE_GREEN,
            checks
        );

        MetricsProvider healthyMetrics = (release, traffic) ->
            new Metrics(0.004, 150, 0.999);

        if (!service.deploy(first, healthyMetrics)) {
            throw new IllegalStateException(
                "Initial production deployment failed."
            );
        }

        ChangeRequest secondChange = new ChangeRequest(
            "Database optimization",
            "engineering-team",
            Risk.HIGH
        );

        secondChange.approve("technical-lead");
        secondChange.approve("security-lead");

        Artifact candidate = new Artifact(
            "2.0.0",
            "b234567890",
            "sha256:" + "b".repeat(64),
            101
        );

        Release second = service.createRelease(
            candidate,
            secondChange,
            Environment.PRODUCTION,
            Strategy.CANARY,
            checks
        );

        MetricsProvider unstableMetrics = (release, traffic) -> {
            if (traffic >= 25) {
                return new Metrics(0.08, 900, 0.98);
            }

            return new Metrics(0.004, 150, 0.999);
        };

        boolean success = service.deploy(
            second,
            unstableMetrics
        );

        System.out.println(
            "\nCandidate release: " +
            (success ? "SUCCESS" : "ROLLED BACK")
        );

        service.printReport();
    }
}
