"""
Git Collaboration: Pull Requests, Code Review, and Git Workflows
================================================================

A standalone study program covering Git collaboration from beginner through
advanced practical workflows.

The demonstrations model Git concepts in Python without requiring Git itself.
The script also detects whether Git is installed and, when available, can run
safe read-only Git commands against a temporary repository created by the
script.

Topics demonstrated:
- Distributed version control concepts
- Repository, commit, branch, HEAD, working tree, index
- Branching and merging
- Fast-forward and three-way merges
- Pull-request concepts
- Code review workflows
- Review comments and approval rules
- Feature, release, hotfix, trunk-based, and GitHub-style workflows
- Merge conflicts and conflict resolution
- Rebase concepts and safety considerations
- Cherry-picking
- Revert versus reset
- Commit quality and atomic changes
- Protected branches and CI-style checks
- Semantic validation of pull requests
- Collaboration policies
- Audit trails
- Graph analysis
- Failure modes and recovery
- Performance and scalability considerations
- Security considerations
- A practical collaboration simulator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterable, Optional
import copy
import json
import os
import shutil
import subprocess
import textwrap
import time
import unittest


# ============================================================================
# 1. FUNDAMENTAL DATA TYPES
# ============================================================================

class ReviewState(Enum):
    """Possible states of a pull-request review."""
    COMMENTED = "commented"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"


class PullRequestState(Enum):
    """Lifecycle states for a pull request."""
    OPEN = "open"
    MERGED = "merged"
    CLOSED = "closed"


class CheckState(Enum):
    """Simplified CI/check status."""
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


@dataclass(frozen=True)
class Commit:
    """
    A simplified immutable commit.

    Real Git commits contain a tree reference, parent references, author,
    committer, timestamps, message, and metadata. This model keeps the
    educationally important parts.
    """

    commit_id: str
    author: str
    message: str
    parent_ids: tuple[str, ...] = ()
    files: tuple[tuple[str, str], ...] = ()

    def file_map(self) -> dict[str, str]:
        return dict(self.files)


@dataclass
class Branch:
    """A branch is a movable name pointing to a commit."""
    name: str
    head: Optional[str]


@dataclass
class Review:
    """A review submitted by a collaborator."""
    reviewer: str
    state: ReviewState
    comments: list[str] = field(default_factory=list)


@dataclass
class PullRequest:
    """A simplified pull request with review and check state."""
    number: int
    title: str
    author: str
    source_branch: str
    target_branch: str
    description: str
    state: PullRequestState = PullRequestState.OPEN
    reviews: list[Review] = field(default_factory=list)
    checks: dict[str, CheckState] = field(default_factory=dict)

    def approvals(self) -> int:
        return sum(r.state == ReviewState.APPROVED for r in self.reviews)

    def has_requested_changes(self) -> bool:
        return any(
            r.state == ReviewState.CHANGES_REQUESTED
            for r in self.reviews
        )


# ============================================================================
# 2. A SMALL EDUCATIONAL GIT MODEL
# ============================================================================

class MiniGit:
    """
    Educational simulation of selected Git mechanisms.

    This is deliberately not a replacement for Git. It models the concepts
    needed to understand collaboration while keeping the implementation
    inspectable.
    """

    def __init__(self) -> None:
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, Branch] = {}
        self.current_branch = "main"
        self._counter = 0

        # An empty repository starts with an empty main branch.
        self.branches["main"] = Branch("main", None)

    @property
    def head(self) -> Optional[str]:
        """Return the commit currently referenced by the checked-out branch."""
        return self.branches[self.current_branch].head

    def _new_id(self) -> str:
        self._counter += 1
        return f"C{self._counter:04d}"

    def commit(
        self,
        author: str,
        message: str,
        changes: dict[str, Optional[str]],
    ) -> str:
        """
        Create a commit.

        A value of None deletes a file. Other values create or replace it.
        The complete file snapshot is stored to make the simulation easy to
        reason about.
        """
        parent = self.head
        snapshot = self.snapshot(parent)

        for path, content in changes.items():
            if content is None:
                snapshot.pop(path, None)
            else:
                snapshot[path] = content

        commit_id = self._new_id()
        parents = (parent,) if parent else ()

        self.commits[commit_id] = Commit(
            commit_id=commit_id,
            author=author,
            message=message,
            parent_ids=parents,
            files=tuple(sorted(snapshot.items())),
        )
        self.branches[self.current_branch].head = commit_id
        return commit_id

    def snapshot(self, commit_id: Optional[str]) -> dict[str, str]:
        """Return the file snapshot represented by a commit."""
        if commit_id is None:
            return {}
        return self.commits[commit_id].file_map()

    def create_branch(self, name: str, from_commit: Optional[str] = None) -> None:
        """Create a branch pointing to the specified commit or current HEAD."""
        if name in self.branches:
            raise ValueError(f"Branch already exists: {name}")

        if from_commit is None:
            from_commit = self.head

        if from_commit is not None and from_commit not in self.commits:
            raise ValueError(f"Unknown commit: {from_commit}")

        self.branches[name] = Branch(name, from_commit)

    def checkout(self, name: str) -> None:
        """Switch the current branch."""
        if name not in self.branches:
            raise ValueError(f"Unknown branch: {name}")
        self.current_branch = name

    def ancestors(self, commit_id: Optional[str]) -> set[str]:
        """Return all ancestors, including the supplied commit."""
        if commit_id is None:
            return set()

        result: set[str] = set()
        stack = [commit_id]

        while stack:
            current = stack.pop()
            if current in result:
                continue

            result.add(current)
            stack.extend(self.commits[current].parent_ids)

        return result

    def is_ancestor(self, older: Optional[str], newer: Optional[str]) -> bool:
        """Determine whether older is reachable from newer."""
        if older is None:
            return True
        return older in self.ancestors(newer)

    def log(self, branch_name: Optional[str] = None) -> list[Commit]:
        """Return commits reachable from a branch in reverse traversal order."""
        branch_name = branch_name or self.current_branch
        branch_head = self.branches[branch_name].head

        if branch_head is None:
            return []

        result: list[Commit] = []
        visited: set[str] = set()
        stack = [branch_head]

        while stack:
            current = stack.pop()
            if current in visited:
                continue

            visited.add(current)
            commit = self.commits[current]
            result.append(commit)
            stack.extend(commit.parent_ids)

        return result

    def merge(self, source_branch: str, message: Optional[str] = None) -> str:
        """
        Merge source into the current branch.

        Fast-forward is performed when possible. Otherwise a simplified
        three-way merge is attempted. A conflicting file raises ValueError.
        """
        if source_branch not in self.branches:
            raise ValueError(f"Unknown branch: {source_branch}")

        target = self.head
        source = self.branches[source_branch].head

        if source is None:
            raise ValueError("Cannot merge an empty branch.")

        if target == source:
            return source

        if self.is_ancestor(target, source):
            self.branches[self.current_branch].head = source
            return source

        if self.is_ancestor(source, target):
            return target

        merge_base = self._find_merge_base(target, source)
        base_snapshot = self.snapshot(merge_base)
        target_snapshot = self.snapshot(target)
        source_snapshot = self.snapshot(source)

        merged = self._three_way_merge(
            base_snapshot,
            target_snapshot,
            source_snapshot,
        )

        commit_id = self._new_id()
        self.commits[commit_id] = Commit(
            commit_id=commit_id,
            author="merge-bot",
            message=message or f"Merge {source_branch} into {self.current_branch}",
            parent_ids=(target, source),
            files=tuple(sorted(merged.items())),
        )
        self.branches[self.current_branch].head = commit_id
        return commit_id

    def _find_merge_base(
        self,
        first: Optional[str],
        second: Optional[str],
    ) -> Optional[str]:
        """Find a simple common ancestor."""
        if first is None or second is None:
            return None

        first_ancestors = self.ancestors(first)
        candidates = self.ancestors(second) & first_ancestors

        if not candidates:
            return None

        # For this educational DAG, selecting the most recently created
        # candidate is adequate because IDs increase with creation order.
        return max(candidates, key=lambda value: int(value[1:]))

    @staticmethod
    def _three_way_merge(
        base: dict[str, str],
        target: dict[str, str],
        source: dict[str, str],
    ) -> dict[str, str]:
        """
        Merge independent changes.

        If both branches changed the same file differently from the base,
        the operation stops rather than silently choosing a side.
        """
        merged: dict[str, str] = {}
        all_paths = set(base) | set(target) | set(source)

        for path in all_paths:
            base_value = base.get(path)
            target_value = target.get(path)
            source_value = source.get(path)

            target_changed = target_value != base_value
            source_changed = source_value != base_value

            if target_changed and source_changed and target_value != source_value:
                raise ValueError(
                    f"Merge conflict in '{path}': both branches changed it."
                )

            if source_changed:
                chosen = source_value
            else:
                chosen = target_value

            if chosen is not None:
                merged[path] = chosen

        return merged

    def status(self) -> dict[str, object]:
        """Return a compact repository state representation."""
        return {
            "branch": self.current_branch,
            "head": self.head,
            "branches": {
                name: branch.head
                for name, branch in self.branches.items()
            },
        }


# ============================================================================
# 3. BEGINNER EXAMPLES
# ============================================================================

def beginner_branch_example() -> MiniGit:
    """
    Demonstrate the basic feature-branch workflow:

        main -> feature branch -> commit -> merge -> main
    """
    repo = MiniGit()

    repo.commit(
        "Atul",
        "Add project README",
        {"README.md": "# Collaboration Demo\n"},
    )

    repo.create_branch("feature/login")
    repo.checkout("feature/login")

    repo.commit(
        "Atul",
        "Add login validation",
        {"login.py": "def validate_login(user, password):\n    return bool(user and password)\n"},
    )

    repo.checkout("main")
    repo.merge("feature/login", "Merge login feature")

    return repo


def demonstrate_basic_concepts() -> None:
    print("\n=== BASIC GIT CONCEPTS ===")

    repo = beginner_branch_example()

    print("Current state:")
    print(json.dumps(repo.status(), indent=2))

    print("\nMain branch history:")
    for commit in repo.log("main"):
        print(f"{commit.commit_id}: {commit.message} [{commit.author}]")

    print(
        "\nA branch is a movable reference to a commit. "
        "Creating a branch does not copy the repository."
    )


# ============================================================================
# 4. FAST-FORWARD VS THREE-WAY MERGE
# ============================================================================

def demonstrate_merge_types() -> None:
    print("\n=== FAST-FORWARD AND THREE-WAY MERGES ===")

    repo = MiniGit()
    repo.commit("Alice", "Initial application", {"app.py": "print('v1')\n"})

    repo.create_branch("feature")
    repo.checkout("feature")
    repo.commit("Bob", "Add feature", {"feature.py": "feature()\n"})

    repo.checkout("main")
    fast_forward_result = repo.merge("feature")
    print("Fast-forward result:", fast_forward_result)
    print("Main HEAD:", repo.head)

    # Create divergence for a three-way merge.
    repo.commit("Alice", "Update documentation", {"README.md": "Version 2\n"})

    repo.create_branch("feature-2")
    repo.checkout("feature-2")
    repo.commit("Bob", "Add metrics", {"metrics.py": "print('metrics')\n"})

    repo.checkout("main")
    repo.commit("Alice", "Update configuration", {"config.ini": "debug=false\n"})

    merge_commit = repo.merge("feature-2")
    print("Three-way merge commit:", merge_commit)
    print("Merge parents:", repo.commits[merge_commit].parent_ids)


# ============================================================================
# 5. PULL REQUEST MODEL
# ============================================================================

class PullRequestService:
    """
    Small pull-request service.

    A real hosting provider stores much more information, but these rules
    demonstrate the core collaboration workflow.
    """

    def __init__(
        self,
        repository: MiniGit,
        required_approvals: int = 1,
        required_checks: Optional[Iterable[str]] = None,
    ) -> None:
        self.repository = repository
        self.required_approvals = required_approvals
        self.required_checks = set(required_checks or ())
        self.pull_requests: dict[int, PullRequest] = {}
        self._next_number = 1

    def open_pull_request(
        self,
        title: str,
        author: str,
        source_branch: str,
        target_branch: str,
        description: str,
    ) -> PullRequest:
        """Open a pull request after validating its branches."""
        if source_branch not in self.repository.branches:
            raise ValueError("Source branch does not exist.")

        if target_branch not in self.repository.branches:
            raise ValueError("Target branch does not exist.")

        if source_branch == target_branch:
            raise ValueError("Source and target branches must differ.")

        pull_request = PullRequest(
            number=self._next_number,
            title=title,
            author=author,
            source_branch=source_branch,
            target_branch=target_branch,
            description=description,
        )
        self.pull_requests[pull_request.number] = pull_request
        self._next_number += 1
        return pull_request

    def submit_review(
        self,
        number: int,
        reviewer: str,
        state: ReviewState,
        comments: Optional[list[str]] = None,
    ) -> None:
        """Add a review to an open pull request."""
        pull_request = self._get_open(number)

        if reviewer == pull_request.author:
            raise ValueError("Self-approval is disabled.")

        pull_request.reviews.append(
            Review(
                reviewer=reviewer,
                state=state,
                comments=comments or [],
            )
        )

    def set_check(
        self,
        number: int,
        check_name: str,
        state: CheckState,
    ) -> None:
        """Record a CI or policy check."""
        pull_request = self._get_open(number)
        pull_request.checks[check_name] = state

    def merge(self, number: int) -> str:
        """
        Merge only if review and check policies are satisfied.
        """
        pull_request = self._get_open(number)

        if pull_request.has_requested_changes():
            raise ValueError("Changes have been requested.")

        if pull_request.approvals() < self.required_approvals:
            raise ValueError("Required approvals have not been received.")

        missing_checks = self.required_checks - set(pull_request.checks)
        if missing_checks:
            raise ValueError(
                f"Missing required checks: {sorted(missing_checks)}"
            )

        failed_checks = [
            name
            for name in self.required_checks
            if pull_request.checks[name] != CheckState.PASS
        ]

        if failed_checks:
            raise ValueError(
                f"Required checks are not passing: {failed_checks}"
            )

        self.repository.checkout(pull_request.target_branch)
        merge_commit = self.repository.merge(
            pull_request.source_branch,
            message=f"Merge PR #{number}: {pull_request.title}",
        )
        pull_request.state = PullRequestState.MERGED
        return merge_commit

    def _get_open(self, number: int) -> PullRequest:
        if number not in self.pull_requests:
            raise KeyError(f"Unknown pull request #{number}")

        pull_request = self.pull_requests[number]

        if pull_request.state != PullRequestState.OPEN:
            raise ValueError("Pull request is no longer open.")

        return pull_request


def demonstrate_pull_request() -> None:
    print("\n=== PULL REQUEST WORKFLOW ===")

    repo = MiniGit()
    repo.commit("Atul", "Create service", {"service.py": "SERVICE = True\n"})
    repo.create_branch("feature/audit")
    repo.checkout("feature/audit")

    repo.commit(
        "Atul",
        "Add audit logging",
        {"audit.py": "def audit(event):\n    return event\n"},
    )

    service = PullRequestService(
        repo,
        required_approvals=1,
        required_checks={"tests", "lint"},
    )

    pull_request = service.open_pull_request(
        title="Add audit logging",
        author="Atul",
        source_branch="feature/audit",
        target_branch="main",
        description="Adds a small audit-event abstraction.",
    )

    print(f"Opened PR #{pull_request.number}: {pull_request.title}")

    service.submit_review(
        pull_request.number,
        reviewer="Reviewer",
        state=ReviewState.APPROVED,
        comments=["The change is focused and readable."],
    )

    service.set_check(pull_request.number, "tests", CheckState.PASS)
    service.set_check(pull_request.number, "lint", CheckState.PASS)

    merge_commit = service.merge(pull_request.number)

    print("PR state:", pull_request.state.value)
    print("Merge commit:", merge_commit)


# ============================================================================
# 6. CODE REVIEW PRINCIPLES
# ============================================================================

@dataclass
class CodeChange:
    """Represents a reviewable change in a source file."""
    path: str
    before: str
    after: str


def review_change(change: CodeChange) -> list[str]:
    """
    Perform simple static review checks.

    This does not replace human review. It demonstrates how automated checks
    can handle objective rules while reviewers concentrate on design,
    correctness, maintainability, and context.
    """
    findings: list[str] = []

    if not change.after.strip():
        findings.append("ERROR: resulting file is empty.")

    if "TODO: SECURITY" in change.after:
        findings.append("SECURITY: unresolved security marker found.")

    if "password =" in change.after and "hash_password" not in change.after:
        findings.append(
            "SECURITY: password assignment should be reviewed for secret handling."
        )

    before_lines = len(change.before.splitlines())
    after_lines = len(change.after.splitlines())

    if abs(after_lines - before_lines) > 200:
        findings.append(
            "REVIEW: unusually large change; consider splitting it."
        )

    return findings


def demonstrate_code_review() -> None:
    print("\n=== CODE REVIEW ===")

    change = CodeChange(
        path="auth.py",
        before="def login(user, password):\n    pass\n",
        after=(
            "def login(user, password):\n"
            "    password = password\n"
            "    # TODO: SECURITY\n"
            "    return True\n"
        ),
    )

    findings = review_change(change)

    for finding in findings:
        print(f"- {finding}")

    print(
        "\nAutomated checks are strongest for deterministic rules. "
        "Human reviewers are needed for intent, architecture, maintainability, "
        "domain behavior, and trade-offs."
    )


# ============================================================================
# 7. CONFLICTS AND RESOLUTION
# ============================================================================

def demonstrate_conflict() -> None:
    print("\n=== MERGE CONFLICT ===")

    repo = MiniGit()
    repo.commit(
        "Alice",
        "Initial configuration",
        {"config.txt": "timeout=30\n"},
    )

    repo.create_branch("feature-timeout")
    repo.checkout("feature-timeout")
    repo.commit(
        "Bob",
        "Set feature timeout",
        {"config.txt": "timeout=60\n"},
    )

    repo.checkout("main")
    repo.commit(
        "Alice",
        "Set production timeout",
        {"config.txt": "timeout=90\n"},
    )

    try:
        repo.merge("feature-timeout")
    except ValueError as error:
        print("Expected conflict:", error)

    print(
        "A conflict means Git cannot safely determine which concurrent "
        "change should win. Resolution requires human or policy-driven "
        "decision-making."
    )


# ============================================================================
# 8. REBASE CONCEPTS
# ============================================================================

def explain_rebase() -> None:
    print("\n=== REBASE ===")

    print(
        textwrap.dedent(
            """
            Merge:
                main:    A---B-------M
                          \\         /
                feature:  C---D-----

            Rebase:
                main:    A---B
                              \
                feature:       C'---D'

            Rebase recreates commits with different parent relationships.
            The resulting commit IDs are different because Git commits are
            content-addressed objects whose metadata includes parent history.

            Practical rule:
            - Rebasing local/unpublished work is commonly safe.
            - Rebasing commits already shared with others rewrites history.
            - Never treat rebase as a cosmetic operation.
            """
        ).strip()
    )


# ============================================================================
# 9. CHERRY-PICK, REVERT, AND RESET
# ============================================================================

def explain_history_operations() -> None:
    print("\n=== CHERRY-PICK, REVERT, RESET ===")

    definitions = {
        "cherry-pick": (
            "Copies the effect of an existing commit onto the current branch, "
            "creating a new commit."
        ),
        "revert": (
            "Creates a new commit that reverses the effect of an earlier "
            "commit. It preserves the public history."
        ),
        "reset": (
            "Moves a branch reference. Depending on the mode, it can also "
            "change the index and working tree. It is dangerous on shared "
            "history when used to rewrite published commits."
        ),
    }

    for operation, description in definitions.items():
        print(f"{operation}: {description}")


# ============================================================================
# 10. WORKFLOW MODELS
# ============================================================================

@dataclass(frozen=True)
class Workflow:
    """Describes a Git collaboration workflow."""
    name: str
    branch_model: str
    release_model: str
    typical_use: str


def workflow_catalog() -> list[Workflow]:
    return [
        Workflow(
            "Feature Branch",
            "main + short-lived feature branches",
            "Merge reviewed features into main",
            "General collaborative application development",
        ),
        Workflow(
            "GitHub Flow",
            "main + short-lived branches",
            "Deploy from main after review",
            "Continuous delivery",
        ),
        Workflow(
            "GitLab Flow",
            "feature branches plus environment/release conventions",
            "Promotion through defined environments",
            "Teams needing explicit deployment environments",
        ),
        Workflow(
            "Trunk-Based Development",
            "main/trunk with very short-lived branches or direct integration",
            "Frequent integration",
            "High integration frequency and strong automation",
        ),
        Workflow(
            "Git Flow",
            "main, develop, feature, release, and hotfix branches",
            "Dedicated release branches",
            "Products with structured release cycles",
        ),
    ]


def demonstrate_workflows() -> None:
    print("\n=== GIT WORKFLOWS ===")

    for workflow in workflow_catalog():
        print(f"\n{workflow.name}")
        print(f"  Branch model: {workflow.branch_model}")
        print(f"  Release model: {workflow.release_model}")
        print(f"  Typical use:  {workflow.typical_use}")


# ============================================================================
# 11. COMMIT QUALITY
# ============================================================================

def validate_commit_message(message: str) -> list[str]:
    """Apply simple, objective commit-message conventions."""
    findings: list[str] = []

    cleaned = message.strip()

    if not cleaned:
        findings.append("Commit message is empty.")
        return findings

    if len(cleaned) > 72:
        findings.append("Subject is longer than 72 characters.")

    if cleaned.endswith("."):
        findings.append("Subject should normally omit the trailing period.")

    first_word = cleaned.split()[0]
    if first_word and first_word[0].islower():
        findings.append("Start the subject with a capitalized word.")

    return findings


def demonstrate_commit_quality() -> None:
    print("\n=== COMMIT QUALITY ===")

    examples = [
        "add login",
        "Add login validation",
        "Add login validation.",
        "",
    ]

    for message in examples:
        print(f"\nMessage: {message!r}")
        findings = validate_commit_message(message)
        if findings:
            for finding in findings:
                print(" -", finding)
        else:
            print(" - Accepted by the example policy.")


# ============================================================================
# 12. CI / PROTECTION POLICY
# ============================================================================

@dataclass
class BranchProtection:
    """Simplified protected-branch policy."""
    require_pull_request: bool = True
    required_approvals: int = 1
    require_passing_checks: bool = True
    allow_force_push: bool = False
    allow_deletion: bool = False


def can_direct_push(
    policy: BranchProtection,
    actor: str,
) -> tuple[bool, str]:
    """
    Evaluate a direct push against a protected branch policy.

    The actor argument exists to make the example resemble a real authorization
    check, even though this simplified policy does not distinguish roles.
    """
    if policy.require_pull_request:
        return (
            False,
            f"Direct push denied for {actor}: pull request required.",
        )

    return True, "Direct push allowed."


def demonstrate_branch_protection() -> None:
    print("\n=== BRANCH PROTECTION ===")

    policy = BranchProtection()

    allowed, reason = can_direct_push(policy, "developer")
    print("Allowed:", allowed)
    print("Reason:", reason)

    print(
        "Typical protected-branch controls include required reviews, "
        "required CI checks, restricted force pushes, and restricted deletion."
    )


# ============================================================================
# 13. DIFF ANALYSIS
# ============================================================================

def calculate_line_diff(before: str, after: str) -> dict[str, int]:
    """Calculate simple added, removed, and unchanged line counts."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()

    common = min(len(before_lines), len(after_lines))

    return {
        "before": len(before_lines),
        "after": len(after_lines),
        "added": max(0, len(after_lines) - common),
        "removed": max(0, len(before_lines) - common),
        "unchanged_position_count": sum(
            a == b
            for a, b in zip(before_lines, after_lines)
        ),
    }


