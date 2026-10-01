"""
Software Design Principles Case Study
DRY, KISS, YAGNI, and Separation of Concerns

This executable module models a software deployment platform and progressively
refactors the design around four principles:

DRY  - shared rules and transformations have one authoritative implementation.
KISS - behavior remains straightforward instead of hiding simple decisions behind
       unnecessary abstractions.
YAGNI - capabilities are implemented when the current requirements need them,
        rather than building speculative infrastructure.
Separation of Concerns - validation, authorization, pricing, persistence,
                         notification, and orchestration have distinct roles.

The program intentionally uses a realistic deployment workflow rather than
isolated syntax demonstrations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, Iterable, List, Optional, Protocol, Sequence
import json
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Domain model
# ---------------------------------------------------------------------------

class DeploymentStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPLOYED = "deployed"
    FAILED = "failed"


@dataclass(frozen=True)
class Developer:
    username: str
    team: str
    active: bool = True


@dataclass(frozen=True)
class DeploymentRequest:
    request_id: str
    service: str
    version: str
    environment: str
    requester: str
    tests_passed: bool
    change_count: int
    risk_score: int


@dataclass
class DeploymentRecord:
    request: DeploymentRequest
    status: DeploymentStatus
    reason: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# KISS: small functions for simple domain rules
# ---------------------------------------------------------------------------

def utc_now() -> str:
    """Use one simple timestamp representation throughout the application."""
    return datetime.now(timezone.utc).isoformat()


def validate_version(version: str) -> bool:
    """
    Keep version validation deliberately small.

    The deployment system only requires a conventional numeric semantic-style
    version such as 2.4.1. It does not need a full package-version parser.
    """
    pieces = version.split(".")
    return len(pieces) == 3 and all(piece.isdigit() for piece in pieces)


def normalize_environment(environment: str) -> str:
    """Normalize user input before policy evaluation."""
    return environment.strip().lower()


def calculate_risk(change_count: int, tests_passed: bool) -> int:
    """
    Simple risk model used by the current product requirements.

    Larger changes receive more risk points. A failed test suite is a direct
    risk signal. There is no speculative machine-learning risk subsystem.
    """
    risk = min(change_count // 10, 7)
    if not tests_passed:
        risk += 5
    return min(risk, 10)


# ---------------------------------------------------------------------------
# Separation of concerns: dedicated validation component
# ---------------------------------------------------------------------------

class ValidationError(Exception):
    """Raised when a deployment request violates input rules."""


class DeploymentValidator:
    """Owns request validation and nothing else."""

    ALLOWED_ENVIRONMENTS = {"staging", "production"}

    def validate(self, request: DeploymentRequest) -> None:
        if not request.request_id.strip():
            raise ValidationError("request_id cannot be empty")

        if not request.service.strip():
            raise ValidationError("service cannot be empty")

        if not validate_version(request.version):
            raise ValidationError(
                "version must contain three numeric components, such as 2.4.1"
            )

        environment = normalize_environment(request.environment)
        if environment not in self.ALLOWED_ENVIRONMENTS:
            raise ValidationError(
                f"unsupported environment: {request.environment}"
            )

        if not request.requester.strip():
            raise ValidationError("requester cannot be empty")

        if request.change_count < 0:
            raise ValidationError("change_count cannot be negative")

        if not 0 <= request.risk_score <= 10:
            raise ValidationError("risk_score must be between 0 and 10")


# ---------------------------------------------------------------------------
# Separation of concerns: authorization
# ---------------------------------------------------------------------------

class AuthorizationService:
    """
    Determines whether the requester can initiate a deployment.

    It does not validate versions, write files, send messages, or deploy code.
    """

    def __init__(self, developers: Iterable[Developer]) -> None:
        self._developers = {
            developer.username: developer for developer in developers
        }

    def can_request_deployment(
        self,
        requester: str,
        environment: str,
    ) -> bool:
        developer = self._developers.get(requester)

        if developer is None or not developer.active:
            return False

        # Production deployment is restricted to platform engineers.
        if normalize_environment(environment) == "production":
            return developer.team == "platform"

        return True


# ---------------------------------------------------------------------------
# DRY: one authoritative deployment policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeploymentPolicy:
    """
    Configuration contains policy data rather than duplicated conditionals.

    The same policy object can be used by validation and eligibility checks.
    """

    maximum_risk_without_approval: int = 4
    maximum_changes_without_extra_review: int = 50
    production_requires_tests: bool = True


class PolicyEngine:
    """Evaluates policy rules without performing side effects."""

    def __init__(self, policy: DeploymentPolicy) -> None:
        self.policy = policy

    def evaluate(self, request: DeploymentRequest) -> List[str]:
        reasons: List[str] = []
        environment = normalize_environment(request.environment)

        if (
            environment == "production"
            and self.policy.production_requires_tests
            and not request.tests_passed
        ):
            reasons.append("production deployments require passing tests")

        if request.risk_score > self.policy.maximum_risk_without_approval:
            reasons.append(
                "risk exceeds the threshold for automatic deployment"
            )

        if request.change_count > self.policy.maximum_changes_without_extra_review:
            reasons.append(
                "large changes require additional review"
            )

        return reasons


# ---------------------------------------------------------------------------
# Separation of concerns: persistence
# ---------------------------------------------------------------------------

class DeploymentRepository(Protocol):
    def save(self, record: DeploymentRecord) -> None:
        ...

    def get(self, request_id: str) -> Optional[DeploymentRecord]:
        ...


class InMemoryDeploymentRepository:
    """Useful for the executable demonstration and automated testing."""

    def __init__(self) -> None:
        self._records: Dict[str, DeploymentRecord] = {}

    def save(self, record: DeploymentRecord) -> None:
        self._records[record.request.request_id] = record

    def get(self, request_id: str) -> Optional[DeploymentRecord]:
        return self._records.get(request_id)


class JsonDeploymentRepository:
    """
    Minimal file-backed repository.

    Persistence is deliberately simple because the current requirement is local
    audit storage, not a distributed database.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def _load(self) -> Dict[str, dict]:
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"deployment audit file is invalid: {self.path}"
            ) from exc

    def save(self, record: DeploymentRecord) -> None:
        data = self._load()
        data[record.request.request_id] = {
            "request": {
                "request_id": record.request.request_id,
                "service": record.request.service,
                "version": record.request.version,
                "environment": record.request.environment,
                "requester": record.request.requester,
                "tests_passed": record.request.tests_passed,
                "change_count": record.request.change_count,
                "risk_score": record.request.risk_score,
            },
            "status": record.status.value,
            "reason": record.reason,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )

    def get(self, request_id: str) -> Optional[DeploymentRecord]:
        raw = self._load().get(request_id)

        if raw is None:
            return None

        request_data = raw["request"]
        request = DeploymentRequest(**request_data)

        return DeploymentRecord(
            request=request,
            status=DeploymentStatus(raw["status"]),
            reason=raw["reason"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )


# ---------------------------------------------------------------------------
# Separation of concerns: notification
# ---------------------------------------------------------------------------

class NotificationService:
    """Owns user-facing notifications but not deployment decisions."""

    def __init__(self) -> None:
        self.messages: List[str] = []

    def notify(self, username: str, message: str) -> None:
        rendered = f"notification[{username}]: {message}"
        self.messages.append(rendered)
        print(rendered)


# ---------------------------------------------------------------------------
# YAGNI: current deployment executor
# ---------------------------------------------------------------------------

class DeploymentExecutor:
    """
    Performs the operation actually required by the current system.

    There is intentionally no plugin registry, container orchestrator,
    multi-cloud adapter, rollback DSL, or speculative workflow engine.
    """

    def deploy(self, request: DeploymentRequest) -> DeploymentStatus:
        if not request.tests_passed:
            return DeploymentStatus.FAILED

        print(
            f"deploying {request.service} {request.version} "
            f"to {normalize_environment(request.environment)}"
        )
        return DeploymentStatus.DEPLOYED


# ---------------------------------------------------------------------------
# Application orchestration
# ---------------------------------------------------------------------------

class DeploymentService:
    """
    Coordinates independent components.

    It owns workflow sequencing, while each collaborator owns one concern.
    """

    def __init__(
        self,
        validator: DeploymentValidator,
        authorization: AuthorizationService,
        policy_engine: PolicyEngine,
        repository: DeploymentRepository,
        notifier: NotificationService,
        executor: DeploymentExecutor,
    ) -> None:
        self.validator = validator
        self.authorization = authorization
        self.policy_engine = policy_engine
        self.repository = repository
        self.notifier = notifier
        self.executor = executor

    def submit(
        self,
        request: DeploymentRequest,
    ) -> DeploymentRecord:
        self.validator.validate(request)

        if not self.authorization.can_request_deployment(
            request.requester,
            request.environment,
        ):
            record = self._record(
                request,
                DeploymentStatus.REJECTED,
                "requester is not authorized for this environment",
            )
            self.repository.save(record)
            self.notifier.notify(
                request.requester,
                "deployment rejected: authorization failed",
            )
            return record

        policy_reasons = self.policy_engine.evaluate(request)

        if policy_reasons:
            reason = "; ".join(policy_reasons)
            record = self._record(
                request,
                DeploymentStatus.REJECTED,
                reason,
            )
            self.repository.save(record)
            self.notifier.notify(
                request.requester,
                f"deployment rejected: {reason}",
            )
            return record

        status = self.executor.deploy(request)

        reason = (
            "deployment completed"
            if status == DeploymentStatus.DEPLOYED
            else "deployment execution failed"
        )

        record = self._record(request, status, reason)
        self.repository.save(record)

        self.notifier.notify(request.requester, reason)
        return record

    @staticmethod
    def _record(
        request: DeploymentRequest,
        status: DeploymentStatus,
        reason: str,
    ) -> DeploymentRecord:
        timestamp = utc_now()
        return DeploymentRecord(
            request=request,
            status=status,
            reason=reason,
            created_at=timestamp,
            updated_at=timestamp,
        )


# ---------------------------------------------------------------------------
# A deliberately problematic design for comparison
# ---------------------------------------------------------------------------

class DuplicatedDeploymentRules:
    """
    This class illustrates what DRY prevents.

    The example is intentionally executable so the repeated policy is visible
    as behavior rather than only as prose.
    """

    def allows_staging(self, request: DeploymentRequest) -> bool:
        # Rule appears here.
        return request.tests_passed and request.risk_score <= 4

    def allows_production(self, request: DeploymentRequest) -> bool:
        # The same rule has been copied instead of reused.
        return request.tests_passed and request.risk_score <= 4


# ---------------------------------------------------------------------------
# KISS versus unnecessary abstraction
# ---------------------------------------------------------------------------

def is_safe_small_change(request: DeploymentRequest) -> bool:
    """
    A direct predicate is clearer than introducing a strategy hierarchy for a
    rule that has only one known form.
    """
    return request.tests_passed and request.change_count <= 10


# ---------------------------------------------------------------------------
# YAGNI example: demonstrate that a requirement should drive a feature
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CurrentRequirements:
    """
    Requirements intentionally describe only capabilities currently needed.
    """

    local_audit: bool = True
    production_authorization: bool = True
    automatic_deployment: bool = True


def demonstrate_yagni(requirements: CurrentRequirements) -> None:
    """
    The function records what the current system actually needs.

    A speculative architecture would add features such as:
    - multi-region failover
    - arbitrary deployment plugins
    - custom workflow scripting
    - predictive capacity planning

    None of those are implemented because no current requirement uses them.
    """
    print("current requirements:")
    print(f"  local audit storage: {requirements.local_audit}")
    print(f"  production authorization: {requirements.production_authorization}")
    print(f"  automatic deployment: {requirements.automatic_deployment}")
    print("speculative infrastructure: intentionally absent")


# ---------------------------------------------------------------------------
# Tests embedded in the executable example
# ---------------------------------------------------------------------------

def run_assertions(service: DeploymentService) -> None:
    """Exercise normal behavior and important failure conditions."""

    valid_production = DeploymentRequest(
        request_id="DEP-100",
        service="payments-api",
        version="2.4.1",
        environment="production",
        requester="maya",
        tests_passed=True,
        change_count=8,
        risk_score=3,
    )

    record = service.submit(valid_production)
    assert record.status == DeploymentStatus.DEPLOYED

    unauthorized = DeploymentRequest(
        request_id="DEP-101",
        service="catalog-api",
        version="1.5.0",
        environment="production",
        requester="leo",
        tests_passed=True,
        change_count=4,
        risk_score=2,
    )

    record = service.submit(unauthorized)
    assert record.status == DeploymentStatus.REJECTED
    assert "authorized" in record.reason

    risky = DeploymentRequest(
        request_id="DEP-102",
        service="search-api",
        version="3.0.0",
        environment="staging",
        requester="leo",
        tests_passed=True,
        change_count=100,
        risk_score=8,
    )

    record = service.submit(risky)
    assert record.status == DeploymentStatus.REJECTED
    assert "risk" in record.reason

    failing_tests = DeploymentRequest(
        request_id="DEP-103",
        service="billing-api",
        version="4.1.0",
        environment="production",
        requester="maya",
        tests_passed=False,
        change_count=2,
        risk_score=2,
    )

    record = service.submit(failing_tests)
    assert record.status == DeploymentStatus.REJECTED
    assert "tests" in record.reason

    try:
        service.submit(
            DeploymentRequest(
                request_id="DEP-104",
                service="identity-api",
                version="bad-version",
                environment="staging",
                requester="maya",
                tests_passed=True,
                change_count=2,
                risk_score=1,
            )
        )
    except ValidationError:
        print("validation edge case correctly rejected")


# ---------------------------------------------------------------------------
# Demonstration of repository substitution
# ---------------------------------------------------------------------------

def demonstrate_file_persistence(
    service_dependencies: Dict[str, object],
) -> None:
    """
    Demonstrate that orchestration does not depend on one persistence mechanism.

    The temporary file keeps the example self-contained and leaves no permanent
    application state on the developer's machine.
    """
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "deployment-audit.json"
        repository = JsonDeploymentRepository(path)

        service = DeploymentService(
            validator=service_dependencies["validator"],  # type: ignore[arg-type]
            authorization=service_dependencies["authorization"],  # type: ignore[arg-type]
            policy_engine=service_dependencies["policy_engine"],  # type: ignore[arg-type]
            repository=repository,
            notifier=service_dependencies["notifier"],  # type: ignore[arg-type]
            executor=service_dependencies["executor"],  # type: ignore[arg-type]
        )

        request = DeploymentRequest(
            request_id="DEP-200",
            service="orders-api",
            version="1.9.2",
            environment="staging",
            requester="leo",
            tests_passed=True,
            change_count=6,
            risk_score=2,
        )

        service.submit(request)

        restored = repository.get("DEP-200")
        assert restored is not None
        assert restored.request.service == "orders-api"
        print(f"persisted audit record: {restored.status.value}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def build_service() -> tuple[DeploymentService, Dict[str, object]]:
    developers = [
        Developer("maya", "platform"),
        Developer("leo", "application"),
        Developer("nina", "application", active=False),
    ]

    policy = DeploymentPolicy(
        maximum_risk_without_approval=4,
        maximum_changes_without_extra_review=50,
        production_requires_tests=True,
    )

    validator = DeploymentValidator()
    authorization = AuthorizationService(developers)
    policy_engine = PolicyEngine(policy)
    repository = InMemoryDeploymentRepository()
    notifier = NotificationService()
    executor = DeploymentExecutor()

    service = DeploymentService(
        validator=validator,
        authorization=authorization,
        policy_engine=policy_engine,
        repository=repository,
        notifier=notifier,
        executor=executor,
    )

    dependencies: Dict[str, object] = {
        "validator": validator,
        "authorization": authorization,
        "policy_engine": policy_engine,
        "notifier": notifier,
        "executor": executor,
    }

    return service, dependencies


def main() -> None:
    print("=== Software Design Principles Case Study ===")
    print("DRY, KISS, YAGNI, and Separation of Concerns")
    print()

    service, dependencies = build_service()

    print("=== KISS: direct domain rules ===")
    sample = DeploymentRequest(
        request_id="DEP-KISS",
        service="profile-api",
        version="1.0.0",
        environment="staging",
        requester="leo",
        tests_passed=True,
        change_count=5,
        risk_score=1,
    )
    print(f"safe small change: {is_safe_small_change(sample)}")
    print()

    print("=== DRY: centralized policy evaluation ===")
    reasons = service.policy_engine.evaluate(
        DeploymentRequest(
            request_id="DEP-DRY",
            service="analytics-api",
            version="2.0.0",
            environment="production",
            requester="maya",
            tests_passed=False,
            change_count=12,
            risk_score=6,
        )
    )
    print("policy findings:", reasons)
    print()

    print("=== YAGNI: requirement-driven scope ===")
    demonstrate_yagni(CurrentRequirements())
    print()

    print("=== Separation of Concerns: complete workflow ===")
    run_assertions(service)
    print()

    print("=== Persistence abstraction ===")
    demonstrate_file_persistence(dependencies)
    print()

    print("=== Design consequences ===")
    print("A policy change belongs in PolicyEngine or DeploymentPolicy.")
    print("A validation change belongs in DeploymentValidator.")
    print("A storage change can replace the repository implementation.")
    print("A notification change does not require rewriting deployment policy.")
    print("A new feature should be added when its requirement is concrete.")
    print()

    print("case study completed successfully")


if __name__ == "__main__":
    main()
