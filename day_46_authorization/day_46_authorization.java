import java.time.Instant;
import java.time.temporal.ChronoUnit;
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
import java.util.stream.Collectors;

/**
 * Enterprise authorization service for source-code repositories.
 *
 * Compile and run:
 *   javac AuthorizationGovernance.java
 *   java AuthorizationGovernance
 *
 * Requires Java 17 or later.
 */
public class AuthorizationGovernance {

    enum Effect {
        ALLOW, DENY
    }

    enum DecisionReason {
        GRANTED,
        UNKNOWN_USER,
        INACTIVE_USER,
        UNKNOWN_RESOURCE,
        MISSING_PERMISSION,
        EXPLICIT_DENY,
        OWNERSHIP_REQUIRED,
        MFA_REQUIRED,
        TRUSTED_NETWORK_REQUIRED,
        INVALID_REQUEST
    }

    record Permission(String resourceType, String action) {
        Permission {
            if (resourceType == null || resourceType.isBlank()
                    || action == null || action.isBlank()) {
                throw new IllegalArgumentException(
                        "Permission resource type and action are required.");
            }
        }

        boolean matches(String requestedResource, String requestedAction) {
            return (resourceType.equals("*")
                    || resourceType.equals(requestedResource))
                    && (action.equals("*") || action.equals(requestedAction));
        }
    }

    record PolicyCondition(
            String department,
            String environment,
            boolean requireOwner,
            boolean requireMfa,
            boolean requireTrustedNetwork) {
    }

    record PolicyRule(
            String name,
            Effect effect,
            Permission permission,
            PolicyCondition condition) {
        PolicyRule {
            Objects.requireNonNull(name);
            Objects.requireNonNull(effect);
            Objects.requireNonNull(permission);
            Objects.requireNonNull(condition);
        }
    }

    static final class Role {
        private final String name;
        private final Set<Permission> permissions;
        private final Set<String> inheritedRoles;

        Role(String name, Set<Permission> permissions, Set<String> inheritedRoles) {
            this.name = Objects.requireNonNull(name);
            this.permissions = Set.copyOf(permissions);
            this.inheritedRoles = Set.copyOf(inheritedRoles);
        }

        String name() {
            return name;
        }

        Set<Permission> permissions() {
            return permissions;
        }

        Set<String> inheritedRoles() {
            return inheritedRoles;
        }
    }

    static final class User {
        private final String id;
        private final String department;
        private final Set<String> roleNames;
        private boolean active;

        User(String id, String department, Set<String> roleNames, boolean active) {
            this.id = Objects.requireNonNull(id);
            this.department = Objects.requireNonNull(department);
            this.roleNames = new HashSet<>(roleNames);
            this.active = active;
        }

        String id() {
            return id;
        }

        String department() {
            return department;
        }

        Set<String> roleNames() {
            return Collections.unmodifiableSet(roleNames);
        }

        boolean active() {
            return active;
        }

        void deactivate() {
            active = false;
        }
    }

    record Resource(
            String id,
            String type,
            String ownerId,
            String environment,
            String classification) {
        Resource {
            Objects.requireNonNull(id);
            Objects.requireNonNull(type);
            Objects.requireNonNull(ownerId);
            Objects.requireNonNull(environment);
            Objects.requireNonNull(classification);
        }
    }

    record AccessContext(
            String requestId,
            Instant timestamp,
            String sourceIp,
            boolean mfaVerified) {
        AccessContext {
            Objects.requireNonNull(requestId);
            Objects.requireNonNull(timestamp);
            Objects.requireNonNull(sourceIp);
        }
    }

    record TemporaryGrant(
            String userId,
            Permission permission,
            Instant expiresAt,
            String justification) {
        TemporaryGrant {
            Objects.requireNonNull(userId);
            Objects.requireNonNull(permission);
            Objects.requireNonNull(expiresAt);
            if (justification == null || justification.isBlank()) {
                throw new IllegalArgumentException(
                        "Temporary grants require a justification.");
            }
        }

        boolean activeAt(Instant instant) {
            return instant.isBefore(expiresAt);
        }
    }

