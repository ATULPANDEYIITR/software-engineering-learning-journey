import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.Objects;

public class UnitTestingCaseStudy {

    enum OrderStatus {
        NEW, PAID, CANCELLED
    }

    static class ValidationException extends RuntimeException {
        ValidationException(String message) {
            super(message);
        }
    }

    record Product(String id, String name, BigDecimal price, int stock) {
        Product {
            if (id == null || id.isBlank()) {
                throw new ValidationException("product id is required");
            }
            if (name == null || name.isBlank()) {
                throw new ValidationException("product name is required");
            }
            if (price == null || price.compareTo(BigDecimal.ZERO) < 0) {
                throw new ValidationException("price must be non-negative");
            }
            if (stock < 0) {
                throw new ValidationException("stock must be non-negative");
            }
        }
    }

    record OrderItem(String productId, int quantity) {
        OrderItem {
            if (productId == null || productId.isBlank()) {
                throw new ValidationException("product id is required");
            }
            if (quantity <= 0) {
                throw new ValidationException("quantity must be positive");
            }
        }
    }

    static final class Order {
        private final String id;
        private final String customer;
        private final List<OrderItem> items = new ArrayList<>();
        private OrderStatus status = OrderStatus.NEW;

        Order(String id, String customer) {
            if (id == null || id.isBlank()) {
                throw new ValidationException("order id is required");
            }
            if (customer == null || customer.isBlank()) {
                throw new ValidationException("customer is required");
            }
            this.id = id;
            this.customer = customer;
        }

        void addItem(String productId, int quantity) {
            items.add(new OrderItem(productId, quantity));
        }

        String id() {
            return id;
        }

        List<OrderItem> items() {
            return List.copyOf(items);
        }

        OrderStatus status() {
            return status;
        }

        void status(OrderStatus status) {
            this.status = Objects.requireNonNull(status);
        }
    }

    static final class Inventory {
        private final Map<String, Product> products = new HashMap<>();

        Inventory(List<Product> products) {
            for (Product product : products) {
                if (this.products.putIfAbsent(product.id(), product) != null) {
                    throw new ValidationException("duplicate product: " + product.id());
                }
            }
        }

        Product get(String id) {
            Product product = products.get(id);
            if (product == null) {
                throw new ValidationException("unknown product: " + id);
            }
            return product;
        }

        void reserve(String id, int quantity) {
            Product product = get(id);

            if (quantity <= 0) {
                throw new ValidationException("quantity must be positive");
            }

            if (product.stock() < quantity) {
                throw new ValidationException("insufficient stock for " + id);
            }

            products.put(
                id,
                new Product(
                    product.id(),
                    product.name(),
                    product.price(),
                    product.stock() - quantity
                )
            );
        }

        void release(String id, int quantity) {
            Product product = get(id);

            products.put(
                id,
                new Product(
                    product.id(),
                    product.name(),
                    product.price(),
                    product.stock() + quantity
                )
            );
        }

        int stock(String id) {
            return get(id).stock();
        }
    }

    interface MergePolicy {
        boolean eligible(
            int approvals,
            boolean checksPassing,
            boolean conversationsResolved,
            boolean hasChanges
        );
    }

    static final class ProtectedBranchPolicy implements MergePolicy {
        private final int requiredApprovals;
        private final boolean requireChecks;
        private final boolean requireResolvedConversations;

        ProtectedBranchPolicy(
            int requiredApprovals,
            boolean requireChecks,
            boolean requireResolvedConversations
        ) {
            if (requiredApprovals < 0) {
                throw new ValidationException("required approvals cannot be negative");
            }
            this.requiredApprovals = requiredApprovals;
            this.requireChecks = requireChecks;
            this.requireResolvedConversations = requireResolvedConversations;
        }

        @Override
        public boolean eligible(
            int approvals,
            boolean checksPassing,
            boolean conversationsResolved,
            boolean hasChanges
        ) {
            return hasChanges
                && approvals >= requiredApprovals
                && (!requireChecks || checksPassing)
                && (!requireResolvedConversations || conversationsResolved);
        }
    }

    static final class OrderService {
        private static final BigDecimal TAX = new BigDecimal("0.18");
        private final Inventory inventory;

        OrderService(Inventory inventory) {
            this.inventory = inventory;
        }

        BigDecimal subtotal(Order order) {
            if (order.items().isEmpty()) {
                throw new ValidationException("order must contain items");
            }

            BigDecimal subtotal = BigDecimal.ZERO;

            for (OrderItem item : order.items()) {
                Product product = inventory.get(item.productId());
                subtotal = subtotal.add(
                    product.price().multiply(BigDecimal.valueOf(item.quantity()))
                );
            }

            return subtotal.setScale(2, RoundingMode.HALF_UP);
        }

        BigDecimal total(Order order) {
            return subtotal(order)
                .multiply(BigDecimal.ONE.add(TAX))
                .setScale(2, RoundingMode.HALF_UP);
        }

        BigDecimal pay(Order order) {
            if (order.status() != OrderStatus.NEW) {
                throw new ValidationException("order is not payable");
            }

            List<OrderItem> reserved = new ArrayList<>();

            try {
                for (OrderItem item : order.items()) {
                    inventory.reserve(item.productId(), item.quantity());
                    reserved.add(item);
                }
            } catch (ValidationException error) {
                for (OrderItem item : reserved) {
                    inventory.release(item.productId(), item.quantity());
                }
                throw error;
            }

            order.status(OrderStatus.PAID);
            return total(order);
        }

