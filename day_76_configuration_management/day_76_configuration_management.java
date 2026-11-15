import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Predicate;
import java.util.stream.Collectors;

/**
 * Enterprise Configuration Governance System.
 *
 * Java 17.
 *
 * Models:
 * - Typed configuration definitions
 * - Environment-specific configuration
 * - Secret references
 * - Role-based secret access
 * - Configuration versioning
 * - Approval workflows
 * - Policy enforcement
 * - Deployment and rollback
 * - Audit events
 */

public class ConfigurationGovernance {

    enum Environment {
        DEVELOPMENT,
        TESTING,
        STAGING,
        PRODUCTION
    }

    enum ValueType {
        STRING,
        INTEGER,
        BOOLEAN
    }

    enum Role {
        DEVELOPER,
        REVIEWER,
        SECURITY_OFFICER,
        ADMINISTRATOR
    }

    enum ChangeState {
        DRAFT,
        VALIDATED,
        APPROVED,
        DEPLOYED,
        REJECTED,
        ROLLED_BACK
    }

    static class ConfigurationException extends RuntimeException {
        ConfigurationException(String message) {
            super(message);
        }
    }

    static class AuthorizationException extends RuntimeException {
        AuthorizationException(String message) {
            super(message);
        }
    }

    record Principal(String id, Role role) {
        Principal {
            if (id == null || id.isBlank() || role == null) {
                throw new IllegalArgumentException(
                    "Valid principal identity and role are required"
                );
            }
        }
    }

    record ConfigDefinition(
        String name,
        ValueType type,
        String defaultValue,
        boolean required,
        boolean secret,
        Long minimum,
        Long maximum,
        Set<String> choices
    ) {
        ConfigDefinition {
            if (
                name == null ||
                !name.matches("[A-Z][A-Z0-9_]*")
            ) {
                throw new IllegalArgumentException(
                    "Invalid configuration name"
                );
            }

            Objects.requireNonNull(type);

            choices = choices == null
                ? Set.of()
                : Set.copyOf(choices);

            if (
                minimum != null &&
                maximum != null &&
                minimum > maximum
            ) {
                throw new IllegalArgumentException(
                    "Invalid numeric range"
                );
            }
        }
    }

    record ConfigChange(
        String key,
        String oldValue,
        String newValue,
        boolean secretReference
    ) {}

    record AuditEvent(
        Instant timestamp,
        String actor,
        String action,
        String resource,
        boolean successful,
        String detail
    ) {}

    record ReviewDecision(
        String reviewerId,
        Role reviewerRole,
        boolean approved,
        String comment,
        int reviewedRevision
    ) {}

    record PolicyDecision(
        boolean allowed,
        List<String> violations
    ) {
        PolicyDecision {
            violations = List.copyOf(violations);
        }
    }

    interface ConfigurationValidator {
        void validate(
            ConfigDefinition definition,
            String value
        );
    }

    static final class TypedValidator
        implements ConfigurationValidator {

        @Override
        public void validate(
            ConfigDefinition definition,
            String value
        ) {
            if (value == null) {
                if (definition.required()) {
                    throw new ConfigurationException(
                        definition.name() + " is required"
                    );
                }
                return;
            }

            switch (definition.type()) {
                case STRING -> {
                    // String values are retained without implicit coercion.
                }

                case INTEGER -> {
                    long number;

                    try {
                        number = Long.parseLong(value);
                    } catch (NumberFormatException exception) {
                        throw new ConfigurationException(
                            "Invalid integer: " + definition.name()
                        );
                    }

                    if (
                        definition.minimum() != null &&
                        number < definition.minimum()
                    ) {
                        throw new ConfigurationException(
                            "Value below minimum: " + definition.name()
                        );
                    }

                    if (
                        definition.maximum() != null &&
                        number > definition.maximum()
                    ) {
                        throw new ConfigurationException(
                            "Value above maximum: " + definition.name()
                        );
                    }
                }

                case BOOLEAN -> {
                    if (
                        !value.equals("true") &&
                        !value.equals("false")
                    ) {
                        throw new ConfigurationException(
                            "Boolean must be true or false: " +
                            definition.name()
                        );
                    }
                }
            }

            if (
                !definition.choices().isEmpty() &&
                !definition.choices().contains(value)
            ) {
                throw new ConfigurationException(
                    "Value not allowed: " + definition.name()
                );
            }
        }
    }