    record Decision(
            boolean allowed,
            DecisionReason reason,
            String matchedPolicy) {
    }

    record AuditEvent(
            String requestId,
            Instant timestamp,
            String userId,
            String resourceId,
            String action,
            boolean allowed,
            DecisionReason reason,
            String policy) {
    }

    static final class AuthorizationException extends RuntimeException {
        AuthorizationException(Decision decision) {
            super("Authorization failed: " + decision.reason());
        }
    }

    static final class AuthorizationService {
        private final Map<String, Role> roles = new LinkedHashMap<>();
        private final Map<String, User> users = new LinkedHashMap<>();
        private final Map<String, Resource> resources = new LinkedHashMap<>();
        private final List<PolicyRule> rules = new ArrayList<>();
        private final List<TemporaryGrant> grants = new ArrayList<>();
        private final List<AuditEvent> audit = new ArrayList<>();

        void registerRole(Role role) {
            if (roles.containsKey(role.name())) {
                throw new IllegalArgumentException("Duplicate role.");
            }
            roles.put(role.name(), role);
            try {
                validateRoleGraph();
            } catch (RuntimeException error) {
                roles.remove(role.name());
                throw error;
            }
        }

        private void validateRoleGraph() {
            Set<String> visiting = new HashSet<>();
            Set<String> visited = new HashSet<>();
            for (String name : roles.keySet()) {
                visitRole(name, visiting, visited);
            }
        }

        private void visitRole(
                String name, Set<String> visiting, Set<String> visited) {
            if (!roles.containsKey(name)) {
                throw new IllegalArgumentException(
                        "Unknown inherited role: " + name);
            }
            if (visiting.contains(name)) {
                throw new IllegalArgumentException(
                        "Role inheritance cycle at " + name);
            }
            if (!visited.add(name)) {
                return;
            }
            visiting.add(name);
            for (String parent : roles.get(name).inheritedRoles()) {
                visitRole(parent, visiting, visited);
            }
            visiting.remove(name);
        }

        void registerUser(User user) {
            if (user.id().isBlank() || users.containsKey(user.id())) {
                throw new IllegalArgumentException("Invalid or duplicate user.");
            }
            if (!roles.keySet().containsAll(user.roleNames())) {
                throw new IllegalArgumentException("Unknown assigned role.");
            }
            users.put(user.id(), user);
        }

        void registerResource(Resource resource) {
            if (resources.containsKey(resource.id())) {
                throw new IllegalArgumentException("Duplicate resource.");
            }
            if (!users.containsKey(resource.ownerId())) {
                throw new IllegalArgumentException("Resource owner not found.");
            }
            resources.put(resource.id(), resource);
        }

        void addPolicy(PolicyRule rule) {
            rules.add(Objects.requireNonNull(rule));
        }

        void addTemporaryGrant(TemporaryGrant grant) {
            if (!users.containsKey(grant.userId())) {
                throw new IllegalArgumentException("Unknown grant recipient.");
            }
            if (!grant.expiresAt().isAfter(Instant.now())) {
                throw new IllegalArgumentException(
                        "New grants must expire in the future.");
            }
            grants.add(grant);
        }

        Set<Permission> resolvePermissions(User user) {
            Set<Permission> effective = new HashSet<>();
            Set<String> visited = new HashSet<>();
            for (String role : user.roleNames()) {
                collectPermissions(role, visited, effective);
            }
            return Collections.unmodifiableSet(effective);
        }

        private void collectPermissions(
                String roleName,
                Set<String> visited,
                Set<Permission> effective) {
            if (!visited.add(roleName)) {
                return;
            }
            Role role = roles.get(roleName);
            if (role == null) {
                throw new IllegalStateException("Role configuration corrupted.");
            }
            effective.addAll(role.permissions());
            for (String parent : role.inheritedRoles()) {
                collectPermissions(parent, visited, effective);
            }
        }

