import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

public class NormalizationEnterpriseDemo {

    enum NormalForm {
        FIRST,
        SECOND,
        THIRD,
        DENORMALIZED
    }

    enum FindingType {
        ATOMICITY_VIOLATION,
        PARTIAL_DEPENDENCY,
        TRANSITIVE_DEPENDENCY,
        DUPLICATE_KEY,
        REFERENTIAL_INTEGRITY
    }

    record FunctionalDependency(
        Set<String> determinant,
        Set<String> dependent
    ) {
        public FunctionalDependency {
            determinant = Set.copyOf(determinant);
            dependent = Set.copyOf(dependent);
        }
    }

    record Finding(
        FindingType type,
        NormalForm normalForm,
        String message
    ) {}

    record Customer(
        long id,
        String name,
        String city
    ) {
        Customer {
            if (id <= 0) {
                throw new IllegalArgumentException("customer id must be positive");
            }
            if (name == null || name.isBlank()) {
                throw new IllegalArgumentException("customer name is required");
            }
            if (city == null || city.isBlank()) {
                throw new IllegalArgumentException("customer city is required");
            }
        }
    }

    record Order(
        long id,
        long customerId,
        long amount
    ) {
        Order {
            if (id <= 0 || customerId <= 0) {
                throw new IllegalArgumentException("identifiers must be positive");
            }
            if (amount <= 0) {
                throw new IllegalArgumentException("amount must be positive");
            }
        }
    }

    static final class NormalizationPolicy {

        private NormalizationPolicy() {
        }

        static List<Finding> inspect1NF(
            List<String> columns,
            List<Map<String, Object>> rows
        ) {
            List<Finding> findings = new ArrayList<>();

            for (Map<String, Object> row : rows) {
                if (!row.keySet().equals(Set.copyOf(columns))) {
                    findings.add(new Finding(
                        FindingType.ATOMICITY_VIOLATION,
                        NormalForm.FIRST,
                        "Row does not match the declared atomic relation"
                    ));
                    continue;
                }

                for (Map.Entry<String, Object> entry : row.entrySet()) {
                    Object value = entry.getValue();

                    if (value instanceof List<?> ||
                        value instanceof Set<?> ||
                        value instanceof Map<?, ?>) {
                        findings.add(new Finding(
                            FindingType.ATOMICITY_VIOLATION,
                            NormalForm.FIRST,
                            "Column " + entry.getKey() +
                            " contains a multivalued or structured attribute"
                        ));
                    }
                }
            }

            return findings;
        }

        static List<Finding> inspect2NF(
            Set<String> candidateKey,
            List<FunctionalDependency> dependencies
        ) {
            List<Finding> findings = new ArrayList<>();

            for (FunctionalDependency dependency : dependencies) {
                boolean properSubset =
                    dependency.determinant().size() < candidateKey.size()
                    && candidateKey.containsAll(dependency.determinant());

                boolean determinesNonKey = dependency.dependent().stream()
                    .anyMatch(attribute -> !candidateKey.contains(attribute));

                if (properSubset && determinesNonKey) {
                    findings.add(new Finding(
                        FindingType.PARTIAL_DEPENDENCY,
                        NormalForm.SECOND,
                        dependency.determinant() +
                        " determines non-key attributes " +
                        dependency.dependent()
                    ));
                }
            }

            return findings;
        }

        static List<Finding> inspect3NF(
            Set<String> candidateKey,
            List<FunctionalDependency> dependencies
        ) {
            List<Finding> findings = new ArrayList<>();

            Map<String, Set<String>> dependencyMap = new HashMap<>();

            for (FunctionalDependency dependency : dependencies) {
                if (dependency.determinant().size() == 1) {
                    String determinant =
                        dependency.determinant().iterator().next();

                    dependencyMap.put(
                        determinant,
                        dependency.dependent()
                    );
                }
            }

            for (FunctionalDependency first : dependencies) {
                if (!first.determinant().equals(candidateKey)) {
                    continue;
                }

                for (String middle : first.dependent()) {
                    Set<String> downstream = dependencyMap.get(middle);

                    if (downstream == null) {
                        continue;
                    }

                    for (String finalAttribute : downstream) {
                        if (!candidateKey.contains(finalAttribute)) {
                            findings.add(new Finding(
                                FindingType.TRANSITIVE_DEPENDENCY,
                                NormalForm.THIRD,
                                candidateKey + " -> " +
                                middle + " -> " +
                                finalAttribute
                            ));
                        }
                    }
                }
            }

            return findings;
        }
    }

    static final class Repository {

        private final Map<Long, Customer> customers =
            new LinkedHashMap<>();

        private final Map<Long, Order> orders =
            new LinkedHashMap<>();

        void addCustomer(Customer customer) {
            Objects.requireNonNull(customer, "customer");

            if (customers.containsKey(customer.id())) {
                throw new IllegalStateException(
                    "duplicate customer id: " + customer.id()
                );
            }

            customers.put(customer.id(), customer);
        }

        void addOrder(Order order) {
            Objects.requireNonNull(order, "order");

            if (orders.containsKey(order.id())) {
                throw new IllegalStateException(
                    "duplicate order id: " + order.id()
                );
            }

            if (!customers.containsKey(order.customerId())) {
                throw new IllegalStateException(
                    "customer does not exist: " + order.customerId()
                );
            }

            orders.put(order.id(), order);
        }

