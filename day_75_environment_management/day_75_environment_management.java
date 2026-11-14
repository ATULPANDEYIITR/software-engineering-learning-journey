import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.locks.ReentrantLock;
import java.util.stream.Collectors;

/**
 * Environment Management
 *
 * Enterprise environment governance using Java 17.
 *
 * Features:
 * - Immutable artifact records
 * - Explicit environment policies
 * - Release promotion
 * - Approval governance
 * - Configuration validation
 * - Deployment state transitions
 * - Health verification
 * - Rollback
 *
 * Run:
 * javac EnvironmentManagement.java
 * java EnvironmentManagement
 */
public class EnvironmentManagement {

    enum Environment {
        DEVELOPMENT,
        TESTING,
        STAGING,
        PRODUCTION
    }

    enum DeploymentStatus {
        PENDING,
        VALIDATING,
        DEPLOYED,
        FAILED,
        ROLLED_BACK
    }

    static class GovernanceException extends RuntimeException {
        GovernanceException(String message) {
            super(message);
        }
    }

    static class PolicyViolationException extends GovernanceException {
        PolicyViolationException(String message) {
            super(message);
        }
    }

    static class DeploymentException extends GovernanceException {
        DeploymentException(String message) {
            super(message);
        }
    }

    record Artifact(
        String id,
        String version,
        String sourceCommit,
        String digest,
        Instant createdAt
    ) {
        Artifact {
            Objects.requireNonNull(id);
            Objects.requireNonNull(version);
            Objects.requireNonNull(sourceCommit);
            Objects.requireNonNull(digest);
            Objects.requireNonNull(createdAt);

            if (!version.matches("\\d+\\.\\d+\\.\\d+")) {
                throw new IllegalArgumentException(
                    "Invalid semantic version."
                );
            }

            if (!sourceCommit.matches("[a-f0-9]{7,64}")) {
                throw new IllegalArgumentException(
                    "Invalid source commit."
                );
            }

            if (digest.isBlank()) {
                throw new IllegalArgumentException("Empty artifact digest.");
            }
        }
    }

    record EnvironmentConfiguration(
        Environment environment,
        String applicationUrl,
        String databaseName,
        boolean debug,
        int replicas,
        int minimumHealthyReplicas,
        int deploymentTimeoutSeconds,
        boolean secretsRequired
    ) {
        EnvironmentConfiguration {
            Objects.requireNonNull(environment);
            Objects.requireNonNull(applicationUrl);
            Objects.requireNonNull(databaseName);

            if (replicas < 1 ||
                minimumHealthyReplicas < 1 ||
                minimumHealthyReplicas > replicas) {
                throw new IllegalArgumentException(
                    "Invalid replica configuration."
                );
            }

            if (deploymentTimeoutSeconds <= 0) {
                throw new IllegalArgumentException(
                    "Invalid deployment timeout."
                );
            }

            if (environment == Environment.PRODUCTION && debug) {
                throw new PolicyViolationException(
                    "Production debugging is prohibited."
                );
            }

            if (environment != Environment.DEVELOPMENT && debug) {
                throw new PolicyViolationException(
                    "Debugging is restricted to development."
                );
            }

            if (
                environment != Environment.DEVELOPMENT &&
                !applicationUrl.startsWith("https://")
            ) {
                throw new IllegalArgumentException(
                    "HTTPS is required outside development."
                );
            }
        }
    }

    record Approval(
        String reviewer,
        Instant approvedAt,
        String reason
    ) {
        Approval {
            if (reviewer == null || reviewer.isBlank()) {
                throw new IllegalArgumentException("Reviewer required.");
            }

            Objects.requireNonNull(approvedAt);

            if (reason == null || reason.isBlank()) {
                throw new IllegalArgumentException("Approval reason required.");
            }
        }
    }

    record ReviewPolicy(
        Set<String> requiredChecks,
        boolean approvalRequired,
        boolean independentApprovalRequired,
        Set<String> requiredRoles
    ) {
        ReviewPolicy {
            requiredChecks = Set.copyOf(requiredChecks);
            requiredRoles = Set.copyOf(requiredRoles);
        }
    }

