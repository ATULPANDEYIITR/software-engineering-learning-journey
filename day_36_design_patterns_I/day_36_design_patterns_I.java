import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/*
 * Design Patterns I: Factory, Builder, Singleton
 *
 * Enterprise scenario:
 * A release platform creates deployment requests, selects an execution
 * adapter for the target infrastructure, and records one process-wide audit
 * trail.
 *
 * Factory:
 *   Decides which DeploymentExecutor implementation should handle a target.
 *
 * Builder:
 *   Constructs and validates a deployment request containing required and
 *   optional configuration.
 *
 * Singleton:
 *   Provides one shared AuditRegistry within the application process.
 *
 * Java 17 features used here include records, enums, immutable collections,
 * interfaces, generics, and explicit domain exceptions.
 */

public class DesignPatternsI {

    // -----------------------------------------------------------------------
    // Domain types
    // -----------------------------------------------------------------------

    enum DeploymentTarget {
        KUBERNETES,
        VIRTUAL_MACHINE,
        SERVERLESS
    }

    enum RiskLevel {
        LOW,
        MEDIUM,
        HIGH,
        CRITICAL
    }

    enum DeploymentState {
        CREATED,
        VALIDATED,
        EXECUTING,
        COMPLETED,
        FAILED
    }

    record AuditEvent(
        String id,
        String type,
        String application,
        String timestamp
    ) {
        AuditEvent {
            Objects.requireNonNull(id);
            Objects.requireNonNull(type);
            Objects.requireNonNull(application);
            Objects.requireNonNull(timestamp);
        }
    }

    static final class InvalidDeploymentException
            extends RuntimeException {

        InvalidDeploymentException(String message) {
            super(message);
        }
    }

    // -----------------------------------------------------------------------
    // Builder Pattern
    // -----------------------------------------------------------------------

    static final class DeploymentRequest {

        private final String application;
        private final String version;
        private final String owner;
        private final DeploymentTarget target;
        private final RiskLevel risk;
        private final int replicas;
        private final boolean rollbackEnabled;
        private final List<String> environment;
        private final Map<String, String> metadata;

        private DeploymentRequest(Builder builder) {
            this.application = builder.application;
            this.version = builder.version;
            this.owner = builder.owner;
            this.target = builder.target;
            this.risk = builder.risk;
            this.replicas = builder.replicas;
            this.rollbackEnabled = builder.rollbackEnabled;

            // Defensive immutable copies stop callers from mutating the
            // request after validation.
            this.environment =
                    List.copyOf(builder.environment);

            this.metadata =
                    Map.copyOf(builder.metadata);
        }

        static Builder builder(
                String application,
                String version,
                String owner,
                DeploymentTarget target
        ) {
            return new Builder(
                    application,
                    version,
                    owner,
                    target
            );
        }

        String application() {
            return application;
        }

        String version() {
            return version;
        }

        String owner() {
            return owner;
        }

        DeploymentTarget target() {
            return target;
        }

        RiskLevel risk() {
            return risk;
        }

        int replicas() {
            return replicas;
        }

        boolean rollbackEnabled() {
            return rollbackEnabled;
        }

        List<String> environment() {
            return environment;
        }

        Map<String, String> metadata() {
            return metadata;
        }

        static final class Builder {

            private final String application;
            private final String version;
            private final String owner;
            private final DeploymentTarget target;

            private RiskLevel risk = RiskLevel.MEDIUM;
            private int replicas = 1;
            private boolean rollbackEnabled = true;

            private final List<String> environment =
                    new ArrayList<>();

            private final Map<String, String> metadata =
                    new HashMap<>();

            private Builder(
                    String application,
                    String version,
                    String owner,
                    DeploymentTarget target
            ) {
                this.application = application;
                this.version = version;
                this.owner = owner;
                this.target = target;
            }

            Builder risk(RiskLevel value) {
                this.risk = Objects.requireNonNull(value);
                return this;
            }

            Builder replicas(int value) {
                this.replicas = value;
                return this;
            }

            Builder rollbackEnabled(boolean value) {
                this.rollbackEnabled = value;
                return this;
            }

            Builder environmentVariable(String value) {
                if (value == null || !value.contains("=")) {
                    throw new InvalidDeploymentException(
                            "Environment variables require KEY=VALUE."
                    );
                }

                environment.add(value);
                return this;
            }

            Builder metadata(String key, String value) {
                if (key == null || key.isBlank()) {
                    throw new InvalidDeploymentException(
                            "Metadata key cannot be blank."
                    );
                }

                metadata.put(key, value);
                return this;
            }

            DeploymentRequest build() {
                validate();
                return new DeploymentRequest(this);
            }

