Git Branching: branches, merge, rebase, conflicts, and advanced workflows.

This standalone study script teaches Git branching from beginner to advanced
level by creating and manipulating a real temporary Git repository.

Requirements:
    Python 3.9+
    Git installed and available on PATH

The script deliberately uses only the Python standard library.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


# ============================================================================
# 1. FUNDAMENTALS
# ============================================================================

def print_title(title: str) -> None:
    """Print a readable section heading."""
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def print_subtitle(title: str) -> None:
    print(f"\n--- {title} ---")


def explain(text: str) -> None:
    """Print a compact conceptual explanation."""
    print(text)


def run_command(
    command: Sequence[str],
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Execute a Git or operating-system command.

    capture_output=True lets the study program inspect command output.
    text=True converts byte output to strings.
    """
    result = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.stdout:
        print(result.stdout.rstrip())

    if result.stderr:
        print(result.stderr.rstrip())

    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: "
            f"{' '.join(command)}"
        )

    return result


def git(
    repository: Path,
    *arguments: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a Git command inside a repository."""
    return run_command(
        ["git", *arguments],
        cwd=repository,
        check=check,
    )


def write_file(repository: Path, relative_path: str, content: str) -> None:
    """Create or replace a file inside the repository."""
    path = repository / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_file(repository: Path, relative_path: str) -> str:
    return (repository / relative_path).read_text(encoding="utf-8")


def commit(
    repository: Path,
    message: str,
) -> None:
    """Create a Git commit after staging all changes."""
    git(repository, "add", ".")
    git(repository, "commit", "-m", message)


# ============================================================================
# 2. GIT'S BRANCHING MODEL
# ============================================================================

@dataclass(frozen=True)
class CommitRecord:
    """A small Python representation of a conceptual Git commit."""

    identifier: str
    parent: str | None
    message: str


def demonstrate_commit_graph_concept() -> None:
    print_title("1. Commit Graph and Branch Fundamentals")

    explain(
        "A Git branch is a movable reference to a commit. A branch does not "
        "contain a second copy of the entire repository. The branch name "
        "normally points at the latest commit in that line of development."
    )

    explain(
        "A commit points to one or more parent commits. A normal commit has "
        "one parent. A merge commit usually has two or more parents. A branch "
        "can therefore be understood as a named pointer into a directed "
        "acyclic commit graph."
    )

    commits = [
        CommitRecord("A", None, "initial commit"),
        CommitRecord("B", "A", "add application"),
        CommitRecord("C", "B", "add tests"),
    ]

    for item in commits:
        print(
            f"Commit {item.identifier}: "
            f"parent={item.parent!r}, message={item.message!r}"
        )

    print(
        """
Conceptual graph:

A -- B -- C
          ^
          main

If a new branch is created at C:

A -- B -- C
          ^\\
          | feature
          main

The two branch names are references. Creating a branch is therefore
usually inexpensive.
""".strip()
    )


# ============================================================================
# 3. INITIALIZE A REAL REPOSITORY
# ============================================================================

def create_repository() -> Path:
    """
    Create a temporary real Git repository.

    The directory is returned to the caller. The caller owns its lifecycle.
    """
    repository = Path(tempfile.mkdtemp(prefix="git-branching-study-"))

    git(repository, "init", "-b", "main")
    git(repository, "config", "user.name", "Git Branching Study")
    git(repository, "config", "user.email", "git-study@example.invalid")

    write_file(
        repository,
        "README.txt",
        "Git Branching Study Repository\n",
    )
    write_file(
        repository,
        "app.txt",
        "version=1\nstatus=stable\n",
    )
    commit(repository, "Create initial application")

    return repository


def show_repository_state(repository: Path) -> None:
    print_subtitle("Repository state")
    git(repository, "status", "--short", "--branch")
    print("\nBranches:")
    git(repository, "branch", "-vv")
    print("\nRecent history:")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
        "-12",
    )


# ============================================================================
# 4. BASIC BRANCH OPERATIONS
# ============================================================================

def demonstrate_basic_branches(repository: Path) -> None:
    print_title("2. Creating, Switching, Renaming, and Deleting Branches")

    explain(
        "The classic commands are: git branch to inspect or create branches, "
        "git switch to move HEAD to another branch, and git branch -d to "
        "delete a safely merged local branch."
    )

    print_subtitle("List branches")
    git(repository, "branch")

    print_subtitle("Create a feature branch")
    git(repository, "switch", "-c", "feature/login")
    write_file(
        repository,
        "login.txt",
        "login validation enabled\n",
    )
    commit(repository, "Add login validation")

    print_subtitle("Return to main")
    git(repository, "switch", "main")

    explain(
        "The commit made on feature/login is not part of main merely because "
        "the file exists in the repository history. Each branch points to a "
        "different commit until the histories are integrated."
    )

    print_subtitle("Inspect both branch histories")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    print_subtitle("Create and rename a temporary branch")
    git(repository, "switch", "-c", "temporary")
    git(repository, "switch", "main")
    git(repository, "branch", "-m", "temporary", "renamed-temporary")

    print_subtitle("Delete the renamed branch")
    git(repository, "branch", "-d", "renamed-temporary")

    print_subtitle("Inspect branches")
    git(repository, "branch", "--verbose")


