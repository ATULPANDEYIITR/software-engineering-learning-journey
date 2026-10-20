from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


class ValidationError(ValueError):
    """Raised when repository data violates a business rule."""


@dataclass
class PullRequest:
    number: int
    title: str
    source_branch: str
    target_branch: str
    author: str
    commits: List[str] = field(default_factory=list)
    status: str = "OPEN"
    draft: bool = False

    def add_commit(self, commit_id: str) -> None:
        commit_id = commit_id.strip()
        if not commit_id:
            raise ValidationError("Commit ID cannot be empty.")
        if commit_id not in self.commits:
            self.commits.append(commit_id)

    def synchronize(self, target_head: str, source_base: str) -> None:
        if self.status == "CLOSED":
            raise ValidationError("A closed pull request cannot be synchronized.")
        if not target_head or not source_base:
            raise ValidationError("Synchronization references are required.")
        self.add_commit(f"sync:{source_base}->{target_head}")

    def close(self) -> None:
        if self.status == "MERGED":
            raise ValidationError("A merged pull request cannot be closed.")
        self.status = "CLOSED"

    def reopen(self) -> None:
        if self.status != "CLOSED":
            raise ValidationError("Only closed pull requests can be reopened.")
        self.status = "OPEN"


@dataclass
class Review:
    reviewer: str
    state: str
    comment: str = ""
    submitted_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class BranchProtection:
    branch: str
    required_reviews: int
    required_checks: List[str]
    allow_direct_push: bool = False
    allow_force_push: bool = False
    require_conversation_resolution: bool = True
    require_linear_history: bool = False


class Repository:
    def __init__(self, name: str):
        if not name.strip():
            raise ValidationError("Repository name is required.")
        self.name = name
        self.branches: Dict[str, str] = {
            "main": "c100",
            "feature/sql-crud": "c104",
        }
        self.pull_requests: Dict[int, PullRequest] = {}
        self.reviews: Dict[int, List[Review]] = {}
        self.status_checks: Dict[int, Dict[str, str]] = {}
        self.protection: Dict[str, BranchProtection] = {}
        self.next_pr_number = 1

    def protect_branch(self, policy: BranchProtection) -> None:
        if policy.required_reviews < 0:
            raise ValidationError("Required review count cannot be negative.")
        self.protection[policy.branch] = policy

    def create_pull_request(
        self,
        title: str,
        source_branch: str,
        target_branch: str,
        author: str,
        draft: bool = False,
    ) -> PullRequest:
        for branch in (source_branch, target_branch):
            if branch not in self.branches:
                raise ValidationError(f"Unknown branch: {branch}")

        if source_branch == target_branch:
            raise ValidationError("Source and target branches must differ.")

        pr = PullRequest(
            number=self.next_pr_number,
            title=title.strip(),
            source_branch=source_branch,
            target_branch=target_branch,
            author=author.strip(),
            draft=draft,
        )

        if not pr.title or not pr.author:
            raise ValidationError("Title and author are required.")

        self.pull_requests[pr.number] = pr
        self.reviews[pr.number] = []
        self.status_checks[pr.number] = {}
        self.next_pr_number += 1
        return pr

    def add_review(
        self,
        pr_number: int,
        reviewer: str,
        state: str,
        comment: str = "",
    ) -> None:
        if pr_number not in self.pull_requests:
            raise ValidationError("Pull request does not exist.")

        if state not in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}:
            raise ValidationError("Unsupported review state.")

        pr = self.pull_requests[pr_number]
        if reviewer == pr.author:
            raise ValidationError("Authors cannot approve their own pull request.")

        self.reviews[pr_number].append(
            Review(
                reviewer=reviewer,
                state=state,
                comment=comment.strip(),
            )
        )

    def set_status_check(self, pr_number: int, check_name: str, state: str) -> None:
        if pr_number not in self.pull_requests:
            raise ValidationError("Pull request does not exist.")

        if state not in {"PASSING", "FAILING", "PENDING"}:
            raise ValidationError("Invalid status-check state.")

        self.status_checks[pr_number][check_name] = state

    def unresolved_review_threads(self, pr_number: int) -> int:
        return sum(
            1
            for review in self.reviews[pr_number]
            if review.comment and review.state == "CHANGES_REQUESTED"
        )

    def merge_eligibility(self, pr_number: int) -> tuple[bool, List[str]]:
        if pr_number not in self.pull_requests:
            return False, ["Pull request does not exist."]

        pr = self.pull_requests[pr_number]
        policy = self.protection.get(pr.target_branch)

        if not policy:
            return True, []

        reasons: List[str] = []

        if pr.status != "OPEN":
            reasons.append("Pull request is not open.")

        if pr.draft:
            reasons.append("Draft pull requests cannot be merged.")

        approvals = {
            review.reviewer
            for review in self.reviews[pr_number]
            if review.state == "APPROVED"
        }

        if len(approvals) < policy.required_reviews:
            reasons.append(
                f"{policy.required_reviews} unique approval(s) required; "
                f"{len(approvals)} available."
            )

        for required_check in policy.required_checks:
            if self.status_checks[pr_number].get(required_check) != "PASSING":
                reasons.append(f"Required check '{required_check}' is not passing.")

        if policy.require_conversation_resolution:
            unresolved = self.unresolved_review_threads(pr_number)
            if unresolved:
                reasons.append(f"{unresolved} review discussion(s) require resolution.")

        return not reasons, reasons

    def merge(self, pr_number: int) -> None:
        eligible, reasons = self.merge_eligibility(pr_number)
        if not eligible:
            raise ValidationError("Merge blocked: " + "; ".join(reasons))

        pr = self.pull_requests[pr_number]
        self.branches[pr.target_branch] = self.branches[pr.source_branch]
        pr.status = "MERGED"

    def list_pull_requests(self, status: Optional[str] = None) -> List[PullRequest]:
        prs = list(self.pull_requests.values())
        if status is not None:
            prs = [pr for pr in prs if pr.status == status]
        return prs


