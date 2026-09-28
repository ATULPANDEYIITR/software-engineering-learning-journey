#!/usr/bin/env python3
"""
Software Engineering Project: Build a Small CLI Application with Git

This standalone program demonstrates how a small command-line application can
be designed around a Git-backed project workflow.

Learning progression:
1. CLI fundamentals and command parsing
2. Data modeling and validation
3. File-system operations
4. Git repository initialization and inspection
5. Git status, staging, committing, branching, and history
6. Safe subprocess execution
7. Error handling and recovery
8. Separation of concerns
9. Testing
10. Production-oriented design considerations

The application manages simple software projects stored in a directory. Each
project is represented by a folder containing a project metadata file and a
Git repository.

Examples:
    python git_project_cli.py init demo
    python git_project_cli.py add-task demo "Implement login"
    python git_project_cli.py list-tasks demo
    python git_project_cli.py status demo
    python git_project_cli.py commit demo -m "Add login task"
    python git_project_cli.py log demo
    python git_project_cli.py branch demo feature-login
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional


APP_NAME = "git-project-cli"
METADATA_FILE = ".project.json"
TASKS_FILE = "tasks.json"
README_FILE = "README.md"


# ---------------------------------------------------------------------------
# Fundamental data modeling
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A small software-engineering task stored in the project."""

    id: int
    title: str
    completed: bool = False
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=int(data["id"]),
            title=str(data["title"]),
            completed=bool(data.get("completed", False)),
            created_at=str(data.get("created_at", "")),
        )


@dataclass
class ProjectMetadata:
    """Persistent information describing a managed project."""

    name: str
    created_at: str
    application_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# General utility functions
# ---------------------------------------------------------------------------

def utc_timestamp() -> str:
    """Return an unambiguous UTC timestamp suitable for persistent data."""

    return datetime.now(timezone.utc).isoformat()


def print_error(message: str) -> None:
    """Write errors to stderr so shell scripts can distinguish them."""

    print(f"Error: {message}", file=sys.stderr)