# ============================================================================
# 5. FAST-FORWARD MERGE
# ============================================================================

def demonstrate_fast_forward_merge(repository: Path) -> None:
    print_title("3. Fast-Forward Merge")

    explain(
        "A fast-forward merge occurs when the receiving branch has no new "
        "commit since the feature branch diverged. Git can simply move the "
        "receiving branch pointer forward. No merge commit is required."
    )

    git(repository, "switch", "main")
    git(repository, "switch", "-c", "feature/search")

    write_file(
        repository,
        "search.txt",
        "search algorithm: linear\n",
    )
    commit(repository, "Add search feature")

    print_subtitle("History before merge")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    git(repository, "switch", "main")
    git(repository, "merge", "feature/search")

    print_subtitle("History after fast-forward merge")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    # The feature branch can now be deleted because its changes are in main.
    git(repository, "branch", "-d", "feature/search")


# ============================================================================
# 6. TRUE MERGE COMMIT
# ============================================================================

def demonstrate_merge_commit(repository: Path) -> None:
    print_title("4. Three-Way Merge and Merge Commits")

    explain(
        "When both branches have advanced after their common ancestor, Git "
        "cannot simply move one pointer. It performs a three-way merge using "
        "the common ancestor and the two branch tips."
    )

    git(repository, "switch", "main")
    write_file(
        repository,
        "app.txt",
        "version=2\nstatus=stable\nmain-change=yes\n",
    )
    commit(repository, "Update application on main")

    git(repository, "switch", "-c", "feature/reporting")
    write_file(
        repository,
        "report.txt",
        "reporting enabled\n",
    )
    commit(repository, "Add reporting")

    git(repository, "switch", "main")
    write_file(
        repository,
        "operations.txt",
        "monitoring enabled\n",
    )
    commit(repository, "Add monitoring")

    print_subtitle("Diverged history")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    git(repository, "merge", "--no-ff", "feature/reporting", "-m",
        "Merge reporting feature")

    print_subtitle("Merge commit created with --no-ff")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    git(repository, "branch", "-d", "feature/reporting")

    explain(
        "The --no-ff option forces a merge commit even when a fast-forward "
        "would be possible. Teams may use this when they want merge commits "
        "to preserve explicit feature boundaries in project history."
    )


# ============================================================================
# 7. MERGE CONFLICTS
# ============================================================================

def demonstrate_conflict(repository: Path) -> None:
    print_title("5. Merge Conflicts")

    explain(
        "A conflict occurs when Git cannot safely combine changes. A common "
        "case is two branches modifying overlapping lines of the same file "
        "in incompatible ways. Git stops the merge and asks the developer to "
        "resolve the affected files."
    )

    git(repository, "switch", "main")
    write_file(
        repository,
        "config.txt",
        "timeout=30\nmode=production\n",
    )
    commit(repository, "Add shared configuration")

    git(repository, "switch", "-c", "feature/config")
    write_file(
        repository,
        "config.txt",
        "timeout=60\nmode=production\n",
    )
    commit(repository, "Increase feature timeout")

    git(repository, "switch", "main")
    write_file(
        repository,
        "config.txt",
        "timeout=15\nmode=production\n",
    )
    commit(repository, "Reduce production timeout")

    result = git(
        repository,
        "merge",
        "feature/config",
        check=False,
    )

    if result.returncode == 0:
        raise RuntimeError("The demonstration expected a merge conflict.")

    print_subtitle("Conflict detected")
    print(read_file(repository, "config.txt"))

    explain(
        "Conflict markers have the general structure:\n"
        "<<<<<<< HEAD\n"
        "current branch version\n"
        "=======\n"
        "incoming branch version\n"
        ">>>>>>> feature/config\n"
    )

    # Resolve the conflict explicitly.
    write_file(
        repository,
        "config.txt",
        "timeout=30\nmode=production\n",
    )

    print_subtitle("Resolved content")
    print(read_file(repository, "config.txt"))

    git(repository, "add", "config.txt")
    git(repository, "commit", "-m", "Resolve configuration conflict")

    print_subtitle("History after conflict resolution")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    git(repository, "branch", "-d", "feature/config")

    explain(
        "The important workflow is: inspect the conflict, edit the affected "
        "files, remove conflict markers, test the result, stage the resolved "
        "files with git add, then complete the merge with git commit. During "
        "an unresolved merge, git merge --abort can return the working tree "
        "to its pre-merge state."
    )


