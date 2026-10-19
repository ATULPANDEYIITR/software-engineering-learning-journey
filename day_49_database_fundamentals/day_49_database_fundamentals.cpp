#include <algorithm>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

/*
 * Database Fundamentals: Relational vs Non-Relational Databases
 *
 * Case study:
 * A commerce platform must store customer accounts, product information,
 * orders, and product-specific attributes. The architecture team compares
 * a normalized relational model with a document-oriented model.
 *
 * The program implements both models in memory so the data structures and
 * integrity rules can be inspected without external database libraries.
 *
 * C++ is used here to emphasize:
 * - explicit domain types
 * - deterministic ownership of data
 * - associative indexes
 * - validation at write boundaries
 * - query algorithms
 * - cost trade-offs between normalized relationships and embedded documents
 */

namespace relational {

struct Customer {
    int id;
    std::string email;
    std::string name;
    std::string country;
};

struct Product {
    int id;
    std::string sku;
    std::string name;
    std::string category;
    long long priceCents;
};

struct Order {
    int id;
    int customerId;
    std::string status;
};

struct OrderItem {
    int orderId;
    int productId;
    int quantity;
    long long unitPriceCents;
};

class CommerceDatabase {
private:
    std::unordered_map<int, Customer> customers_;
    std::unordered_map<int, Product> products_;
    std::unordered_map<int, Order> orders_;
    std::map<std::pair<int, int>, OrderItem> orderItems_;

    // These indexes provide lookup behavior similar to database indexes.
    std::unordered_map<std::string, int> customerByEmail_;
    std::unordered_map<std::string, int> productBySku_;

public:
    void addCustomer(Customer customer) {
        if (customer.id <= 0) {
            throw std::invalid_argument("Customer ID must be positive");
        }

        if (customer.email.empty()) {
            throw std::invalid_argument("Customer email is required");
        }

        if (customers_.contains(customer.id)) {
            throw std::runtime_error("Duplicate customer ID");
        }

        if (customerByEmail_.contains(customer.email)) {
            throw std::runtime_error("Duplicate customer email");
        }

        customerByEmail_[customer.email] = customer.id;
        customers_.emplace(customer.id, std::move(customer));
    }

    void addProduct(Product product) {
        if (product.id <= 0 || product.sku.empty()) {
            throw std::invalid_argument("Product ID and SKU are required");
        }

        if (product.priceCents < 0) {
            throw std::invalid_argument("Product price cannot be negative");
        }

        if (products_.contains(product.id)) {
            throw std::runtime_error("Duplicate product ID");
        }

        if (productBySku_.contains(product.sku)) {
            throw std::runtime_error("Duplicate product SKU");
        }

        productBySku_[product.sku] = product.id;
        products_.emplace(product.id, std::move(product));
    }

    void addOrder(Order order) {
        if (!customers_.contains(order.customerId)) {
            throw std::runtime_error(
                "Cannot create order for unknown customer"
            );
        }

        static const std::set<std::string> validStatuses{
            "pending", "paid", "shipped", "cancelled"
        };

        if (!validStatuses.contains(order.status)) {
            throw std::invalid_argument("Invalid order status");
        }

        if (orders_.contains(order.id)) {
            throw std::runtime_error("Duplicate order ID");
        }

        orders_.emplace(order.id, std::move(order));
    }

    void addOrderItem(OrderItem item) {
        if (!orders_.contains(item.orderId)) {
            throw std::runtime_error("Order does not exist");
        }

        if (!products_.contains(item.productId)) {
            throw std::runtime_error("Product does not exist");
        }

        if (item.quantity <= 0) {
            throw std::invalid_argument("Quantity must be positive");
        }

        if (item.unitPriceCents < 0) {
            throw std::invalid_argument("Unit price cannot be negative");
        }

        const auto key = std::make_pair(item.orderId, item.productId);

        if (orderItems_.contains(key)) {
            throw std::runtime_error(
                "The same product cannot occur twice in this order"
            );
        }

        orderItems_.emplace(key, std::move(item));
    }

    long long orderTotal(int orderId) const {
        if (!orders_.contains(orderId)) {
            throw std::runtime_error("Unknown order");
        }

        long long total = 0;

        for (const auto& [key, item] : orderItems_) {
            if (item.orderId == orderId) {
                total += item.quantity * item.unitPriceCents;
            }
        }

        return total;
    }