    static final class SchemaRegistry {
        private final Map<String, ConfigDefinition> definitions =
            new LinkedHashMap<>();

        public void register(ConfigDefinition definition) {
            Objects.requireNonNull(definition);

            if (definitions.containsKey(definition.name())) {
                throw new ConfigurationException(
                    "Duplicate definition: " + definition.name()
                );
            }

            definitions.put(definition.name(), definition);
        }

        public ConfigDefinition get(String name) {
            ConfigDefinition definition = definitions.get(name);

            if (definition == null) {
                throw new ConfigurationException(
                    "Unknown configuration: " + name
                );
            }

            return definition;
        }

        public Map<String, ConfigDefinition> all() {
            return Collections.unmodifiableMap(definitions);
        }
    }

    static final class SecretVault {
        private final Map<String, String> secrets =
            new ConcurrentHashMap<>();

        public void store(String key, String value) {
            if (
                key == null ||
                key.isBlank() ||
                value == null ||
                value.isBlank()
            ) {
                throw new ConfigurationException(
                    "Secret key and value are required"
                );
            }

            secrets.put(key, value);
        }

        public String retrieve(String key, Principal principal) {
            if (
                principal.role() != Role.ADMINISTRATOR &&
                principal.role() != Role.SECURITY_OFFICER
            ) {
                throw new AuthorizationException(
                    "Secret retrieval is not authorized"
                );
            }

            String value = secrets.get(key);

            if (value == null) {
                throw new ConfigurationException(
                    "Secret does not exist: " + key
                );
            }

            return value;
        }

        public boolean contains(String key) {
            return secrets.containsKey(key);
        }

        @Override
        public String toString() {
            return "SecretVault[count=" + secrets.size() +
                ", values=[REDACTED]]";
        }
    }

    static final class ConfigurationRepository {
        private final Environment environment;
        private final SchemaRegistry schema;
        private final ConfigurationValidator validator;
        private final SecretVault vault;

        private Map<String, String> values =
            new LinkedHashMap<>();

        private final AtomicLong version = new AtomicLong();

        ConfigurationRepository(
            Environment environment,
            SchemaRegistry schema,
            SecretVault vault
        ) {
            this.environment = environment;
            this.schema = schema;
            this.vault = vault;
            this.validator = new TypedValidator();
        }

        public synchronized void load(
            Map<String, String> input
        ) {
            Map<String, String> candidate =
                new LinkedHashMap<>();

            for (ConfigDefinition definition :
                schema.all().values()) {

                if (definition.secret()) {
                    if (
                        definition.required() &&
                        !vault.contains(definition.name())
                    ) {
                        throw new ConfigurationException(
                            "Missing secret: " + definition.name()
                        );
                    }
                    continue;
                }

                String value = input.containsKey(definition.name())
                    ? input.get(definition.name())
                    : definition.defaultValue();

                validator.validate(definition, value);

                if (value != null) {
                    candidate.put(definition.name(), value);
                }
            }

            values = candidate;
            version.incrementAndGet();
        }

        public synchronized long version() {
            return version.get();
        }

        public synchronized Map<String, String> snapshot() {
            return Collections.unmodifiableMap(
                new LinkedHashMap<>(values)
            );
        }

        public synchronized String get(String name) {
            ConfigDefinition definition = schema.get(name);

            if (definition.secret()) {
                throw new AuthorizationException(
                    "Secrets cannot be retrieved through configuration"
                );
            }

            if (!values.containsKey(name)) {
                throw new ConfigurationException(
                    "Configuration is not loaded: " + name
                );
            }

            return values.get(name);
        }

