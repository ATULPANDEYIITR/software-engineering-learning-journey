import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.function.Function;

/*
 * Dependency Injection in Java
 *
 * Enterprise-oriented order processing model demonstrating:
 * - dependency contracts through interfaces
 * - constructor injection
 * - explicit service boundaries
 * - policy injection
 * - dependency lifetimes
 * - validation and domain exceptions
 * - test doubles
 * - a small type-safe container
 *
 * Compile:
 *   javac DependencyInjectionDemo.java
 *
 * Run:
 *   java DependencyInjectionDemo
 */

public class DependencyInjectionDemo {

    // -------------------------------------------------------------------------
    // Domain types
    // -------------------------------------------------------------------------

    public record Order(String id, String customerEmail, double amount) {
        public Order {
            if (id == null || id.isBlank()) {
                throw new IllegalArgumentException("Order ID is required");
            }

            if (customerEmail == null || !customerEmail.contains("@")) {
                throw new IllegalArgumentException("Invalid customer email");
            }

            if (amount <= 0) {
                throw new IllegalArgumentException(
                    "Order amount must be greater than zero"
                );
            }
        }
    }

    public record Receipt(String orderId, double amount, String message) {}

    // -------------------------------------------------------------------------
    // Explicit application exceptions
    // -------------------------------------------------------------------------

    public static class OrderProcessingException extends Exception {
        public OrderProcessingException(String message) {
            super(message);
        }
    }

    // -------------------------------------------------------------------------
    // Dependency contracts
    // -------------------------------------------------------------------------

    public interface OrderRepository {
        void save(Order order);

        Optional<Order> find(String orderId);
    }

    public interface PaymentGateway {
        boolean charge(Order order);
    }

    public interface NotificationService {
        void send(Order order, Receipt receipt);
    }

    // -------------------------------------------------------------------------
    // Infrastructure implementations
    // -------------------------------------------------------------------------

    public static final class InMemoryOrderRepository
            implements OrderRepository {

        private final Map<String, Order> orders = new HashMap<>();

        @Override
        public void save(Order order) {
            Objects.requireNonNull(order, "order");

            if (orders.putIfAbsent(order.id(), order) != null) {
                throw new IllegalStateException(
                    "Duplicate order: " + order.id()
                );
            }
        }

        @Override
        public Optional<Order> find(String orderId) {
            return Optional.ofNullable(orders.get(orderId));
        }
    }

    public static final class SimulatedPaymentGateway
            implements PaymentGateway {

        private final boolean available;
        private final List<String> chargedOrders = new ArrayList<>();

        public SimulatedPaymentGateway(boolean available) {
            this.available = available;
        }

        @Override
        public boolean charge(Order order) {
            if (!available) {
                return false;
            }

            chargedOrders.add(order.id());
            return true;
        }

        public List<String> chargedOrders() {
            return List.copyOf(chargedOrders);
        }
    }

    public static final class ConsoleNotificationService
            implements NotificationService {

        @Override
        public void send(Order order, Receipt receipt) {
            System.out.println(
                "Notification to " + order.customerEmail()
                    + ": " + receipt.message()
            );
        }
    }

    // -------------------------------------------------------------------------
    // Application service
    // -------------------------------------------------------------------------

    public static final class OrderService {

        private final OrderRepository repository;
        private final PaymentGateway paymentGateway;
        private final NotificationService notificationService;

        /*
         * Constructor injection makes dependencies mandatory and immutable.
         * The service can therefore be instantiated with production adapters
         * or test doubles without changing business logic.
         */
        public OrderService(
                OrderRepository repository,
                PaymentGateway paymentGateway,
                NotificationService notificationService) {

            this.repository = Objects.requireNonNull(repository);
            this.paymentGateway = Objects.requireNonNull(paymentGateway);
            this.notificationService =
                Objects.requireNonNull(notificationService);
        }

        public Receipt placeOrder(Order order)
                throws OrderProcessingException {

            Objects.requireNonNull(order, "order");

            if (repository.find(order.id()).isPresent()) {
                throw new OrderProcessingException(
                    "Order already exists: " + order.id()
                );
            }

            if (!paymentGateway.charge(order)) {
                throw new OrderProcessingException(
                    "Payment was declined or unavailable"
                );
            }

            repository.save(order);

            Receipt receipt = new Receipt(
                order.id(),
                order.amount(),
                "Order " + order.id()
                    + " paid successfully for $"
                    + String.format("%.2f", order.amount())
            );

            notificationService.send(order, receipt);

            return receipt;
        }
    }

    // -------------------------------------------------------------------------
    // Policy injection
    // -------------------------------------------------------------------------

    public static final class PricingService {

        private final Function<Double, Double> taxPolicy;

        public PricingService(Function<Double, Double> taxPolicy) {
            this.taxPolicy = Objects.requireNonNull(taxPolicy);
        }

        public double total(double amount) {
            if (amount < 0) {
                throw new IllegalArgumentException(
                    "Amount cannot be negative"
                );
            }

            return amount + taxPolicy.apply(amount);
        }
    }

    // -------------------------------------------------------------------------
    // Type-safe dependency container
    // -------------------------------------------------------------------------

    public static final class Container {

        private final Map<Class<?>, Provider<?>> providers = new HashMap<>();

        public <T> void singleton(
                Class<T> type,
                Provider<T> provider) {

            providers.put(type, new SingletonProvider<>(provider));
        }

        public <T> void transientDependency(
                Class<T> type,
                Provider<T> provider) {

            providers.put(type, provider);
        }

