"""
Documentation, README, API Documentation, and Technical Documentation
=======================================================================

A standalone study and demonstration program covering documentation from
beginner concepts through advanced documentation engineering.

The program demonstrates:
- Documentation fundamentals and terminology
- Documentation types
- README design
- API documentation
- Technical documentation
- Documentation quality and structure
- Information architecture
- Examples and executable specifications
- Markdown generation and validation
- API specification modeling
- Cross-references and consistency checks
- Versioning and change documentation
- Security and privacy considerations
- Documentation testing
- Search-oriented documentation design
- Documentation coverage and quality metrics
- A practical documentation build pipeline

The examples use only the Python standard library.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable
import json
import re
import textwrap
import unittest


# ---------------------------------------------------------------------------
# 1. FUNDAMENTAL TERMINOLOGY
# ---------------------------------------------------------------------------

class DocumentationType(Enum):
    README = "README"
    API = "API documentation"
    TUTORIAL = "Tutorial"
    HOW_TO = "How-to guide"
    REFERENCE = "Reference documentation"
    CONCEPTUAL = "Conceptual documentation"
    TECHNICAL = "Technical documentation"
    CHANGELOG = "Changelog"
    RUNBOOK = "Runbook"
    ARCHITECTURE = "Architecture documentation"


@dataclass
class DocumentSection:
    """A reusable structural unit of a technical document."""

    title: str
    content: str
    level: int = 2

    def to_markdown(self) -> str:
        heading = "#" * self.level
        return f"{heading} {self.title}\n\n{self.content.strip()}\n"


@dataclass
class Document:
    """Represents a documentation document independent of file format."""

    title: str
    description: str
    sections: list[DocumentSection] = field(default_factory=list)
    version: str = "1.0.0"

    def add_section(self, title: str, content: str, level: int = 2) -> None:
        self.sections.append(DocumentSection(title, content, level))

    def render_markdown(self) -> str:
        parts = [
            f"# {self.title}",
            "",
            self.description.strip(),
            "",
            f"**Version:** `{self.version}`",
            "",
        ]
        for section in self.sections:
            parts.append(section.to_markdown().strip())
            parts.append("")
        return "\n".join(parts).strip() + "\n"


# ---------------------------------------------------------------------------
# 2. README FUNDAMENTALS
# ---------------------------------------------------------------------------

README_PRINCIPLES = {
    "purpose": "A README gives users a fast, practical understanding of a project.",
    "audience": "Readers may include users, developers, maintainers, reviewers, and operators.",
    "entry_point": "A README is usually the first project document a new reader encounters.",
    "scope": "It should explain the project without attempting to contain every technical detail.",
    "navigation": "Links should lead readers to deeper documentation when more detail is needed.",
}

print("=" * 78)
print("DOCUMENTATION ENGINEERING STUDY PROGRAM")
print("=" * 78)

print("\nCore documentation principle:")
print(
    "Good documentation answers the reader's question at the appropriate "
    "level of detail and provides a reliable path to deeper information."
)

print("\nCommon documentation types:")
for documentation_type in DocumentationType:
    print(f"  - {documentation_type.value}")


# ---------------------------------------------------------------------------
# 3. README STRUCTURE
# ---------------------------------------------------------------------------

def build_readme(
    project_name: str,
    description: str,
    installation_command: str,
    usage_command: str,
) -> Document:
    """Build a practical README using structured sections."""

    document = Document(
        title=project_name,
        description=description,
        version="1.0.0",
    )

    document.add_section(
        "Features",
        "- Input validation\n"
        "- Deterministic processing\n"
        "- Structured API behavior\n"
        "- Clear error handling",
    )

    document.add_section(
        "Installation",
        f"1. Install the project dependencies.\n"
        f"2. Run `{installation_command}`.",
    )

    document.add_section(
        "Usage",
        f"Run `{usage_command}` to execute the application.",
    )

    document.add_section(
        "Configuration",
        "Configuration values should be documented with their type, "
        "default value, allowed range, and security implications.",
    )

    document.add_section(
        "API",
        "The HTTP API is described separately using endpoint, request, "
        "response, authentication, validation, and error information.",
    )

    document.add_section(
        "Testing",
        "Automated tests should verify both implementation behavior and "
        "important documentation examples.",
    )

    return document


readme = build_readme(
    project_name="Documentation Demo Service",
    description="A small example application used to demonstrate documentation engineering.",
    installation_command="python -m pip install -r requirements.txt",
    usage_command="python app.py",
)

print("\nGenerated README:")
print("-" * 78)
print(readme.render_markdown())


# ---------------------------------------------------------------------------
# 4. API DOCUMENTATION MODEL
# ---------------------------------------------------------------------------

class HttpMethod(Enum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass
class ApiParameter:
    name: str
    location: str
    data_type: str
    required: bool
    description: str
    example: Any = None


@dataclass
class ApiEndpoint:
    method: HttpMethod
    path: str
    summary: str
    description: str
    parameters: list[ApiParameter] = field(default_factory=list)
    request_body: dict[str, Any] | None = None
    success_status: int = 200
    success_response: dict[str, Any] | None = None
    errors: dict[int, str] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate documentation completeness."""

        problems: list[str] = []

        if not self.path.startswith("/"):
            problems.append("Path must start with '/'.")

        if not self.summary.strip():
            problems.append("Endpoint summary cannot be empty.")

        if not self.description.strip():
            problems.append("Endpoint description cannot be empty.")

        names = set()
        for parameter in self.parameters:
            if parameter.name in names:
                problems.append(
                    f"Duplicate parameter documented: {parameter.name}"
                )
            names.add(parameter.name)

            if parameter.location not in {"path", "query", "header", "cookie"}:
                problems.append(
                    f"Unsupported parameter location: {parameter.location}"
                )

            if not parameter.data_type.strip():
                problems.append(
                    f"Missing data type for parameter: {parameter.name}"
                )

            if parameter.required and parameter.example is None:
                problems.append(
                    f"Required parameter has no example: {parameter.name}"
                )

        if self.success_response is None:
            problems.append("Successful response schema is missing.")

        if self.success_status < 200 or self.success_status >= 300:
            problems.append("Success status must be in the 2xx range.")

        return problems

    def to_markdown(self) -> str:
        """Render API reference information as Markdown."""

        lines = [
            f"### `{self.method.value} {self.path}`",
            "",
            f"**Summary:** {self.summary}",
            "",
            self.description,
            "",
        ]

        if self.parameters:
            lines.extend(
                [
                    "#### Parameters",
                    "",
                    "| Name | Location | Type | Required | Example | Description |",
                    "|---|---|---|---|---|---|",
                ]
            )

            for parameter in self.parameters:
                example = (
                    str(parameter.example)
                    if parameter.example is not None
                    else ""
                )
                lines.append(
                    f"| `{parameter.name}` | `{parameter.location}` | "
                    f"`{parameter.data_type}` | "
                    f"{'Yes' if parameter.required else 'No'} | "
                    f"`{example}` | {parameter.description} |"
                )
            lines.append("")

        if self.request_body is not None:
            lines.extend(
                [
                    "#### Request Body",
                    "",
                    f"`{json.dumps(self.request_body, indent=2)}`",
                    "",
                ]
            )

        lines.extend(
            [
                "#### Success Response",
                "",
                f"HTTP status: `{self.success_status}`",
                "",
                f"`{json.dumps(self.success_response, indent=2)}`",
                "",
            ]
        )

        if self.errors:
            lines.extend(
                [
                    "#### Errors",
                    "",
                    "| Status | Meaning |",
                    "|---:|---|",
                ]
            )

            for status, message in sorted(self.errors.items()):
                lines.append(f"| `{status}` | {message} |")

            lines.append("")

        return "\n".join(lines).rstrip()