        public synchronized void update(
            Map<String, String> changes,
            long expectedVersion
        ) {
            if (expectedVersion != version.get()) {
                throw new ConfigurationException(
                    "Concurrent configuration modification detected"
                );
            }

            Map<String, String> candidate =
                new LinkedHashMap<>(values);

            for (var entry : changes.entrySet()) {
                ConfigDefinition definition =
                    schema.get(entry.getKey());

                if (definition.secret()) {
                    throw new AuthorizationException(
                        "Secret references require the secret workflow"
                    );
                }

                validator.validate(
                    definition,
                    entry.getValue()
                );

                candidate.put(
                    entry.getKey(),
                    entry.getValue()
                );
            }

            values = candidate;
            version.incrementAndGet();
        }

        public String readSecret(
            String name,
            Principal principal
        ) {
            if (!schema.get(name).secret()) {
                throw new ConfigurationException(
                    "Not a secret configuration"
                );
            }

            return vault.retrieve(name, principal);
        }

        public Environment environment() {
            return environment;
        }
    }

    static final class GovernancePolicy {
        private final Environment environment;
        private final int requiredApprovals;
        private final boolean requireSecurityApproval;
        private final boolean requireTests;
        private final boolean requireSecretScan;
        private final boolean requireResolvedDiscussions;

        GovernancePolicy(
            Environment environment,
            int requiredApprovals,
            boolean requireSecurityApproval,
            boolean requireTests,
            boolean requireSecretScan,
            boolean requireResolvedDiscussions
        ) {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Approval count cannot be negative"
                );
            }

