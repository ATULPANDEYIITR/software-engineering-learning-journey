#!/usr/bin/env python3
"""
Software Release Engineering
Release strategies, rollback, and change management.

A self-contained release management simulator supporting:
- Rolling, canary, blue-green, and recreate deployments.
- Release artifact validation and version tracking.
- Change request approval and risk assessment.
- Automated deployment health checks.
- Traffic allocation and progressive rollout.
- Deployment failure detection and rollback.
- Release history and audit logging.
- Production safety assertions.
"""

from __future__ import annotations

import json
import logging
import random
import sys
import uuid

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("release-engine")


# ---------------------------------------------------------
# Domain types
# ---------------------------------------------------------

class ReleaseStrategy(str, Enum):
    ROLLING = "rolling"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    RECREATE = "recreate"


class ChangeRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeStatus(str, Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


class ReleaseStatus(str, Enum):
    CREATED = "created"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ---------------------------------------------------------
# Data models
# ---------------------------------------------------------

@dataclass(frozen=True)
class ReleaseArtifact:
    version: str
    commit_hash: str
    image_digest: str
    build_number: int
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def validate(self) -> None:
        if not self.version.strip():
            raise ValueError("Release version is required.")

        if len(self.commit_hash) < 7:
            raise ValueError("Commit hash must contain at least 7 characters.")

        if not self.image_digest.startswith("sha256:"):
            raise ValueError("Artifact must use a SHA-256 image digest.")

        if self.build_number <= 0:
            raise ValueError("Build number must be positive.")


@dataclass
class ChangeRequest:
    change_id: str
    title: str
    description: str
    risk: ChangeRisk
    requested_by: str
    status: ChangeStatus = ChangeStatus.SUBMITTED
    approvals: set[str] = field(default_factory=set)
    rejected_by: set[str] = field(default_factory=set)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def approve(self, reviewer: str) -> None:
        if self.status != ChangeStatus.SUBMITTED:
            raise ValueError("Change is not awaiting approval.")

        if reviewer == self.requested_by:
            raise PermissionError("Requesters cannot approve their own changes.")

        if reviewer in self.rejected_by:
            raise ValueError("A rejecting reviewer cannot approve the same request.")

        self.approvals.add(reviewer)

        required = {
            ChangeRisk.LOW: 1,
            ChangeRisk.MEDIUM: 1,
            ChangeRisk.HIGH: 2,
            ChangeRisk.CRITICAL: 3,
        }[self.risk]

        if len(self.approvals) >= required:
            self.status = ChangeStatus.APPROVED

    def reject(self, reviewer: str) -> None:
        if self.status != ChangeStatus.SUBMITTED:
            raise ValueError("Change is not awaiting approval.")

        if reviewer == self.requested_by:
            raise PermissionError("Requesters cannot reject their own changes.")

        self.rejected_by.add(reviewer)
        self.status = ChangeStatus.REJECTED


@dataclass
class DeploymentMetrics:
    error_rate: float
    latency_ms: float
    availability: float
    successful_requests: int
    failed_requests: int

    def healthy(self) -> bool:
        return (
            0 <= self.error_rate <= 0.02
            and self.latency_ms <= 500
            and self.availability >= 0.995
            and self.failed_requests >= 0
            and self.successful_requests >= 0
        )


@dataclass
class Release:
    release_id: str
    artifact: ReleaseArtifact
    environment: Environment
    strategy: ReleaseStrategy
    change_request: ChangeRequest
    status: ReleaseStatus = ReleaseStatus.CREATED
    traffic_percentage: int = 0
    previous_version: Optional[str] = None
    deployment_steps: list[str] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# ---------------------------------------------------------
# Change management
# ---------------------------------------------------------

class ChangeManager:

    def __init__(self):
        self.requests: dict[str, ChangeRequest] = {}

    def submit(
        self,
        title: str,
        description: str,
        risk: ChangeRisk,
        requester: str,
    ) -> ChangeRequest:

        if not title.strip() or not description.strip():
            raise ValueError("Change title and description are required.")

        if not requester.strip():
            raise ValueError("Requester identity is required.")

        request = ChangeRequest(
            change_id=str(uuid.uuid4()),
            title=title,
            description=description,
            risk=risk,
            requested_by=requester,
        )

        self.requests[request.change_id] = request
        logger.info("Change submitted: %s", request.change_id)

        return request

    def get(self, change_id: str) -> ChangeRequest:
        try:
            return self.requests[change_id]
        except KeyError as exc:
            raise ValueError("Unknown change request.") from exc


# ---------------------------------------------------------
# Release engine
# ---------------------------------------------------------

class ReleaseEngine:

    def __init__(self):
        self.current_versions: dict[Environment, Optional[str]] = {
            Environment.DEVELOPMENT: None,
            Environment.STAGING: None,
            Environment.PRODUCTION: None,
        }

        self.releases: dict[str, Release] = {}
        self.audit_log: list[dict] = {}

    def _audit(self, action: str, release: Release, details: str) -> None:
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "release_id": release.release_id,
            "version": release.artifact.version,
            "details": details,
        })

    def create_release(
        self,
        artifact: ReleaseArtifact,
        environment: Environment,
        strategy: ReleaseStrategy,
        change: ChangeRequest,
    ) -> Release:

        artifact.validate()

        if change.status != ChangeStatus.APPROVED:
            raise PermissionError("Release requires an approved change request.")

        if change.status == ChangeStatus.REJECTED:
            raise PermissionError("Rejected changes cannot be released.")

        current = self.current_versions[environment]

        if current == artifact.version:
            raise ValueError("This version is already deployed.")

        release = Release(
            release_id=str(uuid.uuid4()),
            artifact=artifact,
            environment=environment,
            strategy=strategy,
            change_request=change,
            previous_version=current,
        )

        self.releases[release.release_id] = release
        self._audit("RELEASE_CREATED", release, strategy.value)

        return release

    def deploy(
        self,
        release: Release,
        metrics_provider,
        failure_step: Optional[int] = None,
    ) -> bool:

        if release.status != ReleaseStatus.CREATED:
            raise ValueError("Release is not in the created state.")

        if (
            release.environment == Environment.PRODUCTION
            and release.change_request.status != ChangeStatus.APPROVED
        ):
            raise PermissionError("Production release requires approved change.")

        release.status = ReleaseStatus.VALIDATING
        self._audit("VALIDATION_STARTED", release, "Artifact validation")

        try:
            release.artifact.validate()
            release.status = ReleaseStatus.DEPLOYING

            steps = self._deployment_steps(release.strategy)

            for index, traffic in enumerate(steps, start=1):

                if failure_step == index:
                    raise RuntimeError(
                        f"Simulated deployment failure at step {index}."
                    )

                release.traffic_percentage = traffic
                release.deployment_steps.append(
                    f"Traffic allocation: {traffic}%"
                )

                metrics = metrics_provider(release, traffic)

                if not metrics.healthy():
                    raise RuntimeError(
                        f"Health check failed: {metrics}"
                    )

                logger.info(
                    "%s: %s%% traffic, error rate %.3f%%, latency %.1f ms",
                    release.artifact.version,
                    traffic,
                    metrics.error_rate * 100,
                    metrics.latency_ms,
                )

                self._audit(
                    "HEALTH_CHECK_PASSED",
                    release,
                    f"Traffic={traffic}%",
                )

            release.status = ReleaseStatus.SUCCEEDED
            self.current_versions[release.environment] = (
                release.artifact.version
            )

            release.change_request.status = ChangeStatus.IMPLEMENTED

            self._audit("RELEASE_SUCCEEDED", release, "Deployment complete")

            return True

        except Exception as exc:
            logger.error("Deployment failed: %s", exc)

            release.status = ReleaseStatus.FAILED
            self._audit("RELEASE_FAILED", release, str(exc))

            self.rollback(release)
            return False

    @staticmethod
    def _deployment_steps(strategy: ReleaseStrategy) -> list[int]:

        strategies = {
            ReleaseStrategy.CANARY: [5, 10, 25, 50, 100],
            ReleaseStrategy.ROLLING: [25, 50, 75, 100],
            ReleaseStrategy.BLUE_GREEN: [0, 100],
            ReleaseStrategy.RECREATE: [0, 100],
        }

        return strategies[strategy]

    def rollback(self, release: Release) -> None:

        if release.status not in (
            ReleaseStatus.FAILED,
            ReleaseStatus.SUCCEEDED,
        ):
            raise ValueError("Release cannot be rolled back from this state.")

        previous = release.previous_version

        # Restore the last known good version, not the failed artifact.
        self.current_versions[release.environment] = previous
        release.traffic_percentage = 0
        release.status = ReleaseStatus.ROLLED_BACK

        self._audit(
            "ROLLBACK",
            release,
            f"Restored version: {previous}",
        )

        logger.warning(
            "Rollback completed. Active version: %s",
            previous,
        )

    def get_release(self, release_id: str) -> Release:
        try:
            return self.releases[release_id]
        except KeyError as exc:
            raise ValueError("Release not found.") from exc

    def report(self) -> dict:

        return {
            "active_versions": {
                environment.value: version
                for environment, version in self.current_versions.items()
            },
            "release_count": len(self.releases),
            "releases": [
                {
                    "id": release.release_id,
                    "version": release.artifact.version,
                    "environment": release.environment.value,
                    "strategy": release.strategy.value,
                    "status": release.status.value,
                    "previous_version": release.previous_version,
                }
                for release in self.releases.values()
            ],
            "audit_events": len(self.audit_log),
        }


