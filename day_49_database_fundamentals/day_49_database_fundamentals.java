import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;

/*
 * Database Fundamentals: Relational vs Non-Relational Databases
 *
 * Enterprise case study:
 * A commerce organization is designing a product and order platform.
 * The Java model represents both normalized relational entities and
 * document-oriented aggregates so that application architecture can be
 * evaluated against data-integrity and access-pattern requirements.
 *
 * Java 17 features used here include:
 * - records for immutable value objects
 * - enums for controlled state
 * - interfaces for storage abstractions
 * - generics and collections
 * - explicit domain exceptions
 * - service-layer validation
 */

public class DatabaseFundamentals {

    enum OrderStatus {
        PENDING,
        PAID,
        SHIPPED,
        CANCELLED
    }

    enum PaymentState {
        AUTHORIZED,
        CAPTURED,
        FAILED,
        REFUNDED
    }

    record Customer(
        long id,
        String email,
        String name,
        String country
    ) {
        Customer {
            if (id <= 0) {
                throw new IllegalArgumentException(
                    "Customer ID must be positive"
                );
            }

            if (email == null || email.isBlank()) {
                throw new IllegalArgumentException(
                    "Customer email is required"
                );
            }
        }
    }

    record Product(
        long id,
        String sku,
        String name,
        String category,
        long priceCents
    ) {
        Product {
            if (id <= 0 || sku == null || sku.isBlank()) {
                throw new IllegalArgumentException(
                    "Product ID and SKU are required"
                );
            }

            if (priceCents < 0) {
                throw new IllegalArgumentException(
                    "Product price cannot be negative"
                );
            }
        }
    }

    record Order(
        long id,
        long customerId,
        OrderStatus status
    ) {}

    record OrderLine(
        long orderId,
        long productId,
        int quantity,
        long unitPriceCents
    ) {
        OrderLine {
            if (quantity <= 0) {
                throw new IllegalArgumentException(
                    "Quantity must be positive"
                );
            }

            if (unitPriceCents < 0) {
                throw new IllegalArgumentException(
                    "Unit price cannot be negative"
                );
            }
        }
    }

    record ProductDocument(
        String id,
        String sku,
        String name,
        String category,
        long priceCents,
        Map<String, Object> attributes
    ) {
        ProductDocument {
            Objects.requireNonNull(id);
            Objects.requireNonNull(sku);
            Objects.requireNonNull(name);
            Objects.requireNonNull(category);
            Objects.requireNonNull(attributes);

            if (priceCents < 0) {
                throw new IllegalArgumentException(
                    "Document price cannot be negative"
                );
            }

            attributes = Map.copyOf(attributes);
        }
    }

    record EmbeddedOrderLine(
        String sku,
        String name,
        int quantity,
        long unitPriceCents
    ) {}

    record OrderDocument(
        String id,
        Map<String, Object> customer,
        List<EmbeddedOrderLine> items,
        PaymentState paymentState,
        OrderStatus status
    ) {
        OrderDocument {
            Objects.requireNonNull(id);
            customer = Map.copyOf(customer);
            items = List.copyOf(items);
        }
    }

    interface ProductStore<T> {
        void save(T value);
        T findById(String id);
        List<T> findByCategory(String category);
    }

    static class RelationalIntegrityException
        extends RuntimeException {

        RelationalIntegrityException(String message) {
            super(message);
        }
    }

    static class RelationalProductStore
        implements ProductStore<Product> {

        private final Map<Long, Product> products = new HashMap<>();
        private final Map<String, Long> productBySku = new HashMap<>();

        @Override
        public void save(Product product) {
            if (products.containsKey(product.id())) {
                throw new RelationalIntegrityException(
                    "Duplicate product primary key"
                );
            }

            if (productBySku.containsKey(product.sku())) {
                throw new RelationalIntegrityException(
                    "Duplicate product unique key"
                );
            }

            products.put(product.id(), product);
            productBySku.put(product.sku(), product.id());
        }

        @Override
        public Product findById(String id) {
            long numericId;

            try {
                numericId = Long.parseLong(id);
            } catch (NumberFormatException exception) {
                return null;
            }

            return products.get(numericId);
        }

        @Override
        public List<Product> findByCategory(String category) {
            return products.values()
                .stream()
                .filter(product -> product.category().equals(category))
                .toList();
        }
    }

    static class RelationalOrderService {

