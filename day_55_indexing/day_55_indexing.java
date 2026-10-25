import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Enterprise-oriented indexing and query-performance model.
 *
 * The program represents:
 * - a relational table
 * - B-tree-style indexes
 * - composite indexes
 * - covering indexes
 * - partial indexes
 * - query-plan selection
 * - explicit validation
 * - query execution
 * - index-maintenance implications
 */
public class IndexingPerformance {

    enum ScanType {
        SEQUENTIAL_SCAN,
        INDEX_SCAN,
        INDEX_ONLY_SCAN
    }

    record Order(
        int id,
        int customerId,
        String status,
        String region,
        double amount,
        String createdAt
    ) {}

    record Query(
        Map<String, String> filters,
        List<String> selectedColumns
    ) {
        Query {
            filters = Map.copyOf(filters);
            selectedColumns = List.copyOf(selectedColumns);

            if (selectedColumns.isEmpty()) {
                throw new ValidationException(
                    "At least one selected column is required"
                );
            }
        }
    }

    record QueryPlan(
        ScanType scanType,
        String indexName,
        int estimatedRows,
        double estimatedCost,
        String reason
    ) {}

    static final class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    interface IndexPredicate {
        boolean matches(Order order);
    }

    static final class Index {
        private final String name;
        private final List<String> keyColumns;
        private final List<String> includedColumns;
        private final IndexPredicate predicate;
        private final List<IndexEntry> entries = new ArrayList<>();

        record IndexEntry(List<String> key, int rowId) {}

        Index(
            String name,
            List<String> keyColumns,
            List<String> includedColumns,
            IndexPredicate predicate
        ) {
            if (name == null || name.isBlank()) {
                throw new ValidationException("Index name is required");
            }

            if (keyColumns == null || keyColumns.isEmpty()) {
                throw new ValidationException(
                    "At least one index key is required"
                );
            }

            this.name = name;
            this.keyColumns = List.copyOf(keyColumns);
            this.includedColumns = List.copyOf(includedColumns);
            this.predicate = predicate;
        }

        String name() {
            return name;
        }

        boolean applicable(Order order) {
            return predicate == null || predicate.matches(order);
        }

        boolean supportsEqualityPrefix(Map<String, String> filters) {
            boolean matched = false;

            for (String column : keyColumns) {
                if (filters.containsKey(column)) {
                    matched = true;
                } else {
                    break;
                }
            }

            return matched;
        }

        boolean covers(List<String> requestedColumns) {
            Set<String> available = new java.util.HashSet<>();
            available.addAll(keyColumns);
            available.addAll(includedColumns);

            return requestedColumns.stream()
                .allMatch(available::contains);
        }

        List<String> key(Order order) {
            List<String> result = new ArrayList<>();

            for (String column : keyColumns) {
                result.add(value(order, column));
            }

            return result;
        }

        void add(Order order) {
            entries.add(new IndexEntry(key(order), order.id()));
        }

        void finalizeIndex() {
            entries.sort(
                Comparator
                    .comparing(IndexEntry::key, IndexingPerformance::compareKeys)
                    .thenComparingInt(IndexEntry::rowId)
            );
        }

        List<IndexEntry> entries() {
            return List.copyOf(entries);
        }

        private static int compareKeys(
            List<String> left,
            List<String> right
        ) {
            int size = Math.min(left.size(), right.size());

            for (int i = 0; i < size; i++) {
                int comparison = left.get(i).compareTo(right.get(i));

                if (comparison != 0) {
                    return comparison;
                }
            }

            return Integer.compare(left.size(), right.size());
        }
    }

    static final class OrderRepository {
        private final Map<Integer, Order> orders = new HashMap<>();
        private final Map<String, Index> indexes = new HashMap<>();
        private long baseWrites;

        void insert(Order order) {
            validate(order);

            if (orders.containsKey(order.id())) {
                throw new ValidationException(
                    "Duplicate order ID: " + order.id()
                );
            }

            orders.put(order.id(), order);
            baseWrites++;

            for (Index index : indexes.values()) {
                if (index.applicable(order)) {
                    index.add(order);
                }
            }
        }

