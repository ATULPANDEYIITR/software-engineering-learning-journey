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
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

/*
 * Distributed System Challenges
 *
 * Enterprise-oriented distributed key-value service:
 * - Versioned records
 * - Asynchronous replication
 * - Quorum policies
 * - Network latency and timeouts
 * - Failure detection
 * - Idempotent operations
 * - Read repair
 * - Replica recovery
 * - Operational metrics
 */

public class DistributedSystemsDemo {

    enum NodeStatus {
        HEALTHY,
        UNAVAILABLE,
        PARTITIONED
    }

    enum ConsistencyLevel {
        ONE,
        QUORUM,
        ALL
    }

    enum OperationStatus {
        PENDING,
        COMMITTED,
        FAILED
    }

    record VersionedRecord(
        String key,
        String value,
        long version,
        long timestamp,
        String operationId
    ) {
        VersionedRecord {
            if (key == null || key.isBlank()) {
                throw new IllegalArgumentException("Invalid key");
            }

            Objects.requireNonNull(value);
            Objects.requireNonNull(operationId);
        }
    }

    record WriteResult(
        String operationId,
        OperationStatus status,
        int acknowledgements,
        int requiredAcknowledgements
    ) {}

    record NetworkResult(
        String nodeId,
        long latencyMillis
    ) {}

    static class DistributedException extends RuntimeException {
        DistributedException(String message) {
            super(message);
        }
    }

    static class QuorumException extends DistributedException {
        QuorumException(String message) {
            super(message);
        }
    }

    static class NetworkException extends DistributedException {
        NetworkException(String message) {
            super(message);
        }
    }

    static class Replica {

        private final String nodeId;

        private NodeStatus status = NodeStatus.HEALTHY;

        private final Map<String, VersionedRecord> storage =
            new HashMap<>();

        private final Set<String> appliedOperations =
            new HashSet<>();

        Replica(String nodeId) {
            this.nodeId = nodeId;
        }

        String getNodeId() {
            return nodeId;
        }

        synchronized void setStatus(NodeStatus status) {
            this.status = Objects.requireNonNull(status);
        }

        synchronized boolean isAvailable() {
            return status == NodeStatus.HEALTHY;
        }

        synchronized void apply(VersionedRecord record) {
            if (!isAvailable()) {
                throw new NetworkException(
                    nodeId + " is unavailable"
                );
            }

            if (appliedOperations.contains(record.operationId())) {
                return;
            }

            VersionedRecord current = storage.get(record.key());

            if (
                current == null ||
                compare(record, current) > 0
            ) {
                storage.put(record.key(), record);
            }

            appliedOperations.add(record.operationId());
        }

        synchronized Optional<VersionedRecord> read(String key) {
            if (!isAvailable()) {
                throw new NetworkException(
                    nodeId + " is unavailable"
                );
            }

            return Optional.ofNullable(storage.get(key));
        }

        synchronized int size() {
            return storage.size();
        }

        private static int compare(
            VersionedRecord first,
            VersionedRecord second
        ) {
            int versionComparison = Long.compare(
                first.version(),
                second.version()
            );

            if (versionComparison != 0) {
                return versionComparison;
            }

            int timestampComparison = Long.compare(
                first.timestamp(),
                second.timestamp()
            );

            if (timestampComparison != 0) {
                return timestampComparison;
            }

            return first.operationId().compareTo(
                second.operationId()
            );
        }
    }

    interface NetworkTransport {
        CompletableFuture<NetworkResult> transmit(
            String source,
            Replica destination
        );
    }

    static class SimulatedNetwork implements NetworkTransport {

        private final long minimumLatency;
        private final long maximumLatency;
        private final long timeout;

        private final Set<String> blockedLinks =
            new HashSet<>();

        SimulatedNetwork(
            long minimumLatency,
            long maximumLatency,
            long timeout
        ) {
            if (
                minimumLatency < 0 ||
                maximumLatency < minimumLatency ||
                timeout <= 0
            ) {
                throw new IllegalArgumentException(
                    "Invalid network parameters"
                );
            }

            this.minimumLatency = minimumLatency;
            this.maximumLatency = maximumLatency;
            this.timeout = timeout;
        }

        synchronized void partition(
            String source,
            String destination
        ) {
            blockedLinks.add(source + "->" + destination);
            blockedLinks.add(destination + "->" + source);
        }

        synchronized void heal(
            String source,
            String destination
        ) {
            blockedLinks.remove(source + "->" + destination);
            blockedLinks.remove(destination + "->" + source);
        }