# ============================================================================
# 8. REBASE
# ============================================================================

def demonstrate_rebase(repository: Path) -> None:
    print_title("6. Rebase")

    explain(
        "Rebase takes commits from one line of development and reapplies them "
        "on top of another base commit. The resulting commits have new "
        "identities because their parent relationship changes."
    )

    git(repository, "switch", "main")
    write_file(
        repository,
        "release.txt",
        "release=1\n",
    )
    commit(repository, "Prepare release")

    git(repository, "switch", "-c", "feature/rebase-demo")
    write_file(
        repository,
        "feature.txt",
        "step=one\n",
    )
    commit(repository, "Feature step one")

    write_file(
        repository,
        "feature.txt",
        "step=two\n",
    )
    commit(repository, "Feature step two")

    git(repository, "switch", "main")
    write_file(
        repository,
        "main-progress.txt",
        "main-progress=yes\n",
    )
    commit(repository, "Advance main")

    print_subtitle("Diverged history before rebase")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    git(repository, "switch", "feature/rebase-demo")
    git(repository, "rebase", "main")

    print_subtitle("Linearized history after rebase")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
    )

    explain(
        "After rebase, feature/rebase-demo contains new versions of its "
        "feature commits whose parent is the updated main history. Rebase "
        "does not merge the old commits in place."
    )

    git(repository, "switch", "main")
    git(repository, "merge", "--ff-only", "feature/rebase-demo")
    git(repository, "branch", "-d", "feature/rebase-demo")


# ============================================================================
# 9. REBASE CONFLICTS
# ============================================================================

