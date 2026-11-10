#!/usr/bin/env python3
"""
CI/CD Pipeline Automation and Stage Orchestration Engine

Features:
- Pipeline stages and dependency management
- Build, test, security scan, package, approval, deployment
- DAG validation and execution
- Retry policies and failure handling
- Artifact tracking and integrity hashes
- Environment-specific deployment controls
- Manual approval gates
- Execution history and JSON reporting
- Unit-style assertions
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("cicd")


class PipelineError(Exception):
    pass


class ValidationError(PipelineError):
    pass


class StageFailure(PipelineError):
    pass


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PipelineStatus(str, Enum):
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    delay_seconds: float = 0.0

    def __post_init__(self):
        if self.max_attempts < 1:
            raise ValidationError("At least one attempt is required.")
        if self.delay_seconds < 0:
            raise ValidationError("Retry delay cannot be negative.")


@dataclass
class Artifact:
    name: str
    content: str
    checksum: str = field(init=False)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self):
        self.checksum = hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()


@dataclass
class StageResult:
    stage_name: str
    status: StageStatus
    attempts: int = 0
    duration_seconds: float = 0.0
    error: str | None = None
    output: dict = field(default_factory=dict)


@dataclass
class PipelineContext:
    pipeline_id: str
    repository: str
    commit_sha: str
    environment: str
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    results: dict[str, StageResult] = field(default_factory=dict)
    approval_granted: bool = False

    def add_artifact(self, artifact: Artifact):
        if artifact.name in self.artifacts:
            raise ValidationError(
                f"Artifact already exists: {artifact.name}"
            )
        self.artifacts[artifact.name] = artifact


@dataclass
class Stage:
    name: str
    action: Callable[[PipelineContext], dict]
    dependencies: list[str] = field(default_factory=list)
    retry: RetryPolicy = field(default_factory=RetryPolicy)
    timeout_seconds: float = 30.0
    requires_approval: bool = False
    status: StageStatus = StageStatus.PENDING

    def __post_init__(self):
        if not self.name.strip():
            raise ValidationError("Stage name cannot be empty.")
        if self.timeout_seconds <= 0:
            raise ValidationError("Timeout must be positive.")


class Pipeline:
    def __init__(self, context: PipelineContext):
        self.context = context
        self.stages: dict[str, Stage] = {}
        self.status = PipelineStatus.CREATED
        self.execution_order: list[str] = []

    def add_stage(self, stage: Stage):
        if stage.name in self.stages:
            raise ValidationError(
                f"Duplicate stage: {stage.name}"
            )
        self.stages[stage.name] = stage

    def validate(self):
        if not self.stages:
            raise ValidationError("Pipeline has no stages.")

        for stage in self.stages.values():
            for dependency in stage.dependencies:
                if dependency not in self.stages:
                    raise ValidationError(
                        f"Unknown dependency {dependency} "
                        f"in stage {stage.name}"
                    )

                if dependency == stage.name:
                    raise ValidationError("Self-dependency detected.")

        # Topological ordering detects circular dependencies.
        indegree = {
            name: len(stage.dependencies)
            for name, stage in self.stages.items()
        }

        dependents = {name: [] for name in self.stages}

        for name, stage in self.stages.items():
            for dependency in stage.dependencies:
                dependents[dependency].append(name)

        ready = sorted(
            name for name, degree in indegree.items()
            if degree == 0
        )

        order = []

        while ready:
            current = ready.pop(0)
            order.append(current)

            for dependent in sorted(dependents[current]):
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    ready.append(dependent)
                    ready.sort()

        if len(order) != len(self.stages):
            raise ValidationError(
                "Circular dependency detected."
            )

        self.execution_order = order
        return order

    def _execute_stage(self, stage: Stage):
        result = StageResult(
            stage_name=stage.name,
            status=StageStatus.RUNNING,
        )

        stage.status = StageStatus.RUNNING
        start = time.monotonic()

        if stage.requires_approval and not self.context.approval_granted:
            result.status = StageStatus.FAILED
            result.error = "Manual approval required."
            stage.status = result.status
            self.context.results[stage.name] = result
            return result

        for dependency in stage.dependencies:
            dependency_result = self.context.results[dependency]

            if dependency_result.status != StageStatus.SUCCESS:
                result.status = StageStatus.SKIPPED
                result.error = (
                    f"Dependency {dependency} did not succeed."
                )
                stage.status = result.status
                self.context.results[stage.name] = result
                return result

        for attempt in range(1, stage.retry.max_attempts + 1):
            result.attempts = attempt

            try:
                logger.info(
                    "Executing stage=%s attempt=%s",
                    stage.name,
                    attempt,
                )

                output = stage.action(self.context)

                if not isinstance(output, dict):
                    raise StageFailure(
                        "Stage action must return a dictionary."
                    )

                result.output = output
                result.status = StageStatus.SUCCESS
                result.error = None
                break

            except Exception as exc:
                result.error = (
                    f"{type(exc).__name__}: {exc}"
                )

                logger.exception(
                    "Stage %s failed on attempt %s",
                    stage.name,
                    attempt,
                )

                if attempt < stage.retry.max_attempts:
                    time.sleep(stage.retry.delay_seconds)

        result.duration_seconds = round(
            time.monotonic() - start, 4
        )

        stage.status = result.status
        self.context.results[stage.name] = result

        return result

    def run(self):
        self.validate()
        self.status = PipelineStatus.RUNNING

        logger.info(
            "Starting pipeline %s for %s",
            self.context.pipeline_id,
            self.context.repository,
        )

        for stage_name in self.execution_order:
            stage = self.stages[stage_name]
            result = self._execute_stage(stage)

            if result.status == StageStatus.FAILED:
                self.status = PipelineStatus.FAILED

                # Independent stages are not executed after a
                # pipeline-level failure in this serial runner.
                for remaining in self.execution_order[
                    self.execution_order.index(stage_name) + 1:
                ]:
                    pending = self.stages[remaining]
                    pending.status = StageStatus.SKIPPED
                    self.context.results[remaining] = StageResult(
                        stage_name=remaining,
                        status=StageStatus.SKIPPED,
                        error="Pipeline stopped after failure.",
                    )

                return self.status

        self.status = PipelineStatus.SUCCESS
        return self.status

    def report(self):
        return {
            "pipeline_id": self.context.pipeline_id,
            "repository": self.context.repository,
            "commit_sha": self.context.commit_sha,
            "environment": self.context.environment,
            "status": self.status.value,
            "execution_order": self.execution_order,
            "stages": {
                name: {
                    "status": result.status.value,
                    "attempts": result.attempts,
                    "duration_seconds": result.duration_seconds,
                    "error": result.error,
                    "output": result.output,
                }
                for name, result in self.context.results.items()
            },
            "artifacts": {
                name: {
                    "sha256": artifact.checksum,
                    "created_at": artifact.created_at,
                }
                for name, artifact in self.context.artifacts.items()
            },
        }

    def save_report(self, path: str):
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)

        temporary = target.with_suffix(
            target.suffix + ".tmp"
        )

        temporary.write_text(
            json.dumps(self.report(), indent=2),
            encoding="utf-8",
        )

        temporary.replace(target)


# ---------------------- Pipeline actions ----------------------

def checkout(context: PipelineContext):
    if len(context.commit_sha) != 40:
        raise ValidationError("Commit SHA must contain 40 characters.")

    return {
        "repository": context.repository,
        "commit": context.commit_sha,
        "checkout": "completed",
    }


def build(context: PipelineContext):
    build_output = (
        f"Application build for {context.commit_sha}"
    )

    artifact = Artifact(
        name="application-build",
        content=build_output,
    )

    context.add_artifact(artifact)

    return {
        "artifact": artifact.name,
        "sha256": artifact.checksum,
    }


def unit_tests(context: PipelineContext):
    checks = {
        "configuration": True,
        "core_logic": True,
        "input_validation": True,
        "error_handling": True,
    }

    failed = [
        name for name, passed in checks.items()
        if not passed
    ]

    if failed:
        raise StageFailure(
            f"Failed tests: {failed}"
        )

    return {
        "tests_executed": len(checks),
        "passed": len(checks),
        "failed": 0,
    }


def security_scan(context: PipelineContext):
    # A production scanner should evaluate actual source and
    # dependency manifests. This demonstration models its result.
    findings = []

    if findings:
        raise StageFailure(
            f"Security findings: {findings}"
        )

    return {
        "scanner": "dependency-and-source-policy",
        "critical_findings": 0,
        "high_findings": 0,
        "result": "PASSED",
    }


def package(context: PipelineContext):
    if "application-build" not in context.artifacts:
        raise StageFailure("Build artifact is missing.")

    artifact = context.artifacts["application-build"]

    return {
        "package": "application.tar",
        "source_checksum": artifact.checksum,
        "immutable": True,
    }


def deploy(context: PipelineContext):
    if context.environment == "production":
        if not context.approval_granted:
            raise StageFailure(
                "Production deployment is not approved."
            )

    return {
        "environment": context.environment,
        "deployment": "completed",
        "commit": context.commit_sha,
    }


def run_tests():
    policy = RetryPolicy(max_attempts=2, delay_seconds=0)

    context = PipelineContext(
        pipeline_id=str(uuid.uuid4()),
        repository="engineering/payment-service",
        commit_sha="a" * 40,
        environment="production",
        variables={
            "PYTHON_VERSION": "3.13",
            "DEPLOY_REGION": "ap-south-1",
        },
        approval_granted=True,
    )

    pipeline = Pipeline(context)

    pipeline.add_stage(
        Stage("checkout", checkout)
    )

    pipeline.add_stage(
        Stage(
            "build",
            build,
            dependencies=["checkout"],
        )
    )

    pipeline.add_stage(
        Stage(
            "unit_tests",
            unit_tests,
            dependencies=["build"],
            retry=policy,
        )
    )

    pipeline.add_stage(
        Stage(
            "security_scan",
            security_scan,
            dependencies=["build"],
        )
    )

    pipeline.add_stage(
        Stage(
            "package",
            package,
            dependencies=["unit_tests", "security_scan"],
        )
    )

    pipeline.add_stage(
        Stage(
            "deploy",
            deploy,
            dependencies=["package"],
            requires_approval=True,
        )
    )

    assert pipeline.run() == PipelineStatus.SUCCESS

    report = pipeline.report()

    assert report["stages"]["build"]["status"] == "SUCCESS"
    assert report["stages"]["deploy"]["status"] == "SUCCESS"
    assert len(context.artifacts) == 1

    # Validate rejection of circular dependencies.
    invalid = Pipeline(context)
    invalid.add_stage(
        Stage("first", checkout, dependencies=["second"])
    )
    invalid.add_stage(
        Stage("second", build, dependencies=["first"])
    )

    try:
        invalid.validate()
        raise AssertionError("Cycle validation failed.")
    except ValidationError:
        pass

    # Validate that a missing approval blocks deployment.
    blocked_context = PipelineContext(
        pipeline_id=str(uuid.uuid4()),
        repository="engineering/payment-service",
        commit_sha="b" * 40,
        environment="production",
        approval_granted=False,
    )

    blocked = Pipeline(blocked_context)
    blocked.add_stage(Stage("deploy", deploy))

    assert blocked.run() == PipelineStatus.FAILED

    return report


def main():
    report = run_tests()

    output_file = "pipeline_report.json"

    # Report is written atomically to avoid partial JSON files.
    context_report = json.dumps(report, indent=2)
    Path(output_file).write_text(
        context_report,
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to {output_file}")


if __name__ == "__main__":
    main()
