# Database Fundamentals: Relational vs Non-Relational Databases

## Topic Scope

Database systems organize persistent information so that applications can store, retrieve, validate, update, and analyze data reliably. Two important families are relational databases and non-relational databases.

A relational database represents information through relations that are commonly exposed as tables containing rows and columns. Relationships between entities are explicit through keys. Constraints can enforce rules such as uniqueness, referential integrity, valid ranges, and allowed states.

Non-relational databases use several models rather than one universal structure. The implementations in this project focus on the **document-oriented model**, where an entity or aggregate can be represented as a document containing nested objects, arrays, and fields whose shape can vary between documents.

The distinction is not simply "tables versus JSON." The deeper distinction concerns how data relationships, schema rules, query patterns, consistency boundaries, and aggregate retrieval are modeled.

## Core Conceptual Distinction

| Concern | Relational model | Document-oriented model |
| --- | --- | --- |
| Primary structure | Tables and rows | Documents |
| Relationships | Explicit keys and joins | Embedding or application-managed references |
| Schema | Usually explicitly defined | Often flexible or application-enforced |
| Normalization | Common technique for reducing duplication | Embedding is often used when data is read together |
| Integrity | Commonly enforced by database constraints | Often distributed between database features and application logic |
| Query style | Strong support for joins and relational aggregation | Strong fit for retrieving complete document aggregates |
| Schema evolution | Usually requires deliberate schema migration | New fields can often be introduced per document |
| Typical strength | Structured relationships and transactional integrity | Flexible aggregate-shaped records |

These characteristics are tendencies rather than absolute rules. Modern database products increasingly combine multiple capabilities.

## Relational Data Modeling

The relational implementation uses a commerce domain containing customers, products, orders, and order items.

A customer is represented separately from an order because the customer may participate in many orders. A product is also represented separately because the same product can appear in many orders.

The order-item relationship connects an order to a product and stores quantity and historical selling price.

The resulting conceptual relationship is:

`customers -> orders -> order_items -> products`

This separation avoids copying the complete customer and product record into every order row.

### Keys and Relationships

A primary key identifies a row uniquely. The `customer_id`, `product_id`, and `order_id` values serve this purpose in the relational examples.

Foreign keys express relationships between tables. An order references an existing customer, while an order item references both an order and a product.

This is more than a naming convention. The database can reject an order item whose referenced order does not exist.

A unique constraint on product SKU prevents two product rows from claiming the same business identifier.

### Normalization

Normalization separates facts according to their logical ownership.

The customer email belongs to the customer entity rather than being copied into every order. The product's current name belongs to the product entity. An order item stores the quantity purchased and the price charged for that particular order.

The SQL implementation deliberately retains `unit_price_cents` inside `order_items`. This is not redundant accidental duplication. It is historical order data: changing a product's current catalog price must not rewrite the amount that a customer paid previously.

Normalization therefore does not mean "never duplicate any value." It means structuring data so that dependencies and ownership are explicit and controlled.

## Document-Oriented Modeling

The Python, JavaScript, C++, and Java implementations also represent products as documents.

A product document can contain fields such as:

`id`, `sku`, `name`, `category`, `price_cents`, and `attributes`

The `attributes` object can vary naturally.

A keyboard may have `switch`, `layout`, and `backlight` attributes. A mouse may instead have `dpi`, `connection`, and `battery_months`. A camera can have `resolution`, microphone settings, and supported operating modes.

The documents therefore represent the product as an aggregate rather than requiring every product-specific property to become a separate relational column.

This flexibility is useful when product types have substantially different attributes or when those attributes evolve frequently.

## Embedding Versus Referencing

Document databases commonly force a modeling decision around whether related information should be embedded or referenced.

The document examples embed customer information and order items inside an order-shaped document.

An order can therefore contain:

- customer identity and contact information
- shipping information
- purchased items
- payment state
- order state

Retrieving the order can become a single aggregate read because the required information is already inside the document.