            private void validate() {
                if (application == null || application.isBlank()) {
                    throw new InvalidDeploymentException(
                            "Application is required."
                    );
                }

                if (version == null ||
                        !version.matches("v?[0-9]+\\.[0-9]+\\.[0-9]+")) {
                    throw new InvalidDeploymentException(
                            "Version must use semantic version syntax."
                    );
                }

                if (owner == null || owner.isBlank()) {
                    throw new InvalidDeploymentException(
                            "Owner is required."
                    );
                }

                if (target == null) {
                    throw new InvalidDeploymentException(
                            "Deployment target is required."
                    );
                }

                if (replicas < 1 || replicas > 100) {
                    throw new InvalidDeploymentException(
                            "Replicas must be between 1 and 100."
                    );
                }

                if (risk == RiskLevel.CRITICAL &&
                        !rollbackEnabled) {
                    throw new InvalidDeploymentException(
                            "Critical deployments require rollback."
                    );
                }

                if (target == DeploymentTarget.SERVERLESS &&
                        replicas != 1) {
                    throw new InvalidDeploymentException(
                            "Serverless deployment requires one replica."
                    );
                }
            }
        }
    }

    // -----------------------------------------------------------------------
    // Factory Pattern
    // -----------------------------------------------------------------------

    interface DeploymentExecutor {

        String execute(DeploymentRequest request);
    }

    static final class KubernetesExecutor
            implements DeploymentExecutor {

        @Override
        public String execute(DeploymentRequest request) {
            return "Kubernetes rollout: "
                    + request.application()
                    + " "
                    + request.version()
                    + " replicas="
                    + request.replicas();
        }
    }

    static final class VirtualMachineExecutor
            implements DeploymentExecutor {

        @Override
        public String execute(DeploymentRequest request) {
            return "VM deployment: "
                    + request.application()
                    + " "
                    + request.version()
                    + " replicas="
                    + request.replicas();
        }
    }

    static final class ServerlessExecutor
            implements DeploymentExecutor {

        @Override
        public String execute(DeploymentRequest request) {
            return "Serverless publication: "
                    + request.application()
                    + " "
                    + request.version();
        }
    }

    static final class DeploymentExecutorFactory {

        private static final Map<DeploymentTarget, DeploymentExecutor>
                EXECUTORS;

        static {
            EnumMap<DeploymentTarget, DeploymentExecutor> map =
                    new EnumMap<>(DeploymentTarget.class);

            map.put(
                    DeploymentTarget.KUBERNETES,
                    new KubernetesExecutor()
            );

            map.put(
                    DeploymentTarget.VIRTUAL_MACHINE,
                    new VirtualMachineExecutor()
            );

            map.put(
                    DeploymentTarget.SERVERLESS,
                    new ServerlessExecutor()
            );

            EXECUTORS = Collections.unmodifiableMap(map);
        }

        private DeploymentExecutorFactory() {
        }

        static DeploymentExecutor create(
                DeploymentTarget target
        ) {
            DeploymentExecutor executor = EXECUTORS.get(target);

            if (executor == null) {
                throw new InvalidDeploymentException(
                        "No executor exists for target " + target
                );
            }

            return executor;
        }
    }

    // -----------------------------------------------------------------------
    // Singleton Pattern
    // -----------------------------------------------------------------------

    static final class AuditRegistry {

        /*
         * The initialization-on-demand holder idiom provides lazy creation
         * while relying on Java class initialization for thread safety.
         */
        private static class Holder {
            private static final AuditRegistry INSTANCE =
                    new AuditRegistry();
        }

        private final List<AuditEvent> events =
                Collections.synchronizedList(new ArrayList<>());

        private AuditRegistry() {
        }

        static AuditRegistry instance() {
            return Holder.INSTANCE;
        }

        void record(
                String type,
                String application
        ) {
            events.add(
                    new AuditEvent(
                            UUID.randomUUID().toString(),
                            type,
                            application,
                            java.time.Instant.now().toString()
                    )
            );
        }

        List<AuditEvent> snapshot() {
            synchronized (events) {
                return List.copyOf(events);
            }
        }
    }

    // -----------------------------------------------------------------------
    // Enterprise service
    // -----------------------------------------------------------------------

    static final class DeploymentGovernanceService {

        private final AuditRegistry auditRegistry;

        DeploymentGovernanceService(
                AuditRegistry auditRegistry
        ) {
            this.auditRegistry =
                    Objects.requireNonNull(auditRegistry);
        }

        DeploymentState deploy(
                DeploymentRequest request
        ) {
            DeploymentState state = DeploymentState.CREATED;

            auditRegistry.record(
                    "deployment.created",
                    request.application()
            );

            try {
                validatePolicy(request);
                state = DeploymentState.VALIDATED;

                auditRegistry.record(
                        "deployment.validated",
                        request.application()
                );

                DeploymentExecutor executor =
                        DeploymentExecutorFactory.create(
                                request.target()
                        );

                state = DeploymentState.EXECUTING;

                auditRegistry.record(
                        "deployment.executing",
                        request.application()
                );

                System.out.println(
                        executor.execute(request)
                );

                state = DeploymentState.COMPLETED;

                auditRegistry.record(
                        "deployment.completed",
                        request.application()
                );

                return state;
            } catch (RuntimeException exception) {
                auditRegistry.record(
                        "deployment.failed",
                        request.application()
                );

                throw exception;
            }
        }