# ---------------------------------------------------------
# Metrics simulation
# ---------------------------------------------------------

def simulated_metrics(
    release: Release,
    traffic: int,
) -> DeploymentMetrics:

    # Lower traffic can reduce exposure during early canary stages.
    error_rate = random.uniform(0.001, 0.008)

    if release.artifact.version == "2.0.0":
        error_rate = 0.04 if traffic >= 25 else 0.005

    return DeploymentMetrics(
        error_rate=error_rate,
        latency_ms=random.uniform(80, 250),
        availability=0.999,
        successful_requests=random.randint(1000, 5000),
        failed_requests=random.randint(0, 10),
    )


# ---------------------------------------------------------
# Demonstration
# ---------------------------------------------------------

def main() -> None:

    manager = ChangeManager()
    engine = ReleaseEngine()

    initial_artifact = ReleaseArtifact(
        version="1.0.0",
        commit_hash="a12bc34def",
        image_digest="sha256:" + "a" * 64,
        build_number=100,
    )

    change = manager.submit(
        title="Initial production deployment",
        description="Deploy the first stable application release.",
        risk=ChangeRisk.MEDIUM,
        requester="release-manager",
    )

    change.approve("engineering-lead")

    initial_release = engine.create_release(
        initial_artifact,
        Environment.PRODUCTION,
        ReleaseStrategy.BLUE_GREEN,
        change,
    )

    assert engine.deploy(initial_release, simulated_metrics)
    assert engine.current_versions[Environment.PRODUCTION] == "1.0.0"

    print("\nInitial deployment completed.")

    # A high-risk change requires two independent reviewers.
    risky_change = manager.submit(
        title="Performance optimization",
        description="Introduce a modified database query execution path.",
        risk=ChangeRisk.HIGH,
        requester="engineering-team",
    )

    risky_change.approve("technical-lead")
    risky_change.approve("security-lead")

    candidate = ReleaseArtifact(
        version="2.0.0",
        commit_hash="b23cd45ef6",
        image_digest="sha256:" + "b" * 64,
        build_number=101,
    )

    candidate_release = engine.create_release(
        candidate,
        Environment.PRODUCTION,
        ReleaseStrategy.CANARY,
        risky_change,
    )

    # The simulated metrics intentionally trigger a health failure.
    successful = engine.deploy(
        candidate_release,
        simulated_metrics,
    )

    assert not successful
    assert candidate_release.status == ReleaseStatus.ROLLED_BACK
    assert engine.current_versions[Environment.PRODUCTION] == "1.0.0"

    print("\nFailed release rolled back successfully.")

    print("\nRelease report:")
    print(json.dumps(engine.report(), indent=2))

    print("\nAudit history:")
    print(json.dumps(engine.audit_log, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, PermissionError, RuntimeError) as exc:
        logger.error("Execution stopped: %s", exc)
        sys.exit(1)