The trade-off is duplication and update complexity. If customer information is copied into many historical documents, changing the customer's current email does not automatically update every historical snapshot.

That behavior may be desirable when the document represents historical transaction state.

Referencing would instead store an identifier such as `customer_id` and retrieve the customer separately. This reduces duplication but introduces a cross-document lookup.

The correct choice depends on how the application reads and updates the data.

## Python Implementation

The Python program provides two contrasting implementations.

The relational side uses the standard-library `sqlite3` module. Its schema contains `customers`, `products`, `orders`, and `order_items`.

The SQL layer demonstrates primary keys, foreign keys, uniqueness, check constraints, indexes, joins, grouping, transactions, and rollback behavior.

The order query reconstructs an order total by joining normalized tables and calculating:

`quantity × unit_price_cents`

The transaction example inserts a customer and order and then intentionally raises an exception. The transaction context rolls the changes back, demonstrating the relationship between application failure and transactional integrity.

The non-relational side implements a small document store with a Python dictionary. Each document is stored under an identifier and can contain nested structures.

Application-level validation checks required product fields and prevents negative prices. Nested attributes can be updated without altering unrelated documents.

The Python implementation also demonstrates JSON persistence with temporary-file replacement. That persistence mechanism is deliberately separate from a production database engine. Its purpose is to show how a document-shaped representation can be serialized and safely replaced as a complete snapshot.

## JavaScript Implementation

The JavaScript implementation uses Node.js-specific capabilities rather than simply translating the Python program.

The relational-style representation uses `Map` collections for customers, products, orders, and order items. The repository explicitly validates relationships before accepting writes.

The document representation uses another `Map`, but its records contain flexible nested objects. A product can contain a different set of attributes from another product without modifying a global table definition.

JavaScript's `structuredClone()` is used when records cross storage boundaries so callers do not accidentally mutate stored objects through shared references.

The program also introduces `EventEmitter` and asynchronous filesystem operations. A document change emits an event, while a persistence component records the event asynchronously.

This demonstrates an important application-level distinction: data storage and downstream processing can be separate concerns. A database operation may cause auditing, integration, indexing, or other asynchronous work without requiring those responsibilities to be mixed into the data model itself.

## C++ Case Study

The C++ implementation models a commerce database as a repository and focuses on explicit integrity and lookup structures.

The relational model stores separate `Customer`, `Product`, `Order`, and `OrderItem` types.

`unordered_map` collections represent primary-key lookup structures, while additional maps act as indexes for customer email and product SKU. This makes the performance purpose of an index visible: a lookup by email or SKU does not require scanning every stored entity.

The order-item collection uses a composite key consisting of order ID and product ID. This corresponds to a relational primary key such as:

`PRIMARY KEY (order_id, product_id)`

The repository rejects invalid foreign-key references, duplicate identifiers, invalid quantities, negative prices, and duplicate order-product relationships.

The document case study instead uses `ProductDocument`, where product-specific attributes are stored in an `unordered_map`. Different products can carry different attributes without changing a shared class schema.

The embedded order uses a vector of item documents and customer snapshot information. Its total can be calculated directly from the aggregate.

The program also makes an important performance distinction. The simple document category lookup scans all documents, giving it linear behavior in the number of documents. A production document database could maintain an index on category. The same principle applies to relational systems: a database index can reduce the amount of data examined for suitable queries.

## Java Enterprise Model

The Java implementation represents the domain through explicit types and service boundaries.

Records provide immutable value objects for customers, products, orders, order lines, and document representations. Enums represent controlled states such as `PENDING`, `PAID`, `SHIPPED`, and `CANCELLED`.

The relational product store implements a generic `ProductStore<Product>` interface. The document product store implements the same conceptual abstraction for `ProductDocument`.

The relational order service validates customer existence before creating an order and validates product existence before accepting an order line. These rules correspond directly to foreign-key relationships in a relational database.

The document order service operates on an embedded order aggregate. It can calculate the aggregate's value without reconstructing the order through separate entity lookups.