def demonstrate_diff() -> None:
    print("\n=== CHANGE SIZE ===")

    before = "line one\nline two\nline three\n"
    after = "line one\nline two changed\nline three\nline four\n"

    print(json.dumps(calculate_line_diff(before, after), indent=2))

    print(
        "A diff describes changes rather than merely showing complete files. "
        "Small focused diffs generally make review easier because the reviewer "
        "can reason about a narrower change."
    )


# ============================================================================
# 14. COLLABORATION AUDIT LOG
# ============================================================================

@dataclass(frozen=True)
class AuditEvent:
    timestamp: float
    actor: str
    action: str
    object_id: str
    details: str


class AuditLog:
    """Append-only educational audit log."""

    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def record(
        self,
        actor: str,
        action: str,
        object_id: str,
        details: str,
    ) -> None:
        self.events.append(
            AuditEvent(
                timestamp=time.time(),
                actor=actor,
                action=action,
                object_id=object_id,
                details=details,
            )
        )

    def export(self) -> str:
        return json.dumps(
            [
                {
                    "timestamp": event.timestamp,
                    "actor": event.actor,
                    "action": event.action,
                    "object_id": event.object_id,
                    "details": event.details,
                }
                for event in self.events
            ],
            indent=2,
        )


def demonstrate_audit_log() -> None:
    print("\n=== COLLABORATION AUDIT ===")

    audit = AuditLog()
    audit.record("Atul", "open", "PR-1", "Feature branch submitted.")
    audit.record("Reviewer", "review", "PR-1", "Approved after CI passed.")
    audit.record("Maintainer", "merge", "PR-1", "Merged into main.")

    print(audit.export())