        Decision authorize(
                String userId,
                String resourceId,
                String action,
                AccessContext context) {
            User user = users.get(userId);
            Resource resource = resources.get(resourceId);
            Decision decision;

            if (context.requestId().isBlank() || context.sourceIp().isBlank()) {
                decision = new Decision(
                        false, DecisionReason.INVALID_REQUEST, null);
            } else if (user == null) {
                decision = new Decision(
                        false, DecisionReason.UNKNOWN_USER, null);
            } else if (!user.active()) {
                decision = new Decision(
                        false, DecisionReason.INACTIVE_USER, null);
            } else if (resource == null) {
                decision = new Decision(
                        false, DecisionReason.UNKNOWN_RESOURCE, null);
            } else {
                decision = evaluate(user, resource, action, context);
            }

            audit.add(new AuditEvent(
                    context.requestId(),
                    context.timestamp(),
                    userId,
                    resourceId,
                    action,
                    decision.allowed(),
                    decision.reason(),
                    decision.matchedPolicy()));
            return decision;
        }

        private Decision evaluate(
                User user,
                Resource resource,
                String action,
                AccessContext context) {
            Permission requested = new Permission(resource.type(), action);
            Set<Permission> effective = new HashSet<>(resolvePermissions(user));

            grants.stream()
                    .filter(grant -> grant.userId().equals(user.id()))
                    .filter(grant -> grant.activeAt(context.timestamp()))
                    .map(TemporaryGrant::permission)
                    .forEach(effective::add);

            List<PolicyRule> matching = rules.stream()
                    .filter(rule -> rule.permission().matches(
                            resource.type(), action))
                    .filter(rule -> conditionMatches(
                            rule.condition(), user, resource, context))
                    .toList();

            // An explicit deny is decisive even if a role or temporary grant
            // supplies the requested permission.
            for (PolicyRule rule : matching) {
                if (rule.effect() == Effect.DENY) {
                    return new Decision(
                            false, DecisionReason.EXPLICIT_DENY, rule.name());
                }
            }

            boolean hasPermission = effective.stream().anyMatch(
                    permission -> permission.matches(
                            requested.resourceType(), requested.action()));

            if (!hasPermission) {
                return new Decision(
                        false, DecisionReason.MISSING_PERMISSION, null);
            }

            for (PolicyRule rule : matching) {
                if (rule.effect() != Effect.ALLOW) {
                    continue;
                }
                return new Decision(
                        true, DecisionReason.GRANTED, rule.name());
            }

            boolean ownerRequired = rules.stream()
                    .filter(rule -> rule.effect() == Effect.ALLOW)
                    .filter(rule -> rule.permission().matches(
                            resource.type(), action))
                    .anyMatch(rule -> rule.condition().requireOwner());

            if (ownerRequired && !resource.ownerId().equals(user.id())) {
                return new Decision(
                        false, DecisionReason.OWNERSHIP_REQUIRED, null);
            }

            if ("production".equals(resource.environment())
                    && ("deploy".equals(action) || "delete".equals(action))) {
                if (!context.mfaVerified()) {
                    return new Decision(
                            false, DecisionReason.MFA_REQUIRED, null);
                }
                if (!context.sourceIp().startsWith("10.")) {
                    return new Decision(
                            false, DecisionReason.TRUSTED_NETWORK_REQUIRED, null);
                }
            }

            return new Decision(true, DecisionReason.GRANTED, null);
        }

        private boolean conditionMatches(
                PolicyCondition condition,
                User user,
                Resource resource,
                AccessContext context) {
            if (condition.department() != null
                    && !condition.department().equals(user.department())) {
                return false;
            }
            if (condition.environment() != null
                    && !condition.environment().equals(resource.environment())) {
                return false;
            }
            if (condition.requireMfa() && !context.mfaVerified()) {
                return false;
            }
            return !condition.requireTrustedNetwork()
                    || context.sourceIp().startsWith("10.");
        }

        Resource requireAccess(
                String userId,
                String resourceId,
                String action,
                AccessContext context) {
            Decision decision = authorize(
                    userId, resourceId, action, context);
            if (!decision.allowed()) {
                throw new AuthorizationException(decision);
            }
            return resources.get(resourceId);
        }