The Java implementation also demonstrates immutable document attributes through `Map.copyOf`. When a document attribute changes, the store constructs a replacement document rather than exposing an uncontrolled mutable object to callers.

The payment state and order state are represented independently. This matters because payment authorization and fulfillment state are different business dimensions. A paid order is not necessarily shipped, and a cancelled order should not be treated as an ordinary payment-processing candidate.

## PostgreSQL Data Model

The SQL implementation uses a dedicated `database_fundamentals` schema.

The main relational entities are:

- `customers` stores customer identity and country.
- `products` stores catalog identity, SKU, category, price, and product attributes.
- `orders` stores customer ownership and order state.
- `order_items` connects orders to products and stores quantity and historical selling price.

The foreign-key structure expresses:

`customers -> orders`

and

`orders -> order_items -> products`

The composite primary key on `order_items` prevents the same product from being inserted twice into one order.

The `CHECK` constraints prevent negative prices, zero quantities, malformed country codes, and invalid order states.

## PostgreSQL JSONB and the Relational Boundary

The SQL model includes a `JSONB` column named `product_attributes`.

This is useful because relational and non-relational modeling are not mutually exclusive at the physical-database level. PostgreSQL can store semi-structured attributes while keeping core entities relational.

The product still has a relational primary key, SKU, category, and constrained price. The JSONB field contains attributes that vary by product type.

A GIN index supports JSONB containment and related queries.

This design is materially different from replacing the entire relational model with documents. Customers, orders, products, and order lines remain relational entities with explicit integrity rules.

The JSONB field is therefore an example of selective schema flexibility rather than a conversion to a document database.

## Transactions and Integrity

The SQL script creates an order and its order items inside a transaction.

The transaction establishes an important database property: the order creation workflow should not leave a partially completed order if a later operation fails.

Foreign keys protect relationships. Check constraints protect domain values. Unique constraints protect business identifiers.

A trigger prevents adding an order item to a cancelled order. This illustrates a case where application-level validation alone may be insufficient because another process could attempt a write directly against the database.

Database-level enforcement is particularly important when multiple applications, services, administrative tools, or background workers can modify the same data.

## Pulling the Models Apart

Relational and document-oriented models solve different modeling problems.

A relational model is particularly strong when:

- multiple entities share relationships
- referential integrity is important
- transactions span several related records
- analytical queries require joins and aggregation
- the schema represents stable business concepts
- duplicated information would create significant consistency problems

A document model is particularly attractive when:

- an entity naturally forms a self-contained aggregate
- applications commonly retrieve the entire aggregate
- nested data is frequently read together
- different records require different attributes
- schema evolution is frequent
- cross-document relationships are less central than aggregate retrieval

Neither list is an absolute rule. Real systems often combine approaches.

## Schema Flexibility Is Not the Same as No Schema

A document database may permit documents with different fields, but production applications still need a contract.

The Python document store explicitly validates required fields.

The JavaScript implementation validates product shape before insertion.

The C++ and Java implementations validate required identifiers and price constraints.

This demonstrates an important architectural point: moving schema enforcement away from a rigid relational table does not eliminate the need for data contracts.

Without validation, flexible documents can accumulate incompatible shapes that make querying and application behavior increasingly difficult to maintain.

## Consistency and Duplication

Normalization reduces unnecessary duplication of shared facts.

If a customer email changes in a normalized relational model, there is one customer record whose value can be updated.

Embedded documents can deliberately duplicate information.

For example, an order may store the customer's name and shipping information as a historical snapshot. This can be valuable because the order should preserve what was known at purchase time.

The same mechanism creates a consistency decision. If the customer's current profile changes, historical embedded documents may intentionally remain unchanged.

The design question is therefore not simply "Is duplication bad?" It is whether duplicated information represents a controlled snapshot or an uncontrolled second source of truth.

## Query Behavior

Relational queries are strong when information must be combined across entities.

The SQL implementation calculates revenue by category by joining products and order items and then grouping the resulting rows.

A relational query can answer questions such as:

