import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

public class AdvancedSqlAnalytics {

    enum Category {
        ELECTRONICS,
        FURNITURE
    }

    record Customer(int id, String name, String region) {
        Customer {
            if (id <= 0 || name == null || name.isBlank()) {
                throw new IllegalArgumentException("Invalid customer");
            }
        }
    }

    record Sale(
            int id,
            int customerId,
            int productId,
            String month,
            Category category,
            BigDecimal amount) {

        Sale {
            if (id <= 0 || customerId <= 0 || productId <= 0) {
                throw new IllegalArgumentException("Invalid sale identifiers");
            }

            Objects.requireNonNull(month, "month");
            Objects.requireNonNull(category, "category");
            Objects.requireNonNull(amount, "amount");

            if (!month.matches("\\d{4}-\\d{2}")) {
                throw new IllegalArgumentException("Invalid month: " + month);
            }

            if (amount.signum() < 0) {
                throw new IllegalArgumentException("Negative sale amount");
            }
        }
    }

    record CustomerTotal(int customerId, BigDecimal total) {}

    record RunningSale(
            int customerId,
            String month,
            int saleId,
            BigDecimal amount,
            BigDecimal runningTotal) {}

    record RegionRank(
            String region,
            int customerId,
            BigDecimal total,
            int rank) {}

    interface AggregationPolicy<T, R> {
        R apply(List<T> rows);
    }

    static final class Repository {
        private final Map<Integer, Customer> customers;
        private final List<Sale> sales;

        Repository(List<Customer> customers, List<Sale> sales) {
            this.customers = customers.stream()
                    .collect(Collectors.toUnmodifiableMap(Customer::id, c -> c));
            this.sales = List.copyOf(sales);
        }

        // Explicit hash indexing models the lookup side of an INNER JOIN.
        List<String> innerJoin() {
            return sales.stream()
                    .filter(sale -> customers.containsKey(sale.customerId()))
                    .map(sale -> {
                        Customer customer = customers.get(sale.customerId());
                        return sale.id() + " -> " + customer.name();
                    })
                    .toList();
        }

        // The result is equivalent to a GROUP BY customer_id aggregation.
        List<CustomerTotal> customerTotals() {
            Map<Integer, BigDecimal> totals = new HashMap<>();

            for (Sale sale : sales) {
                totals.merge(
                        sale.customerId(),
                        sale.amount(),
                        BigDecimal::add
                );
            }

            return totals.entrySet()
                    .stream()
                    .map(entry -> new CustomerTotal(
                            entry.getKey(),
                            entry.getValue()
                    ))
                    .sorted(Comparator.comparing(
                            CustomerTotal::total,
                            Comparator.reverseOrder()
                    ))
                    .toList();
        }

        // The average is produced by an independent aggregate and then used
        // as the predicate for the outer result, matching a subquery pattern.
        List<CustomerTotal> aboveAverageCustomers() {
            List<CustomerTotal> totals = customerTotals();

            if (totals.isEmpty()) {
                return List.of();
            }

            BigDecimal sum = totals.stream()
                    .map(CustomerTotal::total)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);

            BigDecimal average = sum.divide(
                    BigDecimal.valueOf(totals.size()),
                    2,
                    RoundingMode.HALF_UP
            );

            return totals.stream()
                    .filter(row -> row.total().compareTo(average) >= 0)
                    .toList();
        }

        // A CTE is represented as a staged immutable result before the
        // reporting operation consumes it.
        Map<String, BigDecimal> monthlyTotals() {
            return sales.stream()
                    .collect(Collectors.groupingBy(
                            Sale::month,
                            LinkedHashMap::new,
                            Collectors.reducing(
                                    BigDecimal.ZERO,
                                    Sale::amount,
                                    BigDecimal::add
                            )
                    ));
        }

        // Window semantics are partitioned by customer and ordered by time.
        List<RunningSale> runningTotals() {
            Map<Integer, List<Sale>> partitions = sales.stream()
                    .collect(Collectors.groupingBy(Sale::customerId));

            List<RunningSale> result = new ArrayList<>();

            partitions.entrySet()
                    .stream()
                    .sorted(Map.Entry.comparingByKey())
                    .forEach(entry -> {
                        List<Sale> ordered = entry.getValue()
                                .stream()
                                .sorted(
                                        Comparator.comparing(Sale::month)
                                                .thenComparing(Sale::id)
                                )
                                .toList();

                        BigDecimal running = BigDecimal.ZERO;

                        for (Sale sale : ordered) {
                            running = running.add(sale.amount());

                            result.add(new RunningSale(
                                    sale.customerId(),
                                    sale.month(),
                                    sale.id(),
                                    sale.amount(),
                                    running
                            ));
                        }
                    });

            return List.copyOf(result);
        }

