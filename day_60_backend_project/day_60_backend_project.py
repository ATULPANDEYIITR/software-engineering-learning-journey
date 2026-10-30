#!/usr/bin/env python3
"""Production-style task REST API using only the Python standard library."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import re
import sqlite3
import threading
import time
import uuid

from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterator
from urllib.parse import parse_qs, urlsplit


MAX_BODY_BYTES = 1_048_576
MAX_TITLE_LENGTH = 160
MAX_DESCRIPTION_LENGTH = 2_000
IDEMPOTENCY_TTL_HOURS = 24
RATE_LIMIT_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("task-api")


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS = {
    TaskStatus.PENDING: {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
    TaskStatus.IN_PROGRESS: {
        TaskStatus.PENDING,
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.COMPLETED: set(),
    TaskStatus.CANCELLED: set(),
}


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: datetime | None = None) -> str:
    current = value or utc_now()
    return current.isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_title(value: Any) -> str:
    if not isinstance(value, str):
        raise ApiError(400, "invalid_title", "Title must be a string.")

    value = value.strip()
    if not value:
        raise ApiError(400, "invalid_title", "Title cannot be empty.")

    if len(value) > MAX_TITLE_LENGTH:
        raise ApiError(
            400,
            "invalid_title",
            f"Title cannot exceed {MAX_TITLE_LENGTH} characters.",
        )

    return value


def validate_description(value: Any) -> str:
    if value is None:
        return ""

    if not isinstance(value, str):
        raise ApiError(
            400,
            "invalid_description",
            "Description must be a string.",
        )

    if len(value) > MAX_DESCRIPTION_LENGTH:
        raise ApiError(
            400,
            "invalid_description",
            f"Description cannot exceed {MAX_DESCRIPTION_LENGTH} characters.",
        )

    return value


def validate_status(value: Any) -> TaskStatus:
    if not isinstance(value, str):
        raise ApiError(400, "invalid_status", "Status must be a string.")

    try:
        return TaskStatus(value)
    except ValueError:
        allowed = ", ".join(status.value for status in TaskStatus)
        raise ApiError(
            400,
            "invalid_status",
            f"Status must be one of: {allowed}.",
        ) from None


def parse_if_match(value: str | None) -> int:
    if value is None:
        raise ApiError(
            428,
            "precondition_required",
            "Supply the current version through the If-Match header.",
        )

    match = re.fullmatch(r'"?([1-9][0-9]*)"?', value.strip())
    if not match:
        raise ApiError(
            400,
            "invalid_if_match",
            "If-Match must contain a positive version number.",
        )

    return int(match.group(1))


class RateLimiter:
    """Thread-safe sliding-window limiter keyed by client IP address."""

    def __init__(self, maximum: int, window_seconds: int):
        self.maximum = maximum
        self.window_seconds = window_seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, client: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self.lock:
            bucket = self.requests[client]

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.maximum:
                raise ApiError(
                    429,
                    "rate_limit_exceeded",
                    "Too many requests. Retry after the current rate-limit window.",
                )

            bucket.append(now)

            # Prevent inactive client addresses from accumulating indefinitely.
            if len(self.requests) > 10_000:
                inactive = [
                    key
                    for key, values in self.requests.items()
                    if not values or values[-1] <= cutoff
                ]
                for key in inactive:
                    self.requests.pop(key, None)


class TaskRepository:
    """SQLite persistence with parameterized queries and transactional writes."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(
            self.database_path,
            timeout=10,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            yield connection
        except Exception:
            if connection.in_transaction:
                connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                        CHECK(length(trim(title)) BETWEEN 1 AND 160),
                    description TEXT NOT NULL DEFAULT ''
                        CHECK(length(description) <= 2000),
                    status TEXT NOT NULL
                        CHECK(status IN (
                            'pending',
                            'in_progress',
                            'completed',
                            'cancelled'
                        )),
                    version INTEGER NOT NULL DEFAULT 1
                        CHECK(version > 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS idempotency_records (
                    idempotency_key TEXT PRIMARY KEY,
                    request_hash TEXT NOT NULL,
                    task_id TEXT NOT NULL
                        REFERENCES tasks(id) ON DELETE CASCADE,
                    expires_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_status_created
                    ON tasks(status, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_tasks_created
                    ON tasks(created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_idempotency_expiry
                    ON idempotency_records(expires_at);
                """
            )

    @staticmethod
    def task_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row is not None else None

    def create(
        self,
        title: str,
        description: str,
        idempotency_key: str,
    ) -> tuple[dict[str, Any], bool]:
        canonical_request = json.dumps(
            {"title": title, "description": description},
            sort_keys=True,
            separators=(",", ":"),
        )
        request_hash = hashlib.sha256(
            canonical_request.encode("utf-8")
        ).hexdigest()

        now = utc_now()
        expires_at = timestamp(now + timedelta(hours=IDEMPOTENCY_TTL_HOURS))

        with self.connection() as connection:
            # Serializes the read-check-create sequence across SQLite writers.
            connection.execute("BEGIN IMMEDIATE")

            connection.execute(
                "DELETE FROM idempotency_records WHERE expires_at <= ?",
                (timestamp(now),),
            )

            existing = connection.execute(
                """
                SELECT request_hash, task_id
                FROM idempotency_records
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()

            if existing is not None:
                if not hmac.compare_digest(
                    existing["request_hash"],
                    request_hash,
                ):
                    raise ApiError(
                        409,
                        "idempotency_conflict",
                        "This idempotency key was already used with a different request.",
                    )

                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?",
                    (existing["task_id"],),
                ).fetchone()

                if row is None:
                    raise ApiError(
                        409,
                        "idempotency_record_unavailable",
                        "The original resource is no longer available.",
                    )

                return self.task_dict(row), True

            task_id = str(uuid.uuid4())
            now_text = timestamp()

            connection.execute(
                """
                INSERT INTO tasks (
                    id, title, description, status,
                    version, created_at, updated_at
                )
                VALUES (?, ?, ?, 'pending', 1, ?, ?)
                """,
                (task_id, title, description, now_text, now_text),
            )

            connection.execute(
                """
                INSERT INTO idempotency_records (
                    idempotency_key, request_hash, task_id, expires_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (idempotency_key, request_hash, task_id, expires_at),
            )

            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            return self.task_dict(row), False

    def get(self, task_id: str) -> dict[str, Any] | None:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()
            return self.task_dict(row)

    def list(
        self,
        status: TaskStatus | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        with self.connection() as connection:
            if status is None:
                rows = connection.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY created_at DESC, id
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT * FROM tasks
                    WHERE status = ?
                    ORDER BY created_at DESC, id
                    LIMIT ? OFFSET ?
                    """,
                    (status.value, limit, offset),
                ).fetchall()

            return [dict(row) for row in rows]

    def update(
        self,
        task_id: str,
        expected_version: int,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        with self.connection() as connection:
            current = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            if current is None:
                raise ApiError(404, "task_not_found", "Task does not exist.")

            if current["version"] != expected_version:
                raise ApiError(
                    412,
                    "version_conflict",
                    "The task changed. Retrieve the latest representation before updating it.",
                )

            new_status = TaskStatus(current["status"])
            if "status" in changes:
                new_status = changes["status"]
                old_status = TaskStatus(current["status"])

                if (
                    new_status != old_status
                    and new_status not in ALLOWED_TRANSITIONS[old_status]
                ):
                    raise ApiError(
                        409,
                        "invalid_state_transition",
                        f"Cannot transition from {old_status.value} to {new_status.value}.",
                    )

            title = changes.get("title", current["title"])
            description = changes.get(
                "description",
                current["description"],
            )

            result = connection.execute(
                """
                UPDATE tasks
                SET title = ?,
                    description = ?,
                    status = ?,
                    version = version + 1,
                    updated_at = ?
                WHERE id = ? AND version = ?
                """,
                (
                    title,
                    description,
                    new_status.value,
                    timestamp(),
                    task_id,
                    expected_version,
                ),
            )

            if result.rowcount != 1:
                raise ApiError(
                    412,
                    "version_conflict",
                    "The task changed during the update.",
                )

            row = connection.execute(
                "SELECT * FROM tasks WHERE id = ?",
                (task_id,),
            ).fetchone()

            return self.task_dict(row)

    def delete(self, task_id: str, expected_version: int) -> None:
        with self.connection() as connection:
            result = connection.execute(
                """
                DELETE FROM tasks
                WHERE id = ? AND version = ?
                """,
                (task_id, expected_version),
            )

            if result.rowcount == 0:
                exists = connection.execute(
                    "SELECT 1 FROM tasks WHERE id = ?",
                    (task_id,),
                ).fetchone()

                if exists is None:
                    raise ApiError(
                        404,
                        "task_not_found",
                        "Task does not exist.",
                    )

                raise ApiError(
                    412,
                    "version_conflict",
                    "The task changed. Retrieve its latest version before deleting it.",
                )


class TaskApiHandler(BaseHTTPRequestHandler):
    server_version = "TaskAPI/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def repository(self) -> TaskRepository:
        return self.server.repository  # type: ignore[attr-defined]

    @property
    def rate_limiter(self) -> RateLimiter:
        return self.server.rate_limiter  # type: ignore[attr-defined]

    @property
    def api_token(self) -> str:
        return self.server.api_token  # type: ignore[attr-defined]

    def log_message(self, format_string: str, *args: Any) -> None:
        # Avoid the default logger, which may record query strings or sensitive data.
        return

    def send_json(
        self,
        status: int,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> None:
        body = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Request-ID", self.request_id)

        for name, value in (headers or {}).items():
            self.send_header(name, value)

        self.end_headers()
        self.wfile.write(body)

    def authenticate(self) -> None:
        authorization = self.headers.get("Authorization", "")
        supplied = (
            authorization[7:]
            if authorization.startswith("Bearer ")
            else ""
        )

        if not hmac.compare_digest(supplied, self.api_token):
            raise ApiError(
                401,
                "unauthorized",
                "A valid bearer token is required.",
            )

    def read_json(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "")
        if content_type.split(";")[0].strip().lower() != "application/json":
            raise ApiError(
                415,
                "unsupported_media_type",
                "Content-Type must be application/json.",
            )

        length_header = self.headers.get("Content-Length")
        if length_header is None:
            raise ApiError(
                411,
                "content_length_required",
                "Content-Length is required.",
            )

        try:
            length = int(length_header)
        except ValueError:
            raise ApiError(
                400,
                "invalid_content_length",
                "Content-Length must be an integer.",
            ) from None

        if length <= 0:
            raise ApiError(400, "empty_body", "A JSON request body is required.")

        if length > MAX_BODY_BYTES:
            raise ApiError(413, "payload_too_large", "Request body is too large.")

        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ApiError(400, "incomplete_body", "Request body was incomplete.")

        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(
                400,
                "invalid_json",
                "Request body must contain valid UTF-8 JSON.",
            ) from None

        if not isinstance(value, dict):
            raise ApiError(
                400,
                "invalid_json_shape",
                "The JSON request body must be an object.",
            )

        return value

    @staticmethod
    def validate_idempotency_key(value: str | None) -> str:
        if value is None or not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
            raise ApiError(
                400,
                "invalid_idempotency_key",
                "Idempotency-Key must contain 8 to 128 permitted characters.",
            )
        return value

    @staticmethod
    def validate_query_integer(
        value: str | None,
        default: int,
        minimum: int,
        maximum: int,
        name: str,
    ) -> int:
        if value is None:
            return default

        try:
            parsed = int(value)
        except ValueError:
            raise ApiError(
                400,
                f"invalid_{name}",
                f"{name} must be an integer.",
            ) from None

        if not minimum <= parsed <= maximum:
            raise ApiError(
                400,
                f"invalid_{name}",
                f"{name} must be between {minimum} and {maximum}.",
            )

        return parsed

    def handle_request(self) -> None:
        self.request_id = str(uuid.uuid4())
        status = 500
        started = time.monotonic()

        try:
            parsed_url = urlsplit(self.path)
            path = parsed_url.path
            method = self.command.upper()

            if path == "/health":
                if method != "GET":
                    raise ApiError(405, "method_not_allowed", "Use GET.")
                self.send_json(
                    200,
                    {"status": "healthy", "request_id": self.request_id},
                )
                status = 200
                return

            if not path.startswith("/v1/"):
                raise ApiError(404, "route_not_found", "Route does not exist.")

            self.rate_limiter.check(self.client_address[0])
            self.authenticate()

            query = parse_qs(parsed_url.query, keep_blank_values=True)
            parts = path.strip("/").split("/")

            if parts == ["v1", "tasks"]:
                self.handle_collection(method, query)
            elif len(parts) == 3 and parts[:2] == ["v1", "tasks"]:
                self.handle_item(method, parts[2])
            else:
                raise ApiError(404, "route_not_found", "Route does not exist.")

            status = 200
        except ApiError as error:
            status = error.status
            self.send_json(
                error.status,
                {
                    "error": {
                        "code": error.code,
                        "message": error.message,
                    },
                    "request_id": self.request_id,
                },
            )
        except sqlite3.Error:
            logger.exception("Database failure request_id=%s", self.request_id)
            status = 503
            self.send_json(
                503,
                {
                    "error": {
                        "code": "database_unavailable",
                        "message": "The service could not complete the database operation.",
                    },
                    "request_id": self.request_id,
                },
            )
        except Exception:
            logger.exception("Unhandled request failure request_id=%s", self.request_id)
            status = 500
            self.send_json(
                500,
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected server error occurred.",
                    },
                    "request_id": self.request_id,
                },
            )
        finally:
            elapsed_ms = round((time.monotonic() - started) * 1000, 2)
            logger.info(
                "request_id=%s method=%s path=%s status=%s duration_ms=%s",
                self.request_id,
                self.command,
                urlsplit(self.path).path,
                status,
                elapsed_ms,
            )

    def handle_collection(
        self,
        method: str,
        query: dict[str, list[str]],
    ) -> None:
        if method == "GET":
            status_value = query.get("status", [None])[0]
            status_filter = (
                validate_status(status_value)
                if status_value is not None
                else None
            )

            limit = self.validate_query_integer(
                query.get("limit", [None])[0],
                default=20,
                minimum=1,
                maximum=100,
                name="limit",
            )
            offset = self.validate_query_integer(
                query.get("offset", [None])[0],
                default=0,
                minimum=0,
                maximum=1_000_000,
                name="offset",
            )

            tasks = self.repository.list(status_filter, limit, offset)
            self.send_json(
                200,
                {
                    "data": tasks,
                    "pagination": {
                        "limit": limit,
                        "offset": offset,
                        "returned": len(tasks),
                    },
                    "request_id": self.request_id,
                },
            )
            return

        if method == "POST":
            body = self.read_json()
            unknown = set(body) - {"title", "description"}
            if unknown:
                raise ApiError(
                    400,
                    "unknown_fields",
                    "Unsupported fields: " + ", ".join(sorted(unknown)),
                )

            title = validate_title(body.get("title"))
            description = validate_description(body.get("description"))
            key = self.validate_idempotency_key(
                self.headers.get("Idempotency-Key")
            )

            task, replayed = self.repository.create(title, description, key)
            response_headers = {"ETag": f'"{task["version"]}"'}

            if replayed:
                response_headers["Idempotent-Replayed"] = "true"

            self.send_json(
                200 if replayed else 201,
                {"data": task, "request_id": self.request_id},
                response_headers,
            )
            return

        raise ApiError(
            405,
            "method_not_allowed",
            "Supported methods for this resource are GET and POST.",
        )

    def handle_item(self, method: str, task_id: str) -> None:
        try:
            normalized_id = str(uuid.UUID(task_id))
        except ValueError:
            raise ApiError(404, "task_not_found", "Task does not exist.") from None

        if method == "GET":
            task = self.repository.get(normalized_id)
            if task is None:
                raise ApiError(404, "task_not_found", "Task does not exist.")

            self.send_json(
                200,
                {"data": task, "request_id": self.request_id},
                {"ETag": f'"{task["version"]}"'},
            )
            return

        if method == "PATCH":
            expected_version = parse_if_match(
                self.headers.get("If-Match")
            )
            body = self.read_json()

            allowed_fields = {"title", "description", "status"}
            unknown = set(body) - allowed_fields
            if unknown:
                raise ApiError(
                    400,
                    "unknown_fields",
                    "Unsupported fields: " + ", ".join(sorted(unknown)),
                )

            if not body:
                raise ApiError(
                    400,
                    "empty_patch",
                    "At least one field must be supplied.",
                )

            changes: dict[str, Any] = {}
            if "title" in body:
                changes["title"] = validate_title(body["title"])
            if "description" in body:
                changes["description"] = validate_description(
                    body["description"]
                )
            if "status" in body:
                changes["status"] = validate_status(body["status"])

            task = self.repository.update(
                normalized_id,
                expected_version,
                changes,
            )
            self.send_json(
                200,
                {"data": task, "request_id": self.request_id},
                {"ETag": f'"{task["version"]}"'},
            )
            return

        if method == "DELETE":
            expected_version = parse_if_match(
                self.headers.get("If-Match")
            )
            self.repository.delete(normalized_id, expected_version)
            self.send_json(
                200,
                {
                    "data": {"id": normalized_id, "deleted": True},
                    "request_id": self.request_id,
                },
            )
            return

        raise ApiError(
            405,
            "method_not_allowed",
            "Supported methods for this resource are GET, PATCH and DELETE.",
        )

    def do_GET(self) -> None:
        self.handle_request()

    def do_POST(self) -> None:
        self.handle_request()

    def do_PATCH(self) -> None:
        self.handle_request()

    def do_DELETE(self) -> None:
        self.handle_request()

    def do_PUT(self) -> None:
        self.handle_request()

    def do_OPTIONS(self) -> None:
        self.handle_request()


class TaskApiServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        handler_class: type[BaseHTTPRequestHandler],
        repository: TaskRepository,
        api_token: str,
    ):
        super().__init__(address, handler_class)
        self.repository = repository
        self.api_token = api_token
        self.rate_limiter = RateLimiter(
            RATE_LIMIT_REQUESTS,
            RATE_LIMIT_WINDOW_SECONDS,
        )


def main() -> None:
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8080"))
    database_path = os.getenv("API_DB_PATH", "tasks_api.db")
    api_token = os.getenv("API_TOKEN", "local-development-token")

    if len(api_token) < 16:
        raise SystemExit("API_TOKEN must contain at least 16 characters.")

    if api_token == "local-development-token":
        logger.warning(
            "Using the development token. Set API_TOKEN before deployment."
        )

    repository = TaskRepository(database_path)
    server = TaskApiServer(
        (host, port),
        TaskApiHandler,
        repository,
        api_token,
    )

    logger.info("Task API listening on http://%s:%s", host, port)
    logger.info("Database path: %s", database_path)

    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        logger.info("Shutdown requested.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
