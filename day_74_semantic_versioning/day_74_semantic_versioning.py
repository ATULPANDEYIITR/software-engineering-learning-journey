#!/usr/bin/env python3
"""
Semantic Versioning (SemVer)
Complete implementation of version parsing, comparison, validation,
version increments, compatibility constraints, and release management.

Standard: Semantic Versioning 2.0.0
"""

from __future__ import annotations

import json
import re
import unittest
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from functools import total_ordering
from typing import Optional


SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


class VersionError(ValueError):
    """Raised when a semantic version is invalid."""


class ReleaseError(RuntimeError):
    """Raised when a release operation is invalid."""


class ChangeType(Enum):
    PATCH = "patch"
    MINOR = "minor"
    MAJOR = "major"


@dataclass(frozen=True)
class Version:
    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = ()

    def __post_init__(self):
        for name, value in (
            ("major", self.major),
            ("minor", self.minor),
            ("patch", self.patch),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise VersionError(f"{name} must be an integer")
            if value < 0:
                raise VersionError(f"{name} cannot be negative")

        for identifier in self.prerelease:
            self._validate_identifier(identifier, True)

        for identifier in self.build:
            self._validate_identifier(identifier, False)

    @staticmethod
    def _validate_identifier(identifier: str, prerelease: bool):
        if not identifier or not re.fullmatch(r"[0-9A-Za-z-]+", identifier):
            raise VersionError("Invalid version identifier")

        if prerelease and identifier.isdigit():
            if len(identifier) > 1 and identifier.startswith("0"):
                raise VersionError(
                    "Numeric prerelease identifiers cannot contain leading zeros"
                )

    @classmethod
    def parse(cls, value: str) -> Version:
        if not isinstance(value, str):
            raise VersionError("Version must be a string")

        match = SEMVER_PATTERN.fullmatch(value)

        if not match:
            raise VersionError(f"Invalid semantic version: {value}")

        major, minor, patch, prerelease, build = match.groups()

        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=tuple(prerelease.split(".")) if prerelease else (),
            build=tuple(build.split(".")) if build else (),
        )

    def __str__(self) -> str:
        result = f"{self.major}.{self.minor}.{self.patch}"

        if self.prerelease:
            result += "-" + ".".join(self.prerelease)

        if self.build:
            result += "+" + ".".join(self.build)

        return result

    def precedence_key(self):
        return self.major, self.minor, self.patch

    @staticmethod
    def _compare_prerelease(left, right) -> int:
        if not left and not right:
            return 0
        if not left:
            return 1
        if not right:
            return -1

        for a, b in zip(left, right):
            if a == b:
                continue

            a_numeric = a.isdigit()
            b_numeric = b.isdigit()

            if a_numeric and b_numeric:
                return (int(a) > int(b)) - (int(a) < int(b))

            if a_numeric:
                return -1

            if b_numeric:
                return 1

            return (a > b) - (a < b)

        return (len(left) > len(right)) - (len(left) < len(right))

    def compare(self, other: Version) -> int:
        if not isinstance(other, Version):
            raise TypeError("Can only compare Version objects")

        if self.precedence_key() != other.precedence_key():
            return (
                (self.precedence_key() > other.precedence_key())
                - (self.precedence_key() < other.precedence_key())
            )

        return self._compare_prerelease(
            self.prerelease, other.prerelease
        )

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.compare(other) == 0

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.compare(other) < 0

    def increment(self, change: ChangeType) -> Version:
        if change == ChangeType.MAJOR:
            return Version(self.major + 1, 0, 0)

        if change == ChangeType.MINOR:
            return Version(self.major, self.minor + 1, 0)

        if change == ChangeType.PATCH:
            return Version(self.major, self.minor, self.patch + 1)

        raise VersionError("Unsupported version increment")

    def to_dict(self):
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "prerelease": list(self.prerelease),
            "build": list(self.build),
            "version": str(self),
        }