        private final Map<Long, Customer> customers = new HashMap<>();
        private final Map<Long, Order> orders = new HashMap<>();
        private final List<OrderLine> lines = new ArrayList<>();
        private final RelationalProductStore productStore;

        RelationalOrderService(RelationalProductStore productStore) {
            this.productStore = productStore;
        }

        void addCustomer(Customer customer) {
            if (customers.putIfAbsent(customer.id(), customer) != null) {
                throw new RelationalIntegrityException(
                    "Customer primary key already exists"
                );
            }
        }

        void addOrder(Order order) {
            if (!customers.containsKey(order.customerId())) {
                throw new RelationalIntegrityException(
                    "Foreign-key customer does not exist"
                );
            }

            if (orders.putIfAbsent(order.id(), order) != null) {
                throw new RelationalIntegrityException(
                    "Order primary key already exists"
                );
            }
        }

        void addLine(OrderLine line) {
            if (!orders.containsKey(line.orderId())) {
                throw new RelationalIntegrityException(
                    "Foreign-key order does not exist"
                );
            }

            if (productStore.findById(
                Long.toString(line.productId())
            ) == null) {
                throw new RelationalIntegrityException(
                    "Foreign-key product does not exist"
                );
            }

            boolean duplicate = lines.stream().anyMatch(existing ->
                existing.orderId() == line.orderId()
                    && existing.productId() == line.productId()
            );

            if (duplicate) {
                throw new RelationalIntegrityException(
                    "Duplicate order/product relationship"
                );
            }

            lines.add(line);
        }

        long calculateOrderTotal(long orderId) {
            return lines.stream()
                .filter(line -> line.orderId() == orderId)
                .mapToLong(line ->
                    line.quantity() * line.unitPriceCents()
                )
                .sum();
        }
    }

    static class DocumentProductStore
        implements ProductStore<ProductDocument> {

        private final Map<String, ProductDocument> documents =
            new HashMap<>();

        @Override
        public void save(ProductDocument document) {
            if (documents.containsKey(document.id())) {
                throw new IllegalArgumentException(
                    "Document ID already exists"
                );
            }

            documents.put(document.id(), document);
        }

        @Override
        public ProductDocument findById(String id) {
            return documents.get(id);
        }

        @Override
        public List<ProductDocument> findByCategory(
            String category
        ) {
            return documents.values()
                .stream()
                .filter(document ->
                    document.category().equals(category)
                )
                .toList();
        }

        void replaceAttribute(
            String documentId,
            String attribute,
            Object value
        ) {
            ProductDocument current = documents.get(documentId);

            if (current == null) {
                throw new IllegalArgumentException(
                    "Document does not exist"
                );
            }

            Map<String, Object> mutableAttributes =
                new HashMap<>(current.attributes());

            mutableAttributes.put(attribute, value);

            documents.put(
                documentId,
                new ProductDocument(
                    current.id(),
                    current.sku(),
                    current.name(),
                    current.category(),
                    current.priceCents(),
                    mutableAttributes
                )
            );
        }
    }

    static class DocumentOrderService {

        long calculateTotal(OrderDocument order) {
            if (order.status() == OrderStatus.CANCELLED) {
                throw new IllegalStateException(
                    "Cancelled orders cannot be valued for payment"
                );
            }

            return order.items()
                .stream()
                .mapToLong(item ->
                    item.quantity() * item.unitPriceCents()
                )
                .sum();
        }

        boolean isPaymentMergeEligible(OrderDocument order) {
            return order.paymentState() == PaymentState.AUTHORIZED
                && order.status() != OrderStatus.CANCELLED;
        }
    }

    private static void printHeading(String title) {
        System.out.println("\n" + "=".repeat(72));
        System.out.println(title);
        System.out.println("=".repeat(72));
    }

