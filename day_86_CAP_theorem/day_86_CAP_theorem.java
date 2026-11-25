import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/*
 * CAP Theorem: Enterprise Distributed Storage Governance
 *
 * Java 17.
 * No third-party dependencies.
 *
 * Features:
 * - Typed domain model
 * - CP and AP consistency policies
 * - Replica management
 * - Quorum validation
 * - Partition simulation
 * - Versioned records
 * - Conflict resolution
 * - Operation audit
 * - Explicit failure states
 * - Enterprise-oriented service architecture
 */

public class Main {

    enum CAPMode {
        CP,
        AP
    }

    enum OperationStatus {
        SUCCESS,
        REJECTED,
        UNAVAILABLE
    }

    enum PartitionState {
        CONNECTED,
        PARTITIONED
    }

    record Version(long logicalTime, String writerId)
            implements Comparable<Version> {

        Version {
            if (logicalTime < 0) {
                throw new IllegalArgumentException(
                    "Logical time cannot be negative."
                );
            }

            Objects.requireNonNull(writerId);

            if (writerId.isBlank()) {
                throw new IllegalArgumentException(
                    "Writer ID cannot be empty."
                );
            }
        }

        @Override
        public int compareTo(Version other) {
            int result = Long.compare(
                logicalTime,
                other.logicalTime
            );

            if (result != 0) {
                return result;
            }

            return writerId.compareTo(other.writerId);
        }
    }

    record DataRecord(
        String key,
        String value,
        Version version,
        Instant updatedAt
    ) {
        DataRecord {
            if (key == null || key.isBlank() || key.length() > 255) {
                throw new IllegalArgumentException("Invalid record key.");
            }

            if (value == null || value.length() > 10000) {
                throw new IllegalArgumentException("Invalid record value.");
            }

            Objects.requireNonNull(version);
            Objects.requireNonNull(updatedAt);
        }
    }

    record OperationResult(
        OperationStatus status,
        String message,
        Optional<String> value
    ) {
        OperationResult {
            Objects.requireNonNull(status);
            Objects.requireNonNull(message);
            Objects.requireNonNull(value);
        }
    }

    record AuditEvent(
        Instant timestamp,
        String operation,
        String replicaId,
        String key,
        String outcome
    ) {}

    interface ConsistencyPolicy {
        boolean canWrite(int connectedReplicas, int quorum);

        boolean canRead(int connectedReplicas, int quorum);

        String description();
    }

    static final class CPPolicy implements ConsistencyPolicy {

        @Override
        public boolean canWrite(int connectedReplicas, int quorum) {
            return connectedReplicas >= quorum;
        }

        @Override
        public boolean canRead(int connectedReplicas, int quorum) {
            return connectedReplicas >= quorum;
        }

        @Override
        public String description() {
            return "Consistency with quorum and partition tolerance";
        }
    }

    static final class APPolicy implements ConsistencyPolicy {

        @Override
        public boolean canWrite(int connectedReplicas, int quorum) {
            return connectedReplicas >= 1;
        }

        @Override
        public boolean canRead(int connectedReplicas, int quorum) {
            return connectedReplicas >= 1;
        }

        @Override
        public String description() {
            return "Local availability with eventual reconciliation";
        }
    }

    static final class Replica {
        private final String id;
        private final Map<String, DataRecord> records =
            new HashMap<>();

        private boolean available = true;
        private int partitionId = 0;

        Replica(String id) {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException(
                    "Replica ID is required."
                );
            }

            this.id = id;
        }

        String id() {
            return id;
        }

        boolean available() {
            return available;
        }

        void setAvailable(boolean available) {
            this.available = available;
        }

        int partitionId() {
            return partitionId;
        }

        void setPartitionId(int partitionId) {
            this.partitionId = partitionId;
        }

        Map<String, DataRecord> records() {
            return Map.copyOf(records);
        }

        Optional<DataRecord> read(String key) {
            ensureAvailable();
            return Optional.ofNullable(records.get(key));
        }

        void apply(DataRecord record) {
            ensureAvailable();

            DataRecord existing = records.get(record.key());

            if (existing == null ||
                record.version().compareTo(existing.version()) > 0) {
                records.put(record.key(), record);
            }
        }

