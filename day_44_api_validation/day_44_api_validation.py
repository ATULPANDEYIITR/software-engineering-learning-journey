"""
API Validation and Error Responses
==================================

A self-contained demonstration of API input validation, structured errors,
request parsing, field constraints, business rules, security boundaries,
and consistent HTTP responses.

Run:
    python api_validation.py

The program uses only the Python standard library. It simulates an HTTP API
without requiring a web framework or an external server.
"""

from __future__ import annotations

import json
import re
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Callable
from urllib.parse import urlsplit
from uuid import uuid4


# A common error representation keeps validation failures consistent across
# endpoints, even when different rules detect the failures.
@dataclass(frozen=True)
class APIError:
    status: int
    code: str
    message: str
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self, request_id: str) -> dict[str, Any]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details,
                "request_id": request_id,
            }
        }


@dataclass
class APIResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(self.body, indent=2, ensure_ascii=False)


class ValidationError(Exception):
    def __init__(self, details: list[dict[str, Any]]) -> None:
        super().__init__("Request validation failed")
        self.details = details


class HTTPError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def issue(
    field_name: str,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "field": field_name,
        "code": code,
        "message": message,
    }


def require_object(value: Any, field_name: str = "body") -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError([
            issue(field_name, "invalid_type", "Expected a JSON object.")
        ])
    return value


def validate_json_object(raw_body: bytes) -> dict[str, Any]:
    if not raw_body:
        raise HTTPError(400, "empty_body", "A JSON request body is required.")

    try:
        text = raw_body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPError(
            400, "invalid_encoding", "The request body must use UTF-8."
        ) from exc

    def reject_nonstandard_constant(value: str) -> None:
        raise ValueError(f"Non-standard JSON constant: {value}")

    try:
        value = json.loads(
            text,
            parse_constant=reject_nonstandard_constant,
        )
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise HTTPError(
            400,
            "invalid_json",
            "The request body is not valid JSON.",
        ) from exc

    return require_object(value)


def validate_email(value: Any, field_name: str = "email") -> str:
    if not isinstance(value, str):
        raise ValidationError([
            issue(field_name, "invalid_type", "Expected a string.")
        ])

    value = value.strip()

    if not value:
        raise ValidationError([
            issue(field_name, "required", "This field cannot be empty.")
        ])

    if len(value) > 254:
        raise ValidationError([
            issue(field_name, "too_long", "Email must not exceed 254 characters.")
        ])

    # This deliberately implements a practical application-level check,
    # not the full email-address grammar or mailbox verification.
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.fullmatch(pattern, value):
        raise ValidationError([
            issue(field_name, "invalid_email", "Enter a valid email address.")
        ])

    return value


def validate_positive_integer(
    value: Any,
    field_name: str,
    minimum: int = 1,
    maximum: int = 100,
) -> int:
    # bool is a subclass of int in Python, so reject it explicitly.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError([
            issue(field_name, "invalid_type", "Expected an integer.")
        ])

    if not minimum <= value <= maximum:
        raise ValidationError([
            issue(
                field_name,
                "out_of_range",
                f"Value must be between {minimum} and {maximum}.",
            )
        ])

    return value


def validate_display_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError([
            issue("name", "invalid_type", "Expected a string.")
        ])

    normalized = value.strip()

    if not 2 <= len(normalized) <= 80:
        raise ValidationError([
            issue(
                "name",
                "invalid_length",
                "Name must contain between 2 and 80 characters.",
            )
        ])

    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValidationError([
            issue(
                "name",
                "invalid_characters",
                "Control characters are not permitted.",
            )
        ])

    return normalized