        @Override
        public CompletableFuture<NetworkResult> transmit(
            String source,
            Replica destination
        ) {
            synchronized (this) {
                if (
                    blockedLinks.contains(
                        source + "->" + destination.getNodeId()
                    )
                ) {
                    return CompletableFuture.failedFuture(
                        new NetworkException("Network partition")
                    );
                }
            }

            if (!destination.isAvailable()) {
                return CompletableFuture.failedFuture(
                    new NetworkException("Replica unavailable")
                );
            }

            long latency = minimumLatency +
                (long) (
                    Math.random() *
                    (maximumLatency - minimumLatency + 1)
                );

            if (latency > timeout) {
                return CompletableFuture.failedFuture(
                    new NetworkException("Network timeout")
                );
            }

            return CompletableFuture.supplyAsync(() -> {
                try {
                    TimeUnit.MILLISECONDS.sleep(latency);
                } catch (InterruptedException exception) {
                    Thread.currentThread().interrupt();
                    throw new CompletionException(exception);
                }

                return new NetworkResult(
                    destination.getNodeId(),
                    latency
                );
            });
        }
    }

    static class RepositoryPolicy {

        private final int replicationFactor;
        private final Map<ConsistencyLevel, Integer> requirements;

        RepositoryPolicy(int replicationFactor) {
            if (replicationFactor < 1) {
                throw new IllegalArgumentException(
                    "Invalid replication factor"
                );
            }

            this.replicationFactor = replicationFactor;

            int quorum = replicationFactor / 2 + 1;

            Map<ConsistencyLevel, Integer> configured =
                new HashMap<>();

            configured.put(ConsistencyLevel.ONE, 1);
            configured.put(ConsistencyLevel.QUORUM, quorum);
            configured.put(
                ConsistencyLevel.ALL,
                replicationFactor
            );

            this.requirements = Map.copyOf(configured);
        }

        int required(ConsistencyLevel level) {
            Integer required = requirements.get(level);

            if (required == null) {
                throw new IllegalArgumentException(
                    "Unsupported consistency level"
                );
            }

            return required;
        }

        int replicationFactor() {
            return replicationFactor;
        }
    }

    static class DistributedMetrics {

        private final AtomicLong successfulWrites =
            new AtomicLong();

        private final AtomicLong failedWrites =
            new AtomicLong();

        private final AtomicLong successfulReads =
            new AtomicLong();

        private final AtomicLong networkFailures =
            new AtomicLong();

        private final List<Long> latencies =
            new ArrayList<>();

        synchronized void recordLatency(long latency) {
            latencies.add(latency);
        }

        void writeSucceeded() {
            successfulWrites.incrementAndGet();
        }

        void writeFailed() {
            failedWrites.incrementAndGet();
        }

        void readSucceeded() {
            successfulReads.incrementAndGet();
        }

        void networkFailed() {
            networkFailures.incrementAndGet();
        }

        synchronized void report() {
            List<Long> sorted = latencies.stream()
                .sorted()
                .collect(Collectors.toList());

            double average = sorted.isEmpty()
                ? 0
                : sorted.stream()
                    .mapToLong(Long::longValue)
                    .average()
                    .orElse(0);

            long p95 = sorted.isEmpty()
                ? 0
                : sorted.get(
                    Math.min(
                        sorted.size() - 1,
                        (int) Math.ceil(sorted.size() * 0.95) - 1
                    )
                );

            System.out.println("\nSYSTEM METRICS");
            System.out.println("------------------------------");
            System.out.println(
                "Successful writes: " + successfulWrites.get()
            );
            System.out.println(
                "Failed writes: " + failedWrites.get()
            );
            System.out.println(
                "Successful reads: " + successfulReads.get()
            );
            System.out.println(
                "Network failures: " + networkFailures.get()
            );
            System.out.printf("Average latency: %.2f ms%n", average);
            System.out.println("P95 latency: " + p95 + " ms");
        }
    }

    static class DistributedStore {

        private final List<Replica> replicas;

        private final RepositoryPolicy policy;

        private final NetworkTransport network;

        private final DistributedMetrics metrics =
            new DistributedMetrics();

        private final AtomicLong logicalClock =
            new AtomicLong();

        private final Map<String, WriteResult> operationLedger =
            new HashMap<>();

        private final String coordinator = "coordinator";

        DistributedStore(
            int nodeCount,
            int replicationFactor,
            NetworkTransport network
        ) {
            if (
                nodeCount < 1 ||
                replicationFactor < 1 ||
                replicationFactor > nodeCount
            ) {
                throw new IllegalArgumentException(
                    "Invalid cluster configuration"
                );
            }

            this.policy = new RepositoryPolicy(
                replicationFactor
            );

            this.network = Objects.requireNonNull(network);

            this.replicas = new ArrayList<>();

            for (int i = 1; i <= nodeCount; i++) {
                replicas.add(new Replica("node-" + i));
            }
        }

