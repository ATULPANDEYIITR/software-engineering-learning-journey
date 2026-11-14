#!/usr/bin/env python3
"""
Environment Management
Development, Testing, Staging, and Production

Models environment configuration, artifact promotion, deployment validation,
configuration isolation, release approvals, health checks, and rollback.

Python 3.10+
Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("environment-management")


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class EnvironmentError(Exception):
    pass


class ConfigurationError(EnvironmentError):
    pass


class DeploymentError(EnvironmentError):
    pass


class PolicyViolation(EnvironmentError):
    pass


@dataclass(frozen=True)
class EnvironmentConfig:
    name: Environment
    application_url: str
    database_name: str
    debug: bool
    replicas: int
    minimum_healthy_replicas: int
    require_approval: bool
    require_tests: bool
    require_security_scan: bool
    allow_debug_endpoints: bool
    deployment_timeout_seconds: int
    required_checks: tuple[str, ...]


CONFIGURATIONS: dict[Environment, EnvironmentConfig] = {
    Environment.DEVELOPMENT: EnvironmentConfig(
        name=Environment.DEVELOPMENT,
        application_url="http://localhost:8000",
        database_name="app_development",
        debug=True,
        replicas=1,
        minimum_healthy_replicas=1,
        require_approval=False,
        require_tests=False,
        require_security_scan=False,
        allow_debug_endpoints=True,
        deployment_timeout_seconds=60,
        required_checks=(),
    ),
    Environment.TESTING: EnvironmentConfig(
        name=Environment.TESTING,
        application_url="https://test.example.internal",
        database_name="app_testing",
        debug=False,
        replicas=1,
        minimum_healthy_replicas=1,
        require_approval=False,
        require_tests=True,
        require_security_scan=True,
        allow_debug_endpoints=False,
        deployment_timeout_seconds=120,
        required_checks=("unit_tests", "integration_tests", "security_scan"),
    ),
    Environment.STAGING: EnvironmentConfig(
        name=Environment.STAGING,
        application_url="https://staging.example.com",
        database_name="app_staging",
        debug=False,
        replicas=2,
        minimum_healthy_replicas=2,
        require_approval=True,
        require_tests=True,
        require_security_scan=True,
        allow_debug_endpoints=False,
        deployment_timeout_seconds=180,
        required_checks=(
            "unit_tests",
            "integration_tests",
            "security_scan",
            "smoke_tests",
        ),
    ),
    Environment.PRODUCTION: EnvironmentConfig(
        name=Environment.PRODUCTION,
        application_url="https://app.example.com",
        database_name="app_production",
        debug=False,
        replicas=3,
        minimum_healthy_replicas=3,
        require_approval=True,
        require_tests=True,
        require_security_scan=True,
        allow_debug_endpoints=False,
        deployment_timeout_seconds=300,
        required_checks=(
            "unit_tests",
            "integration_tests",
            "security_scan",
            "smoke_tests",
            "load_tests",
        ),
    ),
}


@dataclass(frozen=True)
class BuildArtifact:
    artifact_id: str
    version: str
    digest: str
    source_commit: str
    build_timestamp: datetime

    @staticmethod
    def create(version: str, source_commit: str, contents: bytes) -> BuildArtifact:
        if not re.fullmatch(r"\d+\.\d+\.\d+", version):
            raise ValueError("Version must follow MAJOR.MINOR.PATCH.")

        if not re.fullmatch(r"[a-f0-9]{7,64}", source_commit):
            raise ValueError("Invalid source commit identifier.")

        if not contents:
            raise ValueError("Artifact cannot be empty.")

        digest = hashlib.sha256(contents).hexdigest()

        return BuildArtifact(
            artifact_id=f"artifact-{digest[:12]}",
            version=version,
            digest=digest,
            source_commit=source_commit,
            build_timestamp=datetime.now(timezone.utc),
        )


@dataclass
class Deployment:
    deployment_id: str
    artifact_id: str
    environment: Environment
    status: DeploymentStatus
    deployed_by: str
    created_at: datetime
    approved_by: str | None = None
    failure_reason: str | None = None
    previous_deployment_id: str | None = None


@dataclass
class EnvironmentState:
    environment: Environment
    active_deployment: Deployment | None = None
    deployment_history: list[Deployment] = field(default_factory=list)
    available: bool = True


class EnvironmentManager:
    """Controls artifact promotion and environment deployment."""

    ORDER = [
        Environment.DEVELOPMENT,
        Environment.TESTING,
        Environment.STAGING,
        Environment.PRODUCTION,
    ]

    def __init__(self, configurations: dict[Environment, EnvironmentConfig]):
        self.configurations = configurations
        self.states = {
            environment: EnvironmentState(environment)
            for environment in Environment
        }
        self.artifacts: dict[str, BuildArtifact] = {}
        self.deployment_counter = 0

    def register_artifact(self, artifact: BuildArtifact) -> None:
        existing = self.artifacts.get(artifact.artifact_id)

        if existing and existing.digest != artifact.digest:
            raise EnvironmentError("Artifact identifier collision.")

        self.artifacts[artifact.artifact_id] = artifact
        logger.info("Registered artifact %s", artifact.artifact_id)

    def validate_configuration(self, environment: Environment) -> None:
        config = self.configurations.get(environment)

        if config is None:
            raise ConfigurationError("Missing environment configuration.")

        if config.replicas < 1:
            raise ConfigurationError("At least one replica is required.")

        if not 1 <= config.minimum_healthy_replicas <= config.replicas:
            raise ConfigurationError("Invalid healthy replica threshold.")

        if config.deployment_timeout_seconds <= 0:
            raise ConfigurationError("Deployment timeout must be positive.")

        if environment == Environment.PRODUCTION:
            if config.debug or config.allow_debug_endpoints:
                raise PolicyViolation(
                    "Production cannot enable debugging or debug endpoints."
                )

        if environment != Environment.DEVELOPMENT and config.debug:
            raise PolicyViolation("Debug mode is restricted to development.")

        if not config.application_url.startswith("https://") and (
            environment != Environment.DEVELOPMENT
        ):
            raise ConfigurationError("Non-development URLs must use HTTPS.")

    def validate_secrets(self, environment: Environment) -> None:
        """Check secret presence without printing secret values."""
        prefix = environment.value.upper()

        required = (
            f"{prefix}_DATABASE_PASSWORD",
            f"{prefix}_APPLICATION_SECRET",
        )

        if environment == Environment.DEVELOPMENT:
            return

        missing = [
            name for name in required
            if not os.environ.get(name)
        ]

        if missing:
            raise ConfigurationError(
                f"Missing required secret variables: {', '.join(missing)}"
            )

    def validate_checks(
        self,
        environment: Environment,
        checks: dict[str, bool],
    ) -> None:
        config = self.configurations[environment]

        failed = [
            check
            for check in config.required_checks
            if checks.get(check) is not True
        ]

        if failed:
            raise PolicyViolation(
                f"Required checks missing or unsuccessful: {failed}"
            )

    def validate_promotion(
        self,
        artifact: BuildArtifact,
        target: Environment,
    ) -> None:
        index = self.ORDER.index(target)

        if index == 0:
            return

        previous_environment = self.ORDER[index - 1]
        previous_state = self.states[previous_environment]

        deployment = previous_state.active_deployment

        if deployment is None:
            raise PolicyViolation(
                f"Artifact must first be deployed to {previous_environment.value}."
            )

        if deployment.artifact_id != artifact.artifact_id:
            raise PolicyViolation(
                "Artifact must be promoted without rebuilding or replacement."
            )

    def deploy(
        self,
        artifact_id: str,
        target: Environment,
        deployed_by: str,
        checks: dict[str, bool] | None = None,
        approved_by: str | None = None,
    ) -> Deployment:
        artifact = self.artifacts.get(artifact_id)

        if artifact is None:
            raise DeploymentError("Unknown artifact.")

        if not deployed_by.strip():
            raise DeploymentError("Deployment actor is required.")

        checks = checks or {}
        config = self.configurations[target]
        state = self.states[target]

        self.validate_configuration(target)
        self.validate_secrets(target)
        self.validate_checks(target, checks)
        self.validate_promotion(artifact, target)

        if not state.available:
            raise DeploymentError("Target environment is unavailable.")

        if config.require_approval and not approved_by:
            raise PolicyViolation(
                f"{target.value} requires an authorized approval."
            )

        if approved_by and approved_by == deployed_by:
            raise PolicyViolation(
                "Deployment approver must differ from deployment actor."
            )

        previous = state.active_deployment

        self.deployment_counter += 1

        deployment = Deployment(
            deployment_id=f"DEP-{self.deployment_counter:05d}",
            artifact_id=artifact.artifact_id,
            environment=target,
            status=DeploymentStatus.VALIDATING,
            deployed_by=deployed_by,
            approved_by=approved_by,
            created_at=datetime.now(timezone.utc),
            previous_deployment_id=(
                previous.deployment_id if previous else None
            ),
        )

        state.deployment_history.append(deployment)

        try:
            # Simulate a deployment health check.
            healthy_replicas = config.replicas

            if healthy_replicas < config.minimum_healthy_replicas:
                raise DeploymentError("Insufficient healthy replicas.")

            if not state.available:
                raise DeploymentError("Environment became unavailable.")

            deployment.status = DeploymentStatus.DEPLOYED
            state.active_deployment = deployment

            logger.info(
                "Deployment %s succeeded: %s -> %s",
                deployment.deployment_id,
                artifact.version,
                target.value,
            )

            return deployment

        except Exception as exc:
            deployment.status = DeploymentStatus.FAILED
            deployment.failure_reason = str(exc)
            logger.exception("Deployment failed.")
            raise

    def rollback(
        self,
        environment: Environment,
        requested_by: str,
    ) -> Deployment:
        state = self.states[environment]
        current = state.active_deployment

        if current is None:
            raise DeploymentError("Nothing is currently deployed.")

        if len(state.deployment_history) < 2:
            raise DeploymentError("No previous successful deployment exists.")

        previous = next(
            (
                deployment
                for deployment in reversed(state.deployment_history[:-1])
                if deployment.status == DeploymentStatus.DEPLOYED
            ),
            None,
        )

        if previous is None:
            raise DeploymentError("No rollback target is available.")

        if not requested_by.strip():
            raise DeploymentError("Rollback actor is required.")

        current.status = DeploymentStatus.ROLLED_BACK
        state.active_deployment = previous

        logger.warning(
            "Rollback in %s: %s -> %s requested by %s",
            environment.value,
            current.deployment_id,
            previous.deployment_id,
            requested_by,
        )

        return previous

    def report(self) -> dict[str, Any]:
        result = {}

        for environment, state in self.states.items():
            active = state.active_deployment

            result[environment.value] = {
                "available": state.available,
                "active_deployment": (
                    active.deployment_id if active else None
                ),
                "artifact_id": active.artifact_id if active else None,
                "deployment_count": len(state.deployment_history),
                "statuses": [
                    item.status.value
                    for item in state.deployment_history
                ],
            }

        return result


def run_demonstration() -> None:
    manager = EnvironmentManager(CONFIGURATIONS)

    artifact_v1 = BuildArtifact.create(
        version="1.0.0",
        source_commit="a1b2c3d4e5f6",
        contents=b"application-release-1.0.0",
    )

    artifact_v2 = BuildArtifact.create(
        version="1.1.0",
        source_commit="b2c3d4e5f6a7",
        contents=b"application-release-1.1.0",
    )

    manager.register_artifact(artifact_v1)

    successful_checks = {
        "unit_tests": True,
        "integration_tests": True,
        "security_scan": True,
        "smoke_tests": True,
        "load_tests": True,
    }

    # Development deployment.
    manager.deploy(
        artifact_v1.artifact_id,
        Environment.DEVELOPMENT,
        "developer-01",
    )

    # Testing deployment.
    manager.deploy(
        artifact_v1.artifact_id,
        Environment.TESTING,
        "ci-pipeline",
        successful_checks,
    )

    # Staging requires independent approval.
    manager.deploy(
        artifact_v1.artifact_id,
        Environment.STAGING,
        "release-engineer",
        successful_checks,
        approved_by="qa-manager",
    )

    # Production requires a production-specific approval.
    manager.deploy(
        artifact_v1.artifact_id,
        Environment.PRODUCTION,
        "release-engineer",
        successful_checks,
        approved_by="production-manager",
    )

    # Promote a new immutable artifact through the same sequence.
    manager.register_artifact(artifact_v2)

    manager.deploy(
        artifact_v2.artifact_id,
        Environment.DEVELOPMENT,
        "developer-01",
    )

    manager.deploy(
        artifact_v2.artifact_id,
        Environment.TESTING,
        "ci-pipeline",
        successful_checks,
    )

    manager.deploy(
        artifact_v2.artifact_id,
        Environment.STAGING,
        "release-engineer",
        successful_checks,
        approved_by="qa-manager",
    )

    manager.deploy(
        artifact_v2.artifact_id,
        Environment.PRODUCTION,
        "release-engineer",
        successful_checks,
        approved_by="production-manager",
    )

    # Demonstrate production rollback.
    manager.rollback(
        Environment.PRODUCTION,
        requested_by="incident-commander",
    )

    print("\nENVIRONMENT REPORT")
    print(json.dumps(manager.report(), indent=2))

    # Demonstrate invalid production configuration.
    try:
        original = manager.configurations[Environment.PRODUCTION]

        invalid = EnvironmentConfig(
            **{
                **asdict(original),
                "debug": True,
            }
        )

        temporary = dict(manager.configurations)
        temporary[Environment.PRODUCTION] = invalid

        EnvironmentManager(temporary).validate_configuration(
            Environment.PRODUCTION
        )

    except (ConfigurationError, PolicyViolation) as exc:
        logger.info("Expected configuration rejection: %s", exc)

    # Demonstrate failed check validation.
    try:
        manager.validate_checks(
            Environment.PRODUCTION,
            {"unit_tests": True},
        )
    except PolicyViolation as exc:
        logger.info("Expected validation failure: %s", exc)


if __name__ == "__main__":
    try:
        run_demonstration()
    except EnvironmentError as error:
        logger.error("Environment management failure: %s", error)
        sys.exit(1)
