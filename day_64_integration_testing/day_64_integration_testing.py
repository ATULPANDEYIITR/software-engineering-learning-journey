from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import json
import re
import unittest


class PRState(Enum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class ReviewState(Enum):
    COMMENTED = "commented"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    DISMISSED = "dismissed"


class MergeStrategy(Enum):
    MERGE_COMMIT = "merge_commit"
    SQUASH = "squash"
    REBASE = "rebase"


@dataclass(frozen=True)
class Commit:
    sha: str
    message: str
    branch: str


@dataclass
class Review:
    reviewer: str
    state: ReviewState
    commit_sha: str
    comments: List[str] = field(default_factory=list)
    resolved: bool = True


@dataclass
class StatusCheck:
    name: str
    passed: bool
    commit_sha: str
    required: bool = True


@dataclass
class BranchProtection:
    required_reviews: int = 2
    required_checks: Set[str] = field(
        default_factory=lambda: {"integration-tests", "security-scan"}
    )
    allow_direct_push: bool = False
    allow_force_push: bool = False
    allow_deletion: bool = False
    require_conversation_resolution: bool = True
    require_linear_history: bool = False
    allow_admin_bypass: bool = False


@dataclass
class Branch:
    name: str
    commits: List[Commit] = field(default_factory=list)
    protected: bool = False


@dataclass
class PullRequest:
    number: int
    title: str
    source_branch: str
    target_branch: str
    author: str
    state: PRState = PRState.OPEN
    draft: bool = False
    commits: List[Commit] = field(default_factory=list)
    reviews: List[Review] = field(default_factory=list)
    checks: List[StatusCheck] = field(default_factory=list)
    changed_files: Set[str] = field(default_factory=set)
    merge_strategy: Optional[MergeStrategy] = None

    def latest_commit(self) -> Optional[str]:
        return self.commits[-1].sha if self.commits else None


class Repository:
    def __init__(self, name: str):
        self.name = name
        self.branches: Dict[str, Branch] = {}
        self.pull_requests: Dict[int, PullRequest] = {}
        self.protection: Dict[str, BranchProtection] = {}
        self._next_pr = 1

    def add_branch(self, branch: Branch) -> None:
        if branch.name in self.branches:
            raise ValueError(f"Branch already exists: {branch.name}")
        self.branches[branch.name] = branch

    def protect_branch(self, name: str, policy: BranchProtection) -> None:
        if name not in self.branches:
            raise ValueError(f"Unknown branch: {name}")
        self.branches[name].protected = True
        self.protection[name] = policy

    def add_commit(self, branch_name: str, sha: str, message: str) -> Commit:
        branch = self.branches.get(branch_name)
        if branch is None:
            raise ValueError(f"Unknown branch: {branch_name}")

        if not re.fullmatch(r"[0-9a-f]{7,40}", sha):
            raise ValueError("Commit SHA must contain 7-40 hexadecimal characters")

        commit = Commit(sha, message.strip(), branch_name)
        branch.commits.append(commit)
        return commit

    def create_pull_request(
        self,
        title: str,
        source: str,
        target: str,
        author: str,
        changed_files: Set[str],
        draft: bool = False,
    ) -> PullRequest:
        if source not in self.branches or target not in self.branches:
            raise ValueError("Source and target branches must exist")
        if source == target:
            raise ValueError("A Pull Request cannot target its own source branch")

        pr = PullRequest(
            number=self._next_pr,
            title=title.strip(),
            source_branch=source,
            target_branch=target,
            author=author,
            draft=draft,
            commits=list(self.branches[source].commits),
            changed_files=set(changed_files),
            state=PRState.DRAFT if draft else PRState.OPEN,
        )
        if not pr.commits:
            raise ValueError("A Pull Request must contain at least one commit")

        self.pull_requests[pr.number] = pr
        self._next_pr += 1
        return pr

    def synchronize(self, pr_number: int) -> None:
        pr = self.pull_requests[pr_number]
        pr.commits = list(self.branches[pr.source_branch].commits)

    def reopen(self, pr_number: int) -> None:
        pr = self.pull_requests[pr_number]
        if pr.state != PRState.CLOSED:
            raise ValueError("Only closed Pull Requests can be reopened")
        pr.state = PRState.OPEN

    def close(self, pr_number: int) -> None:
        pr = self.pull_requests[pr_number]
        if pr.state == PRState.MERGED:
            raise ValueError("Merged Pull Requests cannot be closed")
        pr.state = PRState.CLOSED

    def add_review(
        self,
        pr_number: int,
        reviewer: str,
        state: ReviewState,
        commit_sha: str,
        comments: Optional[List[str]] = None,
    ) -> None:
        pr = self.pull_requests[pr_number]

        if reviewer == pr.author:
            raise ValueError("Authors cannot approve their own Pull Request")
        if commit_sha != pr.latest_commit():
            state = ReviewState.DISMISSED

        pr.reviews.append(
            Review(
                reviewer=reviewer,
                state=state,
                commit_sha=commit_sha,
                comments=comments or [],
            )
        )

    def add_status_check(
        self,
        pr_number: int,
        name: str,
        passed: bool,
        commit_sha: str,
    ) -> None:
        pr = self.pull_requests[pr_number]
        pr.checks.append(
            StatusCheck(
                name=name,
                passed=passed,
                commit_sha=commit_sha,
                required=name in self.protection[pr.target_branch].required_checks,
            )
        )

    def unresolved_conversations(self, pr: PullRequest) -> int:
        return sum(
            1
            for review in pr.reviews
            for _ in review.comments
            if not review.resolved
        )

    def merge_eligibility(self, pr_number: int) -> Tuple[bool, List[str]]:
        pr = self.pull_requests[pr_number]
        policy = self.protection.get(pr.target_branch)

        reasons: List[str] = []

        if pr.state not in {PRState.OPEN, PRState.DRAFT}:
            reasons.append("Pull Request is not open")

        if pr.draft:
            reasons.append("Pull Request is still a draft")

        if policy is None:
            reasons.append("Target branch has no protection policy")
            return False, reasons

        latest = pr.latest_commit()

        approvals = {
            review.reviewer
            for review in pr.reviews
            if review.state == ReviewState.APPROVED
            and review.commit_sha == latest
        }

        if len(approvals) < policy.required_reviews:
            reasons.append(
                f"Requires {policy.required_reviews} current approval(s), "
                f"found {len(approvals)}"
            )

        required_checks = policy.required_checks
        for check_name in required_checks:
            matching = [
                c for c in pr.checks
                if c.name == check_name and c.commit_sha == latest
            ]
            if not matching or not matching[-1].passed:
                reasons.append(f"Required status check failed or missing: {check_name}")

        if policy.require_conversation_resolution:
            if self.unresolved_conversations(pr) > 0:
                reasons.append("Unresolved review conversations remain")

        if not pr.changed_files:
            reasons.append("Pull Request contains no changed files")

        return len(reasons) == 0, reasons

    def merge(self, pr_number: int, strategy: MergeStrategy) -> str:
        eligible, reasons = self.merge_eligibility(pr_number)
        if not eligible:
            raise RuntimeError("Merge rejected: " + "; ".join(reasons))

        pr = self.pull_requests[pr_number]
        target = self.branches[pr.target_branch]

        if strategy == MergeStrategy.MERGE_COMMIT:
            sha = f"merge{pr.number:04d}abc"
            target.commits.append(
                Commit(sha, f"Merge PR #{pr.number}: {pr.title}", target.name)
            )
        elif strategy == MergeStrategy.SQUASH:
            sha = f"squash{pr.number:04d}"
            target.commits.append(
                Commit(sha, pr.title, target.name)
            )
        elif strategy == MergeStrategy.REBASE:
            target.commits.extend(
                Commit(c.sha, c.message, target.name) for c in pr.commits
            )

        pr.merge_strategy = strategy
        pr.state = PRState.MERGED
        return target.commits[-1].sha


class RepositoryWorkflowIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Repository("integration-testing-demo")
        self.repo.add_branch(Branch("main"))
        self.repo.add_branch(Branch("feature/api-tests"))
        self.repo.protect_branch(
            "main",
            BranchProtection(
                required_reviews=2,
                required_checks={"integration-tests", "security-scan"},
                require_conversation_resolution=True,
            ),
        )

        self.repo.add_commit("main", "1111111", "Initial production release")
        self.repo.add_commit(
            "feature/api-tests",
            "2222222",
            "Add API and database integration tests",
        )

        self.pr = self.repo.create_pull_request(
            title="Add database and API integration testing",
            source="feature/api-tests",
            target="main",
            author="alice",
            changed_files={"tests/api.py", "tests/database.py"},
        )

    def test_merge_requires_current_approvals_and_checks(self) -> None:
        latest = self.pr.latest_commit()

        self.repo.add_review(
            self.pr.number, "bob", ReviewState.APPROVED, latest
        )
        self.repo.add_review(
            self.pr.number, "carol", ReviewState.APPROVED, latest
        )
        self.repo.add_status_check(
            self.pr.number, "integration-tests", True, latest
        )
        self.repo.add_status_check(
            self.pr.number, "security-scan", True, latest
        )

        eligible, reasons = self.repo.merge_eligibility(self.pr.number)
        self.assertTrue(eligible, reasons)

    def test_stale_approval_is_not_valid_after_new_commit(self) -> None:
        latest = self.pr.latest_commit()

        self.repo.add_review(
            self.pr.number, "bob", ReviewState.APPROVED, latest
        )
        self.repo.add_review(
            self.pr.number, "carol", ReviewState.APPROVED, latest
        )

        self.repo.add_commit(
            "feature/api-tests",
            "3333333",
            "Fix database rollback assertion",
        )
        self.repo.synchronize(self.pr.number)

        self.repo.add_status_check(
            self.pr.number, "integration-tests", True, "3333333"
        )
        self.repo.add_status_check(
            self.pr.number, "security-scan", True, "3333333"
        )

        eligible, reasons = self.repo.merge_eligibility(self.pr.number)
        self.assertFalse(eligible)
        self.assertTrue(any("approval" in r.lower() for r in reasons))

    def test_failed_status_check_blocks_merge(self) -> None:
        latest = self.pr.latest_commit()

        self.repo.add_review(
            self.pr.number, "bob", ReviewState.APPROVED, latest
        )
        self.repo.add_review(
            self.pr.number, "carol", ReviewState.APPROVED, latest
        )
        self.repo.add_status_check(
            self.pr.number, "integration-tests", False, latest
        )
        self.repo.add_status_check(
            self.pr.number, "security-scan", True, latest
        )

        eligible, reasons = self.repo.merge_eligibility(self.pr.number)
        self.assertFalse(eligible)
        self.assertTrue(
            any("integration-tests" in reason for reason in reasons)
        )

    def test_database_and_api_workflow_state_is_separate_from_review_state(self) -> None:
        self.assertEqual(self.pr.state, PRState.OPEN)
        self.assertEqual(self.pr.source_branch, "feature/api-tests")
        self.assertEqual(self.pr.target_branch, "main")
        self.assertEqual(self.pr.changed_files, {
            "tests/api.py",
            "tests/database.py",
        })


def run_demo() -> None:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        RepositoryWorkflowIntegrationTest
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)

    print("\nIntegration-test result:")
    print(json.dumps({
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "successful": result.wasSuccessful(),
    }, indent=2))


if __name__ == "__main__":
    run_demo()
