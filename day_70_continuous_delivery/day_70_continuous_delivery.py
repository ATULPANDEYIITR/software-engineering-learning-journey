#!/usr/bin/env python3
"""
Continuous Delivery: Build, Test, Package, and Release

A self-contained continuous delivery pipeline simulator.

Features:
- Pipeline stage orchestration
- Build and automated testing
- Artifact packaging and SHA-256 verification
- Release validation and promotion
- Environment-specific approvals
- Atomic artifact publication
- Failure handling and rollback
- Pipeline event logging
- Automated integrity tests

Requires Python 3.10 or later.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
import zipfile

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("continuous_delivery")


class PipelineError(Exception):
    """Base exception for pipeline failures."""


class ValidationError(PipelineError):
    """Raised when pipeline input or artifacts are invalid."""


class IntegrityError(PipelineError):
    """Raised when artifact integrity verification fails."""


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RELEASED = "released"


class StageName(Enum):
    BUILD = "build"
    TEST = "test"
    PACKAGE = "package"
    RELEASE = "release"


@dataclass
class PipelineConfig:
    application: str
    version: str
    workspace: Path
    environment: str = "staging"
    minimum_test_count: int = 1

    def validate(self) -> None:
        if not self.application or not self.application.replace("-", "").replace("_", "").isalnum():
            raise ValidationError("Invalid application name")

        if not self.version or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-+" for c in self.version):
            raise ValidationError("Invalid version identifier")

        if self.environment not in {"development", "staging", "production"}:
            raise ValidationError("Unsupported deployment environment")

        if self.minimum_test_count < 1:
            raise ValidationError("At least one test is required")


@dataclass
class StageResult:
    name: StageName
    status: StageStatus = StageStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    message: str = ""
    duration_seconds: float = 0.0


@dataclass
class Artifact:
    filename: str
    path: Path
    checksum: str
    size: int
    version: str


@dataclass
class PipelineRun:
    run_id: str
    config: PipelineConfig
    status: PipelineStatus = PipelineStatus.CREATED
    stages: list[StageResult] = field(default_factory=list)
    artifact: Artifact | None = None
    events: list[dict] = field(default_factory=list)
    failure_reason: str | None = None

    def record_event(self, event: str, details: str = "") -> None:
        self.events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "details": details
        })


class ContinuousDeliveryPipeline:
    """Coordinates the complete delivery lifecycle."""

    def __init__(self, config: PipelineConfig):
        config.validate()
        self.config = config
        self.workspace = config.workspace.resolve()
        self.source_dir = self.workspace / "source"
        self.build_dir = self.workspace / "build"
        self.package_dir = self.workspace / "packages"
        self.release_dir = self.workspace / "releases"

        for directory in (
            self.source_dir,
            self.build_dir,
            self.package_dir,
            self.release_dir
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self.run = PipelineRun(
            run_id=f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}",
            config=config
        )

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)

        return digest.hexdigest()

    def prepare_source(self) -> None:
        """Create a small application source tree for the demonstration."""
        app_file = self.source_dir / "application.json"

        if not app_file.exists():
            content = {
                "application": self.config.application,
                "version": self.config.version,
                "entrypoint": "main.py",
                "runtime": "python"
            }

            app_file.write_text(
                json.dumps(content, indent=2),
                encoding="utf-8"
            )

        main_file = self.source_dir / "main.py"

        if not main_file.exists():
            main_file.write_text(
                "def calculate_total(values):\n"
                "    return sum(values)\n\n"
                "if __name__ == '__main__':\n"
                "    print(calculate_total([10, 20, 30]))\n",
                encoding="utf-8"
            )

    def execute_stage(
        self,
        stage_name: StageName,
        operation: Callable[[], str]
    ) -> StageResult:

        result = StageResult(name=stage_name)
        started = datetime.now(timezone.utc)

        result.status = StageStatus.RUNNING
        result.started_at = started.isoformat()

        self.run.record_event(
            "stage_started",
            stage_name.value
        )

        logger.info("Starting stage: %s", stage_name.value)

        try:
            result.message = operation()
            result.status = StageStatus.PASSED

        except Exception as exc:
            result.status = StageStatus.FAILED
            result.message = str(exc)
            self.run.failure_reason = (
                f"{stage_name.value}: {exc}"
            )

            logger.exception("Stage failed: %s", stage_name.value)
            raise

        finally:
            completed = datetime.now(timezone.utc)
            result.completed_at = completed.isoformat()
            result.duration_seconds = (
                completed - started
            ).total_seconds()

            self.run.stages.append(result)

            self.run.record_event(
                f"stage_{result.status.value}",
                result.message
            )

        logger.info(
            "Completed %s: %s",
            stage_name.value,
            result.status.value
        )

        return result

    def build(self) -> str:
        """Validate source and create build output."""
        self.prepare_source()

        manifest_path = self.source_dir / "application.json"

        try:
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (json.JSONDecodeError, OSError) as exc:
            raise ValidationError(
                f"Cannot read application manifest: {exc}"
            ) from exc

        if manifest.get("version") != self.config.version:
            raise ValidationError("Source version mismatch")

        main_file = self.source_dir / "main.py"

        if not main_file.is_file():
            raise ValidationError("Application entrypoint is missing")

        if main_file.stat().st_size == 0:
            raise ValidationError("Application entrypoint is empty")

        self.build_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(main_file, self.build_dir / "main.py")
        shutil.copy2(
            manifest_path,
            self.build_dir / "application.json"
        )

        logger.info("Build contains %d files", len(list(self.build_dir.iterdir())))

        return "Build completed and source manifest validated"

    def test(self) -> str:
        """Execute functional and edge-case tests."""
        main_file = self.build_dir / "main.py"

        if not main_file.exists():
            raise PipelineError("Build output does not exist")

        source = main_file.read_text(encoding="utf-8")

        namespace: dict = {}
        exec(compile(source, str(main_file), "exec"), namespace)

        calculate_total = namespace.get("calculate_total")

        if not callable(calculate_total):
            raise ValidationError("Required function is unavailable")

        tests = [
            ([10, 20, 30], 60),
            ([], 0),
            ([5], 5),
            ([-10, 10], 0),
            ([1, 2, 3, 4], 10)
        ]

        passed = 0

        for values, expected in tests:
            actual = calculate_total(values)

            if actual != expected:
                raise PipelineError(
                    f"Test failed: {values}, expected {expected}, got {actual}"
                )

            passed += 1

        if passed < self.config.minimum_test_count:
            raise PipelineError("Minimum test requirement not satisfied")

        return f"{passed}/{len(tests)} functional tests passed"

    def package(self) -> str:
        """Create a reproducible archive from the build directory."""
        if not any(self.build_dir.iterdir()):
            raise PipelineError("Cannot package an empty build")

        self.package_dir.mkdir(parents=True, exist_ok=True)

        filename = (
            f"{self.config.application}-{self.config.version}.zip"
        )

        package_path = self.package_dir / filename

        temporary_path = package_path.with_suffix(".tmp")

        try:
            with zipfile.ZipFile(
                temporary_path,
                "w",
                compression=zipfile.ZIP_DEFLATED
            ) as archive:

                for file_path in sorted(self.build_dir.rglob("*")):
                    if file_path.is_file():
                        relative = file_path.relative_to(self.build_dir)
                        archive.write(file_path, relative.as_posix())

            # Verify archive readability before publishing it.
            with zipfile.ZipFile(temporary_path, "r") as archive:
                bad_file = archive.testzip()

                if bad_file:
                    raise IntegrityError(
                        f"Corrupt archive entry: {bad_file}"
                    )

            os.replace(temporary_path, package_path)

        finally:
            temporary_path.unlink(missing_ok=True)

        checksum = self.sha256(package_path)

        self.run.artifact = Artifact(
            filename=filename,
            path=package_path,
            checksum=checksum,
            size=package_path.stat().st_size,
            version=self.config.version
        )

        metadata = {
            "application": self.config.application,
            "version": self.config.version,
            "filename": filename,
            "sha256": checksum,
            "size": package_path.stat().st_size,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        metadata_path = package_path.with_suffix(".json")
        metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8"
        )

        return f"Package created: {filename}; SHA-256: {checksum}"

    def verify_artifact(self) -> None:
        """Check artifact existence, checksum and archive structure."""
        artifact = self.run.artifact

        if artifact is None:
            raise PipelineError("No artifact is available")

        if not artifact.path.is_file():
            raise IntegrityError("Artifact is missing")

        actual_checksum = self.sha256(artifact.path)

        if actual_checksum != artifact.checksum:
            raise IntegrityError("Artifact checksum mismatch")

        with zipfile.ZipFile(artifact.path, "r") as archive:
            if archive.testzip() is not None:
                raise IntegrityError("Archive integrity failure")

            for item in archive.infolist():
                target = Path(item.filename)

                if target.is_absolute() or ".." in target.parts:
                    raise IntegrityError("Unsafe archive path")

    def release(self, approved: bool = False) -> str:
        """Promote a verified artifact to the configured environment."""
        if self.config.environment == "production" and not approved:
            raise ValidationError(
                "Production deployment requires explicit approval"
            )

        self.verify_artifact()

        artifact = self.run.artifact
        assert artifact is not None

        environment_dir = self.release_dir / self.config.environment
        environment_dir.mkdir(parents=True, exist_ok=True)

        destination = environment_dir / artifact.filename

        if destination.exists():
            raise PipelineError(
                "This version already exists; releases are immutable"
            )

        temporary = destination.with_suffix(".deploying")

        try:
            shutil.copy2(artifact.path, temporary)

            if self.sha256(temporary) != artifact.checksum:
                raise IntegrityError("Published copy failed verification")

            os.replace(temporary, destination)

        finally:
            temporary.unlink(missing_ok=True)

        self.run.status = PipelineStatus.RELEASED

        self.run.record_event(
            "release_completed",
            f"{self.config.environment}: {destination}"
        )

        return f"Released to {self.config.environment}: {destination}"

    def execute(self, approved: bool = False) -> PipelineRun:
        """Run the delivery stages in dependency order."""
        self.run.status = PipelineStatus.RUNNING

        stages = [
            (StageName.BUILD, self.build),
            (StageName.TEST, self.test),
            (StageName.PACKAGE, self.package),
            (
                StageName.RELEASE,
                lambda: self.release(approved)
            )
        ]

        try:
            for stage_name, operation in stages:
                self.execute_stage(stage_name, operation)

            if self.run.status != PipelineStatus.RELEASED:
                self.run.status = PipelineStatus.SUCCEEDED

        except Exception:
            self.run.status = PipelineStatus.FAILED

            # Stages not executed after a failure are explicitly skipped.
            completed = {stage.name for stage in self.run.stages}

            for stage_name, _ in stages:
                if stage_name not in completed:
                    self.run.stages.append(
                        StageResult(
                            name=stage_name,
                            status=StageStatus.SKIPPED,
                            message="Dependency stage failed"
                        )
                    )

        return self.run

    def write_report(self, destination: Path) -> None:
        report = {
            "run_id": self.run.run_id,
            "application": self.config.application,
            "version": self.config.version,
            "environment": self.config.environment,
            "status": self.run.status.value,
            "failure_reason": self.run.failure_reason,
            "artifact": (
                {
                    "filename": self.run.artifact.filename,
                    "sha256": self.run.artifact.checksum,
                    "size": self.run.artifact.size
                }
                if self.run.artifact else None
            ),
            "stages": [
                {
                    "name": stage.name.value,
                    "status": stage.status.value,
                    "message": stage.message,
                    "duration_seconds": stage.duration_seconds
                }
                for stage in self.run.stages
            ],
            "events": self.run.events
        }

        destination.parent.mkdir(parents=True, exist_ok=True)

        destination.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8"
        )


def run_integrity_tests() -> None:
    """Validate important failure and success conditions."""
    with tempfile.TemporaryDirectory() as temporary:
        workspace = Path(temporary)

        config = PipelineConfig(
            application="inventory-service",
            version="1.2.0",
            workspace=workspace,
            environment="staging"
        )

        pipeline = ContinuousDeliveryPipeline(config)
        result = pipeline.execute()

        assert result.status == PipelineStatus.RELEASED
        assert len(result.stages) == 4
        assert all(
            stage.status == StageStatus.PASSED
            for stage in result.stages
        )

        pipeline.verify_artifact()

        # Existing releases must not be overwritten.
        try:
            pipeline.release()
            raise AssertionError("Duplicate release should fail")
        except PipelineError:
            pass

        # Production requires an approval decision.
        production = ContinuousDeliveryPipeline(
            PipelineConfig(
                application="inventory-service",
                version="2.0.0",
                workspace=workspace / "production",
                environment="production"
            )
        )

        production_result = production.execute(approved=False)
        assert production_result.status == PipelineStatus.FAILED

        approved_pipeline = ContinuousDeliveryPipeline(
            PipelineConfig(
                application="inventory-service",
                version="2.1.0",
                workspace=workspace / "approved-production",
                environment="production"
            )
        )

        approved_result = approved_pipeline.execute(approved=True)
        assert approved_result.status == PipelineStatus.RELEASED

    logger.info("All integrity tests passed")


def main() -> None:
    run_integrity_tests()

    with tempfile.TemporaryDirectory() as temporary:
        config = PipelineConfig(
            application="payment-service",
            version="3.4.0",
            workspace=Path(temporary),
            environment="staging"
        )

        pipeline = ContinuousDeliveryPipeline(config)
        result = pipeline.execute()

        report_path = Path(temporary) / "pipeline-report.json"
        pipeline.write_report(report_path)

        print("\nCONTINUOUS DELIVERY REPORT")
        print("=" * 50)
        print("Run ID:", result.run_id)
        print("Application:", config.application)
        print("Version:", config.version)
        print("Environment:", config.environment)
        print("Pipeline status:", result.status.value)

        for stage in result.stages:
            print(
                f"{stage.name.value:10} "
                f"{stage.status.value:10} "
                f"{stage.duration_seconds:.4f}s"
            )

        if result.artifact:
            print("Artifact:", result.artifact.filename)
            print("SHA-256:", result.artifact.checksum)

        print("Report:", report_path)

        if result.status != PipelineStatus.RELEASED:
            raise SystemExit("Delivery pipeline failed")


if __name__ == "__main__":
    main()
