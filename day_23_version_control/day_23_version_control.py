#!/usr/bin/env python3
"""
Git Fundamentals: Repositories, Commits, Objects, History, Branches, and Integrity

This standalone study program teaches Git fundamentals by building a small,
educational model of Git's content-addressed storage system.

The program covers:
- Working trees and repositories
- Staging and commits
- Snapshots and commit history
- Git-like object identifiers
- Blobs, trees, and commits
- Parent-child relationships
- Branch references
- Detached history
- Status and diffs
- Merge-base reasoning
- Three-way merging
- Integrity verification
- Content-addressable storage
- Common Git workflows and failure cases

It intentionally models important Git concepts rather than invoking Git itself.
That makes the internal mechanisms easier to inspect and experiment with.

Run with:
    python git_fundamentals.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha1
from typing import Dict, Iterable, List, Optional, Tuple
import copy
import difflib
import re


# ---------------------------------------------------------------------------
# 1. Fundamental terminology
# ---------------------------------------------------------------------------
#
# A Git repository contains objects and references.
#
# A working tree is the collection of files currently checked out.
# The index (staging area) records the exact content intended for the next
# commit.
# A commit points to a tree representing a complete project snapshot and
# optionally points to one or more parent commits.
#
# A branch is fundamentally a movable name pointing to a commit. In real Git,
# branch names are references stored under refs/heads/.
#
# This model uses SHA-1 because Git historically uses SHA-1 object IDs.
# Modern Git also supports SHA-256 repositories. SHA-1 here is educational.


def git_hash(object_type: str, content: bytes) -> str:
    """Calculate a Git-style object ID.

    Git hashes:
        <type> <length>\\0<content>

    The resulting digest identifies the content and its object type.
    """
    header = f"{object_type} {len(content)}\0".encode("utf-8")
    return sha1(header + content).hexdigest()


def short_hash(object_id: str, length: int = 8) -> str:
    return object_id[:length]


def normalize_path(path: str) -> str:
    """Normalize a simple repository path and reject unsafe paths."""
    path = path.replace("\\", "/").strip("/")
    if not path or path.startswith("../") or "/../" in path:
        raise ValueError(f"Invalid repository path: {path!r}")
    if path == ".." or "\x00" in path:
        raise ValueError(f"Invalid repository path: {path!r}")
    return path


def validate_branch_name(name: str) -> None:
    """Apply a deliberately conservative subset of Git branch rules."""
    if not name:
        raise ValueError("Branch name cannot be empty.")
    if name.startswith("-") or name.endswith(".") or name.endswith("/"):
        raise ValueError("Invalid branch name.")
    if ".." in name or " " in name or "~" in name or "^" in name:
        raise ValueError("Branch name contains a prohibited sequence.")


# ---------------------------------------------------------------------------
# 2. Educational Git object types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Blob:
    """A file's contents."""

    content: bytes

    @property
    def object_id(self) -> str:
        return git_hash("blob", self.content)


@dataclass(frozen=True)
class TreeEntry:
    """A directory entry stored by a tree."""

    path: str
    mode: str
    object_id: str
    entry_type: str = "blob"


@dataclass
class Tree:
    """A simplified tree containing file entries."""

    entries: Dict[str, TreeEntry] = field(default_factory=dict)

    def serialize(self) -> bytes:
        lines = []
        for path in sorted(self.entries):
            entry = self.entries[path]
            lines.append(
                f"{entry.mode} {entry.entry_type} "
                f"{entry.object_id} {entry.path}"
            )
        return "\n".join(lines).encode("utf-8")

    @property
    def object_id(self) -> str:
        return git_hash("tree", self.serialize())


@dataclass(frozen=True)
class Commit:
    """A simplified Git commit object."""

    tree_id: str
    parents: Tuple[str, ...]
    author: str
    message: str

    def serialize(self) -> bytes:
        lines = [f"tree {self.tree_id}"]
        lines.extend(f"parent {parent}" for parent in self.parents)
        lines.append(f"author {self.author}")
        lines.append("")
        lines.append(self.message)
        return "\n".join(lines).encode("utf-8")

    @property
    def object_id(self) -> str:
        return git_hash("commit", self.serialize())


# ---------------------------------------------------------------------------
# 3. Repository implementation
# ---------------------------------------------------------------------------

