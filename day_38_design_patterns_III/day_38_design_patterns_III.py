from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Dict, Iterable, List, Optional, Protocol
import json
import time


# ============================================================
# Repository Pattern
# ============================================================

@dataclass
class Product:
    product_id: int
    name: str
    category: str
    price: float
    active: bool = True


class ProductRepository(Protocol):
    """Repository abstraction hides persistence details from services."""

    def save(self, product: Product) -> Product:
        ...

    def find_by_id(self, product_id: int) -> Optional[Product]:
        ...

    def find_by_category(self, category: str) -> List[Product]:
        ...

    def list_active(self) -> List[Product]:
        ...

    def delete(self, product_id: int) -> bool:
        ...


class InMemoryProductRepository:
    """Concrete repository useful for tests and small in-process applications."""

    def __init__(self) -> None:
        self._products: Dict[int, Product] = {}

    def save(self, product: Product) -> Product:
        if product.product_id <= 0:
            raise ValueError("Product ID must be positive.")
        if not product.name.strip():
            raise ValueError("Product name cannot be empty.")
        if product.price < 0:
            raise ValueError("Product price cannot be negative.")

        self._products[product.product_id] = product
        return product

    def find_by_id(self, product_id: int) -> Optional[Product]:
        return self._products.get(product_id)

    def find_by_category(self, category: str) -> List[Product]:
        normalized = category.strip().lower()
        return [
            product
            for product in self._products.values()
            if product.category.lower() == normalized
        ]

    def list_active(self) -> List[Product]:
        return [product for product in self._products.values() if product.active]

    def delete(self, product_id: int) -> bool:
        return self._products.pop(product_id, None) is not None


class JsonProductRepository(InMemoryProductRepository):
    """
    A file-backed repository variant.

    The persistence representation is JSON, while callers still use
    ProductRepository operations. This demonstrates why the repository
    abstraction is useful: the service does not need to know the storage format.
    """

    def __init__(self, filename: str) -> None:
        super().__init__()
        self.filename = filename
        self._load()

    def _load(self) -> None:
        try:
            with open(self.filename, "r", encoding="utf-8") as file:
                records = json.load(file)

            for record in records:
                product = Product(**record)
                self._products[product.product_id] = product
        except FileNotFoundError:
            self._persist()
        except (json.JSONDecodeError, TypeError, KeyError, ValueError) as exc:
            raise RuntimeError(
                f"Repository data could not be loaded: {exc}"
            ) from exc

    def _persist(self) -> None:
        records = [
            {
                "product_id": product.product_id,
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "active": product.active,
            }
            for product in self._products.values()
        ]

        with open(self.filename, "w", encoding="utf-8") as file:
            json.dump(records, file, indent=2)

    def save(self, product: Product) -> Product:
        saved = super().save(product)
        self._persist()
        return saved

    def delete(self, product_id: int) -> bool:
        deleted = super().delete(product_id)
        if deleted:
            self._persist()
        return deleted


class ProductService:
    """
    Business logic depends on the repository abstraction instead of
    depending directly on a dictionary, database driver, or file format.
    """

    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def register_product(
        self,
        product_id: int,
        name: str,
        category: str,
        price: float,
    ) -> Product:
        if price <= 0:
            raise ValueError("A registered product must have a positive price.")

        product = Product(
            product_id=product_id,
            name=name.strip(),
            category=category.strip(),
            price=round(price, 2),
        )

        if self.repository.find_by_id(product_id) is not None:
            raise ValueError(f"Product {product_id} already exists.")

        return self.repository.save(product)

    def deactivate(self, product_id: int) -> None:
        product = self.repository.find_by_id(product_id)

        if product is None:
            raise LookupError(f"Product {product_id} does not exist.")

        product.active = False
        self.repository.save(product)

    def inventory_value(self) -> float:
        return round(
            sum(product.price for product in self.repository.list_active()),
            2,
        )


# ============================================================
# Facade Pattern
# ============================================================

class InventoryGateway:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def reserve(self, product_id: int) -> bool:
        product = self.repository.find_by_id(product_id)
        if product is None or not product.active:
            return False

        product.active = False
        self.repository.save(product)
        return True