    public static void main(String[] args) {
        printHeading(
            "Database Fundamentals: Relational vs Non-Relational"
        );

        printHeading("Relational enterprise model");

        RelationalProductStore relationalProducts =
            new RelationalProductStore();

        relationalProducts.save(
            new Product(
                100,
                "KB-100",
                "Mechanical Keyboard",
                "electronics",
                8900
            )
        );

        relationalProducts.save(
            new Product(
                200,
                "MS-200",
                "Wireless Mouse",
                "electronics",
                4200
            )
        );

        RelationalOrderService orderService =
            new RelationalOrderService(relationalProducts);

        orderService.addCustomer(
            new Customer(
                1,
                "aisha@example.com",
                "Aisha Khan",
                "India"
            )
        );

        orderService.addOrder(
            new Order(
                5000,
                1,
                OrderStatus.PAID
            )
        );

        orderService.addLine(
            new OrderLine(
                5000,
                100,
                1,
                8900
            )
        );

        orderService.addLine(
            new OrderLine(
                5000,
                200,
                2,
                4200
            )
        );

        System.out.printf(
            "Normalized order total: $%.2f%n",
            orderService.calculateOrderTotal(5000) / 100.0
        );

        try {
            orderService.addLine(
                new OrderLine(
                    5000,
                    999,
                    1,
                    5000
                )
            );
        } catch (RelationalIntegrityException exception) {
            System.out.println(
                "Relational integrity rejected the write: "
                    + exception.getMessage()
            );
        }

        printHeading("Document-oriented enterprise model");

        DocumentProductStore documents =
            new DocumentProductStore();

        documents.save(
            new ProductDocument(
                "KB-100",
                "KB-100",
                "Mechanical Keyboard",
                "electronics",
                8900,
                Map.of(
                    "switch", "tactile",
                    "layout", "US",
                    "rgb", true
                )
            )
        );

        documents.save(
            new ProductDocument(
                "MS-200",
                "MS-200",
                "Wireless Mouse",
                "electronics",
                4200,
                Map.of(
                    "dpi", 1600,
                    "connection", "Bluetooth",
                    "batteryMonths", 12
                )
            )
        );

        documents.save(
            new ProductDocument(
                "CAM-300",
                "CAM-300",
                "Web Camera",
                "electronics",
                12500,
                Map.of(
                    "resolution", "4K",
                    "microphoneNoiseReduction", true,
                    "supportedModes",
                    List.of(
                        "conference",
                        "streaming"
                    )
                )
            )
        );

        System.out.println(
            "Electronics document count: "
                + documents.findByCategory("electronics").size()
        );

        documents.replaceAttribute(
            "KB-100",
            "switch",
            "linear"
        );

        System.out.println(
            "Updated KB-100 switch: "
                + documents.findById("KB-100")
                    .attributes()
                    .get("switch")
        );

        printHeading("Embedded order aggregate");

        OrderDocument orderDocument =
            new OrderDocument(
                "DOC-9000",
                Map.of(
                    "id", "C100",
                    "name", "Aisha Khan",
                    "email", "aisha@example.com"
                ),
                List.of(
                    new EmbeddedOrderLine(
                        "KB-100",
                        "Mechanical Keyboard",
                        1,
                        8900
                    ),
                    new EmbeddedOrderLine(
                        "MS-200",
                        "Wireless Mouse",
                        2,
                        4200
                    )
                ),
                PaymentState.AUTHORIZED,
                OrderStatus.PAID
            );

        DocumentOrderService documentOrderService =
            new DocumentOrderService();

        System.out.printf(
            "Embedded order total: $%.2f%n",
            documentOrderService.calculateTotal(orderDocument)
                / 100.0
        );

        System.out.println(
            "Payment state allows processing: "
                + documentOrderService.isPaymentMergeEligible(
                    orderDocument
                )
        );

        printHeading("Enterprise modeling decision");

        System.out.println(
            "The relational implementation treats customers, products, "
                + "orders, and order lines as distinct entities."
        );

        System.out.println(
            "Foreign-key validation prevents an order line from "
                + "referencing a missing product."
        );

        System.out.println(
            "The document implementation stores variable product "
                + "attributes without requiring every product to share "
                + "the same field set."
        );

        System.out.println(
            "The embedded order is optimized for retrieving an order "
                + "aggregate without reconstructing it from multiple "
                + "normalized tables."
        );

        System.out.println(
            "Relational design is favored when shared relationships, "
                + "constraints, joins, and transactional integrity dominate."
        );

        System.out.println(
            "Document design is favored when aggregate retrieval, "
                + "schema flexibility, and independent document evolution "
                + "are stronger requirements."
        );

        /*
         * Immutable records make value objects safer to pass between
         * services. Mutable maps are deliberately isolated inside the
         * document store, where replacing a complete document gives the
         * application a clear update boundary.
         */
        List<ProductDocument> immutableView =
            Collections.unmodifiableList(
                documents.findByCategory("electronics")
            );

        System.out.println(
            "Immutable document query result size: "
                + immutableView.size()
        );
    }
}