    record DeploymentRequest(
        String artifactId,
        Environment environment,
        String deployedBy,
        Optional<Approval> approval,
        Map<String, Boolean> checks,
        Set<String> availableSecrets
    ) {
        DeploymentRequest {
            Objects.requireNonNull(artifactId);
            Objects.requireNonNull(environment);
            Objects.requireNonNull(deployedBy);
            Objects.requireNonNull(approval);

            checks = Map.copyOf(checks);
            availableSecrets = Set.copyOf(availableSecrets);

            if (deployedBy.isBlank()) {
                throw new IllegalArgumentException("Deployment actor required.");
            }
        }
    }

    static final class Deployment {
        private final String id;
        private final Artifact artifact;
        private final Environment environment;
        private final String deployedBy;
        private final Instant createdAt;
        private final String previousDeploymentId;

        private DeploymentStatus status;
        private String failureReason;

        Deployment(
            String id,
            Artifact artifact,
            Environment environment,
            String deployedBy,
            String previousDeploymentId
        ) {
            this.id = id;
            this.artifact = artifact;
            this.environment = environment;
            this.deployedBy = deployedBy;
            this.previousDeploymentId = previousDeploymentId;
            this.createdAt = Instant.now();
            this.status = DeploymentStatus.PENDING;
            this.failureReason = null;
        }

        void transition(DeploymentStatus next) {
            boolean valid = switch (status) {
                case PENDING ->
                    next == DeploymentStatus.VALIDATING ||
                    next == DeploymentStatus.FAILED;

                case VALIDATING ->
                    next == DeploymentStatus.DEPLOYED ||
                    next == DeploymentStatus.FAILED;

                case DEPLOYED ->
                    next == DeploymentStatus.ROLLED_BACK;

                case FAILED, ROLLED_BACK -> false;
            };

            if (!valid) {
                throw new GovernanceException(
                    "Invalid deployment transition: " +
                    status + " -> " + next
                );
            }

            status = next;
        }

        void fail(String reason) {
            failureReason = reason;

            if (
                status == DeploymentStatus.PENDING ||
                status == DeploymentStatus.VALIDATING
            ) {
                transition(DeploymentStatus.FAILED);
            }
        }

        String id() {
            return id;
        }

        Artifact artifact() {
            return artifact;
        }

        Environment environment() {
            return environment;
        }

        DeploymentStatus status() {
            return status;
        }

        String deployedBy() {
            return deployedBy;
        }

        Instant createdAt() {
            return createdAt;
        }

        String previousDeploymentId() {
            return previousDeploymentId;
        }

        String failureReason() {
            return failureReason;
        }
    }

    static final class EnvironmentState {
        private final EnvironmentConfiguration configuration;
        private final List<Deployment> history = new ArrayList<>();

        private Deployment activeDeployment;
        private boolean available = true;

        EnvironmentState(EnvironmentConfiguration configuration) {
            this.configuration = configuration;
        }

        EnvironmentConfiguration configuration() {
            return configuration;
        }

        List<Deployment> history() {
            return Collections.unmodifiableList(history);
        }

        Deployment activeDeployment() {
            return activeDeployment;
        }
    }

    interface HealthVerifier {
        int verify(
            EnvironmentConfiguration configuration,
            Artifact artifact
        );
    }

    static final class SimulatedHealthVerifier
        implements HealthVerifier {

        @Override
        public int verify(
            EnvironmentConfiguration configuration,
            Artifact artifact
        ) {
            // Infrastructure-specific implementations replace this adapter.
            return configuration.replicas();
        }
    }

    static final class EnvironmentService {
        private static final List<Environment> PROMOTION_ORDER =
            List.of(
                Environment.DEVELOPMENT,
                Environment.TESTING,
                Environment.STAGING,
                Environment.PRODUCTION
            );

        private final Map<Environment, EnvironmentState> environments =
            new EnumMap<>(Environment.class);

