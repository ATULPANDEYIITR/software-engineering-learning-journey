"""
Database Fundamentals: Relational vs Non-Relational Databases

A self-contained executable comparison of relational and non-relational
data models using only Python's standard library.

The relational side uses SQLite to demonstrate:
- tables, rows, columns, primary keys, foreign keys
- normalization and joins
- constraints and transactions
- indexing and aggregate queries

The non-relational side implements a small document-oriented store with
Python dictionaries and JSON persistence to demonstrate:
- document-shaped records
- flexible schemas
- embedding related data
- key-based access
- schema validation at the application boundary
- atomic file replacement

The examples model an online retail catalog and orders because the same
business domain exposes useful differences between relational and
document-oriented storage.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def print_heading(title: str) -> None:
    print(f"\n{'=' * 72}")
    print(title)
    print("=" * 72)


# ---------------------------------------------------------------------------
# Relational database model
# ---------------------------------------------------------------------------

RELATIONAL_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    country TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'paid', 'shipped', 'cancelled')
    ),
    created_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_products_category ON products(category);
CREATE INDEX idx_order_items_product ON order_items(product_id);
"""


def create_relational_database() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(RELATIONAL_SCHEMA)
    return connection


def seed_relational_database(connection: sqlite3.Connection) -> None:
    customers = [
        (1, "aisha@example.com", "Aisha Khan", "India"),
        (2, "daniel@example.com", "Daniel Reed", "United Kingdom"),
        (3, "mei@example.com", "Mei Chen", "Singapore"),
    ]

    products = [
        (1, "KB-100", "Mechanical Keyboard", "electronics", 8900),
        (2, "MS-200", "Wireless Mouse", "electronics", 4200),
        (3, "NB-300", "Notebook", "stationery", 900),
        (4, "ST-400", "Desk Stand", "office", 3500),
    ]

    orders = [
        (1001, 1, "paid", "2026-10-18T09:30:00Z"),
        (1002, 2, "shipped", "2026-10-18T11:15:00Z"),
        (1003, 1, "pending", "2026-10-19T07:20:00Z"),
    ]

    items = [
        (1001, 1, 1, 8900),
        (1001, 2, 2, 4200),
        (1002, 3, 4, 900),
        (1002, 4, 1, 3500),
        (1003, 1, 1, 8900),
    ]

    with connection:
        connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?)", customers
        )
        connection.executemany(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?)", products
        )
        connection.executemany(
            "INSERT INTO orders VALUES (?, ?, ?, ?)", orders
        )
        connection.executemany(
            """
            INSERT INTO order_items
                (order_id, product_id, quantity, unit_price_cents)
            VALUES (?, ?, ?, ?)
            """,
            items,
        )


def demonstrate_relational_queries(connection: sqlite3.Connection) -> None:
    print_heading("Relational model: normalized data and joins")

    rows = connection.execute(
        """
        SELECT
            o.order_id,
            c.name AS customer,
            o.status,
            SUM(oi.quantity * oi.unit_price_cents) AS total_cents
        FROM orders AS o
        JOIN customers AS c ON c.customer_id = o.customer_id
        JOIN order_items AS oi ON oi.order_id = o.order_id
        GROUP BY o.order_id, c.name, o.status
        ORDER BY o.order_id
        """
    ).fetchall()

    for row in rows:
        print(
            f"Order {row['order_id']}: {row['customer']:<15} "
            f"{row['status']:<9} total=${row['total_cents'] / 100:.2f}"
        )

    print("\nCategory revenue:")
    category_rows = connection.execute(
        """
        SELECT
            p.category,
            SUM(oi.quantity * oi.unit_price_cents) AS revenue_cents
        FROM products AS p
        JOIN order_items AS oi ON oi.product_id = p.product_id
        GROUP BY p.category
        ORDER BY revenue_cents DESC
        """
    ).fetchall()

    for row in category_rows:
        print(
            f"  {row['category']:<12} "
            f"${row['revenue_cents'] / 100:.2f}"
        )