    std::vector<Product> productsInCategory(
        const std::string& category
    ) const {
        std::vector<Product> result;

        for (const auto& [id, product] : products_) {
            if (product.category == category) {
                result.push_back(product);
            }
        }

        return result;
    }

    std::optional<Customer> findCustomerByEmail(
        const std::string& email
    ) const {
        const auto iterator = customerByEmail_.find(email);

        if (iterator == customerByEmail_.end()) {
            return std::nullopt;
        }

        return customers_.at(iterator->second);
    }

    void printOrder(int orderId) const {
        const auto& order = orders_.at(orderId);
        const auto& customer = customers_.at(order.customerId);

        std::cout
            << "Order " << order.id
            << " | customer=" << customer.name
            << " | status=" << order.status
            << " | total=$"
            << std::fixed << std::setprecision(2)
            << orderTotal(orderId) / 100.0
            << '\n';
    }
};

} // namespace relational

namespace document {

using Value = std::string;

struct ProductDocument {
    std::string id;
    std::string sku;
    std::string name;
    std::string category;
    long long priceCents;

    // Document-specific attributes can differ by product.
    std::unordered_map<std::string, Value> attributes;
};

struct OrderItemDocument {
    std::string sku;
    std::string name;
    int quantity;
    long long unitPriceCents;
};

struct OrderDocument {
    std::string id;

    // Customer information is embedded because an order commonly needs
    // the customer snapshot during order-history retrieval.
    std::string customerId;
    std::string customerName;
    std::string customerEmail;

    std::vector<OrderItemDocument> items;
    std::string paymentState;
    std::string status;
};

class DocumentCatalog {
private:
    std::unordered_map<std::string, ProductDocument> documents_;

public:
    void insert(ProductDocument document) {
        if (document.id.empty()) {
            throw std::invalid_argument("Document ID is required");
        }

        if (document.sku.empty()) {
            throw std::invalid_argument("Document SKU is required");
        }

        if (document.priceCents < 0) {
            throw std::invalid_argument(
                "Document price cannot be negative"
            );
        }

        if (documents_.contains(document.id)) {
            throw std::runtime_error("Duplicate document ID");
        }

        documents_.emplace(document.id, std::move(document));
    }

    const ProductDocument& get(const std::string& id) const {
        return documents_.at(id);
    }

    std::vector<ProductDocument> findByCategory(
        const std::string& category
    ) const {
        std::vector<ProductDocument> result;

        for (const auto& [id, document] : documents_) {
            if (document.category == category) {
                result.push_back(document);
            }
        }

        return result;
    }

    void setAttribute(
        const std::string& id,
        const std::string& attribute,
        const std::string& value
    ) {
        auto iterator = documents_.find(id);

        if (iterator == documents_.end()) {
            throw std::runtime_error("Document not found");
        }

        iterator->second.attributes[attribute] = value;
    }
};

long long calculateEmbeddedOrderTotal(const OrderDocument& order) {
    long long total = 0;

    for (const auto& item : order.items) {
        if (item.quantity <= 0) {
            throw std::invalid_argument(
                "Embedded order contains invalid quantity"
            );
        }

        if (item.unitPriceCents < 0) {
            throw std::invalid_argument(
                "Embedded order contains invalid price"
            );
        }

        total +=
            static_cast<long long>(item.quantity)
            * item.unitPriceCents;
    }

    return total;
}

} // namespace document

void populateRelationalModel(relational::CommerceDatabase& database) {
    database.addCustomer({
        1,
        "aisha@example.com",
        "Aisha Khan",
        "India"
    });

    database.addCustomer({
        2,
        "daniel@example.com",
        "Daniel Reed",
        "United Kingdom"
    });

    database.addProduct({
        100,
        "KB-100",
        "Mechanical Keyboard",
        "electronics",
        8900
    });

    database.addProduct({
        200,
        "MS-200",
        "Wireless Mouse",
        "electronics",
        4200
    });

    database.addProduct({
        300,
        "NB-300",
        "Notebook",
        "stationery",
        900
    });

    database.addOrder({
        5000,
        1,
        "paid"
    });

    database.addOrderItem({
        5000,
        100,
        1,
        8900
    });

    database.addOrderItem({
        5000,
        200,
        2,
        4200
    });
}

