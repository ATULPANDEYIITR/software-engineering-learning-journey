import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Consumer;
import java.util.stream.Collectors;

/**
 * Behavior-Driven Development
 *
 * Enterprise acceptance testing for an order management system.
 *
 * Run:
 * javac BehaviorDrivenDevelopment.java
 * java BehaviorDrivenDevelopment
 */
public class BehaviorDrivenDevelopment {

    // ========================================================
    // 1. Domain types
    // ========================================================

    enum OrderStatus {
        PENDING,
        CONFIRMED,
        REJECTED
    }

    enum StepKeyword {
        GIVEN,
        WHEN,
        THEN,
        AND
    }

    enum ScenarioStatus {
        PASSED,
        FAILED
    }

    record Product(
        String id,
        String name,
        BigDecimal price,
        int stock
    ) {
        Product {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException("Product ID is required");
            }

            if (price == null || price.signum() <= 0) {
                throw new IllegalArgumentException("Invalid product price");
            }

            if (stock < 0) {
                throw new IllegalArgumentException("Stock cannot be negative");
            }
        }
    }

    record Order(
        String id,
        String productId,
        int quantity,
        BigDecimal total,
        OrderStatus status
    ) {}

    record ScenarioResult(
        String scenarioName,
        ScenarioStatus status,
        Duration duration,
        String error
    ) {}

    // ========================================================
    // 2. Custom exceptions
    // ========================================================

    static class BusinessRuleException extends RuntimeException {
        BusinessRuleException(String message) {
            super(message);
        }
    }

    static class AcceptanceTestException extends RuntimeException {
        AcceptanceTestException(String message) {
            super(message);
        }
    }

    // ========================================================
    // 3. Test context
    // ========================================================

    static class TestContext {

        final Map<String, Product> products = new HashMap<>();
        final List<Order> orders = new ArrayList<>();
        final List<String> events = new ArrayList<>();

        boolean authenticated = true;
        boolean paymentApproved = true;

        void addProduct(Product product) {
            if (products.putIfAbsent(product.id(), product) != null) {
                throw new BusinessRuleException("Duplicate product");
            }
        }

        Product getProduct(String id) {
            Product product = products.get(id);

            if (product == null) {
                throw new BusinessRuleException("Product not found");
            }

            return product;
        }

        void updateStock(String id, int newStock) {
            Product old = getProduct(id);

            products.put(
                id,
                new Product(
                    old.id(),
                    old.name(),
                    old.price(),
                    newStock
                )
            );
        }
    }

    // ========================================================
    // 4. Enterprise service layer
    // ========================================================

    interface PaymentGateway {
        boolean authorize(String customerId, BigDecimal amount);
    }

    static class SimulatedPaymentGateway implements PaymentGateway {

        private final Set<String> rejectedCustomers;

        SimulatedPaymentGateway(Set<String> rejectedCustomers) {
            this.rejectedCustomers = Set.copyOf(rejectedCustomers);
        }

        @Override
        public boolean authorize(String customerId, BigDecimal amount) {
            return !rejectedCustomers.contains(customerId);
        }
    }

    static class OrderService {

        private final PaymentGateway paymentGateway;
        private final BigDecimal taxRate;

        OrderService(
            PaymentGateway paymentGateway,
            BigDecimal taxRate
        ) {
            if (taxRate == null ||
                taxRate.signum() < 0 ||
                taxRate.compareTo(BigDecimal.ONE) > 0) {
                throw new IllegalArgumentException("Invalid tax rate");
            }

            this.paymentGateway = paymentGateway;
            this.taxRate = taxRate;
        }

        BigDecimal calculateTotal(Product product, int quantity) {

            if (quantity <= 0) {
                throw new BusinessRuleException(
                    "Quantity must be positive"
                );
            }

            return product.price()
                .multiply(BigDecimal.valueOf(quantity))
                .multiply(BigDecimal.ONE.add(taxRate))
                .setScale(2, RoundingMode.HALF_UP);
        }

        Order placeOrder(
            TestContext context,
            String customerId,
            String productId,
            int quantity
        ) {

            if (!context.authenticated) {
                throw new BusinessRuleException(
                    "Customer authentication required"
                );
            }

            if (customerId == null || customerId.isBlank()) {
                throw new BusinessRuleException("Invalid customer");
            }

            if (quantity <= 0) {
                throw new BusinessRuleException("Invalid quantity");
            }

            Product product = context.getProduct(productId);

            if (product.stock() < quantity) {
                throw new BusinessRuleException(
                    "Insufficient inventory"
                );
            }

            BigDecimal total = calculateTotal(product, quantity);

            if (!context.paymentApproved ||
                !paymentGateway.authorize(customerId, total)) {
                throw new BusinessRuleException(
                    "Payment authorization failed"
                );
            }

            // State transition occurs only after successful validation
            // and payment authorization.
            context.updateStock(
                productId,
                product.stock() - quantity
            );

            Order order = new Order(
                "ORD-" + (context.orders.size() + 1),
                productId,
                quantity,
                total,
                OrderStatus.CONFIRMED
            );

            context.orders.add(order);

            context.events.add(
                "OrderConfirmed:" + order.id()
            );

            return order;
        }
    }

    // ========================================================
    // 5. Acceptance policy
    // ========================================================

    interface AcceptancePolicy {
        void validate(TestContext context);
    }

    static class OrderConfirmationPolicy implements AcceptancePolicy {

        @Override
        public void validate(TestContext context) {

            if (context.orders.isEmpty()) {
                throw new AcceptanceTestException(
                    "No confirmed order exists"
                );
            }

            if (context.orders.stream().noneMatch(
                order -> order.status() == OrderStatus.CONFIRMED
            )) {
                throw new AcceptanceTestException(
                    "No order satisfies confirmation policy"
                );
            }
        }
    }

    // ========================================================
    // 6. BDD step model
    // ========================================================

    record BDDStep(
        StepKeyword keyword,
        String description,
        Consumer<TestContext> action
    ) {
        BDDStep {
            if (keyword == null ||
                description == null ||
                description.isBlank() ||
                action == null) {
                throw new IllegalArgumentException("Invalid BDD step");
            }
        }
    }

    static class Scenario {

        private final String name;
        private final String description;
        private final List<BDDStep> steps = new ArrayList<>();

        Scenario(String name, String description) {
            this.name = name;
            this.description = description;
        }

        Scenario add(
            StepKeyword keyword,
            String description,
            Consumer<TestContext> action
        ) {
            steps.add(new BDDStep(keyword, description, action));
            return this;
        }

        String name() {
            return name;
        }

        List<BDDStep> steps() {
            return Collections.unmodifiableList(steps);
        }
    }

    static class Feature {

        private final String name;
        private final List<Scenario> scenarios = new ArrayList<>();

        Feature(String name) {
            this.name = name;
        }

        Feature add(Scenario scenario) {
            scenarios.add(scenario);
            return this;
        }

        String name() {
            return name;
        }

        List<Scenario> scenarios() {
            return Collections.unmodifiableList(scenarios);
        }
    }

    // ========================================================
    // 7. BDD runner
    // ========================================================

    static class BDDRunner {

        private final AcceptancePolicy policy;

        BDDRunner(AcceptancePolicy policy) {
            this.policy = policy;
        }

        ScenarioResult run(Scenario scenario) {

            TestContext context = new TestContext();

            Instant start = Instant.now();

            try {
                for (BDDStep step : scenario.steps()) {
                    step.action().accept(context);
                }

                Instant end = Instant.now();

                return new ScenarioResult(
                    scenario.name(),
                    ScenarioStatus.PASSED,
                    Duration.between(start, end),
                    null
                );

            } catch (RuntimeException exception) {

                Instant end = Instant.now();

                return new ScenarioResult(
                    scenario.name(),
                    ScenarioStatus.FAILED,
                    Duration.between(start, end),
                    exception.getMessage()
                );
            }
        }

        List<ScenarioResult> runFeature(Feature feature) {

            System.out.println("\nFeature: " + feature.name());

            List<ScenarioResult> results = feature.scenarios()
                .stream()
                .map(this::run)
                .collect(Collectors.toList());

            results.forEach(result -> {
                System.out.printf(
                    "[%s] %s (%d ms)%n",
                    result.status(),
                    result.scenarioName(),
                    result.duration().toMillis()
                );

                if (result.error() != null) {
                    System.out.println("  Error: " + result.error());
                }
            });

            return results;
        }
    }

    // ========================================================
    // 8. Step definitions
    // ========================================================

    static BDDStep productExists(
        String id,
        String price,
        int stock
    ) {
        return new BDDStep(
            StepKeyword.GIVEN,
            "Product is available",
            context -> context.addProduct(
                new Product(
                    id,
                    "Wireless Keyboard",
                    new BigDecimal(price),
                    stock
                )
            )
        );
    }

    static BDDStep customerAuthenticated(boolean authenticated) {
        return new BDDStep(
            StepKeyword.GIVEN,
            "Customer authentication state",
            context -> context.authenticated = authenticated
        );
    }

    static BDDStep paymentApproved(boolean approved) {
        return new BDDStep(
            StepKeyword.GIVEN,
            "Payment authorization state",
            context -> context.paymentApproved = approved
        );
    }

    static BDDStep customerPlacesOrder(
        OrderService service,
        String customerId,
        String productId,
        int quantity
    ) {
        return new BDDStep(
            StepKeyword.WHEN,
            "Customer submits an order",
            context -> service.placeOrder(
                context,
                customerId,
                productId,
                quantity
            )
        );
    }

    static BDDStep orderIsConfirmed(AcceptancePolicy policy) {
        return new BDDStep(
            StepKeyword.THEN,
            "Order satisfies confirmation policy",
            policy::validate
        );
    }

    static BDDStep stockEquals(String productId, int expected) {
        return new BDDStep(
            StepKeyword.THEN,
            "Inventory has expected quantity",
            context -> {
                int actual = context.getProduct(productId).stock();

                if (actual != expected) {
                    throw new AcceptanceTestException(
                        "Expected stock " + expected + ", found " + actual
                    );
                }
            }
        );
    }

    static BDDStep orderIsRejected() {
        return new BDDStep(
            StepKeyword.THEN,
            "No order is created",
            context -> {
                if (!context.orders.isEmpty()) {
                    throw new AcceptanceTestException(
                        "Unexpected order creation"
                    );
                }
            }
        );
    }

    // ========================================================
    // 9. Feature construction
    // ========================================================

    static Feature buildFeature(
        OrderService service,
        AcceptancePolicy policy
    ) {

        Feature feature = new Feature("Enterprise order acceptance");

        feature.add(
            new Scenario(
                "Successful order placement",
                "Authenticated customer purchases available stock."
            )
                .add(
                    StepKeyword.GIVEN,
                    "Product exists",
                    productExists("KB-101", "1000.00", 10).action()
                )
                .add(
                    StepKeyword.AND,
                    "Customer is authenticated",
                    customerAuthenticated(true).action()
                )
                .add(
                    StepKeyword.WHEN,
                    "Customer purchases two units",
                    customerPlacesOrder(
                        service,
                        "CUS-101",
                        "KB-101",
                        2
                    ).action()
                )
                .add(
                    StepKeyword.THEN,
                    "Order is confirmed",
                    orderIsConfirmed(policy).action()
                )
                .add(
                    StepKeyword.AND,
                    "Stock is reduced",
                    stockEquals("KB-101", 8).action()
                )
        );

        feature.add(
            new Scenario(
                "Insufficient inventory",
                "Requested quantity exceeds available inventory."
            )
                .add(
                    StepKeyword.GIVEN,
                    "Only two units are available",
                    productExists("KB-101", "1000.00", 2).action()
                )
                .add(
                    StepKeyword.WHEN,
                    "Customer requests five units",
                    customerPlacesOrder(
                        service,
                        "CUS-102",
                        "KB-101",
                        5
                    ).action()
                )
                .add(
                    StepKeyword.THEN,
                    "Inventory restriction rejects the order",
                    context -> {
                        if (context.errors.size() != 0) {
                            throw new AcceptanceTestException(
                                "Unexpected error state"
                            );
                        }
                    }
                )
        );

        feature.add(
            new Scenario(
                "Unauthenticated customer",
                "An unauthenticated customer cannot order."
            )
                .add(
                    StepKeyword.GIVEN,
                    "Product exists",
                    productExists("KB-101", "1000.00", 10).action()
                )
                .add(
                    StepKeyword.AND,
                    "Customer is unauthenticated",
                    customerAuthenticated(false).action()
                )
                .add(
                    StepKeyword.WHEN,
                    "Customer attempts purchase",
                    customerPlacesOrder(
                        service,
                        "CUS-103",
                        "KB-101",
                        1
                    ).action()
                )
                .add(
                    StepKeyword.THEN,
                    "No order is created",
                    orderIsRejected().action()
                )
                .add(
                    StepKeyword.AND,
                    "Inventory remains unchanged",
                    stockEquals("KB-101", 10).action()
                )
        );

        feature.add(
            new Scenario(
                "Payment failure",
                "Payment rejection prevents inventory reservation."
            )
                .add(
                    StepKeyword.GIVEN,
                    "Product exists",
                    productExists("KB-101", "1000.00", 10).action()
                )
                .add(
                    StepKeyword.GIVEN,
                    "Payment is rejected",
                    paymentApproved(false).action()
                )
                .add(
                    StepKeyword.WHEN,
                    "Customer attempts purchase",
                    customerPlacesOrder(
                        service,
                        "CUS-104",
                        "KB-101",
                        1
                    ).action()
                )
                .add(
                    StepKeyword.THEN,
                    "No order is created",
                    orderIsRejected().action()
                )
                .add(
                    StepKeyword.AND,
                    "Inventory remains unchanged",
                    stockEquals("KB-101", 10).action()
                )
        );

        return feature;
    }

    // ========================================================
    // 10. Data-driven scenario outline
    // ========================================================

    static void runScenarioOutline(OrderService service) {

        System.out.println("\nScenario Outline: Order quantity examples");

        record Example(int quantity, int stock, String expected) {}

        List<Example> examples = List.of(
            new Example(1, 5, "1100.00"),
            new Example(2, 5, "2200.00"),
            new Example(3, 5, "3300.00")
        );

        for (Example example : examples) {

            TestContext context = new TestContext();

            context.addProduct(
                new Product(
                    "KB-101",
                    "Wireless Keyboard",
                    new BigDecimal("1000.00"),
                    example.stock()
                )
            );

            Order order = service.placeOrder(
                context,
                "CUS-105",
                "KB-101",
                example.quantity()
            );

            BigDecimal expected = new BigDecimal(example.expected());

            if (order.total().compareTo(expected) != 0) {
                throw new AcceptanceTestException(
                    "Scenario outline failed"
                );
            }

            System.out.printf(
                "[PASSED] Quantity: %d, Total: %s%n",
                example.quantity(),
                order.total()
            );
        }
    }

    // ========================================================
    // 11. Main
    // ========================================================

    public static void main(String[] args) {

        Set<String> rejectedCustomers = new HashSet<>();

        PaymentGateway gateway =
            new SimulatedPaymentGateway(rejectedCustomers);

        OrderService service = new OrderService(
            gateway,
            new BigDecimal("0.10")
        );

        AcceptancePolicy policy = new OrderConfirmationPolicy();

        Feature feature = buildFeature(service, policy);

        BDDRunner runner = new BDDRunner(policy);

        List<ScenarioResult> results = runner.runFeature(feature);

        runScenarioOutline(service);

        long passed = results.stream()
            .filter(r -> r.status() == ScenarioStatus.PASSED)
            .count();

        long failed = results.size() - passed;

        System.out.println("\nAcceptance Test Report");
        System.out.println("Total: " + results.size());
        System.out.println("Passed: " + passed);
        System.out.println("Failed: " + failed);

        if (failed > 0) {
            System.exit(1);
        }
    }
}
