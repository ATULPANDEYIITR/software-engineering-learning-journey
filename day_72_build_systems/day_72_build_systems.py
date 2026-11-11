#!/usr/bin/env python3
"""
Build Systems: Dependencies, Compilation, and Packaging

A self-contained build-system simulator demonstrating:
- Dependency management and directed acyclic graphs
- Topological compilation order
- Circular dependency detection
- Incremental builds and artifact caching
- Compiler configuration and build profiles
- Parallelizable build planning
- Packaging and SHA-256 checksums
- Validation, error handling, and testing

Run: python build_system.py
Python: 3.10+
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

LOGGER = logging.getLogger("build-system")


class BuildError(Exception):
    """Base exception for build-system failures."""


class DependencyError(BuildError):
    """Invalid or unresolved dependency."""


class CircularDependencyError(BuildError):
    """Circular dependency detected."""


class CompilationError(BuildError):
    """Compilation failure."""


class PackagingError(BuildError):
    """Packaging failure."""


class BuildProfile(Enum):
    DEBUG = "debug"
    RELEASE = "release"


class TargetType(Enum):
    LIBRARY = "library"
    EXECUTABLE = "executable"


@dataclass(frozen=True)
class Dependency:
    name: str
    version: str
    optional: bool = False

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("Dependency name cannot be empty.")

        if not re.fullmatch(r"\d+\.\d+\.\d+", self.version):
            raise ValueError(f"Invalid dependency version: {self.version}")


@dataclass
class BuildTarget:
    name: str
    source: str
    dependencies: list[str] = field(default_factory=list)
    target_type: TargetType = TargetType.LIBRARY
    version: str = "1.0.0"
    enabled: bool = True

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.name):
            raise ValueError(f"Invalid target name: {self.name}")

        if not self.source.strip():
            raise ValueError("Source cannot be empty.")

        if self.version.count(".") != 2:
            raise ValueError("Target version must use semantic versioning.")


@dataclass
class BuildArtifact:
    target: str
    path: str
    checksum: str
    build_hash: str
    profile: str
    size: int
    cached: bool = False


class DependencyGraph:
    """Directed graph with dependency-first topological ordering."""

    def __init__(self):
        self.targets: dict[str, BuildTarget] = {}

    def add_target(self, target: BuildTarget):
        if target.name in self.targets:
            raise DependencyError(f"Duplicate target: {target.name}")

        self.targets[target.name] = target

    def validate(self):
        for target in self.targets.values():
            for dependency in target.dependencies:
                if dependency not in self.targets:
                    raise DependencyError(
                        f"{target.name} requires missing target {dependency}"
                    )

                if dependency == target.name:
                    raise CircularDependencyError(
                        f"{target.name} depends on itself."
                    )

    def topological_sort(self) -> list[str]:
        self.validate()

        temporary = set()
        permanent = set()
        result = []

        def visit(name):
            if name in permanent:
                return

            if name in temporary:
                raise CircularDependencyError(
                    f"Circular dependency involving {name}"
                )

            temporary.add(name)

            for dependency in sorted(
                self.targets[name].dependencies
            ):
                visit(dependency)

            temporary.remove(name)
            permanent.add(name)
            result.append(name)

        for name in sorted(self.targets):
            visit(name)

        return result

    def build_levels(self) -> list[list[str]]:
        """Group independent targets into parallelizable stages."""

        order = self.topological_sort()
        levels = {}

        for name in order:
            dependencies = self.targets[name].dependencies

            levels[name] = (
                0 if not dependencies
                else 1 + max(levels[d] for d in dependencies)
            )

        result = []

        for level in range(max(levels.values(), default=-1) + 1):
            result.append(
                sorted(
                    name for name, value in levels.items()
                    if value == level
                )
            )

        return result


class BuildSystem:
    def __init__(
        self,
        output_directory: str = "build_output",
        profile: BuildProfile = BuildProfile.DEBUG
    ):
        self.output_directory = Path(output_directory)
        self.profile = profile
        self.graph = DependencyGraph()
        self.cache: dict[str, BuildArtifact] = {}
        self.artifacts: dict[str, BuildArtifact] = {}

        self.output_directory.mkdir(
            parents=True,
            exist_ok=True
        )

    def register(self, target: BuildTarget):
        self.graph.add_target(target)

    def fingerprint(self, target: BuildTarget) -> str:
        """Create a deterministic cache key."""

        dependency_hashes = {
            name: self.artifacts[name].build_hash
            for name in sorted(target.dependencies)
        }

        payload = {
            "target": target.name,
            "source": target.source,
            "dependencies": dependency_hashes,
            "version": target.version,
            "profile": self.profile.value,
            "compiler": "simulated-compiler-1.0"
        }

        serialized = json.dumps(
            payload,
            sort_keys=True
        ).encode()

        return hashlib.sha256(serialized).hexdigest()

    def compile_target(self, name: str) -> BuildArtifact:
        target = self.graph.targets[name]

        if not target.enabled:
            raise CompilationError(
                f"Target {name} is disabled."
            )

        build_hash = self.fingerprint(target)

        if build_hash in self.cache:
            cached = self.cache[build_hash]

            artifact = BuildArtifact(
                target=cached.target,
                path=cached.path,
                checksum=cached.checksum,
                build_hash=cached.build_hash,
                profile=cached.profile,
                size=cached.size,
                cached=True
            )

            self.artifacts[name] = artifact

            LOGGER.info("Cache hit: %s", name)
            return artifact

        if "COMPILE_ERROR" in target.source:
            raise CompilationError(
                f"Compilation failed for {name}"
            )

        # A deterministic simulation of compilation.
        compiled_content = (
            f"TARGET={target.name}\n"
            f"VERSION={target.version}\n"
            f"PROFILE={self.profile.value}\n"
            f"SOURCE={target.source}\n"
            f"BUILD_HASH={build_hash}\n"
        )

        suffix = (
            ".exe" if target.target_type == TargetType.EXECUTABLE
            else ".lib"
        )

        output_path = (
            self.output_directory / f"{name}{suffix}"
        )

        try:
            output_path.write_text(
                compiled_content,
                encoding="utf-8"
            )
        except OSError as exc:
            raise CompilationError(
                f"Cannot write artifact for {name}: {exc}"
            ) from exc

        checksum = hashlib.sha256(
            output_path.read_bytes()
        ).hexdigest()

        artifact = BuildArtifact(
            target=name,
            path=str(output_path),
            checksum=checksum,
            build_hash=build_hash,
            profile=self.profile.value,
            size=output_path.stat().st_size
        )

        self.cache[build_hash] = artifact
        self.artifacts[name] = artifact

        LOGGER.info("Compiled: %s", name)

        return artifact

    def build(self) -> list[BuildArtifact]:
        self.artifacts.clear()

        order = self.graph.topological_sort()

        for name in order:
            self.compile_target(name)

        return list(self.artifacts.values())

    def package(
        self,
        package_name: str = "application",
        package_version: str = "1.0.0"
    ) -> Path:
        if not self.artifacts:
            raise PackagingError(
                "No compiled artifacts are available."
            )

        if not re.fullmatch(
            r"[A-Za-z0-9_-]+",
            package_name
        ):
            raise PackagingError("Invalid package name.")

        if not re.fullmatch(
            r"\d+\.\d+\.\d+",
            package_version
        ):
            raise PackagingError("Invalid package version.")

        manifest = {
            "name": package_name,
            "version": package_version,
            "profile": self.profile.value,
            "artifacts": [
                asdict(artifact)
                for artifact in self.artifacts.values()
            ]
        }

        package_directory = (
            self.output_directory
            / f"{package_name}-{package_version}"
        )

        package_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        copied_artifacts = []

        try:
            for artifact in self.artifacts.values():
                source = Path(artifact.path)

                if not source.is_file():
                    raise PackagingError(
                        f"Missing artifact: {source}"
                    )

                destination = package_directory / source.name

                shutil.copy2(source, destination)

                if hashlib.sha256(
                    destination.read_bytes()
                ).hexdigest() != artifact.checksum:
                    raise PackagingError(
                        f"Checksum mismatch: {destination}"
                    )

                copied_artifacts.append(destination)

            manifest_path = package_directory / "manifest.json"

            manifest_path.write_text(
                json.dumps(manifest, indent=4),
                encoding="utf-8"
            )

        except (OSError, PackagingError):
            for path in copied_artifacts:
                path.unlink(missing_ok=True)
            raise

        LOGGER.info("Package created: %s", package_directory)

        return package_directory


def create_demo_build() -> BuildSystem:
    system = BuildSystem(
        output_directory="build_output",
        profile=BuildProfile.RELEASE
    )

    system.register(
        BuildTarget(
            name="core",
            source="core.cpp",
            target_type=TargetType.LIBRARY
        )
    )

    system.register(
        BuildTarget(
            name="database",
            source="database.cpp",
            dependencies=["core"]
        )
    )

    system.register(
        BuildTarget(
            name="network",
            source="network.cpp",
            dependencies=["core"]
        )
    )

    system.register(
        BuildTarget(
            name="application",
            source="main.cpp",
            dependencies=["database", "network"],
            target_type=TargetType.EXECUTABLE
        )
    )

    return system


def run_tests():
    graph = DependencyGraph()

    graph.add_target(
        BuildTarget("a", "a.cpp")
    )

    graph.add_target(
        BuildTarget("b", "b.cpp", ["a"])
    )

    assert graph.topological_sort() == ["a", "b"]
    assert graph.build_levels() == [["a"], ["b"]]

    cycle = DependencyGraph()

    cycle.add_target(
        BuildTarget("x", "x.cpp", ["y"])
    )

    cycle.add_target(
        BuildTarget("y", "y.cpp", ["x"])
    )

    try:
        cycle.topological_sort()
        raise AssertionError("Cycle detection failed.")
    except CircularDependencyError:
        pass

    try:
        Dependency("library", "invalid")
        raise AssertionError("Version validation failed.")
    except ValueError:
        pass

    LOGGER.info("All tests passed.")


def main():
    run_tests()

    system = create_demo_build()

    print("\nDEPENDENCY GRAPH")
    for level, targets in enumerate(
        system.graph.build_levels()
    ):
        print(f"Stage {level}: {', '.join(targets)}")

    print("\nBUILD EXECUTION")
    artifacts = system.build()

    for artifact in artifacts:
        print(
            f"{artifact.target}: "
            f"{artifact.path} | "
            f"SHA256={artifact.checksum[:16]}"
        )

    print("\nINCREMENTAL BUILD")
    system.build()

    print("\nPACKAGING")
    package = system.package(
        package_name="enterprise_application",
        package_version="1.0.0"
    )

    print(f"Package directory: {package.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except BuildError as exc:
        LOGGER.error("Build failed: %s", exc)
        raise SystemExit(1)