# ============================================================================
# 15. SECURITY CONSIDERATIONS
# ============================================================================

def security_review_rules() -> dict[str, str]:
    return {
        "secrets": (
            "Never commit API keys, passwords, private keys, or production "
            "credentials. Use secret-management mechanisms."
        ),
        "dependencies": (
            "Review dependency changes and lock versions where appropriate."
        ),
        "permissions": (
            "Use least privilege for repository roles, tokens, and automation."
        ),
        "pull_requests": (
            "Treat external pull-request code as untrusted until checks and "
            "review are complete."
        ),
        "CI": (
            "Avoid exposing privileged secrets to untrusted code execution."
        ),
        "history": (
            "Remember that removing a secret from the latest commit does not "
            "necessarily remove it from repository history."
        ),
        "force_push": (
            "Restrict force pushes on shared branches to protect collaboration "
            "and auditability."
        ),
    }


def demonstrate_security() -> None:
    print("\n=== SECURITY ===")

    for topic, rule in security_review_rules().items():
        print(f"{topic}: {rule}")


# ============================================================================
# 16. PERFORMANCE AND SCALE
# ============================================================================

def explain_performance() -> None:
    print("\n=== PERFORMANCE AND SCALE ===")

    considerations = [
        (
            "Repository size",
            "Large binary files increase clone, fetch, and storage costs. "
            "Git LFS or external artifact storage may be appropriate."
        ),
        (
            "History depth",
            "Long histories increase the amount of data clients may need to "
            "process. Shallow clones can reduce initial transfer when appropriate."
        ),
        (
            "CI duration",
            "Slow checks increase pull-request feedback time. Parallel jobs, "
            "caching, and selective testing can reduce latency."
        ),
        (
            "Change size",
            "Large pull requests increase review and integration complexity."
        ),
        (
            "Branch lifetime",
            "Long-lived branches increase divergence and conflict risk."
        ),
    ]

    for subject, explanation in considerations:
        print(f"{subject}: {explanation}")


