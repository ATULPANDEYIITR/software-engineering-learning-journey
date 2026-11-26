import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

public class ConsistencyEnterprise {

    enum ConsistencyModel {
        STRONG,
        EVENTUAL,
        CAUSAL
    }

    enum ReplicaStatus {
        ONLINE,
        OFFLINE
    }

    enum OperationStatus {
        COMMITTED,
        REPLICATING,
        REJECTED
    }

    static class ConsistencyException extends RuntimeException {
        ConsistencyException(String message) {
            super(message);
        }
    }

    static class ReplicaUnavailableException extends ConsistencyException {
        ReplicaUnavailableException(String message) {
            super(message);
        }
    }

    static class CausalViolationException extends ConsistencyException {
        CausalViolationException(String message) {
            super(message);
        }
    }

    record Version(Map<String, Long> components) {

        Version {
            components = Collections.unmodifiableMap(
                new HashMap<>(components)
            );
        }

        static Version empty() {
            return new Version(Map.of());
        }

        long get(String node) {
            return components.getOrDefault(node, 0L);
        }

        Version increment(String node) {
            Map<String, Long> next = new HashMap<>(components);
            next.merge(node, 1L, Long::sum);
            return new Version(next);
        }

        Version merge(Version other) {
            Map<String, Long> merged = new HashMap<>(components);

            other.components.forEach(
                (node, value) ->
                    merged.merge(node, value, Math::max)
            );

            return new Version(merged);
        }

        boolean dominates(Version other) {
            Set<String> keys = new java.util.HashSet<>(
                components.keySet()
            );

            keys.addAll(other.components.keySet());

            return keys.stream().allMatch(
                key -> get(key) >= other.get(key)
            );
        }

        boolean concurrentWith(Version other) {
            return !dominates(other) && !other.dominates(this);
        }
    }

    record WriteEvent(
        UUID eventId,
        String key,
        String value,
        String origin,
        Version version,
        Version dependencies,
        Instant timestamp,
        long sequence
    ) {}

    record ReadResult(
        String key,
        String value,
        String replica,
        Version version
    ) {}

    record OperationResult(
        UUID eventId,
        OperationStatus status,
        String message
    ) {}

    static final class Replica {

        private final String id;
        private ReplicaStatus status = ReplicaStatus.ONLINE;

        private final Map<String, WriteEvent> data =
            new HashMap<>();

        private final List<WriteEvent> pending =
            new ArrayList<>();

        private Version clock = Version.empty();

        Replica(String id) {
            this.id = id;
        }

        String id() {
            return id;
        }

        boolean online() {
            return status == ReplicaStatus.ONLINE;
        }

        void setStatus(ReplicaStatus status) {
            this.status = Objects.requireNonNull(status);
        }

        Version clock() {
            return clock;
        }

        WriteEvent get(String key) {
            return data.get(key);
        }

        List<WriteEvent> pending() {
            return pending;
        }

        boolean apply(WriteEvent event) {
            WriteEvent current = data.get(event.key());

            if (current != null) {
                if (current.version().dominates(event.version())) {
                    return false;
                }

                if (current.version().concurrentWith(event.version())) {
                    int comparison = current.timestamp()
                        .compareTo(event.timestamp());

                    if (comparison > 0 ||
                        (comparison == 0 &&
                         current.origin().compareTo(event.origin()) >= 0)) {
                        return false;
                    }
                }
            }

            data.put(event.key(), event);
            clock = clock.merge(event.version());
            return true;
        }

        Version increment(Version context) {
            return clock.merge(context).increment(id);
        }
    }

    static final class ApprovalPolicy {

        private final int requiredApprovals;
        private final Set<String> eligibleRoles;
        private final boolean disallowAuthorApproval;

        ApprovalPolicy(
            int requiredApprovals,
            Set<String> eligibleRoles,
            boolean disallowAuthorApproval
        ) {
            if (requiredApprovals < 0) {
                throw new IllegalArgumentException(
                    "Approval count cannot be negative."
                );
            }

            this.requiredApprovals = requiredApprovals;
            this.eligibleRoles = Set.copyOf(eligibleRoles);
            this.disallowAuthorApproval = disallowAuthorApproval;
        }

        boolean eligible(String author, String reviewer, String role) {
            if (disallowAuthorApproval && author.equals(reviewer)) {
                return false;
            }

            return eligibleRoles.contains(role);
        }

        int requiredApprovals() {
            return requiredApprovals;
        }
    }

    static final class ConsistencyPolicy {

        private final ConsistencyModel model;
        private final boolean requireAllReplicas;
        private final int minimumReplicas;

        ConsistencyPolicy(
            ConsistencyModel model,
            boolean requireAllReplicas,
            int minimumReplicas
        ) {
            this.model = Objects.requireNonNull(model);

            if (minimumReplicas < 1) {
                throw new IllegalArgumentException(
                    "Minimum replicas must be positive."
                );
            }

            this.requireAllReplicas = requireAllReplicas;
            this.minimumReplicas = minimumReplicas;
        }

        ConsistencyModel model() {
            return model;
        }