def demonstrate_rebase_conflict(repository: Path) -> None:
    print_title("7. Rebase Conflict and Recovery")

    explain(
        "Rebase can also produce conflicts. The difference is that Git stops "
        "while replaying a particular commit rather than while creating a "
        "merge commit."
    )

    git(repository, "switch", "main")
    write_file(
        repository,
        "policy.txt",
        "level=normal\n",
    )
    commit(repository, "Add policy")

    git(repository, "switch", "-c", "feature/rebase-conflict")
    write_file(
        repository,
        "policy.txt",
        "level=high\n",
    )
    commit(repository, "Raise feature policy")

    git(repository, "switch", "main")
    write_file(
        repository,
        "policy.txt",
        "level=low\n",
    )
    commit(repository, "Lower main policy")

    git(repository, "switch", "feature/rebase-conflict")

    result = git(
        repository,
        "rebase",
        "main",
        check=False,
    )

    if result.returncode == 0:
        raise RuntimeError("The demonstration expected a rebase conflict.")

    print_subtitle("Rebase conflict state")
    git(repository, "status", "--short", "--branch")
    print(read_file(repository, "policy.txt"))

    # Resolve the conflict and continue.
    write_file(
        repository,
        "policy.txt",
        "level=high\n",
    )
    git(repository, "add", "policy.txt")
    git(repository, "rebase", "--continue", check=False)

    # Git may require an editor for the replayed commit. Supplying the
    # sequence editor as an environment variable avoids interactive editing.
    # If continue still needs the message, retry with GIT_EDITOR=true.
    if (repository / ".git" / "rebase-merge").exists() or (
        repository / ".git" / "rebase-apply"
    ).exists():
        env = os.environ.copy()
        env["GIT_EDITOR"] = "true"
        subprocess.run(
            ["git", "rebase", "--continue"],
            cwd=repository,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    if (repository / ".git" / "rebase-merge").exists() or (
        repository / ".git" / "rebase-apply"
    ).exists():
        # The environment used for a commit message is sometimes editor
        # dependent. Finish deterministically by aborting the demonstration
        # if the repository is still in an unfinished rebase.
        git(repository, "rebase", "--abort", check=False)
        print(
            "The rebase was intentionally aborted after demonstrating the "
            "conflict state."
        )
    else:
        print_subtitle("Rebase completed after resolution")
        git(
            repository,
            "log",
            "--oneline",
            "--decorate",
            "--graph",
            "--all",
        )

    # The branch may have been rebased successfully. Remove it from main.
    git(repository, "switch", "main")
    git(repository, "branch", "-D", "feature/rebase-conflict")


# ============================================================================
# 10. DETACHED HEAD
# ============================================================================

def demonstrate_detached_head(repository: Path) -> None:
    print_title("8. Detached HEAD")

    explain(
        "HEAD normally points to the current branch. In detached HEAD state, "
        "HEAD points directly to a commit, tag, or another non-branch "
        "reference. This is useful for inspecting historical states, but a "
        "new commit made there can become difficult to find unless a branch "
        "is created."
    )

    current_commit = git(
        repository,
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    git(repository, "switch", "--detach", current_commit)

    print_subtitle("Detached HEAD status")
    git(repository, "status", "--short", "--branch")

    git(repository, "switch", "main")

    explain(
        "Modern Git also provides git switch for branch-oriented operations "
        "and git restore for many working-tree/file restoration operations. "
        "Older workflows commonly use git checkout for both jobs."
    )


# ============================================================================
# 11. BRANCH COMPARISON AND DIAGNOSTICS
# ============================================================================

def demonstrate_diagnostics(repository: Path) -> None:
    print_title("9. Branch Comparison and Diagnostic Commands")

    explain(
        "Branching becomes easier to reason about when you inspect the graph "
        "rather than relying only on the current directory contents."
    )

    print_subtitle("Current branch")
    git(repository, "branch", "--show-current")

    print_subtitle("All branches")
    git(repository, "branch", "--all", "--verbose")

    print_subtitle("Commit IDs")
    git(repository, "rev-parse", "HEAD")
    git(repository, "rev-parse", "main")

    print_subtitle("Files changed between two revisions")
    git(repository, "diff", "HEAD~1", "HEAD", "--stat")

    print_subtitle("Common ancestor")
    git(repository, "merge-base", "HEAD", "main")

    print_subtitle("Reachability")
    git(repository, "show-branch", "--more=5", "main", "HEAD")

    explain(
        "Useful diagnostic commands include git log --graph --decorate --all, "
        "git status, git diff, git show, git branch -vv, git merge-base, and "
        "git reflog. These commands expose different parts of repository "
        "state and history."
    )


# ============================================================================
# 12. REFL0G AND RECOVERY
# ============================================================================

def demonstrate_reflog(repository: Path) -> None:
    print_title("10. Reflog and Recovery")

    explain(
        "The reflog records local movements of references such as HEAD and "
        "branch pointers. It can help locate commits after operations such "
        "as reset or rebase appear to have removed them from normal branch "
        "history."
    )

    print_subtitle("Recent HEAD movements")
    git(repository, "reflog", "-8")

    explain(
        "Reflog entries are local administrative records. They are not a "
        "substitute for backups or a shared remote history, and their "
        "retention is governed by Git's reflog expiration settings."
    )


# ============================================================================
# 13. RESET, RESTORE, AND REVERT
# ============================================================================

def demonstrate_recovery_commands(repository: Path) -> None:
    print_title("11. Reset, Restore, and Revert")

    explain(
        "These commands solve different problems. git restore primarily "
        "changes working-tree or index contents. git reset moves references "
        "and can also alter the index and working tree depending on its mode. "
        "git revert creates a new commit that reverses an earlier commit."
    )

    # Create a throwaway branch so destructive demonstrations never alter
    # the main study history.
    git(repository, "switch", "main")
    git(repository, "switch", "-c", "recovery-demo")

    write_file(
        repository,
        "recovery.txt",
        "original\n",
    )
    commit(repository, "Create recovery example")

    write_file(
        repository,
        "recovery.txt",
        "working-tree-edit\n",
    )

    print_subtitle("Working tree before restore")
    print(read_file(repository, "recovery.txt"))
    git(repository, "restore", "recovery.txt")

    print_subtitle("Working tree after restore")
    print(read_file(repository, "recovery.txt"))

    write_file(
        repository,
        "recovery.txt",
        "committed-change\n",
    )
    commit(repository, "Create change to revert")

    git(repository, "revert", "--no-edit", "HEAD")

    print_subtitle("History after revert")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "-6",
    )

    git(repository, "switch", "main")
    git(repository, "branch", "-D", "recovery-demo")


# ============================================================================
# 14. CHERRY-PICK
# ============================================================================

def demonstrate_cherry_pick(repository: Path) -> None:
    print_title("12. Cherry-Pick")

    explain(
        "git cherry-pick applies the changes introduced by selected commits "
        "onto the current branch. It is useful when a specific fix is needed "
        "without merging an entire feature branch."
    )

    git(repository, "switch", "main")
    git(repository, "switch", "-c", "feature/security-fix")

    write_file(
        repository,
        "security.txt",
        "input-validation=enabled\n",
    )
    commit(repository, "Add input validation")

    fix_commit = git(
        repository,
        "rev-parse",
        "HEAD",
    ).stdout.strip()

    git(repository, "switch", "main")
    git(repository, "cherry-pick", fix_commit)

    print_subtitle("Main after cherry-picking a specific fix")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
        "-10",
    )

    git(repository, "branch", "-D", "feature/security-fix")


# ============================================================================
# 15. INTERACTIVE REBASE CONCEPTS
# ============================================================================