create_user_endpoint = ApiEndpoint(
    method=HttpMethod.POST,
    path="/v1/users",
    summary="Create a user",
    description=(
        "Creates a new user after validating the submitted identity fields. "
        "The email address must be syntactically valid and unique."
    ),
    parameters=[],
    request_body={
        "name": "Ada Lovelace",
        "email": "ada@example.com",
    },
    success_status=201,
    success_response={
        "id": "usr_1001",
        "name": "Ada Lovelace",
        "email": "ada@example.com",
    },
    errors={
        400: "The request body is invalid.",
        409: "A user with the same email already exists.",
        422: "The submitted values fail semantic validation.",
    },
)

validation_errors = create_user_endpoint.validate()

print("API documentation validation:")
if validation_errors:
    for error in validation_errors:
        print(f"  ERROR: {error}")
else:
    print("  API endpoint documentation is complete.")

print("\nRendered API reference:")
print(create_user_endpoint.to_markdown())


# ---------------------------------------------------------------------------
# 5. TECHNICAL DOCUMENTATION
# ---------------------------------------------------------------------------

@dataclass
class TechnicalSpecification:
    """A technical specification records how a system is designed."""

    problem: str
    scope: str
    requirements: list[str]
    architecture: list[str]
    data_flow: list[str]
    failure_modes: list[str]
    operational_notes: list[str]

    def validate(self) -> list[str]:
        problems = []

        if not self.problem.strip():
            problems.append("Problem statement is missing.")

        if not self.scope.strip():
            problems.append("Scope is missing.")

        if not self.requirements:
            problems.append("At least one requirement is required.")

        if not self.architecture:
            problems.append("Architecture description is missing.")

        if not self.failure_modes:
            problems.append("Failure modes should be documented.")

        return problems

    def render(self) -> str:
        sections = [
            ("Problem", self.problem),
            ("Scope", self.scope),
            ("Requirements", "\n".join(f"- {x}" for x in self.requirements)),
            ("Architecture", "\n".join(f"- {x}" for x in self.architecture)),
            ("Data Flow", "\n".join(f"- {x}" for x in self.data_flow)),
            (
                "Failure Modes",
                "\n".join(f"- {x}" for x in self.failure_modes),
            ),
            (
                "Operational Notes",
                "\n".join(f"- {x}" for x in self.operational_notes),
            ),
        ]

        output = ["# Technical Specification", ""]
        for title, body in sections:
            output.extend([f"## {title}", "", body, ""])

        return "\n".join(output).strip()


