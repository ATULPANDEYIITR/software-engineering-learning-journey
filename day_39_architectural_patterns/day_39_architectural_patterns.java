import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/*
 * Architectural Patterns: Layered, MVC, and Hexagonal
 *
 * Enterprise scenario:
 * An order-processing capability is implemented three ways so that
 * architectural boundaries can be compared without changing the
 * underlying business rules.
 *
 * Compile:
 *   javac ArchitecturePatterns.java
 *
 * Run:
 *   java ArchitecturePatterns
 */
public class ArchitecturePatterns {

    // ============================================================
    // Shared domain
    // ============================================================

    enum OrderStatus {
        PENDING,
        CONFIRMED,
        CANCELLED
    }

    record OrderItem(
        String productId,
        int quantity,
        double unitPrice
    ) {
        OrderItem {
            if (productId == null || productId.isBlank()) {
                throw new DomainException("Product ID is required.");
            }

            if (quantity <= 0) {
                throw new DomainException(
                    "Quantity must be positive."
                );
            }

            if (!Double.isFinite(unitPrice) || unitPrice < 0) {
                throw new DomainException(
                    "Unit price must be finite and non-negative."
                );
            }
        }

        double subtotal() {
            return quantity * unitPrice;
        }
    }

    static final class DomainException extends RuntimeException {
        DomainException(String message) {
            super(message);
        }
    }

    static final class Order {
        private final String id;
        private final String customerId;
        private final List<OrderItem> items;
        private OrderStatus status;

        Order(
            String id,
            String customerId,
            List<OrderItem> items
        ) {
            if (id == null || id.isBlank()) {
                throw new DomainException("Order ID is required.");
            }

            if (customerId == null || customerId.isBlank()) {
                throw new DomainException("Customer ID is required.");
            }

            if (items == null || items.isEmpty()) {
                throw new DomainException(
                    "An order must contain at least one item."
                );
            }

            this.id = id;
            this.customerId = customerId;
            this.items = List.copyOf(items);
            this.status = OrderStatus.PENDING;
        }

        void confirm() {
            if (status != OrderStatus.PENDING) {
                throw new DomainException(
                    "Only pending orders can be confirmed."
                );
            }

            status = OrderStatus.CONFIRMED;
        }

        void cancel() {
            if (status != OrderStatus.PENDING) {
                throw new DomainException(
                    "Only pending orders can be cancelled."
                );
            }

            status = OrderStatus.CANCELLED;
        }

        String id() {
            return id;
        }

        String customerId() {
            return customerId;
        }

        List<OrderItem> items() {
            return Collections.unmodifiableList(items);
        }

        OrderStatus status() {
            return status;
        }

        double total() {
            return Math.round(
                items.stream()
                    .mapToDouble(OrderItem::subtotal)
                    .sum() * 100.0
            ) / 100.0;
        }
    }


    // ============================================================
    // LAYERED ARCHITECTURE
    // ============================================================
    //
    // Presentation -> Application -> Domain -> Infrastructure
    //
    // This implementation favors a conventional enterprise
    // structure. The application service coordinates concrete
    // infrastructure collaborators.
    // ============================================================

    static final class LayeredRepository {
        private final Map<String, Order> orders = new HashMap<>();

        void save(Order order) {
            orders.put(order.id(), order);
        }

        Optional<Order> findById(String id) {
            return Optional.ofNullable(orders.get(id));
        }
    }

    static final class LayeredNotificationService {
        void sendConfirmation(Order order) {
            System.out.printf(
                "[Layered notification] %s confirmed for %s%n",
                order.id(),
                order.customerId()
            );
        }
    }

    static final class LayeredOrderService {
        private final LayeredRepository repository;
        private final LayeredNotificationService notification;
        private int sequence = 1000;

        LayeredOrderService(
            LayeredRepository repository,
            LayeredNotificationService notification
        ) {
            this.repository = repository;
            this.notification = notification;
        }

        Order createOrder(
            String customerId,
            List<OrderItem> items
        ) {
            Order order = new Order(
                "LAYER-" + sequence++,
                customerId,
                items
            );

            order.confirm();
            repository.save(order);
            notification.sendConfirmation(order);

            return order;
        }
    }


    // ============================================================
    // MVC ARCHITECTURE
    // ============================================================
    //
    // Controller -> Model -> View interaction is coordinated without
    // allowing the view to own business state transitions.
    // ============================================================