def demonstrate_relational_constraints(connection: sqlite3.Connection) -> None:
    print_heading("Relational constraints and transaction behavior")

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO order_items
                    (order_id, product_id, quantity, unit_price_cents)
                VALUES (?, ?, ?, ?)
                """,
                (9999, 1, 1, 8900),
            )
    except sqlite3.IntegrityError as exc:
        print(f"Foreign-key violation rejected: {exc}")

    try:
        with connection:
            connection.execute(
                """
                INSERT INTO products
                    (product_id, sku, name, category, price_cents)
                VALUES (?, ?, ?, ?, ?)
                """,
                (5, "KB-100", "Duplicate Keyboard", "electronics", 7000),
            )
    except sqlite3.IntegrityError as exc:
        print(f"Unique constraint rejected: {exc}")

    print("\nTransaction rollback demonstration:")
    try:
        with connection:
            connection.execute(
                """
                INSERT INTO customers
                    (customer_id, email, name, country)
                VALUES (?, ?, ?, ?)
                """,
                (10, "new@example.com", "New Customer", "India"),
            )
            connection.execute(
                """
                INSERT INTO orders
                    (order_id, customer_id, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (1010, 10, "paid", "2026-10-19T10:00:00Z"),
            )
            raise RuntimeError("Simulated downstream failure")
    except RuntimeError as exc:
        print(f"Transaction aborted: {exc}")

    customer_exists = connection.execute(
        "SELECT 1 FROM customers WHERE customer_id = 10"
    ).fetchone()
    print(f"Customer 10 exists after rollback: {customer_exists is not None}")


# ---------------------------------------------------------------------------
# Document-oriented non-relational model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProductDocument:
    product_id: str
    sku: str
    name: str
    category: str
    price_cents: int
    attributes: dict[str, Any]


class DocumentValidationError(ValueError):
    """Raised when a document violates the application's document contract."""


class DocumentStore:
    """
    A small document-oriented store.

    Each document is independently shaped and stored under a key.
    Relationships can be embedded instead of represented by foreign keys.

    This is intentionally not presented as a production database engine.
    It demonstrates the data-modeling behavior that distinguishes document
    storage from normalized relational tables.
    """

    def __init__(self) -> None:
        self._documents: dict[str, dict[str, Any]] = {}

    def put(self, document_id: str, document: dict[str, Any]) -> None:
        if not document_id.strip():
            raise DocumentValidationError("Document ID cannot be empty")

        if not isinstance(document, dict):
            raise DocumentValidationError("Document must be a mapping")

        if document.get("id") != document_id:
            raise DocumentValidationError(
                "Document id must match its storage key"
            )

        self._documents[document_id] = json.loads(json.dumps(document))

    def get(self, document_id: str) -> dict[str, Any] | None:
        document = self._documents.get(document_id)
        if document is None:
            return None

        return json.loads(json.dumps(document))

    def find_by_field(self, field: str, value: Any) -> list[dict[str, Any]]:
        return [
            json.loads(json.dumps(document))
            for document in self._documents.values()
            if document.get(field) == value
        ]

    def update_nested(
        self,
        document_id: str,
        path: Iterable[str],
        value: Any,
    ) -> None:
        document = self._documents.get(document_id)
        if document is None:
            raise KeyError(document_id)

        parts = list(path)
        if not parts:
            raise ValueError("Nested path cannot be empty")

        target = document
        for part in parts[:-1]:
            child = target.get(part)
            if not isinstance(child, dict):
                raise KeyError(".".join(parts))
            target = child

        target[parts[-1]] = value

    def to_json(self) -> str:
        return json.dumps(
            self._documents,
            indent=2,
            sort_keys=True,
        )


def validate_product_document(document: dict[str, Any]) -> None:
    required_fields = {
        "id",
        "sku",
        "name",
        "category",
        "price_cents",
    }

    missing = required_fields - document.keys()
    if missing:
        raise DocumentValidationError(
            f"Missing required fields: {sorted(missing)}"
        )

    if not isinstance(document["price_cents"], int):
        raise DocumentValidationError("price_cents must be an integer")

    if document["price_cents"] < 0:
        raise DocumentValidationError("price_cents cannot be negative")


def build_document_store() -> DocumentStore:
    store = DocumentStore()

    products = [
        {
            "id": "KB-100",
            "sku": "KB-100",
            "name": "Mechanical Keyboard",
            "category": "electronics",
            "price_cents": 8900,
            "attributes": {
                "switch": "tactile",
                "layout": "US",
                "backlight": True,
            },
        },
        {
            "id": "MS-200",
            "sku": "MS-200",
            "name": "Wireless Mouse",
            "category": "electronics",
            "price_cents": 4200,
            "attributes": {
                "dpi": 1600,
                "connection": "Bluetooth",
                "battery_months": 12,
            },
        },
        {
            "id": "NB-300",
            "sku": "NB-300",
            "name": "Notebook",
            "category": "stationery",
            "price_cents": 900,
            "attributes": {
                "pages": 200,
                "paper": "recycled",
            },
        },
    ]

    for product in products:
        validate_product_document(product)
        store.put(product["id"], product)

    return store