technical_specification = TechnicalSpecification(
    problem=(
        "Provide a documented service contract for creating users while "
        "making behavior, validation, and failures predictable."
    ),
    scope=(
        "The service accepts validated JSON requests and returns structured "
        "JSON responses."
    ),
    requirements=[
        "Reject malformed JSON.",
        "Validate required fields.",
        "Return deterministic HTTP status categories.",
        "Avoid exposing internal implementation details in public errors.",
    ],
    architecture=[
        "HTTP request layer",
        "Input validation layer",
        "Application service layer",
        "Persistence abstraction",
        "HTTP response serialization",
    ],
    data_flow=[
        "Client sends request.",
        "Request is parsed.",
        "Input is validated.",
        "Application logic executes.",
        "Response is serialized.",
    ],
    failure_modes=[
        "Malformed request",
        "Missing required field",
        "Duplicate resource",
        "Unexpected internal failure",
    ],
    operational_notes=[
        "Log internal diagnostic information without exposing secrets.",
        "Version public API contracts deliberately.",
        "Monitor error rates and latency.",
    ],
)

print("\nTechnical specification validation:")
for problem in technical_specification.validate():
    print(f"  ERROR: {problem}")

if not technical_specification.validate():
    print("  Specification contains the required structural components.")


# ---------------------------------------------------------------------------
# 6. DOCUMENTATION INFORMATION ARCHITECTURE
# ---------------------------------------------------------------------------

DOCUMENTATION_LAYERS = {
    "Landing": "What is this and where should I start?",
    "Tutorial": "How do I learn the basic workflow?",
    "How-to": "How do I accomplish a specific task?",
    "Reference": "What are the exact technical details?",
    "Conceptual": "Why does the system work this way?",
    "Operations": "How do I deploy, monitor, recover, and maintain it?",
}

print("\nDocumentation information architecture:")
for layer, question in DOCUMENTATION_LAYERS.items():
    print(f"  {layer:12} -> {question}")


# ---------------------------------------------------------------------------
# 7. AUDIENCE-DRIVEN DOCUMENTATION
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Audience:
    name: str
    primary_goal: str
    preferred_detail: str


AUDIENCES = [
    Audience(
        "End user",
        "Complete a task successfully",
        "Task-focused",
    ),
    Audience(
        "Developer",
        "Integrate or modify the system",
        "Technical",
    ),
    Audience(
        "Operator",
        "Run and troubleshoot the system",
        "Operational",
    ),
    Audience(
        "Architect",
        "Understand system structure and trade-offs",
        "Architectural",
    ),
    Audience(
        "Maintainer",
        "Keep documentation and implementation synchronized",
        "Detailed",
    ),
]