        void createIndex(
            String name,
            List<String> keyColumns,
            List<String> includedColumns,
            IndexPredicate predicate
        ) {
            if (indexes.containsKey(name)) {
                throw new ValidationException(
                    "Index already exists: " + name
                );
            }

            validateColumns(keyColumns);
            validateColumns(includedColumns);

            Index index = new Index(
                name,
                keyColumns,
                includedColumns,
                predicate
            );

            for (Order order : orders.values()) {
                if (index.applicable(order)) {
                    index.add(order);
                }
            }

            index.finalizeIndex();
            indexes.put(name, index);
        }

        QueryPlan explain(Query query) {
            int totalRows = orders.size();

            if (totalRows == 0) {
                return new QueryPlan(
                    ScanType.SEQUENTIAL_SCAN,
                    null,
                    0,
                    0,
                    "The table contains no rows"
                );
            }

            double sequentialCost = totalRows;
            QueryPlan best = null;

            for (Index index : indexes.values()) {
                if (!index.supportsEqualityPrefix(query.filters())) {
                    continue;
                }

                double selectivity = estimateSelectivity(query.filters());

                int estimatedRows = Math.max(
                    1,
                    (int) Math.floor(totalRows * selectivity)
                );

                double cost = 3.0 + estimatedRows * 0.8;
                ScanType scanType = ScanType.INDEX_SCAN;

                String reason =
                    index.name() +
                    " matches the leading equality predicate";

                if (index.covers(query.selectedColumns())) {
                    scanType = ScanType.INDEX_ONLY_SCAN;
                    cost *= 0.75;
                    reason += " and covers the requested columns";
                }

                QueryPlan candidate = new QueryPlan(
                    scanType,
                    index.name(),
                    estimatedRows,
                    cost,
                    reason
                );

                if (best == null ||
                    candidate.estimatedCost() < best.estimatedCost()) {
                    best = candidate;
                }
            }

            if (best == null || best.estimatedCost() >= sequentialCost) {
                return new QueryPlan(
                    ScanType.SEQUENTIAL_SCAN,
                    null,
                    totalRows,
                    sequentialCost,
                    "No index has a lower estimated cost"
                );
            }

            return best;
        }

        List<Map<String, String>> execute(Query query) {
            QueryPlan plan = explain(query);
            List<Order> candidates = new ArrayList<>();

            if (plan.indexName() == null) {
                candidates.addAll(orders.values());
            } else {
                Index index = indexes.get(plan.indexName());

                for (Index.IndexEntry entry : index.entries()) {
                    Order order = orders.get(entry.rowId());

                    if (order != null) {
                        candidates.add(order);
                    }
                }
            }

            List<Map<String, String>> results = new ArrayList<>();

            for (Order order : candidates) {
                if (!matches(order, query.filters())) {
                    continue;
                }

                Map<String, String> projected = new HashMap<>();

                for (String column : query.selectedColumns()) {
                    projected.put(column, value(order, column));
                }

                results.add(Map.copyOf(projected));
            }

            return results;
        }

        long baseWrites() {
            return baseWrites;
        }

        int rowCount() {
            return orders.size();
        }

        private double estimateSelectivity(
            Map<String, String> filters
        ) {
            if (filters.isEmpty()) {
                return 1.0;
            }

            double selectivity = 1.0;

            for (Map.Entry<String, String> filter : filters.entrySet()) {
                long matches = orders.values()
                    .stream()
                    .filter(order ->
                        matches(
                            order,
                            Map.of(filter.getKey(), filter.getValue())
                        )
                    )
                    .count();

                selectivity *=
                    (double) matches / Math.max(1, orders.size());
            }

            return Math.min(1.0, selectivity);
        }

        private static boolean matches(
            Order order,
            Map<String, String> filters
        ) {
            for (Map.Entry<String, String> filter : filters.entrySet()) {
                if (!value(order, filter.getKey())
                    .equals(filter.getValue())) {
                    return false;
                }
            }

            return true;
        }

        private static String value(Order order, String column) {
            return switch (column) {
                case "id" -> Integer.toString(order.id());
                case "customerId" -> Integer.toString(order.customerId());
                case "status" -> order.status();
                case "region" -> order.region();
                case "amount" -> Double.toString(order.amount());
                case "createdAt" -> order.createdAt();
                default -> throw new ValidationException(
                    "Unknown column: " + column
                );
            };
        }

