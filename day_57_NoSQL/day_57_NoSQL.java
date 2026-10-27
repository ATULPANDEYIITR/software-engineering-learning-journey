import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Queue;
import java.util.Set;

public class NoSqlEnterpriseModel {

    enum NoSqlModel {
        DOCUMENT,
        KEY_VALUE,
        COLUMN_FAMILY,
        GRAPH
    }

    enum ReviewState {
        NEW,
        ACTIVE,
        BLOCKED,
        COMPLETE
    }

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    static class NotFoundException extends RuntimeException {
        NotFoundException(String message) {
            super(message);
        }
    }

    record DocumentRecord(
            String id,
            Map<String, Object> fields,
            int version,
            Instant updatedAt) {

        DocumentRecord {
            Objects.requireNonNull(id, "Document ID is required.");
            fields = Map.copyOf(fields);
        }

        DocumentRecord updated(Map<String, Object> changes) {
            Map<String, Object> next = new HashMap<>(fields);
            next.putAll(changes);
            return new DocumentRecord(
                    id,
                    next,
                    version + 1,
                    Instant.now()
            );
        }
    }

    static final class DocumentRepository {
        private final Map<String, DocumentRecord> documents = new HashMap<>();

        void create(String id, Map<String, Object> fields) {
            validateId(id);
            if (fields == null || fields.isEmpty()) {
                throw new ValidationException("Document fields are required.");
            }
            if (documents.containsKey(id)) {
                throw new ValidationException("Document already exists.");
            }

            documents.put(
                    id,
                    new DocumentRecord(id, fields, 1, Instant.now())
            );
        }

        void update(String id, Map<String, Object> changes) {
            DocumentRecord record = find(id);
            if (changes == null || changes.isEmpty()) {
                throw new ValidationException("Update cannot be empty.");
            }
            documents.put(id, record.updated(changes));
        }

        DocumentRecord find(String id) {
            DocumentRecord record = documents.get(id);
            if (record == null) {
                throw new NotFoundException("Document does not exist: " + id);
            }
            return record;
        }

        List<DocumentRecord> findByField(String field, Object expected) {
            return documents.values()
                    .stream()
                    .filter(record -> Objects.equals(record.fields().get(field), expected))
                    .toList();
        }
    }

    static final class KeyValueRepository {
        private record Entry(Object value, Instant expiresAt) {}

        private final Map<String, Entry> values = new HashMap<>();

        void put(String key, Object value, Duration ttl) {
            validateKey(key);

            if (ttl != null && ttl.isZero()) {
                throw new ValidationException("TTL must be positive.");
            }

            Instant expiry = ttl == null ? null : Instant.now().plus(ttl);
            values.put(key, new Entry(value, expiry));
        }

        Optional<Object> get(String key) {
            validateKey(key);

            Entry entry = values.get(key);
            if (entry == null) {
                return Optional.empty();
            }

            if (entry.expiresAt() != null &&
                    !Instant.now().isBefore(entry.expiresAt())) {
                values.remove(key);
                return Optional.empty();
            }

            return Optional.ofNullable(entry.value());
        }

        boolean compareAndSet(
                String key,
                Object expected,
                Object replacement) {

            Object current = get(key).orElse(null);

            if (!Objects.equals(current, expected)) {
                return false;
            }

            put(key, replacement, null);
            return true;
        }
    }

    static final class ColumnFamilyRepository {
        private final Map<String, Map<String, Object>> rows = new HashMap<>();

        void put(String rowKey, Map<String, Object> columns) {
            validateKey(rowKey);

            if (columns == null || columns.isEmpty()) {
                throw new ValidationException("At least one column is required.");
            }

            rows.computeIfAbsent(rowKey, ignored -> new HashMap<>())
                    .putAll(columns);
        }

        Map<String, Object> read(String rowKey, Set<String> requestedColumns) {
            Map<String, Object> row = rows.get(rowKey);
            if (row == null) {
                throw new NotFoundException("Column-family row does not exist.");
            }

            if (requestedColumns == null || requestedColumns.isEmpty()) {
                return Map.copyOf(row);
            }

            Map<String, Object> selected = new HashMap<>();
            for (String column : requestedColumns) {
                if (row.containsKey(column)) {
                    selected.put(column, row.get(column));
                }
            }
            return Map.copyOf(selected);
        }

        List<String> findByColumn(String column, Object expected) {
            return rows.entrySet()
                    .stream()
                    .filter(entry -> Objects.equals(
                            entry.getValue().get(column),
                            expected))
                    .map(Map.Entry::getKey)
                    .sorted()
                    .toList();
        }
    }

    enum Relationship {
        OWNS,
        CONTAINS,
        USES,
        DEPENDS_ON
    }

    record Node(String id, Set<String> labels) {
        Node {
            labels = Set.copyOf(labels);
        }
    }

    record Edge(String target, Relationship relationship) {}

    static final class GraphRepository {
        private final Map<String, Node> nodes = new HashMap<>();
        private final Map<String, List<Edge>> adjacency = new HashMap<>();

        void addNode(String id, Set<String> labels) {
            validateKey(id);

            if (nodes.containsKey(id)) {
                throw new ValidationException("Node already exists.");
            }

            nodes.put(id, new Node(id, labels));
            adjacency.put(id, new ArrayList<>());
        }

        void addRelationship(
                String source,
                String target,
                Relationship relationship) {

            requireNode(source);
            requireNode(target);

            adjacency.get(source)
                    .add(new Edge(target, relationship));
        }