def explain_interactive_rebase() -> None:
    print_title("13. Interactive Rebase Concepts")

    explain(
        "Interactive rebase provides a commit-sequence editor. Typical "
        "actions include pick, reword, edit, squash, fixup, drop, and exec."
    )

    actions = {
        "pick": "keep the commit as-is",
        "reword": "keep the changes but edit the commit message",
        "edit": "pause after applying the commit for manual changes",
        "squash": "combine the commit with the previous commit and edit messages",
        "fixup": "combine the commit with the previous commit without keeping its message",
        "drop": "remove the commit from the rebased sequence",
        "exec": "run a shell command during the sequence",
    }

    for action, meaning in actions.items():
        print(f"{action:8} -> {meaning}")

    explain(
        "Interactive rebase is often used to clean up unpublished local "
        "history before sharing it. Rewriting commits that other people have "
        "already based work on can create integration problems."
    )


# ============================================================================
# 16. REMOTE BRANCHES
# ============================================================================

def explain_remote_branches() -> None:
    print_title("14. Remote Branches")

    explain(
        "A remote-tracking branch such as origin/main is a local reference "
        "that records the last known state of main on the remote named "
        "origin. It is not the remote repository itself."
    )

    commands = [
        "git remote -v",
        "git fetch origin",
        "git branch -r",
        "git switch -c feature origin/feature",
        "git push -u origin feature",
        "git branch -vv",
    ]

    for command in commands:
        print(command)

    explain(
        "git fetch downloads remote references and objects without merging "
        "them into the current branch. git pull is conceptually a fetch "
        "followed by an integration operation, commonly merge or rebase "
        "depending on configuration and command options."
    )


# ============================================================================
# 17. UPSTREAM TRACKING
# ============================================================================

def explain_tracking() -> None:
    print_title("15. Upstream Tracking")

    explain(
        "A local branch can have an upstream branch. Tracking information "
        "lets commands such as git status and git branch -vv show whether the "
        "local branch is ahead of, behind, or diverged from its upstream."
    )

    print(
        """
Common patterns:

git push -u origin feature/login
git branch --set-upstream-to=origin/main main
git status
git branch -vv
""".strip()
    )


# ============================================================================
# 18. BRANCH STRATEGY
# ============================================================================

def explain_branch_strategies() -> None:
    print_title("16. Branching Strategies")

    strategies = {
        "Short-lived feature branches": (
            "Create a branch for a focused change and integrate it quickly."
        ),
        "Release branches": (
            "Maintain a temporary stabilization line for a planned release."
        ),
        "Hotfix branches": (
            "Isolate urgent production fixes and integrate them deliberately."
        ),
        "Trunk-based development": (
            "Keep integration branches short-lived and integrate frequently."
        ),
        "Long-lived development branches": (
            "Maintain larger independent lines, accepting higher divergence."
        ),
    }

    for name, description in strategies.items():
        print(f"{name}: {description}")

    explain(
        "No branching strategy is universally correct. The trade-off is "
        "between isolation, integration frequency, release control, review "
        "workflow, repository complexity, and the cost of resolving drift."
    )


# ============================================================================
# 19. MERGE VS REBASE
# ============================================================================

def compare_merge_and_rebase() -> None:
    print_title("17. Merge versus Rebase")

    comparison = [
        ("Merge", "Combines histories", "Preserves existing commits", "May create merge commits"),
        ("Rebase", "Moves commits onto a new base", "Creates rewritten commit identities", "Produces a more linear history"),
    ]

    print(f"{'Operation':<12} {'Mechanism':<34} {'Commit identity':<34} {'Typical result'}")
    print("-" * 118)

    for row in comparison:
        print(f"{row[0]:<12} {row[1]:<34} {row[2]:<34} {row[3]}")

    explain(
        "A critical rule is that commit IDs depend on commit contents and "
        "parent relationships. Rebase changes parent relationships, so the "
        "rebased commits normally receive different IDs."
    )


# ============================================================================
# 20. CONFLICT RESOLUTION PRINCIPLES
# ============================================================================

def explain_conflict_resolution() -> None:
    print_title("18. Conflict Resolution Principles")

    principles = [
        "Read git status before editing.",
        "Understand which branch is current and which change is incoming.",
        "Inspect the surrounding code rather than resolving only the marked lines.",
        "Preserve the intended behavior from both sides when appropriate.",
        "Run tests after resolving conflicts.",
        "Stage only the files whose conflicts have actually been resolved.",
        "Use git diff --check to detect whitespace problems.",
        "Complete the operation with git merge --continue, git rebase --continue, or the appropriate commit workflow.",
        "Use git merge --abort or git rebase --abort when abandoning the operation is safer.",
    ]

    for principle in principles:
        print(f"* {principle}")


# ============================================================================
# 21. EDGE CASES
# ============================================================================