        List<String> normalizedReport() {
            return orders.values().stream()
                .map(order -> {
                    Customer customer =
                        customers.get(order.customerId());

                    return String.format(
                        "order=%d customer=%s city=%s amount=%d",
                        order.id(),
                        customer.name(),
                        customer.city(),
                        order.amount()
                    );
                })
                .toList();
        }

        List<String> denormalizedProjection() {
            /*
             * This projection is intentionally redundant for a read-heavy
             * report. It is derived from normalized authoritative data rather
             * than becoming a second writable source of truth.
             */
            return orders.values().stream()
                .map(order -> {
                    Customer customer =
                        customers.get(order.customerId());

                    return String.format(
                        "order=%d customer_id=%d customer=%s city=%s",
                        order.id(),
                        customer.id(),
                        customer.name(),
                        customer.city()
                    );
                })
                .toList();
        }
    }

    static final class DenormalizationDecision {

        private final int readFrequency;
        private final int joinCost;
        private final int updateFrequency;
        private final int consistencyRisk;

        DenormalizationDecision(
            int readFrequency,
            int joinCost,
            int updateFrequency,
            int consistencyRisk
        ) {
            if (readFrequency < 0 ||
                joinCost < 0 ||
                updateFrequency < 0 ||
                consistencyRisk < 0) {
                throw new IllegalArgumentException(
                    "workload metrics cannot be negative"
                );
            }

            this.readFrequency = readFrequency;
            this.joinCost = joinCost;
            this.updateFrequency = updateFrequency;
            this.consistencyRisk = consistencyRisk;
        }

        boolean justified() {
            long readBenefit =
                (long) readFrequency * joinCost;

            long writeRisk =
                (long) updateFrequency * consistencyRisk;

            return readBenefit > writeRisk * 2;
        }

        String explanation() {
            return justified()
                ? "Controlled redundancy may be justified for this workload."
                : "Keep the normalized design because write and consistency costs dominate.";
        }
    }

    public static void main(String[] args) {
        System.out.println("ENTERPRISE DATABASE NORMALIZATION MODEL\n");

        List<String> atomicColumns =
            List.of("customer_id", "phone_number", "phone_type");

        List<Map<String, Object>> atomicRows = List.of(
            Map.of(
                "customer_id", 1L,
                "phone_number", "9876543210",
                "phone_type", "mobile"
            ),
            Map.of(
                "customer_id", 1L,
                "phone_number", "0522123456",
                "phone_type", "office"
            )
        );

        System.out.println("1NF findings:");
        printFindings(
            NormalizationPolicy.inspect1NF(
                atomicColumns,
                atomicRows
            )
        );

        List<FunctionalDependency> enrollmentDependencies = List.of(
            new FunctionalDependency(
                Set.of("student_id"),
                Set.of("student_name")
            ),
            new FunctionalDependency(
                Set.of("course_id"),
                Set.of("course_name")
            ),
            new FunctionalDependency(
                Set.of("student_id", "course_id"),
                Set.of("grade")
            )
        );

        System.out.println("\n2NF findings:");
        printFindings(
            NormalizationPolicy.inspect2NF(
                Set.of("student_id", "course_id"),
                enrollmentDependencies
            )
        );

        List<FunctionalDependency> employeeDependencies = List.of(
            new FunctionalDependency(
                Set.of("employee_id"),
                Set.of("department_id")
            ),
            new FunctionalDependency(
                Set.of("department_id"),
                Set.of("department_name")
            )
        );

        System.out.println("\n3NF findings:");
        printFindings(
            NormalizationPolicy.inspect3NF(
                Set.of("employee_id"),
                employeeDependencies
            )
        );

        Repository repository = new Repository();

        repository.addCustomer(
            new Customer(1, "Nisha", "Lucknow")
        );

        repository.addCustomer(
            new Customer(2, "Arjun", "Delhi")
        );

        repository.addOrder(
            new Order(9001, 1, 2500)
        );

        repository.addOrder(
            new Order(9002, 2, 1800)
        );

        System.out.println("\nNormalized report:");
        repository.normalizedReport()
            .forEach(row -> System.out.println("  " + row));

        System.out.println("\nDerived denormalized projection:");
        repository.denormalizedProjection()
            .forEach(row -> System.out.println("  " + row));

        DenormalizationDecision decision =
            new DenormalizationDecision(
                1000,
                4,
                10,
                20
            );

        System.out.println("\nDenormalization policy:");
        System.out.println("  " + decision.explanation());

        try {
            repository.addOrder(
                new Order(9003, 999, 1200)
            );
        } catch (IllegalStateException exception) {
            System.out.println(
                "\nExpected referential-integrity failure: " +
                exception.getMessage()
            );
        }

        try {
            repository.addCustomer(
                new Customer(1, "Duplicate", "Delhi")
            );
        } catch (IllegalStateException exception) {
            System.out.println(
                "Expected uniqueness failure: " +
                exception.getMessage()
            );
        }
    }

    private static void printFindings(List<Finding> findings) {
        if (findings.isEmpty()) {
            System.out.println("  No violation detected.");
            return;
        }

        findings.forEach(finding ->
            System.out.println(
                "  [" + finding.normalForm() + "] " +
                finding.type() + ": " +
                finding.message()
            )
        );
    }
}
