from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse
import json
import re
import threading
import urllib.error
import urllib.request


# REST API DESIGN LAB
# Demonstrates resource-oriented URI design, API versioning, pagination,
# validation, filtering, error contracts, HTTP semantics, and a small
# executable HTTP API using only the Python standard library.

HOST = "127.0.0.1"
PORT = 8080
API_VERSION = "v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Book:
    id: int
    title: str
    author: str
    category: str
    published_year: int
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


class BookRepository:
    """In-memory persistence keeps the example executable without dependencies."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._next_id = 6
        self._books: dict[int, Book] = {
            1: Book(1, "Designing Data-Intensive Applications", "Martin Kleppmann",
                    "distributed-systems", 2017, utc_now()),
            2: Book(2, "Clean Architecture", "Robert C. Martin",
                    "software-engineering", 2017, utc_now()),
            3: Book(3, "HTTP: The Definitive Guide", "David Gourley",
                    "web", 2002, utc_now()),
            4: Book(4, "Building Microservices", "Sam Newman",
                    "architecture", 2021, utc_now()),
            5: Book(5, "API Design Patterns", "JJ Geewax",
                    "api-design", 2021, utc_now()),
        }

    def list(self) -> list[Book]:
        with self._lock:
            return list(self._books.values())

    def get(self, book_id: int) -> Book:
        with self._lock:
            try:
                return self._books[book_id]
            except KeyError:
                raise ApiError(
                    404,
                    "resource_not_found",
                    f"Book {book_id} does not exist."
                )

    def create(self, payload: dict[str, Any]) -> Book:
        required = {"title", "author", "category", "published_year"}
        missing = sorted(required - payload.keys())

        if missing:
            raise ApiError(
                400,
                "validation_error",
                "Required fields are missing.",
                {"missing": missing},
            )

        title = payload["title"]
        author = payload["author"]
        category = payload["category"]
        published_year = payload["published_year"]

        if not all(isinstance(value, str) and value.strip()
                   for value in (title, author, category)):
            raise ApiError(
                400,
                "validation_error",
                "title, author, and category must be non-empty strings.",
            )

        if not isinstance(published_year, int) or isinstance(published_year, bool):
            raise ApiError(
                400,
                "validation_error",
                "published_year must be an integer.",
            )

        current_year = datetime.now(timezone.utc).year
        if published_year < 1000 or published_year > current_year:
            raise ApiError(
                422,
                "invalid_published_year",
                f"published_year must be between 1000 and {current_year}.",
            )

        with self._lock:
            book = Book(
                id=self._next_id,
                title=title.strip(),
                author=author.strip(),
                category=category.strip().lower(),
                published_year=published_year,
                created_at=utc_now(),
            )
            self._books[book.id] = book
            self._next_id += 1
            return book


repository = BookRepository()


def parse_positive_integer(value: str | None, name: str, default: int) -> int:
    if value is None:
        return default

    try:
        parsed = int(value)
    except ValueError:
        raise ApiError(400, "invalid_parameter", f"{name} must be an integer.")

    if parsed < 1:
        raise ApiError(400, "invalid_parameter", f"{name} must be greater than zero.")

    return parsed


def paginate(items: list[Any], page: int, page_size: int) -> dict[str, Any]:
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = items[start:end]
    total_pages = (total + page_size - 1) // page_size if total else 0

    return {
        "data": page_items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_previous": page > 1 and total > 0,
            "has_next": end < total,
        },
    }


def build_page_url(path: str, page: int, page_size: int) -> str:
    return f"{path}?page={page}&page_size={page_size}"


def add_pagination_links(
    response: dict[str, Any],
    path: str,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    pagination = response["pagination"]
    links = {
        "self": build_page_url(path, page, page_size),
        "first": build_page_url(path, 1, page_size),
    }

    if pagination["has_previous"]:
        links["previous"] = build_page_url(path, page - 1, page_size)

    if pagination["has_next"]:
        links["next"] = build_page_url(path, page + 1, page_size)

    if pagination["total_pages"] > 0:
        links["last"] = build_page_url(
            path,
            pagination["total_pages"],
            page_size,
        )

    response["links"] = links
    return response


def list_books(query: dict[str, list[str]]) -> dict[str, Any]:
    page = parse_positive_integer(
        query.get("page", [None])[0],
        "page",
        1,
    )
    page_size = parse_positive_integer(
        query.get("page_size", [None])[0],
        "page_size",
        2,
    )

    if page_size > 50:
        raise ApiError(
            400,
            "page_size_too_large",
            "page_size cannot exceed 50.",
        )

    category = query.get("category", [None])[0]
    author = query.get("author", [None])[0]
    search = query.get("q", [None])[0]

    books = repository.list()

    if category:
        books = [
            book for book in books
            if book.category.casefold() == category.casefold()
        ]

    if author:
        books = [
            book for book in books
            if author.casefold() in book.author.casefold()
        ]

    if search:
        search_value = search.casefold()
        books = [
            book for book in books
            if search_value in book.title.casefold()
            or search_value in book.author.casefold()
        ]

    # Stable ordering makes page-based pagination predictable.
    books.sort(key=lambda book: book.id)

    response = paginate(
        [book.to_dict() for book in books],
        page,
        page_size,
    )

    return add_pagination_links(
        response,
        "/api/v1/books",
        page,
        page_size,
    )


class ApiHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_json(
        self,
        status: int,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(
            body or {},
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")

        if headers:
            for key, value in headers.items():
                self.send_header(key, value)

        self.end_headers()
        self.wfile.write(payload)

    def _error(self, error: ApiError) -> None:
        self._send_json(
            error.status,
            {
                "error": {
                    "code": error.code,
                    "message": error.message,
                    "details": error.details,
                }
            },
        )

    def _parse_body(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length", "0")

        try:
            content_length = int(raw_length)
        except ValueError:
            raise ApiError(400, "invalid_content_length", "Invalid Content-Length.")

        if content_length > 1_000_000:
            raise ApiError(
                413,
                "payload_too_large",
                "Request body exceeds the 1 MB limit.",
            )

        if content_length == 0:
            raise ApiError(400, "empty_body", "Request body is required.")

        raw = self.rfile.read(content_length)

        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(
                400,
                "invalid_json",
                "Request body must contain valid UTF-8 JSON.",
            )

        if not isinstance(payload, dict):
            raise ApiError(
                400,
                "invalid_body",
                "The JSON request body must be an object.",
            )

        return payload

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/api/v1/books":
                self._send_json(200, list_books(query))
                return

            match = re.fullmatch(r"/api/v1/books/(\d+)", path)
            if match:
                book = repository.get(int(match.group(1)))
                self._send_json(
                    200,
                    {
                        "data": book.to_dict(),
                        "links": {
                            "self": path,
                            "collection": "/api/v1/books",
                        },
                    },
                )
                return

            if path == "/api/v1/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "api_version": API_VERSION,
                        "timestamp": utc_now(),
                    },
                )
                return

            if path == "/api/books":
                raise ApiError(
                    410,
                    "deprecated_endpoint",
                    "Use /api/v1/books.",
                )

            raise ApiError(
                404,
                "route_not_found",
                "The requested API resource does not exist.",
            )

        except ApiError as error:
            self._error(error)
        except Exception:
            self._send_json(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "An unexpected server error occurred.",
                    }
                },
            )

    def do_POST(self) -> None:
        try:
            parsed = urlparse(self.path)

            if parsed.path != "/api/v1/books":
                raise ApiError(
                    404,
                    "route_not_found",
                    "POST is supported only for /api/v1/books.",
                )

            payload = self._parse_body()
            book = repository.create(payload)

            self._send_json(
                201,
                {
                    "data": book.to_dict(),
                    "links": {
                        "self": f"/api/v1/books/{book.id}",
                        "collection": "/api/v1/books",
                    },
                },
                {
                    "Location": f"/api/v1/books/{book.id}",
                },
            )

        except ApiError as error:
            self._error(error)
        except Exception:
            self._send_json(
                500,
                {
                    "error": {
                        "code": "internal_error",
                        "message": "An unexpected server error occurred.",
                    }
                },
            )

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header(
            "Allow",
            "GET, POST, OPTIONS",
        )
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[{utc_now()}] {self.address_string()} - {format % args}")


def demonstrate_uri_design() -> None:
    print("\nURI design examples")
    print("Collection: /api/v1/books")
    print("Individual resource: /api/v1/books/5")
    print("Filtered collection: /api/v1/books?category=api-design")
    print("Paginated collection: /api/v1/books?page=2&page_size=2")
    print("Search: /api/v1/books?q=architecture")
    print("Avoid: /api/v1/getBooks")
    print("Avoid: /api/v1/deleteBook/5")


def demonstrate_pagination() -> None:
    print("\nPagination behavior")
    result = list_books({"page": ["1"], "page_size": ["2"]})
    print(json.dumps(result, indent=2))

    second_page = list_books({"page": ["2"], "page_size": ["2"]})
    print(json.dumps(second_page, indent=2))


def demonstrate_validation() -> None:
    print("\nValidation behavior")

    invalid_payloads = [
        {},
        {
            "title": "Invalid Year",
            "author": "Example",
            "category": "testing",
            "published_year": 3000,
        },
        {
            "title": "",
            "author": "Example",
            "category": "testing",
            "published_year": 2024,
        },
    ]

    for payload in invalid_payloads:
        try:
            repository.create(payload)
        except ApiError as error:
            print(
                json.dumps(
                    {
                        "status": error.status,
                        "code": error.code,
                        "message": error.message,
                    },
                    indent=2,
                )
            )


def request_json(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any]]:
    data = None

    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        f"http://{HOST}:{PORT}{path}",
        data=data,
        method=method,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, json.loads(
                response.read().decode("utf-8")
            )
    except urllib.error.HTTPError as error:
        payload = json.loads(error.read().decode("utf-8"))
        return error.code, payload


def demonstrate_live_api() -> None:
    print("\nStarting live API demonstration")

    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        status, body = request_json("GET", "/api/v1/books?page=1&page_size=2")
        print(f"GET /api/v1/books -> {status}")
        print(json.dumps(body, indent=2))

        status, body = request_json("GET", "/api/v1/books/3")
        print(f"\nGET /api/v1/books/3 -> {status}")
        print(json.dumps(body, indent=2))

        status, body = request_json(
            "POST",
            "/api/v1/books",
            {
                "title": "RESTful Web APIs",
                "author": "Leonard Richardson",
                "category": "api-design",
                "published_year": 2013,
            },
        )
        print(f"\nPOST /api/v1/books -> {status}")
        print(json.dumps(body, indent=2))

        status, body = request_json(
            "GET",
            "/api/v1/books/9999",
        )
        print(f"\nGET /api/v1/books/9999 -> {status}")
        print(json.dumps(body, indent=2))

        status, body = request_json(
            "GET",
            "/api/books",
        )
        print(f"\nGET /api/books -> {status}")
        print(json.dumps(body, indent=2))

    finally:
        server.shutdown()
        server.server_close()


def main() -> None:
    demonstrate_uri_design()
    demonstrate_pagination()
    demonstrate_validation()
    demonstrate_live_api()


if __name__ == "__main__":
    main()