        private List<Replica> selectReplicas(String key) {
            int start = Math.floorMod(
                key.hashCode(),
                replicas.size()
            );

            List<Replica> selected = new ArrayList<>();

            for (
                int i = 0;
                i < policy.replicationFactor();
                i++
            ) {
                selected.add(
                    replicas.get((start + i) % replicas.size())
                );
            }

            return selected;
        }

        WriteResult write(
            String key,
            String value,
            ConsistencyLevel consistency,
            String operationId
        ) {
            if (
                key == null ||
                key.isBlank() ||
                key.length() > 256 ||
                value == null ||
                value.length() > 10000
            ) {
                throw new IllegalArgumentException(
                    "Invalid write request"
                );
            }

            if (
                operationId == null ||
                operationId.isBlank()
            ) {
                throw new IllegalArgumentException(
                    "Operation ID is required"
                );
            }

            synchronized (operationLedger) {
                WriteResult previous = operationLedger.get(
                    operationId
                );

                if (previous != null) {
                    return previous;
                }
            }

            long startTime = System.nanoTime();

            int required = policy.required(consistency);

            VersionedRecord record = new VersionedRecord(
                key,
                value,
                logicalClock.incrementAndGet(),
                Instant.now().toEpochMilli(),
                operationId
            );

            List<CompletableFuture<Boolean>> requests =
                selectReplicas(key).stream()
                    .map(replica ->
                        network.transmit(coordinator, replica)
                            .thenApply(result -> {
                                replica.apply(record);
                                return true;
                            })
                            .exceptionally(error -> {
                                metrics.networkFailed();
                                return false;
                            })
                    )
                    .toList();

            int acknowledgements = (int) requests.stream()
                .map(CompletableFuture::join)
                .filter(Boolean::booleanValue)
                .count();

            WriteResult result;

            if (acknowledgements >= required) {
                result = new WriteResult(
                    operationId,
                    OperationStatus.COMMITTED,
                    acknowledgements,
                    required
                );

                metrics.writeSucceeded();

            } else {
                result = new WriteResult(
                    operationId,
                    OperationStatus.FAILED,
                    acknowledgements,
                    required
                );

                metrics.writeFailed();
            }

            synchronized (operationLedger) {
                operationLedger.put(operationId, result);
            }

            metrics.recordLatency(
                TimeUnit.NANOSECONDS.toMillis(
                    System.nanoTime() - startTime
                )
            );

            if (result.status() == OperationStatus.FAILED) {
                throw new QuorumException(
                    "Write failed: received " +
                    acknowledgements + "/" + required +
                    " acknowledgements"
                );
            }

            return result;
        }

        Optional<VersionedRecord> read(
            String key,
            ConsistencyLevel consistency,
            boolean readRepair
        ) {
            if (key == null || key.isBlank()) {
                throw new IllegalArgumentException(
                    "Invalid read key"
                );
            }

            long startTime = System.nanoTime();

            List<CompletableFuture<Optional<VersionedRecord>>>
                requests = selectReplicas(key).stream()
                    .map(replica ->
                        network.transmit(coordinator, replica)
                            .thenApply(result -> replica.read(key))
                            .exceptionally(error -> {
                                metrics.networkFailed();
                                return Optional.empty();
                            })
                    )
                    .toList();

            List<Optional<VersionedRecord>> responses =
                requests.stream()
                    .map(CompletableFuture::join)
                    .collect(Collectors.toList());

            int required = policy.required(consistency);

            long successfulResponses = responses.stream()
                .filter(Optional::isPresent)
                .count();

            // A missing key is a valid response. The service must
            // count successful network responses separately from values.
            // Recheck network reachability rather than treating null
            // records as failed messages.
            List<Replica> selected = selectReplicas(key);

            int availableResponses = (int) selected.stream()
                .filter(Replica::isAvailable)
                .count();

            if (availableResponses < required) {
                throw new QuorumException(
                    "Insufficient read responses"
                );
            }

            Optional<VersionedRecord> latest = responses.stream()
                .flatMap(Optional::stream)
                .max(Comparator
                    .comparingLong(VersionedRecord::version)
                    .thenComparingLong(VersionedRecord::timestamp)
                    .thenComparing(VersionedRecord::operationId));

            if (readRepair && latest.isPresent()) {
                for (Replica replica : selected) {
                    if (!replica.isAvailable()) {
                        continue;
                    }

                    Optional<VersionedRecord> current =
                        replica.read(key);

                    if (
                        current.isEmpty() ||
                        compare(
                            latest.get(),
                            current.get()
                        ) > 0
                    ) {
                        replica.apply(latest.get());
                    }
                }
            }

            metrics.readSucceeded();

            metrics.recordLatency(
                TimeUnit.NANOSECONDS.toMillis(
                    System.nanoTime() - startTime
                )
            );

            return latest;
        }

