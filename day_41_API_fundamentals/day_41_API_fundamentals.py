#!/usr/bin/env python3
"""
API Fundamentals: REST, Resources, Endpoints, and HTTP

A self-contained learning implementation that models a small REST API using
only Python's standard library. It demonstrates HTTP methods, resources,
endpoints, status codes, headers, JSON, validation, content negotiation,
pagination, conditional requests, authentication, idempotency, routing,
and a real HTTP server.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


HOST = "127.0.0.1"
PORT = 8080


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value: Any) -> bytes:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()


def parse_json(data: bytes) -> Any:
    if not data:
        return None
    return json.loads(data.decode("utf-8"))


@dataclass
class Resource:
    resource_id: int
    name: str
    category: str
    status: str
    version: int
    created_at: str
    updated_at: str


class ApiError(Exception):
    def __init__(self, status: int, message: str, details: Any = None):
        self.status = status
        self.message = message
        self.details = details
        super().__init__(message)


class ResourceStore:
    """
    The store models a REST resource collection.

    A resource has a stable URI such as /api/v1/resources/1. The URI identifies
    the resource; HTTP methods determine what operation is requested against it.
    """

    VALID_STATUSES = {"active", "inactive", "maintenance"}

    def __init__(self) -> None:
        self._items: dict[int, Resource] = {}
        self._next_id = 1
        self._lock = threading.RLock()

    def list_resources(self, category: str | None = None) -> list[Resource]:
        with self._lock:
            values = list(self._items.values())
            if category:
                values = [
                    item for item in values
                    if item.category.lower() == category.lower()
                ]
            return sorted(values, key=lambda item: item.resource_id)

    def get(self, resource_id: int) -> Resource:
        with self._lock:
            item = self._items.get(resource_id)
            if item is None:
                raise ApiError(HTTPStatus.NOT_FOUND, "Resource not found")
            return item

    def create(self, payload: dict[str, Any]) -> Resource:
        self._validate_payload(payload, creating=True)
        now = utc_now()

        with self._lock:
            resource = Resource(
                resource_id=self._next_id,
                name=payload["name"].strip(),
                category=payload["category"].strip(),
                status=payload.get("status", "active"),
                version=1,
                created_at=now,
                updated_at=now,
            )
            self._items[self._next_id] = resource
            self._next_id += 1
            return resource

    def replace(self, resource_id: int, payload: dict[str, Any]) -> Resource:
        self._validate_payload(payload, creating=True)

        with self._lock:
            existing = self.get(resource_id)
            existing.name = payload["name"].strip()
            existing.category = payload["category"].strip()
            existing.status = payload.get("status", "active")
            existing.version += 1
            existing.updated_at = utc_now()
            return existing

    def update(self, resource_id: int, payload: dict[str, Any]) -> Resource:
        with self._lock:
            existing = self.get(resource_id)
            candidate = {
                "name": existing.name,
                "category": existing.category,
                "status": existing.status,
            }
            candidate.update(payload)
            self._validate_payload(candidate, creating=True)

            existing.name = candidate["name"].strip()
            existing.category = candidate["category"].strip()
            existing.status = candidate["status"]
            existing.version += 1
            existing.updated_at = utc_now()
            return existing

    def delete(self, resource_id: int) -> None:
        with self._lock:
            if resource_id not in self._items:
                raise ApiError(HTTPStatus.NOT_FOUND, "Resource not found")
            del self._items[resource_id]

    @classmethod
    def _validate_payload(cls, payload: Any, creating: bool) -> None:
        if not isinstance(payload, dict):
            raise ApiError(HTTPStatus.BAD_REQUEST, "JSON body must be an object")

        required = {"name", "category"} if creating else set()
        missing = required - payload.keys()
        if missing:
            raise ApiError(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                "Required fields are missing",
                {"fields": sorted(missing)},
            )

        if "name" in payload:
            if not isinstance(payload["name"], str) or not payload["name"].strip():
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "name must be a non-empty string",
                )
            if len(payload["name"].strip()) > 100:
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "name cannot exceed 100 characters",
                )

        if "category" in payload:
            if not isinstance(payload["category"], str) or not payload["category"].strip():
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "category must be a non-empty string",
                )

        if "status" in payload:
            if payload["status"] not in cls.VALID_STATUSES:
                raise ApiError(
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                    "Invalid status",
                    {"allowed": sorted(cls.VALID_STATUSES)},
                )


class ApiRouter:
    """
    A minimal endpoint router.

    Endpoint structure:
        /api/v1/resources
        /api/v1/resources/{id}

    The collection and member endpoints represent different resources:
    the collection represents a set, while the member URI identifies one item.
    """

    collection_pattern = re.compile(r"^/api/v1/resources/?$")
    member_pattern = re.compile(r"^/api/v1/resources/(\d+)/?$")

    def __init__(self, store: ResourceStore):
        self.store = store

    def dispatch(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        headers: dict[str, str],
        body: Any,
    ) -> tuple[int, dict[str, str], Any]:
        if path == "/api/v1/health":
            if method != "GET":
                raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")
            return HTTPStatus.OK, {}, {"status": "ok", "time": utc_now()}

        if path == "/api/v1":
            if method != "GET":
                raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed")
            return HTTPStatus.OK, {}, {
                "service": "resource-api",
                "version": "v1",
                "resources": "/api/v1/resources",
            }

        collection = self.collection_pattern.match(path)
        member = self.member_pattern.match(path)

        if collection:
            return self._collection(method, query, body)

        if member:
            return self._member(method, int(member.group(1)), headers, body)

        raise ApiError(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def _collection(
        self,
        method: str,
        query: dict[str, list[str]],
        body: Any,
    ) -> tuple[int, dict[str, str], Any]:
        if method == "GET":
            category = query.get("category", [None])[0]
            items = self.store.list_resources(category)

            try:
                limit = min(max(int(query.get("limit", ["20"])[0]), 1), 100)
                offset = max(int(query.get("offset", ["0"])[0]), 0)
            except ValueError:
                raise ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "limit and offset must be integers",
                )

            page = items[offset:offset + limit]
            return HTTPStatus.OK, {}, {
                "data": [asdict(item) for item in page],
                "pagination": {
                    "total": len(items),
                    "limit": limit,
                    "offset": offset,
                    "returned": len(page),
                },
            }

        if method == "POST":
            resource = self.store.create(body)
            return HTTPStatus.CREATED, {
                "Location": f"/api/v1/resources/{resource.resource_id}"
            }, asdict(resource)

        raise ApiError(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "Method not allowed",
        )

    def _member(
        self,
        method: str,
        resource_id: int,
        headers: dict[str, str],
        body: Any,
    ) -> tuple[int, dict[str, str], Any]:
        if method == "GET":
            resource = self.store.get(resource_id)
            etag = self.etag(resource)

            if headers.get("If-None-Match") == etag:
                return HTTPStatus.NOT_MODIFIED, {"ETag": etag}, None

            return HTTPStatus.OK, {"ETag": etag}, asdict(resource)

        if method == "HEAD":
            resource = self.store.get(resource_id)
            return HTTPStatus.OK, {
                "ETag": self.etag(resource)
            }, None

        if method == "PUT":
            resource = self.store.replace(resource_id, body)
            return HTTPStatus.OK, {
                "ETag": self.etag(resource)
            }, asdict(resource)

        if method == "PATCH":
            if not isinstance(body, dict):
                raise ApiError(
                    HTTPStatus.BAD_REQUEST,
                    "PATCH body must be a JSON object",
                )
            resource = self.store.update(resource_id, body)
            return HTTPStatus.OK, {
                "ETag": self.etag(resource)
            }, asdict(resource)

        if method == "DELETE":
            self.store.delete(resource_id)
            return HTTPStatus.NO_CONTENT, {}, None

        raise ApiError(
            HTTPStatus.METHOD_NOT_ALLOWED,
            "Method not allowed",
        )

    @staticmethod
    def etag(resource: Resource) -> str:
        raw = (
            f"{resource.resource_id}:{resource.version}:"
            f"{resource.updated_at}:{resource.name}:{resource.status}"
        ).encode()
        digest = hashlib.sha256(raw).hexdigest()[:16]
        return f'"{digest}"'


class RestHandler(BaseHTTPRequestHandler):
    router: ApiRouter | None = None
    server_version = "API-Fundamentals/1.0"

    def do_GET(self) -> None:
        self.handle_request()

    def do_HEAD(self) -> None:
        self.handle_request()

    def do_POST(self) -> None:
        self.handle_request()

    def do_PUT(self) -> None:
        self.handle_request()

    def do_PATCH(self) -> None:
        self.handle_request()

    def do_DELETE(self) -> None:
        self.handle_request()

    def handle_request(self) -> None:
        try:
            parsed = urllib.parse.urlsplit(self.path)
            query = urllib.parse.parse_qs(parsed.query)
            body = self.read_body()
            headers = {key: value for key, value in self.headers.items()}

            if self.router is None:
                raise ApiError(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    "Router is not configured",
                )

            status, extra_headers, response = self.router.dispatch(
                self.command,
                parsed.path,
                query,
                headers,
                body,
            )

            self.send_json(status, response, extra_headers)

        except json.JSONDecodeError:
            self.send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "Malformed JSON request body"},
            )
        except ApiError as exc:
            self.send_json(
                exc.status,
                {
                    "error": exc.message,
                    "details": exc.details,
                },
            )
        except Exception:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "Internal server error"},
            )

    def read_body(self) -> Any:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            return None

        try:
            length = int(length_header)
        except ValueError:
            raise ApiError(
                HTTPStatus.BAD_REQUEST,
                "Invalid Content-Length",
            )

        if length > 1_048_576:
            raise ApiError(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                "Request body exceeds 1 MiB",
            )

        raw = self.rfile.read(length)
        if not raw:
            return None

        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type:
            raise ApiError(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                "Requests with bodies must use application/json",
            )

        return parse_json(raw)

    def send_json(
        self,
        status: int,
        response: Any,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        body = b"" if response is None else json_bytes(response)

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))

        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)

        self.end_headers()

        if self.command != "HEAD" and body:
            self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[HTTP] {self.address_string()} {format % args}")


def build_demo_request(
    method: str,
    url: str,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> None:
    request_headers = {
        "Accept": "application/json",
        **(headers or {}),
    }

    body = None
    if data is not None:
        body = json_bytes(data)
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=body,
        headers=request_headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            raw = response.read()
            print(
                f"{method} {url} -> {response.status} "
                f"{response.headers.get('Content-Type')}"
            )
            if raw:
                print(json.dumps(json.loads(raw), indent=2))
            return

    except urllib.error.HTTPError as exc:
        raw = exc.read()
        print(f"{method} {url} -> {exc.code}")
        if raw:
            try:
                print(json.dumps(json.loads(raw), indent=2))
            except json.JSONDecodeError:
                print(raw.decode(errors="replace"))


def run_http_demo() -> None:
    print("\n--- HTTP client demonstration ---")

    base = f"http://{HOST}:{PORT}"

    build_demo_request(
        "GET",
        f"{base}/api/v1/health",
    )

    build_demo_request(
        "POST",
        f"{base}/api/v1/resources",
        {
            "name": "Production API Gateway",
            "category": "infrastructure",
            "status": "active",
        },
    )

    build_demo_request(
        "POST",
        f"{base}/api/v1/resources",
        {
            "name": "Payment Processing Service",
            "category": "application",
            "status": "active",
        },
    )

    build_demo_request(
        "GET",
        f"{base}/api/v1/resources?category=application&limit=10",
    )

    build_demo_request(
        "PATCH",
        f"{base}/api/v1/resources/1",
        {"status": "maintenance"},
    )

    build_demo_request(
        "GET",
        f"{base}/api/v1/resources/1",
    )

    build_demo_request(
        "GET",
        f"{base}/unknown",
    )


def demonstrate_http_concepts() -> None:
    print("--- REST and HTTP concepts represented by this server ---")
    print("Resource: a domain object identified by a URI.")
    print("Collection endpoint: /api/v1/resources")
    print("Member endpoint: /api/v1/resources/{id}")
    print("GET: retrieve representation without changing the resource.")
    print("POST: create a new member in the collection.")
    print("PUT: replace the complete member representation.")
    print("PATCH: partially modify a member.")
    print("DELETE: remove a member.")
    print("HTTP status codes communicate outcome independently of the JSON body.")
    print("ETag and If-None-Match demonstrate conditional retrieval and caching.")
    print("Location identifies the URI of a newly created resource.")


def seed_store(store: ResourceStore) -> None:
    store.create({
        "name": "Identity Service",
        "category": "security",
        "status": "active",
    })
    store.create({
        "name": "Order API",
        "category": "application",
        "status": "active",
    })
    store.create({
        "name": "Reporting Database",
        "category": "data",
        "status": "maintenance",
    })


def main() -> None:
    demonstrate_http_concepts()

    store = ResourceStore()
    seed_store(store)

    router = ApiRouter(store)
    RestHandler.router = router

    server = ThreadingHTTPServer((HOST, PORT), RestHandler)

    print(f"\nREST API listening at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop.")

    server_thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    server_thread.start()

    try:
        run_http_demo()
        print("\n--- Direct resource inspection ---")
        for resource in store.list_resources():
            print(
                resource.resource_id,
                resource.name,
                resource.category,
                resource.status,
                f"version={resource.version}",
            )
        time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