@dataclass(frozen=True)
class VersionConstraint:
    operator: str
    version: Version

    def matches(self, candidate: Version) -> bool:
        comparisons = {
            "=": candidate == self.version,
            ">": candidate > self.version,
            ">=": candidate >= self.version,
            "<": candidate < self.version,
            "<=": candidate <= self.version,
        }

        if self.operator not in comparisons:
            raise VersionError(
                f"Unsupported operator: {self.operator}"
            )

        return comparisons[self.operator]


@dataclass
class Release:
    version: Version
    description: str
    change_type: ChangeType
    published: bool = False
    dependencies: list[str] = field(default_factory=list)


class ReleaseManager:
    def __init__(self, project: str):
        if not project or not project.strip():
            raise ReleaseError("Project name cannot be empty")

        self.project = project.strip()
        self.releases: dict[str, Release] = {}
        self.current_version: Optional[Version] = None

    def register(self, release: Release):
        key = str(release.version)

        if key in self.releases:
            raise ReleaseError(f"Version already registered: {key}")

        if self.current_version and release.version <= self.current_version:
            raise ReleaseError("Release must increase version precedence")

        self.releases[key] = release

    def publish(self, version: str):
        release = self.releases.get(version)

        if release is None:
            raise ReleaseError("Release does not exist")

        if release.published:
            raise ReleaseError("Release is already published")

        # Dependencies must be available before publication.
        for dependency in release.dependencies:
            if dependency not in self.releases:
                raise ReleaseError(
                    f"Missing dependency: {dependency}"
                )

            if not self.releases[dependency].published:
                raise ReleaseError(
                    f"Unpublished dependency: {dependency}"
                )

        release.published = True
        self.current_version = release.version

    def suggest_next_version(self, change: ChangeType) -> Version:
        if self.current_version is None:
            return Version(1, 0, 0)

        return self.current_version.increment(change)

    def history(self) -> list[dict]:
        return [
            {
                "version": str(release.version),
                "description": release.description,
                "change_type": release.change_type.value,
                "published": release.published,
            }
            for release in sorted(
                self.releases.values(),
                key=lambda item: item.version
            )
        ]

    def export_json(self, filename: str):
        destination = Path(filename)

        payload = {
            "project": self.project,
            "current_version": (
                str(self.current_version)
                if self.current_version else None
            ),
            "releases": self.history(),
        }

        # Write atomically to avoid leaving partially written files.
        temporary = destination.with_suffix(destination.suffix + ".tmp")

        try:
            temporary.write_text(
                json.dumps(payload, indent=2),
                encoding="utf-8",
            )
            temporary.replace(destination)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise


def determine_change(
    breaking: bool,
    feature: bool,
    bug_fix: bool,
) -> ChangeType:
    """Apply SemVer precedence to the highest-impact change."""

    if breaking:
        return ChangeType.MAJOR

    if feature:
        return ChangeType.MINOR

    if bug_fix:
        return ChangeType.PATCH

    raise VersionError("At least one release change must be specified")


def satisfies_all(
    version: Version,
    constraints: list[VersionConstraint],
) -> bool:
    """Evaluate a conjunction of version constraints."""

    return all(
        constraint.matches(version)
        for constraint in constraints
    )