        private static void validate(Order order) {
            Objects.requireNonNull(order, "order");

            if (order.id() <= 0) {
                throw new ValidationException("Order ID must be positive");
            }

            if (order.customerId() <= 0) {
                throw new ValidationException(
                    "Customer ID must be positive"
                );
            }

            if (!Set.of(
                "pending",
                "paid",
                "shipped",
                "cancelled"
            ).contains(order.status())) {
                throw new ValidationException(
                    "Unsupported status: " + order.status()
                );
            }

            if (order.amount() < 0) {
                throw new ValidationException(
                    "Order amount cannot be negative"
                );
            }
        }

        private static void validateColumns(List<String> columns) {
            Set<String> allowed = Set.of(
                "id",
                "customerId",
                "status",
                "region",
                "amount",
                "createdAt"
            );

            for (String column : columns) {
                if (!allowed.contains(column)) {
                    throw new ValidationException(
                        "Unknown column: " + column
                    );
                }
            }
        }
    }

    static OrderRepository seed() {
        OrderRepository repository = new OrderRepository();

        String[] statuses = {
            "pending", "paid", "shipped", "cancelled"
        };

        String[] regions = {
            "north", "south", "east", "west"
        };

        for (int id = 1; id <= 1000; id++) {
            repository.insert(
                new Order(
                    id,
                    (id * 17) % 100 + 1,
                    statuses[id % statuses.length],
                    regions[id % regions.length],
                    100 + ((id * 37) % 4900),
                    String.format(
                        "2026-10-%02d",
                        (id % 28) + 1
                    )
                )
            );
        }

        return repository;
    }

    static void printQuery(
        OrderRepository repository,
        Query query
    ) {
        QueryPlan plan = repository.explain(query);

        System.out.println("PLAN");
        System.out.println("  Type: " + plan.scanType());
        System.out.println(
            "  Index: " +
            (plan.indexName() == null
                ? "(none)"
                : plan.indexName())
        );
        System.out.println(
            "  Estimated rows: " + plan.estimatedRows()
        );
        System.out.printf(
            "  Estimated cost: %.2f%n",
            plan.estimatedCost()
        );
        System.out.println("  Reason: " + plan.reason());

        List<Map<String, String>> result =
            repository.execute(query);

        System.out.println(
            "  Actual rows: " + result.size()
        );

        if (!result.isEmpty()) {
            System.out.println(
                "  First row: " + result.get(0)
            );
        }

        System.out.println();
    }

    public static void main(String[] args) {
        OrderRepository repository = seed();

        repository.createIndex(
            "idx_customer",
            List.of("customerId"),
            List.of(),
            null
        );

        repository.createIndex(
            "idx_status_region",
            List.of("status", "region"),
            List.of("amount", "createdAt"),
            null
        );

        repository.createIndex(
            "idx_paid_customer",
            List.of("customerId"),
            List.of("amount"),
            order -> order.status().equals("paid")
        );

        Query customerQuery = new Query(
            Map.of("customerId", "42"),
            List.of("id", "customerId", "amount")
        );

        Query compositeQuery = new Query(
            Map.of(
                "status", "paid",
                "region", "north"
            ),
            List.of("id", "amount", "createdAt")
        );

        Query nonLeadingQuery = new Query(
            Map.of("region", "north"),
            List.of("id", "customerId")
        );

        System.out.println("CUSTOMER LOOKUP");
        printQuery(repository, customerQuery);

        System.out.println("COMPOSITE LOOKUP");
        printQuery(repository, compositeQuery);

        System.out.println("NON-LEADING COLUMN LOOKUP");
        printQuery(repository, nonLeadingQuery);

        repository.insert(
            new Order(
                5001,
                42,
                "paid",
                "north",
                725.50,
                "2026-10-25"
            )
        );

        System.out.println(
            "Rows: " + repository.rowCount()
        );
        System.out.println(
            "Base writes: " + repository.baseWrites()
        );

        try {
            repository.insert(
                new Order(
                    5002,
                    42,
                    "unknown",
                    "north",
                    100.0,
                    "2026-10-25"
                )
            );
        } catch (ValidationException ex) {
            System.err.println(
                "Rejected invalid row: " + ex.getMessage()
            );
        }
    }
}