def run_command(
    command: list[str],
    cwd: Optional[Path] = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Execute an external command safely.

    A list of arguments is used instead of shell=True. This avoids shell
    interpolation and is an important security practice when arguments can
    originate from users.
    """

    try:
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Required executable was not found: {command[0]}"
        ) from exc
    except OSError as exc:
        raise RuntimeError(f"Could not execute {command[0]}: {exc}") from exc

    if check and result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}\n{details}"
        )

    return result


def ensure_directory(path: Path) -> None:
    """Create a directory tree if it does not already exist."""

    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    """Write readable JSON with deterministic formatting."""

    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def read_json(path: Path, default: Any) -> Any:
    """Read JSON or return a caller-provided default when the file is absent."""

    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in {path}: {exc}") from exc


# ---------------------------------------------------------------------------
# Project storage layer
# ---------------------------------------------------------------------------

class ProjectStore:
    """
    Encapsulates project file operations.

    Keeping persistence separate from CLI parsing is a basic software
    engineering principle: each component has a focused responsibility.
    """

    def __init__(self, root: Path):
        self.root = root.resolve()

    @property
    def metadata_path(self) -> Path:
        return self.root / METADATA_FILE

    @property
    def tasks_path(self) -> Path:
        return self.root / TASKS_FILE

    @property
    def readme_path(self) -> Path:
        return self.root / README_FILE

    def exists(self) -> bool:
        return self.root.is_dir() and self.metadata_path.exists()

    def load_metadata(self) -> ProjectMetadata:
        if not self.exists():
            raise RuntimeError(f"Not a managed project: {self.root}")

        data = read_json(self.metadata_path, {})
        return ProjectMetadata(
            name=str(data["name"]),
            created_at=str(data["created_at"]),
            application_version=str(
                data.get("application_version", "1.0.0")
            ),
        )

    def load_tasks(self) -> list[Task]:
        data = read_json(self.tasks_path, [])
        if not isinstance(data, list):
            raise RuntimeError("tasks.json must contain a JSON array.")
        return [Task.from_dict(item) for item in data]

    def save_tasks(self, tasks: Iterable[Task]) -> None:
        write_json(
            self.tasks_path,
            [task.to_dict() for task in tasks],
        )


# ---------------------------------------------------------------------------
# Git abstraction
# ---------------------------------------------------------------------------

class GitRepository:
    """
    Thin wrapper around the Git command-line interface.

    Git remains the source-control engine. This class provides an application
    boundary so the rest of the program does not need to know subprocess
    details.
    """

    def __init__(self, project_root: Path):
        self.root = project_root.resolve()

    def initialize(self) -> None:
        if (self.root / ".git").exists():
            return
        run_command(["git", "init"], cwd=self.root)

    def is_repository(self) -> bool:
        result = run_command(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=self.root,
            check=False,
        )
        return result.returncode == 0 and result.stdout.strip() == "true"

    def status(self) -> str:
        result = run_command(
            ["git", "status", "--short", "--branch"],
            cwd=self.root,
        )
        return result.stdout.rstrip()

    def add(self, paths: list[str]) -> None:
        if not paths:
            paths = ["."]
        run_command(["git", "add", "--", *paths], cwd=self.root)

    def commit(self, message: str) -> str:
        if not message.strip():
            raise ValueError("Commit message cannot be empty.")

        result = run_command(
            ["git", "commit", "-m", message],
            cwd=self.root,
        )
        return result.stdout.strip()

    def log(self, limit: int = 10) -> str:
        if limit < 1:
            raise ValueError("Log limit must be at least 1.")

        result = run_command(
            [
                "git",
                "log",
                f"-{limit}",
                "--date=short",
                "--pretty=format:%h | %ad | %an | %s",
            ],
            cwd=self.root,
        )
        return result.stdout.rstrip()

    def branch(self, branch_name: str) -> str:
        validate_branch_name(branch_name)

        result = run_command(
            ["git", "switch", "-c", branch_name],
            cwd=self.root,
        )
        return result.stdout.strip()

    def current_branch(self) -> str:
        result = run_command(
            ["git", "branch", "--show-current"],
            cwd=self.root,
        )
        return result.stdout.strip()

    def diff(self) -> str:
        result = run_command(
            ["git", "diff"],
            cwd=self.root,
        )
        return result.stdout


def validate_branch_name(name: str) -> None:
    """
    Apply conservative branch-name validation before passing the value to Git.

    Git itself has more detailed rules. Restricting the application to a
    simple portable subset makes the CLI easier to reason about.
    """

    if not name:
        raise ValueError("Branch name cannot be empty.")

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789"
        "-_/"
    )

    if any(character not in allowed for character in name):
        raise ValueError(
            "Branch name may contain only letters, numbers, '-', '_' and '/'."
        )

    if name.startswith("/") or name.endswith("/"):
        raise ValueError("Branch name cannot start or end with '/'.")


# ---------------------------------------------------------------------------
# Application service layer
# ---------------------------------------------------------------------------

class ProjectService:
    """Coordinates project storage and Git operations."""

    def create_project(self, path: Path) -> ProjectStore:
        path = path.resolve()

        if path.exists() and any(path.iterdir()):
            raise RuntimeError(
                f"Project directory already exists and is not empty: {path}"
            )

        ensure_directory(path)

        metadata = ProjectMetadata(
            name=path.name,
            created_at=utc_timestamp(),
        )

        store = ProjectStore(path)

        write_json(store.metadata_path, metadata.to_dict())
        store.save_tasks([])

        store.readme_path.write_text(
            f"# {metadata.name}\n\n"
            "This project is managed by git-project-cli.\n\n"
            "## Development\n\n"
            "Use Git to track changes and project tasks to organize work.\n",
            encoding="utf-8",
        )

        git = GitRepository(path)
        git.initialize()

        return store

    def add_task(self, store: ProjectStore, title: str) -> Task:
        title = title.strip()

        if not title:
            raise ValueError("Task title cannot be empty.")

        if len(title) > 200:
            raise ValueError("Task title cannot exceed 200 characters.")

        tasks = store.load_tasks()
        next_id = max((task.id for task in tasks), default=0) + 1

        task = Task(
            id=next_id,
            title=title,
            created_at=utc_timestamp(),
        )

        tasks.append(task)
        store.save_tasks(tasks)
        return task

    def complete_task(self, store: ProjectStore, task_id: int) -> Task:
        tasks = store.load_tasks()

        for task in tasks:
            if task.id == task_id:
                task.completed = True
                store.save_tasks(tasks)
                return task

        raise ValueError(f"Task {task_id} does not exist.")

    def remove_task(self, store: ProjectStore, task_id: int) -> None:
        tasks = store.load_tasks()
        remaining = [task for task in tasks if task.id != task_id]

        if len(remaining) == len(tasks):
            raise ValueError(f"Task {task_id} does not exist.")

        store.save_tasks(remaining)

    def list_tasks(self, store: ProjectStore) -> list[Task]:
        return store.load_tasks()


# ---------------------------------------------------------------------------
# CLI presentation
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description="Manage small software projects with Git.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser(
        "init",
        help="Create a project and initialize Git.",
    )
    init_parser.add_argument("path", type=Path)

    task_parser = subparsers.add_parser(
        "add-task",
        help="Add a development task.",
    )
    task_parser.add_argument("project", type=Path)
    task_parser.add_argument("title")

    list_parser = subparsers.add_parser(
        "list-tasks",
        help="Display project tasks.",
    )
    list_parser.add_argument("project", type=Path)

    complete_parser = subparsers.add_parser(
        "complete-task",
        help="Mark a task as completed.",
    )
    complete_parser.add_argument("project", type=Path)
    complete_parser.add_argument("task_id", type=int)

    remove_parser = subparsers.add_parser(
        "remove-task",
        help="Remove a task.",
    )
    remove_parser.add_argument("project", type=Path)
    remove_parser.add_argument("task_id", type=int)

    status_parser = subparsers.add_parser(
        "status",
        help="Show Git status.",
    )
    status_parser.add_argument("project", type=Path)

    commit_parser = subparsers.add_parser(
        "commit",
        help="Stage all project changes and create a Git commit.",
    )
    commit_parser.add_argument("project", type=Path)
    commit_parser.add_argument("-m", "--message", required=True)

    log_parser = subparsers.add_parser(
        "log",
        help="Display Git history.",
    )
    log_parser.add_argument("project", type=Path)
    log_parser.add_argument("-n", "--limit", type=int, default=10)

    branch_parser = subparsers.add_parser(
        "branch",
        help="Create and switch to a new Git branch.",
    )
    branch_parser.add_argument("project", type=Path)
    branch_parser.add_argument("name")

    diff_parser = subparsers.add_parser(
        "diff",
        help="Display unstaged changes.",
    )
    diff_parser.add_argument("project", type=Path)

    test_parser = subparsers.add_parser(
        "self-test",
        help="Run the built-in test suite.",
    )

    return parser


def load_store(project: Path) -> ProjectStore:
    store = ProjectStore(project)

    if not store.exists():
        raise RuntimeError(
            f"{project} is not a valid {APP_NAME} project."
        )

    return store


def print_tasks(tasks: list[Task]) -> None:
    if not tasks:
        print("No tasks.")
        return

    for task in tasks:
        marker = "x" if task.completed else " "
        print(f"[{marker}] {task.id}: {task.title}")


def execute_command(args: argparse.Namespace) -> int:
    service = ProjectService()

    if args.command == "init":
        store = service.create_project(args.path)
        print(f"Project created: {store.root}")
        print("Git repository initialized.")
        return 0

    if args.command == "self-test":
        return run_tests()

    store = load_store(args.project)
    git = GitRepository(store.root)

    if not git.is_repository():
        raise RuntimeError("The project does not contain a valid Git repository.")

    if args.command == "add-task":
        task = service.add_task(store, args.title)
        print(f"Added task {task.id}: {task.title}")

    elif args.command == "list-tasks":
        print_tasks(service.list_tasks(store))

    elif args.command == "complete-task":
        task = service.complete_task(store, args.task_id)
        print(f"Completed task {task.id}: {task.title}")

    elif args.command == "remove-task":
        service.remove_task(store, args.task_id)
        print(f"Removed task {args.task_id}.")

    elif args.command == "status":
        print(git.status())

    elif args.command == "commit":
        git.add(["."])
        print(git.commit(args.message))

    elif args.command == "log":
        print(git.log(args.limit))

    elif args.command == "branch":
        print(git.branch(args.name))
        print(f"Current branch: {git.current_branch()}")

    elif args.command == "diff":
        output = git.diff()
        print(output if output else "No unstaged changes.")

    return 0


# ---------------------------------------------------------------------------
# Automated tests
# ---------------------------------------------------------------------------

class ProjectServiceTests(unittest.TestCase):
    """Tests the application without relying on a user's existing project."""

    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.service = ProjectService()

    def tearDown(self) -> None:
        self.temp_directory.cleanup()

    def test_project_creation(self) -> None:
        project = self.root / "demo"
        store = self.service.create_project(project)

        self.assertTrue(store.exists())
        self.assertTrue((project / ".git").exists())
        self.assertEqual(store.load_tasks(), [])

    def test_add_and_complete_task(self) -> None:
        store = self.service.create_project(self.root / "demo")

        task = self.service.add_task(store, "Write tests")
        self.assertEqual(task.id, 1)
        self.assertFalse(task.completed)

        completed = self.service.complete_task(store, 1)
        self.assertTrue(completed.completed)

    def test_invalid_empty_task(self) -> None:
        store = self.service.create_project(self.root / "demo")

        with self.assertRaises(ValueError):
            self.service.add_task(store, "   ")

    def test_remove_task(self) -> None:
        store = self.service.create_project(self.root / "demo")
        self.service.add_task(store, "Task A")
        self.service.add_task(store, "Task B")

        self.service.remove_task(store, 1)

        tasks = self.service.list_tasks(store)
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].id, 2)


def run_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(
        ProjectServiceTests
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


# ---------------------------------------------------------------------------
# Program entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return execute_command(args)
    except (RuntimeError, ValueError) as exc:
        print_error(str(exc))
        return 1
    except KeyboardInterrupt:
        print_error("Operation cancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