class PaymentGateway:
    def charge(self, customer_id: str, amount: float) -> str:
        if not customer_id.strip():
            raise ValueError("Customer ID is required.")
        if amount <= 0:
            raise ValueError("Payment amount must be positive.")

        return f"PAY-{customer_id.upper()}-{amount:.2f}"


class ShippingService:
    def create_shipment(self, customer_id: str, address: str) -> str:
        if not address.strip():
            raise ValueError("Shipping address is required.")

        return f"SHIP-{customer_id.upper()}-{abs(hash(address)) % 100000}"


class NotificationService:
    def send_confirmation(self, customer_id: str, payment_id: str) -> None:
        print(
            f"Notification sent to {customer_id}: "
            f"payment {payment_id} confirmed."
        )


class OrderFacade:
    """
    Facade presents one high-level operation over several subsystems.

    Clients do not need to understand inventory reservation, payment,
    shipping, or notification sequencing.
    """

    def __init__(
        self,
        inventory: InventoryGateway,
        payment: PaymentGateway,
        shipping: ShippingService,
        notifications: NotificationService,
    ) -> None:
        self.inventory = inventory
        self.payment = payment
        self.shipping = shipping
        self.notifications = notifications

    def place_order(
        self,
        customer_id: str,
        product_id: int,
        amount: float,
        address: str,
    ) -> Dict[str, str]:
        if not self.inventory.reserve(product_id):
            raise RuntimeError("Product is unavailable.")

        payment_id = self.payment.charge(customer_id, amount)
        shipment_id = self.shipping.create_shipment(customer_id, address)

        self.notifications.send_confirmation(customer_id, payment_id)

        return {
            "customer_id": customer_id,
            "payment_id": payment_id,
            "shipment_id": shipment_id,
            "status": "confirmed",
        }


# ============================================================
# Decorator Pattern
# ============================================================

class ProductCatalog(ABC):
    @abstractmethod
    def get_products(self) -> List[Product]:
        raise NotImplementedError


class RepositoryCatalog(ProductCatalog):
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    def get_products(self) -> List[Product]:
        return self.repository.list_active()


class CatalogDecorator(ProductCatalog):
    def __init__(self, wrapped: ProductCatalog) -> None:
        self.wrapped = wrapped


class TimingDecorator(CatalogDecorator):
    def get_products(self) -> List[Product]:
        start = time.perf_counter()
        products = self.wrapped.get_products()
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"Catalog query completed in {elapsed_ms:.3f} ms")
        return products


class LoggingDecorator(CatalogDecorator):
    def get_products(self) -> List[Product]:
        print("Catalog request started.")
        products = self.wrapped.get_products()
        print(f"Catalog request returned {len(products)} product(s).")
        return products


class CategoryFilterDecorator(CatalogDecorator):
    def __init__(self, wrapped: ProductCatalog, category: str) -> None:
        super().__init__(wrapped)
        self.category = category

    def get_products(self) -> List[Product]:
        products = self.wrapped.get_products()
        normalized = self.category.lower()
        return [
            product
            for product in products
            if product.category.lower() == normalized
        ]


class PriceRangeDecorator(CatalogDecorator):
    def __init__(
        self,
        wrapped: ProductCatalog,
        minimum: float,
        maximum: float,
    ) -> None:
        super().__init__(wrapped)

        if minimum < 0 or maximum < minimum:
            raise ValueError("Invalid price range.")

        self.minimum = minimum
        self.maximum = maximum

    def get_products(self) -> List[Product]:
        products = self.wrapped.get_products()
        return [
            product
            for product in products
            if self.minimum <= product.price <= self.maximum
        ]


# ============================================================
# Python decorator syntax
# ============================================================

def audit(operation: str) -> Callable:
    """
    Python's function decorator syntax can add cross-cutting behavior
    without changing the wrapped function's business implementation.
    """

    def decorator(function: Callable) -> Callable:
        @wraps(function)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                result = function(*args, **kwargs)
                print(f"AUDIT {operation}: success")
                return result
            except Exception as exc:
                print(f"AUDIT {operation}: failure={exc}")
                raise
            finally:
                elapsed = (time.perf_counter() - started) * 1000
                print(f"AUDIT {operation}: {elapsed:.3f} ms")

        return wrapper

    return decorator