print("\nAudience analysis:")
for audience in AUDIENCES:
    print(
        f"  {audience.name}: {audience.primary_goal} "
        f"({audience.preferred_detail})"
    )


# ---------------------------------------------------------------------------
# 8. MARKDOWN VALIDATION
# ---------------------------------------------------------------------------

def validate_markdown(markdown: str) -> list[str]:
    """
    Perform simple structural checks.

    A documentation linter should not try to prove that prose is good.
    It should identify objective structural problems that can be automated.
    """

    problems: list[str] = []

    if not markdown.strip():
        return ["Document is empty."]

    if not re.search(r"^#\s+\S+", markdown, flags=re.MULTILINE):
        problems.append("Document has no level-one heading.")

    if markdown.count("```") % 2 != 0:
        problems.append("Unbalanced Markdown code fences.")

    heading_lines = re.findall(r"^(#{1,6})\s+(.+)$", markdown, flags=re.MULTILINE)

    for hashes, title in heading_lines:
        if not title.strip():
            problems.append("A heading has no title.")

        if len(hashes) > 1:
            # Heading depth jumps greater than one can make navigation unclear.
            pass

    links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown)
    for label, target in links:
        if not label.strip():
            problems.append("A Markdown link has an empty label.")
        if not target.strip():
            problems.append(f"Link '{label}' has an empty target.")

    return problems


documentation_to_validate = """
# API Guide

## Authentication

Clients authenticate using a bearer token.

## Endpoint

Use `POST /v1/users` to create a user.

[API Reference](./api.md)
"""

print("\nMarkdown linting:")
markdown_errors = validate_markdown(documentation_to_validate)
if markdown_errors:
    for error in markdown_errors:
        print(f"  ERROR: {error}")
else:
    print("  No structural Markdown problems detected.")


# ---------------------------------------------------------------------------
# 9. LINK CHECKING
# ---------------------------------------------------------------------------

def extract_local_links(markdown: str) -> list[str]:
    """Return local Markdown targets and ignore external URLs."""

    targets = []
    for _, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", markdown):
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
            targets.append(target)
    return targets


def check_local_links(markdown: str, root: Path) -> dict[str, bool]:
    """Check whether relative documentation links point to existing files."""

    results = {}

    for target in extract_local_links(markdown):
        clean_target = target.split("#", 1)[0]
        if not clean_target:
            results[target] = True
            continue

        results[target] = (root / clean_target).exists()

    return results


# ---------------------------------------------------------------------------
# 10. API VERSIONING
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ApiVersion:
    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def classify_api_change(old: ApiVersion, new: ApiVersion) -> str:
    """
    Demonstrate semantic-version reasoning.

    Major:
        Breaking contract change.

    Minor:
        Backward-compatible capability.

    Patch:
        Backward-compatible correction.
    """

    if new.major != old.major:
        return "potentially breaking / major contract change"

    if new.minor != old.minor:
        return "backward-compatible feature change"

    if new.patch != old.patch:
        return "backward-compatible correction"

    return "no version change"


old_version = ApiVersion(1, 4, 2)

print("\nAPI versioning examples:")
for new_version in [
    ApiVersion(1, 4, 3),
    ApiVersion(1, 5, 0),
    ApiVersion(2, 0, 0),
]:
    print(
        f"  {old_version} -> {new_version}: "
        f"{classify_api_change(old_version, new_version)}"
    )


# ---------------------------------------------------------------------------
# 11. CHANGELOG GENERATION
# ---------------------------------------------------------------------------

@dataclass
class Change:
    category: str
    description: str
    issue: str | None = None


def render_changelog(version: str, changes: Iterable[Change]) -> str:
    grouped: dict[str, list[Change]] = {}

    for change in changes:
        grouped.setdefault(change.category, []).append(change)

    lines = [f"## [{version}]", ""]

    for category in sorted(grouped):
        lines.extend([f"### {category}", ""])

        for change in grouped[category]:
            suffix = f" ({change.issue})" if change.issue else ""
            lines.append(f"- {change.description}{suffix}")

        lines.append("")

    return "\n".join(lines).strip()