        List<String> shortestPath(String start, String target) {
            requireNode(start);
            requireNode(target);

            Queue<String> queue = new ArrayDeque<>();
            Map<String, String> previous = new HashMap<>();
            Set<String> visited = new HashSet<>();

            queue.add(start);
            visited.add(start);

            while (!queue.isEmpty()) {
                String current = queue.remove();

                if (current.equals(target)) {
                    List<String> path = new ArrayList<>();
                    String cursor = current;

                    while (cursor != null) {
                        path.add(cursor);
                        cursor = previous.get(cursor);
                    }

                    Collections.reverse(path);
                    return path;
                }

                for (Edge edge : adjacency.getOrDefault(
                        current, List.of())) {

                    if (visited.add(edge.target())) {
                        previous.put(edge.target(), current);
                        queue.add(edge.target());
                    }
                }
            }

            return List.of();
        }

        private void requireNode(String id) {
            if (!nodes.containsKey(id)) {
                throw new NotFoundException("Unknown graph node: " + id);
            }
        }
    }

    interface EligibilityPolicy {
        boolean accepts(Map<String, Object> attributes);
    }

    record ActiveDevicePolicy() implements EligibilityPolicy {
        @Override
        public boolean accepts(Map<String, Object> attributes) {
            return Boolean.TRUE.equals(attributes.get("active"));
        }
    }

    static final class DeviceService {
        private final DocumentRepository documents;
        private final EligibilityPolicy policy;

        DeviceService(
                DocumentRepository documents,
                EligibilityPolicy policy) {
            this.documents = documents;
            this.policy = policy;
        }

        ReviewState evaluate(String deviceId) {
            DocumentRecord record = documents.find(deviceId);

            if (!policy.accepts(record.fields())) {
                return ReviewState.BLOCKED;
            }

            Object signal = record.fields().get("signal");
            if (!(signal instanceof Number number) ||
                    number.doubleValue() < 80.0) {
                return ReviewState.BLOCKED;
            }

            return ReviewState.COMPLETE;
        }
    }

    private static void validateId(String id) {
        validateKey(id);
    }

    private static void validateKey(String key) {
        if (key == null || key.isBlank() || key.length() > 256) {
            throw new ValidationException(
                    "Identifier must contain 1-256 characters.");
        }
    }

    public static void main(String[] args) {
        try {
            DocumentRepository documents = new DocumentRepository();

            documents.create(
                    "device-01",
                    Map.of(
                            "name", "GNSS-01",
                            "region", "Lucknow",
                            "active", true,
                            "signal", 94
                    )
            );

            documents.create(
                    "device-02",
                    Map.of(
                            "name", "GNSS-02",
                            "region", "Delhi",
                            "active", true,
                            "signal", 72
                    )
            );

            documents.update(
                    "device-01",
                    Map.of("firmware", "3.2.1")
            );

            KeyValueRepository sessions = new KeyValueRepository();
            sessions.put(
                    "session:device-01",
                    "authenticated",
                    Duration.ofMinutes(5)
            );

            ColumnFamilyRepository telemetry = new ColumnFamilyRepository();
            telemetry.put(
                    "device-01",
                    Map.of(
                            "temperature", 31.5,
                            "signal", 94,
                            "region", "Lucknow"
                    )
            );
            telemetry.put(
                    "device-02",
                    Map.of(
                            "signal", 72,
                            "region", "Delhi"
                    )
            );

            GraphRepository graph = new GraphRepository();
            graph.addNode("team", Set.of("Team"));
            graph.addNode("repository", Set.of("Repository"));
            graph.addNode("service", Set.of("Service"));
            graph.addNode("database", Set.of("Database"));

            graph.addRelationship(
                    "team",
                    "repository",
                    Relationship.OWNS
            );
            graph.addRelationship(
                    "repository",
                    "service",
                    Relationship.CONTAINS
            );
            graph.addRelationship(
                    "service",
                    "database",
                    Relationship.USES
            );

            DeviceService service = new DeviceService(
                    documents,
                    new ActiveDevicePolicy()
            );

            System.out.println("DOCUMENT MODEL");
            System.out.println(
                    documents.findByField("region", "Lucknow")
            );

            System.out.println("\nKEY-VALUE MODEL");
            System.out.println(
                    sessions.get("session:device-01")
            );

            System.out.println("\nCOLUMN-FAMILY MODEL");
            System.out.println(
                    telemetry.findByColumn("signal", 94)
            );

            System.out.println("\nGRAPH MODEL");
            System.out.println(
                    graph.shortestPath("team", "database")
            );

            System.out.println("\nENTERPRISE POLICY");
            System.out.println(
                    "device-01 state: " +
                            service.evaluate("device-01")
            );
            System.out.println(
                    "device-02 state: " +
                            service.evaluate("device-02")
            );

            System.out.println("\nFAILURE VALIDATION");
            try {
                documents.create("", Map.of("invalid", true));
            } catch (ValidationException exception) {
                System.out.println(
                        "Rejected invalid document: " +
                                exception.getMessage()
                );
            }

            try {
                graph.addRelationship(
                        "missing",
                        "database",
                        Relationship.USES
                );
            } catch (NotFoundException exception) {
                System.out.println(
                        "Rejected invalid graph relationship: " +
                                exception.getMessage()
                );
            }

            System.out.println("\nMODEL DISTINCTIONS");
            System.out.println(
                    "Document: schema-flexible aggregates."
            );
            System.out.println(
                    "Key-value: direct key-based access."
            );
            System.out.println(
                    "Column-family: sparse row-oriented access."
            );
            System.out.println(
                    "Graph: relationship and traversal-oriented data."
            );

        } catch (RuntimeException exception) {
            System.err.println(
                    "Application failure: " + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