# ============================================================================
# 17. PRACTICAL COLLABORATION SIMULATION
# ============================================================================

class CollaborationSimulator:
    """
    Simulates a complete development cycle.

    Flow:
        issue -> branch -> commits -> pull request -> review -> CI -> merge
    """

    def __init__(self) -> None:
        self.repository = MiniGit()
        self.audit = AuditLog()
        self.pr_service = PullRequestService(
            self.repository,
            required_approvals=2,
            required_checks={"unit-tests", "lint", "security"},
        )

    def initialize(self) -> None:
        self.repository.commit(
            "maintainer",
            "Initialize application",
            {
                "README.md": "# Collaboration Application\n",
                "app.py": "def main():\n    return 'ready'\n",
            },
        )

    def develop_feature(self) -> PullRequest:
        self.repository.create_branch("feature/user-profile")
        self.repository.checkout("feature/user-profile")

        self.repository.commit(
            "developer",
            "Add profile model",
            {
                "profile.py": (
                    "class Profile:\n"
                    "    def __init__(self, username):\n"
                    "        self.username = username\n"
                )
            },
        )

        self.audit.record(
            "developer",
            "commit",
            self.repository.head or "unknown",
            "Added profile model.",
        )

        self.repository.commit(
            "developer",
            "Add profile validation",
            {
                "profile.py": (
                    "class Profile:\n"
                    "    def __init__(self, username):\n"
                    "        if not username or not username.strip():\n"
                    "            raise ValueError('username required')\n"
                    "        self.username = username.strip()\n"
                )
            },
        )

        self.audit.record(
            "developer",
            "commit",
            self.repository.head or "unknown",
            "Added validation.",
        )

        pull_request = self.pr_service.open_pull_request(
            title="Add user profile validation",
            author="developer",
            source_branch="feature/user-profile",
            target_branch="main",
            description=(
                "Adds a small profile model and validation for usernames."
            ),
        )

        self.audit.record(
            "developer",
            "open",
            f"PR-{pull_request.number}",
            "Submitted feature for review.",
        )

        return pull_request

    def review_and_merge(self, pull_request: PullRequest) -> str:
        self.pr_service.submit_review(
            pull_request.number,
            "reviewer-a",
            ReviewState.APPROVED,
            ["Validation behavior is explicit."],
        )

        self.pr_service.submit_review(
            pull_request.number,
            "reviewer-b",
            ReviewState.APPROVED,
            ["The change is focused."],
        )

        for check in ("unit-tests", "lint", "security"):
            self.pr_service.set_check(
                pull_request.number,
                check,
                CheckState.PASS,
            )

        self.audit.record(
            "reviewer-a",
            "approve",
            f"PR-{pull_request.number}",
            "Approved.",
        )

        merge_commit = self.pr_service.merge(pull_request.number)

        self.audit.record(
            "maintainer",
            "merge",
            f"PR-{pull_request.number}",
            merge_commit,
        )

        return merge_commit