changes = [
    Change("Added", "Documented user creation endpoint", "#101"),
    Change("Changed", "Clarified email validation rules", "#102"),
    Change("Fixed", "Corrected the duplicate-user error description", "#103"),
]

print("\nGenerated changelog:")
print(render_changelog("1.5.0", changes))


# ---------------------------------------------------------------------------
# 12. API CONTRACT EXAMPLE
# ---------------------------------------------------------------------------

API_CONTRACT = {
    "openapi": "3.0.3",
    "info": {
        "title": "Documentation Demo API",
        "version": "1.0.0",
    },
    "paths": {
        "/v1/users": {
            "post": {
                "summary": "Create a user",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["name", "email"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string", "format": "email"},
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "201": {
                        "description": "User created",
                    },
                    "400": {
                        "description": "Invalid request",
                    },
                    "409": {
                        "description": "Duplicate user",
                    },
                },
            }
        }
    },
}

print("\nAPI contract:")
print(json.dumps(API_CONTRACT, indent=2))


# ---------------------------------------------------------------------------
# 13. EXAMPLE VALIDATION
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def validate_user_payload(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate a documented example of an API request."""

    errors = []

    if not isinstance(payload, dict):
        return False, ["Request body must be a JSON object."]

    name = payload.get("name")
    email = payload.get("email")

    if not isinstance(name, str) or not name.strip():
        errors.append("name is required and must be a non-empty string.")

    if not isinstance(email, str) or not EMAIL_PATTERN.fullmatch(email):
        errors.append("email must contain a syntactically valid email address.")

    unknown_fields = set(payload) - {"name", "email"}
    if unknown_fields:
        errors.append(
            "Unknown fields: " + ", ".join(sorted(unknown_fields))
        )

    return not errors, errors


payloads = [
    {"name": "Ada Lovelace", "email": "ada@example.com"},
    {"name": "", "email": "bad"},
    {"name": "Grace Hopper", "email": "grace@example.com", "role": "admin"},
]

print("\nAPI request validation:")
for payload in payloads:
    valid, errors = validate_user_payload(payload)
    print(f"  Input: {payload}")
    print(f"  Valid: {valid}")
    for error in errors:
        print(f"    - {error}")


# ---------------------------------------------------------------------------
# 14. DOCUMENTATION AS AN EXECUTABLE SPECIFICATION
# ---------------------------------------------------------------------------

def create_user(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Minimal documented application behavior.

    Production systems would normally persist data and handle concurrent
    requests. This example intentionally focuses on the contract.
    """

    valid, errors = validate_user_payload(payload)

    if not valid:
        raise ValueError("; ".join(errors))

    return {
        "id": "usr_demo_001",
        "name": payload["name"].strip(),
        "email": payload["email"].lower(),
    }


print("\nExecutable documentation example:")
try:
    created = create_user(
        {
            "name": "Ada Lovelace",
            "email": "ADA@example.com",
        }
    )
    print(json.dumps(created, indent=2))
except ValueError as exc:
    print(f"Validation error: {exc}")


# ---------------------------------------------------------------------------
# 15. DOCUMENTATION QUALITY METRICS
# ---------------------------------------------------------------------------

def documentation_metrics(
    markdown: str,
    required_sections: Iterable[str],
) -> dict[str, float]:
    """
    Calculate simple measurable indicators.

    Metrics are signals rather than absolute proof of documentation quality.
    A document can score well structurally while still containing inaccurate
    or confusing information.
    """

    lines = markdown.splitlines()
    headings = re.findall(r"^#{1,6}\s+(.+)$", markdown, flags=re.MULTILINE)

    normalized_headings = {heading.strip().lower() for heading in headings}
    normalized_required = {section.lower() for section in required_sections}

    section_coverage = (
        len(normalized_headings & normalized_required)
        / len(normalized_required)
        if normalized_required
        else 1.0
    )

    link_count = len(re.findall(r"\[[^\]]+\]\([^)]+\)", markdown))
    code_inline_count = len(re.findall(r"`[^`]+`", markdown))

    return {
        "line_count": float(len(lines)),
        "heading_count": float(len(headings)),
        "section_coverage": section_coverage,
        "link_count": float(link_count),
        "inline_code_count": float(code_inline_count),
    }


metrics = documentation_metrics(
    readme.render_markdown(),
    ["Features", "Installation", "Usage", "Configuration", "API", "Testing"],
)

print("\nDocumentation metrics:")
for metric, value in metrics.items():
    print(f"  {metric}: {value}")


# ---------------------------------------------------------------------------
# 16. SECURITY-SAFE DOCUMENTATION
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|secret|password|token)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
]