        private final Map<String, Artifact> artifacts =
            new HashMap<>();

        private final Map<String, Deployment> deployments =
            new HashMap<>();

        private final Map<Environment, ReviewPolicy> policies =
            new EnumMap<>(Environment.class);

        private final Map<Environment, ReentrantLock> locks =
            new EnumMap<>(Environment.class);

        private final HealthVerifier healthVerifier;

        private int sequence = 0;

        EnvironmentService(HealthVerifier healthVerifier) {
            this.healthVerifier = healthVerifier;

            initializeConfigurations();
            initializePolicies();

            for (Environment environment : Environment.values()) {
                locks.put(environment, new ReentrantLock());
            }
        }

        private void initializeConfigurations() {
            addConfiguration(new EnvironmentConfiguration(
                Environment.DEVELOPMENT,
                "http://localhost:8000",
                "app_development",
                true,
                1,
                1,
                60,
                false
            ));

            addConfiguration(new EnvironmentConfiguration(
                Environment.TESTING,
                "https://test.example.internal",
                "app_testing",
                false,
                1,
                1,
                120,
                true
            ));

            addConfiguration(new EnvironmentConfiguration(
                Environment.STAGING,
                "https://staging.example.com",
                "app_staging",
                false,
                2,
                2,
                180,
                true
            ));

            addConfiguration(new EnvironmentConfiguration(
                Environment.PRODUCTION,
                "https://app.example.com",
                "app_production",
                false,
                3,
                3,
                300,
                true
            ));
        }

        private void addConfiguration(
            EnvironmentConfiguration configuration
        ) {
            environments.put(
                configuration.environment(),
                new EnvironmentState(configuration)
            );
        }

        private void initializePolicies() {
            policies.put(
                Environment.DEVELOPMENT,
                new ReviewPolicy(
                    Set.of(),
                    false,
                    false,
                    Set.of()
                )
            );

            policies.put(
                Environment.TESTING,
                new ReviewPolicy(
                    Set.of(
                        "unit_tests",
                        "integration_tests",
                        "security_scan"
                    ),
                    false,
                    false,
                    Set.of()
                )
            );

            policies.put(
                Environment.STAGING,
                new ReviewPolicy(
                    Set.of(
                        "unit_tests",
                        "integration_tests",
                        "security_scan",
                        "smoke_tests"
                    ),
                    true,
                    true,
                    Set.of("QA_MANAGER")
                )
            );

            policies.put(
                Environment.PRODUCTION,
                new ReviewPolicy(
                    Set.of(
                        "unit_tests",
                        "integration_tests",
                        "security_scan",
                        "smoke_tests",
                        "load_tests"
                    ),
                    true,
                    true,
                    Set.of("PRODUCTION_MANAGER")
                )
            );
        }

        void registerArtifact(Artifact artifact) {
            Artifact existing = artifacts.get(artifact.id());

            if (
                existing != null &&
                !existing.digest().equals(artifact.digest())
            ) {
                throw new GovernanceException(
                    "Artifact identifier conflicts with existing digest."
                );
            }

            artifacts.putIfAbsent(artifact.id(), artifact);
        }

        private void validatePromotion(
            Artifact artifact,
            Environment target
        ) {
            int index = PROMOTION_ORDER.indexOf(target);

            if (index < 0) {
                throw new GovernanceException("Invalid promotion target.");
            }

            if (index == 0) {
                return;
            }

            Environment previous = PROMOTION_ORDER.get(index - 1);

            Deployment active =
                environments.get(previous).activeDeployment;

            if (active == null) {
                throw new PolicyViolationException(
                    "Previous environment has no successful release."
                );
            }

            if (
                !active.artifact().id().equals(artifact.id()) ||
                active.status() != DeploymentStatus.DEPLOYED
            ) {
                throw new PolicyViolationException(
                    "Only the previously promoted artifact is eligible."
                );
            }
        }