        void cancel(Order order) {
            if (order.status() != OrderStatus.PAID) {
                throw new ValidationException("only paid orders can be cancelled");
            }

            for (OrderItem item : order.items()) {
                inventory.release(item.productId(), item.quantity());
            }

            order.status(OrderStatus.CANCELLED);
        }
    }

    static List<Product> fixtureProducts() {
        return List.of(
            new Product("KB-01", "Mechanical Keyboard", new BigDecimal("80.00"), 10),
            new Product("MS-01", "Wireless Mouse", new BigDecimal("25.00"), 20),
            new Product("HD-01", "USB Headset", new BigDecimal("45.00"), 5)
        );
    }

    static Order fixtureOrder() {
        Order order = new Order("ORD-100", "Test Customer");
        order.addItem("KB-01", 2);
        order.addItem("MS-01", 1);
        return order;
    }

    static void assertTrue(boolean condition, String message) {
        if (!condition) {
            throw new AssertionError(message);
        }
    }

    static void assertEquals(Object expected, Object actual) {
        if (!Objects.equals(expected, actual)) {
            throw new AssertionError(
                "expected=" + expected + ", actual=" + actual
            );
        }
    }

    static void assertThrows(Class<? extends Throwable> type, Runnable action) {
        try {
            action.run();
        } catch (Throwable error) {
            if (type.isInstance(error)) {
                return;
            }
            throw new AssertionError(
                "expected " + type.getSimpleName()
                    + " but received " + error.getClass().getSimpleName()
            );
        }

        throw new AssertionError("expected " + type.getSimpleName());
    }

    static void testValidProduct() {
        Product product = new Product(
            "P1",
            "Keyboard",
            new BigDecimal("50.00"),
            3
        );

        assertEquals(3, product.stock());
    }

    static void testInvalidProduct() {
        assertThrows(
            ValidationException.class,
            () -> new Product(
                "P1",
                "Keyboard",
                new BigDecimal("-1.00"),
                3
            )
        );
    }

    static void testSubtotal() {
        Inventory inventory = new Inventory(fixtureProducts());
        OrderService service = new OrderService(inventory);

        assertEquals(
            new BigDecimal("185.00"),
            service.subtotal(fixtureOrder())
        );
    }

    static void testPayment() {
        Inventory inventory = new Inventory(fixtureProducts());
        OrderService service = new OrderService(inventory);
        Order order = fixtureOrder();

        assertEquals(new BigDecimal("218.30"), service.pay(order));
        assertEquals(OrderStatus.PAID, order.status());
        assertEquals(8, inventory.stock("KB-01"));
        assertEquals(19, inventory.stock("MS-01"));
    }

    static void testRollback() {
        Inventory inventory = new Inventory(fixtureProducts());
        OrderService service = new OrderService(inventory);

        Order order = new Order("ORD-101", "Customer");
        order.addItem("KB-01", 2);
        order.addItem("HD-01", 6);

        assertThrows(
            ValidationException.class,
            () -> service.pay(order)
        );

        assertEquals(10, inventory.stock("KB-01"));
        assertEquals(5, inventory.stock("HD-01"));
        assertEquals(OrderStatus.NEW, order.status());
    }

    static void testCancellation() {
        Inventory inventory = new Inventory(fixtureProducts());
        OrderService service = new OrderService(inventory);
        Order order = fixtureOrder();

        service.pay(order);
        service.cancel(order);

        assertEquals(OrderStatus.CANCELLED, order.status());
        assertEquals(10, inventory.stock("KB-01"));
    }

    static void testProtectedBranchPolicy() {
        MergePolicy policy = new ProtectedBranchPolicy(2, true, true);

        assertTrue(
            policy.eligible(2, true, true, true),
            "valid merge should be eligible"
        );

        assertTrue(
            !policy.eligible(1, true, true, true),
            "one approval must fail"
        );

        assertTrue(
            !policy.eligible(2, false, true, true),
            "failed status check must block merge"
        );

        assertTrue(
            !policy.eligible(2, true, false, true),
            "unresolved conversation must block merge"
        );
    }

    static void runTest(String name, Runnable test) {
        try {
            test.run();
            System.out.println("[PASS] " + name);
        } catch (Throwable error) {
            System.out.println(
                "[FAIL] " + name + ": " + error.getMessage()
            );
            throw error;
        }
    }

    public static void main(String[] args) {
        runTest("valid product", UnitTestingCaseStudy::testValidProduct);
        runTest("invalid product", UnitTestingCaseStudy::testInvalidProduct);
        runTest("subtotal", UnitTestingCaseStudy::testSubtotal);
        runTest("payment", UnitTestingCaseStudy::testPayment);
        runTest("transaction rollback", UnitTestingCaseStudy::testRollback);
        runTest("cancellation", UnitTestingCaseStudy::testCancellation);
        runTest(
            "protected branch policy",
            UnitTestingCaseStudy::testProtectedBranchPolicy
        );

        System.out.println("All tests passed.");
    }
}