def validate_url(value: Any, field_name: str = "website") -> str:
    if not isinstance(value, str):
        raise ValidationError([
            issue(field_name, "invalid_type", "Expected a string.")
        ])

    candidate = value.strip()

    if not candidate or len(candidate) > 2048:
        raise ValidationError([
            issue(
                field_name,
                "invalid_length",
                "URL must contain between 1 and 2048 characters.",
            )
        ])

    parsed = urlsplit(candidate)

    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValidationError([
            issue(
                field_name,
                "invalid_url",
                "Provide an HTTPS URL without embedded credentials.",
            )
        ])

    try:
        parsed.port
    except ValueError as exc:
        raise ValidationError([
            issue(field_name, "invalid_url", "URL contains an invalid port.")
        ]) from exc

    return candidate


def validate_create_user(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, Any]] = []
    allowed = {"name", "email", "age", "website"}

    for key in payload:
        if key not in allowed:
            errors.append(
                issue(key, "unknown_field", "This field is not accepted.")
            )

    validated: dict[str, Any] = {}

    for key, validator in (
        ("name", validate_display_name),
        ("email", validate_email),
    ):
        if key not in payload:
            errors.append(issue(key, "required", "This field is required."))
            continue

        try:
            validated[key] = validator(payload[key])
        except ValidationError as exc:
            errors.extend(exc.details)

    if "age" in payload:
        try:
            validated["age"] = validate_positive_integer(
                payload["age"], "age", minimum=18, maximum=120
            )
        except ValidationError as exc:
            errors.extend(exc.details)

    if "website" in payload:
        try:
            validated["website"] = validate_url(payload["website"])
        except ValidationError as exc:
            errors.extend(exc.details)

    if errors:
        raise ValidationError(errors)

    return validated


def validate_pagination(query: dict[str, str]) -> tuple[int, int]:
    allowed = {"limit", "offset"}
    unknown = set(query) - allowed

    if unknown:
        raise ValidationError([
            issue(key, "unknown_parameter", "Query parameter is not supported.")
            for key in sorted(unknown)
        ])

    def parse_integer(
        key: str,
        default: int,
        minimum: int,
        maximum: int,
    ) -> int:
        raw = query.get(key, str(default))

        # Reject floats, empty strings, signs, and other ambiguous formats.
        if not re.fullmatch(r"\d+", raw):
            raise ValidationError([
                issue(key, "invalid_integer", "Expected a non-negative integer.")
            ])

        return validate_positive_integer(
            int(raw),
            key,
            minimum=minimum,
            maximum=maximum,
        )

    limit = parse_integer("limit", 20, 1, 100)

    # Offset is allowed to be zero, unlike ordinary positive integers.
    raw_offset = query.get("offset", "0")
    if not re.fullmatch(r"\d+", raw_offset):
        raise ValidationError([
            issue("offset", "invalid_integer", "Offset must be non-negative.")
        ])

    offset = int(raw_offset)

    if offset > 1_000_000:
        raise ValidationError([
            issue("offset", "out_of_range", "Offset must not exceed 1000000.")
        ])

    return limit, offset


@dataclass
class User:
    user_id: int
    name: str
    email: str
    age: int | None = None
    website: str | None = None


