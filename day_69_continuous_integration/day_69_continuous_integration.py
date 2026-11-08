#!/usr/bin/env python3
"""
Continuous Integration Pipeline Simulation

Implements:
- Pipeline configuration and validation
- Commit-triggered execution
- Dependency-aware stage scheduling
- Automated lint, test, security, and build checks
- Retry handling
- Failure propagation
- Artifact generation and integrity verification
- Pipeline metrics and reporting
- Execution history and JSON export

Python 3.10+
Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
import unittest

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("continuous_integration")


class PipelineError(Exception):
    """Base exception for pipeline failures."""


class ConfigurationError(PipelineError):
    pass


class ValidationError(PipelineError):
    pass


class StageExecutionError(PipelineError):
    pass


class PipelineStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class TriggerType(str, Enum):
    PUSH = "PUSH"
    PULL_REQUEST = "PULL_REQUEST"
    SCHEDULE = "SCHEDULE"
    MANUAL = "MANUAL"


@dataclass(frozen=True)
class Commit:
    commit_id: str
    branch: str
    author: str
    message: str

    def __post_init__(self):
        if not re.fullmatch(r"[a-f0-9]{7,40}", self.commit_id):
            raise ValidationError("Invalid commit identifier.")

        if not self.branch or not re.fullmatch(
            r"[A-Za-z0-9._/-]+", self.branch
        ):
            raise ValidationError("Invalid branch name.")

        if not self.author.strip():
            raise ValidationError("Commit author is required.")


@dataclass
class CheckResult:
    name: str
    passed: bool
    message: str
    duration_seconds: float = 0.0


@dataclass
class Stage:
    name: str
    dependencies: list[str] = field(default_factory=list)
    max_retries: int = 0
    status: StageStatus = StageStatus.PENDING
    attempts: int = 0
    results: list[CheckResult] = field(default_factory=list)
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Artifact:
    name: str
    content: str
    checksum: str
    created_at: str

    @classmethod
    def create(cls, name: str, content: str) -> Artifact:
        checksum = hashlib.sha256(
            content.encode("utf-8")
        ).hexdigest()

        return cls(
            name=name,
            content=content,
            checksum=checksum,
            created_at=datetime.now(timezone.utc).isoformat()
        )

    def verify(self) -> bool:
        calculated = hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()

        return calculated == self.checksum


@dataclass
class Pipeline:
    pipeline_id: str
    commit: Commit
    trigger: TriggerType
    stages: list[Stage]
    status: PipelineStatus = PipelineStatus.PENDING
    artifacts: list[Artifact] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    logs: list[str] = field(default_factory=list)


class PipelineValidator:

    @staticmethod
    def validate_stages(stages: list[Stage]) -> None:
        names = [stage.name for stage in stages]

        if len(names) != len(set(names)):
            raise ConfigurationError("Duplicate stage names.")

        known = set(names)

        for stage in stages:
            if stage.max_retries < 0:
                raise ConfigurationError(
                    f"Invalid retry count: {stage.name}"
                )

            for dependency in stage.dependencies:
                if dependency not in known:
                    raise ConfigurationError(
                        f"Unknown dependency: {dependency}"
                    )

                if dependency == stage.name:
                    raise ConfigurationError(
                        "A stage cannot depend on itself."
                    )

        # Detect circular dependencies using depth-first traversal.
        graph = {
            stage.name: stage.dependencies
            for stage in stages
        }

        visited = set()
        active = set()

        def visit(node):
            if node in active:
                raise ConfigurationError(
                    "Circular pipeline dependency detected."
                )

            if node in visited:
                return

            active.add(node)

            for dependency in graph[node]:
                visit(dependency)

            active.remove(node)
            visited.add(node)

        for name in names:
            visit(name)


class AutomatedChecks:

    @staticmethod
    def lint() -> CheckResult:
        started = time.perf_counter()

        source = "def calculate_total(items):\n    return sum(items)\n"

        passed = (
            "def " in source
            and "return" in source
            and "\t" not in source
        )

        return CheckResult(
            name="lint",
            passed=passed,
            message="Source formatting and basic syntax checks passed."
            if passed else "Lint validation failed.",
            duration_seconds=time.perf_counter() - started
        )

    @staticmethod
    def test() -> CheckResult:
        started = time.perf_counter()

        def calculate_total(items):
            return sum(items)

        cases = [
            ([10, 20, 30], 60),
            ([], 0),
            ([-5, 5], 0),
            ([100], 100)
        ]

        passed = all(
            calculate_total(values) == expected
            for values, expected in cases
        )

        return CheckResult(
            name="unit_tests",
            passed=passed,
            message=f"{len(cases)} unit tests evaluated.",
            duration_seconds=time.perf_counter() - started
        )

    @staticmethod
    def security() -> CheckResult:
        started = time.perf_counter()

        source = """