def explain_edge_cases() -> None:
    print_title("19. Important Edge Cases")

    cases = [
        (
            "Uncommitted changes while switching branches",
            "Git may refuse the switch if changes would be overwritten."
        ),
        (
            "Untracked files",
            "An untracked file can block a switch if another branch would place a conflicting path there."
        ),
        (
            "Binary-file conflicts",
            "Git generally cannot perform line-based automatic merging of binary content."
        ),
        (
            "Rename conflicts",
            "A rename combined with edits or another rename can require manual interpretation."
        ),
        (
            "File/directory conflicts",
            "One branch can contain a file while another uses the same path as a directory."
        ),
        (
            "Empty merge",
            "Sometimes a merge is already represented in the current history, so Git reports nothing to merge."
        ),
        (
            "Force-pushed rebased branch",
            "Remote consumers may need to reconcile their local history with rewritten commits."
        ),
        (
            "Detached HEAD commit",
            "A commit made without a branch reference can become hard to locate later unless referenced."
        ),
    ]

    for name, explanation_text in cases:
        print(f"{name}: {explanation_text}")


# ============================================================================
# 22. PERFORMANCE
# ============================================================================

def explain_performance() -> None:
    print_title("20. Performance Considerations")

    explain(
        "Branch creation is normally cheap because a branch is primarily a "
        "reference. The expensive work can appear during large merges, "
        "rebases, conflict-heavy operations, object transfer, repository "
        "maintenance, and large working-tree operations."
    )

    explain(
        "Git's object database stores content efficiently and uses hashes to "
        "identify objects. Commit graphs, packfiles, reachability analysis, "
        "and repository maintenance improve performance for large histories."
    )

    explain(
        "Frequent integration reduces the amount of divergent work that must "
        "be reconciled at once. Short-lived branches can therefore reduce "
        "conflict complexity even though they increase the number of branch "
        "references."
    )


# ============================================================================
# 23. SECURITY AND INTEGRITY
# ============================================================================

def explain_security() -> None:
    print_title("21. Security and Integrity Considerations")

    explain(
        "Git uses cryptographic object identifiers to make accidental or "
        "malicious object modification detectable through changed hashes. "
        "Modern Git also supports stronger hash algorithms and signed commits "
        "or tags for additional provenance mechanisms."
    )

    explain(
        "Do not assume that a commit being signed means every file or build "
        "artifact is trustworthy. Repository security also depends on access "
        "control, protected branches, review policies, dependency security, "
        "secret management, CI permissions, and release controls."
    )

    explain(
        "Never commit passwords, private keys, API tokens, cloud credentials, "
        "or other secrets merely because a branch is private. Git history can "
        "retain sensitive data even after a file is deleted in a later commit."
    )


# ============================================================================
# 24. PRODUCTION BEST PRACTICES
# ============================================================================

def explain_best_practices() -> None:
    print_title("22. Production Branching Practices")

    practices = [
        "Keep commits focused and logically coherent.",
        "Use descriptive branch names.",
        "Integrate small changes frequently.",
        "Do not rewrite shared history without an explicit team agreement.",
        "Review diffs before merging.",
        "Run automated tests before integration.",
        "Resolve conflicts with behavioral correctness as the priority.",
        "Use protected branches for critical shared branches.",
        "Prefer reproducible builds and automated verification.",
        "Document exceptional branching procedures.",
        "Delete obsolete local branches to reduce clutter.",
        "Use reflog and backups as recovery mechanisms rather than treating reset as a backup.",
    ]

    for practice in practices:
        print(f"* {practice}")


# ============================================================================
# 25. COMMON MISTAKES
# ============================================================================

def explain_common_mistakes() -> None:
    print_title("23. Common Mistakes")

    mistakes = [
        (
            "Confusing a branch with a folder",
            "A branch is a reference to history, not a separate directory."
        ),
        (
            "Merging while on the wrong branch",
            "Always check git branch --show-current before integration."
        ),
        (
            "Rebasing shared history casually",
            "Rebase changes commit identities and can disrupt collaborators."
        ),
        (
            "Ignoring git status during conflicts",
            "Status tells you which operation is active and which paths remain unresolved."
        ),
        (
            "Resolving only syntax rather than behavior",
            "A conflict can produce syntactically valid but logically incorrect code."
        ),
        (
            "Deleting a branch before confirming its commits",
            "Inspect history or use reflog when recovery may matter."
        ),
        (
            "Assuming git pull always means merge",
            "Pull behavior can be configured and can also explicitly use rebase."
        ),
        (
            "Using force push without understanding leases",
            "Prefer mechanisms such as git push --force-with-lease when rewriting a remote branch is intentionally required."
        ),
    ]

    for mistake, correction in mistakes:
        print(f"{mistake}: {correction}")


# ============================================================================
# 26. ADVANCED CONCEPTS
# ============================================================================