class GitRepository:
    """A compact educational model of a Git repository."""

    def __init__(self, author: str = "Student <student@example.com>") -> None:
        self.author = author

        # Object database:
        # object_id -> object instance
        self.objects: Dict[str, object] = {}

        # The working tree contains current file contents.
        self.working_tree: Dict[str, bytes] = {}

        # The index/staging area contains the next snapshot.
        self.index: Dict[str, bytes] = {}

        # Branch references are names pointing to commit IDs.
        self.branches: Dict[str, str] = {}

        # HEAD can either reference a branch or contain a commit ID directly.
        self.head_branch: Optional[str] = None
        self.detached_head: Optional[str] = None

    # -----------------------------------------------------------------------
    # Object database
    # -----------------------------------------------------------------------

    def write_blob(self, content: bytes) -> str:
        blob = Blob(content)
        self.objects[blob.object_id] = blob
        return blob.object_id

    def write_tree(self, files: Dict[str, bytes]) -> str:
        entries: Dict[str, TreeEntry] = {}

        for path, content in sorted(files.items()):
            normalized = normalize_path(path)
            blob_id = self.write_blob(content)
            entries[normalized] = TreeEntry(
                path=normalized,
                mode="100644",
                object_id=blob_id,
            )

        tree = Tree(entries)
        self.objects[tree.object_id] = tree
        return tree.object_id

    def write_commit(
        self,
        tree_id: str,
        parents: Iterable[str],
        message: str,
    ) -> str:
        commit = Commit(
            tree_id=tree_id,
            parents=tuple(parents),
            author=self.author,
            message=message.strip(),
        )
        if not commit.message:
            raise ValueError("Commit message cannot be empty.")

        self.objects[commit.object_id] = commit
        return commit.object_id

    # -----------------------------------------------------------------------
    # HEAD and branches
    # -----------------------------------------------------------------------

    def head(self) -> Optional[str]:
        """Return the commit currently referenced by HEAD."""
        if self.head_branch is not None:
            return self.branches.get(self.head_branch)
        return self.detached_head

    def init(self, branch: str = "main") -> None:
        """Initialize an empty repository."""
        validate_branch_name(branch)
        if self.branches:
            raise RuntimeError("Repository is already initialized.")
        self.branches[branch] = ""
        self.head_branch = branch

    def create_branch(self, name: str, start_point: Optional[str] = None) -> None:
        validate_branch_name(name)
        if name in self.branches:
            raise ValueError(f"Branch already exists: {name}")

        target = self.head() if start_point is None else start_point
        if target is None:
            raise ValueError("Cannot create branch without a starting commit.")

        self._require_commit(target)
        self.branches[name] = target

    def checkout(self, target: str) -> None:
        """Switch branches or enter detached HEAD mode."""
        if target in self.branches:
            self.head_branch = target
            self.detached_head = None
            target_commit = self.branches[target]
            if target_commit:
                self.restore_commit(target_commit)
            return

        self._require_commit(target)
        self.head_branch = None
        self.detached_head = target
        self.restore_commit(target)

    def _update_head(self, commit_id: str) -> None:
        if self.head_branch is not None:
            self.branches[self.head_branch] = commit_id
        else:
            self.detached_head = commit_id

    # -----------------------------------------------------------------------
    # Working tree and index
    # -----------------------------------------------------------------------

    def write_file(self, path: str, content: str | bytes) -> None:
        path = normalize_path(path)
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.working_tree[path] = content

    def delete_file(self, path: str) -> None:
        path = normalize_path(path)
        self.working_tree.pop(path, None)

    def stage(self, *paths: str) -> None:
        """Copy selected working-tree content into the index."""
        for path in paths:
            normalized = normalize_path(path)
            if normalized in self.working_tree:
                self.index[normalized] = self.working_tree[normalized]
            else:
                # Staging deletion is represented by removing the path from
                # the index when it was previously tracked.
                self.index.pop(normalized, None)

    def stage_all(self) -> None:
        """Make the index match the working tree."""
        self.index = copy.deepcopy(self.working_tree)

    def restore_commit(self, commit_id: str) -> None:
        """Replace the working tree with a committed snapshot."""
        snapshot = self.snapshot_from_commit(commit_id)
        self.working_tree = copy.deepcopy(snapshot)
        self.index = copy.deepcopy(snapshot)

    # -----------------------------------------------------------------------
    # Snapshots, commits, status, and log
    # -----------------------------------------------------------------------

    def snapshot_from_commit(self, commit_id: str) -> Dict[str, bytes]:
        commit = self.get_commit(commit_id)
        tree = self.get_tree(commit.tree_id)

        snapshot: Dict[str, bytes] = {}
        for path, entry in tree.entries.items():
            blob = self.objects.get(entry.object_id)
            if not isinstance(blob, Blob):
                raise RuntimeError("Tree references an invalid blob.")
            snapshot[path] = blob.content

        return snapshot

    def commit(self, message: str) -> str:
        """Create a commit from the current index."""
        if not self.index:
            raise RuntimeError("Nothing is staged.")

        tree_id = self.write_tree(self.index)
        parent = self.head()
        parents = [parent] if parent else []
        commit_id = self.write_commit(tree_id, parents, message)
        self._update_head(commit_id)
        self.working_tree = copy.deepcopy(self.index)
        return commit_id

    def status(self) -> Dict[str, List[str]]:
        """Compare working tree, index, and HEAD."""
        head_snapshot = self.snapshot_from_commit(self.head()) if self.head() else {}
        tracked_paths = set(head_snapshot) | set(self.index) | set(self.working_tree)

        staged = []
        modified = []
        deleted = []
        untracked = []

        for path in sorted(tracked_paths):
            head_content = head_snapshot.get(path)
            index_content = self.index.get(path)
            working_content = self.working_tree.get(path)

            if index_content != head_content:
                if index_content is None:
                    staged.append(f"deleted: {path}")
                else:
                    staged.append(f"staged: {path}")

            if working_content != index_content:
                if working_content is None and index_content is not None:
                    deleted.append(path)
                elif index_content is None and working_content is not None:
                    untracked.append(path)
                else:
                    modified.append(path)

        return {
            "staged": staged,
            "modified": modified,
            "deleted": deleted,
            "untracked": untracked,
        }

    def log(self, limit: int = 20) -> List[Tuple[str, str]]:
        """Return first-parent history from HEAD."""
        result = []
        current = self.head()

        while current and len(result) < limit:
            commit = self.get_commit(current)
            result.append((current, commit.message))
            current = commit.parents[0] if commit.parents else None

        return result

    # -----------------------------------------------------------------------
    # Inspection
    # -----------------------------------------------------------------------

    def get_commit(self, commit_id: str) -> Commit:
        self._require_commit(commit_id)
        obj = self.objects[commit_id]
        assert isinstance(obj, Commit)
        return obj

    def get_tree(self, tree_id: str) -> Tree:
        obj = self.objects.get(tree_id)
        if not isinstance(obj, Tree):
            raise KeyError(f"Tree not found: {tree_id}")
        return obj

    def show_commit(self, commit_id: Optional[str] = None) -> str:
        commit_id = commit_id or self.head()
        if not commit_id:
            return "No commits."

        commit = self.get_commit(commit_id)
        lines = [
            f"commit {commit.object_id}",
            f"tree   {commit.tree_id}",
            f"author {commit.author}",
        ]
        for parent in commit.parents:
            lines.append(f"parent {parent}")
        lines.extend(["", commit.message])
        return "\n".join(lines)

    def diff(
        self,
        old_snapshot: Dict[str, bytes],
        new_snapshot: Dict[str, bytes],
    ) -> str:
        """Produce a readable text diff for UTF-8 files."""
        lines: List[str] = []

        for path in sorted(set(old_snapshot) | set(new_snapshot)):
            old = old_snapshot.get(path, b"").decode("utf-8", errors="replace")
            new = new_snapshot.get(path, b"").decode("utf-8", errors="replace")

            if old == new:
                continue

            diff_lines = difflib.unified_diff(
                old.splitlines(),
                new.splitlines(),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
                lineterm="",
            )
            lines.extend(diff_lines)

        return "\n".join(lines) if lines else "No differences."

    # -----------------------------------------------------------------------
    # Graph algorithms
    # -----------------------------------------------------------------------

    def ancestors(self, commit_id: Optional[str]) -> Dict[str, int]:
        """Return reachable commits with shortest parent distance."""
        if not commit_id:
            return {}

        distances = {commit_id: 0}
        queue = [commit_id]

        while queue:
            current = queue.pop(0)
            distance = distances[current]
            commit = self.get_commit(current)

            for parent in commit.parents:
                if parent not in distances:
                    distances[parent] = distance + 1
                    queue.append(parent)

        return distances

    def merge_base(self, first: str, second: str) -> Optional[str]:
        """Find a nearest common ancestor using ancestor distances."""
        first_ancestors = self.ancestors(first)
        second_ancestors = self.ancestors(second)

        common = set(first_ancestors) & set(second_ancestors)
        if not common:
            return None

        return min(
            common,
            key=lambda commit_id: (
                max(first_ancestors[commit_id], second_ancestors[commit_id]),
                first_ancestors[commit_id] + second_ancestors[commit_id],
            ),
        )

    # -----------------------------------------------------------------------
    # Integrity and educational merge support
    # -----------------------------------------------------------------------

    def verify_integrity(self) -> List[str]:
        """Recompute all object IDs and report corrupt objects."""
        problems = []

        for object_id, obj in self.objects.items():
            if isinstance(obj, Blob):
                expected = obj.object_id
            elif isinstance(obj, Tree):
                expected = obj.object_id
            elif isinstance(obj, Commit):
                expected = obj.object_id
            else:
                problems.append(f"Unknown object type: {object_id}")
                continue

            if expected != object_id:
                problems.append(
                    f"Corrupt object {object_id}: expected {expected}"
                )

        for branch, commit_id in self.branches.items():
            if commit_id and commit_id not in self.objects:
                problems.append(
                    f"Branch {branch!r} points to missing object {commit_id}."
                )

        return problems

    def three_way_merge_snapshots(
        self,
        base: Dict[str, bytes],
        ours: Dict[str, bytes],
        theirs: Dict[str, bytes],
    ) -> Tuple[Dict[str, bytes], List[str]]:
        """Perform a simplified three-way file merge.

        A conflict occurs when both sides changed a file differently from
        the common base.
        """
        merged: Dict[str, bytes] = {}
        conflicts: List[str] = []

        paths = set(base) | set(ours) | set(theirs)

        for path in sorted(paths):
            base_value = base.get(path)
            ours_value = ours.get(path)
            theirs_value = theirs.get(path)

            if ours_value == theirs_value:
                if ours_value is not None:
                    merged[path] = ours_value
            elif ours_value == base_value:
                if theirs_value is not None:
                    merged[path] = theirs_value
            elif theirs_value == base_value:
                if ours_value is not None:
                    merged[path] = ours_value
            else:
                conflicts.append(path)

        return merged, conflicts

    def _require_commit(self, commit_id: str) -> None:
        obj = self.objects.get(commit_id)
        if not isinstance(obj, Commit):
            raise KeyError(f"Commit not found: {commit_id}")