def find_possible_secrets(text: str) -> list[str]:
    """
    Detect common secret-like patterns before documentation is published.

    This is intentionally conservative. A real security scanner should use
    organization-specific detection and secret-management rules.
    """

    findings = []

    for pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            findings.append(match.group(0))

    return findings


unsafe_documentation = """
# Configuration

api_key = sk-example-secret-value
"""

print("\nSecurity scan:")
security_findings = find_possible_secrets(unsafe_documentation)
if security_findings:
    for finding in security_findings:
        print(f"  Potential secret detected: {finding}")
else:
    print("  No obvious secret-like values detected.")


# ---------------------------------------------------------------------------
# 17. DOCUMENTATION CONSISTENCY CHECK
# ---------------------------------------------------------------------------

def extract_api_paths(markdown: str) -> set[str]:
    """Extract documented HTTP paths from Markdown."""

    return set(
        re.findall(
            r"`(?:GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+([^`\s]+)`",
            markdown,
        )
    )


documented_api = """
# API Reference

### Users
Use `POST /v1/users` to create a user.

### User lookup
Use `GET /v1/users/{id}` to retrieve a user.
"""

print("\nDocumented API paths:")
for path in sorted(extract_api_paths(documented_api)):
    print(f"  - {path}")


# ---------------------------------------------------------------------------
# 18. DOCUMENTATION DIFF
# ---------------------------------------------------------------------------

def compare_documentation(
    old_document: str,
    new_document: str,
) -> dict[str, set[str]]:
    """Compare headings between two document versions."""

    old_headings = {
        title.strip()
        for title in re.findall(r"^#{1,6}\s+(.+)$", old_document, re.MULTILINE)
    }

    new_headings = {
        title.strip()
        for title in re.findall(r"^#{1,6}\s+(.+)$", new_document, re.MULTILINE)
    }

    return {
        "added_headings": new_headings - old_headings,
        "removed_headings": old_headings - new_headings,
    }


old_docs = """
# API
## Authentication
## Users
"""

new_docs = """
# API
## Authentication
## Users
## Pagination
"""

print("\nDocumentation structure change:")
diff = compare_documentation(old_docs, new_docs)
print(f"  Added: {sorted(diff['added_headings'])}")
print(f"  Removed: {sorted(diff['removed_headings'])}")


# ---------------------------------------------------------------------------
# 19. ERROR DOCUMENTATION
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ErrorDefinition:
    code: str
    http_status: int
    meaning: str
    resolution: str
    safe_for_client: bool = True


ERRORS = [
    ErrorDefinition(
        "INVALID_REQUEST",
        400,
        "The request cannot be parsed or validated.",
        "Correct the request according to the API schema.",
    ),
    ErrorDefinition(
        "UNAUTHORIZED",
        401,
        "Authentication credentials are missing or invalid.",
        "Provide valid authentication credentials.",
    ),
    ErrorDefinition(
        "NOT_FOUND",
        404,
        "The requested resource does not exist.",
        "Verify the resource identifier.",
    ),
    ErrorDefinition(
        "CONFLICT",
        409,
        "The requested operation conflicts with current resource state.",
        "Refresh the resource state and retry when appropriate.",
    ),
    ErrorDefinition(
        "INTERNAL_ERROR",
        500,
        "The server encountered an unexpected condition.",
        "Use the request correlation ID when contacting operators.",
    ),
]

print("\nError reference:")
for error in ERRORS:
    print(
        f"  {error.code} ({error.http_status}): "
        f"{error.meaning} -> {error.resolution}"
    )


# ---------------------------------------------------------------------------
# 20. ACCESSIBILITY AND READABILITY
# ---------------------------------------------------------------------------

def readability_warnings(markdown: str) -> list[str]:
    """Find simple patterns that can reduce technical-document usability."""

    warnings = []

    for line_number, line in enumerate(markdown.splitlines(), start=1):
        if len(line) > 120:
            warnings.append(
                f"Line {line_number} is longer than 120 characters."
            )

        if line.strip().startswith("##") and not line.strip()[2:].strip():
            warnings.append(f"Line {line_number} contains an empty heading.")

    if "Click here" in markdown:
        warnings.append(
            "Use descriptive link text instead of generic 'Click here'."
        )

    return warnings