class UserRepository:
    """In-memory persistence with a uniqueness constraint on email."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._email_index: dict[str, int] = {}
        self._next_id = 1

    def create(self, data: dict[str, Any]) -> User:
        email_key = data["email"].casefold()

        if email_key in self._email_index:
            raise HTTPError(
                409,
                "email_conflict",
                "A user with this email address already exists.",
                [issue("email", "already_exists", "Email must be unique.")],
            )

        user = User(
            user_id=self._next_id,
            name=data["name"],
            email=data["email"],
            age=data.get("age"),
            website=data.get("website"),
        )

        self._users[user.user_id] = user
        self._email_index[email_key] = user.user_id
        self._next_id += 1
        return user

    def list_users(self, limit: int, offset: int) -> list[User]:
        # Stable ID ordering makes pagination predictable for this simulation.
        users = sorted(self._users.values(), key=lambda user: user.user_id)
        return users[offset:offset + limit]

    def get(self, user_id: int) -> User:
        user = self._users.get(user_id)

        if user is None:
            raise HTTPError(404, "user_not_found", "The requested user does not exist.")

        return user


class UserAPI:
    """An HTTP-like application boundary with consistent error handling."""

    def __init__(self) -> None:
        self.repository = UserRepository()

    @staticmethod
    def _user_dict(user: User) -> dict[str, Any]:
        return {
            "id": user.user_id,
            "name": user.name,
            "email": user.email,
            "age": user.age,
            "website": user.website,
        }

    @staticmethod
    def _success(
        status: int,
        data: Any,
        request_id: str,
    ) -> APIResponse:
        return APIResponse(
            status=status,
            body={"data": data, "request_id": request_id},
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Request-ID": request_id,
                "Cache-Control": "no-store",
            },
        )

    @staticmethod
    def _error_response(
        error: APIError,
        request_id: str,
    ) -> APIResponse:
        return APIResponse(
            status=error.status,
            body=error.to_dict(request_id),
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Request-ID": request_id,
                "Cache-Control": "no-store",
            },
        )

    def handle(
        self,
        method: str,
        path: str,
        raw_body: bytes = b"",
        query: dict[str, str] | None = None,
        content_type: str = "application/json",
    ) -> APIResponse:
        request_id = str(uuid4())
        method = method.upper()
        query = query or {}

        try:
            if method == "POST" and path == "/users":
                if content_type.split(";", 1)[0].strip().lower() != "application/json":
                    raise HTTPError(
                        415,
                        "unsupported_media_type",
                        "Content-Type must be application/json.",
                    )

                payload = validate_json_object(raw_body)
                validated = validate_create_user(payload)
                user = self.repository.create(validated)

                return self._success(
                    201,
                    self._user_dict(user),
                    request_id,
                )

            if method == "GET" and path == "/users":
                limit, offset = validate_pagination(query)
                users = self.repository.list_users(limit, offset)

                return self._success(
                    200,
                    {
                        "items": [self._user_dict(user) for user in users],
                        "limit": limit,
                        "offset": offset,
                    },
                    request_id,
                )

            match = re.fullmatch(r"/users/([0-9]+)", path)
            if method == "GET" and match:
                user_id = int(match.group(1))

                if user_id < 1 or user_id > 2_147_483_647:
                    raise HTTPError(
                        400,
                        "invalid_user_id",
                        "User ID is outside the supported range.",
                    )

                return self._success(
                    200,
                    self._user_dict(self.repository.get(user_id)),
                    request_id,
                )

            raise HTTPError(
                404,
                "route_not_found",
                "The requested API route does not exist.",
            )

        except ValidationError as exc:
            return self._error_response(
                APIError(
                    422,
                    "validation_failed",
                    "One or more fields failed validation.",
                    exc.details,
                ),
                request_id,
            )

        except HTTPError as exc:
            return self._error_response(
                APIError(exc.status, exc.code, exc.message, exc.details),
                request_id,
            )

        except Exception:
            # Production systems should log the exception with request_id.
            # Internal exception text and stack traces must not reach clients.
            return self._error_response(
                APIError(
                    500,
                    "internal_server_error",
                    "An unexpected error occurred.",
                ),
                request_id,
            )


def demonstrate_api() -> None:
    api = UserAPI()

    requests = [
        (
            "Create valid user",
            "POST",
            "/users",
            json.dumps({
                "name": "Asha Verma",
                "email": "asha@example.com",
                "age": 29,
                "website": "https://example.com/profile",
            }).encode(),
            {},
            "application/json",
        ),
        (
            "Reject invalid fields",
            "POST",
            "/users",
            json.dumps({
                "name": " ",
                "email": "not-an-email",
                "age": True,
                "admin": True,
            }).encode(),
            {},
            "application/json",
        ),
        (
            "Reject malformed JSON",
            "POST",
            "/users",
            b'{"name": "Asha",',
            {},
            "application/json",
        ),
        (
            "Reject duplicate email",
            "POST",
            "/users",
            json.dumps({
                "name": "Asha Duplicate",
                "email": "ASHA@example.com",
            }).encode(),
            {},
            "application/json",
        ),
        (
            "List users",
            "GET",
            "/users",
            b"",
            {"limit": "10", "offset": "0"},
            "application/json",
        ),
        (
            "Reject invalid pagination",
            "GET",
            "/users",
            b"",
            {"limit": "1000"},
            "application/json",
        ),
        (
            "Return missing resource",
            "GET",
            "/users/999",
            b"",
            {},
            "application/json",
        ),
        (
            "Reject unsupported content type",
            "POST",
            "/users",
            b'{}',
            {},
            "text/plain",
        ),
    ]

    for label, method, path, body, query, content_type in requests:
        response = api.handle(method, path, body, query, content_type)
        print(f"\n{label}: HTTP {response.status}")
        print(response.to_json())


class APIValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.api = UserAPI()

    def request(self, payload: Any) -> APIResponse:
        return self.api.handle(
            "POST",
            "/users",
            json.dumps(payload).encode("utf-8"),
        )

    def test_valid_user_creation(self) -> None:
        response = self.request({
            "name": "Asha Verma",
            "email": "asha@example.com",
        })
        self.assertEqual(response.status, 201)
        self.assertEqual(response.body["data"]["id"], 1)

    def test_multiple_validation_errors(self) -> None:
        response = self.request({
            "name": "",
            "email": "invalid",
            "age": True,
        })
        self.assertEqual(response.status, 422)
        self.assertEqual(
            response.body["error"]["code"],
            "validation_failed",
        )
        self.assertGreaterEqual(
            len(response.body["error"]["details"]),
            2,
        )

    def test_boolean_is_not_an_integer(self) -> None:
        response = self.request({
            "name": "Asha",
            "email": "asha@example.com",
            "age": True,
        })
        self.assertEqual(response.status, 422)

    def test_malformed_json(self) -> None:
        response = self.api.handle(
            "POST",
            "/users",
            b'{"name":',
        )
        self.assertEqual(response.status, 400)

    def test_duplicate_email_is_case_insensitive(self) -> None:
        self.request({"name": "Asha", "email": "asha@example.com"})
        response = self.request({
            "name": "Another Asha",
            "email": "ASHA@example.com",
        })
        self.assertEqual(response.status, 409)

    def test_missing_user(self) -> None:
        response = self.api.handle("GET", "/users/88")
        self.assertEqual(response.status, 404)

    def test_invalid_content_type(self) -> None:
        response = self.api.handle(
            "POST",
            "/users",
            b'{}',
            content_type="text/plain",
        )
        self.assertEqual(response.status, 415)

    def test_invalid_pagination(self) -> None:
        response = self.api.handle(
            "GET",
            "/users",
            query={"limit": "0"},
        )
        self.assertEqual(response.status, 422)

    def test_error_contains_request_id(self) -> None:
        response = self.api.handle("GET", "/missing")
        self.assertIn("request_id", response.body["error"])
        self.assertEqual(
            response.headers["X-Request-ID"],
            response.body["error"]["request_id"],
        )

    def test_non_object_json(self) -> None:
        response = self.api.handle("POST", "/users", b"[]")
        self.assertEqual(response.status, 422)

    def test_unknown_field(self) -> None:
        response = self.request({
            "name": "Asha",
            "email": "asha@example.com",
            "is_admin": True,
        })
        self.assertEqual(response.status, 422)
        codes = {
            detail["code"]
            for detail in response.body["error"]["details"]
        }
        self.assertIn("unknown_field", codes)


if __name__ == "__main__":
    demonstrate_api()
    print("\nRunning validation tests...")
    unittest.main(argv=["api_validation.py"], exit=False)