# ---------------------------------------------------------------------------
# 4. Beginner demonstration: repository lifecycle
# ---------------------------------------------------------------------------

def demonstrate_basic_workflow() -> GitRepository:
    print("=" * 72)
    print("1. BASIC GIT WORKFLOW")
    print("=" * 72)

    repo = GitRepository()
    repo.init("main")

    print("Repository initialized.")
    print(f"Current branch: {repo.head_branch}")
    print(f"HEAD: {repo.head()}")

    repo.write_file("README.md", "# Version Control\n")
    repo.write_file("app.py", 'print("Hello, Git")\n')

    print("\nAfter creating files:")
    print(repo.status())

    repo.stage("README.md", "app.py")
    print("\nAfter staging:")
    print(repo.status())

    first_commit = repo.commit("Create initial project")
    print("\nCreated commit:")
    print(short_hash(first_commit))

    repo.write_file("app.py", 'print("Hello, Git version 2")\n')
    print("\nAfter modifying app.py:")
    print(repo.status())

    repo.stage("app.py")
    second_commit = repo.commit("Update application message")

    print("\nHistory:")
    for commit_id, message in repo.log():
        print(f"{short_hash(commit_id)} {message}")

    print("\nSecond commit details:")
    print(repo.show_commit(second_commit))

    return repo