        List<RegionRank> regionalRanks() {
            Map<String, Map<Integer, BigDecimal>> regionTotals = new HashMap<>();

            for (Sale sale : sales) {
                Customer customer = customers.get(sale.customerId());

                if (customer == null) {
                    continue;
                }

                regionTotals
                        .computeIfAbsent(customer.region(), key -> new HashMap<>())
                        .merge(
                                sale.customerId(),
                                sale.amount(),
                                BigDecimal::add
                        );
            }

            List<RegionRank> result = new ArrayList<>();

            for (Map.Entry<String, Map<Integer, BigDecimal>> region
                    : regionTotals.entrySet()) {

                List<CustomerTotal> totals = region.getValue()
                        .entrySet()
                        .stream()
                        .map(entry -> new CustomerTotal(
                                entry.getKey(),
                                entry.getValue()
                        ))
                        .sorted(
                                Comparator.comparing(
                                        CustomerTotal::total,
                                        Comparator.reverseOrder()
                                ).thenComparing(CustomerTotal::customerId)
                        )
                        .toList();

                BigDecimal previous = null;
                int rank = 0;

                for (int i = 0; i < totals.size(); i++) {
                    CustomerTotal total = totals.get(i);

                    if (previous == null ||
                            total.total().compareTo(previous) != 0) {
                        rank = i + 1;
                        previous = total.total();
                    }

                    result.add(new RegionRank(
                            region.getKey(),
                            total.customerId(),
                            total.total(),
                            rank
                    ));
                }
            }

            return List.copyOf(result);
        }
    }

    public static void main(String[] args) {
        List<Customer> customers = List.of(
                new Customer(101, "Asha", "North"),
                new Customer(102, "Ravi", "South"),
                new Customer(103, "Meera", "North"),
                new Customer(104, "Kabir", "West"),
                new Customer(105, "Nisha", "West"),
                new Customer(106, "Dev", "East")
        );

        List<Sale> sales = List.of(
                new Sale(1, 101, 1001, "2026-01", Category.ELECTRONICS, new BigDecimal("1200.00")),
                new Sale(2, 102, 1002, "2026-01", Category.ELECTRONICS, new BigDecimal("850.00")),
                new Sale(3, 103, 1003, "2026-01", Category.FURNITURE, new BigDecimal("450.00")),
                new Sale(4, 101, 1004, "2026-02", Category.ELECTRONICS, new BigDecimal("400.00")),
                new Sale(5, 104, 1005, "2026-02", Category.FURNITURE, new BigDecimal("300.00")),
                new Sale(6, 102, 1001, "2026-02", Category.ELECTRONICS, new BigDecimal("1300.00")),
                new Sale(7, 105, 1002, "2026-03", Category.ELECTRONICS, new BigDecimal("900.00")),
                new Sale(8, 103, 1005, "2026-03", Category.FURNITURE, new BigDecimal("280.00")),
                new Sale(9, 101, 1002, "2026-03", Category.ELECTRONICS, new BigDecimal("820.00")),
                new Sale(10, 104, 1001, "2026-04", Category.ELECTRONICS, new BigDecimal("1250.00"))
        );

        Repository repository = new Repository(customers, sales);

        System.out.println("INNER JOIN");
        repository.innerJoin().forEach(System.out::println);

        System.out.println("\nSUBQUERY-STYLE FILTER");
        repository.aboveAverageCustomers()
                .forEach(System.out::println);

        System.out.println("\nCTE-STYLE MONTHLY TOTALS");
        repository.monthlyTotals()
                .forEach((month, total) ->
                        System.out.println(month + " = " + total));

        System.out.println("\nWINDOW RUNNING TOTALS");
        repository.runningTotals()
                .forEach(System.out::println);

        System.out.println("\nWINDOW RANKS");
        repository.regionalRanks()
                .forEach(System.out::println);
    }
}