def demonstrate_document_model(store: DocumentStore) -> None:
    print_heading("Non-relational model: document-oriented storage")

    for document in store.find_by_field("category", "electronics"):
        print(
            f"{document['sku']}: {document['name']} "
            f"attributes={document['attributes']}"
        )

    print("\nSchema flexibility:")
    store.put(
        "ST-400",
        {
            "id": "ST-400",
            "sku": "ST-400",
            "name": "Desk Stand",
            "category": "office",
            "price_cents": 3500,
            "attributes": {
                "material": "aluminium",
                "adjustable": True,
                "height_range_mm": [80, 140],
                "cable_channel": True,
            },
            "supplier_metadata": {
                "lead_time_days": 5,
                "region": "APAC",
            },
        },
    )

    print(store.get("ST-400"))

    store.update_nested(
        "KB-100",
        ("attributes", "switch"),
        "linear",
    )

    print("\nUpdated nested attribute:")
    print(store.get("KB-100"))

    print("\nDocument model does not automatically enforce relational integrity:")
    order_document = {
        "id": "ORD-9001",
        "customer": {
            "id": "C-100",
            "name": "Aisha Khan",
            "email": "aisha@example.com",
        },
        "items": [
            {
                "sku": "KB-100",
                "name": "Mechanical Keyboard",
                "quantity": 1,
                "unit_price_cents": 8900,
            },
            {
                "sku": "UNKNOWN",
                "name": "Deleted Product",
                "quantity": 1,
                "unit_price_cents": 100,
            },
        ],
        "status": "pending",
    }

    store.put(order_document["id"], order_document)

    # The application can detect the orphaned product reference, but the
    # document store itself has no foreign-key constraint to enforce it.
    known_skus = {
        document["sku"]
        for document in store.find_by_field("category", "electronics")
    }
    invalid_items = [
        item["sku"]
        for item in order_document["items"]
        if item["sku"] not in known_skus
    ]

    print(f"Application-level orphan detection: {invalid_items}")


# ---------------------------------------------------------------------------
# Modeling decisions and performance observations
# ---------------------------------------------------------------------------

def compare_models(
    relational: sqlite3.Connection,
    documents: DocumentStore,
) -> None:
    print_heading("Model selection: workload and integrity")

    relational_query = """
        SELECT c.country, COUNT(*) AS order_count
        FROM customers AS c
        JOIN orders AS o ON o.customer_id = c.customer_id
        GROUP BY c.country
        ORDER BY order_count DESC
    """

    relational_rows = relational.execute(relational_query).fetchall()

    print("Relational aggregation by country:")
    for row in relational_rows:
        print(f"  {row['country']}: {row['order_count']} orders")

    electronics = documents.find_by_field("category", "electronics")
    print(
        "\nDocument lookup by category scanned the in-memory document "
        f"collection: {len(electronics)} matching documents"
    )

    print(
        "\nRelational databases are particularly useful when integrity, "
        "joins, transactions, and structured analytical queries are central."
    )
    print(
        "Document-oriented systems are particularly useful when records "
        "have variable attributes, natural document boundaries, and "
        "access patterns dominated by retrieving complete aggregates."
    )


# ---------------------------------------------------------------------------
# Persistence demonstration
# ---------------------------------------------------------------------------

def atomic_json_save(store: DocumentStore, path: Path) -> None:
    """
    Write the complete document set to a temporary file and replace the
    destination only after the temporary file has been successfully written.
    This reduces the risk of leaving a partially written JSON document.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    file_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f"{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )

    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as handle:
            handle.write(store.to_json())
            handle.flush()
            os.fsync(handle.fileno())

        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def demonstrate_json_persistence(store: DocumentStore) -> None:
    print_heading("Document persistence and failure safety")

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "catalog.json"
        atomic_json_save(store, path)

        loaded = json.loads(path.read_text(encoding="utf-8"))

        print(f"Persisted document count: {len(loaded)}")
        print(f"Persistence file exists: {path.exists()}")
        print(
            "Atomic replacement keeps the destination from being replaced "
            "by a partially written temporary file."
        )


# ---------------------------------------------------------------------------
# Main execution
# ---------------------------------------------------------------------------

def main() -> None:
    print_heading("Database Fundamentals: Relational vs Non-Relational")

    relational = create_relational_database()
    seed_relational_database(relational)

    demonstrate_relational_queries(relational)
    demonstrate_relational_constraints(relational)

    document_store = build_document_store()
    demonstrate_document_model(document_store)

    compare_models(relational, document_store)
    demonstrate_json_persistence(document_store)

    print_heading("Database modeling conclusion")
    print(
        "The relational model separates customers, products, orders, and "
        "order items so constraints and joins can enforce consistency."
    )
    print(
        "The document model keeps aggregate-shaped information together "
        "and allows records to evolve with different attributes."
    )
    print(
        "The correct choice depends on access patterns, integrity needs, "
        "transaction boundaries, schema stability, scale characteristics, "
        "and the cost of cross-record relationships."
    )

    relational.close()


if __name__ == "__main__":
    main()