# ---------------------------------------------------------------------------
# 5. Demonstrate staging as a separate snapshot
# ---------------------------------------------------------------------------

def demonstrate_index() -> None:
    print("\n" + "=" * 72)
    print("2. WORKING TREE VS INDEX VS COMMIT")
    print("=" * 72)

    repo = GitRepository()
    repo.init()

    repo.write_file("a.txt", "A\n")
    repo.write_file("b.txt", "B\n")
    repo.stage_all()
    repo.commit("Initial files")

    repo.write_file("a.txt", "A changed\n")
    repo.write_file("b.txt", "B changed\n")

    # Only a.txt enters the next commit.
    repo.stage("a.txt")

    print("Status after changing two files but staging one:")
    for category, values in repo.status().items():
        print(f"{category}: {values}")

    commit_id = repo.commit("Change only a.txt")
    snapshot = repo.snapshot_from_commit(commit_id)

    print("\nCommitted snapshot:")
    for path, content in snapshot.items():
        print(f"{path}: {content.decode().rstrip()}")

    print("\nNotice that b.txt remains modified in the working tree.")
    print("This is why the index is an important Git concept.")


# ---------------------------------------------------------------------------
# 6. Demonstrate object model
# ---------------------------------------------------------------------------

def demonstrate_objects(repo: GitRepository) -> None:
    print("\n" + "=" * 72)
    print("3. GIT-LIKE OBJECT DATABASE")
    print("=" * 72)

    head = repo.head()
    if not head:
        return

    commit = repo.get_commit(head)
    tree = repo.get_tree(commit.tree_id)

    print(f"HEAD commit: {short_hash(head)}")
    print(f"Commit tree: {short_hash(commit.tree_id)}")

    print("\nTree entries:")
    for path, entry in tree.entries.items():
        print(
            f"  {entry.mode} {entry.entry_type} "
            f"{short_hash(entry.object_id)} {path}"
        )

    print("\nObject counts:")
    counts = {"blob": 0, "tree": 0, "commit": 0}

    for obj in repo.objects.values():
        if isinstance(obj, Blob):
            counts["blob"] += 1
        elif isinstance(obj, Tree):
            counts["tree"] += 1
        elif isinstance(obj, Commit):
            counts["commit"] += 1

    for kind, count in counts.items():
        print(f"  {kind}: {count}")

    print(
        "\nA commit points to a tree, and the tree points to file blobs. "
        "The commit also records parent commit IDs."
    )


