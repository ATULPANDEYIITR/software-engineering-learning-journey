import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/**
 * Distributed Systems: Enterprise Replication and Consistency Platform
 *
 * Java 17 implementation.
 *
 * Features:
 * - Enterprise cluster membership
 * - Distributed node lifecycle
 * - Versioned records
 * - Logical clocks
 * - Network partitions
 * - Configurable consistency policies
 * - Quorum-based replication
 * - Conflict resolution
 * - Idempotent operations
 * - Anti-entropy synchronization
 * - Failure detection
 * - Operational reporting
 *
 * Compile:
 * javac DistributedSystems.java
 *
 * Run:
 * java DistributedSystems
 */

public class DistributedSystems {

    // ========================================================
    // DOMAIN EXCEPTIONS
    // ========================================================

    static class DistributedException extends RuntimeException {
        DistributedException(String message) {
            super(message);
        }
    }

    static class NodeUnavailableException extends DistributedException {
        NodeUnavailableException(String message) {
            super(message);
        }
    }

    static class QuorumUnavailableException extends DistributedException {
        QuorumUnavailableException(String message) {
            super(message);
        }
    }

    static class InvalidOperationException extends DistributedException {
        InvalidOperationException(String message) {
            super(message);
        }
    }

    // ========================================================
    // ENUMS
    // ========================================================

    enum NodeStatus {
        ACTIVE,
        STOPPED,
        SUSPECTED
    }

    enum ConsistencyLevel {
        ONE,
        QUORUM,
        ALL
    }

    enum MessageType {
        REPLICATION,
        HEARTBEAT,
        SYNCHRONIZATION
    }

    enum OperationState {
        CREATED,
        REPLICATING,
        COMMITTED,
        FAILED
    }

    // ========================================================
    // IMMUTABLE VERSION
    // ========================================================

    record Version(long logicalTime, String nodeId)
            implements Comparable<Version> {

        Version {
            if (logicalTime < 0) {
                throw new IllegalArgumentException(
                    "Logical time cannot be negative"
                );
            }

            Objects.requireNonNull(nodeId);

            if (nodeId.isBlank()) {
                throw new IllegalArgumentException(
                    "Node ID cannot be blank"
                );
            }
        }

        @Override
        public int compareTo(Version other) {
            int comparison = Long.compare(
                logicalTime,
                other.logicalTime
            );

            if (comparison != 0) {
                return comparison;
            }

            return nodeId.compareTo(other.nodeId);
        }
    }

    // ========================================================
    // RECORD MODEL
    // ========================================================

    record DistributedRecord(
        String key,
        String value,
        Version version,
        Instant updatedAt
    ) {

        DistributedRecord {
            if (key == null || key.isBlank() || key.length() > 256) {
                throw new IllegalArgumentException(
                    "Invalid distributed key"
                );
            }

            Objects.requireNonNull(value);
            Objects.requireNonNull(version);
            Objects.requireNonNull(updatedAt);

            if (value.length() > 1_000_000) {
                throw new IllegalArgumentException(
                    "Record exceeds maximum size"
                );
            }
        }
    }

    // ========================================================
    // NETWORK MESSAGE
    // ========================================================

    record NetworkMessage(
        String messageId,
        String sender,
        String receiver,
        MessageType type,
        DistributedRecord record
    ) {
        NetworkMessage {
            Objects.requireNonNull(messageId);
            Objects.requireNonNull(sender);
            Objects.requireNonNull(receiver);
            Objects.requireNonNull(type);
        }
    }

    // ========================================================
    // CONSISTENCY POLICY
    // ========================================================

    static final class ConsistencyPolicy {

        private final int replicationFactor;

        ConsistencyPolicy(int replicationFactor) {
            if (replicationFactor < 1) {
                throw new IllegalArgumentException(
                    "Replication factor must be positive"
                );
            }

            this.replicationFactor = replicationFactor;
        }

        int requiredAcknowledgements(ConsistencyLevel level) {
            return switch (level) {
                case ONE -> 1;
                case QUORUM -> replicationFactor / 2 + 1;
                case ALL -> replicationFactor;
            };
        }

        int replicationFactor() {
            return replicationFactor;
        }
    }

    // ========================================================
    // NETWORK TOPOLOGY
    // ========================================================

    static final class Network {

        private final Set<String> partitions =
            ConcurrentHashMap.newKeySet();

        private String link(String a, String b) {
            List<String> endpoints = new ArrayList<>(List.of(a, b));

            Collections.sort(endpoints);

            return endpoints.get(0) + "|" + endpoints.get(1);
        }

        void partition(String a, String b) {
            if (a.equals(b)) {
                throw new InvalidOperationException(
                    "Cannot partition a node from itself"
                );
            }

            partitions.add(link(a, b));
        }