def demonstrate():
    print("=" * 65)
    print("SEMANTIC VERSIONING 2.0.0")
    print("=" * 65)

    versions = [
        Version.parse("1.0.0-alpha"),
        Version.parse("1.0.0-alpha.1"),
        Version.parse("1.0.0-beta"),
        Version.parse("1.0.0-rc.1"),
        Version.parse("1.0.0"),
        Version.parse("1.0.1"),
        Version.parse("1.1.0"),
        Version.parse("2.0.0"),
    ]

    print("\n1. Version precedence")
    for version in sorted(versions):
        print(version)

    print("\n2. Version increment")
    current = Version.parse("2.4.6")

    for change in ChangeType:
        print(f"{change.value}: {current.increment(change)}")

    print("\n3. Compatibility evaluation")
    candidate = Version.parse("2.5.3")

    constraints = [
        VersionConstraint(">=", Version.parse("2.0.0")),
        VersionConstraint("<", Version.parse("3.0.0")),
    ]

    print(
        f"{candidate} satisfies constraints: "
        f"{satisfies_all(candidate, constraints)}"
    )

    print("\n4. Release management")
    manager = ReleaseManager("Inventory API")

    initial = Release(
        Version.parse("1.0.0"),
        "Initial stable API",
        ChangeType.MAJOR,
    )
    manager.register(initial)
    manager.publish("1.0.0")

    minor = Release(
        Version.parse("1.1.0"),
        "Added inventory search endpoint",
        ChangeType.MINOR,
    )
    manager.register(minor)
    manager.publish("1.1.0")

    patch = Release(
        Version.parse("1.1.1"),
        "Corrected pagination defect",
        ChangeType.PATCH,
    )
    manager.register(patch)
    manager.publish("1.1.1")

    print("Current version:", manager.current_version)

    for item in manager.history():
        print(item)

    print("\n5. Change classification")
    print(
        determine_change(
            breaking=False,
            feature=True,
            bug_fix=True,
        ).value
    )


class SemanticVersionTests(unittest.TestCase):

    def test_valid_version(self):
        self.assertEqual(
            str(Version.parse("1.2.3")),
            "1.2.3",
        )

    def test_invalid_version(self):
        invalid = [
            "01.2.3",
            "1.02.3",
            "1.2.03",
            "1.2",
            "v1.2.3",
            "1.2.3-01",
            "1.2.3+",
        ]

        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(VersionError):
                    Version.parse(value)

    def test_prerelease_precedence(self):
        sequence = [
            "1.0.0-alpha",
            "1.0.0-alpha.1",
            "1.0.0-alpha.beta",
            "1.0.0-beta",
            "1.0.0-beta.2",
            "1.0.0-beta.11",
            "1.0.0-rc.1",
            "1.0.0",
        ]

        parsed = [Version.parse(value) for value in sequence]
        self.assertEqual(parsed, sorted(parsed))

    def test_build_metadata_ignored_in_precedence(self):
        first = Version.parse("1.0.0+build.1")
        second = Version.parse("1.0.0+build.2")

        self.assertEqual(first, second)

    def test_increments(self):
        version = Version.parse("2.4.6")

        self.assertEqual(
            str(version.increment(ChangeType.MAJOR)),
            "3.0.0",
        )
        self.assertEqual(
            str(version.increment(ChangeType.MINOR)),
            "2.5.0",
        )
        self.assertEqual(
            str(version.increment(ChangeType.PATCH)),
            "2.4.7",
        )

    def test_constraint(self):
        version = Version.parse("2.5.0")

        self.assertTrue(
            VersionConstraint(">=", Version.parse("2.0.0"))
            .matches(version)
        )

    def test_change_classification(self):
        self.assertEqual(
            determine_change(True, True, True),
            ChangeType.MAJOR,
        )

    def test_release_publication(self):
        manager = ReleaseManager("Test API")

        release = Release(
            Version.parse("1.0.0"),
            "Initial release",
            ChangeType.MAJOR,
        )

        manager.register(release)
        manager.publish("1.0.0")

        self.assertTrue(release.published)

    def test_duplicate_release(self):
        manager = ReleaseManager("Test API")

        release = Release(
            Version.parse("1.0.0"),
            "Initial release",
            ChangeType.MAJOR,
        )

        manager.register(release)

        with self.assertRaises(ReleaseError):
            manager.register(release)


if __name__ == "__main__":
    demonstrate()

    print("\n6. Automated tests")
    unittest.main(argv=["semantic_versioning.py"], exit=False)