# ---------------------------------------------------------------------------
# 7. Branching demonstration
# ---------------------------------------------------------------------------

def demonstrate_branches() -> None:
    print("\n" + "=" * 72)
    print("4. BRANCHES AND HISTORY")
    print("=" * 72)

    repo = GitRepository()
    repo.init("main")

    repo.write_file("app.txt", "base\n")
    repo.stage_all()
    base = repo.commit("Create base")

    repo.create_branch("feature")

    repo.write_file("app.txt", "main change\n")
    repo.stage("app.txt")
    main_commit = repo.commit("Update main")

    repo.checkout("feature")
    repo.write_file("app.txt", "feature change\n")
    repo.stage("app.txt")
    feature_commit = repo.commit("Develop feature")

    print(f"Base:    {short_hash(base)}")
    print(f"Main:    {short_hash(main_commit)}")
    print(f"Feature: {short_hash(feature_commit)}")

    print("\nBranch references:")
    for branch, commit_id in repo.branches.items():
        print(f"  {branch}: {short_hash(commit_id)}")

    print(
        "\nThe branch names identify different tips of related commit history. "
        "The commits themselves are immutable objects."
    )


# ---------------------------------------------------------------------------
# 8. Diff and edge cases
# ---------------------------------------------------------------------------

def demonstrate_diff_and_edge_cases() -> None:
    print("\n" + "=" * 72)
    print("5. DIFFS AND EDGE CASES")
    print("=" * 72)

    repo = GitRepository()
    repo.init()

    repo.write_file(
        "config.txt",
        "host=localhost\nport=8000\nmode=development\n",
    )
    repo.stage_all()
    first = repo.commit("Add configuration")

    old_snapshot = repo.snapshot_from_commit(first)

    repo.write_file(
        "config.txt",
        "host=localhost\nport=8080\nmode=production\n",
    )
    new_snapshot = copy.deepcopy(repo.working_tree)

    print(repo.diff(old_snapshot, new_snapshot))

    print("\nTesting invalid branch name:")
    try:
        repo.create_branch("bad..name")
    except ValueError as exc:
        print(f"Caught expected error: {exc}")

    print("\nTesting commit without staging:")
    empty_repo = GitRepository()
    empty_repo.init()
    try:
        empty_repo.commit("Nothing here")
    except RuntimeError as exc:
        print(f"Caught expected error: {exc}")

    print("\nTesting missing commit:")
    try:
        repo.checkout("0" * 40)
    except KeyError as exc:
        print(f"Caught expected error: {exc}")