@audit("catalog-report")
def generate_catalog_report(catalog: ProductCatalog) -> str:
    products = catalog.get_products()

    if not products:
        return "No matching products."

    return "\n".join(
        f"{product.product_id}: {product.name} | "
        f"{product.category} | ${product.price:.2f}"
        for product in products
    )


# ============================================================
# Demonstration
# ============================================================

def demonstrate_repository() -> ProductRepository:
    repository = InMemoryProductRepository()
    service = ProductService(repository)

    service.register_product(101, "ThinkPad Dock", "hardware", 189.99)
    service.register_product(102, "Mechanical Keyboard", "hardware", 129.50)
    service.register_product(103, "Cloud Security Course", "training", 249.00)
    service.register_product(104, "USB-C Hub", "hardware", 59.99)

    print("\nRepository lookup:")
    print(repository.find_by_id(102))

    print("\nHardware products:")
    for product in repository.find_by_category("hardware"):
        print(product)

    print(f"\nActive inventory value: ${service.inventory_value():.2f}")

    service.deactivate(104)
    print("\nAfter deactivation:")
    for product in repository.list_active():
        print(product)

    return repository


def demonstrate_facade(repository: ProductRepository) -> None:
    inventory = InventoryGateway(repository)
    payment = PaymentGateway()
    shipping = ShippingService()
    notifications = NotificationService()

    facade = OrderFacade(
        inventory=inventory,
        payment=payment,
        shipping=shipping,
        notifications=notifications,
    )

    print("\nFacade order workflow:")

    try:
        result = facade.place_order(
            customer_id="CUST-42",
            product_id=102,
            amount=129.50,
            address="42 Technology Park, Bengaluru",
        )
        print(result)
    except (ValueError, RuntimeError) as exc:
        print(f"Order failed: {exc}")


def demonstrate_decorator(repository: ProductRepository) -> None:
    catalog: ProductCatalog = RepositoryCatalog(repository)

    decorated_catalog = TimingDecorator(
        LoggingDecorator(
            PriceRangeDecorator(
                CategoryFilterDecorator(catalog, "hardware"),
                minimum=100,
                maximum=250,
            )
        )
    )

    print("\nDecorator pipeline:")
    print(generate_catalog_report(decorated_catalog))


def demonstrate_json_repository() -> None:
    filename = "products_design_patterns_demo.json"

    repository = JsonProductRepository(filename)
    service = ProductService(repository)

    existing = repository.find_by_id(501)

    if existing is None:
        service.register_product(
            501,
            "Encrypted Backup Appliance",
            "security",
            899.00,
        )

    print("\nFile-backed repository:")
    print(repository.find_by_id(501))


def run_edge_cases(repository: ProductRepository) -> None:
    print("\nEdge cases:")

    try:
        ProductService(repository).register_product(
            101,
            "Duplicate",
            "hardware",
            10,
        )
    except ValueError as exc:
        print(f"Duplicate protection: {exc}")

    try:
        ProductService(repository).register_product(
            999,
            "",
            "hardware",
            10,
        )
    except ValueError as exc:
        print(f"Validation protection: {exc}")

    try:
        ProductService(repository).deactivate(99999)
    except LookupError as exc:
        print(f"Missing entity protection: {exc}")

    try:
        PriceRangeDecorator(
            RepositoryCatalog(repository),
            minimum=500,
            maximum=100,
        )
    except ValueError as exc:
        print(f"Decorator configuration protection: {exc}")


def main() -> None:
    print("DESIGN PATTERNS III: REPOSITORY, FACADE, DECORATOR")

    repository = demonstrate_repository()
    demonstrate_facade(repository)
    demonstrate_decorator(repository)
    run_edge_cases(repository)

    # File persistence is demonstrated separately so the primary examples
    # remain deterministic and do not require an external database.
    demonstrate_json_repository()


if __name__ == "__main__":
    main()