readability_sample = """
# Installation

## Requirements

Python 3.11 or later is required.

## Procedure

Install the package and run the documented command.
"""

print("\nReadability checks:")
warnings = readability_warnings(readability_sample)
if warnings:
    for warning in warnings:
        print(f"  WARNING: {warning}")
else:
    print("  No simple readability problems detected.")


# ---------------------------------------------------------------------------
# 21. PERFORMANCE CONSIDERATIONS
# ---------------------------------------------------------------------------

def estimate_word_count(text: str) -> int:
    """Count whitespace-separated tokens as a simple documentation metric."""

    return len(text.split())


def documentation_statistics(text: str) -> dict[str, int]:
    """Produce inexpensive statistics suitable for CI checks."""

    return {
        "characters": len(text),
        "words": estimate_word_count(text),
        "lines": len(text.splitlines()),
        "headings": len(re.findall(r"^#{1,6}\s+", text, re.MULTILINE)),
        "links": len(re.findall(r"\[[^\]]+\]\([^)]+\)", text)),
    }


print("\nDocumentation statistics:")
for name, value in documentation_statistics(readme.render_markdown()).items():
    print(f"  {name}: {value}")


# ---------------------------------------------------------------------------
# 22. DOCUMENTATION BUILD PIPELINE
# ---------------------------------------------------------------------------

class DocumentationPipeline:
    """
    A simplified documentation CI pipeline.

    Typical stages are:
    1. Load source documents.
    2. Validate structure.
    3. Check links.
    4. Check examples/contracts.
    5. Scan for accidental secrets.
    6. Generate artifacts.
    7. Publish only after checks succeed.
    """

    def __init__(self, root: Path):
        self.root = root

    def lint(self, markdown: str) -> list[str]:
        return validate_markdown(markdown)

    def security_scan(self, markdown: str) -> list[str]:
        return find_possible_secrets(markdown)

    def build(self, document: Document) -> str:
        rendered = document.render_markdown()

        structural_errors = self.lint(rendered)
        security_errors = self.security_scan(rendered)

        if structural_errors:
            raise ValueError(
                "Documentation lint failed: " + "; ".join(structural_errors)
            )

        if security_errors:
            raise ValueError(
                "Documentation security scan failed."
            )

        return rendered


pipeline = DocumentationPipeline(Path("."))

try:
    generated_document = pipeline.build(readme)
    print("\nDocumentation pipeline:")
    print("  PASS: lint")
    print("  PASS: security scan")
    print(f"  PASS: generated {len(generated_document)} characters")
except ValueError as exc:
    print(f"\nDocumentation pipeline failed: {exc}")


# ---------------------------------------------------------------------------
# 23. TESTING DOCUMENTATION CODE
# ---------------------------------------------------------------------------

class DocumentationTests(unittest.TestCase):
    """Tests for executable documentation examples."""

    def test_valid_user_payload(self):
        valid, errors = validate_user_payload(
            {
                "name": "Ada Lovelace",
                "email": "ada@example.com",
            }
        )
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_invalid_email(self):
        valid, errors = validate_user_payload(
            {
                "name": "Ada Lovelace",
                "email": "not-an-email",
            }
        )
        self.assertFalse(valid)
        self.assertTrue(errors)

    def test_unknown_field(self):
        valid, errors = validate_user_payload(
            {
                "name": "Ada",
                "email": "ada@example.com",
                "admin": True,
            }
        )
        self.assertFalse(valid)
        self.assertIn("Unknown fields: admin.", errors)

    def test_api_documentation(self):
        self.assertEqual(create_user_endpoint.validate(), [])

    def test_markdown_has_title(self):
        errors = validate_markdown(readme.render_markdown())
        self.assertEqual(errors, [])

    def test_version_classification(self):
        self.assertEqual(
            classify_api_change(
                ApiVersion(1, 0, 0),
                ApiVersion(1, 1, 0),
            ),
            "backward-compatible feature change",
        )