# ---------------------------------------------------------------------------
# 9. Three-way merge reasoning
# ---------------------------------------------------------------------------

def demonstrate_three_way_merge() -> None:
    print("\n" + "=" * 72)
    print("6. THREE-WAY MERGE")
    print("=" * 72)

    repo = GitRepository()
    repo.init()

    repo.write_file("document.txt", "line 1\nline 2\n")
    repo.stage_all()
    base_commit = repo.commit("Create document")

    repo.create_branch("feature")

    repo.write_file("document.txt", "line 1\nmain change\n")
    repo.stage("document.txt")
    main_commit = repo.commit("Change second line on main")

    repo.checkout("feature")
    repo.write_file("document.txt", "line 1\nfeature change\n")
    repo.stage("document.txt")
    feature_commit = repo.commit("Change second line on feature")

    base = repo.snapshot_from_commit(base_commit)
    ours = repo.snapshot_from_commit(main_commit)
    theirs = repo.snapshot_from_commit(feature_commit)

    merged, conflicts = repo.three_way_merge_snapshots(base, ours, theirs)

    print(f"Base:    {short_hash(base_commit)}")
    print(f"Main:    {short_hash(main_commit)}")
    print(f"Feature: {short_hash(feature_commit)}")

    print(f"\nCommon ancestor: {short_hash(repo.merge_base(main_commit, feature_commit))}")
    print(f"Conflicts: {conflicts}")

    if conflicts:
        print(
            "The two branches changed the same file differently relative "
            "to their common base, so automatic merging requires human input."
        )
    else:
        print("Merged snapshot:")
        for path, content in merged.items():
            print(path, content.decode().rstrip())


# ---------------------------------------------------------------------------
# 10. Integrity verification
# ---------------------------------------------------------------------------

def demonstrate_integrity() -> None:
    print("\n" + "=" * 72)
    print("7. OBJECT INTEGRITY")
    print("=" * 72)

    repo = GitRepository()
    repo.init()

    repo.write_file("data.txt", "important data\n")
    repo.stage_all()
    commit_id = repo.commit("Store important data")

    print(f"Commit: {short_hash(commit_id)}")
    print("Integrity before corruption:", repo.verify_integrity())

    commit = repo.get_commit(commit_id)

    # Replacing the object with a modified commit demonstrates why content
    # hashing detects changes.
    corrupted = Commit(
        tree_id=commit.tree_id,
        parents=commit.parents,
        author=commit.author,
        message="Tampered message",
    )
    repo.objects[commit_id] = corrupted

    problems = repo.verify_integrity()
    print("Integrity after simulated corruption:")
    for problem in problems:
        print(" ", problem)


# ---------------------------------------------------------------------------
# 11. Git command mapping
# ---------------------------------------------------------------------------

def print_real_git_workflow() -> None:
    print("\n" + "=" * 72)
    print("8. REAL GIT COMMANDS AND THEIR PURPOSES")
    print("=" * 72)

    commands = [
        ("git init", "Create a new repository in the current directory."),
        ("git status", "Inspect working-tree and staging-area state."),
        ("git add file.txt", "Stage a file for the next commit."),
        ("git add .", "Stage changes under the current directory."),
        ("git commit -m \"message\"", "Create a permanent history entry."),
        ("git log", "Inspect commit history."),
        ("git diff", "Compare working-tree changes."),
        ("git diff --staged", "Inspect changes staged for commit."),
        ("git branch", "List local branches."),
        ("git switch -c feature", "Create and switch to a branch."),
        ("git switch main", "Switch to an existing branch."),
        ("git merge feature", "Merge another branch into the current branch."),
        ("git restore file.txt", "Restore a file from a known Git state."),
        ("git show <commit>", "Inspect a commit and its associated data."),
        ("git status --short", "Display compact status information."),
    ]

    for command, purpose in commands:
        print(f"{command:<32} {purpose}")


# ---------------------------------------------------------------------------
# 12. Common mistakes and debugging checks
# ---------------------------------------------------------------------------