        public <T> T resolve(Class<T> type) {
            Provider<?> provider = providers.get(type);

            if (provider == null) {
                throw new IllegalStateException(
                    "No provider registered for " + type.getName()
                );
            }

            return type.cast(provider.get());
        }
    }

    @FunctionalInterface
    public interface Provider<T> {
        T get();
    }

    private static final class SingletonProvider<T>
            implements Provider<T> {

        private final Provider<T> factory;
        private T instance;

        private SingletonProvider(Provider<T> factory) {
            this.factory = factory;
        }

        @Override
        public synchronized T get() {
            if (instance == null) {
                instance = factory.get();
            }

            return instance;
        }
    }

    // -------------------------------------------------------------------------
    // Test doubles
    // -------------------------------------------------------------------------

    public static final class FakePaymentGateway
            implements PaymentGateway {

        private final boolean result;
        private final List<String> calls = new ArrayList<>();

        public FakePaymentGateway(boolean result) {
            this.result = result;
        }

        @Override
        public boolean charge(Order order) {
            calls.add(order.id());
            return result;
        }

        public List<String> calls() {
            return List.copyOf(calls);
        }
    }

    public static final class FakeNotificationService
            implements NotificationService {

        private final List<String> calls = new ArrayList<>();

        @Override
        public void send(Order order, Receipt receipt) {
            calls.add(order.id());
        }

        public List<String> calls() {
            return List.copyOf(calls);
        }
    }

    // -------------------------------------------------------------------------
    // Tests
    // -------------------------------------------------------------------------

    private static void testSuccessfulOrder() throws Exception {
        InMemoryOrderRepository repository =
            new InMemoryOrderRepository();

        FakePaymentGateway payment =
            new FakePaymentGateway(true);

        FakeNotificationService notification =
            new FakeNotificationService();

        OrderService service =
            new OrderService(repository, payment, notification);

        Order order =
            new Order("JAVA-001", "buyer@example.com", 250.0);

        Receipt receipt = service.placeOrder(order);

        assert receipt.orderId().equals("JAVA-001");
        assert repository.find("JAVA-001").isPresent();
        assert payment.calls().size() == 1;
        assert notification.calls().size() == 1;
    }

    private static void testPaymentFailure() {
        InMemoryOrderRepository repository =
            new InMemoryOrderRepository();

        FakePaymentGateway payment =
            new FakePaymentGateway(false);

        FakeNotificationService notification =
            new FakeNotificationService();

        OrderService service =
            new OrderService(repository, payment, notification);

        Order order =
            new Order("JAVA-002", "buyer@example.com", 300.0);

        try {
            service.placeOrder(order);
            throw new AssertionError("Expected payment failure");
        } catch (OrderProcessingException exception) {
            assert exception.getMessage().contains("Payment");
        }

        assert repository.find("JAVA-002").isEmpty();
        assert notification.calls().isEmpty();
    }

    private static void testDuplicateOrder() throws Exception {
        InMemoryOrderRepository repository =
            new InMemoryOrderRepository();

        Order existing =
            new Order("JAVA-003", "existing@example.com", 50.0);

        repository.save(existing);

        FakePaymentGateway payment =
            new FakePaymentGateway(true);

        FakeNotificationService notification =
            new FakeNotificationService();

        OrderService service =
            new OrderService(repository, payment, notification);

        try {
            service.placeOrder(existing);
            throw new AssertionError("Expected duplicate-order failure");
        } catch (OrderProcessingException exception) {
            assert exception.getMessage().contains("already exists");
        }

        assert payment.calls().isEmpty();
    }

    private static void testContainerLifetime() {
        Container container = new Container();

        container.singleton(
            OrderRepository.class,
            InMemoryOrderRepository::new
        );

        container.transientDependency(
            PaymentGateway.class,
            () -> new SimulatedPaymentGateway(true)
        );

        assert container.resolve(OrderRepository.class)
            == container.resolve(OrderRepository.class);

        assert container.resolve(PaymentGateway.class)
            != container.resolve(PaymentGateway.class);
    }

    private static void testPolicyInjection() {
        PricingService standard =
            new PricingService(amount -> amount * 0.18);

        PricingService exempt =
            new PricingService(amount -> 0.0);

        assert Math.abs(standard.total(100.0) - 118.0) < 0.0001;
        assert Math.abs(exempt.total(100.0) - 100.0) < 0.0001;
    }

    // -------------------------------------------------------------------------
    // Composition root
    // -------------------------------------------------------------------------

    private static Container buildProductionContainer() {
        Container container = new Container();

        container.singleton(
            OrderRepository.class,
            InMemoryOrderRepository::new
        );

        container.transientDependency(
            PaymentGateway.class,
            () -> new SimulatedPaymentGateway(true)
        );

        container.singleton(
            NotificationService.class,
            ConsoleNotificationService::new
        );

        container.singleton(
            OrderService.class,
            () -> new OrderService(
                container.resolve(OrderRepository.class),
                container.resolve(PaymentGateway.class),
                container.resolve(NotificationService.class)
            )
        );

        return container;
    }

    public static void main(String[] args) throws Exception {
        System.out.println("Dependency Injection in Java\n");

        Container container = buildProductionContainer();

        OrderService service =
            container.resolve(OrderService.class);

        Receipt receipt = service.placeOrder(
            new Order(
                "JAVA-PROD-001",
                "customer@example.com",
                149.99
            )
        );

        System.out.println(receipt.message());

        testSuccessfulOrder();
        testPaymentFailure();
        testDuplicateOrder();
        testContainerLifetime();
        testPolicyInjection();

        System.out.println("\nAll DI tests passed.");
        System.out.println(
            "The composition root selects implementations while "
                + "the application service depends on interfaces."
        );
    }
}