def demonstrate_complete_workflow() -> None:
    print("\n=== COMPLETE COLLABORATION SIMULATION ===")

    simulator = CollaborationSimulator()
    simulator.initialize()

    pull_request = simulator.develop_feature()

    print(
        f"PR #{pull_request.number} opened: "
        f"{pull_request.title}"
    )

    merge_commit = simulator.review_and_merge(pull_request)

    print("Merged with commit:", merge_commit)
    print("\nAudit trail:")
    print(simulator.audit.export())


# ============================================================================
# 18. TESTING
# ============================================================================

class TestMiniGit(unittest.TestCase):
    """Tests for important educational Git-model behavior."""

    def test_fast_forward_merge(self) -> None:
        repo = MiniGit()
        initial = repo.commit("Alice", "Initial", {"a.txt": "A"})
        repo.create_branch("feature")
        repo.checkout("feature")
        feature = repo.commit("Bob", "Feature", {"b.txt": "B"})
        repo.checkout("main")

        result = repo.merge("feature")

        self.assertEqual(result, feature)
        self.assertEqual(repo.head, feature)
        self.assertEqual(repo.branches["main"].head, feature)
        self.assertNotEqual(initial, feature)

    def test_three_way_merge(self) -> None:
        repo = MiniGit()
        repo.commit("Alice", "Initial", {"a.txt": "A"})
        repo.create_branch("feature")

        repo.checkout("feature")
        repo.commit("Bob", "Feature", {"b.txt": "B"})

        repo.checkout("main")
        repo.commit("Alice", "Main change", {"c.txt": "C"})

        merge_commit = repo.merge("feature")

        self.assertEqual(
            repo.commits[merge_commit].parent_ids,
            (
                repo.commits[merge_commit].parent_ids[0],
                repo.commits[merge_commit].parent_ids[1],
            ),
        )
        self.assertEqual(len(repo.commits[merge_commit].parent_ids), 2)

    def test_conflict_detection(self) -> None:
        repo = MiniGit()
        repo.commit("Alice", "Initial", {"config": "A"})
        repo.create_branch("feature")

        repo.checkout("feature")
        repo.commit("Bob", "Feature change", {"config": "B"})

        repo.checkout("main")
        repo.commit("Alice", "Main change", {"config": "C"})

        with self.assertRaises(ValueError):
            repo.merge("feature")

    def test_pull_request_policy(self) -> None:
        repo = MiniGit()
        repo.commit("maintainer", "Initial", {"app.py": "x = 1"})
        repo.create_branch("feature")
        repo.checkout("feature")
        repo.commit("developer", "Feature", {"app.py": "x = 2"})

        service = PullRequestService(
            repo,
            required_approvals=1,
            required_checks={"tests"},
        )

        pull_request = service.open_pull_request(
            "Feature",
            "developer",
            "feature",
            "main",
            "Test feature",
        )

        with self.assertRaises(ValueError):
            service.merge(pull_request.number)

        service.submit_review(
            pull_request.number,
            "reviewer",
            ReviewState.APPROVED,
        )

        service.set_check(
            pull_request.number,
            "tests",
            CheckState.PASS,
        )

        service.merge(pull_request.number)
        self.assertEqual(
            pull_request.state,
            PullRequestState.MERGED,
        )


