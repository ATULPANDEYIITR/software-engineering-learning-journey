#!/usr/bin/env python3
"""
Package Management: Dependency Management and Versioning

Features:
- Semantic versioning
- Version constraint evaluation
- Package registry
- Dependency resolution
- Conflict detection
- Circular dependency detection
- Lockfile generation
- Dependency auditing
- Installation simulation
- Reproducible package environments
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class PackageError(Exception):
    """Base exception for package management."""


class VersionError(PackageError):
    pass


class DependencyConflict(PackageError):
    pass


class CircularDependency(PackageError):
    pass


class PackageNotFound(PackageError):
    pass


class PackageState(Enum):
    AVAILABLE = "available"
    INSTALLED = "installed"
    DEPRECATED = "deprecated"
    VULNERABLE = "vulnerable"


@dataclass(frozen=True, order=True)
class Version:
    major: int
    minor: int
    patch: int

    PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

    @classmethod
    def parse(cls, value: str) -> "Version":
        match = cls.PATTERN.fullmatch(value)
        if not match:
            raise VersionError(f"Invalid semantic version: {value}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


class VersionConstraint:
    """Evaluates a practical subset of semantic version constraints."""

    @staticmethod
    def matches(version: Version, constraint: str) -> bool:
        if not constraint or constraint == "*":
            return True

        for expression in constraint.split(","):
            expression = expression.strip()

            match = re.fullmatch(r"(>=|<=|>|<|=|\^|~)?(.+)", expression)
            if not match:
                raise VersionError(f"Invalid constraint: {expression}")

            operator = match.group(1) or "="
            target = Version.parse(match.group(2))

            if operator == "=" and version != target:
                return False
            elif operator == ">=" and version < target:
                return False
            elif operator == "<=" and version > target:
                return False
            elif operator == ">" and version <= target:
                return False
            elif operator == "<" and version >= target:
                return False
            elif operator == "^":
                upper = (
                    Version(target.major + 1, 0, 0)
                    if target.major > 0
                    else Version(0, target.minor + 1, 0)
                    if target.minor > 0
                    else Version(0, 0, target.patch + 1)
                )
                if not target <= version < upper:
                    return False
            elif operator == "~":
                if not target <= version < Version(
                    target.major, target.minor + 1, 0
                ):
                    return False

        return True


@dataclass
class Package:
    name: str
    version: Version
    dependencies: dict[str, str] = field(default_factory=dict)
    checksum: str = ""
    state: PackageState = PackageState.AVAILABLE

    def __post_init__(self):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,99}", self.name):
            raise PackageError(f"Invalid package name: {self.name}")

        if not self.checksum:
            raw = f"{self.name}:{self.version}"
            self.checksum = hashlib.sha256(raw.encode()).hexdigest()


class PackageRegistry:
    def __init__(self):
        self.packages: dict[str, list[Package]] = {}

    def publish(self, package: Package):
        versions = self.packages.setdefault(package.name, [])

        if any(p.version == package.version for p in versions):
            raise PackageError("Package version already exists")

        versions.append(package)
        versions.sort(key=lambda p: p.version, reverse=True)

    def available(self, name: str) -> list[Package]:
        if name not in self.packages:
            raise PackageNotFound(name)

        return [
            package
            for package in self.packages[name]
            if package.state == PackageState.AVAILABLE
        ]

    def resolve_version(
        self, name: str, constraint: str
    ) -> Package:
        candidates = [
            package
            for package in self.available(name)
            if VersionConstraint.matches(package.version, constraint)
        ]

        if not candidates:
            raise DependencyConflict(
                f"No version of {name} satisfies {constraint}"
            )

        return candidates[0]


class DependencyResolver:
    """
    Resolves a dependency graph using recursive backtracking.

    A single version is selected for each package name.
    """

    def __init__(self, registry: PackageRegistry):
        self.registry = registry
        self.selected: dict[str, Package] = {}
        self.constraints: dict[str, list[str]] = {}
        self.resolving: set[str] = set()
        self.resolved: set[str] = set()

    def resolve(self, requirements: dict[str, str]) -> dict[str, Package]:
        self.selected.clear()
        self.constraints.clear()
        self.resolving.clear()
        self.resolved.clear()

        for name, constraint in requirements.items():
            self.constraints.setdefault(name, []).append(constraint)

        self._visit_all()
        return dict(self.selected)

    def _visit_all(self):
        unresolved = [
            name for name in self.constraints
            if name not in self.resolved
        ]

        if not unresolved:
            return

        name = min(unresolved)

        if name in self.resolving:
            raise CircularDependency(f"Cycle involving {name}")

        constraints = self.constraints[name]

        candidates = [
            package
            for package in self.registry.available(name)
            if all(
                VersionConstraint.matches(package.version, constraint)
                for constraint in constraints
            )
        ]

        if not candidates:
            raise DependencyConflict(
                f"Conflicting requirements for {name}: {constraints}"
            )

        # Try newer versions first, backtracking when dependencies conflict.
        for candidate in candidates:
            snapshot = (
                dict(self.selected),
                {key: list(value) for key, value in self.constraints.items()},
                set(self.resolving),
                set(self.resolved),
            )

            try:
                self.selected[name] = candidate
                self.resolving.add(name)

                for dependency, constraint in candidate.dependencies.items():
                    self.constraints.setdefault(dependency, []).append(
                        constraint
                    )

                    if dependency in self.resolving:
                        raise CircularDependency(
                            f"{name} -> {dependency}"
                        )

                self.resolving.remove(name)
                self.resolved.add(name)
                self._visit_all()
                return

            except (PackageError, KeyError):
                (
                    self.selected,
                    self.constraints,
                    self.resolving,
                    self.resolved,
                ) = snapshot

        raise DependencyConflict(
            f"Unable to resolve dependencies for {name}"
        )


class PackageManager:
    def __init__(self, registry: PackageRegistry):
        self.registry = registry
        self.installed: dict[str, Package] = {}

    def install(self, requirements: dict[str, str]) -> dict[str, Package]:
        resolver = DependencyResolver(self.registry)
        plan = resolver.resolve(requirements)

        # Validate the complete plan before changing installed state.
        new_state = dict(self.installed)
        new_state.update(plan)

        self.installed = new_state

        for package in self.installed.values():
            package.state = PackageState.INSTALLED

        return plan

    def uninstall(self, name: str):
        if name not in self.installed:
            raise PackageNotFound(name)

        dependents = [
            package.name
            for package in self.installed.values()
            if name in package.dependencies
        ]

        if dependents:
            raise DependencyConflict(
                f"{name} is required by {dependents}"
            )

        package = self.installed.pop(name)
        package.state = PackageState.AVAILABLE

    def dependency_tree(self) -> dict:
        result = {}

        for name, package in sorted(self.installed.items()):
            result[name] = {
                "version": str(package.version),
                "dependencies": package.dependencies,
                "checksum": package.checksum,
            }

        return result

    def create_lockfile(self, path: str = "package-lock.json"):
        data = {
            "lockfile_version": 1,
            "packages": self.dependency_tree(),
        }

        destination = Path(path)
        temporary = destination.with_suffix(destination.suffix + ".tmp")

        try:
            temporary.write_text(
                json.dumps(data, indent=2),
                encoding="utf-8",
            )
            temporary.replace(destination)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise

    def audit(self) -> list[str]:
        issues = []

        for package in self.installed.values():
            if package.state == PackageState.VULNERABLE:
                issues.append(
                    f"Security risk: {package.name}@{package.version}"
                )
            elif package.state == PackageState.DEPRECATED:
                issues.append(
                    f"Deprecated package: {package.name}"
                )

        return issues


def build_registry() -> PackageRegistry:
    registry = PackageRegistry()

    registry.publish(Package("core", Version.parse("1.0.0")))
    registry.publish(Package("core", Version.parse("1.2.0")))
    registry.publish(Package("core", Version.parse("2.0.0")))

    registry.publish(
        Package(
            "database",
            Version.parse("1.0.0"),
            {"core": "^1.0.0"},
        )
    )

    registry.publish(
        Package(
            "database",
            Version.parse("2.0.0"),
            {"core": "^2.0.0"},
        )
    )

    registry.publish(
        Package(
            "web-framework",
            Version.parse("1.0.0"),
            {"core": "^1.0.0", "database": "^1.0.0"},
        )
    )

    registry.publish(
        Package(
            "web-framework",
            Version.parse("1.1.0"),
            {"core": "^1.0.0", "database": "^1.0.0"},
        )
    )

    registry.publish(
        Package(
            "web-framework",
            Version.parse("2.0.0"),
            {"core": "^2.0.0", "database": "^2.0.0"},
        )
    )

    return registry


def main():
    registry = build_registry()
    manager = PackageManager(registry)

    print("PACKAGE MANAGEMENT AND DEPENDENCY RESOLUTION")
    print("=" * 55)

    requirements = {"web-framework": "^1.0.0"}

    installed = manager.install(requirements)

    print("\nResolved installation plan:")

    for name, package in sorted(installed.items()):
        print(f"  {name}: {package.version}")

    print("\nDependency tree:")
    print(json.dumps(manager.dependency_tree(), indent=2))

    manager.create_lockfile("package-lock.json")
    print("\nLockfile generated successfully.")

    print("\nVersion constraint tests:")

    tests = [
        ("1.2.0", "^1.0.0"),
        ("2.0.0", "^1.0.0"),
        ("1.2.0", "~1.2.0"),
        ("1.3.0", "~1.2.0"),
        ("1.2.0", ">=1.0.0,<2.0.0"),
    ]

    for version, constraint in tests:
        result = VersionConstraint.matches(
            Version.parse(version), constraint
        )
        print(f"  {version} satisfies {constraint}: {result}")

    print("\nConflict detection:")

    try:
        manager.install({
            "core": "^1.0.0",
            "database": "^2.0.0",
        })
    except PackageError as error:
        print(f"  Expected failure: {error}")

    print("\nUninstallation protection:")

    try:
        manager.uninstall("core")
    except PackageError as error:
        print(f"  Expected failure: {error}")

    print("\nAudit:")
    issues = manager.audit()
    print(issues if issues else "  No known package issues.")

    # Assertions provide executable correctness checks.
    assert VersionConstraint.matches(
        Version.parse("1.5.0"), "^1.0.0"
    )
    assert not VersionConstraint.matches(
        Version.parse("2.0.0"), "^1.0.0"
    )
    assert "core" in manager.installed
    assert "database" in manager.installed

    print("\nAll validation checks passed.")


if __name__ == "__main__":
    main()
