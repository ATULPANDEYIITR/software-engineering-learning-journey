from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterable
import json
import unittest


class TestLevel(Enum):
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"


@dataclass(frozen=True)
class User:
    user_id: int
    name: str
    email: str


@dataclass
class InMemoryUserRepository:
    users: dict[int, User] = field(default_factory=dict)

    def save(self, user: User) -> None:
        if user.user_id <= 0:
            raise ValueError("user_id must be positive")
        if not user.name.strip():
            raise ValueError("name must not be empty")
        if "@" not in user.email:
            raise ValueError("invalid email")
        if user.user_id in self.users:
            raise ValueError("user already exists")
        self.users[user.user_id] = user

    def find(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    def delete(self, user_id: int) -> bool:
        return self.users.pop(user_id, None) is not None


class UserService:
    """Application logic kept separate from persistence."""

    def __init__(self, repository: InMemoryUserRepository) -> None:
        self.repository = repository

    def register(self, user: User) -> User:
        self.repository.save(user)
        return user

    def get_user(self, user_id: int) -> User:
        user = self.repository.find(user_id)
        if user is None:
            raise LookupError(f"user {user_id} was not found")
        return user

    def export_user(self, user_id: int, directory: Path) -> Path:
        user = self.get_user(user_id)
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / f"user-{user.user_id}.json"
        output.write_text(
            json.dumps(
                {
                    "user_id": user.user_id,
                    "name": user.name,
                    "email": user.email,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return output


@dataclass(frozen=True)
class TestCase:
    name: str
    level: TestLevel
    function: Callable[[], None]


def is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.rsplit("@", 1)[-1] and " " not in email


def calculate_discount(total: float, percentage: float) -> float:
    if total < 0:
        raise ValueError("total cannot be negative")
    if not 0 <= percentage <= 100:
        raise ValueError("percentage must be between 0 and 100")
    return round(total * (1 - percentage / 100), 2)


class TestUnitFunctions(unittest.TestCase):
    def test_email_validation(self) -> None:
        self.assertTrue(is_valid_email("user@example.com"))
        self.assertFalse(is_valid_email("user example.com"))
        self.assertFalse(is_valid_email("user@example"))

    def test_discount(self) -> None:
        self.assertEqual(calculate_discount(1000, 20), 800)
        self.assertEqual(calculate_discount(1000, 0), 1000)
        self.assertEqual(calculate_discount(1000, 100), 0)

    def test_discount_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            calculate_discount(-1, 10)
        with self.assertRaises(ValueError):
            calculate_discount(100, 101)


class TestIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryUserRepository()
        self.service = UserService(self.repository)

    def test_service_persists_and_retrieves_user(self) -> None:
        user = User(1, "Atul", "atul@example.com")
        self.service.register(user)
        self.assertEqual(self.service.get_user(1), user)
        self.assertEqual(self.repository.find(1), user)

    def test_duplicate_user_is_rejected(self) -> None:
        user = User(1, "Atul", "atul@example.com")
        self.service.register(user)
        with self.assertRaises(ValueError):
            self.service.register(user)

    def test_missing_user_is_reported(self) -> None:
        with self.assertRaises(LookupError):
            self.service.get_user(99)


class TestSystemWorkflow(unittest.TestCase):
    def test_register_export_and_read_file(self) -> None:
        repository = InMemoryUserRepository()
        service = UserService(repository)

        with TemporaryDirectory() as temp:
            output = service.export_user if False else None
            service.register(User(7, "System User", "system@example.com"))
            path = service.export_user(7, Path(temp))

            data = json.loads(path.read_text(encoding="utf-8"))

            self.assertEqual(data["user_id"], 7)
            self.assertEqual(data["name"], "System User")
            self.assertEqual(data["email"], "system@example.com")


def run_custom_test_suite() -> None:
    """
    A small test runner illustrates test metadata without replacing
    unittest. It reports the three testing levels used by the example.
    """
    tests: Iterable[TestCase] = [
        TestCase(
            "valid email",
            TestLevel.UNIT,
            lambda: assert_true(is_valid_email("a@example.com")),
        ),
        TestCase(
            "service persistence",
            TestLevel.INTEGRATION,
            lambda: assert_equal(
                UserService(InMemoryUserRepository())
                .register(User(10, "Integration", "i@example.com"))
                .user_id,
                10,
            ),
        ),
    ]

    for test in tests:
        test.function()
        print(f"[PASS] {test.level.value:11} {test.name}")


def assert_true(value: bool) -> None:
    if not value:
        raise AssertionError("expected True")


def assert_equal(actual, expected) -> None:
    if actual != expected:
        raise AssertionError(f"expected {expected!r}, got {actual!r}")


def main() -> None:
    print("Testing Fundamentals: unit, integration, and system testing")
    print("\nCustom smoke checks:")
    run_custom_test_suite()

    print("\nAutomated unittest suite:")
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromModule(__import__(__name__))
    )

    if not result.wasSuccessful():
        raise SystemExit(1)

    print("\nAll tests passed.")
    print("Test design principles:")
    print("- Unit tests isolate deterministic business rules.")
    print("- Integration tests verify collaboration between components.")
    print("- System tests exercise the user-visible workflow and file boundary.")
    print("- Invalid input and failure paths are tested explicitly.")
    print("- Production suites should also isolate external services and protect test data.")


if __name__ == "__main__":
    main()