# ============================================================================
# 19. REAL GIT INSPECTION
# ============================================================================

def run_git_command(
    arguments: list[str],
    cwd: Path,
) -> tuple[int, str, str]:
    """
    Execute a Git command safely.

    This function does not use shell=True, avoiding shell interpolation and
    reducing command-injection risk.
    """
    process = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )

    return process.returncode, process.stdout, process.stderr


def demonstrate_real_git_if_available() -> None:
    """
    Create a temporary repository and inspect actual Git behavior.

    The repository is temporary and deleted when the context exits.
    """
    print("\n=== REAL GIT INSPECTION ===")

    git_path = shutil.which("git")

    if git_path is None:
        print("Git executable not found. Skipping real-Git demonstration.")
        return

    with TemporaryDirectory(prefix="git-collaboration-") as temporary_directory:
        repository_path = Path(temporary_directory)

        commands = [
            (["init", "-b", "main"], "Initialize repository"),
            (
                ["config", "user.name", "Educational User"],
                "Configure author name",
            ),
            (
                ["config", "user.email", "educational@example.invalid"],
                "Configure author email",
            ),
        ]

        for command, description in commands:
            return_code, _, stderr = run_git_command(
                command,
                repository_path,
            )

            if return_code != 0:
                print(f"{description} failed: {stderr.strip()}")
                return

        (repository_path / "README.md").write_text(
            "# Real Git Demonstration\n",
            encoding="utf-8",
        )

        return_code, _, stderr = run_git_command(
            ["add", "README.md"],
            repository_path,
        )

        if return_code != 0:
            print("git add failed:", stderr.strip())
            return

        return_code, _, stderr = run_git_command(
            ["commit", "-m", "Initial commit"],
            repository_path,
        )

        if return_code != 0:
            print("git commit failed:", stderr.strip())
            return

        return_code, stdout, stderr = run_git_command(
            ["log", "--oneline", "--decorate", "-1"],
            repository_path,
        )

        if return_code == 0:
            print("Actual Git log:")
            print(stdout.strip())
        else:
            print("git log failed:", stderr.strip())

        return_code, stdout, _ = run_git_command(
            ["status", "--short", "--branch"],
            repository_path,
        )

        if return_code == 0:
            print("\nActual Git status:")
            print(stdout.strip())