def explain_advanced_concepts() -> None:
    print_title("24. Advanced Git Branching Concepts")

    concepts = [
        (
            "Reachability",
            "A commit is reachable when a reference can traverse parent links to it."
        ),
        (
            "Merge base",
            "The merge base is a suitable common ancestor used for three-way integration."
        ),
        (
            "Fast-forward",
            "The target reference can move forward without creating a merge commit."
        ),
        (
            "Three-way merge",
            "Git compares the merge base with both branch tips to determine combined changes."
        ),
        (
            "Patch replay",
            "Rebase reapplies changes represented by commits onto another base."
        ),
        (
            "First-parent history",
            "git log --first-parent emphasizes the mainline ancestry through merge commits."
        ),
        (
            "Bisect",
            "git bisect uses a binary-search process across commits to locate a regression."
        ),
        (
            "Worktree",
            "git worktree allows multiple working directories connected to one repository."
        ),
        (
            "Submodules",
            "A repository can reference another repository at a specific commit, introducing additional branch and release coordination concerns."
        ),
    ]

    for concept, definition in concepts:
        print(f"{concept}: {definition}")


# ============================================================================
# 27. GIT BISect
# ============================================================================

def demonstrate_bisect_concept(repository: Path) -> None:
    print_title("25. Bisect Concept")

    explain(
        "When a bug is known to exist in one commit and not another, git "
        "bisect can perform a binary search through history. Each tested "
        "commit is classified as good or bad until Git identifies a likely "
        "first bad commit."
    )

    print(
        """
Typical workflow:

git bisect start
git bisect bad
git bisect good <known-good-commit>
# test the checked-out commit
git bisect good
# or:
git bisect bad
git bisect reset
""".strip()
    )

    print_subtitle("Repository remains usable after conceptual bisect example")
    git(repository, "status", "--short", "--branch")


# ============================================================================
# 28. WORKTREES
# ============================================================================

def demonstrate_worktree(repository: Path) -> None:
    print_title("26. Multiple Working Trees")

    explain(
        "A Git worktree allows multiple branches to be checked out in "
        "different directories while sharing the underlying repository "
        "objects. This can be useful when switching between a feature and "
        "an urgent fix without repeatedly changing one working directory."
    )

    worktree_path = repository.parent / "git-branching-secondary-worktree"

    try:
        git(repository, "switch", "-c", "feature/worktree")
        write_file(
            repository,
            "worktree-feature.txt",
            "worktree demonstration\n",
        )
        commit(repository, "Add worktree feature")

        git(repository, "switch", "main")
        git(
            repository,
            "worktree",
            "add",
            str(worktree_path),
            "feature/worktree",
        )

        print_subtitle("Registered worktrees")
        git(repository, "worktree", "list")

    finally:
        if worktree_path.exists():
            git(
                repository,
                "worktree",
                "remove",
                "--force",
                str(worktree_path),
                check=False,
            )

        git(repository, "branch", "-D", "feature/worktree", check=False)


# ============================================================================
# 29. TAGS AND RELEASE REFERENCES
# ============================================================================

def demonstrate_tags(repository: Path) -> None:
    print_title("27. Tags and Branches Are Different")

    explain(
        "A branch is expected to move as development continues. A release "
        "tag normally identifies a specific historical point and is intended "
        "to remain stable."
    )

    git(repository, "switch", "main")
    git(repository, "tag", "v1.0.0")

    print_subtitle("Tags")
    git(repository, "tag", "--list")

    explain(
        "A tag is not a replacement for a release branch. A tag identifies a "
        "point in history, while a branch identifies a moving development "
        "line."
    )


# ============================================================================
# 30. TESTING BRANCH INTEGRATION
# ============================================================================

def demonstrate_integration_testing(repository: Path) -> None:
    print_title("28. Integration Verification")

    explain(
        "A successful Git operation does not guarantee that the resulting "
        "software is correct. After merge or rebase, run unit tests, static "
        "analysis, builds, integration tests, and other project-specific "
        "verification."
    )

    # A tiny built-in application-style check.
    app_content = read_file(repository, "app.txt")
    assert "version=" in app_content

    print("Repository-level verification: app.txt contains a version field.")
    git(repository, "diff", "--check")
    print("Git whitespace verification: passed.")


# ============================================================================
# 31. AUTOMATION AND CI
# ============================================================================

def explain_ci_relationship() -> None:
    print_title("29. Branches and Continuous Integration")

    explain(
        "A common production workflow is to trigger automated validation for "
        "branch pushes and pull requests. The branch provides an isolated "
        "change set, while CI checks whether that change remains compatible "
        "with the integration target."
    )

    explain(
        "A robust pipeline can include formatting checks, static analysis, "
        "unit tests, integration tests, security scanning, package builds, "
        "and deployment checks. Git branching supplies the history model; "
        "CI supplies automated verification."
    )


# ============================================================================
# 32. COMPLETE WORKFLOW
# ============================================================================