        private void ensureAvailable() {
            if (!available) {
                throw new IllegalStateException(
                    "Replica is unavailable: " + id
                );
            }
        }
    }

    static final class DistributedCluster {

        private final CAPMode mode;
        private final ConsistencyPolicy policy;
        private final Map<String, Replica> replicas =
            new TreeMap<>();
        private final List<AuditEvent> auditLog =
            new ArrayList<>();

        private final AtomicLong logicalClock =
            new AtomicLong(0);

        DistributedCluster(CAPMode mode, int nodeCount) {
            Objects.requireNonNull(mode);

            if (nodeCount < 1 || nodeCount > 100) {
                throw new IllegalArgumentException(
                    "Node count must be between 1 and 100."
                );
            }

            this.mode = mode;
            this.policy = mode == CAPMode.CP
                ? new CPPolicy()
                : new APPolicy();

            for (int i = 1; i <= nodeCount; i++) {
                String id = "node-" + i;
                replicas.put(id, new Replica(id));
            }
        }

        int quorum() {
            return replicas.size() / 2 + 1;
        }

        Replica getReplica(String id) {
            Replica replica = replicas.get(id);

            if (replica == null) {
                throw new IllegalArgumentException(
                    "Unknown replica: " + id
                );
            }

            return replica;
        }

        List<Replica> connectedReplicas(String id) {
            Replica requester = getReplica(id);

            if (!requester.available()) {
                return List.of();
            }

            return replicas.values().stream()
                .filter(Replica::available)
                .filter(replica ->
                    replica.partitionId() == requester.partitionId()
                )
                .collect(Collectors.toList());
        }

        void partition(List<List<String>> groups) {
            if (groups == null || groups.isEmpty()) {
                throw new IllegalArgumentException(
                    "Partition groups are required."
                );
            }

            Set<String> assigned = new HashSet<>();

            for (int i = 0; i < groups.size(); i++) {
                List<String> group = groups.get(i);

                if (group == null || group.isEmpty()) {
                    throw new IllegalArgumentException(
                        "Partition groups cannot be empty."
                    );
                }

                for (String id : group) {
                    Replica replica = getReplica(id);

                    if (!assigned.add(id)) {
                        throw new IllegalArgumentException(
                            "Duplicate replica: " + id
                        );
                    }

                    replica.setPartitionId(i);
                }
            }

            int nextGroup = groups.size();

            for (Replica replica : replicas.values()) {
                if (!assigned.contains(replica.id())) {
                    replica.setPartitionId(nextGroup++);
                }
            }

            audit(
                "PARTITION",
                "cluster",
                null,
                "NETWORK_PARTITION_CREATED"
            );
        }

        void setAvailability(String id, boolean available) {
            getReplica(id).setAvailable(available);

            audit(
                "AVAILABILITY",
                id,
                null,
                Boolean.toString(available)
            );
        }

        OperationResult write(
            String nodeId,
            String key,
            String value
        ) {
            if (key == null || key.isBlank() || key.length() > 255) {
                throw new IllegalArgumentException("Invalid key.");
            }

            if (value == null || value.length() > 10000) {
                throw new IllegalArgumentException("Invalid value.");
            }

            List<Replica> connected =
                connectedReplicas(nodeId);

            if (!policy.canWrite(connected.size(), quorum())) {
                audit(
                    "WRITE",
                    nodeId,
                    key,
                    "REJECTED"
                );

                return new OperationResult(
                    connected.isEmpty()
                        ? OperationStatus.UNAVAILABLE
                        : OperationStatus.REJECTED,
                    "Required write conditions are unavailable.",
                    Optional.empty()
                );
            }

            DataRecord record = new DataRecord(
                key,
                value,
                new Version(
                    logicalClock.incrementAndGet(),
                    nodeId
                ),
                Instant.now()
            );

            if (mode == CAPMode.CP) {
                connected.forEach(
                    replica -> replica.apply(record)
                );
            } else {
                getReplica(nodeId).apply(record);
            }

            audit("WRITE", nodeId, key, "SUCCESS");

            return new OperationResult(
                OperationStatus.SUCCESS,
                "Write acknowledged.",
                Optional.of(value)
            );
        }

        OperationResult read(String nodeId, String key) {
            if (key == null || key.isBlank()) {
                throw new IllegalArgumentException("Invalid key.");
            }

            List<Replica> connected =
                connectedReplicas(nodeId);

            if (!policy.canRead(connected.size(), quorum())) {
                return new OperationResult(
                    connected.isEmpty()
                        ? OperationStatus.UNAVAILABLE
                        : OperationStatus.REJECTED,
                    "Read requirements are unavailable.",
                    Optional.empty()
                );
            }

            if (mode == CAPMode.AP) {
                Optional<DataRecord> record =
                    getReplica(nodeId).read(key);

                return new OperationResult(
                    OperationStatus.SUCCESS,
                    "Local replica read.",
                    record.map(DataRecord::value)
                );
            }

            Optional<DataRecord> latest = connected.stream()
                .map(replica -> replica.read(key))
                .flatMap(Optional::stream)
                .max(Comparator.comparing(DataRecord::version));

            return new OperationResult(
                OperationStatus.SUCCESS,
                "Quorum read completed.",
                latest.map(DataRecord::value)
            );
        }

        void healPartition() {
            replicas.values().forEach(
                replica -> replica.setPartitionId(0)
            );

            Map<String, DataRecord> merged = new HashMap<>();

            for (Replica replica : replicas.values()) {
                if (!replica.available()) {
                    continue;
                }

                for (DataRecord record : replica.records().values()) {
                    merged.merge(
                        record.key(),
                        record,
                        (first, second) ->
                            first.version().compareTo(second.version()) >= 0
                                ? first
                                : second
                    );
                }
            }

            for (Replica replica : replicas.values()) {
                if (!replica.available()) {
                    continue;
                }

                merged.values().forEach(replica::apply);
            }

            audit(
                "RECONCILIATION",
                "cluster",
                null,
                "COMPLETED"
            );
        }

        boolean isConsistent() {
            List<Map<String, String>> snapshots =
                replicas.values().stream()
                    .filter(Replica::available)
                    .map(replica ->
                        replica.records().entrySet().stream()
                            .collect(Collectors.toMap(
                                Map.Entry::getKey,
                                entry -> entry.getValue().value()
                            ))
                    )
                    .toList();

            return snapshots.stream().distinct().count() <= 1;
        }

        void printReport() {
            System.out.println("\nMode: " + mode);
            System.out.println("Policy: " + policy.description());
            System.out.println("Quorum: " + quorum());

            replicas.values().forEach(replica -> {
                System.out.println(
                    replica.id()
                    + " | available=" + replica.available()
                    + " | partition=" + replica.partitionId()
                    + " | records=" + replica.records()
                );
            });

            System.out.println(
                "Consistent: " + isConsistent()
            );

            System.out.println(
                "Audit events: " + auditLog.size()
            );
        }

        private void audit(
            String operation,
            String replicaId,
            String key,
            String outcome
        ) {
            auditLog.add(new AuditEvent(
                Instant.now(),
                operation,
                replicaId,
                key,
                outcome
            ));
        }
    }

    private static void demonstrateCP() {
        System.out.println("\n========== ENTERPRISE CP ==========");

        DistributedCluster cluster =
            new DistributedCluster(CAPMode.CP, 3);

        cluster.write("node-1", "account-501", "5000");

        cluster.partition(List.of(
            List.of("node-1"),
            List.of("node-2", "node-3")
        ));

        OperationResult minority =
            cluster.write("node-1", "account-501", "6000");

        OperationResult majority =
            cluster.write("node-2", "account-501", "5500");

        System.out.println("Minority: " + minority.status());
        System.out.println("Majority: " + majority.status());

        cluster.healPartition();
        cluster.printReport();
    }

    private static void demonstrateAP() {
        System.out.println("\n========== ENTERPRISE AP ==========");

        DistributedCluster cluster =
            new DistributedCluster(CAPMode.AP, 3);

        cluster.write("node-1", "inventory-101", "100");

        cluster.partition(List.of(
            List.of("node-1"),
            List.of("node-2", "node-3")
        ));

        cluster.write("node-1", "inventory-101", "80");
        cluster.write("node-2", "inventory-101", "90");

        System.out.println("Before reconciliation:");
        cluster.printReport();

        cluster.healPartition();

        System.out.println("After reconciliation:");
        cluster.printReport();
    }

    private static void runTests() {
        DistributedCluster cp =
            new DistributedCluster(CAPMode.CP, 3);

        cp.partition(List.of(
            List.of("node-1"),
            List.of("node-2", "node-3")
        ));

        assert cp.write("node-1", "k", "A").status()
            == OperationStatus.REJECTED;

        assert cp.write("node-2", "k", "B").status()
            == OperationStatus.SUCCESS;

        cp.healPartition();

        assert cp.isConsistent();

        DistributedCluster ap =
            new DistributedCluster(CAPMode.AP, 3);

        ap.partition(List.of(
            List.of("node-1"),
            List.of("node-2", "node-3")
        ));

        assert ap.write("node-1", "k", "A").status()
            == OperationStatus.SUCCESS;

        assert ap.write("node-2", "k", "B").status()
            == OperationStatus.SUCCESS;

        ap.healPartition();

        assert ap.isConsistent();

        ap.setAvailability("node-1", false);

        assert ap.read("node-1", "k").status()
            == OperationStatus.UNAVAILABLE;

        try {
            new DistributedCluster(CAPMode.CP, 0);
            throw new AssertionError("Invalid cluster accepted.");
        } catch (IllegalArgumentException expected) {
            // Configuration validation succeeded.
        }

        System.out.println("\nAll Java assertions passed.");
    }

    public static void main(String[] args) {
        demonstrateCP();
        demonstrateAP();
        runTests();
    }
}