# ============================================================================
# 20. EDGE CASES
# ============================================================================

def demonstrate_edge_cases() -> None:
    print("\n=== EDGE CASES ===")

    cases = [
        (
            "Empty commit message",
            lambda: validate_commit_message(""),
        ),
        (
            "Unknown branch",
            lambda: MiniGit().checkout("does-not-exist"),
        ),
        (
            "Self approval",
            lambda: _self_approval_case(),
        ),
    ]

    for name, operation in cases:
        try:
            result = operation()
            print(f"{name}: result={result}")
        except Exception as error:
            print(f"{name}: handled -> {type(error).__name__}: {error}")


def _self_approval_case() -> None:
    repo = MiniGit()
    repo.commit("Alice", "Initial", {"a": "A"})
    repo.create_branch("feature")
    repo.checkout("feature")
    repo.commit("Alice", "Feature", {"b": "B"})

    service = PullRequestService(repo)
    pull_request = service.open_pull_request(
        "Feature",
        "Alice",
        "feature",
        "main",
        "Self-review test.",
    )

    service.submit_review(
        pull_request.number,
        "Alice",
        ReviewState.APPROVED,
    )


# ============================================================================
# 21. STUDY CHECKLIST
# ============================================================================

def study_checklist() -> list[str]:
    return [
        "Explain working tree, index, local repository, and remote repository.",
        "Explain commit identity and parent relationships.",
        "Create and switch branches.",
        "Describe fast-forward and three-way merges.",
        "Explain why merge conflicts occur.",
        "Explain pull requests as a collaboration and policy layer.",
        "Distinguish comments, approvals, and change requests.",
        "Explain the role of CI in pull-request validation.",
        "Compare merge and rebase.",
        "Distinguish revert, reset, and cherry-pick.",
        "Explain why force-pushing shared history can disrupt collaborators.",
        "Describe protected-branch policies.",
        "Identify secrets and untrusted-code risks in CI.",
        "Explain why focused pull requests are easier to review.",
        "Describe how workflow choice affects release management.",
    ]