    static final class OrderModel {
        private final Map<String, Order> orders = new HashMap<>();
        private int sequence = 2000;

        Order create(
            String customerId,
            List<OrderItem> items
        ) {
            Order order = new Order(
                "MVC-" + sequence++,
                customerId,
                items
            );

            order.confirm();
            orders.put(order.id(), order);
            return order;
        }

        Optional<Order> find(String id) {
            return Optional.ofNullable(orders.get(id));
        }
    }

    static final class OrderView {
        String render(Order order) {
            if (order == null) {
                return "Order not found.";
            }

            StringBuilder output = new StringBuilder();

            output.append("Order: ")
                .append(order.id())
                .append(System.lineSeparator());

            output.append("Customer: ")
                .append(order.customerId())
                .append(System.lineSeparator());

            output.append("Status: ")
                .append(order.status())
                .append(System.lineSeparator());

            output.append("Total: ")
                .append(String.format("%.2f", order.total()));

            return output.toString();
        }

        String renderError(String message) {
            return "Order error: " + message;
        }
    }

    static final class OrderController {
        private final OrderModel model;
        private final OrderView view;

        OrderController(
            OrderModel model,
            OrderView view
        ) {
            this.model = model;
            this.view = view;
        }

        String create(
            String customerId,
            List<OrderItem> items
        ) {
            try {
                Order order = model.create(customerId, items);
                return view.render(order);
            } catch (DomainException exception) {
                return view.renderError(exception.getMessage());
            }
        }
    }


    // ============================================================
    // HEXAGONAL ARCHITECTURE
    // ============================================================
    //
    // Application core
    //       ^
    //       |
    //   ports/interfaces
    //       ^
    //       |
    // adapters
    //
    // The core depends on interfaces. Infrastructure classes depend
    // on those interfaces. This reverses the usual concrete
    // infrastructure dependency and makes the core easier to test.
    // ============================================================

    interface OrderRepositoryPort {
        void save(Order order);

        Optional<Order> findById(String id);
    }

    interface NotificationPort {
        void sendConfirmation(Order order);
    }

    static final class MemoryOrderAdapter
        implements OrderRepositoryPort {

        private final Map<String, Order> store = new HashMap<>();

        @Override
        public void save(Order order) {
            store.put(order.id(), order);
        }

        @Override
        public Optional<Order> findById(String id) {
            return Optional.ofNullable(store.get(id));
        }
    }

    static final class ConsoleNotificationAdapter
        implements NotificationPort {

        @Override
        public void sendConfirmation(Order order) {
            System.out.printf(
                "[Hexagonal notification] %s confirmed for %s%n",
                order.id(),
                order.customerId()
            );
        }
    }

    static final class RecordingNotificationAdapter
        implements NotificationPort {

        private final List<String> confirmedOrderIds =
            new ArrayList<>();

        @Override
        public void sendConfirmation(Order order) {
            confirmedOrderIds.add(order.id());
        }

        List<String> confirmedOrderIds() {
            return List.copyOf(confirmedOrderIds);
        }
    }

    static final class OrderApplication {
        private final OrderRepositoryPort repository;
        private final NotificationPort notification;
        private int sequence = 3000;

        OrderApplication(
            OrderRepositoryPort repository,
            NotificationPort notification
        ) {
            this.repository = Objects.requireNonNull(repository);
            this.notification = Objects.requireNonNull(notification);
        }

        Order placeOrder(
            String customerId,
            List<OrderItem> items
        ) {
            Order order = new Order(
                "HEX-" + sequence++,
                customerId,
                items
            );

            order.confirm();
            repository.save(order);
            notification.sendConfirmation(order);

            return order;
        }
    }


    // ============================================================
    // Test the application core using only ports and test adapters
    // ============================================================