def demonstrate_complete_feature_workflow(repository: Path) -> None:
    print_title("30. Complete Feature Workflow")

    explain(
        "The following compact workflow models a practical feature branch "
        "from creation through integration."
    )

    git(repository, "switch", "main")
    git(repository, "switch", "-c", "feature/audit")

    write_file(
        repository,
        "audit.txt",
        "audit-log=enabled\n",
    )
    commit(repository, "Enable audit logging")

    write_file(
        repository,
        "audit.txt",
        "audit-log=enabled\nretention-days=90\n",
    )
    commit(repository, "Configure audit retention")

    print_subtitle("Feature branch before integration")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
        "-8",
    )

    git(repository, "switch", "main")
    git(repository, "merge", "--no-ff", "feature/audit", "-m",
        "Merge audit feature")

    print_subtitle("Integrated history")
    git(
        repository,
        "log",
        "--oneline",
        "--decorate",
        "--graph",
        "--all",
        "-10",
    )

    git(repository, "branch", "-d", "feature/audit")


# ============================================================================
# 33. COMMAND REFERENCE
# ============================================================================

def print_command_reference() -> None:
    print_title("31. Practical Command Reference")

    commands = [
        ("git branch", "List local branches."),
        ("git branch <name>", "Create a branch."),
        ("git switch <name>", "Switch branches."),
        ("git switch -c <name>", "Create and switch to a branch."),
        ("git branch -m <old> <new>", "Rename a branch."),
        ("git branch -d <name>", "Delete a merged branch."),
        ("git branch -D <name>", "Force-delete a branch."),
        ("git merge <branch>", "Merge another branch into the current branch."),
        ("git merge --no-ff <branch>", "Force a merge commit."),
        ("git merge --abort", "Abort an in-progress merge."),
        ("git rebase <base>", "Replay current branch commits onto another base."),
        ("git rebase --continue", "Continue a paused rebase."),
        ("git rebase --abort", "Abort an in-progress rebase."),
        ("git status", "Inspect current working-tree and integration state."),
        ("git log --graph --oneline --all", "Visualize history."),
        ("git diff", "Inspect working-tree changes."),
        ("git fetch", "Update remote-tracking references."),
        ("git pull", "Fetch and integrate according to configuration/options."),
        ("git push", "Send commits and references to a remote."),
        ("git cherry-pick <commit>", "Apply one selected commit."),
        ("git reflog", "Inspect local reference movements."),
        ("git merge-base A B", "Find a common ancestor suitable for merging."),
        ("git worktree add", "Create another working directory."),
        ("git revert <commit>", "Create a new commit that reverses a commit."),
        ("git restore <path>", "Restore working-tree/index content."),
        ("git reset", "Move/reset references and optionally index/worktree."),
        ("git tag <name>", "Create a tag at the current or selected revision."),
        ("git bisect", "Binary-search history for a regression."),
    ]

    width = max(len(command) for command, _ in commands)

    for command, description in commands:
        print(f"{command:<{width}}  {description}")


# ============================================================================
# 34. MAIN PROGRAM
# ============================================================================

def main() -> None:
    print_title("Git Branching: Complete Practical Study")

    if shutil.which("git") is None:
        raise SystemExit(
            "Git was not found on PATH. Install Git and run this program again."
        )

    print(f"Git executable: {shutil.which('git')}")

    repository = create_repository()
    print(f"Temporary repository: {repository}")

    try:
        demonstrate_commit_graph_concept()
        show_repository_state(repository)

        demonstrate_basic_branches(repository)
        demonstrate_fast_forward_merge(repository)
        demonstrate_merge_commit(repository)
        demonstrate_conflict(repository)
        demonstrate_rebase(repository)
        demonstrate_rebase_conflict(repository)
        demonstrate_detached_head(repository)
        demonstrate_diagnostics(repository)
        demonstrate_reflog(repository)
        demonstrate_recovery_commands(repository)
        demonstrate_cherry_pick(repository)
        explain_interactive_rebase()
        explain_remote_branches()
        explain_tracking()
        explain_branch_strategies()
        compare_merge_and_rebase()
        explain_conflict_resolution()
        explain_edge_cases()
        explain_performance()
        explain_security()
        explain_best_practices()
        explain_common_mistakes()
        explain_advanced_concepts()
        demonstrate_bisect_concept(repository)
        demonstrate_worktree(repository)
        demonstrate_tags(repository)
        demonstrate_integration_testing(repository)
        explain_ci_relationship()
        demonstrate_complete_feature_workflow(repository)
        print_command_reference()

        print_title("Final Repository State")
        show_repository_state(repository)

        print(
            "\nAll demonstrations completed. The temporary repository will "
            "be removed when the program exits."
        )

    finally:
        shutil.rmtree(repository, ignore_errors=True)


if __name__ == "__main__":
    main()