        private void validateRequest(
            DeploymentRequest request,
            Artifact artifact
        ) {
            Environment environment = request.environment();

            EnvironmentState state = environments.get(environment);

            if (state == null || !state.available) {
                throw new DeploymentException(
                    "Environment unavailable."
                );
            }

            ReviewPolicy policy = policies.get(environment);

            for (String check : policy.requiredChecks()) {
                if (!Boolean.TRUE.equals(request.checks().get(check))) {
                    throw new PolicyViolationException(
                        "Required check unsuccessful: " + check
                    );
                }
            }

            if (
                state.configuration().secretsRequired()
            ) {
                String prefix = environment.name();

                for (String suffix : List.of(
                    "_DATABASE_PASSWORD",
                    "_APPLICATION_SECRET"
                )) {
                    String secret = prefix + suffix;

                    if (!request.availableSecrets().contains(secret)) {
                        throw new PolicyViolationException(
                            "Missing environment secret: " + secret
                        );
                    }
                }
            }

            if (policy.approvalRequired()) {
                Approval approval = request.approval().orElseThrow(
                    () -> new PolicyViolationException(
                        "Independent approval required."
                    )
                );

                if (
                    policy.independentApprovalRequired() &&
                    approval.reviewer().equals(request.deployedBy())
                ) {
                    throw new PolicyViolationException(
                        "Self-approval is prohibited."
                    );
                }

                if (
                    !policy.requiredRoles().contains(approval.reason())
                ) {
                    throw new PolicyViolationException(
                        "Approval does not satisfy required role policy."
                    );
                }
            }

            validatePromotion(artifact, environment);
        }

        Deployment deploy(DeploymentRequest request) {
            ReentrantLock lock = locks.get(request.environment());
            lock.lock();

            try {
                Artifact artifact = artifacts.get(request.artifactId());

                if (artifact == null) {
                    throw new DeploymentException("Unknown artifact.");
                }

                validateRequest(request, artifact);

                EnvironmentState state =
                    environments.get(request.environment());

                String previousId =
                    state.activeDeployment == null
                        ? null
                        : state.activeDeployment.id();

                String id = String.format("DEP-%05d", ++sequence);

                Deployment deployment = new Deployment(
                    id,
                    artifact,
                    request.environment(),
                    request.deployedBy(),
                    previousId
                );

                state.history.add(deployment);
                deployments.put(id, deployment);

                try {
                    deployment.transition(
                        DeploymentStatus.VALIDATING
                    );

                    int healthy = healthVerifier.verify(
                        state.configuration(),
                        artifact
                    );

                    if (
                        healthy <
                        state.configuration().minimumHealthyReplicas()
                    ) {
                        throw new DeploymentException(
                            "Minimum healthy replica count not reached."
                        );
                    }

                    deployment.transition(
                        DeploymentStatus.DEPLOYED
                    );

                    state.activeDeployment = deployment;

                    System.out.printf(
                        "[DEPLOYED] %s | %s | %s%n",
                        id,
                        request.environment(),
                        artifact.version()
                    );

                    return deployment;

                } catch (RuntimeException exception) {
                    deployment.fail(exception.getMessage());
                    throw exception;
                }

            } finally {
                lock.unlock();
            }
        }

        Deployment rollback(
            Environment environment,
            String requestedBy
        ) {
            if (requestedBy == null || requestedBy.isBlank()) {
                throw new GovernanceException(
                    "Rollback actor required."
                );
            }

            ReentrantLock lock = locks.get(environment);
            lock.lock();

            try {
                EnvironmentState state = environments.get(environment);

                if (state.activeDeployment == null) {
                    throw new DeploymentException(
                        "No active deployment."
                    );
                }

                Deployment current = state.activeDeployment;

                Optional<Deployment> previous = state.history
                    .stream()
                    .filter(item -> item != current)
                    .filter(item ->
                        item.status() == DeploymentStatus.DEPLOYED
                    )
                    .reduce((first, second) -> second);

                Deployment target = previous.orElseThrow(
                    () -> new DeploymentException(
                        "No rollback target available."
                    )
                );

                current.transition(DeploymentStatus.ROLLED_BACK);
                state.activeDeployment = target;

                System.out.printf(
                    "[ROLLBACK] %s restored %s by %s%n",
                    environment,
                    target.id(),
                    requestedBy
                );

                return target;

            } finally {
                lock.unlock();
            }
        }

