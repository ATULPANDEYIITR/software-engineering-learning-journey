"""
Design Patterns II: Strategy, Observer, Adapter

A self-contained Python learning program that demonstrates three behavioral/
structural design patterns through a repository governance scenario.

Scenario:
A software delivery platform evaluates Pull Requests using interchangeable
merge strategies, notifies interested components when repository events occur,
and adapts external status-check providers to the platform's internal API.

Patterns:
- Strategy: interchangeable merge-eligibility policies.
- Observer: event subscribers reacting to Pull Request lifecycle events.
- Adapter: translating an external CI provider into the internal status-check
  interface expected by the governance engine.

Run:
    python design_patterns_ii.py
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Iterable, Protocol


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

class PullRequestState(Enum):
    DRAFT = "draft"
    OPEN = "open"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    MERGED = "merged"
    CLOSED = "closed"


class CheckStatus(Enum):
    PASSING = "passing"
    FAILING = "failing"
    PENDING = "pending"


class ReviewDecision(Enum):
    APPROVE = "approve"
    REQUEST_CHANGES = "request_changes"
    COMMENT = "comment"


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str


@dataclass
class Review:
    reviewer: str
    decision: ReviewDecision
    commit_sha: str
    comment: str = ""


@dataclass
class StatusCheck:
    name: str
    status: CheckStatus
    commit_sha: str


@dataclass
class PullRequest:
    number: int
    title: str
    source_branch: str
    target_branch: str
    author: str
    commits: list[Commit]
    state: PullRequestState = PullRequestState.OPEN
    reviews: list[Review] = field(default_factory=list)
    checks: list[StatusCheck] = field(default_factory=list)
    mergeable: bool = True

    @property
    def head_sha(self) -> str:
        if not self.commits:
            raise ValueError("A Pull Request must contain at least one commit.")
        return self.commits[-1].sha

    def add_review(self, review: Review) -> None:
        if self.state in {PullRequestState.MERGED, PullRequestState.CLOSED}:
            raise ValueError("Cannot review a closed or merged Pull Request.")
        self.reviews.append(review)

    def add_check(self, check: StatusCheck) -> None:
        self.checks.append(check)


# ---------------------------------------------------------------------------
# Strategy pattern
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MergeDecision:
    allowed: bool
    reasons: tuple[str, ...]


class MergeStrategy(ABC):
    """Strategy interface for interchangeable merge policies."""

    @abstractmethod
    def evaluate(self, pull_request: PullRequest) -> MergeDecision:
        raise NotImplementedError


class FastForwardStrategy(MergeStrategy):
    """
    A simplified fast-forward policy.

    This strategy requires:
    - an open Pull Request,
    - no requested changes,
    - all checks passing,
    - a cleanly mergeable branch.

    It intentionally does not require an approval because that is a policy
    decision that can be supplied by a different strategy.
    """

    def evaluate(self, pull_request: PullRequest) -> MergeDecision:
        reasons: list[str] = []

        if pull_request.state != PullRequestState.OPEN:
            reasons.append("Pull Request is not open.")

        if any(
            review.decision == ReviewDecision.REQUEST_CHANGES
            and review.commit_sha == pull_request.head_sha
            for review in pull_request.reviews
        ):
            reasons.append("The current commit has a change request.")

        current_checks = [
            check
            for check in pull_request.checks
            if check.commit_sha == pull_request.head_sha
        ]

        if not current_checks:
            reasons.append("No status checks exist for the current commit.")
        elif any(check.status != CheckStatus.PASSING for check in current_checks):
            reasons.append("At least one current status check is not passing.")

        if not pull_request.mergeable:
            reasons.append("The Pull Request has a merge conflict.")

        return MergeDecision(not reasons, tuple(reasons))


class ProtectedBranchStrategy(MergeStrategy):
    """
    A stronger strategy representing a protected production branch.

    Requirements:
    - Pull Request must be open.
    - At least two distinct eligible reviewers must approve the current head.
    - No current-head change request may remain.
    - Every known check for the current head must pass.
    - The Pull Request must be conflict-free.
    """

    def __init__(self, eligible_reviewers: Iterable[str], required_approvals: int = 2):
        self.eligible_reviewers = frozenset(eligible_reviewers)
        self.required_approvals = required_approvals

    def evaluate(self, pull_request: PullRequest) -> MergeDecision:
        reasons: list[str] = []

        if pull_request.state != PullRequestState.OPEN:
            reasons.append("Pull Request is not open.")

        approvals = {
            review.reviewer
            for review in pull_request.reviews
            if review.commit_sha == pull_request.head_sha
            and review.decision == ReviewDecision.APPROVE
            and review.reviewer in self.eligible_reviewers
        }

        if len(approvals) < self.required_approvals:
            reasons.append(
                f"{self.required_approvals} eligible approvals are required; "
                f"only {len(approvals)} are present."
            )

        if any(
            review.decision == ReviewDecision.REQUEST_CHANGES
            and review.commit_sha == pull_request.head_sha
            for review in pull_request.reviews
        ):
            reasons.append("A reviewer requested changes on the current commit.")

        current_checks = [
            check
            for check in pull_request.checks
            if check.commit_sha == pull_request.head_sha
        ]

        if not current_checks:
            reasons.append("No status checks exist for the current commit.")
        elif any(check.status != CheckStatus.PASSING for check in current_checks):
            reasons.append("One or more current status checks are failing or pending.")

        if not pull_request.mergeable:
            reasons.append("The Pull Request has unresolved merge conflicts.")

        return MergeDecision(not reasons, tuple(reasons))


# ---------------------------------------------------------------------------
# Observer pattern
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PullRequestEvent:
    event_type: str
    pull_request_number: int
    actor: str
    message: str


class PullRequestObserver(Protocol):
    def update(self, event: PullRequestEvent) -> None:
        ...


class EventBus:
    """
    Subject in the Observer pattern.

    Observers subscribe to the event bus. The publisher does not need to know
    whether an observer sends email, records an audit event, updates metrics,
    or performs another action.
    """

    def __init__(self) -> None:
        self._observers: list[PullRequestObserver] = []

    def subscribe(self, observer: PullRequestObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: PullRequestObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def publish(self, event: PullRequestEvent) -> None:
        for observer in tuple(self._observers):
            try:
                observer.update(event)
            except Exception as exc:
                # One observer failure must not prevent other subscribers from
                # receiving the event.
                print(
                    f"[event-bus] observer {type(observer).__name__} failed: {exc}"
                )


class AuditLogger:
    def __init__(self) -> None:
        self.entries: list[str] = []

    def update(self, event: PullRequestEvent) -> None:
        entry = (
            f"{event.event_type}: PR #{event.pull_request_number} "
            f"by {event.actor}: {event.message}"
        )
        self.entries.append(entry)
        print(f"[audit] {entry}")


class ReviewNotifier:
    def __init__(self) -> None:
        self.notifications: list[str] = []

    def update(self, event: PullRequestEvent) -> None:
        if event.event_type in {"review_requested", "changes_requested"}:
            message = (
                f"Review notification for PR #{event.pull_request_number}: "
                f"{event.message}"
            )
            self.notifications.append(message)
            print(f"[notification] {message}")


class MetricsCollector:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def update(self, event: PullRequestEvent) -> None:
        self.counts[event.event_type] = self.counts.get(event.event_type, 0) + 1


# ---------------------------------------------------------------------------
# Adapter pattern
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExternalBuild:
    build_id: str
    conclusion: str
    commit: str


class ExternalCiProvider:
    """
    Simulates an external CI system with terminology different from the
    repository platform.
    """

    def __init__(self) -> None:
        self._builds = [
            ExternalBuild("build-901", "success", "abc123"),
            ExternalBuild("build-902", "failure", "def456"),
        ]

    def get_latest_build(self, commit: str) -> ExternalBuild | None:
        matching = [build for build in self._builds if build.commit == commit]
        return matching[-1] if matching else None


class StatusProvider(Protocol):
    def get_status(self, commit_sha: str) -> StatusCheck:
        ...


class CiAdapter:
    """
    Adapter translating the external CI provider's API and terminology into
    the application's StatusProvider interface.
    """

    def __init__(self, provider: ExternalCiProvider) -> None:
        self.provider = provider

    def get_status(self, commit_sha: str) -> StatusCheck:
        build = self.provider.get_latest_build(commit_sha)

        if build is None:
            return StatusCheck(
                name="external-ci",
                status=CheckStatus.PENDING,
                commit_sha=commit_sha,
            )

        status_map = {
            "success": CheckStatus.PASSING,
            "failure": CheckStatus.FAILING,
            "cancelled": CheckStatus.FAILING,
        }

        status = status_map.get(build.conclusion, CheckStatus.PENDING)

        return StatusCheck(
            name=f"external-ci/{build.build_id}",
            status=status,
            commit_sha=commit_sha,
        )


# ---------------------------------------------------------------------------
# Repository service
# ---------------------------------------------------------------------------

class PullRequestService:
    """
    Coordinates domain operations.

    Strategy is injected rather than selected by the Pull Request itself.
    Observer notifications are emitted as domain events.
    Adapter-based status retrieval is hidden behind StatusProvider.
    """

    def __init__(
        self,
        merge_strategy: MergeStrategy,
        status_provider: StatusProvider,
        event_bus: EventBus,
    ) -> None:
        self.merge_strategy = merge_strategy
        self.status_provider = status_provider
        self.event_bus = event_bus

    def synchronize_status(self, pull_request: PullRequest, actor: str) -> None:
        check = self.status_provider.get_status(pull_request.head_sha)
        pull_request.checks.append(check)

        self.event_bus.publish(
            PullRequestEvent(
                event_type="status_updated",
                pull_request_number=pull_request.number,
                actor=actor,
                message=f"{check.name} is {check.status.value}.",
            )
        )

    def request_review(
        self,
        pull_request: PullRequest,
        actor: str,
        reviewer: str,
    ) -> None:
        self.event_bus.publish(
            PullRequestEvent(
                event_type="review_requested",
                pull_request_number=pull_request.number,
                actor=actor,
                message=f"Review requested from {reviewer}.",
            )
        )

    def add_review(
        self,
        pull_request: PullRequest,
        actor: str,
        decision: ReviewDecision,
        comment: str = "",
    ) -> None:
        review = Review(
            reviewer=actor,
            decision=decision,
            commit_sha=pull_request.head_sha,
            comment=comment,
        )
        pull_request.add_review(review)

        event_type = (
            "changes_requested"
            if decision == ReviewDecision.REQUEST_CHANGES
            else "review_submitted"
        )

        self.event_bus.publish(
            PullRequestEvent(
                event_type=event_type,
                pull_request_number=pull_request.number,
                actor=actor,
                message=f"Review decision: {decision.value}.",
            )
        )

    def evaluate_merge(self, pull_request: PullRequest) -> MergeDecision:
        return self.merge_strategy.evaluate(pull_request)

    def merge(self, pull_request: PullRequest, actor: str) -> bool:
        decision = self.evaluate_merge(pull_request)

        if not decision.allowed:
            print("[merge] blocked:")
            for reason in decision.reasons:
                print(f"  - {reason}")
            return False

        pull_request.state = PullRequestState.MERGED

        self.event_bus.publish(
            PullRequestEvent(
                event_type="merged",
                pull_request_number=pull_request.number,
                actor=actor,
                message="Pull Request merged successfully.",
            )
        )

        return True


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def build_pull_request() -> PullRequest:
    return PullRequest(
        number=42,
        title="Harden payment authorization workflow",
        source_branch="feature/payment-auth",
        target_branch="main",
        author="alice",
        commits=[
            Commit("abc123", "Implement authorization policy"),
        ],
    )


def demonstrate_strategy() -> None:
    print("\n=== Strategy Pattern ===")

    pull_request = build_pull_request()

    pull_request.add_check(
        StatusCheck("unit-tests", CheckStatus.PASSING, pull_request.head_sha)
    )
    pull_request.add_review(
        Review(
            reviewer="bob",
            decision=ReviewDecision.APPROVE,
            commit_sha=pull_request.head_sha,
        )
    )

    basic = FastForwardStrategy()
    protected = ProtectedBranchStrategy(
        eligible_reviewers={"bob", "carol", "david"},
        required_approvals=2,
    )

    basic_result = basic.evaluate(pull_request)
    protected_result = protected.evaluate(pull_request)

    print(f"Fast-forward strategy: allowed={basic_result.allowed}")
    print(f"Protected-branch strategy: allowed={protected_result.allowed}")
    print(f"Protected reasons: {protected_result.reasons}")

    # The same Pull Request can be evaluated against a stronger policy without
    # modifying the Pull Request class. This is the key Strategy benefit.
    pull_request.add_review(
        Review(
            reviewer="carol",
            decision=ReviewDecision.APPROVE,
            commit_sha=pull_request.head_sha,
        )
    )

    protected_result = protected.evaluate(pull_request)
    print(f"Protected strategy after second approval: {protected_result.allowed}")


def demonstrate_observer_and_adapter() -> None:
    print("\n=== Observer + Adapter Patterns ===")

    pull_request = build_pull_request()

    event_bus = EventBus()
    audit_logger = AuditLogger()
    notifier = ReviewNotifier()
    metrics = MetricsCollector()

    event_bus.subscribe(audit_logger)
    event_bus.subscribe(notifier)
    event_bus.subscribe(metrics)

    external_ci = ExternalCiProvider()
    ci_adapter = CiAdapter(external_ci)

    strategy = FastForwardStrategy()
    service = PullRequestService(strategy, ci_adapter, event_bus)

    service.request_review(pull_request, "alice", "bob")
    service.synchronize_status(pull_request, "ci-bot")
    service.add_review(
        pull_request,
        "bob",
        ReviewDecision.APPROVE,
        "The authorization boundary is clear.",
    )

    result = service.evaluate_merge(pull_request)
    print(f"Merge eligibility: {result.allowed}")

    service.merge(pull_request, "release-bot")

    print("\nMetrics:")
    for event_type, count in sorted(metrics.counts.items()):
        print(f"  {event_type}: {count}")


def demonstrate_adapter_failure() -> None:
    print("\n=== Adapter Edge Case ===")

    external_ci = ExternalCiProvider()
    adapter = CiAdapter(external_ci)

    missing_commit = adapter.get_status("does-not-exist")
    print(
        f"Unknown commit status: {missing_commit.status.value}; "
        "unknown builds are treated as pending rather than passing."
    )


def demonstrate_observer_unsubscription() -> None:
    print("\n=== Observer Lifecycle ===")

    event_bus = EventBus()
    metrics = MetricsCollector()

    event_bus.subscribe(metrics)
    event_bus.publish(
        PullRequestEvent(
            event_type="opened",
            pull_request_number=99,
            actor="alice",
            message="Pull Request opened.",
        )
    )

    event_bus.unsubscribe(metrics)

    event_bus.publish(
        PullRequestEvent(
            event_type="closed",
            pull_request_number=99,
            actor="alice",
            message="Pull Request closed.",
        )
    )

    print(f"Metrics after unsubscribe: {metrics.counts}")


def main() -> None:
    demonstrate_strategy()
    demonstrate_observer_and_adapter()
    demonstrate_adapter_failure()
    demonstrate_observer_unsubscription()


if __name__ == "__main__":
    main()