DATABASE_URL = os.environ.get("DATABASE_URL")
TOKEN = os.environ.get("API_TOKEN")
"""

        dangerous_patterns = [
            r"password\s*=\s*['\"]",
            r"api_key\s*=\s*['\"]",
            r"token\s*=\s*['\"]"
        ]

        findings = [
            pattern for pattern in dangerous_patterns
            if re.search(pattern, source, re.IGNORECASE)
        ]

        return CheckResult(
            name="security_scan",
            passed=not findings,
            message="No hardcoded credentials detected."
            if not findings else "Potential credential exposure detected.",
            duration_seconds=time.perf_counter() - started
        )

    @staticmethod
    def build() -> CheckResult:
        started = time.perf_counter()

        source = "application-build-v1"

        passed = len(source) > 0

        return CheckResult(
            name="build",
            passed=passed,
            message="Application build completed."
            if passed else "Build failed.",
            duration_seconds=time.perf_counter() - started
        )


class PipelineRunner:

    def __init__(self):
        self.check_registry: dict[
            str, Callable[[], CheckResult]
        ] = {
            "lint": AutomatedChecks.lint,
            "test": AutomatedChecks.test,
            "security": AutomatedChecks.security,
            "build": AutomatedChecks.build
        }

        self.history: list[Pipeline] = []

    def log(self, pipeline: Pipeline, message: str):
        timestamp = datetime.now(timezone.utc).isoformat()
        pipeline.logs.append(f"{timestamp} | {message}")
        logger.info("%s: %s", pipeline.pipeline_id, message)

    def execute_stage(
        self,
        pipeline: Pipeline,
        stage: Stage
    ) -> bool:

        stage.status = StageStatus.RUNNING
        stage.started_at = datetime.now(timezone.utc).isoformat()

        for attempt in range(stage.max_retries + 1):
            stage.attempts += 1
            self.log(
                pipeline,
                f"Stage {stage.name}, attempt {attempt + 1}"
            )

            try:
                check = self.check_registry.get(stage.name)

                if check is None:
                    raise ConfigurationError(
                        f"No implementation for stage: {stage.name}"
                    )

                result = check()
                stage.results.append(result)

                if not result.passed:
                    raise StageExecutionError(result.message)

                stage.status = StageStatus.SUCCESS
                stage.completed_at = datetime.now(
                    timezone.utc
                ).isoformat()

                self.log(
                    pipeline,
                    f"Stage {stage.name} completed successfully."
                )

                return True

            except Exception as exc:
                stage.error = str(exc)

                self.log(
                    pipeline,
                    f"Stage {stage.name} failed: {exc}"
                )

        stage.status = StageStatus.FAILED
        stage.completed_at = datetime.now(timezone.utc).isoformat()

        return False

    def execute(self, pipeline: Pipeline) -> Pipeline:

        if pipeline.status != PipelineStatus.PENDING:
            raise PipelineError(
                "Only pending pipelines can execute."
            )

        PipelineValidator.validate_stages(pipeline.stages)

        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now(timezone.utc).isoformat()

        stage_lookup = {
            stage.name: stage
            for stage in pipeline.stages
        }

        try:
            for stage in pipeline.stages:

                dependencies = [
                    stage_lookup[name]
                    for name in stage.dependencies
                ]

                if any(
                    dependency.status != StageStatus.SUCCESS
                    for dependency in dependencies
                ):
                    stage.status = StageStatus.SKIPPED
                    stage.error = "A dependency did not succeed."

                    self.log(
                        pipeline,
                        f"Stage {stage.name} skipped."
                    )

                    continue

                success = self.execute_stage(pipeline, stage)

                if not success:
                    # Downstream stages are skipped automatically.
                    for remaining in pipeline.stages:
                        if remaining.status == StageStatus.PENDING:
                            remaining.status = StageStatus.SKIPPED

                    break

            failed = any(
                stage.status == StageStatus.FAILED
                for stage in pipeline.stages
            )

            pipeline.status = (
                PipelineStatus.FAILED
                if failed
                else PipelineStatus.SUCCESS
            )

            if pipeline.status == PipelineStatus.SUCCESS:
                artifact = Artifact.create(
                    name=f"application-{pipeline.pipeline_id}.txt",
                    content=(
                        f"Commit: {pipeline.commit.commit_id}\n"
                        f"Branch: {pipeline.commit.branch}\n"
                        f"Build: successful\n"
                    )
                )

                if not artifact.verify():
                    raise PipelineError("Artifact integrity failure.")

                pipeline.artifacts.append(artifact)

        except Exception:
            pipeline.status = PipelineStatus.FAILED
            raise

        finally:
            pipeline.completed_at = datetime.now(
                timezone.utc
            ).isoformat()

            self.history.append(pipeline)

        return pipeline

    def report(self, pipeline: Pipeline) -> dict:

        return {
            "pipeline_id": pipeline.pipeline_id,
            "commit_id": pipeline.commit.commit_id,
            "branch": pipeline.commit.branch,
            "trigger": pipeline.trigger.value,
            "status": pipeline.status.value,
            "stages": [
                {
                    "name": stage.name,
                    "status": stage.status.value,
                    "attempts": stage.attempts,
                    "error": stage.error,
                    "checks": [
                        asdict(result)
                        for result in stage.results
                    ]
                }
                for stage in pipeline.stages
            ],
            "artifacts": [
                {
                    "name": artifact.name,
                    "checksum": artifact.checksum,
                    "verified": artifact.verify()
                }
                for artifact in pipeline.artifacts
            ],
            "started_at": pipeline.started_at,
            "completed_at": pipeline.completed_at,
            "logs": pipeline.logs
        }

    def export_report(
        self,
        pipeline: Pipeline,
        destination: Path
    ) -> None:

        report = self.report(pipeline)

        # Restrict output to a local destination selected by the caller.
        destination = destination.resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)

        destination.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8"
        )


def create_default_pipeline(commit: Commit) -> Pipeline:

    stages = [
        Stage(name="lint"),
        Stage(name="test", dependencies=["lint"]),
        Stage(name="security", dependencies=["lint"]),
        Stage(
            name="build",
            dependencies=["test", "security"],
            max_retries=1
        )
    ]

    return Pipeline(
        pipeline_id="CI-2026-001",
        commit=commit,
        trigger=TriggerType.PULL_REQUEST,
        stages=stages
    )


class PipelineTests(unittest.TestCase):

    def setUp(self):
        self.runner = PipelineRunner()

    def test_successful_pipeline(self):
        commit = Commit(
            "a123456",
            "feature/payment",
            "developer@example.com",
            "Add payment validation"
        )

        pipeline = create_default_pipeline(commit)
        result = self.runner.execute(pipeline)

        self.assertEqual(
            result.status,
            PipelineStatus.SUCCESS
        )

        self.assertEqual(len(result.artifacts), 1)

    def test_invalid_dependency(self):
        stages = [
            Stage("lint", dependencies=["missing"])
        ]

        with self.assertRaises(ConfigurationError):
            PipelineValidator.validate_stages(stages)

    def test_circular_dependency(self):
        stages = [
            Stage("lint", dependencies=["test"]),
            Stage("test", dependencies=["lint"])
        ]

        with self.assertRaises(ConfigurationError):
            PipelineValidator.validate_stages(stages)

    def test_invalid_commit(self):
        with self.assertRaises(ValidationError):
            Commit(
                "INVALID",
                "main",
                "developer",
                "Invalid commit"
            )


def main():

    commit = Commit(
        commit_id="a123456",
        branch="feature/payment-validation",
        author="developer@example.com",
        message="Implement payment validation"
    )

    runner = PipelineRunner()
    pipeline = create_default_pipeline(commit)

    result = runner.execute(pipeline)

    print("\nCONTINUOUS INTEGRATION REPORT")
    print(json.dumps(runner.report(result), indent=2))

    print("\nRUNNING VALIDATION TESTS")

    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        PipelineTests
    )

    unittest.TextTestRunner(verbosity=2).run(suite)

    print("\nPipeline status:", result.status.value)


if __name__ == "__main__":
    main()