void populateDocumentModel(document::DocumentCatalog& catalog) {
    catalog.insert({
        "KB-100",
        "KB-100",
        "Mechanical Keyboard",
        "electronics",
        8900,
        {
            {"switch", "tactile"},
            {"layout", "US"},
            {"backlight", "true"}
        }
    });

    catalog.insert({
        "MS-200",
        "MS-200",
        "Wireless Mouse",
        "electronics",
        4200,
        {
            {"dpi", "1600"},
            {"connection", "Bluetooth"},
            {"batteryMonths", "12"}
        }
    });

    catalog.insert({
        "NB-300",
        "NB-300",
        "Notebook",
        "stationery",
        900,
        {
            {"pages", "200"},
            {"paper", "recycled"},
            {"cover", "soft"}
        }
    });
}

int main() {
    std::cout
        << "Database Fundamentals: Relational vs Non-Relational\n";

    std::cout
        << "\n--- Relational commerce model ---\n";

    relational::CommerceDatabase relationalDatabase;
    populateRelationalModel(relationalDatabase);

    relationalDatabase.printOrder(5000);

    const auto customer =
        relationalDatabase.findCustomerByEmail("aisha@example.com");

    if (customer.has_value()) {
        std::cout
            << "Indexed customer lookup: "
            << customer->name
            << '\n';
    }

    const auto electronics =
        relationalDatabase.productsInCategory("electronics");

    std::cout
        << "Electronics products stored as separate rows: "
        << electronics.size()
        << '\n';

    try {
        relationalDatabase.addOrder({
            5001,
            999,
            "paid"
        });
    } catch (const std::exception& error) {
        std::cout
            << "Relational integrity failure: "
            << error.what()
            << '\n';
    }

    try {
        relationalDatabase.addProduct({
            400,
            "KB-100",
            "Duplicate SKU",
            "electronics",
            5000
        });
    } catch (const std::exception& error) {
        std::cout
            << "Relational uniqueness failure: "
            << error.what()
            << '\n';
    }

    std::cout
        << "\n--- Document-oriented catalog ---\n";

    document::DocumentCatalog documentCatalog;
    populateDocumentModel(documentCatalog);

    for (const auto& product :
         documentCatalog.findByCategory("electronics")) {
        std::cout
            << product.sku
            << " | "
            << product.name
            << " | attributes="
            << product.attributes.size()
            << '\n';
    }

    documentCatalog.setAttribute(
        "KB-100",
        "switch",
        "linear"
    );

    std::cout
        << "Updated nested document attribute: "
        << documentCatalog.get("KB-100").attributes.at("switch")
        << '\n';

    documentCatalog.insert({
        "CAM-400",
        "CAM-400",
        "Web Camera",
        "electronics",
        12500,
        {
            {"resolution", "4K"},
            {"microphoneNoiseReduction", "true"},
            {"frameRate", "60"},
            {"lens", "wide"}
        }
    });

    std::cout
        << "A new product-specific document shape was accepted "
        << "without altering every existing product structure.\n";

    document::OrderDocument order{
        "DOC-9000",
        "1",
        "Aisha Khan",
        "aisha@example.com",
        {
            {
                "KB-100",
                "Mechanical Keyboard",
                1,
                8900
            },
            {
                "MS-200",
                "Wireless Mouse",
                2,
                4200
            }
        },
        "authorized",
        "paid"
    };

    const long long documentTotal =
        document::calculateEmbeddedOrderTotal(order);

    std::cout
        << "Embedded order total: $"
        << std::fixed
        << std::setprecision(2)
        << documentTotal / 100.0
        << '\n';

    /*
     * A relational foreign key can reject a nonexistent product reference
     * during an order-item insert. The document model above instead embeds
     * product snapshots. This improves aggregate reads but means that
     * cross-document integrity must be deliberately designed by the
     * application or by the selected document database's mechanisms.
     */

    std::cout
        << "\n--- Engineering trade-off ---\n";

    std::cout
        << "Relational storage favors normalized shared entities, "
        << "referential integrity, joins, and transactional consistency.\n";

    std::cout
        << "Document storage favors aggregate reads, flexible attributes, "
        << "and records whose fields evolve independently.\n";

    std::cout
        << "The model should follow access patterns and consistency "
        << "requirements rather than language preference.\n";

    std::cout
        << "Relational order total scans order items here: O(n) in the "
        << "number of stored order-item records; a production database "
        << "index can reduce the amount of data examined.\n";

    std::cout
        << "The document category lookup is O(n) in this simple in-memory "
        << "catalog because no category index has been implemented.\n";

    return 0;
}