        void heal() {
            partitions.clear();
        }

        boolean connected(String a, String b) {
            return !a.equals(b) &&
                   !partitions.contains(link(a, b));
        }

        boolean isPartitioned() {
            return !partitions.isEmpty();
        }
    }

    // ========================================================
    // DISTRIBUTED NODE
    // ========================================================

    static final class DistributedNode {

        private final String nodeId;
        private final AtomicLong logicalClock =
            new AtomicLong(0);

        private final Map<String, DistributedRecord> data =
            new ConcurrentHashMap<>();

        private final Set<String> processedMessages =
            ConcurrentHashMap.newKeySet();

        private volatile NodeStatus status = NodeStatus.ACTIVE;

        DistributedNode(String nodeId) {
            if (nodeId == null || nodeId.isBlank()) {
                throw new IllegalArgumentException(
                    "Node ID is required"
                );
            }

            this.nodeId = nodeId;
        }

        String id() {
            return nodeId;
        }

        NodeStatus status() {
            return status;
        }

        void stop() {
            status = NodeStatus.STOPPED;
        }

        void start() {
            status = NodeStatus.ACTIVE;
        }

        void assertActive() {
            if (status != NodeStatus.ACTIVE) {
                throw new NodeUnavailableException(
                    "Node unavailable: " + nodeId
                );
            }
        }

        long tick() {
            assertActive();
            return logicalClock.incrementAndGet();
        }

        void observe(Version version) {
            logicalClock.updateAndGet(
                current -> Math.max(
                    current,
                    version.logicalTime()
                ) + 1
            );
        }

        DistributedRecord write(String key, String value) {
            assertActive();

            DistributedRecord record = new DistributedRecord(
                key,
                value,
                new Version(tick(), nodeId),
                Instant.now()
            );

            data.put(key, record);

            return record;
        }

        boolean apply(DistributedRecord incoming) {
            assertActive();

            final boolean[] updated = {false};

            data.compute(incoming.key(), (key, existing) -> {
                if (
                    existing != null &&
                    existing.version().compareTo(
                        incoming.version()
                    ) >= 0
                ) {
                    return existing;
                }

                observe(incoming.version());
                updated[0] = true;

                return incoming;
            });

            return updated[0];
        }

        boolean receive(NetworkMessage message) {
            assertActive();

            if (!processedMessages.add(message.messageId())) {
                return false;
            }

            if (processedMessages.size() > 100_000) {
                processedMessages.clear();
            }

            if (message.type() == MessageType.REPLICATION ||
                message.type() == MessageType.SYNCHRONIZATION) {

                if (message.record() != null) {
                    return apply(message.record());
                }
            }

            return true;
        }

        Optional<DistributedRecord> read(String key) {
            assertActive();

            return Optional.ofNullable(data.get(key));
        }

        Map<String, DistributedRecord> snapshot() {
            return Collections.unmodifiableMap(
                new LinkedHashMap<>(data)
            );
        }

        int recordCount() {
            return data.size();
        }

        long logicalTime() {
            return logicalClock.get();
        }
    }

    // ========================================================
    // OPERATION TRACKING
    // ========================================================

    static final class DistributedOperation {

        private final String operationId = UUID.randomUUID().toString();

        private final DistributedRecord record;

        private final int requiredAcknowledgements;

        private int acknowledgements;

        private OperationState state = OperationState.CREATED;

        DistributedOperation(
            DistributedRecord record,
            int requiredAcknowledgements
        ) {
            this.record = record;
            this.requiredAcknowledgements =
                requiredAcknowledgements;
        }

        void begin() {
            if (state != OperationState.CREATED) {
                throw new InvalidOperationException(
                    "Operation already started"
                );
            }

            state = OperationState.REPLICATING;
        }

        void acknowledge() {
            acknowledgements++;
        }

        void complete() {
            if (acknowledgements < requiredAcknowledgements) {
                state = OperationState.FAILED;

                throw new QuorumUnavailableException(
                    "Insufficient replication acknowledgements"
                );
            }

            state = OperationState.COMMITTED;
        }

        String operationId() {
            return operationId;
        }

        OperationState state() {
            return state;
        }

        int acknowledgements() {
            return acknowledgements;
        }

        DistributedRecord record() {
            return record;
        }
    }

    // ========================================================
    // CLUSTER MEMBERSHIP
    // ========================================================

    static final class Cluster {

        private final Map<String, DistributedNode> nodes =
            new LinkedHashMap<>();

        private final Network network = new Network();

        private final ConsistencyPolicy policy;

        private final List<DistributedOperation> operations =
            new ArrayList<>();

