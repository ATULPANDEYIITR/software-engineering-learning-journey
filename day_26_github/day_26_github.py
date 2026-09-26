"""
GitHub: Repositories, Issues, Projects, and Releases
======================================================

A standalone study program that teaches GitHub repository management, issues,
projects, and releases from beginner to advanced level.

The program uses only Python's standard library. It does not require a GitHub
account or external package to run.

It contains:
    1. Git and GitHub fundamentals
    2. Repository concepts
    3. Repository metadata and structure
    4. Issues and issue lifecycle
    5. Labels, milestones, assignees, and issue templates
    6. GitHub Projects concepts and local project-board simulation
    7. Releases, tags, semantic versioning, and release assets
    8. Repository automation concepts
    9. GitHub REST API examples using urllib
    10. Authentication and security considerations
    11. Validation and error handling
    12. Pagination and rate-limit handling
    13. Search and filtering
    14. Local project/release management case study
    15. Testing
    16. Performance considerations
    17. Production-oriented design patterns

The examples intentionally separate:
    - Git: version-control operations
    - GitHub: collaboration and hosting
    - Issues: work and discussion
    - Projects: planning and workflow
    - Releases: published software versions

Run:
    python github_management.py

Optional GitHub API demonstration:
    Set GITHUB_TOKEN to a personal access token and optionally set
    GITHUB_OWNER and GITHUB_REPOSITORY.

Example:
    Windows PowerShell:
        $env:GITHUB_TOKEN="your_token"
        $env:GITHUB_OWNER="octocat"
        $env:GITHUB_REPOSITORY="Hello-World"
        python github_management.py

The API examples are read-oriented by default. Destructive or mutating
operations are represented by functions that require explicit calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable, Iterator, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


# ============================================================================
# 1. FUNDAMENTAL TERMINOLOGY
# ============================================================================

def explain_fundamentals() -> None:
    print("=" * 80)
    print("1. GITHUB FUNDAMENTALS")
    print("=" * 80)

    concepts = {
        "Git": (
            "A distributed version-control system used to record changes to "
            "files and coordinate development."
        ),
        "GitHub": (
            "A web platform built around Git repositories and collaboration "
            "features."
        ),
        "Repository": (
            "A project space containing source code, history, documentation, "
            "configuration, and related GitHub metadata."
        ),
        "Issue": (
            "A tracked unit of work, question, bug report, feature request, "
            "discussion, or other repository-level task."
        ),
        "Project": (
            "A planning and tracking workspace used to organize issues, pull "
            "requests, and other work items into views and workflows."
        ),
        "Release": (
            "A published version of a project associated with a Git tag and "
            "release notes, optionally containing downloadable assets."
        ),
        "Tag": (
            "A Git reference that identifies a particular point in repository "
            "history. Releases commonly use tags such as v1.2.0."
        ),
        "Pull Request": (
            "A proposed change that can be reviewed and merged into another "
            "branch."
        ),
        "Branch": (
            "An independent line of development within a Git repository."
        ),
        "Commit": (
            "A recorded snapshot of changes in Git history."
        ),
    }

    for name, description in concepts.items():
        print(f"\n{name}")
        print(f"  {description}")

    print("\nImportant distinction:")
    print("  Git manages repository history.")
    print("  GitHub adds collaboration, hosting, automation, planning,")
    print("  issue tracking, releases, permissions, and project-management tools.")


# ============================================================================
# 2. REPOSITORY MODEL
# ============================================================================

class Visibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INTERNAL = "internal"


class RepositoryState(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass
class Repository:
    owner: str
    name: str
    description: str = ""
    visibility: Visibility = Visibility.PUBLIC
    default_branch: str = "main"
    archived: bool = False
    topics: set[str] = field(default_factory=set)
    stars: int = 0
    forks: int = 0
    open_issues: int = 0

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"

    @property
    def state(self) -> RepositoryState:
        return RepositoryState.ARCHIVED if self.archived else RepositoryState.ACTIVE

    def add_topic(self, topic: str) -> None:
        normalized = topic.strip().lower()
        if not normalized:
            raise ValueError("A repository topic cannot be empty.")
        if len(normalized) > 50:
            raise ValueError("Repository topics should be short.")
        self.topics.add(normalized)

    def remove_topic(self, topic: str) -> None:
        self.topics.discard(topic.strip().lower())

    def validate(self) -> list[str]:
        errors: list[str] = []

        if not self.owner.strip():
            errors.append("Repository owner is required.")

        if not self.name.strip():
            errors.append("Repository name is required.")

        if not re.fullmatch(r"[A-Za-z0-9._-]+", self.name):
            errors.append(
                "Repository name contains characters outside the commonly "
                "accepted GitHub repository naming pattern."
            )

        if not self.default_branch.strip():
            errors.append("Default branch cannot be empty.")

        if self.stars < 0:
            errors.append("Stars cannot be negative.")

        if self.forks < 0:
            errors.append("Fork count cannot be negative.")

        if self.open_issues < 0:
            errors.append("Open issue count cannot be negative.")

        return errors


def repository_example() -> Repository:
    repository = Repository(
        owner="example-owner",
        name="asset-management-system",
        description="A system for tracking organizational assets.",
        visibility=Visibility.PUBLIC,
        default_branch="main",
    )

    repository.add_topic("github")
    repository.add_topic("asset-management")
    repository.add_topic("python")

    return repository


# ============================================================================
# 3. REPOSITORY FILE STRUCTURE
# ============================================================================

def demonstrate_repository_structure() -> None:
    print("\n" + "=" * 80)
    print("2. TYPICAL REPOSITORY STRUCTURE")
    print("=" * 80)

    structure = [
        ("README.md", "Project documentation and entry point."),
        ("LICENSE", "Defines legal terms for using and distributing the code."),
        (".gitignore", "Specifies files Git should normally ignore."),
        (".github/", "GitHub-specific configuration."),
        (".github/workflows/", "GitHub Actions workflow definitions."),
        (".github/ISSUE_TEMPLATE/", "Issue templates."),
        (".github/pull_request_template.md", "Pull-request template."),
        ("src/", "Application source code."),
        ("tests/", "Automated tests."),
        ("docs/", "Detailed project documentation."),
        ("CHANGELOG.md", "Human-readable history of important changes."),
    ]

    for path, purpose in structure:
        print(f"{path:<38} {purpose}")

    print("\nA repository can contain much more than source code.")
    print("Repository design should make the project understandable and maintainable.")


# ============================================================================
# 4. ISSUES
# ============================================================================

class IssueState(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class IssueComment:
    author: str
    body: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Issue:
    number: int
    title: str
    body: str = ""
    state: IssueState = IssueState.OPEN
    labels: set[str] = field(default_factory=set)
    assignees: set[str] = field(default_factory=set)
    milestone: Optional[str] = None
    comments: list[IssueComment] = field(default_factory=list)

    def add_label(self, label: str) -> None:
        label = label.strip()
        if not label:
            raise ValueError("Issue label cannot be empty.")
        self.labels.add(label)

    def assign(self, username: str) -> None:
        username = username.strip()
        if not username:
            raise ValueError("Assignee username cannot be empty.")
        self.assignees.add(username)

    def add_comment(self, author: str, body: str) -> None:
        if not author.strip():
            raise ValueError("Comment author cannot be empty.")
        if not body.strip():
            raise ValueError("Comment cannot be empty.")

        self.comments.append(
            IssueComment(
                author=author,
                body=body,
            )
        )

    def close(self) -> None:
        self.state = IssueState.CLOSED

    def reopen(self) -> None:
        self.state = IssueState.OPEN

    def summary(self) -> str:
        labels = ", ".join(sorted(self.labels)) or "none"
        assignees = ", ".join(sorted(self.assignees)) or "none"
        milestone = self.milestone or "none"

        return (
            f"#{self.number} [{self.state.value}] {self.title}\n"
            f"  Labels: {labels}\n"
            f"  Assignees: {assignees}\n"
            f"  Milestone: {milestone}\n"
            f"  Comments: {len(self.comments)}"
        )


class IssueTracker:
    """
    Local model of issue-management behavior.

    GitHub itself stores this information remotely. This class is useful for
    learning the data model before interacting with a real repository.
    """

    def __init__(self) -> None:
        self._issues: dict[int, Issue] = {}
        self._next_number = 1

    def create_issue(self, title: str, body: str = "") -> Issue:
        if not title.strip():
            raise ValueError("Issue title cannot be empty.")

        issue = Issue(
            number=self._next_number,
            title=title.strip(),
            body=body,
        )

        self._issues[issue.number] = issue
        self._next_number += 1
        return issue

    def get(self, number: int) -> Issue:
        try:
            return self._issues[number]
        except KeyError as exc:
            raise KeyError(f"Issue #{number} does not exist.") from exc

    def close_issue(self, number: int) -> None:
        self.get(number).close()

    def list_issues(
        self,
        state: Optional[IssueState] = None,
        label: Optional[str] = None,
    ) -> list[Issue]:
        issues = list(self._issues.values())

        if state is not None:
            issues = [issue for issue in issues if issue.state == state]

        if label is not None:
            issues = [
                issue
                for issue in issues
                if label in issue.labels
            ]

        return sorted(issues, key=lambda issue: issue.number)


def issue_demo() -> None:
    print("\n" + "=" * 80)
    print("3. ISSUES")
    print("=" * 80)

    tracker = IssueTracker()

    bug = tracker.create_issue(
        "Login fails after password reset",
        "Users receive an unexpected error after resetting credentials.",
    )
    bug.add_label("bug")
    bug.add_label("security")
    bug.assign("developer-a")
    bug.milestone = "v2.0"
    bug.add_comment(
        "developer-a",
        "The failure appears to be caused by an expired session token.",
    )

    feature = tracker.create_issue(
        "Add CSV export",
        "Users should be able to export filtered records.",
    )
    feature.add_label("enhancement")
    feature.assign("developer-b")

    docs = tracker.create_issue(
        "Improve installation documentation",
    )
    docs.add_label("documentation")
    docs.close()

    for issue in tracker.list_issues():
        print(issue.summary())

    print("\nOpen bugs:")
    for issue in tracker.list_issues(
        state=IssueState.OPEN,
        label="bug",
    ):
        print(f"  #{issue.number}: {issue.title}")

    print("\nTypical issue lifecycle:")
    print("  Create -> Discuss -> Label -> Assign -> Develop -> Verify -> Close")
    print("  A closed issue may be reopened when the problem or requirement returns.")


# ============================================================================
# 5. ISSUE TEMPLATES AND GOOD ISSUE DESIGN
# ============================================================================

def demonstrate_issue_template() -> None:
    print("\n" + "=" * 80)
    print("4. ISSUE TEMPLATES AND ISSUE QUALITY")
    print("=" * 80)

    bug_template = {
        "title": "[Bug]: ",
        "sections": [
            "Description",
            "Steps to reproduce",
            "Expected behavior",
            "Actual behavior",
            "Environment",
            "Logs or screenshots",
            "Additional context",
        ],
    }

    feature_template = {
        "title": "[Feature]: ",
        "sections": [
            "Problem statement",
            "Proposed behavior",
            "Acceptance criteria",
            "Alternatives considered",
            "Additional context",
        ],
    }

    for template_name, template in [
        ("Bug template", bug_template),
        ("Feature template", feature_template),
    ]:
        print(f"\n{template_name}")
        print(f"Suggested title: {template['title']}")
        for section in template["sections"]:
            print(f"  - {section}")

    print("\nGood issue titles are specific.")
    print("Weak:  'It doesn't work'")
    print("Better: 'CSV export fails when a filter contains a comma'")


# ============================================================================
# 6. LABELS AND MILESTONES
# ============================================================================

@dataclass
class Milestone:
    name: str
    description: str = ""
    due_date: Optional[datetime] = None

    def is_overdue(self) -> bool:
        if self.due_date is None:
            return False

        return (
            self.due_date < datetime.now(timezone.utc)
        )


def label_and_milestone_demo() -> None:
    print("\n" + "=" * 80)
    print("5. LABELS AND MILESTONES")
    print("=" * 80)

    labels = {
        "bug": "A defect or unexpected behavior.",
        "enhancement": "A proposed improvement.",
        "documentation": "Documentation-related work.",
        "security": "Security-sensitive work.",
        "good first issue": "A task suitable for new contributors.",
        "priority:high": "A work item requiring high priority.",
    }

    for name, meaning in labels.items():
        print(f"{name:<22} {meaning}")

    milestone = Milestone(
        name="v2.0",
        description="Major production release.",
        due_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
    )

    print(f"\nMilestone: {milestone.name}")
    print(f"Description: {milestone.description}")
    print(f"Due date: {milestone.due_date.date()}")
    print(f"Overdue: {milestone.is_overdue()}")


# ============================================================================
# 7. GITHUB PROJECTS
# ============================================================================

class ProjectStatus(str, Enum):
    TODO = "Todo"
    IN_PROGRESS = "In Progress"
    DONE = "Done"
    BLOCKED = "Blocked"


@dataclass
class ProjectItem:
    item_id: int
    title: str
    status: ProjectStatus = ProjectStatus.TODO
    priority: int = 3
    labels: set[str] = field(default_factory=set)
    linked_issue: Optional[int] = None

    def move_to(self, status: ProjectStatus) -> None:
        self.status = status


class ProjectBoard:
    """
    A local Kanban-style model inspired by GitHub Projects.

    Real GitHub Projects can connect work items and organize them into
    configurable views and fields. This class demonstrates the underlying
    planning concepts without requiring a GitHub account.
    """

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ValueError("Project name cannot be empty.")

        self.name = name
        self.items: dict[int, ProjectItem] = {}
        self._next_id = 1

    def add_item(
        self,
        title: str,
        priority: int = 3,
        linked_issue: Optional[int] = None,
    ) -> ProjectItem:
        if not title.strip():
            raise ValueError("Project item title cannot be empty.")

        if priority not in {1, 2, 3, 4, 5}:
            raise ValueError("Priority must be between 1 and 5.")

        item = ProjectItem(
            item_id=self._next_id,
            title=title.strip(),
            priority=priority,
            linked_issue=linked_issue,
        )

        self.items[item.item_id] = item
        self._next_id += 1
        return item

    def move_item(self, item_id: int, status: ProjectStatus) -> None:
        if item_id not in self.items:
            raise KeyError(f"Project item {item_id} does not exist.")

        self.items[item_id].move_to(status)

    def items_by_status(self, status: ProjectStatus) -> list[ProjectItem]:
        return [
            item
            for item in self.items.values()
            if item.status == status
        ]

    def progress(self) -> float:
        if not self.items:
            return 0.0

        completed = sum(
            item.status == ProjectStatus.DONE
            for item in self.items.values()
        )

        return completed / len(self.items) * 100.0

    def display(self) -> None:
        print(f"\nProject: {self.name}")
        for status in ProjectStatus:
            print(f"\n[{status.value}]")

            items = self.items_by_status(status)

            if not items:
                print("  -")

            for item in items:
                print(
                    f"  #{item.item_id} {item.title} "
                    f"(priority={item.priority})"
                )

        print(f"\nCompletion: {self.progress():.1f}%")


def project_demo() -> None:
    print("\n" + "=" * 80)
    print("6. GITHUB PROJECTS")
    print("=" * 80)

    project = ProjectBoard("Asset Management Platform")

    database = project.add_item(
        "Design database schema",
        priority=1,
    )

    api = project.add_item(
        "Implement REST API",
        priority=1,
    )

    frontend = project.add_item(
        "Build dashboard",
        priority=2,
    )

    testing = project.add_item(
        "Create integration tests",
        priority=2,
    )

    deployment = project.add_item(
        "Prepare production deployment",
        priority=3,
    )

    project.move_item(database.item_id, ProjectStatus.DONE)
    project.move_item(api.item_id, ProjectStatus.IN_PROGRESS)
    project.move_item(frontend.item_id, ProjectStatus.TODO)
    project.move_item(testing.item_id, ProjectStatus.BLOCKED)

    deployment.labels.add("release")

    project.display()

    print("\nTypical Project concepts:")
    print("  Views: table, board, roadmap-style planning")
    print("  Fields: status, priority, dates, estimates, custom metadata")
    print("  Items: issues, pull requests, and other trackable work")
    print("  Filters: narrow a view to a useful subset of work")


# ============================================================================
# 8. RELEASES AND TAGS
# ============================================================================

SEMVER_PATTERN = re.compile(
    r"^v?"
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@dataclass(frozen=True, order=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    build: Optional[str] = None

    @classmethod
    def parse(cls, value: str) -> "SemanticVersion":
        match = SEMVER_PATTERN.fullmatch(value.strip())

        if not match:
            raise ValueError(
                f"Invalid semantic version: {value!r}"
            )

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease,
            build=build,
        )

    def __str__(self) -> str:
        value = f"v{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            value += f"-{self.prerelease}"

        if self.build:
            value += f"+{self.build}"

        return value

    def bump_major(self) -> "SemanticVersion":
        return SemanticVersion(self.major + 1, 0, 0)

    def bump_minor(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_patch(self) -> "SemanticVersion":
        return SemanticVersion(self.major, self.minor, self.patch + 1)


@dataclass
class ReleaseAsset:
    name: str
    size_bytes: int
    content_type: str

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("Release asset name cannot be empty.")

        if self.size_bytes < 0:
            raise ValueError("Release asset size cannot be negative.")


@dataclass
class Release:
    version: SemanticVersion
    name: str
    body: str
    tag_name: str
    prerelease: bool = False
    draft: bool = False
    assets: list[ReleaseAsset] = field(default_factory=list)

    def add_asset(self, asset: ReleaseAsset) -> None:
        asset.validate()

        if any(existing.name == asset.name for existing in self.assets):
            raise ValueError(
                f"An asset named {asset.name!r} already exists."
            )

        self.assets.append(asset)

    def validate(self) -> list[str]:
        errors: list[str] = []

        if self.tag_name != str(self.version):
            errors.append(
                "Tag name should match the version in this learning model."
            )

        if not self.name.strip():
            errors.append("Release name cannot be empty.")

        if self.draft and self.prerelease:
            # This combination can be meaningful in some workflows, but the
            # learning model intentionally flags it for review.
            errors.append(
                "Review whether a draft prerelease is intentional."
            )

        return errors


def release_demo() -> None:
    print("\n" + "=" * 80)
    print("7. RELEASES, TAGS, AND SEMANTIC VERSIONING")
    print("=" * 80)

    current = SemanticVersion.parse("v1.4.2")

    print(f"Current version: {current}")
    print(f"Patch release:  {current.bump_patch()}")
    print(f"Minor release:  {current.bump_minor()}")
    print(f"Major release:  {current.bump_major()}")

    examples = [
        "v1.0.0",
        "v2.5.3",
        "v3.0.0-beta.1",
        "v1.2.3+build.17",
    ]

    print("\nSemantic-version examples:")
    for value in examples:
        parsed = SemanticVersion.parse(value)
        print(
            f"  {value:<20} -> "
            f"major={parsed.major}, "
            f"minor={parsed.minor}, "
            f"patch={parsed.patch}, "
            f"prerelease={parsed.prerelease}"
        )

    release = Release(
        version=SemanticVersion.parse("v2.0.0"),
        name="Asset Management Platform 2.0",
        body=(
            "Major release containing the redesigned dashboard, "
            "workflow improvements, and API changes."
        ),
        tag_name="v2.0.0",
    )

    release.add_asset(
        ReleaseAsset(
            name="asset-management-linux-x64.tar.gz",
            size_bytes=8_500_000,
            content_type="application/gzip",
        )
    )

    release.add_asset(
        ReleaseAsset(
            name="asset-management-windows-x64.zip",
            size_bytes=9_100_000,
            content_type="application/zip",
        )
    )

    print("\nRelease:")
    print(f"  Name: {release.name}")
    print(f"  Tag: {release.tag_name}")
    print(f"  Draft: {release.draft}")
    print(f"  Prerelease: {release.prerelease}")

    print("\nAssets:")
    for asset in release.assets:
        print(
            f"  {asset.name} "
            f"({asset.size_bytes:,} bytes, {asset.content_type})"
        )

    print("\nSemantic versioning principle:")
    print("  MAJOR: incompatible API or behavior changes")
    print("  MINOR: backward-compatible functionality")
    print("  PATCH: backward-compatible bug fixes")


# ============================================================================
# 9. GITHUB API CLIENT
# ============================================================================

class GitHubAPIError(RuntimeError):
    """Raised when the GitHub API returns an error."""


@dataclass
class APIResponse:
    status_code: int
    data: Any
    headers: dict[str, str]


class GitHubClient:
    """
    Small standard-library GitHub API client.

    The implementation deliberately keeps network access explicit. The class
    supports authentication, GET requests, query parameters, pagination, and
    basic error handling.

    It does not automatically perform destructive operations.
    """

    API_ROOT = "https://api.github.com"

    def __init__(
        self,
        token: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        self.token = token
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> APIResponse:
        if not path.startswith("/"):
            path = "/" + path

        url = self.API_ROOT + path

        if query:
            query_string = urlencode(
                {
                    key: str(value)
                    for key, value in query.items()
                    if value is not None
                }
            )

            if query_string:
                url += "?" + query_string

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-learning-example",
        }

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        encoded_body = None

        if body is not None:
            encoded_body = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            url=url,
            data=encoded_body,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")

                if raw:
                    data = json.loads(raw)
                else:
                    data = None

                return APIResponse(
                    status_code=response.status,
                    data=data,
                    headers=dict(response.headers.items()),
                )

        except HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {"message": raw}

            raise GitHubAPIError(
                f"GitHub API returned HTTP {exc.code}: "
                f"{data.get('message', data)}"
            ) from exc

        except URLError as exc:
            raise GitHubAPIError(
                f"Network error while contacting GitHub: {exc.reason}"
            ) from exc

    def get_repository(
        self,
        owner: str,
        repository: str,
    ) -> dict[str, Any]:
        path = (
            f"/repos/{quote(owner, safe='')}/"
            f"{quote(repository, safe='')}"
        )

        response = self.request("GET", path)

        if not isinstance(response.data, dict):
            raise GitHubAPIError("Unexpected repository response.")

        return response.data

    def list_issues(
        self,
        owner: str,
        repository: str,
        *,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        if state not in {"open", "closed", "all"}:
            raise ValueError(
                "state must be 'open', 'closed', or 'all'."
            )

        per_page = max(1, min(per_page, 100))
        page = max(1, page)

        path = (
            f"/repos/{quote(owner, safe='')}/"
            f"{quote(repository, safe='')}/issues"
        )

        response = self.request(
            "GET",
            path,
            query={
                "state": state,
                "per_page": per_page,
                "page": page,
            },
        )

        if not isinstance(response.data, list):
            raise GitHubAPIError("Unexpected issue list response.")

        return response.data

    def list_releases(
        self,
        owner: str,
        repository: str,
        *,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        per_page = max(1, min(per_page, 100))
        page = max(1, page)

        path = (
            f"/repos/{quote(owner, safe='')}/"
            f"{quote(repository, safe='')}/releases"
        )

        response = self.request(
            "GET",
            path,
            query={
                "per_page": per_page,
                "page": page,
            },
        )

        if not isinstance(response.data, list):
            raise GitHubAPIError("Unexpected release list response.")

        return response.data

    def list_all_pages(
        self,
        path: str,
        *,
        per_page: int = 100,
        max_pages: int = 10,
    ) -> Iterator[dict[str, Any]]:
        """
        Demonstrates explicit pagination.

        The maximum-page limit prevents an educational example from making an
        unbounded number of requests.
        """
        per_page = max(1, min(per_page, 100))

        for page in range(1, max_pages + 1):
            response = self.request(
                "GET",
                path,
                query={
                    "per_page": per_page,
                    "page": page,
                },
            )

            if not isinstance(response.data, list):
                raise GitHubAPIError(
                    "Pagination endpoint did not return a list."
                )

            if not response.data:
                return

            for item in response.data:
                if isinstance(item, dict):
                    yield item

            if len(response.data) < per_page:
                return


def api_demo() -> None:
    print("\n" + "=" * 80)
    print("8. GITHUB REST API")
    print("=" * 80)

    token = os.getenv("GITHUB_TOKEN")
    owner = os.getenv("GITHUB_OWNER", "")
    repository = os.getenv("GITHUB_REPOSITORY", "")

    print("The API example is disabled unless GITHUB_OWNER and")
    print("GITHUB_REPOSITORY are supplied.")
    print("A token is recommended for authenticated requests.")

    if not owner or not repository:
        print("\nNo repository configured. Skipping network requests.")
        return

    client = GitHubClient(token=token)

    try:
        data = client.get_repository(owner, repository)

        print(f"\nRepository: {data.get('full_name')}")
        print(f"Description: {data.get('description')}")
        print(f"Visibility: {data.get('visibility')}")
        print(f"Default branch: {data.get('default_branch')}")
        print(f"Stars: {data.get('stargazers_count')}")
        print(f"Forks: {data.get('forks_count')}")
        print(f"Open issues: {data.get('open_issues_count')}")

        issues = client.list_issues(
            owner,
            repository,
            state="open",
            per_page=10,
        )

        print(f"\nFirst {len(issues)} open issue/PR records:")

        for item in issues:
            print(
                f"  #{item.get('number')}: "
                f"{item.get('title')}"
            )

        releases = client.list_releases(
            owner,
            repository,
            per_page=10,
        )

        print(f"\nReleases returned: {len(releases)}")

        for release in releases:
            print(
                f"  {release.get('tag_name')} - "
                f"{release.get('name')}"
            )

    except GitHubAPIError as exc:
        print(f"\nAPI request failed safely: {exc}")


# ============================================================================
# 10. SEARCH AND FILTERING
# ============================================================================

def filter_issues(
    issues: Iterable[Issue],
    *,
    text: Optional[str] = None,
    labels: Optional[set[str]] = None,
    state: Optional[IssueState] = None,
) -> list[Issue]:
    """
    Flexible local filtering.

    Complexity:
        O(n * L) in the worst case, where n is issue count and L is the
        number of required labels.
    """
    result = list(issues)

    if text:
        search_text = text.casefold()
        result = [
            issue
            for issue in result
            if (
                search_text in issue.title.casefold()
                or search_text in issue.body.casefold()
            )
        ]

    if labels:
        result = [
            issue
            for issue in result
            if labels.issubset(issue.labels)
        ]

    if state:
        result = [
            issue
            for issue in result
            if issue.state == state
        ]

    return result


def search_demo() -> None:
    print("\n" + "=" * 80)
    print("9. SEARCH, FILTERING, AND QUERY DESIGN")
    print("=" * 80)

    tracker = IssueTracker()

    first = tracker.create_issue(
        "CSV export fails with comma-containing filters",
        "CSV parser rejects a filter value containing commas.",
    )
    first.add_label("bug")
    first.add_label("export")

    second = tracker.create_issue(
        "Add CSV export scheduling",
        "Allow users to schedule recurring exports.",
    )
    second.add_label("enhancement")
    second.add_label("export")

    third = tracker.create_issue(
        "Improve export documentation",
        "Document CSV column behavior.",
    )
    third.add_label("documentation")
    third.add_label("export")

    results = filter_issues(
        tracker.list_issues(),
        text="CSV",
        labels={"export"},
    )

    print("Matching issues:")
    for issue in results:
        print(f"  #{issue.number}: {issue.title}")


# ============================================================================
# 11. VALIDATION AND ERROR HANDLING
# ============================================================================

def validation_demo() -> None:
    print("\n" + "=" * 80)
    print("10. VALIDATION AND ERROR HANDLING")
    print("=" * 80)

    invalid_repository = Repository(
        owner="",
        name="invalid repository name!",
    )

    errors = invalid_repository.validate()

    print("Repository validation errors:")
    for error in errors:
        print(f"  - {error}")

    print("\nInvalid semantic-version example:")

    try:
        SemanticVersion.parse("version-two")
    except ValueError as exc:
        print(f"  Correctly rejected: {exc}")

    print("\nInvalid issue example:")

    try:
        IssueTracker().create_issue("")
    except ValueError as exc:
        print(f"  Correctly rejected: {exc}")

    print("\nGeneral rule:")
    print("  Validate user-controlled input before changing application state.")
    print("  Catch expected exceptions at system boundaries.")
    print("  Do not hide unexpected programming errors with broad exception handling.")


# ============================================================================
# 12. SECURITY
# ============================================================================

def security_demo() -> None:
    print("\n" + "=" * 80)
    print("11. SECURITY CONSIDERATIONS")
    print("=" * 80)

    rules = [
        "Never hard-code a GitHub token in source code.",
        "Do not commit .env files containing credentials.",
        "Use environment variables or a secure secret-management mechanism.",
        "Give tokens only the permissions required for the task.",
        "Review repository visibility before publishing sensitive material.",
        "Do not place passwords, private keys, API keys, or personal data in issues.",
        "Treat GitHub Actions secrets and workflow permissions as security boundaries.",
        "Review third-party GitHub Actions before trusting them in production.",
        "Be careful when workflows execute code from pull requests.",
        "Rotate credentials if a secret is accidentally exposed.",
    ]

    for index, rule in enumerate(rules, start=1):
        print(f"{index:>2}. {rule}")

    print("\nExample of safe token access:")
    print('  token = os.getenv("GITHUB_TOKEN")')
    print("The token itself is never printed by this program.")


# ============================================================================
# 13. PERFORMANCE AND RATE LIMITS
# ============================================================================

def performance_demo() -> None:
    print("\n" + "=" * 80)
    print("12. PERFORMANCE AND API EFFICIENCY")
    print("=" * 80)

    principles = [
        (
            "Pagination",
            "Retrieve API results in pages instead of assuming all records fit in one response.",
        ),
        (
            "Filtering",
            "Ask the server for narrower data when the API supports suitable filters.",
        ),
        (
            "Caching",
            "Avoid repeatedly requesting information that has not changed.",
        ),
        (
            "Batching",
            "Group compatible operations where the API provides batch mechanisms.",
        ),
        (
            "Backoff",
            "Slow down after transient failures instead of repeatedly retrying immediately.",
        ),
        (
            "Timeouts",
            "Never allow network requests to wait indefinitely.",
        ),
    ]

    for name, explanation in principles:
        print(f"{name:<14} {explanation}")

    print("\nLocal complexity examples:")
    print("  Dictionary lookup by issue number: average O(1)")
    print("  Filtering n issues: O(n)")
    print("  Sorting n issues: O(n log n)")
    print("  Project progress calculation: O(n)")


# ============================================================================
# 14. RELEASE WORKFLOW
# ============================================================================

def release_workflow_demo() -> None:
    print("\n" + "=" * 80)
    print("13. PRACTICAL RELEASE WORKFLOW")
    print("=" * 80)

    workflow = [
        "1. Implement a change on a branch.",
        "2. Commit the change with a meaningful message.",
        "3. Open a pull request.",
        "4. Review and test the pull request.",
        "5. Merge the approved change.",
        "6. Update release notes or changelog information.",
        "7. Create a Git tag representing the version.",
        "8. Create a GitHub Release associated with that tag.",
        "9. Attach production artifacts when appropriate.",
        "10. Communicate important breaking changes and migration requirements.",
    ]

    for step in workflow:
        print(step)

    print("\nExample version progression:")
    print("  v1.0.0 -> v1.0.1  bug fix")
    print("  v1.0.1 -> v1.1.0  backward-compatible feature")
    print("  v1.1.0 -> v2.0.0  incompatible change")


# ============================================================================
# 15. REALISTIC LOCAL CASE STUDY
# ============================================================================

@dataclass
class WorkItem:
    title: str
    issue_number: int
    status: ProjectStatus
    priority: int
    release: str


class EngineeringWorkspace:
    """
    Combines repository, issues, project planning, and releases.

    This is a local educational model of how these concepts relate:
        Repository
            |
            +-- Issues
            |
            +-- Project planning
            |
            +-- Releases/tags
    """

    def __init__(self, repository: Repository) -> None:
        self.repository = repository
        self.issues = IssueTracker()
        self.project = ProjectBoard(
            f"{repository.name} Delivery Board"
        )
        self.releases: dict[str, Release] = {}

    def create_work_item(
        self,
        title: str,
        body: str,
        *,
        priority: int,
        release: str,
        labels: Iterable[str],
    ) -> WorkItem:
        issue = self.issues.create_issue(title, body)

        for label in labels:
            issue.add_label(label)

        project_item = self.project.add_item(
            title=title,
            priority=priority,
            linked_issue=issue.number,
        )

        return WorkItem(
            title=title,
            issue_number=issue.number,
            status=project_item.status,
            priority=priority,
            release=release,
        )

    def add_release(
        self,
        version: str,
        name: str,
        notes: str,
    ) -> Release:
        parsed = SemanticVersion.parse(version)

        release = Release(
            version=parsed,
            name=name,
            body=notes,
            tag_name=str(parsed),
        )

        self.releases[str(parsed)] = release
        return release

    def report(self) -> None:
        print("\n" + "=" * 80)
        print("14. INTEGRATED ENGINEERING WORKSPACE")
        print("=" * 80)

        print(f"Repository: {self.repository.full_name}")
        print(f"Visibility: {self.repository.visibility.value}")
        print(f"Default branch: {self.repository.default_branch}")

        print("\nIssues:")
        for issue in self.issues.list_issues():
            print(
                f"  #{issue.number} "
                f"[{issue.state.value}] "
                f"{issue.title}"
            )

        self.project.display()

        print("\nReleases:")
        for version, release in sorted(self.releases.items()):
            print(
                f"  {version}: "
                f"{release.name} "
                f"(draft={release.draft}, prerelease={release.prerelease})"
            )


def integrated_case_study() -> None:
    repository = repository_example()

    workspace = EngineeringWorkspace(repository)

    database_item = workspace.create_work_item(
        "Design asset database",
        "Create normalized tables for assets, locations, owners, and status.",
        priority=1,
        release="v1.0.0",
        labels={"feature", "database"},
    )

    api_item = workspace.create_work_item(
        "Implement asset API",
        "Create validated endpoints for asset operations.",
        priority=1,
        release="v1.0.0",
        labels={"feature", "api"},
    )

    security_item = workspace.create_work_item(
        "Audit authentication flow",
        "Review authentication and authorization boundaries.",
        priority=1,
        release="v1.1.0",
        labels={"security"},
    )

    workspace.project.move_item(
        database_item.issue_number,
        ProjectStatus.DONE,
    )

    # The project item ID is not necessarily equal to the issue number in a
    # real GitHub Project, so we find it explicitly in this local model.
    for item in workspace.project.items.values():
        if item.linked_issue == api_item.issue_number:
            item.move_to(ProjectStatus.IN_PROGRESS)

        if item.linked_issue == security_item.issue_number:
            item.move_to(ProjectStatus.BLOCKED)

    release = workspace.add_release(
        "v1.0.0",
        "Asset Management Platform 1.0",
        (
            "Initial production release containing the asset database "
            "and core API."
        ),
    )

    release.add_asset(
        ReleaseAsset(
            name="asset-platform-v1.0.0.zip",
            size_bytes=12_500_000,
            content_type="application/zip",
        )
    )

    workspace.report()


# ============================================================================
# 16. TESTING
# ============================================================================

def run_tests() -> None:
    print("\n" + "=" * 80)
    print("15. AUTOMATED TESTS")
    print("=" * 80)

    repository = Repository(
        owner="test-owner",
        name="test-repository",
    )

    assert repository.full_name == "test-owner/test-repository"

    repository.add_topic("Python")
    assert "python" in repository.topics

    tracker = IssueTracker()
    issue = tracker.create_issue("Test issue")
    issue.add_label("bug")
    issue.assign("tester")
    issue.close()

    assert issue.state == IssueState.CLOSED
    assert "bug" in issue.labels
    assert "tester" in issue.assignees

    project = ProjectBoard("Test Project")
    item = project.add_item("Testing task", priority=1)
    assert project.progress() == 0.0

    project.move_item(item.item_id, ProjectStatus.DONE)
    assert project.progress() == 100.0

    version = SemanticVersion.parse("v1.2.3")
    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert str(version.bump_patch()) == "v1.2.4"

    release = Release(
        version=version,
        name="Test Release",
        body="Testing release behavior.",
        tag_name="v1.2.3",
    )

    release.add_asset(
        ReleaseAsset(
            name="test.zip",
            size_bytes=100,
            content_type="application/zip",
        )
    )

    assert len(release.assets) == 1

    print("All built-in tests passed.")


# ============================================================================
# 17. GIT VS GITHUB VS ISSUES VS PROJECTS VS RELEASES
# ============================================================================

def comparison_demo() -> None:
    print("\n" + "=" * 80)
    print("16. IMPORTANT DISTINCTIONS")
    print("=" * 80)

    rows = [
        ("Git", "Version history", "Commits, branches, merges, tags"),
        ("GitHub repository", "Hosted collaboration space", "Code, settings, metadata"),
        ("Issue", "Work/discussion tracking", "Bug, feature, task, discussion"),
        ("Project", "Planning/workflow", "Views, fields, status, planning"),
        ("Release", "Published version", "Tag, notes, assets"),
        ("Pull request", "Code review/change integration", "Diff, review, checks, merge"),
        ("Tag", "Git history marker", "Version or significant commit"),
    ]

    print(f"{'Concept':<22} {'Purpose':<32} {'Typical content'}")
    print("-" * 80)

    for concept, purpose, content in rows:
        print(f"{concept:<22} {purpose:<32} {content}")


# ============================================================================
# 18. COMMON MISTAKES
# ============================================================================

def common_mistakes_demo() -> None:
    print("\n" + "=" * 80)
    print("17. COMMON MISTAKES")
    print("=" * 80)

    mistakes = [
        (
            "Using issues as an unstructured dump",
            "Use clear titles, labels, descriptions, and acceptance criteria.",
        ),
        (
            "Creating releases without meaningful versioning",
            "Use a consistent versioning strategy appropriate to the project.",
        ),
        (
            "Putting secrets in the repository",
            "Use secret-management mechanisms and rotate exposed credentials.",
        ),
        (
            "Treating a Project as a replacement for issue details",
            "Keep detailed technical context in the work item and use Projects for planning.",
        ),
        (
            "Ignoring closed issues",
            "Closed issues provide historical context and can document decisions.",
        ),
        (
            "Using too many labels",
            "Keep the taxonomy understandable and useful.",
        ),
        (
            "Making every repository public",
            "Choose visibility based on business, legal, security, and collaboration requirements.",
        ),
        (
            "Making network requests without timeouts",
            "Use explicit request timeouts.",
        ),
        (
            "Assuming API responses are unlimited",
            "Use pagination and respect API limits.",
        ),
        (
            "Printing authentication tokens during debugging",
            "Never expose credentials in logs.",
        ),
    ]

    for mistake, correction in mistakes:
        print(f"\nMistake: {mistake}")
        print(f"Better practice: {correction}")


# ============================================================================
# 19. ADVANCED DESIGN CONCEPTS
# ============================================================================

def advanced_design_demo() -> None:
    print("\n" + "=" * 80)
    print("18. ADVANCED DESIGN CONCEPTS")
    print("=" * 80)

    concepts = [
        "Issue-driven development",
        "Project-based portfolio planning",
        "Release trains and milestone planning",
        "Semantic versioning",
        "Automated release pipelines",
        "Changelog generation",
        "Continuous integration and continuous delivery",
        "Repository governance",
        "Branch protection and required checks",
        "Least-privilege automation permissions",
        "Reusable workflow design",
        "Dependency management",
        "Security scanning",
        "Auditability",
        "API pagination and caching",
        "Idempotent automation",
        "Observability and structured logging",
    ]

    for index, concept in enumerate(concepts, start=1):
        print(f"{index:>2}. {concept}")

    print("\nImportant architectural relationship:")
    print("  Code change")
    print("      -> Commit")
    print("      -> Pull request")
    print("      -> Review and checks")
    print("      -> Merge")
    print("      -> Tag")
    print("      -> Release")
    print("      -> Project and issue status updated")
    print("      -> Users receive the published version")


# ============================================================================
# 20. AUTOMATION SAFETY
# ============================================================================

def automation_safety_demo() -> None:
    print("\n" + "=" * 80)
    print("19. AUTOMATION SAFETY")
    print("=" * 80)

    safeguards = [
        "Validate all inputs before calling mutation endpoints.",
        "Use dry-run modes for scripts that modify repositories.",
        "Log identifiers and outcomes, not secrets.",
        "Use idempotent operations where practical.",
        "Check whether an issue, release, or label already exists before creating duplicates.",
        "Use explicit repository and owner configuration.",
        "Fail closed when required credentials are missing.",
        "Handle HTTP 401, 403, 404, 409, 422, and 5xx responses deliberately.",
        "Retry only transient failures and use bounded exponential backoff.",
        "Test automation against a non-production repository before wider deployment.",
    ]

    for safeguard in safeguards:
        print(f"  - {safeguard}")


# ============================================================================
# 21. MINI AUTOMATION ENGINE
# ============================================================================

@dataclass
class AutomationRule:
    name: str
    trigger: str
    action: str

    def describe(self) -> str:
        return (
            f"WHEN {self.trigger} "
            f"THEN {self.action}"
        )


class LocalAutomationEngine:
    """
    Small rule engine illustrating how GitHub automation can be modeled.

    It intentionally performs no remote GitHub mutations.
    """

    def __init__(self) -> None:
        self.rules: list[AutomationRule] = []

    def add_rule(
        self,
        name: str,
        trigger: str,
        action: str,
    ) -> None:
        if not name.strip():
            raise ValueError("Rule name cannot be empty.")

        self.rules.append(
            AutomationRule(
                name=name,
                trigger=trigger,
                action=action,
            )
        )

    def show_rules(self) -> None:
        for rule in self.rules:
            print(f"  {rule.name}: {rule.describe()}")


def automation_demo() -> None:
    print("\n" + "=" * 80)
    print("20. AUTOMATION RULES")
    print("=" * 80)

    engine = LocalAutomationEngine()

    engine.add_rule(
        "Close stale bug workflow",
        "issue is closed",
        "move linked Project item to Done",
    )

    engine.add_rule(
        "Release tracking",
        "release is published",
        "update release-related Project items",
    )

    engine.add_rule(
        "Security issue routing",
        "issue receives security label",
        "route work to the security workflow",
    )

    engine.show_rules()


# ============================================================================
# 22. COMMAND-LINE ENTRY POINT
# ============================================================================

def print_menu() -> None:
    print("\n" + "=" * 80)
    print("GITHUB LEARNING PROGRAM")
    print("=" * 80)
    print("1. Fundamentals")
    print("2. Repository model")
    print("3. Repository structure")
    print("4. Issues")
    print("5. Issue templates")
    print("6. Labels and milestones")
    print("7. Projects")
    print("8. Releases and semantic versioning")
    print("9. GitHub API")
    print("10. Search and filtering")
    print("11. Validation and errors")
    print("12. Security")
    print("13. Performance")
    print("14. Release workflow")
    print("15. Integrated case study")
    print("16. Tests")
    print("17. Comparisons")
    print("18. Common mistakes")
    print("19. Advanced design")
    print("20. Automation safety")
    print("21. Automation rules")
    print("22. Run complete lesson")
    print("0. Exit")


def run_complete_lesson() -> None:
    explain_fundamentals()
    repository_example()
    demonstrate_repository_structure()
    issue_demo()
    demonstrate_issue_template()
    label_and_milestone_demo()
    project_demo()
    release_demo()
    api_demo()
    search_demo()
    validation_demo()
    security_demo()
    performance_demo()
    release_workflow_demo()
    integrated_case_study()
    run_tests()
    comparison_demo()
    common_mistakes_demo()
    advanced_design_demo()
    automation_safety_demo()
    automation_demo()


def interactive_mode() -> None:
    actions = {
        "1": explain_fundamentals,
        "2": lambda: print(repository_example()),
        "3": demonstrate_repository_structure,
        "4": issue_demo,
        "5": demonstrate_issue_template,
        "6": label_and_milestone_demo,
        "7": project_demo,
        "8": release_demo,
        "9": api_demo,
        "10": search_demo,
        "11": validation_demo,
        "12": security_demo,
        "13": performance_demo,
        "14": release_workflow_demo,
        "15": integrated_case_study,
        "16": run_tests,
        "17": comparison_demo,
        "18": common_mistakes_demo,
        "19": advanced_design_demo,
        "20": automation_safety_demo,
        "21": automation_demo,
        "22": run_complete_lesson,
    }

    while True:
        print_menu()
        choice = input("\nSelect an option: ").strip()

        if choice == "0":
            print("Exiting.")
            return

        action = actions.get(choice)

        if action is None:
            print("Invalid option.")
            continue

        try:
            action()
        except KeyboardInterrupt:
            print("\nOperation interrupted.")
        except Exception as exc:
            print(
                f"\nUnexpected error: {type(exc).__name__}: {exc}"
            )


def main() -> None:
    # With a command-line argument, the complete lesson can be executed
    # without entering the interactive menu.
    if len(sys.argv) > 1 and sys.argv[1] in {
        "--all",
        "--complete",
    }:
        run_complete_lesson()
        return

    if len(sys.argv) > 1 and sys.argv[1] == "--tests":
        run_tests()
        return

    interactive_mode()


if __name__ == "__main__":
    main()