        boolean requireAllReplicas() {
            return requireAllReplicas;
        }

        int minimumReplicas() {
            return minimumReplicas;
        }
    }

    static final class ConsistencyService {

        private final Map<String, Replica> replicas =
            new LinkedHashMap<>();

        private final AtomicLong sequence = new AtomicLong();

        private ConsistencyPolicy policy;

        ConsistencyService(
            List<String> replicaIds,
            ConsistencyPolicy policy
        ) {
            if (replicaIds == null || replicaIds.size() < 2) {
                throw new IllegalArgumentException(
                    "At least two replicas are required."
                );
            }

            if (replicaIds.stream().anyMatch(
                id -> id == null || id.isBlank()
            )) {
                throw new IllegalArgumentException(
                    "Replica IDs cannot be empty."
                );
            }

            if (replicaIds.stream().distinct().count()
                != replicaIds.size()) {
                throw new IllegalArgumentException(
                    "Replica IDs must be unique."
                );
            }

            replicaIds.forEach(
                id -> replicas.put(id, new Replica(id))
            );

            this.policy = Objects.requireNonNull(policy);
        }

        synchronized void updatePolicy(ConsistencyPolicy policy) {
            this.policy = Objects.requireNonNull(policy);
        }

        synchronized void setReplicaStatus(
            String replicaId,
            ReplicaStatus status
        ) {
            getReplica(replicaId).setStatus(status);
        }

        private Replica getReplica(String id) {
            Replica replica = replicas.get(id);

            if (replica == null) {
                throw new IllegalArgumentException(
                    "Unknown replica: " + id
                );
            }

            return replica;
        }

        private void validate(String key, String value) {
            if (key == null || key.isBlank() || key.length() > 200) {
                throw new IllegalArgumentException(
                    "Key must contain 1 to 200 characters."
                );
            }

            if (value == null || value.length() > 1000000) {
                throw new IllegalArgumentException(
                    "Value is null or exceeds the size limit."
                );
            }
        }

        synchronized OperationResult write(
            String replicaId,
            String key,
            String value,
            Version context
        ) {
            validate(key, value);

            Replica origin = getReplica(replicaId);

            if (!origin.online()) {
                throw new ReplicaUnavailableException(
                    "Origin replica is offline."
                );
            }

            Version dependencies = context == null
                ? Version.empty()
                : context;

            if (
                policy.model() == ConsistencyModel.CAUSAL &&
                !origin.clock().dominates(dependencies)
            ) {
                throw new CausalViolationException(
                    "Origin has not observed all dependencies."
                );
            }

            if (policy.model() == ConsistencyModel.STRONG) {
                List<String> unavailable = replicas.values()
                    .stream()
                    .filter(replica -> !replica.online())
                    .map(Replica::id)
                    .toList();

                if (
                    policy.requireAllReplicas() &&
                    !unavailable.isEmpty()
                ) {
                    throw new ReplicaUnavailableException(
                        "Strong write rejected. Offline replicas: "
                        + unavailable
                    );
                }

                long available = replicas.values().stream()
                    .filter(Replica::online)
                    .count();

                if (available < policy.minimumReplicas()) {
                    throw new ReplicaUnavailableException(
                        "Insufficient available replicas."
                    );
                }
            }

            long eventSequence = sequence.incrementAndGet();

            WriteEvent event = new WriteEvent(
                UUID.randomUUID(),
                key,
                value,
                replicaId,
                origin.increment(dependencies),
                dependencies,
                Instant.now(),
                eventSequence
            );

            if (policy.model() == ConsistencyModel.STRONG) {
                // Validation occurs before this commit phase.
                replicas.values().forEach(
                    replica -> replica.apply(event)
                );

                return new OperationResult(
                    event.eventId(),
                    OperationStatus.COMMITTED,
                    "Synchronous replica commit completed."
                );
            }

            origin.apply(event);

            replicas.values().stream()
                .filter(replica -> !replica.id().equals(replicaId))
                .forEach(replica -> replica.pending().add(event));

            return new OperationResult(
                event.eventId(),
                OperationStatus.REPLICATING,
                "Local commit completed; replication is pending."
            );
        }

        synchronized Optional<ReadResult> read(
            String replicaId,
            String key,
            Version requiredContext
        ) {
            Replica replica = getReplica(replicaId);

            if (!replica.online()) {
                throw new ReplicaUnavailableException(
                    "Read replica is offline."
                );
            }

            WriteEvent event;

            if (policy.model() == ConsistencyModel.STRONG) {
                event = replicas.values()
                    .stream()
                    .map(candidate -> candidate.get(key))
                    .filter(Objects::nonNull)
                    .max(
                        Comparator.comparingLong(
                            WriteEvent::sequence
                        )
                    )
                    .orElse(null);
            } else {
                event = replica.get(key);
            }

            if (event == null) {
                return Optional.empty();
            }

            if (
                requiredContext != null &&
                !event.version().dominates(requiredContext)
            ) {
                throw new CausalViolationException(
                    "Read does not satisfy the required causal context."
                );
            }

            return Optional.of(
                new ReadResult(
                    key,
                    event.value(),
                    replicaId,
                    event.version()
                )
            );
        }