    static void testHexagonalCore() {
        MemoryOrderAdapter repository = new MemoryOrderAdapter();
        RecordingNotificationAdapter notification =
            new RecordingNotificationAdapter();

        OrderApplication application =
            new OrderApplication(repository, notification);

        Order order = application.placeOrder(
            "TEST-CUSTOMER",
            List.of(
                new OrderItem("SERVER", 1, 1500.00),
                new OrderItem("SSD", 2, 180.00)
            )
        );

        if (Math.abs(order.total() - 1860.00) > 0.0001) {
            throw new IllegalStateException(
                "Unexpected order total."
            );
        }

        if (notification.confirmedOrderIds().size() != 1) {
            throw new IllegalStateException(
                "Expected one confirmation."
            );
        }

        if (repository.findById(order.id()).isEmpty()) {
            throw new IllegalStateException(
                "Order was not persisted."
            );
        }

        System.out.println("[Test] Hexagonal core test passed.");
    }


    // ============================================================
    // Enterprise-oriented policy validation
    // ============================================================
    //
    // This demonstrates that architectural structure does not replace
    // domain policy. The policy remains an explicit business concern.
    // ============================================================

    static final class OrderPolicy {
        private static final double MAX_SINGLE_ORDER_VALUE = 10_000.00;

        void validate(Order order) {
            if (order.total() > MAX_SINGLE_ORDER_VALUE) {
                throw new DomainException(
                    "Order exceeds the permitted transaction value."
                );
            }
        }
    }


    static void demonstrateArchitectures() {
        System.out.println("=== Layered Architecture ===");

        LayeredRepository layeredRepository =
            new LayeredRepository();

        LayeredNotificationService layeredNotification =
            new LayeredNotificationService();

        LayeredOrderService layeredService =
            new LayeredOrderService(
                layeredRepository,
                layeredNotification
            );

        Order layeredOrder = layeredService.createOrder(
            "CUST-LAYER",
            List.of(
                new OrderItem("KEYBOARD", 2, 75.00),
                new OrderItem("MOUSE", 1, 40.00)
            )
        );

        System.out.printf(
            "Layered total: %.2f%n%n",
            layeredOrder.total()
        );


        System.out.println("=== MVC Architecture ===");

        OrderModel model = new OrderModel();
        OrderView view = new OrderView();
        OrderController controller =
            new OrderController(model, view);

        System.out.println(
            controller.create(
                "CUST-MVC",
                List.of(
                    new OrderItem("MONITOR", 1, 300.00),
                    new OrderItem("CABLE", 3, 12.50)
                )
            )
        );


        System.out.println("\n=== Hexagonal Architecture ===");

        MemoryOrderAdapter repository =
            new MemoryOrderAdapter();

        ConsoleNotificationAdapter notification =
            new ConsoleNotificationAdapter();

        OrderApplication application =
            new OrderApplication(
                repository,
                notification
            );

        Order hexagonalOrder = application.placeOrder(
            "CUST-HEX",
            List.of(
                new OrderItem("API-GATEWAY", 1, 500.00),
                new OrderItem("CACHE", 2, 125.00)
            )
        );

        System.out.printf(
            "Hexagonal total: %.2f%n",
            hexagonalOrder.total()
        );


        System.out.println("\n=== Policy Validation ===");

        OrderPolicy policy = new OrderPolicy();
        policy.validate(hexagonalOrder);
        System.out.println("Valid transaction accepted.");

        try {
            Order expensiveOrder = new Order(
                "POLICY-FAIL",
                "CUST-POLICY",
                List.of(
                    new OrderItem(
                        "ENTERPRISE-SERVER",
                        2,
                        6000.00
                    )
                )
            );

            expensiveOrder.confirm();
            policy.validate(expensiveOrder);
        } catch (DomainException exception) {
            System.out.println(
                "Policy rejected transaction: "
                    + exception.getMessage()
            );
        }


        System.out.println("\n=== Invalid State ===");

        try {
            Order order = new Order(
                "STATE-FAIL",
                "CUST-STATE",
                List.of(
                    new OrderItem("BOOK", 1, 25.00)
                )
            );

            order.confirm();
            order.confirm();
        } catch (DomainException exception) {
            System.out.println(
                "Invalid transition rejected: "
                    + exception.getMessage()
            );
        }


        System.out.println("\n=== Port Isolation Test ===");
        testHexagonalCore();


        System.out.println("\n=== Architectural Distinction ===");
        System.out.println(
            "Layered architecture organizes responsibilities into layers."
        );
        System.out.println(
            "MVC separates controller coordination, model state, and view rendering."
        );
        System.out.println(
            "Hexagonal architecture isolates the core behind ports and adapters."
        );
    }


    public static void main(String[] args) {
        demonstrateArchitectures();
    }
}