        private void validatePolicy(
                DeploymentRequest request
        ) {
            if (request.risk() == RiskLevel.CRITICAL &&
                    !request.rollbackEnabled()) {
                throw new InvalidDeploymentException(
                        "Critical deployment lacks rollback."
                );
            }

            if (request.target() ==
                    DeploymentTarget.SERVERLESS &&
                    request.replicas() != 1) {
                throw new InvalidDeploymentException(
                        "Invalid serverless replica policy."
                );
            }
        }
    }

    // -----------------------------------------------------------------------
    // Scenario construction
    // -----------------------------------------------------------------------

    private static DeploymentRequest productionRequest() {
        return DeploymentRequest.builder(
                    "payment-api",
                    "4.2.0",
                    "platform-team",
                    DeploymentTarget.KUBERNETES
                )
                .risk(RiskLevel.HIGH)
                .replicas(6)
                .rollbackEnabled(true)
                .environmentVariable("ENVIRONMENT=production")
                .environmentVariable("REGION=ap-south-1")
                .metadata("changeTicket", "CHG-2026-1042")
                .metadata("ownerTeam", "platform")
                .build();
    }

    private static void demonstrateFactory() {
        System.out.println("\n=== Factory ===");

        DeploymentRequest kubernetesRequest =
                productionRequest();

        DeploymentRequest vmRequest =
                DeploymentRequest.builder(
                            "legacy-reporting",
                            "3.4.1",
                            "operations-team",
                            DeploymentTarget.VIRTUAL_MACHINE
                        )
                        .risk(RiskLevel.MEDIUM)
                        .replicas(2)
                        .build();

        DeploymentRequest serverlessRequest =
                DeploymentRequest.builder(
                            "billing-worker",
                            "2.1.0",
                            "platform-team",
                            DeploymentTarget.SERVERLESS
                        )
                        .risk(RiskLevel.LOW)
                        .replicas(1)
                        .build();

        System.out.println(
                DeploymentExecutorFactory.create(
                        kubernetesRequest.target()
                ).execute(kubernetesRequest)
        );

        System.out.println(
                DeploymentExecutorFactory.create(
                        vmRequest.target()
                ).execute(vmRequest)
        );

        System.out.println(
                DeploymentExecutorFactory.create(
                        serverlessRequest.target()
                ).execute(serverlessRequest)
        );
    }

    private static void demonstrateBuilderValidation() {
        System.out.println("\n=== Builder Validation ===");

        try {
            DeploymentRequest.builder(
                        "payment-api",
                        "4.2.0",
                        "platform-team",
                        DeploymentTarget.KUBERNETES
                    )
                    .risk(RiskLevel.CRITICAL)
                    .replicas(4)
                    .rollbackEnabled(false)
                    .build();

            throw new AssertionError(
                    "Invalid critical deployment was accepted."
            );
        } catch (InvalidDeploymentException exception) {
            System.out.println(
                    "Rejected invalid request: "
                            + exception.getMessage()
            );
        }
    }

    private static void verifyPatterns() {
        System.out.println("\n=== Verification ===");

        DeploymentRequest request =
                productionRequest();

        if (!request.application().equals("payment-api")) {
            throw new AssertionError(
                    "Builder created an incorrect application."
            );
        }

        DeploymentExecutor executor =
                DeploymentExecutorFactory.create(
                        request.target()
                );

        if (!(executor instanceof KubernetesExecutor)) {
            throw new AssertionError(
                    "Factory returned an incorrect executor."
            );
        }

        AuditRegistry first =
                AuditRegistry.instance();

        AuditRegistry second =
                AuditRegistry.instance();

        if (first != second) {
            throw new AssertionError(
                    "Singleton identity invariant failed."
            );
        }

        System.out.println(
                "Factory selection verified."
        );
        System.out.println(
                "Builder validation verified."
        );
        System.out.println(
                "Singleton identity verified."
        );
    }

    public static void main(String[] args) {
        try {
            System.out.println(
                    "=== Enterprise Deployment Pattern Case Study ==="
            );

            AuditRegistry auditRegistry =
                    AuditRegistry.instance();

            DeploymentGovernanceService service =
                    new DeploymentGovernanceService(
                            auditRegistry
                    );

            DeploymentRequest request =
                    productionRequest();

            DeploymentState state =
                    service.deploy(request);

            System.out.println(
                    "Final state: " + state
            );

            demonstrateFactory();
            demonstrateBuilderValidation();
            verifyPatterns();

            System.out.println("\n=== Audit Events ===");

            for (AuditEvent event :
                    auditRegistry.snapshot()) {
                System.out.println(
                        event.type()
                                + " | "
                                + event.application()
                                + " | "
                                + event.timestamp()
                );
            }

        } catch (RuntimeException exception) {
            System.err.println(
                    "Deployment application failed: "
                            + exception.getMessage()
            );

            System.exit(1);
        }
    }
}