def print_study_checklist() -> None:
    print("\n=== STUDY CHECKLIST ===")

    for index, item in enumerate(study_checklist(), start=1):
        print(f"{index:02d}. {item}")


# ============================================================================
# 22. MAIN PROGRAM
# ============================================================================

def run_tests() -> None:
    """Run the embedded unit tests without requiring an external test runner."""
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMiniGit)
    result = unittest.TextTestRunner(verbosity=1).run(suite)

    if not result.wasSuccessful():
        raise SystemExit("Embedded tests failed.")


def main() -> None:
    print("=" * 78)
    print("GIT COLLABORATION: PULL REQUESTS, CODE REVIEW, AND GIT WORKFLOWS")
    print("=" * 78)

    demonstrate_basic_concepts()
    demonstrate_merge_types()
    demonstrate_pull_request()
    demonstrate_code_review()
    demonstrate_conflict()
    explain_rebase()
    explain_history_operations()
    demonstrate_workflows()
    demonstrate_commit_quality()
    demonstrate_branch_protection()
    demonstrate_diff()
    demonstrate_audit_log()
    demonstrate_security()
    explain_performance()
    demonstrate_complete_workflow()
    demonstrate_edge_cases()

    print("\n=== RUNNING EMBEDDED TESTS ===")
    run_tests()

    demonstrate_real_git_if_available()
    print_study_checklist()

    print("\nProgram completed successfully.")


if __name__ == "__main__":
    main()
