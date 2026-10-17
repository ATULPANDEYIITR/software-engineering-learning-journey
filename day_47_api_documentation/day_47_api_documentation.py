#!/usr/bin/env python3
"""
API Documentation, OpenAPI, Swagger, and API Contracts.

A self-contained repository-style learning implementation that demonstrates:
- API contract modeling and validation.
- OpenAPI 3.1 document construction and structural checks.
- Request and response validation against declared schemas.
- Parameter serialization, authentication, and HTTP semantics.
- Contract-first development and implementation conformance.
- Versioning, compatibility checks, and breaking-change detection.
- Consumer-driven expectations and deterministic contract tests.
- Documentation generation, artifact export, and failure reporting.

Run:
    python api_contract_lab.py

Only the Python standard library is required.
"""

from __future__ import annotations

import copy
import json
import re
import unittest
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, quote, urlencode, urlsplit


class ContractError(Exception):
    """Raised when an API contract or payload violates a declared rule."""


class AuthenticationError(Exception):
    """Raised when a request does not satisfy the authentication contract."""


class ApiError(Exception):
    """Represents a documented HTTP error response."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def to_response(self) -> "ApiResponse":
        return ApiResponse(
            status=self.status,
            body={"error": {"code": self.code, "message": self.message}},
            headers={"Content-Type": "application/json"},
        )


class HttpMethod(str, Enum):
    GET = "GET"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True)
class ParameterContract:
    name: str
    location: str
    required: bool
    schema: dict[str, Any]
    description: str


@dataclass(frozen=True)
class OperationContract:
    operation_id: str
    method: HttpMethod
    path: str
    summary: str
    parameters: tuple[ParameterContract, ...]
    request_schema: str | None
    responses: dict[str, str]
    security: bool = True


def validate_schema(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
) -> list[ValidationIssue]:
    """
    Validate a useful subset of JSON Schema.

    Supported keywords include type, required, properties, additionalProperties,
    items, enum, minimum, maximum, minLength, maxLength, pattern, minItems,
    maxItems, and format=email. The subset is explicit: this is not a complete
    JSON Schema implementation and should not be substituted for one in
    production when arbitrary OpenAPI schemas must be validated.
    """
    issues: list[ValidationIssue] = []
    expected = schema.get("type")

    type_matches = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "number": lambda v: isinstance(v, (int, float))
        and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }

    if expected in type_matches and not type_matches[expected](value):
        return [
            ValidationIssue(
                path,
                f"expected {expected}, received {type(value).__name__}",
            )
        ]

    if "enum" in schema and value not in schema["enum"]:
        issues.append(
            ValidationIssue(path, f"value must be one of {schema['enum']}")
        )

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for name in required:
            if name not in value:
                issues.append(
                    ValidationIssue(f"{path}.{name}", "required property is missing")
                )

        for name, child_value in value.items():
            child_schema = properties.get(name)
            if child_schema is None:
                if schema.get("additionalProperties") is False:
                    issues.append(
                        ValidationIssue(f"{path}.{name}", "unknown property")
                    )
                elif isinstance(schema.get("additionalProperties"), dict):
                    issues.extend(
                        validate_schema(
                            child_value,
                            schema["additionalProperties"],
                            f"{path}.{name}",
                        )
                    )
                continue

            issues.extend(
                validate_schema(child_value, child_schema, f"{path}.{name}")
            )

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            issues.append(
                ValidationIssue(path, f"must contain at least {schema['minItems']} items")
            )
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            issues.append(
                ValidationIssue(path, f"must contain at most {schema['maxItems']} items")
            )

        if "items" in schema:
            for index, item in enumerate(value):
                issues.extend(
                    validate_schema(item, schema["items"], f"{path}[{index}]")
                )

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            issues.append(
                ValidationIssue(path, f"must have at least {schema['minLength']} characters")
            )
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            issues.append(
                ValidationIssue(path, f"must have at most {schema['maxLength']} characters")
            )
        if "pattern" in schema and re.search(schema["pattern"], value) is None:
            issues.append(
                ValidationIssue(path, f"does not match pattern {schema['pattern']!r}")
            )
        if schema.get("format") == "email":
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                issues.append(ValidationIssue(path, "must be an email address"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            issues.append(ValidationIssue(path, f"must be >= {schema['minimum']}"))
        if "maximum" in schema and value > schema["maximum"]:
            issues.append(ValidationIssue(path, f"must be <= {schema['maximum']}"))

    return issues


COMPONENT_SCHEMAS: dict[str, dict[str, Any]] = {
    "Project": {
        "type": "object",
        "required": ["id", "name", "status"],
        "properties": {
            "id": {"type": "integer", "minimum": 1},
            "name": {"type": "string", "minLength": 3, "maxLength": 100},
            "status": {
                "type": "string",
                "enum": ["planned", "active", "completed"],
            },
            "owner": {"type": "string", "format": "email"},
            "createdAt": {"type": "string", "format": "date-time"},
        },
        "additionalProperties": False,
    },
    "CreateProject": {
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string", "minLength": 3, "maxLength": 100},
            "status": {
                "type": "string",
                "enum": ["planned", "active", "completed"],
            },
            "owner": {"type": "string", "format": "email"},
        },
        "additionalProperties": False,
    },
    "Error": {
        "type": "object",
        "required": ["error"],
        "properties": {
            "error": {
                "type": "object",
                "required": ["code", "message"],
                "properties": {
                    "code": {"type": "string", "minLength": 1},
                    "message": {"type": "string", "minLength": 1},
                },
                "additionalProperties": False,
            }
        },
        "additionalProperties": False,
    },
}


OPERATIONS = (
    OperationContract(
        "listProjects",
        HttpMethod.GET,
        "/projects",
        "List projects with bounded pagination",
        (
            ParameterContract(
                "limit",
                "query",
                False,
                {"type": "integer", "minimum": 1, "maximum": 100},
                "Maximum number of projects to return.",
            ),
            ParameterContract(
                "offset",
                "query",
                False,
                {"type": "integer", "minimum": 0},
                "Number of projects to skip.",
            ),
        ),
        None,
        {"200": "ProjectList", "401": "Error"},
    ),
    OperationContract(
        "createProject",
        HttpMethod.POST,
        "/projects",
        "Create a project",
        (),
        "CreateProject",
        {"201": "Project", "400": "Error", "401": "Error", "409": "Error"},
    ),
    OperationContract(
        "getProject",
        HttpMethod.GET,
        "/projects/{projectId}",
        "Retrieve one project",
        (
            ParameterContract(
                "projectId",
                "path",
                True,
                {"type": "integer", "minimum": 1},
                "Unique project identifier.",
            ),
        ),
        None,
        {"200": "Project", "401": "Error", "404": "Error"},
    ),
    OperationContract(
        "updateProject",
        HttpMethod.PATCH,
        "/projects/{projectId}",
        "Update selected project fields",
        (
            ParameterContract(
                "projectId",
                "path",
                True,
                {"type": "integer", "minimum": 1},
                "Unique project identifier.",
            ),
        ),
        "UpdateProject",
        {"200": "Project", "400": "Error", "401": "Error", "404": "Error"},
    ),
    OperationContract(
        "deleteProject",
        HttpMethod.DELETE,
        "/projects/{projectId}",
        "Delete a project",
        (
            ParameterContract(
                "projectId",
                "path",
                True,
                {"type": "integer", "minimum": 1},
                "Unique project identifier.",
            ),
        ),
        None,
        {"204": "NoContent", "401": "Error", "404": "Error"},
    ),
)


def build_openapi_document() -> dict[str, Any]:
    """Build an OpenAPI 3.1 document from the explicit contract registry."""
    paths: dict[str, Any] = {}

    for operation in OPERATIONS:
        parameters = [
            {
                "name": parameter.name,
                "in": parameter.location,
                "required": parameter.required,
                "description": parameter.description,
                "schema": copy.deepcopy(parameter.schema),
            }
            for parameter in operation.parameters
        ]

        response_definitions: dict[str, Any] = {}
        for status, schema_name in operation.responses.items():
            response: dict[str, Any] = {
                "description": f"HTTP {status} response",
            }
            if schema_name != "NoContent":
                response["content"] = {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{schema_name}"}
                    }
                }
            response_definitions[status] = response

        operation_document: dict[str, Any] = {
            "operationId": operation.operation_id,
            "summary": operation.summary,
            "description": (
                "The contract defines accepted inputs and documented outcomes. "
                "Runtime authorization and business rules remain server responsibilities."
            ),
            "parameters": parameters,
            "responses": response_definitions,
        }

        if operation.request_schema:
            operation_document["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "$ref": (
                                f"#/components/schemas/{operation.request_schema}"
                            )
                        }
                    }
                },
            }

        if operation.security:
            operation_document["security"] = [{"BearerAuth": []}]

        paths.setdefault(operation.path, {})[operation.method.value.lower()] = (
            operation_document
        )

    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Project Operations API",
            "version": "1.2.0",
            "description": (
                "Contract-first API for project lifecycle management. "
                "The contract is the authoritative interface specification."
            ),
        },
        "servers": [{"url": "https://api.example.test/v1"}],
        "tags": [{"name": "Projects", "description": "Project operations"}],
        "paths": paths,
        "components": {
            "securitySchemes": {
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                **copy.deepcopy(COMPONENT_SCHEMAS),
                "ProjectList": {
                    "type": "object",
                    "required": ["items", "total", "limit", "offset"],
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Project"},
                        },
                        "total": {"type": "integer", "minimum": 0},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                        "offset": {"type": "integer", "minimum": 0},
                    },
                    "additionalProperties": False,
                },
                "UpdateProject": {
                    "type": "object",
                    "minProperties": 1,
                    "properties": {
                        "name": {"type": "string", "minLength": 3, "maxLength": 100},
                        "status": {
                            "type": "string",
                            "enum": ["planned", "active", "completed"],
                        },
                        "owner": {"type": "string", "format": "email"},
                    },
                    "additionalProperties": False,
                },
            },
        },
    }


def validate_openapi_document(document: dict[str, Any]) -> list[str]:
    """
    Check contract-level invariants.

    A production pipeline should also run a standards-compliant OpenAPI validator,
    because this deliberately small checker does not implement the complete
    OpenAPI 3.1 specification or JSON Schema dialect.
    """
    errors: list[str] = []

    if document.get("openapi") != "3.1.0":
        errors.append("OpenAPI version must be 3.1.0")

    info = document.get("info", {})
    if not info.get("title") or not info.get("version"):
        errors.append("info.title and info.version are required")

    operations_seen: set[str] = set()
    schemas = document.get("components", {}).get("schemas", {})
    paths = document.get("paths", {})

    if not paths:
        errors.append("At least one path is required")

    for path, methods in paths.items():
        if not path.startswith("/"):
            errors.append(f"{path}: paths must begin with '/'")

        for method, operation in methods.items():
            operation_id = operation.get("operationId")
            if not operation_id:
                errors.append(f"{method.upper()} {path}: operationId is required")
            elif operation_id in operations_seen:
                errors.append(f"Duplicate operationId: {operation_id}")
            else:
                operations_seen.add(operation_id)

            for parameter in operation.get("parameters", []):
                if parameter.get("in") == "path":
                    if parameter.get("required") is not True:
                        errors.append(
                            f"{method.upper()} {path}: path parameters must be required"
                        )
                    token = "{" + parameter.get("name", "") + "}"
                    if token not in path:
                        errors.append(
                            f"{method.upper()} {path}: path parameter {token} is absent"
                        )

            for response_code, response in operation.get("responses", {}).items():
                if not response.get("description"):
                    errors.append(
                        f"{method.upper()} {path} response {response_code} "
                        "requires a description"
                    )

                content = response.get("content", {})
                json_schema = content.get("application/json", {}).get("schema", {})
                reference = json_schema.get("$ref")
                if reference and reference.startswith("#/components/schemas/"):
                    schema_name = reference.rsplit("/", 1)[-1]
                    if schema_name not in schemas:
                        errors.append(
                            f"{method.upper()} {path}: unknown schema {schema_name}"
                        )

    schemes = document.get("components", {}).get("securitySchemes", {})
    if "BearerAuth" not in schemes:
        errors.append("BearerAuth security scheme is missing")

    return errors


def resolve_local_schema(
    document: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    """Resolve a direct local component reference without network access."""
    reference = schema.get("$ref")
    if not reference:
        return schema

    prefix = "#/components/schemas/"
    if not reference.startswith(prefix):
        raise ContractError(f"Unsupported schema reference: {reference}")

    name = reference[len(prefix):]
    try:
        return document["components"]["schemas"][name]
    except KeyError as exc:
        raise ContractError(f"Unknown schema reference: {reference}") from exc


def serialize_query_parameters(
    values: dict[str, str | int | bool | list[str]],
) -> str:
    """Serialize query parameters using percent encoding and repeated list keys."""
    pairs: list[tuple[str, str]] = []
    for key, value in values.items():
        if isinstance(value, bool):
            pairs.append((key, str(value).lower()))
        elif isinstance(value, list):
            pairs.extend((key, item) for item in value)
        else:
            pairs.append((key, str(value)))
    return urlencode(pairs, doseq=True, safe="")


def match_path_template(
    template: str,
    actual_path: str,
) -> dict[str, str] | None:
    """
    Match a route template without treating user-supplied path text as regex syntax.
    Returns raw path parameters; percent decoding is left to the transport layer.
    """
    template_parts = template.strip("/").split("/")
    actual_parts = actual_path.strip("/").split("/")

    if len(template_parts) != len(actual_parts):
        return None

    parameters: dict[str, str] = {}
    for expected, actual in zip(template_parts, actual_parts):
        if expected.startswith("{") and expected.endswith("}"):
            name = expected[1:-1]
            if not actual:
                return None
            parameters[name] = actual
        elif expected != actual:
            return None

    return parameters


class ProjectService:
    """
    Small in-memory API implementation used for conformance testing.

    A real service must use durable storage, transaction isolation, rate limiting,
    a verified identity provider, and authorization checks appropriate to each
    resource. This example treats the token as a demonstration credential only.
    """

    def __init__(self) -> None:
        self._projects: dict[int, dict[str, Any]] = {}
        self._next_id = 1

    def _require_auth(self, authorization: str | None) -> None:
        if authorization != "Bearer demo-token":
            raise AuthenticationError("A valid bearer token is required")

    def _new_project(self, payload: dict[str, Any]) -> dict[str, Any]:
        project = {
            "id": self._next_id,
            "name": payload["name"],
            "status": payload["status"],
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        if "owner" in payload:
            project["owner"] = payload["owner"]

        self._next_id += 1
        return project

    def dispatch(
        self,
        method: str,
        path: str,
        *,
        authorization: str | None = None,
        query: dict[str, Any] | None = None,
        body: Any = None,
    ) -> ApiResponse:
        try:
            self._require_auth(authorization)
            query = query or {}

            if method == "GET" and path == "/projects":
                limit = query.get("limit", 20)
                offset = query.get("offset", 0)
                issues = (
                    validate_schema(limit, {"type": "integer", "minimum": 1, "maximum": 100})
                    + validate_schema(offset, {"type": "integer", "minimum": 0})
                )
                if issues:
                    raise ApiError(400, "INVALID_QUERY", "; ".join(map(str, issues)))

                items = list(self._projects.values())
                return ApiResponse(
                    200,
                    {
                        "items": copy.deepcopy(items[offset:offset + limit]),
                        "total": len(items),
                        "limit": limit,
                        "offset": offset,
                    },
                    {"Content-Type": "application/json"},
                )

            if method == "POST" and path == "/projects":
                issues = validate_schema(body, COMPONENT_SCHEMAS["CreateProject"])
                if issues:
                    raise ApiError(400, "INVALID_BODY", "; ".join(map(str, issues)))

                if any(project["name"] == body["name"] for project in self._projects.values()):
                    raise ApiError(409, "PROJECT_EXISTS", "Project name already exists")

                project = self._new_project(body)
                self._projects[project["id"]] = project
                return ApiResponse(
                    201,
                    copy.deepcopy(project),
                    {
                        "Content-Type": "application/json",
                        "Location": f"/projects/{project['id']}",
                    },
                )

            match = match_path_template("/projects/{projectId}", path)
            if match is not None:
                raw_id = match["projectId"]
                if not raw_id.isdigit() or int(raw_id) < 1:
                    raise ApiError(400, "INVALID_ID", "projectId must be a positive integer")

                project_id = int(raw_id)
                project = self._projects.get(project_id)
                if project is None:
                    raise ApiError(404, "NOT_FOUND", "Project does not exist")

                if method == "GET":
                    return ApiResponse(200, copy.deepcopy(project), {"Content-Type": "application/json"})

                if method == "PATCH":
                    schema = {
                        "type": "object",
                        "minProperties": 1,
                        "properties": {
                            "name": COMPONENT_SCHEMAS["CreateProject"]["properties"]["name"],
                            "status": COMPONENT_SCHEMAS["CreateProject"]["properties"]["status"],
                            "owner": COMPONENT_SCHEMAS["CreateProject"]["properties"]["owner"],
                        },
                        "additionalProperties": False,
                    }
                    issues = validate_schema(body, schema)
                    if not isinstance(body, dict) or not body:
                        issues.append(ValidationIssue("$", "PATCH body must not be empty"))
                    if issues:
                        raise ApiError(400, "INVALID_BODY", "; ".join(map(str, issues)))

                    if "name" in body and any(
                        other_id != project_id and other["name"] == body["name"]
                        for other_id, other in self._projects.items()
                    ):
                        raise ApiError(409, "PROJECT_EXISTS", "Project name already exists")

                    project.update(body)
                    return ApiResponse(200, copy.deepcopy(project), {"Content-Type": "application/json"})

                if method == "DELETE":
                    del self._projects[project_id]
                    return ApiResponse(204, None, {})

            raise ApiError(404, "ROUTE_NOT_FOUND", "No documented operation matches this request")

        except AuthenticationError:
            return ApiError(401, "UNAUTHENTICATED", "Valid bearer authentication is required").to_response()
        except ApiError as error:
            return error.to_response()


def compare_schema_compatibility(
    old_schema: dict[str, Any],
    new_schema: dict[str, Any],
    path: str = "$",
) -> list[str]:
    """
    Detect common response-contract breaking changes.

    This is a conservative teaching checker, not a complete semantic compatibility
    algorithm. Removing response properties, making optional properties required,
    narrowing enums, and narrowing numeric bounds can break consumers.
    """
    changes: list[str] = []

    if old_schema.get("type") != new_schema.get("type"):
        changes.append(
            f"{path}: type changed from {old_schema.get('type')} to {new_schema.get('type')}"
        )
        return changes

    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))
    for name in sorted(new_required - old_required):
        changes.append(f"{path}.{name}: property became required")

    old_properties = old_schema.get("properties", {})
    new_properties = new_schema.get("properties", {})

    for name in sorted(old_properties.keys() - new_properties.keys()):
        changes.append(f"{path}.{name}: response property was removed")

    for name in sorted(old_properties.keys() & new_properties.keys()):
        changes.extend(
            compare_schema_compatibility(
                old_properties[name],
                new_properties[name],
                f"{path}.{name}",
            )
        )

    if "enum" in old_schema and "enum" in new_schema:
        removed_values = set(old_schema["enum"]) - set(new_schema["enum"])
        if removed_values:
            changes.append(f"{path}: enum values removed: {sorted(removed_values)}")

    if "minimum" in old_schema and "minimum" in new_schema:
        if new_schema["minimum"] > old_schema["minimum"]:
            changes.append(f"{path}: minimum increased")

    if "maximum" in old_schema and "maximum" in new_schema:
        if new_schema["maximum"] < old_schema["maximum"]:
            changes.append(f"{path}: maximum decreased")

    return changes


class ApiContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ProjectService()
        self.auth = "Bearer demo-token"

    def call(self, method: str, path: str, **kwargs: Any) -> ApiResponse:
        return self.service.dispatch(method, path, authorization=self.auth, **kwargs)

    def test_openapi_contract_has_no_known_structural_errors(self) -> None:
        self.assertEqual(validate_openapi_document(build_openapi_document()), [])

    def test_create_and_retrieve_project(self) -> None:
        created = self.call(
            "POST",
            "/projects",
            body={"name": "Network Modernization", "status": "planned"},
        )
        self.assertEqual(created.status, 201)
        self.assertIn("Location", created.headers)

        retrieved = self.call("GET", "/projects/1")
        self.assertEqual(retrieved.status, 200)
        self.assertEqual(retrieved.body["name"], "Network Modernization")

    def test_invalid_payload_is_rejected(self) -> None:
        response = self.call(
            "POST",
            "/projects",
            body={"name": "X", "status": "unknown"},
        )
        self.assertEqual(response.status, 400)

    def test_missing_authentication_is_rejected(self) -> None:
        response = self.service.dispatch("GET", "/projects")
        self.assertEqual(response.status, 401)

    def test_duplicate_name_conflicts(self) -> None:
        payload = {"name": "Data Governance", "status": "active"}
        self.assertEqual(self.call("POST", "/projects", body=payload).status, 201)
        self.assertEqual(self.call("POST", "/projects", body=payload).status, 409)

    def test_empty_patch_is_rejected(self) -> None:
        self.call("POST", "/projects", body={"name": "Audit Portal", "status": "active"})
        response = self.call("PATCH", "/projects/1", body={})
        self.assertEqual(response.status, 400)

    def test_delete_returns_no_content(self) -> None:
        self.call("POST", "/projects", body={"name": "Incident Portal", "status": "active"})
        deleted = self.call("DELETE", "/projects/1")
        self.assertEqual(deleted.status, 204)
        self.assertIsNone(deleted.body)
        self.assertEqual(self.call("GET", "/projects/1").status, 404)

    def test_compatibility_detects_removed_property(self) -> None:
        old = {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
            },
        }
        new = {"type": "object", "properties": {"id": {"type": "integer"}}}
        self.assertTrue(compare_schema_compatibility(old, new))

    def test_query_encoding_preserves_repeated_keys(self) -> None:
        encoded = serialize_query_parameters({"tag": ["security", "operations"]})
        self.assertEqual(parse_qs(encoded), {"tag": ["security", "operations"]})


def print_contract_report(document: dict[str, Any]) -> None:
    """Display a compact report of the contract and its declared operations."""
    print("\n=== OpenAPI Contract Report ===")
    print(f"Specification: {document['openapi']}")
    print(f"API: {document['info']['title']} {document['info']['version']}")
    print(f"Paths: {len(document['paths'])}")

    for path, methods in document["paths"].items():
        for method, operation in methods.items():
            response_codes = ", ".join(operation["responses"].keys())
            print(
                f"{method.upper():6} {path:28} "
                f"{operation['operationId']:18} responses={response_codes}"
            )

    errors = validate_openapi_document(document)
    print(f"Structural checks: {'PASS' if not errors else 'FAIL'}")
    for error in errors:
        print(f"  ERROR: {error}")


def demonstrate_request_workflow() -> None:
    """Exercise representative successful and failing HTTP interactions."""
    service = ProjectService()
    auth = "Bearer demo-token"

    print("\n=== Runtime Contract Demonstration ===")

    create_response = service.dispatch(
        "POST",
        "/projects",
        authorization=auth,
        body={
            "name": "Secure API Gateway",
            "status": "active",
            "owner": "platform@example.test",
        },
    )
    print(f"Create: HTTP {create_response.status} {create_response.body}")

    invalid_response = service.dispatch(
        "POST",
        "/projects",
        authorization=auth,
        body={"name": "A", "status": "running"},
    )
    print(f"Invalid body: HTTP {invalid_response.status} {invalid_response.body}")

    unauthorized_response = service.dispatch("GET", "/projects")
    print(f"Unauthorized: HTTP {unauthorized_response.status} {unauthorized_response.body}")

    listing = service.dispatch(
        "GET",
        "/projects",
        authorization=auth,
        query={"limit": 10, "offset": 0},
    )
    print(f"List: HTTP {listing.status} {json.dumps(listing.body, indent=2)}")


def demonstrate_contract_evolution() -> None:
    """Show why schema changes must be checked against existing consumers."""
    print("\n=== Contract Evolution ===")

    version_1 = {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "integer", "minimum": 1},
            "name": {"type": "string"},
            "description": {"type": "string"},
        },
    }
    version_2 = {
        "type": "object",
        "required": ["id", "name", "status"],
        "properties": {
            "id": {"type": "integer", "minimum": 1},
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "completed"]},
        },
    }

    for change in compare_schema_compatibility(version_1, version_2):
        print(f"Potential breaking change: {change}")


def export_openapi_document(
    document: dict[str, Any],
    output_path: str = "openapi.json",
) -> Path:
    """
    Write a deterministic JSON artifact.

    The destination is intentionally supplied by the caller. In automated builds,
    restrict writable directories and avoid using untrusted paths.
    """
    destination = Path(output_path)
    destination.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


def main() -> None:
    document = build_openapi_document()
    print_contract_report(document)
    demonstrate_request_workflow()
    demonstrate_contract_evolution()

    print("\n=== Automated Contract Tests ===")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ApiContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    if not result.wasSuccessful():
        raise SystemExit(1)

    # Export is opt-in so running the teaching script does not unexpectedly
    # overwrite a file in the current working directory.
    if "--export" in __import__("sys").argv:
        destination = export_openapi_document(document)
        print(f"OpenAPI artifact written to {destination.resolve()}")


if __name__ == "__main__":
    main()