- revenue by category
- orders by customer country
- products that have never been ordered
- average order value
- order history for a customer

These queries depend on relationships between normalized entities.

Document-oriented access patterns instead tend to emphasize aggregate retrieval.

A complete order document can contain its customer snapshot and line items. A single aggregate read can therefore return most of what an order-history screen needs.

The advantage depends on the application's read pattern. If the application frequently asks cross-document analytical questions, a document model may require additional indexing, denormalized views, aggregation mechanisms, or an analytical data system.

## Performance Considerations

Indexes change the cost of database access.

A relational database can index customer IDs, product SKUs, order status, foreign keys, and other frequently queried attributes.

A document database can similarly index fields inside documents, including nested fields where supported.

An index improves selected reads but introduces storage overhead and write-maintenance cost. Indexes therefore should correspond to real access patterns rather than being added indiscriminately.

Joins also have performance implications. A well-indexed relational database can perform joins efficiently, but complex relationship-heavy queries may require careful query planning.

Document embedding can eliminate some joins by placing related data in one aggregate. That can make reads efficient while making updates to duplicated information more complicated.

## Edge Cases

A relational system must handle attempts to reference missing entities. Foreign keys are designed precisely for this problem.

A document system must consider documents containing references to data that has been deleted or changed. If references are application-managed, the application must define what happens when the target disappears.

A flexible document can also contain an unexpected field type. A field expected to be numeric might appear as a string in another document. Validation and schema-versioning strategies become important as document diversity grows.

Historical values deserve special treatment. Order prices should usually represent what was actually charged rather than dynamically reading today's product price.

Cancellation rules also need explicit treatment. The PostgreSQL trigger demonstrates that a cancelled order should not silently receive additional order items.

## Common Modeling Mistakes

### Treating every relationship as a document embedding

Embedding is useful when data is naturally retrieved together, but deeply nested copies of highly shared information can create excessive duplication.

A customer referenced by thousands of orders is usually a poor candidate for uncontrolled duplication when the application requires a single authoritative current profile.

### Normalizing data that is always consumed as one aggregate

Extreme normalization can produce a large number of joins for an application that always retrieves the same bounded aggregate.

A document model or carefully designed relational projection may be more appropriate when the aggregate boundary is clear.

### Assuming flexible schema means no validation

Flexible documents still require meaningful application contracts. Without validation, the same field may acquire incompatible types or meanings across documents.

### Storing current product prices in historical orders

An order should preserve the price actually charged. Reading the current product price later can corrupt financial history.

### Choosing a database based only on popularity

Database selection should follow workload requirements, consistency boundaries, relationship complexity, query patterns, operational constraints, and expected growth.

## Practical Decision Boundary

The central architectural question is:

**What is the natural unit of consistency and retrieval for the application?**

If a business process naturally modifies several strongly related entities together and those relationships require database-enforced integrity, a relational model is often a strong fit.

If the application usually retrieves and modifies a bounded aggregate with variable nested data, a document model may provide a simpler representation.

For an order-processing system, relational storage can be attractive because customers, products, orders, inventory, payments, and line items often have strong integrity requirements.

For a product catalog containing widely varying attributes, document-oriented storage can be attractive because different product categories may have substantially different specifications.

A hybrid relational design can also use JSONB for variable attributes while preserving relational integrity for the core entities.

## Production Considerations

Production database selection must account for more than data representation.

Important concerns include transaction requirements, backup and recovery, replication, indexing strategy, query observability, migration procedures, concurrency, authorization, encryption, availability requirements, operational tooling, and data-retention policies.

Relational systems should not be evaluated only by whether joins are convenient. Their transactional and integrity capabilities can be fundamental to financial, inventory, identity, and workflow correctness.

Document systems should not be evaluated only by schema flexibility. Aggregate boundaries, document growth, duplication, secondary indexes, cross-document consistency, and query limitations must be explicit architectural decisions.

The strongest design is the one whose data model matches the application's actual consistency and access requirements rather than one chosen solely because a particular storage model appears simpler.