def main() -> None:
    repository = Repository("sql-learning-repository")

    repository.protect_branch(
        BranchProtection(
            branch="main",
            required_reviews=2,
            required_checks=["unit-tests", "sql-validation"],
            allow_direct_push=False,
            allow_force_push=False,
            require_conversation_resolution=True,
        )
    )

    pr = repository.create_pull_request(
        title="Add SELECT INSERT UPDATE DELETE examples",
        source_branch="feature/sql-crud",
        target_branch="main",
        author="developer",
    )

    pr.add_commit("a81f2d")
    pr.add_commit("b93c10")

    repository.add_review(
        pr.number,
        "reviewer-alice",
        "APPROVED",
        "CRUD queries are correctly constrained.",
    )
    repository.add_review(
        pr.number,
        "reviewer-bob",
        "APPROVED",
        "Validation and transaction examples are acceptable.",
    )

    repository.set_status_check(pr.number, "unit-tests", "PASSING")
    repository.set_status_check(pr.number, "sql-validation", "PASSING")

    eligible, reasons = repository.merge_eligibility(pr.number)

    print(f"Repository: {repository.name}")
    print(f"Pull request #{pr.number}: {pr.title}")
    print(f"Changesets: {len(pr.commits)}")
    print(f"Eligible for merge: {eligible}")

    if reasons:
        print("Blocking conditions:")
        for reason in reasons:
            print(f"  - {reason}")

    if eligible:
        repository.merge(pr.number)
        print(f"Target branch '{pr.target_branch}' updated successfully.")

    print("\nCurrent pull requests:")
    for item in repository.list_pull_requests():
        print(
            f"#{item.number} | {item.status} | "
            f"{item.source_branch} -> {item.target_branch}"
        )


if __name__ == "__main__":
    main()
