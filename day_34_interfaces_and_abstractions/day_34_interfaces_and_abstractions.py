"""
Interfaces & Abstractions
Contracts, dependency boundaries

A self-contained progression from simple contracts to a production-oriented
service architecture.

The examples deliberately separate:
- interfaces: what a component promises to provide
- abstractions: stable concepts that hide implementation details
- dependency boundaries: where one component is allowed to depend on another
- contracts: explicit rules that inputs, outputs, and implementations must obey

No third-party packages are required.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol
import json
import re
import unittest


# ---------------------------------------------------------------------------
# Fundamental abstraction: a notification contract
# ---------------------------------------------------------------------------

class NotificationChannel(ABC):
    """
    Abstract interface for delivering notifications.

    Callers depend on this contract rather than on SMTP, an HTTP API,
    a message broker, or any other concrete transport.
    """

    @abstractmethod
    def send(self, recipient: str, subject: str, body: str) -> str:
        """Return a provider-independent delivery identifier."""
        raise NotImplementedError


class ConsoleNotification(NotificationChannel):
    """Concrete implementation useful for local development."""

    def send(self, recipient: str, subject: str, body: str) -> str:
        if not recipient.strip():
            raise ValueError("recipient cannot be empty")
        if not subject.strip():
            raise ValueError("subject cannot be empty")
        print(f"[CONSOLE] to={recipient} subject={subject}")
        print(body)
        return "console-delivery"


class InMemoryNotification(NotificationChannel):
    """Test implementation that records calls without external side effects."""

    def __init__(self) -> None:
        self.messages: list[dict[str, str]] = []

    def send(self, recipient: str, subject: str, body: str) -> str:
        if not recipient.strip():
            raise ValueError("recipient cannot be empty")
        message = {
            "recipient": recipient,
            "subject": subject,
            "body": body,
        }
        self.messages.append(message)
        return f"memory-{len(self.messages)}"


def demonstrate_basic_interface() -> None:
    print("\n=== Basic interface boundary ===")

    channels: list[NotificationChannel] = [
        ConsoleNotification(),
        InMemoryNotification(),
    ]

    for channel in channels:
        delivery_id = channel.send(
            "developer@example.com",
            "Build completed",
            "The protected release branch passed its validation pipeline.",
        )
        print("delivery:", delivery_id)


# ---------------------------------------------------------------------------
# Structural abstraction with Protocol
# ---------------------------------------------------------------------------

class Clock(Protocol):
    """Structural contract: an object only needs a now() method."""

    def now(self) -> datetime:
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """Deterministic clock for repeatable tests."""

    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor: str
    timestamp: datetime
    details: dict[str, str]


class AuditSink(Protocol):
    """Boundary contract for audit-event persistence."""

    def write(self, event: AuditEvent) -> None:
        ...


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    def write(self, event: AuditEvent) -> None:
        self.events.append(event)


class AuditService:
    """
    Depends on abstractions rather than infrastructure.

    It does not know whether events are stored in memory, PostgreSQL,
    a file, or a remote event system.
    """

    def __init__(self, clock: Clock, sink: AuditSink) -> None:
        self.clock = clock
        self.sink = sink

    def record(self, event_type: str, actor: str, details: dict[str, str]) -> AuditEvent:
        if not event_type.strip():
            raise ValueError("event_type cannot be empty")
        if not actor.strip():
            raise ValueError("actor cannot be empty")

        event = AuditEvent(
            event_type=event_type,
            actor=actor,
            timestamp=self.clock.now(),
            details=dict(details),
        )
        self.sink.write(event)
        return event


# ---------------------------------------------------------------------------
# Domain contract: repository access
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Repository:
    name: str
    default_branch: str
    archived: bool = False


class RepositoryRepository(Protocol):
    """
    Domain-facing repository contract.

    The awkward but explicit name illustrates an important boundary:
    domain code should not depend directly on an ORM or database client.
    """

    def find(self, name: str) -> Repository | None:
        ...

    def save(self, repository: Repository) -> None:
        ...


class InMemoryRepositoryStore:
    def __init__(self) -> None:
        self._items: dict[str, Repository] = {}

    def find(self, name: str) -> Repository | None:
        return self._items.get(name)

    def save(self, repository: Repository) -> None:
        if not repository.name.strip():
            raise ValueError("repository name cannot be empty")
        if not repository.default_branch.strip():
            raise ValueError("default branch cannot be empty")
        self._items[repository.name] = repository


class RepositoryService:
    """
    Application service.

    Notice that this class has no SQL, HTTP, filesystem, or vendor-specific
    dependency. Those concerns terminate at the repository contract.
    """

    def __init__(self, store: RepositoryRepository) -> None:
        self.store = store

    def register(self, name: str, default_branch: str = "main") -> Repository:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
            raise ValueError("repository name contains unsupported characters")

        if self.store.find(name) is not None:
            raise ValueError("repository already exists")

        repository = Repository(name=name, default_branch=default_branch)
        self.store.save(repository)
        return repository


# ---------------------------------------------------------------------------
# Explicit business contract for dependency boundaries
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PullRequest:
    number: int
    repository: str
    source_branch: str
    target_branch: str
    author: str
    changed_files: tuple[str, ...]
    status_checks_passed: bool


@dataclass(frozen=True)
class MergePolicy:
    protected_branch: str
    minimum_approvals: int
    require_tests: bool
    require_linear_history: bool


@dataclass(frozen=True)
class Review:
    reviewer: str
    approved: bool
    comment: str


class ReviewProvider(Protocol):
    def reviews_for(self, repository: str, pull_request_number: int) -> list[Review]:
        ...


class StaticReviewProvider:
    def __init__(self, reviews: Iterable[Review]) -> None:
        self._reviews = list(reviews)

    def reviews_for(self, repository: str, pull_request_number: int) -> list[Review]:
        return list(self._reviews)


class MergeEligibility:
    """
    Application-level policy object.

    It consumes Pull Request data and review data through contracts.
    It does not know how GitHub, GitLab, or another platform stores reviews.
    """

    def __init__(self, review_provider: ReviewProvider) -> None:
        self.review_provider = review_provider

    def evaluate(
        self,
        pull_request: PullRequest,
        policy: MergePolicy,
    ) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if pull_request.target_branch != policy.protected_branch:
            reasons.append("pull request does not target the protected branch")

        if policy.require_tests and not pull_request.status_checks_passed:
            reasons.append("required status checks have not passed")

        reviews = self.review_provider.reviews_for(
            pull_request.repository,
            pull_request.number,
        )

        unique_approvers = {
            review.reviewer
            for review in reviews
            if review.approved and review.reviewer != pull_request.author
        }

        if len(unique_approvers) < policy.minimum_approvals:
            reasons.append(
                f"requires {policy.minimum_approvals} eligible approval(s); "
                f"found {len(unique_approvers)}"
            )

        return not reasons, reasons


# ---------------------------------------------------------------------------
# Dependency inversion with a complete application workflow
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MergeDecision:
    allowed: bool
    reasons: tuple[str, ...]
    evaluated_at: datetime


class MergeService:
    """
    The service owns orchestration while collaborators own infrastructure.

    Dependencies are injected, making the boundary explicit and testable.
    """

    def __init__(
        self,
        eligibility: MergeEligibility,
        clock: Clock,
        audit: AuditSink,
    ) -> None:
        self.eligibility = eligibility
        self.clock = clock
        self.audit = audit

    def evaluate(
        self,
        pull_request: PullRequest,
        policy: MergePolicy,
        actor: str,
    ) -> MergeDecision:
        allowed, reasons = self.eligibility.evaluate(pull_request, policy)

        decision = MergeDecision(
            allowed=allowed,
            reasons=tuple(reasons),
            evaluated_at=self.clock.now(),
        )

        self.audit.write(
            AuditEvent(
                event_type="merge_eligibility_evaluated",
                actor=actor,
                timestamp=decision.evaluated_at,
                details={
                    "repository": pull_request.repository,
                    "pull_request": str(pull_request.number),
                    "allowed": str(decision.allowed),
                },
            )
        )

        return decision


def demonstrate_dependency_boundaries() -> None:
    print("\n=== Dependency boundary workflow ===")

    reviews = [
        Review("reviewer-a", True, "Looks correct."),
        Review("reviewer-b", True, "Tests cover the change."),
        Review("reviewer-a", True, "Approved again."),
    ]

    review_provider = StaticReviewProvider(reviews)
    eligibility = MergeEligibility(review_provider)

    audit = MemoryAuditSink()
    clock = FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc))

    service = MergeService(
        eligibility=eligibility,
        clock=clock,
        audit=audit,
    )

    pull_request = PullRequest(
        number=42,
        repository="release-control",
        source_branch="feature/approval-policy",
        target_branch="main",
        author="developer",
        changed_files=("policy.py", "tests/test_policy.py"),
        status_checks_passed=True,
    )

    policy = MergePolicy(
        protected_branch="main",
        minimum_approvals=2,
        require_tests=True,
        require_linear_history=True,
    )

    decision = service.evaluate(
        pull_request=pull_request,
        policy=policy,
        actor="merge-bot",
    )

    print("merge allowed:", decision.allowed)
    print("reasons:", decision.reasons)
    print("audit events:", len(audit.events))


# ---------------------------------------------------------------------------
# Contract validation at the boundary
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CreateRepositoryRequest:
    name: str
    default_branch: str


def validate_create_repository_request(
    request: CreateRepositoryRequest,
) -> None:
    """
    Boundary validation prevents invalid external data from entering
    the domain model.
    """
    if not request.name:
        raise ValueError("repository name is required")

    if len(request.name) > 100:
        raise ValueError("repository name is too long")

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", request.name):
        raise ValueError("repository name contains invalid characters")

    if request.default_branch not in {"main", "trunk"}:
        raise ValueError("unsupported default branch")


def demonstrate_validation_boundary() -> None:
    print("\n=== Boundary validation ===")

    valid = CreateRepositoryRequest("payment-gateway", "main")
    validate_create_repository_request(valid)
    print("valid request accepted:", valid)

    invalid = CreateRepositoryRequest("payment gateway", "main")
    try:
        validate_create_repository_request(invalid)
    except ValueError as exc:
        print("invalid request rejected:", exc)


# ---------------------------------------------------------------------------
# Serialization boundary
# ---------------------------------------------------------------------------

def decision_to_json(decision: MergeDecision) -> str:
    """
    Converts a domain result into a transport representation.

    The domain object itself does not need to know JSON syntax.
    """
    payload = {
        "allowed": decision.allowed,
        "reasons": list(decision.reasons),
        "evaluated_at": decision.evaluated_at.isoformat(),
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------------------
# Testing the contracts
# ---------------------------------------------------------------------------

class InterfaceBoundaryTests(unittest.TestCase):
    def test_notification_contract(self) -> None:
        channel = InMemoryNotification()
        result = channel.send("a@example.com", "Test", "Hello")
        self.assertEqual(result, "memory-1")
        self.assertEqual(len(channel.messages), 1)

    def test_repository_service_does_not_require_database(self) -> None:
        store = InMemoryRepositoryStore()
        service = RepositoryService(store)

        repository = service.register("orders")
        self.assertEqual(repository.default_branch, "main")

        with self.assertRaises(ValueError):
            service.register("orders")

    def test_merge_policy_rejects_missing_approval(self) -> None:
        provider = StaticReviewProvider(
            [Review("reviewer-a", True, "Approved")]
        )
        evaluator = MergeEligibility(provider)

        pull_request = PullRequest(
            number=7,
            repository="orders",
            source_branch="feature/payment",
            target_branch="main",
            author="developer",
            changed_files=("payment.py",),
            status_checks_passed=True,
        )

        policy = MergePolicy(
            protected_branch="main",
            minimum_approvals=2,
            require_tests=True,
            require_linear_history=True,
        )

        allowed, reasons = evaluator.evaluate(pull_request, policy)

        self.assertFalse(allowed)
        self.assertTrue(any("approval" in reason for reason in reasons))

    def test_author_approval_is_not_counted(self) -> None:
        provider = StaticReviewProvider(
            [Review("developer", True, "Self-approved")]
        )
        evaluator = MergeEligibility(provider)

        pull_request = PullRequest(
            number=8,
            repository="orders",
            source_branch="feature/payment",
            target_branch="main",
            author="developer",
            changed_files=("payment.py",),
            status_checks_passed=True,
        )

        policy = MergePolicy(
            protected_branch="main",
            minimum_approvals=1,
            require_tests=True,
            require_linear_history=False,
        )

        allowed, _ = evaluator.evaluate(pull_request, policy)
        self.assertFalse(allowed)


def run_tests() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        InterfaceBoundaryTests
    )
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


def main() -> None:
    print("INTERFACES AND ABSTRACTIONS")
    print("===========================")

    demonstrate_basic_interface()

    audit = MemoryAuditSink()
    audit_service = AuditService(
        clock=FixedClock(datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)),
        sink=audit,
    )
    event = audit_service.record(
        "repository_registered",
        "system",
        {"repository": "release-control"},
    )
    print("\nrecorded audit event:", event.event_type)

    demonstrate_dependency_boundaries()
    demonstrate_validation_boundary()

    print("\n=== Repository service ===")
    store = InMemoryRepositoryStore()
    repository_service = RepositoryService(store)
    repository = repository_service.register("release-control")
    print(repository)

    print("\n=== JSON transport boundary ===")
    provider = StaticReviewProvider(
        [
            Review("security-reviewer", True, "Security boundary reviewed."),
            Review("platform-reviewer", True, "Infrastructure contract reviewed."),
        ]
    )
    evaluator = MergeEligibility(provider)
    audit_sink = MemoryAuditSink()

    merge_service = MergeService(
        eligibility=evaluator,
        clock=SystemClock(),
        audit=audit_sink,
    )

    pull_request = PullRequest(
        number=101,
        repository="release-control",
        source_branch="feature/contracts",
        target_branch="main",
        author="atul",
        changed_files=("contracts.py", "tests/test_contracts.py"),
        status_checks_passed=True,
    )

    policy = MergePolicy(
        protected_branch="main",
        minimum_approvals=2,
        require_tests=True,
        require_linear_history=True,
    )

    decision = merge_service.evaluate(
        pull_request,
        policy,
        actor="merge-controller",
    )

    print(decision_to_json(decision))

    print("\n=== Contract tests ===")
    run_tests()


if __name__ == "__main__":
    main()