        private int compare(
            VersionedRecord first,
            VersionedRecord second
        ) {
            int version = Long.compare(
                first.version(),
                second.version()
            );

            if (version != 0) {
                return version;
            }

            int timestamp = Long.compare(
                first.timestamp(),
                second.timestamp()
            );

            if (timestamp != 0) {
                return timestamp;
            }

            return first.operationId().compareTo(
                second.operationId()
            );
        }

        int synchronize(String key) {
            List<Replica> selected = selectReplicas(key);

            Optional<VersionedRecord> latest = selected.stream()
                .filter(Replica::isAvailable)
                .map(replica -> replica.read(key))
                .flatMap(Optional::stream)
                .max(Comparator
                    .comparingLong(VersionedRecord::version)
                    .thenComparingLong(VersionedRecord::timestamp)
                    .thenComparing(VersionedRecord::operationId));

            if (latest.isEmpty()) {
                return 0;
            }

            int repaired = 0;

            for (Replica replica : selected) {
                if (!replica.isAvailable()) {
                    continue;
                }

                Optional<VersionedRecord> current =
                    replica.read(key);

                if (
                    current.isEmpty() ||
                    compare(latest.get(), current.get()) > 0
                ) {
                    replica.apply(latest.get());
                    repaired++;
                }
            }

            return repaired;
        }

        void setNodeStatus(
            String nodeId,
            NodeStatus status
        ) {
            replicas.stream()
                .filter(replica ->
                    replica.getNodeId().equals(nodeId)
                )
                .findFirst()
                .orElseThrow(() ->
                    new IllegalArgumentException("Unknown node")
                )
                .setStatus(status);
        }

        void report() {
            metrics.report();

            System.out.println("\nREPLICA STORAGE");

            for (Replica replica : replicas) {
                System.out.println(
                    replica.getNodeId() +
                    ": " + replica.size() + " records"
                );
            }
        }
    }

    public static void main(String[] args) {
        SimulatedNetwork network = new SimulatedNetwork(
            5,
            25,
            100
        );

        DistributedStore store = new DistributedStore(
            5,
            3,
            network
        );

        try {
            System.out.println("DISTRIBUTED SYSTEM CHALLENGES");

            System.out.println("\n1. QUORUM WRITE");

            WriteResult result = store.write(
                "inventory:product-100",
                "quantity:250",
                ConsistencyLevel.QUORUM,
                "inventory-update-001"
            );

            System.out.println(result);

            System.out.println("\n2. IDEMPOTENT OPERATION");

            System.out.println(
                store.write(
                    "inventory:product-100",
                    "quantity:250",
                    ConsistencyLevel.QUORUM,
                    "inventory-update-001"
                )
            );

            System.out.println("\n3. QUORUM READ");

            System.out.println(
                store.read(
                    "inventory:product-100",
                    ConsistencyLevel.QUORUM,
                    true
                )
            );

            System.out.println("\n4. NODE FAILURE");

            store.setNodeStatus(
                "node-1",
                NodeStatus.UNAVAILABLE
            );

            System.out.println(
                store.write(
                    "inventory:product-200",
                    "quantity:100",
                    ConsistencyLevel.QUORUM,
                    "inventory-update-002"
                )
            );

            System.out.println("\n5. NETWORK PARTITION");

            network.partition("coordinator", "node-2");

            try {
                store.write(
                    "inventory:product-300",
                    "quantity:50",
                    ConsistencyLevel.ALL,
                    "inventory-update-003"
                );
            } catch (QuorumException exception) {
                System.out.println(
                    "Expected failure: " + exception.getMessage()
                );
            }

            System.out.println("\n6. PARTITION RECOVERY");

            network.heal("coordinator", "node-2");

            store.setNodeStatus(
                "node-1",
                NodeStatus.HEALTHY
            );

            System.out.println(
                "Repairs: " +
                store.synchronize("inventory:product-100")
            );

            System.out.println("\n7. OPERATIONAL REPORT");

            store.report();

        } catch (DistributedException exception) {
            System.err.println(
                "Distributed operation failed: " +
                exception.getMessage()
            );

            System.exitCode = 1;

        } catch (IllegalArgumentException exception) {
            System.err.println(
                "Validation error: " +
                exception.getMessage()
            );

            System.exitCode = 1;
        }
    }
}