        Map<String, Long> auditCountsByOutcome() {
            return audit.stream().collect(Collectors.groupingBy(
                    event -> event.allowed() ? "ALLOW" : "DENY",
                    Collectors.counting()));
        }

        List<AuditEvent> auditEvents() {
            return List.copyOf(audit);
        }
    }

    private static Role role(
            String name, Set<Permission> permissions, Set<String> inherited) {
        return new Role(name, permissions, inherited);
    }

    private static Set<Permission> permissions(Permission... values) {
        return Set.of(values);
    }

    private static Set<String> names(String... values) {
        return Set.of(values);
    }

    public static void main(String[] args) {
        AuthorizationService service = new AuthorizationService();

        service.registerRole(role(
                "reader",
                permissions(
                        new Permission("repository", "read"),
                        new Permission("pull_request", "read")),
                names()));

        service.registerRole(role(
                "developer",
                permissions(
                        new Permission("repository", "write"),
                        new Permission("pull_request", "create")),
                names("reader")));

        service.registerRole(role(
                "reviewer",
                permissions(
                        new Permission("pull_request", "review"),
                        new Permission("pull_request", "approve")),
                names("reader")));

        service.registerRole(role(
                "release_manager",
                permissions(
                        new Permission("repository", "deploy"),
                        new Permission("repository", "delete")),
                names()));

        service.registerUser(
                new User("maya", "engineering", names("developer"), true));
        service.registerUser(
                new User("noah", "security", names("reviewer"), true));
        service.registerUser(
                new User("olivia", "platform", names("release_manager"), true));
        service.registerUser(
                new User("retired-account", "engineering", names("reader"), false));

        service.registerResource(new Resource(
                "payments-service", "repository", "maya",
                "production", "restricted"));
        service.registerResource(new Resource(
                "pr-842", "pull_request", "maya",
                "development", "internal"));

        service.addPolicy(new PolicyRule(
                "platform-production-delete-denial",
                Effect.DENY,
                new Permission("repository", "delete"),
                new PolicyCondition(
                        "platform", "production", false, false, false)));

        Instant now = Instant.now();
        service.addTemporaryGrant(new TemporaryGrant(
                "maya",
                new Permission("repository", "deploy"),
                now.plus(15, ChronoUnit.MINUTES),
                "Incident-approved release window"));

        record TestCase(
                String user, String resource, String action,
                String ip, boolean mfa) {
        }

        List<TestCase> cases = List.of(
                new TestCase("maya", "payments-service", "read", "10.2.0.4", true),
                new TestCase("maya", "payments-service", "write", "10.2.0.4", true),
                new TestCase("noah", "pr-842", "approve", "10.2.0.8", true),
                new TestCase("olivia", "payments-service", "deploy", "10.2.0.9", true),
                new TestCase("olivia", "payments-service", "delete", "10.2.0.9", true),
                new TestCase("olivia", "payments-service", "deploy", "192.0.2.10", true),
                new TestCase("retired-account", "payments-service", "read", "10.2.0.4", true),
                new TestCase("unknown-user", "payments-service", "read", "10.2.0.4", true));

        int sequence = 0;
        for (TestCase test : cases) {
            AccessContext context = new AccessContext(
                    "java-" + (++sequence),
                    now,
                    test.ip(),
                    test.mfa());

            Decision decision = service.authorize(
                    test.user(), test.resource(), test.action(), context);

            System.out.printf(
                    "%s %-16s %-8s %-20s %s (%s)%n",
                    context.requestId(),
                    test.user(),
                    test.action(),
                    test.resource(),
                    decision.allowed() ? "ALLOW" : "DENY",
                    decision.reason());
        }

        System.out.println("Audit counts: " + service.auditCountsByOutcome());

        try {
            service.requireAccess(
                    "noah",
                    "payments-service",
                    "write",
                    new AccessContext(
                            "protected-operation",
                            now,
                            "10.2.0.8",
                            true));
        } catch (AuthorizationException error) {
            System.out.println(error.getMessage());
        }
    }
}