def run_tests() -> None:
    """Run the examples as an executable quality check."""

    print("\nRunning documentation tests...")
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        DocumentationTests
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    print(
        f"Tests run: {result.testsRun}; "
        f"failures: {len(result.failures)}; "
        f"errors: {len(result.errors)}"
    )


run_tests()


# ---------------------------------------------------------------------------
# 24. EDGE CASES
# ---------------------------------------------------------------------------

print("\nEdge-case demonstrations:")

edge_cases = [
    {},
    {"name": " ", "email": "person@example.com"},
    {"name": "User", "email": "person@example"},
    {"name": "User", "email": "person@example.com", "extra": 1},
    {"name": "User", "email": "PERSON@EXAMPLE.COM"},
]

for case in edge_cases:
    valid, errors = validate_user_payload(case)
    print(f"  {case!r} -> valid={valid}")
    if errors:
        print(f"    errors={errors}")


# ---------------------------------------------------------------------------
# 25. DOCUMENTATION DESIGN TRADE-OFFS
# ---------------------------------------------------------------------------

TRADE_OFFS = [
    (
        "Short README vs exhaustive README",
        "Short documents improve scanning; exhaustive documents improve "
        "self-containment but can obscure the primary workflow.",
    ),
    (
        "Generated docs vs hand-written docs",
        "Generated documentation reduces duplication for structured APIs; "
        "hand-written prose is usually better for concepts and rationale.",
    ),
    (
        "Examples vs formal reference",
        "Examples teach behavior quickly; reference material defines exact "
        "contracts and edge conditions.",
    ),
    (
        "Single document vs multiple documents",
        "A single document is easy to locate; multiple focused documents "
        "usually scale better as systems become complex.",
    ),
]

print("\nDocumentation design trade-offs:")
for topic, explanation in TRADE_OFFS:
    print(f"  {topic}: {explanation}")


# ---------------------------------------------------------------------------
# 26. PRODUCTION DOCUMENTATION CHECKLIST
# ---------------------------------------------------------------------------

PRODUCTION_CHECKLIST = [
    "Audience and purpose are explicit.",
    "Installation instructions are reproducible.",
    "Commands and examples are syntactically valid.",
    "API endpoints document requests and responses.",
    "Required and optional parameters are distinguished.",
    "Errors and failure conditions are documented.",
    "Authentication and authorization behavior is documented.",
    "Security-sensitive information is not embedded in examples.",
    "Version information is clear.",
    "Breaking changes are explicitly communicated.",
    "Local links are valid.",
    "Documentation is reviewed when implementation changes.",
    "Operational procedures include failure and recovery paths.",
    "Examples are tested where practical.",
]

print("\nProduction documentation checklist:")
for item in PRODUCTION_CHECKLIST:
    print(f"  [ ] {item}")


# ---------------------------------------------------------------------------
# 27. FINAL STUDY EXAMPLE
# ---------------------------------------------------------------------------

def create_study_document() -> str:
    """Build a compact but complete technical documentation example."""

    document = Document(
        title="User Creation API",
        description=(
            "Reference documentation for creating users through a versioned "
            "HTTP API."
        ),
        version="1.0.0",
    )

    document.add_section(
        "Purpose",
        "This API creates a user resource after validating the request.",
    )

    document.add_section(
        "Authentication",
        "Requests require valid authentication credentials. "
        "Credentials must not be embedded in source-control examples.",
    )

    document.add_section(
        "Endpoint",
        create_user_endpoint.to_markdown(),
    )

    document.add_section(
        "Validation Rules",
        "- `name` must be a non-empty string.\n"
        "- `email` must be syntactically valid.\n"
        "- Unknown request fields are rejected by this example contract.",
    )

    document.add_section(
        "Failure Behavior",
        "- `400`: malformed or invalid request.\n"
        "- `409`: duplicate user.\n"
        "- `500`: unexpected server failure.",
    )

    document.add_section(
        "Operational Notes",
        "Production implementations should use structured logs, "
        "correlation identifiers, monitoring, controlled retries, "
        "authentication, authorization, rate limiting, and secure secret "
        "management.",
    )

    return document.render_markdown()


study_document = create_study_document()

print("\nComplete study document:")
print("-" * 78)
print(study_document)

print("=" * 78)
print("DOCUMENTATION STUDY PROGRAM COMPLETE")
print("=" * 78)