            this.environment = environment;
            this.requiredApprovals = requiredApprovals;
            this.requireSecurityApproval = requireSecurityApproval;
            this.requireTests = requireTests;
            this.requireSecretScan = requireSecretScan;
            this.requireResolvedDiscussions =
                requireResolvedDiscussions;
        }

        PolicyDecision evaluate(
            ConfigurationChangeRequest request
        ) {
            List<String> errors = new ArrayList<>();

            Set<String> eligibleReviewers =
                new HashSet<>();

            for (ReviewDecision decision : request.reviews) {
                if (
                    decision.approved() &&
                    !decision.reviewerId().equals(request.author) &&
                    decision.reviewedRevision() == request.revision
                ) {
                    eligibleReviewers.add(
                        decision.reviewerId()
                    );
                }
            }

            if (eligibleReviewers.size() < requiredApprovals) {
                errors.add("Insufficient current approvals");
            }

            if (requireSecurityApproval &&
                environment == Environment.PRODUCTION) {

                boolean securityApproved = request.reviews.stream()
                    .anyMatch(review ->
                        review.approved() &&
                        review.reviewerRole() ==
                            Role.SECURITY_OFFICER &&
                        !review.reviewerId().equals(request.author) &&
                        review.reviewedRevision() == request.revision
                    );

                if (!securityApproved) {
                    errors.add(
                        "Production security approval is required"
                    );
                }
            }

            if (requireTests &&
                !Boolean.TRUE.equals(
                    request.checks.get("unit-tests")
                )) {
                errors.add("Unit tests must pass");
            }

            if (requireSecretScan &&
                !Boolean.TRUE.equals(
                    request.checks.get("secret-scan")
                )) {
                errors.add("Secret scanning must pass");
            }

            if (request.hasConflicts) {
                errors.add("Merge conflicts must be resolved");
            }

            if (!request.sourceSynchronized) {
                errors.add("Source branch must be synchronized");
            }

            if (request.reviewedRevision != request.revision) {
                errors.add("Review decisions are stale");
            }

            if (
                requireResolvedDiscussions &&
                request.unresolvedDiscussions > 0
            ) {
                errors.add("Discussions remain unresolved");
            }

            if (!request.configurationValidated) {
                errors.add("Configuration validation failed");
            }

            if (request.state == ChangeState.DRAFT) {
                errors.add("Draft changes cannot be deployed");
            }

            if (request.state == ChangeState.REJECTED) {
                errors.add("Rejected changes cannot be deployed");
            }

            return new PolicyDecision(
                errors.isEmpty(),
                errors
            );
        }
    }

    static final class ConfigurationChangeRequest {
        private final String id = UUID.randomUUID().toString();
        private final String author;
        private final Environment targetEnvironment;
        private final List<ConfigChange> changes = new ArrayList<>();
        private final List<ReviewDecision> reviews = new ArrayList<>();
        private final Map<String, Boolean> checks =
            new HashMap<>();

        private ChangeState state = ChangeState.DRAFT;
        private int revision = 1;
        private int reviewedRevision = 1;
        private boolean sourceSynchronized = true;
        private boolean hasConflicts;
        private boolean configurationValidated;
        private int unresolvedDiscussions;

        ConfigurationChangeRequest(
            String author,
            Environment targetEnvironment
        ) {
            this.author = Objects.requireNonNull(author);
            this.targetEnvironment =
                Objects.requireNonNull(targetEnvironment);
        }

        public void addChange(ConfigChange change) {
            if (state == ChangeState.DEPLOYED) {
                throw new ConfigurationException(
                    "Deployed requests cannot be modified"
                );
            }

            changes.add(change);
            revision++;
            reviewedRevision = 0;
            state = ChangeState.DRAFT;
        }

        public void validateConfiguration() {
            if (changes.isEmpty()) {
                throw new ConfigurationException(
                    "Changeset cannot be empty"
                );
            }

            configurationValidated = true;
            state = ChangeState.VALIDATED;
        }

        public void addReview(ReviewDecision decision) {
            if (decision.reviewerId().equals(author)) {
                throw new AuthorizationException(
                    "Self-approval is prohibited"
                );
            }

            if (decision.reviewedRevision() != revision) {
                throw new ConfigurationException(
                    "Review references an outdated revision"
                );
            }

            reviews.removeIf(
                existing -> existing.reviewerId()
                    .equals(decision.reviewerId())
            );

            reviews.add(decision);

            reviewedRevision = revision;

            if (decision.approved()) {
                state = ChangeState.APPROVED;
            } else {
                state = ChangeState.REJECTED;
            }
        }

        public void setCheck(String name, boolean passed) {
            checks.put(name, passed);
        }

        public void synchronizeSource() {
            sourceSynchronized = true;
        }

        public void setConflicts(boolean value) {
            hasConflicts = value;
        }

        public void resolveDiscussion() {
            if (unresolvedDiscussions > 0) {
                unresolvedDiscussions--;
            }
        }

        public void addDiscussion() {
            unresolvedDiscussions++;
        }

        public int revision() {
            return revision;
        }

        public String id() {
            return id;
        }
    }

    static final class DeploymentService {
        private final GovernancePolicy policy;
        private final ConfigurationRepository repository;
        private final List<AuditEvent> audit = new ArrayList<>();

        DeploymentService(
            GovernancePolicy policy,
            ConfigurationRepository repository
        ) {
            this.policy = policy;
            this.repository = repository;
        }

        public void deploy(
            ConfigurationChangeRequest request,
            Principal actor
        ) {
            PolicyDecision decision = policy.evaluate(request);

            if (!decision.allowed()) {
                throw new ConfigurationException(
                    "Deployment rejected: " +
                    String.join("; ", decision.violations())
                );
            }

            Map<String, String> previous =
                repository.snapshot();

            Map<String, String> updates =
                request.changes.stream()
                    .filter(change -> !change.secretReference())
                    .collect(Collectors.toMap(
                        ConfigChange::key,
                        ConfigChange::newValue,
                        (first, second) -> second,
                        LinkedHashMap::new
                    ));

            try {
                repository.update(
                    updates,
                    repository.version()
                );

                request.state = ChangeState.DEPLOYED;

                audit.add(new AuditEvent(
                    Instant.now(),
                    actor.id(),
                    "DEPLOY",
                    request.id,
                    true,
                    "Configuration deployment completed"
                ));

            } catch (RuntimeException exception) {
                // Restore the previous state if deployment fails.
                repository.update(
                    previous,
                    repository.version()
                );

                request.state = ChangeState.ROLLED_BACK;

                audit.add(new AuditEvent(
                    Instant.now(),
                    actor.id(),
                    "DEPLOY",
                    request.id,
                    false,
                    "Deployment failed and rollback was requested"
                ));

                throw exception;
            }
        }

        public List<AuditEvent> auditEvents() {
            return List.copyOf(audit);
        }
    }

    public static void main(String[] args) {
        SchemaRegistry schema = new SchemaRegistry();

        schema.register(new ConfigDefinition(
            "APP_PORT",
            ValueType.INTEGER,
            "8000",
            true,
            false,
            1024L,
            65535L,
            Set.of()
        ));

        schema.register(new ConfigDefinition(
            "DEBUG",
            ValueType.BOOLEAN,
            "false",
            true,
            false,
            null,
            null,
            Set.of()
        ));

        schema.register(new ConfigDefinition(
            "DATABASE_POOL_SIZE",
            ValueType.INTEGER,
            "10",
            true,
            false,
            1L,
            100L,
            Set.of()
        ));

        schema.register(new ConfigDefinition(
            "LOG_LEVEL",
            ValueType.STRING,
            "INFO",
            true,
            false,
            null,
            null,
            Set.of("DEBUG", "INFO", "WARNING", "ERROR")
        ));

        schema.register(new ConfigDefinition(
            "DATABASE_PASSWORD",
            ValueType.STRING,
            null,
            true,
            true,
            null,
            null,
            Set.of()
        ));

        SecretVault vault = new SecretVault();

        vault.store(
            "DATABASE_PASSWORD",
            "local-example-secret"
        );

        ConfigurationRepository repository =
            new ConfigurationRepository(
                Environment.PRODUCTION,
                schema,
                vault
            );

        repository.load(Map.of(
            "APP_PORT", "8000",
            "DEBUG", "false",
            "DATABASE_POOL_SIZE", "10",
            "LOG_LEVEL", "INFO"
        ));

        System.out.println("INITIAL CONFIGURATION");
        System.out.println(repository.snapshot());
        System.out.println("Version: " + repository.version());

        System.out.println("\nSECRET ACCESS");

        Principal developer = new Principal(
            "developer-01",
            Role.DEVELOPER
        );

        Principal securityOfficer = new Principal(
            "security-01",
            Role.SECURITY_OFFICER
        );

        try {
            repository.readSecret(
                "DATABASE_PASSWORD",
                developer
            );
        } catch (AuthorizationException exception) {
            System.out.println(exception.getMessage());
        }

        System.out.println(
            "Authorized retrieval: " +
            !repository.readSecret(
                "DATABASE_PASSWORD",
                securityOfficer
            ).isBlank()
        );

        ConfigurationChangeRequest request =
            new ConfigurationChangeRequest(
                "developer-01",
                Environment.PRODUCTION
            );

        request.addChange(new ConfigChange(
            "APP_PORT",
            "8000",
            "8080",
            false
        ));

        request.addChange(new ConfigChange(
            "DATABASE_POOL_SIZE",
            "10",
            "25",
            false
        ));

        request.validateConfiguration();

        request.setCheck("unit-tests", true);
        request.setCheck("secret-scan", true);

        request.addReview(new ReviewDecision(
            "reviewer-01",
            Role.REVIEWER,
            true,
            "Configuration changes reviewed",
            request.revision()
        ));

        request.addReview(new ReviewDecision(
            "security-01",
            Role.SECURITY_OFFICER,
            true,
            "Security requirements satisfied",
            request.revision()
        ));

        request.addDiscussion();
        request.resolveDiscussion();

        GovernancePolicy policy = new GovernancePolicy(
            Environment.PRODUCTION,
            2,
            true,
            true,
            true,
            true
        );

        PolicyDecision decision = policy.evaluate(request);

        System.out.println("\nPOLICY EVALUATION");
        System.out.println("Allowed: " + decision.allowed());
        System.out.println("Violations: " + decision.violations());

        DeploymentService service = new DeploymentService(
            policy,
            repository
        );

        if (decision.allowed()) {
            service.deploy(
                request,
                new Principal(
                    "administrator-01",
                    Role.ADMINISTRATOR
                )
            );
        }

        System.out.println("\nDEPLOYED CONFIGURATION");
        System.out.println(repository.snapshot());

        System.out.println("\nAUDIT EVENTS");

        for (AuditEvent event : service.auditEvents()) {
            System.out.println(event);
        }

        System.out.println("\nINVALID CONFIGURATION");

        try {
            repository.update(
                Map.of("APP_PORT", "99999"),
                repository.version()
            );
        } catch (ConfigurationException exception) {
            System.out.println(
                "Rejected: " + exception.getMessage()
            );
        }
    }
}
