import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class DatabaseOptimizationCaseStudy {

    enum AccessPath {
        SEQUENTIAL_SCAN,
        INDEX_SCAN,
        INDEX_ONLY_SCAN
    }

    enum JoinAlgorithm {
        NESTED_LOOP,
        HASH_JOIN,
        MERGE_JOIN
    }

    enum QueryState {
        RECEIVED,
        PLANNED,
        ANALYZED,
        OPTIMIZED,
        FAILED
    }

    record ColumnStats(
        String name,
        long distinctValues,
        double nullFraction
    ) {
        ColumnStats {
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("Column name is required.");
            }
            if (distinctValues < 1) {
                throw new IllegalArgumentException(
                    "Distinct-value count must be positive."
                );
            }
            if (nullFraction < 0 || nullFraction > 1) {
                throw new IllegalArgumentException(
                    "Null fraction must be between zero and one."
                );
            }
        }
    }

    record IndexDefinition(
        String name,
        List<String> columns,
        Set<String> coveringColumns,
        boolean unique
    ) {
        IndexDefinition {
            if (name == null || name.isBlank() || columns.isEmpty()) {
                throw new IllegalArgumentException(
                    "An index requires a name and columns."
                );
            }

            columns = List.copyOf(columns);
            coveringColumns = Set.copyOf(coveringColumns);
        }

        boolean matches(String column) {
            return columns.getFirst().equals(column);
        }

        boolean covers(List<String> projectedColumns) {
            Set<String> available = new HashSet<>(columns);
            available.addAll(coveringColumns);
            return projectedColumns.stream().allMatch(available::contains);
        }
    }

    static final class TableStats {
        private final String name;
        private final double rows;
        private final double pages;
        private final Map<String, ColumnStats> columns;
        private final List<IndexDefinition> indexes;

        TableStats(
            String name,
            double rows,
            double pages,
            Map<String, ColumnStats> columns,
            List<IndexDefinition> indexes
        ) {
            if (name == null || name.isBlank() || rows <= 0 || pages <= 0) {
                throw new IllegalArgumentException("Invalid table statistics.");
            }

            this.name = name;
            this.rows = rows;
            this.pages = pages;
            this.columns = Map.copyOf(columns);
            this.indexes = List.copyOf(indexes);
        }

        String name() {
            return name;
        }

        double rows() {
            return rows;
        }

        double pages() {
            return pages;
        }

        ColumnStats column(String name) {
            return columns.get(name);
        }

        IndexDefinition findIndex(String column) {
            return indexes.stream()
                .filter(index -> index.matches(column))
                .findFirst()
                .orElse(null);
        }

        List<IndexDefinition> indexes() {
            return indexes;
        }
    }

    record Predicate(
        String column,
        String operator,
        String value
    ) {
        double selectivity(TableStats table) {
            ColumnStats stats = table.column(column);

            if (stats == null) {
                return 0.10;
            }

            return switch (operator) {
                case "=" -> Math.max(
                    1.0 / stats.distinctValues(),
                    0.000001
                );
                case "<", "<=", ">", ">=" -> 0.33;
                case "IS NULL" -> Math.max(
                    stats.nullFraction(),
                    0.000001
                );
                case "IS NOT NULL" -> Math.max(
                    1.0 - stats.nullFraction(),
                    0.000001
                );
                case "LIKE" -> 0.05;
                default -> 0.25;
            };
        }
    }

    record ScanPlan(
        TableStats table,
        AccessPath accessPath,
        double estimatedRows,
        double startupCost,
        double totalCost,
        String reason
    ) {}

    record JoinPlan(
        JoinAlgorithm algorithm,
        double leftRows,
        double rightRows,
        double outputRows,
        double cost,
        String reason
    ) {}

    record QueryPlan(
        String sql,
        List<ScanPlan> scans,
        List<JoinPlan> joins,
        double sortCost,
        double aggregateCost
    ) {
        double totalCost() {
            return scans.stream().mapToDouble(ScanPlan::totalCost).sum()
                + joins.stream().mapToDouble(JoinPlan::cost).sum()
                + sortCost
                + aggregateCost;
        }
    }

    static final class OptimizationException extends Exception {
        OptimizationException(String message) {
            super(message);
        }
    }

    static final class QueryContext {
        private QueryState state = QueryState.RECEIVED;

        void transition(QueryState next) throws OptimizationException {
            boolean valid = switch (state) {
                case RECEIVED -> next == QueryState.PLANNED
                    || next == QueryState.FAILED;
                case PLANNED -> next == QueryState.ANALYZED
                    || next == QueryState.FAILED;
                case ANALYZED -> next == QueryState.OPTIMIZED
                    || next == QueryState.FAILED;
                case OPTIMIZED, FAILED -> false;
            };

            if (!valid) {
                throw new OptimizationException(
                    "Invalid query state transition: "
                        + state + " -> " + next
                );
            }

            state = next;
        }

        QueryState state() {
            return state;
        }
    }

    static final class QueryOptimizer {
        private static final double SEQ_PAGE_COST = 1.0;
        private static final double RANDOM_PAGE_COST = 4.0;
        private static final double CPU_TUPLE_COST = 0.01;
        private static final double CPU_INDEX_TUPLE_COST = 0.005;

        ScanPlan estimateScan(
            TableStats table,
            List<Predicate> predicates,
            List<String> projected
        ) {
            double selectivity = 1.0;

            for (Predicate predicate : predicates) {
                selectivity *= predicate.selectivity(table);
            }

            double estimatedRows =
                Math.max(1.0, table.rows() * selectivity);

            IndexDefinition usableIndex = predicates.stream()
                .map(predicate -> table.findIndex(predicate.column()))
                .filter(Objects::nonNull)
                .findFirst()
                .orElse(null);

            boolean selective =
                estimatedRows < table.rows() * 0.20;

            if (usableIndex != null && selective) {
                boolean covering = usableIndex.covers(projected);

                AccessPath path = covering
                    ? AccessPath.INDEX_ONLY_SCAN
                    : AccessPath.INDEX_SCAN;

                double indexPages =
                    Math.max(1.0, Math.log(
                        Math.max(table.pages(), 2.0)
                    ) / Math.log(2.0));

                double heapPages =
                    Math.min(
                        table.pages(),
                        Math.max(
                            1.0,
                            estimatedRows
                                / Math.max(
                                    table.rows() / table.pages(),
                                    1.0
                                )
                        )
                    );

                double startup =
                    indexPages * RANDOM_PAGE_COST;

                double total =
                    startup
                    + heapPages * RANDOM_PAGE_COST
                    + estimatedRows * CPU_INDEX_TUPLE_COST;

                return new ScanPlan(
                    table,
                    path,
                    estimatedRows,
                    startup,
                    total,
                    "Selective predicates favor indexed access."
                );
            }

            double total =
                table.pages() * SEQ_PAGE_COST
                + table.rows() * CPU_TUPLE_COST;

            return new ScanPlan(
                table,
                AccessPath.SEQUENTIAL_SCAN,
                estimatedRows,
                0,
                total,
                usableIndex == null
                    ? "No suitable predicate index exists."
                    : "Available index is not selective enough."
            );
        }

        JoinPlan chooseJoin(
            double leftRows,
            double rightRows,
            double selectivity,
            boolean indexedInner
        ) {
            double outputRows =
                Math.max(1.0, leftRows * rightRows * selectivity);

            double nestedLoop =
                leftRows
                * (
                    indexedInner
                        ? Math.log(Math.max(rightRows, 2.0))
                            / Math.log(2.0)
                        : rightRows
                )
                * 0.01;

            double hashJoin =
                (leftRows + rightRows) * 0.03;

            double mergeJoin =
                (
                    leftRows
                        * Math.log(Math.max(leftRows, 2.0))
                        / Math.log(2.0)
                    + rightRows
                        * Math.log(Math.max(rightRows, 2.0))
                        / Math.log(2.0)
                ) * 0.005;

            List<JoinPlan> candidates = List.of(
                new JoinPlan(
                    JoinAlgorithm.NESTED_LOOP,
                    leftRows,
                    rightRows,
                    outputRows,
                    nestedLoop,
                    "Effective when the outer relation is small or the inner side is indexed."
                ),
                new JoinPlan(
                    JoinAlgorithm.HASH_JOIN,
                    leftRows,
                    rightRows,
                    outputRows,
                    hashJoin,
                    "Effective for large equality joins."
                ),
                new JoinPlan(
                    JoinAlgorithm.MERGE_JOIN,
                    leftRows,
                    rightRows,
                    outputRows,
                    mergeJoin,
                    "Useful when both inputs are ordered."
                )
            );

            return candidates.stream()
                .min(Comparator.comparingDouble(JoinPlan::cost))
                .orElseThrow();
        }
    }

    static final class RepositoryOptimizationService {
        private final QueryOptimizer optimizer = new QueryOptimizer();

        QueryPlan buildPlan(boolean optimized) {
            TableStats orders = createOrders(optimized);
            TableStats customers = createCustomers();

            List<Predicate> predicates = List.of(
                new Predicate("status", "=", "completed"),
                new Predicate("created_at", ">=", "2026-01-01")
            );

            ScanPlan orderScan = optimizer.estimateScan(
                orders,
                predicates,
                List.of("customer_id", "total_amount")
            );

            ScanPlan customerScan = optimizer.estimateScan(
                customers,
                List.of(),
                List.of("id", "region")
            );

            JoinPlan join = optimizer.chooseJoin(
                orderScan.estimatedRows(),
                customerScan.estimatedRows(),
                1.0 / customers.rows(),
                true
            );

            double sortCost =
                join.outputRows()
                * (
                    Math.log(
                        Math.max(join.outputRows(), 2.0)
                    ) / Math.log(2.0)
                )
                * 0.02;

            double aggregateCost = join.outputRows() * 0.02;

            return new QueryPlan(
                """
                SELECT c.region, SUM(o.total_amount)
                FROM orders o
                JOIN customers c ON c.id = o.customer_id
                WHERE o.status = 'completed'
                  AND o.created_at >= DATE '2026-01-01'
                GROUP BY c.region
                ORDER BY SUM(o.total_amount) DESC
                """,
                List.of(orderScan, customerScan),
                List.of(join),
                sortCost,
                aggregateCost
            );
        }

        private TableStats createOrders(boolean optimized) {
            List<IndexDefinition> indexes = new ArrayList<>(
                List.of(
                    new IndexDefinition(
                        "orders_pkey",
                        List.of("id"),
                        Set.of(),
                        true
                    ),
                    new IndexDefinition(
                        "idx_orders_customer",
                        List.of("customer_id"),
                        Set.of(),
                        false
                    ),
                    new IndexDefinition(
                        "idx_orders_created",
                        List.of("created_at"),
                        Set.of(),
                        false
                    ),
                    new IndexDefinition(
                        "idx_orders_status_created",
                        List.of("status", "created_at"),
                        Set.of(),
                        false
                    )
                )
            );

            if (optimized) {
                indexes.add(
                    new IndexDefinition(
                        "idx_orders_status_created_covering",
                        List.of("status", "created_at"),
                        Set.of("customer_id", "total_amount"),
                        false
                    )
                );
            }

            Map<String, ColumnStats> columns = new HashMap<>();
            columns.put("id", new ColumnStats("id", 2_500_000, 0));
            columns.put(
                "customer_id",
                new ColumnStats("customer_id", 180_000, 0)
            );
            columns.put("status", new ColumnStats("status", 5, 0));
            columns.put(
                "created_at",
                new ColumnStats("created_at", 900, 0)
            );
            columns.put(
                "total_amount",
                new ColumnStats("total_amount", 1_000_000, 0)
            );

            return new TableStats(
                "orders",
                2_500_000,
                125_000,
                columns,
                indexes
            );
        }

        private TableStats createCustomers() {
            Map<String, ColumnStats> columns = new HashMap<>();
            columns.put("id", new ColumnStats("id", 180_000, 0));
            columns.put("region", new ColumnStats("region", 8, 0));
            columns.put(
                "customer_tier",
                new ColumnStats("customer_tier", 4, 0)
            );
            columns.put("email", new ColumnStats("email", 180_000, 0));

            return new TableStats(
                "customers",
                180_000,
                12_000,
                columns,
                List.of(
                    new IndexDefinition(
                        "customers_pkey",
                        List.of("id"),
                        Set.of(),
                        true
                    ),
                    new IndexDefinition(
                        "idx_customers_region",
                        List.of("region"),
                        Set.of(),
                        false
                    )
                )
            );
        }
    }

    static void printPlan(String label, QueryPlan plan) {
        System.out.println("\n" + "=".repeat(78));
        System.out.println(label);
        System.out.println("=".repeat(78));
        System.out.printf(
            "Estimated total cost: %.2f%n%n",
            plan.totalCost()
        );

        for (ScanPlan scan : plan.scans()) {
            System.out.printf(
                "Table=%s, access=%s, rows=%.0f, cost=%.2f%n",
                scan.table().name(),
                scan.accessPath(),
                scan.estimatedRows(),
                scan.totalCost()
            );
            System.out.println("Reason: " + scan.reason());
        }

        for (JoinPlan join : plan.joins()) {
            System.out.printf(
                "Join=%s, output rows=%.0f, cost=%.2f%n",
                join.algorithm(),
                join.outputRows(),
                join.cost()
            );
            System.out.println("Reason: " + join.reason());
        }

        System.out.printf(
            "Sort cost=%.2f, aggregate cost=%.2f%n",
            plan.sortCost(),
            plan.aggregateCost()
        );
    }

    static void validateStateMachine() throws OptimizationException {
        QueryContext context = new QueryContext();

        context.transition(QueryState.PLANNED);
        context.transition(QueryState.ANALYZED);
        context.transition(QueryState.OPTIMIZED);

        if (context.state() != QueryState.OPTIMIZED) {
            throw new OptimizationException("State transition test failed.");
        }
    }

    public static void main(String[] args) {
        try {
            validateStateMachine();

            RepositoryOptimizationService service =
                new RepositoryOptimizationService();

            QueryPlan baseline = service.buildPlan(false);
            QueryPlan optimized = service.buildPlan(true);

            printPlan("BASELINE QUERY PLAN", baseline);
            printPlan("OPTIMIZED QUERY PLAN", optimized);

            double improvement =
                (
                    (baseline.totalCost() - optimized.totalCost())
                    / baseline.totalCost()
                ) * 100.0;

            System.out.println("\n" + "=".repeat(78));
            System.out.println("OPTIMIZATION RESULT");
            System.out.println("=".repeat(78));
            System.out.printf(
                "Baseline cost:  %.2f%n",
                baseline.totalCost()
            );
            System.out.printf(
                "Optimized cost: %.2f%n",
                optimized.totalCost()
            );
            System.out.printf(
                "Estimated cost change: %.2f%%%n",
                improvement
            );

            System.out.println("\nENTERPRISE CONTROLS");
            System.out.println(
                "1. Compare estimates with actual execution statistics."
            );
            System.out.println(
                "2. Refresh optimizer statistics after significant data changes."
            );
            System.out.println(
                "3. Treat index creation as a write-cost and storage decision."
            );
            System.out.println(
                "4. Use parameter binding for application queries."
            );
            System.out.println(
                "5. Restrict expensive diagnostic operations to authorized roles."
            );
        } catch (Exception exception) {
            System.err.println(
                "Optimization workflow failed: "
                    + exception.getMessage()
            );
            System.exit(1);
        }
    }
}