        Cluster(Collection<String> nodeIds) {
            if (nodeIds.size() < 3) {
                throw new IllegalArgumentException(
                    "At least three nodes are required"
                );
            }

            if (nodeIds.stream().distinct().count() != nodeIds.size()) {
                throw new IllegalArgumentException(
                    "Duplicate node identifiers"
                );
            }

            for (String id : nodeIds) {
                nodes.put(id, new DistributedNode(id));
            }

            policy = new ConsistencyPolicy(
                Math.min(3, nodes.size())
            );
        }

        DistributedNode node(String id) {
            DistributedNode node = nodes.get(id);

            if (node == null) {
                throw new InvalidOperationException(
                    "Unknown node: " + id
                );
            }

            return node;
        }

        Network network() {
            return network;
        }

        List<DistributedNode> activeNodes() {
            return nodes.values().stream()
                .filter(n -> n.status() == NodeStatus.ACTIVE)
                .collect(Collectors.toList());
        }

        // ----------------------------------------------------
        // WRITE SERVICE
        // ----------------------------------------------------

        DistributedOperation write(
            String coordinatorId,
            String key,
            String value,
            ConsistencyLevel level
        ) {
            DistributedNode coordinator = node(coordinatorId);

            coordinator.assertActive();

            int required =
                policy.requiredAcknowledgements(level);

            DistributedRecord record = coordinator.write(key, value);

            DistributedOperation operation =
                new DistributedOperation(record, required);

            operations.add(operation);

            operation.begin();

            operation.acknowledge();

            List<DistributedNode> targets = activeNodes().stream()
                .filter(n -> !n.id().equals(coordinatorId))
                .filter(n -> network.connected(coordinatorId, n.id()))
                .limit(policy.replicationFactor() - 1)
                .toList();

            for (DistributedNode target : targets) {
                NetworkMessage message = new NetworkMessage(
                    UUID.randomUUID().toString(),
                    coordinatorId,
                    target.id(),
                    MessageType.REPLICATION,
                    record
                );

                try {
                    target.receive(message);
                    operation.acknowledge();
                } catch (NodeUnavailableException exception) {
                    // A failed target does not count as an acknowledgement.
                }
            }

            operation.complete();

            return operation;
        }

        // ----------------------------------------------------
        // READ SERVICE
        // ----------------------------------------------------

        Optional<DistributedRecord> read(
            String key,
            ConsistencyLevel level
        ) {
            int required =
                policy.requiredAcknowledgements(level);

            List<DistributedRecord> replicas = activeNodes()
                .stream()
                .map(n -> n.read(key))
                .flatMap(Optional::stream)
                .sorted(
                    Comparator.comparing(
                        DistributedRecord::version
                    ).reversed()
                )
                .toList();

            if (replicas.size() < required) {
                throw new QuorumUnavailableException(
                    "Insufficient replicas for read"
                );
            }

            DistributedRecord latest = replicas.get(0);

            if (level != ConsistencyLevel.ONE) {
                repair(latest);
            }

            return Optional.of(latest);
        }

        // ----------------------------------------------------
        // READ REPAIR
        // ----------------------------------------------------

        void repair(DistributedRecord latest) {
            for (DistributedNode node : activeNodes()) {
                if (network.connected(
                    latest.version().nodeId(),
                    node.id()
                )) {
                    node.apply(latest);
                }
            }
        }

        // ----------------------------------------------------
        // ANTI-ENTROPY
        // ----------------------------------------------------

        void antiEntropy() {
            Map<String, DistributedRecord> merged =
                new HashMap<>();

            for (DistributedNode node : activeNodes()) {
                node.snapshot().forEach((key, record) -> {
                    merged.merge(
                        key,
                        record,
                        (existing, incoming) ->
                            existing.version().compareTo(
                                incoming.version()
                            ) >= 0 ? existing : incoming
                    );
                });
            }

            for (DistributedNode target : activeNodes()) {
                for (DistributedRecord record : merged.values()) {
                    if (network.connected(
                        record.version().nodeId(),
                        target.id()
                    )) {
                        target.apply(record);
                    }
                }
            }
        }

        void stopNode(String id) {
            node(id).stop();
        }

        void startNode(String id) {
            node(id).start();
        }

        boolean converged() {
            List<DistributedNode> active = activeNodes();

            if (active.size() < 2) {
                return true;
            }

            Map<String, DistributedRecord> expected =
                active.get(0).snapshot();

            return active.stream()
                .allMatch(n -> n.snapshot().equals(expected));
        }