        void report() {
            System.out.println("\nENVIRONMENT REPORT");

            environments.forEach((environment, state) -> {
                Deployment active = state.activeDeployment;

                System.out.printf(
                    "%-12s | active=%-12s | version=%-8s | history=%d%n",
                    environment,
                    active == null ? "none" : active.id(),
                    active == null ? "none" : active.artifact().version(),
                    state.history.size()
                );
            });
        }
    }

    static Artifact createArtifact(
        String version,
        String commit,
        String contents
    ) {
        try {
            MessageDigest digest =
                MessageDigest.getInstance("SHA-256");

            String hash = java.util.HexFormat.of().formatHex(
                digest.digest(contents.getBytes(StandardCharsets.UTF_8))
            );

            return new Artifact(
                "artifact-" + hash.substring(0, 12),
                version,
                commit,
                hash,
                Instant.now()
            );

        } catch (NoSuchAlgorithmException exception) {
            throw new IllegalStateException(
                "SHA-256 unavailable.",
                exception
            );
        }
    }

    static DeploymentRequest request(
        Artifact artifact,
        Environment environment,
        String actor,
        String approver,
        String role
    ) {
        Map<String, Boolean> checks = Map.of(
            "unit_tests", true,
            "integration_tests", true,
            "security_scan", true,
            "smoke_tests", true,
            "load_tests", true
        );

        Set<String> secrets = environment == Environment.DEVELOPMENT
            ? Set.of()
            : Set.of(
                environment.name() + "_DATABASE_PASSWORD",
                environment.name() + "_APPLICATION_SECRET"
            );

        Optional<Approval> approval = approver == null
            ? Optional.empty()
            : Optional.of(new Approval(
                approver,
                Instant.now(),
                role
            ));

        return new DeploymentRequest(
            artifact.id(),
            environment,
            actor,
            approval,
            checks,
            secrets
        );
    }

    public static void main(String[] args) {
        EnvironmentService service = new EnvironmentService(
            new SimulatedHealthVerifier()
        );

        Artifact v1 = createArtifact(
            "1.0.0",
            "a1b2c3d4e5f6",
            "release-1.0.0"
        );

        Artifact v2 = createArtifact(
            "1.1.0",
            "b2c3d4e5f6a7",
            "release-1.1.0"
        );

        service.registerArtifact(v1);

        for (Environment environment : Environment.values()) {
            String approver = switch (environment) {
                case DEVELOPMENT, TESTING -> null;
                case STAGING -> "qa-manager";
                case PRODUCTION -> "production-manager";
            };

            String role = switch (environment) {
                case STAGING -> "QA_MANAGER";
                case PRODUCTION -> "PRODUCTION_MANAGER";
                default -> "";
            };

            service.deploy(request(
                v1,
                environment,
                "release-engineer",
                approver,
                role
            ));
        }

        service.registerArtifact(v2);

        for (Environment environment : Environment.values()) {
            String approver = switch (environment) {
                case DEVELOPMENT, TESTING -> null;
                case STAGING -> "qa-manager";
                case PRODUCTION -> "production-manager";
            };

            String role = switch (environment) {
                case STAGING -> "QA_MANAGER";
                case PRODUCTION -> "PRODUCTION_MANAGER";
                default -> "";
            };

            service.deploy(request(
                v2,
                environment,
                "release-engineer",
                approver,
                role
            ));
        }

        service.rollback(
            Environment.PRODUCTION,
            "incident-commander"
        );

        service.report();

        try {
            service.deploy(new DeploymentRequest(
                v2.id(),
                Environment.PRODUCTION,
                "developer",
                Optional.empty(),
                Map.of(),
                Set.of()
            ));

        } catch (GovernanceException exception) {
            System.out.println(
                "\nEXPECTED POLICY REJECTION: " +
                exception.getMessage()
            );
        }
    }
}