        synchronized int synchronize() {
            int applied = 0;

            for (Replica replica : replicas.values()) {
                if (!replica.online()) continue;

                boolean progress = true;

                while (progress && !replica.pending().isEmpty()) {
                    progress = false;

                    List<WriteEvent> remaining = new ArrayList<>();

                    for (WriteEvent event : replica.pending()) {
                        if (
                            policy.model() == ConsistencyModel.CAUSAL &&
                            !replica.clock().dominates(event.dependencies())
                        ) {
                            remaining.add(event);
                            continue;
                        }

                        if (replica.apply(event)) {
                            applied++;
                        }

                        progress = true;
                    }

                    replica.pending().clear();
                    replica.pending().addAll(remaining);
                }
            }

            return applied;
        }

        synchronized Map<String, Object> inspect(String key) {
            Map<String, Object> result = new LinkedHashMap<>();

            for (Replica replica : replicas.values()) {
                WriteEvent event = replica.get(key);

                Map<String, Object> state = new LinkedHashMap<>();
                state.put("status", replica.online()
                    ? ReplicaStatus.ONLINE
                    : ReplicaStatus.OFFLINE);
                state.put("value", event == null ? null : event.value());
                state.put("clock", event == null
                    ? Map.of()
                    : event.version().components());
                state.put("pending", replica.pending().size());

                result.put(replica.id(), state);
            }

            return result;
        }
    }

    static void strongConsistency() {
        System.out.println("\n1. STRONG CONSISTENCY");

        ConsistencyService service = new ConsistencyService(
            List.of("mumbai", "delhi", "singapore"),
            new ConsistencyPolicy(
                ConsistencyModel.STRONG,
                true,
                3
            )
        );

        service.write(
            "mumbai",
            "account:101",
            "balance=50000",
            null
        );

        System.out.println(
            "Delhi read: " +
            service.read("delhi", "account:101", null).orElseThrow()
        );

        service.setReplicaStatus(
            "singapore",
            ReplicaStatus.OFFLINE
        );

        try {
            service.write(
                "mumbai",
                "account:101",
                "balance=40000",
                null
            );
        } catch (ConsistencyException exception) {
            System.out.println(
                "Rejected: " + exception.getMessage()
            );
        }

        System.out.println(service.inspect("account:101"));
    }

    static void eventualConsistency() {
        System.out.println("\n2. EVENTUAL CONSISTENCY");

        ConsistencyService service = new ConsistencyService(
            List.of("region-a", "region-b", "region-c"),
            new ConsistencyPolicy(
                ConsistencyModel.EVENTUAL,
                false,
                1
            )
        );

        service.write(
            "region-a",
            "inventory:1",
            "quantity=250",
            null
        );

        System.out.println("Before synchronization:");
        System.out.println(service.inspect("inventory:1"));

        System.out.println(
            "Applied events: " + service.synchronize()
        );

        System.out.println("After synchronization:");
        System.out.println(service.inspect("inventory:1"));
    }

    static void causalConsistency() {
        System.out.println("\n3. CAUSAL CONSISTENCY");

        ConsistencyService service = new ConsistencyService(
            List.of("node-a", "node-b", "node-c"),
            new ConsistencyPolicy(
                ConsistencyModel.CAUSAL,
                false,
                1
            )
        );

        OperationResult first = service.write(
            "node-a",
            "order:1",
            "CREATED",
            null
        );

        Version firstContext = service.read(
            "node-a",
            "order:1",
            null
        ).orElseThrow().version();

        OperationResult second = service.write(
            "node-a",
            "payment:1",
            "INITIATED",
            firstContext
        );

        System.out.println("Order event: " + first.eventId());
        System.out.println("Payment event: " + second.eventId());

        service.synchronize();

        System.out.println(
            "Node B payment: " +
            service.read("node-b", "payment:1", firstContext)
                .orElseThrow()
        );

        System.out.println(service.inspect("payment:1"));
    }

    static void failureHandling() {
        System.out.println("\n4. FAILURE HANDLING");

        ConsistencyService service = new ConsistencyService(
            List.of("primary", "secondary"),
            new ConsistencyPolicy(
                ConsistencyModel.EVENTUAL,
                false,
                1
            )
        );

        try {
            service.write("primary", "", "invalid", null);
        } catch (IllegalArgumentException exception) {
            System.out.println(
                "Validation: " + exception.getMessage()
            );
        }

        service.setReplicaStatus(
            "secondary",
            ReplicaStatus.OFFLINE
        );

        service.write(
            "primary",
            "session:10",
            "ACTIVE",
            null
        );

        service.setReplicaStatus(
            "secondary",
            ReplicaStatus.ONLINE
        );

        service.synchronize();

        System.out.println(
            "Recovered read: " +
            service.read("secondary", "session:10", null)
                .orElseThrow()
        );
    }

    public static void main(String[] args) {
        try {
            strongConsistency();
            eventualConsistency();
            causalConsistency();
            failureHandling();
        } catch (Exception exception) {
            System.err.println(
                "Application failure: " + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