def print_common_mistakes() -> None:
    print("\n" + "=" * 72)
    print("9. COMMON MISTAKES")
    print("=" * 72)

    mistakes = [
        (
            "Editing a file after staging it",
            "The index keeps the earlier staged version. "
            "Stage the file again if the later edit should be committed.",
        ),
        (
            "Assuming git add means git commit",
            "git add prepares the next snapshot; git commit records it.",
        ),
        (
            "Committing generated secrets",
            "Credentials should never be committed. Rotate exposed secrets "
            "and use appropriate secret-management practices.",
        ),
        (
            "Using unclear commit messages",
            "A useful message identifies the meaningful change represented "
            "by the commit.",
        ),
        (
            "Working directly on the wrong branch",
            "Check git status and the current branch before making changes.",
        ),
        (
            "Assuming a branch is a permanent copy",
            "A branch is primarily a movable reference to a commit history.",
        ),
        (
            "Deleting a file and expecting Git to forget it immediately",
            "A deletion must become part of a commit to become historical state.",
        ),
        (
            "Ignoring uncommitted changes before switching",
            "Some operations can overwrite or conflict with local changes. "
            "Inspect status first.",
        ),
    ]

    for mistake, explanation in mistakes:
        print(f"\nMistake: {mistake}")
        print(f"Reason:  {explanation}")


# ---------------------------------------------------------------------------
# 13. Advanced conceptual notes
# ---------------------------------------------------------------------------

def print_advanced_notes() -> None:
    print("\n" + "=" * 72)
    print("10. ADVANCED CONCEPTS")
    print("=" * 72)

    notes = {
        "Immutability":
            "Git objects are identified by their content hash. Changing "
            "content changes the object ID.",
        "Snapshots":
            "A commit describes a project state through a tree rather than "
            "storing only a sequence of textual edits.",
        "DAG":
            "Commit history forms a directed acyclic graph because commits "
            "refer to earlier parents.",
        "References":
            "Branches and tags are names that make particular objects easy "
            "to locate.",
        "HEAD":
            "HEAD identifies the currently checked-out line of development "
            "or a specific commit in detached mode.",
        "Staging":
            "The index allows a user to construct the exact next snapshot "
            "instead of committing every working-tree modification.",
        "Merge":
            "Three-way merging compares a common ancestor with both branch "
            "tips to determine compatible and conflicting changes.",
        "Distributed model":
            "A clone contains repository history locally, so many operations "
            "do not require network access.",
        "Remote":
            "A remote is a named reference to another repository location. "
            "Fetch and push transfer objects and references.",
        "Reflog":
            "Real Git records local reference movements in reflogs, which "
            "can help recover commits that are no longer reachable by a branch.",
    }

    for topic, explanation in notes.items():
        print(f"{topic}: {explanation}")


# ---------------------------------------------------------------------------
# 14. Small self-tests
# ---------------------------------------------------------------------------

def run_tests() -> None:
    print("\n" + "=" * 72)
    print("11. SELF-TESTS")
    print("=" * 72)

    repo = GitRepository()
    repo.init()

    repo.write_file("test.txt", "hello\n")
    repo.stage("test.txt")
    first = repo.commit("Initial test")

    assert repo.head() == first
    assert repo.snapshot_from_commit(first)["test.txt"] == b"hello\n"

    repo.write_file("test.txt", "changed\n")
    assert repo.status()["modified"] == ["test.txt"]

    repo.stage("test.txt")
    assert repo.status()["modified"] == []

    second = repo.commit("Change test")
    assert repo.get_commit(second).parents == (first,)

    repo.create_branch("feature")
    assert repo.branches["feature"] == second

    repo.checkout("feature")
    assert repo.head_branch == "feature"

    repo.checkout(second)
    assert repo.head_branch is None
    assert repo.detached_head == second

    assert repo.verify_integrity() == []

    print("All assertions passed.")


# ---------------------------------------------------------------------------
# 15. Main program
# ---------------------------------------------------------------------------

def main() -> None:
    repo = demonstrate_basic_workflow()
    demonstrate_index()
    demonstrate_objects(repo)
    demonstrate_branches()
    demonstrate_diff_and_edge_cases()
    demonstrate_three_way_merge()
    demonstrate_integrity()
    print_real_git_workflow()
    print_common_mistakes()
    print_advanced_notes()
    run_tests()

    print("\n" + "=" * 72)
    print("END OF GIT FUNDAMENTALS STUDY PROGRAM")
    print("=" * 72)


if __name__ == "__main__":
    main()
