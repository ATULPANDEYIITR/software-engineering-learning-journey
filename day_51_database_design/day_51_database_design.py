from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class MergeStrategy(Enum):
    MERGE_COMMIT = "merge_commit"
    SQUASH = "squash"
    REBASE = "rebase"


class PullRequestState(Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ReviewState(Enum):
    COMMENTED = "commented"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str
    author: str


@dataclass
class Review:
    reviewer: str
    state: ReviewState
    commit_sha: str
    comments: List[str] = field(default_factory=list)


@dataclass
class StatusCheck:
    name: str
    passed: bool
    required: bool = True


@dataclass
class BranchProtection:
    branch: str
    required_approvals: int = 1
    required_checks: Set[str] = field(default_factory=set)
    require_conversation_resolution: bool = True
    require_linear_history: bool = False
    allow_direct_push: bool = False
    allow_force_push: bool = False
    allow_deletion: bool = False
    bypass_users: Set[str] = field(default_factory=set)


@dataclass
class PullRequest:
    number: int
    source_branch: str
    target_branch: str
    author: str
    title: str
    commits: List[Commit] = field(default_factory=list)
    reviewers: Set[str] = field(default_factory=set)
    reviews: List[Review] = field(default_factory=list)
    checks: Dict[str, StatusCheck] = field(default_factory=dict)
    conversations: Dict[int, bool] = field(default_factory=dict)
    state: PullRequestState = PullRequestState.DRAFT
    merge_strategy: Optional[MergeStrategy] = None

    def add_commit(self, commit: Commit) -> None:
        if self.state in {PullRequestState.MERGED, PullRequestState.CLOSED}:
            raise ValueError("Cannot add commits to a closed or merged Pull Request.")
        if any(existing.sha == commit.sha for existing in self.commits):
            raise ValueError(f"Commit {commit.sha} already exists in the Pull Request.")
        self.commits.append(commit)

    def request_review(self, reviewer: str) -> None:
        if not reviewer or reviewer == self.author:
            raise ValueError("The author cannot be the sole requested reviewer.")
        self.reviewers.add(reviewer)

    def add_review(
        self,
        reviewer: str,
        state: ReviewState,
        commit_sha: str,
        comments: Optional[List[str]] = None,
    ) -> None:
        if reviewer not in self.reviewers:
            raise ValueError(f"{reviewer} was not requested as a reviewer.")
        if not any(c.sha == commit_sha for c in self.commits):
            raise ValueError("A review must reference a commit in the Pull Request.")
        self.reviews.append(
            Review(
                reviewer=reviewer,
                state=state,
                commit_sha=commit_sha,
                comments=comments or [],
            )
        )

    def add_status_check(self, name: str, passed: bool) -> None:
        self.checks[name] = StatusCheck(name=name, passed=passed)

    def add_conversation(self, comment_id: int, resolved: bool = False) -> None:
        self.conversations[comment_id] = resolved

    def synchronize(self, new_commit: Commit) -> None:
        """
        Base-branch synchronization changes the latest commit context.
        Reviews tied to older commits are retained as history but approvals
        are treated as stale by the governance engine.
        """
        self.add_commit(new_commit)

    def open(self) -> None:
        if self.state != PullRequestState.DRAFT:
            raise ValueError("Only a draft Pull Request can be opened.")
        self.state = PullRequestState.OPEN

    def close(self) -> None:
        if self.state == PullRequestState.MERGED:
            raise ValueError("A merged Pull Request cannot be closed.")
        self.state = PullRequestState.CLOSED

    def reopen(self) -> None:
        if self.state != PullRequestState.CLOSED:
            raise ValueError("Only a closed Pull Request can be reopened.")
        self.state = PullRequestState.OPEN

    @property
    def latest_commit_sha(self) -> Optional[str]:
        return self.commits[-1].sha if self.commits else None


class RepositoryGovernance:
    def __init__(self, repository: str) -> None:
        self.repository = repository
        self.protections: Dict[str, BranchProtection] = {}

    def protect(self, policy: BranchProtection) -> None:
        self.protections[policy.branch] = policy

    def evaluate(self, pr: PullRequest) -> Tuple[bool, List[str]]:
        reasons: List[str] = []

        if pr.state != PullRequestState.OPEN:
            reasons.append(f"Pull Request state is '{pr.state.value}', not open.")

        if not pr.commits:
            reasons.append("The Pull Request contains no commits.")

        policy = self.protections.get(pr.target_branch)
        if policy is None:
            reasons.append("Target branch has no branch-protection policy.")
            return not reasons, reasons

        if pr.author in policy.bypass_users:
            return True, ["Protected-branch policy bypass granted to the author."]

        latest_sha = pr.latest_commit_sha

        eligible_approvers = {
            review.reviewer
            for review in pr.reviews
            if review.state == ReviewState.APPROVED
            and review.commit_sha == latest_sha
            and review.reviewer in pr.reviewers
            and review.reviewer != pr.author
        }

        if len(eligible_approvers) < policy.required_approvals:
            reasons.append(
                f"Need {policy.required_approvals} current approval(s); "
                f"found {len(eligible_approvers)}."
            )

        for check_name in policy.required_checks:
            check = pr.checks.get(check_name)
            if check is None or not check.passed:
                reasons.append(f"Required status check failed or is missing: {check_name}.")

        if policy.require_conversation_resolution:
            unresolved = [
                comment_id
                for comment_id, resolved in pr.conversations.items()
                if not resolved
            ]
            if unresolved:
                reasons.append(
                    f"Unresolved review conversations: {', '.join(map(str, unresolved))}."
                )

        if policy.require_linear_history and pr.merge_strategy == MergeStrategy.MERGE_COMMIT:
            reasons.append("Merge commits are not allowed by the linear-history policy.")

        return not reasons, reasons

    def merge(self, pr: PullRequest, strategy: MergeStrategy) -> str:
        pr.merge_strategy = strategy
        eligible, reasons = self.evaluate(pr)

        if not eligible:
            raise RuntimeError("Merge blocked:\n- " + "\n- ".join(reasons))

        pr.state = PullRequestState.MERGED

        if strategy == MergeStrategy.MERGE_COMMIT:
            return f"PR #{pr.number} merged with a merge commit."
        if strategy == MergeStrategy.SQUASH:
            return f"PR #{pr.number} merged by squashing its changes."
        return f"PR #{pr.number} merged by rebasing its commits."


def demonstrate() -> None:
    repository = RepositoryGovernance("payments-service")

    repository.protect(
        BranchProtection(
            branch="main",
            required_approvals=2,
            required_checks={"unit-tests", "security-scan"},
            require_conversation_resolution=True,
            require_linear_history=True,
        )
    )

    pr = PullRequest(
        number=42,
        source_branch="feature/payment-validation",
        target_branch="main",
        author="alice",
        title="Validate payment requests",
    )

    pr.add_commit(Commit("a1", "Add payment validation", "alice"))
    pr.add_commit(Commit("a2", "Add boundary checks", "alice"))
    pr.request_review("bob")
    pr.request_review("carol")
    pr.open()

    pr.add_status_check("unit-tests", True)
    pr.add_status_check("security-scan", True)

    pr.add_conversation(101, resolved=True)
    pr.add_conversation(102, resolved=False)

    pr.add_review("bob", ReviewState.APPROVED, "a2")
    pr.add_review(
        "carol",
        ReviewState.CHANGES_REQUESTED,
        "a2",
        ["Handle negative payment amounts."],
    )

    eligible, reasons = repository.evaluate(pr)
    print("Initial merge eligibility:", eligible)
    for reason in reasons:
        print("  -", reason)

    pr.add_commit(Commit("a3", "Reject negative payment amounts", "alice"))
    pr.add_conversation(102, resolved=True)

    # Earlier approvals are stale because they referenced a2.
    eligible, reasons = repository.evaluate(pr)
    print("\nAfter synchronization:", eligible)
    for reason in reasons:
        print("  -", reason)

    pr.add_review("bob", ReviewState.APPROVED, "a3")
    pr.add_review("carol", ReviewState.APPROVED, "a3")

    eligible, reasons = repository.evaluate(pr)
    print("\nAfter current approvals:", eligible)

    if eligible:
        print(repository.merge(pr, MergeStrategy.REBASE))

    print("\nFinal PR state:", pr.state.value)


if __name__ == "__main__":
    demonstrate()