        void report() {
            System.out.println("\nENTERPRISE CLUSTER REPORT");

            for (DistributedNode node : nodes.values()) {
                System.out.printf(
                    "%-18s status=%-8s records=%d logicalClock=%d%n",
                    node.id(),
                    node.status(),
                    node.recordCount(),
                    node.logicalTime()
                );
            }

            System.out.println(
                "Network partitioned: " + network.isPartitioned()
            );

            System.out.println(
                "Successful operations: " +
                operations.stream()
                    .filter(o -> o.state() == OperationState.COMMITTED)
                    .count()
            );

            System.out.println(
                "Converged: " + converged()
            );
        }
    }

    // ========================================================
    // FAILURE DETECTOR
    // ========================================================

    static final class FailureDetector {

        private final long timeoutMillis;

        private final Map<String, Long> lastHeartbeat =
            new ConcurrentHashMap<>();

        FailureDetector(long timeoutMillis) {
            if (timeoutMillis <= 0) {
                throw new IllegalArgumentException(
                    "Timeout must be positive"
                );
            }

            this.timeoutMillis = timeoutMillis;
        }

        void heartbeat(String nodeId, long timestamp) {
            lastHeartbeat.put(nodeId, timestamp);
        }

        Set<String> suspected(long now) {
            Set<String> result = new HashSet<>();

            lastHeartbeat.forEach((nodeId, timestamp) -> {
                if (now - timestamp > timeoutMillis) {
                    result.add(nodeId);
                }
            });

            return result;
        }
    }

    // ========================================================
    // TESTS
    // ========================================================

    static void runTests() {
        Cluster cluster = new Cluster(
            List.of("node-A", "node-B", "node-C")
        );

        DistributedOperation operation = cluster.write(
            "node-A",
            "account:1001",
            "balance=5000",
            ConsistencyLevel.QUORUM
        );

        assert operation.state() == OperationState.COMMITTED;
        assert operation.acknowledgements() == 3;

        Optional<DistributedRecord> result =
            cluster.read("account:1001", ConsistencyLevel.QUORUM);

        assert result.isPresent();
        assert result.get().value().equals("balance=5000");

        // Network partition prevents quorum.
        cluster.network().partition("node-A", "node-B");
        cluster.network().partition("node-A", "node-C");

        boolean failed = false;

        try {
            cluster.write(
                "node-A",
                "account:1001",
                "balance=6000",
                ConsistencyLevel.QUORUM
            );
        } catch (QuorumUnavailableException exception) {
            failed = true;
        }

        assert failed;

        // Restore and reconcile.
        cluster.network().heal();
        cluster.antiEntropy();

        assert cluster.converged();

        // Node lifecycle.
        cluster.stopNode("node-C");
        cluster.startNode("node-C");

        cluster.antiEntropy();

        assert cluster.converged();

        // Failure detector.
        FailureDetector detector = new FailureDetector(5000);

        detector.heartbeat("node-A", 1000);

        assert detector.suspected(7000).contains("node-A");

        System.out.println("All Java 17 tests passed.");
    }

    // ========================================================
    // MAIN
    // ========================================================

    public static void main(String[] args) {

        try {
            runTests();

            Cluster cluster = new Cluster(
                List.of(
                    "india-primary",
                    "india-secondary",
                    "europe-primary",
                    "us-primary",
                    "us-secondary"
                )
            );

            System.out.println("\n1. Enterprise distributed write");

            DistributedOperation operation = cluster.write(
                "india-primary",
                "payment:7001",
                "amount=25000;status=AUTHORIZED",
                ConsistencyLevel.QUORUM
            );

            System.out.println(
                "Operation: " + operation.operationId()
            );

            System.out.println(
                "State: " + operation.state()
            );

            System.out.println(
                "Acknowledgements: " + operation.acknowledgements()
            );

            System.out.println("\n2. Network partition");

            cluster.network().partition(
                "india-primary",
                "europe-primary"
            );

            cluster.network().partition(
                "india-primary",
                "us-primary"
            );

            try {
                cluster.write(
                    "india-primary",
                    "payment:7001",
                    "amount=25000;status=SETTLED",
                    ConsistencyLevel.QUORUM
                );
            } catch (QuorumUnavailableException exception) {
                System.out.println(
                    "Expected quorum rejection: " +
                    exception.getMessage()
                );
            }

            System.out.println("\n3. Network recovery");

            cluster.network().heal();
            cluster.antiEntropy();

            System.out.println("\n4. Latest payment state");

            cluster.read(
                "payment:7001",
                ConsistencyLevel.QUORUM
            ).ifPresent(System.out::println);

            System.out.println("\n5. Operational reporting");

            cluster.report();

        } catch (DistributedException exception) {
            System.err.println(
                "Distributed operation failed: " +
                exception.getMessage()
            );

            System.exit(1);
        }
    }
}
